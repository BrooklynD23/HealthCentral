# Phase 2 — The Loop Closes (multi-step reflect)

**Last Updated:** 2026-06-24
**Owner:** [Owner]
**Refresh Trigger:** Step-budget value, run-log shape, or the four new tool contracts change

| Map | Value |
|---|---|
| Release | **R1 — Walking skeleton** — **SHIPPED 2026-06-24** (end of S2, commit fbb4fe7) |
| Epic | **E1 — Agent Core** (`skills/healthcentral-agent`) |
| Sprint | **S2** (S2-1…S2-4) — **delivered**, commit fbb4fe7; agent suite 30 passed / 12 skipped |
| Binding skills | `healthcentral-agent`, `healthcentral-backend`, `healthcentral-evals` |

## Objective
Close the loop: four more read-only tools, a reflect node with a hard ≤5-step budget that
terminates gracefully, a replayable per-step run log, and the eval-harness skeleton with
two seed cases (1 grounded, 1 abstain).

## Status: delivered (commit fbb4fe7) — R1 exit criteria met
- S2-1 — `compute_trend`, `check_verification`, `lookup_reference`, `retrieve_chunks`:
  **delivered**, all four typed/read-only/audited and registered.
- S2-2 — reflect node + hard `MAX_STEPS=5` budget: **delivered**;
  `graph.run_agent` is the real plan→act→reflect→(loop|draft)→guard(passthrough)→terminal
  loop; over-budget → graceful abstain (`ABSTAIN_TEMPLATE`).
- S2-3 — replayability: **delivered**; `graph.replay` reconstructs the terminal from
  `RunLog.steps` without re-calling any tool (proven by a test that makes `registry.get`
  raise during replay).
- S2-4 — eval harness + 2 seed cases: **delivered**; `tests/agent/eval_harness.py`
  materializes a golden case's vault into an in-memory profile DB and runs `run_agent`;
  `grounded-ldl-trend` and `abstain-unverified-ldl` both pass.

### AC deviations (see RECONCILIATION.md R-10, R-11)
- **`retrieve_chunks`** uses a deterministic text-match fallback over verified chunks
  rather than the RAG vector retriever — the real vector path needs an `Embedding` row
  per chunk from the ingest pipeline, which golden/unit fixtures don't generate. Falls
  back further to most-recent verified chunks if no text match. Still typed, read-only,
  audited, and scoped to `Document.status == "verified"`.
- **`lookup_reference`** reads the master-DB `BiomarkerKnowledge` table directly via
  `core.database.async_session_maker` (new `modules/agent/knowledge_lookup.py` adapter),
  not `ctx.db_session` — the contract's `ToolContext.db_session` is profile-scoped, but
  reference-range knowledge lives in the master DB. Degrades gracefully to handle-only
  (`reference=None`, stable handle still returned) when the master DB isn't reachable.

## Exit criteria (= **R1 exit**, AGILE_PLAN §5) — MET
- One tool end-to-end, audited, **flag off = no change** — demonstrated by a flag-ON
  agent answering a real biomarker question with citations. ✓
- `compute_trend`, `retrieve_chunks`, `lookup_reference`, `check_verification` each typed,
  read-only, profile-scoped, audited (FR-5). ✓ (see AC deviations above for
  `retrieve_chunks`/`lookup_reference` data-source notes — both remain read-only/audited)
- Step budget exceeded → graceful terminal `abstain` ("insufficient evidence within
  budget"), never crash/spin (FR-6). ✓
- A failed run is reconstructable from its structured log (FR-7). ✓
- 2 seed eval cases pass locally (1 grounded, 1 abstain). ✓ (harness exists and is green
  locally; **CI eval gate is S6/R3 scope**, not part of this R1 exit)

## CONTRACTS

### API / routes
No new routes; `endpoints.md` diff: **none**.

### Pydantic — new read-only tools (`modules/agent/tools/`)
| Tool | Input (key fields) | Output (key fields) |
|---|---|---|
| `compute_trend` | `analyte: str`, `window_days: int \| None` | `points: list[TrendPoint]` (each carries `observation_id` as its source handle), `direction: Literal["up","down","flat"]` |
| `retrieve_chunks` | `query: str`, `k: int<=10` | `chunks: list[ChunkRef]` (only chunks whose `Document.status=="verified"`) |
| `lookup_reference` | `analyte: str` | `reference: ReferenceRange \| None`, `handle: str` |
| `check_verification` | exactly one of `observation_id: str` **or** `analyte: str` | `status: Literal["absent","unverified","verified"]`, `verified: bool`, `verified_at`, `match_count` — **never the unverified value** |

> **Why `check_verification` takes an analyte too:** `query_observations` hides
> unverified rows (output pins `verified == True`), so an unverified value is
> otherwise indistinguishable from an absent one. The analyte mode returns
> status + counts only — never the value — giving the agent the discovery path it
> needs to abstain with "value not yet verified" (golden `abstain-unverified-ldl`)
> while preserving the don't-surface-unverified-values rule.
>
> **Why each `TrendPoint` carries `observation_id`:** trend sentences must map to
> a real source for groundedness. A manually entered observation has no document
> chunk, so the supporting observation handle travels with each point or the
> drafted sentence can't be cited.

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
