# WEAR-14 — Docs: API, Privacy, Schema, Task List — Implementation Plan

**Last Updated:** 2026-10-13
**Owner:** repository owner
**Status:** PROPOSED — not executed (code waits for program M0 and WEAR-06 and WEAR-09 merged; this is docs only).
**Base measured:** `origin/main` @ `8234990`; program file @ `a985390`.
**Refresh trigger:** any WEAR-01/06/07/08/09 route, field or copy change after this plan; an answer to D1, D6 or D7; a new profile migration; any edit to `docs/api/endpoints.md`, `docs/compliance/data-privacy.md` or `docs/features/TASK_LIST.md`.
**Program:** [00-program](2026-10-13-wearables-00-program.md) (§10 owner queue, A2, A12, D1, D6, D7).
**Depends on:** WEAR-06 (import route, temp file, audit), WEAR-09 (packet fields). WEAR-07/08 routes are documented only if mounted by then; never list a route as "coming". Document what `grep` finds mounted (Task 0).
**Owner decisions:** D1 (b) raw ZIP not kept, D6 (b) app-owned temp file, D7 (b) not in patient export. The docs state whatever is signed; the defaults are drafted here.
**Size target:** S, ~200 lines of diff, one L1 PR, no code and no tests added (collected count unchanged).

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (or executing-plans). Steps use `- [ ]`. Docs only: no product code, no `CLAUDE.md` or `AGENT.md` edit (no count slot moves because no test is added).

## 1. Scope

**This plan does:**
- Add a "Wearables" section to `docs/api/endpoints.md` and update the visit-prep row.
- Add `docs/api/wearable-summary.md` (the `wearable-summary` v1 schema) and link it from `docs/api/README.md`.
- Add a "Wearable data" section to `docs/compliance/data-privacy.md`.
- Add owner rows OW-W0..OW-W6 to `docs/features/TASK_LIST.md` and fix the stale wearables rows there.
- Regenerate `docs/INDEX.md`.

**This plan does NOT license:**
- Any statement that is not true of merged code. Every route, field, path and number is copied from the merged tree at Task 0, not from a plan.
- Any medical-device classification claim (OD-8 open). Any compliance claim ("HIPAA compliant", "FDA cleared").
- Edits to `CLAUDE.md`, `AGENT.md`, `docs/compliance/` files other than `data-privacy.md`, or any `src/` file.

## 2. Evidence

