# WEAR-10 — Wearables page shell, nav gating, disclaimer copy — Implementation Plan

**Last Updated:** 2026-10-13
**Owner:** repository owner
**Status:** PROPOSED — not executed (code waits for program M0, WEAR-01 merged; §Copy approved by WEAR-D8 (owner, 2026-10-14; commit `c53ba44`, PR #92): "Approve drafts as written (Recommended)", incl. G1-G4).
**Base measured:** `origin/main` @ `8234990` (frontend files re-read in worktree `hc-wear-plans` @ `a985390`; no frontend file differs from the base).
**Refresh trigger:** WEAR-01 changes the shape of `GET /wearables/status`; the owner reverses WEAR-D6 (b); OD-8 (legal read) lands; any edit to `App.tsx`, `components/layout/Sidebar.tsx` or `services/index.ts` merges first.
**Program:** [`2026-10-13-wearables-00-program.md`](2026-10-13-wearables-00-program.md) (§3 flag, §6 row WEAR-10, §9 D6 and D8).
**Depends on:** WEAR-01 (`GET /wearables/status`). Wave WC, parallel with WEAR-07 (disjoint: this plan is frontend only).
**Owner decisions it depends on:** **D8** (copy approval, builds the §Copy drafts below); **D6 (b), signed** (owner, 2026-10-14; temp-file sentence is the (b) wording; if the owner ever reverses it, C6/C7 change and this plan is refreshed; Opus D1D8 R11).
**Size target:** S, about 250 lines of diff (about 90 service and component, 60 page, 100 tests).

> For agentic workers: use superpowers:test-driven-development and superpowers:subagent-driven-development. Frontend only: no backend skill needed. Frontend checks run **on Windows only** (vitest stalls on `/mnt/c/` under WSL, program §10 OW-W4). Nothing in this file has been run.

## Scope

**Does license**
- `services/wearables.ts` with `useWearablesStatus()` and its barrel export.
- A `/wearables` route in `App.tsx` and a Sidebar entry shown only when the status says enabled.
- A Wearables page shell: title, persistent disclaimer, intended-use line, privacy line, iPhone export steps, a Garmin "not available yet" line, and a temporary placeholder slot for WEAR-07b and WEAR-08.
- One copy constants file so tests and the §Copy table cannot drift apart.

**Does NOT license**
- Turning Garmin instructions on (WEAR-12 flips `GARMIN_EXPORT_READY`).
- Any upload, import list, review table or chart (WEAR-07b, WEAR-08).
- Any backend change, any change to `TrendsDashboard.tsx`, `DisclaimerBanner.tsx` or the lab-interpreter components.
- Any claim about medical-device classification, FDA, or clinical use (OD-8 open).
- Any new dependency (see Questions: axe is not installed).

## Evidence

| Fact | path:line @8234990 |
|---|---|
| Routes live in one `<Routes>` block; protected pages are children of `<AppLayout />` | `src/frontend/src/App.tsx:113-131` |
| Pages are lazy-loaded with `lazyRoute(...)` (Suspense fallback) | `src/frontend/src/App.tsx:22-69,97-99` |
| Insertion point for a new route (after export, before settings) | `src/frontend/src/App.tsx:128-129` |
| One `QueryClient` wraps the whole app (`staleTime` 5 min, `retry: 1`) | `src/frontend/src/App.tsx:71-78,103` |
| Nav is a module-level constant array of `{to, icon, label}` | `src/frontend/src/components/layout/Sidebar.tsx:21-34` |
| Nav is rendered by `navItems.map`; link carries `min-h-target` and focus ring classes | `src/frontend/src/components/layout/Sidebar.tsx:56-86` |
| Sidebar already imports lucide icons and uses a framer-motion `motion.div` for the active pill | `src/frontend/src/components/layout/Sidebar.tsx:2-17,75-81` |
| `AppLayout` renders `Sidebar` inside the router and query provider | `src/frontend/src/components/layout/AppLayout.tsx:3,13` |
| Service pattern: `useQuery` + `apiGet<T>(path)` in a small file | `src/frontend/src/services/timeline.ts:7-8,58-63` |
| `apiGet` signature | `src/frontend/src/services/api.ts:141-145` |
| Barrel re-exports hooks and types per service file; last block is feedback | `src/frontend/src/services/index.ts:326-341` |
| Existing disclaimer: `role="alert"`, caution colours, **hard-coded AI-interpretation wording** (so it cannot be reused for wearables) | `src/frontend/src/components/lab-interpreter/DisclaimerBanner.tsx:10-27` |
| Test pattern for mocking `@/services/api` and rendering with `QueryClientProvider` | `src/frontend/src/__tests__/TimelineService.test.tsx:12-29` |
| framer-motion mock used by page tests: spreads **all** props onto `div` (no filtering); only `motion.div` | `src/frontend/src/__tests__/ExportPage.test.tsx:40-49`, `src/frontend/src/__tests__/ExplainAssistant.test.tsx:39-50` |
| `Accessibility.test.tsx` has **no** framer-motion mock and no axe call; it checks roles and text only | `src/frontend/src/__tests__/Accessibility.test.tsx:1-64` (grep: `framer-motion` only in the header comment `:7`) |
| No axe package in `devDependencies` | `src/frontend/package.json:37-57` (grep `axe` empty) |
| `Routing.test.tsx` renders the real `<App />` with `apiGet` mocked to resolve `[]` | `src/frontend/src/__tests__/Routing.test.tsx:12-17` |
| E2E pattern: `openAuthenticatedPage(page, request, path)` | `src/frontend/e2e/routing.spec.ts:9,13` |
| Page index exports eager pages only; lazy pages are imported straight from `./pages/X` in `App.tsx` | `src/frontend/src/pages/index.ts:1-13`, `App.tsx:22-69` |

## Files to touch

| Path | new/edit | Why | ~Lines |
|---|---|---|---|
| `src/frontend/src/services/wearables.ts` | new | `WearablesStatus` type, `useWearablesStatus()` | 25 |
| `src/frontend/src/services/index.ts` | edit | barrel export (WEAR-10 owns the first edit, 07b and 08 extend) | 6 |
| `src/frontend/src/components/wearables/wearablesCopy.ts` | new | every patient-facing string, one `as const` object | 45 |
| `src/frontend/src/components/wearables/WearablesDisclaimer.tsx` | new | persistent banner, `role="note"`, caution styling copied from `DisclaimerBanner.tsx:10-27` | 30 |
| `src/frontend/src/pages/WearablesPage.tsx` | new | shell, status gate, export steps, placeholder slot | 90 |
| `src/frontend/src/App.tsx` | edit | lazy `WearablesPage` + `<Route path="wearables">` | 6 |
| `src/frontend/src/components/layout/Sidebar.tsx` | edit | insert Wearables item when enabled | 12 |
| `src/frontend/src/__tests__/WearablesShell.test.tsx` | new | HC-WRB-1001..1007 | 130 |
| `src/frontend/e2e/wearables-shell.spec.ts` | new | HC-WRB-1008, Windows only | 30 |

## Ask-first files touched

None. (`DisclaimerBanner.tsx` is read only. No backend file.)

## Data contract

Consumes only `GET /api/v1/wearables/status` from WEAR-01: `{ "enabled": boolean }`.

- Fail closed: loading, error, and any body where `enabled !== true` all behave as "off". (`Routing.test.tsx` mocks every GET to `[]`, which is `enabled === undefined` and so off.)
- Query key `['wearables', 'status']`. WEAR-07b and WEAR-08 reuse the same hook.
- Gate in **two places**: the Sidebar entry and the page itself (a typed URL must not show the page when off). Page behaviour when off: `<Navigate to="/inbox" replace />` after the status settles; while loading, an `aria-live` status text.

## Copy

D8: the owner approves or edits every string below before merge. All strings live in `wearablesCopy.ts`. None uses: caused, due to, indicates, diagnos*, normal, abnormal, average, mean, risk, should (checked by HC-WRB-1005 against the constants and the rendered page). None names FDA, a device class, "cleared" or "approved".

| ID | Where | String (verbatim) |
|---|---|---|
| C1 | Sidebar label, page `<h1>` | `Wearables` |
| C2 | Page subtitle | `Your own watch and phone records, kept in your HealthCentral data.` |
| C3 | Disclaimer heading | `Research and education tool` |
| C4 | Disclaimer body (persistent, top of page) | `This is not medical or legal advice. Wearable numbers come from a consumer device and are not clinical measurements. Talk to your healthcare provider about your health.` |
| C5 | Intended-use line (under the banner) | `Intended use: personal record-keeping, research and education. It is built for people who are curious about their own health and want their records in one place.` |
| C6 | Privacy line 1 (WEAR-D6 (b) signed wording, exact) | `The export file is processed by your HealthCentral app and deleted after import.` |
| C7 | Privacy line 2 | `Only daily summaries are kept: resting heart rate, minutes asleep and step count. The file is uploaded to the HealthCentral backend this app is connected to (in the standard setup, this computer). HealthCentral sends nothing to Apple, Garmin or any other online service.` (Codex plans N5, R2-2: the backend URL is configurable via `VITE_API_URL` (`services/api.ts:17-20`), so the copy discloses the upload instead of denying it) | |
| C8 | Export steps heading | `Export from an iPhone` |
| C9 | Export step 1 | `Open the Health app and tap your profile picture.` |
| C10 | Export step 2 | `Tap Export All Health Data, then Export.` |
| C11 | Export step 3 | `Save the file (export.zip) to this computer.` |
| C12 | Garmin line | `Garmin: not available yet.` |
| G1 | Garmin steps heading. Shown only after WEAR-12 merges (M5) | `Export from Garmin Connect` |
| G2 | Garmin step 1. Same condition | `Sign in to your Garmin account on the Garmin website and open Account Management.` |
| G3 | Garmin step 2. Same condition | `Choose Export Your Data and request the export.` |
| G4 | Garmin step 3. Same condition | `Download the file Garmin sends you and save it to this computer.` |
| C13 | Loading status (screen reader) | `Checking whether wearables are turned on...` |
| C14 | Status error (only shown if the user stays on the page; otherwise redirect) | `Could not check whether wearables are turned on. Reload the page to try again.` |
| C15 | Temporary placeholder (removed by WEAR-07b) | `Imports and daily summaries will appear here.` |

Notes for the owner
- C6 is the exact signed D6 (b) sentence (Opus D1D8 R11). If the owner reverses D6 to (a), C6 is replaced by a sentence that names the system temporary folder.
- G1-G4 are approved now so D8 is asked once. They render only when the constant `GARMIN_EXPORT_READY` in `wearablesCopy.ts` is `true`; it ships as `false` and C12 shows instead. WEAR-12 flips the constant and has no other frontend change. G2-G3 are INFERRED from Garmin's account pages; OM-2 / OW-W3 confirms them.
- C9-C11 are INFERRED from Apple's Health app wording. OM-1 / OW-W0 should confirm them on a real phone.
- C4 and C5 state use and a limit. They make no device-classification statement; the legal read stays open as OD-8.
- Line "Talk to your healthcare provider about your health." in C4 is the only action phrase. Delete it if you want the banner to carry the first sentence only.

## TDD test list

Frontend test IDs use the `HC-WRB-<pkg><NN>` scheme with `10` for WEAR-10 (`git grep -i hc-wrb` was empty at base).

| ID | file | assertion | RED reason |
|---|---|---|---|
| HC-WRB-1001 | `__tests__/WearablesShell.test.tsx` | `useWearablesStatus` calls `apiGet('/wearables/status')` once and returns `enabled: true` when mocked | `services/wearables.ts` does not exist (import error) |
| HC-WRB-1002 | same | `<Sidebar />` with status `{enabled:false}` has no link named `Wearables` (`queryByRole('link', {name: 'Wearables'})` is null) | Sidebar has no such logic; this passes trivially before, so it is paired with 1003 and must be run as a pair (see break check 1) |
| HC-WRB-1003 | same | `<Sidebar />` with status `{enabled:true}` shows a link named `Wearables` with `href="/wearables"` | link not rendered today |
| HC-WRB-1004 | same | status request rejects (500) or resolves `[]` or `{}`: link absent (fail closed) | not implemented |
| HC-WRB-1005 | same | every value in `WEARABLES_COPY`, and the rendered page text, matches none of `/\b(caused\|due to\|indicates\|diagnos\w*\|normal\|abnormal\|average\|mean\|risk\|should)\b/i` and none of `/FDA\|medical device\|cleared\|approved\|clinical-grade/i` | copy module does not exist |
| HC-WRB-1006 | same | page with status enabled shows C4 and C6 **exactly** (string equality to the approved text), C4 inside an element with `role="note"`, and it is present on first render, not after a click | page does not exist |
| HC-WRB-1007 | same | page with status `{enabled:false}` renders no `<h1>Wearables` and navigates to `/inbox` (router at `/wearables` ends at `/inbox`); with status enabled and path `/wearables` the `<h1>` shows | route not defined, so `*` redirects to `/` in both cases; the enabled half fails |
| HC-WRB-1010 | same | with `GARMIN_EXPORT_READY` false the page shows C12 and none of G1-G4; with the constant mocked true it shows G1-G4 in an ordered list and hides C12; G1-G4 also pass the banned-phrase regex | Garmin block and constant missing |
| HC-WRB-1008 | `e2e/wearables-shell.spec.ts` (Windows) | real backend flag off: nav has no Wearables and `/wearables` lands on `/inbox`; flag on: nav shows it and the disclaimer is visible | route missing |
| HC-WRB-1009 | `__tests__/Routing.test.tsx` (existing, unchanged) | still passes: unknown path falls back, and the mocked `[]` status keeps the nav entry hidden | none (characterization, must stay green) |

HC-WRB-1002 cannot fail before the change by itself. It is kept because it is the half that fails if someone later makes the entry unconditional; break check 1 proves it.

Accessibility without axe: role and name queries (`getByRole('note')`, `getByRole('heading', {level: 1})`, `getByRole('status')`, ordered list for the steps via `getByRole('list')`), plus keyboard reachability of the Sidebar link (`userEvent.tab()` reaches it). A real axe pass needs a new dev dependency; see Questions.

framer-motion: the Sidebar renders `motion.div` only for the active route, but the page is wrapped by `PageTransition` in `AppLayout` when rendered through `<App />`. Tests render `<Sidebar />` and `<WearablesPage />` directly; where a test renders through `<App />`, mock framer-motion with a prop-filtering `motion` Proxy (drop `initial, animate, exit, variants, transition, layoutId, whileHover, whileTap`) covering `div, button, tr, p`. The existing mocks do not filter (see Evidence), so write the filtering mock inline; do not copy `ExportPage.test.tsx:40-49` as is.

## Tasks

- [ ] **Task 0 — gates.** `git merge-base --is-ancestor <WEAR-01 merge commit> origin/main` returns 0; WEAR-D8 row (approved as written) on `origin/main` in `docs/capstone-report/owner-decisions-*.md`; this plan file present; `curl`/read of WEAR-01's merged `api/wearables.py` confirms the status body is `{"enabled": bool}`. If any fails, stop. Record the frontend test baseline on Windows: `cd src/frontend && npx vitest run` (paste the totals line).
- [ ] **RED.** Create `__tests__/WearablesShell.test.tsx` (HC-WRB-1001..1007) importing the not-yet-existing modules. Run on Windows: `cd src/frontend && npx vitest run src/__tests__/WearablesShell.test.tsx`. Expected: suite fails on unresolved imports; after stubbing empty modules, 1003, 1004 (positive half), 1006, 1007 fail on assertions. Paste both outputs.
- [ ] **GREEN 1.** `services/wearables.ts` (hook, `retry: false` on the query so a 404/500 settles fast), barrel export. 1001 passes.
- [ ] **GREEN 2.** `wearablesCopy.ts` (including `GARMIN_EXPORT_READY = false`), `WearablesDisclaimer.tsx`, `WearablesPage.tsx`; copy exactly as §Copy. 1005, 1006 pass.
- [ ] **GREEN 3.** `App.tsx` lazy route; `Sidebar.tsx`: call `useWearablesStatus()`, build `items` by inserting `{ to: '/wearables', icon: Watch, label: 'Wearables' }` before `/export` only when `data?.enabled === true`. 1002, 1003, 1004, 1007 pass.
- [ ] **Refactor.** None expected. Do not touch `navItems` order for existing entries.
- [ ] **Checks, Windows.** `npx tsc --noEmit`, `npm run lint`, `npx vitest run` (full), then `npx playwright test e2e/wearables-shell.spec.ts` with the backend started `WEARABLES_ENABLED=false` then `true`. WSL is not a valid place for vitest here (OW-W4).
- [ ] **Slots.** Frontend test count is not a CLAUDE.md slot; backend collected count is unchanged by this plan (record `pytest --collect-only -q | tail -1` unchanged from start, expect 1392 or the then-current value).
- [ ] **Docs lint.** `python3 scripts/docs_lint.py --link-graph` on any docs touched (none expected).

## Mutation / break checks (temporary, never committed)

1. Make the Sidebar entry unconditional (delete the `enabled` check). Expect HC-WRB-1002 and 1004 red. Revert; `git diff --stat` shows only the intended files.
2. Remove the page-level redirect. Expect HC-WRB-1007 (disabled half) red. Revert.
3. Change C4 to include the word "normal". Expect HC-WRB-1005 red and 1006 red (exact match). Revert.
4. Set `GARMIN_EXPORT_READY = true`. Expect HC-WRB-1010 red. Revert.
5. Change C6 to drop "and deleted after import". Expect HC-WRB-1006 red. Revert.

After each revert run `git diff` and confirm it matches the pre-break diff.

## Acceptance criteria (measured, seen output)

- Windows vitest output pasted: `WearablesShell.test.tsx` shows 7 passed; full run shows 0 new failures and the count is baseline + 7 (plus `Routing.test.tsx` unchanged).
- Playwright HC-WRB-1008 passes both with the flag off and on (two runs pasted).
- `tsc --noEmit` and lint clean (output pasted).
- Screenshot or DOM text dump of the enabled page matches the §Copy table row by row.
- `git diff --stat origin/main` lists only the files in "Files to touch"; `TrendsDashboard.tsx`, `DisclaimerBanner.tsx` untouched.

## Rollback

Revert the PR. Flag default is off, so no user sees the page before the revert; no data or migration is involved.

## What these tests cannot see

- Recurring-failures #1: mocked `apiGet` proves the UI reads `enabled`, not that WEAR-01's real route returns it. Covered by WEAR-01's `TestClient(main.app)` test and the Playwright run against a real backend (1008).
- Recurring-failures #9: the gate is enforced in the nav and the page. A third entry point (a deep link inside another page, a later "Go to Wearables" button in WEAR-09) is not covered; each new link must use `useWearablesStatus()`.
- Recurring-failures #10: unit tests render components directly. The route being mounted in the real `App.tsx` is shown only by the Playwright test and the `<App />` render in 1007.
- Recurring-failures #4: results depend on Windows and a real browser; WSL runs prove nothing here.
- Whether the words are right: tests check banned phrases and exact equality, not whether the copy is clear or legally sufficient (D8, OD-8).
- Whether Apple's Health app still uses the quoted menu names (C9-C11, INFERRED).

## Owner / model-machine items

- **OW-W4** — run vitest and Playwright for this plan on Windows.
- None: WEAR-D8 and WEAR-D6 answered 2026-10-14. Any change to an approved string needs the owner again.
- **OW-W0** — confirm C9-C11 against the real iPhone.
- **OW-W3** — confirm G2-G3 against the real Garmin account pages (with OM-2).
- No model-machine items.

## Questions for the orchestrator

Raised in the drafting report: test ID scheme for 07b and 10, the missing axe dependency, and the filename mechanism for raw-body upload.
