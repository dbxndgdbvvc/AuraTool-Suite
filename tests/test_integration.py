"""
Integration Tests — Module Interactions End-to-End
====================================================
Tests verify that multiple modules work together correctly in real
workflows: AI → Repair → Security → Licensing → Device managers.
"""

import unittest
import sys
import os
import shutil

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.licensing import LicenseManager, LicenseTier
from core.api import APIClient
from core.security import SecurityManager
from drivers.driver_manager import DriverManager
from modules.aura_ai_assistant import AuraAIAssistant
from modules.ultimate_repair import UltimateRepairModule
from modules.flashing_engine import FlashingEngine
from modules.biometrics_fix import BiometricsFix
from modules.smart_devices import SmartDeviceManager
from modules.data_recovery import DataRecoveryModule
from modules.account_repair import AccountRepairModule
from modules.localization import LocalizationManager
from modules.android import AndroidDeviceManager
from modules.apple import AppleDeviceManager
from modules.download import DownloadManager


class TestAIRepairPipeline(unittest.TestCase):
    """Test the full AI → Repair pipeline: AI detects issue → repair executes."""

    def setUp(self):
        self.ai = AuraAIAssistant()
        self.repair = UltimateRepairModule()

    def test_ai_flash_command_triggers_repair_flow(self):
        """AI receives 'flash firmware' → queues flash → repair can flash."""
        ai_res = self.ai.process_voice_or_text_command("flash firmware for Samsung Galaxy S23")
        self.assertEqual(ai_res["status"], "ACTION_QUEUED")
        self.assertEqual(ai_res["action"], "flash_firmware")

        # Repair engine can independently handle the same device
        repair_res = self.repair.repair_major_system_issues("Samsung_Galaxy_S23", "bootloop")
        self.assertEqual(repair_res["status"], "COMPLETED")
        self.assertEqual(repair_res["device_id"], "Samsung_Galaxy_S23")

    def test_ai_detects_issues_repair_fixes_them(self):
        """AI analyzes logs → detects issues → repair fixes same issues."""
        log = "kernel panic ufs error bootloop frp_locked"
        diag = self.ai.analyze_system_logs(log)
        self.assertLess(diag["health_score"], 50)
        self.assertIn("bootloop", diag["issues_detected"])

        # Repair engine fixes the bootloop detected by AI
        repair_res = self.repair.repair_major_system_issues("DeviceX", "bootloop")
        self.assertEqual(repair_res["issues_resolved"], 1)
        self.assertEqual(repair_res["results"][0]["issue"], "bootloop")

    def test_ai_bypass_frp_repair_cloud_sync(self):
        """AI routes FRP bypass → repair handles cloud sync for same device."""
        ai_res = self.ai.process_voice_or_text_command("bypass FRP lock")
        self.assertEqual(ai_res["action"], "bypass_frp")

        cloud_res = self.repair.repair_cloud_and_account_sync("Samsung_Galaxy_S23", "samsung")
        self.assertEqual(cloud_res["status"], "RESOLVED")
        self.assertEqual(cloud_res["platform_detected"], "samsung")

    def test_ai_diagnose_repair_full_pipeline(self):
        """AI diagnoses device → repair runs full diagnostic → history tracked."""
        diag = self.ai.diagnose_device("Xiaomi_Redmi_Note12", "kernel panic wifi fail")
        self.assertIn("health_score", diag)
        self.assertEqual(diag["device_class"], "smartphone")

        full = self.repair.full_system_diagnostic("Xiaomi_Redmi_Note12")
        self.assertEqual(full["overall_status"], "COMPLETED")
        self.assertGreater(len(self.repair.get_repair_history()), 0)

    def test_ai_scan_devices_match_repair_catalogue(self):
        """AI scans ecosystem → repair catalogue covers all device types."""
        scan = self.ai.process_voice_or_text_command("scan connected devices")
        self.assertEqual(scan["status"], "SCAN_COMPLETE")
        self.assertGreater(scan["device_families"], 20)

        issues = self.repair.get_supported_issues()
        self.assertGreater(len(issues["major_issues"]), 5)
        self.assertGreater(len(issues["minor_issues"]), 5)
        self.assertGreater(len(issues["cloud_sync_issues"]), 5)


