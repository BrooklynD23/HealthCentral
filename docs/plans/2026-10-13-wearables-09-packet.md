# WEAR-09 — Visit-Prep Packet Section + Symptom Journal Selection — Implementation Plan

**Last Updated:** 2026-10-14
**Amended after WEAR-D2..D8 (owner, 2026-10-14; commit `c53ba44`, PR #92):** D2 = (b) saved symptom journal (typed-in notes replaced by selecting saved entries, with a redacted preview); D3 = 14 days; D8 = approve drafts as written (covers only the pre-amendment strings; new journal strings are OW-W8).
**Owner:** repository owner
**Status:** PROPOSED — not executed. **Four PRs, one plan (Opus D1D8 A1/R3):** **09a-metrics** (backend, wearable section only; waits for program M0, WEAR-02 incl. its audit vocabulary, WEAR-05, WEAR-07, WEAR-08a; does not wait for OW-W9). **09a-journal** (backend: journal fields, preview route, snapshot store; additionally waits for 09a-metrics, WEAR-15a, OW-W12, and **the owner row OW-W9 on `origin/main` — blocker, its Task 0 STOPs without it**). **09b-metrics** (ExportPage wearable option). **09b-journal** (ExportPage journal picker; after 09a-journal, 09b-metrics, WEAR-15b). D2, D3, D8 are answered; owner copy approval OW-W8 for the new journal strings.
**Base measured:** `origin/main` @ `8234990`; program file @ `a985390`.
**Refresh trigger:** any edit to `api/export.py`, `modules/export.py`, `api/pinboards.py`, `core/audit.py` or `ExportPage.tsx`; WEAR-02, 05, 07, 08 or 10 merge (their names and signatures are assumed below); WEAR-15 merges; OW-W8 or OW-W9 answered.
**Program:** [00-program](2026-10-13-wearables-00-program.md) (A3, A4, A5b, A7, A12, A13; risks R3, R7, R8).
**Depends on:** WEAR-02 (tables, audit vocabulary, static guard), WEAR-05 (`describe()`), WEAR-07 (review state exists), WEAR-08 (owns `modules/wearables/select.py::select_current`; orchestrator decision, this plan reuses it and never re-implements selection), WEAR-10 (`useWearablesStatus`, 09b only). The program table lists 07 only; the orchestrator adds 08 (Question 1). 09a-metrics also depends on WEAR-02's audit vocabulary: `metrics_included` is reserved by WEAR-02, so the persisted-details test (920) needs it. **WEAR-15a** (table `symptom_journal_entries`, `SymptomJournalEntry`; **09a-journal only**: it reads the table by id and never writes it); 09b-journal also needs WEAR-15b's `useJournalEntries` hook (otherwise it ships its own small query; orchestrator to confirm).
**Owner decisions (resolved):** WEAR-D2: "(b) Saved symptom journal" (the owner did not take the recommendation). Strict redaction does not catch natural-language names (`modules/redaction.py:81-88`), so the packet path adds a mandatory redacted, server-issued preview snapshot (`journal_preview_id`), a fixed warning, and no way to skip the preview; "redaction of names in free text" stays an OPEN RISK (OW-W9, a hard gate for 09a-journal/09b-journal; a name-capable scrubber would touch ask-first `modules/redaction.py`). WEAR-D3: 14 days. WEAR-D8: drafts approved as written; C14 (rewritten), C19 and C22-C28 are new and need OW-W8.
**Size target (Opus D1D8 A1):** four PRs. **09a-metrics** ~150 lines of source plus ~280 of tests. **09a-journal** ~170 lines of source plus ~260 of tests (preview store module, preview route, journal wiring, PUT/DELETE and reset/delete purge calls). **09b-metrics** ~60 lines of source plus ~70 of tests. **09b-journal** ~100 lines of source plus ~80 of tests. 09b-metrics starts after 09a-metrics and WEAR-10; 09b-journal after 09a-journal, 09b-metrics and WEAR-15b.

> **For agentic workers:** REQUIRED SUB-SKILLS: superpowers:test-driven-development and superpowers:subagent-driven-development. Backend work also loads domain skill `asclexis-backend`. Steps use `- [ ]`.

## 1. Scope

**This plan does:**
- Add `include_wearables: bool = False`, `journal_entry_ids: list[str] = []` (max 10) and `journal_preview_id: str | None = None` to `VisitPrepRequest` (server-issued preview snapshot, Codex r3 ADV-2). **The journal part (09a-journal, 09b-journal) does not start until the owner row OW-W9 is on `origin/main`** (names in free text, Codex r3 ADV-1); 09a-journal Task 0 enforces it with a STOP. The wearable-metrics part (09a-metrics, 09b-metrics) contains no journal field, route or test and does not wait.
- Add `POST /export/visit-prep/journal-preview`: returns each selected entry's date and text after strict redaction plus a fixed warning (names written in sentences may not be removed). Nothing is written to a database; the redacted snapshot is held in memory only, purged on expiry, capped per profile, single-use, and purged on journal edit/delete and on profile reset/delete (section 5; Opus D1D8 A4).
- Add a pure renderer `modules/wearables/packet_section.py` that turns reviewed + included rows into a markdown section, and a second section "Symptom journal entries (written by the patient)" for the selected journal entries.
- Insert both sections inside `compose_visit_prep_packet`, before the strict redaction loop, so the whole text is redacted.
- Add one small frontend option on the existing visit-prep card (09b).

**This plan does NOT license:**
- Any edit to `modules/redaction.py`, `modules/interpret_safety.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`, `core/auth.py`, `core/security.py` or encryption. None is touched.
- Any LLM or `ModelRunner` call. The section is a template.
- Reading wearable rows from `_fetch_observations`, trends, RAG, timeline or the doctor summary (A3).
- Writing or changing journal entries (WEAR-15 owns the table and routes), a name-capable scrubber, or any edit to `modules/redaction.py` (OW-W9).
- Journal entries in `GET /export/json` (undecided, WEAR-15 OW-W10).
- Any medical-device classification claim, threshold, normal range, comparison to a population, or causal wording (D8, OD-8 open).
- A change to `GET /export/csv` or `/export/json`.

## 2. Evidence

| Fact | Path:line @8234990 |
|---|---|
| Request model, fields end at `confirm` | `src/backend/api/export.py:666-686` |
| Packet store is in-memory | `api/export.py:47-48` |
| Route and confirm check | `api/export.py:700-701`, `:718` |
| Labs verified-only filter in the route | `api/export.py:765-769` |
| Route calls compose with named section args | `api/export.py:791-800` |
| Packet stored, then audited with `count` and `redaction_count` | `api/export.py:801-812` |
| Download re-renders `packet["sections"]` for html/pdf, markdown from `packet["markdown"]` | `api/export.py:829-875` (read through the html branch) |
| `compose_visit_prep_packet` signature; each section arg optional | `src/backend/modules/export.py:502-514` |
| Sections built inline, in order: Reason `:537`, Medications `:543`, Labs `:560`, Visits `:589`, Follow-up `:602`, Questions `:616`, Source Documents `:623-633` | `modules/export.py:537-633` |
| Strict engine, loop over every `section["content"]`, counts summed | `modules/export.py:635-642` |
| Footer says "Only user-verified data is included" | `modules/export.py:645-650` (asserted by HC-PKT-007, `tests/test_visit_prep_packet.py:220-227`) |
| Return dict (`sections`, `markdown`, `redaction_count`) | `modules/export.py:665-677` |
| Second caller of compose (pinboards), no wearable args | `src/backend/api/pinboards.py:501-510` |
| `name_context` needs a label word plus two capitalised tokens; "Jane's Apple Watch" does not match | `src/backend/modules/redaction.py:81-88` (read only, ask-first) |
| Other strict rules that could touch numbers: ssn `:59-64`, phone `:73-80` | `modules/redaction.py:59-80` |
| Existing route tests call the handler as a plain function | `tests/test_visit_prep_packet.py:295,325`; fetchers monkeypatched `:265-285` |
| `route_client(router, prefix, profile_id, master_db, ...)`; overrides auth and `get_db` only | `src/backend/tests/support/routes.py:27` |
| Profile DB override pattern for route tests | `tests/test_audit_order.py:165-173` (`dependency_overrides[get_profile_db_session]`) |
| Audit: string keys exclude `import_id`, `vendor`, `metric`; count keys include `count`, `redaction_count` | `core/audit.py:68-76`, `:89-110` |
| `log_export_event` puts `export_type` in details | `core/audit.py:452-471` |
| ExportPage visit-prep state, hook, handler | `src/frontend/src/pages/ExportPage.tsx:73-78`, `:90`, `:176-192` |
| Visit-prep card; confirm checkbox; buttons | `ExportPage.tsx:440-454`, `:525-536`, `:558-584` |
| `VisitPrepRequest` TS type; `useGenerateVisitPrep` | `src/frontend/src/services/export.ts:54-65`, `:308-313` |
| Wearable models, `wearables_enabled`, `describe()` do not exist yet | INFERRED from `ls modules` and `grep core/config.py`: no `wearable` hit |

## 3. Files to touch

PR key: **M** = 09a-metrics, **J** = 09a-journal, **Mb** = 09b-metrics, **Jb** = 09b-journal (Opus D1D8 A1).

| PR | Path | New/edit | Why | ~Lines |
|---|---|---|---|---|
| M | `src/backend/modules/wearables/packet_section.py` | new | Pure renderer: `render_wearable_section`, `COPY` (non-journal strings), closed `DEVICE_LABELS`, include filter | 80 |
| J | `src/backend/modules/wearables/packet_section.py` | edit | `render_journal_section`, journal `COPY` (C14-C16, C22-C28) | 30 |
| M | `src/backend/modules/export.py` | edit | New param `extra_sections`, insert before `:635`; footer variant | 25 |
| M | `src/backend/api/export.py` | edit | `include_wearables` field, flag check, wearable row fetch, build section, `metrics_included` audit key, `wearables_min_days` passed to the renderer | 60 |
| J | `src/backend/api/export.py` | edit | `journal_entry_ids` and `journal_preview_id` fields, check order, `_fetch_journal_entries`, preview route, `item_count` audit key | 90 |
| J | `src/backend/modules/wearables/journal_preview.py` | new | In-memory snapshot store: `put` (purges expired, caps 5 per profile), `get`, `pop`, `purge_profile`, `purge_entry`; a module so `api/wearables.py` and `api/profiles.py` can purge without importing `api/export.py` (Opus D1D8 A3/A4) | 45 |
| J | `src/backend/api/wearables.py` | edit | WEAR-15a's journal PUT and DELETE call `purge_entry(profile_id, id)` after commit | 4 |
| J (**OW-W12**) | `src/backend/api/profiles.py` | edit | `reset_synthetic_test_profile` (`:476`) and `delete_profile` (`:772`) each call `purge_profile(profile_id)`; delete-path edit, owner-gated | 4 |
| M | `src/backend/tests/test_wearables_packet_section.py` | new | Pure renderer tests (M subset) | 120 |
| J | same file | edit | Pure journal tests | 60 |
| M | `src/backend/tests/test_wearables_packet.py` | new | HTTP tests (M subset) | 190 |
| J | same file | edit | HTTP journal tests | 200 |
| M, J | WEAR-02 static guard test file | edit | M: allow `models.wearable` in `api/export.py` only. J: also allow `models.symptom_journal` (`SymptomJournalEntry`) there | 4 + 4 |
| M, J | `CLAUDE.md`, `AGENT.md` | edit (count slots only) | SLOT-RULE, once per PR | 2 + 2 |
| Mb | `ExportPage.tsx`, `services/export.ts` | edit | Wearable checkbox, `include_wearables` request field | 60 |
| Mb | `src/frontend/src/__tests__/WearablePacketOption.test.tsx` | new | Frontend tests (Mb subset) | 70 |
| Jb | `ExportPage.tsx`, `services/export.ts`, `services/wearablesJournal.ts` use | edit | Journal picker, preview step, `journal_entry_ids` and `journal_preview_id` request fields, `journalPreviewId` state | 100 |
| Jb | same test file | edit | Journal frontend tests | 80 |

## 4. Ask-first files touched

09a-metrics, 09b-metrics, 09b-journal: none. 09a-journal: `api/profiles.py` reset route (`:476`) and `delete_profile` (`:772`) gain one in-memory purge call each. That edits the delete path, which the RL-EXPORTS-DELETE-PATH precedent (`docs/capstone-report/owner-decisions-2026-09-27.md`) treats as ask-first, so it is owner-gated by **OW-W12** (Task 0 STOPs without the row; Opus D1D8 A4). `modules/redaction.py` is read, never edited. The `core/audit.py` vocabulary is reserved by WEAR-02; this plan only uses it. If Task 0 finds `metrics_included` missing there, STOP and fix WEAR-02 first (security-reviewer on that diff).

## 5. Data contract

**Request (additive, defaults keep today's behaviour):**
- `include_wearables: bool = False` (09a-metrics).
- 09a-journal only: `journal_entry_ids: list[str] = []`, `Field(max_length=10)`; `journal_preview_id: str | None = None`. Ids reference WEAR-15's `symptom_journal_entries`; nothing is typed into the request.
- **Check order (Opus D1D8 R2), after `confirm`:** (1) pydantic: more than 10 ids → 422; (2) `include_wearables=true` or non-empty `journal_entry_ids` while `settings.wearables_enabled` is False → 400 (C18 / C26); (3) non-empty ids without a valid `journal_preview_id` → 400 (C27) — valid means: issued by the preview route to this profile, for exactly these ids, not expired (15 min), not already used (single-use); (4) re-read the entries: an id deleted since the preview → 404 (C28, no entry content in the body); an entry whose `updated_at` changed since the preview → 409 ("entry changed since preview"). A **foreign** entry id never reaches step 4: the preview route returns 404 for it, so no valid preview can exist and the packet call stops at step 3 with 400 (C27). The foreign-id 404 is therefore asserted on the **preview** route. The journal is independent of `include_wearables`.

**Preview route (`api/export.py`, `ProfileDbSession`, flag-gated, audited):** `POST /export/visit-prep/journal-preview`, body `{journal_entry_ids: list[str]}` (1-10 ids, else 422; flag off → 400 C26; unknown or foreign id → 404). Response `{entries: [{id, entry_date, text}], redaction_count, warning}` where `text` went through `RedactionEngine(policy_level="strict")` (called, never edited) and `warning` is the fixed string C24. The route also stores a snapshot `{profile_id, ids, redacted entries, updated_at per entry, expires_at}` in an in-memory store (`modules/wearables/journal_preview.py`, same restart caveat as `_packet_store`, `api/export.py:48`) keyed by a new uuid and returns it as `preview_id`. The stored journal entry stays raw. **Bounds (Opus D1D8 A4):** each insert first purges every expired snapshot; at most **5 snapshots per profile** (the oldest is dropped); a snapshot is **popped on successful packet generation** (single use, so reuse → 400); a profile's snapshots are **purged on profile reset and on profile delete** (`api/profiles.py:476` and `:772`, owner-gated **OW-W12**); and snapshots holding an entry id are **dropped on journal PUT/DELETE** of that id (`api/wearables.py`, Opus D1D8 A3). Redacted PHI therefore sits in memory for at most 15 minutes and is gone on restart. The packet renders **the snapshot text the patient saw**, never a fresh re-read of the text, so an edit after preview cannot change what is sent (the re-read in step 4 only compares `updated_at` and detects deletion). 09b calls the preview, shows it, and sends `journal_preview_id` only afterwards. A caller cannot skip the preview: without a server-issued id the request is 400.

**Journal rows read (profile DB, this profile only):** `_fetch_journal_entries(profile_db, profile_id, ids)` selects by `id IN ids` and `profile_id`, returns plain dicts `{id, entry_date, text}` sorted by date, or signals a missing id (404). Nothing else from the table is read and nothing joins it to wearable rows.

**Wearable rows read (profile DB, this profile only):** `wearable_daily_metrics` joined to `wearable_metric_reviews` on (import_id, metric) and `wearable_imports`. Window = request `from_date`..`to_date`; if absent, the 30 days ending `utcnow().date()` (INFERRED default, Question 2). M = days in window.

**Selection (A5b, A4):** 1) fetch only rows whose review has `patient_reviewed_at` set; 2) call WEAR-08's `select_current(rows)` (group by (metric, local_date); most recent reviewed import wins; tie goes to the larger import id); 3) in the packet path, drop rows whose chosen import has `include_in_packet = False`. Step 3 comes after step 2 on purpose: an older included import must not resurface behind a newer one the patient left out.

