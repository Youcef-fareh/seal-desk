"""
Seal Desktop – History Page
Shows all previously downloaded items with search & open-folder actions.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from typing import Callable

from ...core.settings import settings
from ..theme import FONTS, PALETTE as P, SPACING
from ..widgets import SealButton, SealCard, SealEntry, SealLabel, SealScrollFrame


class HistoryRow(tk.Frame):
    def __init__(self, parent: tk.Widget, entry: dict) -> None:
        super().__init__(parent, bg=P["bg_1"], padx=SPACING["md"], pady=SPACING["sm"])
        self._entry = entry
        self._build()

    def _build(self) -> None:
        icon = "🎵" if self._entry.get("is_audio") else "🎬"
        title = self._entry.get("title") or self._entry.get("url", "")

        row = tk.Frame(self, bg=P["bg_1"])
        row.pack(fill="x")

        tk.Label(
            row,
            text=f"{icon}  {title[:80]}",
            bg=P["bg_1"],
            fg=P["text_primary"],
            font=FONTS["body"],
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

        if self._entry.get("output") and os.path.exists(self._entry["output"]):
            SealButton(
                row,
                text="📂",
                variant="ghost",
                command=self._open_folder,
                height=28,
            ).pack(side="right", padx=(4, 0))

        url = self._entry.get("url", "")
        tk.Label(
            self,
            text=url[:100],
            bg=P["bg_1"],
            fg=P["text_tertiary"],
            font=FONTS["caption"],
            anchor="w",
        ).pack(fill="x")

        tk.Frame(self, bg=P["divider"], height=1).pack(fill="x", pady=(SPACING["sm"], 0))

    def _open_folder(self) -> None:
        path = self._entry.get("output", "")
        if not path:
            return
        folder = os.path.dirname(path)
        if sys.platform == "win32":
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.run(["open", folder])
        else:
            subprocess.run(["xdg-open", folder])


class HistoryPage(tk.Frame):
    def __init__(self, parent: tk.Widget, nav_callback: Callable) -> None:
        super().__init__(parent, bg=P["bg_0"])
        self._nav = nav_callback
        self._all_entries: list[dict] = []
        self._build()
        self._load()

    def _build(self) -> None:
        header_row = tk.Frame(self, bg=P["bg_0"], padx=SPACING["lg"], pady=SPACING["md"])
        header_row.pack(fill="x")

        SealLabel(header_row, "History", style="heading2", bg=P["bg_0"]).pack(
            side="left"
        )
        SealButton(
            header_row,
            text="🗑  Clear all",
            variant="danger",
            command=self._clear,
            height=32,
        ).pack(side="right")

        # Search
        search_row = tk.Frame(self, bg=P["bg_0"], padx=SPACING["lg"])
        search_row.pack(fill="x", pady=(0, SPACING["sm"]))

        self._search_entry = SealEntry(search_row, placeholder="Search history…")
        self._search_entry.pack(fill="x")
        self._search_entry.bind_entry("<KeyRelease>", lambda _: self._filter())

        # Scroll area
        self._scroll = SealScrollFrame(self)
        self._scroll.pack(fill="both", expand=True, padx=SPACING["lg"])

        self._empty_lbl = tk.Label(
            self._scroll.inner,
            text="No downloads yet.\nStart downloading to build your history! 📼",
            bg=P["bg_0"],
            fg=P["text_tertiary"],
            font=FONTS["body"],
            justify="center",
        )

    def _load(self) -> None:
        self._all_entries = settings.get_history()
        self._render(self._all_entries)

    def _render(self, entries: list[dict]) -> None:
        for w in self._scroll.inner.winfo_children():
            w.destroy()

        if not entries:
            self._empty_lbl.pack(expand=True, pady=60)
            return

        for entry in entries:
            HistoryRow(self._scroll.inner, entry).pack(fill="x")

    def _filter(self) -> None:
        q = self._search_entry.get().lower()
        if not q:
            self._render(self._all_entries)
        else:
            filtered = [
                e
                for e in self._all_entries
                if q in (e.get("title") or "").lower()
                or q in (e.get("url") or "").lower()
            ]
            self._render(filtered)

    def _clear(self) -> None:
        settings.clear_history()
        self._all_entries = []
        self._render([])

    def refresh(self) -> None:
        self._load()
