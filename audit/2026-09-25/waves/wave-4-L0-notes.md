# Wave 4 — L0 notes

**Last Updated:** 2026-10-08
L0 log for Wave 4: dispatches, verifications, merges. Scaffold and reviews: [scaffold/README.md](scaffold/README.md), [scaffold/REVIEWS-2026-10-07.md](scaffold/REVIEWS-2026-10-07.md).

## Tracks (base `origin/main` `777adf5`, 1370 collected, vitest 195, Playwright chromium 31 listed)

| L1 | Kind | Phases, in order | Worktrees |
|---|---|---|---|
| A | code (backend) | PROHIBITED-PARAPHRASE measure-only (PARA-1-REDO; no `interpret_safety.py` edit) → P5 (TIME-03 in scope, P5-IMPORT) | `../hc-<id>` per phase |
| B | code (frontend, Windows npm) | NPM-AUDIT-2 → DEV-PS1-INSTALL; later, after those merge: React Router 7 → Tailwind 4 | `../hc-npm-audit-2`, `../hc-devps1` |
| C | docs (architectural) | W-10 with fold-ins (LOCAL-07, DOC-OVERCLAIM incl. `hipaa-controls.md:49,52`, CLAUDE-FAILURE-COUNT); Codex re-review of the amended plan + diff review | `../hc-w10` |

Not dispatched yet: AUDIT-ORDER + AUDIT-DENIALS plan (plan-only; starts when a slot frees), P4-deferred N8 + N10 (after W-10), React Router 7, Tailwind 4. G-C2 deferred by the owner (G-C2-DEFER).

## Merge order (serial; owner merges)

To be fixed as PRs open. Known overlaps: `CLAUDE.md` count slots (PARA test PR, P5) versus W-10's `CLAUDE.md` hunks; `docs/INDEX.md` in every PR that adds or edits a plan.

## Log
- 2026-10-08: owner merged the scaffold PR #50 → main `777adf5` (all 2026-10-07 owner rows on main: 6 of 6 spot-checked rows found by grep). Dispatched L1-A, L1-B, L1-C in one message (2 code L1s + 1 docs L1; flock for full suites; one L2 per L1). Each brief carries the Fable / Codex amendments and the stop conditions.
- 2026-10-08: L1-A Phase 1 done → PR #51 (PROHIBITED-PARAPHRASE measure-only) @`9a68f9c`. L0 in ../hc-l0-verify: MERGEABLE CLEAN; 12 files; 0 files under `src/backend/modules/` or `src/backend/api/`; `tests/test_prohibited_patterns_regression.py` 3 passed; collected 1373 = `CLAUDE.md:30,:35` = `AGENT.md:76`; index --check fresh; break-it: delete `interpret_safety.py:57` (the "should take|must take" pattern) → `test_hc_para_001` and `test_hc_para_003` FAILED (2 failed, 1 passed), restored, tree clean; `scripts/measure_prohibited_patterns.py --final --final2 --markdown` re-run by L0 reproduces the report's rows (current 68/191 and 71/174 held-out, 170/170 must-not-regress; plan_18 loses 77 of 170; revised_b 160/174 out-of-sample, loses 16, 2/171 false positives); CI 6/6. Result: no measured list meets the owner's three conditions (0 lost, ≥85 % held-out, 0 false positives). Handed to owner with the PARA-1 question (A one more round / B revised_b / C revised_min / D no edit).
- Progress seen in worktrees (no L1 report yet): #52 NPM-AUDIT-2 open; DEV-PS1-INSTALL 6 commits; P5 10 commits; W-10 9 commits, still in Codex plan-review rounds.