**Per metric statistics:** `describe(values)` from WEAR-05 (median, p25, p75, min, max, days). No mean anywhere (F1). A metric with fewer than `settings.wearables_min_days` days (WEAR-D3 = 14; the setting is added by WEAR-07 and reused here, not redefined) prints a suppression line and no numbers. The route passes `settings.wearables_min_days` to the renderer (never a literal); 932 pins the 13/14 boundary and 933 proves the route wiring (Opus D1D8 A6).

**Renderer inputs:** plain dicts `{metric, local_date, value, unit, tz_changed, device_class, import_id, imported_at}`. `source_name` and filename are not renderer inputs. Test 904 passes them anyway to prove they are ignored.

**Closed device map:** `apple_watch` → "Apple Watch", `iphone` → "iPhone", `garmin_device` → "Garmin device", anything else → "Other".

**Section dict:** `{"title": str, "content": str}`, same shape as the existing inline sections. Order in the packet: after "Questions for Your Provider", before "Source Documents" (`modules/export.py:616` and `:623`). Wearable section first, journal section after it as its own section, never merged and never joined to metrics. The whole packet, journal text included, still passes the strict engine at `modules/export.py:637`.

**Audit (Opus D1D8 A5):** the existing `log_export_event` call gains `metrics_included` (09a-metrics; WEAR-02 reserves the key) and `item_count` (09a-journal; journal entries included; an existing allowed key, `core/audit.py:95`). The preview route logs `audit_and_commit(master_db, log_export_event, ..., export_type="visit_prep_journal_preview", details={"count": n})` **before** the response body is built from the entries, so a failed audit returns 500 and never entry text (`export_type` is an allowed string key, `core/audit.py:72`). The action string is unchanged: `log_export_event` writes the registered "Exported data" (`core/audit.py:466`); no new audit vocabulary is added, because the preview, like an export, sends patient-facing data from the server to the client. No `core/audit.py` edit. Never entry text, dates or ids. Tests 920 and 929 write to a **real master DB** and assert the persisted `details_json` keys (not a patched helper), because `create_audit_log` silently scrubs any key outside the allow-list.

