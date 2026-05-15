"""
Lab interpretation API endpoints.

Handles generation, retrieval, and management of AI-powered
lab result interpretations.

Phase 1: Core Lab Interpretation Engine - API Layer
"""

import json
import logging
import re
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth import RequireAuth, Session, ProfileDbSession
from models import (
    Observation,
    LabInterpretation,
    PanelInterpretation,
    BiomarkerKnowledge,
)
from modules import get_interpret_module
from modules.rag import ModelUnavailableError
from api.assistant import get_rag_module

logger = logging.getLogger(__name__)

router = APIRouter()

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


# Response Models


class CitationResponse(BaseModel):
    """Citation reference in an interpretation."""
    type: str  # knowledge_base, intervention, source
    id: str
    text: str


class InterpretationResponse(BaseModel):
    """Response model for lab interpretation."""
    id: str
    observation_id: str
    interpretation_text: str
    severity_level: str
    advice_text: Optional[str] = None
    citations: list[CitationResponse]
    context: Optional[dict] = None
    model_id: str
    model_tier: str
    confidence_score: float
    requires_physician_review: bool
    physician_review_reason: Optional[str] = None
    viewed_at: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, interp: LabInterpretation) -> "InterpretationResponse":
        """Convert from ORM model."""
        citations = []
        if interp.citations_json:
            try:
                citations_data = json.loads(interp.citations_json)
                citations = [CitationResponse(**c) for c in citations_data]
            except (json.JSONDecodeError, TypeError):
                pass

        context = None
        if interp.context_json:
            try:
                context = json.loads(interp.context_json)
            except json.JSONDecodeError:
                pass

        return cls(
            id=interp.id,
            observation_id=interp.observation_id,
            interpretation_text=interp.interpretation_text,
            severity_level=interp.severity_level,
            advice_text=interp.advice_text,
            citations=citations,
            context=context,
            model_id=interp.model_id,
            model_tier=interp.model_tier,
            confidence_score=interp.confidence_score,
            requires_physician_review=interp.requires_physician_review,
            physician_review_reason=interp.physician_review_reason,
            viewed_at=interp.viewed_at.isoformat() if interp.viewed_at else None,
            created_at=interp.created_at.isoformat(),
        )


class GroundedCitationResponse(BaseModel):
    """Citation from grounded interpretation retrieval."""
    source_type: str
    doc_id: Optional[str] = None
    doc_title: Optional[str] = None
    page: Optional[int] = None
    text_snippet: str
    authority_tier: Optional[int] = None
    authority_score: Optional[float] = None


class GroundedSegmentResponse(BaseModel):
    """Grounded segment response."""
    segment_type: str
    content: str
    citations: list[GroundedCitationResponse] = []


class GroundedVerificationResponse(BaseModel):
    """Verification details for grounded interpretation."""
    enabled: bool = False
    total_claims: int = 0
    verified_claims: int = 0
    failed_claims: int = 0
    faithfulness_score: float = 0.0
    authority_score: float = 0.0
    summary: str = ""
    issues: list[str] = []


class GroundedInterpretationResponse(BaseModel):
    """Combined template interpretation + grounded RAG explanation."""
    interpretation: InterpretationResponse
    grounded_segments: list[GroundedSegmentResponse]
    full_response: str
    insufficient_context: bool = False
    insufficient_reasons: list[str] = []
    verification: GroundedVerificationResponse = GroundedVerificationResponse()
    is_valid: bool = True
    validation_errors: list[str] = []


class RelationshipInsight(BaseModel):
    """Insight from biomarker relationship analysis."""
    relationship: str
    value: float
    status: str
    interpretation: str
    source_id: Optional[str] = None


class PanelInterpretationResponse(BaseModel):
    """Response model for panel interpretation."""
    id: str
    panel_name: str
    collected_at: str
    observation_ids: list[str]
    summary_text: str
    overall_status: str
    relationship_insights: Optional[list[RelationshipInsight]] = None
    advice_text: Optional[str] = None
    citations: list[CitationResponse]
    confidence_score: float
    requires_physician_review: bool
    created_at: str

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, interp: PanelInterpretation) -> "PanelInterpretationResponse":
        """Convert from ORM model."""
        observation_ids = []
        if interp.observation_ids_json:
            try:
                observation_ids = json.loads(interp.observation_ids_json)
            except json.JSONDecodeError:
                pass

        citations = []
        if interp.citations_json:
            try:
                citations_data = json.loads(interp.citations_json)
                citations = [CitationResponse(**c) for c in citations_data]
            except (json.JSONDecodeError, TypeError):
                pass

        relationship_insights = None
        if interp.relationship_insights_json:
            try:
                insights_data = json.loads(interp.relationship_insights_json)
                relationship_insights = [RelationshipInsight(**i) for i in insights_data]
            except (json.JSONDecodeError, TypeError):
                pass

        return cls(
            id=interp.id,
            panel_name=interp.panel_name,
            collected_at=interp.collected_at.isoformat(),
            observation_ids=observation_ids,
            summary_text=interp.summary_text,
            overall_status=interp.overall_status,
            relationship_insights=relationship_insights,
            advice_text=interp.advice_text,
            citations=citations,
            confidence_score=interp.confidence_score,
            requires_physician_review=interp.requires_physician_review,
            created_at=interp.created_at.isoformat(),
        )


