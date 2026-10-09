# Seal Desktop — Issues Ordered by User Impact

Severity key: 🔴 Breaks core functionality · 🟠 Degrades reliability · 🟡 Minor annoyance · 🟢 Enhancement

---

## Tier 1 — Breaks Core Functionality

### #1 🔴 Ghost task after delete  
**B2 · [`downloader.py`](file:///c:/projects/tyn/seal-desktop/src/core/downloader.py#L395) · Effort: Low**

When a card is deleted while metadata is still being prefetched in the background, the prefetch thread calls `_update_task()` on the deleted task, silently re-inserting it into `_tasks`. The user sees no card for it, but internally the queue treats it as an active item — this can block subsequent downloads from ever starting.

**Fix:** In `_update_task`, skip the write if `task.task_id` is no longer in `self._tasks`.
```python
def _update_task(self, task: DownloadTask) -> None:
    with self._lock:
        if task.task_id not in self._tasks:  # ← add this guard
            return
        self._tasks[task.task_id] = task
    self.on_task_updated(task)
```

---

### #2 🔴 TOCTOU race — two workers start on the same task  
**R2 · [`downloader.py`](file:///c:/projects/tyn/seal-desktop/src/core/downloader.py#L376) · Effort: Low**

`thread.start()` is called **after** the lock is released, so if two threads reach `_process_next_in_queue` simultaneously (e.g. `start_queue` thread + `_on_task_finished` callback), both can pick the same next task and launch two download workers for it — producing duplicate files or a crash.

**Fix:** Set `_active_task_id` inside the lock before releasing it, which makes the second thread see a non-None active ID and bail out correctly. The current code already does this; the real fix is to also start the thread **while still holding the lock** or use a threading `Semaphore(1)`.

---

### #3 🔴 Queue stuck permanently after pausing a not-yet-started task  
**B1 · [`downloader.py`](file:///c:/projects/tyn/seal-desktop/src/core/downloader.py#L253) · Effort: Medium**

Pausing a QUEUED item (before its worker thread starts) sets it to PAUSED without ever launching a worker. `_active_task_id` is still `None`. Later, if the user deletes that paused task while another download is active, `delete_task` sets `was_active = (self._active_task_id == task_id)` → `False`, so `_process_next_in_queue` is never triggered and the queue freezes.

**Fix:** In `delete_task`, always call `_process_next_in_queue()` when `_queue_running`, not only when `was_active`.

---

### #4 🔴 Global mousewheel capture breaks all scroll areas  
**B4 · [`widgets.py`](file:///c:/projects/tyn/seal-desktop/src/ui/widgets.py) · Effort: Low**

`bind_all("<MouseWheel>", …)` in `SealScrollFrame` intercepts every scroll event in the entire application. Settings, Downloads, and History pages all use `SealScrollFrame`. The **last one created** captures all scroll events — so scrolling the Downloads list may actually scroll the hidden Settings page instead, and vice versa.

**Fix:** Replace `bind_all` with enter/leave-scoped binding:
```python
self._canvas.bind("<Enter>", lambda _: self._canvas.bind_all("<MouseWheel>", self._on_mousewheel))
self._canvas.bind("<Leave>", lambda _: self._canvas.unbind_all("<MouseWheel>"))
```

---

### #5 🔴 No URL validation — yt-dlp receives garbage input  
**R1 · [`download_page.py`](file:///c:/projects/tyn/seal-desktop/src/ui/pages/download_page.py#L550) · Effort: Low**

Any string (including clipboard noise like `"hello"`, `"undefined"`, whitespace) is sent directly to yt-dlp. yt-dlp errors with a cryptic exception that surfaces as `❌ Error: …` in the card with a 10+ second delay. Users assume the app is broken.

**Fix:** A quick check before queuing:
```python
import re
URL_RE = re.compile(r"https?://[^\s]+", re.IGNORECASE)
if not URL_RE.match(url):
    messagebox.showwarning(...)
    return
```

---

## Tier 2 — Degrades Reliability / Data Integrity (ALL FIXED ✅)

### #6 🟠 Wrong output_path stored — "Open Folder" opens a .part temp file location `[FIXED]`  
**B7 · [`downloader.py`](file:///c:/projects/tyn/seal-desktop/src/core/downloader.py#L585) · Effort: Low**

The `_progress_hook` stores `filename` as `output_path` when yt-dlp status is `"finished"`. At that moment the file is still the raw un-merged `.part` stream. The final path only arrives in `_postproc_hook`. If FFmpeg conversion fails silently, `output_path` remains the `.part` path and the folder button points to a broken file.

**Fix Applied:** `_postproc_hook` is now the authoritative source (`filepath` / `filename`), and `_progress_hook` only sets `output_path` if not already set. Also strips `.part` suffix on task completion if the cleaned destination file exists on disk.

---

### #7 🟠 Update banner crashes when page hasn't been navigated to yet `[FIXED]`  
**B5 · [`app_shell.py`](file:///c:/projects/tyn/seal-desktop/src/ui/app_shell.py#L289) · Effort: Trivial**

The startup update check fires after 3 s. If the user hasn't navigated away from the download page, `self._pages.get("download")` is fine. But if the page dict is empty for any reason, `before=None` raises a `TclError` on some Tkinter builds, crashing the update banner silently.

**Fix Applied:** Verified `current_page_widget and current_page_widget.winfo_exists() and current_page_widget.winfo_manager() == "pack"` before adding `before=...` to `pack_kwargs`.

---

### #8 🟠 Disk write on every single setting change `[FIXED]`  
**B3 · [`settings.py`](file:///c:/projects/tyn/seal-desktop/src/core/settings.py#L86) · Effort: Medium**

`settings.set()` always calls `self.save()` which rewrites the entire JSON file. Dropdowns in the settings page have `trace_add("write", _on_change)`, which fires on every character in a text field. On spinning-disk machines this introduces noticeable lag when typing.

**Fix Applied:** Added value-equality checks to avoid redundant writes, added 300 ms debounced saves using a background `threading.Timer`, thread-safety locks, explicit `flush()`, and registered `atexit` save.

---

### #9 🟠 Single-instance guard missing — two instances corrupt settings.json `[FIXED]`  
**E9 · [`main.py`](file:///c:/projects/tyn/seal-desktop/main.py) · Effort: Low**

Launching Seal Desktop twice causes both processes to read and write `settings.json` concurrently. The last writer wins, silently discarding history entries or preference changes made in the first window.

**Fix Applied:** Added `_acquire_instance_lock()` and `_release_instance_lock()` in `main.py` using `seal.lock` in the app's user configuration directory. Checks if existing PID is actively alive (using Win32 process handles on Windows / signal 0 elsewhere) before alerting the user with translated dialog (`app_already_running_msg` in `en` and `ar`) and exiting.

---

### #10 🟠 Window geometry saved when minimized — restores as tiny window `[FIXED]`  
**E2 · [`main.py`](file:///c:/projects/tyn/seal-desktop/main.py#L77) · Effort: Trivial**

`root.geometry()` when the window is minimized returns a geometry with height = 0 or the last known size with an iconified state bit. Storing and restoring this makes the window appear as a tiny sliver on next launch.

**Fix Applied:** Guarded geometry persistence in `_on_close` to only save when `root.state() == "normal"` and parsed width/height exceed minimum valid thresholds (>= 400x300). Also enforced minimum bounds (`800x540`) on restore.
```

---

## Tier 3 — Minor Annoyances / Polish

### #11 🟡 Search placeholder not updated on language switch  
**B6 · [`history_page.py`](file:///c:/projects/tyn/seal-desktop/src/ui/pages/history_page.py#L163) · Effort: Trivial**

`_retranslate` in `HistoryPage` is missing:
```python
self._search_entry.update_placeholder(t("search_history_placeholder"))
```

---

### #12 🟡 Hardcoded English status strings in settings actions  
**B8 · [`settings_page.py`](file:///c:/projects/tyn/seal-desktop/src/ui/pages/settings_page.py#L470) · Effort: Low**

`"Checking…"`, `"Installing…"`, `"Downloading…"`, and `"Ready!"` are hardcoded English in button labels. Add i18n keys and use `t()` for all of them.

---

### #13 🟡 macOS/Linux FFmpeg install leaves button stuck on "Installing…"  
**B9 · [`ffmpeg_utils.py`](file:///c:/projects/tyn/seal-desktop/src/core/ffmpeg_utils.py#L105) · Effort: Trivial**

`progress_callback` is never called before `done_callback(False, …)` on non-Windows, so the button text never resets.

**Fix:** Call `progress_callback(0.0, "")` first on all platforms.

---

### #14 🟡 `_trans_labels` list in settings could reference destroyed widgets  
**E8 · [`settings_page.py`](file:///c:/projects/tyn/seal-desktop/src/ui/pages/settings_page.py) · Effort: Low**

If the settings page is ever recreated or partially destroyed while a language switch fires, `_retranslate` will attempt `.configure()` on dead Tkinter widgets and raise a silent `TclError`. Guard each with `lbl.winfo_exists()`.

---

## Tier 4 — Features / Enhancements

### #15 🟢 Retry button on error state  
**E4 · [`download_page.py`](file:///c:/projects/tyn/seal-desktop/src/ui/pages/download_page.py) · Effort: Low**

When a download fails, the card only shows a delete button. A Retry button (`downloader.start_download(task.url, task.prefs)`) would save users from manually copy-pasting the URL again.

---

### #16 🟢 Light mode toggle  
**E1 · [`theme.py`](file:///c:/projects/tyn/seal-desktop/src/ui/theme.py) · Effort: Medium**

`LIGHT_OVERRIDES` and `get_palette(dark: bool)` already exist. A toggle in Settings and a full widget refresh would complete this.

---

### #17 🟢 Timestamp in history entries  
**E5 · [`settings.py`](file:///c:/projects/tyn/seal-desktop/src/core/settings.py#L95) · Effort: Trivial**

Add `"downloaded_at": datetime.now().isoformat()` in `add_history()` and display it in `HistoryRow`.

---

### #18 🟢 Concurrent downloads (configurable pool)  
**E6 · [`downloader.py`](file:///c:/projects/tyn/seal-desktop/src/core/downloader.py) · Effort: High**

Replace the single `_active_task_id` with a `threading.Semaphore(max_concurrent)` pool. Expose a slider in Settings (1–5). Queue would then run up to N tasks simultaneously.

---

### #19 🟢 Styled scrollbar (native scrollbar clashes with dark theme)  
**E3 · [`widgets.py`](file:///c:/projects/tyn/seal-desktop/src/ui/widgets.py) · Effort: Medium**

Replace `tk.Scrollbar` with a Canvas-drawn custom scrollbar using `P["scrollbar"]` and `P["scrollbar_hover"]` colors (already defined in the palette but unused).

---

### #20 🟢 FFmpeg binary integrity check after download  
**E10 · [`ffmpeg_utils.py`](file:///c:/projects/tyn/seal-desktop/src/core/ffmpeg_utils.py) · Effort: Low**

Add SHA256 verification of the downloaded `ffmpeg.exe` against a pinned hash before using it.

---

## One-Page Summary

| # | Severity | ID | Description | Effort |
|---|----------|----|-------------|--------|
| 1 | 🔴 | B2 | Ghost task blocks queue after delete | Low |
| 2 | 🔴 | R2 | TOCTOU race — duplicate workers | Low |
| 3 | 🔴 | B1 | Queue frozen after pausing queued task | Med |
| 4 | 🔴 | B4 | Global mousewheel hijack in scroll frames | Low |
| 5 | 🔴 | R1 | No URL validation before queuing | Low |
| 6 | 🟠 | B7 | output_path = .part file, open folder broken | Low |
| 7 | 🟠 | B5 | Update banner crash if page not yet loaded | Trivial |
| 8 | 🟠 | B3 | Disk write on every setting change | Med |
| 9 | 🟠 | E9 | No single-instance guard | Low |
| 10 | 🟠 | E2 | Minimized geometry saved on close | Trivial |
| 11 | 🟡 | B6 | Search placeholder not retranslated | Trivial |
| 12 | 🟡 | B8 | Hardcoded English action strings | Low |
| 13 | 🟡 | B9 | macOS FFmpeg button stuck | Trivial |
| 14 | 🟡 | E8 | Destroyed widget reference in retranslate | Low |
| 15 | 🟢 | E4 | Retry button on error | Low |
| 16 | 🟢 | E1 | Light mode toggle | Med |
| 17 | 🟢 | E5 | Timestamp in history | Trivial |
| 18 | 🟢 | E6 | Concurrent downloads | High |
| 19 | 🟢 | E3 | Custom styled scrollbar | Med |
| 20 | 🟢 | E10 | FFmpeg binary integrity check | Low |

> Scanned: all 9 source files across `src/core/` and `src/ui/`.

---

## 🔴 Bugs (Confirmed Defects)

### B1 · `downloader.py` — Pausing a QUEUED task breaks the queue permanently
**File:** [`downloader.py`](file:///c:/projects/tyn/seal-desktop/src/core/downloader.py#L253-L263)

When a QUEUED (not yet started) task is paused and then resumed, `resume_download` puts it back to `QUEUED` but `_queue` still contains its ID. However, after a `pause_queue()` followed by re-adding the same item, `_active_task_id` may already point to a finished task (never cleared), causing `_process_next_in_queue` to return early thinking a task is still active.

**Root cause:** `_active_task_id` is only cleared in `_on_task_finished` — but `_on_task_finished` is only called by `_worker`. Pausing a QUEUED task (before the worker starts) never calls `_worker`, so `_active_task_id` could remain set to the old completed task ID.

**Fix:** In `_on_task_finished`, also clear stale IDs from `_cancel_flags`/`_pause_flags`. And in `delete_task`, ensure `_active_task_id` is explicitly set to `None` even if no thread ran.

---

### B2 · `downloader.py` — `_prefetch_task_info` runs even after task is deleted
**File:** [`downloader.py`](file:///c:/projects/tyn/seal-desktop/src/core/downloader.py#L395-L495)

`queue_download` always spawns a prefetch thread. If the user deletes the card immediately, `delete_task` removes the task from `_tasks`, but the prefetch thread is still running and calls `_update_task(task)` on a now-deleted task — which re-inserts it into `_tasks` via `self._tasks[task.task_id] = task`, causing a ghost entry that has no UI card.

**Fix:** Check `task_id in self._tasks` in `_update_task` before writing, or add a cancel event to `_prefetch_task_info`.

---

### B3 · `settings.py` — `settings.set()` writes to disk on every keystroke
**File:** [`settings.py`](file:///c:/projects/tyn/seal-desktop/src/core/settings.py#L86-L88)

`_entry_row` in `settings_page.py` binds `<FocusOut>` → `settings.set(key, ent.get())`. But dropdown rows use `var.trace_add("write", _on_change)` which fires on every character typed if the user modifies a text field programmatically. Every `settings.set()` calls `self.save()` which does a full JSON write.

**Fix:** Debounce or batch writes. At minimum, only save if the value actually changed.

---

### B4 · `widgets.py` — `SealScrollFrame` binds `<MouseWheel>` globally (`bind_all`)
**File:** [`widgets.py`](file:///c:/projects/tyn/seal-desktop/src/ui/widgets.py#L508-L518) (old line ref, ~line 510 post-edits)

`self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)` captures **all** mousewheel events app-wide, even when another scroll frame is visible. If two `SealScrollFrame` instances exist simultaneously (e.g. settings + download page are both in memory), the last one created "wins" and scrolls when the user is hovering over the other.

**Fix:** Bind only on `<Enter>`/`<Leave>` to activate/deactivate the handler, or use `bind` instead of `bind_all`.

---

### B5 · `app_shell.py` — Update banner is inserted before a `None` widget
**File:** [`app_shell.py`](file:///c:/projects/tyn/seal-desktop/src/ui/app_shell.py#L289)

```python
self._update_banner.pack(fill="x", side="top", before=self._pages.get(self._current_page))
```

`self._pages.get(self._current_page)` returns `None` if the page hasn't been created yet (race between startup 3-second timer and navigation). Tkinter silently ignores `before=None` on some builds, but on others it raises `TclError`.

**Fix:** Guard: `before=self._pages.get(self._current_page) or None` works, but better to always ensure the page exists first, or pack without `before`.

---

### B6 · `history_page.py` — `_retranslate` does not update search placeholder
**File:** [`history_page.py`](file:///c:/projects/tyn/seal-desktop/src/ui/pages/history_page.py#L163-L166)

`_retranslate` updates title and clear button, but never calls `self._search_entry.update_placeholder(t("search_history_placeholder"))`, so after a language switch the history search box still shows the old placeholder.

**Fix:** Add `self._search_entry.update_placeholder(t("search_history_placeholder"))` to `_retranslate`.

---

### B7 · `downloader.py` — `output_path` from `_progress_hook` is the `.part` temp file
**File:** [`downloader.py`](file:///c:/projects/tyn/seal-desktop/src/core/downloader.py#L585-L589)

In `_progress_hook`, on `status == "finished"`:
```python
task.output_path = d.get("filename") or ""
```
At this point yt-dlp hasn't yet merged/converted the file — `filename` is the `.part` or raw stream file. The final merged path arrives later via `_postproc_hook`. But if FFmpeg conversion fails silently, `output_path` stays as the `.part` path and the "Open Folder" button opens a directory containing a broken partial file.

**Fix:** Prefer `_postproc_hook`'s `filepath` as the canonical `output_path`, and fall back to `_progress_hook`'s `filename` only if post-processing doesn't fire.

---

### B8 · `settings_page.py` — `_check_app_updates_clicked` label uses hardcoded English "Checking…"
**File:** [`settings_page.py`](file:///c:/projects/tyn/seal-desktop/src/core/../ui/pages/settings_page.py#L470)

```python
self._app_update_btn.configure_text("Checking…")
```

Also in `_setup_ffmpeg`: `"Installing…"`, in `_download_and_run_update`: `"Downloading…"` and `"Ready!"` — all hardcoded English strings not going through `t()`.

**Fix:** Add i18n keys `btn_checking`, `btn_installing`, `btn_downloading`, `btn_ready` and use them.

---

### B9 · `ffmpeg_utils.py` — No progress on macOS/Linux; non-Windows users get no feedback
**File:** [`ffmpeg_utils.py`](file:///c:/projects/tyn/seal-desktop/src/core/ffmpeg_utils.py#L105-L110)

The `download_ffmpeg_async` worker immediately calls `done_callback(False, "Please install…")` on non-Windows without calling `progress_callback` at all. The button text will stay "Installing…" if the UI only resets on `done_callback`.

**Fix:** Call `progress_callback(0.0, "Not supported on this platform")` before `done_callback`.

---

## 🟡 Robustness / UX Issues

### R1 · `downloader.py` — No URL validation before queuing
Any string (including empty after strip, or non-URL like "hello") is passed directly to yt-dlp. yt-dlp will error, but the error message is cryptic. A simple `http://` or `https://` prefix check + domain validation would give a much better UX.

---

### R2 · `downloader.py` — `_process_next_in_queue` has a TOCTOU race
Between the `with self._lock:` block where `next_task` is chosen and `thread.start()` is called **outside** the lock, another thread could call `_process_next_in_queue` simultaneously. Both threads pick the same `next_task` and two workers start for the same task.

**Fix:** Move `thread.start()` inside the lock, or add a guard that sets `_active_task_id` **before** releasing the lock.

---

### R3 · `settings.py` — History deduplication compares full URL only
```python
history = [h for h in history if h.get("url") != entry.get("url")]
```
If a user re-downloads the same video with a different quality, the old entry (with the old file path) is discarded even if that file still exists and the new one hasn't finished yet. Also there's no timestamp stored in the history entry, making it impossible to sort or display "Downloaded 2 days ago".

---

### R4 · `app_shell.py` — Pages are never destroyed when navigating away
```python
self._pages[page_id].pack_forget()
```
Pages are hidden with `pack_forget` but never destroyed. The `DownloadPage` holds `downloader.on_task_updated` as a reference — when `DownloadPage` is hidden but not destroyed, task updates still call into the old page. This is fine as long as only one `DownloadPage` exists, but the pattern could leak callbacks if pages were ever recreated.

---

### R5 · `download_page.py` — `_collect_current_prefs` reloads from settings every time
```python
def _collect_current_prefs(self) -> DownloadPreferences:
    prefs = self._load_prefs()  # reads from settings on disk
    prefs.extract_audio = self._audio_var.get()
    ...
```
`_load_prefs` calls `settings.get()` for every field, meaning a disk read on every download. The live UI var values (`_audio_var`, `_quality_var`, etc.) are then applied on top. But codec and container overrides **only** come from settings, not from UI vars — so if the user changes the codec dropdown mid-session, it **will** apply because it's stored to settings via the OptionMenu trace. But the copy of prefs is fresh each time, which is redundant disk access.

---

### R6 · `download_page.py` — Playlist item count is wrong for nested playlists
In `_worker`, `task.playlist_count = len(info.get("entries") or [])` is set from the flat list. For nested playlists (e.g. a YouTube channel), `entries` is a list of playlist stubs, not individual videos, so `playlist_count` will show an incorrect low number.

---

## 🟢 Enhancement Opportunities

### E1 · Light Mode / Theming
`theme.py` has a full `LIGHT_OVERRIDES` dict and a `get_palette(dark: bool)` function, but it's never called. The Settings page even has a `theme` key in defaults. Wiring up a dark/light toggle would be straightforward.

---

### E2 · Window geometry persistence is lossy
`_on_close` parses `root.geometry()` string with a split — but if the window is minimized at close time, the geometry string returns the minimized state, storing a negative or zero height. A guard `if int(parts[1]) > 100` would prevent saving a bad geometry.

---

### E3 · `SealScrollFrame` — No scroll indicator styling
The native `tk.Scrollbar` is used unstyled. On Windows it uses the system scrollbar (blue on Win11), which clashes with the dark theme. A custom Canvas-based scrollbar would match the design.

---

### E4 · `DownloadCard` — No retry button on error state
When a download errors, only a delete button is shown. A "Retry" button that calls `downloader.start_download(task.url, task.prefs)` would greatly improve UX.

---

### E5 · `history_page.py` — No timestamp in history entries
History items have no date. Adding `"downloaded_at": datetime.now().isoformat()` in `settings.add_history()` and displaying it in `HistoryRow` would make the history page much more useful.

---

### E6 · `downloader.py` — No concurrent download option
The queue is strictly sequential. A `max_concurrent` setting (default 1) with a semaphore-based pool would allow power users to download 2-3 items simultaneously.

---

### E7 · `i18n.py` — No pluralization support
`queue_summary` uses `"{count} item(s)"` as a workaround. A proper `ngettext`-style helper for singular/plural would improve Arabic text quality significantly (Arabic has 6 plural forms).

---

### E8 · `settings_page.py` — `_trans_labels` list approach is fragile
Labels are registered with `(widget, key)` tuples in a list. If `_retranslate` is called while the page is partially built (e.g. during an async language switch), it could reference already-destroyed widgets and crash silently. A safer pattern would be to store `WeakRef` objects or re-check `widget.winfo_exists()`.

---

### E9 · `main.py` — No single-instance guard
If the user launches Seal Desktop twice, two instances will run and both will write to the same `settings.json` concurrently. A lock file in the user data directory would prevent this.

---

### E10 · `ffmpeg_utils.py` — No integrity check after download
After downloading and extracting `ffmpeg.exe`, there is no hash/signature verification. A man-in-the-middle or a corrupt partial download could place a bad binary. Checking the SHA256 against a pinned known-good value would improve security.

---

## Priority Summary

| ID | Category | Severity | Effort | Status |
|----|----------|----------|--------|--------|
| B2 | Ghost task after delete | 🔴 High | Low | ✅ Fixed (Tier 1) |
| B4 | Global mousewheel capture | 🔴 High | Low | ✅ Fixed (Tier 1) |
| B1 | Queue stuck after pause | 🟠 Med | Med | ✅ Fixed (Tier 1) |
| R2 | TOCTOU race in queue | 🟠 Med | Low | ✅ Fixed (Tier 1) |
| R1 | No URL validation | 🟡 Low | Low | ✅ Fixed (Tier 1) |
| B7 | Wrong output_path (.part) | 🟠 Med | Low | ✅ Fixed (Tier 2) |
| B5 | Update banner crash | 🟠 Med | Low | ✅ Fixed (Tier 2) |
| B3 | Disk write on every keystroke | 🟡 Low | Med | ✅ Fixed (Tier 2) |
| E9 | Single-instance guard | 🟢 Feature | Low | ✅ Fixed (Tier 2) |
| E2 | Window geometry minimized restore | 🟠 Med | Trivial | ✅ Fixed (Tier 2) |
| B8 | Hardcoded English strings | 🟡 Low | Low | ⏳ Pending (Tier 3) |
| B6 | Search placeholder not retranslated | 🟡 Low | Trivial | ⏳ Pending (Tier 3) |
| B9 | macOS progress callback missing | 🟡 Low | Trivial | ⏳ Pending (Tier 3) |
| E4 | Retry button on error | 🟢 Feature | Low | ⏳ Pending (Tier 3) |
| E5 | Timestamp in history | 🟢 Feature | Trivial | ⏳ Pending (Tier 3) |
| E1 | Light mode toggle | 🟢 Feature | Med | ⏳ Pending (Tier 4) |
| E6 | Concurrent downloads | 🟢 Feature | High | ⏳ Pending (Tier 4) |
| E10 | FFmpeg download integrity check | 🟢 Feature | Med | ⏳ Pending (Tier 4) |
