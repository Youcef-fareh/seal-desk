"""
Seal Desktop – Comprehensive Unit Tests
Tests core downloader, sequential queue, pause/resume, deletion, i18n, updater, and settings.
"""

from __future__ import annotations

from pathlib import Path

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
from src.core.updater import CURRENT_VERSION, _parse_version_tuple, is_newer_version

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
    assert prefs.subtitles_only is False
    assert prefs.download_mode == "video"
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


def test_downloader_retry_reuses_failed_task(monkeypatch):
    dl = Downloader()
    before = DownloadTask(url="https://example.com/watch?v=before", state=DownloadState.QUEUED)
    task = DownloadTask(
        url="https://example.com/watch?v=retry",
        state=DownloadState.ERROR,
        error="temporary failure",
    )
    after = DownloadTask(url="https://example.com/watch?v=after", state=DownloadState.QUEUED)
    dl._tasks[before.task_id] = before
    dl._tasks[task.task_id] = task
    dl._tasks[after.task_id] = after
    dl._queue.extend((before.task_id, task.task_id, after.task_id))
    monkeypatch.setattr(dl, "start_queue", lambda: None)

    assert dl.retry_download(task.task_id) is True
    assert dl.retry_download(task.task_id) is False
    assert len(dl.get_tasks()) == 3
    assert task.state == DownloadState.QUEUED
    assert dl.get_queued_count() == 3
    assert dl._queue.count(task.task_id) == 1
    assert dl.get_queue_order() == [before.task_id, task.task_id, after.task_id]


def test_downloader_reorders_only_queued_tasks():
    dl = Downloader()
    first = DownloadTask(state=DownloadState.QUEUED)
    active = DownloadTask(state=DownloadState.DOWNLOADING)
    second = DownloadTask(state=DownloadState.QUEUED)
    third = DownloadTask(state=DownloadState.QUEUED)
    dl._tasks = {task.task_id: task for task in (first, active, second, third)}
    dl._queue = [first.task_id, active.task_id, second.task_id, third.task_id]

    assert dl.move_queue_item(third.task_id, 0) is True
    assert dl.get_queue_order() == [third.task_id, first.task_id, second.task_id]
    assert dl.reorder_queue(first.task_id, 1) is True
    assert dl.get_queue_order() == [third.task_id, second.task_id, first.task_id]
    assert dl.get_queue_positions() == {
        third.task_id: 1,
        second.task_id: 2,
        first.task_id: 3,
    }


def test_pending_queue_is_restored_and_ordered(monkeypatch):
    class FakeSettings:
        def __init__(self):
            self.values = {"pending_downloads": []}

        def get(self, key, default=None):
            return self.values.get(key, default)

        def set(self, key, value):
            self.values[key] = value

    fake_settings = FakeSettings()
    monkeypatch.setattr("src.core.downloader.settings", fake_settings)

    original = Downloader(persist_queue=True)
    first = DownloadTask(url="https://example.com/1", title="First", state=DownloadState.QUEUED)
    second = DownloadTask(
        url="https://example.com/2",
        title="Second",
        state=DownloadState.PAUSED,
        prefs=DownloadPreferences(extract_audio=True),
    )
    original._tasks = {first.task_id: first, second.task_id: second}
    original._queue = [first.task_id, second.task_id]
    original._persist_queue()

    restored = Downloader(persist_queue=True)

    assert restored.get_queue_order() == [first.task_id]
    assert [task.title for task in restored.get_tasks()] == ["First", "Second"]
    assert restored.get_tasks()[1].state == DownloadState.PAUSED
    assert restored.get_tasks()[1].is_audio is True


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
    assert CURRENT_VERSION == "1.5.5"
    assert is_newer_version("v1.5.1") is False
    assert is_newer_version("v1.5.2") is False
    assert is_newer_version("v1.5.3") is False
    assert is_newer_version("v1.5.4") is False
    assert is_newer_version("v1.5.6") is True

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


def test_settings_get_default(monkeypatch, tmp_path):
    from src.core.settings import Settings

    monkeypatch.setattr("src.core.settings._config_path", lambda: tmp_path / "settings.json")
    s = Settings()
    assert s.get("download_mode") == "video"
    assert s.get("subtitles_only") is False
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


def test_video_without_ffmpeg_never_selects_separate_streams(monkeypatch):
    import threading

    monkeypatch.setattr("src.core.downloader.get_ffmpeg_path", lambda: None)

    dl = Downloader()
    task = DownloadTask()
    opts = dl._build_opts(
        task,
        DownloadPreferences(video_quality="best"),
        threading.Event(),
        threading.Event(),
    )

    assert opts["format"] == "best[ext=mp4]/best"
    assert "+" not in opts["format"]
    assert "merge_output_format" not in opts


