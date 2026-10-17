# WEAR-03 — Timestamp, Offset and Unit Normalization — Implementation Plan

**Last Updated:** 2026-10-13
**Owner:** repository owner
**Status:** PROPOSED — not executed (code waits for program M0 and OM-1; see Task 0)
**Base measured:** `origin/main` @ `8234990`
**Refresh trigger:** OM-1 notes land (they replace every INFERRED row below); OM-2 notes land (fills the Garmin table); any edit to `core/time.py`; a profile or module named `modules/wearables/` appears on `origin/main` (WEAR-02 may have created the package first).
**Program:** [`2026-10-13-wearables-00-program.md`](2026-10-13-wearables-00-program.md) (A5, A6, A8)
**Depends on:** program M0 only (OM-1 formats). No other WEAR package.
**Owner decisions it depends on:** none directly. It builds the closed vocabulary D3/D8 later read. It assumes D1 (b) and D5 (a) only through what WEAR-04 and WEAR-11 do with it.
**Size target:** S, about 330 lines of diff of which about 170 are tests. One L1 PR.

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:test-driven-development, then superpowers:subagent-driven-development. Domain skill for backend: `asclexis-backend`. Steps use `- [ ]` checkboxes.

**Goal.** Two tiny pure modules that every parser and the aggregator share: `timeparse.py` turns a vendor timestamp string into a timezone-aware `datetime` that keeps the record's own offset, and `records.py` holds the closed vocabulary (metrics, canonical units, device classes, skip reasons), the unit map, the normalized-record dict shape and one shared error type. Neither touches the database, the network, the host timezone or any HealthCentral module.

## 1. Scope

**This plan does:**
1. Add `modules/wearables/timeparse.py`: strict Apple timestamp parser, `local_date`, `utc_instant`, `utc_offset_minutes`, `interval_minutes`.
2. Add `modules/wearables/records.py`: enums as tuples, `CANON_UNIT`, `normalize_unit`, skip-reason constants, `RECORD_KEYS` + `make_record`, `WearableParseError`.
3. Add `modules/wearables/__init__.py` (empty) unless it already exists.
4. Add one test file with fixtures that prove the offset, DST, host-timezone and unit rules.

**This plan does NOT license:**
- Any database, route, config or migration change (WEAR-01, 02, 06 own those).
- Any edit to `core/time.py`, `modules/import_structured.py`, or any ask-first file.
- Any Garmin parsing code. The Garmin timestamp forms are a table to fill from OM-2; WEAR-11 adds `parse_garmin_timestamp` after OM-2.
- Any rule about which source wins or how days are summed (WEAR-05).
- Imports from `core`, `models`, `api` or any other HealthCentral package (program A8).

## 2. Evidence

| Fact | Path:line @8234990 |
|---|---|
| Naive-UTC storage helpers exist: `utcnow` | `src/backend/core/time.py:9` |
| `utcfromtimestamp` (naive) | `src/backend/core/time.py:14` |
| `to_naive_utc` converts aware to UTC and drops tzinfo; leaves naive unchanged. Spans `:24-33`. | `src/backend/core/time.py:24` |
| `_parse_date` returns a date string only; for a full ISO datetime it keeps `.date()` of the parsed value and drops the time and offset. Its format tuple is date-only. **Do not reuse.** Program A6 says `:77-96`; the function ends at `:97` (`return None`). | `src/backend/modules/import_structured.py:74`, `:77`, `:95`, `:97` |
| Free-text cap constant and `_cap` helper exist; WEAR-03 does not import them (A8) but mirrors the discipline: nothing unbounded. | `src/backend/modules/import_structured.py:41`, `:55` |
| Skip items in the existing importer are `{reason, detail}` dicts; the wearable contract uses counts only (WEAR-02), so `detail` is not carried | `src/backend/modules/import_structured.py:45`, `:50` |
| Precedent for patching the host timezone in a test: `monkeypatch.setenv("TZ", ...)`, `time.tzset()`, `skipif(not hasattr(time, "tzset"))` | `src/backend/tests/test_gamification_api.py:84`, `:90`, `:91`, `:114` |
| Route-test helper (not used here; recorded so reviewers see no route test is owed) | `src/backend/tests/support/routes.py:27` |
| Backend baseline at this base: 1487 collected | `CLAUDE.md:30`, `AGENT.md:76` |
| Apple timestamp is `YYYY-MM-DD HH:MM:SS ±HHMM` (one space before the offset, no colon in the offset) | **INFERRED** (OM-1 confirms) |
| Apple resting-heart-rate unit string is `count/min`; step unit is `count`; sleep records have no unit attribute | **INFERRED** (OM-1 confirms) |
| Python 3.11+ `datetime.strptime` accepts `%z` with `+HHMM` | measured on 3.12.3 here (`datetime.strptime('2025-03-09 23:30:00 -0700', '%Y-%m-%d %H:%M:%S %z')` returns an aware value). Not measured on 3.11. |

