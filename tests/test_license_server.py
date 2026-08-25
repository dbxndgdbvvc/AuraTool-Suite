"""
Unit Tests — License Server
=============================
Tests cover:
  - LicenseStore: key generation, activation, validation, deactivation
  - Server-side key management (generate, list, revoke)
  - HWID-bound activation with max-device limits
  - Token signing and verification
  - Admin API key authentication
  - Full HTTP API integration tests
"""

import json
import os
import shutil
import tempfile
import threading
import time
import urllib.request
import urllib.error
import pytest

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.license_server import (
    LicenseStore,
    AdminKeyManager,
    LicenseHTTPServer,
    LicenseServerHandler,
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
def store(tmp_dir):
    return LicenseStore(data_dir=tmp_dir)


@pytest.fixture
def server(tmp_dir):
    """Start a test license server on a random port."""
    store = LicenseStore(data_dir=tmp_dir)
    admin_mgr = AdminKeyManager(data_dir=tmp_dir)

    # Generate bootstrap admin key
    admin_key = admin_mgr.generate_key(label="test-admin")

    LicenseServerHandler.store = store
    LicenseServerHandler.admin_mgr = admin_mgr
    LicenseServerHandler.require_admin_auth = True

    import socket
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    srv = LicenseHTTPServer(
        ("127.0.0.1", port), LicenseServerHandler, store, admin_mgr,
        require_admin_auth=True,
    )
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)

    yield f"http://127.0.0.1:{port}", store, admin_key

    srv.shutdown()


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _get(url: str, headers: dict = None) -> tuple[int, dict]:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        resp = urllib.request.urlopen(req)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _post(url: str, data: dict = None, headers: dict = None) -> tuple[int, dict]:
    body = json.dumps(data or {}).encode()
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=body, headers=hdrs, method="POST")
    try:
        resp = urllib.request.urlopen(req)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _delete(url: str, headers: dict = None) -> tuple[int, dict]:
    req = urllib.request.Request(url, method="DELETE", headers=headers or {})
    try:
        resp = urllib.request.urlopen(req)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


# ===========================================================================
# LicenseStore Unit Tests
# ===========================================================================

class TestKeyGeneration:
    def test_generate_trial_key(self, store):
        result = store.generate_key(tier="trial_15d", label="test")
        assert "key" in result
        assert result["key"].startswith("AL-T15-")
        assert result["tier"] == "trial_15d"
        assert result["valid_days"] == 15

    def test_generate_6month_key(self, store):
        result = store.generate_key(tier="rental_6m")
        assert result["key"].startswith("AL-R6M-")
        assert result["tier"] == "rental_6m"
        assert result["valid_days"] == 182

    def test_generate_1year_key(self, store):
        result = store.generate_key(tier="rental_1y")
        assert result["key"].startswith("AL-R1Y-")
        assert result["tier"] == "rental_1y"
        assert result["valid_days"] == 365

    def test_generate_invalid_tier_raises(self, store):
        with pytest.raises(ValueError, match="Invalid tier"):
            store.generate_key(tier="nonexistent")

    def test_generate_expired_tier_raises(self, store):
        with pytest.raises(ValueError, match="Invalid tier"):
            store.generate_key(tier="expired")

    def test_key_checksum_valid(self, store):
        result = store.generate_key()
        assert store._verify_checksum(result["key"]) is True

    def test_key_format_has_4_parts(self, store):
        result = store.generate_key()
        parts = result["key"].split("-")
        assert len(parts) == 4

    def test_custom_max_activations(self, store):
        result = store.generate_key(max_activations=5)
        key_hash = store._hash_key(result["key"])
        assert store._keys[key_hash]["max_activations"] == 5


