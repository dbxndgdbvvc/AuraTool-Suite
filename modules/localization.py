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

    TRANSLATIONS = {
        "en": {
            "title": "AuraTool-Suite — Advanced Ecosystem Maintenance Framework",
            "ai_tab": "Aura-AI Diagnostic",
            "vendor_tab": "Vendor Operations",
            "repair_tab": "Ultimate Repair",
            "chat_tab": "Live Chat Rooms",
            "stream_tab": "Media Stream Network",
            "store_tab": "E-Commerce Store",
            "settings_tab": "Settings & Language",
            "run_ai": "Run AI Command",
            "flash": "Flash Firmware Image",
            "checkout": "Complete Checkout",
        },
        "ar": {
            "title": "AuraTool-Suite — منصة صيانة وإدارة الأجهزة الذكية 2030",
            "ai_tab": "المساعد الذكي Aura-AI",
            "vendor_tab": "عمليات الشركات",
            "repair_tab": "الإصلاح الشامل",
            "chat_tab": "غرف الدردشة المباشرة",
            "stream_tab": "شبكة بث الوسائط",
            "store_tab": "متجر قطع الغيار والتراخيص",
            "settings_tab": "الإعدادات واللغة",
            "run_ai": "تشغيل الأمر الذكي",
            "flash": "بدء تفليش النظام",
            "checkout": "إتمام الشراء",
        },
        "es": {
            "title": "AuraTool-Suite — Marco Avanzado de Mantenimiento",
            "ai_tab": "Diagnóstico Aura-AI",
            "vendor_tab": "Operaciones de Fabricante",
            "repair_tab": "Reparación Definitiva",
            "chat_tab": "Salas de Chat",
            "stream_tab": "Red de Transmisión",
            "store_tab": "Tienda Electrónica",
            "settings_tab": "Configuración e Idioma",
            "run_ai": "Ejecutar Comando AI",
            "flash": "Iniciar Flasheo",
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
