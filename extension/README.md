# 🦭 Seal Desktop Companion — Browser Extension

The official companion extension for **[Seal Desktop](https://github.com/Youcef-fareh/seal-desk)**. Download videos, audio, and playlists from YouTube, Twitter/X, TikTok, SoundCloud, and 1000+ sites directly from your web browser — no link copying required.

---

## ✨ Features

### Automatic Video Detection
The extension **automatically detects videos on every page** and shows a floating overlay directly on the video player. Just hover over any video and two buttons appear:

- **⚡ Download Now** — sends the video directly to Seal Desktop and starts immediately
- **➕ Add to Queue** — adds to Seal Desktop's download queue without starting

No popup, no copy-pasting — the overlay appears right on the video.

### Supported Platforms (auto-detection)
| Platform | In-Page Overlay | Toolbar Button |
|----------|----------------|---------------|
| YouTube | ✅ On video player | ✅ In action bar |
| Twitter / X | ✅ On video tweets | — |
| TikTok | ✅ On video element | — |
| Reddit (v.redd.it) | ✅ On player | — |
| Facebook Watch | ✅ On player | — |
| Twitch | ✅ On player | — |
| Vimeo | ✅ On player | — |
| Dailymotion | ✅ On player | — |
| Bilibili | ✅ On player | — |
| Rumble / Odysee | ✅ On player | — |
| Instagram | ✅ On player | — |
| Any HTML5 `<video>` | ✅ On any site | — |

### Other Features
- 🖱 **Right-click context menu** on any link, page, video, or audio element:
  - *Download Video with Seal*
  - *Download Audio (MP3)*
  - *Add to Queue*
- ⌨️ **Keyboard shortcut** `Alt + Shift + D` to instantly send the current tab
- 🟢 **Live status indicator** in the popup — shows whether Seal Desktop is running and the current queue count
- 📋 **Seamless fallback** — if Seal Desktop is closed, the URL is copied to clipboard (for Seal's clipboard monitor)
- 🔒 **Zero telemetry** — all communication is strictly local (`127.0.0.1:48123`)

---

## 🚀 Installation Guide

### Google Chrome / Microsoft Edge / Brave / Opera

1. Open your browser's extension manager:
   - **Chrome**: `chrome://extensions`
   - **Edge**: `edge://extensions`
   - **Brave**: `brave://extensions`
   - **Opera**: `opera://extensions`
2. Enable **Developer mode** (toggle switch in the top-right corner).
3. Click the **Load unpacked** button in the top-left corner.
4. Select the `extension` folder from your `seal-desktop` directory.
5. The **Seal Desktop** icon (🦭) will appear in your toolbar — pin it for quick access.

### Mozilla Firefox

1. Go to `about:debugging#/runtime/this-firefox`
2. Click **Load Temporary Add-on...**
3. Select `extension/manifest.json`

---

## ⚙️ How It Works

1. **Seal Desktop** starts a lightweight local REST API server on `http://127.0.0.1:48123` (toggle in Settings → Behaviour → Browser extension companion server).
2. The content script scans every page for `<video>` elements and known platform patterns.
3. When a video is detected, a **floating overlay** is injected right on top of the video element — visible only on hover.
4. Clicking a button in the overlay sends a `POST /api/download` request with the URL, title, and your format preferences to the local server.
5. Seal Desktop queues or starts the download via yt-dlp and sends you a desktop notification.

---

## 🛠 Configuration

Click the extension icon → ⚙️ (gear) button, or right-click the extension icon → **Options**:

| Option | Default | Description |
|--------|---------|-------------|
| API Server URL | `http://127.0.0.1:48123` | Port where Seal Desktop listens |
| Default Mode | Video | Video or Audio extraction |
| Default Quality | Best | 4K / 1440p / 1080p / 720p / 480p |
| Default Audio Format | MP3 | MP3 / M4A / FLAC / OPUS / WAV |
| Embed Thumbnails & Tags | ✅ On | Save metadata into files |
| Embed Subtitles | Off | Auto-download subtitles |
| Right-Click Context Menu | ✅ On | Show Seal options on right-click |
| In-Page Video Buttons | ✅ On | Show overlay on detected videos |
