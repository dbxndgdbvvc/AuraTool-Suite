"""
AuraTool-Suite — API Key Management CLI
=========================================
Standalone command-line tool for managing API keys used by the
Factory REST API server.

Commands:
    list                  List all API keys
    generate              Generate a new API key
    revoke <hash_prefix>  Revoke an API key by hash prefix
    stats                 Show key statistics

Usage:
    python -m core.api_key_cli list
    python -m core.api_key_cli generate --role admin --label "my-key"
    python -m core.api_key_cli revoke abc123def456
    python -m core.api_key_cli stats

Options:
    --data-dir DIR   Custom data directory (default: ~/.auratool/)
    --json           Output in JSON format
"""

from __future__ import annotations

import argparse
import json
import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.factory_api import APIKeyManager
from core.audit_log import AuditLogger


# ---------------------------------------------------------------------------
# Output Formatting
# ---------------------------------------------------------------------------

def _print_table(keys: list[dict]) -> None:
    """Print keys as a formatted table."""
    if not keys:
        print("  (no keys found)")
        return

    # Header
    print(f"  {'HASH':<16} {'ROLE':<10} {'LABEL':<20} {'STATUS':<10} {'REQUESTS':<10} {'LAST USED'}")
    print("  " + "-" * 95)

    for k in keys:
        status = "🔴 REVOKED" if k["revoked"] else "🟢 Active"
        last_used = (
            datetime.fromtimestamp(k["last_used"]).strftime("%Y-%m-%d %H:%M")
            if k["last_used"] > 0
            else "never"
        )
        label = (k["label"][:18] + "..") if len(k["label"]) > 20 else k["label"]
        print(
            f"  {k['key_prefix']:<16} {k['role']:<10} {label:<20} "
            f"{status:<10} {k['request_count']:<10} {last_used}"
        )


def _print_key_generated(key: str, role: str, label: str) -> None:
    """Print a newly generated key with emphasis."""
    print()
    print("  ╔══════════════════════════════════════════════════════════════╗")
    print("  ║  ⚠️  NEW API KEY GENERATED — SAVE IT NOW!                   ║")
    print("  ╠══════════════════════════════════════════════════════════════╣")
    print(f"  ║  Key:    {key:<50} ║")
    print(f"  ║  Role:   {role:<50} ║")
    print(f"  ║  Label:  {label:<50} ║")
    print("  ╠══════════════════════════════════════════════════════════════╣")
    print("  ║  This key will NOT be shown again.                          ║")
    print("  ║  Use: X-API-Key header or ?api_key= query parameter         ║")
    print("  ╚══════════════════════════════════════════════════════════════╝")
    print()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_list(mgr: APIKeyManager, as_json: bool) -> None:
    """List all API keys."""
    keys = mgr.list_keys()
    if as_json:
        print(json.dumps(keys, indent=2, default=str))
    else:
        print(f"\n  API Keys ({len(keys)} total):\n")
        _print_table(keys)
        print()


def cmd_generate(mgr: APIKeyManager, role: str, label: str, as_json: bool) -> None:
    """Generate a new API key."""
    try:
        key = mgr.generate_key(role=role, label=label)
    except ValueError as e:
        print(f"  ❌ Error: {e}", file=sys.stderr)
        sys.exit(1)

    if as_json:
        print(json.dumps({
            "api_key": key,
            "role": role,
            "label": label,
            "message": "Store this key securely — it will not be shown again.",
        }, indent=2))
    else:
        _print_key_generated(key, role, label)


