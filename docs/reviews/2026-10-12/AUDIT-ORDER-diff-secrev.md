# AUDIT-ORDER — security review of the execution diff

**Reviewer:** security-reviewer agent (Opus 5.5), read-only, 2026-10-12. Diff: `origin/main...fix/audit-order` at `5aa8450` (10 commits, 21 files, +1635/-78). The reviewer could not run pytest (no venv in its shell); verdict is from reading the code.

**Verdict: PASS.** 0 CRITICAL, 0 HIGH, 0 MEDIUM, 3 LOW, 3 INFO.

| # | Sev | File:line | Issue | Fix |
|---|---|---|---|---|
| 1 | LOW | `core/denial_audit.py:42-47` | `denial.suppressed` is awaited before the window is reset; two concurrent denials just after expiry can both write the summary row | Reset the window first, then write |
| 2 | LOW | `core/denial_audit.py:48-50` | `written` is incremented before the write; a failed write uses up a cap slot without a row or a suppressed count | Increment only after the write succeeds |
| 3 | LOW | `api/documents.py:1236-1244` | Reprocess `completed` row no longer carries `document.status` (§13 decision 4) | Use another allowlisted key, or accept and note |
| 4 | INFO | `core/auth.py:280-284` | Denied profile routes can wait up to SQLite's 5 s busy timeout under write contention; the 403 always stands | None |
| 5 | INFO | `core/denial_audit.py:28` | `_state` never shrinks; bounded by the number of profiles | None |
| 6 | INFO | `api/profiles.py:853-860` | If Step 6 fails after key destruction, the `started` row stays beside rows that already carry the id; a retry purges it | None |

Checks passed: no PHI or other-profile id in intent rows, batch `observation_ids` (UUID-filtered then vault-filtered), denial rows (caller id only, `entity_id` None), ERROR/WARNING logs (ids only, WARNING drops the target id); cap bounds denial rows to 20 per caller per 600 s; the denial writer never changes the 403; profile-delete crypto-erase order unchanged; restore `started` after re-auth, phrase and verify, before close/restore; no auth/encryption edit beyond `core/auth.py:278-286`.
