# WEAR — Apple Watch + Garmin Wearable Module — Program Plan

**Last Updated:** 2026-10-14 (owner answered D1-D8: owner, 2026-10-14, rows WEAR-D1..WEAR-D8, commit `c53ba44`, PR #92; D2, D3, D5, D7 differ from the recommendations and are applied below)
**Owner:** repository owner
**Status:** PROPOSED — planning only. No code is licensed by this file. D1-D8 are resolved (§9); every code wave still waits for milestone M0 (§5): OM-1 notes and owner approval of this plan set.
**Base measured:** `origin/main` @ `8234990` (research package #87 merged at `7630aaa`). Every `file:line` below was re-read at this base on 2026-10-13 unless marked INFERRED.
**Refresh trigger:** OM-1 or OM-2 notes land; the owner answers any decision in [§9](#9-owner-decisions); any profile migration merges (P6, G-C1, AUDIT-ORDER, GAM2 2b); any edit to `api/documents.py`, `api/export.py`, `modules/export.py`, `core/config.py` or `security/input_validator.py`.
**Review:** after the owner answers, Codex r3 needs-attention (5 findings, all accepted and applied, not re-reviewed): [`../reviews/2026-10-14/WEAR-PLANS-r3-response.md`](../reviews/2026-10-14/WEAR-PLANS-r3-response.md). Before them: plan set Codex r1 needs-attention (10 findings: 9 accepted, 1 partial) and r2 needs-attention (6 findings, all accepted and fixed after r2; not re-reviewed, round cap 2 per `docs/agentic/orchestration.md` §5): [`../reviews/2026-10-13/WEAR-PLANS-r1-response.md`](../reviews/2026-10-13/WEAR-PLANS-r1-response.md), [`../reviews/2026-10-13/WEAR-PLANS-r2-response.md`](../reviews/2026-10-13/WEAR-PLANS-r2-response.md). Research package Codex review and response: [`../reviews/2026-10-13/WEAR-RESEARCH-codex.md`](../reviews/2026-10-13/WEAR-RESEARCH-codex.md), [`../reviews/2026-10-13/WEAR-RESEARCH-response.md`](../reviews/2026-10-13/WEAR-RESEARCH-response.md). Fable review of this file: [`../reviews/2026-10-13/WEAR-00-program-fable.md`](../reviews/2026-10-13/WEAR-00-program-fable.md) — GO WITH AMENDMENTS (5 MAJOR, 7 MINOR), all 12 accepted and applied ([response](../reviews/2026-10-13/WEAR-00-program-fable-response.md)). Codex review of the plan set: [`../reviews/2026-10-13/`](../reviews/2026-10-13/) `WEAR-PLANS-*`.

**Input of record:** [`docs/research/2026-10-12/`](../research/2026-10-12/00-README.md) (00-README … 06-decisions-go-nogo).

## 1. Authority

Owner rows, quoted verbatim from [`owner-decisions-2026-09-27.md`](../capstone-report/owner-decisions-2026-09-27.md) lines 148-150. They are direction, not approval of any plan below.

- **WEAR-OD1** (answer, free text): "Since this project is a research study, can we disclaimer to not use it as professional medical/legal advice. It's about open-sourcing and allowing for development for those who are curious about their healths to track it in a centralized way & develop personal software to track and make use of their health/fitness recording. As I only have Apple & Garmin watch, can we focus on getting the datas from those to be fully-integrated into HealthCentral? The original prompt ask for multi-repo setup with wearable as additional plugin (would multi-repo works, or a single-repo?)"
- **WEAR-OD2** (answer, free text): "Refer to first question's answer for me. If it works better internally within this repo, then in-repo"
- **WEAR-PR** (option chosen): "Yes, docs PR (Recommended)"

What this licenses: planning for Apple + Garmin, in-repo, behind a flag. What it does **not** license: any code before M0; any ask-first edit; any claim about medical-device classification (that stays with OD-8 / OM-7, see research review finding C3).

## 2. Goal and non-goals

**Goal.** A patient can import an Apple Health export ZIP (then a Garmin Connect export), review a per-metric daily summary, see a descriptive "Wearable (patient-recorded)" trend panel, keep a saved symptom journal (WEAR-D2), and optionally add a template-rendered, strictly redacted section to the visit-prep packet, with journal entries only by per-entry selection after a redacted preview. Wearable rows are also in the patient's own `GET /export/json` (WEAR-D7). Three metrics only: resting heart rate, sleep (asleep minutes), steps.

**Non-goals.** No live sync. No mobile or watch app. No vendor cloud API (Garmin Health API, HealthKit). No ML or LLM inference anywhere in the module. No diagnosis, thresholds, "normal ranges", alerts or causal wording. No SpO₂, HRV, stress, Body Battery, ECG analysis, workout routes or clinical records (`export_cda.xml`). No raw-sample storage. No Samsung. No plugin repository (WEAR-OD2).

## 3. Feature flag

- `wearables_enabled: bool = False` in `core/config.py`, beside the other default-False flags (`ocr_enabled` `core/config.py:123`, `allow_legacy_plaintext_documents` `:126`). Env var `WEARABLES_ENABLED`.
- **Off (default):** every `/wearables/*` route except `GET /wearables/status` returns 404. Two routers share the `/wearables` prefix: an ungated status router and a gated router whose `APIRouter(dependencies=[...])` raises 404 (a router-level dependency would also gate `/status`; Fable F8). The upload size cap for the wearables path applies only when the flag is on (D4), so a flag-off upload stays under the default 10 MB body limit (`security/input_validator.py:38`) before the 404 — FastAPI parses the multipart body before dependencies run (`fastapi/routing.py:430` vs `:481`); `GET /wearables/status` returns `{"enabled": false}`; the frontend hides the Wearables nav entry and page; `VisitPrepRequest.include_wearables=true` returns 400. No migration is gated: the new tables exist but stay empty.
- **On:** routes respond; the nav entry shows; the packet option appears.
- Why a status route: no route exposes settings to the frontend today (only `GET /assistant/memory-settings` `api/assistant.py:481-499` and `GET /settings/model` `api/model_settings.py:353` expose single flags). One read-only boolean is the smallest seam.

## 4. Design decisions fixed by evidence (not owner decisions)

| # | Decision | Evidence / reason |
|---|---|---|
| A1 | **Dedicated route `POST /wearables/imports`**, not `POST /documents/import` | `modules/ingest.py:105-106` rejects by extension against the global `supported_doc_types` (`core/config.py:122`), before `detect_doc_type` runs; `IngestModule.import_document` reads the whole upload into memory (`modules/ingest.py:273`). Widening the global list would let `.zip` reach every document path. A dedicated route keeps the documents path unchanged. |
| A2 | **Own provenance table `wearable_imports`**, not a `Document` row | With OD-3 option (b) (no raw ZIP kept), there is no vault file for a `Document` to point to; a `Document` row would also surface in the inbox, timeline and document delete paths. `wearable_daily_metrics.import_id` → `wearable_imports.id` declares `ON DELETE CASCADE`, but **SQLite does not enforce it here**: `PRAGMA foreign_keys` is set nowhere (`api/profiles.py:939-942`; P6 is unmerged). Every delete therefore deletes child rows explicitly before the parent (recurring-failures #9), and a test asserts zero child rows after delete. |
| A3 | **Wearable rows never enter `observations`** | Trends (`api/observations.py:512-540`) and RAG (`modules/rag.py:272-456`, labels only at `:435,:448`) do not filter on `user_verified`. A separate table is the exclusion: no code path in `api/observations.py`, `modules/rag.py`, `modules/timeline.py` or `api/export.py::_fetch_observations` (`:131`) reads it. Pinned by a static import-guard test (WEAR-02). |
| A4 | **"Reviewed", never "verified"** | `patient_reviewed_at` per (import, metric). The wearable trend panel and the packet read only reviewed rows; the packet additionally requires `include_in_packet`. `user_verified` is not reused. |
| A5 | **Daily value semantics** (research Codex C1, C2, ADV-4) | Each row holds **one daily value**: steps = sum of the selected source's records, bucketed by each record's start local date; sleep = length of the **union** of the selected source's asleep intervals (overlaps not double counted), each interval attributed whole to the local date of its **end** (wake date), duration measured between UTC instants so a DST change neither adds nor removes an hour; resting HR = the device's own daily `RestingHeartRate` value (last of the day if several). Median / IQR / min / max / days-with-data are computed **across days** at read time for the review screen, panel and packet. The research contract's per-day `value_median…value_max` columns are dropped. |
| A5b | **Row grain and replacement** (ADV-3) | Rows are **immutable per import**: unique (`import_id`, `metric`, `local_date`). No destructive upsert. The "current" value for (vendor, metric, local date) is chosen at read time: the row from the most recent **reviewed** import that covers that day. Deleting an import removes only its rows, so an older import's values show again. Re-importing the identical file is refused by `content_hash` (409 with the existing import id), not merged. The upload is a raw `application/zip` body: `request.stream()` is written to an app-owned temp file while a SHA-256 is updated per chunk (D6 default (b), WEAR-06), then `zipfile` opens that file — never a whole-file read, never multipart (Fable F12, Codex plans ADV-3). Cross-vendor (Apple and Garmin on the same day): one vendor per metric per day, rule in WEAR-12. Selection lives in one pure function, `modules/wearables/select.py::select_current` (created by WEAR-08, reused by WEAR-09 and WEAR-12); ZIP guards live in one pure module, `modules/wearables/_zipguard.py` (created by WEAR-04, reused by WEAR-11). |
| A6 | **Local date from the record's own offset** | Each record's timestamp carries its offset (INFERRED format `YYYY-MM-DD HH:MM:SS ±HHMM`, OM-1 confirms). Bucket by that local date; never the host timezone; store `utc_offset_minutes`; `tz_changed` when a day has more than one offset. The repo's `_parse_date` (`modules/import_structured.py:77-97`) drops time and offset and is **not** reused. Audit/created timestamps use `core.time.utcnow` (`core/time.py:9`); any aware → naive conversion uses `core.time.to_naive_utc` (`core/time.py:24`, PR #85). |
| A7 | **No free text from the file in the packet** (ADV-2) | `source_name` can be "Jane's Apple Watch". Strict redaction runs over the packet (`modules/export.py:637`), but its `name_context` rule (`modules/redaction.py:82-88`) needs a label such as "Patient:" and two capitalised tokens, so it does **not** match "Jane's Apple Watch"; `modules/redaction.py` is ask-first and is not changed. The packet prints a device class from a closed map (`Apple Watch`, `iPhone`, `Garmin device`, `Other`), the import date and short import id — never `source_name` or the filename. The redaction test still runs (defence in depth). |
| A8 | **Parsers are pure** | `modules/wearables/` parsers import only the stdlib (`zipfile`, `xml.etree.ElementTree.iterparse`, `json`, `datetime`), no DB and no HealthCentral imports, and emit `wearable-summary` v1 rows (research 03 §5.2). Keeps later extraction a move, not a redesign. **One named exception (WEAR-D5):** `modules/wearables/garmin_fit.py` imports the pinned `garmin-fit-sdk`; no other module may (AST guard, WEAR-11b). |
| A9 | **Hostile-file guards in the parser** | ZIP: member-count cap, per-member and total uncompressed-size caps **counted on bytes actually read** (header `file_size`/`compress_size` are attacker-controlled; a fixture lies in the header, Fable F9), reject absolute/`..` member names, read members as streams. XML: scan the prolog bytes before parsing and reject any `<!ENTITY` declaration or external identifier (`SYSTEM`/`PUBLIC`) in the DOCTYPE; an internal subset holding only `<!ELEMENT`/`<!ATTLIST` is allowed, because real Apple exports are believed to carry one (INFERRED, OM-1 shows the real prolog; a blanket internal-subset reject would refuse every real export); depth and longest-token caps; `iterparse` with `elem.clear()`; every string through a cap. `defusedxml` is not a dependency (research 03 §3) and none is added. |
| A10 | **Upload never fully in memory** | Starlette spools `UploadFile` above 1 MB to a `SpooledTemporaryFile` in the **OS temp dir** (`%TEMP%` on Windows), unencrypted, outside `app_data_path`; the route passes `upload.file` to `zipfile.ZipFile` directly. A crash leaves the plaintext export there. Owner decision D6 chooses between accepting that and streaming to an app-owned temp path with a startup sweep (risk R6). |
| A11 | **Migration number = profile head + 1 at merge time** | Head is `012_pinboards` (`migrations/profile/versions/012_pinboards.py:13`). Claimed next: P6 `013_fk_cascade_alignment` (`implementation-program.md:343`), G-C1 `014_export_artifacts` (`2026-09-27-W11b-…:195`), AUDIT-ORDER `015_audit_outbox` (`2026-10-09-AUDIT-ORDER.md:249`), GAM2 task 2b unnumbered ("whichever lands second renumbers", GAM2-PLAN-APPROVAL `owner-decisions…:134`). Paths: `docs/capstone-report/implementation-program.md:343`, `docs/plans/2026-09-27-W11b-roadmap-items-gc1-gc4.md:195`, `docs/plans/2026-10-09-AUDIT-ORDER.md:249`, `docs/capstone-report/owner-decisions-2026-09-27.md:134`. WEAR-02 Task 0 reads the head on `origin/main` and takes the next number; it updates the 4 head literals: `tests/test_care_tasks.py:809,825`, `tests/test_profile_migrations_sqlcipher_fallback.py:41`, `tests/test_source_spans.py:313`. |
| A12 | **Shared registries owned once** (Fable F3, F6) | WEAR-02 adds the three models to `core/profile_database.py:409-417` (the `create_all` import list), `models/__init__.py`, and the synthetic-reset tuple `api/profiles.py:498-515` (children before parents), with a reset test. WEAR-02 also reserves the whole audit vocabulary once in `core/audit.py`: actions (`ALLOWED_ACTIONS` `:36`) for import, review, delete, metrics view, and string keys `import_id`, `vendor` (absent from `STRING_DETAIL_KEYS` `:69-76`, so the scrubber would drop them silently) plus count keys; `metric` is deliberately **not** reserved, so which metric a patient reviewed stays out of the master audit log (Codex plans R2-6). Later packages only use them; a test asserts the scrubbed details still hold them. Every `core/audit.py` diff gets a security-reviewer pass. |
| A13 | **Real-app tests per milestone** (Fable F5) | `route_client` mounts the router on a bare app (`tests/support/routes.py:27-35`), so it cannot see a missing mount in `api/__init__.py`, the InputValidation cap, or the flag-off 404 at the real prefix. Each milestone adds `TestClient(main.app)` tests: `/api/v1/wearables/status` reachable; flag off → 404; oversize → 413 (recurring-failures #10). |
| A14 | **One copy of the enums** | `METRICS`, `VENDORS`, `DEVICE_CLASSES` and the canonical unit map exist once. WEAR-02 (`modules/wearables/contract.py`) and WEAR-03 (`modules/wearables/records.py`) both plan them; whichever merges second deletes its copy and imports the other's, so no parity test is needed. |

## 5. Milestones and exit criteria

| M | Name | Exit criteria (all seen, not asserted) |
|---|---|---|
| **M0** | Evidence and plan approval | OM-1 notes committed (Apple: member list, record type names, date/offset format, `RestingHeartRate` presence, sleep overlap and stage values per research C2, XML prolog, duplicate records, ZIP size); D1-D8 answered (done 2026-10-14, owner, 2026-10-14, rows WEAR-D1..WEAR-D8, commit `c53ba44`, PR #92); this plan set Codex-reviewed, findings dispositioned; owner approves the plan set. |
| **M1** | Foundations (flag off) | WEAR-01, WEAR-02, WEAR-03 merged; flag off → `/wearables/*` 404 except status, proven on `TestClient(main.app)` at `/api/v1/wearables/...` (A13); synthetic reset clears the new tables; migration up/down round-trip test green; collected count = start + new tests; no user-visible change. |
| **M2** | Apple import, backend | WEAR-04, WEAR-05, WEAR-06 merged; synthetic export imports over HTTP via `route_client`; oversize upload → 413 on `main.app`; hostile fixtures 400 under a memory cap; profile B cannot read A's rows; audit rows hold counts plus opaque `import_id` and `vendor` enum only. |
| **M3** | Review, trends, UI | WEAR-07, WEAR-08, WEAR-10 merged; review screen + panel + disclaimer behind the flag; axe clean; frontend tsc/vitest run on Windows (WSL stall, orchestration.md §4). |
| **M4** | Packet, journal, patient export — Apple slice complete | WEAR-15a/15b, WEAR-09a/09b, WEAR-13 merged; packet section passes F1/F2/F7/F8/F11 tests; **OW-W9 answered by the owner** before any journal entry can reach the packet (otherwise WEAR-09 ships the metrics section only and the journal stays out of the packet); journal entries reach the packet only through per-entry selection + a server-issued strict-redacted preview snapshot (`preview_id`); `/export/json?include_wearables=true` carries the versioned block; owner dogfoods with the real Apple export (OW-W1). |
| **M5** | Garmin slice | OM-2 notes committed; WEAR-11a, WEAR-12 merged; WEAR-11b only if OM-2 shows an in-scope metric only in FIT **and** the FIT licence read (OW-W7) is recorded as `WEAR-FIT-LIC`; cross-vendor overlap rule tested. |
| — | (M6 removed) | WEAR-13 moved into M4 by WEAR-D7. |

## 6. Work packages and wave map

Size = source diff, tests excluded; target ≤ ~400 lines per PR. A plan that exceeds it ships as two PRs (`a` backend, `b` frontend) from one plan file.

| ID | Plan | Size (diff) | Depends on |
|---|---|---|---|
| WEAR-01 | [Flag + status route + router skeleton](2026-10-13-wearables-01-flag-router.md) | S (~150) | M0 |
| WEAR-02 | [Data contract + profile migration](2026-10-13-wearables-02-contract-migration.md) | M (~350) | M0 |
| WEAR-03 | [Timestamp, offset and unit normalization](2026-10-13-wearables-03-time-units.md) | S (~250) | M0 (OM-1 formats) |
| WEAR-04 | [Apple export parser — 04a `_zipguard.py`, 04b `apple.py` (two PRs, one plan)](2026-10-13-wearables-04-apple-parser.md) | M+M (~700 with tests) | 03 |
| WEAR-05 | [Daily aggregation, dedup, multi-device overlap](2026-10-13-wearables-05-aggregate-dedup.md) | M (~300) | 03 |
| WEAR-06 | [Import route, persistence, audit, size cap](2026-10-13-wearables-06-import-route.md) | M (~400) | 01, 02, 04, 05; D4 |
| WEAR-07 | [Review queue + delete import — backend](2026-10-13-wearables-07-review-backend.md) | M (~350) | 06 |
| WEAR-07b | [Review screen — frontend](2026-10-13-wearables-07b-review-frontend.md) | M (~350) | 07, 10 |
| WEAR-08 | [Descriptive trends — 08a backend route + `select.py`, 08b panel (two PRs, one plan)](2026-10-13-wearables-08-trends.md) | M+M (~600 total) | 07, 10 |
| WEAR-09 | [Visit-prep packet section + journal selection and preview — 09a backend, 09b ExportPage (two PRs, one plan)](2026-10-13-wearables-09-packet.md) | M+S | 07, 08a (`select.py`), 15a |
| WEAR-10 | [Wearables page shell, nav gating, disclaimer copy](2026-10-13-wearables-10-ui-shell-disclaimer.md) | S (~250) | 01; D8 |
| WEAR-11 | [Garmin parser — 11a JSON (stdlib), 11b FIT via pinned `garmin-fit-sdk` for metrics absent from JSON (two PRs, one plan)](2026-10-13-wearables-11-garmin-parser.md) | M+S | 03, 05; OM-2; 11b also OW-W7 |
| WEAR-12 | [Garmin wiring + cross-vendor overlap](2026-10-13-wearables-12-garmin-wiring.md) | S (~200) | 06, 11 |
| WEAR-13 | [Wearable rows in `GET /export/json` (MVP, WEAR-D7)](2026-10-13-wearables-13-patient-export.md) | S (~150) | 02, 09a (both edit `api/export.py`) |
| WEAR-14 | [Docs: API, privacy, schema, task list](2026-10-13-wearables-14-docs.md) | S (~200) | 06, 09 |
| WEAR-15 | [Symptom journal — 15a table, migration, CRUD routes; 15b journal UI (two PRs, one plan)](2026-10-14-wearables-15-symptom-journal.md) | M+M | 01, 02 (15b also 10); WEAR-D2 |

Tickets: [`2026-10-13-wearables-tickets.md`](2026-10-13-wearables-tickets.md).

### Wave map

Host rule: at most 2 code L1s at once on the 12 GB box, full suites under `flock` (orchestration.md §2 step 4). Merges are serial; any PR that changes the collected count updates the CLAUDE.md / AGENT.md slots (SLOT-RULE).

| Wave | Runs in parallel | Serial after | Gate before start |
|---|---|---|---|
| WA | WEAR-01 ‖ WEAR-02 ‖ WEAR-03 (disjoint files; run 2 at a time) | — | M0 |
| WB | WEAR-04a → 04b ‖ WEAR-05 (pure, disjoint new files) | WEAR-06 | M1; D4 for 06 |
| WC | WEAR-07 ‖ WEAR-10 | WEAR-07b, then WEAR-08a, WEAR-08b (07b, 08, 10 all edit `App.tsx`, `components/layout/Sidebar.tsx`, `services/index.ts`: 10 owns them first, the others serialise) | M2; D8 for 10 |
| WD | WEAR-15a | then WEAR-15b, WEAR-09a, WEAR-09b, WEAR-13, WEAR-14 (09a and 13 share `api/export.py`: serial; 15a moves the profile migration head) | M3 |
| WE | WEAR-11a | WEAR-12, then WEAR-11b only if needed | M4; OM-2; OW-W7 for 11b |
| — | (WF removed: WEAR-13 is in WD) | — | — |

### Dependency graph

```
M0 ──► 01 ─────────────────┐            ┌─► 10 ─► 07b
   ├─► 02 ─────────────────┼─► 06 ─► 07 ┼─► 07b
   └─► 03 ─┬─► 04 ─────────┤            ├─► 08
           └─► 05 ─────────┘            └─► 09 ──► M4 ─► 11a ─► 12 ─► 11b (OW-W7)
                                  (08 ─► 09: shared select.py)
                         10 ─► 08     09 ─► 13, 14
   01, 02 ─► 15a ─► 09 ; 10 ─► 15b
```

## 7. Owner gates per wave

| Wave | Gate | Kind |
|---|---|---|
| all code | M0 met; owner approves the plan set | OWNER |
| WA | WEAR-02 migration number re-read on `origin/main` at Task 0 | check |
| WB / 06 | WEAR-D4 approved the §5 `security/input_validator.py` diff exactly as written; any deviation → new owner question | OWNER (signed) |
| WA / 02 | WEAR-D4 approved the `core/audit.py` vocabulary + `log_wearable_event` diff exactly as written (AO-ASKFIRST precedent); any deviation, including new journal vocabulary, → new owner question; security-reviewer on every `core/audit.py` diff | OWNER (signed) |
| WC / 10 | WEAR-D8 approved plan 10 and 09 §Copy as written; 07b, 08 and journal strings still need owner copy approval (OW-W8) | OWNER |
| WD | WEAR-D2 journal (resolved); OW-W11 journal audit vocabulary (new `core/audit.py` diff) before 15a; journal + 07b/08 copy (OW-W8); open risk: names in free text (OW-W9) | OWNER |
| WE | OM-2 notes; FIT licence read OW-W7 → row `WEAR-FIT-LIC` before 11b; `requirements.txt` pin shown in the 11b PR | OWNER |
| WD / 13 | WEAR-D7 resolved (a) | OWNER (signed) |
| any | A touch on `modules/redaction.py`, `modules/interpret_safety.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`, `core/auth.py`, `core/security.py`, encryption → STOP; none is planned | OWNER |

**Ask-first files touched by the plan set: none on the CLAUDE.md list.** `security/input_validator.py` (WEAR-06) and `core/audit.py` (WEAR-02) are treated as owner-gated (D4).

## 8. Risk register

| # | Risk | L | I | Mitigation | Owner |
|---|---|---|---|---|---|
| R1 | Apple export format differs from the inferred one (attribute names, date format, sleep values) | M | H | M0 needs OM-1; fixtures built from OM-1 structure; parser skips unknowns with counted reasons | owner (OM-1) |
| R2 | Garmin export layout unknown; FIT licence ("internal business use") | H | M | Garmin slice after M4; JSON first (11a); FIT SDK only in 11b, after the OW-W7 licence read (WEAR-D5), pinned `==` | owner (OM-2, OM-7) |
| R3 | Unreviewed wearable data reaches trends, RAG, timeline or doctor summary | L | H | Separate table (A3); static import-guard test; panel/packet read reviewed rows only | WEAR-02, 08, 09 |
| R4 | Hostile file (zip bomb, entity expansion, giant attributes) | M | H | A9 guards; hostile fixtures with a memory ceiling; size cap (D4) | WEAR-04, 06 |
| R5 | Timezone/DST misbucketing; sleep double-counted across overlapping sources | M | M | A5, A6; DST and overlap fixtures; `tz_changed` footnote | WEAR-03, 05 |
| R6 | Plaintext temp file of the whole export during upload; left behind on a crash | M | H | D6: default (b) app-owned temp path, `finally` delete, startup sweep; disclaimer copy matches whichever option is signed; no other copy written | WEAR-06, 10 |
| R7 | Personal name in device name or filename leaks into the packet | M | H | A7 closed device map; strict redaction still runs; HTTP test with "Jane's Apple Watch" | WEAR-09 |
| R8 | Wording drifts into medical advice or device claims | M | H | Template-only section; banned-phrase test; `interpret_safety` suite unchanged; copy approved (D8); classification stays open (OD-8) | WEAR-09, 10 |
| R9 | Profile migration collides with P6 / G-C1 / AUDIT-ORDER / GAM2 2b | H | L | A11 head-plus-one at merge; second lander renumbers | WEAR-02 L1 |
| R10 | Green tests that could not fail (route functions called directly; isolation asserted on names) | M | H | All route tests via `tests/support/routes.py::route_client` (`:27`); isolation tests assert on returned values; RED-first logged | every plan |
| R11 | Large export too slow or too big for the 12 GB box | M | M | Streaming parse; perf smoke on a 200 MB synthetic file is an owner/Windows task (OW-W2) | WEAR-04 |
| R12 | Names written in journal sentences reach the third-party packet: strict `name_context` (`modules/redaction.py:82-88`) needs a label and two name tokens | M | H | Journal entries enter the packet only by explicit per-entry selection after a strict-redacted preview with a fixed warning; whole packet still strict-redacted; a name-capable scrubber would edit ask-first `modules/redaction.py` → **open owner follow-up OW-W9** | WEAR-09, 15 |
| R13 | `garmin-fit-sdk` licence ("internal business use") vs open-source distribution; new supply-chain dependency | M | M | 11b gated on OW-W7 licence read; exact `==` pin; one importing module; no-network test; JSON stays primary | WEAR-11b |
| R14 | Journal migration collides with WEAR-02's, P6 013, G-C1 014, AUDIT-ORDER 015, GAM2 2b | H | L | Same head-plus-one rule (A11); WEAR-15a lands after WEAR-02; head literals updated in the same PR | WEAR-15a |

## 9. Owner decisions

All 8 answered by the owner on 2026-10-14 (owner, 2026-10-14, rows WEAR-D1..WEAR-D8, commit `c53ba44`, PR #92). Answers quoted verbatim (option label as chosen). D2, D3, D5 and D7 differ from the recommendation and change the plans.

| ID | Question (short) | Owner answer (verbatim) | Recommended was | Effect on the plans |
|---|---|---|---|---|
| D1 (WEAR-D1) | Keep the raw export ZIP? | "(b) Hash + extracted rows only (Recommended)" | (b) | No change: no raw-ZIP or vault column (WEAR-02, 06). |
| D2 (WEAR-D2) | Symptom context in the packet | "(b) Saved symptom journal" | (c) none | New **WEAR-15** (table, own profile migration, CRUD routes, audit, reset, UI). WEAR-09 replaces typed notes with per-entry selection + strict-redacted preview + confirmation. Names in free text stay an open risk (R12, OW-W9); `modules/redaction.py` is not edited. |
| D3 (WEAR-D3) | Minimum days before a metric is shown | "14 days" | 7 | `wearables_min_days = 14` (WEAR-07); boundaries 13/14 in WEAR-07, 08 tests; WEAR-09 fixtures ≥ 14 days; coverage line "data on N of M days" kept. |
| D4 (WEAR-D4) | Upload cap + the two security-adjacent diffs | "(a) Per-path cap; approve both diffs as planned (Recommended)" | (a) | `security/input_validator.py` (WEAR-06 §5) and `core/audit.py` (WEAR-02) diffs approved **exactly as written**; any deviation needs a new owner question. |
| D5 (WEAR-D5) | Garmin parser source | "(b) garmin-fit-sdk after licence read" | (a) JSON only | WEAR-11 splits: 11a JSON (unchanged); 11b FIT via `garmin-fit-sdk` pinned `==`, one importing module, no-network test, only for in-scope metrics absent from JSON; gated on the OW-W7 licence read (row `WEAR-FIT-LIC`). |
| D6 (WEAR-D6) | Where the upload sits while parsed | "(b) App-owned temp + cleanup (Recommended)" | (b) | No change (WEAR-06). |
| D7 (WEAR-D7) | Wearable rows in the patient's own export | "(a) Add to /export/json now" | (b) not in MVP | WEAR-13 moves into wave WD / milestone M4; versioned block on `GET /export/json` only (D3 full-fidelity route); no new export route. |
| D8 (WEAR-D8) | Approve patient-facing copy | "Approve drafts as written (Recommended)" | approve | Plan 10 and plan 09 §Copy approved as written (incl. Garmin G1-G4). The question named only plans 10 and 09, so 07b, 08 and the new journal strings go to OW-W8. |

Carried open from research, not re-asked here: OD-8 legal read before any public distribution (OM-7, OM-8); whether OM-4/OM-5 are still required (OW-W6). New open follow-ups: OW-W7, OW-W8, OW-W9, OW-W10, OW-W11 (§10).

## 10. Owner and model-machine queue

No package needs a local model (no LLM in the module). Items for `docs/features/TASK_LIST.md` "Owner and Model-Machine Queue" → "Needs the owner":

- **OW-W0** — OM-1: Apple export notes (research 06 §4), plus research Codex C2: how overlapping sleep records from several sources look, which `HKCategoryValueSleepAnalysis*` values appear; the exact `export.xml` prolog (DOCTYPE and internal subset, no values); whether exact-duplicate step records occur (WEAR-05 sums them today).
- **OW-W1** — M4 dogfood: import the real Apple export on the owner's machine with `WEARABLES_ENABLED=true`; record ZIP size, import time, row counts, what the review screen and packet showed (no values in the note).
- **OW-W2** — Windows perf smoke: 200 MB synthetic export import time and peak memory.
- **OW-W3** — OM-2: Garmin export notes before WE.
- **OW-W4** — Frontend vitest/Playwright for WEAR-07b, 08, 09b, 10, 15b on Windows (WSL stalls).
- **OW-W5** — Answer D1-D8. **Done 2026-10-14** (owner, 2026-10-14, rows WEAR-D1..WEAR-D8, commit `c53ba44`, PR #92).
- **OW-W6** — Confirm whether OM-4/OM-5 are still required (research 06 §1).
- **OW-W7** — FIT licence read for WEAR-11b: read the FIT Protocol License (`https://github.com/garmin/fit-python-sdk/blob/main/LICENSE.txt`) and answer "may this open-source project declare `garmin-fit-sdk` as a pip dependency and be distributed with it?"; record as row `WEAR-FIT-LIC`.
- **OW-W8** — Copy approval for strings outside WEAR-D8's scope: WEAR-07b R-table, WEAR-08 P-strings, WEAR-15b journal strings, WEAR-09 journal preview warning and section heading.
- **OW-W9** — Names in free text (journal → packet): accept the residual exposure with the preview + warning, or open an ask-first change to `modules/redaction.py` for a name-capable scrubber.
- **OW-W10** — Should journal entries join `GET /export/json`? (WEAR-D7 covered only wearable rows.) Not planned until answered.
- **OW-W11** — Approve, in `core/audit.py`: 4 symptom-journal action strings in `ALLOWED_ACTIONS` **and** the 4 matching entries in `log_wearable_event`'s event→action map, plus the HC-AUD-004 extension (vocabulary only; outside the WEAR-D4-approved diff). Recommended: approve. Blocks WEAR-15a.

## 11. What this program cannot see

- Whether real exports match any fixture (OM-1/OM-2 only).
- Whether the parser is fast enough on a multi-year export on the owner's hardware (OW-W2).
- Whether a clinician finds the section useful (D6; no study planned).
- Whether the wording satisfies FDA general-wellness or FTC HBNR (OD-8, legal).
