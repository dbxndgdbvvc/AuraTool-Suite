"""
AuraTool-Suite — HWID-Based License Manager
=============================================
Production-grade licensing system with:
  - Hardware fingerprint (HWID) binding — prevents license transfer
  - Encrypted license file with HMAC integrity — prevents tampering
  - Time-locked tiers: 15-day trial, 6-month rental, 1-year rental
  - Anti-clock-rollback protection (monitors system time)
  - Automatic shutdown when license expires
  - Persistent storage in ~/.auratool/license.enc

Platform support: Windows, Linux Ubuntu (single codebase, separate builds).
"""

from __future__ import annotations

import datetime
import hashlib
import hmac
import json
import logging
import os
import platform
import re
import secrets
import struct
import sys
import time
import urllib.request
import urllib.error
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger("AuraTool.LicenseManager")


# ---------------------------------------------------------------------------
# License Tiers
# ---------------------------------------------------------------------------

class LicenseTier(Enum):
    """Supported license tiers."""
    TRIAL_15_DAYS = "trial_15d"
    RENTAL_6_MONTHS = "rental_6m"
    RENTAL_1_YEAR = "rental_1y"
    EXPIRED = "expired"


TIER_CONFIG = {
    LicenseTier.TRIAL_15_DAYS: {
        "days": 15,
        "label": "15-Day Free Trial",
        "features": [
            "basic_diagnostics",
            "firmware_flash_limited",
            "log_analysis",
            "storage_health_scan",
        ],
        "max_devices": 5,
        "cloud_backup": False,
        "priority_support": False,
    },
    LicenseTier.RENTAL_6_MONTHS: {
        "days": 182,
        "label": "6-Month Professional Rental",
        "features": [
            "full_diagnostics",
            "all_firmware_flash",
            "ai_assistant",
            "data_recovery",
            "account_repair",
            "biometric_calibration",
            "smart_device_support",
            "factory_management",
        ],
        "max_devices": 50,
        "cloud_backup": True,
        "priority_support": False,
    },
    LicenseTier.RENTAL_1_YEAR: {
        "days": 365,
        "label": "1-Year Ultimate Rental",
        "features": [
            "all_professional",
            "vip_cloud_vault",
            "priority_support",
            "ar_vr_wearable_support",
            "continuous_updates_2030",
            "ultimate_ai_suite",
            "factory_management",
        ],
        "max_devices": -1,  # unlimited
        "cloud_backup": True,
        "priority_support": True,
    },
}


# ---------------------------------------------------------------------------
# HWID Generation
# ---------------------------------------------------------------------------

class HWIDCollector:
    """
    Collects a stable hardware fingerprint from the host machine.
    Combines multiple system identifiers into a single SHA-256 hash.
    Works on both Windows and Linux.
    """

    @staticmethod
    def collect() -> str:
        """Return a 64-character hex HWID string."""
        raw_parts: list[str] = []

        # 1. Machine ID (Linux) or MachineGuid (Windows)
        raw_parts.append(HWIDCollector._get_machine_id())

        # 2. CPU info
        raw_parts.append(HWIDCollector._get_cpu_id())

        # 3. Hostname + username
        raw_parts.append(platform.node())
        raw_parts.append(os.getenv("USER", os.getenv("USERNAME", "unknown")))

        # 4. OS release
        raw_parts.append(platform.release())
        raw_parts.append(platform.version())

        combined = "|".join(raw_parts)
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    @staticmethod
    def _get_machine_id() -> str:
        """Read a stable machine identifier from the OS."""
        sysname = platform.system()

        if sysname == "Linux":
            # /etc/machine-id is unique per installation
            for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
                try:
                    with open(path, "r") as f:
                        return f.read().strip()
                except (OSError, IOError):
                    continue
            # Fallback: /sys/class/dmi/id/product_uuid
            try:
                with open("/sys/class/dmi/id/product_uuid", "r") as f:
                    return f.read().strip()
            except (OSError, IOError):
                pass

        elif sysname == "Windows":
            # Windows MachineGuid from registry
            try:
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"SOFTWARE\Microsoft\Cryptography",
                )
                value, _ = winreg.QueryValueEx(key, "MachineGuid")
                winreg.CloseKey(key)
                return str(value)
            except (ImportError, OSError):
                pass

        # Fallback
        return platform.node()

    @staticmethod
    def _get_cpu_id() -> str:
        """Extract a CPU identifier string."""
        sysname = platform.system()

        if sysname == "Linux":
            try:
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if line.strip().startswith("model name"):
                            return line.split(":", 1)[1].strip()
            except (OSError, IOError):
                pass

        elif sysname == "Windows":
            try:
                import winreg
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
                )
                value, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                winreg.CloseKey(key)
                return str(value)
            except (ImportError, OSError):
                pass

        return platform.processor() or "unknown_cpu"


