# Backend Structure

**Last Updated:** 2026-11-06 (DOCS-AUDIT-1106: profile head `018_ocr_opt_in`, chain counts, vault table list, `model_selector` reachability)
**Owner:** Project Lead
**Refresh Trigger:** Middleware order changes, a router is added/removed, or a migration chain gains a head

Part of the [architecture diagram set](README.md).

---

## Request lifecycle

Every request crosses the same middleware chain before it reaches a route. The
order is defined in `src/backend/main.py` and matters: cheap rejections happen
before expensive work. Audit **rows** are written by the route handlers (through
`core.audit`), not by middleware: `SecurityAuditMiddleware` writes an app-log line
for each POST, PUT, PATCH and DELETE only.

```mermaid
flowchart TD
    REQ["Incoming request"] --> CORS["CORSMiddleware<br/><i>explicit allow_headers, never *</i>"]
    CORS --> CID["CorrelationIdMiddleware<br/>attaches a request id"]
    CID --> SEC["SecurityHeadersMiddleware"]
    SEC --> RATE["RateLimitMiddleware<br/>sliding window"]
    RATE --> VAL["InputValidationMiddleware<br/>path/query sanity, body size → 413"]
    VAL --> AUD["SecurityAuditMiddleware<br/>app log only, mutating methods<br/>(audit_security_events_to_db is passed but never read)"]
    AUD --> TIME["TimingMiddleware<br/>p50/p95/p99"]
    TIME --> ROUTE["Route handler"]

    ROUTE --> AUTH{"requires auth?"}
    AUTH -->|yes| JWT["require_auth / require_profile_access<br/>JWT + revocation list"]
    AUTH -->|"no — /health, list and create profiles,<br/>login, unlock, recover"| SKIP[" "]
    JWT --> PDB["ProfileDbSession<br/><b>the only way to profile data</b>"]

    PDB --> WORK["modules/ feature logic"]
    WORK --> AUDROW["core.audit.create_audit_log<br/>allowlist-scrubbed"]
    AUDROW --> MASTER[("master DB")]
    WORK --> VAULTDB[("per-profile SQLCipher DB")]

    style VAL fill:#e65100,stroke:#ff9800,color:#fff
    style PDB fill:#1b5e20,stroke:#66bb6a,color:#fff
    style AUDROW fill:#4a148c,stroke:#ba68c8,color:#fff
```

Two nodes carry invariants rather than just behaviour:

- **`ProfileDbSession`** is the only sanctioned route to patient data. Querying
  profile data through the master `get_db()` breaks per-profile isolation.
- **`create_audit_log`** is a single choke point on purpose. Every `log_*_event`
  helper and every agent audit event passes through it, so the PHI allowlist
  cannot be bypassed by a new call site.

`InputValidationMiddleware` is highlighted because it is the one that returns
before the app runs: oversized bodies get a clean 413 on both the
`Content-Length` path and the streaming path (`_BodyTooLargeError`).

## Module dependency direction

```mermaid
flowchart TD
    subgraph api["api/ — 19 routers"]
        direction LR
        A1["documents · observations · assistant"]
        A2["timeline · care_tasks · pinboards · search"]
        A3["export · medications · med_reconcile"]
        A4["profiles · memory · feedback · model_settings · donation"]
        A5["interpretations · notifications · gamification · backup"]
    end

    subgraph modules["modules/ — feature logic"]
        direction LR
        M1["ingest · extract* · import_structured · document_classifier<br/>normalize · chunking · embeddings · glossary · test_intent"]
        M2["rag · agent/ · interpret · knowledge_loader · recommend<br/>model_selector · hardware_detection · model_integrity"]
        M3["timeline · care_tasks · highlights · search · med_reconcile"]
        M4["export · fhir_export · rl_dataset"]
        M5["backup_scheduler · notification_scheduler · platform_notifications<br/>adherence_patterns · message_generator · streak_engine · badge_evaluator"]
        SAFE["<b>safety</b><br/>redaction · faithfulness · verifier_agent · interpret_safety<br/>claim_extractor · source_authority"]
    end

    subgraph core["core/ — infrastructure"]
        direction LR
        C1["config · time · security · auth<br/>token_revocation · rate_limiter"]
        C2["database · profile_database · migrations<br/>sqlcipher_driver · audit · denial_audit"]
        C3["model_runner → llm/factory → providers"]
        C4["external_runner (D12) · document_crypto"]
    end

    api --> modules --> core
    api --> core
    modules --> SAFE
    api -.->|"model_settings: provider switch only, no generation"| C3
    api -.->|"assistant, interpretations: get_runner_for_request"| C4

    style SAFE fill:#4a148c,stroke:#ba68c8,color:#fff
```