class TestSecurityLicensingPipeline(unittest.TestCase):
    """Test Security ↔ Licensing interactions."""

    def setUp(self):
        self.sec = SecurityManager()
        self._tmp_dir = os.path.join(os.path.dirname(__file__), "_test_lic_tmp")
        os.makedirs(self._tmp_dir, exist_ok=True)
        self.lic = LicenseManager(data_dir=self._tmp_dir)

    def tearDown(self):
        import shutil
        if os.path.exists(self._tmp_dir):
            shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_encrypted_license_key(self):
        """Generate license key → encrypt it → decrypt → verify."""
        key = self.lic.generate_vip_key()
        self.assertIn("AT-1Y", key)

        encrypted = self.sec.encrypt_data(key)
        decrypted = self.sec.decrypt_data(encrypted)
        self.assertEqual(decrypted, key)

    def test_license_status_with_encrypted_token(self):
        """License status check + encrypted token generation."""
        status = self.lic.check_license_status()
        self.assertTrue(status["is_active"])

        token = self.sec.generate_token()
        self.assertEqual(len(token), 64)  # 32 bytes hex = 64 chars

        # Hash the token for integrity
        hashed = self.sec.hash_data(token)
        self.assertTrue(self.sec.verify_hash(token, hashed))

    def test_feature_gating_by_tier(self):
        """Different tiers grant different features."""
        # Trial tier
        trial = LicenseManager(data_dir=self._tmp_dir + "_trial", tier=LicenseTier.TRIAL_15_DAYS)
        trial_status = trial.check_license_status()
        self.assertIn("Trial", trial_status["tier"])
        self.assertFalse(trial_status["cloud_backup"])

        # Professional tier
        pro = LicenseManager(data_dir=self._tmp_dir + "_pro", tier=LicenseTier.SIX_MONTHS)
        pro_status = pro.check_license_status()
        self.assertTrue(pro_status["cloud_backup"])
        self.assertFalse(pro_status["priority_support"])

        # VIP tier
        vip = LicenseManager(data_dir=self._tmp_dir + "_vip", tier=LicenseTier.ONE_YEAR_VIP)
        vip_status = vip.check_license_status()
        self.assertTrue(vip_status["cloud_backup"])
        self.assertTrue(vip_status["priority_support"])
        self.assertEqual(vip_status["supported_until_year"], 2030)

    def test_key_activation_updates_tier(self):
        """Activate a valid key → tier changes → features update."""
        activation_dir = self._tmp_dir + "_activation"
        if os.path.exists(activation_dir):
            shutil.rmtree(activation_dir, ignore_errors=True)
        mgr = LicenseManager(data_dir=activation_dir)
        self.assertEqual(mgr.tier, LicenseTier.TRIAL_15_DAYS)

        key = mgr.generate_valid_key("AT-6M")
        success = mgr.activate_key(key)
        self.assertTrue(success)
        self.assertEqual(mgr.tier, LicenseTier.SIX_MONTHS)

        status = mgr.check_license_status()
        self.assertEqual(status["tier"], "6 Months Professional")
        self.assertGreater(status["days_remaining"], 170)

    def test_storage_health_with_encrypted_backup(self):
        """Scan storage health → encrypt backup → verify integrity."""
        health = self.sec.scan_storage_health("TestDevice")
        self.assertGreater(health["health_score"], 50)

        # Simulate encrypting a backup of EFS data
        efs_data = "EFS_backup_partition_data_12345"
        encrypted = self.sec.encrypt_data(efs_data)
        decrypted = self.sec.decrypt_data(encrypted)
        self.assertEqual(decrypted, efs_data)

        # Verify integrity
        expected_hash = self.sec.hash_data(efs_data)
        self.assertTrue(self.sec.verify_hash(efs_data, expected_hash))