class TestActivation:
    def test_activate_valid_key(self, store):
        result = store.generate_key(tier="trial_15d")
        act = store.activate(result["key"], "hwid_machine_001")
        assert act["success"] is True
        assert "token" in act
        assert act["tier"] == "trial_15d"

    def test_activate_with_checksum(self, store):
        result = store.generate_key(tier="trial_15d")
        act = store.activate(result["key"], "hwid_machine_001")
        assert act["success"] is True

    def test_activate_invalid_checksum(self, store):
        store.generate_key(tier="trial_15d")
        act = store.activate("AL-T15-000000000000-00000000", "hwid_001")
        assert act["success"] is False
        assert "checksum" in act["error"].lower()

    def test_activate_unknown_key(self, store):
        act = store.activate("AL-T15-AAAAAAAAAAAA-BBBBBBBB", "hwid_001")
        assert act["success"] is False

    def test_activate_revoked_key(self, store):
        result = store.generate_key()
        key_hash = store._hash_key(result["key"])
        store.revoke_key(key_hash)
        act = store.activate(result["key"], "hwid_001")
        assert act["success"] is False
        assert "revoked" in act["error"].lower()

    def test_activate_missing_fields(self, store):
        act = store.activate("", "hwid_001")
        assert act["success"] is False

    def test_activate_reuses_existing(self, store):
        result = store.generate_key(max_activations=1)
        store.activate(result["key"], "hwid_001")
        # Second activation with same HWID should succeed (re-validate)
        act2 = store.activate(result["key"], "hwid_001")
        assert act2["success"] is True

    def test_activate_respects_limit(self, store):
        result = store.generate_key(max_activations=1)
        store.activate(result["key"], "hwid_001")
        # Different HWID should fail
        act2 = store.activate(result["key"], "hwid_002")
        assert act2["success"] is False
        assert "limit" in act2["error"].lower()


class TestValidation:
    def test_validate_valid_token(self, store):
        result = store.generate_key()
        act = store.activate(result["key"], "hwid_001")
        val = store.validate(act["token"], "hwid_001")
        assert val["valid"] is True
        assert val["tier"] == "trial_15d"

    def test_validate_wrong_hwid(self, store):
        result = store.generate_key()
        act = store.activate(result["key"], "hwid_001")
        val = store.validate(act["token"], "hwid_WRONG")
        assert val["valid"] is False
        assert "hwid" in val["error"].lower()

    def test_validate_missing_fields(self, store):
        val = store.validate("", "hwid_001")
        assert val["valid"] is False

    def test_validate_tampered_token(self, store):
        result = store.generate_key()
        act = store.activate(result["key"], "hwid_001")
        # Tamper with token
        parts = act["token"].split(".")
        tampered = parts[0] + ".0000000000000000"
        val = store.validate(tampered, "hwid_001")
        assert val["valid"] is False
        assert "signature" in val["error"].lower()

    def test_validate_after_revocation(self, store):
        result = store.generate_key()
        act = store.activate(result["key"], "hwid_001")
        key_hash = store._hash_key(result["key"])
        store.revoke_key(key_hash)
        val = store.validate(act["token"], "hwid_001")
        assert val["valid"] is False


class TestDeactivation:
    def test_deactivate_existing(self, store):
        result = store.generate_key()
        store.activate(result["key"], "hwid_001")
        deact = store.deactivate(result["key"], "hwid_001")
        assert deact["success"] is True

    def test_deactivate_nonexistent(self, store):
        result = store.generate_key()
        deact = store.deactivate(result["key"], "hwid_001")
        assert deact["success"] is False

    def test_deactivate_frees_slot(self, store):
        result = store.generate_key(max_activations=1)
        store.activate(result["key"], "hwid_001")
        store.deactivate(result["key"], "hwid_001")
        # Now a different HWID can activate
        act = store.activate(result["key"], "hwid_002")
        assert act["success"] is True


class TestRevocation:
    def test_revoke_key(self, store):
        result = store.generate_key()
        key_hash = store._hash_key(result["key"])
        assert store.revoke_key(key_hash) is True

    def test_revoke_nonexistent(self, store):
        assert store.revoke_key("nonexistent") is False

    def test_revoke_clears_activations(self, store):
        result = store.generate_key()
        store.activate(result["key"], "hwid_001")
        key_hash = store._hash_key(result["key"])
        store.revoke_key(key_hash)
        assert len(store._activations) == 0


