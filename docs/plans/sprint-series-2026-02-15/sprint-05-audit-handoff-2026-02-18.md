# Sprint 05 Audit Findings and Agent Handoff

**Date:** 2026-02-18  
**Branch Audited:** `sprint/05-frontend-quality-testing`  
**Primary Commit Reviewed:** `661b1e5`  
**Purpose:** Preserve audit context and hand off implementation planning to the next agent.

## Audit Scope

- Sprint 05 closeout changes (PWA scaffold, accessibility tests, chart additions, test regressions fix-up).
- Documentation drift review for Sprint 05 planning/backlog docs.
- Security-focused review of changed frontend surfaces.
- CI-equivalent local checks where environment allowed.

## Confirmed Findings

### FND-001 (Medium) - E2E contrast audit may validate the wrong page

- **Location:** `src/frontend/e2e/contrast-audit.spec.ts:22`, `src/frontend/e2e/contrast-audit.spec.ts:31`
- **Related auth gate:** `src/frontend/src/components/auth/ProtectedRoute.tsx:15`
- **Issue:** The contrast test navigates to protected routes but does not establish authenticated state first.
- **Risk:** False-positive accessibility signal. Test can pass while auditing redirect/setup route instead of target route.
- **Fix direction:** Add deterministic auth bootstrap in test setup and assert route before running `AxeBuilder`.

### FND-002 (Low) - File inventory counts are inconsistent in Sprint 05 closeout doc

- **Location:** `docs/plans/sprint-05-closeout-plan.md:367`, `docs/plans/sprint-05-closeout-plan.md:381`
- **Issue:** “New Files (8)” lists 10 rows; “Modified Files (5)” lists 7 rows.
- **Risk:** Planning/reporting drift.
- **Fix direction:** Correct headings/counts to match listed rows.

### FND-003 (Low) - Flaky-test remediation narrative differs from final implementation

- **Planned text:** `docs/plans/sprint-05-closeout-plan.md:20`, `docs/plans/sprint-05-closeout-plan.md:21`
- **Implemented test timeout:** `src/frontend/src/__tests__/ResponsiveLayout.test.tsx:264`, `src/frontend/src/__tests__/ResponsiveLayout.test.tsx:271`
- **Issue:** Plan states `30000` + `vi.setConfig`; code uses `120000` and no `vi.setConfig`.
- **Risk:** Future agents may optimize toward outdated assumptions.
- **Fix direction:** Update plan text to actual fix or reduce test timeout with measured evidence.

### FND-004 (Low, hardening) - Service worker fetch interception is overly broad

- **Location:** `src/frontend/public/sw.js:12`
- **Issue:** All fetch requests are intercepted without request gating.
- **Risk:** Not directly exploitable now, but increases future risk when caching logic is added.
- **Fix direction:** Guard fetch handler to same-origin `GET` requests and pass through others.

## Security Review Outcome

- No direct exploitable vulnerabilities were identified in Sprint 05 deltas.
- Offline dependency audit returned no frontend advisories in this environment (`npm audit --offline`).

## CI and Verification Status (from this audit run)

- **Passed:**
  - `python3 scripts/docs_lint.py`
  - Frontend `npx tsc --noEmit` in isolated scratch workspace
  - `npm audit --offline` (frontend, including dev deps)
- **Blocked/partial due environment:**
  - Frontend `npm ci` in repo path hit WSL filesystem I/O lock on esbuild Windows binary.
  - Full frontend `vitest run` could not be completed to final summary in this shell environment (partial suites did run earlier).
  - Backend pytest could not run cleanly from Linux Python against Windows venv artifacts (`pydantic_core` binary import mismatch).
  - GitHub Actions status could not be queried here (`gh` CLI unavailable).

## FND Resolution Status (2026-02-19)

All four findings have been implemented on `sprint/05-frontend-quality-testing`:

| Finding | Status | Files Changed |
|---------|--------|---------------|
| FND-001 | **DONE** | `src/frontend/e2e/contrast-audit.spec.ts` — added `setupAuthenticatedUser` + route assertion before AxeBuilder |
| FND-002 | **DONE** | `docs/plans/sprint-05-closeout-plan.md` — corrected "New Files (8)" → (10), "Modified Files (5)" → (7) |
| FND-003 | **DONE** | `docs/plans/sprint-05-closeout-plan.md` — updated narrative to 120000ms `waitFor` + `it()` timeout, removed `vi.setConfig` |
| FND-004 | **DONE** | `src/frontend/public/sw.js` — guarded fetch to same-origin GET only |

