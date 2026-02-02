# Audit of Proposed Fixes Plan (2026-02-02)

This document reviews the proposed "HealthCentral Security Audit Co-Assessment & Remediation Plan" for correctness, completeness, and risk.

Scope: **audit the plan only** (no implementation performed here).

---

## Implementation Status: COMPLETE (2026-02-02)

All remediation items have been implemented. See commit for full changes.

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1: FastAPI DI fix | COMPLETE | 6 endpoints fixed in model_settings.py |
| Phase 2: Decrypt-on-read | COMPLETE | New document_crypto.py helper created |
| Phase 3: Document encryption | COMPLETE | IngestModule now receives encryption key |
| Phase 4: SQLCipher verification | COMPLETE | cipher_version check + config option added |
| Phase 5a: DocumentInbox fix | COMPLETE | Uses useAuthStore instead of localStorage |
| Phase 5b: Panel ID mismatch | COMPLETE | Changed 'lipids' to 'lipid' |
| Phase 6a: ESLint config | COMPLETE | Created eslint.config.js with flat config |
| Phase 6b: Revision pinning | COMPLETE | Added to all 3 hf_hub_download locations |
| Phase 6c: Contract drift | COMPLETE | Removed unused profile_id params |
| Phase 6d: Ruff config | COMPLETE | Created pyproject.toml with E712 ignored |

---

## Executive Assessment

Your verification table is accurate for the listed findings. The remediation plan is directionally correct, but **incomplete in two P0 areas** and **risky in one P1 area**:

1) **P0 missing**: Enabling document vault encryption will break the current pipeline unless you also add **decrypt-on-read** in multiple places (import → extract, pages endpoint, chunking/embeddings).
2) **P0 missing**: SQLCipher “verification” is good (fail-closed), but the plan does not include the **runtime/driver reality** (current code uses `sqlite+aiosqlite`, which is typically not SQLCipher-enabled). You either need to (a) ship a SQLCipher-enabled SQLite, or (b) allow an explicit dev-only plaintext mode.
3) **P1 risky**: `ruff check --fix .` can apply **incorrect autofixes** for SQLAlchemy boolean comparisons (notably E712 “not <column>” suggestions), potentially breaking query semantics.

## Phase-by-Phase Audit

### Phase 1 (P0): Fix FastAPI dependency injection in `model_settings.py`

**Assessment: VALID and REQUIRED.**

- The proposed change to use:
  - `session: RequireAuth`
  - `profile_db: ProfileDbSession`
  is correct for FastAPI’s `Annotated[..., Depends(...)]` dependency aliases.
- Your referenced line ranges match the file (6 occurrences).

**Note:** After fixing this, add a tiny import/startup smoke test so this class of issue cannot regress.

### Phase 2 (P0): Security critical fixes

#### 2a) Enable document vault encryption

**Assessment: INCOMPLETE (must expand to avoid breaking runtime).**

What’s correct:
- Passing an encryption key into `IngestModule(..., encryption_key=...)` will cause AES-GCM encryption at rest.
- Using the per-profile key from the profile DB connection is workable because `DocumentEncryption` supports both 32-byte raw keys and 44-byte Fernet keys (it base64-decodes 44-byte keys).

What’s missing (P0 blockers):
- Multiple code paths currently treat the stored file as plaintext and call `pdfplumber.open(doc_path)` directly. Once encrypted, these will fail:
  - `src/backend/api/documents.py`: import/extract step uses `ExtractModule.extract_from_pdf(doc_path, ...)`
  - `src/backend/api/documents.py`: `/documents/{id}/pages` reads `doc_path` directly
  - `src/backend/api/documents.py`: `_create_chunks_and_embeddings()` reads `doc_path` directly
- Therefore, the plan must explicitly include **decrypt-on-read** wherever a stored document is opened.

Recommended plan addition (still P0):
- Introduce a single “open decrypted document” helper and use it in all readers:
  - Option A: decrypt to memory (`bytes`) and pass `io.BytesIO(...)` to `pdfplumber.open()`
  - Option B: do extraction/chunking from the **original upload bytes** before writing the encrypted file (still need decrypt for `/pages`)
- Ensure you do **not** write plaintext PDFs to disk as a “temp convenience” (or if you must, keep them in a temp folder with aggressive cleanup and treat as sensitive).

