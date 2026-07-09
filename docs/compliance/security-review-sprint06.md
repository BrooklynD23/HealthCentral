# Sprint 06 Security Best-Practices Review (Static)

Date: 2026-02-22  
Scope (Sprint 06 commits): `a2d25cc` (OPS-003), `1662f0e` (OPS-001), `48e122c` (OPS-002), plus docs commits `902dff5` (OPS-004), `8d61783` (OPS-005), `c9fe966` (OPS-006).  
Primary stack in scope: FastAPI (Python) backend + GitHub Actions CI.

This report is **findings + remediation plan only**. It intentionally **does not implement** changes.

> **Status update (2026-07-01):** Re-verified against current code during a doc-accuracy audit. **S06-SEC-001 is RESOLVED** (auth now enforced). **S06-SEC-002 is PARTIALLY MITIGATED** (bounded limit now applied, no longer unlimited — see finding for what's still unverified). **S06-SEC-003 is CONFIRMED STILL OPEN** (the `ValueError`-to-500 gap is real as of this pass). CI's `bandit`/`pip-audit` still run with `continue-on-error: true` per `.github/workflows/ci.yml` — unchanged.

## Executive summary

Sprint 06 adds valuable security middleware, monitoring, and backup tooling, but it also introduces a few high-impact security risks:

1) **Critical**: A full metrics dashboard endpoint is exposed without authentication (`/monitoring/metrics` and `/api/v1/monitoring/metrics`). This discloses internal route templates and service behavior and is easy recon for attackers.  
2) **High**: The new input-validation middleware **explicitly bypasses** request-body size limits on document import/upload endpoints; combined with existing code that reads uploads fully into memory, this enables straightforward memory/CPU DoS.  
3) **High**: Backup `restore()` trusts `manifest.json` paths without sanitization, enabling **path traversal / arbitrary file overwrite** if a backup package is tampered with.

Additional medium/low items include `/health` being rate-limit-exempt while computing metrics, production “debug/reload/docs” misconfiguration footguns, and CI security scans that never fail builds.

## Assumptions / threat model notes

- HealthCentral runs in two modes (`local` vs `server`). Findings that involve endpoint exposure are **low risk in strictly-localhost deployments**, but become **high risk if `server` mode is reachable by untrusted clients**.
- Static review only; runtime infra protections (reverse proxy, WAF, network allowlists) are **not visible here**.

---

## Findings

### S06-SEC-001 — Unauthenticated metrics dashboard exposed — ✅ RESOLVED (verified 2026-07-01)

**Update:** Independently re-verified against current code. `src/backend/monitoring/health.py:34` now takes `session: RequireAuth` as a parameter on `get_metrics()` — the fix recommended below has been applied. `docs/api/endpoints.md:172` already correctly documents this route as `Auth: Yes`. No further action needed on this finding; retained below for historical record only.

- Severity: **Critical** (at time of original review)
- Impact (1 sentence): Any network-reachable deployment exposes internal endpoint inventory + performance/error characteristics, which materially improves attacker reconnaissance and can reveal operational state.
- Location:
  - `src/backend/monitoring/health.py:38-70` (metrics dashboard route)
  - `src/backend/main.py:111-114` (router included both at `/` and `/api/v1`)
  - `docs/api/endpoints.md:183-188` (documents dashboard as “Auth: No”)
- Evidence:
  - `src/backend/monitoring/health.py:38-45` defines `@router.get("/monitoring/metrics")` and notes “Should be auth-protected in production” but does not enforce auth.
  - `src/backend/monitoring/health.py:49-70` returns per-endpoint stats including route templates.
- Why this is risky:
  - Reveals internal route templates (API surface map).
  - Reveals uptime, error rate, latency percentiles, and RPS-like stats which can help tune attacks and identify “weak” endpoints.
- Fix (recommended):
  1. Require authentication/authorization for `/monitoring/metrics` in `server` mode (and ideally always).
     - E.g., apply an auth dependency such as `RequireAuth` / `require_auth` (from `core.auth`) or a dedicated “admin token” mechanism.
  2. Consider splitting endpoints:
     - Keep `/health` minimal and unauthenticated (200 + “ok”) for liveness.
     - Gate “detailed metrics” behind auth and/or local-only access.
  3. Update docs to match the enforced policy (currently indicates no auth).
- Mitigations (defense-in-depth):
  - Network allowlist / bind to localhost / expose only via VPN.
  - Add rate limiting specifically for metrics endpoints (even after auth).
- False-positive notes:
  - If deployment always binds to `127.0.0.1` and is never proxied publicly, the practical exposure is lower. Verify `app_mode`/host settings at runtime.

---

### S06-SEC-002 — Upload endpoints bypass request size limits → memory/CPU DoS — ⚠️ PARTIALLY MITIGATED (verified 2026-07-01)

