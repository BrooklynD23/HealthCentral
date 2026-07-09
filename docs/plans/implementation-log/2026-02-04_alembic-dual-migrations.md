# Date
2026-02-04

> Historical Reference: this plan predates later implementation work and contains completed items.
> Use `docs/features/TASK_LIST.md` for active remaining tasks.

# Feature
Dual Alembic migration system (master + per-profile SQLCipher vaults)

# Status
Completed

# Phase
0 (Infrastructure / reliability)

# Overview
Add Alembic migration support to HealthCentral’s dual-database architecture:
- Master DB (non-sensitive): `settings.app_data_path / "healthcentral.db"`
- Per-profile DBs (sensitive, SQLCipher): `settings.app_data_path / "vaults" / {profile_id} / "vault.db"`

This replaces runtime `metadata.create_all()` schema creation with explicit, versioned migrations.

# Goals
- Maintain two independent migration histories (master vs profile vault).
- Support safe rollout to existing users with already-created tables (baseline stamping).
- Support SQLCipher-encrypted vault migrations (PRAGMA key applied before any Alembic work).
- Avoid blocking the FastAPI event loop during migrations.

# Non-goals
- PostgreSQL migrations (future work).
- Automatic “migrate all vaults” when vault keys require user-provided passwords (only DPAPI-only best-effort is feasible).
- Data backfills beyond what schema migrations require.

# Current repo constraints (must align with implementation)
- The backend is async (SQLAlchemy `create_async_engine`); Alembic is typically sync.
- Today, schemas are created via:
  - `src/backend/core/database.py:init_database()` → `Base.metadata.create_all`
  - `src/backend/core/profile_database.py:open_profile_database()` → `ProfileDatabaseBase.metadata.create_all`
- A master DB already exists in-repo at `src/backend/data/healthcentral.db` (dev artifact).

# Rollout strategy (safe path)
1) Introduce Alembic envs + initial revisions for both DBs.
2) Add baseline logic:
   - If tables exist but `alembic_version` does not, **stamp head** (don’t run `001_initial_schema`).
   - If DB is empty, **upgrade head** (create schema via migrations).
3) Cut over runtime:
   - Remove/disable `create_all` calls in normal startup/login flows.
4) Wire migrations:
   - Master migrations on startup (in a thread).
   - Profile migrations on vault open (in a thread), using the unsealed vault key.

# Implementation tasks

## Task A — Dependency
- [ ] Add `alembic>=1.13.0` to `src/backend/requirements.txt`.

## Task B — Alembic config + folder structure
- [ ] Create `src/backend/alembic.ini`.
- [ ] Create `src/backend/migrations/master/` and `src/backend/migrations/profile/`:
  - [ ] `env.py`
  - [ ] `script.py.mako`
  - [ ] `versions/`

Decision: Use Alembic “named configs” (`-n master` / `-n profile`) OR override `script_location` programmatically; avoid mixing both patterns.

## Task C — Master env.py (sync engine; offline + online)
- [ ] `target_metadata = Base.metadata` from `core.database`.
- [ ] Ensure master models are imported so metadata is populated:
  - `models.profile`, `models.audit`, `models.knowledge_base`
- [ ] Build a sync URL:
  - Convert `settings.database_url` from `sqlite+aiosqlite:///...` to `sqlite:///...` for Alembic.

## Task D — Profile env.py (SQLCipher-aware)
- [ ] `target_metadata = ProfileDatabaseBase.metadata` from `core.profile_database`.
- [ ] Ensure profile models are imported so metadata is populated:
  - `models.document`, `models.observation`, `models.chunk`, `models.embedding`,
    `models.interpretation`, `models.medication`, `models.model_settings`
- [ ] Accept runtime attributes from the Config object:
  - `vault_path` (Path-like / string)
  - `encryption_key` (bytes)
- [ ] Create a sync engine with SQLCipher DBAPI selection:
  - `module=get_sqlcipher_module()` from `core.sqlcipher_driver`
- [ ] On connect, execute `PRAGMA key = "x'<HEX>'"` **before** any Alembic work.
  - Key formatting must match `PerProfileDatabaseManager._key_to_hex()` semantics.
- [ ] If `settings.database_encryption_required` is true but SQLCipher isn’t available, fail fast.

## Task E — Initial revisions (schema-only)
- [ ] Add `migrations/master/versions/001_initial_schema.py` with master tables:
  - `profiles`, `audit_logs`, `biomarker_knowledge`, `intervention_mappings`, `biomarker_relationships`
