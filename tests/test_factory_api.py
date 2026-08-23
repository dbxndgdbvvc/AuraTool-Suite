"""
Unit tests for AuraTool-Suite Workshop & Factory REST API.
Tests all endpoints using a live server on a random port.
"""

import json
import threading
import time
import urllib.request
import urllib.error
import tempfile
import shutil
import pytest

from core.factory_api import FactoryAPIServer, FactoryAPIHandler, register_routes, Router
from auratool_factory import (
    FactoryManager, DeviceCategory, RepairStatus, PartType,
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
def factory(tmp_dir):
    return FactoryManager(tmp_dir)


@pytest.fixture
def server(tmp_dir):
    """Start a test API server on a random port."""
    factory = FactoryManager(tmp_dir)

    # Build a fresh router
    router = Router()
    register_routes(router)

    # Monkeypatch the handler class
    FactoryAPIHandler.factory = factory
    FactoryAPIHandler.router = router

    # Find a free port
    import socket
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    srv = FactoryAPIServer(("127.0.0.1", port), FactoryAPIHandler, factory)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)

    yield f"http://127.0.0.1:{port}", factory

    srv.shutdown()


def _get(url: str) -> dict:
    resp = urllib.request.urlopen(url)
    return json.loads(resp.read())


def _post(url: str, data: dict = None) -> tuple[int, dict]:
    body = json.dumps(data or {}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        resp = urllib.request.urlopen(req)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _put(url: str, data: dict) -> tuple[int, dict]:
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="PUT")
    try:
        resp = urllib.request.urlopen(req)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def _delete(url: str) -> tuple[int, dict]:
    req = urllib.request.Request(url, method="DELETE")
    try:
        resp = urllib.request.urlopen(req)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


# ===========================================================================
# Client Endpoints
# ===========================================================================

class TestClientEndpoints:
    def test_list_empty(self, server):
        base, _ = server
        data = _get(f"{base}/api/clients")
        assert isinstance(data, list)
        assert len(data) == 0

    def test_create_client(self, server):
        base, _ = server
        status, resp = _post(f"{base}/api/clients", {
            "name": "Ahmed", "phone": "+96891234", "email": "a@test.com",
        })
        assert status == 201
        assert "client_id" in resp
        assert resp["name"] == "Ahmed"

    def test_create_client_no_name(self, server):
        base, _ = server
        status, resp = _post(f"{base}/api/clients", {"phone": "123"})
        assert status == 400
        assert "error" in resp

    def test_get_client(self, server):
        base, fm = server
        c = fm.clients.add_client("Test Get")
        data = _get(f"{base}/api/clients/{c.client_id}")
        assert data["name"] == "Test Get"
        assert data["client_id"] == c.client_id

    def test_get_client_not_found(self, server):
        base, _ = server
        status, resp = _get(f"{base}/api/clients/nonexistent") if False else (None, None)
        try:
            urllib.request.urlopen(f"{base}/api/clients/nonexistent")
        except urllib.error.HTTPError as e:
            assert e.code == 404

    def test_delete_client(self, server):
        base, fm = server
        c = fm.clients.add_client("To Delete")
        status, resp = _delete(f"{base}/api/clients/{c.client_id}")
        assert status == 200
        assert fm.clients.get_client(c.client_id) is None

    def test_delete_client_not_found(self, server):
        base, _ = server
        status, _ = _delete(f"{base}/api/clients/nope")
        assert status == 404

    def test_search_clients(self, server):
        base, fm = server
        fm.clients.add_client("Alice Smith")
        fm.clients.add_client("Bob Jones")
        data = _get(f"{base}/api/clients/search?q=alice")
        assert len(data) == 1
        assert data[0]["name"] == "Alice Smith"

    def test_top_clients(self, server):
        base, fm = server
        c1 = fm.clients.add_client("Top1")
        c2 = fm.clients.add_client("Top2")
        c1.ticket_ids = ["t1", "t2", "t3"]
        data = _get(f"{base}/api/clients/top?limit=1")
        assert len(data) == 1
        assert data[0]["client_id"] == c1.client_id


# ===========================================================================
# Ticket Endpoints
# ===========================================================================

