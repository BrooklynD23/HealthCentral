# Wave 3 — L0 notes

**Last Updated:** 2026-10-04
**Base:** origin/main `90c502a` (Waves 0-2 merged, PR #36 merged).

## Gates answered (2026-10-04, chat; recorded in owner-decisions-2026-09-27.md)

S-C3-3 signed; W3-SEC-SCHED (DOC-DELETE-INTERP, RECOVERY-CODE-CACHE); NPM-AUDIT-SCHED (plan now, run now; no `--force`); OG-4, OG-5, OG-6 approved.

## Dispatch (≤2 code L1s; full backend suites under flock)

| L1 | Kind | Phases (in order) | Worktrees |
|---|---|---|---|
| A: backend | code | DOC-DELETE-INTERP (new plan + Codex) → G-C3b | `../hc-ddi`, `../hc-gc3b` |
| B: frontend | code (Windows npm) | RECOVERY-CODE-CACHE (new plan) → NPM-AUDIT (new plan) → W-11a PR-4 | `../hc-rcc`, `../hc-npm`, `../hc-w11a-pr4` |
| C: docs | docs | P4-core | `../hc-p4` |

## Merge order (serial; owner merges)

1. DOC-DELETE-INTERP 2. RECOVERY-CODE-CACHE 3. NPM-AUDIT 4. G-C3b 5. W-11a PR-4 6. P4-core

## Log
