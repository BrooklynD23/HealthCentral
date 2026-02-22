# Sprint 06 Agent Handoff Prompt

> Historical Reference: Sprint 06 was fully implemented on `sprint/06-platform-compliance` (2026-02-21). This handoff prompt is retained for history and is not an active tracker.

**Created:** 2026-02-21
**For:** Next Claude Code agent session
**Branch base:** `main` (commit `7f64ea7`)
**Sprint scope:** Platform Operations and Compliance (HC-S06-OPS)
**Status:** Implemented — 6 commits, 39 new files, 68 tests, 4163 lines added

---

## Instructions for the Agent (Historical)

The instructions below were used to bootstrap the Sprint 06 implementation agent session.

---

## Prompt

You are starting Sprint 06 — Platform Operations and Compliance for HealthCentral. Your job is to **plan first, then implement** using Claude plan mode and a git worktree for isolation.

### Step 0: Set Up Git Worktree

Before any planning or code changes, create an isolated worktree:

```bash
cd /mnt/c/Users/DangT/Documents/GitHub/HealthCentral
git worktree add ../HealthCentral-sprint06 -b sprint/06-platform-compliance main
cd ../HealthCentral-sprint06
```

All work for this sprint happens in `../HealthCentral-sprint06`. Do NOT modify the main repo working tree.

### Step 1: Read Context (Do Not Skip)

Read these files to understand project state before planning:

1. `docs/plans/sprint-series-2026-02-15/sprint-06-platform-compliance.md` — Sprint 06 scope (6 work packages: OPS-001 through OPS-006)
2. `docs/plans/pm-complete-unimplemented-features-2026-02-15.md` — PM backlog with priority tiers and remaining work
3. `docs/plans/sprint-series-2026-02-15/README.md` — Sprint series index and architecture guardrails
4. `docs/plans/sprint-series-2026-02-15/sprint-05-audit-handoff-2026-02-18.md` — Previous sprint audit findings and WSL environment blockers
5. `src/backend/main.py` — Existing FastAPI app structure (OPS-003 wires middleware here)
6. `src/backend/core/audit.py` — Existing audit module (OPS-003 extends this)
7. `src/backend/core/config.py` — Existing config/validation (OPS-001 metrics config goes here)
8. `.github/workflows/ci.yml` — Current CI pipeline (OPS-003 adds security scan job)

### Step 2: Enter Plan Mode and Create Structured Plans

Use `/plan` or enter plan mode. Create a detailed implementation plan covering all 6 work packages. The plan must include:

**For each work package (OPS-001 through OPS-006):**
- Task ID and title
- Files to create/modify (exact paths)
- Dependencies on other tasks
- Test file paths and test count targets
- Acceptance criteria
- Rollback strategy

**Execution order (respect these constraints):**
- **OPS-003 (Security Hardening) first** — it impacts all other packages via middleware
- **OPS-001 (Monitoring) second** — metrics instrumentation feeds into OPS-002 validation
- **OPS-002 (Backup/Recovery) third** — depends on monitoring for integrity checks
- **OPS-004/005/006 (Documentation) in parallel** — independent of each other

**Architecture constraints:**
- New backend packages: `src/backend/monitoring/`, `src/backend/security/`
- New doc directories: `docs/api/`, `docs/user/`, `docs/compliance/`
- Existing files to modify: `src/backend/main.py` (middleware), `.github/workflows/ci.yml` (security scan)
- Follow existing patterns: FastAPI routers in `src/backend/api/`, modules in `src/backend/modules/`, config in `src/backend/core/config.py`
- Use TDD: write tests first, implement to pass, target 80%+ coverage
- Keep files under 400 lines; extract utilities when needed

### Step 3: Wait for Plan Approval

Do NOT write any code until the plan is explicitly approved. Present the plan and wait for confirmation.

### Step 4: Implement with TDD

After approval, implement in the planned order. For each work package:
1. Create test file first (RED)
2. Implement minimal code to pass (GREEN)
3. Refactor if needed (IMPROVE)
4. Run `python3 -m pytest <test_file>` to verify
5. Commit with conventional commit format: `feat(S06-OPS-XXX): <description>`

### Step 5: Verify and Report

After all packages are implemented:

```bash
# From the worktree root
cd src/frontend && npx tsc --noEmit && npm run lint && cd ../..
python3 scripts/docs_lint.py
cd src/backend && python3 -m pytest tests/ -v
```

Create a closeout summary documenting:
- Files created/modified with line counts
- Test counts and pass/fail status
- Any environment blockers encountered
- Remaining work or known gaps

### Sprint 06 Work Package Summary

| ID | Package | Priority | New Files | Key Behavior |
|----|---------|----------|-----------|-------------|
| OPS-001 | Performance Monitoring | Medium | `src/backend/monitoring/` | Latency/error/throughput metrics, correlation IDs |
| OPS-002 | Backup & Recovery | Medium | `src/backend/scripts/backup.py`, `docs/compliance/disaster-recovery.md` | Scheduled backups, integrity validation, restore runbook |
| OPS-003 | Security Hardening | **High** | `src/backend/security/` | Audit logging, input validation, rate limiting, CI security scan |
| OPS-004 | API Documentation | Medium | `docs/api/` | Endpoint catalog, request/response examples, integration guide |
| OPS-005 | User Documentation | Low | `docs/user/` | Workflow manuals, troubleshooting, FAQ |
| OPS-006 | Regulatory Compliance | Low | `docs/compliance/` | HIPAA controls mapping, data privacy docs, audit checklist |

### What Already Exists (Do Not Duplicate)

- `src/backend/core/audit.py` — Basic audit logging (19 lines; OPS-003 extends this)
- `src/backend/core/config.py` — Config validation with `validate_startup()` (OPS-001 adds metrics config)
- `src/backend/main.py` — FastAPI app with CORS middleware (OPS-003 adds rate limiting + security middleware)
- `src/backend/tests/security/test_auth_bypass.py` — Auth bypass regression tests (OPS-003 adds rate limiting tests alongside)
- `src/backend/tests/performance/test_api_load.py` — API load baseline (OPS-001 monitoring tests complement this)
- `.github/workflows/ci.yml` — CI with docs-lint, backend-tests, frontend-tests, e2e-tests jobs
- STAB-004 CORS hardening already done in `main.py:64`

### Environment Notes

- **WSL blocker**: `vitest run` stalls on `/mnt/c/` NTFS mount. Frontend tests must run in GitHub Actions CI or native Linux. Static checks (`tsc --noEmit`, `lint`) work fine locally.
- **Backend pytest**: May fail in WSL due to `pydantic_core` binary mismatch if using Windows venv. Use a Linux-native venv or run in CI.
- **npm install**: Use `--ignore-scripts` flag in WSL to avoid esbuild/rollup binary lock errors.

### Commit Convention

```
feat(S06-OPS-001): add monitoring metrics module with correlation IDs
feat(S06-OPS-002): add backup automation with integrity validation
feat(S06-OPS-003): add rate limiting middleware and security scan CI job
docs(S06-OPS-004): add API endpoint documentation
docs(S06-OPS-005): add user workflow manuals
docs(S06-OPS-006): add HIPAA controls mapping and compliance checklist
```

### Definition of Done

- Monitoring, backup, and security scaffolding exists and is testable
- API, user, and compliance docs have baseline structure
- All new code has tests targeting 80%+ coverage
- `tsc --noEmit` and `lint` pass
- CI pipeline updated with security scan job
- Closeout summary written to `docs/plans/sprint-06-closeout-plan.md`
