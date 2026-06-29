# Exploration Summary — agent overhaul integration points

**Last Updated:** 2026-06-23
**Owner:** [Owner] (solo client/engineer)
**Refresh Trigger:** A touched module below is renamed/moved, or a new integration
point is discovered during a sprint

> Merged, de-duplicated output of five read-only explorer passes (STEP 1), one per
> concern. Each pass returned `{files, current behavior, integration points, risks,
> open questions}`. Conflicts were routed to [RECONCILIATION.md](RECONCILIATION.md);
> what remains here is the load-bearing map a sprint can build against. File paths
> are relative to repo root.

---

## A. `/assistant/` RAG path + model serving

**Files:** `src/backend/api/assistant.py` (route handlers) ·
`src/backend/modules/rag.py` (`RAGModule.query`, `retrieve`, `compose_prompt`,
`validate_response`) · `modules/model_selector.py` (tiered GGUF loading + fallback) ·
`core/model_runner.py` (llama-cpp wrapper, async via `to_thread`) ·
`core/external_runner.py` (`get_runner_for_request`, opt-in external APIs) ·
`modules/faithfulness.py`, `modules/source_authority.py`, `modules/interpret_safety.py`.

**Current behavior:** `POST /assistant/chat` → `ChatRequest{question, selected_analytes,
enable_verification}` → `RAGModule.query()` retrieves user-doc + reference chunks,
composes a citation-templated prompt (`[DOCUMENT:n]`/`[REFERENCE:n]`), one model call
at low temperature, then `validate_response()` enforces citations on report-facts,
scores claims (`ClaimExtractor` → `SourceAuthorityScorer` → `VerifierAgent` →
`FaithfulnessScorer`) and returns `ChatResponse{segments, full_response, verification}`.

**Integration points:**
- **Flag gate** sits at the top of the chat handler / `RAGModule.query()`: when
  `agent_enabled` is on, branch into the agent graph; when off, the existing
  single-shot path runs untouched.
- The agent **reuses** `retrieve`, the runner resolution (`get_runner_for_request`),
  and the claim/faithfulness scorers as building blocks for tools and the draft node.
- Response schema extends additively to a discriminated union `answer | abstain |
  escalate` (see Phase 5 contract); flag-OFF shape stays identical.

**Risks:** context-window overflow across multi-step loops; citation/chunk-id
consistency if the loop re-retrieves; silent model-fallback degradation needs to be
visible to `reflect`. **Open Q:** does the agent observe raw ranked chunks+scores or
only validated segments?

## B. Data layer — vaults, master/profile split, migrations

**Files:** `core/database.py` (master `Base`) · `core/profile_database.py`
(`PerProfileDatabaseManager`, `ProfileDatabaseConnection`, SQLCipher PRAGMA key) ·
`core/auth.py` (`RequireAuth`, `ProfileDbSession` dependency) · `core/migrations.py`
(dual-env baseline-stamping runners) · `models/observation.py` (`user_verified`,
`verified_at`), `models/document.py` (`status`), `models/chunk.py`, `models/embedding.py` ·
`alembic.ini` (`[master]`/`[profile]`), `migrations/master/env.py`,
`migrations/profile/env.py`.

**Current behavior:** master DB holds profiles/audit/knowledge; each profile gets a
SQLCipher vault at `data/vaults/{profile_id}/vault.db`, unlocked on login, cached in a
singleton manager, injected into handlers as `ProfileDbSession`. Master migrations run
at startup; profile migrations on vault open; pre-existing DBs are **stamped** not
migrated.

**Integration points:** a read-only agent tool takes `RequireAuth` + `ProfileDbSession`
and runs `select(Observation).where(Observation.user_verified == True)` scoped to the
session's profile. Chunks filter via parent `Document.status == "verified"` (chunks have
no own verified column — RECONCILIATION R-5).

**Risks:** best-effort key zeroing; baseline-stamp race; dev-only unencrypted fallback
path exists. **Open Q:** does `compute_trend` need date-range/confidence filters beyond
"verified"?

## C. Middleware / security / audit / monitoring

**Files:** `main.py` (middleware registration) · `security/audit_middleware.py`,
`security/input_validator.py`, `security/rate_limit_middleware.py`,
`security/security_headers.py` · `core/audit.py` (`create_audit_log`) ·
`models/audit.py` (`AuditLog`) · `monitoring/metrics.py` (`MetricsCollector`, ring
buffer, p50/p95/p99), `monitoring/correlation.py`, `monitoring/timing_middleware.py`,
`monitoring/health.py` (`/monitoring/metrics`) · `modules/redaction.py`.

