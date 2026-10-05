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
        "app_footer": "v1.1.0 · Powered by yt-dlp",
        # Download Page Header & Inputs
        "page_download_title": "Download",
        "url_placeholder": "Paste a YouTube, SoundCloud, or any supported URL…",
        "btn_download_now": "Download Now",
        "btn_add_queue": "Add to Queue",
        "btn_start_queue": "Start Downloads",
        "btn_pause_queue": "Pause Queue",
        "btn_clear_done": "Clear done",
        "audio_only": "Audio only",
        "video_quality": "Quality:",
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
        "sec_download": "Download Options",
        "label_output_dir": "Output folder",
        "label_output_template": "Output template",
        "label_playlist_subdir": "Playlist subdirectory",
        "label_restrict_filenames": "Restrict filenames (ASCII)",
        "sec_format": "Format & Merging",
        "label_default_audio": "Audio only by default",
        "label_audio_format": "Audio format",
        "label_video_quality": "Video quality",
        "label_video_container": "Merged video format",
        "sec_ffmpeg": "FFmpeg Engine (Audio/Video Merger)",
        "ffmpeg_ready": "FFmpeg is ready: audio and video will be merged into a single file.",
        "ffmpeg_missing": "FFmpeg is missing: videos may be restricted or lack high-res merging.",
        "btn_setup_ffmpeg": "⬇ Download & Setup FFmpeg",
        "sec_postproc": "Post-processing",
        "label_embed_metadata": "Embed metadata",
        "label_embed_thumbnail": "Embed thumbnail",
        "label_embed_subtitles": "Embed subtitles",
        "label_sub_languages": "Subtitle languages",
        "sec_network": "Network & Performance",
        "label_proxy": "HTTP proxy",
        "label_rate_limit": "Rate limit",
        "label_aria2c": "Use aria2c (faster)",
        "label_concurrent": "Concurrent fragments",
        "label_cookies": "Cookies file (Netscape)",
        "sec_updates": "App Updates & Auto-Updater",
        "label_auto_check": "Check for updates automatically on startup",
        "btn_check_updates": "🔄 Check for App Updates",
        "btn_update_ytdlp": "⬆ Update yt-dlp",
        "sec_about": "About",
        "about_desc": "Seal Desktop v1.1.0\nA modern cross-platform video & audio downloader powered by yt-dlp.\nFeatures: sequential queue, audio-video merger, multi-download handling, auto-updater.",
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
    },
    "ar": {
        # App & Nav
        "app_title": "سيل ديسكتوب",
        "app_subtitle": "ديسكتوب",
        "nav_download": "التحميل",
        "nav_history": "السجل",
        "nav_settings": "الإعدادات",
        "app_footer": "الإصدار 1.1.0 · مدعوم بواسطة yt-dlp",
        # Download Page Header & Inputs
        "page_download_title": "التحميل",
        "url_placeholder": "ألصق رابط يوتيوب أو ساوند كلاود أو أي رابط مدعوم…",
        "btn_download_now": "تحميل الآن",
        "btn_add_queue": "إضافة لقائمة الانتظار",
        "btn_start_queue": "بدء التحميلات",
        "btn_pause_queue": "إيقاف مؤقت للقائمة",
        "btn_clear_done": "مسح المكتمل",
        "audio_only": "صوت فقط",
        "video_quality": "الجودة:",
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
        "sec_download": "خيارات التحميل",
        "label_output_dir": "مجلد الحفظ",
        "label_output_template": "قالب تسمية الملفات",
        "label_playlist_subdir": "مجلد فرعي لقوائم التشغيل",
        "label_restrict_filenames": "تقييد أسماء الملفات (ASCII)",
        "sec_format": "الصيغة والدمج",
        "label_default_audio": "صوت فقط افتراضياً",
        "label_audio_format": "صيغة الصوت",
        "label_video_quality": "جودة الفيديو",
        "label_video_container": "حاوية الفيديو المدمج",
        "sec_ffmpeg": "محرك دمج الوسائط (FFmpeg)",
        "ffmpeg_ready": "FFmpeg جاهز: سيتم دمج الصوت والفيديو معاً في ملف واحد عالي الجودة.",
        "ffmpeg_missing": "FFmpeg غير مثبت: قد يتعذر دمج الجودات العالية جداً بدون تحميله.",
        "btn_setup_ffmpeg": "⬇ تحميل وإعداد FFmpeg تلقائياً",
        "sec_postproc": "المعالجة اللاحقة",
        "label_embed_metadata": "تضمين البيانات الوصفية",
        "label_embed_thumbnail": "تضمين الصورة المصغرة",
        "label_embed_subtitles": "تضمين ملفات الترجمة",
        "label_sub_languages": "لغات الترجمة",
        "sec_network": "الشبكة والأداء",
        "label_proxy": "بروكسي HTTP",
        "label_rate_limit": "تحديد السرعة",
        "label_aria2c": "استخدام aria2c (تسريع التحميل)",
        "label_concurrent": "الأجزاء المتزامنة",
        "label_cookies": "ملف الكوكيز (Netscape)",
        "sec_updates": "تحديثات التطبيق والتحديث التلقائي",
        "label_auto_check": "فحص التحديثات تلقائياً عند بدء التشغيل",
        "btn_check_updates": "🔄 فحص تحديثات التطبيق",
        "btn_update_ytdlp": "⬆ تحديث yt-dlp",
        "sec_about": "حول البرنامج",
        "about_desc": "سيل ديسكتوب v1.1.0\nبرنامج حديث لتحميل الفيديو والصوت عبر مختلف المنصات مدعوم بـ yt-dlp.\nالميزات: قائمة تحميل تتابعية، دمج الصوت والفيديو، تحكم كامل بالإيقاف والاستئناف، تحديثات تلقائية.",
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
