R1 (codex) dispositions:
1. [MAJOR] HC-PKT-014/015, HC-FHIR-104 keep status assertions on direct handler calls -> ACCEPTED: any status/auth assertion this plan adds or relies on goes through route_client with a break-it; existing direct-call tests are listed as a recurring-failures #1 finding (not silently relied on).
2. [BLOCKER] rollback uses bare alembic (defaults to master chain; profile chain needs vault path + key) -> ACCEPTED: per-vault downgrade procedure through the supported migration API (find the function used by the app/tests to migrate a profile vault with path+key), run on a backup copy first; or state the migration is additive and rollback = code revert with the table left in place, if that is safe — prove which.
3. [MAJOR] G-C4 treats `download_models.py embedding` as available -> ACCEPTED: conditional on W-8 landing; label "proposed (W-8)" otherwise.
4. [MAJOR] Apache-2.0 + NOTICE mandated without verification -> ACCEPTED: C4.1 verifies upstream licence/NOTICE (base model too) or marks UNMEASURED; redistribution terms stay with S-C4-4.
Apply reviews/GLOBAL-rules.md too.
