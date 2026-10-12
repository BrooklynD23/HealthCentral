# Wave 4 — L1-B report (frontend sequence)

**Date:** 2026-10-08. **L1:** L1-B (Opus). **Base:** `origin/main` = `777adf5`.
This dispatch had two phases, each its own worktree, branch and PR: Phase 1 NPM-AUDIT-2 (PR #52, merged 2026-10-09 → `f428a99`) and Phase 2 DEV-PS1-INSTALL (PR #55, merged 2026-10-09 → `87accae`). The file was committed on both branches, each copy holding its own phase; #55 merged second and kept both sections. Both merge-order notes are under one heading at the end.

Legend: **[L1]** = L1-B ran the command and read the output. **[L2]** = an implementer agent (Sonnet) reported it. **[R]** = a reviewer agent (Opus) reported it.

## Phase 2 — DEV-PS1-INSTALL

| | |
|---|---|
| Branch / worktree | `fix/dev-ps1-install` / `../hc-devps1` |
| Plan | `docs/plans/2026-10-08-DEV-PS1-install-on-lockfile-change.md` (first commit of the branch; amended after each review round) |
| Gate | DEV-PS1-FIRST (`docs/capstone-report/owner-decisions-2026-09-27.md:70`) |
| Result | `dev.ps1` STEP 5 reinstalls with `npm ci` when `package-lock.json` is not the one `node_modules` was installed from, and stops when the install fails |
| Backend collected delta | 0 (1370). No backend file changed; backend suite not run |

### What changed in `dev.ps1` (one hunk, `@@ -623,21 +623,101 @@`, STEP 5 only)

1. `Get-FrontendInstallReason`: `missing` / `incomplete` / `lockfile-changed` / `` (current). "Changed" = SHA-256 of `package-lock.json` differs from `node_modules\.asclexis-lockfile.sha256`. A content hash, not a timestamp: `git checkout` and clock skew move mtimes.
2. `Get-NpmApplicationPath`: the npm application (`npm.cmd` / `npm.exe`), never `& npm`.
3. `Install-FrontendDependencies`: refuses a linked `node_modules`; deletes the old marker; hashes the lockfile; runs `npm ci` inside the frontend folder only; checks the exit code and Vite; writes the marker last.

### Finding on `main` (pre-existing, fixed by this PR)

**`dev.ps1:635` on `main` cannot install on this machine.** [L1, Windows PowerShell 5.1.26100, npm 11.6.2]

```
A: main's exact line: & npm install 2>&1 | Out-Null
   exit=1 lockfile-created=False
   same line, output kept: [Unknown command: "pm"]
B: application resolution
   path=[C:\Program Files\nodejs\npm.cmd]
   & <path> install: exit=0 lockfile-created=True last=[found 0 vulnerabilities]
```

PowerShell resolves `npm` to the shim `npm.ps1`, which cuts `InvocationName.Length` characters off the statement text. Called through `&`, the invocation name is `&`, so npm receives `pm install`. A first-time `dev.ps1` run on `main` therefore ends in "npm install succeeded but Vite was not found". `& npm --version` at `dev.ps1:429` works only because npm answers `--version` whatever the command is; that line is outside this phase and unchanged. The first version of this branch copied `& npm ci`; ten green stubbed cases did not see it, and the first real run did.

### Commits (17 before the report commit)

| SHA | Subject | Author |
|---|---|---|
| `b1c2289` | docs: plan for DEV-PS1-INSTALL | L1 |
| `0269b98` | test(dev): check script for dev.ps1 frontend install decision | L2 |
| `e9df84e` | fix(dev): reinstall frontend dependencies when package-lock.json changed | L2 |
| `8314704`, `400bc44` | docs: plan — npm application, not the shim; partial tree wording | L1 |
| `93dc690` | test(dev): check script covers the real npm call and a missing npm | L2 |
| `26fbb34` | fix(dev): call the npm application so npm ci receives its arguments | L2 |
| `9533506`, `dc79200` | docs: plan — review round 1 | L1 |
| `f7cd9fa` | test(dev): check script drives the launcher's own npm lookup | L2 |
| `06c18c6` | fix(dev): clear the install record before npm ci; literal paths; no test-only parameter | L2 |
| `65d7fe4` | docs: plan — refuse a linked node_modules; hash before npm | L1 |
| `01198df` | test(dev): linked node_modules and lockfile changed mid-install | L2 |
| `c499759` | fix(dev): refuse a linked node_modules; record the hash taken before npm ci | L2 |
| `e39a9cb` | docs: plan — link test by LinkType; cases 21-22 | L1 |
| `ef7ab85` | test(dev): unwritable marker, missing frontend folder, removal before refusal | L2 |
| `8e35d0a` | fix(dev): detect a linked node_modules by LinkType; never run npm outside the frontend folder | L2 |

Each code change was preceded by its test commit and a red run [L2].

### Check script [L1] — `scripts/check_dev_ps1_install.ps1`, at `8e35d0a`

Loads the three functions out of `dev.ps1` with the PowerShell parser (the launcher never runs). npm is a stub `npm.cmd` put first on PATH, so the launcher's own lookup is under test.

```
PASS  1 no node_modules -> missing
PASS  2 no vite -> incomplete
PASS  3 marker missing -> lockfile-changed
PASS  4 marker matches -> skip
PASS  5 lockfile edited -> lockfile-changed
PASS  6 mtime one day back and forward, content same -> skip both
PASS  7 lockfile deleted -> lockfile-changed
PASS  8 npm ci fails, old vite + old marker -> false, marker gone
PASS  9 npm ci ok, vite created -> true, marker = hash, then skip
PASS  10 npm ci ok, no vite -> false, no marker
PASS  11 npm not on PATH, stale exit 0 -> false, no marker
PASS  12 npm receives exactly: ci
PASS  13 npm ci ok but writes to stderr -> true, marker written
PASS  14 npm.cmd chosen over extensionless npm and npm.ps1 earlier on PATH
PASS  15 folder name with space and brackets -> true, then skip
PASS  19 node_modules is a junction -> false, target untouched, npm not run
PASS  20 lockfile changed mid-install -> true, marker = hash before npm, then lockfile-changed
PASS  21 marker cannot be written -> true (one output), no error shown, then lockfile-changed
PASS  22 missing frontend folder -> false, npm not run in the current folder
PASS  16 empty marker -> lockfile-changed, no error record
PASS  17 Get-NpmApplicationPath (real PATH) -> existing .cmd/.exe
PASS  18 npm application ci --help -> exit 0, mentions npm ci
checks: 22/22
check=0
```

Red before green, per round [L2]: round 1 `checks: 0/2`, exit 1 (functions absent); round 2 `10/14` (9, 12, 13, 14 red); round 3 `15/18` (8, 15, 16 red); round 4 `18/20` (19, 20 red); round 5 `21/22` (22 red).

Break-its (mutate `dev.ps1`, run, restore) — all red:

| Mutation | Fails | By |
|---|---|---|
| `-ne $recorded` → `-eq` | 4, 5, 6, 9, 15, 16 | L2 |
| delete `if ($npmExit -ne 0)` block | 8, 11 | L2 |
| `$npmCommand = "npm"` (the shim defect) | 14 (`shimRan=True`) | L2, **L1**, R |
| delete the marker `Remove-Item` | 8 | L2, R |
| initial `$npmExit = 0` | 11 | L2, R |
| delete the link check | 19 (`npmRan=True`) | L2, R |
| hash taken after npm | 20 | L2, R |
| marker `Remove-Item` above the link check | 19 (`seedKept=False`) | L2, R |
| bare `Set-Content` (no try/catch) | 21 | L2, R |
| `Push-Location` without `-ErrorAction Stop` | 22 (`npmRan=True nodeModulesInCwd=True`) | L2, R |

One mutant stays green: the link test reverted to the `ReparsePoint` attribute → 22/22 [R]. See findings.

### Manual acceptance [L1] — Windows, real `npm ci`, `-Live` mode, no server started, at `8e35d0a`

```
--- (a) fresh tree                      (node_modules removed first)
reason: [missing]
install result: True
marker: 318A8D6B06B5E8AEF7CC703755AB348574EEBB68335C28423F6133FF4B01C17D
reason after: []
real 1m30.162s   live=0
sha256sum package-lock.json -> 318A8D6B06B5E8AEF7CC703755AB348574EEBB68335C28423F6133FF4B01C17D
--- (b) again
reason: []
install result: skipped (tree is current)
real 0m0.677s    live=0
--- (c) marker = wrong hash             (what a changed lockfile looks like; the tracked file stays untouched)
reason: [lockfile-changed]
install result: True
marker: 318A8D6B...C17D
reason after: []
real 1m1.515s    live=0
--- (d) registry unreachable (127.0.0.1:9), empty npm cache, marker invalidated
reason: [lockfile-changed]
  [ERR] npm ci failed (exit code 1). Frontend dependencies are not installed.
      npm error Exit handler never called!
      npm error This is an error with npm itself. Please report this error at:
      npm error   <https://github.com/npm/cli/issues>
  [ERR] Check your internet connection, close other Asclexis windows, and run again.
install result: False
marker: (absent)
reason after: [incomplete]
live=1
--- restore
reason: [incomplete]
install result: True
reason after: []
live=0
npm ls --depth=0 -> npmls=0 ;  npx tsc --noEmit -> tsc=0
git status --short -> (empty)
```

The first real run, on `e9df84e`, failed with `Unknown command: "pm"` (`live=1`); that is how the shim defect was found.

Scope checks [L1]: `git diff origin/main..HEAD -- dev.ps1 | grep '^@@'` → one hunk, `@@ -623,21 +623,101 @@`; non-ASCII grep on both files → `nonascii=1` (none); `file` → ASCII text, both; parser error count for `dev.ps1` → `0`.

Docs gates [L1]: `python3 scripts/generate_docs_index.py` → 0; `python3 scripts/docs_lint.py --link-graph` → 0; `python3 scripts/docs_lint.py` → 0 ("Docs lint passed."); `python3 scripts/generate_docs_index.py --check` → 0.

### Not tested

- A full `dev.ps1` run (it starts both servers and opens a browser; no dry-run switch). STEP 5 was exercised through its three functions; the 8-line calling block (`switch`, `Read-Host`, `exit 1`) was read, not run.
- PowerShell 7. A machine with a dev server holding `node_modules` files open during `npm ci`.
- `LinkType` for a directory symlink or a volume mount point (creating either needs administrator rights here).
- CI does not run the check script (CI is Linux; wiring it in touches `ci.yml`, outside this phase).

### Reviews

| Reviewer | Verdict | What changed because of it |
|---|---|---|
| code-reviewer, round 1 [R] (at `400bc44`) | REQUEST CHANGES, 1 major | The check stayed 14/14 with the npm lookup reverted to `"npm"` (a test-only `-NpmCommand` parameter hid it). Parameter removed; stub on PATH. Also: old marker survived a failed install; `[ ]` in a folder name read as a wildcard; empty marker raised an error; check script ran under `Stop` |
| security-reviewer [R] (at `dc79200`) | APPROVE (0 critical, 0 high, 1 medium, 4 low) | Medium: `npm ci` empties the **target** of a junctioned `node_modules`; main's `Remove-Item` removed only the link. Guard added. Low: hash taken after npm → now before |
| code-reviewer, round 2 [R] (at `c499759`) | REQUEST CHANGES, 1 major | The guard tested the `ReparsePoint` attribute, which OneDrive-synced plain folders carry (4 of 4 sampled): installs under a synced Documents would have been refused. Now `LinkType`. Also: a missing frontend folder let `npm ci` run in the caller's folder |
| code-reviewer, round 3 [R] (at `8e35d0a`) | **APPROVE** (0 blocker, 0 major, 3 minor) | Plan wording fixed; two minors left as findings 2 and 4 below |

The security reviewer saw `dc79200`, not the final head. Its two fixes and the round-2 changes were reviewed by the code reviewer in rounds 2 and 3 (junction, `New-Item` junction, dangling junction: refused; 6 of 6 OneDrive folders: not refused).

### Findings not fixed (owner items)

| # | Finding | Evidence | Note |
|---|---|---|---|
| 1 | `dev.ps1:429` still calls `& npm --version` through the `npm.ps1` shim; `dev.ps1:781` resolves npm unfiltered | L1 probe; security review L4 | outside STEP 5. Works today only because of how npm treats `--version` |
| 2 | No check case fails if the link test reverts to the `ReparsePoint` attribute | round-3 review: mutant 22/22 | needs a non-link folder with that attribute; only OneDrive provides one here |
| 3 | A marker path that is a directory prints one raw access-denied line (`dev.ps1` `Get-Content` in `Get-FrontendInstallReason`); result is still `lockfile-changed` | L2, check case 21 output | corner case; safe direction |
| 4 | First start after merge says "Frontend dependencies changed since the last install" on every existing install, though nothing changed | round-3 review M3 | wording only |
| 5 | `npm.cmd` without a sibling `node.exe` finds `node` in the current folder first | security review L1 (`planted ran=True`) | needs write access to `src/frontend`, which already means code execution via `vite.config.ts` |
| 6 | npm's last 15 output lines are printed unmasked on failure (could show a proxy URL with credentials from the user's own `.npmrc`) | security review L2 | user's own console only |
| 7 | An offline machine cannot start after a lockfile change (before: it started on stale packages) | plan, "Cost accepted"; acceptance (d) | the behaviour DEV-PS1-FIRST asks for; worth a line in the user docs when Tailwind 4 ships |
| 8 | The backend half may have the same gap for `requirements.txt` | not read in this phase (UNMEASURED) | — |
| 9 | CI does not run `scripts/check_dev_ps1_install.ps1` | `.github/workflows/ci.yml` | GitHub's Windows runners could; outside this phase |
| 10 | DEV-SERVER-RUNTIME unchanged: the product frontend is still served by the Vite dev server | `implementation-program.md:501` | packaging (G-C4) |

