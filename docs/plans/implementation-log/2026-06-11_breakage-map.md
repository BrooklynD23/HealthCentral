# HealthCentral Breakage Map — 2026-06-11

> Historical Reference: this plan predates later implementation work and contains completed items.
> Use `docs/features/TASK_LIST.md` for active remaining tasks.

Branch: `fix/agent-overhaul`  
Diagnosed by: automated agent (Claude Sonnet 4.6)  
Python runtime used: system Python 3.10.12 (venv at `.wsl-pytest-venv` is Python 3.12 but its `lib/` directory is a dead symlink on the 9p mount — all tests were run with `python3` directly)

---

## 1. Test Environment

### How to run backend tests (reproducible commands)

```bash
# From repo root in WSL (not Windows-native Python)
cd src/backend

# Install missing deps into system Python 3.10 (one-time):
python3 -m pip install --break-system-packages \
  pytest pytest-asyncio pytest-cov \
  fastapi httpx pydantic pydantic-settings \
  sqlalchemy aiosqlite alembic \
  python-multipart aiofiles python-dateutil \
  python-jose[cryptography] apscheduler \
  plyer weasyprint pytesseract pdf2image \
  huggingface-hub py-cpuinfo uvicorn[standard] \
  faiss-cpu sentence-transformers

# Run the passing test subset (excludes UTC-broken API test files):
python3 -m pytest tests/ \
  --ignore=tests/test_documents_api.py \
  --ignore=tests/test_document_category_api.py \
  --ignore=tests/test_gamification_api.py \
  --ignore=tests/test_gamification_models.py \
  --ignore=tests/test_medications_dose_logging.py \
  --ignore=tests/test_memory_crud.py \
  --ignore=tests/test_model_settings_api.py \
  --ignore=tests/test_voice_settings_api.py \
  --ignore=tests/test_observation_panel_snapshots.py \
  --ignore=tests/test_ocr_bbox.py \
  --ignore=tests/test_profile_migrations_sqlcipher_fallback.py \
  -p no:cacheprovider --tb=short -q

# Full collection attempt (shows all errors):
python3 -m pytest tests/ -p no:cacheprovider --tb=no -q \
  --ignore=tests/test_profile_migrations_sqlcipher_fallback.py
```

### What works

- system `python3` (3.10.12) with `--break-system-packages` deps
- `conftest.py` sets `TEST_MODE=1` and `DATABASE_ENCRYPTION_REQUIRED=false`, disabling SQLCipher for tests
- 373 tests pass across: config validation, redaction, badge evaluator, streak engine, extraction pipeline,
  extract_imaging/pathology/visit_notes, rag_pipeline (all except one assertion), document_classifier,
  phase3/4 safety/notifications, security middleware, monitoring, backup, hardware detection,
  memory integration, voice permissions

### Known environment limits

- `.wsl-pytest-venv` Python 3.12 venv has a broken `lib/` (symlink, not directory) on the 9p/WSL mount — unusable. Use system `python3` (3.10).
- `llama-cpp-python`, `sqlcipher3-binary` — not installable without native build toolchain; tests requiring them are skipped or mocked.
- `faiss-cpu` and `sentence-transformers` installed successfully; RAG embedding tests work.
- Frontend `node_modules/.bin/` symlinks are absent on the 9p mount (Windows checkout); TypeScript lib `.d.ts` files also missing. TypeScript type-check was not runnable — run `npx tsc --noEmit` from Windows PowerShell instead.

---

## 2. Backend Test Failures

### Collection errors — 10 files, all same root cause

All 10 files fail to import because `api/__init__.py` imports `api.medications`, which imports
`core.time`, which does `from datetime import UTC` — a Python 3.11+ symbol.

| File | Error |
|------|-------|
| `tests/test_documents_api.py` | `ImportError: cannot import name 'UTC' from 'datetime'` |
| `tests/test_document_category_api.py` | same |
| `tests/test_gamification_api.py` | same |
| `tests/test_gamification_models.py` | same |
| `tests/test_medications_dose_logging.py` | same |
| `tests/test_memory_crud.py` | same |
| `tests/test_model_settings_api.py` | same |
| `tests/test_voice_settings_api.py` | same |
| `tests/test_observation_panel_snapshots.py` | same |
| `tests/test_ocr_bbox.py` | same |

