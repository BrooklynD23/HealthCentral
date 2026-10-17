# WEAR-05 — Daily Aggregation, Dedup and Multi-Device Overlap — Implementation Plan

**Last Updated:** 2026-10-13
**Owner:** repository owner
**Status:** PROPOSED — not executed (code waits for program M0 and WEAR-03 merged)
**Base measured:** `origin/main` @ `8234990`
**Refresh trigger:** WEAR-03 merges (record dict shape re-read from its code); WEAR-04 merges (confirm the parser emits exactly that shape); OM-1 notes land (they answer the duplicate-record and sleep-overlap questions in section 11); the owner answers D3; any edit to the WEAR-02 contract.
**Program:** [`2026-10-13-wearables-00-program.md`](2026-10-13-wearables-00-program.md) (A5, A5b, A6, A8)
**Depends on:** WEAR-03 (`timeparse.py`, `records.py`). Consumes the record shape that WEAR-04 and WEAR-11 emit; it does not need WEAR-04 merged to be built or tested.
**Owner decisions it depends on:** none. D3 (minimum days) is applied at read time by WEAR-08 and WEAR-09, not here. `describe()` only reports the day count.
**Size target:** M, about 480 lines (about 150 code, about 330 tests). Slightly over the one-PR target of 400; the test file is repetitive fixture tables. Split point if the reviewer wants it: `describe()` + its tests (about 120) separate from `aggregate_daily` (about 360).

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:test-driven-development, then superpowers:subagent-driven-development. Domain skill for backend: `asclexis-backend`. Steps use `- [ ]` checkboxes.

**Goal.** One pure module turns a stream of normalized records into `wearable-summary` v1 rows (one value per vendor, metric and local day) and offers `describe(values)` for the read-time statistics. One source wins each day; the others are counted in `duplicate_sources` and never summed. No mean exists anywhere in the module.

## 1. Scope

**This plan does:**
1. `modules/wearables/aggregate.py`: `aggregate_daily(records)`, `build_summary(rows, records_read, skipped)`, `describe(values)`.
2. Fixture-driven tests for source selection, sleep union, day attribution, DST, `tz_changed`, outliers and streaming memory.

**This plan does NOT license:**
- Reading or writing the database; the "current value" selection across imports is read-time work in WEAR-08 (A5b).
- Cross-vendor selection (WEAR-12).
- Coverage ("N of M days") and the D3 minimum-days suppression (WEAR-08, WEAR-09).
- Any mean, average, percentage change, threshold, "normal" band or good/bad flag (F1).
- Any import from `core`, `models`, `api` or other HealthCentral packages (A8).

## 2. Evidence

| Fact | Path:line @8234990 |
|---|---|
| Program A5: steps = sum of the selected source bucketed by start local date; sleep = union of the selected source's asleep intervals attributed whole to the end local date, duration between UTC instants; resting HR = last of the day; stats across days at read time | `docs/plans/2026-10-13-wearables-00-program.md` (A5 row of section 4) |
| Program A5b: rows immutable per import, unique (`import_id`, `metric`, `local_date`) | same file, A5b row |
| Program A6: local date from the record's own offset, `tz_changed` when a day has more than one offset | same file, A6 row |
| Record dict keys, units, enums, skip reasons, `make_record`: WEAR-03 section 5 | `docs/plans/2026-10-13-wearables-03-time-units.md` |
| `local_date`, `utc_instant`, `interval_minutes` come from `timeparse.py` (WEAR-03); the host timezone is never used | WEAR-03 section 5 |
| Skip items elsewhere are `{reason, detail}`; the summary uses `reason -> count` | `src/backend/modules/import_structured.py:45`, `:50` |
| Free-text cap discipline | `src/backend/modules/import_structured.py:41`, `:55` |
| `statistics.quantiles(data, n=4, method="inclusive")` on `[1..7]` returns `[2.5, 4.0, 5.5]`; on `[1, 2]` returns `[1.25, 1.5, 1.75]` | measured on 3.12.3 here; not measured on 3.11 |
| Backend baseline at this base: 1487 collected | `CLAUDE.md:30`, `AGENT.md:76` |
| Several sources (Watch, iPhone, apps) can write the same metric for one day; overlapping sleep records may appear | **INFERRED** (research C1/C2; OM-1 confirms) |
| `HKCategoryValueSleepAnalysis*` stage records overlap each other inside one source | **INFERRED** (OM-1 confirms) |

## 3. Files to touch

| Path | New/edit | Why | Approx lines |
|---|---|---|---|
| `src/backend/modules/wearables/aggregate.py` | new | grouping, selection, union, describe | 150 |
| `src/backend/tests/test_wearables_aggregate.py` | new | tests below | 330 |
| `CLAUDE.md` (30), `AGENT.md` (76) | edit | collected-count slots (SLOT-RULE) | 2 |

