"""
Unit Tests — WearableEngine
============================
Tests for modules/wearables.py covering WEARABLE_BRAND_MAP integrity,
WearOS diagnostics/flash, Apple Watch DFU, Galaxy Watch flash,
fitness band sync, universal wearable flash, and ADB/Fastboot wrappers.
"""

import os
import platform
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.wearables import WearableEngine, WEARABLE_BRAND_MAP


# ═══════════════════════════════════════════════════════════════════════════════
#  WEARABLE BRAND MAP
# ═══════════════════════════════════════════════════════════════════════════════

class TestWearableBrandMap(unittest.TestCase):
    """Test WEARABLE_BRAND_MAP data integrity."""

    def test_brand_map_not_empty(self):
        self.assertGreater(len(WEARABLE_BRAND_MAP), 0)

    def test_all_brands_have_required_keys(self):
        required = {"protocol", "chipset", "vendor_id"}
        for brand, mapping in WEARABLE_BRAND_MAP.items():
            with self.subTest(brand=brand):
                self.assertIsInstance(mapping, dict)
                self.assertTrue(required.issubset(mapping.keys()),
                                f"{brand} missing keys: {required - mapping.keys()}")

    def test_samsung_wearable_mapping(self):
        m = WEARABLE_BRAND_MAP["Samsung"]
        self.assertEqual(m["protocol"], "SAMSUNG_ODIN")
        self.assertEqual(m["chipset"], "Exynos_W")

    def test_apple_wearable_mapping(self):
        m = WEARABLE_BRAND_MAP["Apple"]
        self.assertEqual(m["protocol"], "APPLE_DFU")
        self.assertEqual(m["chipset"], "Apple_S")

    def test_google_wearable_mapping(self):
        m = WEARABLE_BRAND_MAP["Google"]
        self.assertEqual(m["protocol"], "FASTBOOT")
        self.assertEqual(m["chipset"], "Google_Tensor")

    def test_garmin_mapping_is_proprietary(self):
        m = WEARABLE_BRAND_MAP["Garmin"]
        self.assertEqual(m["protocol"], "Proprietary")

    def test_fitbit_mapping_is_proprietary(self):
        m = WEARABLE_BRAND_MAP["Fitbit"]
        self.assertEqual(m["protocol"], "Proprietary")

    def test_vendor_ids_are_hex_strings(self):
        for brand, mapping in WEARABLE_BRAND_MAP.items():
            with self.subTest(brand=brand):
                vid = mapping["vendor_id"]
                self.assertIsInstance(vid, str)
                self.assertEqual(len(vid), 4)
                int(vid, 16)  # Should not raise

    def test_protocols_are_valid(self):
        valid = {"FASTBOOT", "SAMSUNG_ODIN", "APPLE_DFU", "Proprietary"}
        for brand, mapping in WEARABLE_BRAND_MAP.items():
            with self.subTest(brand=brand):
                self.assertIn(mapping["protocol"], valid)


# ═══════════════════════════════════════════════════════════════════════════════
#  WEARABLE ENGINE INIT
# ═══════════════════════════════════════════════════════════════════════════════

class TestWearableEngineInit(unittest.TestCase):
    """Test WearableEngine initialization."""

    def test_engine_creates(self):
        eng = WearableEngine()
        self.assertIsNotNone(eng)

    def test_os_type_is_string(self):
        eng = WearableEngine()
        self.assertIsInstance(eng.os_type, str)
        self.assertIn(eng.os_type, ("linux", "windows", "darwin"))

    def test_has_adb(self):
        eng = WearableEngine()
        self.assertIsNotNone(eng._adb)

    def test_has_fastboot(self):
        eng = WearableEngine()
        self.assertIsNotNone(eng._fastboot)

    def test_multiple_instances_are_independent(self):
        e1 = WearableEngine()
        e2 = WearableEngine()
        self.assertIsNot(e1, e2)


# ═══════════════════════════════════════════════════════════════════════════════
#  ADB / FASTBOOT WRAPPERS
# ═══════════════════════════════════════════════════════════════════════════════

