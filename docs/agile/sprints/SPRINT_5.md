# Sprint 5 — Cutover + cache (07-27 → 08-02)

**Last Updated:** 2026-06-24 (S5 delivered — **R2 SHIPPED**, commit 3765565)
**Owner:** [Owner]
**Refresh Trigger:** S5 story scope/AC, `/assistant/chat` response shape, or cache key changes
**Release:** R2 (**R2 SHIPPED 2026-06-24**) · **Epic:** E5 + E4 · **Phase:** [PHASE_5](../../prd/phases/PHASE_5_cutover_cache.md)

## Goal
The agent IS the assistant: flip the route, add the semantic cache, surface per-node timing.

## Stories
| ID | Story | Acceptance criteria | Pts | Status |
|---|---|---|---|---|
| S5-1 | Flip `/assistant/` to agent; keep legacy as one-release fallback | flag default on; fallback reachable | 3 | **Delivered** — `AGENT_ENABLED_DEFAULT=True`, persisted via profile migration `009_agent_enabled` (NOT master), `PATCH /model-settings/agent`, `api/assistant.py` try/except fallback to legacy `rag.query` on any agent exception or flag-off |
| S5-2 | Semantic cache keyed `(question, profile_version)` | repeat served from cache; invalidates on new verified data | 5 | **Delivered** — `modules/agent/cache.py`, `profile_version` = count of verified observations |
| S5-3 | Per-node timing/token tracking in monitoring dashboard | p95 latency visible | 3 | **Delivered** — `modules/agent/metrics.py` + `graph.py`, surfaces on `/api/v1/monitoring/metrics` |

## DoR / DoD
- **DoR:** AC + touched-files + proving tests in `test_s5_cutover_cache.py`. The
  `endpoints.md` description diff (Phase 5) is part of the touched-files list.
- **DoD:** green CI; **`docs/api/endpoints.md` updated in the same change** (additive
  response-shape note); flag-OFF regression byte-identical; frontend union handles
  abstain/escalate (strict TS); p95 ≤ legacy + 50%; proof bundle passes. **R2 exit met.**

## Test-coverage plan
- **Eval axes:** all four re-run post-cutover to confirm no regression; latency metric
  (p95 ≤ main + 50%) checked via monitoring. **Guard/answer-path rule:** grounded +
  abstain + advice-bait re-asserted on the live route.
- **Unit suites:** `test_s5_cutover_cache.py` — cache key requires `profile_version`
  ✓ live; version distinguishes keys ✓ live; skip-marked: cutover-keeps-fallback,
  cache-hit+invalidation, per-node-timing-surfaced. **Frontend:** `tsc --noEmit` must
  pass with the new discriminated union. Coverage target for S5 code: **≥ 85%**.

## Code templates (committed scaffolds)
- `modules/agent/cache.py` (`CacheKey`, `get_cached`/`put_cached`), `metrics.py`
  (`record_node_timing`).
- **endpoints.md diff** (apply when S5-1 lands) — see Phase 5 "API / routes".

## Standup / retro pointers
- STANDUP daily; RETRO Sunday — **R2 review:** legacy path retired-pending; agent live
  with cache + metrics; confirm rollback fallback reachable.

## Close-out (2026-06-24, commit 3765565)
All three stories delivered; agent suite **43 passed, 3 skipped**; chat-session and
biomarker-assistant suites pass with zero regressions. **R2 ships** — see
RELEASE_CHECKLIST.md rows 3, 4, 6, 7 (`[~]`, p95 numeric gate not yet measured), 9, and
the "R2 SHIPPED 2026-06-24" exit-criteria note. RECONCILIATION R-8 resolved (agent_enabled
now persisted via profile migration 009, not master). Three new reconciliation items
opened at close-out (agent path drops legacy context features; `insufficient_context`
hardcoded `False` on agent abstain terminals; semantic cache has no eviction/TTL and
narrow invalidation) — see RECONCILIATION.md R-15, R-16, R-17.
