# DOSE-VAR diff review response

| Finding | Response |
|---|---|
| LOW duplicate settings query | **Deferred.** It is one local query, and merging the two blocks would restructure the badge path. That is beyond a surgical fix. |
| LOW sign flip beyond 12h | **Accepted as intended.** Nearest daily occurrence is the decision's intent. The old raw diff gave -1425 for a 23:50 target logged at 00:05. Recorded here for the owner. |
| LOW test gaps | **Fixed.** Added 4 rows to `test_hc_med_http_011`: fall-back 01:30 PDT and 01:30 PST (both 0), a `+02:00` offset input, and an invalid zone falling back to UTC. Collected count updated to 1498. |
| LOW schedule not tied to medication | **Deferred, owner item.** This predates the diff and is out of scope. Ticket candidate: add `MedicationSchedule.medication_id == medication_id` to the lookup. |
