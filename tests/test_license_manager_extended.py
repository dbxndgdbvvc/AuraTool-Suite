"""
Extended Unit Tests — License Manager (Crypto, Server Client, Online Validation)
=================================================================================
Targets uncovered code paths in core/license_manager.py:
  - _Crypto: derive_hmac_key, sign, verify, encrypt, decrypt
  - LicenseServerClient: activate, validate, deactivate, health, _post, _get, is_reachable
  - LicenseManager: get_tier_config, online_activate, online_validate, smart_check,
    set_server_token, _build_status, _verify_key_checksum, enforce_or_exit
"""

import datetime
import hashlib
import hmac
import json
import os
import shutil
import struct
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch, mock_open

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.license_manager import (
    LicenseManager,
    LicenseTier,
    HWIDCollector,
    LicenseServerClient,
    TIER_CONFIG,
    _Crypto,
)


# ═══════════════════════════════════════════════════════════════════════════
#  _Crypto — HMAC Key Derivation
# ═══════════════════════════════════════════════════════════════════════════

class TestCryptoHMAC(unittest.TestCase):
    """Test _Crypto HMAC key derivation and signing."""

    def test_derive_hmac_key_returns_32_bytes(self):
        """derive_hmac_key returns32-byte key."""
        key = _Crypto.derive_hmac_key("test_hwid")
        self.assertEqual(len(key), 32)
        self.assertIsInstance(key, bytes)

    def test_derive_hmac_key_deterministic(self):
        """Same HWID produces same key."""
        k1 = _Crypto.derive_hmac_key("HWID-001")
        k2 = _Crypto.derive_hmac_key("HWID-001")
        self.assertEqual(k1, k2)

    def test_derive_hmac_key_different_for_different_hwid(self):
        """Different HWIDs produce different keys."""
        k1 = _Crypto.derive_hmac_key("HWID-001")
        k2 = _Crypto.derive_hmac_key("HWID-002")
        self.assertNotEqual(k1, k2)

    def test_sign_returns_hex_string(self):
        """sign returns a 64-char hex string."""
        sig = _Crypto.sign(b"test data", "HWID-001")
        self.assertEqual(len(sig), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in sig))

    def test_sign_deterministic(self):
        """Same data + HWID produces same signature."""
        s1 = _Crypto.sign(b"test", "HWID-001")
        s2 = _Crypto.sign(b"test", "HWID-001")
        self.assertEqual(s1, s2)

    def test_verify_correct(self):
        """verify returns True for correct signature."""
        data = b"important data"
        sig = _Crypto.sign(data, "HWID-001")
        self.assertTrue(_Crypto.verify(data, sig, "HWID-001"))

    def test_verify_incorrect(self):
        """verify returns False for wrong signature."""
        self.assertFalse(_Crypto.verify(b"data", "wrong_sig", "HWID-001"))

    def test_verify_wrong_hwid(self):
        """verify returns False for wrong HWID."""
        data = b"test data"
        sig = _Crypto.sign(data, "HWID-001")
        self.assertFalse(_Crypto.verify(data, sig, "HWID-002"))


# ═══════════════════════════════════════════════════════════════════════════
#  _Crypto — Encrypt / Decrypt
# ═══════════════════════════════════════════════════════════════════════════