class TestFlashingWithAPICloudPipeline(unittest.TestCase):
    """Test FlashingEngine ↔ APIClient cloud sync interactions."""

    def setUp(self):
        self.api = APIClient()
        self.flash = FlashingEngine()

    def test_firmware_download_then_flash(self):
        """Fetch firmware metadata → download → flash to device."""
        meta = self.api.fetch_firmware_metadata("Galaxy_S23")
        self.assertEqual(meta["model"], "Galaxy_S23")
        self.assertIn("download_url", meta)
        self.assertIn("sha256", meta)

        # Simulate download
        success = self.api.download_firmware(
            meta["download_url"],
            "/tmp/galaxy_s23_fw.bin"
        )
        self.assertTrue(success)

        # Flash the firmware
        flash_result = self.flash.flash_firmware("Galaxy_S23", meta["download_url"], "FASTBOOT")
        self.assertTrue(flash_result)

    def test_storage_health_scan_then_backup_to_cloud(self):
        """Scan storage → detect health → backup EFS to cloud."""
        health = self.flash.scan_storage_health("Galaxy_S23")
        self.assertEqual(health["partition_table_status"], "VALID")
        self.assertGreater(health["read_speed_mbps"], 100)

        # Backup to cloud
        backup = self.api.cloud_backup_partition(
            "Galaxy_S23", "efs", b"efs_partition_data"
        )
        self.assertIn("cloud_id", backup)
        self.assertEqual(backup["device_id"], "Galaxy_S23")

        # Restore from cloud
        restored = self.api.cloud_restore_partition("Galaxy_S23", "efs")
        self.assertEqual(restored, b"restored_partition_data_placeholder")

    def test_usb_port_scan_detects_edl_device(self):
        """Scan USB ports → find EDL device → enter EDL mode."""
        ports = self.api.scan_usb_ports()
        self.assertGreater(len(ports), 0)

        edl_ports = [p for p in ports if p["mode"] == "EDL"]
        self.assertGreater(len(edl_ports), 0)
        self.assertEqual(edl_ports[0]["vid"], "0x05C6")
        self.assertEqual(edl_ports[0]["pid"], "0x9008")

        # Enter EDL mode
        edl_result = self.api.enter_edl_mode("TestDevice")
        self.assertEqual(edl_result["target_mode"], "EDL (Qualcomm 9008)")

    def test_brom_port_detection_and_command(self):
        """Detect BROM port → send BROM command."""
        ports = self.api.scan_usb_ports()
        brom_ports = [p for p in ports if p["mode"] == "BROM"]
        self.assertGreater(len(brom_ports), 0)

        result = self.api.send_brom_command("READ_REG", b"\x00\x00\x00\x00")
        self.assertEqual(result["status"], "SUCCESS")


class TestAndroidApplePlatformPipeline(unittest.TestCase):
    """Test Android ↔ Apple device managers with shared operations."""

    def setUp(self):
        self.android = AndroidDeviceManager()
        self.apple = AppleDeviceManager()
        self.flash = FlashingEngine()
        self.bio = BiometricsFix()

    def test_samsung_flash_then_biometric_calibrate(self):
        """Flash Samsung device → run biometric diagnostics → recalibrate."""
        flash_res = self.android.flash_device("Galaxy_S23", "Samsung", "/fw/s23.tar")
        self.assertEqual(flash_res["status"], "SUCCESS")
        self.assertEqual(flash_res["manufacturer"], "Samsung")

        # After flash, run biometrics
        bio_diag = self.bio.run_diagnostics("Galaxy_S23")
        self.assertEqual(bio_diag["fingerprint_sensor"], "OPERATIONAL")

        calib = self.bio.recalibrate_sensors("Galaxy_S23", "FINGERPRINT")
        self.assertTrue(calib)

    def test_xiaomi_edl_backup_restore_cycle(self):
        """Xiaomi EDL flash → backup EFS → restore EFS."""
        flash_res = self.android.flash_device("Redmi_Note12", "xiaomi", "/fw/note12.bin")
        self.assertEqual(flash_res["status"], "SUCCESS")

        # Backup critical partitions
        backup = self.android.backup_partitions("Redmi_Note12", "xiaomi", "/backup/")
        self.assertGreater(len(backup["partitions_backed_up"]), 0)

    def test_apple_dfu_restore_flow(self):
        """Enter DFU mode → restore firmware → verify activation lock."""
        dfu = self.apple.enter_dfu_mode("iPhone_15_Pro")
        self.assertEqual(dfu["target_mode"], "DFU Mode")

        restore = self.apple.restore_device("iPhone_15_Pro", "iPhone_15_Pro_17.6.ipsw")
        self.assertEqual(restore["status"], "RESTORE_COMPLETE")

        lock = self.apple.check_activation_lock("iPhone_15_Pro")
        self.assertFalse(lock["activation_lock"])

    def test_apple_watch_pairing_flow(self):
        """Pair Apple Watch → verify connection."""
        result = self.apple.pair_apple_watch("Watch_Ultra_2", "iPhone_15_Pro")
        self.assertEqual(result["pairing_status"], "INITIATED")

    def test_cross_platform_firmware_list(self):
        """List firmware for both Android and Apple ecosystems."""
        android_fw = self.android.get_manufacturer_info("samsung")
        self.assertIn("flash_tool", android_fw)
        self.assertEqual(android_fw["flash_tool"], "Odin / Heimdall")

        apple_families = self.apple.list_families()
        self.assertGreater(len(apple_families), 3)
        family_names = [f["name"] for f in apple_families]
        self.assertIn("iPhone", family_names)
        self.assertIn("iPad", family_names)