class TestWearableADBWrapper(unittest.TestCase):
    """Test ADB and Fastboot command wrappers."""

    def test_adb_returns_dict(self):
        eng = WearableEngine()
        r = eng.adb("devices")
        self.assertIsInstance(r, dict)
        self.assertIn("success", r)
        self.assertIn("stdout", r)
        self.assertIn("stderr", r)
        self.assertIn("returncode", r)

    def test_fastboot_returns_dict(self):
        eng = WearableEngine()
        r = eng.fastboot("devices")
        self.assertIsInstance(r, dict)

    @patch("modules.wearables.subprocess.run")
    def test_adb_command_construction(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")
        eng = WearableEngine()
        eng.adb("-s", "WATCH01", "shell", "getprop", "ro.product.model")
        args = mock_run.call_args[0][0]
        self.assertIn("-s", args)
        self.assertIn("WATCH01", args)

    @patch("modules.wearables.subprocess.run")
    def test_adb_handles_timeout(self, mock_run):
        mock_run.side_effect = Exception("timeout")
        eng = WearableEngine()
        r = eng.adb("shell", "sleep", "100")
        self.assertFalse(r["success"])

    @patch("modules.wearables.subprocess.run")
    def test_adb_handles_file_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError("not found")
        eng = WearableEngine()
        r = eng.adb("devices")
        self.assertFalse(r["success"])


# ═══════════════════════════════════════════════════════════════════════════════
#  WEAROS DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════════════════════

class TestWearOSDiagnostics(unittest.TestCase):
    """Test WearOS diagnostic routines."""

    @patch("modules.wearables.subprocess.run")
    def test_diagnostics_returns_complete(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="model_info", stderr="")
        eng = WearableEngine()
        r = eng.wearos_diagnostics("WATCH01")
        self.assertEqual(r["status"], "COMPLETED")
        self.assertEqual(r["device_id"], "WATCH01")
        self.assertEqual(r["platform"], "WearOS")

    @patch("modules.wearables.subprocess.run")
    def test_diagnostics_includes_info(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="Galaxy Watch6", stderr="")
        eng = WearableEngine()
        r = eng.wearos_diagnostics("WATCH01")
        self.assertIn("info", r)
        self.assertIn("model", r["info"])
        self.assertIn("has_nfc", r["info"])
        self.assertIn("has_heart_rate", r["info"])
        self.assertIn("has_gps", r["info"])

    @patch("modules.wearables.subprocess.run")
    def test_diagnostics_handles_adb_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="offline")
        eng = WearableEngine()
        r = eng.wearos_diagnostics("WATCH01")
        self.assertEqual(r["status"], "COMPLETED")
        self.assertEqual(r["info"]["model"], "unknown")

    @patch("modules.wearables.subprocess.run")
    def test_diagnostics_nfc_detection(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="feature:nfc\nfeature:bluetooth", stderr="")
        eng = WearableEngine()
        r = eng.wearos_diagnostics("WATCH01")
        self.assertTrue(r["info"]["has_nfc"])

    @patch("modules.wearables.subprocess.run")
    def test_diagnostics_heart_rate_detection(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="feature:sensor_heartrate", stderr="")
        eng = WearableEngine()
        r = eng.wearos_diagnostics("WATCH01")
        self.assertTrue(r["info"]["has_heart_rate"])


# ═══════════════════════════════════════════════════════════════════════════════
#  WEAROS FLASH
# ═══════════════════════════════════════════════════════════════════════════════

class TestWearOSFlash(unittest.TestCase):
    """Test WearOS flash operations."""

    def test_wearos_flash_with_directory(self):
        eng = WearableEngine()
        with tempfile.TemporaryDirectory() as td:
            for name in ["boot.img", "system.img"]:
                (Path(td) / name).write_bytes(b"fake")
            r = eng.wearos_flash("WATCH01", td)
            self.assertIn("results", r)
            self.assertEqual(len(r["results"]), 2)

    def test_wearos_flash_with_empty_directory(self):
        eng = WearableEngine()
        with tempfile.TemporaryDirectory() as td:
            r = eng.wearos_flash("WATCH01", td)
            self.assertIn("results", r)
            self.assertEqual(len(r["results"]), 0)

    def test_wearos_flash_single_file(self):
        eng = WearableEngine()
        r = eng.wearos_flash("WATCH01", "/tmp/firmware.img")
        self.assertIsInstance(r, dict)


# ═══════════════════════════════════════════════════════════════════════════════
#  APPLE WATCH DFU
# ═══════════════════════════════════════════════════════════════════════════════

class TestAppleWatchDFU(unittest.TestCase):
    """Test Apple Watch DFU restore."""

    def test_dfu_restore_simulated(self):
        eng = WearableEngine()
        r = eng.apple_watch_dfu("WATCH01", "/tmp/watch.ipsw")
        self.assertEqual(r["status"], "SIMULATED")
        self.assertEqual(r["method"], "APPLE_WATCH_DFU")

    def test_dfu_restore_returns_dict(self):
        eng = WearableEngine()
        r = eng.apple_watch_dfu("DEVICE_ID", "/path/to/firmware")
        self.assertIsInstance(r, dict)
        self.assertIn("status", r)
        self.assertIn("method", r)


# ═══════════════════════════════════════════════════════════════════════════════
#  SAMSUNG GALAXY WATCH FLASH
# ═══════════════════════════════════════════════════════════════════════════════

