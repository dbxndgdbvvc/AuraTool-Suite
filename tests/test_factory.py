"""
Unit tests for AuraTool-Suite Workshop & Factory Management System.
Covers: SparePart, InventoryManager, Client, ClientManager,
DiagnosticRecord, DiagnosticWorkflow, RepairTicket, FactoryManager.
"""

import os
import shutil
import tempfile
import pytest

from auratool_factory import (
    DeviceCategory,
    RepairStatus,
    DiagnosticStep,
    PartType,
    SparePart,
    InventoryManager,
    Client,
    ClientManager,
    DiagnosticRecord,
    DiagnosticWorkflow,
    RepairTicket,
    FactoryManager,
    COMMON_PARTS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_dir():
    """Create a temporary directory for test data files."""
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def inventory(tmp_dir):
    return InventoryManager(os.path.join(tmp_dir, "inv.json"))


@pytest.fixture
def clients(tmp_dir):
    return ClientManager(os.path.join(tmp_dir, "cli.json"))


@pytest.fixture
def factory(tmp_dir):
    return FactoryManager(tmp_dir)


@pytest.fixture
def sample_part():
    return SparePart(
        part_id="test001",
        part_type=PartType.SCREEN_OLED,
        name="Test OLED Screen",
        compatible_devices=["galaxy_s24", "iphone_15"],
        quantity=10,
        min_stock=5,
        unit_cost=80.0,
        supplier="TestSupplier",
        location="Shelf-B",
    )


@pytest.fixture
def sample_ticket(tmp_dir):
    return RepairTicket(
        ticket_id="TK-TEST01",
        client_id="client-001",
        device_category=DeviceCategory.PHONE,
        device_brand="Samsung",
        device_model="galaxy_s24",
        device_serial="SN-12345",
        issue_description="Cracked screen",
        status=RepairStatus.RECEIVED,
        priority=1,
        technician="Tech-A",
    )


@pytest.fixture
def sample_workflow():
    return DiagnosticWorkflow.for_ticket("TK-TEST01")


# ===========================================================================
# SparePart Tests
# ===========================================================================

class TestSparePart:
    def test_in_stock(self, sample_part):
        assert sample_part.in_stock is True

    def test_not_in_stock(self, sample_part):
        sample_part.quantity = 0
        assert sample_part.in_stock is False

    def test_low_stock(self, sample_part):
        sample_part.quantity = 3
        assert sample_part.low_stock is True

    def test_not_low_stock(self, sample_part):
        sample_part.quantity = 20
        assert sample_part.low_stock is False

    def test_consume_success(self, sample_part):
        assert sample_part.consume(3) is True
        assert sample_part.quantity == 7

    def test_consume_all(self, sample_part):
        assert sample_part.consume(10) is True
        assert sample_part.quantity == 0

    def test_consume_insufficient(self, sample_part):
        assert sample_part.consume(15) is False
        assert sample_part.quantity == 10

    def test_consume_default_one(self, sample_part):
        assert sample_part.consume() is True
        assert sample_part.quantity == 9

    def test_restock(self, sample_part):
        sample_part.restock(5)
        assert sample_part.quantity == 15

    def test_part_type_property(self, sample_part):
        assert sample_part.part_type == PartType.SCREEN_OLED


# ===========================================================================
# InventoryManager Tests
# ===========================================================================

class TestInventoryManager:
    def test_add_part(self, inventory):
        part = inventory.add_part(
            PartType.BATTERY_LIPO, "Test Battery",
            ["iphone_15"], qty=15, cost=25.0,
        )
        assert part.part_id in inventory.parts
        assert part.name == "Test Battery"
        assert part.quantity == 15

    def test_get_part(self, inventory):
        part = inventory.add_part(PartType.SCREEN_LCD, "LCD", ["model_a"])
        assert inventory.get_part(part.part_id) is not None
        assert inventory.get_part(part.part_id).name == "LCD"

    def test_get_part_not_found(self, inventory):
        assert inventory.get_part("nonexistent") is None

    def test_remove_part(self, inventory):
        part = inventory.add_part(PartType.SPEAKER, "Speaker", ["model_a"])
        assert inventory.remove_part(part.part_id) is True
        assert inventory.get_part(part.part_id) is None

    def test_remove_nonexistent(self, inventory):
        assert inventory.remove_part("nonexistent") is False

    def test_find_for_device(self, inventory):
        inventory.add_part(PartType.SCREEN_OLED, "Screen", ["galaxy_s24"], qty=5)
        inventory.add_part(PartType.BATTERY_LIPO, "Battery", ["galaxy_s24"], qty=5)
        inventory.add_part(PartType.SCREEN_LCD, "iPhone Screen", ["iphone_15"], qty=5)

        results = inventory.find_for_device("galaxy_s24")
        assert len(results) == 2

    def test_find_for_device_with_type(self, inventory):
        inventory.add_part(PartType.SCREEN_OLED, "Screen", ["galaxy_s24"], qty=5)
        inventory.add_part(PartType.BATTERY_LIPO, "Battery", ["galaxy_s24"], qty=5)

        results = inventory.find_for_device("galaxy_s24", PartType.SCREEN_OLED)
        assert len(results) == 1
        assert results[0].part_type == PartType.SCREEN_OLED

    def test_find_for_unknown_device(self, inventory):
        inventory.add_part(PartType.SCREEN_LCD, "LCD", ["model_a"])
        results = inventory.find_for_device("unknown_model")
        assert len(results) == 0

    def test_low_stock_items(self, inventory):
        p1 = inventory.add_part(PartType.SPEAKER, "Speaker", ["a"], qty=2, min_stock=5)
        p2 = inventory.add_part(PartType.MICROPHONE, "Mic", ["b"], qty=20, min_stock=5)
        low = inventory.low_stock_items()
        assert len(low) == 1
        assert low[0].part_id == p1.part_id

    def test_stock_summary(self, inventory):
        inventory.add_part(PartType.SCREEN_LCD, "LCD1", ["a"], qty=5)
        inventory.add_part(PartType.SCREEN_LCD, "LCD2", ["b"], qty=3)
        inventory.add_part(PartType.BATTERY_LIPO, "Batt", ["c"], qty=10)

        summary = inventory.stock_summary()
        assert summary["screen_lcd"] == 8
        assert summary["battery_lipo"] == 10

    def test_total_value(self, inventory):
        inventory.add_part(PartType.SCREEN_LCD, "LCD", ["a"], qty=5, cost=10.0)
        inventory.add_part(PartType.BATTERY_LIPO, "Batt", ["b"], qty=3, cost=20.0)
        assert inventory.total_value() == pytest.approx(110.0)

    def test_save_and_reload(self, tmp_dir):
        path = os.path.join(tmp_dir, "inv_reload.json")
        inv1 = InventoryManager(path)
        inv1.add_part(PartType.SCREEN_LCD, "Test", ["m"], qty=7, cost=30.0)
        inv1.save()

        inv2 = InventoryManager(path)
        assert len(inv2.parts) == 1
        part = list(inv2.parts.values())[0]
        assert part.name == "Test"
        assert part.quantity == 7
        assert part.unit_cost == 30.0


# ===========================================================================
# Client Tests
# ===========================================================================

class TestClient:
    def test_total_repairs(self):
        c = Client(client_id="c1", name="Test", ticket_ids=["t1", "t2", "t3"])
        assert c.total_repairs == 3

    def test_total_repairs_empty(self):
        c = Client(client_id="c1", name="Test")
        assert c.total_repairs == 0

    def test_created_at_auto(self):
        c = Client(client_id="c1", name="Test")
        assert c.created_at != ""


# ===========================================================================
# ClientManager Tests
# ===========================================================================

class TestClientManager:
    def test_add_client(self, clients):
        c = clients.add_client("John Doe", "+1234567890", "john@test.com")
        assert c.client_id in clients.clients
        assert c.name == "John Doe"

    def test_get_client(self, clients):
        c = clients.add_client("Jane Doe")
        assert clients.get_client(c.client_id).name == "Jane Doe"

    def test_get_client_not_found(self, clients):
        assert clients.get_client("nonexistent") is None

    def test_search_by_name(self, clients):
        clients.add_client("Ahmed Ali")
        clients.add_client("Sara Hassan")
        clients.add_client("Omar Test")
        results = clients.search("ahmed")
        assert len(results) == 1
        assert results[0].name == "Ahmed Ali"

    def test_search_by_phone(self, clients):
        clients.add_client("John", "+968123456")
        results = clients.search("+968")
        assert len(results) == 1

    def test_search_by_email(self, clients):
        clients.add_client("Test User", "", "test@domain.com")
        results = clients.search("domain.com")
        assert len(results) == 1

    def test_search_no_results(self, clients):
        clients.add_client("John")
        assert len(clients.search("nonexistent")) == 0

    def test_remove_client(self, clients):
        c = clients.add_client("Remove Me")
        assert clients.remove_client(c.client_id) is True
        assert clients.get_client(c.client_id) is None

    def test_remove_nonexistent(self, clients):
        assert clients.remove_client("nope") is False

    def test_top_clients(self, clients):
        c1 = clients.add_client("A")
        c2 = clients.add_client("B")
        c3 = clients.add_client("C")
        c1.ticket_ids = ["t1", "t2", "t3"]
        c2.ticket_ids = ["t1"]
        c3.ticket_ids = ["t1", "t2"]

        top = clients.top_clients(2)
        assert top[0].client_id == c1.client_id
        assert top[1].client_id == c3.client_id

    def test_top_clients_limit(self, clients):
        for i in range(5):
            clients.add_client(f"Client {i}")
        assert len(clients.top_clients(3)) == 3

    def test_save_and_reload(self, tmp_dir):
        path = os.path.join(tmp_dir, "cli_reload.json")
        cm1 = ClientManager(path)
        cm1.add_client("Persist Test", "+111")
        cm1.save()

        cm2 = ClientManager(path)
        assert len(cm2.clients) == 1
        c = list(cm2.clients.values())[0]
        assert c.name == "Persist Test"
        assert c.phone == "+111"


# ===========================================================================
# DiagnosticRecord Tests
# ===========================================================================

class TestDiagnosticRecord:
    def test_complete_passed(self):
        rec = DiagnosticRecord(
            record_id="r1", ticket_id="t1",
            step=DiagnosticStep.POWER_TEST,
            started_at="2025-01-01T00:00:00",
        )
        rec.complete(True, "All OK", {"voltage": 4.2})
        assert rec.status == "passed"
        assert rec.notes == "All OK"
        assert rec.findings["voltage"] == 4.2
        assert rec.completed_at != ""

    def test_complete_failed(self):
        rec = DiagnosticRecord(
            record_id="r2", ticket_id="t1",
            step=DiagnosticStep.DISPLAY_TEST,
        )
        rec.complete(False, "Dead pixels found")
        assert rec.status == "failed"
        assert rec.notes == "Dead pixels found"

    def test_complete_no_findings(self):
        rec = DiagnosticRecord(
            record_id="r3", ticket_id="t1",
            step=DiagnosticStep.STORAGE_CHECK,
        )
        rec.complete(True)
        assert rec.findings == {}


# ===========================================================================
# DiagnosticWorkflow Tests
# ===========================================================================

class TestDiagnosticWorkflow:
    def test_for_ticket_creates_all_steps(self, sample_workflow):
        assert len(sample_workflow.steps) == len(DiagnosticStep)

    def test_for_ticket_step_order(self, sample_workflow):
        expected = list(DiagnosticStep)
        for i, step in enumerate(expected):
            assert sample_workflow.steps[i].step == step

    def test_current_step_initial(self, sample_workflow):
        assert sample_workflow.current_step is not None
        assert sample_workflow.current_step.step == DiagnosticStep.INTAKE_CHECK

    def test_advance_passed(self, sample_workflow):
        rec = sample_workflow.advance(True, "Passed")
        assert rec is not None
        assert rec.status == "passed"
        assert sample_workflow.current_index == 1

    def test_advance_failed_stays(self, sample_workflow):
        rec = sample_workflow.advance(False, "Failed")
        assert rec.status == "failed"
        assert sample_workflow.current_index == 0  # didn't advance

    def test_advance_failed_then_pass(self, sample_workflow):
        sample_workflow.advance(False, "Failed")
        assert sample_workflow.current_index == 0
        sample_workflow.advance(True, "Retried OK")
        assert sample_workflow.current_index == 1

    def test_advance_past_end(self, sample_workflow):
        for _ in range(len(DiagnosticStep)):
            sample_workflow.advance(True, "OK")
        assert sample_workflow.current_step is None
        rec = sample_workflow.advance(True, "Extra")
        assert rec is None

    def test_is_complete(self, sample_workflow):
        assert sample_workflow.is_complete is False
        for _ in range(len(DiagnosticStep)):
            sample_workflow.advance(True)
        assert sample_workflow.is_complete is True

    def test_progress_pct(self, sample_workflow):
        assert sample_workflow.progress_pct == 0.0
        sample_workflow.advance(True)
        expected = (1 / len(DiagnosticStep)) * 100
        assert sample_workflow.progress_pct == pytest.approx(expected)

    def test_progress_pct_empty(self):
        wf = DiagnosticWorkflow(ticket_id="empty")
        assert wf.progress_pct == 0.0

    def test_failed_steps(self, sample_workflow):
        sample_workflow.advance(True)            # step 0 → passed, index=1
        sample_workflow.advance(False, "Bad")    # step 1 → failed, index=1
        sample_workflow.advance(True)            # step 1 → passed (retry), index=2
        sample_workflow.advance(False, "Also bad")  # step 2 → failed, index=2
        failed = sample_workflow.failed_steps
        # Only step 2 remains failed; step 1 was overwritten to 'passed' on retry
        assert len(failed) == 1
        assert failed[0].step == DiagnosticStep.DISPLAY_TEST

    def test_summary(self, sample_workflow):
        s = sample_workflow.summary()
        assert s["ticket_id"] == "TK-TEST01"
        assert s["total_steps"] == len(DiagnosticStep)
        assert s["completed"] == 0
        assert s["complete"] is False
        assert s["failures"] == 0

    def test_full_diagnostic_pass(self, sample_workflow):
        for i in range(len(DiagnosticStep)):
            result = sample_workflow.advance(True, f"Step {i}")
            assert result.status == "passed"
        assert sample_workflow.is_complete is True
        assert sample_workflow.failed_steps == []


# ===========================================================================
# RepairTicket Tests
# ===========================================================================

class TestRepairTicket:
    def test_initial_status(self, sample_ticket):
        assert sample_ticket.status == RepairStatus.RECEIVED
        assert sample_ticket.is_open is True

    def test_set_status(self, sample_ticket):
        sample_ticket.set_status(RepairStatus.IN_PROGRESS)
        assert sample_ticket.status == RepairStatus.IN_PROGRESS
        assert sample_ticket.updated_at != ""

    def test_set_delivered_records_time(self, sample_ticket):
        sample_ticket.set_status(RepairStatus.DELIVERED)
        assert sample_ticket.delivered_at != ""

    def test_add_note(self, sample_ticket):
        sample_ticket.add_note("Checked screen")
        assert len(sample_ticket.notes) == 1
        assert "Checked screen" in sample_ticket.notes[0]

    def test_add_note_multiple(self, sample_ticket):
        sample_ticket.add_note("First")
        sample_ticket.add_note("Second")
        assert len(sample_ticket.notes) == 2

    def test_add_part(self, sample_ticket):
        sample_ticket.add_part("p1")
        assert "p1" in sample_ticket.parts_used

    def test_add_part_no_duplicate(self, sample_ticket):
        sample_ticket.add_part("p1")
        sample_ticket.add_part("p1")
        assert sample_ticket.parts_used.count("p1") == 1

    def test_remove_part(self, sample_ticket):
        sample_ticket.add_part("p1")
        assert sample_ticket.remove_part("p1") is True
        assert "p1" not in sample_ticket.parts_used

    def test_remove_part_not_found(self, sample_ticket):
        assert sample_ticket.remove_part("nonexistent") is False

    def test_is_open_delivered(self, sample_ticket):
        sample_ticket.set_status(RepairStatus.DELIVERED)
        assert sample_ticket.is_open is False

    def test_is_open_cancelled(self, sample_ticket):
        sample_ticket.set_status(RepairStatus.CANCELLED)
        assert sample_ticket.is_open is False

    def test_is_open_in_progress(self, sample_ticket):
        sample_ticket.set_status(RepairStatus.IN_PROGRESS)
        assert sample_ticket.is_open is True

    def test_days_open(self, sample_ticket):
        assert sample_ticket.days_open >= 0

    def test_to_dict(self, sample_ticket):
        d = sample_ticket.to_dict()
        assert d["device_category"] == "phone"
        assert d["status"] == "received"
        assert "diagnostic" not in d
        assert d["ticket_id"] == "TK-TEST01"

    def test_to_dict_preserves_parts(self, sample_ticket):
        sample_ticket.add_part("p1")
        d = sample_ticket.to_dict()
        assert "p1" in d["parts_used"]


# ===========================================================================
# FactoryManager Tests
# ===========================================================================

class TestFactoryManager:
    def test_create_ticket(self, factory):
        client = factory.clients.add_client("Test Client")
        ticket = factory.create_ticket(
            client.client_id, DeviceCategory.PHONE,
            "Samsung", "galaxy_s24", "Broken screen",
        )
        assert ticket.ticket_id.startswith("TK-")
        assert ticket.ticket_id in factory.tickets
        assert ticket.ticket_id in factory.workflows

    def test_create_ticket_links_client(self, factory):
        client = factory.clients.add_client("Linked Client")
        ticket = factory.create_ticket(
            client.client_id, DeviceCategory.TABLET,
            "Apple", "ipad_pro_m2", "Battery issue",
        )
        assert ticket.ticket_id in client.ticket_ids

    def test_create_ticket_no_client(self, factory):
        ticket = factory.create_ticket(
            "nonexistent", DeviceCategory.SMARTWATCH,
            "Samsung", "galaxy_watch_6", "Touch issue",
        )
        assert ticket.ticket_id in factory.tickets

    def test_get_ticket(self, factory):
        client = factory.clients.add_client("C1")
        t = factory.create_ticket(
            client.client_id, DeviceCategory.PHONE,
            "Samsung", "galaxy_s24", "Crack",
        )
        assert factory.get_ticket(t.ticket_id) is not None

    def test_get_ticket_not_found(self, factory):
        assert factory.get_ticket("NONEXISTENT") is None

    def test_update_status(self, factory):
        client = factory.clients.add_client("C1")
        t = factory.create_ticket(
            client.client_id, DeviceCategory.PHONE,
            "Samsung", "galaxy_s24", "Crack",
        )
        assert factory.update_status(t.ticket_id, RepairStatus.IN_PROGRESS) is True
        assert factory.get_ticket(t.ticket_id).status == RepairStatus.IN_PROGRESS

    def test_update_status_not_found(self, factory):
        assert factory.update_status("NOPE", RepairStatus.READY) is False

    def test_cancel_ticket(self, factory):
        client = factory.clients.add_client("C1")
        t = factory.create_ticket(
            client.client_id, DeviceCategory.PHONE,
            "Samsung", "galaxy_s24", "Crack",
        )
        assert factory.cancel_ticket(t.ticket_id) is True
        assert factory.get_ticket(t.ticket_id).status == RepairStatus.CANCELLED

    def test_add_part_to_ticket(self, factory):
        client = factory.clients.add_client("C1")
        part = factory.inventory.add_part(
            PartType.SCREEN_OLED, "Screen", ["galaxy_s24"], qty=5,
        )
        t = factory.create_ticket(
            client.client_id, DeviceCategory.PHONE,
            "Samsung", "galaxy_s24", "Crack",
        )
        assert factory.add_part_to_ticket(t.ticket_id, part.part_id) is True
        assert part.part_id in factory.get_ticket(t.ticket_id).parts_used
        assert part.quantity == 4  # consumed one

    def test_add_part_no_stock(self, factory):
        client = factory.clients.add_client("C1")
        part = factory.inventory.add_part(
            PartType.SCREEN_LCD, "LCD", ["model"], qty=0,
        )
        t = factory.create_ticket(
            client.client_id, DeviceCategory.PHONE,
            "Samsung", "model", "Issue",
        )
        assert factory.add_part_to_ticket(t.ticket_id, part.part_id) is False

    def test_add_part_invalid_ticket(self, factory):
        part = factory.inventory.add_part(
            PartType.SCREEN_LCD, "LCD", ["m"], qty=5,
        )
        assert factory.add_part_to_ticket("NOPE", part.part_id) is False

    def test_start_diagnostic(self, factory):
        client = factory.clients.add_client("C1")
        t = factory.create_ticket(
            client.client_id, DeviceCategory.PHONE,
            "Samsung", "galaxy_s24", "Crack",
        )
        wf = factory.start_diagnostic(t.ticket_id)
        assert wf is not None
        assert factory.get_ticket(t.ticket_id).status == RepairStatus.DIAGNOSED

    def test_start_diagnostic_not_found(self, factory):
        assert factory.start_diagnostic("NOPE") is None

    def test_advance_diagnostic_pass(self, factory):
        client = factory.clients.add_client("C1")
        t = factory.create_ticket(
            client.client_id, DeviceCategory.PHONE,
            "Samsung", "galaxy_s24", "Crack",
        )
        factory.start_diagnostic(t.ticket_id)
        rec = factory.advance_diagnostic(t.ticket_id, True, "OK")
        assert rec is not None
        assert rec.status == "passed"

    def test_advance_diagnostic_fail_sets_in_progress(self, factory):
        client = factory.clients.add_client("C1")
        t = factory.create_ticket(
            client.client_id, DeviceCategory.PHONE,
            "Samsung", "galaxy_s24", "Crack",
        )
        factory.start_diagnostic(t.ticket_id)
        factory.advance_diagnostic(t.ticket_id, False, "Failed")
        assert factory.get_ticket(t.ticket_id).status == RepairStatus.IN_PROGRESS

    def test_advance_diagnostic_complete_sets_quality_check(self, factory):
        client = factory.clients.add_client("C1")
        t = factory.create_ticket(
            client.client_id, DeviceCategory.PHONE,
            "Samsung", "galaxy_s24", "Crack",
        )
        factory.start_diagnostic(t.ticket_id)
        for _ in range(len(DiagnosticStep)):
            factory.advance_diagnostic(t.ticket_id, True, "OK")
        assert factory.get_ticket(t.ticket_id).status == RepairStatus.QUALITY_CHECK

    def test_advance_diagnostic_not_found(self, factory):
        assert factory.advance_diagnostic("NOPE", True) is None

    def test_open_tickets(self, factory):
        client = factory.clients.add_client("C1")
        t1 = factory.create_ticket(
            client.client_id, DeviceCategory.PHONE,
            "Samsung", "galaxy_s24", "Issue",
        )
        t2 = factory.create_ticket(
            client.client_id, DeviceCategory.TABLET,
            "Apple", "ipad", "Issue",
        )
        factory.cancel_ticket(t1.ticket_id)
        open_t = factory.open_tickets()
        assert len(open_t) == 1
        assert open_t[0].ticket_id == t2.ticket_id

    def test_tickets_by_status(self, factory):
        client = factory.clients.add_client("C1")
        t1 = factory.create_ticket(
            client.client_id, DeviceCategory.PHONE,
            "Samsung", "galaxy_s24", "Issue",
        )
        t2 = factory.create_ticket(
            client.client_id, DeviceCategory.PHONE,
            "Samsung", "galaxy_s23", "Issue",
        )
        factory.update_status(t1.ticket_id, RepairStatus.READY)
        results = factory.tickets_by_status(RepairStatus.READY)
        assert len(results) == 1
        assert results[0].ticket_id == t1.ticket_id

    def test_tickets_by_category(self, factory):
        client = factory.clients.add_client("C1")
        factory.create_ticket(
            client.client_id, DeviceCategory.PHONE,
            "Samsung", "galaxy_s24", "Issue",
        )
        factory.create_ticket(
            client.client_id, DeviceCategory.TABLET,
            "Apple", "ipad", "Issue",
        )
        factory.create_ticket(
            client.client_id, DeviceCategory.SMART_GLASSES,
            "Xreal", "nreal_air", "Issue",
        )
        phones = factory.tickets_by_category(DeviceCategory.PHONE)
        assert len(phones) == 1
        glasses = factory.tickets_by_category(DeviceCategory.SMART_GLASSES)
        assert len(glasses) == 1

    def test_overdue_tickets(self, factory):
        client = factory.clients.add_client("C1")
        t = factory.create_ticket(
            client.client_id, DeviceCategory.PHONE,
            "Samsung", "galaxy_s24", "Issue",
        )
        # Ticket just created — days_open is 0, so 0 > 0 is False
        assert len(factory.overdue_tickets(0)) == 0
        assert len(factory.overdue_tickets(999)) == 0
        # A ticket with days_open=0 is overdue only with threshold < 0
        # (not practical); test with threshold=-1 to confirm logic
        assert len(factory.overdue_tickets(-1)) == 1

    def test_revenue_report_empty(self, factory):
        report = factory.revenue_report()
        assert report["total_repairs"] == 0
        assert report["total_revenue"] == 0.0

    def test_revenue_report(self, factory):
        client = factory.clients.add_client("C1")
        t1 = factory.create_ticket(
            client.client_id, DeviceCategory.PHONE,
            "Samsung", "galaxy_s24", "Issue",
        )
        t2 = factory.create_ticket(
            client.client_id, DeviceCategory.PHONE,
            "Samsung", "galaxy_s23", "Issue",
        )
        t1.final_cost = 100.0
        t2.final_cost = 50.0
        factory.update_status(t1.ticket_id, RepairStatus.DELIVERED)
        factory.update_status(t2.ticket_id, RepairStatus.DELIVERED)

        report = factory.revenue_report()
        assert report["total_repairs"] == 2
        assert report["total_revenue"] == 150.0
        assert report["average_cost"] == 75.0
        assert report["by_brand"]["Samsung"] == 150.0

    def test_dashboard(self, factory):
        client = factory.clients.add_client("C1")
        factory.create_ticket(
            client.client_id, DeviceCategory.PHONE,
            "Samsung", "galaxy_s24", "Issue",
        )
        factory.inventory.add_part(
            PartType.SCREEN_LCD, "LCD", ["a"], qty=2, cost=10.0, min_stock=5,
        )
        dash = factory.dashboard()
        assert "open_tickets" in dash
        assert "by_status" in dash
        assert "by_category" in dash
        assert dash["total_clients"] == 1
        assert dash["inventory_value"] == 20.0
        assert dash["low_stock_parts"] == 1

    def test_export_report(self, factory):
        path = os.path.join(factory.data_dir, "report.json")
        factory.export_report(path)
        assert os.path.exists(path)

    def test_save_and_reload(self, tmp_dir):
        fm1 = FactoryManager(tmp_dir)
        client = fm1.clients.add_client("Reload Test")
        t = fm1.create_ticket(
            client.client_id, DeviceCategory.PHONE,
            "Samsung", "galaxy_s24", "Crack",
        )
        fm1.save()

        fm2 = FactoryManager(tmp_dir)
        assert len(fm2.tickets) == 1
        assert fm2.tickets[t.ticket_id].device_model == "galaxy_s24"


# ===========================================================================
# Common Parts Catalog Tests
# ===========================================================================

class TestCommonPartsCatalog:
    def test_catalog_not_empty(self):
        assert len(COMMON_PARTS) > 0

    def test_all_have_required_keys(self):
        for part in COMMON_PARTS:
            assert "part_type" in part
            assert "name" in part
            assert "compatible" in part
            assert "cost" in part

    def test_all_have_valid_part_type(self):
        for part in COMMON_PARTS:
            assert isinstance(part["part_type"], PartType)

    def test_all_compatible_lists_non_empty(self):
        for part in COMMON_PARTS:
            assert len(part["compatible"]) > 0

    def test_phone_parts_present(self):
        phone_models = {"galaxy_s24", "iphone_15", "xiaomi_14", "pixel_8"}
        found = False
        for part in COMMON_PARTS:
            if phone_models & set(part["compatible"]):
                found = True
                break
        assert found

    def test_tablet_parts_present(self):
        tablet_models = {"ipad_pro_m2", "tab_s9", "ipad_air_m1"}
        found = False
        for part in COMMON_PARTS:
            if tablet_models & set(part["compatible"]):
                found = True
                break
        assert found

    def test_smartwatch_parts_present(self):
        watch_models = {"apple_watch_9", "galaxy_watch_6"}
        found = False
        for part in COMMON_PARTS:
            if watch_models & set(part["compatible"]):
                found = True
                break
        assert found

    def test_glasses_parts_present(self):
        glasses_models = {"rayneo_air", "nreal_air", "meta_rayban", "xreal_air"}
        found = False
        for part in COMMON_PARTS:
            if glasses_models & set(part["compatible"]):
                found = True
                break
        assert found


# ===========================================================================
# Enum Completeness Tests
# ===========================================================================

class TestEnums:
    def test_device_categories(self):
        expected = {"phone", "tablet", "smartwatch", "smart_glasses"}
        actual = {c.value for c in DeviceCategory}
        assert actual == expected

    def test_repair_statuses(self):
        expected = {"received", "diagnosed", "waiting_parts", "in_progress",
                    "quality_check", "ready", "delivered", "cancelled"}
        actual = {s.value for s in RepairStatus}
        assert actual == expected

    def test_diagnostic_steps(self):
        expected = {"intake_check", "power_test", "display_test",
                    "connectivity_test", "sensor_calibration", "storage_check",
                    "software_diagnostic", "battery_health", "final_inspection"}
        actual = {s.value for s in DiagnosticStep}
        assert actual == expected

    def test_part_types_count(self):
        assert len(PartType) == 19


# ===========================================================================
# Integration: Full Factory Workflow
# ===========================================================================

class TestFactoryWorkflow:
    def test_full_phone_repair_workflow(self, factory):
        """End-to-end: client → ticket → diagnose → part → deliver."""
        # 1. Register client
        client = factory.clients.add_client("Integration Test", "+123")

        # 2. Add parts
        screen = factory.inventory.add_part(
            PartType.SCREEN_OLED, "OLED Screen", ["galaxy_s24"],
            qty=5, cost=80.0,
        )
        battery = factory.inventory.add_part(
            PartType.BATTERY_LIPO, "Battery", ["galaxy_s24"],
            qty=10, cost=20.0,
        )

        # 3. Create ticket
        ticket = factory.create_ticket(
            client.client_id, DeviceCategory.PHONE,
            "Samsung", "galaxy_s24", "Cracked screen + battery drain",
            serial="SM-TEST-001", priority=1, technician="Tech-A",
        )

        # 4. Start and complete diagnostics
        factory.start_diagnostic(ticket.ticket_id)
        for _ in range(len(DiagnosticStep)):
            factory.advance_diagnostic(ticket.ticket_id, True, "OK")

        # 5. Assign parts
        factory.add_part_to_ticket(ticket.ticket_id, screen.part_id)
        factory.add_part_to_ticket(ticket.ticket_id, battery.part_id)

        # 6. Update status and cost
        factory.update_status(ticket.ticket_id, RepairStatus.IN_PROGRESS)
        ticket.final_cost = 120.0
        factory.update_status(ticket.ticket_id, RepairStatus.READY)
        factory.update_status(ticket.ticket_id, RepairStatus.DELIVERED)

        # 7. Verify
        assert factory.get_ticket(ticket.ticket_id).status == RepairStatus.DELIVERED
        assert screen.quantity == 4
        assert battery.quantity == 9
        assert client.ticket_ids == [ticket.ticket_id]
        assert ticket.delivered_at != ""

        # 8. Revenue check
        report = factory.revenue_report()
        assert report["total_repairs"] == 1
        assert report["total_revenue"] == 120.0

    def test_multi_device_repair(self, factory):
        """All 4 device categories in one session."""
        client = factory.clients.add_client("Multi-Device Client")

        categories = [
            (DeviceCategory.PHONE, "Samsung", "galaxy_s24", "Screen crack"),
            (DeviceCategory.TABLET, "Apple", "ipad_pro_m2", "Battery issue"),
            (DeviceCategory.SMARTWATCH, "Samsung", "galaxy_watch_6", "Touch dead"),
            (DeviceCategory.SMART_GLASSES, "Xreal", "nreal_air", "Lens flicker"),
        ]

        tickets = []
        for cat, brand, model, issue in categories:
            t = factory.create_ticket(
                client.client_id, cat, brand, model, issue,
            )
            tickets.append(t)

        assert len(factory.tickets) == 4
        assert len(client.ticket_ids) == 4
        assert len(factory.open_tickets()) == 4

        # Diagnose one from each category
        for t in tickets:
            factory.start_diagnostic(t.ticket_id)
            factory.advance_diagnostic(t.ticket_id, True, "Checked")
            assert factory.get_ticket(t.ticket_id).status == RepairStatus.DIAGNOSED

        # Cancel one
        factory.cancel_ticket(tickets[3].ticket_id)
        assert len(factory.open_tickets()) == 3

        # Dashboard check
        dash = factory.dashboard()
        assert dash["open_tickets"] == 3
        assert dash["by_category"]["phone"] == 1
        assert dash["by_category"]["tablet"] == 1
        assert dash["by_category"]["smartwatch"] == 1
        assert dash["by_category"]["smart_glasses"] == 1  # cancelled still counts in category
        # Verify cancelled not in open
        open_by_cat = [t for t in factory.open_tickets()
                       if t.device_category == DeviceCategory.SMART_GLASSES]
        assert len(open_by_cat) == 0

    def test_diagnostic_failure_blocks_delivery(self, factory):
        """A failed diagnostic prevents quality check completion."""
        client = factory.clients.add_client("Fail Test")
        ticket = factory.create_ticket(
            client.client_id, DeviceCategory.PHONE,
            "Google", "pixel_8", "Bootloop",
        )
        factory.start_diagnostic(ticket.ticket_id)

        # Pass 3 steps
        for _ in range(3):
            factory.advance_diagnostic(ticket.ticket_id, True)

        # Fail on step 4
        factory.advance_diagnostic(ticket.ticket_id, False, "Storage corrupt")

        # Should be IN_PROGRESS, not QUALITY_CHECK
        assert factory.get_ticket(ticket.ticket_id).status == RepairStatus.IN_PROGRESS

        # Retry step 4 — now pass (overwrites failed status to passed)
        factory.advance_diagnostic(ticket.ticket_id, True, "Storage OK after format")
        wf = factory.workflows[ticket.ticket_id]
        # The failed step was retried and overwritten to 'passed'
        assert len(wf.failed_steps) == 0

        # Complete remaining steps
        for _ in range(len(DiagnosticStep) - 4):
            factory.advance_diagnostic(ticket.ticket_id, True)

        assert factory.get_ticket(ticket.ticket_id).status == RepairStatus.QUALITY_CHECK

    def test_inventory_depletes_correctly(self, factory):
        """Consuming parts decrements inventory and blocks at zero."""
        part = factory.inventory.add_part(
            PartType.CHARGING_PORT, "USB-C Port", ["model_a"],
            qty=2, cost=10.0,
        )
        client = factory.clients.add_client("Parts Test")

        t1 = factory.create_ticket(
            client.client_id, DeviceCategory.PHONE,
            "Samsung", "model_a", "Bad port",
        )
        t2 = factory.create_ticket(
            client.client_id, DeviceCategory.PHONE,
            "Samsung", "model_a", "Bad port",
        )
        t3 = factory.create_ticket(
            client.client_id, DeviceCategory.PHONE,
            "Samsung", "model_a", "Bad port",
        )

        assert factory.add_part_to_ticket(t1.ticket_id, part.part_id) is True
        assert part.quantity == 1

        assert factory.add_part_to_ticket(t2.ticket_id, part.part_id) is True
        assert part.quantity == 0

        assert factory.add_part_to_ticket(t3.ticket_id, part.part_id) is False
        assert part.quantity == 0
