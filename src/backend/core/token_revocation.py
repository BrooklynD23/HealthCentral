"""
JWT token revocation (logout invalidation) support.

HealthCentral uses short-lived JWTs for API authentication. By default JWTs are
stateless, so logging out would not invalidate an already-issued token.

This module provides a lightweight local-first revocation list keyed by token
`jti` claim. Entries are persisted to disk so revocations survive backend restarts.
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RevokedToken:
    """A revoked JWT token identifier."""

    jti: str
    exp: int  # unix timestamp (seconds)


class TokenRevocationList:
    """
    Persistent revocation list for JWT `jti`s.

    Storage format:
    {
      "schema_version": 1,
      "revoked": [{"jti": "...", "exp": 123}, ...]
    }
    """

    _SCHEMA_VERSION = 1

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = threading.Lock()
        self._loaded = False
        self._revoked: dict[str, int] = {}

    def _now_ts(self) -> int:
        return int(datetime.now(timezone.utc).timestamp())

    def _load_if_needed(self) -> None:
        if self._loaded:
            return

        self._loaded = True
        if not self._path.exists():
            return

        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Failed to read token revocation list at {self._path}: {e}")
            return

        if not isinstance(data, dict) or data.get("schema_version") != self._SCHEMA_VERSION:
            logger.warning(f"Token revocation list schema mismatch at {self._path}")
            return

        revoked = data.get("revoked", [])
        if not isinstance(revoked, list):
            return

        for entry in revoked:
            if not isinstance(entry, dict):
                continue
            jti = entry.get("jti")
            exp = entry.get("exp")
            if isinstance(jti, str) and isinstance(exp, int):
                self._revoked[jti] = exp

        self._prune_expired(now_ts=self._now_ts())

    def _prune_expired(self, now_ts: int) -> None:
        expired = [jti for jti, exp in self._revoked.items() if exp <= now_ts]
        for jti in expired:
            self._revoked.pop(jti, None)

    def _persist(self) -> None:
        payload = {
            "schema_version": self._SCHEMA_VERSION,
            "revoked": [{"jti": jti, "exp": exp} for jti, exp in self._revoked.items()],
        }

        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")

        tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        tmp_path.replace(self._path)

    def is_revoked(self, jti: str) -> bool:
        """Return True if `jti` is revoked (and not expired)."""
        with self._lock:
            self._load_if_needed()
            now_ts = self._now_ts()
            self._prune_expired(now_ts=now_ts)
            return jti in self._revoked

    def revoke(self, jti: str, exp: int) -> None:
        """
        Revoke a token until its expiration.

        Args:
            jti: Token identifier claim
            exp: Token expiration unix timestamp (seconds)
        """
        with self._lock:
            self._load_if_needed()
            self._revoked[jti] = exp
            self._prune_expired(now_ts=self._now_ts())
            try:
                self._persist()
            except Exception as e:
                logger.warning(f"Failed to persist revoked token list at {self._path}: {e}")