## 3. Files to touch

| Path | New/edit | Why | Approx lines |
|---|---|---|---|
| `src/backend/modules/wearables/__init__.py` | new (skip if present) | package marker | 0 |
| `src/backend/modules/wearables/timeparse.py` | new | strict timestamp parse, local date, UTC instant, interval minutes | 80 |
| `src/backend/modules/wearables/records.py` | new | vocabulary, unit map, record shape, error type | 70 |
| `src/backend/tests/test_wearables_time.py` | new | tests below | 170 |
| `CLAUDE.md` (line 30), `AGENT.md` (line 76) | edit | collected-count slots, same commit (SLOT-RULE) | 2 |

## 4. Ask-first files touched

None. `core/time.py` is read only.

## 5. Data contract

**`parse_apple_timestamp(raw) -> datetime | None`.** Accepts exactly `YYYY-MM-DD HH:MM:SS ±HHMM` (full-match regex first, then `strptime`). Returns an aware `datetime` with a fixed `timezone(timedelta)`. Returns `None` for anything else: non-string, empty, longer than 32 characters, wrong separator, missing offset (never guess the host zone), `Z`, colon offset, trailing newline, offset minutes >= 60, offset outside -1200..+1400, year outside 1970..2100, `OverflowError` on UTC conversion.

**Garmin forms** (filled from OM-2; WEAR-11 owns the function):

| Form seen in the export | Example | Has offset? | Function | Status |
|---|---|---|---|---|
| (OM-2) | — | — | — | UNKNOWN until OM-2 |
| (OM-2) | — | — | — | UNKNOWN until OM-2 |

**Other functions** (all require aware input; naive input raises `ValueError` because a naive value means "host timezone", which this module never uses):
- `local_date(dt) -> date`: `dt.date()` of the value in its own offset.
- `utc_instant(dt) -> datetime`: `dt.astimezone(timezone.utc)`, still aware. Not `core.time.to_naive_utc`. That helper is for WEAR-06 when an aware value is stored in a naive-UTC column.
- `utc_offset_minutes(dt) -> int`.
- `interval_minutes(start, end) -> float | None`: `(utc_instant(end) - utc_instant(start))` in minutes; `end < start` returns `None`; equal returns `0.0`.

**`records.py`:**
- `METRICS = ("resting_heart_rate", "sleep_asleep_minutes", "step_count")`; `VENDORS = ("apple", "garmin")`; `DEVICE_CLASSES = ("apple_watch", "iphone", "garmin_device", "other")`. Must equal the WEAR-02 enums; whichever of WEAR-02 / WEAR-03 merges second deletes its copy and imports the other (program A14).
- `CANON_UNIT = {"resting_heart_rate": "bpm", "sleep_asleep_minutes": "min", "step_count": "count"}`.
- `normalize_unit(metric, raw_unit) -> str | None`. Exact, case-sensitive map: resting HR accepts `count/min`; steps accepts `count`; sleep accepts `None` (the value is computed minutes). Anything else returns `None`; the caller counts skip reason `unit_unsupported`.
- Skip reasons (counts only, never file text): `timestamp_malformed`, `unit_unsupported`, `value_malformed`, `interval_invalid`. `SKIP_REASONS` is the closed tuple. WEAR-04, 05, 11 add their own reasons in their own modules.
- **Normalized record** (a plain dict, treated as read-only; the exact shape WEAR-04 and WEAR-11 emit and WEAR-05 consumes):

