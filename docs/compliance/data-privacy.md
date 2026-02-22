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
