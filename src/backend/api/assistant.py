"""
RAG Assistant API endpoints.

Provides grounded explanations with citation requirements.
All endpoints require authentication.

Phase 4: Now includes verification metadata in responses.
ASSIST-HIST-001: Session persistence — create/list/resume chat sessions,
  persist every user+assistant turn to the per-profile DB.
ASSIST-MEM-003: Memory injection gated by (request flag AND per-profile setting).
Agent Overhaul S5-1: POST /chat serves via the agent graph when
  is_agent_enabled(settings) is True (the default post-cutover), falling back
  to the legacy rag.query path on any agent exception or when the flag is
  explicitly off. Session/turn persistence is identical on both paths.
"""

import logging
import uuid
from contextlib import asynccontextmanager
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth import RequireAuth, ProfileDbSession
from core.time import utcnow
from models.chat_session import ChatSession, ChatTurn
from models.model_settings import UserModelSettings
from models.document import Document
from models.observation import Observation
from modules.rag import RAGModule, VerificationConfig, ModelUnavailableError
from modules.faithfulness import FaithfulnessConfig
from modules.agent.cache import (
    CacheKey,
    get_cached,
    normalize_question,
    put_cached,
)
from modules.agent.graph import RunContext, new_run_id, run_agent
from modules.agent.schemas import AgentTerminal
from modules.agent.settings import is_agent_enabled

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    """Single chat message."""
    role: str  # "user" or "assistant"
    content: str
    # Persisted ChatTurn.id — populated when returned from DB history so the
    # client can attach feedback to the real turn. Omitted on request input.
    turn_id: Optional[str] = None


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
    # CITE-SRC-001: deep-link target, so a citation is checkable evidence
    # rather than a label. All optional and additive — a citation with no
    # resolvable source (a reference-corpus entry, say) simply leaves them
    # unset, and the UI renders it as non-interactive.
    observation_id: Optional[str] = None
    entity_id: Optional[str] = None
    source_page: Optional[int] = None
    source_bbox_json: Optional[str] = None  # "[x0,y0,x1,y1]" in page coords


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
    # Persisted assistant ChatTurn.id, for attaching feedback (RL-FEED-001)
    turn_id: Optional[str] = None


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
    return [ChatMessage(role=t.role, content=t.content, turn_id=t.id) for t in turns]


async def _append_turns(
    session: ChatSession,
    profile_id: str,
    user_content: str,
    assistant_content: str,
    profile_db: AsyncSession,
) -> str:
    """Append a user+assistant turn pair to the DB session.

    Returns the assistant ChatTurn.id so callers can attach feedback to the
    persisted turn (RL-FEED-001).
    """
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
    assistant_turn_id = str(uuid.uuid4())
    profile_db.add(ChatTurn(
        id=assistant_turn_id,
        session_id=session.id,
        profile_id=profile_id,
        turn_index=base_index + 1,
        role="assistant",
        content=assistant_content,
        created_at=now,
    ))
    session.updated_at = now
    return assistant_turn_id


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
# Agent cutover helpers (Agent Overhaul S5-1, S5-2)
# ---------------------------------------------------------------------------

async def _get_user_model_settings(
    profile_id: str,
    profile_db: AsyncSession,
) -> Optional[UserModelSettings]:
    """Fetch the profile's UserModelSettings row, or None if it has never
    saved settings (is_agent_enabled treats that as AGENT_ENABLED_DEFAULT).
    """
    result = await profile_db.execute(
        select(UserModelSettings).where(UserModelSettings.profile_id == profile_id)
    )
    return result.scalar_one_or_none()


