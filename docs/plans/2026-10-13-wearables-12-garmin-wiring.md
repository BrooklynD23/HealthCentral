# WEAR-12 — Garmin Wiring + Cross-Vendor Overlap — Implementation Plan

**Last Updated:** 2026-10-13
**Owner:** repository owner
**Status:** PROPOSED — not executed. Code waits for WEAR-11 merged, M4, OM-2 notes and D5.
**Base measured:** `origin/main` @ `8234990`. Product-code lines re-read on planning tree `a985390` (docs-only ahead) on 2026-10-13.
**Refresh trigger:** WEAR-06/07/08/09/11 merge (this plan edits what they create); OM-2 vendor marker filled; any edit to `api/wearables.py`.
**Program:** [`2026-10-13-wearables-00-program.md`](2026-10-13-wearables-00-program.md) (A5b cross-vendor line, wave WE).
**Depends on:** WEAR-06 (import route), WEAR-11 (`garmin.py`), and the read paths of WEAR-07/08/09. All PLANNED, none exist on this tree.
**Owner decisions it depends on:** D5 (a), and OM-2 for the Garmin marker. The overlap rule below is proposed here, not owner-signed: see Questions in the hand-back.
**Size target:** S, ~200 diff lines.

> For agentic workers: use superpowers:test-driven-development and superpowers:subagent-driven-development; domain skill `asclexis-backend`. RED first.

## 1. Scope

Does:
- Add pure `modules/wearables/detect.py`: `detect_vendor(names) -> "apple" | "garmin" | None | "ambiguous"` from ZIP member names.
- In `POST /wearables/imports`, after the temp file is written and hashed, open the ZIP, detect the vendor, dispatch to `apple.py` or `garmin.py`, set `source_vendor`. Unknown or ambiguous → 400.
- Define and implement the cross-vendor read rule (§5) in the one shared selection function, and update the WEAR-08 / WEAR-09 read-path tests.

Does NOT:
- No frontend change beyond flipping `GARMIN_EXPORT_READY` (WEAR-10). The upload control already takes a ZIP and its copy is vendor-neutral (WEAR-07b R2/R8, Codex plans N3); Garmin export instructions are WEAR-10 §Copy G1-G4, approved once under D8.
- No schema or migration change: `source_vendor` already allows `garmin` (WEAR-02 contract).
- No change to Apple parsing, to the size cap (D4), or to temp-file handling (D6).
- No summing across vendors, ever.

## 2. Evidence

| Fact | path:line |
|---|---|
| Cross-vendor: one vendor per metric per day, rule defined in WEAR-12 | `docs/plans/2026-10-13-wearables-00-program.md:44` (A5b) |
| Selection is at read time from the most recent REVIEWED import covering the day | `docs/plans/2026-10-13-wearables-00-program.md:44` |
| Dedicated route, not `documents/import` | `docs/plans/2026-10-13-wearables-00-program.md:39` (A1) |
| Garmin slice milestone and dependency | `docs/plans/2026-10-13-wearables-00-program.md:63` (M5), `:82` (WEAR-12 row) |
| Tests must go through `main.app` for mount, cap and flag behaviour | `docs/plans/2026-10-13-wearables-00-program.md:52` (A13) |
| `route_client` mounts a bare app | `src/backend/tests/support/routes.py:27` |
| Routers are mounted statically (WEAR-01 adds the wearables mounts here) | `src/backend/api/__init__.py:48-67` |
| Import-path size prefixes (D4 owner gate, not touched here) | `src/backend/security/input_validator.py:18`, `:70-71` |
| Audit string keys scrubber (WEAR-02 reserves `vendor`; absent today) | `src/backend/core/audit.py:69` |
| Aware → naive helper if a detection step ever stores aware values | `src/backend/core/time.py:24` |
| `modules/wearables/` and `api/wearables.py` do not exist yet | `ls src/backend/modules/wearables` → no such directory |
| Garmin layout/marker unknown until OM-2 | `docs/research/2026-10-12/01-vendor-matrix.md:78-81` |

## 3. OM-2 fill-in (carried from WEAR-11, copy its confirmed values)

