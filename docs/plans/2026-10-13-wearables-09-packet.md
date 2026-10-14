# WEAR-09 — Visit-Prep Packet Section + Symptom Notes — Implementation Plan

**Last Updated:** 2026-10-13
**Owner:** repository owner
**Status:** PROPOSED — not executed (code waits for program M0, WEAR-02 and WEAR-07 merged, and owner decisions D3, D8; D2 only if notes are built).
**Base measured:** `origin/main` @ `8234990`; program file @ `a985390`.
**Refresh trigger:** any edit to `api/export.py`, `modules/export.py`, `api/pinboards.py`, `core/audit.py` or `ExportPage.tsx`; WEAR-02, 05, 07, 08 or 10 merge (their names and signatures are assumed below); D2, D3 or D8 answered.
**Program:** [00-program](2026-10-13-wearables-00-program.md) (A3, A4, A5b, A7, A12, A13; risks R3, R7, R8).
**Depends on:** WEAR-02 (tables, audit vocabulary, static guard), WEAR-05 (`describe()`), WEAR-07 (review state exists), WEAR-08 (owns `modules/wearables/select.py::select_current`; orchestrator decision, this plan reuses it and never re-implements selection), WEAR-10 (`useWearablesStatus`, 09b only). The program table lists 07 only; the orchestrator adds 08 (Question 1).
**Owner decisions:** D2 default **(c): no symptom notes** (program D2; Codex plans ADV-1, R2-1). Notes are built only if the owner signs D2 (a) in writing, accepting that strict redaction does not catch natural-language names; a name-capable sanitizer would touch ask-first `modules/redaction.py` and is a separate owner decision. D3 default 7 days. D8: approve the §Copy table below.
**Size target:** two PRs. **09a backend** ~245 lines of source plus ~400 of tests. **09b frontend** ~120 lines of source plus ~110 of tests. Together they pass 400 lines, so the frontend is a separate section (WEAR-09b) in this file and a separate PR. 09b starts only after 09a and WEAR-10 merge.

> **For agentic workers:** REQUIRED SUB-SKILLS: superpowers:test-driven-development and superpowers:subagent-driven-development. Backend work also loads domain skill `asclexis-backend`. Steps use `- [ ]`.

## 1. Scope

**This plan does:**
- Add `include_wearables: bool = False` to `VisitPrepRequest`. **Symptom notes (`symptom_notes`, everything about them below, copy C21-C24, and their tests) are built only if the owner signs D2 = (a); the program default is D2 = (c), not built** (Codex plans ADV-1: strict redaction does not catch natural-language names).
- Add a pure renderer `modules/wearables/packet_section.py` that turns reviewed + included rows into a markdown section, and a second section for the patient's own notes.
- Insert both sections inside `compose_visit_prep_packet`, before the strict redaction loop, so the whole text is redacted.
- Add one small frontend option on the existing visit-prep card (09b).

**This plan does NOT license:**
- Any edit to `modules/redaction.py`, `modules/interpret_safety.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`, `core/auth.py`, `core/security.py` or encryption. None is touched.
- Any LLM or `ModelRunner` call. The section is a template.
- Reading wearable rows from `_fetch_observations`, trends, RAG, timeline or the doctor summary (A3).
- Persisting symptom notes (D2 option b is a separate decision).
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
| `src/backend/modules/wearables/packet_section.py` | new | Pure renderer: `render_wearable_section`, `render_notes_section`, `COPY`, closed `DEVICE_LABELS` | 110 |
| `src/backend/modules/export.py` | edit | New param `extra_sections`, insert before `:635`; footer variant | 25 |
| `src/backend/api/export.py` | edit | Request fields, flag check, row fetch, build sections, audit count | 75 |
| `src/backend/tests/test_wearables_packet_section.py` | new | Pure renderer tests | 170 |
| `src/backend/tests/test_wearables_packet.py` | new | HTTP tests | 230 |
| WEAR-02 static guard test file | edit | Allow `models.wearable` in `api/export.py` only | 6 |
| `CLAUDE.md`, `AGENT.md` | edit (count slots only) | SLOT-RULE | 2 |
| 09b: `ExportPage.tsx`, `services/export.ts` | edit | Checkbox, notes, request fields | 120 |
| 09b: `src/frontend/src/__tests__/WearablePacketOption.test.tsx` | new | Frontend tests | 110 |

