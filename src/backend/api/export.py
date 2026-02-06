"""
Export API endpoints.

Generates clinician-ready summaries and data exports.
All endpoints require authentication.

Sprint 4: Wired to ExportModule for CSV/JSON/summary/questions generation.
"""

import logging
import re
from typing import Optional
from datetime import datetime, timezone
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth import RequireAuth, ProfileDbSession
from core.audit import log_export_event
from models import Observation
from modules.export import ExportModule

logger = logging.getLogger(__name__)

router = APIRouter()

# UUID validation pattern
UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
    re.IGNORECASE
)

# In-memory summary storage (for MVP - would be DB in production)
_summary_store: dict[str, dict] = {}


def validate_uuid(value: str, field_name: str = "ID") -> str:
    """Validate that a string is a valid UUID format."""
    if not UUID_PATTERN.match(value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name} format"
        )
    return value


class SummaryRequest(BaseModel):
    """Request model for generating doctor summary."""

    # Time range
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None

    # Content options
    include_all_values: bool = False  # vs only abnormal/changed
    include_trends: bool = True
    include_questions: bool = False  # "Questions to ask" section

    # Format
    format: str = "text"  # "pdf", "text", "html"


class SummaryResponse(BaseModel):
    """Response model for summary generation."""
    summary_id: str
    profile_id: str
    generated_at: str
    format: str

    # Content preview
    key_findings: list[str]
    abnormal_count: int
    date_range: str


class QuestionItem(BaseModel):
    """A discussion prompt for clinician visits."""
    category: str  # "trend", "abnormal", "clarification"
    question: str
    context: str  # Why this question is suggested
    related_analytes: list[str]


async def _fetch_observations(
    profile_db: AsyncSession,
    profile_id: str,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    analyte_filter: Optional[list[str]] = None,
) -> list[dict]:
    """
    Fetch observations from the profile database.

    Returns observations as dictionaries for use with ExportModule.
    """
    query = select(Observation).where(Observation.profile_id == profile_id)

    if from_date:
        query = query.where(Observation.collected_at >= from_date)
    if to_date:
        query = query.where(Observation.collected_at <= to_date)
    if analyte_filter:
        query = query.where(Observation.analyte_canonical.in_(analyte_filter))

    query = query.order_by(Observation.collected_at.desc(), Observation.analyte_canonical)

    result = await profile_db.execute(query)
    observations = result.scalars().all()

    # Convert to dictionaries for ExportModule
    return [
        {
            "id": obs.id,
            "analyte_canonical": obs.analyte_canonical,
            "analyte_raw": obs.analyte_raw,
            "value": obs.value,
            "value_text": obs.value_text,
            "unit": obs.unit,
            "ref_low": obs.ref_low,
            "ref_high": obs.ref_high,
            "flag": obs.flag,
            "is_abnormal": obs.is_abnormal,
            "user_verified": obs.user_verified,
            "collected_at": obs.collected_at,
        }
        for obs in observations
    ]


def _compute_trends(observations: list[dict]) -> list[dict]:
    """
    Compute trend data from observations.

    Groups by analyte and calculates direction/change.
    """
    # Group observations by analyte
    analyte_groups: dict[str, list[dict]] = {}
    for obs in observations:
        analyte = obs["analyte_canonical"]
        if analyte not in analyte_groups:
            analyte_groups[analyte] = []
        analyte_groups[analyte].append(obs)

    trends = []
    for analyte, obs_list in analyte_groups.items():
        # Sort by date
        sorted_obs = sorted(
            [o for o in obs_list if o.get("collected_at") and o.get("value") is not None],
            key=lambda x: x["collected_at"]
        )

        if len(sorted_obs) < 2:
            continue

        first_val = sorted_obs[0]["value"]
        last_val = sorted_obs[-1]["value"]

        if first_val == 0:
            continue

        delta_percent = ((last_val - first_val) / first_val) * 100

        if abs(delta_percent) < 5:
            direction = "stable"
        elif delta_percent > 0:
            direction = "up"
        else:
            direction = "down"

        trends.append({
            "analyte": analyte,
            "trend_direction": direction,
            "delta_percent": abs(delta_percent),
        })

    return trends


