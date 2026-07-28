"""Audit-event schema + emission hook for agent nodes (Phase 0).

The audit trail IS the governance deliverable: every node emits one structured
event. A node with no audit event is not done (skills/healthcentral-agent).

Read GETs are NOT auto-audited by SecurityAuditMiddleware (see
docs/agile/RECONCILIATION.md R-4), so nodes emit explicitly through this hook.
At implementation time ``emit_audit_event`` maps onto::

    from core.audit import create_audit_log
    await create_audit_log(
        db, event_type=event.event_type, action=event.action,
        profile_id=event.profile_id, entity_type="agent_node",
        entity_id=event.run_id, details=event.details,
    )

``details`` MUST NOT carry raw PHI prompts — handles/counts only (PRD §7).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

AgentNode = Literal["plan", "act", "reflect", "draft", "guard", "terminal"]


class AgentAuditEvent(BaseModel):
    run_id: str
    node: AgentNode
    profile_id: str
    event_type: str  # e.g. "agent.plan"
    action: str  # human-readable
    step_index: int
    details: dict[str, Any] = Field(default_factory=dict)


# Static per-node action templates (AUDIT-PHI-001). Keyed by AgentNode so a new
# *tool* never needs a new entry — only a genuinely new node would.
AGENT_NODE_ACTIONS: dict[str, str] = {
    "plan": "Agent planned a step",
    "act": "Agent used a tool",
    "draft": "Agent drafted a response",
    "reflect": "Agent reflected on a draft",
}


async def emit_audit_event(event: AgentAuditEvent, *, db: Any = None) -> None:
    """Persist one agent audit event through core.audit.create_audit_log.

    No-ops gracefully when ``db`` is ``None`` so unit tests can exercise
    callers without a live database session. ``event.details`` must already
    contain only handles/counts — never raw PHI prompts (PRD §7); this hook
    does not scrub, it only forwards.

    AUDIT-PHI-001: the persisted ``action`` is a static per-node template, and
    the specific node/tool identity travels in ``details`` instead. Passing
    ``event.action`` straight through would mean registering every tool name in
    ``ALLOWED_ACTIONS`` and silently degrading each new tool's audit rows until
    someone remembered to. The identity is not lost — it is just carried as
    allowlisted enum data rather than as free-form prose.
    """
    if db is None:
        return

    from core.audit import create_audit_log

    details = dict(event.details)
    details.setdefault("node", event.node)
    # `action` here is the node/tool identity ("query_timeline", "plan:draft").
    # Keep it, but as an allowlisted enum-shaped value rather than the row's
    # action string. Values with spaces are dropped by the scrubber anyway.
    details.setdefault("action", event.action)

    await create_audit_log(
        db,
        event_type=event.event_type,
        action=AGENT_NODE_ACTIONS.get(event.node, "Agent step"),
        profile_id=event.profile_id,
        entity_type="agent_node",
        entity_id=event.run_id,
        details=details,
    )
