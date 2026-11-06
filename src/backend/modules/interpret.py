"""
Main interpretation pipeline for lab results.

Orchestrates the generation of AI-powered lab result interpretations
using the knowledge base, safety guardrails, and recommendation engine.

Phase 1: Core Lab Interpretation Engine - Main Orchestrator
"""

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import LabInterpretation, Observation, PanelInterpretation
from modules.agent.guardrails.templates import ESCALATE_TEMPLATE
from modules.normalize import (
    UNIT_CONVERSIONS,
    canonical_unit_for,
    convert_to_canonical,
    normalize_unit,
)

from .interpret_safety import (
    InterpretationSafetyGuard,
    SafetyValidationResult,
    get_safety_guard,
)
from .knowledge_loader import (
    BiomarkerInfo,
    KnowledgeLoader,
    get_knowledge_loader,
)
from .model_selector import ModelSelector, get_model_selector
from .recommend import (
    RecommendationEngine,
    RecommendationSet,
    get_recommendation_engine,
)

logger = logging.getLogger(__name__)

# VALUE-RANGE-COMPARE: the status sentences a card says when there is no knowledge-base
# entry. The status block writes them and the saved-card check reads them back.
SENTENCE_ABOVE = "This value is above the reference range."
SENTENCE_BELOW = "This value is below the reference range."
SENTENCE_WITHIN = "This value is within the normal reference range."
SENTENCE_OUTSIDE = "This value is outside the normal reference range."

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
    # INTERP-WITHHOLD-MSG: True only when the safety check withheld the card.
    withheld: bool = False
    # VALUE-RANGE-COMPARE: True only when a saved card was deleted and replaced by this call.
    replaced: bool = False


@dataclass
class PanelInterpretationResult:
    """Result of generating a panel interpretation."""
    success: bool
    interpretation: Optional[PanelInterpretation] = None
    error_message: Optional[str] = None
    # VALUE-RANGE-COMPARE: members whose rebuild the safety check withheld, as
    # (observation_id, result). Set only on the fail-closed return, which happens when the
    # read replaces a saved panel or the withheld member has a saved card.
    withheld_members: list[tuple[str, InterpretationResult]] = field(default_factory=list)
    # VALUE-RANGE-COMPARE: ids of the member cards this read deleted and rebuilt, set on the
    # success and the fail-closed return (a sibling rebuilt before a withheld member stays).
    replaced_member_ids: list[str] = field(default_factory=list)


# KB-UNIT-BADGE: spellings of the cell-count unit 10^3/uL the extractor writes (extract.py
# _UNIT_ALT), for white cells and platelets only. The first group is numerically identical
# (factor 1); cells/uL is divided by 1000. Any other spelling is not converted. normalize_unit
# folds the superscript in "10³/µL" to "103/ul", so that key is listed as it folds.
_CELL_COUNT_ANALYTES = {"white_blood_cells", "platelets"}
_CELL_COUNT_UNIT = normalize_unit("10^3/uL")
_CELL_COUNT_FACTORS = {
    normalize_unit(spelling): factor
    for spelling, factor in (
        ("x10E3/uL", 1.0), ("x10^3/uL", 1.0), ("10*3/uL", 1.0), ("K/uL", 1.0),
        ("10^3/µL", 1.0), ("10³/µL", 1.0), ("10^9/L", 1.0), ("x10^9/L", 1.0),
        ("cells/uL", 0.001),
    )
}


# KB-UNIT-BADGE: exact definitions for a KB unit of mg/dL (not clinical factors): mg per 100 mL
# is mg/dL, and 1 g/L is 100 mg/dL.
_MG_DL_UNIT = normalize_unit("mg/dL")
_MG_DL_FACTORS = {normalize_unit("mg%"): 1.0, normalize_unit("g/L"): 100.0}


