**BLOCKED** — hard dependencies P5 and W-4 are not merged on `origin/main` (W-4 itself needs P5).

# W-11a PR-3 — G-B4 migration heads + CI gates · readiness pack (sections 1-3 only)

**Written:** 2026-10-07 · **Measured on:** worktree `hc-scaffold` @ `8d6f02e`, `origin/main` = `6b4dd84` · **Plan:** [`docs/plans/2026-09-27-W11a-test-and-gate-hardening.md`](../../../../docs/plans/2026-09-27-W11a-test-and-gate-hardening.md) (Task 0, Tasks 4-10) · **Status:** scaffold only. Nothing here is implemented, signed or approved. Work stops at the blocker; sections 4-7 are not written.

## 1. Readiness verdict

| Dependency / gate | State |
|---|---|
| P4-core (PR #40; fixes `ci-and-quality-gates.md` first) | merged |
| D9 venv | present |
| **P5** (adds its step to `ci.yml` first) | **NOT merged** → BLOCKED |
| **W-4** (adds the `legacy-evals` job to `ci.yml` first) | **NOT merged** → BLOCKED |
| Q-RUFF (Task 7) | **UNSIGNED** |
| Q-COV (coverage threshold) | **UNSIGNED** |
| CI-SEED = plan OG-3 (optional real-CI proof) | **UNSIGNED** |

Not architectural (orchestration §5). No ask-first file is edited, so security-reviewer is not required by the orchestration rule; code-reviewer always.

## 2. Task 0 evidence (measured)

| Check | Command | Output |
|---|---|---|
| base | `git rev-parse --short origin/main` | `6b4dd84` |
| P4-core | `git merge-base --is-ancestor 6b4dd84 origin/main; echo $?` | `0` |
| D9 venv | `~/venvs/asclexis-311/bin/python --version` | `Python 3.11.16` |
| **P5 missing** | `git ls-tree --name-only origin/main scripts/ \| grep -c time_source_lint` | `0` |
| **W-4 missing** (the plan's own probe, `:279`) | `git grep -n 'legacy-evals' origin/main -- .github/workflows/ci.yml \| wc -l` | `0` |
| W-4 commit search | `git log --oneline origin/main --grep "W-4\|W04\|legacy abstain\|W-2\|W02\|doctor-summary" \| head -5` | 3 old export commits (`49e683c`, `72b156e`, `b2ee43a`); none is W-4 or W-2 |
| PR-3 not started | `ls src/backend/tests/test_migration_heads.py` | No such file |
| PR-3 not started | `grep -n "npm run lint\|npm run build\|--cov\|ruff" .github/workflows/ci.yml` | no lines |
| branches / PRs | `git branch -r \| grep -iE 'w11a\|gb4'`; `gh pr list --state open` | only the merged PR-2 / PR-4 branches; open PR #49 (docs) |
| plan tracked | `git ls-files docs/plans/2026-09-27-W11a-test-and-gate-hardening.md` | path printed; also on `origin/main` |

**Owner gates**

| Gate | Row | State |
|---|---|---|
| D9 / D9-SRC | `docs/capstone-report/owner-decisions-2026-09-27.md:12`, `:29` | signed |
| SLOT-RULE | `owner-decisions-2026-09-27.md:31` | signed |
| Q-RUFF | `grep -n "Q-RUFF" owner-decisions-2026-09-27.md` → 0 rows; plan `:1947` blank | **UNSIGNED** |
| Q-COV | 0 rows; plan `:1953` blank | **UNSIGNED** |
| CI-SEED (plan OG-3) | 0 rows; plan `:1954` blank; program `:507` "Still owner-gated" | **UNSIGNED** (optional) |

## 3. Owner questions still to ask (after P5 and W-4 merge)

**Q1 — Q-RUFF (plan `:1947`, wording kept).** "Which ruff rules gate CI?"

| Option | Effect |
|---|---|
| **(a) Gate on `ruff check --select E9,F63,F7,F82`, ruff pinned to 0.15.10** — the plan's recommendation | 0 findings when the plan measured (2026-09-27, A+B tree); the configured F/I/W set stays advisory. Re-measure on the start tree (Task 5). |
| (b) Clean up all configured-rule findings first | 561 findings in 154 files when measured, 37 of them in 10 ask-first / auth / encryption files; each of those needs its own approval. |
| (c) No ruff gate | Task 7 is skipped. |

Current finding counts on `6b4dd84`: UNMEASURED by this pass (ruff was not run).

**Q2 — Q-COV (plan `:1953`).** "Coverage is added as a report that fails closed when the report is missing. Set a threshold?" Options: **(a) report only, no threshold now; decide after the first measured TOTAL — recommended** (the plan says TOTAL is UNMEASURED); (b) a threshold of ___% after Task 5 Step 4 measures it; (c) no coverage step. Note: the user-level rule asks for 80%; the repo has no measured figure yet, so a number chosen now would be asserted, not measured.

**Q3 — CI-SEED (plan OG-3, optional; shared with W-4 and with P5 pack Q4).** "Allow one throwaway draft PR carrying seeded violations, to show each new CI gate failing in GitHub Actions; closed unmerged?" Options: **(a) yes, one draft PR for all PR-3 gates — recommended** (the program's acceptance is "each new gate fails on a seeded violation"; without it the real-CI column is recorded as `UNMEASURED in CI`); (b) no, local proof only.

**Q4 — merge order with W-4 (plan stop gate 9, `:1904`).** Only if PR-3 is ready before W-4: "Which lands first on `ci.yml`?" The program order is P5 → W-4 → W-11a PR-3 → W-8. **Recommended: keep the program order.**

**Q5 — GATE-14 home (unowned; 3b proposed W-11a).** "`scripts/agent_eval_gate.py` printed PASS and did not exit on Windows Py 3.13.7 (`rc=124`). PR-3 is the CI-gates PR. Add a fix or an exit-code assertion here?" Options: **(a) keep it an owner item; PR-3 records the Linux exit code as a read-only measurement (the plan offers this at `:1892`) — recommended**; (b) add a fix to PR-3 (new scope; `scripts/agent_eval_gate.py` is not in the plan's file list); (c) leave unmeasured.

**Ask-first edits in PR-3**

| File | Edit | Covered? |
|---|---|---|
| any ask-first file | **none** under Q-RUFF (a) or (c) | n/a |
| four safety modules, `core/auth.py`, `core/security.py`, `core/profile_database.py`, `core/audit.py`, `core/migrations.py`, `api/profiles.py` | edited **only** under Q-RUFF (b) (lint fixes) | not covered by any signed row; each needs its own approval |
| `pyproject.toml`, `src/backend/requirements.txt`, `src/frontend/package.json`, `eslint.config.js` | none; the plan lists them as not licensed (`:100`) | n/a |

Non-ask-first files PR-3 does edit: `.github/workflows/ci.yml` (`frontend-tests` lint + build; `backend-tests` coverage; new `backend-lint` job), new `src/backend/tests/test_migration_heads.py` (HC-MIGHEAD-001…003), `docs/architecture/ci-and-quality-gates.md`, capstone rows, `CLAUDE.md` / `AGENT.md` collected slot, `TASK_LIST.md`.

**Carry into the drift check once unblocked (seen while reading, not checked in depth):**
- `src/backend/requirements.txt:119` has `pytest-cov>=4.1.0` and `:121` `ruff>=0.1.0` (unpinned); Q-RUFF (a) pins ruff 0.15.10 in the workflow step, not in the file.
- `ci.yml` job lines cited against `B@7b2ff1f` have moved: `frontend-tests` is `:55-78` today, and CI-DISK (PR #25) added a CPU-torch install to the three test jobs.
- P5 adds the `time_source_lint` step and P6 adds profile migration `013`; HC-MIGHEAD must not pin a head name. The new file also matches plan 06's `-k migration` selector (plan `:138`).
- The new gates must be described in `docs/architecture/ci-and-quality-gates.md` (Task 9); P5's lint step has no doc owner today (P5 pack §4 amendment 9) and could be folded in here on the owner's word.

**Next action:** after P5 and W-4 merge, re-run `git grep -n 'legacy-evals' origin/main -- .github/workflows/ci.yml | wc -l` (expect ≥ 1), ask Q1-Q3 in one prompt, and write sections 4-7.