def test_split_stream_download_requires_merged_file(tmp_path):
    import pytest
    import yt_dlp

    task = DownloadTask(output_path=str(tmp_path / "video.f397.mp4"))
    Path(task.output_path).touch()
    info = {"requested_formats": [{"format_id": "397"}, {"format_id": "251"}]}

    with pytest.raises(yt_dlp.utils.DownloadError, match="did not merge"):
        Downloader._validate_download_result(info, task, DownloadPreferences())


def test_split_stream_download_accepts_existing_merged_file(tmp_path):
    task = DownloadTask(output_path=str(tmp_path / "video.mp4"))
    Path(task.output_path).touch()
    info = {"requested_formats": [{"format_id": "397"}, {"format_id": "251"}]}

    Downloader._validate_download_result(info, task, DownloadPreferences())


def test_prefetch_task_info(monkeypatch):
    class FakeSettings:
        def __init__(self):
            self.values = {"pending_downloads": []}

        def get(self, key, default=None):
            return self.values.get(key, default)

        def set(self, key, value):
            self.values[key] = value

    fake_settings = FakeSettings()
    monkeypatch.setattr("src.core.downloader.settings", fake_settings)
    dl = Downloader(persist_queue=True)
    prefs = DownloadPreferences(video_codec="h264", video_quality="1080")
    task = DownloadTask(url="https://example.com/test", prefs=prefs, state=DownloadState.QUEUED)
    dl._tasks[task.task_id] = task
    dl._queue.append(task.task_id)

    fake_info = {
        "_type": "playlist",
        "title": "Awesome Sample Video",
        "uploader": "Test Channel",
        "duration": 180,
        "thumbnail": "https://example.com/thumb.jpg",
        "resolution": "1920x1080",
        "height": 1080,
        "filesize_approx": 52428800,
    }

    class FakeYDL:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def extract_info(self, url, download=False):
            return fake_info

    monkeypatch.setattr("yt_dlp.YoutubeDL", FakeYDL)

    dl._prefetch_task_info(task.task_id)

    updated = dl._tasks[task.task_id]
    assert updated.title == "Awesome Sample Video"
    assert updated.uploader == "Test Channel"
    assert updated.duration_str == "03:00"
    assert updated.quality_label == "1920x1080 · H264"
    assert "~50.0 MB" in updated.estimated_size
    assert updated.is_playlist is True
    assert fake_settings.get("pending_downloads")[0]["title"] == "Awesome Sample Video"


def test_subtitles_build_opts():
    import threading

    dl = Downloader()
    prefs = DownloadPreferences(
        subtitles_only=True,
        subtitle_source="both",
        subtitle_languages="en,ar",
    )
    task = DownloadTask(url="https://example.com/watch?v=123", prefs=prefs)
    opts = dl._build_opts(task, prefs, threading.Event(), threading.Event())

    assert opts.get("skip_download") is True
    assert opts.get("writesubtitles") is True
    assert opts.get("writeautomaticsub") is True
    assert opts.get("subtitleslangs") == ["en", "ar"]
    assert opts.get("convertsubtitles") == "srt"


def test_subtitles_retry_youtube_reload_error(monkeypatch):
    import threading

    import yt_dlp

    dl = Downloader()
    prefs = DownloadPreferences(subtitles_only=True)
    task = DownloadTask(url="https://example.com/watch?v=subs", prefs=prefs)
    dl._tasks[task.task_id] = task
    attempts = 0

    class FakeYDL:
        def __init__(self, opts):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def extract_info(self, url, download=False):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise yt_dlp.utils.DownloadError("The page needs to be reloaded.")
            return {"title": "Subtitled video"}

        def download(self, urls):
            pass

    monkeypatch.setattr("yt_dlp.YoutubeDL", FakeYDL)
    dl._worker(task, prefs, threading.Event(), threading.Event())

    assert attempts == 2
    assert task.state == DownloadState.COMPLETED
    assert task.title == "Subtitled video"


def test_embedded_subtitle_failure_retries_media_without_subtitles(monkeypatch):
    import threading

    import yt_dlp

    dl = Downloader()
    prefs = DownloadPreferences(embed_subtitles=True)
    task = DownloadTask(url="https://example.com/watch?v=video", prefs=prefs)
    dl._tasks[task.task_id] = task
    options_seen = []

    class FakeYDL:
        def __init__(self, opts):
            options_seen.append(opts)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def extract_info(self, url, download=False):
            return {"title": "Video without subtitles"}

        def download(self, urls):
            if options_seen[-1].get("writesubtitles"):
                raise yt_dlp.utils.PostProcessingError("Unable to embed subtitles")

    monkeypatch.setattr("yt_dlp.YoutubeDL", FakeYDL)
    dl._worker(task, prefs, threading.Event(), threading.Event())

    assert len(options_seen) == 2
    assert options_seen[0].get("writesubtitles") is True
    assert not options_seen[1].get("writesubtitles")
    assert task.state == DownloadState.COMPLETED
    assert task.subtitle_warning is True
    assert task.title == "Video without subtitles"


