# WEAR — Wearables Module Tickets

**Last Updated:** 2026-10-13
**Owner:** repository owner
**Status:** PROPOSED — no ticket is startable before program milestone M0.
**Program:** [2026-10-13-wearables-00-program.md](2026-10-13-wearables-00-program.md) (design decisions A1-A13, owner decisions D1-D8, wave map).

One ticket = one L1 PR (target ≤ ~400 lines of source diff, tests excluded); WEAR-04, WEAR-08 and WEAR-09 are one plan each, two PRs. "Ask-first?" means a file on the CLAUDE.md §1 list is touched; "Owner gate?" lists the owner decisions or evidence the ticket waits for. No ticket needs a model-capable machine (the module makes no LLM call); "Windows" marks frontend suites that stall under WSL and run on the owner's Windows machine (OW-W4).

| ID | Title | Plan | Wave | Depends on | Size | Ask-first? | Owner gate? | Model-machine? |
|---|---|---|---|---|---|---|---|---|
| WEAR-01 | Flag `wearables_enabled`, status route, gated router | [01](2026-10-13-wearables-01-flag-router.md) | WA | M0 | S | No | M0 | No |
| WEAR-02 | Data contract, models, profile migration, reset + audit vocabulary | [02](2026-10-13-wearables-02-contract-migration.md) | WA | M0 | M | **Owner-gated** `core/audit.py` (AO-ASKFIRST precedent) | M0; D1; D4 | No |
| WEAR-03 | Timestamp, offset, local-date and unit normalization | [03](2026-10-13-wearables-03-time-units.md) | WA | M0 (OM-1 formats) | S | No | M0 (OW-W0) | No |
| WEAR-04a | Shared ZIP guards `_zipguard.py` | [04](2026-10-13-wearables-04-apple-parser.md) | WB | 03 | M | No | — | No |
| WEAR-04b | Apple `export.xml` streaming parser | [04](2026-10-13-wearables-04-apple-parser.md) | WB | 04a | M | No | OW-W0 prolog | No (OW-W2 perf smoke on Windows) |
| WEAR-05 | Daily aggregation, source selection, dedup | [05](2026-10-13-wearables-05-aggregate-dedup.md) | WB | 03 | M | No | — | No |
| WEAR-06 | `POST /wearables/imports`: temp file, hash, persist, audit, size cap | [06](2026-10-13-wearables-06-import-route.md) | WB | 01, 02, 04, 05 | M | **Owner-gated** `security/input_validator.py` (security middleware) | D4, D6 | No |
| WEAR-07 | Review queue + delete import (backend) | [07](2026-10-13-wearables-07-review-backend.md) | WC | 06 | M | No | — | No |
| WEAR-10 | Wearables page shell, nav gating, disclaimer copy | [10](2026-10-13-wearables-10-ui-shell-disclaimer.md) | WC | 01 | S | No | D8 | Windows |
| WEAR-07b | Review screen (frontend) | [07b](2026-10-13-wearables-07b-review-frontend.md) | WC | 07, 10 | M | No | — | Windows |
| WEAR-08a | Trends route + shared `select.py` (backend) | [08](2026-10-13-wearables-08-trends.md) | WC | 07 | M | No | D3 | No |
| WEAR-08b | "Wearable (patient-recorded)" panel (frontend) | [08](2026-10-13-wearables-08-trends.md) | WC | 08a, 10 | M | No | D8 | Windows |
| WEAR-09a | Visit-prep wearable section + symptom notes (backend) | [09](2026-10-13-wearables-09-packet.md) | WD | 07, 08a (`select.py`) | M | No (calls strict redaction; `modules/redaction.py` not edited) | D3, D8 (D2 only if notes are built) | No |
| WEAR-09b | ExportPage wearable option + notes inputs | [09](2026-10-13-wearables-09-packet.md) | WD | 09a, 10 | S | No | D8 | Windows |
| WEAR-14 | Docs: API routes, privacy, `wearable-summary` v1 schema, task list | [14](2026-10-13-wearables-14-docs.md) | WD | 06, 09 | S | No | — | No |
| WEAR-11 | Garmin export parser (JSON, no FIT SDK) | [11](2026-10-13-wearables-11-garmin-parser.md) | WE | 03, 05, M4 | M | No | OM-2 (OW-W3); D5 | No |
| WEAR-12 | Garmin wiring + cross-vendor overlap | [12](2026-10-13-wearables-12-garmin-wiring.md) | WE | 06, 11 | S | No | — | No |
| WEAR-13 | Wearable rows in `GET /export/json` | [13](2026-10-13-wearables-13-patient-export.md) | WF | 02, 09 | S | No | D7 = include | No |

## Owner items (no code)

| ID | Item | Blocks |
|---|---|---|
| OW-W0 | OM-1 Apple export notes, incl. sleep overlap and sleep values | M0, WEAR-03/04 |
| OW-W1 | M4 dogfood with the real Apple export | M4 |
| OW-W2 | Windows perf smoke, 200 MB synthetic export | M2 sign-off |
| OW-W3 | OM-2 Garmin export notes | WEAR-11 |
| OW-W4 | Frontend vitest/Playwright on Windows for 07b, 08, 09, 10 | M3, M4 |
| OW-W5 | Answer D1-D8 | per ticket |
| OW-W6 | Confirm whether OM-4/OM-5 are still required | wording only |