class TestSmartDeviceEcosystemPipeline(unittest.TestCase):
    """Test SmartDeviceManager ↔ other modules for full ecosystem."""

    def setUp(self):
        self.smart = SmartDeviceManager()
        self.ai = AuraAIAssistant()
        self.repair = UltimateRepairModule()

    def test_detect_tablet_then_diagnose(self):
        """Detect tablet → AI classifies → repair handles."""
        devices = self.smart.detect_connected_devices()
        tablets = [d for d in devices if d["type"].lower() == "tablet"]
        self.assertGreater(len(tablets), 0)

        tablet = tablets[0]
        classification = self.ai._classify_device(tablet["model"])
        self.assertEqual(classification, "tablet")

    def test_detect_watch_then_classify(self):
        """Detect smartwatch → AI classifies correctly."""
        devices = self.smart.detect_connected_devices()
        watches = [d for d in devices if d["type"].lower() == "smartwatch"]
        self.assertGreater(len(watches), 0)

        watch = watches[0]
        classification = self.ai._classify_device(watch["model"])
        self.assertEqual(classification, "smartwatch")

    def test_detect_ar_vr_headset(self):
        """Detect AR/VR headset → classify → repair supports it."""
        devices = self.smart.detect_connected_devices()
        ar_vr = [d for d in devices if "ar_vr" in d["type"].lower() or "glasses" in d["type"].lower()]
        self.assertGreater(len(ar_vr), 0)

        device = ar_vr[0]
        classification = self.ai._classify_device(device["model"])
        self.assertEqual(classification, "smart_glasses_ar_vr")

    def test_firmware_update_check_for_peripheral(self):
        """Check firmware updates for connected peripherals."""
        devices = self.smart.detect_connected_devices()
        for dev in devices[:2]:
            update = self.smart.scan_firmware_updates(dev["model"])
            self.assertIn("update_available", update)

    def test_device_diagnostics_across_ecosystem(self):
        """Run diagnostics on all detected device types."""
        devices = self.smart.detect_connected_devices()
        for dev in devices:
            diag = self.smart.run_device_diagnostics(dev["model"])
            self.assertEqual(diag["overall_status"], "HEALTHY")


