"""Sprint 4 — PHI gate + external path. Stories S4-1..S4-3."""

from __future__ import annotations

import socket

import pytest

from modules.agent.guardrails import redaction_gate


# --- live: the gate exists and exposes no bypass parameter (SG-4) ------------

def test_s4_1_redaction_gate_signature_has_no_bypass():
    import inspect

    params = inspect.signature(redaction_gate.gate_external_payload).parameters
    assert "payload" in params
    assert not any("bypass" in p or "skip" in p for p in params)


# --- live: S4-1 behavior ------------------------------------------------------

def test_s4_1_payload_redacted_before_external_call():
    """The gate is a thin adapter over RedactionEngine — same output, no bypass."""
    from modules.redaction import RedactionEngine

    payload = "Patient: John Smith, SSN 123-45-6789, contact john@example.com"
    expected = RedactionEngine(policy_level="strict").redact(payload).text

    gated = redaction_gate.gate_external_payload(payload, policy_level="strict")

    assert gated == expected
    assert "123-45-6789" not in gated
    assert "john@example.com" not in gated


def test_s4_1_gate_fails_closed_on_invalid_policy_level():
    """Unavailable/misconfigured redaction must RAISE, never return the raw payload."""
    with pytest.raises(Exception):
        redaction_gate.gate_external_payload("anything with PHI", policy_level="not-a-real-level")


def test_s4_1_gate_fails_closed_when_engine_raises(monkeypatch):
    """If the underlying engine construction/redaction blows up, propagate — no silent passthrough."""
    import modules.redaction as redaction_mod

    class _BoomEngine:
        def __init__(self, *a, **kw):
            raise RuntimeError("redaction engine unavailable")

    monkeypatch.setattr(redaction_mod, "RedactionEngine", _BoomEngine)

    with pytest.raises(RuntimeError):
        redaction_gate.gate_external_payload("sensitive payload", policy_level="standard")


# --- live: S4-2 offline integration -----------------------------------------

def test_s4_2_offline_loop_completes(monkeypatch):
    """The full default agent loop never touches the network.

    Disables INTERNET socket creation/connection at the lowest level (the same
    chokepoint httpx/requests/urllib all eventually call through) and asserts
    both a grounded case (-> answer with >=1 citation) and an abstain case
    (-> abstain) complete locally with zero network access, proving the
    local-first FR/NFR for the default run_agent path (no external-runner call
    exists in this path at all — see redaction_gate.py's module docstring).

    Only AF_INET/AF_INET6 socket construction and ``create_connection`` are
    blocked — AF_UNIX sockets are left alone because asyncio's own event loop
    uses a local AF_UNIX self-pipe internally (unrelated to network egress);
    blocking those would produce a false positive having nothing to do with
    this test's actual claim.
    """
    import asyncio

    from tests.agent.conftest import load_golden_cases
    from tests.agent.eval_harness import run_golden_case

    real_socket = socket.socket

    def _guarded_socket(family=socket.AF_INET, *args, **kwargs):
        if family in (socket.AF_INET, socket.AF_INET6):
            raise AssertionError("network socket attempted during offline agent run")
        return real_socket(family, *args, **kwargs)

    def _network_blocked(*args, **kwargs):
        raise AssertionError("network access attempted during offline agent run")

    monkeypatch.setattr(socket, "socket", _guarded_socket)
    monkeypatch.setattr(socket, "create_connection", _network_blocked)

    cases = {case["id"]: case for case in load_golden_cases()}

    async def _run_both():
        grounded_terminal, grounded_failures = await run_golden_case(cases["grounded-ldl-trend"])
        abstain_terminal, abstain_failures = await run_golden_case(cases["abstain-unverified-ldl"])
        return grounded_terminal, grounded_failures, abstain_terminal, abstain_failures

    grounded_terminal, grounded_failures, abstain_terminal, abstain_failures = asyncio.run(_run_both())

    assert grounded_failures == [], grounded_failures
    assert grounded_terminal.terminal == "answer"
    assert len(grounded_terminal.citations) >= 1

    assert abstain_failures == [], abstain_failures
    assert abstain_terminal.terminal == "abstain"


# --- live: S4-3 golden set growth --------------------------------------------

def test_s4_3_golden_set_categories_pass():
    """Every golden case (~30, spanning all required categories) resolves to
    its expected terminal (and min_citations / drops_unmapped where the
    fixture specifies them) through the real eval harness.
    """
    import asyncio

    from tests.agent.conftest import load_golden_cases
    from tests.agent.eval_harness import run_golden_case

    cases = load_golden_cases()
    assert len(cases) >= 30, f"expected >=30 golden cases, found {len(cases)}"

    categories = {case["category"] for case in cases}
    required = {"grounded", "abstain", "advice-bait", "mixed"}
    assert required.issubset(categories), f"missing categories: {required - categories}"

    async def _run_all():
        all_failures: dict[str, list[str]] = {}
        for case in cases:
            _, failures = await run_golden_case(case)
            if failures:
                all_failures[case["id"]] = failures
        return all_failures

    all_failures = asyncio.run(_run_all())
    assert all_failures == {}, all_failures
