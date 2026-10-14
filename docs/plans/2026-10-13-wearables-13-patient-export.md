# WEAR-13 — Patient Export of Wearable Rows — Implementation Plan

**Last Updated:** 2026-10-13
**Owner:** repository owner
**Status:** PROPOSED — not executed. Gated on owner decision D7. Recommended default is (b) "not in MVP": with that answer this plan stays unexecuted.
**Base measured:** `origin/main` @ 8234990
**Refresh trigger:** owner answers D7; WEAR-09 merges (shared `api/export.py`); any edit to `api/export.py` or `modules/export.py`; WEAR-02 changes the table contract.
**Program:** [00-program](2026-10-13-wearables-00-program.md) (A3, D7, milestone M6)
**Depends on:** WEAR-02 (tables, static guard), WEAR-09 (also edits `api/export.py`; serialise after it).
**Owner decisions it depends on:** D7. This plan builds option (a) only: add a block to `GET /export/json`. It does not build a new route.
**Size target:** ~150 lines of non-test diff, one L1 PR.

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:test-driven-development, with superpowers:subagent-driven-development. Domain skill: `asclexis-backend`.

## 1. Scope

**Does:**
- `GET /export/json?include_wearables=true` returns an object with the existing observations and a `wearable_daily_metrics` block (`schema_version: "wdm-1"`).
- The block is the profile's own imports, daily rows and review state, full fidelity.
- Flag off + `include_wearables=true` → 400.

**Does NOT:**
- Add a route. Touch `GET /export/csv`, FHIR export, visit prep or the doctor summary.
- Change the default `GET /export/json` response (still a bare JSON list).
- Edit `_fetch_observations`, `modules/redaction.py`, or `ExportPage.tsx`.
- Make any other export exempt from redaction. If the owner wants a separate wearable export route, it must pass `modules/redaction.py` at `strict` (CLAUDE.md "Redaction before anything leaves": only `/export/csv` and `/export/json` are exempt, owner decision D3). That is a new owner decision, not this plan.

## 2. Evidence

| Fact | path:line @8234990 |
|---|---|
| `GET /export/csv` route (not changed) | `src/backend/api/export.py:907` |
| `GET /export/json` route (the only one changed) | `src/backend/api/export.py:963-964` |
| Handler body: fetch → `ExportModule().export_json` → `audit_and_commit(... log_export_event, export_type="json", details={"observation_count": ...})` | `src/backend/api/export.py:963-1015` (read in full) |
| `_fetch_observations` (stays untouched, guarded) | `src/backend/api/export.py:131` |
| Auth + profile DB imports already in the file | `src/backend/api/export.py:25-26` |
| `ExportModule.export_json` returns `json.dumps(list, indent=2)`: the default response is a bare array | `src/backend/modules/export.py:267-288` |
| Existing tests parse that list | `tests/test_export_api.py:144-149`, `:163-164`, `:583-584` |
| `log_export_event` moves `export_type` into `details` | `src/backend/core/audit.py:452-471` |
| `"count"` is an allowed numeric detail key | `core/audit.py:95` |
| `route_client` | `src/backend/tests/support/routes.py:26-33` |
| Profile DB override on a `route_client` client | `tests/test_audit_order.py:163-173` |
| Wearable models, static import guard, `wearables_enabled` | INFERRED from WEAR-01/02/09 plans; none exists on this tree. |

Finding: the response of `/export/json` is a bare list today. Adding a top-level key would break every consumer. This plan therefore makes the object form opt-in with a query parameter.

## 3. Files to touch

