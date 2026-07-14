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
from core.audit import audit_and_commit, log_export_event
from models import CarePlanTask, Document, Medication, Observation
from models.document_category import DocumentEntity
from modules.export import ExportModule
from modules.normalize import canonical_unit_for, convert_to_canonical, normalize_unit

logger = logging.getLogger(__name__)

router = APIRouter()

# UUID validation pattern
UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
    re.IGNORECASE
)

# In-memory summary storage (for MVP - would be DB in production)
_summary_store: dict[str, dict] = {}

# In-memory visit-prep packet storage (HC-M18; same MVP pattern as summaries)
_packet_store: dict[str, dict] = {}

# Visit-note entity types that generate doctor questions (HC-M17).
QUESTION_ENTITY_TYPES = ("medication_change", "test_ordered", "referral")

# Verified entity types shown as visit/diagnosis mentions in the packet.
VISIT_MENTION_ENTITY_TYPES = ("diagnoses", "visit_type", "chief_complaint")


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
    """A discussion prompt for clinician visits.

    Categories: "trend", "abnormal", "clarification", "follow_up",
    "medication_change", "test_ordered", "referral" (HC-M17).
    """
    category: str
    question: str
    context: str  # Why this question is suggested
    related_analytes: list[str]
    # Provenance (HC-M17). Optional so existing consumers keep working.
    source_kind: Optional[str] = None  # observation | trend | care_task | entity
    source_id: Optional[str] = None
    source_quote: Optional[str] = None

    @classmethod
    def from_prompt(cls, q) -> "QuestionItem":
        return cls(
            category=q.category,
            question=q.question,
            context=q.context,
            related_analytes=q.related_analytes,
            source_kind=q.source_kind,
            source_id=q.source_id,
            source_quote=q.source_quote,
        )


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


async def _fetch_care_task_dicts(profile_db: AsyncSession) -> list[dict]:
    """Open and needs_review care-plan tasks as dicts for ExportModule.

    Tasks are user-accepted by construction (HC-M15), so no verification
    filter is needed. Profile isolation comes from the per-profile DB.
    """
    result = await profile_db.execute(
        select(CarePlanTask).where(CarePlanTask.status.in_(["open", "needs_review"]))
    )
    return [
        {
            "id": task.id,
            "title": task.title,
            "status": task.status,
            "due_date": task.due_date,
            "source_quote": task.source_quote,
            "source_entity_id": task.source_entity_id,
        }
        for task in result.scalars().all()
    ]


async def _fetch_question_entity_dicts(profile_db: AsyncSession) -> list[dict]:
    """Verified visit-note entities that can generate doctor questions."""
    result = await profile_db.execute(
        select(DocumentEntity).where(
            DocumentEntity.entity_type.in_(QUESTION_ENTITY_TYPES),
            DocumentEntity.verified_by_user.is_(True),
        )
    )
    return [
        {
            "id": ent.id,
            "entity_type": ent.entity_type,
            "entity_value": ent.entity_value,
            "quote": ent.quote,
            "verified_by_user": ent.verified_by_user,
        }
        for ent in result.scalars().all()
    ]


async def _fetch_active_medication_dicts(
    profile_db: AsyncSession, profile_id: str
) -> list[dict]:
    """Active medications from the tracker for the packet."""
    result = await profile_db.execute(
        select(Medication).where(
            Medication.profile_id == profile_id,
            Medication.is_active.is_(True),
        )
    )
    return [
        {
            "id": med.id,
            "name": med.name,
            "dosage_amount": med.dosage_amount,
            "dosage_unit": med.dosage_unit,
            "frequency": med.frequency,
            "instructions": med.instructions,
        }
        for med in result.scalars().all()
    ]


