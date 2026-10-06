"""
Seal Desktop – Comprehensive Unit Tests
Tests core downloader, sequential queue, pause/resume, deletion, i18n, updater, and settings.
"""

from __future__ import annotations

from src.core.downloader import (
    Downloader,
    DownloadPreferences,
    DownloadState,
    DownloadTask,
    _fmt_bytes,
    _fmt_eta,
    _fmt_speed,
)
from src.core.ffmpeg_utils import get_ffmpeg_path, is_ffmpeg_available
from src.core.i18n import get_language, is_rtl, set_language, t
from src.core.updater import _parse_version_tuple, is_newer_version

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
    assert prefs.video_container == "mp4"
    assert prefs.video_codec == "h264"
    assert prefs.embed_metadata is True
    assert prefs.concurrent_fragments == 4


# ──────────────────────────────────────────────
# Downloader state machine & Queue tests
# ──────────────────────────────────────────────


def test_downloader_cancel():
    dl = Downloader()
    dl.cancel_download("nonexistent-id")  # Should not raise


def test_downloader_get_tasks_empty():
    dl = Downloader()
    assert dl.get_tasks() == []


def test_downloader_clear_completed_empty():
    dl = Downloader()
    dl.clear_completed()  # Should not raise


def test_download_task_defaults():
    t_task = DownloadTask()
    assert t_task.state == DownloadState.IDLE
    assert t_task.progress == 0.0
    assert t_task.task_id != ""


def test_downloader_queue_and_controls():
    dl = Downloader()
    prefs = DownloadPreferences()

    # Queue an item (should remain in QUEUED state until queue runs)
    task_id = dl.queue_download("https://example.com/watch?v=123", prefs)
    tasks = dl.get_tasks()
    assert len(tasks) == 1
    assert tasks[0].task_id == task_id
    assert tasks[0].state == DownloadState.QUEUED
    assert dl.get_queued_count() == 1

    # Pause the queued item
    dl.pause_download(task_id)
    assert tasks[0].state == DownloadState.PAUSED
    assert dl.get_queued_count() == 0

    # Resume the item
    dl.resume_download(task_id)
    assert tasks[0].state == DownloadState.QUEUED
    assert dl.get_queued_count() == 1

    # Delete the task from queue
    dl.delete_task(task_id)
    assert len(dl.get_tasks()) == 0
    assert dl.get_queued_count() == 0


def test_downloader_queue_toggle():
    dl = Downloader()
    assert dl.is_queue_running() is False
    dl.start_queue()
    assert dl.is_queue_running() is True
    dl.pause_queue()
    assert dl.is_queue_running() is False


# ──────────────────────────────────────────────
# i18n Localization tests
# ──────────────────────────────────────────────


def test_i18n_translations():
    set_language("en")
    assert get_language() == "en"
    assert is_rtl() is False
    assert t("page_download_title") == "Download"
    assert "queue" in t("btn_add_queue").lower()

    # Switch to Arabic
    set_language("ar")
    assert get_language() == "ar"
    assert is_rtl() is True
    assert t("page_download_title") == "التحميل"
    assert "الانتظار" in t("btn_add_queue")

    # Formatting interpolation
    formatted = t("queue_summary", count=3, active=1)
    assert "3" in formatted and "1" in formatted

    # Fallback to key or en if unknown
    assert t("non_existent_key_xyz") == "non_existent_key_xyz"

    # Reset back to English
    set_language("en")
    assert get_language() == "en"


# ──────────────────────────────────────────────
# FFmpeg utilities tests
# ──────────────────────────────────────────────


def test_ffmpeg_utils():
    # Should safely return bool or None without exception
    assert isinstance(is_ffmpeg_available(), bool)
    path = get_ffmpeg_path()
    assert path is None or isinstance(path, str)


# ──────────────────────────────────────────────
# Updater version comparisons
# ──────────────────────────────────────────────


def test_updater_version_check():
    assert _parse_version_tuple("v1.2.0") == (1, 2, 0)
    assert _parse_version_tuple("1.0.0") == (1, 0, 0)
    assert _parse_version_tuple("v2.0-beta") == (2, 0)

    assert is_newer_version("1.2.1", "1.2.0") is True
    assert is_newer_version("1.2.0", "1.1.0") is True
    assert is_newer_version("v2.0.0", "1.1.0") is True
    assert is_newer_version("1.1.0", "1.1.0") is False
    assert is_newer_version("1.0.5", "1.1.0") is False


# ──────────────────────────────────────────────
# Settings tests
# ──────────────────────────────────────────────


def test_settings_get_default():
    from src.core.settings import Settings

    s = Settings()
    assert s.get("extract_audio") is False
    assert s.get("audio_format") == "mp3"
    assert s.get("language") in ("en", "ar")
    assert s.get("video_container") in ("mp4", "mkv")
    assert isinstance(s.get("output_dir"), str)


def test_settings_set_get():
    from src.core.settings import Settings

    s = Settings()
    s._data["test_key"] = "test_value"
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


def test_video_codec_opts():
    import threading

    dl = Downloader()
    task = DownloadTask()
    cancel_ev = threading.Event()
    pause_ev = threading.Event()

    # Default h264 produces format_sort prioritizing h264 video and m4a/aac audio
    prefs_h264 = DownloadPreferences(video_codec="h264")
    opts_h264 = dl._build_opts(task, prefs_h264, cancel_ev, pause_ev)
    assert opts_h264.get("format_sort") == ["vcodec:h264", "acodec:m4a"]

    # vp9
    prefs_vp9 = DownloadPreferences(video_codec="vp9")
    opts_vp9 = dl._build_opts(task, prefs_vp9, cancel_ev, pause_ev)
    assert opts_vp9.get("format_sort") == ["vcodec:vp9"]

    # av1
    prefs_av1 = DownloadPreferences(video_codec="av1")
    opts_av1 = dl._build_opts(task, prefs_av1, cancel_ev, pause_ev)
    assert opts_av1.get("format_sort") == ["vcodec:av01"]

    # auto (no format_sort override)
    prefs_auto = DownloadPreferences(video_codec="auto")
    opts_auto = dl._build_opts(task, prefs_auto, cancel_ev, pause_ev)
    assert "format_sort" not in opts_auto

