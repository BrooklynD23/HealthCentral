# NPM-AUDIT — Non-Breaking `npm audit fix` for the Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:verification-before-completion. Every count in this plan is re-measured, not copied. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status:** owner-scheduled 2026-10-04 (gate NPM-AUDIT-SCHED in [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md)). Wave 3, L1-B.
**Source:** owner item NPM-AUDIT ([implementation-program.md](../capstone-report/implementation-program.md), "NPM-AUDIT (security, 2026-10-01)" row: 21 vulnerabilities, 1 critical, 14 high, measured on `8064244`).
**Architectural:** no. No Codex review. `code-reviewer` + `security-reviewer` required.

**Goal:** Apply every `npm audit` fix in `src/frontend` that needs no semver-major upgrade, prove the app still type-checks, lints, builds and tests, and list what is left with the major version it needs.

**Architecture:** Lockfile-first. `npm audit fix` (never `--force`) rewrites `package-lock.json` and may raise a `package.json` range within its current major. Nothing else changes.

**Tech Stack:** npm 11.6.2, Node v22.20.0 (Windows, measured 2026-10-04), Vite 7, vitest 4, Tailwind 3.

**Spec:** the owner gate text below; there is no separate spec.

## Global Constraints

- Owner gate NPM-AUDIT-SCHED (2026-10-04), verbatim: "L1 measures, runs `npm audit fix` without --force, then Windows vitest + E2E. Any breaking major upgrade comes back to you."
- Never `npm audit fix --force`. Never a manual edit of a version in `package.json`. Never `npm install <pkg>@<major>`.
- A vulnerability whose only fix is a semver-major upgrade is **reported, not fixed**.
- Commit `src/frontend/package.json` and `src/frontend/package-lock.json` only (plus this plan and the regenerated docs index in the plan commit).
- All npm commands run from **Windows** (`powershell.exe`). `npm install` / `npm ci` from WSL replaces Windows native binaries and breaks the tree.
- Backend collected count stays **1346** (`CLAUDE.md:30,:35`, `AGENT.md:76`). No backend file changes; if one does, STOP.
- E2E runs in CI (the "E2E Smoke" job); it is not run locally in this phase.

## Baseline (measured by L1, Windows, worktree `hc-npm` at `origin/main` `90c502a`, after `npm ci`)

`npm audit`: **26 vulnerabilities (2 low, 4 moderate, 19 high, 1 critical)**. The 2026-10-01 figure (21) was measured on `8064244`; new advisories since then account for the difference. Per package (`npm audit --json`, `fixAvailable`):

| Severity | Package | Direct | Fix per npm |
|---|---|---|---|
| critical | vitest | yes | non-major |
| high | vite, postcss, react-router-dom | yes | non-major |
| high | @remix-run/router, react-router, brace-expansion, browserslist, fast-glob, flatted, js-yaml, minimatch, nanoid, picomatch, rollup, ws | no | non-major |
| high | **tailwindcss** | yes | **`tailwindcss@4.3.3`, semver-major** |
| high | **braces, chokidar, micromatch** | no | **via `tailwindcss@4.3.3`, semver-major** |
| moderate | @humanfs/node, @vitest/mocker, ajv, baseline-browser-mapping | no | non-major |
| low | @babel/core, postcss-selector-parser | no | non-major |

Prediction: 4 of 26 (tailwindcss, braces, chokidar, micromatch; all high) stay, each needing Tailwind 3 → 4. That is an owner decision, not part of this phase.

**Amendment 1 (L1, 2026-10-04, measured by the Task 1 run).** The prediction was wrong. `npm audit fix` leaves **7 (2 moderate, 5 high)**, all needing a semver-major the gate forbids here:

| Severity | Package | Needs |
|---|---|---|
| high | tailwindcss, braces, chokidar, micromatch, **fast-glob** | `tailwindcss@4.3.3` (major) |
| moderate | **react-router, react-router-dom** (now 6.30.6; GHSA-wrjc-x8rr-h8h6, GHSA-337j-9hxr-rhxg) | `react-router-dom@7.18.4` (major) |

