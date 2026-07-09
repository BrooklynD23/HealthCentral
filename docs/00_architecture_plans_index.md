# HealthCentral Documentation Index (Current)

**Last Updated:** 2026-05-15
**Owner:** Project Lead
**Refresh Trigger:** New doc added or doc archived

This index defines the canonical documentation order and marks legacy planning files that are kept only for history.

> Canonical index — see also [`docs/features/TASK_LIST.md`](features/TASK_LIST.md) for active work items.

## Start Here (Canonical Doc Order)

1. `README.md`
   Repository entrypoint, current architecture overview, setup, and verification commands.
2. `docs/api/endpoints.md`
   Exact mounted backend route inventory and auth requirements.
3. `docs/00_architecture_plans_index.md`
   This file — full documentation index (you are here).
4. `docs/features/TASK_LIST.md`
   Remaining backlog only (active implementation and consolidation tasks).
5. `docs/05_backend_integration_status.md`
   Historical Reference — Sprint 06 snapshot retained for audit context, not the live tracker.

Also see [`docs/roles/00_roles_index.md`](roles/00_roles_index.md) for a domain-based ("which doc for
X") entry point, and [`docs/plans/implementation-log/`](plans/implementation-log/) for point-in-time
implementation notes (formerly the top-level `implementation_plan/` directory).

## Planning (Current)

- `docs/plans/roadmap_gap_closure.md`  
  Gap-closure roadmap (security follow-ups + PRD completion) intended for PM/Senior Dev approval, then conversion into GitHub Issues.

## Architecture References (Current)

- `docs/01_backend_architecture_plan.md`
- `docs/02_frontend_accessibility_plan.md`
- `docs/03_data_confidentiality_pipeline_plan.md`
- `docs/04_local_models_inference_plan.md`

## Feature References

- `docs/features/00_features_index.md`
- `docs/features/01_lab_result_interpreter_architecture.md`
- `docs/features/02_medication_adherence_coach_architecture.md`
- `docs/features/03_features_prd.md`

## Operations & Compliance Documentation (Sprint 06)

- `docs/api/` — API endpoint documentation, authentication, integration guide
- `docs/user/` — User workflows, getting started, troubleshooting, FAQ
- `docs/compliance/` — HIPAA controls, data privacy, audit checklist, disaster recovery, security review
- `docs/model_tiers/` — Tiered model system documentation

## Historical References (Do Not Use as Active Backlog)

- `docs/05_backend_integration_status.md` (Sprint 06 integration snapshot retained for audit context)
- `docs/06_mvp_to_rag_execution_board.md` (sprint history)
- `docs/plans/UI-implementation-2-4.md` (superseded UI plan)
- `docs/plans/remaining-features-implementation.md` (superseded execution plan)
- `docs/plans/next-agent-documentation-consolidation.md` (completed hardening plan)
- `docs/plans/sprint-phase-2026-02-13-implementation-plan.md` (superseded planning draft)
- `docs/plans/2026-02-15-sprint-06-handoff-prompt.md` (completed sprint handoff; flattened from `sprint-series-2026-02-15/`)
- `docs/plans/2026-03-04-handoff.md` (superseded handoff, 22/23 tasks — RAG category-filter still open)
- `docs/plans/2026-03-28-roadmap-gsd-m001-m003-historical.md` (formerly root `ROADMAP.md`; `.gsd/` source no longer exists)
- `docs/plans/2026-05-15-cursor-lab-workflow-plan.md` (formerly `.cursor/plans/`; confirmed shipped)
- `docs/plans/implementation-log/` (formerly top-level `implementation_plan/`; 5 point-in-time notes, all shipped)

## Source PRDs

- `docs/Local_First_Medical_Results_Companion_PRD_v0_1.md`
- `docs/features/03_features_prd.md`
