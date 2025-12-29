"""
RAG (Retrieval-Augmented Generation) module.

Handles:
- Document chunk retrieval
- Reference corpus retrieval
- Prompt composition with citation requirements
- Response validation
"""

from typing import Optional
from dataclasses import dataclass, field
import re


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


@dataclass
class Citation:
    """A citation in the response."""
    citation_id: str
    source_type: str
    doc_id: Optional[str]
    doc_title: Optional[str]
    page: Optional[int]
    text_snippet: str


@dataclass
class ResponseSegment:
    """A segment of the assistant response."""
    segment_type: str  # "report_facts", "general_info", "uncertainty"
    content: str
    citations: list[Citation] = field(default_factory=list)


@dataclass
class ValidatedResponse:
    """Validated assistant response."""
    segments: list[ResponseSegment]
    is_valid: bool
    validation_errors: list[str] = field(default_factory=list)
    insufficient_context: bool = False
    insufficient_reasons: list[str] = field(default_factory=list)


class RAGModule:
    """
    Retrieval-Augmented Generation service.
    
    Implements grounded assistant with strict citation requirements.
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

    def __init__(self):
        """Initialize RAG module."""
        # TODO: Initialize embedding model
        # TODO: Initialize LLM
        pass
    
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
        
        # TODO: Embed query
        # TODO: Search user document vectors
        # TODO: Search reference corpus vectors
        # TODO: Merge and rank results
        
        return chunks
    
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
        
        Checks:
        - All report facts have citations
        - Citations reference valid chunks
        - No diagnosis/treatment advice detected
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
        
        # Build validated response
        validated_segments = []
        for segment in segments:
            segment_citations = []
            for match in re.finditer(citation_pattern, segment.content):
                cite_id = match.group(1)
                idx = int(cite_id) - 1
                if 0 <= idx < len(retrieved_chunks):
                    chunk = retrieved_chunks[idx]
                    segment_citations.append(Citation(
                        citation_id=cite_id,
                        source_type=chunk.source_type,
                        doc_id=chunk.doc_id,
                        doc_title=chunk.doc_title,
                        page=chunk.page,
                        text_snippet=chunk.text[:200],
                    ))
            
            validated_segments.append(ResponseSegment(
                segment_type=segment.segment_type,
                content=segment.content,
                citations=segment_citations,
            ))
        
        return ValidatedResponse(
            segments=validated_segments,
            is_valid=len(errors) == 0,
            validation_errors=errors,
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