Task 1 Step 3 also printed `major changes: 2`: `es-module-lexer` 1.7.0 → 2.3.2 and `std-env` 3.10.0 → 4.3.0. Each has exactly one consumer in the lockfile before and after, `vitest` (4.0.16 `^1.7.0` / `^3.10.0` → 4.1.11 `^2.0.0` / `^4.0.0-rc.1`), and `vitest` itself moves 4.0.16 → 4.1.11, a minor. These are vitest's own declared internals, not a major upgrade of anything `package.json` names, so they are **reported, not a stop**. The rule in Step 3 is therefore: a major change stops the phase if the package is in `package.json`, or if any consumer of it moved by a major, or if it has a consumer outside the package that pulled it. Task 2's full tsc/lint/build/vitest run on a clean `npm ci` is the evidence the vitest minor is not breaking here; E2E Smoke in CI is the rest.

Frontend baseline at `90c502a` (L1, Windows, 2026-10-04): vitest **32 files, 186 tests passed**.

## Files (the complete list)

| File | Change |
|---|---|
| `src/frontend/package-lock.json` | Rewritten by `npm audit fix`. |
| `src/frontend/package.json` | Only if `npm audit fix` itself raises a range; every changed range keeps its major. |
| `docs/plans/2026-10-04-NPM-audit-fix.md` | This plan. |
| `docs/INDEX.md`, `docs/_link_graph.json` | Regenerated for the new plan. |

## Review Focus

1. **A hidden major bump.** `npm audit fix` without `--force` should not cross a major, but a caret range can move a transitive dependency's major. Task 1 Step 3 diffs every `package.json` range and every top-level direct version in the lockfile against its old major.
2. **Linux CI binaries dropped from the lockfile.** The lockfile is regenerated on Windows; CI runs Linux. Task 1 Step 4 checks the Linux optional natives (`@rollup/rollup-linux-x64-gnu`, `@esbuild/linux-x64`) are still recorded.
3. **Tooling behaviour change inside a minor.** vite/vitest/rollup minors can change test or build behaviour. Task 2 runs tsc, lint, build and the full vitest suite; E2E Smoke runs in CI.
4. **The count that does not go down.** If the after-count is not 7 (the major-only set, Amendment 1), the plan's model is wrong: report the difference package by package.
5. **`npm ci` from the committed lockfile.** A lockfile that only works with the `node_modules` it was produced in is useless. Task 2 Step 1 deletes `node_modules` and runs `npm ci` before the checks.

---

### Task 0: Preconditions (STOP on any failure)

**Files:** none.

- [ ] **Step 1: Ancestry, plan, gate, worktree**

Start directory: the canonical repo root.

```bash
set -o pipefail
git fetch origin
git merge-base --is-ancestor 90c502a origin/main && echo "base on main"
git worktree add ../hc-npm -b fix/npm-audit origin/main     # skip if it exists at origin/main
git -C ../hc-npm ls-files docs/plans/2026-10-04-NPM-audit-fix.md   # non-empty once the plan commit exists
grep -n 'NPM-AUDIT-SCHED' /mnt/c/Users/DangT/Documents/GitHub/hc-l0-docs/docs/capstone-report/owner-decisions-2026-09-27.md
```

- [ ] **Step 2: Baseline audit (already measured above; re-run if `origin/main` moved)**

```bash
powershell.exe -NoProfile -Command "cd C:\Users\DangT\Documents\GitHub\hc-npm\src\frontend; npm ci; npm audit 2>&1 | Select-Object -Last 8"
```

Expected last line: `26 vulnerabilities (2 low, 4 moderate, 19 high, 1 critical)`. A different figure: record it and continue (advisories change daily), but the after-count expectation changes with it.

### Task 1: `npm audit fix` and its guards

**Files:**
- Modify: `src/frontend/package-lock.json`, possibly `src/frontend/package.json`

- [ ] **Step 1: Save the old manifest for comparison**

```bash
cd /mnt/c/Users/DangT/Documents/GitHub/hc-npm
git show HEAD:src/frontend/package.json > /tmp/claude-1000/npm-pkg-before.json
git show HEAD:src/frontend/package-lock.json > /tmp/claude-1000/npm-lock-before.json
```

- [ ] **Step 2: Run the fix (no `--force`)**

```bash
powershell.exe -NoProfile -Command "cd C:\Users\DangT\Documents\GitHub\hc-npm\src\frontend; npm audit fix 2>&1 | Select-Object -Last 15; npm audit 2>&1 | Select-Object -Last 40"
```

Paste both outputs. Expected (Amendment 1): `7 vulnerabilities (2 moderate, 5 high)` remain, all needing a major (tailwindcss chain, react-router-dom), with "fix available via `npm audit fix --force`" and "Will install tailwindcss@4.x, which is a breaking change".

