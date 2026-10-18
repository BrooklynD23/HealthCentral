"""
Tests for the redaction pipeline (PRIV-RED-001).

Covers: SSN/email/phone/name/DOB redaction, policy levels,
no-mutation, metadata-no-plaintext, disabled bypass, external_runner integration.
"""

import random
import re
from unittest.mock import AsyncMock, patch

import pytest

from modules.redaction import (
    _RULES,
    VALID_POLICY_LEVELS,
    RedactionEngine,
    RedactionResult,
    RedactionRule,
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
    # rev 3: label + qualifier word, '#'/'.' separators, value punctuation
    ("mrn_number:_12345678", "12345678"),
    ("mrn_no.:_12345678", "12345678"),
    ("mrn_id:_a1234567", "a1234567"),
    ("patient_name_first:_jane", "jane"),
    ("mrn_#_12345", "12345"),
    ("mrn#:_12345", "12345"),
    ("medical_record_no.:_44-ab", "44-ab"),
    ("medical_record_#:_991234", "991234"),
    ("patient_id:_98765", "98765"),
    ("name:_mary_o'brien", "brien"),
    ("name:_doe,_jane", "jane"),
]

ANALYTE_LIKE = [
    "vitamin_d", "ldl_cholesterol", "hemoglobin_a1c", "25_hydroxy_vitamin_d",
    "t4_free", "glucose_fasting", "ms_afp", "mrna_level",
    "name_of_test", "patient_count_3", "hba1c_2025-05-01",
    "dobutamine_level", "medical_records_count",
]


class TestUnderscoreJoinedRedaction:
    @pytest.mark.parametrize("text,secret", UNDERSCORE_PHI)
    def test_hc_redact_001_underscore_labelled_shapes_redacted_strict(self, text, secret):
        """HC-REDACT-001: labelled underscore-joined name/DOB/MRN are redacted."""
        result = _engine("strict").redact(text)
        assert secret not in result.text
        assert "[ID-REDACTED]" in result.text
        # rev 3: the whole labelled value goes; only full_name keeps a prefix
        assert result.text.removeprefix("full_") == "[ID-REDACTED]"

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

    def test_hc_redact_008_long_underscore_run_is_linear_time(self):
        """HC-REDACT-008: a long '_' run after a label does not backtrack quadratically."""
        import time

        text = "dob" + "_" * 50000 + "!"
        start = time.perf_counter()
        result = _engine("strict").redact(text)
        assert time.perf_counter() - start < 1.0  # rev 2 rule: 7.9 s
        assert result.text == text

    @pytest.mark.parametrize(
        "text",
        [
            pytest.param("mrn" + "._" * 60000, id="mrn_dot_us"),
            pytest.param("a." * 60000, id="a_dot"),
            pytest.param("a." * 120000, id="a_dot_2x"),
        ],
    )
    def test_hc_redact_010_email_rule_linear_time_without_at(self, text):
        """HC-REDACT-010: a long local-part-class run with no '@' is not quadratic."""
        import time

        start = time.perf_counter()
        result = _engine("strict").redact(text)
        assert time.perf_counter() - start < 1.0
        assert result.text == text

    def test_hc_redact_011_email_anchor_output_identical_to_unanchored(self):
        """HC-REDACT-011: anchored email rule gives the same text, count and spans."""
        old_email = RedactionRule(
            "email",
            re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
            "[EMAIL-REDACTED]",
            frozenset({"strict", "standard"}),
        )
        new_email = next(r for r in _RULES if r.name == "email")
        corpus = [
            "jane@x.com", "a.b+c@sub.x.org", "jane_doe@example.com",
            ".jane@x.com", "-a@x.io", "mail: jane@x.com.", "\u00e9jane@x.com",
            "jane@@x.com", "a@b@c.com", "a@b.com.c@d.com", "x@y", "@x.com",
            "John.Doe@Example.COM", "J9@x.io", "Z|A9@x.io",
        ]
        rng = random.Random(20261018)
        alphabet = "a._-+%@\u00e9 ,;\n0AZ9|"
        corpus += [
            "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 40)))
            for _ in range(2000)
        ]
        for lvl in ("strict", "standard"):
            old_engine = RedactionEngine(policy_level=lvl, rules=[old_email])
            new_engine = RedactionEngine(policy_level=lvl, rules=[new_email])
            for text in corpus:
                old = old_engine.redact(text)
                new = new_engine.redact(text)
                assert new.text == old.text, (lvl, text)
                assert new.redacted_count == old.redacted_count, (lvl, text)
                assert [(m.rule_name, m.start, m.end) for m in new.metadata] == [
                    (m.rule_name, m.start, m.end) for m in old.metadata
                ], (lvl, text)

    def test_hc_redact_012_rule_anchor_defaults_to_none(self):
        """HC-REDACT-012: anchor is optional; rules without it keep the finditer path."""
        rule = RedactionRule("t", re.compile("x"), "[X]", frozenset({"strict"}))
        assert rule.anchor is None

    def test_hc_redact_012b_anchor_is_email_only_and_local_chars_match_pattern(self):
        """HC-REDACT-012b: only email is anchored; _LOCAL_CHARS equals the pattern's local-part class."""
        from modules import redaction as red

        assert [r.name for r in _RULES if r.anchor] == ["email"]
        email = next(r for r in _RULES if r.name == "email")
        cls = re.match(r"\\b\[([^\]]+)\]\+@", email.pattern.pattern).group(1)
        expected = {c for c in map(chr, range(128)) if re.fullmatch(f"[{cls}]", c)}
        assert set(red._LOCAL_CHARS) == expected


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
