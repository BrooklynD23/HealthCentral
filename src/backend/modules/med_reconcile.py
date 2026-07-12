"""Medication reconciliation from documents (HC-M19).

Pure comparison, computed on read: a document's medication_change entities
(rejected entities excluded) are compared against the profile's medication
list, and each difference becomes a *suggestion* — "the note says X, your
list has Y". Nothing here persists anything, and no route built on this
module may change the medication list; applying a change happens only
through the existing medications endpoints, initiated by the user.

Safety constraints (tested in tests/test_med_reconcile.py, HC-MREC):

- No fabrication: every drug token in a suggestion comes verbatim from the
  entity's own value/quote; ``current_list_summary`` is built only from the
  matched medication's own stored fields or the fixed neutral phrases.
- No advice: all generated strings are record-keeping labels ("not on your
  list"), never instructions or recommendations.
- Never guess: drug-name matching is exact-token only. An ambiguous or
  unmatchable name yields an ``unclear`` suggestion that says why.
"""

from __future__ import annotations

import re

SUGGESTION_TYPES = frozenset({
    "new_medication",
    "stopped_medication",
    "dose_or_frequency_change",
    "possible_duplicate",
    "unclear",
})

# Hard cap on suggestions returned for one document (bounded output for
# pathological documents; first entities win, deterministically).
MAX_SUGGESTIONS = 100

# Canonical leading action verbs guaranteed by extract_visit_notes.
_ACTIONS = frozenset({"start", "stop", "increase", "decrease", "change", "continue"})

# Filler tokens that may sit between the action verb and the drug name
# ("change to lisinopril", "start taking metformin").
_LEADING_FILLER = frozenset({"to", "taking", "using", "the", "your", "a", "an"})

# Tokens that are dose/frequency/route vocabulary, not part of a drug name.
# Hitting one of these ends the drug-name span.
_NON_DRUG_TOKENS = frozenset({
    # units
    "mg", "mcg", "g", "gram", "grams", "ml", "mls", "l", "iu", "meq",
    "milligram", "milligrams", "microgram", "micrograms", "unit", "units",
    "percent",
    # forms
    "tablet", "tablets", "tab", "tabs", "capsule", "capsules", "cap", "caps",
    "pill", "pills", "puff", "puffs", "drop", "drops", "patch", "patches",
    "spray", "sprays", "injection", "injections", "inhaler",
    # frequency / timing
    "daily", "nightly", "weekly", "monthly", "hourly", "once", "twice",
    "three", "four", "times", "time", "every", "other", "hour", "hours",
    "day", "days", "week", "weeks", "morning", "evening", "night", "bedtime",
    "am", "pm", "qd", "qhs", "bid", "tid", "qid", "prn",
    # route / narrative connectors
    "as", "needed", "with", "without", "food", "meals", "by", "mouth",
    "orally", "po", "at", "per", "to", "and", "or", "if", "for", "from", "of",
    "dose", "doses", "dosage", "half", "one", "two", "before", "after",
})

_TOKEN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")

_FREQUENCY_LABELS = {
    "once_daily": "once daily",
    "twice_daily": "twice daily",
    "three_times_daily": "three times daily",
    "four_times_daily": "four times daily",
    "every_other_day": "every other day",
    "weekly": "weekly",
    "as_needed": "as needed",
    "custom": "custom schedule",
}

# Fixed neutral phrases — the only generated wording besides list fields.
NOT_ON_LIST = "not on your list"
_INACTIVE_SUFFIX = " (marked inactive on your list)"
_REASON_NO_ACTION = (
    "This line does not begin with a recognized action word, so it was not compared."
)
_REASON_NO_DRUG = "No medication name could be read from this line."
_REASON_NOT_ON_LIST = (
    "This medication is not on your list, so there is no entry to compare."
)


def _get(obj, name: str):
    """Read a field from an ORM row or a plain dict (extractor output)."""
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _drug_tokens(entity_value: str) -> tuple[str | None, list[str]]:
    """(action, drug tokens) parsed from a medication_change entity value.

    The value's canonical shape is "<action> <object...>" (see
    extract_visit_notes). Drug tokens are the consecutive name-like tokens
    right after the action verb (fillers skipped), ending at the first
    number or dose/frequency word. Returns (None, []) when the leading
    token is not a recognized action.
    """
    tokens = _TOKEN.findall(str(entity_value).lower())
    if not tokens or tokens[0] not in _ACTIONS:
        return None, []
    action = tokens[0]
    rest = tokens[1:]
    while rest and rest[0] in _LEADING_FILLER:
        rest = rest[1:]
    drug: list[str] = []
    for token in rest:
        if token in _NON_DRUG_TOKENS or token.isdigit() or not re.search(r"[a-z]", token):
            break
        drug.append(token)
        if len(drug) >= 4:
            break
    return action, drug


def _name_tokens(medication) -> set[str]:
    tokens = set(_TOKEN.findall(str(_get(medication, "name") or "").lower()))
    generic = _get(medication, "generic_name")
    if generic:
        tokens |= set(_TOKEN.findall(str(generic).lower()))
    return tokens


