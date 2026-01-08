"""
Faithfulness Scoring module for AI Safety.

Phase 4: Implements comprehensive faithfulness metrics to measure
how well LLM-generated claims are grounded in source evidence.

Faithfulness scoring combines:
1. Entailment-based scoring (NLI)
2. Lexical faithfulness (n-gram overlap)
3. Semantic faithfulness (embedding similarity)
4. Consistency checking (multiple generation passes)
"""

from typing import Optional
from dataclasses import dataclass, field
import re
import math


@dataclass
class FaithfulnessScores:
    """Collection of faithfulness metrics for a claim or response."""

    # Overall composite score (0.0 - 1.0)
    overall_score: float

    # Component scores
    entailment_score: float  # NLI-based entailment ratio
    lexical_score: float     # Token/n-gram overlap
    semantic_score: float    # Embedding similarity (when available)
    consistency_score: float # Multi-pass consistency (when enabled)

    # Detailed breakdown
    n_supporting_facts: int
    n_contradicting_facts: int
    n_unsupported_facts: int

    # Confidence in the scoring
    scoring_confidence: float

    # Issues detected
    issues: list[str] = field(default_factory=list)


@dataclass
class FaithfulnessConfig:
    """Configuration for faithfulness scoring."""

    # Component weights (must sum to 1.0)
    entailment_weight: float = 0.5
    lexical_weight: float = 0.3
    semantic_weight: float = 0.2

    # Thresholds
    min_overall_score: float = 0.6  # Below this, flag as unfaithful
    high_faithfulness_threshold: float = 0.85  # Above this, highly faithful

    # Lexical scoring parameters
    ngram_sizes: list[int] = field(default_factory=lambda: [1, 2, 3])
    min_ngram_overlap: float = 0.3

    # Semantic similarity threshold
    min_semantic_similarity: float = 0.7

    # Consistency checking
    enable_consistency_check: bool = False
    consistency_passes: int = 3
    consistency_threshold: float = 0.8


