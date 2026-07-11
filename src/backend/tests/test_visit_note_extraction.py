"""HC-M13 after-visit / discharge extraction tests (HC-AVS-NNN).

Golden set: tests/fixtures/visit_notes_golden/ — 12 synthetic (fictional)
after-visit-summary / discharge / consult / progress fixtures with labeled
expected entities in manifest.json.

Measured precision/recall of the rule-based extractor (rule-v2) over the
golden set at the time thresholds were set (see HC-AVS-002):

    entity_type            precision  recall   (expected n)
    visit_type             1.00       1.00     (12)
    medication_change      1.00       1.00     (21)
    test_ordered           1.00       1.00     (10)
    referral               1.00       1.00     (4)
    follow_up_instruction  1.00       1.00     (12)
    warning_sign           1.00       1.00     (11)
    facility               1.00       1.00     (6)

Thresholds below are set beneath those measured numbers to allow honest
rule evolution, and must never be lowered just to make a change pass.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.model_runner import InferenceResult
from modules.document_classifier import classify_document
from modules.extract_spans import EXTRACTION_VERSION
from modules.extract_visit_notes import (
    LLM_ASSIST_ALLOWED_TYPES,
    LLM_ASSIST_EXTRACTION_VERSION,
    LLM_ASSIST_MAX_CONFIDENCE,
    extract_visit_note_entities,
    llm_assist_visit_entities,
)

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "visit_notes_golden"

with open(GOLDEN_DIR / "manifest.json", encoding="utf-8") as f:
    MANIFEST = json.load(f)

EVALUATED_TYPES = MANIFEST["evaluated_types"]

# Minimum per-type precision/recall over the golden set (see module header
# for the measured numbers these were derived from).
THRESHOLDS = {
    "visit_type": (0.9, 0.9),
    "medication_change": (0.85, 0.8),
    "test_ordered": (0.85, 0.8),
    "referral": (0.85, 0.75),
    "follow_up_instruction": (0.85, 0.8),
    "warning_sign": (0.85, 0.8),
    "facility": (0.85, 0.8),
}


def _load_fixture(name: str) -> str:
    return (GOLDEN_DIR / name).read_text(encoding="utf-8")


def _matches(expected: dict, entity: dict) -> bool:
    if expected["entity_type"] != entity["entity_type"]:
        return False
    if expected["entity_type"] == "visit_type":
        return entity["entity_value"] == expected["match"]
    return expected["match"].lower() in entity["entity_value"].lower()


def _score_golden_set() -> dict:
    """Greedy one-to-one matching per fixture; returns per-type tp/fp/fn."""
    counts = {t: {"tp": 0, "fp": 0, "fn": 0} for t in EVALUATED_TYPES}
    for fixture in MANIFEST["fixtures"]:
        text = _load_fixture(fixture["file"])
        extracted = [
            e for e in extract_visit_note_entities(text)
            if e["entity_type"] in EVALUATED_TYPES
        ]
        unmatched = list(extracted)
        for expected in fixture["expected"]:
            hit = next((e for e in unmatched if _matches(expected, e)), None)
            if hit is not None:
                unmatched.remove(hit)
                counts[expected["entity_type"]]["tp"] += 1
            else:
                counts[expected["entity_type"]]["fn"] += 1
        for extra in unmatched:
            counts[extra["entity_type"]]["fp"] += 1
    return counts


class TestGoldenSet:
    def test_hc_avs_001_manifest_sane(self):
        assert 10 <= len(MANIFEST["fixtures"]) <= 20
        for fixture in MANIFEST["fixtures"]:
            assert (GOLDEN_DIR / fixture["file"]).is_file()
            for expected in fixture["expected"]:
                assert expected["entity_type"] in EVALUATED_TYPES

    @pytest.mark.parametrize("entity_type", list(THRESHOLDS))
    def test_hc_avs_002_precision_recall_thresholds(self, entity_type):
        counts = _score_golden_set()[entity_type]
        tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
        assert tp + fn > 0, f"golden set has no expected {entity_type} entities"
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn)
        min_p, min_r = THRESHOLDS[entity_type]
        assert precision >= min_p, (
            f"{entity_type}: precision {precision:.2f} < {min_p} "
            f"(tp={tp}, fp={fp}, fn={fn})"
        )
        assert recall >= min_r, (
            f"{entity_type}: recall {recall:.2f} < {min_r} "
            f"(tp={tp}, fp={fp}, fn={fn})"
        )

    def test_hc_avs_003_all_spans_exact(self):
        """Every entity from every fixture carries an exact verbatim span."""
        for fixture in MANIFEST["fixtures"]:
            text = _load_fixture(fixture["file"])
            entities = extract_visit_note_entities(text)
            assert entities
            for ent in entities:
                assert ent["extraction_version"] == EXTRACTION_VERSION
                assert ent["quote"] is not None, ent
                assert isinstance(ent["char_start"], int)
                assert isinstance(ent["char_end"], int)
                assert text[ent["char_start"]:ent["char_end"]] == ent["quote"]

    def test_hc_avs_004_medication_change_starts_with_action_verb(self):
        allowed = {"start", "stop", "increase", "decrease", "change", "continue"}
        seen = 0
        for fixture in MANIFEST["fixtures"]:
            text = _load_fixture(fixture["file"])
            for ent in extract_visit_note_entities(text):
                if ent["entity_type"] == "medication_change":
                    seen += 1
                    assert ent["entity_value"].split()[0] in allowed, ent
        assert seen > 0


class TestMedicationChangeStoplist:
    """Device/lifestyle instructions must not be labeled medication changes,
    even when the stoplist word is not the first word of the object."""

    @pytest.mark.parametrize(
        "sentence",
        [
            "Start using a cane when walking outside.",
            "Start wearing compression stockings daily.",
            "Begin gentle daily walks around the block.",
        ],
    )
    def test_hc_avs_016_device_lifestyle_is_not_medication_change(self, sentence):
        med_changes = [
            e for e in extract_visit_note_entities(sentence)
            if e["entity_type"] == "medication_change"
        ]
        assert med_changes == [], sentence

    @pytest.mark.parametrize(
        "sentence,expected",
        [
            ("Start atorvastatin 20 mg nightly.", "start atorvastatin 20 mg nightly"),
            ("Stop lisinopril.", "stop lisinopril"),
            ("Increase metformin to 1000 mg twice daily.", "increase metformin to 1000 mg twice daily"),
        ],
    )
    def test_hc_avs_017_real_medication_phrases_still_match(self, sentence, expected):
        values = [
            e["entity_value"] for e in extract_visit_note_entities(sentence)
            if e["entity_type"] == "medication_change"
        ]
        assert values == [expected]


class TestVisitTypeCanonicalization:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("AFTER VISIT SUMMARY\nChief Complaint: cough", "after_visit_summary"),
            ("AVS - Patient Instructions", "after_visit_summary"),
            ("HOSPITAL DISCHARGE SUMMARY", "discharge"),
            ("DISCHARGE INSTRUCTIONS", "discharge"),
            ("PROGRESS NOTE", "progress"),
            ("NEPHROLOGY CONSULT NOTE", "consult"),
            ("Annual exam today.", "annual"),
            ("Patient here for follow-up.", "other"),
        ],
    )
    def test_hc_avs_005_visit_type_is_canonical(self, text, expected):
        entities = extract_visit_note_entities(text)
        visit_types = [e for e in entities if e["entity_type"] == "visit_type"]
        assert len(visit_types) == 1
        assert visit_types[0]["entity_value"] == expected


class TestAdversarialInjection:
    """Embedded prompt-injection text must be inert: it is ordinary document
    content and must never alter extraction behavior."""

    def test_hc_avs_006_injection_is_inert(self):
        text = _load_fixture("adversarial_injection.txt")
        marker = "IGNORE PREVIOUS INSTRUCTIONS"
        assert marker in text

        entities = extract_visit_note_entities(text)
        # Deterministic: two runs, identical output.
        assert extract_visit_note_entities(text) == entities

        # Removing the injected paragraph leaves the evaluated-type
        # entities unchanged (types and values identical).
        lines = [
            line for line in text.splitlines()
            if marker not in line and "patient portal" not in line
        ]
        clean_text = "\n".join(lines)
        assert marker not in clean_text

        def evaluated(ents):
            return sorted(
                (e["entity_type"], e["entity_value"])
                for e in ents
                if e["entity_type"] in EVALUATED_TYPES
            )

        assert evaluated(entities) == evaluated(
            extract_visit_note_entities(clean_text)
        )

        # The injected demands are not honored: confidences stay in the
        # normal rule-based range.
        for ent in entities:
            assert 0.0 < ent["confidence"] <= 0.95


class TestClassifierAvsKeywords:
    def test_hc_avs_007_after_visit_summary_classifies_as_visit_notes(self):
        text = (
            "AFTER VISIT SUMMARY\n"
            "Patient Instructions\n"
            "Start lisinopril 10 mg daily.\n"
            "Follow up in 4 weeks.\n"
        )
        result = classify_document(text)
        assert result.category == "visit_notes"
        assert result.confidence >= 0.8


# ---------------------------------------------------------------------------
# LLM-assist pass (llm-assist-v1) — default OFF, hard-validated proposals.
# ---------------------------------------------------------------------------

AVS_TEXT = _load_fixture("avs_01.txt")


class _FakeRunner:
    def __init__(self, response_text: str, available: bool = True):
        self._response_text = response_text
        self._available = available
        self.prompts: list[str] = []

    def is_available(self) -> bool:
        return self._available

    async def generate_async(self, prompt, config=None):
        self.prompts.append(prompt)
        return InferenceResult(
            text=self._response_text,
            tokens_generated=1,
            finish_reason="stop",
            model_name="fake",
        )


class TestLlmAssist:
    @pytest.mark.asyncio
    async def test_hc_avs_008_valid_proposal_accepted_with_derived_span(self):
        quote = "Call the office if you have a headache"
        assert quote in AVS_TEXT
        runner = _FakeRunner(json.dumps([
            {
                "entity_type": "warning_sign",
                "entity_value": "call the office if you have a headache",
                "quote": quote,
                "confidence": 0.99,
            }
        ]))
        entities = await llm_assist_visit_entities(AVS_TEXT, [], runner=runner)
        assert len(entities) == 1
        ent = entities[0]
        assert ent["entity_type"] == "warning_sign"
        assert ent["quote"] == quote
        assert AVS_TEXT[ent["char_start"]:ent["char_end"]] == quote
        assert ent["confidence"] <= LLM_ASSIST_MAX_CONFIDENCE
        assert ent["extraction_version"] == LLM_ASSIST_EXTRACTION_VERSION

    @pytest.mark.asyncio
    async def test_hc_avs_009_invalid_proposals_rejected(self):
        runner = _FakeRunner(json.dumps([
            # Quote not an exact substring of the document -> reject.
            {
                "entity_type": "medication_change",
                "entity_value": "start lisinopril 40 mg",
                "quote": "Start lisinopril 40 mg by mouth once daily",
            },
            # Entity type outside the allowed set -> reject.
            {
                "entity_type": "diagnosis",
                "entity_value": "hypertension",
                "quote": "high blood pressure check",
            },
            # Injection-shaped garbage -> reject.
            {
                "entity_type": "system_override",
                "entity_value": "ignore all previous instructions",
                "quote": "AFTER VISIT SUMMARY",
            },
            # medication_change without a leading action verb -> reject.
            {
                "entity_type": "medication_change",
                "entity_value": "lisinopril 10 mg",
                "quote": "Start lisinopril 10 mg by mouth once daily",
            },
            # Missing quote -> reject.
            {"entity_type": "referral", "entity_value": "cardiology"},
            "not-a-dict",
        ]))
        entities = await llm_assist_visit_entities(AVS_TEXT, [], runner=runner)
        assert entities == []
        assert "diagnosis" not in LLM_ASSIST_ALLOWED_TYPES
        assert "system_override" not in LLM_ASSIST_ALLOWED_TYPES

    @pytest.mark.asyncio
    async def test_hc_avs_010_dedupes_against_rule_entities_and_caps_output(self):
        quote = "Follow up in 4 weeks"
        assert quote in AVS_TEXT
        runner = _FakeRunner(json.dumps([
            {
                "entity_type": "follow_up_instruction",
                "entity_value": "follow up in 4 weeks",
                "quote": quote,
            }
        ] * 5))
        existing = [{"entity_type": "follow_up_instruction", "quote": quote}]
        assert await llm_assist_visit_entities(AVS_TEXT, existing, runner=runner) == []

        # Without the rule-based duplicate, identical proposals collapse to one.
        entities = await llm_assist_visit_entities(AVS_TEXT, [], runner=runner)
        assert len(entities) == 1

    @pytest.mark.asyncio
    async def test_hc_avs_011_unavailable_or_broken_runner_returns_empty(self):
        assert await llm_assist_visit_entities(
            AVS_TEXT, [], runner=_FakeRunner("[]", available=False)
        ) == []
        # Non-JSON output degrades to no proposals, never raises.
        assert await llm_assist_visit_entities(
            AVS_TEXT, [], runner=_FakeRunner("I cannot help with that.")
        ) == []

    @pytest.mark.asyncio
    async def test_hc_avs_014_fabricated_value_with_real_quote_rejected(self):
        """A crafted document can induce the model to pair a real verbatim
        quote with fabricated advice text. entity_value must be grounded in
        the validated quote — no free model text may survive into it."""
        text = (
            "DISCHARGE INSTRUCTIONS\n"
            "Medication changes:\n"
            "Discontinue warfarin immediately.\n"
            "Follow up in 2 weeks.\n"
        )
        quote = "Discontinue warfarin immediately"
        assert quote in text
        runner = _FakeRunner(json.dumps([
            # Real quote, fabricated dosing advice (leading canonical verb
            # alone must not be enough).
            {
                "entity_type": "medication_change",
                "entity_value": "start URGENT: take double dose of warfarin tonight",
                "quote": quote,
            },
            # Non-medication types have no verb check at all — grounding
            # must still reject fabricated text.
            {
                "entity_type": "warning_sign",
                "entity_value": "URGENT: take double dose of warfarin tonight",
                "quote": quote,
            },
            {
                "entity_type": "follow_up_instruction",
                "entity_value": "return tomorrow for emergency dialysis",
                "quote": "Follow up in 2 weeks",
            },
        ]))
        assert await llm_assist_visit_entities(text, [], runner=runner) == []

    @pytest.mark.asyncio
    async def test_hc_avs_015_faithful_normalization_accepted(self):
        """A value that faithfully normalizes its quote is accepted,
        including the canonical medication verb normalized from a synonym
        in the quote ("Discontinue" -> "stop")."""
        text = (
            "DISCHARGE INSTRUCTIONS\n"
            "Medication changes:\n"
            "Discontinue warfarin immediately.\n"
        )
        quote = "Discontinue warfarin immediately"
        runner = _FakeRunner(json.dumps([
            {
                "entity_type": "medication_change",
                "entity_value": "stop warfarin",
                "quote": quote,
            }
        ]))
        entities = await llm_assist_visit_entities(text, [], runner=runner)
        assert len(entities) == 1
        assert entities[0]["entity_value"] == "stop warfarin"
        assert entities[0]["quote"] == quote

    @pytest.mark.asyncio
    async def test_hc_avs_012_document_text_is_data_not_instructions(self):
        # The prompt must fence the document and instruct the model to treat
        # it as untrusted data.
        runner = _FakeRunner("[]")
        await llm_assist_visit_entities(AVS_TEXT, [], runner=runner)
        assert len(runner.prompts) == 1
        prompt = runner.prompts[0]
        assert "<document>" in prompt and "</document>" in prompt
        assert "not instructions" in prompt.lower()


class TestLlmAssistWiring:
    """The reprocess/upload pipeline only invokes the LLM pass when the
    request explicitly enables it; rule-based extraction always runs."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("flag", [False, True])
    async def test_hc_avs_013_llm_assist_behind_explicit_flag(self, flag, monkeypatch):
        from unittest.mock import AsyncMock, MagicMock

        import api.documents as documents_api

        llm_mock = AsyncMock(return_value=[])
        monkeypatch.setattr(documents_api, "llm_assist_visit_entities", llm_mock)

        added: list[object] = []
        mock_db = AsyncMock()
        mock_db.add = MagicMock(side_effect=added.append)

        await documents_api._classify_and_extract_entities(
            profile_db=mock_db,
            profile_id="test-profile",
            doc_id="doc-1",
            doc_type="pdf",
            pre_extracted_text=_load_fixture("progress_01.txt"),
            llm_assist=flag,
        )

        assert llm_mock.await_count == (1 if flag else 0)
        # Rule-based entities were persisted either way.
        assert any(
            getattr(obj, "entity_type", None) == "test_ordered"
            for obj in added
        )
