**READY (first of the frontend sequence; no plan file — see §1/§3 Q1)**

# NPM-AUDIT-2 — readiness pack (scaffold, not an execution record)

## 1. Readiness verdict

**READY (first of the frontend sequence)** — with one pre-dispatch condition: the phase has **no plan file**, so orchestration §3 step 1 (`git ls-files docs/plans/...` non-empty) cannot pass as written. L0 settles that with owner question Q1 below before spawning L1.

- Gate: NPM-MAJORS-RUN, signed 2026-10-07 (`docs/capstone-report/owner-decisions-2026-09-27.md:64`).
- Hard dependency: NPM-AUDIT PR #38 (`c4d407e`) is on `origin/main`.
- Order: runs first; React Router 7 and Tailwind 4 wait for its merge (all three rewrite `package-lock.json`).

Scaffold written 2026-10-07 in worktree `hc-scaffold` (branch `docs/wave4plus-scaffold`, HEAD `8d6f02e`, `origin/main` = `6b4dd84`). Nothing was run with `npm`; every `npm audit` figure below is quoted from a dated record, not re-measured.

## 2. Task 0 evidence (measured 2026-10-07)

| Check | Command | Result |
|---|---|---|
| NPM-AUDIT #38 merged | `git merge-base --is-ancestor c4d407e origin/main; echo $?` | `0` |
| #38 lockfile commit merged | `git merge-base --is-ancestor 93def9e origin/main; echo $?` | `0` |
| Dedicated plan file | `git ls-files docs/plans \| grep -i npm` | 3 files: `2026-10-04-NPM-audit-fix.md`, `-NPM-MAJORS-react-router7.md`, `-NPM-MAJORS-tailwind4.md`. **None for NPM-AUDIT-2** |
| Reusable plan present | `git ls-files docs/plans/2026-10-04-NPM-audit-fix.md` | non-empty |
| Gate NPM-MAJORS-RUN | `owner-decisions-2026-09-27.md:64` | **signed**: "NPM-AUDIT-2, then React Router 7, then Tailwind 4, each as its own PR… an NPM-AUDIT-2 phase (`npm audit fix` without `--force`; Windows vitest + E2E)" |
| Gate NPM-AUDIT-SCHED (prior art) | `owner-decisions-2026-09-27.md:51` | signed 2026-10-04; scoped to NPM-AUDIT #38 |
| Gate NPM-AMEND-1 (transitive majors) | `owner-decisions-2026-09-27.md:53` | signed 2026-10-04, **for 2 named packages only** (`es-module-lexer` 1→2, `std-env` 3→4). A general rule for NPM-AUDIT-2: **UNSIGNED** (Q2) |
| Leftover worktree | `git worktree list` | `../hc-npm` exists at `92e96ca` on merged branch `fix/npm-audit`. Do not reuse it |

`src/frontend/package.json` (read, not run):

| Field | `package.json` range | `package-lock.json` resolved |
|---|---|---|
| `engines.node` | `>=22` (`package.json:6-8`) | root `>=22` |
| react-router-dom | `^6.21.0` | 6.30.6 (`react-router` 6.30.6, `@remix-run/router` 1.23.4) |
| tailwindcss | `^3.4.1` | 3.4.19 |
| tailwind-merge | `^2.2.0` | 2.6.0 |
| vite | `^7.3.0` | 7.3.6 (engines `^20.19.0 \|\| >=22.12.0`) |
| vitest | `^4.0.16` | 4.1.11 (engines `^20.0.0 \|\| ^22.0.0 \|\| >=24.0.0`) |
| `@tailwindcss/*` | none | none |
| The 3 packages NPM-AUDIT-DRIFT names | not in `package.json` | `fast-glob` 3.3.3, `postcss-nested` 6.2.0 (sole consumer of both: `tailwindcss` 3.4.19); `source-map-js` 1.2.1 (consumers: `postcss` 8.5.28 `^1.2.1`, `css-tree` 3.1.0 `^1.0.1`) |

`npm audit` today: **UNMEASURED** (no npm in this scaffold). Last record: 10 (4 moderate, 6 high) on 2026-10-06, Windows, at `92e96ca` (`implementation-program.md:492`; `wave-3-L0-notes.md:56`).

