# Wave 3 — L1-B (frontend) report, 2026-10-04

All 3 phases have an open PR, CI 6/6 green, and reviews addressed. Nothing is merged. No gates were signed.

**Merge order:** #37 → #38 → #39. They touch disjoint files, so any order merges cleanly. #39's vitest figure (186) is pinned to `90c502a` and is correct in any order. #38 also passes on its own.

| Phase | PR | Branch | Head | CI | Backend collected delta | vitest delta |
|---|---|---|---|---|---|---|
| RECOVERY-CODE-CACHE | https://github.com/BrooklynD23/HealthCentral/pull/37 | fix/rcc-recovery-code-cache | `7113db5` | 6/6 pass | 0 (1346) | +2 (186 → 188) |
| NPM-AUDIT | https://github.com/BrooklynD23/HealthCentral/pull/38 | fix/npm-audit | `93def9e` | 6/6 pass (E2E Smoke pass) | 0 | 0 |
| W-11a PR-4 (G-B6) | https://github.com/BrooklynD23/HealthCentral/pull/39 | docs/w11a-pr4-frontend-counts | `85f0948` | 6/6 pass | 0 | 0 |

- **Base:** `origin/main` @ `90c502a` for all 3. Main did not move during the wave.
- **Environment:** frontend commands ran on Windows through `powershell.exe` (node v22.20.0, npm 11.6.2).
- **Gates used:** W3-SEC-SCHED (RCC) and NPM-AUDIT-SCHED, both verbatim from owner-decisions. W-11a PR-4 needed no gate.

## 1. RECOVERY-CODE-CACHE (PR #37)

**Plan:** `docs/plans/2026-10-04-RCC-recovery-code-cache.md`, committed first on the branch (`821ffa8`).

**The fix needs 2 lines.** I read the TanStack source (query-core 5.90.14):
- `reset()` alone leaves the detached mutation in the cache for the default 5-minute gcTime.
- `gcTime: 0` alone keeps the mutation while the card is mounted, because `optionalRemove` skips mutations that still have observers.

So both are applied:
- `onSettled: () => issueRecoveryCode.reset()` in `components/settings/RecoveryCodeCard.tsx:66`
- `gcTime: 0` in `services/profiles.ts:272` (`useIssueRecoveryCode`)

**Placement flag for the owner:** the gate says "in `RecoveryCodeCard.tsx`". `gcTime` is a `useMutation` option and can only live in the hook. The change there is 1 line. The hook has 1 caller, and the file is not ask-first. Both reviewers judged the placement justified.

**Tests added:** FE-RECOV-007 (success) and FE-RECOV-008 (error, then retry). Each has a `MutationCache.subscribe` positive control that shows the secret was in the cache before the negative `waitFor`.

| Check (Windows) | Output |
|---|---|
| RED before the fix | `Tests 2 failed \| 6 passed (8)`. 007 and 008 fail with `AssertionError: expected 1 to be +0` |
| `npx tsc --noEmit` | `tsc=0` |
| `npm run lint` | `0 errors, 5 warnings` (pre-existing, in `useSpeechRecognition.ts`), `lint=0` |
| `npm run build` | `✓ built`, `build=0` |
| `npx vitest run` on base `90c502a` | `Test Files 32 passed (32)`, `Tests 186 passed (186)` |
| `npx vitest run` on head `7113db5` | `Test Files 32 passed (32)`, `Tests 188 passed (188)` |
| Break-it: `sed -i '66d' RecoveryCodeCard.tsx` (removes the `reset()` line) | `Tests 2 failed \| 6 passed (8)` (007 and 008) |
| Break-it: `sed -i '272d' profiles.ts` (removes the `gcTime` line) | `Tests 2 failed \| 6 passed (8)` (007 and 008) |
| After the break-it runs | restored with `git checkout --`; `git status --short` is clean |

**Reviews:**
- **code-reviewer:** returned 1 MINOR. The FE-RECOV-008 `toBeEnabled` check could not fail. The implementer replaced it with a real retry in `7113db5`. Re-review: APPROVE.
- **security-reviewer:** APPROVE, with 0 in-scope findings.

## 2. NPM-AUDIT (PR #38)

