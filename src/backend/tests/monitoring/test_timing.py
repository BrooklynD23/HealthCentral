"""Tests for TimingMiddleware."""

from unittest.mock import MagicMock

import pytest
from monitoring.timing_middleware import TimingMiddleware
from monitoring.metrics import MetricsCollector, metrics_collector


# --- ASGI test helpers ---

def make_scope(
    method: str = "GET",
    path: str = "/test",
    route_path: str | None = None,
) -> dict:
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [],
    }
    if route_path is not None:
        route = MagicMock()
        route.path = route_path
        scope["route"] = route
    return scope


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
async def test_response_time_header_present():
    """X-Response-Time-Ms header is present on response."""
    mw = TimingMiddleware(passthrough_app)
    scope = make_scope(route_path="/test")
    capture = ResponseCapture()
    await mw(scope, make_receive, capture)
    assert "x-response-time-ms" in capture.headers_dict
    assert float(capture.headers_dict["x-response-time-ms"]) >= 0


@pytest.mark.asyncio
async def test_collector_called_with_route_template():
    """Metrics collector receives route template, not raw path."""
    # Reset the global collector for this test
    original_records = list(metrics_collector._records)
    metrics_collector._records.clear()

    try:
        mw = TimingMiddleware(passthrough_app)
        scope = make_scope(
            path="/api/v1/documents/abc-123",
            route_path="/api/v1/documents/{document_id}",
        )
        capture = ResponseCapture()
        await mw(scope, make_receive, capture)

        summary = metrics_collector.get_summary()
        assert summary.total_requests >= 1
        assert any(
            ep.route_template == "/api/v1/documents/{document_id}"
            for ep in summary.endpoints
        )
    finally:
        metrics_collector._records.clear()
        metrics_collector._records.extend(original_records)


@pytest.mark.asyncio
async def test_duration_positive():
    """Recorded duration is positive."""
    metrics_collector._records.clear()
    try:
        mw = TimingMiddleware(passthrough_app)
        scope = make_scope(route_path="/test")
        capture = ResponseCapture()
        await mw(scope, make_receive, capture)
        ms = float(capture.headers_dict["x-response-time-ms"])
        assert ms >= 0
    finally:
        metrics_collector._records.clear()


@pytest.mark.asyncio
async def test_error_responses_still_timed():
    """Error responses also get timing headers."""
    mw = TimingMiddleware(error_app)
    scope = make_scope(route_path="/failing")
    capture = ResponseCapture()
    await mw(scope, make_receive, capture)
    assert "x-response-time-ms" in capture.headers_dict


@pytest.mark.asyncio
async def test_unmatched_route_uses_fallback():
    """Requests without matched route use 'unmatched' key."""
    metrics_collector._records.clear()
    try:
        mw = TimingMiddleware(passthrough_app)
        scope = make_scope()  # No route_path
        capture = ResponseCapture()
        await mw(scope, make_receive, capture)

        summary = metrics_collector.get_summary()
        assert any(
            ep.route_template == "unmatched"
            for ep in summary.endpoints
        )
    finally:
        metrics_collector._records.clear()