@router.post("/doctor-summary", response_model=SummaryResponse)
async def generate_doctor_summary(
    request: SummaryRequest,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Generate a clinician-ready summary.

    Creates a 1-2 page summary with:
    - Key values and dates
    - Trend highlights
    - Abnormal values with context
    - Exact values and collection dates
    - Citations to source documents

    Creates audit log entry.
    Only includes data from the authenticated profile.
    """
    profile_id = session.profile_id

    # Fetch observations from profile database
    observations = await _fetch_observations(
        profile_db,
        profile_id,
        from_date=request.from_date,
        to_date=request.to_date,
    )

    # Compute trends
    trends = _compute_trends(observations) if request.include_trends else []

    # Generate summary using ExportModule
    export_module = ExportModule()
    summary = await export_module.generate_doctor_summary(
        profile_id=profile_id,
        observations=observations,
        trends=trends,
        from_date=request.from_date,
        to_date=request.to_date,
        include_all_values=request.include_all_values,
        include_trends=request.include_trends,
    )

    # Store summary for later download
    summary_data = {
        "summary_id": summary.summary_id,
        "profile_id": profile_id,
        "generated_at": summary.generated_at.isoformat(),
        "format": request.format,
        "key_findings": summary.key_findings,
        "sections": [{"title": s.title, "content": s.content} for s in summary.sections],
        "total_observations": summary.total_observations,
        "abnormal_count": summary.abnormal_count,
        "critical_count": summary.critical_count,
    }
    _summary_store[summary.summary_id] = summary_data

    # Create audit log
    try:
        await log_export_event(
            db=master_db,
            profile_id=profile_id,
            export_type="doctor_summary",
            details={
                "summary_id": summary.summary_id,
                "format": request.format,
                "observation_count": summary.total_observations,
            },
        )
        await master_db.commit()
    except Exception as e:
        logger.warning(f"Failed to log export event: {e}")

    # Build date range string
    date_range = "All time"
    if request.from_date and request.to_date:
        date_range = f"{request.from_date.strftime('%Y-%m-%d')} to {request.to_date.strftime('%Y-%m-%d')}"
    elif request.from_date:
        date_range = f"Since {request.from_date.strftime('%Y-%m-%d')}"
    elif request.to_date:
        date_range = f"Until {request.to_date.strftime('%Y-%m-%d')}"

    return SummaryResponse(
        summary_id=summary.summary_id,
        profile_id=profile_id,
        generated_at=summary.generated_at.isoformat(),
        format=request.format,
        key_findings=summary.key_findings,
        abnormal_count=summary.abnormal_count,
        date_range=date_range,
    )


@router.get("/doctor-summary/{summary_id}/download")
async def download_summary(
    summary_id: str,
    session: RequireAuth,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Download a previously generated summary.

    Returns the summary file in text format.
    Verifies the summary belongs to the authenticated profile.
    """
    validate_uuid(summary_id, "summary_id")

    # Retrieve from store
    summary_data = _summary_store.get(summary_id)

    if not summary_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Summary not found"
        )

    # Verify ownership
    if summary_data["profile_id"] != session.profile_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this summary"
        )

    # Build text content
    lines = [
        "=" * 60,
        "HEALTH SUMMARY REPORT",
        "=" * 60,
        "",
        f"Generated: {summary_data['generated_at']}",
        f"Total Observations: {summary_data['total_observations']}",
        f"Abnormal Values: {summary_data['abnormal_count']}",
        f"Critical Values: {summary_data['critical_count']}",
        "",
    ]

    if summary_data["key_findings"]:
        lines.append("-" * 40)
        lines.append("KEY FINDINGS")
        lines.append("-" * 40)
        for finding in summary_data["key_findings"]:
            lines.append(f"  - {finding}")
        lines.append("")

    for section in summary_data["sections"]:
        lines.append("-" * 40)
        lines.append(section["title"].upper())
        lines.append("-" * 40)
        lines.append(section["content"])
        lines.append("")

    lines.append("=" * 60)
    lines.append("This summary was generated by HealthCentral based on")
    lines.append("uploaded laboratory reports. This is not medical advice.")
    lines.append("Discuss all results with your healthcare provider.")
    lines.append("=" * 60)

    content = "\n".join(lines)

    # Log download
    try:
        await log_export_event(
            db=master_db,
            profile_id=session.profile_id,
            export_type="summary_download",
            details={"summary_id": summary_id},
        )
        await master_db.commit()
    except Exception as e:
        logger.warning(f"Failed to log export event: {e}")

    return Response(
        content=content,
        media_type="text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="health_summary_{summary_id[:8]}.txt"'
        }
    )