## 6. §Copy — every patient-facing string (owner approval D8)

Approve or edit each row. Code reads these from one `COPY` dict, and test 908 pins them. None may contain: caused, due to, indicates, diagnos*, normal, abnormal, average, mean, risk, should (test 902 and 956). None claims device classification.

| # | Where | String |
|---|---|---|
| C1 | Section heading | Wearable measurements (patient-recorded, not clinically verified) |
| C2 | Opening line | Recorded by a consumer device. Not a clinical measurement. |
| C3 | Window line | Window: {start} to {end} ({M} days). |
| C4 | Table header | Metric / Days with data / Median per day / Middle half (25th to 75th percentile) / Lowest to highest / Device / Imported |
| C5 | Metric: resting HR | Resting heart rate (bpm) |
| C6 | Metric: sleep | Sleep, time asleep (min) |
| C7 | Metric: steps | Steps (count per day) |
| C8 | Days cell | {n} of {M} |
| C9 | Device labels | Apple Watch / iPhone / Garmin device / Other |
| C10 | Imported cell | {YYYY-MM-DD} (import {first 8 chars of id}) |
| C11 | Time-zone footnote | * Some days had more than one time zone offset; those days were grouped by each record's own local date. |
| C12 | Suppressed metric | {metric label}: not shown. Only {n} of {M} days have data; at least {min} are needed. |
| C13 | Nothing selected | No reviewed wearable measurements were selected. |
| C14 | Journal heading (rewritten; OW-W8) | Symptom journal entries (written by the patient) |
| C15 | Journal line (unchanged; covered by WEAR-D8) | Written by the patient. Not checked or interpreted. |
| C16 | Journal row (unchanged; covered by WEAR-D8) | - {YYYY-MM-DD}: {text} |
| C17 | Footer variant (only when a wearable section is present) | Except the wearable section, only user-verified data is included in this packet. |
| C18 | 400 flag off | Wearable summary is not available. |
| C19 | (removed: notes no longer ride the wearable option) | — |
| C20 | 09b checkbox label | Include wearable summary |
| C21 | 09b helper | Adds the wearable measurements you reviewed and marked for the packet. Recorded by a consumer device. Not a clinical measurement. |
| C22 | 09b journal label (OW-W8) | Symptom journal entries (optional, up to 10) |
| C23 | 09b journal controls (OW-W8) | Select entries / Preview selected entries / Include previewed entries / Change selection |
| C24 | Fixed preview warning, server string, also shown by 09b (OW-W8) | Names written inside sentences may not be removed automatically. Read each entry before you include it. |
| C25 | 09b no entries (OW-W8) | No journal entries yet. Add them on the Wearables page. |
| C26 | 400 journal flag off (OW-W8) | Symptom journal is not available. |
| C27 | 400 no preview (OW-W8) | Preview the selected journal entries before including them. |
| C28 | 404 unknown entry (OW-W8) | Journal entry not found. |

