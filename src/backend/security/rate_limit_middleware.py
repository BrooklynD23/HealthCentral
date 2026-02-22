"""
HTTP rate limiting middleware with sliding window counter.

Purpose-built for HTTP middleware — tracks all requests (not just failures),
returns remaining count and reset time for standard rate limit headers.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Callable

logger = logging.getLogger(__name__)

# Paths exempt from rate limiting
EXEMPT_PATHS = ("/health",)


@dataclass(frozen=True)
class RateLimitResult:
    """Immutable result of a rate limit check."""
    allowed: bool
    remaining: int
    retry_after_seconds: int
    reset_at: float


class SlidingWindowCounter:
    """
    Sliding window rate limiter for HTTP middleware.

    Records every request (not just failures) and returns remaining count
    for X-RateLimit-Remaining headers.
    """

    def __init__(self, max_requests: int = 100, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._requests: dict[str, deque[float]] = {}

    def _prune(self, timestamps: deque[float], now: float) -> None:
        cutoff = now - self.window_seconds
        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()

    def record_request(self, key: str) -> RateLimitResult:
        """Record a request and return the rate limit decision."""
        now = time.time()
        with self._lock:
            timestamps = self._requests.setdefault(key, deque())
            self._prune(timestamps, now)

            reset_at = now + self.window_seconds

            if len(timestamps) >= self.max_requests:
                oldest = timestamps[0]
                retry_after = max(1, int((oldest + self.window_seconds) - now))
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    retry_after_seconds=retry_after,
                    reset_at=reset_at,
                )

            timestamps.append(now)
            remaining = max(0, self.max_requests - len(timestamps))
            return RateLimitResult(
                allowed=True,
                remaining=remaining,
                retry_after_seconds=0,
                reset_at=reset_at,
            )


class RateLimitMiddleware:
    """
    ASGI middleware for HTTP rate limiting.

    Adds standard rate limit headers to all responses:
    - X-RateLimit-Limit
    - X-RateLimit-Remaining
    - X-RateLimit-Reset
    - Retry-After (on 429 only)

    Exempts /health and OPTIONS (CORS preflight) requests.
    """

    def __init__(
        self,
        app: Callable,
        max_requests: int = 100,
        window_seconds: int = 60,
        enabled: bool = True,
    ) -> None:
        self.app = app
        self.enabled = enabled
        self.counter = SlidingWindowCounter(
            max_requests=max_requests,
            window_seconds=window_seconds,
        )

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if not self.enabled:
            await self.app(scope, receive, send)
            return

        # Exempt OPTIONS preflight and health checks
        method = scope.get("method", "")
        path = scope.get("path", "")

        if method == "OPTIONS" or path in EXEMPT_PATHS:
            await self.app(scope, receive, send)
            return

        # Extract client IP
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"

        result = self.counter.record_request(client_ip)
        limit_str = str(self.counter.max_requests).encode()
        remaining_str = str(result.remaining).encode()
        reset_str = str(int(result.reset_at)).encode()

        if not result.allowed:
            logger.warning(
                "Rate limit exceeded for %s on %s %s",
                client_ip, method, path,
            )
            await self._send_429(
                send, limit_str, remaining_str, reset_str,
                str(result.retry_after_seconds).encode(),
            )
            return

        # Wrap send to inject rate limit headers into response
        async def send_with_headers(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend([
                    [b"x-ratelimit-limit", limit_str],
                    [b"x-ratelimit-remaining", remaining_str],
                    [b"x-ratelimit-reset", reset_str],
                ])
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)

    @staticmethod
    async def _send_429(
        send: Callable,
        limit: bytes,
        remaining: bytes,
        reset: bytes,
        retry_after: bytes,
    ) -> None:
        """Send a 429 Too Many Requests response."""
        import json
        body = json.dumps({"detail": "Rate limit exceeded"}).encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": 429,
            "headers": [
                [b"content-type", b"application/json"],
                [b"content-length", str(len(body)).encode()],
                [b"x-ratelimit-limit", limit],
                [b"x-ratelimit-remaining", remaining],
                [b"x-ratelimit-reset", reset],
                [b"retry-after", retry_after],
            ],
        })
        await send({
            "type": "http.response.body",
            "body": body,
        })
