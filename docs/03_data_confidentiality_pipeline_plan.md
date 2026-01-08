# Data + Confidentiality Pipeline Plan (Draft v0 — pending PM approval)

## Objectives
- Patient data stays on-device by default (offline-first)
- Encrypt at rest:
  - database
  - vector index
  - stored documents
- Per-profile isolation + strong local key management
- Tamper resistance and local auditability for sensitive actions

PRD baseline: encrypt DB/vector/documents; protect per-profile keys via Windows DPAPI or equivalent; profile lock/auto-lock; local audit log.

---

## Storage layout (per profile)
`{app_data}/profiles/{profile_id}/`
- `vault.db` (encrypted SQLite)
- `docs/` (encrypted blobs OR stored in DB)
- `cache/` (temporary decrypted renderings; aggressively cleared)
- `exports/` (user-chosen; default outside vault with warnings)
- `audit.log` (append-only; prefer inside encrypted DB)

---

## Database encryption (SQLCipher)
Use SQLCipher (SQLite extension/fork) to provide transparent AES-256 database encryption.

Implementation rules:
- Enforce KDF and cipher settings centrally.
- Disable unsafe PRAGMAs; keep temp stores inside encrypted DB.
- Never log plaintext keys; never store keys in crash reports.

Licensing:
- Confirm distribution/licensing constraints early (SQLCipher has community + commercial options).

---

## Key management

### Master key per profile
- Generate random 256-bit profile master key at profile creation.
- Seal (encrypt) that master key with Windows DPAPI using the user’s Windows logon context.

### Separation of concerns
- DPAPI protects the profile master key.
- Profile master key wraps:
  - DB key
  - per-document keys
  - vector-index key (if stored separately)

### Key lifecycle
- Explicit lifecycle: generation, rotation plan (MVP+), destruction, compromise handling.
- On profile “lock”, clear decrypted keys from process memory best-effort.

### Backup/export (MVP+)
- Never export DPAPI-sealed keys directly.
- For “profile backup”: re-encrypt vault with user passphrase + strong KDF and export as a single archive.

---

## Document confidentiality

### Default: encrypted file blobs
Store each imported document as an encrypted blob (AES-GCM recommended) with:
- random per-document key
- random nonce
- AAD binding: `{profile_id, document_id, content_hash}`

Key wrapping:
- Wrap per-document key with profile master key; store wrapped key in encrypted DB.

### Temporary plaintext handling
Rendering/OCR requires temporary plaintext:
- write temp files under the profile vault directory
- automatic cleanup on close + crash recovery sweep
- avoid caching extracted text outside encrypted DB

---

## Vector index confidentiality

Preferred options:
1) Store embeddings inside the encrypted DB and query via a SQLite vector extension (keeps encryption-at-rest under SQLCipher).
2) Store an external index file (FAISS, etc.) but encrypt it as an opaque blob; decrypt to memory on demand.

Rules:
- Never store plaintext embeddings on disk outside the encrypted boundary.
- Store `embedding_model_id` per vector for reproducibility.

---

## Local network safety
- Any local HTTP server must bind to `127.0.0.1` only and require an auth token.
- No LAN exposure by default for backend or model runners.

---

## Audit logging
Append-only events:
- profile create/unlock/lock + idle auto-lock
- import/parse/verify edits
- exports
- model configuration changes (local vs optional online in later phases)

MVP:
- append-only table inside encrypted DB.

MVP+:
- hash-chain records for tamper-evidence.

---

## Threat model snapshot
Primary threats:
- lost/stolen device
- malicious local user account access
- malware reading user files
- accidental LAN exposure of local services

Mitigations:
- encrypted DB + encrypted documents + encrypted index
- DPAPI key sealing
- loopback-only binding + token auth
- minimize plaintext caching; explicit retention controls; per-profile isolation

---

## Open decisions (PM approval)
- SQLCipher licensing approach for distribution
- DB-embedded vectors vs encrypted external index default
- Backup/export encryption UX (passphrase and recovery)
- "exports" folder policy: inside-vault vs user-selected location

---

## Implementation Status (Updated 2026-01-07)

### Phase 3: Per-Profile SQLCipher Databases - COMPLETED

**Architecture Implemented:**

```
data/
├── healthcentral.db          # Master DB (profiles, audit logs only)
└── vaults/
    └── {profile_id}/
        ├── vault.db          # Per-profile encrypted SQLCipher DB
        ├── key.bin           # Sealed encryption key
        ├── key.method        # Seal method (dpapi/password)
        └── docs/             # Encrypted document blobs
```

**Key Components:**

1. **PerProfileDatabaseManager** (`core/profile_database.py`)
   - Singleton manager for per-profile database connections
   - Opens encrypted database on login with password-derived key
   - Closes database and clears keys on logout/lock
   - Thread-safe connection pool with asyncio locks

2. **Database Separation:**
   - **Master DB (Base):** Profile, AuditLog
   - **Per-Profile DB (ProfileDatabaseBase):** Document, Observation, Chunk, Embedding

3. **Session-Bound Database Access:**
   - `ProfileDbSession` dependency for API endpoints
   - Database connection tied to authenticated session
   - Automatic key clearing on logout/lock

4. **Security Features:**
   - SQLCipher with raw hex key (no PBKDF2 overhead at query time)
   - Key derived from sealed vault key using password
   - Memory clearing attempt on connection close
   - No cross-profile database access possible

**Known Limitations:**
- Python doesn't guarantee memory clearing (best-effort overwrite)
- SQLCipher requires proper library installation for full encryption
- Current implementation uses aiosqlite (encryption via PRAGMA on connect)

**Files Modified:**
- `core/profile_database.py` - NEW: Per-profile database manager
- `core/database.py` - Updated: Master DB only
- `core/auth.py` - Updated: ProfileDbSession dependency, login/logout hooks
- `models/*.py` - Updated: Split between Base and ProfileDatabaseBase
- `api/profiles.py` - Updated: Open/close profile DB on login/logout
- `api/documents.py` - Updated: Use ProfileDbSession
- `api/observations.py` - Updated: Use ProfileDbSession
