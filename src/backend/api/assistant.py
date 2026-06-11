"""
RAG Assistant API endpoints.

Provides grounded explanations with citation requirements.
All endpoints require authentication.

Phase 4: Now includes verification metadata in responses.
ASSIST-HIST-001: Session persistence — create/list/resume chat sessions,
  persist every user+assistant turn to the per-profile DB.
ASSIST-MEM-003: Memory injection gated by (request flag AND per-profile setting).
"""

import logging
import uuid
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth import RequireAuth, ProfileDbSession
from core.time import utcnow
from models.chat_session import ChatSession, ChatTurn
from modules.rag import RAGModule, VerificationConfig, ModelUnavailableError
from modules.faithfulness import FaithfulnessConfig

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------

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
    authority_tier: Optional[int] = None
    authority_score: Optional[float] = None


DocumentCategoryValue = Literal["imaging", "pathology", "visit_notes", "lab"]


class ChatRequest(BaseModel):
    """Request model for chat."""
    question: str

    # Optional: resume an existing session (omit to create implicit session)
    session_id: Optional[str] = None

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
    include_references: bool = True

    # Conversation history (for context — used when session_id is absent/legacy)
    history: list[ChatMessage] = []

    # ASSIST-MEM-003: Include user memory items in context
    use_memory: bool = False

    # Phase 4: Verification options
    enable_verification: bool = True
    min_faithfulness_score: Optional[float] = None


class ResponseSegment(BaseModel):
    segment_type: str
    content: str
    citations: list[Citation] = []


class VerificationInfo(BaseModel):
    enabled: bool = False
    total_claims: int = 0
    verified_claims: int = 0
    failed_claims: int = 0
    faithfulness_score: float = 0.0
    authority_score: float = 0.0
    summary: str = ""
    issues: list[str] = []


class ChatResponse(BaseModel):
    """Response model for chat."""
    segments: list[ResponseSegment]
    full_response: str
    insufficient_context: bool = False
    insufficient_reasons: list[str] = []
    verification: VerificationInfo = VerificationInfo()
    is_valid: bool = True
    validation_errors: list[str] = []
    # ASSIST-HIST-001: echo back the session_id (new or resumed)
    session_id: Optional[str] = None


class TestIntentResponse(BaseModel):
    analyte: str
    analyte_display_name: str
    intent_summary: str
    general_info: str
    citations: list[Citation]
    verification: VerificationInfo = VerificationInfo()


class GlossaryTermResponse(BaseModel):
    term: str
    definition: str
    related_terms: list[str] = []
    source: str = ""


# ASSIST-HIST-001 session management models

class SessionSummary(BaseModel):
    session_id: str
    title: Optional[str]
    turn_count: int
    created_at: str
    updated_at: str


class SessionListResponse(BaseModel):
    sessions: list[SessionSummary]


class NewSessionRequest(BaseModel):
    title: Optional[str] = None


class NewSessionResponse(BaseModel):
    session_id: str
    title: Optional[str]
    created_at: str


class SessionHistoryResponse(BaseModel):
    session_id: str
    title: Optional[str]
    turns: list[ChatMessage]


# ---------------------------------------------------------------------------
# RAG module singleton
# ---------------------------------------------------------------------------

_rag_module: Optional[RAGModule] = None


def get_rag_module() -> RAGModule:
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


# ---------------------------------------------------------------------------
# Session persistence helpers
# ---------------------------------------------------------------------------

