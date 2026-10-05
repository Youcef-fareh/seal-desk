<div align="center">

<h1>🦭 Seal Desktop</h1>

### Cross-Platform Video & Audio Downloader

[![Build & Release](https://img.shields.io/github/actions/workflow/status/your-username/seal-desktop/build-release.yml?label=Build&logo=github)](https://github.com/your-username/seal-desktop/actions)
[![CI](https://img.shields.io/github/actions/workflow/status/your-username/seal-desktop/ci.yml?label=CI&logo=github)](https://github.com/your-username/seal-desktop/actions)
[![Release](https://img.shields.io/github/v/release/your-username/seal-desktop?label=Latest&logo=github)](https://github.com/your-username/seal-desktop/releases/latest)
[![License](https://img.shields.io/github/license/your-username/seal-desktop?color=blue)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://python.org)
[![Powered by yt-dlp](https://img.shields.io/badge/Powered%20by-yt--dlp-red)](https://github.com/yt-dlp/yt-dlp)

A beautiful, powerful desktop GUI for [yt-dlp](https://github.com/yt-dlp/yt-dlp) — inspired by the Android [Seal](https://github.com/JunkFood02/Seal) app.  
Download from **1000+ sites** including YouTube, SoundCloud, Twitch, Twitter/X, TikTok, and more.

</div>

---

## ✨ Features

| Feature | Details |
|---------|---------|
| 📹 **Video Download** | Any quality: 4K, 1080p, 720p, 480p, 360p |
| 🎵 **Audio Extraction** | MP3, M4A, OPUS, FLAC, WAV |
| 📂 **Playlist Support** | Download full playlists with organized subdirectories |
| 🏷 **Metadata Embedding** | Titles, artists, thumbnails, chapters |
| 📝 **Subtitle Embedding** | Download & embed subtitles in your language |
| 📋 **History** | Searchable download history with folder quick-open |
| ⚡ **Fast Downloads** | Concurrent fragments + optional aria2c integration |
| 🌐 **Proxy Support** | HTTP/HTTPS/SOCKS proxy support |
| 📊 **Live Progress** | Real-time speed, ETA, and progress per download |
| 🎨 **Dark UI** | Modern dark interface with violet accent |
| ⚙ **Flexible Settings** | Output templates, rate limiting, cookies file |

## 🖥 Supported Platforms

| OS | Installer | Portable |
|----|-----------|---------|
| Windows 10/11 | ✅ `.exe` installer | ✅ ZIP |
| macOS 12+ | ✅ `.dmg` disk image | ✅ `.app` |
| Linux (x86_64) | ✅ AppImage | ✅ tar.gz |

## ⬇️ Installation

### Windows
Download `SealDesktop-*-Setup.exe` from [Releases](https://github.com/your-username/seal-desktop/releases/latest) and run it.

### macOS
Download `SealDesktop-*-macos.dmg`, open it, and drag **Seal Desktop** to Applications.

### Linux
```bash
chmod +x SealDesktop-*-linux-x86_64.AppImage
./SealDesktop-*-linux-x86_64.AppImage
```

### Prerequisites
- **FFmpeg** is required for audio extraction and video merging:
  - Windows: `choco install ffmpeg` or [download](https://ffmpeg.org/download.html)
  - macOS: `brew install ffmpeg`
  - Linux: `sudo apt install ffmpeg`

## 🛠 Running from Source

```bash
git clone https://github.com/your-username/seal-desktop
cd seal-desktop

# Create virtual environment
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
```

## 🏗 Building

```bash
# Install build tools
pip install pyinstaller

# Build (produces dist/SealDesktop/)
pyinstaller SealDesktop.spec --clean --noconfirm

# Windows: Create installer (requires NSIS)
makensis installer/windows.nsi
```

Or simply **push a version tag** to trigger the GitHub Actions build:

```bash
git tag v1.0.0
git push origin v1.0.0
```

This automatically builds and publishes a GitHub Release for all three platforms.

## 🗂 Project Structure

```
seal-desktop/
├── main.py                         # Entry point
├── SealDesktop.spec                # PyInstaller build spec
├── requirements.txt                # Runtime dependencies
├── requirements-build.txt          # Build-time dependencies
├── installer/
│   └── windows.nsi                 # NSIS Windows installer script
├── assets/
│   └── icon.ico                    # App icon
├── src/
│   ├── core/
│   │   ├── downloader.py           # yt-dlp wrapper & state machine
│   │   ├── settings.py             # Persistent settings manager
│   │   └── updater.py              # App & yt-dlp update checker
│   └── ui/
│       ├── theme.py                # Design system (colors, fonts, spacing)
│       ├── widgets.py              # Reusable custom widgets
│       ├── app_shell.py            # Window layout & navigation
│       └── pages/
│           ├── download_page.py    # Main download UI
│           ├── history_page.py     # Download history
│           └── settings_page.py    # Settings panel
├── tests/
│   └── test_downloader.py          # Unit tests
└── .github/
    └── workflows/
        ├── build-release.yml       # Build + publish releases
        └── ci.yml                  # Lint & test on PR/push
```

## 🤝 Contributing

Pull requests welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Write tests for new functionality
4. Ensure `ruff check` and `pytest` pass
5. Submit a PR

## 📃 License

GPL-3.0 — see [LICENSE](LICENSE).

Seal Desktop is inspired by [Seal for Android](https://github.com/JunkFood02/Seal) and is powered by [yt-dlp](https://github.com/yt-dlp/yt-dlp).

<div align="right">
<a href="#top">👆 Back to top</a>
</div>
