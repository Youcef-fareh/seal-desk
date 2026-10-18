/**
 * Seal Desktop Companion Extension — Popup Logic
 */

const DEFAULT_SERVER_URL = "http://127.0.0.1:48123";

let currentServerUrl = DEFAULT_SERVER_URL;
let currentTab = null;
let isConnected = false;
let currentMode = "video"; // "video" | "audio"

// Platform detection patterns
const PLATFORMS = [
  { name: "YouTube", class: "youtube", regex: /(youtube\.com|youtu\.be)/i },
  { name: "Twitter / X", class: "twitter", regex: /(twitter\.com|x\.com)/i },
  { name: "TikTok", class: "tiktok", regex: /tiktok\.com/i },
  { name: "Twitch", class: "twitch", regex: /twitch\.tv/i },
  { name: "SoundCloud", class: "soundcloud", regex: /soundcloud\.com/i },
  { name: "Reddit", class: "reddit", regex: /reddit\.com/i },
  { name: "Instagram", class: "instagram", regex: /instagram\.com/i },
  { name: "Vimeo", class: "vimeo", regex: /vimeo\.com/i },
  { name: "Facebook", class: "facebook", regex: /facebook\.com/i },
];

document.addEventListener("DOMContentLoaded", async () => {
  await loadSettings();
  setupUIHandlers();
  await detectCurrentTab();
  await checkConnection();
});

/** Load stored user settings */
async function loadSettings() {
  try {
    const data = await chrome.storage.sync.get({
      serverUrl: DEFAULT_SERVER_URL,
      defaultMode: "video",
      defaultQuality: "best",
      defaultAudioFormat: "mp3",
      embedSubtitles: false,
      embedMetadata: true,
    });

    currentServerUrl = data.serverUrl || DEFAULT_SERVER_URL;
    currentMode = data.defaultMode || "video";
    setMode(currentMode);

    if (data.defaultQuality) {
      document.getElementById("video-quality").value = data.defaultQuality;
    }
    if (data.defaultAudioFormat) {
      document.getElementById("audio-format").value = data.defaultAudioFormat;
    }
    document.getElementById("embed-subs").checked = Boolean(data.embedSubtitles);
    document.getElementById("embed-meta").checked = Boolean(data.embedMetadata);
  } catch (e) {
    console.warn("Could not load stored settings:", e);
  }
}

/** Detect current active browser tab */
async function detectCurrentTab() {
  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tabs || tabs.length === 0) return;

    currentTab = tabs[0];
    const url = currentTab.url || "";
    const title = currentTab.title || "";

    const urlInput = document.getElementById("media-url");
    const titleLbl = document.getElementById("media-title");
    const platformBadge = document.getElementById("platform-badge");

    if (url && (url.startsWith("http://") || url.startsWith("https://"))) {
      urlInput.value = url;
      titleLbl.textContent = title || "Current Web Page";

      // Match platform
      let matched = false;
      for (const p of PLATFORMS) {
        if (p.regex.test(url)) {
          platformBadge.textContent = p.name;
          platformBadge.className = `platform-badge ${p.class}`;
          matched = true;
          break;
        }
      }
      if (!matched) {
        try {
          const host = new URL(url).hostname.replace(/^www\./, "");
          platformBadge.textContent = host;
          platformBadge.className = "platform-badge";
        } catch (_) {
          platformBadge.textContent = "🌐 Web";
          platformBadge.className = "platform-badge";
        }
      }
    } else {
      titleLbl.textContent = "No downloadable media detected";
      urlInput.placeholder = "Paste a media link here...";
    }
  } catch (err) {
    console.error("Error querying current tab:", err);
  }
}

/** Check connectivity with Seal Desktop local REST API */
async function checkConnection() {
  const statusBadge = document.getElementById("status-badge");
  const statusLabel = document.getElementById("status-label");
  const offlineBanner = document.getElementById("offline-banner");
  const fallbackBtn = document.getElementById("btn-copy-fallback");
  const queueStat = document.getElementById("queue-stat");

  statusLabel.textContent = "Connecting...";
  statusBadge.className = "status-badge";

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 2000);

    const res = await fetch(`${currentServerUrl}/api/ping`, {
      method: "GET",
      signal: controller.signal,
    });
    clearTimeout(timeout);

    if (res.ok) {
      isConnected = true;
      statusBadge.className = "status-badge connected";
      statusLabel.textContent = "Connected";
      offlineBanner.style.display = "none";
      fallbackBtn.style.display = "none";

      // Query status stats
      fetchQueueStatus();
    } else {
      throw new Error(`HTTP ${res.status}`);
    }
  } catch (err) {
    isConnected = false;
    statusBadge.className = "status-badge offline";
    statusLabel.textContent = "Offline";
    offlineBanner.style.display = "flex";
    fallbackBtn.style.display = "block";
    queueStat.textContent = "Seal Desktop offline";
  }
}

/** Fetch queue statistics from Seal Desktop */
async function fetchQueueStatus() {
  try {
    const res = await fetch(`${currentServerUrl}/api/status`);
    if (res.ok) {
      const data = await res.json();
      const queueStat = document.getElementById("queue-stat");
      const queued = data.queued_count || 0;
      const active = data.active_count || 0;
      if (active > 0) {
        queueStat.textContent = `Active: ${active} | Queued: ${queued}`;
      } else {
        queueStat.textContent = `Queue: ${queued} items`;
      }
    }
  } catch (_) {
    // ignore
  }
}

