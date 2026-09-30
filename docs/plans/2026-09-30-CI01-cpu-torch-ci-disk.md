# CI-DISK — CPU-only torch in CI test jobs

**Status:** owner-approved 2026-09-30 (gate CI-DISK-FIX in [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md)). Wave 1, before P1 PR #2 (#24) merges.
**Architectural:** no (CI only, no product code). No Codex review.

## Problem (measured)

E2E Smoke fails on every run since at least 2026-09-07 with `ERROR: Could not install packages due to an OSError: [Errno 28] No space left on device` during `pip install -r src/backend/requirements.txt` (jobs 109255740989, 109502705404, 109566187890). The job has already spent disk on `npm ci` and `npx playwright install --with-deps chromium`. The pip step then pulls the default PyPI `torch-2.14.0` (CUDA build) through `sentence-transformers` (`requirements.txt:73`). That brings about 15 `nvidia_*_cu13` wheels plus `triton`. The Playwright tests never run.

## Owner approval (verbatim)

- **CI-DISK-FIX:** "Small PR, .github/workflows/ci.yml only: in every job that runs `pip install -r src/backend/requirements.txt`, first `pip install torch --index-url https://download.pytorch.org/whl/cpu`. No product code. L1 proves E2E Smoke reaches the Playwright step; then #24 rebases and its E2E runs for real. Merge order: CI-DISK → #24."

**L0 scope note (within the approval, narrower):** the Security Scan job's `pip install -r` (`ci.yml:115`) feeds `pip-audit`. A `+cpu` local-version wheel may not match PyPI's vulnerability index, and `security_gate.py` ignores pip-audit `skip_reason` (owner item SECGATE-SHAPE). So torch could silently drop out of the audit. That job has disk to spare and passes today. **Leave `ci.yml:115` unchanged.** Apply the CPU pre-install to the three test jobs only: backend-tests (`:48`), agent-evals (`:165`), e2e-tests (`:200`). If the owner wants `:115` too, that is a separate answer.

## Files

| File | Change |
|---|---|
| `.github/workflows/ci.yml` | Before each of the three `pip install -r src/backend/requirements.txt` lines named above, add `pip install torch --index-url https://download.pytorch.org/whl/cpu`. Nothing else. |
| `docs/plans/2026-09-30-CI01-cpu-torch-ci-disk.md` | This plan (first commit), plus the regenerated `docs/INDEX.md` / `docs/_link_graph.json`. |

No product code, no test files, no requirements change. The collected count is unchanged (SLOT-RULE does not trigger).

## Tasks

1. **Task 0.** `git fetch origin`; worktree `../hc-ci-disk`, branch `ci/cpu-torch-ci-disk`, from `origin/main`. Record the sha.
2. **Local proof, in a scratch venv outside the repo** (for example `uv venv -p 3.11 /tmp/ci-torch-venv`):
   - `uv pip install -p /tmp/ci-torch-venv/bin/python torch --index-url https://download.pytorch.org/whl/cpu`
   - `uv pip install -p /tmp/ci-torch-venv/bin/python -r src/backend/requirements.txt`
   - `uv pip list -p /tmp/ci-torch-venv/bin/python | grep -ci nvidia` must print `0`.
   - `python -c "import torch, sentence_transformers; print(torch.__version__)"` must end in `+cpu`.
   - Paste all four outputs. If a step fails, or nvidia wheels still appear, STOP and report.
3. **Edit** `ci.yml` as in the file table. Commit `ci: install CPU-only torch before backend deps in test jobs`.
4. **Commit the plan**, regenerate the index, and run `docs_lint.py` and `generate_docs_index.py --check`.
5. **Open the PR.** Watch CI with `gh pr checks <n>` (tab output; this gh has no `--json` there).
   - **Acceptance:** Backend, Agent Eval, Docs Lint, Frontend and Security all pass.
   - **E2E Smoke** gets past "Install backend dependencies" and reaches "Run E2E tests". Paste the log lines that prove it (`gh api repos/BrooklynD23/HealthCentral/actions/jobs/<id>/logs`).
   - If E2E then fails inside Playwright, that is a real test failure, not CI-DISK. Report it with the first failing spec and its error. Do not "fix" tests in this PR.
6. **Report to L0.** Do not merge.

## Stop gates

- Any file other than `ci.yml`, this plan and the two generated index files.
- Disk still exhausted with CPU torch. Report the log; the next option (free runner disk) needs a new owner answer.

## Rollback

`git revert` the merge commit. CI returns to the CUDA torch install.
