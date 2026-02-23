"""Tests for proxy-aware client IP extraction in rate limiting (SEC-007)."""

import pytest
from security.rate_limit_middleware import _extract_client_ip


def make_scope(client_ip="127.0.0.1", headers=None):
    """Build a minimal ASGI scope for testing."""
    return {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/test",
        "client": (client_ip, 12345),
        "headers": headers or [],
    }


class TestExtractClientIP:
    """SEC-007: Proxy-aware client IP extraction."""

    def test_default_uses_scope_client(self):
        """Default mode (no proxy trust) returns direct client IP."""
        scope = make_scope(client_ip="192.168.1.100")
        assert _extract_client_ip(scope) == "192.168.1.100"

    def test_proxy_disabled_ignores_xff(self):
        """With proxy trust disabled, X-Forwarded-For is ignored."""
        scope = make_scope(
            client_ip="10.0.0.1",
            headers=[[b"x-forwarded-for", b"203.0.113.50"]],
        )
        assert _extract_client_ip(scope) == "10.0.0.1"

    def test_proxy_enabled_trusted_source_uses_xff(self):
        """With proxy trust enabled and client in trusted CIDR, use XFF."""
        scope = make_scope(
            client_ip="10.0.0.1",
            headers=[[b"x-forwarded-for", b"203.0.113.50, 10.0.0.2"]],
        )
        result = _extract_client_ip(
            scope,
            trusted_proxy_enabled=True,
            trusted_proxy_cidrs=["10.0.0.0/8"],
        )
        assert result == "203.0.113.50"

    def test_proxy_enabled_untrusted_source_ignores_xff(self):
        """With proxy trust enabled but client NOT in trusted CIDR, ignore XFF."""
        scope = make_scope(
            client_ip="192.168.1.100",
            headers=[[b"x-forwarded-for", b"203.0.113.50"]],
        )
        result = _extract_client_ip(
            scope,
            trusted_proxy_enabled=True,
            trusted_proxy_cidrs=["10.0.0.0/8"],
        )
        assert result == "192.168.1.100"

    def test_spoof_attempt_rejected(self):
        """Untrusted client sending XFF header is ignored."""
        scope = make_scope(
            client_ip="203.0.113.99",
            headers=[[b"x-forwarded-for", b"10.0.0.1"]],
        )
        result = _extract_client_ip(
            scope,
            trusted_proxy_enabled=True,
            trusted_proxy_cidrs=["10.0.0.0/8"],
        )
        # 203.0.113.99 is not in trusted CIDRs, so XFF is ignored
        assert result == "203.0.113.99"

    def test_no_xff_header_falls_back(self):
        """Trusted proxy without XFF header falls back to direct IP."""
        scope = make_scope(client_ip="10.0.0.1")
        result = _extract_client_ip(
            scope,
            trusted_proxy_enabled=True,
            trusted_proxy_cidrs=["10.0.0.0/8"],
        )
        assert result == "10.0.0.1"

    def test_no_client_in_scope(self):
        """Missing client in scope returns 'unknown'."""
        scope = {"type": "http", "method": "GET", "path": "/", "headers": []}
        assert _extract_client_ip(scope) == "unknown"
