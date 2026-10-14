# WEAR-07 — Review Queue and Delete Import (Backend) — Implementation Plan

**Last Updated:** 2026-10-13
**Owner:** repository owner
**Status:** PROPOSED — not executed (code waits for program M0 and WEAR-06 merged)
**Base measured:** `origin/main` @ 8234990
**Refresh trigger:** WEAR-06 merges (re-read the review-stub rule and the gated router); WEAR-02 changes the audit vocabulary; owner answers D3.
**Program:** [00-program](2026-10-13-wearables-00-program.md) (A2, A4, A5, A5b, A12)
**Depends on:** WEAR-06 (imports + review stubs exist), WEAR-05 (`describe()`), WEAR-02 (models, audit vocabulary).
**Owner decisions it builds:** D3 (minimum 7 days, display flag only).
**Size target:** ~330 lines of non-test diff, one L1 PR.

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:test-driven-development, with superpowers:subagent-driven-development. Domain skill: `asclexis-backend`.

## 1. Scope

**Does:**
- `GET /wearables/imports` — this profile's imports, newest first, with review state per metric.
- `GET /wearables/imports/{id}/summary` — per metric: days with data, median / p25 / p75 / min / max, device classes, days with duplicate sources, days with a timezone change, skipped counts, review state, `below_minimum_days`.
- `PUT /wearables/imports/{id}/review` — set reviewed / include-in-packet per metric.
- `DELETE /wearables/imports/{id}` — delete metrics, reviews, then the import, in one transaction.
- Audit all four (counts only).

