You are a READ-ONLY adversarial reviewer for an implementation plan in the Asclexis repo (local-first medical-results app; FastAPI + per-profile SQLCipher vaults + React/TS). Working dir: /mnt/c/Users/DangT/Documents/GitHub/HealthCentral. Reasoning effort: HIGH.

DO NOT edit, create, stage or commit any file. Do not run git write commands. Read code and docs; run read-only commands (grep, git show, git grep, git diff, cat) only.

PLAN UNDER REVIEW: docs/plans/2026-09-27-W08-bundled-embedding-model.md
ROUND: 4
PRIOR ROUND FINDINGS AND ORCHESTRATOR RESPONSES (verify each was actually fixed in the plan; re-raise if not):
R1 (codex) findings and orchestrator dispositions:
1. [MAJOR] interpret-grounded 501 not tested over HTTP -> ACCEPTED. Fix: route_client test for POST /interpretations/observations/{id}/interpret-grounded asserting 501 and the fixed detail (no file path), plus break-it on the route mapping. Keep Q-FC owner gate on the wording.
Also apply repo-wide executability rules: absolute WT path, no relative cd after cd, pipefail/PIPESTATUS for piped exit codes, count updates in the same commit that changes collection.
R2 (codex) dispositions:
1. [BLOCKER] downloader rm -r of an existing `<target>.partial` -> ACCEPTED. Refuse (exit non-zero with a message) if `<target>.partial` already exists; only delete a .partial this run created (e.g. created via mkdir exclusive in this run). Add HC-EMB test for a pre-existing .partial (not deleted, command fails).
2. [BLOCKER] worktree at origin/main fails ancestry check -> REJECTED as a defect: this is the intended STOP until P1 is merged. Fix wording: add explicit "Prerequisites: P0-B and P1 merged to origin/main" at top and in Task 0.
3. [MAJOR] route break-it edits read-only api/interpretations.py with git checkout -- -> ACCEPTED: monkeypatch the mapping or use a disposable detached worktree.
R3 (codex) dispositions — POST-ROUND-3 fixes (review budget exhausted; escalated to owner for optional round 4):
1. [MAJOR] a transient snapshot_download error leaves this run's .partial, blocking the next run -> ACCEPTED: wrap the fetch; on any exception remove the .partial only if this run created it, then re-raise; add a test where the fake downloader raises: this run's partial is removed, a pre-existing partial is preserved (existing HC-EMB-004d).
Add a line near the top: "Review status: 3 Codex rounds; round-3 MAJOR fixed after the last round, not re-reviewed (owner may request round 4)."

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