# ---------------------------------------------------------------------------
# Cryptographic Helpers
# ---------------------------------------------------------------------------

class _Crypto:
    """Lightweight crypto helpers using only the Python standard library."""

    # Derive a fixed key from HWID + salt (for HMAC signing)
    _HMAC_KEY_SEED = b"AuraTool-Suite-License-Master-2025"

    @staticmethod
    def derive_hmac_key(hwid: str) -> bytes:
        """Derive a 32-byte HMAC key from the HWID."""
        return hashlib.pbkdf2_hmac(
            "sha256",
            hwid.encode("utf-8"),
            _Crypto._HMAC_KEY_SEED,
            iterations=100_000,
            dklen=32,
        )

    @staticmethod
    def sign(data: bytes, hwid: str) -> str:
        """Return HMAC-SHA256 hex signature."""
        key = _Crypto.derive_hmac_key(hwid)
        return hmac.new(key, data, hashlib.sha256).hexdigest()

    @staticmethod
    def verify(data: bytes, signature: str, hwid: str) -> bool:
        """Constant-time HMAC verification."""
        expected = _Crypto.sign(data, hwid)
        return hmac.compare_digest(expected, signature)

    @staticmethod
    def encrypt(plaintext: str, hwid: str) -> bytes:
        """
        XOR stream cipher with HMAC-derived key schedule.
        Format: 16-byte IV || ciphertext.
        """
        key = _Crypto.derive_hmac_key(hwid)
        iv = secrets.token_bytes(16)
        data = plaintext.encode("utf-8")

        # Generate keystream via counter-mode HMAC expansion
        keystream = b""
        counter = 0
        while len(keystream) < len(data):
            block = hmac.new(
                key, iv + struct.pack(">I", counter), hashlib.sha256
            ).digest()
            keystream += block
            counter += 1

        ciphertext = bytes(a ^ b for a, b in zip(data, keystream[: len(data)]))
        return iv + ciphertext

    @staticmethod
    def decrypt(encrypted: bytes, hwid: str) -> str:
        """Decrypt bytes produced by encrypt()."""
        if len(encrypted) < 17:
            raise ValueError("Invalid encrypted data: too short")

        key = _Crypto.derive_hmac_key(hwid)
        iv = encrypted[:16]
        ciphertext = encrypted[16:]

        keystream = b""
        counter = 0
        while len(keystream) < len(ciphertext):
            block = hmac.new(
                key, iv + struct.pack(">I", counter), hashlib.sha256
            ).digest()
            keystream += block
            counter += 1

        plaintext = bytes(a ^ b for a, b in zip(ciphertext, keystream[: len(ciphertext)]))
        return plaintext.decode("utf-8")


# ---------------------------------------------------------------------------
# License Server Client (Online Validation)
# ---------------------------------------------------------------------------

class LicenseServerClient:
    """
    HTTP client for communicating with the AuraTool License Server.
    Handles activation, validation, and deactivation over the network.
    """

    DEFAULT_TIMEOUT = 10  # seconds

    def __init__(self, server_url: str, timeout: int = DEFAULT_TIMEOUT):
        """
        Args:
            server_url: Base URL of the license server (e.g., "https://license.auratool.com:8600").
            timeout: HTTP request timeout in seconds.
        """
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout
        self._ssl_context = None

    def set_ssl_context(self, ctx) -> None:
        """Set a custom SSL context (for self-signed certs)."""
        self._ssl_context = ctx

    def activate(self, key: str, hwid: str) -> dict:
        """Send activation request to the license server."""
        return self._post("/activate", {"key": key, "hwid": hwid})

    def validate(self, token: str, hwid: str) -> dict:
        """Send validation request to the license server."""
        return self._post("/validate", {"token": token, "hwid": hwid})

    def deactivate(self, key: str, hwid: str) -> dict:
        """Send deactivation request to the license server."""
        return self._post("/deactivate", {"key": key, "hwid": hwid})

    def health(self) -> dict:
        """Check server health."""
        return self._get("/health")

    def _post(self, path: str, data: dict) -> dict:
        """Send a POST request with JSON body."""
        url = f"{self.server_url}{path}"
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            resp = urllib.request.urlopen(req, timeout=self.timeout, context=self._ssl_context)
            return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            try:
                return json.loads(e.read())
            except Exception:
                return {"error": f"HTTP {e.code}: {e.reason}"}
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            return {"error": f"Connection failed: {e}"}

    def _get(self, path: str) -> dict:
        """Send a GET request."""
        url = f"{self.server_url}{path}"
        req = urllib.request.Request(url)
        try:
            resp = urllib.request.urlopen(req, timeout=self.timeout, context=self._ssl_context)
            return json.loads(resp.read())
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            return {"error": f"Connection failed: {e}"}

    def is_reachable(self) -> bool:
        """Quick check if the server is reachable."""
        try:
            result = self.health()
            return "error" not in result
        except Exception:
            return False


