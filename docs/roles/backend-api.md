# Backend / API

**Owner:** Project Lead
**Refresh Trigger:** New route group added, or `docs/api/endpoints.md` drifts from mounted routers

## Scope

FastAPI application (`src/backend/`), route handlers under `src/backend/api/`, business-logic modules
under `src/backend/modules/`, and per-profile SQLCipher-encrypted vault access via `ProfileDbSession`.

## Start here

- [`docs/01_backend_architecture_plan.md`](../01_backend_architecture_plan.md) — architecture plan
- [`docs/api/endpoints.md`](../api/endpoints.md) — mounted route inventory (source of truth)
- [`docs/api/authentication.md`](../api/authentication.md) — auth flow
- [`docs/api/error-codes.md`](../api/error-codes.md) — error response conventions
- [`docs/api/integration-guide.md`](../api/integration-guide.md) — client integration guide
- [`../../skills/healthcentral-backend/SKILL.md`](../../skills/healthcentral-backend/SKILL.md) — project skill for backend work

## Related roles

- [`data-and-migrations.md`](data-and-migrations.md) — the models/DB layer this reads and writes
- [`security-and-compliance.md`](security-and-compliance.md) — auth, encryption, audit logging invariants
