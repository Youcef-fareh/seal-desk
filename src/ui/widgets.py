"""
Seal Desktop – Custom Widgets
Reusable styled components built on top of tkinter.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from typing import Any

from ..core.i18n import t
from .theme import FONTS, PALETTE, SPACING

P = PALETTE  # shorthand


# ──────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}"


def _blend(c1: str, c2: str, t: float) -> str:
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    return _rgb_to_hex(
        int(r1 + (r2 - r1) * t),
        int(g1 + (g2 - g1) * t),
        int(b1 + (b2 - b1) * t),
    )


# ──────────────────────────────────────────────
# SealButton
# ──────────────────────────────────────────────


class SealButton(tk.Frame):
    """Rounded, hover-animated button."""

    def __init__(
        self,
        parent: tk.Widget,
        text: str = "",
        command: Callable = None,
        variant: str = "primary",  # primary | secondary | danger | ghost
        icon: str = "",
        width: int = 0,
        height: int = 36,
        **kwargs: Any,
    ) -> None:
        colors = {
            "primary": (P["btn_primary"], P["btn_primary_hover"], P["text_primary"]),
            "secondary": (P["btn_secondary"], P["btn_secondary_hover"], P["text_primary"]),
            "danger": (P["btn_danger"], P["btn_danger_hover"], P["text_primary"]),
            "ghost": ("", P["bg_3"], P["text_secondary"]),
        }
        self._bg, self._hover_bg, self._fg = colors.get(variant, colors["primary"])
        self._command = command

        if self._bg == "":
            real_bg = P["bg_1"]
        else:
            real_bg = self._bg

        super().__init__(
            parent,
            bg=real_bg,
            cursor="hand2",
            **{k: v for k, v in kwargs.items() if k not in ("bg", "cursor")},
        )

        label_text = f"{icon}  {text}" if icon else text
        self._label = tk.Label(
            self,
            text=label_text,
            bg=real_bg,
            fg=self._fg,
            font=FONTS["body"],
            padx=SPACING["md"],
            pady=0,
            cursor="hand2",
        )
        self._label.pack(expand=True, fill="both", ipady=4)

        # Bind
        for w in (self, self._label):
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)
            w.bind("<Button-1>", self._on_click)
            w.bind("<ButtonRelease-1>", self._on_release)

        self._real_bg = real_bg

    def _on_enter(self, _e: tk.Event) -> None:
        c = self._hover_bg if self._hover_bg else P["bg_3"]
        self.configure(bg=c)
        self._label.configure(bg=c)

    def _on_leave(self, _e: tk.Event) -> None:
        self.configure(bg=self._real_bg)
        self._label.configure(bg=self._real_bg)

    def _on_click(self, _e: tk.Event) -> None:
        c = _blend(self._real_bg, "#000000", 0.15)
        self.configure(bg=c)
        self._label.configure(bg=c)

    def _on_release(self, _e: tk.Event) -> None:
        self._on_enter(_e)
        if self._command:
            self._command()

    def configure_text(self, text: str) -> None:
        self._label.configure(text=text)


# ──────────────────────────────────────────────
# SealEntry
# ──────────────────────────────────────────────


class SealEntry(tk.Frame):
    """Styled single-line entry with focus ring and right-click context menu."""

    def __init__(
        self,
        parent: tk.Widget,
        placeholder: str = "",
        show: str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, bg=P["entry_border"], padx=1, pady=1)

        self._inner = tk.Frame(self, bg=P["entry_bg"])
        self._inner.pack(fill="both", expand=True)

        self._var = tk.StringVar()
        self._entry = tk.Entry(
            self._inner,
            textvariable=self._var,
            bg=P["entry_bg"],
            fg=P["text_primary"],
            insertbackground=P["accent"],
            relief="flat",
            bd=0,
            font=FONTS["body"],
            show=show,
            **{k: v for k, v in kwargs.items() if k not in ("bg", "fg", "font", "relief", "bd")},
        )
        self._entry.pack(fill="both", expand=True, padx=SPACING["sm"], pady=6)

        self._placeholder = placeholder
        self._has_placeholder = False
        if placeholder:
            self._show_placeholder()

        self._entry.bind("<FocusIn>", self._on_focus_in)
        self._entry.bind("<FocusOut>", self._on_focus_out)
        # Clear placeholder before paste so it never merges with placeholder text
        self._entry.bind("<<Paste>>", self._on_paste)
        # Right-click context menu
        self._entry.bind("<Button-3>", self._show_context_menu)
        self._entry.bind("<Button-2>", self._show_context_menu)  # middle-click (X11)

        # Build context menu
        self._ctx_menu = tk.Menu(
            self._entry,
            tearoff=0,
            bg=P["bg_2"],
            fg=P["text_primary"],
            activebackground=P["accent"],
            activeforeground="white",
            relief="flat",
            bd=0,
            font=FONTS["body"],
        )
        self._ctx_menu.add_command(label="Cut", command=self._ctx_cut)
        self._ctx_menu.add_command(label="Copy", command=self._ctx_copy)
        self._ctx_menu.add_command(label="Paste", command=self._ctx_paste)
        self._ctx_menu.add_separator()
        self._ctx_menu.add_command(label="Select All", command=self._ctx_select_all)

    # ── Placeholder helpers ────────────────────

    def _show_placeholder(self) -> None:
        if not self._var.get():
            self._entry.configure(fg=P["text_tertiary"])
            self._var.set(self._placeholder)
            self._has_placeholder = True

    def _hide_placeholder(self) -> None:
        if self._has_placeholder:
            self._var.set("")
            self._entry.configure(fg=P["text_primary"])
            self._has_placeholder = False

    def _on_focus_in(self, _e: tk.Event) -> None:
        self.configure(bg=P["entry_border_focus"])
        self._hide_placeholder()

    def _on_focus_out(self, _e: tk.Event) -> None:
        self.configure(bg=P["entry_border"])
        self._show_placeholder()

    def _on_paste(self, _e: tk.Event) -> None:
        """Ensure placeholder is cleared before pasted text lands in the entry."""
        self._hide_placeholder()
        # Return None so the default paste handler still runs

    # ── Context menu ───────────────────────────

    def _show_context_menu(self, e: tk.Event) -> None:
        """Show right-click context menu at the cursor position."""
        self._entry.focus_set()
        self._hide_placeholder()
        # Refresh labels in case language changed
        self._ctx_menu.entryconfig(0, label=t("ctx_cut"))
        self._ctx_menu.entryconfig(1, label=t("ctx_copy"))
        self._ctx_menu.entryconfig(2, label=t("ctx_paste"))
        self._ctx_menu.entryconfig(4, label=t("ctx_select_all"))
        try:
            self._ctx_menu.tk_popup(e.x_root, e.y_root)
        finally:
            self._ctx_menu.grab_release()

    def _ctx_cut(self) -> None:
        if self._entry.selection_present():
            self._entry.event_generate("<<Cut>>")
        if not self._var.get():
            self._show_placeholder()

    def _ctx_copy(self) -> None:
        if self._entry.selection_present():
            self._entry.event_generate("<<Copy>>")

    def _ctx_paste(self) -> None:
        self._hide_placeholder()
        self._entry.event_generate("<<Paste>>")

    def _ctx_select_all(self) -> None:
        self._hide_placeholder()
        self._entry.select_range(0, "end")
        self._entry.icursor("end")

    # ── Public API ─────────────────────────────

    def get(self) -> str:
        if self._has_placeholder:
            return ""
        return self._var.get()

    def set(self, value: str) -> None:
        self._has_placeholder = False
        self._var.set(value)
        self._entry.configure(fg=P["text_primary"])

    def clear(self) -> None:
        self._var.set("")
        self._has_placeholder = False
        self._show_placeholder()

    def update_placeholder(self, placeholder: str) -> None:
        """Update the placeholder text (called on language change)."""
        self._placeholder = placeholder
        if self._has_placeholder:
            self._var.set(placeholder)

    def bind_entry(self, event: str, callback: Callable) -> None:
        self._entry.bind(event, callback)


# ──────────────────────────────────────────────
# SealProgressBar
# ──────────────────────────────────────────────


class SealProgressBar(tk.Canvas):
    """Animated progress bar with gradient fill."""

    def __init__(
        self,
        parent: tk.Widget,
        height: int = 6,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            parent,
            height=height,
            bg=P["bg_1"],
            highlightthickness=0,
            **kwargs,
        )
        self._progress = 0.0
        self._height = height
        self.bind("<Configure>", self._redraw)

    def set_progress(self, value: float) -> None:
        self._progress = max(0.0, min(1.0, value))
        self._redraw()

    def _redraw(self, _e: tk.Event = None) -> None:
        self.delete("all")
        w = self.winfo_width()
        h = self._height
        r = h // 2

        # Track
        self.create_rounded_rect(0, 0, w, h, r, fill=P["progress_track"])

        # Fill
        fill_w = int(w * self._progress)
        if fill_w > 0:
            self.create_rounded_rect(0, 0, fill_w, h, r, fill=P["progress_fill"])

    def create_rounded_rect(
        self, x1: int, y1: int, x2: int, y2: int, radius: int, **kwargs: Any
    ) -> None:
        r = radius
        self.create_arc(
            x1,
            y1,
            x1 + 2 * r,
            y1 + 2 * r,
            start=90,
            extent=90,
            style="pieslice",
            outline="",
            **kwargs,
        )
        self.create_arc(
            x2 - 2 * r,
            y1,
            x2,
            y1 + 2 * r,
            start=0,
            extent=90,
            style="pieslice",
            outline="",
            **kwargs,
        )
        self.create_arc(
            x1,
            y2 - 2 * r,
            x1 + 2 * r,
            y2,
            start=180,
            extent=90,
            style="pieslice",
            outline="",
            **kwargs,
        )
        self.create_arc(
            x2 - 2 * r,
            y2 - 2 * r,
            x2,
            y2,
            start=270,
            extent=90,
            style="pieslice",
            outline="",
            **kwargs,
        )
        self.create_rectangle(x1 + r, y1, x2 - r, y2, outline="", **kwargs)
        self.create_rectangle(x1, y1 + r, x2, y2 - r, outline="", **kwargs)


# ──────────────────────────────────────────────
# SealCard
# ──────────────────────────────────────────────


class SealCard(tk.Frame):
    """A rounded-corner card container (emulated via Canvas background)."""

    def __init__(self, parent: tk.Widget, **kwargs: Any) -> None:
        super().__init__(
            parent,
            bg=P["bg_1"],
            relief="flat",
            **kwargs,
        )


# ──────────────────────────────────────────────
# SealLabel
# ──────────────────────────────────────────────


class SealLabel(tk.Label):
    def __init__(
        self,
        parent: tk.Widget,
        text: str = "",
        style: str = "body",  # display | heading1..3 | body | body_sm | caption | mono
        color: str = "text_primary",
        **kwargs: Any,
    ) -> None:
        super().__init__(
            parent,
            text=text,
            font=FONTS.get(style, FONTS["body"]),
            fg=P.get(color, color),
            bg=kwargs.pop("bg", P["bg_1"]),
            **kwargs,
        )


# ──────────────────────────────────────────────
# SealSwitch (Toggle)
# ──────────────────────────────────────────────


class SealSwitch(tk.Canvas):
    """Animated iOS-style toggle switch."""

    WIDTH = 44
    HEIGHT = 24
    PADDING = 2

    def __init__(
        self,
        parent: tk.Widget,
        variable: tk.BooleanVar = None,
        command: Callable[[bool], None] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            parent,
            width=self.WIDTH,
            height=self.HEIGHT,
            bg=P["bg_1"],
            highlightthickness=0,
            cursor="hand2",
            **kwargs,
        )
        self._var = variable or tk.BooleanVar(value=False)
        self._command = command
        self._animating = False

        self._draw()
        self.bind("<Button-1>", self._toggle)
        self._var.trace_add("write", lambda *_: self._draw())

    def _draw(self) -> None:
        self.delete("all")
        on = self._var.get()
        track_color = P["accent"] if on else P["bg_3"]
        knob_x = (
            (self.WIDTH - self.PADDING - self.HEIGHT // 2)
            if on
            else (self.PADDING + self.HEIGHT // 2)
        )
        r_track = self.HEIGHT // 2

        # Track
        self.create_oval(0, 0, self.HEIGHT, self.HEIGHT, fill=track_color, outline="")
        self.create_oval(
            self.WIDTH - self.HEIGHT, 0, self.WIDTH, self.HEIGHT, fill=track_color, outline=""
        )
        self.create_rectangle(
            r_track, 0, self.WIDTH - r_track, self.HEIGHT, fill=track_color, outline=""
        )

        # Knob
        r_knob = self.HEIGHT // 2 - self.PADDING
        self.create_oval(
            knob_x - r_knob,
            self.PADDING,
            knob_x + r_knob,
            self.HEIGHT - self.PADDING,
            fill="white",
            outline="",
        )

    def _toggle(self, _e: tk.Event) -> None:
        self._var.set(not self._var.get())
        if self._command:
            self._command(self._var.get())


# ──────────────────────────────────────────────
# SealScrollFrame
# ──────────────────────────────────────────────


class SealScrollFrame(tk.Frame):
    """A frame with an internal vertical scrollbar."""

    def __init__(self, parent: tk.Widget, **kwargs: Any) -> None:
        super().__init__(parent, bg=P["bg_0"], **kwargs)

        self._canvas = tk.Canvas(self, bg=P["bg_0"], highlightthickness=0, bd=0)
        self._scrollbar = tk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._scrollbar.set)

        self._scrollbar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self.inner = tk.Frame(self._canvas, bg=P["bg_0"])
        self._window = self._canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", self._on_inner_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        # Scope mousewheel to this frame only: activate on Enter, deactivate on Leave.
        # Fixes B4: using bind_all captured scroll events globally, meaning the last
        # SealScrollFrame created would intercept ALL scroll events app-wide.
        self._canvas.bind("<Enter>", self._on_enter)
        self._canvas.bind("<Leave>", self._on_leave)
        self.inner.bind("<Enter>", self._on_enter)
        self.inner.bind("<Leave>", self._on_leave)

    def _on_enter(self, _e: tk.Event) -> None:
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self._canvas.bind_all("<Button-4>", self._on_mousewheel_linux)  # Linux scroll up
        self._canvas.bind_all("<Button-5>", self._on_mousewheel_linux)  # Linux scroll down

    def _on_leave(self, _e: tk.Event) -> None:
        self._canvas.unbind_all("<MouseWheel>")
        self._canvas.unbind_all("<Button-4>")
        self._canvas.unbind_all("<Button-5>")

    def _on_inner_configure(self, _e: tk.Event) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, e: tk.Event) -> None:
        self._canvas.itemconfig(self._window, width=e.width)

    def _on_mousewheel(self, e: tk.Event) -> None:
        self._canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")

    def _on_mousewheel_linux(self, e: tk.Event) -> None:
        self._canvas.yview_scroll(-1 if e.num == 4 else 1, "units")