## 4. Ask-first files touched

None.

## 5. Data contract

**Input.** An iterable of normalized records (dicts with exactly WEAR-03's `RECORD_KEYS`: `source_vendor`, `metric`, `start`, `end`, `value`, `unit`, `source_name`, `device_class`). It is consumed **once**, never turned into a list: the function keeps one small accumulator per (vendor, metric, local day, source) so memory grows with days and sources, not with records.

**Output row** (the A5 row, keys in this order):

| Key | Rule |
|---|---|
| `source_vendor` | from the record |
| `metric` | one of the three |
| `local_date` | ISO date. Steps and resting HR: `local_date(start)`. Sleep: `local_date(end)` (wake date) |
| `value` | float. Steps: sum of the selected source's `value`, after collapsing exact duplicates (same `source_name`, `start`, `end`, `value`: counted once, skip reason `duplicate_record`; test HC-WRB-518, Codex plans N1; OM-1 confirms whether they occur). Resting HR: `value` of the record with the latest `utc_instant(start)` (ties: the later one in input order). Sleep: minutes in the **union** of that source's intervals for that date, merged on UTC instants |
| `unit` | `CANON_UNIT[metric]` |
| `utc_offset_minutes` | offset of the latest record of the selected source that day (steps/RHR: by `start`; sleep: by `end`) |
| `tz_changed` | `True` if the selected source's records that day show more than one UTC offset (sleep: start and end offsets of every interval are both counted, so a night that crosses a DST change is flagged) |
| `n_records` | count of the selected source's records that day |
| `device_class` | selected source's class |
| `source_name` | selected source's name, cut to 255 chars |
| `duplicate_sources` | number of **other** sources that had at least one valid record for that metric and date |

**Source selection** for each (vendor, metric, local date): rank by `device_class` (`apple_watch` 0, `garmin_device` 1, `iphone` 2, `other` 3); within a class, the source with the most records that day; still tied, the lower `source_name` in plain string order (so the output does not depend on input order). A source is the pair (`source_name`, `device_class`).

**Known limit of this rule.** A Watch worn for an hour beats an iPhone that counted the whole day. The program chose it (A5). Patients see `device_class` and `duplicate_sources` on the review screen (WEAR-07) so this is visible, not hidden.

**Other functions.**
- `build_summary(rows, records_read, skipped) -> dict`: `{"schema": "hc.wearable-summary", "version": "1.0", "rows": [...], "records_read": int, "skipped": {reason: count}}`. Rows are sorted by (`metric`, `local_date`). `skipped` merges the caller's counts with the aggregator's own and does not modify its arguments.
- `describe(values: Sequence[float]) -> dict` with exactly the keys `n`, `median`, `p25`, `p75`, `min`, `max`. `median` is `statistics.median`. `p25`/`p75` come from `statistics.quantiles(values, n=4, method="inclusive")`; **chosen** because it is stdlib, deterministic, stays inside [min, max], and needs no rank-rounding rule to explain on a review screen. Nearest-rank was rejected because it jumps for small day counts. With 1 value, `p25 = p75 = value`. With 0 values every statistic is `None` and `n` is 0. A NaN or infinite value raises `ValueError`. `n` is the number of days with data (one value per day).
- Aggregator's own skip reasons: `record_invalid` (record is not a dict with the exact keys, naive datetime, `end < start` for sleep, non-finite or negative value, unknown metric, vendor or device class) and `source_cap`. `MAX_SOURCES_PER_DAY = 8` bounds the accumulators against a hostile file with a new `sourceName` on every record; records from a ninth source on that (metric, date) are dropped and counted.

**Invariants.** Output values are finite and >= 0. Sleep minutes never exceed 1440 x (number of days spanned) for one source because the union cannot exceed the covered time. The module contains no `mean`, `average` or `avg` identifier (HC-WRB-510 greps the source).

## 6. TDD test list

File: `src/backend/tests/test_wearables_aggregate.py`. Fixtures are built with `make_record` and `parse_apple_timestamp` from WEAR-03, so a record-shape change breaks tests loudly. Research IDs covered: HC-WRB-003, HC-WRB-002 (the `tz_changed` half), F1.

| ID | Assertion | RED reason |
|---|---|---|
| HC-WRB-501 | iPhone steps 6000 (30 records) + Watch steps 4200 (10 records), same day -> one row, `value` 4200.0, `device_class` apple_watch, `n_records` 10, `duplicate_sources` 1; never 10200 (HC-WRB-003) | module missing |
| HC-WRB-502 | Steps within one source sum exactly; a record `23:50 -0700` to `00:10 -0700` is counted whole on its start date; the next day gets 0 from it | module missing |
| HC-WRB-503 | Selection table: {watch, garmin, iphone, other} each pair picks the higher class; equal class picks more records; equal records picks the lower `source_name`; 24 permutations of the same four-source input produce byte-identical rows | module missing |
| HC-WRB-504 | Two sources with overlapping sleep on the same night -> one row from the higher-ranked source only, `duplicate_sources` 1, minutes are not the union across sources | module missing |
| HC-WRB-505 | One source with nested stage intervals (Core 22:00-02:00, Deep 00:00-01:00, REM 01:30-03:00, Unspecified 02:30-03:30) -> minutes equal the union (330.0), not the sum (450.0) | module missing |
| HC-WRB-506 | Sleep 23:00 to 07:00 (+0000) is attributed to the wake date with 480.0 minutes; the evening date has no sleep row | module missing |
| HC-WRB-507 | Spring-forward night `2026-03-07 22:00 -0800` to `2026-03-08 06:00 -0700` -> 420.0; fall-back night `2026-10-31 22:00 -0700` to `2026-11-01 06:00 -0800` -> 540.0; both `tz_changed` True | module missing |
| HC-WRB-508 | Resting HR: three readings in shuffled input order -> `value` is the one with the latest UTC start; `n_records` 3; a later reading in a different offset still wins by UTC instant, not by wall clock | module missing |
| HC-WRB-509 | `tz_changed`: same day records at `-0700` and `+0100` -> True and `utc_offset_minutes` of the latest; single offset -> False; two records at different offsets land on their own local dates (HC-WRB-002, offset half) | module missing |
| HC-WRB-510 | `describe([1..7])` = n 7, median 4.0, p25 2.5, p75 5.5, min 1, max 7. Seven daily steps near 8000 plus one 40000 outlier: median equals the median without the outlier. Result keys are exactly the six names; the source text of `aggregate.py` contains none of `mean`, `average`, `avg` (F1) | module missing |
| HC-WRB-511 | `describe([])` -> `n` 0, rest `None`; `describe([5.0])` -> p25 = p75 = 5.0; `describe([1, 2])` -> p25 1.25, median 1.5, p75 1.75; `describe([1, float("nan")])` raises `ValueError` | module missing |
| HC-WRB-512 | Streaming: a generator of 300000 step records over 100 days is consumed once (a spy on `iter` shows one pass; no `list()` of the input); `tracemalloc` peak < 32 MB (ceiling fixed after the first measured run). 40 distinct sources on one day -> 8 kept, `skipped["source_cap"]` = records of the other 32 | module missing |
| HC-WRB-513 | Invalid records (naive datetime, `nan`, `-1`, unknown metric, missing key, sleep with `end < start`) are counted under `record_invalid`; the valid records around them produce the same rows as without them | module missing |
| HC-WRB-514 | `build_summary`: schema and version strings exact; rows sorted; `skipped` merges parser and aggregator counts (3 + 2 -> 5 for the same reason); the argument dicts are unchanged afterwards (compare to deep copies) | module missing |
| HC-WRB-515 | Every row has exactly the 11 keys of section 5 in order; `value` is `float`; `unit` equals `CANON_UNIT[metric]`; `local_date` parses with `date.fromisoformat`; `n_records` >= 1; `duplicate_sources` >= 0 | module missing |
| HC-WRB-516 | Determinism: a mixed fixture (all three metrics, 3 sources, 5 days) shuffled with `random.Random(0)` twenty times gives identical `build_summary` output | module missing |
| HC-WRB-517 | AST guard: imports in `aggregate.py` are stdlib plus `modules.wearables.*` only (A8) | file missing |
| HC-WRB-518 | two identical step records (same `source_name`, `start`, `end`, `value`) plus one distinct record from the same source on one day: daily value = one duplicate + the distinct one; `skipped["duplicate_record"] == 1` | duplicates summed (value too high) |

Expected new tests: 18 functions. Collected = Task 0 baseline + 18 (use `--collect-only -q` if parametrised).

## 7. Tasks

### Task 0 — gates
- [ ] `git merge-base --is-ancestor <WEAR-03 merge commit> origin/main`. STOP if not an ancestor; `ls src/backend/modules/wearables/` must show `timeparse.py` and `records.py`.
- [ ] Read `records.py` and confirm `RECORD_KEYS`, `CANON_UNIT`, `DEVICE_CLASSES` match section 5 here and WEAR-04 section 5. Any drift: fix the plan text before code.
- [ ] If WEAR-04 is already merged, run its HC-WRB-401 fixture through `aggregate_daily` once by hand and paste the rows.
- [ ] `git grep -n -i "hc-wrb-5" -- src/backend/tests` empty. Measure the baseline with `--collect-only -q`.
- [ ] If OM-1 is in: record answers on exact duplicate records and sleep overlaps (section 11) and adjust HC-WRB-501/505 fixtures to the real shapes.

### Task 1 — RED
- [ ] Write the test file with HC-WRB-501..518. Run: `cd src/backend && HF_HUB_OFFLINE=1 python -m pytest tests/test_wearables_aggregate.py -p no:cacheprovider -q`.
- [ ] Expect `ModuleNotFoundError: No module named 'modules.wearables.aggregate'` for all 17. Paste the first lines.

### Task 2 — GREEN
- [ ] Implement `describe` first (HC-WRB-510, 511 go green). Then steps (501, 502), resting HR (508), selection (503), sleep union (504-507), `tz_changed` (509), caps and invalid handling (512, 513), `build_summary` (514-516).
- [ ] After each group rerun the command above and note how many pass. Final expectation: 17 pass. Paste.
- [ ] Measure the HC-WRB-512 peak once, set the ceiling to about 2x that, remove the print.
- [ ] Full suite: `cd src/backend && flock /tmp/claude-1000/hc-pytest.lock env HF_HUB_OFFLINE=1 python -m pytest tests/ -p no:cacheprovider -q`; only `test_api_rag_index_002b` may fail (CLAUDE.md:30-33).
- [ ] Update `CLAUDE.md:30` and `AGENT.md:76`.

### Task 3 — refactor and checks
- [ ] Functions under 50 lines, accumulators not leaked to callers, no mutation of the input records (HC-WRB-513 compares). Lint per `AGENT.md`. Run section 8, then `git diff --name-only origin/main...HEAD` lists only section 3 files.

## 8. Mutation / break checks (temporary, never committed)

| # | Break | Expected red |
|---|---|---|
| B1 | Sum steps across all sources | HC-WRB-501 reads 10200.0; HC-WRB-503 fails |
| B2 | Sum interval lengths instead of merging | HC-WRB-505 reads 450.0; HC-WRB-504 changes |
| B3 | Attribute sleep to the start date | HC-WRB-506 and 507 fail |
| B4 | Compute `p25`/`p75` with `method="exclusive"` or replace median with mean | HC-WRB-510/511 numbers differ |
| B5 | Use `local_date` from wall clock after converting to UTC | HC-WRB-509 and 502 fail |
| B6 | Build `list(records)` first | HC-WRB-512 exceeds its ceiling or the single-pass spy fails |

Revert each with `git checkout -- src/backend/modules/wearables/aggregate.py`; `git diff --stat` guard. Record failing IDs in the PR.

## 9. Acceptance criteria (measured, seen output)

1. `test_wearables_aggregate.py`: 17 passed (output pasted).
2. HC-WRB-512 peak memory number printed once and the ceiling written.
3. Collected = baseline + 18; slots updated; only the known environmental failure in the full suite.
4. B1..B6 each flipped the named tests; clean `git diff --stat` after reverts.
5. Rows from the HC-WRB-401 fixture (WEAR-04) pass `validate_summary` once WEAR-02 is merged (checked in WEAR-06, not here; note the result in the WEAR-06 PR).

## 10. Rollback

Revert the PR. Only WEAR-06 imports this module; revert WEAR-06 first if it has landed. No data or config involved.

## 11. What these tests cannot see

- **#1 (a green suite that could not have failed).** Fixture tables I wrote check the rule I wrote. B1..B6 prove the tests can fail; they do not prove the rule is right for real exports.
- **#3 (figures asserted, not measured).** Whether real Apple data has exact duplicate records inside one source, how stage intervals overlap, and whether a Watch worn briefly should beat an iPhone are all unmeasured until OM-1 (INFERRED). The 8-source cap is a guess.
- **#4 (environment-dependent).** `statistics.quantiles` behaviour was measured on Python 3.12.3 only; 3.11 not run.
- **#8 (stale guidance reading as authority).** Program A5 is a planning rule, not an observed fact about Apple's data. If OM-1 contradicts it, change A5 first.
- **#9 (invariant at one site).** "No mean" is enforced here by a source grep and in WEAR-09 by the banned-phrase test; WEAR-08's API response and the frontend are not covered by this plan.
- Steps records that straddle midnight are attributed whole to the start date (known ceiling, not hidden).
- Time-zone travel across the date line inside a source: handled only through `tz_changed`; no correction is attempted.

## 12. Owner / model-machine items

- **OW-W0** (OM-1): same list as WEAR-04 plus: a day where both iPhone and Watch have steps (counts only), and one night with overlapping sleep records (interval times only, no identifiers). None else.