def test_embedded_subtitle_http_error_survives_cookie_save_failure(monkeypatch):
    import threading

    import yt_dlp

    dl = Downloader()
    prefs = DownloadPreferences(embed_subtitles=True, subtitle_languages="ar")
    task = DownloadTask(url="https://example.com/watch?v=video", prefs=prefs)
    dl._tasks[task.task_id] = task
    options_seen = []

    class FakeYDL:
        def __init__(self, opts):
            self.opts = opts
            options_seen.append(opts)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            if self.opts.get("writesubtitles"):
                raise OSError(9, "Bad file descriptor")

        def extract_info(self, url, download=False):
            return {"title": "Video with subtitles", "subtitles": {"ar": [{}]}}

        def download(self, urls):
            if self.opts.get("writesubtitles"):
                raise yt_dlp.utils.DownloadError(
                    "Unable to download video subtitles for 'ar': HTTP Error 429: Too Many Requests"
                )

    monkeypatch.setattr("yt_dlp.YoutubeDL", FakeYDL)
    dl._worker(task, prefs, threading.Event(), threading.Event())

    assert len(options_seen) == 2
    assert options_seen[0].get("writesubtitles") is True
    assert not options_seen[1].get("writesubtitles")
    assert task.state == DownloadState.COMPLETED
    assert task.subtitle_warning is True


def test_missing_subtitles_still_completes_media_download(monkeypatch):
    import threading

    dl = Downloader()
    prefs = DownloadPreferences(embed_subtitles=True, subtitle_languages="en")
    task = DownloadTask(url="https://example.com/watch?v=no-subs", prefs=prefs)
    dl._tasks[task.task_id] = task
    options_seen = []

    class FakeYDL:
        def __init__(self, opts):
            options_seen.append(opts)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def extract_info(self, url, download=False):
            return {"title": "No captions in source"}

        def download(self, urls):
            pass

    monkeypatch.setattr("yt_dlp.YoutubeDL", FakeYDL)
    dl._worker(task, prefs, threading.Event(), threading.Event())

    assert len(options_seen) == 2
    assert options_seen[0].get("writesubtitles") is True
    assert not options_seen[1].get("writesubtitles")
    assert task.state == DownloadState.COMPLETED
    assert task.subtitle_warning is True


def test_playlist_without_subtitles_retries_without_embedding(monkeypatch):
    import threading

    dl = Downloader()
    prefs = DownloadPreferences(embed_subtitles=True, subtitle_languages="en")
    task = DownloadTask(url="https://example.com/playlist?id=123", prefs=prefs)
    dl._tasks[task.task_id] = task
    options_seen = []

    class FakeYDL:
        def __init__(self, opts):
            options_seen.append(opts)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def extract_info(self, url, download=False):
            return {"_type": "playlist", "entries": [{"title": "No captions"}]}

        def download(self, urls):
            pass

    monkeypatch.setattr("yt_dlp.YoutubeDL", FakeYDL)
    dl._worker(task, prefs, threading.Event(), threading.Event())

    assert len(options_seen) == 2
    assert options_seen[0].get("writesubtitles") is True
    assert not options_seen[1].get("writesubtitles")
    assert task.state == DownloadState.COMPLETED
    assert task.subtitle_warning is True


def test_video_download_does_not_retry_youtube_reload_error(monkeypatch):
    import threading

    import yt_dlp

    dl = Downloader()
    prefs = DownloadPreferences()
    task = DownloadTask(url="https://example.com/watch?v=video", prefs=prefs)
    dl._tasks[task.task_id] = task
    attempts = 0

    class FakeYDL:
        def __init__(self, opts):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def extract_info(self, url, download=False):
            nonlocal attempts
            attempts += 1
            raise yt_dlp.utils.DownloadError("The page needs to be reloaded.")

    monkeypatch.setattr("yt_dlp.YoutubeDL", FakeYDL)
    dl._worker(task, prefs, threading.Event(), threading.Event())

    assert attempts == 1
    assert task.state == DownloadState.ERROR


def test_subtitles_prefetch(monkeypatch):
    dl = Downloader()
    prefs = DownloadPreferences(subtitles_only=True, subtitle_languages="en,fr")
    task_id = dl.queue_download("https://example.com/watch?v=subs", prefs)
    task = dl._tasks[task_id]
    assert task.is_subtitles is True

    fake_info = {
        "title": "Subtitled Video",
        "uploader": "Sub Channel",
        "duration": 120,
    }

    class FakeYDL:
        def __init__(self, opts):
            self.opts = opts

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def extract_info(self, url, download=False):
            return fake_info

    monkeypatch.setattr("yt_dlp.YoutubeDL", FakeYDL)
    dl._prefetch_task_info(task.task_id)

    updated = dl._tasks[task.task_id]
    assert updated.title == "Subtitled Video"
    assert updated.is_subtitles is True
    assert "Subtitles" in updated.quality_label
