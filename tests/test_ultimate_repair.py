"""
Unit Tests — UltimateRepairModule
===================================
Tests cover:
  - Major system issue detection and repair (bootloop, memory, EDL, BROM)
  - Minor issue detection and repair (apps, Wi-Fi, Bluetooth, power)
  - Cloud/account sync loop repair (Samsung, Apple, Xiaomi, Huawei, Google)
  - Full system diagnostic pipeline
  - Device platform auto-detection
  - Repair history tracking
  - Issue catalogue completeness
  - Fix step execution
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.ultimate_repair import UltimateRepairModule, RepairSeverity


class TestMajorRepair(unittest.TestCase):
    """Test major system issue repair (bootloop, memory corruption, EDL, BROM)."""

    def setUp(self):
        self.ur = UltimateRepairModule()

    # ── Bootloop repair ────────────────────────────────────────────── #

    def test_repair_bootloop(self):
        result = self.ur.repair_major_system_issues("TestDevice", "bootloop")
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["repair_type"], "MAJOR")
        self.assertEqual(result["issues_found"], 1)
        self.assertEqual(result["issues_resolved"], 1)
        self.assertEqual(result["results"][0]["issue"], "bootloop")
        self.assertEqual(result["results"][0]["severity"], "CRITICAL")

    def test_bootloop_fix_steps_count(self):
        result = self.ur.repair_major_system_issues("TestDevice", "bootloop")
        steps = result["results"][0]["details"]
        self.assertEqual(len(steps), 5)
        for step in steps:
            self.assertEqual(step["status"], "EXECUTED")

    # ── Memory corruption repair ───────────────────────────────────── #

    def test_repair_memory_corruption(self):
        result = self.ur.repair_major_system_issues("TestDevice", "memory_corruption")
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["results"][0]["issue"], "memory_corruption")
        self.assertEqual(result["results"][0]["severity"], "CRITICAL")

    # ── EDL boot failure repair ────────────────────────────────────── #

    def test_repair_boot_failure_edl(self):
        result = self.ur.repair_major_system_issues("TestDevice", "boot_failure_edl")
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["results"][0]["severity"], "MAJOR")

    def test_edl_fix_includes_sahara(self):
        result = self.ur.repair_major_system_issues("TestDevice", "boot_failure_edl")
        steps = [s["description"] for s in result["results"][0]["details"]]
        self.assertTrue(any("Sahara" in s or "EDL" in s for s in steps))

    # ── BROM boot failure repair ───────────────────────────────────── #

    def test_repair_boot_failure_brom(self):
        result = self.ur.repair_major_system_issues("TestDevice", "boot_failure_brom")
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["results"][0]["severity"], "MAJOR")

    def test_brom_fix_includes_scatter(self):
        result = self.ur.repair_major_system_issues("TestDevice", "boot_failure_brom")
        steps = [s["description"] for s in result["results"][0]["details"]]
        self.assertTrue(any("scatter" in s.lower() or "BROM" in s for s in steps))

    # ── Fastboot stuck repair ──────────────────────────────────────── #

    def test_repair_fastboot_stuck(self):
        result = self.ur.repair_major_system_issues("TestDevice", "fastboot_stuck")
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["results"][0]["issue"], "fastboot_stuck")

    # ── Dead screen repair ─────────────────────────────────────────── #

    def test_repair_dead_screen(self):
        result = self.ur.repair_major_system_issues("TestDevice", "dead_screen")
        self.assertEqual(result["status"], "COMPLETED")

    # ── Baseband lost repair ───────────────────────────────────────── #

    def test_repair_baseband_lost(self):
        result = self.ur.repair_major_system_issues("TestDevice", "baseband_lost")
        self.assertEqual(result["status"], "COMPLETED")
        steps = [s["description"] for s in result["results"][0]["details"]]
        self.assertTrue(any("EFS" in s or "IMEI" in s for s in steps))

    # ── Auto-detection (no issue_key) ──────────────────────────────── #

    def test_auto_detect_major_issues(self):
        result = self.ur.repair_major_system_issues("TestDevice")
        self.assertEqual(result["status"], "COMPLETED")
        self.assertGreaterEqual(result["issues_found"], 1)

    # ── Invalid issue key ──────────────────────────────────────────── #

    def test_invalid_issue_key_returns_empty(self):
        result = self.ur.repair_major_system_issues("TestDevice", "nonexistent_issue")
        self.assertEqual(result["issues_found"], 0)

    # ── Device ID preserved ────────────────────────────────────────── #

    def test_device_id_preserved(self):
        result = self.ur.repair_major_system_issues("MyDevice_001", "bootloop")
        self.assertEqual(result["device_id"], "MyDevice_001")


class TestMinorRepair(unittest.TestCase):
    """Test minor system issue repair (apps, Wi-Fi, Bluetooth, power)."""

    def setUp(self):
        self.ur = UltimateRepairModule()

    # ── App crash repair ───────────────────────────────────────────── #

    def test_repair_app_crash(self):
        result = self.ur.repair_minor_system_issues("TestDevice", "app_crash")
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["repair_type"], "MINOR")
        self.assertEqual(result["results"][0]["issue"], "app_crash")

    def test_app_crash_fix_steps(self):
        result = self.ur.repair_minor_system_issues("TestDevice", "app_crash")
        steps = [s["description"] for s in result["results"][0]["details"]]
        self.assertTrue(any("cache" in s.lower() for s in steps))

    # ── Wi-Fi repair ───────────────────────────────────────────────── #

    def test_repair_wifi_failure(self):
        result = self.ur.repair_minor_system_issues("TestDevice", "wifi_failure")
        self.assertEqual(result["status"], "COMPLETED")

    # ── Bluetooth repair ───────────────────────────────────────────── #

    def test_repair_bluetooth(self):
        result = self.ur.repair_minor_system_issues("TestDevice", "bluetooth_issue")
        self.assertEqual(result["status"], "COMPLETED")

    # ── GPS repair ─────────────────────────────────────────────────── #

    def test_repair_gps(self):
        result = self.ur.repair_minor_system_issues("TestDevice", "gps_failure")
        self.assertEqual(result["status"], "COMPLETED")

    # ── Touchscreen repair ─────────────────────────────────────────── #

    def test_repair_touchscreen(self):
        result = self.ur.repair_minor_system_issues("TestDevice", "touchscreen_unresponsive")
        self.assertEqual(result["status"], "COMPLETED")

    # ── Power drain repair ─────────────────────────────────────────── #

    def test_repair_power_drain(self):
        result = self.ur.repair_minor_system_issues("TestDevice", "power_drain")
        self.assertEqual(result["status"], "COMPLETED")
        steps = [s["description"] for s in result["results"][0]["details"]]
        self.assertTrue(any("wake lock" in s.lower() or "battery" in s.lower() for s in steps))

    # ── Camera repair ──────────────────────────────────────────────── #

    def test_repair_camera(self):
        result = self.ur.repair_minor_system_issues("TestDevice", "camera_malfunction")
        self.assertEqual(result["status"], "COMPLETED")

    # ── Charging repair ────────────────────────────────────────────── #

    def test_repair_charging(self):
        result = self.ur.repair_minor_system_issues("TestDevice", "charging_error")
        self.assertEqual(result["status"], "COMPLETED")

    # ── Audio repair ───────────────────────────────────────────────── #

    def test_repair_audio(self):
        result = self.ur.repair_minor_system_issues("TestDevice", "audio_distortion")
        self.assertEqual(result["status"], "COMPLETED")

    # ── Auto-detection ─────────────────────────────────────────────── #

    def test_auto_detect_minor_issues(self):
        result = self.ur.repair_minor_system_issues("TestDevice")
        self.assertEqual(result["status"], "COMPLETED")
        self.assertGreaterEqual(result["issues_found"], 1)

    # ── Multiple minor issues ──────────────────────────────────────── #

    def test_repair_multiple_minor_issues(self):
        # Auto-detect should find app_crash and wifi_failure by default
        result = self.ur.repair_minor_system_issues("TestDevice")
        self.assertGreaterEqual(result["issues_found"], 2)


class TestCloudSyncRepair(unittest.TestCase):
    """Test cloud/account sync loop repair for all platforms."""

    def setUp(self):
        self.ur = UltimateRepairModule()

    # ── Samsung account ────────────────────────────────────────────── #

    def test_repair_samsung_cloud(self):
        result = self.ur.repair_cloud_and_account_sync("Samsung_Galaxy_S23", "samsung")
        self.assertEqual(result["status"], "RESOLVED")
        self.assertEqual(result["repair_type"], "CLOUD_SYNC")
        self.assertEqual(result["platform_detected"], "samsung")
        self.assertEqual(result["issue"], "samsung_account_loop")

    def test_samsung_cloud_fix_steps(self):
        result = self.ur.repair_cloud_and_account_sync("Samsung_Galaxy_S23", "samsung")
        steps = [s["description"] for s in result["details"]]
        self.assertTrue(any("Odin" in s or "EDL" in s or "Samsung" in s for s in steps))

    # ── Apple iCloud ───────────────────────────────────────────────── #

    def test_repair_apple_icloud(self):
        result = self.ur.repair_cloud_and_account_sync("iPhone_15_Pro", "apple")
        self.assertEqual(result["status"], "RESOLVED")
        self.assertEqual(result["platform_detected"], "apple")
        self.assertEqual(result["issue"], "apple_icloud_lock")

    def test_apple_icloud_ethical_note(self):
        result = self.ur.repair_cloud_and_account_sync("iPhone_15_Pro", "apple")
        steps = [s["description"] for s in result["details"]]
        self.assertTrue(any("ethical" in s.lower() or "Apple Support" in s or "iforgot" in s for s in steps))

    # ── Xiaomi Mi Account ──────────────────────────────────────────── #

    def test_repair_xiaomi_cloud(self):
        result = self.ur.repair_cloud_and_account_sync("Xiaomi_13_Pro", "xiaomi")
        self.assertEqual(result["status"], "RESOLVED")
        self.assertEqual(result["issue"], "xiaomi_mi_account")

    # ── Huawei ID ──────────────────────────────────────────────────── #

    def test_repair_huawei_cloud(self):
        result = self.ur.repair_cloud_and_account_sync("Huawei_P50_Pro", "huawei")
        self.assertEqual(result["status"], "RESOLVED")
        self.assertEqual(result["issue"], "huawei_id_lock")

    # ── Google FRP ─────────────────────────────────────────────────── #

    def test_repair_google_cloud(self):
        result = self.ur.repair_cloud_and_account_sync("Pixel_8_Pro", "google")
        self.assertEqual(result["status"], "RESOLVED")
        self.assertEqual(result["issue"], "google_account_loop")

    # ── Generic FRP (unknown platform) ─────────────────────────────── #

    def test_generic_frp_fallback(self):
        result = self.ur.repair_cloud_and_account_sync("Generic_Device", "generic_brand")
        self.assertEqual(result["status"], "RESOLVED")
        self.assertEqual(result["issue"], "generic_frp")

    # ── Auto-detect platform from device_id ────────────────────────── #

    def test_auto_detect_samsung_platform(self):
        result = self.ur.repair_cloud_and_account_sync("Samsung_Galaxy_S23")
        self.assertEqual(result["platform_detected"], "samsung")

    def test_auto_detect_apple_platform(self):
        result = self.ur.repair_cloud_and_account_sync("iPhone_15_Pro")
        self.assertEqual(result["platform_detected"], "apple")

    def test_auto_detect_xiaomi_platform(self):
        result = self.ur.repair_cloud_and_account_sync("Xiaomi_Redmi_Note_12")
        self.assertEqual(result["platform_detected"], "xiaomi")

    def test_auto_detect_huawei_platform(self):
        result = self.ur.repair_cloud_and_account_sync("Huawei_Mate_40_Pro")
        self.assertEqual(result["platform_detected"], "huawei")

    def test_auto_detect_google_platform(self):
        result = self.ur.repair_cloud_and_account_sync("Google_Pixel_8")
        self.assertEqual(result["platform_detected"], "google")


class TestFullDiagnostic(unittest.TestCase):
    """Test full system diagnostic pipeline."""

    def setUp(self):
        self.ur = UltimateRepairModule()

    def test_full_diagnostic_structure(self):
        result = self.ur.full_system_diagnostic("TestDevice")
        self.assertIn("major_repairs", result)
        self.assertIn("minor_repairs", result)
        self.assertIn("cloud_repairs", result)
        self.assertEqual(result["overall_status"], "COMPLETED")

    def test_full_diagnostic_all_repair_types(self):
        result = self.ur.full_system_diagnostic("TestDevice")
        self.assertEqual(result["major_repairs"]["repair_type"], "MAJOR")
        self.assertEqual(result["minor_repairs"]["repair_type"], "MINOR")
        self.assertEqual(result["cloud_repairs"]["repair_type"], "CLOUD_SYNC")

    def test_full_diagnostic_device_id(self):
        result = self.ur.full_system_diagnostic("MyPhone_001")
        self.assertEqual(result["device_id"], "MyPhone_001")


class TestRepairHistory(unittest.TestCase):
    """Test repair history tracking."""

    def setUp(self):
        self.ur = UltimateRepairModule()

    def test_history_starts_empty(self):
        self.assertEqual(len(self.ur.get_repair_history()), 0)

    def test_major_repair_recorded(self):
        self.ur.repair_major_system_issues("Device1", "bootloop")
        history = self.ur.get_repair_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["repair_type"], "MAJOR")

    def test_minor_repair_recorded(self):
        self.ur.repair_minor_system_issues("Device2", "app_crash")
        history = self.ur.get_repair_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["repair_type"], "MINOR")

    def test_cloud_repair_recorded(self):
        self.ur.repair_cloud_and_account_sync("Device3", "samsung")
        history = self.ur.get_repair_history()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["repair_type"], "CLOUD_SYNC")

    def test_multiple_repairs_accumulate(self):
        self.ur.repair_major_system_issues("D1", "bootloop")
        self.ur.repair_minor_system_issues("D2", "wifi_failure")
        self.ur.repair_cloud_and_account_sync("D3", "apple")
        self.assertEqual(len(self.ur.get_repair_history()), 3)

    def test_full_diagnostic_recorded(self):
        self.ur.full_system_diagnostic("DeviceX")
        # full_diagnostic calls 3 internal repairs, each recorded
        self.assertEqual(len(self.ur.get_repair_history()), 3)


class TestIssueCatalogue(unittest.TestCase):
    """Test the issue catalogue completeness."""

    def setUp(self):
        self.ur = UltimateRepairModule()

    def test_supported_issues_structure(self):
        issues = self.ur.get_supported_issues()
        self.assertIn("major_issues", issues)
        self.assertIn("minor_issues", issues)
        self.assertIn("cloud_sync_issues", issues)

    def test_major_issues_count(self):
        issues = self.ur.get_supported_issues()
        self.assertGreaterEqual(len(issues["major_issues"]), 6)

    def test_minor_issues_count(self):
        issues = self.ur.get_supported_issues()
        self.assertGreaterEqual(len(issues["minor_issues"]), 8)

    def test_cloud_sync_issues_count(self):
        issues = self.ur.get_supported_issues()
        self.assertGreaterEqual(len(issues["cloud_sync_issues"]), 5)

    def test_bootloop_in_major_issues(self):
        issues = self.ur.get_supported_issues()
        self.assertIn("bootloop", issues["major_issues"])

    def test_app_crash_in_minor_issues(self):
        issues = self.ur.get_supported_issues()
        self.assertIn("app_crash", issues["minor_issues"])

    def test_google_account_in_cloud_issues(self):
        issues = self.ur.get_supported_issues()
        self.assertIn("google_account_loop", issues["cloud_sync_issues"])


class TestRepairSeverity(unittest.TestCase):
    """Test severity enum usage in repair results."""

    def setUp(self):
        self.ur = UltimateRepairModule()

    def test_bootloop_is_critical(self):
        result = self.ur.repair_major_system_issues("D", "bootloop")
        self.assertEqual(result["results"][0]["severity"], "CRITICAL")

    def test_memory_corruption_is_critical(self):
        result = self.ur.repair_major_system_issues("D", "memory_corruption")
        self.assertEqual(result["results"][0]["severity"], "CRITICAL")

    def test_edl_is_major(self):
        result = self.ur.repair_major_system_issues("D", "boot_failure_edl")
        self.assertEqual(result["results"][0]["severity"], "MAJOR")

    def test_brom_is_major(self):
        result = self.ur.repair_major_system_issues("D", "boot_failure_brom")
        self.assertEqual(result["results"][0]["severity"], "MAJOR")


class TestFixStepExecution(unittest.TestCase):
    """Test that fix steps execute with correct structure."""

    def setUp(self):
        self.ur = UltimateRepairModule()

    def test_fix_steps_have_step_number(self):
        result = self.ur.repair_major_system_issues("D", "bootloop")
        for step in result["results"][0]["details"]:
            self.assertIn("step", step)
            self.assertIn("description", step)
            self.assertIn("status", step)

    def test_fix_steps_sequential(self):
        result = self.ur.repair_major_system_issues("D", "bootloop")
        steps = result["results"][0]["details"]
        for i, step in enumerate(steps, 1):
            self.assertEqual(step["step"], i)

    def test_fix_steps_all_executed(self):
        result = self.ur.repair_major_system_issues("D", "bootloop")
        for step in result["results"][0]["details"]:
            self.assertEqual(step["status"], "EXECUTED")

    def test_steps_count_matches_catalogue(self):
        # Bootloop should have 5 fix steps
        result = self.ur.repair_major_system_issues("D", "bootloop")
        self.assertEqual(len(result["results"][0]["details"]),
                         len(self.ur.MAJOR_ISSUES["bootloop"]["fix_steps"]))


if __name__ == "__main__":
    unittest.main()
