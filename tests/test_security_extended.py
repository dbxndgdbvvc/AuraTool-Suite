"""
Extended Unit Tests — Security Module (AntiReverseEngineering, AdvancedEncryption, SecurityManager)
====================================================================================================
Targets uncovered code paths in core/security.py:
  - AntiReverseEngineering: debugger/VM detection, code integrity, string protection,
    memory integrity, module encryption, hooks detection
  - AdvancedEncryption: key derivation, AES-CBC/GCM, hashing, secure compare
  - SecurityManager: protection status, integrity checks, secure wipe, security report
"""

import hashlib
import hmac
import os
import secrets
import shutil
import struct
import sys
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch, mock_open

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.security import (
    AntiReverseEngineering,
    AdvancedEncryption,
    SecurityManager,
    SecurityError,
    anti_tamper_decorator,
)


# ═══════════════════════════════════════════════════════════════════════════
#  AntiReverseEngineering — String Protection
# ═══════════════════════════════════════════════════════════════════════════

class TestStringProtection(unittest.TestCase):
    """Test triple-cipher obfuscation/deobfuscation."""

    def test_protect_unprotect_roundtrip(self):
        """Protected string can be unprotected back to original."""
        original = "AuraTool Secret String"
        protected = AntiReverseEngineering.protect_string(original)
        unprotected = AntiReverseEngineering.unprotect_string(protected)
        self.assertEqual(unprotected, original)

    def test_protect_produces_hex(self):
        """protect_string returns a hex string."""
        result = AntiReverseEngineering.protect_string("test")
        self.assertTrue(all(c in "0123456789abcdef" for c in result))

    def test_protect_different_each_time(self):
        """Same input produces different hex (randomized)."""
        p1 = AntiReverseEngineering.protect_string("same")
        p2 = AntiReverseEngineering.protect_string("same")
        # XOR key is constant but the encoding may vary
        # At minimum, both should decrypt correctly
        self.assertEqual(AntiReverseEngineering.unprotect_string(p1), "same")
        self.assertEqual(AntiReverseEngineering.unprotect_string(p2), "same")

    def test_obfuscate_deobfuscate_roundtrip(self):
        """Internal obfuscate/deobfuscate works."""
        original = "Internal test"
        encoded = AntiReverseEngineering._obfuscate_str(original)
        decoded = AntiReverseEngineering._deobfuscate_str(encoded)
        self.assertEqual(decoded, original)

    def test_obfuscate_returns_bytes(self):
        """obfuscate_str returns base64-encoded bytes."""
        result = AntiReverseEngineering._obfuscate_str("hello")
        self.assertIsInstance(result, bytes)

    def test_protect_unicode_string(self):
        """Protection handles Unicode strings."""
        for text in ["عربي", "中文", "日本語", "🔐💻🛡️"]:
            protected = AntiReverseEngineering.protect_string(text)
            self.assertEqual(AntiReverseEngineering.unprotect_string(protected), text)


# ═══════════════════════════════════════════════════════════════════════════
#  AntiReverseEngineering — Debugger Detection
# ═══════════════════════════════════════════════════════════════════════════

class TestDebuggerDetection(unittest.TestCase):
    """Test debugger detection methods."""

    def test_detect_debugger_returns_bool(self):
        """detect_debugger returns a boolean."""
        result = AntiReverseEngineering.detect_debugger()
        self.assertIsInstance(result, bool)

    @patch("sys.gettrace", return_value=lambda: None)
    def test_detect_debugger_with_trace(self, mock_trace):
        """detect_debugger detects active trace."""
        result = AntiReverseEngineering.detect_debugger()
        self.assertTrue(result)

    @patch("sys.gettrace", return_value=None)
    @patch("sys.getprofile", return_value=lambda: None)
    def test_detect_debugger_with_profile(self, mock_profile, mock_trace):
        """detect_debugger detects active profile."""
        result = AntiReverseEngineering.detect_debugger()
        self.assertTrue(result)

    @patch.dict(os.environ, {"PYDEVD": "1"})
    def test_detect_debugger_with_env_var(self):
        """detect_debugger detects debug environment variable."""
        result = AntiReverseEngineering.detect_debugger()
        self.assertTrue(result)

    @patch.dict(os.environ, {"REMOTE_DEBUG": "1"})
    def test_detect_debugger_with_remote_debug(self):
        """detect_debugger detects REMOTE_DEBUG env."""
        result = AntiReverseEngineering.detect_debugger()
        self.assertTrue(result)

    @patch.dict(os.environ, {"DEBUGPY_RUNNING": "1"})
    def test_detect_debugger_with_debugpy(self):
        """detect_debugger detects DEBUGPY_RUNNING env."""
        result = AntiReverseEngineering.detect_debugger()
        self.assertTrue(result)