async def _profile_version(profile_id: str, profile_db: AsyncSession) -> str:
    """Cache version source (S5-2): a fingerprint of the evidence this profile's
    agent can ground an answer in.

    PRD §10 Q4 requires that changed data can never serve a cached answer. The
    original derivation was a COUNT of verified observations, and a count is not
    a version: it decreases on delete, so deleting one verified observation and
    verifying a different one returned the count — and therefore the CacheKey —
    to a value the cache had already seen, serving an answer about data that no
    longer existed (HC-CACHE-VER-001).

    Two sources are fingerprinted because two feed the agent's tools: verified
    observations (``query_observations``, ``compute_trend``) and verified
    documents (``retrieve_chunks``, which filters on
    ``Document.status == "verified"``). Each contributes a count paired with the
    latest ``verified_at``, so the value changes on a verify, on a delete, and on
    the delete-then-verify sequence that collides on count alone.

    Memory items are deliberately excluded: no agent tool reads them
    (``modules/agent/tools/`` has no memory tool), so they cannot change an
    agent answer. Add them here if that ever stops being true.

    Residual: two evidence sets could collide only by sharing both counts and
    both microsecond ``verified_at`` maxima — a delete and a verify landing on
    the identical timestamp with compensating counts. Fingerprinting the full id
    set would close it exactly, at the cost of fetching every row per request.
    """
    obs_result = await profile_db.execute(
        select(func.count(Observation.id), func.max(Observation.verified_at)).where(
            Observation.profile_id == profile_id,
            Observation.user_verified == True,  # noqa: E712
        )
    )
    obs_count, obs_latest = obs_result.one()

    doc_result = await profile_db.execute(
        select(func.count(Document.id), func.max(Document.verified_at)).where(
            Document.profile_id == profile_id,
            Document.status == "verified",
        )
    )
    doc_count, doc_latest = doc_result.one()

    return f"o:{obs_count or 0}:{obs_latest or ''}|d:{doc_count or 0}:{doc_latest or ''}"


def _agent_terminal_to_response_parts(
    terminal: AgentTerminal,
) -> tuple[list[ResponseSegment], VerificationInfo]:
    """Map an AgentTerminal onto the ChatResponse's segments/verification
    shape (ChatResponse schema itself is unchanged — no breaking client
    changes). One segment carries the terminal's text; "answer" terminals
    are grounded (every sentence in them already carries a citation per
    draft/guard's contract) so verification reports them as such, while
    abstain/escalate are fixed-template, zero-claim terminals.
    """
    def _to_api_citation(c) -> Citation:
        """Map an agent citation onto the API shape (CITE-SRC-001).

        The agent carries every row id as source_type="document", so
        `source_kind` is what says whether source_id is an observation, a care
        task, an entity or a timeline event. Only observations and entities are
        deep-linkable today — tasks and events have no page/bbox of their own,
        so they are left without a target and the UI renders them as plain
        labels rather than dead buttons.
        """
        kind = getattr(c, "source_kind", None)
        is_document = c.source_type == "document"
        return Citation(
            source_type="reference" if c.source_type == "reference" else "user_document",
            # `locator` carries the doc id for entity-backed citations.
            doc_id=(c.locator if kind == "entity" else None) if is_document else None,
            doc_title=None,
            page=None,
            observation_id=c.source_id if kind == "observation" else None,
            entity_id=c.source_id if kind == "entity" else None,
            text_snippet=c.locator or c.source_id,
            relevance_score=1.0,
        )

    citations = [_to_api_citation(c) for c in terminal.citations]

    segment_type = "report_facts" if terminal.terminal == "answer" else "uncertainty"
    segments = [
        ResponseSegment(segment_type=segment_type, content=terminal.text, citations=citations)
    ]

    is_answer = terminal.terminal == "answer"
    verification = VerificationInfo(
        enabled=True,
        total_claims=len(citations) if is_answer else 0,
        verified_claims=len(citations) if is_answer else 0,
        failed_claims=0,
        faithfulness_score=1.0 if is_answer else 0.0,
        authority_score=1.0 if is_answer else 0.0,
        summary=f"agent:{terminal.terminal}",
        issues=[],
    )
    return segments, verification


