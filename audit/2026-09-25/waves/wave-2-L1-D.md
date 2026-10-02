# Wave 2 — L1-D report (P8, G-C4)

Both PRs are open. Neither is merged, and no owner gate was signed.
- P8: https://github.com/BrooklynD23/HealthCentral/pull/30 (head `2ca3bd1`)
- G-C4: https://github.com/BrooklynD23/HealthCentral/pull/28 (head `376c376`)

Base for both: `origin/main` @ `8064244`. Main has since moved to `2e85487` (PR #27). Neither branch is refreshed yet; L0 will say when.

## P8 — gated-items decision packet

| Item | Value |
|---|---|
| PR | https://github.com/BrooklynD23/HealthCentral/pull/30 |
| Branch / head | `docs/p8-gated-packet-hipaa-aligned` / `2ca3bd11e5d2139cca29d234209b7015c9af4db9` |
| Worktree | `../hc-p8` |
| Plan | `docs/plans/2026-09-27-P08-gated-packet-hipaa-aligned-amendment.md` Tasks 0–7 |
| Files (4) | `audit/2026-09-25/gated-items-decision-packet.md`, `docs/features/TASK_LIST.md`, `docs/INDEX.md`, `docs/_link_graph.json` |
| Collected | 1296 → 1296 (delta 0; D9 venv 3.11.16, `flock` + HF_HUB_OFFLINE=1) |
| Gates used | D10 (verbatim in PR), SLOT-RULE (no slot change), SQL-ECHO (F-P8-3 routed to S-1) |
| Review | opus round 1: CHANGES, 0 blockers / 5 major / 13 minor. All fixed in `2ca3bd1`; L1 re-verified. |

Commits:
- `afea770`, `11bb595`, `cac9dd7`, `c4a2f7c`, `191566a`, `f59f19d`: Tasks 1–6 (L2)
- `3cdbb0e`: Task 7, packet + TASK_LIST. The L2 left this work uncommitted when the host ran out of memory; L1 verified and committed it.
- `c96df6e`: index regeneration
- `2ca3bd1`: review fixes

### Gate outputs (head 2ca3bd1)
```
$ python3 scripts/docs_lint.py            -> Docs lint passed. (0)
$ python3 scripts/generate_docs_index.py --check -> docs/INDEX.md and docs/_link_graph.json are fresh. (0)
$ python3 scripts/harness_drift_check.py  -> Harness drift check passed. (0)
```
- Before the index commit, `--check` printed `docs/INDEX.md is stale.` / `docs/_link_graph.json is stale.` (exit 1). The TASK_LIST edit caused it. The index was regenerated and committed in `c96df6e`.
- Mechanical checks: forbidden-phrase grep exit 1 (seeded copy → 1); mandatory phrase 2 (broken copy → 0); C2-ok, C7-ok, C13-ok (each break-it fired); 5 briefs / 7 `## ` headings / 8 `Owner decision:`; feature_list.json unchanged.
- Security gate fail-closed: exit 2 on both the bandit and the pip-audit path.

### Owner sign-off lines (owner fills after merge)
All in `audit/2026-09-25/gated-items-decision-packet.md`:
1. `Owner decision:` lines:
   - `:64` Brief 1 MFA
   - `:117` Brief 2 key rotation
   - `:196` Brief 3 pen test
   - `:330` Q4a
   - `:333` Q4b
   - `:336` Q4c
   - `:393` Q5a
   - `:407` Q5b
2. Sign-off ledger rows `:420`–`:427`, items 1, 2, 3, 4a, 4b, 4c, 5a, 5b. The Date and Notes cells are empty.
3. **P8-B2-ORDER** (plan S-2, `docs/plans/2026-09-27-P08-gated-packet-hipaa-aligned-amendment.md:635`): run Brief 2 to signature before P4 edits `hipaa-controls.md:169`, or have P4 skip that task.

### Open findings
1. **Full-suite start/end failure diff was not run at the end.** After the out-of-memory crash, L0 ruled no backend pytest for docs-only phases, and the start log in `/tmp/hc-p8-measure` was lost. Only collection was measured. The diff is docs-only.
2. **F-P8-2 / new:** the following doc claims overstate what the code does. Route to P4/W-10.
   - `docs/compliance/data-privacy.md:33` says "log file"; no sink exists.
   - `hipaa-controls.md:49` mentions correlation IDs; `models/audit.py` has no correlation-id column.
   - `hipaa-controls.md:52` says "append-only", contradicted by the DELETE at `api/profiles.py:908-910`.
3. **F-P8-3 (security, PRIV-06):** debug SQL echo writes display names to stderr. Measured on both TestClient and uvicorn. Owned by S-1.
4. Audit-INSERT echo count was 1 under TestClient and 2 under uvicorn. Cause UNMEASURED.
5. `TASK_LIST.md` is shared. If another Wave-2 PR edits it first, rebase P8 before merging.

## G-C4 — HC-M08a packaging decision record

| Item | Value |
|---|---|
| PR | https://github.com/BrooklynD23/HealthCentral/pull/28 |
| Branch / head | `docs/gc4-packaging-decision` / `376c376fbe9824645998e26887266ebfe9a160c9` |
| Worktree | `../hc-gc4` (the plan says `HealthCentral-gc4`) |
| Plan | `docs/plans/2026-09-27-W11b-roadmap-items-gc1-gc4.md` G-C4, Tasks C4.0–C4.3. **C4.4 not done**: S-C4-1 is unsigned, so `feature_list.json` is untouched. |
| Files (3) | `docs/plans/2026-10-01-packaging-decision.md`, `docs/INDEX.md`, `docs/_link_graph.json` |
| Collected | 1296 → 1296 (delta 0) |
| Gates used | D8 `:21`, D8-delivery `:26`, note 4 `:62` (options plus a labelled recommendation; nothing decided); EMB-REV unsigned |
| Review | opus round 1: CHANGES, 0 blockers / 3 major / 7 minor. All fixed in `376c376`; L1 re-verified. |

Commits:
- `f96b5e3`: the record (L2)
- `376c376`: review fixes (verbatim transcripts, CUDA footprint, base-model wording, citations)

### Gate outputs (head 376c376)
```
$ python3 scripts/docs_lint.py            -> Docs lint passed. (0)
$ python3 scripts/generate_docs_index.py --check -> docs/INDEX.md and docs/_link_graph.json are fresh. (0)
$ python3 scripts/harness_drift_check.py  -> Harness drift check passed. (0)
$ python3 scripts/feature_list_lint.py    -> OK feature_list.json: 27 entries, no violations (0)
```

### Owner sign-off lines (owner fills after merge)
All in `docs/plans/2026-10-01-packaging-decision.md`, each `☐ owner: ____ date: ____`:
1. `:160` S-C4-1: packaging path (A/B/C)
2. `:161` S-C4-2: data-directory location
3. `:162` S-C4-3: code signing (yes/no, cost)
4. `:163` S-C4-4: licence notices
5. `:164` S-C4-5: embedding model and revision (= **EMB-REV**)

After S-C4-1 is signed: Task C4.4 is a separate commit that flips HC-M08a in `feature_list.json`.

### Open findings
1. **Security, pre-existing, out of scope:** `npm audit` in `src/frontend` reports 21 vulnerabilities (1 critical, 14 high). No ticket exists. Suggest registering it as an owner item.
2. W-11b plan errata:
   - The HC-EMB-002 re-run is cited as W-8 `:72`; the requirement is actually at `:78`.
   - F-5 ("D8-delivery not yet a row") is stale; the row is at `:26`.
   - The plan cites `requirements.txt:52`/`:108`; the actual lines are `:72`/`:128`.
3. The D9 venv drifted: site-packages measured 4.7G, then 5.9G on the same day. torch is a CUDA build (`2.14.0+cu130`), so the CPU-build installer footprint is UNMEASURED.

## Merge order (L0 hands over)
P8 (#30) and G-C4 (#28) go last, after S-1, W-6, W-11a PR-2, W-5, W-1 and P2. For each:
1. Merge `origin/main` into the branch.
2. Run `python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py --link-graph`.
3. Commit the two index files.
4. Re-run the 3 gates.

## Incidents
- The host ran out of memory mid-phase and every agent died, including the first G-C4 reviewer and the P8 implementer during Task 7. Committed work survived. L1 resumed and kept one L2 at a time from then on.

## Update 2026-10-02: P8 refreshed onto main (L0's turn signal)
1. `git merge origin/main` (cff3827) produced merge commit `98f3b3d`. The only conflict was in `docs/features/TASK_LIST.md`. It was resolved by keeping all 3 notes dated 2026-10-01: P8 packet, notification scheduler, Wave 1 merged. Against main the diff is the P8 note plus Last Updated.
2. Regenerating `docs/INDEX.md` and `docs/_link_graph.json` gave byte-identical files, so there was nothing to commit.
3. Gates:
   - docs_lint: "Docs lint passed." (0)
   - index --check: "fresh" (0)
   - harness_drift_check: "passed" (0)
   - collect-only under flock: `1346 tests collected` (= main; CLAUDE.md:30 says 1346)
4. Pushed. `gh pr checks 30`: 6/6 pass (Agent Eval Gate, Backend Tests, Documentation Lint, E2E Smoke Tests, Frontend Tests, Security Scan).
