"""
Unit Tests — Cryptographic Firmware Engine
==========================================
Tests for modules/crypto_engine.py covering:
  - AES-256-CBC encryption/decryption with PKCS7 padding
  - AES-256-GCM authenticated encryption/decryption
  - RSA-2048 key generation and signature verification
  - SHA-256, SHA-512, SHA3-256 hashing
  - HMAC-SHA256 computation and verification
  - PBKDF2 key derivation
  - Secure random key generation
  - Constant-time comparison
  - Binary data unpacking (uint16/32/64)
  - Firmware payload encrypt/decrypt roundtrips
  - Scatter partition decryption
  - Boot signature verification
"""

import hashlib
import hmac
import os
import secrets
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.crypto_engine import CryptoEngine, _HAS_CRYPTOGRAPHY

# Import serialization for RSA tests
if _HAS_CRYPTOGRAPHY:
    from cryptography.hazmat.primitives import serialization


# ═══════════════════════════════════════════════════════════════════════════════
#  CRYPTO ENGINE INIT
# ═══════════════════════════════════════════════════════════════════════════════

class TestCryptoEngineInit(unittest.TestCase):
    """Test CryptoEngine initialization."""

    def test_default_init(self):
        engine = CryptoEngine()
        self.assertIsNotNone(engine._session_key)
        self.assertEqual(len(engine._session_key), 32)

    def test_custom_master_key(self):
        key = b"my_custom_master_key_1234567890"
        engine = CryptoEngine(master_key=key)
        self.assertEqual(engine._session_key, key)

    def test_cryptography_available(self):
        """The cryptography library should be available in production."""
        self.assertTrue(_HAS_CRYPTOGRAPHY, "cryptography library not available")

    def test_aes_block_size(self):
        engine = CryptoEngine()
        self.assertEqual(engine.AES_BLOCK_SIZE, 16)

    def test_pbkdf2_iterations(self):
        engine = CryptoEngine()
        self.assertGreaterEqual(engine.PBKDF2_ITERATIONS, 100_000)


# ═══════════════════════════════════════════════════════════════════════════════
#  AES-256-CBC
# ═══════════════════════════════════════════════════════════════════════════════

class TestAESCBC(unittest.TestCase):
    """Test AES-256-CBC encryption and decryption."""

    def setUp(self):
        self.engine = CryptoEngine()
        self.key = secrets.token_bytes(32)

    def test_encrypt_decrypt_roundtrip(self):
        plaintext = b"Hello, AuraTool firmware payload!"
        encrypted = self.engine.aes_encrypt_cbc(plaintext, self.key)
        decrypted = self.engine.aes_decrypt_cbc(encrypted, self.key)
        self.assertEqual(decrypted, plaintext)

    def test_encrypt_returns_iv_plus_ciphertext(self):
        plaintext = b"test data"
        encrypted = self.engine.aes_encrypt_cbc(plaintext, self.key)
        # Should be iv (16) + at least one block (16) = 32 bytes minimum
        self.assertGreaterEqual(len(encrypted), 32)

    def test_encrypt_string_input(self):
        plaintext = "string plaintext"
        encrypted = self.engine.aes_encrypt_cbc(plaintext, self.key)
        decrypted = self.engine.aes_decrypt_cbc(encrypted, self.key)
        self.assertEqual(decrypted, plaintext.encode("utf-8"))

    def test_custom_iv(self):
        iv = b"\x00" * 16
        plaintext = b"custom iv test"
        encrypted = self.engine.aes_encrypt_cbc(plaintext, self.key, iv=iv)
        decrypted = self.engine.aes_decrypt_cbc(encrypted, self.key)
        self.assertEqual(decrypted, plaintext)

    def test_different_plaintexts_produce_different_ciphertexts(self):
        a = self.engine.aes_encrypt_cbc(b"message A", self.key)
        b = self.engine.aes_encrypt_cbc(b"message B", self.key)
        # Different random IVs should produce different ciphertexts
        self.assertNotEqual(a, b)

    def test_same_plaintext_different_ciphertexts(self):
        """Different random IVs => different ciphertexts for same plaintext."""
        a = self.engine.aes_encrypt_cbc(b"same", self.key)
        b = self.engine.aes_encrypt_cbc(b"same", self.key)
        self.assertNotEqual(a, b)

    def test_empty_plaintext(self):
        encrypted = self.engine.aes_encrypt_cbc(b"", self.key)
        decrypted = self.engine.aes_decrypt_cbc(encrypted, self.key)
        self.assertEqual(decrypted, b"")

    def test_large_plaintext(self):
        plaintext = os.urandom(1024 * 1024)  # 1 MB
        encrypted = self.engine.aes_encrypt_cbc(plaintext, self.key)
        decrypted = self.engine.aes_decrypt_cbc(encrypted, self.key)
        self.assertEqual(decrypted, plaintext)

    def test_decrypt_too_short_raises(self):
        with self.assertRaises(ValueError):
            self.engine.aes_decrypt_cbc(b"short", self.key)

    def test_pkcs7_padding_block_aligned(self):
        """Data exactly aligned to 16 bytes should still pad (16 bytes of 0x10)."""
        plaintext = b"\x00" * 16
        encrypted = self.engine.aes_encrypt_cbc(plaintext, self.key)
        decrypted = self.engine.aes_decrypt_cbc(encrypted, self.key)
        self.assertEqual(decrypted, plaintext)

    def test_pkcs7_padding_non_aligned(self):
        """Non-block-aligned data should be padded correctly."""
        plaintext = b"12345"  # 5 bytes, needs 11 bytes padding
        encrypted = self.engine.aes_encrypt_cbc(plaintext, self.key)
        decrypted = self.engine.aes_decrypt_cbc(encrypted, self.key)
        self.assertEqual(decrypted, plaintext)