class BiomarkerKnowledgeResponse(BaseModel):
    """Response model for biomarker knowledge lookup."""
    id: str
    analyte_canonical: str
    display_name: str
    description: str
    clinical_significance: str
    normal_interpretation: str
    high_interpretation: str
    low_interpretation: str
    reference_ranges: dict
    common_causes_high: Optional[list[str]] = None
    common_causes_low: Optional[list[str]] = None
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None
    standard_unit: str
    category: str
    panels: Optional[list[str]] = None
    sources: list[dict]

    @classmethod
    def from_model(cls, kb: BiomarkerKnowledge) -> "BiomarkerKnowledgeResponse":
        """Convert from ORM model."""
        ref_ranges = {}
        if kb.ref_range_adult_json:
            try:
                ref_ranges = json.loads(kb.ref_range_adult_json)
            except json.JSONDecodeError:
                pass

        causes_high = None
        if kb.common_causes_high_json:
            try:
                causes_high = json.loads(kb.common_causes_high_json)
            except json.JSONDecodeError:
                pass

        causes_low = None
        if kb.common_causes_low_json:
            try:
                causes_low = json.loads(kb.common_causes_low_json)
            except json.JSONDecodeError:
                pass

        panels = None
        if kb.panels_json:
            try:
                panels = json.loads(kb.panels_json)
            except json.JSONDecodeError:
                pass

        sources = []
        if kb.sources_json:
            try:
                sources = json.loads(kb.sources_json)
            except json.JSONDecodeError:
                pass

        return cls(
            id=kb.id,
            analyte_canonical=kb.analyte_canonical,
            display_name=kb.display_name,
            description=kb.description,
            clinical_significance=kb.clinical_significance,
            normal_interpretation=kb.normal_interpretation,
            high_interpretation=kb.high_interpretation,
            low_interpretation=kb.low_interpretation,
            reference_ranges=ref_ranges,
            common_causes_high=causes_high,
            common_causes_low=causes_low,
            critical_low=kb.critical_low,
            critical_high=kb.critical_high,
            standard_unit=kb.standard_unit,
            category=kb.category,
            panels=panels,
            sources=sources,
        )


class BatchInterpretRequest(BaseModel):
    """Request for batch interpretation generation."""
    observation_ids: list[str] = Field(..., min_length=1, max_length=50)
    force_regenerate: bool = False


class BatchInterpretResponse(BaseModel):
    """Response for batch interpretation."""
    successful: list[str]
    failed: list[dict]  # {"observation_id": str, "error": str}


# Endpoints


