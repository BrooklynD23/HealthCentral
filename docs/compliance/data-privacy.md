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
| Audit logs | Master DB (not encrypted); each event is also logged to the application logger only (the process's stderr), at INFO below the default WARN level — the app writes no log file (`dev.sh` redirects it to `logs/dev-backend.log`) | Indefinite |
| Request metrics | In-memory ring buffer | Session only (configurable size) |
| Security events | Request events from `SecurityAuditMiddleware`: application logger only (the process's stderr); no log file is written, and they are logged at INFO, below the default WARN level, so by default they are not emitted. Break-glass external calls: an audit row in the master DB (`security.external_api.break_glass`) | Request events: not retained by the app. Break-glass rows: as audit logs |
| Correlation IDs | Request-scoped | Not persisted |

## Encryption

### At Rest

| Component | Algorithm | Key Management |
|-----------|-----------|----------------|
| Profile vaults | AES-256-CBC (SQLCipher) | Password-derived key (PBKDF2) |
| Master database | Not encrypted | Contains no PHI |
| Backups | Same as source | SQLite backup API preserves encryption for the database files; `manifest.json` is plaintext metadata and sealed keys stay sealed |

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
| Pre-017 vault snapshot (and its aside copy) | Until the first vault open 30 days or more after it was made, and only once migration 017 has completed on that vault. A vault that cannot complete 017 keeps it past 30 days. | One per profile, in its own folder, made once before migration 017 runs on an existing vault. A snapshot that fails verification is moved aside to a second file instead of being overwritten, so a profile can hold two full copies of its patient data until the purge removes the aside. See [Pre-017 vault snapshot](#pre-017-vault-snapshot). Both are deleted with the profile and by the synthetic-profile test reset. |
| Request metrics | In-memory (session) | Cleared on restart |
| AI model cache | Persistent | Manual cleanup via settings |

### Pre-017 vault snapshot

Migration 017 (C-P6, SQL-FK-001) deletes orphan rows that point at a parent
that no longer exists and clears dangling links, and its downgrade restores
neither. So before 017 runs on a vault that already holds data, the app keeps a
copy of the vault file.

- **Where and what.** One per profile, in the profile's own folder
  (`<app_data>/vaults/<profile_id>/vault.pre017.snapshot`). It is a copy of the
  encrypted file, sealed with the same key as the vault. It is never decrypted
  and never written as plain text. That holds with SQLCipher; in the
  local-development mode without it the vault is a plain SQLite file and the
  copy is exactly as plain as the vault.
- **When.** Only when 017 has not yet run on a vault that already holds a user
  table. A new empty vault (a file with no table, or only the derived search
  index), and a vault already at 017 or later, take none.
- **Verified before it counts.** The write-ahead log is folded into the vault
  file first, the copy is written under a temporary name and flushed, opened
  with the same key, and `PRAGMA quick_check` must report `ok`. Only then is it
  renamed into place. If any step fails, the migration is **refused**: the vault
  is left untouched and is not upgraded. The patient sees the existing generic
  500 "Failed to open profile database"; the reason (the step and the error
  class, no path or key) goes to the application log only. On recovery with a
  recovery code the new password and the rotated code are committed before the
  vault is opened, so a refused snapshot there loses the new code.
- **A good snapshot is kept.** If one already verifies, it is kept and not
  copied again, so a retry after a failed upgrade cannot replace the original
  with a copy of a partly cleaned vault. A vault that has not completed 017 keeps
  a snapshot that verifies at any age. After a backup is restored over a vault
  that holds such a snapshot, and 017 has not completed on the restored vault,
  migration therefore takes no fresh one; the restored backup is the recovery
  copy.
- **A snapshot that fails verification is moved aside, not replaced.** If the
  snapshot is there but no longer opens with the key, or fails the integrity
  check, it is moved, with any journal, WAL or shm files beside it, to
  `vault.pre017.snapshot.aside` in the same folder, and a new snapshot is
  taken. The aside file is the original file: same key, same bytes, never
  decrypted. Only a file the database reports as damaged is moved. A read fault
  partway through the file can be reported as damage, so a good copy can still
  be moved aside; it is kept, not deleted. A snapshot that cannot be opened or
  read for another reason (no permission, a lock, no file handles left, a disk
  read error on the first read) is not moved: the migration is refused and
  nothing is touched. The aside file follows the same 30-day rule, counted from
  the time the original snapshot was made, not from the move. Because it is a full copy of
  the vault as it was, a profile can hold two full copies of its patient data,
  the aside and the new snapshot, until the purge removes the aside. That lasts
  at least until day 30 and has no limit while 017 cannot complete. If the
  aside name is already occupied (by the aside file or by any of its journal,
  WAL or shm files: `vault.pre017.snapshot.aside`, `-journal`, `-wal`, `-shm`),
  the migration is **refused**, the same way as a failed snapshot: nothing is
  touched, the vault is not upgraded, and the patient sees the same generic
  500. The age purge cannot free the name, because it runs only after 017 has
  completed. The vault therefore stays closed until those files are removed by
  hand. Deleting the profile would also remove them, but that needs a signed-in
  session, and login and unlock create the session only after the vault has
  opened, so a patient whose vault is refused cannot normally get one: the
  practical exit is removing the aside files by hand. That lets the open
  continue, and the vault opens only if 017 then completes. If 017 still fails,
  the vault stays closed, and the removed file, the original that was moved
  there, may be the only intact pre-017 copy.
- **Deleted.** With the profile (the vault-folder sweep in step 4 below) and by
  the synthetic-profile test reset. Both remove the snapshot, the aside copy and
  their journal, WAL and shm files.
- **A document deleted afterwards stays in it.** The snapshot is a frozen copy
  of the vault as it was before 017. A document, entity quote or care-plan
  quote the patient deletes after the migration is gone from the live vault but
  still readable in the snapshot, and in the aside copy if there is one, until
  the purge below removes it, and that purge waits for the next open of the
  vault on or after day 30, once 017 has completed on that vault. Deleting a
  document does not touch the snapshot or the aside. See the known gap under
  [Document Deletion](#document-deletion).
  A replacement snapshot taken after a failed attempt is only as complete as
  the live vault it was copied from. A copy already 30 days old is removed on
  the first open after 017 completes, so in that case no recovery window remains.
- **Purged by age.** On the first open of the vault 30 days or more after the
  snapshot was made, and only once the vault is confirmed at revision 017 or
  later. The open that completes 017 does not purge, because that same open has
  just deleted rows; the next open does. A vault that cannot complete 017 (the
  migration fails or is refused) keeps its snapshot and its aside copy past 30
  days, for as long as it takes, until 017 completes. Deleting the profile
  also removes them, but that needs a signed-in session that a refused login
  cannot create. What removing files by hand does depends on why the vault is
  closed. If the aside name is occupied, removing the occupying files lets the
  open continue; the vault opens only if 017 then completes, and if 017 still
  fails it stays closed and the removed file may be the only intact pre-017
  copy. If the snapshot cannot be read (no permission, a lock, a disk read
  error), the vault stays closed until the fault is repaired and nothing needs
  removing; removing the snapshot lets the open continue and the vault opens if
  017 then completes, but it discards the original. If 017 fails, or the file
  matches no schema, there is no exit until the cause is repaired, and removing
  the snapshot does not open the vault, ends the retention and discards the only
  copy of the rows 017 deletes (the next open then snapshots the live vault).
  This extends the
  retention of that data beyond 30 days on purpose: the
  snapshot is the only copy of the rows 017 deletes. The snapshot and the aside
  copy are each judged by their own time, which is the time the original
  snapshot was made, not the vault's or the move's. A session that is already
  open does not purge them until the vault is opened again. A leftover
  temporary copy from an interrupted attempt is removed on every open, at any
  age.
- **Not purged when the password or recovery code changes.** Those re-seal the
  same data key and there is no re-keying path, so the snapshot is keyed by the
  same key as the live vault. An old password opens nothing without the old
  sealed key file, and whoever holds the data key can read the live vault too.
- **Excluded from backups by name.** A backup copies the files ending in `.db`
  and the four sealed-key files; none of the snapshot, its temporary copy and
  its aside copy ends in `.db`. A restore does not remove a snapshot or an
  aside copy; they survive it, and the 30-day purge covers them.

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
- **The doctor summary is redacted at the `strict` policy level,** because it
  goes to a third party, in all three download formats (text, HTML, PDF).
  Implemented in `c4b1aa5`; tests HC-EXPR-001…003.

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
4. Sweep the whole vault directory — database, WAL/SHM sidecars, encrypted
   documents, and the pre-017 snapshot and its aside copy if they are still
   there. Failures here are
   logged but do not abort: the data is already cryptographically erased, and a
   retry finishes the cleanup.
5. Sweep the profile's backup directory (`<app_data>/backups/<profile_id>`) on
   the same log-and-continue terms. Each backup holds its own copy of the sealed
   key, so leaving them behind would leave the record restorable after a
   "permanent" deletion.
6. In one master transaction: purge the audit rows, delete the profile row,
   delete the `backup_schedules` row, write the tombstone. The schedule row is
   deleted explicitly even though `PRAGMA foreign_keys` is now ON and the
   `ondelete="CASCADE"` on the model would fire too, because the steps are
   ordered on purpose and restore's raw `sqlite3` path never sees the pragma.

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
packet, the pinboard export, the FHIR bundle, the RL dataset and, under D3, the
doctor summary (implemented in `c4b1aa5`).

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

**Known gap (pre-017 snapshot).** On a vault that already held data when
migration 017 ran, `vault.pre017.snapshot` is a full copy of the vault from
before the migration, made automatically. A snapshot that failed verification
is kept as `vault.pre017.snapshot.aside`, another full copy, beside the new
one. Deleting a document afterwards does not reach either: the document, its
extracted entities and quotes, and any care-plan quote stay readable in those
copies until they are purged, on the first open of the vault 30 days or more
after the snapshot was made, once 017 has completed on that vault (an
already-open session does not purge them until the vault is opened again). A
vault that cannot complete 017 keeps them past 30 days, until it completes.
Deleting the profile removes them too, but that needs a signed-in session that
a refused login cannot create. For a locked-out patient, removing files by hand
means different things. With the aside name occupied, removing the aside files
lets the open continue; the vault opens only if 017 then completes, and if 017
still fails it stays closed and the removed file may be the only intact pre-017
copy. With a snapshot that cannot be read (no permission, a lock, a disk read
error), the vault stays closed until the fault is repaired and nothing needs
removing; removing the snapshot lets the open continue and the vault opens if
017 then completes, but it discards the original. While 017 fails, or the file
matches no schema, nothing opens the vault until the cause is repaired, and
removing the snapshot only ends the retention and discards the only copy of the
rows 017 deletes. The copies are encrypted with the same key as the
vault, so they expose nothing that the vault key did not already open; the gap
is only that a deletion is not final until then, and the purge needs a vault
open, so a vault that is never opened keeps the copies. Deleting the whole
profile removes them at once. Deleting a document does not delete the snapshot
or the aside (see [Pre-017 vault snapshot](#pre-017-vault-snapshot)).

## Unverified Extracted Values

Values extracted from an imported document are stored as unverified until the
user confirms them. Owner decision D4 (2026-09-27): trends show unverified
points visibly marked "unverified", and the legacy assistant (RAG) path cites
verified values only, matching the agent path. That includes the no-LLM
fallback, which cites verified values only, and legacy RAG document chunks,
which come from verified documents only. Implemented in `b45f9cb`; tests
HC-VER-001…005 and vitest HC-VER-FE-001…003.

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
- PHI redaction: `strict` through `modules/redaction.py` on every external
  call (owner decision D12, 2026-09-27; implemented in `2f0cb6f`).
  Break-glass is the only bypass, and it is allowed only with an audit record
  and a UI warning. The warning shows in Settings and on the chat page
  (`2f0cb6f`) and on the interpretation page (`eaad770`). Tests: backend
  HC-EXT-001, HC-EXT-002…002d, HC-EXT-004 and HC-EXT-004b; vitest HC-EXT-003
  (the warning component), HC-EXT-005 (chat page) and HC-EXT-006
  (interpretation page). The Settings page has no page-level warning test.

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
