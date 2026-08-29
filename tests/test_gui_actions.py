"""
GUI Action Handler Smoke Tests
===============================
Invokes every toolbar action handler in AuraToolUI and verifies each
one completes without error and produces [SUCCESS] log output.
"""

import logging
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.license_manager import LicenseManager


def _make_app():
    from ui.app import AuraToolUI
    lic_mgr = LicenseManager()
    status = lic_mgr.enforce_or_exit()
    return AuraToolUI(status, {"adb": True, "fastboot": True}, None)


class _ActionTestBase(unittest.TestCase):
    _app = None

    @classmethod
    def setUpClass(cls):
        cls._app = _make_app()

    def _run(self, fn):
        """Run action, flush tkinter, return captured SUCCESS logs."""
        handler = _LogCapture()
        logger = logging.getLogger("AuraTool.UI")
        logger.addHandler(handler)
        try:
            fn()
            self._app.root.update_idletasks()
        except Exception as e:
            self.fail(f"{fn.__name__} raised {type(e).__name__}: {e}")
        finally:
            logger.removeHandler(handler)
        return handler.messages

    def _assert_success(self, logs, keyword):
        """Assert at least one SUCCESS log contains the keyword."""
        success_msgs = [m for m in logs if "[SUCCESS]" in m]
        self.assertTrue(success_msgs, f"No [SUCCESS] logs produced. All logs: {logs}")
        found = any(keyword.lower() in m.lower() for m in success_msgs)
        self.assertTrue(found, f"Keyword '{keyword}' not in success logs: {success_msgs}")


class _LogCapture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.messages = []
    def emit(self, record):
        self.messages.append(record.getMessage())


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN TOOLBAR ACTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFlash(_ActionTestBase):
    def test_act_flash(self):
        logs = self._run(self._app._act_flash)
        self._assert_success(logs, "Flash firmware")

    def test_act_frp(self):
        logs = self._run(self._app._act_frp)
        self._assert_success(logs, "FRP bypass")

    def test_act_format(self):
        logs = self._run(self._app._act_format)
        self._assert_success(logs, "formatted")

    def test_act_update(self):
        logs = self._run(self._app._act_update)
        self._assert_success(logs, "Update")

    def test_act_unlock(self):
        logs = self._run(self._app._act_unlock)
        self._assert_success(logs, "Unlock")

    def test_act_biometric(self):
        logs = self._run(self._app._act_biometric)
        self._assert_success(logs, "calibration")

    def test_act_recovery(self):
        logs = self._run(self._app._act_recovery)
        self._assert_success(logs, "Recovery")

    def test_act_repair(self):
        logs = self._run(self._app._act_repair)
        self._assert_success(logs, "repair")

    def test_act_security(self):
        logs = self._run(self._app._act_security)
        self._assert_success(logs, "Protection")


# ═══════════════════════════════════════════════════════════════════════════════
#  FLASH TAB SUB-ACTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestFlashTab(_ActionTestBase):
    def test_extract(self):
        logs = self._run(self._app._flash_extract)
        self._assert_success(logs, "Extracted")

    def test_single(self):
        logs = self._run(self._app._flash_single)
        self._assert_success(logs, "Partition")

    def test_unbrick(self):
        logs = self._run(self._app._flash_unbrick)
        self._assert_success(logs, "Unbrick")

    def test_storage(self):
        logs = self._run(self._app._flash_storage)
        self._assert_success(logs, "Storage")

    def test_bootloader(self):
        logs = self._run(self._app._flash_boot)
        self._assert_success(logs, "Bootloader")


# ═══════════════════════════════════════════════════════════════════════════════
#  CATEGORY-SPECIFIC FLASH ACTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestCategoryFlash(_ActionTestBase):
    def test_edl(self):
        logs = self._run(self._app._flash_edl)
        self._assert_success(logs, "EDL")

    def test_mtk(self):
        logs = self._run(self._app._flash_mtk)
        self._assert_success(logs, "MTK")

    def test_ipad_dfu(self):
        logs = self._run(self._app._flash_ipad_dfu)
        self._assert_success(logs, "iPad DFU")

    def test_storage_diag(self):
        logs = self._run(self._app._flash_storage_diag)
        self._assert_success(logs, "Storage")

    def test_wearos(self):
        logs = self._run(self._app._flash_wearos)
        self._assert_success(logs, "WearOS")

    def test_watch_sync(self):
        logs = self._run(self._app._flash_watch_sync)
        self._assert_success(logs, "Watch sync")

    def test_headset_cal(self):
        logs = self._run(self._app._flash_headset_cal)
        self._assert_success(logs, "Headset cal")

    def test_xr2(self):
        logs = self._run(self._app._flash_xr2)
        self._assert_success(logs, "XR2")


# ═══════════════════════════════════════════════════════════════════════════════
#  SECURITY TAB ACTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSecurityTab(_ActionTestBase):
    def test_sec_frp(self):
        logs = self._run(self._app._sec_frp)
        self._assert_success(logs, "FRP")

    def test_sec_lock(self):
        logs = self._run(self._app._sec_lock)
        self._assert_success(logs, "Lock status")

    def test_sec_email(self):
        logs = self._run(self._app._sec_email)
        self._assert_success(logs, "Email bypass")

    def test_sec_cloud(self):
        logs = self._run(self._app._sec_cloud)
        self._assert_success(logs, "Cloud unlock")

    def test_sec_diag(self):
        logs = self._run(self._app._sec_diag)
        self._assert_success(logs, "")