## 4. Ask-first files touched

None. `modules/redaction.py` is read, never edited. The `core/audit.py` vocabulary is reserved by WEAR-02; this plan only uses it. If Task 0 finds `metrics_included` missing there, STOP and fix WEAR-02 first (security-reviewer on that diff).

## 5. Data contract

**Request (additive, defaults keep today's behaviour):**
- `include_wearables: bool = False`.
- `symptom_notes: list[SymptomNote] = []`, `Field(max_length=5)`. `SymptomNote`: `date: date` (ISO), `text: str`, 1-280 chars after strip.
- Rules: `include_wearables=true` while `settings.wearables_enabled` is False returns 400. Non-empty `symptom_notes` with `include_wearables=false` returns 400 (notes ride the same switch and flag). More than 5 notes or a long text returns 422.

**Rows read (profile DB, this profile only):** `wearable_daily_metrics` joined to `wearable_metric_reviews` on (import_id, metric) and `wearable_imports`. Window = request `from_date`..`to_date`; if absent, the 30 days ending `utcnow().date()` (INFERRED default, Question 2). M = days in window.

**Selection (A5b, A4):** 1) fetch only rows whose review has `patient_reviewed_at` set; 2) call WEAR-08's `select_current(rows)` (group by (metric, local_date); most recent reviewed import wins; tie goes to the larger import id); 3) in the packet path, drop rows whose chosen import has `include_in_packet = False`. Step 3 comes after step 2 on purpose: an older included import must not resurface behind a newer one the patient left out.

**Per metric statistics:** `describe(values)` from WEAR-05 (median, p25, p75, min, max, days). No mean anywhere (F1). A metric with fewer than `settings.wearables_min_days` days (D3, default 7; the setting is added by WEAR-07 and reused here, not redefined) prints a suppression line and no numbers.

**Renderer inputs:** plain dicts `{metric, local_date, value, unit, tz_changed, device_class, import_id, imported_at}`. `source_name` and filename are not renderer inputs. Test 904 passes them anyway to prove they are ignored.

**Closed device map:** `apple_watch` → "Apple Watch", `iphone` → "iPhone", `garmin_device` → "Garmin device", anything else → "Other".

**Section dict:** `{"title": str, "content": str}`, same shape as the existing inline sections. Order in the packet: after "Questions for Your Provider", before "Source Documents" (`modules/export.py:616` and `:623`). Wearable section first, notes section after it as its own section, never merged.

**Audit:** existing `log_export_event` call gains `metrics_included` (count of metric tables printed). No note text, no values, no ids (WEAR-02 reserves the key).

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
| C14 | Notes heading | Patient-written notes |
| C15 | Notes line | Written by the patient. Not checked or interpreted. |
| C16 | Note row | - {YYYY-MM-DD}: {text} |
| C17 | Footer variant (only when a wearable section is present) | Except the wearable section, only user-verified data is included in this packet. |
| C18 | 400 flag off | Wearable summary is not available. |
| C19 | 400 notes without option | Symptom notes need the wearable summary option. |
| C20 | 09b checkbox label | Include wearable summary |
| C21 | 09b helper | Adds the wearable measurements you reviewed and marked for the packet. Recorded by a consumer device. Not a clinical measurement. |
| C22 | 09b notes label | Notes about symptoms (optional, up to 5) |
| C23 | 09b note fields | Date / Note / {n} of 280 characters / Add note / Remove note |
| C24 | 09b notes warning | Notes are added to the packet as you write them. Personal names in notes are not always removed automatically. |