Rules this diagram encodes:

- Dependencies point **downward** by design: `api/` → `modules/` → `core/`,
  and `api/` also imports `core/` directly (auth dependencies, audit helpers,
  sessions).
  Six `core/` modules import from `modules/` today, all inside functions:
  `core/auth.py` (`modules.notification_scheduler`), `core/config.py`
  (`modules.redaction`, `modules.extract`), `core/external_runner.py` (`modules.redaction`),
  `core/model_runner.py` (`modules.model_selector`), `core/document_crypto.py`
  (`modules.ingest`) and `core/llm/llama_cpp_provider.py`
  (`modules.model_integrity`). None imports from `api/`. New `core/` →
  `modules/` imports should not be added.
- Feature code reaches local inference through `ModelRunner` → `llm/factory`.
  Importing `llama_cpp` or calling Ollama directly from feature code is a
  violation. Known deviations: the `llama_cpp` import in
  `ModelSelector.load_model` (`modules/model_selector.py`), reachable only
  through `InterpretModule.interpret_with_model`, which no route calls at this
  revision (owner decision D7: route it through `ModelRunner`, work item W-7,
  not yet implemented) and the opt-in cloud runner
  `core/external_runner.py` (owner decision D12: a documented exception; its
  redaction hardening landed in W-6, and `CLAUDE.md` names it).
  `api/model_settings.py` calls `llm/factory`
  directly only to inspect and switch the provider (and imports
  `ollama_provider._assert_localhost`); it generates no text. That is the first
  dotted edge. The second: `api/assistant.py` and `api/interpretations.py` call
  `core/external_runner.py::get_runner_for_request` and pass its result on as
  the runner, which is how the opt-in cloud path is reached.
- The safety modules are called *by* feature code but are not a layer feature
  code may reshape — they are on CLAUDE.md's ask-first list.

## Startup sequence

The `main.py` lifespan, in order: `core/db_migration.py::migrate_master_db_filename`
(one-time `healthcentral.db` → `asclexis.db` rename), `settings.validate_startup()`,
`core/database.py::init_database` (refuses to start without SQLCipher when
`DATABASE_ENCRYPTION_REQUIRED`; creates `data/`, logs and vault directories),
`run_master_migrations_async()`, the knowledge-base seed
(`scripts/seed_knowledge_base.py::seed_all`, idempotent), then the background
schedulers. `create_app()` installs correlation-id logging and the access-log
query scrub (`core/logging_setup.py`), the middleware chain above, and three
routers: `api_router` under `/api/v1`, the public `/health` router, and the
authenticated metrics router under `/api/v1/monitoring`. Profile vaults are not
opened at startup; each is opened, and migrated, at login or unlock.

## Module inventory: `core/`

| File | What it owns |
|---|---|
| `config.py` | `Settings` (pydantic-settings) and the `settings` singleton; `validate_startup` |
| `database.py` | Master SQLite engine, `Base`, `get_db`, `init_database` |
| `profile_database.py` | `PerProfileDatabaseManager`: per-profile SQLCipher engines, key unseal, `PRAGMA key`, connection cache; `ProfileDatabaseBase` |
| `sqlcipher_driver.py` | `sqlcipher3` import with a stdlib `sqlite3` fallback, `is_sqlcipher_available` |
| `migrations.py` | Both Alembic runners, unversioned-vault matching, the pre-017 snapshot |
| `db_migration.py` | One-time master DB file rename |
| `auth.py` | JWT session dependencies (`require_auth`, `require_profile_access`, `RequireAuth`), `ProfileDbSession`, vault open/close on login/logout, scheduler (un)registration |
| `security.py` | JWT, bcrypt, PBKDF2 (600 000 iterations), recovery codes, DPAPI/password key sealing, Fernet and AES-GCM (`DocumentEncryption`) |
| `token_revocation.py` | Persistent JWT `jti` revocation list |
| `rate_limiter.py` | In-process login and recovery throttles (`auth_rate_limiter`, `recovery_rate_limiter`); not the HTTP `RateLimitMiddleware`, which is `security/rate_limit_middleware.py` |
| `audit.py` | `create_audit_log` (the single choke point), the `log_*_event` helpers, `audit_and_commit`, the PHI allowlists |
| `denial_audit.py` | Capped `denial.cross_profile` audit rows |
| `document_crypto.py` | Decrypting stored documents for read paths |
| `external_runner.py` | Opt-in OpenAI/Anthropic runner, strict redaction, break-glass audit (D12) |
| `model_runner.py` | `ModelRunner`, the facade feature code calls for local inference |
| `llm/` | `factory.get_provider` / `reset_provider`, `LlamaCppProvider` (default), `OllamaProvider` (localhost only), `provider.py` (`ProviderProtocol`, `CapabilityFlags`, `ProviderUnavailableError`) |
| `time.py` | `utcnow` and the other naive-UTC and profile-timezone helpers |
| `logging_setup.py` | Correlation id on log records; query-string scrub on the access log |
| `fk_audit.py` | Report-only orphan-row checks used by `scripts/fk_orphan_audit.py` and migration 017 |
| `feedback_constants.py` | The feedback tag whitelist |

