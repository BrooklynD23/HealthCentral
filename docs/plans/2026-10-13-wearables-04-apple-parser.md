# WEAR-04 — Apple Export Parser (Streaming, Guarded) — Implementation Plan

**Last Updated:** 2026-10-13
**Owner:** repository owner
**Status:** PROPOSED — not executed (code waits for program M0, OM-1, and WEAR-03 merged)
**Base measured:** `origin/main` @ `8234990`
**Refresh trigger:** OM-1 notes land (every INFERRED row is re-checked and the size caps are re-sized); WEAR-03 merges (record shape and reason strings are re-read from its code); D4 is answered (upload size sets the ratio and byte caps); any edit to `modules/wearables/`.
**Program:** [`2026-10-13-wearables-00-program.md`](2026-10-13-wearables-00-program.md) (A8, A9, A10)
**Depends on:** WEAR-03 (`timeparse.py`, `records.py`). Used by WEAR-06; the zip guard is reused by WEAR-11.
**Owner decisions it depends on:** D1 (b): the parser never writes the ZIP anywhere; D4: the byte and ratio caps below are placeholders sized from OM-1 and from the signed upload cap.
**Size target:** M, about 700 lines including about 420 of tests. That is over the one-PR target of 400. **Recommended split at the Task 3/4 boundary:** PR 04a = `_zipguard.py` + its tests (about 300), PR 04b = `apple.py` + its tests (about 400). The orchestrator decides (see report).

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:test-driven-development, then superpowers:subagent-driven-development. Domain skill for backend: `asclexis-backend`. Steps use `- [ ]` checkboxes.

**Goal.** Take a binary file object holding an Apple Health export ZIP and yield normalized records for three metrics (resting heart rate, sleep asleep intervals, steps), counting everything else as skipped. Hostile input is refused with a coded error before it can use unbounded memory. The parser is pure: stdlib only, no database, no HealthCentral import, no write to disk.

## 1. Scope

**This plan does:**
1. `modules/wearables/_zipguard.py`: shared pure ZIP guards (member count, bytes-actually-read caps, ratio cap, name checks). WEAR-11 reuses it.
2. `modules/wearables/apple.py`: locate `export.xml`, scan the XML prolog, stream-parse with a pull parser, allowlist three record types, emit normalized records.
3. Two test files; hostile fixtures are generated in the tests (no binary blob over 50 KB is committed).

**This plan does NOT license:**
- Daily rows, source selection or summing (WEAR-05).
- A route, upload handling, hashing, temp files or audit (WEAR-06).
- Opening `export_cda.xml`, `workout-routes/*`, `electrocardiograms/*`, or reading raw `HeartRate` samples (F5, F13).
- Adding `defusedxml` or any dependency (program A9).
- Any ask-first file, `security/input_validator.py` included (WEAR-06 owns that gate).

## 2. Evidence