**Does NOT:**
- Choose "current" values across imports (A5b selection is WEAR-08's read path). The summary describes one import's own rows.
- Return a mean, an average, a normal range or any good/bad flag (research F1). Return `source_name` (never leaves the app, A7).
- Add columns, a migration, or audit vocabulary beyond WEAR-02's reserved set. Touch the frontend (WEAR-07b).

## 2. Evidence

| Fact | path:line @8234990 |
|---|---|
| `ProfileDbSession` / `get_profile_db_session` | `src/backend/core/auth.py:341`, `:315` |
| `audit_and_commit` (fail-closed) | `src/backend/core/audit.py:474` |
| `ALLOWED_ACTIONS` (needs wearable view/review/delete) | `core/audit.py:36` |
| `STRING_DETAIL_KEYS` lacks `import_id`, `vendor`, `metric` | `core/audit.py:69-75` |
| `"count"` is an allowed numeric detail key (used for delete counts) | `core/audit.py:95` |
| Scrubber drops anything not allowlisted | `core/audit.py:118-142` |
| `log_export_event` shows the log-function shape to copy | `core/audit.py:452-471` |
| `route_client` signature | `src/backend/tests/support/routes.py:26-33` |
| Profile DB override on a `route_client` client | `tests/test_audit_order.py:163-173` |
| Audit PHI test to mirror | `tests/test_audit_phi_minimization.py:58-62` |
| Export router is mounted statically (same pattern for wearables) | `src/backend/api/__init__.py:55` |
| FK cascade not enforced: delete children explicitly | program A2; amendment 3 (`api/profiles.py:939-942` per program) |
| `api/wearables.py`, `models/wearable.py`, `describe()`, `log_wearable_event`, review-stub rule | INFERRED from WEAR-01/02/05/06 plans; absent on this tree. Task 0 re-reads. |

## 3. Files to touch

| Path | new/edit | Why | ~Lines |
|---|---|---|---|
| `src/backend/api/wearables.py` | edit | four routes + Pydantic bodies | +190 |
| `src/backend/modules/wearables/summary.py` | new | pure `summarize_metric(rows) -> dict` using `describe()` | +50 |
| `src/backend/core/config.py` | edit | `wearables_min_days: int = 7` (D3) | +1 |
| `tests/test_wearables_review.py` | new | tests below | +330 |

## 4. Ask-first files touched

None. `core/audit.py` is not edited if WEAR-02 reserved the vocabulary (Task 0 checks); if a gap appears, stop and add it to WEAR-02, not here.

## 5. Data contract

Request body for `PUT .../review` (flat map keyed by metric):

```json
{"resting_heart_rate": {"reviewed": true, "include_in_packet": false},
 "step_count": {"reviewed": true, "include_in_packet": true}}
```

Rules:
- Keys are the closed metric enum; each must have rows in this import, else 422.
- `include_in_packet` true requires `reviewed` true, else 422 and no row changes.
- `reviewed` true on a stub with `patient_reviewed_at` NULL sets it to `core.time.utcnow()` (`core/time.py:9`). Already reviewed: keep the first timestamp. `reviewed` false: clears the timestamp and forces `include_in_packet` False.
- A missing review stub is treated as unreviewed and created on write.

Summary per metric: `{metric, days_with_data, median, p25, p75, min, max, unit, device_classes[], days_with_duplicate_sources, days_with_tz_change, below_minimum_days, reviewed, include_in_packet, patient_reviewed_at}`. Import-level: `{import_id, first_local_date, last_local_date, records_read, records_skipped, skipped: {reason: count}}`. No `mean`, no `average`, no `source_name`.

`below_minimum_days` = `days_with_data < settings.wearables_min_days` (7). It is a display flag only; nothing is hidden here.

Delete: `204`. Order: reviews → metrics → import (explicit; `PRAGMA foreign_keys` is off). Audit `count` = metric rows deleted.

Audit: `view` events for list and summary (the reserved "metrics view" action), `review`, `delete`. `details` ⊆ `import_id, vendor, metric, metrics_reviewed, metrics_included, count, days_covered`.

## 6. TDD test list

IDs `HC-WRB-7NN`, file `tests/test_wearables_review.py`, all through `route_client(api.wearables.router, "/wearables", ...)` with a seeded profile DB session. Covers research HC-WRB-008, 014, F8, F9. "Other profile" tests seed rows under `profile-a` and call as `profile-b` on the same session: this proves the `profile_id` filter in the query (the real DBs are separate files).

| ID | Assertion | RED reason |
|---|---|---|
| HC-WRB-701 | flag off → list, summary, review, delete all 404 | routes absent |
| HC-WRB-702 | A has 2 imports, B has 1; list as B returns exactly B's id (compare returned ids to seeded ids) | route absent |
| HC-WRB-703 | seeded values for one metric → `median`, `p25`, `p75`, `min`, `max`, `days_with_data` equal hand-computed numbers; response JSON has no key `mean` or `average` (F1) | route absent |
| HC-WRB-704 | `device_classes` ⊆ closed enum; the string of a seeded `source_name` ("Jane's Apple Watch") is absent from the summary body | route absent |
| HC-WRB-705 | 6 days → `below_minimum_days` true; 7 days → false (boundary) | no flag |
| HC-WRB-706 | summary of another profile's id → 404, body holds no value or date | route absent |
| HC-WRB-707 | PUT reviewed+include → row has `patient_reviewed_at` not NULL and `include_in_packet` True (read back from DB) | route absent |
| HC-WRB-708 | PUT include without reviewed → 422; DB row unchanged | no rule |
| HC-WRB-709 | PUT reviewed false after reviewed → timestamp NULL and include False | no rule |
| HC-WRB-710 | PUT unknown metric key → 422; metric with no rows in this import → 422; DB unchanged | no validation |
| HC-WRB-711 | PUT for another profile's import → 404; its review rows unchanged | route absent |
| HC-WRB-712 | DELETE own import → 204; direct queries: zero metric rows, zero review rows, zero import row; a second import's rows all still present | no explicit deletes |
| HC-WRB-713 | DELETE another profile's import → 404; all rows intact | route absent |
| HC-WRB-714 | DELETE then POST the same bytes (WEAR-06 route, same router) → 201 not 409 (hash row gone) | no delete |
| HC-WRB-715 | audit rows (real master DB) for view, review, delete: keys ⊆ allowlist; no filename, `source_name` or value in `details_json` | no audit |
| HC-WRB-716 | audit commit raises on PUT → 500 and review row unchanged; same for DELETE → rows still present | wrong order |
| HC-WRB-717 | `TestClient(main.app)`, flag on, auth + profile DB overridden: `GET /api/v1/wearables/imports` → 200 (real mount, program A13; recurring-failures #10) | not mounted |

Collected = start + 17. Update CLAUDE.md and AGENT.md count slots in the same commit (SLOT-RULE).

## 7. Tasks

### Task 0 — gates
- [ ] `git merge-base --is-ancestor <WEAR-06 merge commit> origin/main`. STOP if not.
- [ ] Plan file present. D3 default (7) is the only decision used; no gate beyond WEAR-06.
- [ ] Re-read WEAR-06's merged code: review-stub creation, response shapes, helper names. Confirm WEAR-02 reserved the view/review/delete actions and the `import_id`/`vendor`/`metric` string keys (`core/audit.py:36`, `:69`). If not, STOP and fix WEAR-02 first.
- [ ] Confirm `describe()` signature and method (inclusive quantiles or nearest rank); HC-WRB-703 numbers must use the same method.

### Task 1 — RED
- [ ] Write `tests/test_wearables_review.py` with a seed helper that inserts imports, metric rows and review stubs for two profile ids.
- [ ] Run: `cd src/backend && HF_HUB_OFFLINE=1 python -m pytest tests/test_wearables_review.py -p no:cacheprovider -q`
- [ ] Paste output. Expected: 17 failures (404 from missing routes, or AttributeError on missing symbols).

### Task 2 — GREEN: read routes
- [ ] `summary.py`: `summarize_metric(rows)` pure, built on `describe()`.
- [ ] `GET /imports` and `GET /imports/{id}/summary`. Every query filters `profile_id == session.profile_id`. Audit through `audit_and_commit` (fail-closed). 701-706, 715 (view part), 717 green.

### Task 3 — GREEN: review
- [ ] Pydantic model `MetricReview(reviewed: bool, include_in_packet: bool)`; body is `dict[MetricName, MetricReview]`. Apply the section 5 rules, then `audit_and_commit` on master before `profile_db.commit()` (same order as WEAR-06). 707-711, 716 (PUT part) green.

### Task 4 — GREEN: delete
- [ ] `DELETE`: fetch import with profile filter (404 if none), delete reviews, metrics, import; `flush`; audit; commit. 712-714, 716 (DELETE part) green.

### Task 5 — verify
- [ ] Full suite: `cd src/backend && flock /tmp/claude-1000/hc-pytest.lock env HF_HUB_OFFLINE=1 python -m pytest -p no:cacheprovider -q`. Collected = start + 17.
- [ ] Count slots, `python3 scripts/docs_lint.py --link-graph`, security-reviewer on the diff.

## 8. Mutation / break checks (temporary, never committed)

1. Remove the `profile_id` filter from the delete query → HC-WRB-713 red.
2. Delete only the import row (skip the two child deletes) → HC-WRB-712 red.
3. Remove the `include requires reviewed` check → HC-WRB-708 red.
4. Add `"mean"` to the summary dict → HC-WRB-703 red. After each: revert, `git diff` empty.

## 9. Acceptance criteria

- RED output (17 failing) and GREEN output (17 passed) pasted.
- Full-suite output with collected = start + 17.
- HC-WRB-712 shows zero child rows by direct query, not by response body.
- `git diff --stat origin/main...HEAD` lists only the section 3 files.

## 10. Rollback

Revert the PR. No migration, no schema change. Review state and imports stay in the profile DB; WEAR-06 data is unaffected.

## 11. What these tests cannot see (recurring-failures.md)

- **#1:** "other profile" tests share one session, so they prove the query filter, not physical DB separation. They assert on rows and returned values, not on file names.
- **#9:** explicit child deletes are tested here for imports only. Any other path that deletes a parent (profile delete, synthetic reset) is WEAR-02's; if it misses a table, 712 will not notice.
- **#2:** audit-then-commit order leaves an audit row with no state change if the profile commit fails. Accepted residual, same as WEAR-06.
- **#10:** HC-WRB-717 covers only the list route on `main.app`; the other three routes ride the same mounted router, which is a deliberate saving.
- Whether the summary numbers help a patient is not tested (WEAR-07b, owner dogfood OW-W1).

## 12. Owner / model-machine items

OW-W5 (D3 answer, default 7). None else.