**Update:** Independently re-verified against current code. `src/backend/security/input_validator.py`'s middleware no longer treats import endpoints as unlimited — it now applies `effective_limit = self.max_upload_bytes if is_import else self.max_request_body_bytes`, i.e. a separate, larger, but still-enforced limit for import/upload paths, matching remediation option 1 below. This is *not* the "explicitly bypasses"/"no limit" behavior originally described — the middleware-level fix has landed. **Still open:** `modules/ingest.py` reportedly still reads the full upload into memory before checking size (not re-verified this pass) — if true, that's a narrower risk (bounded by `max_upload_bytes`, not unlimited) than originally described, but worth a fresh check before closing this finding entirely.

- Severity: **High** (at time of original review; now bounded, not unlimited)
- Impact (1 sentence): Attackers can send extremely large bodies to import/upload endpoints, causing memory exhaustion or severe performance degradation.
- Location:
  - `src/backend/security/input_validator.py:15-87` (import/upload bypass logic)
  - `src/backend/modules/ingest.py:256-263` (reads entire upload into memory before size validation)
- Evidence (original, at time of review):
  - `src/backend/security/input_validator.py:15-19` defines `IMPORT_PATH_PREFIXES` including `/api/v1/documents/import` and `/api/v1/documents/upload`.
  - `src/backend/security/input_validator.py:62-88` sets `is_import` and then **skips** both `Content-Length` enforcement and streaming counting when `is_import` is true.
  - `src/backend/modules/ingest.py:256-263` does `file_data = file.read()` and only then checks `len(file_data)` against `settings.max_import_file_size_mb`.
- Why this is risky:
  - The middleware currently treats import endpoints as “no limit”, but the ingestion pipeline is not streaming; it is explicitly in-memory.
  - This is a classic unauthenticated DoS vector if the endpoint is reachable and accepts uploads.
- Fix (recommended):
  1. Replace “bypass” with a **separate, explicit max** for import endpoints:
     - Example: `max_upload_body_bytes = settings.max_import_file_size_mb * 1024 * 1024 + overhead`.
     - Enforce both via `Content-Length` and streaming byte counting for chunked requests.
  2. Make the bypass conditional on `Content-Type: multipart/form-data` (or on route name), not just path prefix.
  3. Longer-term: refactor ingestion to stream uploads to disk with a hard limit rather than `file.read()`.
- Mitigations:
  - Enforce request size limits at the reverse proxy (Nginx `client_max_body_size`, etc.) even after app fixes.

---

### S06-SEC-003 — Streaming body size enforcement raises `ValueError` (may become 500s)

- Severity: **High**
- Impact (1 sentence): Oversized streaming requests may trigger unhandled exceptions and produce 500s/tracebacks instead of clean 413 responses, enabling noisy DoS and potential information leakage in debug environments.
- Location:
  - `src/backend/security/input_validator.py:90-106` (`_make_counting_receive` raises `ValueError`)
- Evidence:
  - `src/backend/security/input_validator.py:101-104` raises `ValueError(f"Request body exceeded {max_bytes} bytes")`.
  - No global exception handler is registered in `src/backend/main.py` to convert this into an HTTP 413 response.
  - Test coverage indicates the *route/app* must catch the `ValueError` to return 413 (`src/backend/tests/security/test_input_validator.py:110-121`).
- Fix (recommended):
  1. Make the middleware return a 413 itself (do not require downstream apps to catch exceptions).
     - Common pattern: wrap `await self.app(...)` in a try/except for the specific internal exception and send a 413 if the response hasn’t started yet.
  2. Ensure consistent behavior for both Content-Length and streaming paths (same status code + JSON detail).
- Mitigations:
  - If immediate changes are hard, add a top-level FastAPI exception handler to translate this `ValueError` into 413 (but middleware-level fix is cleaner).

---

### S06-SEC-004 — Backup restore trusts manifest paths (path traversal / arbitrary overwrite)

- Severity: **High**
- Impact (1 sentence): A tampered backup can overwrite arbitrary files (or read arbitrary files during verify) when an operator runs `restore`, potentially leading to system compromise under the operator’s privileges.
- Location:
  - `src/backend/scripts/backup.py:205-219` (verify reads files from `entry["path"]`)
  - `src/backend/scripts/backup.py:247-259` (restore writes files to `data_dir / entry["path"]`)
- Evidence:
  - `src/backend/scripts/backup.py:205-207` constructs `file_path = backup_path / entry["path"]` without validating that it stays within `backup_path`.
  - `src/backend/scripts/backup.py:248-250` constructs `dest_file = data_dir / entry["path"]` without validating that it stays within `data_dir`.
- Attack scenario:
  - Attacker provides a “backup” folder where `manifest.json` contains `{"path": "../../some/sensitive/file", ...}`.
  - If the operator runs restore, the script can write outside the intended directory tree.
- Fix (recommended):
  1. Validate manifest paths before use:
     - Reject absolute paths and any path containing `..`.
     - Resolve (`(base / rel).resolve()`) and ensure it is within the intended base directory.
  2. Reduce trust in the manifest:
     - Consider discovering `.db` files directly from the backup directory structure (with strict allowlist) and using the manifest only for integrity metadata.
  3. If tamper resistance is required:
     - Add authenticity (e.g., HMAC/signature) for `manifest.json`, stored separately from the backup, or encrypt/sign the backup bundle.
