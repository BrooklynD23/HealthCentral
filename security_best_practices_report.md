# Security Best Practices Review — HealthCentral (Feb 23, 2026)

## Scope

Reviewed the following commits (static code review only):

- `2d78990` — docs: Fix drift in integration status and roadmap (DOC-DRIFT-002)
- `abb03ec` — feat: Add redaction pipeline for PII before external API calls (PRIV-RED-001)
- `80b33bd` — feat: Add bounding-box citations for extracted observations (OCR-BOX-001)
- `d27b295` — feat: Add extraction confidence indicators across UI surfaces (UX-CONF-001)
- `80d0e4c` — feat: Add PNG and SVG chart image export (EXPORT-CHART-001)
- `1ef425a` — feat: Add memory store CRUD API (ASSIST-MEM-001)
- `e1a301e` — feat: Add memory manager UI to settings page (ASSIST-MEM-002)
- `8613924` — feat: Integrate memory store into RAG context (ASSIST-MEM-003)
- `2d58395` — docs: Add specification for imaging/pathology/visit notes ingest (INGEST-EPIC-001)

Primary code paths reviewed:

- Backend: `src/backend/core/external_runner.py`, `src/backend/modules/redaction.py`, `src/backend/api/memory.py`, `src/backend/models/memory_item.py`, `src/backend/modules/rag.py`, `src/backend/api/documents.py`, `src/backend/api/observations.py`, `src/backend/core/config.py`
- Frontend: `src/frontend/src/components/MemoryManager.tsx`, `src/frontend/src/components/PageImageOverlay.tsx`, `src/frontend/src/services/memory.ts`, `src/frontend/src/services/documents.ts`

## Stack (as observed in repo)

- Backend: FastAPI + Pydantic v2 + SQLAlchemy; per-profile SQLCipher DBs; `httpx` for outbound LLM calls.
- Frontend: React + TypeScript (Vite), React Query.

## Executive Summary

Good security work in these commits:

- External LLM calls are centralized (`ExternalModelRunner`) and redaction happens *before* provider dispatch when enabled (`src/backend/core/external_runner.py:149`).  
- Memory CRUD endpoints enforce authentication and profile isolation checks (`src/backend/api/memory.py:89`, `src/backend/api/memory.py:167`).
- Document page images enforce document access checks and validate `document_id` format (`src/backend/api/documents.py:603`, `src/backend/api/documents.py:614`).

Main risks to address next:

1. **External API redaction defaults may still allow PHI (DOB/address) to leave the system.** (`src/backend/core/config.py:112`, `src/backend/modules/redaction.py:90`)
2. **Prompt-injection and resource-exhaustion risk from injecting memory items into prompts without sanitization/size bounds.** (`src/backend/modules/rag.py:821`, `src/backend/core/config.py:109`)

## Findings

### Critical

#### F-001 — External-API redaction defaults can leak DOB/address PHI

- **Severity:** Critical
- **Rule ID:** FASTAPI / Privacy boundary (outbound data exfiltration)
- **Location:**
  - Redaction defaults: `src/backend/core/config.py:112-115`
  - Rules for DOB/address are `strict`-only: `src/backend/modules/redaction.py:90-107`
  - Redaction is applied only when enabled: `src/backend/core/external_runner.py:149-164`
- **Evidence:**
  - `src/backend/core/config.py:114` defaults to `redaction_policy_level: str = "standard"`.
  - `src/backend/modules/redaction.py:91-107` shows `dob` and `address` rules have `policy_levels=frozenset({"strict"})`.
- **Impact:** If a user opts into external LLM usage, prompts containing DOB/address can be transmitted to third-party LLM providers even though “redaction is enabled”, creating PHI/PII exposure risk.
- **Fix (recommended):**
  - For any external provider call, default to **`strict`** redaction (at least in `production`) and treat weaker policies as an explicit, audited override.
  - Add startup validation to fail-fast on invalid `redaction_policy_level` and to log a clear warning when policy is below `strict` and external API is enabled.
- **False-positive notes:** If prompts never contain DOB/address, the practical risk is lower; however lab PDFs commonly contain DOB/address, and this control is explicitly intended to protect that trust boundary.

### High

#### F-002 — Redaction can be disabled for external calls (privacy control bypass)

- **Severity:** High
- **Rule ID:** FASTAPI / Outbound requests safety
- **Location:** `src/backend/core/external_runner.py:149-164`, `src/backend/core/config.py:113`
- **Evidence:** `src/backend/core/external_runner.py:150-163` only redacts prompts when `settings.redaction_enabled` is truthy.
- **Impact:** A configuration flip (or environment misconfiguration) can silently disable redaction and send full prompts externally.
- **Fix (recommended):**
  - Make redaction mandatory for external calls in `production` (or require an explicit “break-glass” flag with prominent logging/audit).
  - Emit a structured audit event when external API usage happens with redaction disabled.

#### F-003 — Memory-to-prompt injection is unsanitized (prompt-injection + rule-bypass risk)

- **Severity:** High
- **Rule ID:** LLM safety boundary (untrusted content in system prompt context)
- **Location:** `src/backend/modules/rag.py:794-834`, `src/backend/modules/rag.py:905-922`
- **Evidence:**
  - Memory lines are built from user-controlled `item.key`/`item.value` directly: `src/backend/modules/rag.py:823-830`.
  - History is filtered for prompt injection (`src/backend/modules/rag.py:450-481`) but memory items are not filtered.
