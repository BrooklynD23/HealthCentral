"""Sprint 1 — First tool, end-to-end. Stories S1-1..S1-4."""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from modules.agent.tools.query_observations import (
    ObservationRow,
    QueryObservationsInput,
    QueryObservationsTool,
)
from tests.agent.conftest import seed_document, seed_observation


# --- live: typed-registry / tool contracts (FR-2, FR-3) ---------------------

def test_s1_1_malformed_tool_args_rejected_by_validation():
    """S1-1: bad input fails Pydantic validation; it never reaches the tool body."""
    with pytest.raises(ValidationError):
        QueryObservationsInput(limit=999)  # le=100


def test_s1_2_output_row_can_only_represent_verified():
    """S1-2: ObservationRow pins verified=True — unverified rows can't be returned."""
    with pytest.raises(ValidationError):
        ObservationRow(
            observation_id="o1", analyte="LDL", value=1.0,
            collected_at="2025-12-01T00:00:00", verified=False,
        )


def test_query_observations_tool_declares_read_only_schemas():
    assert QueryObservationsTool.name == "query_observations"
    assert QueryObservationsTool.InputModel is QueryObservationsInput


# --- live: behavior landed in S1 ---------------------------------------------

@pytest.mark.asyncio
async def test_s1_2_returns_only_verified_rows(agent_profile_db, make_run_context):
    """S1-2: query returns only verified rows for current profile."""
    session_maker = agent_profile_db
    profile_id = str(uuid.uuid4())
    doc_id = await seed_document(session_maker, profile_id=profile_id)

    verified_id = await seed_observation(
        session_maker, profile_id=profile_id, doc_id=doc_id,
        analyte="LDL", value=138.0, verified=True,
    )
    await seed_observation(
        session_maker, profile_id=profile_id, doc_id=doc_id,
        analyte="LDL", value=999.0, verified=False,
    )

    ctx = make_run_context(session_maker, profile_id=profile_id)
    tool = QueryObservationsTool()
    output = await tool.run(QueryObservationsInput(), ctx)

    assert len(output.rows) == 1
    assert output.rows[0].observation_id == verified_id
    assert output.rows[0].verified is True
    assert output.rows[0].value == 138.0


@pytest.mark.asyncio
async def test_s1_3_flag_on_answer_has_citation(agent_profile_db, make_run_context):
    """S1-3: flag-on plan->act->answer yields >=1 citation."""
    from modules.agent.graph import run_agent

    session_maker = agent_profile_db
    profile_id = str(uuid.uuid4())
    doc_id = await seed_document(session_maker, profile_id=profile_id)
    await seed_observation(
        session_maker, profile_id=profile_id, doc_id=doc_id,
        analyte="LDL", value=138.0, verified=True,
    )

    ctx = make_run_context(session_maker, profile_id=profile_id)
    terminal = await run_agent("How has my LDL changed over the last year?", ctx)

    assert terminal.terminal == "answer"
    assert len(terminal.citations) >= 1


@pytest.mark.asyncio
async def test_s1_4_audit_event_per_node(agent_profile_db, make_run_context, monkeypatch):
    """S1-4: plan, act, and draft each emit exactly one audit event."""
    from modules.agent import audit
    from modules.agent.graph import run_agent

    emitted: list[str] = []
    original = audit.emit_audit_event

    async def _capture(event, *, db=None):
        emitted.append(event.node)
        return await original(event, db=db)

    monkeypatch.setattr(audit, "emit_audit_event", _capture)
    # query_observations / compute_trend / plan / draft import emit_audit_event
    # by reference at module load time, so patch each module's bound name too.
    # (Since S2-2, a "changed over time" question like this test's plans
    # compute_trend directly rather than query_observations — see
    # nodes/plan.py's trend-keyword detection — so both tools' bound
    # references need patching for this capture to see every act event.)
    import modules.agent.nodes.plan as plan_mod
    import modules.agent.nodes.draft as draft_mod
    import modules.agent.tools.query_observations as qo_mod
    import modules.agent.tools.compute_trend as ct_mod

    monkeypatch.setattr(plan_mod, "emit_audit_event", _capture)
    monkeypatch.setattr(draft_mod, "emit_audit_event", _capture)
    monkeypatch.setattr(qo_mod, "emit_audit_event", _capture)
    monkeypatch.setattr(ct_mod, "emit_audit_event", _capture)

    session_maker = agent_profile_db
    profile_id = str(uuid.uuid4())
    doc_id = await seed_document(session_maker, profile_id=profile_id)
    await seed_observation(
        session_maker, profile_id=profile_id, doc_id=doc_id,
        analyte="LDL", value=138.0, verified=True,
    )

    ctx = make_run_context(session_maker, profile_id=profile_id)
    await run_agent("How has my LDL changed over the last year?", ctx)

    assert emitted.count("plan") == 1
    assert emitted.count("act") == 1
    assert emitted.count("draft") == 1
