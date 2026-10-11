"""
Seal Desktop – Application Logger
Rotating file logger that captures backend (yt-dlp) output, download
events, and application errors to a persistent log file.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import platformdirs

APP_NAME = "SealDesktop"
APP_AUTHOR = "SealDesktop"

_log_dir = Path(platformdirs.user_log_dir(APP_NAME, APP_AUTHOR))
_log_dir.mkdir(parents=True, exist_ok=True)
LOG_FILE_PATH = _log_dir / "seal_desktop.log"

_logger: logging.Logger | None = None


def get_logger() -> logging.Logger:
    global _logger
    if _logger is not None:
        return _logger

    _logger = logging.getLogger("SealDesktop")
    _logger.setLevel(logging.DEBUG)

    # Rotating file: 2 MB max, keep 3 backups
    fh = RotatingFileHandler(
        LOG_FILE_PATH,
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    _logger.addHandler(fh)

    # Also surface WARNING+ to stderr during development
    if not getattr(sys, "frozen", False):
        sh = logging.StreamHandler(sys.stderr)
        sh.setLevel(logging.WARNING)
        sh.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        _logger.addHandler(sh)

    return _logger


class YtDlpLogger:
    """Adapter that routes yt-dlp's own logging into Seal's logger."""

    def debug(self, msg: str) -> None:  # noqa: D401
        get_logger().debug("[yt-dlp] %s", msg)

    def info(self, msg: str) -> None:
        get_logger().info("[yt-dlp] %s", msg)

    def warning(self, msg: str) -> None:
        get_logger().warning("[yt-dlp] %s", msg)

    def error(self, msg: str) -> None:
        get_logger().error("[yt-dlp] %s", msg)
