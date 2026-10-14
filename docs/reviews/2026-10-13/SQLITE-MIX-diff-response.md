# SQLITE-MIX diff — author response to security review

| # | Decision | What was done |
|---|----------|---------------|
| M1 | Comment fixed; snapshot fix deferred | Reworded the `api/backup.py` comment: the open waits for the writer's lock, then an encrypted vault falls back to a plain file copy, as before this change. Snapshotting from the keyed engine needs key use in backup code, which is ask-first and outside SQLITE-MIX/BKUP-MIX, so it goes to the owner as a follow-up. |
| M2 | Fixed | `scripts/backup.py`: `backup()` now holds a process-wide `threading.Lock` and calls `_backup_unlocked()`, so backups from the route and the scheduler run one at a time, as they did when they blocked the loop. Marked as a deliberate `ponytail:` simplification: per-profile locks if concurrent backups ever matter. |
| L1 | Deferred | A deadline needs a timeout policy for backups. The writer that holds the lock is driven by the now-free event loop, so the wait ends when that write commits. |
| L2 | Deferred | Existed before this change; not touched, to keep the diff surgical. |
| L3 | Verified, no change | CI run 38357922673 already resolved `aiosqlite-0.22.1` with the old `>=0.19.0` floor (Security Scan job, "Downloading aiosqlite-0.22.1"). The pin changes nothing CI installs. |
