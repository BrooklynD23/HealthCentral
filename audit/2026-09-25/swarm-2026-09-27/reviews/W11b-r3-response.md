R3 (codex) dispositions — fixed after round 3 (owner asked about round 4):
1. [MAJOR] S-C1-1 says nine direct-call tests migrated; four remain direct -> ACCEPTED: state in S-C1-1 and the recurring-failures row that HC-PKT-014/015 and HC-FHIR-103/104 remain legacy direct-call checks, not relied on, with HTTP coverage in HC-EXPA.
2. [MAJOR] baseline `| tail -15` truncates START_FAILURES -> ACCEPTED: full output to a named file; extract all failure node IDs; tail only for display. Scan the whole plan for the same pattern.
Add "Review status: 3 Codex rounds; round-3 findings fixed after the last round (owner decides on round 4)."