async def _get_or_create_session(
    session_id: Optional[str],
    profile_id: str,
    first_question: str,
    profile_db: AsyncSession,
) -> ChatSession:
    """
    Return an existing ChatSession or create a new one.

    If session_id is provided and belongs to the profile, use it.
    Otherwise create an implicit session titled from the first question.
    """
    if session_id:
        result = await profile_db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.profile_id == profile_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing
        # Fall through and create a new one (session_id may be stale/foreign)

    title = first_question[:120] if first_question else "New conversation"
    new_session = ChatSession(
        id=str(uuid.uuid4()),
        profile_id=profile_id,
        title=title,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    profile_db.add(new_session)
    await profile_db.flush()  # get the id without committing yet
    return new_session


async def _load_session_history(
    session: ChatSession,
    profile_db: AsyncSession,
) -> list[ChatMessage]:
    """Load ordered turns from DB for a session."""
    result = await profile_db.execute(
        select(ChatTurn)
        .where(ChatTurn.session_id == session.id)
        .order_by(ChatTurn.turn_index)
    )
    turns = result.scalars().all()
    return [ChatMessage(role=t.role, content=t.content) for t in turns]


async def _append_turns(
    session: ChatSession,
    profile_id: str,
    user_content: str,
    assistant_content: str,
    profile_db: AsyncSession,
) -> None:
    """Append a user+assistant turn pair to the DB session."""
    # Determine next turn_index
    count_result = await profile_db.execute(
        select(func.count(ChatTurn.id)).where(ChatTurn.session_id == session.id)
    )
    base_index = count_result.scalar() or 0

    now = utcnow()
    profile_db.add(ChatTurn(
        id=str(uuid.uuid4()),
        session_id=session.id,
        profile_id=profile_id,
        turn_index=base_index,
        role="user",
        content=user_content,
        created_at=now,
    ))
    profile_db.add(ChatTurn(
        id=str(uuid.uuid4()),
        session_id=session.id,
        profile_id=profile_id,
        turn_index=base_index + 1,
        role="assistant",
        content=assistant_content,
        created_at=now,
    ))
    session.updated_at = now


# ---------------------------------------------------------------------------
# Memory-enabled check helper
# ---------------------------------------------------------------------------

async def _effective_use_memory(
    use_memory_request: bool,
    profile_id: str,
    profile_db: AsyncSession,
) -> bool:
    """
    Return True only when BOTH the request flag AND the per-profile
    (or global config) setting allow memory injection.

    Falls back to the global config default when no per-profile row exists.
    """
    if not use_memory_request:
        return False

    from core.config import settings as app_settings

    # Check per-profile setting if available
    try:
        from models.model_settings import UserModelSettings
        result = await profile_db.execute(
            select(UserModelSettings).where(
                UserModelSettings.profile_id == profile_id
            )
        )
        row = result.scalar_one_or_none()
        if row is not None:
            # Per-profile column may not exist on old DBs before migration —
            # getattr with default True mirrors the column default
            per_profile = getattr(row, "assistant_memory_enabled", True)
            return bool(per_profile)
    except Exception:
        pass

    return bool(app_settings.assistant_memory_enabled)


# ---------------------------------------------------------------------------
# Session management endpoints  (ASSIST-HIST-001)
# ---------------------------------------------------------------------------

@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
):
    """List all chat sessions for the authenticated profile, newest first."""
    profile_id = session.profile_id

    sessions_result = await profile_db.execute(
        select(ChatSession)
        .where(ChatSession.profile_id == profile_id)
        .order_by(ChatSession.updated_at.desc())
    )
    sessions = sessions_result.scalars().all()

    summaries = []
    for s in sessions:
        count_result = await profile_db.execute(
            select(func.count(ChatTurn.id)).where(ChatTurn.session_id == s.id)
        )
        turn_count = count_result.scalar() or 0
        summaries.append(SessionSummary(
            session_id=s.id,
            title=s.title,
            turn_count=turn_count,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
        ))

    return SessionListResponse(sessions=summaries)


@router.post("/sessions", response_model=NewSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    data: NewSessionRequest,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
):
    """Explicitly create a new chat session (client-driven)."""
    profile_id = session.profile_id
    now = utcnow()
    new_session = ChatSession(
        id=str(uuid.uuid4()),
        profile_id=profile_id,
        title=data.title or "New conversation",
        created_at=now,
        updated_at=now,
    )
    profile_db.add(new_session)
    await profile_db.commit()
    await profile_db.refresh(new_session)
    return NewSessionResponse(
        session_id=new_session.id,
        title=new_session.title,
        created_at=new_session.created_at.isoformat(),
    )


