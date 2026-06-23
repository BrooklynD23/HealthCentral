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


async def emit_audit_event(event: AgentAuditEvent, *, db: Any = None) -> None:
    """Persist one agent audit event through core.audit.create_audit_log.

    SCAFFOLD: implemented in Sprint 0 (story S0-3).
    """
    raise NotImplementedError("S0-3: wire emit_audit_event -> core.audit.create_audit_log")
