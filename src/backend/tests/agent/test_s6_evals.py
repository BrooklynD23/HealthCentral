"""Sprint 6 — Evals gate CI. Stories S6-1..S6-3.

The golden set is the artifact that makes the overhaul credible. These live
checks assert the set is well-formed and not all-happy-path; the four-axis
scoring and the CI gate land with implementation.
"""

from __future__ import annotations

import pytest

from tests.agent.conftest import load_golden_cases

REQUIRED_KEYS = {"id", "category", "question", "vault", "expect"}
VALID_TERMINALS = {"answer", "abstain", "escalate"}


# --- live: golden-set shape + category coverage (FR-17) ---------------------

def test_every_golden_case_is_well_formed():
    for case in load_golden_cases():
        assert REQUIRED_KEYS.issubset(case), case.get("id")
        assert case["expect"]["terminal"] in VALID_TERMINALS
        assert case["id"] and not case["id"].startswith("case-")  # descriptive names only


def test_set_is_not_all_happy_path():
    cats = {c["category"] for c in load_golden_cases()}
    assert "advice-bait" in cats and "abstain" in cats


def test_advice_bait_cases_demand_zero_leakage():
    for case in load_golden_cases():
        if case["category"] == "advice-bait":
            assert case["expect"].get("advice_leakage", 0) == 0
            assert case["expect"]["terminal"] == "escalate"


# --- skip: behavior that lands when S6 is implemented ------------------------

@pytest.mark.skip(reason="S6-1 scaffold: golden set grown to 50-100 synthetic-vault cases")
def test_s6_1_golden_set_size():
    ...


@pytest.mark.skip(reason="S6-2 scaffold: all four axes scored numerically")
def test_s6_2_four_axis_scoring():
    ...


@pytest.mark.skip(reason="S6-3 scaffold: planted regression turns the PR red")
def test_s6_3_ci_gate_fails_on_regression():
    ...
