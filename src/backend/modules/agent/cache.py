"""Semantic answer cache (Phase 5, story S5-2).

Keyed on ``(profile_id, normalized_question, profile_version)``. Invalidates
when new verified data lands — a stale cached explanation of changed data is
a correctness bug, so the cache is NEVER consulted without the profile
version (skills/asclexis-backend). ``profile_version`` changes whenever the
evidence the agent can ground an answer in changes (PRD §10 Q4). It is a
fingerprint built by ``api/assistant.py::_profile_version`` over the verified
observations AND verified documents for the profile — each as a count paired
with the latest ``verified_at``. A COUNT alone was not sufficient: counts
decrease on delete, so a delete followed by a different verify returned the
key to a value the cache had already seen and served a stale answer for data
that no longer existed (HC-CACHE-VER-001). A version change is the
invalidation; there is no separate eviction/TTL mechanism to keep correct.

``profile_id`` is required for the same reason: without it, two profiles that
happen to share a ``profile_version`` fingerprint (for example two empty
profiles, both ``"o:0:|d:0:"``) collide on the same key and the cache serves
one profile's answer to another (HC-CACHE-ISO-001/002, S-CACHE).

In-process only (a module-level dict) — no cross-process/cross-restart
persistence is required or implied; this is a same-process answer cache, not
a durable store, and it carries no PHI on disk.
"""

from __future__ import annotations

import re
import threading

from pydantic import BaseModel, ConfigDict

from .schemas import AgentTerminal


class CacheKey(BaseModel):
    model_config = ConfigDict(frozen=True)

    normalized_question: str
    profile_version: str
    profile_id: str


def normalize_question(question: str) -> str:
    """Deterministic normalization: lowercase, strip, collapse whitespace.

    Two questions that differ only in case/leading-trailing/internal
    whitespace hit the same cache entry; anything else (punctuation,
    wording) is treated as a different question — this is intentionally
    simple, not a fuzzy/embedding-based match.
    """
    return re.sub(r"\s+", " ", question.strip().lower())


_lock = threading.Lock()
_cache: dict[CacheKey, AgentTerminal] = {}


def get_cached(key: CacheKey) -> AgentTerminal | None:
    """Return the cached terminal for ``key``, or ``None`` on a miss.

    A miss includes the "version changed" case by construction: ``key``
    already carries ``profile_version``, so a stale version simply never
    matches a dict entry written under the new version. ``key`` also carries
    ``profile_id``, so a different profile's entry never matches even when
    the question text and version fingerprint are identical.
    """
    with _lock:
        return _cache.get(key)


def put_cached(key: CacheKey, terminal: AgentTerminal) -> None:
    """Store ``terminal`` under the version-scoped ``key``."""
    with _lock:
        _cache[key] = terminal


def clear_cache() -> None:
    """Drop all entries. Test-only convenience; production never needs this
    because a profile_version bump already invalidates old entries by not
    matching them.
    """
    with _lock:
        _cache.clear()
