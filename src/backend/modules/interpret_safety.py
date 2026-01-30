"""
Safety guardrails for lab interpretation.

Implements content filtering to ensure interpretations:
- Do not make diagnoses
- Do not recommend medications or dosages
- Always include appropriate disclaimers
- Flag critical values for physician review
- Include citations for all claims

Phase 1: Core Lab Interpretation Engine - Safety Component
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SafetyValidationResult:
    """Result of safety validation on an interpretation."""
    passed: bool
    checks_passed: list[str] = field(default_factory=list)
    checks_failed: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    requires_physician_review: bool = False
    physician_review_reason: Optional[str] = None
    filtered_text: Optional[str] = None  # Text after safety filtering


class InterpretationSafetyGuard:
    """
    Safety guardrails for lab result interpretations.

    Validates interpretation text to ensure it:
    - Does not diagnose conditions
    - Does not recommend medications or dosages
    - Uses hedged/uncertain language appropriately
    - Includes required disclaimers
    - Has citations for factual claims

    Also identifies critical values requiring immediate attention.
    """

    # Prohibited patterns - phrases that should never appear
    PROHIBITED_PATTERNS = [
        # Diagnostic language
        (r"\b(you have|you are diagnosed with|diagnosis of)\s+\w+", "diagnostic_language"),
        (r"\b(this (means|indicates|confirms) you have)\b", "diagnostic_language"),
        (r"\b(definitely|certainly|clearly) (have|indicates?|shows?)\b", "certainty_claims"),

        # Medication/dosing recommendations
        (r"\btake\s+\d+\s*(mg|mcg|g|ml|units?)\b", "dosing_recommendation"),
        (r"\b(prescribe|prescription|should take|must take|need to take)\b", "medication_advice"),
        (r"\b(medication dosage|dose adjustment|increase.*dose|decrease.*dose)\b", "dosing_recommendation"),
        (r"\b(start taking|stop taking|discontinue)\s+\w+", "medication_advice"),

        # Overly certain language
        (r"\b(always means|never means|100%|absolutely)\b", "certainty_claims"),
        (r"\b(guaranteed|definite(ly)?|certain(ly)?)\b", "certainty_claims"),

        # Emergency instructions (should direct to professionals)
        (r"\b(call 911|go to (the )?ER|emergency room|seek immediate)\b", "emergency_advice"),
        (r"\b(medical emergency|life.?threatening)\b", "emergency_advice"),
    ]

    # Required elements in interpretation
    REQUIRED_DISCLAIMER_KEYWORDS = [
        "consult",  # Must suggest consulting healthcare provider
        "healthcare provider|doctor|physician",  # Reference to medical professional
        "educational|informational|general information",  # Purpose disclaimer
    ]

    # Citation pattern - interpretations should cite knowledge base
    CITATION_PATTERN = re.compile(r"\[KB:[^\]]+\]|\[INT:[^\]]+\]|\[Source:[^\]]+\]")

    # Critical value thresholds (examples - should be loaded from knowledge base)
    DEFAULT_CRITICAL_THRESHOLDS = {
        "glucose": {"critical_low": 50, "critical_high": 400},
        "hemoglobin": {"critical_low": 7.0, "critical_high": 20.0},
        "potassium": {"critical_low": 2.5, "critical_high": 6.5},
        "sodium": {"critical_low": 120, "critical_high": 160},
        "platelets": {"critical_low": 50, "critical_high": 1000},
        "wbc": {"critical_low": 2.0, "critical_high": 30.0},
    }

    def __init__(self):
        """Initialize safety guard with compiled patterns."""
        self._compiled_prohibited = [
            (re.compile(pattern, re.IGNORECASE), name)
            for pattern, name in self.PROHIBITED_PATTERNS
        ]
        self._compiled_required = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.REQUIRED_DISCLAIMER_KEYWORDS
        ]

    def validate_interpretation(
        self,
        interpretation_text: str,
        advice_text: Optional[str] = None,
        require_citations: bool = True,
    ) -> SafetyValidationResult:
        """
        Validate an interpretation for safety compliance.

        Args:
            interpretation_text: The main interpretation text
            advice_text: Optional advice/recommendations text
            require_citations: Whether to require citations

        Returns:
            SafetyValidationResult with validation details
        """
        result = SafetyValidationResult(passed=True)
        full_text = interpretation_text
        if advice_text:
            full_text = f"{interpretation_text}\n{advice_text}"

        # Check for prohibited patterns
        for pattern, violation_type in self._compiled_prohibited:
            if pattern.search(full_text):
                result.passed = False
                result.checks_failed.append(f"prohibited_{violation_type}")
                logger.warning(
                    f"Safety violation: {violation_type} pattern found in interpretation"
                )

        if not any(f"prohibited_" in c for c in result.checks_failed):
            result.checks_passed.append("no_prohibited_content")

        # Check for required disclaimers
        disclaimers_found = 0
        for pattern in self._compiled_required:
            if pattern.search(full_text):
                disclaimers_found += 1

        if disclaimers_found >= 2:
            result.checks_passed.append("has_required_disclaimers")
        else:
            result.passed = False
            result.checks_failed.append("missing_disclaimers")
            logger.warning("Safety violation: Missing required disclaimers")

        # Check for citations if required
        if require_citations:
            citations = self.CITATION_PATTERN.findall(full_text)
            if citations:
                result.checks_passed.append("has_citations")
            else:
                # Warn but don't fail - citations can be added later
                result.warnings.append("no_citations_found")
                logger.debug("Warning: No citations found in interpretation")

        return result

    def check_critical_value(
        self,
        analyte_canonical: str,
        value: float,
        critical_low: Optional[float] = None,
        critical_high: Optional[float] = None,
    ) -> SafetyValidationResult:
        """
        Check if a value is critical and requires physician review.

        Args:
            analyte_canonical: The canonical analyte name
            value: The observed value
            critical_low: Override critical low threshold
            critical_high: Override critical high threshold

        Returns:
            SafetyValidationResult with critical value assessment
        """
        result = SafetyValidationResult(passed=True)

        # Get thresholds from defaults if not provided
        thresholds = self.DEFAULT_CRITICAL_THRESHOLDS.get(
            analyte_canonical.lower(), {}
        )
        c_low = critical_low if critical_low is not None else thresholds.get("critical_low")
        c_high = critical_high if critical_high is not None else thresholds.get("critical_high")

        if c_low is not None and value < c_low:
            result.requires_physician_review = True
            result.physician_review_reason = (
                f"Critical low value: {value} is below critical threshold of {c_low}"
            )
            result.warnings.append("critical_low_value")
            logger.warning(
                f"Critical value detected: {analyte_canonical}={value} < {c_low}"
            )

        if c_high is not None and value > c_high:
            result.requires_physician_review = True
            result.physician_review_reason = (
                f"Critical high value: {value} is above critical threshold of {c_high}"
            )
            result.warnings.append("critical_high_value")
            logger.warning(
                f"Critical value detected: {analyte_canonical}={value} > {c_high}"
            )

        if not result.requires_physician_review:
            result.checks_passed.append("value_not_critical")

        return result

    def filter_prohibited_content(self, text: str) -> str:
        """
        Remove or replace prohibited content from text.

        Args:
            text: Text to filter

        Returns:
            Filtered text with prohibited content removed/replaced
        """
        filtered = text

        for pattern, violation_type in self._compiled_prohibited:
            if violation_type == "emergency_advice":
                # Replace emergency instructions with safer guidance
                filtered = pattern.sub(
                    "contact your healthcare provider immediately",
                    filtered
                )
            elif violation_type == "dosing_recommendation":
                # Remove dosing recommendations
                filtered = pattern.sub("[dosing information removed]", filtered)
            elif violation_type == "medication_advice":
                # Soften medication language
                filtered = pattern.sub(
                    "discuss with your healthcare provider about",
                    filtered
                )
            else:
                # Generic removal for other prohibited content
                filtered = pattern.sub("[content removed for safety]", filtered)

        return filtered

    def add_required_disclaimers(
        self,
        interpretation_text: str,
        advice_text: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        Ensure required disclaimers are present.

        Args:
            interpretation_text: Main interpretation
            advice_text: Optional advice section

        Returns:
            Tuple of (interpretation_text, advice_text) with disclaimers added
        """
        disclaimer_present = False
        for pattern in self._compiled_required:
            if pattern.search(interpretation_text):
                disclaimer_present = True
                break

        if not disclaimer_present:
            # Add standard disclaimer to end of interpretation
            disclaimer = (
                "\n\nThis information is for educational purposes only. "
                "Please consult your healthcare provider for personalized medical advice."
            )
            interpretation_text = interpretation_text + disclaimer

        # Ensure advice has disclaimer if present
        if advice_text:
            advice_disclaimer_present = False
            for pattern in self._compiled_required:
                if pattern.search(advice_text):
                    advice_disclaimer_present = True
                    break

            if not advice_disclaimer_present:
                advice_disclaimer = (
                    "\n\nAlways consult your healthcare provider before making "
                    "any changes to your diet, exercise, or lifestyle."
                )
                advice_text = advice_text + advice_disclaimer

        return interpretation_text, advice_text or ""

    def generate_safety_disclaimer(self, severity_level: str) -> str:
        """
        Generate appropriate disclaimer based on severity.

        Args:
            severity_level: Interpretation severity (normal, borderline, abnormal, critical)

        Returns:
            Appropriate disclaimer text
        """
        base_disclaimer = (
            "This interpretation is for educational purposes only and does not "
            "constitute medical advice. "
        )

        if severity_level in ["critical_low", "critical_high"]:
            return (
                base_disclaimer +
                "This result may require immediate medical attention. "
                "Please contact your healthcare provider or seek medical care promptly."
            )
        elif severity_level in ["abnormal_low", "abnormal_high"]:
            return (
                base_disclaimer +
                "This result is outside the normal range. "
                "Please discuss these findings with your healthcare provider."
            )
        elif severity_level in ["borderline_low", "borderline_high"]:
            return (
                base_disclaimer +
                "This result is near the edge of the normal range. "
                "Your healthcare provider can help you understand what this means for you."
            )
        else:
            return (
                base_disclaimer +
                "Even normal results should be discussed with your healthcare provider "
                "in the context of your overall health."
            )


# Global instance
_safety_guard: Optional[InterpretationSafetyGuard] = None


def get_safety_guard() -> InterpretationSafetyGuard:
    """Get or create the global safety guard instance."""
    global _safety_guard
    if _safety_guard is None:
        _safety_guard = InterpretationSafetyGuard()
    return _safety_guard
