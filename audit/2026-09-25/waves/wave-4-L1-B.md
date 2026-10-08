# Wave 4 — L1-B report (frontend sequence)

**Date:** 2026-10-08. **L1:** L1-B (Opus). **Base:** `origin/main` = `777adf5`.
This dispatch has two phases, each its own worktree, branch and PR. This file is committed on both branches; each copy holds its own phase. The copy on `fix/npm-audit-2` (PR #52) holds Phase 1. Whichever PR merges second keeps both sections.

Legend: **[L1]** = L1-B ran the command and read the output. **[L2]** = the implementer agent (Sonnet) reported it. **[R]** = a reviewer agent (Opus) reported it.

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

### Merge order

1. No dependency between this PR and NPM-AUDIT-2 (PR #52). Disjoint files, except this report (same path on both branches, different content: the second to merge keeps both sections) and `docs/INDEX.md` / `docs/_link_graph.json` (changed only here; if another docs PR merges first, regenerate with `python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py --link-graph`).
2. Tailwind 4 waits for this PR (gate DEV-PS1-FIRST). React Router 7 waits for PR #52 only.
3. Effect on merge day: every existing install reinstalls once on its next start (no marker yet), about 1 to 1.5 minutes here with a warm npm cache. That is also when PR #52's `source-map-js` fix reaches it.

Rollback: `git revert <merge sha>`. The marker file left in `node_modules` is inert. Note that reverting restores `& npm install`, which does not work with npm 11.6.2 under Windows PowerShell 5.1 (see the finding on `main`).