def cmd_revoke(mgr: APIKeyManager, key_prefix: str, as_json: bool) -> None:
    """Revoke an API key by its hash prefix."""
    # Find the full hash by prefix
    found_hash = None
    for kh in mgr._keys:
        if kh.startswith(key_prefix) or kh[:12].startswith(key_prefix):
            found_hash = kh
            break

    if found_hash is None:
        # Try partial match
        for kh in mgr._keys:
            if kh[:len(key_prefix)] == key_prefix:
                found_hash = kh
                break

    if found_hash is None:
        print(f"  ❌ No key found matching prefix: {key_prefix}", file=sys.stderr)
        sys.exit(1)

    if mgr.revoke_key(found_hash):
        if as_json:
            print(json.dumps({"success": True, "message": "Key revoked"}))
        else:
            print(f"  ✅ Key revoked: {found_hash[:12]}...")
    else:
        print(f"  ❌ Failed to revoke key", file=sys.stderr)
        sys.exit(1)


def cmd_stats(mgr: APIKeyManager, as_json: bool) -> None:
    """Show key statistics."""
    keys = mgr.list_keys()
    total = len(keys)
    active = sum(1 for k in keys if not k["revoked"])
    revoked = total - active
    total_requests = sum(k["request_count"] for k in keys)

    by_role: dict[str, int] = {}
    for k in keys:
        r = k["role"]
        by_role[r] = by_role.get(r, 0) + (0 if k["revoked"] else 1)

    stats = {
        "total_keys": total,
        "active_keys": active,
        "revoked_keys": revoked,
        "total_requests": total_requests,
        "by_role": by_role,
    }

    if as_json:
        print(json.dumps(stats, indent=2))
    else:
        print(f"\n  📊 API Key Statistics\n")
        print(f"  Total keys:      {total}")
        print(f"  Active keys:     {active}")
        print(f"  Revoked keys:    {revoked}")
        print(f"  Total requests:  {total_requests}")
        print(f"\n  By role:")
        for role, count in by_role.items():
            print(f"    {role:<12} {count}")
        print()


# ---------------------------------------------------------------------------
# Audit Commands
# ---------------------------------------------------------------------------

def cmd_audit(args, as_json: bool) -> None:
    """Query audit log entries."""
    audit = AuditLogger(data_dir=getattr(args, 'data_dir', None))
    entries = audit.query(
        limit=args.limit,
        event_type=args.event_type,
        method=args.method,
        path_contains=args.path,
        key_hash_prefix=args.key,
        since_ts=args.since,
    )
    if as_json:
        print(json.dumps(entries, indent=2, default=str))
    else:
        if not entries:
            print("  (no audit entries found)")
            return
        print(f"\n  Audit Log ({len(entries)} entries):\n")
        print(f"  {'TIME':<22} {'TYPE':<14} {'METHOD':<8} {'PATH':<30} {'STATUS':<8} {'IP':<16} {'KEY'}")
        print("  " + "-" * 115)
        for e in entries:
            ts = datetime.fromtimestamp(e.get("ts", 0)).strftime("%Y-%m-%d %H:%M:%S")
            etype = e.get("type", "")
            if etype == "request":
                method = e.get("method", "")
                path = e.get("path", "")
                status = str(e.get("status", ""))
                ip = e.get("client_ip", "")
                key = e.get("key_hash", "")
                print(f"  {ts:<22} {etype:<14} {method:<8} {path:<30} {status:<8} {ip:<16} {key}")
            elif etype == "auth_event":
                success = "✅" if e.get("success") else "❌"
                reason = e.get("reason", "")
                ip = e.get("client_ip", "")
                key = e.get("key_hash", "")
                print(f"  {ts:<22} {etype:<14} {'':8} {'':30} {success:<8} {ip:<16} {key}  {reason}")
            elif etype == "key_event":
                event = e.get("event", "")
                key = e.get("key_hash", "")
                detail = e.get("detail", {})
                detail_str = json.dumps(detail) if detail else ""
                print(f"  {ts:<22} {etype:<14} {'':8} {event:<30} {'':8} {'':16} {key}  {detail_str}")
        print()


