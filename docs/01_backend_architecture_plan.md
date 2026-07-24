# Backend Architecture Plan (Current Baseline + Future Hardening)

## Scope
Local-first backend services that power:
- Document ingestion (PDF/images, plus CSV/FHIR R4 Bundle structured imports — HC-M23), parsing, normalization, and verification workflow
- Trend/stat calculations (deterministic code, not the LLM)
- Grounded assistant (local RAG) with citation enforcement, including bounded read-only agent tools for record-navigation questions (HC-M24)
- Export pipelines (clinician-ready summary, CSV/JSON, FHIR R4 Bundle — HC-M22)
- Local audit logs and safety rails

Constraints (from PRD): offline-by-default; conservative outputs; provenance required for extracted fields and retrieved context; encryption at rest for DB, vector index, and stored documents.

Status note (2026-05-15):
- Loopback HTTP (`127.0.0.1`) + JWT Bearer auth is the current implementation, not a future proposal.
- The Windows developer launcher resolves the next free backend/frontend ports when defaults are unavailable and syncs `src/frontend/.env.local` for the Vite proxy.
- [`docs/api/endpoints.md`](api/endpoints.md) is the source of truth for the live mounted API surface.
- Sections labeled "Future hardening" describe optional follow-on improvements.

---

## Process topology (Windows desktop)

### Current implementation (as of 2026-05-15)
- Backend runs as a local FastAPI server on `127.0.0.1`; default port is `8000`, and the Windows dev launcher can select the next free port.
- Frontend is a Vite/React app that talks to the backend over same-origin `/api/v1` in development through the Vite proxy, or over loopback HTTP in packaged/deployed modes.
- Auth uses JWT Bearer tokens (HS256) with per-profile vault unlock for PHI access.

### Option A (recommended): sidecar service + local IPC
- Desktop UI (Tauri/Electron) launches a packaged local backend process.
- UI ↔ backend communication:
  - Loopback HTTP on `127.0.0.1` with JWT Bearer tokens (current baseline), or
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
- Type detection (lab PDF vs scan vs image vs CSV lab export vs FHIR R4 Bundle — HC-M23; CSV/FHIR skip OCR/extraction and are parsed by a dedicated structured-import pipeline, always landing unverified)

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
- bounded, read-only agent tools (`query_care_tasks`, `query_medication_changes`, `query_timeline` — HC-M24) answer record-navigation questions with cited, non-speculative summaries and a deterministic no-LLM fallback for the same intents

### 7) `export`
- Clinician-ready summary (1–2 pages) from verified observations + citations
- CSV/JSON export of normalized observations
- Chart export images + CSV
- FHIR R4 `Bundle` export (HC-M22) — verified-only, strict-redacted, confirmation-gated

### 8) `audit`
- Append-only event log:
  - import, verify edits, exports, model configuration changes
- MVP: append-only table in encrypted DB
- MVP+: hash-chained records for tamper-evidence

---

## API surface (local-only)

The live mounted route inventory is maintained in [`docs/api/endpoints.md`](api/endpoints.md). Keep endpoint-level details there so this architecture document remains focused on process boundaries, module responsibilities, and hardening policy.

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
- Packaging comms hardening beyond current loopback HTTP + JWT baseline
- OCR engine selection (Phase 1)
- Curated reference corpus licensing constraints
- External runner support policy (if any)
