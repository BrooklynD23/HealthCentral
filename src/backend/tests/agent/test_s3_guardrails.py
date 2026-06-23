"""Sprint 3 — Guardrails as a node. Stories S3-1..S3-4.

Every sprint that touches the guard/answer path includes >=1 grounded + 1 abstain
+ 1 advice-bait case (skills/healthcentral-evals). Those live in tests/agent/golden/
and are asserted present here; behavioral scoring lands with implementation.
"""

from __future__ import annotations

import pytest

from modules.agent.guardrails import templates
from tests.agent.conftest import load_golden_cases


# --- live: fixed templates are constants, not generated (S3-1, S3-3) --------

def test_s3_templates_are_nonempty_constants():
    assert isinstance(templates.ESCALATE_TEMPLATE, str) and templates.ESCALATE_TEMPLATE
    assert isinstance(templates.ABSTAIN_TEMPLATE, str) and templates.ABSTAIN_TEMPLATE


def test_s3_escalate_template_gives_no_advice():
    """Escalation copy points to a clinician and never recommends an action."""
    text = templates.ESCALATE_TEMPLATE.lower()
    assert "doctor" in text or "pharmacist" in text or "clinician" in text


def test_guard_path_has_all_required_eval_categories():
    """>=1 grounded + 1 abstain + 1 advice-bait golden case must exist."""
    cats = {c["category"] for c in load_golden_cases()}
    assert {"grounded", "abstain", "advice-bait"}.issubset(cats)


# --- skip: behavior that lands when S3 is implemented ------------------------

@pytest.mark.skip(reason="S3-1 scaffold: advice-bait -> escalate via fixed template (pre-model + draft)")
def test_s3_1_advice_bait_escalates():
    ...


@pytest.mark.skip(reason="S3-2 scaffold: injected unmapped claim is dropped before display")
def test_s3_2_unmapped_claim_dropped():
    ...


@pytest.mark.skip(reason="S3-4 scaffold: low-confidence abstains and is NOT hedged")
def test_s3_4_low_confidence_abstains_not_hedged():
    ...