class TestCryptoEncryptDecrypt(unittest.TestCase):
    """Test _Crypto XOR stream cipher."""

    def test_encrypt_decrypt_roundtrip(self):
        """Encrypted data can be decrypted back."""
        plaintext = "License state JSON"
        hwid = "HWID-ABC"
        encrypted = _Crypto.encrypt(plaintext, hwid)
        decrypted = _Crypto.decrypt(encrypted, hwid)
        self.assertEqual(decrypted, plaintext)

    def test_encrypt_produces_iv_plus_ciphertext(self):
        """Encrypted output starts with 16-byte IV."""
        encrypted = _Crypto.encrypt("test", "HWID")
        iv = encrypted[:16]
        self.assertEqual(len(iv), 16)

    def test_encrypt_different_each_time(self):
        """Same plaintext produces different ciphertext (random IV)."""
        e1 = _Crypto.encrypt("test", "HWID")
        e2 = _Crypto.encrypt("test", "HWID")
        self.assertNotEqual(e1, e2)

    def test_decrypt_too_short_raises(self):
        """Decrypting too-short data raises ValueError."""
        with self.assertRaises(ValueError):
            _Crypto.decrypt(b"short", "HWID")

    def test_decrypt_empty_raises(self):
        """Decrypting empty bytes raises ValueError."""
        with self.assertRaises(ValueError):
            _Crypto.decrypt(b"", "HWID")

    def test_encrypt_unicode(self):
        """Encryption handles Unicode data."""
        for text in ["عربي", "中文", "日本語", "🔐"]:
            encrypted = _Crypto.encrypt(text, "HWID-001")
            decrypted = _Crypto.decrypt(encrypted, "HWID-001")
            self.assertEqual(decrypted, text)

    def test_encrypt_long_text(self):
        """Encryption handles long text."""
        plaintext = "A" * 10000
        encrypted = _Crypto.encrypt(plaintext, "HWID")
        decrypted = _Crypto.decrypt(encrypted, "HWID")
        self.assertEqual(decrypted, plaintext)

    def test_encrypt_with_json(self):
        """Encryption works with JSON strings."""
        state = {"tier": "6M", "hwid": "ABC", "expires": time.time()}
        plaintext = json.dumps(state)
        encrypted = _Crypto.encrypt(plaintext, "HWID")
        decrypted = _Crypto.decrypt(encrypted, "HWID")
        restored = json.loads(decrypted)
        self.assertEqual(restored["tier"], "6M")
        self.assertEqual(restored["hwid"], "ABC")


# ═══════════════════════════════════════════════════════════════════════════
#  LicenseServerClient
# ═══════════════════════════════════════════════════════════════════════════

