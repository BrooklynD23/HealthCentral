# Post-Visit & Record Intelligence Roadmap

> Status: **PLAN ONLY — no product code changes in this document's commit**
> Date: 2026-07-10
> Input: external "verdict report" comparing HealthCentral against PostVisit.ai, OpenHealth, Doctor Dok, FreeScribe, PicnicHealth, and Epic MyChart/Emmie — cross-checked against the actual codebase.
> Authority: [CLAUDE.md](../../CLAUDE.md) and [AGENT.md](../../AGENT.md) override everything here. Existing milestones HC-M02/M05/M06/M07/M08 in [feature_list.json](../../feature_list.json) are **not** displaced by this plan.

---

## 1. Assessment of the verdict report

The report's strategic conclusion is sound and adopted: **expand from a lab-results dashboard toward a local-first, citation-grounded post-visit / personal-health-record intelligence system** — import → classify → extract → verify → timeline → explain → prepare → track → export. It correctly identifies the defensible lane (more private than cloud PHR products, stricter safety posture than "AI second opinion" tools) and correctly warns off diagnosis/treatment framing, physician-scribe SOAP generation, and early mobile/cloud/provider-integration work.

However, the report's gap analysis is **stale in several places**. Verified against the code on 2026-07-10:

| Report claim | Actual repo state |
|---|---|
| "Visit-note analysis: limited / not primary — major gap" | **v1 exists.** INGEST-EPIC-001 shipped: rule-based `modules/document_classifier.py` (imaging / pathology / visit_notes / lab), regex extractors `extract_visit_notes.py`, `extract_imaging.py`, `extract_pathology.py`, wired into `api/documents.py`, persisted in `document_category` / `document_entity` tables (profile migration 004). |
| "Imaging report support — gap (high priority)" | v1 extractor exists (modality, findings, impression, etc. per `docs/plans/ingest-imaging-pathology-spec.md`). |
| "Doctor-question generator — missing (very high)" | **Partially exists.** `api/export.py POST /questions` + `QuestionPrompt` in `modules/export.py` generate discussion prompts from trends/abnormals. Missing: questions sourced from visit-note entities, med changes, and open tasks. |
| "Exportable visit-prep packet — missing" | **Partially exists.** Doctor-summary generation + download (`/export/doctor-summary`), CSV/JSON export. Missing: tasks, symptoms, questions, attached source docs in one packet. |
| "Family/caregiver profiles — gap" | Multi-profile support with per-profile SQLCipher isolation already exists (`api/profiles.py`, `ProfileSetup.tsx`). Missing only caregiver-specific UX (proxy labels, per-profile share packets). |
| "Document-type classifiers + typed schemas (recommended architecture)" | Already the chosen architecture in the repo. |
| "Medication management" listed as current | Confirmed — plus adherence patterns, notifications, streak/gamification engines the report doesn't mention. |

**Genuinely missing** (report is right, confirmed by grep — no hits in product code): health timeline, follow-up task extraction, smart highlights, pinboards, medication reconciliation from documents, char-offset source spans with verbatim quotes (`document_entity` has `source_page`/`source_bbox_json` but extractors never populate them and there is no quote/char-span model), symptom journal, FHIR import/export, wearable import.

**Corrections to the report's priorities:**

- "Document type classifier" and "after-visit summary parser" are not greenfield builds — they are **upgrades** of existing v1 modules. Cheaper than the report assumes; extend, don't create (CLAUDE.md §2).
- The report's "source-span extraction model" is under-ranked at #2 in its own list but is actually the **single prerequisite** for highlights, tasks, timeline citations, and safe question generation. It goes first.
- LLM-based extraction prompts ("one per record type") must remain **optional enhancement on top of rule-based extraction**, behind ModelRunner, with the no-LLM fallback functional (AGENT.md flow 2 invariant). Rule-first, LLM-assist-second.
- The report's Phase 1 bundles eight features; that is too large for evidence-gated milestones. Re-cut below into smaller verifiable slices consistent with `feature_list.json` conventions.

---

## 2. Verified capability baseline (what exists today)

