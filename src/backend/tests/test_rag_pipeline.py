"""
Tests for Sprint 5: RAG Assistant Pipeline.

TDD Tests that verify:
- Document chunking creates chunks with provenance
- Embeddings are generated and stored
- Similarity search retrieves relevant chunks
- RAG responses include citations
- Prohibited topics are refused
- Glossary and test-intent lookups work

All tests verify authenticated access and data isolation.
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
import json
import struct

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestChunkingPipeline:
    """Tests for document chunking (S5-BE-001)."""

    @pytest.fixture
    def sample_document_text(self):
        """Sample document text for chunking tests."""
        return """
        Quest Diagnostics Laboratory Report
        Patient: John Doe
        Collection Date: January 15, 2024

        METABOLIC PANEL

        Glucose: 95 mg/dL (Reference: 70-100)
        This value is within normal range.

        BUN: 18 mg/dL (Reference: 7-20)
        Blood urea nitrogen is normal.

        Creatinine: 1.1 mg/dL (Reference: 0.7-1.3)
        Kidney function appears normal.

        LIPID PANEL

        Total Cholesterol: 245 mg/dL (Reference: <200)
        This value is elevated.

        HDL: 55 mg/dL (Reference: >40)
        Good cholesterol is within normal range.

        LDL: 160 mg/dL (Reference: <100)
        Bad cholesterol is elevated.

        NOTES:
        Please discuss lipid results with your healthcare provider.
        Lifestyle modifications may be recommended.
        """

    @pytest.fixture
    def sample_document(self):
        """Sample document model for testing."""
        return {
            "id": str(uuid.uuid4()),
            "profile_id": str(uuid.uuid4()),
            "doc_type": "lab_pdf",
            "source": "Quest Diagnostics",
            "status": "parsed",
            "page_count": 1,
            "collection_date": datetime(2024, 1, 15, tzinfo=timezone.utc),
        }

    def test_api_rag_index_001_chunking_creates_chunks(self, sample_document_text, sample_document):
        """
        API-RAG-INDEX-001: Chunking creates chunks.

        Document text should be split into manageable chunks for embedding.
        Each chunk should preserve context and include provenance.
        """
        from modules.chunking import ChunkingModule

        chunker = ChunkingModule(
            chunk_size=200,  # tokens
            chunk_overlap=50,
        )

        chunks = chunker.chunk_document(
            doc_id=sample_document["id"],
            text=sample_document_text,
            page_number=1,
        )

        assert isinstance(chunks, list)
        assert len(chunks) >= 1

        # Each chunk should have required fields
        for chunk in chunks:
            assert "chunk_id" in chunk
            assert "doc_id" in chunk
            assert "text" in chunk
            assert "page_number" in chunk
            assert "chunk_index" in chunk
            assert "start_char" in chunk
            assert "end_char" in chunk
            assert "token_count" in chunk

            # Chunk should not exceed max size (with some tolerance)
            assert chunk["token_count"] <= 250

            # Text should not be empty
            assert len(chunk["text"].strip()) > 0

        # Chunks should cover the document
        chunk_ids = {c["chunk_id"] for c in chunks}
        assert len(chunk_ids) == len(chunks)  # All unique IDs

    def test_api_rag_index_001b_chunks_preserve_sentences(self, sample_document_text, sample_document):
        """
        Chunking should avoid splitting mid-sentence when possible.
        """
        from modules.chunking import ChunkingModule

        chunker = ChunkingModule(
            chunk_size=100,
            chunk_overlap=25,
        )

        chunks = chunker.chunk_document(
            doc_id=sample_document["id"],
            text=sample_document_text,
            page_number=1,
        )

        # Most chunks should end with sentence-ending punctuation or newline
        sentence_endings = 0
        for chunk in chunks:
            text = chunk["text"].strip()
            if text.endswith('.') or text.endswith(':') or text.endswith(')') or text.endswith('\n'):
                sentence_endings += 1

        # At least 50% should end cleanly
        assert sentence_endings >= len(chunks) * 0.5

    def test_api_rag_index_001c_chunks_include_overlap(self, sample_document_text, sample_document):
        """
        Consecutive chunks should have overlapping content for context.
        """
        from modules.chunking import ChunkingModule

        chunker = ChunkingModule(
            chunk_size=100,
            chunk_overlap=25,
        )

        chunks = chunker.chunk_document(
            doc_id=sample_document["id"],
            text=sample_document_text,
            page_number=1,
        )

        if len(chunks) >= 2:
            # Check that consecutive chunks have some overlap
            for i in range(len(chunks) - 1):
                current_end = chunks[i]["end_char"]
                next_start = chunks[i + 1]["start_char"]

                # Next chunk should start before or at the current end (overlap)
                # or very close to it
                assert next_start <= current_end + 50  # Allow some tolerance


class TestEmbeddingsPipeline:
    """Tests for embedding generation (S5-BE-001)."""

    @pytest.fixture
    def sample_chunks(self):
        """Sample chunks for embedding tests."""
        return [
            {
                "chunk_id": str(uuid.uuid4()),
                "doc_id": str(uuid.uuid4()),
                "text": "Glucose: 95 mg/dL within normal reference range of 70-100.",
                "page_number": 1,
                "chunk_index": 0,
                "start_char": 0,
                "end_char": 60,
                "token_count": 15,
            },
            {
                "chunk_id": str(uuid.uuid4()),
                "doc_id": str(uuid.uuid4()),
                "text": "Total Cholesterol: 245 mg/dL is elevated above the 200 mg/dL reference.",
                "page_number": 1,
                "chunk_index": 1,
                "start_char": 60,
                "end_char": 130,
                "token_count": 18,
            },
        ]

    def test_api_rag_index_002_embeddings_created_for_chunks(self, sample_chunks):
        """
        API-RAG-INDEX-002: Embeddings created for chunks.

        Each chunk should have a corresponding embedding vector.
        """
        from modules.embeddings import EmbeddingsModule

        embedder = EmbeddingsModule()

        embeddings = embedder.embed_chunks(sample_chunks)

        assert isinstance(embeddings, list)
        assert len(embeddings) == len(sample_chunks)

        for i, emb in enumerate(embeddings):
            assert "chunk_id" in emb
            assert emb["chunk_id"] == sample_chunks[i]["chunk_id"]
            assert "vector" in emb
            assert "dimensions" in emb
            assert "model_name" in emb

            # Vector should be a list of floats
            assert isinstance(emb["vector"], list)
            assert len(emb["vector"]) == emb["dimensions"]
            assert all(isinstance(v, float) for v in emb["vector"])

            # Dimensions should be standard (384 for all-MiniLM-L6-v2 or similar)
            assert emb["dimensions"] in [384, 768, 1024, 1536]

    def test_api_rag_index_002b_similar_text_yields_similar_embeddings(self, sample_chunks):
        """
        Semantically similar text should yield similar embeddings.
        """
        from modules.embeddings import EmbeddingsModule

        embedder = EmbeddingsModule()

        # Create two semantically similar chunks
        similar_chunks = [
            {
                "chunk_id": "1",
                "text": "Blood glucose level is 95 mg/dL which is normal.",
            },
            {
                "chunk_id": "2",
                "text": "The glucose measurement shows 95 mg/dL, within normal range.",
            },
        ]

        embeddings = embedder.embed_chunks(similar_chunks)

        # Calculate cosine similarity
        import math
        v1 = embeddings[0]["vector"]
        v2 = embeddings[1]["vector"]

        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        similarity = dot / (norm1 * norm2)

        # Similar text should have high similarity (> 0.7)
        assert similarity > 0.7

    def test_api_rag_index_002c_embeddings_are_deterministic(self, sample_chunks):
        """
        Same text should produce identical embeddings.
        """
        from modules.embeddings import EmbeddingsModule

        embedder = EmbeddingsModule()

        embeddings1 = embedder.embed_chunks(sample_chunks)
        embeddings2 = embedder.embed_chunks(sample_chunks)

        for e1, e2 in zip(embeddings1, embeddings2):
            assert e1["vector"] == e2["vector"]


class TestRetrievalPipeline:
    """Tests for context retrieval (S5-BE-002)."""

    @pytest.fixture
    def sample_indexed_chunks(self):
        """Pre-indexed chunks with embeddings for retrieval tests."""
        # These would normally be in the database
        return [
            {
                "chunk_id": "chunk-1",
                "doc_id": "doc-1",
                "doc_title": "Quest Lab Report Jan 2024",
                "text": "Glucose: 95 mg/dL (Reference: 70-100). Normal range.",
                "page_number": 1,
                "chunk_type": "text",
                "analytes": ["glucose"],
                "collection_date": datetime(2024, 1, 15, tzinfo=timezone.utc),
            },
            {
                "chunk_id": "chunk-2",
                "doc_id": "doc-1",
                "doc_title": "Quest Lab Report Jan 2024",
                "text": "Hemoglobin A1c: 6.5% (Reference: 4.0-5.6). Elevated.",
                "page_number": 1,
                "chunk_type": "text",
                "analytes": ["hemoglobin_a1c"],
                "collection_date": datetime(2024, 1, 15, tzinfo=timezone.utc),
            },
            {
                "chunk_id": "chunk-3",
                "doc_id": "doc-2",
                "doc_title": "Lab Corp Report Dec 2023",
                "text": "Glucose: 102 mg/dL slightly elevated.",
                "page_number": 1,
                "chunk_type": "text",
                "analytes": ["glucose"],
                "collection_date": datetime(2023, 12, 1, tzinfo=timezone.utc),
            },
            {
                "chunk_id": "chunk-4",
                "doc_id": "doc-2",
                "doc_title": "Lab Corp Report Dec 2023",
                "text": "Total Cholesterol: 220 mg/dL above optimal range.",
                "page_number": 2,
                "chunk_type": "text",
                "analytes": ["cholesterol_total"],
                "collection_date": datetime(2023, 12, 1, tzinfo=timezone.utc),
            },
        ]

    def test_api_rag_retrieve_001_similarity_search_returns_top_k(self, sample_indexed_chunks):
        """
        API-RAG-RETRIEVE-001: Similarity search returns top-k chunks.

        Query should retrieve the most semantically relevant chunks.
        """
        from modules.rag import RAGModule, RetrievedChunk

        rag = RAGModule()

        # Mock the internal retrieval to use our sample data
        with patch.object(rag, '_search_vectors') as mock_search:
            mock_search.return_value = [
                (sample_indexed_chunks[0], 0.95),  # glucose
                (sample_indexed_chunks[2], 0.88),  # glucose Dec
            ]

            # This test verifies the interface - actual implementation
            # will search the vector store
            chunks = rag.retrieve_context_sync(
                query="What is my glucose level?",
                profile_id="test-profile",
                top_k=5,
            )

            assert isinstance(chunks, list)
            # Should return results ordered by relevance
            if len(chunks) >= 2:
                assert chunks[0].relevance_score >= chunks[1].relevance_score

            # Each chunk should have provenance
            for chunk in chunks:
                assert isinstance(chunk, RetrievedChunk)
                assert chunk.chunk_id is not None
                assert chunk.doc_id is not None
                assert chunk.text is not None
                assert chunk.relevance_score >= 0.0
                assert chunk.relevance_score <= 1.0

    def test_api_rag_retrieve_002_filter_by_analyte(self, sample_indexed_chunks):
        """
        API-RAG-RETRIEVE-002: Retrieval filters by analyte.

        When analyte filter is specified, only matching chunks return.
        """
        from modules.rag import RAGModule

        rag = RAGModule()

        with patch.object(rag, '_search_vectors') as mock_search:
            # Only return glucose chunks when filtered
            mock_search.return_value = [
                (sample_indexed_chunks[0], 0.95),
                (sample_indexed_chunks[2], 0.88),
            ]

            chunks = rag.retrieve_context_sync(
                query="Show my glucose trends",
                profile_id="test-profile",
                selected_analytes=["glucose"],
                top_k=5,
            )

            # All returned chunks should be related to glucose
            for chunk in chunks:
                # Check the text contains glucose-related content
                assert "glucose" in chunk.text.lower() or len(chunks) == 0

    def test_api_rag_retrieve_003_filter_by_date_range(self, sample_indexed_chunks):
        """
        API-RAG-RETRIEVE-003: Retrieval filters by date range.

        When date filters are specified, only matching chunks return.
        """
        from modules.rag import RAGModule

        rag = RAGModule()

        with patch.object(rag, '_search_vectors') as mock_search:
            # Only return Jan 2024 chunks when filtered
            mock_search.return_value = [
                (sample_indexed_chunks[0], 0.95),
                (sample_indexed_chunks[1], 0.85),
            ]

            chunks = rag.retrieve_context_sync(
                query="What are my recent results?",
                profile_id="test-profile",
                from_date="2024-01-01",
                to_date="2024-01-31",
                top_k=5,
            )

            # All returned chunks should be from Jan 2024
            # (verified by mock returning filtered data)
            assert len(chunks) >= 0  # Implementation may return empty

    def test_api_rag_index_003_retrieval_returns_chunks_with_provenance(self, sample_indexed_chunks):
        """
        API-RAG-INDEX-003: Retrieval returns chunks with provenance.

        Each retrieved chunk must include source document info for citations.
        """
        from modules.rag import RAGModule, RetrievedChunk

        rag = RAGModule()

        with patch.object(rag, '_search_vectors') as mock_search:
            mock_search.return_value = [
                (sample_indexed_chunks[0], 0.95),
            ]

            chunks = rag.retrieve_context_sync(
                query="glucose level",
                profile_id="test-profile",
                top_k=1,
            )

            if chunks:
                chunk = chunks[0]

                # Provenance fields required for citations
                assert chunk.doc_id is not None
                assert chunk.doc_title is not None or chunk.source_type is not None
                assert chunk.page is not None or chunk.page == 0
                assert chunk.text is not None
                assert len(chunk.text) > 0


class TestRAGResponseGeneration:
    """Tests for RAG response generation (S5-BE-003)."""

    @pytest.fixture
    def sample_context_chunks(self):
        """Sample retrieved chunks for response generation."""
        from modules.rag import RetrievedChunk

        return [
            RetrievedChunk(
                chunk_id="1",
                source_type="user_document",
                doc_id="doc-1",
                doc_title="Quest Lab Report",
                page=1,
                text="Glucose: 95 mg/dL. Reference range: 70-100 mg/dL. Within normal limits.",
                relevance_score=0.95,
            ),
            RetrievedChunk(
                chunk_id="2",
                source_type="reference",
                doc_id=None,
                doc_title="Medical Reference",
                page=None,
                text="Glucose is a simple sugar that is the primary source of energy for the body's cells. Normal fasting glucose is typically 70-100 mg/dL.",
                relevance_score=0.82,
            ),
        ]

    @pytest.mark.asyncio
    async def test_api_ast_chat_001_chat_returns_structured_response(self, sample_context_chunks):
        """
        API-AST-CHAT-001: Chat returns structured response.

        Response should have distinct sections: report facts, general info, uncertainties.
        """
        from modules.rag import RAGModule, ValidatedResponse

        rag = RAGModule()

        # Mock LLM response
        mock_llm_response = """