@router.post(
    "/observations/{observation_id}/interpret",
    response_model=InterpretationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_interpretation(
    observation_id: str,
    session: RequireAuth,
    force_regenerate: bool = Query(False, description="Force regeneration even if exists"),
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Generate interpretation for a lab observation.

    Generates an AI-powered interpretation of a lab result using the
    knowledge base and safety guardrails. If an interpretation already
    exists, returns it unless force_regenerate is True.

    Requires authentication and access to the observation's profile.
    """
    validate_uuid(observation_id, "observation_id")

    # Verify observation exists and belongs to this profile
    result = await profile_db.execute(
        select(Observation).where(Observation.id == observation_id)
    )
    observation = result.scalar_one_or_none()

    if not observation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Observation not found"
        )

    if observation.profile_id != session.profile_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this observation"
        )

    # Generate interpretation
    interpret_module = get_interpret_module()
    interp_result = await interpret_module.interpret_observation(
        observation_id=observation_id,
        profile_db=profile_db,
        master_db=master_db,
        force_regenerate=force_regenerate,
    )

    if not interp_result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=interp_result.error_message or "Failed to generate interpretation"
        )

    logger.info(f"Generated interpretation for observation {observation_id}")
    return InterpretationResponse.from_model(interp_result.interpretation)


@router.post(
    "/observations/{observation_id}/interpret-grounded",
    response_model=GroundedInterpretationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_grounded_interpretation(
    observation_id: str,
    session: RequireAuth,
    force_regenerate: bool = Query(False, description="Force regeneration even if exists"),
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """Generate interpretation plus grounded RAG explanation with citations."""
    validate_uuid(observation_id, "observation_id")

    result = await profile_db.execute(
        select(Observation).where(Observation.id == observation_id)
    )
    observation = result.scalar_one_or_none()
    if not observation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Observation not found",
        )
    if observation.profile_id != session.profile_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this observation",
        )

    interpret_module = get_interpret_module()
    interp_result = await interpret_module.interpret_observation(
        observation_id=observation_id,
        profile_db=profile_db,
        master_db=master_db,
        force_regenerate=force_regenerate,
    )
    if not interp_result.success or not interp_result.interpretation:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=interp_result.error_message or "Failed to generate interpretation",
        )

    rag = get_rag_module()
    question = (
        f"Explain my lab result for {observation.analyte_raw} "
        f"({observation.value if observation.value is not None else observation.value_text} "
        f"{observation.unit or ''}) and what it may indicate. "
        "Use my report details first, then general context."
    )

    runner = None
    try:
        from core.external_runner import get_runner_for_request

        runner = await get_runner_for_request(session.profile_id, profile_db)
    except Exception:
        runner = None

    try:
        rag_result = await rag.query(
            question=question,
            profile_id=session.profile_id,
            selected_analytes=[observation.analyte_canonical],
            include_references=True,
            model_runner=runner,
            master_db=master_db,
            profile_db=profile_db,
            use_memory=False,
        )
    except ModelUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(exc),
        )

    grounded_segments: list[GroundedSegmentResponse] = []
    for seg in rag_result.segments:
        grounded_segments.append(
            GroundedSegmentResponse(
                segment_type=seg.segment_type,
                content=seg.content,
                citations=[
                    GroundedCitationResponse(
                        source_type=c.source_type,
                        doc_id=c.doc_id,
                        doc_title=c.doc_title,
                        page=c.page,
                        text_snippet=c.text_snippet,
                        authority_tier=c.authority_tier,
                        authority_score=c.authority_score,
                    )
                    for c in seg.citations
                ],
            )
        )

    full_response = "\n\n".join(
        f"**{seg.segment_type.upper().replace('_', ' ')}**\n{seg.content}"
        for seg in rag_result.segments
    )

    verification = GroundedVerificationResponse(
        enabled=rag_result.verification.verification_enabled,
        total_claims=rag_result.verification.total_claims,
        verified_claims=rag_result.verification.verified_claims,
        failed_claims=rag_result.verification.failed_claims,
        faithfulness_score=rag_result.verification.faithfulness_score,
        authority_score=rag_result.verification.authority_score,
        summary=rag_result.verification.verification_summary,
        issues=rag_result.verification.claims_with_issues,
    )

    return GroundedInterpretationResponse(
        interpretation=InterpretationResponse.from_model(interp_result.interpretation),
        grounded_segments=grounded_segments,
        full_response=full_response,
        insufficient_context=rag_result.insufficient_context,
        insufficient_reasons=rag_result.insufficient_reasons,
        verification=verification,
        is_valid=rag_result.is_valid,
        validation_errors=rag_result.validation_errors,
    )


@router.get(
    "/observations/{observation_id}/interpretation",
    response_model=InterpretationResponse,
)
async def get_interpretation(
    observation_id: str,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
):
    """
    Get existing interpretation for an observation.

    Returns the stored interpretation if one exists.
    Does not generate a new interpretation.
    """
    validate_uuid(observation_id, "observation_id")

    # Verify observation belongs to this profile
    obs_result = await profile_db.execute(
        select(Observation).where(Observation.id == observation_id)
    )
    observation = obs_result.scalar_one_or_none()

    if not observation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Observation not found"
        )

    if observation.profile_id != session.profile_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this observation"
        )

    # Get interpretation
    result = await profile_db.execute(
        select(LabInterpretation).where(
            LabInterpretation.observation_id == observation_id
        )
    )
    interpretation = result.scalar_one_or_none()

    if not interpretation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No interpretation found for this observation"
        )

    # Mark as viewed
    if not interpretation.viewed_at:
        interpretation.viewed_at = datetime.utcnow()
        await profile_db.commit()

    return InterpretationResponse.from_model(interpretation)


@router.post(
    "/panels/{panel_name}/interpret",
    response_model=PanelInterpretationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_panel_interpretation(
    panel_name: str,
    collected_at: datetime,
    session: RequireAuth,
    force_regenerate: bool = Query(False, description="Force regeneration"),
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Generate holistic interpretation for a lab panel.

    Generates a comprehensive interpretation of a panel (CBC, CMP, lipid, thyroid)
    including relationship analysis between related biomarkers.

    Requires a collection date to identify which observations to include.
    """
    from api.observations import PANEL_DEFINITIONS

    panel_name_lower = panel_name.lower()
    if panel_name_lower not in PANEL_DEFINITIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown panel: {panel_name}. Valid panels: {', '.join(PANEL_DEFINITIONS.keys())}"
        )

    interpret_module = get_interpret_module()
    result = await interpret_module.interpret_panel(
        panel_name=panel_name_lower,
        collected_at=collected_at,
        profile_id=session.profile_id,
        profile_db=profile_db,
        master_db=master_db,
        force_regenerate=force_regenerate,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND if "No observations found" in (result.error_message or "") else status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.error_message or "Failed to generate panel interpretation"
        )

    logger.info(f"Generated panel interpretation for {panel_name}")
    return PanelInterpretationResponse.from_model(result.interpretation)


@router.get(
    "/recent",
    response_model=list[InterpretationResponse],
)
async def get_recent_interpretations(
    session: RequireAuth,
    limit: int = Query(10, ge=1, le=50, description="Max results"),
    include_panels: bool = Query(False, description="Include panel interpretations"),
    profile_db: ProfileDbSession = None,
):
    """
    Get recent interpretations for the authenticated profile.

    Returns the most recently created interpretations, ordered by date.
    """
    result = await profile_db.execute(
        select(LabInterpretation).where(
            LabInterpretation.profile_id == session.profile_id
        ).order_by(LabInterpretation.created_at.desc()).limit(limit)
    )
    interpretations = result.scalars().all()

    return [InterpretationResponse.from_model(i) for i in interpretations]


@router.get(
    "/knowledge/biomarker/{analyte_canonical}",
    response_model=BiomarkerKnowledgeResponse,
)
async def get_biomarker_knowledge(
    analyte_canonical: str,
    session: RequireAuth,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Get knowledge base information for a biomarker.

    Returns reference information about what the biomarker measures,
    its clinical significance, and interpretation guidance.

    Public knowledge - not patient-specific data.
    """
    result = await master_db.execute(
        select(BiomarkerKnowledge).where(
            BiomarkerKnowledge.analyte_canonical == analyte_canonical.lower()
        )
    )
    kb = result.scalar_one_or_none()

    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No knowledge found for biomarker: {analyte_canonical}"
        )

    return BiomarkerKnowledgeResponse.from_model(kb)


@router.post(
    "/batch",
    response_model=BatchInterpretResponse,
)
async def batch_generate_interpretations(
    request: BatchInterpretRequest,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Generate interpretations for multiple observations.

    Processes a batch of observation IDs and generates interpretations
    for each. Returns lists of successful and failed IDs.

    Limited to 50 observations per request.
    """
    successful = []
    failed = []

    interpret_module = get_interpret_module()

    for obs_id in request.observation_ids:
        try:
            validate_uuid(obs_id, "observation_id")

            # Verify access
            obs_result = await profile_db.execute(
                select(Observation).where(Observation.id == obs_id)
            )
            observation = obs_result.scalar_one_or_none()

            if not observation:
                failed.append({"observation_id": obs_id, "error": "Not found"})
                continue

            if observation.profile_id != session.profile_id:
                failed.append({"observation_id": obs_id, "error": "Access denied"})
                continue

            # Generate interpretation
            result = await interpret_module.interpret_observation(
                observation_id=obs_id,
                profile_db=profile_db,
                master_db=master_db,
                force_regenerate=request.force_regenerate,
            )

            if result.success:
                successful.append(obs_id)
            else:
                failed.append({
                    "observation_id": obs_id,
                    "error": result.error_message or "Generation failed"
                })

        except HTTPException as e:
            failed.append({"observation_id": obs_id, "error": e.detail})
        except Exception as e:
            logger.error(f"Batch interpretation error for {obs_id}: {e}")
            failed.append({"observation_id": obs_id, "error": "Internal error"})

    logger.info(
        f"Batch interpretation: {len(successful)} successful, {len(failed)} failed"
    )

    return BatchInterpretResponse(successful=successful, failed=failed)
