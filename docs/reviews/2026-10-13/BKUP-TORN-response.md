# BKUP-TORN diff — author response to security review

| # | Decision | What was done |
|---|----------|---------------|
| 1 | Fixed | `keyed_snapshotter(profile_id)` no longer captures an engine. `_snapshot` looks up `get_profile_db_manager().get_connection(profile_id)` on the loop when it runs. If the profile is closed, it returns False and `_backup_unlocked` takes the keyless path (no app writer can be active then). If the profile closes during `VACUUM INTO`, the connection is `invalidate()`d instead of being returned to a disposed pool. The `_vault_snapshotter` helper is gone; both callers pass `keyed_snapshotter(profile_id)`. New test HC-BKUP-058: the snapshotter is built, the profile is closed, the snapshot returns False, no dest file, 0 fds left on `vault.db`. Mutation (capture the connection at build time, as before) → 058 fails. |
| 2 | Fixed | `future.result(timeout=SNAPSHOT_TIMEOUT_S)` (600 s); on timeout the future is cancelled and the error is raised. |
| 3 | Deferred | Unhandled-exception 500s on the route existed before for non-SQLite errors. Removing the partial dir is unsafe as written: `backup_<second>` is shared with an earlier same-second backup (`exist_ok=True`), so an `rmtree` could delete a good backup. The scheduler already records `failed`. Follow-up: unique backup dir names, then cleanup on failure. |
| 4 | Accepted | Availability only. Writers wait up to the 5 s busy timeout while the snapshot holds SHARED. Integrity was the owner's ask. Chunking or retry would be a separate change. |
| 5 | Noted | Changing `cipher_*` settings is ask-first encryption work. HC-BKUP-056's restore-and-reopen step is the guard. Not adding a comment in `core/profile_database.py`, which is an ask-first file this PR does not touch. |