| Path | new/edit | Why | ~Lines |
|---|---|---|---|
| `src/backend/api/export.py` | edit | `include_wearables` query param on `/json`; `_fetch_wearable_block()` helper placed after `_fetch_observations` | +70 |
| `tests/test_wearables_export.py` | new | tests below | +190 |
| `tests/test_wearables_import_guard.py` (WEAR-02's guard) | edit | allow `models.wearable` in `api/export.py` (already allowed by WEAR-09 for the packet path); add an AST check that `_fetch_observations` has no wearable names | +20 |

The DB helper lives in `api/export.py` and not in `modules/wearables/`, because the parsers there stay stdlib-only (program A8).

## 4. Ask-first files touched

None. `modules/redaction.py` is not touched. The export stays within the D3-exempt route.

## 5. Data contract

Default call (no parameter): response unchanged, a JSON list of observations.

With `include_wearables=true` and `wearables_enabled`:

```json
{"observations": [ ... same list as today ... ],
 "wearable_daily_metrics": {
   "schema_version": "wdm-1",
   "imports": [{"id": "...", "source_vendor": "apple", "filename": "...", "imported_at": "...",
                "content_hash": "...", "records_read": 0, "records_skipped": 0,
                "skipped_reasons": {"reason": 0}, "days_covered": 0,
                "first_local_date": "YYYY-MM-DD", "last_local_date": "YYYY-MM-DD"}],
   "daily_metrics": [{"import_id": "...", "metric": "step_count", "local_date": "YYYY-MM-DD",
                      "value": 0.0, "unit": "count", "utc_offset_minutes": 0, "tz_changed": false,
                      "n_records": 0, "device_class": "apple_watch", "source_name": "...",
                      "duplicate_sources": 0}],
   "reviews": [{"import_id": "...", "metric": "step_count",
                "patient_reviewed_at": null, "include_in_packet": false}]}}
```

Rules:
- Full fidelity: every row of this profile, reviewed or not, with its review state. This is the patient's own data leaving to the patient. `filename` and `source_name` are included here and nowhere that reaches a third party.
- `from_date` / `to_date` (existing query params) filter `local_date` by the date part. `analytes` filters observations only.
- Rows are read with `profile_id == session.profile_id` through `ProfileDbSession`.
- Audit: the existing `log_export_event` with `export_type="json"`; `details["count"]` = wearable rows. No new audit key.

## 6. TDD test list

IDs `HC-WRB-13NN`, file `tests/test_wearables_export.py`, through `route_client(api.export.router, "/export", ...)` with a seeded profile DB override. Program-level research IDs: none cover this (research roadmap excludes patient export); D7 is the only source.

| ID | Assertion | RED reason |
|---|---|---|
| HC-WRB-1301 | no parameter, flag on: body parses to a `list` equal to today's output for the same seeded observations (characterization) | green before; must stay green |
| HC-WRB-1302 | `include_wearables=true`, flag on: body is an object; `wearable_daily_metrics.schema_version == "wdm-1"`; `observations` equals the 1301 list | parameter ignored |
| HC-WRB-1303 | block `daily_metrics` equal seeded `(import_id, metric, local_date, value, unit)` tuples exactly, none missing, none extra | no block |
| HC-WRB-1304 | seed rows for A and B; export as B → B's values only; A's seeded value and import id strings are absent from the body text | no filter |
| HC-WRB-1305 | flag off + `include_wearables=true` → 400, body has no `wearable_daily_metrics`; flag off without parameter → unchanged list | no flag check |
| HC-WRB-1306 | an unreviewed import's rows appear with `patient_reviewed_at: null`, `include_in_packet: false` | review state omitted |
| HC-WRB-1307 | `from_date`/`to_date` window returns only rows inside it | filter missing |
| HC-WRB-1308 | audit row (real master DB): `export_type == "json"`, `count` == wearable row count, no `filename`/`source_name` in `details_json` | no count |
| HC-WRB-1309 | `GET /export/csv?include_wearables=true` → body byte-identical to the call without the parameter, contains no wearable string | csv unchanged check |
| HC-WRB-1310 | `[r.path for r in api.export.router.routes]` has no path containing `wearable` (no new route) | structural guard |
| HC-WRB-1311 | AST of `_fetch_observations` references no `Wearable*` name; `api/observations.py`, `modules/rag.py`, `modules/timeline.py` still import no `models.wearable` (A3) | guard not extended |
| HC-WRB-1312 | `TestClient(main.app)`, flag on, auth + profile DB overridden: `GET /api/v1/export/json?include_wearables=true` → 200 object (real mount, recurring-failures #10) | not reachable |

Collected = start + 12 (1301 is new but green before the change; it still adds to the count). Update CLAUDE.md and AGENT.md count slots in the same commit (SLOT-RULE).

## 7. Tasks

### Task 0 — gates
- [ ] D7 answered **(a)** in the owner-decisions file. If (b) or unanswered: STOP; this plan is not licensed.
- [ ] `git merge-base --is-ancestor <WEAR-02 commit> origin/main` and `<WEAR-09 commit> origin/main`. STOP if either fails (shared file `api/export.py`).
- [ ] Plan file present. Re-read `api/export.py:963-1015` on the new base; the line numbers above may have moved after WEAR-09.
- [ ] Confirm the owner accepts the opt-in query parameter and object envelope (Question 1 in the report). If the owner wants the object always, add a deprecation step for list consumers first; that is a larger plan.

### Task 1 — RED
- [ ] Write `tests/test_wearables_export.py` and the guard additions.
- [ ] Run: `cd src/backend && HF_HUB_OFFLINE=1 python -m pytest tests/test_wearables_export.py tests/test_wearables_import_guard.py -p no:cacheprovider -q`
- [ ] Paste output. Expected: 11 failures; 1301 passes (characterization).

### Task 2 — GREEN
- [ ] Add `include_wearables: bool = Query(False)` to `export_json`. When false: path unchanged. When true: flag off → `HTTPException(400)`; else `_fetch_wearable_block(profile_db, profile_id, from_date, to_date)` and return `json.dumps({"observations": <list>, "wearable_daily_metrics": block}, indent=2)`. Reuse the module's own list (call `export_json` and `json.loads` it, or restructure minimally; no duplicate datetime handling).
- [ ] Pass `details={"observation_count": n, "count": wearable_rows}` to the existing `audit_and_commit`.
- [ ] Update the WEAR-02 guard allow-list (the file name is INFERRED; re-read in Task 0).

### Task 3 — verify
- [ ] Targeted run, then the full suite: `cd src/backend && flock /tmp/claude-1000/hc-pytest.lock env HF_HUB_OFFLINE=1 python -m pytest -p no:cacheprovider -q`. Collected = start + 12.
- [ ] Existing export tests unchanged and green: `python -m pytest tests/test_export_api.py -p no:cacheprovider -q`. `git diff --stat` on that file empty.
- [ ] Count slots, `python3 scripts/docs_lint.py --link-graph`, security-reviewer on the diff.

## 8. Mutation / break checks (temporary, never committed)

1. Remove the `profile_id` filter in `_fetch_wearable_block` → HC-WRB-1304 red.
2. Make the response an object even without the parameter → HC-WRB-1301 red.
3. Delete the flag check → HC-WRB-1305 red.
4. Reference a wearable model inside `_fetch_observations` → HC-WRB-1311 red. After each: revert; `git diff` empty.

## 9. Acceptance criteria

- RED then GREEN output pasted; HC-WRB-1301 green in both.
- `tests/test_export_api.py` passes untouched.
- Full-suite output with collected = start + 12.
- `git diff --stat origin/main...HEAD`: only the section 3 files; no `routes` change in `api/__init__.py`.

## 10. Rollback

Revert the PR. The default response never changed, so no consumer is affected. No migration.

## 11. What these tests cannot see (recurring-failures.md)

- **#1:** isolation (1304) shares one test DB between profiles; it proves the filter, not file separation. It asserts on body text, not names.
- **#9:** "no other export includes wearable data" is guarded for `/csv`, the router paths and `_fetch_observations`. A future route that reads the tables is caught only by the WEAR-02 import guard, which checks imports, not queries.
- **#10:** only `/json` is exercised on `main.app`.
- Whether any downstream tool can read the `wdm-1` block is not tested (no consumer exists). Large profiles (3 metrics x several years x many imports) are built in memory; no size test is planned.
- No UI exists for the parameter. A patient reaches it only by URL until a follow-up adds a checkbox.

## 12. Owner / model-machine items

OW-W5: answer D7. If (a), the owner also confirms the opt-in parameter. None else.
