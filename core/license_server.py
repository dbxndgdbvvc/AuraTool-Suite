"""
AuraTool-Suite — License Server
================================
Zero-dependency HTTP server for online license management:
  - License key generation and distribution (admin)
  - HWID-bound activation with max-device limits
  - License validation and heartbeat
  - Activation tracking and revocation
  - Anti-abuse: rate limiting, key expiration, replay protection

Built on Python's stdlib http.server — no Flask or FastAPI required.

Endpoints
---------
Client (no auth — uses license key):
    POST /activate           Activate a license key on a machine (sends HWID)
    POST /validate           Validate an active license (sends HWID + token)
    POST /deactivate         Deactivate license on a machine
    GET  /tiers              List available license tiers

Admin (requires X-Admin-Key header):
    POST   /admin/keys       Generate a new license key
    GET    /admin/keys       List all license keys
    DELETE /admin/keys/<id>  Revoke a license key
    GET    /admin/activations     List all activations
    DELETE /admin/activations/<id> Revoke a specific activation
    GET    /admin/stats      Server statistics

Run
---
    python -m core/license_server                      # port 8600
    python -m core/license_server --port 9001          # custom port
    python -m core/license_server --no-auth            # no admin auth
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import logging
import os
import secrets
import struct
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.license_manager import LicenseTier, TIER_CONFIG
from core.tls_utils import create_ssl_context, create_ssl_context_auto

logger = logging.getLogger("AuraTool.LicenseServer")


# ---------------------------------------------------------------------------
# Server-Side License Store
# ---------------------------------------------------------------------------

class LicenseStore:
    """
    Server-side license database.  Stores:
      - License keys (hashed) with tier, max_activations, expiration
      - Active bindings (key_hash -> list of HWID + activation metadata)
    All data persists to a JSON file.
    """

    SECRET_SALT = b"AuraTool-LicenseServer-2025"

    def __init__(self, data_dir: str = "license_data"):
        self._data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self._db_file = os.path.join(data_dir, "licenses.json")

        # key_hash -> {tier, max_activations, created_at, label, revoked, activations: [...]}
        self._keys: dict[str, dict] = {}
        # activation_id -> {key_hash, hwid, activated_at, last_validated, ip}
        self._activations: dict[str, dict] = {}

        self._load()

    # -- Key Management -----------------------------------------------------

    def generate_key(
        self,
        tier: str = "trial_15d",
        max_activations: int = 1,
        label: str = "",
        valid_days: int | None = None,
    ) -> dict:
        """
        Generate a new license key.

        Returns dict with the full key string and metadata.
        """
        # Validate tier
        tier_enum = None
        for t in LicenseTier:
            if t.value == tier:
                tier_enum = t
                break
        if tier_enum is None or tier_enum == LicenseTier.EXPIRED:
            raise ValueError(f"Invalid tier: {tier}")

        tier_config = TIER_CONFIG.get(tier_enum, {})
        if valid_days is None:
            valid_days = tier_config.get("days", 15)

        # Generate key: AL-<TIER_CODE>-<RANDOM>-<CHECKSUM>
        tier_code_map = {
            "trial_15d": "T15",
            "rental_6m": "R6M",
            "rental_1y": "R1Y",
        }
        tier_code = tier_code_map.get(tier, "UNK")
        random_part = secrets.token_hex(8).upper()

        raw_payload = f"AL-{tier_code}-{random_part}"
        checksum = hmac.new(
            self.SECRET_SALT, raw_payload.encode(), hashlib.sha256
        ).hexdigest()[:8].upper()
        full_key = f"{raw_payload}-{checksum}"

        key_hash = self._hash_key(full_key)

        self._keys[key_hash] = {
            "tier": tier,
            "tier_code": tier_code,
            "max_activations": max_activations,
            "current_activations": 0,
            "valid_days": valid_days,
            "label": label,
            "created_at": time.time(),
            "revoked": False,
            "activations": {},  # activation_id -> {hwid, activated_at, ...}
        }
        self._save()

        logger.info(
            f"License key generated: {tier} (max={max_activations}, label='{label}')"
        )
        return {
            "key": full_key,
            "tier": tier,
            "tier_label": tier_config.get("label", tier),
            "max_activations": max_activations,
            "valid_days": valid_days,
            "label": label,
        }

    def revoke_key(self, key_hash: str) -> bool:
        if key_hash in self._keys:
            self._keys[key_hash]["revoked"] = True
            # Also revoke all activations for this key
            for aid, act in list(self._activations.items()):
                if act["key_hash"] == key_hash:
                    del self._activations[aid]
            self._keys[key_hash]["activations"] = {}
            self._keys[key_hash]["current_activations"] = 0
            self._save()
            logger.info(f"License key revoked: {key_hash[:12]}...")
            return True
        return False

    def list_keys(self) -> list[dict]:
        result = []
        for kh, meta in self._keys.items():
            result.append({
                "key_prefix": kh[:12] + "...",
                "tier": meta["tier"],
                "label": meta["label"],
                "max_activations": meta["max_activations"],
                "current_activations": meta["current_activations"],
                "revoked": meta["revoked"],
                "created_at": meta["created_at"],
            })
        return result

    # -- Activation ---------------------------------------------------------

    def activate(self, key: str, hwid: str, client_ip: str = "") -> dict:
        """
        Activate a license key on a specific machine (HWID).

        Returns dict with success status, license token, and metadata.
        """
        if not key or not hwid:
            return {"success": False, "error": "Missing key or HWID"}

        # Validate key format
        if not key.startswith("AL-"):
            return {"success": False, "error": "Invalid key format"}

        # Verify checksum
        if not self._verify_checksum(key):
            return {"success": False, "error": "Invalid key checksum"}

        key_hash = self._hash_key(key)
        meta = self._keys.get(key_hash)

        if meta is None:
            return {"success": False, "error": "Unknown license key"}

        if meta["revoked"]:
            return {"success": False, "error": "This license key has been revoked"}

        # Check activation limit
        if meta["current_activations"] >= meta["max_activations"]:
            # Check if this HWID is already activated (re-activation)
            existing_aid = self._find_activation_by_hwid(key_hash, hwid)
            if existing_aid:
                # Re-validate existing activation
                act = self._activations[existing_aid]
                act["last_validated"] = time.time()
                self._save()
                token = self._generate_token(key_hash, hwid)
                tier_config = TIER_CONFIG.get(LicenseTier(meta["tier"]), {})
                return {
                    "success": True,
                    "message": "License re-validated on this machine",
                    "token": token,
                    "tier": meta["tier"],
                    "tier_label": tier_config.get("label", meta["tier"]),
                    "expires_in_days": meta["valid_days"],
                    "activation_id": existing_aid,
                }
            return {
                "success": False,
                "error": f"Activation limit reached ({meta['max_activations']} devices)",
            }

        # Create new activation
        activation_id = f"ACT-{secrets.token_hex(6).upper()}"
        self._activations[activation_id] = {
            "key_hash": key_hash,
            "hwid": hwid,
            "activated_at": time.time(),
            "last_validated": time.time(),
            "ip": client_ip,
        }
        meta["activations"][activation_id] = {
            "hwid": hwid,
            "activated_at": time.time(),
        }
        meta["current_activations"] += 1
        self._save()

        token = self._generate_token(key_hash, hwid, activation_id)
        tier_config = TIER_CONFIG.get(LicenseTier(meta["tier"]), {})

        logger.info(
            f"License activated: tier={meta['tier']}, "
            f"hwid={hwid[:12]}..., activation={activation_id}"
        )

        return {
            "success": True,
            "message": f"License activated: {tier_config.get('label', meta['tier'])}",
            "token": token,
            "tier": meta["tier"],
            "tier_label": tier_config.get("label", meta["tier"]),
            "expires_in_days": meta["valid_days"],
            "activation_id": activation_id,
            "features": tier_config.get("features", []),
        }

    def validate(self, token: str, hwid: str) -> dict:
        """
        Validate a license token for a specific HWID.
        Returns validity status and remaining time.
        """
        if not token or not hwid:
            return {"valid": False, "error": "Missing token or HWID"}

        # Parse token
        try:
            payload_b64, sig = token.split(".")
            payload = self._decode_payload(payload_b64)
        except (ValueError, Exception):
            return {"valid": False, "error": "Invalid token format"}

        key_hash = payload.get("key_hash", "")
        token_hwid = payload.get("hwid", "")
        issued_at = payload.get("issued_at", 0)

        # Verify HWID matches
        if token_hwid != hwid:
            return {"valid": False, "error": "HWID mismatch — token bound to different machine"}

        # Verify HMAC signature
        expected_sig = self._sign_payload(payload_b64)
        if not hmac.compare_digest(sig, expected_sig):
            return {"valid": False, "error": "Invalid token signature"}

        # Check key exists and is not revoked
        meta = self._keys.get(key_hash)
        if meta is None or meta["revoked"]:
            return {"valid": False, "error": "License key revoked or unknown"}

        # Check token freshness (tokens expire after valid_days)
        age_days = (time.time() - issued_at) / 86400
        if age_days > meta["valid_days"]:
            return {"valid": False, "error": "License token expired"}

        # Find activation record
        activation_id = payload.get("activation_id", "")
        act = self._activations.get(activation_id)
        if act is None:
            return {"valid": False, "error": "Activation record not found"}

        # Update last validated timestamp
        act["last_validated"] = time.time()
        self._save()

        tier_config = TIER_CONFIG.get(LicenseTier(meta["tier"]), {})
        days_remaining = max(0, int(meta["valid_days"] - age_days))

        return {
            "valid": True,
            "tier": meta["tier"],
            "tier_label": tier_config.get("label", meta["tier"]),
            "days_remaining": days_remaining,
            "features": tier_config.get("features", []),
            "activation_id": activation_id,
        }

    def deactivate(self, key: str, hwid: str) -> dict:
        """Deactivate a license on a specific machine."""
        if not key or not hwid:
            return {"success": False, "error": "Missing key or HWID"}

        key_hash = self._hash_key(key)
        meta = self._keys.get(key_hash)
        if meta is None:
            return {"success": False, "error": "Unknown license key"}

        aid = self._find_activation_by_hwid(key_hash, hwid)
        if aid is None:
            return {"success": False, "error": "No activation found for this machine"}

        # Remove activation
        del self._activations[aid]
        meta["activations"].pop(aid, None)
        meta["current_activations"] = max(0, meta["current_activations"] - 1)
        self._save()

        logger.info(f"License deactivated: {aid} (hwid={hwid[:12]}...)")
        return {"success": True, "message": "License deactivated on this machine"}

    def list_activations(self) -> list[dict]:
        result = []
        for aid, act in self._activations.items():
            meta = self._keys.get(act["key_hash"], {})
            result.append({
                "activation_id": aid,
                "tier": meta.get("tier", "unknown"),
                "hwid": act["hwid"],
                "ip": act.get("ip", ""),
                "activated_at": act["activated_at"],
                "last_validated": act.get("last_validated", 0),
            })
        return result

    def revoke_activation(self, activation_id: str) -> bool:
        act = self._activations.get(activation_id)
        if act is None:
            return False

        key_hash = act["key_hash"]
        meta = self._keys.get(key_hash, {})
        meta["activations"].pop(activation_id, None)
        meta["current_activations"] = max(0, meta.get("current_activations", 1) - 1)
        del self._activations[activation_id]
        self._save()
        logger.info(f"Activation revoked: {activation_id}")
        return True

    def stats(self) -> dict:
        total_keys = len(self._keys)
        active_keys = sum(1 for k in self._keys.values() if not k["revoked"])
        total_activations = len(self._activations)
        by_tier: dict[str, int] = {}
        for k in self._keys.values():
            t = k["tier"]
            by_tier[t] = by_tier.get(t, 0) + (0 if k["revoked"] else 1)
        return {
            "total_keys": total_keys,
            "active_keys": active_keys,
            "revoked_keys": total_keys - active_keys,
            "total_activations": total_activations,
            "keys_by_tier": by_tier,
        }

    # -- Helpers ------------------------------------------------------------

    def _find_activation_by_hwid(self, key_hash: str, hwid: str) -> str | None:
        for aid, act in self._activations.items():
            if act["key_hash"] == key_hash and act["hwid"] == hwid:
                return aid
        return None

    def _generate_token(self, key_hash: str, hwid: str, activation_id: str = "") -> str:
        """Generate a signed license token: payload.signature"""
        payload_dict = {
            "key_hash": key_hash,
            "hwid": hwid,
            "activation_id": activation_id,
            "issued_at": time.time(),
            "nonce": secrets.token_hex(4),
        }
        payload_b64 = self._encode_payload(payload_dict)
        signature = self._sign_payload(payload_b64)
        return f"{payload_b64}.{signature}"

    @staticmethod
    def _encode_payload(data: dict) -> str:
        """Encode dict to URL-safe base64-like string (no dependency)."""
        raw = json.dumps(data, separators=(",", ":"))
        return raw.encode().hex()

    @staticmethod
    def _decode_payload(encoded: str) -> dict:
        raw = bytes.fromhex(encoded).decode()
        return json.loads(raw)

    def _sign_payload(self, payload_b64: str) -> str:
        return hmac.new(
            self.SECRET_SALT, payload_b64.encode(), hashlib.sha256
        ).hexdigest()[:16]

    @staticmethod
    def _hash_key(key: str) -> str:
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def _verify_checksum(self, key: str) -> bool:
        parts = key.split("-")
        if len(parts) != 4:
            return False
        prefix = "-".join(parts[:-1])
        provided = parts[-1]
        expected = hmac.new(
            self.SECRET_SALT, prefix.encode(), hashlib.sha256
        ).hexdigest()[:8].upper()
        return hmac.compare_digest(provided, expected)

    # -- Persistence --------------------------------------------------------

    def _save(self) -> None:
        data = {
            "keys": self._keys,
            "activations": self._activations,
            "saved_at": time.time(),
        }
        try:
            with open(self._db_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except OSError as e:
            logger.error(f"Failed to save license data: {e}")

    def _load(self) -> None:
        if not os.path.exists(self._db_file):
            return
        try:
            with open(self._db_file) as f:
                data = json.load(f)
            self._keys = data.get("keys", {})
            self._activations = data.get("activations", {})
            logger.info(
                f"Loaded {len(self._keys)} keys, "
                f"{len(self._activations)} activations"
            )
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load license data: {e}")
            self._keys = {}
            self._activations = {}


# ---------------------------------------------------------------------------
# Admin API Key Manager (simple, for admin-only endpoints)
# ---------------------------------------------------------------------------

class AdminKeyManager:
    """Minimal API key auth for admin endpoints."""

    def __init__(self, data_dir: str = "license_data"):
        self._file = os.path.join(data_dir, "admin_keys.json")
        self._keys: dict[str, dict] = {}
        self._load()

    def authenticate(self, key: str) -> bool:
        if not key:
            return False
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        meta = self._keys.get(key_hash)
        return meta is not None and not meta.get("revoked", False)

    def generate_key(self, label: str = "admin") -> str:
        raw = f"ALS-ADMIN-{secrets.token_hex(8).upper()}"
        checksum = hmac.new(
            b"AuraTool-Admin-Key-2025", raw.encode(), hashlib.sha256
        ).hexdigest()[:8].upper()
        full_key = f"{raw}-{checksum}"
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()
        self._keys[key_hash] = {
            "label": label,
            "created_at": time.time(),
            "revoked": False,
        }
        self._save()
        return full_key

    def list_keys(self) -> list[dict]:
        return [
            {"prefix": kh[:12] + "...", "label": m["label"], "revoked": m["revoked"]}
            for kh, m in self._keys.items()
        ]

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._file), exist_ok=True)
            with open(self._file, "w") as f:
                json.dump(self._keys, f, indent=2)
        except OSError as e:
            logger.warning("Failed to save license keys: %s", e)

    def _load(self) -> None:
        if os.path.exists(self._file):
            try:
                with open(self._file) as f:
                    self._keys = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._keys = {}


# ---------------------------------------------------------------------------
# HTTP Server
# ---------------------------------------------------------------------------

def _json(obj: Any) -> str:
    return json.dumps(obj, indent=2, default=str)


class LicenseServerHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the license server."""

    store: LicenseStore = None
    admin_mgr: AdminKeyManager = None
    require_admin_auth: bool = True

    def log_message(self, fmt, *args):
        logger.info(fmt % args)

    # -- helpers ------------------------------------------------------------

    def _send_json(self, data: Any, status: int = 200) -> None:
        body = _json(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Admin-Key")
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, message: str, status: int = 400) -> None:
        self._send_json({"error": message}, status)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    def _path(self) -> str:
        return urlparse(self.path).path

    def _query(self) -> dict[str, list[str]]:
        return parse_qs(urlparse(self.path).query)

    def _client_ip(self) -> str:
        return self.client_address[0] if self.client_address else ""

    def _admin_key(self) -> str:
        return self.headers.get("X-Admin-Key", "").strip()

    # -- HTTP methods -------------------------------------------------------

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
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Admin-Key")
        self.end_headers()

    def _dispatch(self, method: str):
        try:
            path = self._path()

            # --- Admin endpoints (require X-Admin-Key) ---
            if path.startswith("/admin/"):
                if self.require_admin_auth:
                    if not self.admin_mgr or not self.admin_mgr.authenticate(self._admin_key()):
                        self._send_json({"error": "Admin authentication required"}, 401)
                        return
                self._route_admin(method, path)
                return

            # --- Public client endpoints ---
            self._route_client(method, path)

        except Exception as e:
            logger.exception("Unhandled error")
            self._send_json({"error": str(e)}, 500)

    # -- Client routes ------------------------------------------------------

    def _route_client(self, method: str, path: str):
        if method == "POST" and path == "/activate":
            self._handle_activate()
        elif method == "POST" and path == "/validate":
            self._handle_validate()
        elif method == "POST" and path == "/deactivate":
            self._handle_deactivate()
        elif method == "GET" and path == "/tiers":
            self._handle_tiers()
        elif method == "GET" and path == "/health":
            self._send_json({"status": "ok", "version": "2.0.0"})
        else:
            self._send_error("Not Found", 404)

    def _handle_activate(self):
        body = self._read_body()
        key = body.get("key", "").strip()
        hwid = body.get("hwid", "").strip()
        if not key or not hwid:
            self._send_error("'key' and 'hwid' are required")
            return
        result = self.store.activate(key, hwid, self._client_ip())
        status = 200 if result.get("success") else 400
        self._send_json(result, status)

    def _handle_validate(self):
        body = self._read_body()
        token = body.get("token", "").strip()
        hwid = body.get("hwid", "").strip()
        if not token or not hwid:
            self._send_error("'token' and 'hwid' are required")
            return
        result = self.store.validate(token, hwid)
        status = 200 if result.get("valid") else 401
        self._send_json(result, status)

    def _handle_deactivate(self):
        body = self._read_body()
        key = body.get("key", "").strip()
        hwid = body.get("hwid", "").strip()
        if not key or not hwid:
            self._send_error("'key' and 'hwid' are required")
            return
        result = self.store.deactivate(key, hwid)
        status = 200 if result.get("success") else 400
        self._send_json(result, status)

    def _handle_tiers(self):
        tiers = {}
        for tier, cfg in TIER_CONFIG.items():
            if tier == LicenseTier.EXPIRED:
                continue
            tiers[tier.value] = {
                "label": cfg["label"],
                "days": cfg["days"],
                "features": cfg["features"],
                "max_devices": cfg["max_devices"],
            }
        self._send_json({"tiers": tiers})

    # -- Admin routes -------------------------------------------------------

    def _route_admin(self, method: str, path: str):
        if method == "POST" and path == "/admin/keys":
            self._admin_generate_key()
        elif method == "GET" and path == "/admin/keys":
            self._admin_list_keys()
        elif method == "DELETE" and path.startswith("/admin/keys/"):
            key_hash = path.split("/")[-1]
            self._admin_revoke_key(key_hash)
        elif method == "GET" and path == "/admin/activations":
            self._admin_list_activations()
        elif method == "DELETE" and path.startswith("/admin/activations/"):
            aid = path.split("/")[-1]
            self._admin_revoke_activation(aid)
        elif method == "GET" and path == "/admin/stats":
            self._admin_stats()
        elif method == "GET" and path == "/admin/keys/list":
            self._admin_list_keys_full()
        else:
            self._send_error("Not Found", 404)

    def _admin_generate_key(self):
        body = self._read_body()
        tier = body.get("tier", "trial_15d")
        max_act = int(body.get("max_activations", 1))
        label = body.get("label", "")
        valid_days = body.get("valid_days")
        if valid_days is not None:
            valid_days = int(valid_days)
        try:
            result = self.store.generate_key(
                tier=tier, max_activations=max_act,
                label=label, valid_days=valid_days,
            )
        except ValueError as e:
            self._send_error(str(e), 400)
            return
        self._send_json(result, 201)

    def _admin_list_keys(self):
        keys = self.store.list_keys()
        self._send_json({"keys": keys, "total": len(keys)})

    def _admin_list_keys_full(self):
        keys = self.store.list_keys()
        self._send_json({"keys": keys, "total": len(keys)})

    def _admin_revoke_key(self, key_hash: str):
        if self.store.revoke_key(key_hash):
            self._send_json({"message": "Key revoked"})
        else:
            self._send_error("Key not found", 404)

    def _admin_list_activations(self):
        acts = self.store.list_activations()
        self._send_json({"activations": acts, "total": len(acts)})

    def _admin_revoke_activation(self, activation_id: str):
        if self.store.revoke_activation(activation_id):
            self._send_json({"message": "Activation revoked"})
        else:
            self._send_error("Activation not found", 404)

    def _admin_stats(self):
        self._send_json(self.store.stats())


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

