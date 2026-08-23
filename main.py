"""
AuraTool-Suite — Main Entry Point
===================================
Initialises every subsystem and launches the graphical interface.
Supports Windows and Linux Ubuntu from a single codebase.
"""

import logging
import sys

from core.licensing import LicenseManager
from core.api import APIClient
from core.security import SecurityManager
from drivers.driver_manager import DriverManager
from modules.flashing_engine import FlashingEngine
from modules.biometrics_fix import BiometricsFix
from modules.localization import LocalizationManager
from modules.smart_devices import SmartDeviceManager
from modules.data_recovery import DataRecoveryModule
from modules.account_repair import AccountRepairModule
from modules.aura_ai_assistant import AuraAIAssistant
from modules.ultimate_repair import UltimateRepairModule
from modules.android import AndroidDeviceManager
from modules.apple import AppleDeviceManager
from modules.download import DownloadManager
from ui.app import AuraToolUI


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger("AuraTool.Main")

    logger.info("=" * 60)
    logger.info("  AuraTool-Suite — Advanced Ecosystem Maintenance Framework")
    logger.info("  Version 2.0.0  |  Ecosystem Coverage: 2000 – 2030")
    logger.info("=" * 60)

    # ------------------------------------------------------------------ #
    #  1. Core Subsystems
    # ------------------------------------------------------------------ #
    logger.info("[1/6] Initializing core subsystems...")

    license_mgr = LicenseManager()
    license_status = license_mgr.check_license_status()
    logger.info(
        f"  License: {license_status['tier']} "
        f"(Active: {license_status['is_active']}, "
        f"Days left: {license_status['days_remaining']})"
    )

    security_mgr = SecurityManager()
    api_client = APIClient()

    # ------------------------------------------------------------------ #
    #  2. Driver Infrastructure
    # ------------------------------------------------------------------ #
    logger.info("[2/6] Initializing driver infrastructure...")

    driver_mgr = DriverManager()
    drivers_ready = driver_mgr.initialize_drivers()
    logger.info(f"  Drivers ready: {drivers_ready}")

    # ------------------------------------------------------------------ #
    #  3. Feature Modules
    # ------------------------------------------------------------------ #
    logger.info("[3/6] Loading feature modules...")

    flashing_engine = FlashingEngine()
    biometrics_fix = BiometricsFix()
    localization_mgr = LocalizationManager()
    smart_dev_mgr = SmartDeviceManager()
    data_recovery = DataRecoveryModule()
    account_repair = AccountRepairModule()

    # ------------------------------------------------------------------ #
    #  4. AI & Advanced Modules
    # ------------------------------------------------------------------ #
    logger.info("[4/6] Loading AI assistant and advanced repair engines...")

    ai_assistant = AuraAIAssistant()
    ultimate_repair = UltimateRepairModule()

    # ------------------------------------------------------------------ #
    #  5. Platform-Specific Device Managers
    # ------------------------------------------------------------------ #
    logger.info("[5/6] Loading platform device managers...")

    android_mgr = AndroidDeviceManager()
    apple_mgr = AppleDeviceManager()
    download_mgr = DownloadManager()

    # ------------------------------------------------------------------ #
    #  6. Launch GUI
    # ------------------------------------------------------------------ #
    logger.info("[6/6] Launching graphical interface...")

    app = AuraToolUI(
        license_info=license_status,
        driver_status=drivers_ready,
    )
    app.run()


if __name__ == "__main__":
    main()
