# SQL-FK-001 — Foreign Key Audit (prerequisite for enabling `PRAGMA foreign_keys`)

> Status: **AUDIT ONLY — no code changes in this document's commit**
> Date: 2026-09-08
> Owner: Backend
> Refresh Trigger: A new `ForeignKey(...)` is declared, or the pragma decision changes
> Authority: [CLAUDE.md](../../CLAUDE.md) and [AGENT.md](../../AGENT.md) override everything here.
> Tracker row: `SQL-FK-001` in [docs/features/TASK_LIST.md](../features/TASK_LIST.md)

The `SQL-FK-001` ticket says the pragma cannot be flipped until "a written audit of
every FK" exists. This is that audit. It is a reference table, not a plan — the
sequenced work is in
[2026-09-08-backlog-closure-plan.md](2026-09-08-backlog-closure-plan.md#3-sql-fk-001--foreign-key-enforcement).

---

## 1. What is actually true today

Verified 2026-09-08 by reading the tree, not by trusting the tracker:

- `PRAGMA foreign_keys` appears in exactly two places repo-wide, both of them
  **comments explaining that it is off** (`src/backend/api/profiles.py:914`,
  `src/backend/tests/test_profile_deletion.py:408`). It is set on no connection.
- SQLite defaults the pragma to OFF per connection. Every `ondelete=` below is
  therefore inert **as an FK action**.
- The migration DDL and the ORM models agree everywhere (checked
  `migrations/master/versions/001,002` and `migrations/profile/versions/001,003,004,007,011,012`).
  This matters: SQLite enforces the DDL captured at `CREATE TABLE`, not the model.
  Because they agree, flipping the pragma would activate exactly the actions
  listed below — no silent divergence between fresh vaults and migrated ones.
  New vaults built through `ProfileDatabaseBase.metadata.create_all`
  (`src/backend/core/profile_database.py:403`) derive from the same models.

**Consequence:** enabling the pragma is a live behaviour change, not a no-op that
merely "makes the declarations true". Deletes that are tolerated today start
either cascading or raising.

---

## 2. Master DB (`core.database.Base`)

| # | Child table.column | → Parent | Declared action | Nullable | Behaviour once pragma is ON | Decision |
|---|---|---|---|---|---|---|
| M1 | `audit_logs.profile_id` | `profiles.id` | CASCADE | yes | Deleting a profile deletes its audit rows | **Keep CASCADE.** Already done explicitly at `api/profiles.py:907`; the cascade becomes a backstop, not the mechanism. The `profile.delete` tombstone is written with `profile_id=None` *after* the profile row is gone — a NULL FK is never checked, so the tombstone stays safe. |
| M2 | `backup_schedules.profile_id` | `profiles.id` | CASCADE | no | Deleting a profile deletes its schedule row | **Keep CASCADE.** The explicit delete at `api/profiles.py:916-918` (added 2026-07-29 precisely because the cascade was inert) stays as the mechanism; do not remove it when flipping the pragma. |

Neither master-DB FK is a blocker. Both paths already delete children explicitly
in the correct order.

---

## 3. Per-profile DB (`core.profile_database.ProfileDatabaseBase`)

| # | Child table.column | → Parent | Declared action | Nullable | Behaviour once pragma is ON | Decision |
|---|---|---|---|---|---|---|
| P1 | `observations.doc_id` | `documents.id` | CASCADE | no | Document delete cascades | **Keep CASCADE.** Works today anyway via ORM `cascade="all, delete-orphan"` (`models/document.py:73-77`) — see §4.1. |
| P2 | `chunks.doc_id` | `documents.id` | CASCADE | no | Document delete cascades | **Keep CASCADE.** Same ORM cascade (`models/document.py:79-83`). |
| P3 | `embeddings.chunk_id` | `chunks.id` | CASCADE | no (unique) | Chunk delete cascades | **Keep CASCADE.** Closes a real gap: `api/documents.py:867` deletes chunks with a core `delete()` statement, which bypasses ORM cascade — see §4.1. |
| P4 | `lab_interpretations.observation_id` | `observations.id` | CASCADE | no (unique) | Observation delete cascades | **Keep CASCADE.** |
| P5 | `chat_turns.session_id` | `chat_sessions.id` | CASCADE | no | Session delete cascades | **Keep CASCADE.** |
| P6 | `medication_schedules.medication_id` | `medications.id` | CASCADE | no | Med delete cascades | **Keep CASCADE.** |
| P7 | `doses_taken.medication_id` | `medications.id` | CASCADE | no | Med delete cascades | **Keep CASCADE.** |
| P8 | `doses_taken.schedule_id` | `medication_schedules.id` | SET NULL | **yes** | Schedule delete nulls the column | **Keep SET NULL.** Safe: the column is nullable, so SET NULL cannot violate NOT NULL. Preserves adherence history for as-needed doses. |
| P9 | `adherence_patterns.medication_id` | `medications.id` | CASCADE | no | Med delete cascades | **Keep CASCADE.** |
| P10 | `adherence_patterns.schedule_id` | `medication_schedules.id` | CASCADE | yes | Schedule delete deletes the pattern | **Keep CASCADE.** A learned pattern for a deleted schedule has no referent. |
| P11 | `reminder_logs.medication_id` | `medications.id` | CASCADE | no | Med delete cascades | **Keep CASCADE.** |
| P12 | `reminder_logs.schedule_id` | `medication_schedules.id` | SET NULL | **yes** | Schedule delete nulls the column | **Keep SET NULL.** Safe, same reasoning as P8. |
| P13 | `pinboard_item.pinboard_id` | `pinboard.id` | CASCADE | no | Pinboard delete cascades | **Keep CASCADE.** |
| P14 | `document_category.doc_id` | `documents.id` | **none (NO ACTION)** | no | Document delete **RAISES** if a category row survives | **Change to CASCADE** in a profile migration. Ordering already saves the two known paths (`api/documents.py:1193-1194`, `:1850-1851`) but nothing enforces that ordering on the next path someone writes. |
| P15 | `document_entity.doc_id` | `documents.id` | **none (NO ACTION)** | no | Document delete **RAISES** if an entity row survives | **Change to CASCADE.** Same reasoning as P14. |
| P16 | `care_plan_task.source_document_id` | `documents.id` | **none (NO ACTION)** | yes | Document delete **RAISES** whenever a care task was derived from it | **Change to SET NULL — and fix the live bug first. See §4.2.** |
| P17 | `care_plan_task.source_entity_id` | `document_entity.id` | **none (NO ACTION)** | yes | Entity delete **RAISES** whenever a care task cites it | **Change to SET NULL.** Same defect as P16; `document_entity` rows are deleted on every document delete and every reprocess. |
| P18 | `earned_badges.badge_id` | `badge_definition.id` | **none (NO ACTION)** | no | Badge-definition delete raises | **Keep NO ACTION, deliberately.** Badge definitions are seeded and never deleted; RESTRICT-by-default is the correct semantic — losing a definition should not silently erase what a patient earned. |

**Not an FK, and cannot be one:** `pinboard_item.item_id` is polymorphic
(`item_type` + `item_id`, `models/pinboard.py:30-44`), so it can point at a
document, an observation, or an entity. No FK can express that. The manual prune
in `_prune_document_pin_targets` (`api/documents.py:88`) is the *only* integrity
mechanism for pins and must survive the pragma change untouched.

---

## 4. Findings that change the work

### 4.1 The pragma is not what makes document deletion work today

`delete_document` ends with `await profile_db.delete(document)`
(`api/documents.py:1859`), and the comment there says it "cascades to
observations, chunks". That is true, but via SQLAlchemy's ORM
`cascade="all, delete-orphan"`, not via SQLite. The distinction matters because
**core `delete()` statements bypass ORM cascade entirely** — and the codebase uses
them: `api/documents.py:628` (observations) and `:867` (chunks) both delete
children with core statements during reprocess.

The `:867` re-embed path is where that bites. `Chunk.embedding` declares
`cascade="all, delete-orphan"` (`models/chunk.py:76-81`), so deleting a *document*
through the ORM does reach embeddings transitively. But `:867` is a core
`delete(Chunk)` statement, which bypasses ORM cascade entirely — and there is no
`delete(Embedding)` anywhere in `api/`. So re-embedding a document orphans its
previous embedding rows today, because P3's CASCADE is inert and nothing else
covers it. Enabling the pragma closes that orphan class for free.

### 4.2 Care-plan tasks outlive the document they quote — a present-day defect, not just an FK blocker

`delete_document` explicitly deletes `DocumentEntity` and `DocumentCategory`, and
the in-code comment gives the reason plainly: entity quotes are "verbatim document
text" and must not "outlive the document into exports or pins"
(`api/documents.py:1846-1851`).

`CarePlanTask.source_quote` is described in its own model as "Verbatim clinician
wording the task was derived from" (`models/care_plan_task.py:45`). It is the same
class of data, held to the same standard by the same reasoning — and **nothing
deletes it when the source document is deleted.** There is no
`delete(CarePlanTask)` anywhere in `api/`.

So this is two problems wearing one ticket:

1. **A data-retention defect that exists right now, pragma or no pragma.** A
   patient deletes a visit note; verbatim text from it survives in the care-task
   table and remains reachable through the tasks API and exports. This is worth
   fixing on its own schedule, independent of SQL-FK-001.
2. **A hard blocker for the pragma.** With `foreign_keys=ON` and P16 left at NO
   ACTION, `DELETE FROM documents` raises `IntegrityError` for any document that
   produced a care task. Flipping the pragma without fixing this converts a silent
   orphan into a user-visible 500 on document deletion.

The fix for (1) is a decision, not a mechanic: does deleting a document delete the
tasks derived from it, or keep the task and drop the quote? **Recommendation: keep
the task, null the provenance, and clear `source_quote`.** A follow-up the patient
still has to do does not stop being real because they deleted the PDF, but the
verbatim clinician text has no right to outlive its source. That maps exactly onto
`ondelete="SET NULL"` for P16/P17 plus an explicit `source_quote = None` update in
`delete_document`. **This is a data-lifecycle call — confirm with the owner before
implementing**, per the same convention that gated `PROF-DEL-001`.

### 4.3 Enabling the pragma is per-connection, and there are two engines

`PRAGMA foreign_keys=ON` is not a database property — it is per-connection, and
must be re-issued on every pooled connection. Two engines need it:
`core/database.py:44` (master) and `core/profile_database.py:306` (per-profile,
which already has a `@event.listens_for(engine.sync_engine, "connect")` hook at
`:314` that sets the SQLCipher key — the pragma belongs in that same hook). A
`connect` event on each is the only correct place; setting it once at startup, or
in a single session, silently covers only one connection.

---

## 5. Net change list (what §2–§4 add up to)

One profile migration altering four constraints (P14, P15 → CASCADE; P16, P17 →
SET NULL), one behaviour fix in `delete_document` for `source_quote`, and two
`connect` event hooks. No master-DB migration. Every other FK keeps its declared
action; the audit's value is that this is now written down rather than assumed.

Note that SQLite cannot `ALTER` a constraint — the migration must use Alembic's
batch mode (table rebuild, copy, swap), which is the standard approach in this
chain and must be written with a linear `down_revision` per the dual-migration
invariant.
