"""
Seal Desktop – Download Page
Supports multi-link staged queueing, successive execution, pause/resume,
audio-video merger controls, and full Arabic/English bilingual interface.
"""

from __future__ import annotations

import os
import subprocess
import sys
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
    ) -> None:
        super().__init__(parent)
        self.task = task
        self._on_delete = on_delete
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

        # Action buttons frame (Delete, Pause/Resume, Open Folder)
        self._actions_frame = tk.Frame(row1, bg=P["bg_1"])
        self._actions_frame.pack(side="right")

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
        if task.speed:
            stats += f"{task.speed}  "
        if task.size:
            stats += f"{task.size}  "
        if task.eta:
            stats += f"ETA {task.eta}"
        self._stats_lbl.configure(text=stats.strip())

        self._pbar.set_progress(task.progress)

        # Update button states
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

        if task.state == DownloadState.COMPLETED and task.output_path:
            self._folder_btn.pack(side="left", padx=(4, 0))
        else:
            self._folder_btn.pack_forget()

        if task.state == DownloadState.ERROR and task.error:
            self._state_lbl.configure(text=f"{t('state_error')}: {task.error[:80]}")

    def _toggle_pause(self) -> None:
        if self.task.state == DownloadState.PAUSED:
            downloader.resume_download(self.task.task_id)
        else:
            downloader.pause_download(self.task.task_id)

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
            embed_metadata=s.get("embed_metadata"),
            embed_thumbnail=s.get("embed_thumbnail"),
            embed_subtitles=s.get("embed_subtitles"),
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
        self._install_ffmpeg_btn.configure_text("Installing…")

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
        return prefs

    def _queue_item(self) -> None:
        """Add link to the staged queue without immediately starting it."""
        url = self._url_entry.get().strip()
        if not url:
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
        self._update_queue_label()

    def _create_card(self, task: DownloadTask) -> None:
        if task.task_id in self._task_cards:
            self._task_cards[task.task_id].refresh(task)
            return

        self._empty_lbl.pack_forget()
        card = DownloadCard(self._scroll.inner, task, on_delete=self._delete_task)
        card.pack(fill="x", pady=(0, SPACING["sm"]))
        self._task_cards[task.task_id] = card

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

    def _retranslate(self) -> None:
        """Update texts in this page when language changes."""
        self._header_lbl.configure_text(t("page_download_title"))
        self._add_queue_btn.configure_text(t("btn_add_queue"))
        self._dl_btn.configure_text(t("btn_download_now"))
        self._audio_lbl.configure_text(t("audio_only"))
        self._quality_lbl.configure_text(t("video_quality"))
        self._format_lbl.configure_text(t("audio_format"))
        self._out_btn.configure_text(f"📁  {t('output_folder')}")
        self._list_title.configure_text(t("downloads_header"))
        self._clear_btn.configure_text(t("btn_clear_done"))
        self._empty_lbl.configure(text=t("empty_downloads"))
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
