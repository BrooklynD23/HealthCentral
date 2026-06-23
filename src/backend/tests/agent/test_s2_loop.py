"""Sprint 2 — The loop closes. Stories S2-1..S2-4."""

from __future__ import annotations

from datetime import datetime

import pytest

from modules.agent.state import MAX_STEPS, RunLog, RunStep


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


# --- skip: behavior that lands when S2 is implemented ------------------------

@pytest.mark.skip(reason="S2-2 scaffold: over-budget yields graceful abstain terminal")
def test_s2_2_over_budget_abstains_gracefully():
    ...


@pytest.mark.skip(reason="S2-3 scaffold: replay reconstructs a run from its log")
def test_s2_3_run_log_replays():
    ...


@pytest.mark.skip(reason="S2-4 scaffold: 2 seed eval cases (1 grounded, 1 abstain) pass")
def test_s2_4_seed_eval_cases_pass():
    ...