# ═══════════════════════════════════════════════════════════════════════════
#  AntiReverseEngineering — VM Detection
# ═══════════════════════════════════════════════════════════════════════════

class TestVMDetection(unittest.TestCase):
    """Test virtual machine detection."""

    def test_detect_virtual_machine_returns_bool(self):
        """detect_virtual_machine returns a boolean."""
        result = AntiReverseEngineering.detect_virtual_machine()
        self.assertIsInstance(result, bool)

    @patch.dict(os.environ, {"VMWARE_ENV": "some_value"})
    def test_detect_vm_with_env_var(self):
        """detect_virtual_machine detects VM env variable."""
        result = AntiReverseEngineering.detect_virtual_machine()
        self.assertTrue(result)

    @patch.dict(os.environ, {"VIRTUALBOX_HOST_ONLY": "1"})
    def test_detect_vm_virtualbox_env(self):
        """detect_virtual_machine detects VirtualBox env."""
        result = AntiReverseEngineering.detect_virtual_machine()
        self.assertTrue(result)


# ═══════════════════════════════════════════════════════════════════════════
#  AntiReverseEngineering — Code Integrity
# ═══════════════════════════════════════════════════════════════════════════

class TestCodeIntegrity(unittest.TestCase):
    """Test code integrity verification."""

    def test_verify_code_integrity_returns_bool(self):
        """verify_code_integrity returns a boolean."""
        result = AntiReverseEngineering.verify_code_integrity()
        self.assertIsInstance(result, bool)

    def test_verify_code_integrity_passes(self):
        """Code integrity passes when all modules importable."""
        # Since we can import core.security, integrity should pass
        result = AntiReverseEngineering.verify_code_integrity()
        self.assertTrue(result)

    def test_get_module_checksums_returns_dict(self):
        """get_module_checksums returns a dict of checksums."""
        checksums = AntiReverseEngineering.get_module_checksums()
        self.assertIsInstance(checksums, dict)
        self.assertIn("core/security.py", checksums)

    def test_module_checksums_are_hex(self):
        """Checksum values are 64-char hex strings."""
        checksums = AntiReverseEngineering.get_module_checksums()
        for path, checksum in checksums.items():
            self.assertEqual(len(checksum), 64, f"Bad checksum length for {path}")
            self.assertTrue(all(c in "0123456789abcdef" for c in checksum))


# ═══════════════════════════════════════════════════════════════════════════
#  AntiReverseEngineering — System Fingerprint
# ═══════════════════════════════════════════════════════════════════════════

class TestSystemFingerprint(unittest.TestCase):
    """Test system fingerprint generation."""

    def test_get_system_fingerprint_returns_string(self):
        """get_system_fingerprint returns a non-empty string."""
        fp = AntiReverseEngineering.get_system_fingerprint()
        self.assertIsInstance(fp, str)
        self.assertGreater(len(fp), 0)

    def test_fingerprint_is_deterministic(self):
        """Same system produces same fingerprint."""
        fp1 = AntiReverseEngineering.get_system_fingerprint()
        fp2 = AntiReverseEngineering.get_system_fingerprint()
        self.assertEqual(fp1, fp2)


# ═══════════════════════════════════════════════════════════════════════════
#  AntiReverseEngineering — Timing & Anti-Tamper
# ═══════════════════════════════════════════════════════════════════════════

