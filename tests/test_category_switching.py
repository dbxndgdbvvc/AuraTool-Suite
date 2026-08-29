"""
Unit Tests — Category Switching
================================
Tests for brand → category detection, engine routing, action handler
dispatch, and model list population across all device categories
(tablets, wearables, smart glasses, AR/VR headsets).

Validates that switching brands in the GUI correctly updates the active
engine and routes operations to the right device-specific handler.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.smart_devices import ECOSYSTEM_CATALOGUE
from modules.smartphones import SmartphoneEngine
from modules.tablets import TabletEngine
from modules.wearables import WearableEngine
from modules.smart_glasses import SmartGlassesEngine


# ═══════════════════════════════════════════════════════════════════════════════
#  ECOSYSTEM CATALOGUE INTEGRITY
# ═══════════════════════════════════════════════════════════════════════════════

class TestEcosystemCatalogueIntegrity(unittest.TestCase):
    """Test ECOSYSTEM_CATALOGUE structure and completeness."""

    def test_all_categories_exist(self):
        expected = {"smartphones", "tablets", "ipads", "smartwatches",
                    "smart_glasses", "ar_vr_headsets",
                    "car_infotainment", "smart_home", "gaming_handhelds"}
        self.assertEqual(set(ECOSYSTEM_CATALOGUE.keys()), expected)

    def test_each_category_has_brands(self):
        for cat, brands in ECOSYSTEM_CATALOGUE.items():
            with self.subTest(cat=cat):
                self.assertGreater(len(brands), 0, f"{cat} has no brands")

    def test_each_brand_has_models(self):
        for cat, brands in ECOSYSTEM_CATALOGUE.items():
            for brand, models in brands.items():
                with self.subTest(cat=cat, brand=brand):
                    self.assertIsInstance(models, list)
                    self.assertGreater(len(models), 0,
                                       f"{cat}/{brand} has no models")

    def test_no_duplicate_brands_within_category(self):
        for cat, brands in ECOSYSTEM_CATALOGUE.items():
            brand_list = list(brands.keys())
            duplicates = [b for b in brand_list if brand_list.count(b) > 1]
            self.assertEqual(len(duplicates), 0,
                             f"{cat} has duplicate brands: {set(duplicates)}")

    def test_total_model_count(self):
        total = sum(len(m) for v in ECOSYSTEM_CATALOGUE.values()
                    for m in v.values())
        self.assertGreater(total, 1000, f"Expected >1000 total models, got {total}")


# ═══════════════════════════════════════════════════════════════════════════════
#  BRAND → CATEGORY DETECTION (_get_category)
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrandCategoryDetection(unittest.TestCase):
    """Test _get_category() returns correct category for each brand."""

    def _get_category(self, brand):
        """Replicate ui/app.py _get_category logic."""
        for cat, brands in ECOSYSTEM_CATALOGUE.items():
            if brand in brands:
                return cat
        return "smartphones"

    # ─── Smartphone brands ────────────────────────────────────────────
    def test_samsung_is_smartphone(self):
        self.assertEqual(self._get_category("Samsung"), "smartphones")

    def test_apple_is_smartphone(self):
        self.assertEqual(self._get_category("Apple"), "smartphones")

    def test_xiaomi_is_smartphone(self):
        self.assertEqual(self._get_category("Xiaomi"), "smartphones")

    def test_huawei_is_smartphone(self):
        self.assertEqual(self._get_category("Huawei"), "smartphones")

    def test_nokia_is_smartphone(self):
        self.assertEqual(self._get_category("Nokia"), "smartphones")

    def test_sony_is_smartphone(self):
        self.assertEqual(self._get_category("Sony"), "smartphones")

    def test_motorola_is_smartphone(self):
        self.assertEqual(self._get_category("Motorola"), "smartphones")

    def test_google_pixel_is_smartphone(self):
        self.assertEqual(self._get_category("Google Pixel"), "smartphones")

    def test_nothing_is_smartphone(self):
        self.assertEqual(self._get_category("Nothing"), "smartphones")

    def test_poco_is_smartphone(self):
        self.assertEqual(self._get_category("Poco"), "smartphones")

    # ─── Tablet brands ────────────────────────────────────────────────
    def test_samsung_tab_is_tablet(self):
        self.assertEqual(self._get_category("Samsung_Tab"), "tablets")

    def test_xiaomi_pad_is_tablet(self):
        self.assertEqual(self._get_category("Xiaomi_Pad"), "tablets")

    def test_oppo_pad_is_tablet(self):
        self.assertEqual(self._get_category("OPPO_Pad"), "tablets")

    def test_realme_pad_is_tablet(self):
        self.assertEqual(self._get_category("Realme_Pad"), "tablets")

    def test_honor_pad_is_tablet(self):
        self.assertEqual(self._get_category("Honor_Pad"), "tablets")

    def test_lenovo_tab_is_tablet(self):
        self.assertEqual(self._get_category("Lenovo_Tab"), "tablets")

    def test_nokia_tab_is_tablet(self):
        self.assertEqual(self._get_category("Nokia_Tab"), "tablets")

    def test_tcl_tab_is_tablet(self):
        self.assertEqual(self._get_category("TCL_Tab"), "tablets")

    def test_ipad_mini_is_tablet(self):
        self.assertEqual(self._get_category("iPad_Mini"), "tablets")

    def test_microsoft_surface_is_tablet(self):
        self.assertEqual(self._get_category("Microsoft_Surface"), "tablets")

    def test_dell_is_tablet(self):
        self.assertEqual(self._get_category("Dell"), "tablets")

    def test_hp_is_tablet(self):
        self.assertEqual(self._get_category("HP"), "tablets")

    def test_amazon_kids_is_tablet(self):
        self.assertEqual(self._get_category("Amazon_Kids"), "tablets")

    # ─── Smartwatch brands ────────────────────────────────────────────
    def test_garmin_wearables_is_smartwatch(self):
        self.assertEqual(self._get_category("Garmin_Wearables"), "smartwatches")

    def test_fitbit_is_smartwatch(self):
        self.assertEqual(self._get_category("Fitbit"), "smartwatches")

    def test_amazfit_is_smartwatch(self):
        self.assertEqual(self._get_category("Amazfit"), "smartwatches")

    def test_ticwatch_is_smartwatch(self):
        self.assertEqual(self._get_category("TicWatch"), "smartwatches")

    def test_fossil_is_smartwatch(self):
        self.assertEqual(self._get_category("Fossil"), "smartwatches")

    def test_casio_is_smartwatch_or_smartphone(self):
        cat = self._get_category("Casio")
        # Casio appears in both smartphones (legacy phones) and smartwatches
        self.assertIn(cat, ("smartphones", "smartwatches"))

    def test_suunto_is_smartwatch(self):
        self.assertEqual(self._get_category("Suunto"), "smartwatches")

    def test_polar_is_smartwatch(self):
        self.assertEqual(self._get_category("Polar"), "smartwatches")

    def test_coros_is_smartwatch(self):
        self.assertEqual(self._get_category("Coros"), "smartwatches")

    def test_withings_is_smartwatch(self):
        self.assertEqual(self._get_category("Withings"), "smartwatches")

    def test_kospet_is_smartwatch(self):
        self.assertEqual(self._get_category("Kospet"), "smartwatches")

    def test_lumiwatch_is_smartwatch(self):
        self.assertEqual(self._get_category("LumiWatch"), "smartwatches")

    def test_tagheuer_is_smartwatch(self):
        self.assertEqual(self._get_category("TagHeuer"), "smartwatches")

    def test_michaelkors_is_smartwatch(self):
        self.assertEqual(self._get_category("MichaelKors"), "smartwatches")

    def test_louisvuitton_is_smartwatch(self):
        self.assertEqual(self._get_category("LouisVuitton"), "smartwatches")

    def test_montblanc_is_smartwatch(self):
        self.assertEqual(self._get_category("Montblanc"), "smartwatches")

    def test_skagen_is_smartwatch(self):
        self.assertEqual(self._get_category("Skagen"), "smartwatches")

    def test_kronaby_is_smartwatch(self):
        self.assertEqual(self._get_category("Kronaby"), "smartwatches")

    def test_cat_is_smartwatch(self):
        self.assertEqual(self._get_category("Cat"), "smartwatches")

    def test_realme_watch_is_smartwatch(self):
        self.assertEqual(self._get_category("Realme_Watch"), "smartwatches")

    def test_oppo_watch_is_smartwatch(self):
        self.assertEqual(self._get_category("OPPO_Watch"), "smartwatches")

    def test_oneplus_watch_is_smartwatch(self):
        self.assertEqual(self._get_category("OnePlus_Watch"), "smartwatches")

    def test_huawei_watch_is_smartwatch(self):
        self.assertEqual(self._get_category("Huawei_Watch"), "smartwatches")

    def test_google_watch_is_smartwatch(self):
        self.assertEqual(self._get_category("Google_Watch"), "smartwatches")

    def test_xiaomi_watch_is_smartwatch(self):
        self.assertEqual(self._get_category("Xiaomi_Watch"), "smartwatches")

    def test_honor_band_is_smartwatch(self):
        self.assertEqual(self._get_category("Honor_Band"), "smartwatches")

    def test_mobvoi_is_smartwatch(self):
        self.assertEqual(self._get_category("Mobvoi"), "smartwatches")

    def test_amazon_fire_is_tablet_or_smartwatch(self):
        cat = self._get_category("Amazon_Fire")
        self.assertIn(cat, ("tablets", "smartwatches"))  # Multi-category brand

    # ─── Smart glasses brands ─────────────────────────────────────────
    def test_meta_quest_is_smart_glasses(self):
        self.assertEqual(self._get_category("Meta_Quest"), "smart_glasses")

    def test_apple_vision_is_smart_glasses(self):
        self.assertEqual(self._get_category("Apple_Vision"), "smart_glasses")

    def test_xreal_is_smart_glasses(self):
        self.assertEqual(self._get_category("XREAL"), "smart_glasses")

    def test_htc_vive_is_smart_glasses(self):
        self.assertEqual(self._get_category("HTC_Vive"), "smart_glasses")

    def test_pico_is_smart_glasses(self):
        self.assertEqual(self._get_category("Pico"), "smart_glasses")

    def test_nreal_is_smart_glasses(self):
        self.assertEqual(self._get_category("Nreal"), "smart_glasses")

    def test_rokid_is_smart_glasses(self):
        self.assertEqual(self._get_category("Rokid"), "smart_glasses")

    def test_rayneo_is_smart_glasses(self):
        self.assertEqual(self._get_category("RayNeo"), "smart_glasses")

    def test_solos_is_smart_glasses(self):
        self.assertEqual(self._get_category("Solos"), "smart_glasses")

    # ─── AR/VR headset brands ─────────────────────────────────────────
    def test_meta_is_smart_glasses_or_ar_vr(self):
        cat = self._get_category("Meta")
        # Meta appears in both smart_glasses and ar_vr_headsets
        self.assertIn(cat, ("smart_glasses", "ar_vr_headsets"))

    def test_sony_is_smartphone_or_ar_vr(self):
        cat = self._get_category("Sony")
        # Sony appears in both smartphones and ar_vr_headsets
        self.assertIn(cat, ("smartphones", "ar_vr_headsets"))

    def test_valve_is_ar_vr(self):
        self.assertEqual(self._get_category("Valve"), "ar_vr_headsets")

    # ─── Fallback behavior ────────────────────────────────────────────
    def test_unknown_brand_falls_back_to_smartphones(self):
        self.assertEqual(self._get_category("UnknownBrand"), "smartphones")

    def test_empty_brand_falls_back_to_smartphones(self):
        self.assertEqual(self._get_category(""), "smartphones")


# ═══════════════════════════════════════════════════════════════════════════════
#  CATEGORY → ENGINE ROUTING (_get_engine)
# ═══════════════════════════════════════════════════════════════════════════════

class TestCategoryEngineRouting(unittest.TestCase):
    """Test _get_engine() returns correct engine for each category."""

    def setUp(self):
        self.engines = {
            "smartphones": SmartphoneEngine(),
            "tablets": TabletEngine(),
            "ipads": TabletEngine(),
            "smartwatches": WearableEngine(),
            "smart_glasses": SmartGlassesEngine(),
            "ar_vr_headsets": SmartGlassesEngine(),
        }

    def _get_engine(self, category):
        return self.engines.get(category, self.engines["smartphones"])

    def test_smartphones_routes_to_smartphone_engine(self):
        self.assertIsInstance(self._get_engine("smartphones"), SmartphoneEngine)

    def test_tablets_routes_to_tablet_engine(self):
        self.assertIsInstance(self._get_engine("tablets"), TabletEngine)

    def test_ipads_routes_to_tablet_engine(self):
        self.assertIsInstance(self._get_engine("ipads"), TabletEngine)

    def test_smartwatches_routes_to_wearable_engine(self):
        self.assertIsInstance(self._get_engine("smartwatches"), WearableEngine)

    def test_smart_glasses_routes_to_glasses_engine(self):
        self.assertIsInstance(self._get_engine("smart_glasses"), SmartGlassesEngine)

    def test_ar_vr_headsets_routes_to_glasses_engine(self):
        self.assertIsInstance(self._get_engine("ar_vr_headsets"), SmartGlassesEngine)

    def test_unknown_category_falls_back_to_smartphone_engine(self):
        self.assertIsInstance(self._get_engine("unknown"), SmartphoneEngine)

    def test_tablets_and_ipads_share_same_engine_type(self):
        self.assertEqual(type(self._get_engine("tablets")), type(self._get_engine("ipads")))

    def test_smart_glasses_and_ar_vr_share_same_engine_type(self):
        self.assertEqual(type(self._get_engine("smart_glasses")),
                         type(self._get_engine("ar_vr_headsets")))

    def test_engine_names(self):
        name_map = {
            "smartphones": "SmartphoneEngine",
            "tablets": "TabletEngine",
            "ipads": "TabletEngine",
            "smartwatches": "WearableEngine",
            "smart_glasses": "SmartGlassesEngine",
            "ar_vr_headsets": "SmartGlassesEngine",
        }
        for cat, expected_name in name_map.items():
            with self.subTest(cat=cat):
                engine = self._get_engine(cat)
                self.assertEqual(type(engine).__name__, expected_name)


# ═══════════════════════════════════════════════════════════════════════════════
#  MODEL LIST POPULATION (_models)
# ═══════════════════════════════════════════════════════════════════════════════

class TestModelListPopulation(unittest.TestCase):
    """Test model list population when switching brands."""

    def _get_models(self, brand):
        """Replicate ui/app.py _models logic."""
        ms = []
        for c in ECOSYSTEM_CATALOGUE.values():
            if brand in c:
                ms.extend(c[brand])
        return sorted(set(ms))

    def test_samsung_has_models(self):
        models = self._get_models("Samsung")
        self.assertGreater(len(models), 50)

    def test_samsung_tab_has_models(self):
        models = self._get_models("Samsung_Tab")
        self.assertGreater(len(models), 10)

    def test_garmin_wearables_has_models(self):
        models = self._get_models("Garmin_Wearables")
        self.assertGreater(len(models), 5)

    def test_fitbit_has_models(self):
        models = self._get_models("Fitbit")
        self.assertGreater(len(models), 5)

    def test_meta_quest_has_models(self):
        models = self._get_models("Meta_Quest")
        self.assertGreater(len(models), 3)

    def test_xreal_has_models(self):
        models = self._get_models("XREAL")
        self.assertGreater(len(models), 2)

    def test_model_lists_are_unique(self):
        """No duplicate models within a brand."""
        for brand in ["Samsung", "Apple", "Xiaomi", "Samsung_Tab",
                       "Fitbit", "Meta_Quest"]:
            models = self._get_models(brand)
            self.assertEqual(len(models), len(set(models)),
                             f"{brand} has duplicate models")

    def test_models_are_strings(self):
        models = self._get_models("Samsung")
        for m in models:
            self.assertIsInstance(m, str)


# ═══════════════════════════════════════════════════════════════════════════════
#  ACTION HANDLER DISPATCH PER CATEGORY
# ═══════════════════════════════════════════════════════════════════════════════

class TestActionHandlerDispatch(unittest.TestCase):
    """Test that action handlers dispatch to the correct engine per category."""

    def setUp(self):
        self.smartphone_eng = SmartphoneEngine()
        self.tablet_eng = TabletEngine()
        self.wearable_eng = WearableEngine()
        self.glasses_eng = SmartGlassesEngine()

    # ─── Flash operations ─────────────────────────────────────────────
    def test_smartphone_flash_uses_fastboot(self):
        r = self.smartphone_eng.fastboot_flash_all("DEV01", "/fw/Samsung")
        self.assertIsInstance(r, dict)

    def test_tablet_flash_uses_flash_tablet(self):
        r = self.tablet_eng.flash_tablet("DEV01", "/fw/firmware.img", "Xiaomi")
        self.assertIsInstance(r, dict)

    def test_wearable_flash_uses_flash_wearable(self):
        r = self.wearable_eng.flash_wearable("DEV01", "/fw/firmware.img", "Xiaomi")
        self.assertIsInstance(r, dict)

    def test_glasses_flash_uses_flash_headset(self):
        r = self.glasses_eng.flash_headset("DEV01", "/fw/firmware.img", "Meta")
        self.assertIsInstance(r, dict)

    # ─── Diagnostics operations ───────────────────────────────────────
    def test_tablet_diagnostics(self):
        r = self.tablet_eng.tablet_diagnostics("DEV01", "Samsung")
        self.assertEqual(r["status"], "COMPLETED")

    def test_wearable_diagnostics(self):
        r = self.wearable_eng.wearos_diagnostics("DEV01")
        self.assertEqual(r["status"], "COMPLETED")

    def test_glasses_diagnostics(self):
        r = self.glasses_eng.headset_diagnostics("DEV01", "Meta")
        self.assertEqual(r["status"], "COMPLETED")

    # ─── Calibration operations ───────────────────────────────────────
    def test_glasses_sensor_calibration(self):
        r = self.glasses_eng.calibrate_sensors("DEV01", "Meta")
        self.assertEqual(r["status"], "COMPLETED")

    def test_display_repair(self):
        r = self.glasses_eng.repair_display("DEV01", "flickering")
        self.assertEqual(r["status"], "COMPLETED")

    # ─── Fitness band sync (wearable-specific) ────────────────────────
    def test_fitness_band_sync_garmin(self):
        r = self.wearable_eng.sync_fitness_band("DEV01", "Garmin")
        self.assertEqual(r["sync_status"], "COMPLETED")

    def test_fitness_band_sync_fitbit(self):
        r = self.wearable_eng.sync_fitness_band("DEV01", "Fitbit")
        self.assertEqual(r["sync_status"], "COMPLETED")

    # ─── Proprietary protocol handling ────────────────────────────────
    def test_garmin_flash_returns_unsupported(self):
        r = self.wearable_eng.flash_wearable("DEV01", "/fw/fw.bin", "Garmin")
        self.assertEqual(r["status"], "UNSUPPORTED")

    def test_sony_glasses_flash_returns_vendor_tool(self):
        r = self.glasses_eng.flash_headset("DEV01", "/fw/fw.bin", "Sony")
        self.assertEqual(r["status"], "NEEDS_VENDOR_TOOL")

    # ─── Apple DFU routing ────────────────────────────────────────────
    def test_ipad_dfu_restore(self):
        r = self.tablet_eng.ipad_dfu_restore("DEV01", "/fw/firmware.ipsw")
        self.assertIn("status", r)

    def test_apple_watch_dfu(self):
        r = self.wearable_eng.apple_watch_dfu("DEV01", "/fw/firmware.ipsw")
        self.assertEqual(r["status"], "SIMULATED")

    def test_apple_vision_restore(self):
        r = self.glasses_eng._apple_vision_restore("DEV01", "/fw/firmware.ipsw")
        self.assertEqual(r["status"], "SIMULATED")


# ═══════════════════════════════════════════════════════════════════════════════
#  BRAND SWITCHING SIMULATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrandSwitchingSimulation(unittest.TestCase):
    """Simulate switching between brands in the GUI and verify routing."""

    def _get_category(self, brand):
        for cat, brands in ECOSYSTEM_CATALOGUE.items():
            if brand in brands:
                return cat
        return "smartphones"

    def _get_engine(self, category):
        engine_map = {
            "smartphones": SmartphoneEngine(),
            "tablets": TabletEngine(),
            "ipads": TabletEngine(),
            "smartwatches": WearableEngine(),
            "smart_glasses": SmartGlassesEngine(),
            "ar_vr_headsets": SmartGlassesEngine(),
        }
        return engine_map.get(category, engine_map["smartphones"])

    def test_switch_samsung_to_samsung_tab(self):
        """Switching from Samsung phone to Samsung tablet."""
        cat1 = self._get_category("Samsung")
        cat2 = self._get_category("Samsung_Tab")
        self.assertEqual(cat1, "smartphones")
        self.assertEqual(cat2, "tablets")
        self.assertNotEqual(cat1, cat2)

    def test_switch_samsung_to_garmin(self):
        """Switching from Samsung phone to Garmin watch."""
        cat1 = self._get_category("Samsung")
        cat2 = self._get_category("Garmin_Wearables")
        self.assertEqual(cat1, "smartphones")
        self.assertEqual(cat2, "smartwatches")

    def test_switch_samsung_to_meta_quest(self):
        """Switching from Samsung phone to Meta Quest."""
        cat1 = self._get_category("Samsung")
        cat2 = self._get_category("Meta_Quest")
        self.assertEqual(cat1, "smartphones")
        self.assertEqual(cat2, "smart_glasses")

    def test_switch_fitbit_to_meta_quest(self):
        """Switching from Fitbit watch to Meta Quest glasses."""
        cat1 = self._get_category("Fitbit")
        cat2 = self._get_category("Meta_Quest")
        self.assertEqual(cat1, "smartwatches")
        self.assertEqual(cat2, "smart_glasses")

    def test_engine_changes_on_category_switch(self):
        """Engine instance should change when category changes."""
        e1 = self._get_engine("smartphones")
        e2 = self._get_engine("tablets")
        e3 = self._get_engine("smartwatches")
        e4 = self._get_engine("smart_glasses")

        self.assertIsNot(e1, e2)
        self.assertIsNot(e2, e3)
        self.assertIsNot(e3, e4)

    def test_full_brand_switch_chain(self):
        """Simulate a chain of brand switches and verify each routes correctly."""
        switches = [
            ("Samsung", "smartphones", "SmartphoneEngine"),
            ("Samsung_Tab", "tablets", "TabletEngine"),
            ("Xiaomi_Pad", "tablets", "TabletEngine"),
            ("Fitbit", "smartwatches", "WearableEngine"),
            ("Garmin_Wearables", "smartwatches", "WearableEngine"),
            ("Meta_Quest", "smart_glasses", "SmartGlassesEngine"),
            ("XREAL", "smart_glasses", "SmartGlassesEngine"),
            ("Pico", "smart_glasses", "SmartGlassesEngine"),
            ("HTC_Vive", "smart_glasses", "SmartGlassesEngine"),
            ("Apple", "smartphones", "SmartphoneEngine"),
            ("Nokia", "smartphones", "SmartphoneEngine"),
        ]

        for brand, expected_cat, expected_engine in switches:
            with self.subTest(brand=brand):
                cat = self._get_category(brand)
                engine = self._get_engine(cat)
                self.assertEqual(cat, expected_cat)
                self.assertEqual(type(engine).__name__, expected_engine)


# ═══════════════════════════════════════════════════════════════════════════════
#  CATEGORY COVERAGE
# ═══════════════════════════════════════════════════════════════════════════════

class TestCategoryCoverage(unittest.TestCase):
    """Verify all categories have sufficient brand and model coverage."""

    def test_smartphones_coverage(self):
        brands = ECOSYSTEM_CATALOGUE.get("smartphones", {})
        self.assertGreaterEqual(len(brands), 50)

    def test_tablets_coverage(self):
        brands = ECOSYSTEM_CATALOGUE.get("tablets", {})
        self.assertGreaterEqual(len(brands), 30)

    def test_ipads_coverage(self):
        brands = ECOSYSTEM_CATALOGUE.get("ipads", {})
        self.assertGreaterEqual(len(brands), 1)

    def test_smartwatches_coverage(self):
        brands = ECOSYSTEM_CATALOGUE.get("smartwatches", {})
        self.assertGreaterEqual(len(brands), 25)

    def test_smart_glasses_coverage(self):
        brands = ECOSYSTEM_CATALOGUE.get("smart_glasses", {})
        self.assertGreaterEqual(len(brands), 10)

    def test_ar_vr_headsets_coverage(self):
        brands = ECOSYSTEM_CATALOGUE.get("ar_vr_headsets", {})
        self.assertGreaterEqual(len(brands), 10)

    def test_each_category_has_major_brands(self):
        """Each category should have at least one major brand."""
        major_brands = {
            "smartphones": ["Samsung", "Apple", "Xiaomi"],
            "tablets": ["Samsung", "Apple"],
            "ipads": ["Apple"],
            "smartwatches": ["Samsung", "Apple", "Garmin"],
            "smart_glasses": ["Meta", "Apple"],
            "ar_vr_headsets": ["Meta", "Apple", "Sony"],
        }
        for cat, expected in major_brands.items():
            brands = ECOSYSTEM_CATALOGUE.get(cat, {})
            for brand in expected:
                with self.subTest(cat=cat, brand=brand):
                    self.assertIn(brand, brands,
                                  f"{brand} not in {cat} category")


if __name__ == "__main__":
    unittest.main()
