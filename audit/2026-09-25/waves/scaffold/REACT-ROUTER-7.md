**READY (serial after NPM-AUDIT-2)**

# React Router 7 — readiness pack (scaffold, not an execution record)

## 1. Readiness verdict

**READY (serial after NPM-AUDIT-2)** — Tasks 0-2 and 4. Task 3 (move imports to `react-router`) is "optional; the owner decides" in the plan and has no recorded answer, so it stays out of the dispatch unless Q1 is answered.

- Gate: NPM-MAJORS-RUN, signed 2026-10-07 (`docs/capstone-report/owner-decisions-2026-09-27.md:64`): "This approves both NPM-MAJORS plans for execution".
- Hard dependency: NPM-AUDIT PR #38 is on `origin/main`.
- Order constraint (not a code blocker): NPM-AUDIT-2 merges first; both rewrite `src/frontend/package-lock.json`.
- Pre-dispatch process steps the owner directed: Codex plan review (ledger `:193`) and a Fable adversarial review of the briefs (ledger `:194`).

Scaffold written 2026-10-07 in worktree `hc-scaffold` (HEAD `8d6f02e`, `origin/main` = `6b4dd84`). No `npm`, vitest or Playwright was run.

## 2. Task 0 evidence (measured 2026-10-07)

| Check | Command | Result |
|---|---|---|
| NPM-AUDIT #38 merged | `git merge-base --is-ancestor c4d407e origin/main; echo $?` | `0` |
| Plan's own check | `git merge-base --is-ancestor 93def9e origin/main; echo $?` | `0` |
| NPM-AUDIT-2 merged | no branch or PR exists yet | **not started** (order constraint) |
| Plan file | `git ls-files docs/plans/2026-10-04-NPM-MAJORS-react-router7.md` | non-empty (PR #43, `22491e2`) |
| Gate NPM-MAJORS-RUN | `owner-decisions-2026-09-27.md:64` | **signed**. The row names "React Router 7" and "both NPM-MAJORS plans (plans in PR #43)"; it does not quote the file path. Plan Task 0 Step 1 asks for "an approval naming this plan" |
| Gate NPM-MAJORS (plan-first) | `owner-decisions-2026-09-27.md:55` | signed 2026-10-04; satisfied by PR #43 |
| Task 3 (imports from `react-router`) | — | **UNSIGNED** (Q1) |
| Codex model IDs "6.1 sol" / "6-luna high" | ledger `:193` | owner text recorded; IDs **unconfirmed** (L0 note says confirm before first use) |

`src/frontend/package.json` (read, not run):

| Field | `package.json` | `package-lock.json` |
|---|---|---|
| `engines.node` | `>=22` | root `>=22` |
| react-router-dom | `^6.21.0` | 6.30.6 |
| react-router / `@remix-run/router` | transitive | 6.30.6 / 1.23.4 |
| react | `^18.2.0` | 18.3.1 |
| tailwindcss / tailwind-merge | `^3.4.1` / `^2.2.0` | 3.4.19 / 2.6.0 |
| vite | `^7.3.0` | 7.3.6 (needs Node `^20.19.0 \|\| >=22.12.0`) |
| vitest | `^4.0.16` | 4.1.11 |
| `@tailwindcss/*` | none | none |
| `cookie`, `set-cookie-parser` | — | not in the lock today |

## 3. Owner questions still to ask

**Q1. Task 3: move imports from `react-router-dom` to `react-router`?**
- A. **(recommended)** No. Keep `react-router-dom`; v7 still publishes it. Diff stays at `App.tsx`, tests and the lockfile. 3 `vi.mock('react-router-dom')` calls keep working untouched.
- B. Yes, in the same PR as Task 3: 32 files change import paths and all 3 mocks move in one commit, each broken on purpose once.
- C. Yes, as a separate follow-up PR after Tailwind 4.

**Q2. E2E evidence and the lazy-route check (Task 4).** Playwright cannot run against an encrypted backend on Windows.
- A. **(recommended)** CI "E2E Smoke Tests" on the PR (chromium, 31 tests listed 2026-10-07) plus the new `Routing.test.tsx`. The `/trends` → `/timeline` held-page check is done by L1 on a Linux run with `HC_E2E_CHROMIUM_PATH`, or recorded as skipped with the reason.
- B. Add one Playwright spec for unknown-path → `/inbox` and lazy navigation, run in CI. Raises the Playwright count by 1-2 (the plan adds no e2e spec, so this is a scope change).
- C. Manual check by you in the dev app before merge.

**Q3. `engines.node` `>=22` vs vite 7.3.6's `>=22.12.0`.** Same question as NPM-AUDIT-2 Q4; ask once. If it was answered there, nothing to ask here. React Router 7 itself needs Node ≥ 20 (plan `:17`), which `>=22` satisfies.

**Q4. `SettingsPage.tsx:952-954` navigates to a server-supplied `a.url` after only `startsWith('/')`** (admits `/\x` and `//x`; backend sends the literal `/settings` today). The plan lists it but does not change it.
- A. **(recommended)** Leave it out of this PR (plan says no behaviour change); the v7 bump is the fix for the `<Link>` backslash advisory, and the security reviewer re-checks this call site.
- B. Tighten the check in this PR (1 line + 1 test). Scope change.
- C. Register as its own owner item.

## 4. Plan drift check (`docs/plans/2026-10-04-NPM-MAJORS-react-router7.md`, measured at `90c502a`)

Tally: **MATCH 16, MOVED 1, CHANGED 6, UNMEASURED 1.** No router source file changed since the plan's base; every change comes from RCC-2 (#42) and G-C3b (#45).

| # | Plan cites | Now (worktree at `6b4dd84` + docs) | Verdict |
|---|---|---|---|
| 1 | `App.tsx:104` `<BrowserRouter>` | same line | MATCH |
| 2 | data-router grep returns 0 | 0 | MATCH |
| 3 | Routes `App.tsx:107-135`: 2 top-level, 1 layout with 14 path children + index, `*` fallback | `:107-134`; 14 children counted; `*` at `:134` | MATCH |
| 4 | relative-target grep returns 0 lines | 0 | MATCH |
| 5 | `Sidebar.tsx:64` `to={item.to}` | same | MATCH |
| 6 | `SettingsPage.tsx:954` `to={a.url}` (check at `:952`) | same | MATCH |
| 7 | `environment_diagnostics.py:244` `url="/settings"` | same | MATCH |
| 8 | `TimelinePage.tsx:116`, `SearchPage.tsx:60` `to={meta.link}` | same | MATCH |
| 9 | `ExplainAssistant.tsx:596` `navigate(target)` | same | MATCH |
| 10 | 12 lazy routes; `/recover` at `App.tsx:110`; `lazyRoute` `:97-99` | same | MATCH |
| 11 | "Imports in **30** files under `src`" | **32** (`grep -rl "react-router-dom" src/frontend/src \| wc -l`). New: `__tests__/DangerZone.test.tsx`, `__tests__/RecoverProfile.test.tsx` (`145fe77`, RCC-2 #42). Non-test importers: 17 | CHANGED |
| 12 | 12 imported symbols | same 12 (`BrowserRouter` 10, `useNavigate` 10, `Link` 7, `MemoryRouter` 6, …) | MATCH |
| 13 | "**13** test files import" | **15** | CHANGED |
| 14 | "**2** files `vi.mock('react-router-dom')`" | **3**: new `RecoverProfile.test.tsx:35` stubs `useNavigate` (`145fe77`, #42) | CHANGED |
| 15 | `ProfileSetup.test.tsx:39` | now `:44` (`145fe77`, `4448ec9`, `dd8edb6`) | MOVED |
| 16 | `MedicationCorrelations.test.tsx:35` | same | MATCH |
| 17 | E2E "7 spec files; 35 tests in 7 files" | **8** spec files; L0 2026-10-07: 36 tests in 8 files (all projects), 31 in 7 files (chromium). New `e2e/health-smoke.spec.ts` (`564eb41`, G-C3b #45) | CHANGED |
| 18 | `react-router` 6.30.6, `@remix-run/router` 1.23.4 | same | MATCH |
| 19 | CI Node 22 `ci.yml:64,184`; `engines.node >=22`; React `^18.2.0` | same | MATCH |
| 20 | Task 1 Step 2: "**9** files to edit; 4 already pass both flags" at `ChartExport.test.tsx:151`, `ExplainAssistant.test.tsx:62`, `MedicationCorrelations.test.tsx:116`, `TrendsDashboard.test.tsx:61` | The 4 lines match. Files with a router and no `future` prop: **11** (adds `DangerZone.test.tsx`, `RecoverProfile.test.tsx`; `BackupRestoreFlow.test.tsx` was already in the 9) | CHANGED |
| 21 | Review Focus 3: Future Flag warnings seen in 3 test files' stderr | not run | UNMEASURED |
| 22 | Task 0 `93def9e` ancestor | `0` | MATCH |
| 23 | `:3`, `:5` "not approved for execution… Approval pending" | approved by `owner-decisions:64` | CHANGED (status text stale) |
| 24 | Tech stack 6.30.6, Vite 7, vitest 4, Playwright | 6.30.6, 7.3.6, 4.1.11, `@playwright/test` 1.58.1 | MATCH |

Not cited by the plan, checked for this pack:
- `src/frontend/src/services/api.ts:55-70` (401 handling) uses `window.location.replace`, not the router, and does not import `react-router-dom`. The migration does not touch it.
- `main.tsx` holds no router; the only `BrowserRouter` in product code is `App.tsx:104`.
- vitest baseline: 195 tests in 34 files (L0, Windows, 2026-10-07). The plan gives no number and says to measure.
- CI frontend job: `npm ci`, `tsc --noEmit`, `vitest run` only (`ci.yml:55-78`); no build or lint step.

Tailwind-side counts (for the sequence): `@apply` 4 lines in 1 file, `theme(` 0, config-token files 53. This phase edits none.

**Plan amendments needed (do not edit the plan here):**
1. Scope table: 30 → 32 importing files, 13 → 15 test files, 2 → 3 mocked files (add `RecoverProfile.test.tsx:35`; `ProfileSetup.test.tsx:44`).
2. Task 1 Step 2: 9 → 11 files to edit.
3. Task 3: "both `vi.mock` calls" → all 3; break-it each of the 3.
4. E2E row: 8 spec files; CI runs chromium (31 listed).
5. Task 0 Step 1: name `owner-decisions:64` (NPM-MAJORS-RUN) as the approval, and add "NPM-AUDIT-2 merged" as a precondition.
6. Status header (`:3`, `:5`): approved 2026-10-07.
7. Stop gate "vitest count change other than the planned +1/+2": state the absolute expected totals from the Task 0 baseline (195 → 196 after Task 1 → 197 after Task 2 Step 4, if NPM-AUDIT-2 leaves 195).

## 5. File ownership

| File | Task | Change |
|---|---|---|
| `src/frontend/src/__tests__/Routing.test.tsx` | 1, 2 | **new** (fallback → `/inbox`, no Future Flag warning; then the open-redirect origin test) |
| `src/frontend/src/App.tsx` | 1, 2 | `future` prop added at `:104`, removed again after the bump |
| 11 test files under `src/frontend/src/__tests__/` | 1, 2 | `future` prop on `MemoryRouter` / `BrowserRouter` added, then removed: `Accessibility`, `BackupRestoreFlow`, `DangerZone`, `DocumentInbox`, `EntityCitationDeepLink`, `ExportPage`, `NotificationSettingsPage`, `ProfileSetup`, `RecoverProfile`, `SearchPage`, `VerificationWorkbench` (`.test.tsx`) |
| 4 test files that already pass flags | 2 | `future` prop removed: `ChartExport`, `ExplainAssistant`, `MedicationCorrelations`, `TrendsDashboard` (`.test.tsx`) |
| `src/frontend/package.json` | 2 | `react-router-dom` `^6.21.0` → `^7.18.4` only |
| `src/frontend/package-lock.json` | 2 | `@remix-run/router` removed; `react-router` 7.x; `cookie`, `set-cookie-parser` expected new |
| 17 non-test importers + 15 tests + 3 mocks | 3 (only if Q1 = B) | import path `react-router-dom` → `react-router` |

Overlap with undone phases:

| Phase | Shared file | Risk |
|---|---|---|
| NPM-AUDIT-2 | `package-lock.json`, `package.json` | serial, before |
| Tailwind 4 | `package-lock.json`, `package.json`; `App.tsx` (class renames in `RouteFallback` `:82-92`); every `.tsx` it renames classes in | serial, after |
| **W-3** | `__tests__/TrendsDashboard.test.tsx` (W-3 edits it; this phase removes its `future` prop at `:61`). `TrendsDashboard.tsx`, `InterpretedTrendChart.tsx`, `services/types.ts` are not touched by Tasks 1-2 | textual merge conflict in one test file; whichever merges second rebases |
| **W-2** | `__tests__/ExportPage.test.tsx` gets a `future` prop here; W-2 cites `pages/ExportPage.tsx:108-121`. `ExportPage.tsx` does not import the router | low; only if W-2 edits the test |
| W-4 | cites `pages/ExplainAssistant.tsx:213,234` (evidence, not an edit in its file table); this phase touches `ExplainAssistant.test.tsx:62` only | none expected |
| W-11a PR-3 | may add build / lint to `ci.yml`; `package.json` is on its stop list | none |
| P7, W-11a PR-1 | `e2e/support/auth.ts:51` (cited); not touched here | none |
| P5, P6, W-7, W-8, W-10, W-10b, G-C1, G-C2, G-C3a, G-C5, P4-deferred, AUDIT-ORDER, PROHIBITED-PARAPHRASE | no frontend router file | none |

If Q1 = B, Task 3 adds `pages/VerificationWorkbench.tsx` (W-3 cites it), `pages/ExplainAssistant.tsx` (W-4 cites it) and `pages/SettingsPage.tsx`, `pages/ProfileSetup.tsx` (P4 checks them by grep) to the overlap.

Backend files: none. Backend collected delta expected **0** (1370).

## 6. Briefs

### 6.1 L1 brief (frontend sequence, phase 2 of 3)

```
You are the L1 Wave Orchestrator for the Wave 4 frontend sequence of the
Asclexis execution program. Follow docs/agentic/orchestration.md §3 exactly;
you are L1. This brief covers phase 2 of 3.
Phase: React Router 7 — docs/plans/2026-10-04-NPM-MAJORS-react-router7.md,
Tasks 0, 1, 2, 4 <and 3 only if the owner answered Q1 = B>. Read
audit/2026-09-25/waves/scaffold/REACT-ROUTER-7.md §4 first: the plan's
counts are stale (32 importing files, 15 test files, 3 mocks, 11 files to
edit in Task 1 Step 2, 8 e2e spec files).
Base: origin/main @ <sha>. Confirmed merged dependencies: NPM-AUDIT PR #38
(c4d407e), NPM-AUDIT-2 PR #<n> (<sha>; verify with
`git merge-base --is-ancestor <sha> origin/main`). If NPM-AUDIT-2 is not on
origin/main: STOP.
Signed gate (verbatim, owner-decisions:64): "NPM-AUDIT-2, then React Router 7,
then Tailwind 4, each as its own PR. Largest frontend churn of the three."
This approves both NPM-MAJORS plans for execution.
Unsigned: Task 3 (imports from `react-router`) <Q1 answer>; any behaviour
change to SettingsPage.tsx:952-954 <Q4 answer>. A task that needs one STOPS.
Architectural: not in orchestration §5. Owner-directed for this phase
anyway (ledger 2026-10-07): (1) Codex PLAN review before Task 1, model
"6.1 sol", fallback "6-luna" at high effort (confirm the IDs with `codex`
first), handoff §7 procedure, at most 2 rounds, outputs under
audit/2026-09-25/reviews/RR7-r<N>-*; verify each finding against the code
and commit accepted plan amendments as the first commit on the branch;
(2) L0 has run a Fable adversarial review of this brief (findings: <path>).
Also run the Codex diff review before the PR opens (handoff §7.2), focus:
"same routes and URLs; no off-origin navigation; mocks still intercept".
Worktree ../hc-rr7, branch feat/react-router7, one PR.
Spawn one implementer: Agent(subagent_type="general-purpose",
model="sonnet") with the brief below. Reviewers:
Agent(subagent_type="code-reviewer", model="opus") and
Agent(subagent_type="security-reviewer", model="opus") (the plan requires
it: re-check GHSA-wrjc-x8rr-h8h6 and the 5 variable navigation targets;
services/api.ts 401 handling is NOT in the diff — confirm it stays out).
Run the acceptance yourself, FROM WINDOWS, NOT WSL:
  powershell.exe -NoProfile -Command "cd C:\Users\DangT\Documents\GitHub\hc-rr7\src\frontend; Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue; npm ci; npm audit 2>&1 | Select-Object -Last 8; npx tsc --noEmit; echo tsc=$LASTEXITCODE; npm run lint; echo lint=$LASTEXITCODE; npm run build; echo build=$LASTEXITCODE; npx vitest run 2>&1 | Tee-Object $env:TEMP\rr-after.txt | Select-Object -Last 6; (Select-String -Path $env:TEMP\rr-after.txt -Pattern 'Future Flag').Count"
  npx playwright test --list --project chromium   (count only; Windows)
E2E run: <Q2 answer; default CI "E2E Smoke Tests" on the PR>.
Tests this phase adds: 2 vitest tests in 1 new file
(src/__tests__/Routing.test.tsx): baseline + 1 after Task 1, baseline + 2
after Task 2 Step 4 (195/34 → 197/35 if the Task 0 baseline is still
195/34; use the measured baseline). Playwright delta: 0. Backend collected
delta: 0 (1370); no backend file changes; the backend suite is not run.
Break-its you run yourself and paste:
  1. Routing.test.tsx on v6 WITHOUT the future flags → FAIL (Future Flag
     warning printed).
  2. Open-redirect test on 6.30.6 (Task 1 commit) → RED; on 7.18.x → GREEN.
     Green on 6.30.6 = STOP (the test does not reach the advisory).
  3. Delete the `path="*"` route at App.tsx:134 → the fallback assertion
     fails. Restore.
  4. Only if Task 3 runs: break each of the 3 mock paths in turn → its
     tests go red.
Lockfile checks: `@remix-run/router` gone; list every new package and
version; Linux natives still present
(`grep -c '"node_modules/@rollup/rollup-linux-x64-gnu"\|"node_modules/@esbuild/linux-x64"' src/frontend/package-lock.json` → 2);
package.json diff shows only react-router-dom.
Write audit/2026-09-25/waves/wave-4-L1-B.md (append a phase-2 section).
Do not merge. Do not sign gates. Do not edit files outside the plan's
file list.
Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)
```

### 6.2 L2 implementer brief

```
Implement docs/plans/2026-10-04-NPM-MAJORS-react-router7.md, tasks 0-2
<and 3 if told>, in worktree /mnt/c/Users/DangT/Documents/GitHub/hc-rr7 on
branch feat/react-router7.
No Python is needed. All npm / npx / vitest commands run from Windows
through powershell.exe, never from WSL (vitest stalls on /mnt/c; npm from
WSL replaces the Windows native binaries). Do not run Playwright against a
backend with encryption disabled.
Re-run the plan's three scope greps before Task 1 and use their output, not
the plan's numbers. Known today: 32 files import react-router-dom, 15 are
tests, 3 use vi.mock('react-router-dom') (MedicationCorrelations.test.tsx:35,
ProfileSetup.test.tsx:44, RecoverProfile.test.tsx:35), 11 test files have a
router without a `future` prop.
Follow the plan literally, task by task. Test first: write
src/__tests__/Routing.test.tsx, run it and paste the FAIL, then implement,
then paste the PASS. In that test use `await screen.findBy…` or a positive
`waitFor`; never `waitFor(() => expect(x).not.toBeInTheDocument())`
(recurring-failures §1). Stub the auth store and API module with the real
response shapes (recurring-failures §1, SEC-RECOV-002).
Commit exactly as the plan lists, explicit pathspecs (never `git add -A`):
  feat(frontend): adopt React Router v7 future flags on v6
  fix(deps): react-router-dom 7.18 (clears GHSA-wrjc-x8rr-h8h6, GHSA-337j-9hxr-rhxg)
each ending with the Co-Authored-By line from the plan.
Ask-first files: none in scope. Do not touch services/api.ts,
components/auth/ProtectedRoute.tsx (unless Task 3 was ordered: import line
only), or any backend file.
Stop and report, without working around it, if: `npm install` moves any
package other than react-router-dom / react-router / their own deps; a type
error needs more than removing the `future` props; the vitest count differs
from baseline +1 / +2; any test fails; the open-redirect test is green on
6.30.6; an edit would fall outside the plan's file list.
Do NOT spawn agents. Do NOT push.
Return: commits (sha + subject); each test command with its output (RED and
GREEN); vitest totals before, after Task 1, after Task 2; Future Flag
warning count before and after; `npm audit` last line before and after; the
package.json diff; the list of lockfile packages added and removed; any
deviation with its reason.
Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)
```

## 7. Risks / open findings the plan does not cover

| # | Risk | Evidence | Recurring-failures mode |
|---|---|---|---|
| 1 | A third mocked file. `RecoverProfile.test.tsx:35` stubs `useNavigate`; the plan knows 2. If Task 3 runs by the plan's text, this mock silently stops intercepting and its tests may still pass | `git grep "vi.mock('react-router"` → 3 hits; `145fe77` | §1 green suite that could not have failed; §9 invariant fixed at one site, not across its class |
| 2 | The "no Future Flag warning" assertion can pass for the wrong reason. React Router prints each warning once per module instance; if another render in the same file runs first, the spy sees nothing. Keep it the first render in `Routing.test.tsx`, and keep break-it 1 | plan Task 1 Step 1; v6 warn-once behaviour is from library knowledge, **UNMEASURED here** | §1 |
| 3 | `Routing.test.tsx` renders the whole `App`, which imports 4 eager pages and a module-level `QueryClient` (`App.tsx:20,71`). Heavy mocks of `@/services/api` can describe an API the backend does not serve | `App.tsx:20`; SEC-RECOV-002 entry | §1 (mock was a different API) |
| 4 | `v7_startTransition` and tests that wait for loading UI. `grep -rn 'Loading page\|role="status"\|RouteFallback' src/__tests__` → 0 hits today, so no current test asserts the fallback; nothing guards the "old page held" behaviour either. Task 4's check is manual | measured 2026-10-07 | §1 |
| 5 | CI does not build or lint (`ci.yml:55-78`). A v7 type error in a file `tsc --noEmit` covers is caught; a bundling problem is caught only by the local Windows build and by E2E through the Vite dev server | `ci.yml` | §6 documented commands nobody ran |
| 6 | Existing installs keep `react-router-dom` 6 after merge (`dev.ps1:626-635`, DEV-PS1-INSTALL). After Task 2 removes the `future` props, v6 without flags still runs, so this is silent, not broken — but the advisory stays open on those machines | `dev.ps1:626-635`; `implementation-program.md:500` | §2 |
| 7 | AUTH-401-LOGOUT is adjacent and open: `services/api.ts:63-70` clears auth and calls `window.location.replace('/setup')` on every 401. It is outside the router and outside this plan; a reviewer may ask for it. It needs its own owner decision (`api/profiles.py` is auth, ask-first) | `implementation-program.md:489` | scope |
| 8 | The access token persists in `localStorage` (`stores/authStore.ts:73`, L1-B LOW). `Routing.test.tsx` must stub the store, not seed real `localStorage`, or it couples to `setupLocalStorage.ts` | `wave-3-L1-B.md:248`; `vitest.config.ts` setupFiles | §5 contaminated state |
| 9 | Target version `7.18.4` is from the 2026-10-04 `npm audit` output. The current 7.x and its advisories are **UNMEASURED** today | plan `:6` | §3, §4 |
| 10 | E2E-MASTER-CORRUPT: one unexplained E2E failure on main. Rerun once before reading a red E2E as a router regression | `implementation-program.md:502` | §4 |
| 11 | Program text still says "not approved for execution" (`implementation-program.md:426,:491`; plan `:3`). An L1 that reads the plan header literally stops at Task 0 | read at `8d6f02e` | §8 stale guidance |

Next action: L0 asks Q1 (Task 3 yes/no), then starts the Codex plan review with the 7 amendments in §4 as the prompt's known-drift list.
