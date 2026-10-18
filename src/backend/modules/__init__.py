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

# Phase 2: Medication Adherence modules
from .adherence_patterns import (
    MissedDayPattern,
    PatternLearner,
    StreakData,
    TimeWindowPattern,
    WeekdayPattern,
    get_pattern_learner,
)
from .analytics import AnalyticsModule
from .claim_extractor import ClaimExtractionResult, ClaimExtractor, ExtractedClaim
from .export import ExportModule
from .extract import ExtractModule
from .faithfulness import (
    FaithfulnessConfig,
    FaithfulnessScorer,
    FaithfulnessScores,
)
from .hardware_detection import (
    TIER_ORDER,
    TIER_REQUIREMENTS,
    HardwareProfile,
    can_run_tier,
    detect_hardware,
    get_recommended_tier,
    get_tier_display_info,
)
from .ingest import IngestModule
from .interpret import (
    InterpretationContext,
    InterpretationResult,
    InterpretModule,
    PanelInterpretationResult,
    get_interpret_module,
)
from .interpret_safety import (
    InterpretationSafetyGuard,
    SafetyValidationResult,
    get_safety_guard,
)
from .knowledge_loader import (
    BiomarkerInfo,
    InterventionInfo,
    KnowledgeLoader,
    RelationshipInfo,
    get_knowledge_loader,
)
from .message_generator import (
    GeneratedMessage,
    MessageContext,
    MessageGenerator,
    MessageTone,
    ReminderPriority,
    get_message_generator,
)
from .model_selector import (
    TIER_FALLBACK_ORDER,
    TIER_MODEL_CONFIG,
    DownloadProgress,
    ModelSelector,
    get_model_selector,
)
from .normalize import NormalizeModule
from .notification_scheduler import (
    NotificationScheduler,
    NotificationSettings,
    ScheduleCheck,
    SchedulerConfig,
    SchedulerState,
    get_notification_scheduler,
    start_notification_scheduler,
    stop_notification_scheduler,
)
from .platform_notifications import (
    DeliveryResult,
    DeliveryStatus,
    NotificationPayload,
    NotificationPlatform,
    NotificationProvider,
    NotificationService,
    get_notification_service,
    initialize_notifications,
)
from .rag import RAGModule
from .recommend import (
    Recommendation,
    RecommendationEngine,
    RecommendationSet,
    get_recommendation_engine,
)
from .source_authority import (
    ClaimAuthorityAnalysis,
    SourceAuthorityScorer,
    SourceMetadata,
    SourceTier,
)
from .verifier_agent import (
    ClaimVerificationResult,
    EntailmentLabel,
    SourceEvidence,
    VerificationConfig,
    VerifierAgent,
)
from .verify import EDITABLE_FIELDS, VerificationEdit, VerificationPayload, validate_edit_value

__all__ = [
    # Core modules
    "IngestModule",
    "ExtractModule",
    "NormalizeModule",
    "VerificationPayload",
    "VerificationEdit",
    "validate_edit_value",
    "EDITABLE_FIELDS",
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
    # Phase 0.3: Hardware Detection and Model Selection
    "HardwareProfile",
    "detect_hardware",
    "can_run_tier",
    "get_recommended_tier",
    "get_tier_display_info",
    "TIER_REQUIREMENTS",
    "TIER_ORDER",
    "ModelSelector",
    "DownloadProgress",
    "get_model_selector",
    "TIER_MODEL_CONFIG",
    "TIER_FALLBACK_ORDER",
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
