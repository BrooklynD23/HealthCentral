"""
Main interpretation pipeline for lab results.

Orchestrates the generation of AI-powered lab result interpretations
using the knowledge base, safety guardrails, and recommendation engine.

Phase 1: Core Lab Interpretation Engine - Main Orchestrator
"""

import asyncio
import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Observation, LabInterpretation, PanelInterpretation
from modules.normalize import (
    canonical_unit_for,
    convert_to_canonical,
    normalize_unit,
)
from .knowledge_loader import (
    KnowledgeLoader,
    BiomarkerInfo,
    get_knowledge_loader,
)
from .interpret_safety import (
    InterpretationSafetyGuard,
    SafetyValidationResult,
    get_safety_guard,
)
from .recommend import (
    RecommendationEngine,
    RecommendationSet,
    get_recommendation_engine,
)
from .model_selector import ModelSelector, get_model_selector

logger = logging.getLogger(__name__)

# Citation-enforcing prompt template for LLM interpretation
LLM_INTERPRETATION_PROMPT = """You are a medical results assistant explaining lab values to patients.

RULES:
1. Cite knowledge base facts as [KB:analyte_name]
2. Cite intervention advice as [INT:intervention_id]
3. NEVER diagnose conditions or diseases
4. ALWAYS recommend consulting a healthcare provider for personalized advice
5. Be patient-friendly and explain medical terms simply

Lab Result:
- Analyte: {analyte}
- Value: {value} {unit}
- Reference Range: {ref_low} - {ref_high}
- Flag: {flag}

Knowledge Base Information:
{knowledge_text}

Provide a clear, patient-friendly explanation with proper citations:"""


@dataclass
class InterpretationContext:
    """Context assembled for generating an interpretation."""
    observation: Observation
    biomarker_info: Optional[BiomarkerInfo] = None
    historical_values: list[tuple[datetime, float]] = field(default_factory=list)
    comparison_unit: Optional[str] = None
    comparison_current_value: Optional[float] = None
    trend_direction: str = "unknown"  # stable, improving, worsening, unknown
    related_abnormalities: list[str] = field(default_factory=list)
    recommendations: Optional[RecommendationSet] = None


@dataclass
class InterpretationResult:
    """Result of generating an interpretation."""
    success: bool
    interpretation: Optional[LabInterpretation] = None
    error_message: Optional[str] = None
    safety_validation: Optional[SafetyValidationResult] = None


@dataclass
class PanelInterpretationResult:
    """Result of generating a panel interpretation."""
    success: bool
    interpretation: Optional[PanelInterpretation] = None
    error_message: Optional[str] = None


