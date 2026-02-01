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
        # TODO: Initialize embedding model
        # TODO: Initialize LLM

        # Phase 4: Verification components
        self.enable_verification = enable_verification
        self.claim_extractor = ClaimExtractor()
        self.authority_scorer = SourceAuthorityScorer()
        self.verifier = VerifierAgent(verification_config)
        self.faithfulness_scorer = FaithfulnessScorer(faithfulness_config)

    async def retrieve_context(
        self,
        query: str,
        profile_id: str,
        selected_analytes: Optional[list[str]] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        include_references: bool = True,
        top_k: int = 10,
    ) -> list[RetrievedChunk]:
        """
        Retrieve relevant chunks for the query.

        Args:
            query: User question
            profile_id: Profile for user documents
            selected_analytes: Filter by analytes
            from_date: Filter by date range start
            to_date: Filter by date range end
            include_references: Include reference corpus
            top_k: Number of chunks to retrieve

        Returns:
            List of relevant chunks with scores
        """
        chunks = []

        # Use sync version internally
        chunks = self.retrieve_context_sync(
            query=query,
            profile_id=profile_id,
            selected_analytes=selected_analytes,
            from_date=from_date,
            to_date=to_date,
            include_references=include_references,
            top_k=top_k,
        )

        return chunks

    def retrieve_context_sync(
        self,
        query: str,
        profile_id: str,
        selected_analytes: Optional[list[str]] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        include_references: bool = True,
        top_k: int = 10,
    ) -> list[RetrievedChunk]:
        """
        Synchronous version of retrieve_context for use in non-async contexts.

        Args:
            query: User question
            profile_id: Profile for user documents
            selected_analytes: Filter by analytes
            from_date: Filter by date range start
            to_date: Filter by date range end
            include_references: Include reference corpus
            top_k: Number of chunks to retrieve

        Returns:
            List of relevant chunks with scores
        """
        # Search vectors (this is mocked in tests)
        search_results = self._search_vectors(
            query=query,
            profile_id=profile_id,
            selected_analytes=selected_analytes,
            from_date=from_date,
            to_date=to_date,
            top_k=top_k,
        )

        # Convert to RetrievedChunk objects
        chunks = []
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
                is_peer_reviewed=chunk_data.get("is_peer_reviewed", False),
                publisher=chunk_data.get("publisher"),
            ))

        return chunks

    def _search_vectors(
        self,
        query: str,
        profile_id: str,
        selected_analytes: Optional[list[str]] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        top_k: int = 10,
    ) -> list[tuple[dict, float]]:
        """
        Search vector database for relevant chunks.

        This method will be implemented to use the actual vector store.
        For now, returns empty list (to be mocked in tests).

        Args:
            query: Search query
            profile_id: Profile to search
            selected_analytes: Filter by analytes
            from_date: Filter by date start
            to_date: Filter by date end
            top_k: Number of results

        Returns:
            List of (chunk_data, similarity_score) tuples
        """
        # TODO: Implement actual vector search
        # This will use EmbeddingsModule to embed query
        # Then search the vector store in the profile database
        return []

    def compose_prompt(
        self,
        question: str,
        retrieved_chunks: list[RetrievedChunk],
    ) -> str:
        """
        Compose the prompt with context and citation markers.

        Each chunk is labeled for citation tracking.
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

        return self.SYSTEM_PROMPT.format(
            context=context,
            question=question,
        )

    async def generate_response(
        self,
        prompt: str,
    ) -> str:
        """
        Generate response using local LLM.

        Uses llama.cpp or configured model runner.
        """
        # TODO: Implement LLM inference
        raise NotImplementedError("LLM inference not yet implemented")

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
        prohibited_patterns = [
            r"\b(you should take|take this medication|dosage|prescribe)\b",
            r"\b(diagnosis|diagnose|you have)\b",
            r"\b(treatment plan|treat this|therapy)\b",
        ]
        for pattern in prohibited_patterns:
            if re.search(pattern, response, re.IGNORECASE):
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

    async def query(
        self,
        question: str,
        profile_id: str,
        selected_analytes: Optional[list[str]] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        include_references: bool = True,
    ) -> ValidatedResponse:
        """
        Complete RAG query with retrieval, generation, and validation.

        This is the main entry point for the RAG pipeline.

        Args:
            question: User's question
            profile_id: Profile ID for document access
            selected_analytes: Optional analyte filter
            from_date: Optional date range start
            to_date: Optional date range end
            include_references: Whether to include reference corpus

        Returns:
            ValidatedResponse with verified, grounded answer
        """
        # Step 1: Retrieve relevant context
        chunks = await self.retrieve_context(
            query=question,
            profile_id=profile_id,
            selected_analytes=selected_analytes,
            from_date=from_date,
            to_date=to_date,
            include_references=include_references,
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

        # Step 2: Compose prompt
        prompt = self.compose_prompt(question, chunks)

        # Step 3: Generate response
        response = await self.generate_response(prompt)

        # Step 4: Validate and verify response
        validated = self.validate_response(response, chunks)

        return validated