## Phase 1 — NPM-AUDIT-2

| | |
|---|---|
| Branch / worktree | `fix/npm-audit-2` / `../hc-npm-audit-2` |
| Plan | `docs/plans/2026-10-04-NPM-audit-fix.md` + "Amendment 2 (NPM-AUDIT-2)" |
| Gates | NPM-MAJORS-RUN, FE-SEQ, MAJORS-TIED (`docs/capstone-report/owner-decisions-2026-09-27.md:64,69,72`). No approved major in this phase |
| Result | 1 package moved: `source-map-js` 1.2.1 → 1.2.2. `npm audit` 10 → 9. `package.json` unchanged |
| Backend collected delta | 0 (1370). No backend file changed; backend suite not run |

### Commits

| SHA | Subject | Author |
|---|---|---|
| `29653a4` | docs: NPM-AUDIT-2 Amendment 2 to the npm audit fix plan | L1 |
| `eef583e` | fix(deps): apply non-breaking npm audit fixes in frontend (NPM-AUDIT-2) | L2 |
| `28c1e38` | docs: Amendment 2 — lockfile diff that can fail, acceptance line that stops | L1, after code review |
| `8af03f3` | docs: Amendment 2 — exact registry tarball, downgrade and field checks | L1, after security review |
| (this commit) | docs: Amendment 2 minor fixes + wave report | L1, after re-review |

