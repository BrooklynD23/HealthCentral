"""
Tests for the redaction pipeline (PRIV-RED-001).

Covers: SSN/email/phone/name/DOB redaction, policy levels,
no-mutation, metadata-no-plaintext, disabled bypass, external_runner integration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from modules.redaction import (
    RedactionEngine,
    RedactionResult,
    RedactionRule,
    VALID_POLICY_LEVELS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _engine(level: str = "standard") -> RedactionEngine:
    return RedactionEngine(policy_level=level)


# ---------------------------------------------------------------------------
# SSN redaction
# ---------------------------------------------------------------------------

class TestSSNRedaction:
    def test_ssn_redacted_at_all_levels(self):
        text = "SSN: 123-45-6789"
        for level in VALID_POLICY_LEVELS:
            result = RedactionEngine(policy_level=level).redact(text)
            assert "123-45-6789" not in result.text
            assert "[SSN-REDACTED]" in result.text

    def test_ssn_multiple_occurrences(self):
        text = "A: 111-22-3333, B: 444-55-6666"
        result = _engine().redact(text)
        assert result.redacted_count >= 2
        assert "111-22-3333" not in result.text
        assert "444-55-6666" not in result.text


# ---------------------------------------------------------------------------
# Email redaction
# ---------------------------------------------------------------------------

class TestEmailRedaction:
    def test_email_redacted_standard(self):
        text = "Contact: jane.doe@example.com"
        result = _engine("standard").redact(text)
        assert "jane.doe@example.com" not in result.text
        assert "[EMAIL-REDACTED]" in result.text

    def test_email_not_redacted_minimal(self):
        text = "Contact: jane.doe@example.com"
        result = _engine("minimal").redact(text)
        assert "jane.doe@example.com" in result.text


# ---------------------------------------------------------------------------
# Phone redaction
# ---------------------------------------------------------------------------

class TestPhoneRedaction:
    def test_phone_redacted_standard(self):
        text = "Call 555-123-4567 for info"
        result = _engine("standard").redact(text)
        assert "555-123-4567" not in result.text
        assert "[PHONE-REDACTED]" in result.text

    def test_phone_with_parens(self):
        text = "Phone: (555) 123-4567"
        result = _engine("standard").redact(text)
        assert "123-4567" not in result.text

    def test_phone_not_redacted_minimal(self):
        text = "Call 555-123-4567"
        result = _engine("minimal").redact(text)
        assert "555-123-4567" in result.text


# ---------------------------------------------------------------------------
# Name redaction (context-aware)
# ---------------------------------------------------------------------------

class TestNameRedaction:
    def test_name_with_patient_prefix(self):
        text = "Patient: John Smith"
        result = _engine("standard").redact(text)
        assert "[NAME-REDACTED]" in result.text

    def test_name_with_mr_prefix(self):
        text = "Mr. James Wilson"
        result = _engine("standard").redact(text)
        assert "[NAME-REDACTED]" in result.text

    def test_no_false_positive_on_analyte(self):
        text = "Hemoglobin: 14.2 g/dL"
        result = _engine("standard").redact(text)
        assert "Hemoglobin" in result.text


# ---------------------------------------------------------------------------
# DOB redaction
# ---------------------------------------------------------------------------

class TestDOBRedaction:
    def test_dob_redacted_strict(self):
        text = "DOB: 01/15/1990"
        result = _engine("strict").redact(text)
        assert "01/15/1990" not in result.text
        assert "[DOB-REDACTED]" in result.text

    def test_dob_not_redacted_standard(self):
        text = "DOB: 01/15/1990"
        result = _engine("standard").redact(text)
        assert "01/15/1990" in result.text


# ---------------------------------------------------------------------------
# Address redaction
# ---------------------------------------------------------------------------

class TestAddressRedaction:
    def test_address_redacted_strict(self):
        text = "Address: 123 Main St."
        result = _engine("strict").redact(text)
        assert "[ADDRESS-REDACTED]" in result.text

    def test_address_not_redacted_standard(self):
        text = "Address: 123 Main St."
        result = _engine("standard").redact(text)
        assert "123 Main St." in result.text


# ---------------------------------------------------------------------------
# MRN redaction (RL-REDACT-001, strict only)
# ---------------------------------------------------------------------------

class TestMRNRedaction:
    def test_mrn_redacted_strict(self):
        text = "MRN: 8834412 admitted for panel"
        result = _engine("strict").redact(text)
        assert "8834412" not in result.text
        assert "[MRN-REDACTED]" in result.text

    def test_medical_record_number_redacted_strict(self):
        text = "Medical record number 44-AB-9921 on file"
        result = _engine("strict").redact(text)
        assert "44-AB-9921" not in result.text

    def test_mrn_not_redacted_standard(self):
        text = "MRN: 8834412 admitted for panel"
        result = _engine("standard").redact(text)
        assert "8834412" in result.text


# ---------------------------------------------------------------------------
# Numeric date redaction (RL-REDACT-001, strict only)
# ---------------------------------------------------------------------------

class TestNumericDateRedaction:
    def test_slash_date_redacted_strict(self):
        text = "Admitted 03/15/1985 per chart"
        result = _engine("strict").redact(text)
        assert "03/15/1985" not in result.text
        assert "[DATE-REDACTED]" in result.text

    def test_iso_collection_date_preserved_strict(self):
        # ISO-8601 collection timestamps are the longitudinal clinical signal
        # RL exports carry — deliberately NOT matched by the numeric_date rule.
        text = "Glucose 95 mg/dL collected 2025-05-01"
        result = _engine("strict").redact(text)
        assert "2025-05-01" in result.text

    def test_slash_date_not_redacted_standard(self):
        text = "Admitted 03/15/1985 per chart"
        result = _engine("standard").redact(text)
        assert "03/15/1985" in result.text


# ---------------------------------------------------------------------------
# Underscore-joined identifiers (E-1a / W-2 O-3, strict only)
# ---------------------------------------------------------------------------

UNDERSCORE_PHI = [
    ("patient_name:_jane_doe", "jane"),
    ("dob:_01/02/1980", "01/02/1980"),
    ("mrn:_a12345", "a12345"),
    ("patient_name_jane_doe", "jane"),
    ("date_of_birth:_1/2/80", "1/2/80"),
    ("medical_record_number:_44-ab-9921", "44-ab-9921"),
    ("full_name:_jane_doe", "jane"),
    ("PATIENT_NAME:_JANE_DOE", "JANE"),
    ("patient_name:_josé_álvarez", "álvarez"),
    ("patient:_jane_doe", "jane"),
    ("birth_date:_01/02/1980", "01/02/1980"),
    ("medical_record_no:_a12345", "a12345"),
]

ANALYTE_LIKE = [
    "vitamin_d", "ldl_cholesterol", "hemoglobin_a1c", "25_hydroxy_vitamin_d",
    "t4_free", "glucose_fasting", "ms_afp", "mrna_level",
    "name_of_test", "patient_count_3", "hba1c_2025-05-01",
]


class TestUnderscoreJoinedRedaction:
    @pytest.mark.parametrize("text,secret", UNDERSCORE_PHI)
    def test_hc_redact_001_underscore_labelled_shapes_redacted_strict(self, text, secret):
        """HC-REDACT-001: labelled underscore-joined name/DOB/MRN are redacted."""
        result = _engine("strict").redact(text)
        assert secret not in result.text
        assert "[ID-REDACTED]" in result.text

    def test_hc_redact_002_underscore_numeric_date_redacted_strict(self):
        """HC-REDACT-002: an unlabelled d/m/y date after '_' is redacted."""
        result = _engine("strict").redact("admitted_03/15/1985")
        assert "03/15/1985" not in result.text
        assert "[DATE-REDACTED]" in result.text

    def test_hc_redact_003_rendered_summary_line_keeps_value_and_markup(self):
        """HC-REDACT-003: only the identifier goes; value, ISO date and tags stay."""
        line = "• patient_name:_jane_doe: 1.0  (ref: 0.0-0.5) [H] - 2024-03-15"
        assert _engine("strict").redact(line).text == (
            "• [ID-REDACTED]: 1.0  (ref: 0.0-0.5) [H] - 2024-03-15"
        )
        html = "<td>mrn:_a12345</td>"
        assert _engine("strict").redact(html).text == "<td>[ID-REDACTED]</td>"

    @pytest.mark.parametrize("name", ANALYTE_LIKE)
    def test_hc_redact_004_analyte_like_tokens_not_redacted_strict(self, name):
        """HC-REDACT-004: no over-redaction of analyte-shaped tokens."""
        result = _engine("strict").redact(name)
        assert result.text == name
        assert result.redacted_count == 0

    def test_hc_redact_005_all_known_analyte_names_unchanged_strict(self):
        """HC-REDACT-005: every known canonical name and synonym, underscore form."""
        from modules.normalize import NormalizeModule

        names = set()
        for canonical, synonyms in NormalizeModule.ANALYTE_SYNONYMS.items():
            names.add(canonical)
            names.update(synonyms)
        assert len(names) >= 100  # the list loaded; an empty loop proves nothing
        hits = [n for n in sorted(names)
                if _engine("strict").redact(n.replace(" ", "_")).redacted_count]
        assert hits == []

    def test_hc_redact_006_underscore_rules_strict_only(self):
        """HC-REDACT-006: standard and minimal are unchanged."""
        text = "patient_name:_jane_doe mrn:_a12345 admitted_03/15/1985"
        for level in ("standard", "minimal"):
            assert _engine(level).redact(text).text == text

    def test_hc_redact_007_underscore_email_still_fully_redacted(self):
        """HC-REDACT-007: underscore in an email local part is not split."""
        result = _engine("strict").redact("contact jane_doe@example.com")
        assert "jane" not in result.text
        assert "[EMAIL-REDACTED]" in result.text


# ---------------------------------------------------------------------------
# Policy levels
# ---------------------------------------------------------------------------

class TestPolicyLevels:
    def test_strict_catches_all(self):
        text = (
            "Patient: John Doe SSN 123-45-6789 DOB: 03/15/1985 "
            "Email: john@example.com Phone: 555-123-4567 "
            "Address: 456 Oak Ave."
        )
        result = _engine("strict").redact(text)
        assert result.redacted_count >= 5

    def test_standard_skips_dob_address(self):
        text = "DOB: 03/15/1985 Address: 456 Oak Ave."
        result = _engine("standard").redact(text)
        assert "03/15/1985" in result.text

    def test_minimal_only_ssn(self):
        text = "SSN 123-45-6789 Email: a@b.com Phone: 555-123-4567"
        result = _engine("minimal").redact(text)
        assert "123-45-6789" not in result.text
        assert "a@b.com" in result.text
        assert "555-123-4567" in result.text

    def test_invalid_policy_raises(self):
        with pytest.raises(ValueError, match="Invalid policy_level"):
            RedactionEngine(policy_level="nonexistent")


# ---------------------------------------------------------------------------
# Immutability & metadata safety
# ---------------------------------------------------------------------------

class TestImmutability:
    def test_input_not_mutated(self):
        original = "SSN: 123-45-6789"
        original_copy = original  # strings are immutable, but verify result is new
        result = _engine().redact(original)
        assert original == original_copy
        assert result.text != original

    def test_result_is_frozen(self):
        result = _engine().redact("SSN: 123-45-6789")
        assert isinstance(result, RedactionResult)
        with pytest.raises(AttributeError):
            result.text = "modified"  # type: ignore[misc]


class TestMetadataSafety:
    def test_metadata_has_no_plaintext(self):
        text = "SSN: 123-45-6789 Email: test@example.com"
        result = _engine("standard").redact(text)
        for entry in result.metadata:
            # Metadata should only contain rule_name, positions, replacement length
            assert hasattr(entry, "rule_name")
            assert hasattr(entry, "start")
            assert hasattr(entry, "end")
            # No attribute should hold the original matched text
            assert not hasattr(entry, "original_text")
            assert not hasattr(entry, "matched_text")


# ---------------------------------------------------------------------------
# Disabled bypass
# ---------------------------------------------------------------------------

class TestDisabledBypass:
    def test_empty_text_returns_empty(self):
        result = _engine().redact("")
        assert result.text == ""
        assert result.redacted_count == 0

    def test_no_pii_returns_unchanged(self):
        text = "Hemoglobin 14.2 g/dL within normal range."
        result = _engine().redact(text)
        assert result.text == text
        assert result.redacted_count == 0


# ---------------------------------------------------------------------------
# Integration: external_runner redaction call
# ---------------------------------------------------------------------------

class TestExternalRunnerIntegration:
    """Verify that generate_async in ExternalModelRunner calls redaction when enabled."""

    @pytest.mark.asyncio
    async def test_redaction_applied_before_provider_dispatch(self):
        """When redaction is enabled, the prompt sent to the provider should be redacted."""
        from core.external_runner import ExternalModelRunner
        from core.model_runner import InferenceResult

        runner = ExternalModelRunner(
            provider="openai",
            api_key="test-key",
            model="gpt-4o-mini",
        )

        original_prompt = "Patient: John Doe SSN 123-45-6789"

        # Mock the actual API call to capture the prompt
        captured_prompts: list[str] = []

        async def mock_call_openai(prompt, config):
            captured_prompts.append(prompt)
            return InferenceResult(
                text="Response",
                tokens_generated=1,
                finish_reason="stop",
                model_name="gpt-4o-mini",
            )

        with patch.object(runner, "_call_openai", side_effect=mock_call_openai):
            with patch("core.external_runner.settings") as mock_settings:
                mock_settings.redaction_enabled = True
                mock_settings.redaction_policy_level = "standard"
                await runner.generate_async(original_prompt)

        assert len(captured_prompts) == 1
        assert "123-45-6789" not in captured_prompts[0]
        assert "[SSN-REDACTED]" in captured_prompts[0]

    @pytest.mark.asyncio
    async def test_production_blocks_when_redaction_disabled_without_break_glass(self):
        """F-002: External calls must not proceed unredacted in production by default."""
        from core.external_runner import ExternalModelRunner
        from core.model_runner import InferenceResult

        runner = ExternalModelRunner(provider="openai", api_key="test-key")

        async def mock_call_openai(prompt, config):
            return InferenceResult(
                text="Response",
                tokens_generated=1,
                finish_reason="stop",
                model_name="gpt-4o-mini",
            )

        with patch.object(runner, "_call_openai", side_effect=mock_call_openai) as mock_call:
            with patch("core.external_runner.settings") as mock_settings:
                mock_settings.app_env = "production"
                mock_settings.external_api_redaction_break_glass = False
                mock_settings.redaction_enabled = False
                mock_settings.redaction_policy_level = "strict"
                result = await runner.generate_async("SSN: 123-45-6789")

        mock_call.assert_not_called()
        assert result.finish_reason == "error"
        assert "redaction is required" in result.text.lower()

    @pytest.mark.asyncio
    async def test_production_blocks_when_policy_not_strict_without_break_glass(self):
        """F-001: Production external calls must use strict redaction by default."""
        from core.external_runner import ExternalModelRunner
        from core.model_runner import InferenceResult

        runner = ExternalModelRunner(provider="openai", api_key="test-key")

        async def mock_call_openai(prompt, config):
            return InferenceResult(
                text="Response",
                tokens_generated=1,
                finish_reason="stop",
                model_name="gpt-4o-mini",
            )

        with patch.object(runner, "_call_openai", side_effect=mock_call_openai) as mock_call:
            with patch("core.external_runner.settings") as mock_settings:
                mock_settings.app_env = "production"
                mock_settings.external_api_redaction_break_glass = False
                mock_settings.redaction_enabled = True
                mock_settings.redaction_policy_level = "standard"
                result = await runner.generate_async("SSN: 123-45-6789")

        mock_call.assert_not_called()
        assert result.finish_reason == "error"
        assert "strict redaction" in result.text.lower()

    @pytest.mark.asyncio
    async def test_break_glass_allows_unredacted_call_with_audit_warning(self, caplog):
        """F-002: Break-glass must be explicit and logged."""
        import logging

        from core.external_runner import ExternalModelRunner
        from core.model_runner import InferenceResult

        runner = ExternalModelRunner(provider="openai", api_key="test-key")
        original_prompt = "Patient: John Doe SSN 123-45-6789"
        captured_prompts: list[str] = []

        async def mock_call_openai(prompt, config):
            captured_prompts.append(prompt)
            return InferenceResult(
                text="Response",
                tokens_generated=1,
                finish_reason="stop",
                model_name="gpt-4o-mini",
            )

        caplog.set_level(logging.WARNING)
        with patch.object(runner, "_call_openai", side_effect=mock_call_openai), \
             patch("core.external_runner._record_break_glass_audit", new=AsyncMock()) as audit_sink:
            with patch("core.external_runner.settings") as mock_settings:
                mock_settings.app_env = "production"
                mock_settings.external_api_redaction_break_glass = True
                mock_settings.redaction_enabled = False
                mock_settings.redaction_policy_level = "standard"
                await runner.generate_async(original_prompt)

        assert captured_prompts == [original_prompt]
        assert any("SECURITY_AUDIT:" in r.message for r in caplog.records)
        audit_sink.assert_awaited_once()  # D12: break-glass only with audit
