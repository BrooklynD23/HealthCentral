# NPM-MAJORS (b) — React Router 6 → 7 Migration Plan

> **For agentic workers:** this plan is **not approved for execution**. Owner gate NPM-MAJORS: "Plans for both migrations this wave; they come back to the owner before running." Do not start Task 0 until owner-decisions records an approval naming this file.

**Status:** plan only, written 2026-10-04 by L1-B (Wave 3). Approval pending.
**Source:** NPM-AUDIT PR #38. After `npm audit fix`, `react-router` / `react-router-dom` 6.30.6 still carry 2 moderate advisories: GHSA-wrjc-x8rr-h8h6 (open redirect via a backslash in `<Link>` / `useNavigate`) and GHSA-337j-9hxr-rhxg (constructor injection in `deserializeErrors()` during SSR hydration). npm's only fix is `react-router-dom@7.18.4`, a semver-major. PR #38's security review rated both LOW and not reachable today: every navigation target is built by the app with a literal leading `/`, and the app uses declarative `BrowserRouter` with no SSR.
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
| Routes | `App.tsx:107-134`: 2 top-level routes, 1 layout route with 15 children (`inbox` … `settings`, `medications/:medicationId`), an index `<Navigate to="/inbox" replace>`, and a top-level `path="*"` → `<Navigate to="/" replace>` | `v7_relativeSplatPath` changes relative links **inside** splat routes. The only splat route renders an absolute `Navigate`. `grep` for relative `to=` / `navigate('x')` targets (not starting with `/`) in `src` (excluding tests) returns 0 |
| Lazy routes | 11 children are `lazyRoute(...)` = `<Suspense>` around `React.lazy` pages (`App.tsx:97-99`) | `v7_startTransition` wraps navigation state updates in `React.startTransition`. With Suspense, the old page stays visible during a lazy load instead of `RouteFallback` showing. Visible, but not breaking. This is the main behaviour change to check |
| API surface | Imports in 30 files under `src`: `BrowserRouter`, `Routes`, `Route`, `Navigate`, `Outlet`, `Link`, `NavLink`, `useNavigate`, `useLocation`, `useParams`, `useSearchParams`, `MemoryRouter` (tests) | All exist in v7 with the same names. `react-router-dom` stays importable |
| Tests | 13 test files import from `react-router-dom`. 2 files `vi.mock('react-router-dom', …importActual…)` to stub `useNavigate` (`ProfileSetup.test.tsx`, `SearchPage.test.tsx`) | The mocks keep working only while components import from `react-router-dom`. If imports move to `react-router` (Task 3), the mocks must move with them |
| E2E | 7 Playwright spec files (`e2e/*.spec.ts`; `playwright test --list` → 35 tests in 7 files) drive real navigation | CI E2E Smoke is the end-to-end check |
| Transitive deps | `react-router` 6.30.6, `@remix-run/router` 1.23.4 | v7 merges `@remix-run/router` into `react-router`, and adds `cookie` and `set-cookie-parser` (server helpers, unused here). Review the lockfile diff for these |

Re-run before Task 1: `grep -rhoE "import \{[^}]*\} from 'react-router-dom'" src e2e`, `grep -rnE 'path="[^"]*\*' src`, and the relative-target grep below. Use their output, not these numbers.

```bash
cd src/frontend && grep -rnE "(to=|navigate\()\{?['\"\`][^/'\"\`]" src --include=*.tsx | grep -v __tests__   # expect no lines
```

## Review Focus

1. **Suspense fallback timing (`v7_startTransition`).** Navigating to a lazy page now keeps the current page up until the chunk loads. Tests that wait for `RouteFallback`'s `role="status"` can change. `grep -rn 'Loading\|role="status"' src/__tests__` before and after.
2. **Mocked `useNavigate`.** If a component's import path changes and a test mock does not, the mock silently stops intercepting. The test then calls the real `navigate` and may still pass. Task 3 is optional; if it runs, every `vi.mock('react-router-dom')` moves in the same commit.
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

- [ ] **Step 1: Failing test first.** Add `src/__tests__/Routing.test.tsx` (new). Render `App`'s route tree in a `MemoryRouter initialEntries={['/no-such-page']}` with a stubbed authenticated store, and assert the location ends at `/inbox`. Also assert that no console warning matching `/Future Flag/` was printed (`vi.spyOn(console, 'warn')`). Run it on v6 without flags and paste the FAIL (the warning is printed).
- [ ] **Step 2: Turn on the flags.** `App.tsx:104`: `<BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>`. Add the same `future` prop to every `MemoryRouter` / `BrowserRouter` in tests (13 files; list them with `grep -rln 'MemoryRouter\|BrowserRouter' src/__tests__`).
- [ ] **Step 3: Checks** (Windows): tsc, lint, build, full vitest. The Future Flag warning count is 0. vitest total is baseline + 1.
- [ ] **Step 4: Commit:** `feat(frontend): adopt React Router v7 future flags on v6`.

### Task 2: Bump to v7

- [ ] **Step 1.** `npm install react-router-dom@^7.18.4` (Windows). This is the approved major. Paste the `package.json` diff: only `react-router-dom` moves.
- [ ] **Step 2.** Remove the `future` props added in Task 1. v7 makes those behaviours the default, and its types reject v6 flag names. Run `npx tsc --noEmit` first and paste any type error it reports before removing them.
- [ ] **Step 3: Checks** (Windows): tsc, lint, build, full vitest (same total as after Task 1), and `npm audit`. `react-router` and `react-router-dom` must no longer be listed. Lockfile: `@remix-run/router` is gone. List each new package with its version.
- [ ] **Step 4: Open-redirect check.** In `Routing.test.tsx`, add a test that a `<Link to={'/\\evil.example'}>` resolves to a same-origin `href` (it starts with `/` and has no `//` host). Observe it on 6.30.6 first (checkout the Task 1 commit, run, record the result), then on 7.18.x.
- [ ] **Step 5: Commit:** `fix(deps): react-router-dom 7.18 (clears GHSA-wrjc-x8rr-h8h6, GHSA-337j-9hxr-rhxg)`.

### Task 3 (optional; the owner decides): imports from `react-router`

- [ ] Replace `from 'react-router-dom'` with `from 'react-router'` in `src` and `e2e`, and move both `vi.mock('react-router-dom', …)` calls to `vi.mock('react-router', …)` in the same commit. Re-run the full vitest suite. Each test that asserts on `mockNavigate` must still see its call. Before committing, break one mock path on purpose and confirm its test goes red.

### Task 4: Verification and PR

- [ ] CI 6/6, including E2E Smoke.
- [ ] Manual or e2e check that a lazy page (for example `/trends`) loads after navigation from `/inbox`, without a blank screen.
- [ ] Reviews: `code-reviewer` + `security-reviewer` (the security reviewer re-checks the redirect advisory).

## Stop gates

- No approval recorded.
- `npm install` moves any package other than `react-router-dom` / `react-router` / their own deps.
- A vitest count change other than the planned +1/+2 (`Routing.test.tsx`), or any failure.
- A type error that needs a code change beyond removing the `future` props. Report it.

## Rollback

Task 2 is one commit: `git revert` it to return to v6 with the flags still on (a stable state). A full revert of the PR restores v6 without flags.

## Out of scope

- Moving to data routers (`createBrowserRouter`, loaders) or framework mode.
- Tailwind 4 (its own plan: [2026-10-04-NPM-MAJORS-tailwind4.md](2026-10-04-NPM-MAJORS-tailwind4.md)).
