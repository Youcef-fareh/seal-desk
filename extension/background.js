/**
 * Seal Desktop Companion Extension — Background Service Worker
 */

const DEFAULT_SERVER_URL = "http://127.0.0.1:48123";

// Initialize Context Menus and Storage Defaults on Install
chrome.runtime.onInstalled.addListener(async (details) => {
  // Only set defaults that the user hasn't already configured
  // (don't overwrite their preferences on extension updates)
  const DEFAULTS = {
    serverUrl: DEFAULT_SERVER_URL,
    defaultMode: "video",
    defaultQuality: "best",
    defaultAudioFormat: "mp3",
    enableContextMenu: true,
    enablePageButton: true,
    embedSubtitles: false,
    embedMetadata: true,
  };
  const existing = await chrome.storage.sync.get(Object.keys(DEFAULTS));
  const missing = {};
  for (const [key, val] of Object.entries(DEFAULTS)) {
    if (existing[key] === undefined) missing[key] = val;
  }
  if (Object.keys(missing).length > 0) {
    await chrome.storage.sync.set(missing);
  }

  setupContextMenus();
});

// Re-create context menus on service worker startup
chrome.runtime.onStartup.addListener(() => {
  setupContextMenus();
});

function setupContextMenus() {
  chrome.contextMenus.removeAll(() => {
    // Parent context menu
    chrome.contextMenus.create({
      id: "seal-root",
      title: "🦭 Seal Desktop",
      contexts: ["page", "link", "video", "audio", "selection"],
    });

    // Sub-items
    chrome.contextMenus.create({
      id: "seal-download-video",
      parentId: "seal-root",
      title: "🎬 Download Video",
      contexts: ["page", "link", "video", "audio", "selection"],
    });

    chrome.contextMenus.create({
      id: "seal-download-audio",
      parentId: "seal-root",
      title: "🎵 Download Audio (MP3)",
      contexts: ["page", "link", "video", "audio", "selection"],
    });

    chrome.contextMenus.create({
      id: "seal-download-subtitles",
      parentId: "seal-root",
      title: "💬 Download Subtitles",
      contexts: ["page", "link", "video", "audio", "selection"],
    });

    chrome.contextMenus.create({
      id: "seal-add-queue",
      parentId: "seal-root",
      title: "➕ Add to Queue",
      contexts: ["page", "link", "video", "audio", "selection"],
    });
  });
}

// Handle Context Menu item clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  let targetUrl = info.linkUrl || info.srcUrl || info.selectionText || (tab ? tab.url : "");

  if (targetUrl) {
    targetUrl = targetUrl.trim();
  }

  if (!targetUrl || (!targetUrl.startsWith("http://") && !targetUrl.startsWith("https://"))) {
    showNotification("Seal Desktop", "Could not find a valid HTTP/HTTPS link to download.");
    return;
  }

  const title = tab ? tab.title : "";
  const isAudio = info.menuItemId === "seal-download-audio";
  const isSubtitles = info.menuItemId === "seal-download-subtitles";
  const autoStart = info.menuItemId !== "seal-add-queue";

  await triggerDownload({
    url: targetUrl,
    title: title,
    download_mode: isSubtitles ? "subtitles" : (isAudio ? "audio" : "video"),
    extract_audio: isAudio,
    subtitles_only: isSubtitles,
    auto_start: autoStart,
  });
});

// Handle Keyboard Shortcut command (Alt+Shift+D)
chrome.commands.onCommand.addListener(async (command) => {
  if (command === "quick-download") {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab && tab.url && (tab.url.startsWith("http://") || tab.url.startsWith("https://"))) {
      const settings = await chrome.storage.sync.get({
        defaultMode: "video",
        defaultQuality: "best",
        defaultAudioFormat: "mp3",
      });

      await triggerDownload({
        url: tab.url,
        title: tab.title || "",
        extract_audio: settings.defaultMode === "audio",
        auto_start: true,
      });
    }
  }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "TRIGGER_DOWNLOAD") {
    triggerDownload(message.payload)
      .then(sendResponse)
      .catch((err) => sendResponse({ success: false, error: String(err) }));
    return true; // Keep message channel open for async response
  }

  if (message.type === "DOWNLOAD_ADDED") {
    flashBadge("✓", "#10B981");
    // sendResponse not needed for fire-and-forget messages
    return false;
  }
});

/** Send download payload to Seal Desktop server */
async function triggerDownload(options) {
  const settings = await chrome.storage.sync.get({
    serverUrl: DEFAULT_SERVER_URL,
    defaultQuality: "best",
    defaultAudioFormat: "mp3",
    embedSubtitles: false,
    embedMetadata: true,
  });

  const serverUrl = settings.serverUrl || DEFAULT_SERVER_URL;

  const payload = {
    url: options.url,
    title: options.title || "",
    download_mode: options.download_mode || (options.subtitles_only ? "subtitles" : (options.extract_audio ? "audio" : "video")),
    subtitles_only: Boolean(options.subtitles_only),
    extract_audio: Boolean(options.extract_audio),
    subtitle_source: options.subtitle_source || "both",
    audio_format: options.audio_format || settings.defaultAudioFormat,
    video_quality: options.video_quality || settings.defaultQuality,
    video_container: options.video_container || "mp4",
    embed_subtitles: options.embed_subtitles ?? settings.embedSubtitles,
    embed_metadata: options.embed_metadata ?? settings.embedMetadata,
    auto_start: options.auto_start ?? true,
  };

  try {
    const res = await fetch(`${serverUrl}/api/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      flashBadge("✓", "#10B981");
      const msg = payload.auto_start
        ? `Started download: ${(options.title || options.url).slice(0, 45)}`
        : `Queued link in Seal Desktop`;
      showNotification("Seal Desktop", msg);
      return { success: true };
    } else {
      const err = await res.json().catch(() => ({}));
      flashBadge("!", "#EF4444");
      showNotification("Seal Desktop Error", err.message || "Failed to process download request");
      return { success: false, error: err.message };
    }
  } catch (err) {
    flashBadge("!", "#F59E0B");
    showNotification(
      "Seal Desktop Offline",
      "Could not reach Seal Desktop. Make sure the application is open."
    );
    return { success: false, error: "Connection offline" };
  }
}

/** Show temporary badge on the extension action icon */
function flashBadge(text, color) {
  chrome.action.setBadgeText({ text });
  chrome.action.setBadgeBackgroundColor({ color });
  setTimeout(() => {
    chrome.action.setBadgeText({ text: "" });
  }, 2500);
}

/** Show browser system notification */
function showNotification(title, message) {
  if (chrome.notifications) {
    chrome.notifications.create({
      type: "basic",
      iconUrl: "icons/icon128.png",
      title: title,
      message: message,
      priority: 1,
    });
  }
}
