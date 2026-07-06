"""
Observation (lab values) API endpoints.

Handles retrieval, filtering, verification, and trend data.
All endpoints require authentication.

Phase 3: Observations are now stored in per-profile encrypted databases.
Uses ProfileDbSession for database access instead of master database.
"""

import json
import logging
import re
from collections import defaultdict
from typing import Optional
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.audit import audit_and_commit, log_observation_event
from core.auth import RequireAuth, Session, ProfileDbSession
from models import Document, Observation
from modules.normalize import (
    canonical_unit_for,
    convert_to_canonical,
    normalize_unit,
)

logger = logging.getLogger(__name__)

# UUID validation pattern
UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
    re.IGNORECASE
)


def validate_uuid(value: str, field_name: str = "ID") -> str:
    """Validate that a string is a valid UUID format."""
    if not UUID_PATTERN.match(value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name} format"
        )
    return value


def verify_observation_access(observation: Observation, session: Session) -> None:
    """
    Verify that the session has access to the observation.

    Args:
        observation: The observation to check access for
        session: The authenticated session

    Raises:
        HTTPException: 403 if access is denied
    """
    if observation.profile_id != session.profile_id:
        logger.warning(
            f"Observation access denied: session profile {session.profile_id} "
            f"attempted to access observation {observation.id} belonging to {observation.profile_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this observation"
        )


router = APIRouter()


# Panel definitions - maps panel IDs to canonical analyte names
PANEL_DEFINITIONS = {
    "cbc": {
        "name": "Complete Blood Count",
        "analytes": ["wbc", "rbc", "hemoglobin", "hematocrit", "mcv", "mch", "mchc", "rdw", "platelets", "mpv"],
    },
    "cmp": {
        "name": "Comprehensive Metabolic Panel",
        "analytes": ["glucose", "bun", "creatinine", "sodium", "potassium", "chloride", "co2", "calcium", "protein_total", "albumin", "bilirubin_total", "alkaline_phosphatase", "ast", "alt"],
    },
    "lipid": {
        "name": "Lipid Panel",
        "analytes": ["cholesterol_total", "triglycerides", "hdl", "ldl", "vldl"],
    },
    "thyroid": {
        "name": "Thyroid Panel",
        "analytes": ["tsh", "t3_free", "t4_free", "t3_total", "t4_total"],
    },
}


class ObservationResponse(BaseModel):
    """Response model for observation data."""
    id: str
    profile_id: str
    doc_id: str
    analyte_canonical: str
    analyte_raw: str
    value: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    ref_low: Optional[float] = None
    ref_high: Optional[float] = None
    ref_range_text: Optional[str] = None
    flag: Optional[str] = None
    is_abnormal: Optional[bool] = None
    collected_at: Optional[str] = None
    user_verified: bool
    extraction_confidence: Optional[float] = None
    source_page: Optional[int] = None
    source_bbox_json: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, obs: Observation) -> "ObservationResponse":
        return cls(
            id=obs.id,
            profile_id=obs.profile_id,
            doc_id=obs.doc_id,
            analyte_canonical=obs.analyte_canonical,
            analyte_raw=obs.analyte_raw,
            value=obs.value,
            value_text=obs.value_text,
            unit=obs.unit,
            ref_low=obs.ref_low,
            ref_high=obs.ref_high,
            ref_range_text=obs.ref_range_text,
            flag=obs.flag,
            is_abnormal=obs.is_abnormal,
            collected_at=obs.collected_at.isoformat() if obs.collected_at else None,
            user_verified=obs.user_verified,
            extraction_confidence=obs.extraction_confidence,
            source_page=obs.source_page,
            source_bbox_json=obs.source_bbox_json,
        )


class ObservationVerify(BaseModel):
    """Request model for verifying/editing an observation."""
    value: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    ref_low: Optional[float] = None
    ref_high: Optional[float] = None
    collected_at: Optional[datetime] = None
    notes: Optional[str] = None


class TrendPoint(BaseModel):
    """Single point in a trend series."""
    date: str
    value: float
    unit: str
    is_abnormal: bool
    flag: Optional[str] = None
    doc_id: str
    extraction_confidence: Optional[float] = None
    # Provenance when the point was converted from a differently-reported unit
    # (NORM-UNIT-001). Both None when no conversion happened.
    original_value: Optional[float] = None
    original_unit: Optional[str] = None


class TrendResponse(BaseModel):
    """Response model for analyte trend data."""
    analyte_canonical: str
    analyte_display_name: str
    unit: str
    ref_low: Optional[float] = None
    ref_high: Optional[float] = None
    data_points: list[TrendPoint]
    excluded_count: int = 0
    summary: str  # Human-readable summary for accessibility


