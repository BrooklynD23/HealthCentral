"""
Export API endpoints.

Generates clinician-ready summaries and data exports.
All endpoints require authentication.

Sprint 4: Wired to ExportModule for CSV/JSON/summary/questions generation.
"""

import logging
import re
from copy import deepcopy
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth import RequireAuth, ProfileDbSession
from core.audit import log_export_event
from models import Observation, Medication
from modules.export import ExportModule

logger = logging.getLogger(__name__)

router = APIRouter()

# UUID validation pattern
UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
    re.IGNORECASE
)
HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

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


def _build_template_options(
    brand_name: Optional[str],
    brand_tagline: Optional[str],
    accent_color: Optional[str],
    include_overview: bool,
    include_abnormal: bool,
    include_trends: bool,
    include_questions: bool,
    include_key_findings: bool,
) -> dict:
    """Assemble a normalized summary template configuration."""
    resolved_color = (accent_color or "").strip()
    if not HEX_COLOR_RE.fullmatch(resolved_color):
        resolved_color = "#2D7D6F"

    return {
        "brand_name": (brand_name or "HealthCentral").strip() or "HealthCentral",
        "brand_tagline": (brand_tagline or "Lab Results Summary").strip() or "Lab Results Summary",
        "accent_color": resolved_color,
        "include_overview": include_overview,
        "include_abnormal": include_abnormal,
        "include_trends": include_trends,
        "include_questions": include_questions,
        "include_key_findings": include_key_findings,
        "include_disclaimer": True,
    }


