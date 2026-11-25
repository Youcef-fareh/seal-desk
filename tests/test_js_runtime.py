from __future__ import annotations

import sys

from src.core.js_runtime import get_javascript_runtimes


def test_discovers_available_system_javascript_runtime(monkeypatch):
    monkeypatch.setattr(
        "src.core.js_runtime.shutil.which",
        lambda executable: r"C:\Tools\node.exe" if executable == "node.exe" else None,
    )

    assert get_javascript_runtimes()["node"] == {"path": r"C:\Tools\node.exe"}


def test_discovers_bundled_deno(monkeypatch, tmp_path):
    deno_dir = tmp_path / "deno"
    deno_dir.mkdir()
    deno_path = deno_dir / "deno.exe"
    deno_path.write_bytes(b"test")
    monkeypatch.setattr("src.core.js_runtime.shutil.which", lambda _executable: None)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)

    assert get_javascript_runtimes()["deno"] == {"path": str(deno_path)}


def test_discovers_deno_install_directory(monkeypatch, tmp_path):
    deno_bin = tmp_path / "bin"
    deno_bin.mkdir()
    deno_path = deno_bin / "deno.exe"
    deno_path.write_bytes(b"test")
    monkeypatch.setattr("src.core.js_runtime.shutil.which", lambda _executable: None)
    monkeypatch.setenv("DENO_INSTALL", str(tmp_path))

    assert get_javascript_runtimes()["deno"] == {"path": str(deno_path)}
