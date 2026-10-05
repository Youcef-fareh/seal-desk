"""
Seal Desktop - Settings / Preferences Manager
Persists user settings to a JSON file in the platform's config directory.
"""

from __future__ import annotations

import json
import os
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
    # Download
    "output_dir": str(Path.home() / "Downloads" / "Seal"),
    "output_template": "%(title).200B.%(ext)s",
    "playlist_subdir": True,
    # Format
    "extract_audio": False,
    "audio_format": "mp3",
    "video_quality": "best",
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
    # UI
    "theme": "dark",
    "accent_color": "#8B5CF6",   # violet-500
    "window_width": 1100,
    "window_height": 720,
    "window_x": -1,
    "window_y": -1,
    # History
    "history": [],
}


class Settings:
    def __init__(self) -> None:
        self._path = _config_path()
        self._data: dict[str, Any] = dict(DEFAULTS)
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                with open(self._path, encoding="utf-8") as f:
                    loaded = json.load(f)
                self._data.update(loaded)
            except Exception:  # noqa: BLE001
                pass  # Use defaults

    def save(self) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, DEFAULTS.get(key, default))

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    def update(self, mapping: dict[str, Any]) -> None:
        self._data.update(mapping)
        self.save()

    # Convenience helpers
    def add_history(self, entry: dict[str, Any]) -> None:
        history: list = self._data.get("history", [])
        # Avoid duplicates by URL
        history = [h for h in history if h.get("url") != entry.get("url")]
        history.insert(0, entry)
        history = history[:200]   # cap at 200 entries
        self._data["history"] = history
        self.save()

    def clear_history(self) -> None:
        self._data["history"] = []
        self.save()

    def get_history(self) -> list[dict]:
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


# Singleton
settings = Settings()