**Plan:** `docs/plans/2026-10-04-NPM-audit-fix.md` (`0b18508`) plus Amendment 1 (`d982643`). The lockfile commit is `93def9e`. `package.json` is unchanged. `--force` was never used.

| `npm audit` (Windows) | total | critical | high | moderate | low |
|---|---|---|---|---|---|
| Before (`90c502a`) | 26 | 1 | 19 | 4 | 2 |
| After (clean `npm ci` from the new lockfile) | 7 | 0 | 5 | 2 | 0 |

The 2026-10-01 program figure of 21 was measured on `8064244`. New advisories account for the difference.

**Left, each needing a semver-major.** These come back to the owner and were not fixed:

| Severity | Packages | Major needed |
|---|---|---|
| high | tailwindcss, braces, chokidar, micromatch, fast-glob (GHSA-vfj7-8cjw-p6xm; fast-glob is only affected through micromatch) | `tailwindcss@4.3.3` |
| moderate | react-router, react-router-dom 6.30.6 (GHSA-wrjc-x8rr-h8h6, GHSA-337j-9hxr-rhxg) | `react-router-dom@7.18.4` |

The security reviewer rated all 7 LOW and not reachable today:
- The tailwind chain runs only at build time.
- Every route target is built in code with a literal `/`.
- The app uses a declarative `BrowserRouter`, with no SSR.

**The plan's stop gate tripped, and I cleared it with Amendment 1.** Task 1's guard reported `major changes: 2`:
- `es-module-lexer` 1.7.0 → 2.3.2
- `std-env` 3.10.0 → 4.3.0

Each has exactly 1 consumer before and after: `vitest`, which moves 4.0.16 → 4.1.11, a minor. That makes them vitest's own declared internals, not a major upgrade of anything `package.json` names. The code-reviewer confirmed the sole-consumer claim at every depth of the lockfile. **The owner may veto this reading.** If so, revert `93def9e`.

**Direct dependencies moved, all within their major:**
- vite 7.3.0 → 7.3.6
- vitest 4.0.16 → 4.1.11
- postcss 8.5.6 → 8.5.28
- react-router-dom 6.30.2 → 6.30.6

| Check (Windows, clean `npm ci`) | Output |
|---|---|
| tsc / lint / build | `tsc=0`, `lint=0` (0 errors), `build=0` (L1 re-ran all 3) |
| `npx vitest run` | `Test Files 32 passed (32)`, `Tests 186 passed (186)` (L1 re-ran) |
| Versions | `vitest/4.1.11`, `vite/7.3.6` |
| Lockfile | `lockfileVersion` stays 3. 106 entries added or changed, all on `registry.npmjs.org` with sha512 integrity. Linux natives present. 0 new install scripts |
| E2E | CI "E2E Smoke Tests": pass |

**Reviews:**
- **code-reviewer:** APPROVE, with 4 MINOR. The 2 that need follow-up work are under open findings below.
- **security-reviewer:** APPROVE, with 0 CRITICAL and 0 HIGH.

## 3. W-11a PR-4, G-B6 (PR #39)

**Task 0:**
- Worktree `hc-w11a-pr4` at `90c502a`.
- `post-P1-ok`, `p0b-ok`.
- START collected `1346 tests collected`, `pytest exit=0`. Run with `HF_HUB_OFFLINE=1`, under flock, Py 3.11.16.
- I skipped the full backend run. This is a docs-only PR, and the CI Backend Tests job ran the suite (pass).

**Measured on main@90c502a, Windows 11** (vitest 4.0.16, Playwright 1.58.1):

| Measurement | Result |
|---|---|
| vitest | 186 listed / 186 passed / 0 failed, in 32 files |
| Playwright `--list --project chromium` | `Total: 30 tests in 6 files` (L1 re-ran: same) |
| Playwright `--list`, all projects | `Total: 35 tests in 7 files` (L1 re-ran: same) |
| Local Playwright run | **UNMEASURED on Windows.** The backend fails to start: `RuntimeError: SQLCipher required but not available` (`core/database.py:78`). I deliberately did not set `DATABASE_ENCRYPTION_REQUIRED=false`. |

**Files changed:**
- `docs/capstone-report/claims-ledger.md` (H2)
- `docs/capstone-report/architecture-overview.md` (§14)
- `docs/capstone-report/specs-compliance-matrix.md` (GATE-03, GATE-06, and the local-run row)
- `docs/features/TASK_LIST.md` (new Session Note)
- `audit/repository-audit-dashboard.html` (`:255`)

