# HealthCentral Documentation Index (Current)

**Last Updated:** 2026-09-08
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

## Active Plans & Specs (Current)

Linked here so they are reachable from a hand-maintained index rather than only
from the generated map (DOC-011).

- [`docs/plans/2026-09-08-backlog-closure-plan.md`](plans/2026-09-08-backlog-closure-plan.md)
  — every open item (partial features, open tickets, pending HC-M milestones) verified against the
  tree and sequenced, with the four decisions the owner has to make.
- [`docs/plans/2026-09-08-sql-fk-001-foreign-key-audit.md`](plans/2026-09-08-sql-fk-001-foreign-key-audit.md)
  — the written FK audit `SQL-FK-001` was blocked on: all 20 constraints, a decision each.
- [`docs/plans/2026-07-10-post-visit-record-intelligence-roadmap.md`](plans/2026-07-10-post-visit-record-intelligence-roadmap.md)
  — the HC-M12…HC-M24 roadmap; all phases now shipped, retained as the rationale record.
- [`docs/plans/2026-07-02-architect-review-proposal-tickets.md`](plans/2026-07-02-architect-review-proposal-tickets.md)
  — canonical ticket detail for the architect-review backlog (TASK_LIST links here).
- [`docs/plans/roadmap_gap_closure.md`](plans/roadmap_gap_closure.md) — gap-closure roadmap.
- [`docs/plans/ingest-imaging-pathology-spec.md`](plans/ingest-imaging-pathology-spec.md) — imaging/pathology extractor spec.
- [`docs/plans/implementation-log/README.md`](plans/implementation-log/README.md) — point-in-time implementation notes.
- [`docs/plans/2026-06-30-tech-upgrade-survey-9-areas.md`](plans/2026-06-30-tech-upgrade-survey-9-areas.md) — dependency/tech survey.
- [`docs/superpowers/plans/2026-07-13-hc-m21-search.md`](superpowers/plans/2026-07-13-hc-m21-search.md) and
  [`docs/superpowers/plans/2026-05-11-dynamic-port-selection.md`](superpowers/plans/2026-05-11-dynamic-port-selection.md)
  — feature implementation logs.

## Architecture Diagrams (Current)

- [`docs/architecture/README.md`](architecture/README.md) — hand-authored mermaid diagram set:
  system context and process topology, [backend structure](architecture/backend.md) (request
  lifecycle, module dependencies, data architecture), [pipelines](architecture/pipelines.md)
  (document→insight, agent graph, safety control-flow), [frontend](architecture/frontend.md), and
  [CI gates](architecture/ci-and-quality-gates.md).
- [`docs/architecture/performance-scalability-review.md`](architecture/performance-scalability-review.md)
  — honest assessment of what degrades as one profile's record grows, and what this system
  deliberately does not need.

## Generated Navigation (Advisory — Not Authoritative)

- [`openwiki/README.md`](../openwiki/README.md) — OpenWiki-generated repo map for coding agents
  (code location, file relationships). Advisory only: if it conflicts with this index, `CLAUDE.md`,
  `AGENT.md`, or `docs/roles/00_roles_index.md`, the hand-maintained docs win.

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

- [`docs/archive/README.md`](archive/README.md) — archive policy and full historical index
- `docs/05_backend_integration_status.md` (Sprint 06 integration snapshot retained for audit context)
- `docs/06_mvp_to_rag_execution_board.md` (sprint history)
- [`docs/archive/plans/UI-implementation-2-4.md`](archive/plans/UI-implementation-2-4.md) (superseded UI plan)
- [`docs/archive/plans/remaining-features-implementation.md`](archive/plans/remaining-features-implementation.md) (superseded execution plan)
- [`docs/archive/plans/next-agent-documentation-consolidation.md`](archive/plans/next-agent-documentation-consolidation.md) (completed hardening plan)
- [`docs/archive/plans/sprint-phase-2026-02-13-implementation-plan.md`](archive/plans/sprint-phase-2026-02-13-implementation-plan.md) (superseded planning draft)
- [`docs/archive/plans/2026-02-15-sprint-06-handoff-prompt.md`](archive/plans/2026-02-15-sprint-06-handoff-prompt.md) (completed sprint handoff; flattened from `sprint-series-2026-02-15/`)
- [`docs/archive/plans/2026-03-04-handoff.md`](archive/plans/2026-03-04-handoff.md) (superseded handoff, 22/23 tasks — RAG category-filter still open)
- [`docs/archive/plans/2026-03-28-roadmap-gsd-m001-m003-historical.md`](archive/plans/2026-03-28-roadmap-gsd-m001-m003-historical.md) (formerly root `ROADMAP.md`; `.gsd/` source no longer exists)
- [`docs/archive/plans/2026-07-12-phase-c-handoff-prompt.md`](archive/plans/2026-07-12-phase-c-handoff-prompt.md) (Phase C orchestration handoff, superseded)
- [`docs/archive/plans/2026-07-02-fable5-architect-handoff-prompt.md`](archive/plans/2026-07-02-fable5-architect-handoff-prompt.md) (one-time architect-review prompt, superseded)
- `docs/plans/2026-05-15-cursor-lab-workflow-plan.md` (formerly `.cursor/plans/`; confirmed shipped)
- `docs/plans/implementation-log/` (formerly top-level `implementation_plan/`; 5 point-in-time notes, all shipped)

## Source PRDs

- `docs/Local_First_Medical_Results_Companion_PRD_v0_1.md`
- `docs/features/03_features_prd.md`