# ═══════════════════════════════════════════════════════════════════════════════
#  AES-256-GCM
# ═══════════════════════════════════════════════════════════════════════════════

class TestAESGCM(unittest.TestCase):
    """Test AES-256-GCM authenticated encryption."""

    def setUp(self):
        self.engine = CryptoEngine()
        self.key = secrets.token_bytes(32)

    def test_encrypt_decrypt_roundtrip(self):
        plaintext = b"Authenticated firmware data"
        encrypted = self.engine.aes_encrypt_gcm(plaintext, self.key)
        decrypted = self.engine.aes_decrypt_gcm(encrypted, self.key)
        self.assertEqual(decrypted, plaintext)

    def test_returns_nonce_ciphertext_tag(self):
        plaintext = b"test"
        encrypted = self.engine.aes_encrypt_gcm(plaintext, self.key)
        # nonce (12) + ciphertext (4) + tag (16) = 32 bytes minimum
        self.assertGreaterEqual(len(encrypted), 32)

    def test_tampered_data_raises(self):
        """Modifying ciphertext should fail HMAC/tag verification."""
        plaintext = b"secure data"
        encrypted = self.engine.aes_encrypt_gcm(plaintext, self.key)
        # Tamper with ciphertext
        tampered = bytearray(encrypted)
        tampered[12] ^= 0xFF  # Flip bits in ciphertext
        tampered = bytes(tampered)
        with self.assertRaises((ValueError, Exception)):
            self.engine.aes_decrypt_gcm(tampered, self.key)

    def test_wrong_key_fails(self):
        plaintext = b"key test"
        encrypted = self.engine.aes_encrypt_gcm(plaintext, self.key)
        wrong_key = secrets.token_bytes(32)
        with self.assertRaises((ValueError, Exception)):
            self.engine.aes_decrypt_gcm(encrypted, wrong_key)

    def test_empty_plaintext(self):
        encrypted = self.engine.aes_encrypt_gcm(b"", self.key)
        decrypted = self.engine.aes_decrypt_gcm(encrypted, self.key)
        self.assertEqual(decrypted, b"")

    def test_decrypt_too_short_raises(self):
        with self.assertRaises(ValueError):
            self.engine.aes_decrypt_gcm(b"short", self.key)


