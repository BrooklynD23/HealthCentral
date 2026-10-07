# NPM-MAJORS (b) — React Router 6 → 7 Migration Plan

> **For agentic workers:** this plan is **not approved for execution**. Owner gate NPM-MAJORS: "Plans for both migrations this wave; they come back to the owner before running." Do not start Task 0 until owner-decisions records an approval naming this file.

**Status:** plan only, written 2026-10-04 by L1-B (Wave 3). Approval pending.
**Source:** NPM-AUDIT PR #38. After `npm audit fix`, `react-router` / `react-router-dom` 6.30.6 still carry 2 moderate advisories: GHSA-wrjc-x8rr-h8h6 (open redirect via a backslash in `<Link>` / `useNavigate`) and GHSA-337j-9hxr-rhxg (constructor injection in `deserializeErrors()` during SSR hydration). npm's only fix is `react-router-dom@7.18.4`, a semver-major. PR #38's security review rated both LOW and not reachable today: every literal navigation target starts with `/`; 5 targets are variables (listed in the scope table), and the app uses declarative `BrowserRouter` with no SSR.
**Architectural:** no. Routing only, with the same routes and URLs.

**Goal:** Move `src/frontend` to React Router 7.18.x with identical routes and behaviour, and clear the 2 remaining moderate advisories.

**Architecture:** Follow React Router's documented v6 → v7 path.
1. On v6, turn on the 2 future flags that apply to a declarative-mode app. This is a separate, small commit, and it proves the behaviour change before the major.
2. Bump to v7 while keeping the `react-router-dom` import path (v7 still publishes it as a re-export of `react-router`).
3. Optionally switch imports to `react-router`.

**Tech Stack:** react-router-dom 6.30.6 → 7.18.x, React 18.2, Vite 7, vitest 4, Playwright.

## Global Constraints

- Owner gates NPM-AUDIT-SCHED ("Any breaking major upgrade comes back to you") and NPM-MAJORS (plan first; the owner approves before running).
- v7 requires Node ≥ 20 and React ≥ 18. Measured: CI uses Node 22 (`ci.yml:64,184`), `package.json` `engines.node` is `>=22`, and React is `^18.2.0`. All are satisfied.
- Frontend only. No backend file, and no route, path or copy change.
- npm and vitest run on **Windows**. E2E runs in CI.
- Explicit pathspecs. Commit trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Measured scope (origin/main `90c502a`, 2026-10-04)

