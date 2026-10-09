"""
Seal Desktop – Settings Page
Settings UI for download preferences, network, language (EN/AR), FFmpeg setup, and App Auto-Updater.
"""

from __future__ import annotations

import os
import sys
import tkinter as tk
import webbrowser
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox

from ...core.ffmpeg_utils import download_ffmpeg_async, is_ffmpeg_available
from ...core.i18n import (
    add_language_listener,
    get_language,
    remove_language_listener,
    set_language,
    t,
)
from ...core.settings import settings
from ...core.updater import (
    CURRENT_VERSION,
    AppReleaseInfo,
    check_app_update,
    download_app_installer,
    get_ytdlp_version,
    update_ytdlp,
)
from ..theme import FONTS, SPACING
from ..theme import PALETTE as P
from ..widgets import SealButton, SealEntry, SealScrollFrame, SealSwitch

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────


def _section(parent: tk.Widget, title: str) -> tuple[tk.Label, tk.Frame]:
    """Renders a section header + returns (label, content_frame)."""
    header = tk.Label(
        parent,
        text=title.upper(),
        bg=P["bg_0"],
        fg=P["text_tertiary"],
        font=("Segoe UI", 10, "bold"),
        anchor="w",
    )
    header.pack(fill="x", padx=SPACING["lg"], pady=(SPACING["lg"], SPACING["xs"]))

    tk.Frame(parent, bg=P["bg_1"], height=1).pack(fill="x", padx=SPACING["lg"])

    frame = tk.Frame(parent, bg=P["bg_1"], padx=SPACING["lg"], pady=SPACING["md"])
    frame.pack(fill="x", padx=SPACING["lg"])
    return header, frame


def _row(parent: tk.Frame, label_text: str) -> tuple[tk.Frame, tk.Label]:
    row = tk.Frame(parent, bg=P["bg_1"])
    row.pack(fill="x", pady=SPACING["xs"])
    lbl = tk.Label(
        row,
        text=label_text,
        bg=P["bg_1"],
        fg=P["text_primary"],
        font=FONTS["body"],
        anchor="w",
        width=28,
    )
    lbl.pack(side="left")
    return row, lbl


def _toggle_row(parent: tk.Frame, label_text: str, key: str) -> tuple[SealSwitch, tk.Label]:
    row, lbl = _row(parent, label_text)
    var = tk.BooleanVar(value=settings.get(key))
    sw = SealSwitch(row, variable=var, command=lambda v: settings.set(key, v))
    sw.configure(bg=P["bg_1"])
    sw.pack(side="right")
    return sw, lbl


def _entry_row(
    parent: tk.Frame, label_text: str, key: str, placeholder: str = ""
) -> tuple[SealEntry, tk.Label]:
    row, lbl = _row(parent, label_text)
    ent = SealEntry(row, placeholder=placeholder)
    ent.set(str(settings.get(key)))
    ent.bind_entry("<FocusOut>", lambda _: settings.set(key, ent.get()))
    ent.pack(side="right", fill="x", expand=True)
    return ent, lbl


def _dropdown_row(
    parent: tk.Frame,
    label_text: str,
    key: str,
    options: list[str],
    on_change_extra: Callable[[str], None] | None = None,
) -> tuple[tk.StringVar, tk.Label, tk.OptionMenu]:
    row, lbl = _row(parent, label_text)
    var = tk.StringVar(value=settings.get(key))

    def _on_change(*_args: object) -> None:
        val = var.get()
        settings.set(key, val)
        if on_change_extra:
            on_change_extra(val)

    var.trace_add("write", _on_change)
    menu = tk.OptionMenu(row, var, *options)
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
    menu.pack(side="right")
    return var, lbl, menu


# ──────────────────────────────────────────────
# Settings Page
# ──────────────────────────────────────────────


