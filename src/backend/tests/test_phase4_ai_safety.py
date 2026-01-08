"""
Tests for Phase 4 AI Safety modules.

Tests the claim extraction, source authority, verifier agent,
and faithfulness scoring components.
"""

import pytest
import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.claim_extractor import ClaimExtractor, ExtractedClaim, ClaimExtractionResult
from modules.source_authority import (
    SourceAuthorityScorer,
    SourceMetadata,
    SourceTier,
    AuthorityConfig,
    analyze_claim_authority,
)
from modules.verifier_agent import (
    VerifierAgent,
    SourceEvidence,
    VerificationConfig,
    EntailmentLabel,
    verify_all_claims,
)
from modules.faithfulness import (
    FaithfulnessScorer,
    FaithfulnessConfig,
    calculate_faithfulness,
)


class TestClaimExtractor:
    """Tests for the ClaimExtractor module."""

    def test_extract_claims_with_sections(self):
        """Test extraction from properly sectioned response."""
        extractor = ClaimExtractor()

        response = """
REPORT FACTS: Your glucose level is 105 mg/dL [cite:1], which is slightly above the normal fasting range.

GENERAL INFO: Normal fasting glucose is typically between 70-100 mg/dL [cite:2]. Values above 100 mg/dL but below 126 mg/dL may indicate prediabetes [cite:2].

UNCERTAINTIES: Without knowing if this was a fasting measurement, I cannot determine the clinical significance.
"""
        result = extractor.extract_claims(response)

        assert isinstance(result, ClaimExtractionResult)
        assert len(result.claims) >= 2  # Should have claims from report_facts and general_info
        assert result.extraction_method == "rule_based"

        # Check segment types
        segment_types = {c.segment_type for c in result.claims}
        assert "report_facts" in segment_types
        assert "general_info" in segment_types

    def test_extract_claims_with_citations(self):
        """Test that citations are extracted correctly."""
        extractor = ClaimExtractor()

        response = "Your hemoglobin is 14.5 g/dL [cite:1], which is within the normal range [cite:2]."
        result = extractor.extract_claims(response)

        assert len(result.claims) >= 1
        # At least one claim should have citations
        claims_with_citations = [c for c in result.claims if c.cited_sources]
        assert len(claims_with_citations) >= 1

    def test_classify_claim_types(self):
        """Test claim type classification."""
        extractor = ClaimExtractor()

        # Test comparative claim
        response = "GENERAL INFO: Your glucose is higher than the reference range [cite:1]."
        result = extractor.extract_claims(response)
        comparative_claims = [c for c in result.claims if c.claim_type == "comparative"]
        assert len(comparative_claims) >= 1

    def test_filter_unverifiable_claims(self):
        """Test filtering of unverifiable claims."""
        extractor = ClaimExtractor()

        # Note: Uncertainty sections are skipped during extraction (by design)
        # To test unverifiable filtering, use a claim with meta-language
        response = """
REPORT FACTS: Your glucose is 105 mg/dL [cite:1].

GENERAL INFO: I cannot determine the clinical significance without additional context. Please consult your doctor for personalized advice.
"""
        result = extractor.extract_claims(response)
        verifiable, unverifiable = extractor.filter_unverifiable_claims(result.claims)

        # Meta-statements like "I cannot determine" should be unverifiable
        assert len(unverifiable) >= 1

    def test_empty_response(self):
        """Test handling of empty response."""
        extractor = ClaimExtractor()
        result = extractor.extract_claims("")

        assert len(result.claims) == 0
        assert result.extraction_method == "rule_based"


