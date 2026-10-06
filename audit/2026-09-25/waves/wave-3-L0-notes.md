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
- 2026-10-04: #46 RCC-3 @57c3760 (stacked on #42): 6 files = plan; Windows `BackupRestoreFlow.test.tsx` 4 passed; break-it delete `backup.ts:181` gcTime → FE-RCC3-001 failed; restored; CI 6/6. Stack: #37 → #42 → #46.
- 2026-10-04: L1-A round 3 done. #48 SAFE-INTERP-GROUNDED @0ac0e48: 14 files = plan; `test_safe_interp_grounded.py` 11 passed; break-it `interpretations.py:542` → `if False:` → 2 failed; collected 1357 = slots; CI 6/6. #47 PROHIBITED-PARAPHRASE plan @58148d3: plan + INDEX only, "not approved for execution", interpret_safety.py untouched; CI 6/6.
- New owner items to register at close: AUDIT-ORDER (subsumes DDI-AUDIT-ORDER), AUDIT-DENIALS, SAFE-INTERP-EMBEDDED, RAG-RUNTIME-500, PARA-1 (sign-off on #47), AUTH-401-LOGOUT, REPROCESS-INTERP-ORPHAN, PANEL-INTERP-STALE, dev.ps1 install/dev-server items, AGENT-PASS-LINE, implementer Sonnet trailers on 145fe77 f2677e2 02c644a d68e92e (left as-is).
- Merge order (12 PRs): #37 → #41 → #44 → #48 → #42 → #46 → #38 → #45 → #39 → #47 → #43 → #40. Each after #37 refreshes against main.
- 2026-10-04: owner merged #37 → main 1674880. #41 conflicts only in docs/INDEX.md; refresh sent to L1-A.
- 2026-10-04: #41 refreshed → a39b43e (merge of 1674880); L0: MERGEABLE CLEAN, index --check fresh, HC_DDI 4 passed, CI 6/6. Handed to owner.
- 2026-10-04: owner merged #41 → main 421c441 (collected 1350). #44 conflicts: AGENT.md, CLAUDE.md, docs/INDEX.md; refresh sent to L1-A (expect 1355).
- 2026-10-04: #44 refreshed → e650582; L0: MERGEABLE CLEAN, slots 1350→1355 only, index fresh, SAFE-CHAT 5 passed, collected 1355, CI 6/6. Handed to owner.
- 2026-10-05: owner merged #44 → main 0bad019 (1355). #48 conflicts AGENT.md, CLAUDE.md, INDEX; refresh sent to L1-A (expect 1366).
- 2026-10-05: #48 refreshed → 6e18a72; L0: MERGEABLE CLEAN, CLAUDE/AGENT diff 3 lines (1366), rag.py no diff, index fresh, SAFE-INTERP+SAFE-CHAT 16 passed, collected 1366, CI 6/6. Handed to owner.
- 2026-10-05: owner merged #48 → main ee5721d (1366). Refresh of #42 sent to L1-B (conflict: INDEX only). #46, #38 also conflict on INDEX (+_link_graph for #38).
- 2026-10-05: #42 refreshed → 0d4fe42; L0: MERGEABLE CLEAN, 11 files, index fresh, Windows RCC/RCC2 4 files 18 passed, CI 6/6. Handed to owner.
- 2026-10-05: owner merged #42 → main f2dd8f3. Refresh of #46 sent to L1-B.
- 2026-10-05: #46 refreshed → 3710ccf (parents 57c3760 + f2dd8f3); classifier timed out during the refresh, so L0 also diffed source vs the verified 57c3760: 0 lines; 6 files; index fresh; Windows BackupRestoreFlow 4 passed; CI 6/6. Handed to owner.
- 2026-10-05: owner merged #46 → main c11c917 (1366 backend, 195 vitest). Session ended (weekly usage). Delivery Map republished (v4).
- 2026-10-06: new L0 session. State re-checked: main c11c917, docs/wave3-close 29c7f7f, 6 PRs open. #38 refreshed by a refresh agent → 92e96ca (parents 93def9e + c11c917; conflicts INDEX + _link_graph only, both regenerated by script). L0 in ../hc-l0-verify: MERGEABLE CLEAN; 4 files = plan; source diff vs verified 93def9e (package-lock, package.json, plan) 0 lines; CLAUDE/AGENT vs main 0 lines (1366 unchanged); index --check fresh; docs_lint rc=0; Windows `npm ci` + `vitest run RecoveryCodeCard.test.tsx` 8 passed (agent: full vitest 195 passed); CI 6/6. Lockfile PR: no break-it. Handed to owner.
  - **NPM-AUDIT-DRIFT (new, measured by L0 and the agent):** Windows `npm audit` at 92e96ca → 10 (4 moderate, 6 high), was 7 (2 moderate, 5 high) on the byte-identical lockfile on 2026-10-04. Cause inferred, not measured: advisories published since. Agent's `npm audit --json`: fast-glob, source-map-js (GHSA-68fv-2mgg-jv7q), postcss-nested are fixable by non-breaking `npm audit fix`; the rest need Tailwind 4 / react-router 7 (NPM-MAJORS). The plan doc in #38 still says 7. Owner decides: follow-up NPM-AUDIT-2 phase, or leave to NPM-MAJORS. CI does not gate on `npm audit`.
- 2026-10-06: owner merged #38 → main c4d407e (1366 backend, 195 vitest). Refresh of #45 sent to a refresh agent (conflicts expected: CLAUDE.md, AGENT.md count lines; expect 1370).
- 2026-10-06: #45 refreshed → a99558c (parents ba22622 + c4d407e; conflicts CLAUDE.md + AGENT.md only, main's text taken, slots → measured 1370). L0 in ../hc-l0-verify: MERGEABLE CLEAN; 9 files = plan; product + test files vs verified ba22622 0 lines; slots `CLAUDE.md:30,:35` + `AGENT.md:76` = 1370, nothing else differs from main; collected 1370; correlation + audit middleware 15 passed; break-it delete `main.py:106` (`install_correlation_logging()`) → `test_hc_obsv_004` FAILED (1 failed, 14 passed), restored, tree clean; index --check fresh; CI 6/6. Agent's full suite under flock: 1370 passed, 0 failed (`test_api_rag_index_002b` passed: this box has an embedding model). Handed to owner.
