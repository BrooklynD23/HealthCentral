You are a READ-ONLY adversarial reviewer for an implementation plan in the Asclexis repo (local-first medical-results app; FastAPI + per-profile SQLCipher vaults + React/TS). Working dir: /mnt/c/Users/DangT/Documents/GitHub/HealthCentral. Reasoning effort: HIGH.

DO NOT edit, create, stage or commit any file. Do not run git write commands. Read code and docs; run read-only commands (grep, git show, git grep, git diff, cat) only.

PLAN UNDER REVIEW: docs/plans/2026-09-27-W01-harness-agents-branch-a.md
ROUND: 4
PRIOR ROUND FINDINGS AND ORCHESTRATOR RESPONSES (verify each was actually fixed in the plan; re-raise if not):
R1 (codex) findings and orchestrator dispositions:
1. [BLOCKER] Task 1 widens harness_drift_check to skip all leading-slash tokens -> ACCEPTED. Weakening a check to pass is forbidden (CLAUDE.md §3), and D1 does not license checker edits. Resolution: DELETE Task 1's checker edit and HC-AGENTS-009. The false positive comes from A's docs/agentic/recurring-failures.md:33 (`GET /profiles/`), which is one of P1's 5 conflicted files; the orchestrator is adding "drift check exits 0 on the merged tree" to P1 acceptance, resolved in P1's conflict resolution (doc wording, e.g. `GET /profiles/{id}` vs list route phrased without a bare path token, or the orchestrator escalates to the owner). W-1 Task 0 gains a STOP gate: if `python3 scripts/harness_drift_check.py` is non-zero on the post-P1 tree before any W-1 change, STOP and report; do not edit the checker.
2. [BLOCKER] scanner agents' Read can reach patient data; PHI boundary is only an instruction -> ACCEPTED. Verified: patient data lives in gitignored `data/` and `*.db` in the main checkout. Fix: every agent body + harness.md usage section requires dispatch from a fresh source-only `git worktree` (which contains no `data/` or `*.db`), with a verification step (`test ! -e data && ! ls **/*.db` style check) in the smoke test; remove the "Nothing but this instruction stops you" framing and state the real boundary. Enforceable deny rules (.claude/settings.json permissions.deny for data/** and *.db) are NOT licensed by D1 -> add as an unsigned owner option.
3. [MINOR] smoke test restore -> fix with explicit-path `git status --short` + `git checkout -- README.md` in the disposable worktree.
4. [MINOR] rollback omits Task 1 -> moot after #1 (Task 1 removed); make sure rollback lists every commit.
R2 (codex) dispositions:
1. [BLOCKER] smoke check may miss data/ *.db .env in the agent worktree -> ACCEPTED (config.py:37 @B DB path data/asclexis.db). Fix: pre-dispatch gate fails if "$AGENT_WT/data", "$AGENT_WT/src/backend/data", any *.db / *.db-wal / *.db-shm, or any .env exists anywhere in the worktree (find-based); break-it: create each and show the gate fails.
2. [BLOCKER] HC-AGENTS-008 puts the drift checker into the backend CI suite without OG-3 -> ACCEPTED. Keep HC-AGENTS-008 out of the collected backend suite unless OG-3 is signed: default = run the drift check as a manual Task-level command in the PR; adding it to the suite is a separate post-OG-3 step. Adjust counts accordingly.
3. [MAJOR] count inconsistency start+8(+1) -> ACCEPTED: one consistent number derived from the final test list.
Apply reviews/GLOBAL-rules.md too.
R3 (codex) dispositions — POST-ROUND-3 fixes (owner will be asked about round 4):
1. [BLOCKER] dependency-policy-auditor scans all of src/backend incl. ask-first files while the plan calls such use owner-gated -> PARTIALLY ACCEPTED (plan inconsistency). Reading is not "touching" (CLAUDE.md §1 ask-first governs edits); the agent is read-only. Fix: make the plan consistent — remove any statement that reading ask-first files is owner-gated; in the agent body, list the ask-first paths and require any finding that would need a change there to be labelled "ASK-FIRST: owner approval required before any edit"; the agent never proposes patches to those files. Add a check (HC-AGENTS frontmatter/body test) that the ask-first list and label rule are present.
Add a line near the top: "Review status: 3 Codex rounds; round-3 findings fixed after the last round (owner decides on round 4)."

Binding references (read the parts the plan relies on):
- CLAUDE.md, AGENT.md, docs/agentic/recurring-failures.md
- docs/capstone-report/owner-decisions-2026-09-27.md (approval text is VERBATIM scope; anything wider is owner-gated). Addendum 2026-09-27: owner chose D8 delivery "Script + offline load" — "Interim: `src/backend/scripts/download_models.py` fetches it once into a local models dir; runtime loads that path with HF offline and fails closed if absent. Installer bundles it later (G-C4). No weights in git."
- docs/capstone-report/implementation-program.md, architecture-engineering-contract.md, specs-compliance-matrix.md
- audit/2026-09-25/handoff-2026-09-27-execution.md §4-§5
- Plans execute after P1 = main@40f590e + branch B `origin/claude/healthcentral-agentic-research-r1n54x`@7b2ff1f + branch A `origin/claude/asclexis-repo-audit-349pjq`@692fdf3. Read B/A versions with `git show <ref>:<path>`.

Attack the plan against the CODE, not just its prose. Check at minimum:
1. Every path:line and function name it cites exists at the ref it names (spot-check ≥8; all for safety-critical claims).
2. Scope: does any task exceed the verbatim owner approval, or edit an ask-first file (`modules/interpret_safety.py`, `redaction.py`, `faithfulness.py`, `verifier_agent.py`, anything auth/encryption incl. `core/auth.py`) without a named approval that covers that exact edit?
3. Tests: would each new test actually fail before the change (red first) and would it notice the real defect (recurring-failures #1)? Route/auth/status tests through HTTP `tests/support/routes.py::route_client`? A break-it-on-purpose step for safety tests?
4. Invariants: local-first, per-profile isolation via ProfileDbSession, redaction before leaving, audit logging, no medical advice, dual migrations, Py 3.11 target, `core.time.utcnow` naive UTC, all LLM calls via ModelRunner, no threshold lowered.
5. Measured acceptance: are numbers measured with a command (not asserted)? Are unmeasured items marked UNMEASURED? Is acceptance "collected = start + added; failures ⊆ start"?
6. Ordering/collisions: files it owns that other phases also edit (program shared-file order), and dependencies it omits.
7. Executability: could an engineer with zero context execute each step exactly as written (commands runnable from the stated directory, recurring-failures #6)?
8. Rollback and stop gates present and correct; explicit pathspecs; no `git add -A`.

OUTPUT FORMAT (exact):
VERDICT: PASS | REVISE
Then one line per finding:
[BLOCKER|MAJOR|MINOR] <plan path:line> — <defect> — evidence: <code path:line @ref or command + output> — fix: <concrete change>
BLOCKER = unsafe, violates an invariant/approval, or the plan cannot work. MAJOR = a wrong fact, a test that cannot fail, a missing dependency/gate, or a step that would mislead an executor. MINOR = clarity/nits.
PASS only if there are zero BLOCKER and zero MAJOR. No preamble. Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd).
