# Next Agent Plan: Documentation Consolidation + Remaining Hardening

> Historical Reference: this plan is retained for history. All work packages (DOC-003 through DOC-006, TEST-001/002, UX-001, A11Y-001) were completed in the v0.3.0 hardening pass (2026-02-12). This document is not an active tracker.
> For current status, see [`docs/features/TASK_LIST.md`](../../features/TASK_LIST.md).

**Last Updated:** 2026-02-12
**Owner:** Implementation Agent
**Refresh Trigger:** New hardening task added or doc work package completed
**Primary Tracker:** `docs/features/TASK_LIST.md`

## Goal

Execute the remaining documentation-consolidation and hardening backlog with minimal ambiguity, using a test-driven Red/Green/Refactor flow per item.

## Guardrails

- Treat `docs/features/TASK_LIST.md` as source of truth for open items and status.
- Do not re-activate historical plan docs as active trackers.
- Keep file ownership explicit: update canonical docs first, then references.

---

## Work Package 1: `DOC-003` Docs Drift Lint Automation (Baseline Complete)

### Files

- `scripts/docs_lint.py`
- `docs/00_architecture_plans_index.md`
- `docs/features/TASK_LIST.md`

### Implement

1. Extend the existing CLI lint script (`python3 scripts/docs_lint.py`) with additional drift rules as needed.
2. Keep existing deterministic baseline rules:
   - Canonical docs include a `Last Updated` line.
   - Historical docs include `Historical Reference` banner.
   - `docs/05_backend_integration_status.md` does not include stale marker `LLM Required`.
   - `docs/features/TASK_LIST.md` includes `Red`, `Green`, and `Refactor` phases for active items.
3. Preserve machine-readable failures (one line per violation).

### Verify

- `python3 scripts/docs_lint.py`
- Intentionally break one rule and confirm non-zero exit, then restore and pass.

### Done When

- Script continues to pass on clean repo state after any rule additions.
- New rules are documented in script header and reflected in task list notes.

---

## Work Package 2: `DOC-004` Canonical Ownership + Freshness Policy

### Files

- `docs/00_architecture_plans_index.md`
- `docs/05_backend_integration_status.md`
- `docs/features/00_features_index.md`
- `docs/features/TASK_LIST.md`

### Implement

1. Add/update a short `Owner` and `Refresh Trigger` field in each canonical doc.
2. Define a monthly review cadence in `docs/features/TASK_LIST.md`.
3. Add cross-links so each canonical doc points back to the index.

### Verify

- `rg -n "Owner|Refresh Trigger|Last Updated" docs/00_architecture_plans_index.md docs/05_backend_integration_status.md docs/features/00_features_index.md docs/features/TASK_LIST.md`
- Manual link click-through validation from index to all canonical docs.

### Done When

- Canonical docs have explicit ownership/freshness metadata.
- No canonical doc is missing a direct link from the index.

---

## Work Package 3: `DOC-005` Historical Doc Normalization

### Files

- `docs/plans/UI-implementation-2-4.md`
- `docs/plans/remaining-features-implementation.md`
- `docs/06_mvp_to_rag_execution_board.md`

### Implement

1. Ensure each historical doc begins with a clear superseded banner.
2. Add direct pointer to `docs/features/TASK_LIST.md` for active work.
3. Remove or reword any section that presents itself as the active tracker.

### Verify

- `rg -n "Historical Reference|active tracker|Start Here" docs/plans/UI-implementation-2-4.md docs/plans/remaining-features-implementation.md docs/06_mvp_to_rag_execution_board.md`

### Done When

- Historical docs are unambiguous and non-competitive with canonical trackers.

---

## Work Package 4: `TEST-001` Backend Test Runtime Reliability

### Files

- `docs/05_backend_integration_status.md`
- `src/backend/requirements.txt`
- Optional helper: `scripts/backend-test-setup.sh` or `scripts/backend-test-setup.ps1`

### Implement

1. Document exact backend test bootstrap path per environment (WSL/Linux and Windows venv).
2. Add a helper script to install deps and run `pytest` with consistent command line.
3. Capture known failure modes and remediation steps.

### Verify

- `cd src/backend && python3 -m pytest -q` (or documented environment-specific equivalent)

### Done When

- A new contributor can run backend tests without ad-hoc setup discovery.

---

## Work Package 5: `TEST-002` Frontend Vitest Stability

### Files

- `src/frontend/vitest.config.ts`
- `src/frontend/package.json`
- `src/frontend/README.md`

### Implement

1. Reproduce `vitest-pool-runner` worker timeout deterministically.
2. Stabilize runtime config (pool strategy, worker count, timeouts) without masking real failures.
3. Document stable command and expected duration range.

### Verify

- `cd src/frontend && npm test -- --run`
- Run at least twice to confirm deterministic completion.

### Done When

- Full suite exits cleanly without unhandled worker timeout errors.

---

## Work Package 6: `UX-001` and `A11Y-001` Residual Product Polish

### Files

- `src/frontend/src/pages/TrendsDashboard.tsx`
- `src/frontend/src/pages/MedicationDetail.tsx`
- `src/frontend/src/__tests__/`
- `docs/02_frontend_accessibility_plan.md`

### Implement

1. Add explicit lab/medication correlation entry points.
2. Add tests first for cross-navigation and empty states.
3. Run accessibility checks and fix keyboard/screen-reader/reduced-motion gaps.

### Verify

- `cd src/frontend && npm test -- --run`
- Any accessibility checks selected by the agent (document command and result).

### Done When

- Cross-feature flow is discoverable in UI and covered by tests.
- Accessibility acceptance checklist is completed with evidence.

---

## Handoff Completion Checklist

- [ ] Updated `docs/features/TASK_LIST.md` status for each completed item.
- [ ] Added session note with date and exact commands run.
- [ ] Re-ran docs lint and test suites.
- [ ] Confirmed canonical index links are valid.
