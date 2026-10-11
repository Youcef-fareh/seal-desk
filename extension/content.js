/**
 * Seal Desktop Companion Extension — Content Script
 *
 * Automatically detects videos on the page and injects a polished
 * floating overlay with Download Now + Add to Queue buttons directly
 * on the video element. Supports:
 *   - YouTube (watch pages, Shorts, embedded)
 *   - Twitter / X (video tweets)
 *   - TikTok
 *   - Reddit (v.redd.it embeds)
 *   - Facebook Watch
 *   - Twitch VODs & clips
 *   - Vimeo, Dailymotion, Bilibili, Rumble, Odysee
 *   - Any generic HTML5 <video> element
 */

// ──────────────────────────────────────────────
// Initialisation
// ──────────────────────────────────────────────

let _enabled = true;
let _observer = null;
let _lastUrl = location.href;
let _urlPollId = null;
let _running = false;  // re-entrancy guard

(async () => {
  const settings = await chrome.storage.sync.get({ enablePageButton: true });
  _enabled = Boolean(settings.enablePageButton);
  if (!_enabled) return;

  run();

  // Re-run on DOM mutations (SPAs like YouTube navigate without page reload)
  // Watch body only — documentElement includes <head> changes which fire constantly
  _observer = new MutationObserver(debounce(run, 600));
  _observer.observe(document.body || document.documentElement, { childList: true, subtree: true });

  // Also detect SPA URL changes (pushState / replaceState / popstate)
  _urlPollId = setInterval(() => {
    if (location.href !== _lastUrl) {
      _lastUrl = location.href;
      cleanupOrphanedOverlays();
      setTimeout(run, 800);
    }
  }, 500);
})();

function run() {
  if (_running) return;  // prevent re-entrant calls from the MutationObserver
  _running = true;
  try {
    const host = location.hostname.replace(/^www\./, "");
    if (isYouTubeWatch()) {
      injectYouTubeToolbarButton();
    }
    injectVideoOverlays(host);
  } finally {
    _running = false;
  }
}

// ──────────────────────────────────────────────
// Platform helpers
// ──────────────────────────────────────────────

const PLATFORM_MAP = [
  { name: "YouTube",      regex: /youtube\.com|youtu\.be/ },
  { name: "Twitter / X",  regex: /twitter\.com|x\.com/ },
  { name: "TikTok",       regex: /tiktok\.com/ },
  { name: "Reddit",       regex: /reddit\.com/ },
  { name: "Facebook",     regex: /facebook\.com|fb\.watch/ },
  { name: "Twitch",       regex: /twitch\.tv/ },
  { name: "Vimeo",        regex: /vimeo\.com/ },
  { name: "Dailymotion",  regex: /dailymotion\.com/ },
  { name: "Bilibili",     regex: /bilibili\.com/ },
  { name: "Rumble",       regex: /rumble\.com/ },
  { name: "Odysee",       regex: /odysee\.com/ },
  { name: "Instagram",    regex: /instagram\.com/ },
  { name: "SoundCloud",   regex: /soundcloud\.com/ },
];

function detectPlatform(host) {
  for (const p of PLATFORM_MAP) {
    if (p.regex.test(host)) return p.name;
  }
  return null;
}

function isYouTubeWatch() {
  return /youtube\.com/.test(location.hostname) && location.pathname.startsWith("/watch");
}

function getPageUrl() {
  return location.href;
}

function getPageTitle() {
  // Clean up platform-specific suffixes from the document title
  return document.title
    .replace(/\s[-|–]\s*(YouTube|Twitter|TikTok|Reddit|Facebook|Twitch|Vimeo|Instagram|X)\s*$/, "")
    .trim();
}

// ──────────────────────────────────────────────
// YouTube toolbar button
// ──────────────────────────────────────────────