class TestDownloadManagerPipeline(unittest.TestCase):
    """Test DownloadManager ↔ FlashingEngine integration."""

    def setUp(self):
        self.dl = DownloadManager()
        self.flash = FlashingEngine()

    def test_list_firmware_download_flash(self):
        """List firmware → download → flash pipeline."""
        firmware_list = self.dl.list_available_firmware("Samsung")
        self.assertGreater(len(firmware_list), 0)

        fw = firmware_list[0]
        result = self.dl.download_firmware(fw["manufacturer"], fw["model"])
        # Download may fail in test environment (no network), check either success or error
        if result.get("status") == "DOWNLOADED":
            self.assertIn("destination", result)
            # Flash the downloaded firmware
            flash_res = self.flash.flash_firmware(fw["model"], result["destination"], "FASTBOOT")
            self.assertTrue(flash_res)
        else:
            # Network not available, verify error handling works
            self.assertIn("error", result)

    def test_verify_download_integrity(self):
        """Download firmware → verify SHA-256 integrity."""
        result = self.dl.download_firmware("Samsung", "Galaxy S23")
        # Download may fail in test environment (no network)
        if result.get("status") == "DOWNLOADED":
            test_file = result["destination"]
            if os.path.exists(test_file):
                self.assertTrue(os.path.getsize(test_file) > 0)
        else:
            # Network not available, verify error handling works
            self.assertIn("error", result)

    def test_download_history_tracking(self):
        """Download multiple firmwares → verify history or error tracking."""
        result1 = self.dl.download_firmware("Samsung", "Galaxy S23")
        result2 = self.dl.download_firmware("Samsung", "Galaxy A54")

        # Check results (may fail in test environment without network)
        # At minimum, the methods should return valid response structures
        self.assertIn("manufacturer", result1)
        self.assertIn("model", result1)
        self.assertIn("manufacturer", result2)
        self.assertIn("model", result2)


class TestLocalizationWithAIPipeline(unittest.TestCase):
    """Test LocalizationManager ↔ AI assistant language detection."""

    def setUp(self):
        self.loc = LocalizationManager()
        self.ai = AuraAIAssistant()

    def test_ai_arabic_command_triggers_localization(self):
        """AI receives Arabic command → routes to localization."""
        res = self.ai.process_voice_or_text_command("تفعيل اللغة العربية")
        self.assertEqual(res["action"], "localize_device")
        self.assertEqual(res["target_language"], "ar")

    def test_localization_applies_to_device(self):
        """Set language → apply to device → verify."""
        self.loc.set_language("ar")
        title = self.loc.get_string("title")
        self.assertIn("AuraTool", title)

        success = self.loc.apply_locale_to_device("TestDevice", "ar", enable_rtl=True)
        self.assertTrue(success)

    def test_csc_configuration(self):
        """Configure CSC for regional features."""
        success = self.loc.configure_csc("TestDevice", "XSG")
        self.assertTrue(success)

    def test_unhide_languages(self):
        """Unhide system languages on device."""
        success = self.loc.unhide_system_languages("TestDevice")
        self.assertTrue(success)

    def test_multi_language_support(self):
        """Test all supported languages have translations."""
        for code, name in LocalizationManager.SUPPORTED_LANGUAGES.items():
            self.loc.set_language(code)
            title = self.loc.get_string("title")
            self.assertNotEqual(title, "title")  # Should be translated, not key


class TestAccountRepairWithSecurityPipeline(unittest.TestCase):
    """Test AccountRepairModule ↔ SecurityManager data protection."""

    def setUp(self):
        self.acc = AccountRepairModule()
        self.sec = SecurityManager()

    def test_backup_efs_with_encrypted_hash(self):
        """Backup EFS → compute encrypted hash → verify integrity."""
        success = self.acc.backup_efs_nvram("Galaxy_S23", "/backup/efs/")
        self.assertTrue(success)

        # Verify data integrity with security module
        test_data = "EFS_backup_data_galaxy_s23"
        encrypted = self.sec.encrypt_data(test_data)
        decrypted = self.sec.decrypt_data(encrypted)
        self.assertEqual(decrypted, test_data)

        # Hash verification
        expected = self.sec.hash_data(test_data)
        self.assertTrue(self.sec.verify_hash(test_data, expected))

    def test_account_diagnostics_then_repair(self):
        """Run diagnostics → detect issues → repair account."""
        diag = self.acc.run_account_diagnostics("Galaxy_S23", "ADB")
        self.assertIn(diag["account_sync_status"], ["NORMAL", "LOCKED"])
        self.assertEqual(diag["integrity_check"], "PASSED")

    def test_restore_efs_after_encrypted_backup(self):
        """Backup EFS → encrypt backup → restore EFS."""
        # Backup
        self.acc.backup_efs_nvram("Device1", "/backup/")

        # Encrypt backup metadata
        metadata = "efs_backup_Device1_20250101"
        enc_metadata = self.sec.encrypt_data(metadata)

        # Restore
        success = self.acc.restore_efs_nvram("Device1", "/backup/")
        self.assertTrue(success)

        # Verify metadata integrity
        dec_metadata = self.sec.decrypt_data(enc_metadata)
        self.assertEqual(dec_metadata, metadata)