**Root cause:** `src/backend/core/time.py:3` — `from datetime import UTC, datetime`.
`datetime.UTC` was added in Python 3.11. The project targets 3.11+ but CI/WSL environment has 3.10.
Fix: replace with `import datetime; datetime.timezone.utc` or guard with `try/except ImportError`.

### Runtime failures — 12 tests

#### `tests/test_document_import_classification.py` — 11 failures

All failures in `TestClassifyAndExtractEntities`, `TestScannedAndImageClassification`,
`TestNonFatalFailures` classes. Each test calls `unittest.mock.patch("api.documents._get_document_text", ...)`
which triggers lazy import of `api.documents` → `api/__init__.py` → `api.medications` → `core.time` →
`UTC` ImportError.
**Root cause: same Python 3.10 `UTC` issue, triggered lazily through `patch()` target resolution.**
The 5 passing tests in this file import only from `modules.*` and succeed.

#### `tests/test_rag_pipeline.py::TestEmbeddingsPipeline::test_api_rag_index_002b_similar_text_yields_similar_embeddings`

```
assert 0.6316202918382531 > 0.7
```

**Root cause:** No sentence-transformer model is downloaded; the fallback embedder produces vectors
without semantic meaning. Cosine similarity between "glucose levels" and "blood sugar measurement"
is 0.63, below the 0.7 threshold. Environment issue, not a product logic bug — but reveals that
the embedder degrades silently rather than raising `ModelUnavailableError`.

---

## 3. Frontend Errors

### TypeScript type-check

Could not complete `tsc --noEmit` in WSL environment — `node_modules/typescript/lib/*.d.ts` files
are absent (Windows `npm install` creates files invisible over 9p/WSL mount due to symlink handling).
TypeScript binary itself is present but immediately errors on missing lib files.

**Action:** Run `npx tsc --noEmit` from Windows PowerShell (`cd src/frontend; npx tsc --noEmit`).

### Static analysis findings (manual review)

1. **`services/memory.ts` is not exported from `services/index.ts`.**
   `MemoryManager.tsx` imports directly from `@/services/memory` (works). Any future component
   using `import { useMemoryItems } from '@/services'` will get a compile-time TS error.

2. **`useObservations` race condition in `TrendsDashboard.tsx`.**
   `profileId` from `useAuthStore` may be `null` before localStorage hydration. The query is
   `enabled: !!filters.profile_id` — so it stays disabled until hydration completes. On slow
   machines or first load, this shows a flash of "No data available" before data loads.
   Not a hard error; a loading skeleton or `isLoading` guard would improve UX.

3. **No schema mismatches detected** between `services/types.ts` frontend types and backend
   Pydantic models. `Observation`, `TrendData`, `TrendPoint`, `Panel`, `ChatRequest`,
   `ChatResponse`, `MemoryItem` all match field-for-field.

---

## 4. Root-Cause Analysis Per Symptom

---

### Symptom 1: Document import → parsing → parsed data not displaying in TrendsDashboard

**Pipeline:** `POST /api/v1/documents/import` → `_run_extraction_pipeline()` → observations written
to profile DB → `GET /api/v1/observations/` → `useObservations` → `TrendsDashboard`

#### Finding A — `collected_at` is frequently NULL (primary cause of empty charts)

**Files:**
- `src/backend/modules/extract.py:113–128` — `_extract_dates()`
- `src/backend/api/documents.py:410–423` — `_run_extraction_pipeline()`

`_extract_dates` uses three patterns: `MM/DD/YYYY`, `MM-DD-YYYY`, and `Mon DD, YYYY`. It does NOT
match ISO 8601 (`2024-01-15`), fully spelled-out months (`January 15, 2024`), or European formats.
Many real lab PDFs (Quest, LabCorp, etc.) use ISO or spelled-out dates.

When no dates match, `extracted_obs.collected_at` stays `None` for every observation.
`_parse_date_string(None)` returns `None`, and `Observation.collected_at` is stored as NULL.

**Effect:** `GET /observations/trends/{analyte}` at `api/observations.py:340–360` filters:
```python
query = select(Observation).where(
    Observation.value.isnot(None),
)
```
Then in the data-point building loop at line 349:
```python
if obs.collected_at and obs.value is not None:
    data_points.append(...)
```
Observations with `collected_at = NULL` are silently excluded. The chart shows
"No trend data available" even though observations exist in the DB.

