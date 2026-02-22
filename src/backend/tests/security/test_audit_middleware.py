"""Tests for SecurityAuditMiddleware."""

import json
import logging
import pytest
from security.audit_middleware import SecurityAuditMiddleware


# --- ASGI test helpers ---

def make_scope(
    method: str = "GET",
    path: str = "/api/v1/test",
    client: tuple = ("127.0.0.1", 8000),
) -> dict:
    return {
        "type": "http",
        "method": method,
        "path": path,
        "client": client,
        "headers": [],
    }


class ResponseCapture:
    def __init__(self):
        self.messages: list[dict] = []

    async def __call__(self, message: dict) -> None:
        self.messages.append(message)

    @property
    def status(self) -> int:
        for m in self.messages:
            if m["type"] == "http.response.start":
                return m["status"]
        return 0


async def make_app_with_status(status: int):
    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": status, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})
    return app


async def passthrough_app(scope, receive, send):
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"ok"})


async def rate_limited_app(scope, receive, send):
    await send({"type": "http.response.start", "status": 429, "headers": []})
    await send({"type": "http.response.body", "body": b"rate limited"})


async def input_rejected_app(scope, receive, send):
    await send({"type": "http.response.start", "status": 413, "headers": []})
    await send({"type": "http.response.body", "body": b"too large"})


async def make_receive():
    return {"type": "http.request", "body": b"", "more_body": False}


# --- Tests ---

@pytest.mark.asyncio
async def test_mutating_request_logged(caplog):
    """POST requests are logged."""
    mw = SecurityAuditMiddleware(passthrough_app)
    scope = make_scope(method="POST", path="/api/v1/documents")
    capture = ResponseCapture()
    with caplog.at_level(logging.INFO, logger="security.audit_middleware"):
        await mw(scope, make_receive, capture)
    assert any("security.request" in r.message for r in caplog.records)
    assert any("/api/v1/documents" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_get_skipped(caplog):
    """GET requests are not logged."""
    mw = SecurityAuditMiddleware(passthrough_app)
    scope = make_scope(method="GET")
    capture = ResponseCapture()
    with caplog.at_level(logging.INFO, logger="security.audit_middleware"):
        await mw(scope, make_receive, capture)
    audit_records = [r for r in caplog.records if "SECURITY_AUDIT" in r.message]
    assert len(audit_records) == 0


@pytest.mark.asyncio
async def test_rate_limited_event_logged(caplog):
    """429 responses are classified as security.rate_limited."""
    mw = SecurityAuditMiddleware(rate_limited_app)
    scope = make_scope(method="POST")
    capture = ResponseCapture()
    with caplog.at_level(logging.INFO, logger="security.audit_middleware"):
        await mw(scope, make_receive, capture)
    assert any("security.rate_limited" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_input_rejected_event_logged(caplog):
    """413 responses are classified as security.input_rejected."""
    mw = SecurityAuditMiddleware(input_rejected_app)
    scope = make_scope(method="POST")
    capture = ResponseCapture()
    with caplog.at_level(logging.INFO, logger="security.audit_middleware"):
        await mw(scope, make_receive, capture)
    assert any("security.input_rejected" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_log_includes_path_and_method(caplog):
    """Log entries include the request path and method."""
    mw = SecurityAuditMiddleware(passthrough_app)
    scope = make_scope(method="DELETE", path="/api/v1/profiles/123")
    capture = ResponseCapture()
    with caplog.at_level(logging.INFO, logger="security.audit_middleware"):
        await mw(scope, make_receive, capture)
    audit_msgs = [r.message for r in caplog.records if "SECURITY_AUDIT" in r.message]
    assert len(audit_msgs) == 1
    data = json.loads(audit_msgs[0].replace("SECURITY_AUDIT: ", ""))
    assert data["method"] == "DELETE"
    assert data["path"] == "/api/v1/profiles/123"
