"""
Recommendation engine for lab interpretations.

Generates evidence-based lifestyle recommendations based on
biomarker values and the intervention knowledge base.

Phase 1: Core Lab Interpretation Engine - Recommendation Component
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from .knowledge_loader import (
    KnowledgeLoader,
    BiomarkerInfo,
    InterventionInfo,
    get_knowledge_loader,
)

logger = logging.getLogger(__name__)


@dataclass
class Recommendation:
    """A single recommendation for the user."""
    id: str  # Intervention ID for citation
    title: str
    text: str
    category: str  # diet, exercise, lifestyle, monitoring
    strength_of_evidence: str
    rationale: Optional[str] = None
    priority: int = 10
    sources: list[dict] = field(default_factory=list)

    def to_citation(self) -> str:
        """Generate citation reference for this recommendation."""
        return f"[INT:{self.id}]"


@dataclass
class RecommendationSet:
    """Set of recommendations for a biomarker result."""
    analyte_canonical: str
    condition_type: str  # high, low, normal, etc.
    recommendations: list[Recommendation] = field(default_factory=list)
    disclaimer: str = ""

    @property
    def has_recommendations(self) -> bool:
        """Check if there are any recommendations."""
        return len(self.recommendations) > 0

    def get_by_category(self, category: str) -> list[Recommendation]:
        """Get recommendations filtered by category."""
        return [r for r in self.recommendations if r.category == category]


class RecommendationEngine:
    """
    Generates personalized recommendations based on lab results.

    Uses the intervention knowledge base to provide evidence-based
    lifestyle suggestions that are:
    - Conservative in framing
    - Backed by evidence
    - Appropriately hedged
    - Free of medication recommendations
    """

    # Standard disclaimer for all recommendations
    RECOMMENDATION_DISCLAIMER = (
        "These suggestions are for informational purposes only. "
        "Always consult your healthcare provider before making changes "
        "to your diet, exercise routine, or lifestyle."
    )

    # Category display order
    CATEGORY_ORDER = ["monitoring", "diet", "exercise", "lifestyle", "supplement"]

    def __init__(self, knowledge_loader: Optional[KnowledgeLoader] = None):
        """
        Initialize the recommendation engine.

        Args:
            knowledge_loader: Optional knowledge loader instance
        """
        self._knowledge_loader = knowledge_loader or get_knowledge_loader()

    async def generate_recommendations(
        self,
        analyte_canonical: str,
        value: float,
        ref_low: Optional[float],
        ref_high: Optional[float],
        db: AsyncSession,
        max_recommendations: int = 5,
    ) -> RecommendationSet:
        """
        Generate recommendations for a lab result.

        Args:
            analyte_canonical: The canonical analyte name
            value: The observed value
            ref_low: Reference range lower bound
            ref_high: Reference range upper bound
            db: Database session
            max_recommendations: Maximum number of recommendations

        Returns:
            RecommendationSet with applicable recommendations
        """
        # Determine condition type
        condition_type = self._classify_condition(value, ref_low, ref_high)

        result = RecommendationSet(
            analyte_canonical=analyte_canonical,
            condition_type=condition_type,
            disclaimer=self.RECOMMENDATION_DISCLAIMER,
        )

        # Normal values don't typically need recommendations
        if condition_type == "normal":
            logger.debug(f"No recommendations for normal {analyte_canonical}")
            return result

        # Get interventions from knowledge base
        interventions = await self._knowledge_loader.get_interventions(
            analyte_canonical=analyte_canonical,
            condition_type=condition_type,
            db=db,
        )

        if not interventions:
            # Try broader condition type
            broad_condition = "high" if "high" in condition_type else "low"
            interventions = await self._knowledge_loader.get_interventions(
                analyte_canonical=analyte_canonical,
                condition_type=broad_condition,
                db=db,
            )

        # Convert to recommendations
        for interv in interventions[:max_recommendations]:
            rec = self._intervention_to_recommendation(interv)
            result.recommendations.append(rec)

        # Sort by category order and priority
        result.recommendations = self._sort_recommendations(result.recommendations)

        logger.info(
            f"Generated {len(result.recommendations)} recommendations for "
            f"{analyte_canonical} ({condition_type})"
        )
        return result

    async def generate_panel_recommendations(
        self,
        panel_name: str,
        observations: list[dict],
        db: AsyncSession,
        max_per_analyte: int = 2,
        max_total: int = 8,
    ) -> list[RecommendationSet]:
        """
        Generate recommendations for a panel of lab results.

        Aggregates and deduplicates recommendations across multiple
        biomarkers in a panel.

        Args:
            panel_name: Panel name (e.g., "lipid", "cbc")
            observations: List of observation dicts with analyte, value, ref_low, ref_high
            db: Database session
            max_per_analyte: Max recommendations per analyte
            max_total: Max total recommendations

        Returns:
            List of RecommendationSets, one per abnormal analyte
        """
        recommendation_sets = []
        seen_interventions = set()

        for obs in observations:
            value = obs.get("value")
            if value is None:
                continue

            rec_set = await self.generate_recommendations(
                analyte_canonical=obs["analyte_canonical"],
                value=value,
                ref_low=obs.get("ref_low"),
                ref_high=obs.get("ref_high"),
                db=db,
                max_recommendations=max_per_analyte,
            )

            # Deduplicate across panel
            unique_recs = []
            for rec in rec_set.recommendations:
                if rec.id not in seen_interventions:
                    seen_interventions.add(rec.id)
                    unique_recs.append(rec)

            rec_set.recommendations = unique_recs

            if rec_set.has_recommendations:
                recommendation_sets.append(rec_set)

        # Limit total recommendations
        total_recs = sum(len(rs.recommendations) for rs in recommendation_sets)
        if total_recs > max_total:
            logger.debug(f"Trimming panel recommendations from {total_recs} to {max_total}")
            # Prioritize by evidence strength and priority
            all_recs = []
            for rs in recommendation_sets:
                for rec in rs.recommendations:
                    all_recs.append((rs.analyte_canonical, rec))

            # Sort and take top recommendations
            all_recs.sort(
                key=lambda x: (
                    self._evidence_strength_score(x[1].strength_of_evidence),
                    x[1].priority,
                )
            )
            keep_recs = set(rec.id for _, rec in all_recs[:max_total])

            # Filter recommendation sets
            for rs in recommendation_sets:
                rs.recommendations = [r for r in rs.recommendations if r.id in keep_recs]

        return recommendation_sets

    def _classify_condition(
        self,
        value: float,
        ref_low: Optional[float],
        ref_high: Optional[float],
    ) -> str:
        """
        Classify the condition based on value vs reference range.

        Returns condition type for intervention lookup.
        """
        if ref_low is None and ref_high is None:
            return "normal"

        # Check for out of range
        is_low = ref_low is not None and value < ref_low
        is_high = ref_high is not None and value > ref_high

        if is_low:
            # Check how far below
            if ref_low > 0:
                pct_below = (ref_low - value) / ref_low * 100
                if pct_below > 20:
                    return "low"
                return "borderline_low"
            return "low"

        if is_high:
            # Check how far above
            if ref_high > 0:
                pct_above = (value - ref_high) / ref_high * 100
                if pct_above > 20:
                    return "high"
                return "borderline_high"
            return "high"

        # Within range - check if borderline
        if ref_low is not None and ref_high is not None:
            range_size = ref_high - ref_low
            if range_size > 0:
                # Bottom 10% of range
                if value < ref_low + (range_size * 0.1):
                    return "borderline_low"
                # Top 10% of range
                if value > ref_high - (range_size * 0.1):
                    return "borderline_high"

        return "normal"

    def _intervention_to_recommendation(
        self,
        intervention: InterventionInfo,
    ) -> Recommendation:
        """Convert an InterventionInfo to a Recommendation."""
        return Recommendation(
            id=intervention.id,
            title=intervention.intervention_title,
            text=intervention.intervention_text,
            category=intervention.category,
            strength_of_evidence=intervention.strength_of_evidence,
            rationale=intervention.rationale,
            priority=intervention.priority,
            sources=intervention.sources,
        )

    def _sort_recommendations(
        self,
        recommendations: list[Recommendation],
    ) -> list[Recommendation]:
        """Sort recommendations by category order and priority."""
        def sort_key(rec: Recommendation) -> tuple:
            try:
                category_idx = self.CATEGORY_ORDER.index(rec.category)
            except ValueError:
                category_idx = len(self.CATEGORY_ORDER)
            return (category_idx, rec.priority)

        return sorted(recommendations, key=sort_key)

    def _evidence_strength_score(self, strength: str) -> int:
        """Convert evidence strength to sortable score (lower is better)."""
        scores = {
            "strong": 1,
            "moderate": 2,
            "limited": 3,
            "emerging": 4,
        }
        return scores.get(strength.lower(), 5)

    def format_recommendations_text(
        self,
        rec_set: RecommendationSet,
        include_rationale: bool = False,
        include_citations: bool = True,
    ) -> str:
        """
        Format recommendations as readable text.

        Args:
            rec_set: RecommendationSet to format
            include_rationale: Include detailed rationale
            include_citations: Include citation markers

        Returns:
            Formatted recommendation text
        """
        if not rec_set.has_recommendations:
            return ""

        lines = ["Based on your results, consider the following:"]
        lines.append("")

        for i, rec in enumerate(rec_set.recommendations, 1):
            citation = rec.to_citation() if include_citations else ""

            # Category header
            category_label = rec.category.replace("_", " ").title()
            lines.append(f"**{category_label}:** {rec.title}")

            # Main text
            lines.append(f"  {rec.text} {citation}")

            # Rationale if requested
            if include_rationale and rec.rationale:
                lines.append(f"  _Why:_ {rec.rationale}")

            # Evidence strength
            lines.append(f"  (Evidence: {rec.strength_of_evidence})")
            lines.append("")

        # Add disclaimer
        lines.append("---")
        lines.append(rec_set.disclaimer)

        return "\n".join(lines)


# Global instance
_recommendation_engine: Optional[RecommendationEngine] = None


def get_recommendation_engine() -> RecommendationEngine:
    """Get or create the global recommendation engine instance."""
    global _recommendation_engine
    if _recommendation_engine is None:
        _recommendation_engine = RecommendationEngine()
    return _recommendation_engine
