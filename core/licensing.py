"""
AuraTool-Suite — Smart Licensing Engine with Hardware ID (HWID) Binding
========================================================================
Flexible licensing system providing:
  - HWID generation (CPU/Motherboard/Disk/Hostname fingerprinting)
  - 15-Day Free Trial (fully featured, activated automatically on first run)
  - 6-Month Professional Subscription (AT-6M-...)
  - 1-Year Ultimate VIP Subscription (AT-1Y-...)
  - System clock tamper protection (anti-rollback check)
  - Cryptographic key verification bound to unique machine HWID
"""

import datetime
import hashlib
import json
import os
import platform
import subprocess
import time
from enum import Enum


class LicenseTier(Enum):
    TRIAL_15_DAYS = "15-Day Free Trial"
    SIX_MONTHS = "6 Months Professional"
    ONE_YEAR_VIP = "1 Year Ultimate VIP"
    EXPIRED = "Expired"


# Tier configuration
TIER_CONFIG = {
    LicenseTier.TRIAL_15_DAYS: {
        "days": 15,
        "features": [
            "Basic diagnostics", "Firmware flash (limited models)",
            "Log analysis", "Storage health scan",
        ],
        "device_limit": 5,
        "cloud_backup": False,
        "priority_support": False,
    },
    LicenseTier.SIX_MONTHS: {
        "days": 180,
        "features": [
            "Full diagnostics", "All firmware flash operations",
            "AI assistant", "Data recovery", "Account repair",
            "Biometric calibration", "Smart device support",
        ],
        "device_limit": 50,
        "cloud_backup": True,
        "priority_support": False,
    },
    LicenseTier.ONE_YEAR_VIP: {
        "days": 365,
        "features": [
            "ALL Professional features",
            "VIP cloud vault (encrypted EFS/NVRAM backup)",
            "Priority support & early firmware access",
            "AR/VR & wearable full support",
            "Continuous updates through 2030",
            "Ultimate AI diagnostic suite",
        ],
        "device_limit": -1,  # Unlimited
        "cloud_backup": True,
        "priority_support": True,
    },
}


def get_hardware_id() -> str:
    """Generate a unique Hardware ID (HWID) based on machine characteristics."""
    os_name = platform.system()
    raw_identifiers = []

    raw_identifiers.append(platform.node())
    raw_identifiers.append(platform.machine())

    if os_name == "Windows":
        try:
            cmd = "wmic csproduct get uuid"
            uuid = subprocess.check_output(cmd, shell=True).decode().split()[-1]
            raw_identifiers.append(uuid)
        except Exception:
            raw_identifiers.append(os.environ.get("COMPUTERNAME", "WIN_GENERIC"))
    elif os_name == "Linux":
        try:
            if os.path.exists("/etc/machine-id"):
                with open("/etc/machine-id", "r") as f:
                    raw_identifiers.append(f.read().strip())
            elif os.path.exists("/var/lib/dbus/machine-id"):
                with open("/var/lib/dbus/machine-id", "r") as f:
                    raw_identifiers.append(f.read().strip())
        except Exception:
            raw_identifiers.append("LINUX_GENERIC")

    combined = ":".join(raw_identifiers)
    hwid_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()[:16].upper()
    return f"AT-{hwid_hash[:4]}-{hwid_hash[4:8]}-{hwid_hash[8:12]}-{hwid_hash[12:16]}"


