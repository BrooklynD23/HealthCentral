"""
Observation model for lab values and measurements.

Stores extracted medical observations with reference ranges.

Phase 3: This model lives in per-profile encrypted databases,
not the master database.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Float, Boolean, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.profile_database import ProfileDatabaseBase
from core.time import utcnow

if TYPE_CHECKING:
    from .document import Document
    from .interpretation import LabInterpretation


class Observation(ProfileDatabaseBase):
    """
    Medical observation (lab value, vital sign, etc.).

    Stores both numeric and text values with reference ranges
    for trend analysis and abnormal detection.

    Phase 3: Stored in per-profile encrypted SQLCipher database.
    """

    __tablename__ = "observations"

    # Primary key - UUID string
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Profile ID (stored but not a FK since profiles are in master DB)
    profile_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    # Foreign key to document (within same profile database)
    doc_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Analyte identification
    analyte_canonical: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    analyte_raw: Mapped[str] = mapped_column(String(255), nullable=False)

    # Values - support both numeric and text
    value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    value_text: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Reference range
    ref_low: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ref_high: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ref_range_text: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Abnormal flags
    flag: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    is_abnormal: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Collection timestamp
    collected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, index=True
    )

    # Verification tracking
    user_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    extraction_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Version tracking for edits
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    original_value_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Source location in document (for provenance)
    source_page: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source_bbox_json: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relationships (within profile database only)
    document: Mapped["Document"] = relationship(
        "Document", back_populates="observations"
    )
    interpretation: Mapped[Optional["LabInterpretation"]] = relationship(
        "LabInterpretation",
        back_populates="observation",
        uselist=False,
        # DOC-DELETE-INTERP: lab_interpretations.observation_id is NOT NULL and
        # SQLite FK enforcement is off, so the DB-level ondelete is inert. Without
        # this the ORM nulls the FK on observation delete -> IntegrityError.
        # Not delete-orphan: modules/interpret.py creates rows by FK alone.
        cascade="all, delete",
    )

    def __repr__(self) -> str:
        return f"<Observation(id={self.id!r}, analyte={self.analyte_canonical!r}, value={self.value!r})>"
