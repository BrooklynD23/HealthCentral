# Wave 3 — L1-C report (P4-core doc-drift sweep)

**Result:** PR #40 is open (https://github.com/BrooklynD23/HealthCentral/pull/40) with CI green on 6 of 6 checks and reviewer verdict APPROVE (round 2). It has not been merged.

| Item | Value |
|---|---|
| Branch / worktree | `docs/p4-doc-drift` / `/mnt/c/Users/DangT/Documents/GitHub/hc-p4` |
| Base → head | `origin/main` `90c502a` → `cd17e2b8b60b89ddd6774219d76028f7896b8ab2` (26 commits, 30 files) |
| Collected count | 1346 before → 1346 after (S8 holds) |
| Interpreter | Python 3.11.16 (`~/venvs/asclexis-311`), WSL2 Linux 6.6.87.2, `HF_HUB_OFFLINE=1` |
| CI run 37192591719 | Agent Eval Gate, Backend Tests, Documentation Lint, E2E Smoke Tests, Frontend Tests and Security Scan all passed |

## 1. Measurements (L1, in the worktree)

| Run | Output |
|---|---|
| Start collect @90c502a | `1346 tests collected in 55.33s`, collect_exit=0 |
| Start suite (flock) | `1346 passed, 69 warnings in 223.51s`, pytest_exit=0, 0 FAILED |
| End collect @50d4bbe | `1346 tests collected in 26.21s`, collect_exit=0 |
| End suite (flock) | `1346 passed, 60 warnings in 143.31s`, pytest_exit=0, 0 FAILED |
| Baseline lines | `CLAUDE.md:30` and `AGENT.md:76` already say 1346, so they were not edited |

A cached embedding model was present, so `test_api_rag_index_002b` passed locally.

## 2. Gates at the head (`../hc-p4`)

| Gate | Output |
|---|---|
| `docs_lint.py` | Docs lint passed. |
| `generate_docs_index.py --check` | fresh, exit 0 |
| `feature_list_lint.py` | OK feature_list.json: 27 entries, no violations |
| `repo_hygiene_check.py` | Repo hygiene passed. |
| `harness_drift_check.py` | Harness drift check passed. |
| §11 relative-link resolver | relative links OK (run by the implementer) |
| Import smoke | import-ok (run by the implementer) |
| Mermaid, Windows `npx @mermaid-js/mermaid-cli@11` | exit 0 on all 4 files: pipelines 3 charts, arch README 2, backend 4, ci-and-quality-gates 1 |
| File guard: `git diff --name-only origin/main...HEAD -- CLAUDE.md docs/compliance/data-privacy.md docs/compliance/hipaa-controls.md .serena/project.yml docs/capstone-report audit skills/asclexis-guardrails` | empty |

## 3. Per-task status

| Task | Status |
|---|---|
| 0 | done by L1. All 7 preconditions printed. |
| 1, 5R, 6, 7, 8, 9, 12, N1–N3, N6, N7 | done |
| 2 | done. The API rows use `endpoints.md` descriptions instead of plan 04's text, which was wrong for Care Tasks, Pinboards and Search. |
| 3 | docs part: no edit needed. OG-4 done in `c6fb2e7`. |
| 4 | DONE by P2 (`4aa8e03`, `aae90ec`), no edit. Line 26 still says "all implemented", but it carries the true wired-scheduler caveats. |
| 10 | OG-5 done in `fd3f287`. The fallback sentence was verified at `api/assistant.py:801-807`. |
| 11 | real drift found. The undocumented `GET /medications/{medication_id}/correlations` row was added in `3c92467`. |
| 13 | done, in 2 commits (`884b83c`, `e462a4b`). |
| 14 | docs part: no edit needed. OG-6 done in `9db9ff9`. `test_verify_model_repos.py` showed 7 passed before and after. |
| 15 | DONE-N/A. W-1 is merged, there are 5 agents, and the drift check passes. |
| N4 / N5 | done. W-6 is merged, so the W-6 part of D12 is worded as landed, and W-10 is still marked pending. N5 lists **6** `core/` files, because P2 added `core/auth.py:407,441`; the plan said 5. |
| 16 | done. Includes the Session Note, the §12 OG-4/5/6 ticks (recorded, not signed) and the §15 execution record. |
| N8, N9, N10, F1–F6 | not run, because they are deferred. |

Review: `code-reviewer` (opus) returned CHANGES in round 1, with 2 MAJOR and 10 MINOR findings. Fix commits `f4da31c`, `3c6774a`, `5c5f7a2`, `3f2547e`, `50d4bbe` addressed both MAJORs and 6 of the MINORs. Round 2 returned APPROVE.

## 4. Deferred triggers on 90c502a

| Task | Trigger |
|---|---|
| N8 (D11 vocabulary) | **HIT**. W-5 is merged: `rag.py` :128/:133/:134 are now label wording, and the validator `[cite:` at `:819` is unchanged. |
| N10 (guardrails SKILL) | **HIT**. `redaction_bypass_active` and `BREAK_GLASS_AUDIT_EVENT` are in `external_runner.py`, and `redaction_break_glass` is in the frontend. |
| N9 | not hit: P8-B2-ORDER is unsigned. |
| F1 (W-3), F2 (W-2 + W-10), F3 (W-7), F4 (W-4), F5 (W-8) | not hit |
| F6 (W-6 + W-10) | half-met: W-6 is merged, W-10 is not. |

## 5. Open findings

**Must decide**
1. **Safety gap on the legacy chat path (owner).** When an answer matches an `interpret_safety` prohibited-advice pattern, it is still served:
   - `modules/rag.py:836-838` only appends an error.
   - `rag.py:869` sets `is_valid=False`.
   - `api/assistant.py:869-901` returns the answer regardless.
   - The frontend never reads `is_valid`.

   W-4 covers only the case where faithfulness is below 0.6. `pipelines.md` now documents this truthfully. It needs an owner item or work item; P4 cannot fix it.
2. `AGENT.md:76` still says "1269 pass in CI, 1268 without an embedding model" next to "1346 collected". Those pass figures are stale and unmeasured. P4 flags them only.

**Later**
1. The OG-5 text in `src/backend/api/__init__.py` is thinner than the code for pinboards (CRUD and packet export) and care_tasks (accept and patch). Changing it needs a new owner OK.
2. The §12 ticks cite the owner-decisions OG-4/5/6 row, which exists only on `docs/wave3-close` (`9cccbd1`). Merge that branch for the citation to resolve.
3. Plan defect: the Task 6 grep `'if \[ "$code" -ge 2 \]'` reads `$` as an end anchor and prints nothing. `grep -F` gives 2 hits.
4. `docs/architecture/README.md:103-104` wraps "work item W-8" across a line break. Rejoin it when F5 runs.
5. Plan line numbers had drifted (for example, the HC-M23 heading is at `TASK_LIST.md:936`, not `:853`). Every Before block still matched exactly once (S1 held).

## 6. Merge order

PR #40 has no in-wave conflicts with other L1s that L1-C knows of. It edits the `AGENT.md` and `TASK_LIST.md` shared slots, so it must merge serially with any other phase that touches those files. Next come N8 and N10, each as its own PR off main after #40 merges.

Next action: owner reviews and merges PR #40.
