# Internal Audit Report (2026-02-05)

Scope:
- Cross-check `docs/` plans/audits against current implementation.
- Identify remaining unimplemented items called out in `docs/`.
- Implement remaining **P1 security hardening** items from `docs/full_audit_report_2026-02-02.md`.

Branch context: `Security-Revamp-2`

---

## Executive summary

### Security status
- **P0 (critical) security issues:** none identified (per prior audits).
- **P1 (defense-in-depth) items addressed in this audit:**
  1) JWT logout invalidation (revocation list by `jti`)
  2) Rate limiting on auth endpoints (login/unlock)
  3) Explicit legacy plaintext document handling (no silent fallback by default)
  4) Avoid leaking internal exception details in assistant chat responses

### Docs drift fixed
- `docs/06_mvp_to_rag_execution_board.md` updated to reflect export + assistant wiring and chunk/embedding indexing on import.
- `docs/05_backend_integration_status.md` updated to reflect that text extraction is implemented in `ExtractModule`.
- `docs/01_backend_architecture_plan.md` updated to reflect current loopback HTTP + JWT auth model (and keep ephemeral-token ideas as future hardening).

---

## Security hardening implemented (P1 items)

### 1) JWT token invalidation on logout (P1-2)
Problem (from audit): logout did not invalidate a stolen token.

Implementation:
- Add `jti` + `iat` claims to issued JWTs.
- Persist a local revocation list keyed by `jti`.
- Treat revoked tokens as invalid during `verify_token()`.
- Revoke tokens on both `/profiles/logout` and `/profiles/{id}/lock`.

Files:
- `src/backend/core/token_revocation.py` (new) — persistent revocation list
- `src/backend/core/security.py` — add `jti`/`iat`, revocation checks, revoke helper
- `src/backend/core/auth.py` — include `token_jti` in `Session`
- `src/backend/api/profiles.py` — revoke on logout/lock

Notes:
- Revocation is **local-first** and stored in `data/.jwt_revoked_tokens.json` (relative to `settings.app_data_path`).
- Tokens issued before `jti` support cannot be revoked and will expire naturally.

### 2) Rate limiting on auth endpoints (P1-3)
Problem (from audit): login/unlock were brute-forceable.

Implementation:
- Add lightweight in-memory rate limiter (sliding window) and apply to:
  - `POST /profiles/login`
  - `POST /profiles/{profile_id}/unlock`
- Count only failed attempts; reset on success.
- Return `429` with `Retry-After` when limited.

Files:
- `src/backend/core/rate_limiter.py` (new)
- `src/backend/api/profiles.py` (login/unlock updated)

Notes:
- Limiting is per-process (sufficient for desktop/local mode). For future server mode, replace with shared storage.

### 3) Legacy plaintext document handling made explicit (P1-5 / P1-4)
Problem (from audit): document decryption silently fell back to plaintext.

Implementation:
- Require explicit setting `ALLOW_LEGACY_PLAINTEXT_DOCUMENTS=true` to enable plaintext fallback.
- Only allow fallback when bytes match known supported file signatures (PDF/PNG/JPEG) to avoid treating corrupted ciphertext as plaintext.

Files:
- `src/backend/modules/ingest.py` (decrypt behavior)
- `src/backend/core/config.py` (new setting)
- `config/.env.example` (documented)

### 4) Reduce internal error detail leakage in assistant chat
Problem: `/assistant/chat` returned raw exception strings in HTTP 500 responses.

Implementation:
- Log exceptions server-side and return a generic error message.

Files:
- `src/backend/api/assistant.py`

---

## Remaining unimplemented items (docs/ vs code)

### Backend stubs / TODOs
- `src/backend/modules/verify.py` contains `NotImplementedError` paths (verification workflow not implemented).
- `src/backend/modules/ingest.py` still has TODO for content-hash deduplication.
- `src/backend/modules/rag.py` vector search filters (`selected_analytes`, `from_date`, `to_date`) are not implemented in the async search.

### Feature backlog (docs/features/TASK_LIST.md)
Large sections remain TODO, especially:
- Phase 4 UI (Lab Interpreter + Medication Coach pages/components/services/hooks)
- Phase 5 safety testing (adversarial prompt testing, citation/disclaimer coverage verification)
- Accessibility audit (WCAG 2.2 AA checklist)
- Performance polish (model lazy loading, caching, bundle size)
- Documentation deliverables (user guides, API docs refresh)

---

## Test/verification notes (local-first expectations)

Observed during test runs in restricted environments:
- Some tests use the system temp directory; ensure `TEMP`/`TMP` are writable or redirect them to a workspace directory.
- Some embedding tests attempt to download models from Hugging Face; ensure models are pre-provisioned locally or provide an offline fallback for CI.

---

## Configuration additions

New settings (see `src/backend/core/config.py` and `config/.env.example`):
- `JWT_REVOCATION_ENABLED` (default: true)
- `AUTH_RATE_LIMIT_ENABLED` / `AUTH_RATE_LIMIT_MAX_ATTEMPTS` / `AUTH_RATE_LIMIT_WINDOW_SECONDS`
- `ALLOW_LEGACY_PLAINTEXT_DOCUMENTS` (default: false)

