"""
AuraTool-Suite — Workshop & Factory Export Module
==================================================
Generates CSV and PDF reports/invoices from the factory management system.

Reports:
  - Client list
  - Ticket list (with filters)
  - Inventory stock report
  - Revenue report
  - Full dashboard summary
  - Per-ticket invoice
"""

from __future__ import annotations

import csv
import io
import os
from datetime import datetime
from typing import Optional

from fpdf import FPDF

from auratool_factory import (
    FactoryManager, RepairStatus, DeviceCategory, PartType,
)


# ---------------------------------------------------------------------------
# PDF Styling
# ---------------------------------------------------------------------------

def _safe_text(text: str) -> str:
    """Replace non-latin-1 characters for core font compatibility."""
    text = text.replace("\u2014", "-").replace("\u2013", "-")
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    return text


class AuraPDF(FPDF):
    """Custom PDF with header/footer branding.

    Compatible with fpdf 1.7.2 — uses positional args only (no new_x/new_y).
    """

    def __init__(self, title: str = "AuraTool-Suite Report"):
        super().__init__()
        self.report_title = title
        self.set_auto_page_break(auto=True, margin=20)

    def cell(self, *args, **kwargs):
        # Auto-sanitize text arg (positional index 2 or keyword 'txt'/'text')
        if len(args) > 2 and isinstance(args[2], str):
            args = list(args)
            args[2] = _safe_text(args[2])
            args = tuple(args)
        elif 'txt' in kwargs and isinstance(kwargs['txt'], str):
            kwargs['txt'] = _safe_text(kwargs['txt'])
        elif 'text' in kwargs and isinstance(kwargs['text'], str):
            kwargs['text'] = _safe_text(kwargs['text'])
        # Strip fpdf2-only kwargs for fpdf 1.7.2 compatibility
        kwargs.pop('new_x', None)
        kwargs.pop('new_y', None)
        return super().cell(*args, **kwargs)

    def multi_cell(self, *args, **kwargs):
        if len(args) > 2 and isinstance(args[2], str):
            args = list(args)
            args[2] = _safe_text(args[2])
            args = tuple(args)
        elif 'txt' in kwargs and isinstance(kwargs['txt'], str):
            kwargs['txt'] = _safe_text(kwargs['txt'])
        # Strip fpdf2-only kwargs for fpdf 1.7.2 compatibility
        kwargs.pop('new_x', None)
        kwargs.pop('new_y', None)
        kwargs.pop('dry_run', None)
        kwargs.pop('output', None)
        kwargs.pop('max_line_height', None)
        return super().multi_cell(*args, **kwargs)

    def cell_ln(self, w, h, txt, border=0, align="", fill=False):
        """Helper: cell with automatic line break after (ln=1)."""
        self.cell(w, h, txt, border, ln=1, align=align, fill=fill)

    def header(self):
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 8, "AuraTool-Suite", ln=1)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 5, _safe_text(self.report_title), ln=1)
        self.set_text_color(0, 0, 0)
        self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}  |  Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                  align="C")

    def section_title(self, title: str):
        self.set_font("Helvetica", "B", 11)
        self.set_fill_color(45, 55, 72)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, f"  {_safe_text(title)}", fill=True, ln=1)
        self.set_text_color(0, 0, 0)
        self.ln(3)

    def table_header(self, cols: list[str], widths: list[int]):
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(230, 230, 230)
        for col, w in zip(cols, widths):
            self.cell(w, 7, _safe_text(col), border=1, fill=True, align="C")
        self.ln()

    def table_row(self, values: list[str], widths: list[int]):
        self.set_font("Helvetica", "", 8)
        safe_vals = [_safe_text(str(v)) for v in values]
        # Calculate row height based on text width (approximate line count)
        max_h = 7
        for val, w in zip(safe_vals, widths):
            text_w = self.get_string_width(val)
            lines_needed = max(1, int(text_w / w) + 1) if w > 0 else 1
            h = lines_needed * 5
            if h > max_h:
                max_h = h
        # Check page break
        if self.get_y() + max_h > 270:
            self.add_page()
        y_start = self.get_y()
        x_start = self.get_x()
        for val, w in zip(safe_vals, widths):
            self.set_xy(x_start, y_start)
            self.multi_cell(w, 5, val, border=1, align="L")
            x_start += w
        self.set_y(y_start + max_h)


# ---------------------------------------------------------------------------
# CSV Export
# ---------------------------------------------------------------------------

