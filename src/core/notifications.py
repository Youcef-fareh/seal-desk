"""
Seal Desktop – Desktop Notification Helper
Native OS toast notifications via winotify (Windows 10/11) with
graceful fallback if winotify is not installed or when running on macOS/Linux.
"""

from __future__ import annotations

import sys
import threading


def _notify_win(title: str, message: str) -> None:
    try:
        from winotify import Notification  # type: ignore[import-untyped]

        toast = Notification(
            app_id="Seal Desktop",
            title=title,
            msg=message,
        )
        toast.show()
    except Exception:  # noqa: BLE001
        pass


def send_notification(title: str, message: str, duration: int = 5) -> None:
    """Fire-and-forget OS desktop notification (Windows only; silent fallback on others)."""
    if sys.platform != "win32":
        return
    threading.Thread(
        target=_notify_win,
        args=(title, message),
        daemon=True,
        name="seal-notify",
    ).start()


def is_notifications_supported() -> bool:
    """Return True when OS-level toast notifications are available."""
    if sys.platform != "win32":
        return False
    try:
        import winotify  # noqa: F401 # type: ignore[import-untyped]

        return True
    except ImportError:
        return False
