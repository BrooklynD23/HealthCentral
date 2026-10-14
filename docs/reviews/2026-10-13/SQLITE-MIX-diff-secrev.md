# SQLITE-MIX diff — security review

Reviewer: security-reviewer subagent (Opus 5.5), read-only, 2026-10-13. Reviewed the diff before the M2 fix and comment correction (see the response file).

**Verdict: APPROVE WITH NITS.** No CRITICAL or HIGH findings. The encryption guarantees hold, no new key material is exposed, and the test fixture change is a fidelity fix. 2 MEDIUM and 3 LOW findings.

The reviewer did not run pytest. The SQLAlchemy and SQLCipher behaviour below comes from reading the code, not from running it.

## The 5 checks

1. **Encryption is still guaranteed.** `async_creator` only replaces how the raw connection is built. The pool's `connect` event still fires on every new connection, so `set_sqlite_pragma` (`core/profile_database.py:330`) still runs `PRAGMA cipher_version` and then `PRAGMA key` before any use. When sqlcipher is available, every profile connection uses sqlcipher3, with no fallback to stdlib. When sqlcipher is unavailable, no creator is set and the existing raise (required) or warn (not required) branch is unchanged. Key handling, PRAGMA order and KDF are untouched. The creator closure captures only `db_path` and the module.
2. **No new key exposure.** `hex_key` was already captured by the listener closure. `conn._thread.daemon = True` matches what SQLAlchemy did on the old path. Backups never open a vault with a key.
3. **The backup cannot alter the live vault.** A keyless open can only write by rolling back a hot journal. With the same SQLite library as the app, it now sees the writer's lock and no longer rolls back a live journal. Rolling back a journal left by a real crash copies encrypted pages back raw, as stdlib did before. `to_thread` brings one new concurrency risk (M2).
4. **The fixture change is a fidelity fix.** The assertion at `tests/test_backup_api.py:495` is unchanged. The backup API rewrites the library version number in the file header, so a stdlib-created file backed up through sqlcipher3 differs in those header bytes for a reason unrelated to restore. When sqlcipher is missing, the fixture falls back to stdlib. Caveat: the fixture vault is plaintext both before and after (M1).
5. **Other CRITICAL/HIGH:** none.

## Findings

| # | Sev | Location | Issue | Fix |
|---|-----|----------|-------|-----|
| M1 | MEDIUM (existed before) | `scripts/backup.py:178-190` | Opening an encrypted vault without the key fails with NOTADB once the lock is free, and the code falls back to `shutil.copy2` without holding a lock. A commit during the copy can leave a torn backup. The `api/backup.py` comment "waits on a live write's lock" is only half true. | Follow-up, needs owner sign-off because it touches key use: snapshot from the keyed engine. For now, correct the comment. |
| M2 | MEDIUM (new) | `api/backup.py:259`, `modules/backup_scheduler.py:132` | With `backup()` off the event loop, two backups can run at once. The backup dir name has 1-second resolution with `exist_ok=True`, so two runs in the same second write into the same directory. | Add a lock, or make the dir name unique. |
| L1 | LOW | `scripts/backup.py:180-182` | `Connection.backup()` retries BUSY forever. A stuck writer pins the worker thread. | Add a deadline through the `pages`/`progress` arguments. |
| L2 | LOW | `scripts/backup.py:180-185` | `src_conn` and `dst_conn` are not closed on exception. | Use `closing` or `try/finally`. |
| L3 | LOW | `requirements.txt:28` | The pin also applies to the master engine. In 0.22, `Connection` is not a Thread. | Check what CI resolved before this change. |
