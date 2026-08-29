"""
Unit Tests — Flashing Engine (USB / ADB / Fastboot)
====================================================
Comprehensive tests for modules/flashing_engine.py covering firmware
verification, ADB/Fastboot flash operations, unbrick, format, storage
health diagnostics, and bootloader management.
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.flashing_engine import FlashingEngine


class TestFlashingEngineInit(unittest.TestCase):
    """Test FlashingEngine initialization."""

    def setUp(self):
        self.engine = FlashingEngine()

    def test_instance_creation(self):
        """FlashingEngine can be instantiated."""
        self.assertIsInstance(self.engine, FlashingEngine)

    def test_os_type_detected(self):
        """OS type is detected."""
        import platform
        expected = platform.system().lower()
        self.assertEqual(self.engine.os_type, expected)

    def test_supported_formats_defined(self):
        """All firmware formats are defined."""
        self.assertIn("OTA_PAYLOAD_BIN", self.engine.SUPPORTED_FORMATS)
        self.assertIn("SPARSE_SUPER_IMG", self.engine.SUPPORTED_FORMATS)
        self.assertIn("SAMSUNG_ODIN_TAR", self.engine.SUPPORTED_FORMATS)
        self.assertIn("MEDIATEK_SCATTER", self.engine.SUPPORTED_FORMATS)
        self.assertIn("QUALCOMM_FIREHOSE", self.engine.SUPPORTED_FORMATS)
        self.assertIn("APPLE_IPSW", self.engine.SUPPORTED_FORMATS)

    def test_common_partitions_defined(self):
        """Common partitions list is defined."""
        self.assertIn("boot", self.engine.COMMON_PARTITIONS)
        self.assertIn("system", self.engine.COMMON_PARTITIONS)
        self.assertIn("recovery", self.engine.COMMON_PARTITIONS)
        self.assertIn("userdata", self.engine.COMMON_PARTITIONS)

    def test_adb_path_resolved(self):
        """ADB path is resolved."""
        self.assertIsInstance(self.engine._adb_path, str)

    def test_fastboot_path_resolved(self):
        """Fastboot path is resolved."""
        self.assertIsInstance(self.engine._fastboot_path, str)


class TestFlashingEngineCommandExecution(unittest.TestCase):
    """Test underlying command execution."""

    def setUp(self):
        self.engine = FlashingEngine()

    def test_run_cmd_success(self):
        """_run_cmd executes successful command."""
        result = self.engine._run_cmd(["echo", "hello"])
        self.assertTrue(result["success"])
        self.assertEqual(result["stdout"], "hello")
        self.assertEqual(result["returncode"], 0)

    def test_run_cmd_failure(self):
        """_run_cmd handles failed command."""
        result = self.engine._run_cmd(["false"])
        self.assertFalse(result["success"])
        self.assertNotEqual(result["returncode"], 0)

    def test_run_cmd_timeout(self):
        """_run_cmd handles timeout."""
        result = self.engine._run_cmd(["sleep", "30"], timeout=1)
        self.assertFalse(result["success"])
        self.assertIn("timed out", result["stderr"])

    def test_run_cmd_not_found(self):
        """_run_cmd handles missing tool."""
        result = self.engine._run_cmd(["nonexistent_tool_xyz"])
        self.assertFalse(result["success"])

    def test_run_cmd_captures_stderr(self):
        """_run_cmd captures stderr."""
        result = self.engine._run_cmd(["bash", "-c", "echo error_msg >&2"])
        self.assertIn("error_msg", result["stderr"])

    @patch.object(FlashingEngine, '_run_cmd')
    def test_adb_calls_run_cmd(self, mock_cmd):
        """adb() helper calls _run_cmd with correct args."""
        mock_cmd.return_value = {"success": True, "stdout": "", "stderr": "", "returncode": 0}
        result = self.engine.adb("devices")
        self.assertTrue(result["success"])
        mock_cmd.assert_called_once()

    @patch.object(FlashingEngine, '_run_cmd')
    def test_fastboot_calls_run_cmd(self, mock_cmd):
        """fastboot() helper calls _run_cmd with correct args."""
        mock_cmd.return_value = {"success": True, "stdout": "", "stderr": "", "returncode": 0}
        result = self.engine.fastboot("devices")
        self.assertTrue(result["success"])
        mock_cmd.assert_called_once()


class TestFirmwareVerification(unittest.TestCase):
    """Test firmware image verification."""

    def setUp(self):
        self.engine = FlashingEngine()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_verify_nonexistent_file(self):
        """Verify nonexistent firmware returns invalid."""
        result = self.engine.verify_firmware_image("/nonexistent/file.bin")
        self.assertFalse(result["valid"])
        self.assertEqual(result["format"], "UNKNOWN")

    def test_verify_empty_path(self):
        """Verify empty path returns invalid."""
        result = self.engine.verify_firmware_image("")
        self.assertFalse(result["valid"])

    def test_verify_ota_payload(self):
        """Verify payload.bin format detection."""
        fw_path = os.path.join(self.tmpdir, "payload.bin")
        Path(fw_path).touch()
        result = self.engine.verify_firmware_image(fw_path)
        self.assertTrue(result["valid"])
        self.assertEqual(result["format"], "OTA_PAYLOAD_BIN")

    def test_verify_super_img(self):
        """Verify super.img format detection."""
        fw_path = os.path.join(self.tmpdir, "super.img")
        Path(fw_path).touch()
        result = self.engine.verify_firmware_image(fw_path)
        self.assertTrue(result["valid"])
        self.assertEqual(result["format"], "SPARSE_SUPER_IMG")

    def test_verify_samsung_tar(self):
        """Verify Samsung .tar format detection."""
        fw_path = os.path.join(self.tmpdir, "firmware.tar")
        Path(fw_path).touch()
        result = self.engine.verify_firmware_image(fw_path)
        self.assertTrue(result["valid"])
        self.assertEqual(result["format"], "SAMSUNG_ODIN_TAR")

    def test_verify_samsung_md5(self):
        """Verify Samsung .md5 format detection."""
        fw_path = os.path.join(self.tmpdir, "firmware.md5")
        Path(fw_path).touch()
        result = self.engine.verify_firmware_image(fw_path)
        self.assertTrue(result["valid"])
        self.assertEqual(result["format"], "SAMSUNG_ODIN_TAR")

    def test_verify_mtk_scatter(self):
        """Verify MediaTek scatter.txt detection."""
        fw_path = os.path.join(self.tmpdir, "MT6785_Android_scatter.txt")
        Path(fw_path).touch()
        result = self.engine.verify_firmware_image(fw_path)
        self.assertTrue(result["valid"])
        self.assertEqual(result["format"], "MEDIATEK_SCATTER")

    def test_verify_qualcomm_bin(self):
        """Verify Qualcomm .bin format detection."""
        fw_path = os.path.join(self.tmpdir, "prog_firehose_ddr.bin")
        Path(fw_path).touch()
        result = self.engine.verify_firmware_image(fw_path)
        self.assertTrue(result["valid"])
        self.assertEqual(result["format"], "QUALCOMM_FIREHOSE")

    def test_verify_qualcomm_xml(self):
        """Verify Qualcomm .xml format detection."""
        fw_path = os.path.join(self.tmpdir, "rawprogram_unsparse.xml")
        Path(fw_path).touch()
        result = self.engine.verify_firmware_image(fw_path)
        self.assertTrue(result["valid"])
        self.assertEqual(result["format"], "QUALCOMM_FIREHOSE")

    def test_verify_apple_ipsw(self):
        """Verify Apple .ipsw format detection."""
        fw_path = os.path.join(self.tmpdir, "iPhone_15_17.6.ipsw")
        Path(fw_path).touch()
        result = self.engine.verify_firmware_image(fw_path)
        self.assertTrue(result["valid"])
        self.assertEqual(result["format"], "APPLE_IPSW")

    def test_verify_generic_raw(self):
        """Verify generic raw format detection."""
        fw_path = os.path.join(self.tmpdir, "firmware.img")
        Path(fw_path).touch()
        result = self.engine.verify_firmware_image(fw_path)
        self.assertTrue(result["valid"])
        self.assertEqual(result["format"], "GENERIC_RAW")


class TestPayloadExtraction(unittest.TestCase):
    """Test payload.bin extraction."""

    def setUp(self):
        self.engine = FlashingEngine()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_extract_creates_output_dir(self):
        """Extraction creates output directory."""
        output_dir = os.path.join(self.tmpdir, "extracted")
        result = self.engine.extract_payload_bin("/fake/payload.bin", output_dir)
        self.assertIsInstance(result, list)
        self.assertTrue(os.path.isdir(output_dir))

    def test_extract_returns_partitions(self):
        """Extraction returns list of partition names."""
        output_dir = os.path.join(self.tmpdir, "extracted")
        result = self.engine.extract_payload_bin("/fake/payload.bin", output_dir)
        self.assertIn("boot.img", result)
        self.assertIn("system.img", result)
        self.assertIn("recovery.img", result)
        self.assertIn("super.img", result)

    def test_extract_with_callback(self):
        """Extraction calls callback with progress."""
        output_dir = os.path.join(self.tmpdir, "extracted")
        callback = MagicMock()
        result = self.engine.extract_payload_bin("/fake/payload.bin", output_dir, callback=callback)
        self.assertTrue(callback.called)
        # Callback should be called at least once per partition
        self.assertGreaterEqual(callback.call_count, len(result))


class TestFlashOperations(unittest.TestCase):
    """Test firmware flashing operations."""

    def setUp(self):
        self.engine = FlashingEngine()

    @patch.object(FlashingEngine, '_flash_via_fastboot')
    def test_flash_firmware_fastboot_mode(self, mock_flash):
        """flash_firmware with FASTBOOT mode calls _flash_via_fastboot."""
        mock_flash.return_value = True
        result = self.engine.flash_firmware("SERIAL1", "/firmware/", "FASTBOOT")
        self.assertTrue(result)
        mock_flash.assert_called_once()

    @patch.object(FlashingEngine, '_flash_via_adb')
    def test_flash_firmware_adb_mode(self, mock_flash):
        """flash_firmware with ADB mode calls _flash_via_adb."""
        mock_flash.return_value = True
        result = self.engine.flash_firmware("SERIAL1", "/firmware/update.zip", "ADB")
        self.assertTrue(result)
        mock_flash.assert_called_once()

    @patch.object(FlashingEngine, '_flash_generic')
    def test_flash_firmware_generic_mode(self, mock_flash):
        """flash_firmware with unknown mode calls _flash_generic."""
        mock_flash.return_value = True
        result = self.engine.flash_firmware("SERIAL1", "/firmware/", "ODIN")
        self.assertTrue(result)
        mock_flash.assert_called_once()

    @patch.object(FlashingEngine, 'fastboot')
    def test_flash_via_fastboot_single_image(self, mock_fb):
        """_flash_via_fastboot flashes single .img file."""
        mock_fb.return_value = {"success": True, "stdout": "OKAY", "stderr": "", "returncode": 0}
        with tempfile.NamedTemporaryFile(suffix=".img", delete=False) as f:
            fw_path = f.name
        try:
            result = self.engine._flash_via_fastboot("SERIAL1", fw_path)
            self.assertTrue(result)
        finally:
            os.unlink(fw_path)

    @patch.object(FlashingEngine, 'fastboot')
    def test_flash_via_fastboot_directory(self, mock_fb):
        """_flash_via_fastboot flashes all images in directory."""
        mock_fb.return_value = {"success": True, "stdout": "OKAY", "stderr": "", "returncode": 0}
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ["boot", "recovery", "system"]:
                Path(tmpdir, f"{name}.img").touch()
            result = self.engine._flash_via_fastboot("SERIAL1", tmpdir)
            self.assertTrue(result)
            self.assertEqual(mock_fb.call_count, 3)

    @patch.object(FlashingEngine, 'fastboot')
    def test_flash_via_fastboot_directory_partial_failure(self, mock_fb):
        """_flash_via_fastboot handles partial failures."""
        def side_effect(*args):
            if "boot" in args:
                return {"success": True, "stdout": "OKAY", "stderr": "", "returncode": 0}
            return {"success": False, "stdout": "", "stderr": "FAILED", "returncode": 1}

        mock_fb.side_effect = side_effect
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "boot.img").touch()
            Path(tmpdir, "system.img").touch()
            result = self.engine._flash_via_fastboot("SERIAL1", tmpdir)
            self.assertFalse(result)

    @patch.object(FlashingEngine, 'fastboot')
    def test_flash_via_fastboot_url_path(self, mock_fb):
        """_flash_via_fastboot simulates flash for URL paths."""
        mock_fb.return_value = {"success": True, "stdout": "OKAY", "stderr": "", "returncode": 0}
        result = self.engine._flash_via_fastboot("SERIAL1", "https://example.com/firmware.bin")
        self.assertTrue(result)

    @patch.object(FlashingEngine, 'adb')
    def test_flash_via_adb_sideload(self, mock_adb):
        """_flash_via_adb uses adb sideload."""
        mock_adb.return_value = {"success": True, "stdout": "sending", "stderr": "", "returncode": 0}
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as f:
            fw_path = f.name
        try:
            result = self.engine._flash_via_adb("SERIAL1", fw_path)
            self.assertTrue(result)
        finally:
            os.unlink(fw_path)

    def test_flash_via_adb_nonexistent_file(self):
        """_flash_via_adb fails with nonexistent file."""
        result = self.engine._flash_via_adb("SERIAL1", "/nonexistent/firmware.zip")
        self.assertFalse(result)

    @patch.object(FlashingEngine, 'fastboot')
    def test_flash_generic(self, mock_fb):
        """_flash_generic simulates flash with progress."""
        mock_fb.return_value = {"success": True, "stdout": "OKAY", "stderr": "", "returncode": 0}
        callback = MagicMock()
        result = self.engine._flash_generic("SERIAL1", "/firmware/", callback=callback)
        self.assertTrue(result)
        self.assertTrue(callback.called)


class TestSinglePartitionFlash(unittest.TestCase):
    """Test single partition flash operations."""

    def setUp(self):
        self.engine = FlashingEngine()

    @patch.object(FlashingEngine, 'fastboot')
    def test_flash_single_partition_fastboot(self, mock_fb):
        """flash_single_partition via Fastboot."""
        mock_fb.return_value = {"success": True, "stdout": "OKAY", "stderr": "", "returncode": 0}
        with tempfile.NamedTemporaryFile(suffix=".img", delete=False) as f:
            img_path = f.name
        try:
            result = self.engine.flash_single_partition("SERIAL1", "boot", img_path, "FASTBOOT")
            self.assertTrue(result["success"])
            self.assertEqual(result["partition"], "boot")
        finally:
            os.unlink(img_path)

    @patch.object(FlashingEngine, 'adb')
    def test_flash_single_partition_adb(self, mock_adb):
        """flash_single_partition via ADB push."""
        mock_adb.return_value = {"success": True, "stdout": "pushed", "stderr": "", "returncode": 0}
        result = self.engine.flash_single_partition("SERIAL1", "boot", "/path/boot.img", "ADB")
        self.assertTrue(result["success"])

    def test_flash_single_partition_generic(self):
        """flash_single_partition with generic mode simulates."""
        result = self.engine.flash_single_partition("SERIAL1", "boot", "/path/boot.img", "ODIN")
        self.assertTrue(result["success"])


class TestUnbrick(unittest.TestCase):
    """Test device unbrick operations."""

    def setUp(self):
        self.engine = FlashingEngine()

    def test_unbrick_returns_success(self):
        """unbrick_device returns success status."""
        result = self.engine.unbrick_device("SERIAL1", "Samsung", "EDL_9008")
        self.assertEqual(result["status"], "UNBRICK_SUCCESSFUL")
        self.assertTrue(result["bootloader_restored"])

    def test_unbrick_default_brand(self):
        """unbrick_device works with default brand."""
        result = self.engine.unbrick_device("SERIAL1")
        self.assertEqual(result["brand"], "GENERIC")

    def test_unbrick_custom_brand(self):
        """unbrick_device works with custom brand."""
        result = self.engine.unbrick_device("SERIAL1", "Xiaomi")
        self.assertEqual(result["brand"], "Xiaomi")


class TestFormatOperations(unittest.TestCase):
    """Test device format/wipe operations."""

    def setUp(self):
        self.engine = FlashingEngine()

    @patch.object(FlashingEngine, 'fastboot')
    def test_perform_full_format(self, mock_fb):
        """perform_full_format erases userdata and cache."""
        mock_fb.return_value = {"success": True, "stdout": "OKAY", "stderr": "", "returncode": 0}
        result = self.engine.perform_full_format("SERIAL1")
        self.assertTrue(result)
        # Should call fastboot erase at least twice (userdata + cache + persistent)
        self.assertGreaterEqual(mock_fb.call_count, 2)

    @patch.object(FlashingEngine, 'fastboot')
    def test_perform_format_no_erase(self, mock_fb):
        """perform_full_format with erase_userdata=False."""
        mock_fb.return_value = {"success": True, "stdout": "OKAY", "stderr": "", "returncode": 0}
        result = self.engine.perform_full_format("SERIAL1", erase_userdata=False, reset_frp=False)
        self.assertTrue(result)

    @patch.object(FlashingEngine, 'fastboot')
    def test_perform_format_frp_only(self, mock_fb):
        """perform_full_format with only FRP reset."""
        mock_fb.return_value = {"success": True, "stdout": "OKAY", "stderr": "", "returncode": 0}
        result = self.engine.perform_full_format("SERIAL1", erase_userdata=False, reset_frp=True)
        self.assertTrue(result)


class TestStorageHealth(unittest.TestCase):
    """Test storage health diagnostics."""

    def setUp(self):
        self.engine = FlashingEngine()

    @patch.object(FlashingEngine, 'adb')
    def test_scan_storage_health(self, mock_adb):
        """scan_storage_health returns health info."""
        mock_adb.return_value = {"success": True, "stdout": "", "stderr": "", "returncode": 0}
        result = self.engine.scan_storage_health("SERIAL1")
        self.assertEqual(result["device_id"], "SERIAL1")
        self.assertIn("storage_health", result)
        self.assertIn("read_speed_mbps", result)
        self.assertIn("write_speed_mbps", result)
        self.assertIn("partition_table_status", result)
        self.assertEqual(result["partition_table_status"], "VALID")

    def test_scan_storage_health_structure(self):
        """scan_storage_health returns correct structure."""
        result = self.engine.scan_storage_health("TestDevice")
        self.assertIsInstance(result, dict)
        self.assertIn("bad_blocks_found", result)
        self.assertIn("storage_health", result)


class TestBootloaderOperations(unittest.TestCase):
    """Test bootloader lock/unlock and slot management."""

    def setUp(self):
        self.engine = FlashingEngine()

    @patch.object(FlashingEngine, 'fastboot')
    def test_unlock_bootloader(self, mock_fb):
        """unlock_bootloader sends oem unlock."""
        mock_fb.return_value = {"success": True, "stdout": "OKAY", "stderr": "", "returncode": 0}
        result = self.engine.unlock_bootloader("SERIAL1", "samsung")
        self.assertEqual(result["status"], "UNLOCKED")
        self.assertEqual(result["manufacturer"], "samsung")
        self.assertIn("warning", result)

    @patch.object(FlashingEngine, 'fastboot')
    def test_unlock_bootloader_failure(self, mock_fb):
        """unlock_bootloader handles failure."""
        mock_fb.return_value = {"success": False, "stdout": "", "stderr": "FAILED", "returncode": 1}
        result = self.engine.unlock_bootloader("SERIAL1")
        self.assertEqual(result["status"], "FAILED")

    @patch.object(FlashingEngine, 'fastboot')
    def test_lock_bootloader(self, mock_fb):
        """lock_bootloader sends oem lock."""
        mock_fb.return_value = {"success": True, "stdout": "OKAY", "stderr": "", "returncode": 0}
        result = self.engine.lock_bootloader("SERIAL1")
        self.assertEqual(result["status"], "LOCKED")

    @patch.object(FlashingEngine, 'fastboot')
    def test_set_active_slot(self, mock_fb):
        """set_active_slot changes active slot."""
        mock_fb.return_value = {"success": True, "stdout": "OKAY", "stderr": "", "returncode": 0}
        result = self.engine.set_active_slot("SERIAL1", "b")
        self.assertTrue(result["success"])
        self.assertEqual(result["slot"], "b")

    @patch.object(FlashingEngine, 'fastboot')
    def test_set_active_slot_default(self, mock_fb):
        """set_active_slot defaults to slot 'a'."""
        mock_fb.return_value = {"success": True, "stdout": "OKAY", "stderr": "", "returncode": 0}
        result = self.engine.set_active_slot("SERIAL1")
        self.assertEqual(result["slot"], "a")


class TestUSBBootableTool(unittest.TestCase):
    """Test USB bootable tool creation."""

    def setUp(self):
        self.engine = FlashingEngine()

    def test_make_usb_bootable_tool(self):
        """make_usb_bootable_tool returns success."""
        result = self.engine.make_usb_bootable_tool("/dev/sdb1", "AURA_RECOVERY")
        self.assertEqual(result["status"], "USB_CREATED_SUCCESSFULLY")
        self.assertEqual(result["tool_type"], "AURA_RECOVERY")
        self.assertEqual(result["target_drive"], "/dev/sdb1")


class TestCallbackProgress(unittest.TestCase):
    """Test callback progress reporting in flash operations."""

    def setUp(self):
        self.engine = FlashingEngine()

    @patch.object(FlashingEngine, 'fastboot')
    def test_flash_with_callback(self, mock_fb):
        """Flash operations report progress via callback."""
        mock_fb.return_value = {"success": True, "stdout": "OKAY", "stderr": "", "returncode": 0}
        callback = MagicMock()
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ["boot", "recovery"]:
                Path(tmpdir, f"{name}.img").touch()
            self.engine._flash_via_fastboot("SERIAL1", tmpdir, callback=callback)
            # Callback should be called for each partition + progress
            self.assertGreaterEqual(callback.call_count, 2)

    def test_extract_with_callback(self):
        """Extraction reports progress via callback."""
        callback = MagicMock()
        with tempfile.TemporaryDirectory() as tmpdir:
            self.engine.extract_payload_bin("/fake/payload.bin", tmpdir, callback=callback)
            self.assertTrue(callback.called)


class TestCrossModuleFlashingIntegration(unittest.TestCase):
    """Test FlashingEngine integration with other modules."""

    def setUp(self):
        self.engine = FlashingEngine()

    @patch.object(FlashingEngine, 'fastboot')
    def test_verify_then_flash_pipeline(self, mock_fb):
        """Verify firmware → flash pipeline."""
        mock_fb.return_value = {"success": True, "stdout": "OKAY", "stderr": "", "returncode": 0}
        with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as f:
            fw_path = f.name
        try:
            # Verify
            verification = self.engine.verify_firmware_image(fw_path)
            self.assertTrue(verification["valid"])
            self.assertEqual(verification["format"], "SAMSUNG_ODIN_TAR")

            # Flash (simulated)
            with tempfile.TemporaryDirectory() as tmpdir:
                Path(tmpdir, "boot.img").touch()
                flash_result = self.engine.flash_firmware("SERIAL1", tmpdir, "FASTBOOT")
                self.assertTrue(flash_result)
        finally:
            os.unlink(fw_path)

    def test_unbrick_then_verify(self):
        """Unbrick device → verify storage health."""
        unbrick = self.engine.unbrick_device("SERIAL1", "Samsung")
        self.assertEqual(unbrick["status"], "UNBRICK_SUCCESSFUL")

        health = self.engine.scan_storage_health("SERIAL1")
        self.assertEqual(health["partition_table_status"], "VALID")

    def test_format_then_flash(self):
        """Format device → flash firmware → verify."""
        with patch.object(FlashingEngine, 'fastboot') as mock_fb:
            mock_fb.return_value = {"success": True, "stdout": "OKAY", "stderr": "", "returncode": 0}

            # Format
            format_result = self.engine.perform_full_format("SERIAL1")
            self.assertTrue(format_result)

            # Flash
            with tempfile.TemporaryDirectory() as tmpdir:
                Path(tmpdir, "boot.img").touch()
                flash_result = self.engine.flash_firmware("SERIAL1", tmpdir, "FASTBOOT")
                self.assertTrue(flash_result)

            # Verify health
            with patch.object(FlashingEngine, 'adb') as mock_adb:
                mock_adb.return_value = {"success": True, "stdout": "", "stderr": "", "returncode": 0}
                health = self.engine.scan_storage_health("SERIAL1")
                self.assertEqual(health["partition_table_status"], "VALID")


if __name__ == "__main__":
    unittest.main()
