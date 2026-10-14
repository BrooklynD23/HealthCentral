# WEAR-09 — Visit-Prep Packet Section + Symptom Journal Selection — Implementation Plan

**Last Updated:** 2026-10-14
**Amended after WEAR-D2..D8 (owner, 2026-10-14; commit `c53ba44`, PR #92):** D2 = (b) saved symptom journal (typed-in notes replaced by selecting saved entries, with a redacted preview); D3 = 14 days; D8 = approve drafts as written (covers only the pre-amendment strings; new journal strings are OW-W8).
**Owner:** repository owner
**Status:** PROPOSED — not executed (code waits for program M0, WEAR-02, WEAR-07 and WEAR-15a merged; D2, D3, D8 are answered; owner copy approval OW-W8 for the new journal strings).
**Base measured:** `origin/main` @ `8234990`; program file @ `a985390`.
**Refresh trigger:** any edit to `api/export.py`, `modules/export.py`, `api/pinboards.py`, `core/audit.py` or `ExportPage.tsx`; WEAR-02, 05, 07, 08 or 10 merge (their names and signatures are assumed below); WEAR-15 merges; OW-W8 or OW-W9 answered.
**Program:** [00-program](2026-10-13-wearables-00-program.md) (A3, A4, A5b, A7, A12, A13; risks R3, R7, R8).
**Depends on:** WEAR-02 (tables, audit vocabulary, static guard), WEAR-05 (`describe()`), WEAR-07 (review state exists), WEAR-08 (owns `modules/wearables/select.py::select_current`; orchestrator decision, this plan reuses it and never re-implements selection), WEAR-10 (`useWearablesStatus`, 09b only). The program table lists 07 only; the orchestrator adds 08 (Question 1). **WEAR-15a** (table `symptom_journal_entries`, `SymptomJournalEntry`; 09a reads it by id and never writes it); 09b also needs WEAR-15b's `useJournalEntries` hook (otherwise 09b ships its own small query; orchestrator to confirm).
**Owner decisions (resolved):** WEAR-D2: "(b) Saved symptom journal" (the owner did not take the recommendation). Strict redaction does not catch natural-language names (`modules/redaction.py:81-88`), so the packet path adds a mandatory redacted preview, a fixed warning, and an explicit confirmation; "redaction of names in free text" stays an OPEN RISK (OW-W9; a name-capable scrubber would touch ask-first `modules/redaction.py`). WEAR-D3: 14 days. WEAR-D8: drafts approved as written; C14 (rewritten), C19 and C22-C28 are new and need OW-W8.
**Size target:** two PRs. **09a backend** ~290 lines of source plus ~500 of tests. **09b frontend** ~150 lines of source plus ~140 of tests. Together they pass 400 lines, so the frontend is a separate section (WEAR-09b) in this file and a separate PR. 09b starts only after 09a and WEAR-10 merge.

> **For agentic workers:** REQUIRED SUB-SKILLS: superpowers:test-driven-development and superpowers:subagent-driven-development. Backend work also loads domain skill `asclexis-backend`. Steps use `- [ ]`.

## 1. Scope

**This plan does:**
- Add `include_wearables: bool = False`, `journal_entry_ids: list[str] = []` (max 10) and `journal_preview_id: str | None = None` to `VisitPrepRequest` (server-issued preview snapshot, Codex r3 ADV-2). **The journal part of 09a/09b does not start until the owner answers OW-W9** (names in free text, Codex r3 ADV-1); the wearable-metrics part does not wait.
- Add `POST /export/visit-prep/journal-preview`: returns each selected entry's date and text after strict redaction plus a fixed warning (names written in sentences may not be removed). Nothing is stored.
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

| Path | New/edit | Why | ~Lines |
|---|---|---|---|
| `src/backend/modules/wearables/packet_section.py` | new | Pure renderer: `render_wearable_section`, `render_journal_section`, `COPY`, closed `DEVICE_LABELS` | 110 |
| `src/backend/modules/export.py` | edit | New param `extra_sections`, insert before `:635`; footer variant | 25 |
| `src/backend/api/export.py` | edit | Request fields, flag/preview checks, row + journal fetch, preview route, build sections, audit counts | 120 |
| `src/backend/tests/test_wearables_packet_section.py` | new | Pure renderer tests | 170 |
| `src/backend/tests/test_wearables_packet.py` | new | HTTP tests | 330 |
| WEAR-02 static guard test file | edit | Allow `models.wearable` and `models.symptom_journal` (`SymptomJournalEntry`) in `api/export.py` only | 8 |
| `CLAUDE.md`, `AGENT.md` | edit (count slots only) | SLOT-RULE | 2 |
| 09b: `ExportPage.tsx`, `services/export.ts` | edit | Checkbox, journal picker, preview step, request fields | 150 |
| 09b: `src/frontend/src/__tests__/WearablePacketOption.test.tsx` | new | Frontend tests | 140 |

## 4. Ask-first files touched

None. `modules/redaction.py` is read, never edited. The `core/audit.py` vocabulary is reserved by WEAR-02; this plan only uses it. If Task 0 finds `metrics_included` missing there, STOP and fix WEAR-02 first (security-reviewer on that diff).

## 5. Data contract

**Request (additive, defaults keep today's behaviour):**
- `include_wearables: bool = False`.
- `journal_entry_ids: list[str] = []`, `Field(max_length=10)`; `journal_preview_id: str | None = None`. Ids reference WEAR-15's `symptom_journal_entries`; nothing is typed into the request.
- Rules, checked in this order after `confirm`: `include_wearables=true` or non-empty `journal_entry_ids` while `settings.wearables_enabled` is False returns 400 (C18 / C26); non-empty ids without a valid `journal_preview_id` returns 400 (C27) — valid means: issued by the preview route to this profile, for exactly these ids, not expired (15 min), and every entry's `updated_at` unchanged since the preview (else 409, "entry changed since preview"); more than 10 ids returns 422; any id not in this profile returns 404 for the whole request (C28, no entry content in the body). The journal is independent of `include_wearables`.

**Preview route (`api/export.py`, `ProfileDbSession`, flag-gated, audited):** `POST /export/visit-prep/journal-preview`, body `{journal_entry_ids: list[str]}` (1-10 ids, else 422; flag off → 400 C26; unknown or foreign id → 404). Response `{entries: [{id, entry_date, text}], redaction_count, warning}` where `text` went through `RedactionEngine(policy_level="strict")` (called, never edited) and `warning` is the fixed string C24. The route also stores a snapshot `{profile_id, ids, redacted entries, updated_at per entry, expires_at}` in an in-memory `_journal_preview_store` keyed by a new uuid (same pattern and same restart caveat as `_packet_store`, `api/export.py:48`) and returns it as `preview_id`. The stored journal entry stays raw. The packet renders **the snapshot text the patient saw**, never a fresh re-read, so an edit after preview cannot change what is sent. 09b calls the preview, shows it, and sends `journal_preview_id` only afterwards. A caller cannot skip the preview: without a server-issued id the request is 400.

**Journal rows read (profile DB, this profile only):** `_fetch_journal_entries(profile_db, profile_id, ids)` selects by `id IN ids` and `profile_id`, returns plain dicts `{id, entry_date, text}` sorted by date, or signals a missing id (404). Nothing else from the table is read and nothing joins it to wearable rows.

**Wearable rows read (profile DB, this profile only):** `wearable_daily_metrics` joined to `wearable_metric_reviews` on (import_id, metric) and `wearable_imports`. Window = request `from_date`..`to_date`; if absent, the 30 days ending `utcnow().date()` (INFERRED default, Question 2). M = days in window.

**Selection (A5b, A4):** 1) fetch only rows whose review has `patient_reviewed_at` set; 2) call WEAR-08's `select_current(rows)` (group by (metric, local_date); most recent reviewed import wins; tie goes to the larger import id); 3) in the packet path, drop rows whose chosen import has `include_in_packet = False`. Step 3 comes after step 2 on purpose: an older included import must not resurface behind a newer one the patient left out.

