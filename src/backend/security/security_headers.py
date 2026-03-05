"""
Security headers middleware.

Adds standard security headers to all HTTP responses.
HSTS and CSP are only enabled in server mode (not localhost).
"""

from __future__ import annotations

import logging
from typing import Callable

logger = logging.getLogger(__name__)

# Headers applied in all modes
BASE_HEADERS: list[tuple[bytes, bytes]] = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"strict-origin-when-cross-origin"),
    (b"x-xss-protection", b"1; mode=block"),
    (b"permissions-policy", b"camera=(), microphone=(self), geolocation=()"),
]

# Headers only in server mode (external access)
SERVER_HEADERS: list[tuple[bytes, bytes]] = [
    (b"strict-transport-security", b"max-age=31536000; includeSubDomains"),
    (b"content-security-policy", b"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"),
]


class SecurityHeadersMiddleware:
    """
    ASGI middleware that adds security headers to responses.

    Args:
        app: ASGI application
        enabled: Whether to add headers (default True)
        server_mode: Whether to include HSTS/CSP (default False)
    """

    def __init__(
        self,
        app: Callable,
        enabled: bool = True,
        server_mode: bool = False,
    ) -> None:
        self.app = app
        self.enabled = enabled
        self.server_mode = server_mode

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http" or not self.enabled:
            await self.app(scope, receive, send)
            return

        extra_headers = list(BASE_HEADERS)
        if self.server_mode:
            extra_headers.extend(SERVER_HEADERS)

        async def send_with_headers(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(extra_headers)
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)