def export_clients_csv(fm: FactoryManager, filepath: str) -> str:
    """Export client list to CSV. Returns filepath."""
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Client ID", "Name", "Phone", "Email", "Address",
                         "Total Repairs", "Created At"])
        for c in fm.clients.clients.values():
            writer.writerow([c.client_id, c.name, c.phone, c.email,
                             c.address, c.total_repairs, c.created_at])
    return filepath


def export_tickets_csv(fm: FactoryManager, filepath: str,
                       status: Optional[RepairStatus] = None,
                       category: Optional[DeviceCategory] = None) -> str:
    """Export tickets to CSV with optional filters."""
    tickets = list(fm.tickets.values())
    if status:
        tickets = [t for t in tickets if t.status == status]
    if category:
        tickets = [t for t in tickets if t.device_category == category]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Ticket ID", "Client ID", "Category", "Brand",
                         "Model", "Serial", "Issue", "Status", "Priority",
                         "Technician", "Est. Cost", "Final Cost",
                         "Parts Used", "Days Open", "Created At"])
        for t in tickets:
            writer.writerow([
                t.ticket_id, t.client_id, t.device_category.value,
                t.device_brand, t.device_model, t.device_serial,
                t.issue_description, t.status.value, t.priority,
                t.technician, t.estimated_cost, t.final_cost,
                ",".join(t.parts_used), t.days_open, t.created_at,
            ])
    return filepath


def export_inventory_csv(fm: FactoryManager, filepath: str) -> str:
    """Export spare parts inventory to CSV."""
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Part ID", "Type", "Name", "Compatible Devices",
                         "Quantity", "Min Stock", "Unit Cost",
                         "Stock Value", "Supplier", "Location",
                         "In Stock", "Low Stock"])
        for p in fm.inventory.parts.values():
            writer.writerow([
                p.part_id, p.part_type.value, p.name,
                ";".join(p.compatible_devices), p.quantity, p.min_stock,
                p.unit_cost, round(p.quantity * p.unit_cost, 2),
                p.supplier, p.location, p.in_stock, p.low_stock,
            ])
    return filepath


def export_revenue_csv(fm: FactoryManager, filepath: str) -> str:
    """Export revenue report to CSV."""
    report = fm.revenue_report()
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Total Repairs", report["total_repairs"]])
        writer.writerow(["Total Revenue", report["total_revenue"]])
        writer.writerow(["Average Cost", report["average_cost"]])
        writer.writerow([])
        writer.writerow(["Brand", "Revenue"])
        for brand, amt in report["by_brand"].items():
            writer.writerow([brand, amt])
    return filepath


def export_dashboard_csv(fm: FactoryManager, filepath: str) -> str:
    """Export full dashboard summary to CSV."""
    dash = fm.dashboard()
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Metric", "Value"])
        writer.writerow(["Open Tickets", dash["open_tickets"]])
        writer.writerow(["Overdue Tickets", dash["overdue"]])
        writer.writerow(["Total Clients", dash["total_clients"]])
        writer.writerow(["Low Stock Parts", dash["low_stock_parts"]])
        writer.writerow(["Inventory Value", dash["inventory_value"]])
        writer.writerow([])
        writer.writerow(["Status", "Count"])
        for s, c in dash["by_status"].items():
            if c:
                writer.writerow([s, c])
        writer.writerow([])
        writer.writerow(["Category", "Count"])
        for cat, c in dash["by_category"].items():
            if c:
                writer.writerow([cat, c])
        writer.writerow([])
        writer.writerow(["Revenue Metric", "Value"])
        rev = dash["revenue"]
        writer.writerow(["Repairs Completed", rev["total_repairs"]])
        writer.writerow(["Total Revenue", rev["total_revenue"]])
        writer.writerow(["Average Cost", rev["average_cost"]])
    return filepath


# ---------------------------------------------------------------------------
# PDF Export
# ---------------------------------------------------------------------------

def _pdf_table(pdf: AuraPDF, headers: list[str], widths: list[int],
               rows: list[list[str]]):
    """Render a table in a PDF."""
    pdf.table_header(headers, widths)
    for row in rows:
        pdf.table_row(row, widths)


