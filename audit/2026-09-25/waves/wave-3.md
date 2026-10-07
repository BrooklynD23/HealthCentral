# Wave 3 — Report (L0 summary)

**Last Updated:** 2026-10-07
**Base:** origin/main `90c502a` (Waves 0-2 merged) → **end** `6b4dd84`.
**Detail:** the L1 reports [wave-3-L1-A.md](wave-3-L1-A.md) (DOC-DELETE-INTERP, SAFE-CHAT, G-C3b, SAFE-INTERP-GROUNDED, PROHIBITED-PARAPHRASE plan), [wave-3-L1-B.md](wave-3-L1-B.md) (RCC, NPM-AUDIT, W-11a PR-4, RCC-2, NPM-MAJORS plans, RCC-3), [wave-3-L1-C.md](wave-3-L1-C.md) (P4-core), and the L0 log [wave-3-L0-notes.md](wave-3-L0-notes.md). The L1 files show heads and counts from before each pre-merge refresh; this table is the merged state.

## Merged PRs (serial, in this order)

| # | Phase | PR | Merge commit | Collected after merge | L0 verification (in `../hc-l0-verify` at the PR head) |
|---|---|---|---|---|---|
| 1 | RCC recovery-code mutation cache | [#37](https://github.com/BrooklynD23/HealthCentral/pull/37) | `1674880` | 1346 (0; vitest +2) | Windows `RecoveryCodeCard.test.tsx` 8 passed; break-it: delete `profiles.ts:272` (`gcTime`) → FE-RECOV-007/008 FAILED; CI 6/6 |
| 2 | DOC-DELETE-INTERP | [#41](https://github.com/BrooklynD23/HealthCentral/pull/41) | `421c441` | 1350 (+4) | `-k HC_DDI` 4 passed; break-it: delete the `observation.py:114` cascade → 2 FAILED; CI 6/6 |
| 3 | SAFE-CHAT legacy chat escalation | [#44](https://github.com/BrooklynD23/HealthCentral/pull/44) | `0bad019` | 1355 (+5) | `test_safe_chat_prohibited.py` 5 passed; break-it: `assistant.py:879` → `if False:` → 2 FAILED; CI 6/6 |
| 4 | SAFE-INTERP-GROUNDED + interpretation audit rows | [#48](https://github.com/BrooklynD23/HealthCentral/pull/48) | `ee5721d` | 1366 (+11) | `test_safe_interp_grounded.py` 11 passed; break-it: `interpretations.py:542` → `if False:` → 2 FAILED; CI 6/6 |
| 5 | RCC-2 create / recover / delete profile | [#42](https://github.com/BrooklynD23/HealthCentral/pull/42) | `f2dd8f3` | 1366 (0) | Windows, 4 files 18 passed; break-it: delete `profiles.ts:125` (`gcTime: 0`) → FE-RCC2-001/002 FAILED; CI 6/6 |
| 6 | RCC-3 restore backup | [#46](https://github.com/BrooklynD23/HealthCentral/pull/46) | `c11c917` | 1366 (0; vitest 195) | Windows `BackupRestoreFlow.test.tsx` 4 passed; break-it: delete `backup.ts:181` (`gcTime`) → FE-RCC3-001 FAILED; source diff vs verified head 0 lines; CI 6/6 |
| 7 | NPM-AUDIT (lockfile only) | [#38](https://github.com/BrooklynD23/HealthCentral/pull/38) | `c4d407e` | 1366 (0) | lockfile vs verified head 0 lines; Windows `npm ci` + vitest (195 passed, refresh agent); `npm audit` 10 on 2026-10-06 (was 7 on 2026-10-04: NPM-AUDIT-DRIFT); CI 6/6 |
| 8 | G-C3b HC-M07 observability baseline | [#45](https://github.com/BrooklynD23/HealthCentral/pull/45) | `29c11e8` | 1370 (+4) | correlation + audit middleware 15 passed; break-it: delete `main.py:106` (`install_correlation_logging()`) → `test_hc_obsv_004` FAILED; full suite 1370 passed (refresh agent); CI 6/6 |
| 9 | W-11a PR-4 frontend counts (G-B6) | [#39](https://github.com/BrooklynD23/HealthCentral/pull/39) | `25c993e` | 1370 (0) | 5 files = plan; inventory grep leaves only dated history; docs gates 0; CI 6/6 |
| 10 | PROHIBITED-PARAPHRASE plan (**not approved for execution**) | [#47](https://github.com/BrooklynD23/HealthCentral/pull/47) | `930c678` | 1370 (0) | plan + INDEX only; `interpret_safety.py` untouched; 0 ticked boxes; CI 6/6 after the billing block cleared |
| 11 | NPM-MAJORS plans (**not approved for execution**) | [#43](https://github.com/BrooklynD23/HealthCentral/pull/43) | `22491e2` | 1370 (0) | 2 plans + generated files only; 0 ticked boxes; CI 6/6 |
| 12 | P4-core doc-drift sweep | [#40](https://github.com/BrooklynD23/HealthCentral/pull/40) | `6b4dd84` | 1370 (0) | 30 files = plan; `TASK_LIST.md` conflict resolved by keeping both sections; `.env.example` `VECTOR_STORE_TYPE` 0; root `download_models.py` gone; full suite 1370 passed (refresh agent); CI 6/6 |

**Main after Wave 3 (`6b4dd84`):** `1370 tests collected` = `CLAUDE.md:30` = `AGENT.md:76` (L0 collect-only at the #40 head; the merge commit adds nothing). Post-merge gate output is in the L0 notes (2026-10-07 entry).

## Owner gates used

Signed 2026-10-04 (owner-decisions): S-C3-1, S-C3-3, W3-SEC-SCHED, NPM-AUDIT-SCHED, NPM-AMEND-1, RCC-2, RCC-3, SAFE-CHAT ("Fix now, abstain") + SAFE-CHAT-TPL (ESCALATE_TEMPLATE), SAFE-INTERP-GROUNDED, OG-4 / OG-5 / OG-6 (P4), NPM-MAJORS ("Plan now"), PROHIBITED-PARAPHRASE ("Plan now, edit later"), AUTH-401-LOGOUT ("Register, later").

## Owner actions still open from this wave

1. **PARA-1:** sign or decline the PROHIBITED-PARAPHRASE plan (ask-first `modules/interpret_safety.py`); it needs a held-out corpus and a recall floor.
2. **NPM-MAJORS:** approve or defer the Tailwind 4 and react-router 7 plans; decide NPM-AUDIT-DRIFT (3 non-breaking fixes now, or with the majors).
3. **AUDIT-ORDER / AUDIT-DENIALS:** decide the design (audit row committed after the profile commit; denials not audited).
4. **P4-deferred:** N8 and N10 triggers are hit (W-5 and W-6 merged); each runs as its own PR. N9 still needs P8-B2-ORDER.
5. Carried from Wave 2, still open: W1-SMOKE, the 8 P8 `Owner decision:` lines, S-C4-1…5.

## Incidents

- **CI billing block (2026-10-06):** GitHub Actions refused to start jobs ("recent account payments have failed or your spending limit needs to be increased") for the #47 run and two main runs. The owner made the repository public; the reruns passed 6/6.
- **E2E failure on main `29c11e8` (run 37453242129):** 9 of 31 E2E tests failed after one `disk I/O error` on an audit commit left the e2e backend's database malformed for the rest of the process. The same tree passed E2E in two PR runs, and main `25c993e` passed on rerun. Cause UNMEASURED; registered as E2E-MASTER-CORRUPT.
- **Classifier timeout during the #46 refresh (2026-10-05):** L0 diffed the source against the last verified head (0 lines) before handing over.

## New owner items

Registered in the program's "Program owner items" table: AUDIT-ORDER (subsumes DDI-AUDIT-ORDER), AUDIT-DENIALS, AUTH-401-LOGOUT, PARA-1, NPM-MAJORS, NPM-AUDIT-DRIFT, SAFE-INTERP-EMBEDDED, RAG-RUNTIME-500, REPROCESS-INTERP-ORPHAN, PANEL-INTERP-STALE, SAFE-CHAT-AGENT / -FALLBACK / -HISTORY, DDI-ORPHAN-BIN, CORRELATION-NORMALISE, DEV-PS1-INSTALL, DEV-SERVER-RUNTIME, E2E-MASTER-CORRUPT. Closed: DOC-DELETE-INTERP (#41), RECOVERY-CODE-CACHE (#37, #42, #46), NPM-AUDIT (#38).

Not registered as rows (LOW, in [wave-3-L1-B.md](wave-3-L1-B.md)): `useLogin` / `useUnlockProfile` lack the RCC pattern (0 callers); the access token persists in `localStorage`; `SettingsPage.tsx` navigates to a server-supplied path after a `startsWith('/')` check only; `engines.node >=22` is below vite 7's `>=22.12`.
