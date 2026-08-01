---
name: healthcentral-backend
description: FastAPI backend and data conventions for the HealthCentral repo. Use whenever creating or modifying backend routes, feature modules under src/backend/modules/, SQLAlchemy models, Pydantic schemas, the SQLCipher per-profile vault, Alembic dual-environment migrations, the security/monitoring middleware stack, LLMOps concerns (semantic cache, model tiers, llama.cpp serving, timing/token tracking), or the contributor proof bundle. Triggers include work mentioning "FastAPI route", "modules/", "SQLCipher", "vault", "Alembic migration", "model tier", "semantic cache", "endpoints.md", or "proof bundle".
---

# HealthCentral Backend — conventions

Operational summary for backend work. The README architecture section and
`docs/01_backend_architecture_plan.md` are the deeper authority; `docs/api/endpoints.md`
is the LIVE route source of truth (`05_backend_integration_status.md` is historical
audit context only — do not treat it as the tracker).

## Module & route conventions

- Feature logic lives under `src/backend/modules/<feature>/`; routes mount under
  `/api/v1/<group>/`. New endpoints must be reflected in `docs/api/endpoints.md`
  in the same change — it is the source of truth, not the code alone.
- Every request passes the middleware stack: CORS, correlation IDs, security
  headers, rate limiting, input validation, security audit logging, timing. Don't
  add routes that sidestep it.
- All request/response bodies are Pydantic-typed. No untyped dict payloads.

## Data & encryption (the local-first contract)

- **Master DB** (SQLite, unencrypted): profiles, audit logs, knowledge base.
- **Profile DB** (per-profile SQLCipher, AES-256): all PHI / clinical data, opened
  only on vault unlock, session-bound.
- Documents stored as AES-GCM files under the per-profile vault dir.
- NEVER write PHI to the master DB. NEVER assume `DATABASE_ENCRYPTION_REQUIRED=false`
  in anything but a dev convenience path — production default stays encrypted.

## Migrations (dual-environment Alembic)

- Master migrations run on app startup; profile migrations run on vault open.
- Baseline detection stamps pre-existing DBs instead of migrating — preserve this
  so existing installs don't hit "table already exists".
- Add migrations for both environments when a change touches both schemas.

## LLMOps conventions

- Local GGUF via llama-cpp-python is the default and must work offline. External
  LLMs are opt-in, behind model settings AND the redaction gate.
- Model tiers route by task; keep tier selection in model settings, not hardcoded.
- Semantic cache keys on `(question, profile_version)` and invalidates when new
  verified data lands — a stale cached explanation of changed data is a correctness bug.
- Track per-node timing/tokens and surface p95 in the monitoring dashboard.

## Proof bundle (run from repo root, WSL/Linux interpreter)

Before merge-sensitive work, run the maintained bundle:
`python3 scripts/repo_hygiene_check.py` · `python3 scripts/docs_lint.py` ·
frontend type-check (`npx --prefix src/frontend tsc --noEmit ...`) ·
`PYTHONPATH=src/backend ./.wsl-pytest-venv/bin/python -m pytest <relevant suites>`.
Run `git status --short` first; clear local-only scratch (`PLAN.md`, `HANDOFF-*.md`,
`*_report*.md`, `.bg-shell/`, `.wsl-pytest-venv/`) rather than committing it.

## Never

Add a route missing from `endpoints.md` · bypass the middleware stack · write PHI to
master DB · ship a one-environment migration for a two-environment change · hardcode
a model tier · cache without profile-version invalidation · commit root scratch files.
