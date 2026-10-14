# MED-UTC diff code review

Reviewer: code-reviewer subagent (Opus 5.5), read-only, 2026-10-12. Scope: uncommitted diff on `fix/medications-utc` (`core/time.py::to_naive_utc`, `NaiveUtcDatetime` in `api/medications.py`, tests `http_006`-`http_010`).

VERDICT: approve. The fix is correct and minimal. No CRITICAL or HIGH findings.

## Checks
| Check | Result |
|---|---|
| Naive input | Returned unchanged |
| `Z` input | `06:30Z` gives naive `06:30` |
| Unix timestamp | Pydantic parses it as aware UTC, then it converts correctly |
| DST (spring forward and fall back) | Converted correctly |
| Query params (`from_date`/`to_date`) | The validator runs: `-07:00` gives `06:00`, a date-only value gives midnight, `bad` gives 422, missing gives None |
| Missed write or filter sites | None. The writers are create, PATCH, `utcnow` end, and dose. `med_reconcile.py` and `export.py` only read. `gamification.py:165` compares stored values |
| Can the tests pass while the bug exists? | No. Before the fix, `http_010` stores `ended_at` 20:00 Mar 2, which cuts off the dose, so streak is 0 |
| Over-engineering | None |

## Findings
**[MEDIUM] `variance_minutes` compares the UTC hour with a local-time schedule target.** `api/medications.py` (log_dose variance block). `taken_at` is now always UTC, while `schedule.target_time` is local wall-clock time. The frontend sends `Z` (`DoseLoggingModal.tsx:61`), so it was already wrong on that path. Clients that send an offset now also get variance that is off by the offset. Fix (separate ticket): compute the hour in the profile timezone, and add an HTTP test that sends `schedule_id`.

**[LOW] The frontend parses naive-UTC ISO strings as local time.** `MedicationDetail.tsx:308,419,421`. This predates the diff.

**[LOW] `ended_at` cannot be cleared via PATCH**, because of the `is not None` guard. This predates the diff.

VERDICT: approve