/** Setup UI handlers */
function setupUIHandlers() {
  // Mode tabs
  const tabVideo = document.getElementById("tab-video");
  const tabAudio = document.getElementById("tab-audio");
  const tabSubtitles = document.getElementById("tab-subtitles");

  tabVideo.addEventListener("click", () => setMode("video"));
  tabAudio.addEventListener("click", () => setMode("audio"));
  if (tabSubtitles) {
    tabSubtitles.addEventListener("click", () => setMode("subtitles"));
  }

  // Paste button
  document.getElementById("btn-paste-url").addEventListener("click", async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text && (text.startsWith("http://") || text.startsWith("https://"))) {
        document.getElementById("media-url").value = text.trim();
        showToast("URL pasted from clipboard", "success");
      }
    } catch (e) {
      showToast("Cannot read clipboard automatically", "error");
    }
  });

  // Action: Download Now
  document.getElementById("btn-download-now").addEventListener("click", () => {
    sendDownload(true);
  });

  // Action: Add to Queue
  document.getElementById("btn-add-queue").addEventListener("click", () => {
    sendDownload(false);
  });

  // Action: Fallback Copy to Clipboard
  document.getElementById("btn-copy-fallback").addEventListener("click", async () => {
    const url = document.getElementById("media-url").value.trim();
    if (!url) return;
    try {
      await navigator.clipboard.writeText(url);
      showToast("Copied! Seal Desktop clipboard monitor will capture this.", "success");
    } catch (_) {
      showToast("Failed to copy URL", "error");
    }
  });

  // Status Badge / Retry Click
  document.getElementById("status-badge").addEventListener("click", checkConnection);
  document.getElementById("btn-retry-conn").addEventListener("click", checkConnection);

  // Settings Gear
  document.getElementById("btn-open-options").addEventListener("click", () => {
    if (chrome.runtime.openOptionsPage) {
      chrome.runtime.openOptionsPage();
    } else {
      window.open(chrome.runtime.getURL("options.html"));
    }
  });
}

/** Set UI download mode (video vs audio vs subtitles) */
function setMode(mode) {
  currentMode = mode;
  const tabVideo = document.getElementById("tab-video");
  const tabAudio = document.getElementById("tab-audio");
  const tabSubtitles = document.getElementById("tab-subtitles");
  const videoOpts = document.getElementById("video-options");
  const audioOpts = document.getElementById("audio-options");
  const subsOpts = document.getElementById("subtitles-options");

  tabVideo?.classList.remove("active");
  tabAudio?.classList.remove("active");
  tabSubtitles?.classList.remove("active");

  if (videoOpts) videoOpts.style.display = "none";
  if (audioOpts) audioOpts.style.display = "none";
  if (subsOpts) subsOpts.style.display = "none";

  if (mode === "video") {
    tabVideo?.classList.add("active");
    if (videoOpts) videoOpts.style.display = "flex";
  } else if (mode === "audio") {
    tabAudio?.classList.add("active");
    if (audioOpts) audioOpts.style.display = "flex";
  } else if (mode === "subtitles") {
    tabSubtitles?.classList.add("active");
    if (subsOpts) subsOpts.style.display = "flex";
  }
}

/** Send download command to Seal Desktop */
async function sendDownload(autoStart = true) {
  const url = document.getElementById("media-url").value.trim();
  const title = document.getElementById("media-title").textContent.trim();

  if (!url || (!url.startsWith("http://") && !url.startsWith("https://"))) {
    showToast("Please enter a valid HTTP/HTTPS link", "error");
    return;
  }

  const payload = {
    url: url,
    title: title || "Media Download",
    download_mode: currentMode,
    subtitles_only: currentMode === "subtitles",
    extract_audio: currentMode === "audio",
    subtitle_source: document.getElementById("sub-source")?.value || "both",
    audio_format: document.getElementById("audio-format")?.value || "mp3",
    video_quality: document.getElementById("video-quality")?.value || "best",
    video_container: document.getElementById("video-format")?.value || "mp4",
    embed_subtitles: document.getElementById("embed-subs")?.checked ?? false,
    embed_metadata: document.getElementById("embed-meta")?.checked ?? true,
    auto_start: autoStart,
  };

  const btn = autoStart ? document.getElementById("btn-download-now") : document.getElementById("btn-add-queue");
  const originalText = btn.innerHTML;
  btn.innerHTML = `<span class="btn-icon">⏳</span><span>Sending...</span>`;
  btn.disabled = true;

  try {
    const res = await fetch(`${currentServerUrl}/api/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      const data = await res.json();
      showToast(autoStart ? "🚀 Started in Seal Desktop!" : "➕ Added to Seal queue!", "success");
      // Update badge in background
      chrome.runtime.sendMessage({ type: "DOWNLOAD_ADDED", autoStart });
      setTimeout(() => {
        window.close();
      }, 1400);
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(`Error: ${err.message || res.statusText}`, "error");
    }
  } catch (err) {
    // If connection failed, offer fallback
    showToast("Cannot connect to Seal Desktop. Copied URL to clipboard!", "error");
    try {
      await navigator.clipboard.writeText(url);
    } catch (_) {}
    document.getElementById("offline-banner").style.display = "flex";
    document.getElementById("btn-copy-fallback").style.display = "block";
  } finally {
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}

/** Display brief feedback banner */
function showToast(msg, type = "success") {
  const toast = document.getElementById("toast-banner");
  const icon = document.getElementById("toast-icon");
  const label = document.getElementById("toast-msg");

  label.textContent = msg;
  icon.textContent = type === "success" ? "✅" : "⚠️";
  toast.className = `toast-banner ${type}`;
  toast.style.display = "flex";

  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => {
    toast.style.display = "none";
  }, 4000);
}