def cmd_audit_stats(data_dir: str | None, as_json: bool) -> None:
    """Show audit log statistics."""
    audit = AuditLogger(data_dir=data_dir)
    stats = audit.stats()
    if as_json:
        print(json.dumps(stats, indent=2))
    else:
        print(f"\n  📊 Audit Log Statistics\n")
        print(f"  Total entries:    {stats['total_entries']}")
        print(f"  Auth attempts:    {stats['auth_attempts']}")
        print(f"  Auth failures:    {stats['auth_failures']}")
        print(f"  Unique IPs:       {stats['unique_ips']}")
        print(f"  Unique keys:      {stats['unique_keys']}")
        print(f"\n  By type:")
        for t, c in stats.get("by_type", {}).items():
            print(f"    {t:<20} {c}")
        print(f"\n  By method:")
        for m, c in stats.get("by_method", {}).items():
            print(f"    {m:<20} {c}")
        print()


def cmd_audit_clear(data_dir: str | None, as_json: bool) -> None:
    """Archive and clear the audit log."""
    audit = AuditLogger(data_dir=data_dir)
    count = audit.clear()
    if as_json:
        print(json.dumps({"archived": count, "message": "Audit log archived"}))
    else:
        print(f"  ✅ Audit log archived: {count} entries")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="AuraTool-Suite — API Key Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list                        List all keys
  %(prog)s generate --role admin -l "prod-key"  Generate admin key
  %(prog)s generate --role readonly    Generate read-only key
  %(prog)s revoke abc123def456         Revoke key by hash prefix
  %(prog)s stats                       Show statistics
  %(prog)s list --json                 JSON output
        """,
    )
    parser.add_argument("--data-dir", help="Custom data directory")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Shared --json flag for all subcommands
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="Output in JSON format")

    # audit
    audit_parser = subparsers.add_parser("audit", parents=[common], help="Query audit log")
    audit_parser.add_argument("--type", dest="event_type", help="Filter by type: request, key_event, auth_event")
    audit_parser.add_argument("--method", help="Filter by HTTP method (GET, POST, etc.)")
    audit_parser.add_argument("--path", help="Filter by path (contains match)")
    audit_parser.add_argument("--key", help="Filter by key hash prefix")
    audit_parser.add_argument("--since", type=float, help="Only entries after this Unix timestamp")
    audit_parser.add_argument("-n", "--limit", type=int, default=50, help="Max entries to show (default: 50)")

    # audit-stats
    subparsers.add_parser("audit-stats", parents=[common], help="Show audit log statistics")

    # audit-clear
    subparsers.add_parser("audit-clear", parents=[common], help="Archive and clear audit log")

    # list
    subparsers.add_parser("list", parents=[common], help="List all API keys")

    # generate
    gen_parser = subparsers.add_parser("generate", parents=[common], help="Generate a new API key")
    gen_parser.add_argument(
        "--role", "-r", default="readonly",
        choices=["admin", "readonly"],
        help="Key role (default: readonly)",
    )
    gen_parser.add_argument(
        "--label", "-l", default="",
        help="Label/description for the key",
    )

    # revoke
    revoke_parser = subparsers.add_parser("revoke", parents=[common], help="Revoke an API key")
    revoke_parser.add_argument("key_prefix", help="Key hash prefix (first 12+ chars)")

    # stats
    subparsers.add_parser("stats", parents=[common], help="Show key statistics")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # Initialize manager
    mgr = APIKeyManager(data_dir=args.data_dir)

    # Dispatch
    if args.command == "list":
        cmd_list(mgr, args.json)
    elif args.command == "generate":
        cmd_generate(mgr, args.role, args.label, args.json)
    elif args.command == "revoke":
        cmd_revoke(mgr, args.key_prefix, args.json)
    elif args.command == "stats":
        cmd_stats(mgr, args.json)
    elif args.command == "audit":
        cmd_audit(args, args.json)
    elif args.command == "audit-stats":
        cmd_audit_stats(args.data_dir, args.json)
    elif args.command == "audit-clear":
        cmd_audit_clear(args.data_dir, args.json)


if __name__ == "__main__":
    main()
