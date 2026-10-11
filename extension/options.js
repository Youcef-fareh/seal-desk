/**
 * Seal Desktop Companion — Options Page Script
 */

const DEFAULT_SERVER_URL = "http://127.0.0.1:48123";

document.addEventListener("DOMContentLoaded", async () => {
  await loadOptions();
  setupListeners();
});

async function loadOptions() {
  const data = await chrome.storage.sync.get({
    serverUrl: DEFAULT_SERVER_URL,
    defaultMode: "video",
    defaultQuality: "best",
    defaultAudioFormat: "mp3",
    embedMetadata: true,
    embedSubtitles: false,
    enableContextMenu: true,
    enablePageButton: true,
  });

  document.getElementById("server-url").value = data.serverUrl || DEFAULT_SERVER_URL;
  document.getElementById("default-mode").value = data.defaultMode || "video";
  document.getElementById("default-quality").value = data.defaultQuality || "best";
  document.getElementById("default-audio-format").value = data.defaultAudioFormat || "mp3";
  document.getElementById("embed-metadata").checked = Boolean(data.embedMetadata);
  document.getElementById("embed-subtitles").checked = Boolean(data.embedSubtitles);
  document.getElementById("enable-context-menu").checked = Boolean(data.enableContextMenu);
  document.getElementById("enable-page-button").checked = Boolean(data.enablePageButton);

  testConnection(false);
}

function setupListeners() {
  document.getElementById("btn-save").addEventListener("click", saveOptions);
  document.getElementById("btn-test-connection").addEventListener("click", () => testConnection(true));

  // Navigation link scroll
  document.querySelectorAll(".nav-link").forEach((link) => {
    link.addEventListener("click", (e) => {
      document.querySelectorAll(".nav-link").forEach((l) => l.classList.remove("active"));
      link.classList.add("active");
    });
  });
}

async function saveOptions() {
  const serverUrl = document.getElementById("server-url").value.trim() || DEFAULT_SERVER_URL;
  const defaultMode = document.getElementById("default-mode").value;
  const defaultQuality = document.getElementById("default-quality").value;
  const defaultAudioFormat = document.getElementById("default-audio-format").value;
  const embedMetadata = document.getElementById("embed-metadata").checked;
  const embedSubtitles = document.getElementById("embed-subtitles").checked;
  const enableContextMenu = document.getElementById("enable-context-menu").checked;
  const enablePageButton = document.getElementById("enable-page-button").checked;

  await chrome.storage.sync.set({
    serverUrl,
    defaultMode,
    defaultQuality,
    defaultAudioFormat,
    embedMetadata,
    embedSubtitles,
    enableContextMenu,
    enablePageButton,
  });

  const saveStatus = document.getElementById("save-status");
  saveStatus.style.display = "inline";
  setTimeout(() => {
    saveStatus.style.display = "none";
  }, 3000);

  // Update context menus if setting changed
  chrome.runtime.sendMessage({ type: "SETTINGS_UPDATED" });
}

async function testConnection(notify = true) {
  const serverUrl = document.getElementById("server-url").value.trim() || DEFAULT_SERVER_URL;
  const dot = document.getElementById("conn-dot");
  const text = document.getElementById("conn-status-text");

  dot.className = "conn-dot";
  text.textContent = "Testing connection...";

  const t0 = performance.now();
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 2500);

    const res = await fetch(`${serverUrl}/api/ping`, {
      method: "GET",
      signal: controller.signal,
    });
    clearTimeout(timeout);

    const latency = Math.round(performance.now() - t0);
    if (res.ok) {
      const data = await res.json();
      dot.className = "conn-dot online";
      text.textContent = `🟢 Connected to ${data.app || "Seal Desktop"} (${latency}ms)`;
    } else {
      throw new Error(`HTTP ${res.status}`);
    }
  } catch (err) {
    dot.className = "conn-dot offline";
    text.textContent = `🔴 Offline — Seal Desktop is not reachable on this port`;
  }
}