@router.get("/sessions/{session_id}", response_model=SessionHistoryResponse)
async def get_session_history(
    session_id: str,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
):
    """Return all turns for a session (for client-side reload)."""
    profile_id = session.profile_id

    result = await profile_db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.profile_id == profile_id,
        )
    )
    chat_session = result.scalar_one_or_none()
    if not chat_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    turns = await _load_session_history(chat_session, profile_db)
    return SessionHistoryResponse(
        session_id=chat_session.id,
        title=chat_session.title,
        turns=turns,
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
):
    """Delete a chat session and all its turns."""
    profile_id = session.profile_id
    result = await profile_db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.profile_id == profile_id,
        )
    )
    chat_session = result.scalar_one_or_none()
    if not chat_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    await profile_db.delete(chat_session)
    await profile_db.commit()


# ---------------------------------------------------------------------------
# Memory settings endpoint  (ASSIST-MEM-003)
# ---------------------------------------------------------------------------

class MemorySettingsResponse(BaseModel):
    assistant_memory_enabled: bool
    global_default: bool


class MemorySettingsUpdate(BaseModel):
    assistant_memory_enabled: bool


@router.get("/memory-settings", response_model=MemorySettingsResponse)
async def get_memory_settings(
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
):
    """Return per-profile memory injection toggle + global default."""
    from core.config import settings as app_settings
    from models.model_settings import UserModelSettings

    result = await profile_db.execute(
        select(UserModelSettings).where(
            UserModelSettings.profile_id == session.profile_id
        )
    )
    row = result.scalar_one_or_none()
    per_profile = getattr(row, "assistant_memory_enabled", app_settings.assistant_memory_enabled) if row else app_settings.assistant_memory_enabled
    return MemorySettingsResponse(
        assistant_memory_enabled=bool(per_profile),
        global_default=bool(app_settings.assistant_memory_enabled),
    )