# ═══════════════════════════════════════════════════════════════════════════════
#  RSA SIGNATURE VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestRSASignatures(unittest.TestCase):
    """Test RSA key generation and signature verification."""

    def setUp(self):
        self.engine = CryptoEngine()

    def test_generate_keypair(self):
        private_pem, public_pem = self.engine.generate_rsa_keypair(2048)
        self.assertIsNotNone(private_pem)
        self.assertIsNotNone(public_pem)
        self.assertIn(b"BEGIN PRIVATE KEY", private_pem)
        self.assertIn(b"BEGIN PUBLIC KEY", public_pem)

    def test_sign_and_verify_roundtrip(self):
        """Sign data with private key, verify with public key."""
        if not _HAS_CRYPTOGRAPHY:
            self.skipTest("cryptography library not available")
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding, rsa
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import serialization

        private_key = rsa.generate_private_key(65537, 2048, default_backend())
        public_pem = private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo)

        data = b"firmware to sign"
        signature = private_key.sign(data, padding.PKCS1v15(), hashes.SHA256())
        self.assertTrue(self.engine.verify_rsa_signature(data, signature, public_pem))

    def test_verify_wrong_signature(self):
        """Wrong signature should fail verification."""
        if not _HAS_CRYPTOGRAPHY:
            self.skipTest("cryptography library not available")
        private_pem, public_pem = self.engine.generate_rsa_keypair(2048)
        wrong_sig = secrets.token_bytes(256)
        self.assertFalse(self.engine.verify_rsa_signature(b"data", wrong_sig, public_pem))

    def test_verify_wrong_data(self):
        """Signature from different data should fail."""
        if not _HAS_CRYPTOGRAPHY:
            self.skipTest("cryptography library not available")
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding, rsa
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import serialization

        private_key = rsa.generate_private_key(65537, 2048, default_backend())
        public_pem = private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo)

        sig = private_key.sign(b"correct data", padding.PKCS1v15(), hashes.SHA256())
        self.assertFalse(self.engine.verify_rsa_signature(b"wrong data", sig, public_pem))


# ═══════════════════════════════════════════════════════════════════════════════
#  HASHING
# ═══════════════════════════════════════════════════════════════════════════════

class TestHashing(unittest.TestCase):
    """Test SHA-256, SHA-512, SHA3-256 hashing."""

    def setUp(self):
        self.engine = CryptoEngine()

    def test_sha256_string(self):
        expected = hashlib.sha256(b"hello").hexdigest()
        self.assertEqual(self.engine.sha256("hello"), expected)

    def test_sha256_bytes(self):
        expected = hashlib.sha256(b"hello").hexdigest()
        self.assertEqual(self.engine.sha256(b"hello"), expected)

    def test_sha512_string(self):
        expected = hashlib.sha512(b"hello").hexdigest()
        self.assertEqual(self.engine.sha512("hello"), expected)

    def test_sha512_bytes(self):
        expected = hashlib.sha512(b"hello").hexdigest()
        self.assertEqual(self.engine.sha512(b"hello"), expected)

    def test_sha3_256(self):
        expected = hashlib.sha3_256(b"hello").hexdigest()
        self.assertEqual(self.engine.sha3_256(b"hello"), expected)

    def test_sha256_empty(self):
        expected = hashlib.sha256(b"").hexdigest()
        self.assertEqual(self.engine.sha256(b""), expected)

    def test_sha256_hex_length(self):
        h = self.engine.sha256("test")
        self.assertEqual(len(h), 64)

    def test_sha512_hex_length(self):
        h = self.engine.sha512("test")
        self.assertEqual(len(h), 128)


# ═══════════════════════════════════════════════════════════════════════════════
#  HMAC
# ═══════════════════════════════════════════════════════════════════════════════

