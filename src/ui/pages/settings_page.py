"""
Seal Desktop – Settings Page
Full settings UI for download preferences, network, and UI options.
"""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from typing import Callable

from ...core.settings import settings
from ...core.updater import get_ytdlp_version, update_ytdlp
from ..theme import FONTS, PALETTE as P, SPACING
from ..widgets import SealButton, SealEntry, SealLabel, SealScrollFrame, SealSwitch


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _section(parent: tk.Widget, title: str) -> tk.Frame:
    """Renders a section header + returns a content frame."""
    tk.Label(
        parent,
        text=title.upper(),
        bg=P["bg_0"],
        fg=P["text_tertiary"],
        font=("Segoe UI", 10, "bold"),
        anchor="w",
    ).pack(fill="x", padx=SPACING["lg"], pady=(SPACING["lg"], SPACING["xs"]))

    tk.Frame(parent, bg=P["bg_1"], height=1).pack(fill="x", padx=SPACING["lg"])

    frame = tk.Frame(parent, bg=P["bg_1"], padx=SPACING["lg"], pady=SPACING["md"])
    frame.pack(fill="x", padx=SPACING["lg"])
    return frame


def _row(parent: tk.Frame, label: str) -> tuple[tk.Frame, tk.Label]:
    row = tk.Frame(parent, bg=P["bg_1"])
    row.pack(fill="x", pady=SPACING["xs"])
    lbl = tk.Label(row, text=label, bg=P["bg_1"], fg=P["text_primary"], font=FONTS["body"], anchor="w", width=28)
    lbl.pack(side="left")
    return row, lbl


def _toggle_row(parent: tk.Frame, label: str, key: str) -> SealSwitch:
    row, _ = _row(parent, label)
    var = tk.BooleanVar(value=settings.get(key))
    sw = SealSwitch(row, variable=var, command=lambda v: settings.set(key, v))
    sw.configure(bg=P["bg_1"])
    sw.pack(side="right")
    return sw


def _entry_row(parent: tk.Frame, label: str, key: str, placeholder: str = "") -> SealEntry:
    row, _ = _row(parent, label)
    ent = SealEntry(row, placeholder=placeholder)
    ent.set(str(settings.get(key)))
    ent.bind_entry("<FocusOut>", lambda _: settings.set(key, ent.get()))
    ent.pack(side="right", fill="x", expand=True)
    return ent


def _dropdown_row(parent: tk.Frame, label: str, key: str, options: list[str]) -> tk.StringVar:
    row, _ = _row(parent, label)
    var = tk.StringVar(value=settings.get(key))

    def _on_change(*_args: object) -> None:
        settings.set(key, var.get())

    var.trace_add("write", _on_change)
    menu = tk.OptionMenu(row, var, *options)
    menu.configure(
        bg=P["bg_2"], fg=P["text_primary"],
        activebackground=P["bg_3"], activeforeground=P["text_primary"],
        highlightthickness=0, relief="flat", font=FONTS["body"], bd=0,
    )
    menu["menu"].configure(
        bg=P["bg_2"], fg=P["text_primary"],
        activebackground=P["accent"], activeforeground="white",
        font=FONTS["body"], bd=0,
    )
    menu.pack(side="right")
    return var


# ──────────────────────────────────────────────
# Settings Page
# ──────────────────────────────────────────────


