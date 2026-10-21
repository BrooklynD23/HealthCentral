"""
Claim Extraction module for AI Safety.

Phase 4: Extracts individual factual claims from LLM responses
for verification against source documents.

This module is part of the dual-agent verification pattern:
1. Primary agent generates response with citations
2. Claim extractor parses individual facts
3. Verifier agent checks each claim against cited sources
"""

import re
from dataclasses import dataclass, field
from typing import Optional


def _carries_fact(claim: "ExtractedClaim") -> bool:
    """True when a claim has a citation or a number (UNC-VERIFY-SCOPE (a))."""
    return bool(claim.cited_sources) or bool(re.search(r"\d", claim.text))


@dataclass
class ExtractedClaim:
    """
    A single factual claim extracted from a response.

    Each claim is a verifiable statement that should be
    supported by cited evidence.
    """
    claim_id: str
    text: str
    segment_type: str  # "report_facts", "general_info", "uncertainty"
    cited_sources: list[str] = field(default_factory=list)  # Citation IDs
    claim_type: str = "factual"  # factual, comparative, temporal, causal
    confidence: float = 1.0  # Extraction confidence

    # Verification results (populated by verifier)
    verified: Optional[bool] = None
    verification_score: Optional[float] = None
    verification_notes: list[str] = field(default_factory=list)


@dataclass
class ClaimExtractionResult:
    """Result of claim extraction from a response."""
    claims: list[ExtractedClaim]
    extraction_method: str  # "rule_based" or "llm_assisted"
    raw_response: str
    parsing_errors: list[str] = field(default_factory=list)


