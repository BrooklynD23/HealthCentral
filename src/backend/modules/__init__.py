"""
Backend modules for HealthCentral.

Each module handles a specific domain of functionality:
- ingest: Document import and storage
- extract: PDF parsing and data extraction
- normalize: Analyte mapping and unit handling
- verify: Verification workflow
- analytics: Trend calculations and statistics
- rag: Retrieval-augmented generation
- export: Summary and data export generation

Phase 4 AI Safety modules:
- claim_extractor: Parse individual claims from LLM responses
- source_authority: Score source reliability by tier
- verifier_agent: Verify claims against cited sources
- faithfulness: Measure response faithfulness to sources
"""

from .ingest import IngestModule
from .extract import ExtractModule
from .normalize import NormalizeModule
from .verify import VerifyModule
from .analytics import AnalyticsModule
from .rag import RAGModule
from .export import ExportModule

# Phase 4: AI Safety modules
from .claim_extractor import ClaimExtractor, ExtractedClaim, ClaimExtractionResult
from .source_authority import (
    SourceAuthorityScorer,
    SourceMetadata,
    SourceTier,
    ClaimAuthorityAnalysis,
)
from .verifier_agent import (
    VerifierAgent,
    SourceEvidence,
    ClaimVerificationResult,
    VerificationConfig,
    EntailmentLabel,
)
from .faithfulness import (
    FaithfulnessScorer,
    FaithfulnessScores,
    FaithfulnessConfig,
)

__all__ = [
    # Core modules
    "IngestModule",
    "ExtractModule",
    "NormalizeModule",
    "VerifyModule",
    "AnalyticsModule",
    "RAGModule",
    "ExportModule",
    # Phase 4: AI Safety
    "ClaimExtractor",
    "ExtractedClaim",
    "ClaimExtractionResult",
    "SourceAuthorityScorer",
    "SourceMetadata",
    "SourceTier",
    "ClaimAuthorityAnalysis",
    "VerifierAgent",
    "SourceEvidence",
    "ClaimVerificationResult",
    "VerificationConfig",
    "EntailmentLabel",
    "FaithfulnessScorer",
    "FaithfulnessScores",
    "FaithfulnessConfig",
]
