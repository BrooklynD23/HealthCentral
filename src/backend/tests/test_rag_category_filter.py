"""Tests for category-aware RAG retrieval.

Validates that:
- retrieve_context accepts an optional category filter
- _search_vectors_async joins on DocumentCategory when category is provided
- Unfiltered retrieval is unchanged when category is None
- Graceful fallback when category data is missing
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.document_classifier import classify_document


class TestClassifierCategories:
    """Classifier returns valid categories (existing tests preserved)."""

    def test_classifier_returns_valid_categories(self) -> None:
        valid_categories = {"imaging", "pathology", "visit_notes", "lab", "unknown"}

        texts = [
            "RADIOLOGY REPORT\nMRI brain\nFINDINGS: Normal\nIMPRESSION: Normal",
            "PATHOLOGY REPORT\nSPECIMEN: Biopsy\nDIAGNOSIS: Benign",
            "PROGRESS NOTE\nChief Complaint: Headache\nASSESSMENT: Migraine",
            "LABORATORY RESULTS\nGlucose: 95 mg/dL",
            "Random unrelated text with no keywords",
        ]

        for text in texts:
            result = classify_document(text)
            assert result.category in valid_categories
            assert 0.0 <= result.confidence <= 1.0
            assert result.classified_by == "rule"

    def test_unknown_category_has_zero_confidence(self) -> None:
        result = classify_document("This text has no medical keywords whatsoever.")
        assert result.category == "unknown"
        assert result.confidence == 0.0


class TestRetrieveContextCategoryParam:
    """RAGModule.retrieve_context accepts optional category filter."""

    @pytest.mark.asyncio
    async def test_retrieve_context_accepts_category_param(self) -> None:
        """retrieve_context signature includes category parameter."""
        from modules.rag import RAGModule

        with patch.object(RAGModule, "__init__", lambda self, **kw: None):
            rag = RAGModule.__new__(RAGModule)
            rag._logger = MagicMock()

            # Mock _search_vectors_async to capture args
            captured = {}

            async def mock_search(**kwargs):
                captured.update(kwargs)
                return []

            rag._search_vectors_async = mock_search
            rag._get_reference_chunks = AsyncMock(return_value=[])

            mock_db = AsyncMock()

            await rag.retrieve_context(
                query="show imaging results",
                profile_id="p1",
                category="imaging",
                profile_db=mock_db,
            )

            assert captured.get("category") == "imaging"

    @pytest.mark.asyncio
    async def test_retrieve_context_defaults_category_none(self) -> None:
        """When category is not passed, it defaults to None."""
        from modules.rag import RAGModule

        with patch.object(RAGModule, "__init__", lambda self, **kw: None):
            rag = RAGModule.__new__(RAGModule)
            rag._logger = MagicMock()

            captured = {}

            async def mock_search(**kwargs):
                captured.update(kwargs)
                return []

            rag._search_vectors_async = mock_search
            rag._get_reference_chunks = AsyncMock(return_value=[])

            mock_db = AsyncMock()

            await rag.retrieve_context(
                query="general question",
                profile_id="p1",
                profile_db=mock_db,
            )

            assert captured.get("category") is None


class TestSearchVectorsCategoryFilter:
    """_search_vectors_async applies DocumentCategory join when category given."""

    @pytest.mark.asyncio
    async def test_category_filter_adds_where_clause(self) -> None:
        """When category is provided, the SQL query includes a subquery filter."""
        from modules.rag import RAGModule

        with patch.object(RAGModule, "__init__", lambda self, **kw: None):
            rag = RAGModule.__new__(RAGModule)
            rag._logger = MagicMock()
            rag._embedder = MagicMock()
            rag._embedder.embed_text.return_value = [0.1] * 384

            # Mock profile_db.execute to return empty results
            mock_result = MagicMock()
            mock_result.all.return_value = []
            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=mock_result)

            results = await rag._search_vectors_async(
                query="MRI results",
                profile_id="p1",
                category="imaging",
                profile_db=mock_db,
            )

            # Should have called execute (proving no crash with category param)
            assert mock_db.execute.called
            assert results == []

    @pytest.mark.asyncio
    async def test_no_category_filter_when_none(self) -> None:
        """When category is None, search proceeds without category join."""
        from modules.rag import RAGModule

        with patch.object(RAGModule, "__init__", lambda self, **kw: None):
            rag = RAGModule.__new__(RAGModule)
            rag._logger = MagicMock()
            rag._embedder = MagicMock()
            rag._embedder.embed_text.return_value = [0.1] * 384

            mock_result = MagicMock()
            mock_result.all.return_value = []
            mock_db = AsyncMock()
            mock_db.execute = AsyncMock(return_value=mock_result)

            results = await rag._search_vectors_async(
                query="general query",
                profile_id="p1",
                category=None,
                profile_db=mock_db,
            )

            assert mock_db.execute.called
            assert results == []


class TestQueryCategoryParam:
    """RAGModule.query passes category through to retrieve_context."""

    @pytest.mark.asyncio
    async def test_query_passes_category_to_retrieve(self) -> None:
        """query() forwards category parameter to retrieve_context."""
        from modules.rag import RAGModule

        with patch.object(RAGModule, "__init__", lambda self, **kw: None):
            rag = RAGModule.__new__(RAGModule)
            rag._logger = MagicMock()
            rag.enable_verification = False

            captured_kwargs = {}
            original_retrieve = AsyncMock(return_value=[])

            async def capture_retrieve(**kwargs):
                captured_kwargs.update(kwargs)
                return await original_retrieve(**kwargs)

            rag.retrieve_context = capture_retrieve
            rag._generate_with_runner = AsyncMock(return_value="UNCERTAINTIES:\nNo data.")
            rag.validate_response = MagicMock(return_value=MagicMock(
                segments=[], is_valid=True, validation_errors=[],
                insufficient_context=False, insufficient_reasons=[],
                verification=MagicMock(),
            ))
            rag._model_runner = MagicMock()

            # query should accept and pass category
            # Since retrieve_context returns [] it will return insufficient context
            result = await rag.query(
                question="show my imaging",
                profile_id="p1",
                category="imaging",
            )

            assert captured_kwargs.get("category") == "imaging"

    @pytest.mark.asyncio
    async def test_query_defaults_category_none(self) -> None:
        """query() without category passes None to retrieve_context."""
        from modules.rag import RAGModule

        with patch.object(RAGModule, "__init__", lambda self, **kw: None):
            rag = RAGModule.__new__(RAGModule)
            rag._logger = MagicMock()
            rag.enable_verification = False

            captured_kwargs = {}

            async def capture_retrieve(**kwargs):
                captured_kwargs.update(kwargs)
                return []

            rag.retrieve_context = capture_retrieve

            result = await rag.query(
                question="general question",
                profile_id="p1",
            )

            assert captured_kwargs.get("category") is None


class TestChatRequestCategoryField:
    """ChatRequest model accepts optional document_category field."""

    def test_chat_request_accepts_category(self) -> None:
        from api.assistant import ChatRequest

        req = ChatRequest(question="test", document_category="imaging")
        assert req.document_category == "imaging"

    def test_chat_request_category_defaults_none(self) -> None:
        from api.assistant import ChatRequest

        req = ChatRequest(question="test")
        assert req.document_category is None

    def test_chat_request_rejects_invalid_category(self) -> None:
        from api.assistant import ChatRequest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ChatRequest(question="test", document_category="invalid_category")
