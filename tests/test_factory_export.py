"""
Unit tests for AuraTool-Suite Workshop & Factory Export Module.
Tests CSV and PDF export for clients, tickets, inventory, revenue,
dashboard, and per-ticket invoices.
"""

import csv
import os
import tempfile
import shutil
import pytest

from modules.factory_export import (
    export_clients_csv, export_tickets_csv, export_inventory_csv,
    export_revenue_csv, export_dashboard_csv, export_dashboard_pdf,
    export_tickets_pdf, export_inventory_pdf, export_ticket_invoice_pdf,
    export_all,
)
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
    fm = FactoryManager(tmp_dir)
    # Seed inventory
    fm.inventory.add_part(PartType.SCREEN_OLED, "OLED Screen",
                          ["galaxy_s24"], qty=10, cost=80.0, supplier="Test")
    fm.inventory.add_part(PartType.BATTERY_LIPO, "Battery",
                          ["galaxy_s24"], qty=5, cost=20.0, supplier="Test")
    fm.inventory.add_part(PartType.SCREEN_LCD, "LCD Screen",
                          ["iphone_15"], qty=2, cost=60.0, supplier="Test")

    # Register clients
    c1 = fm.clients.add_client("Ahmed Ali", "+968123", "ahmed@test.com")
    c2 = fm.clients.add_client("Sara Hassan", "+968456", "sara@test.com")

    # Create tickets
    t1 = fm.create_ticket(c1.client_id, DeviceCategory.PHONE,
                          "Samsung", "galaxy_s24", "Cracked screen",
                          serial="SN-001", priority=1, technician="Tech-A")
    fm.start_diagnostic(t1.ticket_id)
    for _ in range(9):
        fm.advance_diagnostic(t1.ticket_id, True, "OK")
    # Assign a part
    part = fm.inventory.get_part(list(fm.inventory.parts.keys())[0])
    if part:
        fm.add_part_to_ticket(t1.ticket_id, part.part_id)
    t1.final_cost = 95.0
    fm.update_status(t1.ticket_id, RepairStatus.IN_PROGRESS)
    fm.update_status(t1.ticket_id, RepairStatus.DELIVERED)

    t2 = fm.create_ticket(c2.client_id, DeviceCategory.TABLET,
                          "Apple", "ipad_pro_m2", "Battery issue",
                          serial="SN-002", priority=2, technician="Tech-B")
    fm.start_diagnostic(t2.ticket_id)

    t3 = fm.create_ticket(c1.client_id, DeviceCategory.SMARTWATCH,
                          "Samsung", "galaxy_watch_6", "Touch dead")
    fm.cancel_ticket(t3.ticket_id)

    return fm


