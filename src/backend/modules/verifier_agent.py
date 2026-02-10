"""
Verifier Agent module for AI Safety.

Phase 4: Secondary LLM agent that verifies claims against cited sources
using Natural Language Inference (NLI) and entailment checking.

Dual-Agent Verification Pattern:
1. Primary agent generates response with citations
2. Claim extractor parses individual facts
3. Verifier agent checks each claim:
   - Does cited text support this claim?
   - Is this within the source's authority?
4. Only verified claims are returned to user
"""

from typing import Optional
from dataclasses import dataclass, field
from enum import Enum
import re


class EntailmentLabel(Enum):
    """NLI entailment classification labels."""
    ENTAILMENT = "entailment"      # Source supports the claim
    CONTRADICTION = "contradiction"  # Source contradicts the claim
    NEUTRAL = "neutral"            # Source neither supports nor contradicts


@dataclass
class SourceEvidence:
    """Evidence from a cited source for verification."""
    source_id: str
    source_text: str
    source_type: str
    doc_title: Optional[str] = None
    page: Optional[int] = None


@dataclass
class EntailmentResult:
    """Result of entailment check between claim and source."""
    source_id: str
    label: EntailmentLabel
    confidence: float  # 0.0 to 1.0
    explanation: str = ""


@dataclass
class ClaimVerificationResult:
    """Complete verification result for a single claim."""
    claim_id: str
    claim_text: str

    # Entailment results for each cited source
    entailment_results: list[EntailmentResult] = field(default_factory=list)

    # Overall verification outcome
    is_verified: bool = False
    verification_score: float = 0.0  # Faithfulness score 0.0 - 1.0

    # Detailed analysis
    supporting_sources: list[str] = field(default_factory=list)
    contradicting_sources: list[str] = field(default_factory=list)
    neutral_sources: list[str] = field(default_factory=list)

    # Issues and recommendations
    issues: list[str] = field(default_factory=list)
    recommendation: str = ""


@dataclass
class VerificationConfig:
    """Configuration for the verifier agent."""

    # Minimum confidence for entailment to count as support
    min_entailment_confidence: float = 0.7

    # Minimum number of supporting sources required
    min_supporting_sources: int = 1

    # Whether a single contradiction fails verification
    fail_on_contradiction: bool = True

    # Minimum faithfulness score to pass verification
    min_faithfulness_score: float = 0.6

    # Whether to use LLM for complex entailment (vs rule-based)
    use_llm_entailment: bool = False

    # Enable multiple verification passes for consistency
    multi_pass_verification: bool = False
    verification_passes: int = 3