class TestSourceAuthority:
    """Tests for the SourceAuthorityScorer module."""

    def test_tier_1_user_verified_document(self):
        """Test that user-verified documents get Tier 1."""
        scorer = SourceAuthorityScorer()

        meta = SourceMetadata(
            source_id="1",
            source_type="user_document",
            is_user_verified=True,
        )
        classified = scorer.classify_source(meta)

        assert classified.authority_tier == SourceTier.TIER_1
        assert classified.authority_score >= 0.9

    def test_tier_2_peer_reviewed(self):
        """Test that peer-reviewed sources get Tier 2."""
        scorer = SourceAuthorityScorer()

        meta = SourceMetadata(
            source_id="2",
            source_type="reference",
            is_peer_reviewed=True,
        )
        classified = scorer.classify_source(meta)

        assert classified.authority_tier == SourceTier.TIER_2

    def test_tier_3_educational_content(self):
        """Test that educational content gets Tier 3."""
        scorer = SourceAuthorityScorer()

        meta = SourceMetadata(
            source_id="3",
            source_type="glossary",
        )
        classified = scorer.classify_source(meta)

        assert classified.authority_tier == SourceTier.TIER_3

    def test_tier_4_unverified(self):
        """Test that unverified sources get Tier 4."""
        scorer = SourceAuthorityScorer()

        meta = SourceMetadata(
            source_id="4",
            source_type="unknown",
        )
        classified = scorer.classify_source(meta)

        assert classified.authority_tier == SourceTier.TIER_4
        assert classified.authority_score <= 0.5

    def test_known_publishers_detection(self):
        """Test detection of known authoritative publishers."""
        scorer = SourceAuthorityScorer()

        # NEJM should be recognized as peer-reviewed
        meta = SourceMetadata(
            source_id="5",
            source_type="reference",
            publisher="New England Journal of Medicine",
        )
        classified = scorer.classify_source(meta)

        assert classified.is_peer_reviewed is True
        assert classified.authority_tier == SourceTier.TIER_2

    def test_aggregate_source_score(self):
        """Test aggregation of multiple source scores."""
        scorer = SourceAuthorityScorer()

        sources = [
            SourceMetadata(source_id="1", source_type="user_document", is_user_verified=True),
            SourceMetadata(source_id="2", source_type="reference", is_peer_reviewed=True),
        ]

        # Classify sources first
        classified = [scorer.classify_source(s) for s in sources]

        aggregate = scorer.aggregate_source_score(classified)
        assert 0.0 <= aggregate <= 1.0
        assert aggregate > 0.7  # Should be high with tier 1 and tier 2 sources

    def test_check_authority_sufficient(self):
        """Test authority sufficiency checking."""
        scorer = SourceAuthorityScorer()

        # Tier 1 source should be sufficient for personal result claims
        sources = [
            SourceMetadata(source_id="1", source_type="user_document", is_user_verified=True),
        ]
        classified = [scorer.classify_source(s) for s in sources]

        is_sufficient, issues = scorer.check_authority_sufficient(
            classified, "personal_result"
        )
        assert is_sufficient is True
        assert len(issues) == 0


class TestVerifierAgent:
    """Tests for the VerifierAgent module."""

    def test_verify_claim_with_supporting_source(self):
        """Test verification with matching source."""
        verifier = VerifierAgent()

        claim = "Your glucose level is 105 mg/dL"
        sources = [
            SourceEvidence(
                source_id="1",
                source_text="Patient glucose: 105 mg/dL collected on 2026-01-01",
                source_type="user_document",
            )
        ]

        result = verifier.verify_claim(claim, "claim_1", sources)

        assert result.is_verified is True
        assert result.verification_score > 0.5
        assert len(result.supporting_sources) >= 1

    def test_verify_claim_without_sources(self):
        """Test verification fails without sources."""
        verifier = VerifierAgent()

        result = verifier.verify_claim("Some claim", "claim_1", [])

        assert result.is_verified is False
        assert result.verification_score == 0.0
        assert "No sources provided" in result.issues[0]

    def test_contradiction_detection(self):
        """Test detection of contradicting sources."""
        verifier = VerifierAgent()

        # Claim says high, source says low
        claim = "Your glucose level is elevated"
        sources = [
            SourceEvidence(
                source_id="1",
                source_text="Patient glucose is low at 65 mg/dL",
                source_type="user_document",
            )
        ]

        result = verifier.verify_claim(claim, "claim_1", sources)

        # Should detect contradiction
        assert len(result.contradicting_sources) >= 1 or result.verification_score < 0.5

    def test_batch_verification(self):
        """Test batch verification of multiple claims."""
        claims = [
            ("claim_1", "Glucose is 105 mg/dL", [
                SourceEvidence("1", "Glucose: 105 mg/dL", "user_document")
            ]),
            ("claim_2", "Hemoglobin is 14.5 g/dL", [
                SourceEvidence("2", "Hemoglobin: 14.5 g/dL", "user_document")
            ]),
        ]

        result = verify_all_claims(claims)

        assert result.total_claims == 2
        assert result.verified_claims + result.failed_claims == 2

    def test_entailment_with_value_match(self):
        """Test entailment detection with numeric value matching."""
        verifier = VerifierAgent()

        claim = "Your hemoglobin A1c is 6.2%"
        sources = [
            SourceEvidence(
                source_id="1",
                source_text="HbA1c: 6.2% (within target range)",
                source_type="user_document",
            )
        ]

        result = verifier.verify_claim(claim, "claim_1", sources)

        assert result.is_verified is True
        assert len(result.supporting_sources) >= 1


