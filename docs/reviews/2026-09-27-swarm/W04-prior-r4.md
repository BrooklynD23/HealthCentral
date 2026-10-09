R1 (codex) findings and orchestrator dispositions:
1. [BLOCKER] green "claims verified" footer under an abstention (ExplainAssistant.tsx:607-618) not a pre-merge gate -> ACCEPTED. Fix: OQ-5 becomes a required signed pre-merge owner gate; if the footer must change, that edit is planned only after separate approval (not licensed by G-B5).
2. [MAJOR] eval gate piped through tail masks exit code -> ACCEPTED. Fix: run gates unpiped, or `set -o pipefail` and record `${PIPESTATUS[0]}`.
3. [MAJOR] commit pathspec omits conditionally-staged docs/INDEX.md -> ACCEPTED. Fix: include docs/INDEX.md (and docs/_link_graph.json if regenerated) in the commit pathspec.
4. [MAJOR] golden-fixture comparison `python -c` with undefined CASES -> ACCEPTED. Fix: make it a named test (or a complete runnable command).
R2 (codex) dispositions:
1. [MAJOR] collected count written into the "all N pass" claim -> ACCEPTED. Update only collected counts; pass sentence only with a measured pass count in a named environment (see GLOBAL rules).
R3 (codex) dispositions — POST-ROUND-3 fixes (review budget exhausted; escalated to owner for optional round 4):
1. [MAJOR] timeout golden case bypasses the real finish_reason=="timeout" branch (rag.py:1291-1295 @B) -> ACCEPTED: a fake runner returns finish_reason="timeout" through the real _generate_with_runner path; if that is not feasible in the gate harness, rename the case to "canned timeout text" and do not claim timeout-branch coverage.
2. [MAJOR] HC-LEG-004 (0.6 stays valid) cannot go red -> ACCEPTED: label it a baseline-green characterization test, excluded from the red-first list; keep HC-LEG-001 as the red-first abstention test.
Add a line near the top: "Review status: 3 Codex rounds; round-3 MAJORs fixed after the last round, not re-reviewed (owner may request round 4)."
