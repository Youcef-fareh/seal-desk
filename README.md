<div align="center">

<h1>🦭 Seal Desktop</h1>

### Cross-Platform Video & Audio Downloader

[![Build & Release](https://img.shields.io/github/actions/workflow/status/Youcef-fareh/seal-desk/build-release.yml?label=Build&logo=github)](https://github.com/Youcef-fareh/seal-desk/actions)
[![CI](https://img.shields.io/github/actions/workflow/status/Youcef-fareh/seal-desk/ci.yml?label=CI&logo=github)](https://github.com/Youcef-fareh/seal-desk/actions)
[![Release](https://img.shields.io/github/v/release/Youcef-fareh/seal-desk?label=Latest&logo=github)](https://github.com/Youcef-fareh/seal-desk/releases/latest)
[![License](https://img.shields.io/github/license/Youcef-fareh/seal-desk?color=blue)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://python.org)
[![Powered by yt-dlp](https://img.shields.io/badge/Powered%20by-yt--dlp-red)](https://github.com/yt-dlp/yt-dlp)

A beautiful, powerful desktop GUI for [yt-dlp](https://github.com/yt-dlp/yt-dlp) — inspired by the Android [Seal](https://github.com/JunkFood02/Seal) app.  
Download from **1000+ sites** including YouTube, SoundCloud, Twitch, Twitter/X, TikTok, and more.

</div>

---

## ✨ Features

| Feature | Details |
|---------|---------|
| 📹 **Video Download & Merging** | Any quality: 4K, 1080p, 720p, 480p, 360p with seamless audio-video merging |
| 🗂 **Sequential Queue** | Stage multiple links, configure options per item, and download successively (one-after-one) |
| ⏯ **Pause, Resume & Delete** | Full control over downloads: pause active items, resume from partial files, or delete anytime |
| 🌍 **Bilingual Interface** | Instant language switching between English and Arabic (العربية) |
| 🔄 **App Auto-Updater** | Automatic startup update checking, incremental release changelogs, and direct installer updating |
| 🎵 **Audio Extraction** | MP3, M4A, OPUS, FLAC, WAV |
| 📂 **Playlist Support** | Download full playlists with organized subdirectories |
| 🏷 **Metadata Embedding** | Titles, artists, thumbnails, chapters |
| 📝 **Subtitle Embedding** | Download & embed subtitles in your language |
| 📋 **History** | Searchable, timestamped download history with folder quick-open |
| ⚡ **Fast Downloads** | Concurrent fragments + optional aria2c integration |
| 🌐 **Proxy Support** | HTTP/HTTPS/SOCKS proxy support |
| 📊 **Live Progress** | Real-time speed, ETA, and progress per download |
| 🎨 **Themes** | Live dark/light theme switching with violet accent |
| 🔁 **Retry Failed Downloads** | Retry failed tasks directly from the download queue |
| 🌐 **Broad Site Support** | Facebook and 1000+ other sites supported through yt-dlp |
| ⚙ **Flexible Settings** | Output templates, rate limiting, cookies file, FFmpeg auto-installer |
| 🧩 **Browser Extension** | Official companion for Chrome, Edge, Firefox & Brave — 1-click send from browser to app |

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
- Packaged builds include FFmpeg and need no separate installation.
- When running from source, install FFmpeg with your platform's package manager for audio extraction and video merging.

## 🧩 Browser Extension

Seal Desktop ships with an official companion browser extension (`extension/`) that lets you send any video or audio link from your browser directly to the app with one click.

### Features
- **Auto-detects videos on any page** — a floating overlay appears directly on the video player when you hover. No need to copy links.
- **⚡ Download Now / ➕ Add to Queue buttons** appear right on the video on YouTube, Twitter/X, TikTok, Reddit, Twitch, Vimeo, Facebook, and any HTML5 `<video>`
- **Right-click context menu** on any link, video, or page: *Download Video*, *Download Audio*, or *Add to Queue*
- **Keyboard shortcut** `Alt + Shift + D` to instantly send the current tab
- **Live status indicator** showing whether Seal Desktop is running and queue count
- **Zero telemetry** — all communication stays local (`127.0.0.1:48123`)

### How the companion server works

When Seal Desktop launches, it starts a lightweight local REST API on `http://127.0.0.1:48123`. The browser extension communicates with it over this private loopback address. You can toggle the server under **Settings → Behaviour → Browser extension companion server**.

### Installing the Extension

**Chrome / Edge / Brave / Opera:**
1. Open `chrome://extensions` (or your browser's equivalent)
2. Enable **Developer mode** (top-right toggle)
3. Click **Load unpacked** and select the `extension/` folder in this repository
4. Pin the 🦭 Seal icon to your toolbar

**Firefox:**
1. Go to `about:debugging#/runtime/this-firefox`
2. Click **Load Temporary Add-on...**
3. Select `extension/manifest.json`

> See [`extension/README.md`](extension/README.md) for full details and configuration options.

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
├── extension/                      # Browser extension (Chrome, Edge, Firefox, Brave)
│   ├── manifest.json               # Extension manifest (Manifest V3)
│   ├── popup.html / popup.js       # Extension popup UI & logic
│   ├── background.js               # Service worker (context menus, shortcuts)
│   ├── content.js / content.css    # In-page video download buttons
│   ├── options.html / options.js   # Extension settings page
│   └── icons/                      # Extension icons (16, 32, 48, 128px)
├── installer/
│   └── windows.nsi                 # NSIS Windows installer script
├── assets/
│   └── icon.ico                    # App icon
├── src/
│   ├── core/
│   │   ├── api_server.py           # Local REST API for browser extension companion
│   │   ├── clipboard_monitor.py    # Clipboard URL watcher
│   │   ├── downloader.py           # yt-dlp wrapper & state machine
│   │   ├── logger.py               # Rotating file logger
│   │   ├── notifications.py        # Desktop notification helper
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
│   ├── test_downloader.py          # Downloader unit tests
│   └── test_api_server.py          # Companion API server tests
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