#### Finding B — `needs_verification=True` forced by low confidence (cosmetic but noisy)

**File:** `src/backend/api/documents.py:493–505` — `_compute_needs_verification()`

Text extraction base confidence is 0.5; a value+unit+range observation reaches ~0.9 max.
The threshold is 0.8. Most real-world observations (value present, unit absent or range absent)
score 0.65–0.75, so `needs_verification` is always `True`. TrendsDashboard always shows the
"X unverified values" badge. Not a data loss bug, but drives user confusion.

#### Finding C — Embedding model absent → silent degradation

**File:** `src/backend/modules/embeddings.py` (inferred)

When no sentence-transformer model is downloaded, the embedder falls back to non-semantic vectors.
`_search_vectors_async` (rag.py) returns near-random cosine scores. RAG chunk retrieval is broken.
This doesn't affect the raw TrendsDashboard (uses SQL not vectors) but breaks the full
ingest→explain pipeline used in ExplainAssistant.

---

### Symptom 2: Assistant cannot talk about biomarkers

**Pipeline:** `POST /api/v1/assistant/chat` → `RAGModule.query()` → `_get_reference_chunks()`
→ `knowledge.get_biomarker_knowledge(analyte, master_db)` → `SELECT FROM biomarker_knowledge`

#### Finding A — Knowledge base table is never seeded at startup (primary cause)

**Files:**
- `src/backend/scripts/seed_knowledge_base.py:16` — documents: `python -m scripts.seed_knowledge_base`
- `src/backend/main.py:27–40` — `lifespan()` calls only `init_database()` and `run_master_migrations_async()`; no seed step
- `src/backend/migrations/master/versions/001_initial_schema.py` — creates tables, inserts zero rows

The `biomarker_knowledge` table is created by migration but **empty on a fresh install** unless the
operator manually runs the seed script. There is no automatic seeding at startup or in migrations.

When the table is empty:
- `get_biomarker_knowledge()` returns `None` for every analyte
- `_get_reference_chunks()` builds zero ref chunks
- `retrieve_context()` returns `[]`
- `RAGModule.query()` returns `insufficient_context=True` with "No relevant documents found"

Even the no-LLM fallback path (`_build_knowledge_fallback` at `api/assistant.py:218–260`) calls
the same `knowledge.get_biomarker_knowledge()` and gets `None`, producing only the
"Note: This response is based on the knowledge base only" uncertainty message.

The seed script covers 27 canonical analytes (lipid, CBC, CMP, thyroid panels — confirmed by
`grep -c "analyte_canonical" scripts/seed_knowledge_base.py`).

#### Finding B — Double failure: LLM absent + KB empty

When no GGUF model and no external API is configured, `generate_response()` raises
`ModelUnavailableError`. `api/assistant.py:chat()` catches it and calls `_build_knowledge_fallback()`.
But `_build_knowledge_fallback` depends on the seeded KB (Finding A). **Both paths fail silently.**
The user receives only: *"I don't have specific information about your question in my knowledge base."*

---

### Symptom 3: RAG does not persist patient/user history (no memory)

#### Sub-problem A — Memory CRUD works; injection is gated off by config default (primary cause)

**Files:**
- `src/backend/core/config.py:112` — `assistant_memory_enabled: bool = False`
- `src/backend/modules/rag.py:995–998`:

```python
memory_section = ""
if use_memory:
    if settings.assistant_memory_enabled:   # <-- GATE: False by default
        memory_section = await self._retrieve_memory_context(profile_id, profile_db)
```

The frontend sends `use_memory: true` (`src/frontend/src/pages/ExplainAssistant.tsx:132`).
The backend receives it, but `settings.assistant_memory_enabled` is `False`, so the gate is never
entered. Memory items are stored and displayed in `SettingsPage` via `MemoryManager`, but they are
**never injected into the RAG prompt**.

There is no UI toggle for this setting. Enabling requires `ASSISTANT_MEMORY_ENABLED=true` in `.env`.

#### Sub-problem B — Conversation history is session-only; no cross-session persistence

Multi-turn conversation history is built from React state in `ExplainAssistant.tsx` and sent as
`history: ChatHistoryMessage[]` per request. The backend processes it in `rag.py:compose_prompt()`.
It is **never written to the database**. No `ConversationHistory` model, no DB table, no migration
for chat sessions. Each browser refresh starts blank.

