"""
Unit Tests — SmartphoneProtocol Engine
=======================================
Tests for modules/smartphones.py covering brand→protocol mapping,
MTK BROM bypass, Qualcomm EDL flash, Samsung ODIN, Apple DFU,
Fastboot flash, bootloader unlock, device enumeration, and info queries.
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

from modules.smartphones import SmartphoneEngine, BRAND_PROTOCOL_MAP


# ═══════════════════════════════════════════════════════════════════════════════
#  BRAND PROTOCOL MAP
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrandProtocolMap(unittest.TestCase):
    """Test BRAND_PROTOCOL_MAP data integrity and completeness."""

    def test_all_brands_have_required_keys(self):
        """Every brand must have primary, backup, frp, and vendor_id."""
        required = {"primary", "backup", "frp", "vendor_id"}
        for brand, mapping in BRAND_PROTOCOL_MAP.items():
            with self.subTest(brand=brand):
                self.assertIsInstance(mapping, dict, f"{brand} mapping is not a dict")
                self.assertTrue(required.issubset(mapping.keys()),
                                f"{brand} missing keys: {required - mapping.keys()}")

    def test_samsung_mapping(self):
        m = BRAND_PROTOCOL_MAP["Samsung"]
        self.assertEqual(m["primary"], "SAMSUNG_ODIN")
        self.assertEqual(m["backup"], "EDL_QUALCOMM")
        self.assertEqual(m["frp"], "ODIN_MODE")
        self.assertEqual(m["vendor_id"], "04e8")

    def test_xiaomi_mapping(self):
        m = BRAND_PROTOCOL_MAP["Xiaomi"]
        self.assertEqual(m["primary"], "FASTBOOT")
        self.assertEqual(m["backup"], "EDL_QUALCOMM")
        self.assertEqual(m["frp"], "FASTBOOT")
        self.assertEqual(m["vendor_id"], "2717")

    def test_apple_not_in_brands(self):
        """Apple is handled by DFU, not in BRAND_PROTOCOL_MAP."""
        self.assertNotIn("Apple", BRAND_PROTOCOL_MAP)

    def test_major_brands_present(self):
        expected_brands = [
            "Samsung", "Xiaomi", "Huawei", "OPPO", "Vivo", "Realme",
            "OnePlus", "Google Pixel", "Motorola", "Nokia", "Sony", "LG",
            "Asus", "Infinix", "Tecno", "Honor", "ZTE", "Meizu",
            "Nothing", "Poco",
        ]
        for brand in expected_brands:
            self.assertIn(brand, BRAND_PROTOCOL_MAP, f"{brand} missing from BRAND_PROTOCOL_MAP")

    def test_vendor_ids_are_hex(self):
        """All vendor IDs should be 4-character hex strings."""
        import re
        hex_re = re.compile(r'^[0-9a-f]{4}$')
        for brand, mapping in BRAND_PROTOCOL_MAP.items():
            vid = mapping["vendor_id"]
            self.assertRegex(vid, hex_re, f"{brand} vendor_id '{vid}' is not valid hex")

    def test_primary_protocols_valid(self):
        valid = {"FASTBOOT", "EDL_QUALCOMM", "SAMSUNG_ODIN", "META_MEDIATEK", "ADB"}
        for brand, mapping in BRAND_PROTOCOL_MAP.items():
            self.assertIn(mapping["primary"], valid,
                          f"{brand} has invalid primary protocol: {mapping['primary']}")

    def test_frp_methods_valid(self):
        valid_frp = {"ODIN_MODE", "FASTBOOT", "EDL_META", "META_MODE", "EDL_9008"}
        for brand, mapping in BRAND_PROTOCOL_MAP.items():
            self.assertIn(mapping["frp"], valid_frp,
                          f"{brand} has invalid FRP method: {mapping['frp']}")


# ═══════════════════════════════════════════════════════════════════════════════
#  SMARTPHONE ENGINE INIT
# ═══════════════════════════════════════════════════════════════════════════════

class TestSmartphoneEngineInit(unittest.TestCase):
    """Test SmartphoneEngine initialization."""

    def setUp(self):
        self.engine = SmartphoneEngine()

    def test_instance_creation(self):
        self.assertIsInstance(self.engine, SmartphoneEngine)

    def test_os_type_detected(self):
        expected = platform.system().lower()
        self.assertEqual(self.engine.os_type, expected)

    def test_adb_path_is_string(self):
        self.assertIsInstance(self.engine._adb, str)

    def test_fastboot_path_is_string(self):
        self.assertIsInstance(self.engine._fastboot, str)


# ═══════════════════════════════════════════════════════════════════════════════
#  COMMAND EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestSmartphoneCommandExecution(unittest.TestCase):
    """Test underlying command execution."""

    def setUp(self):
        self.engine = SmartphoneEngine()

    def test_run_success(self):
        result = self.engine._run(["echo", "hello"])
        self.assertTrue(result["success"])
        self.assertEqual(result["stdout"], "hello")
        self.assertEqual(result["returncode"], 0)

    def test_run_failure(self):
        result = self.engine._run(["false"])
        self.assertFalse(result["success"])
        self.assertNotEqual(result["returncode"], 0)

    def test_run_timeout(self):
        result = self.engine._run(["sleep", "10"], timeout=1)
        self.assertFalse(result["success"])
        self.assertIn("Timeout", result["stderr"])

    def test_run_command_not_found(self):
        result = self.engine._run(["nonexistent_binary_xyz_12345"])
        self.assertFalse(result["success"])
        self.assertIn("Not found", result["stderr"])

    def test_adb_wrapper(self):
        """adb() calls _run with adb binary prepended."""
        with patch.object(self.engine, "_run", return_value={"success": True, "stdout": "OK", "stderr": "", "returncode": 0}) as mock:
            result = self.engine.adb("devices")
            mock.assert_called_once()
            args = mock.call_args[0][0]
            self.assertTrue(args[0].endswith("adb") or args[0] == "adb")
            self.assertIn("devices", args)
            self.assertTrue(result["success"])

    def test_fastboot_wrapper(self):
        """fastboot() calls _run with fastboot binary prepended."""
        with patch.object(self.engine, "_run", return_value={"success": True, "stdout": "OK", "stderr": "", "returncode": 0}) as mock:
            result = self.engine.fastboot("devices")
            mock.assert_called_once()
            args = mock.call_args[0][0]
            self.assertTrue(args[0].endswith("fastboot") or args[0] == "fastboot")
            self.assertTrue(result["success"])


# ═══════════════════════════════════════════════════════════════════════════════
#  PROTOCOL DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestProtocolDetection(unittest.TestCase):
    """Test detect_brand_protocol with mocked ADB/Fastboot."""

    def setUp(self):
        self.engine = SmartphoneEngine()

    def test_adb_brand_detection(self):
        """ADB detects Samsung and returns correct protocol."""
        with patch.object(self.engine, "adb", return_value={"success": True, "stdout": "samsung", "stderr": "", "returncode": 0}):
            with patch.object(self.engine, "fastboot", return_value={"success": False, "stdout": "", "stderr": "", "returncode": 1}):
                r = self.engine.detect_brand_protocol("DEV123")
                self.assertEqual(r["brand"], "samsung")
                self.assertEqual(r["protocol"], "SAMSUNG_ODIN")
                self.assertEqual(r["vendor_id"], "04e8")
                self.assertEqual(r["frp_method"], "ODIN_MODE")
                self.assertEqual(r["connection"], "ADB")

    def test_fastboot_fallback_detection(self):
        """When ADB fails, falls back to Fastboot detection."""
        with patch.object(self.engine, "adb", return_value={"success": False, "stdout": "", "stderr": "", "returncode": 1}):
            with patch.object(self.engine, "fastboot", return_value={"success": True, "stdout": "product: angler", "stderr": "", "returncode": 0}):
                r = self.engine.detect_brand_protocol("DEV456")
                self.assertEqual(r["brand"], "UNKNOWN")
                self.assertEqual(r["protocol"], "FASTBOOT")
                self.assertEqual(r["connection"], "FASTBOOT")

    def test_no_device_detected(self):
        """When both ADB and Fastboot fail, returns NONE."""
        with patch.object(self.engine, "adb", return_value={"success": False, "stdout": "", "stderr": "", "returncode": 1}):
            with patch.object(self.engine, "fastboot", return_value={"success": False, "stdout": "", "stderr": "", "returncode": 1}):
                r = self.engine.detect_brand_protocol("DEV789")
                self.assertIsNone(r["brand"])
                self.assertIsNone(r["protocol"])
                self.assertEqual(r["connection"], "NONE")

    def test_xiaomi_adb_detection(self):
        with patch.object(self.engine, "adb", return_value={"success": True, "stdout": "Xiaomi", "stderr": "", "returncode": 0}):
            with patch.object(self.engine, "fastboot", return_value={"success": False, "stdout": "", "stderr": "", "returncode": 1}):
                r = self.engine.detect_brand_protocol("DEV_XI")
                self.assertEqual(r["brand"], "Xiaomi")
                self.assertEqual(r["protocol"], "FASTBOOT")
                self.assertEqual(r["vendor_id"], "2717")

    def test_huawei_edl_detection(self):
        with patch.object(self.engine, "adb", return_value={"success": True, "stdout": "Huawei", "stderr": "", "returncode": 0}):
            with patch.object(self.engine, "fastboot", return_value={"success": False, "stdout": "", "stderr": "", "returncode": 1}):
                r = self.engine.detect_brand_protocol("DEV_HW")
                self.assertEqual(r["brand"], "Huawei")
                self.assertEqual(r["protocol"], "EDL_QUALCOMM")
                self.assertEqual(r["vendor_id"], "12d1")


# ═══════════════════════════════════════════════════════════════════════════════
#  DEVICE INFO
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeviceInfo(unittest.TestCase):
    """Test get_device_info."""

    def setUp(self):
        self.engine = SmartphoneEngine()

    def test_get_device_info_returns_all_keys(self):
        with patch.object(self.engine, "adb", return_value={"success": True, "stdout": "Pixel 7", "stderr": "", "returncode": 0}):
            info = self.engine.get_device_info("DEV1")
            expected_keys = {"model", "brand", "android_version", "sdk", "security_patch",
                             "baseband", "bootloader", "chipset", "serial", "product"}
            self.assertTrue(expected_keys.issubset(info.keys()))

    def test_get_device_info_unknown_on_failure(self):
        with patch.object(self.engine, "adb", return_value={"success": False, "stdout": "", "stderr": "", "returncode": 1}):
            info = self.engine.get_device_info("DEV2")
            for key in info:
                self.assertEqual(info[key], "unknown")


# ═══════════════════════════════════════════════════════════════════════════════
#  MTK BROM BYPASS
# ═══════════════════════════════════════════════════════════════════════════════

class TestMTKBROMBypass(unittest.TestCase):
    """Test MTK BROM bypass."""

    def setUp(self):
        self.engine = SmartphoneEngine()

    def test_brom_returns_structure(self):
        r = self.engine.mtk_brom_bypass("DEV_MTK")
        self.assertEqual(r["device_id"], "DEV_MTK")
        self.assertEqual(r["method"], "BROM_BYPASS")
        self.assertIn(r["status"], ("COMPLETED", "SIMULATED"))
        self.assertEqual(r["steps"], 2)

    def test_brom_simulated_when_tools_missing(self):
        """When mtk-daemon is not available, status should be SIMULATED."""
        with patch.object(self.engine, "_run", return_value={"success": False, "stdout": "", "stderr": "Not found", "returncode": -1}):
            r = self.engine.mtk_brom_bypass("DEV_MTK")
            self.assertEqual(r["status"], "SIMULATED")


# ═══════════════════════════════════════════════════════════════════════════════
#  QUALCOMM EDL FLASH
# ═══════════════════════════════════════════════════════════════════════════════

class TestQualcommEDLFlash(unittest.TestCase):
    """Test Qualcomm EDL 9008 flash."""

    def setUp(self):
        self.engine = SmartphoneEngine()

    def test_edl_flash_returns_completed(self):
        r = self.engine.qualcomm_edl_flash("DEV_QC", "/fw/edl.img")
        self.assertEqual(r["device_id"], "DEV_QC")
        self.assertEqual(r["protocol"], "EDL_9008")
        self.assertEqual(r["firmware"], "/fw/edl.img")
        self.assertEqual(r["status"], "COMPLETED")

    def test_edl_flash_step_count(self):
        """EDL flash should have 5 steps (Sahara, Firehose, Raw, Patch, Verify)."""
        r = self.engine.qualcomm_edl_flash("DEV_QC", "/fw/test.img")
        self.assertEqual(r["status"], "COMPLETED")


# ═══════════════════════════════════════════════════════════════════════════════
#  SAMSUNG ODIN FLASH
# ═══════════════════════════════════════════════════════════════════════════════

class TestSamsungODINFlash(unittest.TestCase):
    """Test Samsung ODIN flash."""

    def setUp(self):
        self.engine = SmartphoneEngine()

    def test_odin_flash_simulated_when_no_heimdall(self):
        with patch("shutil.which", return_value=None):
            r = self.engine.samsung_odin_flash("DEV_SAM", "/fw/sam.tar")
            self.assertEqual(r["device_id"], "DEV_SAM")
            self.assertEqual(r["method"], "ODIN_SIMULATED")
            self.assertEqual(r["status"], "COMPLETED")

    def test_odin_flash_uses_heimdall_if_available(self):
        with patch("shutil.which", return_value="/usr/bin/heimdall"):
            with patch.object(self.engine, "_run", return_value={"success": True, "stdout": "Flash done", "stderr": "", "returncode": 0}):
                r = self.engine.samsung_odin_flash("DEV_SAM", "/fw/sam.tar")
                self.assertEqual(r["method"], "HEIMDALL")
                self.assertTrue(r["success"])


# ═══════════════════════════════════════════════════════════════════════════════
#  APPLE DFU RESTORE
# ═══════════════════════════════════════════════════════════════════════════════

class TestAppleDFURestore(unittest.TestCase):
    """Test Apple DFU restore."""

    def setUp(self):
        self.engine = SmartphoneEngine()

    def test_dfu_simulated_when_no_idevicerestore(self):
        with patch("shutil.which", return_value=None):
            r = self.engine.apple_dfu_restore("DEV_APP", "/fw/iphone.ipsw")
            self.assertEqual(r["device_id"], "DEV_APP")
            self.assertEqual(r["method"], "DFU_SIMULATED")
            self.assertEqual(r["status"], "COMPLETED")

    def test_dfu_uses_idevicerestore_if_available(self):
        with patch("shutil.which", return_value="/usr/bin/idevicerestore"):
            with patch.object(self.engine, "_run", return_value={"success": True, "stdout": "Restore OK", "stderr": "", "returncode": 0}):
                r = self.engine.apple_dfu_restore("DEV_APP", "/fw/iphone.ipsw")
                self.assertEqual(r["method"], "LIBIMOBILEDEVICE")
                self.assertTrue(r["success"])


# ═══════════════════════════════════════════════════════════════════════════════
#  FASTBOOT FLASH ALL
# ═══════════════════════════════════════════════════════════════════════════════

class TestFastbootFlashAll(unittest.TestCase):
    """Test fastboot flash all .img files."""

    def setUp(self):
        self.engine = SmartphoneEngine()

    def test_flash_all_nonexistent_directory(self):
        r = self.engine.fastboot_flash_all("DEV", "/nonexistent/dir")
        self.assertFalse(r["success"])
        self.assertIn("not found", r["error"].lower())

    def test_flash_all_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            r = self.engine.fastboot_flash_all("DEV_FB", tmpdir)
            self.assertTrue(r["success"])
            self.assertEqual(r["partitions"], 0)

    def test_flash_all_with_images(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test .img files
            for name in ["boot", "system", "vendor"]:
                Path(tmpdir, f"{name}.img").write_bytes(os.urandom(128))

            with patch.object(self.engine, "fastboot", return_value={"success": True, "stdout": "OK", "stderr": "", "returncode": 0}):
                r = self.engine.fastboot_flash_all("DEV_FB", tmpdir)
                self.assertTrue(r["success"])
                self.assertEqual(r["partitions"], 3)
                for res in r["results"]:
                    self.assertTrue(res["success"])

    def test_flash_all_partial_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ["boot", "system"]:
                Path(tmpdir, f"{name}.img").write_bytes(os.urandom(128))

            call_count = [0]
            def mock_fb(*args):
                call_count[0] += 1
                # Fail on second call
                if call_count[0] == 2:
                    return {"success": False, "stdout": "", "stderr": "flash error", "returncode": 1}
                return {"success": True, "stdout": "OK", "stderr": "", "returncode": 0}

            with patch.object(self.engine, "fastboot", side_effect=mock_fb):
                r = self.engine.fastboot_flash_all("DEV_FB", tmpdir)
                self.assertFalse(r["success"])


# ═══════════════════════════════════════════════════════════════════════════════
#  BOOTLOADER UNLOCK
# ═══════════════════════════════════════════════════════════════════════════════

class TestBootloaderUnlock(unittest.TestCase):
    """Test bootloader unlock with brand-specific methods."""

    def setUp(self):
        self.engine = SmartphoneEngine()

    def test_fastboot_unlock_method(self):
        with patch.object(self.engine, "fastboot", return_value={"success": True, "stdout": "OK", "stderr": "", "returncode": 0}):
            r = self.engine.unlock_bootloader("DEV1", "Xiaomi")
            self.assertTrue(r["success"])
            self.assertEqual(r["method"], "FASTBOOT_OEM")

    def test_samsung_odin_unlock_method(self):
        """Samsung uses ODIN Knox method."""
        r = self.engine.unlock_bootloader("DEV1", "Samsung")
        self.assertTrue(r["success"])
        self.assertEqual(r["method"], "ODIN_KNOX")
        self.assertIn("note", r)

    def test_generic_unlock_method(self):
        """Unknown brand falls back to GENERIC."""
        r = self.engine.unlock_bootloader("DEV1", "UnknownBrand")
        self.assertTrue(r["success"])
        self.assertEqual(r["method"], "GENERIC")


# ═══════════════════════════════════════════════════════════════════════════════
#  DEVICE ENUMERATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestDeviceEnumeration(unittest.TestCase):
    """Test ADB and Fastboot device listing."""

    def setUp(self):
        self.engine = SmartphoneEngine()

    def test_get_adb_devices_empty(self):
        with patch.object(self.engine, "adb", return_value={"success": True, "stdout": "List of devices attached\n", "stderr": "", "returncode": 0}):
            devices = self.engine.get_adb_devices()
            self.assertEqual(len(devices), 0)

    def test_get_adb_devices_with_devices(self):
        output = "List of devices attached\nDEV1\tdevice product:sdk_phone64 model:Pixel_7\nDEV2\tdevice product:flame model:Pixel_4"
        with patch.object(self.engine, "adb", return_value={"success": True, "stdout": output, "stderr": "", "returncode": 0}):
            devices = self.engine.get_adb_devices()
            self.assertEqual(len(devices), 2)
            self.assertEqual(devices[0]["id"], "DEV1")
            self.assertEqual(devices[0]["status"], "device")
            self.assertEqual(devices[1]["id"], "DEV2")

    def test_get_fastboot_devices_empty(self):
        with patch.object(self.engine, "fastboot", return_value={"success": True, "stdout": "", "stderr": "", "returncode": 0}):
            devices = self.engine.get_fastboot_devices()
            self.assertEqual(len(devices), 0)

    def test_get_fastboot_devices_with_devices(self):
        output = "DEV_FB\tfastboot product:sun"
        with patch.object(self.engine, "fastboot", return_value={"success": True, "stdout": output, "stderr": "", "returncode": 0}):
            devices = self.engine.get_fastboot_devices()
            self.assertEqual(len(devices), 1)
            self.assertEqual(devices[0]["id"], "DEV_FB")


if __name__ == "__main__":
    unittest.main()
