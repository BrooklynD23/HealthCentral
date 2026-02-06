"""
In-memory rate limiting helpers.

This project is local-first and typically runs on localhost. Even so, auth
endpoints should be protected against brute-force attempts.

This is intentionally lightweight (no Redis, no external deps). It is best-effort
per-process; if the backend is run with multiple workers, each worker has its own
limit window.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass

from .config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int | None = None


class FixedWindowRateLimiter:
    """
    Sliding-window rate limiter (implemented via timestamp deque per key).

    Call pattern:
    - `check(key)` before performing the sensitive action.
    - `add_failure(key)` when the sensitive action fails.
    - `reset(key)` on success (optional).
    """

    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds
        self._lock = threading.Lock()
        self._attempts: dict[str, deque[float]] = {}

    def _prune(self, attempts: deque[float], now: float) -> None:
        cutoff = now - self._window_seconds
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()

    def check(self, key: str) -> RateLimitDecision:
        if not settings.auth_rate_limit_enabled:
            return RateLimitDecision(allowed=True)

        now = time.time()
        with self._lock:
            attempts = self._attempts.setdefault(key, deque())
            self._prune(attempts, now)

            if len(attempts) >= self._max_attempts:
                oldest = attempts[0]
                retry_after = max(1, int((oldest + self._window_seconds) - now))
                return RateLimitDecision(allowed=False, retry_after_seconds=retry_after)

        return RateLimitDecision(allowed=True)

    def add_failure(self, key: str) -> None:
        if not settings.auth_rate_limit_enabled:
            return

        now = time.time()
        with self._lock:
            attempts = self._attempts.setdefault(key, deque())
            attempts.append(now)
            self._prune(attempts, now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)


# Singleton limiter for auth endpoints.
auth_rate_limiter = FixedWindowRateLimiter(
    max_attempts=settings.auth_rate_limit_max_attempts,
    window_seconds=settings.auth_rate_limit_window_seconds,
)

