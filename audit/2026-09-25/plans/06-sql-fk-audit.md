# SQL-FK-001 Foreign-Key Enforcement Implementation Plan

> **2026-09-27 corrections ([review follow-up](../review/2026-09-27-followup.md), F-02/F-06/F-15):**
> - **Approval provenance (F-02 — record found; delete-semantics approval inferred; the review's stop stands).** An owner decision *is* recorded, but not where the review looked. `docs/plans/2026-09-08-backlog-closure-plan.md` §14 decision 3 (line 404, branch `origin/claude/asclexis-repo-audit-349pjq`, commit `fe31e78` "docs: record the four owner decisions…") reads: "**Full: fix the four constraints, then flip the pragma**". §3.2 of that plan defines the four: P14/P15 → CASCADE, P16/P17 → SET NULL. §3.3 puts the pragma on **both** engines. The FK audit doc's "AUDIT ONLY" status is about that doc's own commit, not about approval. **However**, the question put to the owner (text removed in the `fe31e78` diff) asked about *blast radius*: "Confirm the appetite for fixing those [orphan-write failures] as they appear rather than deferring the flip again". The record's "What it licenses" cell says "Fixing orphan-write failures as the suite surfaces them". Explicit approval of each relationship's delete effect was never asked.
> - **Residual gates this plan must honour.**
>   1. The record exists only on an unmerged branch until plan 01 lands.
>   2. It is an agent-written transcription of the owner's answer, not an owner-signed artifact.
>   3. The approval covers exactly P14–P17 plus the pragma on both engines. Anything else is **outside** it: Task 3 Step 5's reset-tuple expansion, any change to crypto-erase ordering, any change to backup/restore delete semantics.
>   4. The recorded text says to "measure the delta against this baseline, not against a remembered number" (§14). The commit message adds that the blast radius "should be measured before the flip, not during".
>
>   The implementation program therefore keeps an **explicit owner stop** before Task 2 (migration). There the owner approves each changed relationship's delete effect (P14/P15 CASCADE, P16/P17 SET NULL); this is the review's required correction, retained.
> - **F-15:** the pragma hook wording is corrected in Global Constraints ("once per new physical DBAPI connection").
> - **Baseline:** "1245" is main@`40f590e`. Measure the count on the post-plan-05 tree before Task 1 and use that number.

> **Wave-3 integration banner (2026-09-28)** — sources: `audit/2026-09-25/swarm-2026-09-27/wave3/3a-integration.md` B-4, M-5 (re-checked against `40f590e` before this banner was written).
> 1. **Collected-count slots (3a B-4; owner-gated SLOT-RULE).** Tasks 1, 2 and 3 add test files (`test_fk_audit.py`, `test_fk_migration_013.py`, the HC-FK pragma tests), and no commit here stages `CLAUDE.md`/`AGENT.md`. If the owner signs SLOT-RULE: every commit that changes the collected count also updates the collected slots in `CLAUDE.md` and `AGENT.md`, in the same commit, with the number measured on that commit's tree. Collected slots only; pass sentences are left as they are and flagged in the PR. Without the rule, a later phase that checks the slots (W-2, S-1, P08 Task 0) STOPs on a stale figure.
> 2. **Task 2 breaks two existing assertions (3a M-5, from W-11b F-4).** `src/backend/tests/test_care_tasks.py:809` and `:825` both assert `== "012_pinboards"` (`git show 40f590e:src/backend/tests/test_care_tasks.py | sed -n 800,828p`). Migration `013` moves the profile head, so Task 2 must update both literals to `"013_fk_cascade_alignment"` in its own commit. G-C1 (W-11b) later moves them to `014`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make SQLite actually enforce the foreign keys the schema already declares — detect pre-existing orphans first, realign the four constraints that would break live code paths, then set `PRAGMA foreign_keys=ON` on every application-owned connection (master + per-profile vault).

**Architecture:** `PRAGMA foreign_keys` is per-connection and defaults OFF, so enforcement lives in SQLAlchemy `connect` event listeners on each runtime engine — never in DDL. The only schema change is a single profile-chain Alembic migration (batch table rebuild) flipping four FK constraints on three child tables to their audited actions; everything else is runtime pragma + detection tooling + tests.

**Tech Stack:** Python 3.11+, SQLAlchemy 2.x async (`create_async_engine` + `engine.sync_engine` connect listeners — the pattern already used at `core/profile_database.py:314`), Alembic dual chains (`migrations/profile/` head = `012_pinboards`), SQLite/SQLCipher, pytest + `tests/support/routes.py::route_client` for HTTP-level route tests.

## Global Constraints

- **Conservative on patient vaults.** Report before enforcing; never auto-delete orphan rows; never weaken a constraint or relax a test to reach green (owner-approved blast radius, recorded as branch1 backlog plan §14 decision 3 — `docs/plans/2026-09-08-backlog-closure-plan.md:404` on `origin/claude/asclexis-repo-audit-349pjq`, commit `fe31e78`, 2026-09-08; branch-only until plan 01 lands; see banner: *"Full: fix the four constraints, then flip the pragma"* — each red test is a finding about a real orphan write, fixed in test setup or the code path, never in the FK).
- **Per-connection, every engine.** ~~The pragma must be re-issued on every pooled checkout; the only correct place is a `connect` event listener.~~ *Corrected 2026-09-27 ([review F-15](../review/2026-09-27-followup.md)):* the pragma must be set **once per new physical DBAPI connection**. That is what a `connect` listener does: SQLAlchemy documents `PoolEvents.connect` as firing when a DBAPI connection is first created, and `PoolEvents.checkout` as firing on every retrieval from the pool. Add a `checkout` hook only if some code path can change this connection-local pragma while the connection is pooled. Tests must check the pragma on **more than one distinct physical connection per engine**, not on one session. Setting it once at startup or in one session silently covers one connection.
- **Migration engines stay pragma-OFF.** `core/migrations.py` (:134, :255-257, :368, :406-408) and `migrations/profile/env.py` (:153-159) build their own engines for Alembic. Batch table rebuilds on SQLite require `foreign_keys` OFF (SQLite docs; the pragma can't even change mid-transaction). Do not add the pragma there — add a comment marking the omission deliberate.
- **`scripts/backup.py` uses raw `sqlite3.connect`** (:175-176, :258, :473-495) — untouched by SQLAlchemy listeners, and that must stay true: restore does `DELETE FROM profiles WHERE id=?` then re-INSERTs the same row (:495-496), which under FK enforcement would CASCADE-delete that profile's `audit_logs` and `backup_schedules` before the re-INSERT. Flag: if anyone ever routes restore through the hooked SQLAlchemy engine, restore silently eats audit history.
- **Dual migrations invariant:** profile tables → `migrations/profile/` only, linear `down_revision`. No master migration in this plan (both master FKs keep their declared CASCADE).
- **Baseline:** `cd src/backend && python -m pytest tests/ -p no:cacheprovider -q` → **1245 collected** at main@`40f590e` (measure again at plan start; see banner); CI 1245 pass, local 1244 (`test_api_rag_index_002b` env-only embedding failure — do not touch). On WSL/9p: `find src/backend -name __pycache__ -type d -exec rm -rf {} +` before pytest. Frontend toolchain on Windows, not WSL.
- **TDD:** every task writes the check first and observes it fail. Route tests go through HTTP via `tests/support/routes.py::route_client` (+ `get_profile_db_session` override per `tests/test_timeline.py:279-287`).
- Re-read `docs/agentic/recurring-failures.md` before claiming done — mode #8 already cites this exact ticket ("The same review asserted an FK cascade removed a row").

## Prior art — what branch1 already covers (read it; do not redo it)

`docs/plans/2026-09-08-sql-fk-001-foreign-key-audit.md` on `origin/claude/asclexis-repo-audit-349pjq` (lands on main with that branch — the ticket itself says the pragma could not flip until this written audit existed). Verified against main @ `40f590e`, it already provides:

- **Full FK inventory with per-FK decisions:** master `audit_logs.profile_id` (M1) + `backup_schedules.profile_id` (M2), both CASCADE and both already backed by explicit deletes; profile P1–P18 — fourteen keep their declared action, four change (`document_category.doc_id`, `document_entity.doc_id` → CASCADE; `care_plan_task.source_document_id`, `source_entity_id` → SET NULL; `earned_badge.badge_id` stays NO ACTION deliberately — its actual table name is `earned_badge`, singular, not `earned_badges` as the audit writes).
- **Two findings that precede the pragma:** §4.1 — `api/documents.py:867` core `delete(Chunk)` bypasses ORM cascade and orphans `embeddings` rows **today** (pragma closes this for free; same for `delete(Observation)` at `:628` orphaning `lab_interpretations` — `Observation.interpretation` has no `cascade=` at `models/observation.py:106-108`); §4.2 — `care_plan_task.source_quote` outliving its document, already fixed on the branch (`45ac889`, `api/documents.py:1851+` clears provenance+quote in `delete_document` only).
- **§4.3:** the pragma belongs in the existing connect hook at `core/profile_database.py:314`.
- **Owner approval recorded:** fix the four constraints then flip; suite expected to go red partway; weakening an FK to get green is explicitly out of scope.

**Gaps this plan fills:** the branch audit is a reference table, not a task sequence — it has no orphan-detection tooling (mandatory before enforcement: P3's orphan class means real vaults can already hold dangling `embeddings`), no migration mechanics (SQLite can't ALTER constraints — batch rebuild required), no pragma code for the master engine, no test plan, and no regression checks on crypto-erase / `/profiles/test/reset`. Care-quote retention fix is branch1 commit `45ac889` — a prerequisite for the retention promise but **not** for FK correctness: under post-migration SET NULL the delete path is safe either way (see Task 3 note).

## Verified facts this plan relies on (checked on main @ `40f590e`, not trusted from docs)

1. `PRAGMA foreign_keys` is executed **nowhere**. `core/database.py:44-48` master engine has no connect listener; `core/profile_database.py:314-356` listener sets only `PRAGMA cipher_version`/`key`; `migrations/*/env.py` + `core/migrations.py` listeners set only `PRAGMA key`. Only mentions are comments admitting it is off (`api/profiles.py:913-916`, `tests/test_profile_deletion.py:406-409`).
2. Model↔DDL agreement holds today (FK audit §1 — re-verified against `migrations/master/versions/001:49,002:34` and `migrations/profile/versions/001:64,103,124,144,241,267,273,297,303,331,337`, `003:68`, `004:25,36`, `007:39`, `011:32-33`, `012:32`).
3. `response_feedback.session_id`/`turn_id` have **no FK constraint** — `models/response_feedback.py:48-49` declares them logical-only ("enforced at application layer"). They go in the orphan audit as *informational* checks, not enforced FKs. `pinboard_item.item_id` is polymorphic — can never be an FK; `_prune_document_pin_targets` (`api/documents.py:88`) is its only integrity mechanism and must survive untouched.
4. `delete_profile` (`api/profiles.py:773-940`) is manual ordered deletes — sealed keys → vault sweep → backup sweep → one master transaction (`delete(AuditLog)` :909, `delete(BackupSchedule)` :918, `delete(Profile)` :923, tombstone `profile_id=None` :928-937). FK-ON changes nothing here: explicit child deletes run before the parent; the cascade becomes a backstop; NULL tombstone FK is never checked. `create_profile` (:316 add → :319 audit insert → :326 commit) relies on SQLAlchemy UOW sorting the parent INSERT first — it does (mapper-level FK dependency), so creation is safe under immediate-mode enforcement.
5. Core `delete()` sites bypassing ORM cascade: `documents.py:88` (pinboard prune — child table, safe), `:628` (Observation → orphans `lab_interpretations` today), `:867` (Chunk → orphans `embeddings` today), `:1193-1194` + `:1850-1851` (DocumentEntity/DocumentCategory — children; under post-migration CASCADE they only harden ordering). ORM `profile_db.delete()` sites: `medications.py:649` (Medication — ORM cascade covers schedules/doses/patterns; `reminder_logs` has **no** ORM relationship and orphans today → P11 closes it), `medications.py:882` (MedicationSchedule — `doses`/`patterns` relationships declare no cascade → today orphans; post-pragma P8 SET NULLs, P10 cascades), `assistant.py:461` (ChatSession → turns, ORM + DB cascade agree), `pinboards.py:206,271,361`, `memory.py:234`, `interpret.py:276,1031` — all child-side or ORM-covered.
6. `/profiles/test/reset` (`api/profiles.py:477-532`) deletes child-before-parent in a fixed tuple — already FK-safe ordering **except** it never touches `care_plan_task`, `chat_sessions`/`chat_turns`, `response_feedback`, `pinboard`/`pinboard_item` (the audit's separate P2 finding). Post-migration this is safe: SET NULL on P16/P17 fires during its `delete(DocumentEntity)`/`delete(Document)` instead of raising. **Pre-migration + pragma-ON it would 500** — which is why Task 2 (migration) lands before Task 3 (pragma).

## Risk register — where enforcement can break a live path

| Site | Risk under `foreign_keys=ON` | Mitigation |
|---|---|---|
| `POST /{id}/reprocess` (`documents.py:1193-1194`) | `delete(DocumentEntity)` raises if `care_plan_task.source_entity_id` still NO ACTION | Migration 013 → SET NULL (auto-nulls stale refs; `source_document_id`+`source_quote` persist for dedup — preserves branch1's deliberate reprocess semantics) |
| `DELETE /documents/{id}` | Same via `:1850-1851`; `delete(Document)` via P14-P17 | 013; branch1's `45ac889` additionally clears `source_quote` (retention fix — separate concern) |
| `POST /profiles/test/reset` | Pre-013 IntegrityError on tasks pointing at deleted entities/docs | 013 ordering (Task 2 before Task 3) |
| Pre-existing orphans in real vaults (embeddings from `:867`, lab_interpretations from `:628`, dose/schedule refs from `:649/:882`) | Next parent delete raises `IntegrityError` → user-visible 500 | Task 1 audit report first; findings fixed per-owner-review, never auto-deleted |
| `scripts/backup.py` restore (:493-496) | Would cascade-eat audit history **if** it used a hooked engine — it doesn't (raw sqlite3) | Do not migrate it to SQLAlchemy; comment the hazard |
| `delete_profile` | None — child deletes precede parent; tombstone NULL | Regression test Task 4 proves it |
| `create_profile` (parent+audit in one flush) | None — UOW sorts INSERTs | covered by existing profile tests under pragma-enabled master engine |
| `MedicationSchedule` delete nulling `doses_taken.schedule_id` | Visible behavior change: linked dose loses schedule linkage (declared intent of schema; today it orphans instead) | Test asserts SET NULL; flag to owner in PR description |

---

### Task 1: Orphan audit — detection tooling, report only

Detection runs **before** enforcement: real vaults can already hold orphans (embeddings from re-embed, lab_interpretations from reprocess, reminder_logs from med deletes). The audit reports; it never deletes.

**Files:**
- Create: `src/backend/core/fk_audit.py`
- Create: `src/backend/scripts/fk_orphan_audit.py`
- Test: `src/backend/tests/test_fk_audit.py`

**Interfaces:**
- Produces: `MASTER_CHECKS: list[FkCheck]`, `PROFILE_CHECKS: list[FkCheck]`, `LOGICAL_CHECKS: list[FkCheck]`, `FkCheck(check_id, child_table, child_column, parent_table, parent_column, scope, enforced, where=None, note="")`, `OrphanFinding(check_id, count, sample_ids)`, `async find_orphans(session, checks) -> list[OrphanFinding]`, `find_orphans_dbapi(conn, checks) -> list[OrphanFinding]`
- Consumed by: Task 1 script, Task 4 tests, and reusable post-migration verification.

- [ ] **Step 1: Write the failing test** — `tests/test_fk_audit.py`

```python
"""HC-FKA: report-only orphan detection for every declared + logical FK."""
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from core.profile_database import ProfileDatabaseBase
from core.fk_audit import PROFILE_CHECKS, LOGICAL_CHECKS, find_orphans


@pytest_asyncio.fixture
async def profile_db():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_hc_fka_001_clean_vault_has_no_orphans(profile_db):
    findings = await find_orphans(profile_db, PROFILE_CHECKS + LOGICAL_CHECKS)
    assert findings == []


@pytest.mark.asyncio
async def test_hc_fka_002_finds_seeded_orphan(profile_db):
    """FKs are off in test engines, so a dangling child can be inserted raw —
    exactly the state pragma enforcement must never silently inherit."""
    await profile_db.execute(text(
        "INSERT INTO embeddings (id, chunk_id, model_name, vector_blob, "
        "dimensions, created_at) VALUES ('e1', 'ghost-chunk', 'm', x'00', 3, "
        "datetime('now'))"
    ))
    await profile_db.commit()
    findings = await find_orphans(profile_db, PROFILE_CHECKS)
    hit = [f for f in findings if f.check_id == "P3"]
    assert len(hit) == 1 and hit[0].count == 1 and hit[0].sample_ids == ["e1"]


@pytest.mark.asyncio
async def test_hc_fka_003_logical_checks_flagged_not_enforced(profile_db):
    await profile_db.execute(text(
        "INSERT INTO response_feedback (id, profile_id, session_id, turn_id, "
        "rating, created_at, updated_at) VALUES ('f1', 'p', 'ghost-session', "
        "'ghost-turn', 1, datetime('now'), datetime('now'))"
    ))
    await profile_db.commit()
    findings = await find_orphans(profile_db, LOGICAL_CHECKS)
    assert {f.check_id for f in findings} == {"L1", "L2"}
    assert all(f.enforced is False for f in findings)
```

(adjust the seeded columns to the real NOT NULL set when writing — read `models/embedding.py` / `response_feedback.py` first)

- [ ] **Step 2: Run to verify it fails** — `cd src/backend && python -m pytest tests/test_fk_audit.py -x -q` → expected: `ModuleNotFoundError: core.fk_audit`.

- [ ] **Step 3: Implement `core/fk_audit.py`** — full check table, IDs matching the branch audit so docs cross-reference cleanly:

```python
"""Report-only orphan detection across declared and logical FKs (SQL-FK-001).

The pragma is per-connection and was never set, so vaults can already hold
dangling children. This module finds them; nothing here deletes.
"""
from dataclasses import dataclass
from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class FkCheck:
    check_id: str          # M1/M2, P1..P18, L1.. — matches docs/plans FK audit
    child_table: str
    child_column: str
    parent_table: str
    parent_column: str = "id"
    scope: str = "profile"  # "master" | "profile"
    enforced: bool = True   # False = logical relation, no DB constraint
    where: Optional[str] = None  # extra child-side predicate (polymorphic)


@dataclass
class OrphanFinding:
    check_id: str
    child_table: str
    child_column: str
    parent_table: str
    enforced: bool
    count: int
    sample_ids: list[str]


MASTER_CHECKS = [
    FkCheck("M1", "audit_logs", "profile_id", "profiles", scope="master"),
    FkCheck("M2", "backup_schedules", "profile_id", "profiles", scope="master"),
]

PROFILE_CHECKS = [
    FkCheck("P1", "observations", "doc_id", "documents"),
    FkCheck("P2", "chunks", "doc_id", "documents"),
    FkCheck("P3", "embeddings", "chunk_id", "chunks"),
    FkCheck("P4", "lab_interpretations", "observation_id", "observations"),
    FkCheck("P5", "chat_turns", "session_id", "chat_sessions"),
    FkCheck("P6", "medication_schedules", "medication_id", "medications"),
    FkCheck("P7", "doses_taken", "medication_id", "medications"),
    FkCheck("P8", "doses_taken", "schedule_id", "medication_schedules"),
    FkCheck("P9", "adherence_patterns", "medication_id", "medications"),
    FkCheck("P10", "adherence_patterns", "schedule_id", "medication_schedules"),
    FkCheck("P11", "reminder_logs", "medication_id", "medications"),
    FkCheck("P12", "reminder_logs", "schedule_id", "medication_schedules"),
    FkCheck("P13", "pinboard_item", "pinboard_id", "pinboard"),
    FkCheck("P14", "document_category", "doc_id", "documents"),
    FkCheck("P15", "document_entity", "doc_id", "documents"),
    FkCheck("P16", "care_plan_task", "source_document_id", "documents"),
    FkCheck("P17", "care_plan_task", "source_entity_id", "document_entity"),
    FkCheck("P18", "earned_badge", "badge_id", "badge_definition"),
]

# No constraint exists for these (verify: models/response_feedback.py:48-49;
# pinboard_item.item_id is polymorphic). Informational only — a hit is a data
# smell to report, never a migration target.
LOGICAL_CHECKS = [
    FkCheck("L1", "response_feedback", "session_id", "chat_sessions", enforced=False),
    FkCheck("L2", "response_feedback", "turn_id", "chat_turns", enforced=False),
    FkCheck("L3", "pinboard_item", "item_id", "documents", enforced=False,
            where="item_type = 'document'"),
    FkCheck("L4", "pinboard_item", "item_id", "observations", enforced=False,
            where="item_type = 'observation'"),
    FkCheck("L5", "pinboard_item", "item_id", "care_plan_task", enforced=False,
            where="item_type = 'care_task'"),
]
```

plus `orphan_sql(check)` (`SELECT c.id FROM <child> c LEFT JOIN <parent> p ON c.<col> = p.<pcol> WHERE c.<col> IS NOT NULL AND p.<pcol> IS NULL [AND <where>]`) and two runners — `find_orphans_dbapi(conn, checks)` for raw sqlite/sqlcipher cursors (scripts) and `async find_orphans(session, checks)` via `session.execute(text(sql))`, each returning `OrphanFinding` with `count` + ≤5 `sample_ids`.

- [ ] **Step 4: Implement `scripts/fk_orphan_audit.py`** — CLI, exits 0 clean / 1 orphans:

```
python scripts/fk_orphan_audit.py --master
python scripts/fk_orphan_audit.py --profile <id> --password <pw>
python scripts/fk_orphan_audit.py --profile <id>          # plaintext dev vault
```

Master path: parse the file path out of `settings.database_url` (`sqlite+aiosqlite:///`), `sqlite3.connect`, run `MASTER_CHECKS`. Profile path: `asyncio.run(get_profile_db_manager()._load_encryption_key(profile_id, password))` (it's `async`) → `get_sqlcipher_module().connect(manager._get_profile_db_path(profile_id))` → `PRAGMA key = "x'<hex>'"` (reuse `core.migrations._key_to_hex`); if `is_sqlcipher_available()` is False, plain `sqlite3.connect` (dev vaults). Prints one line per check (`P3 embeddings.chunk_id→chunks.id: 7 orphans (e1, e2, …)`) + summary; `sys.exit(1)` if any enforced finding, `0` otherwise — logical findings print under a separate `INFORMATIONAL (no constraint)` header and do not fail the run.

- [ ] **Step 5: Run tests + script** — `python -m pytest tests/test_fk_audit.py -v` → 3 pass; `python scripts/fk_orphan_audit.py --master` → prints `M1/M2: 0 orphans`, exit 0. On a dev machine with a seeded vault, run `--profile` once against a real vault and **attach the report to the PR** — that is the pre-enforcement evidence, not an optional nicety.

- [ ] **Step 6: Commit** — `git add src/backend/core/fk_audit.py src/backend/scripts/fk_orphan_audit.py src/backend/tests/test_fk_audit.py && git commit -m "feat(fk-audit): report-only orphan detection for SQL-FK-001 (HC-FKA-001..003)"`

---

### Task 2: Profile migration `013_fk_cascade_alignment` — realign the four mismatching constraints

SQLite cannot `ALTER` a constraint; the chain already uses `op.batch_alter_table` (`007:53`). P14/P15 → CASCADE, P16/P17 → SET NULL, per the owner-approved decisions in the branch audit §3. **The pragma itself needs no migration** — it is runtime, not DDL. This migration exists only because the audit found declared actions that are wrong for live code paths.

**Files:**
- Create: `src/backend/migrations/profile/versions/013_fk_cascade_alignment.py` (`down_revision = "012_pinboards"`)
- Modify: `src/backend/models/document_category.py:22,38` (add `ondelete="CASCADE"`), `src/backend/models/care_plan_task.py:38-43` (add `ondelete="SET NULL"` ×2)
- Test: `src/backend/tests/test_fk_migration_013.py`
- Modify: `src/backend/tests/test_care_tasks.py:809,825` — head literal `"012_pinboards"` → `"013_fk_cascade_alignment"` (Wave-3 banner item 2)

**Interfaces:**
- Produces: migrated vaults whose `PRAGMA foreign_key_list(document_category)` / `(document_entity)` report `on_delete=CASCADE`; `(care_plan_task)` reports `SET NULL` on both columns. Model and DDL stay in agreement (the audit §1 invariant).

- [ ] **Step 1: Write the failing test** — build a scratch vault at head-1 then upgrade. Helpers: `_get_alembic_config("profile")` from `core/migrations`, set `config.attributes["vault_path"]` **and** `config.attributes["encryption_key"]` (env.py:120-124 raises without it even on plaintext test DBs — `DATABASE_ENCRYPTION_REQUIRED=false` in conftest lets `b"0"*32` pass harmlessly), `command.upgrade(config, "012_pinboards")`, seed rows, `command.upgrade(config, "head")`. Then:

```python
def _fk_actions(db_path, table):
    # foreign_key_list columns: id, seq, table, from, to, on_update, on_delete, match
    rows = sqlite3.connect(db_path).execute(
        f"PRAGMA foreign_key_list({table})").fetchall()
    return {r[3]: r[6] for r in rows}   # {child_col: on_delete}

def test_hc_fkm_001_constraint_actions_aligned(tmp_path):
    db = tmp_path / "v.db"
    _build_vault_at_012(db)          # helper: run migrations to 012 on a file DB
    _upgrade_one(db)                 # helper: alembic upgrade 012 -> head
    assert _fk_actions(db, "document_category")["doc_id"] == "CASCADE"
    assert _fk_actions(db, "document_entity")["doc_id"] == "CASCADE"
    fks = _fk_actions(db, "care_plan_task")
    assert fks["source_document_id"] == "SET NULL"
    assert fks["source_entity_id"] == "SET NULL"

def test_hc_fkm_002_rows_survive_rebuild(tmp_path):
    # seed one row per rebuilt table at 012, upgrade, assert count + contents
    ...
```

- [ ] **Step 2: Run to verify it fails** — `pytest tests/test_fk_migration_013.py -x` → fails: `document_category` still reports `NO ACTION`.

- [ ] **Step 3: Implement the migration** — batch rebuild per table with `copy_from` (required: the existing FKs are **unnamed**, so `drop_constraint` cannot target them; `copy_from` supplies the complete desired table — copies data, drops the old table, renames):

```python
revision: str = "013_fk_cascade_alignment"
down_revision: Union[str, None] = "012_pinboards"

def upgrade() -> None:
    _rebuild("document_category", doc_fk_action="CASCADE")
    _rebuild("document_entity",   doc_fk_action="CASCADE")
    _rebuild_care_plan_task()
```

For each `copy_from` table declare **every column verbatim from the DDL in `004`/`010`/`011`** (e.g. `document_entity` = 004's nine columns + 010's `char_start/char_end/quote/verified_by_user/extraction_version`) plus its `sa.Index` objects and `server_default`s — a drift here silently drops a column/index during the copy. Verify afterwards with `PRAGMA table_info` + `PRAGMA index_list`, not by eyeballing the diff. `downgrade()` rebuilds the same tables with no `ondelete` (original NO ACTION).

- [ ] **Step 4: Update the models** — the three `ForeignKey(...)` sites above gain `ondelete=`, keeping model↔DDL agreement.

- [ ] **Step 5: Run** — `pytest tests/test_fk_migration_013.py -v` → pass; also run any existing migration tests (`pytest tests/ -k migration`).

- [ ] **Step 6: Commit** — `git commit -m "feat(migrations): 013 realign document_entity/category/care_plan_task FK actions for SQL-FK-001"`.

---

### Task 3: Enable `PRAGMA foreign_keys=ON` on both runtime engines

**Files:**
- Modify: `src/backend/core/database.py` (import `event`, add listener after `engine` creation ~:48)
- Modify: `src/backend/core/profile_database.py` (~:314, inside `open_profile_database`)
- Create: `src/backend/tests/support/db.py` (shared pragma-enabled test-engine factory)
- Test: `src/backend/tests/test_fk_enforcement.py`

**Interfaces:**
- Produces: `install_sqlite_foreign_keys(sync_engine) -> None` in `core/database.py` — one definition, three call sites (master engine, profile runtime engine, test factory). No cycles: `profile_database` already imports `core.*`; `database` never imports `profile_database`.
- Consumed by: Task 4 regression tests; every subsequent test fixture that wants production-fidelity enforcement.

- [ ] **Step 1: Write failing tests** — `tests/test_fk_enforcement.py`:

```python
@pytest.mark.asyncio
async def test_hc_fk_001_pragma_on_every_pooled_connection():
    from core.database import engine
    async with engine.connect() as c1:
        assert (await c1.execute(text("PRAGMA foreign_keys"))).scalar() == 1
    async with engine.connect() as c2:   # fresh pooled checkout
        assert (await c2.execute(text("PRAGMA foreign_keys"))).scalar() == 1
```

- [ ] **Step 2: Run to verify fail** — `pytest tests/test_fk_enforcement.py::test_hc_fk_001_pragma_on_every_pooled_connection` → `assert 0 == 1`.

- [ ] **Step 3: Implement** — in `core/database.py`:

```python
def install_sqlite_foreign_keys(sync_engine) -> None:
    """Enforce declared FK actions on every pooled connection (SQL-FK-001).

    SQLite defaults foreign_keys=OFF per connection; without this every
    ondelete= on the models is inert. Runtime pragma — no migration needed.
    """
    @event.listens_for(sync_engine, "connect")
    def _fk_on(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

if engine.sync_engine.url.get_backend_name() == "sqlite":
    # Master URL can be postgres in server mode, where the pragma doesn't exist.
    install_sqlite_foreign_keys(engine.sync_engine)
```

in `core/profile_database.py`, immediately after the existing `set_sqlite_pragma` registration (~:356, inside `open_profile_database`):

```python
            # FK enforcement lands on the migrated schema: this engine's first
            # connection is opened only after run_profile_migration_async
            # completes below, and listener order puts PRAGMA key first.
            install_sqlite_foreign_keys(engine.sync_engine)
```

(add `from .database import install_sqlite_foreign_keys` to imports — verify no import cycle; if one appears, move the helper to `core/sqlcipher_driver.py` instead.)

- [ ] **Step 4: Test factory** — `tests/support/db.py`:

```python
def fk_profile_engine() -> AsyncEngine:
    """In-memory profile-vault engine with production FK enforcement (SQL-FK-001)."""
    engine = create_async_engine("sqlite+aiosqlite://")
    install_sqlite_foreign_keys(engine.sync_engine)
    return engine
```

- [ ] **Step 5: Run** — `pytest tests/test_fk_enforcement.py -v` → pass.

- [ ] **Step 6: Mark the deliberate omissions** — one comment line each in `migrations/profile/env.py` above its `connect` listener and at `core/migrations.py:260`/`scripts/backup.py:493`:

```python
# PRAGMA foreign_keys stays OFF here on purpose: Alembic batch rebuilds and
# restore's delete-then-reinsert both require it (SQL-FK-001).
```

- [ ] **Step 7: Commit** — `git commit -m "feat(db): enforce PRAGMA foreign_keys on master + profile engines (SQL-FK-001)"`.

---

### Task 4: Enforcement proofs + crypto-erase/reset regression

**Files:**
- Test: `src/backend/tests/test_fk_enforcement.py` (extend)
- Modify (optional, folds in the audit's separate P2 — confirm scope first): `src/backend/api/profiles.py:499-517` reset tuple

- [ ] **Step 1: Cascade now enforces** — on `fk_profile_engine()` + `create_all`, insert document→chunk→embedding, run a **core** `delete(Chunk)` (same shape as `documents.py:867`), assert `SELECT count(*) FROM embeddings` = 0. Pre-pragma this would have been 1 — this test *proves the orphan class is closed*, not just that the pragma is set.

- [ ] **Step 2: SET NULL enforces** — medication+schedule+dose; core `delete(MedicationSchedule)`; assert dose row survives with `schedule_id IS NULL`. Plus the negative: undeclared relations change nothing — delete a `chat_sessions` row with a `response_feedback` row pointing at it (no FK declared) → feedback row **survives untouched** (proves no phantom enforcement; logical-FK orphans stay a report item, not a delete action).

- [ ] **Step 3: Crypto-erase regression** — real master engine (`create_all` + `install_sqlite_foreign_keys`), seed Profile + AuditLog + BackupSchedule; call `delete_profile` with real session + `vaults`-style tmp-path monkeypatch (reuse `tests/test_profile_deletion.py`'s `_delete`/`vaults` harness but a real `AsyncSession` for `db`). Assert 204, zero audit/schedule rows for the profile, tombstone row exists with `profile_id IS NULL`. This is the check that would catch an FK-driven reordering of the master transaction.

- [ ] **Step 4: `/profiles/test/reset` regression** — `route_client`-style app overriding `require_auth` (name must start `"Playwright E2E"`), `get_profile_db_session` → `fk_profile_engine` session, `get_db` → AsyncMock. Seed document+entity+category+care_task+chat session+turn+pinboard+item+dose chain; `POST /profiles/test/reset` → **204** (post-013 SET NULL fires; pre-013 this was the IntegrityError path). Assert no 500 and — because the audit flags reset missing 6 tables — record actual surviving rows so the gap is evidenced, not assumed.

- [ ] **Step 5 (optional — decision point):** extend the reset tuple with `CarePlanTask`, `ChatTurn`→`ChatSession`, `ResponseFeedback`, `PinboardItem`→`Pinboard` (child-first). Folds in the audit P2 "reset misses 6 tables" while this file is already open and now has an FK-correct ordering to preserve. If owner wants scope tight, defer and link the finding instead — do not silently expand.

- [ ] **Step 6: Commit** — `git commit -m "test(fk): prove cascades enforce and crypto-erase/reset are unchanged (SQL-FK-001)"`.

---

### Task 5: Full-suite sweep, docs, tracker

- [ ] **Step 1: Baseline then sweep** —
```bash
find src/backend -name __pycache__ -type d -exec rm -rf {} +   # WSL/9p stale-bytecode trap
cd src/backend && python -m pytest tests/ -p no:cacheprovider -q
```
Expected deltas: +~10 new tests collected (target ≥1255 collected; state the real number in the PR). **Every new failure is a finding** — fix the test's data setup or the code path it exposed; never the constraint, never a threshold. The one tolerated red is `test_api_rag_index_002b` (env-only). Bare-engine fixtures in ~12 test files (`test_timeline.py:121`, `test_search.py:69`, `test_documents_api.py:550`, `test_chat_sessions.py`, `test_pinboards.py:83`, `test_care_tasks.py:676`, `test_med_reconcile.py:567`, `test_visit_prep_packet.py:569`, `test_highlights.py:303`, `test_structured_import.py:416`, `test_document_confidence_duplicates.py:196`, `tests/agent/*`) do **not** enforce — that is a known coverage gap; converting them is a follow-up, and any fixture converted must be listed in the PR.

- [ ] **Step 2: Re-check the stale comments** — `api/profiles.py:913-916` and `tests/test_profile_deletion.py:406-409` both say the pragma "is set nowhere" — update to name the hook sites; stale guidance that reads as authority is recurring-failure #8.

- [ ] **Step 3: Tracker + docs** — `docs/features/TASK_LIST.md` `SQL-FK-001` row → DONE with evidence (commands + outputs); Session Notes entry. If the suite surfaced a failure mode not in `docs/agentic/recurring-failures.md`, record it there in the same commit.

- [ ] **Step 4: Boot check** — `cd src/backend && python -c "from main import app"`.

- [ ] **Step 5: Commit** — `git commit -m "docs: close SQL-FK-001 — pragma enabled, orphan audit tooling, migration 013"`.

## Definition of done (per AGENT.md — evidence required, not belief)

- [ ] Orphan audit ran against a real/seeded vault **before** enforcement; report attached to PR; zero auto-deletions.
- [ ] `PRAGMA foreign_keys=ON` verified on fresh pooled checkouts of both engines.
- [ ] New tests observed failing before each fix; cascade/SET-NULL proofs pass after.
- [ ] `pytest tests/ -p no:cacheprovider -q` shows collected ≥1255 and no unexplained failures (paste output).
- [ ] Crypto-erase + `/profiles/test/reset` regression tests pass against pragma-enabled engines.
- [ ] Explicit statement in the PR: pragma needs no migration; migration 013 exists only to fix the four audited constraint mismatches.
- [ ] `delete_document`'s `source_quote` retention note cross-checked against branch1 `45ac889` — if that branch hasn't merged, this plan still lands correctly (SET NULL covers correctness; quote-clearing is a separate retention fix).
