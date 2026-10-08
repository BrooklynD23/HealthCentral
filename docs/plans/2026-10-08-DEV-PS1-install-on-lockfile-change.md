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
| `npm ci` or `npm install`? | `npm ci`, for all three cases (first time, incomplete, lockfile changed) | `npm ci` installs exactly the committed lockfile and never rewrites it. `npm install` may rewrite `package-lock.json` on a patient machine, which would then differ from the repository and from the stored hash. `npm ci` removes `node_modules` first, so a failed run leaves no half-installed tree: the next run sees no `node_modules` and installs again. CI already runs `npm ci` on every PR (`ci.yml` frontend jobs), so the lockfile is known to be in sync with `package.json`. |
| Install failure | Check npm's exit code, print the last lines of npm's output, stop with exit 1. The marker is written only after exit code 0 **and** Vite is present | Today the exit code is ignored and only Vite's presence is checked. With a reinstall over an existing tree that check would pass on the old Vite. |
| `package-lock.json` missing | The decision returns "install"; `npm ci` then fails with its own message and the script stops | An incomplete download. No guess is made. |

Cost accepted: `npm ci` needs the registry (or npm's cache). A machine that is offline on the first run after a lockfile change gets a clear error and does not launch; before this change it launched on the stale packages. That is the behaviour the gate asks for.

## Files (the complete list)

| File | Change |
|---|---|
| `dev.ps1` | STEP 5 only: two functions plus the rewritten install block |
| `scripts/check_dev_ps1_install.ps1` | New. Self-contained check script (no Pester). Loads the two functions out of `dev.ps1` with the PowerShell parser, so it tests the shipped code without running the launcher |
| `docs/plans/2026-10-08-DEV-PS1-install-on-lockfile-change.md` | This plan |
| `docs/INDEX.md`, `docs/_link_graph.json` | Regenerated for the new plan |
| `audit/2026-09-25/waves/wave-4-L1-B.md` | L1 wave report |

Prior art checked: `grep -rn "dev.ps1" src/backend/tests scripts tests .github` returns nothing at `777adf5`. No existing test pattern for the launcher, so the check script is new.

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
    if (-not (Test-Path $modules)) { return "missing" }
    if (-not (Test-Path (Join-Path $modules ".bin\vite.cmd")) -or
        -not (Test-Path (Join-Path $modules "vite\bin\vite.js"))) { return "incomplete" }
    $lockFile = Join-Path $FrontendDir "package-lock.json"
    $marker   = Join-Path $modules ".asclexis-lockfile.sha256"
    if (-not (Test-Path $lockFile) -or -not (Test-Path $marker)) { return "lockfile-changed" }
    $current  = (Get-FileHash -Path $lockFile -Algorithm SHA256).Hash
    $recorded = ([string](Get-Content -Path $marker -TotalCount 1)).Trim()
    if ($current -ne $recorded) { return "lockfile-changed" }
    return ""
}

