"""Tests for CorrelationIdMiddleware."""

import json
import logging
import logging.config
import uuid
from pathlib import Path

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


ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


@pytest.fixture
def restore_logging_state():
    root = logging.getLogger()
    factory, handlers, level = logging.getLogRecordFactory(), root.handlers[:], root.level
    yield
    logging.setLogRecordFactory(factory)
    root.handlers[:] = handlers
    root.setLevel(level)


async def _log_inside_and_outside_request(correlation_id: str) -> list[logging.LogRecord]:
    records: list[logging.LogRecord] = []

    class _ListHandler(logging.Handler):
        def emit(self, record):
            records.append(record)

    log = logging.getLogger("hc.obsv.test")
    handler = _ListHandler(level=logging.DEBUG)
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)
    log.propagate = False
    try:
        async def app(scope, receive, send):
            log.warning("inside request")
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        scope = make_scope([(b"x-correlation-id", correlation_id.encode())])
        await CorrelationIdMiddleware(app)(scope, make_receive, ResponseCapture())
        log.warning("outside request")
    finally:
        log.removeHandler(handler)
        log.propagate = True
    return records


@pytest.mark.asyncio
async def test_hc_obsv_001_log_record_carries_request_correlation_id(restore_logging_state):
    from core.logging_setup import install_correlation_logging
    install_correlation_logging()
    cid = str(uuid.uuid4())
    inside, outside = await _log_inside_and_outside_request(cid)
    assert inside.correlation_id == cid
    assert outside.correlation_id == "-"


@pytest.mark.asyncio
async def test_hc_obsv_002_correlation_survives_alembic_logging_reset(restore_logging_state):
    """alembic.ini fileConfig runs at startup and on every vault open
    (migrations/*/env.py); it replaces root handlers and their filters."""
    from core.logging_setup import install_correlation_logging
    install_correlation_logging()
    logging.config.fileConfig(ALEMBIC_INI, disable_existing_loggers=False)
    cid = str(uuid.uuid4())
    inside, _ = await _log_inside_and_outside_request(cid)
    assert inside.correlation_id == cid


def test_hc_obsv_004_create_app_installs_correlation_logging(restore_logging_state):
    import main
    logging.setLogRecordFactory(logging.LogRecord)
    main.create_app()
    record = logging.getLogRecordFactory()("x", logging.INFO, __file__, 1, "m", None, None)
    assert getattr(record, "correlation_id", None) == "-"
