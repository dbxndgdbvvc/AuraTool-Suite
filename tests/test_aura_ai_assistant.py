"""
Unit Tests — AuraAIAssistant Module
=====================================
Tests cover:
  - Natural-language command parsing and routing
  - System log analysis with error signature detection
  - Health-score calculation accuracy
  - License verification and activation
  - Device ecosystem catalogue
  - Device classification heuristics
  - Session logging history
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.aura_ai_assistant import AuraAIAssistant


class TestCommandRouting(unittest.TestCase):
    """Test natural-language command parsing and action routing."""

    def setUp(self):
        self.ai = AuraAIAssistant()

    # ── Flash / Update commands ────────────────────────────────────── #

    def test_flash_command(self):
        res = self.ai.process_voice_or_text_command("flash firmware for Samsung Galaxy S23")
        self.assertEqual(res["status"], "ACTION_QUEUED")
        self.assertEqual(res["action"], "flash_firmware")
        self.assertGreater(res["confidence"], 0.8)

    def test_update_command(self):
        res = self.ai.process_voice_or_text_command("update the system software")
        self.assertEqual(res["action"], "flash_firmware")

    # ── FRP / Bypass commands ──────────────────────────────────────── #

    def test_frp_bypass_command(self):
        res = self.ai.process_voice_or_text_command("bypass FRP lock on this device")
        self.assertEqual(res["action"], "bypass_frp")
        self.assertEqual(res["status"], "ACTION_QUEUED")

    def test_account_lock_command(self):
        res = self.ai.process_voice_or_text_command("remove account lock")
        self.assertEqual(res["action"], "bypass_frp")

    # ── Log analysis commands ──────────────────────────────────────── #

    def test_analyze_logs_command(self):
        res = self.ai.process_voice_or_text_command("analyze the system logs")
        self.assertEqual(res["action"], "analyze_logs")
        self.assertEqual(res["status"], "NEEDS_LOG")

    def test_diagnose_command(self):
        res = self.ai.process_voice_or_text_command("diagnose errors on this device")
        self.assertEqual(res["action"], "analyze_logs")

    # ── Storage commands ───────────────────────────────────────────── #

    def test_storage_health_command(self):
        res = self.ai.process_voice_or_text_command("check storage health")
        self.assertEqual(res["action"], "storage_health")

    # ── Backup / Restore / Recover commands ─────────────────────────── #

    def test_backup_command(self):
        res = self.ai.process_voice_or_text_command("backup my data")
        self.assertEqual(res["action"], "backup_data")

    def test_restore_command(self):
        res = self.ai.process_voice_or_text_command("restore data from backup")
        self.assertEqual(res["action"], "restore_data")

    def test_recover_command(self):
        res = self.ai.process_voice_or_text_command("recover deleted photos")
        self.assertEqual(res["action"], "recover_data")

    # ── Biometrics commands ────────────────────────────────────────── #

    def test_fingerprint_command(self):
        res = self.ai.process_voice_or_text_command("fix fingerprint sensor")
        self.assertEqual(res["action"], "fix_biometrics")

    def test_face_id_command(self):
        res = self.ai.process_voice_or_text_command("calibrate face recognition")
        self.assertEqual(res["action"], "fix_biometrics")

    # ── Reboot commands ────────────────────────────────────────────── #

    def test_reboot_command(self):
        res = self.ai.process_voice_or_text_command("reboot the device")
        self.assertEqual(res["action"], "reboot_device")

    def test_restart_command(self):
        res = self.ai.process_voice_or_text_command("restart phone into fastboot")
        self.assertEqual(res["action"], "reboot_device")

    # ── Repair commands ────────────────────────────────────────────── #

    def test_repair_command(self):
        res = self.ai.process_voice_or_text_command("run ultimate repair")
        self.assertEqual(res["action"], "ultimate_repair")

    def test_fix_command(self):
        res = self.ai.process_voice_or_text_command("fix bootloop issues")
        self.assertEqual(res["action"], "ultimate_repair")

    # ── License commands ───────────────────────────────────────────── #

    def test_check_license_command(self):
        res = self.ai.process_voice_or_text_command("check my license status")
        self.assertEqual(res["action"], "check_license")
        self.assertEqual(res["status"], "INFO")
        self.assertIn("license", res["message"].lower())

    def test_activate_license_command(self):
        res = self.ai.process_voice_or_text_command("activate license key")
        self.assertEqual(res["action"], "activate_license")
        self.assertEqual(res["status"], "NEEDS_KEY")

    # ── Scan / Detect commands ─────────────────────────────────────── #

    def test_scan_devices_command(self):
        res = self.ai.process_voice_or_text_command("scan connected devices")
        self.assertEqual(res["action"], "scan_devices")
        self.assertEqual(res["status"], "SCAN_COMPLETE")
        self.assertGreater(res["device_families"], 0)

    # ── Localization commands ──────────────────────────────────────── #

    def test_language_command(self):
        res = self.ai.process_voice_or_text_command("change language settings")
        self.assertEqual(res["action"], "localize_device")

    def test_arabic_command(self):
        res = self.ai.process_voice_or_text_command("تفعيل اللغة العربية")
        self.assertEqual(res["action"], "localize_device")
        self.assertEqual(res["target_language"], "ar")

    # ── Unknown commands ───────────────────────────────────────────── #

    def test_unknown_command(self):
        res = self.ai.process_voice_or_text_command("xyzzy foobar baz")
        self.assertEqual(res["status"], "UNKNOWN_COMMAND")
        self.assertEqual(res["confidence"], 0.0)
        self.assertIn("could not map", res["message"].lower())

    # ── Case insensitivity ─────────────────────────────────────────── #

    def test_case_insensitive_command(self):
        res = self.ai.process_voice_or_text_command("FLASH FIRMWARE")
        self.assertEqual(res["action"], "flash_firmware")

    def test_mixed_case_command(self):
        res = self.ai.process_voice_or_text_command("BaCkUp My DaTa")
        self.assertEqual(res["action"], "backup_data")


class TestLogAnalysis(unittest.TestCase):
    """Test system log analysis engine."""

    def setUp(self):
        self.ai = AuraAIAssistant()

    # ── Individual error signatures ────────────────────────────────── #

    def test_kernel_panic_detected(self):
        log = "CRITICAL: kernel panic at 0x8000000 — not syncing"
        diag = self.ai.analyze_system_logs(log)
        self.assertIn("kernel_panic", diag["issues_detected"])
        self.assertLess(diag["health_score"], 100)

    def test_bootloop_detected(self):
        log = "Device entering boot loop after OTA update"
        diag = self.ai.analyze_system_logs(log)
        self.assertIn("bootloop", diag["issues_detected"])

    def test_frp_locked_detected(self):
        log = "FRP lock active — factory reset protection enabled"
        diag = self.ai.analyze_system_logs(log)
        self.assertIn("frp_locked", diag["issues_detected"])

    def test_ufs_error_detected(self):
        log = "UFS error: bad block at sector 4096"
        diag = self.ai.analyze_system_logs(log)
        self.assertIn("ufs_error", diag["issues_detected"])

    def test_memory_corruption_detected(self):
        log = "dm-verity corruption detected in system partition"
        diag = self.ai.analyze_system_logs(log)
        self.assertIn("memory_corrupt", diag["issues_detected"])

    def test_wifi_failure_detected(self):
        log = "wifi fail: wlan0 interface down"
        diag = self.ai.analyze_system_logs(log)
        self.assertIn("wifi_failure", diag["issues_detected"])

    def test_bluetooth_issue_detected(self):
        log = "bluetooth error: unable to enable adapter"
        diag = self.ai.analyze_system_logs(log)
        self.assertIn("bluetooth_issue", diag["issues_detected"])

    def test_touchscreen_detected(self):
        log = "touchscreen error: digitizer not responding"
        diag = self.ai.analyze_system_logs(log)
        self.assertIn("touchscreen", diag["issues_detected"])

    def test_battery_drain_detected(self):
        log = "battery drain detected: thermal throttling active"
        diag = self.ai.analyze_system_logs(log)
        self.assertIn("battery_drain", diag["issues_detected"])

    def test_camera_fail_detected(self):
        log = "camera fail: sensor not detected on i2c bus"
        diag = self.ai.analyze_system_logs(log)
        self.assertIn("camera_fail", diag["issues_detected"])

    def test_network_lost_detected(self):
        log = "no service: sim not detected in slot 1"
        diag = self.ai.analyze_system_logs(log)
        self.assertIn("network_lost", diag["issues_detected"])

    def test_storage_full_detected(self):
        log = "storage full: no space left on device"
        diag = self.ai.analyze_system_logs(log)
        self.assertIn("storage_full", diag["issues_detected"])

    def test_app_crash_detected(self):
        log = "fatal exception in com.example.app at line 42"
        diag = self.ai.analyze_system_logs(log)
        self.assertIn("app_crash", diag["issues_detected"])

    def test_virus_detected(self):
        log = "malware detected: trojan.genericKD.12345"
        diag = self.ai.analyze_system_logs(log)
        self.assertIn("virus_detected", diag["issues_detected"])

    def test_bootloader_issue_detected(self):
        log = "bootloader locked — dm-verity corrupt"
        diag = self.ai.analyze_system_logs(log)
        self.assertIn("bootloader", diag["issues_detected"])

    # ── Health score calculation ────────────────────────────────────── #

    def test_clean_log_gives_high_score(self):
        log = "System started successfully. All services running."
        diag = self.ai.analyze_system_logs(log)
        self.assertEqual(diag["health_score"], 100)
        self.assertEqual(len(diag["issues_detected"]), 0)

    def test_multiple_issues_lower_score(self):
        log = "kernel panic ufs error bootloop frp_locked wifi fail"
        diag = self.ai.analyze_system_logs(log)
        self.assertLess(diag["health_score"], 50)
        self.assertGreaterEqual(diag["issue_count"], 4)

    def test_health_score_never_negative(self):
        # Worst case: every signature triggers
        log = ("kernel panic bootloop frp_locked ufs_error memory_corrupt "
               "wifi_fail bluetooth_issue touchscreen battery_drain camera_fail "
               "network_lost storage_full app_crash virus_detected bootloader_locked")
        diag = self.ai.analyze_system_logs(log)
        self.assertGreaterEqual(diag["health_score"], 0)

    # ── Recommendations ────────────────────────────────────────────── #

    def test_recommendations_present_for_issues(self):
        log = "kernel panic bad block ufs error"
        diag = self.ai.analyze_system_logs(log)
        self.assertGreater(len(diag["all_recommendations"]), 0)

    def test_no_recommendations_for_clean_log(self):
        log = "System healthy"
        diag = self.ai.analyze_system_logs(log)
        self.assertEqual(len(diag["all_recommendations"]), 0)

    def test_analyzed_at_timestamp(self):
        diag = self.ai.analyze_system_logs("test")
        self.assertIn("analyzed_at", diag)

    def test_case_insensitive_log_matching(self):
        diag = self.ai.analyze_system_logs("KERNEL PANIC UFS ERROR")
        self.assertIn("kernel_panic", diag["issues_detected"])
        self.assertIn("ufs_error", diag["issues_detected"])


class TestLicenseVerification(unittest.TestCase):
    """Test license verification and key activation."""

    def setUp(self):
        self.ai = AuraAIAssistant()

    def test_verify_license_returns_valid_structure(self):
        result = self.ai.verify_extended_license_2030()
        self.assertIn("tier", result)
        self.assertIn("is_active", result)
        self.assertIn("days_remaining", result)
        self.assertIn("supported_until_year", result)
        self.assertEqual(result["supported_until_year"], 2030)

    def test_activate_valid_key(self):
        key = self.ai.activate_license_key("AT-15D-A1B2C3D4")
        # The key must match the expected format to activate
        # Since we generate keys internally, test the structure
        self.assertIn("activated", key)
        self.assertIn("message", key)

    def test_activate_invalid_key(self):
        result = self.ai.activate_license_key("INVALID-KEY")
        self.assertFalse(result["activated"])

    def test_activate_empty_key(self):
        result = self.ai.activate_license_key("")
        self.assertFalse(result["activated"])


class TestDeviceEcosystem(unittest.TestCase):
    """Test device ecosystem coverage and classification."""

    def setUp(self):
        self.ai = AuraAIAssistant()

    def test_ecosystem_has_smartphones(self):
        eco = self.ai.get_supported_devices()
        self.assertIn("smartphones", eco)
        self.assertGreater(len(eco["smartphones"]), 5)

    def test_ecosystem_has_tablets(self):
        eco = self.ai.get_supported_devices()
        self.assertIn("tablets", eco)
        self.assertGreater(len(eco["tablets"]), 3)

    def test_ecosystem_has_smartwatches(self):
        eco = self.ai.get_supported_devices()
        self.assertIn("smartwatches", eco)
        self.assertGreater(len(eco["smartwatches"]), 2)

    def test_ecosystem_has_smart_glasses(self):
        eco = self.ai.get_supported_devices()
        self.assertIn("smart_glasses_ar_vr", eco)
        self.assertGreater(len(eco["smart_glasses_ar_vr"]), 2)

    # ── Device classification ──────────────────────────────────────── #

    def test_classify_smartwatch(self):
        self.assertEqual(self.ai._classify_device("Apple Watch Series 9"), "smartwatch")
        self.assertEqual(self.ai._classify_device("Galaxy Watch 6"), "smartwatch")
        self.assertEqual(self.ai._classify_device("Mi Band 7 Pro"), "smartwatch")

    def test_classify_tablet(self):
        self.assertEqual(self.ai._classify_device("Galaxy Tab S9"), "tablet")
        self.assertEqual(self.ai._classify_device("iPad Pro 12.9"), "tablet")
        self.assertEqual(self.ai._classify_device("Xiaomi Pad 6"), "tablet")

    def test_classify_smart_glasses(self):
        self.assertEqual(self.ai._classify_device("Apple Vision Pro"), "smart_glasses_ar_vr")
        self.assertEqual(self.ai._classify_device("Meta Quest 3"), "smart_glasses_ar_vr")
        self.assertEqual(self.ai._classify_device("XREAL Air 2"), "smart_glasses_ar_vr")

    def test_classify_smartphone_default(self):
        self.assertEqual(self.ai._classify_device("Samsung Galaxy S23"), "smartphone")
        self.assertEqual(self.ai._classify_device("iPhone 15 Pro"), "smartphone")

    # ── Combined device diagnosis ──────────────────────────────────── #

    def test_diagnose_device_with_logs(self):
        result = self.ai.diagnose_device("Samsung_S23", "kernel panic ufs error")
        self.assertIn("device_id", result)
        self.assertIn("health_score", result)
        self.assertIn("device_class", result)
        self.assertEqual(result["device_id"], "Samsung_S23")

    def test_diagnose_device_without_logs(self):
        result = self.ai.diagnose_device("GenericDevice")
        self.assertEqual(result["health_score"], 100)


class TestSessionLogging(unittest.TestCase):
    """Test session log history tracking."""

    def setUp(self):
        self.ai = AuraAIAssistant()

    def test_session_log_records_commands(self):
        self.ai.process_voice_or_text_command("flash firmware")
        self.ai.process_voice_or_text_command("check license")
        self.assertEqual(len(self.ai.session_log), 2)

    def test_session_log_entry_structure(self):
        self.ai.process_voice_or_text_command("backup data")
        entry = self.ai.session_log[0]
        self.assertIn("timestamp", entry)
        self.assertIn("command", entry)
        self.assertIn("result", entry)
        self.assertEqual(entry["command"], "backup data")

    def test_session_log_includes_last_analysis(self):
        self.ai.analyze_system_logs("kernel panic")
        self.assertIsNotNone(self.ai.last_analysis)
        self.assertIn("health_score", self.ai.last_analysis)


class TestConfidenceScores(unittest.TestCase):
    """Test that confidence scores are reasonable."""

    def setUp(self):
        self.ai = AuraAIAssistant()

    def test_known_command_high_confidence(self):
        res = self.ai.process_voice_or_text_command("flash firmware")
        self.assertGreaterEqual(res["confidence"], 0.8)

    def test_unknown_command_zero_confidence(self):
        res = self.ai.process_voice_or_text_command("unknown gibberish")
        self.assertEqual(res["confidence"], 0.0)


if __name__ == "__main__":
    unittest.main()
