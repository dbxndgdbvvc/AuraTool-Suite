"""
Unit Tests — API Key Authentication Middleware
================================================
Tests cover:
  - API key generation (admin + readonly)
  - Key format validation and checksum verification
  - Authentication with valid/invalid/missing keys
  - Role-based access control (admin vs readonly)
  - Key revocation
  - Key persistence across instances
  - Rate limiting on failed attempts
  - HMAC constant-time comparison
  - Integration with Factory REST API endpoints
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

from core.factory_api import (
    APIKeyManager,
    FactoryAPIServer,
    FactoryAPIHandler,
    register_routes,
    Router,
)
from auratool_factory import FactoryManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def key_mgr(tmp_dir):
    return APIKeyManager(data_dir=tmp_dir)


@pytest.fixture
def server_with_auth(tmp_dir):
    """Start a test API server with authentication enabled."""
    factory = FactoryManager(tmp_dir)
    api_key_mgr = APIKeyManager(data_dir=tmp_dir)

    # Generate a test key
    test_key = api_key_mgr.generate_key(role="admin", label="test-admin")

    # Build router
    router = Router()
    register_routes(router)

    FactoryAPIHandler.factory = factory
    FactoryAPIHandler.router = router
    FactoryAPIHandler.license_mgr = None
    FactoryAPIHandler.api_key_mgr = api_key_mgr
    FactoryAPIHandler.require_auth = True

    import socket
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    srv = FactoryAPIServer(
        ("127.0.0.1", port), FactoryAPIHandler, factory,
        api_key_mgr=api_key_mgr, require_auth=True,
    )
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)

    yield f"http://127.0.0.1:{port}", factory, api_key_mgr, test_key

    srv.shutdown()


@pytest.fixture
def server_no_auth(tmp_dir):
    """Start a test API server without authentication."""
    factory = FactoryManager(tmp_dir)

    router = Router()
    register_routes(router)

    FactoryAPIHandler.factory = factory
    FactoryAPIHandler.router = router
    FactoryAPIHandler.license_mgr = None
    FactoryAPIHandler.api_key_mgr = None
    FactoryAPIHandler.require_auth = False

    import socket
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    srv = FactoryAPIServer(
        ("127.0.0.1", port), FactoryAPIHandler, factory,
        api_key_mgr=None, require_auth=False,
    )
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)

    yield f"http://127.0.0.1:{port}", factory

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
# APIKeyManager Unit Tests
# ===========================================================================

class TestKeyGeneration:
    def test_generate_admin_key(self, key_mgr):
        key = key_mgr.generate_key(role="admin", label="test")
        assert key.startswith("ATK-ADMIN-")
        assert len(key) > 20

    def test_generate_readonly_key(self, key_mgr):
        key = key_mgr.generate_key(role="readonly", label="viewer")
        assert key.startswith("ATK-READONLY-")

    def test_generate_invalid_role_raises(self, key_mgr):
        with pytest.raises(ValueError, match="Invalid role"):
            key_mgr.generate_key(role="superadmin")

    def test_key_format_has_checksum(self, key_mgr):
        key = key_mgr.generate_key(role="admin")
        parts = key.split("-")
        assert len(parts) == 4  # ATK-ADMIN-RANDOM-CHECKSUM
        assert len(parts[-1]) == 8  # 8-char hex checksum

    def test_checksum_is_valid(self, key_mgr):
        key = key_mgr.generate_key(role="admin")
        assert APIKeyManager._verify_checksum(key) is True

    def test_tampered_checksum_fails(self, key_mgr):
        key = key_mgr.generate_key(role="admin")
        parts = key.split("-")
        parts[-1] = "00000000"
        tampered = "-".join(parts)
        assert APIKeyManager._verify_checksum(tampered) is False


class TestKeyPersistence:
    def test_key_survives_reload(self, tmp_dir):
        mgr1 = APIKeyManager(data_dir=tmp_dir)
        key = mgr1.generate_key(role="admin", label="persist-test")

        mgr2 = APIKeyManager(data_dir=tmp_dir)
        status, _, _ = mgr2.authenticate(key)
        assert status is True

    def test_revoked_key_stays_revoked(self, tmp_dir):
        mgr1 = APIKeyManager(data_dir=tmp_dir)
        key = mgr1.generate_key(role="admin")
        key_hash = APIKeyManager._hash_key(key)
        mgr1.revoke_key(key_hash)

        mgr2 = APIKeyManager(data_dir=tmp_dir)
        status, error, _ = mgr2.authenticate(key)
        assert status is False
        assert "revoked" in error.lower()


class TestAuthentication:
    def test_valid_admin_key(self, key_mgr):
        key = key_mgr.generate_key(role="admin")
        status, error, meta = key_mgr.authenticate(key, method="POST")
        assert status is True
        assert meta["role"] == "admin"

    def test_valid_readonly_key_get(self, key_mgr):
        key = key_mgr.generate_key(role="readonly")
        status, error, meta = key_mgr.authenticate(key, method="GET")
        assert status is True
        assert meta["role"] == "readonly"

    def test_readonly_key_rejected_for_post(self, key_mgr):
        key = key_mgr.generate_key(role="readonly")
        status, error, meta = key_mgr.authenticate(key, method="POST")
        assert status is False
        assert "readonly" in error.lower()

    def test_readonly_key_rejected_for_put(self, key_mgr):
        key = key_mgr.generate_key(role="readonly")
        status, error, _ = key_mgr.authenticate(key, method="PUT")
        assert status is False

    def test_readonly_key_rejected_for_delete(self, key_mgr):
        key = key_mgr.generate_key(role="readonly")
        status, error, _ = key_mgr.authenticate(key, method="DELETE")
        assert status is False

    def test_missing_key(self, key_mgr):
        status, error, _ = key_mgr.authenticate("")
        assert status is False
        assert "missing" in error.lower()

    def test_invalid_key(self, key_mgr):
        status, error, _ = key_mgr.authenticate("ATK-ADMIN-000000000000-00000000")
        assert status is False
        assert "invalid" in error.lower()

    def test_wrong_format_key(self, key_mgr):
        status, error, _ = key_mgr.authenticate("WRONG-FORMAT-KEY")
        assert status is False

    def test_revoked_key(self, key_mgr):
        key = key_mgr.generate_key(role="admin")
        key_hash = APIKeyManager._hash_key(key)
        key_mgr.revoke_key(key_hash)

        status, error, _ = key_mgr.authenticate(key)
        assert status is False
        assert "revoked" in error.lower()

    def test_usage_stats_updated(self, key_mgr):
        key = key_mgr.generate_key(role="admin")
        key_mgr.authenticate(key, method="GET")
        key_mgr.authenticate(key, method="POST")

        keys = key_mgr.list_keys()
        admin_key = [k for k in keys if k["role"] == "admin"][0]
        assert admin_key["request_count"] >= 2
        assert admin_key["last_used"] > 0


class TestKeyRevocation:
    def test_revoke_existing_key(self, key_mgr):
        key = key_mgr.generate_key(role="admin")
        key_hash = APIKeyManager._hash_key(key)
        assert key_mgr.revoke_key(key_hash) is True

        status, _, _ = key_mgr.authenticate(key)
        assert status is False

    def test_revoke_nonexistent_key(self, key_mgr):
        assert key_mgr.revoke_key("nonexistent_hash") is False


class TestKeyListing:
    def test_list_keys(self, key_mgr):
        key_mgr.generate_key(role="admin", label="admin-key")
        key_mgr.generate_key(role="readonly", label="viewer-key")

        keys = key_mgr.list_keys()
        assert len(keys) == 2
        roles = {k["role"] for k in keys}
        assert "admin" in roles
        assert "readonly" in roles

    def test_list_keys_shows_revoked_status(self, key_mgr):
        key = key_mgr.generate_key(role="admin")
        key_hash = APIKeyManager._hash_key(key)
        key_mgr.revoke_key(key_hash)

        keys = key_mgr.list_keys()
        assert any(k["revoked"] for k in keys)


class TestRateLimiting:
    def test_rate_limit_ip_after_failures(self, key_mgr):
        for _ in range(APIKeyManager.MAX_FAILED_ATTEMPTS + 1):
            key_mgr.authenticate("INVALID", client_ip="192.168.1.100")

        # Now even a valid key from the same IP is blocked
        valid_key = key_mgr.generate_key(role="admin")
        status, error, _ = key_mgr.authenticate(valid_key, client_ip="192.168.1.100")
        assert status is False
        assert "too many" in error.lower()

    def test_different_ip_not_affected(self, key_mgr):
        for _ in range(APIKeyManager.MAX_FAILED_ATTEMPTS + 1):
            key_mgr.authenticate("INVALID", client_ip="192.168.1.100")

        valid_key = key_mgr.generate_key(role="admin")
        status, _, _ = key_mgr.authenticate(valid_key, client_ip="192.168.1.200")
        assert status is True

    def test_clear_failed_attempts(self, key_mgr):
        for _ in range(APIKeyManager.MAX_FAILED_ATTEMPTS + 1):
            key_mgr.authenticate("INVALID", client_ip="10.0.0.1")

        key_mgr.clear_failed_attempts("10.0.0.1")
        valid_key = key_mgr.generate_key(role="admin")
        status, _, _ = key_mgr.authenticate(valid_key, client_ip="10.0.0.1")
        assert status is True


# ===========================================================================
# API Integration Tests (with live server)
# ===========================================================================

class TestAPIAuthMiddleware:
    def test_no_key_returns_401(self, server_with_auth):
        base, _, _, _ = server_with_auth
        status, resp = _get(f"{base}/api/clients")
        assert status == 401
        assert "authentication" in resp["error"].lower()

    def test_invalid_key_returns_401(self, server_with_auth):
        base, _, _, _ = server_with_auth
        status, resp = _get(
            f"{base}/api/clients",
            headers={"X-API-Key": "ATK-ADMIN-000000000000-00000000"},
        )
        assert status == 401

    def test_valid_key_allows_access(self, server_with_auth):
        base, _, _, test_key = server_with_auth
        status, resp = _get(
            f"{base}/api/clients",
            headers={"X-API-Key": test_key},
        )
        assert status == 200
        assert isinstance(resp, list)

    def test_key_via_query_param(self, server_with_auth):
        base, _, _, test_key = server_with_auth
        status, resp = _get(f"{base}/api/clients?api_key={test_key}")
        assert status == 200

    def test_readonly_key_blocks_post(self, server_with_auth):
        base, _, api_key_mgr, _ = server_with_auth
        readonly_key = api_key_mgr.generate_key(role="readonly", label="ro")

        status, resp = _post(
            f"{base}/api/clients",
            data={"name": "Test"},
            headers={"X-API-Key": readonly_key},
        )
        assert status == 401
        assert "readonly" in resp["message"].lower()

    def test_readonly_key_allows_get(self, server_with_auth):
        base, _, api_key_mgr, _ = server_with_auth
        readonly_key = api_key_mgr.generate_key(role="readonly", label="ro")

        status, resp = _get(
            f"{base}/api/clients",
            headers={"X-API-Key": readonly_key},
        )
        assert status == 200

    def test_no_auth_mode_allows_all(self, server_no_auth):
        base, _ = server_no_auth
        status, resp = _get(f"{base}/api/clients")
        assert status == 200

    def test_no_auth_mode_allows_post(self, server_no_auth):
        base, _ = server_no_auth
        status, resp = _post(
            f"{base}/api/clients",
            data={"name": "NoAuth Client"},
        )
        assert status == 201


class TestAPIKeyManagementEndpoints:
    def test_generate_key_via_api(self, server_with_auth):
        base, _, _, test_key = server_with_auth
        status, resp = _post(
            f"{base}/api/auth/keys",
            data={"role": "readonly", "label": "generated-via-api"},
            headers={"X-API-Key": test_key},
        )
        assert status == 201
        assert "api_key" in resp
        assert resp["role"] == "readonly"

    def test_list_keys_via_api(self, server_with_auth):
        base, _, _, test_key = server_with_auth
        status, resp = _get(
            f"{base}/api/auth/keys",
            headers={"X-API-Key": test_key},
        )
        assert status == 200
        assert "keys" in resp
        assert resp["total"] >= 1

    def test_generated_key_works(self, server_with_auth):
        base, _, _, test_key = server_with_auth

        # Generate a new key
        _, gen_resp = _post(
            f"{base}/api/auth/keys",
            data={"role": "admin", "label": "new-admin"},
            headers={"X-API-Key": test_key},
        )
        new_key = gen_resp["api_key"]

        # Use the new key to access the API
        status, resp = _get(
            f"{base}/api/clients",
            headers={"X-API-Key": new_key},
        )
        assert status == 200

    def test_revoke_key_via_api(self, server_with_auth):
        base, _, api_key_mgr, test_key = server_with_auth

        # Generate a key to revoke
        key_to_revoke = api_key_mgr.generate_key(role="readonly", label="to-revoke")
        key_hash = APIKeyManager._hash_key(key_to_revoke)

        # Revoke it
        status, resp = _delete(
            f"{base}/api/auth/keys/{key_hash[:12]}",
            headers={"X-API-Key": test_key},
        )
        assert status == 200

        # Verify it no longer works
        status, resp = _get(
            f"{base}/api/clients",
            headers={"X-API-Key": key_to_revoke},
        )
        assert status == 401

    def test_full_workflow_with_auth(self, server_with_auth):
        """End-to-end: auth → create client → list → verify."""
        base, _, _, test_key = server_with_auth
        auth_headers = {"X-API-Key": test_key}

        # 1. List clients (empty)
        _, clients = _get(f"{base}/api/clients", headers=auth_headers)
        assert len(clients) == 0

        # 2. Create a client
        status, resp = _post(
            f"{base}/api/clients",
            data={"name": "Auth Test Client", "phone": "+12345"},
            headers=auth_headers,
        )
        assert status == 201

        # 3. List clients (now has 1)
        _, clients = _get(f"{base}/api/clients", headers=auth_headers)
        assert len(clients) == 1
        assert clients[0]["name"] == "Auth Test Client"

        # 4. Dashboard
        status, dash = _get(f"{base}/api/dashboard", headers=auth_headers)
        assert status == 200
        assert dash["total_clients"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
