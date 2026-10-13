# 02 — Existing implementation map (file-level evidence)

> **Point-in-time research (2026-10-12)** on `origin/main@4884d38`. Paths are
> relative to `src/backend/` unless they start with `src/frontend`. **✓** = the
> orchestrator re-read the line or ran the command; unmarked rows come from the
> workstream-D map and were not individually re-read. Back to
> [00-README.md](00-README.md). Scope since owner direction WEAR-OD1
> (2026-10-13): Apple and Garmin; Samsung mentions below are reference only.

## Summary

There is **no wearable code** in the repo. Every seam is lab-oriented. The
closest prior art is HC-M23 structured import (CSV + FHIR) and HC-M18 visit-prep
packet. Wearables were explicitly deferred in
[2026-07-10 roadmap](../../plans/2026-07-10-post-visit-record-intelligence-roadmap.md)
(lines 106 and 114 ✓) and "Apple Health … out of scope v1" in
[04-mcp-interop.md](../2026-09-08/04-mcp-interop.md) (✓).

## 1. Upload, structured import, dedup

| path:line | symbol | fact | tests |
|---|---|---|---|
| `api/documents.py:402` ✓ | `POST /documents/import` → `import_document` | Encrypts to vault, creates `Document`, routes structured types | `test_documents_api.py` |
| `api/documents.py:56` ✓ | `_STRUCTURED_IMPORT_DOC_TYPES = ("lab_csv", "fhir_bundle")` | Dispatch list a new `wearable_export` type would join | `test_structured_import.py` |
| `api/documents.py:710-826` ✓ | `_run_structured_import_pipeline` | Decrypt → pure parse → persist; `user_verified=False` at `:759` | `test_structured_import.py` |
| `api/documents.py:338-386` | `_find_duplicate_warning` | Same `content_hash` → warning only, never blocks | `test_document_confidence_duplicates.py` |
| `modules/import_structured.py:1-23` ✓ | module contract | Pure, DB-free, stdlib only, length-capped, never invents dates | `test_structured_import.py` |
| `modules/import_structured.py:77` ✓ | `_parse_date` | Returns a date string; **drops time and offset** (`'2026-10-01T23:30:00-07:00'` → `'2026-10-01'`, run 2026-10-12) | same |
| `modules/import_structured.py:224` ✓ | `_map_fhir_observation` | Reads `code.text`, `effectiveDateTime`, `valueQuantity`, `referenceRange`, `interpretation`; ignores `device`, `method`, `effectivePeriod` | same |
| `modules/ingest.py:131-174` ✓ | `detect_doc_type` | `.csv` → `lab_csv` always; `.json` only if `resourceType == "Bundle"`; `.xml`, `.zip`, `.fit` → `unknown` → 400 | none found |
| `core/config.py:121-122` ✓ | `max_import_file_size_mb = 50`, `supported_doc_types` | `.xml`/`.zip` not accepted; 50 MB likely below a multi-year Apple export (INFERRED, OM-1 measures it) | `test_config_validation.py` |
| `security/input_validator.py:41` ✓ | upload guard | Import limit = 50 MB × 1.05 on Content-Length | `tests/security/test_input_validator.py` |
| `src/frontend/src/pages/DocumentInbox.tsx:161` ✓ | `accept=".pdf,.png,.jpg,.jpeg,.csv,.json"` | Client accept list | `DocumentInbox.test.tsx` |

**Works today with zero code:** a vendor ECG **PDF** (Apple/Garmin/Samsung
share sheets) can be imported as a document. It will be classified as a lab
PDF and may yield no observations. That is a usable stopgap for "bring the ECG
report", not a wearable feature.

## 2. Storage

