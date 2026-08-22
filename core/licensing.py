import datetime
import hashlib
from enum import Enum

class LicenseTier(Enum):
    TRIAL_15_DAYS = "15-Day Trial"
    SIX_MONTHS = "6 Months"
    ONE_YEAR = "1 Year"
    EXPIRED = "Expired"

class LicenseManager:
    """Handles license activation, cryptographic verification, and expiration tracking."""

    SECRET_SALT = "AuraToolSuite2025SecretKey"

    def __init__(self, activation_date: datetime.date = None, tier: LicenseTier = LicenseTier.TRIAL_15_DAYS):
        self.activation_date = activation_date or datetime.date.today()
        self.tier = tier
        self.license_key = ""

    def check_license_status(self) -> dict:
        today = datetime.date.today()

        if self.tier == LicenseTier.TRIAL_15_DAYS:
            days_allowed = 15
        elif self.tier == LicenseTier.SIX_MONTHS:
            days_allowed = 180
        elif self.tier == LicenseTier.ONE_YEAR:
            days_allowed = 365
        else:
            days_allowed = 0

        expiration_date = self.activation_date + datetime.timedelta(days=days_allowed)
        is_active = today <= expiration_date if self.tier != LicenseTier.EXPIRED else False

        return {
            "tier": self.tier.value,
            "is_active": is_active,
            "days_remaining": max(0, (expiration_date - today).days) if is_active else 0,
            "activation_date": str(self.activation_date),
            "expiration_date": str(expiration_date)
        }

    def generate_valid_key(self, prefix: str) -> str:
        """Generates a valid signed license key for a given prefix."""
        raw = f"{prefix}-{self.SECRET_SALT}"
        checksum = hashlib.sha256(raw.encode()).hexdigest()[:8].upper()
        return f"{prefix}-{checksum}"

    def activate_key(self, key: str) -> bool:
        """Validates license keys using cryptographic signature check and updates tier."""
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
                self.tier = LicenseTier.ONE_YEAR
            else:
                return False

            self.activation_date = datetime.date.today()
            self.license_key = key
            return True

        return False