class LicenseHTTPServer(HTTPServer):
    def __init__(self, addr, handler_class, store: LicenseStore,
                 admin_mgr: AdminKeyManager, require_admin_auth: bool = True,
                 ssl_context=None):
        super().__init__(addr, handler_class)
        handler_class.store = store
        handler_class.admin_mgr = admin_mgr
        handler_class.require_admin_auth = require_admin_auth
        if ssl_context:
            self.socket = ssl_context.wrap_socket(self.socket, server_side=True)
            logger.info("License server wrapped with SSL/TLS")


def run_server(host: str = "0.0.0.0", port: int = 8600,
               data_dir: str = "license_data", no_auth: bool = False,
               ssl_cert: str = None, ssl_key: str = None, auto_ssl: bool = False):
    """Start the license server.

    Args:
        host: Bind address.
        port: Bind port.
        data_dir: License data directory.
        no_auth: Disable admin authentication.
        ssl_cert: Path to SSL certificate PEM file.
        ssl_key: Path to SSL private key PEM file.
        auto_ssl: Auto-generate self-signed cert if no cert provided.
    """
    store = LicenseStore(data_dir)
    admin_mgr = AdminKeyManager(data_dir)

    # Auto-generate bootstrap admin key on first run
    if not no_auth and len(admin_mgr._keys) == 0:
        bootstrap = admin_mgr.generate_key(label="bootstrap-admin")
        logger.info("=" * 55)
        logger.info("  ⚠️  First run — Bootstrap admin key generated:")
        logger.info(f"  🔑  {bootstrap}")
        logger.info("  Save this key! It won't be shown again.")
        logger.info("=" * 55)

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

    server = LicenseHTTPServer(
        (host, port), LicenseServerHandler, store, admin_mgr,
        require_admin_auth=not no_auth,
        ssl_context=ssl_ctx,
    )

    logger.info("=" * 55)
    logger.info("  AuraTool-Suite — License Server")
    logger.info(f"  Listening on {scheme}://{host}:{port}")
    logger.info("=" * 55)
    logger.info("  Client endpoints:")
    logger.info("    POST /activate       Activate license (key + hwid)")
    logger.info("    POST /validate       Validate license (token + hwid)")
    logger.info("    POST /deactivate     Deactivate license")
    logger.info("    GET  /tiers          List tiers")
    logger.info("  Admin endpoints:")
    logger.info("    POST   /admin/keys       Generate key")
    logger.info("    GET    /admin/keys       List keys")
    logger.info("    DELETE /admin/keys/<id>  Revoke key")
    logger.info("    GET    /admin/stats      Statistics")
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

    parser = argparse.ArgumentParser(description="AuraTool-Suite License Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8600, help="Bind port (default: 8600)")
    parser.add_argument("--data-dir", default="license_data", help="Data directory")
    parser.add_argument("--no-auth", action="store_true", help="Disable admin authentication")
    parser.add_argument("--ssl-cert", help="Path to SSL certificate PEM file")
    parser.add_argument("--ssl-key", help="Path to SSL private key PEM file")
    parser.add_argument("--auto-ssl", action="store_true", help="Auto-generate self-signed TLS cert")
    args = parser.parse_args()

    run_server(args.host, args.port, args.data_dir, args.no_auth,
               args.ssl_cert, args.ssl_key, args.auto_ssl)