### Local Verification Results

| Check | Working Dir | Result |
|-------|-------------|--------|
| `npx tsc --noEmit` | `src/frontend` | **PASS** — 0 errors |
| `npm run lint` | `src/frontend` | **PASS** — 0 warnings |
| `python3 scripts/docs_lint.py` | repo root | **PASS** |
| `npx vitest run` | `src/frontend` | **BLOCKED** — see WSL blocker below |
| `pytest` | `src/backend` | **BLOCKED** — pydantic_core binary mismatch (unchanged from audit) |
| Playwright E2E | `src/frontend` | **BLOCKED** — requires running backend |

### WSL Environment Blocker — Frontend Test Suite

**Problem:** `npx vitest run` (with default `threads` or `forks` pool) stalls indefinitely in WSL2 on this repo. Partial suites execute (e.g., ResponsiveLayout 22/22, VisualizationInteractions 22/22, Accessibility 32/32 observed passing individually) but the full 188-test run never reaches a summary line. Multiple attempts over ~40 hours of wall time confirmed the hang.

**Root cause:** WSL2 filesystem I/O through `/mnt/c/` (Windows NTFS mount) introduces high latency and lock contention for vitest's parallel worker orchestration. The `@esbuild/win32-x64` and `@rollup/rollup-win32-x64-msvc` native binaries also create cross-platform conflicts (`npm install` hits `ENOTEMPTY` rename errors; `rm -rf node_modules` fails on locked `.exe` files).

**Known workarounds (none fully successful locally):**
1. `--pool forks` — reduces contention but still stalls after 2-4 suites
2. `vi.setConfig({ testTimeout })` / increased `START_TIMEOUT` — helps individual tests but doesn't fix worker hang
3. Running from native Windows `cmd.exe` — fails on Linux-platform lock file packages

**Recommended resolution:** Run the full vitest suite in GitHub Actions CI (Linux runner with native filesystem) or on a native Linux/macOS dev machine. The CI workflow at `.github/workflows/ci.yml` already runs `vitest` in the `frontend-tests` job on `ubuntu-latest`.

**Impact on this PR:** The code changes (FND-001 through FND-004) do not modify any vitest-executed files. FND-001 changes a Playwright E2E spec (not run by vitest). FND-004 changes `sw.js` (not imported by any vitest test). FND-002/003 are documentation only. Regression risk from these changes is minimal.

## Next Agent Handoff

### Objective

Produce an implementation plan (not immediate code changes) that resolves FND-001 through FND-004 with minimal regression risk and clear CI validation steps.

### Required Planning Outputs

1. A sequenced implementation plan with task IDs and dependency order.
2. Test strategy updates for each finding.
3. CI execution plan that is runnable in clean environment and in GitHub Actions.
4. Rollback considerations for each code change.

### Suggested Task Breakdown

1. **TASK-A11Y-E2E-001**
   - Add authenticated setup helper for contrast audit spec.
   - Assert expected route before running axe scan.
   - Ensure failures show route mismatch clearly.
2. **TASK-DOC-DRIFT-001**
   - Fix closeout-plan file counts and stale remediation narrative.
   - Confirm consistency with `pm-complete-unimplemented-features-2026-02-15.md`.
3. **TASK-SW-HARDEN-001**
   - Scope service worker fetch interception to safe request classes.
   - Add concise comments documenting intentional pass-through behavior.
4. **TASK-CI-VERIFY-001**
   - Re-run `docs-lint`, frontend typecheck, frontend vitest, backend tests, and Playwright suite in clean CI-capable environment.
   - Capture final pass/fail counts and attach to PR notes.

### Acceptance Criteria for Resolution

- Contrast audit fails if redirected away from intended protected route.
- Sprint 05 closeout plan has accurate counts and consistent remediation narrative.
- Service worker only intercepts explicitly allowed requests.
- CI evidence shows green checks or a documented/environment-reproducible blocker list with remediation.

## Notes for Planner

- Keep changes narrow to Sprint 05 files first.
- Avoid changing unrelated backend behavior while addressing this handoff.
- If timeout reductions are proposed, include baseline timing data and retry/flakiness evidence.
