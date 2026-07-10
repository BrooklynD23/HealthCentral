"""
Health timeline API endpoint (HC-M14).

Read-only chronological view over the profile's health record:
lab observations, classified documents, and medication starts/stops.
Events are derived on read by modules/timeline.py — no timeline tables.

Follows the observations API conventions: profile scoping via the
authenticated session, data from the per-profile database, audit log
in the master database (fail-closed via audit_and_commit).
"""

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit import audit_and_commit, create_audit_log
from core.auth import ProfileDbSession, RequireAuth
from core.database import get_db
from modules.timeline import VALID_EVENT_TYPES, TimelineEvent, build_timeline

logger = logging.getLogger(__name__)

router = APIRouter()


class TimelineEventResponse(BaseModel):
    """A single derived timeline event."""

    event_id: str
    event_type: str
    event_date: Optional[str] = None
    event_date_source: Optional[str] = None
    title: str
    doc_id: Optional[str] = None
    related_ids: list[str]
    verification_status: str

    @classmethod
    def from_event(cls, event: TimelineEvent) -> "TimelineEventResponse":
        return cls(
            event_id=event.event_id,
            event_type=event.event_type,
            event_date=event.event_date,
            event_date_source=event.event_date_source,
            title=event.title,
            doc_id=event.doc_id,
            related_ids=event.related_ids,
            verification_status=event.verification_status,
        )


class TimelineResponse(BaseModel):
    """Dated events (newest first) plus undated items."""

    events: list[TimelineEventResponse]
    undated: list[TimelineEventResponse]


@router.get("/", response_model=TimelineResponse)
async def get_timeline(
    session: RequireAuth,
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    date_from: Optional[date] = Query(None, description="Inclusive start date"),
    date_to: Optional[date] = Query(None, description="Inclusive end date"),
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Chronological view of the profile's health record.

    Events are derived on read from observations, classified documents,
    and medications in the per-profile database. Items without a usable
    date are returned separately in ``undated`` (mirroring the
    undated-observation rule in the observations API).
    """
    profile_id = session.profile_id

    if event_type is not None and event_type not in VALID_EVENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown event_type. Valid values: {sorted(VALID_EVENT_TYPES)}",
        )

    result = await build_timeline(
        profile_db,
        profile_id,
        event_type=event_type,
        date_from=date_from,
        date_to=date_to,
    )

    await audit_and_commit(
        master_db,
        create_audit_log,
        event_type="timeline.view",
        action="Viewed health timeline",
        profile_id=profile_id,
        entity_type="timeline",
        entity_id="all",
        details={
            "count": len(result.events),
            "undated_count": len(result.undated),
            "event_type": event_type or "all",
        },
    )

    return TimelineResponse(
        events=[TimelineEventResponse.from_event(e) for e in result.events],
        undated=[TimelineEventResponse.from_event(e) for e in result.undated],
    )
