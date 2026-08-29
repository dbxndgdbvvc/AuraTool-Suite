"""
Unit Tests — TabletEngine
==========================
Tests for modules/tablets.py covering TABLET_BRAND_MAP integrity,
iPad DFU restore, Samsung Tab ODIN flash, universal tablet flash,
tablet diagnostics, and ADB/Fastboot command wrappers.
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

from modules.tablets import TabletEngine, TABLET_BRAND_MAP


# ═══════════════════════════════════════════════════════════════════════════════
#  TABLET BRAND MAP
# ═══════════════════════════════════════════════════════════════════════════════

class TestTabletBrandMap(unittest.TestCase):
    """Test TABLET_BRAND_MAP data integrity."""

    def test_brand_map_not_empty(self):
        self.assertGreater(len(TABLET_BRAND_MAP), 0)

    def test_all_brands_have_required_keys(self):
        required = {"protocol", "frp", "vendor_id"}
        for brand, mapping in TABLET_BRAND_MAP.items():
            with self.subTest(brand=brand):
                self.assertIsInstance(mapping, dict)
                self.assertTrue(required.issubset(mapping.keys()),
                                f"{brand} missing keys: {required - mapping.keys()}")

    def test_samsung_tablet_mapping(self):
        m = TABLET_BRAND_MAP["Samsung"]
        self.assertEqual(m["protocol"], "SAMSUNG_ODIN")
        self.assertEqual(m["frp"], "ODIN_MODE")
        self.assertEqual(m["vendor_id"], "04e8")

    def test_apple_tablet_mapping(self):
        m = TABLET_BRAND_MAP["Apple"]
        self.assertEqual(m["protocol"], "APPLE_DFU")
        self.assertEqual(m["frp"], "DFU_RESTORE")

    def test_xiaomi_tablet_mapping(self):
        m = TABLET_BRAND_MAP["Xiaomi"]
        self.assertEqual(m["protocol"], "FASTBOOT")
        self.assertEqual(m["frp"], "FASTBOOT")

    def test_lenovo_tablet_mapping(self):
        m = TABLET_BRAND_MAP["Lenovo"]
        self.assertEqual(m["protocol"], "FASTBOOT")
        self.assertEqual(m["vendor_id"], "17ef")

    def test_microsoft_tablet_mapping(self):
        m = TABLET_BRAND_MAP["Microsoft"]
        self.assertEqual(m["protocol"], "FASTBOOT")
        self.assertEqual(m["vendor_id"], "045e")

    def test_vendor_ids_are_hex_strings(self):
        for brand, mapping in TABLET_BRAND_MAP.items():
            with self.subTest(brand=brand):
                vid = mapping["vendor_id"]
                self.assertIsInstance(vid, str)
                self.assertEqual(len(vid), 4, f"{brand} vendor_id should be 4 hex chars")
                int(vid, 16)  # Should not raise


# ═══════════════════════════════════════════════════════════════════════════════
#  TABLET ENGINE INIT
# ═══════════════════════════════════════════════════════════════════════════════

class TestTabletEngineInit(unittest.TestCase):
    """Test TabletEngine initialization."""

    def test_engine_creates(self):
        eng = TabletEngine()
        self.assertIsNotNone(eng)

    def test_os_type_is_string(self):
        eng = TabletEngine()
        self.assertIsInstance(eng.os_type, str)
        self.assertIn(eng.os_type, ("linux", "windows", "darwin"))

    def test_has_adb(self):
        eng = TabletEngine()
        self.assertIsNotNone(eng._adb)

    def test_has_fastboot(self):
        eng = TabletEngine()
        self.assertIsNotNone(eng._fastboot)


# ═══════════════════════════════════════════════════════════════════════════════
#  ADB / FASTBOOT WRAPPERS
# ═══════════════════════════════════════════════════════════════════════════════

class TestTabletADBWrapper(unittest.TestCase):
    """Test ADB and Fastboot command wrappers."""

    def test_adb_returns_dict(self):
        eng = TabletEngine()
        r = eng.adb("devices")
        self.assertIsInstance(r, dict)
        self.assertIn("success", r)
        self.assertIn("stdout", r)
        self.assertIn("stderr", r)
        self.assertIn("returncode", r)

    def test_fastboot_returns_dict(self):
        eng = TabletEngine()
        r = eng.fastboot("devices")
        self.assertIsInstance(r, dict)
        self.assertIn("success", r)

    @patch("modules.tablets.subprocess.run")
    def test_adb_command_construction(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="OK", stderr="")
        eng = TabletEngine()
        eng.adb("-s", "DEVICE01", "shell", "getprop", "ro.product.model")
        args = mock_run.call_args[0][0]
        self.assertIn("adb", args[0].lower() if isinstance(args[0], str) else str(args))
        self.assertIn("-s", args)
        self.assertIn("DEVICE01", args)

    @patch("modules.tablets.subprocess.run")
    def test_fastboot_command_construction(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        eng = TabletEngine()
        eng.fastboot("-s", "DEVICE01", "getvar", "product")
        args = mock_run.call_args[0][0]
        self.assertIn("fastboot", args[0].lower() if isinstance(args[0], str) else str(args))

    @patch("modules.tablets.subprocess.run")
    def test_adb_handles_timeout(self, mock_run):
        mock_run.side_effect = Exception("timeout")
        eng = TabletEngine()
        r = eng.adb("shell", "sleep", "100")
        self.assertFalse(r["success"])
        self.assertIn("timeout", r["stderr"].lower())

    @patch("modules.tablets.subprocess.run")
    def test_adb_handles_file_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError("not found")
        eng = TabletEngine()
        r = eng.adb("devices")
        self.assertFalse(r["success"])


# ═══════════════════════════════════════════════════════════════════════════════
#  iPAD DFU RESTORE
# ═══════════════════════════════════════════════════════════════════════════════

class TestIPadDFURestore(unittest.TestCase):
    """Test iPad DFU restore operations."""

    def test_dfu_restore_simulated(self):
        eng = TabletEngine()
        r = eng.ipad_dfu_restore("DEVICE01", "/tmp/firmware.ipsw")
        self.assertIsInstance(r, dict)
        self.assertIn("status", r)
        # Without idevicerestore, should be SIMULATED
        if not shutil.which("idevicerestore"):
            self.assertEqual(r["status"], "SIMULATED")
            self.assertEqual(r["method"], "DFU_RESTORE")

    @patch("modules.tablets.shutil.which", return_value="/usr/bin/idevicerestore")
    @patch("modules.tablets.subprocess.run")
    def test_dfu_restore_with_idevicerestore(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(returncode=0, stdout="Done", stderr="")
        eng = TabletEngine()
        r = eng.ipad_dfu_restore("DEVICE01", "/tmp/test.ipsw")
        self.assertEqual(r["method"], "LIBIMOBILEDEVICE")
        self.assertTrue(r["success"])

    @patch("modules.tablets.shutil.which", return_value="/usr/bin/idevicerestore")
    @patch("modules.tablets.subprocess.run")
    def test_dfu_restore_failure(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Error")
        eng = TabletEngine()
        r = eng.ipad_dfu_restore("DEVICE01", "/tmp/test.ipsw")
        self.assertFalse(r["success"])


# ═══════════════════════════════════════════════════════════════════════════════
#  iPAD PARTITION INFO
# ═══════════════════════════════════════════════════════════════════════════════

class TestIPadPartitionInfo(unittest.TestCase):
    """Test iPad partition info query."""

    @patch("modules.tablets.subprocess.run")
    def test_partition_info_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="sda1\nsda2\nsdb1", stderr="")
        eng = TabletEngine()
        r = eng.ipad_partition_info("DEVICE01")
        self.assertIn("partitions", r)
        self.assertEqual(len(r["partitions"]), 3)

    @patch("modules.tablets.subprocess.run")
    def test_partition_info_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        eng = TabletEngine()
        r = eng.ipad_partition_info("DEVICE01")
        self.assertEqual(r["partitions"], [])


# ═══════════════════════════════════════════════════════════════════════════════
#  SAMSUNG TAB FLASH
# ═══════════════════════════════════════════════════════════════════════════════

class TestSamsungTabFlash(unittest.TestCase):
    """Test Samsung Galaxy Tab ODIN flash."""

    def test_samsung_tab_flash_simulated(self):
        eng = TabletEngine()
        r = eng.samsung_tab_flash("DEVICE01", "/tmp/firmware.tar")
        self.assertIsInstance(r, dict)
        # Without heimdall, should be SIMULATED
        if not shutil.which("heimdall"):
            self.assertEqual(r["status"], "SIMULATED")
            self.assertEqual(r["method"], "ODIN")

    @patch("modules.tablets.shutil.which", return_value="/usr/bin/heimdall")
    @patch("modules.tablets.subprocess.run")
    def test_samsung_tab_flash_with_heimdall(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(returncode=0, stdout="Flash complete", stderr="")
        eng = TabletEngine()
        r = eng.samsung_tab_flash("DEVICE01", "/tmp/firmware.tar")
        self.assertEqual(r["method"], "HEIMDALL")
        self.assertTrue(r["success"])

    @patch("modules.tablets.shutil.which", return_value="/usr/bin/heimdall")
    @patch("modules.tablets.subprocess.run")
    def test_samsung_tab_flash_failure(self, mock_run, mock_which):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Error")
        eng = TabletEngine()
        r = eng.samsung_tab_flash("DEVICE01", "/tmp/firmware.tar")
        self.assertFalse(r["success"])


# ═══════════════════════════════════════════════════════════════════════════════
#  UNIVERSAL TABLET FLASH
# ═══════════════════════════════════════════════════════════════════════════════

class TestUniversalTabletFlash(unittest.TestCase):
    """Test flash_tablet routing to correct protocol."""

    def test_flash_apple_routes_to_dfu(self):
        eng = TabletEngine()
        r = eng.flash_tablet("DEVICE01", "/tmp/firmware.ipsw", "Apple")
        self.assertIn("status", r)
        if not shutil.which("idevicerestore"):
            self.assertEqual(r["status"], "SIMULATED")

    def test_flash_samsung_routes_to_odin(self):
        eng = TabletEngine()
        r = eng.flash_tablet("DEVICE01", "/tmp/firmware.tar", "Samsung")
        self.assertIn("status", r)
        if not shutil.which("heimdall"):
            self.assertEqual(r["status"], "SIMULATED")

    def test_flash_xiaomi_routes_to_fastboot(self):
        eng = TabletEngine()
        r = eng.flash_tablet("DEVICE01", "/tmp/firmware.img", "Xiaomi")
        self.assertIsInstance(r, dict)

    def test_flash_unknown_brand_defaults_to_fastboot(self):
        eng = TabletEngine()
        r = eng.flash_tablet("DEVICE01", "/tmp/firmware.img", "UnknownBrand")
        self.assertIsInstance(r, dict)

    def test_flash_with_directory(self):
        """Flash a directory of .img files."""
        eng = TabletEngine()
        with tempfile.TemporaryDirectory() as td:
            # Create fake img files
            for name in ["boot.img", "system.img", "recovery.img"]:
                (Path(td) / name).write_bytes(b"fake")
            r = eng.flash_tablet("DEVICE01", td, "Xiaomi")
            self.assertIn("results", r)

    def test_flash_with_empty_directory(self):
        """Flash an empty directory returns empty results."""
        eng = TabletEngine()
        with tempfile.TemporaryDirectory() as td:
            r = eng.flash_tablet("DEVICE01", td, "Xiaomi")
            self.assertIn("results", r)
            self.assertEqual(len(r["results"]), 0)

    def test_flash_with_nonexistent_file(self):
        """Flash a non-existent single file returns SIMULATED."""
        eng = TabletEngine()
        r = eng.flash_tablet("DEVICE01", "/nonexistent/firmware.img", "Xiaomi")
        self.assertIsInstance(r, dict)


# ═══════════════════════════════════════════════════════════════════════════════
#  TABLET DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════════════════════

class TestTabletDiagnostics(unittest.TestCase):
    """Test tablet diagnostic routines."""

    @patch("modules.tablets.subprocess.run")
    def test_diagnostics_returns_complete(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="model_info", stderr="")
        eng = TabletEngine()
        r = eng.tablet_diagnostics("DEVICE01", "Samsung")
        self.assertEqual(r["status"], "COMPLETED")
        self.assertEqual(r["device_id"], "DEVICE01")
        self.assertEqual(r["brand"], "Samsung")
        self.assertIn("info", r)

    @patch("modules.tablets.subprocess.run")
    def test_diagnostics_includes_model(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="Galaxy Tab S9", stderr="")
        eng = TabletEngine()
        r = eng.tablet_diagnostics("DEVICE01", "Samsung")
        self.assertEqual(r["info"]["model"], "Galaxy Tab S9")

    @patch("modules.tablets.subprocess.run")
    def test_diagnostics_handles_adb_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="device offline")
        eng = TabletEngine()
        r = eng.tablet_diagnostics("DEVICE01", "Samsung")
        self.assertEqual(r["status"], "COMPLETED")
        self.assertEqual(r["info"]["model"], "unknown")


# ═══════════════════════════════════════════════════════════════════════════════
#  UNLOCK BOOTLOADER
# ═══════════════════════════════════════════════════════════════════════════════

class TestTabletUnlockBootloader(unittest.TestCase):
    """Test tablet bootloader unlock via fastboot."""

    @patch("modules.tablets.subprocess.run")
    def test_unlock_returns_dict(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="OKAY", stderr="")
        eng = TabletEngine()
        # Check if method exists
        if hasattr(eng, 'unlock_bootloader'):
            r = eng.unlock_bootloader("DEVICE01")
            self.assertIsInstance(r, dict)
        else:
            # Method may not exist on TabletEngine, skip
            self.skipTest("unlock_bootloader not available on TabletEngine")


# ═══════════════════════════════════════════════════════════════════════════════
#  EDGE CASES
# ═══════════════════════════════════════════════════════════════════════════════

class TestTabletEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def test_empty_device_id(self):
        eng = TabletEngine()
        r = eng.flash_tablet("", "/tmp/firmware.img", "Xiaomi")
        self.assertIsInstance(r, dict)

    def test_empty_brand(self):
        eng = TabletEngine()
        r = eng.flash_tablet("DEVICE01", "/tmp/firmware.img", "")
        self.assertIsInstance(r, dict)

    def test_all_brand_protocols_are_valid(self):
        valid_protocols = {"FASTBOOT", "SAMSUNG_ODIN", "APPLE_DFU", "EDL_QUALCOMM"}
        for brand, mapping in TABLET_BRAND_MAP.items():
            with self.subTest(brand=brand):
                self.assertIn(mapping["protocol"], valid_protocols)

    def test_all_frp_methods_are_valid(self):
        valid_frp = {"FASTBOOT", "ODIN_MODE", "DFU_RESTORE", "EDL_META"}
        for brand, mapping in TABLET_BRAND_MAP.items():
            with self.subTest(brand=brand):
                self.assertIn(mapping["frp"], valid_frp)

    def test_engine_multiple_instances(self):
        e1 = TabletEngine()
        e2 = TabletEngine()
        self.assertIsNot(e1, e2)
        self.assertEqual(type(e1), type(e2))


if __name__ == "__main__":
    unittest.main()
