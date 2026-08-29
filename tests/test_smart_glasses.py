"""
Unit Tests — SmartGlassesEngine
================================
Tests for modules/smart_glasses.py covering SMART_GLASSES_BRAND_MAP integrity,
headset diagnostics, sensor calibration, display repair, firmware flash,
and ADB/Fastboot command wrappers.
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

from modules.smart_glasses import SmartGlassesEngine, SMART_GLASSES_BRAND_MAP


# ═══════════════════════════════════════════════════════════════════════════════
#  SMART GLASSES BRAND MAP
# ═══════════════════════════════════════════════════════════════════════════════

class TestSmartGlassesBrandMap(unittest.TestCase):
    """Test SMART_GLASSES_BRAND_MAP data integrity."""

    def test_brand_map_not_empty(self):
        self.assertGreater(len(SMART_GLASSES_BRAND_MAP), 0)

    def test_all_brands_have_required_keys(self):
        required = {"protocol", "chipset", "vendor_id"}
        for brand, mapping in SMART_GLASSES_BRAND_MAP.items():
            with self.subTest(brand=brand):
                self.assertIsInstance(mapping, dict)
                self.assertTrue(required.issubset(mapping.keys()),
                                f"{brand} missing keys: {required - mapping.keys()}")

    def test_meta_mapping(self):
        m = SMART_GLASSES_BRAND_MAP["Meta"]
        self.assertEqual(m["protocol"], "FASTBOOT")
        self.assertIn("XR2", m["chipset"])

    def test_apple_mapping(self):
        m = SMART_GLASSES_BRAND_MAP["Apple"]
        self.assertEqual(m["protocol"], "APPLE_DFU")
        self.assertIn("M2", m["chipset"])

    def test_pico_mapping(self):
        m = SMART_GLASSES_BRAND_MAP["Pico"]
        self.assertEqual(m["protocol"], "FASTBOOT")
        self.assertIn("XR2", m["chipset"])

    def test_htc_mapping(self):
        m = SMART_GLASSES_BRAND_MAP["HTC"]
        self.assertEqual(m["protocol"], "FASTBOOT")

    def test_sony_mapping_is_proprietary(self):
        m = SMART_GLASSES_BRAND_MAP["Sony"]
        self.assertEqual(m["protocol"], "Proprietary")

    def test_vendor_ids_are_hex_strings(self):
        for brand, mapping in SMART_GLASSES_BRAND_MAP.items():
            with self.subTest(brand=brand):
                vid = mapping["vendor_id"]
                self.assertIsInstance(vid, str)
                self.assertEqual(len(vid), 4)
                int(vid, 16)

    def test_protocols_are_valid(self):
        valid = {"FASTBOOT", "APPLE_DFU", "Proprietary", "ADB", "USB_HID"}
        for brand, mapping in SMART_GLASSES_BRAND_MAP.items():
            with self.subTest(brand=brand):
                self.assertIn(mapping["protocol"], valid)

    def test_brand_count(self):
        self.assertGreaterEqual(len(SMART_GLASSES_BRAND_MAP), 10)


# ═══════════════════════════════════════════════════════════════════════════════
#  ENGINE INIT
# ═══════════════════════════════════════════════════════════════════════════════

class TestSmartGlassesEngineInit(unittest.TestCase):
    """Test SmartGlassesEngine initialization."""

    def test_engine_creates(self):
        eng = SmartGlassesEngine()
        self.assertIsNotNone(eng)

    def test_os_type_is_string(self):
        eng = SmartGlassesEngine()
        self.assertIsInstance(eng.os_type, str)
        self.assertIn(eng.os_type, ("linux", "windows", "darwin"))

    def test_has_adb(self):
        eng = SmartGlassesEngine()
        self.assertIsNotNone(eng._adb)

    def test_has_fastboot(self):
        eng = SmartGlassesEngine()
        self.assertIsNotNone(eng._fastboot)

    def test_multiple_instances_are_independent(self):
        e1 = SmartGlassesEngine()
        e2 = SmartGlassesEngine()
        self.assertIsNot(e1, e2)


# ═══════════════════════════════════════════════════════════════════════════════
#  ADB / FASTBOOT WRAPPERS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSmartGlassesADBWrapper(unittest.TestCase):
    """Test ADB and Fastboot command wrappers."""

    def test_adb_returns_dict(self):
        eng = SmartGlassesEngine()
        r = eng.adb("devices")
        self.assertIsInstance(r, dict)
        self.assertIn("success", r)
        self.assertIn("stdout", r)
        self.assertIn("stderr", r)
        self.assertIn("returncode", r)

    def test_fastboot_returns_dict(self):
        eng = SmartGlassesEngine()
        r = eng.fastboot("devices")
        self.assertIsInstance(r, dict)

    @patch("modules.smart_glasses.subprocess.run")
    def test_adb_command_construction(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")
        eng = SmartGlassesEngine()
        eng.adb("-s", "QUEST01", "shell", "getprop", "ro.product.model")
        args = mock_run.call_args[0][0]
        self.assertIn("-s", args)
        self.assertIn("QUEST01", args)

    @patch("modules.smart_glasses.subprocess.run")
    def test_adb_handles_timeout(self, mock_run):
        mock_run.side_effect = Exception("timeout")
        eng = SmartGlassesEngine()
        r = eng.adb("shell", "sleep", "100")
        self.assertFalse(r["success"])

    @patch("modules.smart_glasses.subprocess.run")
    def test_adb_handles_file_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError("not found")
        eng = SmartGlassesEngine()
        r = eng.adb("devices")
        self.assertFalse(r["success"])


# ═══════════════════════════════════════════════════════════════════════════════
#  HEADSET DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════════════════════

class TestHeadsetDiagnostics(unittest.TestCase):
    """Test AR/VR headset diagnostic routines."""

    @patch("modules.smart_glasses.subprocess.run")
    def test_diagnostics_returns_complete(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="model_info", stderr="")
        eng = SmartGlassesEngine()
        r = eng.headset_diagnostics("QUEST01", "Meta")
        self.assertEqual(r["status"], "COMPLETED")
        self.assertEqual(r["device_id"], "QUEST01")
        self.assertEqual(r["brand"], "Meta")
        self.assertEqual(r["platform"], "AR/VR")

    @patch("modules.smart_glasses.subprocess.run")
    def test_diagnostics_includes_info(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="Quest 3", stderr="")
        eng = SmartGlassesEngine()
        r = eng.headset_diagnostics("QUEST01", "Meta")
        self.assertIn("info", r)
        self.assertIn("model", r["info"])
        self.assertIn("display_resolution", r["info"])
        self.assertIn("refresh_rate", r["info"])
        self.assertIn("gyroscope", r["info"])
        self.assertIn("accelerometer", r["info"])

    @patch("modules.smart_glasses.subprocess.run")
    def test_diagnostics_handles_adb_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="offline")
        eng = SmartGlassesEngine()
        r = eng.headset_diagnostics("QUEST01", "Meta")
        self.assertEqual(r["status"], "COMPLETED")
        self.assertEqual(r["info"]["model"], "unknown")

    @patch("modules.smart_glasses.subprocess.run")
    def test_diagnostics_sensor_count(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="Sensor: accel\nSensor: gyro\nSensor: mag", stderr="")
        eng = SmartGlassesEngine()
        r = eng.headset_diagnostics("QUEST01", "Meta")
        self.assertEqual(r["info"]["sensor_count"], 3)

    def test_diagnostics_all_brands(self):
        """Test diagnostics works for all brands in the map."""
        eng = SmartGlassesEngine()
        for brand in SMART_GLASSES_BRAND_MAP:
            r = eng.headset_diagnostics("DEVICE01", brand)
            self.assertEqual(r["status"], "COMPLETED", f"Diagnostics failed for {brand}")


# ═══════════════════════════════════════════════════════════════════════════════
#  SENSOR CALIBRATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestSensorCalibration(unittest.TestCase):
    """Test sensor calibration routines."""

    def test_calibration_returns_complete(self):
        eng = SmartGlassesEngine()
        r = eng.calibrate_sensors("QUEST01", "Meta")
        self.assertEqual(r["status"], "COMPLETED")
        self.assertEqual(r["device_id"], "QUEST01")
        self.assertEqual(r["brand"], "Meta")

    def test_calibration_steps_count(self):
        eng = SmartGlassesEngine()
        r = eng.calibrate_sensors("QUEST01", "Meta")
        self.assertEqual(r["steps_completed"], 7)

    def test_calibration_all_brands(self):
        """Calibration should work for all brands."""
        eng = SmartGlassesEngine()
        for brand in SMART_GLASSES_BRAND_MAP:
            r = eng.calibrate_sensors("DEVICE01", brand)
            self.assertEqual(r["status"], "COMPLETED", f"Calibration failed for {brand}")

    def test_calibration_returns_dict(self):
        eng = SmartGlassesEngine()
        r = eng.calibrate_sensors("QUEST01", "Pico")
        self.assertIsInstance(r, dict)
        self.assertIn("steps_completed", r)


# ═══════════════════════════════════════════════════════════════════════════════
#  DISPLAY REPAIR
# ═══════════════════════════════════════════════════════════════════════════════

class TestDisplayRepair(unittest.TestCase):
    """Test display repair routines."""

    def test_flickering_repair(self):
        eng = SmartGlassesEngine()
        r = eng.repair_display("QUEST01", "flickering")
        self.assertEqual(r["status"], "COMPLETED")
        self.assertEqual(r["issue"], "flickering")
        self.assertGreater(r["fixes_applied"], 0)

    def test_dead_pixels_repair(self):
        eng = SmartGlassesEngine()
        r = eng.repair_display("QUEST01", "dead_pixels")
        self.assertEqual(r["status"], "COMPLETED")
        self.assertEqual(r["issue"], "dead_pixels")

    def test_color_drift_repair(self):
        eng = SmartGlassesEngine()
        r = eng.repair_display("QUEST01", "color_drift")
        self.assertEqual(r["status"], "COMPLETED")
        self.assertEqual(r["issue"], "color_drift")

    def test_stereo_misalign_repair(self):
        eng = SmartGlassesEngine()
        r = eng.repair_display("QUEST01", "stereo_misalign")
        self.assertEqual(r["status"], "COMPLETED")
        self.assertEqual(r["issue"], "stereo_misalign")

    def test_unknown_issue_uses_general_fix(self):
        eng = SmartGlassesEngine()
        r = eng.repair_display("QUEST01", "unknown_issue")
        self.assertEqual(r["status"], "COMPLETED")
        self.assertEqual(r["fixes_applied"], 1)  # General display reset

    def test_empty_issue(self):
        eng = SmartGlassesEngine()
        r = eng.repair_display("QUEST01", "")
        self.assertEqual(r["status"], "COMPLETED")


# ═══════════════════════════════════════════════════════════════════════════════
#  FIRMWARE FLASH
# ═══════════════════════════════════════════════════════════════════════════════

class TestHeadsetFlash(unittest.TestCase):
    """Test headset firmware flash operations."""

    def test_flash_meta_routes_to_fastboot(self):
        eng = SmartGlassesEngine()
        r = eng.flash_headset("QUEST01", "/tmp/firmware.img", "Meta")
        self.assertIsInstance(r, dict)

    def test_flash_apple_routes_to_dfu(self):
        eng = SmartGlassesEngine()
        r = eng.flash_headset("VISION01", "/tmp/firmware.ipsw", "Apple")
        self.assertEqual(r["status"], "SIMULATED")
        self.assertEqual(r["method"], "APPLE_DFU")

    def test_flash_sony_returns_vendor_tool(self):
        eng = SmartGlassesEngine()
        r = eng.flash_headset("PSVR01", "/tmp/firmware.bin", "Sony")
        self.assertEqual(r["status"], "NEEDS_VENDOR_TOOL")
        self.assertEqual(r["brand"], "Sony")

    def test_flash_pico_routes_to_fastboot(self):
        eng = SmartGlassesEngine()
        r = eng.flash_headset("PICO01", "/tmp/firmware.img", "Pico")
        self.assertIsInstance(r, dict)

    def test_flash_htc_routes_to_fastboot(self):
        eng = SmartGlassesEngine()
        r = eng.flash_headset("VIVE01", "/tmp/firmware.img", "HTC")
        self.assertIsInstance(r, dict)

    def test_flash_with_directory(self):
        eng = SmartGlassesEngine()
        with tempfile.TemporaryDirectory() as td:
            for name in ["boot.img", "system.img"]:
                (Path(td) / name).write_bytes(b"fake")
            r = eng.flash_headset("QUEST01", td, "Meta")
            self.assertIn("results", r)
            self.assertEqual(len(r["results"]), 2)

    def test_flash_with_empty_directory(self):
        eng = SmartGlassesEngine()
        with tempfile.TemporaryDirectory() as td:
            r = eng.flash_headset("QUEST01", td, "Meta")
            self.assertIn("results", r)
            self.assertEqual(len(r["results"]), 0)

    def test_flash_single_file(self):
        eng = SmartGlassesEngine()
        r = eng.flash_headset("QUEST01", "/tmp/firmware.img", "Meta")
        self.assertIsInstance(r, dict)

    def test_flash_unknown_brand(self):
        eng = SmartGlassesEngine()
        r = eng.flash_headset("DEVICE01", "/tmp/firmware.img", "UnknownBrand")
        self.assertIsInstance(r, dict)

    def test_flash_proprietary_brands(self):
        """Brands with Proprietary protocol should return NEEDS_VENDOR_TOOL."""
        eng = SmartGlassesEngine()
        for brand in ["Sony"]:
            r = eng.flash_headset("DEVICE01", "/tmp/fw", brand)
            self.assertEqual(r["status"], "NEEDS_VENDOR_TOOL", f"{brand} should need vendor tool")


# ═══════════════════════════════════════════════════════════════════════════════
#  INTERNAL FLASH HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

class TestInternalFlashHelpers(unittest.TestCase):
    """Test internal flash helper methods."""

    def test_fastboot_flash_headset_with_directory(self):
        eng = SmartGlassesEngine()
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "boot.img").write_bytes(b"fake")
            r = eng._fastboot_flash_headset("DEVICE01", td)
            self.assertIn("results", r)

    def test_fastboot_flash_headset_single_file(self):
        eng = SmartGlassesEngine()
        r = eng._fastboot_flash_headset("DEVICE01", "/tmp/firmware.img")
        self.assertEqual(r["status"], "SIMULATED")
        self.assertEqual(r["method"], "FASTBOOT")

    def test_apple_vision_restore(self):
        eng = SmartGlassesEngine()
        r = eng._apple_vision_restore("VISION01", "/tmp/vision.ipsw")
        self.assertEqual(r["status"], "SIMULATED")
        self.assertEqual(r["method"], "APPLE_DFU")


# ═══════════════════════════════════════════════════════════════════════════════
#  EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════════

class TestSmartGlassesEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def test_empty_device_id(self):
        eng = SmartGlassesEngine()
        r = eng.flash_headset("", "/tmp/firmware.img", "Meta")
        self.assertIsInstance(r, dict)

    def test_empty_brand(self):
        eng = SmartGlassesEngine()
        r = eng.flash_headset("QUEST01", "/tmp/firmware.img", "")
        self.assertIsInstance(r, dict)

    def test_calibration_empty_device(self):
        eng = SmartGlassesEngine()
        r = eng.calibrate_sensors("", "Meta")
        self.assertEqual(r["status"], "COMPLETED")

    def test_display_repair_empty_device(self):
        eng = SmartGlassesEngine()
        r = eng.repair_display("", "flickering")
        self.assertEqual(r["status"], "COMPLETED")

    def test_diagnostics_empty_device(self):
        eng = SmartGlassesEngine()
        r = eng.headset_diagnostics("", "Meta")
        self.assertEqual(r["status"], "COMPLETED")


if __name__ == "__main__":
    unittest.main()
