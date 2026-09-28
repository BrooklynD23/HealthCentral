R3 (codex) dispositions — POST-ROUND-3 fixes (review budget exhausted; escalated to owner for optional round 4):
1. [MAJOR] timeout golden case bypasses the real finish_reason=="timeout" branch (rag.py:1291-1295 @B) -> ACCEPTED: a fake runner returns finish_reason="timeout" through the real _generate_with_runner path; if that is not feasible in the gate harness, rename the case to "canned timeout text" and do not claim timeout-branch coverage.
2. [MAJOR] HC-LEG-004 (0.6 stays valid) cannot go red -> ACCEPTED: label it a baseline-green characterization test, excluded from the red-first list; keep HC-LEG-001 as the red-first abstention test.
Add a line near the top: "Review status: 3 Codex rounds; round-3 MAJORs fixed after the last round, not re-reviewed (owner may request round 4)."