class TestStats:
    def test_stats(self, store):
        store.generate_key(tier="trial_15d", label="k1")
        store.generate_key(tier="rental_6m", label="k2")
        result = store.generate_key()
        store.activate(result["key"], "hwid_001")

        stats = store.stats()
        assert stats["total_keys"] == 3
        assert stats["active_keys"] == 3
        assert stats["total_activations"] == 1
        assert "trial_15d" in stats["keys_by_tier"]


# ===========================================================================
# API Integration Tests
# ===========================================================================

class TestClientEndpoints:
    def test_get_tiers(self, server):
        base, _, _ = server
        status, resp = _get(f"{base}/tiers")
        assert status == 200
        assert "tiers" in resp
        assert "trial_15d" in resp["tiers"]
        assert "rental_6m" in resp["tiers"]
        assert "rental_1y" in resp["tiers"]

    def test_health(self, server):
        base, _, _ = server
        status, resp = _get(f"{base}/health")
        assert status == 200
        assert resp["status"] == "ok"

    def test_activate_via_api(self, server):
        base, store, admin_key = server
        # Generate key via admin endpoint
        _, gen_resp = _post(
            f"{base}/admin/keys",
            data={"tier": "trial_15d", "label": "api-test"},
            headers={"X-Admin-Key": admin_key},
        )
        key = gen_resp["key"]

        # Activate
        status, resp = _post(f"{base}/activate", {"key": key, "hwid": "test_hwid_001"})
        assert status == 200
        assert resp["success"] is True
        assert "token" in resp

    def test_activate_missing_fields(self, server):
        base, _, _ = server
        status, resp = _post(f"{base}/activate", {"key": "some-key"})
        assert status == 400

    def test_validate_via_api(self, server):
        base, store, admin_key = server
        # Generate + activate
        _, gen = _post(
            f"{base}/admin/keys",
            data={"tier": "trial_15d"},
            headers={"X-Admin-Key": admin_key},
        )
        _, act = _post(f"{base}/activate", {"key": gen["key"], "hwid": "val_hwid"})

        # Validate
        status, resp = _post(f"{base}/validate", {"token": act["token"], "hwid": "val_hwid"})
        assert status == 200
        assert resp["valid"] is True

    def test_validate_wrong_hwid_via_api(self, server):
        base, store, admin_key = server
        _, gen = _post(
            f"{base}/admin/keys",
            data={"tier": "trial_15d"},
            headers={"X-Admin-Key": admin_key},
        )
        _, act = _post(f"{base}/activate", {"key": gen["key"], "hwid": "hw_A"})

        status, resp = _post(f"{base}/validate", {"token": act["token"], "hwid": "hw_B"})
        assert status == 401
        assert resp["valid"] is False

    def test_deactivate_via_api(self, server):
        base, store, admin_key = server
        _, gen = _post(
            f"{base}/admin/keys",
            data={"tier": "trial_15d"},
            headers={"X-Admin-Key": admin_key},
        )
        _post(f"{base}/activate", {"key": gen["key"], "hwid": "deact_hwid"})

        status, resp = _post(f"{base}/deactivate", {"key": gen["key"], "hwid": "deact_hwid"})
        assert status == 200
        assert resp["success"] is True

    def test_unknown_endpoint(self, server):
        base, _, _ = server
        status, _ = _get(f"{base}/nonexistent")
        assert status == 404


