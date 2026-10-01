# HealthCentral Features Index (Current)

**Last Updated:** 2026-07-23
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
| `04_self_improvement_loop.md` | Self-Improvement Loop | Design spec |
| `TASK_LIST.md` | Remaining implementation tasks | **Canonical active tracker** |

## Current Status Summary (as of Sprint 06)

- **Core features**: Auth, import, extraction, verification, trends, export, assistant, interpretations — all implemented.
- **Lab Interpreter**: Backend and frontend implemented with knowledge base, batch interpretation, panel interpretation.
- **Medication Coach**: Medications, schedules, dose logging, adherence stats, pattern learning — all implemented.
- **Notifications**: Settings, history, scheduler, test notifications — all implemented. Reminders are delivered as OS toasts while the profile vault is unlocked; locked profiles are recorded as `skipped_locked`. Quiet-hours settings are stored per-medication but not yet enforced by the scheduler (pre-existing gap).
- **Sprint 05 (Frontend Quality)**: 188 frontend tests, accessibility (axe-core), responsive layout, visualization interactions, E2E workflows.
- **Sprint 06 (Platform Ops)**: Security middleware, monitoring/metrics, backup/restore, API/user/compliance documentation.
- Lab-to-medication correlation UX implemented (MedicationOverlay component, TrendsDashboard integration).
- Accessibility audit completed with ARIA roles, live regions, keyboard navigation.

### Recent Updates

- **FHIR R4 Export (HC-M22)**: `POST /api/v1/export/fhir` generates a verified-only, strict-redacted FHIR R4 `Bundle` (Patient/Observation/MedicationStatement/Condition/DocumentReference/Encounter/CarePlan/DiagnosticReport); `GET /api/v1/export/fhir/{export_id}/download` returns it as `application/fhir+json`. Requires explicit `confirm=true`. See `docs/api/endpoints.md` and `docs/features/TASK_LIST.md` session notes for the full field mapping.
- **CSV/FHIR Structured Import (HC-M23)**: `.csv` and `.json` (FHIR R4 `Bundle`) files upload through the existing `POST /api/v1/documents/import` route. Pure parsers (`modules/import_structured.py`) land observations and medication/diagnosis mentions as **unverified** rows — no OCR, no LLM. Medication mentions become HC-M19 reconciliation suggestions; they never mutate the medication tracker directly. Reprocessing a structured-import document is rejected (data-loss guard); the fix is delete-and-re-import.
- **Bounded Agentic Queries (HC-M24)**: three read-only agent tools (`query_care_tasks`, `query_medication_changes`, `query_timeline`) let the assistant answer record-navigation questions ("what's still open?", "what changed?") with cited, non-speculative answers, including deterministic no-LLM fallbacks. "Ask about your records" suggested-query chips surface the same intents in the assistant UI.
- **Model-Agnostic Provider Layer**: Backend now supports hardware-adaptive LLM selection via `src/backend/core/llm/` provider interface. Users select provider and model through the model provider API (`GET`/`PUT /api/v1/settings/model/provider`). Available providers: `llama_cpp_provider` (default, embeds llama.cpp, auto-detects GGUF chat template) and `ollama_provider` (optional, localhost-only base URL). Hardware tier auto-selection currently accepts `low`, `mid`, and `high` for set/download operations; Gemma 4 configs are registered/read-visible as alternates but current write schemas do not accept them as selectable/downloadable tiers.
- **Biomarker Grounding in RAG**: Lab Interpreter assistant responses now ground in two citation layers. `[YOUR_RESULTS:N]` cites patient's own observation context (latest measured value, normal range, trend direction), while `[REFERENCE:N]` cites auto-seeded reference knowledge base (general biomarker definitions, clinical significance). At startup, the reference KB auto-populates if empty via `seed_knowledge_base.py`. Response structure separates "Report Facts" (citing user's data) from "General Info" (citing reference KB) to maintain education-only framing and no-medical-advice compliance.

## Remaining Work

- Security remediation from Sprint 06 review (see `docs/compliance/security-review-sprint06.md`).
- Deferred feature backlog (advanced export formats, enhanced search). CSV/FHIR import (HC-M23) and FHIR R4 export (HC-M22) shipped — see Recent Updates above.
