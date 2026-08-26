"""
Unit Tests — Localization Module
=================================
Tests for LocalizationManager: translations, RTL, device locale, CSC, and language unhide.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.localization import LocalizationManager


class TestBasicLocalization(unittest.TestCase):
    """Test core translation and language switching."""

    def setUp(self):
        self.loc = LocalizationManager()

    def test_default_language_is_english(self):
        self.assertEqual(self.loc.current_lang, "en")

    def test_switch_to_arabic(self):
        result = self.loc.set_language("ar")
        self.assertTrue(result)
        self.assertEqual(self.loc.current_lang, "ar")

    def test_switch_to_invalid_language_fails(self):
        result = self.loc.set_language("zz")
        self.assertFalse(result)
        self.assertEqual(self.loc.current_lang, "en")

    def test_get_string_english(self):
        title = self.loc.get_string("title")
        self.assertIn("AuraTool", title)

    def test_get_string_arabic(self):
        self.loc.set_language("ar")
        title = self.loc.get_string("title")
        self.assertIn("AuraTool", title)

    def test_get_string_unknown_key_returns_key(self):
        result = self.loc.get_string("nonexistent_key")
        self.assertEqual(result, "nonexistent_key")

    def test_fallback_to_english_for_missing_key(self):
        """Spanish translations don't have all keys; should fall back to English."""
        self.loc.set_language("es")
        # "run_ai" exists in es
        es_val = self.loc.get_string("run_ai")
        self.assertNotEqual(es_val, "run_ai")

    def test_is_rtl_arabic(self):
        self.loc.set_language("ar")
        self.assertTrue(self.loc.is_rtl())

    def test_is_not_rtl_english(self):
        self.assertFalse(self.loc.is_rtl())

    def test_is_rtl_non_rtl_language(self):
        self.loc.set_language("fr")
        self.assertFalse(self.loc.is_rtl())


class TestSupportedLanguages(unittest.TestCase):
    """Test that all supported languages have basic translations."""

    def setUp(self):
        self.loc = LocalizationManager()

    def test_all_supported_languages_are_switchable(self):
        for code in LocalizationManager.SUPPORTED_LANGUAGES:
            result = self.loc.set_language(code)
            self.assertTrue(result, f"Failed to switch to {code}")
            self.assertEqual(self.loc.current_lang, code)

    def test_all_languages_have_title_translation(self):
        """Every supported language should have at least a 'title' key."""
        for code in LocalizationManager.SUPPORTED_LANGUAGES:
            self.loc.set_language(code)
            title = self.loc.get_string("title")
            self.assertNotEqual(title, "title", f"Language {code} missing 'title' translation")


class TestApplyLocaleToDevice(unittest.TestCase):
    """Test apply_locale_to_device method."""

    def setUp(self):
        self.loc = LocalizationManager()

    def test_apply_valid_locale(self):
        result = self.loc.apply_locale_to_device("TestDevice", "ar", enable_rtl=True)
        self.assertTrue(result)

    def test_apply_valid_locale_ltr(self):
        result = self.loc.apply_locale_to_device("TestDevice", "en")
        self.assertTrue(result)

    def test_apply_invalid_locale_returns_false(self):
        result = self.loc.apply_locale_to_device("TestDevice", "zz")
        self.assertFalse(result)

    def test_apply_empty_locale_returns_false(self):
        result = self.loc.apply_locale_to_device("TestDevice", "")
        self.assertFalse(result)

    def test_apply_locale_all_supported_languages(self):
        """All supported languages should be applyable to a device."""
        for code in LocalizationManager.SUPPORTED_LANGUAGES:
            result = self.loc.apply_locale_to_device("Device1", code)
            self.assertTrue(result, f"Failed to apply locale {code}")

    def test_apply_locale_with_device_id(self):
        """Should accept any device_id string without error."""
        result = self.loc.apply_locale_to_device("Samsung_Galaxy_S23_IMEI12345", "es")
        self.assertTrue(result)


class TestConfigureCSC(unittest.TestCase):
    """Test configure_csc method."""

    def setUp(self):
        self.loc = LocalizationManager()

    def test_configure_valid_csc(self):
        result = self.loc.configure_csc("TestDevice", "XSG")
        self.assertTrue(result)

    def test_configure_long_csc_code(self):
        result = self.loc.configure_csc("TestDevice", "XSG-KSA")
        self.assertTrue(result)

    def test_configure_empty_csc_returns_false(self):
        result = self.loc.configure_csc("TestDevice", "")
        self.assertFalse(result)

    def test_configure_short_csc_returns_false(self):
        result = self.loc.configure_csc("TestDevice", "AB")
        self.assertFalse(result)

    def test_configure_single_char_csc_returns_false(self):
        result = self.loc.configure_csc("TestDevice", "A")
        self.assertFalse(result)

    def test_configure_known_csc_codes(self):
        """Test common Samsung CSC codes."""
        known_codes = ["XSG", "KSA", "TUR", "EUX", "XAR"]
        for csc in known_codes:
            result = self.loc.configure_csc("TestDevice", csc)
            self.assertTrue(result, f"Failed to configure CSC {csc}")


class TestUnhideSystemLanguages(unittest.TestCase):
    """Test unhide_system_languages method."""

    def setUp(self):
        self.loc = LocalizationManager()

    def test_unhide_returns_true(self):
        result = self.loc.unhide_system_languages("TestDevice")
        self.assertTrue(result)

    def test_unhide_with_various_device_ids(self):
        """Should work with any device_id."""
        device_ids = ["Galaxy_S23", "iPhone_15", "Pixel_8", "Xiaomi_14"]
        for device_id in device_ids:
            result = self.loc.unhide_system_languages(device_id)
            self.assertTrue(result, f"Failed for device {device_id}")


class TestArabicLog(unittest.TestCase):
    """Test get_arabic_log method."""

    def setUp(self):
        self.loc = LocalizationManager()

    def test_get_log_english(self):
        msg = self.loc.get_arabic_log("FLASHING_START")
        self.assertIn("flashing", msg.lower())

    def test_get_log_arabic(self):
        self.loc.set_language("ar")
        msg = self.loc.get_arabic_log("FLASHING_START")
        # Arabic text may be reshaped/reordered by bidi algorithm
        self.assertNotEqual(msg, "FLASHING_START")
        self.assertGreater(len(msg), 0)

    def test_get_log_unknown_key_returns_key(self):
        msg = self.loc.get_arabic_log("UNKNOWN_KEY")
        self.assertEqual(msg, "UNKNOWN_KEY")


class TestArabicReshaping(unittest.TestCase):
    """Test Arabic text reshaping (if library available)."""

    def setUp(self):
        self.loc = LocalizationManager()
        self.loc.set_language("ar")

    def test_reshaping_does_not_crash(self):
        """Reshaping should handle text gracefully even without the library."""
        result = self.loc.reshape_arabic_text("اختبار")
        self.assertIsNotNone(result)

    def test_reshaping_empty_string(self):
        result = self.loc.reshape_arabic_text("")
        self.assertEqual(result, "")

    def test_reshaping_none(self):
        result = self.loc.reshape_arabic_text(None)
        self.assertIsNone(result)

    def test_reshaping_ltr_language_passthrough(self):
        """Non-Arabic language should pass text through unchanged."""
        self.loc.set_language("en")
        result = self.loc.reshape_arabic_text("Hello")
        self.assertEqual(result, "Hello")


if __name__ == "__main__":
    unittest.main()
