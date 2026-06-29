"""Sprint 2 — The loop closes. Stories S2-1..S2-4."""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest

from modules.agent.state import MAX_STEPS, RunLog, RunStep
from tests.agent.conftest import load_golden_cases, seed_document, seed_observation
from tests.agent.eval_harness import run_golden_case


def _act_step(i: int) -> RunStep:
    return RunStep(step_index=i, node="act", timestamp=datetime.utcnow())


# --- live: budget accounting on the run log (FR-6) --------------------------

def test_s2_2_budget_exceeded_after_max_act_steps():
    log = RunLog(run_id="r1", profile_id="p1", steps=[_act_step(i) for i in range(MAX_STEPS)])
    assert log.act_count() == MAX_STEPS
    assert log.budget_exceeded() is True


def test_s2_2_under_budget_when_below_max():
    log = RunLog(run_id="r1", profile_id="p1", steps=[_act_step(0)])
    assert log.budget_exceeded() is False


# --- live: the four new tools declare read-only typed schemas (FR-5) --------

def test_s2_1_new_tools_declare_schemas():
    from modules.agent.tools.check_verification import CheckVerificationTool
    from modules.agent.tools.compute_trend import ComputeTrendTool
    from modules.agent.tools.lookup_reference import LookupReferenceTool
    from modules.agent.tools.retrieve_chunks import RetrieveChunksTool

    for tool in (ComputeTrendTool, RetrieveChunksTool, LookupReferenceTool, CheckVerificationTool):
        assert isinstance(tool.name, str) and tool.InputModel and tool.OutputModel


def test_s2_1_trend_point_carries_source_handle():
    """Groundedness: every trend point must carry an observation_id to cite."""
    from pydantic import ValidationError

    from modules.agent.tools.compute_trend import TrendPoint

    assert "observation_id" in TrendPoint.model_fields
    with pytest.raises(ValidationError):
        TrendPoint(collected_at="2025-12-01T00:00:00", value=1.0)  # missing source handle


def test_s2_1_check_verification_discovers_by_analyte_without_values():
    """Discovery path for unverified analytes; status only, never the value."""
    from pydantic import ValidationError

    from modules.agent.tools.check_verification import (
        CheckVerificationInput,
        CheckVerificationOutput,
    )

    # exactly one selector required
    CheckVerificationInput(analyte="LDL")
    CheckVerificationInput(observation_id="o1")
    with pytest.raises(ValidationError):
        CheckVerificationInput()
    with pytest.raises(ValidationError):
        CheckVerificationInput(analyte="LDL", observation_id="o1")
    # output reports status, never an unverified value
    assert "status" in CheckVerificationOutput.model_fields
    assert "value" not in CheckVerificationOutput.model_fields


# --- live: the loop closes (S2-2, S2-3, S2-4) --------------------------------

@pytest.mark.asyncio
async def test_s2_2_over_budget_abstains_gracefully(agent_profile_db, make_run_context):
    """A question with no detected analyte and no verified data never finds
    grounding, so the planner keeps replanning query_observations on every
    turn. reflect() must catch this BEFORE a 6th act call and return
    abstain_budget rather than letting the loop spin past MAX_STEPS.
    """
    from modules.agent.graph import run_agent

    session_maker = agent_profile_db
    profile_id = str(uuid.uuid4())
    # No observations at all seeded — there is nothing for any tool to find.

    ctx = make_run_context(session_maker, profile_id=profile_id)
    terminal = await run_agent(
        "Correlate every biomarker in my record and explain all interactions.", ctx
    )

    assert terminal.terminal == "abstain"
    assert terminal.citations == []


@pytest.mark.asyncio
async def test_s2_3_run_log_replays(agent_profile_db, make_run_context):
    """Replaying a completed run's RunLog reproduces the same terminal
    WITHOUT re-calling any tool (monkeypatch act's registry lookup to prove
    replay never touches it).
    """
    from modules.agent import graph as graph_mod
    from modules.agent.graph import replay, run_agent

    session_maker = agent_profile_db
    profile_id = str(uuid.uuid4())
    doc_id = await seed_document(session_maker, profile_id=profile_id)
    await seed_observation(
        session_maker, profile_id=profile_id, doc_id=doc_id,
        analyte="LDL", value=160.0, verified=True,
        collected_at=datetime(2025, 6, 1),
    )
    await seed_observation(
        session_maker, profile_id=profile_id, doc_id=doc_id,
        analyte="LDL", value=138.0, verified=True,
        collected_at=datetime(2025, 12, 1),
    )

    ctx = make_run_context(session_maker, profile_id=profile_id)
    run_log = graph_mod.RunLog(run_id=ctx.run_id, profile_id=ctx.profile_id)

    # Run the real graph once, capturing the RunLog it produces, by swapping
    # in a thin wrapper that mirrors run_agent's own bookkeeping. Simplest
    # faithful way to get a populated RunLog: call run_agent, then rebuild
    # the RunLog by re-deriving it is circular — so instead we drive the
    # same path run_agent takes but keep our own run_log reference by
    # monkeypatching RunLog's constructor for the duration of this call.
    original_run_log_cls = graph_mod.RunLog
    captured: list[graph_mod.RunLog] = []

    class _CapturingRunLog(original_run_log_cls):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            captured.append(self)

    graph_mod.RunLog = _CapturingRunLog
    try:
        live_terminal = await run_agent("How has my LDL changed over the last year?", ctx)
    finally:
        graph_mod.RunLog = original_run_log_cls

    assert captured, "run_agent should have constructed exactly one RunLog"
    completed_log = captured[0]
    assert completed_log.terminal == live_terminal

    # Replay must reproduce the same terminal WITHOUT re-calling any tool.
    def _boom(*args, **kwargs):
        raise AssertionError("replay must not re-call any tool")

    import modules.agent.tools.registry as registry_mod

    original_get = registry_mod.get
    registry_mod.get = _boom
    try:
        replayed_terminal = replay(completed_log)
    finally:
        registry_mod.get = original_get

    assert replayed_terminal.terminal == live_terminal.terminal
    assert replayed_terminal.text == live_terminal.text
    assert replayed_terminal.citations == live_terminal.citations


@pytest.mark.asyncio
async def test_s2_4_seed_eval_cases_pass():
    """The two S2 seed golden cases pass through the eval harness end-to-end."""
    cases = {case["id"]: case for case in load_golden_cases()}

    grounded_case = cases["grounded-ldl-trend"]
    _, grounded_failures = await run_golden_case(grounded_case)
    assert grounded_failures == [], grounded_failures

    abstain_case = cases["abstain-unverified-ldl"]
    _, abstain_failures = await run_golden_case(abstain_case)
    assert abstain_failures == [], abstain_failures
