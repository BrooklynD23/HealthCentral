# Sprint 1 — First tool, end-to-end (06-29 → 07-05)

**Last Updated:** 2026-06-24
**Owner:** [Owner]
**Refresh Trigger:** S1 story scope/AC changes, or tool/registry contracts move
**Release:** R1 · **Epic:** E1 · **Phase:** [PHASE_1](../../prd/phases/PHASE_1_first_tool.md)
**Status:** Delivered — commit 0f09cd3. Suite: 27 passed, 15 skipped (was 24
passed, 18 skipped). Flag-off legacy path untouched.

## Goal
One real read-only loop end-to-end behind the flag.

## Stories
| ID | Story | Acceptance criteria | Pts | Status |
|---|---|---|---|---|
| S1-1 | Typed tool registry with Pydantic I/O | bad input → validation error, never reaches model | 3 | `[x]` delivered |
| S1-2 | `query_observations` tool (read-only) | returns only verified rows for current profile | 3 | `[x]` delivered |
| S1-3 | Plan→Act→single-step Answer behind flag | flag on → answer with ≥1 citation; flag off → legacy | 5 | `[x]` delivered *(see AC deviations)* |
| S1-4 | Audit event per node | assertion: plan/act/answer each emit | 2 | `[x]` delivered |

### AC deviations
- **S1-3:** the "plan" half of plan→act uses a deterministic, keyword-based
  analyte detector (`nodes/plan.py`), not an LLM call. The `planner` argument
  is an injectable seam for a future LLM-backed planner — out of scope for S1,
  no live model invoked. Additionally, `graph.py` wires a `guard` step after
  `draft`, but it is `_passthrough_guard` (no-op) — the real guard logic is
  S3 scope. The `reflect` node and its step-budget loop are S2-2 scope and are
  not called at all in S1; this sprint never loops past one step.

## DoR / DoD
- **DoR:** AC + touched-files (Phase 1 contracts + scaffolds) + proving tests in
  `test_s1_first_tool.py`.
- **DoD:** green CI; every new tool/node emits an audit event; flag-off regression
  green; `endpoints.md` unchanged (no new route this sprint); proof bundle passes.

## Test-coverage plan
- **Eval axes touched:** axis 1 (groundedness — answer must carry ≥1 source) and
  axis 2 (citation accuracy) begin here. **Guard/answer-path rule:** this sprint
  touches the answer path → include ≥1 **grounded** + 1 **abstain** + 1
  **advice-bait** golden case (already present in `tests/agent/golden/`).
- **Unit suites:** `test_s1_first_tool.py` — malformed-args rejection (FR-2) ✓ live;
  verified-only output model (FR-3) ✓ live; skip-marked: verified-rows query, flag-on
  citation, per-node audit. Coverage target for S1 code: **≥ 85%**.

## Code templates (committed scaffolds)
- `modules/agent/tools/base.py` (`ToolInput/Output`, `ReadOnlyTool`),
  `tools/registry.py` (`register`, `get`, `validate_args`),
  `tools/query_observations.py` (typed I/O, read-only `run`).
- `modules/agent/nodes/plan.py`, `nodes/act.py` (single tool call, never batch).

## Standup / retro pointers
- STANDUP daily; RETRO Sunday. Review: demo a flag-on agent answering a real
  biomarker question with a citation.