async def _serve_via_agent(
    question: str,
    profile_id: str,
    profile_db: AsyncSession,
    db: AsyncSession,
) -> tuple[list[ResponseSegment], str, VerificationInfo]:
    """Run the agent graph for ``question`` and return (segments,
    full_response, verification) — the same shapes the legacy rag.query path
    produces, so the caller's session/turn persistence is unaffected.

    Consults the semantic cache (S5-2) first: a hit short-circuits the run
    entirely. PHI: nothing here logs the raw question; only the run_id and
    handle/count-shaped audit details cross into logging (audit.py contract).
    """
    profile_version = await _profile_version(profile_id, profile_db)
    cache_key = CacheKey(
        normalized_question=normalize_question(question),
        profile_version=profile_version,
    )

    cached = get_cached(cache_key)
    if cached is not None:
        segments, verification = _agent_terminal_to_response_parts(cached)
        return segments, cached.text, verification

    @asynccontextmanager
    async def _db_session_factory():
        yield profile_db

    ctx = RunContext(
        profile_id=profile_id,
        run_id=new_run_id(),
        db_session_factory=_db_session_factory,
        audit_db=db,
    )
    terminal = await run_agent(question, ctx)

    put_cached(cache_key, terminal)

    segments, verification = _agent_terminal_to_response_parts(terminal)
    return segments, terminal.text, verification


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
    chat_session = None

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

        # --- Agent Overhaul S5-1: agent path with legacy fallback ---
        # Resolve the persisted per-profile flag (resolves RECONCILIATION
        # R-8); None (fresh profile, no settings row) falls through to
        # AGENT_ENABLED_DEFAULT inside is_agent_enabled.
        user_model_settings = await _get_user_model_settings(session.profile_id, profile_db)
        use_agent = is_agent_enabled(user_model_settings)

        agent_failed = False
        if use_agent:
            try:
                segments, full_response, verification = await _serve_via_agent(
                    question=request.question,
                    profile_id=session.profile_id,
                    profile_db=profile_db,
                    db=db,
                )
                insufficient_context = False
                insufficient_reasons: list[str] = []
                is_valid = True
                validation_errors: list[str] = []
            except Exception:
                # One-release safety net (S5-1 AC): ANY agent exception falls
                # back to the legacy path below so the user still gets an
                # answer. Never log the raw question (PHI) — handles/counts
                # only, per the agent audit contract.
                logger.exception(
                    "Agent path failed; falling back to legacy rag.query",
                    extra={"profile_id": session.profile_id},
                )
                agent_failed = True

        if not use_agent or agent_failed:
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

            insufficient_context = result.insufficient_context
            insufficient_reasons = result.insufficient_reasons
            is_valid = result.is_valid
            validation_errors = result.validation_errors

        # --- Persist user + assistant turn (identical on both paths) ---
        assistant_turn_id = await _append_turns(
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

        return ChatResponse(
            segments=segments,
            full_response=full_response,
            insufficient_context=insufficient_context,
            insufficient_reasons=insufficient_reasons,
            verification=verification,
            is_valid=is_valid,
            validation_errors=validation_errors,
            session_id=chat_session.id,
            turn_id=assistant_turn_id,
        )

    except ModelUnavailableError:
        fallback = await _build_knowledge_fallback(
            request, session.profile_id, db, profile_db
        )
        # Persist the fallback turn so no-model installs can resume from history
        # and attach feedback (Codex P2). Best-effort: never fail the response.
        if chat_session is not None:
            try:
                fallback.turn_id = await _append_turns(
                    session=chat_session,
                    profile_id=session.profile_id,
                    user_content=request.question,
                    assistant_content=fallback.full_response,
                    profile_db=profile_db,
                )
                await profile_db.commit()
                fallback.session_id = chat_session.id
            except Exception:
                await profile_db.rollback()
        return fallback
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


async def _build_care_task_fallback(request: ChatRequest, profile_db) -> ChatResponse:
    """No-LLM deterministic answer for the open-tasks intent (HC-M24).

    Lists open + needs_review care_plan_task rows (both count as "still
    outstanding" from the user's point of view) with their source quotes,
    each carrying a citation. Record-keeping framing only — never advice.
    ``verification.enabled`` stays False, same as the rest of the fallback.
    """
    from models.care_plan_task import CarePlanTask
    from modules.agent.guardrails.redaction_gate import sanitize_untrusted_field

    result = await profile_db.execute(
        select(CarePlanTask)
        .where(CarePlanTask.status.in_(["open", "needs_review"]))
        .order_by(CarePlanTask.created_at.desc())
        .limit(50)
    )
    tasks = result.scalars().all()

    citations: list[Citation] = []
    lines: list[str] = []
    for task in tasks:
        title = sanitize_untrusted_field(task.title)
        due = f" (due {task.due_date.isoformat()})" if task.due_date else ""
        quote = sanitize_untrusted_field(task.source_quote)
        quote_part = f' The note says: "{quote}"' if quote else ""
        lines.append(f"- {title}{due}.{quote_part}")
        citations.append(Citation(
            source_type="user_observation",
            doc_id=task.source_document_id,
            doc_title="Care task",
            # CITE-SRC-001: a task points back at the entity it was derived from.
            entity_id=task.source_entity_id,
            text_snippet=(quote or title)[:200],
            relevance_score=1.0,
        ))

    plural = "s" if len(tasks) != 1 else ""
    header = f"You have {len(tasks)} open follow-up item{plural}."
    content = header + ("\n" + "\n".join(lines) if lines else "")

    segments = [
        ResponseSegment(segment_type="report_facts", content=content, citations=citations),
        ResponseSegment(
            segment_type="uncertainty",
            content=(
                "Note: This response is based on your recorded follow-up tasks only. "
                "For personalized analysis, please configure a local AI model or "
                "external API in Settings."
            ),
            citations=[],
        ),
    ]

    return ChatResponse(
        segments=segments,
        full_response="\n\n".join(s.content for s in segments),
        insufficient_context=False,
        verification=VerificationInfo(enabled=False, summary="Care task response (no LLM)"),
        is_valid=True,
        session_id=None,
    )


async def _build_med_change_fallback(request: ChatRequest, profile_db) -> ChatResponse:
    """No-LLM deterministic answer for the medication-changes intent (HC-M24).

    Lists verified ``medication_change`` DocumentEntity rows (unverified/
    rejected NEVER returned) with their source quotes, each carrying a
    citation. Record-keeping framing only — never advice.
    ``verification.enabled`` stays False, same as the rest of the fallback.
    """
    from models.document import Document
    from models.document_category import DocumentEntity
    from modules.agent.guardrails.redaction_gate import sanitize_untrusted_field

    result = await profile_db.execute(
        select(DocumentEntity, Document.collection_date)
        .join(Document, DocumentEntity.doc_id == Document.id)
        .where(
            DocumentEntity.entity_type == "medication_change",
            DocumentEntity.verified_by_user == True,  # noqa: E712
        )
        .order_by(Document.collection_date.desc())
        .limit(50)
    )
    rows = result.all()

    citations: list[Citation] = []
    lines: list[str] = []
    for entity, collection_date in rows:
        value = sanitize_untrusted_field(entity.entity_value)
        quote = sanitize_untrusted_field(entity.quote)
        date_str = f" ({collection_date.strftime('%Y-%m-%d')})" if collection_date else ""
        quote_part = f' The note says: "{quote}"' if quote else ""
        lines.append(f"- {value}{date_str}.{quote_part}")
        citations.append(Citation(
            source_type="user_observation",
            doc_id=entity.doc_id,
            doc_title="Medication change",
            # CITE-SRC-001: deep-link to the exact extracted entity.
            entity_id=entity.id,
            source_page=entity.source_page,
            source_bbox_json=entity.source_bbox_json,
            page=entity.source_page,
            text_snippet=(quote or value)[:200],
            relevance_score=1.0,
        ))

    plural = "s" if len(rows) != 1 else ""
    header = f"You have {len(rows)} recorded medication change{plural}."
    content = header + ("\n" + "\n".join(lines) if lines else "")

    segments = [
        ResponseSegment(segment_type="report_facts", content=content, citations=citations),
        ResponseSegment(
            segment_type="uncertainty",
            content=(
                "Note: This response is based on your recorded medication changes only. "
                "For personalized analysis, please configure a local AI model or "
                "external API in Settings."
            ),
            citations=[],
        ),
    ]

    return ChatResponse(
        segments=segments,
        full_response="\n\n".join(s.content for s in segments),
        insufficient_context=False,
        verification=VerificationInfo(enabled=False, summary="Medication change response (no LLM)"),
        is_valid=True,
        session_id=None,
    )


async def _build_knowledge_fallback(
    request: ChatRequest,
    profile_id: str,
    db,
    profile_db=None,
) -> ChatResponse:
    """Build a knowledge-base response when no LLM is available.

    When profile_db is provided, we augment each analyte block with the
    user's latest observed value, reference range, and flag so the
    answer is grounded in their own data even without an LLM.

    HC-M24: two deterministic record-navigation intents are checked FIRST,
    before the analyte path below — open-tasks and medication-changes
    questions never name a biomarker, so routing them through the analyte
    KB lookup would just fall through to "I don't have specific information".
    Reuses the SAME intent keyword-detection the agent's plan node uses
    (``modules.agent.nodes.plan``) so the two surfaces can't drift on what
    counts as each intent.
    """
    from modules.agent.nodes.plan import _detect_care_task_intent, _detect_med_change_intent

    if profile_db is not None and _detect_care_task_intent(request.question):
        return await _build_care_task_fallback(request, profile_db)
    if profile_db is not None and _detect_med_change_intent(request.question):
        return await _build_med_change_fallback(request, profile_db)

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

    # Pull latest observation for each analyte so fallback is user-grounded
    async def _fetch_latest_obs(analyte: str):
        if profile_db is None:
            return None
        try:
            from sqlalchemy import select
            from models.observation import Observation
            result = await profile_db.execute(
                select(Observation)
                .where(
                    Observation.profile_id == profile_id,
                    Observation.analyte_canonical == analyte,
                    Observation.value.isnot(None),
                )
                .order_by(Observation.collected_at.desc().nullslast())
                .limit(1)
            )
            return result.scalar_one_or_none()
        except Exception:
            return None

    knowledge_parts = []
    obs_citations = []
    for analyte in found_analytes[:3]:
        try:
            info = await knowledge.get_biomarker_knowledge(analyte, db)
            obs = await _fetch_latest_obs(analyte)

            if info:
                part_lines = [f"**{info.display_name}**: {info.description}"]

                # ── User's own result block ──────────────────────────────
                if obs is not None:
                    val_str = str(obs.value)
                    if obs.unit:
                        val_str += f" {obs.unit}"
                    date_str = ""
                    if obs.collected_at:
                        date_str = f" (collected {obs.collected_at.strftime('%Y-%m-%d')})"
                    ref_str = ""
                    if obs.ref_low is not None and obs.ref_high is not None:
                        ref_str = f"{obs.ref_low}–{obs.ref_high}"
                        if obs.unit:
                            ref_str += f" {obs.unit}"
                    elif obs.ref_range_text:
                        ref_str = obs.ref_range_text
                    flag_str = ""
                    if obs.flag:
                        flag_str = f"  **[{obs.flag.upper()}]**"
                    elif obs.is_abnormal:
                        if obs.ref_high is not None and obs.value > obs.ref_high:
                            flag_str = "  **[HIGH]**"
                        elif obs.ref_low is not None and obs.value < obs.ref_low:
                            flag_str = "  **[LOW]**"

                    cite_idx = len(obs_citations) + 1
                    obs_citations.append(Citation(
                        source_type="user_observation",
                        doc_id=obs.doc_id,
                        doc_title=f"Your {info.display_name} Result",
                        # CITE-SRC-001: the row is in hand here, so carry the
                        # deep-link target. `page` was hardcoded None even
                        # though source_page has been populated since HC-M12.
                        # getattr: this whole block is wrapped in a bare
                        # `except Exception: pass`, so a missing provenance
                        # attribute would silently drop the entire biomarker
                        # explanation. Provenance is nice to have; the
                        # explanation is the point.
                        page=getattr(obs, "source_page", None),
                        observation_id=getattr(obs, "id", None),
                        source_page=getattr(obs, "source_page", None),
                        source_bbox_json=getattr(obs, "source_bbox_json", None),
                        text_snippet=f"{info.display_name}: {val_str}{date_str}",
                        relevance_score=0.95,
                    ))
                    result_line = f"  **Your result**: {val_str}{date_str}{flag_str} [cite:{cite_idx}]"
                    if ref_str:
                        result_line += f"\n  Reference range: {ref_str}"
                    part_lines.append(result_line)

                # ── Standard interpretation guidance ─────────────────────
                part_lines.append(f"- Normal: {info.normal_interpretation}")
                part_lines.append(f"- High: {info.high_interpretation}")
                part_lines.append(f"- Low: {info.low_interpretation}")
                knowledge_parts.append("\n".join(part_lines))
        except Exception:
            pass

    if knowledge_parts:
        segments.append(ResponseSegment(
            segment_type="general_info",
            content="\n\n".join(knowledge_parts),
            citations=obs_citations,
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
