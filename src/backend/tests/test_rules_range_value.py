"""HC-RRV: range-clause bounds must not verify a wrong measured value (RULES-RANGE-VALUE)."""
from modules.verifier_agent import (
    EntailmentLabel,
    SourceEvidence,
    VerificationConfig,
    VerifierAgent,
)

CLAIM = "Potassium 9.0 mmol is above the reference range 3.5-5.0 mmol"


def _agent() -> VerifierAgent:
    return VerifierAgent(VerificationConfig(use_llm_entailment=False))


def _src(text: str) -> SourceEvidence:
    return SourceEvidence(source_id="s1", source_text=text, source_type="lab")


def test_hc_rrv_001_range_echo_does_not_entail():
    r = _agent()._check_entailment_rules(CLAIM, _src("Potassium 3.8 mmol, reference range 3.5-5.0 mmol"))
    assert r.label is not EntailmentLabel.ENTAILMENT


def test_hc_rrv_002_measured_value_match_still_entails():
    r = _agent()._check_entailment_rules(CLAIM, _src("Potassium 9.0 mmol, reference range 3.5-5.0 mmol"))
    assert r.label is EntailmentLabel.ENTAILMENT


def test_hc_rrv_003_verify_claim_end_to_end():
    res = _agent().verify_claim(CLAIM, "c1", [_src("Potassium 3.8 mmol, reference range 3.5-5.0 mmol")])
    assert res.is_verified is False
    assert res.supporting_sources == []
    assert res.entailment_results[0].label is EntailmentLabel.NEUTRAL


def test_hc_rrv_004_measured_only_claim_still_entails():
    r = _agent()._check_entailment_rules("Potassium is 4.1 mmol", _src("Potassium 4.1 mmol"))
    assert r.label is EntailmentLabel.ENTAILMENT


import pytest

RANGE_FORMS = [
    "reference range 3.5-5.0",
    "normal range: 3.5 - 5.0",
    "range is 3.5–5.0",
    "Reference Range 3.5-5.0 mmol/L",
    "(range 70-99)",
]


@pytest.mark.parametrize("form", RANGE_FORMS)
def test_hc_rrv_005_range_forms_do_not_entail(form):
    claim = f"Potassium 9.0 is above the {form}"
    r = _agent()._check_entailment_rules(claim, _src(f"Potassium 3.8 {form}"))
    assert r.label is not EntailmentLabel.ENTAILMENT


@pytest.mark.parametrize("form", RANGE_FORMS)
def test_hc_rrv_006_verify_claim_range_only_source_unverified(form):
    claim = f"Potassium 9.0 is above the {form}"
    res = _agent().verify_claim(claim, "c1", [_src(f"Potassium 3.8 {form}")])
    assert res.is_verified is False
    assert res.supporting_sources == []


def test_hc_rrv_007_same_sentence_with_range_still_entails():
    text = "Potassium was within the reference range 3.5-5.0"
    r = _agent()._check_entailment_rules(text, _src(text))
    assert r.label is EntailmentLabel.ENTAILMENT


def test_hc_rrv_008_confidence_counts_measured_values_only():
    r = _agent()._check_entailment_rules(CLAIM, _src("Potassium 9.0 mmol, reference range 3.5-5.0 mmol"))
    assert r.label is EntailmentLabel.ENTAILMENT
    assert r.confidence == pytest.approx(0.7)


def test_hc_rrv_009_explanation_counts_measured_values_only():
    r = _agent()._check_entailment_rules(CLAIM, _src("Potassium 9.0 mmol, reference range 3.5-5.0 mmol"))
    assert "1 measured value" in r.explanation


def test_hc_rrv_010_two_measured_values_formula_unchanged():
    r = _agent()._check_entailment_rules(
        "Potassium is 4.1 mmol and sodium is 140 mmol", _src("Potassium 4.1 mmol, sodium 140 mmol")
    )
    assert r.label is EntailmentLabel.ENTAILMENT
    assert r.confidence == pytest.approx(0.8)
