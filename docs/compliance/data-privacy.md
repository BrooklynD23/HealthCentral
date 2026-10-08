# Data Privacy

## Data Classification

### Tier 1: Protected Health Information (PHI)

Stored only in encrypted profile vaults (SQLCipher).

| Data Type | Storage | Encryption |
|-----------|---------|------------|
| Lab observations | Profile vault DB | AES-256 (SQLCipher) |
| Document content | Profile vault DB | AES-256 (SQLCipher) |
| Medications | Profile vault DB | AES-256 (SQLCipher) |
| AI interpretations | Profile vault DB | AES-256 (SQLCipher) |
| Dose records | Profile vault DB | AES-256 (SQLCipher) |
| Chat history | Profile vault DB | AES-256 (SQLCipher) |

### Tier 2: Profile Metadata

Stored in master database (not encrypted by default).

| Data Type | Storage | Notes |
|-----------|---------|-------|
| Profile name | Master DB | User-chosen display name |
| Profile ID | Master DB | UUID identifier |
| Creation date | Master DB | Timestamp |
| Vault path | Master DB | File path reference |

### Tier 3: Operational Data

| Data Type | Storage | Retention |
|-----------|---------|-----------|
| Audit logs | Master DB (not encrypted). No log file is written | Indefinite |
| Request metrics | In-memory ring buffer | Session only (configurable size) |
| Security events | Request events from `SecurityAuditMiddleware`: application logger only (the process's stderr); no log file is written, and they are logged at INFO, below the default WARN level, so by default they are not emitted. Break-glass external calls: an audit row in the master DB (`security.external_api.break_glass`) | Request events: not retained by the app. Break-glass rows: as audit logs |
| Correlation IDs | Request-scoped | Not persisted |

## Encryption

### At Rest

| Component | Algorithm | Key Management |
|-----------|-----------|----------------|
| Profile vaults | AES-256-CBC (SQLCipher) | Password-derived key (PBKDF2) |
| Master database | Not encrypted | Contains no PHI |
| Backups | Same as source | SQLite backup API preserves encryption |
| Log files | Not encrypted | Contains event metadata, not PHI |

### In Transit

| Mode | Protection |
|------|------------|
| Local mode | Localhost binding only (127.0.0.1) — no network exposure |
| Server mode | HTTPS required (HSTS enforced), TLS 1.2+ |

## Data Retention

| Data Type | Default Retention | User Control |
|-----------|-------------------|--------------|
| Health data (PHI) | Indefinite | Delete via UI or API |
| Audit logs | Indefinite | Archival recommended |
| Backups | 30 days | Settings → Backup & restore, or `--retention-days`. `0` means never prune. Deleted with the profile. |
| Request metrics | In-memory (session) | Cleared on restart |
| AI model cache | Persistent | Manual cleanup via settings |

## Data Portability

Users can export their data at any time:

| Format | Endpoint | Content |
|--------|----------|---------|
| CSV | `GET /export/csv` | All observations |
| JSON | `GET /export/json` | All observations |
| Doctor Summary | `POST /export/doctor-summary` | Formatted clinical report |

**Redaction scope, owner decision D3 (2026-09-27).** Record:
`docs/capstone-report/owner-decisions-2026-09-27.md`.
- **CSV and JSON are deliberate exceptions to redaction.** They are the
  patient's own data export, so they stay full-fidelity, like backups.
- **The doctor summary must be redacted at the `strict` policy level,** because
  it goes to a third party. Status: owner-approved, **not yet implemented**.
  Today the summary and its text, HTML and PDF downloads are produced without
  redaction. Tracked as W-2 in
  `docs/capstone-report/implementation-program.md` (matrix PRIV-04).

## Reinforcement Learning Dataset Export

Users can opt-in to feedback collection on assistant chat responses (thumbs up/down, optional corrections). This feedback enables local RL dataset generation for future model fine-tuning:

| Property | Implementation |
|----------|----------------|
| Feedback collection | User rates responses via `POST /api/v1/feedback/turns/{turn_id}` with optional text corrections |
| Export endpoint | `POST /api/v1/feedback/export` (requires explicit `confirmed=true` — never automatic) |
| Export format | JSONL files: DPO pairs, SFT examples, GRPO reward data (written to local storage only) |
| PHI redaction | **Mandatory and non-configurable**: prompt/response text is passed through `modules/redaction.py` at the **strict** policy level before export (RL-REDACT-001, 2026-07-07). Strict covers SSNs, emails, phone numbers, context-prefixed names, DOB, street addresses, MRNs, and slash/dash numeric dates. It does not remove lab values, biomarker names, medication names, or ISO-8601 collection timestamps — a recorded deferral (they are the training signal); see `docs/features/TASK_LIST.md` RL-REDACT-001. |
| Local-first | No network calls; files written to local storage only |
| Audit logging | Feedback creation and export events captured as `feedback.*` audit log entries |

**Key safeguards:**
- Export requires explicit user confirmation (`confirmed=true` parameter); never silent or automatic
- Identifier redaction is applied before export; users should still review JSONL files before sharing because medical values and medication names may remain when not matched by the redaction rules
- Redaction policy is mandatory and not user-configurable for the export endpoint (see `modules/redaction.py`)
- Exported datasets are persistent local files under the configured export directory until manually deleted

#### Exported fields (exact)

| Field | Exported? | Notes |
|---|---|---|
| Redacted prompt snapshot | ✅ Yes | SSNs, emails, phone, name-context, DOB, addresses, MRNs, and slash/dash numeric dates stripped (`strict` policy — the export's mandatory level since RL-REDACT-001). Lab values, biomarker names, and ISO-8601 collection dates are **not** removed (recorded deferral: they are the training signal). |
| User rating (+1/−1) | ✅ Yes | |
| Correction text | ✅ Yes | Same redaction as prompt snapshot |
| Model name / provider | ✅ Yes | |
| Full unredacted observation text | ❌ Never | Only the prompt snapshot (which may reference observations) is exported |
| Original pre-redaction content | ❌ Never | Redaction is applied before any write; originals are not stored in export files |

**Confirmation gate:** `confirmed=true` must be present in the request body. Absent this flag the export endpoint returns HTTP 400.

**Output path:** `rl_exports/profile_<full-profile-uuid>/` — local disk only, no network write.

## Data Deletion

### Profile Deletion (PROF-DEL-001)

`DELETE /api/v1/profiles/{id}` — implemented 2026-07-27. Before this, every
sub-entity was deletable but the profile itself was not, which contradicted the
product's data-sovereignty premise.

**Gates.** The request requires all three:
1. the profile password, re-entered (a session token alone is not sufficient)
2. the exact confirmation phrase `DELETE MY HEALTH DATA`
3. `export_acknowledged` — the UI offers a data download first

**Order of operations**, chosen so that an interrupted deletion leaves a
recoverable state rather than a corrupt one:
1. Re-authenticate; rate-limited per client and profile.
2. Revoke the caller's session token and close the profile database, releasing
   file handles and clearing the in-memory encryption key.
3. **Delete the sealed key files first.** This is the crypto-erase commit
   point: without the sealed key the vault is unreadable even if the database
   file survives. If the key cannot be destroyed, the operation aborts before
   the master row is touched, so the user can retry.
4. Sweep the whole vault directory — database, WAL/SHM sidecars, and encrypted
   documents. Failures here are logged but do not abort: the data is already
   cryptographically erased, and a retry finishes the cleanup.
5. Sweep the profile's backup directory (`<app_data>/backups/<profile_id>`) on
   the same log-and-continue terms. Each backup holds its own copy of the sealed
   key, so leaving them behind would leave the record restorable after a
   "permanent" deletion.
6. In one master transaction: purge the audit rows, delete the profile row,
   delete the `backup_schedules` row, write the tombstone. The schedule row is
   deleted explicitly rather than by FK cascade — `PRAGMA foreign_keys` is not
   enabled, so the `ondelete="CASCADE"` on the model is inert on SQLite.

**Audit-row retention — owner decision, 2026-07-27.** The profile's audit rows
are **purged**, and a single **anonymized** `profile.delete` tombstone is
retained recording that a deletion occurred and how many rows were purged. The
tombstone carries no profile id, no display name and no hash of either — a
random id would still be a linkage handle back to the person.

The alternative considered and rejected was retaining the full audit trail for
HIPAA-style accountability. It was rejected because it leaves the unencrypted
master database holding a trace of a person who asked to be erased, which
contradicts the guarantee this feature exists to provide. This purge is also
the **only** mechanism that removes audit rows written before AUDIT-PHI-001's
minimization landed (see `hipaa-controls.md` — legacy rows are otherwise left
untouched).

**What is claimed, and what is not.** The claim is *file deletion plus key
destruction*. We do not claim the bytes are overwritten: SSD wear-levelling
makes that guarantee false, and the UI copy says exactly this.

**App-created backups are deleted with the profile; downloaded archives are
not.** A backup contains the sealed key and remains readable with the password
— which is exactly what makes it restorable, and exactly why one left on disk
would defeat the erase. So the backups the app manages, under
`<app_data>/backups/<profile_id>`, are swept as part of deletion (step 5 above).
An archive the user downloaded has left the app's reach entirely and cannot be
reclaimed; it should be kept as carefully as the device itself, and destroyed by
hand if the intent is a complete erase. The delete flow offers "back up and
download" as its first step precisely so this is a deliberate choice rather than
a leftover.

**Backup archives are deliberately not redacted** (BKUP-UX-001). A backup is
the user's own full-fidelity record, going to their own machine, and a redacted
backup cannot be restored. The CSV and JSON exports are deliberately not
redacted on the same grounds: they are the patient's own data export (owner
decision D3, 2026-09-27; see Data Portability). These three are the
export-shaped paths that are intentionally unredacted. The exports built for a
third party pass through `modules/redaction.py` at `strict`: the visit-prep
packet, the pinboard export, the FHIR bundle and the RL dataset. Under D3 the
doctor summary must join them; that is owner-approved but not yet implemented
(W-2).

### Document Deletion

When a document is deleted:
1. Document record removed from vault DB, and the encrypted file removed from
   `<app_data>/vaults/<profile_id>/docs/`
2. Observations and chunks are removed with it (ORM cascade), and embeddings
   with the chunks
3. Extracted entities and categories are deleted explicitly — an entity `quote`
   is verbatim document text and must not remain exportable once the document
   is gone
4. Pins targeting the document, its observations or its entities are pruned
5. Care-plan tasks derived from the document are **kept**, but their provenance
   (`source_document_id`, `source_entity_id`) and their verbatim
   `source_quote` are cleared (CARE-QUOTE-001). A follow-up the patient still
   has to do survives the document; the clinician's verbatim wording does not.
6. Audit log records the deletion

**Known gap.** `response_feedback.prompt_snapshot` stores the fully-composed
assistant prompt including retrieved document context, and carries no link back
to the documents it quoted, so document deletion cannot target it. It stays
inside the encrypted per-profile vault, and RL dataset export forces strict
redaction over it (RL-REDACT-001), but it is not erased when a source document
is. Tracked as `FEEDBACK-SNAP-001`.

## Unverified Extracted Values

Values extracted from an imported document are stored as unverified until the
user confirms them. Owner decision D4 (2026-09-27): trends may show unverified
points, but each must be visibly marked "unverified"; the legacy assistant
(RAG) path cites verified values only, matching the agent path. Status:
owner-approved, **not yet implemented**. Today the trends response carries no
verification flag and legacy RAG retrieval does not filter on it. Tracked as
W-3 in `docs/capstone-report/implementation-program.md` (matrix SAFE-02).

## Third-Party Data Sharing

### Default (Local Mode)

No data leaves the device. All AI processing uses local models.

### Optional External API

When enabled by user opt-in:
- What is sent: the whole prompt the assistant composes for that request, not
  only the question. The prompt holds the assistant's instructions, the context
  retrieved for the question (summaries of the patient's own results, passages
  from their documents with the document's title and, where known, page
  number, and reference text) and the question. In assistant chat it also holds earlier
  turns of the chat session and, when memory is switched on, saved memory
  items (`modules/rag.py`, `compose_prompt` and `query`). Two features can use
  the external provider: assistant chat when it answers through the legacy RAG
  path, and the grounded interpretation of a single result.
- Unless break-glass is active (see the PHI redaction bullet below), the
  prompt is redacted at `strict` before it is sent (`core/external_runner.py`).
  Under break-glass, which is an installation setting and not a patient
  choice, it is sent with reduced or no redaction. `strict` redaction is
  pattern-based. It removes text that matches its rules: dashed SSNs, emails,
  phone numbers, names that follow a label such as "Patient" or "Dr", labelled
  dates of birth and other numeric dates written day-first or month-first with
  slashes or dashes, street addresses with an abbreviated suffix such as "St"
  or "Ave", and labelled MRNs. It has no rule for anything else: for example names with no such
  label, dates written in words or as ISO-8601, lab values, analyte names,
  document titles and document passages. Health information in the prompt
  therefore reaches the provider, and identifying text can too. The prompt is
  built from the context retrieved for that request, not from an export of the
  whole vault.
- API key stored locally (never logged or transmitted elsewhere)
- Provider: OpenAI or Anthropic (user choice)
- PHI redaction: owner decision D12 (2026-09-27) requires `strict` redaction
  through `modules/redaction.py` on every external call, with break-glass as
  the only bypass, allowed only with an audit record and a UI warning. Status:
  code merged in `2f0cb6f` (W-6); **conformance unverified** (matrix
  LOCAL-04).

### No Analytics or Telemetry

HealthCentral does not collect analytics, telemetry, or usage data.
No data is sent to HealthCentral developers or any third party.

## Access Control

| Control | Implementation |
|---------|----------------|
| Authentication | Password + JWT |
| Authorization | Profile-scoped (each user sees only their data) |
| Rate limiting | Per-IP sliding window |
| Brute force protection | Auth rate limiter (10 attempts/60s) |
| Auto-lock | Configurable timeout (default 15 min) |
| Vault isolation | Each profile has a separate encrypted database |