**Per metric statistics:** `describe(values)` from WEAR-05 (median, p25, p75, min, max, days). No mean anywhere (F1). A metric with fewer than `settings.wearables_min_days` days (WEAR-D3 = 14; the setting is added by WEAR-07 and reused here, not redefined) prints a suppression line and no numbers.

**Renderer inputs:** plain dicts `{metric, local_date, value, unit, tz_changed, device_class, import_id, imported_at}`. `source_name` and filename are not renderer inputs. Test 904 passes them anyway to prove they are ignored.

**Closed device map:** `apple_watch` → "Apple Watch", `iphone` → "iPhone", `garmin_device` → "Garmin device", anything else → "Other".

**Section dict:** `{"title": str, "content": str}`, same shape as the existing inline sections. Order in the packet: after "Questions for Your Provider", before "Source Documents" (`modules/export.py:616` and `:623`). Wearable section first, journal section after it as its own section, never merged and never joined to metrics. The whole packet, journal text included, still passes the strict engine at `modules/export.py:637`.

**Audit:** the existing `log_export_event` call gains `metrics_included` (WEAR-02 reserves the key) and `item_count` (journal entries included; an existing allowed key, `core/audit.py:95`). The preview route logs `log_export_event(export_type="visit_prep_journal_preview", details={"count": n})` (`export_type` is an allowed string key, `core/audit.py:72`). No `core/audit.py` edit. Never entry text, dates or ids.

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

