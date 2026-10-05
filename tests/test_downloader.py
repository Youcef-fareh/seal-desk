"""
Seal Desktop – Core Downloader Tests
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.core.downloader import (
    DownloadPreferences,
    DownloadState,
    DownloadTask,
    Downloader,
    _fmt_bytes,
    _fmt_eta,
    _fmt_speed,
)


# ──────────────────────────────────────────────
# Utility function tests
# ──────────────────────────────────────────────


def test_fmt_bytes():
    assert _fmt_bytes(0) == "0.0 B"
    assert _fmt_bytes(1024) == "1.0 KB"
    assert _fmt_bytes(1024 * 1024) == "1.0 MB"
    assert _fmt_bytes(None) == ""


def test_fmt_speed():
    assert _fmt_speed(None) == ""
    assert "/s" in _fmt_speed(1024 * 512)


def test_fmt_eta():
    assert _fmt_eta(None) == ""
    assert _fmt_eta(61) == "01:01"
    assert _fmt_eta(3661) == "1:01:01"
    assert _fmt_eta(0) == "00:00"


# ──────────────────────────────────────────────
# DownloadPreferences defaults
# ──────────────────────────────────────────────


def test_download_preferences_defaults():
    prefs = DownloadPreferences()
    assert prefs.extract_audio is False
    assert prefs.audio_format == "mp3"
    assert prefs.video_quality == "best"
    assert prefs.embed_metadata is True
    assert prefs.concurrent_fragments == 4


# ──────────────────────────────────────────────
# Downloader state machine
# ──────────────────────────────────────────────


def test_downloader_cancel():
    dl = Downloader()
    dl.cancel_download("nonexistent-id")   # Should not raise


def test_downloader_get_tasks_empty():
    dl = Downloader()
    assert dl.get_tasks() == []


def test_downloader_clear_completed_empty():
    dl = Downloader()
    dl.clear_completed()    # Should not raise


def test_download_task_defaults():
    t = DownloadTask()
    assert t.state == DownloadState.IDLE
    assert t.progress == 0.0
    assert t.task_id != ""


# ──────────────────────────────────────────────
# Settings tests
# ──────────────────────────────────────────────


def test_settings_get_default():
    from src.core.settings import Settings
    s = Settings()
    assert s.get("extract_audio") is False
    assert s.get("audio_format") == "mp3"
    assert isinstance(s.get("output_dir"), str)


def test_settings_set_get():
    from src.core.settings import Settings
    s = Settings()
    s._data["test_key"] = "test_value"    # direct injection, no file I/O
    assert s.get("test_key") == "test_value"


def test_settings_history():
    from src.core.settings import Settings
    s = Settings()
    s._data["history"] = []
    s.add_history({"url": "https://example.com", "title": "Test"})
    h = s.get_history()
    assert len(h) == 1
    assert h[0]["url"] == "https://example.com"

    # Duplicate URL should be deduped
    s.add_history({"url": "https://example.com", "title": "Test"})
    assert len(s.get_history()) == 1


def test_settings_clear_history():
    from src.core.settings import Settings
    s = Settings()
    s._data["history"] = [{"url": "x"}]
    s.clear_history()
    assert s.get_history() == []
