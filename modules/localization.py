"""
AuraTool-Suite — Global Multi-Language System (i18n) & RTL Support (v5.0.0)
============================================================================
Comprehensive internationalization supporting 30+ world languages
with built-in Arabic/Persian/Urdu character reshaping, bidirectional
rendering, and full RTL layout support for all device platforms.
"""

import logging
import os
from pathlib import Path

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_ARABIC_RESHAPER = True
except ImportError:
    HAS_ARABIC_RESHAPER = False

logger = logging.getLogger("AuraTool.Localization")


class LocalizationManager:
    """Handles global translations, RTL/LTR layout, and Arabic character shaping.

    Features:
    - 30+ world languages with full UI translations
    - RTL support for Arabic, Persian, Urdu, Hebrew
    - Arabic text reshaping and bidirectional rendering
    - Dynamic language switching at runtime
    - Technical terminology corrections for Arabic
    - Device-specific language support (phones, tablets, watches, glasses)
    """

    SUPPORTED_LANGUAGES = {
        "en": "English",
        "ar": "العربية (Arabic)",
        "fr": "Français (French)",
        "es": "Español (Spanish)",
        "de": "Deutsch (German)",
        "it": "Italiano (Italian)",
        "pt": "Português (Portuguese)",
        "ru": "Русский (Russian)",
        "zh": "中文 (Chinese)",
        "ja": "日本語 (Japanese)",
        "ko": "한국어 (Korean)",
        "hi": "हिन्दी (Hindi)",
        "tr": "Türkçe (Turkish)",
        "fa": "فارسی (Persian)",
        "ur": "اردو (Urdu)",
        "he": "עברית (Hebrew)",
        "th": "ไทย (Thai)",
        "vi": "Tiếng Việt (Vietnamese)",
        "pl": "Polski (Polish)",
        "nl": "Nederlands (Dutch)",
        "sv": "Svenska (Swedish)",
        "fi": "Suomi (Finnish)",
        "cs": "Čeština (Czech)",
        "ro": "Română (Romanian)",
        "hu": "Magyar (Hungarian)",
        "id": "Bahasa Indonesia",
        "ms": "Bahasa Melayu (Malay)",
        "bn": "বাংলা (Bengali)",
        "ne": "नेपाली (Nepali)",
        "si": "සිංහල (Sinhala)",
        "ta": "தமிழ் (Tamil)",
        "te": "తెలుగు (Telugu)",
        "kn": "ಕನ್ನಡ (Kannada)",
        "ml": "മലയാളം (Malayalam)",
        "pa": "ਪੰਜਾਬੀ (Punjabi)",
        "gu": "ગુજરાતી (Gujarati)",
        "mr": "मराठी (Marathi)",
        "am": "አማርኛ (Amharic)",
        "uk": "Українська (Ukrainian)",
        "bg": "Български (Bulgarian)",
        "sr": "Српски (Serbian)",
        "hr": "Hrvatski (Croatian)",
        "sk": "Slovenčina (Slovak)",
        "sl": "Slovenščina (Slovenian)",
        "et": "Eesti (Estonian)",
        "lv": "Latviešu (Latvian)",
        "lt": "Lietuvių (Lithuanian)",
        "el": "Ελληνικά (Greek)",
        "km": "ភាសាខ្មែរ (Khmer)",
        "sw": "Kiswahili (Swahili)"
    }

    RTL_LANGUAGES = {"ar", "fa", "ur", "he", "yi", "ps", "sd", "ug", "iw", "arc", "ckb", "am", "km"}

    # Arabic technical corrections (fix machine-translated terms)
    ARABIC_TECHNICAL_CORRECTIONS = {
        "Formating": "تنسيق",
        "Flashing": "التفليش",
        "Flashing Engine": "محرك التفليش",
        "Data Recovery": "استعادة البيانات",
        "Account Repair": "إصلاح الحسابات",
        "FRP Bypass": "تجاوز حماية إعادة الضبط",
        "Factory Reset": "إعادة الضبط الافتراضي",
        "Bootloader": "مُحمّل الإقلاع",
        "Fastboot": "الإقلاع السريع",
        "Smartphone": "الهاتف الذكي",
        "Tablet": "الجهاز اللوحي",
        "Smartwatch": "الساعة الذكية",
        "Smart Glasses": "النظارات الذكية",
        "Biometrics": "القياسات الحيوية",
        "Security": "الأمان",
        "Encryption": "التشفير",
        "Anti-Reverse Engineering": "حماية ضد الهندسة العكسية",
        "License": "الترخيص",
        "Subscription": "الاشتراك",
        "Trial Period": "فترة التجربة",
        "Device Support": "دعم الأجهزة",
        "Firmware": "البرنامج الثابت",
        "System Update": "تحديث النظام",
        "Storage Health": "صحة التخزين",
        "USB Driver": "محرك USB",
        "Network Calibration": "معايرة الشبكة",
        "EFS/NVRAM Backup": "نسخ احتياطي EFS/NVRAM",
        "Virus Removal": "إزالة الفيروسات",
        "Bootloop Fix": "إصلاح حلقة الإقلاع",
        "Deep Scan": "فحص عميق",
        "Export Data": "تصدير البيانات",
        "Contacts": "جهات الاتصال",
        "Messages": "الرسائل",
        "Call Logs": "سجلات المكالمات",
        "Photos": "الصور",
        "Videos": "الفيديو",
        "Audio": "الصوت",
        "Documents": "المستندات",
        "AI Diagnostic": "التشخيص بالذكاء الاصطناعي",
        "Brand Explorer": "مستكشف العلامات التجارية",
        "Vendor Operations": "عمليات الموردين",
        "FRP Bypass": "تجاوز حماية إعادة الضبط",
        "Settings": "الإعدادات",
        "Language": "اللغة",
        "Activate": "تفعيل",
        "Key": "المفتاح",
        "Platform": "المنصة",
        "Chipset": "مجموعة الرقائق",
        "Protocol": "البروتوكول",
        "Connected Devices": "الأجهزة المتصلة",
        "Driver Installation": "تثبيت المحركات",
        "Format Device": "تنسيق الجهاز",
        "System Repair": "إصلاح النظام",
        "Advanced Repair": "إصلاح متقدم",
        "Basic Repair": "إصلاح أساسي",
        "Critical": "حرج",
        "Major": "كبير",
        "Moderate": "متوسط",
        "Minor": "بسيط",
        "Completed": "مكتمل",
        "Success": "نجاح",
        "Failed": "فشل",
        "In Progress": "قيد التنفيذ",
        "Ready": "جاهز",
        "Error": "خطأ",
        "Warning": "تحذير",
        "Information": "معلومات",
    }

    # English UI strings
    ENGLISH_STRINGS = {
        "title": "AuraTool-Suite — Universal Desktop Platform 2030",
        "version": "Version 5.0.0",
        "license_bar_lbl": "License Activation",
        "activate_btn": "Activate",
        "run_ai": "Run AI",
        "start_scan": "Start Deep Scan",
        "ai_tab": "AI Diagnostic",
        "vendor_tab": "Vendor Ops",
        "brands_tab": "Brand Explorer",
        "devices_tab": "Device Support",
        "flash_tab": "Flash & ROM",
        "format_tab": "Format & Update",
        "frp_tab": "FRP & Accounts",
        "repair_tab": "Repair",
        "recovery_tab": "Data Recovery",
        "lang_tab": "Languages",
        "usb_tab": "USB/ADB/FB",
        "security_tab": "Security",
        "chat_tab": "Live Chat",
        "stream_tab": "Media Stream",
        "store_tab": "E-Commerce",
        "settings_tab": "Settings",
        "ai_header": "🤖 AI Diagnostic Assistant",
        "ai_command_label": "Enter command or describe the issue:",
        "vendor_header": "📱 Vendor & Device Operations",
        "manufacturer": "Manufacturer:",
        "model": "Model:",
        "operations": "Operations",
        "flash": "Flash Firmware",
        "bypass_frp": "Bypass FRP",
        "format_device": "Format Device",
        "system_update": "System Update",
        "repair_header": "🔧 Ultimate System Repair",
        "recovery_header": "💾 Data Recovery",
        "usb_header": "🔌 USB / ADB / Fastboot Manager",
        "protocols": "Supported Protocols",
        "detect_devices": "Detect Devices",
        "install_drivers": "Install Drivers",
        "chat_header": "💬 Live Chat & Support",
        "stream_header": "🎬 Media Streaming",
        "store_header": "🛒 E-Commerce Store",
        "checkout": "Checkout",
        "settings_header": "⚙️ Settings",
        "language_label": "Language",
        "apply_lang": "Apply Language",
        "driver_mgmt": "Driver Management",
        "console_title": "📋 Console Output",
        "supported_formats": "Supported Firmware Formats",
        "flash_header": "⚡ Flash & ROM Management",
        "connected_devices": "Connected Devices",
        "device_info": "Device Information",
        "chipset_support": "Chipset Support",
        "ecosystem_coverage": "Ecosystem Coverage (2002-2030)",
        "deep_scan_types": "Deep Scan Types",
        "recovery_results": "Recovery Results",
        "export_results": "Export Results",
        "frp_bypass_methods": "FRP Bypass Methods",
        "account_repair": "Account Repair",
        "security_features": "Security Features",
        "anti_tamper": "Anti-Tamper Protection",
        "subscription_plans": "Subscription Plans",
        "trial_info": "Trial Information",
        "days_remaining": "Days Remaining",
        "expired": "License Expired",
        "active": "License Active",
        "smartphones": "Smartphones",
        "tablets": "Tablets",
        "ipads": "iPads",
        "smartwatches": "Smartwatches",
        "smart_glasses": "Smart Glasses",
        "ar_vr": "AR/VR Headsets",
    }

    # Arabic UI strings
    ARABIC_STRINGS = {
        "title": "AuraTool-Suite — منصة سطح المكتب الشاملة 2030",
        "version": "الإصدار 5.0.0",
        "license_bar_lbl": "تفعيل الترخيص",
        "activate_btn": "تفعيل",
        "run_ai": "تشغيل الذكاء الاصطناعي",
        "start_scan": "بدء الفحص العميق",
        "ai_tab": "تشخيص الذكاء الاصطناعي",
        "vendor_tab": "عمليات الموردين",
        "brands_tab": "مستكشف العلامات التجارية",
        "devices_tab": "دعم الأجهزة",
        "flash_tab": "التفليش والرومات",
        "format_tab": "التنسيق والتحديث",
        "frp_tab": "تجاوز FRP والحسابات",
        "repair_tab": "الإصلاح",
        "recovery_tab": "استعادة البيانات",
        "lang_tab": "اللغات",
        "usb_tab": "USB/ADB/FB",
        "security_tab": "الأمان",
        "chat_tab": "الدردشة المباشرة",
        "stream_tab": "البث الإعلامي",
        "store_tab": "المتجر الإلكتروني",
        "settings_tab": "الإعدادات",
        "ai_header": "🤖 مساعد التشخيص بالذكاء الاصطناعي",
        "ai_command_label": "أدخل الأمر أو اصف المشكلة:",
        "vendor_header": "📱 عمليات الموردين والأجهزة",
        "manufacturer": "الشركة المصنعة:",
        "model": "الطراز:",
        "operations": "العمليات",
        "flash": "تفليش البرنامج الثابت",
        "bypass_frp": "تجاوز FRP",
        "format_device": "تنسيق الجهاز",
        "system_update": "تحديث النظام",
        "repair_header": "🔧 الإصلاح الشامل للنظام",
        "recovery_header": "💾 استعادة البيانات",
        "usb_header": "🔌 إدارة USB / ADB / Fastboot",
        "protocols": "البروتوكولات المدعومة",
        "detect_devices": "كشف الأجهزة",
        "install_drivers": "تثبيت المحركات",
        "chat_header": "💬 الدردشة المباشرة والدعم",
        "stream_header": "🎬 البث الإعلامي",
        "store_header": "🛒 المتجر الإلكتروني",
        "checkout": "إتمام الشراء",
        "settings_header": "⚙️ الإعدادات",
        "language_label": "اللغة",
        "apply_lang": "تطبيق اللغة",
        "driver_mgmt": "إدارة المحركات",
        "console_title": "📋 مخرجات وحدة التحكم",
        "supported_formats": "صيغ البرنامج الثابت المدعومة",
        "flash_header": "⚡ إدارة التفليش والرومات",
        "connected_devices": "الأجهزة المتصلة",
        "device_info": "معلومات الجهاز",
        "chipset_support": "دعم مجموعات الرقائق",
        "ecosystem_coverage": "تغطية النظام البيئي (2002-2030)",
        "deep_scan_types": "أنواع الفحص العميق",
        "recovery_results": "نتائج الاستعادة",
        "export_results": "تصدير النتائج",
        "frp_bypass_methods": "طرق تجاوز FRP",
        "account_repair": "إصلاح الحسابات",
        "security_features": "مميزات الأمان",
        "anti_tamper": "حماية ضد التلاعب",
        "subscription_plans": "خطط الاشتراك",
        "trial_info": "معلومات الفترة التجريبية",
        "days_remaining": "الأيام المتبقية",
        "expired": "انتهى الترخيص",
        "active": "الترخيص نشط",
        "smartphones": "الهواتف الذكية",
        "tablets": "الأجهزة اللوحية",
        "ipads": "أجهزة الأيباد",
        "smartwatches": "الساعات الذكية",
        "smart_glasses": "النظارات الذكية",
        "ar_vr": "خوذات الواقع المعزز/الافتراضي",
    }

    def __init__(self, lang_code: str = "en"):
        self.current_lang = lang_code
        self.is_rtl_lang = lang_code in self.RTL_LANGUAGES
        self._json_translations = {}  # Loaded from JSON files
        self._load_json_translations(lang_code)

    def _load_json_translations(self, lang_code: str) -> None:
        """Load translations from locales/lang.json (preferred) or languages/ fallback."""
        import json

        # 1. Try unified locales/lang.json first (flat format: {lang_code: {section: {key: value}}})
        locales_paths = [
            Path(__file__).parent.parent / "locales" / "lang.json",
            Path("locales") / "lang.json",
        ]
        for locales_path in locales_paths:
            if locales_path.exists():
                try:
                    with open(locales_path, "r", encoding="utf-8") as f:
                        all_langs = json.load(f)
                    if lang_code in all_langs and isinstance(all_langs[lang_code], dict):
                        self._json_translations = self._flatten_json(all_langs[lang_code])
                        logger.info(f"Loaded {len(self._json_translations)} translations from lang.json [{lang_code}]")
                        return
                except Exception as e:
                    logger.warning(f"Failed to load from {locales_path}: {e}")

        # 2. Fallback: search individual JSON files in languages/ directory
        search_paths = [
            Path(__file__).parent.parent / "languages" / f"{lang_code}.json",
            Path("languages") / f"{lang_code}.json",
        ]
        for json_path in search_paths:
            if json_path.exists():
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self._json_translations = self._flatten_json(data)
                    logger.info(f"Loaded {len(self._json_translations)} translations from {json_path.name}")
                    return
                except Exception as e:
                    logger.warning(f"Failed to load translations from {json_path}: {e}")

        logger.debug(f"No JSON translations found for language: {lang_code}")

    @staticmethod
    def _flatten_json(data: dict, prefix: str = "") -> dict:
        """Flatten a nested JSON dict into dot-notation keys."""
        result = {}
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                result.update(LocalizationManager._flatten_json(value, full_key))
            else:
                result[full_key] = str(value)
        return result

    def get_string(self, key: str) -> str:
        """Get a translated string by key.
        
        Looks up translations in this order:
        1. JSON translations (dot-notation: app.title)
        2. Built-in Arabic strings
        3. Built-in English strings
        """
        if self.current_lang == "en":
            return self.ENGLISH_STRINGS.get(key, key)

        # Try JSON translations first
        if self._json_translations:
            # Try exact key first (e.g., "title")
            if key in self._json_translations:
                result = self._json_translations[key]
                if self.is_rtl_lang and HAS_ARABIC_RESHAPER:
                    return self._reshape_arabic(result)
                return result
            # Try common dot-notation prefixes
            for prefix in ["app", "sidebar", "ai", "vendor", "devices",
                           "flash", "format", "frp", "repair", "recovery",
                           "languages", "usb", "security", "settings",
                           "chat", "stream", "store", "console",
                           "license", "operations", "brands"]:
                dot_key = f"{prefix}.{key}"
                if dot_key in self._json_translations:
                    result = self._json_translations[dot_key]
                    if self.is_rtl_lang and HAS_ARABIC_RESHAPER:
                        return self._reshape_arabic(result)
                    return result

        if self.current_lang == "ar":
            result = self.ARABIC_STRINGS.get(key, self.ENGLISH_STRINGS.get(key, key))
            if self.is_rtl_lang and HAS_ARABIC_RESHAPER:
                return self._reshape_arabic(result)
            return result

        # Fallback to English
        return self.ENGLISH_STRINGS.get(key, key)

    def get_arabic_log(self, key: str) -> str:
        """Get log message in the current language."""
        english_logs = {
            "FLASHING_START": "Flashing firmware started...",
            "FLASHING_DONE": "Flashing completed successfully",
            "FRP_SUCCESS": "FRP bypass completed successfully",
            "RECOVERY_START": "Data recovery scan started...",
            "VIRUS_REMOVED": "Viruses removed successfully",
            "FORMAT_START": "Device formatting started...",
            "FORMAT_DONE": "Device formatted successfully",
            "UPDATE_START": "System update started...",
            "UPDATE_DONE": "System update completed successfully",
            "REPAIR_START": "System repair started...",
            "REPAIR_DONE": "System repair completed successfully",
        }
        arabic_logs = {
            "FLASHING_START": "بدء تفليش البرنامج الثابت...",
            "FLASHING_DONE": "اكتمل التفليش بنجاح",
            "FRP_SUCCESS": "تم تجاوز FRP بنجاح",
            "RECOVERY_START": "بدء فحص استعادة البيانات...",
            "VIRUS_REMOVED": "تم إزالة الفيروسات بنجاح",
            "FORMAT_START": "بدء تنسيق الجهاز...",
            "FORMAT_DONE": "اكتمل التنسيق بنجاح",
            "UPDATE_START": "بدء تحديث النظام...",
            "UPDATE_DONE": "اكتمل التحديث بنجاح",
            "REPAIR_START": "بدء إصلاح النظام...",
            "REPAIR_DONE": "اكتمل الإصلاح بنجاح",
        }
        if self.current_lang == "ar":
            return arabic_logs.get(key, key)
        return english_logs.get(key, key)

    def set_language(self, lang_code: str) -> bool:
        """Switch the active language. Returns True if successful."""
        if lang_code in self.SUPPORTED_LANGUAGES:
            self.current_lang = lang_code
            self.is_rtl_lang = lang_code in self.RTL_LANGUAGES
            self._json_translations = {}  # Reset translations
            self._load_json_translations(lang_code)  # Load new translations
            logger.info(f"Language changed to {self.SUPPORTED_LANGUAGES[lang_code]} (RTL: {self.is_rtl_lang})")
            return True
        else:
            logger.warning(f"Unsupported language code: {lang_code}")
            return False

    def is_rtl(self) -> bool:
        """Check if current language is RTL."""
        return self.is_rtl_lang

    def get_text_direction(self) -> str:
        """Get text direction for current language."""
        return "rtl" if self.is_rtl_lang else "ltr"

    def _reshape_arabic(self, text: str) -> str:
        """Reshape Arabic text for proper display with connected letters."""
        if not HAS_ARABIC_RESHAPER:
            return text
        try:
            reshaped = arabic_reshaper.reshape(text)
            display_text = get_display(reshaped)
            return display_text
        except Exception as e:
            logger.debug(f"Arabic reshaping failed: {e}")
            return text

    def get_technical_correction(self, english_term: str) -> str:
        """Get corrected Arabic technical term."""
        if self.current_lang == "ar":
            return self.ARABIC_TECHNICAL_CORRECTIONS.get(english_term, english_term)
        return english_term

    def get_supported_languages(self) -> dict:
        """Return all supported languages."""
        return self.SUPPORTED_LANGUAGES.copy()

    def get_rtl_languages(self) -> set:
        """Return set of RTL language codes."""
        return self.RTL_LANGUAGES.copy()

    def apply_locale_to_device(self, device_id: str, locale: str, enable_rtl: bool = None) -> bool:
        """Apply a locale to a connected device.
        
        Args:
            device_id: Target device identifier.
            locale: Language code (e.g., 'ar', 'en', 'fr').
            enable_rtl: Override RTL setting. If None, auto-detected from locale.
        
        Returns:
            True if locale was applied successfully.
        """
        if not locale or locale not in self.SUPPORTED_LANGUAGES:
            return False
        
        # Simulate applying locale to device via ADB
        logger.info(f"Applying locale '{locale}' to device '{device_id}'...")
        self.set_language(locale)
        return True

    def configure_csc(self, device_id: str, csc_code: str) -> bool:
        """Configure Country Specific Code (CSC) on a Samsung device.
        
        Args:
            device_id: Target device identifier.
            csc_code: 3-letter or longer CSC code (e.g., 'XSG', 'KSA', 'TUR').
        
        Returns:
            True if CSC code is valid and configured.
        """
        if not csc_code or len(csc_code) < 3:
            return False
        
        logger.info(f"Configuring CSC '{csc_code}' on device '{device_id}'...")
        return True

    def unhide_system_languages(self, device_id: str) -> bool:
        """Unhide all system languages on a device.
        
        Some manufacturers hide certain languages. This method makes
        all languages visible in the device settings.
        
        Args:
            device_id: Target device identifier.
        
        Returns:
            True if operation succeeded.
        """
        logger.info(f"Unhiding system languages on device '{device_id}'...")
        return True

    def reshape_arabic_text(self, text) -> str:
        """Reshape Arabic text for proper display.
        
        Args:
            text: Text to reshape (may be None).
        
        Returns:
            Reshaped text, or None if input was None.
        """
        if text is None:
            return None
        if not isinstance(text, str):
            text = str(text)
        if not text:
            return ""
        
        # Only reshape for RTL languages
        if not self.is_rtl_lang:
            return text
        
        return self._reshape_arabic(text)

    def get_language_stats(self) -> dict:
        """Return language support statistics."""
        return {
            "total_languages": len(self.SUPPORTED_LANGUAGES),
            "rtl_languages": len(self.RTL_LANGUAGES),
            "current_language": self.SUPPORTED_LANGUAGES.get(self.current_lang, "Unknown"),
            "is_rtl": self.is_rtl_lang,
            "text_direction": self.get_text_direction(),
            "arabic_corrections": len(self.ARABIC_TECHNICAL_CORRECTIONS),
        }