**Grep and docs checks:**
- The plan's inventory grep prints no lines.
- A raw grep finds 3 hits for the old figures, all dated or historical.
- `docs_lint`: pass. `generate_docs_index --check`: fresh.

**Review:** code-reviewer returned CHANGES with 1 MAJOR. The H2 claim cell had not been replaced, and the plan's grep filter hid it, because a line that mentions `TASK_LIST.md` is excluded (a §1/§5-style blind spot in the plan's own check). Fixed in `85f0948`, along with 3 MINOR. Re-review: APPROVE.

**Deviations:**
- The plan's line numbers had moved.
- The live claims had already been reworded to 165/28 and 179/31. I replaced them where they now are.
- The GATE-03 "no build/eslint in CI" text stays, because PR-3 (G-B4) is not merged.

## Open findings (not fixed; owner items)

**Must decide now:**
1. **NPM residual, 7 advisories, majors only:** Tailwind 3 → 4 clears 5 high. react-router 6 → 7 clears 2 moderate. Each needs its own migration phase.
2. **NPM transitive majors:** es-module-lexer 2.x and std-env 4.x arrive through vitest 4.1.11. Accept Amendment 1's reading, or veto it.
3. **HIGH, RCC pattern elsewhere:** the same 5-minute mutation-cache retention exists in 2 more places:
   - `useCreateProfile` (`services/profiles.ts:120`, `pages/ProfileSetup.tsx:136`): password in; recovery code and token out.
   - `useRecoverProfile` (`:241`, `pages/RecoverProfile.tsx:45-49`).

   Medium items in the same area:
   - `RecoverProfile.tsx:32-33` and `ProfileSetup.tsx:92` never clear the secret state.
   - `useDeleteProfile` (`:217`) keeps the password after a failed delete.
4. **MEDIUM, `dev.ps1:627-635`:** the launcher installs only when `node_modules` is missing, so existing installs keep vite 7.3.0 and ws 8.19.0 after #38 merges.
5. **MEDIUM, `dev.ps1:281-282`:** the product frontend runs on the Vite dev server. Every Vite dev-server CVE is therefore a runtime CVE on patient machines.

**Later:**
- LOW: a wrong password on the settings recovery card returns 401 (`api/profiles.py:611`). `services/api.ts:65-68` then signs the user out instead of showing "Incorrect password".
- LOW: if the user leaves Settings while issuing a code, the backend replaces the code but the new code is never shown. Pre-existing.
- LOW:
  - `package.json` `engines.node >=22` is below vite 7's `>=22.12`.
  - CI never runs `npm run build` or lint. That is PR-3's G-B4 scope.
  - rollup 4.64.0 adds the optional `@napi-rs/lzma-linux-x64-gnu`. It is upstream metadata and the integrity matches.
- Close-out: `docs/capstone-report/implementation-program.md:405` (G-B6 row) still reads 165/28 @`40f590e`. Fix it in the Wave-3 ledger close-out.
- Nit: specs-compliance-matrix `:181` reads "Measured … UNMEASURED". "Attempted" would be clearer.

## Process notes

- Plans were written with the superpowers writing-plans skill. No Codex review, per the brief.
- 3 implementers (sonnet) and 6 reviewer runs (opus: 4 code-reviewer, 2 security-reviewer), 1 L2 batch at a time.
- `gh pr create` worked, so no PATCH was needed.
- Worktrees left in place: `../hc-rcc`, `../hc-npm`, `../hc-w11a-pr4`.

Next action: owner reviews #37 first. Its body explains the `profiles.ts` placement.

---

# Wave 3 L1-B, round 2 (2026-10-04): RCC-2 and the NPM-MAJORS plans

Owner answers from L0, recorded on `docs/wave3-close`:
- **NPM-AMEND-1:** accepted. #38 is unchanged.
- **RCC-2:** "New phase now".
- **NPM-MAJORS:** "Plan now".

Both new PRs are open with CI 6/6 green, and reviews are addressed. Nothing is merged and no gates were signed. `origin/main` is still at `90c502a`.

