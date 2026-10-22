"""
Seal Desktop - Internationalization (i18n) Module
Supports English (en) and Arabic (ar) with on-the-fly switching.
"""

from __future__ import annotations

from collections.abc import Callable

_current_lang = "en"
_listeners: list[Callable[[], None]] = []

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        # App & Nav
        "app_title": "Seal Desktop",
        "app_subtitle": "Desktop",
        "nav_download": "Download",
        "nav_history": "History",
        "nav_settings": "Settings",
        "app_footer": "v1.5.3 · Powered by yt-dlp",
        # Download Page Header & Inputs
        "page_download_title": "Download",
        "url_placeholder": "Paste a YouTube, Facebook, SoundCloud, or any supported URL…",
        "btn_download_now": "Download Now",
        "btn_add_queue": "Add to Queue",
        "btn_start_queue": "Start Downloads",
        "btn_pause_queue": "Pause Queue",
        "btn_clear_done": "Clear done",
        "label_download_mode": "Mode:",
        "mode_video": "🎬 Video + Audio",
        "mode_audio": "🎵 Audio only",
        "mode_subtitles": "💬 Subtitles only",
        "audio_only": "Audio only",
        "subtitles_only": "Subtitles only",
        "video_quality": "Quality:",
        "video_codec": "Codec:",
        "audio_format": "Format:",
        "output_folder": "Output Folder",
        "downloads_header": "Downloads Queue",
        "queue_status_running": "▶ Queue Running (Successive)",
        "queue_status_paused": "⏸ Queue Paused",
        "queue_summary": "{count} item(s) in queue · {active} active",
        "empty_downloads": "No downloads yet.\nPaste a URL above to add to queue or download! 🚀",
        # Task Card States & Actions
        "state_idle": "Idle",
        "state_queued": "⏳ Queued (Waiting)",
        "state_fetching": "🔍 Fetching info…",
        "state_downloading": "⬇ Downloading",
        "state_playlist": "⬇ Playlist {index}/{count}",
        "state_paused": "⏸ Paused",
        "state_converting": "⚙ Merging & Processing…",
        "state_completed": "✅ Completed",
        "state_cancelled": "🚫 Cancelled",
        "state_error": "❌ Error",
        "btn_pause": "Pause",
        "btn_resume": "Resume",
        "btn_delete": "Delete",
        "btn_cancel": "Cancel",
        "btn_open_folder": "Open folder",
        # FFmpeg banner
        "ffmpeg_banner_title": "⚠️ FFmpeg Not Detected",
        "ffmpeg_banner_desc": "Without FFmpeg, video & audio will use single-stream format to avoid separate files.",
        "btn_install_ffmpeg_quick": "Install FFmpeg",
        "ffmpeg_installed_success": "FFmpeg installed successfully! Video & audio will now merge seamlessly.",
        # History Page
        "history_title": "History",
        "btn_clear_all": "🗑 Clear all",
        "search_history_placeholder": "Search history…",
        "empty_history": "No downloads yet.\nStart downloading to build your history! 📼",
        # Settings Page
        "settings_title": "Settings",
        "sec_general": "General & Language",
        "label_language": "Interface Language",
        "label_theme": "Theme",
        "sec_download": "Download Options",
        "label_output_dir": "Output folder",
        "label_output_template": "Output template",
        "label_playlist_subdir": "Playlist subdirectory",
        "label_restrict_filenames": "Restrict filenames (ASCII)",
        "sec_format": "Format & Merging",
        "label_default_mode": "Default download mode",
        "label_default_audio": "Audio only by default",
        "label_audio_format": "Audio format",
        "label_video_quality": "Video quality",
        "label_video_container": "Merged video format",
        "label_video_codec": "Video codec (compatibility)",
        "sec_ffmpeg": "FFmpeg Engine (Audio/Video Merger)",
        "ffmpeg_ready": "FFmpeg is ready: audio and video will be merged into a single file.",
        "ffmpeg_missing": "FFmpeg is missing: videos may be restricted or lack high-res merging.",
        "btn_setup_ffmpeg": "⬇ Download & Setup FFmpeg",
        "theme_dark": "Dark",
        "theme_light": "Light",
        "theme_system": "System",
        "sec_postproc": "Post-processing",
        "label_embed_metadata": "Embed metadata",
        "label_embed_thumbnail": "Embed thumbnail",
        "label_embed_subtitles": "Embed subtitles",
        "label_extract_chapters": "Extract chapters",
        "label_sponsorblock": "Remove sponsor segments (SponsorBlock)",
        "label_sub_languages": "Subtitle languages",
        "label_sub_source": "Subtitle source",
        "sub_source_manual": "Manual/Uploaded",
        "sub_source_auto": "Auto-generated",
        "sub_source_both": "Both",
        "sub_source_label": "Source:",
        "sec_network": "Network & Performance",
        "label_proxy": "HTTP proxy",
        "label_rate_limit": "Rate limit",
        "label_aria2c": "Use aria2c (faster)",
        "label_concurrent": "Concurrent fragments",
        "label_max_concurrent": "Concurrent downloads",
        "label_cookies": "Cookies file (Netscape)",
        "sec_behaviour": "Behaviour",
        "label_desktop_notifications": "Desktop notifications",
        "label_clipboard_monitor": "Clipboard URL monitor",
        "label_api_server": "Browser extension companion server",
        "clipboard_detected_title": "URL Detected",
        "clipboard_detected_msg": "A URL was detected in your clipboard:\n{url}\n\nAdd to download queue?",
        "btn_add_to_queue": "Add to Queue",
        "btn_ignore": "Ignore",
        "sec_advanced": "Advanced",
        "label_log_file": "Diagnostic log file",
        "btn_open_log": "Open Log",
        "btn_export_settings": "Export Settings",
        "btn_import_settings": "Import Settings",
        "settings_exported": "Settings exported successfully.",
        "settings_imported": "Settings imported successfully. Restart recommended.",
        "settings_import_error": "Failed to import settings: {error}",
        "sec_updates": "App Updates & Auto-Updater",
        "label_auto_check": "Check for updates automatically on startup",
        "btn_check_updates": "🔄 Check for App Updates",
        "btn_update_ytdlp": "⬆ Update yt-dlp",
        "sec_about": "About",
        "about_desc": "Seal Desktop v1.5.3\nA modern cross-platform video & audio downloader powered by yt-dlp.\nFeatures: sequential queue, audio-video merger, companion browser extension, auto-updater.",
        # Dialogs / Updates
        "update_available_title": "New Update Available!",
        "update_available_msg": "Version {version} is available! (Current: {current})",
        "update_notes_title": "What's New in this Update:",
        "btn_download_update": "Download & Install Update",
        "btn_view_release": "View on GitHub",
        "btn_close": "Close",
        "up_to_date": "You are using the latest version of Seal Desktop ({version}).",
        "update_check_failed": "Failed to check for updates. Check your internet connection.",
        "browse": "Browse",
        "status_checking": "Checking…",
        "status_installing": "Installing…",
        "status_downloading": "Downloading…",
        "status_ready": "Ready!",
        "status_updating": "Updating…",
        # Entry context menu
        "ctx_cut": "Cut",
        "ctx_copy": "Copy",
        "ctx_paste": "Paste",
        "ctx_select_all": "Select All",
        # URL validation
        "invalid_url_title": "Invalid URL",
        "invalid_url_msg": "Please enter a valid URL starting with http:// or https://.",
        "unsupported_site_title": "Unsupported Site",
        "unsupported_site_msg": "This platform is not supported or the URL is invalid. Please check the URL and try again.",
        # Download page extras
        "btn_pick_format": "Pick Format",
        "btn_select_items": "Select Items",
        "format_picker_title": "Select Format",
        "playlist_picker_title": "Select Playlist Items",
        "btn_download_selected": "Download Selected",
        "btn_move_up": "▲",
        "btn_move_down": "▼",
        "history_redownload": "↻ Re-download",
        "notify_completed_title": "Download Completed",
        "notify_completed_msg": "{title} has been saved.",
        "notify_subs_completed_title": "Subtitles Downloaded",
        "notify_subs_completed_msg": "Subtitles saved for {title}.",
        "notify_error_title": "Download Failed",
        "notify_error_msg": "{title}: {error}",
        # Single instance
        "app_already_running_title": "Seal Desktop",
        "app_already_running_msg": "Another instance of Seal Desktop is already running.",
    },
    "ar": {
        # App & Nav
        "app_title": "سيل ديسكتوب",
        "app_subtitle": "ديسكتوب",
        "nav_download": "التحميل",
        "nav_history": "السجل",
        "nav_settings": "الإعدادات",
        "app_footer": "الإصدار 1.5.3 · مدعوم بواسطة yt-dlp",
        # Download Page Header & Inputs
        "page_download_title": "التحميل",
        "url_placeholder": "ألصق رابط يوتيوب أو فيسبوك أو ساوند كلاود أو أي رابط مدعوم…",
        "btn_download_now": "تحميل الآن",
        "btn_add_queue": "إضافة لقائمة الانتظار",
        "btn_start_queue": "بدء التحميلات",
        "btn_pause_queue": "إيقاف مؤقت للقائمة",
        "btn_clear_done": "مسح المكتمل",
        "label_download_mode": "نوع التحميل:",
        "mode_video": "🎬 فيديو + صوت",
        "mode_audio": "🎵 صوت فقط",
        "mode_subtitles": "💬 ترجمة فقط",
        "audio_only": "صوت فقط",
        "subtitles_only": "ترجمة فقط",
        "video_quality": "الجودة:",
        "video_codec": "الترميز:",
        "audio_format": "الصيغة:",
        "output_folder": "مجلد الحفظ",
        "downloads_header": "قائمة التحميلات",
        "queue_status_running": "▶ جاري التحميل التتابعي (عنصر تلو الآخر)",
        "queue_status_paused": "⏸ القائمة متوقفة مؤقتاً",
        "queue_summary": "{count} عنصر في القائمة · {active} قيد التحميل",
        "empty_downloads": "لا توجد تحميلات حالياً.\nألصق رابطاً أعلاه للإضافة إلى القائمة أو التحميل المباشر! 🚀",
        # Task Card States & Actions
        "state_idle": "خامل",
        "state_queued": "⏳ في الانتظار",
        "state_fetching": "🔍 جاري جلب المعلومات…",
        "state_downloading": "⬇ جاري التحميل",
        "state_playlist": "⬇ قائمة التشغيل {index}/{count}",
        "state_paused": "⏸ متوقف مؤقتاً",
        "state_converting": "⚙ جاري الدمج والمعالجة…",
        "state_completed": "✅ اكتمل التحميل",
        "state_cancelled": "🚫 ملغى",
        "state_error": "❌ خطأ",
        "btn_pause": "إيقاف مؤقت",
        "btn_resume": "استئناف",
        "btn_delete": "حذف",
        "btn_cancel": "إلغاء",
        "btn_open_folder": "فتح المجلد",
        # FFmpeg banner
        "ffmpeg_banner_title": "⚠️ لم يتم العثور على محرك FFmpeg",
        "ffmpeg_banner_desc": "بدون FFmpeg، سيتم تحميل صيغة مدمجة مسبقاً لتفادي فصل الصوت عن الفيديو.",
        "btn_install_ffmpeg_quick": "تثبيت FFmpeg",
        "ffmpeg_installed_success": "تم تثبيت FFmpeg بنجاح! سيتم دمج الصوت والفيديو تلقائياً في ملف واحد.",
        # History Page
        "history_title": "سجل التحميلات",
        "btn_clear_all": "🗑 مسح الكل",
        "search_history_placeholder": "بحث في السجل…",
        "empty_history": "لا توجد تحميلات سابقة.\nابدأ التحميل لإنشاء سجلك! 📼",
        # Settings Page
        "settings_title": "الإعدادات",
        "sec_general": "عام واللغة",
        "label_language": "لغة الواجهة",
        "label_theme": "المظهر",
        "sec_download": "خيارات التحميل",
        "label_output_dir": "مجلد الحفظ",
        "label_output_template": "قالب تسمية الملفات",
        "label_playlist_subdir": "مجلد فرعي لقوائم التشغيل",
        "label_restrict_filenames": "تقييد أسماء الملفات (ASCII)",
        "sec_format": "الصيغة والدمج",
        "label_default_mode": "نوع التحميل الافتراضي",
        "label_default_audio": "صوت فقط افتراضياً",
        "label_audio_format": "صيغة الصوت",
        "label_video_quality": "جودة الفيديو",
        "label_video_container": "حاوية الفيديو المدمج",
        "label_video_codec": "ترميز الفيديو (التوافق)",
        "sec_ffmpeg": "محرك دمج الوسائط (FFmpeg)",
        "ffmpeg_ready": "FFmpeg جاهز: سيتم دمج الصوت والفيديو معاً في ملف واحد عالي الجودة.",
        "ffmpeg_missing": "FFmpeg غير مثبت: قد يتعذر دمج الجودات العالية جداً بدون تحميله.",
        "btn_setup_ffmpeg": "⬇ تحميل وإعداد FFmpeg تلقائياً",
        "theme_dark": "داكن",
        "theme_light": "فاتح",
        "theme_system": "مظهر النظام",
        "sec_postproc": "المعالجة اللاحقة",
        "label_embed_metadata": "تضمين البيانات الوصفية",
        "label_embed_thumbnail": "تضمين الصورة المصغرة",
        "label_embed_subtitles": "تضمين ملفات الترجمة",
        "label_extract_chapters": "استخراج الفصول",
        "label_sponsorblock": "إزالة المقاطع الترويجية (SponsorBlock)",
        "label_sub_languages": "لغات الترجمة",
        "label_sub_source": "مصدر الترجمة",
        "sub_source_manual": "مرفوعة يدوياً",
        "sub_source_auto": "مُنشأة تلقائياً",
        "sub_source_both": "كلاهما",
        "sub_source_label": "المصدر:",
        "sec_network": "الشبكة والأداء",
        "label_proxy": "بروكسي HTTP",
        "label_rate_limit": "تحديد السرعة",
        "label_aria2c": "استخدام aria2c (تسريع التحميل)",
        "label_concurrent": "الأجزاء المتزامنة",
        "label_max_concurrent": "التحميلات المتزامنة",
        "label_cookies": "ملف الكوكيز (Netscape)",
        "sec_behaviour": "السلوك",
        "label_desktop_notifications": "إشعارات سطح المكتب",
        "label_clipboard_monitor": "مراقبة الحافظة للروابط",
        "label_api_server": "خادم ملحق المتصفح (Companion)",
        "clipboard_detected_title": "تم اكتشاف رابط",
        "clipboard_detected_msg": "تم اكتشاف رابط في الحافظة:\n{url}\n\nهل تريد إضافته لقائمة التحميل؟",
        "btn_add_to_queue": "إضافة للقائمة",
        "btn_ignore": "تجاهل",
        "sec_advanced": "متقدم",
        "label_log_file": "ملف السجلات التشخيصية",
        "btn_open_log": "فتح السجل",
        "btn_export_settings": "تصدير الإعدادات",
        "btn_import_settings": "استيراد الإعدادات",
        "settings_exported": "تم تصدير الإعدادات بنجاح.",
        "settings_imported": "تم استيراد الإعدادات بنجاح. يُنصح بإعادة التشغيل.",
        "settings_import_error": "فشل استيراد الإعدادات: {error}",
        "sec_updates": "تحديثات التطبيق والتحديث التلقائي",
        "label_auto_check": "فحص التحديثات تلقائياً عند بدء التشغيل",
        "btn_check_updates": "🔄 فحص تحديثات التطبيق",
        "btn_update_ytdlp": "⬆ تحديث yt-dlp",
        "sec_about": "حول البرنامج",
        "about_desc": "سيل ديسكتوب v1.5.3\nبرنامج حديث لتحميل الفيديو والصوت عبر مختلف المنصات مدعوم بـ yt-dlp.\nالميزات: قائمة تحميل تتابعية، دمج الصوت والفيديو، إضافة المتصفح للتحميل السريع، تحديثات تلقائية.",
        # Dialogs / Updates
        "update_available_title": "يتوفر تحديث جديد!",
        "update_available_msg": "الإصدار {version} متوفر الآن! (الإصدار الحالي: {current})",
        "update_notes_title": "الجديد في هذا التحديث (ملاحظات التغيير):",
        "btn_download_update": "تحميل وتثبيت التحديث",
        "btn_view_release": "عرض على GitHub",
        "btn_close": "إغلاق",
        "up_to_date": "أنت تستخدم أحدث إصدار من سيل ديسكتوب بالفعل ({version}).",
        "update_check_failed": "فشل فحص التحديثات. يرجى التحقق من اتصال الإنترنت.",
        "browse": "استعراض",
        "status_checking": "جارٍ الفحص…",
        "status_installing": "جارٍ التثبيت…",
        "status_downloading": "جارٍ التنزيل…",
        "status_ready": "جاهز!",
        "status_updating": "جارٍ التحديث…",
        # Entry context menu
        "ctx_cut": "قص",
        "ctx_copy": "نسخ",
        "ctx_paste": "لصق",
        "ctx_select_all": "تحديد الكل",
        # URL validation
        "invalid_url_title": "رابط غير صالح",
        "invalid_url_msg": "يرجى إدخال رابط صحيح يبدأ بـ http:// أو https://.",
        "unsupported_site_title": "موقع غير مدعوم",
        "unsupported_site_msg": "هذا الموقع غير مدعوم أو الرابط غير صالح. يرجى التحقق من الرابط والمحاولة مجدداً.",
        # Download page extras
        "btn_pick_format": "اختر الصيغة",
        "btn_select_items": "اختر العناصر",
        "format_picker_title": "اختيار الصيغة",
        "playlist_picker_title": "اختيار عناصر قائمة التشغيل",
        "btn_download_selected": "تحميل المحدد",
        "btn_move_up": "▲",
        "btn_move_down": "▼",
        "history_redownload": "↻ إعادة التحميل",
        "notify_completed_title": "اكتمل التحميل",
        "notify_completed_msg": "تم حفظ {title}.",
        "notify_subs_completed_title": "تم تحميل الترجمة",
        "notify_subs_completed_msg": "تم حفظ ملف الترجمة بنجاح لـ {title}.",
        "notify_error_title": "فشل التحميل",
        "notify_error_msg": "{title}: {error}",
        # Single instance
        "app_already_running_title": "سيل ديسكتوب",
        "app_already_running_msg": "هناك نافذة أخرى من سيل ديسكتوب قيد التشغيل بالفعل.",
    },
}


def t(key: str, **kwargs: object) -> str:
    """Translate a key into current language string, optionally formatting kwargs."""
    lang_dict = TRANSLATIONS.get(_current_lang, TRANSLATIONS["en"])
    text = lang_dict.get(key) or TRANSLATIONS["en"].get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text


def get_language() -> str:
    return _current_lang


def set_language(lang: str) -> None:
    global _current_lang
    if lang in TRANSLATIONS and lang != _current_lang:
        _current_lang = lang
        _notify_listeners()


def is_rtl() -> bool:
    return _current_lang == "ar"


def add_language_listener(listener: Callable[[], None]) -> None:
    if listener not in _listeners:
        _listeners.append(listener)


def remove_language_listener(listener: Callable[[], None]) -> None:
    if listener in _listeners:
        _listeners.remove(listener)


def _notify_listeners() -> None:
    for listener in list(_listeners):
        try:
            listener()
        except Exception:
            pass