### Task 0 [L1]

| Command | Output |
|---|---|
| `git merge-base --is-ancestor c4d407e origin/main; echo $?` | `0` |
| `node --version`, `npm --version` (Windows) | `v22.20.0`, `11.6.2` |
| `npm ci` at `777adf5` | `npmci=0` |
| `npx vitest run` at `777adf5` | `Test Files 34 passed (34)`, `Tests 195 passed (195)`, `vitest=0` |
| `npm audit` at `777adf5` | `10 vulnerabilities (4 moderate, 6 high)`, exit `1` |

### `npm audit` before / after, per package [L1, from `npm audit --json`; L2 measured the same]

| Package | Before (`777adf5`) | Fix per npm | After (`eef583e`) |
|---|---|---|---|
| source-map-js | high | non-major | **gone** (1.2.2; GHSA-68fv-2mgg-jv7q) |
| fast-glob | high | non-major (`fixAvailable: true`) | high, still listed, still `true` |
| postcss-nested | moderate | non-major (`fixAvailable: true`) | moderate, still listed, still `true` |
| tailwindcss | high | `tailwindcss@4.3.3` major | high |
| braces | high | via `tailwindcss@4.3.3` major | high |
| chokidar | high | via `tailwindcss@4.3.3` major | high |
| micromatch | high | via `tailwindcss@4.3.3` major | high |
| postcss-selector-parser | moderate | via `tailwindcss@4.3.3` major | moderate |
| react-router-dom | moderate | `react-router-dom@7.18.4` major | moderate |
| react-router | moderate | via `react-router-dom@7.18.4` major | moderate |
| **Total** | **10 (4 moderate, 6 high)** | | **9 (4 moderate, 5 high)** |