@router.patch("/memory-settings", response_model=MemorySettingsResponse)
async def update_memory_settings(
    data: MemorySettingsUpdate,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
):
    """Toggle per-profile memory injection."""
    from core.config import settings as app_settings
    from models.model_settings import UserModelSettings

    result = await profile_db.execute(
        select(UserModelSettings).where(
            UserModelSettings.profile_id == session.profile_id
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = UserModelSettings(
            id=str(uuid.uuid4()),
            profile_id=session.profile_id,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        profile_db.add(row)

    row.assistant_memory_enabled = data.assistant_memory_enabled
    row.updated_at = utcnow()
    await profile_db.commit()
    await profile_db.refresh(row)
    return MemorySettingsResponse(
        assistant_memory_enabled=bool(row.assistant_memory_enabled),
        global_default=bool(app_settings.assistant_memory_enabled),
    )


# ---------------------------------------------------------------------------
# Main chat endpoint
# ---------------------------------------------------------------------------

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    session: RequireAuth,
    profile_db: ProfileDbSession = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Chat with the grounded assistant.

    Session handling (ASSIST-HIST-001):
    - If request.session_id is provided and valid, resume that session.
    - Otherwise an implicit session is created.
    - Each user+assistant turn is persisted to the per-profile DB.
    - DB history is used as multi-turn context; client-supplied history[]
      is used only as a fallback for clients not sending session_id.

    Memory injection (ASSIST-MEM-003):
    - Injected only when BOTH request.use_memory==True AND the per-profile
      (or global) assistant_memory_enabled flag is True.
    """
    rag = get_rag_module()

    try:
        # Resolve model runner for this request
        runner = None
        try:
            from core.external_runner import get_runner_for_request
            runner = await get_runner_for_request(session.profile_id, profile_db)
        except (ImportError, Exception):
            pass

        # --- ASSIST-HIST-001: session resolution ---
        chat_session = await _get_or_create_session(
            session_id=request.session_id,
            profile_id=session.profile_id,
            first_question=request.question,
            profile_db=profile_db,
        )

        # Load full DB history for this session as multi-turn context
        db_history = await _load_session_history(chat_session, profile_db)

        # Fall back to client-supplied history when session is brand-new
        # (no turns yet) and client sent legacy history
        if not db_history and request.history:
            db_history = list(request.history)

        # --- ASSIST-MEM-003: dual-gate memory ---
        inject_memory = await _effective_use_memory(
            request.use_memory, session.profile_id, profile_db
        )

        result = await rag.query(
            question=request.question,
            profile_id=session.profile_id,
            selected_analytes=request.selected_analytes,
            selected_panel=request.selected_panel,
            from_date=request.from_date,
            to_date=request.to_date,
            include_references=request.include_references,
            history=db_history if db_history else None,
            model_runner=runner,
            master_db=db,
            profile_db=profile_db,
            use_memory=inject_memory,
            category=request.document_category,
        )

        # Build full response text
        full_response = "\n\n".join(
            f"**{seg.segment_type.upper().replace('_', ' ')}**\n{seg.content}"
            for seg in result.segments
        )

        # --- Persist user + assistant turn ---
        await _append_turns(
            session=chat_session,
            profile_id=session.profile_id,
            user_content=request.question,
            assistant_content=full_response,
            profile_db=profile_db,
        )
        await profile_db.commit()

        # --- Auto-extract lightweight memory facts ---
        if inject_memory:
            try:
                await _auto_extract_memory(
                    request.question,
                    session.profile_id,
                    profile_db,
                )
            except Exception:
                pass  # non-fatal

        # Build response
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
            session_id=chat_session.id,
        )

    except ModelUnavailableError:
        return await _build_knowledge_fallback(request, session.profile_id, db)
    except Exception as e:
        logger.exception(
            "Assistant chat request failed",
            extra={"profile_id": session.profile_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing chat request",
        )


# ---------------------------------------------------------------------------
# Lightweight auto-memory extraction  (ASSIST-MEM-004)
# ---------------------------------------------------------------------------

import re as _re

# Patterns for conservative fact extraction.
# Each tuple: (category, regex, value_group_index)
_FACT_PATTERNS: list[tuple[str, _re.Pattern, int]] = [
    # "I take metformin" / "I'm taking lisinopril"
    (
        "medication",
        _re.compile(
            r"\bI(?:'m| am| take| takes)\s+taking\s+([\w\s\-]+?)(?:\s+(?:for|daily|every|mg|tablet)|[,.]|$)",
            _re.IGNORECASE,
        ),
        1,
    ),
    (
        "medication",
        _re.compile(
            r"\bI\s+take\s+([\w\s\-]+?)(?:\s+(?:for|daily|every|mg|tablet)|[,.]|$)",
            _re.IGNORECASE,
        ),
        1,
    ),
    # "I am allergic to penicillin" / "I have an allergy to aspirin"
    (
        "allergy",
        _re.compile(
            r"\bI(?:'m| am)\s+allergic\s+to\s+([\w\s\-]+?)(?:[,.]|$)",
            _re.IGNORECASE,
        ),
        1,
    ),
    (
        "allergy",
        _re.compile(
            r"\ballerg(?:y|ies)\s+to\s+([\w\s\-]+?)(?:[,.]|$)",
            _re.IGNORECASE,
        ),
        1,
    ),
    # "I have diabetes / hypertension / ..."
    (
        "condition",
        _re.compile(
            r"\bI\s+have\s+((?:type\s*[12]\s+)?(?:diabetes|hypertension|asthma|hypothyroid\w*|"
            r"hyperthyroid\w*|celiac|crohn|lupus|fibromyalg\w*|ckd|chronic kidney disease|"
            r"heart failure|copd|epilepsy|anemia|arthritis))",
            _re.IGNORECASE,
        ),
        1,
    ),
]

_MAX_AUTO_MEMORY_ITEMS = 10  # hard cap on auto-extracted facts per profile


async def _auto_extract_memory(
    user_text: str,
    profile_id: str,
    profile_db: AsyncSession,
) -> None:
    """
    Lightweight heuristic extraction of stable user facts into memory items.

    Conservative: only fires on explicit first-person statements about
    medications, allergies, and known chronic conditions.  Duplicates
    (same key+value) are silently skipped.
    """
    from sqlalchemy import select, func
    from models.memory_item import MemoryItem

    # Count existing auto-extracted items to avoid unbounded growth
    count_result = await profile_db.execute(
        select(func.count(MemoryItem.id)).where(
            MemoryItem.profile_id == profile_id,
            MemoryItem.category.in_(["medication", "allergy", "condition"]),
        )
    )
    auto_count = count_result.scalar() or 0
    if auto_count >= _MAX_AUTO_MEMORY_ITEMS:
        return

    for category, pattern, grp in _FACT_PATTERNS:
        for match in pattern.finditer(user_text):
            value = match.group(grp).strip(" .,;")
            if not value or len(value) > 200:
                continue

            key = f"auto:{category}:{value.lower()[:60]}"

            # Skip if already exists (key uniqueness within profile)
            existing = await profile_db.execute(
                select(MemoryItem).where(
                    MemoryItem.profile_id == profile_id,
                    MemoryItem.key == key,
                )
            )
            if existing.scalar_one_or_none():
                continue

            now = utcnow()
            profile_db.add(MemoryItem(
                id=str(uuid.uuid4()),
                profile_id=profile_id,
                key=key,
                value=value,
                category=category,
                created_at=now,
                updated_at=now,
            ))
            auto_count += 1
            if auto_count >= _MAX_AUTO_MEMORY_ITEMS:
                return


# ---------------------------------------------------------------------------
# Knowledge-base fallback (no LLM available)
# ---------------------------------------------------------------------------

@router.get("/test-intent/{analyte}", response_model=TestIntentResponse)
async def get_test_intent(
    analyte: str,
    session: RequireAuth,
    db: AsyncSession = Depends(get_db),
):
    """Get explanation of what a test is typically ordered for."""
    from modules.test_intent import TestIntentModule

    intent_module = TestIntentModule()
    result = intent_module.lookup(analyte)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No information available for analyte: {analyte}",
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
    """Get plain-language definition of a medical term."""
    from modules.glossary import GlossaryModule

    glossary = GlossaryModule()
    result = glossary.lookup(term)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Term not found in glossary: {term}",
        )

    return GlossaryTermResponse(
        term=result["term"],
        definition=result["definition"],
        related_terms=result.get("related_terms", []),
        source=result.get("source", "Medical Reference Glossary"),
    )


@router.get("/verification-status")
async def get_verification_status(session: RequireAuth):
    """Get current verification system status."""
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
    """Build a knowledge-base response when no LLM is available."""
    from modules.glossary import GlossaryModule
    from modules.knowledge_loader import get_knowledge_loader
    from modules.normalize import NormalizeModule

    glossary = GlossaryModule()
    knowledge = get_knowledge_loader()
    normalizer = NormalizeModule()

    segments = []
    question_lower = request.question.lower()

    found_analytes = []
    for canonical, synonyms in normalizer.ANALYTE_SYNONYMS.items():
        if canonical in question_lower or any(syn in question_lower for syn in synonyms):
            found_analytes.append(canonical)

    if request.selected_analytes:
        found_analytes.extend(request.selected_analytes)
    found_analytes = list(set(found_analytes))

    knowledge_parts = []
    for analyte in found_analytes[:3]:
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

    words = question_lower.split()
    for word in words:
        result = glossary.lookup(word)
        if result:
            segments.append(ResponseSegment(
                segment_type="general_info",
                content=f"**{result['term']}**: {result['definition']}",
                citations=[],
            ))
            break

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
        session_id=None,
    )
