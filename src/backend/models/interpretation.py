"""
Lab interpretation models for the Personal Lab Result Interpreter.

Stores AI-generated interpretations of lab results with citations,
safety metadata, and confidence scores.

Phase 0: Foundation for Lab Result Interpreter feature.

Note: Interpretations are stored in per-profile encrypted databases
since they contain patient-specific health information.
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Float, Boolean, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.profile_database import ProfileDatabaseBase

if TYPE_CHECKING:
    from .observation import Observation


class LabInterpretation(ProfileDatabaseBase):
    """
    AI-generated interpretation of a single lab observation.

    Contains:
    - Plain-language explanation of the result
    - Severity classification
    - Personalized advice with citations
    - Model provenance and confidence
    - Safety flags for physician review

    One interpretation per observation (unique constraint).
    """

    __tablename__ = "lab_interpretations"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Profile ID (stored but not FK - profiles in master DB)
    profile_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )

    # Foreign key to observation (one interpretation per observation)
    observation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("observations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Plain-language interpretation of the result
    # Example: "Your hemoglobin level of 14.2 g/dL is within the normal range
    # for adult males (13.5-17.5 g/dL). This indicates healthy oxygen-carrying
    # capacity in your blood."
    interpretation_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Severity classification
    # Values: "normal", "borderline_low", "borderline_high", "abnormal_low",
    #         "abnormal_high", "critical_low", "critical_high"
    severity_level: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Personalized advice/recommendations
    # Example: "To support healthy hemoglobin levels, consider maintaining adequate
    # iron intake through foods like lean red meat, spinach, and legumes."
    advice_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Citations for interpretation claims (JSON array)
    # Format: [{"type": "knowledge_base", "id": "kb_123", "text": "..."},
    #          {"type": "intervention", "id": "int_456", "text": "..."}]
    citations_json: Mapped[str] = mapped_column(Text, nullable=False)

    # Historical context (JSON object)
    # Format: {"trend": "stable|improving|worsening", "prev_value": 14.0,
    #          "prev_date": "2024-06-15", "change_percent": 1.4}
    context_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Model provenance
    model_id: Mapped[str] = mapped_column(String(100), nullable=False)
    model_tier: Mapped[str] = mapped_column(String(20), nullable=False)  # "high", "mid", "low", "template"

    # Confidence score (0.0-1.0)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Safety flags
    requires_physician_review: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    physician_review_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Safety validation results (JSON)
    # Format: {"passed": true, "checks": ["no_diagnosis", "has_citations", ...]}
    safety_validation_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Whether user has viewed this interpretation
    viewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Regeneration tracking
    regeneration_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    previous_interpretation_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    observation: Mapped["Observation"] = relationship(
        "Observation", back_populates="interpretation"
    )

    def __repr__(self) -> str:
        return f"<LabInterpretation(id={self.id!r}, observation_id={self.observation_id!r}, severity={self.severity_level!r})>"


class PanelInterpretation(ProfileDatabaseBase):
    """
    Holistic interpretation of a lab panel (group of related biomarkers).

    Provides:
    - Summary interpretation across multiple related observations
    - Relationship analysis (ratios, correlations)
    - Panel-specific advice
    - Overall status assessment

    Examples: Lipid panel, CBC, CMP, Thyroid panel
    """

    __tablename__ = "panel_interpretations"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Profile ID (stored but not FK - profiles in master DB)
    profile_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True
    )

    # Panel identification
    panel_name: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # "lipid", "cbc", "cmp", "thyroid"

    # When the panel tests were collected
    collected_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True
    )

    # Observation IDs included in this panel interpretation (JSON array)
    observation_ids_json: Mapped[str] = mapped_column(Text, nullable=False)

    # Holistic panel summary
    # Example: "Your lipid panel shows a mixed picture. While your HDL cholesterol
    # is excellent at 65 mg/dL, your LDL is elevated at 142 mg/dL. Your triglycerides
    # are within normal range."
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Overall panel status
    # Values: "optimal", "normal", "borderline", "abnormal", "concerning"
    overall_status: Mapped[str] = mapped_column(String(20), nullable=False)

    # Relationship insights (JSON)
    # Format: [{"relationship": "ldl_hdl_ratio", "value": 2.18, "status": "optimal",
    #           "interpretation": "Your LDL/HDL ratio of 2.18 suggests good cardiovascular health"}]
    relationship_insights_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Panel-specific advice
    advice_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Citations (JSON array)
    citations_json: Mapped[str] = mapped_column(Text, nullable=False)

    # Model provenance
    model_id: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Safety flags
    requires_physician_review: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<PanelInterpretation(id={self.id!r}, panel={self.panel_name!r}, status={self.overall_status!r})>"
