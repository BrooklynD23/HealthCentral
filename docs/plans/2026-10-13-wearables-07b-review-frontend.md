# WEAR-07b — Review screen — frontend — Implementation Plan

**Last Updated:** 2026-10-13
**Owner:** repository owner
**Status:** PROPOSED — not executed (code waits for program M0, WEAR-07 and WEAR-10 merged, D8 signed on the §Copy table).
**Base measured:** `origin/main` @ `8234990` (files re-read in worktree `hc-wear-plans` @ `a985390`).
**Refresh trigger:** WEAR-06 or WEAR-07 change a route path, body or response field; WEAR-10 changes `wearablesCopy.ts` or the page shell; D6 or D8 answers change the copy; any edit to `services/api.ts`, `services/index.ts` or `App.tsx` merges first.
**Program:** [`2026-10-13-wearables-00-program.md`](2026-10-13-wearables-00-program.md) (§4 A4, A5, A5b; §6 row WEAR-07b).
**Depends on:** WEAR-07 (list, summary, review, delete routes) and WEAR-10 (page shell, `services/wearables.ts`, `wearablesCopy.ts`, barrel edit). Wave WC, serial after WEAR-07 and WEAR-10.
**Owner decisions it depends on:** D8 (copy), D3 default 7 (only as the backend's `below_minimum_days` flag; the number is not hard-coded in the UI), D1 default (b) (no stored ZIP, so no download link anywhere).
**Size target:** M, about 350 lines of diff (about 170 code, 180 tests).

> For agentic workers: use superpowers:test-driven-development and superpowers:subagent-driven-development. Frontend only. Frontend checks run **on Windows only** (vitest stalls on `/mnt/c/` under WSL). Nothing in this file has been run.

## Scope

**Does license**
- Upload control (`accept=".zip"`), import list, per-import review table with two toggles per metric, delete-import control.
- Hooks in `services/wearables.ts` for list, summary, upload, review, delete; barrel export.
- A small raw-body upload helper in `services/api.ts` (WEAR-06 takes the ZIP as a raw `application/zip` body, not multipart; `apiUpload` can only send `FormData`).
- Neutral display: numbers and units only.

**Does NOT license**
- Any chart or trend (WEAR-08). Any packet UI (WEAR-09).
- Computing statistics in the browser. Median, IQR, min, max and days come from the server (`describe()` in WEAR-05). The UI formats them only.
- Showing a mean, an "average", normal ranges, or good/bad colour. No `status-*` colour classes inside the table.
- Any backend change.

## Evidence

| Fact | path:line @8234990 |
|---|---|
| Upload helper sends `FormData` with a `file` field, so it cannot send a raw ZIP body | `src/frontend/src/services/api.ts:273-290` (`apiUpload`) |
| Auth header, URL builder, response handler and fetch wrapper are module-private in `api.ts`; a new exported helper must live in that file | `src/frontend/src/services/api.ts:44,84,98,124` |
| `apiGet` / `apiDelete` signatures (delete returns `void`, optional body) | `src/frontend/src/services/api.ts:141-145,218-222` |
| `apiPut` exists for the review call | `src/frontend/src/services/api.ts:180` |
| `ApiError(status, statusText, message)` is the error type tests construct | `src/frontend/src/__tests__/Accessibility.test.tsx:28-37` |
| Service hook pattern (`useQuery`, `queryKey`, `apiGet`) | `src/frontend/src/services/timeline.ts:7-8,58-63` |
| Barrel pattern; WEAR-10 adds the wearables block, this plan extends it | `src/frontend/src/services/index.ts:326-341` |
| Component test pattern: mock `@/services/api`, fresh `QueryClient` with `retry:false`, `QueryClientProvider` | `src/frontend/src/__tests__/TimelineService.test.tsx:12-29`, `src/frontend/src/__tests__/Accessibility.test.tsx:51-64` |
| framer-motion mocks in page tests spread all props (no filtering) | `src/frontend/src/__tests__/ExportPage.test.tsx:40-49` |
| `Accessibility.test.tsx` uses role and text queries; no axe | `src/frontend/src/__tests__/Accessibility.test.tsx:12-16,165-171`; `src/frontend/package.json:37-57` has no axe package |
| Existing chart pages keep a screen-reader data summary; this plan uses a visible real table instead | `src/frontend/src/pages/TrendsDashboard.tsx:455-470` (summary paragraph under the chart) |
| E2E helper `openAuthenticatedPage` | `src/frontend/e2e/routing.spec.ts:9,13` |
| WEAR-02 table and enum names the UI displays (metric, device_class, review per import per metric) | `docs/plans/2026-10-13-wearables-00-program.md:A4,A5b` (program) and the WEAR-02 contract in the planning brief |

Routes and response shapes consumed (**INFERRED** from the WEAR-07 brief, since WEAR-07's plan is drafted in parallel; Task 0 reconciles with the merged WEAR-07 and fixes this plan if they differ):

| Call | Path | Shape |
|---|---|---|
| list | `GET /wearables/imports` | `[{id, source_vendor, filename, imported_at, records_read, records_skipped, days_covered, first_local_date, last_local_date}]` |
| summary | `GET /wearables/imports/{id}/summary` | `{import_id, skipped_reasons: {reason: count}, metrics: [{metric, unit, days_with_data, median, p25, p75, min, max, device_classes: string[], reviewed: bool, include_in_packet: bool, below_minimum_days: bool}]}` |
| review | `PUT /wearables/imports/{id}/review` | body `{[metric]: {reviewed, include_in_packet}}` (only the changed metric is sent) |
| delete | `DELETE /wearables/imports/{id}` | no body |
| upload | `POST /wearables/imports` | raw body, `Content-Type: application/zip` (WEAR-06 amendment 4); filename travels in header `X-Wearable-Filename` (WEAR-06 §Import row; Task 0 confirms on the merged route) |
| upload ok | 201 | `{id, records_read, records_skipped, days_covered, skipped_reasons}` |
| upload errors | 409 (same hash; body names the existing id), 413 (over cap), 400/422 (unreadable or invalid), 404 (flag off) |

## Files to touch

| Path | new/edit | Why | ~Lines |
|---|---|---|---|
| `src/frontend/src/services/api.ts` | edit | add `apiUploadRaw<T>(endpoint, file, params?)`: `POST`, `Content-Type: application/zip`, `body: file`, same auth and error path | 18 |
| `src/frontend/src/services/wearables.ts` | edit | types and 5 hooks (list, summary, upload, review, delete); invalidate `['wearables','imports']` | 70 |
| `src/frontend/src/services/index.ts` | edit | barrel exports for the new hooks and types | 12 |
| `src/frontend/src/components/wearables/wearablesCopy.ts` | edit | add the R-strings below | 35 |
| `src/frontend/src/components/wearables/ImportUpload.tsx` | new | file input, busy and error states | 50 |
| `src/frontend/src/components/wearables/ImportList.tsx` | new | list, selection, delete (two-step) | 60 |
| `src/frontend/src/components/wearables/ReviewTable.tsx` | new | real `<table>` with caption, two checkboxes per row | 70 |
| `src/frontend/src/pages/WearablesPage.tsx` | edit | mount the three components, drop the C15 placeholder | 12 |
| `src/frontend/src/__tests__/WearablesReview.test.tsx` | new | HC-WRB-7B01..7B11 | 190 |
| `src/frontend/e2e/wearables-review.spec.ts` + a small synthetic zip fixture | new | HC-WRB-7B12 | 40 |

If the diff passes about 400 lines, split the delete control into a follow-up and say so in the PR.

## Ask-first files touched

None. (`services/api.ts` is ordinary client code, not `security/` or `core/auth.py`.)

## Data contract

- Types mirror the table above. `metric` is the closed set `resting_heart_rate | sleep_asleep_minutes | step_count`; `device_classes` entries are the closed set `apple_watch | iphone | garmin_device | other`. An unknown value renders as `Other` (never as raw text).
- UI rules: `include_in_packet` can be true only when `reviewed` is true. Un-ticking Reviewed sends `include_in_packet: false` in the same request.
- Display order: Resting heart rate, Sleep, Steps. Numbers shown with at most one decimal; units `bpm`, `min`, `steps`.
- All text from the server (filename) is rendered as React text, never as HTML.

## Copy

Added to `wearablesCopy.ts` and approved under D8 with WEAR-10's table. None uses: caused, due to, indicates, diagnos*, normal, abnormal, average, mean, risk, should; none makes a device-classification claim.

| ID | Where | String (verbatim) |
|---|---|---|
| R1 | Upload heading | `Import an export file` |
| R2 | File input label | `Apple Health export (.zip)` |
| R3 | Import button | `Import` |
| R4 | Busy status | `Importing. Large files can take a few minutes.` |
| R5 | Success | `Imported {days} days of data from {records} records. {skipped} records were skipped.` |
| R6 | 409 | `This file was already imported.` |
| R7 | 413 | `This file is larger than the size limit.` |
| R8 | 400 / 422 | `This file could not be read as an Apple Health export.` |
| R9 | any other failure | `The import did not finish. Nothing was saved.` |
| R10 | non-.zip chosen | `Choose a .zip file.` |
| R11 | List heading / empty | `Imports` / `No imports yet.` |
| R12 | List item line | `Imported {date}. {first} to {last}, {days} days with data.` |
| R13 | Review heading | `Review daily summaries` |
| R14 | Review intro | `Check each summary against what you know. Mark it reviewed to show it in the trends panel. Include it in the visit packet only if you choose to.` |
| R15 | Table caption | `Daily summary for import {filename}` |
| R16 | Column headers | `Metric`, `Days with data`, `Median`, `Middle half of days (25th to 75th percentile)`, `Lowest to highest`, `Device`, `Reviewed`, `Include in packet` |
| R17 | Metric names | `Resting heart rate`, `Sleep (minutes asleep)`, `Steps` |
| R18 | Device names | `Apple Watch`, `iPhone`, `Garmin device`, `Other` |
| R19 | Few days flag | `Too few days to show in trends or the packet.` |
| R20 | Skipped line | `Records skipped: {n}` (then one line per reason: `{reason}: {count}`) |
| R21 | Checkbox accessible names | `Reviewed: {metric}`, `Include in packet: {metric}` |
| R22 | Delete | `Delete import` / `Delete this import's daily values? Other imports are not affected.` / `Delete` / `Cancel` |
| R23 | Load error | `Could not load imports. Reload the page to try again.` |

R8 and R9 never print server text. R9's "Nothing was saved" holds only if WEAR-06 writes in one transaction (it does in the brief); Task 0 re-checks.

## TDD test list

IDs `HC-WRB-7B<NN>`. File `src/frontend/src/__tests__/WearablesReview.test.tsx` unless stated. "Covers research" applies to the UI half of HC-WRB-008 and F8 (reviewed, never "verified").

| ID | assertion | RED reason |
|---|---|---|
| HC-WRB-7B01 | hooks call the right endpoints: list `GET /wearables/imports`; summary `GET /wearables/imports/{id}/summary`; review `PUT .../review` with exactly `{resting_heart_rate:{reviewed:true,include_in_packet:false}}`; delete `DELETE .../{id}` | hooks missing |
| HC-WRB-7B02 | `apiUploadRaw` (fetch mocked): method POST, header `Content-Type: application/zip`, `body` is the same `File` object (not `FormData`), auth header present, `X-Wearable-Filename` header set to the file name; 413 becomes `ApiError` | helper missing |
| HC-WRB-7B03 | input has accessible name R2 and `accept=".zip"`; choosing `notes.txt` shows R10 and `apiUploadRaw` is not called | component missing |
| HC-WRB-7B04 | success path: R4 shown while pending, then R5 with the fixture counts; list query invalidated (second `GET /imports` call) | component missing |
| HC-WRB-7B05 | 409, 413, 400, 500 show R6, R7, R8, R9 respectively and none contains the server message text (fixture message `SECRET-DETAIL`) | component missing |
| HC-WRB-7B06 | list renders `<ul>` items; a filename `<img src=x onerror=alert(1)>.zip` appears as text and `container.querySelector('img')` is null | component missing |
| HC-WRB-7B07 | review table is a real table: `getByRole('table')` named by R15, 8 `columnheader`s (R16), 3 `row`s in the body, fixture numbers present with units | component missing |
| HC-WRB-7B08 | table subtree text matches none of `/\b(caused\|due to\|indicates\|diagnos\w*\|normal\|abnormal\|average\|mean\|risk\|should)\b/i`; no element in the subtree has a class starting `text-status-` or `bg-status-`; all of `WEARABLES_COPY` passes the same regex | component missing |
| HC-WRB-7B09 | Include checkbox is disabled while Reviewed is off; ticking Reviewed sends `{reviewed:true,include_in_packet:false}`; ticking Include then sends `{reviewed:true,include_in_packet:true}`; un-ticking Reviewed while Include is on sends `{reviewed:false,include_in_packet:false}` | component missing |
| HC-WRB-7B10 | `below_minimum_days: true` shows R19 on that row only; `skipped_reasons` renders R20 lines; a metric with `device_classes: ['weird']` shows `Other` | component missing |
| HC-WRB-7B11 | delete is two-step: first click shows R22 confirm and fires no request; Cancel fires none; Delete fires exactly one `DELETE`, then list refetches | component missing |
| HC-WRB-7B12 | `e2e/wearables-review.spec.ts` (Windows): flag on, upload the synthetic zip, table appears, tick Reviewed and Include, reload, state persists; delete removes the row | page lacks the UI |

Accessibility: no axe (not installed). Assertions use roles and names (`table`, `columnheader`, `checkbox` with R21 names, `status` for R4, `alert` for R5-R9) and keyboard order (`userEvent.tab()` reaches input, Import, then the table checkboxes). See Questions.

framer-motion: these components import no `motion.*`. If a composed `Card` or `PageTransition` does, mock framer-motion with a prop-filtering proxy (drop `initial, animate, exit, variants, transition, layoutId, whileHover, whileTap`; cover `div, button, tr, p`). Do not copy the non-filtering mock at `ExportPage.test.tsx:40-49`.

## Tasks

- [ ] **Task 0 — gates.** `git merge-base --is-ancestor <WEAR-07 commit> origin/main` and the same for WEAR-10 return 0. Read merged `api/wearables.py`: paths, bodies, and the upload filename mechanism; edit the "INFERRED" table above to match and note the diff. D8 signed. Windows baseline: `cd src/frontend && npx vitest run` (paste totals).
- [ ] **RED.** Write `WearablesReview.test.tsx` (7B01-7B11) against missing modules. Run on Windows: `npx vitest run src/__tests__/WearablesReview.test.tsx`. Paste failure output (unresolved imports, then assertion failures after empty stubs).
- [ ] **GREEN 1.** `apiUploadRaw` and the hooks, barrel. 7B01, 7B02 pass.
- [ ] **GREEN 2.** `ImportUpload` (7B03-7B05), `ImportList` (7B06, 7B11), `ReviewTable` (7B07-7B10). Copy exactly as R1-R23.
- [ ] **GREEN 3.** Mount in `WearablesPage.tsx`, remove C15. Re-run WEAR-10's `WearablesShell.test.tsx` (must stay green; update its C15 assertion if present, in this commit).
- [ ] **Refactor.** Extract nothing unless a file passes 200 lines.
- [ ] **Checks, Windows.** `npx tsc --noEmit`, `npm run lint`, `npx vitest run`, then `npx playwright test e2e/wearables-review.spec.ts` against a backend started with `WEARABLES_ENABLED=true` and the WEAR-06 route merged. Paste outputs.
- [ ] **Slots.** No backend tests added; backend collected count unchanged (paste `--collect-only` tail).

## Mutation / break checks (temporary, never committed)

1. Remove `disabled={!reviewed}` on Include. Expect 7B09 red.
2. Replace `<table>` with a `div` grid. Expect 7B07 red.
3. Render the filename with `dangerouslySetInnerHTML`. Expect 7B06 red.
4. Send `include_in_packet: true` when un-ticking Reviewed. Expect 7B09 red.
5. Add `text-status-success` to a value cell. Expect 7B08 red.

Revert each, then `git diff` must equal the pre-break diff.

## Acceptance criteria (measured, seen output)

- Windows vitest: `WearablesReview.test.tsx` 11 passed; full suite baseline + 11 (+ WEAR-10's 7), 0 new failures. Output pasted.
- Playwright 7B12 passes once on a real backend; output pasted.
- `tsc --noEmit` and lint clean.
- A screen capture or DOM dump of the review table reviewed against R13-R20 by the owner.
- `git diff --stat origin/main` shows only the files above; `TrendsDashboard.tsx` untouched.

## Rollback

Revert the PR. The shell from WEAR-10 remains (with its placeholder). Backend data created through the UI is removed by deleting the imports (WEAR-07) or by the profile reset.

## What these tests cannot see

- Recurring-failures #1: every vitest case mocks `@/services/api`. A wrong path, method or body field against the real WEAR-07 routes passes here. Only Task 0's reconciliation and the Playwright run (7B12) touch the real backend.
- Recurring-failures #3: "N days" and the statistics are shown, not computed, by the UI; tests use fixtures and prove formatting only. Whether the server numbers are right is WEAR-05 and WEAR-07's job.
- Recurring-failures #9: the profile-isolation invariant lives in the backend. The UI test cannot show that profile B never sees A's imports.
- Recurring-failures #4: results depend on Windows and a real browser. A large (hundreds of MB) upload through `fetch` with a `File` body is not exercised by any test (OW-W2 covers the backend side).
- Recurring-failures #6: the Playwright command is only a plan until it is run on Windows against a flag-on backend.
- Whether the table is understandable to a patient. Only the owner dogfood (OW-W1) shows that.

## Owner / model-machine items

- **OW-W4** — run vitest and Playwright for this plan on Windows.
- **OW-W5** — answer D8 (R-table).
- **OW-W1** — dogfood the screen with the real export.
- No model-machine items.