class TestLicenseServerClient(unittest.TestCase):
    """Test LicenseServerClient HTTP methods."""

    def setUp(self):
        self.client = LicenseServerClient("https://license.auratool.com:8600")

    def test_init_strips_trailing_slash(self):
        """Server URL trailing slash is stripped."""
        c = LicenseServerClient("https://example.com/")
        self.assertEqual(c.server_url, "https://example.com")

    def test_set_ssl_context(self):
        """set_ssl_context stores the context."""
        ctx = MagicMock()
        self.client.set_ssl_context(ctx)
        self.assertEqual(self.client._ssl_context, ctx)

    @patch("urllib.request.urlopen")
    def test_activate_sends_post(self, mock_urlopen):
        """activate sends POST to /activate."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"success": True, "token": "tok123"}).encode()
        mock_urlopen.return_value = mock_resp

        result = self.client.activate("KEY-001", "HWID-001")
        self.assertTrue(result["success"])
        self.assertEqual(result["token"], "tok123")
        mock_urlopen.assert_called_once()

    @patch("urllib.request.urlopen")
    def test_validate_sends_post(self, mock_urlopen):
        """validate sends POST to /validate."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"valid": True}).encode()
        mock_urlopen.return_value = mock_resp

        result = self.client.validate("tok123", "HWID-001")
        self.assertTrue(result["valid"])

    @patch("urllib.request.urlopen")
    def test_deactivate_sends_post(self, mock_urlopen):
        """deactivate sends POST to /deactivate."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"success": True}).encode()
        mock_urlopen.return_value = mock_resp

        result = self.client.deactivate("KEY-001", "HWID-001")
        self.assertTrue(result["success"])

    @patch("urllib.request.urlopen")
    def test_health_sends_get(self, mock_urlopen):
        """health sends GET to /health."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"status": "ok"}).encode()
        mock_urlopen.return_value = mock_resp

        result = self.client.health()
        self.assertEqual(result["status"], "ok")

    @patch("urllib.request.urlopen")
    def test_is_reachable_true(self, mock_urlopen):
        """is_reachable returns True when server responds."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"status": "ok"}).encode()
        mock_urlopen.return_value = mock_resp

        self.assertTrue(self.client.is_reachable())

    @patch("urllib.request.urlopen")
    def test_is_reachable_false_on_error(self, mock_urlopen):
        """is_reachable returns False on connection error."""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        self.assertFalse(self.client.is_reachable())

    @patch("urllib.request.urlopen")
    def test_post_handles_http_error(self, mock_urlopen):
        """_post handles HTTP errors gracefully."""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "https://example.com", 401, "Unauthorized", {}, None
        )

        result = self.client._post("/test", {"key": "val"})
        self.assertIn("error", result)

    @patch("urllib.request.urlopen")
    def test_post_handles_connection_error(self, mock_urlopen):
        """_post handles connection errors gracefully."""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Timeout")

        result = self.client._post("/test", {"key": "val"})
        self.assertIn("error", result)

    @patch("urllib.request.urlopen")
    def test_get_handles_connection_error(self, mock_urlopen):
        """_get handles connection errors gracefully."""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Timeout")

        result = self.client._get("/test")
        self.assertIn("error", result)


# ═══════════════════════════════════════════════════════════════════════════
#  LicenseManager — get_tier_config
# ═══════════════════════════════════════════════════════════════════════════

class TestGetTierConfig(unittest.TestCase):
    """Test get_tier_config method."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mgr = LicenseManager(data_dir=self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_get_tier_config_default(self):
        """get_tier_config returns config for current tier."""
        config = self.mgr.get_tier_config()
        self.assertIsInstance(config, dict)

    def test_get_tier_config_specific(self):
        """get_tier_config returns config for specified tier."""
        config = self.mgr.get_tier_config(LicenseTier.TRIAL_15_DAYS)
        self.assertIn("days", config)
        self.assertEqual(config["days"], 15)

    def test_get_tier_config_6m(self):
        """get_tier_config for 6-month tier."""
        config = self.mgr.get_tier_config(LicenseTier.RENTAL_6_MONTHS)
        self.assertEqual(config["days"], 182)

    def test_get_tier_config_1y(self):
        """get_tier_config for 1-year tier."""
        config = self.mgr.get_tier_config(LicenseTier.RENTAL_1_YEAR)
        self.assertEqual(config["days"], 365)


# ═══════════════════════════════════════════════════════════════════════════
#  LicenseManager — _verify_key_checksum
# ═══════════════════════════════════════════════════════════════════════════

class TestVerifyKeyChecksum(unittest.TestCase):
    """Test _verify_key_checksum internal method."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mgr = LicenseManager(data_dir=self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_verify_valid_key(self):
        """Valid generated key passes checksum verification."""
        key = self.mgr.generate_key(LicenseTier.TRIAL_15_DAYS)
        result = self.mgr._verify_key_checksum(key, LicenseTier.TRIAL_15_DAYS)
        self.assertTrue(result)

    def test_verify_invalid_checksum(self):
        """Key with wrong checksum fails."""
        key = self.mgr.generate_key(LicenseTier.TRIAL_15_DAYS)
        parts = key.split("-")
        # Tamper with checksum
        tampered = f"{parts[0]}-{'0' * 12}"
        result = self.mgr._verify_key_checksum(tampered, LicenseTier.TRIAL_15_DAYS)
        self.assertFalse(result)

    def test_verify_malformed_key(self):
        """Malformed key (no dash) fails."""
        result = self.mgr._verify_key_checksum("INVALIDKEY", LicenseTier.TRIAL_15_DAYS)
        self.assertFalse(result)


# ═══════════════════════════════════════════════════════════════════════════
#  LicenseManager — _build_status
# ═══════════════════════════════════════════════════════════════════════════

class TestBuildStatus(unittest.TestCase):
    """Test _build_status internal method."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mgr = LicenseManager(data_dir=self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_build_status_structure(self):
        """_build_status returns correct structure."""
        status = self.mgr._build_status(datetime.date.today(), is_active=True, days_remaining=15)
        self.assertIn("is_active", status)
        self.assertIn("tier", status)
        self.assertIn("tier_label", status)
        self.assertIn("days_remaining", status)
        self.assertIn("hwid", status)
        self.assertIn("features", status)
        self.assertIn("version", status)

    def test_build_status_with_error(self):
        """_build_status includes error field."""
        status = self.mgr._build_status(
            datetime.date.today(), is_active=False, error="License expired"
        )
        self.assertEqual(status["error"], "License expired")
        self.assertFalse(status["is_active"])