def export_dashboard_pdf(fm: FactoryManager, filepath: str) -> str:
    """Export dashboard summary as PDF."""
    dash = fm.dashboard()
    rev = dash["revenue"]

    pdf = AuraPDF("Workshop Dashboard Report")
    pdf.alias_nb_pages()
    pdf.add_page()

    # Summary section
    pdf.section_title("Summary")
    pdf.set_font("Helvetica", "", 10)
    summary_items = [
        f"Open Tickets:       {dash['open_tickets']}",
        f"Overdue (>7 days):  {dash['overdue']}",
        f"Total Clients:      {dash['total_clients']}",
        f"Low-Stock Parts:    {dash['low_stock_parts']}",
        f"Inventory Value:    ${dash['inventory_value']:,.2f}",
    ]
    for item in summary_items:
        pdf.cell(0, 6, item, ln=1)
    pdf.ln(4)

    # Status breakdown
    pdf.section_title("Tickets by Status")
    cols = ["Status", "Count"]
    widths = [80, 40]
    rows = [[s, str(c)] for s, c in dash["by_status"].items() if c]
    _pdf_table(pdf, cols, widths, rows)
    pdf.ln(4)

    # Category breakdown
    pdf.section_title("Tickets by Device Category")
    cols = ["Category", "Count"]
    rows = [[cat, str(c)] for cat, c in dash["by_category"].items() if c]
    _pdf_table(pdf, cols, widths, rows)
    pdf.ln(4)

    # Revenue
    pdf.section_title("Revenue Report")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Repairs Completed: {rev['total_repairs']}", ln=1)
    pdf.cell(0, 6, f"Total Revenue:     ${rev['total_revenue']:,.2f}", ln=1)
    pdf.cell(0, 6, f"Average Cost:      ${rev['average_cost']:,.2f}", ln=1)
    pdf.ln(4)

    if rev["by_brand"]:
        pdf.section_title("Revenue by Brand")
        cols = ["Brand", "Revenue"]
        widths = [80, 50]
        rows = [[b, f"${a:,.2f}"] for b, a in rev["by_brand"].items()]
        _pdf_table(pdf, cols, widths, rows)
        pdf.ln(4)

    # Low stock alerts
    low = fm.inventory.low_stock_items()
    if low:
        pdf.section_title("Low Stock Alerts")
        cols = ["Part Name", "Type", "Qty", "Min"]
        widths = [60, 40, 25, 25]
        rows = [[p.name, p.part_type.value, str(p.quantity), str(p.min_stock)]
                for p in low]
        _pdf_table(pdf, cols, widths, rows)

    pdf.output(filepath)
    return filepath


def export_tickets_pdf(fm: FactoryManager, filepath: str,
                       status: Optional[RepairStatus] = None,
                       category: Optional[DeviceCategory] = None) -> str:
    """Export tickets list as PDF."""
    tickets = list(fm.tickets.values())
    if status:
        tickets = [t for t in tickets if t.status == status]
    if category:
        tickets = [t for t in tickets if t.device_category == category]

    title = "Repair Tickets Report"
    if status:
        title += f" ({status.value})"
    if category:
        title += f" — {category.value}"

    pdf = AuraPDF(title)
    pdf.alias_nb_pages()
    pdf.add_page()

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Total tickets: {len(tickets)}", ln=1)
    pdf.ln(3)

    cols = ["ID", "Brand", "Model", "Issue", "Status", "Prio", "Days"]
    widths = [25, 22, 28, 45, 22, 12, 12]
    rows = [[
        t.ticket_id, t.device_brand, t.device_model,
        t.issue_description[:40], t.status.value,
        str(t.priority), str(t.days_open),
    ] for t in tickets]
    _pdf_table(pdf, cols, widths, rows)

    pdf.output(filepath)
    return filepath


def export_inventory_pdf(fm: FactoryManager, filepath: str) -> str:
    """Export inventory report as PDF."""
    pdf = AuraPDF("Spare Parts Inventory Report")
    pdf.alias_nb_pages()
    pdf.add_page()

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Total parts: {len(fm.inventory.parts)}", ln=1)
    pdf.cell(0, 6, f"Total value: ${fm.inventory.total_value():,.2f}", ln=1)
    pdf.ln(3)

    cols = ["Name", "Type", "Qty", "Min", "Cost", "Value"]
    widths = [50, 35, 15, 15, 20, 25]
    rows = [[
        p.name, p.part_type.value, str(p.quantity), str(p.min_stock),
        f"${p.unit_cost:.2f}", f"${p.quantity * p.unit_cost:.2f}",
    ] for p in fm.inventory.parts.values()]
    _pdf_table(pdf, cols, widths, rows)

    pdf.output(filepath)
    return filepath


