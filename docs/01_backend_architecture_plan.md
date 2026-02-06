# Backend Architecture Plan (Draft v0 — pending PM approval)

## Scope
Local-first backend services that power:
- Document ingestion (PDF/images), parsing, normalization, and verification workflow
- Trend/stat calculations (deterministic code, not the LLM)
- Grounded assistant (local RAG) with citation enforcement
- Export pipelines (clinician-ready summary, CSV/JSON)
- Local audit logs and safety rails

Constraints (from PRD): offline-by-default; conservative outputs; provenance required for extracted fields and retrieved context; encryption at rest for DB, vector index, and stored documents.

---

## Process topology (Windows desktop)

### Current implementation (as of 2026-02-05)
- Backend runs as a local FastAPI server on `127.0.0.1` (fixed port by default).
- Frontend is a Vite/React app that talks to the backend over loopback HTTP.
- Auth uses JWT Bearer tokens (HS256) with per-profile vault unlock for PHI access.

### Option A (recommended): sidecar service + local IPC
- Desktop UI (Tauri/Electron) launches a packaged local backend process.
- UI ↔ backend communication:
  - Loopback HTTP on `127.0.0.1` with JWT Bearer tokens (current), or
  - (Future hardening) per-launch bearer token and random ephemeral port.

Rules:
- Backend must never bind to `0.0.0.0`.
- Backend must reject requests lacking token.
- Backend runs with least privileges.
- No outbound network calls in MVP.

### Option B: embedded backend (Rust-only)
- Move parsing/RAG to Rust crates.
- Higher engineering cost; revisit post‑MVP.

---

## Internal modules (suggested: Python + FastAPI)

### 1) `ingest`
Responsibilities:
- Import/copy/link source files into per-profile vault folder
- Content hashing, dedup heuristics, metadata capture
- Type detection (lab PDF vs scan vs image)

Outputs:
- `document_id`, `path_hash`, `doc_type`, `imported_at`, `metadata_json`

### 2) `extract`
Phase 0: text-based PDFs
- Layout-aware PDF text extraction
- Vendor/portal plugins (format adapters)
- Persist per-row provenance (page + span)

Phase 1: OCR
- Page rendering → OCR → layout reconstruction
- Store bounding boxes for citations/provenance

### 3) `normalize`
- Canonical analyte mapping and synonym handling
- Unit preservation (conversion only when explicit and reversible)
- Confidence scoring per field

### 4) `verify`
- Serve verification payloads for UI:
  - extracted rows + provenance pointers (page + span; later bounding boxes)
  - validation rules (numeric/unit/date)
- Apply user edits, version changes, record verified status

### 5) `analytics`
Deterministic computations:
- deltas, rolling averages, new high/low markers, abnormal event markers
- chart-ready series + human-readable summaries (for alt text)

### 6) `rag_assistant`
Retrieval over:
- user document chunks (per-profile)
- curated local reference corpus

Composition rules:
- strict prompt template that separates:
  - “What the report shows” (must cite user documents)
  - “General information” (cite local references)
  - “Uncertainties / missing context”
- response validator rejects output if:
  - citations are missing where required
  - “report facts” are not supported by retrieved user chunks
  - model attempts diagnosis/treatment advice

### 7) `export`
- Clinician-ready summary (1–2 pages) from verified observations + citations
- CSV/JSON export of normalized observations
- Chart export images + CSV

### 8) `audit`
- Append-only event log:
  - import, verify edits, exports, model configuration changes
- MVP: append-only table in encrypted DB
- MVP+: hash-chained records for tamper-evidence

---

## API surface (local-only)

### Documents
- `POST /documents/import`
- `GET /documents`
- `GET /documents/{id}/pages` (for provenance viewing)

### Observations
- `GET /observations?analyte=&from=&to=&abnormal=`
- `POST /observations/{id}/verify` (apply edit + verified flag)
- `GET /panels/{panel_id}` (CBC/CMP/etc aggregation)

### Assistant
- `POST /assistant/chat`
  - Input: profile, selected analytes/panels, timeframe, user question, “include references” toggle
  - Output: answer segments + citations + “insufficient info” reasons

### Export
- `POST /export/doctor-summary`
- `POST /export/csv`
- `POST /export/json`

### Settings / Safety
- `GET /settings`
- `POST /settings` (offline-only, model selection, memory toggle, idle lock timer)

---

## Determinism and reproducibility
- Parsing outputs must be stable across runs for the same document (seeded config).
- Maintain a golden regression set (20–50 PDFs) with snapshot tests.
- Record parser version + model IDs in metadata to reproduce outputs.

---

## Packaging (Windows)
- Package backend as a single executable (PyInstaller/Nuitka) invoked by the desktop shell.
- Model runner integration options:
  - Embedded `llama.cpp` library (lowest friction; no server)
  - Optional external runner integration (Ollama / LM Studio) with hard requirements:
    - loopback-only binding
    - token auth between app and runner
    - LAN exposure disabled by default

---

## Open decisions (PM approval)
- Tauri vs Electron choice (iteration speed vs footprint)
- Backend comms: Tauri invoke vs loopback HTTP
- OCR engine selection (Phase 1)
- Curated reference corpus licensing constraints
- External runner support policy (if any)