| Key | Type | Note |
|---|---|---|
| `source_vendor` | str in `VENDORS` | |
| `metric` | str in `METRICS` | |
| `start`, `end` | aware `datetime` | own offset kept; `end` may equal `start` for point readings |
| `value` | float, finite, >= 0 | steps = count; resting HR = bpm; sleep = interval minutes (informational, WEAR-05 recomputes the union) |
| `unit` | str | equals `CANON_UNIT[metric]` |
| `source_name` | str, <= 255 chars | app-only, never printed in the packet |
| `device_class` | str in `DEVICE_CLASSES` | |

`RECORD_KEYS` is that key tuple. `make_record(**kw)` builds the dict, takes keyword-only arguments, and raises `ValueError` for an unknown metric, vendor or device class or a wrong unit.
- `WearableParseError(ValueError)` with a `code` attribute; `str(e)` is the code only, so no file text can reach a log or an HTTP body.

**Invariants.** Imports are stdlib only. No function reads the environment, the clock or `time.tzset` state. Outputs depend only on arguments.

## 6. TDD test list

File: `src/backend/tests/test_wearables_time.py`. Research ID HC-WRB-002 is covered only for offset bucketing; its "DST day sets `tz_changed`" half lives in WEAR-05 (HC-WRB-509).

| ID | Assertion | RED reason |
|---|---|---|
| HC-WRB-301 | `parse_apple_timestamp("2026-03-09 23:30:00 -0700")` returns aware `datetime` with offset -420 min and the same wall clock | module missing (`ImportError`) |
| HC-WRB-302 | `23:30 -0700` has `local_date` 2026-03-09 and UTC instant 2026-03-10 06:30Z; `00:30 +0100` on 2026-03-10 has `local_date` 2026-03-10 and UTC instant 2026-03-09 23:30Z (each record keeps its own date) | function missing |
| HC-WRB-303 | Parametrised malformed table returns `None`: `None`, `""`, `b"..."`, an int, `"2026-03-09T23:30:00 -0700"`, `"2026-03-09 23:30:00"` (naive), `"2026-03-09 23:30:00 Z"`, `"2026-03-09 23:30:00 -07:00"`, `"2026-03-09 23:30:00 -0700\n"`, `"2026-03-09 23:30:00 -0775"`, `"2026-03-09 23:30:00 +1500"`, `"2026-03-09 23:30:00 -1300"`, `"1969-12-31 23:59:59 +0000"`, `"2101-01-01 00:00:00 +0000"`, a 5000-character string | function missing |
| HC-WRB-304 | Half-hour and 45-minute offsets (`+0530`, `+0545`, `-0330`) parse; `utc_offset_minutes` returns 330, 345, -210 | function missing |
| HC-WRB-305 | Host-timezone independence: with `TZ` set to `Pacific/Kiritimati`, `America/Los_Angeles` and `UTC` in turn (`monkeypatch.setenv` + `time.tzset()`), the tuple `(local_date, utc_instant, utc_offset_minutes, interval_minutes)` for a fixed fixture set is identical. A sentinel first asserts the patch took effect (`datetime.fromtimestamp(0).hour` differs between the two zones) and fails loudly otherwise. Skipped only where `time.tzset` does not exist (same guard as `tests/test_gamification_api.py:84`) | functions missing |
| HC-WRB-306 | `local_date`, `utc_instant`, `interval_minutes` on a naive `datetime` raise `ValueError` (naive means host zone) | functions missing |
| HC-WRB-307 | Spring-forward night: `2026-03-07 22:00:00 -0800` to `2026-03-08 06:00:00 -0700` is `420.0` minutes (7 h of real time, not 8) | function missing |
| HC-WRB-308 | Fall-back night: `2026-10-31 22:00:00 -0700` to `2026-11-01 06:00:00 -0800` is `540.0` minutes | function missing |
| HC-WRB-309 | `end < start` returns `None`; `end == start` returns `0.0`; start and end in different offsets compare by UTC instant | function missing |
| HC-WRB-310 | `normalize_unit` table: (`resting_heart_rate`, `count/min`) is `bpm`; (`step_count`, `count`) is `count`; (`sleep_asleep_minutes`, `None`) is `min`. Unsupported return `None`: (`step_count`, `km`), (`step_count`, `None`), (`resting_heart_rate`, `Count/Min`), (`resting_heart_rate`, `count/s`), (`sleep_asleep_minutes`, `hr`), (`unknown_metric`, `count`) | `ImportError` |
| HC-WRB-311 | `SKIP_REASONS` equals the exact 4-tuple above; every entry matches `^[a-z_]{1,40}$` | `ImportError` |
| HC-WRB-312 | `make_record(...)` returns a dict whose keys equal `RECORD_KEYS` in order; unknown metric, vendor, device class and a wrong unit each raise `ValueError`; a missing keyword raises `TypeError` | `ImportError` |
| HC-WRB-313 | `WearableParseError("zip_unsafe_name").code == "zip_unsafe_name"` and `str(...)` equals the code, not a sentence | `ImportError` |
| HC-WRB-314 | AST guard: every import in `timeparse.py` and `records.py` is in `sys.stdlib_module_names`; none starts with `core`, `models`, `api`, `modules`, `security` (program A8). Reads the source files; fails if either file is missing | files missing |