The `memory_items` feature was designed to fill this gap for preferences/context, but Sub-problem A
prevents it from being used.

#### Sub-problem C — `memory.ts` not re-exported from services barrel

**File:** `src/frontend/src/services/index.ts` — missing exports:
`useMemoryItems`, `useCreateMemoryItem`, `useUpdateMemoryItem`, `useDeleteMemoryItem`.
Low-severity today (MemoryManager imports directly), will cause TS errors if anything else
tries to use the barrel.

---

## 5. Hazards — Things Future Fixers Must Not Break

1. **`modules/interpret_safety.py:44–66` — PROHIBITED_PATTERNS**
   Regex guards preventing diagnoses, dosing recommendations, certainty claims. Also compiled in
   `rag.py:__init__` (`_compiled_prohibited_patterns`) and checked in `validate_response()`.
   **Never remove, weaken, or bypass.** All new LLM provider integrations must route output through
   `validate_response()`.

2. **`modules/redaction.py` + `core/config.py:redaction_enabled`**
   PHI/PII redaction runs before any external API call. Production raises `RuntimeError` if
   `redaction_enabled=False` or `redaction_policy_level != "strict"`. New external AI provider
   integrations must route prompts through redaction. `external_api_redaction_break_glass` flag
   exists but must stay `False` in production.

3. **`security/audit_middleware.py` + `core/audit.py` — Audit logging**
   All document/observation events write to `audit_logs` in master DB. New routes touching
   documents or observations must call `log_document_event()` / `log_observation_event()`.

4. **Per-profile encrypted DB isolation** (`core/profile_database.py`, `core/auth.py:ProfileDbSession`)
   Per-profile models (`Observation`, `Document`, `Chunk`, `Embedding`, `MemoryItem`) live in
   separate SQLCipher databases. Routes must use `ProfileDbSession`, not master `get_db()`.
   Mixing sessions fails silently or raises FK violations.

5. **`core/token_revocation.py` — JWT revocation**
   `jwt_revocation_enabled=True` by default. Logout invalidates tokens server-side. New auth flows
   must respect the revocation check.

6. **`modules/interpret_safety.py:REQUIRED_DISCLAIMER_KEYWORDS`**
   Interpretations must include "consult healthcare provider" disclaimer. Template and LLM responses
   are both validated. Do not remove when adding new interpretation backends.

7. **`security/input_validator.py:InputValidationMiddleware`**
   10 MB body limit. New large-upload endpoints must update `settings.max_request_body_bytes`
   deliberately, not disable the middleware.

---

## 6. Summary Table

| # | Symptom | Primary File(s) | Root Cause | Severity |
|---|---------|-----------------|------------|----------|
| 1a | Parsed data not in charts | `modules/extract.py:113–128`, `api/observations.py:349` | `collected_at` NULL: date regex misses ISO 8601 / spelled-out months; trend endpoint silently skips NULL-date observations | High |
| 1b | Always `needs_verification` | `api/documents.py:493–505` | Confidence threshold 0.8 is above typical text-extraction scores (0.65–0.75) | Medium |
| 1c | RAG chunk retrieval broken | `modules/embeddings.py` | No embedding model downloaded → non-semantic fallback vectors | Medium |
| 2a | Assistant knows nothing | `scripts/seed_knowledge_base.py`, `main.py:lifespan` | `biomarker_knowledge` table never seeded at startup; empty DB | High |
| 2b | KB fallback also empty | `api/assistant.py:228–260` | `_build_knowledge_fallback` queries same empty KB | Medium (consequence of 2a) |
| 3a | Memory not injected into RAG | `core/config.py:112`, `modules/rag.py:995–998` | `assistant_memory_enabled=False` default; no UI toggle | High |
| 3b | No cross-session chat history | (no model/migration exists) | Conversation history in React state only; no DB persistence | Medium |
| 3c | Memory barrel not exported | `services/index.ts` | `memory.ts` hooks missing from barrel | Low |
| BE1 | 10 test files uncollectable | `core/time.py:3` | `datetime.UTC` requires Python 3.11+; system Python is 3.10 | High (blocks CI) |
| BE2 | RAG similarity test fails | `tests/test_rag_pipeline.py:270` | No embedding model; fallback vectors score 0.63 vs threshold 0.7 | Low (env only) |