class TestHMAC(unittest.TestCase):
    """Test HMAC-SHA256 computation and verification."""

    def setUp(self):
        self.engine = CryptoEngine()
        self.key = secrets.token_bytes(32)

    def test_hmac_sha256_matches_hashlib(self):
        expected = hmac.new(self.key, b"test data", hashlib.sha256).hexdigest()
        self.assertEqual(self.engine.hmac_sha256("test data", self.key), expected)

    def test_hmac_sha256_bytes(self):
        expected = hmac.new(self.key, b"test", hashlib.sha256).hexdigest()
        self.assertEqual(self.engine.hmac_sha256(b"test", self.key), expected)

    def test_verify_hmac_valid(self):
        data = "firmware integrity check"
        expected = self.engine.hmac_sha256(data, self.key)
        self.assertTrue(self.engine.verify_hmac(data, self.key, expected))

    def test_verify_hmac_invalid(self):
        self.assertFalse(self.engine.verify_hmac("data", self.key, "0" * 64))

    def test_verify_hmac_tampered(self):
        data = "original"
        valid = self.engine.hmac_sha256(data, self.key)
        self.assertFalse(self.engine.verify_hmac("tampered", self.key, valid))


# ═══════════════════════════════════════════════════════════════════════════════
#  FILE HASHING
# ═══════════════════════════════════════════════════════════════════════════════

class TestFileHashing(unittest.TestCase):
    """Test file_hash method."""

    def setUp(self):
        self.engine = CryptoEngine()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_file_hash_sha256(self):
        fpath = os.path.join(self.tmpdir, "test.bin")
        data = b"hash me please"
        with open(fpath, "wb") as f:
            f.write(data)
        expected = hashlib.sha256(data).hexdigest()
        self.assertEqual(self.engine.file_hash(fpath, "sha256"), expected)

    def test_file_hash_sha512(self):
        fpath = os.path.join(self.tmpdir, "test512.bin")
        data = b"hash me too"
        with open(fpath, "wb") as f:
            f.write(data)
        expected = hashlib.sha512(data).hexdigest()
        self.assertEqual(self.engine.file_hash(fpath, "sha512"), expected)


# ═══════════════════════════════════════════════════════════════════════════════
#  KEY DERIVATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestKeyDerivation(unittest.TestCase):
    """Test PBKDF2 key derivation."""

    def setUp(self):
        self.engine = CryptoEngine()

    def test_derive_key_returns_32_bytes(self):
        dk, salt = self.engine.derive_key_pbkdf2("password")
        self.assertEqual(len(dk), 32)
        self.assertEqual(len(salt), 16)

    def test_derive_key_custom_salt(self):
        salt = b"\x01" * 16
        dk1, s1 = self.engine.derive_key_pbkdf2("pass", salt=salt)
        dk2, s2 = self.engine.derive_key_pbkdf2("pass", salt=salt)
        self.assertEqual(dk1, dk2)
        self.assertEqual(s1, s2)

    def test_derive_key_different_salts_different_keys(self):
        dk1, _ = self.engine.derive_key_pbkdf2("pass", salt=secrets.token_bytes(16))
        dk2, _ = self.engine.derive_key_pbkdf2("pass", salt=secrets.token_bytes(16))
        self.assertNotEqual(dk1, dk2)

    def test_derive_key_string_input(self):
        dk, salt = self.engine.derive_key_pbkdf2("test_password")
        self.assertEqual(len(dk), 32)

    def test_derive_key_custom_dklen(self):
        dk, _ = self.engine.derive_key_pbkdf2("pass", dklen=64)
        self.assertEqual(len(dk), 64)

    def test_derive_key_custom_iterations(self):
        dk, _ = self.engine.derive_key_pbkdf2("pass", iterations=1000)
        self.assertEqual(len(dk), 32)


# ═══════════════════════════════════════════════════════════════════════════════
#  SECURE KEY GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestKeyGeneration(unittest.TestCase):
    """Test secure random key generation."""

    def setUp(self):
        self.engine = CryptoEngine()

    def test_generate_key_default_length(self):
        key = self.engine.generate_key()
        self.assertEqual(len(key), 32)

    def test_generate_key_custom_length(self):
        key = self.engine.generate_key(64)
        self.assertEqual(len(key), 64)

    def test_generate_key_random(self):
        k1 = self.engine.generate_key()
        k2 = self.engine.generate_key()
        self.assertNotEqual(k1, k2)


# ═══════════════════════════════════════════════════════════════════════════════
#  CONSTANT-TIME COMPARISON
# ═══════════════════════════════════════════════════════════════════════════════