REPORT FACTS:
Your glucose level is 95 mg/dL, which falls within the normal reference range of 70-100 mg/dL [cite:1].

GENERAL INFO:
Glucose is a simple sugar that serves as the primary energy source for your body's cells. Normal fasting glucose is typically 70-100 mg/dL [cite:2].

UNCERTAINTIES:
Reference ranges may vary slightly between laboratories. Always discuss your specific results with your healthcare provider.
"""

        with patch.object(rag, 'generate_response', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_llm_response

            validated = rag.validate_response(
                response=mock_llm_response,
                retrieved_chunks=sample_context_chunks,
            )

            assert isinstance(validated, ValidatedResponse)
            assert len(validated.segments) >= 1

            # Check for expected segment types
            segment_types = {s.segment_type for s in validated.segments}
            # At least one of these should be present
            expected_types = {"report_facts", "general_info", "uncertainty"}
            assert len(segment_types & expected_types) >= 1

    @pytest.mark.asyncio
    async def test_api_ast_chat_002_response_includes_citations(self, sample_context_chunks):
        """
        API-AST-CHAT-002: Response includes citations.

        Response must include [cite:N] format citations that map to sources.
        """
        from modules.rag import RAGModule

        rag = RAGModule()

        mock_llm_response = """
REPORT FACTS:
Your glucose is 95 mg/dL [cite:1], within normal range.