def _read_csv(filepath: str) -> list[dict]:
    """Read a CSV file and return list of row dicts."""
    with open(filepath, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ===========================================================================
# CSV Export Tests
# ===========================================================================

class TestClientsCSV:
    def test_creates_file(self, factory, tmp_dir):
        path = os.path.join(tmp_dir, "clients.csv")
        result = export_clients_csv(factory, path)
        assert os.path.exists(result)

    def test_has_header(self, factory, tmp_dir):
        path = os.path.join(tmp_dir, "clients.csv")
        export_clients_csv(factory, path)
        with open(path) as f:
            header = f.readline().strip()
        assert "Client ID" in header
        assert "Name" in header

    def test_row_count(self, factory, tmp_dir):
        path = os.path.join(tmp_dir, "clients.csv")
        export_clients_csv(factory, path)
        rows = _read_csv(path)
        assert len(rows) == 2

    def test_client_data(self, factory, tmp_dir):
        path = os.path.join(tmp_dir, "clients.csv")
        export_clients_csv(factory, path)
        rows = _read_csv(path)
        names = {r["Name"] for r in rows}
        assert "Ahmed Ali" in names
        assert "Sara Hassan" in names

    def test_has_repairs_column(self, factory, tmp_dir):
        path = os.path.join(tmp_dir, "clients.csv")
        export_clients_csv(factory, path)
        rows = _read_csv(path)
        ahmed = [r for r in rows if r["Name"] == "Ahmed Ali"][0]
        assert int(ahmed["Total Repairs"]) >= 1


class TestTicketsCSV:
    def test_creates_file(self, factory, tmp_dir):
        path = os.path.join(tmp_dir, "tickets.csv")
        export_tickets_csv(factory, path)
        assert os.path.exists(path)

    def test_all_tickets(self, factory, tmp_dir):
        path = os.path.join(tmp_dir, "tickets.csv")
        export_tickets_csv(factory, path)
        rows = _read_csv(path)
        assert len(rows) == 3

    def test_filter_by_status(self, factory, tmp_dir):
        path = os.path.join(tmp_dir, "tickets_delivered.csv")
        export_tickets_csv(factory, path, status=RepairStatus.DELIVERED)
        rows = _read_csv(path)
        assert len(rows) == 1
        assert rows[0]["Status"] == "delivered"

    def test_filter_by_category(self, factory, tmp_dir):
        path = os.path.join(tmp_dir, "tickets_phone.csv")
        export_tickets_csv(factory, path, category=DeviceCategory.PHONE)
        rows = _read_csv(path)
        assert len(rows) == 1
        assert rows[0]["Category"] == "phone"

    def test_filter_combined(self, factory, tmp_dir):
        path = os.path.join(tmp_dir, "tickets_combined.csv")
        export_tickets_csv(factory, path, status=RepairStatus.CANCELLED,
                           category=DeviceCategory.SMARTWATCH)
        rows = _read_csv(path)
        assert len(rows) == 1
        assert rows[0]["Category"] == "smartwatch"
        assert rows[0]["Status"] == "cancelled"

    def test_has_columns(self, factory, tmp_dir):
        path = os.path.join(tmp_dir, "tickets.csv")
        export_tickets_csv(factory, path)
        rows = _read_csv(path)
        expected_cols = {"Ticket ID", "Brand", "Model", "Status", "Priority"}
        assert expected_cols.issubset(set(rows[0].keys()))


class TestInventoryCSV:
    def test_creates_file(self, factory, tmp_dir):
        path = os.path.join(tmp_dir, "inventory.csv")
        export_inventory_csv(factory, path)
        assert os.path.exists(path)

    def test_row_count(self, factory, tmp_dir):
        path = os.path.join(tmp_dir, "inventory.csv")
        export_inventory_csv(factory, path)
        rows = _read_csv(path)
        assert len(rows) == 3

    def test_has_stock_value(self, factory, tmp_dir):
        path = os.path.join(tmp_dir, "inventory.csv")
        export_inventory_csv(factory, path)
        rows = _read_csv(path)
        for row in rows:
            assert "Stock Value" in row
            assert float(row["Stock Value"]) >= 0

    def test_has_low_stock_flag(self, factory, tmp_dir):
        path = os.path.join(tmp_dir, "inventory.csv")
        export_inventory_csv(factory, path)
        rows = _read_csv(path)
        low = [r for r in rows if r["Low Stock"] == "True"]
        # Battery qty=5, min=5 and LCD qty=2, min=5 are both low stock
        assert len(low) == 2


class TestRevenueCSV:
    def test_creates_file(self, factory, tmp_dir):
        path = os.path.join(tmp_dir, "revenue.csv")
        export_revenue_csv(factory, path)
        assert os.path.exists(path)

    def test_has_revenue_data(self, factory, tmp_dir):
        path = os.path.join(tmp_dir, "revenue.csv")
        export_revenue_csv(factory, path)
        with open(path) as f:
            content = f.read()
        assert "Total Revenue" in content
        assert "Samsung" in content


class TestDashboardCSV:
    def test_creates_file(self, factory, tmp_dir):
        path = os.path.join(tmp_dir, "dashboard.csv")
        export_dashboard_csv(factory, path)
        assert os.path.exists(path)

    def test_has_metrics(self, factory, tmp_dir):
        path = os.path.join(tmp_dir, "dashboard.csv")
        export_dashboard_csv(factory, path)
        with open(path) as f:
            content = f.read()
        assert "Open Tickets" in content
        assert "Total Clients" in content
        assert "Inventory Value" in content


# ===========================================================================
# PDF Export Tests
# ===========================================================================

class TestDashboardPDF:
    def test_creates_file(self, factory, tmp_dir):
        path = os.path.join(tmp_dir, "dashboard.pdf")
        export_dashboard_pdf(factory, path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0

    def test_is_valid_pdf(self, factory, tmp_dir):
        path = os.path.join(tmp_dir, "dashboard.pdf")
        export_dashboard_pdf(factory, path)
        with open(path, "rb") as f:
            header = f.read(5)
        assert header == b"%PDF-"

    def test_contains_text(self, factory, tmp_dir):
        path = os.path.join(tmp_dir, "dashboard.pdf")
        export_dashboard_pdf(factory, path)
        assert os.path.getsize(path) > 500  # non-trivial content


class TestTicketsPDF:
    def test_creates_file(self, factory, tmp_dir):
        path = os.path.join(tmp_dir, "tickets.pdf")
        export_tickets_pdf(factory, path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0

    def test_is_valid_pdf(self, factory, tmp_dir):
        path = os.path.join(tmp_dir, "tickets.pdf")
        export_tickets_pdf(factory, path)
        with open(path, "rb") as f:
            assert f.read(5) == b"%PDF-"

    def test_filter_by_category(self, factory, tmp_dir):
        path = os.path.join(tmp_dir, "tickets_phone.pdf")
        export_tickets_pdf(factory, path, category=DeviceCategory.PHONE)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0


class TestInventoryPDF:
    def test_creates_file(self, factory, tmp_dir):
        path = os.path.join(tmp_dir, "inventory.pdf")
        export_inventory_pdf(factory, path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0

    def test_is_valid_pdf(self, factory, tmp_dir):
        path = os.path.join(tmp_dir, "inventory.pdf")
        export_inventory_pdf(factory, path)
        with open(path, "rb") as f:
            assert f.read(5) == b"%PDF-"


class TestInvoicePDF:
    def test_creates_file(self, factory, tmp_dir):
        tid = list(factory.tickets.keys())[0]
        path = os.path.join(tmp_dir, "invoice.pdf")
        export_ticket_invoice_pdf(factory, tid, path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0

    def test_is_valid_pdf(self, factory, tmp_dir):
        tid = list(factory.tickets.keys())[0]
        path = os.path.join(tmp_dir, "invoice.pdf")
        export_ticket_invoice_pdf(factory, tid, path)
        with open(path, "rb") as f:
            assert f.read(5) == b"%PDF-"

    def test_contains_invoice_header(self, factory, tmp_dir):
        tid = list(factory.tickets.keys())[0]
        path = os.path.join(tmp_dir, "invoice.pdf")
        export_ticket_invoice_pdf(factory, tid, path)
        assert os.path.getsize(path) > 500  # non-trivial content

    def test_invalid_ticket_raises(self, factory, tmp_dir):
        path = os.path.join(tmp_dir, "bad.pdf")
        with pytest.raises(ValueError, match="not found"):
            export_ticket_invoice_pdf(factory, "TK-NONEXISTENT", path)

    def test_delivered_ticket_has_cost(self, factory, tmp_dir):
        delivered = [t for t in factory.tickets.values()
                     if t.status == RepairStatus.DELIVERED]
        assert len(delivered) == 1
        path = os.path.join(tmp_dir, "invoice_delivered.pdf")
        export_ticket_invoice_pdf(factory, delivered[0].ticket_id, path)
        assert os.path.exists(path)
        assert os.path.getsize(path) > 500


# ===========================================================================
# Export All
# ===========================================================================

class TestExportAll:
    def test_creates_all_files(self, factory, tmp_dir):
        out = os.path.join(tmp_dir, "exports")
        files = export_all(factory, out)
        assert len(files) == 8
        for ftype, fpath in files.items():
            assert os.path.exists(fpath), f"{ftype} not found at {fpath}"

    def test_csv_files_are_valid(self, factory, tmp_dir):
        out = os.path.join(tmp_dir, "exports")
        files = export_all(factory, out)
        csv_files = {k: v for k, v in files.items() if k.endswith("_csv")}
        assert len(csv_files) == 5
        for ftype, fpath in csv_files.items():
            rows = _read_csv(fpath)
            assert len(rows) >= 1, f"{ftype} is empty"

    def test_pdf_files_are_valid(self, factory, tmp_dir):
        out = os.path.join(tmp_dir, "exports")
        files = export_all(factory, out)
        pdf_files = {k: v for k, v in files.items() if k.endswith("_pdf")}
        assert len(pdf_files) == 3
        for ftype, fpath in pdf_files.items():
            with open(fpath, "rb") as f:
                assert f.read(5) == b"%PDF-", f"{ftype} is not valid PDF"