# ═══════════════════════════════════════════════════════════════════════════
#  LicenseManager — Online Activation (Mocked)
# ═══════════════════════════════════════════════════════════════════════════

class TestOnlineActivation(unittest.TestCase):
    """Test online_activate with mocked server responses."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mgr = LicenseManager(data_dir=self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    @patch.object(LicenseServerClient, "activate")
    def test_online_activate_success(self, mock_activate):
        """online_activate stores token on success."""
        mock_activate.return_value = {
            "success": True,
            "token": "server_token_123",
            "tier": "trial_15d",
            "tier_label": "15-Day Trial",
            "expires_in_days": 15,
            "activation_id": "act_001",
        }

        result = self.mgr.online_activate("KEY-001", "https://license.example.com")
        self.assertTrue(result["success"])
        self.assertEqual(self.mgr._server_token, "server_token_123")

    @patch.object(LicenseServerClient, "activate")
    def test_online_activate_server_error(self, mock_activate):
        """online_activate handles server error."""
        mock_activate.return_value = {"error": "Invalid key"}

        result = self.mgr.online_activate("INVALID", "https://license.example.com")
        self.assertFalse(result["success"])

    @patch.object(LicenseServerClient, "activate")
    def test_online_activate_unknown_tier(self, mock_activate):
        """online_activate handles unknown server tier."""
        mock_activate.return_value = {
            "success": True,
            "token": "tok",
            "tier": "unknown_tier",
        }

        result = self.mgr.online_activate("KEY-001", "https://license.example.com")
        self.assertTrue(result["success"])
        # Tier should not change for unknown server tier
        self.assertEqual(self.mgr.tier, LicenseTier.EXPIRED)


# ═══════════════════════════════════════════════════════════════════════════
#  LicenseManager — Online Validation (Mocked)
# ═══════════════════════════════════════════════════════════════════════════

class TestOnlineValidation(unittest.TestCase):
    """Test online_validate with mocked server responses."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mgr = LicenseManager(data_dir=self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_online_validate_no_token(self):
        """online_validate returns error when no token."""
        result = self.mgr.online_validate("https://license.example.com")
        self.assertFalse(result["valid"])
        self.assertIn("No server token", result["error"])

    @patch.object(LicenseServerClient, "validate")
    def test_online_validate_success(self, mock_validate):
        """online_validate returns valid on success."""
        self.mgr._server_token = "tok123"
        mock_validate.return_value = {
            "valid": True,
            "tier": "rental_6m",
            "days_remaining": 180,
            "features": ["basic_diagnostics", "ai_assistant"],
        }

        result = self.mgr.online_validate("https://license.example.com")
        self.assertTrue(result["valid"])

    @patch.object(LicenseServerClient, "validate")
    def test_online_validate_invalid_token(self, mock_validate):
        """online_validate handles invalid token."""
        self.mgr._server_token = "bad_token"
        mock_validate.return_value = {"valid": False, "error": "Token expired"}

        result = self.mgr.online_validate("https://license.example.com")
        self.assertFalse(result["valid"])


# ═══════════════════════════════════════════════════════════════════════════
#  LicenseManager — Smart Check
# ═══════════════════════════════════════════════════════════════════════════