| Item | Research guess + label | Confirmed value (OM-2) |
|---|---|---|
| Garmin marker: member name or folder present only in a Garmin export | none — U | |
| Apple marker: member `*/export.xml` | INFERRED `apple_health_export/export.xml` — S (OM-1 confirms) | |
| Can one ZIP contain both vendors? | assumed no — U | |

## 4. Files to touch

| Path | New/edit | Why | Lines |
|---|---|---|---|
| `src/backend/modules/wearables/detect.py` | new | pure vendor detection | ~35 |
| `src/backend/api/wearables.py` | edit | dispatch in the import handler | ~30 |
| `src/backend/modules/wearables/select.py` (or wherever WEAR-08 put the A5b selection) | edit | group key becomes `(metric, date)` | ~25 |
| `src/backend/tests/test_wearables_garmin_wiring.py` | new | tests below | ~200 |
| `src/backend/tests/test_wearables_trends.py`, `test_wearables_packet.py` | edit | add a Garmin+Apple case to existing read-path tests | ~40 |

## 5. Cross-vendor overlap rule (proposed)

For each `(metric, local_date)` there is exactly one current value:
1. Candidate rows are those in **reviewed** imports (review is per import per metric) of this profile that have a row for that metric and date. "Covers" means a row exists, not that the date lies inside the import's first/last range (a range would blank days the newer vendor lacks).
2. Winner = the candidate from the import with the latest `imported_at`; tie → larger `id`. The winner's vendor is the day's vendor.
3. Losers are never summed or averaged. The read result carries `other_vendor_days` (count of days where another vendor had a candidate) so the panel and packet can say "also recorded by another device on N days" in neutral words. Wording needs D8 copy approval.
4. The patient controls it: re-importing or un-reviewing changes the winner. Deleting an import (WEAR-07, explicit child deletes first) brings the older vendor back.
5. Inside one import the WEAR-05 device-class preference still applies. Across imports only rule 2 applies.

This is exactly A5b with the vendor removed from the grouping key. It never mixes vendors within one day.

## 6. Data contract

No new fields. `wearable_imports.source_vendor` in `{apple, garmin}`; `wearable_daily_metrics.device_class` includes `garmin_device`. Audit details for a Garmin import: `vendor="garmin"` plus count keys only (never filename, `source_name`, values). Error body for unknown vendor: `{"detail": "unrecognized_export"}`; ambiguous: `{"detail": "ambiguous_export"}`.

## 7. TDD test list (`src/backend/tests/test_wearables_garmin_wiring.py`)

