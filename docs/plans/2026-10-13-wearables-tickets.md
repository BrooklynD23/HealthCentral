# WEAR — Wearables Module Tickets

**Last Updated:** 2026-10-14 (owner answers WEAR-D1..D8, commit `c53ba44`, PR #92)
**Owner:** repository owner
**Status:** PROPOSED — no ticket is startable before program milestone M0.
**Program:** [2026-10-13-wearables-00-program.md](2026-10-13-wearables-00-program.md) (design decisions A1-A13, owner decisions D1-D8, wave map).

One ticket = one L1 PR (target ≤ ~400 lines of source diff, tests excluded); WEAR-04, 08, 11 and 15 are one plan each, two PRs; WEAR-09 is one plan, four PRs (09a-metrics, 09a-journal, 09b-metrics, 09b-journal). "Ask-first?" means a file on the CLAUDE.md §1 list is touched; "Owner gate?" lists the owner decisions or evidence the ticket waits for. No ticket needs a model-capable machine (the module makes no LLM call); "Windows" marks frontend suites that stall under WSL and run on the owner's Windows machine (OW-W4).

| ID | Title | Plan | Wave | Depends on | Size | Ask-first? | Owner gate? | Model-machine? |
|---|---|---|---|---|---|---|---|---|
| WEAR-01 | Flag `wearables_enabled`, status route, gated router | [01](2026-10-13-wearables-01-flag-router.md) | WA | M0 | S | No | M0 | No |
| WEAR-02 | Data contract, models, profile migration, reset + audit vocabulary | [02](2026-10-13-wearables-02-contract-migration.md) | WA | M0 | M | **Owner-gated** `core/audit.py` (AO-ASKFIRST precedent) | M0; WEAR-D1, WEAR-D4 signed (diff exactly as written) | No |
| WEAR-03 | Timestamp, offset, local-date and unit normalization | [03](2026-10-13-wearables-03-time-units.md) | WA | M0 (OM-1 formats) | S | No | M0 (OW-W0) | No |
| WEAR-04a | Shared ZIP guards `_zipguard.py` | [04](2026-10-13-wearables-04-apple-parser.md) | WB | 03 | M | No | — | No |
| WEAR-04b | Apple `export.xml` streaming parser | [04](2026-10-13-wearables-04-apple-parser.md) | WB | 04a | M | No | OW-W0 prolog | No (OW-W2 perf smoke on Windows) |
| WEAR-05 | Daily aggregation, source selection, dedup | [05](2026-10-13-wearables-05-aggregate-dedup.md) | WB | 03 | M | No | — | No |
| WEAR-06 | `POST /wearables/imports`: temp file, hash, persist, audit, size cap | [06](2026-10-13-wearables-06-import-route.md) | WB | 01, 02, 04, 05 | M | **Owner-gated** `security/input_validator.py` (security middleware) | WEAR-D4, WEAR-D6 signed (diff exactly as written) | No |
| WEAR-07 | Review queue + delete import (backend) | [07](2026-10-13-wearables-07-review-backend.md) | WC | 06 | M | No | — | No |
| WEAR-10 | Wearables page shell, nav gating, disclaimer copy | [10](2026-10-13-wearables-10-ui-shell-disclaimer.md) | WC | 01 | S | No | WEAR-D8 signed | Windows |
| WEAR-07b | Review screen (frontend) | [07b](2026-10-13-wearables-07b-review-frontend.md) | WC | 07, 10 | M | No | OW-W8 copy | Windows |
| WEAR-08a | Trends route + shared `select.py` (backend) | [08](2026-10-13-wearables-08-trends.md) | WC | 07 | M | No | WEAR-D3 = 14 days | No |
| WEAR-08b | "Wearable (patient-recorded)" panel (frontend) | [08](2026-10-13-wearables-08-trends.md) | WC | 08a, 10 | M | No | OW-W8 copy | Windows |
| WEAR-09a-metrics | Visit-prep wearable section (backend; no journal field, route or test) | [09](2026-10-13-wearables-09-packet.md) | WD | 07, 08a (`select.py`), WEAR-02 vocabulary | M | No (calls strict redaction; `modules/redaction.py` not edited) | WEAR-D3, WEAR-D8 | No |
| WEAR-09a-journal | Journal selection + strict-redacted preview snapshot (backend; bounded in-memory store) | [09](2026-10-13-wearables-09-packet.md) | WD | 09a-metrics, 15a | M | **Owner-gated** reset/delete-path purge calls in `api/profiles.py` (RL-EXPORTS-DELETE-PATH precedent); `modules/redaction.py` not edited | **OW-W9 = blocker (Task 0 STOP)**; OW-W12; journal strings OW-W8 | No |
| WEAR-09b-metrics | ExportPage wearable option | [09](2026-10-13-wearables-09-packet.md) | WD | 09a-metrics, 10 | S | No | WEAR-D8 | Windows |
| WEAR-09b-journal | ExportPage per-entry journal selection and preview | [09](2026-10-13-wearables-09-packet.md) | WD | 09a-journal, 09b-metrics, 15b | S | No | OW-W9 blocker; OW-W8 copy | Windows |
| WEAR-14 | Docs: API routes, privacy, `wearable-summary` v1 schema, task list | [14](2026-10-13-wearables-14-docs.md) | WD | 06, 09a-metrics, 13, 15a | S | No | — | No |
| WEAR-15a | Symptom journal: table, own profile migration, CRUD routes, audit, reset | [15](2026-10-14-wearables-15-symptom-journal.md) | WD | 01, 02 | M | **Owner-gated** `core/audit.py` (4 journal actions, OW-W11) | WEAR-D2 signed; OW-W11 | No |
| WEAR-15b | Symptom journal UI | [15](2026-10-14-wearables-15-symptom-journal.md) | WD | 15a, 10 | M | No | OW-W8 copy | Windows |
| WEAR-11a | Garmin JSON parser (stdlib) | [11](2026-10-13-wearables-11-garmin-parser.md) | WE | 03, 05, M4 | M | No | OM-2 (OW-W3) | No |
| WEAR-11b | Garmin FIT path via pinned `garmin-fit-sdk` (only for metrics absent from JSON) | [11](2026-10-13-wearables-11-garmin-parser.md) | WE | 11a, 12 | S | No (new dependency in `requirements.txt`, shown to owner) | WEAR-D5; FIT licence read OW-W7 → `WEAR-FIT-LIC` | No |
| WEAR-12 | Garmin wiring + cross-vendor overlap | [12](2026-10-13-wearables-12-garmin-wiring.md) | WE | 06, 11a | S | No | — | No |
| WEAR-13 | Wearable rows in `GET /export/json` (MVP) + frontend sends `include_wearables=true` when enabled | [13](2026-10-13-wearables-13-patient-export.md) | WD | 02, 09a-metrics | S | No | WEAR-D7 signed | Windows (export.ts vitest) |

## Owner items (no code)

| ID | Item | Blocks |
|---|---|---|
| OW-W0 | OM-1 Apple export notes, incl. sleep overlap and sleep values | M0, WEAR-03/04 |
| OW-W1 | M4 dogfood with the real Apple export | M4 |
| OW-W2 | Windows perf smoke, 200 MB synthetic export | M2 sign-off |
| OW-W3 | OM-2 Garmin export notes | WEAR-11 |
| OW-W4 | Frontend vitest/Playwright on Windows for 07b, 08, 09b-metrics, 09b-journal, 10, 13 (export.ts), 15b | M3, M4 |
| OW-W5 | Answer D1-D8 — **done 2026-10-14** (WEAR-D1..D8) | — |
| OW-W6 | Confirm whether OM-4/OM-5 are still required | wording only |
| OW-W7 | FIT licence read → row `WEAR-FIT-LIC` | WEAR-11b |
| OW-W8 | Copy approval for 07b, 08, 09 journal strings, 15b | 07b, 08b, 09a-journal, 09b-journal, 15b |
| OW-W10 | Journal entries in `/export/json`? | follow-up plan |
| OW-W11 | Approve 4 journal action strings in `core/audit.py` + HC-AUD-004 | WEAR-15a |
| OW-W9 | Names in free text (journal → packet): accept residual or open ask-first redaction change (Opus D1D8 A1) | **blocks 09a-journal and 09b-journal** (Task 0 STOP); 09a-metrics does not wait |
| OW-W12 | Approve purging in-memory journal preview snapshots in the profile reset/delete paths (`api/profiles.py`) | WEAR-09a-journal |
| OW-W13 | Confirm the profile-migration merge order: P6 `013` → G-C1 `014` → AUDIT-ORDER `015` → GAM2-2b → WEAR-02 → WEAR-15 | WEAR-02, WEAR-15a (renumbering) |