def export_ticket_invoice_pdf(fm: FactoryManager, ticket_id: str,
                              filepath: str) -> str:
    """Generate a per-ticket invoice PDF."""
    ticket = fm.get_ticket(ticket_id)
    if ticket is None:
        raise ValueError(f"Ticket {ticket_id} not found")

    client = fm.clients.get_client(ticket.client_id)
    client_name = client.name if client else "Unknown"

    # Calculate parts cost
    parts_cost = 0.0
    parts_detail = []
    for pid in ticket.parts_used:
        part = fm.inventory.get_part(pid)
        if part:
            parts_cost += part.unit_cost
            parts_detail.append((part.name, part.part_type.value, part.unit_cost))

    pdf = AuraPDF(f"Invoice — {ticket.ticket_id}")
    pdf.alias_nb_pages()
    pdf.add_page()

    # Invoice header
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "INVOICE", align="C", ln=1)
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(40, 6, "Invoice No:")
    pdf.cell(0, 6, ticket.ticket_id, ln=1)
    pdf.cell(40, 6, "Date:")
    pdf.cell(0, 6, datetime.now().strftime("%Y-%m-%d"), ln=1)
    pdf.cell(40, 6, "Technician:")
    pdf.cell(0, 6, ticket.technician or "N/A", ln=1)
    pdf.ln(3)

    # Client info
    pdf.section_title("Client Information")
    pdf.cell(40, 6, "Name:")
    pdf.cell(0, 6, client_name, ln=1)
    if client:
        if client.phone:
            pdf.cell(40, 6, "Phone:")
            pdf.cell(0, 6, client.phone, ln=1)
        if client.email:
            pdf.cell(40, 6, "Email:")
            pdf.cell(0, 6, client.email, ln=1)
    pdf.ln(3)

    # Device info
    pdf.section_title("Device Information")
    pdf.cell(40, 6, "Category:")
    pdf.cell(0, 6, ticket.device_category.value, ln=1)
    pdf.cell(40, 6, "Brand:")
    pdf.cell(0, 6, ticket.device_brand, ln=1)
    pdf.cell(40, 6, "Model:")
    pdf.cell(0, 6, ticket.device_model, ln=1)
    if ticket.device_serial:
        pdf.cell(40, 6, "Serial:")
        pdf.cell(0, 6, ticket.device_serial, ln=1)
    pdf.cell(40, 6, "Issue:")
    pdf.cell(0, 6, ticket.issue_description, ln=1)
    pdf.ln(3)

    # Parts used
    if parts_detail:
        pdf.section_title("Parts Used")
        cols = ["Part Name", "Type", "Cost"]
        widths = [70, 50, 30]
        rows = [[n, t, f"${c:.2f}"] for n, t, c in parts_detail]
        _pdf_table(pdf, cols, widths, rows)
        pdf.ln(3)

    # Cost summary
    pdf.section_title("Cost Summary")
    pdf.set_font("Helvetica", "", 10)
    if parts_detail:
        pdf.cell(100, 6, "Parts Cost:")
        pdf.cell(0, 6, f"${parts_cost:.2f}", ln=1)
    if ticket.estimated_cost > 0:
        pdf.cell(100, 6, "Estimated Cost:")
        pdf.cell(0, 6, f"${ticket.estimated_cost:.2f}", ln=1)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(100, 8, "TOTAL:")
    pdf.cell(0, 8, f"${ticket.final_cost:.2f}", ln=1)

    # Status
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(40, 6, "Status:")
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, ticket.status.value.upper(), ln=1)

    pdf.output(filepath)
    return filepath


# ---------------------------------------------------------------------------
# Convenience: export all
# ---------------------------------------------------------------------------

def export_all(fm: FactoryManager, output_dir: str = "exports") -> dict[str, str]:
    """Generate all report files. Returns dict of type -> filepath."""
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    files = {}
    files["clients_csv"] = export_clients_csv(fm, os.path.join(output_dir, f"clients_{ts}.csv"))
    files["tickets_csv"] = export_tickets_csv(fm, os.path.join(output_dir, f"tickets_{ts}.csv"))
    files["inventory_csv"] = export_inventory_csv(fm, os.path.join(output_dir, f"inventory_{ts}.csv"))
    files["revenue_csv"] = export_revenue_csv(fm, os.path.join(output_dir, f"revenue_{ts}.csv"))
    files["dashboard_csv"] = export_dashboard_csv(fm, os.path.join(output_dir, f"dashboard_{ts}.csv"))
    files["dashboard_pdf"] = export_dashboard_pdf(fm, os.path.join(output_dir, f"dashboard_{ts}.pdf"))
    files["tickets_pdf"] = export_tickets_pdf(fm, os.path.join(output_dir, f"tickets_{ts}.pdf"))
    files["inventory_pdf"] = export_inventory_pdf(fm, os.path.join(output_dir, f"inventory_{ts}.pdf"))
    return files
