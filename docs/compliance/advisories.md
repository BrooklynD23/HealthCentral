# Security & Compliance Advisories

This document records security/observability issues discovered in HealthCentral
that affect compliance posture, along with their resolution and operational
guidance.

---

## ADV-2026-001 — Audit logging silently suppressed after database migrations

**Status:** Resolved
**Severity:** Medium (observability / audit-trail integrity)
**Affected area:** Audit logging (`SECURITY_AUDIT`, including break-glass trails)

### Summary

Database migrations run in-process via Alembic at two points in the application
lifecycle:

- **App startup** — `run_master_migrations_async()` in the FastAPI `lifespan`
  hook (`src/backend/main.py`).
- **Every profile-vault open** — `run_profile_migration_async()` invoked from
  `src/backend/core/profile_database.py`.

Alembic's `env.py` applies logging configuration from `alembic.ini` via
`logging.config.fileConfig()`. That function defaults to
`disable_existing_loggers=True`, which **disables every logger not explicitly
named in the ini's `[loggers]` section**. `alembic.ini` declares only `root`,
`sqlalchemy`, and `alembic` — so all application loggers (`core.*`,
`security.*`, `modules.*`, and critically `SECURITY_AUDIT`) were silently
disabled the first time a migration ran.

### Impact

In affected builds, audit log records — including HIPAA-relevant security audit
events and break-glass access trails — could be **silently dropped** after the
first migration in a process. Because migrations run at startup and on every
profile open, this affected normal operation, not just edge cases. No data was
exposed; the issue is one of **missing audit evidence**, which is itself a
compliance concern (HIPAA §164.312(b) audit controls).

### Resolution

Both Alembic environments now pass `disable_existing_loggers=False`:

- `src/backend/migrations/master/env.py`
- `src/backend/migrations/profile/env.py`

A regression test guards the fix:
`src/backend/tests/test_migration_logging_not_disabled.py` asserts that an
application logger (including `SECURITY_AUDIT`) remains enabled after a migration
runs. The test fails if `disable_existing_loggers` reverts to the default.

### Operational guidance

- For any deployment built before this fix, treat audit-log completeness as
  **not guaranteed** for sessions following an in-process migration. Audit
  evidence from those builds should not be relied upon as a complete record.
- After upgrading to a build containing this fix, verify audit output by
  confirming `SECURITY_AUDIT` entries appear in logs following a profile open.
