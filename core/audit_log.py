"""
AuraTool-Suite — API Audit Trail
==================================
Centralized request and event logging for the Factory REST API.

Logs every:
  - API request (method, path, key used, IP, status, latency)
  - Key lifecycle event (generated, revoked, failed auth)
  - License event (activation, expiration)

Storage: JSONL (one JSON object per line) for efficient append and grep.
Rotation: auto-rotate when file exceeds max size.

Usage:
    from core.audit_log import AuditLogger

    audit = AuditLogger(data_dir="~/.auratool")
    audit.log_request(method="GET", path="/api/clients", api_key_hash="...",
                      client_ip="127.0.0.1", status=200, latency_ms=12)
    audit.log_event("key_generated", key_hash="...", role="admin", label="prod")
    audit.query(limit=50, event_type="auth_failed")
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("AuraTool.Audit")


class AuditLogger:
    """
    Append-only JSONL audit logger with rotation and query support.

    Each log entry is a single JSON line:
    {
        "ts": 1700000000.0,
        "type": "request" | "key_event" | "auth_event",
        "method": "GET",
        "path": "/api/clients",
        "key_hash": "abc123...",
        "client_ip": "127.0.0.1",
        "status": 200,
        "latency_ms": 12,
        "detail": {}
    }
    """

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB per log file
    LOG_FILE = "audit.jsonl"
    ARCHIVE_SUFFIX = ".archived"

    def __init__(self, data_dir: str | None = None):
        self._data_dir = data_dir or self._default_data_dir()
        os.makedirs(self._data_dir, exist_ok=True)
        self._log_path = os.path.join(self._data_dir, self.LOG_FILE)

    @staticmethod
    def _default_data_dir() -> str:
        home = os.path.expanduser("~")
        if os.name == "nt":
            app_data = os.getenv("APPDATA", home)
            return os.path.join(app_data, ".auratool")
        return os.path.join(home, ".auratool")

    # ==================================================================
    #  WRITE API
    # ==================================================================

    def log_request(
        self,
        method: str,
        path: str,
        key_hash: str = "",
        client_ip: str = "",
        status: int = 200,
        latency_ms: float = 0,
        detail: dict | None = None,
    ) -> None:
        """Log an API request."""
        entry = {
            "ts": time.time(),
            "type": "request",
            "method": method,
            "path": path,
            "key_hash": key_hash[:16] + "..." if len(key_hash) > 16 else key_hash,
            "client_ip": client_ip,
            "status": status,
            "latency_ms": round(latency_ms, 2),
        }
        if detail:
            entry["detail"] = detail
        self._write(entry)

    def log_event(
        self,
        event_type: str,
        key_hash: str = "",
        client_ip: str = "",
        detail: dict | None = None,
    ) -> None:
        """Log a key lifecycle or system event."""
        entry = {
            "ts": time.time(),
            "type": "key_event",
            "event": event_type,
            "key_hash": key_hash[:16] + "..." if len(key_hash) > 16 else key_hash,
            "client_ip": client_ip,
        }
        if detail:
            entry["detail"] = detail
        self._write(entry)

    def log_auth(
        self,
        success: bool,
        key_hash: str = "",
        client_ip: str = "",
        method: str = "",
        path: str = "",
        reason: str = "",
    ) -> None:
        """Log an authentication attempt."""
        entry = {
            "ts": time.time(),
            "type": "auth_event",
            "success": success,
            "key_hash": key_hash[:16] + "..." if len(key_hash) > 16 else key_hash,
            "client_ip": client_ip,
            "method": method,
            "path": path,
        }
        if reason:
            entry["reason"] = reason
        self._write(entry)

    # ==================================================================
    #  QUERY API
    # ==================================================================

    def query(
        self,
        limit: int = 100,
        event_type: str | None = None,
        method: str | None = None,
        path_contains: str | None = None,
        since_ts: float | None = None,
        key_hash_prefix: str | None = None,
        status_min: int | None = None,
        status_max: int | None = None,
        include_archived: bool = False,
    ) -> list[dict]:
        """
        Query audit log entries with filters.

        Args:
            limit: Maximum entries to return (most recent first).
            event_type: Filter by type ("request", "key_event", "auth_event").
            method: Filter by HTTP method ("GET", "POST", etc.).
            path_contains: Filter paths containing this string.
            since_ts: Only entries after this timestamp.
            key_hash_prefix: Filter by key hash prefix.
            status_min: Minimum HTTP status code.
            status_max: Maximum HTTP status code.
            include_archived: Also search archived log files.

        Returns:
            List of matching entries, newest first.
        """
        entries = self._read_log(self._log_path)

        if include_archived:
            for f in sorted(Path(self._data_dir).glob(f"{self.LOG_FILE}{self.ARCHIVE_SUFFIX}*")):
                entries.extend(self._read_log(str(f)))

        # Apply filters
        if event_type:
            entries = [e for e in entries if e.get("type") == event_type]
        if method:
            entries = [e for e in entries if e.get("method") == method.upper()]
        if path_contains:
            entries = [e for e in entries if path_contains in e.get("path", "")]
        if since_ts:
            entries = [e for e in entries if e.get("ts", 0) >= since_ts]
        if key_hash_prefix:
            entries = [e for e in entries if e.get("key_hash", "").startswith(key_hash_prefix)]
        if status_min is not None:
            entries = [e for e in entries if e.get("status", 0) >= status_min]
        if status_max is not None:
            entries = [e for e in entries if e.get("status", 0) <= status_max]

        # Sort by timestamp descending, return limited
        entries.sort(key=lambda e: e.get("ts", 0), reverse=True)
        return entries[:limit]

    def stats(self) -> dict:
        """Return aggregate statistics from the audit log."""
        entries = self._read_log(self._log_path)
        total = len(entries)
        by_type: dict[str, int] = {}
        by_method: dict[str, int] = {}
        by_status: dict[int, int] = {}
        auth_attempts = 0
        auth_failures = 0
        unique_ips: set[str] = set()
        unique_keys: set[str] = set()

        for e in entries:
            t = e.get("type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1

            m = e.get("method", "")
            if m:
                by_method[m] = by_method.get(m, 0) + 1

            s = e.get("status")
            if s is not None:
                by_status[s] = by_status.get(s, 0) + 1

            if t == "auth_event":
                auth_attempts += 1
                if not e.get("success", True):
                    auth_failures += 1

            ip = e.get("client_ip", "")
            if ip:
                unique_ips.add(ip)

            kh = e.get("key_hash", "")
            if kh and kh != "":
                unique_keys.add(kh)

        return {
            "total_entries": total,
            "by_type": by_type,
            "by_method": by_method,
            "by_status": by_status,
            "auth_attempts": auth_attempts,
            "auth_failures": auth_failures,
            "unique_ips": len(unique_ips),
            "unique_keys": len(unique_keys),
        }

    def clear(self) -> int:
        """Clear the current audit log (archive it first). Returns count of archived entries."""
        if not os.path.exists(self._log_path):
            return 0

        count = sum(1 for _ in open(self._log_path))
        if count == 0:
            return 0

        # Archive current log
        archive_name = f"{self.LOG_FILE}{self.ARCHIVE_SUFFIX}.{int(time.time())}"
        archive_path = os.path.join(self._data_dir, archive_name)
        os.rename(self._log_path, archive_path)
        logger.info(f"Audit log archived: {archive_path} ({count} entries)")
        return count

    # ==================================================================
    #  INTERNAL
    # ==================================================================

    def _write(self, entry: dict) -> None:
        """Append a single JSONL entry with rotation."""
        self._rotate_if_needed()
        try:
            line = json.dumps(entry, default=str) + "\n"
            with open(self._log_path, "a") as f:
                f.write(line)
        except OSError as e:
            logger.error(f"Failed to write audit log: {e}")

    def _read_log(self, path: str) -> list[dict]:
        """Read all entries from a JSONL file."""
        entries = []
        if not os.path.exists(path):
            return entries
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue  # skip corrupt lines
        except OSError as e:
            logger.warning("Failed to read audit log %s: %s", path, e)
        return entries

    def _rotate_if_needed(self) -> None:
        """Rotate the log file if it exceeds max size."""
        if not os.path.exists(self._log_path):
            return
        try:
            if os.path.getsize(self._log_path) > self.MAX_FILE_SIZE:
                archive_name = f"{self.LOG_FILE}{self.ARCHIVE_SUFFIX}.{int(time.time())}"
                archive_path = os.path.join(self._data_dir, archive_name)
                os.rename(self._log_path, archive_path)
                logger.info(f"Audit log rotated: {archive_path}")
        except OSError as e:
            logger.warning("Failed to rotate audit log: %s", e)


