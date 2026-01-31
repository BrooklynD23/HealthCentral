"""
User model settings stored in per-profile encrypted database.

Phase 0.3: Tiered Hardware Model System
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.profile_database import ProfileDatabaseBase


class UserModelSettings(ProfileDatabaseBase):
    """
    User's model tier preferences and hardware detection results.

    Stored in per-profile database for data isolation.

    Tier semantics (aligned with 04_local_models_inference_plan.md):
    - "low" = Tier 1 (small + fast) - Qwen2.5 0.5B - DEFAULT
    - "mid" = Tier 2 (balanced) - Phi-3-mini
    - "high" = Tier 3 (quality) - BioMistral-7B
    - "template" = Fallback when no model available
    """

    __tablename__ = "user_model_settings"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    profile_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    # User preference - string tiers: "low", "mid", "high"
    preferred_tier: Mapped[str] = mapped_column(
        String(20),
        default="low",
        nullable=False,
    )

    # Whether to auto-detect hardware and recommend tier
    auto_detect_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Last hardware detection result (JSON)
    # Contains: ram_total_gb, cpu_cores, disk_free_gb, recommended_tier, etc.
    last_hardware_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Timestamp of last hardware detection
    last_detection_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )

    # Download state (JSON) - persists across restarts
    # Contains: {tier: {status, progress, path, error}, ...}
    download_state_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def __repr__(self) -> str:
        return (
            f"<UserModelSettings(id={self.id}, "
            f"profile_id={self.profile_id}, "
            f"preferred_tier={self.preferred_tier})>"
        )
