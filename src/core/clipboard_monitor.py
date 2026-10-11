"""
Seal Desktop – Clipboard Monitor
Monitors system clipboard for valid HTTP(S) URLs and notifies callback.
Uses non-blocking Tkinter root.after() event-loop polling to avoid secondary
Tk instances or thread-safety issues with OS clipboard access.
"""

from __future__ import annotations

import re
import tkinter as tk
from collections.abc import Callable

_URL_RE = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)
_POLL_INTERVAL_MS = 900


class ClipboardMonitor:
    """
    Polls the system clipboard safely on the main thread via Tk after().
    When a new HTTP(S) URL is copied, ``on_url_detected`` is called.
    """

    def __init__(self, root: tk.Misc, on_url_detected: Callable[[str], None]) -> None:
        self._root = root
        self._callback = on_url_detected
        self._last: str = ""
        self._running = False
        self._timer_id: str | None = None

        # Seed current clipboard content so app startup doesn't trigger immediately
        try:
            self._last = self._root.clipboard_get().strip()
        except Exception:  # noqa: BLE001
            self._last = ""

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._schedule_poll()

    def stop(self) -> None:
        self._running = False
        if self._timer_id:
            try:
                self._root.after_cancel(self._timer_id)
            except Exception:  # noqa: BLE001
                pass
            self._timer_id = None

    def _schedule_poll(self) -> None:
        if not self._running:
            return
        self._timer_id = self._root.after(_POLL_INTERVAL_MS, self._poll)

    def _poll(self) -> None:
        if not self._running:
            return
        try:
            text = self._root.clipboard_get().strip()
            if text and text != self._last and _URL_RE.match(text):
                self._last = text
                self._callback(text)
            elif text:
                self._last = text
        except Exception:  # noqa: BLE001
            pass  # Clipboard may contain binary or non-string data
        finally:
            self._schedule_poll()