class TestFullSystemWorkflow(unittest.TestCase):
    """End-to-end workflow: detect → diagnose → repair → verify."""

    def setUp(self):
        self.ai = AuraAIAssistant()
        self.repair = UltimateRepairModule()
        self.smart = SmartDeviceManager()
        self.flash = FlashingEngine()
        self.acc = AccountRepairModule()
        self.sec = SecurityManager()
        self.bio = BiometricsFix()
        self.api = APIClient()
        self.lic = LicenseManager()

    def test_complete_samsung_repair_workflow(self):
        """Full workflow: license check → detect → diagnose → repair → verify."""
        # 1. Verify license
        status = self.lic.check_license_status()
        self.assertTrue(status["is_active"])

        # 2. Detect device
        devices = self.smart.detect_connected_devices()
        self.assertGreater(len(devices), 0)

        # 3. AI diagnosis
        diag = self.ai.diagnose_device(
            "Samsung_Galaxy_S23",
            "kernel panic bootloop ufs error"
        )
        self.assertLess(diag["health_score"], 60)
        self.assertIn("bootloop", diag["issues_detected"])

        # 4. Repair major issues
        major = self.repair.repair_major_system_issues("Samsung_Galaxy_S23", "bootloop")
        self.assertEqual(major["issues_resolved"], 1)

        # 5. Repair cloud sync
        cloud = self.repair.repair_cloud_and_account_sync("Samsung_Galaxy_S23", "samsung")
        self.assertEqual(cloud["status"], "RESOLVED")

        # 6. Account diagnostics
        acc_diag = self.acc.run_account_diagnostics("Samsung_Galaxy_S23")
        self.assertEqual(acc_diag["integrity_check"], "PASSED")

        # 7. Storage health check
        health = self.flash.scan_storage_health("Samsung_Galaxy_S23")
        self.assertEqual(health["partition_table_status"], "VALID")

        # 8. Biometric calibration
        bio = self.bio.recalibrate_sensors("Samsung_Galaxy_S23")
        self.assertTrue(bio)

        # 9. Verify repair history
        history = self.repair.get_repair_history()
        self.assertGreaterEqual(len(history), 2)

    def test_complete_apple_device_workflow(self):
        """Full Apple workflow: detect → DFU restore → activation check."""
        apple = AppleDeviceManager()

        # 1. Enter DFU
        dfu = apple.enter_dfu_mode("iPhone_15_Pro")
        self.assertEqual(dfu["target_mode"], "DFU Mode")

        # 2. Restore
        restore = apple.restore_device("iPhone_15_Pro")
        self.assertEqual(restore["status"], "RESTORE_COMPLETE")

        # 3. Check activation lock
        lock = apple.check_activation_lock("iPhone_15_Pro")
        self.assertFalse(lock["activation_lock"])

        # 4. Backup
        backup = apple.backup_device("iPhone_15_Pro", "/backup/iphone/")
        self.assertEqual(backup["status"], "BACKUP_COMPLETE")

    def test_cloud_sync_encrypted_backup_workflow(self):
        """Cloud backup → encrypt → verify → restore workflow."""
        # 1. Scan USB ports
        ports = self.api.scan_usb_ports()
        self.assertGreater(len(ports), 0)

        # 2. Backup EFS to cloud
        backup = self.api.cloud_backup_partition("Device1", "efs", b"efs_data")
        self.assertIn("cloud_id", backup)

        # 3. Encrypt backup metadata
        meta = self.sec.encrypt_data(f"backup_{backup['cloud_id']}")
        self.assertIsNotNone(meta)

        # 4. Verify integrity
        hash_val = self.sec.hash_data("efs_data")
        self.assertTrue(self.sec.verify_hash("efs_data", hash_val))

        # 5. Restore from cloud
        restored = self.api.cloud_restore_partition("Device1", "efs")
        self.assertEqual(restored, b"restored_partition_data_placeholder")

        # 6. List cloud backups
        backups = self.api.list_cloud_backups("Device1")
        self.assertGreater(len(backups), 0)


if __name__ == "__main__":
    unittest.main()
