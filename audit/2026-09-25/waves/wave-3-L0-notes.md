# Wave 3 — L0 notes

**Last Updated:** 2026-10-04
**Base:** origin/main `90c502a` (Waves 0-2 merged, PR #36 merged).

## Gates answered (2026-10-04, chat; recorded in owner-decisions-2026-09-27.md)

S-C3-1 and S-C3-3 signed (S-C3-1 asked separately: the handoff missed it, W11b `:1543`); W3-SEC-SCHED (DOC-DELETE-INTERP, RECOVERY-CODE-CACHE); NPM-AUDIT-SCHED (plan now, run now; no `--force`); OG-4, OG-5, OG-6 approved.

## Dispatch (≤2 code L1s; full backend suites under flock)

| L1 | Kind | Phases (in order) | Worktrees |
|---|---|---|---|
| A: backend | code | DOC-DELETE-INTERP (new plan + Codex) → G-C3b | `../hc-ddi`, `../hc-gc3b` |
| B: frontend | code (Windows npm) | RECOVERY-CODE-CACHE (new plan) → NPM-AUDIT (new plan) → W-11a PR-4 | `../hc-rcc`, `../hc-npm`, `../hc-w11a-pr4` |
| C: docs | docs | P4-core | `../hc-p4` |

## Merge order (serial; owner merges)

1. DOC-DELETE-INTERP 2. RECOVERY-CODE-CACHE 3. NPM-AUDIT 4. G-C3b 5. W-11a PR-4 6. P4-core

## Log
- 2026-10-04: dispatched L1-A (DDI → G-C3b), L1-B (RCC → NPM → W-11a PR-4), L1-C (P4-core) on 90c502a. S-C3-1 signed after dispatch; L1-A told.
- 2026-10-04: L1-B done. L0 verification:
  - #37 RCC @7113db5: 6 files = plan; Windows `vitest run RecoveryCodeCard.test.tsx` 8 passed; break-it delete `profiles.ts:272` (gcTime) → FE-RECOV-007/008 FAILED, restored; CI 6/6.
  - #38 NPM @93def9e: package.json unchanged; Windows `npm audit` → 7 (2 moderate, 5 high); CI 6/6 incl. E2E.
  - #39 W-11a PR-4 @85f0948: inventory grep (path-anchored exclusions) → only ledger H2 quoting "155/25" as CONTRADICTED history; CI 6/6. H2 cell still says "1,245 backend collected" → close-out item.
  - #37 and #38 both regenerate docs/INDEX.md + _link_graph.json (L1-B said disjoint; wrong): second to merge needs merge-main + regen.