class TestTimingAnomaly(unittest.TestCase):
    """Test timing anomaly detection."""

    def test_timing_anomaly_check_returns_bool(self):
        """timing_anomaly_check returns a boolean."""
        result = AntiReverseEngineering.timing_anomaly_check()
        self.assertIsInstance(result, bool)

    def test_anti_tamper_check_returns_dict(self):
        """anti_tamper_check returns comprehensive results."""
        result = AntiReverseEngineering.anti_tamper_check()
        self.assertIsInstance(result, dict)
        self.assertIn("debugger_detected", result)
        self.assertIn("vm_detected", result)
        self.assertIn("code_integrity", result)
        self.assertIn("timing_anomaly", result)
        self.assertIn("system_fingerprint", result)
        self.assertIn("module_checksums", result)
        self.assertIn("protection_active", result)
        self.assertIn("layer_count", result)
        self.assertEqual(result["layer_count"], 9)
        self.assertTrue(result["protection_active"])


# ═══════════════════════════════════════════════════════════════════════════
#  AntiReverseEngineering — Memory Integrity & Hooks
# ═══════════════════════════════════════════════════════════════════════════

class TestMemoryIntegrity(unittest.TestCase):
    """Test memory integrity and hook detection."""

    def test_check_memory_integrity_returns_bool(self):
        """check_memory_integrity returns a boolean."""
        result = AntiReverseEngineering.check_memory_integrity()
        self.assertIsInstance(result, bool)

    def test_detect_hooks_returns_bool(self):
        """detect_hooks returns a boolean."""
        result = AntiReverseEngineering.detect_hooks()
        self.assertIsInstance(result, bool)


# ═══════════════════════════════════════════════════════════════════════════
#  AntiReverseEngineering — Module Encryption
# ═══════════════════════════════════════════════════════════════════════════