Also consider:
- Using one key for both DB and documents is acceptable as an interim step, but longer-term you should derive distinct subkeys (e.g., HKDF) to reduce key reuse risk.

#### 2b) SQLCipher verification / enforcement

**Assessment: PARTIAL (good detection, missing driver/ops plan).**

What’s correct:
- `PRAGMA cipher_version` is a good “is SQLCipher present?” check.
- Failing closed if SQLCipher isn’t available is reasonable for a security-first local PHI vault.

What’s missing:
- Today the engine uses `sqlite+aiosqlite` (standard Python SQLite), which is *commonly not* SQLCipher-enabled. Your check will correctly detect that and then hard-fail profile DB open.
- The plan must therefore include **how SQLCipher is actually provided**:
  - ship a SQLCipher-enabled SQLite/Python build, or
  - switch to a SQLCipher-capable DB-API driver, or
  - allow a clearly marked, explicit dev override (e.g., `DATABASE_ENCRYPTION_ENABLED=false`) and ensure production builds are fail-closed.

Implementation detail note:
- The plan references `ProfileDatabaseEncryptionError`, which does not exist today; you’ll need to introduce an exception type or raise a standard exception and map it to an HTTP response upstream.

### Phase 3 (P0): Frontend fixes

#### 3a) DocumentInbox `activeProfileId` bug

**Assessment: VALID.**

- Switching `DocumentInbox.tsx` to use `useAuthStore().profileId` is the right fix.
- Optional plan improvement: also handle the “no profileId/token” case explicitly (redirect or call-to-action).

#### 3b) Panel ID mismatch (`lipids` vs `lipid`)

**Assessment: VALID.**

- Backend defines `panel_id = "lipid"`, so frontend should request `/observations/panels/lipid`.

### Phase 4 (P1): Code quality and hardening

#### 4a) Add ESLint configuration

**Assessment: VALID.**

- Adding `src/frontend/eslint.config.js` is the right direction to make `npm run lint` usable.
- Note: `npm audit` flagged `eslint` (dev tooling). If you choose to upgrade ESLint major versions, treat that as a separate change from “add config” to reduce risk.

#### 4b) Model download revision pinning

**Assessment: VALID but INCOMPLETE.**

- Add `revision` to `hf_hub_download` calls.
- Also update `src/backend/scripts/model_manager.py` (Bandit flagged it too).
- Consider pinning by commit hash and optionally validating file hashes for GGUF artifacts (stronger supply-chain integrity).

#### 4c) Remove contract drift (`profile_id` query params)

**Assessment: VALID but watch UX/caching behavior.**

- Removing `profile_id` from query params is correct since backend derives profile from JWT.
- If you keep `profile_id` only for React Query cache keys/enabling, that’s fine; just don’t send it to the API.
- Alternatively: remove it from filter types entirely and gate queries on `isAuthenticated()` instead of `!!filters.profile_id`.

#### 4d) Run `ruff --fix` + `black`

**Assessment: RISKY unless constrained/configured.**

- `ruff` autofixes can be unsafe around SQLAlchemy boolean expressions (E712 suggestions like `not Column` are not valid SQLAlchemy and can raise or change behavior).
- Recommendation: first add/adjust backend lint configuration to:
  - ignore/disable E712 in SQLAlchemy contexts, or
  - restrict autofix to safe rules (imports, formatting) and fix query logic manually.

## Recommended Adjustments to Implementation Order

Proposed safer P0 sequence:

1) Fix `model_settings.py` dependency injection (Phase 1)
2) Implement document decrypt-on-read plumbing (new P0 sub-phase)
3) Enable document encryption (Phase 2a) + verify import/pages/chunking all still work
4) Add SQLCipher availability enforcement (Phase 2b) *only after* deciding how SQLCipher will be shipped/required
5) Fix frontend `activeProfileId` and `lipid(s)` mismatch (Phase 3)

## Verification Improvements (Additions)

Beyond the current verification steps, add:

- **Backend smoke test:** start app and hit `/health`, and at least one authenticated endpoint.
- **Encrypted document roundtrip:** import PDF → verify `/documents/{id}/pages` still works (requires decrypt path).
- **SQLCipher enforcement check:** confirm `PRAGMA cipher_version` returns non-empty and that `vault.db` cannot be opened by standard SQLite tooling without key.
- **Panel request:** ensure `/observations/panels/lipid` returns data and UI tab works.

