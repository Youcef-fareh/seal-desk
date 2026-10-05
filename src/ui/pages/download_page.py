"""
Seal Desktop – Download Page
The main download UI: URL input, format selection, progress cards.
"""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable, Optional

from ..core.downloader import DownloadPreferences, DownloadState, DownloadTask, downloader
from ..core.settings import settings
from .theme import FONTS, PALETTE as P, SPACING
from .widgets import (
    SealButton,
    SealCard,
    SealEntry,
    SealLabel,
    SealProgressBar,
    SealScrollFrame,
    SealSwitch,
)


# ──────────────────────────────────────────────
# Download card (one per active download)
# ──────────────────────────────────────────────


class DownloadCard(SealCard):
    def __init__(self, parent: tk.Widget, task: DownloadTask) -> None:
        super().__init__(parent)
        self.task = task
        self._build()

    def _build(self) -> None:
        pad = SPACING["md"]
        self.configure(padx=pad, pady=pad)

        # Row 1: title + cancel
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

        self._cancel_btn = SealButton(
            row1, text="✕", variant="ghost", command=self._cancel, width=32, height=28
        )
        self._cancel_btn.pack(side="right", padx=(8, 0))

        # Row 2: status + stats
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

        # Row 3: progress bar
        self._pbar = SealProgressBar(self, height=6)
        self._pbar.pack(fill="x", pady=(8, 4))

        # Row 4: url
        self._url_lbl = tk.Label(
            self,
            text=self.task.url[:80] + ("…" if len(self.task.url) > 80 else ""),
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
            DownloadState.IDLE: ("⏸  Idle", P["text_secondary"]),
            DownloadState.FETCHING_INFO: ("🔍  Fetching info…", P["info"]),
            DownloadState.DOWNLOADING: ("⬇  Downloading", P["accent"]),
            DownloadState.DOWNLOADING_PLAYLIST: (
                f"⬇  Playlist {task.playlist_index}/{task.playlist_count}", P["accent"]
            ),
            DownloadState.CONVERTING: ("⚙  Processing…", P["warning"]),
            DownloadState.COMPLETED: ("✅  Completed", P["success"]),
            DownloadState.CANCELLED: ("🚫  Cancelled", P["text_secondary"]),
            DownloadState.ERROR: ("❌  Error", P["error"]),
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

        if task.state in (DownloadState.COMPLETED, DownloadState.CANCELLED, DownloadState.ERROR):
            self._cancel_btn.configure_text("🗑")

        if task.state == DownloadState.ERROR and task.error:
            self._state_lbl.configure(text=f"❌  {task.error[:80]}")

    def _cancel(self) -> None:
        if self.task.state in (
            DownloadState.COMPLETED, DownloadState.CANCELLED, DownloadState.ERROR
        ):
            self.destroy()
        else:
            downloader.cancel_download(self.task.task_id)


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

        self._build()

    def _load_prefs(self) -> DownloadPreferences:
        s = settings
        return DownloadPreferences(
            extract_audio=s.get("extract_audio"),
            audio_format=s.get("audio_format"),
            video_quality=s.get("video_quality"),
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
        # ── Top input area ──────────────────────────
        input_area = tk.Frame(self, bg=P["bg_1"], padx=SPACING["lg"], pady=SPACING["md"])
        input_area.pack(fill="x", padx=SPACING["lg"], pady=(SPACING["lg"], 0))

        header = SealLabel(
            input_area, "Download", style="heading2", bg=P["bg_1"]
        )
        header.pack(anchor="w", pady=(0, SPACING["sm"]))

        # URL row
        url_row = tk.Frame(input_area, bg=P["bg_1"])
        url_row.pack(fill="x")

        self._url_entry = SealEntry(
            url_row,
            placeholder="Paste a YouTube, SoundCloud, or any supported URL…",
        )
        self._url_entry.pack(side="left", fill="x", expand=True)
        self._url_entry.bind_entry("<Return>", lambda _: self._start())

        self._dl_btn = SealButton(
            url_row,
            text="Download",
            icon="⬇",
            variant="primary",
            command=self._start,
            height=40,
        )
        self._dl_btn.pack(side="left", padx=(SPACING["sm"], 0))

        # ── Quick options row ────────────────────────
        opts_row = tk.Frame(input_area, bg=P["bg_1"])
        opts_row.pack(fill="x", pady=(SPACING["sm"], 0))

        self._audio_var = tk.BooleanVar(value=settings.get("extract_audio"))
        SealLabel(opts_row, "Audio only", style="body", color="text_secondary", bg=P["bg_1"]).pack(
            side="left", padx=(0, SPACING["xs"])
        )
        SealSwitch(opts_row, variable=self._audio_var, command=self._on_audio_toggle).pack(
            side="left"
        )

        # Quality dropdown
        SealLabel(opts_row, "Quality:", style="body", color="text_secondary", bg=P["bg_1"]).pack(
            side="left", padx=(SPACING["md"], SPACING["xs"])
        )
        self._quality_var = tk.StringVar(value=settings.get("video_quality"))
        quality_opts = ["best", "2160", "1440", "1080", "720", "480", "360"]
        q_menu = tk.OptionMenu(opts_row, self._quality_var, *quality_opts)
        q_menu.configure(
            bg=P["bg_2"],
            fg=P["text_primary"],
            activebackground=P["bg_3"],
            activeforeground=P["text_primary"],
            highlightthickness=0,
            relief="flat",
            font=FONTS["body"],
            bd=0,
        )
        q_menu["menu"].configure(
            bg=P["bg_2"],
            fg=P["text_primary"],
            activebackground=P["accent"],
            activeforeground="white",
            font=FONTS["body"],
            bd=0,
        )
        q_menu.pack(side="left")

        # Audio format dropdown (shown when audio only)
        SealLabel(opts_row, "Format:", style="body", color="text_secondary", bg=P["bg_1"]).pack(
            side="left", padx=(SPACING["md"], SPACING["xs"])
        )
        self._audio_fmt_var = tk.StringVar(value=settings.get("audio_format"))
        audio_fmts = ["mp3", "m4a", "opus", "flac", "wav", "best"]
        af_menu = tk.OptionMenu(opts_row, self._audio_fmt_var, *audio_fmts)
        af_menu.configure(
            bg=P["bg_2"],
            fg=P["text_primary"],
            activebackground=P["bg_3"],
            activeforeground=P["text_primary"],
            highlightthickness=0,
            relief="flat",
            font=FONTS["body"],
            bd=0,
        )
        af_menu["menu"].configure(
            bg=P["bg_2"],
            fg=P["text_primary"],
            activebackground=P["accent"],
            activeforeground="white",
            font=FONTS["body"],
            bd=0,
        )
        af_menu.pack(side="left")

        # Output dir
        out_btn = SealButton(
            opts_row,
            text="📁  Output Folder",
            variant="secondary",
            command=self._pick_output_dir,
            height=32,
        )
        out_btn.pack(side="right")

        self._out_lbl = tk.Label(
            opts_row,
            text=self._short_path(settings.get("output_dir")),
            bg=P["bg_1"],
            fg=P["text_secondary"],
            font=FONTS["body_sm"],
        )
        self._out_lbl.pack(side="right", padx=(0, SPACING["sm"]))

        # ── Downloads list area ──────────────────────
        list_label_row = tk.Frame(self, bg=P["bg_0"])
        list_label_row.pack(fill="x", padx=SPACING["lg"], pady=(SPACING["md"], 0))

        SealLabel(
            list_label_row, "Downloads", style="heading3", color="text_secondary", bg=P["bg_0"]
        ).pack(side="left")

        SealButton(
            list_label_row,
            text="Clear done",
            variant="ghost",
            command=self._clear_done,
            height=28,
        ).pack(side="right")

        self._scroll = SealScrollFrame(self)
        self._scroll.pack(fill="both", expand=True, padx=SPACING["lg"], pady=SPACING["sm"])

        self._empty_lbl = tk.Label(
            self._scroll.inner,
            text="No active downloads.\nPaste a URL above to get started! 🚀",
            bg=P["bg_0"],
            fg=P["text_tertiary"],
            font=FONTS["body"],
            justify="center",
        )
        self._empty_lbl.pack(expand=True, pady=60)

    # ── Actions ───────────────────────────────

    def _start(self) -> None:
        url = self._url_entry.get().strip()
        if not url:
            return

        self._prefs = self._load_prefs()
        self._prefs.extract_audio = self._audio_var.get()
        self._prefs.audio_format = self._audio_fmt_var.get()
        self._prefs.video_quality = self._quality_var.get()

        self._url_entry.clear()
        task_id = downloader.start_download(url, self._prefs)

        # Optimistically create a placeholder card
        from ..core.downloader import DownloadTask, DownloadState
        t = DownloadTask(task_id=task_id, url=url, state=DownloadState.FETCHING_INFO)
        self._create_card(t)

    def _on_task_updated(self, task: DownloadTask) -> None:
        """Called from a worker thread — schedule UI update on main thread."""
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

    def _create_card(self, task: DownloadTask) -> None:
        self._empty_lbl.pack_forget()
        card = DownloadCard(self._scroll.inner, task)
        card.pack(fill="x", pady=(0, SPACING["sm"]))
        self._task_cards[task.task_id] = card

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

    def _on_audio_toggle(self, value: bool) -> None:
        settings.set("extract_audio", value)

    def _pick_output_dir(self) -> None:
        d = filedialog.askdirectory(initialdir=settings.get("output_dir"))
        if d:
            settings.set("output_dir", d)
            self._out_lbl.configure(text=self._short_path(d))

    @staticmethod
    def _short_path(p: str) -> str:
        path = Path(p)
        home = Path.home()
        try:
            rel = path.relative_to(home)
            return "~/" + str(rel)
        except ValueError:
            return str(path)[-40:]