# Runs `npm ci` and records the lockfile hash only when it succeeded and Vite is present.
# Returns $true on success. On failure prints why and returns $false; nothing is recorded.
function Install-FrontendDependencies {
    param([string]$FrontendDir)
    $modules = Join-Path $FrontendDir "node_modules"
    Push-Location $FrontendDir
    $npmOutput = & npm ci 2>&1
    $npmExit = $LASTEXITCODE
    Pop-Location
    if ($npmExit -ne 0) {
        Write-Err "npm ci failed (exit code $npmExit). Frontend dependencies are not installed."
        $npmOutput | Select-Object -Last 15 | ForEach-Object { Write-Host "      $_" }
        Write-Err "Check your internet connection, close other Asclexis windows, and run again."
        return $false
    }
    if (-not (Test-Path (Join-Path $modules ".bin\vite.cmd")) -or
        -not (Test-Path (Join-Path $modules "vite\bin\vite.js"))) {
        Write-Err "npm install succeeded but Vite was not found."
        Write-Err "Try deleting src\frontend\node_modules and running again."
        return $false
    }
    $hash = (Get-FileHash -Path (Join-Path $FrontendDir "package-lock.json") -Algorithm SHA256).Hash
    Set-Content -Path (Join-Path $modules ".asclexis-lockfile.sha256") -Value $hash -Encoding ASCII
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
- [ ] `grep -rn "dev.ps1" src/backend/tests scripts tests .github 2>/dev/null` → empty (no prior test pattern).
- [ ] `grep -n 'viteBin\|viteScript\|nodeModulesDir' dev.ps1` → outside STEP 5 only `$viteScript` at `:731` and `:843` (measured 2026-10-08). Anything else: STOP.

### Task 1: Check script first (RED)

**Files:** create `scripts/check_dev_ps1_install.ps1`.

- [ ] **Step 1.** Write the script. It takes no dependency and never runs `dev.ps1`:
  - Loads `Get-FrontendInstallReason` and `Install-FrontendDependencies` from `dev.ps1` with `[System.Management.Automation.Language.Parser]::ParseFile`, finds each `FunctionDefinitionAst` by name and defines it in the script scope. A function that is not found is a **failed check with its own message**, not a crash and not a skip.
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

  - Install cases, with `npm` replaced by a stub function defined in the check script (so no network and no real install):

    | # | Stub `npm ci` | Expected |
    |---|---|---|
    | 8 | exit code 1, Vite files already present from an old tree | returns `$false`; marker **not** written (the case today's code gets wrong) |
    | 9 | exit code 0, creates the Vite files | returns `$true`; marker equals the lockfile hash; `Get-FrontendInstallReason` then returns `` |
    | 10 | exit code 0, creates nothing | returns `$false`; marker not written |

  - Prints one `PASS` / `FAIL` line per case and a last line `checks: <passed>/<total>`; exits `0` only when all pass, else `1`.
  - Optional switch `-Live <frontendDir>`: runs the real decision and, when it says so, the real `Install-FrontendDependencies` (real `npm ci`) against that directory, and prints the reason, the result and the marker. This is the manual-acceptance entry point; it starts no server.

- [ ] **Step 2. Run it against the unchanged `dev.ps1`: it must fail.**

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\Users\DangT\Documents\GitHub\hc-devps1\scripts\check_dev_ps1_install.ps1'; echo "check=$?"
```

Expected: `check=1`, with the failures naming the two functions as not found in `dev.ps1`. Paste the output. A pass here means the script cannot fail: fix the script, not the expectation.

- [ ] **Step 3. Commit** `test(dev): check script for dev.ps1 frontend install decision` (pathspec `scripts/check_dev_ps1_install.ps1`).

### Task 2: Change `dev.ps1` STEP 5 (GREEN)

**Files:** modify `dev.ps1` (STEP 5 only).

- [ ] **Step 1.** Replace the Before block with the After block.
- [ ] **Step 2.** Parse check, then the check script:

```bash
powershell.exe -NoProfile -Command "\$e = \$null; [void][System.Management.Automation.Language.Parser]::ParseFile('C:\Users\DangT\Documents\GitHub\hc-devps1\dev.ps1', [ref]\$null, [ref]\$e); \$e.Count"   # expect 0
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\Users\DangT\Documents\GitHub\hc-devps1\scripts\check_dev_ps1_install.ps1'; echo "check=$?"   # expect checks: 10/10, check=0
```

- [ ] **Step 3. Break-it (must go red, then be restored).** In `Get-FrontendInstallReason` change `-ne $recorded` to `-eq $recorded`; run the check script: expect `check=1` with cases 4, 5 and 6 failing. Restore; `git diff --stat` shows only the intended change; run again: `check=0`. Second break-it: in `Install-FrontendDependencies` delete the `if ($npmExit -ne 0) { ... }` block: expect case 8 to fail. Restore.
- [ ] **Step 4. Scope check.**

```bash
git diff origin/main -- dev.ps1 | grep '^@@'         # every hunk inside STEP 5 (lines 617-700)
LC_ALL=C grep -nP '[^\x00-\x7F]' dev.ps1 scripts/check_dev_ps1_install.ps1; echo "nonascii=$?"   # expect nonascii=1 (none)
git status --short                                   # only dev.ps1 (and nothing under src/)
```

- [ ] **Step 5. Commit** `fix(dev): reinstall frontend dependencies when package-lock.json changed` (pathspec `dev.ps1`).

### Task 3: Manual acceptance on Windows (L1 runs it; real `npm ci`, no server started)

In worktree `hc-devps1`, which has no `src/frontend/node_modules` yet. One heavy step at a time.

- [ ] (a) Fresh tree: `-Live` prints reason `missing`, runs `npm ci`, result `True`, marker = SHA-256 of `package-lock.json`.
- [ ] (b) Again: reason `` (skip), no npm run. Record the elapsed time.
- [ ] (c) Lockfile state changed without editing the tracked file: overwrite the **marker** with a wrong hash (this is exactly what a changed lockfile looks like to the decision; `package-lock.json` stays byte-identical so `git status` stays clean): reason `lockfile-changed`, `npm ci` runs, marker restored to the real hash.
- [ ] (d) Failure path, real npm: run `-Live` with the registry unreachable for that process only (`$env:npm_config_registry='http://127.0.0.1:9'` and `$env:npm_config_offline` unset, `npm_config_cache` pointed at an empty temp folder) after invalidating the marker: result `False`, the error lines print, the marker is absent, and a following `Get-FrontendInstallReason` says `missing` or `lockfile-changed` (not ``). Then run (a) again to leave a working tree.
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
