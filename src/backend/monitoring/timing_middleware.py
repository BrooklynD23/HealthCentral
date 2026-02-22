"""
Request timing middleware.

Measures request duration and records to MetricsCollector.
Uses route template (not raw path) to avoid cardinality explosion.
"""

from __future__ import annotations

import time
from typing import Callable

from .metrics import metrics_collector


class TimingMiddleware:
    """
    ASGI middleware that times requests and records metrics.

    Extracts the matched route template from Starlette's scope.
    Adds X-Response-Time-Ms header to responses.
    """

    def __init__(self, app: Callable) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        response_status = 200

        async def capture_send(message: dict) -> None:
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message.get("status", 200)
                duration = time.perf_counter() - start
                duration_ms = round(duration * 1000, 2)

                # Add timing header
                headers = list(message.get("headers", []))
                headers.append([b"x-response-time-ms", str(duration_ms).encode()])
                message = {**message, "headers": headers}

                # Extract route template
                route = scope.get("route")
                if route and hasattr(route, "path"):
                    route_template = route.path
                else:
                    route_template = "unmatched"

                method = scope.get("method", "UNKNOWN")
                metrics_collector.record_request(
                    method=method,
                    route_template=route_template,
                    status_code=response_status,
                    duration_seconds=duration,
                )

            await send(message)

        await self.app(scope, receive, capture_send)