- **Impact:** A stored memory item can embed adversarial instructions (or formatting tricks) that degrade citation discipline, safety rules, or output behavior—especially risky in a medical assistant context.
- **Fix (recommended):**
  - Apply the same `_contains_prompt_injection()` filtering used for `history` to memory content (or store memory as structured preferences and render into the prompt in a way that prevents “instruction-shaped” content from being treated as instructions).
  - Normalize/escape multiline values so they can’t break the intended “bullet” format (e.g., indent subsequent lines, or wrap in a fenced block).

#### F-004 — Memory prompt injection can cause resource exhaustion (cost/latency DoS)

- **Severity:** High
- **Rule ID:** FASTAPI / Abuse & resource controls
- **Location:**
  - Max items: `src/backend/core/config.py:109`
  - Max value length: `src/backend/api/memory.py:48`
  - All items are injected with no prompt budget: `src/backend/modules/rag.py:814-830`
- **Evidence:** `src/backend/api/memory.py:48` permits `value` up to `10_000` chars; `src/backend/core/config.py:109` allows up to `100` items.
- **Impact:** A single profile can generate extremely large prompts (up to ~1M chars) that increase inference cost, latency, and failure modes, and may be exploitable for denial-of-service (especially with external APIs).
- **Fix (recommended):**
  - Enforce a “memory context budget” (e.g., max total characters or max items injected per request) in `RAGModule._retrieve_memory_context()`; include most-recently-updated items first.
  - Consider adding per-profile quota + server-side truncation of `value` for prompt injection purposes (separate from storage limit).

### Medium

#### F-005 — Page image rendering endpoint is a CPU/memory hot path (DoS sensitivity)

- **Severity:** Medium
- **Rule ID:** FASTAPI / File handling & abuse controls
- **Location:** `src/backend/api/documents.py:591-657`
- **Evidence:** `src/backend/api/documents.py:634-639` renders a PDF page to a PNG at `resolution=150` on-demand per request.
- **Impact:** Even with global rate limiting, a user can repeatedly trigger expensive PDF rasterization, increasing CPU/memory usage.
- **Fix (recommended):**
  - Add lightweight caching (per `document_id` + `page_number` + resolution) or pre-render small thumbnails at ingest time.
  - Consider bounding resolution and adding an explicit timeout/guard for very large pages.
- **False-positive notes:** Your existing `RateLimitMiddleware` in `src/backend/main.py:82-89` helps; this is a defense-in-depth recommendation due to the inherent cost of rasterization.

#### F-006 — Data minimization: responses expose `profile_id` broadly

- **Severity:** Medium
- **Rule ID:** Privacy / Least data exposure
- **Location:**
  - Memory API: `src/backend/api/memory.py:59-67`
  - Documents API: `src/backend/api/documents.py:95-105`
  - Observations API: `src/backend/api/observations.py:92-112`
  - Frontend types rely on it: `src/frontend/src/services/types.ts:419-427`
- **Evidence:** Response DTOs include `profile_id` even though it is derivable from auth context.
- **Impact:** Increases the amount of sensitive identifier data available to the client and any client-side telemetry/logging, and slightly increases blast radius if a client compromise occurs.
- **Fix (recommended):** Remove `profile_id` from response models unless there is a clear client need; keep it server-side for access control.

### Low

#### F-007 — Cross-profile memory item existence leak (403 vs 404 distinction)

- **Severity:** Low
- **Rule ID:** FASTAPI / Authorization + information disclosure
- **Location:** `src/backend/api/memory.py:156-173`
- **Evidence:** The handler returns `403` when an `item_id` exists but belongs to another profile (`src/backend/api/memory.py:167-171`), and `404` otherwise (`src/backend/api/memory.py:161-166`).
- **Impact:** If an attacker ever obtains a valid `item_id`, they can confirm existence across profiles by the status code difference.
- **Fix (recommended):** Query by `(id, profile_id)` and always return `404` on misses; log authorization failures server-side if you still want that signal.

#### F-008 — Frontend page image loading currently relies on credentialed `<img>` requests

- **Severity:** Low (security) / Medium (reliability)
- **Rule ID:** Frontend auth transport consistency
- **Location:** `src/frontend/src/components/PageImageOverlay.tsx:98-109`, `src/frontend/src/services/api.ts:26-31`
- **Evidence:** API calls use an `Authorization: Bearer ...` header (`src/frontend/src/services/api.ts:26-31`), but `<img>` requests can’t attach that header and instead set `crossOrigin="use-credentials"` (`src/frontend/src/components/PageImageOverlay.tsx:107-109`).
- **Impact:** Teams often “fix” this by putting tokens in URLs (bad) or shifting to cookies (requires CSRF considerations). This is a common foot-gun when adding binary endpoints consumed by `<img>`.
- **Fix (recommended):** Fetch the image as a blob via `fetch` with the Authorization header and render via `URL.createObjectURL(blob)`; avoid putting tokens into query strings.

## Suggested Next Steps

- Decide the privacy bar for external LLM providers and set redaction defaults accordingly (recommend: `strict` for any external call in `production`).
- Add a prompt-budget cap for memory injection and apply injection filtering/safe formatting.
- Consider removing `profile_id` from public API responses for data minimization.

