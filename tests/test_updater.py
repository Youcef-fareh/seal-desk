from __future__ import annotations

import threading

from src.core import updater


def test_update_check_prefers_setup_installer(monkeypatch):
    monkeypatch.setattr(
        updater,
        "get_latest_release",
        lambda _repo: {
            "tag_name": "v99.0.0",
            "assets": [
                {
                    "name": "SealDesktop.exe",
                    "browser_download_url": "https://example.com/portable.exe",
                },
                {
                    "name": "SealDesktop-99.0.0-Setup.exe",
                    "browser_download_url": "https://example.com/setup.exe",
                },
            ],
        },
    )
    result = []
    completed = threading.Event()

    updater.check_app_update(lambda info, error: (result.append((info, error)), completed.set()))

    assert completed.wait(2)
    info, error = result[0]
    assert error is None
    assert info is not None
    assert info.asset_name == "SealDesktop-99.0.0-Setup.exe"
    assert info.asset_url == "https://example.com/setup.exe"


def test_download_app_installer_saves_complete_file(monkeypatch, tmp_path):
    class FakeResponse:
        headers = {"content-length": "9"}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

        def raise_for_status(self):
            pass

        def iter_content(self, chunk_size):
            assert chunk_size == 1024 * 64
            yield b"setup "
            yield b"exe"

    monkeypatch.setattr(updater.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(updater.requests, "get", lambda *args, **kwargs: FakeResponse())
    results = []
    completed = threading.Event()

    updater.download_app_installer(
        "https://example.com/setup.exe",
        "SealDesktop-Setup.exe",
        lambda _progress, _message: None,
        lambda success, result: (results.append((success, result)), completed.set()),
    )

    assert completed.wait(2)
    success, path = results[0]
    assert success is True
    assert (tmp_path / "SealDesktopUpdates" / "SealDesktop-Setup.exe").read_bytes() == b"setup exe"
    assert path.endswith("SealDesktop-Setup.exe")


def test_download_app_installer_rejects_incomplete_file(monkeypatch, tmp_path):
    class FakeResponse:
        headers = {"content-length": "20"}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

        def raise_for_status(self):
            pass

        def iter_content(self, chunk_size):
            yield b"short"

    monkeypatch.setattr(updater.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(updater.requests, "get", lambda *args, **kwargs: FakeResponse())
    results = []
    completed = threading.Event()

    updater.download_app_installer(
        "https://example.com/setup.exe",
        "SealDesktop-Setup.exe",
        lambda _progress, _message: None,
        lambda success, result: (results.append((success, result)), completed.set()),
    )

    assert completed.wait(2)
    success, error = results[0]
    assert success is False
    assert "Incomplete installer download" in error
    assert not (tmp_path / "SealDesktopUpdates" / "SealDesktop-Setup.exe").exists()
    assert not (tmp_path / "SealDesktopUpdates" / "SealDesktop-Setup.exe.download").exists()


def test_launch_app_installer_validates_and_starts_exe(monkeypatch, tmp_path):
    installer = tmp_path / "SealDesktop-Setup.exe"
    installer.touch()
    launches = []
    monkeypatch.setattr(updater.sys, "platform", "win32")

    class FakeShellExecute:
        restype = None

        def __call__(self, *args):
            launches.append(args)
            return 64

    shell_execute = type("Shell32", (), {"ShellExecuteW": FakeShellExecute()})()
    monkeypatch.setattr(
        updater.ctypes,
        "windll",
        type("Windll", (), {"shell32": shell_execute})(),
        raising=False,
    )

    assert updater.launch_app_installer(str(installer)) == 64
    assert launches == [(None, "runas", str(installer), None, str(tmp_path), 1)]


def test_launch_app_installer_reports_elevation_failure(monkeypatch, tmp_path):
    installer = tmp_path / "SealDesktop-Setup.exe"
    installer.touch()
    monkeypatch.setattr(updater.sys, "platform", "win32")

    class FakeShellExecute:
        restype = None

        def __call__(self, *_args):
            return 5

    shell32 = type("Shell32", (), {"ShellExecuteW": FakeShellExecute()})()
    windll = type("Windll", (), {"shell32": shell32})()
    monkeypatch.setattr(updater.ctypes, "windll", windll, raising=False)

    try:
        updater.launch_app_installer(str(installer))
    except OSError:
        pass
    else:
        raise AssertionError("Expected Windows elevation failure to be raised")
