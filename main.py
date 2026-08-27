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
    logger.info("  AuraTool-Suite — Universal Device Maintenance & Repair Platform")
    logger.info("  Version 3.0.0  |  Ecosystem Coverage: 2002 – 2030")
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

    # 2. Security & Anti-Reverse Engineering
    logger.info("[2/9] Initializing security & anti-tamper protection...")
    security_mgr = SecurityManager()
    protection_status = security_mgr.get_protection_status()
    logger.info(f"  Protection: Active={protection_status['protection_active']}, "
                f"Debugger={protection_status['debugger_detected']}, "
                f"VM={protection_status['vm_detected']}, "
                f"Integrity={protection_status['code_integrity']}")

    # 3. Driver Infrastructure
    logger.info("[3/9] Initializing driver infrastructure...")
    driver_mgr = DriverManager()
    drivers_ready = driver_mgr.initialize_drivers()
    logger.info(f"  Drivers status: {drivers_ready}")

    # 4. Feature & AI Modules
    logger.info("[4/9] Loading maintenance & AI feature modules...")
    flashing_engine = FlashingEngine()
    biometrics_fix = BiometricsFix()
    localization_mgr = LocalizationManager()
    smart_dev_mgr = SmartDeviceManager()
    data_recovery = DataRecoveryModule()
    account_repair = AccountRepairModule()
    ai_assistant = AuraAIAssistant()
    ultimate_repair = UltimateRepairModule()

    # 5. Chat, Streaming & E-Commerce Subsystems
    logger.info("[5/9] Loading Live Chat, Media Streaming & E-Commerce Store...")
    chat_mgr = ChatRoomManager()
    media_stream = MediaStreamEngine()
    ecommerce_mgr = ECommerceManager()

    # 6. Factory / Workshop Subsystem
    logger.info("[6/9] Initializing workshop & factory manager...")
    factory_mgr = FactoryManager()
    logger.info(f"  Factory initialized ({len(factory_mgr.inventory.parts)} parts in stock).")

    # 7. Device Support Verification
    logger.info("[7/9] Verifying device ecosystem coverage...")
    all_mfrs = smart_dev_mgr.get_all_manufacturers()
    total_devices = sum(len(models) for cat in all_mfrs.values() for models in cat.values())
    logger.info(f"  Device database: {len(all_mfrs)} categories, {total_devices} models (2002–2030)")

    # 8. Supported Chipsets
    logger.info("[8/9] Loaded chipset support:")
    chipsets = smart_dev_mgr.get_chipset_support()
    for vendor, chips in chipsets.items():
        logger.info(f"  {vendor}: {len(chips)} variants")

    # 9. Launch Desktop Native GUI
    logger.info("[9/9] Launching graphical desktop interface...")
    app = AuraToolUI(
        license_info=license_status,
        driver_status=drivers_ready,
        factory_mgr=factory_mgr,
    )
    app.run()


if __name__ == "__main__":
    main()
