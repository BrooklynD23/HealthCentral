# WEAR-11 — Garmin Export Parser (JSON only) — Implementation Plan

**Last Updated:** 2026-10-13
**Owner:** repository owner
**Status:** PROPOSED — not executed. Code waits for program M0, M4 (Apple slice done), **OM-2 notes committed** and **D5 answered**.
**Base measured:** `origin/main` @ `8234990`. Product-code lines below were re-read on the planning tree (`a985390`, docs-only ahead of the base) on 2026-10-13.
**Refresh trigger:** OM-2 notes land (fill the table in §3); WEAR-03/04/05 merge (record shape may differ from §6); D5 answer changes; any edit to `modules/wearables/`.
**Program:** [`2026-10-13-wearables-00-program.md`](2026-10-13-wearables-00-program.md) (A8, A9, R2, wave WE).
**Depends on:** WEAR-03 (`timeparse.py`), WEAR-04 (`apple.py`: guard helpers and normalized-record shape), WEAR-05 (`aggregate.py`). All three are PLANNED, not existing. Gate: OM-2.
**Owner decisions it depends on:** **D5** default (a): JSON wellness files only, stdlib, **no FIT**, no new dependency. FIT licence ("internal business use") is OM-7 / OD-8 and stays open; this plan does not touch it.
**Size target:** M, ~400 diff lines (parser ~180, tests ~220).

> For agentic workers: use superpowers:test-driven-development and superpowers:subagent-driven-development; domain skill `asclexis-backend`. RED first, log the failure.

## 1. Scope

Does:
- Add `src/backend/modules/wearables/garmin.py`, a pure stdlib parser: ZIP in (binary file object), normalized records out, same shape as `apple.py`.
- Apply the A9 guards to ZIP and JSON (member count, bytes-actually-read caps, name checks, JSON size and depth, NaN rejection).
- Emit only resting heart rate, steps, sleep intervals. `device_class="garmin_device"`, `source_vendor="garmin"`.
- Count FIT members as skipped `fit_not_supported`; count every out-of-scope file as `metric_not_in_scope`. Neither is opened.

Does NOT:
- No FIT decoding, no `garmin-fit-sdk`, no new dependency (D5 b/c are separate plans).
- No stress, HRV, SpO2, Body Battery, respiration, heart-rate samples (program non-goals; F5).
- No route, DB, aggregation or vendor detection (WEAR-12 / WEAR-05).
- No guessing a layout. If OM-2 does not show all three metrics as JSON, STOP and ask (D5 "revisit only if OM-2 shows the 3 metrics are FIT-only").
- No claim that any real Garmin export matches the fixtures (R2, program §11).

## 2. Evidence

| Fact | path:line |
|---|---|
| Program: Garmin slice after M4, JSON-only recommended, FIT not added | `docs/plans/2026-10-13-wearables-00-program.md:132` (R2), `:153` (D5) |
| Hostile-file guards, bytes read not headers | `docs/plans/2026-10-13-wearables-00-program.md:48` (A9) |
| Parsers pure, stdlib only, emit `wearable-summary` v1 | `docs/plans/2026-10-13-wearables-00-program.md:47` (A8) |
| Garmin export: layout, turnaround, JSON-vs-FIT, timezone fields are NOT verified | `docs/research/2026-10-12/01-vendor-matrix.md:78-81` |
| Garmin rows are labelled S (single secondary source) or U; resting HR "NE (S)", steps "NE (S)", sleep "NE JSON (S)" | `docs/research/2026-10-12/01-vendor-matrix.md:24-33` |
| Garmin Connect export row: label S, layout "if confirmed" | `docs/research/2026-10-12/01-vendor-matrix.md:60` |
| FIT SDK licence: internal business use, V, legal read first | `docs/research/2026-10-12/01-vendor-matrix.md:61` |
| OM-2 definition: record turnaround, folder layout, which files hold the metrics, timezone fields; "Do not commit the file" | `docs/research/2026-10-12/06-decisions-go-nogo.md:54` |
| OM-7 legal read incl. FIT licence | `docs/research/2026-10-12/06-decisions-go-nogo.md:59` |
| "Garmin wellness JSON holds stress, HRV, SpO2" is an untested assumption | `docs/research/2026-10-12/00-README.md:77` |
| Owner queue row for OM-2 (still pairs it with dropped Samsung OM-3: stale, see §13) | `docs/features/TASK_LIST.md:100` |
| `modules/wearables/` does not exist on this tree (everything it holds is planned) | `ls src/backend/modules/wearables` → no such directory |
| `_cap` and `_MAX_FIELD_LEN = 2000` exist as a pattern; `_parse_date` drops time and offset, do not reuse | `src/backend/modules/import_structured.py:41`, `:55`, `:77` |
| Aware→naive helper, only for storing an aware value as naive UTC | `src/backend/core/time.py:24` |
| `route_client` signature (used by WEAR-12, not here) | `src/backend/tests/support/routes.py:27` |

