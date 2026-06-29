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


# Deterministic mapping rule: ``draft`` produces sentences PARALLEL to
# citations in composition order, but NOT strictly one-citation-per-sentence —
# nodes/draft.py's trend composition appends one citation per TrendPoint
# sentence, THEN a multi-citation summary sentence that cites every point
# again (see ``_trend_sentences``: "a single summary sentence per trend
# citing every point that supports it"). So citations can OUTNUMBER sentences
# for a real, fully-grounded draft; a flat positional zip alone would
# under-count and wrongly drop the extra trailing citations.
#
# The rule that handles both shapes correctly: walk sentences in order,
# consuming one citation per sentence by index AS LONG AS that index is
# within range. A sentence survives iff its consumed citation exists and
# carries a non-empty ``source_id`` (a real retrieved-chunk / curated-
# reference / observation handle). Once every sentence has been matched,
# any LEFTOVER citations (the trend summary's extra supporting points, for
# example) are carried through unchanged in ``MappingResult.citations`` —
# they back an already-surviving sentence, so dropping them would silently
# strip real grounding evidence that the draft legitimately attached.
# A sentence with no citation at its index — or whose citation lacks a
# ``source_id`` — is dropped mechanically; this is the path exercised by an
# injected/tampered sentence with no real source handle (story S3-2).
def map_sentences(sentences: list[str], citations: list[Citation]) -> MappingResult:
    """Keep only sentences backed by a real source handle; drop the rest.

    Zero survivors signals the caller (the guard node) to abstain.
    """
    surviving: list[str] = []
    dropped: list[str] = []
    surviving_citations: list[Citation] = []

    for index, sentence in enumerate(sentences):
        citation = citations[index] if index < len(citations) else None
        if citation is not None and citation.source_id:
            surviving.append(sentence)
            surviving_citations.append(citation)
        else:
            dropped.append(sentence)

    # Leftover citations beyond len(sentences) belong to already-surviving
    # sentences (e.g. a trend summary's extra supporting points) — carry
    # them through rather than silently discarding real grounding evidence.
    if len(citations) > len(sentences) and surviving:
        surviving_citations.extend(citations[len(sentences):])

    return MappingResult(surviving=surviving, dropped=dropped, citations=surviving_citations)