class TestTicketEndpoints:
    def test_list_empty(self, server):
        base, _ = server
        data = _get(f"{base}/api/tickets")
        assert isinstance(data, list)
        assert len(data) == 0

    def test_create_ticket(self, server):
        base, fm = server
        c = fm.clients.add_client("Client1")
        status, resp = _post(f"{base}/api/tickets", {
            "client_id": c.client_id,
            "device_category": "phone",
            "device_brand": "Samsung",
            "device_model": "galaxy_s24",
            "issue_description": "Cracked screen",
        })
        assert status == 201
        assert "ticket_id" in resp
        assert resp["ticket_id"].startswith("TK-")

    def test_create_ticket_missing_fields(self, server):
        base, _ = server
        status, resp = _post(f"{base}/api/tickets", {"client_id": "x"})
        assert status == 400

    def test_get_ticket(self, server):
        base, fm = server
        c = fm.clients.add_client("C")
        t = fm.create_ticket(
            c.client_id, DeviceCategory.PHONE,
            "Samsung", "galaxy_s24", "Crack",
        )
        data = _get(f"{base}/api/tickets/{t.ticket_id}")
        assert data["ticket_id"] == t.ticket_id
        assert data["device_brand"] == "Samsung"

    def test_update_status(self, server):
        base, fm = server
        c = fm.clients.add_client("C")
        t = fm.create_ticket(
            c.client_id, DeviceCategory.PHONE,
            "Samsung", "galaxy_s24", "Crack",
        )
        status, resp = _put(f"{base}/api/tickets/{t.ticket_id}/status", {
            "status": "in_progress",
        })
        assert status == 200
        assert fm.get_ticket(t.ticket_id).status == RepairStatus.IN_PROGRESS

    def test_cancel_ticket(self, server):
        base, fm = server
        c = fm.clients.add_client("C")
        t = fm.create_ticket(
            c.client_id, DeviceCategory.TABLET,
            "Apple", "ipad", "Issue",
        )
        status, resp = _post(f"{base}/api/tickets/{t.ticket_id}/cancel")
        assert status == 200
        assert fm.get_ticket(t.ticket_id).status == RepairStatus.CANCELLED

    def test_deliver_ticket(self, server):
        base, fm = server
        c = fm.clients.add_client("C")
        t = fm.create_ticket(
            c.client_id, DeviceCategory.PHONE,
            "Samsung", "galaxy_s24", "Crack",
        )
        status, resp = _post(f"{base}/api/tickets/{t.ticket_id}/deliver")
        assert status == 200
        assert fm.get_ticket(t.ticket_id).status == RepairStatus.DELIVERED

    def test_add_note(self, server):
        base, fm = server
        c = fm.clients.add_client("C")
        t = fm.create_ticket(
            c.client_id, DeviceCategory.PHONE,
            "Samsung", "galaxy_s24", "Crack",
        )
        status, resp = _post(f"{base}/api/tickets/{t.ticket_id}/note", {
            "note": "Checked screen damage",
        })
        assert status == 200
        assert len(fm.get_ticket(t.ticket_id).notes) == 1

    def test_assign_part(self, server):
        base, fm = server
        part = fm.inventory.add_part(
            PartType.SCREEN_LCD, "LCD", ["model"], qty=5,
        )
        c = fm.clients.add_client("C")
        t = fm.create_ticket(
            c.client_id, DeviceCategory.PHONE,
            "Samsung", "model", "Crack",
        )
        status, resp = _post(f"{base}/api/tickets/{t.ticket_id}/part", {
            "part_id": part.part_id,
        })
        assert status == 200
        assert part.part_id in fm.get_ticket(t.ticket_id).parts_used
        assert part.quantity == 4

    def test_filter_by_status(self, server):
        base, fm = server
        c = fm.clients.add_client("C")
        t1 = fm.create_ticket(c.client_id, DeviceCategory.PHONE, "A", "m1", "i")
        t2 = fm.create_ticket(c.client_id, DeviceCategory.PHONE, "A", "m2", "i")
        fm.update_status(t1.ticket_id, RepairStatus.READY)
        data = _get(f"{base}/api/tickets?status=ready")
        assert len(data) == 1
        assert data[0]["ticket_id"] == t1.ticket_id

    def test_filter_by_category(self, server):
        base, fm = server
        c = fm.clients.add_client("C")
        fm.create_ticket(c.client_id, DeviceCategory.PHONE, "A", "m1", "i")
        fm.create_ticket(c.client_id, DeviceCategory.TABLET, "B", "m2", "i")
        data = _get(f"{base}/api/tickets?category=tablet")
        assert len(data) == 1
        assert data[0]["device_category"] == "tablet"


# ===========================================================================
# Diagnostic Endpoints
# ===========================================================================

