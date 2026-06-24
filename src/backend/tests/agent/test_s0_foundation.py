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

def test_s0_2_flag_off_means_legacy_path_unchanged():
    """S0-2: flag defaults OFF for absent key / empty settings / None; ON only
    when agent_enabled is explicitly truthy — so the legacy /assistant/ path
    is unaffected unless a profile opts in.
    """
    # Absent key in a dict-like settings payload.
    assert settings.is_agent_enabled({}) is False
    # No settings row at all (fresh profile).
    assert settings.is_agent_enabled(None) is False
    # Explicitly falsy.
    assert settings.is_agent_enabled({"agent_enabled": False}) is False

    # Explicitly truthy -> True, via dict shape.
    assert settings.is_agent_enabled({"agent_enabled": True}) is True

    # Explicitly truthy -> True, via attribute access (ORM/Pydantic-style).
    class _Settings:
        agent_enabled = True

    assert settings.is_agent_enabled(_Settings()) is True

    # Attribute absent on an object -> default OFF.
    class _EmptySettings:
        pass

    assert settings.is_agent_enabled(_EmptySettings()) is False


@pytest.mark.asyncio
async def test_s0_3_audit_event_persists_through_monitoring():
    """S0-3: emit_audit_event calls core.audit.create_audit_log exactly once
    with fields mapped per the audit.py docstring contract.
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
        action="chose tool",
        profile_id="profile-1",
        entity_type="agent_node",
        entity_id="run-1",
        details={"tool_count": 2},
    )
