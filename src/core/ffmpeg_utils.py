"""
Seal Desktop - FFmpeg Utility & Downloader
Ensures audio and video are properly merged by detecting or auto-installing FFmpeg.

FFmpeg is bundled with the app via the `imageio-ffmpeg` package, which ships
prebuilt binaries for Windows, macOS, and Linux. No user action required.
"""

from __future__ import annotations

import io
import os
import shutil
import sys
import threading
import zipfile
from collections.abc import Callable
from pathlib import Path

import platformdirs
import requests

APP_NAME = "SealDesktop"
APP_AUTHOR = "SealDesktop"

# Official standalone FFmpeg build zip for Windows x64 (yt-dlp curated builds)
# Used as a fallback when the bundled imageio-ffmpeg binary is unavailable.
WIN64_FFMPEG_URL = "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"


def get_local_bin_dir() -> Path:
    base = Path(platformdirs.user_data_dir(APP_NAME, APP_AUTHOR))
    bin_dir = base / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    return bin_dir


def _get_bundled_ffmpeg() -> str | None:
    """Return the FFmpeg binary bundled via imageio-ffmpeg, if available."""
    try:
        import imageio_ffmpeg  # noqa: PLC0415

        path = imageio_ffmpeg.get_ffmpeg_exe()
        if path and os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    except Exception:  # noqa: BLE001
        pass
    return None


def get_ffmpeg_path() -> str | None:
    """Find ffmpeg – checks bundled binary first, then local/system locations."""

    # 1. Bundled binary (imageio-ffmpeg) — always available in the packaged app
    bundled = _get_bundled_ffmpeg()
    if bundled:
        return bundled

    exe_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"

    # 2. User-downloaded binary in local app-data dir
    local_path = get_local_bin_dir() / exe_name
    if local_path.is_file() and os.access(local_path, os.X_OK):
        return str(local_path)

    # 3. Project-relative bin folder (dev-mode convenience)
    proj_bin = Path(__file__).resolve().parent.parent.parent / "bin" / exe_name
    if proj_bin.is_file() and os.access(proj_bin, os.X_OK):
        return str(proj_bin)

    # 4. System PATH
    system_path = shutil.which("ffmpeg")
    if system_path:
        return system_path

    # 5. Common Windows install locations
    if sys.platform == "win32":
        for candidate in (
            Path("C:/ffmpeg/bin/ffmpeg.exe"),
            Path("C:/Program Files/ffmpeg/bin/ffmpeg.exe"),
            Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Links/ffmpeg.exe",
        ):
            if candidate.is_file():
                return str(candidate)

    return None


def is_ffmpeg_available() -> bool:
    return get_ffmpeg_path() is not None


def download_ffmpeg_async(
    progress_callback: Callable[[float, str], None],
    done_callback: Callable[[bool, str], None],
) -> None:
    """
    Downloads static FFmpeg binary for Windows x64 and extracts to local bin dir.
    Only needed as a fallback when the bundled imageio-ffmpeg binary is missing.
    Calls progress_callback(fraction, message) and done_callback(success, message).
    """

    def _worker() -> None:
        try:
            if sys.platform != "win32":
                done_callback(
                    False,
                    "Please install ffmpeg via your package manager (e.g. sudo apt install ffmpeg)",
                )
                return

            dest_dir = get_local_bin_dir()
            progress_callback(0.05, "Connecting to FFmpeg repository…")

            resp = requests.get(WIN64_FFMPEG_URL, stream=True, timeout=30)
            resp.raise_for_status()

            total_len = int(resp.headers.get("content-length", 0))
            downloaded = 0
            buffer = io.BytesIO()

            for chunk in resp.iter_content(chunk_size=1024 * 64):
                if chunk:
                    buffer.write(chunk)
                    downloaded += len(chunk)
                    if total_len > 0:
                        pct = 0.05 + 0.85 * (downloaded / total_len)
                        progress_callback(
                            pct,
                            f"Downloading FFmpeg: {downloaded // (1024 * 1024)}MB / {total_len // (1024 * 1024)}MB",
                        )

            progress_callback(0.92, "Extracting FFmpeg binaries…")
            buffer.seek(0)

            with zipfile.ZipFile(buffer) as zf:
                for member in zf.namelist():
                    basename = os.path.basename(member)
                    if basename.lower() in ("ffmpeg.exe", "ffprobe.exe"):
                        target_file = dest_dir / basename
                        with zf.open(member) as src, open(target_file, "wb") as dst:
                            shutil.copyfileobj(src, dst)

            final_ffmpeg = dest_dir / "ffmpeg.exe"
            if final_ffmpeg.is_file():
                progress_callback(1.0, "FFmpeg installed successfully.")
                done_callback(True, str(final_ffmpeg))
            else:
                done_callback(False, "FFmpeg binary was not found in downloaded archive.")

        except Exception as exc:  # noqa: BLE001
            done_callback(False, f"Failed to download FFmpeg: {exc}")

    threading.Thread(target=_worker, daemon=True, name="seal-ffmpeg-download").start()
