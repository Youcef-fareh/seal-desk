"""
Seal Desktop – Application Entry Point
Configures the root Tk window and launches the app shell.
"""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

# Ensure src/ is on path when running directly
sys.path.insert(0, str(Path(__file__).parent))

from src.core.settings import settings
from src.ui.app_shell import AppShell
from src.ui.theme import PALETTE as P


def _set_window_icon(root: tk.Tk) -> None:
    icon_path = Path(__file__).parent / "assets" / "icon.ico"
    if icon_path.exists():
        root.iconbitmap(str(icon_path))


def _apply_title_bar_dark(root: tk.Tk) -> None:
    """On Windows 10/11, make the title bar dark."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(ctypes.c_int(1)),
            ctypes.sizeof(ctypes.c_int),
        )
    except Exception:  # noqa: BLE001
        pass


def main() -> None:
    root = tk.Tk()
    root.title("Seal Desktop")
    root.configure(bg=P["bg_0"])

    # Restore window geometry
    w = settings.get("window_width")
    h = settings.get("window_height")
    x = settings.get("window_x")
    y = settings.get("window_y")

    if x >= 0 and y >= 0:
        root.geometry(f"{w}x{h}+{x}+{y}")
    else:
        # Centre on screen
        root.update_idletasks()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        cx = (sw - w) // 2
        cy = (sh - h) // 2
        root.geometry(f"{w}x{h}+{cx}+{cy}")

    root.minsize(800, 540)

    _set_window_icon(root)

    # Dark title bar on Windows
    root.update()
    _apply_title_bar_dark(root)

    AppShell(root)

    def _on_close() -> None:
        geo = root.geometry()  # e.g. "1100x720+200+100"
        parts = geo.replace("x", "+").split("+")
        if len(parts) == 4:
            settings.update(
                {
                    "window_width": int(parts[0]),
                    "window_height": int(parts[1]),
                    "window_x": int(parts[2]),
                    "window_y": int(parts[3]),
                }
            )
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