function injectYouTubeToolbarButton() {
  if (document.getElementById("seal-yt-btn")) return;

  const container = document.querySelector(
    "#top-row #actions #actions-inner, #actions #top-level-buttons-computed, ytd-watch-metadata #actions"
  );
  if (!container) return;

  const btn = document.createElement("button");
  btn.id = "seal-yt-btn";
  btn.className = "seal-yt-btn";
  btn.title = "Download with Seal Desktop";
  btn.innerHTML = `<span class="seal-logo">🦭</span><span class="seal-label">Seal</span>`;

  btn.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    triggerWithFeedback(btn, ".seal-label", getPageUrl(), getPageTitle(), true);
  });

  container.prepend(btn);
}

// ──────────────────────────────────────────────
// Generic <video> overlay injection
// ──────────────────────────────────────────────

function injectVideoOverlays(host) {
  const platform = detectPlatform(host);
  const videos = document.querySelectorAll("video");

  videos.forEach((video) => {
    if (video.dataset.sealDone) return;

    // Determine video dimensions — videoWidth is only available after metadata loads
    // Fall back to layout size, and skip only if both are definitively tiny
    const layoutW = video.offsetWidth || video.getBoundingClientRect().width;
    const layoutH = video.offsetHeight || video.getBoundingClientRect().height;
    const mediaW = video.videoWidth || layoutW;
    const mediaH = video.videoHeight || layoutH;
    if (mediaW < 180 || mediaH < 100) return;
    // Extra guard: skip videos not yet attached to the document
    if (!document.body || !document.body.contains(video)) return;

    video.dataset.sealDone = "1";

    // Resolve the best available URL for this video
    const resolvedUrl = resolveVideoUrl(video);

    // Find/create a positioned wrapper we can absolutely-position inside
    const anchor = findOrCreateAnchor(video);
    if (!anchor) return;

    const overlay = buildOverlay(resolvedUrl, platform);
    anchor.appendChild(overlay);

    // Show overlay on hover (both video and overlay itself)
    let showTimer, hideTimer;
    const show = () => {
      clearTimeout(hideTimer);
      showTimer = setTimeout(() => overlay.classList.add("seal-visible"), 120);
    };
    const hide = () => {
      clearTimeout(showTimer);
      hideTimer = setTimeout(() => overlay.classList.remove("seal-visible"), 350);
    };

    video.addEventListener("mouseenter", show);
    video.addEventListener("mouseleave", hide);
    overlay.addEventListener("mouseenter", show);
    overlay.addEventListener("mouseleave", hide);
  });
}

/** Resolve the best URL to send — prefer page URL over blob: src */
function resolveVideoUrl(video) {
  const src = video.currentSrc || video.src || "";
  if (src && !src.startsWith("blob:") && !src.startsWith("data:")) {
    return src;
  }
  // For blob:, MSE, and embedded streams, use the page URL (yt-dlp handles it)
  return getPageUrl();
}

/** Find a relatively-positioned ancestor to use as the positioning context */
function findOrCreateAnchor(video) {
  // Walk up to find a natural container that is already positioned
  let el = video.parentElement;
  for (let i = 0; i < 6; i++) {
    if (!el) break;
    const pos = getComputedStyle(el).position;
    if (pos === "relative" || pos === "absolute" || pos === "fixed" || pos === "sticky") {
      return el;
    }
    el = el.parentElement;
  }
  // Otherwise force the direct parent to be positioned
  if (video.parentElement) {
    video.parentElement.style.position = "relative";
    return video.parentElement;
  }
  return null;
}