## 3. Owner questions still to ask

**Q1. NPM-AUDIT-2 has no plan file. Which document does L1 execute?**
- A. Reuse `docs/plans/2026-10-04-NPM-audit-fix.md` Tasks 0-3 as written, with the deltas in §4 carried in the L1 brief only. No docs commit.
- B. **(recommended)** Reuse that plan, and L1's first commit on the phase branch adds a dated "Amendment 2 (NPM-AUDIT-2)" section to it with the §4 deltas. One file, docs-only, keeps orchestration §3 step 1 literal and leaves a record.
- C. Write a new `docs/plans/2026-10-07-NPM-AUDIT-2.md`. Most paper for a lockfile-only change.

**Q2. May NPM-AUDIT-2 accept a transitive major the way NPM-AMEND-1 did?**
- A. **(recommended)** Yes, under Amendment 1's rule only: the package is not in `package.json`, its only consumer moved by a minor or patch, and tsc / lint / build / vitest / E2E are green. L1 reports each one in the PR body.
- B. No. Any major in the lockfile stops the phase and comes back to you (the wording of NPM-AUDIT-SCHED).
- C. Yes for dev-only packages; stop for anything that ships in the runtime bundle.

**Q3. Where does "E2E" run for this phase?** Your text says "Windows vitest + E2E". Playwright cannot start the backend on Windows (`RuntimeError: SQLCipher required but not available`, `wave-3-L1-B.md:111`).
- A. **(recommended)** CI "E2E Smoke Tests" on the PR (`ci.yml:174-209`, chromium, 31 tests listed 2026-10-07) is the E2E evidence, as accepted for #38.
- B. CI plus a local Linux run with `HC_E2E_CHROMIUM_PATH` set (recurring-failures §4). Adds roughly one run of 31 tests; needs a Linux `node_modules` that is not the Windows one.
- C. Windows E2E with `DATABASE_ENCRYPTION_REQUIRED=false`. Not recommended: unencrypted evidence.

**Q4. `engines.node` is `>=22`, but the resolved vite 7.3.6 needs `>=22.12.0` and jsdom 27.4.0 needs `^22.12.0`. Fix it in this PR?**
- A. **(recommended)** Yes: one line, `"node": ">=22.12"`, in NPM-AUDIT-2 (the phase already owns `package.json`). It is a manual `package.json` edit, which the reused plan's Global Constraints forbid, so it needs this answer.
- B. No. Leave it; register it as its own item.
- C. Defer to Tailwind 4 (which also edits `package.json`).

## 4. Plan drift check (reused plan `docs/plans/2026-10-04-NPM-audit-fix.md`)

Tally: **MATCH 8, MOVED 1, CHANGED 6, UNMEASURED 1.**

