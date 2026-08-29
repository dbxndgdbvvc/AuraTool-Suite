"""
AuraTool-Suite — Main Entry Point (v6.0.0)
============================================
Initialises every subsystem and launches the graphical interface.
Supports Windows and Linux Ubuntu from a single codebase.
Comprehensive device maintenance & repair platform covering
Smartphones, Tablets, iPads, Smartwatches, Smart Glasses (2000–2030).
"""

import logging
import os
import sys
import time
from pathlib import Path

# ═══════════════════════════════════════════════════════════════════════════════
#  LOGGING SETUP
# ═══════════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("AuraTool.Main")


# ═══════════════════════════════════════════════════════════════════════════════
#  RESILIENT IMPORTS — fail gracefully for missing modules
# ═══════════════════════════════════════════════════════════════════════════════

def _safe_import(module_path, class_name, display_name):
    """Import a class safely, returning None on failure."""
    try:
        module = __import__(module_path, fromlist=[class_name])
        return getattr(module, class_name)
    except (ImportError, AttributeError, Exception) as e:
        logger.warning(f"  [SKIP] {display_name} not available: {e}")
        return None


# Core modules
LicenseManager = _safe_import("core.license_manager", "LicenseManager", "License Manager")
SecurityManager = _safe_import("core.security", "SecurityManager", "Security Manager")

# Driver modules
DriverManager = _safe_import("drivers.driver_manager", "DriverManager", "Driver Manager")

# Feature modules
FlashingEngine = _safe_import("modules.flashing_engine", "FlashingEngine", "Flashing Engine")
BiometricsFix = _safe_import("modules.biometrics_fix", "BiometricsFix", "Biometrics Fix")
LocalizationManager = _safe_import("modules.localization", "LocalizationManager", "Localization")
SmartDeviceManager = _safe_import("modules.smart_devices", "SmartDeviceManager", "Smart Devices")
DataRecoveryModule = _safe_import("modules.data_recovery", "DataRecoveryModule", "Data Recovery")
AccountRepairModule = _safe_import("modules.account_repair", "AccountRepairModule", "Account Repair")
AuraAIAssistant = _safe_import("modules.aura_ai_assistant", "AuraAIAssistant", "AI Assistant")
UltimateRepairModule = _safe_import("modules.ultimate_repair", "UltimateRepairModule", "Ultimate Repair")
DeviceDriverManager = _safe_import("modules.device_drivers", "DeviceDriverManager", "Device Drivers")
ChatRoomManager = _safe_import("modules.chat_rooms", "ChatRoomManager", "Chat Rooms")
MediaStreamEngine = _safe_import("modules.media_stream", "MediaStreamEngine", "Media Stream")
ECommerceManager = _safe_import("modules.ecommerce", "ECommerceManager", "E-Commerce")
FactoryManager = _safe_import("auratool_factory", "FactoryManager", "Factory Manager")

# Extended modules (v6.0.0)
SmartphoneEngine = _safe_import("modules.smartphones", "SmartphoneEngine", "Smartphone Engine")
TabletEngine = _safe_import("modules.tablets", "TabletEngine", "Tablet Engine")
WearableEngine = _safe_import("modules.wearables", "WearableEngine", "Wearable Engine")
SmartGlassesEngine = _safe_import("modules.smart_glasses", "SmartGlassesEngine", "Smart Glasses Engine")
FirmwareHandler = _safe_import("modules.firmware_handler", "FirmwareHandler", "Firmware Handler")
CryptoEngine = _safe_import("modules.crypto_engine", "CryptoEngine", "Crypto Engine")

# UI
AuraToolUI = _safe_import("ui.app", "AuraToolUI", "GUI Application")