| Item | PR | Branch | Head | CI | Backend count | vitest |
|---|---|---|---|---|---|---|
| RCC-2 | https://github.com/BrooklynD23/HealthCentral/pull/42 | fix/rcc2-secret-retention | `dd8edb6` | 6/6 | +0 (1346) | 188 → 193 (+5) |
| NPM-MAJORS plans (docs only) | https://github.com/BrooklynD23/HealthCentral/pull/43 | docs/npm-majors-plans | `22de642` | 6/6 | +0 | +0 |

**Merge order:** #37 → #42 (#42 is stacked on #37) → #38 → #39 → #43. #37, #38, #42 and #43 all touch `docs/INDEX.md` and `docs/_link_graph.json`. After each merge, refresh the next PR (L0 has said it will ask).

## RCC-2 (#42)

- **Plan:** `docs/plans/2026-10-04-RCC2-secret-retention.md` (`c26ac11`).
- **Base:** #37's head `7113db5`, because #37 was not merged. The PR body says so. After #37 merges: merge main and re-run the checks.

**The fix, in 3 hooks:**
- `useCreateProfile`, `useRecoverProfile` and `useDeleteProfile` each get `gcTime: 0`.
- Each caller calls `reset()` after `mutateAsync` settles: on success and in `catch` for create and recover; in `catch` only for delete, because success already runs `queryClient.clear()`.
- Page state is cleared: `ProfileSetup` `setPassword('')`; `RecoverProfile` `setCode('')` and `setNewPassword('')`.

**Tests:**
- New helper `__tests__/support/secretRetention.ts` with `cachedMutationsContaining`, `watchCacheFor` and `reactStateContains`. The last one walks the committed fiber tree; its limits are documented in the code.
- FE-RCC2-001 to FE-RCC2-005, each with a positive control.

| Check (Windows) | Output |
|---|---|
| RED before the fix | `Tests 5 failed \| 5 passed (10)`. All 5 FE-RCC2 tests fail with `expected 1 to be +0` |
| GREEN | `Tests 10 passed (10)` |
| tsc / lint / build | `tsc=0`; `lint=0` (0 errors); `build=0` |
| Full vitest | `Test Files 34 passed (34)`, `Tests 193 passed (193)` (base `7113db5`: 32 / 188) |
| Break-it | 11 of 11 fix lines each turn their target test red when removed. The 3 state lines fail with `expected true to be false`. See the table in the PR body |
| Flake | 1 of about 20 runs timed out on `findByTestId` at the default 1 s, because ProfileSetup has 2 artificial 500 ms delays. Fixed with a 5 s wait in `4448ec9` and `dd8edb6`. 5 of 5 later runs passed |

**Reviews:**
- **code-reviewer:** APPROVE with 5 MINOR. 4 fixed in `dd8edb6`; 1 is out of scope.
- **security-reviewer:** APPROVE, 0 findings in scope.

**Commit trailers:** `145fe77` and `f2677e2` carry `Co-Authored-By: Claude Sonnet 5.5`, the implementer's real model, not the brief's Opus 5.5 line. I left them as they are; I did not rewrite history on a pushed branch.

## NPM-MAJORS plans (#43, docs only, not approved for execution)

**Plans:**
- `docs/plans/2026-10-04-NPM-MAJORS-tailwind4.md` names **2 majors**: tailwindcss 3 → 4 and tailwind-merge 2 → 3, because `cn()` depends on tailwind-merge.
- `docs/plans/2026-10-04-NPM-MAJORS-react-router7.md`: react-router-dom 6 → 7.18.

