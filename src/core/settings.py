"""
Seal Desktop - Settings / Preferences Manager
Persists user settings to a JSON file in the platform's config directory.
"""

from __future__ import annotations

import atexit
import json
import threading
from pathlib import Path
from typing import Any

import platformdirs

APP_NAME = "SealDesktop"
APP_AUTHOR = "SealDesktop"


def _config_path() -> Path:
    cfg_dir = Path(platformdirs.user_config_dir(APP_NAME, APP_AUTHOR))
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "settings.json"


DEFAULTS: dict[str, Any] = {
    # Localization
    "language": "en",  # "en" | "ar"
    # Download
    "output_dir": str(Path.home() / "Downloads" / "Seal"),
    "output_template": "%(title).200B.%(ext)s",
    "playlist_subdir": True,
    "restrict_filenames": False,
    # Format & Merging
    "extract_audio": False,
    "audio_format": "mp3",
    "video_quality": "best",
    "video_container": "mp4",  # "mp4" | "mkv"
    "video_codec": "h264",  # "h264" | "auto" | "vp9" | "av1"
    "auto_merge": True,
    # Post-processing
    "embed_metadata": True,
    "embed_thumbnail": True,
    "embed_subtitles": False,
    "subtitle_languages": "en",
    # Network
    "proxy": "",
    "rate_limit": "",
    "concurrent_fragments": 4,
    "use_aria2c": False,
    "cookies_file": "",
    # Updates
    "auto_check_updates": True,
    # UI
    "theme": "dark",
    "accent_color": "#8B5CF6",  # violet-500
    "window_width": 1100,
    "window_height": 740,
    "window_x": -1,
    "window_y": -1,
    # History
    "history": [],
}


class Settings:
    def __init__(self) -> None:
        self._path = _config_path()
        self._data: dict[str, Any] = dict(DEFAULTS)
        self._lock = threading.Lock()
        self._save_timer: threading.Timer | None = None
        self._load()
        atexit.register(self.save)

    def _load(self) -> None:
        if self._path.exists():
            try:
                with open(self._path, encoding="utf-8") as f:
                    loaded = json.load(f)
                self._data.update(loaded)
            except Exception:  # noqa: BLE001
                pass  # Use defaults

    def _schedule_save(self) -> None:
        with self._lock:
            if self._save_timer and self._save_timer.is_alive():
                self._save_timer.cancel()
            self._save_timer = threading.Timer(0.3, self.save)
            self._save_timer.daemon = True
            self._save_timer.start()

    def save(self) -> None:
        with self._lock:
            if self._save_timer and self._save_timer.is_alive():
                self._save_timer.cancel()
                self._save_timer = None
            try:
                with open(self._path, "w", encoding="utf-8") as f:
                    json.dump(self._data, f, indent=2, ensure_ascii=False)
            except Exception:  # noqa: BLE001
                pass

    def flush(self) -> None:
        self.save()

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, DEFAULTS.get(key, default))

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if self._data.get(key) == value:
                return
            self._data[key] = value
        self._schedule_save()

    def update(self, mapping: dict[str, Any]) -> None:
        changed = False
        with self._lock:
            for k, v in mapping.items():
                if self._data.get(k) != v:
                    self._data[k] = v
                    changed = True
        if changed:
            self._schedule_save()

    # Convenience helpers
    def add_history(self, entry: dict[str, Any]) -> None:
        with self._lock:
            history: list = self._data.get("history", [])
            cleaned_entry = dict(entry)
            if "downloaded_at" not in cleaned_entry:
                from datetime import datetime

                cleaned_entry["downloaded_at"] = datetime.now().isoformat()
            # Avoid duplicates by URL
            history = [h for h in history if h.get("url") != cleaned_entry.get("url")]
            history.insert(0, cleaned_entry)
            history = history[:200]  # cap at 200 entries
            self._data["history"] = history
        self._schedule_save()

    def clear_history(self) -> None:
        with self._lock:
            self._data["history"] = []
        self._schedule_save()

    def get_history(self) -> list[dict]:
        with self._lock:
            return list(self._data.get("history", []))

    @property
    def output_dir(self) -> str:
        return self.get("output_dir")

    @property
    def theme(self) -> str:
        return self.get("theme")

    @property
    def accent_color(self) -> str:
        return self.get("accent_color")

    @property
    def language(self) -> str:
        return self.get("language")


# Singleton
settings = Settings()
