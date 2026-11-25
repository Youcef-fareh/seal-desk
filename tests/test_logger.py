from __future__ import annotations

from pathlib import Path

import pytest

from src.core.logger import export_sanitized_log, sanitize_log_text


def test_sanitize_log_redacts_query_credentials_and_home(monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: Path("C:/Users/Test"))
    lower_home = str(Path("C:/Users/Test")).lower()
    text = (
        "Fetching https://example.com/watch?v=123&token=secret\n"
        "Cookie: session=secret\n"
        f"Output: {lower_home}{Path('/Downloads/video.mp4')}\n"
        "Credentials: api_key=secret-value\n"
    )

    sanitized = sanitize_log_text(text)

    assert "token=secret" not in sanitized
    assert "session=secret" not in sanitized
    assert "secret-value" not in sanitized
    assert str(Path("C:/Users/Test")) not in sanitized
    assert "[REDACTED]" in sanitized
    assert "https://example.com/watch?<query-redacted>" in sanitized
    assert f"~{Path('/Downloads/video.mp4')}" in sanitized


def test_export_sanitized_log(monkeypatch, tmp_path):
    source = tmp_path / "source.log"
    source.write_text("https://example.com/?token=secret", encoding="utf-8")
    destination = tmp_path / "diagnostics.txt"
    monkeypatch.setattr("src.core.logger.LOG_FILE_PATH", source)

    assert export_sanitized_log(destination) == destination
    assert "secret" not in destination.read_text(encoding="utf-8")


def test_export_does_not_overwrite_original_log(monkeypatch, tmp_path):
    source = tmp_path / "source.log"
    original = "https://example.com/?token=secret"
    source.write_text(original, encoding="utf-8")
    monkeypatch.setattr("src.core.logger.LOG_FILE_PATH", source)

    with pytest.raises(OSError, match="original application log"):
        export_sanitized_log(source)

    assert source.read_text(encoding="utf-8") == original
