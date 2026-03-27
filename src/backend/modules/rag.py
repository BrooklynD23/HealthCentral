"""
RAG (Retrieval-Augmented Generation) module.

Handles:
- Document chunk retrieval
- Reference corpus retrieval
- Prompt composition with citation requirements
- Response validation
- Dual-agent verification (Phase 4)
"""

from typing import Optional
from dataclasses import dataclass, field
import re
import logging

from core.model_runner import get_model_runner, InferenceConfig
from core.config import settings


class ModelUnavailableError(Exception):
    """Raised when no LLM model is available for inference."""

from .embeddings import EmbeddingsModule
from .claim_extractor import ClaimExtractor, ExtractedClaim, ClaimExtractionResult
from .source_authority import (
    SourceAuthorityScorer,
    SourceMetadata,
    SourceTier,
    ClaimAuthorityAnalysis,
    analyze_claim_authority,
)
from .verifier_agent import (
    VerifierAgent,
    SourceEvidence,
    ClaimVerificationResult,
    VerificationConfig,
    verify_all_claims,
)
from .faithfulness import (
    FaithfulnessScorer,
    FaithfulnessScores,
    FaithfulnessConfig,
)
from .interpret_safety import InterpretationSafetyGuard


@dataclass
class RetrievedChunk:
    """A chunk retrieved for context."""
    chunk_id: str
    source_type: str  # "user_document" or "reference"
    doc_id: Optional[str]
    doc_title: Optional[str]
    page: Optional[int]
    text: str
    relevance_score: float
    # Phase 4: Additional metadata for authority scoring
    is_user_verified: bool = False
    is_peer_reviewed: bool = False
    publisher: Optional[str] = None


@dataclass
class Citation:
    """A citation in the response."""
    citation_id: str
    source_type: str
    doc_id: Optional[str]
    doc_title: Optional[str]
    page: Optional[int]
    text_snippet: str
    # Phase 4: Authority information
    authority_tier: Optional[int] = None
    authority_score: Optional[float] = None


@dataclass
class ResponseSegment:
    """A segment of the assistant response."""
    segment_type: str  # "report_facts", "general_info", "uncertainty"
    content: str
    citations: list[Citation] = field(default_factory=list)


@dataclass
class VerificationMetadata:
    """Metadata from the verification pipeline (Phase 4)."""
    verification_enabled: bool = False
    total_claims: int = 0
    verified_claims: int = 0
    failed_claims: int = 0
    claims_with_issues: list[str] = field(default_factory=list)
    faithfulness_score: float = 0.0
    authority_score: float = 0.0
    verification_summary: str = ""


@dataclass
class ValidatedResponse:
    """Validated assistant response."""
    segments: list[ResponseSegment]
    is_valid: bool
    validation_errors: list[str] = field(default_factory=list)
    insufficient_context: bool = False
    insufficient_reasons: list[str] = field(default_factory=list)
    # Phase 4: Verification metadata
    verification: VerificationMetadata = field(default_factory=VerificationMetadata)