Backend, pure (`src/backend/tests/test_wearables_packet_section.py`):

| ID | Assertion | RED reason |
|---|---|---|
| HC-WRB-901 | Fixture of 20 days (above the WEAR-D3 14-day minimum) renders C1, C2, C3, one row per metric with median, p25-p75, min-max, "20 of 30" matching `describe()`; one outlier day leaves the median unchanged (F1) | module missing |
| HC-WRB-902 | Parametrised over the 10 banned words, case-insensitive: absent from wearable section, journal section and C17, with fixture covering tz footnote, suppressed metric, all device classes (covers research HC-WRB-010, F7, F11) | module missing |
| HC-WRB-903 | Metric with 3 of 30 days prints C12 and no median, min or max digits for it (covers research HC-WRB-013, F2) | module missing |
| HC-WRB-904 | Rows carrying `source_name="Jane's Apple Watch"` and filename "Jane Smith export.zip": neither string, nor "Jane", appears; unknown `device_class` prints "Other" (A7; covers research HC-WRB-012 at unit level) | module missing |
| HC-WRB-905 | C11 appears only when some included day has `tz_changed` | module missing |
| HC-WRB-906 | Journal entries render under C14/C15 in their own section, sorted by date, text verbatim; wearable section text contains no entry text and no entry date line | module missing |
| HC-WRB-907 | No rows → C13 only; no journal entries → no journal section | module missing |
| HC-WRB-908 | Every `COPY` value equals the literal in §6 (pins D8 approval) | module missing |
| HC-WRB-909 | Rendered section through `RedactionEngine("strict").redact` is unchanged and `redacted_count == 0` (numbers and ids are not eaten by the phone or ssn rules) | module missing |
| HC-WRB-923 | Packet-path wrapper over WEAR-08's `select_current`: newest reviewed but not included drops the day instead of falling back to an older included import; unreviewed import never offered | wrapper missing |

Backend, HTTP (`src/backend/tests/test_wearables_packet.py`; `route_client(export.router, "/export", ...)` with `get_profile_db_session` overridden to a real temp profile DB, the `test_audit_order.py:173` pattern; flag via `monkeypatch.setattr(settings, "wearables_enabled", ...)`). All POST `/export/visit-prep` with `confirm=true`:

