"""
Tests for ASSIST-MEM-003: Memory Store RAG Integration.

Verifies that user memory items are correctly injected into RAG context
when the feature is enabled, and excluded when disabled.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass


@dataclass(frozen=True)
class FakeMemoryItem:
    """Lightweight stand-in for models.memory_item.MemoryItem."""
    id: str
    profile_id: str
    key: str
    value: str
    category: str | None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_rag_module():
    """Construct a RAGModule with mocked heavy deps."""
    with (
        patch("modules.rag.get_model_runner") as mock_runner,
        patch("modules.rag.EmbeddingsModule"),
    ):
        mock_runner.return_value = MagicMock(is_available=MagicMock(return_value=True))
        from modules.rag import RAGModule
        return RAGModule(enable_verification=False)


def _fake_profile_db(items: list[FakeMemoryItem]):
    """Return a mock async db session that yields *items* from a SELECT."""
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = items

    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock

    db = AsyncMock()
    db.execute.return_value = result_mock
    return db


# ---------------------------------------------------------------------------
# Tests — _retrieve_memory_context
# ---------------------------------------------------------------------------

class TestRetrieveMemoryContext:
    """Unit tests for RAGModule._retrieve_memory_context."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_profile_db(self):
        rag = _make_rag_module()
        result = await rag._retrieve_memory_context("prof-1", profile_db=None)
        assert result == ""

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_items(self):
        rag = _make_rag_module()
        db = _fake_profile_db([])
        result = await rag._retrieve_memory_context("prof-1", profile_db=db)
        assert result == ""

    @pytest.mark.asyncio
    async def test_formats_items_with_category(self):
        items = [
            FakeMemoryItem("1", "prof-1", "Preferred units", "metric", "preferences"),
        ]
        rag = _make_rag_module()
        db = _fake_profile_db(items)
        result = await rag._retrieve_memory_context("prof-1", profile_db=db)
        assert "Preferred units [preferences]: metric" in result
        assert "USER PREFERENCES" in result

    @pytest.mark.asyncio
    async def test_formats_items_without_category(self):
        items = [
            FakeMemoryItem("2", "prof-1", "Allergies", "penicillin", None),
        ]
        rag = _make_rag_module()
        db = _fake_profile_db(items)
        result = await rag._retrieve_memory_context("prof-1", profile_db=db)
        assert "- Allergies: penicillin" in result
        # No brackets when category is None
        assert "[]" not in result

    @pytest.mark.asyncio
    async def test_multiple_items_joined(self):
        items = [
            FakeMemoryItem("1", "prof-1", "Units", "metric", "prefs"),
            FakeMemoryItem("2", "prof-1", "Language", "en", "prefs"),
        ]
        rag = _make_rag_module()
        db = _fake_profile_db(items)
        result = await rag._retrieve_memory_context("prof-1", profile_db=db)
        assert "Units [prefs]: metric" in result
        assert "Language [prefs]: en" in result

    @pytest.mark.asyncio
    async def test_gracefully_handles_db_error(self):
        rag = _make_rag_module()
        db = AsyncMock()
        db.execute.side_effect = RuntimeError("DB gone")
        result = await rag._retrieve_memory_context("prof-1", profile_db=db)
        assert result == ""


# ---------------------------------------------------------------------------
# Tests — query() memory integration
# ---------------------------------------------------------------------------

class TestQueryMemoryIntegration:
    """Integration-level tests ensuring memory flows through query()."""

    @pytest.mark.asyncio
    async def test_memory_excluded_when_disabled(self):
        """When assistant_memory_enabled=False, no memory section appears."""
        rag = _make_rag_module()

        with patch.object(rag, "retrieve_context", new_callable=AsyncMock, return_value=[]):
            result = await rag.query(
                question="What is my hemoglobin?",
                profile_id="prof-1",
                use_memory=True,  # requested but config disabled
            )
        # Insufficient context branch — no memory was queried
        assert result.insufficient_context is True

    @pytest.mark.asyncio
    async def test_memory_excluded_when_not_requested(self):
        """When use_memory=False (default), _retrieve_memory_context is never called."""
        rag = _make_rag_module()

        with (
            patch.object(rag, "retrieve_context", new_callable=AsyncMock, return_value=[]),
            patch.object(rag, "_retrieve_memory_context", new_callable=AsyncMock) as mem_mock,
        ):
            await rag.query(
                question="What is my hemoglobin?",
                profile_id="prof-1",
                use_memory=False,
            )
        mem_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_memory_injected_when_enabled(self):
        """When both config and request flag are on, memory appears in prompt."""
        rag = _make_rag_module()

        fake_chunk = MagicMock(
            chunk_id="c1", source_type="user_document", doc_id="d1",
            doc_title="Report", page=1, text="HGB 14.2",
            relevance_score=0.9, is_user_verified=True,
            is_peer_reviewed=False, publisher=None,
        )

        with (
            patch.object(rag, "retrieve_context", new_callable=AsyncMock, return_value=[fake_chunk]),
            patch.object(
                rag, "_retrieve_memory_context", new_callable=AsyncMock,
                return_value="\nUSER PREFERENCES:\n- Units: metric\n",
            ),
            patch.object(rag, "_generate_with_runner", new_callable=AsyncMock, return_value="REPORT FACTS: HGB is 14.2 [cite:1]"),
            patch("modules.rag.settings") as mock_settings,
        ):
            mock_settings.assistant_memory_enabled = True
            result = await rag.query(
                question="What is my hemoglobin?",
                profile_id="prof-1",
                use_memory=True,
            )
        # Should get a valid response (not insufficient context)
        assert result.insufficient_context is False

    @pytest.mark.asyncio
    async def test_empty_memory_store_produces_no_extra_context(self):
        """When memory store is empty, prompt is unchanged."""
        rag = _make_rag_module()

        fake_chunk = MagicMock(
            chunk_id="c1", source_type="user_document", doc_id="d1",
            doc_title="Report", page=1, text="HGB 14.2",
            relevance_score=0.9, is_user_verified=True,
            is_peer_reviewed=False, publisher=None,
        )

        original_compose = rag.compose_prompt

        captured_prompts = []

        def spy_compose(*args, **kwargs):
            result = original_compose(*args, **kwargs)
            captured_prompts.append(result)
            return result

        with (
            patch.object(rag, "retrieve_context", new_callable=AsyncMock, return_value=[fake_chunk]),
            patch.object(
                rag, "_retrieve_memory_context", new_callable=AsyncMock,
                return_value="",  # empty store
            ),
            patch.object(rag, "compose_prompt", side_effect=spy_compose),
            patch.object(rag, "_generate_with_runner", new_callable=AsyncMock, return_value="REPORT FACTS: HGB is 14.2 [cite:1]"),
            patch("modules.rag.settings") as mock_settings,
        ):
            mock_settings.assistant_memory_enabled = True
            await rag.query(
                question="What is my hemoglobin?",
                profile_id="prof-1",
                use_memory=True,
            )

        # The prompt should NOT contain USER PREFERENCES
        assert captured_prompts
        assert "USER PREFERENCES" not in captured_prompts[0]
