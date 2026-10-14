# DOSE-VAR diff code review

Reviewer: code-reviewer subagent (Opus 5.5), 2026-10-14. Diff: `log_dose` variance computed in the profile time zone (`src/backend/api/medications.py`), HTTP test `test_hc_med_http_011`.

## What was verified
| Check | Result |
|---|---|
| Naive vs aware `taken_at` | Safe. `to_naive_utc` always yields naive UTC, so `.replace(tzinfo=utc).astimezone(...)` is correct. |
| DST, ambiguous local times | UTC to local is never ambiguous. Fall-back 2026-11-01, target 01:30: 08:30Z gives 01:30 PDT (0), 09:30Z gives 01:30 PST (0). |
| DST, nonexistent target | Target 02:30 on 2026-03-08, dose 10:05Z (03:05 PDT) gives +35 wall-clock minutes. Reasonable. |
| Wrap math | `(d + 720) % 1440 - 720` is in [-720, 720). Exactly 12h off gives -720. |
| Time zone source | Same `_profile_timezone_name` as the streak/badge code. An invalid or missing zone falls back to UTC. |
| Per-profile isolation | Settings query runs on `profile_db` (ProfileDbSession), filtered by `session.profile_id`. |
| Audit | Untouched. |
| Python 3.11 | `zoneinfo` and `datetime.timezone` only, both already imported. |

## Findings
1. **[LOW] Duplicate settings query**, `api/medications.py` variance block and badge block. `UserModelSettings` is fetched twice in `log_dose`. Optional fix: fetch it once and reuse it.
2. **[LOW] Wrap flips the sign for doses more than 12h off**, `api/medications.py` wrap line. A 08:00 target logged at 21:00 was +780 and is now -660. Badges are unaffected (abs <= 60). The UI label changes sign, and the color does not. Nearest occurrence is the right call.
3. **[LOW] Test gaps**: the fall-back ambiguous hour, an invalid zone falling back to UTC, and a non-Z offset input.
4. **[LOW, pre-existing, out of scope] Schedule not tied to the medication**: the `MedicationSchedule` lookup filters only on `id`. A dose can link to another medication's schedule in the same profile. Not a cross-profile leak.

## Not run by the reviewer
The reviewer's checkout had no backend venv. The reviewer checked the math with stdlib Python and relied on the author's suite output.

VERDICT: approve