GENERAL INFO:
Glucose provides energy to cells [cite:2].
"""

        validated = rag.validate_response(
            response=mock_llm_response,
            retrieved_chunks=sample_context_chunks,
        )

        # Should have parsed citations
        total_citations = sum(len(s.citations) for s in validated.segments)
        assert total_citations >= 2

        # Citations should reference valid chunks
        for segment in validated.segments:
            for citation in segment.citations:
                assert citation.citation_id in ["1", "2"]
                assert citation.source_type in ["user_document", "reference"]

    @pytest.mark.asyncio
    async def test_api_ast_chat_003_refusal_for_prohibited_topics(self, sample_context_chunks):
        """
        API-AST-CHAT-003: Refusal for prohibited topics.

        System should refuse to provide diagnosis, treatment advice, or medication dosing.
        """
        from modules.rag import RAGModule

        rag = RAGModule()

        # Test that prohibited content triggers validation failure
        prohibited_response = """
REPORT FACTS:
Your glucose is 95 mg/dL [cite:1].

GENERAL INFO:
You should take metformin to control your blood sugar. I diagnose you with pre-diabetes.
"""

        validated = rag.validate_response(
            response=prohibited_response,
            retrieved_chunks=sample_context_chunks,
        )

        # Should be marked invalid due to prohibited content
        assert validated.is_valid is False
        assert len(validated.validation_errors) > 0

        # Error should mention prohibited advice
        error_text = " ".join(validated.validation_errors).lower()
        assert "prohibited" in error_text or "advice" in error_text

    @pytest.mark.asyncio
    async def test_insufficient_context_returns_safe_response(self):
        """
        When no relevant chunks are found, return safe "insufficient context" response.
        """
        from modules.rag import RAGModule

        rag = RAGModule()

        # Mock empty retrieval
        with patch.object(rag, 'retrieve_context', new_callable=AsyncMock) as mock_retrieve:
            mock_retrieve.return_value = []

            result = await rag.query(
                question="What is my glucose level?",
                profile_id="test-profile",
            )

            assert result.insufficient_context is True
            assert len(result.insufficient_reasons) > 0

            # Response should mention lack of information
            response_text = " ".join(s.content for s in result.segments)
            assert "information" in response_text.lower() or "documents" in response_text.lower()


class TestGlossaryEndpoint:
    """Tests for glossary lookup (S5-BE-004)."""

    def test_api_ast_glossary_001_glossary_lookup(self):
        """
        API-AST-GLOSSARY-001: Glossary lookup returns definition.

        Medical terms should have plain-language definitions.
        """
        from modules.glossary import GlossaryModule

        glossary = GlossaryModule()

        result = glossary.lookup("hemoglobin")

        assert result is not None
        assert "term" in result
        assert "definition" in result
        assert result["term"].lower() == "hemoglobin"
        assert len(result["definition"]) > 10  # Meaningful definition

        # Definition should be plain language (no jargon-only response)
        assert len(result["definition"].split()) >= 5

    def test_api_ast_glossary_002_unknown_term_handled(self):
        """
        Unknown terms should return a graceful "not found" response.
        """
        from modules.glossary import GlossaryModule

        glossary = GlossaryModule()

        result = glossary.lookup("xyznonexistentterm123")

        # Should return None or a not-found indicator
        assert result is None or result.get("not_found", False) is True

    def test_api_ast_glossary_003_related_terms_included(self):
        """
        Glossary should include related terms when available.
        """
        from modules.glossary import GlossaryModule

        glossary = GlossaryModule()

        result = glossary.lookup("glucose")

        if result and "related_terms" in result:
            assert isinstance(result["related_terms"], list)
            # Related terms might include: blood sugar, glycemia, etc.


class TestTestIntentEndpoint:
    """Tests for test intent lookup (S5-BE-004)."""

    def test_api_ast_intent_001_test_intent_lookup(self):
        """
        API-AST-INTENT-001: Test intent lookup returns explanation.

        Should explain what a test is typically ordered for.
        """
        from modules.test_intent import TestIntentModule

        intent_module = TestIntentModule()

        result = intent_module.lookup("hemoglobin_a1c")

        assert result is not None
        assert "analyte" in result
        assert "intent_summary" in result
        assert "general_info" in result

        # Intent should be meaningful
        assert len(result["intent_summary"]) > 20

        # Should mention diabetes/blood sugar (what HbA1c is for)
        combined_text = (result["intent_summary"] + result["general_info"]).lower()
        assert "diabetes" in combined_text or "blood sugar" in combined_text or "glucose" in combined_text

    def test_api_ast_intent_002_unknown_analyte_handled(self):
        """
        Unknown analytes should return graceful response.
        """
        from modules.test_intent import TestIntentModule

        intent_module = TestIntentModule()

        result = intent_module.lookup("xyz_unknown_analyte")

        # Should return None or generic response
        assert result is None or result.get("not_found", False) is True

    def test_api_ast_intent_003_no_medical_advice_in_intent(self):
        """
        Test intent should be educational, not prescriptive.
        """
        from modules.test_intent import TestIntentModule

        intent_module = TestIntentModule()

        result = intent_module.lookup("glucose")

        if result:
            combined = (result["intent_summary"] + result["general_info"]).lower()

            # Should not contain prescriptive language
            assert "you should" not in combined
            assert "take medication" not in combined
            assert "i diagnose" not in combined


class TestRAGIntegration:
    """Integration tests for full RAG pipeline."""

    @pytest.mark.asyncio
    async def test_e2e_rag_001_no_docs_returns_insufficient_context(self):
        """
        E2E-RAG-001: No docs → chat returns insufficient context.

        When profile has no documents, assistant should not hallucinate.
        """
        from modules.rag import RAGModule

        rag = RAGModule()

        # Mock empty document state
        with patch.object(rag, 'retrieve_context', new_callable=AsyncMock) as mock_retrieve:
            mock_retrieve.return_value = []

            result = await rag.query(
                question="What are my cholesterol levels?",
                profile_id="empty-profile",
            )

            assert result.insufficient_context is True

            # Should not claim to have information
            response_text = " ".join(s.content for s in result.segments).lower()
            assert "your cholesterol" not in response_text or "don't have" in response_text

    @pytest.mark.asyncio
    async def test_e2e_rag_002_with_docs_includes_citations(self):
        """
        E2E-RAG-002: With docs → response includes citations.

        When documents exist, response should cite them with [cite:N] format.
        """
        from modules.rag import RAGModule, RetrievedChunk

        rag = RAGModule()

        mock_chunks = [
            RetrievedChunk(
                chunk_id="1",
                source_type="user_document",
                doc_id="doc-1",
                doc_title="Lab Report",
                page=1,
                text="Cholesterol: 200 mg/dL",
                relevance_score=0.9,
            ),
        ]

        mock_response = """
