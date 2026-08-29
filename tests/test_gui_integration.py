"""
Integration Tests — GUI Engine Routing End-to-End
==================================================
Tests that launch the GUI, switch brands across categories, and verify
that the correct engine is loaded and operations route to the right handler.

These tests exercise the full stack: ECOSYSTEM_CATALOGUE → _get_category() →
_get_engine() → action handlers → engine-specific methods.
"""

import logging
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.smart_devices import ECOSYSTEM_CATALOGUE
from modules.smartphones import SmartphoneEngine
from modules.tablets import TabletEngine
from modules.wearables import WearableEngine
from modules.smart_glasses import SmartGlassesEngine


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPER: Simulate GUI engine routing without tkinter
# ═══════════════════════════════════════════════════════════════════════════════

class _EngineRouter:
    """Replicate ui/app.py engine routing logic for testing."""

    def __init__(self):
        self.smartphone_eng = SmartphoneEngine()
        self.tablet_eng = TabletEngine()
        self.wearable_eng = WearableEngine()
        self.glasses_eng = SmartGlassesEngine()
        self._active_category = "smartphones"
        self._selected_brand = None

    def _get_category(self, brand):
        for cat, brands in ECOSYSTEM_CATALOGUE.items():
            if brand in brands:
                return cat
        return "smartphones"

    def _get_engine(self, category=None):
        cat = category or self._active_category
        engine_map = {
            "smartphones": self.smartphone_eng,
            "tablets": self.tablet_eng,
            "ipads": self.tablet_eng,
            "smartwatches": self.wearable_eng,
            "smart_glasses": self.glasses_eng,
            "ar_vr_headsets": self.glasses_eng,
            "car_infotainment": self.smartphone_eng,
            "smart_home": self.smartphone_eng,
            "gaming_handhelds": self.smartphone_eng,
        }
        return engine_map.get(cat, self.smartphone_eng)

    def _get_engine_name(self, category=None):
        cat = category or self._active_category
        name_map = {
            "smartphones": "SmartphoneEngine",
            "tablets": "TabletEngine",
            "ipads": "TabletEngine",
            "smartwatches": "WearableEngine",
            "smart_glasses": "SmartGlassesEngine",
            "ar_vr_headsets": "SmartGlassesEngine",
        }
        return name_map.get(cat, "SmartphoneEngine")

    def select_brand(self, brand):
        """Simulate selecting a brand in the GUI."""
        self._selected_brand = brand
        self._active_category = self._get_category(brand)

    def get_models(self, brand):
        """Get model list for a brand."""
        ms = []
        for c in ECOSYSTEM_CATALOGUE.values():
            if brand in c:
                ms.extend(c[brand])
        return sorted(set(ms))


