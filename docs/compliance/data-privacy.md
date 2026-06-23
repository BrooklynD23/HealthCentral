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
| PHI redaction | **Mandatory and non-configurable**: prompt/response text is passed through `modules/redaction.py` before export. The current standard policy covers identifiers such as SSNs, emails, phone numbers, and context-prefixed names; it does not guarantee removal of every lab value, date, medication name, or biomarker value. |
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
| Redacted prompt snapshot | ✅ Yes | SSNs, emails, phone, name-context stripped (`standard` policy). Dates of birth, addresses, MRNs require `strict` policy and are **not** removed by the default export. Lab values and biomarker names are **not** removed. |
| User rating (+1/−1) | ✅ Yes | |
| Correction text | ✅ Yes | Same redaction as prompt snapshot |
| Model name / provider | ✅ Yes | |
| Full unredacted observation text | ❌ Never | Only the prompt snapshot (which may reference observations) is exported |
| Original pre-redaction content | ❌ Never | Redaction is applied before any write; originals are not stored in export files |

**Confirmation gate:** `confirmed=true` must be present in the request body. Absent this flag the export endpoint returns HTTP 400.

**Output path:** `rl_exports/profile_<full-profile-uuid>/` — local disk only, no network write.

## Data Deletion

### Profile Deletion

When a profile is deleted:
1. Encrypted vault database file is removed
2. Master database entry is deleted
3. Audit log records the deletion event
4. Associated backups are not automatically deleted (manual prune required)

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
