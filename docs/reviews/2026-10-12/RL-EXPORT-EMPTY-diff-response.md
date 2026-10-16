# RL-EXPORT-EMPTY diff review — author response (2026-10-12)

| Finding | Action |
|---|---|
| HIGH: NULL-row backfill untested | Added `test_hc_rlexp_003_rerating_a_row_stored_without_prompt_backfills_it` (HTTP). Mutant `existing is None` now fails it. |
| MEDIUM: duplicate `turn_index` -> 500 | `_preceding_user_prompt` uses `.scalars().all()` and returns a snapshot only when exactly one user turn matches. Test 002 adds a duplicate-index session; mutant `if users else None` fails it. |
| LOW: assistant-lookup mutants survive | Test 002 adds a rated user turn and an assistant turn owned by `OTHER_PROFILE`. Both mutants (drop role filter, drop profile filter) now fail it. |
| LOW: body snapshot beats derived | Not changed: spec §3 step 3 says derive only when `body.prompt_snapshot` is None. |

Evidence (src/backend, `flock /tmp/claude-1000/hc-pytest.lock ~/venvs/asclexis-311/bin/python -m pytest ...`):
- New tests on `origin/main` feedback.py: `3 failed` (`assert 0 == 1` each).
- 8 mutants, 8 killed.
- Collected: `1469 tests collected`. Full suite: `1469 passed, 63 warnings in 218.77s`.