- [ ] Add `migrations/profile/versions/001_initial_schema.py` with profile tables:
  - `documents`, `observations`, `chunks`, `embeddings`,
    `lab_interpretations`, `panel_interpretations`,
    `medications`, `medication_schedules`, `doses_taken`, `adherence_patterns`, `reminder_logs`,
    `user_model_settings`

Note: These revisions are correct for new installs. Existing DBs should be baselined via stamping.

## Task F — Migration utilities (baseline + thread-safe use)
- [ ] Create `src/backend/core/migrations.py` with:
  - `run_master_migrations()`:
    - Detect existing schema without `alembic_version` → `stamp head`
    - Else → `upgrade head`
  - `run_profile_migration(vault_path: Path, encryption_key: bytes)`:
    - Same baseline behavior, but able to open SQLCipher DB
  - Async wrappers that call Alembic via `asyncio.to_thread(...)` for use in startup/login.

Baseline detection (simple and robust for SQLite):
- Check if any expected tables exist in `sqlite_master`.
- Check if `alembic_version` table exists.

## Task G — Runtime cutover (remove create_all)
- [ ] Update `src/backend/core/database.py:init_database()`:
  - Keep directory creation and SQLCipher availability checks.
  - Remove `Base.metadata.create_all` (schema creation now via Alembic).
- [ ] Update `src/backend/core/profile_database.py:open_profile_database()`:
  - Remove `_init_profile_schema()` (or keep for tests only).
  - Run vault migrations before returning the connection.

## Task H — FastAPI lifespan integration (master only)
- [ ] Update `src/backend/main.py` lifespan:
  - Run master migrations on startup (threaded; non-blocking).

## Task I — Profile migration on vault open (on-demand)
- [ ] Update `src/backend/core/profile_database.py`:
  - After key unsealing and `db_path` resolution, run profile migration (threaded).

## Task J — CLI tool
- [ ] Create `src/backend/scripts/migrate.py`:
  - `master`
  - `profile --profile-id ... --password ...` (or prompt)
  - Optional: `profiles --dpapi-only` best-effort batch mode (no password prompting).

# Acceptance criteria

## AC1 — New install creates schemas via Alembic
- Starting the backend on a clean data directory results in:
  - Master DB has all master tables + `alembic_version`
  - New profile vault created/opened has all profile tables + `alembic_version`
- No `metadata.create_all()` is executed in normal runtime flows.

## AC2 — Existing master DB baselines safely
- With a pre-existing master DB containing tables but no `alembic_version`, startup:
  - Does not error with “table already exists”
  - Produces `alembic_version` stamped to head
  - Leaves data intact

## AC3 — Existing encrypted vault baselines safely
- With a pre-existing encrypted vault DB containing tables but no `alembic_version`, opening the profile:
  - Applies PRAGMA key successfully
  - Stamps head (does not attempt to re-create tables)
  - Leaves data intact

## AC4 — Non-blocking startup/login
- Migration execution does not block the FastAPI event loop:
  - Alembic runs in a background thread via `asyncio.to_thread`.

## AC5 — Clear failure modes for missing SQLCipher
- If `settings.database_encryption_required` is true and SQLCipher isn’t available:
  - Profile migrations and profile DB open fail with a clear error message.

# Verification matrix

## Automated tests (minimum)
- [ ] Unit: baseline detection chooses `stamp` vs `upgrade` appropriately (master).
- [ ] Unit/Integration: profile migration path requires SQLCipher when encryption required (skip if SQLCipher unavailable in test env).

## Manual checks (PowerShell)
From repo root:
- Master migrate:
  - `cd src\\backend`
  - `python -m scripts.migrate master`
- Master status:
  - `alembic -c alembic.ini -n master current`
- Start backend:
  - `python -m uvicorn main:app --reload`

# Risks & mitigations
- Risk: Existing DBs already have tables created via `create_all`, so initial Alembic revisions will conflict.
  - Mitigation: baseline stamp logic before removing `create_all`.
- Risk: Encrypted vaults can’t be opened by stdlib `sqlite3`.
  - Mitigation: profile Alembic env uses `get_sqlcipher_module()` and sets PRAGMA key on connect.
- Risk: Blocking async event loop during migrations.
  - Mitigation: run Alembic calls in `asyncio.to_thread`.