- [ ] **Step 3: No major crossed**

```bash
cd /mnt/c/Users/DangT/Documents/GitHub/hc-npm
python3 - <<'EOF'
import json, re
def major(v):
    m = re.search(r'(\d+)', v or '')
    return m.group(1) if m else None
old = json.load(open('/tmp/claude-1000/npm-pkg-before.json'))
new = json.load(open('src/frontend/package.json'))
lo = json.load(open('/tmp/claude-1000/npm-lock-before.json'))['packages']
ln = json.load(open('src/frontend/package-lock.json'))['packages']
bad = 0
for sec in ('dependencies', 'devDependencies'):
    for k, v in new.get(sec, {}).items():
        ov = old.get(sec, {}).get(k)
        if ov != v:
            print(f'package.json {k}: {ov} -> {v}')
            if major(ov) != major(v): bad += 1; print('  MAJOR CHANGE')
for path, meta in ln.items():
    if not path.startswith('node_modules/') or path.count('node_modules/') != 1: continue
    o = lo.get(path, {}).get('version'); n = meta.get('version')
    if o and n and o != n:
        flag = '  MAJOR' if major(o) != major(n) else ''
        print(f'{path[13:]}: {o} -> {n}{flag}')
        if flag: bad += 1
print('major changes:', bad)
EOF
```

Expected: `major changes: 0`, or only majors that pass Amendment 1's rule (sole consumer is a package that moved by minor/patch). Any other major change: STOP and report it (owner gate: "Any breaking major upgrade comes back to you").

- [ ] **Step 4: Linux natives still in the lockfile**

```bash
grep -c '"node_modules/@rollup/rollup-linux-x64-gnu"\|"node_modules/@esbuild/linux-x64"' src/frontend/package-lock.json   # expect 2
git diff --stat -- src/frontend/
git status --short                                                                          # only package.json / package-lock.json
```

### Task 2: Verify from a clean install, then commit

**Files:** none new.

- [ ] **Step 1: Clean install from the new lockfile and run every frontend check**

```bash
powershell.exe -NoProfile -Command "cd C:\Users\DangT\Documents\GitHub\hc-npm\src\frontend; Remove-Item -Recurse -Force node_modules; npm ci 2>&1 | Select-Object -Last 4; npx tsc --noEmit; echo tsc=\$LASTEXITCODE; npm run lint; echo lint=\$LASTEXITCODE; npm run build 2>&1 | Select-Object -Last 6; echo build=\$LASTEXITCODE; npx vitest run 2>&1 | Select-Object -Last 8"
```

Expected: `npm ci` succeeds; `tsc=0`, `lint=0`, `build=0`; vitest **32 files, 186 tests passed** (no test changes in this phase). Any failure: STOP and report the error text; do not change source or tests to fit a new tool version.

- [ ] **Step 2: Commit**

```bash
cd /mnt/c/Users/DangT/Documents/GitHub/hc-npm
git add src/frontend/package-lock.json src/frontend/package.json
git commit -m "fix(deps): apply non-breaking npm audit fixes in frontend" -m "<before/after counts and the remaining major-only list>" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- src/frontend/package-lock.json src/frontend/package.json
```

### Task 3: L1 verification and PR

- [ ] Re-run Task 1 Step 3 and Task 2 Step 1 output in the PR body; `git diff --name-only origin/main...HEAD` lists only the files in the table; docs gates `python3 scripts/docs_lint.py && python3 scripts/generate_docs_index.py --check`.
- [ ] `code-reviewer` + `security-reviewer` (opus) on the diff (lockfile: resolved URLs on `registry.npmjs.org`, `integrity` present on every changed entry).
- [ ] PR body: before/after audit counts, every package left with the major it needs, CI E2E Smoke result.

## Stop gates

- Any `--force`, any major change (Task 1 Step 3), any file outside the table.
- tsc, lint, build or vitest fails after the fix.
- A remaining vulnerability whose fix npm reports as non-major (then `npm audit fix` did not do what the plan assumes; report).

## Rollback

One PR; `git revert <merge sha>` restores the old lockfile. Then `npm ci`.

## Out of scope (owner decision)

