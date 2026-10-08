# DEV-PS1-INSTALL — `dev.ps1` Reinstalls Frontend Dependencies When the Lockfile Changed

> **For agentic workers:** REQUIRED SUB-SKILLS: superpowers:test-driven-development, superpowers:verification-before-completion. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** owner-scheduled 2026-10-07 (gate DEV-PS1-FIRST in [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md)). Wave 4, L1-B.
**Source:** owner item DEV-PS1-INSTALL ([implementation-program.md](../capstone-report/implementation-program.md)): `dev.ps1` installs only when `node_modules` or the Vite binary is missing, so an existing install keeps the old packages after a lockfile change merges.
**Architectural:** no. No Codex review. `code-reviewer` + `security-reviewer` required (the script runs on patient machines).

**Goal:** `dev.ps1` reinstalls frontend dependencies when `src/frontend/package-lock.json` differs from the lockfile the current `node_modules` was installed from, and refuses to launch when that install fails.

**Tech stack:** Windows PowerShell 5.1 (what `dev.bat` starts), npm 11.6.2, Node v22.20.0 (measured 2026-10-08). No new dependency, no test framework.

## Global Constraints

- Owner gate DEV-PS1-FIRST (2026-10-07), verbatim: "A small PR before Tailwind 4 (owner item DEV-PS1-INSTALL): dev.ps1 reinstalls when package-lock.json is newer than node_modules. Tailwind 4 refuses to start until it is merged. Also makes the npm audit fixes actually reach existing installs."
- Edit **only** STEP 5 of `dev.ps1` (`:617-648` at `777adf5`). Do not touch the backend half, the SQLCipher handling (`:471-500`, `:586-593`), the port step, or how Vite is launched (`:728`).
- `dev.ps1` stays one self-contained ASCII file: no dot-sourced helper, no non-ASCII character (Windows PowerShell 5.1 reads a BOM-less file as ANSI).
- No network call other than the npm registry the script already uses. No user data is deleted: the only directory removed is `src/frontend/node_modules`.
- Keep the three existing messages: "Installing frontend dependencies (first-time setup) ...", "node_modules exists but looks incomplete. Reinstalling ...", "Frontend dependencies already installed", and the two Vite-not-found error lines.
- Backend collected count stays **1370**; no backend file changes, so `CLAUDE.md` / `AGENT.md` do not change.
- Stage with explicit pathspecs. Never `git add -A`.

## Design decisions

| Question | Decision | Why |
|---|---|---|
| How is "lockfile changed" detected? | SHA-256 of `package-lock.json` (`Get-FileHash`), compared with the hash stored in `node_modules\.asclexis-lockfile.sha256` after the last successful install | The owner's wording is "newer than node_modules". A timestamp says that only when clocks and mtimes are honest: `git checkout`, an unzip or a copied folder rewrites mtimes, and clock skew can make an old lockfile look new or a new one look old. The missed case (new lockfile, older mtime) is the dangerous one: the app launches on packages the lockfile no longer names. A content hash has no missed case. |
| Why not npm's own `node_modules\.package-lock.json`? | Not used | It is npm's private format (no root entry, extra fields), not a copy of `package-lock.json`, so a content comparison needs a parser, and its timestamp has the problem above. |
| Where does the marker live? | Inside `node_modules` | Deleting `node_modules` deletes the marker, so the two cannot disagree. `node_modules/` is git-ignored (`.gitignore:59`). |
| Marker missing, `node_modules` present | Install once | This is every existing install on the day this merges: the tree is unverified. It is how the NPM-AUDIT fixes reach existing installs. Cost: one reinstall per machine. |
| `npm ci` or `npm install`? | `npm ci`, for all three cases (first time, incomplete, lockfile changed) | `npm ci` installs exactly the committed lockfile and never rewrites it. `npm install` may rewrite `package-lock.json` on a patient machine, which would then differ from the repository and from the stored hash. `npm ci` removes `node_modules` first. A failed run can still leave a partial tree (measured in Task 3 (d): 288 package folders, no Vite), but never a marker (the old one is deleted before npm starts), so the script stops with exit 1 and the next run reports `incomplete` or `lockfile-changed` and installs again. A partial tree is never launched. CI already runs `npm ci` on every PR (`ci.yml` frontend jobs), so the lockfile is known to be in sync with `package.json`. |
| Install failure | The old marker is deleted before npm starts. Check npm's exit code, print the last lines of npm's output, stop with exit 1. The marker is written only after exit code 0 **and** Vite is present | Today the exit code is ignored and only Vite's presence is checked. With a reinstall over an existing tree that check would pass on the old Vite. |
| How is npm called? | Through the npm **application** (`npm.cmd`, or `npm.exe`), resolved with `Get-Command npm -CommandType Application`, never through `& npm` | Measured 2026-10-08 (Windows PowerShell 5.1.26100, npm 11.6.2): PowerShell resolves `npm` to the shim `npm.ps1` first, and that shim rebuilds its arguments from the statement text by cutting off `InvocationName.Length` characters. Called as `& npm ci`, the invocation name is `&`, so npm receives `pm ci` and prints `Unknown command: "pm"`, exit 1. The line on `main` today, `& npm install 2>&1 \| Out-Null` (`dev.ps1:635`), fails the same way: in an empty project it exits 1 and creates nothing. So a first-time install through `dev.ps1` is already broken with this npm; the old code then prints "npm install succeeded but Vite was not found". `& npm --version` (`:429`) works only because npm answers `--version` whatever the command is. The first version of this plan copied `& npm`; the stubbed check cases could not see it and the first real run did (Task 3). |
| Marker cannot be written (read-only folder, file locked) | One warning; the app starts, because the tree is correct. The next start reinstalls | Refusing to launch a correct tree would be the wrong failure. |
| Paths | `-LiteralPath` in the three functions | A folder name with `[` `]` is a wildcard pattern to `-Path`; measured in review: a valid tree in `Asclexis [1]` read as `missing` and reinstalled on every run. |
| `package-lock.json` missing | The decision returns "install"; `npm ci` then fails with its own message and the script stops | An incomplete download. No guess is made. |

