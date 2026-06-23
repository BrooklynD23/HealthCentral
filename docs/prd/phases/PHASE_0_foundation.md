# Phase 0 — Foundation & Flag

**Last Updated:** 2026-06-23
**Owner:** [Owner]
**Refresh Trigger:** Flag mechanism, audit-event schema, or `modules/agent/` layout changes

| Map | Value |
|---|---|
| Release | **R1 — Walking skeleton** |
| Epic | **E1 — Agent Core** (`skills/healthcentral-agent`) |
| Sprint | **S0** (stories S0-1…S0-4) |
| Binding skills | `healthcentral-agent`, `healthcentral-backend` |

## Objective
Stand up a provable foundation: a home for agent nodes, an `agent_enabled` flag that
keeps `main` behavior identical when OFF, and the audit-event schema wired through the
existing monitoring/audit stack — so governance exists from day one, before any node does.

## Exit criteria (= R1 exit, partial — the flag half)
- `modules/agent/` imports clean; `pytest` collects `tests/agent/`.
- `agent_enabled` defaults **OFF**; `/assistant/chat` byte-identical to legacy when off.
- One audit event persists through the existing `core.audit` / monitoring path.
- AGILE_PLAN + STANDUP + RETRO committed under `docs/agile/` (done in this pass).

## CONTRACTS

### API / routes
**No new routes.** `docs/api/endpoints.md` diff: **none for Phase 0** — the flag is read
inside the existing `POST /assistant/chat` handler. (First endpoints.md change is Phase 5.)

### Pydantic — terminal contract (defined now, used from Phase 1)
`modules/agent/schemas.py`:
```python
class Citation(BaseModel):       # source handle the draft/guard attaches per sentence
    source_type: Literal["document", "reference"]
    source_id: str
    locator: str | None = None   # page+span / reference handle

class AgentTerminal(BaseModel):
    terminal: Literal["answer", "abstain", "escalate"]
    text: str                    # for abstain/escalate this is a FIXED template (Phase 3)
    citations: list[Citation] = []
    run_id: str
```

### Audit-event schema (the governance deliverable — agent skill)
`modules/agent/audit.py`:
```python
class AgentAuditEvent(BaseModel):
    run_id: str
    node: Literal["plan", "act", "reflect", "draft", "guard", "terminal"]
    profile_id: str
    event_type: str              # e.g. "agent.plan"
    action: str                  # human-readable
    details: dict[str, Any] = {} # NO raw PHI prompts (handles only — PRD §7)
    step_index: int
```
Emission maps onto `core.audit.create_audit_log(db, event_type, action, profile_id,
entity_type="agent_node", entity_id=run_id, details=...)`. Read GETs are not
auto-audited (RECONCILIATION R-4) → emit explicitly.

### Data-shape contract
`agent_enabled: bool` lives in model settings (same store as tier/external-API toggles),
default `False`, profile-scoped. No schema migration needed if stored in existing settings
JSON; if a column is added, ship **both** master+profile migrations only where the column
lands (settings are master-side, so master only).

## CONTACTS (RACI)
| Role | Who |
|---|---|
| Responsible | [Owner] |
| Accountable | [Owner] |
| Consulted | [Safety-reviewer] (audit-event schema completeness) |
| Informed | [Reviewer] |

## Dependencies
None (first phase). Unblocks every later phase.

## Risk + mitigation
| Risk | Mitigation |
|---|---|
| Flag leaks behavior change when OFF | Flag-OFF regression test is a DoD gate (FR-1) |
| Audit schema misses a field needed later | Schema reviewed by [Safety-reviewer] now; additive-only changes after |
| Scaffold drags in heavy backend deps and won't collect | Agent modules stay stdlib+pydantic; integration via documented hooks |
