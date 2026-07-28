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
| Audit logs | Master DB + log file | Indefinite |
| Request metrics | In-memory ring buffer | Session only (configurable size) |
| Security events | Log file | Per log rotation policy |
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
| Backups | 30 days | Configurable via `--retention-days` |
| Request metrics | In-memory (session) | Cleared on restart |
| AI model cache | Persistent | Manual cleanup via settings |

## Data Portability

Users can export their data at any time:

| Format | Endpoint | Content |
|--------|----------|---------|
| CSV | `GET /export/csv` | All observations |
| JSON | `GET /export/json` | All observations |
| Doctor Summary | `POST /export/doctor-summary` | Formatted clinical report |

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
5. In one master transaction: purge the audit rows, delete the profile row,
   write the tombstone.

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

**Backups are not automatically deleted** — a manual prune is still required
(Settings → Backup & restore). A backup taken before deletion contains the
sealed key and remains readable with the password, which is exactly what makes
it restorable; it is also why a downloaded archive should be kept as carefully
as the device itself.

**Backup archives are deliberately not redacted** (BKUP-UX-001). Every other
export path passes through `modules/redaction.py` because it produces something
destined for a third party. A backup is the opposite: the user's own
full-fidelity record, going to their own machine, and a redacted backup cannot
be restored. This is the one export-shaped path that is intentionally
unredacted.

### Document Deletion

When a document is deleted:
1. Document record removed from vault DB
2. Associated observations optionally removed
3. Audit log records the deletion

## Third-Party Data Sharing

### Default (Local Mode)

No data leaves the device. All AI processing uses local models.

### Optional External API

When enabled by user opt-in:
- Only the specific query text is sent to the external provider
- Full health records are never transmitted
- API key stored locally (never logged or transmitted elsewhere)
- Provider: OpenAI or Anthropic (user choice)
- PHI redaction applied to API prompts per `modules/redaction.py` policy

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
