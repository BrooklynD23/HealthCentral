"""
Security audit middleware.

Logs structured security events for mutating HTTP requests.
Optionally persists events to the database via core.audit.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Callable

from monitoring.correlation import get_correlation_id

logger = logging.getLogger(__name__)

# HTTP methods considered mutating
MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class SecurityAuditMiddleware:
    """
    ASGI middleware for security event logging.

    Logs structured JSON for mutating requests (POST/PUT/PATCH/DELETE).
    GET/HEAD/OPTIONS are skipped to reduce noise.
    """

    def __init__(self, app: Callable, log_to_db: bool = False) -> None:
        self.app = app
        self.log_to_db = log_to_db

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")

        if method not in MUTATING_METHODS:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        client = scope.get("client")
        client_ip = client[0] if client else "unknown"
        start_time = time.time()
        response_status = 0

        async def capture_send(message: dict) -> None:
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message.get("status", 0)
            await send(message)

        try:
            await self.app(scope, receive, capture_send)
        finally:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            event_data = {
                "event": "security.request",
                "method": method,
                "path": path,
                "client_ip": client_ip,
                "status": response_status,
                "duration_ms": duration_ms,
                "correlation_id": get_correlation_id(),
            }

            # Classify event type
            if response_status == 429:
                event_data["event"] = "security.rate_limited"
            elif response_status in (400, 413):
                event_data["event"] = "security.input_rejected"

            logger.info(
                "SECURITY_AUDIT: %s",
                json.dumps(event_data, default=str),
            )
