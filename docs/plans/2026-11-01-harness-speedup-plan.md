# Harness speedup 2026-11-01 — plan for HARNESS-SPEEDUP

**Last Updated:** 2026-11-01 (Opus planner on `5e4c2e8a`: one lane E harness row from L0's measured analysis of 2026-11-01, per owner row SPEEDUP-1-3; RUNBOOK L0 duties #2, #4 and #5 applied in the same docs PR)
**Owner:** repository owner
**Status:** APPROVED (owner, SPEEDUP-1-3, L0 AskUserQuestion, answered 2026-11-01: "#1 Path-scoped tests and CI" and "#3 Small-row fast lane", both chosen). Docs only. The row is **ready**. Merge-only gate **SPEEDUP-CI-DIFF** (new, not asked yet): L0 shows the owner the `.github/workflows/ci.yml` diff before merge. Every gate keeps its state in [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md).
**Base measured:** `origin/main` @ `5e4c2e8a` (2026-11-01, #438 merged). Every `file:line` below was re-read by the planner on that commit.
**Refresh Trigger:** any edit before this row is built to `.github/workflows/ci.yml`, `.claude/workflows/build-item.js` or `.claude/workflows/build-program.js`; a change to the required status checks on `main`; a new backend test that reads a file outside `src/backend/`.

Queue row: [queue.md, "Planned 2026-11-01, harness speedup"](2026-10-15-build-program/queue.md#planned-2026-11-01-harness-speedup). Rules: [RUNBOOK](2026-10-15-build-program/RUNBOOK.md), [contracts](2026-10-15-build-program/contracts.md) §b-§d. CI doc: [ci-and-quality-gates](../architecture/ci-and-quality-gates.md).

## Why (L0's measured analysis, 2026-11-01)

- 18 build-item runs this session took about 12.7 agent-hours and 10.8M tokens. 8 reached a ready PR and 10 stopped.
- Trivial rows paid for the full pipeline. UIG002-TITLE (2 lines) took 35 min and 411k tokens. SHELL-NAVREF-DEAD (1 line) took 37 min and 382k tokens.
- 5 of the 10 stops were harness friction: PR retitles denied by auto mode inside subagents; the Workflow tool not available for a dry run; `hold_slots.sh` wiped from `/tmp`; a dirty worktree. These are L0 duties #2 and #5, now in [RUNBOOK §10.1](2026-10-15-build-program/RUNBOOK.md#101-claude-code) (this docs PR).
- 3 stops were plan file-list gaps: the parity test HC-SLOG-004, the audit-order guard, and unlisted hunks. This is the planner checklist #4, also in RUNBOOK §10.1 now. Task 5 below wires it into the build-program planner prompt.
- CI has no path filters. A docs-only PR waits about 10 min: E2E Smoke ≈600 s, Security Scan ≈365 s, Backend ≈260 s, Frontend ≈145 s.

## Facts (re-read on `5e4c2e8a`)

1. **Required status checks (measured 2026-11-01).** `gh api repos/BrooklynD23/HealthCentral/branches/main/protection` returns `required_status_checks.contexts` = `Documentation Lint`, `Backend Tests`, `Frontend Tests`, `Agent Eval Gate`, `Security Scan`, with `strict: false` and `enforce_admins: true`. The one repository ruleset, "Default" (id 12762999), holds only `deletion` and `non_fast_forward`, and no required checks. `RSI Replay` is **not** required yet. The owner action RSI-REPLAY-REQUIRED (queue `:836`, answered 2026-10-22 "Make it required") is still pending. E2E Smoke, Backend Lint and Legacy RAG Eval Gate are not required. This matches the CI doc (`ci-and-quality-gates.md:61`, measured 2026-10-21).
2. **CI has no filter.** `ci.yml:3-7` triggers on every push to `main` / `Security-Revamp-*` and every PR to `main`. No job has `if:` or `needs:`, except `e2e-tests`, which has `needs: [frontend-tests, backend-tests]` (`:256`). Jobs: docs-lint `:10-36`, backend-tests `:38-74`, backend-lint `:78-94`, frontend-tests `:96-131`, security-scan `:133-203`, agent-evals `:205-227`, legacy-evals `:229-251`, e2e-tests `:253-315`, rsi-replay `:317-338`. Each uses `actions/checkout@v4` with the default `fetch-depth: 1`.
3. **Some backend tests read files outside `src/backend/`.** These are the couplings a path filter must respect. The planner listed every `REPO_ROOT` / `parents[3]` read in `src/backend/tests`:
   - `test_docs_lint.py:118-126` reads every repo `.md` link (DOC-007), `src/frontend` README scripts (DOC-009) and **the committed `docs/INDEX.md` + `docs/_link_graph.json`** (`test_docs_index_check_passes_on_real_repo`). The CI docs-lint job regenerates the index *before* linting (`ci.yml:23-24`), so today only Backend Tests checks the committed index.
   - `test_claude_agent_definitions.py` reads `.claude/agents/*.md`, `scripts/harness_drift_check.py` and `docs/agentic/harness.md` (HC-AGENTS-008, `:237-247`: harness.md names each agent by full path, then the drift check over `docs/agentic/*.md` passes).
   - `test_session_log_hook.py` reads `.claude/hooks/session_log.py`, `.claude/settings.json` and `.claude/mods/asclexis-rsi/hooks/logic.ts` (HC-SLOG-004, `:165-167`). This is the parity test that stopped #429.
   - `test_ocr_rapid.py:1123-1125` reads `THIRD_PARTY_NOTICES.md` (HC-OCR-013).
   - `test_dev_sh_prereqs.py` reads `dev.sh`; `test_donation_routes_http.py` reads `src/frontend/src/components/settings/DataDonationCard.tsx`; `test_docs_lint.py`, `test_security_gate.py`, `test_repo_hygiene_check.py` and `test_harness_drift_check.py` load `scripts/*.py`.
   - Neither eval gate reads `docs/` (`scripts/agent_eval_gate.py:37`, `scripts/legacy_eval_gate.py:10`: golden cases under `src/backend/tests/`). No vitest or Playwright file reads a doc (grep of `src/frontend/src`, `src/frontend/e2e`).
   - `python3 scripts/generate_docs_index.py --check` (`generate_docs_index.py:150-160`) prints `docs/INDEX.md and docs/_link_graph.json are fresh.` (exit 0), and `python3 scripts/harness_drift_check.py --repo-root .` prints `Harness drift check passed.` (exit 0). Both measured on `5e4c2e8a`, stdlib only.
4. **build-item.js test stage.** `runTests(round)` (`build-item.js:263-278`) always runs, in this order: (1) focused test files from `impl.files_changed`, (2) `--collect-only`, (3) **the full backend suite** (`:269`), (4) the plan's acceptance commands, (5) `docs_lint.py`. It is called at `:286`, `:291` and `:333`. Vitest is listed only for changed `src/frontend/**/*.test.ts(x)` (`vitestFiles`, `:260`). No step runs `claude plugin test`. Verify (`:357`) and RUNBOOK §6 step 2 (`RUNBOOK.md:135-140`) both assume a full-suite run.
5. **build-item.js stages for every row.** Explore (Haiku xhigh, `:108-124`) reads the queue row. The runtime/kind refusals (`:126-135`) run on its output. Then come Plan check (Opus, `:143-157`), Implement, Test, Review and Verify. Review uses one lens, `spec + quality + recurring failures`, plus a second, `security`, only when `spec.security_sensitive` (`:317-318`). So a non-security row already gets **one** Opus review per round. The fast lane therefore saves the explore stage and, through #1, the full suite; it never removes a lens (see Design §3).
6. **Resume identity (`:150`).** A resume needs the title to start with `[blocked:claude]`, or `[escalated:claude]` plus an `L0 ruling:` comment. Task 0 then retitles to `[claim:claude…]` (step (d)). When auto mode denies that retitle inside the subagent, the item stops. If L0 pre-retitles to `[claim:…]` instead, the identity check fails (`title is not [blocked:`), which is the TOAST-SHELL #410 shape. `block()` (`:196-206`), the escalation (`:340-348`) and Verify step 5 (`:360`) also retitle from inside agents.
7. **Planner prompt.** `build-program.js:174-182` (task text `:177`) asks for file lists and RED-first test ids. It does not ask the planner to look for parity or guard tests over the touched files.
8. **Queue columns** (`queue.md` tables): `| id | lane | kind | depends_on | owner gates | ask-first | files | est h | runtime | status |`. `est h` is free text (for example `0.75`, `3 (+0.5 Task 3)`). `ask-first` is `—` when there is none.

## Design

### 1. CI: docs-only PRs skip the code jobs, and still report success

**Pattern (chosen because it cannot leave a PR unmergeable and cannot let code skip its tests):** add a `changes` job, give each skippable job a job-level `if:` on its output, and make that `if:` fail closed.

- **Never** add workflow-level `on.pull_request.paths` / `paths-ignore`. When a whole workflow is filtered out, GitHub leaves its required checks **Pending** for ever ("Expected — waiting for status"), so a docs PR could never merge. When a *job* is skipped by its `if:` condition, GitHub reports that check as **Success**, and a required check that reports Success does not block merge (GitHub docs, "Handling skipped but required checks"). So job-level skipping is safe for the 3 required jobs we skip: Backend Tests, Frontend Tests and Agent Eval Gate.
- **The bypass to close:** when a job in `needs` fails, the dependent job is skipped too, and that skip would also report Success. A naive `if: needs.changes.outputs.docs_only != 'true'` therefore turns a broken `changes` job into "all required jobs green". So every skippable job uses exactly:
  ```yaml
  needs: changes
  if: ${{ !cancelled() && !(needs.changes.result == 'success' && needs.changes.outputs.docs_only == 'true') }}
  ```
  A job is skipped only when `changes` **succeeded** and **explicitly** printed `docs_only=true`. If `changes` fails, times out or prints nothing, every job runs.
- `e2e-tests` keeps its order and inherits the skip:
  ```yaml
  needs: [changes, frontend-tests, backend-tests]
  if: ${{ !cancelled() && needs.frontend-tests.result == 'success' && needs.backend-tests.result == 'success' }}
  ```
  It is skipped when both are skipped (docs-only) or when either fails (as today).
- **New job `changes`** (name `Change Scope`, not required). It runs `actions/checkout@v4` with `fetch-depth: 2`, then one step:
  ```bash
  set -uo pipefail
  if [ "$EVENT" = pull_request ] && git rev-parse -q --verify HEAD^2 >/dev/null \
     && files=$(git diff --name-only --no-renames HEAD^1 HEAD); then
    printf '%s\n' "$files" | python3 scripts/change_scope.py >> "$GITHUB_OUTPUT"
  else
    echo docs_only=false >> "$GITHUB_OUTPUT"
  fi
  ```
  `EVENT` is `${{ github.event_name }}`. On `pull_request`, `HEAD` is GitHub's merge commit, so `HEAD^1..HEAD` is exactly the PR's change against the base it merges into. `--no-renames` lists both sides of a rename, so moving `src/x.py` to `docs/x.md` counts as a code change. A push to `main` / `Security-Revamp-*`, a missing merge parent or a failed `git diff` all mean `docs_only=false`, so everything runs.
- **Skipped on docs-only:** `backend-tests`, `frontend-tests`, `agent-evals`, `legacy-evals`, `e2e-tests`. **Unchanged, always run:** `docs-lint`, `security-scan`, `backend-lint` (ruff, cheap) and `rsi-replay`. RSI Replay is left alone so that it is already correct if the owner makes it required (RSI-REPLAY-REQUIRED); it is not in owner SPEEDUP-1-3's skip list.
- **The couplings in Fact 3 stay covered on docs-only PRs.** docs-lint gains two always-run steps:
  - `python3 scripts/generate_docs_index.py --check`, placed **before** the "Regenerate docs index and link graph" step (`ci.yml:23-24`). Placed after it, it could never fail. This moves the committed-index check of `test_docs_index_check_passes_on_real_repo` into a job that always runs. It fails in exactly the cases where Backend Tests fails today: the same merge ref, the same function.
  - `python3 scripts/harness_drift_check.py --repo-root .`: the drift half of HC-AGENTS-008.
  
  DOC-007 and DOC-009 already run in `docs_lint.py` (`docs_lint.py:537-538`). Two paths are **carved out** of docs-only, because the backend tests that read them cannot be replaced by a stdlib step: `docs/agentic/harness.md` (the agent-name half of HC-AGENTS-008) and `THIRD_PARTY_NOTICES.md` (HC-OCR-013). A PR touching either one runs everything.
- **`scripts/change_scope.py`** (new, stdlib only, the single source of the scope rule for CI and for build-item). It reads changed paths from stdin, one per line, and prints exactly four lines, `docs_only=`, `backend=`, `frontend=`, `mods=`, each `true` or `false`:
  - `docs_only`: true only if the list is non-empty and **every** path matches `^(docs|openwiki)/` or `^[^/]+\.md$` (a root-level `.md`) and is not one of the two carve-outs.
  - `backend`: true if any path matches one of the backend couplings: `^src/backend/`, `(^|/)requirements[^/]*\.txt$`, `(^|/)migrations/`, `^scripts/`, `^\.github/`, `^\.claude/(hooks|agents|mods)/`, `^\.claude/settings\.json$`, `^dev\.sh$`, `^THIRD_PARTY_NOTICES\.md$`, `^docs/agentic/harness\.md$`, `^src/frontend/src/components/settings/DataDonationCard\.tsx$`. A comment beside each pattern names the test that needs it (Fact 3).
  - `frontend`: any path matching `^src/frontend/`.
  - `mods`: any path matching `^\.claude/mods/`.
  - **Fail closed:** empty input, or any line that is absolute, contains `..` or a backslash, or holds a control character, gives `docs_only=false backend=true frontend=true mods=true`. Any exception prints the same four lines and exits 0.

### 2. build-item: full backend suite only when the diff reaches the backend

- **Where:** `build-item.js`, beside `vitestFiles` (`:260`) and in `runTests` (`:263-278`). A new Haiku (medium) step, `scopeOf(round)`, runs exactly `git -C "<worktree>" diff --name-only --no-renames origin/main...HEAD | python3 "<worktree>/scripts/change_scope.py"`. It returns `{exit_code, output}`, with `output` verbatim. The step only runs a script, so it fits the Haiku (medium) role (MODEL-ROUTING-SONNET-IMPL). A new self-contained pure `function parseScope(text)` returns `{docs_only, backend, frontend, mods}` only when the text is exactly those four `key=true|false` lines, and `null` otherwise. `runTests` calls `scopeOf` first on every call, because each fix round changes the diff.
- **Rule** (decided in JS, fail closed): `const s = scope && scope.exit_code === 0 ? parseScope(scope.output) : null`.
  - Step 3 (the full suite, `:269`) runs **unless** `s && s.backend === false`. When it is skipped, the prompt says `SKIPPED-SCOPE (change_scope: backend=false; CI Backend Tests runs the full suite on this PR)`, and the runner lists it as such. It does not count against `all_passed`.
  - Steps 1 (focused tests), 2 (`--collect-only`, so the count and its delta are always measured), 4 (acceptance) and 5 (`docs_lint.py`) always run.
  - When `!s || s.frontend`: vitest runs for the changed test files, as today (`:266`, `:273`), plus `npx tsc --noEmit` from `src/frontend` (RUNBOOK §6 step 5; the WSL `/mnt/` skip rule at `:273` still applies).
  - When `!s || s.mods`: `claude plugin validate .claude/mods/asclexis-rsi` and `claude plugin test .claude/mods/asclexis-rsi` run.
  - The scope output is pasted into the test evidence (`testEvidence`, `:296`), so Review and Verify see it.
- **Verify** (`:357`) re-runs the same scope command itself. If it prints `backend=true` (or fails) and the evidence has no full-suite run, Verify returns FAILED and blocks the item (RUNBOOK §8). An Opus check of a Haiku decision is a lead made into a finding.
- **Never weaker than CI:** every non-docs PR still runs Backend Tests in CI (Design §1). Locally, the full suite is skipped only for diffs that no backend test reads (Fact 3). Rows such as `.claude/workflows/*.js` and `src/frontend/**` save about 8 min each.

### 3. build-item: the small-row fast lane

- **How a row is marked:** no new queue field. A row qualifies only from its existing cells, as returned by Opus Task 0. L0 opts in per run with `{"id": "<ID>", "fast": true}`; the arg validation sits next to `resume_pr` (`:26-31`). build-wave and build-program never pass it (a later row may).
- **`fast: true` changes exactly one thing: Explore is skipped.** The Plan-check prompt (`:145-155`) gains a step 0 (fast only): read the row from `git show origin/main:<QUEUE>` and copy its cells, as Explore steps 2-7 do (`:112-117`). Return `row: {found, repo_root, kind, runtime, est_h, ask_first, owner_gates, files, spec_paths, acceptance_commands, contracts, architectural, security_sensitive}` in `PLANCHECK_SCHEMA` (`:54-69`, optional `row`). **Before claiming**, apply the `:122-134` refusals (not found, owner or model-machine, runtime), quoted into the prompt. Then JS sets `spec = plan.row` and re-applies the same refusals itself. If one fires after a claim, `block()` the PR and stop.
- **Eligibility** (a new self-contained pure `function fastLane(row)`, `{ok, why}`), all of:
  - `est_h` matches `^\s*\d+(\.\d+)?\s*$` and is ≤ 0.5. `0.5 (+0.5 Task 3)` does not qualify.
  - The row lists 1 or 2 files after `be/` and `fe/` expansion, not counting `slots`.
  - The `ask-first` cell is `—`, `-`, `none` or empty.
  - `architectural` is false and `security_sensitive` is false.
  - `kind` does not match `/OWNER|HARNESS|RSI|safety|privacy|audit|security|ask-first/i`.
  - No file matches `SAFETY_RE`: `/(redaction|interpret_safety|faithfulness|verifier_agent|auth|encrypt|security|export|external_runner|audit|logging|session_log|migrations\/|^\.github\/|^scripts\/|^\.claude\/|owner-decisions|(^|\/)(CLAUDE|AGENT)\.md$)/i`.
- **What changes for an eligible row:** nothing after Plan check. Review keeps exactly the `:317-318` lens code. An eligible row is never security-sensitive, so it gets the single spec lens, as any non-security row does today. Owner SPEEDUP-1-3's "one Opus review instead of two" is therefore already true for such rows; the fast lane makes it hold by exclusion and does not delete a lens. `MAX_ROUNDS` (`:19`), Task 0 checks 1-7, the test stage (with §2's scope rule), Verify and every gate are unchanged.
- **A row that fails `fastLane`** after a fast Task 0 is logged `fast lane: not eligible (<why>)`. It continues on the normal path with `spec = plan.row`. Its `security_sensitive` is the OR of Task 0's flag and a `SAFETY_RE` hit, so the security lens is never dropped. The Explore stage adds nothing for it, because Opus Task 0 has already read the row.
- **Expected saving:** for a 0.5 h, 2-file row, about 20 of 35 min (explore plus the full suite). Acceptance measures it on the next two fast rows.

### 4. Resume and retitles that auto mode denies (L0 duty #2, the build-item half)

- The resume identity check (`:150`) also accepts a title starting `[claim:claude` when the newest comment after the stop or escalation comment has a first line starting `L0 ruling: preflight retitle`. In that case Task 0 skips step (d) and its own retitle, and still runs (a) the lock check, (c) the slot check and (e) the race re-check. The branch, not-merged and worktree checks are unchanged.
- `block()` (`:196-206`), the escalation (`:340-348`) and Verify step 5 (`:360`) say: if `gh pr edit` (and the `gh api` fallback, `:361`) is refused by the permission system, do not retry another way. Write `retitle: L0 → <exact title>` in the result, and L0 retitles from the main session. This mirrors GH-READY-REFUSED (`RUNBOOK.md:162`).

### 5. Planner checklist in the planner prompt (#4)

The checklist text is in RUNBOOK §10.1 ("Planner checklist", this docs PR). `build-program.js:177` gains one sentence: "Before marking a row ready, apply the RUNBOOK §10.1 planner checklist and say in the row which parity, guard and isolation tests you found." The unblock prompt (`:116`) gains the same clause for plan deltas.

## Tasks (test-first)

0. **Task 0 (Opus).** Re-anchor every `file:line` on the start commit. Re-measure the required checks (`gh api repos/BrooklynD23/HealthCentral/branches/main/protection --jq .required_status_checks.contexts`) and paste them. If the list now holds a job this row skips other than Backend Tests, Frontend Tests or Agent Eval Gate, keep going, since the pattern reports Success, and say so. If it holds `Change Scope`, stop and tell L0. Re-run the Fact 3 grep (`grep -rnE "parents\[[2-9]\]|REPO_ROOT|repo_root|\.\./\.\." src/backend/tests`) and list every read outside `src/backend/`. Each one becomes a `backend` coupling, or stops the row if it lies under `docs/` beyond the two carve-outs. Then a new docs-lint step is needed, and L0 rules. Quote SPEEDUP-1-3.
1. **RED: scope rule.** New `src/backend/tests/test_change_scope.py`, which runs the script by subprocess, as `test_docs_lint.py` does. RED: the script is missing.
   - **HC-SCOPE-001:** docs only (`docs/plans/x.md`, `openwiki/README.md`, `README.md`, `CLAUDE.md`) gives `docs_only=true backend=false frontend=false mods=false`.
   - **HC-SCOPE-002:** carve-outs. `docs/agentic/harness.md` gives `docs_only=false backend=true`, and `THIRD_PARTY_NOTICES.md` gives the same.
   - **HC-SCOPE-003:** every backend coupling gives `backend=true`. It is a table with one path per pattern, including `.claude/mods/asclexis-rsi/hooks/logic.ts` (HC-SLOG-004, the #429 stop), `.claude/hooks/session_log.py`, `.claude/settings.json`, `scripts/docs_lint.py`, `.github/workflows/ci.yml`, `src/backend/requirements.txt`, `dev.sh`.
   - **HC-SCOPE-004:** `src/frontend/src/App.tsx` gives `frontend=true backend=false`. `DataDonationCard.tsx` gives `frontend=true backend=true`.
   - **HC-SCOPE-005:** `.claude/mods/asclexis-rsi/rsi.test.ts` gives `mods=true backend=true`.
   - **HC-SCOPE-006:** `.claude/workflows/build-item.js` alone gives all `false`. Mixed `docs/x.md` + `src/backend/main.py` gives `docs_only=false backend=true`.
   - **HC-SCOPE-007:** fail closed. Empty stdin, `../x`, `/abs/x`, `a\tb` and `a\\b` each give `docs_only=false backend=true frontend=true mods=true`.
2. **RED: CI wiring.** **HC-SCOPE-008** in the same file loads `ci.yml` with `yaml.safe_load` (PyYAML, as `test_claude_agent_definitions.py:24`) and checks:
   - PyYAML reads the bare `on` key as `True`, so the test reads `data.get('on', data.get(True))`. That trigger holds no `paths` and no `paths-ignore`.
   - A `changes` job exists. Its step text has `--no-renames`, `HEAD^1` and `scripts/change_scope.py`, and its checkout has `fetch-depth: 2`.
   - `backend-tests`, `frontend-tests`, `agent-evals` and `legacy-evals` each have `changes` in `needs`, and an `if` equal to the exact fail-closed string in Design §1.
   - The `if` of `e2e-tests` requires `frontend-tests` and `backend-tests` success.
   - `docs-lint` and `security-scan` have neither `if` nor `needs`.
   - docs-lint has a `generate_docs_index.py --check` step **before** the regenerate step, and a `harness_drift_check.py` step.
   
   RED: there is no `changes` job.
3. **GREEN.** `scripts/change_scope.py`; the `ci.yml` edits (the `changes` job; `needs` + `if` on the 5 jobs; 2 docs-lint steps). Run actionlint (pinned release binary under `/tmp/claude-1000`; if it cannot be fetched, record it as NOT RUN with the reason; HC-SCOPE-008 and `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml'))"` still run).
4. **RED → GREEN: build-item.** Scratch node fixture (the lane E §2.17 / §2.25a pattern; the fixture stays scratch because OQ-HI-FIXTURE (a) licensed a committed fixture for the rsi-loop gate only, `owner-decisions-2026-09-27.md:449`). `sed -n '/^function parseScope/,/^}/p'` and `sed -n '/^function fastLane/,/^}/p'` from `build-item.js` go into `/tmp/claude-1000/speedup-fixture/`, and a node script asserts:
   - **(a)** `parseScope`: the four lines in any order give the object; a missing key, `backend=False`, an extra line, `''` and `null` each give `null`.
   - **(b)** the full-suite rule (a pure helper `fullSuite(scope)` = `!(scope && scope.exit_code === 0 && (parseScope(scope.output) || {}).backend === false)`, also extracted): `backend=false` gives no full suite; `backend=true`, exit 1, garbage and `null` each give a full suite.
   - **(c)** `fastLane`: eligible `{est_h: '0.5', files: ['fe/pages/X.tsx', 'fe/__tests__/X.test.tsx'], ask_first: '—', kind: 'PRODUCT (code)', architectural: false, security_sensitive: false}` gives ok. Each of these gives not ok, one per rule: `est_h` `'0.75'`, `'0.5 (+0.5 Task 3)'` or `''`; 3 files; 0 files; ask-first `` `be/modules/redaction.py` called only ``; file `be/core/audit.py`; file `.claude/workflows/x.js`; kind `HARNESS`; kind `PRODUCT (code; safety-adjacent, audit)`; `security_sensitive: true`; `architectural: true`.
   
   RED on `main`: both `sed`s print nothing. GREEN: `scopeOf`, `parseScope`, `fullSuite`, `fastLane`; the `runTests` step 3 / frontend / mods conditions; the Verify re-check; the fast Task 0 step 0 and `row`; the Design §4 resume and retitle sentences.
5. **Docs.**
   - `build-program.js:177` and `:116`: one sentence each (Design §5).
   - RUNBOOK §6 step 2 (`:135-140`): the full suite runs when `change_scope.py` prints `backend=true`, else the paste is the scope output plus `SKIPPED-SCOPE`.
   - RUNBOOK §10.1 (`:212-214`): a `fast` bullet and a scope bullet.
   - AGENT.md Definition of done (the pytest bullet): one clause: for a diff `scripts/change_scope.py` reports as `backend=false`, the PR's CI Backend Tests run is the full-suite evidence (owner SPEEDUP-1-3).
   - `docs/architecture/ci-and-quality-gates.md`: the `changes` job, the skip set, the two new docs-lint steps, the skipped-is-Success note, Last Updated.
   - Regenerate the docs index.

## Acceptance

- `pytest tests/test_change_scope.py`: RED pasted (8 failing), then `8 passed`. The full backend suite passes (this diff touches `scripts/` and `src/backend/tests/`, so its own scope is `backend=true`). Collected delta **+8**.
- `python3 scripts/change_scope.py` on this branch's own diff prints `docs_only=false` (the PR is code, so every CI job runs on it, including the full suite).
- The scratch node fixture prints `speedup ok (N)`, with its RED pasted. actionlint is clean, or NOT RUN with the reason. HC-SCOPE-008 is green.
- `git diff origin/main -- .github/workflows/ci.yml` shows only: the `changes` job; `needs:` + `if:` lines on backend-tests, frontend-tests, agent-evals, legacy-evals and e2e-tests; the 2 docs-lint steps. No step of an existing job is removed or changed. `git diff origin/main -- .claude/workflows/build-item.js` leaves `MAX_ROUNDS`, the lens code `:317-318`, `ARG_OK` / `buildMeasureCmds` (`:227-238`) and the Task 0 checks text unchanged.
- **Post-merge (L0, before any later docs PR merges):**
  - On the first docs-only PR, `gh pr checks <n>` shows Backend Tests, Frontend Tests and Agent Eval Gate as skipped/pass, with Documentation Lint, Security Scan and Change Scope run. `gh pr view <n> --json mergeStateStatus` is not `BLOCKED` on a check.
  - On the first code PR after merge, every job runs.
  - If a required check sits at Pending/Expected, L0 opens a revert PR at once. The revert is a code PR, so it runs everything.
  - L0 records the wall time of the next two fast-lane items next to the 35 min baseline.

## Risk

- **Never weaken a gate.** The code path still runs every job. Only a PR whose every path is docs and not carved out skips anything, and only after `changes` succeeded. Every failure of the scope machinery runs more, not less. The committed-index and drift checks move into a job that always runs, so docs-only PRs lose no check that a Python stdlib step can make. The two that need the full test environment are carved out.
- **Residual:** a backend test added later that reads a new path under `docs/` would not run on a docs-only PR. The RUNBOOK §10.1 planner checklist and HC-SCOPE-003's table are where that coupling must be added. Task 0 re-greps.
- **Residual:** a run cancelled by hand leaves jobs skipped or cancelled. L0 never merges on a cancelled run (RUNBOOK §7 rule 6: CI green).
- `ci.yml` is a gate file. It is approved by owner SPEEDUP-1-3, and the merge waits on SPEEDUP-CI-DIFF: L0 shows the owner the `ci.yml` diff before merge.

**Files:**
- `scripts/change_scope.py` (new)
- `src/backend/tests/test_change_scope.py` (new, HC-SCOPE-001…008)
- `.github/workflows/ci.yml` (new `changes` job; `needs` + `if` on backend-tests `:38`, frontend-tests `:96`, agent-evals `:205`, legacy-evals `:229`, e2e-tests `:253-256`; docs-lint 2 steps around `:21-24`)
- `.claude/workflows/build-item.js` (args `:26-31`; `PLANCHECK_SCHEMA` `:54-69`; Explore `:108-124` skipped under `fast`; refusals `:126-135`; Plan check `:145-155`; new `scopeOf`, `parseScope`, `fullSuite`, `fastLane` near `:260`; `runTests` `:263-278`; `testEvidence` `:296`; `block` `:196-206`; escalation `:340-348`; Verify `:357`, `:360`)
- `.claude/workflows/build-program.js` (`:116`, `:177`, one sentence each)
- `docs/plans/2026-10-15-build-program/RUNBOOK.md` (§6 step 2 `:135-140`; §10.1 `:212-214`)
- `AGENT.md` (Definition of done, one clause)
- `docs/architecture/ci-and-quality-gates.md`
- `docs/INDEX.md`, `docs/_link_graph.json` (regenerated), slots (none edited)

**Est:** 3.5 h. **depends_on:** —. **Order:** first, ahead of RSI-OWNER-NOTES (resume #439), INTERP-WITHHOLD-MSG Task 3 (#433), RSI rows E-H and the quiet-box chain, because every later item benefits. It is file-disjoint from #439, #440 and #433, so it may run beside them. **Never beside:** another PR on `.github/workflows/ci.yml` (RSI-GATE-ADVERSARIAL adds a `rsi-replay` step and goes after this row) or on `.claude/workflows/build-item.js` / `build-program.js`. While this PR is open, no `build-program` run is started from a checkout that has it; L0 pulls `main` only between runs. **Owner gates:** SPEEDUP-1-3 (answered 2026-11-01: #1 and #3); merge-only **SPEEDUP-CI-DIFF** (L0 shows the `ci.yml` diff to the owner before merge). **Stops:**
- a required check that would stay Pending;
- a coupling under `docs/` that no stdlib step can cover;
- any change to an existing job's steps;
- any need to edit branch protection (RUNBOOK §7 rule 6; only the owner changes it).

**Runtime:** claude. **Kind:** HARNESS (CI, workflow scripts, one script and one backend test; no slot).
