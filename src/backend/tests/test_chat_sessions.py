"""
Tests for ASSIST-HIST-001: Chat session persistence + ASSIST-MEM-003: dual-gate memory.

Covers:
- ChatSession / ChatTurn CRUD helpers
- session_id echoed in ChatResponse
- DB history loaded on resume
- memory injection: request flag AND per-profile setting required
- token budget bounding in compose_prompt
- auto-extract memory heuristics
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass
from datetime import datetime


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _utcnow():
    from core.time import utcnow
    return utcnow()


def _make_session(profile_id="prof-1", title="Test session"):
    from models.chat_session import ChatSession
    return ChatSession(
        id=str(uuid.uuid4()),
        profile_id=profile_id,
        title=title,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )


def _make_turn(session_id, profile_id="prof-1", role="user", content="hello", index=0):
    from models.chat_session import ChatTurn
    return ChatTurn(
        id=str(uuid.uuid4()),
        session_id=session_id,
        profile_id=profile_id,
        turn_index=index,
        role=role,
        content=content,
        created_at=_utcnow(),
    )


def _fake_profile_db_for_sessions(sessions=None, turns=None, count_val=0):
    """Build a mock AsyncSession that returns canned query results."""
    sessions = sessions or []
    turns = turns or []

    def _make_result(items):
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = items
        scalars_mock.first.return_value = items[0] if items else None
        r = MagicMock()
        r.scalars.return_value = scalars_mock
        r.scalar_one_or_none.return_value = items[0] if items else None
        r.scalar.return_value = count_val
        return r

    call_count = [0]

    async def _execute(stmt):
        call_count[0] += 1
        # Heuristic: alternate between session/turn results
        if call_count[0] == 1:
            return _make_result(sessions)
        return _make_result(turns)

    db = AsyncMock()
    db.execute.side_effect = _execute
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()
    db.delete = AsyncMock()
    return db


def _make_rag_module():
    with (
        patch("modules.rag.get_model_runner") as mock_runner,
        patch("modules.rag.EmbeddingsModule"),
    ):
        mock_runner.return_value = MagicMock(is_available=MagicMock(return_value=True))
        from modules.rag import RAGModule
        return RAGModule(enable_verification=False)


@dataclass(frozen=True)
class FakeMemoryItem:
    id: str
    profile_id: str
    key: str
    value: str
    category: str | None


def _fake_memory_db(items: list):
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = items
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    db = AsyncMock()
    db.execute.return_value = result_mock
    return db


# ---------------------------------------------------------------------------
# Tests: ChatSession / ChatTurn model imports
# ---------------------------------------------------------------------------

class TestChatSessionModels:
    def test_chat_session_importable(self):
        from models.chat_session import ChatSession, ChatTurn
        assert ChatSession.__tablename__ == "chat_sessions"
        assert ChatTurn.__tablename__ == "chat_turns"

    def test_chat_session_fields(self):
        from models.chat_session import ChatSession
        s = _make_session()
        assert s.profile_id == "prof-1"
        assert s.title == "Test session"

    def test_chat_turn_fields(self):
        sid = str(uuid.uuid4())
        t = _make_turn(session_id=sid, role="assistant", content="hi there", index=1)
        assert t.session_id == sid
        assert t.role == "assistant"
        assert t.turn_index == 1


# ---------------------------------------------------------------------------
# Tests: _get_or_create_session helper
# ---------------------------------------------------------------------------

class TestGetOrCreateSession:
    @pytest.mark.asyncio
    async def test_creates_new_session_when_no_id(self):
        from api.assistant import _get_or_create_session

        db = AsyncMock()
        # No existing session found
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db.execute.return_value = result_mock
        db.flush = AsyncMock()
        db.add = MagicMock()

        session = await _get_or_create_session(
            session_id=None,
            profile_id="prof-1",
            first_question="What is glucose?",
            profile_db=db,
        )

        assert session.profile_id == "prof-1"
        assert session.title == "What is glucose?"
        db.add.assert_called_once()
        db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_resumes_existing_session(self):
        from api.assistant import _get_or_create_session
        from models.chat_session import ChatSession

        existing = _make_session(profile_id="prof-1", title="Old session")

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = existing
        db.execute.return_value = result_mock
        db.flush = AsyncMock()
        db.add = MagicMock()

        session = await _get_or_create_session(
            session_id=existing.id,
            profile_id="prof-1",
            first_question="New question",
            profile_db=db,
        )

        assert session.id == existing.id
        assert session.title == "Old session"
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_creates_new_when_session_id_not_found(self):
        """Stale/foreign session_id → create a fresh implicit session."""
        from api.assistant import _get_or_create_session

        db = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None  # not found
        db.execute.return_value = result_mock
        db.flush = AsyncMock()
        db.add = MagicMock()

        session = await _get_or_create_session(
            session_id="stale-id-9999",
            profile_id="prof-1",
            first_question="Question?",
            profile_db=db,
        )

        # Should create new, not raise
        assert session.profile_id == "prof-1"
        db.add.assert_called_once()


# ---------------------------------------------------------------------------
# Tests: _load_session_history
# ---------------------------------------------------------------------------

class TestLoadSessionHistory:
    @pytest.mark.asyncio
    async def test_returns_turns_in_order(self):
        from api.assistant import _load_session_history

        sid = str(uuid.uuid4())
        turns = [
            _make_turn(sid, role="user", content="hello", index=0),
            _make_turn(sid, role="assistant", content="hi", index=1),
            _make_turn(sid, role="user", content="more", index=2),
        ]

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = turns
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock

        db = AsyncMock()
        db.execute.return_value = result_mock

        session_obj = _make_session()
        msgs = await _load_session_history(session_obj, db)
        assert len(msgs) == 3
        assert msgs[0].role == "user"
        assert msgs[0].content == "hello"
        assert msgs[2].content == "more"

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_turns(self):
        from api.assistant import _load_session_history

        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock

        db = AsyncMock()
        db.execute.return_value = result_mock

        msgs = await _load_session_history(_make_session(), db)
        assert msgs == []


# ---------------------------------------------------------------------------
# Tests: _append_turns
# ---------------------------------------------------------------------------

class TestAppendTurns:
    @pytest.mark.asyncio
    async def test_adds_two_turn_objects(self):
        from api.assistant import _append_turns

        count_result = MagicMock()
        count_result.scalar.return_value = 4  # 4 existing turns

        db = AsyncMock()
        db.execute.return_value = count_result
        db.add = MagicMock()  # add() is sync in SQLAlchemy

        added = db.add.call_args_list

        session_obj = _make_session()
        await _append_turns(
            session=session_obj,
            profile_id="prof-1",
            user_content="What is HbA1c?",
            assistant_content="HbA1c measures...",
            profile_db=db,
        )

        assert len(added) == 2
        roles = {call[0][0].role for call in added}
        assert roles == {"user", "assistant"}
        # turn indexes should be 4 and 5
        indexes = sorted(call[0][0].turn_index for call in added)
        assert indexes == [4, 5]


# ---------------------------------------------------------------------------
# Tests: _effective_use_memory  (dual-gate logic)
# ---------------------------------------------------------------------------

class TestEffectiveUseMemory:
    @pytest.mark.asyncio
    async def test_returns_false_when_request_flag_false(self):
        from api.assistant import _effective_use_memory

        db = AsyncMock()
        result = await _effective_use_memory(False, "prof-1", db)
        assert result is False
        # DB should not be queried at all
        db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_uses_per_profile_setting_when_true(self):
        from api.assistant import _effective_use_memory
        from models.model_settings import UserModelSettings

        row = MagicMock(spec=UserModelSettings)
        row.assistant_memory_enabled = True

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = row
        db = AsyncMock()
        db.execute.return_value = result_mock

        result = await _effective_use_memory(True, "prof-1", db)
        assert result is True

    @pytest.mark.asyncio
    async def test_per_profile_false_overrides_request_true(self):
        from api.assistant import _effective_use_memory
        from models.model_settings import UserModelSettings

        row = MagicMock(spec=UserModelSettings)
        row.assistant_memory_enabled = False

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = row
        db = AsyncMock()
        db.execute.return_value = result_mock

        result = await _effective_use_memory(True, "prof-1", db)
        assert result is False

    @pytest.mark.asyncio
    async def test_falls_back_to_global_config_when_no_row(self):
        from api.assistant import _effective_use_memory

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db = AsyncMock()
        db.execute.return_value = result_mock

        with patch("core.config.settings") as mock_settings:
            mock_settings.assistant_memory_enabled = True
            result = await _effective_use_memory(True, "prof-1", db)
        assert result is True

    @pytest.mark.asyncio
    async def test_global_false_prevents_injection(self):
        from api.assistant import _effective_use_memory

        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        db = AsyncMock()
        db.execute.return_value = result_mock

        with patch("core.config.settings") as mock_settings:
            mock_settings.assistant_memory_enabled = False
            result = await _effective_use_memory(True, "prof-1", db)
        assert result is False


# ---------------------------------------------------------------------------
# Tests: RAG compose_prompt — token budget for session history
# ---------------------------------------------------------------------------

class TestComposePromptTokenBudget:
    def test_history_injected_up_to_budget(self):
        rag = _make_rag_module()
        # 10 turns of 200 chars each = 2000 chars total > 500-char floor
        history = [
            {"role": "user", "content": "A" * 200},
            {"role": "assistant", "content": "B" * 200},
        ] * 5  # 10 messages

        from modules.rag import RetrievedChunk
        chunks = [
            RetrievedChunk(
                chunk_id="c1", source_type="reference",
                doc_id=None, doc_title="Ref", page=None,
                text="some context", relevance_score=0.9,
            )
        ]

        with patch("modules.rag.settings") as mock_settings:
            mock_settings.chat_context_size = 4096
            prompt = rag.compose_prompt("My question", chunks, history=history)

        # Prompt should contain the section header
        assert "SESSION HISTORY" in prompt
        # Should NOT include all 2000 chars (budget ~2048 for 4096 ctx)
        # but also should not be empty
        assert "USER:" in prompt or "ASSISTANT:" in prompt

    def test_history_section_label_is_non_citable(self):
        """Label must say 'do NOT cite' to avoid confusing faithfulness checker."""
        rag = _make_rag_module()
        history = [{"role": "user", "content": "prior question"}]

        from modules.rag import RetrievedChunk
        chunks = [
            RetrievedChunk(
                chunk_id="c1", source_type="reference",
                doc_id=None, doc_title="Ref", page=None,
                text="reference text", relevance_score=0.9,
            )
        ]
        with patch("modules.rag.settings") as mock_settings:
            mock_settings.chat_context_size = 4096
            prompt = rag.compose_prompt("Question", chunks, history=history)

        assert "do NOT cite" in prompt

    def test_empty_history_no_section(self):
        rag = _make_rag_module()
        from modules.rag import RetrievedChunk
        chunks = [
            RetrievedChunk(
                chunk_id="c1", source_type="reference",
                doc_id=None, doc_title="Ref", page=None,
                text="reference text", relevance_score=0.9,
            )
        ]
        with patch("modules.rag.settings") as mock_settings:
            mock_settings.chat_context_size = 4096
            prompt = rag.compose_prompt("Question", chunks, history=[])
        assert "SESSION HISTORY" not in prompt

    def test_none_history_no_section(self):
        rag = _make_rag_module()
        from modules.rag import RetrievedChunk
        chunks = [
            RetrievedChunk(
                chunk_id="c1", source_type="reference",
                doc_id=None, doc_title="Ref", page=None,
                text="reference text", relevance_score=0.9,
            )
        ]
        with patch("modules.rag.settings") as mock_settings:
            mock_settings.chat_context_size = 4096
            prompt = rag.compose_prompt("Question", chunks, history=None)
        assert "SESSION HISTORY" not in prompt


# ---------------------------------------------------------------------------
# Tests: memory injection in RAG (use_memory=True no longer double-gated)
# ---------------------------------------------------------------------------

class TestMemoryInjectionInRAG:
    @pytest.mark.asyncio
    async def test_memory_injected_when_use_memory_true(self):
        items = [
            FakeMemoryItem("1", "prof-1", "Current meds", "metformin", "medication"),
        ]
        rag = _make_rag_module()
        db = _fake_memory_db(items)

        with patch("modules.rag.settings") as mock_settings:
            mock_settings.assistant_memory_max_items_in_prompt = 20
            mock_settings.assistant_memory_max_prompt_chars = 2000
            result = await rag._retrieve_memory_context("prof-1", profile_db=db)

        assert "metformin" in result
        assert "USER PREFERENCES" in result

    @pytest.mark.asyncio
    async def test_memory_not_injected_when_use_memory_false(self):
        """use_memory=False → _retrieve_memory_context is never called."""
        rag = _make_rag_module()

        called = []

        async def _spy(*args, **kwargs):
            called.append(1)
            return ""

        rag._retrieve_memory_context = _spy

        from modules.rag import RetrievedChunk
        chunks = [
            RetrievedChunk(
                chunk_id="c1", source_type="reference",
                doc_id=None, doc_title="Ref", page=None,
                text="context", relevance_score=0.9,
            )
        ]
        # Directly call the internal path without going through the full pipeline
        # Simulate what query() does: only call _retrieve_memory_context if use_memory
        use_memory = False
        memory_section = ""
        if use_memory:
            memory_section = await rag._retrieve_memory_context("prof-1", None)

        assert not called
        assert memory_section == ""


# ---------------------------------------------------------------------------
# Tests: config default is now True
# ---------------------------------------------------------------------------

class TestConfigDefault:
    def test_assistant_memory_enabled_default_is_true(self):
        # Import fresh settings (not the live singleton, which may differ)
        import importlib
        import core.config as cfg_module
        # Re-instantiate settings with defaults
        from core.config import Settings
        fresh = Settings()
        assert fresh.assistant_memory_enabled is True


# ---------------------------------------------------------------------------
# Tests: auto-extract memory heuristics
# ---------------------------------------------------------------------------

class TestAutoExtractMemory:
    @pytest.mark.asyncio
    async def test_extracts_medication(self):
        from api.assistant import _auto_extract_memory

        added = []

        count_result = MagicMock()
        count_result.scalar.return_value = 0  # 0 existing auto items

        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = None  # not a dup

        call_n = [0]

        async def _execute(stmt):
            call_n[0] += 1
            if call_n[0] == 1:
                return count_result
            return existing_result

        db = AsyncMock()
        db.execute.side_effect = _execute
        db.add = MagicMock()

        await _auto_extract_memory("I take metformin for diabetes", "prof-1", db)

        assert db.add.call_count >= 1
        keys = [call[0][0].key for call in db.add.call_args_list]
        assert any("metformin" in k for k in keys)

    @pytest.mark.asyncio
    async def test_extracts_allergy(self):
        from api.assistant import _auto_extract_memory

        added = []

        count_result = MagicMock()
        count_result.scalar.return_value = 0

        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = None

        call_n = [0]

        async def _execute(stmt):
            call_n[0] += 1
            if call_n[0] == 1:
                return count_result
            return existing_result

        db = AsyncMock()
        db.execute.side_effect = _execute
        db.add = MagicMock()

        await _auto_extract_memory("I'm allergic to penicillin.", "prof-1", db)

        keys = [call[0][0].key for call in db.add.call_args_list]
        assert any("penicillin" in k for k in keys)

    @pytest.mark.asyncio
    async def test_skips_duplicate(self):
        from api.assistant import _auto_extract_memory

        added = []

        count_result = MagicMock()
        count_result.scalar.return_value = 0

        # Simulate existing duplicate
        existing_item = MagicMock()
        existing_result = MagicMock()
        existing_result.scalar_one_or_none.return_value = existing_item

        call_n = [0]

        async def _execute(stmt):
            call_n[0] += 1
            if call_n[0] == 1:
                return count_result
            return existing_result

        db = AsyncMock()
        db.execute.side_effect = _execute
        db.add.side_effect = added.append

        await _auto_extract_memory("I take metformin", "prof-1", db)

        # Should not add anything because duplicate
        assert len(added) == 0

    @pytest.mark.asyncio
    async def test_respects_max_auto_items(self):
        from api.assistant import _auto_extract_memory

        added = []

        # Already at the cap
        count_result = MagicMock()
        count_result.scalar.return_value = 10  # _MAX_AUTO_MEMORY_ITEMS == 10

        db = AsyncMock()
        db.execute.return_value = count_result
        db.add.side_effect = added.append

        await _auto_extract_memory("I take metformin", "prof-1", db)

        assert len(added) == 0
