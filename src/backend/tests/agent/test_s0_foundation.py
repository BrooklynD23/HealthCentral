"""Sprint 0 — Foundation & Flag. Stories S0-1..S0-4.

Live assertions verify the scaffold is import-clean and the day-one contracts
(terminal schema, audit-event schema, flag default) hold. Skip-marked stubs mark
behavior that lands when S0 is implemented.
"""

from __future__ import annotations

import pytest

from modules.agent import audit, schemas, settings, state


# --- live: scaffold contracts that hold today -------------------------------

def test_s0_1_agent_package_imports_clean():
    """S0-1: modules/agent imports clean and the graph runner is importable."""
    from modules.agent import graph  # noqa: F401

    assert graph is not None


def test_s0_2_flag_defaults_off():
    """S0-2: the agent flag default is OFF (legacy path unchanged)."""
    assert settings.AGENT_ENABLED_DEFAULT is False


def test_s0_3_audit_event_schema_has_required_fields():
    """S0-3: AgentAuditEvent carries run_id, node, profile_id, event_type, step_index."""
    ev = audit.AgentAuditEvent(
        run_id="r1", node="plan", profile_id="p1",
        event_type="agent.plan", action="chose tool", step_index=0,
    )
    assert ev.node == "plan" and ev.details == {}


def test_terminal_schema_validates_three_terminals():
    for t in ("answer", "abstain", "escalate"):
        term = schemas.AgentTerminal(terminal=t, text="…", run_id="r1")
        assert term.terminal == t


def test_step_budget_constant_is_five():
    assert state.MAX_STEPS == 5


# --- skip: behavior that lands when S0 is implemented ------------------------

@pytest.mark.skip(reason="S0-2 scaffold: is_agent_enabled reads model settings")
def test_s0_2_flag_off_means_legacy_path_unchanged():
    ...


@pytest.mark.skip(reason="S0-3 scaffold: emit_audit_event -> core.audit persists one event")
def test_s0_3_audit_event_persists_through_monitoring():
    ...