class SettingsPage(tk.Frame):
    def __init__(
        self,
        parent: tk.Widget,
        nav_callback: Callable,
        theme_callback: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent, bg=P["bg_0"])
        self._nav = nav_callback
        self._theme_callback = theme_callback
        self._trans_labels: list[tuple[tk.Label, str]] = []
        self._trans_buttons: list[tuple[SealButton, str]] = []
        add_language_listener(self._retranslate)

        self._build()

    def destroy(self) -> None:
        remove_language_listener(self._retranslate)
        super().destroy()

    def _build(self) -> None:
        scroll = SealScrollFrame(self)
        scroll.pack(fill="both", expand=True)
        inner = scroll.inner

        # Main Header
        self._page_title_lbl = tk.Label(
            inner,
            text=t("settings_title"),
            bg=P["bg_0"],
            fg=P["text_primary"],
            font=FONTS["heading2"],
            anchor="w",
        )
        self._page_title_lbl.pack(fill="x", padx=SPACING["lg"], pady=(SPACING["lg"], 0))

        # ── 1. General & Language ───────────────────
        sec_gen_lbl, sec_gen = _section(inner, t("sec_general"))
        self._trans_labels.append((sec_gen_lbl, "sec_general"))

        # Language dropdown
        row_lang, lbl_lang = _row(sec_gen, t("label_language"))
        self._trans_labels.append((lbl_lang, "label_language"))

        self._lang_var = tk.StringVar(
            value="العربية (Arabic)" if get_language() == "ar" else "English"
        )
        lang_opts = ["English", "العربية (Arabic)"]

        def _on_lang_picked(choice: str) -> None:
            code = "ar" if "Arabic" in choice or "العربية" in choice else "en"
            settings.set("language", code)
            set_language(code)

        lang_menu = tk.OptionMenu(row_lang, self._lang_var, *lang_opts, command=_on_lang_picked)
        lang_menu.configure(
            bg=P["bg_2"],
            fg=P["text_primary"],
            activebackground=P["bg_3"],
            activeforeground=P["text_primary"],
            highlightthickness=0,
            relief="flat",
            font=FONTS["body"],
            bd=0,
        )
        lang_menu["menu"].configure(
            bg=P["bg_2"],
            fg=P["text_primary"],
            activebackground=P["accent"],
            activeforeground="white",
            font=FONTS["body"],
            bd=0,
        )
        lang_menu.pack(side="right")

        row_theme, lbl_theme = _row(sec_gen, t("label_theme"))
        self._trans_labels.append((lbl_theme, "label_theme"))
        self._theme_var = tk.BooleanVar(value=settings.get("theme", "dark") != "light")
        self._theme_switch = SealSwitch(
            row_theme,
            variable=self._theme_var,
            command=lambda value: (
                settings.set("theme", "dark" if value else "light"),
                self._theme_callback() if self._theme_callback else None,
            ),
        )
        self._theme_switch.configure(bg=P["bg_1"])
        self._theme_switch.pack(side="right")

        # ── 2. Download Options ─────────────────────
        sec_dl_lbl, sec_dl = _section(inner, t("sec_download"))
        self._trans_labels.append((sec_dl_lbl, "sec_download"))

        row_out, lbl_out = _row(sec_dl, t("label_output_dir"))
        self._trans_labels.append((lbl_out, "label_output_dir"))

        self._out_lbl = tk.Label(
            row_out,
            text=self._short(settings.get("output_dir")),
            bg=P["bg_1"],
            fg=P["text_secondary"],
            font=FONTS["body_sm"],
        )
        self._out_lbl.pack(side="right", padx=(0, SPACING["sm"]))

        btn_browse = SealButton(
            row_out, text=t("browse"), variant="secondary", command=self._pick_dir, height=30
        )
        btn_browse.pack(side="right")
        self._trans_buttons.append((btn_browse, "browse"))

        _, lbl_tmpl = _entry_row(
            sec_dl, t("label_output_template"), "output_template", "%(title).200B.%(ext)s"
        )
        self._trans_labels.append((lbl_tmpl, "label_output_template"))

        _, lbl_pl = _toggle_row(sec_dl, t("label_playlist_subdir"), "playlist_subdir")
        self._trans_labels.append((lbl_pl, "label_playlist_subdir"))

        _, lbl_re = _toggle_row(sec_dl, t("label_restrict_filenames"), "restrict_filenames")
        self._trans_labels.append((lbl_re, "label_restrict_filenames"))

        # ── 3. Format & Merging ─────────────────────
        sec_fmt_lbl, sec_fmt = _section(inner, t("sec_format"))
        self._trans_labels.append((sec_fmt_lbl, "sec_format"))

        _, lbl_def_audio = _toggle_row(sec_fmt, t("label_default_audio"), "extract_audio")
        self._trans_labels.append((lbl_def_audio, "label_default_audio"))

        _, lbl_af, _ = _dropdown_row(
            sec_fmt,
            t("label_audio_format"),
            "audio_format",
            ["mp3", "m4a", "opus", "flac", "wav", "best"],
        )
        self._trans_labels.append((lbl_af, "label_audio_format"))

        _, lbl_vq, _ = _dropdown_row(
            sec_fmt,
            t("label_video_quality"),
            "video_quality",
            ["best", "2160", "1440", "1080", "720", "480", "360"],
        )
        self._trans_labels.append((lbl_vq, "label_video_quality"))

        _, lbl_vc, _ = _dropdown_row(
            sec_fmt,
            t("label_video_container"),
            "video_container",
            ["mp4", "mkv"],
        )
        self._trans_labels.append((lbl_vc, "label_video_container"))

        _, lbl_vcodec, _ = _dropdown_row(
            sec_fmt,
            t("label_video_codec"),
            "video_codec",
            ["h264", "auto", "vp9", "av1"],
        )
        self._trans_labels.append((lbl_vcodec, "label_video_codec"))

        # ── 4. FFmpeg Engine (Audio/Video Merger) ───
        sec_ff_lbl, sec_ff = _section(inner, t("sec_ffmpeg"))
        self._trans_labels.append((sec_ff_lbl, "sec_ffmpeg"))

        self._ffmpeg_status_row = tk.Frame(sec_ff, bg=P["bg_1"])
        self._ffmpeg_status_row.pack(fill="x", pady=SPACING["xs"])

        self._ffmpeg_status_lbl = tk.Label(
            self._ffmpeg_status_row,
            text="",
            bg=P["bg_1"],
            font=FONTS["body"],
            anchor="w",
        )
        self._ffmpeg_status_lbl.pack(side="left", fill="x", expand=True)

        self._ffmpeg_setup_btn = SealButton(
            self._ffmpeg_status_row,
            text=t("btn_setup_ffmpeg"),
            variant="secondary",
            command=self._setup_ffmpeg,
            height=30,
        )
        self._ffmpeg_setup_btn.pack(side="right")
        self._trans_buttons.append((self._ffmpeg_setup_btn, "btn_setup_ffmpeg"))

        self._refresh_ffmpeg_status()

        # ── 5. Post-processing ──────────────────────
        sec_post_lbl, sec_post = _section(inner, t("sec_postproc"))
        self._trans_labels.append((sec_post_lbl, "sec_postproc"))

        _, lbl_em = _toggle_row(sec_post, t("label_embed_metadata"), "embed_metadata")
        self._trans_labels.append((lbl_em, "label_embed_metadata"))

        _, lbl_et = _toggle_row(sec_post, t("label_embed_thumbnail"), "embed_thumbnail")
        self._trans_labels.append((lbl_et, "label_embed_thumbnail"))

        _, lbl_es = _toggle_row(sec_post, t("label_embed_subtitles"), "embed_subtitles")
        self._trans_labels.append((lbl_es, "label_embed_subtitles"))

        _, lbl_sl = _entry_row(
            sec_post, t("label_sub_languages"), "subtitle_languages", "en,ar,fr,de"
        )
        self._trans_labels.append((lbl_sl, "label_sub_languages"))

        # ── 6. Network ──────────────────────────────
        sec_net_lbl, sec_net = _section(inner, t("sec_network"))
        self._trans_labels.append((sec_net_lbl, "sec_network"))

        _, lbl_px = _entry_row(sec_net, t("label_proxy"), "proxy", "http://host:port")
        self._trans_labels.append((lbl_px, "label_proxy"))

        _, lbl_rl = _entry_row(sec_net, t("label_rate_limit"), "rate_limit", "e.g. 1M")
        self._trans_labels.append((lbl_rl, "label_rate_limit"))

        _, lbl_ar = _toggle_row(sec_net, t("label_aria2c"), "use_aria2c")
        self._trans_labels.append((lbl_ar, "label_aria2c"))

        # Cookies
        row_c, lbl_ck = _row(sec_net, t("label_cookies"))
        self._trans_labels.append((lbl_ck, "label_cookies"))

        self._cookie_lbl = tk.Label(
            row_c,
            text=self._short(settings.get("cookies_file") or "None"),
            bg=P["bg_1"],
            fg=P["text_secondary"],
            font=FONTS["body_sm"],
        )
        self._cookie_lbl.pack(side="right", padx=(0, SPACING["sm"]))
        btn_ck_browse = SealButton(
            row_c, text=t("browse"), variant="secondary", command=self._pick_cookies, height=30
        )
        btn_ck_browse.pack(side="right")
        self._trans_buttons.append((btn_ck_browse, "browse"))

        # ── 7. App Updates & Auto-Updater ───────────
        sec_up_lbl, sec_up = _section(inner, t("sec_updates"))
        self._trans_labels.append((sec_up_lbl, "sec_updates"))

        _, lbl_auto_up = _toggle_row(sec_up, t("label_auto_check"), "auto_check_updates")
        self._trans_labels.append((lbl_auto_up, "label_auto_check"))

        # App updates row
        app_up_row = tk.Frame(sec_up, bg=P["bg_1"])
        app_up_row.pack(fill="x", pady=SPACING["xs"])

        tk.Label(
            app_up_row,
            text=f"Seal Desktop: v{CURRENT_VERSION}",
            bg=P["bg_1"],
            fg=P["text_secondary"],
            font=FONTS["body"],
        ).pack(side="left")

        self._app_update_btn = SealButton(
            app_up_row,
            text=t("btn_check_updates"),
            variant="primary",
            command=self._check_app_updates_clicked,
            height=30,
        )
        self._app_update_btn.pack(side="right")
        self._trans_buttons.append((self._app_update_btn, "btn_check_updates"))

        self._app_update_msg = tk.Label(
            sec_up, text="", bg=P["bg_1"], fg=P["accent_light"], font=FONTS["body_sm"]
        )
        self._app_update_msg.pack(anchor="e", pady=(0, SPACING["xs"]))

        # yt-dlp update row
        ytdlp_row = tk.Frame(sec_up, bg=P["bg_1"])
        ytdlp_row.pack(fill="x", pady=SPACING["xs"])

        self._ytdlp_ver_lbl = tk.Label(
            ytdlp_row,
            text=f"yt-dlp: {get_ytdlp_version()}",
            bg=P["bg_1"],
            fg=P["text_secondary"],
            font=FONTS["body"],
        )
        self._ytdlp_ver_lbl.pack(side="left")

        self._ytdlp_update_btn = SealButton(
            ytdlp_row,
            text=t("btn_update_ytdlp"),
            variant="secondary",
            command=self._update_ytdlp,
            height=30,
        )
        self._ytdlp_update_btn.pack(side="right")
        self._trans_buttons.append((self._ytdlp_update_btn, "btn_update_ytdlp"))

        # ── 8. About ────────────────────────────────
        sec_ab_lbl, sec_ab = _section(inner, t("sec_about"))
        self._trans_labels.append((sec_ab_lbl, "sec_about"))

        self._about_lbl = tk.Label(
            sec_ab,
            text=t("about_desc"),
            bg=P["bg_1"],
            fg=P["text_secondary"],
            font=FONTS["body_sm"],
            justify="left",
        )
        self._about_lbl.pack(anchor="w")

        # Bottom space
        tk.Frame(inner, bg=P["bg_0"], height=SPACING["2xl"]).pack()

    # ── Actions ───────────────────────────────

    def _refresh_ffmpeg_status(self) -> None:
        if not self.winfo_exists() or not self._ffmpeg_status_lbl.winfo_exists():
            return
        if is_ffmpeg_available():
            self._ffmpeg_status_lbl.configure(
                text="✔  " + t("ffmpeg_ready"),
                fg=P["success"],
            )
            if self._ffmpeg_setup_btn.winfo_exists():
                self._ffmpeg_setup_btn.pack_forget()
        else:
            self._ffmpeg_status_lbl.configure(
                text="⚠️  " + t("ffmpeg_missing"),
                fg=P["warning"],
            )
            if self._ffmpeg_setup_btn.winfo_exists():
                self._ffmpeg_setup_btn.pack(side="right")

    def _setup_ffmpeg(self) -> None:
        self._ffmpeg_setup_btn.configure_text(t("status_installing"))

        def on_prog(_pct: float, msg: str) -> None:
            self.after(0, lambda: self._ffmpeg_setup_btn.configure_text(msg[:22]))

        def on_done(success: bool, msg: str) -> None:
            def _apply() -> None:
                if success:
                    self._refresh_ffmpeg_status()
                    messagebox.showinfo("FFmpeg", t("ffmpeg_installed_success"))
                else:
                    self._ffmpeg_setup_btn.configure_text(t("btn_setup_ffmpeg"))
                    messagebox.showwarning("FFmpeg", msg)

            self.after(0, _apply)

        download_ffmpeg_async(on_prog, on_done)

    def _check_app_updates_clicked(self) -> None:
        self._app_update_btn.configure_text(t("status_checking"))
        self._app_update_msg.configure(text="")

        def on_result(info: AppReleaseInfo | None, error: str | None) -> None:
            def _apply() -> None:
                self._app_update_btn.configure_text(t("btn_check_updates"))
                if error:
                    self._app_update_msg.configure(text=t("update_check_failed"), fg=P["error"])
                elif info:
                    self._show_update_dialog(info)
                else:
                    self._app_update_msg.configure(
                        text=t("up_to_date", version=CURRENT_VERSION), fg=P["success"]
                    )

            self.after(0, _apply)

        check_app_update(on_result)

    def _show_update_dialog(self, info: AppReleaseInfo) -> None:
        dlg = tk.Toplevel(self)
        dlg.title(t("update_available_title"))
        dlg.geometry("540x440")
        dlg.configure(bg=P["bg_1"])
        dlg.transient(self.winfo_toplevel())
        dlg.grab_set()

        pad = SPACING["lg"]
        tk.Label(
            dlg,
            text=f"🚀  {t('update_available_title')}",
            bg=P["bg_1"],
            fg=P["accent"],
            font=FONTS["heading2"],
        ).pack(anchor="w", padx=pad, pady=(pad, 4))

        tk.Label(
            dlg,
            text=t("update_available_msg", version=info.version, current=CURRENT_VERSION),
            bg=P["bg_1"],
            fg=P["text_primary"],
            font=FONTS["body"],
        ).pack(anchor="w", padx=pad, pady=(0, pad))

        # Incremental update notes
        tk.Label(
            dlg,
            text=t("update_notes_title"),
            bg=P["bg_1"],
            fg=P["text_secondary"],
            font=FONTS["heading3"],
        ).pack(anchor="w", padx=pad, pady=(0, 4))

        text_frame = tk.Frame(dlg, bg=P["bg_2"], padx=8, pady=8)
        text_frame.pack(fill="both", expand=True, padx=pad, pady=(0, pad))

        txt = tk.Text(
            text_frame,
            bg=P["bg_2"],
            fg=P["text_primary"],
            font=FONTS["body_sm"],
            relief="flat",
            wrap="word",
            bd=0,
        )
        txt.insert("1.0", info.notes)
        txt.configure(state="disabled")
        txt.pack(fill="both", expand=True)

        btn_row = tk.Frame(dlg, bg=P["bg_1"])
        btn_row.pack(fill="x", padx=pad, pady=(0, pad))

        if info.asset_url and info.asset_name:
            download_btn = SealButton(
                btn_row,
                text=t("btn_download_update"),
                variant="primary",
                command=lambda: self._download_and_run_update(info, download_btn, dlg),
                height=36,
            )
            download_btn.pack(side="left")

        SealButton(
            btn_row,
            text=t("btn_view_release"),
            variant="secondary",
            command=lambda: webbrowser.open(info.html_url),
            height=36,
        ).pack(side="left", padx=(SPACING["sm"], 0))

        SealButton(
            btn_row,
            text=t("btn_close"),
            variant="ghost",
            command=dlg.destroy,
            height=36,
        ).pack(side="right")

    def _download_and_run_update(
        self, info: AppReleaseInfo, btn: SealButton, dlg: tk.Toplevel
    ) -> None:
        btn.configure_text(t("status_downloading"))

        def on_prog(_pct: float, msg: str) -> None:
            self.after(0, lambda: btn.configure_text(msg[:20]))

        def on_done(success: bool, path_or_err: str) -> None:
            def _apply() -> None:
                if success:
                    btn.configure_text(t("status_ready"))
                    if sys.platform == "win32" and path_or_err.endswith(".exe"):
                        os.startfile(path_or_err)
                        dlg.destroy()
                    else:
                        messagebox.showinfo("Update", f"Update downloaded to:\n{path_or_err}")
                else:
                    btn.configure_text(t("btn_download_update"))
                    messagebox.showerror("Update failed", path_or_err)

            self.after(0, _apply)

        download_app_installer(info.asset_url, info.asset_name, on_prog, on_done)

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
        self._ytdlp_update_btn.configure_text(t("status_updating"))

        def done(success: bool, msg: str) -> None:
            self.after(
                0,
                lambda: (
                    self._ytdlp_update_btn.configure_text(t("btn_update_ytdlp")),
                    self._ytdlp_ver_lbl.configure(text=f"yt-dlp: {get_ytdlp_version()}"),
                    messagebox.showinfo("yt-dlp", msg)
                    if success
                    else messagebox.showwarning("yt-dlp", msg),
                ),
            )

        update_ytdlp(done)

    def _retranslate(self) -> None:
        """Dynamically refresh labels when language is changed."""
        if self.winfo_exists() and self._page_title_lbl.winfo_exists():
            self._page_title_lbl.configure(text=t("settings_title"))
        for lbl, key in self._trans_labels:
            if lbl.winfo_exists():
                lbl.configure(text=t(key).upper() if key.startswith("sec_") else t(key))
        for btn, key in self._trans_buttons:
            if btn.winfo_exists():
                btn.configure_text(t(key))
        if self._about_lbl.winfo_exists():
            self._about_lbl.configure(text=t("about_desc"))
        self._refresh_ffmpeg_status()

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