## 3. OM-2 fill-in (every value below is UNVERIFIED until the owner fills the last column)

Rule: no row may be treated as fact. A blank "confirmed value" blocks the code step that uses it.

| Item | Research guess + label | Confirmed value (OM-2) |
|---|---|---|
| Export delivery (ZIP? one or several?) | ZIP via account "Export Your Data", emailed link — S | |
| Top-level folder name(s) holding wellness data | none stated in repo research — U | |
| Vendor marker for WEAR-12 (a member name or folder unique to Garmin) | none — U | |
| Resting HR: file name pattern, JSON path to date, JSON path to value | "NE (S)", format unknown — U | |
| Steps: file name pattern, grain (daily total or intervals), JSON paths | "NE (S)", format unknown — U | |
| Sleep: file name pattern, start/end fields, asleep-vs-awake/stage field, overlaps | "NE JSON (S)", fields unknown — U | |
| Timestamp format and timezone/offset field (UTC + separate offset? local string?) | research 01:81 says tz fields unverified — U | |
| Units (sleep seconds vs minutes; steps count) | none — U | |
| Are all 3 metrics JSON (not FIT-only)? | unknown — U | |
| Typical file sizes, member count, total size | none — U | |
| Is the same day split over several files? | none — U | |

OM-2 notes must contain structure only (names, field names, one redacted sample line shape), never values.

## 4. Files to touch

| Path | New/edit | Why | Lines |
|---|---|---|---|
| `src/backend/modules/wearables/garmin.py` | new | pure parser | ~180 |
| `src/backend/tests/test_wearables_garmin.py` | new | tests below, synthetic export built from a layout dict | ~220 |
| `src/backend/modules/wearables/__init__.py` | edit only if WEAR-03/04 did not already create it | package | 0-1 |

If WEAR-04 put the ZIP guard helpers in `apple.py`, import them from a shared `_zipguard.py` created by the WEAR-04 L1; if not, Task 0 decides between a tiny `_zipguard.py` move (preferred, one more file) and a copy. Do not edit `apple.py` behaviour.

## 5. Ask-first files touched

