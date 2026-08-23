"""
AuraTool-Suite — Workshop & Factory REST API
=============================================
Zero-dependency HTTP API exposing the factory management system.
Built on Python's stdlib http.server — no Flask or FastAPI required.

Endpoints
---------
Clients:
    GET    /api/clients                List all clients
    POST   /api/clients                Create a client
    GET    /api/clients/<id>           Get a client
    DELETE /api/clients/<id>           Delete a client
    GET    /api/clients/search?q=...   Search clients
    GET    /api/clients/top?limit=10   Top clients by repair count

Tickets:
    GET    /api/tickets                List all tickets (query: status, category)
    POST   /api/tickets                Create a ticket
    GET    /api/tickets/<id>           Get a ticket
    PUT    /api/tickets/<id>/status    Update ticket status
    POST   /api/tickets/<id>/cancel    Cancel a ticket
    POST   /api/tickets/<id>/deliver   Mark ticket delivered
    POST   /api/tickets/<id>/note      Add a note
    POST   /api/tickets/<id>/part      Assign a part

Diagnostics:
    GET    /api/tickets/<id>/diagnostic       Get diagnostic workflow
    POST   /api/tickets/<id>/diagnostic/start Start diagnostic
    POST   /api/tickets/<id>/diagnostic/next  Advance diagnostic step

Inventory:
    GET    /api/parts                 List all parts (query: device, type)
    POST   /api/parts                 Add a part
    GET    /api/parts/<id>            Get a part
    DELETE /api/parts/<id>            Delete a part
    GET    /api/parts/low-stock       Low stock items
    GET    /api/parts/summary         Stock summary by type
    POST   /api/parts/seed            Seed common parts catalog

Dashboard:
    GET    /api/dashboard             Full dashboard data
    GET    /api/revenue               Revenue report
    GET    /api/report                Export full report

Run
---
    python -m core.factory_api              # starts on port 8500
    python -m core.factory_api --port 9000  # custom port
"""

from __future__ import annotations

import json
import sys
import argparse
import logging
from enum import Enum
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Any

import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auratool_factory import (
    FactoryManager, DeviceCategory, RepairStatus, PartType,
    COMMON_PARTS,
)

logger = logging.getLogger("AuraTool.API")


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def _json(obj: Any) -> str:
    return json.dumps(obj, indent=2, default=str)


def _enum_val(e: Enum) -> str:
    return e.value if isinstance(e, Enum) else str(e)


class ErrorResponse(Exception):
    def __init__(self, message: str, status: int = 400):
        self.message = message
        self.status = status


# ---------------------------------------------------------------------------
# URL Router
# ---------------------------------------------------------------------------

class Router:
    """Simple pattern-based URL router supporting decorator registration."""

    def __init__(self):
        self.routes: list[tuple[str, str, callable]] = []  # (method, pattern, handler)

    def _add(self, method: str, pattern: str, handler=None):
        if handler is not None:
            # Direct call: r.get("/path", func)
            self.routes.append((method, pattern, handler))
            return handler
        # Decorator call: @r.get("/path")
        def decorator(fn):
            self.routes.append((method, pattern, fn))
            return fn
        return decorator

    def get(self, pattern: str, handler=None):
        return self._add("GET", pattern, handler)

    def post(self, pattern: str, handler=None):
        return self._add("POST", pattern, handler)

    def put(self, pattern: str, handler=None):
        return self._add("PUT", pattern, handler)

    def delete(self, pattern: str, handler=None):
        return self._add("DELETE", pattern, handler)

    def match(self, method: str, path: str) -> tuple[callable | None, dict]:
        # Try static routes first (no placeholders), then dynamic
        static = []
        dynamic = []
        for route_method, pattern, handler in self.routes:
            if method != route_method:
                continue
            if "<" in pattern:
                dynamic.append((pattern, handler))
            else:
                static.append((pattern, handler))
        for pattern, handler in static:
            if path.rstrip("/") == pattern.rstrip("/"):
                return handler, {}
        for pattern, handler in dynamic:
            params = self._match_pattern(pattern, path)
            if params is not None:
                return handler, params
        return None, {}

    def _match_pattern(self, pattern: str, path: str) -> dict | None:
        """Match /api/resource/<id> style patterns."""
        pattern_parts = pattern.strip("/").split("/")
        path_parts = path.strip("/").split("/")
        if len(pattern_parts) != len(path_parts):
            return None
        params = {}
        for pp, rp in zip(pattern_parts, path_parts):
            if pp.startswith("<") and pp.endswith(">"):
                params[pp[1:-1]] = rp
            elif pp != rp:
                return None
        return params


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------

class FactoryAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the factory REST API."""

    factory: FactoryManager = None  # set by server class
    router: Router = None           # set by server class

    def log_message(self, format, *args):
        logger.info(format % args)

    # -- helpers -------------------------------------------------------------

    def _send_json(self, data: Any, status: int = 200) -> None:
        body = _json(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, message: str, status: int = 400) -> None:
        self._send_json({"error": message}, status)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw)

    def _path(self) -> str:
        parsed = urlparse(self.path)
        return parsed.path

    def _query(self) -> dict[str, list[str]]:
        parsed = urlparse(self.path)
        return parse_qs(parsed.query)

    # -- dispatch -----------------------------------------------------------

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _dispatch(self, method: str):
        try:
            handler, params = self.router.match(method, self._path())
            if handler is None:
                self._send_error("Not Found", 404)
                return
            handler(self, params)
        except ErrorResponse as e:
            self._send_error(e.message, e.status)
        except Exception as e:
            logger.exception("Unhandled error")
            self._send_error(str(e), 500)


# ---------------------------------------------------------------------------
# Route Registration
# ---------------------------------------------------------------------------

def register_routes(r: Router) -> None:

    # === Clients ===========================================================

    @r.get("/api/clients")
    def list_clients(h: FactoryAPIHandler, params: dict):
        clients = list(h.factory.clients.clients.values())
        h._send_json([{
            "client_id": c.client_id, "name": c.name, "phone": c.phone,
            "email": c.email, "address": c.address,
            "total_repairs": c.total_repairs,
            "created_at": c.created_at,
        } for c in clients])

    @r.post("/api/clients")
    def create_client(h: FactoryAPIHandler, params: dict):
        body = h._read_body()
        name = body.get("name", "").strip()
        if not name:
            raise ErrorResponse("'name' is required")
        c = h.factory.clients.add_client(
            name, body.get("phone", ""), body.get("email", ""),
            body.get("address", ""), body.get("notes", ""),
        )
        h._send_json({"client_id": c.client_id, "name": c.name, "message": "created"}, 201)

    @r.get("/api/clients/<id>")
    def get_client(h: FactoryAPIHandler, params: dict):
        c = h.factory.clients.get_client(params["id"])
        if c is None:
            raise ErrorResponse("Client not found", 404)
        h._send_json({
            "client_id": c.client_id, "name": c.name, "phone": c.phone,
            "email": c.email, "address": c.address, "notes": c.notes,
            "total_repairs": c.total_repairs, "ticket_ids": c.ticket_ids,
            "created_at": c.created_at,
        })

    @r.delete("/api/clients/<id>")
    def delete_client(h: FactoryAPIHandler, params: dict):
        if not h.factory.clients.remove_client(params["id"]):
            raise ErrorResponse("Client not found", 404)
        h._send_json({"message": "deleted"})

    @r.get("/api/clients/search")
    def search_clients(h: FactoryAPIHandler, params: dict):
        q = h._query().get("q", [""])[0]
        results = h.factory.clients.search(q)
        h._send_json([{
            "client_id": c.client_id, "name": c.name, "phone": c.phone,
            "email": c.email, "total_repairs": c.total_repairs,
        } for c in results])

    @r.get("/api/clients/top")
    def top_clients(h: FactoryAPIHandler, params: dict):
        limit = int(h._query().get("limit", ["10"])[0])
        top = h.factory.clients.top_clients(limit)
        h._send_json([{
            "client_id": c.client_id, "name": c.name,
            "total_repairs": c.total_repairs,
        } for c in top])

    # === Tickets ===========================================================

    @r.get("/api/tickets")
    def list_tickets(h: FactoryAPIHandler, params: dict):
        q = h._query()
        tickets = list(h.factory.tickets.values())
        if "status" in q:
            status = RepairStatus(q["status"][0])
            tickets = [t for t in tickets if t.status == status]
        if "category" in q:
            cat = DeviceCategory(q["category"][0])
            tickets = [t for t in tickets if t.device_category == cat]
        h._send_json([t.to_dict() for t in tickets])

    @r.post("/api/tickets")
    def create_ticket(h: FactoryAPIHandler, params: dict):
        body = h._read_body()
        for field in ("client_id", "device_category", "device_brand", "device_model", "issue_description"):
            if not body.get(field):
                raise ErrorResponse(f"'{field}' is required")
        cat = DeviceCategory(body["device_category"])
        t = h.factory.create_ticket(
            body["client_id"], cat, body["device_brand"],
            body["device_model"], body["issue_description"],
            body.get("device_serial", ""),
            int(body.get("priority", 2)),
            body.get("technician", ""),
        )
        h._send_json({"ticket_id": t.ticket_id, "message": "created"}, 201)

    @r.get("/api/tickets/<id>")
    def get_ticket(h: FactoryAPIHandler, params: dict):
        t = h.factory.get_ticket(params["id"])
        if t is None:
            raise ErrorResponse("Ticket not found", 404)
        h._send_json(t.to_dict())

    @r.put("/api/tickets/<id>/status")
    def update_ticket_status(h: FactoryAPIHandler, params: dict):
        body = h._read_body()
        status_val = body.get("status")
        if not status_val:
            raise ErrorResponse("'status' is required")
        status = RepairStatus(status_val)
        if not h.factory.update_status(params["id"], status):
            raise ErrorResponse("Ticket not found", 404)
        h._send_json({"message": f"status set to {status_val}"})

    @r.post("/api/tickets/<id>/cancel")
    def cancel_ticket(h: FactoryAPIHandler, params: dict):
        if not h.factory.cancel_ticket(params["id"]):
            raise ErrorResponse("Ticket not found", 404)
        h._send_json({"message": "ticket cancelled"})

    @r.post("/api/tickets/<id>/deliver")
    def deliver_ticket(h: FactoryAPIHandler, params: dict):
        if not h.factory.update_status(params["id"], RepairStatus.DELIVERED):
            raise ErrorResponse("Ticket not found", 404)
        h._send_json({"message": "ticket delivered"})

    @r.post("/api/tickets/<id>/note")
    def add_ticket_note(h: FactoryAPIHandler, params: dict):
        body = h._read_body()
        note = body.get("note", "")
        t = h.factory.get_ticket(params["id"])
        if t is None:
            raise ErrorResponse("Ticket not found", 404)
        t.add_note(note)
        h.factory.save()
        h._send_json({"message": "note added"})

    @r.post("/api/tickets/<id>/part")
    def assign_part(h: FactoryAPIHandler, params: dict):
        body = h._read_body()
        part_id = body.get("part_id", "")
        if not h.factory.add_part_to_ticket(params["id"], part_id):
            raise ErrorResponse("Failed to assign part (not found or out of stock)", 400)
        h._send_json({"message": "part assigned"})

    # === Diagnostics =======================================================

    @r.get("/api/tickets/<id>/diagnostic")
    def get_diagnostic(h: FactoryAPIHandler, params: dict):
        wf = h.factory.workflows.get(params["id"])
        if wf is None:
            raise ErrorResponse("No diagnostic workflow found", 404)
        h._send_json({
            "summary": wf.summary(),
            "steps": [{
                "step": rec.step.value,
                "status": rec.status,
                "notes": rec.notes,
                "findings": rec.findings,
            } for rec in wf.steps],
        })

    @r.post("/api/tickets/<id>/diagnostic/start")
    def start_diagnostic(h: FactoryAPIHandler, params: dict):
        wf = h.factory.start_diagnostic(params["id"])
        if wf is None:
            raise ErrorResponse("Ticket not found", 404)
        h._send_json({"message": "diagnostic started", "steps": len(wf.steps)})

    @r.post("/api/tickets/<id>/diagnostic/next")
    def advance_diagnostic(h: FactoryAPIHandler, params: dict):
        body = h._read_body()
        passed = body.get("passed")
        if passed is None:
            raise ErrorResponse("'passed' (bool) is required")
        result = h.factory.advance_diagnostic(
            params["id"], bool(passed),
            body.get("notes", ""), body.get("findings"),
        )
        if result is None:
            raise ErrorResponse("No active workflow for this ticket", 400)
        h._send_json({
            "step": result.step.value,
            "status": result.status,
            "notes": result.notes,
        })

    # === Inventory =========================================================

    @r.get("/api/parts")
    def list_parts(h: FactoryAPIHandler, params: dict):
        q = h._query()
        parts = list(h.factory.inventory.parts.values())
        if "device" in q:
            model = q["device"][0]
            pt = PartType(q["type"][0]) if "type" in q else None
            parts = h.factory.inventory.find_for_device(model, pt)
        elif "type" in q:
            pt = PartType(q["type"][0])
            parts = [p for p in parts if p.part_type == pt]
        h._send_json([{
            "part_id": p.part_id, "part_type": p.part_type.value,
            "name": p.name, "compatible_devices": p.compatible_devices,
            "quantity": p.quantity, "min_stock": p.min_stock,
            "unit_cost": p.unit_cost, "supplier": p.supplier,
            "location": p.location, "in_stock": p.in_stock,
            "low_stock": p.low_stock,
        } for p in parts])

    @r.post("/api/parts")
    def add_part(h: FactoryAPIHandler, params: dict):
        body = h._read_body()
        ptype_str = body.get("part_type")
        name = body.get("name", "")
        if not ptype_str or not name:
            raise ErrorResponse("'part_type' and 'name' are required")
        ptype = PartType(ptype_str)
        compatible = body.get("compatible_devices", [])
        part = h.factory.inventory.add_part(
            ptype, name, compatible,
            qty=int(body.get("quantity", 0)),
            cost=float(body.get("unit_cost", 0)),
            supplier=body.get("supplier", ""),
            location=body.get("location", ""),
        )
        h._send_json({"part_id": part.part_id, "message": "created"}, 201)

    @r.get("/api/parts/<id>")
    def get_part(h: FactoryAPIHandler, params: dict):
        p = h.factory.inventory.get_part(params["id"])
        if p is None:
            raise ErrorResponse("Part not found", 404)
        h._send_json({
            "part_id": p.part_id, "part_type": p.part_type.value,
            "name": p.name, "compatible_devices": p.compatible_devices,
            "quantity": p.quantity, "min_stock": p.min_stock,
            "unit_cost": p.unit_cost, "supplier": p.supplier,
            "location": p.location,
        })

    @r.delete("/api/parts/<id>")
    def delete_part(h: FactoryAPIHandler, params: dict):
        if not h.factory.inventory.remove_part(params["id"]):
            raise ErrorResponse("Part not found", 404)
        h._send_json({"message": "deleted"})

    @r.get("/api/parts/low-stock")
    def low_stock(h: FactoryAPIHandler, params: dict):
        items = h.factory.inventory.low_stock_items()
        h._send_json([{
            "part_id": p.part_id, "name": p.name,
            "part_type": p.part_type.value,
            "quantity": p.quantity, "min_stock": p.min_stock,
        } for p in items])

    @r.get("/api/parts/summary")
    def stock_summary(h: FactoryAPIHandler, params: dict):
        h._send_json({
            "summary": h.factory.inventory.stock_summary(),
            "total_value": h.factory.inventory.total_value(),
        })

    @r.post("/api/parts/seed")
    def seed_parts(h: FactoryAPIHandler, params: dict):
        count = 0
        for p in COMMON_PARTS:
            h.factory.inventory.add_part(
                p["part_type"], p["name"], p["compatible"],
                qty=20, cost=p["cost"], supplier="AuraParts Inc.",
            )
            count += 1
        h._send_json({"message": f"seeded {count} parts"})

    # === Dashboard & Reports ===============================================

    @r.get("/api/dashboard")
    def get_dashboard(h: FactoryAPIHandler, params: dict):
        h._send_json(h.factory.dashboard())

    @r.get("/api/revenue")
    def get_revenue(h: FactoryAPIHandler, params: dict):
        h._send_json(h.factory.revenue_report())

    @r.get("/api/report")
    def get_report(h: FactoryAPIHandler, params: dict):
        report = h.factory.dashboard()
        report["exported_at"] = __import__("datetime").datetime.now().isoformat()
        h._send_json(report)


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

class FactoryAPIServer(HTTPServer):
    """Custom HTTPServer that holds the FactoryManager instance."""

    def __init__(self, addr, handler_class, factory: FactoryManager):
        super().__init__(addr, handler_class)
        self.factory = factory

        # Setup router
        self.router = Router()
        register_routes(self.router)

        # Bind to handler
        handler_class.factory = factory
        handler_class.router = self.router


def run_server(host: str = "0.0.0.0", port: int = 8500, data_dir: str = "factory_data"):
    """Start the REST API server."""
    factory = FactoryManager(data_dir)
    server = FactoryAPIServer((host, port), FactoryAPIHandler, factory)

    logger.info("=" * 55)
    logger.info("  AuraTool-Suite — Workshop & Factory REST API")
    logger.info(f"  Listening on http://{host}:{port}")
    logger.info("=" * 55)
    logger.info("  Endpoints:")
    logger.info("    GET  /api/clients          List clients")
    logger.info("    POST /api/clients          Create client")
    logger.info("    GET  /api/tickets          List tickets")
    logger.info("    POST /api/tickets          Create ticket")
    logger.info("    GET  /api/parts            List parts")
    logger.info("    POST /api/parts            Add part")
    logger.info("    GET  /api/dashboard        Dashboard")
    logger.info("    GET  /api/revenue          Revenue report")
    logger.info("=" * 55)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("\nServer shutting down...")
        server.shutdown()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="AuraTool-Suite Factory REST API")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8500, help="Bind port (default: 8500)")
    parser.add_argument("--data-dir", default="factory_data", help="Data directory (default: factory_data)")
    args = parser.parse_args()

    run_server(args.host, args.port, args.data_dir)
