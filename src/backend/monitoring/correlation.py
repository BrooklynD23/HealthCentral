"""
Correlation ID middleware for request tracing.

Reads or generates a correlation ID per request, stores in contextvars,
and sets on the response header.
"""

from __future__ import annotations

import contextvars
import uuid
from typing import Callable

_correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default=""
)


def get_correlation_id() -> str:
    """Get the current request's correlation ID."""
    return _correlation_id_var.get()


class CorrelationIdMiddleware:
    """
    ASGI middleware for correlation ID propagation.

    Reads X-Correlation-ID from the request header or generates a new UUID4.
    Stores in contextvars for downstream access and sets on the response.
    """

    def __init__(self, app: Callable, header_name: str = "X-Correlation-ID") -> None:
        self.app = app
        self.header_name = header_name
        self.header_name_lower = header_name.lower().encode()

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract or generate correlation ID
        correlation_id = None
        for key, value in scope.get("headers", []):
            if key == self.header_name_lower:
                raw = value.decode("utf-8", errors="replace").strip()
                # Validate it looks like a UUID
                try:
                    uuid.UUID(raw)
                    correlation_id = raw
                except ValueError:
                    correlation_id = None
                break

        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Store in contextvars
        token = _correlation_id_var.set(correlation_id)

        header_bytes = correlation_id.encode()

        async def send_with_correlation(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append([self.header_name_lower, header_bytes])
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_correlation)
        finally:
            _correlation_id_var.reset(token)
