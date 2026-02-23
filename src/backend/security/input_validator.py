"""
Raw ASGI middleware for input validation.

Enforces request body size limits and rejects malicious path/query patterns.
Implemented as raw ASGI to avoid double-reading request bodies.
"""

from __future__ import annotations

import logging
from typing import Callable

from core.config import settings as app_settings

logger = logging.getLogger(__name__)

# Paths that allow multipart/form-data uploads (larger bodies expected)
IMPORT_PATH_PREFIXES = (
    "/api/v1/documents/import",
    "/api/v1/documents/upload",
)


class _BodyTooLargeError(Exception):
    """Internal signal raised by counting receive when body exceeds limit."""


class InputValidationMiddleware:
    """
    ASGI middleware for input validation.

    - Rejects requests with null bytes in path or query string.
    - Enforces Content-Length limit (rejects before body is read).
    - For chunked/streaming requests, wraps receive to count bytes incrementally.
    - Import endpoints get a larger limit (max_import_file_size_mb from config).
    """

    def __init__(self, app: Callable, max_request_body_bytes: int = 10_485_760) -> None:
        self.app = app
        self.max_request_body_bytes = max_request_body_bytes
        self.max_upload_bytes = app_settings.max_import_file_size_mb * 1024 * 1024

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Allow OPTIONS preflight through without validation
        method = scope.get("method", "")
        if method == "OPTIONS":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        query_string: bytes = scope.get("query_string", b"")

        # Reject null bytes in path
        if "\x00" in path:
            logger.warning("Null byte in request path: %s", repr(path))
            await self._send_error(send, 400, "Invalid request path")
            return

        # Reject null bytes in query string
        if b"\x00" in query_string:
            logger.warning("Null byte in query string")
            await self._send_error(send, 400, "Invalid query string")
            return

        # Check if this is an import endpoint (allows larger multipart uploads)
        is_import = any(path.startswith(prefix) for prefix in IMPORT_PATH_PREFIXES)
        effective_limit = self.max_upload_bytes if is_import else self.max_request_body_bytes

        # Body size enforcement for non-GET/HEAD/OPTIONS methods
        if method in ("POST", "PUT", "PATCH", "DELETE"):
            headers = dict(scope.get("headers", []))
            content_length_raw = headers.get(b"content-length")

            if content_length_raw is not None:
                try:
                    content_length = int(content_length_raw)
                    if content_length < 0:
                        raise ValueError("negative")
                except (ValueError, TypeError):
                    await self._send_error(send, 400, "Invalid Content-Length")
                    return

                if content_length > effective_limit:
                    logger.warning(
                        "Request body too large: %d > %d",
                        content_length, effective_limit,
                    )
                    await self._send_error(send, 413, "Request body too large")
                    return
            else:
                # No Content-Length — wrap receive to count bytes incrementally
                receive = self._make_counting_receive(receive, effective_limit)

        response_started = False

        async def tracked_send(message: dict) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, tracked_send)
        except _BodyTooLargeError:
            if not response_started:
                await self._send_error(send, 413, "Request body too large")
            else:
                logger.error(
                    "Body size limit exceeded after response headers already sent"
                )

    def _make_counting_receive(
        self, original_receive: Callable, max_bytes: int,
    ) -> Callable:
        """Wrap receive to count body bytes and reject if exceeded."""
        bytes_received = 0

        async def counting_receive() -> dict:
            nonlocal bytes_received
            message = await original_receive()
            if message.get("type") == "http.request":
                body = message.get("body", b"")
                bytes_received += len(body)
                if bytes_received > max_bytes:
                    raise _BodyTooLargeError(
                        f"Request body exceeded {max_bytes} bytes"
                    )
            return message

        return counting_receive

    @staticmethod
    async def _send_error(send: Callable, status: int, detail: str) -> None:
        """Send an HTTP error response."""
        import json
        body = json.dumps({"detail": detail}).encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": status,
            "headers": [
                [b"content-type", b"application/json"],
                [b"content-length", str(len(body)).encode()],
            ],
        })
        await send({
            "type": "http.response.body",
            "body": body,
        })
