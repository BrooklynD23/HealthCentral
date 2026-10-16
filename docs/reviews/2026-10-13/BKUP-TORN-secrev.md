# BKUP-TORN diff — security review

Reviewer: security-reviewer subagent (Opus 5.5), read-only, 2026-10-13. Reviewed the first version of the fix (snapshotter built from a captured engine), before the finding 1 fix (see the response file).

**Verdict: REQUEST CHANGES.** One MEDIUM finding, confirmed by experiment, with a small fix. The core fix is sound: `VACUUM INTO` through the keyed engine gives an encrypted, consistent, byte-restorable snapshot, and keying is untouched.

## Findings

| # | Sev | Location | Issue | Fix |
|---|-----|----------|-------|-----|
| 1 | MEDIUM | `scripts/backup.py::keyed_snapshotter`, `api/backup.py::_vault_snapshotter`, `modules/backup_scheduler.py:134` | The engine is captured on the loop when the call starts, but it is used later, after `_BACKUP_LOCK` is acquired. If the user logs out or locks in between, `close_profile_database` calls `engine.dispose()`. SQLAlchemy then builds a new pool, so `engine.connect()` opens a **new connection, re-keyed through the `set_sqlite_pragma` closure**. The keyed connection stays open in the new pool after the engine is dropped. Experiment: fds to vault after dispose = `[]`; after snapshot + `del engine` + `gc.collect()` = `['6']`. This breaks the logout/lock promise of no residual access. | Look up the live connection on the loop inside `_snapshot`. If the profile is closed, return False and fall back to the keyless path. After `VACUUM`, check again and release the connection if the profile closed during the run. Add a test. |
| 2 | LOW | `snapshot()` `.result()` | `.result()` has no timeout while the thread holds `_BACKUP_LOCK`. A bare `loop.stop()` would hang the thread and every later backup. | `.result(timeout=…)`, then cancel the future. |
| 3 | LOW | `_backup_unlocked` vault branch | An exception from `snapshot_vault` (pool timeout, `database is locked`, disk full) escapes `backup()`. The route returns an unhandled 500 with no audit row, and a `backup_*` dir without a manifest is left behind. The scheduler catches it and marks the run failed. | Catch in the route, or return `success=False`. |
| 4 | LOW | `VACUUM INTO` lock hold | `journal_mode=delete`, so the snapshot holds SHARED for its whole run, and app writers wait out the 5 s busy timeout. Measured on a 329 MB vault on ext4: VACUUM took 4.5 s and a writer committed after 4.3 s. A larger vault or `/mnt/c` NTFS can give writers `database is locked`. Availability only, not integrity. | Accept and document. |
| 5 | INFO | SQLCipher config coupling | With the app's settings (defaults plus raw key) the output is encrypted and restorable. With a non-default `cipher_page_size=8192` on the source, the `VACUUM INTO` output was ciphertext that opened with neither setting. A future `cipher_*` pragma would silently produce unrestorable backups. HC-BKUP-056's restore-and-reopen step catches this. | Note: `cipher_*` changes must re-run HC-BKUP-056. |

## The 5 checks

| Check | Result | How |
|---|---|---|
| 1. Key material | New code never reads, logs or passes key material; the engine has `hide_parameters=True` and the only bound value is the dest path. `set_sqlite_pragma` and the PRAGMA key order are unchanged. Key access outlived logout via finding 1. | Read + experiment |
| 2. Output encrypted | SQLCipher 4.12.0 community / SQLite 3.51.1: no plaintext header, canary absent, keyless open gives `file is not a database`, keyed open reads and `integrity_check=ok`. Only plaintext case: dev mode without SQLCipher, where the source is already plaintext. | Ran |
| 3. Injection / unlink / symlinks | Bound param is safe. Dest is built on the server, not supplied by the caller. `VACUUM INTO` refuses an existing file and follows symlinks, so unlinking first is protective. | Ran |
| 4. Concurrency / deadlock | The loop never takes `_BACKUP_LOCK`, so there is no deadlock. Pool checkout is bounded at 30 s, busy at 5 s. See findings 2 and 4. | Read + ran |
| 5. Fallback and test validity | The fallback is acceptable: a closed profile has no app writer. 056 tears deterministically when the snapshot is skipped. 057 asserts `method != file_copy`. Neither covered finding 1. | Ran |

Reviewer test run: `pytest tests/test_backup_snapshot.py tests/test_backup_api.py` → `32 passed, 10 warnings in 19.01s`.
