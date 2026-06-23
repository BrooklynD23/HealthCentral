# Phase 2 — The Loop Closes (multi-step reflect)

**Last Updated:** 2026-06-23
**Owner:** [Owner]
**Refresh Trigger:** Step-budget value, run-log shape, or the four new tool contracts change

| Map | Value |
|---|---|
| Release | **R1 — Walking skeleton** (R1 **ships** at end of S2) |
| Epic | **E1 — Agent Core** (`skills/healthcentral-agent`) |
| Sprint | **S2** (S2-1…S2-4) |
| Binding skills | `healthcentral-agent`, `healthcentral-backend`, `healthcentral-evals` |

## Objective
Close the loop: four more read-only tools, a reflect node with a hard ≤5-step budget that
terminates gracefully, a replayable per-step run log, and the eval-harness skeleton with
two seed cases (1 grounded, 1 abstain).

## Exit criteria (= **R1 exit**, AGILE_PLAN §5)
- One tool end-to-end, audited, **flag off = no change** — demonstrated by a flag-ON
  agent answering a real biomarker question with citations.
- `compute_trend`, `retrieve_chunks`, `lookup_reference`, `check_verification` each typed,
  read-only, profile-scoped, audited (FR-5).
- Step budget exceeded → graceful terminal `abstain` ("insufficient evidence within
  budget"), never crash/spin (FR-6).
- A failed run is reconstructable from its structured log (FR-7).
- 2 seed eval cases pass locally (1 grounded, 1 abstain).

## CONTRACTS

### API / routes
No new routes; `endpoints.md` diff: **none**.

### Pydantic — new read-only tools (`modules/agent/tools/`)
| Tool | Input (key fields) | Output (key fields) |
|---|---|---|
| `compute_trend` | `analyte: str`, `window_days: int \| None` | `points: list[TrendPoint]`, `direction: Literal["up","down","flat"]` |
| `retrieve_chunks` | `query: str`, `k: int<=10` | `chunks: list[ChunkRef]` (only chunks whose `Document.status=="verified"`) |
| `lookup_reference` | `analyte: str` | `reference: ReferenceRange \| None`, `handle: str` |
| `check_verification` | `observation_id: str` | `verified: bool`, `verified_at: datetime \| None` |

All subclass `ToolInput`/`ToolOutput`; all read-only; all profile-scoped (Phase 1 base).

### Data-shape — run log (replay, agent skill)
`modules/agent/state.py`:
```python
class RunStep(BaseModel):
    step_index: int
    node: Literal["plan","act","reflect","draft","guard","terminal"]
    payload: dict[str, Any]   # tool name+args, reflect decision, etc. (handles, no PHI)
    timestamp: datetime
class RunLog(BaseModel):
    run_id: str; profile_id: str
    steps: list[RunStep]
    terminal: AgentTerminal | None = None
```
**Contract:** replaying `steps` in order reproduces the same terminal. Budget = `len([s for
s in steps if s.node=="act"]) <= 5`; exceeding → terminal abstain.

### Audit-event schema
New `event_type`s: `agent.reflect` (records loop-or-proceed + remaining budget),
`agent.terminal` (records terminal kind). One event per node — a node without an event
is not done (agent skill).

## CONTACTS (RACI)
| Role | Who |
|---|---|
| Responsible | [Owner] |
| Accountable | [Owner] |
| Consulted | [Safety-reviewer] (budget-exhaustion = abstain, not partial answer) |
| Informed | [Reviewer] |

## Dependencies
Phase 1 (registry, first tool, node audit).

## Risk + mitigation
| Risk | Mitigation |
|---|---|
| Loop spins / latency balloons | Hard ≤5 budget → graceful abstain (FR-6); timing visible later (S5) |
| Non-deterministic replay | Run log captures validated tool args + decisions; seed config |
| Reflect proceeds without grounding | Reflect only proceeds when ≥1 grounded source exists, else loops/abstains |
