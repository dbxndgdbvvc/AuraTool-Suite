"""
Unit Tests — HWID-Based License Manager
=========================================
Tests cover:
  - HWID generation and stability
  - Key generation and verification
  - License activation (all tiers)
  - Encrypted persistence (save/load/HMAC integrity)
  - Anti-clock-rollback detection
  - Feature gating per tier
  - Expiration enforcement
  - Tamper detection (HWID mismatch, file corruption)
"""

import datetime
import json
import os
import shutil
import tempfile
import time
import unittest

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.license_manager import (
    LicenseManager,
    LicenseTier,
    HWIDCollector,
    TIER_CONFIG,
)


class TestHWIDCollector(unittest.TestCase):
    """Test hardware fingerprint generation."""

    def test_collect_returns_hex_string(self):
        hwid = HWIDCollector.collect()
        self.assertIsInstance(hwid, str)
        self.assertEqual(len(hwid), 64)  # SHA-256 hex digest
        self.assertTrue(all(c in "0123456789abcdef" for c in hwid))

    def test_collect_is_deterministic(self):
        hwid1 = HWIDCollector.collect()
        hwid2 = HWIDCollector.collect()
        self.assertEqual(hwid1, hwid2)

    def test_collect_not_empty(self):
        hwid = HWIDCollector.collect()
        self.assertNotEqual(hwid, "")


class TestKeyGeneration(unittest.TestCase):
    """Test license key generation for all tiers."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mgr = LicenseManager(data_dir=self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_generate_trial_key(self):
        key = self.mgr.generate_key(LicenseTier.TRIAL_15_DAYS)
        self.assertTrue(key.startswith("AT15-"))
        self.assertEqual(len(key), 17)  # AT15- + 12 hex chars

    def test_generate_6month_key(self):
        key = self.mgr.generate_key(LicenseTier.RENTAL_6_MONTHS)
        self.assertTrue(key.startswith("AT6M-"))

    def test_generate_1year_key(self):
        key = self.mgr.generate_key(LicenseTier.RENTAL_1_YEAR)
        self.assertTrue(key.startswith("AT1Y-"))

    def test_generated_key_is_valid(self):
        key = self.mgr.generate_key(LicenseTier.TRIAL_15_DAYS)
        result = self.mgr.activate(key)
        self.assertTrue(result["success"])

    def test_generate_invalid_tier_raises(self):
        with self.assertRaises(ValueError):
            self.mgr.generate_key(LicenseTier.EXPIRED)


class TestLicenseActivation(unittest.TestCase):
    """Test license key activation and tier assignment."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mgr = LicenseManager(data_dir=self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_activate_trial_key(self):
        key = self.mgr.generate_key(LicenseTier.TRIAL_15_DAYS)
        result = self.mgr.activate(key)
        self.assertTrue(result["success"])
        self.assertEqual(self.mgr.tier, LicenseTier.TRIAL_15_DAYS)

    def test_activate_6month_key(self):
        key = self.mgr.generate_key(LicenseTier.RENTAL_6_MONTHS)
        result = self.mgr.activate(key)
        self.assertTrue(result["success"])
        self.assertEqual(self.mgr.tier, LicenseTier.RENTAL_6_MONTHS)

    def test_activate_1year_key(self):
        key = self.mgr.generate_key(LicenseTier.RENTAL_1_YEAR)
        result = self.mgr.activate(key)
        self.assertTrue(result["success"])
        self.assertEqual(self.mgr.tier, LicenseTier.RENTAL_1_YEAR)

    def test_activate_invalid_key(self):
        result = self.mgr.activate("INVALID-KEY-123")
        self.assertFalse(result["success"])

    def test_activate_empty_key(self):
        result = self.mgr.activate("")
        self.assertFalse(result["success"])

    def test_activate_tampered_key(self):
        result = self.mgr.activate("AT15-000000000000")
        self.assertFalse(result["success"])

    def test_activation_sets_date(self):
        key = self.mgr.generate_key(LicenseTier.TRIAL_15_DAYS)
        self.mgr.activate(key)
        self.assertEqual(self.mgr.activation_date, datetime.date.today())


