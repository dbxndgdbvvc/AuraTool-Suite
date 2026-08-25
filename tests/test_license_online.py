"""
Unit Tests — Online License Integration
=========================================
Tests cover:
  - LicenseServerClient: HTTP communication with license server
  - LicenseManager.online_activate(): server-side activation
  - LicenseManager.online_validate(): server-side validation
  - LicenseManager.check_license_online(): hybrid online/offline check
  - Offline fallback when server is unreachable
  - Token persistence across restarts
  - End-to-end: server generate → client activate → validate → deactivate
"""

import json
import os
import shutil
import socket
import tempfile
import threading
import time
import pytest

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.license_manager import (
    LicenseManager, LicenseServerClient, LicenseTier, TIER_CONFIG,
)
from core.license_server import (
    LicenseStore, AdminKeyManager, LicenseHTTPServer, LicenseServerHandler,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def license_server(tmp_dir):
    """Start a test license server."""
    data_dir = os.path.join(tmp_dir, "server_data")
    store = LicenseStore(data_dir=data_dir)
    admin_mgr = AdminKeyManager(data_dir=data_dir)
    admin_key = admin_mgr.generate_key(label="test-admin")

    LicenseServerHandler.store = store
    LicenseServerHandler.admin_mgr = admin_mgr
    LicenseServerHandler.require_admin_auth = False

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    srv = LicenseHTTPServer(
        ("127.0.0.1", port), LicenseServerHandler, store, admin_mgr,
        require_admin_auth=False,
    )
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)

    yield f"http://127.0.0.1:{port}", store, admin_key

    srv.shutdown()


# ===========================================================================
# LicenseServerClient Tests
# ===========================================================================

class TestLicenseServerClient:
    def test_health(self, license_server):
        base, _, _ = license_server
        client = LicenseServerClient(base)
        result = client.health()
        assert result["status"] == "ok"

    def test_is_reachable(self, license_server):
        base, _, _ = license_server
        client = LicenseServerClient(base)
        assert client.is_reachable() is True

    def test_is_reachable_unreachable(self):
        client = LicenseServerClient("http://127.0.0.1:19999", timeout=1)
        assert client.is_reachable() is False

    def test_activate(self, license_server):
        base, store, _ = license_server
        key_info = store.generate_key(tier="trial_15d")
        client = LicenseServerClient(base)
        result = client.activate(key_info["key"], "test_hwid_001")
        assert result["success"] is True
        assert "token" in result

    def test_activate_invalid_key(self, license_server):
        base, _, _ = license_server
        client = LicenseServerClient(base)
        result = client.activate("INVALID-KEY", "hwid")
        assert result.get("success") is False

    def test_validate(self, license_server):
        base, store, _ = license_server
        key_info = store.generate_key(tier="trial_15d")
        client = LicenseServerClient(base)
        act = client.activate(key_info["key"], "val_hwid")
        val = client.validate(act["token"], "val_hwid")
        assert val["valid"] is True
        assert val["tier"] == "trial_15d"

    def test_validate_wrong_hwid(self, license_server):
        base, store, _ = license_server
        key_info = store.generate_key()
        client = LicenseServerClient(base)
        act = client.activate(key_info["key"], "hwid_A")
        val = client.validate(act["token"], "hwid_B")
        assert val["valid"] is False

    def test_deactivate(self, license_server):
        base, store, _ = license_server
        key_info = store.generate_key()
        client = LicenseServerClient(base)
        client.activate(key_info["key"], "deact_hwid")
        result = client.deactivate(key_info["key"], "deact_hwid")
        assert result["success"] is True

    def test_connection_error(self):
        client = LicenseServerClient("http://127.0.0.1:19999", timeout=1)
        result = client.activate("key", "hwid")
        assert "error" in result


# ===========================================================================
# LicenseManager Online Tests
# ===========================================================================

class TestOnlineActivation:
    def test_online_activate(self, license_server, tmp_dir):
        base, store, _ = license_server
        key_info = store.generate_key(tier="rental_1y")

        mgr = LicenseManager(data_dir=tmp_dir)
        result = mgr.online_activate(key_info["key"], base)

        assert result["success"] is True
        assert result["tier"] == "rental_1y"
        assert mgr.tier == LicenseTier.RENTAL_1_YEAR
        assert mgr.license_key == key_info["key"]

    def test_online_activate_persists(self, license_server, tmp_dir):
        base, store, _ = license_server
        key_info = store.generate_key()

        mgr1 = LicenseManager(data_dir=tmp_dir)
        mgr1.online_activate(key_info["key"], base)

        # Reload from disk
        mgr2 = LicenseManager(data_dir=tmp_dir)
        assert mgr2.tier == LicenseTier.TRIAL_15_DAYS
        assert mgr2.license_key == key_info["key"]

    def test_online_activate_server_token_stored(self, license_server, tmp_dir):
        base, store, _ = license_server
        key_info = store.generate_key()

        mgr = LicenseManager(data_dir=tmp_dir)
        mgr.online_activate(key_info["key"], base)
        assert mgr._server_token != ""

    def test_online_activate_invalid_key(self, license_server, tmp_dir):
        base, _, _ = license_server
        mgr = LicenseManager(data_dir=tmp_dir)
        result = mgr.online_activate("INVALID", base)
        assert result["success"] is False

    def test_online_activate_unreachable(self, tmp_dir):
        mgr = LicenseManager(data_dir=tmp_dir)
        result = mgr.online_activate("key", "http://127.0.0.1:19999")
        assert result["success"] is False
        assert result.get("message", "").startswith("Connection failed")


