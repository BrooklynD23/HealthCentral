VERDICT up front: **approve**. I found no CRITICAL or HIGH issues: 0 CRITICAL, 0 HIGH, 1 MEDIUM (an older bug the diff relies on), 4 LOW.

## Scope reviewed
Worktree `/mnt/c/Users/DangT/Documents/GitHub/hc-gam-v2-t1`, branch `feat/gamification-v2-t1`, uncommitted diff against `64e5820`. 4 files:

| File | Change |
|---|---|
| `src/backend/api/gamification.py` | `_audit_view` via `audit_and_commit`; `master_db` dependency on both routes; Q2 `ended_at` filter |
| `src/backend/tests/test_gamification_api.py` | 1 direct-call test removed, 11 HTTP tests added (8 functions, parametrized) |
| `CLAUDE.md`, `AGENT.md` | baseline count 1466 -> 1476 |

I did not run anything, as instructed. The +10 count matches the diff (-1 +11), but I have not confirmed it with `--collect-only`.

## Checks
| Check | Result | Evidence |
|---|---|---|
| Q2 `ended_at` compare | Correct | `api/gamification.py:164`: `or_(ended_at IS NULL, taken_at <= ended_at)` is applied per dose row, so an ended medication does not hide doses from an active one. On SQLite both columns use the same `DateTime` storage format, so comparing them as strings is sound. |
| Naive UTC | Correct for server-written values | `api/medications.py:673` sets `ended_at = utcnow()`. Values the client supplies are a separate problem (MEDIUM-1). |
| Fail-closed ordering | Correct | `api/gamification.py:135,179`: the audit is written after the read and before `return`. If commit raises, nothing is served. `core/audit.py:485-486` re-raises. |
| PHI in audit row | None | The row holds only `event_type`, `action=event_type`, `profile_id`, `entity_type="gamification"`. No `entity_id`, no `details`. `action == event_type` correctly suppresses the "unregistered action" warning (`core/audit.py:183`). `ALLOWED_ACTIONS` is untouched. |
| Isolation | Correct | The `profile_id` filters at `:99` and `:161` are unchanged. Routes use `ProfileDbSession`; `get_db` is used only for the master audit write. |
| Scope creep | None | The count bump is required by the CLAUDE.md §4 rule. Removing `test_get_streaks_returns_profile_summary` is fine because `http_002` covers it over HTTP. |

## Test strength: would each test fail if the behaviour broke?
| Test | Fails if... | Verdict |
|---|---|---|
| `http_001` (x2) | the real `require_auth` stops returning 401 | Yes |
| `http_002` | the streak maths or the HTTP wiring breaks | Yes |
| `http_003` | the `Medication.profile_id` filter is dropped (B's days 1-3 would join A's day 4, making current=4) | Yes |
| `http_004` | the `EarnedBadge.profile_id` filter is dropped (earned=True) | Yes |
| `http_005` (x2) | `_audit_view` is removed, renamed, or given the wrong profile | Yes |
| `http_006` (x2) | the audit is removed or its error is swallowed | Yes |
| `http_007` | the Q2 filter is removed (current=4, longest=4) | Yes |
| `http_008` | the Q2 filter is too broad and drops the whole ended medication (current=2) | Yes |

## Findings

### MEDIUM
**M1. Q2 is only correct if `ended_at` and `taken_at` are naive UTC, and client input is not normalised.** This bug predates the diff; the new filter depends on it.
- Location: `api/medications.py:117` (`ended_at: Optional[datetime]`) is stored as received at `:609`. `taken_at` from `:141` is stored as received at `:962`.
- Cause: a tz-aware value such as `2026-03-02T23:00-05:00` loses its offset on SQLite and is stored as 23:00 instead of 04:00Z. That moves the Q2 cutoff by the offset, and the same applies to dose days.
- Fix (separate ticket, not this diff): at the boundary, `value.astimezone(timezone.utc).replace(tzinfo=None)` when `value.tzinfo` is set. Do this for both fields.

### LOW
1. **The `<=` boundary is not pinned.** `tests/test_gamification_api.py` `http_007` uses ended 23:00 and doses at 08:00, so changing `<=` to `<` would still pass. Fix: add one dose at exactly `ended_at` and assert that it counts.
2. **`http_006` asserts that an exception propagates, not what the HTTP response is.** Fix: call `route_client(..., raise_server_exceptions=False)`, then assert `status_code == 500` and that `"current_streak_days"` is not in `response.text`.
3. **`http_005` does not pin the PHI-minimal row shape.** A later change that adds `details` or `entity_id` would still pass. Fix: also assert `r.action == event_type` and `r.details_json is None` and `r.entity_id is None`.
4. **Redundant local imports.** `tests/test_gamification_api.py:87-88` (`import api.gamification as gamification_api`, `from core.auth import get_profile_db_session`) are now imported at module level. Safe to delete.

Note, not a finding: the `@pytest.mark.asyncio` tests drive a sync `TestClient` against an aiosqlite session made on the test loop. `tests/test_audit_order.py` already uses this cross-loop pattern, so I accept it.

VERDICT: approve

Next action: run `cd src/backend && python -m pytest tests/ --collect-only -q | tail -1` once the lock is free, and confirm it reports 1476.