class SettingsPage(tk.Frame):
    def __init__(self, parent: tk.Widget, nav_callback: Callable) -> None:
        super().__init__(parent, bg=P["bg_0"])
        self._nav = nav_callback
        self._build()

    def _build(self) -> None:
        scroll = SealScrollFrame(self)
        scroll.pack(fill="both", expand=True)
        inner = scroll.inner

        # Header
        tk.Label(
            inner,
            text="Settings",
            bg=P["bg_0"],
            fg=P["text_primary"],
            font=FONTS["heading2"],
            anchor="w",
        ).pack(fill="x", padx=SPACING["lg"], pady=(SPACING["lg"], 0))

        # ── Download ────────────────────────────────
        sec = _section(inner, "Download")

        # Output directory
        row, _ = _row(sec, "Output folder")
        self._out_lbl = tk.Label(
            row,
            text=self._short(settings.get("output_dir")),
            bg=P["bg_1"],
            fg=P["text_secondary"],
            font=FONTS["body_sm"],
        )
        self._out_lbl.pack(side="right", padx=(0, SPACING["sm"]))
        SealButton(row, text="Browse", variant="secondary", command=self._pick_dir, height=30).pack(side="right")

        _entry_row(sec, "Output template", "output_template", "%(title).200B.%(ext)s")
        _toggle_row(sec, "Playlist subdirectory", "playlist_subdir")
        _toggle_row(sec, "Restrict filenames", "restrict_filenames")

        # ── Format ──────────────────────────────────
        sec2 = _section(inner, "Format")
        _toggle_row(sec2, "Audio only by default", "extract_audio")
        _dropdown_row(sec2, "Audio format", "audio_format", ["mp3", "m4a", "opus", "flac", "wav", "best"])
        _dropdown_row(sec2, "Video quality", "video_quality", ["best", "2160", "1440", "1080", "720", "480", "360"])

        # ── Post-processing ─────────────────────────
        sec3 = _section(inner, "Post-processing")
        _toggle_row(sec3, "Embed metadata", "embed_metadata")
        _toggle_row(sec3, "Embed thumbnail", "embed_thumbnail")
        _toggle_row(sec3, "Embed subtitles", "embed_subtitles")
        _entry_row(sec3, "Subtitle languages", "subtitle_languages", "en,fr,de")

        # ── Network ─────────────────────────────────
        sec4 = _section(inner, "Network")
        _entry_row(sec4, "HTTP proxy", "proxy", "http://host:port")
        _entry_row(sec4, "Rate limit", "rate_limit", "e.g. 1M  (0 = unlimited)")
        _toggle_row(sec4, "Use aria2c (faster)", "use_aria2c")

        row_cf, _ = _row(sec4, "Concurrent fragments")
        cf_var = tk.IntVar(value=settings.get("concurrent_fragments"))
        cf_spin = tk.Spinbox(
            row_cf, from_=1, to=32, textvariable=cf_var, width=5,
            bg=P["entry_bg"], fg=P["text_primary"],
            insertbackground=P["accent"], relief="flat",
            font=FONTS["body"], bd=1,
            command=lambda: settings.set("concurrent_fragments", cf_var.get()),
        )
        cf_spin.pack(side="right")

        # Cookies
        row_c, _ = _row(sec4, "Cookies file (Netscape)")
        self._cookie_lbl = tk.Label(
            row_c, text=self._short(settings.get("cookies_file") or "None"),
            bg=P["bg_1"], fg=P["text_secondary"], font=FONTS["body_sm"],
        )
        self._cookie_lbl.pack(side="right", padx=(0, SPACING["sm"]))
        SealButton(row_c, text="Browse", variant="secondary", command=self._pick_cookies, height=30).pack(side="right")

        # ── Updates ─────────────────────────────────
        sec5 = _section(inner, "Updates")
        ytdlp_ver = get_ytdlp_version()

        ytdlp_row = tk.Frame(sec5, bg=P["bg_1"])
        ytdlp_row.pack(fill="x", pady=SPACING["xs"])
        tk.Label(
            ytdlp_row,
            text=f"yt-dlp version: {ytdlp_ver}",
            bg=P["bg_1"],
            fg=P["text_secondary"],
            font=FONTS["body"],
        ).pack(side="left")

        self._ytdlp_update_btn = SealButton(
            ytdlp_row,
            text="⬆  Update yt-dlp",
            variant="secondary",
            command=self._update_ytdlp,
            height=30,
        )
        self._ytdlp_update_btn.pack(side="right")

        self._ytdlp_msg = tk.Label(sec5, text="", bg=P["bg_1"], fg=P["success"], font=FONTS["body_sm"])
        self._ytdlp_msg.pack(anchor="e", pady=(0, SPACING["xs"]))

        # ── About ────────────────────────────────────
        sec6 = _section(inner, "About")
        tk.Label(
            sec6,
            text="Seal Desktop  v1.0.0\nA powerful video & audio downloader powered by yt-dlp\nBuilt with Python · tkinter · yt-dlp",
            bg=P["bg_1"],
            fg=P["text_secondary"],
            font=FONTS["body_sm"],
            justify="left",
        ).pack(anchor="w")

        # Bottom padding
        tk.Frame(inner, bg=P["bg_0"], height=SPACING["2xl"]).pack()

    # ── Actions ───────────────────────────────

    def _pick_dir(self) -> None:
        d = filedialog.askdirectory(initialdir=settings.get("output_dir"))
        if d:
            settings.set("output_dir", d)
            self._out_lbl.configure(text=self._short(d))

    def _pick_cookies(self) -> None:
        f = filedialog.askopenfilename(
            filetypes=[("Netscape cookies", "*.txt"), ("All files", "*.*")]
        )
        if f:
            settings.set("cookies_file", f)
            self._cookie_lbl.configure(text=self._short(f))

    def _update_ytdlp(self) -> None:
        self._ytdlp_update_btn.configure_text("Updating…")
        self._ytdlp_msg.configure(text="")

        def done(success: bool, msg: str) -> None:
            self.after(
                0,
                lambda: (
                    self._ytdlp_update_btn.configure_text("⬆  Update yt-dlp"),
                    self._ytdlp_msg.configure(
                        text=msg,
                        fg=P["success"] if success else P["error"],
                    ),
                ),
            )

        update_ytdlp(done)

    @staticmethod
    def _short(p: str) -> str:
        if not p:
            return "None"
        path = Path(p)
        home = Path.home()
        try:
            return "~/" + str(path.relative_to(home))
        except ValueError:
            return str(path)[-50:]