| Fact | Path:line @8234990 |
|---|---|
| endpoints.md header fields; all routes under `/api/v1` | `docs/api/endpoints.md:1-10` |
| Export table; visit-prep row to update | `docs/api/endpoints.md:142-154` (row `:149`) |
| Last section before the new one: "Health and Monitoring" | `docs/api/endpoints.md:245` |
| README index table and router-group table; says "Eighteen routers" | `docs/api/README.md:30-38`, `:41` |
| Same "18 routers" claim elsewhere | `docs/architecture/backend.md:60`, `docs/architecture/README.md:47`, `docs/capstone-report/architecture-overview.md:36` |
| data-privacy headings: Data Classification `:3`, Tier 1 table `:5-16`, Data Retention `:56`, Data Portability `:66`, Data Deletion `:120`, Document Deletion `:194`, Unverified Extracted Values `:218`, Third-Party Data Sharing `:228` | `docs/compliance/data-privacy.md` |
| data-privacy has no `Last Updated` or `Owner` header block | `docs/compliance/data-privacy.md:1-3` |
| TASK_LIST: `Last Updated` `:4`; queue `:76`; "Needs the owner" `:87-93`; "Wearables evidence gate" `:95-103`; stale text "not yet merged" `:97`; row `:100` still lists Samsung | `docs/features/TASK_LIST.md` |
| Samsung (OM-3) dropped: out of scope | `docs/research/2026-10-12/06-decisions-go-nogo.md:29,55,66` |
| The research package is merged (#87 at `7630aaa`) | program header `00-program:6` |
| `wearable-summary` v1 contract, to be published in `docs/api/` | `docs/research/2026-10-12/03-architecture-contracts.md:110-125` (§5.2) |
| docs lint rules: Last Updated, Owner/Refresh Trigger on canonical docs, relative links resolve (DOC-007), every doc reachable (DOC-011) | `scripts/docs_lint.py:1-30`, `:232-244`; canonical list `:38-42` |
| CI runs `docs_lint.py` and `generate_docs_index.py --check` | `.github/workflows/ci.yml:22,25` |
| Index generator is run manually, with `--link-graph` | `scripts/generate_docs_index.py:1-12` |

## 3. Files to touch

| Path | New/edit | Why | ~Lines |
|---|---|---|---|
| `docs/api/endpoints.md` | edit | "Wearables" table; visit-prep row; `Last Updated` | 30 |
| `docs/api/wearable-summary.md` | new | Schema doc, one JSON example, field table, rejection rules | 70 |
| `docs/api/README.md` | edit | Index row, router-group row, router count | 6 |
| `docs/compliance/data-privacy.md` | edit | Tier 1 rows, new "Wearable data" section | 45 |
| `docs/features/TASK_LIST.md` | edit | OW-W0..W6 rows; fix `:97`, `:100`; `Last Updated` | 20 |
| `docs/architecture/backend.md`, `docs/architecture/README.md`, `docs/capstone-report/architecture-overview.md` | edit (count only) | Keep the router count equal to the measured one | 3 |
| `docs/INDEX.md` | regenerated | Output of `generate_docs_index.py` | generated |

## 4. Ask-first files touched

None. `docs/` only.

## 5. Content contract (what each doc must say)

**endpoints.md "Wearables"** (one table, columns as the file's others; routes read from `src/backend/api/wearables.py` at Task 0, expected set):
`GET /wearables/status` (auth, never 404: `{enabled}`), `POST /wearables/imports` (raw body `Content-Type: application/zip`, size cap `wearables_max_import_mb`, 404 when off, 409 duplicate hash, 413 oversize, 400 hostile, 422 invalid summary), `GET /wearables/imports`, `GET /wearables/imports/{id}/summary`, `PUT /wearables/imports/{id}/review`, `DELETE /wearables/imports/{id}`, `GET /wearables/metrics`. Intro line: every route except `status` returns 404 unless `WEARABLES_ENABLED=true`. Visit-prep row gains: "optional `include_wearables` and up to 5 `symptom_notes` (not stored); reviewed and included metrics only". Raw bytes are the body, so the table says so (A4 amendment).

**wearable-summary.md:** schema id `hc.wearable-summary`, version `1.0`; field table (source_vendor, metric enum of 3, local_date ISO, value, unit fixed per metric, utc_offset_minutes, tz_changed, n_records, device_class closed enum, source_name capped and never printed in the packet, duplicate_sources); one daily value per (metric, date) with the A5 semantics in plain words; counts-only `skipped`; unknown major version rejected; "internal format today, no plugin repo (WEAR-OD2)". One JSON example with 3 rows that must validate against WEAR-02's `validate_summary` (check HC-WRB-1405).

**data-privacy.md "Wearable data"** (drafted from D1/D6/D7 defaults; edit to match what is signed and merged):
- Tier 1 rows: wearable imports, daily metrics, metric reviews, in the profile vault DB, AES-256 (SQLCipher).
- Not stored: the uploaded ZIP (D1 b), raw samples, heart-rate series, workout routes, ECG.
- While parsing: the upload is streamed to `app_data_path/tmp/` as a plaintext file, deleted in `finally`, with a startup sweep for leftovers after a crash (D6 b). If the owner signs D6 (a), say instead that it sits in the OS temp folder.
- Deletion: deleting an import deletes its metric rows and review rows explicitly, then the import (SQLite foreign keys are not enforced, A2). Profile deletion removes the whole vault. The synthetic reset clears the three tables.
- Exports: only reviewed and included metrics, as a closed device class, can enter the visit-prep packet; they pass the strict redaction pass; symptom notes are not stored. Not in `GET /export/csv` or `/json` (D7 b).
- Audit: counts plus the opaque `import_id` and the `vendor` enum (as `document_id` is logged for documents today); never filenames, device names, values or dates.
- Not used by: trends, RAG, timeline, doctor summary, any model. No network call.
- Wording: "patient-recorded, not clinically verified". No classification claim.

**TASK_LIST.md:** add OW-W0..OW-W6 under "Needs the owner" exactly as program §10 words them. Fix `:97` (package is merged, #87). Replace the `:100` row "OM-2 / OM-3 — Garmin … and Samsung": keep OM-2 (Garmin, now tracked as OW-W3) and drop Samsung with "dropped: out of scope" per research 06 `:55`. Point the OM-1 row (`:99`) at OW-W0 so the two do not drift. Bump `Last Updated` (`:4`). Keep the existing `Owner` and `Refresh Trigger` fields (docs_lint rule 5).

**Router count:** measure with `grep -c include_router src/backend/api/__init__.py` after WEAR-01 and set all four docs to the same number with the counting rule written once in `docs/api/README.md` (WEAR-01 adds a status router and a gated router on one prefix, so "routers" and "prefixes" differ).

## 6. TDD checks

These are command checks, not pytest. Collected count unchanged. "RED" means the command fails before the edit.

| ID | Command | Assertion | RED reason |
|---|---|---|---|
| HC-WRB-1401 | `python3 scripts/docs_lint.py` | exit 0 | Add the README link first; the target file does not exist yet, so DOC-007 fails |
| HC-WRB-1402 | `python3 scripts/docs_lint.py --link-graph` | `wearable-summary.md` appears reachable from `docs/api/README.md` | File created, link absent: DOC-011 fails |
| HC-WRB-1403 | `python3 scripts/generate_docs_index.py` then `--check` | `--check` exits 0 | New docs added, index stale: `--check` fails |
| HC-WRB-1404 | route-inventory one-liner (Task 3) | every path in the Wearables table matches an `@router`/`@status_router` decorator in `api/wearables.py` and the reverse | table absent |
| HC-WRB-1405 | `python3 -I` script extracts the JSON block from `wearable-summary.md` and calls `modules.wearables.contract.validate_summary` | returns `[]` | example absent |
| HC-WRB-1406 | `grep -n "wearables-" docs/compliance/data-privacy.md` equals the temp-name prefix constant in `api/wearables.py` | same string | privacy section absent |
| HC-WRB-1407 | `grep -c "OW-W[0-6]" docs/features/TASK_LIST.md` | 7 distinct ids; no active row mentions Samsung | rows absent |
| HC-WRB-1408 | `grep -n "Eighteen\|18 routers" docs/api/README.md docs/architecture/*.md docs/capstone-report/architecture-overview.md` | the four files carry the one measured number | WEAR-01 changed the count |

## 7. Tasks

### Task 0 — gates
- [ ] `git merge-base --is-ancestor <WEAR-06 sha> origin/main` and the same for WEAR-09; STOP if either fails.
- [ ] Confirm D1, D6, D7 answers (or that the defaults stand). Note them in the PR body.
- [ ] Read the merged tree, not the plans: `grep -n "@router\.\|@status_router\." src/backend/api/wearables.py`, `grep -n "wearables-" src/backend/api/wearables.py`, `grep -n "wearables_max_import_mb" src/backend/core/config.py`, `sed -n` the `VisitPrepRequest` block in `api/export.py`. Paste the route list into the PR.
- [ ] Baseline: `python3 scripts/docs_lint.py; echo $?` and `python3 scripts/generate_docs_index.py --check; echo $?`. Both must be clean before you start; if not, STOP (not yours).

### Task 1 — RED
- [ ] Add the README index row linking `wearable-summary.md`. Run 1401: DOC-007 fails (missing target). Paste it.
- [ ] Create the empty file with only a title. Run `--link-graph` and `generate_docs_index.py --check`; paste the 1403 failure.

### Task 2 — GREEN, schema and API docs
- [ ] Write `wearable-summary.md` (header fields `Last Updated`, `Owner`, `Refresh Trigger`, `Status` like its neighbours). Run 1405.
- [ ] Write the endpoints.md Wearables table in the file's column style; update `:149`. Run 1404.
- [ ] Router groups table row and count in the four files (1408). Update `Last Updated` fields.

### Task 3 — GREEN, privacy and task list
- [ ] Write the data-privacy section and Tier 1 rows from §5; run 1406.
- [ ] Edit TASK_LIST rows; run 1407.
- [ ] 1404 one-liner (adapt): collect `grep -o '"/[a-z/{}_]*"' src/backend/api/wearables.py` vs backticked `/wearables/...` paths in endpoints.md; `diff` the two sorted lists, expect empty output.

### Task 4 — verify
- [ ] `python3 scripts/generate_docs_index.py`, then `--check` (exit 0), then `python3 scripts/docs_lint.py` and `python3 scripts/docs_lint.py --link-graph`. Paste each last line and exit code.
- [ ] `git diff --stat` shows only the files in §3; no `src/` path.
- [ ] Re-read every sentence of the privacy section against §5 sources; no claim without a merged-code line behind it.
- [ ] Open PR; `docs/` only, so no pytest run is claimed.

## 8. Mutation / break checks (temporary, never committed; `git diff` guard after reverting)

1. Delete the README link to `wearable-summary.md`: 1402 fails.
2. Rename one path in the endpoints table (`/wearables/imports` to `/wearables/import`): 1404 fails.
3. Add a field `heart_rate_zone` to the JSON example: 1405 fails.
4. Skip regeneration after the last edit: 1403 fails.

## 9. Acceptance criteria (seen output)

- 1401 to 1408 each pasted with exit code, after the RED outputs from Task 1.
- Route list in the PR equals the endpoints table (1404 empty diff).
- `git diff --stat` limited to §3 paths.
- Wording check: `grep -inE "caused|due to|indicates|diagnos|normal|abnormal|average|risk|cleared|compliant" docs/api/wearable-summary.md` and on the new privacy section returns nothing, or each hit is a quoted rule (the banned-phrase list itself).

## 10. Rollback

Revert the PR. Docs only; no data, no migration. If CI `--check` goes red after a merge from main, regenerate `docs/INDEX.md` and push.

## 11. What these checks cannot see

- **#6 documented commands nobody ran, #8 stale guidance.** 1404-1406 compare names and strings; they cannot tell whether a sentence such as "deleted in `finally`" is still true after a later refactor. The Refresh trigger covers that only if someone reads it.
- **#3 figures asserted instead of measured.** The router count (1408) is measured at Task 0 but drifts on the next router. The counting rule is written down once to limit that.
- A privacy statement can be accurate for the code and still wrong for the owner's decision; D1, D6, D7 are confirmed in Task 0, not by a test.
- No compliance review: the section makes no HIPAA, FDA or FTC claim (OD-8).
- No test was run while drafting this plan.

## 12. Owner / model-machine items

- **OW-W0 to OW-W6** — this plan adds the seven rows to the TASK_LIST "Needs the owner" list (program §10). It does not complete any of them.
- **OW-W5** — D1, D6, D7 answers feed Task 0.