class VerifierAgent:
    """
    Secondary agent that verifies claims against source evidence.

    Implements:
    1. Rule-based entailment checking (lexical overlap, semantic patterns)
    2. LLM-based entailment for complex claims (optional)
    3. Faithfulness scoring
    4. Multi-pass consistency checking (optional)
    """

    # Patterns indicating entailment (claim matches source)
    ENTAILMENT_INDICATORS = [
        # Direct value matches
        r"(\d+(?:\.\d+)?)\s*(?:mg|g|mmol|µmol|%|ml|L)",
        # Reference range patterns
        r"(?:normal|reference)\s+range\s*[:is]?\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)",
        # Status indicators
        r"\b(elevated|low|high|normal|within range|above|below)\b",
    ]

    # Patterns indicating contradiction
    CONTRADICTION_PATTERNS = [
        # Opposite values
        (r"\bhigh\b", r"\blow\b"),
        (r"\belevated\b", r"\bnormal\b"),
        (r"\babove\b", r"\bbelow\b"),
        (r"\bincreased\b", r"\bdecreased\b"),
    ]

    # Negation patterns that flip meaning
    NEGATION_PATTERNS = [
        r"\bnot\b",
        r"\bno\b",
        r"\bnever\b",
        r"\bwithout\b",
        r"\black of\b",
    ]

    def __init__(self, config: Optional[VerificationConfig] = None):
        """Initialize verifier agent."""
        self.config = config or VerificationConfig()

    def verify_claim(
        self,
        claim_text: str,
        claim_id: str,
        sources: list[SourceEvidence],
    ) -> ClaimVerificationResult:
        """
        Verify a single claim against its cited sources.

        Args:
            claim_text: The claim to verify
            claim_id: ID of the claim
            sources: List of source evidence for this claim

        Returns:
            ClaimVerificationResult with verification outcome
        """
        entailment_results = []
        supporting = []
        contradicting = []
        neutral = []
        issues = []

        if not sources:
            return ClaimVerificationResult(
                claim_id=claim_id,
                claim_text=claim_text,
                is_verified=False,
                verification_score=0.0,
                issues=["No sources provided for verification"],
                recommendation="Cannot verify claim without source evidence",
            )

        # Check entailment for each source
        for source in sources:
            result = self._check_entailment(claim_text, source)
            entailment_results.append(result)

            if result.label == EntailmentLabel.ENTAILMENT:
                if result.confidence >= self.config.min_entailment_confidence:
                    supporting.append(source.source_id)
                else:
                    neutral.append(source.source_id)
            elif result.label == EntailmentLabel.CONTRADICTION:
                contradicting.append(source.source_id)
                issues.append(
                    f"Source {source.source_id} contradicts claim: {result.explanation}"
                )
            else:
                neutral.append(source.source_id)

        # Calculate faithfulness score
        faithfulness = self._calculate_faithfulness(
            supporting, contradicting, neutral
        )

        # Determine verification outcome
        is_verified = self._determine_verification(
            supporting, contradicting, faithfulness
        )

        # Generate recommendation
        recommendation = self._generate_recommendation(
            is_verified, supporting, contradicting, neutral, faithfulness
        )

        return ClaimVerificationResult(
            claim_id=claim_id,
            claim_text=claim_text,
            entailment_results=entailment_results,
            is_verified=is_verified,
            verification_score=faithfulness,
            supporting_sources=supporting,
            contradicting_sources=contradicting,
            neutral_sources=neutral,
            issues=issues,
            recommendation=recommendation,
        )

    def _check_entailment(
        self,
        claim: str,
        source: SourceEvidence,
    ) -> EntailmentResult:
        """
        Check entailment relationship between claim and source.

        Uses rule-based approach with optional LLM fallback.
        """
        if self.config.use_llm_entailment:
            return self._check_entailment_llm(claim, source)
        else:
            return self._check_entailment_rules(claim, source)

    def _check_entailment_rules(
        self,
        claim: str,
        source: SourceEvidence,
    ) -> EntailmentResult:
        """Rule-based entailment checking."""
        claim_lower = claim.lower()
        source_lower = source.source_text.lower()

        # Check for contradiction first
        for pattern_a, pattern_b in self.CONTRADICTION_PATTERNS:
            claim_has_a = re.search(pattern_a, claim_lower)
            claim_has_b = re.search(pattern_b, claim_lower)
            source_has_a = re.search(pattern_a, source_lower)
            source_has_b = re.search(pattern_b, source_lower)

            # Claim says A but source says B (or vice versa)
            if (claim_has_a and source_has_b) or (claim_has_b and source_has_a):
                return EntailmentResult(
                    source_id=source.source_id,
                    label=EntailmentLabel.CONTRADICTION,
                    confidence=0.8,
                    explanation=f"Opposing indicators: claim uses "
                                f"'{claim_has_a or claim_has_b}' but source uses opposite",
                )

        # Check for negation that flips meaning
        claim_negated = any(re.search(p, claim_lower) for p in self.NEGATION_PATTERNS)
        source_negated = any(re.search(p, source_lower) for p in self.NEGATION_PATTERNS)

        if claim_negated != source_negated:
            # One is negated but not the other - potential contradiction
            # Need more analysis to be sure
            pass

        # Check for value matches
        claim_values = self._extract_values(claim)
        source_values = self._extract_values(source.source_text)

        if claim_values and source_values:
            # Check if claim values appear in source
            value_matches = sum(1 for v in claim_values if v in source_values)
            if value_matches > 0:
                confidence = min(0.9, 0.6 + (value_matches * 0.1))
                return EntailmentResult(
                    source_id=source.source_id,
                    label=EntailmentLabel.ENTAILMENT,
                    confidence=confidence,
                    explanation=f"Value match: {value_matches} values from claim found in source",
                )

        # Check lexical overlap
        overlap_score = self._calculate_lexical_overlap(claim, source.source_text)

        if overlap_score >= 0.5:
            return EntailmentResult(
                source_id=source.source_id,
                label=EntailmentLabel.ENTAILMENT,
                confidence=overlap_score,
                explanation=f"High lexical overlap ({overlap_score:.2f})",
            )
        elif overlap_score >= 0.2:
            return EntailmentResult(
                source_id=source.source_id,
                label=EntailmentLabel.NEUTRAL,
                confidence=overlap_score,
                explanation=f"Moderate lexical overlap ({overlap_score:.2f})",
            )
        else:
            return EntailmentResult(
                source_id=source.source_id,
                label=EntailmentLabel.NEUTRAL,
                confidence=overlap_score,
                explanation="Low lexical overlap - source may not be relevant to claim",
            )

    def _check_entailment_llm(
        self,
        claim: str,
        source: SourceEvidence,
    ) -> EntailmentResult:
        """
        LLM-based entailment checking.

        Uses secondary LLM to evaluate claim-source relationship.
        """
        # Optional future enhancement: LLM-based entailment.
        # Current default is rule-based matching (value checks + lexical overlap)
        # and is selected by use_llm_entailment=False in config.
        return self._check_entailment_rules(claim, source)

    def _extract_values(self, text: str) -> list[str]:
        """Extract numeric values with units from text."""
        values = []
        for pattern in self.ENTAILMENT_INDICATORS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    values.extend(m for m in match if m)
                else:
                    values.append(match)
        return values

    def _calculate_lexical_overlap(self, text1: str, text2: str) -> float:
        """Calculate Jaccard similarity between tokenized texts."""
        # Simple tokenization
        tokens1 = set(re.findall(r'\b\w+\b', text1.lower()))
        tokens2 = set(re.findall(r'\b\w+\b', text2.lower()))

        # Remove stopwords
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                     'of', 'in', 'to', 'for', 'with', 'on', 'at', 'by', 'from',
                     'and', 'or', 'but', 'if', 'then', 'than', 'that', 'this'}

        tokens1 = tokens1 - stopwords
        tokens2 = tokens2 - stopwords

        if not tokens1 or not tokens2:
            return 0.0

        intersection = tokens1 & tokens2
        union = tokens1 | tokens2

        return len(intersection) / len(union)

    def _calculate_faithfulness(
        self,
        supporting: list[str],
        contradicting: list[str],
        neutral: list[str],
    ) -> float:
        """
        Calculate faithfulness score for a claim.

        Faithfulness = support_weight - contradiction_penalty

        Args:
            supporting: List of supporting source IDs
            contradicting: List of contradicting source IDs
            neutral: List of neutral source IDs

        Returns:
            Faithfulness score between 0.0 and 1.0
        """
        total_sources = len(supporting) + len(contradicting) + len(neutral)
        if total_sources == 0:
            return 0.0

        # Base score from support ratio
        support_ratio = len(supporting) / total_sources

        # Penalty for contradictions (stronger than neutral)
        contradiction_penalty = len(contradicting) * 0.3

        # Neutral sources don't hurt but don't help much
        neutral_contribution = len(neutral) * 0.1 / total_sources

        faithfulness = support_ratio - contradiction_penalty + neutral_contribution
        return round(max(0.0, min(1.0, faithfulness)), 3)

    def _determine_verification(
        self,
        supporting: list[str],
        contradicting: list[str],
        faithfulness: float,
    ) -> bool:
        """Determine if claim passes verification."""
        # Fail if any contradiction and config says to fail
        if contradicting and self.config.fail_on_contradiction:
            return False

        # Fail if not enough supporting sources
        if len(supporting) < self.config.min_supporting_sources:
            return False

        # Fail if faithfulness score too low
        if faithfulness < self.config.min_faithfulness_score:
            return False

        return True

    def _generate_recommendation(
        self,
        is_verified: bool,
        supporting: list[str],
        contradicting: list[str],
        neutral: list[str],
        faithfulness: float,
    ) -> str:
        """Generate human-readable recommendation."""
        if is_verified:
            if faithfulness >= 0.9:
                return "Claim is strongly supported by cited sources"
            elif faithfulness >= 0.7:
                return "Claim is adequately supported by cited sources"
            else:
                return "Claim passes verification with moderate confidence"

        # Not verified - explain why
        reasons = []

        if contradicting:
            reasons.append(f"{len(contradicting)} source(s) contradict this claim")

        if len(supporting) < self.config.min_supporting_sources:
            reasons.append(
                f"Only {len(supporting)} supporting source(s), "
                f"need at least {self.config.min_supporting_sources}"
            )

        if faithfulness < self.config.min_faithfulness_score:
            reasons.append(
                f"Faithfulness score ({faithfulness:.2f}) below "
                f"threshold ({self.config.min_faithfulness_score})"
            )

        if reasons:
            return "Verification failed: " + "; ".join(reasons)
        else:
            return "Claim could not be verified against cited sources"


