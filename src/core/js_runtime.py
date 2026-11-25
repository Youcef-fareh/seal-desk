"""Discover JavaScript runtimes supported by yt-dlp."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

_RUNTIME_EXECUTABLES = {
    "deno": ("deno.exe", "deno"),
    "node": ("node.exe", "node"),
    "bun": ("bun.exe", "bun"),
    "quickjs": ("qjs.exe", "qjs"),
}


def _packaged_runtime_candidates(name: str) -> list[Path]:
    exe_names = _RUNTIME_EXECUTABLES[name]
    roots: list[Path] = []
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        roots.append(Path(bundle_root))
    roots.append(Path(sys.executable).resolve().parent)
    candidates = [root / name / exe for root in roots for exe in exe_names]
    if name == "deno":
        deno_install = os.environ.get("DENO_INSTALL")
        if deno_install:
            candidates.extend(Path(deno_install) / "bin" / exe for exe in exe_names)
        candidates.extend(Path.home() / ".deno" / "bin" / exe for exe in exe_names)
    return candidates


def get_javascript_runtimes() -> dict[str, dict[str, str]]:
    """Return configured yt-dlp runtimes found in the app bundle or PATH."""
    runtimes: dict[str, dict[str, str]] = {}
    for name, executables in _RUNTIME_EXECUTABLES.items():
        path = None
        for executable in executables:
            path = shutil.which(executable)
            if path:
                break
        if not path:
            path = next(
                (
                    str(candidate)
                    for candidate in _packaged_runtime_candidates(name)
                    if candidate.is_file()
                ),
                None,
            )
        if path:
            runtimes[name] = {"path": path}
    return runtimes
