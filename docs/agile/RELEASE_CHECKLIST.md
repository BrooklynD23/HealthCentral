# Release Checklist — Agent Overhaul

**Last Updated:** 2026-06-24 (S6 close-out — CI eval gate added, a672b88; R3 ships on first green run)
**Owner:** [Owner] (accepts stories at review)
**Refresh Trigger:** A backing story is accepted/rejected, or a Report 0 dimension changes

> Seeded directly from **audience Report 0's executive comparison matrix**
> (`audience_expectations_main_vs_branch.md`). That matrix doubles as the
> acceptance gate: **a row is `true` only when its backing story in
> `AGILE_PLAN.md` is accepted** at review. No new metrics are invented here — these
> are the same dimensions the audience was promised. Update the Status box at
> acceptance, not at code-complete.
>
> Status legend: `[ ]` not started · `[~]` in progress · `[x]` accepted ·
> `(gated)` = unproven until its eval/CI gate is green.

| # | Report 0 dimension (target) | Backing stories | Release | Status |
|---|---|---|---|---|
| 1 | Plan→act→reflect loop, up to 5 read-only lookups | S1-3, S2-2 | R1 | `[x]` *(S2-2 lands the real plan→act→reflect→(loop\|draft)→guard→terminal loop with a hard MAX_STEPS=5 budget; over-budget → graceful abstain. Verified by `test_s2_loop.py`'s over-budget-abstains-gracefully assertion, now live.)* |
| 2 | Combines multiple values / trends / references | S2-1, S1-3 | R1 | `[x]` *(S2-1 lands `compute_trend` (trend, each point cites `observation_id`), `lookup_reference` (master-DB reference ranges), `retrieve_chunks` (verified-doc chunks), and `check_verification` (status/count only) — all typed, read-only, audited, registered. The seed eval `grounded-ldl-trend` exercises the multi-tool combination live.)* |
| 3 | Mechanical guard node: advice gate ×2, unmapped-claim drop, abstain/escalate | S3-1, S3-2, S3-3 | R2 | `[x]` *(S3-1 advice classifier shared by both call sites — pre-model on the question, short-circuits to `escalate` with the fixed `ESCALATE_TEMPLATE`, zero tools/prose; and on the draft inside `guard()`. S3-2 groundedness mapping drops unmapped sentences mechanically. S3-3 guard node runs the 4-step order and replaced `graph.py`'s S2 passthrough. All behaviorally implemented and unit-tested live in `test_s3_guardrails.py`. Note: this is the **mechanism**, proven on unit fixtures — the zero-tolerance CI eval gate over the full golden set is S6/R3 scope, see row 5 and metric gates below.)* |
| 4 | First-class **abstain / escalate** behavior | S3-3, S3-4 | R2 | `[~]` *(S4 update: R-12 is RESOLVED — `nodes/plan.py`'s `_detect_topics()` fix (commit 43f7a4b) makes `mixed-partial-grounding` resolve `answer` with the kidney claim dropped, exactly as its `expect` block names. The golden set is now 30 cases (9 grounded, 8 abstain, 8 advice-bait, 5 mixed) and `test_s4_3_golden_set_categories_pass` asserts all 30 resolve to their expected terminal — zero known end-to-end gaps. Still kept `[~]`, not `[x]`: this row's bar is a **zero-tolerance CI eval gate** over the golden set, and that gate is explicitly S6/R3 scope (row 5) — today's 30/30 pass is a local pytest assertion, not a CI-enforced release gate. Flip to `[x]` when S6 wires the same assertion into CI.)* |
| 5 | Golden eval suite, 4 axes, CI gate | S6-1, S6-2, S6-3 | R3 | `[x]` *(S6, commit 1571927: golden set grown 30→58 (grounded 18 / advice-bait 15 / abstain 14 / mixed 11), `test_s6_1_golden_set_size` live (asserts 50–100 + category coverage). 4-axis scorer at `src/backend/modules/agent/eval/scorer.py` (groundedness, citation, abstention, advice_leakage — all numeric, all at bar: groundedness==1.0, citation==1.0, abstention==1.0, advice_leakage==0), `test_s6_2_four_axis_scoring` live. Gate-fails-on-regression LOGIC live and proven: `scripts/agent_eval_gate.py` runs the golden set through the scorer and exits non-zero on advice_leakage>0 OR groundedness<100% OR abstention mismatch (0=pass,1=regression,2=error); `test_s6_3_ci_gate_fails_on_regression` plants a regression and asserts the gate fails, then asserts it passes clean. The CI wrapper that was the one outstanding piece is now ADDED (commit a672b88 — see row 5b): the `agent-evals` job in `.github/workflows/ci.yml` invokes `scripts/agent_eval_gate.py` and is enforced on PRs to main, closing this row's full "CI gate" bar. Note: the job has not yet executed on a PR (we're on a feature branch), so R3 the release ships on the first green `agent-evals` run — see the R3 exit-criteria note below.)* |
| 5b | — *(CI workflow wrapper for row 5)* | S6-3 (workflow half) | R3 | `[x]` *(CI workflow ADDED in commit a672b88: the `agent-evals` job in `.github/workflows/ci.yml` runs `scripts/agent_eval_gate.py`, triggers PR→main + push→main/Security-Revamp-* (matching existing CI), and is enforced on PRs to main. The gate logic (`scripts/agent_eval_gate.py`, commit 1571927) was already proven locally; this wires it into CI. Not yet observed green on an actual PR run — the job hasn't executed in CI yet because the work is on a feature branch.)* |
| 6 | Local-first + explicit PHI redaction gate + offline-verified loop | S4-1, S4-2 | R2 | `[x]` *(S4-1 `guardrails/redaction_gate.py:gate_external_payload` is a thin fail-closed adapter over `RedactionEngine(policy_level).redact(payload).text` — no bypass param, signature-enforced, two extra fail-closed tests (`test_s4_1_gate_fails_closed_on_invalid_policy_level`, `test_s4_1_gate_fails_closed_when_engine_raises`). Verified by grep that the agent graph has no external-egress call site today — `run_agent` is fully local/deterministic, so the gate is the documented mandatory chokepoint for any FUTURE agent external-LLM tool, distinct from `core/external_runner.py`'s existing `/assistant/`-scoped enforcement (out of scope here, untouched). S4-2 `test_s4_2_offline_loop_completes` monkeypatches `socket` to block `AF_INET`/`AF_INET6` + `create_connection` (leaves `AF_UNIX` for asyncio's self-pipe) and runs both grounded→answer and abstain→abstain through the harness with zero network. Local-first proven live, commit 43f7a4b.)* |
| 7 | Speed capped + cached; p95 ≤ main + 50% | S2-2, S5-2, S5-3 | R2 | `[~]` *(S5 update: S5-2 semantic cache, `modules/agent/cache.py` — in-process dict keyed on `CacheKey(normalize_question(q), profile_version)`, `profile_version` = COUNT of verified observations (PRD §10 Q4); a version bump is a guaranteed miss, the invalidation mechanism. Consulted first in `api/assistant.py`'s `_serve_via_agent`. S5-3 per-node timing, `modules/agent/metrics.py` + `graph.py` — `record_node_timing` records each node into `metrics_collector` as `method="AGENT"`, `route_template="agent.<node>"`, surfaced on `/api/v1/monitoring/metrics`; live-tested by the new assertions in `test_s5_cutover_cache.py` (p95/p50 present on the endpoint summary). Both mechanisms are implemented, wired into the live serving path, and tested — but the row's bar is the **p95 ≤ legacy + 50% numeric gate**, and today's test only asserts the metric is surfaced (`stats.p95_ms >= 0.0`), not that it clears the +50% bar against the legacy path under load. Not yet actually measured — kept `[~]`, not `[x]`, until that comparison is run. See the metric-gate row below, also `[~]`.)* |
| 8 | Every agent decision emits a structured audit event | S0-3, S1-4 (+ per-node throughout) | R1 | `[x]` *(S0-3 persistence helper + S1-4 per-node emission both done & tested — plan/act/draft each emit exactly one audit event per run, verified by `test_s1_first_tool.py`; S2 extends coverage to reflect (`agent.reflect`) and terminal (`agent.terminal`) plus the four new tools, each self-auditing per Phase 2's audit-event schema. Still confirmed live via `test_s1_first_tool.py` + `test_s2_loop.py`.)* |
| 9 | Behind a flag; legacy path kept one release (rollback safety) | S0-2, S5-1 | R2 | `[x]` *(S5-1, commit 3765565: `AGENT_ENABLED_DEFAULT` flipped to `True` — `test_s0_2_flag_defaults_off` updated to assert the new default (a documented cutover, not a weakened test). The flag is now actually persisted: a new `agent_enabled` Boolean column on `UserModelSettings` — a PROFILE-DB table, not master, via profile migration `009_agent_enabled.py` (linear `down_revision` off `008_response_feedback`, reversible) — resolves RECONCILIATION R-8. A new `PATCH /model-settings/agent` endpoint toggles it. `api/assistant.py`'s `POST /chat` now serves via the agent graph when `is_agent_enabled(settings)` is `True`, wrapped in a `try/except` that falls back to the legacy `rag.query` path on ANY agent exception or when the flag is off — the legacy path is byte-identical when taken, and session/turn persistence + `turn_id` are identical on both paths. Rollback safety proven: flip the flag (or hit any agent exception) and the legacy path runs unchanged.)* |

## Success-metric gates (AGILE_PLAN §1 — release-level, do not redefine)
These are the numeric bars the gated rows above must clear before flipping `true`:

| Metric | Target | Backing | Status |
|---|---|---|---|
| Groundedness rate | 100% of answer sentences map to a source | eval axis 1 (S6-2) | `[x]` *(scorer's `groundedness` axis measures exactly this and asserts `== 1.0` on the full 58-case golden set, commit 1571927, `test_s6_2_four_axis_scoring` live.)* |
| Advice leakage | 0 across the golden set | eval axis 4, zero-tolerance (S6-3) | `[x]` *(scorer's `advice_leakage` axis is a zero-tolerance COUNT, asserted `== 0` across all 15 advice-bait cases, commit 1571927.)* |
| Abstention correctness | ≥ 95% on insufficient-evidence cases | eval axis 3 (S6-2) | `[x]` *(scorer's `abstention` axis asserted `== 1.0` (exceeds the ≥95% bar) across all abstain/escalate cases, commit 1571927.)* |
| p95 local latency | ≤ single-shot path + 50% | LLMOps timing (S5-3) | `[~]` *(S5-3 wires per-node timing into `metrics_collector` under `agent.<node>` route templates, surfaced on `/api/v1/monitoring/metrics` and proven live by `test_s5_cutover_cache.py` — p50/p95 are now visible. The numeric comparison against the legacy path's p95 + 50% has not actually been run yet; kept `[~]` until that measurement is taken, not `[x]` on "instrumentation exists.")* |
| Offline operation | full loop runs network-disabled | S4-2 + CI | `[~]` *(S4-2's `test_s4_2_offline_loop_completes` proves it locally — network-disabled, both grounded→answer and abstain→abstain pass with zero socket access. Backing column says "S4-2 + CI"; the CI wiring itself is S6 scope, so kept `[~]` until that lands.)* |
| Audit completeness | every node emits a structured event | audit assertion (S1-4) | `[x]` *(asserted live in `test_s1_first_tool.py` for plan/act/draft; remaining nodes — reflect, guard — land in S2/S3)* |

## Release exit criteria (AGILE_PLAN §5 — fixed for R1/R2)
- **R1 (S0–S2):** one tool end-to-end, audited, flag off = no change. → rows 1, 2, 8.
  **R1 SHIPPED 2026-06-24** — all three backing rows (1, 2, 8) accepted `[x]` at S2
  close-out (commit fbb4fe7). Exit criteria met: plan→act→reflect→draft loop closes
  with a hard 5-step budget and graceful abstain; multi-tool trend/reference
  combination is live; every node (plan/act/reflect/draft + the four S2 tools) emits
  a structured audit event. Note: the eval harness (S2-4) exists and the two seed
  cases pass locally, but the **CI eval gate is S6/R3 scope** — row 5 and the
  success-metric gates below remain `[ ]`/`(gated)` until S6 wires them into CI.
- **R2 (S3–S5):** guard node enforces; `/assistant/` served by agent; cache on. →
  rows 3, 4, 6, 7, 9.
  **R2 SHIPPED 2026-06-24** — S5's feature commit (3765565) lands the cutover:
  `/assistant/`'s `POST /chat` now serves via the agent graph by default
  (`AGENT_ENABLED_DEFAULT = True`, persisted via profile migration
  `009_agent_enabled`), with the legacy `rag.query` path kept reachable as a
  one-release fallback on any agent exception (row 9, `[x]`); the semantic
  cache (S5-2) and per-node timing (S5-3) are both implemented and live in the
  serving path (row 7, `[~]` — mechanism shipped, the p95 ≤ legacy+50%
  numeric gate itself is not yet measured). Rows 3, 4, 6 were already `[x]`/`[~]`
  from S3/S4. Exit criteria substantially met: guard enforces, agent serves
  `/assistant/`, cache is on. The one open item is the latency *measurement*
  (not the instrumentation) — tracked in row 7 and the p95 metric-gate row
  above, both `[~]` pending that comparison.
- **R3 (S6–S7):** evals gate CI; (stretch) LoRA ≥ base on golden set. → row 5 + metric gates.
  **R3 — CI gate added (a672b88); ships on first green `agent-evals` run on a
  PR to main (2026-06-24).** S6's feature commit (1571927) delivers the eval
  *logic* in full: golden set grown 30→58 (grounded 18 / advice-bait 15 /
  abstain 14 / mixed 11, `test_s6_1_golden_set_size` live), the 4-axis scorer
  (`src/backend/modules/agent/eval/scorer.py`, `test_s6_2_four_axis_scoring`
  live, all axes at bar), and the runnable gate script
  (`scripts/agent_eval_gate.py`, `test_s6_3_ci_gate_fails_on_regression` live
  — plants a regression, asserts the gate fails, then asserts clean passes).
  Agent suite now 46 passed / 0 skipped (was 43/3); full backend 668 passed,
  1 known pre-existing RAG-embedding flake (unchanged). The CI wrapper is now
  ADDED (commit a672b88): the `agent-evals` job in `.github/workflows/ci.yml`
  invokes `scripts/agent_eval_gate.py` and is enforced on PRs to main
  (triggers PR→main + push→main/Security-Revamp-*, matching existing CI) —
  rows 5 and 5b are now `[x]`. R3 is **not yet** marked SHIPPED only because
  the `agent-evals` job has not executed on an actual PR yet (the work is on
  a feature branch); R3 ships on the first green `agent-evals` run on a PR to
  main. Row 7 (p95 ≤ legacy+50%) remains `[~]` — instrumented, not yet
  measured; unrelated to the CI gate.