class TestDiagnosticEndpoints:
    def test_get_diagnostic(self, server):
        base, fm = server
        c = fm.clients.add_client("C")
        t = fm.create_ticket(
            c.client_id, DeviceCategory.PHONE,
            "Samsung", "galaxy_s24", "Crack",
        )
        data = _get(f"{base}/api/tickets/{t.ticket_id}/diagnostic")
        assert "summary" in data
        assert "steps" in data
        assert len(data["steps"]) == 9

    def test_start_diagnostic(self, server):
        base, fm = server
        c = fm.clients.add_client("C")
        t = fm.create_ticket(
            c.client_id, DeviceCategory.PHONE,
            "Samsung", "galaxy_s24", "Crack",
        )
        status, resp = _post(f"{base}/api/tickets/{t.ticket_id}/diagnostic/start")
        assert status == 200
        assert fm.get_ticket(t.ticket_id).status == RepairStatus.DIAGNOSED

    def test_advance_diagnostic(self, server):
        base, fm = server
        c = fm.clients.add_client("C")
        t = fm.create_ticket(
            c.client_id, DeviceCategory.PHONE,
            "Samsung", "galaxy_s24", "Crack",
        )
        fm.start_diagnostic(t.ticket_id)
        status, resp = _post(f"{base}/api/tickets/{t.ticket_id}/diagnostic/next", {
            "passed": True, "notes": "All OK",
        })
        assert status == 200
        assert resp["status"] == "passed"

    def test_advance_diagnostic_fail(self, server):
        base, fm = server
        c = fm.clients.add_client("C")
        t = fm.create_ticket(
            c.client_id, DeviceCategory.PHONE,
            "Samsung", "galaxy_s24", "Crack",
        )
        fm.start_diagnostic(t.ticket_id)
        status, resp = _post(f"{base}/api/tickets/{t.ticket_id}/diagnostic/next", {
            "passed": False, "notes": "Failed step",
        })
        assert resp["status"] == "failed"
        assert fm.get_ticket(t.ticket_id).status == RepairStatus.IN_PROGRESS

    def test_advance_no_workflow(self, server):
        base, _ = server
        status, resp = _post(f"{base}/api/tickets/TK-FAKE/diagnostic/next", {
            "passed": True,
        })
        assert status == 400


# ===========================================================================
# Inventory Endpoints
# ===========================================================================

class TestInventoryEndpoints:
    def test_list_empty(self, server):
        base, _ = server
        data = _get(f"{base}/api/parts")
        assert isinstance(data, list)

    def test_add_part(self, server):
        base, _ = server
        status, resp = _post(f"{base}/api/parts", {
            "part_type": "screen_oled",
            "name": "Test OLED",
            "compatible_devices": ["galaxy_s24"],
            "quantity": 10,
            "unit_cost": 80.0,
        })
        assert status == 201
        assert "part_id" in resp

    def test_add_part_missing_fields(self, server):
        base, _ = server
        status, resp = _post(f"{base}/api/parts", {"name": "LCD"})
        assert status == 400

    def test_get_part(self, server):
        base, fm = server
        p = fm.inventory.add_part(PartType.SPEAKER, "Test", ["m"], qty=5)
        data = _get(f"{base}/api/parts/{p.part_id}")
        assert data["name"] == "Test"
        assert data["quantity"] == 5

    def test_delete_part(self, server):
        base, fm = server
        p = fm.inventory.add_part(PartType.SPEAKER, "Delete", ["m"])
        status, resp = _delete(f"{base}/api/parts/{p.part_id}")
        assert status == 200
        assert fm.inventory.get_part(p.part_id) is None

    def test_low_stock(self, server):
        base, fm = server
        fm.inventory.add_part(PartType.SPEAKER, "Low", ["m"], qty=2, min_stock=5)
        fm.inventory.add_part(PartType.MICROPHONE, "OK", ["m"], qty=20, min_stock=5)
        data = _get(f"{base}/api/parts/low-stock")
        assert len(data) == 1
        assert data[0]["name"] == "Low"

    def test_stock_summary(self, server):
        base, fm = server
        fm.inventory.add_part(PartType.SCREEN_LCD, "L1", ["a"], qty=5)
        fm.inventory.add_part(PartType.SCREEN_LCD, "L2", ["b"], qty=3)
        data = _get(f"{base}/api/parts/summary")
        assert data["summary"]["screen_lcd"] == 8

    def test_filter_by_device(self, server):
        base, fm = server
        fm.inventory.add_part(PartType.SCREEN_OLED, "OLED", ["galaxy_s24"], qty=5)
        fm.inventory.add_part(PartType.BATTERY_LIPO, "Batt", ["galaxy_s24"], qty=5)
        fm.inventory.add_part(PartType.SCREEN_LCD, "LCD", ["iphone_15"], qty=5)
        data = _get(f"{base}/api/parts?device=galaxy_s24")
        assert len(data) == 2

    def test_seed_parts(self, server):
        base, fm = server
        status, resp = _post(f"{base}/api/parts/seed")
        assert status == 200
        assert len(fm.inventory.parts) == 14


