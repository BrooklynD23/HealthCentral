"""Care-plan task candidate derivation (HC-M15).

Turns extracted visit-note entities (follow_up_instruction, test_ordered,
referral) into checklist-task candidates. Candidates are computed on read
and are never persisted until the user explicitly accepts one.

Due-date rule (hard constraint) — a candidate NEVER gets an invented due date:

- An absolute date written in the entity's own source text parses directly.
- A relative expression ("in 4 weeks", "within 3 months") resolves only
  against a confident document anchor date (a visit_date entity or the
  document's collection date); the computed date's confidence is <= 0.8.
- Anything else — vague timing ("soon", "as needed"), no timeframe, or a
  relative expression with no anchor — yields due_date=None,
  due_date_confidence=None, and suggested_status "needs_review".
"""

from __future__ import annotations

import calendar
import re
from datetime import date, datetime, timedelta
from typing import Optional

# Entity types that can become tasks.
TASK_ENTITY_TYPES = frozenset({"follow_up_instruction", "test_ordered", "referral"})

# Confidence for a due date parsed verbatim from the source text.
ABSOLUTE_DATE_CONFIDENCE = 0.9
# Confidence ceiling for a computed (anchor + relative) due date. Computed
# dates must never look certain — keep this <= 0.8.
ANCHORED_RELATIVE_CONFIDENCE = 0.75

# "in 4 weeks", "within 2 to 4 months" — resolves to the earliest bound
# (conservative: the user is prompted early, never late).
RELATIVE_PATTERN = re.compile(
    r"\b(?:in|within)\s+(\d{1,3})\s*(?:to\s+\d{1,3}\s*)?(day|week|month|year)s?\b",
    re.IGNORECASE,
)

_MONTHS = (
    r"January|February|March|April|May|June|July|August|September|October"
    r"|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
)

# (pattern, strptime formats) pairs for absolute dates written in the text.
_ABSOLUTE_DATE_PATTERNS: tuple[tuple[re.Pattern, tuple[str, ...]], ...] = (
    (re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"), ("%Y-%m-%d",)),
    (re.compile(r"\b(\d{1,2}/\d{1,2}/\d{4})\b"), ("%m/%d/%Y",)),
    (re.compile(r"\b(\d{1,2}/\d{1,2}/\d{2})\b"), ("%m/%d/%y",)),
    (
        re.compile(r"\b((?:%s)\.?\s+\d{1,2},?\s+\d{4})\b" % _MONTHS, re.IGNORECASE),
        ("%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y"),
    ),
)

_ANCHOR_DATE_FORMATS = ("%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%m-%d-%y", "%Y-%m-%d")

# Timing tail stripped when building a concise title.
_TIMING_TAIL = re.compile(
    r"\s*\b(?:in|within)\s+\d{1,3}\s*(?:to\s+\d{1,3}\s*)?(?:day|week|month|year)s?\b.*$",
    re.IGNORECASE,
)
_FOLLOW_UP_LABEL = re.compile(
    r"^(?:please\s+)?(?:follow[\-\s]?up(?:\s+appointment)?|return(?:\s+to\s+(?:the\s+|our\s+|your\s+)?\w+)?)\b[:\s]*",
    re.IGNORECASE,
)


def _get(entity, name: str):
    """Read a field from an ORM row or an extractor dict."""
    if isinstance(entity, dict):
        return entity.get(name)
    return getattr(entity, name, None)


def _parse_date_text(raw: str, formats) -> Optional[date]:
    for fmt in formats:
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _find_absolute_date(text: str) -> Optional[date]:
    """Return the first absolute calendar date written in *text*, if any."""
    for pattern, formats in _ABSOLUTE_DATE_PATTERNS:
        m = pattern.search(text)
        if m:
            parsed = _parse_date_text(m.group(1).replace(".", ""), formats)
            if parsed:
                return parsed
    return None


def _document_anchor_date(entities, document) -> Optional[date]:
    """A confident date to resolve relative expressions against:
    a visit_date/encounter-date entity, else the document collection date."""
    for ent in entities:
        if _get(ent, "entity_type") == "visit_date":
            parsed = _parse_date_text(str(_get(ent, "entity_value") or ""), _ANCHOR_DATE_FORMATS)
            if parsed:
                return parsed
    collection = getattr(document, "collection_date", None)
    if isinstance(collection, datetime):
        return collection.date()
    if isinstance(collection, date):
        return collection
    return None


def _add_interval(anchor: date, count: int, unit: str) -> date:
    if unit == "day":
        return anchor + timedelta(days=count)
    if unit == "week":
        return anchor + timedelta(weeks=count)
    # Calendar-aware month/year addition, day clamped to the month's end.
    months = count if unit == "month" else count * 12
    total = anchor.month - 1 + months
    year = anchor.year + total // 12
    month = total % 12 + 1
    day = min(anchor.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _derive_due(
    source_text: str, anchor: Optional[date]
) -> tuple[Optional[date], Optional[float], str]:
    """(due_date, due_date_confidence, suggested_status) for one entity.

    A due date is produced ONLY from an absolute date in the source text, or
    a relative expression resolved against an anchored document date.
    """
    absolute = _find_absolute_date(source_text)
    if absolute is not None:
        return absolute, ABSOLUTE_DATE_CONFIDENCE, "open"

    relative = RELATIVE_PATTERN.search(source_text)
    if relative is not None and anchor is not None:
        due = _add_interval(anchor, int(relative.group(1)), relative.group(2).lower())
        return due, ANCHORED_RELATIVE_CONFIDENCE, "open"

    return None, None, "needs_review"


def _capitalize(text: str) -> str:
    return text[:1].upper() + text[1:]


def _derive_title(entity_type: str, value: str) -> str:
    """Concise imperative title from the entity value, timing tail stripped."""
    text = _TIMING_TAIL.sub("", " ".join(str(value).split())).strip(" .,;:")
    if entity_type == "referral":
        return f"Schedule {text} follow-up" if text else "Schedule referral follow-up"
    if entity_type == "follow_up_instruction":
        if _FOLLOW_UP_LABEL.match(text):
            rest = _FOLLOW_UP_LABEL.sub("", text).strip(" .,;:")
            return f"Follow up {rest}" if rest else "Schedule follow-up"
        return _capitalize(text) if text else "Schedule follow-up"
    # test_ordered
    return _capitalize(text) if text else "Complete ordered test"


def derive_task_candidates(entities, document) -> list[dict]:
    """Derive checklist-task candidates from a document's extracted entities.

    *entities* is the document's full entity list (ORM rows or extractor
    dicts) — non-task types are skipped but a visit_date entity among them
    supplies the anchor for relative due dates. Candidates are pure values;
    nothing is persisted here.
    """
    anchor = _document_anchor_date(entities, document)
    doc_id = getattr(document, "id", None)

    candidates: list[dict] = []
    for ent in entities:
        entity_type = _get(ent, "entity_type")
        if entity_type not in TASK_ENTITY_TYPES:
            continue
        value = str(_get(ent, "entity_value") or "")
        quote = _get(ent, "quote")
        # Due dates must come from the source text itself.
        due_date, due_confidence, suggested_status = _derive_due(
            str(quote) if quote else value, anchor
        )
        candidates.append({
            "title": _derive_title(entity_type, value),
            "source_entity_id": _get(ent, "id"),
            "source_document_id": doc_id,
            "source_quote": quote,
            "due_date": due_date,
            "due_date_confidence": due_confidence,
            "suggested_status": suggested_status,
        })
    return candidates
