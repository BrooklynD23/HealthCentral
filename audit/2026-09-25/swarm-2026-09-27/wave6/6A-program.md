# 6A-program — Wave 6 report

Done: all 6 tasks applied to `docs/capstone-report/implementation-program.md` and `owner-decisions-2026-09-27.md`. `python3 scripts/docs_lint.py` → "Docs lint passed." (rc 0). No gate signed. Nothing committed.

## Findings

| Finding | Result | Note / evidence |
|---|---|---|
| 3a §5.1 graph | applied | 3a §2 mermaid copied verbatim from `git show HEAD:…/3a-integration.md:162-245`; critical-path paragraph replaces `:69`. The old "audit order … kept" sentence is kept as-is |
| 3a §5.2 shared-file order (+ M-2) | applied | 24-item list; `docs/capstone-report/*` row-scoped, scorecard = orchestrator only |
| 3a §5.3 P0-B2, D9/D9-SRC, P1 acceptance | applied | D9 facts re-checked: `/usr/bin/python3.12` only; uv `cpython-3.11.16` present. P1 gains drift-check exit 0 (P1-DRIFT) and the "collected only" rule for plan 01 Task 4 |
| 3a §5.4 ground rule 8 (SLOT-RULE) | applied | marked owner-gated, unsigned |
| 3a §5.5 W-plans table | applied, +3 rows | 3a's table had no P8/W-9 row; I added P8 (from the P08 header), RTN (nightly spec) and SHOWCASE. Links to all **16** `docs/plans/2026-09-27-*.md`, not 15 (see gates) |
| 3a §5.5 row updates | applied | P3 → W-1; P8 = W-9; gap table gains a Plan column (G-B3 = W-6 + W-7); P0-D gets P0-D-MOOT; P4 drops `data-privacy.md` + `CLAUDE.md:62`; P7 gets P7-ROUTE; P6 gets the `test_care_tasks.py:809,825` literals (re-checked: both `== "012_pinboards"`) |
| Ledger :69/:195 routing + 3a m-10 | applied | `data-privacy.md` editors = W-10 and W-10b only. P4, G-A1/W-2 and P8 read only. P4 bullet `:195` → "Moved to W-10". G-A1 row notes that W-10 owns the wording. The ":200 break-glass" bullet is `main:200` = `A:217` "PHI redaction applied to API prompts…" (re-checked) |
| 3a §3.3 orphans | applied | new section "Program owner items": INTERP-UNVERIFIED, MSG-UNVERIFIED, AUD-INTERP (= AUD-06), C-LLM-2 remainder, RL-EXPORTS (= PRIV-10) |
| PRIV-10, GATE-14, TIME-03, KEY-08, AUD-06 | applied | all 5 are defined in 3b §3 (`3b-evidence.md:306-315`); none was invented. Evidence re-checked: `rl_exports` not ignored (rc 1), 0 `rl_export` refs in `api/profiles.py`; `evalgate.out` `rc=124 elapsed=409s`; `dev.ps1:471-500`, `:586-593`; 7 routes and 0 audit calls in `api/interpretations.py` |
| TIME-03 count | applied **with a correction** | 3b says "7 sites / 6 files"; `git grep 'datetime\.now(timezone\.utc)'` at main gives **7 sites / 5 files**. The alias `dt_timezone.utc` adds `api/gamification.py:148`, `modules/badge_evaluator.py:84`. Other aware constructions: `core/auth.py:207`, `api/medications.py:84`, `badge_evaluator.py:54` |
| 3b M9 / program `:132` P1 step 6 | applied | step now runs `timeout 600 … ; echo $?`; a timeout after "PASS" is logged as GATE-14, not as a pass |
| 3b M3 / program `:287` G-B6 | applied | verified at main `40f590e`: vitest 165 tests / 28 files (static count). Playwright chromium: 31 `test(` minus 3 inline `test.skip` = 28, in 5 files (`ui-full-verification` excluded by `playwright.config.ts` testIgnore). `TASK_LIST.md:794` "25 passed / 3 conditional skips". Windows run still UNMEASURED |
| 3b minor 12 / owner-decisions `:46` | applied | re-measured: 11 files, 91,578,415 bytes, `model.safetensors` 90,868,376 bytes |
| 3a B-1 | link kept | it resolves on `docs/p0b-plan-set`. The text says P0-B2 is **not** signed |
| 3a M-6 | applied | EMB-REV is named the canonical revision gate. W-8 `:1388` and W-11b `:1859` already cite it |
| Task 6: snapshot note | applied | P0-B "State (2026-09-28)": `docs/p0b-plan-set` @ `5d56557`, not pushed or merged, pending P0-B / P0-B2 sign-off; index not regenerated |

## Files changed (2)

- `docs/capstone-report/implementation-program.md` (+211 / −50)
- `docs/capstone-report/owner-decisions-2026-09-27.md` (+2 / −2: Last Updated and Consequence #4)

## Handoffs (not edited)

1. **6B, matrix TIME-01/TIME-03:** change "7 aware sites / 6 files" to 5 files, and add the aliased and other aware sites listed above.
2. **6B, contract `:137`, `:146` (C-SAFE-1/2 Verify):** fix the eval-gate wording that assumes the gate exits (3b M9). Matrix GATE-03 `:137` / GATE-06 `:140` counts (3b M3) also belong to 6B.
3. **6F, capstone README:** link `2026-09-27-senior-report-showcase-plan.md` if the README lists plans. The program now links it, so there is no DOC-011 orphan either way.
4. **6F, plan 06 banner:** add the `test_care_tasks.py:809,825` literals (M-5). The program row now says so.
5. **Orchestrator:** `generate_docs_index.py --check` is stale (`docs/INDEX.md`, `docs/_link_graph.json`). This is expected. Do not regenerate without owner consent.

## New owner gates surfaced

- **P0-B2 scope:** the snapshot holds **16** plan files, but 3a's P0-B2 text says 15. `senior-report-showcase-plan.md` was not in the Wave-3 audit, so the owner must include or exclude it explicitly. The program row says this.
- No other new IDs. The following are registered and unsigned: P0-B2, D9-SRC, P1-DRIFT, SLOT-RULE, W4-EXPEDITE, P7-ROUTE, CI-SEED, P0-D-MOOT, and the owner items above.

## docs_lint output (final run)

```
Docs lint passed.
rc=0
```

Before my edits: 7 × DOC-011 orphan (W02, W04, W07, W11a, W11b, nightly spec, senior-report), "Docs lint failed with 7 error(s)."

Next action: put P0-B2 (with the 16th-file choice), D9-SRC, P1-DRIFT and SLOT-RULE to the owner as one 4-question prompt.