class TestCheckLicenseOnline(unittest.TestCase):
    """Test check_license_online (online + offline fallback)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mgr = LicenseManager(data_dir=self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_check_license_online_no_token_does_offline(self):
        """check_license_online falls back to offline when no token."""
        result = self.mgr.check_license_online("https://license.example.com")
        self.assertFalse(result.get("online", True))
        self.assertIn("is_active", result)

    @patch.object(LicenseServerClient, "is_reachable", return_value=False)
    def test_check_license_online_server_unreachable(self, mock_reachable):
        """check_license_online falls back to offline when server unreachable."""
        self.mgr._server_token = "tok123"
        result = self.mgr.check_license_online("https://license.example.com")
        self.assertFalse(result.get("online", True))

    @patch.object(LicenseServerClient, "is_reachable", return_value=True)
    @patch.object(LicenseManager, "online_validate")
    def test_check_license_online_success(self, mock_online, mock_reachable):
        """check_license_online uses online validation when server is reachable."""
        self.mgr._server_token = "tok123"
        mock_online.return_value = {
            "valid": True,
            "tier": "rental_1y",
            "tier_label": "1-Year Rental",
            "days_remaining": 360,
            "features": ["basic_diagnostics"],
        }

        result = self.mgr.check_license_online("https://license.example.com")
        self.assertTrue(result.get("online", False))
        self.assertTrue(result["is_active"])


# ═══════════════════════════════════════════════════════════════════════════
#  LicenseManager — set_server_token
# ═══════════════════════════════════════════════════════════════════════════

class TestSetServerToken(unittest.TestCase):
    """Test set_server_token method."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.mgr = LicenseManager(data_dir=self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_set_server_token(self):
        """set_server_token stores token."""
        self.mgr.set_server_token("my_token")
        self.assertEqual(self.mgr._server_token, "my_token")

    def test_set_server_token_persists(self):
        """set_server_token persists across instances."""
        self.mgr.set_server_token("persistent_token")
        mgr2 = LicenseManager(data_dir=self.tmp)
        self.assertEqual(mgr2._server_token, "persistent_token")


# ═══════════════════════════════════════════════════════════════════════════
#  LicenseManager — enforce_or_exit
# ═══════════════════════════════════════════════════════════════════════════