def _apply_section_toggles(summary_data: dict, template_options: dict) -> dict:
    """Filter summary sections/questions for non-HTML exports."""
    rendered = deepcopy(summary_data)
    filtered_sections = []
    for section in rendered.get("sections", []):
        title = str(section.get("title", "")).lower()
        if "overview" in title and not template_options["include_overview"]:
            continue
        if "outside reference range" in title and not template_options["include_abnormal"]:
            continue
        if "trend" in title and not template_options["include_trends"]:
            continue
        filtered_sections.append(section)
    rendered["sections"] = filtered_sections

    if not template_options["include_key_findings"]:
        rendered["key_findings"] = []
    if not template_options["include_questions"]:
        rendered["questions"] = []

    return rendered


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
        "observations": observations,  # Needed for chart generation
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
    format: str = Query("text", description="Download format: text, html, or pdf"),
    include_charts: bool = Query(False, description="Embed trend charts in PDF/HTML"),
    brand_name: Optional[str] = Query(None, description="Template brand name override"),
    brand_tagline: Optional[str] = Query(None, description="Template subtitle override"),
    accent_color: Optional[str] = Query(
        None,
        description="Hex color for HTML/PDF header (e.g. #2D7D6F)",
    ),
    include_overview: bool = Query(True, description="Include overview section"),
    include_abnormal: bool = Query(True, description="Include abnormal-values section"),
    include_trends: bool = Query(True, description="Include trends section"),
    include_questions: bool = Query(True, description="Include questions section"),
    include_key_findings: bool = Query(True, description="Include key findings section"),
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

    template_options = _build_template_options(
        brand_name=brand_name,
        brand_tagline=brand_tagline,
        accent_color=accent_color,
        include_overview=include_overview,
        include_abnormal=include_abnormal,
        include_trends=include_trends,
        include_questions=include_questions,
        include_key_findings=include_key_findings,
    )
    rendered_summary = _apply_section_toggles(summary_data, template_options)

    # Log download
    try:
        await log_export_event(
            db=master_db,
            profile_id=session.profile_id,
            export_type="summary_download",
            details={
                "summary_id": summary_id,
                "format": format,
                "include_charts": include_charts,
                "template": {
                    "brand_name": template_options["brand_name"],
                    "accent_color": template_options["accent_color"],
                    "include_overview": template_options["include_overview"],
                    "include_abnormal": template_options["include_abnormal"],
                    "include_trends": template_options["include_trends"],
                    "include_questions": template_options["include_questions"],
                    "include_key_findings": template_options["include_key_findings"],
                },
            },
        )
        await master_db.commit()
    except Exception as e:
        logger.warning(f"Failed to log export event: {e}")

    export_module = ExportModule()
    short_id = summary_id[:8]

    # Generate chart images if requested
    chart_images = {}
    if include_charts and format in ("pdf", "html"):
        observations = summary_data.get("observations", [])
        # Group by analyte for charting
        from collections import defaultdict
        analyte_data = defaultdict(list)
        for obs in observations:
            if obs.get("value") is not None and obs.get("collected_at"):
                analyte_data[obs["analyte_canonical"]].append(obs)

        for analyte, points in analyte_data.items():
            if len(points) >= 2:
                sorted_points = sorted(points, key=lambda x: x["collected_at"])
                chart_images[analyte] = export_module.generate_chart_image(
                    analyte=analyte,
                    data_points=sorted_points,
                    unit=sorted_points[0].get("unit", ""),
                    ref_low=sorted_points[0].get("ref_low"),
                    ref_high=sorted_points[0].get("ref_high"),
                )

    if format == "html":
        html_content = export_module.render_html_summary(
            rendered_summary,
            chart_images=chart_images,
            template_options=template_options,
        )
        return Response(
            content=html_content,
            media_type="text/html",
            headers={
                "Content-Disposition": f'attachment; filename="health_summary_{short_id}.html"'
            }
        )

    elif format == "pdf":
        try:
            pdf_bytes = export_module.render_pdf_summary(
                rendered_summary,
                chart_images=chart_images,
                template_options=template_options,
            )
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
            f"{template_options['brand_name'].upper()} SUMMARY REPORT",
            "=" * 60,
            "",
            f"Generated: {rendered_summary['generated_at']}",
            f"Total Observations: {rendered_summary['total_observations']}",
            f"Abnormal Values: {rendered_summary['abnormal_count']}",
            f"Critical Values: {rendered_summary['critical_count']}",
            "",
        ]

        if rendered_summary["key_findings"]:
            lines.append("-" * 40)
            lines.append("KEY FINDINGS")
            lines.append("-" * 40)
            for finding in rendered_summary["key_findings"]:
                lines.append(f"  - {finding}")
            lines.append("")

        for section in rendered_summary["sections"]:
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


