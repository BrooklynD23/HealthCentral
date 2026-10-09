# 6E-W11-P-S-RTN — Wave 6 report (2026-09-28)

Done: 3 Codex rounds closed (W11a r4, S01 r3, RTN r1), 6 plans edited, `python3 scripts/docs_lint.py` → `Docs lint passed.` Nothing committed (rule 7).

## 1. Findings → disposition

### Codex rounds

| Finding | Plan | Disposition |
|---|---|---|
| W11a r4 BLOCKER (Task 3 runs before OG-2) | W-11a | applied. Verified G-B2 "encryption: ask first" (`implementation-program.md:283`). OG-2 now gates every Task 3 step (8 lines: PR table, license list, files, deps, Task 3 head/bullets, Step 6, stop gate 4, §11 OG-2) |
| W11a r4 MAJOR (PR-3 docs commit omits ci-and-quality-gates.md + index) | W-11a | applied. Task 10 Step 3 builds `PATHS` per PR plus the conditional files from `git diff --name-only`, then diff-checks the staged list, commits `-- $PATHS` and requires an empty `git status --short` |
| W11a r4 MAJOR (PR-4 omits regenerated index files) | W-11a | applied. Same `PATHS` pattern in Task 11 Step 4 |
| S01 r3 | S-1 | PASS, no findings. `S01-r3-response.md` records that |
| RTN r1 BLOCKER (Bash means read-only is not enforced) | nightly spec | applied in substance. Codex's evidence (`main.py:150`) is irrelevant, but the risk is real. Added: the routine is created disabled; a dry-run push plus `gh auth status` probe runs first; new owner Q6 if the session can push; an in-run C9 check that the checkout is untouched; a wider morning audit; disable on any write |
| RTN r1 MAJOR C6 (`/api/v1`) | nightly spec | applied. Verified `main.py:150,153,155` and `api/__init__.py:39-58` @main = @B. Defined how prefixes compose |
| RTN r1 MAJOR C7 (only zero claims flagged) | nightly spec | applied. Compares every stated number. Only numbers tied to an explicit date or sha count as DATED |
| RTN r1 MAJOR C8 (cwd / package.json) | nightly spec | applied. Added the cd-context rules. Verified `AGENT.md:57-61` @main and that `src/backend/scripts/download_models.py` exists |

### 3a / 3b / ledger

