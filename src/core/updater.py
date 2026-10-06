"""
Seal Desktop - Update Manager
Checks GitHub Releases for new application versions, incremental update notes, and yt-dlp updates.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import requests

REPO = "Youcef-fareh/seal-desk"
YTDLP_REPO = "yt-dlp/yt-dlp"
CURRENT_VERSION = "1.2.1"


@dataclass
class AppReleaseInfo:
    version: str
    title: str
    notes: str
    html_url: str
    asset_url: str | None = None
    asset_name: str | None = None
    published_at: str = ""


def _parse_version_tuple(v_str: str) -> tuple[int, ...]:
    cleaned = v_str.lstrip("v").strip()
    parts = []
    for chunk in cleaned.split("."):
        digits = "".join(filter(str.isdigit, chunk))
        if digits:
            parts.append(int(digits))
    return tuple(parts) if parts else (0,)


def is_newer_version(remote_tag: str, local_version: str = CURRENT_VERSION) -> bool:
    remote_tuple = _parse_version_tuple(remote_tag)
    local_tuple = _parse_version_tuple(local_version)
    return remote_tuple > local_tuple


def get_latest_release(repo: str = REPO) -> dict | None:
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


def check_app_update(
    callback: Callable[[AppReleaseInfo | None, str | None], None],
) -> None:
    """
    Async check for app updates.
    Calls callback(release_info, None) if update is found.
    Calls callback(None, None) if current version is up to date.
    Calls callback(None, error_str) on failure.
    """

    def _run() -> None:
        try:
            data = get_latest_release(REPO)
            if not data:
                callback(None, "Could not fetch release information")
                return

            tag = data.get("tag_name", "").lstrip("v")
            if not tag:
                callback(None, None)
                return

            if is_newer_version(tag, CURRENT_VERSION):
                # Search for preferred downloadable asset (.exe for windows, .zip or .tar.gz)
                assets = data.get("assets", [])
                asset_url = None
                asset_name = None

                for a in assets:
                    name = a.get("name", "").lower()
                    if name.endswith(".exe"):
                        asset_url = a.get("browser_download_url")
                        asset_name = a.get("name")
                        break
                if not asset_url and assets:
                    asset_url = assets[0].get("browser_download_url")
                    asset_name = assets[0].get("name")

                info = AppReleaseInfo(
                    version=tag,
                    title=data.get("name") or f"Release v{tag}",
                    notes=data.get("body") or "No changelog provided.",
                    html_url=data.get("html_url") or f"https://github.com/{REPO}/releases",
                    asset_url=asset_url,
                    asset_name=asset_name,
                    published_at=data.get("published_at", "")[:10],
                )
                callback(info, None)
            else:
                callback(None, None)

        except Exception as exc:  # noqa: BLE001
            callback(None, str(exc))

    threading.Thread(target=_run, daemon=True, name="seal-update-check").start()


def download_app_installer(
    asset_url: str,
    asset_name: str,
    progress_callback: Callable[[float, str], None],
    done_callback: Callable[[bool, str], None],
) -> None:
    """Download update installer to temporary folder and invoke or report."""

    def _run() -> None:
        try:
            target_dir = Path(tempfile.gettempdir()) / "SealDesktopUpdates"
            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / asset_name

            progress_callback(0.05, f"Connecting to download {asset_name}…")
            resp = requests.get(asset_url, stream=True, timeout=30)
            resp.raise_for_status()

            total_size = int(resp.headers.get("content-length", 0))
            downloaded = 0

            with open(target_file, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 64):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            pct = downloaded / total_size
                            progress_callback(
                                pct,
                                f"Downloading update: {downloaded // (1024 * 1024)}MB / {total_size // (1024 * 1024)}MB",
                            )

            progress_callback(1.0, "Download completed.")
            done_callback(True, str(target_file))
        except Exception as exc:  # noqa: BLE001
            done_callback(False, str(exc))

    threading.Thread(target=_run, daemon=True, name="seal-update-download").start()


def update_ytdlp(callback: Callable[[bool, str], None]) -> None:
    """Update yt-dlp in-place using pip. Calls callback(success, message)."""

    def _run() -> None:
        try:
            subprocess.run(
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

    threading.Thread(target=_run, daemon=True, name="seal-ytdlp-update").start()


def get_ytdlp_version() -> str:
    try:
        import yt_dlp

        return yt_dlp.version.__version__
    except Exception:
        return "unknown"