@router.post("/questions", response_model=list[QuestionItem])
async def generate_questions(
    session: RequireAuth,
    from_date: Optional[datetime] = Query(None, description="Start date"),
    to_date: Optional[datetime] = Query(None, description="End date"),
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Generate discussion prompts for clinician visits.

    User-initiated only. Framed as discussion prompts,
    not medical advice.
    Only includes data from the authenticated profile.
    """
    profile_id = session.profile_id

    # Fetch observations from profile database
    observations = await _fetch_observations(
        profile_db,
        profile_id,
        from_date=from_date,
        to_date=to_date,
    )

    # Compute trends
    trends = _compute_trends(observations)

    # Generate questions using ExportModule
    export_module = ExportModule()
    questions = export_module.generate_questions(
        observations=observations,
        trends=trends,
    )

    # Log generation
    try:
        await log_export_event(
            db=master_db,
            profile_id=profile_id,
            export_type="questions",
            details={"question_count": len(questions)},
        )
        await master_db.commit()
    except Exception as e:
        logger.warning(f"Failed to log export event: {e}")

    return [
        QuestionItem(
            category=q.category,
            question=q.question,
            context=q.context,
            related_analytes=q.related_analytes,
        )
        for q in questions
    ]


@router.get("/csv")
async def export_csv(
    session: RequireAuth,
    analytes: Optional[str] = Query(None, description="Comma-separated analyte filter"),
    from_date: Optional[datetime] = Query(None, description="Start date"),
    to_date: Optional[datetime] = Query(None, description="End date"),
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Export observations as CSV.

    Only includes data from the authenticated profile.
    Creates audit log entry.
    """
    profile_id = session.profile_id

    # Parse analyte filter
    analyte_filter = None
    if analytes:
        analyte_filter = [a.strip().lower() for a in analytes.split(",")]

    # Fetch observations from profile database
    observations = await _fetch_observations(
        profile_db,
        profile_id,
        from_date=from_date,
        to_date=to_date,
        analyte_filter=analyte_filter,
    )

    # Generate CSV using ExportModule
    export_module = ExportModule()
    csv_content = export_module.export_csv(observations)

    # Log export
    try:
        await log_export_event(
            db=master_db,
            profile_id=profile_id,
            export_type="csv",
            details={"observation_count": len(observations)},
        )
        await master_db.commit()
    except Exception as e:
        logger.warning(f"Failed to log export event: {e}")

    # Generate filename with date
    filename = f"health_data_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/json")
async def export_json(
    session: RequireAuth,
    analytes: Optional[str] = Query(None, description="Comma-separated analyte filter"),
    from_date: Optional[datetime] = Query(None, description="Start date"),
    to_date: Optional[datetime] = Query(None, description="End date"),
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Export observations as JSON.

    Only includes data from the authenticated profile.
    Creates audit log entry.
    """
    profile_id = session.profile_id

    # Parse analyte filter
    analyte_filter = None
    if analytes:
        analyte_filter = [a.strip().lower() for a in analytes.split(",")]

    # Fetch observations from profile database
    observations = await _fetch_observations(
        profile_db,
        profile_id,
        from_date=from_date,
        to_date=to_date,
        analyte_filter=analyte_filter,
    )

    # Generate JSON using ExportModule
    export_module = ExportModule()
    json_content = export_module.export_json(observations)

    # Log export
    try:
        await log_export_event(
            db=master_db,
            profile_id=profile_id,
            export_type="json",
            details={"observation_count": len(observations)},
        )
        await master_db.commit()
    except Exception as e:
        logger.warning(f"Failed to log export event: {e}")

    # Generate filename with date
    filename = f"health_data_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"

    return Response(
        content=json_content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