| # | Plan cites | Now | Verdict |
|---|---|---|---|
| 1 | `:13` npm 11.6.2, Node v22.20.0 | L0 recorded node v22.20.0 on 2026-10-07 (`wave-3-L0-notes.md:72`); npm version not re-read | UNMEASURED |
| 2 | `:13` Vite 7, vitest 4, Tailwind 3 | lock: 7.3.6, 4.1.11, 3.4.19 | MATCH |
| 3 | `:24` backend collected **1346** (`CLAUDE.md:30,:35`, `AGENT.md:76`) | **1370** at the same three lines (G-C3b #45 and others) | CHANGED |
| 4 | `:29` baseline `npm audit` **26** (2 low, 4 moderate, 19 high, 1 critical) | 10 (4 moderate, 6 high) on 2026-10-06 after #38; today UNMEASURED | CHANGED |
| 5 | `:43`, `:68`, `:117` expected after-count **7** | No valid expectation. It is "Task 0 baseline minus the advisories `npm audit fix` clears". Must be re-derived from Task 0 `npm audit --json` | CHANGED |
| 6 | `:47` Amendment 1 lists `fast-glob` as fixable **only** by `tailwindcss@4.3.3` (major) | `implementation-program.md:492` says `fast-glob` is fixable non-breaking. The two records disagree. Lock: `fast-glob` 3.3.3, sole consumer `tailwindcss` 3.4.19 `^3.3.2` | CHANGED (conflict; measure at Task 0) |
| 7 | `:52`, `:170` vitest **32 files, 186 tests** | **34 files, 195 tests** (L0, Windows, `6b4dd84`; from #37, #42, #46) | CHANGED |
| 8 | `:58-59` `package.json` unchanged by `npm audit fix` | `git log -- src/frontend/package.json`: last commit `7b28612` (before #38); ranges as in §2 | MATCH |
| 9 | `:84` base `90c502a` is an ancestor | `0`. Correct but stale: the base to assert is `c4d407e` | MATCH |
| 10 | `:85` `git worktree add ../hc-npm -b fix/npm-audit` | Worktree and branch already exist, at `92e96ca`, merged | CHANGED |
| 11 | `:87` gate grep `NPM-AUDIT-SCHED` in `hc-l0-docs/...` | The gate for this phase is NPM-MAJORS-RUN at `owner-decisions-2026-09-27.md:64` (SCHED still at `:51`) | MOVED |
| 12 | `:155` Linux natives count 2 | `@rollup/rollup-linux-x64-gnu` and `@esbuild/linux-x64` both in the lock | MATCH |
| 13 | `:25` E2E runs in CI "E2E Smoke" | `ci.yml:174-209`, `npx playwright test --project chromium` | MATCH |
| 14 | `:89` (L1-B) `lockfileVersion` 3 | 3 | MATCH |
| 15 | `:50` `es-module-lexer` 2.3.2, `std-env` 4.3.0 via vitest 4.1.11 | same | MATCH |
| 16 | `:48` `react-router(-dom)` 6.30.6 | same | MATCH |

CI workflow frontend jobs (`.github/workflows/ci.yml`, last commit `1abb4ef`, unchanged since the plan): `frontend-tests` runs `npm ci`, `npx tsc --noEmit`, `npx vitest run` on Node `'22'` (`:64`); `e2e-tests` runs `npm ci`, `playwright install`, `npx playwright test --project chromium` on Node `'22'` (`:184`). No `npm audit`, `npm run build` or `npm run lint` step.

**Plan amendments needed (do not edit the plan here):**
1. Replace 1346 with 1370; replace 186/32 with the Task 0 measured vitest baseline (195/34 on 2026-10-07).
2. Replace the baseline 26 and after-count 7 with Task 0's measured figures; state the after-count as a per-package list, not a total.
3. Resolve the `fast-glob` conflict from Task 0's `npm audit --json` (`fixAvailable` per package).
4. Base ancestry `c4d407e`; worktree `../hc-npm-audit-2`; branch `fix/npm-audit-2`.
5. Gate line: NPM-MAJORS-RUN (`owner-decisions:64`), read from the phase worktree, not `hc-l0-docs`.
6. Amendment 1's major rule applies only if Q2 is answered A or C.

Counts asked for in the brief (shared by all three packs): `grep -rl "react-router-dom" src/frontend/src | wc -l` → **32** (router plan says 30). Tailwind: `@apply` 4 lines in 1 file (`globals.css:49,66,70,80`), `theme(` 0, files using a config colour token 53 (1046 hits). This phase edits none of them.

## 5. File ownership

| File | Change |
|---|---|
| `src/frontend/package-lock.json` | rewritten by `npm audit fix` |
| `src/frontend/package.json` | only if `npm audit fix` raises a range inside its major, or Q4 = A (one `engines` line) |
| `docs/plans/2026-10-04-NPM-audit-fix.md` | only if Q1 = B (Amendment 2 section) |
| `docs/INDEX.md`, `docs/_link_graph.json` | regenerated only if a plan file changes |

Overlap with undone phases:

| Phase | Shared file | Handling |
|---|---|---|
| React Router 7 | `package-lock.json`, `package.json` | serial; RR7 branches from main after this merges |
| Tailwind 4 | `package-lock.json`, `package.json` | serial, third |
| W-11a PR-3 | `src/frontend/package.json` is on W-11a's stop list (`W11a plan:100,172`), so it does not edit it; it may add build / lint steps to `ci.yml` (G-B4) | no file overlap |
| W-3, W-2, W-4, W-7, W-8, P5, P6, P7, W-10, W-10b, G-C1, G-C2, G-C3a, G-C5, P4-deferred, AUDIT-ORDER, PROHIBITED-PARAPHRASE, W-11a PR-1 | none (no frontend dependency file) | — |

Backend files: none. Backend collected delta expected **0** (1370).

## 6. Briefs

### 6.1 L1 brief (frontend sequence, phase 1 of 3)

```
You are the L1 Wave Orchestrator for the Wave 4 frontend sequence of the
Asclexis execution program. Follow docs/agentic/orchestration.md §3 exactly;
you are L1. This brief covers phase 1 of 3; do not start phase 2 until the
owner has merged phase 1.
Phase: NPM-AUDIT-2 — reuses docs/plans/2026-10-04-NPM-audit-fix.md Tasks 0-3
with the deltas in audit/2026-09-25/waves/scaffold/NPM-AUDIT-2.md §4
(<Q1 answer: brief-only | Amendment 2 as first commit | new plan file>).
Base: origin/main @ <sha>. Confirmed merged dependency: NPM-AUDIT PR #38
(c4d407e; `git merge-base --is-ancestor c4d407e origin/main` → 0).
Signed gate (verbatim, owner-decisions:64): "NPM-AUDIT-2, then React Router 7,
then Tailwind 4, each as its own PR. Largest frontend churn of the three."
The row approves an NPM-AUDIT-2 phase: `npm audit fix` without `--force`;
Windows vitest + E2E.
Unsigned: transitive-major rule <Q2 answer>; engines.node bump <Q4 answer>.
A task that needs an unsigned one STOPS; report it.
Architectural: no. Owner-directed extras for this sequence: a Fable
adversarial review of this brief was done by L0 before dispatch
(findings: <path>); no Codex review for this phase unless L0 says so.
Worktree ../hc-npm-audit-2, branch fix/npm-audit-2, one PR. Do NOT reuse
../hc-npm (stale, merged).
Never: `npm audit fix --force`, `npm install <pkg>@<major>`, a manual version
edit in package.json, any file outside src/frontend/package.json and
src/frontend/package-lock.json (+ the plan amendment and regenerated docs
index if Q1 = B).
Spawn one implementer: Agent(subagent_type="general-purpose",
model="sonnet") with the §5 brief below. Reviewers:
Agent(subagent_type="code-reviewer", model="opus") and
Agent(subagent_type="security-reviewer", model="opus") (lockfile: every
changed entry resolves to registry.npmjs.org with sha512 integrity; no new
install scripts; Linux natives still present).
Run the acceptance yourself, FROM WINDOWS, NOT WSL (vitest stalls on
/mnt/c; npm from WSL replaces the Windows native binaries):
  powershell.exe -NoProfile -Command "cd C:\Users\DangT\Documents\GitHub\hc-npm-audit-2\src\frontend; Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue; npm ci; npm audit 2>&1 | Select-Object -Last 8; npx tsc --noEmit; echo tsc=$LASTEXITCODE; npm run lint; echo lint=$LASTEXITCODE; npm run build; echo build=$LASTEXITCODE; npx vitest run 2>&1 | Select-Object -Last 8"
E2E: <Q3 answer; default CI "E2E Smoke Tests" on the PR>. Do not run
`npx playwright test` on Windows with encryption disabled.
Tests this phase adds: 0. vitest must equal the Task 0 baseline (195 tests
in 34 files on 2026-10-07; re-measure). Backend collected delta: 0 (1370);
no backend file changes, so the backend suite is not run.
Break-it (no test is added, so prove the fix did something): save
`npm audit --json` before and after; each package `npm audit fix` claims to
fix must be listed before and absent after, and no package may appear after
that was absent before. Then re-run Task 1 Step 3's major-change script and
paste it.
Write audit/2026-09-25/waves/wave-4-L1-B.md: PR URL, commands and outputs,
before/after audit per package, gates used, open findings, merge order.
Do not merge. Do not sign gates.
Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)
```

### 6.2 L2 implementer brief

```
Implement docs/plans/2026-10-04-NPM-audit-fix.md, Tasks 0-2, as NPM-AUDIT-2,
in worktree /mnt/c/Users/DangT/Documents/GitHub/hc-npm-audit-2 on branch
fix/npm-audit-2. Read audit/2026-09-25/waves/scaffold/NPM-AUDIT-2.md §4
first: the plan's numbers (26, 7, 186/32, 1346, 90c502a, ../hc-npm) are
stale; use the Task 0 output you measure instead.
No Python is needed. All npm / npx commands run from Windows through
powershell.exe, never from WSL.
Follow the plan literally, task by task. This phase adds no test. Commit
exactly: `fix(deps): apply non-breaking npm audit fixes in frontend
(NPM-AUDIT-2)` with pathspecs src/frontend/package-lock.json
src/frontend/package.json only (never `git add -A`), ending with the
Co-Authored-By line from the plan.
Ask-first files: none in scope.
Stop and report, without working around it, if: `npm audit fix` leaves a
package npm calls non-major-fixable; Task 1 Step 3 prints a major that
<Q2 rule> does not allow; tsc, lint, build or vitest fails; the vitest
count differs from your Task 0 baseline; any file other than the two
changes; `--force` would be needed.
Do NOT spawn agents. Do NOT push.
Return: commit sha + subject; `npm audit` last line before and after; the
per-package before/after list from `npm audit --json`; Task 1 Step 3 and
Step 4 output; tsc / lint / build exit codes; vitest summary before and
after; any deviation with its reason.
Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)
```

Reviewers: `code-reviewer` + `security-reviewer`, both opus (handoff §6 template; Pass 3 walks recurring-failures §3, §4, §5). Codex: not architectural (orchestration §5 list); the owner's "large plans" direction (ledger `:193`) names Tailwind 4 and React Router 7, not this phase. Fable adversarial review of the briefs: owner direction (ledger `:194`) covers the whole sequence, so L0 runs it on this brief too.

## 7. Risks / open findings the plan does not cover

| # | Risk | Evidence | Recurring-failures mode |
|---|---|---|---|
| 1 | Two of the three fixable packages exist only because of Tailwind 3. `fast-glob` and `postcss-nested` have one consumer each, `tailwindcss` 3.4.19; Tailwind 4 is expected to remove both. The lasting effect of this PR may be `source-map-js` only | lock read, §2 | §3 figures asserted |
| 2 | Advisory counts move daily on a byte-identical lockfile (7 → 10 in 2 days). A count written in the PR body is true only for its date | `implementation-program.md:492` | §4 environment-dependent results |
| 3 | CI does not gate on `npm audit`, `npm run build` or `npm run lint`. A lockfile that breaks the build passes "Frontend Tests"; only the local Windows build and E2E (Vite dev server) would show it | `ci.yml:55-78`; GATE-15 gap; `wave-3-L1-B.md:152` | §1 green suite that could not have failed |
| 4 | Existing installs keep the old packages after merge: `dev.ps1` installs only when `node_modules` or the vite binary is missing | `dev.ps1:626-635`; owner item DEV-PS1-INSTALL (`implementation-program.md:500`) | §2 fix that creates the next bug |
| 5 | E2E Smoke failed once on main with a malformed DB after a disk I/O error (E2E-MASTER-CORRUPT, cause UNMEASURED). A red E2E on this PR needs one rerun before it is read as a regression | `implementation-program.md:502` | §4 |
| 6 | A stale `node_modules` in a reused worktree makes the checks pass against packages the lockfile no longer names. The plan's clean `npm ci` (Task 2 Step 1) covers it only if the worktree is new | `../hc-npm` at `92e96ca` | §5 contaminated tree |
| 7 | `implementation-program.md:426` and `:491` still say NPM-MAJORS is "unsigned / not approved for execution", against `owner-decisions:64`. L0 doc fix, not this phase | read 2026-10-07 at `8d6f02e` | §8 stale guidance |

Next action: L0 asks Q1 and Q2 in one prompt, then runs the Fable review on §6.