| Fact | Path:line @8234990 |
|---|---|
| The only ZIP code in the app today is a writer (backup); there is no ZIP reader to reuse | `src/backend/api/backup.py:25`, `:346` |
| Skip results elsewhere are `{reason, detail}` dict lists; the wearable summary uses reason counts only | `src/backend/modules/import_structured.py:45`, `:50` |
| Existing per-field text cap discipline (`_MAX_FIELD_LEN = 2000`, `_cap`) | `src/backend/modules/import_structured.py:41`, `:55` |
| Stdlib ZIP layout read from source: end record `structEndArchive = "<4s4H2LH"`, signature `PK\005\006`, total-entries is index 4 | `/usr/lib/python3.12/zipfile/__init__.py:78`, `:79`, `:86` |
| Central entry `"<4s4B4HL2L5H2L"` (compressed size at byte 20, uncompressed at byte 24); local header `"<4s2B4HL2L2H"` (compressed at 18, uncompressed at 22) | `/usr/lib/python3.12/zipfile/__init__.py:97`, `:150` |
| `XMLParser` in this CPython has no `.parser` attribute, so expat entity hooks cannot be attached through `xml.etree` | measured on 3.12.3: `hasattr(ET.XMLParser(), 'parser')` is `False` |
| `iterparse` signature is `(source, events=None, parser=None)` | measured on 3.12.3 |
| Time and unit rules, record dict shape, `WearableParseError`: WEAR-03 section 5 | `docs/plans/2026-10-13-wearables-03-time-units.md` |
| Backend baseline at this base: 1487 collected | `CLAUDE.md:30`, `AGENT.md:76` |
| Export lives at `apple_health_export/export.xml` inside the ZIP | **INFERRED** (OM-1 confirms; folder name may be localised) |
| Root element `HealthData`; children `Record`, `Workout`, `ActivitySummary`, `Correlation`, `ClinicalRecord` | **INFERRED** |
| `Record` attributes: `type`, `sourceName`, `sourceVersion`, `device`, `unit`, `creationDate`, `startDate`, `endDate`, `value`; a `Record` may hold `MetadataEntry` children | **INFERRED** |
| Types: `HKQuantityTypeIdentifierRestingHeartRate`, `HKQuantityTypeIdentifierStepCount`, `HKCategoryTypeIdentifierSleepAnalysis` | **INFERRED** |
| Sleep `value` strings: `HKCategoryValueSleepAnalysisAsleep` (legacy), `...AsleepCore`, `...AsleepDeep`, `...AsleepREM`, `...AsleepUnspecified` count as asleep; `...InBed` and `...Awake` do not | **INFERRED** (OM-1 confirms the full value set and how overlapping records look) |
| `export.xml` starts with a `<!DOCTYPE HealthData [ ... ]>` whose internal subset holds only `<!ELEMENT>` and `<!ATTLIST>` declarations | **INFERRED**. **This conflicts with the brief's wording** ("reject DOCTYPE with an internal subset"): rejecting every internal subset would reject every real export. The plan rejects `<!ENTITY`, external ids and any declaration other than ELEMENT/ATTLIST instead. OM-1 must show the real prolog. |
| `device` attribute is a descriptive string that may contain "Watch" or "iPhone" | **INFERRED** |
| Typical `export.xml` compression ratio and size (multi-GB uncompressed) | **INFERRED**; caps below are placeholders |

## 3. Files to touch

| Path | New/edit | Why | Approx lines |
|---|---|---|---|
| `src/backend/modules/wearables/_zipguard.py` | new | guards: EOCD count precheck, name rules, header precheck, `ReadBudget`, capped chunk reader, ratio | 110 |
| `src/backend/modules/wearables/apple.py` | new | member selection, prolog scan, token/depth guards, record mapping, device class | 190 |
| `src/backend/tests/test_wearables_zipguard.py` | new | guard tests (HC-WRB-410..415) | 150 |
| `src/backend/tests/test_wearables_apple.py` | new | parser tests + synthetic export builder | 270 |
| `CLAUDE.md` (30), `AGENT.md` (76) | edit | collected-count slots (SLOT-RULE) | 2 |

## 4. Ask-first files touched

