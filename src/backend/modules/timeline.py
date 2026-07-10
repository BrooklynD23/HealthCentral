"""Health timeline read-model (HC-M14).

Derives a chronological event stream for a profile on read — no new
tables, no migrations. Sources (all in the per-profile database):

- Observations: one ``lab_results`` event per (document, collection day),
  not one per analyte. Observations without a collection date follow the
  undated-observation rule from ``api/observations.py``: they never enter
  the dated stream and are returned separately in ``undated``.
- Classified documents (``document_category``): one event per document in
  the named categories (imaging, pathology, visit_notes) at the best
  available date, with precedence:
  document.collection_date ('document_date') > parseable date entity
  ('entity_date') > imported_at ('upload_date'). Documents classified as
  'lab' are already represented by their lab_results events.
- Medications: a ``medication_start`` event at ``started_at`` and, when
  ``ended_at`` is set, a ``medication_stop`` event.

Event IDs are deterministic (derived from source row IDs and dates) so
clients can key on them across refreshes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Document, DocumentCategory, DocumentEntity, Medication, Observation
from modules.extract import ExtractModule

logger = logging.getLogger(__name__)

# Categories that produce document events (classifier also emits 'lab' and
# 'unknown'; lab docs surface via lab_results events, unknown stays out).
DOCUMENT_EVENT_CATEGORIES = {"imaging", "pathology", "visit_notes"}

# Entity types that carry a document-level date (see extract_imaging,
# extract_pathology, extract_visit_notes).
DATE_ENTITY_TYPES = {"report_date", "visit_date"}

VALID_EVENT_TYPES = DOCUMENT_EVENT_CATEGORIES | {
    "lab_results",
    "medication_start",
    "medication_stop",
}

_CATEGORY_TITLES = {
    "imaging": "Imaging report",
    "pathology": "Pathology report",
    "visit_notes": "Visit note",
}


@dataclass
class TimelineEvent:
    """A single derived timeline event."""

    event_id: str
    event_type: str
    event_date: Optional[str]  # ISO-8601 calendar date; None only in `undated`
    event_date_source: Optional[str]  # document_date|entity_date|upload_date|recorded_date
    title: str
    doc_id: Optional[str]
    related_ids: list[str] = field(default_factory=list)
    verification_status: str = "n/a"  # verified|unverified|mixed|n/a


@dataclass
class TimelineResult:
    """Dated events (newest first) plus undated items."""

    events: list[TimelineEvent]
    undated: list[TimelineEvent]


def _verification_from_flags(flags: list[bool]) -> str:
    if all(flags):
        return "verified"
    if not any(flags):
        return "unverified"
    return "mixed"


async def _lab_events(
    db: AsyncSession, profile_id: str
) -> tuple[list[TimelineEvent], list[TimelineEvent]]:
    """One event per (doc_id, collection day); undated groups separated."""
    result = await db.execute(
        select(Observation).where(Observation.profile_id == profile_id)
    )
    observations = result.scalars().all()

    groups: dict[tuple[str, Optional[date]], list[Observation]] = {}
    for obs in observations:
        day = obs.collected_at.date() if obs.collected_at else None
        groups.setdefault((obs.doc_id, day), []).append(obs)

    dated: list[TimelineEvent] = []
    undated: list[TimelineEvent] = []
    for (doc_id, day), obs_list in groups.items():
        analyte_count = len({o.analyte_canonical for o in obs_list})
        plural = "s" if analyte_count != 1 else ""
        event = TimelineEvent(
            event_id=f"lab:{doc_id}:{day.isoformat() if day else 'undated'}",
            event_type="lab_results",
            event_date=day.isoformat() if day else None,
            event_date_source="recorded_date" if day else None,
            title=f"Lab results ({analyte_count} analyte{plural})",
            doc_id=doc_id,
            related_ids=sorted(o.id for o in obs_list),
            verification_status=_verification_from_flags(
                [o.user_verified for o in obs_list]
            ),
        )
        (dated if day else undated).append(event)
    return dated, undated


def _entity_date(entities: list[DocumentEntity]) -> tuple[Optional[str], Optional[str]]:
    """Return (ISO date, entity_id) from the highest-confidence parseable
    date entity, or (None, None)."""
    for entity in sorted(entities, key=lambda e: e.confidence, reverse=True):
        parsed = ExtractModule._normalize_date_str(entity.entity_value)
        if parsed:
            return parsed, entity.id
    return None, None


async def _document_events(db: AsyncSession, profile_id: str) -> list[TimelineEvent]:
    """One event per classified (imaging/pathology/visit_notes) document."""
    result = await db.execute(
        select(Document, DocumentCategory)
        .join(DocumentCategory, DocumentCategory.doc_id == Document.id)
        .where(
            Document.profile_id == profile_id,
            DocumentCategory.category.in_(DOCUMENT_EVENT_CATEGORIES),
        )
    )
    rows = result.all()
    if not rows:
        return []

    doc_ids = [doc.id for doc, _cat in rows]
    entity_result = await db.execute(
        select(DocumentEntity).where(
            DocumentEntity.doc_id.in_(doc_ids),
            DocumentEntity.entity_type.in_(DATE_ENTITY_TYPES),
        )
    )
    entities_by_doc: dict[str, list[DocumentEntity]] = {}
    for entity in entity_result.scalars().all():
        entities_by_doc.setdefault(entity.doc_id, []).append(entity)

    events: list[TimelineEvent] = []
    for doc, category in rows:
        related_ids: list[str] = []
        if doc.collection_date:
            event_date = doc.collection_date.date().isoformat()
            date_source = "document_date"
        else:
            event_date, entity_id = _entity_date(entities_by_doc.get(doc.id, []))
            if event_date:
                date_source = "entity_date"
                related_ids = [entity_id]
            else:
                event_date = doc.imported_at.date().isoformat()
                date_source = "upload_date"

        title = _CATEGORY_TITLES.get(category.category, "Document")
        if doc.source:
            filename = doc.source.replace("\\", "/").rsplit("/", 1)[-1]
            title = f"{title} — {filename}"

        events.append(
            TimelineEvent(
                event_id=f"doc:{doc.id}",
                event_type=category.category,
                event_date=event_date,
                event_date_source=date_source,
                title=title,
                doc_id=doc.id,
                related_ids=related_ids,
                verification_status=(
                    "verified" if doc.status == "verified" else "unverified"
                ),
            )
        )
    return events


async def _medication_events(db: AsyncSession, profile_id: str) -> list[TimelineEvent]:
    """Start events for every medication; stop events when ended_at is set."""
    result = await db.execute(
        select(Medication).where(Medication.profile_id == profile_id)
    )
    events: list[TimelineEvent] = []
    for med in result.scalars().all():
        events.append(
            TimelineEvent(
                event_id=f"med-start:{med.id}",
                event_type="medication_start",
                event_date=med.started_at.date().isoformat(),
                event_date_source="recorded_date",
                title=f"Started medication: {med.name}",
                doc_id=None,
                related_ids=[med.id],
                verification_status="n/a",
            )
        )
        if med.ended_at:
            events.append(
                TimelineEvent(
                    event_id=f"med-stop:{med.id}",
                    event_type="medication_stop",
                    event_date=med.ended_at.date().isoformat(),
                    event_date_source="recorded_date",
                    title=f"Stopped medication: {med.name}",
                    doc_id=None,
                    related_ids=[med.id],
                    verification_status="n/a",
                )
            )
    return events


async def build_timeline(
    db: AsyncSession,
    profile_id: str,
    event_type: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> TimelineResult:
    """Derive the timeline for *profile_id* from the per-profile database.

    Args:
        db: Per-profile database session (never the master DB).
        profile_id: Profile whose data is queried; every source query
            filters on it.
        event_type: Optional filter; one of ``VALID_EVENT_TYPES``.
        date_from / date_to: Optional inclusive calendar-date bounds,
            applied to the dated stream only.

    Returns:
        TimelineResult with dated events sorted newest first and undated
        items (currently: observation groups lacking a collection date).
    """
    lab_dated, lab_undated = await _lab_events(db, profile_id)
    doc_events = await _document_events(db, profile_id)
    med_events = await _medication_events(db, profile_id)

    events = lab_dated + doc_events + med_events
    undated = lab_undated

    if event_type:
        events = [e for e in events if e.event_type == event_type]
        undated = [e for e in undated if e.event_type == event_type]

    if date_from:
        bound = date_from.isoformat()
        events = [e for e in events if e.event_date >= bound]
    if date_to:
        bound = date_to.isoformat()
        events = [e for e in events if e.event_date <= bound]

    # ISO-8601 strings sort chronologically; event_id tiebreak for determinism
    events.sort(key=lambda e: (e.event_date, e.event_id), reverse=True)
    undated.sort(key=lambda e: e.event_id)

    return TimelineResult(events=events, undated=undated)
