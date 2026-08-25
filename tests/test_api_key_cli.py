"""
Unit Tests — API Key Management CLI
=====================================
Tests cover:
  - list command (empty and populated)
  - generate command (admin and readonly)
  - revoke command (valid and invalid)
  - stats command
  - JSON output mode
  - Error handling
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.factory_api import APIKeyManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def mgr(tmp_dir):
    return APIKeyManager(data_dir=tmp_dir)


@pytest.fixture
def cli_runner(tmp_dir):
    """Return a helper to run the CLI as a subprocess."""
    cli_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "core", "api_key_cli.py",
    )

    def run(*args):
        cmd = [sys.executable, cli_path, "--data-dir", tmp_dir] + list(args)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result

    return run


# ---------------------------------------------------------------------------
# List Command Tests
# ---------------------------------------------------------------------------

class TestListCommand:
    def test_list_empty(self, cli_runner):
        result = cli_runner("list")
        assert result.returncode == 0
        assert "no keys found" in result.stdout.lower() or "0 total" in result.stdout

    def test_list_with_keys(self, mgr, cli_runner):
        mgr.generate_key(role="admin", label="test-key")
        result = cli_runner("list")
        assert result.returncode == 0
        assert "admin" in result.stdout.lower()

    def test_list_json(self, cli_runner):
        result = cli_runner("list", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)

    def test_list_json_with_keys(self, mgr, cli_runner):
        mgr.generate_key(role="admin", label="json-test")
        result = cli_runner("list", "--json")
        data = json.loads(result.stdout)
        assert len(data) >= 1
        assert data[0]["role"] == "admin"


# ---------------------------------------------------------------------------
# Generate Command Tests
# ---------------------------------------------------------------------------

class TestGenerateCommand:
    def test_generate_default_readonly(self, cli_runner):
        result = cli_runner("generate")
        assert result.returncode == 0
        assert "api_key" in result.stdout.lower() or "ATK-READONLY" in result.stdout

    def test_generate_admin(self, cli_runner):
        result = cli_runner("generate", "--role", "admin", "--label", "test-admin")
        assert result.returncode == 0
        assert "admin" in result.stdout.lower()

    def test_generate_json(self, cli_runner):
        result = cli_runner("generate", "--role", "admin", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "api_key" in data
        assert data["role"] == "admin"

    def test_generate_readonly(self, cli_runner):
        result = cli_runner("generate", "-r", "readonly", "-l", "viewer")
        assert result.returncode == 0
        assert "readonly" in result.stdout.lower()

    def test_generate_invalid_role(self, cli_runner):
        result = cli_runner("generate", "--role", "superadmin")
        assert result.returncode != 0


# ---------------------------------------------------------------------------
# Revoke Command Tests
# ---------------------------------------------------------------------------

class TestRevokeCommand:
    def test_revoke_valid_key(self, mgr, cli_runner):
        key = mgr.generate_key(role="admin", label="to-revoke")
        key_hash = APIKeyManager._hash_key(key)
        result = cli_runner("revoke", key_hash[:12])
        assert result.returncode == 0
        assert "revoked" in result.stdout.lower()

    def test_revoke_nonexistent(self, cli_runner):
        result = cli_runner("revoke", "nonexistent000")
        assert result.returncode != 0
        assert "no key found" in result.stderr.lower() or result.returncode != 0

    def test_revoke_json(self, mgr, cli_runner):
        key = mgr.generate_key(role="readonly")
        key_hash = APIKeyManager._hash_key(key)
        result = cli_runner("revoke", key_hash[:12], "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["success"] is True

    def test_revoke_prevents_auth(self, tmp_dir, cli_runner):
        # Create manager, generate key, then revoke via CLI
        mgr1 = APIKeyManager(data_dir=tmp_dir)
        key = mgr1.generate_key(role="admin")
        key_hash = APIKeyManager._hash_key(key)
        cli_runner("revoke", key_hash[:12])

        # Reload manager from disk to pick up CLI changes
        mgr2 = APIKeyManager(data_dir=tmp_dir)
        valid, _, _ = mgr2.authenticate(key)
        assert valid is False


# ---------------------------------------------------------------------------
# Stats Command Tests
# ---------------------------------------------------------------------------

class TestStatsCommand:
    def test_stats_empty(self, cli_runner):
        result = cli_runner("stats")
        assert result.returncode == 0
        assert "total keys" in result.stdout.lower() or "total_keys" in result.stdout

    def test_stats_with_data(self, mgr, cli_runner):
        mgr.generate_key(role="admin", label="k1")
        mgr.generate_key(role="readonly", label="k2")
        result = cli_runner("stats")
        assert result.returncode == 0
        assert "2" in result.stdout  # total keys

    def test_stats_json(self, cli_runner):
        result = cli_runner("stats", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "total_keys" in data
        assert "active_keys" in data
        assert "revoked_keys" in data

    def test_stats_after_revoke(self, mgr, cli_runner):
        key = mgr.generate_key(role="admin")
        key_hash = APIKeyManager._hash_key(key)
        mgr.revoke_key(key_hash)

        result = cli_runner("stats", "--json")
        data = json.loads(result.stdout)
        assert data["total_keys"] == 1
        assert data["revoked_keys"] == 1
        assert data["active_keys"] == 0


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------

class TestCLIIntegration:
    def test_full_workflow(self, cli_runner):
        """Full workflow: generate → list → revoke → stats."""
        # 1. Generate
        result = cli_runner("generate", "--role", "admin", "-l", "workflow-test", "--json")
        assert result.returncode == 0
        key_data = json.loads(result.stdout)
        key = key_data["api_key"]

        # 2. List (should show 1 key)
        result = cli_runner("list", "--json")
        keys = json.loads(result.stdout)
        assert len(keys) == 1
        assert keys[0]["role"] == "admin"

        # 3. Stats (should show 1 active)
        result = cli_runner("stats", "--json")
        stats = json.loads(result.stdout)
        assert stats["total_keys"] == 1
        assert stats["active_keys"] == 1

        # 4. Generate another
        cli_runner("generate", "-r", "readonly", "-l", "second-key")

        # 5. Stats (should show 2 active)
        result = cli_runner("stats", "--json")
        stats = json.loads(result.stdout)
        assert stats["total_keys"] == 2
        assert stats["active_keys"] == 2

    def test_custom_data_dir(self, tmp_dir):
        """Test --data-dir flag with a custom directory."""
        custom_dir = os.path.join(tmp_dir, "custom")
        cli_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "core", "api_key_cli.py",
        )
        result = subprocess.run(
            [sys.executable, cli_path, "--data-dir", custom_dir, "list"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        # Verify the data dir was created
        assert os.path.isdir(custom_dir)

    def test_help(self, cli_runner):
        result = cli_runner("--help")
        assert result.returncode == 0
        assert "AuraTool" in result.stdout or "api_key_cli" in result.stdout

    def test_no_command(self, cli_runner):
        result = cli_runner()
        assert result.returncode == 0
        assert "help" in result.stdout.lower() or "command" in result.stdout.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