# ═══════════════════════════════════════════════════════════════════════════════
#  RECOVERY TAB ACTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestRecoveryTab(_ActionTestBase):
    def test_rec_scan(self):
        logs = self._run(self._app._rec_scan)
        self._assert_success(logs, "")

    def test_rec_photos(self):
        logs = self._run(self._app._rec_photos)
        self._assert_success(logs, "")

    def test_rec_sms(self):
        logs = self._run(self._app._rec_sms)
        self._assert_success(logs, "")

    def test_rec_health(self):
        logs = self._run(self._app._rec_health)
        self._assert_success(logs, "")

    def test_rec_sensors(self):
        logs = self._run(self._app._rec_sensors)
        self._assert_success(logs, "")

    def test_rec_notes_tablet(self):
        logs = self._run(self._app._rec_notes_tablet)
        self._assert_success(logs, "")


# ═══════════════════════════════════════════════════════════════════════════════
#  BIOMETRIC TAB ACTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestBiometricTab(_ActionTestBase):
    def test_bio_diag(self):
        logs = self._run(self._app._bio_diag)
        self._assert_success(logs, "Diagnostics")

    def test_bio_cal(self):
        logs = self._run(self._app._bio_cal)
        self._assert_success(logs, "Calibration")

    def test_bio_face(self):
        logs = self._run(self._app._bio_face)
        self._assert_success(logs, "")

    def test_bio_touch(self):
        logs = self._run(self._app._bio_touch)
        self._assert_success(logs, "")

    def test_bio_battery_watch(self):
        logs = self._run(self._app._bio_battery_watch)
        self._assert_success(logs, "")

    def test_bio_display(self):
        logs = self._run(self._app._bio_display)
        self._assert_success(logs, "")

    def test_bio_imu(self):
        logs = self._run(self._app._bio_imu)
        self._assert_success(logs, "")


# ═══════════════════════════════════════════════════════════════════════════════
#  SETTINGS TAB ACTIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSettingsTab(_ActionTestBase):
    def test_set_check(self):
        logs = self._run(self._app._set_check)
        self._assert_success(logs, "Protection")

    def test_set_ai(self):
        logs = self._run(self._app._set_ai)
        self._assert_success(logs, "")

    def test_set_lang(self):
        logs = self._run(self._app._set_lang)
        self._assert_success(logs, "")


# ═══════════════════════════════════════════════════════════════════════════════
#  CATEGORY ROUTING
# ═══════════════════════════════════════════════════════════════════════════════

class TestCategoryRouting(_ActionTestBase):
    def _set_cat(self, cat):
        self._app._active_category = cat

    def test_smartphone_routing(self):
        self._set_cat("smartphones")
        logs = self._run(self._app._act_flash)
        self.assertTrue(any("[smartphones]" in m for m in logs))

    def test_tablet_routing(self):
        self._set_cat("tablets")
        logs = self._run(self._app._act_flash)
        self.assertTrue(any("[tablets]" in m for m in logs))

    def test_wearable_routing(self):
        self._set_cat("smartwatches")
        logs = self._run(self._app._act_flash)
        self.assertTrue(any("[smartwatches]" in m for m in logs))

    def test_glasses_routing(self):
        self._set_cat("smart_glasses")
        logs = self._run(self._app._act_flash)
        self.assertTrue(any("[smart_glasses]" in m for m in logs))

    def test_recovery_wearable(self):
        self._set_cat("smartwatches")
        logs = self._run(self._app._act_recovery)
        self.assertTrue(any("[smartwatches]" in m for m in logs))

    def test_repair_glasses(self):
        self._set_cat("smart_glasses")
        logs = self._run(self._app._act_repair)
        self.assertTrue(any("[smart_glasses]" in m for m in logs))

    def test_biometric_wearable(self):
        self._set_cat("smartwatches")
        logs = self._run(self._app._act_biometric)
        self.assertTrue(any("[smartwatches]" in m for m in logs))


# ═══════════════════════════════════════════════════════════════════════════════
#  BRAND CHANGE → ENGINE UPDATE
# ═══════════════════════════════════════════════════════════════════════════════

class TestBrandEngine(_ActionTestBase):
    def test_brand_change_updates_category(self):
        brands = list(self._app.brand_combo["values"])
        if brands:
            self._app.brand_combo.set(brands[-1])
            self._app._brand_chg()
            self.assertIn(self._app._active_category,
                          ("smartphones", "tablets", "smartwatches", "smart_glasses",
                           "ipads", "ar_vr_headsets"))

    def test_engine_label_updates(self):
        brands = list(self._app.brand_combo["values"])
        if brands:
            self._app.brand_combo.set(brands[0])
            self._app._brand_chg()
            if hasattr(self._app, 'engine_lbl'):
                text = self._app.engine_lbl.cget("text")
                self.assertIn("→", text, f"Engine label missing arrow: {text}")


if __name__ == "__main__":
    unittest.main()
