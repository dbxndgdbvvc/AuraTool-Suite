"""
AuraTool-Suite — Smart Licensing Engine
=========================================
Flexible licensing system providing:
  - 15-Day Free Trial (fully featured)
  - 6-Month Professional Plan
  - 1-Year Ultimate Plan (VIP) with continuous updates valid through 2030
  - Cryptographic key verification and expiration tracking
"""

import datetime
import hashlib
import secrets
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


class LicenseManager:
    """
    Handles license activation, cryptographic verification, expiration
    tracking, and feature-gating across the AuraTool-Suite ecosystem.
    """

    SECRET_SALT = "AuraToolSuite2025SecretKey"
    VERSION = "2.0.0"

    def __init__(
        self,
        activation_date: datetime.date = None,
        tier: LicenseTier = LicenseTier.TRIAL_15_DAYS,
    ):
        self.activation_date = activation_date or datetime.date.today()
        self.tier = tier
        self.license_key = ""
        self.logger_name = "AuraTool.License"

    # ================================================================== #
    #  STATUS CHECK
    # ================================================================== #

    def check_license_status(self) -> dict:
        """Check current license status and return detailed info."""
        today = datetime.date.today()
        config = TIER_CONFIG.get(self.tier, TIER_CONFIG[LicenseTier.TRIAL_15_DAYS])
        days_allowed = config["days"]

        expiration_date = self.activation_date + datetime.timedelta(days=days_allowed)
        is_active = (today <= expiration_date) if self.tier != LicenseTier.EXPIRED else False

        return {
            "tier": self.tier.value,
            "is_active": is_active,
            "days_remaining": max(0, (expiration_date - today).days) if is_active else 0,
            "activation_date": str(self.activation_date),
            "expiration_date": str(expiration_date),
            "features": config["features"],
            "device_limit": config["device_limit"],
            "cloud_backup": config["cloud_backup"],
            "priority_support": config["priority_support"],
            "version": self.VERSION,
            "supported_until_year": 2030 if self.tier == LicenseTier.ONE_YEAR_VIP else None,
        }

    # ================================================================== #
    #  KEY GENERATION & ACTIVATION
    # ================================================================== #

    def generate_valid_key(self, prefix: str) -> str:
        """Generate a valid signed license key for a given prefix."""
        raw = f"{prefix}-{self.SECRET_SALT}"
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
        """
        Validate a license key using cryptographic signature check
        and update the tier accordingly.
        """
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

    # ================================================================== #
    #  FEATURE GATING
    # ================================================================== #

    def has_feature(self, feature_name: str) -> bool:
        """Check if the current tier includes a specific feature."""
        config = TIER_CONFIG.get(self.tier, {})
        features = config.get("features", [])
        return any(feature_name.lower() in f.lower() for f in features)

    def can_use_device(self, current_count: int = 0) -> bool:
        """Check if the user can add another device under their plan."""
        config = TIER_CONFIG.get(self.tier, {})
        limit = config.get("device_limit", 0)
        if limit == -1:
            return True  # Unlimited
        return current_count < limit

    def get_all_tiers(self) -> dict:
        """Return all available tier configurations."""
        result = {}
        for tier, config in TIER_CONFIG.items():
            result[tier.value] = {
                "days": config["days"],
                "features": config["features"],
                "device_limit": config["device_limit"],
                "cloud_backup": config["cloud_backup"],
                "priority_support": config["priority_support"],
            }
        return result