C17 keeps the word "verified", so HC-PKT-007 (`tests/test_visit_prep_packet.py:220-227`) still passes. C24 is honest about the known gap: strict redaction does not catch free-text names without a label word (`modules/redaction.py:81-88`). C14 (rewritten), C19 (removed) and C22-C28 are not covered by WEAR-D8; they need owner copy approval (OW-W8). Same banned-word list applies to C14-C16 and C22-C28.

## 7. TDD test list

Each PR owns its own list and collected count (Opus D1D8 A1). **09a-metrics** = 10 pure + 13 HTTP = **23**. **09a-journal** = 2 pure + 12 HTTP = **14**, plus journal assertions added to 918, 919 and 920 (no new test functions). Frontend **09b-metrics** = 6, **09b-journal** = 5.

### 09a-metrics — pure (`src/backend/tests/test_wearables_packet_section.py`)

| ID | Assertion | RED reason |
|---|---|---|
| HC-WRB-901 | Fixture of 20 days (above the WEAR-D3 14-day minimum) renders C1, C2, C3, one row per metric with median, p25-p75, min-max, "20 of 30" matching `describe()`; one outlier day leaves the median unchanged (F1) | module missing |
| HC-WRB-902 | Parametrised over the 10 banned words, case-insensitive: absent from the wearable section and C17, with fixture covering tz footnote, suppressed metric, all device classes (covers research HC-WRB-010, F7, F11); the journal section is covered by 934 | module missing |
| HC-WRB-903 | Metric with 3 of 30 days prints C12 and no median, min or max digits for it (covers research HC-WRB-013, F2) | module missing |
| HC-WRB-904 | Rows carrying `source_name="Jane's Apple Watch"` and filename "Jane Smith export.zip": neither string, nor "Jane", appears; unknown `device_class` prints "Other" (A7; covers research HC-WRB-012 at unit level) | module missing |
| HC-WRB-905 | C11 appears only when some included day has `tz_changed` | module missing |
| HC-WRB-907 | No rows → C13 only | module missing |
| HC-WRB-908 | Every non-journal `COPY` value (C1-C13, C17, C18, C20, C21) equals the literal in §6 (pins D8 approval); the journal strings are pinned by 934 | module missing |
| HC-WRB-909 | Rendered section through `RedactionEngine("strict").redact` is unchanged and `redacted_count == 0` (numbers and ids are not eaten by the phone or ssn rules) | module missing |
| HC-WRB-923 | Packet-path wrapper over WEAR-08's `select_current`: newest reviewed but not included drops the day instead of falling back to an older included import; unreviewed import never offered | wrapper missing |
| HC-WRB-932 | Boundary (WEAR-D3, Opus D1D8 A6): a metric with 13 days and `min_days=14` prints C12 and no number; 14 days prints the median; `>` instead of `>=` or a literal 7 fails | no boundary test |

