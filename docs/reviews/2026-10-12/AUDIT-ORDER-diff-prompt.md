# AUDIT-ORDER — Codex diff review prompt

You are reviewing branch `fix/audit-order` in this repository (read-only). Run `git diff origin/main...HEAD` to see the change. The approved plan is `docs/plans/2026-10-09-AUDIT-ORDER.md`; §13 lists the execution decisions taken. Owner sign-offs: AO-DESIGN D (two-row started/completed intent on the irreversible set, C elsewhere), AO-FAIL A (if the intent row cannot be saved, the request fails and nothing changes), AO-SCOPE B (irreversible set: §3 rows 2, 5, 10 hard, 13, 16, 19/20/23 regenerate, 26, 27, 29, 30), AD-DENIALS B (audit rows for reachable cross-profile 403s only), ask-first edits limited to `core/audit.py` (`audit_intent` only) and `core/auth.py:278-286`.

Check, adversarially:
1. On every scoped route, is the `started` row committed before the first irreversible mutation (vault write, file unlink/rmtree, key destruction, token revoke)? Is any mutation reachable before it?
2. Does any failure path leave a durable change with no audit row, or report success when the audit failed?
3. PHI: can any new row or log line carry patient content, a filename, analyte/medication names, a free-text request value, or another profile's id?
4. Do the new tests go through HTTP and would they fail if the ordering regressed? Does `tests/test_audit_order_guard.py` give false confidence?
5. `core/denial_audit.py`: cap logic, session handling, can it ever turn a 403 into another status?
6. Any edit outside the approved ask-first scope (`modules/interpret_safety.py`, `redaction.py`, `faithfulness.py`, `verifier_agent.py`, auth/encryption code other than `core/auth.py:278-286`, `models/audit.py`, migrations).

Report findings as a table: severity (BLOCKER/MAJOR/MINOR), file:line, finding, fix. End with one line `VERDICT: approve` or `VERDICT: needs-attention`.
