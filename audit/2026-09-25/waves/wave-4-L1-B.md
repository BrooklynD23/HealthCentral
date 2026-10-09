# Wave 4 — L1-B report (frontend sequence)

**Date:** 2026-10-08. **L1:** L1-B (Opus). **Base:** `origin/main` = `777adf5`.
This dispatch has two phases, each its own worktree, branch and PR. This file is committed on both branches; each copy holds its own phase. Whichever PR merges second takes both sections (and refreshes `docs/INDEX.md`, see Merge order).

Legend: **[L1]** = L1-B ran the command and read the output. **[L2]** = an implementer agent (Sonnet) reported it. **[R]** = a reviewer agent (Opus) reported it.

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

### Merge order

1. NPM-AUDIT-2 has no dependency on DEV-PS1-INSTALL; either can merge first. The files are disjoint except this report and (for DEV-PS1-INSTALL only) `docs/INDEX.md` / `docs/_link_graph.json`.
2. This branch does not change `docs/INDEX.md`. DEV-PS1-INSTALL does (new plan file). If NPM-AUDIT-2 merges second, no index refresh is needed for it; the second PR to merge resolves this report file by keeping both phase sections.
3. React Router 7 and Tailwind 4 branch from `origin/main` after this merges (all three rewrite `package-lock.json`). Tailwind 4 also waits for DEV-PS1-INSTALL (gate DEV-PS1-FIRST).

Rollback: `git revert <merge sha>`, then reinstall (`npm ci` in `src/frontend`).