class ClaimExtractor:
    """
    Extracts verifiable claims from LLM responses.

    Uses a combination of:
    1. Rule-based extraction for structured sections
    2. Sentence splitting with claim boundary detection
    3. Citation linking for source tracking

    For Phase 4, this implements the initial rule-based approach.
    LLM-assisted extraction can be added later for complex cases.
    """

    # Patterns for claim boundary detection
    CLAIM_DELIMITERS = [
        r"[.!?](?:\s|$)",  # End of sentence
        r";\s",  # Semicolon separator
        r",\s+(?:and|but|however|also|additionally)\s",  # Conjunction clauses
    ]

    # Patterns for different claim types
    CLAIM_TYPE_PATTERNS = {
        "comparative": [
            r"\b(higher|lower|above|below|greater|less|more|fewer)\b",
            r"\b(increased|decreased|elevated|reduced)\b",
            r"\b(compared to|relative to|versus)\b",
        ],
        "temporal": [
            r"\b(since|after|before|during|when|while)\b",
            r"\b(previously|recently|currently|now)\b",
            r"\b(trend|change|progression)\b",
        ],
        "causal": [
            r"\b(because|due to|caused by|results from)\b",
            r"\b(leads to|results in|contributes to)\b",
            r"\b(indicates|suggests|implies)\b",
        ],
        "quantitative": [
            r"\b\d+(?:\.\d+)?\s*(?:mg|g|kg|mmol|µmol|ml|L|%)\b",
            r"\b\d+(?:\.\d+)?(?:\s*-\s*\d+(?:\.\d+)?)?\b",
        ],
    }

    # Citation pattern
    CITATION_PATTERN = r"\[cite:(\d+)\]"

    def __init__(self, min_claim_length: int = 10, max_claim_length: int = 500):
        """
        Initialize claim extractor.

        Args:
            min_claim_length: Minimum characters for a valid claim
            max_claim_length: Maximum characters before splitting
        """
        self.min_claim_length = min_claim_length
        self.max_claim_length = max_claim_length

    def extract_claims(self, response: str) -> ClaimExtractionResult:
        """
        Extract all verifiable claims from a response.

        Process:
        1. Parse response into sections (REPORT FACTS, GENERAL INFO, etc.)
        2. Split sections into sentences
        3. Identify claim boundaries
        4. Link citations to claims
        5. Classify claim types

        Args:
            response: Full LLM response text

        Returns:
            ClaimExtractionResult with list of claims
        """
        claims: list[ExtractedClaim] = []
        errors: list[str] = []
        claim_counter = 0

        # Parse into sections
        sections = self._parse_sections(response)

        for segment_type, content in sections:
            # Extract claims from section content
            section_claims = self._extract_claims_from_section(
                content, segment_type, claim_counter
            )
            if segment_type == "uncertainty":
                # Fact-free hedges are not claims. Keep only lines that carry a
                # citation or a number, renumbered so ids stay unique and equal
                # to main's when everything is dropped.
                section_claims = [c for c in section_claims if _carries_fact(c)]
                for n, c in enumerate(section_claims, start=1):
                    c.claim_id = f"claim_{claim_counter + n}"
            claims.extend(section_claims)
            claim_counter += len(section_claims)

        # If no sections found, process entire response
        if not claims and response.strip():
            claims = self._extract_claims_from_section(
                response, "general_info", 0
            )

        return ClaimExtractionResult(
            claims=claims,
            extraction_method="rule_based",
            raw_response=response,
            parsing_errors=errors,
        )

    # A section header counts only at the start of a line (LCP-HL-SCOPE (a)). The
    # keyword must be followed by ":", "**" or the end of the line, so a prose line
    # such as "Uncertainty about lab ranges [cite:1]" is not a header. RAGModule
    # splits responses with this same regex and map, so the verifier sees exactly
    # the text the parser serves. A header may carry a list marker ("- ", "1. "), a
    # space before the colon, or a dash / "(note)" terminator.
    SECTION_HEADER_RE = re.compile(
        r"^[ \t]*(?:(?:[-*•]|\d+[.)])[ \t]+)?(?:\*\*|#+[ \t]*)?"
        r"(REPORT FACTS|GENERAL INFO(?:RMATION)?|UNCERTAINTIES|UNCERTAINTY)"
        r"(?:[ \t]*\([^)\n]*\))?"
        r"(?=[ \t]*:|\*\*|[ \t]*$|[ \t]+[-–—][ \t])"
        r"[ \t]*\**[ \t]*(?::|[-–—](?=[ \t]))?\**",
        re.IGNORECASE | re.MULTILINE,
    )
    SECTION_TYPES = {
        "REPORT FACTS": "report_facts",
        "GENERAL INFO": "general_info",
        "GENERAL INFORMATION": "general_info",
        "UNCERTAINTIES": "uncertainty",
        "UNCERTAINTY": "uncertainty",
    }

    def _parse_sections(self, response: str) -> list[tuple[str, str]]:
        """Parse response into labeled sections.

        Text before the first header, and headerless text, is report_facts so the
        verifier checks it. Empty or whitespace-only text gives no section.
        """
        sections: list[tuple[str, str]] = []
        headers = list(self.SECTION_HEADER_RE.finditer(response))

        prefix = response[: headers[0].start()] if headers else response
        if prefix.strip():
            sections.append(("report_facts", prefix.strip()))

        for i, header in enumerate(headers):
            end = headers[i + 1].start() if i + 1 < len(headers) else len(response)
            content = response[header.end() : end].strip()
            if content:
                sections.append((self.SECTION_TYPES[header.group(1).upper()], content))

        return sections

    def _extract_claims_from_section(
        self,
        content: str,
        segment_type: str,
        start_index: int,
    ) -> list[ExtractedClaim]:
        """Extract claims from a single section."""
        claims = []

        # Split into sentences
        sentences = self._split_into_sentences(content)

        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()

            # Skip too short or too long
            if len(sentence) < self.min_claim_length:
                continue

            # Handle overly long sentences by splitting on clauses
            if len(sentence) > self.max_claim_length:
                sub_claims = self._split_long_sentence(sentence)
            else:
                sub_claims = [sentence]

            for j, claim_text in enumerate(sub_claims):
                if len(claim_text) < self.min_claim_length:
                    continue

                claim_id = f"claim_{start_index + len(claims) + 1}"

                # Extract citations from claim
                citations = re.findall(self.CITATION_PATTERN, claim_text)

                # Classify claim type
                claim_type = self._classify_claim_type(claim_text)

                # Calculate extraction confidence based on structure
                confidence = self._calculate_extraction_confidence(
                    claim_text, citations, segment_type
                )

                claims.append(ExtractedClaim(
                    claim_id=claim_id,
                    text=claim_text,
                    segment_type=segment_type,
                    cited_sources=citations,
                    claim_type=claim_type,
                    confidence=confidence,
                ))

        return claims

    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Handle common abbreviations that include periods
        text = re.sub(r'\b(Dr|Mr|Mrs|Ms|Prof|Jr|Sr|vs|etc|e\.g|i\.e)\.',
                      r'\1<PERIOD>', text)

        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)

        # Restore periods in abbreviations
        sentences = [s.replace('<PERIOD>', '.') for s in sentences]

        return [s for s in sentences if s.strip()]

    def _split_long_sentence(self, sentence: str) -> list[str]:
        """Split an overly long sentence into clauses."""
        # Split on conjunctions and semicolons
        parts = re.split(
            r';\s+|,\s+(?:and|but|however|also|additionally|furthermore)\s+',
            sentence
        )

        # Filter and clean parts
        return [p.strip() for p in parts if len(p.strip()) >= self.min_claim_length]

    def _classify_claim_type(self, claim_text: str) -> str:
        """Classify the type of claim."""
        claim_lower = claim_text.lower()

        for claim_type, patterns in self.CLAIM_TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, claim_lower, re.IGNORECASE):
                    return claim_type

        return "factual"

    def _calculate_extraction_confidence(
        self,
        claim_text: str,
        citations: list[str],
        segment_type: str,
    ) -> float:
        """Calculate confidence in claim extraction quality."""
        confidence = 1.0

        # Claims without citations in report_facts are lower confidence
        if segment_type == "report_facts" and not citations:
            confidence *= 0.7

        # Very short claims may be incomplete
        if len(claim_text) < 30:
            confidence *= 0.9

        # Claims with multiple citations are usually well-supported
        if len(citations) >= 2:
            confidence *= 1.1
            confidence = min(confidence, 1.0)  # Cap at 1.0

        # Claims with hedging language are appropriately uncertain
        hedge_patterns = [
            r"\b(may|might|could|possibly|potentially)\b",
            r"\b(suggests|indicates|appears)\b",
        ]
        for pattern in hedge_patterns:
            if re.search(pattern, claim_text, re.IGNORECASE):
                confidence *= 0.95

        return round(confidence, 3)

    def filter_unverifiable_claims(
        self,
        claims: list[ExtractedClaim],
    ) -> tuple[list[ExtractedClaim], list[ExtractedClaim]]:
        """
        Separate claims into verifiable and unverifiable.

        Unverifiable claims include:
        - Pure opinions without citations
        - Meta-statements about the response itself
        - Hedged statements in uncertainty sections

        Returns:
            Tuple of (verifiable_claims, unverifiable_claims)
        """
        verifiable = []
        unverifiable = []

        # Patterns for unverifiable content
        meta_patterns = [
            r"\b(I cannot|I don't have|insufficient information)\b",
            r"\b(based on the provided|according to available)\b",
            r"\b(please consult|speak with your doctor)\b",
        ]

        for claim in claims:
            is_unverifiable = False

            carries_fact = _carries_fact(claim)

            # Uncertainty hedges are unverifiable only when they carry no fact
            # (no citation, no number). UNC-VERIFY-SCOPE (a).
            if claim.segment_type == "uncertainty" and not carries_fact:
                is_unverifiable = True

            # Meta-statements about information availability. A meta phrase never
            # exempts a claim that carries a citation or a number: it still has to
            # be verified.
            for pattern in () if carries_fact else meta_patterns:
                if re.search(pattern, claim.text, re.IGNORECASE):
                    is_unverifiable = True
                    break

            # Claims without citations from report_facts need special handling
            if claim.segment_type == "report_facts" and not claim.cited_sources:
                # Still verifiable but flagged
                claim.verification_notes.append("No citation provided for report fact")

            if is_unverifiable:
                unverifiable.append(claim)
            else:
                verifiable.append(claim)

        return verifiable, unverifiable
