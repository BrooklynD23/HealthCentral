# WEAR-15 — Saved Symptom Journal (table, routes, Wearables-page section) — Implementation Plan

**Last Updated:** 2026-10-14
**Owner:** repository owner
**Status:** PROPOSED — not executed (code waits for program M0, WEAR-01 and WEAR-02 merged, **and owner question OW-W11 answered** (orchestrator amendment 2026-10-14, see §0); 15b also waits for WEAR-10 merged and owner copy approval OW-W8).
**Base measured:** `origin/main` @ `8234990`; every `file:line` below was re-read on the plan worktree (docs-only on top of that base) on 2026-10-14.
**Refresh trigger:** any profile migration merges (P6 `013`, G-C1 `014`, AUDIT-ORDER `015`, GAM2 2b, WEAR-02); any edit to `core/audit.py`, `core/profile_database.py`, `models/__init__.py`, `api/profiles.py`; WEAR-01, 02 or 10 merge (names assumed below); the owner answers OW-W8 or OW-W9.
**Program:** [00-program](2026-10-13-wearables-00-program.md) (A2, A3, A12, A13). Consumer: [09-packet](2026-10-13-wearables-09-packet.md) (amended 2026-10-14).
**Depends on:** WEAR-01 (gated `router` in `api/wearables.py`), WEAR-02 (migration it lands after, `log_wearable_event`, static import guard, reset-tuple convention), WEAR-10 (page shell, 15b only).
**Owner decisions it builds:** WEAR-D2 (owner, 2026-10-14; commit `c53ba44`, PR #92): "(b) Saved symptom journal" — the owner chose this over the recommended (c) "none in the first version". WEAR-D4 approved the WEAR-02 `core/audit.py` diff "as written"; this plan adds nothing to it. WEAR-D8 covered only plans 10 and 09, so this plan's copy is NOT approved (OW-W8).
**Size target:** two PRs from this plan. **15a backend** ~190 lines of source plus ~330 of tests. **15b frontend** ~170 lines of source plus ~170 of tests. 15b starts only after 15a and WEAR-10 merge.

> **For agentic workers:** REQUIRED SUB-SKILLS: superpowers:test-driven-development, superpowers:subagent-driven-development. Backend loads domain skill `asclexis-backend`. Steps use `- [ ]`.

## 0. Orchestrator amendment (2026-10-14) — supersedes the audit approach below

The event-type fallback (`core/audit.py:34-35`) works mechanically, but the repo's anti-regression gate HC-AUD-004 (`src/backend/tests/test_audit_phi_minimization.py:140-185`) requires **every audit helper to emit a registered action** (`assert row.action in ALLOWED_ACTIONS`). WEAR-02 adds `log_wearable_event` to that gate (HC-WRB-216 note). Journal events through the fallback would break it or force an exemption, which is the "invariant at one site" failure (recurring-failures #9). So:

- 15a registers four journal actions in `ALLOWED_ACTIONS` (e.g. `Listed symptom journal`, `Created symptom journal entry`, `Updated symptom journal entry`, `Deleted symptom journal entry`) and extends HC-AUD-004's `log_wearable_event` row with the four journal events. Vocabulary only: no scrubber logic change, no new detail keys (`count` exists, `core/audit.py:95`).
- That is a `core/audit.py` diff **beyond** the one WEAR-D4 approved "exactly as written", so it needs a **new owner question, OW-W11**: "Approve adding 4 symptom-journal action strings to `ALLOWED_ACTIONS` in `core/audit.py` (vocabulary only) and extending HC-AUD-004?" Recommended: approve. 15a does not start until it is answered.
- HC-WRB-1512 changes from "fallback survives" to "each journal event's `row.action` is in `ALLOWED_ACTIONS` and details keep only `count`".

## 1. Scope

**This plan does:**
- One new profile-DB table `symptom_journal_entries` with its own profile migration (15a).
- Four routes on the gated wearables router: list, create, update, delete (15a). Each audited with counts only.
- Extend WEAR-02's static import guard so the journal model is unreachable from observations, RAG, timeline and `_fetch_observations`.
- A "Symptom journal" section on the Wearables page: list, add, edit, delete (15b).

**This plan does NOT license:**
- Any edit to `core/audit.py` (WEAR-D4 approved one diff, as written; a second edit is a deviation needing a NEW owner question), `modules/redaction.py` or any ask-first file (section 4).
- Journal text in RAG, trends, timeline, search, `_fetch_observations`, the doctor summary or any LLM call.
- Using the journal in the visit-prep packet. That is WEAR-09 (amended); this plan only makes entries selectable by id.
- Putting journal entries in `GET /export/json`. **Not decided** (WEAR-D7 covers only `wearable_daily_metrics`); owner follow-up OW-W10, not planned here.
- Linking entries to metrics, imports, medications or observations (no FK children, no joins).
- Tags, mood scores, severity scales, reminders, attachments, search, pagination beyond a row cap.

## 2. Evidence

| Fact | Path:line @8234990 |
|---|---|
| Profile head is `012_pinboards`; migration style to copy | `src/backend/migrations/profile/versions/012_pinboards.py:13-14,21-47` (per plan 02; re-read) |
| Model style: `ProfileDatabaseBase`, `utcnow` default, `onupdate=utcnow` | `src/backend/models/pinboard.py:10,21-23` |
| Models re-exported and listed in `__all__` | `src/backend/models/__init__.py:63,103-105` |
| create_all import list (test-only schema builder) | `src/backend/core/profile_database.py:409-417` |
| Reset tuple, children before parents, ends at `EarnedBadge`; model import block | `src/backend/api/profiles.py:498-515`, `:51-66` |
| Head literals | `tests/test_care_tasks.py:809,825`; `tests/test_profile_migrations_sqlcipher_fallback.py:41`; `tests/test_source_spans.py:313` (all `"012_pinboards"` today) |
| Unregistered audit action is replaced by the event type (comment, then code) | `src/backend/core/audit.py:34-35`; `:173-192` (`_scrub_action`) |
| String details survive only if the key is allow-listed and the value matches `^[A-Za-z0-9_.:/\-]{1,64}$` | `core/audit.py:112` (`_ENUM_VALUE_RE`) |
| `"count"` is an allowed numeric detail key | `core/audit.py:95` |
| `create_audit_log` scrubs action and details at one choke point | `core/audit.py:239-240` |
| Sibling helpers build `event_type=f"<domain>.{event}"` and map event to action with `action_map.get(event, f"...")` | `core/audit.py:329`, `:316-330` |
| HC-AUD-004 asserts `row.action in ALLOWED_ACTIONS` for the helpers it lists; `log_wearable_event` is not on its list today | `tests/test_audit_phi_minimization.py:140-190` |
| `audit_and_commit` is the fail-closed writer | `core/audit.py:474` |
| `route_client(router, prefix, profile_id, master_db, ...)` overrides auth and master DB only | `src/backend/tests/support/routes.py:26-33` |
| Profile DB override on a route client | `tests/test_audit_order.py:165-173` |
| Packet redaction loop (not touched here) | `src/backend/modules/export.py:637-643` |
| Services barrel to extend | `src/frontend/src/services/index.ts` (exports per module) |
| `models/wearable.py`, `api/wearables.py`, `log_wearable_event`, `useWearablesStatus`, WearablesPage | INFERRED from WEAR-01/02/10 plans; absent on this tree. Task 0 re-reads. |
| Baseline collected | `CLAUDE.md:30` (1487) |

**Audit conclusion (read, not yet proven):** an action not in `ALLOWED_ACTIONS` becomes the event type (`audit.py:34-35`, `:192`). `wearable.journal_list` and its three siblings match `_ENUM_VALUE_RE` (letters, dot, underscore). The only count key used is `count` (`:95`). So the events should survive the scrubber with no `core/audit.py` edit. HC-WRB-1512 proves it on the merged helper; Task 0 runs it first.

## 3. Files to touch

| Path | New/edit | Why | ~Lines |
|---|---|---|---|
| `src/backend/models/symptom_journal.py` | new | `SymptomJournalEntry` (own module; keeps the WEAR-02 `models/wearable.py` untouched) | 30 |
| `src/backend/models/__init__.py` | edit | import + `__all__` | 3 |
| `src/backend/core/profile_database.py` | edit | add `symptom_journal` to the `:409-417` list | 1 |
| `src/backend/migrations/profile/versions/0NN_symptom_journal.py` | new | one table, one index | 40 |
| `src/backend/api/profiles.py` | edit | import model, add to reset tuple | 3 |
| `src/backend/api/wearables.py` | edit | four routes + Pydantic bodies | 120 |
| 3 existing test files + WEAR-02 `tests/test_wearables_schema.py` | edit | head literals | +4/-4 |
| WEAR-02 `tests/test_wearables_guard.py` | edit | guard detects journal names; allow-list stays empty | 12 |
| `src/backend/tests/test_wearables_journal.py` | new | HC-WRB-1501..1514 | 330 |
| `CLAUDE.md`, `AGENT.md` | edit (count slots only) | SLOT-RULE | 2 |
| 15b: `src/frontend/src/services/wearablesJournal.ts`, `services/index.ts` | new / edit | types, hooks, barrel | 70 |
| 15b: `src/frontend/src/components/wearables/SymptomJournal.tsx`; WEAR-10 placeholder slot in `pages/WearablesPage.tsx` | new / edit | section | 100 |
| 15b: `src/frontend/src/__tests__/SymptomJournal.test.tsx` | new | HC-WRB-15F01..11 | 170 |

## 4. Ask-first files touched

`core/audit.py`: 4 action strings added to `ALLOWED_ACTIONS` (§0) — **owner-gated by OW-W11** (outside the WEAR-D4 diff; AO-ASKFIRST precedent). security-reviewer on the diff. `modules/redaction.py` is not touched.

## 5. Data contract

### `symptom_journal_entries` (profile DB only)

| Column | Type | Notes |
|---|---|---|
| `id` | String(36) PK | uuid4 (`default=lambda: str(uuid.uuid4())`) |
| `profile_id` | String(36), index | from the session, never from the body |
| `entry_date` | Date | the day the patient picks; no time, no offset |
| `text` | Text | stripped; 1-1000 characters after strip |
| `created_at`, `updated_at` | DateTime | `core.time.utcnow`; `updated_at` also `onupdate=utcnow` |

No FK, no children, no unique key. Not a medical record: not `observations`, not `documents` (program A2/A3).

### Migration
`0NN_symptom_journal`, linear `down_revision` = the profile head on `origin/main` at merge. It lands after WEAR-02's `0NN_wearables`. Other claimants: P6 `013_fk_cascade_alignment`, G-C1 `014_export_artifacts`, AUDIT-ORDER `015_audit_outbox`, GAM2 task 2b (unnumbered; "whichever lands second renumbers", `docs/capstone-report/owner-decisions-2026-09-27.md:134`). Rules: Task 0 reads the head the same day; if anything merges while the PR is open, rebase and renumber the file, `revision`, `down_revision`, the 3 head literals, WEAR-02's own head assertion, and HC-WRB-1501. `downgrade` drops the index, then the table.

### Routes (on WEAR-01's gated `router`; flag off returns 404 for all four)

| Route | Body / params | Result |
|---|---|---|
| `GET /wearables/journal` | optional `from`, `to` (dates, inclusive); `from > to` → 422 | list, newest `entry_date` first, then `created_at`; max 500 rows |
| `POST /wearables/journal` | `{entry_date, text}` | 201, the entry |
| `PUT /wearables/journal/{id}` | `{entry_date, text}` | 200, the entry; `created_at` kept, `updated_at` set |
| `DELETE /wearables/journal/{id}` | none | 204 |

Rules: every query filters `profile_id == session.profile_id` through `ProfileDbSession` (never master `get_db()`); an id belonging to another profile or missing → 404 `Journal entry not found.` with no entry content in the body; unknown body fields are ignored, `profile_id` from the client is never read; text is stripped by a validator, then length-checked (whitespace only → 422); `entry_date` is a real `date` (`2026-02-30` and datetimes → 422).

### Audit (WEAR-02's `log_wearable_event`, through `audit_and_commit`, master commit before `profile_db.commit()`, same order as WEAR-07)

| Route | Event | Details |
|---|---|---|
| list | `wearable.journal_list` | `{"count": n_returned}` |
| create | `wearable.journal_create` | `{"count": 1}` |
| update | `wearable.journal_update` | `{"count": 1}` |
| delete | `wearable.journal_delete` | `{"count": 1}` |

Never text, dates, entry ids or lengths. No new vocabulary: the action falls back to the event type (section 2).

### Isolation from every other reader (A3)
WEAR-02's static guard (`find_wearable_imports`) learns the module `symptom_journal` and the name `SymptomJournalEntry`. Allow-list for all four watched files (`api/observations.py`, `modules/rag.py`, `modules/timeline.py`, `api/export.py`) stays empty in 15a. WEAR-09 (amended) later allows `SymptomJournalEntry` in `api/export.py` only, plus a second test that `_fetch_observations` never names it.

## 6. §Copy — every NEW patient-facing string (15b; needs owner copy approval, OW-W8)

WEAR-D8 approved only the drafts in plans 10 and 09. These are new. Code reads them from one `COPY` const; HC-WRB-15F08 pins them. None may contain: caused, due to, indicates, diagnos*, normal, abnormal, average, mean, risk, should.

| # | Where | String | Status |
|---|---|---|---|
| J1 | Section heading | Symptom journal | needs owner copy approval (OW-W8) |
| J2 | Intro | Notes you write about how you feel, under a date you choose. They are saved in this profile on this device. Nothing checks or interprets them. | needs owner copy approval (OW-W8) |
| J3 | Privacy line | Journal entries are not used in trends, search, the timeline or AI answers. You choose which entries go into a doctor-visit packet. | needs owner copy approval (OW-W8) |
| J4 | Date label | Date | needs owner copy approval (OW-W8) |
| J5 | Note label | Note | needs owner copy approval (OW-W8) |
| J6 | Counter | {n} of 1000 characters | needs owner copy approval (OW-W8) |
| J7 | Add button | Add entry | needs owner copy approval (OW-W8) |
| J8 | Edit save button | Save changes | needs owner copy approval (OW-W8) |
| J9 | Cancel | Cancel | needs owner copy approval (OW-W8) |
| J10 | Row buttons (aria includes the date) | Edit entry / Delete entry | needs owner copy approval (OW-W8) |
| J11 | Delete confirm | Delete this entry? This cannot be undone. | needs owner copy approval (OW-W8) |
| J12 | Empty state | No journal entries yet. | needs owner copy approval (OW-W8) |
| J13 | Load error | Could not load your journal. Try again. | needs owner copy approval (OW-W8) |
| J14 | Save error | Could not save this entry. Try again. | needs owner copy approval (OW-W8) |
| J15 | Empty note | Write a note before saving. | needs owner copy approval (OW-W8) |
| J16 | No date | Pick a date. | needs owner copy approval (OW-W8) |
| J17 | Status after save / delete | Entry saved. / Entry deleted. | needs owner copy approval (OW-W8) |
| J18 | API 404 body (15a) | Journal entry not found. | needs owner copy approval (OW-W8) |

## 7. TDD test list

### 15a — `src/backend/tests/test_wearables_journal.py` (route tests via `route_client(wearables.router, "/wearables", ...)` with the profile DB overridden to a real temp profile DB, `test_audit_order.py:165-173` pattern; flag via `monkeypatch.setattr(settings, "wearables_enabled", ...)`)

| ID | Assertion | RED reason |
|---|---|---|
| HC-WRB-1501 | Real tmp vault: upgrade to head creates `symptom_journal_entries` and revision equals `0NN_symptom_journal`; downgrade removes it and the revision is WEAR-02's; upgrade again restores it; `PRAGMA table_info` names equal `SymptomJournalEntry.__table__.columns.keys()` | migration missing |
| HC-WRB-1502 | Reset: insert entries for a profile, `POST /profiles/test/reset` as a `Playwright E2E x` session via `route_client(profiles_router, "/profiles")` → 204 and `select count()` on the table is 0 (counts, not the 204) | model not in tuple |
| HC-WRB-1503 | Flag off: all four verbs → 404 through `route_client`; plus one `TestClient(main.app)` GET `/api/v1/wearables/journal` with flag off → 404 and flag on (auth + profile DB overridden) → 200 (real mount, A13) | routes absent |
| HC-WRB-1504 | POST → 201; row read back from DB has the session `profile_id`, stripped text, given `entry_date`, both timestamps set; a client-sent `profile_id` is ignored | routes absent |
| HC-WRB-1505 | POST invalid: empty, spaces-only, 1001 chars, `2026-02-30`, `2026-07-01T10:00:00`, missing field → 422 each; row count unchanged. 1000 chars accepted | no validators |
| HC-WRB-1506 | GET: A has 3 entries, B has 1; as B returns exactly B's id (compare to seeded ids); `from`/`to` inclusive bounds; order newest first; `from > to` → 422 | route absent |
| HC-WRB-1507 | PUT own: text and date change in DB, `created_at` unchanged, `updated_at` later; invalid body → 422 and row unchanged | route absent |
| HC-WRB-1508 | PUT and DELETE another profile's id (seeded under `profile-a`, called as `profile-b`) → 404; response body contains neither the text nor the date; the DB rows are unchanged | route absent |
| HC-WRB-1509 | DELETE own → 204; row gone, a sibling entry still present; second DELETE → 404 | route absent |
| HC-WRB-1510 | Real master DB: each of the four routes writes one audit row whose `details_json` keys ⊆ `{"count"}`; seeded text ("my wife Jane 555-123-4567"), the date string and the entry id are absent from `details_json` and `action` | no audit |
| HC-WRB-1511 | `audit_and_commit` patched to raise: POST/PUT/DELETE → 500 and the journal row is unchanged (fail-closed order) | wrong order |
| HC-WRB-1512 | Scrubber survival (Task 0 proof): `log_wearable_event` for each of the 4 events with poisoned details (`text`, `entry_date`, `entry_id`, `count`) writes `event_type == "wearable.journal_*"`, an `action` equal to the event type (`_ENUM_VALUE_RE`-valid), and details exactly `{"count": n}`; HC-AUD-004 style: if the merged helper rejects an unknown event, this test is red → STOP, owner question | helper/events missing |
| HC-WRB-1513 | Static guard: the checker flags a literal source importing `SymptomJournalEntry`, `models.symptom_journal`, `from models import *`; the 4 watched files yield `set()`; `api/wearables.py` imports nothing from `modules.rag`, `modules.timeline`, `core.llm` | guard not updated |
| HC-WRB-1514 | `main.app.openapi()` lists `/api/v1/wearables/journal` (GET, POST) and `/api/v1/wearables/journal/{id}` (PUT, DELETE) (recurring-failures #10) | routes absent |

Collected = start + 14 (parametrised cases may raise the pytest count; state the exact number from `--collect-only`).

### 15b — `src/frontend/src/__tests__/SymptomJournal.test.tsx` (Windows run, OW-W4; framer-motion mocked with prop filtering, `Accessibility.test.tsx` pattern)

| ID | Assertion |
|---|---|
| HC-WRB-15F01 | List renders mocked entries (date + text); an entry whose text is `<img src=x onerror=alert(1)>` shows the literal string and the DOM has no `img` (React text only; no `dangerouslySetInnerHTML`) |
| HC-WRB-15F02 | Add: submit sends `POST /wearables/journal` with `{entry_date, text}`; list refetches; J17 shown |
| HC-WRB-15F03 | Edit: row Edit fills the form; save sends `PUT .../{id}`; Cancel restores the row |
| HC-WRB-15F04 | Delete: confirm (J11) then `DELETE`; cancel sends nothing |
| HC-WRB-15F05 | Empty state J12 when the list is `[]`; loading state while pending |
| HC-WRB-15F06 | List error shows J13; failed save shows J14 and keeps the typed text |
| HC-WRB-15F07 | Empty or spaces-only note blocks submit (J15); no date blocks submit (J16); `maxLength=1000`; counter J6 updates |
| HC-WRB-15F08 | Every rendered string equals §6; none contains a banned word (case-insensitive) |
| HC-WRB-15F09 | axe clean on the section (labels, focus returns to the row after edit/delete) |
| HC-WRB-15F10 | Hooks invalidate the journal query key after create/update/delete (second GET observed) |
| HC-WRB-15F11 | Existing `WearablesShell.test.tsx` (WEAR-10) stays green with the section mounted in its slot |

## 8. Tasks

### Task 0 — gates
- [ ] `git merge-base --is-ancestor <WEAR-01 sha> origin/main` and same for WEAR-02; STOP if either fails.
- [ ] Read the profile head: `ls src/backend/migrations/profile/versions | sort | tail -3`; choose `0NN`. Note which of 013/014/015/GAM2-2b are open.
- [ ] Re-read the merged `log_wearable_event`, WEAR-02's guard (`find_wearable_imports`, allow-list shape) and its head assertion (HC-WRB-208).
- [ ] Row OW-W11 answered "approve" on `origin/main`; STOP if not. Write HC-WRB-1512 (§0 version) first; RED until the 4 actions are registered.
- [ ] Record the collected count: `cd src/backend && HF_HUB_OFFLINE=1 python -m pytest --collect-only -q -p no:cacheprovider | tail -1`.

### Task 1 — RED
- [ ] Write 1501-1514. Run `cd src/backend && HF_HUB_OFFLINE=1 python -m pytest tests/test_wearables_journal.py -p no:cacheprovider -q`. Expected: `ModuleNotFoundError: models.symptom_journal`, 404s from missing routes. Paste output.

### Task 2 — GREEN: model, migration, registries
- [ ] Model (style of `models/pinboard.py`), `models/__init__.py`, `core/profile_database.py:409-417`, migration mirroring `012_pinboards.py`.
- [ ] Update head literals (3 files + WEAR-02's assertion). Do not touch downgrade targets.
- [ ] `api/profiles.py`: import and add to the reset tuple (no children, so any position before `Embedding`).

### Task 3 — GREEN: routes
- [ ] Four routes on WEAR-01's `router`; each filters by session `profile_id`; audit through `audit_and_commit` before `profile_db.commit()`. Reuse the helper names WEAR-07 settled on.
- [ ] Extend the WEAR-02 guard. Run the file; expect 14 passed.

### Task 4 — verify
- [ ] Existing suites: `tests/test_audit_phi_minimization.py tests/test_care_tasks.py tests/test_source_spans.py tests/test_profile_migrations_sqlcipher_fallback.py tests/test_wearables_schema.py tests/test_wearables_guard.py`.
- [ ] `git diff --stat origin/main -- src/backend/core/audit.py src/backend/modules/redaction.py` prints nothing.
- [ ] Full suite under `flock /tmp/claude-1000/hc-pytest.lock`; only `test_api_rag_index_002b` may fail. Update the CLAUDE.md and AGENT.md slots in the same commit. `security-reviewer` and `code-reviewer`. Open PR 15a.

### Task 5 (15b) — frontend, after 15a, WEAR-10 and OW-W8
- [ ] RED 15F01-11; `npx vitest run src/__tests__/SymptomJournal.test.tsx` on Windows fails (component absent).
- [ ] GREEN: services file with `useJournalEntries`, `useCreate/Update/DeleteJournalEntry` (React Query, same shape as other services), barrel export; component with native `<input type="date">` and `<textarea maxLength=1000>`; render text as children only; mount in WEAR-10's slot. If OW-W8 is unsigned, build the §6 drafts and keep the PR draft.
- [ ] `npx tsc --noEmit`, `npx eslint`, vitest, axe on Windows. Playwright stays OW-W4.

## 9. Mutation / break checks (temporary, never committed; `git diff` guard after each revert)

1. Drop the `profile_id` filter in PUT: 1508 fails.
2. Put the entry text in the audit `details`: 1510 fails (and 1512 if the scrubber drops it, the test names the key).
3. Remove the reset-tuple entry: 1502 fails (rows remain).
4. Import `SymptomJournalEntry` in `modules/timeline.py`: 1513 names the file.
5. Move `profile_db.commit()` above the audit call in POST: 1511 fails.
6. 15b: render text with `dangerouslySetInnerHTML`: 15F01 fails.

## 10. Acceptance criteria (seen output, not asserted)

- 1512 output pasted before any other task (audit conclusion proven or STOP).
- `test_wearables_journal.py` prints `14 passed` (or the exact count); RED output from Task 1 pasted before GREEN.
- Migration round trip (1501) green on a tmp vault; head literals updated; existing suites in Task 4 unchanged.
- `git diff --stat` for `core/audit.py` and `modules/redaction.py` is empty (output pasted).
- Collected count equals start + added; slots updated in the same commit. Breaks 1-5 seen red, reverted clean.
- 15b: tsc, eslint, vitest output from a Windows run, or the item left open under OW-W4 with that stated.

## 11. Rollback

Revert the PR. The table is new and written only by these routes. For a database that already ran the migration, `alembic downgrade` to the previous head drops it; the entries are lost (they exist nowhere else; tell the owner before downgrading a real vault). With the flag off the routes return 404 and the section is not rendered. If WEAR-09 merged, revert it first (it reads this table).

## 12. What these tests cannot see

- **#1 green suite that could not fail.** Static guard reads import statements; it cannot see raw SQL or a view reading the table. The self-test inside 1513 shows the checker can fail.
- **#9 invariant at one site.** Journal deletion on profile delete relies on the vault file going away; explicit child deletes are not needed (no children). A future FK child must add its own delete and test.
- **#10 never started.** 1503 and 1514 prove the real mount; the UI section is proven only by 15b tests plus an owner dogfood (OW-W1).
- **Free-text names.** Entries may contain personal names ("my wife Jane"). The journal is local and encrypted with the profile DB; the exposure appears only when entries go to the packet (WEAR-09, OW-W9). Nothing here tests that.
- Whether the copy satisfies the legal read (OD-8). No tool here can see that.
- No test was run while drafting this plan.

## 13. Owner / model-machine items

- **OW-W8** — owner copy approval for §6 (new strings; WEAR-D8 did not cover them).
- **OW-W9** — redaction of names in free text (see WEAR-09): a name-capable scrubber would touch ask-first `modules/redaction.py`.
- **OW-W11** — answer the journal audit-vocabulary question (§0). Blocks 15a.
- **OW-W10** — decide whether `GET /export/json` includes journal entries (WEAR-D7 covered only `wearable_daily_metrics`). Not planned here; a follow-up plan if "include".
- **OW-W4** — 15b vitest, axe and Playwright on Windows.

## 14. Questions for the orchestrator

1. Journal model in its own `models/symptom_journal.py` (assumed, so WEAR-02's module stays closed) or inside `models/wearable.py`? The guard works either way.
2. 500-row cap on the list, no pagination: acceptable for a personal journal?
3. HC-AUD-004 lists helpers by name; should WEAR-02 add `log_wearable_event` to it? If it does with event names that are not registered actions, the journal events fail it (action == event type). Needs a WEAR-02 decision, not an audit edit here.
4. Should 15b show a future-dated entry warning? Assumed no (any real date accepted).