| Finding | Plan | Disposition |
|---|---|---|
| 3a B-3 | W-11a :181; P04 ci-gates row | applied. Both now read P4 N6 → W-11a Task 9 → W-8 (`:58`) (→ F4). W-8 :170 already agrees |
| 3a M-12 (D9) | W-11a D9 row, stop gate 2 | applied. `uv python list --only-installed` re-measured: cpython-3.11.16 is at the stated path and reports `Python 3.11.16`. The plan references gate D9-SRC, which is unsigned |
| 3a m-2 / m-3 / m-4 | W-11b shared-file table | applied. m-2: W-4 and W-7 do not add or commit `main.py`. m-3: W-1 `:671` only reads the file; P08 `:84` forbids editing it. m-4: plan 05 `:338` only runs the test, and `test_fhir_export.py` already uses `core.time.utcnow` |
| 3a m-9 | W-11a :184, Task 10, Task 11 | applied. Notes now go at the top of Session Notes, newest first. On main the top entry is 2026-07-30; three older notes at the file's end were appended out of order |
| 3a m-10 | P08 :82, :122 | applied. `data-privacy.md` editors are W-10 and W-10b. P04 :173 and W-02 :264 confirm this |
| 3a m-11 | P04 config/.env.example row | applied. S-1 is now in the order, with +4/+5 anchors |
| 3a m-12 | nightly spec header | applied. The header says the spec is in P0-B2 scope; the program link belongs to the orchestrator |
| 3a m-13 | P04 §14 finding 11 | applied. Marked superseded: W-10 `:30`/`:1185` already say "does not go to P4" |
| 3a §3.2 IDs | P08 S-2/S-3/R11, S01 S1-A/B, P04 OG-2/N9, W-11a OG-3, W-11b S-C4-5 | applied. P8-B2-ORDER, SQL-ECHO, EXPORT-QUESTIONS, D4-EXPORTS, CI-SEED and EMB-REV added beside the existing questions. The S01 Task 0 signature grep still matches |
| 3a B-4 (stale-slot STOP) | S01 :279, P08 :238 | partly applied: the STOPs stay and now cite SLOT-RULE. The rule itself is the program's (6A) |
| 3b minor 6 | W-11b :325, :1841 | applied. W-8 `:17-22` changed to `:34`, `:103` (re-checked after 6D's edits) |
| 3b minor 7 | W-11a Task 11; W-11b C3b.3 | applied. Both plans now cross-reference the +1 Playwright count (28→29 main, 30→31 A+B) |
| 3b minor 8 | P04 header | applied. `**Size:**` line: 25 headings / 33 units, with the measuring command |
| 3b minor 10 | S01 :110 | applied. Labelled "selector check only — never a baseline" |
| 3b M9 / GATE-14 | W-11a UNMEASURED table | applied as a **flagged, unowned item plus an optional read-only Linux measurement**, not a task. Why: the hang is measured only on Win Py 3.13 (`evalgate.out`: PASS, then `rc=124`), the cause is undiagnosed, and the script is W-4's file. A fix task would be speculative scope in an owner-reviewed plan |
| F-1 / PRIV-10 | W-11b F-1 | applied, status recorded. "Not gitignored" is **true** for the real default `src/backend/rl_exports` (`api/feedback.py:64-66`, main = A = B; `git check-ignore` rc=1). Only `data/rl_exports` and `src/backend/data/rl_exports` match `.gitignore:74 data/`. `api/profiles.py` has 0 `rl_export` references on all 3 refs |
| Ledger WAVE5 | nightly spec §1, §10 | applied. The checkout is origin/main, so audit/, capstone and plans are absent until P0-B/P0-B2; harness_drift_check.py is absent until P1; the UTC cron cannot follow DST |

## 2. Files changed

1. `docs/plans/2026-09-27-W11a-test-and-gate-hardening.md`
2. `docs/plans/2026-09-27-W11b-roadmap-items-gc1-gc4.md`
3. `docs/plans/2026-09-27-P04-doc-drift-sweep-amendment.md`
4. `docs/plans/2026-09-27-P08-gated-packet-hipaa-aligned-amendment.md`
5. `docs/plans/2026-09-27-S01-sql-echo-phi-leak.md`
6. `docs/plans/2026-09-27-nightly-doc-drift-routine-spec.md`
7. NEW `docs/reviews/2026-09-27-swarm/W11a-r4-response.md`
8. NEW `docs/reviews/2026-09-27-swarm/S01-r3-response.md`
9. NEW `docs/reviews/2026-09-27-swarm/RTN-r1-response.md`
10. NEW this report

## 3. Owner gates surfaced (all unsigned)

| Gate | Where | State |
|---|---|---|
| RTN Q6 (NEW): what to do if the cloud session can push | nightly spec §9 | proposed; default "do not enable" |
| OG-2 widened: now covers write/run/commit, not only commit | W-11a §11 | owner-gated |
| D9-SRC referenced in W-11a stop gate 2 | W-11a | proposed (program register) |
| SQL-ECHO over S1-A/S1-B (ask-first `core/profile_database.py` line) | S01 | owner-gated; no agent signs |

## 4. Handoffs (not edited — outside my files)

| Item | Target |
|---|---|
| PRIV-10 `src/backend/rl_exports` erase + ignore: unowned; needs a new ask-first plan (crypto-erase) | orchestrator / program §3.3 |
| GATE-14 eval-gate hang: flagged in W-11a, still has no owner | orchestrator (W-4 owns the script) |
| `api/profiles.py:328` display name logged at INFO (3b PRIV-06 "propose S-01 addendum"). S01 excludes it (#6); adding it needs an owner decision on an auth-adjacent file | orchestrator / owner |
| LOCAL-07 `data-privacy.md:196-197` (3b proposes P04). P04 §1 #2 routes all of data-privacy.md to W-10 | W-10 (6D) |
| Link the nightly spec from the program / capstone (DOC-011) | 6A / 6F |

Next action: the orchestrator reads this report and assigns owners for PRIV-10 and GATE-14 in program §3.3.
