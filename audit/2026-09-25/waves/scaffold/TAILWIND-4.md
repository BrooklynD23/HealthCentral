**GATED (serial after React Router 7; `tailwind-merge` 3 approval unsigned)**

# Tailwind 4 — readiness pack (scaffold, not an execution record)

## 1. Readiness verdict

**GATED (serial after React Router 7)** — the plan's own Task 0 Step 1 and first stop gate need an approval that names **`tailwind-merge` 3**. NPM-MAJORS-RUN (`docs/capstone-report/owner-decisions-2026-09-27.md:64`) approves "both NPM-MAJORS plans" and names Tailwind 4; it does not name `tailwind-merge`. Ask Q1 before dispatch.

- Signed: NPM-MAJORS-RUN (`owner-decisions:64`), NPM-MAJORS plan-first (`owner-decisions:55`).
- Unsigned: `tailwind-merge` 2 → 3 by name (Q1); the browser floor (plan `:53`, "The owner decides"; Q2); screenshot acceptance (plan stop gate 4; decided at PR time).
- Hard dependency: NPM-AUDIT PR #38 is on `origin/main`.
- Order constraint (not a code blocker): NPM-AUDIT-2, then React Router 7, then this.
- Pre-dispatch process steps the owner directed: Codex plan review (ledger `:193`) and a Fable adversarial review of the briefs (ledger `:194`).

Scaffold written 2026-10-07 in worktree `hc-scaffold` (HEAD `8d6f02e`, `origin/main` = `6b4dd84`). No `npm`, vitest or Playwright was run.

## 2. Task 0 evidence (measured 2026-10-07)

