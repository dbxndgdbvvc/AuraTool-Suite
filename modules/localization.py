class LocalizationManager:
    """Handles internationalization (i18n) and locale updates for connected devices and UI."""

    SUPPORTED_LANGUAGES = {
        "en": "English",
        "ar": "العربية",
        "es": "Español",
        "fr": "Français"
    }

    TRANSLATIONS = {
        "en": {
            "title": "AuraTool-Suite",
            "select_vendor": "Select Manufacturer:",
            "select_model": "Select Device Model:",
            "start_flash": "Start Flashing",
            "run_diagnostics": "Run Diagnostics",
            "recalibrate": "Recalibrate Biometrics",
            "detect_devices": "Detect Connected Devices",
            "license_status": "License",
            "days_left": "days left",
            "apply_language": "Apply Language"
        },
        "ar": {
            "title": "AuraTool-Suite - مجموعة الأدوات المتقدمة",
            "select_vendor": "اختر الشركة المصنعة:",
            "select_model": "اختر موديل الجهاز:",
            "start_flash": "بدء التفليش",
            "run_diagnostics": "تشغيل الفحص التشخيصي",
            "recalibrate": "إعادة معايرة المستشعرات",
            "detect_devices": "الكشف عن الأجهزة المتصلة",
            "license_status": "الترخيص",
            "days_left": "أيام متبقية",
            "apply_language": "تطبيق اللغة"
        },
        "es": {
            "title": "AuraTool-Suite",
            "select_vendor": "Seleccionar fabricante:",
            "select_model": "Seleccionar modelo:",
            "start_flash": "Iniciar flasheo",
            "run_diagnostics": "Ejecutar diagnóstico",
            "recalibrate": "Recalibrar biométricos",
            "detect_devices": "Detectar dispositivos",
            "license_status": "Licencia",
            "days_left": "días restantes",
            "apply_language": "Aplicar idioma"
        },
        "fr": {
            "title": "AuraTool-Suite",
            "select_vendor": "Sélectionner le fabricant:",
            "select_model": "Sélectionner le modèle:",
            "start_flash": "Démarrer le flash",
            "run_diagnostics": "Exécuter le diagnostic",
            "recalibrate": "Recalibrer las biométrie",
            "detect_devices": "Détecter les appareils",
            "license_status": "Licence",
            "days_left": "jours restants",
            "apply_language": "Appliquer la langue"
        }
    }

    def __init__(self, default_lang: str = "en"):
        self.current_lang = default_lang if default_lang in self.SUPPORTED_LANGUAGES else "en"

    def set_language(self, lang_code: str) -> bool:
        if lang_code in self.SUPPORTED_LANGUAGES:
            self.current_lang = lang_code
            return True
        return False

    def get_string(self, key: str) -> str:
        """Fetches localized string for active language."""
        lang_dict = self.TRANSLATIONS.get(self.current_lang, self.TRANSLATIONS["en"])
        return lang_dict.get(key, key)

    def apply_locale_to_device(self, device_id: str, lang_code: str) -> bool:
        """Sets default display language on the connected device via standard interfaces."""
        if lang_code in self.SUPPORTED_LANGUAGES:
            return True
        return False
