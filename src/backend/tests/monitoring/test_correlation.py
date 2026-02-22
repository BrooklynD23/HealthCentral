"""Tests for CorrelationIdMiddleware."""

import json
import uuid

import pytest
from monitoring.correlation import CorrelationIdMiddleware, get_correlation_id


# --- ASGI test helpers ---

def make_scope(headers: list | None = None) -> dict:
    return {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "headers": headers or [],
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


async def make_receive():
    return {"type": "http.request", "body": b"", "more_body": False}


# --- Tests ---

@pytest.mark.asyncio
async def test_generates_when_missing():
    """Generates UUID correlation ID when not provided."""
    captured_id = None

    async def app(scope, receive, send):
        nonlocal captured_id
        captured_id = get_correlation_id()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    mw = CorrelationIdMiddleware(app)
    capture = ResponseCapture()
    await mw(make_scope(), make_receive, capture)

    # Should be a valid UUID
    assert captured_id is not None
    uuid.UUID(captured_id)  # Raises if invalid
    assert "x-correlation-id" in capture.headers_dict


@pytest.mark.asyncio
async def test_uses_provided_id():
    """Uses X-Correlation-ID from request header."""
    test_id = str(uuid.uuid4())
    captured_id = None

    async def app(scope, receive, send):
        nonlocal captured_id
        captured_id = get_correlation_id()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    mw = CorrelationIdMiddleware(app)
    scope = make_scope(headers=[[b"x-correlation-id", test_id.encode()]])
    capture = ResponseCapture()
    await mw(scope, make_receive, capture)

    assert captured_id == test_id


@pytest.mark.asyncio
async def test_response_includes_header():
    """Response includes X-Correlation-ID header."""
    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    mw = CorrelationIdMiddleware(app)
    capture = ResponseCapture()
    await mw(make_scope(), make_receive, capture)
    assert "x-correlation-id" in capture.headers_dict
    uuid.UUID(capture.headers_dict["x-correlation-id"])


@pytest.mark.asyncio
async def test_contextvar_accessible_downstream():
    """Correlation ID is accessible via get_correlation_id() in downstream code."""
    downstream_id = None

    async def app(scope, receive, send):
        nonlocal downstream_id
        downstream_id = get_correlation_id()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    mw = CorrelationIdMiddleware(app)
    capture = ResponseCapture()
    await mw(make_scope(), make_receive, capture)
    assert downstream_id != ""
    uuid.UUID(downstream_id)


@pytest.mark.asyncio
async def test_invalid_uuid_regenerated():
    """Invalid X-Correlation-ID in request triggers regeneration."""
    captured_id = None

    async def app(scope, receive, send):
        nonlocal captured_id
        captured_id = get_correlation_id()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    mw = CorrelationIdMiddleware(app)
    scope = make_scope(headers=[[b"x-correlation-id", b"not-a-uuid"]])
    capture = ResponseCapture()
    await mw(scope, make_receive, capture)

    assert captured_id != "not-a-uuid"
    uuid.UUID(captured_id)  # Should be a valid UUID


@pytest.mark.asyncio
async def test_different_requests_different_ids():
    """Different requests get different correlation IDs."""
    ids = []

    async def app(scope, receive, send):
        ids.append(get_correlation_id())
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    mw = CorrelationIdMiddleware(app)
    for _ in range(3):
        capture = ResponseCapture()
        await mw(make_scope(), make_receive, capture)

    assert len(set(ids)) == 3