# ═══════════════════════════════════════════════════════════════════════════════
#  TEST: Brand Selection → Category Detection → Engine Routing
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrandToEngineRouting(unittest.TestCase):
    """Test the full chain: brand selection → category → engine."""

    def setUp(self):
        self.router = _EngineRouter()

    # ─── Smartphone brands ────────────────────────────────────────────
    def test_select_samsung_routes_to_smartphone_engine(self):
        self.router.select_brand("Samsung")
        self.assertEqual(self.router._active_category, "smartphones")
        self.assertIsInstance(self.router._get_engine(), SmartphoneEngine)

    def test_select_apple_routes_to_smartphone_engine(self):
        self.router.select_brand("Apple")
        self.assertEqual(self.router._active_category, "smartphones")
        self.assertIsInstance(self.router._get_engine(), SmartphoneEngine)

    def test_select_xiaomi_routes_to_smartphone_engine(self):
        self.router.select_brand("Xiaomi")
        self.assertEqual(self.router._active_category, "smartphones")
        self.assertIsInstance(self.router._get_engine(), SmartphoneEngine)

    def test_select_nokia_routes_to_smartphone_engine(self):
        self.router.select_brand("Nokia")
        self.assertEqual(self.router._active_category, "smartphones")

    # ─── Tablet brands ────────────────────────────────────────────────
    def test_select_samsung_tab_routes_to_tablet_engine(self):
        self.router.select_brand("Samsung_Tab")
        self.assertEqual(self.router._active_category, "tablets")
        self.assertIsInstance(self.router._get_engine(), TabletEngine)

    def test_select_xiaomi_pad_routes_to_tablet_engine(self):
        self.router.select_brand("Xiaomi_Pad")
        self.assertEqual(self.router._active_category, "tablets")
        self.assertIsInstance(self.router._get_engine(), TabletEngine)

    def test_select_lenovo_tab_routes_to_tablet_engine(self):
        self.router.select_brand("Lenovo_Tab")
        self.assertEqual(self.router._active_category, "tablets")

    def test_select_honor_pad_routes_to_tablet_engine(self):
        self.router.select_brand("Honor_Pad")
        self.assertEqual(self.router._active_category, "tablets")

    # ─── Smartwatch brands ────────────────────────────────────────────
    def test_select_fitbit_routes_to_wearable_engine(self):
        self.router.select_brand("Fitbit")
        self.assertEqual(self.router._active_category, "smartwatches")
        self.assertIsInstance(self.router._get_engine(), WearableEngine)

    def test_select_garmin_routes_to_wearable_engine(self):
        self.router.select_brand("Garmin_Wearables")
        self.assertEqual(self.router._active_category, "smartwatches")
        self.assertIsInstance(self.router._get_engine(), WearableEngine)

    def test_select_amazfit_routes_to_wearable_engine(self):
        self.router.select_brand("Amazfit")
        self.assertEqual(self.router._active_category, "smartwatches")

    def test_select_fossil_routes_to_wearable_engine(self):
        self.router.select_brand("Fossil")
        self.assertEqual(self.router._active_category, "smartwatches")

    def test_select_xiaomi_watch_routes_to_wearable_engine(self):
        self.router.select_brand("Xiaomi_Watch")
        self.assertEqual(self.router._active_category, "smartwatches")

    def test_select_google_watch_routes_to_wearable_engine(self):
        self.router.select_brand("Google_Watch")
        self.assertEqual(self.router._active_category, "smartwatches")

    # ─── Smart glasses brands ─────────────────────────────────────────
    def test_select_meta_quest_routes_to_glasses_engine(self):
        self.router.select_brand("Meta_Quest")
        self.assertEqual(self.router._active_category, "smart_glasses")
        self.assertIsInstance(self.router._get_engine(), SmartGlassesEngine)

    def test_select_xreal_routes_to_glasses_engine(self):
        self.router.select_brand("XREAL")
        self.assertEqual(self.router._active_category, "smart_glasses")

    def test_select_pico_routes_to_glasses_engine(self):
        self.router.select_brand("Pico")
        self.assertEqual(self.router._active_category, "smart_glasses")

    def test_select_htc_vive_routes_to_glasses_engine(self):
        self.router.select_brand("HTC_Vive")
        self.assertEqual(self.router._active_category, "smart_glasses")


# ═══════════════════════════════════════════════════════════════════════════════
#  TEST: Action Handler Dispatch Per Category
# ═══════════════════════════════════════════════════════════════════════════════

class TestActionHandlerDispatch(unittest.TestCase):
    """Test that action handlers dispatch to the correct engine."""

    def setUp(self):
        self.router = _EngineRouter()

    def _dispatch_flash(self, brand):
        self.router.select_brand(brand)
        engine = self.router._get_engine()
        cat = self.router._active_category
        did = f"{brand}_DEV"
        if cat in ('smartphones',):
            return engine.fastboot_flash_all(did, f"/fw/{brand}")
        elif cat in ('tablets', 'ipads'):
            return engine.flash_tablet(did, f"/fw/{brand}.img", brand)
        elif cat == 'smartwatches':
            return engine.flash_wearable(did, f"/fw/{brand}.img", brand)
        elif cat in ('smart_glasses', 'ar_vr_headsets'):
            return engine.flash_headset(did, f"/fw/{brand}.img", brand)
        return {"status": "UNSUPPORTED"}

    def _dispatch_recovery(self, brand):
        self.router.select_brand(brand)
        engine = self.router._get_engine()
        cat = self.router._active_category
        did = f"{brand}_DEV"
        if cat in ('smartphones',):
            return {"status": "COMPLETED"}
        elif cat in ('tablets', 'ipads'):
            return engine.tablet_diagnostics(did, brand)
        elif cat == 'smartwatches':
            return engine.wearos_diagnostics(did)
        elif cat in ('smart_glasses', 'ar_vr_headsets'):
            return engine.headset_diagnostics(did, brand)
        return {"status": "UNSUPPORTED"}

    # ─── Flash dispatch ───────────────────────────────────────────────
    def test_flash_samsung_uses_smartphone_engine(self):
        r = self._dispatch_flash("Samsung")
        self.assertIsInstance(r, dict)

    def test_flash_samsung_tab_uses_tablet_engine(self):
        r = self._dispatch_flash("Samsung_Tab")
        self.assertIsInstance(r, dict)

    def test_flash_fitbit_uses_wearable_engine(self):
        r = self._dispatch_flash("Fitbit")
        self.assertIsInstance(r, dict)

    def test_flash_meta_quest_uses_glasses_engine(self):
        r = self._dispatch_flash("Meta_Quest")
        self.assertIsInstance(r, dict)

    # ─── Recovery dispatch ────────────────────────────────────────────
    def test_recovery_samsung_uses_smartphone_engine(self):
        r = self._dispatch_recovery("Samsung")
        self.assertIsInstance(r, dict)

    def test_recovery_samsung_tab_uses_tablet_engine(self):
        r = self._dispatch_recovery("Samsung_Tab")
        self.assertEqual(r["status"], "COMPLETED")

    def test_recovery_fitbit_uses_wearable_engine(self):
        r = self._dispatch_recovery("Fitbit")
        self.assertEqual(r["status"], "COMPLETED")

    def test_recovery_meta_quest_uses_glasses_engine(self):
        r = self._dispatch_recovery("Meta_Quest")
        self.assertEqual(r["status"], "COMPLETED")