**Tailwind 4, the key finding (the reviewer's BLOCKER, verified):**
- `globals.css:7-10` and `:16-19` define `--color-surface/ink/accent` and `--radius-*` in `@layer base`. Tailwind 4 uses the same variable names, so v4 would render the app's main colours transparent and enlarge the radii.
- 0 consumers (`grep var(--(color|radius)` → 0), so the plan deletes them first.

**Tailwind 4, the rest of the scope:**
- Renames: `outline-none` 42, bare `rounded` 133, `flex-shrink/grow` 23, `shadow-sm` 5, `backdrop-blur-sm` 5.
- Default changes: border colour 107, placeholder 29, `hover:` 78.
- Browser floor.
- Screenshot check on 9 routes plus a modal, including a body-background check.

**React Router 7 scope:**
- Declarative mode, so the data-router breaking changes do not apply.
- `v7_startTransition` changes the Suspense fallback across 12 lazy routes.
- Order of work: future flags on v6 first, then bump to v7.
- 2 test mocks to move: `useNavigate` in ProfileSetup and `useParams` in MedicationCorrelations.
- The open-redirect test compares `URL.origin` and must be RED on 6.30.6.

**Review:** code-reviewer returned CHANGES: 1 BLOCKER, 4 MAJOR (3 planned tests could not fail, wrong mock files) and 10 MINOR. Fixed in `5d5bead`, then APPROVE. The re-review's commit-message nit is fixed in `22de642`.

**Docs checks:** `Docs lint passed.` and `fresh`.

## New open findings (owner items, not fixed)

1. **MAJOR, RCC-3 candidate:** `useRestoreBackup` (`services/backup.ts:173`, `BackupCard.tsx:113`). `RestoreRequest.password` stays in the mutation cache after a failed restore. It is the 5th hook carrying a password; the other 4 are now fixed (recurring-failures §9).
2. **MEDIUM, wrong secret signs the user out:**
   - A wrong recovery code (`api/profiles.py:713`) or a wrong delete password (`:826`) returns 401.
   - `services/api.ts:63-69` then clears auth and redirects to `/setup`, so the user never sees the error message.
   - FE-RCC2-004 and FE-RCC2-005 mock `@/services/api`, so they cannot see this path. The same path is also reachable from the settings card in #37.
3. **LOW, unfixed hooks with no callers:** `useLogin` and `useUnlockProfile` (`profiles.ts:138,156`) still lack the RCC pattern. They have 0 callers.
4. **LOW:** the access token persists in `localStorage` (`stores/authStore.ts:73`).
5. **Seen while reviewing the plans:** `SettingsPage.tsx:954` navigates to a server-supplied `a.url` after checking only `startsWith('/')`, which lets `/\x` and `//x` through. Today the backend sends the literal `/settings` (`environment_diagnostics.py:244`).

**Worktrees left in place:** `../hc-rcc2`, `../hc-npm-majors`, plus the 3 from round 1.

Next action: the owner merges #37, then L1 merges main into #42 and re-runs `npx vitest run` from Windows.

---

# Wave 3, L1-B round 3 (2026-10-04): RCC-3

RCC-3 is done. https://github.com/BrooklynD23/HealthCentral/pull/46 is open at head `57c3760`. CI passed 6/6, both reviews returned APPROVE, and the review findings are addressed. Nothing is merged and no gates were signed.

- **Owner gate RCC-3, verbatim:** "Same small fix as RCC-2, done by L1-B."
- **Deferred by the owner and untouched here:** AUTH-401-LOGOUT and `useLogin`/`useUnlockProfile`. `services/api.ts` is unchanged.
- **Plan:** `docs/plans/2026-10-04-RCC3-restore-backup.md` (`993f286`).
- **Base:** #42's head `dd8edb6`, because #37 and #42 are not merged. The PR body says so.
- **Merge order:** #37 → #42 → #46.

## Change

| File | Change |
|---|---|
| `services/backup.ts` `useRestoreBackup` | `gcTime: 0` |
| `components/settings/BackupCard.tsx` `handleRestore` | Calls `reset()` once `mutateAsync` resolves, and again in `catch` |

The component already cleared the password on success and when the restore target changes. After a failure it keeps the password so the user can retry, the same as RCC and RCC-2.

**Tests:**
- **FE-RCC3-001** covers a failure followed by a retry. It checks the cache, with positive controls on the cache watch and on the retry's call arguments.
- **FE-RCC3-002** covers success. It checks React state, with a `reactStateContains` positive control. This test is needed because `queryClient.clear()` already empties the cache on success, so a cache test there could not fail.

## Measured on Windows

| Check | Output |
|---|---|
| RED | `Tests 2 failed \| 2 passed (4)`: FE-RCC3-001 fails with `expected 1 to be +0`, FE-RCC3-002 with `expected true to be false` |
| GREEN | `Tests 4 passed (4)` |
| tsc / lint / build | `tsc=0`, `lint=0` (0 errors), `build=0` |
| Full vitest | `Tests 195 passed (195)` at head `57c3760` (base `dd8edb6`: 193) |
| Break-it, `backup.ts:181` (`gcTime`) | red (001) |
| Break-it, `BackupCard.tsx:119` (reset after resolve) | red (002) |
| Break-it, `BackupCard.tsx:128` (reset in `catch`) | red (001) |
| After break-it | Restored; `git status` clean |
| Docs gates | Docs gates pass |

**Collected delta:**

| Suite | Before | After |
|---|---|---|
| Backend | 1346 | 1346 (+0) |
| vitest | 193 | 195 (+2) |

## Reviews

- **code-reviewer:** APPROVE. Its 2 MINOR findings (the retry-leg positive control and a comment on the scope of the state control) are fixed in `57c3760`.
- **security-reviewer:** APPROVE, with 0 CRITICAL, HIGH or MEDIUM findings. It confirmed that the only password-carrying mutations without the fix are now `useLogin`/`useUnlockProfile`, which have 0 callers and which the owner said to leave.

Worktree `../hc-rcc3` is left in place.

Next action: the owner merges #37, then #42, then #46. After each merge, L1 merges main into the next PR and re-runs `npx vitest run` on Windows.

---

# Wave 3 L1-B, refresh of #42 (2026-10-05)

PR #42 is refreshed onto `origin/main` `ee5721d` (after #37, #41, #44 and #48 merged). New head: `0d4fe42`. CI passes 6/6 and GitHub reports it `MERGEABLE`. I have not merged it.

**How the merge was done:**
- `git merge origin/main` (not a rebase).
- The only conflict was `docs/INDEX.md`. I resolved it by regenerating with `~/venvs/asclexis-311/bin/python scripts/generate_docs_index.py` and `docs_lint.py --link-graph`.
- I committed the merge with explicit pathspecs.

**Checks:**

| Check | Result |
|---|---|
| `generate_docs_index.py --check` | `fresh` |
| `docs_lint.py` | `Docs lint passed.` |
| `git diff origin/main -- CLAUDE.md AGENT.md` | 0 lines, so #42 changes no counts |
| `git diff --name-only origin/main...HEAD` | Only the 11 RCC-2 files: plan, INDEX, link graph, 4 test files, 4 source files |
| Windows `npm ci` | `ci=0` |
| `tsc` / `lint` / `build` | `tsc=0`, `lint=0` (0 errors, 5 warnings that were already there), `build=0` |
| `npx vitest run` | `Test Files 34 passed (34)`, `Tests 193 passed (193)`, `vitest=0` |
| CI on `0d4fe42` | Agent Eval Gate, Backend Tests, Documentation Lint, E2E Smoke Tests, Frontend Tests, Security Scan: all pass |

Next action: after #42 merges, refresh #46 (`../hc-rcc3`) the same way. Then refresh #38, one PR at a time.

---

# Wave 3 L1-B, refresh of #46 (2026-10-05)

#46 is refreshed onto `origin/main` `f2dd8f3` (the #42 merge). The new head is `3710ccf`, CI is 6/6 green, and GitHub reports it MERGEABLE. I did not merge it.

**How the merge was done:**
- `git merge origin/main`, no rebase.
- The only conflict was `docs/INDEX.md`. I regenerated it with `generate_docs_index.py` and `docs_lint.py --link-graph`, then committed the merge with explicit pathspecs.

**Checks:**

| Check | Result |
|---|---|
| `generate_docs_index.py --check` | fresh |
| `docs_lint` | passed |
| `git diff origin/main -- CLAUDE.md AGENT.md` | 0 lines |
| `git diff --name-only origin/main...HEAD` | 6 RCC-3 files: plan, INDEX, link graph, `BackupRestoreFlow.test.tsx`, `BackupCard.tsx`, `backup.ts` |
| Windows `npm ci` | `ci=0` |
| `tsc` / `lint` / `build` | `tsc=0`, `lint=0` (0 errors), `build=0` |
| `npx vitest run` | `Test Files 34 passed (34)`, `Tests 195 passed (195)` |
| CI on `3710ccf` | Agent Eval Gate, Backend Tests, Documentation Lint, E2E Smoke Tests, Frontend Tests, Security Scan: all pass |

Next action: after #46 merges, refresh #38 (`../hc-npm`) the same way.