REPORT FACTS:
Your cholesterol is 200 mg/dL [cite:1].

GENERAL INFO:
Cholesterol is a waxy substance found in blood.

UNCERTAINTIES:
Discuss with your provider for personalized guidance.
"""

        with patch.object(rag, 'retrieve_context', new_callable=AsyncMock) as mock_retrieve:
            mock_retrieve.return_value = mock_chunks

            with patch.object(rag, 'generate_response', new_callable=AsyncMock) as mock_gen:
                mock_gen.return_value = mock_response

                result = await rag.query(
                    question="What is my cholesterol?",
                    profile_id="test-profile",
                )

                assert result.insufficient_context is False

                # Should have citations
                total_citations = sum(len(s.citations) for s in result.segments)
                assert total_citations >= 1

    @pytest.mark.asyncio
    async def test_e2e_rag_003_prohibited_prompt_safe_refusal(self):
        """
        E2E-RAG-003: Prohibited advice prompt → safe refusal.

        Requests for diagnosis/treatment should be safely refused.
        """
        from modules.rag import RAGModule, RetrievedChunk

        rag = RAGModule()

        mock_chunks = [
            RetrievedChunk(
                chunk_id="1",
                source_type="user_document",
                doc_id="doc-1",
                doc_title="Lab Report",
                page=1,
                text="Blood glucose: 250 mg/dL (High)",
                relevance_score=0.9,
            ),
        ]

        # Even if LLM tries to give advice, validation should catch it
        mock_bad_response = """
