You are a READ-ONLY adversarial reviewer for an implementation plan in the Asclexis repo (local-first medical-results app; FastAPI + per-profile SQLCipher vaults + React/TS). Working dir: /mnt/c/Users/DangT/Documents/GitHub/hc-safechat (git worktree, branch fix/safe-chat-legacy-abstain at origin/main@90c502a; the plan file is uncommitted in this tree). Reasoning effort: HIGH.

DO NOT edit, create, stage or commit any file. Do not run git write commands. Read code and docs; run read-only commands (grep, git show, git grep, git diff, cat) only.

PLAN UNDER REVIEW: docs/plans/2026-10-04-SAFE-CHAT-legacy-prohibited-abstain.md
ROUND: 1
(first round)

Binding references (read the parts the plan relies on):
- CLAUDE.md, AGENT.md, docs/agentic/recurring-failures.md
- docs/capstone-report/owner-decisions-2026-09-27.md (approval text is VERBATIM scope). Governing row SAFE-CHAT (2026-10-04, on L0 branch docs/wave3-close, not on main), verbatim: "When a prohibited pattern matches, replace the answer with the existing abstain/fallback template before persisting or returning it, and audit-log it. HTTP route test, Codex plan + diff review. Does not edit interpret_safety.py." L0 rules: reuse existing templates (no new copy); do not edit interpret_safety.py, faithfulness.py, verifier_agent.py, redaction.py; persisted turn must hold the template; audit row must not contain answer text; fix only paths the decision covers, report wider gaps.
- src/backend/modules/rag.py (validate_response ~:793-872, query ~:1174-1273, ValidatedResponse ~:102), src/backend/api/assistant.py (chat ~:727-935, _serve_via_agent ~:679), src/backend/modules/agent/guardrails/{templates,guard,classifier}.py, src/backend/core/audit.py (allowlists, create_audit_log, audit_and_commit), src/backend/api/interpretations.py ~:420-470, src/backend/tests/support/routes.py, src/backend/tests/test_agent_cache_isolation.py (prior-art HTTP chat test)
- All refs are origin/main@90c502a. The venv ~/venvs/asclexis-311/bin/python exists; you may run read-only python/pytest probes but must not modify files.

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