class LicenseManager:
    """
    Handles automatic trial creation, HWID hardware binding, paid key activation,
    anti-clock tamper verification, and expiration tracking across AuraTool-Suite.
    """

    SECRET_SALT = "AuraToolSuite2030SecretKey"
    VERSION = "2.0.0"

    def __init__(self, data_dir: str | None = None):
        self.hwid = get_hardware_id()
        self.data_dir = data_dir or self._default_storage_dir()
        os.makedirs(self.data_dir, exist_ok=True)
        self.state_file = os.path.join(self.data_dir, "lic_state.json")

        self.activation_date = datetime.date.today()
        self.tier = LicenseTier.TRIAL_15_DAYS
        self.license_key = ""
        self.clock_tampered = False

        self._load_state()

    @staticmethod
    def _default_storage_dir() -> str:
        home = os.path.expanduser("~")
        if os.name == "nt":
            app_data = os.getenv("APPDATA", home)
            return os.path.join(app_data, ".auratool")
        return os.path.join(home, ".auratool")

    def _load_state(self) -> None:
        """Loads state from disk or initializes 15-day trial on first run."""
        now_ts = time.time()

        if not os.path.exists(self.state_file):
            # First application run: initialize 15-day trial automatically
            self.tier = LicenseTier.TRIAL_15_DAYS
            self.activation_date = datetime.date.today()
            self.license_key = "TRIAL-FREE-15D"
            self._save_state(last_seen_ts=now_ts)
            return

        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            stored_hwid = data.get("hwid", "")
            last_seen_ts = data.get("last_seen_ts", 0)

            # Anti-Tamper check: If current system clock is older than last seen, detect clock manipulation
            if now_ts < (last_seen_ts - 3600):  # 1 hour tolerance
                self.clock_tampered = True
                self.tier = LicenseTier.EXPIRED
                return

            act_str = data.get("activation_date", str(datetime.date.today()))
            self.activation_date = datetime.date.fromisoformat(act_str)
            tier_str = data.get("tier", LicenseTier.TRIAL_15_DAYS.value)

            for t in LicenseTier:
                if t.value == tier_str:
                    self.tier = t
                    break

            self.license_key = data.get("license_key", "")
            self._save_state(last_seen_ts=now_ts)

        except Exception:
            self.tier = LicenseTier.TRIAL_15_DAYS
            self.activation_date = datetime.date.today()
            self._save_state(last_seen_ts=now_ts)

    def _save_state(self, last_seen_ts: float | None = None) -> None:
        """Saves licensing metadata and timestamp to disk."""
        data = {
            "hwid": self.hwid,
            "tier": self.tier.value,
            "activation_date": str(self.activation_date),
            "license_key": self.license_key,
            "last_seen_ts": last_seen_ts or time.time(),
        }
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError:
            pass

    def check_license_status(self) -> dict:
        """Check current license status and return detailed info."""
        today = datetime.date.today()

        if self.clock_tampered:
            return {
                "tier": LicenseTier.EXPIRED.value,
                "tier_label": "EXPIRED (Clock Tamper Detected)",
                "is_active": False,
                "days_remaining": 0,
                "hwid": self.hwid,
                "clock_tampered": True,
                "message": "System clock manipulation detected. Licensing revoked.",
            }

        config = TIER_CONFIG.get(self.tier, TIER_CONFIG[LicenseTier.TRIAL_15_DAYS])
        days_allowed = config["days"]

        expiration_date = self.activation_date + datetime.timedelta(days=days_allowed)
        is_active = (today <= expiration_date) if self.tier != LicenseTier.EXPIRED else False
        days_remaining = max(0, (expiration_date - today).days) if is_active else 0

        return {
            "tier": self.tier.value,
            "tier_label": self.tier.value,
            "is_active": is_active,
            "days_remaining": days_remaining,
            "activation_date": str(self.activation_date),
            "expiration_date": str(expiration_date),
            "hwid": self.hwid,
            "license_key": self.license_key,
            "clock_tampered": False,
            "features": config["features"],
            "device_limit": config["device_limit"],
            "cloud_backup": config["cloud_backup"],
            "priority_support": config["priority_support"],
            "version": self.VERSION,
        }

    def generate_valid_key(self, prefix: str) -> str:
        """Generate a valid signed license key for a given prefix and current HWID."""
        raw = f"{prefix}-{self.hwid}-{self.SECRET_SALT}"
        checksum = hashlib.sha256(raw.encode()).hexdigest()[:8].upper()
        return f"{prefix}-{checksum}"

    def generate_6month_key(self) -> str:
        """Generate a 6-month professional license key."""
        return self.generate_valid_key("AT-6M")

    def generate_1year_key(self) -> str:
        """Generate a 1-year VIP license key."""
        return self.generate_valid_key("AT-1Y")

    def activate_key(self, key: str) -> bool:
        """Validate a license key against HWID signature check and store paid subscription."""
        key = key.strip().upper()
        if not key:
            return False

        parts = key.split("-")
        if len(parts) < 3:
            return False

        prefix = f"{parts[0]}-{parts[1]}"
        expected_key = self.generate_valid_key(prefix)

        if key == expected_key:
            if parts[1] == "6M":
                self.tier = LicenseTier.SIX_MONTHS
            elif parts[1] == "1Y":
                self.tier = LicenseTier.ONE_YEAR_VIP
            elif parts[1] == "15D":
                self.tier = LicenseTier.TRIAL_15_DAYS
            else:
                return False

            self.activation_date = datetime.date.today()
            self.license_key = key
            self.clock_tampered = False
            self._save_state()
            return True

        return False

    def deactivate(self) -> None:
        """Deactivate the current license."""
        self.tier = LicenseTier.EXPIRED
        self.license_key = ""
        self._save_state()

    def enforce_or_exit(self) -> dict:
        """Return status for system launch initialization."""
        return self.check_license_status()

    def has_feature(self, feature_name: str) -> bool:
        """Check if the current tier includes a specific feature."""
        config = TIER_CONFIG.get(self.tier, {})
        features = config.get("features", [])
        return any(feature_name.lower() in f.lower() for f in features)