None. (`security/input_validator.py` is WEAR-06's D4 gate, not here.)

## 6. Data contract

Output (planned shape, **Task 0 re-reads `apple.py` and matches it exactly**): `ParseResult(records: list[dict], records_read: int, skipped: dict[str,int])`. Each record dict (INFERRED from the WEAR-04 plan): `metric` in `{resting_heart_rate, sleep_asleep_minutes, step_count}`-source kinds, `start` / `end` aware `datetime` (own offset kept), `value`, `unit`, `source_vendor="garmin"`, `device_class="garmin_device"`, `source_name` capped (`_MAX_FIELD_LEN` pattern, 255 for the column).

Skip reasons added by this plan (closed set, counts only): `fit_not_supported`, `metric_not_in_scope`, `json_invalid`, `json_too_deep`, `value_invalid`, `timestamp_invalid`, `unit_unsupported` (WEAR-03 name). Refusals (raise `ParseError`, route maps to 400): too many members, member or total too large, unsafe member name, ZIP unreadable.

Invariants: values finite and >= 0; no mean; no free text from the file outside `source_name`; parser never sums steps or merges sleep (WEAR-05 does).

## 7. TDD test list (`src/backend/tests/test_wearables_garmin.py`)

Fixtures are built in a helper from a `LAYOUT` dict whose values come from §3. Until §3 is filled the helper raises, so tests cannot pass on guessed names.

| ID | Assertion | RED reason |
|---|---|---|
| HC-WRB-1101 | Synthetic export with the 3 metrics → records for each, all `garmin_device`/`garmin` | module missing |
| HC-WRB-1102 | Steps records returned per source row, not summed | parser absent |
| HC-WRB-1103 | Sleep interval keeps its own offset; two intervals with different offsets keep different `tzinfo` utcoffsets | absent |
| HC-WRB-1104 | `.fit` members → `skipped["fit_not_supported"]==n`; an open-spy on `ZipFile.open` shows they were never opened | absent |
| HC-WRB-1105 | Out-of-scope JSON (stress, HRV, SpO2 names per §3 or a decoy) → `metric_not_in_scope`, never opened (spy) | absent |
| HC-WRB-1106 | Member named `../x.json` or absolute → `ParseError` | absent |
| HC-WRB-1107 | Member-count cap exceeded → `ParseError` before any open | absent |
| HC-WRB-1108 | Bomb: header `file_size` lies small, stream inflates past per-member cap → refused; counted on bytes read (A9) | absent |
| HC-WRB-1109 | tracemalloc peak < 64 MB on the bomb | absent |
| HC-WRB-1110 | JSON nested 10 000 deep → `json_too_deep` skip, no `RecursionError` escapes | absent |
| HC-WRB-1111 | `NaN`, `Infinity`, negative values → `value_invalid` (Python `json.loads` accepts `NaN` unless `parse_constant` rejects it) | absent |
| HC-WRB-1112 | Malformed JSON member → `json_invalid`; other members still parsed | absent |
| HC-WRB-1113 | `source_name` of 5 000 chars is capped | absent |
| HC-WRB-1114 | AST check: `garmin.py` imports only stdlib (+ `modules.wearables.*`); no `models`, `core.database`, `llama_cpp` | absent |
| HC-WRB-1115 | Unknown timestamp format → `timestamp_invalid` skip, row not guessed | absent |
| HC-WRB-1116 | TZ env patched to `Pacific/Kiritimati` and `America/Los_Angeles`: identical records (host tz never used) | absent |

Covers research HC-WRB-001 (partly), 005, 006 for the Garmin path. Tests 1108/1109/1110/1111 are the key hostile set.

## 8. Tasks

- [ ] **Task 0 (gate, STOP if any fails)**
  1. `git fetch origin && git merge-base --is-ancestor <WEAR-04 merge commit> origin/main`; same for WEAR-03, WEAR-05.
  2. Find the committed OM-2 notes: `git grep -n -i "OM-2" -- docs | grep -v "wearables-1[12]\|wearables-00\|research/2026-10-12\|reviews/"`. **If no OM-2 notes document (with §3 items answered) exists in the repo, STOP.** Report "OM-2 notes absent" to the orchestrator and write no code. `TASK_LIST.md:100` is a queue row, not notes.
  3. Confirm D5 is answered (a) in the owner decisions file. If the owner picked (b)/(c), STOP: this plan does not cover them.
  4. Copy the OM-2 answers into §3's last column in this file (same PR). If any metric is FIT-only, STOP and ask.
  5. Read `modules/wearables/apple.py` and `aggregate.py`; align §6 shape. Record the real signatures here.
  6. Baseline: `cd src/backend && python -m pytest --collect-only -q | tail -1`; note the count.
- [ ] **Task 1 RED.** Write `test_wearables_garmin.py` with the `LAYOUT` helper. Run `cd src/backend && HF_HUB_OFFLINE=1 python -m pytest tests/test_wearables_garmin.py -p no:cacheprovider -q`. Expected: collection ImportError on `modules.wearables.garmin`. Paste it in the PR.
- [ ] **Task 2 GREEN, guards first.** ZIP guards (1106-1109), then JSON load with `parse_constant` that raises, size cap on bytes read, depth cap by catching `RecursionError` (1110-1112).
- [ ] **Task 3 GREEN, metrics.** One small function per metric reading paths from §3. FIT/out-of-scope counted by name only (1104, 1105).
- [ ] **Task 4 refactor.** Share guard code with `apple.py` only if the WEAR-04 L1 already extracted it.
- [ ] **Task 5 verify.** Target file command above, then full suite: `cd src/backend && flock /tmp/claude-1000/hc-pytest.lock env HF_HUB_OFFLINE=1 python -m pytest -p no:cacheprovider -q`. Collected = start + 16. Update CLAUDE.md / AGENT.md count slots in the same commit (SLOT-RULE). `test_api_rag_index_002b` may fail for the embedding model; do not touch its 0.7 threshold.

## 9. Mutation / break checks (temporary, never committed; `git diff` guard after reverting)

1. Count ZIP size from `ZipInfo.file_size` instead of bytes read → HC-WRB-1108 must go red.
2. Remove `parse_constant` → HC-WRB-1111 red.
3. Make the loop open `.fit` members → HC-WRB-1104 red.
4. Use `datetime.astimezone()` with host tz → HC-WRB-1116 red.

## 10. Acceptance criteria

- Target file: 16 passed, command and output pasted.
- Full suite: collected count = start + 16, output pasted; failures limited to the known embedding test, named.
- `git diff --stat` shows only the §4 files plus count slots.
- §3 last column filled from OM-2 in the same PR.

## 11. Rollback

Delete `garmin.py` and its test file; nothing imports them until WEAR-12. Revert the count slots.

## 12. What these tests cannot see

- Whether a real Garmin export matches the fixtures at all (fixtures come from OM-2 notes, one account, one date; recurring-failures #3 figures asserted not measured, #8 stale guidance read as authority).
- A fixture built from the same `LAYOUT` the parser reads proves consistency, not truth (#1 a green suite that could not have failed). The only real check is OW-W1-style dogfood with the owner's export.
- Garmin firmware or app changes that rename fields after OM-2.
- Speed on a multi-year export (OW-W2 style perf smoke; not run here).
- No test was run while drafting this plan.

## 13. Owner / model-machine items

- **OW-W3** (OM-2): blocks this plan. Note `docs/features/TASK_LIST.md:100` still bundles OM-2 with the dropped Samsung OM-3; WEAR-14 or the orchestrator should split it.
- **OW-W5**: D5 answer.
- OM-7 legal read (FIT licence) stays open; not needed for the JSON-only path but needed before public distribution.