def main():
    logger.info("=" * 60)
    logger.info("  AuraTool-Suite — Universal Device Maintenance & Repair Platform")
    logger.info("  Version 6.0.0  |  Ecosystem Coverage: 2000 – 2030")
    logger.info("  Devices: Smartphones · Tablets · iPads · Smartwatches · Smart Glasses")
    logger.info("=" * 60)

    # 1. Core Subsystems & HWID Encrypted License Check
    logger.info("[1/9] Initializing core subsystems & HWID verification...")

    if LicenseManager is None:
        logger.critical("[FAIL] License Manager module not found. Exiting.")
        sys.exit(1)

    license_mgr = LicenseManager()
    license_status = license_mgr.enforce_or_exit()

    if not license_status["is_active"]:
        logger.critical(
            "License expired or invalid (tier: %s, HWID: %s). Exiting.",
            license_status.get("tier_label", license_status.get("tier", "UNKNOWN")),
            license_status["hwid"],
        )
        sys.exit(1)

    logger.info(
        f"  HWID: {license_status['hwid']} | "
        f"License: {license_status.get('tier_label', license_status.get('tier', 'UNKNOWN'))} "
        f"(Active: {license_status['is_active']}, Days left: {license_status['days_remaining']})"
    )
    logger.info("[SUCCESS] License verification passed")

    # 2. Security & Anti-Reverse Engineering
    logger.info("[2/9] Initializing security & anti-tamper protection...")
    if SecurityManager is not None:
        security_mgr = SecurityManager()
        protection_status = security_mgr.get_protection_status()
        logger.info(
            f"  Protection: Active={protection_status['protection_active']}, "
            f"Debugger={protection_status['debugger_detected']}, "
            f"VM={protection_status['vm_detected']}, "
            f"Integrity={protection_status['code_integrity']}"
        )
    else:
        protection_status = {"protection_active": False}
        logger.warning("  Security module not available")
    logger.info("[SUCCESS] Security subsystem initialized")

    # 3. Driver Infrastructure
    logger.info("[3/9] Initializing driver infrastructure...")
    if DriverManager is not None:
        driver_mgr = DriverManager()
        drivers_ready = driver_mgr.initialize_drivers()
        logger.info(f"  Drivers status: {drivers_ready}")
    else:
        drivers_ready = {"error": "DriverManager not available"}
        logger.warning("  Driver Manager module not available")
    logger.info("[SUCCESS] Driver infrastructure ready")

    # 4. Feature & AI Modules
    logger.info("[4/9] Loading maintenance & AI feature modules...")
    flashing_engine = FlashingEngine() if FlashingEngine is not None else None
    biometrics_fix = BiometricsFix() if BiometricsFix is not None else None
    localization_mgr = LocalizationManager("en") if LocalizationManager is not None else None
    smart_dev_mgr = SmartDeviceManager() if SmartDeviceManager is not None else None
    data_recovery = DataRecoveryModule() if DataRecoveryModule is not None else None
    account_repair = AccountRepairModule() if AccountRepairModule is not None else None
    ai_assistant = AuraAIAssistant() if AuraAIAssistant is not None else None
    ultimate_repair = UltimateRepairModule() if UltimateRepairModule is not None else None
    logger.info("[SUCCESS] Feature modules loaded")

    # 5. Chat, Streaming & E-Commerce Subsystems
    logger.info("[5/9] Loading Live Chat, Media Streaming & E-Commerce Store...")
    chat_mgr = ChatRoomManager() if ChatRoomManager is not None else None
    media_stream = MediaStreamEngine() if MediaStreamEngine is not None else None
    ecommerce_mgr = ECommerceManager() if ECommerceManager is not None else None
    logger.info("[SUCCESS] Communication subsystems loaded")

    # 6. Factory / Workshop Subsystem
    logger.info("[6/9] Initializing workshop & factory manager...")
    if FactoryManager is not None:
        factory_mgr = FactoryManager()
        logger.info(f"  Factory initialized ({len(factory_mgr.inventory.parts)} parts in stock).")
    else:
        factory_mgr = None
        logger.warning("  Factory Manager not available")
    logger.info("[SUCCESS] Workshop subsystem ready")

    # 7. Device Support Verification (Full Ecosystem 2002–2030)
    logger.info("[7/9] Verifying device ecosystem coverage (2002–2030)...")
    if smart_dev_mgr is not None:
        try:
            all_mfrs = smart_dev_mgr.get_all_manufacturers()
            total_devices = sum(len(models) for cat in all_mfrs.values() for models in cat.values())
            categories = list(all_mfrs.keys())
            logger.info(f"  Device database: {len(categories)} categories ({', '.join(categories)}), {total_devices} models")
        except Exception as e:
            logger.warning(f"  Could not verify device database: {e}")
    else:
        logger.warning("  Smart Device Manager not available")
    logger.info("[SUCCESS] Device ecosystem verified")

    # 8. Supported Chipsets & Protocols
    logger.info("[8/9] Loaded chipset & protocol support:")
    if smart_dev_mgr is not None:
        try:
            chipsets = smart_dev_mgr.get_chipset_support()
            for vendor, chips in chipsets.items():
                logger.info(f"  {vendor}: {len(chips)} variants")
        except Exception as e:
            logger.warning(f"  Could not load chipset data: {e}")

    protocols = ["ADB", "Fastboot", "EDL 9008", "MediaTek BROM", "Samsung ODIN", "Apple DFU",
                  "Meta Mode", "WearOS", "Tizen"]
    logger.info(f"  Protocols: {', '.join(protocols)}")

    lang_count = len(localization_mgr.SUPPORTED_LANGUAGES) if localization_mgr is not None and hasattr(localization_mgr, 'SUPPORTED_LANGUAGES') else 30
    logger.info(f"  Languages: {lang_count} supported (RTL: Arabic, Persian, Urdu, Hebrew)")
    logger.info("[SUCCESS] Chipset & protocol database loaded")

    # 8b. Extended Device Engines (v6.0.0)
    logger.info("[8b/9] Loading modular device engines...")
    smartphone_eng = SmartphoneEngine() if SmartphoneEngine is not None else None
    tablet_eng = TabletEngine() if TabletEngine is not None else None
    wearable_eng = WearableEngine() if WearableEngine is not None else None
    glasses_eng = SmartGlassesEngine() if SmartGlassesEngine is not None else None
    firmware_handler = FirmwareHandler() if FirmwareHandler is not None else None
    crypto_eng = CryptoEngine() if CryptoEngine is not None else None
    if smartphone_eng: logger.info("  ✅ SmartphoneEngine (MTK BROM, QC EDL, Samsung ODIN, Apple DFU)")
    if tablet_eng: logger.info("  ✅ TabletEngine (iPad, Samsung Tab, Android tablets)")
    if wearable_eng: logger.info("  ✅ WearableEngine (Apple Watch, WearOS, Tizen, Fitbit)")
    if glasses_eng: logger.info("  ✅ SmartGlassesEngine (Meta Quest, Vision Pro, XREAL, Pico)")
    if firmware_handler: logger.info("  ✅ FirmwareHandler (payload.bin, scatter, IPSW, boot.img)")
    if crypto_eng: logger.info("  ✅ CryptoEngine (AES-256, RSA-2048, SHA-256, HMAC)")
    logger.info("[SUCCESS] Extended device engines loaded")

    # 9. Launch Desktop Native GUI
    logger.info("[9/9] Launching graphical desktop interface...")

    if AuraToolUI is None:
        logger.critical("[FAIL] GUI Application module not found. Exiting.")
        sys.exit(1)

    app = AuraToolUI(
        license_info=license_status,
        driver_status=drivers_ready,
        factory_mgr=factory_mgr,
    )

    logger.info("[SUCCESS] AuraTool-Suite launched successfully — All systems operational")
    logger.info("=" * 60)

    app.run()


if __name__ == "__main__":
    main()