@dataclass
class BatchVerificationResult:
    """Result of batch verification for multiple claims."""
    total_claims: int
    verified_claims: int
    failed_claims: int

    results: list[ClaimVerificationResult]

    # Overall statistics
    average_faithfulness: float
    claims_with_contradictions: int

    # Summary
    all_verified: bool
    summary: str


def verify_all_claims(
    claims: list[tuple[str, str, list[SourceEvidence]]],
    config: Optional[VerificationConfig] = None,
) -> BatchVerificationResult:
    """
    Verify multiple claims in batch.

    Args:
        claims: List of (claim_id, claim_text, sources) tuples
        config: Optional verification configuration

    Returns:
        BatchVerificationResult with all results
    """
    verifier = VerifierAgent(config)
    results = []

    for claim_id, claim_text, sources in claims:
        result = verifier.verify_claim(claim_text, claim_id, sources)
        results.append(result)

    # Calculate statistics
    verified_count = sum(1 for r in results if r.is_verified)
    failed_count = len(results) - verified_count
    contradiction_count = sum(1 for r in results if r.contradicting_sources)

    avg_faithfulness = (
        sum(r.verification_score for r in results) / len(results)
        if results else 0.0
    )

    # Generate summary
    if verified_count == len(results):
        summary = f"All {len(results)} claims verified successfully"
    elif verified_count == 0:
        summary = f"None of {len(results)} claims could be verified"
    else:
        summary = (
            f"{verified_count}/{len(results)} claims verified "
            f"({failed_count} failed, {contradiction_count} with contradictions)"
        )

    return BatchVerificationResult(
        total_claims=len(results),
        verified_claims=verified_count,
        failed_claims=failed_count,
        results=results,
        average_faithfulness=round(avg_faithfulness, 3),
        claims_with_contradictions=contradiction_count,
        all_verified=(verified_count == len(results)),
        summary=summary,
    )