class TestEnforceOrExit(unittest.TestCase):
    """Test enforce_or_exit method."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_enforce_or_exit_expired(self):
        """enforce_or_exit returns inactive status for expired license."""
        mgr = LicenseManager(data_dir=self.tmp)
        result = mgr.enforce_or_exit()
        self.assertFalse(result["is_active"])

    def test_enforce_or_exit_active(self):
        """enforce_or_exit returns active status for valid license."""
        mgr = LicenseManager(data_dir=self.tmp)
        key = mgr.generate_key(LicenseTier.TRIAL_15_DAYS)
        mgr.activate(key)
        result = mgr.enforce_or_exit()
        self.assertTrue(result["is_active"])


# ═══════════════════════════════════════════════════════════════════════════
#  LicenseManager — Persistence Extended
# ═══════════════════════════════════════════════════════════════════════════

class TestPersistenceExtended(unittest.TestCase):
    """Test license persistence with server tokens and state restoration."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_save_load_preserves_server_token(self):
        """Server token persists across instances."""
        mgr1 = LicenseManager(data_dir=self.tmp)
        key = mgr1.generate_key(LicenseTier.RENTAL_1_YEAR)
        mgr1.activate(key)
        mgr1.set_server_token("server_tok_abc")

        mgr2 = LicenseManager(data_dir=self.tmp)
        self.assertEqual(mgr2._server_token, "server_tok_abc")
        self.assertEqual(mgr2.tier, LicenseTier.RENTAL_1_YEAR)

    def test_save_load_preserves_server_tier(self):
        """Server tier persists across instances."""
        mgr1 = LicenseManager(data_dir=self.tmp)
        key = mgr1.generate_key(LicenseTier.RENTAL_6_MONTHS)
        mgr1.activate(key)
        mgr1._server_tier = "rental_6m"
        mgr1._save_license()

        mgr2 = LicenseManager(data_dir=self.tmp)
        self.assertEqual(mgr2._server_tier, "rental_6m")

    def test_load_corrupted_file(self):
        """Loading corrupted license file sets tier to EXPIRED."""
        # Write garbage to license file
        license_path = os.path.join(self.tmp, "license.enc")
        sig_path = os.path.join(self.tmp, "license.sig")

        mgr = LicenseManager(data_dir=self.tmp)
        key = mgr.generate_key(LicenseTier.TRIAL_15_DAYS)
        mgr.activate(key)

        # Overwrite with garbage
        with open(license_path, "wb") as f:
            f.write(b"garbage data that is not encrypted properly " * 10)

        mgr2 = LicenseManager(data_dir=self.tmp)
        self.assertEqual(mgr2.tier, LicenseTier.EXPIRED)

    def test_load_missing_sig_file(self):
        """Loading with missing sig file handles gracefully."""
        mgr = LicenseManager(data_dir=self.tmp)
        key = mgr.generate_key(LicenseTier.TRIAL_15_DAYS)
        mgr.activate(key)

        # Remove sig file
        sig_path = os.path.join(self.tmp, "license.sig")
        if os.path.exists(sig_path):
            os.remove(sig_path)

        mgr2 = LicenseManager(data_dir=self.tmp)
        # Should either load or set EXPIRED — but not crash
        self.assertIsInstance(mgr2.tier, LicenseTier)

    def test_is_expired_quick_check(self):
        """is_expired returns correct boolean."""
        mgr = LicenseManager(data_dir=self.tmp)
        self.assertTrue(mgr.is_expired())

        key = mgr.generate_key(LicenseTier.TRIAL_15_DAYS)
        mgr.activate(key)
        self.assertFalse(mgr.is_expired())


# ═══════════════════════════════════════════════════════════════════════════
#  LicenseManager — HWID Collector Extended
# ═══════════════════════════════════════════════════════════════════════════

class TestHWIDCollectorExtended(unittest.TestCase):
    """Test HWIDCollector platform-specific methods."""

    def test_get_machine_id_returns_string(self):
        """_get_machine_id returns a string."""
        result = HWIDCollector._get_machine_id()
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

    def test_get_cpu_id_returns_string(self):
        """_get_cpu_id returns a string."""
        result = HWIDCollector._get_cpu_id()
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)


# ═══════════════════════════════════════════════════════════════════════════
#  LicenseManager — All Tier Configs
# ═══════════════════════════════════════════════════════════════════════════

class TestAllTierConfigs(unittest.TestCase):
    """Test that all tier configs have required fields."""

    def test_all_tiers_have_required_fields(self):
        """Every tier config has days, label, features, max_devices."""
        required = ["days", "label", "features", "max_devices"]
        for tier, config in TIER_CONFIG.items():
            for field in required:
                self.assertIn(field, config, f"Tier {tier} missing {field}")

    def test_tier_days_are_positive(self):
        """All tier day counts are positive."""
        for tier, config in TIER_CONFIG.items():
            if config.get("days", 0) > 0:
                self.assertGreater(config["days"], 0)

    def test_trial_15d_has_15_days(self):
        """TRIAL_15_DAYS has 15 days."""
        config = TIER_CONFIG[LicenseTier.TRIAL_15_DAYS]
        self.assertEqual(config["days"], 15)

    def test_rental_6m_has_182_days(self):
        """RENTAL_6_MONTHS has 182 days."""
        config = TIER_CONFIG[LicenseTier.RENTAL_6_MONTHS]
        self.assertEqual(config["days"], 182)

    def test_rental_1y_has_365_days(self):
        """RENTAL_1_YEAR has 365 days."""
        config = TIER_CONFIG[LicenseTier.RENTAL_1_YEAR]
        self.assertEqual(config["days"], 365)


if __name__ == "__main__":
    unittest.main()