class TestOnlineValidation:
    def test_online_validate(self, license_server, tmp_dir):
        base, store, _ = license_server
        key_info = store.generate_key(tier="rental_6m")

        mgr = LicenseManager(data_dir=tmp_dir)
        mgr.online_activate(key_info["key"], base)

        result = mgr.online_validate(base)
        assert result["valid"] is True
        assert result["tier"] == "rental_6m"
        assert result["days_remaining"] > 170

    def test_online_validate_no_token(self, tmp_dir):
        mgr = LicenseManager(data_dir=tmp_dir)
        result = mgr.online_validate("http://127.0.0.1:8600")
        assert result["valid"] is False
        assert "no server token" in result["error"].lower()

    def test_online_validate_after_revocation(self, license_server, tmp_dir):
        base, store, _ = license_server
        key_info = store.generate_key()

        mgr = LicenseManager(data_dir=tmp_dir)
        mgr.online_activate(key_info["key"], base)

        # Revoke on server
        key_hash = LicenseStore._hash_key(key_info["key"])
        store.revoke_key(key_hash)

        result = mgr.online_validate(base)
        assert result["valid"] is False


class TestOnlineDeactivation:
    def test_online_deactivate(self, license_server, tmp_dir):
        base, store, _ = license_server
        key_info = store.generate_key()

        mgr = LicenseManager(data_dir=tmp_dir)
        mgr.online_activate(key_info["key"], base)
        assert mgr.tier == LicenseTier.TRIAL_15_DAYS

        result = mgr.online_deactivate(key_info["key"], base)
        assert result["success"] is True
        assert mgr.tier == LicenseTier.EXPIRED


class TestCheckLicenseOnline:
    def test_online_when_server_available(self, license_server, tmp_dir):
        base, store, _ = license_server
        key_info = store.generate_key(tier="rental_1y")

        mgr = LicenseManager(data_dir=tmp_dir)
        mgr.online_activate(key_info["key"], base)

        status = mgr.check_license_online(base)
        assert status["is_active"] is True
        assert status["online"] is True
        assert status["tier"] == "rental_1y"

    def test_offline_fallback_no_token(self, license_server, tmp_dir):
        base, _, _ = license_server

        mgr = LicenseManager(data_dir=tmp_dir)
        status = mgr.check_license_online(base)
        # No token → offline fallback
        assert status["online"] is False

    def test_offline_fallback_server_unreachable(self, tmp_dir):
        # Activate locally first
        mgr = LicenseManager(data_dir=tmp_dir)
        key = mgr.generate_key(LicenseTier.TRIAL_15_DAYS)
        mgr.activate(key)
        mgr._server_token = "fake-token"

        # Server unreachable → offline fallback
        status = mgr.check_license_online("http://127.0.0.1:19999")
        assert status["online"] is False
        assert status["is_active"] is True  # Still active locally

    def test_offline_fallback_expired(self, tmp_dir):
        mgr = LicenseManager(data_dir=tmp_dir)
        mgr._server_token = "fake-token"

        status = mgr.check_license_online("http://127.0.0.1:19999")
        assert status["online"] is False
        assert status["is_active"] is False


# ===========================================================================
# End-to-End Integration
# ===========================================================================

class TestEndToEnd:
    def test_full_lifecycle(self, license_server, tmp_dir):
        """Full lifecycle: server generate → client activate → validate → deactivate."""
        base, store, _ = license_server

        # 1. Admin generates key on server
        key_info = store.generate_key(
            tier="rental_6m", max_activations=2, label="e2e-test"
        )
        key = key_info["key"]

        # 2. Client activates
        mgr = LicenseManager(data_dir=tmp_dir)
        act_result = mgr.online_activate(key, base)
        assert act_result["success"] is True
        assert mgr.tier == LicenseTier.RENTAL_6_MONTHS

        # 3. Client validates online
        val_result = mgr.online_validate(base)
        assert val_result["valid"] is True
        assert val_result["days_remaining"] > 170

        # 4. check_license_online returns server-confirmed status
        status = mgr.check_license_online(base)
        assert status["is_active"] is True
        assert status["online"] is True
        assert status["tier"] == "rental_6m"

        # 5. Client deactivates
        deact_result = mgr.online_deactivate(key, base)
        assert deact_result["success"] is True
        assert mgr.tier == LicenseTier.EXPIRED

        # 6. Validate should now fail
        val2 = mgr.online_validate(base)
        assert val2["valid"] is False

    def test_token_survives_restart(self, license_server, tmp_dir):
        base, store, _ = license_server
        key_info = store.generate_key()

        # Activate
        mgr1 = LicenseManager(data_dir=tmp_dir)
        mgr1.online_activate(key_info["key"], base)
        token = mgr1._server_token

        # Reload
        mgr2 = LicenseManager(data_dir=tmp_dir)
        assert mgr2._server_token == token

        # Validate with reloaded manager
        result = mgr2.online_validate(base)
        assert result["valid"] is True

    def test_two_machines(self, license_server, tmp_dir):
        base, store, _ = license_server
        key_info = store.generate_key(max_activations=2)

        # Machine 1
        dir1 = os.path.join(tmp_dir, "m1")
        mgr1 = LicenseManager(data_dir=dir1)
        mgr1.online_activate(key_info["key"], base)

        # Machine 2
        dir2 = os.path.join(tmp_dir, "m2")
        mgr2 = LicenseManager(data_dir=dir2)
        mgr2.online_activate(key_info["key"], base)

        # Both validate
        assert mgr1.online_validate(base)["valid"] is True
        assert mgr2.online_validate(base)["valid"] is True

        # Server shows 2 activations
        assert len(store.list_activations()) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