class TestLicenseCheck(unittest.TestCase):
    """Test license status checking."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mgr = LicenseManager(data_dir=self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_fresh_install_is_expired(self):
        status = self.mgr.check_license()
        self.assertFalse(status["is_active"])
        self.assertEqual(status["tier"], "expired")

    def test_trial_is_active_after_activation(self):
        key = self.mgr.generate_key(LicenseTier.TRIAL_15_DAYS)
        self.mgr.activate(key)
        status = self.mgr.check_license()
        self.assertTrue(status["is_active"])
        self.assertEqual(status["days_remaining"], 15)

    def test_6month_is_active(self):
        key = self.mgr.generate_key(LicenseTier.RENTAL_6_MONTHS)
        self.mgr.activate(key)
        status = self.mgr.check_license()
        self.assertTrue(status["is_active"])
        self.assertGreater(status["days_remaining"], 170)

    def test_1year_is_active(self):
        key = self.mgr.generate_key(LicenseTier.RENTAL_1_YEAR)
        self.mgr.activate(key)
        status = self.mgr.check_license()
        self.assertTrue(status["is_active"])
        self.assertGreater(status["days_remaining"], 360)

    def test_status_contains_hwid(self):
        key = self.mgr.generate_key(LicenseTier.TRIAL_15_DAYS)
        self.mgr.activate(key)
        status = self.mgr.check_license()
        self.assertIn("hwid", status)
        self.assertEqual(len(status["hwid"]), 64)

    def test_status_contains_features(self):
        key = self.mgr.generate_key(LicenseTier.RENTAL_1_YEAR)
        self.mgr.activate(key)
        status = self.mgr.check_license()
        self.assertIn("features", status)
        self.assertGreater(len(status["features"]), 0)


class TestEncryptedPersistence(unittest.TestCase):
    """Test that license state persists across instances with encryption."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_license_persists_across_instances(self):
        # Activate in first instance
        mgr1 = LicenseManager(data_dir=self.tmp)
        key = mgr1.generate_key(LicenseTier.RENTAL_6_MONTHS)
        mgr1.activate(key)

        # Load in second instance
        mgr2 = LicenseManager(data_dir=self.tmp)
        self.assertEqual(mgr2.tier, LicenseTier.RENTAL_6_MONTHS)
        self.assertEqual(mgr2.license_key, key)

    def test_encrypted_file_exists(self):
        mgr = LicenseManager(data_dir=self.tmp)
        key = mgr.generate_key(LicenseTier.TRIAL_15_DAYS)
        mgr.activate(key)

        self.assertTrue(os.path.exists(os.path.join(self.tmp, "license.enc")))
        self.assertTrue(os.path.exists(os.path.join(self.tmp, "license.sig")))

    def test_encrypted_file_not_json(self):
        mgr = LicenseManager(data_dir=self.tmp)
        key = mgr.generate_key(LicenseTier.TRIAL_15_DAYS)
        mgr.activate(key)

        enc_path = os.path.join(self.tmp, "license.enc")
        with open(enc_path, "r", errors="ignore") as f:
            content = f.read()
        # Should NOT be readable as plain JSON
        try:
            json.loads(content)
            self.fail("Encrypted file should not be valid JSON")
        except (json.JSONDecodeError, ValueError):
            pass  # Expected — it's encrypted


class TestAntiTamper(unittest.TestCase):
    """Test tamper detection mechanisms."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_tampered_encrypted_file_detected(self):
        mgr = LicenseManager(data_dir=self.tmp)
        key = mgr.generate_key(LicenseTier.TRIAL_15_DAYS)
        mgr.activate(key)

        # Tamper with the encrypted file
        enc_path = os.path.join(self.tmp, "license.enc")
        with open(enc_path, "ab") as f:
            f.write(b"TAMPERED")

        # New instance should detect tampering
        mgr2 = LicenseManager(data_dir=self.tmp)
        status = mgr2.check_license()
        self.assertFalse(status["is_active"])

    def test_tampered_signature_detected(self):
        mgr = LicenseManager(data_dir=self.tmp)
        key = mgr.generate_key(LicenseTier.TRIAL_15_DAYS)
        mgr.activate(key)

        # Tamper with signature
        sig_path = os.path.join(self.tmp, "license.sig")
        with open(sig_path, "w") as f:
            f.write("0" * 64)

        mgr2 = LicenseManager(data_dir=self.tmp)
        status = mgr2.check_license()
        self.assertFalse(status["is_active"])

    def test_wrong_hwid_rejects_license(self):
        # Simulate HWID mismatch by corrupting the hwid field inside the encrypted file
        mgr1 = LicenseManager(data_dir=self.tmp)
        key = mgr1.generate_key(LicenseTier.TRIAL_15_DAYS)
        mgr1.activate(key)

        # Tamper the hwid inside the encrypted payload
        # Re-encrypt with a different HWID to simulate a different machine
        import core.license_manager as lm_mod
        original_collect = lm_mod.HWIDCollector.collect
        lm_mod.HWIDCollector.collect = lambda: "a" * 64

        try:
            # Create a new manager with a different simulated HWID
            mgr_fake = LicenseManager(data_dir=self.tmp)
            # The load should fail because the HWID stored in the file
            # doesn't match the new fake HWID
            status = mgr_fake.check_license()
            self.assertFalse(status["is_active"])
        finally:
            lm_mod.HWIDCollector.collect = original_collect


class TestFeatureGating(unittest.TestCase):
    """Test feature access per tier."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mgr = LicenseManager(data_dir=self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_trial_has_basic_features(self):
        key = self.mgr.generate_key(LicenseTier.TRIAL_15_DAYS)
        self.mgr.activate(key)
        self.assertTrue(self.mgr.has_feature("basic_diagnostics"))
        self.assertTrue(self.mgr.has_feature("log_analysis"))
        self.assertFalse(self.mgr.has_feature("ai_assistant"))

    def test_6month_has_ai_features(self):
        key = self.mgr.generate_key(LicenseTier.RENTAL_6_MONTHS)
        self.mgr.activate(key)
        self.assertTrue(self.mgr.has_feature("ai_assistant"))
        self.assertTrue(self.mgr.has_feature("data_recovery"))
        self.assertFalse(self.mgr.has_feature("vip_cloud_vault"))

    def test_1year_has_all_features(self):
        key = self.mgr.generate_key(LicenseTier.RENTAL_1_YEAR)
        self.mgr.activate(key)
        self.assertTrue(self.mgr.has_feature("vip_cloud_vault"))
        self.assertTrue(self.mgr.has_feature("priority_support"))
        self.assertTrue(self.mgr.has_feature("continuous_updates_2030"))

    def test_expired_has_no_features(self):
        self.assertFalse(self.mgr.has_feature("basic_diagnostics"))