@router.get("/excel")
async def export_excel(
    session: RequireAuth,
    analytes: Optional[str] = Query(None, description="Comma-separated analyte filter"),
    from_date: Optional[datetime] = Query(None, description="Start date"),
    to_date: Optional[datetime] = Query(None, description="End date"),
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Export observations as formatted Excel workbook.

    Multi-sheet with conditional formatting for abnormal values.
    Only includes data from the authenticated profile.
    """
    profile_id = session.profile_id

    analyte_filter = None
    if analytes:
        analyte_filter = [a.strip().lower() for a in analytes.split(",")]

    observations = await _fetch_observations(
        profile_db, profile_id,
        from_date=from_date, to_date=to_date, analyte_filter=analyte_filter,
    )

    trends = _compute_trends(observations)
    meds_result = await profile_db.execute(
        select(Medication)
        .where(Medication.profile_id == profile_id)
        .order_by(Medication.name.asc())
    )
    medications = meds_result.scalars().all()
    medication_rows = [
        {
            "name": med.name,
            "generic_name": med.generic_name,
            "dosage_amount": med.dosage_amount,
            "dosage_unit": med.dosage_unit,
            "frequency": med.frequency,
            "is_active": med.is_active,
            "reminder_enabled": med.reminder_enabled,
            "started_at": med.started_at,
            "ended_at": med.ended_at,
            "instructions": med.instructions,
        }
        for med in medications
    ]

    export_module = ExportModule()
    xlsx_bytes = export_module.export_excel(
        observations,
        trends,
        medications=medication_rows,
    )

    try:
        await log_export_event(
            db=master_db, profile_id=profile_id, export_type="excel",
            details={
                "observation_count": len(observations),
                "medication_count": len(medication_rows),
            },
        )
        await master_db.commit()
    except Exception as e:
        logger.warning(f"Failed to log export event: {e}")

    filename = f"health_data_{datetime.now(timezone.utc).strftime('%Y%m%d')}.xlsx"

    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/fhir")
async def export_fhir(
    session: RequireAuth,
    analytes: Optional[str] = Query(None, description="Comma-separated analyte filter"),
    from_date: Optional[datetime] = Query(None, description="Start date"),
    to_date: Optional[datetime] = Query(None, description="End date"),
    validate: bool = Query(
        False,
        description="Run lightweight FHIR conformance checks (non-strict by default)",
    ),
    validation_strict: bool = Query(
        False,
        description="When validate=true, return 422 if any conformance issues are found",
    ),
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Export observations as FHIR R4 JSON Bundle.

    Maps observations to FHIR Observation resources with LOINC codes
    (when available via BiomarkerKnowledge lookup).
    """
    import json as json_lib
    from models import BiomarkerKnowledge
    from models.fhir_resources import (
        FHIRPatient,
        map_observation_to_fhir,
        create_fhir_bundle,
        validate_fhir_bundle,
    )

    profile_id = session.profile_id

    analyte_filter = None
    if analytes:
        analyte_filter = [a.strip().lower() for a in analytes.split(",")]

    observations = await _fetch_observations(
        profile_db, profile_id,
        from_date=from_date, to_date=to_date, analyte_filter=analyte_filter,
    )

    # LOINC lookup from BiomarkerKnowledge (master DB)
    loinc_map: dict[str, list[str]] = {}
    try:
        from sqlalchemy import select as sa_select
        result = await master_db.execute(
            sa_select(
                BiomarkerKnowledge.analyte_canonical,
                BiomarkerKnowledge.loinc_codes_json,
            )
        )
        for row in result.all():
            if row.loinc_codes_json:
                codes = json_lib.loads(row.loinc_codes_json)
                if isinstance(codes, list) and codes:
                    loinc_map[row.analyte_canonical] = codes
    except Exception as e:
        logger.warning(f"LOINC lookup failed, proceeding without: {e}")

    # Build FHIR resources
    patient = FHIRPatient(id=profile_id, display_name=session.profile_name or "Unknown")
    patient_ref = f"Patient/{profile_id}"

    fhir_observations = [
        map_observation_to_fhir(obs, patient_ref=patient_ref, loinc_map=loinc_map)
        for obs in observations
    ]

    bundle = create_fhir_bundle(patient, fhir_observations)
    bundle_payload = bundle.model_dump(by_alias=True, exclude_none=True)
    validation_issues = validate_fhir_bundle(bundle_payload) if validate else []
    if validate and validation_strict and validation_issues:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "FHIR conformance validation failed",
                "issues": validation_issues,
            },
        )

    bundle_json = json_lib.dumps(bundle_payload, indent=2)

    try:
        await log_export_event(
            db=master_db, profile_id=profile_id, export_type="fhir_r4",
            details={
                "observation_count": len(observations),
                "loinc_mapped": len(loinc_map),
                "validated": validate,
                "validation_issue_count": len(validation_issues),
                "validation_strict": validation_strict,
            },
        )
        await master_db.commit()
    except Exception as e:
        logger.warning(f"Failed to log export event: {e}")

    filename = f"health_data_{datetime.now(timezone.utc).strftime('%Y%m%d')}_fhir.json"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    if validate:
        headers["X-FHIR-Validation-Issues"] = str(len(validation_issues))

    return Response(
        content=bundle_json,
        media_type="application/fhir+json",
        headers=headers,
    )