Sibling packages: `security/` (HTTP middleware: headers, rate limit, input
validation, security audit), `monitoring/` (correlation id, timing, health and
metrics routers), `models/` (SQLAlchemy models; master tables on `Base`,
vault tables on `ProfileDatabaseBase`), `scripts/` (backup engine, migrate CLI,
`download_models.py`, knowledge-base seed).

## Data architecture

```mermaid
erDiagram
    MASTER_DB ||--o{ PROFILE : "holds metadata for"
    MASTER_DB ||--o{ AUDIT_LOG : "holds"
    PROFILE ||--|| VAULT_DIR : "owns"
    VAULT_DIR ||--|| VAULT_DB : contains
    VAULT_DIR ||--o{ KEY_FILE : contains
    VAULT_DIR ||--o{ ENCRYPTED_DOC : contains

    MASTER_DB {
        string engine "SQLite — NOT encrypted"
        string contents "profile rows, audit rows, backup_schedules, knowledge base (6 tables)"
    }
    AUDIT_LOG {
        string action "static template only"
        json details "allowlisted keys only"
        string profile_id "null on delete tombstone"
    }
    VAULT_DB {
        string engine "SQLCipher — encrypted"
        string contents "documents, observations, chunks, embeddings, interpretations, entities, medications, chat, feedback, memory, care tasks, pinboards, gamification, donation (25 tables)"
    }
    KEY_FILE {
        string primary "key.bin — sealed by password (or DPAPI)"
        string recovery "key.recovery.bin — sealed by recovery code, never DPAPI"
    }
```

```mermaid
flowchart LR
    subgraph chains["Two independent Alembic chains"]
        direction TB
        MM["migrations/master/<br/>3 revisions · head: 003_kb_canonical_names"]
        PM["migrations/profile/<br/>18 revisions · head: 018_ocr_opt_in"]
    end

    MM --> MDB[("master DB")]
    PM --> P1[("vault: profile A")]
    PM --> P2[("vault: profile B")]
    PM --> P3[("vault: profile N")]
```

The profile chain is applied **once per profile database**, so an N-profile
install runs the same migration N times against N separate files. New profile
tables need a new profile migration with a linear `down_revision`; the two
chains never cross.

Where they run: `run_master_migrations_async()` in the `main.py` lifespan
(`core/migrations.py::run_master_migrations`), and
`run_profile_migration_async()` from `PerProfileDatabaseManager.open_profile_database` (`core/profile_database.py`),
which login, unlock, create and recover all reach. A master DB with tables but
no `alembic_version` is stamped to head. A profile vault in that state is
stamped at the **oldest revision its schema matches exactly**
(`_match_unversioned_vault`) and then upgraded to head; a vault that matches no
revision is refused. `tests/test_migration_heads.py` asserts one head and no
merge revisions per chain, and `tests/support/migrations.py::PROFILE_HEAD` is
the head tests compare against. Manual runs: `python -m scripts.migrate
master|profile|status` from `src/backend`.

**Backup schedules live in the master DB too, and for a related reason.** A
background scheduler must know a backup is due while the vault is still
*locked* — and anything inside the vault is unreadable until unlock. So
`backup_schedules` (master migration `002`) holds only ids, enums, counts and
timestamps, and a scheduled run against a locked profile is recorded as
`skipped_locked` rather than claimed as a success.

**Why the master DB is the sensitive one.** It is unencrypted and it is
per-install rather than per-profile, so anything written there escapes both the
encryption boundary and the isolation boundary. That is the entire motivation
for the audit allowlist, and why profile deletion purges audit rows.