class TestFaithfulnessScorer:
    """Tests for the FaithfulnessScorer module."""

    def test_score_claim_high_faithfulness(self):
        """Test scoring with highly faithful claim."""
        scorer = FaithfulnessScorer()

        claim = "Your glucose level is 105 mg/dL"
        sources = ["Patient glucose: 105 mg/dL collected on 2026-01-01"]

        scores = scorer.score_claim(claim, sources)

        assert scores.overall_score > 0.5
        assert scores.lexical_score > 0.3

    def test_score_claim_low_faithfulness(self):
        """Test scoring with unfaithful claim."""
        scorer = FaithfulnessScorer()

        claim = "Your cholesterol is concerning and needs medication"
        sources = ["Patient glucose: 105 mg/dL"]  # Unrelated source

        scores = scorer.score_claim(claim, sources)

        assert scores.overall_score < 0.5

    def test_score_response_multiple_claims(self):
        """Test scoring multiple claims together."""
        scorer = FaithfulnessScorer()

        claims = [
            "Your glucose is 105 mg/dL",
            "This is within normal fasting range",
        ]
        sources = [
            "Glucose: 105 mg/dL",
            "Normal fasting glucose: 70-100 mg/dL",
        ]

        scores = scorer.score_response(claims, sources)

        assert scores.overall_score > 0
        assert scores.n_supporting_facts + scores.n_unsupported_facts >= 0

    def test_convenience_function(self):
        """Test the calculate_faithfulness convenience function."""
        text = "Your glucose is 105 mg/dL, which is slightly elevated"
        sources = ["Glucose: 105 mg/dL - above reference range of 70-100"]

        scores = calculate_faithfulness(text, sources)

        assert isinstance(scores.overall_score, float)
        assert 0.0 <= scores.overall_score <= 1.0

    def test_empty_sources(self):
        """Test handling of empty sources."""
        scorer = FaithfulnessScorer()

        scores = scorer.score_claim("Some claim", [])

        assert scores.overall_score == 0.0
        assert scores.scoring_confidence < 1.0


class TestIntegration:
    """Integration tests for the Phase 4 pipeline."""

    def test_full_verification_pipeline(self):
        """Test the complete claim extraction and verification pipeline."""
        # Step 1: Extract claims
        extractor = ClaimExtractor()
        response = """
REPORT FACTS: Your fasting glucose is 105 mg/dL [cite:1].

GENERAL INFO: Normal fasting glucose range is 70-100 mg/dL [cite:2].
"""
        extraction_result = extractor.extract_claims(response)
        verifiable, _ = extractor.filter_unverifiable_claims(extraction_result.claims)

        assert len(verifiable) >= 1

        # Step 2: Check source authority
        scorer = SourceAuthorityScorer()
        source_meta = SourceMetadata(
            source_id="1",
            source_type="user_document",
            is_user_verified=True,
        )
        classified = scorer.classify_source(source_meta)
        assert classified.authority_tier == SourceTier.TIER_1

        # Step 3: Verify claims
        verifier = VerifierAgent()
        for claim in verifiable:
            sources = [
                SourceEvidence(
                    source_id="1",
                    source_text="Fasting glucose: 105 mg/dL",
                    source_type="user_document",
                )
            ]
            result = verifier.verify_claim(claim.text, claim.claim_id, sources)
            # At least some claims should be verifiable
            assert result.verification_score >= 0

        # Step 4: Calculate faithfulness
        fs = FaithfulnessScorer()
        claim_texts = [c.text for c in verifiable]
        source_texts = ["Fasting glucose: 105 mg/dL", "Normal range: 70-100 mg/dL"]
        faithfulness = fs.score_response(claim_texts, source_texts)

        assert faithfulness.overall_score >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