- Tailwind 3 → 4 (`tailwindcss@4.3.3`): clears tailwindcss, braces, chokidar, micromatch (4 high). Tailwind 4 changes config format (`tailwind.config.js` → CSS `@theme`) and the PostCSS plugin; a migration phase of its own.

## Amendment 2 (NPM-AUDIT-2) — L1-B, 2026-10-08

A second run of this plan, as phase NPM-AUDIT-2 (owner item NPM-AUDIT-DRIFT). Tasks 0-3 above are reused; where this section and the text above disagree, this section wins for NPM-AUDIT-2. The record of the first run (PR #38) above is unchanged.

**Gates (verbatim, [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md)):**

- NPM-MAJORS-RUN (2026-10-07): "NPM-AUDIT-2, then React Router 7, then Tailwind 4, each as its own PR."
- FE-SEQ (2026-10-07): "NPM-AUDIT-2 runs from the existing plan plus Amendment 2; … any other transitive major bump (dev/test-only or not) comes back to you before it lands."
- MAJORS-TIED (2026-10-07): pre-approves only packages tied to an **approved major**. NPM-AUDIT-2 has no approved major, so it pre-approves nothing here.

**Base and names.** `origin/main` = `777adf5`; dependency PR #38 (`c4d407e`) is an ancestor (`git merge-base --is-ancestor c4d407e origin/main` → 0). Worktree `../hc-npm-audit-2`, branch `fix/npm-audit-2`. Do not reuse `../hc-npm`.

**Baseline (L1-B measured, Windows, node v22.20.0, npm 11.6.2, `777adf5`, after a clean `npm ci`, 2026-10-08).** vitest: **34 files, 195 tests passed**, exit code 0. Backend collected count stays **1370**; no backend file changes. `npm audit`: **10 (4 moderate, 6 high)**, exit code 1. Per package, from `npm audit --json` (`fixAvailable`):

| Severity | Package | Direct | Fix per npm |
|---|---|---|---|
| high | fast-glob | no | **non-major** (`fixAvailable: true`) |
| high | source-map-js | no | **non-major** (`fixAvailable: true`; GHSA-68fv-2mgg-jv7q) |
| moderate | postcss-nested | no | **non-major** (`fixAvailable: true`) |
| high | tailwindcss | yes | `tailwindcss@4.3.3`, semver-major |
| high | braces, chokidar, micromatch | no | via `tailwindcss@4.3.3`, semver-major |
| moderate | postcss-selector-parser | no | via `tailwindcss@4.3.3`, semver-major |
| moderate | react-router-dom | yes | `react-router-dom@7.18.4`, semver-major |
| moderate | react-router | no | via `react-router-dom@7.18.4`, semver-major |

**Scope.** The three rows npm marks non-major on the day of the run. This table is a dated measurement, not a target: advisories move daily on a byte-identical lockfile (7 → 10 between 2026-10-04 and 2026-10-06). The implementer re-reads `npm audit --json` before the fix and reports before/after **per package and severity**, not as a total. `fast-glob` and `postcss-nested` are flagged through their dependency chain (`micromatch`, `postcss-selector-parser`), so npm may report them fixable and still leave them listed; that is reported, not forced.

**Rules that replace the ones above for this run.**

1. `npm audit fix` without `--force`, from Windows. `src/frontend/package.json` must not change at all (no manual edit, `engines` included). Only `src/frontend/package-lock.json` changes. If `package.json` changes, STOP.
2. **Majors (replaces Amendment 1's rule and Task 1 Step 3).** Any package whose major version changes, in either direction, at any nesting depth, STOPS the phase and goes back to the owner with the list. A `0.x` minor change counts as a major. So does a package added at a path with a major that name did not have before. Amendment 1's "sole consumer moved by a minor" exception does **not** apply.
3. **Exit codes.** After each of `npx tsc --noEmit`, `npm run lint`, `npm run build`, `npx vitest run`, print the numeric exit code and record it. Inside a bash double-quoted string write `\$LASTEXITCODE`; an unescaped `$LASTEXITCODE` is expanded to empty by bash and the check cannot fail. A non-zero code stops the phase.
4. **Lockfile diff (the measurement for rule 2).** Python 3 (`python3` in WSL), every key of `packages`, nested paths included:

```bash
git show origin/main:src/frontend/package-lock.json > "$TMP/lock-main.json"
python3 "$TMP/lockdiff.py" "$TMP/lock-main.json" src/frontend/package-lock.json; echo "lockdiff=$?"
```

`lockdiff.py` (kept outside the repo; this is its whole logic):

```python
import json, sys
def parts(v): return (v or "").split("-")[0].split("+")[0].split(".")
def flag(o, n):
    o, n = parts(o), parts(n)
    if o[0] != n[0]: return "MAJOR"
    if o[0] == "0" and o[1:2] != n[1:2]: return "BREAKING-0.x"
    return ""
old = json.load(open(sys.argv[1], encoding="utf-8"))["packages"]; old.pop("", None)
new = json.load(open(sys.argv[2], encoding="utf-8"))["packages"]; new.pop("", None)
name = lambda k: k.rsplit("node_modules/", 1)[-1]
added, removed = sorted(set(new) - set(old)), sorted(set(old) - set(new))
changed = sorted(k for k in set(old) & set(new) if old[k].get("version") != new[k].get("version"))
stops = 0
print(f"ADDED ({len(added)})");   [print(" ", k, new[k].get("version")) for k in added]
print(f"REMOVED ({len(removed)})"); [print(" ", k, old[k].get("version")) for k in removed]
print(f"VERSION-CHANGED ({len(changed)})")
for k in changed:
    f = flag(old[k].get("version"), new[k].get("version")); stops += bool(f)
    print(" ", k, old[k].get("version"), "->", new[k].get("version"), f)
majors = {}
for k, v in old.items(): majors.setdefault(name(k), set()).add(parts(v.get("version"))[0])
for k in added:  # a name arriving at a new path with a major it did not have
    had = majors.get(name(k))
    if had is None: print("  NEW-NAME", k, new[k].get("version"))
    elif parts(new[k].get("version"))[0] not in had: stops += 1; print("  MAJOR", k, new[k].get("version"), sorted(had))
scripts = lambda p: {k for k, v in p.items() if v.get("hasInstallScript")}
print("hasInstallScript GAINED:", sorted(scripts(new) - scripts(old)))
for k in added + changed:  # source shape: npm registry + sha512 only
    v = new[k]
    if not (v.get("resolved") or "").startswith("https://registry.npmjs.org/") or not (v.get("integrity") or "").startswith("sha512-"):
        stops += 1; print("  BAD-SOURCE", k, v.get("resolved"), v.get("integrity"))
print("STOP-FLAGS:", stops); sys.exit(1 if stops else 0)
```

Expected: `STOP-FLAGS: 0`, `lockdiff=0`, `hasInstallScript GAINED: []` (baseline holders: `esbuild`, `fsevents`, `playwright/node_modules/fsevents`). Self-check run on 2026-10-08: `origin/main` against itself prints 0 added, 0 removed, 0 changed over 485 keys. A `NEW-NAME` line is a package the tree did not have under any version: it is listed in the PR body and is a security-review item. The full output goes in the PR body.

5. **Acceptance (L1 runs it, Windows).**

```bash
powershell.exe -NoProfile -Command "cd C:\Users\DangT\Documents\GitHub\hc-npm-audit-2\src\frontend; Remove-Item -Recurse -Force node_modules; npm ci 2>&1 | Select-Object -Last 4; echo npmci=\$LASTEXITCODE; npx tsc --noEmit; echo tsc=\$LASTEXITCODE; npm run lint; echo lint=\$LASTEXITCODE; npm run build 2>&1 | Select-Object -Last 6; echo build=\$LASTEXITCODE; npx vitest run 2>&1 | Select-Object -Last 8; echo vitest=\$LASTEXITCODE"
```

Expected: `npmci=0 tsc=0 lint=0 build=0 vitest=0`, vitest 34 files / 195 tests. `git diff --name-only origin/main...HEAD` lists only `src/frontend/package-lock.json`, this plan, `docs/INDEX.md`, `docs/_link_graph.json` and the wave report. E2E evidence is CI's "E2E Smoke Tests" job on the PR; Playwright is not run locally (no SQLCipher wheel on Windows).

6. **No break-it.** The change is lockfile-only and adds no test, so there is no assertion to invert. The evidence that the fix did something is the per-package audit list before and after.

**Not in this phase.** `engines.node` (`>=22` against vite's `>=22.12.0`): a `package.json` edit, so it is reported, not made. Existing installs do not pick this lockfile up until DEV-PS1-INSTALL lands (owner row DEV-PS1-FIRST; its own plan and PR). Rollback is unchanged: `git revert`, then reinstall.
