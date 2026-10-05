"""
Seal Desktop - Update Manager
Checks GitHub Releases for new versions and yt-dlp updates.
"""

from __future__ import annotations

import subprocess
import sys
import threading
from typing import Callable, Optional

import requests

REPO = "your-username/seal-desktop"    # Update on release
YTDLP_REPO = "yt-dlp/yt-dlp"
CURRENT_VERSION = "1.0.0"


def get_latest_release(repo: str) -> Optional[dict]:
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{repo}/releases/latest",
            timeout=10,
            headers={"Accept": "application/vnd.github+json"},
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:  # noqa: BLE001
        return None


def check_app_update(callback: Callable[[Optional[str], Optional[str]], None]) -> None:
    """Async check. Calls callback(version, download_url) or (None, None) on failure."""
    def _run() -> None:
        release = get_latest_release(REPO)
        if not release:
            callback(None, None)
            return
        tag = release.get("tag_name", "").lstrip("v")
        url = release.get("html_url")
        if tag and tag != CURRENT_VERSION:
            callback(tag, url)
        else:
            callback(None, None)

    threading.Thread(target=_run, daemon=True).start()


def update_ytdlp(callback: Callable[[bool, str], None]) -> None:
    """Update yt-dlp in-place using pip. Calls callback(success, message)."""
    def _run() -> None:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"],
                capture_output=True,
                text=True,
                check=True,
            )
            callback(True, "yt-dlp updated successfully.")
        except subprocess.CalledProcessError as e:
            callback(False, e.stderr or "Update failed.")
        except Exception as exc:  # noqa: BLE001
            callback(False, str(exc))

    threading.Thread(target=_run, daemon=True).start()


def get_ytdlp_version() -> str:
    try:
        import yt_dlp
        return yt_dlp.version.__version__
    except Exception:
        return "unknown"
