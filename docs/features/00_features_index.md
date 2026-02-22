# HealthCentral Features Index (Current)

**Last Updated:** 2026-02-21
**Owner:** Product Lead
**Refresh Trigger:** Feature shipped or new feature architecture doc added

This folder contains feature architecture references and the active remaining-work tracker.

> See [`docs/00_architecture_plans_index.md`](../00_architecture_plans_index.md) for the full documentation index.

## Feature Documents

| Document | Scope | Current Usage |
|----------|-------|---------------|
| `01_lab_result_interpreter_architecture.md` | Personal Lab Result Interpreter | Architecture reference |
| `02_medication_adherence_coach_architecture.md` | Adaptive Medication Adherence Coach | Architecture reference |
| `03_features_prd.md` | Combined PRD for both features | Product intent reference |
| `TASK_LIST.md` | Remaining implementation tasks | **Canonical active tracker** |

## Current Status Summary (as of Sprint 06)

- **Core features**: Auth, import, extraction, verification, trends, export, assistant, interpretations — all implemented.
- **Lab Interpreter**: Backend and frontend implemented with knowledge base, batch interpretation, panel interpretation.
- **Medication Coach**: Medications, schedules, dose logging, adherence stats, pattern learning — all implemented.
- **Notifications**: Settings, history, scheduler, test notifications — all implemented.
- **Sprint 05 (Frontend Quality)**: 188 frontend tests, accessibility (axe-core), responsive layout, visualization interactions, E2E workflows.
- **Sprint 06 (Platform Ops)**: Security middleware, monitoring/metrics, backup/restore, API/user/compliance documentation.
- Lab-to-medication correlation UX implemented (MedicationOverlay component, TrendsDashboard integration).
- Accessibility audit completed with ARIA roles, live regions, keyboard navigation.

## Remaining Work

- Security remediation from Sprint 06 review (see `docs/compliance/security-review-sprint06.md`).
- Deferred feature backlog (advanced export formats, enhanced search, multi-source imports).
