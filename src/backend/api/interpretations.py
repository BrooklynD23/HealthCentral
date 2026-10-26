"""
Lab interpretation API endpoints.

Handles generation, retrieval, and management of AI-powered
lab result interpretations.

Phase 1: Core Lab Interpretation Engine - API Layer
"""

import json
import logging
import re
from typing import NoReturn, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.assistant import get_rag_module, get_strict_rag_module, is_strict_safety_mode
from core.audit import audit_and_commit, audit_intent, create_audit_log
from core.auth import ProfileDbSession, RequireAuth
from core.database import get_db
from core.time import NaiveUtcDatetime, utcnow
from models import (
    BiomarkerKnowledge,
    LabInterpretation,
    Observation,
    PanelInterpretation,
)
from modules import get_interpret_module
from modules.agent.guardrails.templates import ABSTAIN_TEMPLATE, ESCALATE_TEMPLATE
from modules.rag import ModelUnavailableError

logger = logging.getLogger(__name__)


async def _audit_interpretation(
    master_db: AsyncSession,
    event: str,
    profile_id: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    details: Optional[dict] = None,
    intent: Optional[str] = None,
) -> None:
    """Fail-closed audit row for an interpretation route (CLAUDE.md: audit
    logging on every route that touches observations or profile data).

    Ids, counts and enums only: never the analyte, panel name, question or
    any interpretation text (AUDIT-PHI-001; core.audit scrubs details too).
    """
    event_type = f"interpretation.{event}"
    kwargs = dict(
        event_type=event_type,
        action=event_type,
        profile_id=profile_id,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
    )
    try:
        if intent:
            await audit_intent(master_db, intent, create_audit_log, **kwargs)
        else:
            await audit_and_commit(master_db, create_audit_log, **kwargs)
    except Exception:
        # AUDIT-ORDER C: ids only, never PHI.
        logger.error(
            "AUDIT-ORDER: audit commit failed (event=%s, entity=%s)",
            event_type, entity_id,
        )
        raise


# ponytail: check-then-act window (a row may appear/vanish between this read and
# the module call); accepted for a single-user local app.
async def _has_interpretation(profile_db: AsyncSession, observation_id: str) -> bool:
    """True if a LabInterpretation exists (regenerate then deletes it irreversibly)."""
    res = await profile_db.execute(
        select(LabInterpretation.id)
        .where(LabInterpretation.observation_id == observation_id)
        .limit(1)
    )
    return res.first() is not None


# SAFETY-MODE-VERIFIED: under strict safety mode an observation the patient has
# not verified gets no interpretation. Every route that refuses answers 409 with
# one shape (the batch route lists the id under "failed" instead).
UNVERIFIED_BATCH_ERROR = "Verify this result first"


async def _audit_unverified_refusal(
    master_db: AsyncSession,
    profile_id: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    observation_ids: Optional[list[str]] = None,
) -> None:
    """One audit row per refusal: an observation id, or the unverified member ids of
    a panel. Ids and enums only: no analyte, value, panel name or text. `route` is
    not an allowed audit detail key (core/audit.py), so the entity fields say what
    was refused."""
    details: dict = {"reason": "observation_unverified", "decision": "refuse"}
    if observation_ids is not None:
        details["observation_ids"] = observation_ids
    await _audit_interpretation(
        master_db, "unverified_refused", profile_id,
        entity_type=entity_type, entity_id=entity_id, details=details,
    )


