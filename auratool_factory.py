"""
AuraTool-Suite — Workshop & Factory Management System
======================================================
Comprehensive management for mobile phones, tablets, smartwatches, and smart glasses.
Covers repair tickets, client tracking, spare parts inventory, and diagnostic workflows.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from pathlib import Path

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DeviceCategory(Enum):
    PHONE = "phone"
    TABLET = "tablet"
    SMARTWATCH = "smartwatch"
    SMART_GLASSES = "smart_glasses"


class RepairStatus(Enum):
    RECEIVED = "received"
    DIAGNOSED = "diagnosed"
    WAITING_PARTS = "waiting_parts"
    IN_PROGRESS = "in_progress"
    QUALITY_CHECK = "quality_check"
    READY = "ready"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class DiagnosticStep(Enum):
    INTAKE_CHECK = "intake_check"
    POWER_TEST = "power_test"
    DISPLAY_TEST = "display_test"
    CONNECTIVITY_TEST = "connectivity_test"
    SENSOR_CALIBRATION = "sensor_calibration"
    STORAGE_CHECK = "storage_check"
    SOFTWARE_DIAGNOSTIC = "software_diagnostic"
    BATTERY_HEALTH = "battery_health"
    FINAL_INSPECTION = "final_inspection"


class PartType(Enum):
    SCREEN_LCD = "screen_lcd"
    SCREEN_OLED = "screen_oled"
    SCREEN_AMOLED = "screen_amoled"
    BATTERY_LIPO = "battery_lipo"
    BATTERY_LION = "battery_lion"
    CHARGING_PORT = "charging_port"
    SPEAKER = "speaker"
    MICROPHONE = "microphone"
    CAMERA_MODULE = "camera_module"
    FLEX_CABLE = "flex_cable"
    MAINBOARD = "mainboard"
    BUTTON_ASSEMBLY = "button_assembly"
    TACTILE_STRIP = "tactile_strip"  # for AR glasses
    LENS_MODULE = "lens_module"       # for smart glasses
    TOUCHSCREEN_DIGITIZER = "touchscreen_digitizer"
    ANTENNA_MODULE = "antenna_module"
    SIM_TRAY = "sim_tray"
    VIBRATION_MOTOR = "vibration_motor"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Spare Parts Inventory
# ---------------------------------------------------------------------------

@dataclass
class SparePart:
    part_id: str
    part_type: PartType
    name: str
    compatible_devices: list[str]  # device model keys
    quantity: int = 0
    min_stock: int = 5
    unit_cost: float = 0.0
    supplier: str = ""
    location: str = ""  # shelf / bin reference

    @property
    def in_stock(self) -> bool:
        return self.quantity > 0

    @property
    def low_stock(self) -> bool:
        return self.quantity <= self.min_stock

    def consume(self, qty: int = 1) -> bool:
        if self.quantity >= qty:
            self.quantity -= qty
            return True
        return False

    def restock(self, qty: int) -> None:
        self.quantity += qty


class InventoryManager:
    """Manages all spare parts for the workshop."""

    def __init__(self, data_file: str = "inventory.json"):
        self.data_file = data_file
        self.parts: dict[str, SparePart] = {}
        self._load()

    # -- persistence --------------------------------------------------------
    def _load(self) -> None:
        if not os.path.exists(self.data_file):
            return
        with open(self.data_file) as f:
            for rec in json.load(f):
                rec["part_type"] = PartType(rec["part_type"])
                self.parts[rec["part_id"]] = SparePart(**rec)

    def _serialize(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        return str(obj)

    def save(self) -> None:
        with open(self.data_file, "w") as f:
            json.dump([asdict(p) for p in self.parts.values()], f, indent=2, default=self._serialize)

    # -- CRUD ---------------------------------------------------------------
    def add_part(self, part_type: PartType, name: str, compatible: list[str],
                 qty: int = 0, cost: float = 0.0, supplier: str = "",
                 location: str = "", min_stock: int = 5) -> SparePart:
        pid = str(uuid.uuid4())[:8]
        part = SparePart(part_id=pid, part_type=part_type, name=name,
                         compatible_devices=compatible, quantity=qty,
                         min_stock=min_stock, unit_cost=cost,
                         supplier=supplier, location=location)
        self.parts[pid] = part
        self.save()
        return part

    def get_part(self, part_id: str) -> Optional[SparePart]:
        return self.parts.get(part_id)

    def remove_part(self, part_id: str) -> bool:
        if part_id in self.parts:
            del self.parts[part_id]
            self.save()
            return True
        return False

    # -- queries ------------------------------------------------------------
    def find_for_device(self, device_model: str, part_type: Optional[PartType] = None) -> list[SparePart]:
        results = []
        for p in self.parts.values():
            if device_model in p.compatible_devices:
                if part_type is None or p.part_type == part_type:
                    results.append(p)
        return results

    def low_stock_items(self) -> list[SparePart]:
        return [p for p in self.parts.values() if p.low_stock]

    def stock_summary(self) -> dict[str, int]:
        summary: dict[str, int] = {}
        for p in self.parts.values():
            summary[p.part_type.value] = summary.get(p.part_type.value, 0) + p.quantity
        return summary

    def total_value(self) -> float:
        return sum(p.quantity * p.unit_cost for p in self.parts.values())


# ---------------------------------------------------------------------------
# Client Tracking
# ---------------------------------------------------------------------------

@dataclass
class Client:
    client_id: str
    name: str
    phone: str = ""
    email: str = ""
    address: str = ""
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    ticket_ids: list[str] = field(default_factory=list)

    @property
    def total_repairs(self) -> int:
        return len(self.ticket_ids)


class ClientManager:
    """Manages workshop clients."""

    def __init__(self, data_file: str = "clients.json"):
        self.data_file = data_file
        self.clients: dict[str, Client] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.data_file):
            return
        with open(self.data_file) as f:
            for rec in json.load(f):
                self.clients[rec["client_id"]] = Client(**rec)

    def _serialize(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        return str(obj)

    def save(self) -> None:
        with open(self.data_file, "w") as f:
            json.dump([asdict(c) for c in self.clients.values()], f, indent=2, default=self._serialize)

    def add_client(self, name: str, phone: str = "", email: str = "",
                   address: str = "", notes: str = "") -> Client:
        cid = str(uuid.uuid4())[:8]
        client = Client(client_id=cid, name=name, phone=phone, email=email,
                        address=address, notes=notes)
        self.clients[cid] = client
        self.save()
        return client

    def get_client(self, client_id: str) -> Optional[Client]:
        return self.clients.get(client_id)

    def search(self, query: str) -> list[Client]:
        q = query.lower()
        return [c for c in self.clients.values()
                if q in c.name.lower() or q in c.phone or q in c.email.lower()]

    def remove_client(self, client_id: str) -> bool:
        if client_id in self.clients:
            del self.clients[client_id]
            self.save()
            return True
        return False

    def top_clients(self, limit: int = 10) -> list[Client]:
        return sorted(self.clients.values(), key=lambda c: c.total_repairs, reverse=True)[:limit]


# ---------------------------------------------------------------------------
# Diagnostic Workflow
# ---------------------------------------------------------------------------

@dataclass
class DiagnosticRecord:
    record_id: str
    ticket_id: str
    step: DiagnosticStep
    status: str = "pending"  # pending, passed, failed, skipped
    technician: str = ""
    notes: str = ""
    started_at: str = ""
    completed_at: str = ""
    findings: dict = field(default_factory=dict)

    def complete(self, passed: bool, notes: str = "", findings: dict | None = None) -> None:
        self.status = "passed" if passed else "failed"
        self.notes = notes
        self.completed_at = datetime.now().isoformat()
        if findings:
            self.findings = findings


@dataclass
class DiagnosticWorkflow:
    """Ordered diagnostic steps for a repair ticket."""
    ticket_id: str
    steps: list[DiagnosticRecord] = field(default_factory=list)
    current_index: int = 0

    @classmethod
    def for_ticket(cls, ticket_id: str) -> DiagnosticWorkflow:
        wf = cls(ticket_id=ticket_id)
        for step in DiagnosticStep:
            rec = DiagnosticRecord(
                record_id=str(uuid.uuid4())[:8],
                ticket_id=ticket_id,
                step=step,
                started_at=datetime.now().isoformat(),
            )
            wf.steps.append(rec)
        return wf

    @property
    def current_step(self) -> Optional[DiagnosticRecord]:
        if self.current_index < len(self.steps):
            return self.steps[self.current_index]
        return None

    def advance(self, passed: bool, notes: str = "", findings: dict | None = None) -> Optional[DiagnosticRecord]:
        step = self.current_step
        if step is None:
            return None
        step.complete(passed, notes, findings)
        if passed:
            self.current_index += 1
        return step

    @property
    def is_complete(self) -> bool:
        return self.current_index >= len(self.steps)

    @property
    def progress_pct(self) -> float:
        return (self.current_index / len(self.steps)) * 100 if self.steps else 0

    @property
    def failed_steps(self) -> list[DiagnosticRecord]:
        return [s for s in self.steps if s.status == "failed"]

    def summary(self) -> dict:
        return {
            "ticket_id": self.ticket_id,
            "total_steps": len(self.steps),
            "completed": self.current_index,
            "progress": f"{self.progress_pct:.0f}%",
            "complete": self.is_complete,
            "failures": len(self.failed_steps),
        }


# ---------------------------------------------------------------------------
# Repair Tickets
# ---------------------------------------------------------------------------

@dataclass
class RepairTicket:
    ticket_id: str
    client_id: str
    device_category: DeviceCategory
    device_brand: str = ""
    device_model: str = ""
    device_serial: str = ""
    issue_description: str = ""
    status: RepairStatus = RepairStatus.RECEIVED
    priority: int = 2  # 1=urgent, 2=normal, 3=low
    estimated_cost: float = 0.0
    final_cost: float = 0.0
    parts_used: list[str] = field(default_factory=list)  # part_ids
    technician: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    delivered_at: str = ""
    notes: list[str] = field(default_factory=list)
    diagnostic: Optional[DiagnosticWorkflow] = None

    def set_status(self, status: RepairStatus) -> None:
        self.status = status
        self.updated_at = datetime.now().isoformat()
        if status == RepairStatus.DELIVERED:
            self.delivered_at = self.updated_at

    def add_note(self, note: str) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.notes.append(f"[{ts}] {note}")
        self.updated_at = datetime.now().isoformat()

    def add_part(self, part_id: str) -> None:
        if part_id not in self.parts_used:
            self.parts_used.append(part_id)

    def remove_part(self, part_id: str) -> bool:
        if part_id in self.parts_used:
            self.parts_used.remove(part_id)
            return True
        return False

    @property
    def is_open(self) -> bool:
        return self.status not in (RepairStatus.DELIVERED, RepairStatus.CANCELLED)

    @property
    def days_open(self) -> int:
        created = datetime.fromisoformat(self.created_at)
        return (datetime.now() - created).days

    def to_dict(self) -> dict:
        d = asdict(self)
        d["device_category"] = self.device_category.value
        d["status"] = self.status.value
        d.pop("diagnostic", None)
        return d


# ---------------------------------------------------------------------------
# Factory / Workshop Manager
# ---------------------------------------------------------------------------

class FactoryManager:
    """Central management system for the workshop/factory."""

    def __init__(self, data_dir: str = "factory_data"):
        self.data_dir = data_dir
        Path(data_dir).mkdir(parents=True, exist_ok=True)

        self.inventory = InventoryManager(os.path.join(data_dir, "inventory.json"))
        self.clients = ClientManager(os.path.join(data_dir, "clients.json"))
        self.tickets: dict[str, RepairTicket] = {}
        self.workflows: dict[str, DiagnosticWorkflow] = {}
        self._load_tickets()

    # -- persistence --------------------------------------------------------
    def _load_tickets(self) -> None:
        path = os.path.join(self.data_dir, "tickets.json")
        if not os.path.exists(path):
            return
        with open(path) as f:
            for rec in json.load(f):
                rec["device_category"] = DeviceCategory(rec["device_category"])
                rec["status"] = RepairStatus(rec["status"])
                rec.pop("diagnostic", None)
                self.tickets[rec["ticket_id"]] = RepairTicket(**rec)

    def _serialize(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        return str(obj)

    def save(self) -> None:
        path = os.path.join(self.data_dir, "tickets.json")
        with open(path, "w") as f:
            json.dump([t.to_dict() for t in self.tickets.values()], f, indent=2, default=self._serialize)
        self.inventory.save()
        self.clients.save()

    # -- ticket operations --------------------------------------------------
    def create_ticket(self, client_id: str, category: DeviceCategory,
                      brand: str, model: str, issue: str,
                      serial: str = "", priority: int = 2,
                      technician: str = "") -> RepairTicket:
        tid = f"TK-{uuid.uuid4().hex[:6].upper()}"
        ticket = RepairTicket(
            ticket_id=tid, client_id=client_id, device_category=category,
            device_brand=brand, device_model=model, device_serial=serial,
            issue_description=issue, priority=priority, technician=technician,
        )
        self.tickets[tid] = ticket

        # link to client
        client = self.clients.get_client(client_id)
        if client:
            client.ticket_ids.append(tid)

        # start diagnostic workflow
        self.workflows[tid] = DiagnosticWorkflow.for_ticket(ticket.ticket_id)
        ticket.diagnostic = self.workflows[tid]

        self.save()
        return ticket

    def get_ticket(self, ticket_id: str) -> Optional[RepairTicket]:
        return self.tickets.get(ticket_id)

    def update_status(self, ticket_id: str, status: RepairStatus) -> bool:
        ticket = self.tickets.get(ticket_id)
        if ticket:
            ticket.set_status(status)
            self.save()
            return True
        return False

    def cancel_ticket(self, ticket_id: str) -> bool:
        return self.update_status(ticket_id, RepairStatus.CANCELLED)

    def add_part_to_ticket(self, ticket_id: str, part_id: str) -> bool:
        ticket = self.tickets.get(ticket_id)
        part = self.inventory.get_part(part_id)
        if ticket and part and part.consume():
            ticket.add_part(part_id)
            self.save()
            return True
        return False

    def start_diagnostic(self, ticket_id: str) -> Optional[DiagnosticWorkflow]:
        wf = self.workflows.get(ticket_id)
        if wf:
            self.update_status(ticket_id, RepairStatus.DIAGNOSED)
            return wf
        return None

    def advance_diagnostic(self, ticket_id: str, passed: bool,
                           notes: str = "", findings: dict | None = None) -> Optional[DiagnosticRecord]:
        wf = self.workflows.get(ticket_id)
        if wf is None:
            return None
        result = wf.advance(passed, notes, findings)
        if result and not passed:
            self.update_status(ticket_id, RepairStatus.IN_PROGRESS)
        if wf.is_complete:
            self.update_status(ticket_id, RepairStatus.QUALITY_CHECK)
        self.save()
        return result

    # -- queries ------------------------------------------------------------
    def open_tickets(self) -> list[RepairTicket]:
        return [t for t in self.tickets.values() if t.is_open]

    def tickets_by_status(self, status: RepairStatus) -> list[RepairTicket]:
        return [t for t in self.tickets.values() if t.status == status]

    def tickets_by_category(self, category: DeviceCategory) -> list[RepairTicket]:
        return [t for t in self.tickets.values() if t.device_category == category]

    def overdue_tickets(self, days: int = 7) -> list[RepairTicket]:
        return [t for t in self.open_tickets() if t.days_open > days]

    def revenue_report(self) -> dict:
        delivered = [t for t in self.tickets.values()
                     if t.status == RepairStatus.DELIVERED]
        total = sum(t.final_cost for t in delivered)
        avg = total / len(delivered) if delivered else 0
        by_brand: dict[str, float] = {}
        for t in delivered:
            by_brand[t.device_brand] = by_brand.get(t.device_brand, 0) + t.final_cost
        return {
            "total_repairs": len(delivered),
            "total_revenue": round(total, 2),
            "average_cost": round(avg, 2),
            "by_brand": by_brand,
        }

    def dashboard(self) -> dict:
        return {
            "open_tickets": len(self.open_tickets()),
            "by_status": {s.value: len(self.tickets_by_status(s)) for s in RepairStatus},
            "by_category": {c.value: len(self.tickets_by_category(c)) for c in DeviceCategory},
            "overdue": len(self.overdue_tickets()),
            "low_stock_parts": len(self.inventory.low_stock_items()),
            "inventory_value": round(self.inventory.total_value(), 2),
            "total_clients": len(self.clients.clients),
            "revenue": self.revenue_report(),
        }

    def export_report(self, filename: str = "factory_report.json") -> None:
        report = self.dashboard()
        report["exported_at"] = datetime.now().isoformat()
        with open(filename, "w") as f:
            json.dump(report, f, indent=2, default=self._serialize)


# ---------------------------------------------------------------------------
# Predefined spare parts catalog
# ---------------------------------------------------------------------------

COMMON_PARTS: list[dict] = [
    # Phone screens
    {"part_type": PartType.SCREEN_OLED, "name": "Samsung AMOLED Screen",
     "compatible": ["galaxy_s24", "galaxy_s23", "galaxy_a54"], "cost": 85.0},
    {"part_type": PartType.SCREEN_LCD, "name": "iPhone LCD Screen",
     "compatible": ["iphone_15", "iphone_14", "iphone_13"], "cost": 65.0},
    {"part_type": PartType.SCREEN_AMOLED, "name": "Xiaomi AMOLED Screen",
     "compatible": ["xiaomi_14", "xiaomi_13", "redmi_note_12"], "cost": 55.0},
    # Tablet screens
    {"part_type": PartType.TOUCHSCREEN_DIGITIZER, "name": "iPad Digitizer",
     "compatible": ["ipad_pro_m2", "ipad_air_m1", "ipad_10th"], "cost": 95.0},
    {"part_type": PartType.SCREEN_LCD, "name": "Samsung Tab Screen",
     "compatible": ["tab_s9", "tab_a8", "tab_s6_lite"], "cost": 70.0},
    # Smartwatch parts
    {"part_type": PartType.SCREEN_OLED, "name": "Apple Watch OLED",
     "compatible": ["apple_watch_9", "apple_watch_ultra", "apple_watch_se"], "cost": 120.0},
    {"part_type": PartType.SCREEN_AMOLED, "name": "Galaxy Watch Screen",
     "compatible": ["galaxy_watch_6", "galaxy_watch_5"], "cost": 75.0},
    # Smart glasses parts
    {"part_type": PartType.LENS_MODULE, "name": "AR Lens Module",
     "compatible": ["rayneo_air", "nreal_air", "xreal_air"], "cost": 150.0},
    {"part_type": PartType.TACTILE_STRIP, "name": "Smart Glasses Nose Pad",
     "compatible": ["rayneo_air", "nreal_air", "meta_rayban"], "cost": 15.0},
    # Universal batteries
    {"part_type": PartType.BATTERY_LIPO, "name": "Phone Battery 4000mAh",
     "compatible": ["galaxy_s24", "iphone_15", "xiaomi_14", "pixel_8"], "cost": 22.0},
    {"part_type": PartType.BATTERY_LIPO, "name": "Watch Battery 300mAh",
     "compatible": ["apple_watch_9", "galaxy_watch_6"], "cost": 18.0},
    # Universal parts
    {"part_type": PartType.CHARGING_PORT, "name": "USB-C Charging Port",
     "compatible": ["galaxy_s24", "iphone_15", "xiaomi_14", "ipad_air_m1"], "cost": 12.0},
    {"part_type": PartType.CAMERA_MODULE, "name": "Rear Camera Module",
     "compatible": ["galaxy_s24", "iphone_15", "xiaomi_14"], "cost": 45.0},
    {"part_type": PartType.SPEAKER, "name": "Speaker Assembly",
     "compatible": ["galaxy_s24", "iphone_15", "tab_s9"], "cost": 10.0},
]


# ---------------------------------------------------------------------------
# Demo / CLI
# ---------------------------------------------------------------------------

def demo() -> None:
    """Run a quick demo of the factory management system."""
    print("=" * 65)
    print("  AuraTool-Suite — Workshop & Factory Management System")
    print("=" * 65)

    fm = FactoryManager()

    # --- seed inventory ---
    print("\n[1/5] Seeding spare parts inventory...")
    for part in COMMON_PARTS:
        fm.inventory.add_part(
            part_type=part["part_type"], name=part["name"],
            compatible=part["compatible"], qty=20, cost=part["cost"],
            supplier="AuraParts Inc.", location="Shelf-A",
        )
    print(f"     ✅ {len(fm.inventory.parts)} parts loaded")
    print(f"     💰 Inventory value: ${fm.inventory.total_value():,.2f}")

    # --- register clients ---
    print("\n[2/5] Registering clients...")
    c1 = fm.clients.add_client("Ahmed Al-Farsi", "+96891234567", "ahmed@example.com")
    c2 = fm.clients.add_client("Sara Hassan", "+96892345678", "sara@example.com")
    c3 = fm.clients.add_client("Omar Devices Shop", "+96893456789", "omar@shop.com")
    print(f"     ✅ {len(fm.clients.clients)} clients registered")

    # --- create tickets ---
    print("\n[3/5] Creating repair tickets...")

    t1 = fm.create_ticket(c1.client_id, DeviceCategory.PHONE, "Samsung",
                          "galaxy_s24", "Screen cracked after drop",
                          serial="SM-S926B-XYZ", priority=1, technician="Tech-Ahmed")
    fm.start_diagnostic(t1.ticket_id)
    fm.advance_diagnostic(t1.ticket_id, True, "Screen damage confirmed", {"damage_pct": 85})
    fm.advance_diagnostic(t1.ticket_id, True, "Display backlight OK")
    fm.advance_diagnostic(t1.ticket_id, True, "Battery 92% health")
    fm.advance_diagnostic(t1.ticket_id, True, "Software intact")
    fm.advance_diagnostic(t1.ticket_id, True, "Connectivity OK")
    fm.advance_diagnostic(t1.ticket_id, True, "Sensors calibrated")
    fm.advance_diagnostic(t1.ticket_id, True, "Storage healthy")
    fm.advance_diagnostic(t1.ticket_id, True, "Battery test passed")
    fm.advance_diagnostic(t1.ticket_id, True, "Pre-repair inspection done")
    # assign part
    screen_parts = fm.inventory.find_for_device("galaxy_s24", PartType.SCREEN_OLED)
    if screen_parts:
        fm.add_part_to_ticket(t1.ticket_id, screen_parts[0].part_id)
    fm.update_status(t1.ticket_id, RepairStatus.IN_PROGRESS)
    t1.estimated_cost = 85.0
    t1.final_cost = 95.0
    fm.update_status(t1.ticket_id, RepairStatus.READY)
    print(f"     ✅ {t1.ticket_id}: Samsung Galaxy S24 — {t1.status.value}")

    t2 = fm.create_ticket(c2.client_id, DeviceCategory.TABLET, "Apple",
                          "ipad_pro_m2", "Battery drains in 2 hours",
                          serial="MNXYZ2/A", priority=2, technician="Tech-Sara")
    fm.start_diagnostic(t2.ticket_id)
    fm.advance_diagnostic(t2.ticket_id, True, "Battery at 41% health — replacement needed",
                          {"battery_health": 41})
    print(f"     ✅ {t2.ticket_id}: iPad Pro M2 — {t2.status.value}")

    t3 = fm.create_ticket(c3.client_id, DeviceCategory.SMARTWATCH, "Samsung",
                          "galaxy_watch_6", "Touchscreen unresponsive",
                          serial="SM-R930-1234", priority=2)
    fm.start_diagnostic(t3.ticket_id)
    print(f"     ✅ {t3.ticket_id}: Galaxy Watch 6 — {t3.status.value}")

    t4 = fm.create_ticket(c3.client_id, DeviceCategory.SMART_GLASSES, "Xreal",
                          "nreal_air", "Left lens display flickering",
                          serial="NRA-5678", priority=3, technician="Tech-Ahmed")
    fm.start_diagnostic(t4.ticket_id)
    print(f"     ✅ {t4.ticket_id}: Xreal Air Glasses — {t4.status.value}")

    # --- diagnostics summary ---
    print("\n[4/5] Diagnostic workflow status:")
    for tid, wf in fm.workflows.items():
        s = wf.summary()
        print(f"     {s['ticket_id']}: {s['completed']}/{s['total_steps']} steps "
              f"({s['progress']}) failures={s['failures']}")

    # --- dashboard ---
    print("\n[5/5] Workshop Dashboard:")
    dash = fm.dashboard()
    print(f"     📋 Open tickets:    {dash['open_tickets']}")
    print(f"     ⚠️  Overdue tickets: {dash['overdue']}")
    print(f"     📦 Low stock parts: {dash['low_stock_parts']}")
    print(f"     💰 Inventory value: ${dash['inventory_value']:,.2f}")
    print(f"     👥 Total clients:   {dash['total_clients']}")
    print(f"     📊 Repairs done:    {dash['revenue']['total_repairs']}")
    print(f"     💵 Revenue:         ${dash['revenue']['total_revenue']:,.2f}")
    print()
    print("     Status breakdown:")
    for status, count in dash["by_status"].items():
        if count:
            print(f"       {status:20s}: {count}")
    print()
    print("     By category:")
    for cat, count in dash["by_category"].items():
        if count:
            print(f"       {cat:20s}: {count}")

    # --- inventory alerts ---
    low = fm.inventory.low_stock_items()
    if low:
        print(f"\n     🚨 Low stock alerts ({len(low)} items):")
        for p in low:
            print(f"       • {p.name} ({p.part_type.value}): {p.quantity}/{p.min_stock}")

    # --- save ---
    fm.save()
    fm.export_report()
    print(f"\n     💾 Data saved to {fm.data_dir}/")
    print(f"     📄 Report exported to factory_report.json")

    print("\n" + "=" * 65)
    print("  Demo complete. All subsystems operational.")
    print("=" * 65)


if __name__ == "__main__":
    demo()
