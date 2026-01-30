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

Phase 1 Lab Interpretation modules:
- interpret: Main interpretation pipeline orchestrator
- interpret_safety: Safety guardrails for interpretations
- recommend: Evidence-based recommendation engine
- knowledge_loader: Knowledge base data access
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

# Phase 1: Lab Interpretation modules
from .interpret import (
    InterpretModule,
    InterpretationContext,
    InterpretationResult,
    PanelInterpretationResult,
    get_interpret_module,
)
from .interpret_safety import (
    InterpretationSafetyGuard,
    SafetyValidationResult,
    get_safety_guard,
)
from .recommend import (
    RecommendationEngine,
    Recommendation,
    RecommendationSet,
    get_recommendation_engine,
)
from .knowledge_loader import (
    KnowledgeLoader,
    BiomarkerInfo,
    InterventionInfo,
    RelationshipInfo,
    get_knowledge_loader,
)

# Phase 2: Medication Adherence modules
from .adherence_patterns import (
    PatternLearner,
    TimeWindowPattern,
    WeekdayPattern,
    MissedDayPattern,
    StreakData,
    get_pattern_learner,
)

# Phase 3: Smart Notifications modules
from .message_generator import (
    MessageGenerator,
    MessageContext,
    GeneratedMessage,
    ReminderPriority,
    MessageTone,
    get_message_generator,
)
from .platform_notifications import (
    NotificationService,
    NotificationProvider,
    NotificationPayload,
    DeliveryResult,
    DeliveryStatus,
    NotificationPlatform,
    get_notification_service,
    initialize_notifications,
)
from .notification_scheduler import (
    NotificationScheduler,
    SchedulerState,
    ScheduleCheck,
    NotificationSettings,
    SchedulerConfig,
    get_notification_scheduler,
    start_notification_scheduler,
    stop_notification_scheduler,
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
    # Phase 1: Lab Interpretation
    "InterpretModule",
    "InterpretationContext",
    "InterpretationResult",
    "PanelInterpretationResult",
    "get_interpret_module",
    "InterpretationSafetyGuard",
    "SafetyValidationResult",
    "get_safety_guard",
    "RecommendationEngine",
    "Recommendation",
    "RecommendationSet",
    "get_recommendation_engine",
    "KnowledgeLoader",
    "BiomarkerInfo",
    "InterventionInfo",
    "RelationshipInfo",
    "get_knowledge_loader",
    # Phase 2: Medication Adherence
    "PatternLearner",
    "TimeWindowPattern",
    "WeekdayPattern",
    "MissedDayPattern",
    "StreakData",
    "get_pattern_learner",
    # Phase 3: Smart Notifications
    "MessageGenerator",
    "MessageContext",
    "GeneratedMessage",
    "ReminderPriority",
    "MessageTone",
    "get_message_generator",
    "NotificationService",
    "NotificationProvider",
    "NotificationPayload",
    "DeliveryResult",
    "DeliveryStatus",
    "NotificationPlatform",
    "get_notification_service",
    "initialize_notifications",
    "NotificationScheduler",
    "SchedulerState",
    "ScheduleCheck",
    "NotificationSettings",
    "SchedulerConfig",
    "get_notification_scheduler",
    "start_notification_scheduler",
    "stop_notification_scheduler",
]