- Tests to add (to prevent regressions):
  - A unit test that crafts a manifest containing `../` paths and asserts verify/restore reject it.

---

### S06-SEC-005 — `/health` is rate-limit-exempt while optionally computing metrics

- Severity: **Medium**
- Impact (1 sentence): Attackers can spam an unthrottled endpoint that performs non-trivial computation, degrading availability.
- Location:
  - `src/backend/security/rate_limit_middleware.py:19-21` (`EXEMPT_PATHS = ("/health",)`)
  - `src/backend/monitoring/health.py:18-35` (`/health` returns metrics summary when enabled)
  - `src/backend/monitoring/metrics.py:96-158` (`get_summary()` sorts/aggregates buffer records)
- Fix (recommended):
  - Keep `/health` cheap: return only `{status: "ok"}` (no metrics) and move metrics to an authenticated endpoint.
  - Or cache summary with a short TTL (e.g., 1–5s) so repeated calls are constant-time.
  - Or remove `/health` from the exempt list (or apply a higher-but-nonzero limit).

---

### S06-SEC-006 — Production debug/reload/docs exposure is a configuration footgun

- Severity: **Medium**
- Impact (1 sentence): If `debug` is accidentally left enabled in production, the service may run with auto-reload and expose interactive docs, increasing attack surface and risk of sensitive information disclosure.
- Location:
  - `src/backend/core/config.py:25-33` (`app_env` and `debug` defaults)
  - `src/backend/core/config.py:170-174` (production check only enforces `jwt_secret`)
  - `src/backend/main.py:50-57` (`docs_url` and `redoc_url` tied to `settings.debug`)
  - `src/backend/main.py:127-132` (`uvicorn.run(..., reload=settings.debug)`)
- Fix (recommended):
  1. In `Settings.validate_startup()`, if `app_env == "production"`:
     - hard-fail if `debug` is true, or force it false and log a warning.
     - ensure Uvicorn reload is never enabled.
  2. Consider explicitly disabling docs in production regardless of `debug` (`docs_url=None`, `redoc_url=None`, and optionally `openapi_url=None`).

---

### S06-SEC-007 — Rate limiting keying may be incorrect behind proxies

- Severity: **Low/Medium** (environment-dependent)
- Impact (1 sentence): In proxy deployments, rate limiting may apply to the proxy IP (breaking clients) or, if switched to forwarded headers without trust controls, become spoofable.
- Location:
  - `src/backend/security/rate_limit_middleware.py:124-128` (`client_ip` from `scope["client"]`)
- Fix (recommended):
  - If deployed behind a reverse proxy, configure trusted proxy handling (Uvicorn proxy headers) and validate trusted sources; otherwise keep using `scope["client"]`.
  - Document the deployment requirement clearly (so operators don’t “fix” it by blindly trusting `X-Forwarded-For`).

---

### S06-SEC-008 — CI “security scan” is non-blocking (results can be ignored)

- Severity: **Low** (process risk)
- Impact (1 sentence): Vulnerabilities may ship because CI never fails on scan findings.
- Location:
  - `.github/workflows/ci.yml:69-97` (`continue-on-error: true` plus `|| true`)
- Fix (recommended):
  - Decide policy: fail builds on high/critical `pip-audit` findings and on high-confidence Bandit issues, while keeping lower severities as warnings.
  - Consider generating SARIF for GitHub code scanning, or at minimum posting a PR comment summary.

---

## Remediation plan (prioritized, for next agent)

1) **Lock down monitoring endpoints (S06-SEC-001)**
   - Decide policy by mode:
     - Local mode: allow detailed metrics.
     - Server mode: require auth (and ideally admin role) or disable entirely.
   - Update docs to match behavior.
   - Add tests that verify auth is enforced in server mode.

2) **Fix upload/body size controls (S06-SEC-002, S06-SEC-003)**
   - Replace import/upload “bypass” with a larger, explicit limit aligned to `max_import_file_size_mb`.
   - Ensure oversized streaming bodies return 413 from the middleware itself (no unhandled exceptions).
   - Add tests:
     - Oversize import with `Content-Length` → 413
     - Oversize import streaming (no `Content-Length`) → 413

3) **Harden backup restore against path traversal/tampering (S06-SEC-004)**
   - Add strict path validation for manifest entries.
   - Add unit tests for traversal attempts.
   - If backups are expected to move across trust boundaries, add manifest authenticity (signature/HMAC) and document key management.

4) **Production safety defaults (S06-SEC-006)**
   - Add startup validation that forbids `debug=True` when `app_env=production`.
   - Disable docs in production (or protect them).

5) **DoS resilience for health checks (S06-SEC-005)**
   - Remove metrics summary from unauthenticated `/health`, or cache/limit it.
   - Consider rate limiting `/health` with a generous but nonzero budget.

6) **CI security scan policy (S06-SEC-008)**
   - Convert scans into actionable output (fail on critical/high; upload artifacts for the rest).

