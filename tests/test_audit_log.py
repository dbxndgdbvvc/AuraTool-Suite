"""
Unit Tests — API Audit Trail
==============================
Tests cover:
  - AuditLogger: request, event, and auth logging
  - JSONL persistence and rotation
  - Query with filters (type, method, path, key, since)
  - Statistics computation
  - Log archival and clearing
  - CLI audit commands
  - Factory API /api/auth/audit endpoint
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

from core.audit_log import AuditLogger


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def audit(tmp_dir):
    return AuditLogger(data_dir=tmp_dir)


@pytest.fixture
def api_server(tmp_dir):
    """Start a test Factory API server with audit logging."""
    from core.factory_api import (
        FactoryAPIServer, FactoryAPIHandler, register_routes, Router,
        APIKeyManager,
    )
    from core.audit_log import AuditLogger
    from auratool_factory import FactoryManager

    api_key_mgr = APIKeyManager(data_dir=os.path.join(tmp_dir, "api_keys"))
    test_key = api_key_mgr.generate_key(role="admin", label="test")
    audit_log = AuditLogger(data_dir=tmp_dir)

    factory = FactoryManager(os.path.join(tmp_dir, "factory"))
    router = Router()
    register_routes(router)

    FactoryAPIHandler.factory = factory
    FactoryAPIHandler.router = router
    FactoryAPIHandler.license_mgr = None
    FactoryAPIHandler.api_key_mgr = api_key_mgr
    FactoryAPIHandler.require_auth = True
    FactoryAPIHandler.audit = audit_log

    import socket
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    srv = FactoryAPIServer(
        ("127.0.0.1", port), FactoryAPIHandler, factory,
        api_key_mgr=api_key_mgr, require_auth=True,
        audit=audit_log,
    )
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)

    yield f"http://127.0.0.1:{port}", factory, api_key_mgr, audit_log, test_key

    srv.shutdown()


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        resp = urllib.request.urlopen(req)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _post(url, data=None, headers=None):
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


# ===========================================================================
# AuditLogger Unit Tests
# ===========================================================================

class TestRequestLogging:
    def test_log_request(self, audit):
        audit.log_request("GET", "/api/clients", "abc123", "127.0.0.1", 200, 12.5)
        entries = audit.query()
        assert len(entries) == 1
        assert entries[0]["type"] == "request"
        assert entries[0]["method"] == "GET"
        assert entries[0]["path"] == "/api/clients"
        assert entries[0]["status"] == 200
        assert entries[0]["latency_ms"] == 12.5

    def test_log_request_with_detail(self, audit):
        audit.log_request("POST", "/api/tickets", status=201, detail={"ticket_id": "TK-123"})
        entries = audit.query()
        assert entries[0]["detail"]["ticket_id"] == "TK-123"

    def test_key_hash_truncated(self, audit):
        long_hash = "a" * 64
        audit.log_request("GET", "/", key_hash=long_hash)
        entries = audit.query()
        assert len(entries[0]["key_hash"]) < 64
        assert entries[0]["key_hash"].endswith("...")


class TestEventLogging:
    def test_log_event(self, audit):
        audit.log_event("key_generated", key_hash="abc123", detail={"role": "admin"})
        entries = audit.query()
        assert len(entries) == 1
        assert entries[0]["type"] == "key_event"
        assert entries[0]["event"] == "key_generated"
        assert entries[0]["detail"]["role"] == "admin"

    def test_log_auth_success(self, audit):
        audit.log_auth(True, key_hash="abc", client_ip="10.0.0.1", method="GET", path="/api/clients")
        entries = audit.query()
        assert entries[0]["type"] == "auth_event"
        assert entries[0]["success"] is True

    def test_log_auth_failure(self, audit):
        audit.log_auth(False, key_hash="wrong", client_ip="10.0.0.1", reason="Invalid API key")
        entries = audit.query()
        assert entries[0]["success"] is False
        assert entries[0]["reason"] == "Invalid API key"


class TestQueryFilters:
    def _seed(self, audit):
        audit.log_request("GET", "/api/clients", "key1", "10.0.0.1", 200, 5)
        audit.log_request("POST", "/api/tickets", "key2", "10.0.0.2", 201, 15)
        audit.log_request("GET", "/api/parts", "key1", "10.0.0.1", 200, 8)
        audit.log_auth(True, "key1", "10.0.0.1", "GET", "/api/clients")
        audit.log_auth(False, "key3", "10.0.0.3", "POST", "/api/tickets", "Invalid key")

    def test_filter_by_type(self, audit):
        self._seed(audit)
        reqs = audit.query(event_type="request")
        assert all(e["type"] == "request" for e in reqs)
        assert len(reqs) == 3

    def test_filter_by_method(self, audit):
        self._seed(audit)
        posts = audit.query(method="POST")
        assert all(e["method"] == "POST" for e in posts)

    def test_filter_by_path(self, audit):
        self._seed(audit)
        clients = audit.query(path_contains="clients")
        assert len(clients) == 2  # GET + auth

    def test_filter_by_key(self, audit):
        self._seed(audit)
        key1_entries = audit.query(key_hash_prefix="key1")
        assert all(e["key_hash"].startswith("key1") for e in key1_entries)

    def test_filter_by_since(self, audit):
        self._seed(audit)
        now = time.time()
        audit.log_request("GET", "/after", "k", "127.0.0.1", 200, 1)
        recent = audit.query(since_ts=now)
        assert len(recent) == 1
        assert recent[0]["path"] == "/after"

    def test_limit(self, audit):
        for i in range(20):
            audit.log_request("GET", f"/{i}", status=200)
        result = audit.query(limit=5)
        assert len(result) == 5

    def test_sorted_by_time_desc(self, audit):
        audit.log_request("GET", "/first", status=200)
        time.sleep(0.01)
        audit.log_request("GET", "/second", status=200)
        entries = audit.query()
        assert entries[0]["path"] == "/second"
        assert entries[1]["path"] == "/first"


class TestStats:
    def test_stats(self, audit):
        audit.log_request("GET", "/a", "k1", "10.0.0.1", 200, 5)
        audit.log_request("POST", "/b", "k2", "10.0.0.2", 201, 10)
        audit.log_auth(True, "k1", "10.0.0.1")
        audit.log_auth(False, "k3", "10.0.0.3", reason="bad")

        stats = audit.stats()
        assert stats["total_entries"] == 4
        assert stats["auth_attempts"] == 2
        assert stats["auth_failures"] == 1
        assert stats["unique_ips"] == 3
        assert stats["unique_keys"] == 3
        assert stats["by_method"]["GET"] == 1
        assert stats["by_method"]["POST"] == 1


class TestPersistence:
    def test_entries_persist(self, tmp_dir):
        a1 = AuditLogger(data_dir=tmp_dir)
        a1.log_request("GET", "/test", status=200)

        a2 = AuditLogger(data_dir=tmp_dir)
        entries = a2.query()
        assert len(entries) == 1

    def test_log_file_is_jsonl(self, audit):
        audit.log_request("GET", "/x", status=200)
        audit.log_request("POST", "/y", status=201)

        log_path = os.path.join(audit._data_dir, AuditLogger.LOG_FILE)
        with open(log_path) as f:
            lines = [l.strip() for l in f if l.strip()]
        assert len(lines) == 2
        # Each line should be valid JSON
        for line in lines:
            json.loads(line)


class TestRotation:
    def test_rotation_on_large_file(self, audit):
        # Write a large log entry to trigger rotation
        audit.MAX_FILE_SIZE = 200  # Very small for testing
        for i in range(50):
            audit.log_request("GET", f"/endpoint/{i}", detail={"data": "x" * 20})

        # Should have rotated at least once
        archive_files = [f for f in os.listdir(audit._data_dir)
                        if f.startswith(AuditLogger.LOG_FILE + AuditLogger.ARCHIVE_SUFFIX)]
        assert len(archive_files) >= 1


class TestClear:
    def test_clear_archives(self, audit):
        audit.log_request("GET", "/a", status=200)
        audit.log_request("GET", "/b", status=200)
        count = audit.clear()
        assert count == 2
        # Current log should be empty
        assert len(audit.query()) == 0

    def test_clear_empty(self, audit):
        count = audit.clear()
        assert count == 0


# ===========================================================================
# Factory API Audit Integration Tests
# ===========================================================================

class TestFactoryAPIAudit:
    def test_request_logged(self, api_server):
        base, _, _, audit_log, test_key = api_server
        _get(f"{base}/api/clients", {"X-API-Key": test_key})
        time.sleep(0.1)
        entries = audit_log.query(event_type="request")
        assert len(entries) >= 1
        assert entries[0]["path"] == "/api/clients"

    def test_auth_success_logged(self, api_server):
        base, _, _, audit_log, test_key = api_server
        _get(f"{base}/api/clients", {"X-API-Key": test_key})
        time.sleep(0.1)
        auth_entries = audit_log.query(event_type="auth_event")
        assert len(auth_entries) >= 1
        assert auth_entries[0]["success"] is True

    def test_auth_failure_logged(self, api_server):
        base, _, _, audit_log, _ = api_server
        _get(f"{base}/api/clients", {"X-API-Key": "bad-key"})
        time.sleep(0.1)
        auth_entries = audit_log.query(event_type="auth_event")
        failed = [e for e in auth_entries if not e["success"]]
        assert len(failed) >= 1

    def test_audit_endpoint(self, api_server):
        base, _, _, audit_log, test_key = api_server
        # Generate some log entries
        _get(f"{base}/api/clients", {"X-API-Key": test_key})
        _post(f"{base}/api/clients", {"name": "Test"}, {"X-API-Key": test_key})
        time.sleep(0.2)

        # /api/auth/audit uses API key auth (X-API-Key), not admin key
        status, resp = _get(f"{base}/api/auth/audit?limit=10", {"X-API-Key": test_key})
        assert status == 200
        assert "entries" in resp

    def test_audit_stats_endpoint(self, api_server):
        base, _, _, audit_log, test_key = api_server
        _get(f"{base}/api/clients", {"X-API-Key": test_key})
        time.sleep(0.2)

        status, resp = _get(f"{base}/api/auth/audit/stats", {"X-API-Key": test_key})
        assert status == 200
        assert "total_entries" in resp


# ===========================================================================
# CLI Audit Tests
# ===========================================================================

class TestCLIAudit:
    def _cli(self, tmp_dir, *args):
        import subprocess
        cli_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "core", "api_key_cli.py",
        )
        cmd = [sys.executable, cli_path, "--data-dir", tmp_dir] + list(args)
        return subprocess.run(cmd, capture_output=True, text=True, timeout=10)

    def test_audit_empty(self, tmp_dir):
        result = self._cli(tmp_dir, "audit")
        assert result.returncode == 0
        assert "no audit entries" in result.stdout.lower() or "0 entries" in result.stdout

    def test_audit_with_entries(self, tmp_dir):
        audit = AuditLogger(data_dir=tmp_dir)
        audit.log_request("GET", "/api/clients", status=200)
        audit.log_request("POST", "/api/tickets", status=201)

        result = self._cli(tmp_dir, "audit")
        assert result.returncode == 0
        assert "2" in result.stdout

    def test_audit_json(self, tmp_dir):
        audit = AuditLogger(data_dir=tmp_dir)
        audit.log_request("GET", "/api/clients", status=200)

        result = self._cli(tmp_dir, "audit", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert len(data) == 1

    def test_audit_filter_type(self, tmp_dir):
        audit = AuditLogger(data_dir=tmp_dir)
        audit.log_request("GET", "/a", status=200)
        audit.log_auth(True, "k", "10.0.0.1")

        result = self._cli(tmp_dir, "audit", "--type", "auth_event", "--json")
        data = json.loads(result.stdout)
        assert len(data) == 1
        assert data[0]["type"] == "auth_event"

    def test_audit_filter_method(self, tmp_dir):
        audit = AuditLogger(data_dir=tmp_dir)
        audit.log_request("GET", "/a", status=200)
        audit.log_request("POST", "/b", status=201)

        result = self._cli(tmp_dir, "audit", "--method", "POST", "--json")
        data = json.loads(result.stdout)
        assert len(data) == 1
        assert data[0]["method"] == "POST"

    def test_audit_filter_limit(self, tmp_dir):
        audit = AuditLogger(data_dir=tmp_dir)
        for i in range(10):
            audit.log_request("GET", f"/{i}", status=200)

        result = self._cli(tmp_dir, "audit", "-n", "3", "--json")
        data = json.loads(result.stdout)
        assert len(data) == 3

    def test_audit_stats(self, tmp_dir):
        audit = AuditLogger(data_dir=tmp_dir)
        audit.log_request("GET", "/a", "k1", "10.0.0.1", 200, 5)
        audit.log_auth(True, "k1", "10.0.0.1")

        result = self._cli(tmp_dir, "audit-stats", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["total_entries"] == 2

    def test_audit_clear(self, tmp_dir):
        audit = AuditLogger(data_dir=tmp_dir)
        audit.log_request("GET", "/a", status=200)

        result = self._cli(tmp_dir, "audit-clear")
        assert result.returncode == 0
        assert "archived" in result.stdout.lower()

        # Verify cleared
        audit2 = AuditLogger(data_dir=tmp_dir)
        assert len(audit2.query()) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