No package appears after that was absent before. `npm audit fix` exit code `1` (advisories remain that need `--force`; `--force` was not run) [L2].

`fast-glob` and `postcss-nested` stay: npm marks them fixable, but they carry no advisory of their own. They are listed because they depend on `micromatch` and `postcss-selector-parser`, whose fixes need Tailwind 4. NPM-AUDIT-DRIFT's "3 fixable" (`implementation-program.md:492`) was therefore 1 in practice.

### Lockfile diff [L1] — full output

Script: the `python` block in Amendment 2, extracted from the plan with the plan's own command. sha256 `6b56ea18e220fce972f1d1ce2539d640faf70caafabd9d52c7ed5fb7750c1221`. Inputs: `git show origin/main:src/frontend/package-lock.json` and `git show HEAD:src/frontend/package-lock.json`.

```
packages keys: old=485 new=485
ADDED (0)
REMOVED (0)
CHANGED, any field (1)
  node_modules/source-map-js 1.2.1 -> 1.2.2 fields=['integrity', 'resolved', 'version']
hasInstallScript: old=['node_modules/esbuild', 'node_modules/fsevents', 'node_modules/playwright/node_modules/fsevents']
hasInstallScript GAINED: []
source shape: 485/485 entries are the registry.npmjs.org tarball of their own name and version, sha512
STOP-FLAGS: 0
lockdiff=0
```