| Item | Measurement | v7 relevance |
|---|---|---|
| Router mode | `src/App.tsx:104` `<BrowserRouter>` + `<Routes>`. `grep createBrowserRouter\|RouterProvider\|useLoaderData\|useFetcher\|<Form\|json(\|defer(` returns 0 | Declarative mode. The data-router breaking changes (`json`/`defer` removal, fetcher persistence, form method, partial hydration, action revalidation) do **not** apply. GHSA-337j is SSR/data-mode only |
| Routes | `App.tsx:107-135`: 2 top-level routes, 1 layout route with 14 path children (`inbox` … `settings`, `medications/:medicationId`) plus the index route, an index `<Navigate to="/inbox" replace>`, and a top-level `path="*"` → `<Navigate to="/" replace>` | `v7_relativeSplatPath` changes relative links **inside** splat routes. The only splat route renders an absolute `Navigate`. `grep` for relative `to=` / `navigate('x')` targets (not starting with `/`) in `src` (excluding tests) returns 0. Variable targets the grep cannot see: `Sidebar.tsx:64`, `SettingsPage.tsx:954` (server-supplied `a.url`, checked only with `startsWith('/')`, which admits `/\x` and `//x`; backend sends literal `/settings`, `environment_diagnostics.py:244`), `TimelinePage.tsx:116`, `SearchPage.tsx:60`, `ExplainAssistant.tsx:596` |
| Lazy routes | 12 routes use `lazyRoute(...)` (11 layout children plus `/recover`, `App.tsx:110`) = `<Suspense>` around `React.lazy` pages (`App.tsx:97-99`) | `v7_startTransition` wraps navigation state updates in `React.startTransition`. With Suspense, the old page stays visible during a lazy load instead of `RouteFallback` when the Suspense boundary is reused (lazy page → lazy page, e.g. `/trends` → `/timeline`); `/inbox` (not lazy) → `/trends` still shows `RouteFallback`. Visible, but not breaking. This is the main behaviour change to check |
| API surface | Imports in 30 files under `src`: `BrowserRouter`, `Routes`, `Route`, `Navigate`, `Outlet`, `Link`, `NavLink`, `useNavigate`, `useLocation`, `useParams`, `useSearchParams`, `MemoryRouter` (tests) | All exist in v7 with the same names. `react-router-dom` stays importable |
| Tests | 13 test files import from `react-router-dom`. 2 files `vi.mock('react-router-dom', …importActual…)`: `ProfileSetup.test.tsx:39` stubs `useNavigate`, `MedicationCorrelations.test.tsx:35` stubs `useParams` | The mocks keep working only while components import from `react-router-dom`. If imports move to `react-router` (Task 3), the mocks must move with them |
| E2E | 7 Playwright spec files (`e2e/*.spec.ts`; `playwright test --list` → 35 tests in 7 files) drive real navigation | CI E2E Smoke is the end-to-end check |
| Transitive deps | `react-router` 6.30.6, `@remix-run/router` 1.23.4 (after PR #38; 6.30.2 / 1.23.1 at `90c502a`) | v7 merges `@remix-run/router` into `react-router`, and adds `cookie` and `set-cookie-parser` (server helpers, unused here). Review the lockfile diff for these |

Re-run before Task 1: `grep -rhoE "import \{[^}]*\} from 'react-router-dom'" src e2e`, `grep -rnE 'path="[^"]*\*' src`, and the relative-target grep below. Use their output, not these numbers.

```bash
cd src/frontend && grep -rnE "(to=|navigate\()\{?['\"\`][^/'\"\`]" src --include=*.tsx | grep -v __tests__   # expect no lines
```

## Review Focus

1. **Suspense fallback timing (`v7_startTransition`).** Navigating to a lazy page now keeps the current page up until the chunk loads. Tests that wait for `RouteFallback`'s `role="status"` can change. `grep -rn 'Loading\|role="status"' src/__tests__` before and after.
2. **Mocked `useNavigate` / `useParams`.** If a component's import path changes and a test mock does not, the mock silently stops intercepting. The test then calls the real `navigate` and may still pass. Task 3 is optional; if it runs, every `vi.mock('react-router-dom')` moves in the same commit.
3. **The future-flag console warnings vanish.** v6 prints "React Router Future Flag Warning" in tests (observed by L1 on 2026-10-04 in the stderr of `ProfileSetup.test.tsx`, `RecoverProfile.test.tsx` and `DangerZone.test.tsx`: both `v7_startTransition` and `v7_relativeSplatPath`). After Task 1 the count must be 0. Measure with `npx vitest run 2>&1 | grep -c "Future Flag"`.
4. **Open-redirect advisory.** After v7, a manual check confirms a crafted `/\evil.example` URL does not navigate off-origin (Task 2 Step 4).
5. **The `*` fallback and `index` redirect** still land on `/inbox` from an unknown path. The new `Routing.test.tsx` (Task 1) covers it; no current e2e spec asserts it.

---

### Task 0: Preconditions (STOP on any failure)

- [ ] **Step 1: Approval.** Approval recorded in owner-decisions naming this plan. Then `git worktree add ../hc-rr7 -b feat/react-router7 origin/main`. PR #38 must be on `origin/main` (`git merge-base --is-ancestor 93def9e origin/main`).
- [ ] **Step 2: Windows baseline.**

```bash
powershell.exe -NoProfile -Command "cd C:\Users\DangT\Documents\GitHub\hc-rr7\src\frontend; npm ci; npm audit 2>&1 | Select-Object -Last 1; npx tsc --noEmit; echo tsc=\$LASTEXITCODE; npm run lint; echo lint=\$LASTEXITCODE; npm run build; echo build=\$LASTEXITCODE; npx vitest run 2>&1 | Tee-Object \$env:TEMP\rr-before.txt | Select-Object -Last 4; (Select-String -Path \$env:TEMP\rr-before.txt -Pattern 'Future Flag').Count"
```

Record the counts, including the Future Flag warning count.

### Task 1: Future flags on v6 (behaviour change, before the major)

- [ ] **Step 1: Failing test first.** Add `src/__tests__/Routing.test.tsx` (new). `App` already contains its `BrowserRouter` (`App.tsx:104`), so do not wrap it in a `MemoryRouter` (nested routers throw) and do not copy the route tree (that would test the copy). Instead: `window.history.pushState({}, '', '/no-such-page')`, stub an authenticated auth store and the API module, render `<App />`, and assert `window.location.pathname` becomes `/inbox`. Also assert that no console warning matching `/Future Flag/` was printed (`vi.spyOn(console, 'warn')`). Run it on v6 without flags and paste the FAIL (the warning is printed).
- [ ] **Step 2: Turn on the flags.** `App.tsx:104`: `<BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>`. Add the same `future` prop to every `MemoryRouter` / `BrowserRouter` in tests that lacks it: 9 files to edit; 4 already pass both flags (`ChartExport.test.tsx:151`, `ExplainAssistant.test.tsx:62`, `MedicationCorrelations.test.tsx:116`, `TrendsDashboard.test.tsx:61`). List with `grep -rln 'MemoryRouter\|BrowserRouter' src/__tests__`.
- [ ] **Step 3: Checks** (Windows): tsc, lint, build, full vitest. The Future Flag warning count is 0. vitest total is baseline + 1.
- [ ] **Step 4: Commit:** `feat(frontend): adopt React Router v7 future flags on v6`.

### Task 2: Bump to v7

- [ ] **Step 1.** `npm install react-router-dom@^7.18.4` (Windows). This is the approved major. Paste the `package.json` diff: only `react-router-dom` moves.
- [ ] **Step 2.** Remove the `future` props added in Task 1. v7 makes those behaviours the default, and its types reject v6 flag names. Run `npx tsc --noEmit` first and paste any type error it reports before removing them.
- [ ] **Step 3: Checks** (Windows): tsc, lint, build, full vitest (same total as after Task 1), and `npm audit`. `react-router` and `react-router-dom` must no longer be listed. Lockfile: `@remix-run/router` is gone. List each new package with its version.
- [ ] **Step 4: Open-redirect check.** In `Routing.test.tsx`, add a test that renders `<Link to={'/\\evil.example'}>` and asserts `new URL(link.getAttribute('href')!, 'http://localhost/').origin === 'http://localhost'` (browsers normalise `\` to `/`, so a raw `/\evil.example` href is `//evil.example`, another origin; a string check for a leading `/` would pass on the vulnerable version). Paste it **RED** on 6.30.6 (checkout the Task 1 commit) and GREEN on 7.18.x. If it is green on 6.30.6, STOP: the test does not reach the advisory.
- [ ] **Step 5: Commit:** `fix(deps): react-router-dom 7.18 (clears GHSA-wrjc-x8rr-h8h6, GHSA-337j-9hxr-rhxg)`.

### Task 3 (optional; the owner decides): imports from `react-router`

- [ ] Replace `from 'react-router-dom'` with `from 'react-router'` in `src` and `e2e`, and move both `vi.mock('react-router-dom', …)` calls to `vi.mock('react-router', …)` in the same commit. Re-run the full vitest suite. Each test that asserts on `mockNavigate` must still see its call, and `MedicationCorrelations.test.tsx` must still get its stubbed `useParams`. Before committing, break each of the 2 mock paths on purpose and confirm its tests go red.

### Task 4: Verification and PR

- [ ] CI 6/6, including E2E Smoke.
- [ ] Manual or e2e check that a lazy page loads without a blank screen in both cases: `/inbox` → `/trends` (fallback shown) and `/trends` → `/timeline` (old page held, then new page).
- [ ] Reviews: `code-reviewer` + `security-reviewer` (the security reviewer re-checks the redirect advisory).

## Stop gates

- No approval recorded.
- `npm install` moves any package other than `react-router-dom` / `react-router` / their own deps.
- A vitest count change other than the planned +1/+2 (`Routing.test.tsx`), or any failure.
- A type error that needs a code change beyond removing the `future` props. Report it.

## Rollback

Task 2 is one commit: `git revert <sha>` it to return to v6 with the flags still on (a stable state). A full revert of the PR (`git revert -m 1 <merge sha>`) restores v6 without flags.

## Out of scope

- Moving to data routers (`createBrowserRouter`, loaders) or framework mode.
- Tailwind 4 (its own plan: [2026-10-04-NPM-MAJORS-tailwind4.md](2026-10-04-NPM-MAJORS-tailwind4.md)).