HTTP tests use `route_client` for route behaviour and `TestClient(main.app)` for the mount/flag cases (A13, recurring-failures #10).

| ID | Assertion | RED reason |
|---|---|---|
| HC-WRB-1201 | `detect_vendor` on Apple names → `"apple"` | module missing |
| HC-WRB-1202 | On Garmin names (OM-2 marker) → `"garmin"` | module missing |
| HC-WRB-1203 | Neither → `None`; both markers → `"ambiguous"` | module missing |
| HC-WRB-1204 | POST a synthetic Garmin ZIP: 201, DB rows have `source_vendor=="garmin"`, `device_class=="garmin_device"` (assert row values) | route only knows Apple |
| HC-WRB-1205 | POST an unrecognised ZIP → 400 `unrecognized_export`, zero rows, temp file gone | no detection |
| HC-WRB-1206 | POST an ambiguous ZIP → 400 `ambiguous_export`, zero rows | no detection |
| HC-WRB-1207 | Apple import still works unchanged (characterization) | guards regressions |
| HC-WRB-1208 | Audit row for Garmin import: `vendor=="garmin"`, count keys present, filename / source_name / any value absent | `vendor` path unproven |
| HC-WRB-1209 | Apple (older) and Garmin (newer), both reviewed, same-day steps → read returns **one** value, Garmin's, not the sum | rule missing |
| HC-WRB-1210 | Same data, Apple imported later → Apple's value wins | rule missing |
| HC-WRB-1211 | Newer Garmin import **unreviewed** → older reviewed Apple value returned | rule missing |
| HC-WRB-1212 | Garmin reviewed for steps only; sleep for that day comes from Apple | per-metric review |
| HC-WRB-1213 | Days covered by only one vendor each both appear (no day lost) | range-vs-row bug guard |
| HC-WRB-1214 | Delete the newer Garmin import → Apple's value returns; assert zero child rows of the deleted import | cascade not enforced |
| HC-WRB-1215 | Profile B reads A's merged result: zero rows (assert returned values) | isolation |
| HC-WRB-1216 | `other_vendor_days` equals the number of overlapping days | field missing |
| HC-WRB-1217 | `POST /export/visit-prep` (confirm=true, include_wearables): one value per overlapping day, no vendor sum | 09 read path |
| HC-WRB-1218 | `GET /wearables/metrics` same overlap day: one value | 08 read path |
| HC-WRB-1219 | `TestClient(main.app)`: flag off, POST Garmin ZIP to `/api/v1/wearables/imports` → 404 | mount unseen by `route_client` |

Covers research HC-WRB-003 (cross-source dedup, extended across vendors) and 004 (changed per A5b: no upsert).

## 8. Tasks

- [ ] **Task 0 (gate, STOP if any fails)**
  1. Ancestry: `git merge-base --is-ancestor <WEAR-06>`, `<WEAR-07>`, `<WEAR-08>`, `<WEAR-09>`, `<WEAR-11> origin/main` for each.
  2. OM-2 notes exist and §3's Garmin marker is filled (same check as WEAR-11 Task 0). If absent STOP.
  3. Locate the A5b selection code: `git grep -n "imported_at" -- src/backend/modules/wearables src/backend/api/wearables.py`. Record the real file and function in §4. If selection is duplicated in 08 and 09, STOP and report; fix once, in one function.
  4. Confirm the owner accepted the §5 rule (question in hand-back). If rejected, STOP.
  5. Baseline collected count.
- [ ] **Task 1 RED.** Write the test file; run `cd src/backend && HF_HUB_OFFLINE=1 python -m pytest tests/test_wearables_garmin_wiring.py -p no:cacheprovider -q`. Expect ImportError (`detect`) then assertion failures. Paste.
- [ ] **Task 2 GREEN.** `detect.py`, then dispatch in the handler, then the selection key change. Update the two existing read-path test files.
- [ ] **Task 3 verify.** Target file, the 06/07/08/09 wearables test files, then full suite under `flock /tmp/claude-1000/hc-pytest.lock`. Collected = start + 19. Update CLAUDE.md / AGENT.md slots in the same commit.
- [ ] **Task 4 review.** security-reviewer pass on the handler diff (new input branch on a file upload).

## 9. Mutation / break checks (temporary, never committed; `git diff` guard)

1. Group selection by `(vendor, metric, date)` again → HC-WRB-1209 red (two values).
2. Drop the `reviewed` filter → HC-WRB-1211 red.
3. Use first/last date range instead of row existence → HC-WRB-1213 red.
4. Skip the explicit child delete → HC-WRB-1214 red.

## 10. Acceptance criteria

- Target file 19 passed plus the updated 08/09 files green, output pasted.
- Full suite collected = start + 19, output pasted; only the known embedding failure, named.
- Over real HTTP a Garmin ZIP and an Apple ZIP both import; an Apple+Garmin same-day case returns one value.
- `git diff --stat` limited to §4 files; `security/input_validator.py` untouched.

## 11. Rollback

Revert the PR. Garmin imports already stored keep valid rows (vendor enum allows them) but the detect step is gone, so new Garmin uploads return 400. Imports can be deleted through WEAR-07's DELETE.

## 12. What these tests cannot see

- Whether a real Garmin export carries the OM-2 marker; detection is only as good as the notes (#8, #3).
- Whether "latest reviewed import wins" matches what a patient expects when both devices were worn; it is a simple rule, not a quality judgement (#9 invariant at one site: the selection must live in one function, which Task 0 step 3 checks).
- The mount, flag and cap behaviour is covered only by the `main.app` test 1219; `route_client` alone would not see a missing mount (#10, #1).
- No test was run while drafting this plan.

## 13. Owner / model-machine items

- **OW-W3** (OM-2 marker), **OW-W5** (D5, plus sign-off of the §5 overlap rule).
- Garmin export instructions copy for WEAR-10 §Copy needs D8 approval (follow-up, not in this PR).
- Dogfood: owner imports a real Garmin export after merge (extends OW-W1; record counts only).
