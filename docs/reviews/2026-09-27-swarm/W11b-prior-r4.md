R1 (codex) dispositions:
1. [MAJOR] HC-PKT-014/015, HC-FHIR-104 keep status assertions on direct handler calls -> ACCEPTED: any status/auth assertion this plan adds or relies on goes through route_client with a break-it; existing direct-call tests are listed as a recurring-failures #1 finding (not silently relied on).
2. [BLOCKER] rollback uses bare alembic (defaults to master chain; profile chain needs vault path + key) -> ACCEPTED: per-vault downgrade procedure through the supported migration API (find the function used by the app/tests to migrate a profile vault with path+key), run on a backup copy first; or state the migration is additive and rollback = code revert with the table left in place, if that is safe — prove which.
3. [MAJOR] G-C4 treats `download_models.py embedding` as available -> ACCEPTED: conditional on W-8 landing; label "proposed (W-8)" otherwise.
4. [MAJOR] Apache-2.0 + NOTICE mandated without verification -> ACCEPTED: C4.1 verifies upstream licence/NOTICE (base model too) or marks UNMEASURED; redistribution terms stay with S-C4-4.
Apply reviews/GLOBAL-rules.md too.
R2 (codex) dispositions:
1. [MAJOR] installer pinned to one model revision/hash/file set though D8 approves only "the small embedding model" -> ACCEPTED: mark revision/hash/file set as a PROPOSAL with an unsigned owner sign-off (S-C4-5: model + revision), consistent with W-8 (which pins revision 1110a243… as its proposal).
2. [MAJOR] `show` defined inside one heredoc, called after it exits -> ACCEPTED: one heredoc does both reads, prints results or UNMEASURED.
Also add the prerequisite: plan set committed to main via an owner-approved docs commit (P0-B covers only audit/ + capstone-report/ + INDEX.md).
R3 (codex) dispositions — fixed after round 3 (owner asked about round 4):
1. [MAJOR] S-C1-1 says nine direct-call tests migrated; four remain direct -> ACCEPTED: state in S-C1-1 and the recurring-failures row that HC-PKT-014/015 and HC-FHIR-103/104 remain legacy direct-call checks, not relied on, with HTTP coverage in HC-EXPA.
2. [MAJOR] baseline `| tail -15` truncates START_FAILURES -> ACCEPTED: full output to a named file; extract all failure node IDs; tail only for display. Scan the whole plan for the same pattern.
Add "Review status: 3 Codex rounds; round-3 findings fixed after the last round (owner decides on round 4)."
