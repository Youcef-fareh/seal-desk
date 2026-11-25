# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Seal Desktop.
Produces a single-directory bundle for Windows/macOS/Linux.
"""

import shutil
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas_imageio, binaries_imageio, hiddenimports_imageio = collect_all("imageio_ffmpeg")
hiddenimports_youtube_js = collect_submodules("yt_dlp.extractor.youtube.jsc")

deno_path = shutil.which("deno")
if deno_path:
    binaries_imageio.append((deno_path, "deno"))
else:
    print("Deno was not found at build time; packaged YouTube downloads will use a system runtime.")

block_cipher = None

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=binaries_imageio,
    datas=[
        ("assets", "assets"),
    ] + datas_imageio,
    hiddenimports=[
        "yt_dlp",
        "yt_dlp.extractor",
        "yt_dlp.postprocessor",
        "yt_dlp.utils",
        "yt_dlp.networking",
        "platformdirs",
        "tkinter",
        "tkinter.ttk",
        "tkinter.filedialog",
        "tkinter.messagebox",
    ] + hiddenimports_imageio + hiddenimports_youtube_js,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
        "PyQt5",
        "PyQt6",
        "wx",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SealDesktop",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,           # No console window on Windows
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.ico" if Path("assets/icon.ico").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SealDesktop",
)

# macOS .app bundle
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="SealDesktop.app",
        icon="assets/icon.icns" if Path("assets/icon.icns").exists() else None,
        bundle_identifier="com.sealdesktop.app",
        info_plist={
            "CFBundleDisplayName": "Seal Desktop",
            "CFBundleVersion": "1.5.5",
            "CFBundleShortVersionString": "1.5.5",
            "NSHighResolutionCapable": True,
        },
    )
