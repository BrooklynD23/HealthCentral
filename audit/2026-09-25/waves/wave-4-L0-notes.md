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