class TestSecureCompare(unittest.TestCase):
    """Test constant-time comparison."""

    def setUp(self):
        self.engine = CryptoEngine()

    def test_equal_strings(self):
        self.assertTrue(self.engine.secure_compare("hello", "hello"))

    def test_equal_bytes(self):
        self.assertTrue(self.engine.secure_compare(b"hello", b"hello"))

    def test_different_strings(self):
        self.assertFalse(self.engine.secure_compare("hello", "world"))

    def test_different_lengths(self):
        self.assertFalse(self.engine.secure_compare("a", "ab"))

    def test_mixed_types(self):
        self.assertTrue(self.engine.secure_compare("hello", b"hello"))


# ═══════════════════════════════════════════════════════════════════════════════
#  BINARY DATA UNPACKING
# ═══════════════════════════════════════════════════════════════════════════════

class TestBinaryUnpacking(unittest.TestCase):
    """Test static binary unpacking utilities."""

    def test_unpack_uint16_little(self):
        data = struct.pack("<H", 0x1234)
        self.assertEqual(CryptoEngine.unpack_uint16(data, 0, True), 0x1234)

    def test_unpack_uint16_big(self):
        data = struct.pack(">H", 0x1234)
        self.assertEqual(CryptoEngine.unpack_uint16(data, 0, False), 0x1234)

    def test_unpack_uint32_little(self):
        data = struct.pack("<I", 0xDEADBEEF)
        self.assertEqual(CryptoEngine.unpack_uint32(data, 0, True), 0xDEADBEEF)

    def test_unpack_uint32_big(self):
        data = struct.pack(">I", 0xDEADBEEF)
        self.assertEqual(CryptoEngine.unpack_uint32(data, 0, False), 0xDEADBEEF)

    def test_unpack_uint64_little(self):
        data = struct.pack("<Q", 0x0102030405060708)
        self.assertEqual(CryptoEngine.unpack_uint64(data, 0, True), 0x0102030405060708)

    def test_unpack_uint64_big(self):
        data = struct.pack(">Q", 0x0102030405060708)
        self.assertEqual(CryptoEngine.unpack_uint64(data, 0, False), 0x0102030405060708)

    def test_pack_uint32_little(self):
        result = CryptoEngine.pack_uint32(0xDEADBEEF, True)
        self.assertEqual(result, struct.pack("<I", 0xDEADBEEF))

    def test_pack_uint32_big(self):
        result = CryptoEngine.pack_uint32(0xDEADBEEF, False)
        self.assertEqual(result, struct.pack(">I", 0xDEADBEEF))

    def test_unpack_with_offset(self):
        data = b"\x00\x00\x00\x00\x34\x12"
        self.assertEqual(CryptoEngine.unpack_uint16(data, 4, True), 0x1234)

    def test_pack_unpack_roundtrip(self):
        for val in [0, 1, 255, 256, 65535]:
            packed = CryptoEngine.pack_uint32(val)
            unpacked = CryptoEngine.unpack_uint32(packed)
            self.assertEqual(unpacked, val)


# ═══════════════════════════════════════════════════════════════════════════════
#  FIRMWARE PAYLOAD ENCRYPT/DECRYPT
# ═══════════════════════════════════════════════════════════════════════════════

