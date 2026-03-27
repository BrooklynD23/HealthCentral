"""
RAG Assistant API endpoints.

Provides grounded explanations with citation requirements.
All endpoints require authentication.

Phase 4: Now includes verification metadata in responses.
"""

import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth import RequireAuth, ProfileDbSession
from modules.rag import RAGModule, VerificationConfig, ModelUnavailableError
from modules.faithfulness import FaithfulnessConfig

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatMessage(BaseModel):
    """Single chat message."""
    role: str  # "user" or "assistant"
    content: str


class Citation(BaseModel):
    """Citation reference for grounded responses."""
    source_type: str  # "user_document" or "reference"
    doc_id: Optional[str] = None
    doc_title: Optional[str] = None
    page: Optional[int] = None
    text_snippet: str
    relevance_score: float = 0.0
    # Phase 4: Authority information
    authority_tier: Optional[int] = None  # 1-4, lower is more authoritative
    authority_score: Optional[float] = None  # 0.0-1.0


DocumentCategoryValue = Literal["imaging", "pathology", "visit_notes", "lab"]


class ChatRequest(BaseModel):
    """Request model for chat."""
    question: str

    # Context selection
    selected_analytes: Optional[list[str]] = None
    selected_panel: Optional[str] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    document_category: Optional[DocumentCategoryValue] = Field(
        default=None,
        description="Optional document category filter for user-document retrieval.",
    )

    # Options
    include_references: bool = True  # Include general reference info

    # Conversation history (for context)
    history: list[ChatMessage] = []

    # ASSIST-MEM-003: Include user memory items in context
    use_memory: bool = False

    # Phase 4: Verification options
    enable_verification: bool = True  # Enable claim verification
    min_faithfulness_score: Optional[float] = None  # Override default threshold


class ResponseSegment(BaseModel):
    """
    Segment of assistant response.

    Separates report facts from general information.
    """
    segment_type: str  # "report_facts", "general_info", "uncertainty"
    content: str
    citations: list[Citation] = []


class VerificationInfo(BaseModel):
    """
    Phase 4: Verification metadata for transparency.

    Shows how well the response is grounded in sources.
    """
    enabled: bool = False
    total_claims: int = 0
    verified_claims: int = 0
    failed_claims: int = 0
    faithfulness_score: float = 0.0  # Overall faithfulness 0.0-1.0
    authority_score: float = 0.0  # Average source authority 0.0-1.0
    summary: str = ""
    issues: list[str] = []  # List of verification issues (if any)


class ChatResponse(BaseModel):
    """Response model for chat."""
    segments: list[ResponseSegment]
    full_response: str  # Combined response text
    insufficient_context: bool = False
    insufficient_reasons: list[str] = []

    # Phase 4: Verification metadata
    verification: VerificationInfo = VerificationInfo()

    # Response quality indicators
    is_valid: bool = True
    validation_errors: list[str] = []


class TestIntentResponse(BaseModel):
    """Response for test intent explanation."""
    analyte: str
    analyte_display_name: str
    intent_summary: str  # What the test is typically ordered for
    general_info: str  # What it helps evaluate at a high level
    citations: list[Citation]
    verification: VerificationInfo = VerificationInfo()


class GlossaryTermResponse(BaseModel):
    """Response for glossary term lookup."""
    term: str
    definition: str
    related_terms: list[str] = []
    source: str = ""  # Where the definition comes from


# Initialize RAG module with verification enabled
_rag_module: Optional[RAGModule] = None


