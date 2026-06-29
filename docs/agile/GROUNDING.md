# Grounding — Agent Overhaul

**Last Updated:** 2026-06-23
**Owner:** [Owner] (solo client/engineer)
**Refresh Trigger:** Live route surface, data-layer split, middleware stack, or
feature-flag mechanism changes on `main`

> This is the **ground truth** the PM-orchestrator pass stood on before writing
> any PRD/phase/sprint doc (STEP 0). It records what HealthCentral does **today**
> on `main`, so every downstream artifact can be checked against reality rather
> than against the plan. Deeper exploration of integration points lives in
> [EXPLORATION_SUMMARY.md](EXPLORATION_SUMMARY.md); conflicts surfaced during
> grounding are routed to [RECONCILIATION.md](RECONCILIATION.md).

---

## 1. Branch reality

- **Working branch:** `claude/agent-overhaul-prd-sprints-2vgb5h` (the environment's
  designated development branch). The planning bundle refers to `fix/agent-overhaul`;
  no such branch exists in this clone. Treated as the same logical workstream —
  see RECONCILIATION.md item R-1.
- `main` is never modified. `git status` clean at start of pass.

## 2. Architecture (from README + `docs/01_backend_architecture_plan.md`)

- **Local-first desktop app.** FastAPI backend bound to `127.0.0.1` only (never
  `0.0.0.0`); Vite/React frontend over same-origin `/api/v1` (dev proxy) or
  loopback HTTP (packaged). JWT Bearer (HS256) auth with per-profile vault unlock
  gating PHI access. No outbound network calls by default.
- **Module layout:** feature logic under `src/backend/modules/<feature>/`; routes
  mount under `/api/v1/<group>/`. Every request traverses the middleware stack
  (CORS → correlation ID → security headers → rate limit → input validation →
  security audit → timing). All request/response bodies are Pydantic-typed.
- **LLM serving:** local GGUF via `llama-cpp-python` is the default and must work
  offline; external LLMs are opt-in behind model settings **and** the redaction
  gate. Model tiers route by task (`model_selector.py`), selection kept in model
  settings, not hardcoded.

## 3. Data layer (the local-first contract)

- **Master DB** (SQLite, unencrypted): `Profile`, `AuditLog`, knowledge base.
  **Never holds PHI.**
- **Profile DB** (per-profile SQLCipher, AES-256): all clinical data — `Document`,
  `Observation`, `Chunk`, `Embedding`, interpretations, medications. Opened only on
  vault unlock; session-bound.
- **Verified flag:** `Observation.user_verified: bool` (default `False`) +
  `Observation.verified_at`. The agent's read-only tools must filter
  `user_verified == True` for the current profile. `Chunk`/`Embedding` carry no
  own verified flag — they inherit it via the parent `Document.status`.
- **Migrations (dual-environment Alembic):** master migrations run at app startup;
  profile migrations run on vault open; baseline detection **stamps** pre-existing
  DBs instead of migrating. A change touching both schemas ships migrations for both.

## 4. Live `/assistant/` surface (today = single-shot RAG)

From `docs/api/endpoints.md` (the live route source of truth), under `/api/v1`:

| Method | Path | Auth |
|---|---|---|
| POST | `/assistant/chat` | Yes |
| GET | `/assistant/test-intent/{analyte}` | Yes |
| GET | `/assistant/glossary/{term}` | Yes |
| GET | `/assistant/verification-status` | Yes |

`POST /assistant/chat` today: retrieve context (`modules/rag.py`) → compose a
citation-templated prompt → one model call → validate (citations present, report
facts grounded, no diagnosis/treatment) → return a `ChatResponse` of segments +
`VerificationInfo`. **One retrieval pass, one model call.** No abstain/escalate
terminal; no multi-step loop.

## 5. Governance primitives already present (the overhaul reuses, never replaces)

- **Audit:** `core.audit.create_audit_log(db, event_type, action, profile_id,
  entity_type, entity_id, details, ...)` → `AuditLog` row in master DB. The agent's
  per-node audit events emit through this.
- **PHI redaction:** `modules/redaction.py` → `RedactionEngine(policy_level).redact(text)`
  returning a `RedactionResult` (never stores plaintext). Currently invoked on the
  external-runner path; the agent's external-LLM tool path inherits it unchanged.
- **Monitoring:** `monitoring/` ring-buffer metrics with p50/p95/p99 and a
  `/api/v1/monitoring/metrics` dashboard; per-route timing middleware. Per-node
  agent timing surfaces here (Sprint 5).
- **Safety today:** `modules/interpret_safety.py` prohibited-pattern filters +
  verification-status display. Strong but largely prompt-anchored — the overhaul
  makes it a structural guard **node** (E2 / Phase 3).

## 6. Feature-flag mechanism

Model settings (`/api/v1/settings/model*`, `modules/model_selector.py` +
settings store) is the existing place tier/external-API toggles live. The new
`agent_enabled` flag lands there, **defaults OFF**, and when off `/assistant/chat`
must behave byte-for-byte as the legacy single-shot path.

## 7. Tests & CI baseline

- pytest under `src/backend/tests/`; `tests/conftest.py` sets `TEST_MODE=1` and
  `DATABASE_ENCRYPTION_REQUIRED=false` for the sandbox. Safety patterns to reuse:
  `test_interpret_safety_adversarial.py`, `test_phase4_ai_safety.py`,
  `test_redaction.py`, `test_rag_pipeline.py`.
- CI: `.github/workflows/ci.yml` runs `docs-lint`, `backend-tests`
  (`bash scripts/run-backend-tests.sh -q`), `frontend-tests`, `security-scan`,
  `e2e-tests`. The agent-eval gate (Phase 6 / S6) slots in as a new job.
- Proof bundle: `scripts/repo_hygiene_check.py`, `scripts/docs_lint.py`, frontend
  `tsc --noEmit`, pytest. **Caveat:** the maintained `.wsl-pytest-venv` is
  Windows-pathed and unusable in this Linux container (RECONCILIATION R-2).

## 8. Invariants confirmed against the live code (non-negotiable downstream)

1. Agent is **read-only** over clinical data; only the human-verification flow writes.
2. All new behavior behind `agent_enabled`; `main` behavior unchanged when off.
3. Local-first: loop runs offline; external LLMs opt-in **and** behind redaction.
4. Every new route reflected in `docs/api/endpoints.md` in the same change.
5. Governance is mechanical (code), never prompt-only.
6. Success metrics are fixed (AGILE_PLAN §1 / audience Report 0) — reused, not redefined.