**Collected count.** Start from the number measured in Task 0 (1487 at this base, `CLAUDE.md:30`). Expected end = start + 14 test functions (the HC-WRB-303 and 310 parametrised tables count as one function each only if written as loops; if written with `pytest.mark.parametrize`, count the collected items printed by `--collect-only -q` and use that number). Update both slots in the same commit.

## 7. Tasks

### Task 0 — gates and ancestry
- [ ] `set -e; cd /mnt/c/Users/DangT/Documents/GitHub/hc-wear-plans && git fetch origin && git merge-base --is-ancestor 8234990 origin/main && echo ok`.
- [ ] Program M0 met: OM-1 notes committed under `docs/research/` (STOP if absent: the INFERRED rows above are unconfirmed). Record the timestamp example string from OM-1 and diff it against row 1 of the evidence table.
- [ ] `ls src/backend/modules/wearables/` : if WEAR-02 already created the package, do not recreate `__init__.py`.
- [ ] `git grep -n "hc-wrb-30" -- src/backend/tests` is empty (no ID collision).
- [ ] Measure the baseline: `cd src/backend && HF_HUB_OFFLINE=1 python -m pytest tests/ --collect-only -q -p no:cacheprovider | tail -3` and write the number into the PR description.
- [ ] Confirm `ls /usr/share/zoneinfo/Pacific/Kiritimati /usr/share/zoneinfo/America/Los_Angeles` exists (tzdata present) or HC-WRB-305 cannot fail.

### Task 1 — RED
- [ ] Write `tests/test_wearables_time.py` with HC-WRB-301..314. Import from `modules.wearables.timeparse` and `modules.wearables.records` (same import style as `tests/agent/test_s0_foundation.py:14`).
- [ ] Run: `cd src/backend && HF_HUB_OFFLINE=1 python -m pytest tests/test_wearables_time.py -p no:cacheprovider -q`.
- [ ] Expect: every test errors with `ModuleNotFoundError: No module named 'modules.wearables'` (or `.timeparse`). Paste the first 10 lines of that output into the PR as the RED record. Not yet run in this planning pass.

