You are a READ-ONLY adversarial reviewer for an implementation plan in the Asclexis repo (local-first medical-results app; FastAPI + per-profile SQLCipher vaults + React/TS). Working dir: /mnt/c/Users/DangT/Documents/GitHub/HealthCentral. Reasoning effort: HIGH.

DO NOT edit, create, stage or commit any file. Do not run git write commands. Read code and docs; run read-only commands (grep, git show, git grep, git diff, cat) only.

PLAN UNDER REVIEW: docs/plans/2026-09-27-W10-governance-invariant-amendments.md
ROUND: 3
PRIOR ROUND FINDINGS AND ORCHESTRATOR RESPONSES (verify each was actually fixed in the plan; re-raise if not):
R1 (codex) dispositions:
1. [BLOCKER] export inventory misses multiline `/feedback/export` (api/feedback.py:306 @B, mounted api/__init__.py:58) -> ACCEPTED. Orchestrator verified: route exists; docstring says it applies RedactionEngine and requires confirmed=true (feedback.py:1-12, :319). Fix: inventory mounted routes with a multiline-aware method (e.g. python ast over api/*.py for router decorators, or `git grep -n -A3 "@router\."`); classify /feedback/export from CODE evidence (verify the redaction call path in modules/rl_dataset, not the docstring); DP-2 covers every export-shaped route; S5 stops on any unclassified one.
2. [MAJOR] GREEN/break-it commands hard-code --c3 and omit Q2 flag -> ACCEPTED: one ARGS variable derived from signed Q1–Q3, used by every assertion run.
3. [MAJOR] implemented-variant selection needs only IDs + passing -> ACCEPTED: variant I requires the W-item PR's recorded red-first output + break-it evidence (+ route_client for routes); otherwise variant "approved, not yet implemented".
Also fix the broken DOC-007 link "-> target" in your plan, and the ownership ruling: if Q1 is unsigned, CLAUDE.md:62 stays unchanged and becomes an open owner item — it does NOT go to P4 (fix plan :52). Apply reviews/GLOBAL-rules.md.
R2 (codex) dispositions:
1. [MAJOR] file-wide route_client grep -> ACCEPTED: verify the specific HC test function calls route_client (AST or function-scoped grep) and record the call line as evidence.
2. [MAJOR] merged-without-evidence keeps "not yet implemented" -> ACCEPTED: label "merged; conformance unverified" until the variant-I evidence exists.

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
