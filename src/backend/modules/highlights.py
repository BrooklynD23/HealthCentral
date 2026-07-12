"""Smart highlights (HC-M16).

Small organizational tags derived on read from existing data structures —
no new tables, no migrations, no LLM, no interpretation. Every highlight
resolves to a concrete source row (an extracted DocumentEntity or an
Observation) so the UI can always show where a tag came from.

Rules (strictly mechanical):

- abnormal_value: an observation flagged outside its reference range
  (``Observation.is_abnormal``).
- medication_started / medication_stopped / medication_changed: a
  ``medication_change`` entity, keyed off the canonical leading action verb
  of ``entity_value`` (see ``extract_visit_notes._canonical_med_verb``):
  start -> started, stop -> stopped, everything else -> changed.
- follow_up_needed: ``follow_up_instruction`` entities.
- test_ordered: ``test_ordered`` entities.
- referral_created: ``referral`` entities.
- new_diagnosis_mentioned: ``diagnoses`` entities.
- low_confidence_extraction: any entity with confidence below
  ``LOW_CONFIDENCE_THRESHOLD``.
- needs_verification: any entity the user has not reviewed yet
  (``verified_by_user IS NULL``).

One entity may produce several highlights. Entities the user rejected
(``verified_by_user == False``) produce none at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

LOW_CONFIDENCE_THRESHOLD = 0.6

# One-to-one entity_type -> highlight_type mappings.
_ENTITY_TYPE_HIGHLIGHTS = {
    "follow_up_instruction": "follow_up_needed",
    "test_ordered": "test_ordered",
    "referral": "referral_created",
    "diagnoses": "new_diagnosis_mentioned",
}

# Canonical leading medication_change verbs with their own highlight type;
# every other verb (increase, decrease, change, continue) is "changed".
_MED_VERB_HIGHLIGHTS = {
    "start": "medication_started",
    "stop": "medication_stopped",
}

HIGHLIGHT_TYPES = frozenset(
    {"abnormal_value", "medication_changed", "low_confidence_extraction", "needs_verification"}
    | set(_ENTITY_TYPE_HIGHLIGHTS.values())
    | set(_MED_VERB_HIGHLIGHTS.values())
)


@dataclass
class Highlight:
    """A derived tag pointing back at its source row."""

    highlight_type: str
    doc_id: str
    source_kind: str  # 'entity' | 'observation'
    source_id: str
    quote: Optional[str]  # entity verbatim quote; None for observations
    confidence: Optional[float]
    verification_state: str  # verified | unreviewed (entity) | unverified (observation)


def _medication_highlight_type(entity_value: str) -> str:
    verb = str(entity_value or "").split(maxsplit=1)
    return _MED_VERB_HIGHLIGHTS.get(verb[0].lower() if verb else "", "medication_changed")


def derive_entity_highlights(entities) -> list[Highlight]:
    """Highlights for a document's extracted entities (ORM rows)."""
    highlights: list[Highlight] = []
    for ent in entities:
        if ent.verified_by_user is False:
            continue  # user-rejected extraction: never surfaced

        types: list[str] = []
        if ent.entity_type == "medication_change":
            types.append(_medication_highlight_type(ent.entity_value))
        elif ent.entity_type in _ENTITY_TYPE_HIGHLIGHTS:
            types.append(_ENTITY_TYPE_HIGHLIGHTS[ent.entity_type])
        if ent.confidence is not None and ent.confidence < LOW_CONFIDENCE_THRESHOLD:
            types.append("low_confidence_extraction")
        if ent.verified_by_user is None:
            types.append("needs_verification")

        state = "verified" if ent.verified_by_user else "unreviewed"
        highlights.extend(
            Highlight(
                highlight_type=highlight_type,
                doc_id=ent.doc_id,
                source_kind="entity",
                source_id=ent.id,
                quote=ent.quote,
                confidence=ent.confidence,
                verification_state=state,
            )
            for highlight_type in types
        )
    return highlights


def derive_observation_highlights(observations) -> list[Highlight]:
    """abnormal_value highlights for observations flagged out of range."""
    return [
        Highlight(
            highlight_type="abnormal_value",
            doc_id=obs.doc_id,
            source_kind="observation",
            source_id=obs.id,
            quote=None,
            confidence=obs.extraction_confidence,
            verification_state="verified" if obs.user_verified else "unverified",
        )
        for obs in observations
        if obs.is_abnormal
    ]


def derive_highlights(entities, observations) -> list[Highlight]:
    """All highlights for one or more documents' entities and observations."""
    return derive_observation_highlights(observations) + derive_entity_highlights(entities)