async def _refuse_unverified(
    master_db: AsyncSession,
    profile_id: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    observation_ids: Optional[list[str]] = None,
) -> NoReturn:
    """Audit the refusal, then answer 409. Never returns."""
    await _audit_unverified_refusal(
        master_db, profile_id, entity_type, entity_id, observation_ids,
    )
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"code": "observation_unverified", "message": "Verify this result first."},
    )


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

    # SAFETY-MODE-VERIFIED: refuse before the stored-row shortcut in interpret_observation.
    if not observation.user_verified and await is_strict_safety_mode(profile_db):
        await _refuse_unverified(master_db, session.profile_id, "observation", observation_id)

    # AUDIT-ORDER D: regenerate over an existing interpretation is irreversible.
    started = force_regenerate and await _has_interpretation(profile_db, observation_id)
    if started:
        await _audit_interpretation(
            master_db, "generate", session.profile_id,
            entity_type="observation", entity_id=observation_id, intent="started",
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
    await _audit_interpretation(
        master_db, "generate", session.profile_id,
        entity_type="observation", entity_id=observation_id,
        intent="completed" if started else None,
    )
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

    # SAFETY-MODE-VERIFIED: read once here; the 0.75 module is chosen further down.
    strict = await is_strict_safety_mode(profile_db)
    if strict and not observation.user_verified:
        await _refuse_unverified(master_db, session.profile_id, "observation", observation_id)

    started = force_regenerate and await _has_interpretation(profile_db, observation_id)
    if started:
        await _audit_interpretation(
            master_db, "grounded", session.profile_id,
            entity_type="observation", entity_id=observation_id, intent="started",
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

    # The interpretation may already be written (modules/interpret.py commits
    # it), and rag.query below can still end in 501: audit now, fail-closed.
    await _audit_interpretation(
        master_db, "grounded", session.profile_id,
        entity_type="observation", entity_id=observation_id,
        intent="completed" if started else None,
    )

    # SAFETY-MODE-STRICT: a profile with strict safety mode on gets the 0.75 module.
    rag = get_strict_rag_module() if strict else get_rag_module()
    # IUV-1: an unverified (possibly mis-extracted) value is kept out of the question.
    # It can still reach the model through the RAG context until W-3 (I-13) lands.
    shown = (
        f"{observation.value if observation.value is not None else observation.value_text} "
        if observation.user_verified
        else ""
    )
    question = (
        f"Explain my lab result for {observation.analyte_raw} "
        f"({shown}{observation.unit or ''}) and what it may indicate. "
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
    except RuntimeError as exc:
        logger.error(
            "Grounded interpretation inference failed: %s",
            type(exc).__name__,
            extra={"profile_id": session.profile_id},
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The explanation could not be generated right now. Please try again.",
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

    # SAFE-INTERP-GROUNDED (owner decision 2026-10-04): a prohibited-pattern
    # match must never reach the client. Replace the grounded answer with the
    # fixed escalation template (same as /assistant/chat, SAFE-CHAT) and drop
    # verification detail, which carries claim text from the answer. The
    # grounded answer is not persisted anywhere; audit fail-closed before
    # returning, with no answer or question text.
    if rag_result.prohibited_advice:
        grounded_segments = [
            GroundedSegmentResponse(segment_type="uncertainty", content=ESCALATE_TEMPLATE, citations=[])
        ]
        full_response = ESCALATE_TEMPLATE
        verification = GroundedVerificationResponse()
        await _audit_interpretation(
            master_db, "prohibited_blocked", session.profile_id,
            entity_type="observation", entity_id=observation_id,
            details={"reason": "prohibited_pattern", "decision": "escalate"},
        )
    elif strict and not rag_result.is_valid:
        # SAFETY-MODE-STRICT: under strict safety mode an answer that fails the
        # 0.75 checks is withheld. The withheld text must not ship in
        # full_response either (recurring-failures #2). elif, so the escalation
        # branch above always wins with exactly one prohibited_blocked row.
        grounded_segments = [
            GroundedSegmentResponse(segment_type="uncertainty", content=ABSTAIN_TEMPLATE, citations=[])
        ]
        full_response = ABSTAIN_TEMPLATE
        verification = GroundedVerificationResponse()
        await _audit_interpretation(
            master_db, "strict_abstained", session.profile_id,
            entity_type="observation", entity_id=observation_id,
            details={"reason": "strict_validation_failed", "decision": "abstain"},
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
    master_db: AsyncSession = Depends(get_db),
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

    # SAFETY-MODE-VERIFIED: refuse even when a row is stored, and before viewed_at is written.
    if not observation.user_verified and await is_strict_safety_mode(profile_db):
        await _refuse_unverified(master_db, session.profile_id, "observation", observation_id)

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
        interpretation.viewed_at = utcnow()
        await profile_db.commit()

    await _audit_interpretation(
        master_db, "view", session.profile_id,
        entity_type="observation", entity_id=observation_id,
    )
    return InterpretationResponse.from_model(interpretation)


@router.post(
    "/panels/{panel_name}/interpret",
    response_model=PanelInterpretationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_panel_interpretation(
    panel_name: str,
    collected_at: NaiveUtcDatetime,
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

    # SAFETY-MODE-VERIFIED: refuse before interpret_panel and its stored-row shortcut if
    # any member is unverified. Members are selected exactly as interpret_panel selects
    # them (modules/interpret.py:326-335): same profile, panel analytes, whole day.
    if await is_strict_safety_mode(profile_db):
        day_start = collected_at.replace(hour=0, minute=0, second=0)
        day_end = collected_at.replace(hour=23, minute=59, second=59)
        members = await profile_db.execute(
            select(Observation.id, Observation.user_verified).where(
                Observation.profile_id == session.profile_id,
                Observation.analyte_canonical.in_(PANEL_DEFINITIONS[panel_name_lower]["analytes"]),
                Observation.collected_at >= day_start,
                Observation.collected_at <= day_end,
            )
        )
        unverified_ids = [obs_id for obs_id, verified in members.all() if not verified]
        if unverified_ids:
            await _refuse_unverified(
                master_db, session.profile_id, "panel_interpretation",
                observation_ids=unverified_ids,
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
    # The panel name is clinical content: record the interpretation id only.
    await _audit_interpretation(
        master_db, "panel_generate", session.profile_id,
        entity_type="panel_interpretation", entity_id=result.interpretation.id,
    )
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
    master_db: AsyncSession = Depends(get_db),
):
    """
    Get recent interpretations for the authenticated profile.

    Returns the most recently created interpretations, ordered by date.
    """
    query = select(LabInterpretation).where(
        LabInterpretation.profile_id == session.profile_id
    )
    # SAFETY-MODE-VERIFIED: filter in SQL, before the limit, so a page is never short.
    if await is_strict_safety_mode(profile_db):
        query = query.join(
            Observation, Observation.id == LabInterpretation.observation_id
        ).where(Observation.user_verified.is_(True))
    result = await profile_db.execute(
        query.order_by(LabInterpretation.created_at.desc()).limit(limit)
    )
    interpretations = result.scalars().all()

    await _audit_interpretation(
        master_db, "list_recent", session.profile_id,
        details={"count": len(interpretations), "limit": limit},
    )
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

    # SAFETY-MODE-VERIFIED: under strict mode, read the unverified ids once. They are
    # refused in the loop, so they stay out of the regenerate audit row below.
    strict = await is_strict_safety_mode(profile_db)
    unverified: set[str] = set()
    if strict:
        uuid_ids = [i for i in request.observation_ids if UUID_PATTERN.match(i)]
        if uuid_ids:
            res = await profile_db.execute(
                select(Observation.id).where(
                    Observation.id.in_(uuid_ids),
                    Observation.user_verified.is_(False),
                )
            )
            unverified = set(res.scalars().all())

    # AUDIT-ORDER D: only UUID-shaped ids that already have an interpretation
    # (regenerate deletes it) reach the audit row.
    started = False
    if request.force_regenerate:
        candidates = [
            i for i in request.observation_ids
            if UUID_PATTERN.match(i) and i not in unverified
        ]
        if candidates:
            res = await profile_db.execute(
                select(LabInterpretation.observation_id).where(
                    LabInterpretation.observation_id.in_(candidates)
                )
            )
            existing = set(res.scalars().all())
            at_risk = [i for i in candidates if i in existing]
            if at_risk:
                started = True
                await _audit_interpretation(
                    master_db, "batch_generate", session.profile_id,
                    details={"observation_ids": at_risk, "count": len(at_risk)},
                    intent="started",
                )

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

            # SAFETY-MODE-VERIFIED: refused before generation, listed under "failed".
            if strict and not observation.user_verified:
                await _audit_unverified_refusal(
                    master_db, session.profile_id, "observation", obs_id,
                )
                failed.append({"observation_id": obs_id, "error": UNVERIFIED_BATCH_ERROR})
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
            logger.error("Batch interpretation error for %s: %s", obs_id, type(e).__name__)
            failed.append({"observation_id": obs_id, "error": "Internal error"})

    logger.info(
        f"Batch interpretation: {len(successful)} successful, {len(failed)} failed"
    )

    await _audit_interpretation(
        master_db, "batch_generate", session.profile_id,
        details={
            "observation_ids": successful,
            "count": len(successful),
            "skipped_count": len(failed),
        },
        intent="completed" if started else None,
    )
    return BatchInterpretResponse(successful=successful, failed=failed)