def _match_medication(drug: list[str], medications) -> tuple[object | None, list]:
    """Conservative exact-token match of *drug* against the medication list.

    A medication is a candidate when the primary drug token appears as an
    exact token of its name/generic name. Multiple candidates are refined by
    requiring every drug token; anything still ambiguous is returned as
    (None, candidates) so the caller emits ``unclear`` — never a guess.
    """
    primary = drug[0]
    candidates = [m for m in medications if primary in _name_tokens(m)]
    if len(candidates) > 1:
        refined = [
            m for m in candidates if all(tok in _name_tokens(m) for tok in drug)
        ]
        if len(refined) == 1:
            return refined[0], []
        return None, candidates
    if len(candidates) == 1:
        return candidates[0], []
    return None, []


def _list_summary(medication) -> str:
    """One neutral line describing the user's own list entry, built solely
    from the medication's stored fields (e.g. "atorvastatin 10 mg daily")."""
    parts = [str(_get(medication, "name") or "").strip()]
    amount = _get(medication, "dosage_amount")
    if amount is not None:
        parts.append(f"{amount:g}")
        unit = _get(medication, "dosage_unit")
        if unit:
            parts.append(str(unit))
    frequency = _get(medication, "frequency")
    if frequency in _FREQUENCY_LABELS:
        parts.append(_FREQUENCY_LABELS[frequency])
    summary = " ".join(p for p in parts if p)
    if _get(medication, "is_active") is False:
        summary += _INACTIVE_SUFFIX
    return summary


def _suggestion(
    entity,
    suggestion_type: str,
    *,
    drug_name: str | None,
    matched=None,
    summary: str | None = None,
    reason: str | None = None,
) -> dict:
    confidence = float(_get(entity, "confidence") or 0.5)
    cap = 0.4 if suggestion_type == "unclear" else 0.9
    return {
        "suggestion_type": suggestion_type,
        "source_entity_id": _get(entity, "id"),
        "source_quote": _get(entity, "quote"),
        "entity_value": str(_get(entity, "entity_value") or ""),
        "drug_name": drug_name,
        "matched_medication_id": _get(matched, "id") if matched is not None else None,
        "current_list_summary": summary
        if summary is not None
        else (_list_summary(matched) if matched is not None else NOT_ON_LIST),
        "confidence": min(confidence, cap),
        "reason": reason,
    }


def derive_reconciliation_suggestions(entities, medications) -> list[dict]:
    """Compare a document's medication_change entities with the profile's
    medication list and report the differences as suggestions.

    *entities* is the document's entity list (ORM rows or extractor dicts);
    only medication_change entities not rejected by the user
    (``verified_by_user != False``) are considered. *medications* is the
    profile's medication list (active and inactive). Pure function —
    nothing is persisted, and agreement (e.g. "continue X" for an active
    listed X) produces no suggestion at all.
    """
    suggestions: list[dict] = []
    for entity in entities:
        if len(suggestions) >= MAX_SUGGESTIONS:
            break
        if _get(entity, "entity_type") != "medication_change":
            continue
        if _get(entity, "verified_by_user") is False:
            continue

        action, drug = _drug_tokens(_get(entity, "entity_value") or "")
        if action is None:
            suggestions.append(_suggestion(
                entity, "unclear", drug_name=None, reason=_REASON_NO_ACTION,
            ))
            continue
        if not drug:
            suggestions.append(_suggestion(
                entity, "unclear", drug_name=None, reason=_REASON_NO_DRUG,
            ))
            continue

        drug_name = " ".join(drug)
        matched, ambiguous = _match_medication(drug, medications)
        if ambiguous:
            names = ", ".join(
                sorted(str(_get(m, "name") or "") for m in ambiguous)
            )
            suggestions.append(_suggestion(
                entity,
                "unclear",
                drug_name=drug_name,
                reason=f"This line matches more than one entry on your list: {names}.",
            ))
            continue

        is_active = matched is not None and _get(matched, "is_active") is not False

        if action in ("start", "continue"):
            if matched is None:
                suggestions.append(_suggestion(
                    entity, "new_medication", drug_name=drug_name,
                ))
            elif not is_active:
                # Listed but inactive: reads as a (re)start not yet on the
                # active list; the summary shows the inactive entry.
                suggestions.append(_suggestion(
                    entity, "new_medication", drug_name=drug_name, matched=matched,
                ))
            elif action == "start":
                suggestions.append(_suggestion(
                    entity, "possible_duplicate", drug_name=drug_name, matched=matched,
                ))
            # "continue" of an active listed drug: note and list agree —
            # no difference to report.
        elif action == "stop":
            if matched is not None and is_active:
                suggestions.append(_suggestion(
                    entity, "stopped_medication", drug_name=drug_name, matched=matched,
                ))
            elif matched is None:
                suggestions.append(_suggestion(
                    entity,
                    "unclear",
                    drug_name=drug_name,
                    reason=_REASON_NOT_ON_LIST,
                ))
            # stop of an already-inactive entry: note and list agree.
        else:  # increase / decrease / change
            if matched is not None:
                suggestions.append(_suggestion(
                    entity,
                    "dose_or_frequency_change",
                    drug_name=drug_name,
                    matched=matched,
                ))
            else:
                suggestions.append(_suggestion(
                    entity,
                    "unclear",
                    drug_name=drug_name,
                    reason=_REASON_NOT_ON_LIST,
                ))
    return suggestions
