"""Sprint 4 — PHI gate + external path. Stories S4-1..S4-3."""

from __future__ import annotations

import pytest

from modules.agent.guardrails import redaction_gate


# --- live: the gate exists and exposes no bypass parameter (SG-4) ------------

def test_s4_1_redaction_gate_signature_has_no_bypass():
    import inspect

    params = inspect.signature(redaction_gate.gate_external_payload).parameters
    assert "payload" in params
    assert not any("bypass" in p or "skip" in p for p in params)


# --- skip: behavior that lands when S4 is implemented ------------------------

@pytest.mark.skip(reason="S4-1 scaffold: external payload passes RedactionEngine before egress")
def test_s4_1_payload_redacted_before_external_call():
    ...


@pytest.mark.skip(reason="S4-2 scaffold: full loop completes with network disabled")
def test_s4_2_offline_loop_completes():
    ...


@pytest.mark.skip(reason="S4-3 scaffold: golden set ~30 cases incl. advice-bait + abstention pass")
def test_s4_3_golden_set_categories_pass():
    ...