class TestExpiration(unittest.TestCase):
    """Test license expiration behavior."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_trial_expires_after_15_days(self):
        mgr = LicenseManager(data_dir=self.tmp)
        key = mgr.generate_key(LicenseTier.TRIAL_15_DAYS)
        mgr.activate(key)

        # Simulate 16 days in the future
        mgr.activation_date = datetime.date.today() - datetime.timedelta(days=16)
        mgr._save_license()

        # Reload and check
        mgr2 = LicenseManager(data_dir=self.tmp)
        status = mgr2.check_license()
        self.assertFalse(status["is_active"])
        self.assertEqual(status["days_remaining"], 0)

    def test_6month_expires_after_182_days(self):
        mgr = LicenseManager(data_dir=self.tmp)
        key = mgr.generate_key(LicenseTier.RENTAL_6_MONTHS)
        mgr.activate(key)

        mgr.activation_date = datetime.date.today() - datetime.timedelta(days=183)
        mgr._save_license()

        mgr2 = LicenseManager(data_dir=self.tmp)
        status = mgr2.check_license()
        self.assertFalse(status["is_active"])

    def test_expired_license_auto_sets_tier(self):
        mgr = LicenseManager(data_dir=self.tmp)
        key = mgr.generate_key(LicenseTier.TRIAL_15_DAYS)
        mgr.activate(key)

        mgr.activation_date = datetime.date.today() - datetime.timedelta(days=20)
        mgr._save_license()

        mgr2 = LicenseManager(data_dir=self.tmp)
        mgr2.check_license()
        self.assertEqual(mgr2.tier, LicenseTier.EXPIRED)


class TestDeactivation(unittest.TestCase):
    """Test license deactivation."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mgr = LicenseManager(data_dir=self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_deactivate_clears_license(self):
        key = self.mgr.generate_key(LicenseTier.RENTAL_1_YEAR)
        self.mgr.activate(key)
        self.mgr.deactivate()

        status = self.mgr.check_license()
        self.assertFalse(status["is_active"])
        self.assertEqual(self.mgr.tier, LicenseTier.EXPIRED)

    def test_deactivate_persists(self):
        key = self.mgr.generate_key(LicenseTier.TRIAL_15_DAYS)
        self.mgr.activate(key)
        self.mgr.deactivate()

        mgr2 = LicenseManager(data_dir=self.tmp)
        status = mgr2.check_license()
        self.assertFalse(status["is_active"])


class TestAllTiers(unittest.TestCase):
    """Test get_all_tiers utility."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mgr = LicenseManager(data_dir=self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_all_tiers_returns_dict(self):
        tiers = self.mgr.get_all_tiers()
        self.assertIn("trial_15d", tiers)
        self.assertIn("rental_6m", tiers)
        self.assertIn("rental_1y", tiers)
        self.assertEqual(len(tiers), 3)  # 3 active tiers (expired excluded)

    def test_tier_config_matches(self):
        tiers = self.mgr.get_all_tiers()
        self.assertEqual(tiers["trial_15d"]["days"], 15)
        self.assertEqual(tiers["rental_6m"]["days"], 182)
        self.assertEqual(tiers["rental_1y"]["days"], 365)


class TestClockRollback(unittest.TestCase):
    """Test anti-clock-rollback protection."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_clock_rollback_detected(self):
        mgr = LicenseManager(data_dir=self.tmp)
        key = mgr.generate_key(LicenseTier.TRIAL_15_DAYS)
        mgr.activate(key)

        # Simulate a future time was recorded
        mgr._last_known_time = time.time() + 7200  # 2 hours ahead
        mgr._save_license()

        # Reload — current time is "behind" last known time
        mgr2 = LicenseManager(data_dir=self.tmp)
        status = mgr2.check_license()
        self.assertFalse(status["is_active"])
        self.assertIn("clock", status["error"].lower())


if __name__ == "__main__":
    unittest.main()