Majors: **0**. Added: 0. Removed: 0. New install scripts: 0. `git diff --quiet origin/main..HEAD -- src/frontend/package.json` → `0` (unchanged). Linux natives in the lockfile (`@rollup/rollup-linux-x64-gnu`, `@esbuild/linux-x64`): 2 [L2].

The script can fail: 27 mutated copies of the `origin/main` lockfile behaved as expected [L1] (4 must-pass, 23 must-stop; list in Amendment 2). The re-reviewer ran 49 mutations of its own [R].

### Acceptance [L1] — the plan's rule 5 line, run verbatim from the plan at `eef583e`

```
npmci=0
tsc=0
✖ 5 problems (0 errors, 5 warnings)
lint=0
✓ built in 1m 19s
build=0
 Test Files  34 passed (34)
      Tests  195 passed (195)
vitest=0
failed=0
acceptance=0
```

The 5 lint warnings are `no-explicit-any` in `src/hooks/useSpeechRecognition.ts:25,32,65,70`, present on main. The line can fail: the same accumulator with `cmd /c exit 7` in the middle prints `b=7`, `failed=1`, `acceptance=1` [L1]. L2's own run before committing: `npmci=0 tsc=0 lint=0 build=0 vitest=0`, 34 / 195 [L2]. `npm ls source-map-js`: 1.2.2 under `postcss@8.5.28` and (deduped) `css-tree@3.1.0` [L1].

Break-it: not meaningful. The change is lockfile-only and adds no test; the evidence that it did something is the per-package table above.

Docs gates [L1]: `python3 scripts/generate_docs_index.py` → 0; `python3 scripts/docs_lint.py --link-graph` → 0; `python3 scripts/docs_lint.py` → 0 ("Docs lint passed."); `python3 scripts/generate_docs_index.py --check` → 0. `docs/INDEX.md` and `docs/_link_graph.json` came out unchanged (no document added), so they are not in this branch's diff.

E2E: not run locally (no SQLCipher wheel on Windows). CI "E2E Smoke Tests" on the PR is the evidence; see the PR.

### Reviews

| Reviewer | Verdict | What changed because of it |
|---|---|---|
| code-reviewer, round 1 [R] | REQUEST CHANGES (0 blocker, 3 major, 2 minor) — lockfile change clean and in scope | Amendment 2's first diff script saw only entries whose `version` changed, did not count a gained install script, and missed `0.x` on added paths; the acceptance line could not exit non-zero; `$TMP` undefined. All fixed in `28c1e38` |
| security-reviewer [R] | APPROVE the lockfile (0 critical, 0 high). 5 medium on the gate script | `resolved` checked by host prefix only; downgrades; extra fields on a bumped entry; top-level keys. Fixed in `8af03f3`. Integrity-versus-registry stays a reviewer step (named in Amendment 2) |
| code-reviewer, round 2 [R] | APPROVE (all 9 earlier items closed; 4 minor) | Prerelease moves, empty extraction on CRLF, two wording gaps. Fixed in this commit |

