R1 (codex) findings and orchestrator dispositions:
1. [BLOCKER] green "claims verified" footer under an abstention (ExplainAssistant.tsx:607-618) not a pre-merge gate -> ACCEPTED. Fix: OQ-5 becomes a required signed pre-merge owner gate; if the footer must change, that edit is planned only after separate approval (not licensed by G-B5).
2. [MAJOR] eval gate piped through tail masks exit code -> ACCEPTED. Fix: run gates unpiped, or `set -o pipefail` and record `${PIPESTATUS[0]}`.
3. [MAJOR] commit pathspec omits conditionally-staged docs/INDEX.md -> ACCEPTED. Fix: include docs/INDEX.md (and docs/_link_graph.json if regenerated) in the commit pathspec.
4. [MAJOR] golden-fixture comparison `python -c` with undefined CASES -> ACCEPTED. Fix: make it a named test (or a complete runnable command).
