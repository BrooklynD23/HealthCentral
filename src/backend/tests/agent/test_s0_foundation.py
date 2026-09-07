"""Sprint 0 — Foundation & Flag. Stories S0-1..S0-4.

Live assertions verify the scaffold is import-clean and the day-one contracts
(terminal schema, audit-event schema, flag default) hold. Skip-marked stubs mark
behavior that lands when S0 is implemented.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from modules.agent import audit, schemas, settings, state


# --- live: scaffold contracts that hold today -------------------------------

def test_s0_1_agent_package_imports_clean():
    """S0-1: modules/agent imports clean and the graph runner is importable."""
    from modules.agent import graph  # noqa: F401

    assert graph is not None


def test_s0_2_flag_defaults_off():
    """S0-2 set the agent flag default OFF; S5 cutover flipped it ON per spec
    AC (AGILE_PLAN.md Sprint 5 S5-1) — this is the documented cutover, not a
    weakening. The legacy path remains reachable as a fallback (flag False,
    or any agent exception) — see api/assistant.py.
    """
    assert settings.AGENT_ENABLED_DEFAULT is True


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

def test_s0_2_flag_off_means_legacy_path_unchanged():
    """S0-2 / S5-1: absent key / empty settings / None fall through to
    ``AGENT_ENABLED_DEFAULT`` (True since the S5 cutover); an explicit
    ``False`` always wins, which is exactly what keeps the legacy
    ``/assistant/`` path reachable as the documented fallback.
    """
    # Absent key in a dict-like settings payload -> default (True post-S5-1).
    assert settings.is_agent_enabled({}) is True
    # No settings row at all (fresh profile) -> default.
    assert settings.is_agent_enabled(None) is True
    # Explicitly falsy always wins over the default.
    assert settings.is_agent_enabled({"agent_enabled": False}) is False

    # Explicitly truthy -> True, via dict shape.
    assert settings.is_agent_enabled({"agent_enabled": True}) is True

    # Explicitly truthy -> True, via attribute access (ORM/Pydantic-style).
    class _Settings:
        agent_enabled = True

    assert settings.is_agent_enabled(_Settings()) is True

    # Attribute absent on an object -> default (True post-S5-1).
    class _EmptySettings:
        pass

    assert settings.is_agent_enabled(_EmptySettings()) is True


@pytest.mark.asyncio
async def test_s0_3_audit_event_persists_through_monitoring():
    """S0-3: emit_audit_event calls core.audit.create_audit_log exactly once
    with fields mapped per the audit.py docstring contract.

    Updated for AUDIT-PHI-001: the persisted `action` is now a static per-node
    template and the event's own action string travels in `details` instead.
    Passing it through verbatim would require registering every tool name in
    ALLOWED_ACTIONS, and any tool added later would silently have its rows
    degraded to a bare event type until someone noticed.
    """
    event = audit.AgentAuditEvent(
        run_id="run-1",
        node="plan",
        profile_id="profile-1",
        event_type="agent.plan",
        action="chose tool",
        step_index=0,
        details={"tool_count": 2},
    )
    fake_db = object()

    with patch("core.audit.create_audit_log", new_callable=AsyncMock) as mock_create:
        await audit.emit_audit_event(event, db=fake_db)

    mock_create.assert_awaited_once_with(
        fake_db,
        event_type="agent.plan",
        action="Agent planned a step",
        profile_id="profile-1",
        entity_type="agent_node",
        entity_id="run-1",
        details={"tool_count": 2, "node": "plan", "action": "chose tool"},
    )