None. (`security/input_validator.py` is WEAR-06's gate, D4.)

## 5. Data contract

**Entry point.**

```python
def parse_apple_export(fp: BinaryIO, limits: AppleLimits = DEFAULT_LIMITS) -> AppleParse: ...
class AppleParse:               # single use; iterating twice raises RuntimeError
    def records(self) -> Iterator[dict]: ...   # lazy; never builds a list
    records_read: int            # Record elements seen (all types); valid after the iterator is exhausted
    skipped: dict[str, int]      # snapshot copy: reason -> count
```

The mutable counters live inside `AppleParse` only (streaming needs them); nothing outside mutates them. `fp` must be seekable. The parser never calls `fp.read()` without a size.

**Normalized record** (exactly WEAR-03's `RECORD_KEYS`, built with `make_record`):

| Key | Apple value |
|---|---|
| `source_vendor` | `"apple"` |
| `metric` | `resting_heart_rate` / `step_count` / `sleep_asleep_minutes` |
| `start`, `end` | `parse_apple_timestamp(startDate)`, `(endDate)`; aware, own offset |
| `value` | float of `value` (finite, >= 0); sleep: `interval_minutes(start, end)` |
| `unit` | `normalize_unit(...)` result (`bpm`, `count`, `min`) |
| `source_name` | `sourceName` truncated to 255 chars (WEAR-02 column length) |
| `device_class` | closed map below |

**Device class map** (lower-case substring tests on `sourceName` + space + `device`, first match wins): contains `watch` -> `apple_watch`; contains `iphone` -> `iphone`; contains `garmin` -> `garmin_device`; else `other`. "Jane's Apple Watch" is `apple_watch`; the name itself is never emitted into the packet (program A7).

**Limits** (frozen dataclass `AppleLimits`, placeholders until OM-1 and D4):

| Field | Default | Note |
|---|---|---|
| `max_members` | 20000 | workout-route and ECG folders can hold thousands of files (INFERRED) |
| `max_member_bytes` | 8 GiB | uncompressed bytes **actually read** per member |
| `max_total_bytes` | 8 GiB | across all members read (only `export.xml` is read) |
| `max_ratio` | 100 | bytes read / physical archive size; physical size from `fp.seek(0, 2)` |
| `prolog_bytes` | 262144 | prolog must end (first real start tag) inside this |
| `max_token_bytes` | 65536 | longest run of bytes between two `<` |
| `max_depth` | 32 | element nesting |
| `chunk_bytes` | 65536 | read size |

**Fatal errors** (`WearableParseError.code`; WEAR-06 maps all to HTTP 400 with the code only): `zip_not_readable`, `zip_encrypted`, `zip_too_many_members`, `zip_unsafe_name`, `zip_member_too_large`, `zip_total_too_large`, `zip_ratio_exceeded`, `export_xml_missing`, `export_xml_ambiguous`, `xml_prolog_rejected`, `xml_token_too_large`, `xml_depth_exceeded`, `xml_malformed`, `xml_root_unexpected`.

**Counted skip reasons** (strings from this module, never from the file): the four WEAR-03 reasons plus `type_not_allowlisted`, `sleep_not_asleep`, `sleep_value_unrecognized`, `element_not_record`, `ignored_export_cda`, `ignored_workout_routes`, `ignored_electrocardiograms`, `ignored_other_member`.

**Zip guard order** (`_zipguard.open_guarded(fp, limits)`):
1. Read the last 66 KB; find `PK\005\006`; read total entries. If it is `0xFFFF` (Zip64 marker) or above `max_members`, raise `zip_too_many_members` **before** `zipfile.ZipFile` loads the central directory. Not found: `zip_not_readable`.
2. Open `zipfile.ZipFile(fp)`; any `BadZipFile` becomes `zip_not_readable`.
3. Every member name: reject `..` segment, leading `/` or `\`, any `\`, NUL, drive letter -> `zip_unsafe_name` (all members, opened or not).
4. Header pre-check: sum of `file_size` above `max_total_bytes` -> `zip_total_too_large`. Cheap early exit only. Headers are attacker-controlled, so this is never the real guard.
5. Reading goes through `ReadBudget` + a chunk reader that counts bytes actually returned and raises `zip_member_too_large`, `zip_total_too_large` or `zip_ratio_exceeded` the moment a cap is crossed. At most one chunk beyond the cap is inflated.
6. Encrypted member (flag bit 0): `zip_encrypted`.

**XML prolog rule** (before any byte reaches the parser): accumulate up to `prolog_bytes`; strip `<!-- -->` and `<? ?>` runs (unterminated -> `xml_prolog_rejected`); the prolog ends at the first `<` followed by a letter or `_`; none found in the window -> `xml_prolog_rejected`. In the raw prolog, reject: any `<!ENTITY` (case-insensitive); `<!DOCTYPE` with `SYSTEM` or `PUBLIC`; any `<!` declaration inside it other than `ELEMENT`/`ATTLIST`.

**Streaming rule.** `xml.etree.ElementTree.XMLPullParser(events=("start","end"))`, fed 64 KB chunks (iterparse is the same engine; the feed loop is needed to run the guards on each chunk). Depth counter from start/end events. Process only direct children of the root: on their `end`, map `Record`, count others as `element_not_record`, then `root.clear()` so cleared children do not pile up under the root. First start tag must be `HealthData` (INFERRED) else `xml_root_unexpected`.

## 6. TDD test list

Research IDs covered: HC-WRB-001 (partly: parser level, daily rows are WEAR-05), 005, 006; safety F5, F6, F12, F13. Fixture builders live in the test files and build ZIPs with `zipfile` from small dicts.

**`test_wearables_zipguard.py`**

| ID | Assertion | RED reason |
|---|---|---|
| HC-WRB-410 | Byte cap: a 64 MB zero member in a small archive, `max_member_bytes=10 MB`, ratio cap raised out of the way: raises `zip_member_too_large`; bytes inflated <= cap + one chunk (counted by a wrapper); `tracemalloc` peak < 64 MB (ceiling fixed after the first measured run) | module missing |
| HC-WRB-411 | Ratio cap with default `max_ratio=100`: the same shape raises `zip_ratio_exceeded` while a ratio-10 member of equal size passes | module missing |
| HC-WRB-412 | Header lie: patch compressed/uncompressed sizes to 1 byte in both the central and local headers (offsets in section 2) of a honest bomb; reading still ends in a `zip_*` error and yields no record | module missing |
| HC-WRB-413 | Unsafe names each raise `zip_unsafe_name`: `../x`, `a/../../x`, `/etc/x`, `\win\x`, `a\b`, `C:/x`, name with NUL, even when the member is never read | module missing |
| HC-WRB-414 | EOCD patched to total entries `0xFFFF`: raises `zip_too_many_members` with `zipfile.ZipFile` monkeypatched to fail the test if called; separately 5 real members with `max_members=3` raise the same code | module missing |
| HC-WRB-415 | Not a zip (random bytes), empty file, truncated archive -> `zip_not_readable`; member with encryption flag patched on -> `zip_encrypted`; `str(e)` equals the code and never contains the hostile member name `SECRET` | module missing |

**`test_wearables_apple.py`**

| ID | Assertion | RED reason |
|---|---|---|
| HC-WRB-401 | Synthetic export (1 resting HR, 2 step, 2 asleep sleep records, one export.xml) yields exactly the 5 expected normalized records: keys equal `RECORD_KEYS`, `start`/`end` aware with the fixture offset, units `bpm`/`count`/`min`, vendor `apple` | module missing |
| HC-WRB-402 | Allowlist: `HeartRate`, `OxygenSaturation`, `ActiveEnergyBurned` and an unknown type produce zero records and `skipped["type_not_allowlisted"]` equals their count; a `HeartRate` record with a valid value never appears (F5, F6) | module missing |
| HC-WRB-403 | Sleep values: `Asleep`, `AsleepCore`, `AsleepDeep`, `AsleepREM`, `AsleepUnspecified` emitted; `InBed` and `Awake` -> `sleep_not_asleep`; `FooBar` -> `sleep_value_unrecognized` | module missing |
| HC-WRB-404 | Steps with unit `km` or no unit -> `unit_unsupported`; resting HR with `count/min` accepted, with `bpm` rejected | module missing |
| HC-WRB-405 | Bad timestamp, `nan`, `inf`, `-1`, `abc`, a 70-character value, `endDate` before `startDate` -> the matching counted reason, no record, later records still parsed | module missing |
| HC-WRB-406 | `export_cda.xml`, `workout-routes/r.gpx`, `electrocardiograms/e.csv` hold a sentinel string; a spy on `ZipFile.open` shows only `export.xml` was opened; counts under `ignored_*` equal 1 each; no record contains the sentinel (HC-WRB-006, F13) | module missing |
| HC-WRB-407 | No `export.xml` -> `export_xml_missing`; two `*/export.xml` -> `export_xml_ambiguous`; root element `Foo` -> `xml_root_unexpected` | module missing |
| HC-WRB-408 | Entity bomb (nested `<!ENTITY a0..a9>` expansion, "billion laughs") -> `xml_prolog_rejected`; `tracemalloc` peak < 64 MB (HC-WRB-005, F12) | module missing |
| HC-WRB-409 | Prolog table: Apple-style DOCTYPE with only ELEMENT/ATTLIST accepted; `SYSTEM "x.dtd"` rejected; `<!ENTITY` after a 200 KB comment pad rejected or prolog-too-long rejected; unterminated comment rejected; DOCTYPE hidden after a comment containing `<a` rejected | module missing |
| HC-WRB-416 | Giant attribute: a 10 MB `sourceName` -> `xml_token_too_large`, parser fed < `max_token_bytes` + one chunk, peak < 64 MB; a 60 KB `sourceName` inside the limit is truncated to 255 chars | module missing |
| HC-WRB-417 | Depth bomb: 100000 nested `<a>` -> `xml_depth_exceeded` | module missing |
| HC-WRB-418 | Streaming memory: 150000 flat `Record` elements consumed one at a time (generator, no list) keep `tracemalloc` peak under a ceiling fixed after the first measured run; count of records matches | module missing |
| HC-WRB-419 | Device class table: ("Jane's Apple Watch","") apple_watch; ("iPhone","") iphone; ("Health","Apple Watch") apple_watch; ("MyApp","") other; a 1000-char name is `other` and truncated to 255; every emitted `device_class` is in `DEVICE_CLASSES` | module missing |
| HC-WRB-420 | `fp` contract: `io.BytesIO`, a real file, and `tempfile.SpooledTemporaryFile` all work; a wrapper that raises on size-less `read()` is never tripped | module missing |
| HC-WRB-421 | `records_read` counts `Record` elements only; `Workout`, `ActivitySummary` and a `Correlation` (its nested `Record` too) count under `element_not_record`; iterating `records()` twice raises `RuntimeError` | module missing |
| HC-WRB-422 | AST guard: `apple.py` and `_zipguard.py` import only stdlib modules and `modules.wearables.*` siblings (A8) | files missing |

Expected new tests: 6 + 16 = 22 functions (count `--collect-only` items if parametrised). Collected = Task 0 baseline + that number; update both slots.

## 7. Tasks

### Task 0 — gates
- [ ] `git merge-base --is-ancestor <WEAR-03 merge commit> origin/main`. STOP if not an ancestor. `ls src/backend/modules/wearables/` must show `timeparse.py` and `records.py`.
- [ ] OM-1 committed and read. For every INFERRED row in section 2 write confirmed / changed next to it in the PR. If the real prolog or root differs, fix section 5 first.
- [ ] D4 answered or the placeholder default accepted in writing; re-size `max_member_bytes` and `max_ratio` from OM-1's real ZIP size and ratio.
- [ ] `git grep -n -i "hc-wrb-4" -- src/backend/tests` empty. Measure baseline with `--collect-only -q`.

### Task 1 — RED (guard)
- [ ] Write `test_wearables_zipguard.py` (HC-WRB-410..415). Run: `cd src/backend && HF_HUB_OFFLINE=1 python -m pytest tests/test_wearables_zipguard.py -p no:cacheprovider -q`. Expect `ModuleNotFoundError: modules.wearables._zipguard` on all six. Paste.

### Task 2 — GREEN (guard)
- [ ] Implement `_zipguard.py` in the order of section 5. Rerun; expect 6 pass. Fix the two memory ceilings from the measured peak (record the number; do not guess).

### Task 3 — RED (parser)
- [ ] Write `test_wearables_apple.py` with the synthetic-export builder (`build_export(records: list[dict], extra_members: dict, doctype: str | None)`). Run `python -m pytest tests/test_wearables_apple.py ...`. Expect `ModuleNotFoundError: modules.wearables.apple` on all.

### Task 4 — GREEN (parser)
- [ ] Implement `apple.py`: member selection, prolog scan, token/depth guards, record mapping, device map. Rerun; expect 16 pass. Then the full suite: `cd src/backend && flock /tmp/claude-1000/hc-pytest.lock env HF_HUB_OFFLINE=1 python -m pytest tests/ -p no:cacheprovider -q`. Only `test_api_rag_index_002b` may fail (CLAUDE.md:30-33).
- [ ] Update `CLAUDE.md:30`, `AGENT.md:76`.

### Task 5 — refactor and checks
- [ ] Functions under 50 lines; no mutation of arguments; run the lint command named in `AGENT.md`. Run section 8 breaks. `git diff --name-only origin/main...HEAD` lists only section 3 files.

## 8. Mutation / break checks (temporary, never committed)

| # | Break | Expected red |
|---|---|---|
| B1 | Delete the `<!ENTITY` check in the prolog scan | HC-WRB-408 and HC-WRB-409 fail |
| B2 | Count bytes from `ZipInfo.file_size` instead of bytes read | HC-WRB-410 or HC-WRB-412 fail |
| B3 | Drop `root.clear()` | HC-WRB-418 exceeds its ceiling (if it does not, raise the record count until it does, then keep that count) |
| B4 | Add `HKQuantityTypeIdentifierHeartRate` to the allowlist | HC-WRB-402 fails |
| B5 | Open every member to "check" it | HC-WRB-406 fails |

Revert with `git checkout -- <file>`; `git diff --stat` guard each time. Record failing IDs in the PR.

## 9. Acceptance criteria (measured, seen output)

1. Guard file: 6 pass. Parser file: 16 pass. Output pasted.
2. Peak memory numbers for HC-WRB-408, 410, 416, 418 printed once (`-s` with a debug print removed before commit) and the ceilings written into the tests.
3. Full suite: collected = baseline + 22 (or the printed item count); only the known environmental failure.
4. B1..B5 each flipped the named tests; `git diff --stat` clean after reverting.
5. Both new modules import only stdlib (HC-WRB-422 green).

## 10. Rollback

Revert the PR(s). WEAR-06 is the first caller, so removal is safe before it lands; afterwards revert WEAR-06 first. No data or config involved.

## 11. What these tests cannot see

- **#3 and #4 (figures asserted, environment-dependent).** Every caps number and every Apple format row is a placeholder or INFERRED. Real exports may be multi-GB with an unknown ratio; a hostile file smaller than the caps but slow to parse (wall-clock) is not bounded by any test here. OW-W2 measures time and peak memory on the owner's machine.
- **#1 (green suite that could not fail).** `tracemalloc` peaks depend on the interpreter and the fixture size; break check B3 exists to prove the ceiling can be crossed.
- **#9 (invariant at one site, not across its class).** The guard protects the Apple path only. WEAR-11 must call the same `_zipguard`; WEAR-06 must call the parser rather than reopen the ZIP itself. Neither is enforced by this plan's tests.
- Duplicate records inside one source: the parser does not de-duplicate exact repeats (WEAR-05 sums them). Whether Apple writes exact duplicates is an OM-1 question.
- Locale-dependent names (localised folder or file names) beyond the single-folder `*/export.xml` pattern.
- Python 3.11 behaviour: measured pieces ran on 3.12.3 only.

## 12. Owner / model-machine items

- **OW-W0** (OM-1): the real prolog text (first 2 KB of `export.xml`, no values), root element name, `Record` attribute names, ZIP size and uncompressed size of `export.xml`, whether exact duplicate step records exist, and the sleep `value` set.
- **OW-W2**: 200 MB synthetic import time and peak memory on Windows.
