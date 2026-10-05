"""
Seal Desktop - Core Downloader
Wraps yt-dlp with rich state management, progress tracking,
playlist support, and custom command execution.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Optional

import yt_dlp


# ──────────────────────────────────────────────
# State enums
# ──────────────────────────────────────────────


class DownloadState(Enum):
    IDLE = auto()
    FETCHING_INFO = auto()
    DOWNLOADING = auto()
    DOWNLOADING_PLAYLIST = auto()
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
    audio_format: str = "mp3"          # mp3 | m4a | opus | flac | wav | best
    video_format: str = "bestvideo+bestaudio/best"
    video_quality: str = "best"        # best | 2160 | 1440 | 1080 | 720 | 480 | 360
    embed_metadata: bool = True
    embed_thumbnail: bool = True
    embed_subtitles: bool = False

    subtitle_languages: str = "en"
    output_dir: str = str(Path.home() / "Downloads" / "Seal")
    output_template: str = "%(title).200B.%(ext)s"
    playlist_subdir: bool = True
    restrict_filenames: bool = False
    proxy: str = ""
    rate_limit: str = ""               # e.g. "1M"
    concurrent_fragments: int = 4
    use_aria2c: bool = False
    cookies_file: str = ""
    extra_args: str = ""


@dataclass
class VideoInfo:
    title: str = ""
    uploader: str = ""
    duration: int = 0          # seconds
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
    progress: float = 0.0          # 0.0 – 1.0
    speed: str = ""
    eta: str = ""
    size: str = ""
    error: str = ""
    playlist_index: int = 0
    playlist_count: int = 0
    thumbnail_url: str = ""
    output_path: str = ""
    is_audio: bool = False


# ──────────────────────────────────────────────
# Progress hook helpers
# ──────────────────────────────────────────────


def _fmt_bytes(n: Optional[int]) -> str:
    if n is None:
        return ""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024.0:
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return str(n)


def _fmt_speed(bps: Optional[float]) -> str:
    if bps is None:
        return ""
    return _fmt_bytes(int(bps)) + "/s"


def _fmt_eta(seconds: Optional[int]) -> str:
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
    Thread-safe download manager.  Runs each download in its own thread.
    Consumers register callbacks that are fired from the worker thread.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, DownloadTask] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._cancel_flags: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

        # Callbacks – set by the UI layer
        self.on_task_updated: Callable[[DownloadTask], None] = lambda _: None
        self.on_info_fetched: Callable[[VideoInfo], None] = lambda _: None
        self.on_error: Callable[[str, str], None] = lambda _id, _msg: None

    # ── Public API ────────────────────────────

    def fetch_info(self, url: str, prefs: DownloadPreferences) -> Optional[VideoInfo]:
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
        except Exception as exc:  # noqa: BLE001
            return None

    def start_download(
        self, url: str, prefs: DownloadPreferences
    ) -> str:
        """Enqueue a download and return its task_id."""
        task = DownloadTask(url=url, is_audio=prefs.extract_audio)
        cancel_ev = threading.Event()

        with self._lock:
            self._tasks[task.task_id] = task
            self._cancel_flags[task.task_id] = cancel_ev

        t = threading.Thread(
            target=self._worker,
            args=(task, prefs, cancel_ev),
            daemon=True,
            name=f"seal-dl-{task.task_id[:8]}",
        )
        with self._lock:
            self._threads[task.task_id] = t
        t.start()
        return task.task_id

    def cancel_download(self, task_id: str) -> None:
        with self._lock:
            ev = self._cancel_flags.get(task_id)
        if ev:
            ev.set()

    def get_tasks(self) -> list[DownloadTask]:
        with self._lock:
            return list(self._tasks.values())

    def clear_completed(self) -> None:
        with self._lock:
            done = [
                k
                for k, v in self._tasks.items()
                if v.state
                in (DownloadState.COMPLETED, DownloadState.CANCELLED, DownloadState.ERROR)
            ]
            for k in done:
                self._tasks.pop(k, None)
                self._threads.pop(k, None)
                self._cancel_flags.pop(k, None)

    # ── Internal ──────────────────────────────

    def _update_task(self, task: DownloadTask) -> None:
        with self._lock:
            self._tasks[task.task_id] = task
        self.on_task_updated(task)

    def _worker(
        self, task: DownloadTask, prefs: DownloadPreferences, cancel_ev: threading.Event
    ) -> None:
        task.state = DownloadState.FETCHING_INFO
        self._update_task(task)

        ydl_opts = self._build_opts(task, prefs, cancel_ev)

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
                        task.state = DownloadState.CANCELLED
                        self._update_task(task)
                        return

                    ydl.download([task.url])

            if cancel_ev.is_set():
                task.state = DownloadState.CANCELLED
            else:
                task.state = DownloadState.COMPLETED
                task.progress = 1.0
            self._update_task(task)

        except yt_dlp.utils.DownloadError as exc:
            if cancel_ev.is_set():
                task.state = DownloadState.CANCELLED
            else:
                task.state = DownloadState.ERROR
                task.error = str(exc)
            self._update_task(task)
        except Exception as exc:  # noqa: BLE001
            task.state = DownloadState.ERROR
            task.error = str(exc)
            self._update_task(task)

    def _progress_hook(
        self, task: DownloadTask, cancel_ev: threading.Event
    ) -> Callable:
        def hook(d: dict) -> None:
            status = d.get("status")
            if cancel_ev.is_set():
                raise yt_dlp.utils.DownloadError("Cancelled by user")

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
        return opts

    def _build_opts(
        self, task: DownloadTask, prefs: DownloadPreferences, cancel_ev: threading.Event
    ) -> dict:
        out_dir = prefs.output_dir
        Path(out_dir).mkdir(parents=True, exist_ok=True)

        if prefs.playlist_subdir:
            outtmpl = str(
                Path(out_dir)
                / "%(playlist_title,title|Unknown)s"
                / prefs.output_template
            )
        else:
            outtmpl = str(Path(out_dir) / prefs.output_template)

        opts = self._base_opts(prefs, quiet=True)
        opts.update(
            {
                "outtmpl": outtmpl,
                "progress_hooks": [self._progress_hook(task, cancel_ev)],
                "postprocessor_hooks": [self._postproc_hook(task)],
                "match_filter": yt_dlp.utils.match_filter_func("!is_live"),
                "concurrent_fragment_downloads": prefs.concurrent_fragments,
                "retries": 5,
                "fragment_retries": 5,
            }
        )

        if prefs.extract_audio:
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
            # Build quality-constrained format string
            if prefs.video_quality == "best":
                fmt = "bestvideo+bestaudio/best"
            else:
                height = prefs.video_quality
                fmt = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"
            opts["format"] = fmt
            opts["merge_output_format"] = "mkv"
            if prefs.embed_metadata:
                opts.setdefault("postprocessors", [])
                opts["postprocessors"].append(
                    {"key": "FFmpegMetadata", "add_metadata": True}
                )
            if prefs.embed_subtitles:
                opts["writesubtitles"] = True
                opts["subtitleslangs"] = [
                    s.strip() for s in prefs.subtitle_languages.split(",")
                ]
                opts.setdefault("postprocessors", [])
                opts["postprocessors"].append({"key": "FFmpegEmbedSubtitle"})

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
