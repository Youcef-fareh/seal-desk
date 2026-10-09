"""
Seal Desktop – Application Entry Point
Configures the root Tk window and launches the app shell.
"""

from __future__ import annotations

import atexit
import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import platformdirs

# Ensure src/ is on path when running directly
sys.path.insert(0, str(Path(__file__).parent))

from src.core.i18n import set_language, t
from src.core.settings import settings
from src.ui.app_shell import AppShell
from src.ui.theme import PALETTE as P


def _get_lock_path() -> Path:
    cfg_dir = Path(platformdirs.user_config_dir("SealDesktop", "SealDesktop"))
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "seal.lock"


def _is_pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            import ctypes

            SYNCHRONIZE = 0x00100000
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE, False, pid
            )
            if not handle:
                return False
            exit_code = ctypes.c_ulong()
            ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
            ctypes.windll.kernel32.CloseHandle(handle)
            STILL_ACTIVE = 259
            return exit_code.value == STILL_ACTIVE
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def _acquire_instance_lock() -> bool:
    lock_path = _get_lock_path()
    if lock_path.exists():
        try:
            pid = int(lock_path.read_text(encoding="utf-8").strip())
            if pid != os.getpid() and _is_pid_alive(pid):
                return False
        except Exception:
            pass
    try:
        lock_path.write_text(str(os.getpid()), encoding="utf-8")
    except Exception:
        pass
    return True


def _release_instance_lock() -> None:
    try:
        lock_path = _get_lock_path()
        if lock_path.exists():
            pid_str = lock_path.read_text(encoding="utf-8").strip()
            if pid_str == str(os.getpid()):
                lock_path.unlink(missing_ok=True)
    except Exception:
        pass


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
    current_lang = settings.get("language", "en")
    set_language(current_lang)

    if not _acquire_instance_lock():
        dummy = tk.Tk()
        dummy.withdraw()
        messagebox.showinfo(
            t("app_already_running_title"),
            t("app_already_running_msg"),
            parent=dummy,
        )
        dummy.destroy()
        sys.exit(0)

    atexit.register(_release_instance_lock)

    root = tk.Tk()
    root.title("Seal Desktop")
    root.configure(bg=P["bg_0"])

    # Restore window geometry
    w = max(int(settings.get("window_width") or 1100), 800)
    h = max(int(settings.get("window_height") or 740), 540)
    x = int(settings.get("window_x") if settings.get("window_x") is not None else -1)
    y = int(settings.get("window_y") if settings.get("window_y") is not None else -1)

    if x >= 0 and y >= 0:
        root.geometry(f"{w}x{h}+{x}+{y}")
    else:
        # Centre on screen
        root.update_idletasks()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        cx = max(0, (sw - w) // 2)
        cy = max(0, (sh - h) // 2)
        root.geometry(f"{w}x{h}+{cx}+{cy}")

    root.minsize(800, 540)

    _set_window_icon(root)

    # Dark title bar on Windows
    root.update()
    _apply_title_bar_dark(root)

    AppShell(root)

    def _on_close() -> None:
        if root.state() == "normal":  # only persist when not minimized/iconic/zoomed
            geo = root.geometry()  # e.g. "1100x720+200+100"
            parts = geo.replace("x", "+").split("+")
            if len(parts) == 4:
                try:
                    w_val = int(parts[0])
                    h_val = int(parts[1])
                    x_val = int(parts[2])
                    y_val = int(parts[3])
                    if w_val >= 400 and h_val >= 300 and x_val >= -100 and y_val >= -100:
                        settings.update(
                            {
                                "window_width": w_val,
                                "window_height": h_val,
                                "window_x": x_val,
                                "window_y": y_val,
                            }
                        )
                except ValueError:
                    pass
        settings.flush()
        _release_instance_lock()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