def value_in_kb_unit(info: BiomarkerInfo, value: float, unit: Optional[str]) -> Optional[float]:
    """KB-UNIT-BADGE (D1): `value`, reported in `unit`, in the unit the KB's critical limits use.

    Same unit after normalising: the value as is. White cells and platelets: the listed
    spellings above. A mg/dL KB unit: mg% (x1) and g/L (x100). Otherwise the value is converted with normalize.convert_to_canonical (the
    app's one tested table); it is used when the canonical unit is the KB's standard_unit, or
    when the KB unit is another listed variant of the same table entry (converted with that
    entry's own factor). None (no critical check) for a missing unit, an unconvertible unit,
    or any other KB unit. Never guesses a factor.
    """
    reported = normalize_unit(unit or "")
    standard = normalize_unit(info.standard_unit or "")
    if not reported or not standard:
        return None
    if reported == standard:
        return value
    if info.analyte_canonical in _CELL_COUNT_ANALYTES and standard == _CELL_COUNT_UNIT:
        factor = _CELL_COUNT_FACTORS.get(reported)
        return None if factor is None else value * factor
    if standard == _MG_DL_UNIT and reported in _MG_DL_FACTORS:
        return value * _MG_DL_FACTORS[reported]
    converted = convert_to_canonical(info.analyte_canonical, value, unit)
    if converted is None:
        return None
    if normalize_unit(converted.canonical_unit) == standard:
        return converted.canonical_value
    entry = UNIT_CONVERSIONS.get(info.analyte_canonical.lower())
    kb_factor = entry[1].get(standard) if entry else None
    if not kb_factor:
        return None
    return converted.canonical_value / kb_factor


def _fmt_number(number: float) -> str:
    """No trailing .0 (10 significant digits, so a large count never prints as 1e+06)."""
    return f"{number:.10g}"


def _fmt_converted(number: float, limit: Optional[float] = None) -> str:
    """One decimal under 100, none from 100; up to two more decimals while the rounded number
    would print equal to the threshold (so never '190 mg/dL is above 190 mg/dL')."""
    first = 0 if abs(number) >= 100 else 1
    text = f"{number:.{first}f}"
    for digits in (first + 1, first + 2):
        if limit is None or float(text) != limit:
            break
        text = f"{number:.{digits}f}"
    return text


