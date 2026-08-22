import logging
import sys

from core.licensing import LicenseManager
from core.api import APIClient
from drivers.driver_manager import DriverManager
from modules.flashing_engine import FlashingEngine
from modules.biometrics_fix import BiometricsFix
from modules.localization import LocalizationManager
from modules.smart_devices import SmartDeviceManager
from ui.app import AuraToolUI

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    logger = logging.getLogger("AuraTool.Main")
    
    logger.info("Initializing AuraTool-Suite...")

    # 1. Initialize License Manager
    license_mgr = LicenseManager()
    license_status = license_mgr.check_license_status()
    logger.info(f"License Status: {license_status['tier']} (Active: {license_status['is_active']})")

    # 2. Initialize Driver Infrastructure
    driver_mgr = DriverManager()
    drivers_ready = driver_mgr.initialize_drivers()

    # 3. Initialize Core Modules
    api_client = APIClient()
    flashing_engine = FlashingEngine()
    biometrics_fix = BiometricsFix()
    localization_mgr = LocalizationManager()
    smart_dev_mgr = SmartDeviceManager()

    # 4. Launch Graphical Interface
    logger.info("Starting UI application...")
    app = AuraToolUI(license_info=license_status, driver_status=drivers_ready)
    app.run()

if __name__ == "__main__":
    main()