| path:line | fact |
|---|---|
| `models/observation.py:24-101` ✓ | `Observation`: `doc_id` NOT NULL (`:47`), single naive `collected_at`, `unit` free string, `user_verified`, `source_page`/`source_bbox_json` (PDF provenance). **No device, source-system, period, or timezone field.** |
| `models/document.py:51,57` ✓ | `doc_type String(50)`, `status String(20)` |
| `core/auth.py:341` | `ProfileDbSession` dependency |
| `migrations/profile/versions/012_pinboards.py` ✓ | Head of profile chain (`down_revision = "011_care_plan_tasks"`). A wearable table would be `013_*`. |
| `core/time.py:9-22` ✓ | `utcnow`, `utcfromtimestamp`: naive-UTC storage semantics |
| `modules/normalize.py:39-59` | Unit conversions cover mass/molar lab units only; no bpm, steps, ms, %, minutes |
| `modules/ingest.py:175-245`, `core/security.py:443` | AES-GCM vault at `app_data/vaults/<profile_id>/docs/<doc_id>.bin` |
| `api/backup.py` | Backups copy the whole profile DB and vault, so a new profile table is backed up with no extra code (INFERRED from flow 4 in `AGENT.md`) |

## 3. Paths that read `observations` — why wearable data must not go there

| path:line | Filters on `user_verified`? | Consequence if wearable rows were `Observation`s |
|---|---|---|
| `api/observations.py:512-560` trends ✓ | **No** | Unreviewed wearable points chart next to labs |
| `modules/rag.py:272-456` `_get_observation_chunks` ✓ | **No** (labels verified ones only) | Wearable values become `[YOUR_RESULTS:N]` chat context |
| `api/export.py:131-176` `_fetch_observations` ✓ | No (caller decides) | Doctor summary abnormal/trend sections; CSV/JSON export without provenance columns |
| `modules/export.py:502` packet ✓ | **Yes**, unverified excluded (`:521`) | Packet safe, but only after review |
| `modules/timeline.py:89` `_lab_events` | — | Every daily aggregate becomes a "lab_results" event |

## 4. Visit-prep, export, redaction, audit

| path:line | fact | tests |
|---|---|---|
| `api/export.py:666-823` ✓ | `VisitPrepRequest` (section flags, `reason_for_visit`, `confirm`); `POST /export/visit-prep`; requires `confirm=true` (`:718`) | `test_visit_prep_packet.py` |
| `api/export.py:48` ✓ | `_packet_store` in memory: packets vanish on restart | same |
| `modules/export.py:502-675` ✓ | `compose_visit_prep_packet`; `RedactionEngine(policy_level="strict")` at `:637` over every section | `test_visit_prep_packet.py`, `test_redaction.py` |
| `api/export.py:907-1015` | CSV/JSON patient export, full-fidelity (owner decision D3) | `test_export_api.py` |
| `modules/rl_dataset.py:43` | `SCHEMA_VERSION = "1.0"`: the **only** versioned export schema in the repo | `test_rl_feedback.py` |
| `core/audit.py:89` ✓ | `ALLOWED_DETAIL_KEYS` allowlist; new detail keys must be added | `test_audit_phi_minimization.py` |
| `core/audit.py:474` | `audit_and_commit` (fail-closed) | `test_audit_order_guard.py` |
| `tests/support/routes.py:27` ✓ | `route_client` for HTTP-level route tests (required by CLAUDE.md) | — |
| `src/frontend/src/pages/ExportPage.tsx:444-552` | Visit-prep UI | `VisitPrepService.test.tsx`, `ExportPage.test.tsx` |
| `src/frontend/src/pages/TrendsDashboard.tsx` | Recharts trend page | `TrendsDashboard.test.tsx` |

## 5. Symptoms

No symptom, journal, or diary model, route, or page exists (✓ grep of
`models/`, `api/`, `modules/`, `src/frontend/src` for "symptom": only
`modules/test_intent.py`). The roadmap lists a symptom journal as missing.
The only patient free text reaching the packet today is
`VisitPrepRequest.reason_for_visit`.

## 6. Extension points for an external module

| Mechanism | Exists? | Evidence |
|---|---|---|
| Plugin loader / entry points | **No** | ✓ grep for `entry_points`, `importlib.metadata`, `plugin` in product code: none |
| Settings booleans (`core/config.py`) | Yes | `ocr_enabled`, `redaction_enabled`, `assistant_memory_enabled` pattern for a default-off `wearables_enabled` |
| Router mount list | Yes, static | `api/__init__.py:48-67` |
| File import contract | Yes, implicit | Lab CSV headers and FHIR Bundle subset; neither is versioned |
| Provider abstraction | Yes, LLM only | `core/llm/` — not for data sources |
