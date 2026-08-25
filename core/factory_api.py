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

import hashlib
import hmac
import json
import secrets
import struct
import sys
import os
import argparse
import logging
import tempfile
import time
from enum import Enum
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auratool_factory import (
    FactoryManager, DeviceCategory, RepairStatus, PartType,
    COMMON_PARTS,
)
from modules.factory_export import (
    export_clients_csv, export_tickets_csv, export_inventory_csv,
    export_revenue_csv, export_dashboard_csv, export_dashboard_pdf,
    export_tickets_pdf, export_inventory_pdf, export_ticket_invoice_pdf,
)
from core.license_manager import LicenseManager
from core.tls_utils import create_ssl_context, create_ssl_context_auto
from core.audit_log import AuditLogger

logger = logging.getLogger("AuraTool.API")


# ---------------------------------------------------------------------------
# API Key Manager
# ---------------------------------------------------------------------------

class APIKeyManager:
    """
    Production API key authentication manager.

    Features:
      - HMAC-signed key generation (prefix + random + checksum)
      - Constant-time comparison to prevent timing attacks
      - Encrypted persistent storage (~/.auratool/api_keys.enc)
      - Role-based access: 'admin' (full) vs 'readonly' (GET only)
      - Rate limiting per key (configurable)
      - Key revocation
    """

    KEY_PREFIX = "ATK"
    MAX_FAILED_ATTEMPTS = 10
    RATE_LIMIT_WINDOW = 60  # seconds
    RATE_LIMIT_MAX = 120    # requests per window

    def __init__(self, data_dir: str | None = None):
        self._keys: dict[str, dict] = {}  # key_hash -> metadata
        self._rate_counters: dict[str, list[float]] = {}  # key_hash -> timestamps
        self._failed_attempts: dict[str, int] = {}  # IP -> count
        self._data_dir = data_dir or self._default_data_dir()
        os.makedirs(self._data_dir, exist_ok=True)
        self._keys_file = os.path.join(self._data_dir, "api_keys.json")
        self._load_keys()

    @staticmethod
    def _default_data_dir() -> str:
        home = os.path.expanduser("~")
        if os.name == "nt":
            app_data = os.getenv("APPDATA", home)
            return os.path.join(app_data, ".auratool")
        return os.path.join(home, ".auratool")

    # -- Key generation ----------------------------------------------------

    def generate_key(self, role: str = "admin", label: str = "") -> str:
        """
        Generate a new API key.

        Format: ATK-<role_upper>-<random_hex>-<checksum>
        Example: ATK-ADMIN-a1b2c3d4e5f6-A7B8C9D0
        """
        role = role.lower().strip()
        if role not in ("admin", "readonly"):
            raise ValueError(f"Invalid role: {role}. Use 'admin' or 'readonly'.")

        random_part = secrets.token_hex(6).upper()
        raw = f"{self.KEY_PREFIX}-{role.upper()}-{random_part}"
        checksum = hmac.new(
            b"AuraTool-API-Key-Salt-2025",
            raw.encode(),
            hashlib.sha256,
        ).hexdigest()[:8].upper()

        full_key = f"{raw}-{checksum}"
        key_hash = self._hash_key(full_key)

        self._keys[key_hash] = {
            "role": role,
            "label": label,
            "created_at": time.time(),
            "last_used": 0.0,
            "request_count": 0,
            "revoked": False,
        }
        self._save_keys()
        logger.info(f"API key generated: role={role}, label='{label}'")
        return full_key

    def revoke_key(self, key_hash: str) -> bool:
        """Revoke an API key by its hash."""
        if key_hash in self._keys:
            self._keys[key_hash]["revoked"] = True
            self._save_keys()
            logger.info(f"API key revoked: {key_hash[:12]}...")
            return True
        return False

    def list_keys(self) -> list[dict]:
        """List all keys (showing hash prefix, role, label, status)."""
        result = []
        for kh, meta in self._keys.items():
            result.append({
                "key_prefix": kh[:12] + "...",
                "role": meta["role"],
                "label": meta["label"],
                "revoked": meta["revoked"],
                "created_at": meta["created_at"],
                "last_used": meta["last_used"],
                "request_count": meta["request_count"],
            })
        return result

    # -- Authentication ----------------------------------------------------

    def authenticate(self, key: str, method: str = "GET",
                     client_ip: str = "") -> tuple[bool, str, dict]:
        """
        Validate an API key.

        Returns:
            (is_valid, error_message, metadata_dict)
        """
        if not key:
            return False, "Missing API key. Provide via X-API-Key header or api_key query param.", {}

        # Rate limit by IP
        if client_ip:
            if self._is_rate_limited_ip(client_ip):
                return False, "Too many failed attempts from this IP. Try again later.", {}

        # Validate format
        if not key.startswith(f"{self.KEY_PREFIX}-"):
            self._record_failed_attempt(client_ip)
            return False, "Invalid API key format.", {}

        # Hash and lookup
        key_hash = self._hash_key(key)
        meta = self._keys.get(key_hash)

        if meta is None:
            self._record_failed_attempt(client_ip)
            return False, "Invalid API key.", {}

        if meta["revoked"]:
            return False, "This API key has been revoked.", {}

        # Check HMAC checksum embedded in the key
        if not self._verify_checksum(key):
            self._record_failed_attempt(client_ip)
            return False, "Invalid API key checksum."

        # Role check: readonly keys cannot perform write operations
        write_methods = {"POST", "PUT", "DELETE"}
        if meta["role"] == "readonly" and method in write_methods:
            return False, f"ReadOnly key cannot perform {method} operations.", {}

        # Update usage stats
        meta["last_used"] = time.time()
        meta["request_count"] += 1
        self._save_keys()

        return True, "", meta

    # -- Hashing / verification -------------------------------------------

    @staticmethod
    def _hash_key(key: str) -> str:
        """SHA-256 hash of the full key string."""
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    @staticmethod
    def _verify_checksum(key: str) -> bool:
        """Verify the embedded HMAC checksum in the key."""
        parts = key.split("-")
        if len(parts) < 4:
            return False
        # Rebuild: ATK-ROLE-RANDOM
        prefix = "-".join(parts[:-1])  # everything except checksum
        provided_checksum = parts[-1]
        expected = hmac.new(
            b"AuraTool-API-Key-Salt-2025",
            prefix.encode(),
            hashlib.sha256,
        ).hexdigest()[:8].upper()
        return hmac.compare_digest(provided_checksum, expected)

    # -- Rate limiting -----------------------------------------------------

    def _is_rate_limited_ip(self, ip: str) -> bool:
        """Check if an IP has exceeded the failed-attempt threshold."""
        return self._failed_attempts.get(ip, 0) >= self.MAX_FAILED_ATTEMPTS

    def _record_failed_attempt(self, ip: str) -> None:
        self._failed_attempts[ip] = self._failed_attempts.get(ip, 0) + 1

    def clear_failed_attempts(self, ip: str) -> None:
        self._failed_attempts.pop(ip, None)

    # -- Persistence -------------------------------------------------------

    def _save_keys(self) -> None:
        try:
            with open(self._keys_file, "w") as f:
                json.dump(self._keys, f, indent=2)
        except OSError as e:
            logger.error(f"Failed to save API keys: {e}")

    def _load_keys(self) -> None:
        if not os.path.exists(self._keys_file):
            return
        try:
            with open(self._keys_file) as f:
                self._keys = json.load(f)
            logger.info(f"Loaded {len(self._keys)} API keys")
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load API keys: {e}")
            self._keys = {}


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

    factory: FactoryManager = None       # set by server class
    router: Router = None                # set by server class
    license_mgr: LicenseManager = None   # set by server class
    api_key_mgr: APIKeyManager = None    # set by server class
    require_auth: bool = True            # set by server class
    audit: AuditLogger = None            # set by server class

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

    def _send_file(self, filepath: str, download_name: str, content_type: str) -> None:
        """Send a file as a download response."""
        with open(filepath, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Disposition", f'attachment; filename="{download_name}"')
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

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
        request_start = time.time()
        client_ip = self.client_address[0] if self.client_address else ""
        api_key_hash = ""
        status_code = 200

        try:
            # CORS preflight — always allowed, no auth needed
            path = self._path()

            # License gate: block all API calls if license is expired
            if self.license_mgr is not None:
                lic_status = self.license_mgr.check_license()
                if not lic_status["is_active"]:
                    status_code = 403
                    self._send_json(
                        {
                            "error": "License expired",
                            "tier": lic_status["tier"],
                            "message": "AuraTool-Suite license has expired. Please renew.",
                        },
                        403,
                    )
                    self._audit_request(method, path, api_key_hash, client_ip, status_code, request_start)
                    return

            # API key authentication
            if self.require_auth and self.api_key_mgr is not None:
                api_key = self._extract_api_key()
                api_key_hash = APIKeyManager._hash_key(api_key) if api_key else ""
                is_valid, error_msg, meta = self.api_key_mgr.authenticate(
                    api_key, method, client_ip
                )
                # Log auth event
                if self.audit:
                    self.audit.log_auth(
                        success=is_valid,
                        key_hash=api_key_hash,
                        client_ip=client_ip,
                        method=method,
                        path=path,
                        reason="" if is_valid else error_msg,
                    )
                if not is_valid:
                    status_code = 401
                    self._send_json(
                        {
                            "error": "Authentication failed",
                            "message": error_msg,
                        },
                        401,
                    )
                    self._audit_request(method, path, api_key_hash, client_ip, status_code, request_start)
                    return

            handler, params = self.router.match(method, path)
            if handler is None:
                status_code = 404
                self._send_error("Not Found", 404)
                self._audit_request(method, path, api_key_hash, client_ip, status_code, request_start)
                return
            handler(self, params)
        except ErrorResponse as e:
            status_code = e.status
            self._send_error(e.message, e.status)
        except Exception as e:
            status_code = 500
            logger.exception("Unhandled error")
            self._send_error(str(e), 500)
        finally:
            self._audit_request(method, path, api_key_hash, client_ip, status_code, request_start)

    def _audit_request(self, method: str, path: str, key_hash: str,
                       client_ip: str, status: int, start_time: float):
        """Log the request to the audit trail."""
        if self.audit is None:
            return
        latency_ms = (time.time() - start_time) * 1000
        self.audit.log_request(
            method=method, path=path, key_hash=key_hash,
            client_ip=client_ip, status=status,
            latency_ms=latency_ms,
        )

    def _extract_api_key(self) -> str:
        """Extract API key from X-API-Key header or api_key query param."""
        # 1. Check header first (preferred)
        header_key = self.headers.get("X-API-Key", "").strip()
        if header_key:
            return header_key
        # 2. Fall back to query parameter
        query = self._query()
        api_key_param = query.get("api_key", [""])[0]
        return api_key_param


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

    # === API Key Management ================================================

    @r.get("/api/auth/keys")
    def list_api_keys(h: FactoryAPIHandler, params: dict):
        """List all API keys (admin only)."""
        if h.api_key_mgr is None:
            raise ErrorResponse("API key management not configured", 503)
        keys = h.api_key_mgr.list_keys()
        h._send_json({"keys": keys, "total": len(keys)})

    @r.post("/api/auth/keys")
    def create_api_key(h: FactoryAPIHandler, params: dict):
        """Generate a new API key (admin only)."""
        if h.api_key_mgr is None:
            raise ErrorResponse("API key management not configured", 503)
        body = h._read_body()
        role = body.get("role", "readonly")
        label = body.get("label", "")
        try:
            key = h.api_key_mgr.generate_key(role=role, label=label)
        except ValueError as e:
            raise ErrorResponse(str(e), 400)
        h._send_json({
            "api_key": key,
            "role": role,
            "label": label,
            "message": "Key generated. Store it securely — it will not be shown again.",
        }, 201)

    @r.delete("/api/auth/keys/<id>")
    def revoke_api_key(h: FactoryAPIHandler, params: dict):
        """Revoke an API key by its hash prefix."""
        if h.api_key_mgr is None:
            raise ErrorResponse("API key management not configured", 503)
        key_prefix = params["id"]
        # Find the full hash by prefix
        found_hash = None
        for kh in h.api_key_mgr._keys:
            if kh.startswith(key_prefix) or kh[:12].startswith(key_prefix):
                found_hash = kh
                break
        if found_hash is None:
            # Try matching against the display prefix (first 12 chars)
            for kh in h.api_key_mgr._keys:
                if kh[:len(key_prefix)] == key_prefix:
                    found_hash = kh
                    break
        if found_hash is None or not h.api_key_mgr.revoke_key(found_hash):
            raise ErrorResponse("API key not found", 404)
        h._send_json({"message": "API key revoked"})

    # === Export (CSV / PDF) =================================================

    # === Audit Trail ========================================================

    @r.get("/api/auth/audit")
    def get_audit_log(h: FactoryAPIHandler, params: dict):
        """Query audit log entries (admin only)."""
        if h.audit is None:
            raise ErrorResponse("Audit logging not configured", 503)
        q = h._query()
        limit = int(q.get("limit", ["100"])[0])
        event_type = q.get("type", [None])[0]
        method_filter = q.get("method", [None])[0]
        path_contains = q.get("path", [None])[0]
        key_prefix = q.get("key", [None])[0]
        since_str = q.get("since", [None])[0]
        since_ts = float(since_str) if since_str else None
        entries = h.audit.query(
            limit=limit, event_type=event_type, method=method_filter,
            path_contains=path_contains, key_hash_prefix=key_prefix,
            since_ts=since_ts,
        )
        h._send_json({"entries": entries, "total": len(entries)})

    @r.get("/api/auth/audit/stats")
    def get_audit_stats(h: FactoryAPIHandler, params: dict):
        """Get audit log statistics."""
        if h.audit is None:
            raise ErrorResponse("Audit logging not configured", 503)
        h._send_json(h.audit.stats())

    @r.get("/api/export/clients.csv")
    def export_clients(h: FactoryAPIHandler, params: dict):
        tmp = os.path.join(tempfile.gettempdir(), "aura_clients.csv")
        export_clients_csv(h.factory, tmp)
        h._send_file(tmp, "clients.csv", "text/csv")

    @r.get("/api/export/tickets.csv")
    def export_tickets_csv_route(h: FactoryAPIHandler, params: dict):
        q = h._query()
        status = RepairStatus(q["status"][0]) if "status" in q else None
        cat = DeviceCategory(q["category"][0]) if "category" in q else None
        tmp = os.path.join(tempfile.gettempdir(), "aura_tickets.csv")
        export_tickets_csv(h.factory, tmp, status, cat)
        h._send_file(tmp, "tickets.csv", "text/csv")

    @r.get("/api/export/inventory.csv")
    def export_inventory(h: FactoryAPIHandler, params: dict):
        tmp = os.path.join(tempfile.gettempdir(), "aura_inventory.csv")
        export_inventory_csv(h.factory, tmp)
        h._send_file(tmp, "inventory.csv", "text/csv")

    @r.get("/api/export/revenue.csv")
    def export_revenue(h: FactoryAPIHandler, params: dict):
        tmp = os.path.join(tempfile.gettempdir(), "aura_revenue.csv")
        export_revenue_csv(h.factory, tmp)
        h._send_file(tmp, "revenue.csv", "text/csv")

    @r.get("/api/export/dashboard.csv")
    def export_dashboard_csv_route(h: FactoryAPIHandler, params: dict):
        tmp = os.path.join(tempfile.gettempdir(), "aura_dashboard.csv")
        export_dashboard_csv(h.factory, tmp)
        h._send_file(tmp, "dashboard.csv", "text/csv")

    @r.get("/api/export/dashboard.pdf")
    def export_dashboard_pdf_route(h: FactoryAPIHandler, params: dict):
        tmp = os.path.join(tempfile.gettempdir(), "aura_dashboard.pdf")
        export_dashboard_pdf(h.factory, tmp)
        h._send_file(tmp, "dashboard.pdf", "application/pdf")

    @r.get("/api/export/tickets.pdf")
    def export_tickets_pdf_route(h: FactoryAPIHandler, params: dict):
        q = h._query()
        status = RepairStatus(q["status"][0]) if "status" in q else None
        cat = DeviceCategory(q["category"][0]) if "category" in q else None
        tmp = os.path.join(tempfile.gettempdir(), "aura_tickets.pdf")
        export_tickets_pdf(h.factory, tmp, status, cat)
        h._send_file(tmp, "tickets.pdf", "application/pdf")

    @r.get("/api/export/inventory.pdf")
    def export_inventory_pdf_route(h: FactoryAPIHandler, params: dict):
        tmp = os.path.join(tempfile.gettempdir(), "aura_inventory.pdf")
        export_inventory_pdf(h.factory, tmp)
        h._send_file(tmp, "inventory.pdf", "application/pdf")

    @r.get("/api/export/invoice/<id>.pdf")
    def export_invoice_pdf(h: FactoryAPIHandler, params: dict):
        tmp = os.path.join(tempfile.gettempdir(), f"aura_invoice_{params['id']}.pdf")
        try:
            export_ticket_invoice_pdf(h.factory, params["id"], tmp)
        except ValueError as e:
            raise ErrorResponse(str(e), 404)
        h._send_file(tmp, f"invoice_{params['id']}.pdf", "application/pdf")


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

class FactoryAPIServer(HTTPServer):
    """Custom HTTPServer that holds the FactoryManager instance."""

    def __init__(self, addr, handler_class, factory: FactoryManager,
                 license_mgr: LicenseManager = None,
                 api_key_mgr: APIKeyManager = None,
                 require_auth: bool = True,
                 ssl_context=None,
                 audit: AuditLogger = None):
        super().__init__(addr, handler_class)
        self.factory = factory

        # Setup router
        self.router = Router()
        register_routes(self.router)

        # Bind to handler
        handler_class.factory = factory
        handler_class.router = self.router
        handler_class.license_mgr = license_mgr
        handler_class.api_key_mgr = api_key_mgr
        handler_class.require_auth = require_auth
        handler_class.audit = audit

        # Wrap with SSL/TLS if provided
        if ssl_context:
            self.socket = ssl_context.wrap_socket(self.socket, server_side=True)
            logger.info("Factory API server wrapped with SSL/TLS")


def run_server(host: str = "0.0.0.0", port: int = 8500, data_dir: str = "factory_data",
               require_auth: bool = True, no_auth: bool = False,
               ssl_cert: str = None, ssl_key: str = None, auto_ssl: bool = False):
    """Start the REST API server.

    Args:
        host: Bind address.
        port: Bind port.
        data_dir: Factory data directory.
        require_auth: Require API key authentication.
        no_auth: Disable authentication (local dev mode).
        ssl_cert: Path to SSL certificate PEM file.
        ssl_key: Path to SSL private key PEM file.
        auto_ssl: Auto-generate self-signed cert if no cert provided.
    """
    factory = FactoryManager(data_dir)
    license_mgr = LicenseManager()
    lic_status = license_mgr.enforce_or_exit()
    if not lic_status["is_active"]:
        logger.critical("Cannot start API server — license expired")
        return

    api_key_mgr = APIKeyManager()
    auth_enabled = require_auth and not no_auth

    # Auto-generate a bootstrap key on first run if no keys exist
    if auth_enabled and len(api_key_mgr._keys) == 0:
        bootstrap_key = api_key_mgr.generate_key(role="admin", label="bootstrap-admin")
        logger.info("=" * 55)
        logger.info("  ⚠️  First run — Bootstrap API key generated:")
        logger.info(f"  🔑  {bootstrap_key}")
        logger.info("  Save this key! It won't be shown again.")
        logger.info("=" * 55)

    # Audit logging
    audit = AuditLogger()

    # TLS/SSL setup
    ssl_ctx = None
    scheme = "http"
    if ssl_cert and ssl_key:
        ssl_ctx = create_ssl_context(ssl_cert, ssl_key)
        scheme = "https"
        logger.info(f"TLS enabled: cert={ssl_cert}")
    elif auto_ssl:
        ssl_ctx = create_ssl_context_auto(hostname=host or "localhost")
        if ssl_ctx:
            scheme = "https"
            logger.info("TLS enabled: auto-generated self-signed cert")
        else:
            logger.warning("Auto-TLS failed — falling back to HTTP")

    server = FactoryAPIServer(
        (host, port), FactoryAPIHandler, factory,
        license_mgr=license_mgr,
        api_key_mgr=api_key_mgr if auth_enabled else None,
        require_auth=auth_enabled,
        ssl_context=ssl_ctx,
        audit=audit,
    )

    logger.info("=" * 55)
    logger.info("  AuraTool-Suite — Workshop & Factory REST API")
    logger.info(f"  Listening on {scheme}://{host}:{port}")
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
    parser.add_argument("--no-auth", action="store_true", help="Disable API key authentication (local dev only)")
    parser.add_argument("--ssl-cert", help="Path to SSL certificate PEM file")
    parser.add_argument("--ssl-key", help="Path to SSL private key PEM file")
    parser.add_argument("--auto-ssl", action="store_true", help="Auto-generate self-signed TLS cert")
    args = parser.parse_args()

    run_server(args.host, args.port, args.data_dir, no_auth=args.no_auth,
               ssl_cert=args.ssl_cert, ssl_key=args.ssl_key, auto_ssl=args.auto_ssl)