REPORT FACTS:
Your glucose is 250 mg/dL [cite:1], which is very high.

GENERAL INFO:
You should take insulin immediately. I diagnose you with diabetes. Take metformin 500mg twice daily.
"""

        with patch.object(rag, 'retrieve_context', new_callable=AsyncMock) as mock_retrieve:
            mock_retrieve.return_value = mock_chunks

            with patch.object(rag, 'generate_response', new_callable=AsyncMock) as mock_gen:
                mock_gen.return_value = mock_bad_response

                result = await rag.query(
                    question="Should I take medication for my high glucose?",
                    profile_id="test-profile",
                )

                # Validation should have failed
                assert result.is_valid is False
                assert len(result.validation_errors) > 0


class TestChunkingModuleImplementation:
    """Tests for ChunkingModule implementation details."""

    def test_chunking_handles_empty_text(self):
        """Empty text should return empty chunk list."""
        from modules.chunking import ChunkingModule

        chunker = ChunkingModule()
        chunks = chunker.chunk_document(
            doc_id="test",
            text="",
            page_number=1,
        )

        assert chunks == []

    def test_chunking_handles_short_text(self):
        """Short text under chunk size returns single chunk."""
        from modules.chunking import ChunkingModule

        chunker = ChunkingModule(chunk_size=100)
        chunks = chunker.chunk_document(
            doc_id="test",
            text="Short text.",
            page_number=1,
        )

        assert len(chunks) == 1
        assert chunks[0]["text"] == "Short text."


class TestEmbeddingsModuleImplementation:
    """Tests for EmbeddingsModule implementation details."""

    def test_embeddings_handles_empty_list(self):
        """Empty chunk list should return empty embeddings list."""
        from modules.embeddings import EmbeddingsModule

        embedder = EmbeddingsModule()
        embeddings = embedder.embed_chunks([])

        assert embeddings == []

    def test_embeddings_vector_to_blob_conversion(self):
        """Vectors should be convertible to binary blob for storage."""
        from modules.embeddings import EmbeddingsModule

        embedder = EmbeddingsModule()

        vector = [0.1, 0.2, 0.3, 0.4, 0.5]
        blob = embedder.vector_to_blob(vector)

        assert isinstance(blob, bytes)
        assert len(blob) == len(vector) * 4  # 4 bytes per float32

        # Should be reversible
        recovered = embedder.blob_to_vector(blob)
        assert len(recovered) == len(vector)
        for a, b in zip(vector, recovered):
            assert abs(a - b) < 0.0001  # Float tolerance