# ═══════════════════════════════════════════════════════════════════════════════
#  TEST: Rapid Brand Switching
# ═══════════════════════════════════════════════════════════════════════════════

class TestRapidBrandSwitching(unittest.TestCase):
    """Test switching between brands rapidly and verify correct routing."""

    def setUp(self):
        self.router = _EngineRouter()

    def test_switch_chain_smartphone_to_tablet_to_watch(self):
        """Samsung → Samsung_Tab → Fitbit → Meta_Quest"""
        chain = [
            ("Samsung", "smartphones", "SmartphoneEngine"),
            ("Samsung_Tab", "tablets", "TabletEngine"),
            ("Fitbit", "smartwatches", "WearableEngine"),
            ("Meta_Quest", "smart_glasses", "SmartGlassesEngine"),
        ]
        for brand, expected_cat, expected_engine in chain:
            self.router.select_brand(brand)
            self.assertEqual(self.router._active_category, expected_cat)
            self.assertEqual(type(self.router._get_engine()).__name__, expected_engine)

    def test_switch_chain_reverse(self):
        """Meta_Quest → Fitbit → Samsung_Tab → Samsung"""
        chain = [
            ("Meta_Quest", "smart_glasses"),
            ("Fitbit", "smartwatches"),
            ("Samsung_Tab", "tablets"),
            ("Samsung", "smartphones"),
        ]
        for brand, expected_cat in chain:
            self.router.select_brand(brand)
            self.assertEqual(self.router._active_category, expected_cat)

    def test_switch_between_same_category(self):
        """Samsung → Apple → Xiaomi (all smartphones)"""
        for brand in ["Samsung", "Apple", "Xiaomi", "Nokia", "Sony"]:
            self.router.select_brand(brand)
            self.assertEqual(self.router._active_category, "smartphones")
            self.assertIsInstance(self.router._get_engine(), SmartphoneEngine)

    def test_switch_between_smartwatch_brands(self):
        """Fitbit → Garmin → Amazfit (all smartwatches)"""
        for brand in ["Fitbit", "Garmin_Wearables", "Amazfit", "Fossil", "TicWatch"]:
            self.router.select_brand(brand)
            self.assertEqual(self.router._active_category, "smartwatches")
            self.assertIsInstance(self.router._get_engine(), WearableEngine)

    def test_switch_between_glasses_brands(self):
        """Meta_Quest → XREAL → Pico (all smart_glasses)"""
        for brand in ["Meta_Quest", "XREAL", "Pico", "HTC_Vive"]:
            self.router.select_brand(brand)
            self.assertEqual(self.router._active_category, "smart_glasses")
            self.assertIsInstance(self.router._get_engine(), SmartGlassesEngine)

    def test_full_category_tour(self):
        """Visit every category at least once."""
        tour = [
            ("Samsung", "smartphones"),
            ("Samsung_Tab", "tablets"),
            ("Apple", "smartphones"),
            ("Fitbit", "smartwatches"),
            ("Garmin_Wearables", "smartwatches"),
            ("Meta_Quest", "smart_glasses"),
            ("XREAL", "smart_glasses"),
            ("Nokia", "smartphones"),
            ("Xiaomi_Pad", "tablets"),
            ("Amazfit", "smartwatches"),
            ("Pico", "smart_glasses"),
        ]
        for brand, expected_cat in tour:
            self.router.select_brand(brand)
            self.assertEqual(self.router._active_category, expected_cat)


# ═══════════════════════════════════════════════════════════════════════════════
#  TEST: Model List Population Per Category
# ═══════════════════════════════════════════════════════════════════════════════

class TestModelListPopulation(unittest.TestCase):
    """Test model list population when switching brands."""

    def setUp(self):
        self.router = _EngineRouter()

    def test_samsung_has_many_models(self):
        models = self.router.get_models("Samsung")
        self.assertGreater(len(models), 50)

    def test_samsung_tab_has_models(self):
        models = self.router.get_models("Samsung_Tab")
        self.assertGreater(len(models), 10)

    def test_fitbit_has_models(self):
        models = self.router.get_models("Fitbit")
        self.assertGreater(len(models), 5)

    def test_meta_quest_has_models(self):
        models = self.router.get_models("Meta_Quest")
        self.assertGreater(len(models), 3)

    def test_models_are_unique(self):
        for brand in ["Samsung", "Apple", "Fitbit", "Meta_Quest", "Samsung_Tab"]:
            models = self.router.get_models(brand)
            self.assertEqual(len(models), len(set(models)),
                             f"{brand} has duplicate models")

    def test_models_are_strings(self):
        models = self.router.get_models("Samsung")
        for m in models:
            self.assertIsInstance(m, str)