| Check | Command | Result |
|---|---|---|
| NPM-AUDIT #38 merged | `git merge-base --is-ancestor c4d407e origin/main; echo $?` | `0` |
| Plan's own check | `git merge-base --is-ancestor 93def9e origin/main; echo $?` | `0` |
| NPM-AUDIT-2, React Router 7 merged | no branch or PR exists | **not started** (order constraint) |
| Plan file | `git ls-files docs/plans/2026-10-04-NPM-MAJORS-tailwind4.md` | non-empty (PR #43, `22491e2`) |
| Plan Task 0 Step 1 | `grep -n 'NPM-MAJORS' docs/capstone-report/owner-decisions-2026-09-27.md` | rows `:55` (plan now) and `:64` (run). `grep -n 'tailwind-merge'` on the same file → **0 lines** |
| Gate: Tailwind 4 run | `owner-decisions:64` | **signed** |
| Gate: `tailwind-merge` 3 named | — | **UNSIGNED** |
| Gate: browser floor Safari 16.4 / Chrome 111 / Firefox 128 | plan `:53` | **UNSIGNED** |
| Gate: screenshot deltas accepted | plan `:120` | open until the PR |
| Leftover worktree | `git worktree list` | `../hc-npm-majors` at `da47c4a` (docs branch, merged). Do not reuse |

`src/frontend/package.json` (read, not run):

| Field | `package.json` | `package-lock.json` |
|---|---|---|
| `engines.node` | `>=22` | root `>=22` |
| tailwindcss | `^3.4.1` (dev) | 3.4.19 |
| tailwind-merge | `^2.2.0` | 2.6.0 |
| `@tailwindcss/*` | none | none |
| autoprefixer / postcss | `^10.4.16` / `^8.4.33` | 10.4.23 / 8.5.28 |
| class-variance-authority | `^0.7.0` | 0.7.1 |
| react-router-dom | `^6.21.0` | 6.30.6 (7.x after React Router 7) |
| vite | `^7.3.0` | 7.3.6 (needs Node `^20.19.0 \|\| >=22.12.0`) |
| vitest | `^4.0.16` | 4.1.11 |
| Tailwind 3 chain in the lock | — | `fast-glob` 3.3.3, `postcss-nested` 6.2.0, `chokidar` 3.6.0, `micromatch` 4.0.8, `braces` 3.0.3, `jiti` 1.21.7, `sucrase` 3.35.1 |

## 3. Owner questions still to ask

**Q1. The plan needs your approval to name `tailwind-merge` 2 → 3 as a second major in the same PR. Approve?**
- A. **(recommended)** Yes: `tailwind-merge@^3` moves with Tailwind 4 in one PR. `tailwind-merge` 2 does not know `shadow-xs` or `outline-hidden`; `cn()` is used in 39 files.
- B. No: Tailwind 4 only. The plan's stop gate then blocks the phase (it treats the two as inseparable).
- C. Yes, but as its own follow-up PR. Leaves a window where `cn()` merges v4 class names wrongly.

**Q2. Tailwind 4 needs Safari 16.4+, Chrome 111+, Firefox 128+. Older browsers show unstyled parts. Accept that floor?**
- A. **(recommended)** Accept, and state the floor in `docs/user/` in a follow-up docs commit.
- B. Accept, no docs change.
- C. Do not accept: Tailwind 4 does not run; the 5-6 high advisories on the Tailwind 3 chain stay open.

**Q3. Where are the before/after screenshots taken, and what is the time budget?** They need an encrypted backend (no SQLCipher wheel on Windows), a Linux `node_modules` that is not the Windows one, and `HC_E2E_CHROMIUM_PATH`. 10 shots × 2 runs.
- A. **(recommended)** A Linux-side clone outside `/mnt/c` (for example `~/hc-tw4-shots`), its own `npm ci`, throwaway script outside the repo, shots in `../tw4-shots/`. One L1 at a time on the 12 GB box. Budget: 2 capture runs.
- B. A CI job on a throwaway draft PR that uploads the shots as artifacts. Needs the CI-SEED style approval for a draft PR closed unmerged.
- C. You capture them by hand in the dev app before and after.

**Q4. Existing installs break after this merges.** `dev.ps1:626-635` installs only when `node_modules` is missing; after the merge `postcss.config.js` names `@tailwindcss/postcss`, which an old `node_modules` does not contain. Open owner item DEV-PS1-INSTALL.
- A. **(recommended)** Fix DEV-PS1-INSTALL first, as its own small PR before Tailwind 4 (install when the lockfile is newer than `node_modules`).
- B. Put the `dev.ps1` change in the Tailwind 4 PR. Breaks the plan's "frontend only" constraint; needs your word.
- C. Merge Tailwind 4 as planned and tell users to delete `node_modules` once. Record it in the PR body.

**Q5 (ask once for the sequence). `engines.node` `>=22` vs vite 7.3.6's `>=22.12.0`.** Same as NPM-AUDIT-2 Q4. Tailwind 4's own Node floor is **UNMEASURED** here (no registry access); the implementer reads it from the installed `tailwindcss/package.json` at Task 1.

## 4. Plan drift check (`docs/plans/2026-10-04-NPM-MAJORS-tailwind4.md`, measured at `90c502a`)

Tally: **MATCH 27, MOVED 0, CHANGED 3, UNMEASURED 2.** `git diff --stat 90c502a origin/main -- src/frontend/tailwind.config.js src/frontend/postcss.config.js src/frontend/src/styles src/frontend/src/utils/cn.ts src/frontend/src/components/ui src/frontend/package.json dev.ps1 .github/workflows/ci.yml` → empty. The scope table is still accurate; the plan's gaps are omissions, not drift (§7).

| # | Plan cites | Now | Verdict |
|---|---|---|---|
| 1 | `globals.css:7-10` four `--color-*` RGB triplets | same lines | MATCH |
| 2 | `globals.css:16-19` `--radius-sm/md/lg/xl` 8/12/16/24px | same | MATCH |
| 3 | `globals.css:49` body `@apply bg-surface text-ink` | same | MATCH |
| 4 | `grep -rn 'var(--\(color\|radius\)' src` → 0 | 0 | MATCH |
| 5 | `rounded-md/lg/xl` 169 hits, 43 files | 169 / 43 | MATCH |
| 6 | `--font-*` read at `:27,56,62` | same | MATCH |
| 7 | Directives `globals.css:1-3` | same | MATCH |
| 8 | Layers `:5` base, `:74` components, `:122` utilities | same | MATCH |
| 9 | Custom utilities "1 file, **2 consumer files**" | `min-h-target` is used in 1 `.tsx` (`Sidebar.tsx:68`); the only other file matching is `globals.css` itself. Same at `90c502a`, so the figure was not reproducible when written | CHANGED (plan figure, not code) |
| 10 | Variant-prefixed custom utilities → 0 | 0 | MATCH |
| 11 | `tailwind.config.js` contents (colors, fonts, fontSize, spacing 18/88/128, borderRadius xl/2xl/3xl, boxShadow ×4, 6 animations) | all present. The row omits `transitionDuration` 250/350 (`duration-250/350` → 0 uses) and `content` | MATCH |
| 12 | `postcss.config.js` `tailwindcss: {}` + `autoprefixer` | same | MATCH |
| 13 | `shadow-sm` 5 hits, 3 files | 5 / 3 | MATCH |
| 14 | `backdrop-blur-sm` at `DoseLoggingModal.tsx:79`, `VoiceFirstUseModal.tsx:18`, `SettingsPage.tsx:836,905,1002` | same 5 lines | MATCH |
| 15 | bare `rounded` 133 / 35 files; `rounded-sm` 1 / 1 | 133 / 35; 1 / 1 | MATCH |
| 16 | `outline-none` 42 / 20 files | 42 / 20 (one is `globals.css:66`, inside `@apply`) | MATCH |
| 17 | `flex-shrink/grow` 23 / 12 files | 23 / 12 | MATCH |
| 18 | bare `border` 107 / 38 files; `Input.tsx:43` | 107 / 38; line matches | MATCH |
| 19 | `ring-*` 107 / 23 files; 0 bare `ring` | 107 / 23; 0 | MATCH |
| 20 | `space-x/y` 150 / 35; `divide-*` 16 / 7 | same | MATCH |
| 21 | placeholder 29 hits, 16 files; `placeholder:` 6 hits, 5 files | same | MATCH |
| 22 | `hover:` 78 / 27 files | same | MATCH |
| 23 | Not present: `*-opacity-*`, `overflow-ellipsis`, `theme(`, `[--var]`, `!` prefix | all 0 | MATCH |
| 24 | `dev.ps1:281-282` Vite dev server launch | same | MATCH |
| 25 | Tech stack: Tailwind 3.4.19, tailwind-merge 2, PostCSS 8, Vite 7 | 3.4.19, 2.6.0, 8.5.28, 7.3.6 | MATCH |
| 26 | `utils/cn.ts` = `twMerge(clsx(inputs))` | same, 6 lines | MATCH |
| 27 | Task 0 `93def9e` ancestor | `0` | MATCH |
| 28 | Task 1 Step 2 expected files incl. `tailwind.config.js`, `postcss.config.js`, `src/styles/globals.css` | all exist; `main.tsx:4` is the only CSS import; 1 CSS file in `src` | MATCH |
| 29 | `:6` "5 high advisories remain on the Tailwind 3 chain" | 6 high on 2026-10-06 (`implementation-program.md:492`); which package is the 6th: UNMEASURED | CHANGED |
| 30 | `:3`, `:5` "not approved for execution" | Tailwind 4 approved at `owner-decisions:64`; `tailwind-merge` 3 not yet named | CHANGED (status text stale) |
| 31 | `:6`, `:19` targets `tailwindcss@4.3.3`, 4.3.x | current 4.x: UNMEASURED | UNMEASURED |
| 32 | Task 0 Step 2 vitest baseline (plan gives no number) | 195 / 34 today; expected 197 / 35 after React Router 7. Measure at Task 0 | UNMEASURED |

Counts asked for in the brief:

| Measure | Command (from `src/frontend/src`) | Now | Plan |
|---|---|---|---|
| Files importing `react-router-dom` | `grep -rl "react-router-dom" . \| wc -l` | 32 | n/a here (router plan: 30) |
| `@apply` | `grep -rnE '@apply' .` | 4 lines, 1 file (`globals.css:49,66,70,80`) | names `.glass-card` (`:80`) and body (`:49`); `:66` and `:70` not listed |
| `theme()` | `grep -rnE 'theme\(' .` | 0 | 0 |
| Files using a config colour token (`surface\|ink\|accent\|status\|dark`) | `grep -rlE '\b(bg\|text\|border\|ring\|…)-(surface\|ink\|accent\|status\|dark)\b'` | 53 files, 1046 hits | not counted in the plan |
| Custom shadows / fonts / animations | `shadow-(soft\|card\|elevated\|focus)` 27; `font-(display\|body\|mono)` 54; `animate-(fade-in\|…)` 3 | — | not counted |
| `cn(` callers | `grep -rlE '\bcn\(' .` | 39 files | "across `components/ui`" |
| `.tsx` with `className` | — | 58 of 91 | not counted |
| `<button` / `cursor-pointer` | — | 36 / 14 | "all `<button>`" |

**Plan amendments needed (do not edit the plan here):**
1. Task 0 Step 1: add "NPM-AUDIT-2 and React Router 7 merged"; cite `owner-decisions:64` plus the Q1 answer line.
2. Scope row "Custom CSS layers": 1 consumer `.tsx` (`Sidebar.tsx:68`), not 2.
3. Add scope rows for what the table omits: `bg-gradient-to-br` (2 hits: `Sidebar.tsx:44`, `ProfileSetup.tsx:224`), `index.html:19` body classes, `globals.css:66` (`outline-none` inside `@apply`), the duplicate `@keyframes slideUp` (`globals.css:110` vs the config keyframe), `transitionDuration`.
4. Task 2 Step 5: add a lockfile check for Linux native binaries of the new toolchain (§7 risk 1).
5. Task 3 Step 4 reviewers: add `security-reviewer` for the lockfile (new native packages).
6. File list: add the docs that name `tailwind.config.js` (§5), or state that they are a follow-up.
7. Expected vitest total as an absolute from the Task 0 baseline (+1, `cn.test.ts`).
8. Advisory count: "5 high" → the Task 0 measured list.

## 5. File ownership

| File | Change |
|---|---|
| `src/frontend/package.json` | `tailwindcss` → `^4.x`; `@tailwindcss/postcss` added; `autoprefixer` removed or unused; `tailwind-merge` → `^3` (Q1) |
| `src/frontend/package-lock.json` | rewritten |
| `src/frontend/postcss.config.js` | plugin swap |
| `src/frontend/tailwind.config.js` | deleted or reduced (becomes `@theme`) |
| `src/frontend/src/styles/globals.css` | `@import "tailwindcss"`, `@theme`, 8 variables deleted, compatibility base rules, `@utility` blocks |
| `src/frontend/src/__tests__/cn.test.ts` | **new**, 1 test |
| `src/frontend/index.html` | only if the upgrade tool renames a class at `:19` |
| Component and page `.tsx` files with renamed classes | upper bound 58 files with `className`; by rename: `outline-none` 20 files, bare `rounded` 35, `flex-shrink/grow` 12, `shadow-sm` 3, `backdrop-blur-sm` 3, `bg-gradient-to-*` 2. Exact list = `git status --short` after Task 1 |
| Docs naming `tailwind.config.js` as the token source (**not in the plan's list**) | `src/frontend/README.md:179`, `docs/brand/brand-guidelines.md:5,:121` go stale if the file is deleted |

Overlap with undone phases (this phase touches most `.tsx` files, so it conflicts textually with any open frontend branch):

| Phase | Shared files | Handling |
|---|---|---|
| NPM-AUDIT-2, React Router 7 | `package.json`, `package-lock.json`; `App.tsx` (`RouteFallback` classes `:82-92`) | serial, both before |
| **W-3** (trend labels) | `pages/TrendsDashboard.tsx`, `components/lab-interpreter/InterpretedTrendChart.tsx` (both in W-3's file table `:147-148`); new `components/TrendVerificationMarkers.tsx` (W-3 creates it; if W-3 lands after, its new classes must be written in v4 names); `services/types.ts` is not touched here (no classes) | merge one before the other starts; W-3's cited line ranges (`:145-156`, `:434-461`, `:479-487`, `:496-515`; `:36-43`, `:78-81`, `:158-166`) move if this lands first |
| **W-2** (doctor summary) | `pages/ExportPage.tsx` (W-2 cites `:108-121`) | same: cited lines can move; re-anchor in W-2's Task 0 |
| W-4 | `pages/ExplainAssistant.tsx:213,234` cited as evidence | line numbers only |
| P4-deferred | checks `SettingsPage.tsx`, `ProfileSetup.tsx`, `RecoveryCodeCard.tsx` by grep for copy strings; `src/frontend/README.md` | grep-based, survives class renames; README overlap if the docs fix is added |
| W-11a PR-3 | may add `npm run build` / lint to `ci.yml` (G-B4). If it lands first, this PR gets a CI build gate it otherwise lacks | order helps, no file overlap |
| W-7, W-8, W-3 | each cites `dev.ps1`; overlap only if Q4 = B | avoid B |
| Brand docs (no undone phase owns them) | `docs/brand/brand-guidelines.md` refresh trigger is `tailwind.config.js` colour tokens | docs follow-up |
| P5, P6, P7, W-10, W-10b, G-C1, G-C2, G-C3a, AUDIT-ORDER, PROHIBITED-PARAPHRASE, W-11a PR-1 | none | — |

Backend files: none. Backend collected delta expected **0** (1370).

## 6. Briefs

### 6.1 L1 brief (frontend sequence, phase 3 of 3)

```
You are the L1 Wave Orchestrator for the Wave 4 frontend sequence of the
Asclexis execution program. Follow docs/agentic/orchestration.md §3 exactly;
you are L1. This brief covers phase 3 of 3.
Phase: Tailwind 4 — docs/plans/2026-10-04-NPM-MAJORS-tailwind4.md, Tasks
0-3. Read audit/2026-09-25/waves/scaffold/TAILWIND-4.md §4 and §7 first.
Base: origin/main @ <sha>. Confirmed merged dependencies: NPM-AUDIT PR #38
(c4d407e), NPM-AUDIT-2 PR #<n> (<sha>), React Router 7 PR #<n> (<sha>);
verify each with `git merge-base --is-ancestor <sha> origin/main`. Any one
missing: STOP.
Signed gates (verbatim): owner-decisions:64 "NPM-AUDIT-2, then React Router 7,
then Tailwind 4, each as its own PR. Largest frontend churn of the three.";
tailwind-merge 3: "<Q1 answer, with its owner-decisions line>"; browser
floor: "<Q2 answer>"; dev.ps1 handling: "<Q4 answer>".
Unsigned: acceptance of screenshot deltas (the owner reviews the pairs
before merge; you do not accept a delta yourself). If the tailwind-merge
line is not in owner-decisions: STOP at Task 0.
Architectural: not in orchestration §5 (no data path, safety boundary or
schema). Owner-directed for this phase anyway (ledger 2026-10-07):
(1) Codex PLAN review before Task 1, model "6.1 sol", fallback "6-luna" at
high effort (confirm the IDs with `codex` first), handoff §7 procedure, at
most 2 rounds, outputs under audit/2026-09-25/reviews/TW4-r<N>-*; verify
each finding against the code; commit accepted plan amendments as the first
commit on the branch; (2) L0 has run a Fable adversarial review of this
brief (findings: <path>). Also run the Codex diff review before the PR
opens (handoff §7.2), focus: "no visible regression; every renamed class
keeps its v3 meaning; cn() still merges".
Worktree ../hc-tw4, branch feat/tailwind4, one PR. Do NOT reuse
../hc-npm-majors.
Spawn one implementer: Agent(subagent_type="general-purpose",
model="sonnet") with the brief below; one L2 at a time. Reviewers:
Agent(subagent_type="code-reviewer", model="opus") who also opens every
screenshot pair, and Agent(subagent_type="security-reviewer", model="opus")
for the lockfile (new native packages: registry.npmjs.org, sha512
integrity, install scripts listed) — the diff also renames classes inside
auth and export pages (ProfileSetup, RecoverProfile, ExportPage,
SettingsPage): confirm class names only, no logic.
Run the acceptance yourself, FROM WINDOWS, NOT WSL:
  powershell.exe -NoProfile -Command "cd C:\Users\DangT\Documents\GitHub\hc-tw4\src\frontend; Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue; npm ci; npm audit 2>&1 | Select-Object -Last 8; npx tsc --noEmit; echo tsc=$LASTEXITCODE; npm run lint; echo lint=$LASTEXITCODE; npm run build; echo build=$LASTEXITCODE; npx vitest run 2>&1 | Select-Object -Last 6"
  npx playwright test --list --project chromium   (count only; Windows)
Then the plan's Task 0 Step 3 grep loop (WSL is fine, read-only) before and
after, pasted side by side.
E2E and screenshots: <Q3 answer>. Never an unencrypted Windows run. On
Linux set HC_E2E_CHROMIUM_PATH and use a node_modules that is not the
Windows one. CI "E2E Smoke Tests" must pass on the PR; CI has no build
step, so the Windows `npm run build` output is the only build evidence.
Tests this phase adds: 1 vitest test in 1 new file
(src/__tests__/cn.test.ts): baseline + 1 (197/35 → 198/36 if React Router 7
left 197/35; use the measured baseline). Playwright delta: 0. Backend
collected delta: 0 (1370); no backend file changes; the backend suite is
not run.
Break-its you run yourself and paste:
  1. cn.test.ts on tailwind-merge 2 → RED; on 3 → GREEN.
  2. Put the 8 colliding variables back into globals.css → the computed
     `getComputedStyle(document.body).backgroundColor` check no longer
     returns rgb(250, 250, 248). Restore. If it still returns that value,
     the check cannot see the collision: STOP and report.
  3. Remove the border-colour compatibility rule → at least one screenshot
     pair with a bare `border` changes. Restore.
Lockfile checks (not in the plan; see scaffold §7 risk 1): list every
`@tailwindcss/oxide-*` and `lightningcss-*` entry; the linux-x64-gnu
variants must be recorded next to the win32 ones, and
`@rollup/rollup-linux-x64-gnu` + `@esbuild/linux-x64` must still be there.
package.json diff: only tailwindcss, @tailwindcss/postcss, autoprefixer,
tailwind-merge.
Record per-route pixel deltas in the PR body; attach every pair above 0.5%.
Write audit/2026-09-25/waves/wave-4-L1-B.md (append a phase-3 section).
Do not merge. Do not sign gates. Do not edit files outside the plan's
file list (no dev.ps1, no docs, unless a signed line says so).
Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)
```

### 6.2 L2 implementer brief

```
Implement docs/plans/2026-10-04-NPM-MAJORS-tailwind4.md, tasks 0-2 and
Task 3 Step 3 (cn.test.ts), in worktree
/mnt/c/Users/DangT/Documents/GitHub/hc-tw4 on branch feat/tailwind4.
No Python is needed. All npm / npx / vitest commands run from Windows
through powershell.exe, never from WSL. `npx @tailwindcss/upgrade@4` needs
a clean git tree: run `git status --short` first and paste it.
Re-run the plan's Task 0 Step 3 grep loop first and use its output as the
"before" column, not the plan's numbers.
Follow the plan literally, task by task. Test first for the one new test:
write src/__tests__/cn.test.ts (cn('outline-none', 'outline-hidden') →
'outline-hidden'), run it on tailwind-merge 2 and paste the FAIL, then
install tailwind-merge 3, then paste the PASS.
After Task 1, read the tool's whole diff before going on. Report, do not
fix silently: any class the tool renamed that the plan's scope table does
not list (known candidates: bg-gradient-to-br at Sidebar.tsx:44 and
ProfileSetup.tsx:224; index.html:19; outline-none inside @apply at
globals.css:66); any `@config` line the tool left; what it did with the
duplicate `@keyframes slideUp` (globals.css:110) and with
`transitionDuration`.
Commit exactly as the plan lists, 2 commits, explicit pathspecs taken from
`git status --short` (never `git add -A`):
  feat(frontend): migrate to Tailwind CSS 4 with the official upgrade tool
  fix(frontend): tailwind-merge 3, drop colliding :root vars, v3 border/cursor/placeholder defaults, @utility blocks
each ending with the Co-Authored-By line from the plan.
Ask-first files: none in scope. Class names, CSS and build config only: no
change to component logic, props, copy, services/api.ts or any backend file.
Stop and report, without working around it, if: the upgrade tool touches a
file outside src/frontend; a dependency other than tailwindcss,
@tailwindcss/postcss, autoprefixer or tailwind-merge moves;
`grep -rn 'var(--\(color\|radius\)' src` is non-zero; tsc, lint, build or
vitest fails; the vitest count is not baseline + 1; a Task 2 Step 4 count
is non-zero and you cannot explain each hit; the lockfile lacks the Linux
native packages.
Do NOT spawn agents. Do NOT push. Do NOT take screenshots unless L1 tells
you where (they need an encrypted backend on Linux).
Return: commits (sha + subject); the upgrade tool's full output; the
before/after grep table; tsc / lint / build exit codes; vitest totals
before and after; `npm audit` last line before and after; the package.json
diff; lockfile packages added and removed; cn.test.ts RED and GREEN output;
the list of unlisted renames; any deviation with its reason.
Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)
```

## 7. Risks / open findings the plan does not cover

| # | Risk | Evidence | Recurring-failures mode |
|---|---|---|---|
| 1 | **Linux native binaries missing from a Windows-made lockfile.** Tailwind 4's scanner and CSS engine ship per-platform optional packages (library knowledge; exact names UNMEASURED here). The NPM-AUDIT plan checks this for rollup / esbuild (its Review Focus 2); this plan has no such check. A lockfile without the Linux entries fails `npm ci` or the dev server in CI only | `2026-10-04-NPM-audit-fix.md:66,155`; no equivalent line in the Tailwind plan | §4 environment-dependent results |
| 2 | **Existing installs break, not just go stale.** `dev.ps1:626-635` skips `npm install` when `node_modules` exists. After merge, `postcss.config.js` requires `@tailwindcss/postcss`, absent from a Tailwind 3 `node_modules`; the Vite dev server is the product runtime (`dev.ps1:281-282`) | DEV-PS1-INSTALL, DEV-SERVER-RUNTIME (`implementation-program.md:500-501`) | §2 fix that creates the next bug; §10 feature never started |
| 3 | **CI cannot see a broken build or broken CSS.** "Frontend Tests" runs `tsc` and vitest only (`ci.yml:55-78`); `vitest.config.ts` sets no `css` option and jsdom does not apply Tailwind. E2E Smoke loads pages through the dev server but asserts behaviour, not colour or spacing | `ci.yml`; `vitest.config.ts`; plan Review Focus 1 | §1 green suite that could not have failed |
| 4 | **The body-background check may not see the collision in every route.** `index.html:19` also puts `bg-surface text-ink` on `<body>`, and `globals.css:50-52` paints a gradient `background-image` over it. The computed `backgroundColor` check is right, but only break-it 2 proves it fails when the variables come back | `index.html:19`; `globals.css:49-52` | §1 |
| 5 | **Renames outside the scope table.** `bg-gradient-to-br` (2 hits); `outline-none` inside `@apply` in the global `*:focus-visible` rule (`globals.css:66`) — if it is not renamed, focus outlines change on every element. Whether v4 keeps the old gradient name: UNMEASURED | measured 2026-10-07 | §3 figures asserted; §9 invariant at one site |
| 6 | **Dead CSS that can turn live.** `.glass-card`, `.subtle-noise`, `.stagger-animation`, `.text-balance` have 0 consumers in `.tsx`; `globals.css:110` defines `@keyframes slideUp` a second time with other timing than the config's `slide-up`. In v4 both land in one stylesheet; `animate-slide-up` users (3 `animate-*` hits) could pick up the wrong keyframes | `grep -rlE 'glass-card\|subtle-noise\|stagger-animation\|text-balance' --include=*.tsx` → 0 | §2 |
| 7 | **Accessibility target size.** `min-h-target` (44px, `Sidebar.tsx:68`) moves from `@layer utilities` to `@utility`. If the conversion is missed the class silently produces nothing; no test asserts 44px | `globals.css:122-129` | §1 |
| 8 | **Docs go stale.** `src/frontend/README.md:179` ("Implement in `tailwind.config.js`") and `docs/brand/brand-guidelines.md:5,:121` (refresh trigger and token source) name a file this phase deletes or empties. Not in the plan's file list | grep 2026-10-07 | §8 stale guidance |
| 9 | **Screenshots need data.** `/trends`, `/verify`, `/timeline`, `/search` with an empty profile show empty states, so most renamed classes never render. The plan names routes, not seeded content | plan Task 0 Step 4 | §1 |
| 10 | **`dark:` is used once** (`Skeleton.tsx:15`) and the config has no `darkMode` key. Both versions default to the `prefers-color-scheme` media query (library knowledge, UNMEASURED); capture one shot with a dark OS theme or state it was skipped | measured | §4 |
| 11 | **Merge order with W-3 / W-2.** Their plans cite line ranges in `TrendsDashboard.tsx`, `InterpretedTrendChart.tsx`, `ExportPage.tsx`; a rename pass does not move lines, but the `@tailwindcss/upgrade` tool may reflow long class strings | W-3 plan `:146-148`; W-2 plan `:75` | §8 |
| 12 | **12 GB host.** A Linux `npm ci` plus Chromium plus the backend for screenshots, next to another code L1, is the load that killed Wave 2's agents. Run the capture alone | orchestration §2 step 4 | process |
| 13 | **Program text still says "not approved"** (`implementation-program.md:426,:491`; plan `:3`) | read at `8d6f02e` | §8 |
| 14 | **E2E-MASTER-CORRUPT**: one unexplained E2E failure on main; rerun once before reading red as a CSS regression | `implementation-program.md:502` | §4 |

Next action: L0 asks Q1 (name `tailwind-merge` 3) and Q4 (DEV-PS1-INSTALL order) in one prompt and records both answers in owner-decisions.
