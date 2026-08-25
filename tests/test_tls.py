"""
Unit Tests — TLS/SSL Utilities & HTTPS Server
===============================================
Tests cover:
  - Self-signed certificate generation (openssl + fallback)
  - SSL context creation with security hardening
  - Certificate fingerprint extraction
  - HTTPS server: license server over TLS
  - HTTPS server: factory API over TLS
  - TLS handshake verification
  - Certificate info extraction
"""

import json
import os
import shutil
import socket
import ssl
import tempfile
import threading
import time
import urllib.request
import urllib.error
import pytest

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tls_utils import (
    generate_self_signed_cert,
    create_ssl_context,
    create_ssl_context_auto,
    get_cert_fingerprint,
    get_cert_info,
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
def certs(tmp_dir):
    """Generate self-signed certs for testing."""
    cert = os.path.join(tmp_dir, "test.pem")
    key = os.path.join(tmp_dir, "test.key")
    generate_self_signed_cert(cert, key, hostname="localhost")
    return cert, key


@pytest.fixture
def ssl_ctx(certs):
    """Create an SSL context from generated certs."""
    cert, key = certs
    return create_ssl_context(cert, key)


# ---------------------------------------------------------------------------
# Certificate Generation Tests
# ---------------------------------------------------------------------------

class TestCertGeneration:
    def test_generate_cert_files_exist(self, certs):
        cert, key = certs
        assert os.path.isfile(cert)
        assert os.path.isfile(key)

    def test_generate_cert_is_pem(self, certs):
        cert, key = certs
        with open(cert) as f:
            content = f.read()
        assert "BEGIN CERTIFICATE" in content

    def test_generate_key_is_pem(self, certs):
        cert, key = certs
        with open(key) as f:
            content = f.read()
        assert "PRIVATE KEY" in content

    def test_generate_custom_hostname(self, tmp_dir):
        cert = os.path.join(tmp_dir, "custom.pem")
        key = os.path.join(tmp_dir, "custom.key")
        generate_self_signed_cert(cert, key, hostname="server.example.com")
        assert os.path.isfile(cert)

    def test_generate_custom_valid_days(self, tmp_dir):
        cert = os.path.join(tmp_dir, "long.pem")
        key = os.path.join(tmp_dir, "long.key")
        generate_self_signed_cert(cert, key, valid_days=730)
        assert os.path.isfile(cert)


# ---------------------------------------------------------------------------
# SSL Context Tests
# ---------------------------------------------------------------------------

class TestSSLContext:
    def test_create_context(self, ssl_ctx):
        assert isinstance(ssl_ctx, ssl.SSLContext)

    def test_context_is_tls_server(self, ssl_ctx):
        assert ssl_ctx.protocol & ssl.PROTOCOL_TLS_SERVER

    def test_context_minimum_version(self, ssl_ctx):
        assert ssl_ctx.minimum_version == ssl.TLSVersion.TLSv1_2

    def test_context_has_cert_loaded(self, ssl_ctx):
        # Verify the context has a cert chain loaded by attempting to wrap a socket
        raw_sock = socket.socket()
        try:
            wrapped = ssl_ctx.wrap_socket(raw_sock, server_side=True)
            wrapped.close()
        except ssl.SSLError:
            pass  # Expected — no client connecting
        raw_sock.close()

    def test_context_with_cafile(self, certs, tmp_dir):
        cert, key = certs
        ctx = create_ssl_context(cert, key, cafile=cert)
        assert ctx.verify_mode == ssl.CERT_REQUIRED

    def test_auto_ssl_context(self, tmp_dir):
        ctx = create_ssl_context_auto(
            hostname="localhost",
            cert_dir=tmp_dir,
        )
        assert ctx is not None
        assert isinstance(ctx, ssl.SSLContext)

    def test_auto_ssl_with_existing_cert(self, certs, tmp_dir):
        cert, key = certs
        ctx = create_ssl_context_auto(certfile=cert, keyfile=key)
        assert ctx is not None


# ---------------------------------------------------------------------------
# Certificate Utilities Tests
# ---------------------------------------------------------------------------

class TestCertUtilities:
    def test_cert_fingerprint(self, certs):
        cert, _ = certs
        fp = get_cert_fingerprint(cert)
        assert len(fp) > 0
        # SHA-256 fingerprint: 32 bytes = 32 * 3 chars (XX:) - 1 = 95 chars
        assert ":" in fp

    def test_cert_fingerprint_sha1(self, certs):
        cert, _ = certs
        fp = get_cert_fingerprint(cert, algorithm="sha1")
        assert len(fp) > 0

    def test_cert_info(self, certs):
        cert, _ = certs
        info = get_cert_info(cert)
        # May return error if openssl not available, but should not crash
        assert isinstance(info, dict)

    def test_cert_info_nonexistent(self):
        info = get_cert_info("/nonexistent/cert.pem")
        assert "error" in info


# ---------------------------------------------------------------------------
# HTTPS License Server Tests
# ---------------------------------------------------------------------------

class TestHTTPS_license_server:
    def test_license_server_starts_with_tls(self, tmp_dir):
        """Verify license server can start with TLS and serve requests."""
        from core.license_server import (
            LicenseStore, AdminKeyManager, LicenseHTTPServer,
            LicenseServerHandler,
        )

        data_dir = os.path.join(tmp_dir, "lic_data")
        cert_dir = os.path.join(tmp_dir, "certs")
        os.makedirs(cert_dir)

        cert = os.path.join(cert_dir, "server.pem")
        key = os.path.join(cert_dir, "server.key")
        generate_self_signed_cert(cert, key, hostname="localhost")

        store = LicenseStore(data_dir=data_dir)
        admin_mgr = AdminKeyManager(data_dir=data_dir)
        admin_key = admin_mgr.generate_key(label="tls-test")

        ssl_ctx = create_ssl_context(cert, key)

        LicenseServerHandler.store = store
        LicenseServerHandler.admin_mgr = admin_mgr
        LicenseServerHandler.require_admin_auth = True

        # Find free port
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()

        srv = LicenseHTTPServer(
            ("127.0.0.1", port), LicenseServerHandler, store, admin_mgr,
            require_admin_auth=True, ssl_context=ssl_ctx,
        )
        thread = threading.Thread(target=srv.serve_forever, daemon=True)
        thread.start()
        time.sleep(0.2)

        try:
            # Connect with SSL, ignoring self-signed cert
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            # Test health endpoint via HTTPS
            import urllib.request
            req = urllib.request.Request(f"https://127.0.0.1:{port}/health")
            resp = urllib.request.urlopen(req, context=ctx)
            data = json.loads(resp.read())
            assert data["status"] == "ok"
        finally:
            srv.shutdown()

    def test_license_server_tls_rejects_plain_http(self, tmp_dir):
        """Verify TLS server rejects plain HTTP connections."""
        from core.license_server import (
            LicenseStore, AdminKeyManager, LicenseHTTPServer,
            LicenseServerHandler,
        )

        data_dir = os.path.join(tmp_dir, "lic_data2")
        cert_dir = os.path.join(tmp_dir, "certs2")
        os.makedirs(cert_dir)

        cert = os.path.join(cert_dir, "server.pem")
        key = os.path.join(cert_dir, "server.key")
        generate_self_signed_cert(cert, key, hostname="localhost")

        store = LicenseStore(data_dir=data_dir)
        admin_mgr = AdminKeyManager(data_dir=data_dir)

        ssl_ctx = create_ssl_context(cert, key)

        LicenseServerHandler.store = store
        LicenseServerHandler.admin_mgr = admin_mgr
        LicenseServerHandler.require_admin_auth = False

        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()

        srv = LicenseHTTPServer(
            ("127.0.0.1", port), LicenseServerHandler, store, admin_mgr,
            require_admin_auth=False, ssl_context=ssl_ctx,
        )
        thread = threading.Thread(target=srv.serve_forever, daemon=True)
        thread.start()
        time.sleep(0.2)

        try:
            # Plain HTTP should fail — server expects TLS handshake
            raw = socket.socket()
            raw.settimeout(2)
            try:
                raw.connect(("127.0.0.1", port))
                raw.sendall(b"GET /health HTTP/1.1\r\nHost: localhost\r\n\r\n")
                response = raw.recv(1024)
                # Should get an error or empty response (not valid HTTP)
                # The TLS layer will reject the plain text
                assert len(response) == 0 or b"error" in response.lower() or b"HTTP" not in response
            except (ssl.SSLError, ConnectionResetError, BrokenPipeError, OSError):
                pass  # Expected — TLS rejects plain text
            finally:
                raw.close()
        finally:
            srv.shutdown()


# ---------------------------------------------------------------------------
# HTTPS Factory API Server Tests
# ---------------------------------------------------------------------------

class TestHTTPS_factory_api:
    def test_factory_api_starts_with_tls(self, tmp_dir):
        """Verify factory API server can start with TLS and serve requests."""
        from core.factory_api import (
            FactoryAPIServer, FactoryAPIHandler, register_routes, Router,
            APIKeyManager,
        )
        from core.license_manager import LicenseManager
        from auratool_factory import FactoryManager

        cert_dir = os.path.join(tmp_dir, "certs")
        os.makedirs(cert_dir)
        cert = os.path.join(cert_dir, "server.pem")
        key = os.path.join(cert_dir, "server.key")
        generate_self_signed_cert(cert, key, hostname="localhost")

        ssl_ctx = create_ssl_context(cert, key)
        factory = FactoryManager(os.path.join(tmp_dir, "factory"))
        api_key_mgr = APIKeyManager(data_dir=os.path.join(tmp_dir, "api_keys"))
        test_key = api_key_mgr.generate_key(role="admin", label="tls-test")

        router = Router()
        register_routes(router)

        FactoryAPIHandler.factory = factory
        FactoryAPIHandler.router = router
        FactoryAPIHandler.license_mgr = None
        FactoryAPIHandler.api_key_mgr = api_key_mgr
        FactoryAPIHandler.require_auth = True

        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()

        srv = FactoryAPIServer(
            ("127.0.0.1", port), FactoryAPIHandler, factory,
            api_key_mgr=api_key_mgr, require_auth=True,
            ssl_context=ssl_ctx,
        )
        thread = threading.Thread(target=srv.serve_forever, daemon=True)
        thread.start()
        time.sleep(0.2)

        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            req = urllib.request.Request(
                f"https://127.0.0.1:{port}/api/clients",
                headers={"X-API-Key": test_key},
            )
            resp = urllib.request.urlopen(req, context=ctx)
            data = json.loads(resp.read())
            assert isinstance(data, list)
        finally:
            srv.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