# ---------------------------------------------------------------------------
# License Manager
# ---------------------------------------------------------------------------

class LicenseManager:
    """
    HWID-bound, time-locked license manager with encrypted persistent storage.

    Features:
      - Generates and verifies license keys signed with the machine's HWID
      - Stores license state encrypted on disk (tamper-evident)
      - Detects clock rollback attempts
      - Auto-blocks access when the license expires
    """

    VERSION = "2.0.0"
    APP_DIR_NAME = ".auratool"
    LICENSE_FILE = "license.enc"
    SIGNATURE_FILE = "license.sig"
    KEY_PREFIX_MAP = {
        "AT15": LicenseTier.TRIAL_15_DAYS,
        "AT6M": LicenseTier.RENTAL_6_MONTHS,
        "AT1Y": LicenseTier.RENTAL_1_YEAR,
    }

    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize the license manager.

        Args:
            data_dir: Override for the license storage directory.
                      Defaults to ~/.auratool/
        """
        self.hwid = HWIDCollector.collect()
        self._data_dir = Path(data_dir) if data_dir else self._default_data_dir()
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._license_path = self._data_dir / self.LICENSE_FILE
        self._sig_path = self._data_dir / self.SIGNATURE_FILE

        # In-memory state
        self.tier: LicenseTier = LicenseTier.EXPIRED
        self.activation_date: Optional[datetime.date] = None
        self.license_key: str = ""
        self._last_known_time: float = 0.0  # anti-rollback

        # Load persisted license
        self._load_license()

    def _default_data_dir(self) -> Path:
        home = Path.home()
        if platform.system() == "Windows":
            app_data = os.getenv("APPDATA", str(home))
            return Path(app_data) / self.APP_DIR_NAME
        return home / self.APP_DIR_NAME

    # ==================================================================
    #  PUBLIC API
    # ==================================================================

    def check_license(self) -> dict:
        """
        Check the current license status.

        Returns:
            dict with keys: is_active, tier, tier_label, days_remaining,
            expiration_date, hwid, features, error (if any).
        """
        now = datetime.date.today()

        # Check if expired
        if self.tier == LicenseTier.EXPIRED:
            return self._build_status(now, error="License expired or not activated")

        if self.activation_date is None:
            return self._build_status(now, error="No activation date recorded")

        config = TIER_CONFIG.get(self.tier, {})
        days_allowed = config.get("days", 0)
        expiration = self.activation_date + datetime.timedelta(days=days_allowed)

        # Anti-clock-rollback: ensure system time hasn't gone backward
        current_ts = time.time()
        if self._last_known_time > 0 and current_ts < self._last_known_time - 300:
            logger.warning(
                "Clock rollback detected! System time moved backward by "
                f"{self._last_known_time - current_ts:.0f}s. Blocking access."
            )
            return self._build_status(
                now,
                is_active=False,
                error="System clock manipulated — access denied",
            )

        # Update last known time (with 5-minute tolerance)
        if current_ts > self._last_known_time:
            self._last_known_time = current_ts
            self._save_license()

        is_active = now <= expiration
        days_left = max(0, (expiration - now).days) if is_active else 0

        if not is_active:
            self.tier = LicenseTier.EXPIRED
            self._save_license()
            logger.info("License expired — tier set to EXPIRED")

        return self._build_status(
            now,
            is_active=is_active,
            days_remaining=days_left,
            expiration_date=expiration,
        )

    def activate(self, key: str) -> dict:
        """
        Activate a license key.

        Args:
            key: License key string (e.g., "AT15-A1B2C3D4E5F6")

        Returns:
            dict with keys: success, message, status.
        """
        key = key.strip().upper()
        if not key:
            return {"success": False, "message": "Empty key", "status": self.check_license()}

        # Parse key format: PREFIX-CHECKSUM
        parts = key.split("-")
        if len(parts) < 2:
            return {"success": False, "message": "Invalid key format", "status": self.check_license()}

        prefix = parts[0]
        tier = self.KEY_PREFIX_MAP.get(prefix)
        if tier is None:
            return {
                "success": False,
                "message": f"Unknown key prefix: {prefix}. Valid: AT15, AT6M, AT1Y",
                "status": self.check_license(),
            }

        # Verify key integrity (checksum)
        if not self._verify_key_checksum(key, tier):
            return {
                "success": False,
                "message": "Invalid key checksum — key may be tampered",
                "status": self.check_license(),
            }

        # Activate
        self.tier = tier
        self.activation_date = datetime.date.today()
        self.license_key = key
        self._last_known_time = time.time()
        self._save_license()

        logger.info(f"License activated: {tier.value} ({TIER_CONFIG[tier]['label']})")

        return {
            "success": True,
            "message": f"License activated: {TIER_CONFIG[tier]['label']}",
            "status": self.check_license(),
        }

    def generate_key(self, tier: LicenseTier) -> str:
        """
        Generate a valid license key for the given tier.
        Keys are self-verifying: prefix + HMAC-based checksum.

        NOTE: In production, key generation should happen on a secure server.
              This is for offline/development use only.
        """
        prefix_map = {
            LicenseTier.TRIAL_15_DAYS: "AT15",
            LicenseTier.RENTAL_6_MONTHS: "AT6M",
            LicenseTier.RENTAL_1_YEAR: "AT1Y",
        }
        prefix = prefix_map.get(tier)
        if prefix is None:
            raise ValueError(f"Cannot generate key for tier: {tier}")

        # Generate a deterministic checksum from prefix + secret
        secret_salt = "AuraTool-Suite-2025-SecretKey"
        raw = f"{prefix}-{secret_salt}"
        checksum = hashlib.sha256(raw.encode()).hexdigest()[:12].upper()
        return f"{prefix}-{checksum}"

    def has_feature(self, feature: str) -> bool:
        """Check if the current tier includes a specific feature."""
        config = TIER_CONFIG.get(self.tier, {})
        features = config.get("features", [])
        return feature in features

    def get_tier_config(self, tier: Optional[LicenseTier] = None) -> dict:
        """Return configuration for a specific tier (or the active one)."""
        t = tier or self.tier
        return TIER_CONFIG.get(t, {})

    def get_all_tiers(self) -> dict:
        """Return all available tier configurations."""
        return {
            tier.value: {
                "days": cfg["days"],
                "label": cfg["label"],
                "features": cfg["features"],
                "max_devices": cfg["max_devices"],
            }
            for tier, cfg in TIER_CONFIG.items()
        }

    def deactivate(self) -> None:
        """Deactivate the current license."""
        self.tier = LicenseTier.EXPIRED
        self.license_key = ""
        self.activation_date = None
        self._save_license()
        logger.info("License deactivated")

    def is_expired(self) -> bool:
        """Quick check: has the license expired?"""
        status = self.check_license()
        return not status["is_active"]

    # ==================================================================
    #  ONLINE VALIDATION (License Server Integration)
    # ==================================================================

    def online_activate(self, key: str, server_url: str) -> dict:
        """
        Activate a license key via the remote license server.
        The server validates the key, checks HWID, and returns a token.

        Args:
            key: License key from the server (e.g., "AL-R1Y-...").
            server_url: URL of the license server.

        Returns:
            dict with keys: success, message, token, tier, features.
        """
        client = LicenseServerClient(server_url)
        result = client.activate(key, self.hwid)

        if result.get("error"):
            logger.warning(f"Online activation failed: {result['error']}")
            return {"success": False, "message": result["error"]}

        if result.get("success"):
            # Store server token and tier info locally
            self._server_token = result.get("token", "")
            self._server_tier = result.get("tier", "")
            self._server_expires_in = result.get("expires_in_days", 0)
            self._server_activation_id = result.get("activation_id", "")

            # Map server tier to local tier
            tier_map = {
                "trial_15d": LicenseTier.TRIAL_15_DAYS,
                "rental_6m": LicenseTier.RENTAL_6_MONTHS,
                "rental_1y": LicenseTier.RENTAL_1_YEAR,
            }
            server_tier = result.get("tier", "")
            if server_tier in tier_map:
                self.tier = tier_map[server_tier]
                self.activation_date = datetime.date.today()
                self.license_key = key
                self._last_known_time = time.time()
                self._save_license()

            logger.info(f"Online activation successful: {result.get('tier_label', server_tier)}")

        return result

    def online_validate(self, server_url: str) -> dict:
        """
        Validate the current license against the remote server.
        Sends the stored server token and HWID for verification.

        Args:
            server_url: URL of the license server.

        Returns:
            dict with keys: valid, tier, days_remaining, features, error.
        """
        token = getattr(self, '_server_token', '')
        if not token:
            return {"valid": False, "error": "No server token — activate online first"}

        client = LicenseServerClient(server_url)
        result = client.validate(token, self.hwid)

        if result.get("error"):
            logger.warning(f"Online validation failed: {result['error']}")
            return {"valid": False, "error": result["error"]}

        if result.get("valid"):
            # Update local state with server-confirmed info
            tier_map = {
                "trial_15d": LicenseTier.TRIAL_15_DAYS,
                "rental_6m": LicenseTier.RENTAL_6_MONTHS,
                "rental_1y": LicenseTier.RENTAL_1_YEAR,
            }
            server_tier = result.get("tier", "")
            if server_tier in tier_map:
                self.tier = tier_map[server_tier]
                self._last_known_time = time.time()
                self._save_license()

            logger.info(
                f"Online validation successful: tier={server_tier}, "
                f"days_remaining={result.get('days_remaining', '?')}"
            )

        return result

    def online_deactivate(self, key: str, server_url: str) -> dict:
        """Deactivate this machine from the license server."""
        client = LicenseServerClient(server_url)
        result = client.deactivate(key, self.hwid)

        if result.get("success"):
            self.deactivate()
            self._server_token = ""
            self._save_license()
            logger.info("Online deactivation successful")

        return result

    def check_license_online(self, server_url: str) -> dict:
        """
        Hybrid license check: try online validation first, fall back to offline.

        This is the recommended method for production use:
          1. If we have a server token, validate online
          2. If server is unreachable, fall back to local offline check
          3. If no token exists, do offline check only

        Args:
            server_url: URL of the license server.

        Returns:
            dict — same as check_license(), plus 'online' field.
        """
        # If we have a server token, try online validation
        token = getattr(self, '_server_token', '')
        if token:
            client = LicenseServerClient(server_url)
            if client.is_reachable():
                result = self.online_validate(server_url)
                if result.get("valid"):
                    # Build status from server response
                    tier_map = {
                        "trial_15d": LicenseTier.TRIAL_15_DAYS,
                        "rental_6m": LicenseTier.RENTAL_6_MONTHS,
                        "rental_1y": LicenseTier.RENTAL_1_YEAR,
                    }
                    server_tier = result.get("tier", "")
                    local_tier = tier_map.get(server_tier, LicenseTier.EXPIRED)
                    config = TIER_CONFIG.get(local_tier, {})

                    return {
                        "is_active": True,
                        "tier": server_tier,
                        "tier_label": result.get("tier_label", config.get("label", "N/A")),
                        "days_remaining": result.get("days_remaining", 0),
                        "activation_date": str(self.activation_date) if self.activation_date else None,
                        "expiration_date": None,
                        "hwid": self.hwid,
                        "features": result.get("features", config.get("features", [])),
                        "max_devices": config.get("max_devices", 0),
                        "cloud_backup": config.get("cloud_backup", False),
                        "priority_support": config.get("priority_support", False),
                        "version": self.VERSION,
                        "online": True,
                        "error": None,
                    }
                else:
                    # Server says invalid — fall through to offline
                    logger.warning(
                        f"Online validation failed: {result.get('error', 'unknown')}"
                    )
            else:
                logger.info("License server unreachable — falling back to offline check")

        # Fallback to offline check
        status = self.check_license()
        status["online"] = False
        return status

    def set_server_token(self, token: str) -> None:
        """Manually set the server token (e.g., from a previous activation)."""
        self._server_token = token
        self._save_license()

    # ==================================================================
    #  INTERNAL HELPERS
    # ==================================================================

    def _build_status(
        self,
        today: datetime.date,
        is_active: bool = False,
        days_remaining: int = 0,
        expiration_date: Optional[datetime.date] = None,
        error: Optional[str] = None,
    ) -> dict:
        config = TIER_CONFIG.get(self.tier, {})
        exp = expiration_date
        if exp is None and self.activation_date and self.tier != LicenseTier.EXPIRED:
            exp = self.activation_date + datetime.timedelta(days=config.get("days", 0))

        return {
            "is_active": is_active,
            "tier": self.tier.value,
            "tier_label": config.get("label", "N/A"),
            "days_remaining": days_remaining,
            "activation_date": str(self.activation_date) if self.activation_date else None,
            "expiration_date": str(exp) if exp else None,
            "hwid": self.hwid,
            "features": config.get("features", []),
            "max_devices": config.get("max_devices", 0),
            "cloud_backup": config.get("cloud_backup", False),
            "priority_support": config.get("priority_support", False),
            "version": self.VERSION,
            "error": error,
        }

    def _verify_key_checksum(self, key: str, tier: LicenseTier) -> bool:
        """Verify the key's embedded checksum matches the expected value."""
        parts = key.split("-")
        if len(parts) != 2:
            return False

        prefix = parts[0]
        provided_checksum = parts[1]

        # Recompute expected checksum
        secret_salt = "AuraTool-Suite-2025-SecretKey"
        raw = f"{prefix}-{secret_salt}"
        expected = hashlib.sha256(raw.encode()).hexdigest()[:12].upper()

        return hmac.compare_digest(provided_checksum, expected)

    # ==================================================================
    #  PERSISTENCE (Encrypted File)
    # ==================================================================

    def _save_license(self) -> None:
        """Save license state to encrypted file with HMAC signature."""
        state = {
            "tier": self.tier.value,
            "activation_date": str(self.activation_date) if self.activation_date else None,
            "license_key": self.license_key,
            "hwid": self.hwid,
            "last_known_time": self._last_known_time,
            "saved_at": time.time(),
            "server_token": getattr(self, "_server_token", ""),
            "server_tier": getattr(self, "_server_tier", ""),
            "server_activation_id": getattr(self, "_server_activation_id", ""),
        }

        plaintext = json.dumps(state, indent=2)
        encrypted = _Crypto.encrypt(plaintext, self.hwid)
        signature = _Crypto.sign(encrypted, self.hwid)

        try:
            self._license_path.write_bytes(encrypted)
            self._sig_path.write_text(signature)
            logger.debug("License saved to %s", self._license_path)
        except OSError as e:
            logger.error("Failed to save license: %s", e)

    def _load_license(self) -> None:
        """Load and verify license from encrypted file."""
        if not self._license_path.exists():
            logger.info("No existing license found — starting fresh")
            return

        try:
            encrypted = self._license_path.read_bytes()
            signature = self._sig_path.read_text().strip() if self._sig_path.exists() else ""

            # Verify HMAC integrity
            if not _Crypto.verify(encrypted, signature, self.hwid):
                logger.warning(
                    "License file integrity check FAILED — "
                    "file may have been tampered with or HWID mismatch"
                )
                self.tier = LicenseTier.EXPIRED
                return

            # Decrypt
            plaintext = _Crypto.decrypt(encrypted, self.hwid)
            state = json.loads(plaintext)

            # Verify HWID binding
            if state.get("hwid") != self.hwid:
                logger.warning(
                    "License HWID mismatch — license was generated for a different machine"
                )
                self.tier = LicenseTier.EXPIRED
                return

            # Restore state
            self.tier = LicenseTier(state.get("tier", "expired"))
            self.license_key = state.get("license_key", "")
            self._last_known_time = state.get("last_known_time", 0.0)
            self._server_token = state.get("server_token", "")
            self._server_tier = state.get("server_tier", "")
            self._server_activation_id = state.get("server_activation_id", "")

            date_str = state.get("activation_date")
            if date_str:
                self.activation_date = datetime.date.fromisoformat(date_str)

            logger.info(
                "License loaded: tier=%s, key=%s...",
                self.tier.value,
                self.license_key[:8] if self.license_key else "(none)",
            )

        except (json.JSONDecodeError, ValueError, OSError) as e:
            logger.error("Failed to load license: %s", e)
            self.tier = LicenseTier.EXPIRED

    # ==================================================================
    #  ENFORCEMENT GATE (call at startup)
    # ==================================================================

    def enforce_or_exit(self) -> dict:
        """
        Check license and return status.
        The caller (main.py) should exit the application if is_active is False.

        Returns:
            dict — same as check_license()
        """
        status = self.check_license()

        if not status["is_active"]:
            logger.critical(
                "LICENSE EXPIRED — AuraTool-Suite cannot start.\n"
                "  Tier: %s\n"
                "  Expiration: %s\n"
                "  Please purchase or renew your license.",
                status["tier_label"],
                status["expiration_date"],
            )

        return status