| ID | Assertion | RED reason |
|---|---|---|
| HC-WRB-910 | Flag off + `include_wearables=true` → 400 with C18; flag off, option absent → 200 as today | field unknown (extra ignored → 200) |
| HC-WRB-911 | Flag on: reviewed + included metric appears; reviewed-not-included and unreviewed metrics absent, checked by their distinct values (covers research HC-WRB-009, F8) | no wiring |
| HC-WRB-912 | Seed `source_name="Jane's Apple Watch"` and import filename "Jane Smith export.zip": absent from `response.markdown`, from `GET .../download?format=markdown` and `format=html` (A7; covers research HC-WRB-012, F8) | no wiring |
| HC-WRB-913 | Profile A and B both have rows with different values; request as B contains B's values and none of A's (assert on values, not names) | no wiring |
| HC-WRB-914 | `ModelRunner` methods monkeypatched to raise; request succeeds and section present. AST check: `packet_section.py` imports nothing from `core.llm`, `ModelRunner` or `llama_cpp` (covers research HC-WRB-011, F7) | no wiring |
| HC-WRB-915 | ids without `journal_preview_id` → 400 (C27); a made-up `preview_id` → 400; another profile's `preview_id` → 400; ids differing from the previewed ids → 400; expired preview (clock patched +16 min) → 400; flag off with ids → 400 (C26); 11 ids → 422; empty ids → 200 and no journal section | fields missing |
| HC-WRB-916 | Default request: `section_titles` equal today's set; wearable fetcher monkeypatched to raise is never called | n/a (guards regressions) |
| HC-WRB-917 | `compose_visit_prep_packet` without `extra_sections` returns the same sections and markdown as before; pinboard export (`api/pinboards.py:501`) still has no wearable section | n/a (guards regressions) |
| HC-WRB-918 | `main.app.openapi()` lists `include_wearables`, `journal_entry_ids` and `journal_preview_id` on `/api/v1/export/visit-prep` and the path `/api/v1/export/visit-prep/journal-preview` (A13: real app, not a bare router; recurring-failures #10) | fields/route missing |
| HC-WRB-919 | Static guard (WEAR-02, extended by WEAR-15a) allow-list now permits `models.wearable` and `SymptomJournalEntry`/`models.symptom_journal` in `api/export.py` only; AST of `_fetch_observations` body has no `wearable` or `SymptomJournalEntry` name; `api/observations.py`, `modules/rag.py`, `modules/timeline.py` still clean (A3) | guard not updated |
| HC-WRB-920 | Audit details captured from patched `log_export_event`: packet call has `metrics_included` and `item_count`; contains no entry text, date, value or import id | key unused |
| HC-WRB-921 | `RedactionEngine.redact` spied: one call receives text containing C1 (wearable section went through `modules/export.py:637`'s engine) | no wiring |
| HC-WRB-922 | Section order: titles list has wearable section after "Questions for Your Provider" and before "Source Documents" | no wiring |
| HC-WRB-924 | Profile has 3 entries with distinct texts; packet with 1 id contains only that text (checked in `response.markdown`, `GET .../download?format=markdown` and `format=html`); the 2 unselected texts are absent | no wiring |
| HC-WRB-925 | Entry seeded under profile A; request as B with A's id → 404 on both packet and preview, body holds neither text nor date; a list mixing one own and one foreign id → 404 for the whole request; B's own rows unchanged | no wiring |
| HC-WRB-926 | Preview of an entry "call 555-123-4567 or a@b.com" returns date, `[PHONE-REDACTED]`, `[EMAIL-REDACTED]` and `warning == C24`; the stored row text is still raw (nothing written) | route missing |
| HC-WRB-927 | KNOWN GAP, documented not fixed: entry "my wife Jane noticed I was dizzy" → preview response carries `warning == C24`. The test does NOT assert the name is removed and a comment cites `redaction.py:81-88` and OW-W9 | route missing |
| HC-WRB-928 | `ModelRunner` methods monkeypatched to raise; preview and a packet with journal ids both succeed; AST of the preview handler and `packet_section.py` imports nothing from `core.llm`, `ModelRunner`, `llama_cpp` | route missing |
| HC-WRB-929 | Preview route audit (patched `log_export_event`): `export_type == "visit_prep_journal_preview"`, details keys ⊆ `{export_type, count}`, no entry text, date or id; flag off → 400 (C26) and no DB read | route missing |
| HC-WRB-930 | Confirmed packet: journal section after the wearable section and before "Source Documents"; its text equals the preview text for the same entry; the section holds no metric value; the spied `RedactionEngine.redact` receives text containing C14 (journal passed `modules/export.py:637`) and a phone number in an entry is `[PHONE-REDACTED]` in `markdown` | no wiring |
| HC-WRB-931 | Preview, then edit the entry (`PUT /wearables/journal/{id}` adds "Phone 555-123-4567"), then generate with the old `preview_id` → 409 and no packet stored; preview again → packet text equals the second preview's redacted snapshot exactly (no re-read) | packet re-reads the row / ignores edits |

Frontend (09b, `src/frontend/src/__tests__/WearablePacketOption.test.tsx`, Windows run, OW-W4), 10 tests: HC-WRB-951 wearable checkbox and journal block absent when status `enabled:false`; 952 present when true; 953 generate sends `include_wearables:true` only when checked; 954 journal list renders entries as React text with a checkbox each, the 11th selection is blocked; 955 "Preview selected entries" posts the selected ids to the preview route and shows the redacted text plus the C24 warning; 956 every rendered string equals §6 and holds no banned word; 957 axe clean on the card; 958 existing `ExportPage.test.tsx` still green; 959 generate sends `journal_entry_ids` and the `journal_preview_id` from the preview response only after a preview, and changing the selection clears that id ("Include previewed entries" disabled until previewed again); 960 empty journal shows C25. framer-motion mocked with prop filtering (`Accessibility.test.tsx` pattern; INFERRED, file imports ExportPage at its line 18).

Counts: backend 31 = 10 pure (901-909, 923) + 21 HTTP (910-922, 924-931); frontend 10 (951-960). Rewritten for the journal: 906, 907, 915, 918, 919, 920; new: 924-931 and 959-960; dropped: the note-length, six-note and C19 cases (old 915), old frontend 953-955 (typed notes).

Research mapping: 009→911, 010→901+902, 011→914, 012→904+912, 013→903.

## 8. Tasks

### Task 0 — gates
- [ ] `git merge-base --is-ancestor <WEAR-02 merge sha> origin/main` and same for WEAR-05, WEAR-07; STOP if any fails.
- [ ] Confirm WEAR-15a is merged (`git merge-base --is-ancestor <WEAR-15a sha> origin/main`; `grep -n "class SymptomJournalEntry" src/backend/models/symptom_journal.py`); STOP if absent. D2 (b), D3 (14), D8 are on `origin/main` (PR #92). If OW-W8 (new journal strings) is unsigned, build the §6 drafts and keep the PR draft.
- [ ] `grep -n "metrics_included\|item_count\|export_type" src/backend/core/audit.py` finds all three in the allowed sets (`item_count` and `export_type` exist today at `:95` and `:72`); `grep -n "wearables_enabled\|wearables_min_days" src/backend/core/config.py` finds both (flag from WEAR-01, min days from WEAR-07).
- [ ] `grep -n "def select_current" src/backend/modules/wearables/select.py` finds WEAR-08's function; STOP if absent (do not write a second copy).
- [ ] Record collected count: `cd src/backend && HF_HUB_OFFLINE=1 python -m pytest --collect-only -q -p no:cacheprovider | tail -1`.

### Task 1 — RED, pure tests
- [ ] Write 901-909, 923. Run `cd src/backend && HF_HUB_OFFLINE=1 python -m pytest tests/test_wearables_packet_section.py -p no:cacheprovider -q`.
- [ ] Expected: collection error `ModuleNotFoundError: modules.wearables.packet_section`. Paste it.

### Task 2 — GREEN, renderer
- [ ] Create `packet_section.py`: `COPY` dict from §6, `DEVICE_LABELS`, `render_wearable_section(rows, start, end, min_days) -> dict | None`, `render_journal_section(entries) -> dict | None`. Imports: stdlib and `modules.wearables.aggregate.describe` only. Build tables with plain f-strings; build new lists, never mutate inputs.
- [ ] Add the step-3 include filter as a small pure helper in `packet_section.py` that wraps `select_current`. Run the pure file; expect all green.

### Task 3 — RED, HTTP tests
- [ ] Write 910-922 and 924-931. Run `... pytest tests/test_wearables_packet.py -p no:cacheprovider -q`. Expected RED: 910-915, 918-922 and 924-931 fail (fields ignored, no wiring, no preview route); 916, 917 pass. Paste output.

### Task 4 — GREEN, wiring
- [ ] `modules/export.py`: add `extra_sections: Optional[list[dict]] = None` to the signature (`:502-514`). Insert `sections.extend(extra_sections or [])` between the Questions block (ends `:621`) and Source Documents (`:623`). It must stay above `engine = RedactionEngine(...)` at `:637`. Footer: if `extra_sections` holds a wearable section use C17 instead of the first sentence of `:646`; otherwise unchanged.
- [ ] `api/export.py`: add the three request fields, the checks in §5 order (flag, `journal_preview_id` lookup in `_journal_preview_store` incl. profile, ids, expiry and `updated_at`, 404 via `_fetch_journal_entries`), the `journal-preview` route (strict `RedactionEngine` called per entry, fixed warning C24, snapshot stored, `preview_id` returned, audit `count`); the packet renders the snapshot text, `_fetch_wearable_rows(profile_db, profile_id, start, end)` returning plain dicts (explicit `profile_id` filter plus `ProfileDbSession`), build sections via the renderer, pass `extra_sections=`, add `metrics_included` and `item_count` to the audit `details` (`:803-812`). Import `settings` from `core.config`.
- [ ] Do not edit `_fetch_observations` or any other fetcher. `api/pinboards.py` is not touched.
- [ ] Update the WEAR-02 static guard allow-list for `api/export.py` only (HC-WRB-919): wearable models and `SymptomJournalEntry`.
- [ ] Run both files; expect green. Then update the CLAUDE.md and AGENT.md count slots: collected = start + 31 (all of 901-909, 910-931 are new tests; parametrised cases may raise the pytest count, so state the exact number from `--collect-only`) in the same commit.

### Task 5 — verify, refactor
- [ ] `cd src/backend && HF_HUB_OFFLINE=1 python -m pytest tests/test_visit_prep_packet.py tests/test_redaction.py tests/test_interpret_safety_adversarial.py tests/test_phase4_ai_safety.py -p no:cacheprovider -q` (existing suites, expect unchanged results).
- [ ] `git diff --stat origin/main -- src/backend/modules/redaction.py src/backend/modules/interpret_safety.py src/backend/tests/test_redaction.py src/backend/tests/test_interpret_safety_adversarial.py` prints nothing.
- [ ] Full suite: `cd src/backend && flock /tmp/claude-1000/hc-pytest.lock env HF_HUB_OFFLINE=1 python -m pytest -p no:cacheprovider -q`. Only `test_api_rag_index_002b` may fail (embedding model, environmental, CLAUDE.md §4).
- [ ] `security-reviewer` and `code-reviewer` on the diff. Open PR 09a.

### Task 6 (09b) — frontend, after 09a, WEAR-10 and WEAR-15b (`useJournalEntries`) merge
- [ ] RED: write 951-960; `npx vitest run src/__tests__/WearablePacketOption.test.tsx` on Windows fails (component absent).
- [ ] GREEN: in `ExportPage.tsx` add state beside `:73-78` (`includeWearables`, `journalSelection`, `journalPreview`, `journalConfirmed`), render the option inside the visit-prep card between the Sections block (`:476-494`) and the confirm label (`:525`), only when `useWearablesStatus().data?.enabled`. Send the three fields in the `mutateAsync` body at `:178-188`. Extend `VisitPrepRequest` in `services/export.ts:54-65`. Entry text is rendered as React text only; native checkboxes; no new dependency. Changing the selection resets `journalConfirmed`.
- [ ] Run `npx tsc --noEmit`, `npx eslint`, vitest, axe. Playwright is owner item OW-W4.

## 9. Mutation / break checks (temporary, never committed; `git diff` guard after each revert)

1. Move the `extra_sections` insert below the redaction loop (after `:642`): 930 (phone not redacted in the packet) and 921 fail.
6. Accept any non-empty `journal_preview_id` without looking it up: 915 fails.
7. Drop the `profile_id` filter in `_fetch_journal_entries`: 925 fails.
8. Skip the strict engine in the preview route: 926 fails.
9. Join an entry under a metric row in the renderer: 906 and 930 fail.
2. Remove the `include_in_packet` filter in the fetch: 911 fails.
3. Add `"source_name"` to the rendered device cell: 904 and 912 fail.
4. Drop the `profile_id` filter in `_fetch_wearable_rows`: 913 fails.
5. Put the word "average" in `COPY` C2: 902 and 908 fail.

## 10. Acceptance criteria (seen output, not asserted)

- Pure file: all pass, command and last line pasted.
- HTTP file: all pass; RED output from Task 3 pasted before GREEN.
- Existing suites in Task 5 unchanged; `git diff --stat` for ask-first paths empty (output pasted).
- Collected count equals start + 31 (exact number from `--collect-only`); slots updated in the same commit.
- Break checks 1-9 each shown red then reverted clean.
- 09b: tsc, eslint and vitest output pasted from a Windows run, or the item left open under OW-W4 with that stated.

## 11. Rollback

Revert the PR. Request fields are additive and default off. No migration, no new table. `_packet_store` is in memory, so packets generated meanwhile vanish on restart. With the flag off the code path is unreachable (400).

## 12. What these tests cannot see

- **#1 green suite that could not fail.** The existing route tests call `generate_visit_prep` as a plain function (`test_visit_prep_packet.py:295,325`). This plan's route tests go through `route_client`, and 918 reads the real app's schema (preview route included). They still cannot see a broken `Depends` on a route they do not mount.
- **#10 never started / unwired.** 911 and 921 prove compose is wired in the route; the UI option (09b) is proven only by its own tests plus the owner dogfood (OW-W1).
- **#9 invariant at one site.** The "no wearable data outside the packet path" rule is guarded by AST on 4 named files, not on files added later.
- **OPEN RISK — redaction of names in free text (OW-W9).** Strict redaction needs a label word (`redaction.py:81-88`), so "my wife Jane noticed…" passes into the packet. 927 documents this and asserts only that the warning is shown; no test can prove names are removed, and none is claimed. The preview plus warning and explicit confirmation reduce, not remove, the exposure, and the server cannot verify the patient actually read the preview (931 pins this). A name-capable scrubber would touch ask-first `modules/redaction.py` and is the owner's call.
- Whether the wording satisfies FDA general-wellness or FTC HBNR (OD-8, legal). No tool here can see that.
- No test was run while drafting this plan.

## 13. Owner / model-machine items

- **OW-W5** — D2, D3, D8 answered 2026-10-14 (D2 = (b) journal, D3 = 14, D8 = approve); this plan builds them.
- **OW-W8** — owner copy approval for the new journal strings: C14 (rewritten), C19 (removed), C22-C28.
- **OW-W9** — owner follow-up: redaction of names in free text (journal entries reach a third party). Options are a name-capable scrubber (touches ask-first `modules/redaction.py`) or accept the preview-and-warn control.
- **OW-W1** — M4 dogfood: generate a packet from the real Apple import, record what it showed (no values in the note). Include one journal entry and read the preview.
- **OW-W4** — 09b vitest, axe and Playwright on Windows.