- **Pipeline**: upload → `modules/ingest` → classify (`document_classifier`) → per-category extract (`extract.py` labs; `extract_visit_notes/imaging/pathology`) → `document_category`/`document_entity` + observations (per-profile DB) → verification (VerificationWorkbench) → trends (TrendsDashboard).
- **Assistant**: RAG with `[YOUR_RESULTS:N]` / `[REFERENCE:N]` citations, faithfulness/verifier/interpret_safety guards, per-category context (`api/assistant.py` accepts `document_category`), no-LLM fallback.
- **Export**: doctor summary (sections, key findings, citations), question prompts, CSV/JSON.
- **Meds**: tracking, schedules, adherence patterns, notifications, gamification.
- **Safety/infra**: redaction, audit logging, dual Alembic chains (profile head = 009), eval gate with injection/PHI axes (HC-M05), RL dataset export with strict redaction.
- **Frontend pages**: DocumentInbox, VerificationWorkbench, TrendsDashboard, ExplainAssistant, LabInterpreter, MedicationCoach/Detail, ExportPage, ProfileSetup, Settings, NotificationSettings.

---

## 3. Phased plan

Ordering principle: each phase produces user-visible value and a verifiable eval/test artifact; safety-critical prerequisites come first; nothing here blocks in-flight HC-M05/M06 work (M06's extraction golden-set harness is reused by every extractor upgrade below).

### Phase A — Trustworthy extraction substrate + Post-Visit Mode (proposed HC-M12…HC-M15)

**A1. Source-span model (HC-M12)** — prerequisite for everything.
- *User story*: every extracted fact can show me the exact sentence in my document it came from.
- *Backend*: extend `document_entity` with `char_start`, `char_end`, `quote` (verbatim source text), `verified_by_user` (nullable bool), `extraction_version`. New profile migration `010_entity_source_spans.py` (linear `down_revision = '009'`). Update the three category extractors + lab extractor to populate spans; entities without a resolvable span get `quote=None` and are flagged low-confidence.
- *Frontend*: VerificationWorkbench shows the quote next to each entity; verify/reject per entity.
- *Safety*: unverified entities must be labeled `unverified` in any assistant/export surface; no new safety-module edits needed.
- *Tests*: `HC-SPAN-NNN` pytest — span offsets round-trip against fixture texts; extractor returns quote ⊆ source text (exact substring assertion); migration up/down.
- *Risk*: low (additive columns, additive migration). ~Small.

**A2. After-visit / discharge extraction upgrade (HC-M13)**
- *User story*: I upload an after-visit summary or discharge note and get a verified, structured breakdown: diagnoses mentioned, medication changes, tests ordered, referrals, follow-up instructions, warning signs.
- *Backend*: extend `extract_visit_notes.py` (do **not** create a parallel module) with entity types: `medication_change` (drug/dose/action=start|stop|change), `test_ordered`, `referral`, `follow_up_instruction`, `warning_sign`, `facility`, plus `visit_subtype` (after_visit_summary | discharge | progress | consult) refining the classifier. Discharge-specific fields (admission reason, discharge diagnosis) as entity types, not a new table. Optional LLM-assist extraction pass through `ModelRunner` behind a per-request flag, output constrained to spans present in the source (reject any extraction whose quote is not a substring of the document).
- *Safety*: extraction only — no interpretation. All entities land unverified. `interpret_safety` untouched.
- *Tests*: extend the HC-M06 golden-set harness with a synthetic after-visit/discharge corpus (10–20 fixtures); precision/recall per entity type; adversarial fixture with embedded prompt-injection text (feeds the HC-M05 remaining scope: instructions embedded in uploaded documents).
- *Risk*: medium (regex brittleness on real-world note formats — mitigated by golden set + human verification gate). ~Medium.

**A3. Health timeline (HC-M14)**
- *User story*: one chronological view of everything — labs, visits, imaging, med starts/stops, tasks — each card linking to its source document and verification status.
- *Backend*: new `modules/timeline.py` (read-model service, **no new table initially** — derive events from existing `observations`, `document_category`, `document_entity`, `medications`; a materialized `timeline_event` table only if performance demands it later). Event: `{event_type, event_date, event_date_source (document_date|entity_date|upload_date), title, doc_id, entity_ids, verification_status}`. Undated items appear in a separate "needs a date" tray, mirroring the existing undated-observation rule. New route `api/timeline.py` (GET, filters: type/date-range/provider) with audit logging.
- *Frontend*: new `TimelinePage.tsx` + service hook via `services/index.ts` barrel; cards link into DocumentInbox/VerificationWorkbench/TrendsDashboard.
- *Tests*: `HC-TML-NNN` — event derivation from fixture DB, date-source precedence, per-profile isolation (event query must go through `ProfileDbSession`), audit-log presence; Playwright e2e for render + filter.
- *Risk*: low-medium (read-only aggregation). ~Medium.

**A4. Follow-up task extraction + tracker (HC-M15)**
- *User story*: follow-up instructions from my visit notes become a checklist I can mark done, each item showing the clinician's exact words.
- *Backend*: new `care_plan_task` table (profile migration 011): `title, due_date (nullable), due_date_confidence, status (open|done|ignored|needs_review), source_document_id, source_entity_id, source_quote, user_note, created_at`. New `modules/tasks.py`: derive candidate tasks from `follow_up_instruction`/`test_ordered`/`referral` entities; **never invent due dates** — vague timing ⇒ `due_date=None, status=needs_review`. Tasks are created only on explicit user acceptance in the UI (human-in-the-loop, consistent with observation verification). New route `api/tasks.py` (CRUD + accept-candidates) with audit logging. Optional reminder wiring into the existing `notification_scheduler` (record-keeping reminders only, never clinical urging).
- *Safety*: tasks are transcriptions of clinician-stated instructions, not recommendations; UI copy uses "The note says…". No auto-acceptance.
- *Tests*: `HC-TASK-NNN` — candidate derivation, no-invented-dates property test, status transitions, isolation, audit; e2e accept/complete flow.
- *Risk*: medium (date parsing of relative expressions like "in 4 weeks" — anchor to `event_date` only when both are certain, else needs_review). ~Medium.

**Phase A exit criteria**: upload a fixture discharge note → classified, extracted with quotes, entities verifiable, events on timeline, follow-up candidates offered, all with passing golden-set metrics; ~620-test baseline intact; `tsc --noEmit` clean.

### Phase B — Comprehension & navigation layer (proposed HC-M16…HC-M19)

**B1. Smart highlights (HC-M16)** — derived labels over existing data, not a new extraction pass: `abnormal_value` (from observation reference-range flags), `medication_started/stopped/changed`, `follow_up_needed`, `test_ordered`, `new_diagnosis_mentioned`, `low_confidence_extraction`, `needs_verification`. Implement as `modules/highlights.py` computing tags from entities/observations (no table; recompute on read, cache per doc). Surface as chips in DocumentInbox, timeline cards, and document detail. Every highlight resolves to a source span. Tests: tag derivation matrix.

**B2. Doctor-question generator upgrade (HC-M17)** — extend `modules/export.py` `QuestionPrompt` sources to include verified visit-note entities, medication changes, open/needs_review tasks, and unclear instructions. Questions only, template-driven ("Can you explain why this test was ordered?"), each carrying its source citation; LLM phrasing optional via ModelRunner with template fallback. Guard: generated questions pass `interpret_safety` screening like any assistant output (no new safety code — reuse). Tests extend existing export tests.

**B3. Visit-prep packet (HC-M18)** — extend ExportPage + `api/export.py` with a packet composer: current meds, recent abnormal (verified) labs, recent visits/diagnoses mentioned, open tasks, saved questions, selected source documents. Formats: Markdown + printable PDF reusing the doctor-summary renderer. **All free text passes `modules/redaction.py` before writing to exportable files** (existing invariant). Explicit user confirmation before generation, mirroring RL-export UX.

**B4. Medication reconciliation (HC-M19)** — after each document with `medication_change` entities, diff against the medication tracker: new / stopped / dose-changed / possible-duplicate / unclear. Present as "Source says X — your list has Y — add to tracker?" suggested actions; user confirms every change (never auto-mutate the med list). Extends `modules/recommend.py`-adjacent logic or a small `modules/med_reconcile.py`; check prior art in `medications`/`adherence_patterns` first. This is the highest-safety-sensitivity item in Phase B: wording review against `interpret_safety` prohibited patterns required; **ask before touching** if any safety module needs changes.

### Phase C — Vault & workspace features (proposed HC-M20…HC-M21)

**C1. Pinboards / collections (HC-M20)** — user-curated collections of documents/observations/tasks/questions (`pinboard`, `pinboard_item` tables, profile migration). Each pinboard exports a focused packet via the Phase B packet composer. Simple CRUD; high perceived value, low risk.

**C2. Search & filtering (HC-M21)** — cross-record search over documents/entities/observations (SQLite FTS5 inside the profile DB — stays local and encrypted), filters by provider/date/category/highlight. Reuses timeline filter params.

Also in Phase C, opportunistic: OCR/extraction-confidence UX (surface existing confidence scores prominently before verification), record de-duplication warning on upload (hash + date heuristics).

### Phase D — Interoperability (proposed HC-M22…HC-M23)

**D1. FHIR export (HC-M22)** — map existing entities to FHIR R4 resources: Patient, Observation, MedicationStatement, Condition, DocumentReference, Encounter, CarePlan, DiagnosticReport. Export-only first (import is much harder and lower value until export proves the mapping). File-based, redaction-checked, explicit confirmation. No network.
**D2. FHIR/CSV import (HC-M23)** — FHIR bundle + CSV lab import as new ingest sources feeding the same classify→extract→verify pipeline (imported facts are still unverified until user review). Apple Health / Health Connect import builds on this later and is **out of near-term scope**.

### Phase E — Bounded agentic queries (proposed HC-M24)

"What changed since my last visit?", "Which follow-up tasks are open?", "Summarize my cardiology history", "Show all medication changes." These are RAG compositions over timeline/tasks/entities — extend `modules/rag.py` retrieval sources and the existing `modules/agent/` rather than new layers; all outputs citation-gated, no-LLM fallback preserved. Gate behind the HC-M05 eval axes (each new retrieval source needs injection-corpus coverage — retrieved entity quotes are attacker-controlled text).

### Explicitly deferred (agree with report)

Mobile app, cloud sync/E2EE sharing service, provider record retrieval, audio recording/transcription (visit-audio import can be revisited after Phase B — transcript-file import is just another document type), clinician SOAP generation, translation, wearables, insurance/EOB parsing. Rationale: expensive, off-lane, or dilutes local-first guarantees.

---

## 4. Cross-cutting safety review (applies to every phase)

1. No diagnosis, no treatment recommendation, no dosing — `interpret_safety` prohibited patterns keep passing; new user-facing copy uses "the document says / the note mentions".
2. No extracted fact is treated as trusted until user-verified; unverified facts are labeled wherever surfaced.
3. Every claim in assistant/export output carries a citation (`[YOUR_RESULTS:N]` / `[REFERENCE:N]` or a source quote); no citation ⇒ don't say it.
4. Redaction before anything leaves: packets, FHIR exports, share bundles all route through `modules/redaction.py` (strict mode for anything bundled for third parties).
5. Local-first: no new network paths; LLM assist only through `ModelRunner`; Ollama stays localhost.
6. Per-profile isolation: every new table is a profile-DB table with its own linear migration; no profile data through master `get_db()`.
7. Audit logging on every new route (timeline, tasks, pinboards, search, packet, FHIR).
8. Extracted document text is untrusted input: injection-resistance eval cases required for each new surface that feeds extracted text to the LLM (extends HC-M05 corpus).
9. Changes to `interpret_safety.py`, `redaction.py`, `faithfulness.py`, `verifier_agent.py`, auth/encryption require explicit owner approval before touching (CLAUDE.md §1) — none are *required* by Phases A–C as designed.

---

## 5. Files to inspect before coding each milestone

| Milestone | Read first |
|---|---|
| HC-M12 spans | `modules/extract*.py`, `models/document_category.py`, `migrations/profile/versions/004_*.py`, `api/documents.py` (extraction wiring ~L600–700), VerificationWorkbench |
| HC-M13 after-visit | `modules/extract_visit_notes.py`, `modules/document_classifier.py`, `docs/plans/ingest-imaging-pathology-spec.md`, HC-M06 golden-set harness, `core/model_runner` |
| HC-M14 timeline | `api/observations.py` (trend queries, undated rule), `models/observation.py`, `core/profile_database`, audit middleware/model |
| HC-M15 tasks | `modules/notification_scheduler.py`, `models/medication.py` (schedule/date patterns), `api/medications.py` (CRUD conventions) |
| B-phase | `modules/export.py` + `api/export.py`, `modules/recommend.py`, `modules/adherence_patterns.py`, `modules/interpret_safety.py` (read-only), ExportPage |
| D-phase | `modules/redaction.py` (read-only), `modules/ingest.py`, observation/medication models for FHIR mapping |

---

## 6. Promotion into the live inventory

This document is a proposal. On owner approval, each accepted milestone (HC-M12+) should be added to `feature_list.json` with verification steps per [docs/agentic/harness.md](../agentic/harness.md), sequenced after (or interleaved with, at owner discretion) the in-flight HC-M02/M05/M06/M07/M08 milestones. HC-M06's extraction eval card is a **dependency-of-convenience** for HC-M13's golden set and should land first or together.
