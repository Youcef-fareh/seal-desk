"""
Seal Desktop – Main Application Window
Shell layout: sidebar + page router.
"""

from __future__ import annotations

import tkinter as tk
from typing import Callable

from .pages.download_page import DownloadPage
from .pages.history_page import HistoryPage
from .pages.settings_page import SettingsPage
from .theme import FONTS, PALETTE as P, SIDEBAR_WIDTH, SPACING, TOPBAR_HEIGHT


# ──────────────────────────────────────────────
# Sidebar nav item
# ──────────────────────────────────────────────


class NavItem(tk.Frame):
    def __init__(
        self,
        parent: tk.Widget,
        icon: str,
        label: str,
        on_click: Callable,
        active: bool = False,
    ) -> None:
        super().__init__(parent, bg=P["bg_1"], cursor="hand2")
        self._on_click = on_click
        self._active = active
        self._icon = icon
        self._label = label

        self._indicator = tk.Frame(self, bg=P["bg_1"], width=4)
        self._indicator.pack(side="left", fill="y")

        self._content = tk.Frame(self, bg=P["bg_1"], cursor="hand2")
        self._content.pack(side="left", fill="both", expand=True, padx=SPACING["sm"], pady=SPACING["sm"])

        self._icon_lbl = tk.Label(
            self._content, text=icon, bg=P["bg_1"], fg=P["text_primary"],
            font=("Segoe UI", 18), anchor="w", cursor="hand2"
        )
        self._icon_lbl.pack(side="left")

        self._text_lbl = tk.Label(
            self._content, text=label, bg=P["bg_1"], fg=P["text_primary"],
            font=FONTS["body"], anchor="w", padx=SPACING["sm"], cursor="hand2"
        )
        self._text_lbl.pack(side="left")

        for w in (self, self._content, self._icon_lbl, self._text_lbl, self._indicator):
            w.bind("<Button-1>", lambda _: self._on_click())
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

        if active:
            self.set_active(True)

    def set_active(self, active: bool) -> None:
        self._active = active
        color = P["accent_dim"] if active else P["bg_1"]
        ind_color = P["accent"] if active else P["bg_1"]
        fg = P["accent_light"] if active else P["text_secondary"]

        for w in (self, self._content, self._icon_lbl, self._text_lbl):
            w.configure(bg=color)
        self._indicator.configure(bg=ind_color)
        self._text_lbl.configure(fg=fg)
        self._icon_lbl.configure(fg=fg if active else P["text_secondary"])

    def _on_enter(self, _e: tk.Event) -> None:
        if not self._active:
            color = P["bg_2"]
            for w in (self, self._content, self._icon_lbl, self._text_lbl):
                w.configure(bg=color)

    def _on_leave(self, _e: tk.Event) -> None:
        self.set_active(self._active)


# ──────────────────────────────────────────────
# App Shell
# ──────────────────────────────────────────────


class AppShell(tk.Frame):
    PAGES = ["download", "history", "settings"]

    def __init__(self, root: tk.Tk) -> None:
        super().__init__(root, bg=P["bg_0"])
        self.pack(fill="both", expand=True)
        self._current_page = "download"
        self._nav_items: dict[str, NavItem] = {}
        self._pages: dict[str, tk.Frame] = {}

        self._build_sidebar()
        self._build_content()
        self._navigate("download")

    def _build_sidebar(self) -> None:
        sidebar = tk.Frame(self, bg=P["bg_1"], width=SIDEBAR_WIDTH)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Logo
        logo_frame = tk.Frame(sidebar, bg=P["bg_1"], pady=SPACING["lg"])
        logo_frame.pack(fill="x")

        tk.Label(
            logo_frame,
            text="🦭",
            bg=P["bg_1"],
            font=("Segoe UI", 32),
        ).pack(side="left", padx=(SPACING["md"], 0))

        title_frame = tk.Frame(logo_frame, bg=P["bg_1"])
        title_frame.pack(side="left", padx=SPACING["sm"])

        tk.Label(
            title_frame, text="Seal", bg=P["bg_1"],
            fg=P["text_primary"], font=FONTS["heading1"],
        ).pack(anchor="w")

        tk.Label(
            title_frame, text="Desktop", bg=P["bg_1"],
            fg=P["accent"], font=FONTS["body_sm"],
        ).pack(anchor="w")

        # Separator
        tk.Frame(sidebar, bg=P["divider"], height=1).pack(fill="x", padx=SPACING["md"])

        # Nav items
        nav_defs = [
            ("download", "⬇", "Download"),
            ("history",  "📋", "History"),
            ("settings", "⚙", "Settings"),
        ]

        nav_container = tk.Frame(sidebar, bg=P["bg_1"])
        nav_container.pack(fill="x", pady=SPACING["sm"])

        for page_id, icon, label in nav_defs:
            item = NavItem(
                nav_container,
                icon=icon,
                label=label,
                on_click=lambda p=page_id: self._navigate(p),
                active=(page_id == self._current_page),
            )
            item.pack(fill="x", pady=1)
            self._nav_items[page_id] = item

        # Bottom: version
        bottom_frame = tk.Frame(sidebar, bg=P["bg_1"])
        bottom_frame.pack(side="bottom", fill="x", pady=SPACING["md"])
        tk.Frame(bottom_frame, bg=P["divider"], height=1).pack(fill="x", padx=SPACING["md"], pady=(0, SPACING["sm"]))
        tk.Label(
            bottom_frame,
            text="v1.0.0  ·  Powered by yt-dlp",
            bg=P["bg_1"],
            fg=P["text_tertiary"],
            font=FONTS["caption"],
        ).pack()

    def _build_content(self) -> None:
        self._content = tk.Frame(self, bg=P["bg_0"])
        self._content.pack(side="left", fill="both", expand=True)

    def _navigate(self, page_id: str) -> None:
        if page_id == self._current_page and page_id in self._pages:
            # Refresh if revisiting
            p = self._pages[page_id]
            if hasattr(p, "refresh"):
                p.refresh()
            return

        # Update nav items
        for pid, item in self._nav_items.items():
            item.set_active(pid == page_id)

        # Hide current
        if self._current_page in self._pages:
            self._pages[self._current_page].pack_forget()

        self._current_page = page_id

        # Create or show page
        if page_id not in self._pages:
            page_cls = {
                "download": DownloadPage,
                "history": HistoryPage,
                "settings": SettingsPage,
            }[page_id]
            page = page_cls(self._content, self._navigate)
            self._pages[page_id] = page

        self._pages[page_id].pack(fill="both", expand=True)