### 09a-journal — pure (same file)

| ID | Assertion | RED reason |
|---|---|---|
| HC-WRB-906 | Journal entries render under C14/C15 in their own section, sorted by date, text verbatim; wearable section text contains no entry text and no entry date line; no entries → no journal section | module missing |
| HC-WRB-934 | Every journal `COPY` value (C14-C16, C22-C28) equals the literal in §6; the 10 banned words (parametrised, case-insensitive) are absent from the journal section and C14-C16, C22-C28 | journal copy missing |

### 09a-metrics — HTTP (`src/backend/tests/test_wearables_packet.py`; `route_client(export.router, "/export", ...)` with `get_profile_db_session` overridden to a real temp profile DB, the `test_audit_order.py:173` pattern; flag via `monkeypatch.setattr(settings, "wearables_enabled", ...)`). All POST `/export/visit-prep` with `confirm=true`

| ID | Assertion | RED reason |
|---|---|---|
| HC-WRB-910 | Flag off + `include_wearables=true` → 400 with C18; flag off, option absent → 200 as today | field unknown (extra ignored → 200) |
| HC-WRB-911 | Flag on: reviewed + included metric appears; reviewed-not-included and unreviewed metrics absent, checked by their distinct values (covers research HC-WRB-009, F8) | no wiring |
| HC-WRB-912 | Seed `source_name="Jane's Apple Watch"` and import filename "Jane Smith export.zip": absent from `response.markdown`, from `GET .../download?format=markdown` and `format=html` (A7; covers research HC-WRB-012, F8) | no wiring |
| HC-WRB-913 | Profile A and B both have rows with different values; request as B contains B's values and none of A's (assert on values, not names) | no wiring |
| HC-WRB-914 | `ModelRunner` methods monkeypatched to raise; request succeeds and section present. AST check: `packet_section.py` imports nothing from `core.llm`, `ModelRunner` or `llama_cpp` (covers research HC-WRB-011, F7) | no wiring |
| HC-WRB-916 | Default request: `section_titles` equal today's set; wearable fetcher monkeypatched to raise is never called | n/a (guards regressions) |
| HC-WRB-917 | `compose_visit_prep_packet` without `extra_sections` returns the same sections and markdown as before; pinboard export (`api/pinboards.py:501`) still has no wearable section | n/a (guards regressions) |
| HC-WRB-918 | `main.app.openapi()` lists `include_wearables` on `/api/v1/export/visit-prep` (A13: real app, not a bare router; recurring-failures #10). **09a-journal adds** `journal_entry_ids`, `journal_preview_id` and the path `/api/v1/export/visit-prep/journal-preview` | field missing |
| HC-WRB-919 | Static guard (WEAR-02) allow-list now permits `models.wearable` in `api/export.py` only; AST of `_fetch_observations` body has no `wearable` name; `api/observations.py`, `modules/rag.py`, `modules/timeline.py` still clean (A3). **09a-journal adds** `SymptomJournalEntry`/`models.symptom_journal` to the allow-list and to the `_fetch_observations` check (WEAR-15a extends the guard) | guard not updated |
| HC-WRB-920 | **Real master DB** (WEAR-15 HC-WRB-1510 pattern; Opus D1D8 A5): after the packet call, the persisted audit row's `details_json` contains `metrics_included` (reserved by WEAR-02) and no value, import id or `source_name`. **09a-journal adds** `item_count` and no entry text, date or id. A patched `log_export_event` is not used, because the scrubber would hide a missing key | key unused |
| HC-WRB-921 | `RedactionEngine.redact` spied: one call receives text containing C1 (wearable section went through `modules/export.py:637`'s engine) | no wiring |
| HC-WRB-922 | Section order: titles list has wearable section after "Questions for Your Provider" and before "Source Documents" | no wiring |
| HC-WRB-933 | HTTP boundary (Opus D1D8 A6): seed 13 reviewed + included days; `markdown` contains C12 with "at least 14" and no median digits; with `settings.wearables_min_days` patched to 10 the same request prints the median, proving the route passes the setting and not a literal | route hard-codes a minimum |

### 09a-journal — HTTP (same file; all behind the OW-W9 gate)

| ID | Assertion | RED reason |
|---|---|---|
| HC-WRB-915 | Check order from §5: ids without `journal_preview_id` → 400 (C27); a made-up `preview_id` → 400; another profile's `preview_id` → 400; ids differing from the previewed ids → 400; expired preview (clock patched +16 min) → 400; flag off with ids → 400 (C26); 11 ids → 422; empty ids → 200 and no journal section. **Single use:** a second packet call with the same `preview_id` after a successful one → 400. **Bound:** after 20 previews by one profile the store holds ≤ 5 snapshots for it (oldest dropped), and an expired snapshot is purged by the next insert (Opus D1D8 A4) | fields missing |
| HC-WRB-924 | Profile has 3 entries with distinct texts; packet with 1 id contains only that text (checked in `response.markdown`, `GET .../download?format=markdown` and `format=html`); the 2 unselected texts are absent | no wiring |
| HC-WRB-925 | Entry seeded under profile A. As B: **preview** with A's id → 404, and a mixed own + foreign list → 404 for the whole request, body holds neither text nor date. **Packet** with A's id and no valid preview → 400 (C27), because no preview can exist for a foreign id (check order, §5; Opus D1D8 R2). B's own rows unchanged | no wiring |
| HC-WRB-926 | Preview of an entry "call 555-123-4567 or a@b.com" returns date, `[PHONE-REDACTED]`, `[EMAIL-REDACTED]` and `warning == C24`; the stored row text is still raw (nothing written) | route missing |
| HC-WRB-927 | KNOWN GAP, documented not fixed: entry "my wife Jane noticed I was dizzy" → preview response carries `warning == C24`. The test does NOT assert the name is removed and a comment cites `redaction.py:81-88` and OW-W9 | route missing |
| HC-WRB-928 | `ModelRunner` methods monkeypatched to raise; preview and a packet with journal ids both succeed; AST of the preview handler and `packet_section.py` imports nothing from `core.llm`, `ModelRunner`, `llama_cpp` | route missing |
| HC-WRB-929 | **Real master DB** (Opus D1D8 A5): after a preview, the persisted audit row has action "Exported data" (unchanged, registered), `details_json` keys ⊆ `{export_type, count}` with `export_type == "visit_prep_journal_preview"` and `count` present; no entry text, date or id; flag off → 400 (C26) and no DB read | route missing |
| HC-WRB-930 | Confirmed packet: journal section after the wearable section and before "Source Documents"; its text equals the preview text for the same entry; the section holds no metric value; the spied `RedactionEngine.redact` receives text containing C14 (journal passed `modules/export.py:637`) and a phone number in an entry is `[PHONE-REDACTED]` in `markdown` | no wiring |
| HC-WRB-931 | The test edits and deletes the entry **directly in the profile DB** (this file mounts only `export.router`; Opus D1D8 R10). Preview, then update the row (adds "Phone 555-123-4567"), then generate with the old `preview_id` → 409 and no packet stored; preview again → packet text equals the second preview's redacted snapshot exactly (no re-read of text). **Delete after preview (Opus D1D8 A10):** preview, delete the row in the DB, generate → 404 and no packet stored | packet re-reads the row / ignores edits |
| HC-WRB-935 | `audit_and_commit` patched to raise on the preview route (1511 pattern; Opus D1D8 A5): response is 500, the body contains neither entry text nor date, and no snapshot was stored | audit after response |
| HC-WRB-936 | Mounts `wearables.router` and `export.router`. Preview, then `PUT /wearables/journal/{id}` → the store holds no snapshot with that id; generate with the old `preview_id` → 400. Same for `DELETE`. Other profiles' snapshots untouched (Opus D1D8 A3) | no purge on edit/delete |
| HC-WRB-937 | Store holds snapshots for profiles A and B; `POST /profiles/test/reset` as A (`route_client(profiles_router, "/profiles")`) → A's snapshots gone, B's kept; same for `delete_profile`. Needs OW-W12 (Opus D1D8 A4) | no purge on reset/delete |

### Frontend (`src/frontend/src/__tests__/WearablePacketOption.test.tsx`, Windows run, OW-W4); framer-motion mocked with prop filtering (`Accessibility.test.tsx` pattern; INFERRED, file imports ExportPage at its line 18)

**09b-metrics (6):** HC-WRB-951 wearable checkbox absent when status `enabled:false`; 952 present when true; 953 generate sends `include_wearables:true` only when checked; 956 every wearable string (C20, C21) equals §6 and holds no banned word; 957 axe clean on the card; 958 existing `ExportPage.test.tsx` still green.

**09b-journal (5, after OW-W9):** HC-WRB-954 journal list renders entries as React text with a checkbox each, the 11th selection is blocked; 955 "Preview selected entries" posts the selected ids to the preview route and shows the redacted text plus the C24 warning; 959 generate sends `journal_entry_ids` and the `journal_preview_id` from the preview response only after a preview, and changing the selection clears `journalPreviewId` ("Include previewed entries" disabled until previewed again); 960 empty journal shows C25; 961 journal block absent when status `enabled:false`, every journal string (C14, C22-C28) equals §6 with no banned word, and axe stays clean with the picker open.

Counts: **09a-metrics 23** = 10 pure (901-905, 907-909, 923, 932) + 13 HTTP (910-914, 916-922, 933); **09a-journal 14** = 2 pure (906, 934) + 12 HTTP (915, 924-931, 935-937); frontend **09b-metrics 6** (951-953, 956-958), **09b-journal 5** (954, 955, 959-961). Backend total 37 (was 31; new: 932, 933, 934, 935, 936, 937). Rewritten for the journal: 906, 907, 915, 918, 919, 920; new: 924-931, 959-961; dropped: the note-length, six-note and C19 cases (old 915), old frontend 953-955 (typed notes).

Research mapping: 009→911, 010→901+902, 011→914, 012→904+912, 013→903.

## 8. Tasks

Run the Tasks once per PR, in this order: **09a-metrics**, then **09a-journal**, then 09b-metrics, then 09b-journal. Steps marked (M) or (J) belong to that PR only.

### Task 0 — gates
- [ ] (M, J) `git merge-base --is-ancestor <WEAR-02 merge sha> origin/main` and same for WEAR-05, WEAR-07, WEAR-08a; STOP if any fails. (J) also WEAR-15a and 09a-metrics.
- [ ] (J) **OW-W9 gate (Opus D1D8 A1, blocker):** the owner row OW-W9 must be on `origin/main` (`git show origin/main:docs/capstone-report/owner-decisions-2026-09-27.md | grep -n "OW-W9"` shows an answered row, accept-with-preview or a redaction change). **STOP if absent.** Do not write a journal field, the preview route, journal tests or the journal allow-list before it is. (M) does not check this and contains none of them.
- [ ] (J) Rows OW-W12 (purge calls in the profile reset/delete paths) and OW-W11 (via 15a) answered on `origin/main`; STOP if OW-W12 is absent. `grep -n "class SymptomJournalEntry" src/backend/models/symptom_journal.py` finds the model. D2 (b), D3 (14), D8 are on `origin/main` (PR #92). If OW-W8 (new journal strings) is unsigned, build the §6 drafts and keep the PR draft.
- [ ] (M) `grep -n "metrics_included\|export_type" src/backend/core/audit.py` finds both in the allowed sets (`export_type` exists today at `:72`; `metrics_included` is WEAR-02's); (J) also `item_count` (`:95`). `grep -n "wearables_enabled\|wearables_min_days" src/backend/core/config.py` finds both (flag from WEAR-01, min days from WEAR-07).
- [ ] (M) `grep -n "def select_current" src/backend/modules/wearables/select.py` finds WEAR-08's function; STOP if absent (do not write a second copy).
- [ ] Record collected count: `cd src/backend && HF_HUB_OFFLINE=1 python -m pytest --collect-only -q -p no:cacheprovider | tail -1`.

### Task 1 — RED, pure tests
- [ ] (M) Write 901-905, 907-909, 923, 932. (J) Write 906, 934. Run `cd src/backend && HF_HUB_OFFLINE=1 python -m pytest tests/test_wearables_packet_section.py -p no:cacheprovider -q`.
- [ ] Expected (M): collection error `ModuleNotFoundError: modules.wearables.packet_section`. Paste it. (J): the two tests fail on the missing `render_journal_section` / journal `COPY`.

### Task 2 — GREEN, renderer
- [ ] (M) Create `packet_section.py`: `COPY` dict (non-journal strings from §6), `DEVICE_LABELS`, `render_wearable_section(rows, start, end, min_days) -> dict | None`. Imports: stdlib and `modules.wearables.aggregate.describe` only. Build tables with plain f-strings; build new lists, never mutate inputs. Add the step-3 include filter as a small pure helper wrapping `select_current`.
- [ ] (J) Add `render_journal_section(entries) -> dict | None` and the journal `COPY` entries (C14-C16, C22-C28).
- [ ] Run the pure file; expect all green.

### Task 3 — RED, HTTP tests
- [ ] (M) Write 910-914, 916-922, 933. (J) Write 915, 924-931, 935-937 and the journal assertions of 918-920. Run `... pytest tests/test_wearables_packet.py -p no:cacheprovider -q`. Expected RED (M): 910-913, 918-922, 933 fail (fields ignored, no wiring); 916, 917 pass. (J): 915 and 924-931, 935-937 fail (fields ignored, no preview route, no store). Paste output.

### Task 4 — GREEN, wiring
- [ ] (M) `modules/export.py`: add `extra_sections: Optional[list[dict]] = None` to the signature (`:502-514`). Insert `sections.extend(extra_sections or [])` between the Questions block (ends `:621`) and Source Documents (`:623`). It must stay above `engine = RedactionEngine(...)` at `:637`. Footer: if `extra_sections` holds a wearable section use C17 instead of the first sentence of `:646`; otherwise unchanged.
- [ ] (M) `api/export.py`: add `include_wearables`, the flag check, `_fetch_wearable_rows(profile_db, profile_id, start, end)` returning plain dicts (explicit `profile_id` filter plus `ProfileDbSession`), build the section via the renderer with `min_days=settings.wearables_min_days`, pass `extra_sections=`, add `metrics_included` to the audit `details` (`:803-812`). Import `settings` from `core.config`.
- [ ] (J) `api/export.py`: add `journal_entry_ids` / `journal_preview_id`, the check order in §5 (422, flag, preview lookup in `modules/wearables/journal_preview.py` incl. profile, ids, expiry, single use; then 404 / 409 via `_fetch_journal_entries`), the `journal-preview` route (strict `RedactionEngine` called per entry, fixed warning C24, snapshot stored via `put`, `preview_id` returned, `audit_and_commit` with `count` **before** building the body), pop the snapshot after successful generation, add `item_count` to the audit `details`. Create `journal_preview.py` (purge expired on insert, cap 5 per profile, `pop`, `purge_profile`, `purge_entry`). Call `purge_entry` from WEAR-15a's journal PUT/DELETE and `purge_profile` from `api/profiles.py:476` and `:772`.
- [ ] Do not edit `_fetch_observations` or any other fetcher. `api/pinboards.py` is not touched.
- [ ] Update the WEAR-02 static guard allow-list for `api/export.py` only (HC-WRB-919): (M) wearable models; (J) `SymptomJournalEntry` too.
- [ ] Run both files; expect green. Then update the CLAUDE.md and AGENT.md count slots in the same commit: (M) collected = start + 23; (J) collected = start + 14 (parametrised cases may raise the pytest count, so state the exact number from `--collect-only`).

### Task 5 — verify, refactor
- [ ] `cd src/backend && HF_HUB_OFFLINE=1 python -m pytest tests/test_visit_prep_packet.py tests/test_redaction.py tests/test_interpret_safety_adversarial.py tests/test_phase4_ai_safety.py -p no:cacheprovider -q` (existing suites, expect unchanged results).
- [ ] `git diff --stat origin/main -- src/backend/modules/redaction.py src/backend/modules/interpret_safety.py src/backend/tests/test_redaction.py src/backend/tests/test_interpret_safety_adversarial.py` prints nothing. (M) `git diff --stat origin/main -- src/backend/api/profiles.py` prints nothing; (J) it shows only the two purge calls.
- [ ] Full suite: `cd src/backend && flock /tmp/claude-1000/hc-pytest.lock env HF_HUB_OFFLINE=1 python -m pytest -p no:cacheprovider -q`. Only `test_api_rag_index_002b` may fail (embedding model, environmental, CLAUDE.md §4).
- [ ] `security-reviewer` and `code-reviewer` on the diff. Open PR 09a-metrics / 09a-journal.

### Task 6 (09b-metrics, then 09b-journal) — frontend
- [ ] (Mb, after 09a-metrics and WEAR-10) RED: write 951-953, 956-958; `npx vitest run src/__tests__/WearablePacketOption.test.tsx` on Windows fails (component absent). GREEN: in `ExportPage.tsx` add state beside `:73-78` (`includeWearables`), render the checkbox inside the visit-prep card between the Sections block (`:476-494`) and the confirm label (`:525`), only when `useWearablesStatus().data?.enabled`. Send `include_wearables` in the `mutateAsync` body at `:178-188`. Extend `VisitPrepRequest` in `services/export.ts:54-65`.
- [ ] (Jb, after 09a-journal, 09b-metrics, WEAR-15b `useJournalEntries`, and the OW-W9 row on `origin/main`) RED: write 954, 955, 959-961. GREEN: add state `journalSelection`, `journalPreview`, `journalPreviewId` (a server-issued id; Opus D1D8 R8, not a confirmation flag); picker and preview step; send `journal_entry_ids` and `journal_preview_id`. Changing the selection resets `journalPreviewId`. Entry text is rendered as React text only; native checkboxes; no new dependency.
- [ ] Run `npx tsc --noEmit`, `npx eslint`, vitest, axe. Playwright is owner item OW-W4.

## 9. Mutation / break checks (temporary, never committed; `git diff` guard after each revert)

1. Move the `extra_sections` insert below the redaction loop (after `:642`): 930 (J) and 921 (M) fail.
6. (J) Accept any non-empty `journal_preview_id` without looking it up: 915 fails.
10. (J) Skip the `pop` after successful generation: 915 (reuse → 400) fails. Skip the per-profile cap or the expiry purge: 915 fails. Skip `purge_entry` in journal PUT/DELETE: 936 fails. Skip the reset/delete purge: 937 fails.
11. (M) Hard-code `7` or use `>` in the route's minimum-days check: 933 and 932 fail.
12. (J) Write the audit row after building the response body: 935 fails.
7. (J) Drop the `profile_id` filter in `_fetch_journal_entries`: 925 fails.
8. (J) Skip the strict engine in the preview route: 926 fails.
9. (J) Join an entry under a metric row in the renderer: 906 and 930 fail.
2. Remove the `include_in_packet` filter in the fetch: 911 fails.
3. Add `"source_name"` to the rendered device cell: 904 and 912 fail.
4. Drop the `profile_id` filter in `_fetch_wearable_rows`: 913 fails.
5. Put the word "average" in `COPY` C2: 902 and 908 fail.

## 10. Acceptance criteria (seen output, not asserted)

- (J) Task 0 output shows the OW-W9 row on `origin/main` before any journal file exists in the diff; if it did not, the PR is not opened.
- Pure file: all pass, command and last line pasted.
- HTTP file: all pass; RED output from Task 3 pasted before GREEN.
- Existing suites in Task 5 unchanged; `git diff --stat` for ask-first paths empty (output pasted).
- Collected count equals start + 23 (09a-metrics) or start + 14 (09a-journal) (exact number from `--collect-only`); slots updated in the same commit.
- Break checks for the PR (M: 1-5, 11; J: 1, 6-10, 12) each shown red then reverted clean.
- 09b-metrics / 09b-journal: tsc, eslint and vitest output pasted from a Windows run, or the item left open under OW-W4 with that stated.

## 11. Rollback

Revert the PR; revert 09a-journal without touching 09a-metrics. Request fields are additive and default off. No migration, no new table. `_packet_store` and the journal preview store are in memory, so packets and snapshots generated meanwhile vanish on restart. With the flag off the code path is unreachable (400). G-C1's `014_export_artifacts` would persist packets (including journal text that passed strict redaction) in the profile DB; reverting 09a-journal then does not remove packets already stored (see plan 15 section 12; Opus D1D8 A3).

## 12. What these tests cannot see

- **#1 green suite that could not fail.** The existing route tests call `generate_visit_prep` as a plain function (`test_visit_prep_packet.py:295,325`). This plan's route tests go through `route_client`, and 918 reads the real app's schema (preview route included). They still cannot see a broken `Depends` on a route they do not mount.
- **#10 never started / unwired.** 911 and 921 prove compose is wired in the route; the UI option (09b) is proven only by its own tests plus the owner dogfood (OW-W1).
- **#9 invariant at one site.** The "no wearable data outside the packet path" rule is guarded by AST on 4 named files, not on files added later.
- **OPEN RISK — redaction of names in free text (OW-W9).** Strict redaction needs a label word (`redaction.py:81-88`), so "my wife Jane noticed…" passes into the packet. 927 documents this and asserts only that the warning is shown; no test can prove names are removed, and none is claimed. The preview plus warning reduce, not remove, the exposure, and the server cannot verify the patient actually read the preview (931 pins this). Generated packets keep the snapshot text after the entry is edited or deleted (`_packet_store` has no purge); see plan 15 section 12 (Opus D1D8 A3). A name-capable scrubber would touch ask-first `modules/redaction.py` and is the owner's call.
- Whether the wording satisfies FDA general-wellness or FTC HBNR (OD-8, legal). No tool here can see that.
- No test was run while drafting this plan.

## 13. Owner / model-machine items

- **OW-W5** — D2, D3, D8 answered 2026-10-14 (D2 = (b) journal, D3 = 14, D8 = approve); this plan builds them.
- **OW-W8** — owner copy approval for the new journal strings: C14 (rewritten), C19 (removed), C22-C28.
- **OW-W9** — **blocker for 09a-journal and 09b-journal** (Task 0 STOP; Opus D1D8 A1): redaction of names in free text (journal entries reach a third party). Options are a name-capable scrubber (touches ask-first `modules/redaction.py`) or accept the preview-and-warn control. 09a-metrics does not wait.
- **OW-W12** — approve purging in-memory journal preview snapshots in the profile reset/delete paths (`api/profiles.py:476`, `:772`); blocks 09a-journal.
- **OW-W1** — M4 dogfood: generate a packet from the real Apple import, record what it showed (no values in the note). Include one journal entry and read the preview.
- **OW-W4** — 09b vitest, axe and Playwright on Windows.
