**Product Requirements Document (PRD)\
Local-First Medical Results Companion**

*Version 0.1 • December 28, 2025 • Windows (primary)*

# **1. Executive summary**
Local-first application for patients to import medical documents, extract structured information with user verification, visualize trends, and generate grounded explanations and clinician-ready summaries. Core operation is offline. Optional online model usage is opt-in with explicit consent and a configurable redaction pipeline.
# **2. Background and problem**
User pain:

- Frequent labs and other tests create a fragmented, jargon-heavy record.
- Understanding what changed across time is difficult without tooling.
- Health anxiety increases the cost of uncertainty and ambiguity.

Constraints:

- Must run locally on Windows with a local database and local model options.
- Must prevent confidential patient data from leaving the machine by default.
- Must be conservative and prefer refusal over speculation.
# **3. Goals, non-goals, and principles**
Goals (MVP-aligned):

- Import PDFs and images (PNG, screenshots, scanned PDFs) into a local project folder.
- Extract and normalize key fields with a human verification step.
- Charts and visualizations for longitudinal trends and reference ranges; highlight deltas across time.
- Doctor-ready summary export and user-prompted question lists.
- Local term lookup and test-intent explanations via grounded retrieval (RAG) with citations.

Non-goals:

- Diagnosis, treatment recommendations, medication dosing, or emergency triage.
- Replacing clinician judgment or providing individualized medical advice.

Principles:

- Local-first and privacy-first by default.
- Grounded outputs: every claim cites user documents and/or curated references.
- Conservative behavior: prefer ‘insufficient information’ over inference.
- Explainability: show provenance for extracted fields and retrieved context.
# **4. Target users and personas**
Primary persona: Patient with frequent testing who needs clarity, trends, and trustworthy provenance.

Secondary persona (future): Authorized family member / caregiver via separate local profile vault.
# **5. Scope and roadmap**
Roadmap expands slowly: start with common labs and offline operation; add OCR for scans; then expand to broader documents and a persistent local assistant.

|Phase|Primary scope|Key deliverables|Notes|
| :- | :- | :- | :- |
|0 (MVP)|Labs: common panels from text-based PDFs|Import → parse → verify → trends; grounded explanations; doctor summary; question list|Offline only; no OCR required|
|1|OCR + images (PNG, screenshots, scanned PDFs)|OCR pipeline; bounding-box citations; stronger verification UX|All OCR-derived numerics require verification|
|2|Imaging reports + pathology + visit notes|Report sectioning; conservative summarization with citations; timeline integration|No interpretation beyond summarization|
|3|Persistent local assistant memory + glossary|User-controlled memory store; term library; per-user preferences|Memory is local and reviewable|
|4 (optional)|Opt-in online model usage|Consent + redaction + endpoint allowlist; send-text diff preview|Legal review; opt-in only|

# **6. MVP definition**
MVP document types:

- Text-based lab PDFs from portals (most common starting point).
- Manual entry supported for any missing values.

MVP lab coverage (initial allowlist, expandable):

- CBC, CMP/BMP, lipid panel
- HbA1c, thyroid panel (TSH, Free T4)
- Iron studies (ferritin, iron, TIBC), B12/folate, vitamin D
- Inflammation markers (CRP, ESR) when present
- Urinalysis when in a structured table
# **7. Core user journeys (MVP)**
**Import and verify:** Import a lab PDF. System extracts rows. User confirms or edits.

**Trends and deltas:** View per-analyte time series with reference range and delta summaries.

**Grounded explanation:** Select an analyte and request explanation with citations to report fields and references.

**Doctor-ready output:** Export a concise summary with key abnormalities, trends, and exact values/dates.

**Questions to ask:** Generate discussion prompts for a clinician visit, user-initiated only.
# **8. Functional requirements**
## **8.1 Ingestion**
- Local import from a chosen directory; copy or link files into a managed project folder.
- Supported inputs: Phase 0 text-based PDF; Phase 1 adds PNG/screenshot/scanned PDF via OCR.
- Metadata capture: source, document type, collection date(s), clinician/department (if present).
- Deduplication using content hash + date heuristics.
## **8.2 Parsing and normalization**
- Extract: test name, value, unit, reference range, abnormal flag, specimen type, collection timestamp, and report-level notes.
- Synonym mapping for common analytes; store both raw and canonical names.
- Unit handling: preserve source units; conversions only when explicit and reversible.
- Confidence scoring per field; route low-confidence fields to verification.
## **8.3 Verification and correction UX**
- Review screen showing extracted rows alongside the source snippet (page + text span; Phase 1 adds bounding boxes).
- Inline edits with validation for numeric, unit, and date formats.
- Fallback manual entry when extraction fails; mark entries as user-entered and keep provenance.
- Versioning: maintain original extraction and subsequent user corrections.
## **8.4 Visualization and insights**
- Time-series chart per analyte with reference range shading and abnormal markers.
- Change summaries: last value vs prior value; rolling average; ‘new high/low’ events.
- Panel views (CBC, CMP, lipids) and filters (abnormal only, timeframe).
- Chart export for clinician visits.
## **8.5 Grounded assistant (local RAG)**
- Chat interface tied to selected profile and selected context (analyte, panel, time window).
- Retrieval over user documents and a curated medical reference corpus stored locally.
- Hard requirement: citations for any factual statement about the user’s results or documents.
- Explicit separation of ‘what the report shows’ vs ‘general information’.
- Test intent explanations: what the test is typically ordered for; what it helps evaluate at a high level.
## **8.6 Outputs**
- Doctor-ready summary (1–2 pages): key values, trends, dates, and short narrative.
- Question list: discussion prompts only, user-initiated.
- Export normalized data as CSV/JSON.
# **9. Non-functional requirements**
## **9.1 Privacy and security**
- Default offline operation; no external network calls required for MVP.
- Encrypt at rest: database, vector index, and stored documents.
- Per-profile encryption keys protected via Windows DPAPI or credential manager.
- Profile lock: require unlock on app start; auto-lock on idle (configurable).
- Local audit log for import/export events.
## **9.2 Reliability and performance**
- Deterministic parsing where possible; stable results across runs.
- Graceful degradation for OCR and low-confidence extraction (verify/manual entry).
- Fast search and retrieval across multi-year history.
## **9.3 Safety constraints**
- No diagnosis or treatment advice; provide general education only.
- Critical-value handling relies on report flags; highlight and advise contacting ordering clinician without escalation beyond the report.
- Neutral phrasing; emphasize uncertainty; no catastrophic language.
# **10. Proposed architecture (Windows)**
Suggested modular architecture (maintainable and scalable):