/** Build the floating overlay element */
function buildOverlay(resolvedUrl, platform) {
  const overlay = document.createElement("div");
  overlay.className = "seal-overlay";

  const label = platform ? `${platform}` : "Video";

  overlay.innerHTML = `
    <div class="seal-overlay-inner">
      <div class="seal-overlay-header">
        <span class="seal-overlay-logo">🦭</span>
        <span class="seal-overlay-title">Seal Desktop</span>
        <span class="seal-overlay-platform">${escapeHtml(label)}</span>
      </div>
      <div class="seal-overlay-actions">
        <button class="seal-btn-dl" data-url="${escapeHtml(resolvedUrl)}" title="Download immediately">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M12 16l-6-6h4V4h4v6h4l-6 6zm-8 4h16v-2H4v2z"/></svg>
          Download Now
        </button>
        <button class="seal-btn-queue" data-url="${escapeHtml(resolvedUrl)}" title="Add to Seal queue">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg>
          Add to Queue
        </button>
      </div>
    </div>
  `;

  // Download Now
  overlay.querySelector(".seal-btn-dl").addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    const btn = e.currentTarget;
    sendDownload(btn.dataset.url, getPageTitle(), true, btn, overlay);
  });

  // Add to Queue
  overlay.querySelector(".seal-btn-queue").addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    const btn = e.currentTarget;
    sendDownload(btn.dataset.url, getPageTitle(), false, btn, overlay);
  });

  return overlay;
}

// ──────────────────────────────────────────────
// Send download / feedback
// ──────────────────────────────────────────────

function sendDownload(url, title, autoStart, clickedBtn, overlay) {
  const originalHtml = clickedBtn.innerHTML;
  clickedBtn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10" opacity=".3"/></svg> Sending…`;
  clickedBtn.disabled = true;

  chrome.runtime.sendMessage(
    {
      type: "TRIGGER_DOWNLOAD",
      payload: { url, title, auto_start: autoStart },
    },
    (res) => {
      clickedBtn.disabled = false;
      if (res && res.success) {
        showOverlayFeedback(overlay, autoStart ? "✓ Downloading in Seal!" : "✓ Added to queue!", "success");
      } else {
        showOverlayFeedback(overlay, "⚠ Seal Desktop is offline", "error");
      }
      setTimeout(() => {
        clickedBtn.innerHTML = originalHtml;
      }, 2000);
    }
  );
}

function showOverlayFeedback(overlay, msg, type) {
  let toast = overlay.querySelector(".seal-overlay-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.className = "seal-overlay-toast";
    overlay.querySelector(".seal-overlay-inner").appendChild(toast);
  }
  toast.textContent = msg;
  toast.className = `seal-overlay-toast seal-toast-${type}`;
  clearTimeout(overlay._toastTimer);
  overlay._toastTimer = setTimeout(() => { toast.textContent = ""; toast.className = "seal-overlay-toast"; }, 3500);
}

function triggerWithFeedback(btnEl, labelSel, url, title, autoStart) {
  const labelEl = btnEl.querySelector(labelSel);
  const orig = labelEl ? labelEl.textContent : "";
  if (labelEl) labelEl.textContent = "Sending…";
  btnEl.disabled = true;

  chrome.runtime.sendMessage(
    { type: "TRIGGER_DOWNLOAD", payload: { url, title, auto_start: autoStart } },
    (res) => {
      btnEl.disabled = false;
      if (labelEl) {
        labelEl.textContent = res && res.success ? "✓ In Seal!" : "⚠ Offline";
        setTimeout(() => { labelEl.textContent = orig; }, 3000);
      }
    }
  );
}

// ──────────────────────────────────────────────
// Cleanup & Utilities
// ──────────────────────────────────────────────

function cleanupOrphanedOverlays() {
  document.querySelectorAll(".seal-overlay").forEach(el => el.remove());
  document.querySelectorAll("video[data-seal-done]").forEach(v => {
    delete v.dataset.sealDone;
  });
  const ytBtn = document.getElementById("seal-yt-btn");
  if (ytBtn) ytBtn.remove();
  // Cancel the URL polling interval if extension is being torn down
  if (_urlPollId && !_enabled) {
    clearInterval(_urlPollId);
    _urlPollId = null;
  }
}

function debounce(fn, ms) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
