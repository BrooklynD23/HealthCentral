"""
Knowledge base loader for lab interpretation.

Queries the biomarker knowledge base to retrieve reference information
for generating grounded interpretations.

Phase 1: Core Lab Interpretation Engine
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import BiomarkerKnowledge, InterventionMapping, BiomarkerRelationship

logger = logging.getLogger(__name__)


@dataclass
class BiomarkerInfo:
    """Loaded biomarker information from knowledge base."""
    id: str
    analyte_canonical: str
    display_name: str
    description: str
    clinical_significance: str
    normal_interpretation: str
    high_interpretation: str
    low_interpretation: str
    ref_range_adult: dict = field(default_factory=dict)
    common_causes_high: list[str] = field(default_factory=list)
    common_causes_low: list[str] = field(default_factory=list)
    critical_low: Optional[float] = None
    critical_high: Optional[float] = None
    standard_unit: str = ""
    unit_conversions: dict = field(default_factory=dict)
    category: str = ""
    panels: list[str] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)


@dataclass
class InterventionInfo:
    """Loaded intervention information from knowledge base."""
    id: str
    analyte_canonical: str
    condition_type: str
    category: str
    intervention_title: str
    intervention_text: str
    rationale: Optional[str] = None
    strength_of_evidence: str = "limited"
    details: dict = field(default_factory=dict)
    contraindications: list[str] = field(default_factory=list)
    priority: int = 10
    sources: list[dict] = field(default_factory=list)


@dataclass
class RelationshipInfo:
    """Loaded biomarker relationship information."""
    id: str
    primary_analyte: str
    related_analyte: str
    relationship_type: str
    description: str
    clinical_significance: str
    ratio_calculation: Optional[str] = None
    ratio_target_range: Optional[dict] = None
    abnormal_interpretation: Optional[str] = None
    panel_name: Optional[str] = None
    sources: list[dict] = field(default_factory=list)


class KnowledgeLoader:
    """
    Loads and caches biomarker knowledge from the database.

    Provides efficient access to reference information needed
    for generating lab interpretations.
    """

    def __init__(self):
        """Initialize the knowledge loader."""
        # Simple cache for frequently accessed biomarkers
        self._biomarker_cache: dict[str, BiomarkerInfo] = {}
        self._intervention_cache: dict[str, list[InterventionInfo]] = {}
        self._relationship_cache: dict[str, list[RelationshipInfo]] = {}

    async def get_biomarker_knowledge(
        self,
        analyte_canonical: str,
        db: AsyncSession,
    ) -> Optional[BiomarkerInfo]:
        """
        Get knowledge base entry for a biomarker.

        Args:
            analyte_canonical: The canonical analyte name
            db: Database session (master database)

        Returns:
            BiomarkerInfo if found, None otherwise
        """
        # Check cache first
        cache_key = analyte_canonical.lower()
        if cache_key in self._biomarker_cache:
            return self._biomarker_cache[cache_key]

        # Query database
        result = await db.execute(
            select(BiomarkerKnowledge).where(
                BiomarkerKnowledge.analyte_canonical == cache_key
            )
        )
        kb = result.scalar_one_or_none()

        if not kb:
            logger.debug(f"No knowledge base entry for analyte: {analyte_canonical}")
            return None

        # Parse JSON fields
        ref_range = {}
        if kb.ref_range_adult_json:
            try:
                ref_range = json.loads(kb.ref_range_adult_json)
            except json.JSONDecodeError:
                logger.warning(f"Invalid ref_range_adult_json for {analyte_canonical}")

        causes_high = []
        if kb.common_causes_high_json:
            try:
                causes_high = json.loads(kb.common_causes_high_json)
            except json.JSONDecodeError:
                pass

        causes_low = []
        if kb.common_causes_low_json:
            try:
                causes_low = json.loads(kb.common_causes_low_json)
            except json.JSONDecodeError:
                pass

        unit_conversions = {}
        if kb.unit_conversions_json:
            try:
                unit_conversions = json.loads(kb.unit_conversions_json)
            except json.JSONDecodeError:
                pass

        panels = []
        if kb.panels_json:
            try:
                panels = json.loads(kb.panels_json)
            except json.JSONDecodeError:
                pass

        sources = []
        if kb.sources_json:
            try:
                sources = json.loads(kb.sources_json)
            except json.JSONDecodeError:
                pass

        info = BiomarkerInfo(
            id=kb.id,
            analyte_canonical=kb.analyte_canonical,
            display_name=kb.display_name,
            description=kb.description,
            clinical_significance=kb.clinical_significance,
            normal_interpretation=kb.normal_interpretation,
            high_interpretation=kb.high_interpretation,
            low_interpretation=kb.low_interpretation,
            ref_range_adult=ref_range,
            common_causes_high=causes_high,
            common_causes_low=causes_low,
            critical_low=kb.critical_low,
            critical_high=kb.critical_high,
            standard_unit=kb.standard_unit,
            unit_conversions=unit_conversions,
            category=kb.category,
            panels=panels,
            sources=sources,
        )

        # Cache result
        self._biomarker_cache[cache_key] = info
        return info

    async def get_interventions(
        self,
        analyte_canonical: str,
        condition_type: str,
        db: AsyncSession,
    ) -> list[InterventionInfo]:
        """
        Get applicable interventions for a biomarker condition.

        Args:
            analyte_canonical: The canonical analyte name
            condition_type: "high", "low", "borderline_high", "borderline_low"
            db: Database session

        Returns:
            List of applicable interventions, sorted by priority
        """
        cache_key = f"{analyte_canonical.lower()}:{condition_type}"
        if cache_key in self._intervention_cache:
            return self._intervention_cache[cache_key]

        result = await db.execute(
            select(InterventionMapping).where(
                InterventionMapping.analyte_canonical == analyte_canonical.lower(),
                InterventionMapping.condition_type == condition_type,
                InterventionMapping.is_active == True,
            ).order_by(InterventionMapping.priority)
        )
        interventions = result.scalars().all()

        info_list = []
        for interv in interventions:
            details = {}
            if interv.details_json:
                try:
                    details = json.loads(interv.details_json)
                except json.JSONDecodeError:
                    pass

            contraindications = []
            if interv.contraindications_json:
                try:
                    contraindications = json.loads(interv.contraindications_json)
                except json.JSONDecodeError:
                    pass

            sources = []
            if interv.sources_json:
                try:
                    sources = json.loads(interv.sources_json)
                except json.JSONDecodeError:
                    pass

            info_list.append(InterventionInfo(
                id=interv.id,
                analyte_canonical=interv.analyte_canonical,
                condition_type=interv.condition_type,
                category=interv.category,
                intervention_title=interv.intervention_title,
                intervention_text=interv.intervention_text,
                rationale=interv.rationale,
                strength_of_evidence=interv.strength_of_evidence,
                details=details,
                contraindications=contraindications,
                priority=interv.priority,
                sources=sources,
            ))

        self._intervention_cache[cache_key] = info_list
        return info_list

    async def get_relationships(
        self,
        analyte_canonical: str,
        db: AsyncSession,
    ) -> list[RelationshipInfo]:
        """
        Get relationships involving a biomarker.

        Args:
            analyte_canonical: The canonical analyte name
            db: Database session

        Returns:
            List of relationships where this analyte is primary or related
        """
        cache_key = analyte_canonical.lower()
        if cache_key in self._relationship_cache:
            return self._relationship_cache[cache_key]

        # Query relationships where analyte is either primary or related
        from sqlalchemy import or_

        result = await db.execute(
            select(BiomarkerRelationship).where(
                or_(
                    BiomarkerRelationship.primary_analyte == cache_key,
                    BiomarkerRelationship.related_analyte == cache_key,
                )
            )
        )
        relationships = result.scalars().all()

        info_list = []
        for rel in relationships:
            ratio_target = None
            if rel.ratio_target_range_json:
                try:
                    ratio_target = json.loads(rel.ratio_target_range_json)
                except json.JSONDecodeError:
                    pass

            sources = []
            if rel.sources_json:
                try:
                    sources = json.loads(rel.sources_json)
                except json.JSONDecodeError:
                    pass

            info_list.append(RelationshipInfo(
                id=rel.id,
                primary_analyte=rel.primary_analyte,
                related_analyte=rel.related_analyte,
                relationship_type=rel.relationship_type,
                description=rel.description,
                clinical_significance=rel.clinical_significance,
                ratio_calculation=rel.ratio_calculation,
                ratio_target_range=ratio_target,
                abnormal_interpretation=rel.abnormal_interpretation,
                panel_name=rel.panel_name,
                sources=sources,
            ))

        self._relationship_cache[cache_key] = info_list
        return info_list

    async def get_panel_relationships(
        self,
        panel_name: str,
        db: AsyncSession,
    ) -> list[RelationshipInfo]:
        """
        Get all relationships for a panel.

        Args:
            panel_name: Panel name (e.g., "lipid", "cbc")
            db: Database session

        Returns:
            List of relationships in this panel
        """
        result = await db.execute(
            select(BiomarkerRelationship).where(
                BiomarkerRelationship.panel_name == panel_name.lower()
            )
        )
        relationships = result.scalars().all()

        info_list = []
        for rel in relationships:
            ratio_target = None
            if rel.ratio_target_range_json:
                try:
                    ratio_target = json.loads(rel.ratio_target_range_json)
                except json.JSONDecodeError:
                    pass

            sources = []
            if rel.sources_json:
                try:
                    sources = json.loads(rel.sources_json)
                except json.JSONDecodeError:
                    pass

            info_list.append(RelationshipInfo(
                id=rel.id,
                primary_analyte=rel.primary_analyte,
                related_analyte=rel.related_analyte,
                relationship_type=rel.relationship_type,
                description=rel.description,
                clinical_significance=rel.clinical_significance,
                ratio_calculation=rel.ratio_calculation,
                ratio_target_range=ratio_target,
                abnormal_interpretation=rel.abnormal_interpretation,
                panel_name=rel.panel_name,
                sources=sources,
            ))

        return info_list

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._biomarker_cache.clear()
        self._intervention_cache.clear()
        self._relationship_cache.clear()
        logger.debug("Knowledge loader cache cleared")


# Global instance for reuse
_knowledge_loader: Optional[KnowledgeLoader] = None


def get_knowledge_loader() -> KnowledgeLoader:
    """Get or create the global knowledge loader instance."""
    global _knowledge_loader
    if _knowledge_loader is None:
        _knowledge_loader = KnowledgeLoader()
    return _knowledge_loader
