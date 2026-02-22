"""Tests for SecurityHeadersMiddleware."""

import pytest
from security.security_headers import SecurityHeadersMiddleware


# --- ASGI test helpers ---

def make_scope(method: str = "GET", path: str = "/api/v1/test") -> dict:
    return {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [],
    }


class ResponseCapture:
    def __init__(self):
        self.messages: list[dict] = []

    async def __call__(self, message: dict) -> None:
        self.messages.append(message)

    @property
    def headers_dict(self) -> dict[str, str]:
        for m in self.messages:
            if m["type"] == "http.response.start":
                return {
                    k.decode() if isinstance(k, bytes) else k:
                    v.decode() if isinstance(v, bytes) else v
                    for k, v in m.get("headers", [])
                }
        return {}

    @property
    def status(self) -> int:
        for m in self.messages:
            if m["type"] == "http.response.start":
                return m["status"]
        return 0


async def passthrough_app(scope, receive, send):
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"ok"})


async def error_app(scope, receive, send):
    await send({"type": "http.response.start", "status": 500, "headers": []})
    await send({"type": "http.response.body", "body": b"error"})


async def make_receive():
    return {"type": "http.request", "body": b"", "more_body": False}


# --- Tests ---

@pytest.mark.asyncio
async def test_base_headers_present():
    """All base security headers are present in local mode."""
    mw = SecurityHeadersMiddleware(passthrough_app, enabled=True, server_mode=False)
    capture = ResponseCapture()
    await mw(make_scope(), make_receive, capture)
    headers = capture.headers_dict
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "x-xss-protection" in headers
    assert "permissions-policy" in headers


@pytest.mark.asyncio
async def test_hsts_server_mode_only():
    """HSTS header only present in server mode."""
    mw_local = SecurityHeadersMiddleware(passthrough_app, enabled=True, server_mode=False)
    capture = ResponseCapture()
    await mw_local(make_scope(), make_receive, capture)
    assert "strict-transport-security" not in capture.headers_dict

    mw_server = SecurityHeadersMiddleware(passthrough_app, enabled=True, server_mode=True)
    capture = ResponseCapture()
    await mw_server(make_scope(), make_receive, capture)
    assert "strict-transport-security" in capture.headers_dict


@pytest.mark.asyncio
async def test_csp_server_mode_only():
    """CSP header only present in server mode."""
    mw_local = SecurityHeadersMiddleware(passthrough_app, enabled=True, server_mode=False)
    capture = ResponseCapture()
    await mw_local(make_scope(), make_receive, capture)
    assert "content-security-policy" not in capture.headers_dict

    mw_server = SecurityHeadersMiddleware(passthrough_app, enabled=True, server_mode=True)
    capture = ResponseCapture()
    await mw_server(make_scope(), make_receive, capture)
    assert "content-security-policy" in capture.headers_dict


@pytest.mark.asyncio
async def test_disabled_via_config():
    """No security headers when disabled."""
    mw = SecurityHeadersMiddleware(passthrough_app, enabled=False)
    capture = ResponseCapture()
    await mw(make_scope(), make_receive, capture)
    assert "x-content-type-options" not in capture.headers_dict


@pytest.mark.asyncio
async def test_local_mode_skips_hsts_csp():
    """Local mode has base headers but no HSTS/CSP."""
    mw = SecurityHeadersMiddleware(passthrough_app, enabled=True, server_mode=False)
    capture = ResponseCapture()
    await mw(make_scope(), make_receive, capture)
    headers = capture.headers_dict
    assert "x-content-type-options" in headers
    assert "strict-transport-security" not in headers
    assert "content-security-policy" not in headers


@pytest.mark.asyncio
async def test_headers_on_error_responses():
    """Security headers are present even on error responses."""
    mw = SecurityHeadersMiddleware(error_app, enabled=True, server_mode=False)
    capture = ResponseCapture()
    await mw(make_scope(), make_receive, capture)
    assert capture.status == 500
    assert "x-content-type-options" in capture.headers_dict
