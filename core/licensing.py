"""
AuraTool-Suite — Smart Licensing Engine with Hardware ID (HWID) Binding
========================================================================
Flexible licensing system providing:
  - HWID generation (CPU/Motherboard/Disk/Hostname fingerprinting)
  - 15-Day Free Trial (fully featured)
  - 6-Month Professional Plan
  - 1-Year Ultimate Plan (VIP) through 2030
  - Cryptographic key verification bound to unique machine HWID
"""

import datetime
import hashlib
import platform
import subprocess
import os
from enum import Enum


class LicenseTier(Enum):
    TRIAL_15_DAYS = "15-Day Trial"
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
    Handles license activation, HWID binding, cryptographic verification,
    expiration tracking, and feature-gating across AuraTool-Suite.
    """

    SECRET_SALT = "AuraToolSuite2030SecretKey"
    VERSION = "2.0.0"

    def __init__(
        self,
        activation_date: datetime.date = None,
        tier: LicenseTier = LicenseTier.TRIAL_15_DAYS,
    ):
        self.activation_date = activation_date or datetime.date.today()
        self.tier = tier
        self.license_key = ""
        self.hwid = get_hardware_id()

    def check_license_status(self) -> dict:
        """Check current license status and return detailed info."""
        today = datetime.date.today()
        config = TIER_CONFIG.get(self.tier, TIER_CONFIG[LicenseTier.TRIAL_15_DAYS])
        days_allowed = config["days"]

        expiration_date = self.activation_date + datetime.timedelta(days=days_allowed)
        is_active = (today <= expiration_date) if self.tier != LicenseTier.EXPIRED else False

        return {
            "tier": self.tier.value,
            "tier_label": self.tier.value,
            "is_active": is_active,
            "days_remaining": max(0, (expiration_date - today).days) if is_active else 0,
            "activation_date": str(self.activation_date),
            "expiration_date": str(expiration_date),
            "hwid": self.hwid,
            "features": config["features"],
            "device_limit": config["device_limit"],
            "cloud_backup": config["cloud_backup"],
            "priority_support": config["priority_support"],
            "version": self.VERSION,
            "supported_until_year": 2030 if self.tier == LicenseTier.ONE_YEAR_VIP else None,
        }

    def generate_valid_key(self, prefix: str) -> str:
        """Generate a valid signed license key for a given prefix and current HWID."""
        raw = f"{prefix}-{self.hwid}-{self.SECRET_SALT}"
        checksum = hashlib.sha256(raw.encode()).hexdigest()[:8].upper()
        return f"{prefix}-{checksum}"

    def generate_trial_key(self) -> str:
        """Generate a 15-day trial license key."""
        return self.generate_valid_key("AT-15D")

    def generate_professional_key(self) -> str:
        """Generate a 6-month professional license key."""
        return self.generate_valid_key("AT-6M")

    def generate_vip_key(self) -> str:
        """Generate a 1-year VIP license key (valid through 2030)."""
        return self.generate_valid_key("AT-1Y")

    def activate_key(self, key: str) -> bool:
        """Validate a license key against HWID signature check."""
        key = key.strip().upper()
        if not key:
            return False

        parts = key.split("-")
        if len(parts) < 3:
            return False

        prefix = f"{parts[0]}-{parts[1]}"
        expected_key = self.generate_valid_key(prefix)

        if key == expected_key:
            if parts[1] == "15D":
                self.tier = LicenseTier.TRIAL_15_DAYS
            elif parts[1] == "6M":
                self.tier = LicenseTier.SIX_MONTHS
            elif parts[1] == "1Y":
                self.tier = LicenseTier.ONE_YEAR_VIP
            else:
                return False

            self.activation_date = datetime.date.today()
            self.license_key = key
            return True

        return False

    def deactivate(self) -> None:
        """Deactivate the current license."""
        self.tier = LicenseTier.EXPIRED
        self.license_key = ""

    def enforce_or_exit(self) -> dict:
        """Return status for system launch initialization."""
        return self.check_license_status()

    def has_feature(self, feature_name: str) -> bool:
        """Check if the current tier includes a specific feature."""
        config = TIER_CONFIG.get(self.tier, {})
        features = config.get("features", [])
        return any(feature_name.lower() in f.lower() for f in features)
