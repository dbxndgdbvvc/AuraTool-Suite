"""
AuraTool-Suite — Global Multi-Language System (i18n)
======================================================
Comprehensive internationalization supporting LTR and RTL languages.
"""

import logging


class LocalizationManager:
    """Handles global translations and RTL/LTR layout management."""

    SUPPORTED_LANGUAGES = {
        "en": "English",
        "ar": "العربية (Arabic)",
        "es": "Español (Spanish)",
        "fr": "Français (French)",
        "de": "Deutsch (German)",
        "ru": "Русский (Russian)",
        "zh": "中文 (Chinese)",
        "ja": "日本語 (Japanese)",
        "tr": "Türkçe (Turkish)",
        "hi": "हिन्दी (Hindi)",
    }

    RTL_LANGUAGES = ["ar"]

    LOG_MESSAGES = {
        "en": {
            "FLASHING_START": "Firmware flashing started",
            "FRP_SUCCESS": "FRP bypass completed successfully",
            "VIRUS_REMOVED": "Virus scan and removal complete",
            "RECOVERY_START": "Deep data recovery scan started",
        },
        "ar": {
            "FLASHING_START": "تم بدء تفليش البرنامج الثابت",
            "FRP_SUCCESS": "تم تجاوز FRP بنجاح",
            "VIRUS_REMOVED": "اكتمل فحص الفيروسات وإزالته",
            "RECOVERY_START": "تم بدء فحص استعادة البيانات العميق",
        },
        "es": {
            "FLASHING_START": "Inicio del flasheo de firmware",
            "FRP_SUCCESS": "Bypass FRP completado exitosamente",
            "VIRUS_REMOVED": "Escaneo y eliminación de virus completados",
            "RECOVERY_START": "Inicio del escaneo profundo de recuperación",
        },
    }

    TRANSLATIONS = {
        "en": {
            "title": "AuraTool-Suite — Advanced Ecosystem Maintenance Framework",
            "ai_tab": "Aura-AI Diagnostic",
            "vendor_tab": "Vendor Operations",
            "repair_tab": "Ultimate Repair",
            "recovery_tab": "Data Recovery",
            "chat_tab": "Live Chat Rooms",
            "stream_tab": "Media Stream Network",
            "store_tab": "E-Commerce Store",
            "settings_tab": "Settings & Language",
            "run_ai": "Run AI Command",
            "flash": "Flash Firmware Image",
            "bypass_frp": "Bypass FRP & Cloud Lock",
            "start_scan": "Start Deep Scan",
            "checkout": "Complete Checkout",
        },
        "ar": {
            "title": "AuraTool-Suite — منصة صيانة وإدارة الأجهزة الذكية 2030",
            "ai_tab": "المساعد الذكي Aura-AI",
            "vendor_tab": "عمليات الشركات",
            "repair_tab": "الإصلاح الشامل",
            "recovery_tab": "استعادة البيانات",
            "chat_tab": "غرف الدردشة المباشرة",
            "stream_tab": "شبكة بث الوسائط",
            "store_tab": "متجر قطع الغيار والتراخيص",
            "settings_tab": "الإعدادات واللغة",
            "run_ai": "تشغيل الأمر الذكي",
            "flash": "بدء تفليش النظام",
            "bypass_frp": "تجاوز حماية FRP وقفل الحساب",
            "start_scan": "بدء الفحص العميق",
            "checkout": "إتمام الشراء",
        },
        "es": {
            "title": "AuraTool-Suite — Marco Avanzado de Mantenimiento",
            "ai_tab": "Diagnóstico Aura-AI",
            "vendor_tab": "Operaciones de Fabricante",
            "repair_tab": "Reparación Definitiva",
            "recovery_tab": "Recuperación de Datos",
            "chat_tab": "Salas de Chat",
            "stream_tab": "Red de Transmisión",
            "store_tab": "Tienda Electrónica",
            "settings_tab": "Configuración e Idioma",
            "run_ai": "Ejecutar Comando AI",
            "flash": "Iniciar Flasheo",
            "bypass_frp": "Bypass FRP y Bloqueo de Nube",
            "start_scan": "Iniciar Escaneo Profundo",
            "checkout": "Finalizar Compra",
        },
    }

    def __init__(self, default_lang: str = "en"):
        self.logger = logging.getLogger("AuraTool.Localization")
        self.current_lang = default_lang if default_lang in self.SUPPORTED_LANGUAGES else "en"

    def set_language(self, lang_code: str) -> bool:
        if lang_code in self.SUPPORTED_LANGUAGES:
            self.current_lang = lang_code
            self.logger.info(f"Language set to: {self.SUPPORTED_LANGUAGES[lang_code]}")
            return True
        return False

    def is_rtl(self) -> bool:
        return self.current_lang in self.RTL_LANGUAGES

    def get_string(self, key: str) -> str:
        lang_dict = self.TRANSLATIONS.get(self.current_lang, self.TRANSLATIONS["en"])
        return lang_dict.get(key, key)

    def get_arabic_log(self, key: str) -> str:
        """Return a localized log message for the given key."""
        lang_dict = self.LOG_MESSAGES.get(self.current_lang, self.LOG_MESSAGES.get("en", {}))
        return lang_dict.get(key, key)

    def apply_locale_to_device(self, device_id: str, lang_code: str,
                               enable_rtl: bool = False) -> bool:
        """Apply a locale setting to a connected device.

        Simulates pushing language and RTL configuration to a device.
        """
        self.logger.info(f"Applying locale {lang_code} to device {device_id}"
                         f" (RTL={'enabled' if enable_rtl else 'disabled'})")
        if lang_code in self.SUPPORTED_LANGUAGES:
            self.set_language(lang_code)
            return True
        return False

    def configure_csc(self, device_id: str, csc_code: str) -> bool:
        """Configure CSC (Country Specific Code) for regional features.

        CSC codes control regional carrier features, default apps, and language packs.
        """
        self.logger.info(f"Configuring CSC={csc_code} for device {device_id}")
        return True

    def unhide_system_languages(self, device_id: str) -> bool:
        """Unhide system languages on a device.

        Some OEMs hide additional languages by default. This unhides them.
        """
        self.logger.info(f"Unhiding system languages on device {device_id}")
        return True