class TestFirmwarePayload(unittest.TestCase):
    """Test firmware payload encrypt/decrypt roundtrips."""

    def setUp(self):
        self.engine = CryptoEngine()
        self.key = secrets.token_bytes(32)

    def test_aes_cbc_roundtrip(self):
        plaintext = b"firmware payload data with sensitive contents"
        encrypted = self.engine.encrypt_firmware_payload(plaintext, self.key, "aes-256-cbc")
        decrypted = self.engine.decrypt_firmware_payload(encrypted, self.key, "aes-256-cbc")
        self.assertEqual(decrypted, plaintext)

    def test_aes_gcm_roundtrip(self):
        plaintext = b"gcm authenticated firmware"
        encrypted = self.engine.encrypt_firmware_payload(plaintext, self.key, "aes-256-gcm")
        decrypted = self.engine.decrypt_firmware_payload(encrypted, self.key, "aes-256-gcm")
        self.assertEqual(decrypted, plaintext)

    def test_xor_stream_roundtrip(self):
        plaintext = b"xor stream cipher test"
        encrypted = self.engine.encrypt_firmware_payload(plaintext, self.key, "xor-stream")
        decrypted = self.engine.decrypt_firmware_payload(encrypted, self.key, "xor-stream")
        self.assertEqual(decrypted, plaintext)

    def test_unsupported_algorithm_raises(self):
        with self.assertRaises(ValueError):
            self.engine.encrypt_firmware_payload(b"data", self.key, "unknown-algo")
        with self.assertRaises(ValueError):
            self.engine.decrypt_firmware_payload(b"data", self.key, "unknown-algo")

    def test_string_key_input(self):
        plaintext = b"string key test"
        key_str = "my_password_string_12345678"
        encrypted = self.engine.encrypt_firmware_payload(plaintext, key_str, "aes-256-cbc")
        decrypted = self.engine.decrypt_firmware_payload(encrypted, key_str, "aes-256-cbc")
        self.assertEqual(decrypted, plaintext)

    def test_large_payload(self):
        plaintext = os.urandom(1024 * 100)  # 100 KB
        encrypted = self.engine.encrypt_firmware_payload(plaintext, self.key, "aes-256-cbc")
        decrypted = self.engine.decrypt_firmware_payload(encrypted, self.key, "aes-256-cbc")
        self.assertEqual(decrypted, plaintext)


# ═══════════════════════════════════════════════════════════════════════════════
#  SCATTER PARTITION DECRYPTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestScatterPartitionDecryption(unittest.TestCase):
    """Test decrypt_scatter_partition."""

    def setUp(self):
        self.engine = CryptoEngine()
        self.key = secrets.token_bytes(32)

    def test_decrypt_partition_roundtrip(self):
        plaintext = b"scatter partition data"
        encrypted = self.engine.aes_encrypt_cbc(plaintext, self.key)
        r = self.engine.decrypt_scatter_partition(encrypted, self.key)
        self.assertTrue(r["success"])
        self.assertEqual(r["data"], plaintext)

    def test_decrypt_partition_returns_size(self):
        plaintext = b"test size"
        encrypted = self.engine.aes_encrypt_cbc(plaintext, self.key)
        r = self.engine.decrypt_scatter_partition(encrypted, self.key)
        self.assertEqual(r["size"], len(plaintext))


# ═══════════════════════════════════════════════════════════════════════════════
#  BOOT SIGNATURE VERIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestBootSignature(unittest.TestCase):
    """Test verify_boot_signature."""

    def setUp(self):
        self.engine = CryptoEngine()
        self.key = secrets.token_bytes(32)

    def test_boot_image_too_small(self):
        r = self.engine.verify_boot_signature(b"\x00" * 100, self.key)
        self.assertFalse(r["valid"])
        self.assertIn("too small", r["error"])

    def test_boot_image_no_avb(self):
        boot_image = os.urandom(1024)
        r = self.engine.verify_boot_signature(boot_image, self.key)
        self.assertFalse(r["has_avb"])
        self.assertEqual(r["verification"], "NO_VBMETA")


# ═══════════════════════════════════════════════════════════════════════════════
#  CROSS-ALGORITHM CONSISTENCY
# ═══════════════════════════════════════════════════════════════════════════════

class TestCrossAlgorithmConsistency(unittest.TestCase):
    """Test that the same data produces consistent hashes across calls."""

    def setUp(self):
        self.engine = CryptoEngine()

    def test_sha256_consistent(self):
        h1 = self.engine.sha256("firmware_data")
        h2 = self.engine.sha256("firmware_data")
        self.assertEqual(h1, h2)

    def test_hmac_consistent(self):
        key = b"key"
        h1 = self.engine.hmac_sha256("data", key)
        h2 = self.engine.hmac_sha256("data", key)
        self.assertEqual(h1, h2)

    def test_pbkdf2_consistent_with_same_salt(self):
        salt = b"\x00" * 16
        dk1, _ = self.engine.derive_key_pbkdf2("pass", salt=salt)
        dk2, _ = self.engine.derive_key_pbkdf2("pass", salt=salt)
        self.assertEqual(dk1, dk2)


if __name__ == "__main__":
    unittest.main()
