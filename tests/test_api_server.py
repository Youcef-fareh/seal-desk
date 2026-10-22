"""
Unit tests for the Browser Extension Companion API Server.
"""

from __future__ import annotations

import json
import socket
import urllib.request
import urllib.error
import pytest

from src.core.api_server import ApiServer
from src.core.downloader import downloader
from src.core.updater import CURRENT_VERSION


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def api_server():
    port = _get_free_port()
    added_tasks = []

    def on_task(task_id: str):
        added_tasks.append(task_id)

    server = ApiServer(host="127.0.0.1", port=port, on_task_added=on_task)
    assert server.start() is True
    yield server, port, added_tasks
    server.stop()


def test_api_ping(api_server):
    _, port, _ = api_server
    url = f"http://127.0.0.1:{port}/api/ping"
    with urllib.request.urlopen(url, timeout=5) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "ok"
        assert data["app"] == "Seal Desktop"
        assert data["version"] == CURRENT_VERSION


def test_api_status(api_server):
    _, port, _ = api_server
    url = f"http://127.0.0.1:{port}/api/status"
    with urllib.request.urlopen(url, timeout=5) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "ok"
        assert "queue_running" in data
        assert "total_tasks" in data


def test_api_download_post(api_server):
    _, port, added_tasks = api_server
    url = f"http://127.0.0.1:{port}/api/download"
    payload = json.dumps({
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "title": "Never Gonna Give You Up",
        "extract_audio": False,
        "video_quality": "1080",
        "auto_start": False,  # Keep it queued for test safety
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "success"
        assert "task_id" in data
        assert data["task_id"] in added_tasks

        # Verify task is in downloader
        task = next((t for t in downloader.get_tasks() if t.task_id == data["task_id"]), None)
        assert task is not None
        assert task.url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_api_download_invalid_url(api_server):
    _, port, _ = api_server
    url = f"http://127.0.0.1:{port}/api/download"
    payload = json.dumps({"url": "invalid_url_not_http"}).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req, timeout=5)
    assert exc_info.value.code == 400


def test_api_options_cors(api_server):
    _, port, _ = api_server
    url = f"http://127.0.0.1:{port}/api/download"
    req = urllib.request.Request(url, method="OPTIONS")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        assert resp.headers.get("Access-Control-Allow-Origin") == "*"
        assert "POST" in resp.headers.get("Access-Control-Allow-Methods", "")


def test_api_download_subtitles_post(api_server):
    _, port, added_tasks = api_server
    url = f"http://127.0.0.1:{port}/api/download"
    payload = json.dumps({
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "title": "Never Gonna Give You Up Subs",
        "download_mode": "subtitles",
        "subtitle_source": "both",
        "subtitle_languages": "en,ar",
        "auto_start": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "success"
        assert "task_id" in data
        assert data["task_id"] in added_tasks

        task = next((t for t in downloader.get_tasks() if t.task_id == data["task_id"]), None)
        assert task is not None
        assert task.is_subtitles is True
        assert task.prefs.subtitles_only is True
        assert task.prefs.subtitle_source == "both"
        assert task.prefs.subtitle_languages == "en,ar"
