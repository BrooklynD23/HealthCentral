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
- 2026-10-04: L1-C done. #40 P4-core @cd17e2b: 30 files = plan list (endpoints.md via Task 11 else-branch; correlations row matches `api/medications.py:452-461`, verified_only default True); docs_lint rc=0; index --check fresh; `.env.example` VECTOR_STORE_TYPE count 0; root `scripts/download_models.py` gone; CI 6/6. Docs-only: no break-it.
- SAFE-CHAT confirmed by L0 (`rag.py:836-838`, `assistant.py:869-901`, chat UI ignores is_valid); owner chose "Fix now, abstain"; queued to L1-A after DDI, before G-C3b.
- RCC-2 + NPM-MAJORS plans dispatched to L1-B.
- Merge plan now: #37 → (#38 refresh) → #39 → (#40 refresh) ; DDI / SAFE-CHAT / G-C3b / RCC-2 as they land. #37, #38, #40 all touch docs/INDEX.md: each later one refreshes.
- 2026-10-04: L1-A done (#41 DDI, #44 SAFE-CHAT, #45 G-C3b); L1-B round 2 done (#42 RCC-2 stacked on #37, #43 NPM-MAJORS plans). All CI 6/6. L0 verification (../hc-l0-verify, D9 venv, flock):
  - #41 @ce5b692: `-k HC_DDI` 4 passed; break-it delete `observation.py:114` cascade → 2 failed; collected 1350 = CLAUDE:30 = AGENT:76.
  - #44 @e188567: `test_safe_chat_prohibited.py` 5 passed; break-it `assistant.py:879` → `if False:` → 2 failed; collected 1351 = slots. Diff read: ESCALATE_TEMPLATE replaces segments + full_response, verification cleared, audit row details carry no text.
  - #45 @ba22622: correlation + audit middleware 15 passed; break-it delete `main.py:106` install call → 1 failed; collected 1350 = slots.
  - #42 @dd8edb6 (Windows): 4 files 18 passed; break-it delete first `gcTime: 0` (`profiles.ts:125`, useCreateProfile) → FE-RCC2-001/002 failed; restored.
  - #43 @22de642: plans only, both marked "not approved for execution"; no src change.
  - L1-A's permission layer blocked ticking S-C3-1/S-C3-3; L0 ticked them on docs/wave3-close from the owner's own chat answers (b7c3d42).
