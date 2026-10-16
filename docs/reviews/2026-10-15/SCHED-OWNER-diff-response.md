# SCHED-OWNER diff review response

| Finding | Response |
|---|---|
| 1 MEDIUM vacuous leak assertion | **Fixed.** Test 015 now seeds 7 recent non-skipped doses on med A tagged `sched_b` and checks `leaked` right after the foreign call. Mutation: with the `learn_patterns` guard removed and both 422 assertions disabled, test 015 still fails on the leak assertion. |
| 2 LOW dangling id via learn-patterns | **Accepted, owner item.** Unknown ids were kept as-is per the decision ("keep whatever main does today unless it is a 500"). A future "reject unknown schedule_id" change should cover `log_dose` and `learn_patterns` together. |
| 3 LOW no unscoped learn-patterns test | **Fixed.** Test 015 also posts without `schedule_id` and asserts 200. |
| 4 LOW no audit on these routes | **Deferred, pre-existing.** Neither route audited before this diff, and rejected requests elsewhere in the file (400/404) are not audited either, so the 422 follows the existing pattern. Ticket candidate. |
