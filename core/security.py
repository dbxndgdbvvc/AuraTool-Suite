"""
AuraTool-Suite — Core Security & Encryption Module
====================================================
Provides:
  - Cryptographic hashing (SHA-256, SHA-512, MD5) for integrity verification
  - Secure token generation and key management
  - AES-like symmetric encryption/decryption (using stdlib only)
  - UFS/eMMC Health Guardian — storage memory lifecycle monitoring
  - Secure data wipe utilities for decommissioned devices
"""

import hashlib
import hmac
import os
import secrets
import struct
import time


class SecurityManager:
    """
    Central security engine providing cryptographic utilities, data
    protection, and hardware storage health monitoring.
    """

    SECRET_SALT = b"AuraToolSuite2025SecureSalt"
    TOKEN_LENGTH = 32  # bytes

    # UFS/eMMC health thresholds
    HEALTH_THRESHOLDS = {
        "excellent": 95,
        "good": 80,
        "warning": 60,
        "critical": 40,
        "failing": 20,
    }

    def __init__(self):
        self._master_key = secrets.token_bytes(32)

    # ================================================================== #
    #  HASHING UTILITIES
    # ================================================================== #

    @staticmethod
    def hash_data(data: str) -> str:
        """SHA-256 hash of input string."""
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    @staticmethod
    def hash_data_sha512(data: str) -> str:
        """SHA-512 hash of input string."""
        return hashlib.sha512(data.encode("utf-8")).hexdigest()

    @staticmethod
    def hash_file(filepath: str, algorithm: str = "sha256") -> str:
        """Compute hash of an entire file without loading it fully into memory."""
        h = hashlib.new(algorithm)
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def verify_hash(data: str, expected_hash: str, algorithm: str = "sha256") -> bool:
        """Verify data matches an expected hash."""
        actual = hashlib.new(algorithm, data.encode("utf-8")).hexdigest()
        return hmac.compare_digest(actual, expected_hash)

    # ================================================================== #
    #  TOKEN & KEY GENERATION
    # ================================================================== #

    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate a cryptographically secure random hex token."""
        return secrets.token_hex(length)

    @staticmethod
    def generate_license_token(prefix: str, tier_code: str) -> str:
        """Generate a formatted license token: PREFIX-TIERCODE-RANDOMHEX."""
        random_part = secrets.token_hex(8).upper()
        return f"{prefix}-{tier_code}-{random_part}"

    def get_master_key(self) -> bytes:
        """Return the in-memory master key (for internal encryption use only)."""
        return self._master_key

    # ================================================================== #
    #  SYMMETRIC ENCRYPTION / DECRYPTION (XOR-cipher with key scheduling)
    # ================================================================== #

    def encrypt_data(self, plaintext: str, key: str = None) -> bytes:
        """
        Encrypt a string using a key-derived XOR stream cipher.
        Returns bytes: 16-byte IV + ciphertext.
        """
        enc_key = (key or self._master_key.hex())[:32].encode("utf-8")
        iv = secrets.token_bytes(16)
        data = plaintext.encode("utf-8")

        # Generate key stream via HMAC-based expansion
        keystream = b""
        counter = 0
        while len(keystream) < len(data):
            block = hmac.new(enc_key, iv + struct.pack(">I", counter), hashlib.sha256).digest()
            keystream += block
            counter += 1

        ciphertext = bytes(a ^ b for a, b in zip(data, keystream[: len(data)]))
        return iv + ciphertext

    def decrypt_data(self, encrypted: bytes, key: str = None) -> str:
        """
        Decrypt bytes produced by encrypt_data().
        Expects format: 16-byte IV + ciphertext.
        """
        if len(encrypted) < 17:
            raise ValueError("Invalid encrypted data: too short.")

        enc_key = (key or self._master_key.hex())[:32].encode("utf-8")
        iv = encrypted[:16]
        ciphertext = encrypted[16:]

        keystream = b""
        counter = 0
        while len(keystream) < len(ciphertext):
            block = hmac.new(enc_key, iv + struct.pack(">I", counter), hashlib.sha256).digest()
            keystream += block
            counter += 1

        plaintext = bytes(a ^ b for a, b in zip(ciphertext, keystream[: len(ciphertext)]))
        return plaintext.decode("utf-8")

    # ================================================================== #
    #  UFS / eMMC HEALTH GUARDIAN
    # ================================================================== #

    def scan_storage_health(self, device_id: str, stats: dict = None) -> dict:
        """
        Analyse UFS/eMMC health indicators and return a lifecycle report.
        *stats* may contain:
            - total_blocks, bad_blocks, wear_level, read_errors,
              write_errors, power_cycles, temperature_celsius
        """
        if stats is None:
            stats = {
                "total_blocks": 61440,
                "bad_blocks": 12,
                "wear_level": 87,
                "read_errors": 3,
                "write_errors": 1,
                "power_cycles": 1240,
                "temperature_celsius": 38,
                "storage_type": "UFS 3.1",
                "capacity_gb": 256,
            }

        total = stats.get("total_blocks", 1)
        bad = stats.get("bad_blocks", 0)
        wear = stats.get("wear_level", 100)
        bad_pct = (bad / total * 100) if total else 0

        # Calculate composite health score
        health_score = max(
            0,
            100 - (bad_pct * 2) - ((100 - wear) * 0.5)
            - (stats.get("read_errors", 0) * 2)
            - (stats.get("write_errors", 0) * 3),
        )

        if health_score >= self.HEALTH_THRESHOLDS["excellent"]:
            rating = "EXCELLENT"
        elif health_score >= self.HEALTH_THRESHOLDS["good"]:
            rating = "GOOD"
        elif health_score >= self.HEALTH_THRESHOLDS["warning"]:
            rating = "WARNING — Consider backing up data"
        elif health_score >= self.HEALTH_THRESHOLDS["critical"]:
            rating = "CRITICAL — Storage replacement recommended"
        else:
            rating = "FAILING — Immediate replacement required"

        return {
            "device_id": device_id,
            "storage_type": stats.get("storage_type", "Unknown"),
            "capacity_gb": stats.get("capacity_gb", 0),
            "health_score": round(health_score, 1),
            "health_rating": rating,
            "bad_blocks": bad,
            "bad_block_percentage": round(bad_pct, 3),
            "wear_level_percentage": wear,
            "read_errors": stats.get("read_errors", 0),
            "write_errors": stats.get("write_errors", 0),
            "power_cycles": stats.get("power_cycles", 0),
            "temperature_celsius": stats.get("temperature_celsius", 0),
            "recommendation": self._storage_recommendation(health_score),
        }

    def _storage_recommendation(self, score: float) -> str:
        if score >= 90:
            return "Storage is healthy. No action needed."
        if score >= 70:
            return "Minor wear detected. Monitor periodically and keep backups."
        if score >= 50:
            return "Moderate degradation. Back up all critical data now."
        if score >= 30:
            return "Significant wear. Plan storage replacement soon."
        return "Storage is failing. Replace immediately to avoid data loss."

    # ================================================================== #
    #  SECURE DATA WIPE
    # ================================================================== #

    def secure_wipe_data(self, data: bytearray) -> bytearray:
        """
        Overwrite data in-place with pseudo-random patterns (3-pass wipe).
        Pass 1: zeros, Pass 2: ones, Pass 3: random.
        """
        length = len(data)

        # Pass 1: zeros
        for i in range(length):
            data[i] = 0x00

        # Pass 2: ones
        for i in range(length):
            data[i] = 0xFF

        # Pass 3: random
        random_bytes = secrets.token_bytes(length)
        for i in range(length):
            data[i] = random_bytes[i]

        return data

    def wipe_file_secure(self, filepath: str, passes: int = 3) -> bool:
        """Securely wipe a file by overwriting then deleting."""
        try:
            size = os.path.getsize(filepath)
            with open(filepath, "r+b") as f:
                for pass_num in range(passes):
                    f.seek(0)
                    pattern = bytes([pass_num % 256]) * min(8192, size)
                    written = 0
                    while written < size:
                        chunk_size = min(8192, size - written)
                        f.write(pattern[:chunk_size])
                        written += chunk_size
                    f.flush()
                    os.fsync(f.fileno())
            os.remove(filepath)
            return True
        except (OSError, IOError) as e:
            return False

    # ================================================================== #
    #  INTEGRITY VERIFICATION
    # ================================================================== #

    def verify_file_integrity(self, filepath: str, expected_sha256: str) -> bool:
        """Verify a file's SHA-256 hash matches the expected value."""
        actual = self.hash_file(filepath, "sha256")
        return hmac.compare_digest(actual, expected_sha256)

    def create_integrity_manifest(self, directory: str) -> dict:
        """Create a SHA-256 manifest of all files in a directory."""
        manifest = {}
        for root, _dirs, files in os.walk(directory):
            for fname in sorted(files):
                fpath = os.path.join(root, fname)
                try:
                    manifest[fpath] = self.hash_file(fpath, "sha256")
                except (OSError, IOError):
                    pass
        return manifest
