"""
Source Authority Tier system for AI Safety.

Phase 4: Assigns trust levels to different source types
and provides weighted reliability scoring for citations.

Source Authority Tiers:
- Tier 1: User's verified documents (highest for personal data)
- Tier 2: Peer-reviewed medical references
- Tier 3: General medical information/educational content
- Tier 4: Unverified/unknown sources (lowest)
"""

from typing import Optional
from dataclasses import dataclass, field
from enum import IntEnum


class SourceTier(IntEnum):
    """
    Source authority tiers from highest to lowest trust.

    TIER_1: User-verified documents
        - Personal lab results the user has verified
        - User-confirmed medical records
        - Highest authority for claims about "your results"

    TIER_2: Peer-reviewed medical references
        - Published medical literature
        - Clinical guidelines (ACC, AHA, etc.)
        - Reference ranges from authoritative sources

    TIER_3: General medical education
        - Educational materials
        - General health information
        - Non-peer-reviewed but credible sources

    TIER_4: Unverified sources
        - Unknown source type
        - Web content without verification
        - Should be treated with caution
    """
    TIER_1 = 1  # User-verified personal documents
    TIER_2 = 2  # Peer-reviewed references
    TIER_3 = 3  # Educational content
    TIER_4 = 4  # Unverified/unknown


@dataclass
class SourceMetadata:
    """Metadata about a source for authority scoring."""
    source_id: str
    source_type: str  # "user_document", "reference", "glossary"
    title: Optional[str] = None
    doc_id: Optional[str] = None

    # Authority indicators
    is_user_verified: bool = False  # User has verified this document
    is_peer_reviewed: bool = False  # Peer-reviewed publication
    is_official_guideline: bool = False  # Clinical guideline source
    publication_year: Optional[int] = None
    publisher: Optional[str] = None

    # Derived tier (set by SourceAuthorityScorer)
    authority_tier: SourceTier = SourceTier.TIER_4
    authority_score: float = 0.0


@dataclass
class AuthorityConfig:
    """Configuration for source authority scoring."""

    # Base weights for each tier (higher = more trusted)
    tier_weights: dict[SourceTier, float] = field(default_factory=lambda: {
        SourceTier.TIER_1: 1.0,   # User-verified: full trust
        SourceTier.TIER_2: 0.9,   # Peer-reviewed: very high trust
        SourceTier.TIER_3: 0.7,   # Educational: moderate trust
        SourceTier.TIER_4: 0.3,   # Unknown: low trust
    })

    # Claim type modifiers (some claims require higher authority)
    claim_authority_requirements: dict[str, SourceTier] = field(default_factory=lambda: {
        "personal_result": SourceTier.TIER_1,  # "Your glucose is X" requires user doc
        "reference_range": SourceTier.TIER_2,  # Clinical ranges need peer review
        "general_education": SourceTier.TIER_3,  # General info can use educational
        "factual": SourceTier.TIER_3,  # Default requirement
    })

    # Recency boost for recent publications (within N years)
    recency_boost_years: int = 5
    recency_boost_factor: float = 1.1

    # Official guideline boost
    guideline_boost_factor: float = 1.15


