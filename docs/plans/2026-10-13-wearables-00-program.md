# WEAR — Apple Watch + Garmin Wearable Module — Program Plan

**Last Updated:** 2026-10-13
**Owner:** repository owner
**Status:** PROPOSED — planning only. No code is licensed by this file. Every code wave waits for milestone M0 (§5).
**Base measured:** `origin/main` @ `8234990` (research package #87 merged at `7630aaa`). Every `file:line` below was re-read at this base on 2026-10-13 unless marked INFERRED.
**Refresh trigger:** OM-1 or OM-2 notes land; the owner answers any decision in [§9](#9-owner-decisions); any profile migration merges (P6, G-C1, AUDIT-ORDER, GAM2 2b); any edit to `api/documents.py`, `api/export.py`, `modules/export.py`, `core/config.py` or `security/input_validator.py`.
**Review:** research package Codex review and response: [`../reviews/2026-10-13/WEAR-RESEARCH-codex.md`](../reviews/2026-10-13/WEAR-RESEARCH-codex.md), [`../reviews/2026-10-13/WEAR-RESEARCH-response.md`](../reviews/2026-10-13/WEAR-RESEARCH-response.md). Fable review of this file: [`../reviews/2026-10-13/WEAR-00-program-fable.md`](../reviews/2026-10-13/WEAR-00-program-fable.md). Codex review of the plan set: [`../reviews/2026-10-13/`](../reviews/2026-10-13/) `WEAR-PLANS-*`.

**Input of record:** [`docs/research/2026-10-12/`](../research/2026-10-12/00-README.md) (00-README … 06-decisions-go-nogo).

## 1. Authority

Owner rows, quoted verbatim from [`owner-decisions-2026-09-27.md`](../capstone-report/owner-decisions-2026-09-27.md) lines 148-150. They are direction, not approval of any plan below.

- **WEAR-OD1** (answer, free text): "Since this project is a research study, can we disclaimer to not use it as professional medical/legal advice. It's about open-sourcing and allowing for development for those who are curious about their healths to track it in a centralized way & develop personal software to track and make use of their health/fitness recording. As I only have Apple & Garmin watch, can we focus on getting the datas from those to be fully-integrated into HealthCentral? The original prompt ask for multi-repo setup with wearable as additional plugin (would multi-repo works, or a single-repo?)"
- **WEAR-OD2** (answer, free text): "Refer to first question's answer for me. If it works better internally within this repo, then in-repo"
- **WEAR-PR** (option chosen): "Yes, docs PR (Recommended)"

What this licenses: planning for Apple + Garmin, in-repo, behind a flag. What it does **not** license: any code before M0; any ask-first edit; any claim about medical-device classification (that stays with OD-8 / OM-7, see research review finding C3).

## 2. Goal and non-goals

**Goal.** A patient can import an Apple Health export ZIP (then a Garmin Connect export), review a per-metric daily summary, see a descriptive "Wearable (patient-recorded)" trend panel, and optionally add a template-rendered, strictly redacted section to the visit-prep packet. Three metrics only: resting heart rate, sleep (asleep minutes), steps.

**Non-goals.** No live sync. No mobile or watch app. No vendor cloud API (Garmin Health API, HealthKit). No ML or LLM inference anywhere in the module. No diagnosis, thresholds, "normal ranges", alerts or causal wording. No SpO₂, HRV, stress, Body Battery, ECG analysis, workout routes or clinical records (`export_cda.xml`). No raw-sample storage. No Samsung. No plugin repository (WEAR-OD2).

## 3. Feature flag

- `wearables_enabled: bool = False` in `core/config.py`, beside the other default-False flags (`ocr_enabled` `core/config.py:123`, `allow_legacy_plaintext_documents` `:126`). Env var `WEARABLES_ENABLED`.
- **Off (default):** every `/wearables/*` route except `GET /wearables/status` returns 404 through one router-level dependency; `GET /wearables/status` returns `{"enabled": false}`; the frontend hides the Wearables nav entry and page; `VisitPrepRequest.include_wearables=true` returns 400. No migration is gated: the new tables exist but stay empty.
- **On:** routes respond; the nav entry shows; the packet option appears.
- Why a status route: no route exposes settings to the frontend today (only `GET /assistant/memory-settings` `api/assistant.py:481-499` and `GET /settings/model` `api/model_settings.py:353` expose single flags). One read-only boolean is the smallest seam.

## 4. Design decisions fixed by evidence (not owner decisions)

| # | Decision | Evidence / reason |
|---|---|---|
| A1 | **Dedicated route `POST /wearables/imports`**, not `POST /documents/import` | `modules/ingest.py:105-106` rejects by extension against the global `supported_doc_types` (`core/config.py:122`), before `detect_doc_type` runs; `IngestModule.import_document` reads the whole upload into memory (`modules/ingest.py:273`). Widening the global list would let `.zip` reach every document path. A dedicated route keeps the documents path unchanged. |
| A2 | **Own provenance table `wearable_imports`**, not a `Document` row | With OD-3 option (b) (no raw ZIP kept), there is no vault file for a `Document` to point to; a `Document` row would also surface in the inbox, timeline and document delete paths. `wearable_daily_metrics.import_id` → `wearable_imports.id`, cascade delete. |
| A3 | **Wearable rows never enter `observations`** | Trends (`api/observations.py:512-540`) and RAG (`modules/rag.py:272-456`, labels only at `:435,:448`) do not filter on `user_verified`. A separate table is the exclusion: no code path in `api/observations.py`, `modules/rag.py`, `modules/timeline.py` or `api/export.py::_fetch_observations` (`:131`) reads it. Pinned by a static import-guard test (WEAR-02). |
| A4 | **"Reviewed", never "verified"** | `patient_reviewed_at` per (import, metric). The wearable trend panel and the packet read only reviewed rows; the packet additionally requires `include_in_packet`. `user_verified` is not reused. |
| A5 | **Daily value semantics** (research Codex C1, C2, ADV-4) | Each row holds **one daily value**: steps = sum of the selected source's records, bucketed by each record's start local date; sleep = length of the **union** of the selected source's asleep intervals (overlaps not double counted), each interval attributed whole to the local date of its **end** (wake date), duration measured between UTC instants so a DST change neither adds nor removes an hour; resting HR = the device's own daily `RestingHeartRate` value (last of the day if several). Median / IQR / min / max / days-with-data are computed **across days** at read time for the review screen, panel and packet. The research contract's per-day `value_median…value_max` columns are dropped. |
| A5b | **Row grain and replacement** (ADV-3) | Rows are **immutable per import**: unique (`import_id`, `metric`, `local_date`). No destructive upsert. The "current" value for (vendor, metric, local date) is chosen at read time: the row from the most recent **reviewed** import that covers that day. Deleting an import removes only its rows, so an older import's values show again. Re-importing the identical file is refused by `content_hash` (409 with the existing import id), not merged. Cross-vendor (Apple and Garmin on the same day): one vendor per metric per day, rule in WEAR-12. |
| A6 | **Local date from the record's own offset** | Each record's timestamp carries its offset (INFERRED format `YYYY-MM-DD HH:MM:SS ±HHMM`, OM-1 confirms). Bucket by that local date; never the host timezone; store `utc_offset_minutes`; `tz_changed` when a day has more than one offset. The repo's `_parse_date` (`modules/import_structured.py:77-96`) drops time and offset and is **not** reused. Audit/created timestamps use `core.time.utcnow` (`core/time.py:9`); any aware → naive conversion uses `core.time.to_naive_utc` (`core/time.py:24`, PR #85). |
| A7 | **No free text from the file in the packet** (ADV-2) | `source_name` can be "Jane's Apple Watch". Strict redaction runs over the packet (`modules/export.py:637`), but its `name_context` rule (`modules/redaction.py:82-88`) needs a label such as "Patient:" and two capitalised tokens, so it does **not** match "Jane's Apple Watch"; `modules/redaction.py` is ask-first and is not changed. The packet prints a device class from a closed map (`Apple Watch`, `iPhone`, `Garmin device`, `Other`), the import date and short import id — never `source_name` or the filename. The redaction test still runs (defence in depth). |
| A8 | **Parsers are pure** | `modules/wearables/` parsers import only the stdlib (`zipfile`, `xml.etree.ElementTree.iterparse`, `json`, `datetime`), no DB and no HealthCentral imports, and emit `wearable-summary` v1 rows (research 03 §5.2). Keeps later extraction a move, not a redesign. |
| A9 | **Hostile-file guards in the parser** | ZIP: member-count cap, per-member and total uncompressed-size caps, reject absolute/`..` member names, read members as streams. XML: reject any `<!DOCTYPE` with an internal subset or `<!ENTITY` before parsing (scan the prolog bytes); `iterparse` with `elem.clear()`; every string through a cap. `defusedxml` is not a dependency (research 03 §3) and none is added. |
| A10 | **Upload never fully in memory** | Starlette spools `UploadFile` above 1 MB to a temp file; the route passes `upload.file` to `zipfile.ZipFile` directly. The temp file is plaintext for the request's lifetime (risk R6). |
| A11 | **Migration number = profile head + 1 at merge time** | Head is `012_pinboards` (`migrations/profile/versions/012_pinboards.py:13`). Claimed next: P6 `013_fk_cascade_alignment` (`implementation-program.md:343`), G-C1 `014_export_artifacts` (`2026-09-27-W11b-…:195`), AUDIT-ORDER `015_audit_outbox` (`2026-10-09-AUDIT-ORDER.md:249`), GAM2 task 2b unnumbered ("whichever lands second renumbers", GAM2-PLAN-APPROVAL `owner-decisions…:134`). WEAR-02 Task 0 reads the head on `origin/main` and takes the next number; it updates the 4 head literals: `tests/test_care_tasks.py:809,825`, `tests/test_profile_migrations_sqlcipher_fallback.py:41`, `tests/test_source_spans.py:313`. |

## 5. Milestones and exit criteria

| M | Name | Exit criteria (all seen, not asserted) |
|---|---|---|
| **M0** | Evidence and decisions | OM-1 notes committed (Apple: member list, record type names, date/offset format, `RestingHeartRate` presence, sleep overlap and stage values per research C2, ZIP size); D1-D4, D8 answered (§9); this plan set Codex-reviewed, findings dispositioned; owner approves the plan set. |
| **M1** | Foundations (flag off) | WEAR-01, WEAR-02, WEAR-03 merged; flag off → `/wearables/*` 404 except status; migration up/down round-trip test green; collected count = start + new tests; no user-visible change. |
| **M2** | Apple import, backend | WEAR-04, WEAR-05, WEAR-06 merged; synthetic export imports over HTTP via `route_client`; hostile fixtures 400 under a memory cap; profile B cannot read A's rows; audit rows hold counts only. |
| **M3** | Review, trends, UI | WEAR-07, WEAR-08, WEAR-10 merged; review screen + panel + disclaimer behind the flag; axe clean; frontend tsc/vitest run on Windows (WSL stall, orchestration.md §4). |
| **M4** | Packet — Apple slice complete | WEAR-09 merged; packet section passes F1/F2/F7/F8/F11 tests; owner dogfoods with the real Apple export on their machine (OW-W1) and records what they saw. |
| **M5** | Garmin slice | OM-2 notes committed; D5 answered; WEAR-11, WEAR-12 merged; cross-vendor overlap rule tested. |
| **M6** | Patient export (optional) | D7 answered "include"; WEAR-13 merged. |

## 6. Work packages and wave map

| ID | Plan | Size (diff) | Depends on |
|---|---|---|---|
| WEAR-01 | [Flag + status route + router skeleton](2026-10-13-wearables-01-flag-router.md) | S (~150) | M0 |
| WEAR-02 | [Data contract + profile migration](2026-10-13-wearables-02-contract-migration.md) | M (~350) | M0 |
| WEAR-03 | [Timestamp, offset and unit normalization](2026-10-13-wearables-03-time-units.md) | S (~250) | M0 (OM-1 formats) |
| WEAR-04 | [Apple export parser (streaming, guarded)](2026-10-13-wearables-04-apple-parser.md) | M (~400) | 03 |
| WEAR-05 | [Daily aggregation, dedup, multi-device overlap](2026-10-13-wearables-05-aggregate-dedup.md) | M (~300) | 03 |
| WEAR-06 | [Import route, persistence, audit, size cap](2026-10-13-wearables-06-import-route.md) | M (~400) | 01, 02, 04, 05; D4 |
| WEAR-07 | [Review queue — backend](2026-10-13-wearables-07-review-backend.md) | M (~300) | 06 |
| WEAR-07b | [Review screen — frontend](2026-10-13-wearables-07b-review-frontend.md) | M (~350) | 07, 10 |
| WEAR-08 | [Descriptive trends (backend route + panel)](2026-10-13-wearables-08-trends.md) | M (~350) | 07 |
| WEAR-09 | [Visit-prep packet section + symptom notes](2026-10-13-wearables-09-packet.md) | M (~350) | 07; D2, D3 |
| WEAR-10 | [Wearables page shell, nav gating, disclaimer copy](2026-10-13-wearables-10-ui-shell-disclaimer.md) | S (~250) | 01; D8 |
| WEAR-11 | [Garmin export parser (JSON, no FIT SDK)](2026-10-13-wearables-11-garmin-parser.md) | M (~400) | 03, 05; OM-2; D5 |
| WEAR-12 | [Garmin wiring + cross-vendor overlap](2026-10-13-wearables-12-garmin-wiring.md) | S (~200) | 06, 11 |
| WEAR-13 | [Patient export of wearable rows](2026-10-13-wearables-13-patient-export.md) | S (~150) | 02; D7 |

Tickets: [`2026-10-13-wearables-tickets.md`](2026-10-13-wearables-tickets.md).

### Wave map

Host rule: at most 2 code L1s at once on the 12 GB box, full suites under `flock` (orchestration.md §2 step 4). Merges are serial; any PR that changes the collected count updates the CLAUDE.md / AGENT.md slots (SLOT-RULE).

| Wave | Runs in parallel | Serial after | Gate before start |
|---|---|---|---|
| WA | WEAR-01 ‖ WEAR-02 ‖ WEAR-03 (disjoint files; run 2 at a time) | — | M0 |
| WB | WEAR-04 ‖ WEAR-05 (both pure, disjoint new files) | WEAR-06 | M1; D4 for 06 |
| WC | WEAR-07 ‖ WEAR-10 | WEAR-07b, then WEAR-08 | M2; D8 for 10 |
| WD | WEAR-09 | — | M3; D2, D3 |
| WE | WEAR-11 | WEAR-12 | M4; OM-2; D5 |
| WF | WEAR-13 | — | D7 = include |

### Dependency graph

```
M0 ──► 01 ─────────────────┐            ┌─► 10 ─► 07b
   ├─► 02 ─────────────────┼─► 06 ─► 07 ┼─► 07b
   └─► 03 ─┬─► 04 ─────────┤            ├─► 08
           └─► 05 ─────────┘            └─► 09 ──► M4 ─► 11 ─► 12
                                    02 ─► 13 (D7)
```

## 7. Owner gates per wave

| Wave | Gate | Kind |
|---|---|---|
| all code | M0 met; owner approves the plan set | OWNER |
| WA | WEAR-02 migration number re-read on `origin/main` at Task 0 | check |
| WB / 06 | D4 (size cap + adding `/api/v1/wearables/imports` to `IMPORT_PATH_PREFIXES`, `security/input_validator.py:18-21`): security middleware, treated as ask-first | OWNER |
| WB / 06 | `core/audit.py` allowlist addition (counts only) — not on the ask-first list; security-reviewer required | review |
| WC / 10 | D8 exact disclaimer and intended-use copy | OWNER |
| WD | D2 symptom notes, D3 minimum days; packet section wording (D8) | OWNER |
| WE | OM-2 notes; D5 FIT / Garmin parser source | OWNER |
| WF | D7 | OWNER |
| any | A touch on `modules/redaction.py`, `modules/interpret_safety.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`, `core/auth.py`, `core/security.py`, encryption → STOP; none is planned | OWNER |

**Ask-first files touched by the plan set: none.** `security/input_validator.py` (WEAR-06) is treated as owner-gated (D4).

## 8. Risk register

| # | Risk | L | I | Mitigation | Owner |
|---|---|---|---|---|---|
| R1 | Apple export format differs from the inferred one (attribute names, date format, sleep values) | M | H | M0 needs OM-1; fixtures built from OM-1 structure; parser skips unknowns with counted reasons | owner (OM-1) |
| R2 | Garmin export layout unknown; FIT licence ("internal business use") | H | M | Garmin slice after M4; JSON-only parser recommended (D5); FIT SDK not added | owner (OM-2, OM-7) |
| R3 | Unreviewed wearable data reaches trends, RAG, timeline or doctor summary | L | H | Separate table (A3); static import-guard test; panel/packet read reviewed rows only | WEAR-02, 08, 09 |
| R4 | Hostile file (zip bomb, entity expansion, giant attributes) | M | H | A9 guards; hostile fixtures with a memory ceiling; size cap (D4) | WEAR-04, 06 |
| R5 | Timezone/DST misbucketing; sleep double-counted across overlapping sources | M | M | A5, A6; DST and overlap fixtures; `tz_changed` footnote | WEAR-03, 05 |
| R6 | Plaintext temp file of the whole export during upload | M | M | Request-scoped; closed in `finally`; documented in the disclaimer page as "processed locally, not kept" (OD-3 b); no copy written elsewhere | WEAR-06 |
| R7 | Personal name in device name or filename leaks into the packet | M | H | A7 closed device map; strict redaction still runs; HTTP test with "Jane's Apple Watch" | WEAR-09 |
| R8 | Wording drifts into medical advice or device claims | M | H | Template-only section; banned-phrase test; `interpret_safety` suite unchanged; copy approved (D8); classification stays open (OD-8) | WEAR-09, 10 |
| R9 | Profile migration collides with P6 / G-C1 / AUDIT-ORDER / GAM2 2b | H | L | A11 head-plus-one at merge; second lander renumbers | WEAR-02 L1 |
| R10 | Green tests that could not fail (route functions called directly; isolation asserted on names) | M | H | All route tests via `tests/support/routes.py::route_client` (`:27`); isolation tests assert on returned values; RED-first logged | every plan |
| R11 | Large export too slow or too big for the 12 GB box | M | M | Streaming parse; perf smoke on a 200 MB synthetic file is an owner/Windows task (OW-W2) | WEAR-04 |

## 9. Owner decisions

At most 8. Each plan that depends on one names it and builds the recommended default unless the owner says otherwise. None is decided by this file.

| ID | Question | Options | Recommended default | Blocks |
|---|---|---|---|---|
| D1 (= OD-3) | Keep the raw export ZIP? | (a) keep encrypted in the vault, (b) keep only SHA-256 + extracted rows | **(b)** — data minimisation; also avoids touching vault encryption (ask-first) | 02, 06 |
| D2 (= OD-4) | Symptom context in the packet | (a) up to 5 dated notes in `VisitPrepRequest`, not persisted, (b) persisted journal, (c) none | **(a)** | 09 |
| D3 (= OD-6) | Minimum days with data before a metric is shown | 5 / **7** / 14 days in the window | **7**, shown with coverage "data on N of M days" | 08, 09 |
| D4 (= OD-7) | Upload size cap for wearables | (a) new `wearables_max_import_mb` used only by the wearables route + add its path to `IMPORT_PATH_PREFIXES`, (b) raise the global 50 MB cap | **(a)**, default sized from OM-1 (placeholder 500 MB) | 06 |
| D5 | Garmin parser source (part of OD-8 / OM-7) | (a) JSON wellness files only, stdlib, no FIT, (b) add `garmin-fit-sdk` after a licence read, (c) stdlib FIT decoder | **(a)**; revisit only if OM-2 shows the 3 metrics are FIT-only | 11 |
| D6 | Are OM-4/OM-5 (clinician/patient conversations) still required? | (a) not for this personal tool; required before any clinical-utility claim, (b) required before M4 | **(a)** | M4 wording |
| D7 | Wearable rows in the patient's own export | (a) add a `wearable_daily_metrics` block with `schema_version` to `GET /export/json` only (D3 full-fidelity route), (b) no export in MVP | **(b)** for MVP; (a) later. A new export route would need redaction (CLAUDE.md "no other export is exempt") | 13 |
| D8 | Exact patient-facing copy: disclaimer banner, intended-use sentence, packet section heading and footer | approve the drafts in WEAR-10 §Copy / WEAR-09 §Copy, or edit | **Approve drafts**; they state "not medical or legal advice" and make **no** medical-device classification claim (pending OD-8 legal read) | 09, 10 |

Carried open from research, not re-asked here: OD-8 legal read before any public distribution (OM-7, OM-8).

## 10. Owner and model-machine queue

No package needs a local model (no LLM in the module). Items for `docs/features/TASK_LIST.md` "Owner and Model-Machine Queue" → "Needs the owner":

- **OW-W0** — OM-1: Apple export notes (research 06 §4), plus research Codex C2: how overlapping sleep records from several sources look, which `HKCategoryValueSleepAnalysis*` values appear.
- **OW-W1** — M4 dogfood: import the real Apple export on the owner's machine with `WEARABLES_ENABLED=true`; record ZIP size, import time, row counts, what the review screen and packet showed (no values in the note).
- **OW-W2** — Windows perf smoke: 200 MB synthetic export import time and peak memory.
- **OW-W3** — OM-2: Garmin export notes before WE.
- **OW-W4** — Frontend vitest/Playwright for WEAR-07b, 08, 10 on Windows (WSL stalls).
- **OW-W5** — Answer D1-D8.

## 11. What this program cannot see

- Whether real exports match any fixture (OM-1/OM-2 only).
- Whether the parser is fast enough on a multi-year export on the owner's hardware (OW-W2).
- Whether a clinician finds the section useful (D6; no study planned).
- Whether the wording satisfies FDA general-wellness or FTC HBNR (OD-8, legal).
