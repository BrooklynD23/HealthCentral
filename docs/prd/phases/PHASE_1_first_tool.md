# Phase 1 — First Tool, End-to-End

**Last Updated:** 2026-06-24
**Owner:** [Owner]
**Refresh Trigger:** Tool registry contract, `query_observations` shape, or node audit changes
**Status:** S1-1…S1-4 delivered (commit 0f09cd3; suite 27 passed, 15 skipped). See AC deviations below.

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
- [x] Bad tool input → `ValidationError`, tool body never reached (FR-2). —
  `tools/registry.py` `validate_args` runs raw args through the tool's
  `InputModel` before `run()` is ever called.
- [x] `query_observations` returns only `user_verified == True` rows for the
  current profile (FR-3). — DB filter + `ObservationRow.verified: Literal[True]`
  pinned at the output-model layer.
- [x] Flag ON → answer with ≥1 citation; flag OFF → legacy path (FR-4). —
  `graph.run_agent` single-step plan→act→draft path; abstains via
  `ABSTAIN_TEMPLATE` when no verified data exists.
- [x] plan/act/answer each emit an audit event (assertion test). — one
  `agent.plan` / `agent.act` / `agent.answer` event per run, asserted live in
  `test_s1_first_tool.py`.

### AC deviations from the original contract
- **Planner is deterministic, not LLM-backed.** `nodes/plan.py` uses
  keyword-based analyte detection to decide `call_tool(query_observations)` vs
  `draft`. The `planner` param is an injectable seam for a future LLM-backed
  planner — no live model is called in S1. This satisfies S1-3's AC (flag-on →
  cited answer) without taking on prompt-engineering risk this sprint.
- **Guard node is a passthrough; reflect node is not wired.** `graph.py` wires
  `plan→act→draft→guard` for the single-step case, but `guard` is currently
  `_passthrough_guard` — a trivial seam S3 will replace with the real
  advice/groundedness/confidence gates (no guard logic implemented here). The
  `reflect` node (loop + step budget, S2-2) is intentionally not called yet —
  S1 never loops; multi-step plan→act→reflect is deferred to S2.

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
