# Phase 5 — Cutover + Cache

**Last Updated:** 2026-06-24 (S5 delivered — **R2 SHIPPED**, commit 3765565)
**Owner:** [Owner]
**Refresh Trigger:** `/assistant/chat` response shape, cache key/invalidation, or fallback policy change

| Map | Value |
|---|---|
| Release | **R2 — Governed & live** — **SHIPPED 2026-06-24** (commit 3765565) |
| Epic | **E5 — Cutover & Fallback** + **E4 — LLMOps** (`skills/healthcentral-backend`) |
| Sprint | **S5** (S5-1…S5-3) — **delivered** |
| Binding skills | `healthcentral-backend`, `healthcentral-agent` |

## Objective
Make the agent the assistant: flip `/assistant/chat` to the agent (legacy kept one
release), add a semantic cache keyed `(question, profile_version)` that invalidates on new
verified data, and surface per-node timing/tokens in the monitoring dashboard.

## Delivered (S5, commit 3765565)
- **S5-1 cutover:** `AGENT_ENABLED_DEFAULT` flipped to `True` (`test_s0_2_flag_defaults_off`
  updated to expect `True` — a documented cutover, not a weakening). Persisted via a new
  `agent_enabled` Boolean column on `UserModelSettings` — note this is a **PROFILE-DB**
  table, NOT master, so it ships as profile migration `009_agent_enabled.py` (linear
  `down_revision` off `008_response_feedback`, reversible) — resolves RECONCILIATION R-8.
  New `PATCH /model-settings/agent` endpoint toggles it. `api/assistant.py`'s `POST /chat`
  now serves via the agent graph when `is_agent_enabled(settings)` is `True`, with a
  `try/except` that falls back to the legacy `rag.query` path on ANY agent exception or
  when the flag is off; legacy path is byte-identical when taken; session/turn persistence
  + `turn_id` identical on both paths.
- **S5-2 semantic cache** (`modules/agent/cache.py`): in-process dict keyed on
  `CacheKey(normalize_question(q), profile_version)`; `profile_version` = count of verified
  observations (PRD §10 Q4); a version bump is a different key, which is a guaranteed miss
  (the invalidation). Consulted in the agent serving path (`_serve_via_agent`).
- **S5-3 per-node metrics** (`modules/agent/metrics.py` + `graph.py`): `record_node_timing`
  → `metrics_collector.record_request(method="AGENT", route_template=f"agent.<node>")`;
  each node timed; surfaces on `/api/v1/monitoring/metrics`.

## Exit criteria (= **R2 exit**, AGILE_PLAN §5) — status
- Guard node enforces; `/assistant/chat` served by agent; cache on. — **met.**
- Flag **default ON**; legacy fallback reachable for one release (FR-14). — **met.**
- Repeat question served from cache; invalidates on new verified data (FR-15). — **met.**
- p95 latency visible in `/monitoring/metrics`; p95 ≤ legacy + 50% (FR-16, metric §4). —
  **partially met:** p95/p50 are now visible on the endpoint summary (live-tested); the
  numeric ≤ legacy+50% comparison itself has not yet been measured — tracked as the one
  open item in RELEASE_CHECKLIST row 7 / the p95 metric-gate row (both `[~]`).

## CONTRACTS

### API / routes — **the one phase with an `endpoints.md` change**
The route path is **unchanged**; the **response body** for `POST /assistant/chat` gains
terminal variants when the flag is ON. `docs/api/endpoints.md` diff:

```diff
 ## Assistant
 | Method | Path | Auth | Description |
 |--------|------|------|-------------|
-| POST | `/assistant/chat` | Yes | Chat with the grounded assistant |
+| POST | `/assistant/chat` | Yes | Chat with the grounded assistant. When `agent_enabled` is ON, returns a terminal-typed body (`answer \| abstain \| escalate`); when OFF, the legacy single-shot body is returned unchanged. |
```
No new path, so the table keeps its row — the description records the additive contract.

### Pydantic — additive discriminated union (frontend contract, RECONCILIATION R-6)
```python
class AssistantResponse(BaseModel):
    terminal: Literal["answer", "abstain", "escalate"]   # NEW discriminant
    text: str
    citations: list[Citation] = []
    # legacy fields preserved when flag OFF: segments, full_response, verification
```
**Flag-OFF guarantee:** byte-identical legacy body. The frontend
(`services/assistant.ts`, `pages/ExplainAssistant.tsx`) adds abstain/escalate render
branches; strict TS forces handling all three.

### Data-shape — semantic cache (backend skill)
```python
cache_key = (normalized_question, profile_version)   # invalidates when profile_version bumps
```
`profile_version` increments on any observation verify (a stale cached explanation of
changed data is a correctness bug — never cache without this).

### Per-node metrics
Each node records into `MetricsCollector` keyed `agent.<node>`; `/monitoring/metrics`
exposes p50/p95/p99. No new route (dashboard already exists).

### Audit-event schema
`agent.terminal` records `served_from_cache: bool`. Cutover itself logs a config-change
audit event (flag default flip).

## CONTACTS (RACI)
| Role | Who |
|---|---|
| Responsible | [Owner] |
| Accountable | [Owner] |
| Consulted | [Reviewer] (frontend union), [Safety-reviewer] (guard stays in path on cutover) |
| Informed | [Reviewer] |

## Dependencies
Phases 3 + 4 (guard + offline-safe path must be live before the agent serves real users).

## Risk + mitigation
| Risk | Mitigation |
|---|---|
| Terminal-shape change breaks frontend | Additive union + flag-OFF regression; strict TS catches unhandled branches |
| Stale cached explanation after new verified data | Key includes `profile_version`; invalidate on verify |
| Latency regression on cutover | Per-node timing visible; p95 ≤ legacy+50% gate; cache on |
| No rollback if agent misbehaves | Legacy path kept reachable one full release (E5) |