async def _fetch_visit_mention_dicts(
    profile_db: AsyncSession,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
) -> list[dict]:
    """Verified visit/diagnosis mention entities, with their document date."""
    query = (
        select(DocumentEntity, Document)
        .join(Document, Document.id == DocumentEntity.doc_id)
        .where(
            DocumentEntity.entity_type.in_(VISIT_MENTION_ENTITY_TYPES),
            DocumentEntity.verified_by_user.is_(True),
        )
    )
    if from_date:
        query = query.where(Document.collection_date >= from_date)
    if to_date:
        query = query.where(Document.collection_date <= to_date)

    result = await profile_db.execute(query)
    return [
        {
            "id": ent.id,
            "entity_type": ent.entity_type,
            "entity_value": ent.entity_value,
            "doc_date": (
                doc.collection_date.date().isoformat() if doc.collection_date else None
            ),
            "verified_by_user": ent.verified_by_user,
        }
        for ent, doc in result.all()
    ]


async def _fetch_selected_document_dicts(
    profile_db: AsyncSession, profile_id: str, doc_ids: list[str]
) -> list[dict]:
    """Filename/date metadata for the user-selected source documents."""
    if not doc_ids:
        return []
    result = await profile_db.execute(
        select(Document).where(
            Document.id.in_(doc_ids),
            Document.profile_id == profile_id,
        )
    )
    return [
        {
            "id": doc.id,
            "source": doc.source,
            "collection_date": doc.collection_date,
        }
        for doc in result.scalars().all()
    ]


