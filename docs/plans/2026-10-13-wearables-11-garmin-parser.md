# WEAR-11 — Garmin Export Parser (11a JSON, stdlib; 11b FIT via pinned SDK) — Implementation Plan

**Last Updated:** 2026-10-13
**Owner:** repository owner
**Status:** PROPOSED — not executed. Code waits for program M0, M4 (Apple slice done) and **OM-2 notes committed**; 11b also waits for the **FIT licence read (OW-W7)**. D5 is resolved (WEAR-D5, below).
**Base measured:** `origin/main` @ `8234990`. Product-code lines below were re-read on the planning tree (`a985390`, docs-only ahead of the base) on 2026-10-13.
**Refresh trigger:** OM-2 notes land (fill the table in §3); WEAR-03/04/05 merge (record shape may differ from §6); D5 answer changes; any edit to `modules/wearables/`.
**Program:** [`2026-10-13-wearables-00-program.md`](2026-10-13-wearables-00-program.md) (A8, A9, R2, wave WE).
**Depends on:** WEAR-03 (`timeparse.py`), WEAR-04 (`apple.py`: guard helpers and normalized-record shape), WEAR-05 (`aggregate.py`). All three are PLANNED, not existing. Gate: OM-2.
**Owner decisions it depends on:** **WEAR-D5** (owner, 2026-10-14; commit `c53ba44`, PR #92): **"(b) garmin-fit-sdk after licence read"** — not the recommendation. See §0. **WEAR-D4** does not cover `requirements.txt`; the dependency pin is listed for owner sight in 11b.

## 0. Amendment after WEAR-D5 (2026-10-14) — supersedes conflicting text below

The plan now ships as two PRs from this file:

- **11a — JSON parser (unchanged from the text below).** JSON stays the path for every in-scope metric that OM-2 shows in JSON. FIT members are still counted `fit_not_supported` in 11a.
- **11b — FIT path for metrics absent from JSON.** Only for an in-scope metric (resting HR, sleep, steps) that OM-2 shows exists **only** in FIT files. If OM-2 shows all three in JSON, 11b is not built and FIT stays counted-and-skipped.
  - **Gate:** OW-W7 licence read done and recorded as an owner-decisions row (`WEAR-FIT-LIC`) saying an open-source, pip-installed dependency on `garmin-fit-sdk` is acceptable. A "no" stops 11b; 11a stands alone.
  - **Dependency:** add `garmin-fit-sdk==<exact version>` to `src/backend/requirements.txt`, pinned with `==` (never a range), the version chosen at Task 0 from PyPI, at least two weeks old, and recorded with its licence file hash in the PR. One new file imports it: `modules/wearables/garmin_fit.py`. Program A8 (stdlib-only parsers) gets this one named exception; an AST guard (HC-WRB-1118) asserts no other module imports `garmin_fit_sdk`.
  - **Local-only:** decode from bytes already read through `_zipguard.py` caps (per-member FIT byte cap, default 64 MiB, sized from OM-2). HC-WRB-1119 imports/reloads `modules.wearables.garmin_fit` **inside** a context that patches `socket.socket`, `socket.create_connection`, `socket.getaddrinfo` and `subprocess.Popen` to raise, then runs a full FIT parse and asserts it succeeds (no network, no subprocess at import or parse). HC-WRB-1121 statically scans the installed `garmin_fit_sdk` package's `.py` files for imports of `socket`, `urllib`, `http.client`, `requests` and `subprocess` and fails if any is found (Opus D1D8 A8). HC-WRB-1122 pins the exact `==` line in `requirements.txt`. HC-WRB-1120 asserts FIT-derived records use the same normalized record shape and `device_class="garmin_device"`.
  - **Same rules:** WEAR-03 offsets/local dates (FIT timestamps are UTC seconds since 1989-12-31 plus a local-time offset field where present — INFERRED, OM-2 confirms); WEAR-05 aggregation; no FIT field outside the 3 metrics is read or stored.
  - **Owner sight:** the exact `requirements.txt` line is shown in the 11b PR body for the owner; it is a new dependency, not an ask-first file.
**Size target (Opus D1D8 A7):** **11a** M, ~400 diff lines (parser ~180, tests ~220). **11b** S, ~120 source lines (`garmin_fit.py` ~90, wiring ~30, one `requirements.txt` line) plus ~150 of tests; separate PR after 11a and WEAR-12.

> For agentic workers: use superpowers:test-driven-development and superpowers:subagent-driven-development; domain skill `asclexis-backend`. RED first, log the failure.

## 1. Scope

Does:
- Add `src/backend/modules/wearables/garmin.py`, a pure stdlib parser: ZIP in (binary file object), normalized records out, same shape as `apple.py`.
- Apply the A9 guards to ZIP and JSON (member count, bytes-actually-read caps, name checks, JSON size and depth, NaN rejection).
- Emit only resting heart rate, steps, sleep intervals. `device_class="garmin_device"`, `source_vendor="garmin"`.
- Count FIT members as skipped `fit_not_supported`; count every out-of-scope file as `metric_not_in_scope`. Neither is opened.

Does NOT:
- 11a: no FIT decoding, no new dependency. FIT decoding is 11b only (§0).
- No stress, HRV, SpO2, Body Battery, respiration, heart-rate samples (program non-goals; F5).
- No route, DB, aggregation or vendor detection (WEAR-12 / WEAR-05).
- No guessing a layout. A metric that OM-2 shows only in FIT goes to 11b (§0), not into the JSON parser.
- No claim that any real Garmin export matches the fixtures (R2, program §11).

## 2. Evidence

| Fact | path:line |
|---|---|
| Program: Garmin slice after M4; JSON first (11a), FIT only via 11b after the licence read (WEAR-D5 (b), signed) | `docs/plans/2026-10-13-wearables-00-program.md:139` (R2), `:163` (D5) |
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
| 11b: `src/backend/modules/wearables/garmin_fit.py` | new | the one module that imports `garmin_fit_sdk` | ~90 |
| 11b: `src/backend/requirements.txt` | edit | one `garmin-fit-sdk==<exact>` line | 1 |
| 11b: `src/backend/tests/test_wearables_garmin_fit.py` | new | 1118-1122 | ~150 |
| 11b: `modules/wearables/garmin.py` | edit | route in-scope FIT members to `garmin_fit.py` (WEAR-12 wiring unchanged) | ~30 |

If WEAR-04 put the ZIP guard helpers in `apple.py`, import them from a shared `_zipguard.py` created by the WEAR-04 L1; if not, Task 0 decides between a tiny `_zipguard.py` move (preferred, one more file) and a copy. Do not edit `apple.py` behaviour.

## 5. Ask-first files touched

None. (`security/input_validator.py` is WEAR-06's D4 gate, not here.)

## 6. Data contract

Output (planned shape, **Task 0 re-reads `apple.py` and matches it exactly**): `ParseResult(records: Iterator[dict], records_read: int, skipped: dict[str,int])` — records are **yielded**, never collected into a list (Codex plans N2). Each JSON member is read through a byte counter and refused above `max_json_member_bytes` (default 64 MiB, sized from OM-2) **before** `json.loads`; test HC-WRB-1117 measures tracemalloc peak on a valid export at the production default caps. Each record dict (INFERRED from the WEAR-04 plan): `metric` in `{resting_heart_rate, sleep_asleep_minutes, step_count}`-source kinds, `start` / `end` aware `datetime` (own offset kept), `value`, `unit`, `source_vendor="garmin"`, `device_class="garmin_device"`, `source_name` capped (`_MAX_FIELD_LEN` pattern, 255 for the column).

Skip reasons added by this plan (closed set, counts only): `fit_not_supported`, `metric_not_in_scope`, `json_invalid`, `json_too_deep`, `value_invalid`, `timestamp_invalid`, `unit_unsupported` (WEAR-03 name). Refusals (raise `ParseError`, route maps to 400): too many members, member or total too large, unsafe member name, ZIP unreadable.

Invariants: values finite and >= 0; no mean; no free text from the file outside `source_name`; parser never sums steps or merges sleep (WEAR-05 does).

## 7. TDD test list (`src/backend/tests/test_wearables_garmin.py`)

Fixtures are built in a helper from a `LAYOUT` dict whose values come from §3. Until §3 is filled the helper raises, so tests cannot pass on guessed names.

| ID | Assertion | RED reason |
|---|---|---|
| HC-WRB-1101 | Synthetic export with the 3 metrics → records for each, all `garmin_device`/`garmin` | module missing |
| HC-WRB-1102 | Steps records returned per source row, not summed | parser absent |
| HC-WRB-1103 | Sleep interval keeps its own offset; two intervals with different offsets keep different `tzinfo` utcoffsets | absent |
| HC-WRB-1104 | (11a) FIT members (`.fit`) → `skipped["fit_not_supported"]==n`; an open-spy on `ZipFile.open` shows they were never opened. **11b changes this test** to: out-of-scope FIT members are never opened; only in-scope FIT members reach `garmin_fit.py` (Opus D1D8 A7) | absent |
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
| HC-WRB-1117 | valid synthetic Garmin export generated at the production default caps (members just under `max_json_member_bytes`): consuming the yielded records keeps `tracemalloc` peak < 256 MB (ceiling recorded at Task 0 from OM-2 sizes) | records collected into a list or `json.loads` on an uncapped member → peak over ceiling |
| HC-WRB-1118 | (11b) AST scan of `src/backend`: only `modules/wearables/garmin_fit.py` imports `garmin_fit_sdk` | second importer added |
| HC-WRB-1119 | (11b) Inside one context that patches `socket.socket`, `socket.create_connection`, `socket.getaddrinfo` and `subprocess.Popen` to raise, **import or `importlib.reload` `modules.wearables.garmin_fit`** (so import-time I/O is seen) and decode a synthetic FIT member to records without error (local-only; Opus D1D8 A8) | SDK call opens a socket, resolves a name or spawns a process |
| HC-WRB-1120 | (11b) FIT-derived records have exactly the WEAR-03 record keys, `device_class="garmin_device"`, and only in-scope metrics; a FIT member above the byte cap is refused before decode | shape mismatch / uncapped read |
| HC-WRB-1121 | (11b) Static scan of every `.py` file of the installed `garmin_fit_sdk` package (`importlib.metadata`/`importlib.util.find_spec` location) via `ast`: no import of `socket`, `urllib`, `http.client`, `requests` or `subprocess`; the test fails if any is found (do not allow-list: STOP and report to the owner; Opus D1D8 A8) | SDK reaches the network or a subprocess |
| HC-WRB-1122 | (11b) `src/backend/requirements.txt` has exactly one `garmin-fit-sdk` line and it matches `^garmin-fit-sdk==\d+(\.\d+)*$` (no range, no extras) | range or missing pin |

Covers research HC-WRB-001 (partly), 005, 006 for the Garmin path. Tests 1108/1109/1110/1111 are the key hostile set.

Counts (Opus D1D8 A7): **11a = 17 tests (1101-1117)**; **11b = 5 tests (1118-1122)**, with 1104 re-scoped.

## 8. Tasks

- [ ] **Task 0 (gate, STOP if any fails)**
  1. `git fetch origin && git merge-base --is-ancestor <WEAR-04 merge commit> origin/main`; same for WEAR-03, WEAR-05.
  2. Find the committed OM-2 notes: `git grep -n -i "OM-2" -- docs | grep -v "wearables-1[12]\|wearables-00\|research/2026-10-12\|reviews/"`. **If no OM-2 notes document (with §3 items answered) exists in the repo, STOP.** Report "OM-2 notes absent" to the orchestrator and write no code. `TASK_LIST.md:100` is a queue row, not notes.
  3. Confirm row WEAR-D5 is on `origin/main` (PR #92). 11a proceeds; 11b additionally needs row `WEAR-FIT-LIC` (OW-W7).
  4. Copy the OM-2 answers into §3's last column in this file (same PR). A FIT-only metric is not a stop: it is routed to 11b (§0), not into the JSON parser; 11a still proceeds for the JSON metrics. (Opus D1D8 A7)
  5. Read `modules/wearables/apple.py` and `aggregate.py`; align §6 shape. Record the real signatures here.
  6. Baseline: `cd src/backend && python -m pytest --collect-only -q | tail -1`; note the count.
- [ ] **Task 1 RED.** Write `test_wearables_garmin.py` with the `LAYOUT` helper. Run `cd src/backend && HF_HUB_OFFLINE=1 python -m pytest tests/test_wearables_garmin.py -p no:cacheprovider -q`. Expected: collection ImportError on `modules.wearables.garmin`. Paste it in the PR.
- [ ] **Task 2 GREEN, guards first.** ZIP guards (1106-1109), then JSON load with `parse_constant` that raises, size cap on bytes read, depth cap by catching `RecursionError` (1110-1112).
- [ ] **Task 3 GREEN, metrics.** One small function per metric reading paths from §3. FIT/out-of-scope counted by name only (1104, 1105).
- [ ] **Task 4 refactor.** Share guard code with `apple.py` only if the WEAR-04 L1 already extracted it.
- [ ] **Task 5 verify (11a).** Target file command above, then full suite: `cd src/backend && flock /tmp/claude-1000/hc-pytest.lock env HF_HUB_OFFLINE=1 python -m pytest -p no:cacheprovider -q`. Collected = start + 17 (11a). Update CLAUDE.md / AGENT.md count slots in the same commit (SLOT-RULE). `test_api_rag_index_002b` may fail for the embedding model; do not touch its 0.7 threshold.

### 11b task block (Opus D1D8 A7; runs only if OM-2 shows an in-scope metric only in FIT and `WEAR-FIT-LIC` allows it)

- [ ] **Task 11b-0 (gate, STOP if any fails).** (1) Row `WEAR-FIT-LIC` is on `origin/main` and says an open-source pip dependency on `garmin-fit-sdk` is acceptable (`git show origin/main:docs/capstone-report/owner-decisions-2026-09-27.md | grep -n "WEAR-FIT-LIC"`). (2) 11a and WEAR-12 are merged. (3) Choose the exact `==` version from PyPI, at least two weeks old. (4) From the wheel's `METADATA`/`WHEEL` files: it is pure-python (tag `py3-none-any`), `Requires-Python` covers 3.11 (the CI version), and `Requires-Dist` is empty (zero transitive dependencies). (5) Record the wheel's sha256 in the PR body; `requirements.txt` carries no hashes today, so the exact pin and this record are the supply-chain controls.
- [ ] **Task 11b-1 RED.** Write 1118-1122 and the re-scoped 1104. Run `cd src/backend && HF_HUB_OFFLINE=1 python -m pytest tests/test_wearables_garmin_fit.py tests/test_wearables_garmin.py -p no:cacheprovider -q`. Expected: ImportError on `modules.wearables.garmin_fit`; 1122 fails (no pin). Paste.
- [ ] **Task 11b-2 GREEN.** Add the `requirements.txt` line, install it, create `garmin_fit.py` (decode bytes already capped by `_zipguard.py`; no FIT field outside the 3 metrics; same record shape and `device_class="garmin_device"`), wire in-scope FIT members into `garmin.py`. Run 1118-1122 and 1101-1117; all green. If 1121 fails, STOP and report to the owner (do not allow-list).
- [ ] **Task 11b-3 verify CI.** Read `.github/workflows/ci.yml` and state what it runs: the dependency is installed by `pip install -r src/backend/requirements.txt` on Python 3.11 in the Backend Tests job (`:50-53`), the Security Scan job (`:119-120`, then `pip-audit --format=json --output=pip-audit-report.json` at `:133` and `scripts/security_gate.py` at `:153`, which fails on high/critical findings) and the Agent Eval Gate job (`:169-172`). Locally run `pip install -r src/backend/requirements.txt` in a 3.11 venv and `pip-audit` if installed; paste the output, or say `pip-audit` was not run locally and CI is the check.
- [ ] **Task 11b-4 full suite.** `cd src/backend && flock /tmp/claude-1000/hc-pytest.lock env HF_HUB_OFFLINE=1 python -m pytest -p no:cacheprovider -q`; collected = start + 5; update the count slots in the same commit. Show the exact `requirements.txt` line to the owner in the PR body.
- [ ] **Task 11b-5 rollback.** Revert the PR: remove the `requirements.txt` line, `garmin_fit.py`, its test file and the `garmin.py` routing; FIT members return to `fit_not_supported` (11a behaviour). Nothing else imports `garmin_fit_sdk` (1118).

## 9. Mutation / break checks (temporary, never committed; `git diff` guard after reverting)

1. Count ZIP size from `ZipInfo.file_size` instead of bytes read → HC-WRB-1108 must go red.
2. Remove `parse_constant` → HC-WRB-1111 red.
3. (11a) Make the loop open `.fit` members → HC-WRB-1104 red.
4. Use `datetime.astimezone()` with host tz → HC-WRB-1116 red.
5. (11b) Make `garmin_fit.py` call `socket.getaddrinfo` at import time → 1119 red (import-time visible). Import `garmin_fit_sdk` from a second module → 1118 red. Change the pin to `>=` → 1122 red.

## 10. Acceptance criteria

- Target file: 17 passed for 11a (1101-1117), command and output pasted; 11b adds 5 (HC-WRB-1118..1122).
- Full suite: collected count = start + 17 for 11a; start + 5 for 11b, output pasted; failures limited to the known embedding test, named.
- `git diff --stat` shows only the §4 files plus count slots.
- §3 last column filled from OM-2 in the same PR.

## 11. Rollback

Delete `garmin.py` and its test file; nothing imports them until WEAR-12. Revert the count slots. 11b rollback: see Task 11b-5 (remove the pin and `garmin_fit.py`).

## 12. What these tests cannot see

- Whether a real Garmin export matches the fixtures at all (fixtures come from OM-2 notes, one account, one date; recurring-failures #3 figures asserted not measured, #8 stale guidance read as authority).
- A fixture built from the same `LAYOUT` the parser reads proves consistency, not truth (#1 a green suite that could not have failed). The only real check is OW-W1-style dogfood with the owner's export.
- Garmin firmware or app changes that rename fields after OM-2.
- Speed on a multi-year export (OW-W2 style perf smoke; not run here).
- No test was run while drafting this plan.

## 13. Owner / model-machine items

- **OW-W3** (OM-2): blocks this plan. Note `docs/features/TASK_LIST.md:100` still bundles OM-2 with the dropped Samsung OM-3; WEAR-14 or the orchestrator should split it.
- **OW-W7** (new, owner): FIT licence read — read the FIT Protocol License (`https://github.com/garmin/fit-python-sdk/blob/main/LICENSE.txt`, research 01 §2) and answer: may this open-source project declare `garmin-fit-sdk` as a pip dependency and be distributed with it? Record the answer as owner-decisions row `WEAR-FIT-LIC`. Blocks 11b only.
- OM-7 / OD-8 wider legal read (FDA wording, FTC HBNR) stays open before public distribution.