Security reviewer's checks of `source-map-js@1.2.2` [R]: lockfile integrity equals the registry packument's `dist.integrity` and the hash of the downloaded tarball; published 2026-09-30 by `7rulnik`, the publisher of 1.2.0 and 1.2.1; no install scripts, no dependencies, not deprecated; advisory range `>=1.0.0 <1.2.2`. Not verified by the reviewer: the `source-node.js` hunk of the 1.2.1 → 1.2.2 source diff, the registry signature, and provenance (none is published for either version).

### Findings not fixed (owner items)

| # | Finding | Evidence | Note |
|---|---|---|---|
| 1 | 9 advisories remain; all need Tailwind 4 or React Router 7 | table above | the next two phases of this sequence |
| 2 | Existing installs do not get 1.2.2: `dev.ps1` installs only when `node_modules` or Vite is missing | `dev.ps1:626-635` @`777adf5` | Phase 2 of this dispatch (DEV-PS1-INSTALL) |
| 3 | `engines.node` is `>=22`; vite 7.3.6 needs `>=22.12.0` | `src/frontend/package.json:6-8` | a `package.json` edit; not made (pack Q4 unanswered) |
| 4 | `SettingsPage.tsx:952-954` passes `a.url` to `<Link to>` after only `startsWith('/')`; `/\host` passes that test (GHSA-wrjc-x8rr-h8h6 sink). The only producer found is the literal `"/settings"` at `src/backend/modules/environment_diagnostics.py:244` | security review [R]; not re-read by L1 | REVIEWS-2026-10-07 §1 says this line stays unchanged; closes with React Router 7 |
| 5 | CI does not gate on `npm audit`, `npm run build` or `npm run lint` | `.github/workflows/ci.yml` frontend jobs (pack §4) | W-11a / GATE-15 |
| 6 | The lockfile-diff script exists only inside the plan document. A PR could weaken it and pass it in one diff | security review LOW 6 | mitigated here by the sha256 in the PR body; a tracked `scripts/` file is outside this phase's file list. Worth doing before React Router 7 reuses it |
| 7 | `npm audit` counts move daily on a byte-identical lockfile | 7 → 10 between 2026-10-04 and 2026-10-06 | the figures here are true for 2026-10-08 only |

## Merge order

Written before either PR merged; actual order was #52 then #55 (L0 notes, 2026-10-09).

**Phase 2 — DEV-PS1-INSTALL (PR #55)**

1. No dependency between this PR and NPM-AUDIT-2 (PR #52). Disjoint files, except this report (same path on both branches, different content: the second to merge keeps both sections) and `docs/INDEX.md` / `docs/_link_graph.json` (changed only here; if another docs PR merges first, regenerate with `python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py --link-graph`).
2. Tailwind 4 waits for this PR (gate DEV-PS1-FIRST). React Router 7 waits for PR #52 only.
3. Effect on merge day: every existing install reinstalls once on its next start (no marker yet), about 1 to 1.5 minutes here with a warm npm cache. That is also when PR #52's `source-map-js` fix reaches it.

Rollback: `git revert <merge sha>`. The marker file left in `node_modules` is inert. Note that reverting restores `& npm install`, which does not work with npm 11.6.2 under Windows PowerShell 5.1 (see the finding on `main`).

**Phase 1 — NPM-AUDIT-2 (PR #52)**

1. NPM-AUDIT-2 has no dependency on DEV-PS1-INSTALL; either can merge first. The files are disjoint except this report and (for DEV-PS1-INSTALL only) `docs/INDEX.md` / `docs/_link_graph.json`.
2. This branch does not change `docs/INDEX.md`. DEV-PS1-INSTALL does (new plan file). If NPM-AUDIT-2 merges second, no index refresh is needed for it; the second PR to merge resolves this report file by keeping both phase sections.
3. React Router 7 and Tailwind 4 branch from `origin/main` after this merges (all three rewrite `package-lock.json`). Tailwind 4 also waits for DEV-PS1-INSTALL (gate DEV-PS1-FIRST).

Rollback: `git revert <merge sha>`, then reinstall (`npm ci` in `src/frontend`).
