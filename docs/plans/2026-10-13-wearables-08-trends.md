# WEAR-08 — Descriptive trends (backend route + frontend panel) — Implementation Plan

**Last Updated:** 2026-10-13
**Owner:** repository owner
**Status:** PROPOSED — not executed (code waits for program M0, WEAR-07 and WEAR-10 merged, D3 and D8 answered; NOTE: WEAR-D8 (owner, 2026-10-14; commit `c53ba44`, PR #92) approved the drafts in plans 10 and 09 only — this plan's strings still need owner copy approval, OW-W8).
**Base measured:** `origin/main` @ `8234990` (files re-read in worktree `hc-wear-plans` @ `a985390`).
**Refresh trigger:** WEAR-05 changes `describe()`; WEAR-07 changes the review state names; WEAR-02 changes the audit vocabulary or the model fields; D3 is answered with a number other than 7; any edit to `api/__init__.py`, `services/index.ts` or `App.tsx` merges first.
**Program:** [`2026-10-13-wearables-00-program.md`](2026-10-13-wearables-00-program.md) (§4 A3, A4, A5, A5b; §5 M3; §6 row WEAR-08).
**Depends on:** WEAR-07 (reviewed rows exist; it adds `wearables_min_days: int = 14` to `core/config.py`, which this plan reuses and does not re-add) **and** WEAR-10 (page shell, hook file, copy file), per amendment 6. Also uses WEAR-02 (models, audit vocabulary, static guard) and WEAR-05 (`describe()`).
**Owner decisions it depends on:** **D3** resolved — WEAR-D3 (owner, 2026-10-14): 14 days, coverage line kept; **D8** copy (§Copy P-strings).
**Size target:** M. Honest estimate **about 600 lines** (backend about 130 code and 300 tests; frontend about 170 code and 200 tests), above the ~400 line L1 target. Recommended: two PRs, **08-backend** (Tasks 1-4) then **08-frontend** (Tasks 5-7). See Questions.

> For agentic workers: use superpowers:test-driven-development and superpowers:subagent-driven-development; domain skill `asclexis-backend` for the backend part. Backend tests run in WSL or Windows. **Frontend checks (tsc, vitest, Playwright) run on Windows only**: vitest stalls on `/mnt/c/` under WSL (OW-W4). Nothing in this file has been run.

## Scope

**Does license**
- `modules/wearables/select.py::select_current(rows)` — the single A5b read-time selection function. WEAR-08 creates it; WEAR-09 and WEAR-12 reuse it (WEAR-12 changes only the grouping key).
- `GET /wearables/metrics?metric=&from=&to=` on the gated router: reviewed rows only, one value per date, descriptive statistics, coverage.
- A "Wearable (patient-recorded)" panel on the Wearables page with a line, a middle-half band and a data-table twin.
- Suppression below the D3 minimum with a stated reason.

**Does NOT license**
- Any change to `TrendsDashboard.tsx`, `api/observations.py`, `modules/rag.py`, `modules/timeline.py` or `api/export.py` (A3). The panel is **not** placed in the lab chart: that page reads `useObservations`/`useTrend` from the observations service (`TrendsDashboard.tsx:30,136`), draws reference-range lines from `ref_low`/`ref_high` (`:470-478`) and overlays medications; putting consumer-device values there would mix them with verified lab data and borrow its range and flag styling.
- A mean, an "average", normal ranges, thresholds, alerts, comparisons between metrics, or colour meaning good/bad.
- Cross-vendor rules beyond "most recent reviewed import" (WEAR-12 adds tests). Packet use (WEAR-09).

## Evidence

| Fact | path:line @8234990 |
|---|---|
| Existing trend route shape (path param, `RequireAuth`, `from_date`/`to_date` query, `ProfileDbSession`, master `get_db`) | `src/backend/api/observations.py:511-519` |
| Routers are mounted statically with `/prefix` in one file | `src/backend/api/__init__.py:48-67` |
| `ProfileDbSession` is the profile-DB dependency | `src/backend/core/auth.py:341` |
| `route_client(router, prefix, profile_id="profile-a", master_db=None, raise_server_exceptions=True)` | `src/backend/tests/support/routes.py:27-32` |
| `audit_and_commit(db, log_fn, **log_kwargs)` is fail-closed | `src/backend/core/audit.py:474-478` |
| Allowed audit actions live in a frozenset that WEAR-02 extends | `src/backend/core/audit.py:36` |
| Lab trend page reads observations only; Recharts `LineChart`; lab reference lines; "Latest value" summary text | `src/frontend/src/pages/TrendsDashboard.tsx:30,136,405-406,455-489` |
| Line colour used for the lab series | `src/frontend/src/pages/TrendsDashboard.tsx:476-482` (`stroke="#2D7D6F"`) |
| Recharts is mocked in jsdom by replacing `ResponsiveContainer` | `src/frontend/src/__tests__/Accessibility.test.tsx:41-49` |
| Chart accessibility test today checks only for summary text | `src/frontend/src/__tests__/Accessibility.test.tsx:163-171` |
| Hook pattern with `apiGet<T>(path, params)` | `src/frontend/src/services/timeline.ts:48-63` |
| No axe package installed | `src/frontend/package.json:37-57` |
| Design rules: median + IQR + n + days; coverage line; suppress below minimum; chart needs a data-table twin | `docs/research/2026-10-12/04-safety-privacy.md:45,46,54` (F1, F2, F10) |
| Program rules: A5 daily value, A5b "current value = row from the most recent reviewed import covering that date", panel reads reviewed rows only | program §4 A4, A5, A5b |
| Orchestrator pin: `wearables_min_days` comes from WEAR-07; audit helper `log_wearable_event` from WEAR-02 | orchestrator message, 2026-10-13 |
| Orchestrator decision: selection lives in one pure function `select_current`, tie → larger import id, returns other-row count | orchestrator message to this drafter, 2026-10-13 |

## Files to touch

| Path | new/edit | Why | ~Lines |
|---|---|---|---|
| `src/backend/modules/wearables/select.py` | new | `select_current`, no new constant: the route reads `settings.wearables_min_days` | 55 |
| `src/backend/api/wearables.py` | edit | `GET /metrics` on the **gated** router, response models, audit | 75 |
| `src/backend/tests/test_wearables_select.py` | new | HC-WRB-801..804 (pure) | 80 |
| `src/backend/tests/test_wearables_trends.py` | new | HC-WRB-805..816 (HTTP) | 230 |
| `src/frontend/src/services/wearables.ts` | edit | `WearableMetricSeries` type, `useWearableMetrics()` | 30 |
| `src/frontend/src/services/index.ts` | edit | barrel export | 5 |
| `src/frontend/src/components/wearables/WearableTrendsPanel.tsx` | new | panel, chart, twin table, suppression | 150 |
| `src/frontend/src/components/wearables/wearablesCopy.ts` | edit | P-strings | 25 |
| `src/frontend/src/pages/WearablesPage.tsx` | edit | mount the panel | 5 |
| `src/frontend/src/__tests__/WearableTrendsPanel.test.tsx` | new | HC-WRB-8F01..8F09 | 190 |
| `src/frontend/e2e/wearables-trends.spec.ts` | new | HC-WRB-8F10 | 30 |
| `CLAUDE.md`, `AGENT.md` | edit | collected-count slots only (SLOT-RULE) | 2 |

## Ask-first files touched

None. `core/audit.py` is **not** edited here: WEAR-02 reserves the action and keys (A12). If Task 0 finds a needed key missing, stop and amend WEAR-02, which carries the security-reviewer pass.

## Data contract

Reads WEAR-02 tables `wearable_daily_metrics`, `wearable_metric_reviews`, `wearable_imports`. A row is eligible only when its (import, metric) review has `patient_reviewed_at` not null (A4). `include_in_packet` is irrelevant here.

`select_current(rows) -> list[dict]`: input rows are dicts with `import_id`, `imported_at`, `metric`, `local_date`, `value`, `unit`, `tz_changed`, `device_class`. Group by (`metric`, `local_date`); keep the row of the greatest `imported_at`; tie → greater `import_id`; each output row gains `other_rows` (eligible rows in that group that were not chosen). Input is not mutated; output is sorted by `local_date`.

`GET /api/v1/wearables/metrics` (gated router; 404 when the flag is off):

| Param | Rule |
|---|---|
| `metric` | required; one of `resting_heart_rate`, `sleep_asleep_minutes`, `step_count`; else 422 |
| `from`, `to` | ISO dates, inclusive. Both optional. Default `to` = latest eligible `local_date` for the metric; default `from` = `to` − 89 days. `from` > `to` or window > 1830 days → 422. No host clock is used. |

Response:
- `metric`, `unit`, `from`, `to`, `window_days` (M), `days_with_data` (N), `min_days` (= `settings.wearables_min_days`, WEAR-D3 = 14), `latest_date` (or null)
- `suppression`: `null`, `"no_reviewed_data"` (N = 0) or `"below_minimum_days"` (0 < N < `min_days`)
- `summary`: `{median, p25, p75, min, max}` from `describe()` (WEAR-05), or null when suppressed
- `points`: `[{local_date, value, tz_changed, device_class}]`, or `[]` when suppressed

There is no `mean`, `average`, `source_name`, `filename` or import id key in the response (HC-WRB-815 asserts the key sets). Audit: one row per call via `log_wearable_event` with the "metrics view" action, both reserved by WEAR-02, details `{metric, days_covered}` only (`days_covered` is a count key WEAR-02 reserves; `days_with_data` is not).

## Copy

D8: the owner approves every string with WEAR-10's and WEAR-07b's tables. None uses: caused, due to, indicates, diagnos*, normal, abnormal, average, mean, risk, should; none makes a device-classification claim.

| ID | Where | String (verbatim) |
|---|---|---|
| P1 | Panel title | `Wearable (patient-recorded)` |
| P2 | Panel note | `Daily values recorded by a consumer device and reviewed by you. Not a clinical measurement.` |
| P3 | Metric tabs | `Resting heart rate`, `Sleep (minutes asleep)`, `Steps` (same as R17) |
| P4 | Window select | `30 days`, `90 days`, `365 days`, each followed by `ending {latest_date}` |
| P5 | Coverage | `Data on {n} of {m} days.` |
| P6 | Statistics | `Median`, `Middle half of days`, `Lowest to highest`; values `{p25} to {p75} {unit}`, `{min} to {max} {unit}` |
| P7 | Band legend | `Shaded band: the middle half of the days in this window.` |
| P8 | Suppressed (below minimum) | `Not shown: only {n} days have data in this window. A summary needs at least {min} days.` |
| P9 | Suppressed (none reviewed) | `No reviewed data for this metric. Review an import to see it here.` |
| P10 | Time zone footnote | `* The time zone changed on this day.` (only when a point has `tz_changed`) |
| P11 | Table caption / headers | `Daily values for {metric}, {from} to {to}` / `Date`, `Value`, `Device` |
| P12 | Chart label | `Line chart of daily {metric}, {from} to {to}. The same values are in the table below.` |
| P13 | Loading / error | `Loading wearable values...` / `Could not load wearable values. Reload the page to try again.` |

## TDD test list

Backend: pytest, `src/backend/tests/test_wearables_select.py` (801-804) and `test_wearables_trends.py` (805-816). All route tests go through HTTP: `route_client` (HC-WRB-806-815) or `TestClient(main.app)` (805, 816). Isolation asserts on returned values. Covers research HC-WRB-008 (read half), HC-WRB-013 (suppression), HC-WRB-014 (audit), F1, F2.

| ID | assertion | RED reason |
|---|---|---|
| HC-WRB-801 | two eligible rows, same (metric, date), different `imported_at`: later import's value is returned | `select.py` missing |
| HC-WRB-802 | equal `imported_at`: the larger `import_id` wins, in both input orders | missing |
| HC-WRB-803 | `other_rows` is 1 for the contested date and 0 for the others; non-overlapping dates are all kept; output sorted | missing |
| HC-WRB-804 | input list and dicts are unchanged after the call (deep copy compare) | missing |
| HC-WRB-805 | `TestClient(main.app)` flag off: `GET /api/v1/wearables/metrics?metric=step_count` is 404 | route not mounted yet (404 for the wrong reason; paired with 816) |
| HC-WRB-806 | import with 10 days, review row absent: `days_with_data` 0, `suppression` `no_reviewed_data`, `points == []`; after setting `patient_reviewed_at` the 10 values appear | route missing |
| HC-WRB-807 | reviewed import A (days 1-10) and newer reviewed import B (days 5-14, different values): days 5-10 show B's values; delete B's metrics, reviews, then import (children first, A5b / amendment 3) and A's values for days 5-10 return | route missing |
| HC-WRB-808 | profile B's request returns `days_with_data` 0 and no value from A's sentinel fixtures (A: 61.0, B: 58.0); also, rows with a foreign `profile_id` seeded into the same DB are not returned | route missing |
| HC-WRB-809 | boundary: 13 days → `below_minimum_days`, `summary` null, `points == []`; 14 days → not suppressed | route missing |
| HC-WRB-810 | 30-day window, 12 days with data: `window_days` 30, `days_with_data` 12; rows dated `from` and `to` included, one day outside each excluded | route missing |
| HC-WRB-811 | outlier fixture [49,50,50,51,51,52,90]: median 51, min 49, max 90, p25/p75 equal `describe()` output; adding the outlier does not move the median; response JSON has none of the keys `mean`, `average`, `avg` at any depth | route missing |
| HC-WRB-812 | 422 for unknown `metric`, missing `metric`, `from` > `to`, window of 1831 days | route missing |
| HC-WRB-813 | no `from`/`to`: `to` equals the latest eligible date and `from` is 89 days earlier | route missing |
| HC-WRB-814 | one audit row per call; `details` keys ⊆ {`metric`, `days_covered`}; no value, filename or source name in the row (same method as `tests/test_audit_phi_minimization.py` HC-AUD-001) | route missing |
| HC-WRB-815 | point keys exactly {`local_date`,`value`,`tz_changed`,`device_class`}; `device_class` in the closed set; a seeded `source_name` "Jane's Apple Watch" and filename never appear in the response text | route missing |
| HC-WRB-816 | `TestClient(main.app)` flag on: same URL returns 200 (not 404), so the mount at the real prefix exists (recurring-failures #10) | not mounted |

Frontend (Windows only), `src/frontend/src/__tests__/WearableTrendsPanel.test.tsx`; mock `@/services/api`; mock Recharts `ResponsiveContainer` as at `Accessibility.test.tsx:41-49`; the panel imports no `motion.*`, so framer-motion needs no mock unless rendered through `PageTransition` (then use a prop-filtering proxy: drop `initial, animate, exit, variants, transition, layoutId, whileHover, whileTap`; cover `div, button, tr, p`).

| ID | assertion | RED reason |
|---|---|---|
| HC-WRB-8F01 | `useWearableMetrics` calls `GET /wearables/metrics` with `{metric}` only, then with `{metric, from, to}` after a window change | hook missing |
| HC-WRB-8F02 | panel shows P1, P2, P5 with fixture numbers, and a list of Median / Middle half / Lowest to highest with units | component missing |
| HC-WRB-8F03 | data-table twin: `table` named by P11, headers Date/Value/Device, one body row per point, first and last row text equal the fixture; chart wrapper has `role="img"` and label P12 | missing |
| HC-WRB-8F04 | `below_minimum_days`: P8 with `n` and `min` from the response; no table, no `role="img"`, no statistics list | missing |
| HC-WRB-8F05 | `no_reviewed_data`: P9 shown and nothing else | missing |
| HC-WRB-8F06 | a point with `tz_changed` shows `*` in its row and P10 appears once; with none, P10 is absent | missing |
| HC-WRB-8F07 | rendered text and every P-string match none of `/\b(caused\|due to\|indicates\|diagnos\w*\|normal\|abnormal\|average\|mean\|risk\|should)\b/i`; no element has a class starting `text-status-` or `bg-status-`; no `ReferenceLine` | missing |
| HC-WRB-8F08 | switching metric tab refetches with the new metric; window options carry the response's `latest_date` | missing |
| HC-WRB-8F09 | loading shows P13 in a `status` region; a rejected request shows the P13 error | missing |
| HC-WRB-8F10 | `e2e/wearables-trends.spec.ts` (Windows): flag on, one reviewed and one unreviewed import; panel shows only the reviewed values; keyboard `Tab` reaches the metric tabs and the table | panel missing |

Accessibility: no axe (not installed; research F10 names it). Assertions use roles and names. See Questions.

## Tasks

- [ ] **Task 0 — gates.** `git merge-base --is-ancestor <commit> origin/main` for WEAR-02, 05, 07 and 10. D3 and D8 signed. Read merged `describe()` (name, signature, quantile method), WEAR-07's review state names, WEAR-02's audit action and key names, and `tests/support/routes.py` to see how a second profile is simulated. Fix this plan where they differ; note each change. Record baselines: `cd src/backend && HF_HUB_OFFLINE=1 python -m pytest --collect-only -q -p no:cacheprovider | tail -1`.
- [ ] **Task 1 — RED (select).** Write `test_wearables_select.py`. `cd src/backend && HF_HUB_OFFLINE=1 python -m pytest tests/test_wearables_select.py -p no:cacheprovider -q`. Expect 4 collection or import errors. Paste.
- [ ] **Task 2 — GREEN (select).** Implement `select.py`. Re-run; 4 passed.
- [ ] **Task 3 — RED (route).** Write `test_wearables_trends.py` with a seeding helper that builds imports, rows and reviews through the ORM models. Run `... tests/test_wearables_trends.py -p no:cacheprovider -q`. Expect 12 failures (404 or missing route). Paste.
- [ ] **Task 4 — GREEN (route).** Add the route to the gated router; audit; response models. Re-run until green. Full suite: `cd src/backend && flock /tmp/claude-1000/hc-pytest.lock env HF_HUB_OFFLINE=1 python -m pytest -p no:cacheprovider -q` (expect only the known `test_api_rag_index_002b` environment failure). Collected = start + 16; update the CLAUDE.md and AGENT.md count slots in the same commit.
- [ ] **Task 5 — RED (panel), Windows.** Write `WearableTrendsPanel.test.tsx`. `cd src/frontend && npx vitest run src/__tests__/WearableTrendsPanel.test.tsx`. Paste failures.
- [ ] **Task 6 — GREEN (panel), Windows.** Hook, copy, component, mount in `WearablesPage.tsx`. Recharts `ComposedChart`: `Line` in the existing accent colour, `ReferenceArea` (y1 = p25, y2 = p75) in a neutral grey, no `ReferenceLine`, `animationDuration` 0 when `useReducedMotion()` is true (as `TrendsDashboard.tsx` does). Table in a `max-h-72 overflow-auto` wrapper with `tabIndex={0}`.
- [ ] **Task 7 — checks, Windows.** `npx tsc --noEmit`, `npm run lint`, full `npx vitest run`, `npx playwright test e2e/wearables-trends.spec.ts` (flag on, backend merged). Then `git diff --stat origin/main -- src/frontend/src/pages/TrendsDashboard.tsx src/backend/api/observations.py src/backend/modules/rag.py src/backend/modules/timeline.py src/backend/api/export.py` must print nothing, and `TrendsDashboard.test.tsx` and `Accessibility.test.tsx` pass unchanged. Run the WEAR-02 static import-guard test: `... python -m pytest tests/test_wearables_contract.py -p no:cacheprovider -q` (file name per WEAR-02; paste the result).
- [ ] **Task 8 — security-reviewer** on the route diff (auth dependency present, profile filter, no free text in response or audit).

## Mutation / break checks (temporary, never committed)

1. In the route, drop the "reviewed" filter. Expect HC-WRB-806 red.
2. Remove the `profile_id` filter on the query. Expect HC-WRB-808 (second half) red.
3. Change `n >= min_days` to `n > min_days`. Expect HC-WRB-809 red.
4. Make `select_current` keep the oldest import. Expect 801 and 807 red.
5. Mount `/metrics` on the ungated status router. Expect 805 red.
6. Frontend: render the chart when `suppression` is set. Expect 8F04 red.
7. Frontend: add `<ReferenceLine y={p75}/>`. Expect 8F07 red.

After each revert, `git diff` must equal the pre-break diff.

## Acceptance criteria (measured, seen output)

- Backend: 16 new tests pass (paste), collected count = start + 16 (paste `--collect-only` tail before and after), CLAUDE.md and AGENT.md slots updated; full suite shows only the known environment failure.
- Frontend (Windows): `WearableTrendsPanel.test.tsx` 9 passed; full run baseline + 9 (+ prior WEAR-10/07b additions); `tsc` and lint clean; Playwright 8F10 passes. Output pasted.
- `git diff --stat` guard from Task 7 prints nothing; WEAR-02 static guard green.
- Owner looks at the panel with a real import (OW-W1) and records what they saw.

## Rollback

Revert the PR(s). The route disappears (404 as when the flag is off); no migration, no data change. The panel disappears from the page.

## What these tests cannot see

- Recurring-failures #1: the frontend suite mocks `@/services/api`; a wrong query-parameter name (`from` is a reserved word in Python, so the FastAPI alias must be `from`) passes there. 8F10 and 816 are the real-path checks; 811 and 810 prove arithmetic only on fixtures.
- Recurring-failures #3: `days_with_data`, `window_days` and the statistics are computed in code and asserted against hand-computed fixtures. Real exports (partial days, wrist-off days) are not exercised until OW-W1.
- Recurring-failures #9: the reviewed-only rule is enforced in this one route. WEAR-09 reads through `select_current` too; any later reader that skips it is not caught here.
- Recurring-failures #10: 816 proves the mount only for this route; the status gating at the router level is WEAR-01's.
- Recurring-failures #4: frontend results depend on Windows and a real browser; Recharts rendering under jsdom is mocked, so the band and line are never actually drawn in a test.
- Whether a patient reads the band as "normal". The legend P7 says what it is; only dogfood shows whether it is understood.
- Date edge: the route trusts stored `local_date`; timezone bucketing correctness is WEAR-03.

## Owner / model-machine items

- **OW-W4** — vitest and Playwright on Windows.
- **OW-W8** — owner copy approval for this plan's strings (WEAR-D8 named only plans 10 and 09).
- **OW-W1** — dogfood the panel on the real export.
- No model-machine items.