# ===========================================================================
# Dashboard & Report Endpoints
# ===========================================================================

class TestDashboardEndpoints:
    def test_dashboard(self, server):
        base, fm = server
        c = fm.clients.add_client("C")
        fm.create_ticket(c.client_id, DeviceCategory.PHONE, "A", "m1", "i")
        data = _get(f"{base}/api/dashboard")
        assert "open_tickets" in data
        assert "by_status" in data
        assert "revenue" in data

    def test_revenue(self, server):
        base, fm = server
        c = fm.clients.add_client("C")
        t = fm.create_ticket(c.client_id, DeviceCategory.PHONE, "A", "m1", "i")
        t.final_cost = 100.0
        fm.update_status(t.ticket_id, RepairStatus.DELIVERED)
        data = _get(f"{base}/api/revenue")
        assert data["total_revenue"] == 100.0
        assert data["total_repairs"] == 1

    def test_report(self, server):
        base, _ = server
        data = _get(f"{base}/api/report")
        assert "exported_at" in data
        assert "open_tickets" in data


# ===========================================================================
# 404 Handling
# ===========================================================================

class Test404:
    def test_unknown_endpoint(self, server):
        base, _ = server
        try:
            urllib.request.urlopen(f"{base}/api/unknown")
            assert False, "Should have raised"
        except urllib.error.HTTPError as e:
            assert e.code == 404


# ===========================================================================
# Full Workflow via API
# ===========================================================================

class TestAPIWorkflow:
    def test_end_to_end(self, server):
        """Full workflow: client → ticket → diagnose → part → deliver via API."""
        base, _ = server

        # 1. Create client
        _, c_resp = _post(f"{base}/api/clients", {
            "name": "API Test Client", "phone": "+12345",
        })
        cid = c_resp["client_id"]

        # 2. Seed parts
        _post(f"{base}/api/parts/seed")

        # 3. Create ticket
        _, t_resp = _post(f"{base}/api/tickets", {
            "client_id": cid,
            "device_category": "phone",
            "device_brand": "Samsung",
            "device_model": "galaxy_s24",
            "issue_description": "Cracked screen",
            "technician": "Tech-A",
        })
        tid = t_resp["ticket_id"]

        # 4. Start diagnostic
        _post(f"{base}/api/tickets/{tid}/diagnostic/start")

        # 5. Run through all 9 diagnostic steps
        for i in range(9):
            _, d_resp = _post(f"{base}/api/tickets/{tid}/diagnostic/next", {
                "passed": True, "notes": f"Step {i} OK",
            })
            assert d_resp["status"] == "passed"

        # 6. Check diagnostic is complete
        diag = _get(f"{base}/api/tickets/{tid}/diagnostic")
        assert diag["summary"]["complete"] is True

        # 7. Assign a part
        parts = _get(f"{base}/api/parts?device=galaxy_s24&type=screen_oled")
        _, p_resp = _post(f"{base}/api/parts", {
            "part_type": "screen_oled",
            "name": "Direct Part",
            "compatible_devices": ["galaxy_s24"],
            "quantity": 5,
            "unit_cost": 85.0,
        })
        _post(f"{base}/api/tickets/{tid}/part", {"part_id": p_resp["part_id"]})

        # 8. Add note
        _post(f"{base}/api/tickets/{tid}/note", {"note": "Screen replaced"})

        # 9. Update cost and deliver
        _put(f"{base}/api/tickets/{tid}/status", {"status": "in_progress"})
        _put(f"{base}/api/tickets/{tid}/status", {"status": "ready"})
        _post(f"{base}/api/tickets/{tid}/deliver")

        # 10. Verify final state
        ticket = _get(f"{base}/api/tickets/{tid}")
        assert ticket["status"] == "delivered"
        assert ticket["delivered_at"] != ""

        # 11. Dashboard check
        dash = _get(f"{base}/api/dashboard")
        assert dash["revenue"]["total_repairs"] == 1

        # 12. Client shows repair
        client = _get(f"{base}/api/clients/{cid}")
        assert client["total_repairs"] == 1