class SourceAuthorityScorer:
    """
    Scores sources based on their authority tier and metadata.

    Used by the verifier agent to:
    1. Determine if a source is authoritative enough for a claim type
    2. Weight multiple sources supporting the same claim
    3. Flag claims that lack sufficiently authoritative sources
    """

    # Known authoritative publishers
    PEER_REVIEWED_PUBLISHERS = [
        "nejm", "new england journal",
        "lancet",
        "jama", "journal of the american medical",
        "bmj", "british medical journal",
        "nature", "science",
        "annals of internal medicine",
        "circulation",
        "diabetes care",
        "clinical chemistry",
    ]

    # Known guideline organizations
    GUIDELINE_ORGANIZATIONS = [
        "acc", "american college of cardiology",
        "aha", "american heart association",
        "ada", "american diabetes association",
        "uspstf",
        "nice", "national institute for health",
        "who", "world health organization",
        "cdc", "centers for disease control",
    ]

    def __init__(self, config: Optional[AuthorityConfig] = None):
        """Initialize with optional custom configuration."""
        self.config = config or AuthorityConfig()

    def classify_source(self, metadata: SourceMetadata) -> SourceMetadata:
        """
        Classify a source and assign its authority tier.

        Args:
            metadata: Source metadata to classify

        Returns:
            Updated metadata with tier and score assigned
        """
        # Start with lowest tier
        tier = SourceTier.TIER_4
        score = self.config.tier_weights[SourceTier.TIER_4]

        # User documents
        if metadata.source_type == "user_document":
            if metadata.is_user_verified:
                tier = SourceTier.TIER_1
            else:
                # Unverified user documents are tier 3
                tier = SourceTier.TIER_3

        # Reference materials
        elif metadata.source_type == "reference":
            if metadata.is_peer_reviewed:
                tier = SourceTier.TIER_2
            elif metadata.is_official_guideline:
                tier = SourceTier.TIER_2
            else:
                # Check publisher for known authoritative sources
                if self._is_peer_reviewed_publisher(metadata.publisher):
                    tier = SourceTier.TIER_2
                    metadata.is_peer_reviewed = True
                elif self._is_guideline_org(metadata.publisher):
                    tier = SourceTier.TIER_2
                    metadata.is_official_guideline = True
                else:
                    tier = SourceTier.TIER_3

        # Glossary/educational content
        elif metadata.source_type == "glossary":
            tier = SourceTier.TIER_3

        # Calculate base score from tier
        score = self.config.tier_weights[tier]

        # Apply modifiers
        score = self._apply_modifiers(score, metadata)

        metadata.authority_tier = tier
        metadata.authority_score = round(score, 3)

        return metadata

    def _is_peer_reviewed_publisher(self, publisher: Optional[str]) -> bool:
        """Check if publisher is a known peer-reviewed journal."""
        if not publisher:
            return False

        publisher_lower = publisher.lower()
        return any(p in publisher_lower for p in self.PEER_REVIEWED_PUBLISHERS)

    def _is_guideline_org(self, publisher: Optional[str]) -> bool:
        """Check if publisher is a known guideline organization."""
        if not publisher:
            return False

        publisher_lower = publisher.lower()
        return any(org in publisher_lower for org in self.GUIDELINE_ORGANIZATIONS)

    def _apply_modifiers(
        self,
        base_score: float,
        metadata: SourceMetadata,
    ) -> float:
        """Apply score modifiers based on source attributes."""
        score = base_score

        # Recency boost for recent publications
        if metadata.publication_year:
            from datetime import datetime
            current_year = datetime.now().year
            age = current_year - metadata.publication_year

            if age <= self.config.recency_boost_years:
                score *= self.config.recency_boost_factor

        # Guideline boost
        if metadata.is_official_guideline:
            score *= self.config.guideline_boost_factor

        # Cap at 1.0
        return min(score, 1.0)

    def check_authority_sufficient(
        self,
        sources: list[SourceMetadata],
        claim_type: str,
    ) -> tuple[bool, list[str]]:
        """
        Check if sources are authoritative enough for a claim type.

        Args:
            sources: List of sources cited for a claim
            claim_type: Type of claim being made

        Returns:
            Tuple of (is_sufficient, list of issues)
        """
        issues = []

        if not sources:
            issues.append("No sources provided for claim")
            return False, issues

        required_tier = self.config.claim_authority_requirements.get(
            claim_type, SourceTier.TIER_3
        )

        # Check if any source meets the requirement
        best_tier = min(s.authority_tier for s in sources)

        if best_tier > required_tier:
            tier_names = {
                SourceTier.TIER_1: "user-verified document",
                SourceTier.TIER_2: "peer-reviewed reference",
                SourceTier.TIER_3: "educational source",
                SourceTier.TIER_4: "verified source",
            }
            issues.append(
                f"Claim type '{claim_type}' requires {tier_names[required_tier]}, "
                f"but best available is tier {best_tier.value}"
            )
            return False, issues

        return True, []

    def aggregate_source_score(
        self,
        sources: list[SourceMetadata],
    ) -> float:
        """
        Calculate aggregate authority score for multiple sources.

        Uses weighted combination favoring higher-authority sources.

        Args:
            sources: List of sources to aggregate

        Returns:
            Combined authority score (0.0 - 1.0)
        """
        if not sources:
            return 0.0

        # Weight by authority score with diminishing returns for additional sources
        scores = sorted([s.authority_score for s in sources], reverse=True)

        # First source gets full weight, additional sources add diminishing value
        total = 0.0
        weight = 1.0
        diminish_factor = 0.5

        for score in scores:
            total += score * weight
            weight *= diminish_factor

        # Normalize to 0-1 range
        max_possible = sum(diminish_factor ** i for i in range(len(scores)))
        normalized = total / max_possible if max_possible > 0 else 0.0

        return round(min(normalized, 1.0), 3)


@dataclass
class ClaimAuthorityAnalysis:
    """Result of authority analysis for a claim."""
    claim_id: str
    claim_type: str
    sources: list[SourceMetadata]
    is_authority_sufficient: bool
    aggregate_score: float
    issues: list[str] = field(default_factory=list)
    recommendation: str = ""


def analyze_claim_authority(
    claim_id: str,
    claim_type: str,
    sources: list[SourceMetadata],
    scorer: Optional[SourceAuthorityScorer] = None,
) -> ClaimAuthorityAnalysis:
    """
    Convenience function to analyze authority for a single claim.

    Args:
        claim_id: ID of the claim
        claim_type: Type of claim being made
        sources: Sources cited for this claim
        scorer: SourceAuthorityScorer instance (creates default if None)

    Returns:
        ClaimAuthorityAnalysis with results
    """
    if scorer is None:
        scorer = SourceAuthorityScorer()

    # Classify all sources
    classified_sources = [scorer.classify_source(s) for s in sources]

    # Check if authority is sufficient
    is_sufficient, issues = scorer.check_authority_sufficient(
        classified_sources, claim_type
    )

    # Calculate aggregate score
    aggregate = scorer.aggregate_source_score(classified_sources)

    # Generate recommendation
    if is_sufficient and aggregate >= 0.8:
        recommendation = "Claim is well-supported by authoritative sources"
    elif is_sufficient:
        recommendation = "Claim has adequate source authority"
    elif aggregate >= 0.5:
        recommendation = "Consider adding higher-authority sources for this claim type"
    else:
        recommendation = "Claim requires stronger source support before presentation"

    return ClaimAuthorityAnalysis(
        claim_id=claim_id,
        claim_type=claim_type,
        sources=classified_sources,
        is_authority_sufficient=is_sufficient,
        aggregate_score=aggregate,
        issues=issues,
        recommendation=recommendation,
    )
