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

# Master database models
from .profile import Profile
from .audit import AuditLog

# Knowledge base models (master database - reference data)
from .knowledge_base import (
    BiomarkerKnowledge,
    InterventionMapping,
    BiomarkerRelationship,
)

# Per-profile database models
from .document import Document
from .observation import Observation
from .chunk import Chunk
from .embedding import Embedding

# Lab interpretation models (per-profile)
from .interpretation import LabInterpretation, PanelInterpretation

# Medication adherence models (per-profile)
from .medication import (
    Medication,
    MedicationSchedule,
    DoseTaken,
    AdherencePattern,
    ReminderLog,
)

# Model settings (per-profile, Phase 0.3)
from .model_settings import UserModelSettings

# Gamification (per-profile, GAM-001)
from .gamification import BadgeDefinition, EarnedBadge

# Memory store (per-profile, ASSIST-MEM-001)
from .memory_item import MemoryItem

__all__ = [
    # Master database
    "Profile",
    "AuditLog",
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
    # Memory store (per-profile)
    "MemoryItem",
]
