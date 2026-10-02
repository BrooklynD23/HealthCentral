# Wave 2 — Report (L0 summary)

**Last Updated:** 2026-10-02
**Base:** origin/main `8064244` (Waves 0-1 merged) → **end** `f5d829b`.
**Detail:** the L1 reports [wave-2-L1-A.md](wave-2-L1-A.md) (S-1, P2), [wave-2-L1-B.md](wave-2-L1-B.md) (W-6), [wave-2-L1-C.md](wave-2-L1-C.md) (W-11a PR-2, W-5, W-1), [wave-2-L1-D.md](wave-2-L1-D.md) (P8, G-C4), and the L0 log [wave-2-L0-notes.md](wave-2-L0-notes.md). The L1 files show heads and counts from before each pre-merge refresh; this table is the merged state.

## Merged PRs (serial, in this order)

| # | Phase | PR | Merge commit | Collected after merge | L0 verification (in `../hc-l0-verify` at the PR head) |
|---|---|---|---|---|---|
| 1 | S-1 SQL-echo PHI leak | [#29](https://github.com/BrooklynD23/HealthCentral/pull/29) | `040cf8c` | 1300 (+4) | 4/4 HC-SQLECHO; break-it: remove `hide_parameters` → `test_hc_sqlecho_004` FAILED; CI 6/6 |
| 2 | W-6 external-runner hardening | [#32](https://github.com/BrooklynD23/HealthCentral/pull/32) | `2f0cb6f` | 1317 (+17) | 50 passed (hardening + redaction); break-it: strict forcing off → 3× HC-EXT-001 FAILED; CI 6/6 |
| 3 | W-11a PR-2 vault ciphertext test | [#33](https://github.com/BrooklynD23/HealthCentral/pull/33) | `ceb9d9e` | 1324 (+7) | 7 passed with `HC_REQUIRE_SQLCIPHER=1`; CI 6/6 |
| 4 | W-5 citation-marker prompt | [#34](https://github.com/BrooklynD23/HealthCentral/pull/34) | `d21c59d` | 1327 (+3) | 3/3 HC-CIT; break-it: old rule-2 line → 3 FAILED; eval gate rc=0 (L1); CI 6/6 |
| 5 | W-1 harness agents (incl. Task 9) | [#35](https://github.com/BrooklynD23/HealthCentral/pull/35) | `cbabed1` | 1335 (+8) | 8/8 HC-AGENTS; drift check 0; break-it: delete one agent → drift + 4 tests FAILED; CI 6/6 |
| 6 | P2 notification scheduler | [#31](https://github.com/BrooklynD23/HealthCentral/pull/31) | `cff3827` | 1346 (+11) | 11/11 HC-NSW; `core/auth.py` diff = D6 hooks + P2-INFLIGHT await only; break-it: drop drain wait → HC-NSW-010 "vault file recreated" FAILED; CI 6/6 |
| 7 | P8 gated-items decision packet | [#30](https://github.com/BrooklynD23/HealthCentral/pull/30) | `242f7a0` | 1346 (0) | 0 forbidden legal claims; D10 phrase ×2; 8 blank owner lines; docs gates 0; CI 6/6 |
| 8 | G-C4 packaging decision record | [#28](https://github.com/BrooklynD23/HealthCentral/pull/28) | `f5d829b` | 1346 (0) | merged by the owner without a refresh; L0 checked main afterwards: docs gates + index fresh, 1346 = slots |

**Main after Wave 2 (`f5d829b`):** `1346 tests collected` = `CLAUDE.md:30` = `AGENT.md:76`; docs_lint, generate_docs_index --check, feature_list_lint, repo_hygiene_check, harness_drift_check all rc=0.

## Owner gates used

Signed before the wave: SQL-ECHO (S1-A + S1-B), D6, D1 + D1-scope, OG-2, OG-3, D11, D12, W6-Q4, BG-REACH, D10, SLOT-RULE, D9-SRC, P1-DRIFT.
Signed during the wave (owner-decisions): W6-Q3 "Settings + chat page", W6-Q5 "As written", P2-INFLIGHT "Approve fix in P2", W6-STALE-WARN "Keep plan, register item".

## Owner actions still open from this wave

1. **W-1 Task 7 Steps 2-5:** an interactive `/agents` smoke in a fresh worktree (steps in [wave-2-L0-notes.md](wave-2-L0-notes.md) and PR #35 §5). It settles whether a "no write tool" agent can create files (→ OG-1 if it can).
2. **P8:** fill the 8 `Owner decision:` lines in `audit/2026-09-25/gated-items-decision-packet.md` (`:64, :117, :196, :330, :333, :336, :393, :407`), the ledger rows `:420-427`, and P8-B2-ORDER (plan P08 `:635`).
3. **G-C4:** fill S-C4-1…5 at `docs/plans/2026-10-01-packaging-decision.md:160-164` (S-C4-5 = EMB-REV).

## Incident

The host (12 GB RAM, 6 cores, WSL2) ran out of memory when 4 L1s and their implementers ran backend suites at once; every agent died mid-phase. Commits survived; no PR had opened. Resume rules that worked: every full suite under `flock /tmp/claude-1000/hc-pytest.lock`, one L2 per L1 at a time, at most 2 code L1s at once.

## New owner items

Registered in the program's "Program owner items" table: NPM-AUDIT (security), BG-WARN-STALE, DOC-OVERCLAIM, SCHED-STATUS-GLOBAL, SCHED-DRAIN-UNBOUNDED, TOAST-MED-NAMES, MIGRATION-ECHO, VAULT-SIDECAR, W1-SMOKE.