class PanelResponse(BaseModel):
    """Response model for lab panel (CBC, CMP, etc.)."""
    panel_id: str
    panel_name: str
    observations: list[ObservationResponse]
    collection_date: Optional[str] = None


class PanelSnapshotResponse(BaseModel):
    """One logical panel snapshot: observations from the same document and collection day."""
    collection_date: Optional[str] = None  # ISO date (calendar day) when known
    doc_id: str
    observations: list[ObservationResponse]


def _panel_analyte_sort_key(canonical: str, order: list[str]) -> int:
    try:
        return order.index(canonical)
    except ValueError:
        return 9999


@router.get("/panels/{panel_id}/snapshots", response_model=list[PanelSnapshotResponse])
async def get_panel_snapshots(
    panel_id: str,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Distinct panel snapshots grouped by source document and collection calendar day.

    Use this when a profile has multiple historical panels (e.g. several lipid panels).
    """
    profile_id = session.profile_id
    panel_def = PANEL_DEFINITIONS.get(panel_id.lower())
    if not panel_def:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown panel: {panel_id}",
        )

    query = (
        select(Observation)
        .where(
            and_(
                Observation.profile_id == profile_id,
                Observation.analyte_canonical.in_(panel_def["analytes"]),
            )
        )
        .order_by(Observation.collected_at.desc())
    )
    result = await profile_db.execute(query)
    all_obs = result.scalars().all()

    groups: dict[tuple[str, Optional[date]], list[Observation]] = defaultdict(list)
    for obs in all_obs:
        day = obs.collected_at.date() if obs.collected_at else None
        groups[(obs.doc_id, day)].append(obs)

    snapshots: list[PanelSnapshotResponse] = []
    analyte_order = panel_def["analytes"]
    for (doc_id, day), obs_list in groups.items():
        by_analyte: dict[str, Observation] = {}
        for o in sorted(
            obs_list,
            key=lambda x: (x.extraction_confidence or 0.0),
            reverse=True,
        ):
            if o.analyte_canonical not in by_analyte:
                by_analyte[o.analyte_canonical] = o
        chosen = list(by_analyte.values())
        chosen.sort(key=lambda o: _panel_analyte_sort_key(o.analyte_canonical, analyte_order))
        snapshots.append(
            PanelSnapshotResponse(
                collection_date=day.isoformat() if day else None,
                doc_id=doc_id,
                observations=[ObservationResponse.from_model(o) for o in chosen],
            )
        )

    def sort_snap(s: PanelSnapshotResponse) -> tuple:
        # Newest calendar date first; missing date last
        key_date = s.collection_date or "0000-01-01"
        return (key_date, s.doc_id)

    snapshots.sort(key=sort_snap, reverse=True)

    await audit_and_commit(
        master_db,
        log_observation_event,
        event="view",
        profile_id=profile_id,
        observation_id="all",
        analyte=panel_id.lower(),
        details={"action": "panel_snapshots", "count": len(snapshots)},
    )

    return snapshots


@router.get("/", response_model=list[ObservationResponse])
async def list_observations(
    session: RequireAuth,
    analyte: Optional[str] = Query(None, description="Filter by analyte"),
    doc_id: Optional[str] = Query(None, description="Filter by source document ID"),
    from_date: Optional[datetime] = Query(None, description="Start date"),
    to_date: Optional[datetime] = Query(None, description="End date"),
    abnormal_only: bool = Query(False, description="Only show abnormal values"),
    needs_verification: bool = Query(False, description="Only show unverified"),
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    List observations for the authenticated profile.

    Phase 3: Queries per-profile encrypted database.
    Supports filtering by analyte, date range, abnormal status,
    and verification status.
    """
    profile_id = session.profile_id

    # Build query with filters - observations are in per-profile database
    query = select(Observation).where(Observation.profile_id == profile_id)

    if analyte:
        query = query.where(Observation.analyte_canonical == analyte.lower())

    if doc_id:
        validate_uuid(doc_id, "doc_id")
        query = query.where(Observation.doc_id == doc_id)

    if from_date:
        query = query.where(Observation.collected_at >= from_date)

    if to_date:
        query = query.where(Observation.collected_at <= to_date)

    if abnormal_only:
        query = query.where(Observation.is_abnormal == True)

    if needs_verification:
        query = query.where(Observation.user_verified == False)

    query = query.order_by(Observation.collected_at.desc(), Observation.analyte_canonical)

    result = await profile_db.execute(query)
    observations = result.scalars().all()

    await audit_and_commit(
        master_db,
        log_observation_event,
        event="view",
        profile_id=profile_id,
        observation_id="all",
        analyte=analyte or "all",
        details={"action": "list", "count": len(observations)},
    )

    return [ObservationResponse.from_model(obs) for obs in observations]


@router.get("/{observation_id}", response_model=ObservationResponse)
async def get_observation(
    observation_id: str,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """Get single observation details from per-profile encrypted database."""
    # Validate observation_id format
    validate_uuid(observation_id, "observation_id")

    result = await profile_db.execute(select(Observation).where(Observation.id == observation_id))
    observation = result.scalar_one_or_none()

    if not observation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Observation not found"
        )

    # Verify session has access to this observation
    verify_observation_access(observation, session)

    await audit_and_commit(
        master_db,
        log_observation_event,
        event="view",
        profile_id=observation.profile_id,
        observation_id=observation_id,
        analyte=observation.analyte_canonical,
    )

    return ObservationResponse.from_model(observation)


@router.post("/{observation_id}/verify", response_model=ObservationResponse)
async def verify_observation(
    observation_id: str,
    verify_data: ObservationVerify,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Verify and optionally edit an observation.

    Phase 3: Observation in per-profile DB, audit log in master DB.

    - Applies user edits (value, unit, dates, etc.)
    - Tracks original values for audit
    - Marks as verified
    - Creates audit log entry
    """
    # Validate observation_id format
    validate_uuid(observation_id, "observation_id")

    result = await profile_db.execute(select(Observation).where(Observation.id == observation_id))
    observation = result.scalar_one_or_none()

    if not observation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Observation not found"
        )

    # Verify session has access to this observation
    verify_observation_access(observation, session)

    # Store original values if this is first edit
    if not observation.original_value_json:
        original = {
            "value": observation.value,
            "value_text": observation.value_text,
            "unit": observation.unit,
            "ref_low": observation.ref_low,
            "ref_high": observation.ref_high,
            "collected_at": observation.collected_at.isoformat() if observation.collected_at else None,
        }
        observation.original_value_json = json.dumps(original)

    # Apply edits
    changes = {}
    if verify_data.value is not None:
        changes["value"] = {"old": observation.value, "new": verify_data.value}
        observation.value = verify_data.value

    if verify_data.value_text is not None:
        changes["value_text"] = {"old": observation.value_text, "new": verify_data.value_text}
        observation.value_text = verify_data.value_text

    if verify_data.unit is not None:
        changes["unit"] = {"old": observation.unit, "new": verify_data.unit}
        observation.unit = verify_data.unit

    if verify_data.ref_low is not None:
        changes["ref_low"] = {"old": observation.ref_low, "new": verify_data.ref_low}
        observation.ref_low = verify_data.ref_low

    if verify_data.ref_high is not None:
        changes["ref_high"] = {"old": observation.ref_high, "new": verify_data.ref_high}
        observation.ref_high = verify_data.ref_high

    if verify_data.collected_at is not None:
        changes["collected_at"] = {
            "old": observation.collected_at.isoformat() if observation.collected_at else None,
            "new": verify_data.collected_at.isoformat(),
        }
        observation.collected_at = verify_data.collected_at

    if verify_data.notes is not None:
        observation.notes = verify_data.notes

    # Mark as verified
    observation.user_verified = True
    observation.verified_at = datetime.utcnow()
    observation.version += 1

    # Recalculate abnormal status
    if observation.value is not None:
        if observation.ref_low is not None and observation.value < observation.ref_low:
            observation.is_abnormal = True
            observation.flag = "L"
        elif observation.ref_high is not None and observation.value > observation.ref_high:
            observation.is_abnormal = True
            observation.flag = "H"
        else:
            observation.is_abnormal = False
            observation.flag = None

    await profile_db.flush()

    remaining = await profile_db.execute(
        select(Observation.id).where(
            Observation.doc_id == observation.doc_id,
            Observation.user_verified.is_(False),
        )
    )
    if remaining.first() is None:
        doc_result = await profile_db.execute(
            select(Document).where(Document.id == observation.doc_id)
        )
        document = doc_result.scalar_one_or_none()
        if document is not None and document.status != "verified":
            document.status = "verified"
            document.verified_at = datetime.utcnow()

    await profile_db.commit()

    # Create audit log in master database
    await log_observation_event(
        db=master_db,
        event="verify",
        profile_id=observation.profile_id,
        observation_id=observation_id,
        analyte=observation.analyte_canonical,
        details={"changes": changes} if changes else None,
    )
    await master_db.commit()

    return ObservationResponse.from_model(observation)


@router.get("/trends/{analyte}", response_model=TrendResponse)
async def get_analyte_trend(
    analyte: str,
    session: RequireAuth,
    from_date: Optional[datetime] = Query(None, description="Start date"),
    to_date: Optional[datetime] = Query(None, description="End date"),
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Get trend data for a specific analyte.

    Phase 3: Queries per-profile encrypted database.
    Returns time-series data points with reference ranges
    and a human-readable summary for accessibility.
    """
    profile_id = session.profile_id

    # Build query
    query = select(Observation).where(
        and_(
            Observation.profile_id == profile_id,
            Observation.analyte_canonical == analyte.lower(),
            Observation.value.isnot(None),
        )
    )

    if from_date:
        query = query.where(Observation.collected_at >= from_date)
    if to_date:
        query = query.where(Observation.collected_at <= to_date)

    query = query.order_by(Observation.collected_at.asc())

    result = await profile_db.execute(query)
    observations = result.scalars().all()

    if not observations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data found for analyte '{analyte}'"
        )

    analyte_key = analyte.lower()
    canonical_unit = canonical_unit_for(analyte_key)
    conversions = [
        (obs, convert_to_canonical(analyte_key, obs.value, obs.unit))
        for obs in observations
    ]
    distinct_units = {normalize_unit(o.unit) for o in observations if o.unit}
    any_convertible = any(conv is not None for _, conv in conversions)
    normalize_units = canonical_unit is not None and len(distinct_units) > 1 and any_convertible
    mixed_unnormalized = len(distinct_units) > 1 and not normalize_units

    data_points = []
    undated_count = 0
    ref_low = None
    ref_high = None
    unit = None
    excluded_count = 0
    ref_source_both = None
    ref_source_any = None

    for obs, conv in conversions:
        emitted = True
        if normalize_units:
            if conv is None:
                excluded_count += 1
                emitted = False
            else:
                point_value = conv.canonical_value
                point_unit = canonical_unit or ""
                original_value = conv.original_value if conv.converted else None
                original_unit = conv.original_unit if conv.converted else None
                unit = canonical_unit
        else:
            point_value = obs.value
            point_unit = obs.unit or ""
            original_value = None
            original_unit = None
            if obs.unit:
                unit = obs.unit

        if emitted:
            if obs.ref_low is not None and obs.ref_high is not None:
                ref_source_both = obs
            elif obs.ref_low is not None or obs.ref_high is not None:
                ref_source_any = obs

            if obs.collected_at and obs.value is not None:
                data_points.append(TrendPoint(
                    date=obs.collected_at.isoformat(),
                    value=point_value,
                    unit=point_unit,
                    is_abnormal=obs.is_abnormal or False,
                    flag=obs.flag,
                    doc_id=obs.doc_id,
                    extraction_confidence=obs.extraction_confidence,
                    original_value=original_value,
                    original_unit=original_unit,
                ))
            elif obs.value is not None:
                # Has a value but no date — count it so the summary is accurate
                undated_count += 1

    ref_source = ref_source_both or ref_source_any
    if ref_source is not None:
        if normalize_units:
            ref_low_conv = None
            ref_high_conv = None
            if ref_source.ref_low is not None:
                ref_low_result = convert_to_canonical(
                    analyte_key,
                    ref_source.ref_low,
                    ref_source.unit,
                )
                if ref_low_result is not None:
                    ref_low_conv = ref_low_result.canonical_value
            if ref_source.ref_high is not None:
                ref_high_result = convert_to_canonical(
                    analyte_key,
                    ref_source.ref_high,
                    ref_source.unit,
                )
                if ref_high_result is not None:
                    ref_high_conv = ref_high_result.canonical_value

            if (
                (ref_source.ref_low is None or ref_low_conv is not None)
                and (ref_source.ref_high is None or ref_high_conv is not None)
            ):
                ref_low = ref_low_conv
                ref_high = ref_high_conv
            else:
                ref_low = ref_source.ref_low
                ref_high = ref_source.ref_high
        else:
            ref_low = ref_source.ref_low
            ref_high = ref_source.ref_high

    # Generate summary
    total_count = len(data_points) + undated_count
    suppress_delta = mixed_unnormalized or (canonical_unit is not None and not any_convertible)
    if len(data_points) >= 2 and not suppress_delta:
        first_val = data_points[0].value
        last_val = data_points[-1].value
        change = last_val - first_val
        change_pct = (change / first_val * 100) if first_val != 0 else 0

        if abs(change_pct) < 5:
            trend = "stable"
        elif change > 0:
            trend = f"increased by {abs(change_pct):.1f}%"
        else:
            trend = f"decreased by {abs(change_pct):.1f}%"

        summary = f"{analyte.upper()} has {trend} over {len(data_points)} dated measurements."
        if undated_count:
            summary += f" {undated_count} additional measurement(s) have no collection date and are not shown on the chart."
    elif len(data_points) >= 2 and suppress_delta:
        if mixed_unnormalized:
            summary = (
                f"{analyte.upper()} has {len(data_points)} dated measurements recorded in multiple units; "
                "change across units is not computed."
            )
        else:
            summary = (
                f"{analyte.upper()} has {len(data_points)} dated measurements recorded, "
                "but the unit is not recognized for this analyte; change across units is not computed."
            )
        if undated_count:
            summary += f" {undated_count} additional measurement(s) have no collection date and are not shown on the chart."
    elif len(data_points) == 1:
        summary = f"Single dated measurement of {analyte.upper()} recorded."
        if undated_count:
            summary += f" {undated_count} additional measurement(s) have no collection date."
    elif undated_count or excluded_count:
        # No dated points at all — return a response with empty data_points but
        # a helpful summary rather than 404, so the UI can show the latest-values table.
        hidden_note = ""
        if excluded_count:
            hidden_note = (
                f" {excluded_count} measurement(s) hidden — unit not recognized for this analyte."
            )
        summary = (
            f"{total_count + excluded_count} measurement(s) of {analyte.upper()} found, "
            f"but none have a collection date so no trend line can be drawn."
            f"{hidden_note} "
            f"Use the analyte list to see the latest value."
        )
    else:
        summary = f"Single measurement of {analyte.upper()} recorded."

    if normalize_units:
        summary += f" Values normalized to {canonical_unit} for comparison across labs."

    if excluded_count > 0 and len(data_points) > 0:
        summary += f" {excluded_count} measurement(s) hidden — unit not recognized for this analyte."

    await audit_and_commit(
        master_db,
        log_observation_event,
        event="view",
        profile_id=profile_id,
        observation_id=analyte,
        analyte=analyte,
        details={"action": "trend", "count": len(data_points)},
    )

    return TrendResponse(
        analyte_canonical=analyte.lower(),
        analyte_display_name=analyte.upper(),
        unit=unit or "",
        ref_low=ref_low,
        ref_high=ref_high,
        data_points=data_points,
        excluded_count=excluded_count,
        summary=summary,
    )


@router.get("/panels/{panel_id}", response_model=PanelResponse)
async def get_panel(
    panel_id: str,
    session: RequireAuth,
    collection_date: Optional[datetime] = Query(None, description="Specific collection date"),
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Get lab panel data (CBC, CMP, lipids, etc.).

    When ``collection_date`` is omitted, returns the **most recent value per analyte
    across all documents** (not necessarily a single draw). For separate historical
    panels, use ``GET /observations/panels/{panel_id}/snapshots``.
    """
    profile_id = session.profile_id

    panel_def = PANEL_DEFINITIONS.get(panel_id.lower())
    if not panel_def:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown panel: {panel_id}"
        )

    # Query observations for panel analytes from per-profile database
    query = select(Observation).where(
        and_(
            Observation.profile_id == profile_id,
            Observation.analyte_canonical.in_(panel_def["analytes"]),
        )
    )

    if collection_date:
        # Filter by date (within same day)
        start = collection_date.replace(hour=0, minute=0, second=0)
        end = collection_date.replace(hour=23, minute=59, second=59)
        query = query.where(
            and_(
                Observation.collected_at >= start,
                Observation.collected_at <= end,
            )
        )
    else:
        # Get most recent for each analyte
        query = query.order_by(Observation.collected_at.desc())

    result = await profile_db.execute(query)
    observations = result.scalars().all()

    # If no collection_date specified, get only most recent per analyte
    if not collection_date:
        seen_analytes = set()
        filtered_obs = []
        for obs in observations:
            if obs.analyte_canonical not in seen_analytes:
                seen_analytes.add(obs.analyte_canonical)
                filtered_obs.append(obs)
        observations = filtered_obs

    obs_responses = [ObservationResponse.from_model(obs) for obs in observations]

    # Get collection date from observations
    coll_date = None
    if observations and observations[0].collected_at:
        coll_date = observations[0].collected_at.isoformat()

    await audit_and_commit(
        master_db,
        log_observation_event,
        event="view",
        profile_id=profile_id,
        observation_id=panel_id.lower(),
        analyte=panel_def["name"],
        details={"action": "panel", "count": len(obs_responses)},
    )

    return PanelResponse(
        panel_id=panel_id.lower(),
        panel_name=panel_def["name"],
        observations=obs_responses,
        collection_date=coll_date,
    )