class TestGalaxyWatchFlash(unittest.TestCase):
    """Test Samsung Galaxy Watch flash."""

    def test_galaxy_watch_flash_simulated(self):
        eng = WearableEngine()
        r = eng.galaxy_watch_flash("WATCH01", "/tmp/firmware.tar")
        if not shutil.which("heimdall"):
            self.assertEqual(r["status"], "SIMULATED")
            self.assertEqual(r["method"], "TIZEN_ODIN")

    @patch("modules.wearables.shutil.which", return_value="/usr/bin/heimdall")
    @patch("modules.wearables.subprocess.run")
    def test_galaxy_watch_flash_with_heimdall(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(returncode=0, stdout="Done", stderr="")
        eng = WearableEngine()
        r = eng.galaxy_watch_flash("WATCH01", "/tmp/firmware.tar")
        self.assertEqual(r["method"], "HEIMDALL")
        self.assertTrue(r["success"])


# ═══════════════════════════════════════════════════════════════════════════════
#  UNIVERSAL WEARABLE FLASH
# ═══════════════════════════════════════════════════════════════════════════════

class TestUniversalWearableFlash(unittest.TestCase):
    """Test flash_wearable routing to correct protocol."""

    def test_flash_apple_routes_to_dfu(self):
        eng = WearableEngine()
        r = eng.flash_wearable("WATCH01", "/tmp/firmware.ipsw", "Apple")
        self.assertEqual(r["status"], "SIMULATED")
        self.assertEqual(r["method"], "APPLE_WATCH_DFU")

    def test_flash_samsung_routes_to_odin(self):
        eng = WearableEngine()
        r = eng.flash_wearable("WATCH01", "/tmp/firmware.tar", "Samsung")
        self.assertIn("status", r)

    def test_flash_garmin_returns_unsupported(self):
        eng = WearableEngine()
        r = eng.flash_wearable("WATCH01", "/tmp/firmware.bin", "Garmin")
        self.assertEqual(r["status"], "UNSUPPORTED")
        self.assertEqual(r["brand"], "Garmin")

    def test_flash_fitbit_returns_unsupported(self):
        eng = WearableEngine()
        r = eng.flash_wearable("WATCH01", "/tmp/firmware.bin", "Fitbit")
        self.assertEqual(r["status"], "UNSUPPORTED")

    def test_flash_xiaomi_routes_to_wearos(self):
        eng = WearableEngine()
        r = eng.flash_wearable("WATCH01", "/tmp/firmware.img", "Xiaomi")
        self.assertIsInstance(r, dict)

    def test_flash_unknown_brand(self):
        eng = WearableEngine()
        r = eng.flash_wearable("WATCH01", "/tmp/firmware.img", "UnknownBrand")
        self.assertIsInstance(r, dict)

    def test_flash_with_directory(self):
        eng = WearableEngine()
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "boot.img").write_bytes(b"fake")
            r = eng.flash_wearable("WATCH01", td, "Xiaomi")
            self.assertIn("results", r)

    def test_flash_proprietary_returns_unsupported(self):
        """Brands with Proprietary protocol should return UNSUPPORTED."""
        eng = WearableEngine()
        for brand in ["Garmin", "Fitbit"]:
            r = eng.flash_wearable("WATCH01", "/tmp/fw", brand)
            self.assertEqual(r["status"], "UNSUPPORTED", f"{brand} should be UNSUPPORTED")


# ═══════════════════════════════════════════════════════════════════════════════
#  FITNESS BAND SYNC
# ═══════════════════════════════════════════════════════════════════════════════

class TestFitnessBandSync(unittest.TestCase):
    """Test fitness band sync operations."""

    def test_sync_garmin(self):
        eng = WearableEngine()
        r = eng.sync_fitness_band("WATCH01", "Garmin")
        self.assertEqual(r["sync_status"], "COMPLETED")
        self.assertTrue(r["data_exported"])
        self.assertEqual(r["band_type"], "Garmin")

    def test_sync_fitbit(self):
        eng = WearableEngine()
        r = eng.sync_fitness_band("WATCH01", "Fitbit")
        self.assertEqual(r["sync_status"], "COMPLETED")

    def test_sync_amazfit(self):
        eng = WearableEngine()
        r = eng.sync_fitness_band("WATCH01", "Amazfit")
        self.assertEqual(r["sync_status"], "COMPLETED")

    def test_sync_returns_correct_device_id(self):
        eng = WearableEngine()
        r = eng.sync_fitness_band("MY_BAND_123", "Garmin")
        self.assertEqual(r["device_id"], "MY_BAND_123")

    def test_sync_empty_band_type(self):
        eng = WearableEngine()
        r = eng.sync_fitness_band("WATCH01", "")
        self.assertEqual(r["sync_status"], "COMPLETED")


# ═══════════════════════════════════════════════════════════════════════════════
#  EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════════

class TestWearableEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def test_empty_device_id(self):
        eng = WearableEngine()
        r = eng.flash_wearable("", "/tmp/firmware.img", "Xiaomi")
        self.assertIsInstance(r, dict)

    def test_empty_brand(self):
        eng = WearableEngine()
        r = eng.flash_wearable("WATCH01", "/tmp/firmware.img", "")
        self.assertIsInstance(r, dict)

    def test_all_brand_count(self):
        self.assertGreaterEqual(len(WEARABLE_BRAND_MAP), 10)

    def test_protocols_unique_per_brand(self):
        """Each brand should have exactly one protocol."""
        for brand, mapping in WEARABLE_BRAND_MAP.items():
            with self.subTest(brand=brand):
                self.assertIsInstance(mapping["protocol"], str)
                self.assertGreater(len(mapping["protocol"]), 0)


if __name__ == "__main__":
    unittest.main()
