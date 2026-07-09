# Data & Migrations

**Owner:** Project Lead
**Refresh Trigger:** New migration added, or a model change isn't reflected in either Alembic chain

## Scope

SQLAlchemy models, the **dual** Alembic migration environments (`migrations/master/` for
profile-metadata/audit, `migrations/profile/` for per-profile encrypted vault schema — see
CLAUDE.md's "Dual migrations" invariant), and per-profile SQLCipher encryption.

## Start here

- [`../plans/implementation-log/2026-02-04_alembic-dual-migrations.md`](../plans/implementation-log/2026-02-04_alembic-dual-migrations.md) — dual-migration design (historical, but the mechanics still apply)
- [`docs/03_data_confidentiality_pipeline_plan.md`](../03_data_confidentiality_pipeline_plan.md) — data/confidentiality pipeline (shared with security)

## Related roles

- [`security-and-compliance.md`](security-and-compliance.md) — encryption boundaries, HIPAA controls
- [`backend-api.md`](backend-api.md) — the route layer that reads/writes through this data layer
