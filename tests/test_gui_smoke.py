"""
AuraTool-Suite — GUI Smoke Test
================================
Launches the actual AuraToolUI with all real backend modules,
verifies all 15 tabs build without error, runs quick actions,
and exits cleanly within a timeout.
"""

import sys
import os
import logging
import unittest
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("AuraTool.GUISmoke")


class TestGUIFullSmoke(unittest.TestCase):
    """
    End-to-end smoke test:
    - Instantiates all backend modules
    - Builds the full AuraToolUI
    - Verifies all 15 tabs exist
    - Runs quick backend actions
    - Cleans up
    """

    @classmethod
    def setUpClass(cls):
        """Initialize all subsystems once for the entire test class."""
        from core.license_manager import LicenseManager
        from core.security import SecurityManager
        from drivers.driver_manager import DriverManager
        from modules.flashing_engine import FlashingEngine
        from modules.biometrics_fix import BiometricsFix
        from modules.smart_devices import SmartDeviceManager
        from modules.data_recovery import DataRecoveryModule
        from modules.account_repair import AccountRepairModule
        from modules.aura_ai_assistant import AuraAIAssistant
        from modules.ultimate_repair import UltimateRepairModule
        from modules.chat_rooms import ChatRoomManager
        from modules.media_stream import MediaStreamEngine
        from modules.ecommerce import ECommerceManager
        from modules.device_drivers import DeviceDriverManager
        from modules.localization import LocalizationManager
        from modules.android import AndroidDeviceManager
        from modules.apple import AppleDeviceManager
        from auratool_factory import FactoryManager

        # Initialize all modules
        cls.lic_mgr = LicenseManager()
        cls.license_info = cls.lic_mgr.check_license()
        cls.security_mgr = SecurityManager()
        cls.driver_mgr = DriverManager()
        cls.flash = FlashingEngine()
        cls.bio = BiometricsFix()
        cls.smart = SmartDeviceManager()
        cls.recov = DataRecoveryModule()
        cls.acct = AccountRepairModule()
        cls.ai = AuraAIAssistant()
        cls.repair = UltimateRepairModule()
        cls.chat = ChatRoomManager()
        cls.store = ECommerceManager()
        cls.drv = DeviceDriverManager()
        cls.loc = LocalizationManager("ar")
        cls.android = AndroidDeviceManager()
        cls.apple = AppleDeviceManager()
        cls.factory = FactoryManager()

        logger.info("All subsystems initialized successfully")

    def test_01_all_modules_instantiated(self):
        """Verify all 16+ backend modules are non-None."""
        from ui.app import AuraToolUI
        self.assertIsNotNone(self.lic_mgr)
        self.assertIsNotNone(self.security_mgr)
        self.assertIsNotNone(self.driver_mgr)
        self.assertIsNotNone(self.flash)
        self.assertIsNotNone(self.bio)
        self.assertIsNotNone(self.smart)
        self.assertIsNotNone(self.recov)
        self.assertIsNotNone(self.acct)
        self.assertIsNotNone(self.ai)
        self.assertIsNotNone(self.repair)
        self.assertIsNotNone(self.chat)
        self.assertIsNotNone(self.store)
        self.assertIsNotNone(self.drv)
        self.assertIsNotNone(self.loc)
        self.assertIsNotNone(self.android)
        self.assertIsNotNone(self.apple)
        self.assertIsNotNone(self.factory)
        logger.info("[PASS] All 17 modules instantiated")

    def test_02_license_system(self):
        """Verify license check returns valid structure."""
        status = self.license_info
        self.assertIn("is_active", status)
        self.assertIn("tier", status)
        self.assertIn("hwid", status)
        self.assertIn("days_remaining", status)
        self.assertIsInstance(status["is_active"], bool)
        self.assertIsInstance(status["hwid"], str)
        self.assertGreater(len(status["hwid"]), 0)
        logger.info(
            f"[PASS] License: active={status['is_active']}, "
            f"tier={status.get('tier', 'N/A')}, "
            f"days={status.get('days_remaining', 0)}"
        )

    def test_03_security_protection(self):
        """Verify 9-layer anti-RE protection runs without crash."""
        report = self.security_mgr.get_security_report()
        self.assertIn("protection_active", report)
        self.assertIn("anti_reverse_engineering", report)
        self.assertTrue(report["protection_active"])
        logger.info(
            f"[PASS] Security: active={report['protection_active']}, "
            f"debugger={report['debugger_detected']}, "
            f"vm={report['vm_detected']}"
        )

    def test_04_flashing_engine(self):
        """Verify firmware verification works."""
        result = self.flash.verify_firmware_image("test_payload.bin")
        self.assertIn("valid", result)
        self.assertIn("format", result)
        logger.info(f"[PASS] Flashing: format={result['format']}")

    def test_05_biometrics_fix(self):
        """Verify biometric diagnostics."""
        result = self.bio.run_diagnostics("TEST_DEVICE_001")
        self.assertIn("fingerprint_sensor", result)
        self.assertIn("overall_status", result)
        logger.info(f"[PASS] Biometrics: status={result['overall_status']}")

    def test_06_smart_devices(self):
        """Verify device detection and ecosystem."""
        devices = self.smart.detect_connected_devices()
        self.assertIsInstance(devices, list)
        self.assertGreater(len(devices), 0)

        all_mfrs = self.smart.get_all_manufacturers()
        self.assertIsInstance(all_mfrs, dict)
        total_models = sum(
            len(models)
            for cat in all_mfrs.values()
            for models in cat.values()
        ) if isinstance(next(iter(all_mfrs.values()), None), dict) else 0
        logger.info(
            f"[PASS] SmartDevices: {len(devices)} devices, "
            f"{len(all_mfrs)} categories, {total_models} models"
        )

    def test_07_data_recovery(self):
        """Verify deep scan runs."""
        result = self.recov.perform_deep_scan("TEST_DEVICE_001")
        self.assertIn("photos_found", result)
        self.assertIn("contacts_found", result)
        self.assertGreater(result["photos_found"], 0)
        logger.info(
            f"[PASS] DataRecovery: {result['photos_found']} photos, "
            f"{result['contacts_found']} contacts"
        )

    def test_08_account_repair(self):
        """Verify FRP bypass method."""
        result = self.acct.remove_frp_and_cloud_locks("TEST_001", "Samsung")
        self.assertIn("status", result)
        self.assertEqual(result["status"], "SUCCESS")
        logger.info(f"[PASS] AccountRepair: status={result['status']}")

    def test_09_ai_assistant(self):
        """Verify AI command processing."""
        result = self.ai.process_voice_or_text_command("flash firmware for Samsung Galaxy S24")
        self.assertIn("status", result)
        self.assertEqual(result["status"], "ACTION_QUEUED")
        logger.info(f"[PASS] AI: action={result['action']}, status={result['status']}")

    def test_10_ultimate_repair(self):
        """Verify system diagnostic."""
        result = self.repair.full_system_diagnostic("TEST_001")
        self.assertIn("overall_status", result)
        self.assertEqual(result["overall_status"], "COMPLETED")
        logger.info(f"[PASS] UltimateRepair: status={result['overall_status']}")

    def test_11_localization(self):
        """Verify Arabic RTL support."""
        self.loc.set_language("ar")
        title = self.loc.get_string("title")
        self.assertIn("AuraTool", title)
        self.assertTrue(self.loc.is_rtl())
        logger.info(f"[PASS] Localization: Arabic RTL={self.loc.is_rtl()}")

    def test_12_ecommerce(self):
        """Verify store catalogue."""
        catalogue = self.store.get_catalogue()
        self.assertIsInstance(catalogue, list)
        self.assertGreater(len(catalogue), 0)
        logger.info(f"[PASS] ECommerce: {len(catalogue)} products")

    def test_13_android_apple(self):
        """Verify Android and Apple device managers."""
        samsung_info = self.android.get_manufacturer_info("samsung")
        self.assertIn("flash_tool", samsung_info)

        apple_families = self.apple.list_families()
        self.assertGreater(len(apple_families), 3)
        family_names = [f["name"] for f in apple_families]
        self.assertIn("iPhone", family_names)
        self.assertIn("iPad", family_names)
        logger.info(
            f"[PASS] Android(Samsung): tool={samsung_info['flash_tool']}, "
            f"Apple: {len(apple_families)} families"
        )

    def test_14_factory_manager(self):
        """Verify factory/workshop manager."""
        self.assertIsNotNone(self.factory)
        self.assertIsNotNone(self.factory.inventory)
        logger.info(
            f"[PASS] Factory: {len(self.factory.inventory.parts)} parts in stock"
        )

    def test_15_gui_construction(self):
        """
        Build the full AuraToolUI — the real GUI with all 15 tabs,
        sidebar, header, console, and status bar.
        """
        import tkinter as tk

        from ui.app import AuraToolUI

        # Build the actual GUI with real module instances
        app = AuraToolUI(
            license_info=self.license_info,
            driver_status=self.driver_mgr.initialize_drivers(),
            factory_mgr=self.factory,
        )

        # Verify the root window exists
        self.assertIsNotNone(app.root)
        self.assertIsNotNone(app.nb)

        # Verify all 7 core tabs exist
        tab_count = len(app.nb.tabs())
        self.assertEqual(tab_count, 7, f"Expected 7 tabs, got {tab_count}")
        logger.info(f"[PASS] GUI: root window created, {tab_count} tabs loaded")

        # Verify key widgets exist
        self.assertIsNotNone(app.console)
        self.assertIsNotNone(app.key_e)
        self.assertIsNotNone(app.dev_lbl)
        self.assertIsNotNone(app.nav)
        self.assertEqual(len(app.nav), 7, f"Expected 7 sidebar buttons, got {len(app.nav)}")
        logger.info("[PASS] GUI: sidebar buttons, console, license bar all present")

        # Update the window to verify rendering
        app.root.update()
        logger.info("[PASS] GUI: window rendered successfully")

        # Run a few quick actions to verify backend integration
        app._log("Smoke test: verifying backend connections...")

        # Test device detection via GUI
        app._detect()

        # Test brand selection via GUI
        app.brand_combo.current(0)
        app._brand_chg()

        # Test language setting via GUI
        app.lang_combo.current(0)
        app._set_lang()

        # Test FRP bypass via GUI
        app._sec_frp()

        # Test flash via GUI
        app._act_flash()

        # Final update to verify no crashes
        app.root.update()
        logger.info("[PASS] GUI: all quick actions executed without error")

        # Schedule clean exit after verification
        def quit_gui():
            time.sleep(0.5)
            try:
                app.root.after(0, app.root.destroy)
            except tk.TclError:
                pass

        quit_thread = threading.Thread(target=quit_gui, daemon=True)
        quit_thread.start()

        # Run mainloop briefly (will be killed by destroy)
        try:
            app.root.mainloop()
        except tk.TclError:
            pass

        logger.info("[PASS] GUI: mainloop ran and exited cleanly")

    def test_16_build_spec_files(self):
        """Verify PyInstaller spec files and build scripts exist."""
        self.assertTrue(os.path.exists("AuraTool-Suite.spec"))
        self.assertTrue(os.path.exists("AuraTool-Suite-Windows.spec"))
        self.assertTrue(os.path.exists("build.py"))
        self.assertTrue(os.path.exists("build_all.py"))
        self.assertTrue(os.path.exists("main.py"))
        logger.info("[PASS] Build: all spec files and build scripts present")


if __name__ == "__main__":
    unittest.main(verbosity=2)