class FaithfulnessScorer:
    """
    Calculates faithfulness scores for generated text.

    Measures how well generated claims are grounded in source evidence
    using multiple complementary metrics.
    """

    def __init__(self, config: Optional[FaithfulnessConfig] = None):
        """Initialize faithfulness scorer."""
        self.config = config or FaithfulnessConfig()

        # Validate weights sum to 1.0
        total_weight = (
            self.config.entailment_weight +
            self.config.lexical_weight +
            self.config.semantic_weight
        )
        if not math.isclose(total_weight, 1.0, rel_tol=0.01):
            # Normalize weights
            self.config.entailment_weight /= total_weight
            self.config.lexical_weight /= total_weight
            self.config.semantic_weight /= total_weight

    def score_claim(
        self,
        claim: str,
        source_texts: list[str],
        entailment_scores: Optional[list[float]] = None,
        embedding_similarity: Optional[float] = None,
    ) -> FaithfulnessScores:
        """
        Calculate faithfulness scores for a single claim.

        Args:
            claim: The generated claim to score
            source_texts: List of source texts the claim should be grounded in
            entailment_scores: Optional pre-computed entailment scores per source
            embedding_similarity: Optional pre-computed embedding similarity

        Returns:
            FaithfulnessScores with all metrics
        """
        issues = []

        # Calculate entailment score
        if entailment_scores:
            entailment_score = self._aggregate_entailment_scores(entailment_scores)
        else:
            # Fall back to lexical-based pseudo-entailment
            entailment_score = self._calculate_pseudo_entailment(claim, source_texts)

        # Calculate lexical faithfulness
        lexical_score = self._calculate_lexical_faithfulness(claim, source_texts)

        # Calculate semantic faithfulness
        if embedding_similarity is not None:
            semantic_score = embedding_similarity
        else:
            # No embeddings available - use 0 but don't penalize
            semantic_score = self._estimate_semantic_score(claim, source_texts)

        # Calculate consistency score (placeholder - needs multi-pass data)
        consistency_score = 1.0  # Default to 1.0 if not checking consistency

        # Compute weighted overall score
        overall_score = (
            self.config.entailment_weight * entailment_score +
            self.config.lexical_weight * lexical_score +
            self.config.semantic_weight * semantic_score
        )

        # Count fact categories
        n_supporting, n_contradicting, n_unsupported = self._categorize_facts(
            claim, source_texts, entailment_score, lexical_score
        )

        # Identify issues
        if overall_score < self.config.min_overall_score:
            issues.append(f"Low faithfulness score: {overall_score:.2f}")

        if lexical_score < self.config.min_ngram_overlap:
            issues.append(f"Low lexical overlap with sources: {lexical_score:.2f}")

        if entailment_score < 0.5:
            issues.append(f"Weak entailment from sources: {entailment_score:.2f}")

        # Calculate scoring confidence based on data availability
        scoring_confidence = self._calculate_scoring_confidence(
            has_entailment=entailment_scores is not None,
            has_embeddings=embedding_similarity is not None,
            source_count=len(source_texts),
        )

        return FaithfulnessScores(
            overall_score=round(overall_score, 3),
            entailment_score=round(entailment_score, 3),
            lexical_score=round(lexical_score, 3),
            semantic_score=round(semantic_score, 3),
            consistency_score=round(consistency_score, 3),
            n_supporting_facts=n_supporting,
            n_contradicting_facts=n_contradicting,
            n_unsupported_facts=n_unsupported,
            scoring_confidence=round(scoring_confidence, 3),
            issues=issues,
        )

    def _aggregate_entailment_scores(self, scores: list[float]) -> float:
        """Aggregate multiple entailment scores into single score."""
        if not scores:
            return 0.0

        # Use max-based aggregation (if any source supports, claim is supported)
        # But penalize if some sources contradict
        max_support = max(scores)
        avg_support = sum(scores) / len(scores)

        # Combine max and average for balanced score
        return 0.6 * max_support + 0.4 * avg_support

    def _calculate_pseudo_entailment(
        self,
        claim: str,
        source_texts: list[str],
    ) -> float:
        """Calculate pseudo-entailment using lexical and pattern matching."""
        if not source_texts:
            return 0.0

        combined_sources = " ".join(source_texts)

        # Extract key entities and values from claim
        claim_entities = self._extract_key_entities(claim)
        source_entities = self._extract_key_entities(combined_sources)

        if not claim_entities:
            # No specific entities - use general overlap
            return self._calculate_lexical_faithfulness(claim, source_texts)

        # Calculate entity coverage
        matched = sum(1 for e in claim_entities if self._entity_in_text(e, combined_sources))
        coverage = matched / len(claim_entities) if claim_entities else 0.0

        return coverage

    def _extract_key_entities(self, text: str) -> list[str]:
        """Extract key entities (values, medical terms) from text."""
        entities = []

        # Extract numeric values with units
        value_pattern = r'\b(\d+(?:\.\d+)?)\s*(mg|g|mmol|µmol|ml|L|%|mg/dL|mmol/L|IU/L|U/L)\b'
        values = re.findall(value_pattern, text, re.IGNORECASE)
        entities.extend([f"{v[0]} {v[1]}" for v in values])

        # Extract standalone numbers that might be values
        standalone_nums = re.findall(r'\b(\d+(?:\.\d+)?)\b', text)
        # Only include if they're in a relevant context
        for num in standalone_nums:
            if float(num) not in [0, 1]:  # Skip trivial numbers
                entities.append(num)

        # Extract potential medical terms (capitalized multi-word)
        medical_terms = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', text)
        entities.extend(medical_terms)

        return list(set(entities))

    def _entity_in_text(self, entity: str, text: str) -> bool:
        """Check if entity appears in text (with fuzzy matching for values)."""
        entity_lower = entity.lower()
        text_lower = text.lower()

        # Direct match
        if entity_lower in text_lower:
            return True

        # For numeric values, check with tolerance
        try:
            entity_value = float(entity.split()[0])
            # Look for similar values in text
            text_values = re.findall(r'\b(\d+(?:\.\d+)?)\b', text)
            for tv in text_values:
                if abs(float(tv) - entity_value) < entity_value * 0.05:  # 5% tolerance
                    return True
        except (ValueError, IndexError):
            pass

        return False

    def _calculate_lexical_faithfulness(
        self,
        claim: str,
        source_texts: list[str],
    ) -> float:
        """Calculate lexical faithfulness using n-gram overlap."""
        if not source_texts:
            return 0.0

        combined_sources = " ".join(source_texts)
        scores = []

        for n in self.config.ngram_sizes:
            claim_ngrams = self._get_ngrams(claim, n)
            source_ngrams = self._get_ngrams(combined_sources, n)

            if not claim_ngrams:
                continue

            overlap = len(claim_ngrams & source_ngrams)
            precision = overlap / len(claim_ngrams) if claim_ngrams else 0.0
            scores.append(precision)

        if not scores:
            return 0.0

        # Weight higher n-grams more (they're more specific)
        weighted = sum(s * (i + 1) for i, s in enumerate(scores))
        total_weight = sum(i + 1 for i in range(len(scores)))

        return weighted / total_weight if total_weight > 0 else 0.0

    def _get_ngrams(self, text: str, n: int) -> set[tuple]:
        """Extract n-grams from text."""
        # Tokenize
        tokens = re.findall(r'\b\w+\b', text.lower())

        # Remove stopwords for cleaner n-grams
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be',
                     'been', 'of', 'in', 'to', 'for', 'with', 'on', 'at',
                     'by', 'and', 'or', 'but', 'this', 'that'}

        tokens = [t for t in tokens if t not in stopwords]

        if len(tokens) < n:
            return set()

        return set(tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1))

    def _estimate_semantic_score(
        self,
        claim: str,
        source_texts: list[str],
    ) -> float:
        """Estimate semantic score without embeddings."""
        # Use lexical score as a rough proxy
        lexical = self._calculate_lexical_faithfulness(claim, source_texts)

        # Boost slightly if there's significant overlap (indicating semantic similarity)
        if lexical > 0.5:
            return min(1.0, lexical * 1.2)
        else:
            return lexical * 0.8

    def _categorize_facts(
        self,
        claim: str,
        source_texts: list[str],
        entailment_score: float,
        lexical_score: float,
    ) -> tuple[int, int, int]:
        """Categorize facts as supporting, contradicting, or unsupported."""
        # Simplified categorization based on overall scores
        # In a full implementation, this would analyze individual facts

        avg_score = (entailment_score + lexical_score) / 2

        if avg_score >= 0.7:
            return (1, 0, 0)  # Supporting
        elif avg_score >= 0.4:
            return (0, 0, 1)  # Unsupported
        else:
            return (0, 1, 0)  # Potentially contradicting

    def _calculate_scoring_confidence(
        self,
        has_entailment: bool,
        has_embeddings: bool,
        source_count: int,
    ) -> float:
        """Calculate confidence in the faithfulness scoring."""
        confidence = 0.5  # Base confidence

        if has_entailment:
            confidence += 0.2
        if has_embeddings:
            confidence += 0.2
        if source_count >= 2:
            confidence += 0.1

        return min(1.0, confidence)

    def score_response(
        self,
        claims: list[str],
        source_texts: list[str],
        per_claim_entailment: Optional[list[list[float]]] = None,
    ) -> FaithfulnessScores:
        """
        Calculate faithfulness scores for an entire response.

        Aggregates scores across multiple claims.

        Args:
            claims: List of claims from the response
            source_texts: Source texts for grounding
            per_claim_entailment: Optional entailment scores per claim

        Returns:
            Aggregated FaithfulnessScores
        """
        if not claims:
            return FaithfulnessScores(
                overall_score=0.0,
                entailment_score=0.0,
                lexical_score=0.0,
                semantic_score=0.0,
                consistency_score=0.0,
                n_supporting_facts=0,
                n_contradicting_facts=0,
                n_unsupported_facts=0,
                scoring_confidence=0.0,
                issues=["No claims to score"],
            )

        # Score each claim
        claim_scores = []
        for i, claim in enumerate(claims):
            entailment = per_claim_entailment[i] if per_claim_entailment else None
            score = self.score_claim(claim, source_texts, entailment)
            claim_scores.append(score)

        # Aggregate scores
        return self._aggregate_claim_scores(claim_scores)

    def _aggregate_claim_scores(
        self,
        claim_scores: list[FaithfulnessScores],
    ) -> FaithfulnessScores:
        """Aggregate individual claim scores into response-level scores."""
        n = len(claim_scores)

        # Average component scores
        overall = sum(s.overall_score for s in claim_scores) / n
        entailment = sum(s.entailment_score for s in claim_scores) / n
        lexical = sum(s.lexical_score for s in claim_scores) / n
        semantic = sum(s.semantic_score for s in claim_scores) / n
        consistency = sum(s.consistency_score for s in claim_scores) / n
        confidence = sum(s.scoring_confidence for s in claim_scores) / n

        # Sum fact counts
        supporting = sum(s.n_supporting_facts for s in claim_scores)
        contradicting = sum(s.n_contradicting_facts for s in claim_scores)
        unsupported = sum(s.n_unsupported_facts for s in claim_scores)

        # Collect all issues
        all_issues = []
        for s in claim_scores:
            all_issues.extend(s.issues)

        # Add summary issues if needed
        if overall < self.config.min_overall_score:
            all_issues.append(f"Response overall faithfulness ({overall:.2f}) below threshold")

        if contradicting > 0:
            all_issues.append(f"{contradicting} claim(s) may contradict sources")

        return FaithfulnessScores(
            overall_score=round(overall, 3),
            entailment_score=round(entailment, 3),
            lexical_score=round(lexical, 3),
            semantic_score=round(semantic, 3),
            consistency_score=round(consistency, 3),
            n_supporting_facts=supporting,
            n_contradicting_facts=contradicting,
            n_unsupported_facts=unsupported,
            scoring_confidence=round(confidence, 3),
            issues=list(set(all_issues)),  # Deduplicate
        )


def calculate_faithfulness(
    generated_text: str,
    source_texts: list[str],
    config: Optional[FaithfulnessConfig] = None,
) -> FaithfulnessScores:
    """
    Convenience function to calculate faithfulness for generated text.

    Args:
        generated_text: The LLM-generated text to evaluate
        source_texts: Source texts that should ground the generation
        config: Optional scoring configuration

    Returns:
        FaithfulnessScores with all metrics
    """
    scorer = FaithfulnessScorer(config)
    return scorer.score_claim(generated_text, source_texts)