- Desktop UI: Tauri (Rust + web UI) for smaller footprint, or Electron for faster iteration.
- Backend: Python (FastAPI) for parsing/OCR/RAG services, packaged locally.
- Local database: SQLite + SQLCipher for encrypted per-profile vaults.
- Vector index: FAISS or sqlite-vss; store encrypted.
- Local inference: Ollama or llama.cpp for LLM; local embeddings model (e5-small/bge-small).
## **10.1 Document pipeline**
- PDF text extraction: pdfplumber; vendor-specific format plugins as needed.
- OCR (Phase 1): render pages → OCR → layout reconstruction; persist bounding boxes for citations.
- Chunking: split by page/section/panel for retrieval.
- Provenance: store doc\_id + page + span/box for every extracted field and retrieved chunk.
## **10.2 Assistant pipeline (RAG)**
- Retrieve user observations and relevant report snippets; compute trend stats in code, not in the model.
- Retrieve reference chunks from local corpus.
- Compose a strict prompt template with required citation tokens.
- Validator rejects responses without citations or with claims not supported by retrieved context.
# **11. Data model (initial)**
Minimum tables (conceptual):

- profiles(profile\_id, display\_name, created\_at, encryption\_key\_id)
- documents(doc\_id, profile\_id, path\_hash, type, source, imported\_at, metadata\_json)
- observations(obs\_id, profile\_id, doc\_id, analyte\_canonical, analyte\_raw, value, unit, ref\_low, ref\_high, flag, collected\_at, provenance\_json, user\_verified\_bool)
- chunks(chunk\_id, profile\_id, doc\_id, page, text, provenance\_json)
- embeddings(chunk\_id, vector, model\_id)
- mappings(analyte\_canonical, synonym, source)
# **12. MVP requirements table**

|ID|Requirement|Priority|Acceptance criteria|Phase|
| :- | :- | :- | :- | :- |
|MVP-01|Import text-based lab PDFs into a local profile|P0|PDF appears in documents list; content hash recorded; no network calls|0|
|MVP-02|Extract analyte rows with provenance|P0|>=90% correct on a seeded set; each row links to source snippet|0|
|MVP-03|User verification UI for extracted values|P0|User can edit fields; edits tracked; verified state stored|0|
|MVP-04|Per-analyte trend chart with reference range|P0|Chart renders over time; reference range visible; filters work|0|
|MVP-05|Doctor-ready summary export|P0|Generates PDF with key values/dates and trend highlights; includes citations|0|
|MVP-06|Grounded explanation with citations|P0|Assistant answers only from retrieved context; refuses if ungrounded|0|
|MVP-07|Local encryption for DB and document vault|P0|Data unreadable without key; profile locks on app close|0|
|P1-01|OCR for scanned PDFs and images|P0|User can import scans; OCR text stored with bounding boxes; verify step works|1|
|P2-01|Imaging report ingestion and sectioned summarization|P1|Imports radiology PDFs; summarizes findings with citations; avoids interpretation|2|
|P3-01|Persistent local memory store (reviewable)|P1|User can view/edit/delete memory items; memory used only when enabled|3|
# **13. Risks and mitigations**
- Risk: Parsing variability across lab vendors and portals

Mitigation: Start with common formats; implement format plugins; require verification when confidence is low.

- Risk: OCR errors leading to incorrect values

Mitigation: Confidence scoring; verification mandatory for OCR-derived numerics; highlight uncertain digits.

- Risk: Model hallucinations

Mitigation: Citation-required responses; response validator; conservative refusal policy.

- Risk: User anxiety amplification

Mitigation: Neutral language; uncertainty labels; clinician-discussion framing; configurable safety mode.

- Risk: Security of local embeddings and caches

Mitigation: Encrypt indexes; minimize caching; explicit retention controls; per-profile isolation.
# **14. Inputs needed to finalize MVP spec**
- Hardware baseline for local inference: RAM, CPU class, GPU availability.
- Preferred packaging approach: single installer vs portable app folder.
- Representative lab PDFs for evaluation: 20–50 across sources.
- Curated reference corpus shortlist and licensing constraints.
- Critical-value handling policy: rely solely on lab report flags vs additional thresholds.
