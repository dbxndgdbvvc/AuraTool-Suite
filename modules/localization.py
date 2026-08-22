class LocalizationManager:
    """Handles internationalization (i18n) and locale updates for connected devices."""

    SUPPORTED_LANGUAGES = {
        "en": "English",
        "ar": "العربية",
        "es": "Español",
        "fr": "Français"
    }

    def __init__(self, default_lang: str = "en"):
        self.current_lang = default_lang

    def set_language(self, lang_code: str) -> bool:
        if lang_code in self.SUPPORTED_LANGUAGES:
            self.current_lang = lang_code
            return True
        return False

    def apply_locale_to_device(self, device_id: str, lang_code: str) -> bool:
        """Sets default display language on the connected device via standard interfaces."""
        if lang_code in self.SUPPORTED_LANGUAGES:
            print(f"Applying locale '{lang_code}' to device {device_id}")
            return True
        return False
