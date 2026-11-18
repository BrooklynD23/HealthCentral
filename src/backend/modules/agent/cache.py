"""Semantic answer cache (Phase 5, story S5-2).

Keyed on ``(profile_id, normalized_question, profile_version)``. Invalidates
when new verified data lands — a stale cached explanation of changed data is
a correctness bug, so the cache is NEVER consulted without the profile
version (skills/asclexis-backend). ``profile_version`` changes whenever the
evidence the agent can ground an answer in changes (PRD §10 Q4). It is a
fingerprint built by ``api/assistant.py::_profile_version`` over everything
the agent's tools read: verified observations (``o:``), verified documents
(``d:``), care tasks (``t:``), verified medication changes (``m:``), all
observations (``a:``), timeline document events (``e:``) and medications
(``r:``). Most parts are a count paired with a latest timestamp; ``m:`` and
``e:`` hash the columns the tools read. A COUNT alone was not sufficient:
counts decrease on delete, so a delete followed by a different verify returned
the key to a value the cache had already seen and served a stale answer for
data that no longer existed (HC-CACHE-VER-001). A version change is the
invalidation; there is no separate eviction/TTL mechanism to keep correct.

``profile_id`` is required for the same reason: without it, two profiles that
happen to share a ``profile_version`` fingerprint (for example two empty
profiles, both ``"o:0:|d:0:|t:0:|m:0:|a:0:|e:0:|r:0:"``) collide on the same
key and the cache serves one profile's answer to another (HC-CACHE-ISO-001/002, S-CACHE).

``tz_name`` is required too: answers print local dates, so the same question
under a different profile time zone must not replay the old zone's text.

In-process only (a module-level dict) — no cross-process/cross-restart
persistence is required or implied; this is a same-process answer cache, not
a durable store, and it carries no PHI on disk.

Purge race (MEM-PURGE-RACE): ``purge_profile`` runs on lock, logout, delete and
restore. A chat answer can take seconds, so a purge may land between a request's
``get_cached`` miss and its ``put_cached``; storing that answer would undo the
purge. A miss therefore records ``(key, sequence number)`` in
a per-request ``ContextVar`` and ``put_cached`` drops the answer when that
profile was purged (or the cache cleared) since. The mark holds the whole key, so it can only
affect the put that answers the same question. It is reset on every put and on
``clear_cache``; the sequence is never reset. A put with no matching mark stores as before.
"""

from __future__ import annotations

import logging
import re
import threading
from contextvars import ContextVar

from pydantic import BaseModel, ConfigDict

from .schemas import AgentTerminal
from .state import ChatFilters


class CacheKey(BaseModel):
    model_config = ConfigDict(frozen=True)

    normalized_question: str
    profile_version: str
    profile_id: str
    tz_name: str
    filters: ChatFilters = ChatFilters()


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
# Purge-race guard. One monotonic sequence, never reset, all guarded by _lock.
_seq = 0
_purged_at: dict[str, int] = {}  # profile_id -> _seq of its latest purge (one int per purged profile)
_cleared_at = 0  # _seq of the latest clear_cache
_get_mark: ContextVar[tuple[CacheKey, int] | None] = ContextVar("answer_cache_get_mark", default=None)
_log = logging.getLogger(__name__)


def get_cached(key: CacheKey) -> AgentTerminal | None:
    """Return the cached terminal for ``key``, or ``None`` on a miss.

    A miss includes the "version changed" case by construction: ``key``
    already carries ``profile_version``, so a stale version simply never
    matches a dict entry written under the new version. ``key`` also carries
    ``profile_id``, so a different profile's entry never matches even when
    the question text and version fingerprint are identical.
    """
    with _lock:
        hit = _cache.get(key)
        _get_mark.set((key, _seq) if hit is None else None)
        return hit


def put_cached(key: CacheKey, terminal: AgentTerminal) -> None:
    """Store ``terminal`` under the version-scoped ``key``.

    Dropped when this request's miss for ``key`` came before the latest purge of
    ``key.profile_id`` (see the module docstring).
    """
    with _lock:
        mark = _get_mark.get()
        _get_mark.set(None)
        # No matching mark (a put with no get, or for another key) stores unchecked:
        # tests and callers put without a get, so this has to stay fail-open.
        if mark is not None and mark[0] == key and max(_purged_at.get(key.profile_id, 0), _cleared_at) > mark[1]:
            _log.debug("answer cache: put dropped, profile purged mid-request")
            return
        _cache[key] = terminal


def clear_cache() -> None:
    """Drop all entries and this context's get mark; an in-flight put is dropped.
    Test-only convenience; production never needs this because a
    profile_version bump already invalidates old entries by not matching them.
    """
    global _seq, _cleared_at
    with _lock:
        _seq += 1
        _cleared_at = _seq
        _cache.clear()
        _get_mark.set(None)


def purge_profile(profile_id: str) -> int:
    """Drop every cached answer of `profile_id` (lock, logout, delete, restore).

    Other profiles' entries stay. Returns how many went.
    """
    global _seq
    with _lock:
        keys = [k for k in _cache if k.profile_id == profile_id]
        for k in keys:
            del _cache[k]
        _seq += 1  # bumped even with no entries: the in-flight request is the point
        _purged_at[profile_id] = _seq
    return len(keys)