### Task 2 — GREEN
- [ ] Create `records.py` (constants, `normalize_unit`, `make_record`, `WearableParseError`).
- [ ] Create `timeparse.py`: one compiled `re.fullmatch` pattern; `strptime` inside `try/except (ValueError, OverflowError)`; offset bounds check on `utcoffset()`; year bounds; the four helpers.
- [ ] Rerun the Task 1 command. Expect 14 test functions pass. Paste output.
- [ ] Full suite under lock: `cd src/backend && flock /tmp/claude-1000/hc-pytest.lock env HF_HUB_OFFLINE=1 python -m pytest tests/ -p no:cacheprovider -q`. Expect only the known environmental failure `test_api_rag_index_002b` (CLAUDE.md:30-33); do not touch its 0.7 threshold.
- [ ] Update `CLAUDE.md:30` and `AGENT.md:76` to the measured collected count.

### Task 3 — refactor and checks
- [ ] Re-read both files for lines over 100 characters and functions over 50 lines. Run the repo's lint command listed in `AGENT.md` (read it first; do not guess).
- [ ] Run the break checks in section 8, then `git diff --stat` must show only the five files in section 3.

## 8. Mutation / break checks (temporary, never committed)

| # | Break | Expected red |
|---|---|---|
| B1 | In `local_date`, replace `dt.date()` with `datetime.fromtimestamp(dt.timestamp()).date()` (host zone) | HC-WRB-305 fails; HC-WRB-302 may still pass on a UTC host, which is exactly why 305 exists |
| B2 | In `interval_minutes`, subtract the naive wall clocks (`end.replace(tzinfo=None) - start.replace(tzinfo=None)`) | HC-WRB-307 reads 480.0, HC-WRB-308 reads 480.0 |
| B3 | Relax the regex to `re.match` (not `fullmatch`) or drop the year bounds | HC-WRB-303 rows for the trailing newline and year fail |
| B4 | In `normalize_unit`, lower-case the input before the lookup | HC-WRB-310 `Count/Min` row fails |

After each: `git checkout -- src/backend/modules/wearables/` then `git diff --stat` must list nothing under `modules/wearables/` except the new files you meant to keep. Record the failing test IDs in the PR.

## 9. Acceptance criteria (measured, seen output)

1. Task 2 command prints 14 passed (or the collected-item number agreed in Task 0) for `test_wearables_time.py`. Paste it.
2. The same fixture set gives identical results under three `TZ` values (HC-WRB-305 output pasted).
3. Full-suite collected count equals the Task 0 baseline plus the new tests; both slots updated.
4. B1..B4 each turned the named tests red (IDs pasted), and `git diff --stat` after reverting shows no stray edits.
5. `git diff --name-only origin/main...HEAD` lists only the five files in section 3.

## 10. Rollback

Revert the PR. Nothing else imports these modules until WEAR-04 and WEAR-05 land, so removal is safe before then; after that, revert those first. No data, config or migration is involved.

## 11. What these tests cannot see

- **Recurring failure #1 (a green suite that could not have failed).** On a UTC host a host-timezone leak passes every non-TZ test. HC-WRB-305 plus the sentinel and break check B1 are the answer; if tzdata is missing the sentinel fails rather than skips.
- **Recurring failure #3 (figures asserted, not measured).** The Apple timestamp format and unit strings are INFERRED. Fixtures built from them prove the parser matches the inference, not the real export. Only OM-1 closes that, and Task 0 stops without it.
- **Recurring failure #4 (environment-dependent results).** Measured here on Python 3.12.3; the project targets 3.11+. `strptime("%z")` and `sys.stdlib_module_names` exist in 3.11, but that was not run on 3.11.
- Devices that write a timestamp with seconds precision outside the string (fractional seconds) or a historical offset that does not match the real zone rules: the offset is trusted as written.
- Whether clocks on the watch were set correctly. A wrong watch clock produces a plausible wrong date.

## 12. Owner / model-machine items

- **OW-W0** (OM-1): paste one real `Record` timestamp, one resting-HR unit string, one steps unit string and one sleep record (no values) so the INFERRED rows can be confirmed. No other item.
