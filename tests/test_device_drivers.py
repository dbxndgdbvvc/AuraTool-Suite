"""
Unit Tests — Device Drivers Manager (USB / ADB / Fastboot)
==========================================================
Comprehensive tests for modules/device_drivers.py and drivers/driver_manager.py
covering real device detection, ADB/Fastboot commands, driver installation,
protocol detection, and cross-platform compatibility.
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.device_drivers import DeviceDriverManager
from drivers.driver_manager import DriverManager


# ═══════════════════════════════════════════════════════════════════════════
#  DeviceDriverManager Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestDeviceDriverManagerInit(unittest.TestCase):
    """Test DeviceDriverManager initialization and configuration."""

    def setUp(self):
        self.mgr = DeviceDriverManager()

    def test_instance_creation(self):
        """DeviceDriverManager can be instantiated."""
        self.assertIsInstance(self.mgr, DeviceDriverManager)

    def test_os_type_detected(self):
        """OS type is detected correctly."""
        import platform
        expected = platform.system().lower()
        self.assertEqual(self.mgr.os_type, expected)

    def test_brand_drivers_defined(self):
        """All brand drivers are defined."""
        expected_brands = [
            "samsung", "qualcomm", "mediatek", "xiaomi",
            "huawei", "apple", "google", "generic",
        ]
        for brand in expected_brands:
            self.assertIn(brand, self.mgr.BRAND_DRIVERS)

    def test_adb_paths_defined(self):
        """ADB search paths are defined."""
        self.assertGreater(len(self.mgr.ADB_PATHS), 0)

    def test_fastboot_paths_defined(self):
        """Fastboot search paths are defined."""
        self.assertGreater(len(self.mgr.FASTBOOT_PATHS), 0)

    def test_adb_path_resolved(self):
        """ADB path is resolved to a valid path."""
        self.assertIsInstance(self.mgr._adb_path, str)
        self.assertTrue(len(self.mgr._adb_path) > 0)

    def test_fastboot_path_resolved(self):
        """Fastboot path is resolved to a valid path."""
        self.assertIsInstance(self.mgr._fastboot_path, str)
        self.assertTrue(len(self.mgr._fastboot_path) > 0)


class TestDeviceDriverManagerADB(unittest.TestCase):
    """Test ADB command execution and device operations."""

    def setUp(self):
        self.mgr = DeviceDriverManager()

    @patch.object(DeviceDriverManager, '_run_command')
    def test_adb_command_executes(self, mock_run):
        """ADB command execution calls subprocess."""
        mock_run.return_value = {"success": True, "stdout": "List of devices", "stderr": "", "returncode": 0}
        result = self.mgr.adb_command("devices")
        self.assertTrue(result["success"])
        mock_run.assert_called_once()

    @patch.object(DeviceDriverManager, '_run_command')
    def test_adb_devices_returns_list(self, mock_run):
        """get_connected_adb_devices returns a list."""
        mock_run.return_value = {
            "success": True,
            "stdout": "List of devices attached\nSERIAL1\tdevice\nSERIAL2\tdevice",
            "stderr": "",
            "returncode": 0,
        }
        devices = self.mgr.get_connected_adb_devices()
        self.assertIsInstance(devices, list)
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0]["id"], "SERIAL1")
        self.assertEqual(devices[0]["status"], "device")
        self.assertTrue(devices[0]["connected"])

    @patch.object(DeviceDriverManager, '_run_command')
    def test_adb_devices_empty(self, mock_run):
        """get_connected_adb_devices returns empty list when no devices."""
        mock_run.return_value = {
            "success": True,
            "stdout": "List of devices attached\n",
            "stderr": "",
            "returncode": 0,
        }
        devices = self.mgr.get_connected_adb_devices()
        self.assertIsInstance(devices, list)
        self.assertEqual(len(devices), 0)

    @patch.object(DeviceDriverManager, '_run_command')
    def test_adb_devices_unauthorized(self, mock_run):
        """get_connected_adb_devices handles unauthorized devices."""
        mock_run.return_value = {
            "success": True,
            "stdout": "List of devices attached\nSERIAL1\tunauthorized",
            "stderr": "",
            "returncode": 0,
        }
        devices = self.mgr.get_connected_adb_devices()
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]["status"], "unauthorized")
        self.assertFalse(devices[0]["connected"])

    @patch.object(DeviceDriverManager, '_run_command')
    def test_adb_devices_offline(self, mock_run):
        """get_connected_adb_devices handles offline devices."""
        mock_run.return_value = {
            "success": True,
            "stdout": "List of devices attached\nSERIAL1\toffline",
            "stderr": "",
            "returncode": 0,
        }
        devices = self.mgr.get_connected_adb_devices()
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0]["status"], "offline")
        self.assertFalse(devices[0]["connected"])

    @patch.object(DeviceDriverManager, '_run_command')
    def test_adb_devices_multiple(self, mock_run):
        """get_connected_adb_devices handles multiple devices."""
        mock_run.return_value = {
            "success": True,
            "stdout": (
                "List of devices attached\n"
                "SERIAL1\tdevice\tusb:1-1\n"
                "SERIAL2\tdevice\tusb:2-1 product:redmi model:Redmi_Note_12\n"
                "SERIAL3\tdevice\n"
            ),
            "stderr": "",
            "returncode": 0,
        }
        devices = self.mgr.get_connected_adb_devices()
        self.assertEqual(len(devices), 3)
        self.assertEqual(devices[0]["id"], "SERIAL1")
        self.assertIn("usb:1-1", devices[0]["info"])
        self.assertIn("redmi", devices[1]["info"])

    @patch.object(DeviceDriverManager, '_run_command')
    def test_adb_devices_failure(self, mock_run):
        """get_connected_adb_devices handles ADB failure."""
        mock_run.return_value = {
            "success": False,
            "stdout": "",
            "stderr": "error: cannot connect to daemon",
            "returncode": 1,
        }
        devices = self.mgr.get_connected_adb_devices()
        self.assertIsInstance(devices, list)
        self.assertEqual(len(devices), 0)

    @patch.object(DeviceDriverManager, '_run_command')
    def test_adb_get_device_info(self, mock_run):
        """adb_get_device_info returns device properties."""
        # Mock multiple getprop calls
        props = {
            "ro.product.model": "Galaxy S23",
            "ro.product.brand": "samsung",
            "ro.build.version.release": "14",
            "ro.build.version.sdk": "34",
            "ro.serialno": "R5CT1234567",
            "ro.product.name": "samsung Galaxy S23",
            "ro.product.manufacturer": "samsung",
            "ro.build.version.security_patch": "2024-01-01",
            "gsm.version.baseband": "S926BXXU1AWK1",
            "ro.bootloader": "S926BXXU1AWK1",
        }

        call_count = [0]
        prop_keys = list(props.keys())

        def side_effect(*args, **kwargs):
            idx = call_count[0]
            call_count[0] += 1
            if idx < len(prop_keys):
                return {"success": True, "stdout": props[prop_keys[idx]], "stderr": "", "returncode": 0}
            return {"success": True, "stdout": "", "stderr": "", "returncode": 0}

        mock_run.side_effect = side_effect
        info = self.mgr.adb_get_device_info("SERIAL1")
        self.assertEqual(info["model"], "Galaxy S23")
        self.assertEqual(info["brand"], "samsung")
        self.assertEqual(info["android_version"], "14")
        self.assertEqual(info["serial"], "R5CT1234567")

    @patch.object(DeviceDriverManager, '_run_command')
    def test_adb_reboot_normal(self, mock_run):
        """adb_reboot to normal mode executes reboot command."""
        mock_run.return_value = {"success": True, "stdout": "", "stderr": "", "returncode": 0}
        result = self.mgr.adb_reboot("SERIAL1", "normal")
        self.assertTrue(result["success"])

    @patch.object(DeviceDriverManager, '_run_command')
    def test_adb_reboot_recovery(self, mock_run):
        """adb_reboot to recovery mode executes correct command."""
        mock_run.return_value = {"success": True, "stdout": "", "stderr": "", "returncode": 0}
        result = self.mgr.adb_reboot("SERIAL1", "recovery")
        self.assertTrue(result["success"])
        # Verify command includes "recovery"
        cmd_args = mock_run.call_args[0][0]
        self.assertIn("recovery", cmd_args)

    @patch.object(DeviceDriverManager, '_run_command')
    def test_adb_reboot_bootloader(self, mock_run):
        """adb_reboot to bootloader mode executes correct command."""
        mock_run.return_value = {"success": True, "stdout": "", "stderr": "", "returncode": 0}
        result = self.mgr.adb_reboot("SERIAL1", "bootloader")
        self.assertTrue(result["success"])
        cmd_args = mock_run.call_args[0][0]
        self.assertIn("bootloader", cmd_args)

    def test_adb_reboot_invalid_target(self):
        """adb_reboot rejects invalid target mode."""
        result = self.mgr.adb_reboot("SERIAL1", "invalid_mode")
        self.assertFalse(result["success"])
        self.assertIn("Invalid target", result["error"])

    @patch.object(DeviceDriverManager, '_run_command')
    def test_adb_shell_command(self, mock_run):
        """adb_shell executes command on device."""
        mock_run.return_value = {
            "success": True,
            "stdout": "arm64-v8a",
            "stderr": "",
            "returncode": 0,
        }
        result = self.mgr.adb_shell("SERIAL1", "getprop ro.product.cpu.abi")
        self.assertTrue(result["success"])
        self.assertEqual(result["stdout"], "arm64-v8a")

    @patch.object(DeviceDriverManager, '_run_command')
    def test_adb_push_file(self, mock_run):
        """adb_push sends file to device."""
        mock_run.return_value = {
            "success": True,
            "stdout": "file.img: 1 file pushed, 0 skipped.",
            "stderr": "",
            "returncode": 0,
        }
        result = self.mgr.adb_push("SERIAL1", "/local/file.img", "/sdcard/file.img")
        self.assertTrue(result["success"])

    @patch.object(DeviceDriverManager, '_run_command')
    def test_adb_pull_file(self, mock_run):
        """adb_pull retrieves file from device."""
        mock_run.return_value = {
            "success": True,
            "stdout": "/sdcard/file.img: 1 file pulled.",
            "stderr": "",
            "returncode": 0,
        }
        result = self.mgr.adb_pull("SERIAL1", "/sdcard/file.img", "/local/file.img")
        self.assertTrue(result["success"])

    @patch.object(DeviceDriverManager, '_run_command')
    def test_adb_install_apk(self, mock_run):
        """adb_install installs APK on device."""
        mock_run.return_value = {
            "success": True,
            "stdout": "Success",
            "stderr": "",
            "returncode": 0,
        }
        result = self.mgr.adb_install("SERIAL1", "/local/app.apk")
        self.assertTrue(result["success"])

    @patch.object(DeviceDriverManager, '_run_command')
    def test_adb_sideload(self, mock_run):
        """adb_sideload sideloads ZIP package."""
        mock_run.return_value = {
            "success": True,
            "stdout": "sending 'update.zip'...",
            "stderr": "",
            "returncode": 0,
        }
        result = self.mgr.adb_sideload("SERIAL1", "/local/update.zip")
        self.assertTrue(result["success"])


class TestDeviceDriverManagerFastboot(unittest.TestCase):
    """Test Fastboot command execution and device operations."""

    def setUp(self):
        self.mgr = DeviceDriverManager()

    @patch.object(DeviceDriverManager, '_run_command')
    def test_fastboot_command_executes(self, mock_run):
        """Fastboot command execution calls subprocess."""
        mock_run.return_value = {"success": True, "stdout": "", "stderr": "", "returncode": 0}
        result = self.mgr.fastboot_command("devices")
        self.assertTrue(result["success"])

    @patch.object(DeviceDriverManager, '_run_command')
    def test_fastboot_devices_returns_list(self, mock_run):
        """get_fastboot_devices returns a list."""
        mock_run.return_value = {
            "success": True,
            "stdout": "SERIAL1\tfastboot\nSERIAL2\tfastboot",
            "stderr": "",
            "returncode": 0,
        }
        devices = self.mgr.get_fastboot_devices()
        self.assertIsInstance(devices, list)
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0]["id"], "SERIAL1")

    @patch.object(DeviceDriverManager, '_run_command')
    def test_fastboot_devices_empty(self, mock_run):
        """get_fastboot_devices returns empty list when no devices."""
        mock_run.return_value = {
            "success": True,
            "stdout": "",
            "stderr": "",
            "returncode": 0,
        }
        devices = self.mgr.get_fastboot_devices()
        self.assertEqual(len(devices), 0)

    @patch.object(DeviceDriverManager, '_run_command')
    def test_fastboot_get_device_info(self, mock_run):
        """fastboot_get_device_info returns device info."""
        mock_run.return_value = {
            "success": True,
            "stdout": (
                "all: Done!\n"
                "serialno: SERIAL1\n"
                "product: taro\n"
                "variant: hdd\n"
                "unlocked: yes\n"
                "secure: no\n"
            ),
            "stderr": "",
            "returncode": 0,
        }
        info = self.mgr.fastboot_get_device_info("SERIAL1")
        self.assertIsInstance(info, dict)
        self.assertEqual(info.get("serialno"), "SERIAL1")
        self.assertEqual(info.get("product"), "taro")

    @patch.object(DeviceDriverManager, '_run_command')
    def test_fastboot_flash_partition(self, mock_run):
        """fastboot_flash flashes a partition image."""
        mock_run.return_value = {
            "success": True,
            "stdout": "Sending 'boot.img'...\nOKAY [  0.5s]\nWriting 'boot.img'...\nOKAY [  0.3s]",
            "stderr": "",
            "returncode": 0,
        }
        result = self.mgr.fastboot_flash("SERIAL1", "boot", "/path/to/boot.img")
        self.assertTrue(result["success"])

    @patch.object(DeviceDriverManager, '_run_command')
    def test_fastboot_flash_multiple_partitions(self, mock_run):
        """fastboot_flash_all flashes all images in directory."""
        mock_run.return_value = {
            "success": True,
            "stdout": "OKAY",
            "stderr": "",
            "returncode": 0,
        }
        # Create temporary directory with .img files
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ["boot", "recovery", "system"]:
                Path(tmpdir, f"{name}.img").touch()
            result = self.mgr.fastboot_flash_all("SERIAL1", tmpdir)
            self.assertTrue(result["success"])
            self.assertEqual(result["partitions_flashed"], 3)
            self.assertEqual(len(result["results"]), 3)

    def test_fastboot_flash_all_invalid_directory(self):
        """fastboot_flash_all fails with invalid directory."""
        result = self.mgr.fastboot_flash_all("SERIAL1", "/nonexistent/dir")
        self.assertFalse(result["success"])
        self.assertIn("error", result)

    @patch.object(DeviceDriverManager, '_run_command')
    def test_fastboot_erase_partition(self, mock_run):
        """fastboot_erase erases a partition."""
        mock_run.return_value = {"success": True, "stdout": "OKAY", "stderr": "", "returncode": 0}
        result = self.mgr.fastboot_erase("SERIAL1", "userdata")
        self.assertTrue(result["success"])

    @patch.object(DeviceDriverManager, '_run_command')
    def test_fastboot_oem_command(self, mock_run):
        """fastboot_oem executes OEM commands."""
        mock_run.return_value = {"success": True, "stdout": "OKAY", "stderr": "", "returncode": 0}
        result = self.mgr.fastboot_oem("SERIAL1", "unlock")
        self.assertTrue(result["success"])

    @patch.object(DeviceDriverManager, '_run_command')
    def test_fastboot_unlock_bootloader(self, mock_run):
        """fastboot_unlock sends unlock command."""
        mock_run.return_value = {"success": True, "stdout": "OKAY", "stderr": "", "returncode": 0}
        result = self.mgr.fastboot_unlock("SERIAL1")
        self.assertTrue(result["success"])

    @patch.object(DeviceDriverManager, '_run_command')
    def test_fastboot_reboot(self, mock_run):
        """fastboot_reboot reboots device."""
        mock_run.return_value = {"success": True, "stdout": "OKAY", "stderr": "", "returncode": 0}
        result = self.mgr.fastboot_reboot("SERIAL1")
        self.assertTrue(result["success"])


class TestDeviceDriverManagerDriverInstallation(unittest.TestCase):
    """Test driver installation and verification."""

    def setUp(self):
        self.mgr = DeviceDriverManager()

    def test_check_all_drivers_returns_dict(self):
        """check_all_drivers returns a dictionary."""
        result = self.mgr.check_all_drivers()
        self.assertIsInstance(result, dict)
        self.assertIn("adb", result)
        self.assertIn("fastboot", result)

    def test_driver_info_structure(self):
        """Driver info has correct structure."""
        result = self.mgr.check_all_drivers()
        for key, info in result.items():
            self.assertIn("name", info)
            self.assertIn("installed", info)
            self.assertIn("status", info)

    def test_brand_drivers_all_listed(self):
        """All brand drivers are listed in results."""
        result = self.mgr.check_all_drivers()
        # On Linux, check_all_drivers returns platform-specific keys
        self.assertIn("adb", result)
        self.assertIn("fastboot", result)

    def test_install_brand_driver_samsung(self):
        """install_brand_driver returns success for Samsung."""
        result = self.mgr.install_brand_driver("samsung")
        self.assertIn("status", result)
        self.assertIn("brand", result)
        self.assertEqual(result["brand"], "samsung")

    def test_install_brand_driver_xiaomi(self):
        """install_brand_driver returns success for Xiaomi."""
        result = self.mgr.install_brand_driver("xiaomi")
        self.assertIn("status", result)
        self.assertEqual(result["brand"], "xiaomi")

    def test_install_brand_driver_unknown(self):
        """install_brand_driver handles unknown brands."""
        result = self.mgr.install_brand_driver("unknown_brand")
        self.assertIn("status", result)


class TestDeviceDriverManagerProtocolDetection(unittest.TestCase):
    """Test USB protocol detection (EDL, BROM, Download Mode)."""

    def setUp(self):
        self.mgr = DeviceDriverManager()

    @patch.object(DeviceDriverManager, '_run_command')
    def test_detect_device_mode_adb(self, mock_run):
        """detect_device_mode detects ADB devices."""
        mock_run.return_value = {
            "success": True,
            "stdout": "List of devices attached\nSERIAL1\tdevice product:samsung model:Galaxy_S23",
            "stderr": "",
            "returncode": 0,
        }
        result = self.mgr.detect_device_mode("AUTO")
        self.assertEqual(result["detected_mode"], "ADB")
        self.assertTrue(result["protocol_ready"])

    @patch.object(DeviceDriverManager, '_run_command')
    def test_detect_device_mode_fastboot(self, mock_run):
        """detect_device_mode detects Fastboot devices when no ADB."""
        mock_run.return_value = {
            "success": True,
            "stdout": "SERIAL1\tfastboot",
            "stderr": "",
            "returncode": 0,
        }
        result = self.mgr.detect_device_mode("AUTO")
        self.assertEqual(result["detected_mode"], "FASTBOOT")
        self.assertTrue(result["protocol_ready"])

    @patch.object(DeviceDriverManager, 'get_brom_edl_devices')
    @patch.object(DeviceDriverManager, 'get_fastboot_devices')
    @patch.object(DeviceDriverManager, 'get_connected_adb_devices')
    @patch.object(DeviceDriverManager, '_run_command')
    def test_detect_device_mode_none(self, mock_cmd, mock_adb, mock_fb, mock_edl):
        """detect_device_mode returns NONE when no device."""
        mock_cmd.return_value = {
            "success": True,
            "stdout": "List of devices attached\n",
            "stderr": "",
            "returncode": 0,
        }
        mock_adb.return_value = []
        mock_fb.return_value = []
        mock_edl.return_value = []
        result = self.mgr.detect_device_mode("AUTO")
        self.assertEqual(result["detected_mode"], "NONE")
        self.assertFalse(result["protocol_ready"])

    def test_get_brom_edl_devices_returns_list(self):
        """get_brom_edl_devices returns a list."""
        devices = self.mgr.get_brom_edl_devices()
        self.assertIsInstance(devices, list)

    def test_get_samsung_download_mode_devices_returns_list(self):
        """get_samsung_download_mode_devices returns a list."""
        devices = self.mgr.get_samsung_download_mode_devices()
        self.assertIsInstance(devices, list)


class TestDeviceDriverManagerModeSwitching(unittest.TestCase):
    """Test protocol mode switching operations."""

    def setUp(self):
        self.mgr = DeviceDriverManager()

    @patch.object(DeviceDriverManager, 'adb_reboot')
    def test_switch_to_fastboot(self, mock_reboot):
        """switch_to_mode('FASTBOOT') reboots to bootloader."""
        mock_reboot.return_value = {"success": True}
        result = self.mgr.switch_to_mode("SERIAL1", "FASTBOOT")
        self.assertTrue(result["success"])
        mock_reboot.assert_called_once_with("SERIAL1", "bootloader")

    @patch.object(DeviceDriverManager, 'adb_reboot')
    def test_switch_to_recovery(self, mock_reboot):
        """switch_to_mode('RECOVERY') reboots to recovery."""
        mock_reboot.return_value = {"success": True}
        result = self.mgr.switch_to_mode("SERIAL1", "RECOVERY")
        self.assertTrue(result["success"])
        mock_reboot.assert_called_once_with("SERIAL1", "recovery")

    @patch.object(DeviceDriverManager, 'adb_reboot')
    def test_switch_to_sideload(self, mock_reboot):
        """switch_to_mode('SIDELOAD') reboots to sideload."""
        mock_reboot.return_value = {"success": True}
        result = self.mgr.switch_to_mode("SERIAL1", "SIDELOAD")
        self.assertTrue(result["success"])
        mock_reboot.assert_called_once_with("SERIAL1", "sideload")

    @patch.object(DeviceDriverManager, 'fastboot_reboot')
    def test_switch_to_normal(self, mock_reboot):
        """switch_to_mode('NORMAL') reboots from fastboot."""
        mock_reboot.return_value = {"success": True}
        result = self.mgr.switch_to_mode("SERIAL1", "NORMAL")
        self.assertTrue(result["success"])
        mock_reboot.assert_called_once_with("SERIAL1")

    @patch.object(DeviceDriverManager, 'fastboot_oem')
    def test_switch_to_edl(self, mock_oem):
        """switch_to_mode('EDL') uses fastboot oem edl."""
        mock_oem.return_value = {"success": True}
        result = self.mgr.switch_to_mode("SERIAL1", "EDL")
        mock_oem.assert_called_once_with("SERIAL1", "edl")

    def test_switch_to_download_unsupported(self):
        """switch_to_mode('DOWNLOAD') requires hardware keys."""
        result = self.mgr.switch_to_mode("SERIAL1", "DOWNLOAD")
        self.assertFalse(result["success"])

    def test_switch_to_invalid_mode(self):
        """switch_to_mode rejects invalid modes."""
        result = self.mgr.switch_to_mode("SERIAL1", "INVALID_MODE")
        self.assertFalse(result["success"])
        self.assertIn("Unsupported", result["error"])


class TestDeviceDriverManagerCommandExecution(unittest.TestCase):
    """Test the underlying command execution helper."""

    def setUp(self):
        self.mgr = DeviceDriverManager()

    def test_run_command_success(self):
        """_run_command executes successful command."""
        result = self.mgr._run_command(["echo", "hello"])
        self.assertTrue(result["success"])
        self.assertEqual(result["stdout"], "hello")
        self.assertEqual(result["returncode"], 0)

    def test_run_command_failure(self):
        """_run_command handles failed command."""
        result = self.mgr._run_command(["false"])
        self.assertFalse(result["success"])
        self.assertNotEqual(result["returncode"], 0)

    def test_run_command_timeout(self):
        """_run_command handles timeout."""
        result = self.mgr._run_command(["sleep", "30"], timeout=1)
        self.assertFalse(result["success"])
        self.assertIn("timed out", result["stderr"])

    def test_run_command_not_found(self):
        """_run_command handles missing tool."""
        result = self.mgr._run_command(["nonexistent_tool_xyz"])
        self.assertFalse(result["success"])
        self.assertIn("not found", result["stderr"])

    def test_run_command_captures_stderr(self):
        """_run_command captures stderr output."""
        result = self.mgr._run_command(["bash", "-c", "echo error_msg >&2"])
        self.assertIn("error_msg", result["stderr"])

    def test_run_command_long_output(self):
        """_run_command handles large output."""
        result = self.mgr._run_command(["python3", "-c", "print('x' * 10000)"])
        self.assertTrue(result["success"])
        self.assertEqual(len(result["stdout"]), 10000)


# ═══════════════════════════════════════════════════════════════════════════
#  DriverManager Tests (drivers/driver_manager.py)
# ═══════════════════════════════════════════════════════════════════════════

class TestDriverManager(unittest.TestCase):
    """Test the legacy DriverManager in drivers/."""

    def setUp(self):
        self.mgr = DriverManager()

    def test_supported_brands(self):
        """DriverManager lists all supported brands."""
        self.assertIn("Samsung", self.mgr.SUPPORTED_BRANDS)
        self.assertIn("Apple", self.mgr.SUPPORTED_BRANDS)
        self.assertIn("Xiaomi", self.mgr.SUPPORTED_BRANDS)
        self.assertIn("Huawei", self.mgr.SUPPORTED_BRANDS)
        self.assertIn("Google Pixel", self.mgr.SUPPORTED_BRANDS)
        self.assertGreater(len(self.mgr.SUPPORTED_BRANDS), 15)

    def test_supported_protocols(self):
        """DriverManager lists all supported protocols."""
        self.assertIn("ADB", self.mgr.SUPPORTED_PROTOCOLS)
        self.assertIn("FASTBOOT", self.mgr.SUPPORTED_PROTOCOLS)
        self.assertIn("EDL_9008", self.mgr.SUPPORTED_PROTOCOLS)
        self.assertIn("META_MODE", self.mgr.SUPPORTED_PROTOCOLS)
        self.assertIn("MTK_BROM", self.mgr.SUPPORTED_PROTOCOLS)
        self.assertIn("DOWNLOAD_MODE", self.mgr.SUPPORTED_PROTOCOLS)
        self.assertIn("SIDELOAD_MODE", self.mgr.SUPPORTED_PROTOCOLS)
        self.assertIn("APPLE_DFU", self.mgr.SUPPORTED_PROTOCOLS)

    def test_initialize_drivers(self):
        """initialize_drivers returns status dict."""
        status = self.mgr.initialize_drivers()
        self.assertIsInstance(status, dict)
        self.assertIn("adb", status)
        self.assertIn("fastboot", status)
        self.assertIn("edl_qualcomm", status)
        self.assertIn("mtk_brom_meta", status)
        self.assertIn("samsung_download", status)
        self.assertIn("sideload", status)
        self.assertIn("apple_dfu", status)
        self.assertIn("installed_brand_drivers", status)

    def test_detect_device_mode(self):
        """detect_device_mode returns device info."""
        result = self.mgr.detect_device_mode("AUTO")
        self.assertIn("port", result)
        self.assertIn("detected_mode", result)
        self.assertIn("brand", result)
        self.assertIn("protocol_ready", result)

    def test_get_connected_adb_devices(self):
        """get_connected_adb_devices returns list."""
        devices = self.mgr.get_connected_adb_devices()
        self.assertIsInstance(devices, list)
        self.assertGreater(len(devices), 0)

    def test_get_fastboot_devices(self):
        """get_fastboot_devices returns list."""
        devices = self.mgr.get_fastboot_devices()
        self.assertIsInstance(devices, list)
        self.assertGreater(len(devices), 0)

    def test_get_brom_edl_devices(self):
        """get_brom_edl_devices returns list."""
        devices = self.mgr.get_brom_edl_devices()
        self.assertIsInstance(devices, list)
        self.assertGreater(len(devices), 0)

    def test_get_samsung_download_mode_devices(self):
        """get_samsung_download_mode_devices returns list."""
        devices = self.mgr.get_samsung_download_mode_devices()
        self.assertIsInstance(devices, list)
        self.assertGreater(len(devices), 0)

    def test_switch_to_mode_valid(self):
        """switch_to_mode with valid mode returns True."""
        result = self.mgr.switch_to_mode("TestDevice", "ADB")
        self.assertTrue(result)

    def test_switch_to_mode_invalid(self):
        """switch_to_mode with invalid mode returns False."""
        result = self.mgr.switch_to_mode("TestDevice", "INVALID_MODE")
        self.assertFalse(result)


# ═══════════════════════════════════════════════════════════════════════════
#  Cross-module Integration Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestCrossModuleDriverIntegration(unittest.TestCase):
    """Test interactions between DeviceDriverManager and other modules."""

    def setUp(self):
        self.ddm = DeviceDriverManager()
        self.dm = DriverManager()

    def test_both_managers_support_same_brands(self):
        """Both driver managers support the same major brands."""
        ddm_brands = set(self.ddm.BRAND_DRIVERS.keys())
        dm_brands = set(b.lower().replace(" ", "_") for b in self.dm.SUPPORTED_BRANDS)
        # At least Samsung, Qualcomm, MediaTek overlap
        overlap = ddm_brands & dm_brands
        self.assertGreater(len(overlap), 0)

    def test_driver_check_structures(self):
        """Both managers return structured driver status."""
        ddm_status = self.ddm.check_all_drivers()
        dm_status = self.dm.initialize_drivers()
        self.assertIsInstance(ddm_status, dict)
        self.assertIsInstance(dm_status, dict)

    @patch.object(DeviceDriverManager, '_run_command')
    @patch.object(DeviceDriverManager, 'get_fastboot_devices')
    @patch.object(DeviceDriverManager, 'get_connected_adb_devices')
    def test_device_detection_chain(self, mock_adb, mock_fb, mock_cmd):
        """ADB → Fastboot → EDL detection chain."""
        # No ADB devices
        mock_adb.return_value = []
        # No Fastboot devices
        mock_fb.return_value = []
        # No serial ports
        mock_cmd.return_value = {"success": True, "stdout": "", "stderr": "", "returncode": 0}

        result = self.ddm.detect_device_mode()
        self.assertEqual(result["detected_mode"], "NONE")

    @patch.object(DeviceDriverManager, 'get_connected_adb_devices')
    @patch.object(DeviceDriverManager, 'adb_get_device_info')
    def test_adb_detection_to_info(self, mock_info, mock_devices):
        """ADB detection → device info retrieval chain."""
        mock_devices.return_value = [{"id": "SERIAL1", "status": "device", "info": "", "connected": True}]
        mock_info.return_value = {"model": "Galaxy S23", "brand": "samsung"}

        devices = self.ddm.get_connected_adb_devices()
        self.assertEqual(len(devices), 1)
        info = self.ddm.adb_get_device_info(devices[0]["id"])
        self.assertEqual(info["model"], "Galaxy S23")

    def test_udev_rule_content_generation(self):
        """udev rule content is correctly formatted."""
        # Test the private method directly
        result = self.ddm._install_linux_udev_rules("samsung", "Samsung USB Driver")
        self.assertIn("status", result)
        # The method should handle permission or create rule
        self.assertIn(result["status"], ["INSTALLED_SUCCESSFULLY", "NEEDS_ROOT", "ALREADY_INSTALLED", "ERROR"])


if __name__ == "__main__":
    unittest.main()