class TestAdminEndpoints:
    def test_generate_key(self, server):
        base, _, admin_key = server
        status, resp = _post(
            f"{base}/admin/keys",
            data={"tier": "rental_1y", "label": "test-key", "max_activations": 3},
            headers={"X-Admin-Key": admin_key},
        )
        assert status == 201
        assert resp["tier"] == "rental_1y"
        assert resp["max_activations"] == 3
        assert "key" in resp

    def test_list_keys(self, server):
        base, _, admin_key = server
        _post(
            f"{base}/admin/keys",
            data={"tier": "trial_15d", "label": "k1"},
            headers={"X-Admin-Key": admin_key},
        )
        status, resp = _get(f"{base}/admin/keys", {"X-Admin-Key": admin_key})
        assert status == 200
        assert resp["total"] >= 1

    def test_revoke_key(self, server):
        base, store, admin_key = server
        _, gen = _post(
            f"{base}/admin/keys",
            data={"tier": "trial_15d"},
            headers={"X-Admin-Key": admin_key},
        )
        key_hash = store._hash_key(gen["key"])
        status, resp = _delete(
            f"{base}/admin/keys/{key_hash}",
            {"X-Admin-Key": admin_key},
        )
        assert status == 200

    def test_revoke_nonexistent_key(self, server):
        base, _, admin_key = server
        status, _ = _delete(
            f"{base}/admin/keys/nonexistent",
            {"X-Admin-Key": admin_key},
        )
        assert status == 404

    def test_list_activations(self, server):
        base, _, admin_key = server
        status, resp = _get(f"{base}/admin/activations", {"X-Admin-Key": admin_key})
        assert status == 200
        assert "activations" in resp

    def test_stats(self, server):
        base, _, admin_key = server
        status, resp = _get(f"{base}/admin/stats", {"X-Admin-Key": admin_key})
        assert status == 200
        assert "total_keys" in resp
        assert "total_activations" in resp

    def test_admin_requires_auth(self, server):
        base, _, _ = server
        status, resp = _get(f"{base}/admin/keys")
        assert status == 401

    def test_admin_wrong_key(self, server):
        base, _, _ = server
        status, resp = _get(
            f"{base}/admin/keys",
            {"X-Admin-Key": "wrong-key"},
        )
        assert status == 401


class TestFullWorkflow:
    def test_complete_lifecycle(self, server):
        """Full lifecycle: generate → activate → validate → deactivate."""
        base, store, admin_key = server

        # 1. Generate key
        _, gen = _post(
            f"{base}/admin/keys",
            data={"tier": "rental_6m", "label": "lifecycle-test", "max_activations": 2},
            headers={"X-Admin-Key": admin_key},
        )
        key = gen["key"]
        assert gen["tier"] == "rental_6m"

        # 2. Activate on machine 1
        _, act1 = _post(f"{base}/activate", {"key": key, "hwid": "machine_001"})
        assert act1["success"] is True
        token1 = act1["token"]

        # 3. Activate on machine 2
        _, act2 = _post(f"{base}/activate", {"key": key, "hwid": "machine_002"})
        assert act2["success"] is True

        # 4. Validate machine 1
        _, val1 = _post(f"{base}/validate", {"token": token1, "hwid": "machine_001"})
        assert val1["valid"] is True
        assert val1["days_remaining"] > 170

        # 5. Machine 3 should fail (limit reached)
        _, act3 = _post(f"{base}/activate", {"key": key, "hwid": "machine_003"})
        assert act3["success"] is False
        assert "limit" in act3["error"].lower()

        # 6. Deactivate machine 1
        _, deact = _post(f"{base}/deactivate", {"key": key, "hwid": "machine_001"})
        assert deact["success"] is True

        # 7. Now machine 3 can activate
        _, act3b = _post(f"{base}/activate", {"key": key, "hwid": "machine_003"})
        assert act3b["success"] is True

        # 8. Check stats
        _, stats = _get(f"{base}/admin/stats", {"X-Admin-Key": admin_key})
        assert stats["total_activations"] == 2  # machine_002 + machine_003

    def test_revoke_key_invalidates_all_tokens(self, server):
        base, store, admin_key = server

        _, gen = _post(
            f"{base}/admin/keys",
            data={"tier": "trial_15d"},
            headers={"X-Admin-Key": admin_key},
        )
        key = gen["key"]

        _, act = _post(f"{base}/activate", {"key": key, "hwid": "hw_revoke"})

        # Revoke
        key_hash = store._hash_key(key)
        _delete(f"{base}/admin/keys/{key_hash}", {"X-Admin-Key": admin_key})

        # Validate should fail
        _, val = _post(f"{base}/validate", {"token": act["token"], "hwid": "hw_revoke"})
        assert val["valid"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