class RAGModule:
    """
    Retrieval-Augmented Generation service.

    Implements grounded assistant with strict citation requirements
    and dual-agent verification (Phase 4).
    """

    # Prompt template for grounded responses
    SYSTEM_PROMPT = """You are a medical results assistant that helps patients understand their lab values.

CRITICAL RULES:
1. You must cite sources for ALL factual claims using [cite:N] format
2. Separate your response into:
   - REPORT FACTS: What the patient's report shows (must cite user documents)
   - GENERAL INFO: Educational context (cite reference materials)
   - UNCERTAINTIES: What cannot be determined
3. NEVER provide diagnosis, treatment advice, or medication dosing
4. Use neutral, non-alarming language
5. If you cannot answer with citations, say "I don't have enough information"

CONTEXT:
{context}

USER QUESTION: {question}"""

    # Treat conversation history as untrusted input; strip likely jailbreaks.
    PROMPT_INJECTION_PATTERNS = [
        r"\b(ignore|disregard|forget)\b.{0,60}\b(instructions?|rules?|system|developer|prompt)\b",
        r"\b(system prompt|developer message|jailbreak|dan mode|prompt injection)\b",
        r"\b(override|bypass|disable)\b.{0,40}\b(safety|guardrails?|restrictions?|rules?)\b",
        r"\b(act as|pretend to be|you are now)\b.{0,60}\b(doctor|physician|system|admin)\b",
    ]

    def __init__(
        self,
        enable_verification: bool = True,
        verification_config: Optional[VerificationConfig] = None,
        faithfulness_config: Optional[FaithfulnessConfig] = None,
    ):
        """
        Initialize RAG module.

        Args:
            enable_verification: Enable Phase 4 dual-agent verification
            verification_config: Configuration for verifier agent
            faithfulness_config: Configuration for faithfulness scoring
        """
        self._logger = logging.getLogger(__name__)

        # Sprint 6: Initialize LLM model runner and embeddings
        self._model_runner = get_model_runner()
        self._embedder = EmbeddingsModule()

        # Phase 4: Verification components
        self.enable_verification = enable_verification
        self.claim_extractor = ClaimExtractor()
        self.authority_scorer = SourceAuthorityScorer()
        self.verifier = VerifierAgent(verification_config)
        self.faithfulness_scorer = FaithfulnessScorer(faithfulness_config)
        self._compiled_prohibited_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern, _ in InterpretationSafetyGuard.PROHIBITED_PATTERNS
        ]
        self._compiled_prompt_injection_patterns = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.PROMPT_INJECTION_PATTERNS
        ]

    # INGEST-F: Category filter support for retrieve_context
    VALID_CATEGORIES = {"imaging", "pathology", "visit_notes", "lab"}

    async def retrieve_context(
        self,
        query: str,
        profile_id: str,
        selected_analytes: Optional[list[str]] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        include_references: bool = True,
        top_k: int = 10,
        master_db=None,
        profile_db=None,
        category: Optional[str] = None,
    ) -> list[RetrievedChunk]:
        """
        Retrieve relevant chunks for the query (async).

        Args:
            query: User question
            profile_id: Profile for user documents
            selected_analytes: Filter by analytes
            from_date: Filter by date range start
            to_date: Filter by date range end
            include_references: Include reference corpus
            top_k: Number of chunks to retrieve
            master_db: Master database session for reference lookups
            profile_db: Profile database session for vector search
            category: Optional document category filter (imaging, pathology, visit_notes, lab)

        Returns:
            List of relevant chunks with scores
        """
        chunks = []

        # Search user document vectors directly (async)
        if profile_db is not None:
            search_results = await self._search_vectors_async(
                query=query,
                profile_id=profile_id,
                selected_analytes=selected_analytes,
                from_date=from_date,
                to_date=to_date,
                top_k=top_k,
                profile_db=profile_db,
                category=category,
            )

            for chunk_data, score in search_results:
                chunks.append(RetrievedChunk(
                    chunk_id=chunk_data.get("chunk_id", ""),
                    source_type=chunk_data.get("source_type", "user_document"),
                    doc_id=chunk_data.get("doc_id"),
                    doc_title=chunk_data.get("doc_title"),
                    page=chunk_data.get("page_number"),
                    text=chunk_data.get("text", ""),
                    relevance_score=score,
                    is_user_verified=chunk_data.get("is_user_verified", False),
                ))

        # Add reference corpus chunks from knowledge base
        if include_references and master_db:
            ref_chunks = await self._get_reference_chunks(query, selected_analytes, master_db)
            chunks.extend(ref_chunks)

        return chunks

    async def _get_reference_chunks(
        self,
        query: str,
        selected_analytes: Optional[list[str]],
        master_db,
    ) -> list[RetrievedChunk]:
        """
        Retrieve reference corpus chunks from the knowledge base.

        Uses KnowledgeLoader to fetch biomarker data for analytes mentioned
        in the query or selected by the user.
        """
        from .knowledge_loader import get_knowledge_loader
        from .normalize import NormalizeModule

        ref_chunks = []
        knowledge = get_knowledge_loader()
        normalizer = NormalizeModule()

        # Determine which analytes to look up
        analytes_to_search = set(selected_analytes or [])

        # Also extract analyte mentions from the query text
        query_lower = query.lower()
        for canonical, synonyms in normalizer.ANALYTE_SYNONYMS.items():
            if canonical in query_lower or any(syn in query_lower for syn in synonyms):
                analytes_to_search.add(canonical)

        # Fetch knowledge entries for each analyte
        for analyte in analytes_to_search:
            try:
                info = await knowledge.get_biomarker_knowledge(analyte, master_db)
                if info:
                    # Build a reference text from the knowledge entry
                    ref_text = (
                        f"{info.display_name}: {info.description}\n"
                        f"Clinical significance: {info.clinical_significance}\n"
                        f"Normal: {info.normal_interpretation}\n"
                        f"High: {info.high_interpretation}\n"
                        f"Low: {info.low_interpretation}"
                    )
                    if info.ref_range_adult:
                        ref_text += f"\nReference range: {info.ref_range_adult}"

                    ref_chunks.append(RetrievedChunk(
                        chunk_id=f"ref_{info.id}",
                        source_type="reference",
                        doc_id=None,
                        doc_title=f"Medical Reference: {info.display_name}",
                        page=None,
                        text=ref_text,
                        relevance_score=0.8,
                        is_peer_reviewed=True,
                        publisher="HealthCentral Knowledge Base",
                    ))
            except Exception as e:
                self._logger.debug(f"Failed to load reference for {analyte}: {e}")

        return ref_chunks

    async def _search_vectors_async(
        self,
        query: str,
        profile_id: str,
        selected_analytes: Optional[list[str]] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        top_k: int = 10,
        profile_db=None,
        category: Optional[str] = None,
    ) -> list[tuple[dict, float]]:
        """
        Async implementation of vector search with date/analyte/panel/category filtering.

        Args:
            query: Search query
            profile_id: Profile to search
            selected_analytes: Filter by canonical analyte names
            from_date: Filter by date range start (ISO format)
            to_date: Filter by date range end (ISO format)
            top_k: Number of results
            category: Optional document category filter

        Returns:
            List of (chunk_data, similarity_score) tuples
        """
        from sqlalchemy import select
        from models import Chunk, DocumentCategory, Embedding, Document, Observation
        from datetime import datetime

        # Embed the query
        query_vector = self._embedder.embed_text(query)

        # Build base query
        stmt = (
            select(Chunk, Embedding, Document)
            .join(Embedding, Chunk.id == Embedding.chunk_id)
            .join(Document, Chunk.doc_id == Document.id)
        )

        # Apply date filters on Document.collection_date
        if from_date:
            try:
                from_dt = datetime.fromisoformat(from_date)
                stmt = stmt.where(Document.collection_date >= from_dt)
            except (ValueError, TypeError):
                pass

        if to_date:
            try:
                to_dt = datetime.fromisoformat(to_date)
                stmt = stmt.where(Document.collection_date <= to_dt)
            except (ValueError, TypeError):
                pass

        # Apply analyte filter: only include documents that contain matching observations
        if selected_analytes:
            analyte_doc_stmt = (
                select(Observation.doc_id)
                .where(Observation.analyte_canonical.in_(selected_analytes))
                .distinct()
            )
            stmt = stmt.where(Document.id.in_(analyte_doc_stmt))

        # Apply category filter: only include documents classified into the requested bucket
        if category:
            category_doc_stmt = (
                select(DocumentCategory.doc_id)
                .where(DocumentCategory.category == category)
                .distinct()
            )
            stmt = stmt.where(Document.id.in_(category_doc_stmt))

        result = await profile_db.execute(stmt)
        rows = result.all()

        if not rows:
            return []

        # Calculate similarity scores
        candidates = []
        for chunk, embedding, document in rows:
            stored_vector = self._embedder.blob_to_vector(embedding.vector_blob)
            similarity = self._embedder.cosine_similarity(query_vector, stored_vector)

            chunk_data = {
                "chunk_id": chunk.id,
                "doc_id": chunk.doc_id,
                "doc_title": document.source or f"Document {document.id[:8]}",
                "text": chunk.text,
                "page_number": chunk.page_number,
                "source_type": "user_document",
                "is_user_verified": document.status == "verified",
            }
            candidates.append((chunk_data, similarity))

        # Sort by similarity descending and return top_k
        candidates.sort(key=lambda x: x[1], reverse=True)

        return candidates[:top_k]

    def compose_prompt(
        self,
        question: str,
        retrieved_chunks: list[RetrievedChunk],
        history: Optional[list] = None,
    ) -> str:
        """
        Compose the prompt with context, conversation history, and citation markers.

        Each chunk is labeled for citation tracking.

        Args:
            question: Current user question
            retrieved_chunks: Retrieved context chunks
            history: List of ChatMessage-like objects with .role and .content
        """
        context_parts = []

        for i, chunk in enumerate(retrieved_chunks, start=1):
            source_label = f"[{chunk.source_type.upper()}:{i}]"
            if chunk.doc_title:
                source_label += f" {chunk.doc_title}"
            if chunk.page:
                source_label += f" (page {chunk.page})"

            context_parts.append(f"{source_label}\n{chunk.text}")

        context = "\n\n---\n\n".join(context_parts)

        # Build conversation history section
        history_section = ""
        if history:
            # Limit history to last ~2000 chars to fit context window
            history_lines = []
            char_count = 0
            sanitized_history = self._sanitize_history(history)
            for role, content in reversed(sanitized_history):
                line = f"{role.upper()}: {content}"
                if char_count + len(line) > 2000:
                    break
                history_lines.insert(0, line)
                char_count += len(line)
            if history_lines:
                history_section = "\n\nCONVERSATION HISTORY:\n" + "\n".join(history_lines) + "\n"

        prompt = self.SYSTEM_PROMPT.format(
            context=context,
            question=question,
        )

        # Insert history before the question
        if history_section:
            prompt = prompt.replace(
                f"USER QUESTION: {question}",
                f"{history_section}\nUSER QUESTION: {question}",
            )

        return prompt

    def _sanitize_history(self, history: list) -> list[tuple[str, str]]:
        """
        Drop unsafe history entries before injecting into the model prompt.

        History can contain adversarial instructions from prior turns; these are
        filtered using prompt-injection patterns.
        """
        sanitized = []
        for msg in history:
            role, content = self._extract_history_fields(msg)
            if self._contains_prompt_injection(content):
                self._logger.warning(
                    "Filtered potentially unsafe conversation history entry"
                )
                continue
            sanitized.append((role, content))
        return sanitized

    def _extract_history_fields(self, msg) -> tuple[str, str]:
        """Normalize a history message object/dict into (role, content)."""
        if isinstance(msg, dict):
            role = str(msg.get("role", "user"))
            content = str(msg.get("content", ""))
        else:
            role = str(getattr(msg, "role", "user"))
            content = str(getattr(msg, "content", ""))
        return role, content

    def _contains_prompt_injection(self, text: str) -> bool:
        """Check whether text contains likely prompt-injection content."""
        return any(pattern.search(text) for pattern in self._compiled_prompt_injection_patterns)

    async def generate_response(
        self,
        prompt: str,
    ) -> str:
        """
        Generate response using local LLM.

        Uses llama-cpp-python via the ModelRunner.

        Args:
            prompt: The composed prompt with context and question

        Returns:
            Generated response text

        Raises:
            RuntimeError: If LLM is not available
        """
        if not self._model_runner.is_available():
            self._logger.warning("LLM model not available for inference")
            raise ModelUnavailableError(
                "LLM model not available. Please download a GGUF model to the models directory."
            )

        config = InferenceConfig(
            max_tokens=1024,
            temperature=0.1,  # Low temperature for factual, consistent responses
            top_p=0.9,
            timeout_seconds=60,
        )

        try:
            result = await self._model_runner.generate_async(prompt, config)

            if result.finish_reason == "timeout":
                self._logger.warning("LLM generation timed out")
                # Return a safe response rather than failing
                return """UNCERTAINTIES:
I was unable to fully process your question within the time limit. Please try asking a more specific question about your results."""

            return result.text

        except Exception as e:
            self._logger.error(f"LLM generation failed: {e}")
            raise RuntimeError(f"Failed to generate response: {e}")

    def validate_response(
        self,
        response: str,
        retrieved_chunks: list[RetrievedChunk],
    ) -> ValidatedResponse:
        """
        Validate response has required citations and follows rules.

        Phase 4: Now includes dual-agent verification with:
        - Claim extraction
        - Source authority checking
        - Entailment verification
        - Faithfulness scoring

        Checks:
        - All report facts have citations
        - Citations reference valid chunks
        - No diagnosis/treatment advice detected
        - (Phase 4) Claims are verified against sources
        """
        errors = []

        # Parse response into segments
        segments = self._parse_response_segments(response)

        # Extract citations
        citation_pattern = r"\[cite:(\d+)\]"
        found_citations = set(re.findall(citation_pattern, response))

        # Validate citations exist
        valid_citation_ids = set(str(i) for i in range(1, len(retrieved_chunks) + 1))
        invalid_citations = found_citations - valid_citation_ids
        if invalid_citations:
            errors.append(f"Invalid citation IDs: {invalid_citations}")

        # Check report facts have citations
        for segment in segments:
            if segment.segment_type == "report_facts":
                segment_citations = re.findall(citation_pattern, segment.content)
                if not segment_citations:
                    errors.append("Report facts section missing citations")

        # Check for prohibited content
        for pattern in self._compiled_prohibited_patterns:
            if pattern.search(response):
                errors.append("Response contains prohibited medical advice")
                break

        # Build validated segments with citations
        validated_segments = self._build_validated_segments(
            segments, retrieved_chunks, citation_pattern
        )

        # Phase 4: Dual-agent verification
        verification_metadata = VerificationMetadata(
            verification_enabled=self.enable_verification
        )

        if self.enable_verification and retrieved_chunks:
            verification_metadata = self._run_verification_pipeline(
                response, retrieved_chunks, validated_segments
            )

            # Add verification failures to errors
            if verification_metadata.failed_claims > 0:
                errors.append(
                    f"{verification_metadata.failed_claims} claim(s) could not be verified"
                )

            if verification_metadata.faithfulness_score < 0.6:
                errors.append(
                    f"Low faithfulness score: {verification_metadata.faithfulness_score:.2f}"
                )

        return ValidatedResponse(
            segments=validated_segments,
            is_valid=len(errors) == 0,
            validation_errors=errors,
            verification=verification_metadata,
        )

    def _build_validated_segments(
        self,
        segments: list[ResponseSegment],
        retrieved_chunks: list[RetrievedChunk],
        citation_pattern: str,
    ) -> list[ResponseSegment]:
        """Build validated segments with citation details."""
        validated_segments = []

        for segment in segments:
            segment_citations = []
            for match in re.finditer(citation_pattern, segment.content):
                cite_id = match.group(1)
                idx = int(cite_id) - 1
                if 0 <= idx < len(retrieved_chunks):
                    chunk = retrieved_chunks[idx]

                    # Phase 4: Get authority tier
                    source_meta = SourceMetadata(
                        source_id=cite_id,
                        source_type=chunk.source_type,
                        doc_id=chunk.doc_id,
                        title=chunk.doc_title,
                        is_user_verified=chunk.is_user_verified,
                        is_peer_reviewed=chunk.is_peer_reviewed,
                        publisher=chunk.publisher,
                    )
                    classified = self.authority_scorer.classify_source(source_meta)

                    segment_citations.append(Citation(
                        citation_id=cite_id,
                        source_type=chunk.source_type,
                        doc_id=chunk.doc_id,
                        doc_title=chunk.doc_title,
                        page=chunk.page,
                        text_snippet=chunk.text[:200],
                        authority_tier=classified.authority_tier.value,
                        authority_score=classified.authority_score,
                    ))

            validated_segments.append(ResponseSegment(
                segment_type=segment.segment_type,
                content=segment.content,
                citations=segment_citations,
            ))

        return validated_segments

    def _run_verification_pipeline(
        self,
        response: str,
        retrieved_chunks: list[RetrievedChunk],
        validated_segments: list[ResponseSegment],
    ) -> VerificationMetadata:
        """
        Run Phase 4 verification pipeline.

        Steps:
        1. Extract claims from response
        2. Check source authority for each claim
        3. Verify claims against cited sources
        4. Calculate faithfulness scores
        """
        # Step 1: Extract claims
        extraction_result = self.claim_extractor.extract_claims(response)
        verifiable, unverifiable = self.claim_extractor.filter_unverifiable_claims(
            extraction_result.claims
        )

        if not verifiable:
            return VerificationMetadata(
                verification_enabled=True,
                total_claims=len(extraction_result.claims),
                verified_claims=0,
                failed_claims=0,
                faithfulness_score=1.0,  # No verifiable claims = no failures
                verification_summary="No verifiable claims to check",
            )

        # Step 2: Build source evidence map
        chunk_map = {
            str(i + 1): chunk for i, chunk in enumerate(retrieved_chunks)
        }

        # Step 3: Verify each claim
        claims_to_verify = []
        claim_authority_scores = []

        for claim in verifiable:
            # Get source evidence for this claim's citations
            sources = []
            source_metas = []

            for cite_id in claim.cited_sources:
                if cite_id in chunk_map:
                    chunk = chunk_map[cite_id]
                    sources.append(SourceEvidence(
                        source_id=cite_id,
                        source_text=chunk.text,
                        source_type=chunk.source_type,
                        doc_title=chunk.doc_title,
                        page=chunk.page,
                    ))
                    source_metas.append(SourceMetadata(
                        source_id=cite_id,
                        source_type=chunk.source_type,
                        doc_id=chunk.doc_id,
                        title=chunk.doc_title,
                        is_user_verified=chunk.is_user_verified,
                        is_peer_reviewed=chunk.is_peer_reviewed,
                        publisher=chunk.publisher,
                    ))

            claims_to_verify.append((claim.claim_id, claim.text, sources))

            # Check authority
            if source_metas:
                authority = analyze_claim_authority(
                    claim.claim_id, claim.claim_type, source_metas
                )
                claim_authority_scores.append(authority.aggregate_score)

        # Run batch verification
        verification_results = verify_all_claims(claims_to_verify)

        # Step 4: Calculate faithfulness
        all_source_texts = [chunk.text for chunk in retrieved_chunks]
        claim_texts = [claim.text for claim in verifiable]
        faithfulness = self.faithfulness_scorer.score_response(
            claim_texts, all_source_texts
        )

        # Collect issues
        issues_list = []
        for result in verification_results.results:
            if not result.is_verified:
                issues_list.append(
                    f"{result.claim_id}: {result.recommendation}"
                )

        # Calculate average authority score
        avg_authority = (
            sum(claim_authority_scores) / len(claim_authority_scores)
            if claim_authority_scores else 0.0
        )

        return VerificationMetadata(
            verification_enabled=True,
            total_claims=len(extraction_result.claims),
            verified_claims=verification_results.verified_claims,
            failed_claims=verification_results.failed_claims,
            claims_with_issues=issues_list[:5],  # Limit to first 5 issues
            faithfulness_score=faithfulness.overall_score,
            authority_score=round(avg_authority, 3),
            verification_summary=verification_results.summary,
        )

    def _parse_response_segments(self, response: str) -> list[ResponseSegment]:
        """Parse response into labeled segments."""
        segments = []

        # Look for section headers
        section_patterns = [
            (r"REPORT FACTS:?\s*(.*?)(?=GENERAL INFO:|UNCERTAINTIES:|$)", "report_facts"),
            (r"GENERAL INFO:?\s*(.*?)(?=REPORT FACTS:|UNCERTAINTIES:|$)", "general_info"),
            (r"UNCERTAINTIES:?\s*(.*?)(?=REPORT FACTS:|GENERAL INFO:|$)", "uncertainty"),
        ]

        for pattern, segment_type in section_patterns:
            match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
            if match and match.group(1).strip():
                segments.append(ResponseSegment(
                    segment_type=segment_type,
                    content=match.group(1).strip(),
                ))

        # If no sections found, treat entire response as general
        if not segments:
            segments.append(ResponseSegment(
                segment_type="general_info",
                content=response.strip(),
            ))

        return segments

    async def _retrieve_memory_context(
        self,
        profile_id: str,
        profile_db,
    ) -> str:
        """
        Retrieve user memory items and format as context block.

        ASSIST-MEM-003: Memory items are injected as a USER PREFERENCES section
        so the model can personalise responses without altering citation rules.

        Returns empty string when no items exist or feature is disabled.
        """
        if profile_db is None:
            return ""

        try:
            from sqlalchemy import select
            from models.memory_item import MemoryItem

            max_items = max(0, int(getattr(settings, "assistant_memory_max_items_in_prompt", 0)))
            max_chars = max(0, int(getattr(settings, "assistant_memory_max_prompt_chars", 0)))
            if max_items <= 0 or max_chars <= 0:
                return ""

            header = (
                "\nUSER PREFERENCES (from memory store — do NOT cite, "
                "use only for personalisation):\n"
            )
            if len(header) >= max_chars:
                return ""

            stmt = (
                select(MemoryItem)
                .where(MemoryItem.profile_id == profile_id)
                .order_by(MemoryItem.updated_at.desc())
            )
            result = await profile_db.execute(stmt)
            items = result.scalars().all()

            if not items:
                return ""

            def _single_line(value: str) -> str:
                return " ".join(str(value or "").split())

            def _normalize_value(value: str) -> str:
                text = str(value or "")
                text = text.replace("\x00", "")
                text = text.replace("\r\n", "\n").replace("\r", "\n")
                return text.strip()

            def _render_item(*, label: str, value: str, max_len: int) -> str:
                suffix = " …[truncated]"
                clean_value = _normalize_value(value)
                if "\n" in clean_value:
                    rendered = "- " + label + ":\n" + "\n".join(
                        "  " + line for line in clean_value.split("\n")
                    )
                else:
                    rendered = f"- {label}: {clean_value}"

                if len(rendered) <= max_len:
                    return rendered

                if max_len <= len(suffix):
                    return rendered[:max_len]
                return rendered[: max_len - len(suffix)] + suffix

            lines: list[str] = []
            current_len = len(header) + 1  # include trailing newline below

            for item in items:
                if len(lines) >= max_items:
                    break

                combined = f"{item.key}\n{item.category or ''}\n{item.value}"
                if self._contains_prompt_injection(combined):
                    self._logger.warning(
                        "Filtered potentially unsafe memory item",
                        extra={"memory_item_id": getattr(item, "id", None)},
                    )
                    continue

                label = _single_line(item.key)
                category = _single_line(item.category) if item.category else ""
                if category:
                    label = f"{label} [{category}]"

                remaining = max_chars - current_len
                if remaining <= 0:
                    break

                rendered = _render_item(label=label, value=item.value, max_len=remaining)
                if not rendered:
                    break

                lines.append(rendered)
                current_len += len(rendered) + 1  # newline join
                if current_len >= max_chars:
                    break

            if not lines:
                return ""

            return header + "\n".join(lines) + "\n"
        except Exception as e:
            self._logger.debug(f"Memory retrieval failed: {e}")
            return ""

    async def query(
        self,
        question: str,
        profile_id: str,
        selected_analytes: Optional[list[str]] = None,
        selected_panel: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        include_references: bool = True,
        history: Optional[list] = None,
        model_runner=None,
        master_db=None,
        profile_db=None,
        use_memory: bool = False,
        category: Optional[str] = None,
    ) -> ValidatedResponse:
        """
        Complete RAG query with retrieval, generation, and validation.

        This is the main entry point for the RAG pipeline.

        Args:
            question: User's question
            profile_id: Profile ID for document access
            selected_analytes: Optional analyte filter
            selected_panel: Optional panel name to map to analytes
            from_date: Optional date range start
            to_date: Optional date range end
            include_references: Whether to include reference corpus
            history: Conversation history for multi-turn context
            model_runner: Optional override model runner (for external API)
            master_db: Master database session for reference lookups
            category: Optional document category filter for user-document retrieval

        Returns:
            ValidatedResponse with verified, grounded answer
        """
        # Resolve panel to analyte list if specified
        effective_analytes = list(selected_analytes) if selected_analytes else []
        if selected_panel:
            from .normalize import NormalizeModule
            normalizer = NormalizeModule()
            panel_analytes = normalizer.get_panel_analytes(selected_panel)
            if panel_analytes:
                effective_analytes = list(set(effective_analytes + panel_analytes))

        # Step 1: Retrieve relevant context
        chunks = await self.retrieve_context(
            query=question,
            profile_id=profile_id,
            selected_analytes=effective_analytes if effective_analytes else None,
            from_date=from_date,
            to_date=to_date,
            include_references=include_references,
            master_db=master_db,
            profile_db=profile_db,
            category=category,
        )

        # Check for insufficient context
        if not chunks:
            return ValidatedResponse(
                segments=[ResponseSegment(
                    segment_type="uncertainty",
                    content="I don't have enough information to answer this question. "
                            "Please make sure you have uploaded relevant documents.",
                )],
                is_valid=True,
                insufficient_context=True,
                insufficient_reasons=["No relevant documents found"],
            )

        # Step 2: Optionally retrieve memory context (ASSIST-MEM-003)
        memory_section = ""
        if use_memory:
            if settings.assistant_memory_enabled:
                memory_section = await self._retrieve_memory_context(
                    profile_id, profile_db
                )

        # Step 2b: Compose prompt with history
        prompt = self.compose_prompt(question, chunks, history=history)

        # Inject memory section after context, before user question
        if memory_section:
            prompt = prompt.replace(
                f"USER QUESTION: {question}",
                f"{memory_section}\nUSER QUESTION: {question}",
            )

        # Step 3: Generate response (use override runner if provided)
        runner = model_runner or self._model_runner
        response = await self._generate_with_runner(prompt, runner)

        # Step 4: Validate and verify response
        validated = self.validate_response(response, chunks)

        return validated

    async def _generate_with_runner(self, prompt: str, runner) -> str:
        """Generate response using the provided model runner."""
        if not runner.is_available():
            self._logger.warning("Model runner not available for inference")
            raise ModelUnavailableError(
                "LLM model not available. Please download a GGUF model or configure an external API."
            )

        config = InferenceConfig(
            max_tokens=1024,
            temperature=0.1,
            top_p=0.9,
            timeout_seconds=60,
        )

        try:
            result = await runner.generate_async(prompt, config)
            if result.finish_reason == "timeout":
                return """UNCERTAINTIES:
I was unable to fully process your question within the time limit. Please try asking a more specific question about your results."""
            return result.text
        except Exception as e:
            self._logger.error(f"LLM generation failed: {e}")
            raise RuntimeError(f"Failed to generate response: {e}")