C17 keeps the word "verified", so HC-PKT-007 (`tests/test_visit_prep_packet.py:220-227`) still passes. C24 is honest about D2: strict redaction does not catch free-text names without a label word (`modules/redaction.py:81-88`).

## 7. TDD test list

Backend, pure (`src/backend/tests/test_wearables_packet_section.py`):

| ID | Assertion | RED reason |
|---|---|---|
| HC-WRB-901 | Fixture of 10 days renders C1, C2, C3, one row per metric with median, p25-p75, min-max, "10 of 30" matching `describe()`; one outlier day leaves the median unchanged (F1) | module missing |
| HC-WRB-902 | Parametrised over the 10 banned words, case-insensitive: absent from wearable section, notes section and C17, with fixture covering tz footnote, suppressed metric, all device classes (covers research HC-WRB-010, F7, F11) | module missing |
| HC-WRB-903 | Metric with 3 of 30 days prints C12 and no median, min or max digits for it (covers research HC-WRB-013, F2) | module missing |
| HC-WRB-904 | Rows carrying `source_name="Jane's Apple Watch"` and filename "Jane Smith export.zip": neither string, nor "Jane", appears; unknown `device_class` prints "Other" (A7; covers research HC-WRB-012 at unit level) | module missing |
| HC-WRB-905 | C11 appears only when some included day has `tz_changed` | module missing |
| HC-WRB-906 | Notes render in their own section, sorted by date, text verbatim; wearable section text contains no note text and no note date line | module missing |
| HC-WRB-907 | No rows → C13 only; no notes → no notes section | module missing |
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
| HC-WRB-915 | 6 notes → 422; 281-char note → 422; notes with `include_wearables=false` → 400 (C19); a note holding "555-123-4567" and "a@b.com" returns `[PHONE-REDACTED]` and `[EMAIL-REDACTED]`, proving the notes pass the engine | fields missing |
| HC-WRB-916 | Default request: `section_titles` equal today's set; wearable fetcher monkeypatched to raise is never called | n/a (guards regressions) |
| HC-WRB-917 | `compose_visit_prep_packet` without `extra_sections` returns the same sections and markdown as before; pinboard export (`api/pinboards.py:501`) still has no wearable section | n/a (guards regressions) |
| HC-WRB-918 | `main.app.openapi()` schema for `/api/v1/export/visit-prep` lists `include_wearables` and `symptom_notes` (A13: real app, not a bare router; recurring-failures #10) | fields missing |
| HC-WRB-919 | Static guard (WEAR-02) allow-list now permits `models.wearable` in `api/export.py`; AST of `_fetch_observations` body has no `wearable` name; `api/observations.py`, `modules/rag.py`, `modules/timeline.py` still clean (A3) | guard not updated |
| HC-WRB-920 | Audit details captured from patched `log_export_event`: has `metrics_included`; contains no note text, no value, no import id | key unused |
| HC-WRB-921 | `RedactionEngine.redact` spied: one call receives text containing C1 (wearable section went through `modules/export.py:637`'s engine) | no wiring |
| HC-WRB-922 | Section order: titles list has wearable section after "Questions for Your Provider" and before "Source Documents" | no wiring |

Frontend (09b, `src/frontend/src/__tests__/WearablePacketOption.test.tsx`, Windows run, OW-W4): HC-WRB-951 checkbox absent when status `enabled:false`; 952 present when true; 953 generate sends `include_wearables:true` and notes only when checked; 954 sixth note blocked ("Add note" disabled); 955 text capped at 280; 956 every rendered string equals §6 and holds no banned word; 957 axe clean on the card; 958 existing `ExportPage.test.tsx` still green. framer-motion mocked with prop filtering (`Accessibility.test.tsx` pattern; INFERRED, file imports ExportPage at its line 18).

Research mapping: 009→911, 010→901+902, 011→914, 012→904+912, 013→903.

## 8. Tasks

### Task 0 — gates
- [ ] `git merge-base --is-ancestor <WEAR-02 merge sha> origin/main` and same for WEAR-05, WEAR-07; STOP if any fails.
- [ ] Confirm D2, D3, D8 signed. If D8 is unsigned, build the §6 drafts and keep the PR draft.
- [ ] `grep -n "metrics_included" src/backend/core/audit.py` finds the key in the allowed set; `grep -n "wearables_enabled\|wearables_min_days" src/backend/core/config.py` finds both (flag from WEAR-01, min days from WEAR-07).
- [ ] `grep -n "def select_current" src/backend/modules/wearables/select.py` finds WEAR-08's function; STOP if absent (do not write a second copy).
- [ ] Record collected count: `cd src/backend && HF_HUB_OFFLINE=1 python -m pytest --collect-only -q -p no:cacheprovider | tail -1`.

### Task 1 — RED, pure tests
- [ ] Write 901-909, 923. Run `cd src/backend && HF_HUB_OFFLINE=1 python -m pytest tests/test_wearables_packet_section.py -p no:cacheprovider -q`.
- [ ] Expected: collection error `ModuleNotFoundError: modules.wearables.packet_section`. Paste it.

### Task 2 — GREEN, renderer
- [ ] Create `packet_section.py`: `COPY` dict from §6, `DEVICE_LABELS`, `render_wearable_section(rows, start, end, min_days) -> dict | None`, `render_notes_section(notes) -> dict | None`. Imports: stdlib and `modules.wearables.aggregate.describe` only. Build tables with plain f-strings; build new lists, never mutate inputs.
- [ ] Add the step-3 include filter as a small pure helper in `packet_section.py` that wraps `select_current`. Run the pure file; expect all green.

### Task 3 — RED, HTTP tests
- [ ] Write 910-922. Run `... pytest tests/test_wearables_packet.py -p no:cacheprovider -q`. Expected RED: 910, 911, 912, 913, 914, 915, 918, 919, 920, 921, 922 fail (fields ignored, no wiring); 916, 917 pass. Paste output.

### Task 4 — GREEN, wiring
- [ ] `modules/export.py`: add `extra_sections: Optional[list[dict]] = None` to the signature (`:502-514`). Insert `sections.extend(extra_sections or [])` between the Questions block (ends `:621`) and Source Documents (`:623`). It must stay above `engine = RedactionEngine(...)` at `:637`. Footer: if `extra_sections` holds a wearable section use C17 instead of the first sentence of `:646`; otherwise unchanged.
- [ ] `api/export.py`: add `SymptomNote`, the two request fields, the 400 checks (flag, notes without option), `_fetch_wearable_rows(profile_db, profile_id, start, end)` returning plain dicts (explicit `profile_id` filter plus `ProfileDbSession`), build sections via the renderer, pass `extra_sections=`, add `metrics_included` to the audit `details` (`:803-812`). Import `settings` from `core.config`.
- [ ] Do not edit `_fetch_observations` or any other fetcher. `api/pinboards.py` is not touched.
- [ ] Update the WEAR-02 static guard allow-list for `api/export.py` only (HC-WRB-919).
- [ ] Run both files; expect green. Then update the CLAUDE.md and AGENT.md count slots: collected = start + tests added in the same commit.

### Task 5 — verify, refactor
- [ ] `cd src/backend && HF_HUB_OFFLINE=1 python -m pytest tests/test_visit_prep_packet.py tests/test_redaction.py tests/test_interpret_safety_adversarial.py tests/test_phase4_ai_safety.py -p no:cacheprovider -q` (existing suites, expect unchanged results).
- [ ] `git diff --stat origin/main -- src/backend/modules/redaction.py src/backend/modules/interpret_safety.py src/backend/tests/test_redaction.py src/backend/tests/test_interpret_safety_adversarial.py` prints nothing.
- [ ] Full suite: `cd src/backend && flock /tmp/claude-1000/hc-pytest.lock env HF_HUB_OFFLINE=1 python -m pytest -p no:cacheprovider -q`. Only `test_api_rag_index_002b` may fail (embedding model, environmental, CLAUDE.md §4).
- [ ] `security-reviewer` and `code-reviewer` on the diff. Open PR 09a.

### Task 6 (09b) — frontend, after 09a and WEAR-10 merge
- [ ] RED: write 951-958; `npx vitest run src/__tests__/WearablePacketOption.test.tsx` on Windows fails (component absent).
- [ ] GREEN: in `ExportPage.tsx` add state beside `:73-78` (`includeWearables`, `symptomNotes`), render the option inside the visit-prep card between the Sections block (`:476-494`) and the confirm label (`:525`), only when `useWearablesStatus().data?.enabled`. Send both fields in the `mutateAsync` body at `:178-188`. Extend `VisitPrepRequest` in `services/export.ts:54-65`. Keep the markup a native checkbox, `<input type="date">`, `<textarea maxLength=280>`; no new dependency.
- [ ] Run `npx tsc --noEmit`, `npx eslint`, vitest, axe. Playwright is owner item OW-W4.

## 9. Mutation / break checks (temporary, never committed; `git diff` guard after each revert)

1. Move the `extra_sections` insert below the redaction loop (after `:642`): 915 (email not redacted) and 921 fail.
2. Remove the `include_in_packet` filter in the fetch: 911 fails.
3. Add `"source_name"` to the rendered device cell: 904 and 912 fail.
4. Drop the `profile_id` filter in `_fetch_wearable_rows`: 913 fails.
5. Put the word "average" in `COPY` C2: 902 and 908 fail.

## 10. Acceptance criteria (seen output, not asserted)

- Pure file: all pass, command and last line pasted.
- HTTP file: all pass; RED output from Task 3 pasted before GREEN.
- Existing suites in Task 5 unchanged; `git diff --stat` for ask-first paths empty (output pasted).
- Collected count equals start + added; slots updated in the same commit.
- Break checks 1-5 each shown red then reverted clean.
- 09b: tsc, eslint and vitest output pasted from a Windows run, or the item left open under OW-W4 with that stated.

## 11. Rollback

Revert the PR. Request fields are additive and default off. No migration, no new table. `_packet_store` is in memory, so packets generated meanwhile vanish on restart. With the flag off the code path is unreachable (400).

## 12. What these tests cannot see

- **#1 green suite that could not fail.** The existing route tests call `generate_visit_prep` as a plain function (`test_visit_prep_packet.py:295,325`). This plan's route tests go through `route_client`, and 918 reads the real app's schema. They still cannot see a broken `Depends` on a route they do not mount.
- **#10 never started / unwired.** 911 and 921 prove compose is wired in the route; the UI option (09b) is proven only by its own tests plus the owner dogfood (OW-W1).
- **#9 invariant at one site.** The "no wearable data outside the packet path" rule is guarded by AST on 4 named files, not on files added later.
- Free-text names in symptom notes: strict redaction needs a label word (`redaction.py:81-88`), so "my wife Jane gets headaches" passes. That is why D2 defaults to (c) and notes are not built unless the owner signs (a) accepting it. Only the owner can decide on a note scrubber (ask-first file).
- Whether the wording satisfies FDA general-wellness or FTC HBNR (OD-8, legal). No tool here can see that.
- No test was run while drafting this plan.

## 13. Owner / model-machine items

- **OW-W5** — D2, D3, D8 answers (this plan builds the defaults).
- **OW-W1** — M4 dogfood: generate a packet from the real Apple import, record what it showed (no values in the note).
- **OW-W4** — 09b vitest, axe and Playwright on Windows.