def _compute_trends(observations: list[dict]) -> list[dict]:
    """
    Compute trend data from observations.

    Groups by analyte and calculates direction/change. Values are
    converted to a canonical unit (modules.normalize) before comparing
    across dates so cross-lab unit differences (e.g. mg/dL vs mmol/L)
    don't produce a spurious delta (NORM-UNIT-001). Observations whose
    unit can't be converted are excluded from the comparison; if the
    analyte isn't in the conversion table and its units are mixed, no
    trend is reported rather than comparing incompatible numbers.
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

        canonical_unit = canonical_unit_for(analyte)
        distinct_units = {
            normalize_unit(o["unit"]) for o in sorted_obs if o.get("unit")
        }

        if len(distinct_units) > 1:
            if canonical_unit is None:
                # Untabled analyte with mixed units: no safe basis for
                # comparison, don't report a trend.
                continue
            comparable_values = []
            for o in sorted_obs:
                conv = convert_to_canonical(analyte, o["value"], o.get("unit"))
                if conv is not None:
                    comparable_values.append(conv.canonical_value)
            if len(comparable_values) < 2:
                continue
        else:
            comparable_values = [o["value"] for o in sorted_obs]

        first_val = comparable_values[0]
        last_val = comparable_values[-1]

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

    questions: list[QuestionItem] = []
    if request.include_questions:
        export_module = ExportModule()
        generated_questions = export_module.generate_questions(
            observations=observations,
            trends=trends,
        )
        questions = [QuestionItem.from_prompt(q) for q in generated_questions]

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
        "questions": [q.model_dump() for q in questions],
    }
    _summary_store[summary.summary_id] = summary_data

    # Create audit log
    await audit_and_commit(
        master_db,
        log_export_event,
        profile_id=profile_id,
        export_type="doctor_summary",
        details={
            "summary_id": summary.summary_id,
            "format": request.format,
            "observation_count": summary.total_observations,
            "question_count": len(questions),
        },
    )

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
    format: str = Query("text", description="Download format: text, html, or pdf"),
    master_db: AsyncSession = Depends(get_db),
):
    """
    Download a previously generated summary.

    Supports formats: text (default), html, pdf.
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

    # Log download
    await audit_and_commit(
        master_db,
        log_export_event,
        profile_id=session.profile_id,
        export_type="summary_download",
        details={"summary_id": summary_id, "format": format},
    )

    export_module = ExportModule()
    short_id = summary_id[:8]

    if format == "html":
        html_content = export_module.render_html_summary(summary_data)
        return Response(
            content=html_content,
            media_type="text/html",
            headers={
                "Content-Disposition": f'attachment; filename="health_summary_{short_id}.html"'
            }
        )

    elif format == "pdf":
        try:
            pdf_bytes = export_module.render_pdf_summary(summary_data)
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="health_summary_{short_id}.pdf"'
                }
            )
        except ImportError as e:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=str(e),
            )

    else:
        # Default: text format
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

        if summary_data.get("questions"):
            lines.append("-" * 40)
            lines.append("QUESTIONS FOR YOUR PROVIDER")
            lines.append("-" * 40)
            for q in summary_data["questions"]:
                q_text = q.get("question", "") if isinstance(q, dict) else str(q)
                if q_text:
                    lines.append(f"  - {q_text}")
            lines.append("")

        lines.append("=" * 60)
        lines.append("This summary was generated by HealthCentral based on")
        lines.append("uploaded laboratory reports. This is not medical advice.")
        lines.append("Discuss all results with your healthcare provider.")
        lines.append("=" * 60)

        content = "\n".join(lines)

        return Response(
            content=content,
            media_type="text/plain",
            headers={
                "Content-Disposition": f'attachment; filename="health_summary_{short_id}.txt"'
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

    HC-M17: besides abnormal values and trends, questions are derived from
    open/needs_review care-plan tasks and verified visit-note entities
    (medication changes, ordered tests, referrals), each tied to its source.
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

    # HC-M17 sources: accepted care tasks + verified visit-note entities.
    care_tasks = await _fetch_care_task_dicts(profile_db)
    entities = await _fetch_question_entity_dicts(profile_db)

    # Generate questions using ExportModule
    export_module = ExportModule()
    questions = export_module.generate_questions(
        observations=observations,
        trends=trends,
        care_tasks=care_tasks,
        entities=entities,
    )

    # Log generation
    await audit_and_commit(
        master_db,
        log_export_event,
        profile_id=profile_id,
        export_type="questions",
        details={"question_count": len(questions)},
    )

    return [QuestionItem.from_prompt(q) for q in questions]


class VisitPrepRequest(BaseModel):
    """Request model for the visit-prep packet (HC-M18).

    confirm MUST be true — packet generation assembles personal health data
    into an exportable artifact, so it requires the same explicit user
    confirmation as the RL dataset export.
    """

    reason_for_visit: Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None

    # Section include flags
    include_medications: bool = True
    include_labs: bool = True
    include_visits: bool = True
    include_tasks: bool = True
    include_questions: bool = True

    selected_doc_ids: Optional[list[str]] = None
    confirm: bool = False


class VisitPrepResponse(BaseModel):
    """Response model for visit-prep packet generation."""

    packet_id: str
    profile_id: str
    generated_at: str
    section_titles: list[str]
    markdown: str
    redaction_count: int


@router.post("/visit-prep", response_model=VisitPrepResponse)
async def generate_visit_prep(
    request: VisitPrepRequest,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Generate a visit-prep packet (HC-M18).

    One exportable packet before an appointment: reason for visit, current
    medications, recent abnormal verified labs, verified visit/diagnosis
    mentions, open follow-up tasks, generated questions (HC-M17), and the
    selected source documents. Unverified data is excluded everywhere.

    Requires confirm=true. All content is redacted (strict policy) by the
    ExportModule before it is stored or downloadable. Creates an audit entry.
    """
    if request.confirm is not True:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Visit-prep export requires confirm=true in the request body.",
        )

    profile_id = session.profile_id
    for doc_id in request.selected_doc_ids or []:
        validate_uuid(doc_id, "selected_doc_ids entry")

    observations = None
    questions = None
    if request.include_labs or request.include_questions:
        fetched_observations = await _fetch_observations(
            profile_db,
            profile_id,
            from_date=request.from_date,
            to_date=request.to_date,
        )
        observations = fetched_observations if request.include_labs else None

    medications = (
        await _fetch_active_medication_dicts(profile_db, profile_id)
        if request.include_medications
        else None
    )
    visit_mentions = (
        await _fetch_visit_mention_dicts(
            profile_db, from_date=request.from_date, to_date=request.to_date
        )
        if request.include_visits
        else None
    )
    care_tasks = (
        await _fetch_care_task_dicts(profile_db)
        if request.include_tasks or request.include_questions
        else None
    )

    export_module = ExportModule()
    if request.include_questions:
        # Packet policy: unverified data is excluded — questions inside the
        # packet only draw on verified observations (and verified entities,
        # which generate_questions enforces itself). Content the user has
        # excluded from the packet (include_labs=False / include_tasks=False)
        # must not resurface as question inputs either.
        verified_observations = (
            [o for o in fetched_observations if o.get("user_verified")]
            if request.include_labs
            else []
        )
        questions_care_tasks = care_tasks if request.include_tasks else []
        questions = export_module.generate_questions(
            observations=verified_observations,
            trends=_compute_trends(verified_observations),
            care_tasks=questions_care_tasks,
            entities=await _fetch_question_entity_dicts(profile_db),
        )

    selected_documents = (
        await _fetch_selected_document_dicts(
            profile_db, profile_id, request.selected_doc_ids
        )
        if request.selected_doc_ids
        else None
    )

    packet = export_module.compose_visit_prep_packet(
        profile_id=profile_id,
        reason_for_visit=request.reason_for_visit,
        medications=medications,
        observations=observations,
        visit_mentions=visit_mentions,
        care_tasks=care_tasks if request.include_tasks else None,
        questions=questions,
        selected_documents=selected_documents,
    )
    _packet_store[packet["packet_id"]] = packet

    await audit_and_commit(
        master_db,
        log_export_event,
        profile_id=profile_id,
        export_type="visit_prep",
        details={
            "packet_id": packet["packet_id"],
            "section_titles": [s["title"] for s in packet["sections"]],
            "redaction_count": packet["redaction_count"],
        },
    )

    return VisitPrepResponse(
        packet_id=packet["packet_id"],
        profile_id=profile_id,
        generated_at=packet["generated_at"],
        section_titles=[s["title"] for s in packet["sections"]],
        markdown=packet["markdown"],
        redaction_count=packet["redaction_count"],
    )


@router.get("/visit-prep/{packet_id}/download")
async def download_visit_prep(
    packet_id: str,
    session: RequireAuth,
    format: str = Query("markdown", description="Download format: markdown, html, or pdf"),
    master_db: AsyncSession = Depends(get_db),
):
    """
    Download a previously generated visit-prep packet.

    markdown is always available; html/pdf reuse the doctor-summary
    renderer (pdf requires WeasyPrint, 501 if not installed). Content was
    redacted at composition time, so every format is redacted.
    """
    validate_uuid(packet_id, "packet_id")

    packet = _packet_store.get(packet_id)
    if not packet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visit-prep packet not found",
        )

    if packet["profile_id"] != session.profile_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this packet",
        )

    await audit_and_commit(
        master_db,
        log_export_event,
        profile_id=session.profile_id,
        export_type="visit_prep_download",
        details={"packet_id": packet_id, "format": format},
    )

    short_id = packet_id[:8]
    if format in ("html", "pdf"):
        export_module = ExportModule()
        # Reuse the existing doctor-summary renderer (no new dependency).
        summary_data = {
            "date_range": f"Visit Prep Packet — {packet['generated_at'][:10]}",
            "key_findings": [],
            "sections": packet["sections"],
            "questions": [],  # already rendered as a packet section
        }
        if format == "html":
            return Response(
                content=export_module.render_html_summary(summary_data),
                media_type="text/html",
                headers={
                    "Content-Disposition": f'attachment; filename="visit_prep_{short_id}.html"'
                },
            )
        try:
            pdf_bytes = export_module.render_pdf_summary(summary_data)
        except ImportError as e:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=str(e),
            )
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="visit_prep_{short_id}.pdf"'
            },
        )

    # Default: markdown (always available)
    return Response(
        content=packet["markdown"],
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="visit_prep_{short_id}.md"'
        },
    )


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
    await audit_and_commit(
        master_db,
        log_export_event,
        profile_id=profile_id,
        export_type="csv",
        details={"observation_count": len(observations)},
    )

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
    await audit_and_commit(
        master_db,
        log_export_event,
        profile_id=profile_id,
        export_type="json",
        details={"observation_count": len(observations)},
    )

    # Generate filename with date
    filename = f"health_data_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"

    return Response(
        content=json_content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