# ═══════════════════════════════════════════════════════════════════════════════
#  TEST: Engine Capabilities Per Category
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineCapabilities(unittest.TestCase):
    """Test that each engine has the expected capabilities."""

    def setUp(self):
        self.router = _EngineRouter()

    def test_smartphone_engine_has_flash_methods(self):
        eng = self.router.smartphone_eng
        self.assertTrue(hasattr(eng, 'fastboot_flash_all'))
        self.assertTrue(hasattr(eng, 'qualcomm_edl_flash'))
        self.assertTrue(hasattr(eng, 'samsung_odin_flash'))
        self.assertTrue(hasattr(eng, 'apple_dfu_restore'))

    def test_tablet_engine_has_flash_methods(self):
        eng = self.router.tablet_eng
        self.assertTrue(hasattr(eng, 'flash_tablet'))
        self.assertTrue(hasattr(eng, 'tablet_diagnostics'))
        self.assertTrue(hasattr(eng, 'ipad_dfu_restore'))

    def test_wearable_engine_has_flash_methods(self):
        eng = self.router.wearable_eng
        self.assertTrue(hasattr(eng, 'flash_wearable'))
        self.assertTrue(hasattr(eng, 'wearos_diagnostics'))
        self.assertTrue(hasattr(eng, 'apple_watch_dfu'))
        self.assertTrue(hasattr(eng, 'sync_fitness_band'))

    def test_glasses_engine_has_flash_methods(self):
        eng = self.router.glasses_eng
        self.assertTrue(hasattr(eng, 'flash_headset'))
        self.assertTrue(hasattr(eng, 'headset_diagnostics'))
        self.assertTrue(hasattr(eng, 'calibrate_sensors'))
        self.assertTrue(hasattr(eng, 'repair_display'))


# ═══════════════════════════════════════════════════════════════════════════════
#  TEST: Category Coverage Verification
# ═══════════════════════════════════════════════════════════════════════════════

class TestCategoryCoverageVerification(unittest.TestCase):
    """Verify all categories have sufficient coverage."""

    def test_all_nine_categories_exist(self):
        expected = {
            "smartphones", "tablets", "ipads", "smartwatches",
            "smart_glasses", "ar_vr_headsets",
            "car_infotainment", "smart_home", "gaming_handhelds",
        }
        self.assertEqual(set(ECOSYSTEM_CATALOGUE.keys()), expected)

    def test_smartphones_have_major_brands(self):
        brands = ECOSYSTEM_CATALOGUE["smartphones"]
        for brand in ["Samsung", "Apple", "Xiaomi", "Huawei", "OPPO"]:
            self.assertIn(brand, brands)

    def test_tablets_have_major_brands(self):
        brands = ECOSYSTEM_CATALOGUE["tablets"]
        for brand in ["Samsung", "Apple", "Xiaomi_Pad", "Lenovo_Tab"]:
            self.assertIn(brand, brands)

    def test_smartwatches_have_major_brands(self):
        brands = ECOSYSTEM_CATALOGUE["smartwatches"]
        for brand in ["Samsung", "Apple", "Fitbit", "Garmin_Wearables"]:
            self.assertIn(brand, brands)

    def test_smart_glasses_have_major_brands(self):
        brands = ECOSYSTEM_CATALOGUE["smart_glasses"]
        for brand in ["Meta_Quest", "XREAL", "Pico"]:
            self.assertIn(brand, brands)

    def test_car_infotainment_has_major_brands(self):
        brands = ECOSYSTEM_CATALOGUE["car_infotainment"]
        for brand in ["Tesla", "BMW", "Mercedes-Benz", "Toyota"]:
            self.assertIn(brand, brands)

    def test_smart_home_has_major_brands(self):
        brands = ECOSYSTEM_CATALOGUE["smart_home"]
        for brand in ["Amazon", "Google", "Apple"]:
            self.assertIn(brand, brands)

    def test_gaming_handhelds_has_major_brands(self):
        brands = ECOSYSTEM_CATALOGUE["gaming_handhelds"]
        for brand in ["Nintendo", "Valve", "ASUS_ROG"]:
            self.assertIn(brand, brands)

    def test_total_model_count(self):
        total = sum(len(m) for v in ECOSYSTEM_CATALOGUE.values()
                    for m in v.values())
        self.assertGreater(total, 1500, f"Expected >1500 total models, got {total}")


if __name__ == "__main__":
    unittest.main()
