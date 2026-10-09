# Wave 4 — L1-D: React Router 7

**PR:** PR_URL_PLACEHOLDER (branch `fix/react-router-7`, base `origin/main` = `f428a99`). Not merged.
**Plan:** [2026-10-04-NPM-MAJORS-react-router7.md](../../../docs/plans/2026-10-04-NPM-MAJORS-react-router7.md) Tasks 0, 1, 2, 4 plus Amendment 1 (Task 3 out).
**Result:** `react-router-dom` 6.30.6 → 7.18.4. `npm audit` 9 → 7; `react-router` and `react-router-dom` no longer listed. vitest 195/34 → 197/35. Playwright chromium list 31/7 → 33/8. Backend not touched (collected delta 0, suite not run).

## Gates used

| Gate | Text (verbatim) | Where |
|---|---|---|
| NPM-MAJORS-RUN | "This approves both NPM-MAJORS plans for execution" | owner-decisions on `main` |
| MAJORS-TIED | "Pre-approve only (a) new packages pulled in by an approved major and (b) major bumps of packages whose sole consumer is that approved major. … Any other major still stops and comes back to you." | owner-decisions on `main` |
| RR7-Q1 | "No, keep -dom" (Task 3 out) | chat 2026-10-09, recorded on branch `docs/wave4-close` (`1349d94`), not on `main` yet |
| RR7-Q2 | "Add a Playwright spec": "One spec for unknown-path redirect and lazy navigation, run in CI every time." | same |
| RR7-Q4 | "Separate owner item" (`SettingsPage.tsx:952-954` untouched) | same |
| Unsigned | `engines.node` `>=22` vs vite `>=22.12.0` (pack Q3) | not needed: nothing blocked; `engines` unchanged |

## Commits

| SHA | Subject |
|---|---|
| `651390e` | docs: amend React Router 7 plan for execution (counts, gates, lockfile diff, e2e spec) |
| `2bf244c` | feat(frontend): adopt React Router v7 future flags on v6 |
| `175fc87` | fix(deps): react-router-dom 7.18 (clears GHSA-wrjc-x8rr-h8h6, GHSA-337j-9hxr-rhxg) |
| `09ae6a1` | fix(frontend): e2e spec for unknown-path redirect and lazy navigation |
| `e754b5d` | fix(frontend): address RR7 review nits in routing tests |
| `512218b` | docs: record RR7 open-redirect test change and correct the e2e description |

Net diff against `origin/main`: plan, `package.json` (1 line), `package-lock.json`, `src/__tests__/Routing.test.tsx` (new), `e2e/routing.spec.ts` (new), 4 test files losing their `future` prop (`ChartExport`, `ExplainAssistant`, `MedicationCorrelations`, `TrendsDashboard`), this report. `App.tsx` and the 11 Task-1 test files net to zero (flags added on v6, removed after the bump). No product source file changes.

## Task 0 (L1, Windows, node v22.20.0, npm 11.6.2, clean `npm ci` at `f428a99`)

- Ancestry: `git merge-base --is-ancestor 93def9e origin/main` → 0; `c4d407e` → 0; NPM-AUDIT-2 #52 is `f428a99` itself.
- Scope greps: 32 importers (15 tests), 3 `vi.mock('react-router-dom')` files (`MedicationCorrelations`, `ProfileSetup`, `RecoverProfile`), relative-target grep 0 lines, 1 product splat route (`App.tsx:134`), 11 test files needing the `future` prop, 4 already having it. Matches the readiness pack.
- `npmci=0 tsc=0 lint=0` (0 errors, 5 warnings) `build=0`, vitest `Test Files 34 passed (34)`, `Tests 195 passed (195)`, `vitest=0`. Future Flag lines 44.
- `npm audit`: `{"moderate":4,"high":5,"total":9}`: braces, chokidar, fast-glob, micromatch, tailwindcss (high); postcss-nested, postcss-selector-parser, react-router, react-router-dom (moderate).
- `npx playwright test --list --project chromium` → `Total: 31 tests in 7 files`; all projects → `Total: 36 tests in 8 files`.

## Task 1 (implementer, Windows)

- RED, `Routing.test.tsx` on v6 without flags: `AssertionError: expected [ …(2) ] to deeply equal []` (both Future Flag warnings), `vitest=1`.
- GREEN with flags; full suite 196/35, `vitest=0`, Future Flag lines 0, `tsc=0 lint=0 build=0`.
- Break-it: `path="*"` route deleted → `Expected: "/inbox"  Received: "/no-such-page"`, `vitest=1`. Restored.

## Task 2 (implementer, Windows)

