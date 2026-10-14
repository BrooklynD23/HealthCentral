# MED-UTC diff review response

| Finding | Response |
|---|---|
| MEDIUM variance_minutes uses the UTC hour | **Deferred to owner.** This diff did not create it: the only shipped client (frontend, `Z`) already got UTC-hour variance. Fixing it changes dose-variance semantics for every client, which is beyond decision MED-UTC. I am recording it as a follow-up ticket candidate. No current test covers variance. |
| LOW frontend parses naive ISO as local | **Deferred.** This predates the diff and is a frontend display issue. Follow-up: serialise with `Z`, or parse as UTC on the client. |
| LOW `ended_at` cannot be cleared | **Deferred.** This predates the diff and is out of scope. |

No code changes came out of this review.
