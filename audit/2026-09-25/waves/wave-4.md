# Wave 4 — Report (L0 summary)

**Last Updated:** 2026-10-09
**Base:** origin/main `777adf5` (Wave 3 + scaffold PR #50 merged) → **end** `eb7de28`.
**Detail:** the L1 reports [wave-4-L1-A.md](wave-4-L1-A.md) (PROHIBITED-PARAPHRASE measure-only, P5), [wave-4-L1-B.md](wave-4-L1-B.md) (NPM-AUDIT-2, DEV-PS1-INSTALL), [wave-4-L1-C.md](wave-4-L1-C.md) (W-10), [wave-4-L1-D.md](wave-4-L1-D.md) (React Router 7), and the L0 log [wave-4-L0-notes.md](wave-4-L0-notes.md). The L1 files show heads and counts from before each pre-merge refresh; this table is the merged state.

## Merged PRs (serial, in this order)

| # | Phase | PR | Merged head | Main after | Collected after merge | L0 verification (in `../hc-l0-verify` at the merged head) |
|---|---|---|---|---|---|---|
| 1 | PROHIBITED-PARAPHRASE measure-only | [#51](https://github.com/BrooklynD23/HealthCentral/pull/51) | `3d0d663` | `6e73fea` | 1374 (+4) | 0 files under `modules/` or `api/`; `test_prohibited_patterns_regression.py` 4 passed; measurement rows reproduced (live 215/215 must-not-regress; plan_18 108/215; revised_b 170/215); break-it: delete `interpret_safety.py:57` → 2 FAILED, restored; CI 6/6 |
| 2 | W-10 governance + 3 fold-ins | [#53](https://github.com/BrooklynD23/HealthCentral/pull/53) | `cf05786` | `6c13045` | 1374 (0) | refresh by Devin: PR +/- lines identical to `86de589` (0-line diff); L0 read the 4 `CLAUDE.md` sentences (`:25`, `:50`, `:60`, `:62`) and `hipaa-controls.md:49,:52`; `:169` unchanged; `--collect-only` 1374 = slots; index fresh; CI 6/6 |
| 3 | P5 utcnow migration + TIME-03 | [#54](https://github.com/BrooklynD23/HealthCentral/pull/54) | `b2743ac` | `98bd3c7` | 1381 (+7) | `api/profiles.py` 7 lines exactly; 0 changes to `core/auth.py`, `core/security.py`, `core/token_revocation.py`; `time_source_lint` passed (174 files); break-it: `models/audit.py:63` → `datetime.utcnow` → lint reports `audit.py:63`, restored; HC-TIME 7 passed; `--collect-only` 1381 = slots; CI 6/6 |
| 4 | NPM-AUDIT-2 | [#52](https://github.com/BrooklynD23/HealthCentral/pull/52) | `4c82d6b` | `f428a99` | 1381 (0) | 3 files; lockfile diff = `source-map-js` 1.2.1 → 1.2.2 only; `package.json` unchanged; PR +/- identical to `7281faa`; CI 6/6. Not re-run by L0: any npm command (agent, Windows: `npm audit` 9) |
| 5 | DEV-PS1-INSTALL | [#55](https://github.com/BrooklynD23/HealthCentral/pull/55) | `e980e4a` | `87accae` | 1381 (0) | Windows `check_dev_ps1_install.ps1` → `checks: 22/22`; break-it: `dev.ps1:642` `-ne` → `-eq` → `checks: 14/22`, restored → 22/22; `dev.ps1` identical to `52b2c39`; CI 6/6. Not tested: a full `dev.ps1` launch, PowerShell 7 |
| 6 | React Router 7 | [#57](https://github.com/BrooklynD23/HealthCentral/pull/57) | `af14128` | `eb7de28` | 1381 (0; vitest 197) | 12 files, 0 under `src/backend`; `package.json` one line `^6.21.0` → `^7.18.4`; L0's nested lockfile diff: added `cookie`, `set-cookie-parser`, removed `@remix-run/router`, majors only `react-router` / `react-router-dom` (MAJORS-TIED); `e2e/routing.spec.ts` E2E-ROUTE-001/002; CI 6/6 incl. E2E Smoke. Merged without a refresh after #55 (CI green at its head). Not re-run by L0: npm, vitest, the Playwright break-it |

**Main after Wave 4 (`eb7de28`):** `1381 tests collected` = `CLAUDE.md:30`, `:35` = `AGENT.md:76` (L0 collect-only at the #54 head; #52, #55 and #57 change no backend file). Not re-run on `eb7de28` itself. Frontend (L1-D, Windows, at the #57 head): vitest 197 in 35 files; Playwright chromium 33 listed (all projects 38). `npm audit` 7 (2 moderate, 5 high).

## Compliance matrix after Wave 4

Counted by `audit/2026-09-25/swarm-2026-09-27/wave3/scorecard_count.py` (it reproduces the 2026-10-07 count on the matrix before this edit: 78 rows, 3/31/5/16/16/4/2/1): **78 rows** = 3 enforced · 32 tested · 6 implemented · 18 partial · 15 gap · 1 contradicted · 2 owner-gated · 1 unknown.

- LOCAL-07 contradicted → implemented, SAFE-08 partial → tested, AUD-05 contradicted → partial (#53).
- TIME-01 gap → partial, TIME-03 contradicted → partial (#54): the deprecated helpers are gone and linted in CI; 8 `datetime.now(…utc)` calls and 3 aware conversions remain, the auth ones ask-first.
- SAFE-05 stays partial (#51 measured, did not edit). GATE-15 stays gap: 7 advisories, no CI step.

## Owner gates used

Signed 2026-10-07 (owner-decisions): PARA-1-REDO, P5-SCOPE, P5-IMPORT, W-10-REST, W10-Q4 / W10-Q5, W10-HIPAA, GOV-BG / GOV-D11, NPM-MAJORS-RUN, FE-SEQ, MAJORS-TIED, DEV-PS1-FIRST. Answered during the wave (2026-10-08/09, all rows on `docs/wave4-close` until this PR merges): PARA-1-R2, PARA-R2-BOUND, AO-BRIEF4, W10-HIPAA-52, C2-CLOSURE, OQ-1, O-2, EMB-REV, Q-OFFLINE, PARA-1-R3, BG-WARN-INTERP, RESET-AUDIT-OWNER, RR7-Q1, RR7-Q2, RR7-Q4, AO-DESIGN, AO-FAIL, AO-SCOPE, AD-DENIALS, RR7-Q3, AGENT-PASS-LINE, PONYTAIL-CLEANUP, NEXT-CODE-L1.

## Not merged

- **#56** AUDIT-ORDER + AUDIT-DENIALS plan (plan only), head `f141edd`; Codex ×2 and a security review applied; conflicts with main on `docs/INDEX.md` and `docs/_link_graph.json` only. AO-ASKFIRST and approval for execution are unasked.
- Branch `test/para-round2-measure` @`7991d96` (`union_r2`, 35 patterns): evidence only. On the only set written after the freeze it caught 111/180 (61.7 %) and blocked 23/200 safe sentences; the owner chose "Stop using patterns" (PARA-1-R3).

## Owner actions still open from this wave

1. **AUDIT-ORDER:** AO-ASKFIRST (`core/audit.py` helper, `core/auth.py:278-286`) and approval of plan #56 for execution.
2. **W-4 (next code L1 after BG-WARN-INTERP, NEXT-CODE-L1):** OQ-2 / OQ-5 / CI-SEED; plan amendment first (SAFE-CHAT branch at `api/assistant.py:879-892`).
3. **W-2:** S-3/O-3, P0-D-MOOT, EXPORT-QUESTIONS.
4. Separate small PRs the owner has decided: C2-CLOSURE, AGENT-PASS-LINE, ENGINES-NODE (RR7-Q3), SETTINGS-NAV-URL (RR7-Q4), PONYTAIL-CLEANUP, BG-WARN-INTERP.
5. Carried: W1-SMOKE, the P8 `Owner decision:` lines, S-C4-1…5, G-C2 S-C2-1…3.

## Incidents

- **Devin MCP disconnected** mid-wave (2026-10-09, connect timeout) after doing the #53 refresh and PARA round-2 phase 1; later delegations fell back to Claude agents. One Devin session (AUDIT-ORDER plan, 2026-10-08) never pushed; the plan was redone by a Claude agent.
- **#51 moved after L0's first check** (`9a68f9c` → `3d0d663`): L0 had told the owner `revised_b` loses 16 live catches; at the final head it loses 45 of 215. L0 corrected the figure before the owner decided.
- **wave-4-L1-B.md add/add merge** in the #55 refresh interleaved the two phase sections; tidied in this close PR from the two branch copies.
- **Lost scratchpad:** the blind fourth PARA held-out set (sha256 `7e0830c0…`) and the ponytail audit report lived in the old session scratchpad and are gone; their numbers are in the L0 notes and the program row PONYTAIL-CLEANUP.

## New owner items

Registered in the program's "Program owner items" table: UNAUDITED-WRITES, AUTH-EVENT-UNCALLED, AUDIT-MW-DOCSTRING, SQLCIPHER-CHECK-CI, FE-BKUP-001-FLAKY, SETTINGS-NAV-URL, BG-WARN-INTERP, DOC-OVERCLAIM-2, DEV-PS1-ITEMS, ACHIEVEMENTS-LOCAL-TIME, TIME-LINT-ALIAS, FEEDBACK-AUDIT-FAILOPEN, ENGINES-NODE, PONYTAIL-CLEANUP. Closed: AUD-INTERP (#48, stale since Wave 3), TIME-03 (#54), LOCAL-07 and CLAUDE-FAILURE-COUNT (#53), NPM-AUDIT-DRIFT (#52, #57), DEV-PS1-INSTALL (#55); DOC-OVERCLAIM partly (#53). PARA-1 superseded by PARA-1-R3.

Recurring failures: §1 gained the #55 stubbed-`npm` instance and the two React Router 7 checks that could not fail.
