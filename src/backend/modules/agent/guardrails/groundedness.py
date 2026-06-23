"""Groundedness mapping (Phase 3, story S3-2).

For each answer sentence, confirm it maps to a real retrieved chunk or curated
reference handle. Drop any unmapped sentence BEFORE the user sees it. An answer
with zero surviving grounded sentences -> abstain. Mechanical, not prompt-asked.
"""

from __future__ import annotations

from pydantic import BaseModel

from ..schemas import Citation


class MappingResult(BaseModel):
    surviving: list[str]
    dropped: list[str]
    citations: list[Citation]


def map_sentences(sentences: list[str], citations: list[Citation]) -> MappingResult:
    """Keep only sentences backed by a real source handle; drop the rest.

    SCAFFOLD: Sprint 3 (S3-2). Zero survivors signals the guard to abstain.
    """
    raise NotImplementedError("S3-2: drop unmapped sentences mechanically")
