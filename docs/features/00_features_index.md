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
| `04_self_improvement_loop.md` | Self-Improvement Loop | Design spec |
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

### Recent Updates

- **Model-Agnostic Provider Layer**: Backend now supports hardware-adaptive LLM selection via `src/backend/core/llm/` provider interface. Users select provider and model through the model provider API (`GET`/`PUT /api/v1/settings/model/provider`). Available providers: `llama_cpp_provider` (default, embeds llama.cpp, auto-detects GGUF chat template) and `ollama_provider` (optional, localhost-only base URL). Hardware tier auto-selection currently accepts `low`, `mid`, and `high` for set/download operations; Gemma 4 configs are registered/read-visible as alternates but current write schemas do not accept them as selectable/downloadable tiers.
- **Biomarker Grounding in RAG**: Lab Interpreter assistant responses now ground in two citation layers. `[YOUR_RESULTS:N]` cites patient's own observation context (latest measured value, normal range, trend direction), while `[REFERENCE:N]` cites auto-seeded reference knowledge base (general biomarker definitions, clinical significance). At startup, the reference KB auto-populates if empty via `seed_knowledge_base.py`. Response structure separates "Report Facts" (citing user's data) from "General Info" (citing reference KB) to maintain education-only framing and no-medical-advice compliance.

## Remaining Work

- Security remediation from Sprint 06 review (see `docs/compliance/security-review-sprint06.md`).
- Deferred feature backlog (advanced export formats, enhanced search, multi-source imports).
