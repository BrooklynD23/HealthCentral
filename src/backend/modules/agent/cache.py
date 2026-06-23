"""Semantic answer cache (Phase 5, story S5-2).

Keyed on ``(normalized_question, profile_version)``. Invalidates when new
verified data lands — a stale cached explanation of changed data is a
correctness bug, so the cache is NEVER consulted without the profile version
(skills/healthcentral-backend). ``profile_version`` increments on any
observation verify (PRD §10 Q4).
"""

from __future__ import annotations

from pydantic import BaseModel

from .schemas import AgentTerminal


class CacheKey(BaseModel):
    normalized_question: str
    profile_version: int


def get_cached(key: CacheKey) -> AgentTerminal | None:
    """SCAFFOLD: Sprint 5 (S5-2). Return a cached terminal or None."""
    raise NotImplementedError("S5-2: semantic cache lookup keyed on (question, profile_version)")


def put_cached(key: CacheKey, terminal: AgentTerminal) -> None:
    """SCAFFOLD: Sprint 5 (S5-2). Store a terminal under the version-scoped key."""
    raise NotImplementedError("S5-2: semantic cache store")