**Current behavior:** stack order CORS → correlation-id → security-headers →
rate-limit → input-validation → security-audit → timing. Audit persists to
`audit_logs` (master) with `event_type, action, profile_id, entity_type, entity_id,
details_json, timestamp`. Redaction: `RedactionEngine(policy_level).redact(text)` →
`RedactionResult` (no plaintext stored), today invoked on the external-runner path.

**Integration points:**
- **Audit emit (every node):** `await create_audit_log(db, event_type="agent.<node>",
  action=..., profile_id=..., entity_type="agent_node", entity_id=run_id,
  details={...})`. Read GETs are NOT auto-audited (R-4) — emit explicitly.
- **Redaction gate:** call `RedactionEngine(...).redact()` on any payload before it
  reaches the external runner; nothing leaves without passing.
- **Per-node timing:** record into `MetricsCollector` keyed `agent.<node>`; surfaces in
  `/monitoring/metrics` p95.

**Risks:** `details_json` not auto-redacted (don't dump raw PHI prompts there);
metrics ring buffer caps at 10k. **Open Q:** store full prompt/response in audit
details or a separate encrypted sink?

## D. Tests & CI

**Files:** `tests/conftest.py` (`TEST_MODE=1`, `DATABASE_ENCRYPTION_REQUIRED=false`,
sandbox temp-dir fallback) · `tests/test_interpret_safety_adversarial.py`,
`test_phase4_ai_safety.py`, `test_redaction.py`, `test_rag_pipeline.py` ·
`.github/workflows/ci.yml` · `scripts/run-backend-tests.sh`,
`scripts/repo_hygiene_check.py`, `scripts/docs_lint.py`.

**Current behavior:** CI jobs `docs-lint`, `backend-tests`
(`bash scripts/run-backend-tests.sh -q`), `frontend-tests`, `security-scan`,
`e2e-tests`. Triggers on push to `main`/`Security-Revamp-*` and PRs to `main`. Safety
tests use direct-import fixtures + boolean assertions on guard results;
parametrize-by-policy is the redaction pattern.

**Integration points:** new agent tests live under `src/backend/tests/agent/`
(self-contained, reusing the adversarial-assertion and parametrize patterns). The
agent-eval CI gate (Phase 6) adds a job running `tests/agent/` and **fails the PR if
advice-leakage > 0 or groundedness < 100%**. Golden cases stored as JSON under
`tests/agent/golden/`. New docs must satisfy `docs_lint` (canonical → `Last Updated`,
`Owner`, `Refresh Trigger`; historical → banner + inactive-tracker language).

**Risks:** no shared guard/RAG fixtures today (per-file imports); sandbox temp-dir
variance; `TEST_MODE` bypasses auth, so agent tests must mock the profile session.
**Open Q:** golden cases checked-in JSON vs generated — decided: **checked-in JSON**.

## E. Frontend assistant surface

**Files:** `src/frontend/src/services/assistant.ts` (`sendChatMessage`,
`useSendMessage`, `ChatRequest`/`ChatResponse`/`Citation`/`VerificationInfo` types) ·
`src/frontend/src/services/api.ts` (`apiPost`/`apiGet`) ·
`src/frontend/src/services/modelSettings.ts` (`ExternalApiSettings`) ·
`src/frontend/src/pages/ExplainAssistant.tsx` (renders message + citation pills +
verification badge) · `src/frontend/tsconfig.json` (strict, `noEmit`).

**Current behavior:** `useSendMessage()` posts to `/assistant/chat`, renders
`segments[]` + citations + a verified-claims/faithfulness badge. No agent flags or
terminal-state UI exist.

**Integration points:** when `agent_enabled` is off the client is **unchanged**; when
on, `ChatResponse` becomes a discriminated union and abstain/escalate render as
distinct, citation-less message blocks. Type extensions must be additive so strict TS
catches unhandled branches. **Open Q:** abstain/escalate as new response types vs new
`segment_type` values — decided in Phase 5: **discriminated union on a `terminal` field**.

---

## Cross-cutting conclusions feeding the PRD/phases

1. The flag boundary is a single branch point in the chat handler — cheap to keep
   `main` behavior pristine (invariant #2).
2. Every governance primitive the overhaul needs (audit, redaction, monitoring,
   verified-flag) **already exists** — the work is wiring them into nodes mechanically,
   not building them.
3. The biggest behavioral change with blast radius is the terminal-contract response
   shape (B/E), so cutover (Phase 5) carries the frontend contract and the flag-OFF
   regression test.
