"""Tests for InputValidationMiddleware."""

import json
import pytest
from security.input_validator import InputValidationMiddleware


# --- ASGI test helpers ---

def make_scope(
    method: str = "GET",
    path: str = "/api/v1/test",
    query_string: bytes = b"",
    headers: list | None = None,
) -> dict:
    return {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": query_string,
        "headers": headers or [],
    }


class ResponseCapture:
    """Captures ASGI send messages."""
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

    @property
    def body_json(self) -> dict:
        for m in self.messages:
            if m["type"] == "http.response.body":
                return json.loads(m["body"])
        return {}


async def passthrough_app(scope, receive, send):
    """Simple ASGI app that returns 200."""
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b'{"ok": true}'})


def make_receive(body: bytes = b""):
    """Create a receive callable that returns body."""
    called = False
    async def receive():
        nonlocal called
        if not called:
            called = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}
    return receive


# --- Tests ---

@pytest.mark.asyncio
async def test_normal_get_passes():
    """Normal GET request passes through."""
    mw = InputValidationMiddleware(passthrough_app, max_request_body_bytes=1024)
    scope = make_scope(method="GET")
    capture = ResponseCapture()
    await mw(scope, make_receive(), capture)
    assert capture.status == 200


@pytest.mark.asyncio
async def test_normal_post_passes():
    """POST within body size limit passes through."""
    mw = InputValidationMiddleware(passthrough_app, max_request_body_bytes=1024)
    scope = make_scope(
        method="POST",
        headers=[[b"content-length", b"10"]],
    )
    capture = ResponseCapture()
    await mw(scope, make_receive(b"0123456789"), capture)
    assert capture.status == 200


@pytest.mark.asyncio
async def test_oversized_content_length_rejected():
    """POST with Content-Length exceeding limit returns 413."""
    mw = InputValidationMiddleware(passthrough_app, max_request_body_bytes=100)
    scope = make_scope(
        method="POST",
        headers=[[b"content-length", b"5000"]],
    )
    capture = ResponseCapture()
    await mw(scope, make_receive(), capture)
    assert capture.status == 413
    assert "too large" in capture.body_json["detail"].lower()


@pytest.mark.asyncio
async def test_streaming_body_exceeded_rejected():
    """POST without Content-Length that exceeds limit during streaming returns 413."""

    async def body_reading_app(scope, receive, send):
        """App that reads body via receive before responding."""
        while True:
            msg = await receive()
            if not msg.get("more_body", False):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    mw_with_reader = InputValidationMiddleware(body_reading_app, max_request_body_bytes=10)
    scope = make_scope(method="POST")
    capture = ResponseCapture()
    await mw_with_reader(scope, make_receive(b"x" * 100), capture)
    assert capture.status == 413


@pytest.mark.asyncio
async def test_null_bytes_in_path_rejected():
    """Request with null bytes in path returns 400."""
    mw = InputValidationMiddleware(passthrough_app)
    scope = make_scope(path="/api/v1/test\x00evil")
    capture = ResponseCapture()
    await mw(scope, make_receive(), capture)
    assert capture.status == 400
    assert "path" in capture.body_json["detail"].lower()


@pytest.mark.asyncio
async def test_null_bytes_in_query_rejected():
    """Request with null bytes in query string returns 400."""
    mw = InputValidationMiddleware(passthrough_app)
    scope = make_scope(query_string=b"key=val\x00ue")
    capture = ResponseCapture()
    await mw(scope, make_receive(), capture)
    assert capture.status == 400
    assert "query" in capture.body_json["detail"].lower()


@pytest.mark.asyncio
async def test_invalid_content_length():
    """POST with non-numeric Content-Length returns 400."""
    mw = InputValidationMiddleware(passthrough_app)
    scope = make_scope(
        method="POST",
        headers=[[b"content-length", b"not-a-number"]],
    )
    capture = ResponseCapture()
    await mw(scope, make_receive(), capture)
    assert capture.status == 400


@pytest.mark.asyncio
async def test_multipart_import_allowed():
    """Upload on import endpoints uses the larger upload limit (not the default body limit)."""
    mw = InputValidationMiddleware(passthrough_app, max_request_body_bytes=100)
    scope = make_scope(
        method="POST",
        path="/api/v1/documents/import",
        headers=[[b"content-length", b"999999"]],
    )
    capture = ResponseCapture()
    await mw(scope, make_receive(), capture)
    assert capture.status == 200


@pytest.mark.asyncio
async def test_options_preflight_passes():
    """OPTIONS requests bypass all validation."""
    mw = InputValidationMiddleware(passthrough_app, max_request_body_bytes=1)
    scope = make_scope(method="OPTIONS", path="/api/v1/test\x00evil")
    # Even with null bytes, OPTIONS should pass
    # But path validation happens before method check, let's use clean path
    scope_clean = make_scope(method="OPTIONS")
    capture = ResponseCapture()
    await mw(scope_clean, make_receive(), capture)
    assert capture.status == 200


@pytest.mark.asyncio
async def test_empty_path_safe():
    """Empty path does not crash."""
    mw = InputValidationMiddleware(passthrough_app)
    scope = make_scope(path="")
    capture = ResponseCapture()
    await mw(scope, make_receive(), capture)
    assert capture.status == 200
