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
from modules.chat_rooms import ChatRoomManager
from modules.media_stream import MediaStreamEngine
from modules.ecommerce import ECommerceManager
from auratool_factory import FactoryManager
from ui.app import AuraToolUI


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger("AuraTool.Main")

    logger.info("=" * 60)
    logger.info("  AuraTool-Suite — Mobile Device Maintenance & Repair Framework")
    logger.info("  Version 2.0.0  |  Ecosystem Coverage: 2000 – 2030")
    logger.info("=" * 60)

    # 1. Core Subsystems & HWID Encrypted License Check
    logger.info("[1/7] Initializing core subsystems & HWID verification...")
    license_mgr = LicenseManager()
    license_status = license_mgr.enforce_or_exit()

    if not license_status["is_active"]:
        logger.critical(
            "License expired or invalid (tier: %s, HWID: %s). Exiting.",
            license_status["tier_label"],
            license_status["hwid"],
        )
        sys.exit(1)

    logger.info(
        f"  HWID: {license_status['hwid']} | License: {license_status['tier_label']} "
        f"(Active: {license_status['is_active']}, Days left: {license_status['days_remaining']})"
    )

    security_mgr = SecurityManager()
    api_client = APIClient()

    # 2. Driver Infrastructure
    logger.info("[2/7] Initializing driver infrastructure...")
    driver_mgr = DriverManager()
    drivers_ready = driver_mgr.initialize_drivers()
    logger.info(f"  Drivers status: {drivers_ready}")

    # 3. Feature & AI Modules
    logger.info("[3/7] Loading maintenance & AI feature modules...")
    flashing_engine = FlashingEngine()
    biometrics_fix = BiometricsFix()
    localization_mgr = LocalizationManager()
    smart_dev_mgr = SmartDeviceManager()
    data_recovery = DataRecoveryModule()
    account_repair = AccountRepairModule()
    ai_assistant = AuraAIAssistant()
    ultimate_repair = UltimateRepairModule()

    # 4. Chat, Streaming & E-Commerce Subsystems
    logger.info("[4/7] Loading Live Chat, Media Streaming & E-Commerce Store...")
    chat_mgr = ChatRoomManager()
    media_stream = MediaStreamEngine()
    ecommerce_mgr = ECommerceManager()

    # 5. Factory / Workshop Subsystem
    logger.info("[5/7] Initializing workshop & factory manager...")
    factory_mgr = FactoryManager()
    logger.info(f"  Factory initialized ({len(factory_mgr.inventory.parts)} parts in stock).")

    # 6. Launch Desktop Native GUI
    logger.info("[6/7] Launching graphical desktop interface...")
    app = AuraToolUI(
        license_info=license_status,
        driver_status=drivers_ready,
        factory_mgr=factory_mgr,
    )
    app.run()


if __name__ == "__main__":
    main()
