"""
Seal Desktop – Download Page
Supports multi-link staged queueing, successive execution, pause/resume,
audio-video merger controls, and full Arabic/English bilingual interface.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox

from ...core.downloader import (
    DownloadPreferences,
    DownloadState,
    DownloadTask,
    downloader,
)
from ...core.ffmpeg_utils import download_ffmpeg_async, is_ffmpeg_available
from ...core.i18n import add_language_listener, remove_language_listener, t
from ...core.logger import YtDlpLogger
from ...core.notifications import send_notification
from ...core.settings import settings
from ..theme import FONTS, SPACING
from ..theme import PALETTE as P
from ..widgets import (
    SealButton,
    SealCard,
    SealEntry,
    SealLabel,
    SealProgressBar,
    SealScrollFrame,
    SealSwitch,
)

# ──────────────────────────────────────────────
# Download card (one per download in queue/active)
# ──────────────────────────────────────────────


class DownloadCard(SealCard):
    def __init__(
        self,
        parent: tk.Widget,
        task: DownloadTask,
        on_delete: Callable[[str], None],
        on_move: Callable[[str, int], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.task = task
        self._on_delete = on_delete
        self._on_move = on_move
        self._build()

    def _build(self) -> None:
        pad = SPACING["md"]
        self.configure(padx=pad, pady=pad)

        # Row 1: Type icon + title + actions
        row1 = tk.Frame(self, bg=P["bg_1"])
        row1.pack(fill="x")

        type_icon = "🎵" if self.task.is_audio else "🎬"
        self._title_lbl = tk.Label(
            row1,
            text=f"{type_icon}  {self.task.title[:80]}",
            bg=P["bg_1"],
            fg=P["text_primary"],
            font=FONTS["heading3"],
            anchor="w",
        )
        self._title_lbl.pack(side="left", fill="x", expand=True)

        # Action buttons frame (Delete, Pause/Resume, Open Folder, Reorder)
        self._actions_frame = tk.Frame(row1, bg=P["bg_1"])
        self._actions_frame.pack(side="right")

        self._up_btn = SealButton(
            self._actions_frame,
            text="▲",
            variant="ghost",
            command=self._move_up,
            width=26,
            height=28,
        )

        self._down_btn = SealButton(
            self._actions_frame,
            text="▼",
            variant="ghost",
            command=self._move_down,
            width=26,
            height=28,
        )

        self._folder_btn = SealButton(
            self._actions_frame,
            text="📂",
            variant="ghost",
            command=self._open_folder,
            width=32,
            height=28,
        )

        self._pause_btn = SealButton(
            self._actions_frame,
            text="⏸",
            variant="ghost",
            command=self._toggle_pause,
            width=32,
            height=28,
        )
        self._pause_btn.pack(side="left", padx=(4, 0))

        self._retry_btn = SealButton(
            self._actions_frame,
            text="↻",
            variant="secondary",
            command=self._retry,
            width=32,
            height=28,
        )
        self._retry_btn.pack(side="left", padx=(4, 0))

        self._delete_btn = SealButton(
            self._actions_frame,
            text="🗑",
            variant="ghost",
            command=self._delete,
            width=32,
            height=28,
        )
        self._delete_btn.pack(side="left", padx=(4, 0))

        # Row 2: State label + transfer stats
        row2 = tk.Frame(self, bg=P["bg_1"])
        row2.pack(fill="x", pady=(4, 0))

        self._state_lbl = tk.Label(
            row2, bg=P["bg_1"], fg=P["accent"], font=FONTS["body_sm"], anchor="w"
        )
        self._state_lbl.pack(side="left")

        self._stats_lbl = tk.Label(
            row2, bg=P["bg_1"], fg=P["text_secondary"], font=FONTS["body_sm"], anchor="e"
        )
        self._stats_lbl.pack(side="right")

        # Row 3: Progress bar
        self._pbar = SealProgressBar(self, height=6)
        self._pbar.pack(fill="x", pady=(8, 4))

        # Row 4: URL
        self._url_lbl = tk.Label(
            self,
            text=self.task.url[:85] + ("…" if len(self.task.url) > 85 else ""),
            bg=P["bg_1"],
            fg=P["text_tertiary"],
            font=FONTS["caption"],
            anchor="w",
        )
        self._url_lbl.pack(fill="x")

        # Separator
        sep = tk.Frame(self, bg=P["divider"], height=1)
        sep.pack(fill="x", pady=(pad, 0))

        self.refresh(self.task)

    def refresh(self, task: DownloadTask) -> None:
        self.task = task

        state_labels = {
            DownloadState.IDLE: (t("state_idle"), P["text_secondary"]),
            DownloadState.QUEUED: (t("state_queued"), P["warning"]),
            DownloadState.FETCHING_INFO: (t("state_fetching"), P["info"]),
            DownloadState.DOWNLOADING: (t("state_downloading"), P["accent"]),
            DownloadState.DOWNLOADING_PLAYLIST: (
                t("state_playlist", index=task.playlist_index, count=task.playlist_count),
                P["accent"],
            ),
            DownloadState.PAUSED: (t("state_paused"), P["warning"]),
            DownloadState.CONVERTING: (t("state_converting"), P["accent_light"]),
            DownloadState.COMPLETED: (t("state_completed"), P["success"]),
            DownloadState.CANCELLED: (t("state_cancelled"), P["text_secondary"]),
            DownloadState.ERROR: (t("state_error"), P["error"]),
        }
        label, color = state_labels.get(task.state, ("…", P["text_secondary"]))

        title_text = task.title[:80] if task.title else task.url[:80]
        type_icon = "🎵" if task.is_audio else "🎬"
        self._title_lbl.configure(text=f"{type_icon}  {title_text}")
        self._state_lbl.configure(text=label, fg=color)

        stats = ""
        if task.state in (DownloadState.QUEUED, DownloadState.PAUSED) and not task.speed:
            parts = []
            if task.quality_label:
                parts.append(task.quality_label)
            if task.estimated_size or task.size:
                parts.append(task.estimated_size or task.size)
            if task.duration_str:
                parts.append(task.duration_str)
            stats = " · ".join(parts)
        else:
            if task.speed:
                stats += f"{task.speed}  "
            if task.size:
                stats += f"{task.size}  "
            if task.eta:
                stats += f"ETA {task.eta}"
        self._stats_lbl.configure(text=stats.strip())

        if task.uploader:
            url_display = f"👤 {task.uploader} · {task.url[:70]}"
        else:
            url_display = task.url[:85] + ("…" if len(task.url) > 85 else "")
        self._url_lbl.configure(text=url_display)

        self._pbar.set_progress(task.progress)

        # Update button states
        if task.state == DownloadState.QUEUED and self._on_move:
            self._up_btn.pack(side="left", padx=(2, 0))
            self._down_btn.pack(side="left", padx=(2, 0))
        else:
            self._up_btn.pack_forget()
            self._down_btn.pack_forget()

        if task.state == DownloadState.PAUSED:
            self._pause_btn.configure_text("▶")
            self._pause_btn.pack(side="left", padx=(4, 0))
        elif task.state in (
            DownloadState.DOWNLOADING,
            DownloadState.DOWNLOADING_PLAYLIST,
            DownloadState.FETCHING_INFO,
        ):
            self._pause_btn.configure_text("⏸")
            self._pause_btn.pack(side="left", padx=(4, 0))
        elif task.state == DownloadState.QUEUED:
            self._pause_btn.configure_text("⏸")
            self._pause_btn.pack(side="left", padx=(4, 0))
        else:
            self._pause_btn.pack_forget()

        if task.state == DownloadState.ERROR:
            self._retry_btn.pack(side="left", padx=(4, 0))
        else:
            self._retry_btn.pack_forget()

        if task.state == DownloadState.COMPLETED and task.output_path:
            self._folder_btn.pack(side="left", padx=(4, 0))
        else:
            self._folder_btn.pack_forget()

        if task.state == DownloadState.ERROR and task.error:
            self._state_lbl.configure(text=f"{t('state_error')}: {task.error[:80]}")

    def _move_up(self) -> None:
        if self._on_move:
            self._on_move(self.task.task_id, -1)

    def _move_down(self) -> None:
        if self._on_move:
            self._on_move(self.task.task_id, 1)

    def _toggle_pause(self) -> None:
        if self.task.state == DownloadState.PAUSED:
            downloader.resume_download(self.task.task_id)
        else:
            downloader.pause_download(self.task.task_id)

    def _retry(self) -> None:
        if self.task.state != DownloadState.ERROR or not self.task.url:
            return
        downloader.start_download(self.task.url, self.task.prefs)

    def _delete(self) -> None:
        self._on_delete(self.task.task_id)

    def _open_folder(self) -> None:
        path = self.task.output_path or settings.get("output_dir")
        folder = os.path.dirname(path) if os.path.isfile(path) else path
        if not os.path.exists(folder):
            folder = settings.get("output_dir")

        if sys.platform == "win32":
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.run(["open", folder])
        else:
            subprocess.run(["xdg-open", folder])


# ──────────────────────────────────────────────
# Main Download Page
# ──────────────────────────────────────────────


class DownloadPage(tk.Frame):
    def __init__(self, parent: tk.Widget, nav_callback: Callable) -> None:
        super().__init__(parent, bg=P["bg_0"])
        self._nav = nav_callback
        self._task_cards: dict[str, DownloadCard] = {}
        self._prefs = self._load_prefs()

        downloader.on_task_updated = self._on_task_updated
        downloader.on_queue_status_changed = self._on_queue_status_changed
        add_language_listener(self._retranslate)

        self._build()

    def destroy(self) -> None:
        remove_language_listener(self._retranslate)
        super().destroy()

    def _load_prefs(self) -> DownloadPreferences:
        s = settings
        return DownloadPreferences(
            extract_audio=s.get("extract_audio"),
            audio_format=s.get("audio_format"),
            video_quality=s.get("video_quality"),
            video_container=s.get("video_container", "mp4"),
            video_codec=s.get("video_codec", "h264"),
            embed_metadata=s.get("embed_metadata"),
            embed_thumbnail=s.get("embed_thumbnail"),
            embed_subtitles=s.get("embed_subtitles"),
            subtitle_source=s.get("subtitle_source", "manual"),
            subtitle_languages=s.get("subtitle_languages"),
            output_dir=s.get("output_dir"),
            output_template=s.get("output_template"),
            playlist_subdir=s.get("playlist_subdir"),
            restrict_filenames=s.get("restrict_filenames"),
            proxy=s.get("proxy"),
            rate_limit=s.get("rate_limit"),
            concurrent_fragments=s.get("concurrent_fragments"),
            use_aria2c=s.get("use_aria2c"),
            cookies_file=s.get("cookies_file"),
        )

    def _build(self) -> None:
        # ── FFmpeg warning banner (if missing) ───────
        self._banner_frame = tk.Frame(self, bg=P["bg_2"], padx=SPACING["md"], pady=SPACING["sm"])
        if not is_ffmpeg_available():
            self._render_ffmpeg_banner()

        # ── Top input area ──────────────────────────
        self._input_area = tk.Frame(self, bg=P["bg_1"], padx=SPACING["lg"], pady=SPACING["md"])
        self._input_area.pack(fill="x", padx=SPACING["lg"], pady=(SPACING["md"], 0))

        self._header_lbl = SealLabel(
            self._input_area, t("page_download_title"), style="heading2", bg=P["bg_1"]
        )
        self._header_lbl.pack(anchor="w", pady=(0, SPACING["sm"]))

        # URL row
        url_row = tk.Frame(self._input_area, bg=P["bg_1"])
        url_row.pack(fill="x")

        self._url_entry = SealEntry(
            url_row,
            placeholder=t("url_placeholder"),
        )
        self._url_entry.pack(side="left", fill="x", expand=True)
        self._url_entry.bind_entry("<Return>", lambda _: self._queue_item())

        # Buttons: Add to Queue and Download Now
        self._add_queue_btn = SealButton(
            url_row,
            text=t("btn_add_queue"),
            icon="➕",
            variant="secondary",
            command=self._queue_item,
            height=40,
        )
        self._add_queue_btn.pack(side="left", padx=(SPACING["sm"], 0))

        self._dl_btn = SealButton(
            url_row,
            text=t("btn_download_now"),
            icon="⬇",
            variant="primary",
            command=self._download_now,
            height=40,
        )
        self._dl_btn.pack(side="left", padx=(SPACING["sm"], 0))

        # ── Quick options row ────────────────────────
        opts_row = tk.Frame(self._input_area, bg=P["bg_1"])
        opts_row.pack(fill="x", pady=(SPACING["sm"], 0))

        self._audio_var = tk.BooleanVar(value=settings.get("extract_audio"))
        self._audio_lbl = SealLabel(
            opts_row, t("audio_only"), style="body", color="text_secondary", bg=P["bg_1"]
        )
        self._audio_lbl.pack(side="left", padx=(0, SPACING["xs"]))

        self._audio_sw = SealSwitch(
            opts_row, variable=self._audio_var, command=self._on_audio_toggle
        )
        self._audio_sw.pack(side="left")

        # Quality dropdown
        self._quality_lbl = SealLabel(
            opts_row, t("video_quality"), style="body", color="text_secondary", bg=P["bg_1"]
        )
        self._quality_lbl.pack(side="left", padx=(SPACING["md"], SPACING["xs"]))

        self._quality_var = tk.StringVar(value=settings.get("video_quality"))
        quality_opts = ["best", "2160", "1440", "1080", "720", "480", "360"]
        self._q_menu = tk.OptionMenu(opts_row, self._quality_var, *quality_opts)
        self._style_menu(self._q_menu)
        self._q_menu.pack(side="left")

        # Codec dropdown (avoids unsupported formats like av01)
        self._codec_lbl = SealLabel(
            opts_row, t("video_codec"), style="body", color="text_secondary", bg=P["bg_1"]
        )
        self._codec_lbl.pack(side="left", padx=(SPACING["md"], SPACING["xs"]))

        self._codec_var = tk.StringVar(value=settings.get("video_codec", "h264"))
        codec_opts = ["h264", "auto", "vp9", "av1"]
        self._c_menu = tk.OptionMenu(opts_row, self._codec_var, *codec_opts)
        self._style_menu(self._c_menu)
        self._c_menu.pack(side="left")

        # Audio format dropdown
        self._format_lbl = SealLabel(
            opts_row, t("audio_format"), style="body", color="text_secondary", bg=P["bg_1"]
        )
        self._format_lbl.pack(side="left", padx=(SPACING["md"], SPACING["xs"]))

        self._audio_fmt_var = tk.StringVar(value=settings.get("audio_format"))
        audio_fmts = ["mp3", "m4a", "opus", "flac", "wav", "best"]
        self._af_menu = tk.OptionMenu(opts_row, self._audio_fmt_var, *audio_fmts)
        self._style_menu(self._af_menu)
        self._af_menu.pack(side="left")

        # Output folder picker
        self._out_btn = SealButton(
            opts_row,
            text=f"📁  {t('output_folder')}",
            variant="secondary",
            command=self._pick_output_dir,
            height=32,
        )
        self._out_btn.pack(side="right")

        self._out_lbl = tk.Label(
            opts_row,
            text=self._short_path(settings.get("output_dir")),
            bg=P["bg_1"],
            fg=P["text_secondary"],
            font=FONTS["body_sm"],
        )
        self._out_lbl.pack(side="right", padx=(0, SPACING["sm"]))

        # ── Subtitle options row ─────────────────────
        sub_row = tk.Frame(self._input_area, bg=P["bg_1"])
        sub_row.pack(fill="x", pady=(SPACING["xs"], 0))

        self._sub_src_lbl = SealLabel(
            sub_row, t("sub_source_label"), style="body", color="text_secondary", bg=P["bg_1"]
        )
        self._sub_src_lbl.pack(side="left", padx=(0, SPACING["xs"]))

        self._sub_src_var = tk.StringVar(value=settings.get("subtitle_source", "manual"))
        _sub_src_display = {
            "manual": t("sub_source_manual"),
            "auto": t("sub_source_auto"),
            "both": t("sub_source_both"),
        }
        _sub_src_opts = ["manual", "auto", "both"]
        self._sub_src_menu = tk.OptionMenu(
            sub_row,
            self._sub_src_var,
            *_sub_src_opts,
        )
        self._sub_src_menu["menu"].delete(0, "end")
        for val in _sub_src_opts:
            self._sub_src_menu["menu"].add_command(
                label=t(f"sub_source_{val}"),
                command=lambda v=val: self._sub_src_var.set(v),
            )
        self._style_menu(self._sub_src_menu)
        self._sub_src_menu.pack(side="left")

        # Subtitle languages inline hint
        self._sub_lang_hint_lbl = SealLabel(
            sub_row,
            f"🌐 {t('label_sub_languages')}: {settings.get('subtitle_languages', 'en')}",
            style="body_sm",
            color="text_tertiary",
            bg=P["bg_1"],
        )
        self._sub_lang_hint_lbl.pack(side="left", padx=(SPACING["md"], 0))

        # Format picker & Playlist picker buttons
        self._pick_fmt_btn = SealButton(
            sub_row,
            text=f"🎯 {t('btn_pick_format')}",
            variant="secondary",
            command=self._open_format_picker,
            height=28,
        )
        self._pick_fmt_btn.pack(side="right", padx=(SPACING["xs"], 0))

        self._pick_pl_btn = SealButton(
            sub_row,
            text=f"📑 {t('btn_select_items')}",
            variant="secondary",
            command=self._open_playlist_picker,
            height=28,
        )
        self._pick_pl_btn.pack(side="right", padx=(SPACING["xs"], 0))

        # ── Queue Controls Bar ──────────────────────
        controls_bar = tk.Frame(self, bg=P["bg_0"])
        controls_bar.pack(fill="x", padx=SPACING["lg"], pady=(SPACING["md"], 0))

        self._list_title = SealLabel(
            controls_bar,
            t("downloads_header"),
            style="heading3",
            color="text_secondary",
            bg=P["bg_0"],
        )
        self._list_title.pack(side="left")

        self._queue_info_lbl = tk.Label(
            controls_bar,
            text="",
            bg=P["bg_0"],
            fg=P["accent_light"],
            font=FONTS["body_sm"],
        )
        self._queue_info_lbl.pack(side="left", padx=(SPACING["md"], 0))

        self._clear_btn = SealButton(
            controls_bar,
            text=t("btn_clear_done"),
            variant="ghost",
            command=self._clear_done,
            height=28,
        )
        self._clear_btn.pack(side="right")

        self._queue_toggle_btn = SealButton(
            controls_bar,
            text=t("btn_start_queue"),
            variant="secondary",
            command=self._toggle_queue,
            height=28,
        )
        self._queue_toggle_btn.pack(side="right", padx=(0, SPACING["sm"]))

        # ── Downloads scroll list area ──────────────
        self._scroll = SealScrollFrame(self)
        self._scroll.pack(fill="both", expand=True, padx=SPACING["lg"], pady=SPACING["sm"])

        self._empty_lbl = tk.Label(
            self._scroll.inner,
            text=t("empty_downloads"),
            bg=P["bg_0"],
            fg=P["text_tertiary"],
            font=FONTS["body"],
            justify="center",
        )
        self._empty_lbl.pack(expand=True, pady=60)

        # Populate any existing tasks
        for task in downloader.get_tasks():
            self._create_card(task)
        self._update_queue_label()

    def _render_ffmpeg_banner(self) -> None:
        self._banner_frame.pack(fill="x", padx=SPACING["lg"], pady=(SPACING["sm"], 0))
        for w in self._banner_frame.winfo_children():
            w.destroy()

        b_left = tk.Frame(self._banner_frame, bg=P["bg_2"])
        b_left.pack(side="left", fill="x", expand=True)

        tk.Label(
            b_left,
            text=t("ffmpeg_banner_title"),
            bg=P["bg_2"],
            fg=P["warning"],
            font=FONTS["heading3"],
            anchor="w",
        ).pack(fill="x")

        tk.Label(
            b_left,
            text=t("ffmpeg_banner_desc"),
            bg=P["bg_2"],
            fg=P["text_secondary"],
            font=FONTS["body_sm"],
            anchor="w",
        ).pack(fill="x")

        self._install_ffmpeg_btn = SealButton(
            self._banner_frame,
            text=t("btn_install_ffmpeg_quick"),
            variant="primary",
            command=self._install_ffmpeg_quick,
            height=30,
        )
        self._install_ffmpeg_btn.pack(side="right", padx=(SPACING["sm"], 0))

    def _install_ffmpeg_quick(self) -> None:
        self._install_ffmpeg_btn.configure_text(t("status_installing"))

        def on_prog(_pct: float, msg: str) -> None:
            self.after(0, lambda: self._install_ffmpeg_btn.configure_text(msg[:20]))

        def on_done(success: bool, msg: str) -> None:
            def _apply() -> None:
                if success:
                    self._banner_frame.pack_forget()
                    messagebox.showinfo(
                        "FFmpeg",
                        t("ffmpeg_installed_success"),
                    )
                else:
                    self._install_ffmpeg_btn.configure_text(t("btn_install_ffmpeg_quick"))
                    messagebox.showwarning("FFmpeg", msg)

            self.after(0, _apply)

        download_ffmpeg_async(on_prog, on_done)

    def _style_menu(self, menu: tk.OptionMenu) -> None:
        menu.configure(
            bg=P["bg_2"],
            fg=P["text_primary"],
            activebackground=P["bg_3"],
            activeforeground=P["text_primary"],
            highlightthickness=0,
            relief="flat",
            font=FONTS["body"],
            bd=0,
        )
        menu["menu"].configure(
            bg=P["bg_2"],
            fg=P["text_primary"],
            activebackground=P["accent"],
            activeforeground="white",
            font=FONTS["body"],
            bd=0,
        )

    # ── Actions ───────────────────────────────

    def _collect_current_prefs(self) -> DownloadPreferences:
        prefs = self._load_prefs()
        prefs.extract_audio = self._audio_var.get()
        prefs.audio_format = self._audio_fmt_var.get()
        prefs.video_quality = self._quality_var.get()
        prefs.video_codec = self._codec_var.get()
        prefs.subtitle_source = self._sub_src_var.get()
        return prefs

    # Accepts any syntactically valid HTTP(S) URL — platform validation is
    # delegated to yt-dlp which natively supports 1000+ sites.
    _URL_RE = re.compile(r"^https?://[^\s/$.?#][^\s]*$", re.IGNORECASE)

    def _validate_url(self, url: str) -> bool:
        """Return True if url looks like a valid HTTP(S) link, show warning otherwise."""
        if self._URL_RE.match(url):
            return True
        messagebox.showwarning(
            t("invalid_url_title"),
            t("invalid_url_msg"),
        )
        return False

    def _queue_item(self) -> None:
        """Add link to the staged queue without immediately starting it."""
        url = self._url_entry.get().strip()
        if not url:
            return
        if not self._validate_url(url):
            return

        prefs = self._collect_current_prefs()
        self._url_entry.clear()
        task_id = downloader.queue_download(url, prefs)

        t_obj = next((x for x in downloader.get_tasks() if x.task_id == task_id), None)
        if t_obj:
            self._create_card(t_obj)
        self._update_queue_label()

    def _download_now(self) -> None:
        """Add link and immediately start sequential queue execution."""
        url = self._url_entry.get().strip()
        if not url:
            return
        if not self._validate_url(url):
            return

        prefs = self._collect_current_prefs()
        self._url_entry.clear()
        task_id = downloader.start_download(url, prefs)

        t_obj = next((x for x in downloader.get_tasks() if x.task_id == task_id), None)
        if t_obj:
            self._create_card(t_obj)
        self._update_queue_label()

    def _toggle_queue(self) -> None:
        if downloader.is_queue_running():
            downloader.pause_queue()
        else:
            downloader.start_queue()
        self._update_queue_label()

    def _on_queue_status_changed(self, running: bool) -> None:
        self.after(0, lambda: self._update_queue_label(running))

    def _update_queue_label(self, running: bool | None = None) -> None:
        if running is None:
            running = downloader.is_queue_running()

        btn_txt = t("btn_pause_queue") if running else t("btn_start_queue")
        self._queue_toggle_btn.configure_text(btn_txt)

        tasks = downloader.get_tasks()
        q_count = sum(1 for t_item in tasks if t_item.state == DownloadState.QUEUED)
        active_count = sum(
            1
            for t_item in tasks
            if t_item.state
            in (
                DownloadState.DOWNLOADING,
                DownloadState.DOWNLOADING_PLAYLIST,
                DownloadState.FETCHING_INFO,
            )
        )
        if q_count or active_count:
            self._queue_info_lbl.configure(
                text=t("queue_summary", count=q_count, active=active_count)
            )
        else:
            self._queue_info_lbl.configure(text="")

    def _on_task_updated(self, task: DownloadTask) -> None:
        self.after(0, self._refresh_card, task)

    def _refresh_card(self, task: DownloadTask) -> None:
        if task.task_id in self._task_cards:
            self._task_cards[task.task_id].refresh(task)
        else:
            self._create_card(task)

        if task.state == DownloadState.COMPLETED:
            settings.add_history(
                {
                    "url": task.url,
                    "title": task.title,
                    "output": task.output_path,
                    "is_audio": task.is_audio,
                }
            )
            if settings.get("desktop_notifications", True):
                send_notification(
                    t("notify_completed_title"),
                    t("notify_completed_msg", title=(task.title or "Download")[:60]),
                )
        elif task.state == DownloadState.ERROR:
            if settings.get("desktop_notifications", True):
                send_notification(
                    t("notify_error_title"),
                    t(
                        "notify_error_msg",
                        title=(task.title or "Download")[:40],
                        error=(task.error or "")[:60],
                    ),
                )
            if task.error:
                # Detect unsupported-site / no-extractor errors from yt-dlp and
                # surface a friendly dialog instead of the raw exception string.
                _err_lower = task.error.lower()
                if (
                    "no suitable" in _err_lower
                    or "unsupported url" in _err_lower
                    or "unable to extract" in _err_lower
                    or "ie_key" in _err_lower
                ):
                    messagebox.showwarning(
                        t("unsupported_site_title"),
                        t("unsupported_site_msg"),
                    )
        self._update_queue_label()

    def _create_card(self, task: DownloadTask) -> None:
        if task.task_id in self._task_cards:
            self._task_cards[task.task_id].refresh(task)
            return

        self._empty_lbl.pack_forget()
        card = DownloadCard(
            self._scroll.inner,
            task,
            on_delete=self._delete_task,
            on_move=self._move_task,
        )
        card.pack(fill="x", pady=(0, SPACING["sm"]))
        self._task_cards[task.task_id] = card

    def _move_task(self, task_id: str, direction: int) -> None:
        if downloader.reorder_queue(task_id, direction):
            with downloader._lock:
                q_order = list(downloader._queue)
            for tid in q_order:
                if tid in self._task_cards:
                    card = self._task_cards[tid]
                    card.pack_forget()
                    card.pack(fill="x", pady=(0, SPACING["sm"]))

    def _delete_task(self, task_id: str) -> None:
        downloader.delete_task(task_id)
        if task_id in self._task_cards:
            self._task_cards[task_id].destroy()
            del self._task_cards[task_id]

        if not self._task_cards:
            self._empty_lbl.pack(expand=True, pady=60)
        self._update_queue_label()

    def _clear_done(self) -> None:
        downloader.clear_completed()
        done = [
            k
            for k, c in self._task_cards.items()
            if c.task.state
            in (DownloadState.COMPLETED, DownloadState.CANCELLED, DownloadState.ERROR)
        ]
        for k in done:
            self._task_cards[k].destroy()
            del self._task_cards[k]

        if not self._task_cards:
            self._empty_lbl.pack(expand=True, pady=60)
        self._update_queue_label()

    def _on_audio_toggle(self, value: bool) -> None:
        settings.set("extract_audio", value)

    def _pick_output_dir(self) -> None:
        d = filedialog.askdirectory(initialdir=settings.get("output_dir"))
        if d:
            settings.set("output_dir", d)
            self._out_lbl.configure(text=self._short_path(d))

    def set_url(self, url: str) -> None:
        """Populate the URL entry field and focus it."""
        self._url_entry.set(url)
        self._url_entry.focus()

    def _open_format_picker(self) -> None:
        url = self._url_entry.get().strip()
        if not url:
            return
        if not self._validate_url(url):
            return

        self._pick_fmt_btn.configure_text(f"⏳ {t('status_checking')}")

        def fetch() -> None:
            try:
                import yt_dlp

                ydl_opts = {
                    "skip_download": True,
                    "quiet": True,
                    "no_warnings": True,
                    "logger": YtDlpLogger(),
                }
                if settings.get("proxy"):
                    ydl_opts["proxy"] = settings.get("proxy")
                if settings.get("cookies_file"):
                    ydl_opts["cookiefile"] = settings.get("cookies_file")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                self.after(0, lambda: self._show_format_modal(url, info))
            except Exception as exc:  # noqa: BLE001
                err_msg = str(exc)[:250]
                self.after(
                    0, lambda msg=err_msg: messagebox.showerror(t("format_picker_title"), msg)
                )
            finally:
                self.after(
                    0, lambda: self._pick_fmt_btn.configure_text(f"🎯 {t('btn_pick_format')}")
                )

        threading.Thread(target=fetch, daemon=True, name="seal-fetch-fmt").start()

    def _show_format_modal(self, url: str, info: dict) -> None:
        formats = info.get("formats", [])
        if not formats:
            messagebox.showinfo(t("format_picker_title"), "No separate formats found.")
            return

        dlg = tk.Toplevel(self)
        dlg.title(t("format_picker_title"))
        dlg.geometry("560x480")
        dlg.configure(bg=P["bg_1"])
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        pad = SPACING["md"]
        tk.Label(
            dlg,
            text=f"🎯  {t('format_picker_title')}",
            bg=P["bg_1"],
            fg=P["accent"],
            font=FONTS["heading2"],
        ).pack(anchor="w", padx=pad, pady=(pad, 4))

        title_str = (info.get("title") or url)[:70]
        tk.Label(
            dlg,
            text=title_str,
            bg=P["bg_1"],
            fg=P["text_primary"],
            font=FONTS["body"],
        ).pack(anchor="w", padx=pad, pady=(0, pad))

        scroll = SealScrollFrame(dlg)
        scroll.pack(fill="both", expand=True, padx=pad, pady=(0, pad))

        selected_fmt_id = tk.StringVar()
        seen = set()

        for f in formats:
            fid = f.get("format_id", "")
            ext = f.get("ext", "")
            vcodec = f.get("vcodec", "none")
            acodec = f.get("acodec", "none")
            height = f.get("height")
            fps = f.get("fps")
            note = f.get("format_note", "")

            if vcodec == "none" and acodec == "none":
                continue

            is_video = vcodec != "none"
            if is_video:
                desc = f"🎬 {height}p" if height else f"🎬 {note or ext}"
                if fps:
                    desc += f" {fps}fps"
                desc += f" ({ext}, {vcodec[:8]})"
            else:
                desc = f"🎵 Audio only ({ext}, {acodec[:8]})"

            key = (is_video, height, ext)
            if key in seen:
                continue
            seen.add(key)

            if not selected_fmt_id.get():
                selected_fmt_id.set(fid)

            row = tk.Frame(scroll.inner, bg=P["bg_2"], pady=4, padx=8)
            row.pack(fill="x", pady=2)

            rb = tk.Radiobutton(
                row,
                text=desc,
                value=fid,
                variable=selected_fmt_id,
                bg=P["bg_2"],
                fg=P["text_primary"],
                selectcolor=P["bg_3"],
                activebackground=P["bg_2"],
                activeforeground=P["accent_light"],
                font=FONTS["body_sm"],
                anchor="w",
            )
            rb.pack(side="left", fill="x", expand=True)

        btn_row = tk.Frame(dlg, bg=P["bg_1"])
        btn_row.pack(fill="x", padx=pad, pady=(0, pad))

        def _apply_choice() -> None:
            chosen_id = selected_fmt_id.get()
            chosen_fmt = next((f for f in formats if f.get("format_id") == chosen_id), None)
            if chosen_fmt:
                if chosen_fmt.get("vcodec") == "none":
                    self._audio_var.set(True)
                    self._audio_fmt_var.set(chosen_fmt.get("ext", "mp3"))
                else:
                    self._audio_var.set(False)
                    h = chosen_fmt.get("height")
                    if h:
                        h_str = str(h)
                        if h_str in ("2160", "1440", "1080", "720", "480", "360"):
                            self._quality_var.set(h_str)
            dlg.destroy()

        SealButton(
            btn_row,
            text=t("btn_pick_format"),
            variant="primary",
            command=_apply_choice,
            height=32,
        ).pack(side="left")

        SealButton(
            btn_row,
            text=t("btn_close"),
            variant="ghost",
            command=dlg.destroy,
            height=32,
        ).pack(side="right")

    def _open_playlist_picker(self) -> None:
        url = self._url_entry.get().strip()
        if not url:
            return
        if not self._validate_url(url):
            return

        self._pick_pl_btn.configure_text(f"⏳ {t('status_checking')}")

        def fetch() -> None:
            try:
                import yt_dlp

                ydl_opts = {
                    "extract_flat": "in_playlist",
                    "skip_download": True,
                    "quiet": True,
                    "no_warnings": True,
                    "logger": YtDlpLogger(),
                }
                if settings.get("proxy"):
                    ydl_opts["proxy"] = settings.get("proxy")
                if settings.get("cookies_file"):
                    ydl_opts["cookiefile"] = settings.get("cookies_file")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                self.after(0, lambda: self._show_playlist_modal(info))
            except Exception as exc:  # noqa: BLE001
                err_msg = str(exc)[:250]
                self.after(
                    0, lambda msg=err_msg: messagebox.showerror(t("playlist_picker_title"), msg)
                )
            finally:
                self.after(
                    0, lambda: self._pick_pl_btn.configure_text(f"📑 {t('btn_select_items')}")
                )

        threading.Thread(target=fetch, daemon=True, name="seal-fetch-pl").start()

    def _show_playlist_modal(self, info: dict) -> None:
        raw_entries = list(info.get("entries") or [])
        if not raw_entries:
            messagebox.showinfo(t("playlist_picker_title"), "No playlist items found.")
            return

        dlg = tk.Toplevel(self)
        dlg.title(t("playlist_picker_title"))
        dlg.geometry("640x540")
        dlg.configure(bg=P["bg_1"])
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        pad = SPACING["md"]
        tk.Label(
            dlg,
            text=f"📑  {t('playlist_picker_title')}",
            bg=P["bg_1"],
            fg=P["accent"],
            font=FONTS["heading2"],
        ).pack(anchor="w", padx=pad, pady=(pad, 4))

        pl_title = info.get("title") or "Playlist"
        tk.Label(
            dlg,
            text=f"{pl_title} ({len(raw_entries)} items)",
            bg=P["bg_1"],
            fg=P["text_secondary"],
            font=FONTS["body"],
        ).pack(anchor="w", padx=pad, pady=(0, pad))

        tool_row = tk.Frame(dlg, bg=P["bg_1"])
        tool_row.pack(fill="x", padx=pad, pady=(0, SPACING["xs"]))

        item_vars: list[tuple[dict, tk.BooleanVar]] = []

        def _select_all() -> None:
            for _, v in item_vars:
                v.set(True)

        def _deselect_all() -> None:
            for _, v in item_vars:
                v.set(False)

        SealButton(
            tool_row, text=t("ctx_select_all"), variant="ghost", command=_select_all, height=26
        ).pack(side="left")
        SealButton(
            tool_row, text="Deselect All", variant="ghost", command=_deselect_all, height=26
        ).pack(side="left", padx=(SPACING["sm"], 0))

        scroll = SealScrollFrame(dlg)
        scroll.pack(fill="both", expand=True, padx=pad, pady=(0, pad))

        for idx, entry in enumerate(raw_entries, 1):
            if not entry:
                continue
            e_title = entry.get("title") or entry.get("id") or f"Item {idx}"
            dur = entry.get("duration")
            dur_str = f" ({int(dur // 60)}:{int(dur % 60):02d})" if dur else ""

            var = tk.BooleanVar(value=True)
            item_vars.append((entry, var))

            row = tk.Frame(scroll.inner, bg=P["bg_2"], pady=3, padx=6)
            row.pack(fill="x", pady=1)

            cb = tk.Checkbutton(
                row,
                text=f"{idx}. {e_title[:65]}{dur_str}",
                variable=var,
                bg=P["bg_2"],
                fg=P["text_primary"],
                selectcolor=P["bg_3"],
                activebackground=P["bg_2"],
                activeforeground=P["accent_light"],
                font=FONTS["body_sm"],
                anchor="w",
            )
            cb.pack(side="left", fill="x", expand=True)

        btn_row = tk.Frame(dlg, bg=P["bg_1"])
        btn_row.pack(fill="x", padx=pad, pady=(0, pad))

        def _queue_selected() -> None:
            prefs = self._collect_current_prefs()
            queued_any = False
            for entry, var in item_vars:
                if var.get():
                    e_url = entry.get("url") or entry.get("webpage_url") or entry.get("id")
                    if e_url:
                        if not e_url.startswith("http"):
                            e_url = f"https://www.youtube.com/watch?v={e_url}"
                        task_id = downloader.queue_download(e_url, prefs)
                        t_obj = next(
                            (x for x in downloader.get_tasks() if x.task_id == task_id), None
                        )
                        if t_obj:
                            self._create_card(t_obj)
                        queued_any = True
            if queued_any:
                downloader.start_queue()
                self._update_queue_label()
            dlg.destroy()

        SealButton(
            btn_row,
            text=t("btn_download_selected"),
            variant="primary",
            command=_queue_selected,
            height=32,
        ).pack(side="left")

        SealButton(
            btn_row,
            text=t("btn_close"),
            variant="ghost",
            command=dlg.destroy,
            height=32,
        ).pack(side="right")

    def _retranslate(self) -> None:
        """Update texts in this page when language changes."""
        self._header_lbl.configure_text(t("page_download_title"))
        self._add_queue_btn.configure_text(t("btn_add_queue"))
        self._dl_btn.configure_text(t("btn_download_now"))
        self._audio_lbl.configure_text(t("audio_only"))
        self._quality_lbl.configure_text(t("video_quality"))
        self._codec_lbl.configure_text(t("video_codec"))
        self._format_lbl.configure_text(t("audio_format"))
        self._out_btn.configure_text(f"📁  {t('output_folder')}")
        self._list_title.configure_text(t("downloads_header"))
        self._clear_btn.configure_text(t("btn_clear_done"))
        self._empty_lbl.configure(text=t("empty_downloads"))
        self._url_entry.update_placeholder(t("url_placeholder"))
        self._sub_src_lbl.configure_text(t("sub_source_label"))
        self._pick_fmt_btn.configure_text(f"🎯 {t('btn_pick_format')}")
        self._pick_pl_btn.configure_text(f"📑 {t('btn_select_items')}")
        # Rebuild sub-source menu labels for current language
        self._sub_src_menu["menu"].delete(0, "end")
        for val in ("manual", "auto", "both"):
            self._sub_src_menu["menu"].add_command(
                label=t(f"sub_source_{val}"),
                command=lambda v=val: self._sub_src_var.set(v),
            )
        self._sub_lang_hint_lbl.configure(
            text=f"🌐 {t('label_sub_languages')}: {settings.get('subtitle_languages', 'en')}"
        )
        self._update_queue_label()

        for card in self._task_cards.values():
            card.refresh(card.task)

    @staticmethod
    def _short_path(p: str) -> str:
        path = Path(p)
        home = Path.home()
        try:
            rel = path.relative_to(home)
            return "~/" + str(rel)
        except ValueError:
            return str(path)[-40:]
