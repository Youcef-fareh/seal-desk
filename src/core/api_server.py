"""
Seal Desktop – Browser Extension API Server
Provides a local HTTP REST API for browser extensions (Chrome, Edge, Firefox, Brave).
Listens on 127.0.0.1:48123 to receive download and queuing requests.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from .downloader import DownloadPreferences, downloader
from .logger import get_logger
from .notifications import send_notification
from .settings import settings

DEFAULT_API_PORT = 48123


class _ApiRequestHandler(BaseHTTPRequestHandler):
    """Handles HTTP requests from browser extensions."""

    def log_message(self, format: str, *args: Any) -> None:
        # Route HTTP server logs to Seal logger rather than default stderr
        get_logger().debug(f"[API Server] {format % args}")

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")

    def _send_json_response(self, code: int, data: dict[str, Any]) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path in ("/api/ping", "/ping"):
            self._send_json_response(200, {
                "status": "ok",
                "app": "Seal Desktop",
                "version": "1.4.0",
                "message": "Seal Desktop companion server is active",
            })
            return

        if path in ("/api/status", "/status"):
            tasks = downloader.get_tasks()
            # DownloadState uses auto() ints — compare by name, not value string
            q_count = sum(1 for t in tasks if t.state.name == "QUEUED")
            active_count = sum(
                1 for t in tasks
                if t.state.name in ("DOWNLOADING", "DOWNLOADING_PLAYLIST", "FETCHING_INFO")
            )
            self._send_json_response(200, {
                "status": "ok",
                "app": "Seal Desktop",
                "queue_running": downloader.is_queue_running(),
                "total_tasks": len(tasks),
                "queued_count": q_count,
                "active_count": active_count,
            })
            return

        self._send_json_response(404, {"status": "error", "message": "Endpoint not found"})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path in ("/api/download", "/download", "/api/queue", "/queue"):
            try:
                raw_length = self.headers.get("Content-Length", "0") or "0"
                length = max(0, int(raw_length))
                raw_data = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
                payload = json.loads(raw_data) if raw_data.strip() else {}
            except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as e:
                self._send_json_response(400, {"status": "error", "message": f"Invalid request body: {e}"})
                return
            except Exception as e:
                self._send_json_response(500, {"status": "error", "message": f"Server read error: {e}"})
                return

            url = (payload.get("url") or "").strip()
            if not url or not (url.startswith("http://") or url.startswith("https://")):
                self._send_json_response(400, {"status": "error", "message": "Invalid or missing 'url' parameter"})
                return

            # Construct preferences, combining request payload with user settings
            extract_audio = bool(payload.get("extract_audio", payload.get("is_audio", False)))
            audio_format = str(payload.get("audio_format") or settings.get("audio_format", "mp3"))
            video_quality = str(payload.get("video_quality", payload.get("quality", "best")))
            video_container = str(payload.get("video_container") or settings.get("video_container", "mp4"))
            embed_subtitles = bool(payload.get("embed_subtitles", settings.get("embed_subtitles", False)))

            # Safely resolve output_dir — settings.get may return None if key not set yet
            from pathlib import Path as _Path
            _default_dir = str(_Path.home() / "Downloads" / "Seal")
            _output_dir = settings.get("output_dir") or _default_dir

            prefs = DownloadPreferences(
                extract_audio=extract_audio,
                audio_format=audio_format,
                video_quality=video_quality,
                video_container=video_container,
                embed_subtitles=embed_subtitles,
                output_dir=_output_dir,
                embed_metadata=bool(settings.get("embed_metadata", True)),
                embed_thumbnail=bool(settings.get("embed_thumbnail", True)),
                proxy=str(settings.get("proxy") or ""),
                rate_limit=str(settings.get("rate_limit") or ""),
                concurrent_fragments=int(settings.get("concurrent_fragments") or 4),
                cookies_file=str(settings.get("cookies_file") or ""),
            )

            # Auto-start or queue?
            auto_start = payload.get("auto_start", path not in ("/api/queue", "/queue"))

            if auto_start:
                task_id = downloader.start_download(url, prefs)
            else:
                task_id = downloader.queue_download(url, prefs)

            server_instance: ApiServer | None = getattr(self.server, "_seal_server", None)
            if server_instance and server_instance.on_task_added:
                try:
                    server_instance.on_task_added(task_id)
                except Exception as e:
                    get_logger().error(f"[API Server] Error invoking on_task_added callback: {e}")

            title = payload.get("title", "")
            if settings.get("desktop_notifications", True):
                desc = f"Received from browser: {title[:40] if title else url[:40]}"
                send_notification("Seal Desktop Companion", desc)

            self._send_json_response(200, {
                "status": "success",
                "task_id": task_id,
                "auto_start": auto_start,
                "message": "Task queued successfully" if not auto_start else "Download started successfully",
            })
            return

        self._send_json_response(404, {"status": "error", "message": "Endpoint not found"})


class ApiServer:
    """Lightweight background HTTP daemon for browser extension integration."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = DEFAULT_API_PORT,
        on_task_added: Callable[[str], None] | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.on_task_added = on_task_added
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> bool:
        if self._running:
            return True
        try:
            self._httpd = ThreadingHTTPServer((self.host, self.port), _ApiRequestHandler)
            self._httpd._seal_server = self
            self._running = True
            self._thread = threading.Thread(
                target=self._run,
                daemon=True,
                name="seal-api-server",
            )
            self._thread.start()
            get_logger().info(f"Extension API server started on http://{self.host}:{self.port}")
            return True
        except OSError as exc:
            get_logger().warning(f"Could not bind API server to {self.host}:{self.port} (already in use?): {exc}")
            self._running = False
            return False

    def _run(self) -> None:
        if not self._httpd:
            return
        try:
            self._httpd.serve_forever()
        except Exception:
            pass
        finally:
            self._running = False

    def stop(self) -> None:
        self._running = False
        if self._httpd:
            try:
                self._httpd.shutdown()
                self._httpd.server_close()
            except Exception:
                pass
            self._httpd = None

    def is_running(self) -> bool:
        return self._running
