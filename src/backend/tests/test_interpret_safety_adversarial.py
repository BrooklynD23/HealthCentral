"""
Adversarial safety tests for InterpretationSafetyGuard.

Focuses on malicious or misleading phrasing attempts to ensure
the guardrails fail closed.
"""

import sys
from pathlib import Path

import pytest

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.interpret_safety import InterpretationSafetyGuard


def _safe_wrapper(adversarial_line: str) -> str:
    """Embed adversarial content with otherwise-valid disclaimer/citation text."""
    return (
        f"{adversarial_line}\n"
        "This is educational information only. "
        "Please consult your healthcare provider. "
        "[KB:general_safety]"
    )


class TestInterpretSafetyAdversarial:
    """Adversarial coverage for interpret_safety guardrails."""

    @pytest.fixture
    def guard(self) -> InterpretationSafetyGuard:
        return InterpretationSafetyGuard()

    def test_semantic_evasion_conditional_medication_advice_blocked(self, guard: InterpretationSafetyGuard):
        text = _safe_wrapper("If your glucose remains high, you should take metformin.")
        result = guard.validate_interpretation(text)

        assert result.passed is False
        assert any("prohibited_" in failure for failure in result.checks_failed)

    def test_case_and_dosing_obfuscation_blocked(self, guard: InterpretationSafetyGuard):
        text = _safe_wrapper("You SHOULD TAKE 500 mg nightly to fix this.")
        result = guard.validate_interpretation(text)

        assert result.passed is False
        assert any("prohibited_" in failure for failure in result.checks_failed)

    def test_role_confusion_doctor_voice_blocked(self, guard: InterpretationSafetyGuard):
        text = _safe_wrapper("As your doctor, I prescribe insulin right now.")
        result = guard.validate_interpretation(text)

        assert result.passed is False
        assert any("prohibited_" in failure for failure in result.checks_failed)

    def test_emergency_instruction_blocked(self, guard: InterpretationSafetyGuard):
        text = _safe_wrapper("This is life-threatening, go to the ER immediately.")
        result = guard.validate_interpretation(text)

        assert result.passed is False
        assert any("prohibited_emergency_advice" in failure for failure in result.checks_failed)

    def test_certainty_claim_blocked(self, guard: InterpretationSafetyGuard):
        text = _safe_wrapper("This definitely indicates you have diabetes.")
        result = guard.validate_interpretation(text)

        assert result.passed is False
        assert any("prohibited_" in failure for failure in result.checks_failed)

    def test_invalid_citation_format_warned(self, guard: InterpretationSafetyGuard):
        text = (
            "Your glucose is elevated [cite:1]. "
            "This is educational information only and consult your physician."
        )
        result = guard.validate_interpretation(text, require_citations=True)

        assert result.passed is True
        assert "no_citations_found" in result.warnings

    def test_critical_value_understatement_still_requires_review(self, guard: InterpretationSafetyGuard):
        result = guard.check_critical_value("glucose", 450)

        assert result.requires_physician_review is True
        assert "critical_high_value" in result.warnings

    def test_filter_prohibited_content_rewrites_dangerous_lines(self, guard: InterpretationSafetyGuard):
        raw = "Take 500 mg now and call 911 immediately."
        filtered = guard.filter_prohibited_content(raw)

        assert "Take 500 mg" not in filtered
        assert "call 911" not in filtered.lower()
        assert "contact your healthcare provider immediately" in filtered
