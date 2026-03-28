<!-- Generated from .gsd/milestones/M001/M001-ROADMAP.md via GSD planning tools. Re-run milestone planning to refresh. -->

# M001: Project Re-entry Audit and GSD Baseline

## Vision
Reconstruct the current project state after inactivity by auditing branch history, validating the live functionality baseline, and establishing GSD as the canonical roadmap and context layer for future work.

## Slice Overview
| ID | Slice | Risk | Depends | Done | After this |
|----|-------|------|---------|------|------------|
| S01 | Branch and functionality audit | medium | — | ✅ | After this slice, the team can answer: what shipped through Sprint 06, what `main` added afterward, and what is currently partial or broken. |
| S02 | Initialize GSD baseline artifacts | low | S01 | ✅ | After this slice, future contributors can open GSD artifacts instead of reconstructing status from scratch. |
| S03 | Recovery backlog and next-step framing | medium | S01, S02 | ✅ | After this slice, the team has a prioritized shortlist of cleanup and follow-up work instead of an unstructured pile of drift. |

## Follow-up Milestone Status

- **M002: Immediate Recovery Backlog** — Completed.
  - `S01` Documentation reconciliation — complete
  - `S02` Environment bootstrap verification — complete
  - `S03` Branch hygiene and local artifact containment — complete
  - Canonical roadmap: `.gsd/milestones/M002/M002-ROADMAP.md`
  - Validation: `.gsd/milestones/M002/M002-VALIDATION.md`
  - Summary: `.gsd/milestones/M002/M002-SUMMARY.md`
- **M003: Assistant surfacing and proof hardening** — Active.
  - `S01` Explain Assistant category filter exposure — complete
  - `S02` Proof-surface cleanup for docs and auth — complete
  - `S03` Integrated verification and hygiene guardrails — active
  - Contributor proof bundle (repo root):
    - `python3 scripts/repo_hygiene_check.py`
    - `python3 scripts/docs_lint.py`
    - `npm --prefix src/frontend run test:run -- src/__tests__/ExplainAssistant.test.tsx`
    - `npx --prefix src/frontend playwright test --config src/frontend/playwright.config.ts src/frontend/e2e/assistant.spec.ts --grep "category"`
    - `PYTHONPATH=src/backend ./.wsl-pytest-venv/bin/python -m pytest src/backend/tests/test_bootstrap_check.py src/backend/tests/security/test_password_hashing.py src/backend/tests/test_repo_hygiene_check.py -q`
  - Canonical roadmap: `.gsd/milestones/M003/M003-ROADMAP.md`
  - Slice plans: `.gsd/milestones/M003/slices/S01/S01-PLAN.md`, `.gsd/milestones/M003/slices/S02/S02-PLAN.md`, `.gsd/milestones/M003/slices/S03/S03-PLAN.md`
