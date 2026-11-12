"""DISCLAIMER-GUARD-QUIRK: the fixer and the validator must agree on "enough disclaimers".

validate_interpretation needs >= 2 of the 3 REQUIRED_DISCLAIMER_KEYWORDS groups in
interpretation + advice. add_required_disclaimers used to append the interpretation
disclaimer only when the interpretation had ZERO groups, so a one-group text was
neither fixed nor allowed through.
"""
from __future__ import annotations

import itertools

import pytest

from modules.interpret_safety import InterpretationSafetyGuard

INTERP_DISCLAIMER = (
    "\n\nThis information is for educational purposes only. "
    "Please consult your healthcare provider for personalized medical advice."
)
ADVICE_DISCLAIMER = (
    "\n\nAlways consult your healthcare provider before making "
    "any changes to your diet, exercise, or lifestyle."
)

ONE_GROUP_TEXT = (
    "Your LDL Cholesterol result is listed as 120 mg/dL [KB:ldl]. "
    "Ask your doctor what it means for you."
)

# Interpretation texts naming exactly N disclaimer groups (doctor / provider /
# educational), cited so only the disclaimer check can fail.
BASE = "Your LDL Cholesterol result is listed as 120 mg/dL [KB:ldl]."
INTERP_BY_GROUPS = {
    0: BASE,
    1: BASE + " Ask your doctor what it means for you.",
    2: BASE + " Ask your doctor what it means for you. This is educational information.",
    3: BASE
    + " Ask your doctor what it means for you. This is educational information."
    + " Please consult your healthcare provider.",
}
ADVICE_CASES = {
    "none": None,
    "empty": "",
    "zero_group": "Eat more fibre.",
    "one_same_group": "Ask your doctor about diet.",
    "one_different_group": "This is educational advice about diet.",
}


@pytest.fixture
def guard():
    return InterpretationSafetyGuard()


def _add_validate(guard, interp, advice=None):
    i, a = guard.add_required_disclaimers(interpretation_text=interp, advice_text=advice)
    return i, a, guard.validate_interpretation(
        interpretation_text=i, advice_text=a, require_citations=True
    )


def test_hc_dgq_001_one_group_interpretation_passes_after_add(guard):
    i, a, verdict = _add_validate(guard, ONE_GROUP_TEXT)
    assert verdict.passed is True, verdict.checks_failed
    assert "missing_disclaimers" not in verdict.checks_failed
    assert i.count(INTERP_DISCLAIMER) == 1


def test_hc_dgq_002_one_group_interp_with_same_group_advice_passes(guard):
    i, a, verdict = _add_validate(guard, ONE_GROUP_TEXT, "Ask your doctor about diet.")
    assert verdict.passed is True, verdict.checks_failed
    assert i.count(INTERP_DISCLAIMER) == 1


@pytest.mark.parametrize(
    "groups,advice_key", list(itertools.product(INTERP_BY_GROUPS, ADVICE_CASES))
)
def test_hc_dgq_003_missing_disclaimers_is_unreachable_after_add(guard, groups, advice_key):
    _, _, verdict = _add_validate(guard, INTERP_BY_GROUPS[groups], ADVICE_CASES[advice_key])
    assert "missing_disclaimers" not in verdict.checks_failed, (groups, advice_key)


# Expected outputs pinned from main (before the fix): every case below already
# passed validation there, so the fix must not change a single byte.
_I2 = INTERP_BY_GROUPS[2]
_I1 = INTERP_BY_GROUPS[1]
BYTE_IDENTITY_CASES = [
    # (id, interp, advice, expected_interp, expected_advice)
    ("two_groups_no_append", _I2, None, _I2, ""),
    ("zero_group_append_once", BASE, None, BASE + INTERP_DISCLAIMER, ""),
    (
        "zero_group_with_disclaimed_advice",
        BASE,
        "Ask your doctor about diet.",
        BASE + INTERP_DISCLAIMER,
        "Ask your doctor about diet.",
    ),
    (
        "one_group_interp_zero_group_advice_only_advice_fixed",
        _I1,
        "Eat more fibre.",
        _I1,
        "Eat more fibre." + ADVICE_DISCLAIMER,
    ),
    (
        "one_group_interp_different_group_advice_no_append",
        _I1,
        "This is educational advice about diet.",
        _I1,
        "This is educational advice about diet.",
    ),
]


@pytest.mark.parametrize(
    "interp,advice,expected_i,expected_a",
    [c[1:] for c in BYTE_IDENTITY_CASES],
    ids=[c[0] for c in BYTE_IDENTITY_CASES],
)
def test_hc_dgq_004_passing_cards_are_byte_identical(guard, interp, advice, expected_i, expected_a):
    i, a, verdict = _add_validate(guard, interp, advice)
    assert verdict.passed is True, verdict.checks_failed
    assert (i, a) == (expected_i, expected_a)
    assert i.count(INTERP_DISCLAIMER) <= 1
    # Idempotent: a second pass changes nothing.
    assert guard.add_required_disclaimers(i, a) == (i, a)


def test_hc_dgq_005_one_group_text_with_dosing_is_still_withheld(guard):
    text = ONE_GROUP_TEXT + " You should take 20 mg atorvastatin daily."
    _, _, verdict = _add_validate(guard, text)
    assert verdict.passed is False
    assert verdict.checks_failed
    assert all(c.startswith("prohibited_") for c in verdict.checks_failed), verdict.checks_failed
