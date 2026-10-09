"""
Medical knowledge base models for lab interpretation.

Contains reference data for biomarkers, interventions, and relationships.
This data is loaded from curated sources (LOINC, clinical guidelines, etc.)
and used by the Lab Result Interpreter to generate grounded explanations.

Phase 0: Foundation for Lab Result Interpreter feature.

Note: Knowledge base is stored in the master database (not encrypted per-profile)
since it contains no patient data - only reference medical information.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Float, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from core.time import utcnow


class BiomarkerKnowledge(Base):
    """
    Medical knowledge about biomarkers/lab tests.

    Contains curated information about what each biomarker measures,
    its clinical significance, and how to interpret values.
    This is reference data, not patient data.

    Sources include:
    - LOINC (Logical Observation Identifiers Names and Codes)
    - Clinical guidelines (AHA, ADA, Endocrine Society)
    - Medical textbooks (Harrison's, etc.)
    """

    __tablename__ = "biomarker_knowledge"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Canonical analyte name (matches observations.analyte_canonical)
    analyte_canonical: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )

    # Display name for UI
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # LOINC code(s) - JSON array for multiple codes
    loinc_codes_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # What the biomarker measures
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Why doctors order this test
    clinical_significance: Mapped[str] = mapped_column(Text, nullable=False)

    # Interpretation guidance by value status
    normal_interpretation: Mapped[str] = mapped_column(Text, nullable=False)
    high_interpretation: Mapped[str] = mapped_column(Text, nullable=False)
    low_interpretation: Mapped[str] = mapped_column(Text, nullable=False)

    # Reference ranges by demographic (JSON: {"male": {...}, "female": {...}, "default": {...}})
    ref_range_adult_json: Mapped[str] = mapped_column(Text, nullable=False)

    # Common causes for abnormal values (JSON arrays)
    common_causes_high_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    common_causes_low_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Critical value thresholds (require immediate attention)
    critical_low: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    critical_high: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Standard unit for this biomarker
    standard_unit: Mapped[str] = mapped_column(String(50), nullable=False)

    # Alternative units with conversion factors (JSON: {"mmol/L": 0.0555, ...})
    unit_conversions_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Category for grouping (cbc, cmp, lipid, thyroid, vitamin, etc.)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Panel memberships (JSON array: ["lipid_panel", "cardiovascular"])
    panels_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Source citations (JSON array of source objects)
    sources_json: Mapped[str] = mapped_column(Text, nullable=False)

    # Curation metadata
    last_reviewed: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<BiomarkerKnowledge(analyte={self.analyte_canonical!r}, category={self.category!r})>"


class InterventionMapping(Base):
    """
    Evidence-based lifestyle interventions for abnormal biomarker values.

    Maps biomarker conditions (high/low) to actionable, conservative
    lifestyle recommendations with evidence strength ratings.

    All interventions are:
    - Non-prescription (no medications)
    - Conservative in framing ("may help" not "will fix")
    - Backed by evidence (strength rating required)
    - Safe for general population (contraindications noted)
    """

    __tablename__ = "intervention_mappings"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Link to biomarker (matches biomarker_knowledge.analyte_canonical)
    analyte_canonical: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )

    # Condition that triggers this intervention
    # Values: "high", "low", "borderline_high", "borderline_low", "ratio_abnormal"
    condition_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    # Category of intervention
    # Values: "diet", "exercise", "lifestyle", "supplement", "monitoring"
    category: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    # The intervention recommendation text
    # Example: "Consider increasing fiber intake to 25-30g daily"
    intervention_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Short title for UI display
    intervention_title: Mapped[str] = mapped_column(String(100), nullable=False)

    # Detailed explanation of why this helps
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Strength of evidence
    # Values: "strong", "moderate", "limited", "emerging"
    strength_of_evidence: Mapped[str] = mapped_column(String(20), nullable=False)

    # Specific dietary/lifestyle details (JSON for structured data)
    details_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # When NOT to recommend this (JSON array of contraindication strings)
    contraindications_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Priority for ordering (1 = highest priority)
    priority: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    # Source citations (JSON array of source objects)
    sources_json: Mapped[str] = mapped_column(Text, nullable=False)

    # Whether this intervention is currently active
    is_active: Mapped[bool] = mapped_column(
        Integer, default=True, nullable=False  # SQLite boolean
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<InterventionMapping(analyte={self.analyte_canonical!r}, condition={self.condition_type!r}, category={self.category!r})>"


class BiomarkerRelationship(Base):
    """
    Relationships between biomarkers for panel-level interpretation.

    Captures:
    - Ratio calculations (e.g., LDL/HDL ratio)
    - Panel memberships (e.g., lipid panel components)
    - Correlated biomarkers (e.g., BUN and Creatinine)
    - Inverse correlations (e.g., TSH and Free T4)

    Used by the interpreter to provide holistic panel analysis
    rather than isolated biomarker interpretations.
    """

    __tablename__ = "biomarker_relationships"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Primary biomarker in the relationship
    primary_analyte: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )

    # Related biomarker
    related_analyte: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )

    # Type of relationship
    # Values: "ratio", "inverse_correlation", "direct_correlation",
    #         "panel_member", "derived_from", "confirms"
    relationship_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)

    # Human-readable description of the relationship
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Clinical significance of this relationship
    clinical_significance: Mapped[str] = mapped_column(Text, nullable=False)

    # For ratio types: calculation formula
    # Example: "total_cholesterol / hdl" or "ldl / hdl"
    ratio_calculation: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Target range for ratios (JSON: {"optimal": [0, 3.5], "borderline": [3.5, 5], "high_risk": [5, null]})
    ratio_target_range_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Interpretation guidance when relationship is abnormal
    abnormal_interpretation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Panel this relationship belongs to (if applicable)
    panel_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)

    # Source citations
    sources_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<BiomarkerRelationship({self.primary_analyte!r} -> {self.related_analyte!r}, type={self.relationship_type!r})>"
