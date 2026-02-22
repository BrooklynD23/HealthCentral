"""Tests for RateLimitMiddleware and SlidingWindowCounter."""

import json
import time
from unittest.mock import patch

import pytest
from security.rate_limit_middleware import (
    RateLimitMiddleware,
    SlidingWindowCounter,
)


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


async def make_receive():
    return {"type": "http.request", "body": b"", "more_body": False}


# --- SlidingWindowCounter tests ---

def test_within_limit():
    """Requests within limit are allowed."""
    counter = SlidingWindowCounter(max_requests=5, window_seconds=60)
    result = counter.record_request("test-ip")
    assert result.allowed is True
    assert result.remaining == 4


def test_exceed_limit():
    """Exceeding limit returns not allowed."""
    counter = SlidingWindowCounter(max_requests=3, window_seconds=60)
    for _ in range(3):
        counter.record_request("test-ip")
    result = counter.record_request("test-ip")
    assert result.allowed is False
    assert result.remaining == 0
    assert result.retry_after_seconds >= 1


def test_per_ip_isolation():
    """Different IPs have separate counters."""
    counter = SlidingWindowCounter(max_requests=2, window_seconds=60)
    counter.record_request("ip-1")
    counter.record_request("ip-1")
    # ip-1 is at limit
    result_ip1 = counter.record_request("ip-1")
    assert result_ip1.allowed is False
    # ip-2 should still be allowed
    result_ip2 = counter.record_request("ip-2")
    assert result_ip2.allowed is True


def test_window_reset():
    """Requests are allowed again after window expires."""
    counter = SlidingWindowCounter(max_requests=2, window_seconds=1)
    counter.record_request("test-ip")
    counter.record_request("test-ip")
    result = counter.record_request("test-ip")
    assert result.allowed is False

    # Simulate time passing beyond window
    with patch("security.rate_limit_middleware.time") as mock_time:
        mock_time.time.return_value = time.time() + 2
        result = counter.record_request("test-ip")
        assert result.allowed is True


def test_remaining_decrements():
    """Remaining count decrements with each request."""
    counter = SlidingWindowCounter(max_requests=5, window_seconds=60)
    r1 = counter.record_request("test-ip")
    assert r1.remaining == 4
    r2 = counter.record_request("test-ip")
    assert r2.remaining == 3
    r3 = counter.record_request("test-ip")
    assert r3.remaining == 2


# --- RateLimitMiddleware tests ---

@pytest.mark.asyncio
async def test_middleware_within_limit_200():
    """Request within limit passes through with rate limit headers."""
    mw = RateLimitMiddleware(passthrough_app, max_requests=100, window_seconds=60)
    scope = make_scope()
    capture = ResponseCapture()
    await mw(scope, make_receive, capture)
    assert capture.status == 200
    assert "x-ratelimit-limit" in capture.headers_dict
    assert "x-ratelimit-remaining" in capture.headers_dict
    assert "x-ratelimit-reset" in capture.headers_dict


@pytest.mark.asyncio
async def test_middleware_exceed_429():
    """Exceeding rate limit returns 429."""
    mw = RateLimitMiddleware(passthrough_app, max_requests=2, window_seconds=60)
    scope = make_scope()
    for _ in range(2):
        capture = ResponseCapture()
        await mw(scope, make_receive, capture)

    capture = ResponseCapture()
    await mw(scope, make_receive, capture)
    assert capture.status == 429
    assert "retry-after" in capture.headers_dict


@pytest.mark.asyncio
async def test_middleware_disabled():
    """Disabled middleware passes all requests through."""
    mw = RateLimitMiddleware(passthrough_app, max_requests=1, window_seconds=60, enabled=False)
    scope = make_scope()
    for _ in range(5):
        capture = ResponseCapture()
        await mw(scope, make_receive, capture)
        assert capture.status == 200


@pytest.mark.asyncio
async def test_health_exempt():
    """/health endpoint bypasses rate limiting."""
    mw = RateLimitMiddleware(passthrough_app, max_requests=1, window_seconds=60)
    # Exhaust limit on normal path
    scope = make_scope(path="/api/v1/test")
    capture = ResponseCapture()
    await mw(scope, make_receive, capture)

    # /health should still work
    health_scope = make_scope(path="/health")
    capture = ResponseCapture()
    await mw(health_scope, make_receive, capture)
    assert capture.status == 200


@pytest.mark.asyncio
async def test_options_exempt():
    """OPTIONS requests bypass rate limiting."""
    mw = RateLimitMiddleware(passthrough_app, max_requests=1, window_seconds=60)
    # Exhaust limit
    scope = make_scope()
    capture = ResponseCapture()
    await mw(scope, make_receive, capture)

    # OPTIONS should still work
    options_scope = make_scope(method="OPTIONS")
    capture = ResponseCapture()
    await mw(options_scope, make_receive, capture)
    assert capture.status == 200