Cost accepted: `npm ci` needs the registry (or npm's cache). A machine that is offline on the first run after a lockfile change gets a clear error and does not launch; before this change it launched on the stale packages. That is the behaviour the gate asks for.

## Files (the complete list)

| File | Change |
|---|---|
| `dev.ps1` | STEP 5 only: three functions plus the rewritten install block |
| `scripts/check_dev_ps1_install.ps1` | New. Self-contained check script (no Pester). Loads the three functions out of `dev.ps1` with the PowerShell parser, so it tests the shipped code without running the launcher. The install cases call a real stub `.cmd` process, and two cases call the real npm with `--version` |
| `docs/plans/2026-10-08-DEV-PS1-install-on-lockfile-change.md` | This plan |
| `docs/INDEX.md`, `docs/_link_graph.json` | Regenerated for the new plan |
| `audit/2026-09-25/waves/wave-4-L1-B.md` | L1 wave report (added in the last commit before the PR) |

Prior art checked: `grep -rn "dev.ps1" src/backend/tests scripts tests .github` returns two hits at `777adf5`, neither a test of the launcher: `src/backend/tests/test_claude_agent_definitions.py:83` (an agent's write scope) and `scripts/harness_drift_check.py:44` (a filename allowlist). No existing test pattern, so the check script is new.

## Before / After

**Before** (`dev.ps1:621-648` at `777adf5`):

```powershell
$viteBin = Join-Path $FRONTEND_DIR "node_modules\.bin\vite.cmd"
$viteScript = Join-Path $FRONTEND_DIR "node_modules\vite\bin\vite.js"
$nodeModulesDir = Join-Path $FRONTEND_DIR "node_modules"

# Install if node_modules missing OR vite binary missing (corrupted install)
if (-not (Test-Path $nodeModulesDir) -or -not (Test-Path $viteBin) -or -not (Test-Path $viteScript)) {
    if (Test-Path $nodeModulesDir) {
        Write-Warn "node_modules exists but looks incomplete. Reinstalling ..."
        Remove-Item $nodeModulesDir -Recurse -Force -ErrorAction SilentlyContinue
    } else {
        Write-Status "Installing frontend dependencies (first-time setup) ..."
    }
    Push-Location $FRONTEND_DIR
    & npm install 2>&1 | Out-Null
    Pop-Location

    if (-not (Test-Path $viteBin) -or -not (Test-Path $viteScript)) {
        Write-Err "npm install succeeded but Vite was not found."
        Write-Err "Try deleting src\frontend\node_modules and running again."
        Read-Host "  Press Enter to exit"
        exit 1
    }
    Write-Ok "Frontend dependencies installed"
} else {
    Write-Ok "Frontend dependencies already installed"
}
```

**After** (same place). The three assignments `$viteBin`, `$viteScript`, `$nodeModulesDir` at `:622-624` stay exactly as they are, above this block: the launch step reads `$viteScript` at `:731` and `:843`. Everything from the `# Install if node_modules missing` comment to the closing `}` is replaced by:

```powershell
# Decides whether frontend dependencies must be (re)installed.
# Returns "" when the tree is current, otherwise the reason:
#   "missing"          - no node_modules
#   "incomplete"       - node_modules without the Vite binary
#   "lockfile-changed" - package-lock.json is not the one node_modules was installed from
function Get-FrontendInstallReason {
    param([string]$FrontendDir)
    $modules = Join-Path $FrontendDir "node_modules"
    if (-not (Test-Path -LiteralPath $modules)) { return "missing" }
    if (-not (Test-Path -LiteralPath (Join-Path $modules ".bin\vite.cmd")) -or
        -not (Test-Path -LiteralPath (Join-Path $modules "vite\bin\vite.js"))) { return "incomplete" }
    $lockFile = Join-Path $FrontendDir "package-lock.json"
    $marker   = Join-Path $modules ".asclexis-lockfile.sha256"
    if (-not (Test-Path -LiteralPath $lockFile) -or -not (Test-Path -LiteralPath $marker)) { return "lockfile-changed" }
    $current  = (Get-FileHash -LiteralPath $lockFile -Algorithm SHA256).Hash
    $recorded = "$(Get-Content -LiteralPath $marker -TotalCount 1)".Trim()
    if ($current -ne $recorded) { return "lockfile-changed" }
    return ""
}

# Path of the npm application (npm.cmd / npm.exe), or "" when there is none.
# Not "& npm": PowerShell resolves that to the npm.ps1 shim, which drops the first
# character of its arguments when it is called through "&" (npm 11: `Unknown command: "pm"`).
function Get-NpmApplicationPath {
    $app = Get-Command npm -CommandType Application -ErrorAction SilentlyContinue |
        Where-Object { $_.Extension -in '.cmd', '.exe' } | Select-Object -First 1
    if ($app) { return $app.Source }
    return ""
}

# Runs `npm ci` and records the lockfile hash only when it succeeded and Vite is present.
# Returns $true on success. On failure prints why and returns $false; nothing is recorded.
function Install-FrontendDependencies {
    param([string]$FrontendDir)
    $modules = Join-Path $FrontendDir "node_modules"
    $marker  = Join-Path $modules ".asclexis-lockfile.sha256"
    # The old record goes first: a failed or interrupted install must never look current.
    Remove-Item -LiteralPath $marker -Force -ErrorAction SilentlyContinue
    $npmCommand = Get-NpmApplicationPath
    $npmExit = 1
    $npmOutput = "npm was not found on PATH."
    if ($npmCommand -ne "") {
        Push-Location -LiteralPath $FrontendDir
        try {
            $npmOutput = & $npmCommand ci 2>&1
            $npmExit = $LASTEXITCODE
        } catch {
            $npmOutput = $_.Exception.Message
            $npmExit = 1
        }
        Pop-Location
    }
    if ($npmExit -ne 0) {
        Write-Err "npm ci failed (exit code $npmExit). Frontend dependencies are not installed."
        $npmOutput | Select-Object -Last 15 | ForEach-Object { Write-Host "      $_" }
        Write-Err "Check your internet connection, close other Asclexis windows, and run again."
        return $false
    }
    if (-not (Test-Path -LiteralPath (Join-Path $modules ".bin\vite.cmd")) -or
        -not (Test-Path -LiteralPath (Join-Path $modules "vite\bin\vite.js"))) {
        Write-Err "npm install succeeded but Vite was not found."
        Write-Err "Try deleting src\frontend\node_modules and running again."
        return $false
    }
    try {
        $hash = (Get-FileHash -LiteralPath (Join-Path $FrontendDir "package-lock.json") -Algorithm SHA256).Hash
        Set-Content -LiteralPath $marker -Value $hash -Encoding ASCII -ErrorAction Stop
    } catch {
        # The tree itself is correct, so the app may start; only the record is missing.
        Write-Warn "Could not record the installed version; the next start will reinstall frontend dependencies."
    }
    return $true
}

$installReason = Get-FrontendInstallReason -FrontendDir $FRONTEND_DIR
if ($installReason -ne "") {
    switch ($installReason) {
        "missing"          { Write-Status "Installing frontend dependencies (first-time setup) ..." }
        "incomplete"       { Write-Warn "node_modules exists but looks incomplete. Reinstalling ..." }
        "lockfile-changed" { Write-Status "Frontend dependencies changed since the last install. Reinstalling ..." }
    }
    if (-not (Install-FrontendDependencies -FrontendDir $FRONTEND_DIR)) {
        Read-Host "  Press Enter to exit"
        exit 1
    }
    Write-Ok "Frontend dependencies installed"
} else {
    Write-Ok "Frontend dependencies already installed"
}
```

The `Remove-Item $nodeModulesDir` of the incomplete case goes: `npm ci` removes `node_modules` itself. The implementer may adjust details the red/green run proves necessary (for example the comparison being case-insensitive, or how PowerShell 5.1 returns a single-line `Get-Content`), and reports each deviation. The behaviour in the tables is fixed.

## Tasks

### Task 0: Preconditions (STOP on any failure)

- [ ] `git -C ../hc-devps1 rev-parse --abbrev-ref HEAD` → `fix/dev-ps1-install`; `git merge-base --is-ancestor 777adf5 HEAD; echo $?` → `0`.
- [ ] `grep -n 'DEV-PS1-FIRST' docs/capstone-report/owner-decisions-2026-09-27.md` → one row, signed.
- [ ] `grep -rn "dev.ps1" src/backend/tests scripts tests .github 2>/dev/null` → the two hits named under Files, nothing else.
- [ ] `grep -n 'viteBin\|viteScript\|nodeModulesDir' dev.ps1` → outside STEP 5 only `$viteScript` at `:731` and `:843` (measured 2026-10-08). Anything else: STOP.

### Task 1: Check script first (RED)

**Files:** create `scripts/check_dev_ps1_install.ps1`.

- [ ] **Step 1.** Write the script. It takes no dependency and never runs `dev.ps1`:
  - Loads `Get-FrontendInstallReason`, `Get-NpmApplicationPath` and `Install-FrontendDependencies` from `dev.ps1` with `[System.Management.Automation.Language.Parser]::ParseFile`, finds each `FunctionDefinitionAst` by name and defines it in the script scope. A function that is not found is a **failed check with its own message**, not a crash and not a skip.
  - Builds each case in a fresh directory under `[System.IO.Path]::GetTempPath()` and removes it afterwards. It never touches the repository's `src/frontend`.
  - Decision cases (no npm involved):

    | # | Tree | Expected reason |
    |---|---|---|
    | 1 | no `node_modules` | `missing` |
    | 2 | `node_modules` without `.bin\vite.cmd` | `incomplete` |
    | 3 | Vite files present, marker missing | `lockfile-changed` |
    | 4 | Vite files present, marker = hash of the lockfile | `` (skip) |
    | 5 | case 4, then one byte appended to `package-lock.json` | `lockfile-changed` |
    | 6 | case 4, then the lockfile's mtime set one day back and one day forward, content unchanged | `` (skip) both times |
    | 7 | Vite files and marker present, `package-lock.json` deleted | `lockfile-changed` |

  - Install cases. `npm` is replaced by a stub file named **`npm.cmd`** in a temp folder that the check script puts first on `$env:PATH` for the duration of the case (restored in `finally`). `Install-FrontendDependencies` is called exactly as the launcher calls it, with `-FrontendDir` only, so the case covers the lookup the launcher really uses: no network and no real install, but a real child process and a real `$LASTEXITCODE`. Two earlier versions hid a defect here: a PowerShell function stub hid the `& npm` shim defect, and a stub passed through a test-only `-NpmCommand` parameter left the real lookup uncovered (code review 2026-10-08: reverting the lookup to `"npm"` stayed 14/14). `dev.ps1` has no test-only parameter.

    | # | Stub `npm.cmd` first on PATH | Expected |
    |---|---|---|
    | 8 | exit code 1; Vite files and a marker equal to the lockfile hash already present | returns `$false`; marker **gone** (the old record must not survive a failed install) |
    | 9 | exit code 0, creates the Vite files | returns `$true`; marker equals the lockfile hash; `Get-FrontendInstallReason` then returns `` |
    | 10 | exit code 0, creates nothing | returns `$false`; no marker |
    | 11 | no stub; `$env:PATH` reduced to `%SystemRoot%\System32` (no npm anywhere); Vite files present; `cmd /c exit 0` run first so a stale exit code 0 would show | returns `$false`; no marker |
    | 12 | stub records its arguments | the stub received exactly `ci` |
    | 13 | exit code 0, creates the Vite files, and writes a line to stderr | returns `$true`; marker written (npm warns on stderr on healthy installs) |
    | 14 | stub `npm.cmd` on PATH, and an extensionless file `npm` plus an `npm.ps1` in a folder **before** it | `Get-NpmApplicationPath` returns the stub `npm.cmd`, and the stub received `ci` |
    | 15 | exit code 0, creates the Vite files; the folder is named `Asclexis [1] test` (space and brackets) | returns `$true`; `Get-FrontendInstallReason` then returns `` |

  - Decision edge case:

    | # | Tree | Expected |
    |---|---|---|
    | 16 | Vite files present, marker is an empty file | `lockfile-changed`, and nothing is written to the error stream |

  - npm resolution cases (the real npm, no network, no install):

    | # | Check | Expected |
    |---|---|---|
    | 17 | `Get-NpmApplicationPath` with the unmodified PATH | a path that exists, extension `.cmd` or `.exe` |
    | 18 | `& (Get-NpmApplicationPath) ci --help` called from the script file | exit code 0 and output containing `npm ci` (through the `npm.ps1` shim this is exit 1, `Unknown command: "pm"`; `--version` would pass either way) |

  - The check script sets `$ErrorActionPreference = "Continue"`, the launcher's own setting (`dev.ps1:19`), so the functions run as they do in production.

  - Prints one `PASS` / `FAIL` line per case and a last line `checks: <passed>/<total>`; exits `0` only when all pass, else `1`.
  - Optional switch `-Live <frontendDir>`: runs the real decision and, when it says so, the real `Install-FrontendDependencies` (real `npm ci`) against that directory, and prints the reason, the result and the marker. This is the manual-acceptance entry point; it starts no server.

- [ ] **Step 2. Run it against the unchanged `dev.ps1`: it must fail.**

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\Users\DangT\Documents\GitHub\hc-devps1\scripts\check_dev_ps1_install.ps1'; echo "check=$?"
```

Expected: `check=1`, with the failures naming the functions not found in `dev.ps1` (first round), or the cases the current `dev.ps1` does not satisfy (later rounds). Paste the output. A pass here means the script cannot fail: fix the script, not the expectation.

- [ ] **Step 3. Commit** `test(dev): check script for dev.ps1 frontend install decision` (pathspec `scripts/check_dev_ps1_install.ps1`).

### Task 2: Change `dev.ps1` STEP 5 (GREEN)

**Files:** modify `dev.ps1` (STEP 5 only).

- [ ] **Step 1.** Replace the Before block with the After block.
- [ ] **Step 2.** Parse check, then the check script:

```bash
powershell.exe -NoProfile -Command "\$e = \$null; [void][System.Management.Automation.Language.Parser]::ParseFile('C:\Users\DangT\Documents\GitHub\hc-devps1\dev.ps1', [ref]\$null, [ref]\$e); \$e.Count"   # expect 0
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\Users\DangT\Documents\GitHub\hc-devps1\scripts\check_dev_ps1_install.ps1'; echo "check=$?"   # expect checks: 18/18, check=0
```

- [ ] **Step 3. Break-it (must go red, then be restored).** In `Get-FrontendInstallReason` change `-ne $recorded` to `-eq $recorded`; run the check script: expect `check=1` with cases 4, 5 and 6 failing. Restore; `git diff --stat` shows only the intended change; run again: `check=0`. Second break-it: in `Install-FrontendDependencies` delete the `if ($npmExit -ne 0) { ... }` block: expect cases 8 and 11 to fail. Restore. Third: change `$npmCommand = Get-NpmApplicationPath` to `$npmCommand = "npm"` (the shim defect): expect case 14 to fail (`shimRan=True`). Cases 9 and 12 stay green under this mutation, because their stub folder holds no `npm.ps1` and PowerShell then resolves `npm` to the stub `npm.cmd`; case 14 is the one built to see it. Restore. Fourth: delete the `Remove-Item -LiteralPath $marker` line: expect case 8 to fail. Restore. Fifth: change the initial `$npmExit = 1` to `0`: expect case 11 to fail. Restore.
- [ ] **Step 4. Scope check.**

```bash
git diff origin/main -- dev.ps1 | grep '^@@'         # exactly one hunk, starting at line 623; then: sed -n '617,620p;/STEP 6/p' dev.ps1 shows STEP 5 above it and STEP 6 below it
LC_ALL=C grep -nP '[^\x00-\x7F]' dev.ps1 scripts/check_dev_ps1_install.ps1; echo "nonascii=$?"   # expect nonascii=1 (none)
git status --short                                   # only dev.ps1 (and nothing under src/)
```

- [ ] **Step 5. Commit** `fix(dev): reinstall frontend dependencies when package-lock.json changed` (pathspec `dev.ps1`).

### Task 3: Manual acceptance on Windows (L1 runs it; real `npm ci`, no server started)

In worktree `hc-devps1`, which has no `src/frontend/node_modules` yet. One heavy step at a time.

- [ ] (a) Fresh tree: `-Live` prints reason `missing`, runs `npm ci`, result `True`, marker = SHA-256 of `package-lock.json`.
- [ ] (b) Again: reason `` (skip), no npm run. Record the elapsed time.
- [ ] (c) Lockfile state changed without editing the tracked file: overwrite the **marker** with a wrong hash (this is exactly what a changed lockfile looks like to the decision; `package-lock.json` stays byte-identical so `git status` stays clean): reason `lockfile-changed`, `npm ci` runs, marker restored to the real hash.
- [ ] (d) Failure path, real npm: run `-Live` with the registry unreachable for that process only (`$env:npm_config_registry='http://127.0.0.1:9'` and `$env:npm_config_offline` unset, `npm_config_cache` pointed at an empty temp folder) after invalidating the marker: result `False`, the error lines print, the marker is absent, and a following `Get-FrontendInstallReason` says `missing`, `incomplete` or `lockfile-changed` (not ``). Then run (a) again to leave a working tree.
- [ ] `git status --short` after all four: no tracked file changed.

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\Users\DangT\Documents\GitHub\hc-devps1\scripts\check_dev_ps1_install.ps1' -Live 'C:\Users\DangT\Documents\GitHub\hc-devps1\src\frontend'; echo "live=$?"
```

**Not tested, by design:** a full `dev.ps1` run (it starts both servers and opens a browser; the script has no dry-run switch); PowerShell 7; a machine with a running dev server holding `node_modules` files open while `npm ci` deletes them (expected: `npm ci` exits non-zero and the script stops with the error above; `dev.ps1` frees the ports only in STEP 7, after STEP 5).

### Task 4: L1 verification and PR

- [ ] `python3 scripts/docs_lint.py` rc 0; `python3 scripts/generate_docs_index.py --check` rc 0.
- [ ] `git diff --name-only origin/main...HEAD` lists only the files in the table.
- [ ] `code-reviewer` + `security-reviewer` (opus).
- [ ] PR `fix(dev): ...`; CI 6/6.

## Stop gates

- Any edit outside STEP 5 of `dev.ps1` or outside the file table.
- The check script passes before `dev.ps1` changes, or a break-it stays green.
- A tracked file changes during manual acceptance.
- A need for a new dependency, a test framework or a network endpoint.

## Rollback

One PR; `git revert <merge sha>` restores the old STEP 5. The marker file left inside `node_modules` is inert (nothing else reads it). After a revert the old behaviour returns: an existing install is not refreshed when the lockfile changes.

## Out of scope (owner items, not changed here)

- DEV-SERVER-RUNTIME: the product frontend is still served by the Vite dev server.
- The backend half has the same shape of gap for `requirements.txt` (UNMEASURED here; not read in this phase).
- CI does not run `scripts/check_dev_ps1_install.ps1` (CI is Linux; the launcher is Windows). Wiring it in touches `ci.yml`, outside this phase's files.
