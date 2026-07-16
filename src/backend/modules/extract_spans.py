"""Source-span helper for rule-based entity extractors (HC-M12).

Attaches char_start/char_end/quote provenance to extracted entities so the
UI can show the exact verbatim source text each entity came from. The
invariant is ``text[char_start:char_end] == quote`` whenever a span resolves.
"""

from __future__ import annotations

import re
from typing import Optional

EXTRACTION_VERSION = "rule-v2"


def with_span(entity: dict, text: str, match: Optional[re.Match]) -> dict:
    """Attach source-span fields to an extracted entity dict.

    Uses the full match span (group 0), trimmed of surrounding whitespace.
    When the span cannot be resolved, quote/char_start/char_end are None and
    confidence is capped at 0.5 — an extraction the user cannot check against
    the source must never look certain.
    """
    char_start: Optional[int] = None
    char_end: Optional[int] = None

    if match is not None:
        start, end = match.span()
        if 0 <= start < end <= len(text):
            raw = text[start:end]
            start += len(raw) - len(raw.lstrip())
            end -= len(raw) - len(raw.rstrip())
            if start < end:
                char_start, char_end = start, end

    entity["char_start"] = char_start
    entity["char_end"] = char_end
    entity["quote"] = text[char_start:char_end] if char_start is not None else None
    if entity["quote"] is None:
        entity["confidence"] = min(entity["confidence"], 0.5)
    entity["extraction_version"] = EXTRACTION_VERSION
    return entity
