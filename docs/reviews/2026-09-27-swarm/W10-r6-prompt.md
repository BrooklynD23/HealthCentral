You are a READ-ONLY adversarial reviewer for an implementation plan in the Asclexis repo (local-first medical-results app; FastAPI + per-profile SQLCipher vaults + React/TS). Working dir: /mnt/c/Users/DangT/Documents/GitHub/hc-w10 (a git worktree on branch `docs/w10-governance-amendments`; HEAD = the r5 plan-amendment commit on top of `origin/main` `777adf5`). Reasoning effort: HIGH.

DO NOT edit, create, stage or commit any file. Do not run git write commands. Read code and docs; run read-only commands (grep, git show, git grep, git diff, cat) only.

PLAN UNDER REVIEW: docs/plans/2026-09-27-W10-governance-invariant-amendments.md (as amended by r5; `git diff origin/main -- docs/plans/2026-09-27-W10-governance-invariant-amendments.md` shows the amendment)
ROUND: 6 (second and LAST round on the r5 amendment set)
PRIOR ROUND FINDINGS AND L1 RESPONSES (round 5, `audit/2026-09-25/swarm-2026-09-27/reviews/W10-r5-codex.txt` and `W10-r5-response.md`; verify each was actually fixed in the plan at HEAD; re-raise if not):
1. [BLOCKER] Task 0 Step 1 `git worktree add` on an existing worktree/branch -> ACCEPTED: Step 1 reuses the worktree if it exists, adds it only if absent.
2. [MAJOR] green gates can finish successfully after a failure; pytest piped through `tail` -> ACCEPTED: Task 4b Step 5 uses `set -euo pipefail`, one gate per line, `ALL GREEN` last; collect/pytest pairs write full output to a file and print the exit code.
3. [MAJOR] HC-1 "JSON `details_json` field" vs SQL `Text` -> ACCEPTED: "a text `details_json` column that holds serialized JSON".
4. [MAJOR] W10-A3 / W10-F2 could pass on wrong text -> ACCEPTED: A3 reads only the "Optional External API" subsection and requires the full clause with both conditions; F2, F3, F4 assert the full replacement rows.
5. [MINOR] Task 3 Step 5 expectation -> ACCEPTED: one sentence, `5/9` with A3, A6, A7, A8 failing.
Also re-check everything in the list below once more; this is the last round before the hunks are applied.

Binding references (read the parts the plan relies on):
- CLAUDE.md, AGENT.md, docs/agentic/recurring-failures.md
- docs/capstone-report/owner-decisions-2026-09-27.md (approval text is VERBATIM scope; anything wider is owner-gated). Rows that govern this phase: D3, D4, D11, D12, GOV-BG / GOV-D11, W-10-REST, W10-Q4 / W10-Q5, W10-HIPAA, and Consequences #1 and #5.
- docs/capstone-report/implementation-program.md (owner items LOCAL-07, DOC-OVERCLAIM, CLAUDE-FAILURE-COUNT), architecture-engineering-contract.md, specs-compliance-matrix.md (rows LOCAL-04, LOCAL-07, PRIV-04, AUD-04, AUD-05, AUD-08)
- audit/2026-09-25/waves/scaffold/W-10.md (readiness pack: leads, not facts)
- All code is at the current HEAD of this worktree (= `origin/main` `777adf5` for every non-plan file). The files the plan will edit: `CLAUDE.md`, `docs/compliance/data-privacy.md`, `docs/compliance/hipaa-controls.md`.

This is a DOCS-ONLY, ARCHITECTURAL phase: it rewrites the repo's hard invariants and privacy claims for a health app used by real patients. The standard is: every sentence the plan will land states only what the code does today and only what the owner signed. Attack the plan against the CODE, not just its prose. Check at minimum:
1. Every After block (C-1, C-2 GOV-BG-signed, C-3, DP-1 P, DP-2 P, DP-3 P, DP-4 U GOV-BG-signed, DP-5, DP-6, HC-1, HC-2, C-5): for each sentence that describes code behaviour, open the code and say whether it is true. Key files: `src/backend/core/external_runner.py` (strict redaction, break-glass predicate, audit row), `src/backend/modules/redaction.py` (rules per policy level), `src/backend/modules/rag.py` (prompt composition, context labels, `validate_response`), `src/backend/api/assistant.py` and `api/interpretations.py` (which routes pass the external runner), `src/backend/api/export.py`, `modules/export.py`, `modules/fhir_export.py`, `modules/rl_dataset.py`, `api/pinboards.py`, `api/backup.py` (which exports are redacted), `src/backend/models/audit.py`, `core/audit.py`, `api/profiles.py` (audit rows), `security/audit_middleware.py`, `core/logging_setup.py`, `alembic.ini` (log sinks and levels), `src/frontend/src/components/settings/ExternalApiBreakGlassWarning.tsx`.
2. Scope: does any After block state an exception, a "must", or a protection wider than the verbatim owner text? Does any sentence weaken an invariant, or replace one overclaim with another? Is `hipaa-controls.md:169` untouched, the Local-first line (`CLAUDE.md:59`) untouched, the `CLAUDE.md` count slots (`:30`, `:35`) untouched? Is any legal / HIPAA-compliance conclusion made?
3. Every Before block matches the target file exactly once at HEAD (the 8 original anchors and the 6 fold-in anchors).
4. Every path:line the r5 text cites (§3.2 r5 rows, §3.6) exists and says what the plan claims (spot-check all the safety-critical ones).
5. The assertion scripts (`w10_assert.py`, `w10_foldin_assert.py`): would each assertion fail before the change and pass after it, with `W10_ARGS=" --c3 --govbg"`? Can any pass while the text is wrong (recurring-failures #1)?
6. Internal consistency: does any older paragraph still instruct the executor to do something r5 forbids (apply C-4, use a DP-4 variant-P block, one commit, tick a box, run the full suite)?
7. Executability: commands runnable as written (recurring-failures #6); explicit pathspecs; no `git add -A`; stop gates present.

OUTPUT FORMAT (exact):
VERDICT: PASS | REVISE
Then one line per finding:
[BLOCKER|MAJOR|MINOR] <plan path:line> — <defect> — evidence: <code path:line or command + output> — fix: <concrete change>
BLOCKER = unsafe, violates an invariant/approval, or the plan cannot work. MAJOR = a wrong fact, a test that cannot fail, a missing dependency/gate, or a step that would mislead an executor. MINOR = clarity/nits.
PASS only if there are zero BLOCKER and zero MAJOR. No preamble. End with one line `MODEL / EFFORT: <what your runtime reports>`. Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd).