- `npm install react-router-dom@^7.18.4` exit 0. `package.json` diff: `"react-router-dom": "^6.21.0"` → `"^7.18.4"` only.
- `tsc` before removing the flags: only `TS2322 Property 'future' does not exist` errors in tests. After removing: `tsc=0 lint=0 build=0`.
- Open-redirect test changed (plan amended in `512218b`): the plan's `<Link>` href-origin test was RED on both 6.30.6 and 7.18.4, because v7 renders a `//`- or `/\`-prefixed `to` as an external anchor by design. `HC-ROUTE-002` tests `useNavigate('/\\evil.example')` instead: RED on 6.30.6 (pushState got `"/\\evil.example"`, `expected 'http://evil.example' to be 'http://localhost'`, `vitest=1`), GREEN on 7.18.4 (navigate throws `External navigation is not allowed`, no pushState), `vitest=0`.
- The Future Flag half of `HC-ROUTE-001` was removed in `e754b5d` (code review: "Future Flag" does not occur in react-router 7, so it could not fail any more).

## Final acceptance (L1, Windows, clean `npm ci` at `09ae6a1`; vitest and tsc re-run at `512218b`)

```
powershell.exe -NoProfile -Command "cd C:\Users\DangT\Documents\GitHub\hc-rr7\src\frontend; \$f = 0; Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue; npm ci …; echo npmci=\$LASTEXITCODE; … npx tsc --noEmit; echo tsc=\$LASTEXITCODE; … npm run lint; echo lint=\$LASTEXITCODE; … npm run build; echo build=\$LASTEXITCODE; … npx vitest run …; echo vitest=\$LASTEXITCODE; … echo failed=\$f; exit \$f"; echo acceptance=$?
```

| Check | Output |
|---|---|
| npm ci | `npmci=0` |
| tsc | `tsc=0` |
| lint | `✖ 5 problems (0 errors, 5 warnings)`, `lint=0` |
| build | `✓ built in 36.07s`, `build=0` |
| vitest (at `09ae6a1`) | `Test Files 35 passed (35)`, `Tests 197 passed (197)`, `vitest=0` |
| vitest (at `512218b`) | `Test Files 35 passed (35)`, `Tests 197 passed (197)`, `vitest=0`; `tsc=0` |
| Future Flag lines | 0 (was 44) |
| all | `failed=0`, `acceptance=0` |
| npm audit | `{"moderate":2,"high":5,"total":7}`: braces, chokidar, fast-glob, micromatch, tailwindcss (high); postcss-nested, postcss-selector-parser (moderate) |
| Playwright list | chromium `Total: 33 tests in 8 files`; all projects `Total: 38 tests in 9 files` |
| Linux natives in lock | `grep -c '"node_modules/@rollup/rollup-linux-x64-gnu"\|"node_modules/@esbuild/linux-x64"'` → 2 |

## Lockfile diff

Script extracted from [NPM-audit-fix Amendment 2](../../../docs/plans/2026-10-04-NPM-audit-fix.md) rule 4, sha256 `6b56ea18e220fce972f1d1ce2539d640faf70caafabd9d52c7ed5fb7750c1221`, interpreter `python3` (Python 3.12.3, WSL), `origin/main` lock vs committed `HEAD` lock (`175fc87` onward):

```
packages keys: old=485 new=486
ADDED (2)
  node_modules/cookie 1.1.1
  node_modules/set-cookie-parser 2.7.2
REMOVED (1)
  node_modules/@remix-run/router 1.23.4
CHANGED, any field (2)
  node_modules/react-router 6.30.6 -> 7.18.4 fields=['dependencies', 'engines', 'integrity', 'peerDependencies', 'peerDependenciesMeta', 'resolved', 'version'] MAJOR
  node_modules/react-router-dom 6.30.6 -> 7.18.4 fields=['dependencies', 'engines', 'integrity', 'peerDependencies', 'resolved', 'version'] MAJOR
hasInstallScript: old=['node_modules/esbuild', 'node_modules/fsevents', 'node_modules/playwright/node_modules/fsevents']
hasInstallScript GAINED: []
source shape: 486/486 entries are the registry.npmjs.org tarball of their own name and version, sha512
STOP-FLAGS: 8
  STOP ROOT-OR-TOP-LEVEL-CHANGED (package.json ranges, engines, name, lockfileVersion or a key beside packages)
  STOP MAJOR node_modules/react-router 6.30.6 -> 7.18.4
  STOP UNEXPECTED-FIELDS node_modules/react-router fields=['dependencies', 'engines', 'integrity', 'peerDependencies', 'peerDependenciesMeta', 'resolved', 'version']
  STOP MAJOR node_modules/react-router-dom 6.30.6 -> 7.18.4
  STOP UNEXPECTED-FIELDS node_modules/react-router-dom fields=['dependencies', 'engines', 'integrity', 'peerDependencies', 'resolved', 'version']
  STOP NEW-NAME node_modules/cookie 1.1.1
  STOP NEW-NAME node_modules/set-cookie-parser 2.7.2
  STOP MAJOR-RESOLUTION node_modules/@remix-run/router: lines before=['1'] after=[]
lockdiff=1
```

Classification of all 8 flags against MAJORS-TIED (measured with a second `python3` pass over the same two files):

