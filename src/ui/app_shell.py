"""
Seal Desktop – Main Application Window
Shell layout: sidebar + page router, bilingual support (EN/AR), and startup auto-update check.
"""

from __future__ import annotations

import tkinter as tk
import webbrowser
from collections.abc import Callable

from ..core.i18n import add_language_listener, remove_language_listener, set_language, t
from ..core.settings import settings
from ..core.updater import CURRENT_VERSION, AppReleaseInfo, check_app_update
from .pages.download_page import DownloadPage
from .pages.history_page import HistoryPage
from .pages.settings_page import SettingsPage
from .theme import FONTS, SIDEBAR_WIDTH, SPACING, apply_theme
from .theme import PALETTE as P
from .widgets import SealButton

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
        self._content.pack(
            side="left", fill="both", expand=True, padx=SPACING["sm"], pady=SPACING["sm"]
        )

        self._icon_lbl = tk.Label(
            self._content,
            text=icon,
            bg=P["bg_1"],
            fg=P["text_primary"],
            font=("Segoe UI", 18),
            anchor="w",
            cursor="hand2",
        )
        self._icon_lbl.pack(side="left")

        self._text_lbl = tk.Label(
            self._content,
            text=label,
            bg=P["bg_1"],
            fg=P["text_primary"],
            font=FONTS["body"],
            anchor="w",
            padx=SPACING["sm"],
            cursor="hand2",
        )
        self._text_lbl.pack(side="left")

        for w in (self, self._content, self._icon_lbl, self._text_lbl, self._indicator):
            w.bind("<Button-1>", lambda _: self._on_click())
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

        if active:
            self.set_active(True)

    def set_label(self, label: str) -> None:
        self._label = label
        self._text_lbl.configure(text=label)

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

        # Initialize language from settings
        set_language(settings.get("language", "en"))
        apply_theme(settings.get("theme", "dark") != "light")
        add_language_listener(self._retranslate)

        self._build_sidebar()
        self._build_content()
        self._navigate("download")

        # Startup auto-updater check
        if settings.get("auto_check_updates", True):
            self.after(3000, self._check_startup_update)

    def destroy(self) -> None:
        remove_language_listener(self._retranslate)
        super().destroy()

    def _apply_theme(self) -> None:
        apply_theme(settings.get("theme", "dark") != "light")
        for page in list(self._pages.values()):
            if page.winfo_exists():
                page.destroy()
        self._pages.clear()
        self._navigate(self._current_page)

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

        self._logo_title = tk.Label(
            title_frame,
            text="Seal",
            bg=P["bg_1"],
            fg=P["text_primary"],
            font=FONTS["heading1"],
        )
        self._logo_title.pack(anchor="w")

        self._logo_sub = tk.Label(
            title_frame,
            text=t("app_subtitle"),
            bg=P["bg_1"],
            fg=P["accent"],
            font=FONTS["body_sm"],
        )
        self._logo_sub.pack(anchor="w")

        # Separator
        tk.Frame(sidebar, bg=P["divider"], height=1).pack(fill="x", padx=SPACING["md"])

        # Nav items
        nav_defs = [
            ("download", "⬇", t("nav_download")),
            ("history", "📋", t("nav_history")),
            ("settings", "⚙", t("nav_settings")),
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
        tk.Frame(bottom_frame, bg=P["divider"], height=1).pack(
            fill="x", padx=SPACING["md"], pady=(0, SPACING["sm"])
        )
        self._version_lbl = tk.Label(
            bottom_frame,
            text=t("app_footer"),
            bg=P["bg_1"],
            fg=P["text_tertiary"],
            font=FONTS["caption"],
        )
        self._version_lbl.pack()

    def _build_content(self) -> None:
        self._content = tk.Frame(self, bg=P["bg_0"])
        self._content.pack(side="left", fill="both", expand=True)

        # Top update banner (hidden initially)
        self._update_banner = tk.Frame(
            self._content, bg=P["accent_dim"], padx=SPACING["md"], pady=SPACING["sm"]
        )
        self._update_banner_lbl = tk.Label(
            self._update_banner,
            text="",
            bg=P["accent_dim"],
            fg=P["accent_light"],
            font=FONTS["body"],
        )
        self._update_banner_lbl.pack(side="left")

        self._update_banner_btn = SealButton(
            self._update_banner,
            text="",
            variant="primary",
            command=self._on_update_banner_click,
            height=28,
        )
        self._update_banner_btn.pack(side="right")
        self._update_banner_dismiss = SealButton(
            self._update_banner,
            text="✕",
            variant="ghost",
            command=self._update_banner.pack_forget,
            height=28,
            width=28,
        )
        self._update_banner_dismiss.pack(side="right", padx=(0, SPACING["sm"]))
        self._latest_release_info: AppReleaseInfo | None = None

    def _navigate(self, page_id: str) -> None:
        if page_id == self._current_page and page_id in self._pages:
            p = self._pages[page_id]
            if hasattr(p, "refresh"):
                p.refresh()
            return

        for pid, item in self._nav_items.items():
            item.set_active(pid == page_id)

        if self._current_page in self._pages:
            self._pages[self._current_page].pack_forget()

        self._current_page = page_id

        if page_id not in self._pages:
            page_cls = {
                "download": DownloadPage,
                "history": HistoryPage,
                "settings": SettingsPage,
            }[page_id]
            if page_id == "settings":
                page = page_cls(self._content, self._navigate, theme_callback=self._apply_theme)
            else:
                page = page_cls(self._content, self._navigate)
            self._pages[page_id] = page

        self._pages[page_id].pack(fill="both", expand=True)

    def _check_startup_update(self) -> None:
        def on_result(info: AppReleaseInfo | None, error: str | None) -> None:
            if info and not error:
                self.after(0, lambda: self._show_update_banner(info))

        check_app_update(on_result)

    def _show_update_banner(self, info: AppReleaseInfo) -> None:
        self._latest_release_info = info
        self._update_banner_lbl.configure(
            text=f"🚀  {t('update_available_msg', version=info.version, current=CURRENT_VERSION)}"
        )
        self._update_banner_btn.configure_text(t("btn_download_update"))
        pack_kwargs: dict = {"fill": "x", "side": "top"}
        current_page_widget = self._pages.get(self._current_page)
        if (
            current_page_widget
            and current_page_widget.winfo_exists()
            and current_page_widget.winfo_manager() == "pack"
        ):
            pack_kwargs["before"] = current_page_widget
        self._update_banner.pack(**pack_kwargs)

    def _on_update_banner_click(self) -> None:
        if self._latest_release_info:
            if self._latest_release_info.html_url:
                webbrowser.open(self._latest_release_info.html_url)
            self._navigate("settings")

    def _retranslate(self) -> None:
        """Update navigation text when language switches."""
        self._logo_sub.configure(text=t("app_subtitle"))
        self._version_lbl.configure(text=t("app_footer"))
        if "download" in self._nav_items:
            self._nav_items["download"].set_label(t("nav_download"))
        if "history" in self._nav_items:
            self._nav_items["history"].set_label(t("nav_history"))
        if "settings" in self._nav_items:
            self._nav_items["settings"].set_label(t("nav_settings"))