class InterpretModule:
    """
    Main orchestrator for lab result interpretation.

    Coordinates:
    1. Context assembly (observation, history, knowledge)
    2. Interpretation generation (template or LLM)
    3. Recommendation generation
    4. Safety validation
    5. Storage and audit

    Currently uses template-based generation. LLM integration
    will be added when BioMistral model is configured.
    """

    # Model tier for template-based generation
    MODEL_TIER_TEMPLATE = "template"
    MODEL_ID_TEMPLATE = "template-v1"

    def __init__(
        self,
        knowledge_loader: Optional[KnowledgeLoader] = None,
        safety_guard: Optional[InterpretationSafetyGuard] = None,
        recommendation_engine: Optional[RecommendationEngine] = None,
        model_selector: Optional[ModelSelector] = None,
    ):
        """
        Initialize the interpretation module.

        Args:
            knowledge_loader: Knowledge base loader
            safety_guard: Safety validation
            recommendation_engine: Recommendation generator
            model_selector: Model selector for tiered LLM inference (Phase 0.3)
        """
        self._knowledge_loader = knowledge_loader or get_knowledge_loader()
        self._safety_guard = safety_guard or get_safety_guard()
        self._recommendation_engine = recommendation_engine or get_recommendation_engine()
        self._model_selector = model_selector or get_model_selector()

    async def interpret_observation(
        self,
        observation_id: str,
        profile_db: AsyncSession,
        master_db: AsyncSession,
        force_regenerate: bool = False,
    ) -> InterpretationResult:
        """
        Generate interpretation for a single observation.

        Args:
            observation_id: The observation UUID
            profile_db: Per-profile database session
            master_db: Master database session (for knowledge base)
            force_regenerate: Force regeneration even if exists

        Returns:
            InterpretationResult with interpretation or error
        """
        # Fetch observation
        result = await profile_db.execute(
            select(Observation).where(Observation.id == observation_id)
        )
        observation = result.scalar_one_or_none()

        if not observation:
            return InterpretationResult(
                success=False,
                error_message=f"Observation not found: {observation_id}",
            )

        # Check for existing interpretation
        if not force_regenerate:
            existing = await profile_db.execute(
                select(LabInterpretation).where(
                    LabInterpretation.observation_id == observation_id
                )
            )
            existing_interp = existing.scalar_one_or_none()
            if existing_interp:
                return InterpretationResult(
                    success=True,
                    interpretation=existing_interp,
                )

        # Assemble context
        context = await self._assemble_context(
            observation=observation,
            profile_db=profile_db,
            master_db=master_db,
        )

        # Generate interpretation
        interpretation_text, advice_text = await self._generate_interpretation(
            context=context,
            master_db=master_db,
        )

        # Classify severity
        severity_level = self._classify_severity(
            value=observation.value,
            ref_low=observation.ref_low,
            ref_high=observation.ref_high,
            biomarker_info=context.biomarker_info,
        )

        # Generate citations
        citations = self._generate_citations(context)

        # Validate safety
        safety_result = self._safety_guard.validate_interpretation(
            interpretation_text=interpretation_text,
            advice_text=advice_text,
            require_citations=True,
        )

        # Check for critical values
        if observation.value is not None:
            critical_result = self._safety_guard.check_critical_value(
                analyte_canonical=observation.analyte_canonical,
                value=observation.value,
                critical_low=context.biomarker_info.critical_low if context.biomarker_info else None,
                critical_high=context.biomarker_info.critical_high if context.biomarker_info else None,
            )
            if critical_result.requires_physician_review:
                safety_result.requires_physician_review = True
                safety_result.physician_review_reason = critical_result.physician_review_reason

        # Ensure disclaimers
        interpretation_text, advice_text = self._safety_guard.add_required_disclaimers(
            interpretation_text=interpretation_text,
            advice_text=advice_text,
        )

        # Build context JSON
        context_json = self._build_context_json(context)

        # Safety validation JSON
        safety_json = json.dumps({
            "passed": safety_result.passed,
            "checks_passed": safety_result.checks_passed,
            "checks_failed": safety_result.checks_failed,
            "warnings": safety_result.warnings,
        })

        # Create or update interpretation
        if force_regenerate:
            # Get existing to track regeneration
            existing = await profile_db.execute(
                select(LabInterpretation).where(
                    LabInterpretation.observation_id == observation_id
                )
            )
            existing_interp = existing.scalar_one_or_none()

        interpretation = LabInterpretation(
            id=str(uuid.uuid4()),
            profile_id=observation.profile_id,
            observation_id=observation_id,
            interpretation_text=interpretation_text,
            severity_level=severity_level,
            advice_text=advice_text if advice_text else None,
            citations_json=json.dumps(citations),
            context_json=context_json,
            model_id=self.MODEL_ID_TEMPLATE,
            model_tier=self.MODEL_TIER_TEMPLATE,
            confidence_score=0.85,  # Template confidence
            requires_physician_review=safety_result.requires_physician_review,
            physician_review_reason=safety_result.physician_review_reason,
            safety_validation_json=safety_json,
            regeneration_count=0,
        )

        if force_regenerate and existing_interp:
            interpretation.regeneration_count = existing_interp.regeneration_count + 1
            interpretation.previous_interpretation_id = existing_interp.id
            # Delete old interpretation
            await profile_db.delete(existing_interp)

        profile_db.add(interpretation)
        await profile_db.commit()

        logger.info(
            f"Generated interpretation for observation {observation_id}: "
            f"severity={severity_level}, physician_review={safety_result.requires_physician_review}"
        )

        return InterpretationResult(
            success=True,
            interpretation=interpretation,
            safety_validation=safety_result,
        )

    async def interpret_panel(
        self,
        panel_name: str,
        collected_at: datetime,
        profile_id: str,
        profile_db: AsyncSession,
        master_db: AsyncSession,
        force_regenerate: bool = False,
    ) -> PanelInterpretationResult:
        """
        Generate holistic interpretation for a lab panel.

        Args:
            panel_name: Panel name (lipid, cbc, cmp, thyroid)
            collected_at: Collection date to match observations
            profile_id: Profile ID
            profile_db: Per-profile database session
            master_db: Master database session
            force_regenerate: Force regeneration

        Returns:
            PanelInterpretationResult
        """
        from api.observations import PANEL_DEFINITIONS

        panel_def = PANEL_DEFINITIONS.get(panel_name.lower())
        if not panel_def:
            return PanelInterpretationResult(
                success=False,
                error_message=f"Unknown panel: {panel_name}",
            )

        # Find observations for this panel
        start_date = collected_at.replace(hour=0, minute=0, second=0)
        end_date = collected_at.replace(hour=23, minute=59, second=59)

        result = await profile_db.execute(
            select(Observation).where(
                Observation.profile_id == profile_id,
                Observation.analyte_canonical.in_(panel_def["analytes"]),
                Observation.collected_at >= start_date,
                Observation.collected_at <= end_date,
            )
        )
        observations = result.scalars().all()

        if not observations:
            return PanelInterpretationResult(
                success=False,
                error_message=f"No observations found for panel {panel_name} on {collected_at.date()}",
            )

        # Check for existing interpretation
        if not force_regenerate:
            existing = await profile_db.execute(
                select(PanelInterpretation).where(
                    PanelInterpretation.panel_name == panel_name.lower(),
                    PanelInterpretation.collected_at >= start_date,
                    PanelInterpretation.collected_at <= end_date,
                )
            )
            existing_interp = existing.scalar_one_or_none()
            if existing_interp:
                return PanelInterpretationResult(
                    success=True,
                    interpretation=existing_interp,
                )

        # Get individual interpretations for each observation
        observation_summaries = []
        abnormal_count = 0
        observation_ids = []

        for obs in observations:
            observation_ids.append(obs.id)
            interp_result = await self.interpret_observation(
                observation_id=obs.id,
                profile_db=profile_db,
                master_db=master_db,
            )
            if interp_result.interpretation:
                summary = {
                    "analyte": obs.analyte_canonical,
                    "value": obs.value,
                    "unit": obs.unit,
                    "severity": interp_result.interpretation.severity_level,
                    "is_abnormal": obs.is_abnormal,
                }
                observation_summaries.append(summary)
                if obs.is_abnormal:
                    abnormal_count += 1

        # Generate panel summary
        summary_text = self._generate_panel_summary(
            panel_name=panel_name,
            panel_display_name=panel_def["name"],
            observation_summaries=observation_summaries,
        )

        # Determine overall status
        if abnormal_count == 0:
            overall_status = "normal"
        elif abnormal_count == 1:
            overall_status = "borderline"
        elif abnormal_count <= len(observations) / 2:
            overall_status = "abnormal"
        else:
            overall_status = "concerning"

        # Get relationship insights
        relationship_insights = await self._generate_relationship_insights(
            panel_name=panel_name,
            observations=observations,
            master_db=master_db,
        )

        # Generate panel advice
        advice_text = await self._generate_panel_advice(
            panel_name=panel_name,
            observation_summaries=observation_summaries,
            master_db=master_db,
        )

        # Build citations
        citations = []
        relationships = await self._knowledge_loader.get_panel_relationships(
            panel_name=panel_name,
            db=master_db,
        )
        for rel in relationships:
            citations.append({
                "type": "relationship",
                "id": rel.id,
                "text": rel.description,
            })

        panel_interpretation = PanelInterpretation(
            id=str(uuid.uuid4()),
            profile_id=profile_id,
            panel_name=panel_name.lower(),
            collected_at=collected_at,
            observation_ids_json=json.dumps(observation_ids),
            summary_text=summary_text,
            overall_status=overall_status,
            relationship_insights_json=json.dumps(relationship_insights) if relationship_insights else None,
            advice_text=advice_text if advice_text else None,
            citations_json=json.dumps(citations),
            model_id=self.MODEL_ID_TEMPLATE,
            confidence_score=0.80,
            requires_physician_review=overall_status == "concerning",
        )

        profile_db.add(panel_interpretation)
        await profile_db.commit()

        logger.info(
            f"Generated panel interpretation for {panel_name}: "
            f"status={overall_status}, abnormal_count={abnormal_count}"
        )

        return PanelInterpretationResult(
            success=True,
            interpretation=panel_interpretation,
        )

    async def _assemble_context(
        self,
        observation: Observation,
        profile_db: AsyncSession,
        master_db: AsyncSession,
    ) -> InterpretationContext:
        """Assemble context for interpretation generation."""
        context = InterpretationContext(observation=observation)

        # Get biomarker knowledge
        context.biomarker_info = await self._knowledge_loader.get_biomarker_knowledge(
            analyte_canonical=observation.analyte_canonical,
            db=master_db,
        )

        # Get historical values for trend analysis
        historical = await profile_db.execute(
            select(Observation).where(
                Observation.profile_id == observation.profile_id,
                Observation.analyte_canonical == observation.analyte_canonical,
                Observation.value.isnot(None),
                Observation.id != observation.id,
            ).order_by(Observation.collected_at.desc()).limit(5)
        )
        hist_obs = historical.scalars().all()

        current_canonical_unit = canonical_unit_for(observation.analyte_canonical)
        current_conv = None
        if observation.value is not None and current_canonical_unit is not None:
            current_conv = convert_to_canonical(
                observation.analyte_canonical,
                observation.value,
                observation.unit,
            )

        if current_conv is not None:
            context.comparison_unit = current_conv.canonical_unit
            context.comparison_current_value = current_conv.canonical_value
            context.historical_values = []
            for obs in hist_obs:
                if obs.collected_at and obs.value is not None:
                    hist_conv = convert_to_canonical(
                        observation.analyte_canonical,
                        obs.value,
                        obs.unit,
                    )
                    if hist_conv is None:
                        continue
                    context.historical_values.append(
                        (obs.collected_at, hist_conv.canonical_value)
                    )
        else:
            context.comparison_unit = observation.unit
            context.comparison_current_value = observation.value
            observation_unit_norm = normalize_unit(observation.unit or "")
            context.historical_values = [
                (obs.collected_at, obs.value)
                for obs in hist_obs
                if obs.collected_at
                and obs.value is not None
                and normalize_unit(obs.unit or "") == observation_unit_norm
            ]

        # Determine trend
        if context.historical_values and context.comparison_current_value is not None:
            prev_value = context.historical_values[0][1]
            current_value = context.comparison_current_value
            if abs(current_value - prev_value) / max(prev_value, 0.001) < 0.05:
                context.trend_direction = "stable"
            elif current_value > prev_value:
                # Higher could be better or worse depending on analyte
                context.trend_direction = "increasing"
            else:
                context.trend_direction = "decreasing"

        # Get recommendations
        if observation.value is not None:
            context.recommendations = await self._recommendation_engine.generate_recommendations(
                analyte_canonical=observation.analyte_canonical,
                value=observation.value,
                ref_low=observation.ref_low,
                ref_high=observation.ref_high,
                db=master_db,
            )

        return context

    async def _generate_interpretation(
        self,
        context: InterpretationContext,
        master_db: AsyncSession,
    ) -> tuple[str, Optional[str]]:
        """
        Generate interpretation text using templates.

        Returns tuple of (interpretation_text, advice_text).
        """
        obs = context.observation
        kb = context.biomarker_info

        # Build interpretation parts
        parts = []

        # Value summary
        value_str = f"{obs.value}" if obs.value is not None else obs.value_text or "not reported"
        unit_str = obs.unit or ""
        display_name = kb.display_name if kb else obs.analyte_canonical.upper()

        value_sentence = f"Your {display_name} result is {value_str}".strip()
        if unit_str:
            value_sentence += f" {unit_str}"
        if (
            context.comparison_unit
            and context.comparison_current_value is not None
            and normalize_unit(obs.unit or "") != normalize_unit(context.comparison_unit or "")
        ):
            value_sentence += f" (values compared in {context.comparison_unit})"
        value_sentence += "."
        parts.append(value_sentence)

        # Reference range context
        if obs.ref_low is not None and obs.ref_high is not None:
            parts.append(
                f"The reference range is {obs.ref_low}-{obs.ref_high} {unit_str}."
            )
        elif obs.ref_range_text:
            parts.append(f"Reference range: {obs.ref_range_text}.")

        # Status interpretation
        if obs.is_abnormal:
            if obs.flag in ["H", "HH", "HIGH"]:
                if kb:
                    parts.append(kb.high_interpretation + f" [KB:{kb.id}]")
                else:
                    parts.append("This value is above the reference range.")
            elif obs.flag in ["L", "LL", "LOW"]:
                if kb:
                    parts.append(kb.low_interpretation + f" [KB:{kb.id}]")
                else:
                    parts.append("This value is below the reference range.")
            else:
                parts.append("This value is outside the normal reference range.")
        else:
            if kb:
                parts.append(kb.normal_interpretation + f" [KB:{kb.id}]")
            else:
                parts.append("This value is within the normal reference range.")

        # Trend information
        if context.historical_values and context.comparison_current_value is not None:
            prev_date, prev_value = context.historical_values[0]
            prev_value_str = f"{round(prev_value, 2):g}"
            comparison_unit = context.comparison_unit or ""
            if context.trend_direction == "stable":
                parts.append(
                    f"This is stable compared to your previous result of {prev_value_str} {comparison_unit}."
                )
            elif context.trend_direction == "increasing":
                parts.append(
                    f"This has increased from your previous result of {prev_value_str} {comparison_unit}."
                )
            else:
                parts.append(
                    f"This has decreased from your previous result of {prev_value_str} {comparison_unit}."
                )

        # Clinical significance
        if kb and kb.clinical_significance:
            parts.append(f"\n\n**What this test measures:** {kb.description} [KB:{kb.id}]")

        interpretation_text = " ".join(parts)

        # Generate advice
        advice_text = None
        if context.recommendations and context.recommendations.has_recommendations:
            advice_text = self._recommendation_engine.format_recommendations_text(
                context.recommendations,
                include_rationale=False,
                include_citations=True,
            )

        return interpretation_text, advice_text

    def _classify_severity(
        self,
        value: Optional[float],
        ref_low: Optional[float],
        ref_high: Optional[float],
        biomarker_info: Optional[BiomarkerInfo],
    ) -> str:
        """Classify the severity level of a result."""
        if value is None:
            return "normal"

        # Check critical values first
        if biomarker_info:
            if biomarker_info.critical_low and value < biomarker_info.critical_low:
                return "critical_low"
            if biomarker_info.critical_high and value > biomarker_info.critical_high:
                return "critical_high"

        # Check against reference range
        if ref_low is not None and value < ref_low:
            pct_below = (ref_low - value) / ref_low * 100 if ref_low > 0 else 100
            if pct_below > 20:
                return "abnormal_low"
            return "borderline_low"

        if ref_high is not None and value > ref_high:
            pct_above = (value - ref_high) / ref_high * 100 if ref_high > 0 else 100
            if pct_above > 20:
                return "abnormal_high"
            return "borderline_high"

        return "normal"

    def _generate_citations(self, context: InterpretationContext) -> list[dict]:
        """Generate citations list for the interpretation."""
        citations = []

        if context.biomarker_info:
            citations.append({
                "type": "knowledge_base",
                "id": context.biomarker_info.id,
                "text": f"Biomarker knowledge: {context.biomarker_info.display_name}",
            })
            for source in context.biomarker_info.sources[:3]:
                citations.append({
                    "type": "source",
                    "id": source.get("id", ""),
                    "text": source.get("name", source.get("title", "")),
                })

        if context.recommendations:
            for rec in context.recommendations.recommendations:
                citations.append({
                    "type": "intervention",
                    "id": rec.id,
                    "text": rec.title,
                })

        return citations

    def _build_context_json(self, context: InterpretationContext) -> str:
        """Build context JSON for storage."""
        ctx = {
            "trend": context.trend_direction,
            "historical_count": len(context.historical_values),
            "comparison_unit": context.comparison_unit,
        }

        if context.historical_values:
            prev_date, prev_value = context.historical_values[0]
            ctx["prev_value"] = prev_value
            ctx["prev_date"] = prev_date.isoformat() if prev_date else None

            if context.comparison_current_value is not None and prev_value is not None:
                change = context.comparison_current_value - prev_value
                ctx["change"] = change
                ctx["change_percent"] = (change / prev_value) * 100 if prev_value != 0 else 0

        return json.dumps(ctx)

    # =========================================================================
    # Phase 0.3: LLM-based interpretation methods
    # =========================================================================

    async def _llm_interpretation(
        self,
        model: Any,
        context: InterpretationContext,
        profile_id: str,
        db: AsyncSession,
    ) -> tuple[str, Optional[str]]:
        """
        Generate interpretation using LLM with citation enforcement.

        Falls back to template if LLM output lacks required citations.

        Args:
            model: Loaded Llama model instance
            context: Interpretation context with observation and knowledge
            profile_id: User profile ID
            db: Database session

        Returns:
            Tuple of (interpretation_text, advice_text)
        """
        # Build the prompt
        prompt = self._build_llm_prompt(context)

        try:
            # Run inference in thread pool for async safety
            response = await self._model_selector.run_inference(
                model=model,
                prompt=prompt,
                max_tokens=512,
                temperature=0.3,
                stop=["</s>", "\n\n\n"],
            )

            text = response["choices"][0]["text"].strip()

            # Validate citations exist
            if not self._validate_llm_citations(text):
                logger.warning(
                    "LLM output missing required citations, falling back to template"
                )
                return await self._generate_interpretation(context, db)

            # Extract advice section if present
            advice_text = self._extract_advice_from_llm(text, context)

            return text, advice_text

        except Exception as e:
            logger.error(f"LLM interpretation failed: {e}, falling back to template")
            return await self._generate_interpretation(context, db)

    def _build_llm_prompt(self, context: InterpretationContext) -> str:
        """Build prompt for LLM interpretation."""
        obs = context.observation
        kb = context.biomarker_info

        # Build knowledge text from biomarker info
        knowledge_text = ""
        if kb:
            knowledge_text = f"""
- Display Name: {kb.display_name}
- Description: {kb.description}
- Normal Interpretation: {kb.normal_interpretation}
- High Interpretation: {kb.high_interpretation}
- Low Interpretation: {kb.low_interpretation}
- Clinical Significance: {kb.clinical_significance or 'Not specified'}
"""

        # Add recommendations if available
        if context.recommendations and context.recommendations.has_recommendations:
            knowledge_text += "\nRecommendations:\n"
            for rec in context.recommendations.recommendations[:3]:
                knowledge_text += f"- [{rec.id}] {rec.title}: {rec.text}\n"

        return LLM_INTERPRETATION_PROMPT.format(
            analyte=kb.display_name if kb else obs.analyte_canonical.upper(),
            value=obs.value if obs.value is not None else obs.value_text or "N/A",
            unit=obs.unit or "",
            ref_low=obs.ref_low or "N/A",
            ref_high=obs.ref_high or "N/A",
            flag=obs.flag or "normal",
            knowledge_text=knowledge_text,
        )

    def _validate_llm_citations(self, text: str) -> bool:
        """
        Check for required citation patterns in LLM output.

        Required patterns: [KB:*], [INT:*], or [Source:*]

        Args:
            text: LLM output text

        Returns:
            True if valid citations found, False otherwise.
        """
        pattern = r"\[KB:[^\]]+\]|\[INT:[^\]]+\]|\[Source:[^\]]+\]"
        return bool(re.search(pattern, text))

    def _extract_advice_from_llm(
        self,
        text: str,
        context: InterpretationContext,
    ) -> Optional[str]:
        """
        Extract advice section from LLM output.

        Args:
            text: LLM output text
            context: Interpretation context

        Returns:
            Advice text if found, None otherwise.
        """
        # Look for recommendation citations and extract advice
        advice_parts = []

        # Find sentences with [INT:*] citations
        int_pattern = r"[^.]*\[INT:[^\]]+\][^.]*\."
        matches = re.findall(int_pattern, text)
        if matches:
            advice_parts.extend(matches)

        # Add disclaimer
        if advice_parts:
            advice_parts.append(
                "\nAlways consult your healthcare provider before making "
                "changes to your diet, exercise, or lifestyle."
            )
            return " ".join(advice_parts)

        # Fall back to recommendation engine output
        if context.recommendations and context.recommendations.has_recommendations:
            return self._recommendation_engine.format_recommendations_text(
                context.recommendations,
                include_rationale=False,
                include_citations=True,
            )

        return None

    async def interpret_with_model(
        self,
        observation_id: str,
        profile_id: str,
        profile_db: AsyncSession,
        master_db: AsyncSession,
        force_regenerate: bool = False,
    ) -> InterpretationResult:
        """
        Generate interpretation using tiered model selection.

        This is the preferred entry point for Phase 0.3+ interpretations.
        Automatically selects the appropriate model tier based on user
        preference and hardware capability.

        Args:
            observation_id: The observation UUID
            profile_id: User profile ID
            profile_db: Per-profile database session
            master_db: Master database session
            force_regenerate: Force regeneration even if exists

        Returns:
            InterpretationResult with interpretation or error
        """
        # Get model for inference
        model, active_tier = await self._model_selector.get_model_for_inference(
            profile_id=profile_id,
            db=profile_db,
        )

        # If template mode, use standard method
        if active_tier == "template" or model is None:
            logger.info(f"Using template mode for observation {observation_id}")
            return await self.interpret_observation(
                observation_id=observation_id,
                profile_db=profile_db,
                master_db=master_db,
                force_regenerate=force_regenerate,
            )

        logger.info(f"Using LLM tier '{active_tier}' for observation {observation_id}")

        # Fetch observation
        result = await profile_db.execute(
            select(Observation).where(Observation.id == observation_id)
        )
        observation = result.scalar_one_or_none()

        if not observation:
            return InterpretationResult(
                success=False,
                error_message=f"Observation not found: {observation_id}",
            )

        # Assemble context
        context = await self._assemble_context(
            observation=observation,
            profile_db=profile_db,
            master_db=master_db,
        )

        # Generate LLM interpretation
        interpretation_text, advice_text = await self._llm_interpretation(
            model=model,
            context=context,
            profile_id=profile_id,
            db=profile_db,
        )

        # Classify severity
        severity_level = self._classify_severity(
            value=observation.value,
            ref_low=observation.ref_low,
            ref_high=observation.ref_high,
            biomarker_info=context.biomarker_info,
        )

        # Generate citations
        citations = self._generate_citations(context)

        # Validate safety
        safety_result = self._safety_guard.validate_interpretation(
            interpretation_text=interpretation_text,
            advice_text=advice_text,
            require_citations=True,
        )

        # Check for critical values
        if observation.value is not None:
            critical_result = self._safety_guard.check_critical_value(
                analyte_canonical=observation.analyte_canonical,
                value=observation.value,
                critical_low=context.biomarker_info.critical_low if context.biomarker_info else None,
                critical_high=context.biomarker_info.critical_high if context.biomarker_info else None,
            )
            if critical_result.requires_physician_review:
                safety_result.requires_physician_review = True
                safety_result.physician_review_reason = critical_result.physician_review_reason

        # Ensure disclaimers
        interpretation_text, advice_text = self._safety_guard.add_required_disclaimers(
            interpretation_text=interpretation_text,
            advice_text=advice_text,
        )

        # Build context JSON
        context_json = self._build_context_json(context)

        # Safety validation JSON
        safety_json = json.dumps({
            "passed": safety_result.passed,
            "checks_passed": safety_result.checks_passed,
            "checks_failed": safety_result.checks_failed,
            "warnings": safety_result.warnings,
        })

        # Get model ID from tier config
        from .model_selector import TIER_MODEL_CONFIG
        model_config = TIER_MODEL_CONFIG.get(active_tier, {})
        model_id = model_config.get("description", f"llm-{active_tier}")

        # Handle regeneration
        if force_regenerate:
            existing = await profile_db.execute(
                select(LabInterpretation).where(
                    LabInterpretation.observation_id == observation_id
                )
            )
            existing_interp = existing.scalar_one_or_none()
        else:
            existing_interp = None

        interpretation = LabInterpretation(
            id=str(uuid.uuid4()),
            profile_id=observation.profile_id,
            observation_id=observation_id,
            interpretation_text=interpretation_text,
            severity_level=severity_level,
            advice_text=advice_text if advice_text else None,
            citations_json=json.dumps(citations),
            context_json=context_json,
            model_id=model_id,
            model_tier=active_tier,
            confidence_score=0.90 if active_tier == "high" else 0.85,
            requires_physician_review=safety_result.requires_physician_review,
            physician_review_reason=safety_result.physician_review_reason,
            safety_validation_json=safety_json,
            regeneration_count=0,
        )

        if force_regenerate and existing_interp:
            interpretation.regeneration_count = existing_interp.regeneration_count + 1
            interpretation.previous_interpretation_id = existing_interp.id
            await profile_db.delete(existing_interp)

        profile_db.add(interpretation)
        await profile_db.commit()

        logger.info(
            f"Generated LLM interpretation for observation {observation_id}: "
            f"tier={active_tier}, severity={severity_level}"
        )

        return InterpretationResult(
            success=True,
            interpretation=interpretation,
            safety_validation=safety_result,
        )

    def _generate_panel_summary(
        self,
        panel_name: str,
        panel_display_name: str,
        observation_summaries: list[dict],
    ) -> str:
        """Generate a summary text for a panel interpretation."""
        parts = [f"Your {panel_display_name} results:"]
        parts.append("")

        normal_count = 0
        abnormal_items = []

        for summary in observation_summaries:
            analyte = summary["analyte"].upper()
            value = summary["value"]
            unit = summary.get("unit", "")
            is_abnormal = summary.get("is_abnormal", False)

            if is_abnormal:
                severity = summary.get("severity", "abnormal")
                if "high" in severity:
                    abnormal_items.append(f"{analyte}: {value} {unit} (above normal)")
                elif "low" in severity:
                    abnormal_items.append(f"{analyte}: {value} {unit} (below normal)")
                else:
                    abnormal_items.append(f"{analyte}: {value} {unit} (abnormal)")
            else:
                normal_count += 1

        if abnormal_items:
            parts.append("**Items requiring attention:**")
            for item in abnormal_items:
                parts.append(f"- {item}")
            parts.append("")

        if normal_count > 0:
            parts.append(f"{normal_count} of {len(observation_summaries)} values are within normal range.")

        # Add disclaimer
        parts.append("")
        parts.append(
            "This summary is for educational purposes only. "
            "Please consult your healthcare provider for personalized interpretation."
        )

        return "\n".join(parts)

    async def _generate_relationship_insights(
        self,
        panel_name: str,
        observations: list[Observation],
        master_db: AsyncSession,
    ) -> list[dict]:
        """Generate insights from biomarker relationships in a panel."""
        insights = []

        relationships = await self._knowledge_loader.get_panel_relationships(
            panel_name=panel_name,
            db=master_db,
        )

        # Build lookup for observation values
        obs_values = {obs.analyte_canonical: obs.value for obs in observations}

        for rel in relationships:
            if rel.relationship_type == "ratio" and rel.ratio_calculation:
                # Calculate ratio if both values present
                try:
                    # Simple ratio calculation (primary / related)
                    primary_val = obs_values.get(rel.primary_analyte)
                    related_val = obs_values.get(rel.related_analyte)

                    if primary_val is not None and related_val is not None and related_val != 0:
                        ratio = primary_val / related_val

                        # Determine status from target range
                        status = "unknown"
                        if rel.ratio_target_range:
                            optimal = rel.ratio_target_range.get("optimal", [])
                            if optimal and len(optimal) >= 2:
                                if optimal[0] <= ratio <= optimal[1]:
                                    status = "optimal"
                                elif ratio < optimal[0]:
                                    status = "low"
                                else:
                                    status = "high"

                        insights.append({
                            "relationship": f"{rel.primary_analyte}_{rel.related_analyte}_ratio",
                            "value": round(ratio, 2),
                            "status": status,
                            "interpretation": rel.clinical_significance,
                            "source_id": rel.id,
                        })
                except (TypeError, ZeroDivisionError):
                    pass

        return insights

    async def _generate_panel_advice(
        self,
        panel_name: str,
        observation_summaries: list[dict],
        master_db: AsyncSession,
    ) -> Optional[str]:
        """Generate consolidated advice for a panel."""
        # Get recommendations for abnormal values
        obs_list = [
            {
                "analyte_canonical": s["analyte"],
                "value": s["value"],
                "ref_low": s.get("ref_low"),
                "ref_high": s.get("ref_high"),
            }
            for s in observation_summaries
            if s.get("is_abnormal")
        ]

        if not obs_list:
            return None

        rec_sets = await self._recommendation_engine.generate_panel_recommendations(
            panel_name=panel_name,
            observations=obs_list,
            db=master_db,
            max_per_analyte=2,
            max_total=6,
        )

        if not rec_sets:
            return None

        # Format combined advice
        advice_parts = ["**Recommendations based on your panel results:**", ""]

        for rec_set in rec_sets:
            if rec_set.has_recommendations:
                advice_parts.append(f"For {rec_set.analyte_canonical.upper()}:")
                for rec in rec_set.recommendations:
                    advice_parts.append(f"- {rec.title}: {rec.text} [INT:{rec.id}]")
                advice_parts.append("")

        advice_parts.append(
            "Always consult your healthcare provider before making "
            "changes to your diet, exercise, or lifestyle."
        )

        return "\n".join(advice_parts)


# Global instance
_interpret_module: Optional[InterpretModule] = None


def get_interpret_module() -> InterpretModule:
    """Get or create the global interpret module instance."""
    global _interpret_module
    if _interpret_module is None:
        _interpret_module = InterpretModule()
    return _interpret_module
