import datetime
from enum import Enum

class LicenseTier(Enum):
    TRIAL_15_DAYS = "15-Day Trial"
    SIX_MONTHS = "6 Months"
    ONE_YEAR = "1 Year"
    EXPIRED = "Expired"

class LicenseManager:
    """Handles license activation, verification, and expiration tracking."""
    
    def __init__(self, activation_date: datetime.date = None, tier: LicenseTier = LicenseTier.TRIAL_15_DAYS):
        self.activation_date = activation_date or datetime.date.today()
        self.tier = tier

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
        is_active = today <= expiration_date

        return {
            "tier": self.tier.value,
            "is_active": is_active,
            "days_remaining": max(0, (expiration_date - today).days),
            "expiration_date": str(expiration_date)
        }

    def activate_key(self, key: str) -> bool:
        """Validates license keys and updates tier accordingly."""
        if key.startswith("AURA-6M-"):
            self.tier = LicenseTier.SIX_MONTHS
            self.activation_date = datetime.date.today()
            return True
        elif key.startswith("AURA-1Y-"):
            self.tier = LicenseTier.ONE_YEAR
            self.activation_date = datetime.date.today()
            return True
        return False