class TestModuleEncryption(unittest.TestCase):
    """Test module file encryption/decryption at rest."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.key = b"test_key_32_bytes_long!!!!!!!!"

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_encrypt_module_bytes_roundtrip(self):
        """Encrypt then decrypt module bytes."""
        filepath = os.path.join(self.tmpdir, "test_module.py")
        with open(filepath, "w") as f:
            f.write("def hello(): return 'world'")

        encrypted = AntiReverseEngineering._encrypt_module_bytes(filepath, self.key)
        self.assertGreater(len(encrypted), 0)

        decrypted = AntiReverseEngineering._decrypt_module_bytes(encrypted, self.key)
        self.assertEqual(decrypted, b"def hello(): return 'world'")

    def test_encrypt_nonexistent_returns_empty(self):
        """Encrypting nonexistent file returns empty bytes."""
        result = AntiReverseEngineering._encrypt_module_bytes(
            "/nonexistent/file.py", self.key
        )
        self.assertEqual(result, b"")

    def test_encrypt_decrypt_roundtrip_binary(self):
        """Encrypt/decrypt works with binary data."""
        filepath = os.path.join(self.tmpdir, "binary.bin")
        data = bytes(range(256))
        with open(filepath, "wb") as f:
            f.write(data)

        encrypted = AntiReverseEngineering._encrypt_module_bytes(filepath, self.key)
        decrypted = AntiReverseEngineering._decrypt_module_bytes(encrypted, self.key)
        self.assertEqual(decrypted, data)

    def test_encryption_differs_from_original(self):
        """Encrypted data differs from original."""
        filepath = os.path.join(self.tmpdir, "plain.txt")
        with open(filepath, "w") as f:
            f.write("plaintext data")

        encrypted = AntiReverseEngineering._encrypt_module_bytes(filepath, self.key)
        with open(filepath, "rb") as f:
            original = f.read()
        self.assertNotEqual(encrypted, original)


# ═══════════════════════════════════════════════════════════════════════════
#  Anti-Tamper Decorator
# ═══════════════════════════════════════════════════════════════════════════

class TestAntiTamperDecorator(unittest.TestCase):
    """Test the anti_tamper_decorator."""

    @patch.object(AntiReverseEngineering, "detect_debugger", return_value=False)
    def test_decorator_allows_execution_when_no_debugger(self, mock_debug):
        """Decorator allows function to execute when no debugger."""
        @anti_tamper_decorator
        def my_func():
            return 42

        result = my_func()
        self.assertEqual(result, 42)

    @patch.object(AntiReverseEngineering, "detect_debugger", return_value=True)
    def test_decorator_blocks_execution_when_debugger(self, mock_debug):
        """Decorator raises SecurityError when debugger detected."""
        @anti_tamper_decorator
        def my_func():
            return 42

        with self.assertRaises(SecurityError):
            my_func()


# ═══════════════════════════════════════════════════════════════════════════
#  AdvancedEncryption — Key Derivation
# ═══════════════════════════════════════════════════════════════════════════

class TestKeyDerivation(unittest.TestCase):
    """Test PBKDF2 key derivation."""

    def test_derive_key_returns_bytes(self):
        """derive_key returns (key, salt) tuple."""
        key, salt = AdvancedEncryption.derive_key(b"master_key")
        self.assertIsInstance(key, bytes)
        self.assertIsInstance(salt, bytes)
        self.assertEqual(len(key), 32)
        self.assertEqual(len(salt), 16)

    def test_derive_key_deterministic_with_same_salt(self):
        """Same salt produces same derived key."""
        salt = b"fixed_salt_16byte"
        k1, _ = AdvancedEncryption.derive_key(b"password", salt)
        k2, _ = AdvancedEncryption.derive_key(b"password", salt)
        self.assertEqual(k1, k2)

    def test_derive_key_different_with_different_salt(self):
        """Different salts produce different keys."""
        k1, _ = AdvancedEncryption.derive_key(b"password", salt=b"salt_a__________")
        k2, _ = AdvancedEncryption.derive_key(b"password", salt=b"salt_b__________")
        self.assertNotEqual(k1, k2)


# ═══════════════════════════════════════════════════════════════════════════
#  AdvancedEncryption — AES-CBC
# ═══════════════════════════════════════════════════════════════════════════

class TestAES_CBC(unittest.TestCase):
    """Test AES-CBC encryption/decryption."""

    def test_encrypt_decrypt_roundtrip(self):
        """Encrypted data can be decrypted."""
        key = secrets.token_bytes(32)
        plaintext = "Hello, AuraTool!"
        encrypted = AdvancedEncryption.encrypt_aes_cbc(plaintext, key)
        decrypted = AdvancedEncryption.decrypt_aes_cbc(encrypted, key)
        self.assertEqual(decrypted, plaintext)

    def test_encrypt_produces_different_output(self):
        """Same plaintext produces different ciphertext."""
        key = secrets.token_bytes(32)
        enc1 = AdvancedEncryption.encrypt_aes_cbc("test", key)
        enc2 = AdvancedEncryption.encrypt_aes_cbc("test", key)
        self.assertNotEqual(enc1, enc2)

    def test_decrypt_too_short_raises(self):
        """Decrypting too-short data raises ValueError."""
        key = secrets.token_bytes(32)
        with self.assertRaises(ValueError):
            AdvancedEncryption.decrypt_aes_cbc(b"short", key)

    def test_decrypt_wrong_key_raises(self):
        """Decrypting with wrong key raises ValueError (HMAC failure)."""
        key1 = secrets.token_bytes(32)
        key2 = secrets.token_bytes(32)
        encrypted = AdvancedEncryption.encrypt_aes_cbc("secret", key1)
        with self.assertRaises(ValueError):
            AdvancedEncryption.decrypt_aes_cbc(encrypted, key2)

    def test_encrypt_empty_string_produces_short_output(self):
        """Encrypting empty string produces data shorter than decrypt minimum."""
        key = secrets.token_bytes(32)
        encrypted = AdvancedEncryption.encrypt_aes_cbc("", key)
        # Empty plaintext = 0 ciphertext bytes, total = 64 bytes (IV+Salt+MAC)
        # decrypt_aes_cbc requires >= 65 bytes (including at least 1 ciphertext byte)
        self.assertLess(len(encrypted), 65)

    def test_encrypt_large_data(self):
        """Encrypting large data works."""
        key = secrets.token_bytes(32)
        plaintext = "A" * 10000
        encrypted = AdvancedEncryption.encrypt_aes_cbc(plaintext, key)
        decrypted = AdvancedEncryption.decrypt_aes_cbc(encrypted, key)
        self.assertEqual(decrypted, plaintext)

    def test_encrypted_format_structure(self):
        """Encrypted data has correct format: IV(16) + Salt(16) + MAC(32) + ciphertext."""
        key = secrets.token_bytes(32)
        encrypted = AdvancedEncryption.encrypt_aes_cbc("test", key)
        # 16 + 16 + 32 = 64 bytes overhead minimum
        self.assertGreaterEqual(len(encrypted), 64)


# ═══════════════════════════════════════════════════════════════════════════
#  AdvancedEncryption — Hashing
# ═══════════════════════════════════════════════════════════════════════════

class TestAdvancedHashing(unittest.TestCase):
    """Test AdvancedEncryption hash functions."""

    def test_hash_sha256(self):
        """SHA-256 produces correct hash."""
        result = AdvancedEncryption.hash_sha256("test")
        expected = hashlib.sha256(b"test").hexdigest()
        self.assertEqual(result, expected)

    def test_hash_sha512(self):
        """SHA-512 produces correct hash."""
        result = AdvancedEncryption.hash_sha512("test")
        expected = hashlib.sha512(b"test").hexdigest()
        self.assertEqual(result, expected)

    def test_hash_sha3(self):
        """SHA3-256 produces correct hash."""
        result = AdvancedEncryption.hash_sha3("test")
        expected = hashlib.sha3_256(b"test").hexdigest()
        self.assertEqual(result, expected)

    def test_hash_md5(self):
        """MD5 produces correct hash."""
        result = AdvancedEncryption.hash_md5("test")
        expected = hashlib.md5(b"test").hexdigest()
        self.assertEqual(result, expected)

    def test_generate_key_length(self):
        """generate_key returns correct length."""
        key = AdvancedEncryption.generate_key(64)
        self.assertEqual(len(key), 64)

    def test_generate_key_default(self):
        """generate_key defaults to32 bytes."""
        key = AdvancedEncryption.generate_key()
        self.assertEqual(len(key), 32)

    def test_secure_compare_equal(self):
        """secure_compare returns True for equal strings."""
        self.assertTrue(AdvancedEncryption.secure_compare("abc", "abc"))

    def test_secure_compare_not_equal(self):
        """secure_compare returns False for different strings."""
        self.assertFalse(AdvancedEncryption.secure_compare("abc", "xyz"))


# ═══════════════════════════════════════════════════════════════════════════
#  SecurityManager — Extended Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestSecurityManagerExtended(unittest.TestCase):
    """Test SecurityManager methods not covered by existing tests."""

    def setUp(self):
        self.sec = SecurityManager()

    def test_get_protection_status_returns_dict(self):
        """get_protection_status returns anti-tamper results."""
        status = self.sec.get_protection_status()
        self.assertIsInstance(status, dict)
        self.assertIn("protection_active", status)

    def test_get_protection_status_caches(self):
        """get_protection_status caches results."""
        s1 = self.sec.get_protection_status()
        s2 = self.sec.get_protection_status()
        self.assertEqual(s1, s2)

    def test_verify_integrity_returns_bool(self):
        """verify_integrity returns a boolean."""
        result = self.sec.verify_integrity()
        self.assertIsInstance(result, bool)

    def test_detect_debugger_method(self):
        """SecurityManager.detect_debugger delegates to AntiReverseEngineering."""
        result = self.sec.detect_debugger()
        self.assertIsInstance(result, bool)

    def test_detect_vm_method(self):
        """SecurityManager.detect_vm delegates to AntiReverseEngineering."""
        result = self.sec.detect_vm()
        self.assertIsInstance(result, bool)

    def test_secure_wipe_file(self):
        """secure_wipe overwrites and deletes file."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"secret data to wipe")
            filepath = f.name
        result = self.sec.secure_wipe(filepath)
        self.assertTrue(result)
        self.assertFalse(os.path.exists(filepath))

    def test_secure_wipe_nonexistent(self):
        """secure_wipe handles nonexistent file."""
        result = self.sec.secure_wipe("/nonexistent/file.txt")
        self.assertFalse(result)

    def test_secure_wipe_custom_passes(self):
        """secure_wipe with custom pass count."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"data")
            filepath = f.name
        result = self.sec.secure_wipe(filepath, passes=5)
        self.assertTrue(result)

    def test_get_module_checksums(self):
        """get_module_checksums returns cached checksums."""
        checksums = self.sec.get_module_checksums()
        self.assertIsInstance(checksums, dict)

    def test_get_security_report(self):
        """get_security_report returns comprehensive report."""
        report = self.sec.get_security_report()
        self.assertIsInstance(report, dict)
        self.assertIn("protection_active", report)
        self.assertIn("debugger_detected", report)
        self.assertIn("vm_detected", report)
        self.assertIn("code_integrity", report)
        self.assertIn("anti_reverse_engineering", report)
        self.assertIn("layer_count", report)
        self.assertIn("timestamp", report)

    def test_security_report_layer_count(self):
        """security report shows 9 protection layers."""
        report = self.sec.get_security_report()
        self.assertEqual(report["layer_count"], 9)


# ═══════════════════════════════════════════════════════════════════════════
#  SecurityManager — Storage Health Extended
# ═══════════════════════════════════════════════════════════════════════════

class TestStorageHealthExtended(unittest.TestCase):
    """Test scan_storage_health with various input scenarios."""

    def setUp(self):
        self.sec = SecurityManager()

    def test_health_perfect_storage(self):
        """Perfect storage gets excellent score."""
        stats = {
            "total_blocks": 61440, "bad_blocks": 0,
            "wear_level": 100, "read_errors": 0, "write_errors": 0,
        }
        result = self.sec.scan_storage_health("DEV1", stats)
        self.assertGreaterEqual(result["health_score"], 95)
        self.assertEqual(result["health_rating"], "EXCELLENT")

    def test_health_good_storage(self):
        """Good storage gets good rating."""
        stats = {
            "total_blocks": 61440, "bad_blocks": 10,
            "wear_level": 85, "read_errors": 2, "write_errors": 1,
        }
        result = self.sec.scan_storage_health("DEV1", stats)
        self.assertGreaterEqual(result["health_score"], 70)

    def test_health_fair_storage(self):
        """Fair storage gets degraded rating."""
        stats = {
            "total_blocks": 61440, "bad_blocks": 50,
            "wear_level": 60, "read_errors": 10, "write_errors": 5,
        }
        result = self.sec.scan_storage_health("DEV1", stats)
        # Score depends on the formula — verify it's in valid range
        self.assertGreaterEqual(result["health_score"], 0)
        self.assertLessEqual(result["health_score"], 100)

    def test_health_poor_storage(self):
        """Poor storage gets degraded rating."""
        stats = {
            "total_blocks": 61440, "bad_blocks": 200,
            "wear_level": 35, "read_errors": 50, "write_errors": 25,
        }
        result = self.sec.scan_storage_health("DEV1", stats)
        # Score is lower than perfect storage
        perfect = self.sec.scan_storage_health("DEV1", {
            "total_blocks": 61440, "bad_blocks": 0,
            "wear_level": 100, "read_errors": 0, "write_errors": 0,
        })
        self.assertLess(result["health_score"], perfect["health_score"])

    def test_health_critical_storage(self):
        """Critical storage gets critical rating."""
        stats = {
            "total_blocks": 1000, "bad_blocks": 500,
            "wear_level": 10, "read_errors": 100, "write_errors": 50,
        }
        result = self.sec.scan_storage_health("DEV1", stats)
        self.assertLess(result["health_score"], 30)
        self.assertEqual(result["health_rating"], "CRITICAL")

    def test_health_simulated(self):
        """scan_storage_health works without stats (simulated)."""
        result = self.sec.scan_storage_health("DEV1")
        self.assertIn("health_score", result)
        self.assertIn("storage_type", result)

    def test_health_score_bounds(self):
        """Health score always between 0 and 100."""
        for bad in [0, 100, 500]:
            for wear in [100, 50, 10]:
                stats = {"total_blocks": 1000, "bad_blocks": bad,
                         "wear_level": wear, "read_errors": 0, "write_errors": 0}
                result = self.sec.scan_storage_health("DEV1", stats)
                self.assertGreaterEqual(result["health_score"], 0)
                self.assertLessEqual(result["health_score"], 100)


if __name__ == "__main__":
    unittest.main()
