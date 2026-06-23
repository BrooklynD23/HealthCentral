# Phase 1 — First Tool, End-to-End

**Last Updated:** 2026-06-23
**Owner:** [Owner]
**Refresh Trigger:** Tool registry contract, `query_observations` shape, or node audit changes

| Map | Value |
|---|---|
| Release | **R1 — Walking skeleton** |
| Epic | **E1 — Agent Core** (`skills/healthcentral-agent`) |
| Sprint | **S1** (S1-1…S1-4) |
| Binding skills | `healthcentral-agent`, `healthcentral-backend` |

## Objective
One real read-only loop end-to-end behind the flag: a typed tool registry that rejects
malformed calls, a `query_observations` tool, and a plan→act→single-step-answer path that
returns a cited answer — each node emitting an audit event.

## Exit criteria
- Bad tool input → `ValidationError`, tool body never reached (FR-2).
- `query_observations` returns only `user_verified == True` rows for the current profile (FR-3).
- Flag ON → answer with ≥1 citation; flag OFF → legacy path (FR-4).
- plan/act/answer each emit an audit event (assertion test).

## CONTRACTS

### API / routes
No new routes; `endpoints.md` diff: **none**. The loop runs inside `/assistant/chat`.

### Pydantic — tool registry base + first tool
`modules/agent/tools/base.py`:
```python
class ToolInput(BaseModel):  ...           # base; each tool subclasses
class ToolOutput(BaseModel): ...
class ReadOnlyTool(Protocol):
    name: str
    InputModel: type[ToolInput]
    OutputModel: type[ToolOutput]
    def run(self, args: ToolInput, ctx: ToolContext) -> ToolOutput: ...
```
`modules/agent/tools/query_observations.py`:
```python
class QueryObservationsInput(ToolInput):
    analyte: str | None = None
    limit: int = Field(default=20, le=100)
class ObservationRow(BaseModel):
    observation_id: str; analyte: str; value: float; unit: str | None
    collected_at: datetime; verified: Literal[True]   # only verified rows ever returned
class QueryObservationsOutput(ToolOutput):
    rows: list[ObservationRow]
```
**Data-shape contract:** backed by `select(Observation).where(Observation.user_verified
== True)` scoped to the session profile (EXPLORATION B). No write path.

### Audit-event schema
Reuses `AgentAuditEvent` (Phase 0). New `event_type`s: `agent.plan`, `agent.act`
(records `tool_name` + validated args — no raw PHI), `agent.answer`.

## CONTACTS (RACI)
| Role | Who |
|---|---|
| Responsible | [Owner] |
| Accountable | [Owner] |
| Consulted | [Safety-reviewer] (read-only enforcement, verified-only filter) |
| Informed | [Reviewer] |

## Dependencies
Phase 0 (schemas, flag, audit hook).

## Risk + mitigation
| Risk | Mitigation |
|---|---|
| Tool executes on malformed args | Pydantic validation is the first guardrail layer; reject before `run()` |
| Unverified rows leak into answers | Output model pins `verified: Literal[True]`; query filters at DB |
| Citation missing on flag-ON answer | DoD: answer carries ≥1 source handle or it abstains |
