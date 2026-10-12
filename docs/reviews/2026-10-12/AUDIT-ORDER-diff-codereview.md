# AUDIT-ORDER — code review of the execution diff

**Reviewer:** code-reviewer agent (Opus 5.5), read-only, 2026-10-12, at `5aa8450`. Ran single files: `test_audit_order.py` 54 passed, `test_audit_order_guard.py` 4, `test_denial_audit.py` 6, `test_documents_api.py` 19, `test_pinboards.py` 13, `test_profile_deletion.py` 21.

**Verdict: APPROVE**, 0 CRITICAL, 0 HIGH, 4 MEDIUM, 7 LOW. Ordering verified route by route: on rows 2, 5, 10, 13, 16, 19/20/23, 26, 27 nothing irreversible precedes the committed `started` row; row 28 commits outside the fallback `try`. Changed old tests: none weakened (HC-DDI-002 is stricter).

| # | Sev | file:line | Issue | Suggested fix |
|---|---|---|---|---|
| 1 | MEDIUM | `tests/test_audit_order_guard.py:168` | Dynamic-call check scans only handlers already seen as committing; a handler whose only commit is behind an unresolvable callable is never checked | Scan `_REACH` for every handler; flag def references passed as call arguments |
| 2 | MEDIUM | `tests/support/callgraph.py:118-133` | `unscoped_vault_writes` is satisfied by any reachable commit, including the master commit in `audit_and_commit` | Require a commit on the vault receiver |
| 3 | MEDIUM | `tests/test_audit_order_guard.py` | The 3 plan break-its are not committed as tests | Parametrised tests over a tmp tree with the 3 dummy handlers |
| 4 | MEDIUM | `core/denial_audit.py:42-46` | Fixed window, not rolling; the suppressed count of a final burst is never written | Document the ceiling (comment + plan) or flush |
| 5 | LOW | `core/denial_audit.py:44-49` | Window reset after an await (duplicate `suppressed` rows under concurrency); cap slot used by a failed write | Update state before the await, restore on failure |
| 6 | LOW | `api/profiles.py:937,961` | `audit_rows_purged` now includes the `started` row (+1) | Subtract 1 or note it |
| 7 | LOW | `api/interpretations.py:416,477` | Check-then-act between `_has_interpretation` and the module call | Accept with a `ponytail:` note |
| 8 | LOW | `api/assistant.py:818` | On `agent_failed`, agent rows already added still depend on a later commit | Commit or roll back in the `except` |
| 9 | LOW | `tests/test_audit_order.py:772` | Profile-delete 001a does not assert `revoke_jwt_token` was not called | Add the assertion |
| 10 | LOW | `tests/test_audit_order.py` | No batch 001b/002; no restore-partial ordering case | Add them |
| 11 | LOW | `CLAUDE.md`, plan §13 | Collected count and §13 checkboxes not updated | T8 |
