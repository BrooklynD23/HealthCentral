# Backend Structure

**Last Updated:** 2026-07-27
**Owner:** Project Lead
**Refresh Trigger:** Middleware order changes, a router is added/removed, or a migration chain gains a head

Part of the [architecture diagram set](README.md).

---

## Request lifecycle

Every request crosses the same middleware chain before it reaches a route. The
order is defined in `src/backend/main.py` and matters: cheap rejections happen
before expensive work, and auditing happens before timing so the audit row
exists even for a request that later fails.

```mermaid
flowchart TD
    REQ["Incoming request"] --> CORS["CORSMiddleware<br/><i>explicit allow_headers, never *</i>"]
    CORS --> CID["CorrelationIdMiddleware<br/>attaches a request id"]
    CID --> SEC["SecurityHeadersMiddleware"]
    SEC --> RATE["RateLimitMiddleware<br/>fixed window"]
    RATE --> VAL["InputValidationMiddleware<br/>path/query sanity, body size → 413"]
    VAL --> AUD["SecurityAuditMiddleware<br/>app-log only, never the DB"]
    AUD --> TIME["TimingMiddleware<br/>p50/p95/p99"]
    TIME --> ROUTE["Route handler"]

    ROUTE --> AUTH{"requires auth?"}
    AUTH -->|yes| JWT["require_auth / require_profile_access<br/>JWT + revocation list"]
    AUTH -->|"no — /health, list profiles,<br/>login, recover"| SKIP[" "]
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
    subgraph api["api/ — 18 routers"]
        direction LR
        A1["documents · observations · assistant"]
        A2["timeline · care_tasks · pinboards · search"]
        A3["export · medications · med_reconcile"]
        A4["profiles · memory · feedback · model_settings"]
    end

    subgraph modules["modules/ — feature logic"]
        direction LR
        M1["ingest · extract* · import_structured<br/>normalize · glossary"]
        M2["rag · agent/ · interpret*"]
        M3["timeline · care_tasks · highlights · search"]
        M4["export · fhir_export · rl_dataset"]
        SAFE["<b>safety</b><br/>redaction · faithfulness<br/>verifier_agent · interpret_safety"]
    end

    subgraph core["core/ — infrastructure"]
        direction LR
        C1["config · time · security · auth"]
        C2["database · profile_database · audit"]
        C3["model_runner → llm/factory → providers"]
    end

    api --> modules --> core
    modules --> SAFE
    api -.->|"never directly"| C3

    style SAFE fill:#4a148c,stroke:#ba68c8,color:#fff
```

Rules this diagram encodes:

- Dependencies point **downward only**. `core/` never imports from `modules/`
  or `api/`.
- Feature code reaches the LLM **only** through `ModelRunner` → `llm/factory`.
  Importing `llama_cpp` or calling Ollama directly from a router is a
  violation, which is why that edge is drawn dotted and labelled.
- The safety modules are called *by* feature code but are not a layer feature
  code may reshape — they are on CLAUDE.md's ask-first list.

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
        string contents "profile rows, audit rows"
    }
    AUDIT_LOG {
        string action "static template only"
        json details "allowlisted keys only"
        string profile_id "null on delete tombstone"
    }
    VAULT_DB {
        string engine "SQLCipher — encrypted"
        string contents "observations, documents, entities, medications, chat, memory, tasks, pinboards"
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
        MM["migrations/master/<br/>head: 001_initial_schema"]
        PM["migrations/profile/<br/>head: 012_pinboards"]
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

**Why the master DB is the sensitive one.** It is unencrypted and it is
per-install rather than per-profile, so anything written there escapes both the
encryption boundary and the isolation boundary. That is the entire motivation
for the audit allowlist, and why profile deletion purges audit rows.
