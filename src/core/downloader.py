"""
Seal Desktop - Core Downloader
Wraps yt-dlp with rich state management, sequential queue processing,
audio/video stream merging, pause/resume, and multi-download handling.
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path

import yt_dlp

from .ffmpeg_utils import get_ffmpeg_path, is_ffmpeg_available

# ──────────────────────────────────────────────
# State enums
# ──────────────────────────────────────────────


class DownloadState(Enum):
    IDLE = auto()
    QUEUED = auto()
    FETCHING_INFO = auto()
    DOWNLOADING = auto()
    DOWNLOADING_PLAYLIST = auto()
    PAUSED = auto()
    CONVERTING = auto()
    COMPLETED = auto()
    CANCELLED = auto()
    ERROR = auto()


# ──────────────────────────────────────────────
# Data classes
# ──────────────────────────────────────────────


@dataclass
class DownloadPreferences:
    extract_audio: bool = False
    audio_format: str = "mp3"  # mp3 | m4a | opus | flac | wav | best
    video_format: str = "bestvideo+bestaudio/best"
    video_quality: str = "best"  # best | 2160 | 1440 | 1080 | 720 | 480 | 360
    video_container: str = "mp4"  # mp4 | mkv
    embed_metadata: bool = True
    embed_thumbnail: bool = True
    embed_subtitles: bool = False

    subtitle_languages: str = "en"
    output_dir: str = str(Path.home() / "Downloads" / "Seal")
    output_template: str = "%(title).200B.%(ext)s"
    playlist_subdir: bool = True
    restrict_filenames: bool = False
    proxy: str = ""
    rate_limit: str = ""  # e.g. "1M"
    concurrent_fragments: int = 4
    use_aria2c: bool = False
    cookies_file: str = ""
    extra_args: str = ""


@dataclass
class VideoInfo:
    title: str = ""
    uploader: str = ""
    duration: int = 0  # seconds
    thumbnail: str = ""
    url: str = ""
    ext: str = ""
    filesize: int = 0
    is_playlist: bool = False
    playlist_count: int = 0
    formats: list = field(default_factory=list)


@dataclass
class DownloadTask:
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    url: str = ""
    title: str = "Unknown"
    state: DownloadState = DownloadState.IDLE
    progress: float = 0.0  # 0.0 – 1.0
    speed: str = ""
    eta: str = ""
    size: str = ""
    error: str = ""
    playlist_index: int = 0
    playlist_count: int = 0
    thumbnail_url: str = ""
    output_path: str = ""
    is_audio: bool = False
    prefs: DownloadPreferences = field(default_factory=DownloadPreferences)


# ──────────────────────────────────────────────
# Progress hook helpers
# ──────────────────────────────────────────────


def _fmt_bytes(n: int | None) -> str:
    if n is None:
        return ""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024.0:
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return str(n)


def _fmt_speed(bps: float | None) -> str:
    if bps is None:
        return ""
    return _fmt_bytes(int(bps)) + "/s"


def _fmt_eta(seconds: int | None) -> str:
    if seconds is None:
        return ""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


# ──────────────────────────────────────────────
# Main Downloader
# ──────────────────────────────────────────────


class Downloader:
    """
    Download manager supporting both sequential batch queues and direct execution.
    Manages task lifecycles: Queued -> Fetching -> Downloading -> Paused / Completed.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, DownloadTask] = {}
        self._queue: list[str] = []  # Ordered task_ids
        self._threads: dict[str, threading.Thread] = {}
        self._cancel_flags: dict[str, threading.Event] = {}
        self._pause_flags: dict[str, threading.Event] = {}
        self._lock = threading.RLock()
        self._queue_running: bool = False
        self._active_task_id: str | None = None

        # Callbacks – set by the UI layer
        self.on_task_updated: Callable[[DownloadTask], None] = lambda _: None
        self.on_info_fetched: Callable[[VideoInfo], None] = lambda _: None
        self.on_error: Callable[[str, str], None] = lambda _id, _msg: None
        self.on_queue_status_changed: Callable[[bool], None] = lambda _: None

    # ── Public API ────────────────────────────

    def fetch_info(self, url: str, prefs: DownloadPreferences) -> VideoInfo | None:
        """Synchronously fetch video/playlist metadata (runs in caller's thread)."""
        ydl_opts = self._base_opts(prefs, quiet=True)
        ydl_opts.update(
            {
                "skip_download": True,
                "dump_single_json": True,
                "flat_playlist": True,
                "noplaylist": False,
                "playlistend": 1,
            }
        )
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info is None:
                    return None
                is_pl = info.get("_type") == "playlist"
                entries = info.get("entries") or []
                first = entries[0] if entries else info
                return VideoInfo(
                    title=info.get("title") or first.get("title") or "Unknown",
                    uploader=first.get("uploader") or first.get("channel") or "",
                    duration=first.get("duration") or 0,
                    thumbnail=first.get("thumbnail") or "",
                    url=url,
                    ext=first.get("ext") or "",
                    filesize=first.get("filesize_approx") or 0,
                    is_playlist=is_pl,
                    playlist_count=len(entries) if is_pl else 1,
                    formats=first.get("formats") or [],
                )
        except Exception:  # noqa: BLE001
            return None

    def queue_download(self, url: str, prefs: DownloadPreferences) -> str:
        """
        Stage a download in the queue without running it immediately.
        Returns the new task_id.
        """
        task = DownloadTask(
            url=url,
            is_audio=prefs.extract_audio,
            prefs=prefs,
            state=DownloadState.QUEUED,
        )
        with self._lock:
            self._tasks[task.task_id] = task
            self._queue.append(task.task_id)

        self._update_task(task)

        # If queue is already running, advance queue
        if self._queue_running and not self._active_task_id:
            self._process_next_in_queue()

        return task.task_id

    def start_download(self, url: str, prefs: DownloadPreferences) -> str:
        """Queue and immediately trigger sequential download processing."""
        task_id = self.queue_download(url, prefs)
        self.start_queue()
        return task_id

    def start_queue(self) -> None:
        """Start sequential download processing for all queued tasks."""
        with self._lock:
            self._queue_running = True
        self.on_queue_status_changed(True)
        self._process_next_in_queue()

    def pause_queue(self) -> None:
        """Pause sequential processing."""
        with self._lock:
            self._queue_running = False
        self.on_queue_status_changed(False)

    def is_queue_running(self) -> bool:
        return self._queue_running

    def pause_download(self, task_id: str) -> None:
        """Pause a specific downloading or queued task."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return

            if task.state == DownloadState.QUEUED:
                task.state = DownloadState.PAUSED
                self._update_task(task)
                return

            if task.state in (
                DownloadState.DOWNLOADING,
                DownloadState.DOWNLOADING_PLAYLIST,
                DownloadState.FETCHING_INFO,
            ):
                task.state = DownloadState.PAUSED
                if task_id in self._pause_flags:
                    self._pause_flags[task_id].set()
                if task_id in self._cancel_flags:
                    self._cancel_flags[task_id].set()
                self._update_task(task)

    def resume_download(self, task_id: str) -> None:
        """Resume a paused task."""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task or task.state != DownloadState.PAUSED:
                return
            task.state = DownloadState.QUEUED
            self._update_task(task)

        if self._queue_running and not self._active_task_id:
            self._process_next_in_queue()

    def cancel_download(self, task_id: str) -> None:
        """Cancel an active task."""
        with self._lock:
            ev = self._cancel_flags.get(task_id)
            task = self._tasks.get(task_id)
            if task:
                task.state = DownloadState.CANCELLED
                self._update_task(task)
        if ev:
            ev.set()

    def delete_task(self, task_id: str) -> None:
        """Completely remove a task from memory and queue, cancelling if active."""
        self.cancel_download(task_id)
        with self._lock:
            if task_id in self._queue:
                self._queue.remove(task_id)
            self._tasks.pop(task_id, None)
            self._threads.pop(task_id, None)
            self._cancel_flags.pop(task_id, None)
            self._pause_flags.pop(task_id, None)
            was_active = self._active_task_id == task_id
            if was_active:
                self._active_task_id = None

        if was_active and self._queue_running:
            self._process_next_in_queue()

    def get_tasks(self) -> list[DownloadTask]:
        with self._lock:
            return list(self._tasks.values())

    def get_queued_count(self) -> int:
        with self._lock:
            return sum(1 for t in self._tasks.values() if t.state == DownloadState.QUEUED)

    def clear_completed(self) -> None:
        with self._lock:
            done = [
                k
                for k, v in self._tasks.items()
                if v.state
                in (DownloadState.COMPLETED, DownloadState.CANCELLED, DownloadState.ERROR)
            ]
            for k in done:
                if k in self._queue:
                    self._queue.remove(k)
                self._tasks.pop(k, None)
                self._threads.pop(k, None)
                self._cancel_flags.pop(k, None)
                self._pause_flags.pop(k, None)

    # ── Queue Runner ──────────────────────────

    def _process_next_in_queue(self) -> None:
        """Selects and triggers the next task sequentially (one after one)."""
        with self._lock:
            if not self._queue_running:
                return
            if self._active_task_id:
                # Still running a task
                return

            # Find next QUEUED task in queue order
            next_task: DownloadTask | None = None
            for tid in self._queue:
                t = self._tasks.get(tid)
                if t and t.state == DownloadState.QUEUED:
                    next_task = t
                    break

            if not next_task:
                return

            self._active_task_id = next_task.task_id
            cancel_ev = threading.Event()
            pause_ev = threading.Event()
            self._cancel_flags[next_task.task_id] = cancel_ev
            self._pause_flags[next_task.task_id] = pause_ev

            thread = threading.Thread(
                target=self._worker,
                args=(next_task, next_task.prefs, cancel_ev, pause_ev),
                daemon=True,
                name=f"seal-dl-{next_task.task_id[:8]}",
            )
            self._threads[next_task.task_id] = thread

        thread.start()

    def _on_task_finished(self, task_id: str) -> None:
        """Called when a worker finishes its run; triggers the next queued item."""
        with self._lock:
            if self._active_task_id == task_id:
                self._active_task_id = None

        if self._queue_running:
            self._process_next_in_queue()

    # ── Internal Worker ───────────────────────

    def _update_task(self, task: DownloadTask) -> None:
        with self._lock:
            self._tasks[task.task_id] = task
        self.on_task_updated(task)

    def _worker(
        self,
        task: DownloadTask,
        prefs: DownloadPreferences,
        cancel_ev: threading.Event,
        pause_ev: threading.Event,
    ) -> None:
        task.state = DownloadState.FETCHING_INFO
        self._update_task(task)

        ydl_opts = self._build_opts(task, prefs, cancel_ev, pause_ev)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(task.url, download=False)
                if info:
                    task.title = info.get("title") or task.url
                    task.thumbnail_url = info.get("thumbnail") or ""
                    is_pl = info.get("_type") == "playlist"
                    if is_pl:
                        task.playlist_count = len(info.get("entries") or [])
                        task.state = DownloadState.DOWNLOADING_PLAYLIST
                    else:
                        task.state = DownloadState.DOWNLOADING
                    self._update_task(task)

                    if cancel_ev.is_set():
                        task.state = (
                            DownloadState.PAUSED if pause_ev.is_set() else DownloadState.CANCELLED
                        )
                        self._update_task(task)
                        return

                    ydl.download([task.url])

            if pause_ev.is_set():
                task.state = DownloadState.PAUSED
            elif cancel_ev.is_set():
                task.state = DownloadState.CANCELLED
            else:
                task.state = DownloadState.COMPLETED
                task.progress = 1.0
            self._update_task(task)

        except yt_dlp.utils.DownloadError as exc:
            if pause_ev.is_set():
                task.state = DownloadState.PAUSED
            elif cancel_ev.is_set():
                task.state = DownloadState.CANCELLED
            else:
                task.state = DownloadState.ERROR
                task.error = str(exc)
            self._update_task(task)
        except Exception as exc:  # noqa: BLE001
            if pause_ev.is_set():
                task.state = DownloadState.PAUSED
            elif cancel_ev.is_set():
                task.state = DownloadState.CANCELLED
            else:
                task.state = DownloadState.ERROR
                task.error = str(exc)
            self._update_task(task)
        finally:
            self._on_task_finished(task.task_id)

    def _progress_hook(
        self, task: DownloadTask, cancel_ev: threading.Event, pause_ev: threading.Event
    ) -> Callable:
        def hook(d: dict) -> None:
            if pause_ev.is_set() or cancel_ev.is_set():
                raise yt_dlp.utils.DownloadError("Operation interrupted by user")

            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes") or 0
                task.progress = downloaded / total if total else 0.0
                task.speed = _fmt_speed(d.get("speed"))
                task.eta = _fmt_eta(d.get("eta"))
                task.size = _fmt_bytes(total)
                if task.state not in (
                    DownloadState.DOWNLOADING,
                    DownloadState.DOWNLOADING_PLAYLIST,
                    DownloadState.PAUSED,
                ):
                    task.state = DownloadState.DOWNLOADING
                self._update_task(task)

            elif status == "finished":
                task.output_path = d.get("filename") or ""
                task.state = DownloadState.CONVERTING
                task.progress = 0.99
                self._update_task(task)

            elif status == "error":
                task.state = DownloadState.ERROR
                task.error = str(d.get("error") or "Unknown error")
                self._update_task(task)

        return hook

    def _postproc_hook(self, task: DownloadTask) -> Callable:
        def hook(d: dict) -> None:
            if d.get("status") == "finished":
                task.output_path = d.get("info_dict", {}).get("filepath") or task.output_path
                self._update_task(task)

        return hook

    def _playlist_hook(self, task: DownloadTask) -> Callable:
        def hook(d: dict) -> None:
            idx = d.get("playlist_index")
            count = d.get("n_entries")
            if idx:
                task.playlist_index = idx
            if count:
                task.playlist_count = count
            self._update_task(task)

        return hook

    def _base_opts(self, prefs: DownloadPreferences, quiet: bool = False) -> dict:
        opts: dict = {
            "quiet": quiet,
            "no_warnings": quiet,
            "ignoreerrors": False,
            "noplaylist": False,
        }
        if prefs.proxy:
            opts["proxy"] = prefs.proxy
        if prefs.cookies_file and Path(prefs.cookies_file).exists():
            opts["cookiefile"] = prefs.cookies_file

        ffmpeg_bin = get_ffmpeg_path()
        if ffmpeg_bin:
            opts["ffmpeg_location"] = ffmpeg_bin

        return opts

    def _build_opts(
        self,
        task: DownloadTask,
        prefs: DownloadPreferences,
        cancel_ev: threading.Event,
        pause_ev: threading.Event,
    ) -> dict:
        out_dir = prefs.output_dir
        Path(out_dir).mkdir(parents=True, exist_ok=True)

        if prefs.playlist_subdir:
            outtmpl = str(
                Path(out_dir) / "%(playlist_title,title|Unknown)s" / prefs.output_template
            )
        else:
            outtmpl = str(Path(out_dir) / prefs.output_template)

        opts = self._base_opts(prefs, quiet=True)
        opts.update(
            {
                "outtmpl": outtmpl,
                "progress_hooks": [self._progress_hook(task, cancel_ev, pause_ev)],
                "postprocessor_hooks": [self._postproc_hook(task)],
                "match_filter": yt_dlp.utils.match_filter_func("!is_live"),
                "concurrent_fragment_downloads": prefs.concurrent_fragments,
                "retries": 5,
                "fragment_retries": 5,
                "continuedl": True,  # Allows resume from .part files
            }
        )

        has_ffmpeg = is_ffmpeg_available()

        if prefs.extract_audio:
            if has_ffmpeg:
                opts["format"] = "bestaudio/best"
                opts["postprocessors"] = [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": prefs.audio_format,
                        "preferredquality": "320" if prefs.audio_format == "mp3" else "0",
                    }
                ]
                if prefs.embed_thumbnail:
                    opts["postprocessors"].append(
                        {"key": "EmbedThumbnail", "already_have_thumbnail": False}
                    )
                    opts["writethumbnail"] = True
                if prefs.embed_metadata:
                    opts["postprocessors"].append({"key": "FFmpegMetadata", "add_metadata": True})
            else:
                # Without ffmpeg, download best direct audio without extraction
                opts["format"] = "bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio/best"

        else:
            # Video mode: ensure audio and video are NEVER separated
            container = prefs.video_container or "mp4"

            if has_ffmpeg:
                # With ffmpeg: download best separate video + audio streams and MERGE them into a single file
                if prefs.video_quality == "best":
                    fmt = "bestvideo+bestaudio/best"
                else:
                    h = prefs.video_quality
                    fmt = f"bestvideo[height<={h}]+bestaudio/best[height<={h}]"
                opts["format"] = fmt
                opts["merge_output_format"] = container
                if prefs.embed_metadata:
                    opts.setdefault("postprocessors", [])
                    opts["postprocessors"].append({"key": "FFmpegMetadata", "add_metadata": True})
                if prefs.embed_subtitles:
                    opts["writesubtitles"] = True
                    opts["subtitleslangs"] = [
                        s.strip() for s in prefs.subtitle_languages.split(",")
                    ]
                    opts.setdefault("postprocessors", [])
                    opts["postprocessors"].append({"key": "FFmpegEmbedSubtitle"})
            else:
                # WITHOUT ffmpeg: yt-dlp CANNOT merge separate video and audio streams!
                # If we used bestvideo+bestaudio, it would leave two unmerged files.
                # Therefore, we MUST request a pre-muxed format containing BOTH video and audio!
                if prefs.video_quality == "best":
                    fmt = "best[ext=mp4]/best/bestvideo[ext=mp4]+bestaudio[ext=m4a]"
                else:
                    h = prefs.video_quality
                    fmt = f"best[height<={h}][ext=mp4]/best[height<={h}]/best"
                opts["format"] = fmt

        if prefs.restrict_filenames:
            opts["restrictfilenames"] = True

        if prefs.rate_limit:
            opts["ratelimit"] = prefs.rate_limit

        if prefs.use_aria2c:
            opts["external_downloader"] = "aria2c"
            opts["external_downloader_args"] = [
                "--min-split-size=1M",
                "--max-connection-per-server=16",
                "--max-concurrent-downloads=16",
                "--split=16",
            ]

        # Extra raw args
        if prefs.extra_args:
            for part in prefs.extra_args.split():
                opts.setdefault("_raw_options", []).append(part)

        return opts


# ── Singleton ─────────────────────────────────
downloader = Downloader()