def _sentence_unit(unit: str) -> str:
    """The KB count unit reads as the extractor and labs write it."""
    return "x10^3/uL" if normalize_unit(unit) == _CELL_COUNT_UNIT else unit


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
                # VALUE-RANGE-COMPARE: a saved template card the range check disagrees
                # with is rebuilt by the force path below (one copy of the card logic).
                if await self._saved_card_is_stale(existing_interp, observation, master_db):
                    force_regenerate = True
                else:
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
            unit=observation.unit,
        )

        # Generate citations
        citations = self._generate_citations(context)

        # Ensure disclaimers
        interpretation_text, advice_text = self._safety_guard.add_required_disclaimers(
            interpretation_text=interpretation_text,
            advice_text=advice_text,
        )

        # Validate safety
        safety_result = self._safety_guard.validate_interpretation(
            interpretation_text=interpretation_text,
            advice_text=advice_text,
            require_citations=True,
        )

        # Check for critical values. INTERP-WITHHOLD-MSG (OQ-IWM-CRIT): this runs
        # before the withhold so a withheld card still carries the flag.
        # KB-UNIT-BADGE (D2): the banner follows the badge's unit rule.
        self._apply_critical_check(observation, context.biomarker_info, safety_result)

        # INTERP-SAFETY-ENFORCE: a card that fails the safety check is withheld.
        # Nothing is saved, deleted or committed before this return. The log
        # names the observation and the check types only, never the text.
        if not safety_result.passed:
            logger.warning(
                "Withholding interpretation for observation %s: safety checks failed: %s",
                observation_id, safety_result.checks_failed,
            )
            return InterpretationResult(
                success=False,
                error_message=ESCALATE_TEMPLATE,
                safety_validation=safety_result,
                withheld=True,
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

        replaced = False
        if force_regenerate and existing_interp:
            interpretation.regeneration_count = existing_interp.regeneration_count + 1
            interpretation.previous_interpretation_id = existing_interp.id
            # Delete old interpretation
            await profile_db.delete(existing_interp)
            await profile_db.flush()
            replaced = True

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
            replaced=replaced,
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
        observations = await _panel_members(profile_db, panel_def, profile_id, collected_at)

        if not observations:
            return PanelInterpretationResult(
                success=False,
                error_message=f"No observations found for panel {panel_name} on {collected_at.date()}",
            )

        # Check for existing interpretation
        stale_panel: Optional[PanelInterpretation] = None
        if not force_regenerate:
            existing_interp = await _saved_panel(profile_db, panel_name, collected_at)
            if existing_interp:
                # VALUE-RANGE-COMPARE: a saved template panel the range check disagrees
                # with is rebuilt below. The old row is held and deleted just before the add.
                if await self._saved_panel_is_stale(existing_interp, observations, profile_db):
                    stale_panel = existing_interp
                else:
                    return PanelInterpretationResult(
                        success=True,
                        interpretation=existing_interp,
                    )

        # Get individual interpretations for each observation
        observation_summaries = []
        abnormal_count = 0
        observation_ids = []
        withheld_members: list[tuple[str, InterpretationResult]] = []
        replaced_member_ids: list[str] = []
        # VALUE-RANGE-COMPARE: members that have a saved card before this read starts.
        saved_card_ids = set((await profile_db.execute(
            select(LabInterpretation.observation_id).where(
                LabInterpretation.observation_id.in_([o.id for o in observations])
            )
        )).scalars().all())

        from api.observations import (  # lazy: api imports modules
            observation_range_status,
            status_is_abnormal,
        )

        for obs in observations:
            observation_ids.append(obs.id)
            interp_result = await self.interpret_observation(
                observation_id=obs.id,
                profile_db=profile_db,
                master_db=master_db,
            )
            if interp_result.replaced is True:
                replaced_member_ids.append(obs.id)
            if interp_result.withheld is True and (
                stale_panel is not None or obs.id in saved_card_ids
            ):
                # A read that replaces a saved panel, or a member that already had a card,
                # never drops a withheld member: the saved panel (and the member's old card)
                # stay as they are. Keep going so every other stale member is still rebuilt
                # and every withheld one is named. A first-generation member with no saved
                # card is still dropped (report only, HC-VRC-027).
                withheld_members.append((obs.id, interp_result))
                continue
            if interp_result.interpretation:
                # VALUE-RANGE-COMPARE: the same status the sentence uses; "disagrees" and
                # "keep" fall back to the stored is_abnormal.
                is_abnormal = status_is_abnormal(
                    observation_range_status(
                        obs.flag, obs.value, obs.ref_low, obs.ref_high,
                        bool((obs.ref_range_text or "").strip()),
                    ),
                    obs.is_abnormal,
                )
                summary = {
                    "analyte": obs.analyte_canonical,
                    "value": obs.value,
                    "unit": obs.unit,
                    "severity": interp_result.interpretation.severity_level,
                    "is_abnormal": is_abnormal,
                }
                observation_summaries.append(summary)
                if is_abnormal:
                    abnormal_count += 1

        if withheld_members:
            logger.warning(
                "Panel %s: %d member(s) withheld on a rebuild; the saved panel is kept",
                panel_name, len(withheld_members),
            )
            return PanelInterpretationResult(
                success=False,
                error_message=ESCALATE_TEMPLATE,
                withheld_members=withheld_members,
                replaced_member_ids=replaced_member_ids,
            )

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

        if stale_panel is not None:
            # panel_interpretations has no unique constraint, so a rebuild must remove the
            # old row or the next cached lookup finds two (MultipleResultsFound).
            await profile_db.delete(stale_panel)
            await profile_db.flush()

        profile_db.add(panel_interpretation)
        await profile_db.commit()

        logger.info(
            f"Generated panel interpretation for {panel_name}: "
            f"status={overall_status}, abnormal_count={abnormal_count}"
        )

        return PanelInterpretationResult(
            success=True,
            interpretation=panel_interpretation,
            replaced_member_ids=replaced_member_ids,
        )

    async def _saved_card_is_stale(
        self,
        card: LabInterpretation,
        observation: Observation,
        master_db: AsyncSession,
    ) -> bool:
        """VALUE-RANGE-COMPARE: does a saved template card say the opposite of the range check?

        A card stores no status, so the saved sentence is read. Only a card this module's
        template wrote is judged (model-written cards are left alone). Only the helper's
        "above", "below" and "within" can make a card stale; "disagrees", "keep" and
        "normal_uncompared" never do, and neither does "outside" on an out-of-range value
        (it is not false) or a card with no readable claim. Reads only: no write, no model.
        """
        if card.model_tier != self.MODEL_TIER_TEMPLATE or card.model_id != self.MODEL_ID_TEMPLATE:
            return False
        # KB-UNIT-BADGE (D3): the unit fix changes a result only when the observation's unit is
        # missing or is not the KB's unit. A card counts as critical when its badge says so or it
        # carries the physician-review flag (template cards get that flag only from the critical
        # check). It is rebuilt when the unit is missing, or the value converts, and a critical
        # label is involved and the new result differs. A present unit that cannot be converted
        # never downgrades a saved critical. A same-unit difference is a KB revision: not stale.
        kb_row = await self._knowledge_loader.get_biomarker_knowledge(
            analyte_canonical=observation.analyte_canonical,
            db=master_db,
        )
        reported_unit = normalize_unit(observation.unit or "")
        if kb_row is not None and (
            not reported_unit or reported_unit != normalize_unit(kb_row.standard_unit or "")
        ):
            in_kb_unit = (
                None if observation.value is None
                else value_in_kb_unit(kb_row, observation.value, observation.unit)
            )
            if not reported_unit or in_kb_unit is not None:
                new_severity = self._classify_severity(
                    value=observation.value,
                    ref_low=observation.ref_low,
                    ref_high=observation.ref_high,
                    biomarker_info=kb_row,
                    unit=observation.unit,
                )
                # the banner can also come from the guard's default table (no KB limit)
                new_critical = new_severity.startswith("critical") or (
                    in_kb_unit is not None
                    and self._safety_guard.check_critical_value(
                        observation.analyte_canonical, in_kb_unit,
                        kb_row.critical_low, kb_row.critical_high,
                    ).requires_physician_review
                )
                saved_flag = bool(card.requires_physician_review)
                saved_critical = (card.severity_level or "").startswith("critical") or saved_flag
                if (saved_critical or new_critical) and (
                    card.severity_level != new_severity or saved_flag != new_critical
                ):
                    return True
        from api.observations import observation_range_status  # lazy: api imports modules

        status = observation_range_status(
            observation.flag, observation.value, observation.ref_low, observation.ref_high,
            bool((observation.ref_range_text or "").strip()),
        )
        if status not in ("above", "below", "within"):
            return False

        text = card.interpretation_text or ""
        # Every sentence a card of each kind can hold: the literals, and, only when the card
        # carries a [KB:] marker, the knowledge-base entry's own texts.
        sentences: dict[str, list[str]] = {
            "above": [SENTENCE_ABOVE],
            "below": [SENTENCE_BELOW],
            "within": [SENTENCE_WITHIN],
            "outside": [SENTENCE_OUTSIDE],
        }
        if "[KB:" in text:
            kb = await self._knowledge_loader.get_biomarker_knowledge(
                analyte_canonical=observation.analyte_canonical,
                db=master_db,
            )
            if kb is not None:
                for place, kb_text in (
                    ("above", kb.high_interpretation),
                    ("below", kb.low_interpretation),
                    ("within", kb.normal_interpretation),
                ):
                    if (kb_text or "").strip():  # an empty text would match every KB card
                        # the words and the marker, not the id: each install seeds its own KB
                        # row ids, so a restored vault holds cards naming another row's id
                        sentences[place].append(f"{kb_text} [KB:")

        def says(place: str) -> bool:
            return any(sentence in text for sentence in sentences[place])

        # The correct claim is checked first, so another sentence inside a knowledge-base
        # text can never make a card that already says the right thing rewrite on every read.
        if says(status):
            return False
        # "outside" is false only for a value inside the range, never for above or below.
        wrong = {
            "above": ("within", "below"),
            "below": ("within", "above"),
            "within": ("outside", "above", "below"),
        }[status]
        return any(says(place) for place in wrong)

    async def _saved_panel_is_stale(
        self,
        panel: PanelInterpretation,
        observations: list[Observation],
        profile_db: AsyncSession,
    ) -> bool:
        """VALUE-RANGE-COMPARE: does a saved template panel list the wrong values as abnormal?

        For each member that has a saved card (a member with no saved card is skipped),
        with helper status above, below or within, compare status_is_abnormal against
        whether the saved summary has an attention line `- ANALYTE: value `. Any mismatch is
        stale. "disagrees", "keep" and "normal_uncompared" do not count. Model_id other than
        the template's is left alone.
        """
        if panel.model_id != self.MODEL_ID_TEMPLATE:
            return False
        try:
            saved_ids = json.loads(panel.observation_ids_json or "[]")
        except (TypeError, ValueError):
            return False
        if not isinstance(saved_ids, list):
            return False
        members = [o for o in observations if o.id in set(saved_ids)]
        if not members:
            return False
        from api.observations import (  # lazy: api imports modules
            observation_range_status,
            status_is_abnormal,
        )

        have_card = set((await profile_db.execute(
            select(LabInterpretation.observation_id).where(
                LabInterpretation.observation_id.in_([o.id for o in members])
            )
        )).scalars().all())
        lines = (panel.summary_text or "").splitlines()
        wanted: dict[str, set[bool]] = {}
        for obs in members:
            if obs.id not in have_card:
                continue
            status = observation_range_status(
                obs.flag, obs.value, obs.ref_low, obs.ref_high,
                bool((obs.ref_range_text or "").strip()),
            )
            if status not in ("above", "below", "within"):
                continue
            prefix = f"- {obs.analyte_canonical.upper()}: {obs.value} "
            wanted.setdefault(prefix, set()).add(status_is_abnormal(status, obs.is_abnormal))
        for prefix, wants in wanted.items():
            # two members with one prefix and different answers cannot be told apart by the
            # saved text; leave them, so such a panel is never rewritten on every read
            if len(wants) == 1 and (next(iter(wants)) != any(line.startswith(prefix) for line in lines)):
                return True
        return False

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
            # Untabled analyte (or unit unrecognized): we can't normalize,
            # so only exclude a historical point when both it and the
            # current observation have a unit AND those units clearly
            # differ. A missing/blank unit on either side isn't treated
            # as a mismatch (common OCR extraction gap) — this keeps the
            # pre-fix permissiveness for the common case while still
            # guarding against comparing two visibly different units.
            context.historical_values = [
                (obs.collected_at, obs.value)
                for obs in hist_obs
                if obs.collected_at
                and obs.value is not None
                and (
                    not observation_unit_norm
                    or not normalize_unit(obs.unit or "")
                    or normalize_unit(obs.unit or "") == observation_unit_norm
                )
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
        elif (obs.ref_range_text or "").strip():
            parts.append(f"Reference range: {obs.ref_range_text}.")

        # Status interpretation. VALUE-RANGE-COMPARE: the value is read against its
        # numeric range. "disagrees" and "keep" take today's branch by the stored
        # is_abnormal and the flag exactly as printed; no wording is written for them.
        from api.observations import observation_range_status  # lazy: api imports modules

        status = observation_range_status(
            obs.flag, obs.value, obs.ref_low, obs.ref_high,
            bool((obs.ref_range_text or "").strip()),
        )
        is_abnormal, flag = obs.is_abnormal, obs.flag
        if status == "above":
            is_abnormal, flag = True, "H"
        elif status == "below":
            is_abnormal, flag = True, "L"
        elif status in ("within", "normal_uncompared"):
            is_abnormal = False

        if is_abnormal:
            if flag in ["H", "HH", "HIGH"]:
                if kb:
                    parts.append(kb.high_interpretation + f" [KB:{kb.id}]")
                else:
                    parts.append(SENTENCE_ABOVE)
            elif flag in ["L", "LL", "LOW"]:
                if kb:
                    parts.append(kb.low_interpretation + f" [KB:{kb.id}]")
                else:
                    parts.append(SENTENCE_BELOW)
            else:
                parts.append(SENTENCE_OUTSIDE)
        else:
            if (
                obs.ref_low is None
                and obs.ref_high is None
                and not (obs.ref_range_text or "").strip()
            ):
                parts.append(
                    "This report did not include a reference range, "
                    "so this result can't be compared to one."
                )
            elif kb:
                parts.append(kb.normal_interpretation + f" [KB:{kb.id}]")
            else:
                parts.append(SENTENCE_WITHIN)

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

    def _apply_critical_check(
        self,
        observation: Observation,
        info: Optional[BiomarkerInfo],
        safety_result: Any,
    ) -> None:
        """Set the physician-review flag and reason from the critical-value check.

        With a KB row the value is checked in the KB's unit (same rule as the badge); a missing
        or unconvertible unit makes no check. The sentence then shows the patient's number and
        unit first and the converted number beside it. Without a KB row nothing changes: the
        guard compares the raw value with its default table.
        """
        if observation.value is None:
            return
        if info is None:
            result = self._safety_guard.check_critical_value(
                analyte_canonical=observation.analyte_canonical,
                value=observation.value,
                critical_low=None,
                critical_high=None,
            )
            if result.requires_physician_review:
                safety_result.requires_physician_review = True
                safety_result.physician_review_reason = result.physician_review_reason
            return
        in_kb_unit = value_in_kb_unit(info, observation.value, observation.unit)
        if in_kb_unit is None:
            return
        result = self._safety_guard.check_critical_value(
            analyte_canonical=observation.analyte_canonical,
            value=in_kb_unit,
            critical_low=info.critical_low,
            critical_high=info.critical_high,
        )
        if not result.requires_physician_review:
            return
        defaults = self._safety_guard.DEFAULT_CRITICAL_THRESHOLDS.get(
            observation.analyte_canonical.lower(), {}
        )
        low = "critical_low_value" in result.warnings
        limit = info.critical_low if low else info.critical_high
        if limit is None:
            limit = defaults.get("critical_low" if low else "critical_high")
        kb_unit = _sentence_unit(info.standard_unit)
        patient_unit = (observation.unit or "").strip()
        shown = f"{_fmt_number(observation.value)} {patient_unit}"
        # A factor of exactly 1 is a relabel: no parenthesis, and the limit in the patient's unit.
        relabel = value_in_kb_unit(info, 1.0, observation.unit) == 1.0
        if not relabel:
            shown += f" ({_fmt_converted(in_kb_unit, limit)} {kb_unit})"
        safety_result.requires_physician_review = True
        safety_result.physician_review_reason = (
            f"Critical {'low' if low else 'high'} value: {shown} is "
            f"{'below' if low else 'above'} the critical threshold of "
            f"{_fmt_number(limit)} {patient_unit if relabel else kb_unit}."
        )

    def _classify_severity(
        self,
        value: Optional[float],
        ref_low: Optional[float],
        ref_high: Optional[float],
        biomarker_info: Optional[BiomarkerInfo],
        unit: Optional[str] = None,
    ) -> str:
        """Classify the severity level of a result."""
        if value is None:
            return "normal"

        # Check critical values first. KB-UNIT-BADGE: the limits are in the KB's unit, so the
        # value is compared in that unit; a missing or unconvertible unit is never critical.
        if biomarker_info:
            in_kb_unit = value_in_kb_unit(biomarker_info, value, unit)
            if in_kb_unit is not None:
                if biomarker_info.critical_low and in_kb_unit < biomarker_info.critical_low:
                    return "critical_low"
                if biomarker_info.critical_high and in_kb_unit > biomarker_info.critical_high:
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
            logger.error("LLM interpretation failed: %s, falling back to template", type(e).__name__)
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

        # VALUE-RANGE-COMPARE: an unflagged result outside its range goes to the model as
        # H or L, not "normal". A printed flag stays exactly as printed.
        flag = obs.flag
        if flag is None:
            from api.observations import observation_range_status  # lazy: api imports modules

            flag = {"above": "H", "below": "L"}.get(
                observation_range_status(None, obs.value, obs.ref_low, obs.ref_high)
            )

        return LLM_INTERPRETATION_PROMPT.format(
            analyte=kb.display_name if kb else obs.analyte_canonical.upper(),
            value=obs.value if obs.value is not None else obs.value_text or "N/A",
            unit=obs.unit or "",
            ref_low=obs.ref_low or "N/A",
            ref_high=obs.ref_high or "N/A",
            flag=flag or "normal",
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
            unit=observation.unit,
        )

        # Generate citations
        citations = self._generate_citations(context)

        # Ensure disclaimers
        interpretation_text, advice_text = self._safety_guard.add_required_disclaimers(
            interpretation_text=interpretation_text,
            advice_text=advice_text,
        )

        # Validate safety
        safety_result = self._safety_guard.validate_interpretation(
            interpretation_text=interpretation_text,
            advice_text=advice_text,
            require_citations=True,
        )

        # Check for critical values. INTERP-WITHHOLD-MSG (OQ-IWM-CRIT): this runs
        # before the withhold so a withheld card still carries the flag.
        # KB-UNIT-BADGE (D2): the banner follows the badge's unit rule.
        self._apply_critical_check(observation, context.biomarker_info, safety_result)

        # INTERP-SAFETY-ENFORCE: a card that fails the safety check is withheld.
        # Nothing is saved, deleted or committed before this return. The log
        # names the observation and the check types only, never the text.
        if not safety_result.passed:
            logger.warning(
                "Withholding interpretation for observation %s: safety checks failed: %s",
                observation_id, safety_result.checks_failed,
            )
            return InterpretationResult(
                success=False,
                error_message=ESCALATE_TEMPLATE,
                safety_validation=safety_result,
                withheld=True,
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
            await profile_db.flush()

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


async def saved_card_needs_rebuild(
    observation: Observation,
    profile_db: AsyncSession,
    master_db: AsyncSession,
) -> bool:
    """VALUE-RANGE-COMPARE: would a read of this observation's saved card rebuild it?

    A route asks before the read so it can write the started audit row first (the rebuild
    deletes the saved card). Same check the module makes at its cached return. Reads only:
    no write, no model. False when there is no saved card.
    """
    saved = (await profile_db.execute(
        select(LabInterpretation).where(LabInterpretation.observation_id == observation.id)
    )).scalar_one_or_none()
    if saved is None:
        return False
    return await get_interpret_module()._saved_card_is_stale(saved, observation, master_db)


async def _panel_members(
    profile_db: AsyncSession,
    panel_def: dict,
    profile_id: str,
    collected_at: datetime,
) -> list[Observation]:
    """The observations a panel read covers: this profile's panel analytes on the whole day.

    One select for `interpret_panel` and for `panel_rebuild_at_risk`, so the route's check
    cannot drift from the read it guards.
    """
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
    return list(result.scalars().all())


async def _saved_panel(
    profile_db: AsyncSession,
    panel_name: str,
    collected_at: datetime,
) -> Optional[PanelInterpretation]:
    """The saved panel row of that day, or None (shared by the read and its check)."""
    start_date = collected_at.replace(hour=0, minute=0, second=0)
    end_date = collected_at.replace(hour=23, minute=59, second=59)
    existing = await profile_db.execute(
        select(PanelInterpretation).where(
            PanelInterpretation.panel_name == panel_name.lower(),
            PanelInterpretation.collected_at >= start_date,
            PanelInterpretation.collected_at <= end_date,
        )
    )
    return existing.scalar_one_or_none()


async def panel_rebuild_at_risk(
    panel_name: str,
    collected_at: datetime,
    profile_id: str,
    profile_db: AsyncSession,
    master_db: AsyncSession,
    force_regenerate: bool,
) -> tuple[Optional[str], list[str]]:
    """VALUE-RANGE-COMPARE: what would a panel read delete? (stale panel id or None, stale member ids)

    A route asks before the read so it can write the started audit row first. It follows
    `interpret_panel`'s branches: no members is nothing at risk; an unforced read with a saved
    panel in agreement answers from it and touches no member; an unforced read otherwise
    names the stale saved panel (if any) and every member whose saved card is stale; a forced
    read skips the saved panel lookup (it deletes no panel row) and names stale members only.
    Reads only: no write, no model.
    """
    from api.observations import PANEL_DEFINITIONS  # lazy: api imports modules

    panel_def = PANEL_DEFINITIONS.get(panel_name.lower())
    if not panel_def:
        return None, []
    observations = await _panel_members(profile_db, panel_def, profile_id, collected_at)
    if not observations:
        return None, []
    stale_panel_id: Optional[str] = None
    if not force_regenerate:
        saved = await _saved_panel(profile_db, panel_name, collected_at)
        if saved is not None:
            if not await get_interpret_module()._saved_panel_is_stale(saved, observations, profile_db):
                return None, []
            stale_panel_id = saved.id
    stale_members = [
        obs.id for obs in observations
        if await saved_card_needs_rebuild(obs, profile_db, master_db)
    ]
    return stale_panel_id, stale_members