| Flag | Measurement | Rule |
|---|---|---|
| ROOT changed | root differs only in `dependencies.react-router-dom` `^6.21.0` → `^7.18.4`; no top-level key differs | the approved major |
| react-router-dom MAJOR + fields | the approved major | NPM-MAJORS-RUN |
| react-router MAJOR + fields | sole dependent in the new lock: `node_modules/react-router-dom`; not a root dependency | MAJORS-TIED (b) |
| cookie NEW-NAME | sole dependent: `node_modules/react-router` | MAJORS-TIED (a) |
| set-cookie-parser NEW-NAME | sole dependent: `node_modules/react-router` | MAJORS-TIED (a) |
| @remix-run/router removed | was only used by react-router 6 / react-router-dom 6; v7 inlines it | dropped by the approved major |

No flag outside the approved major. Security review confirmed lock integrity = `npm view` `dist.integrity` for all 4 new/changed entries; react-router and react-router-dom are published by GitHub Actions trusted publishing; no install scripts.

## E2E spec (RR7-Q2)

`src/frontend/e2e/routing.spec.ts`: `E2E-ROUTE-001` (authenticated `/no-such-page` → `/inbox`, "Document Inbox" heading) and `E2E-ROUTE-002` (MutationObserver flags any moment `<main>` has empty text; `/inbox` → `/trends` → `/timeline` by sidebar click).

Run by L1 on Linux (WSL, ext4 git worktree of the branch, `npm ci` there, node v26.10.0, backend `HC_E2E_BACKEND_PYTHON=~/venvs/asclexis-311/bin/python`, `CI=1`, `--retries=0`):

| Run | Command | Result |
|---|---|---|
| at `09ae6a1` | `npx playwright test e2e/routing.spec.ts --project chromium --reporter=line --retries=0` | `2 passed (4.7m)`, `pw=0` (first run compiles the dev server) |
| break-it: `lazyRoute` fallback `<RouteFallback />` → `null` in `App.tsx` (Linux copy only, not committed) | same | `E2E-ROUTE-002` FAILED: `expect(empty).toBe(false)` `Expected: false` `Received: true` at `routing.spec.ts:59`; `1 failed, 1 passed`, `pw=1`. Restored with `git checkout`. |
| at `512218b` (final) | same | `2 passed (12.3s)`, `pw=0` |

The backend log in these runs printed `sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) disk I/O error` from a background commit; both tests still passed. Not investigated (backend, out of scope); CI is the authoritative E2E run.

## Reviews

| Reviewer | Verdict | Findings | Disposition |
|---|---|---|---|
| code-reviewer (opus) | APPROVE WITH NITS | M1 leftover `console.log` in `Routing.test.tsx`; M2 Future Flag half of HC-ROUTE-001 cannot fail on v7; L3 dev-server timeout on headings; L4 plan/spec text said "reused boundary, old page held"; L5 SettingsPage v7 behaviour | M1, M2, L3 fixed in `e754b5d`; L4 fixed in `e754b5d` + `512218b`; L5 open (RR7-Q4) |
| security-reviewer (opus) | APPROVE | 0 critical/high/medium. LOW: `console.log` (fixed); LOW: Link→navigate test change not recorded (fixed in `512218b`). Advisory fix confirmed in installed code (`validateNavigationTarget`). 4 other variable targets are constants; `services/api.ts` not in diff | done |

## Open findings

1. **RR7-Q4 (separate owner item):** `SettingsPage.tsx:952-954` accepts a server-supplied `a.url` after only `startsWith('/')`. On v7 a `//host` or `/\host` value renders a plain off-origin `<a href>` (v6 also reached another origin on click). Only producer today: the constant `"/settings"` in `environment_diagnostics.py`. Suggested fix for that PR: also reject `/^[\\/]{2}/`.
2. `cookie` and `set-cookie-parser` are imported only by react-router's server-side session helpers; tree-shaking out of the client bundle is expected (`sideEffects: false`) but was not confirmed by inspecting the build output.
3. Existing installs keep react-router-dom 6 until DEV-PS1-INSTALL lands (pack risk 6); v6 without flags still runs.
4. `engines.node` `>=22` vs vite `>=22.12.0` (pack Q3) stays unsigned; nothing in this phase needed it.
5. WSL E2E backend logged an sqlite `disk I/O error` (see above); not seen as a test failure.

## Not run

- Backend pytest (no backend file changed; collected delta 0).
- Playwright on Windows (no SQLCipher backend there); the full Playwright suite locally (only `routing.spec.ts` was run, on Linux). CI "E2E Smoke Tests" runs the whole chromium project.
- Codex plan/diff review (not architectural; not requested in this brief).
- Inspection of the production bundle for `cookie` / `set-cookie-parser`.

## Merge notes

- One PR; humans merge. Rollback: `git revert -m 1 <merge sha>` restores v6 without flags. Reverting only `175fc87` would conflict with `e754b5d` (both edit `Routing.test.tsx`).
- Overlaps (pack §5): Tailwind 4 rebases after this on `package.json` / `package-lock.json`; W-3 edits `TrendsDashboard.test.tsx` (this PR changes its `future` prop line).