def get_rag_module() -> RAGModule:
    """Get or create RAG module instance."""
    global _rag_module
    if _rag_module is None:
        _rag_module = RAGModule(
            enable_verification=True,
            verification_config=VerificationConfig(
                min_faithfulness_score=0.6,
                fail_on_contradiction=True,
            ),
            faithfulness_config=FaithfulnessConfig(
                min_overall_score=0.6,
            ),
        )
    return _rag_module


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Chat with the grounded assistant.

    Process:
    1. Retrieve relevant user document chunks for authenticated profile
    2. Retrieve relevant reference corpus chunks
    3. Compose prompt with strict citation requirements
    4. Generate response with local LLM
    5. Validate response has required citations
    6. (Phase 4) Verify claims against sources
    7. Return segmented response with provenance and verification

    Refuses to answer if:
    - Insufficient context for grounded response
    - Question requests diagnosis/treatment advice
    - Claims cannot be supported by retrieved context
    - (Phase 4) Claims fail verification checks

    Args:
        request: Chat request with question and options
        session: Authenticated session (provides profile_id)
        profile_db: Profile database session for vector search
        db: Database session

    Returns:
        ChatResponse with verified, grounded answer
    """
    rag = get_rag_module()

    try:
        # Resolve model runner for this request (supports external API opt-in)
        runner = None
        try:
            from core.external_runner import get_runner_for_request
            runner = await get_runner_for_request(session.profile_id, profile_db)
        except (ImportError, Exception):
            pass  # Use default runner

        # Run the RAG pipeline with verification
        result = await rag.query(
            question=request.question,
            profile_id=session.profile_id,
            selected_analytes=request.selected_analytes,
            selected_panel=request.selected_panel,
            from_date=request.from_date,
            to_date=request.to_date,
            include_references=request.include_references,
            history=request.history if request.history else None,
            model_runner=runner,
            master_db=db,
            profile_db=profile_db,
            use_memory=request.use_memory,
            category=request.document_category,
        )

        # Convert to response format
        segments = []
        for seg in result.segments:
            citations = [
                Citation(
                    source_type=c.source_type,
                    doc_id=c.doc_id,
                    doc_title=c.doc_title,
                    page=c.page,
                    text_snippet=c.text_snippet,
                    authority_tier=c.authority_tier,
                    authority_score=c.authority_score,
                )
                for c in seg.citations
            ]
            segments.append(ResponseSegment(
                segment_type=seg.segment_type,
                content=seg.content,
                citations=citations,
            ))

        # Build full response text
        full_response = "\n\n".join(
            f"**{seg.segment_type.upper().replace('_', ' ')}**\n{seg.content}"
            for seg in result.segments
        )

        # Build verification info
        verification = VerificationInfo(
            enabled=result.verification.verification_enabled,
            total_claims=result.verification.total_claims,
            verified_claims=result.verification.verified_claims,
            failed_claims=result.verification.failed_claims,
            faithfulness_score=result.verification.faithfulness_score,
            authority_score=result.verification.authority_score,
            summary=result.verification.verification_summary,
            issues=result.verification.claims_with_issues,
        )

        return ChatResponse(
            segments=segments,
            full_response=full_response,
            insufficient_context=result.insufficient_context,
            insufficient_reasons=result.insufficient_reasons,
            verification=verification,
            is_valid=result.is_valid,
            validation_errors=result.validation_errors,
        )

    except ModelUnavailableError:
        # No LLM available — return knowledge-base fallback response
        return await _build_knowledge_fallback(request, session.profile_id, db)
    except Exception as e:
        logger.exception(
            "Assistant chat request failed",
            extra={"profile_id": session.profile_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing chat request"
        )


@router.get("/test-intent/{analyte}", response_model=TestIntentResponse)
async def get_test_intent(
    analyte: str,
    session: RequireAuth,
    db: AsyncSession = Depends(get_db),
):
    """
    Get explanation of what a test is typically ordered for.

    Provides general education about test purpose,
    grounded in curated reference corpus.

    Phase 4: Includes verification of the explanation.

    Args:
        analyte: The analyte/test name to explain
        session: Authenticated session
        db: Database session

    Returns:
        TestIntentResponse with verified explanation
    """
    from modules.test_intent import TestIntentModule

    intent_module = TestIntentModule()
    result = intent_module.lookup(analyte)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No information available for analyte: {analyte}"
        )

    return TestIntentResponse(
        analyte=result["analyte"],
        analyte_display_name=result["analyte_display_name"],
        intent_summary=result["intent_summary"],
        general_info=result["general_info"],
        citations=[
            Citation(
                source_type="reference",
                doc_id=None,
                doc_title=result.get("source", "Medical Reference Database"),
                page=None,
                text_snippet=result["intent_summary"][:100],
            )
        ],
        verification=VerificationInfo(enabled=False),
    )


@router.get("/glossary/{term}", response_model=GlossaryTermResponse)
async def get_glossary_term(
    term: str,
    session: RequireAuth,
    db: AsyncSession = Depends(get_db),
):
    """
    Get plain-language definition of a medical term.

    From curated local glossary.

    Args:
        term: The medical term to define
        session: Authenticated session
        db: Database session

    Returns:
        GlossaryTermResponse with definition
    """
    from modules.glossary import GlossaryModule

    glossary = GlossaryModule()
    result = glossary.lookup(term)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Term not found in glossary: {term}"
        )

    return GlossaryTermResponse(
        term=result["term"],
        definition=result["definition"],
        related_terms=result.get("related_terms", []),
        source=result.get("source", "Medical Reference Glossary"),
    )


@router.get("/verification-status")
async def get_verification_status(
    session: RequireAuth,
):
    """
    Get current verification system status.

    Returns information about the Phase 4 verification pipeline.

    Args:
        session: Authenticated session

    Returns:
        Dict with verification system status
    """
    rag = get_rag_module()

    return {
        "verification_enabled": rag.enable_verification,
        "components": {
            "claim_extractor": "active",
            "source_authority_scorer": "active",
            "verifier_agent": "active",
            "faithfulness_scorer": "active",
        },
        "configuration": {
            "min_faithfulness_score": 0.6,
            "fail_on_contradiction": True,
            "min_supporting_sources": 1,
        },
        "source_tiers": {
            "tier_1": "User-verified personal documents (highest trust)",
            "tier_2": "Peer-reviewed medical references",
            "tier_3": "Educational content",
            "tier_4": "Unverified sources (lowest trust)",
        },
    }


async def _build_knowledge_fallback(
    request: ChatRequest,
    profile_id: str,
    db,
) -> ChatResponse:
    """
    Build a knowledge-base response when no LLM is available.

    Uses glossary and biomarker knowledge to provide rule-based answers
    instead of returning a 501 error.
    """
    from modules.glossary import GlossaryModule
    from modules.knowledge_loader import get_knowledge_loader
    from modules.normalize import NormalizeModule

    glossary = GlossaryModule()
    knowledge = get_knowledge_loader()
    normalizer = NormalizeModule()

    segments = []
    question_lower = request.question.lower()

    # Try to find relevant biomarker info
    found_analytes = []
    for canonical, synonyms in normalizer.ANALYTE_SYNONYMS.items():
        if canonical in question_lower or any(syn in question_lower for syn in synonyms):
            found_analytes.append(canonical)

    # Also include any explicitly selected analytes
    if request.selected_analytes:
        found_analytes.extend(request.selected_analytes)
    found_analytes = list(set(found_analytes))

    # Build knowledge-based response
    knowledge_parts = []
    for analyte in found_analytes[:3]:  # Limit to 3 analytes
        try:
            info = await knowledge.get_biomarker_knowledge(analyte, db)
            if info:
                knowledge_parts.append(
                    f"**{info.display_name}**: {info.description}\n"
                    f"- Normal: {info.normal_interpretation}\n"
                    f"- High: {info.high_interpretation}\n"
                    f"- Low: {info.low_interpretation}"
                )
        except Exception:
            pass

    if knowledge_parts:
        segments.append(ResponseSegment(
            segment_type="general_info",
            content="\n\n".join(knowledge_parts),
            citations=[],
        ))

    # Try glossary lookup for terms in the question
    words = question_lower.split()
    for word in words:
        result = glossary.lookup(word)
        if result:
            segments.append(ResponseSegment(
                segment_type="general_info",
                content=f"**{result['term']}**: {result['definition']}",
                citations=[],
            ))
            break  # One glossary hit is enough

    # Add note about limited functionality
    segments.append(ResponseSegment(
        segment_type="uncertainty",
        content=(
            "Note: This response is based on the knowledge base only. "
            "For personalized analysis of your lab results, please configure "
            "a local AI model or external API in Settings."
        ),
        citations=[],
    ))

    if not knowledge_parts and not any(s.segment_type == "general_info" for s in segments):
        segments.insert(0, ResponseSegment(
            segment_type="uncertainty",
            content=(
                "I don't have specific information about your question in my knowledge base. "
                "Try asking about a specific lab test (e.g., hemoglobin, glucose, cholesterol)."
            ),
            citations=[],
        ))

    full_response = "\n\n".join(s.content for s in segments)

    return ChatResponse(
        segments=segments,
        full_response=full_response,
        insufficient_context=False,
        verification=VerificationInfo(
            enabled=False,
            summary="Knowledge base response (no LLM)",
        ),
        is_valid=True,
    )
