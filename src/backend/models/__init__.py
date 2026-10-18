"""
SQLAlchemy models for HealthCentral.

Exports all models for use throughout the application.

Model Organization:
- Master Database (core.database.Base): Profile, AuditLog, BiomarkerKnowledge,
  InterventionMapping, BiomarkerRelationship
- Per-Profile Database (core.profile_database.ProfileDatabaseBase): Document,
  Observation, Chunk, Embedding, LabInterpretation, PanelInterpretation,
  Medication, MedicationSchedule, DoseTaken, AdherencePattern, ReminderLog
"""

from .audit import AuditLog
from .backup_schedule import BackupSchedule
from .care_plan_task import CarePlanTask
from .chat_session import ChatSession, ChatTurn
from .chunk import Chunk
from .document import Document
from .document_category import DocumentCategory, DocumentEntity
from .embedding import Embedding
from .gamification import BadgeDefinition, EarnedBadge
from .interpretation import LabInterpretation, PanelInterpretation
from .knowledge_base import (
    BiomarkerKnowledge,
    BiomarkerRelationship,
    InterventionMapping,
)
from .medication import (
    AdherencePattern,
    DoseTaken,
    Medication,
    MedicationSchedule,
    ReminderLog,
)
from .memory_item import MemoryItem
from .model_settings import UserModelSettings
from .observation import Observation
from .pinboard import Pinboard, PinboardItem
from .profile import Profile

__all__ = [
    # Master database
    "Profile",
    "AuditLog",
    "BackupSchedule",
    # Knowledge base (master)
    "BiomarkerKnowledge",
    "InterventionMapping",
    "BiomarkerRelationship",
    # Per-profile
    "Document",
    "Observation",
    "Chunk",
    "Embedding",
    # Interpretations (per-profile)
    "LabInterpretation",
    "PanelInterpretation",
    # Medications (per-profile)
    "Medication",
    "MedicationSchedule",
    "DoseTaken",
    "AdherencePattern",
    "ReminderLog",
    # Model settings (per-profile, Phase 0.3)
    "UserModelSettings",
    # Gamification (per-profile, GAM-001)
    "BadgeDefinition",
    "EarnedBadge",
    # Document classification (per-profile, INGEST-EPIC-001)
    "DocumentCategory",
    "DocumentEntity",
    # Memory store (per-profile)
    "MemoryItem",
    # Chat session persistence (per-profile)
    "ChatSession",
    "ChatTurn",
    # Care-plan tasks (per-profile, HC-M15)
    "CarePlanTask",
    # Pinboards (per-profile, HC-M20)
    "Pinboard",
    "PinboardItem",
]
