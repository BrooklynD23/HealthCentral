R1 (codex) findings and orchestrator dispositions:
1. [MAJOR] async test_HC_INT_013 lacks @pytest.mark.asyncio -> REJECTED on re-check: the marker was already present above the parametrize decorator; the author added a grep-based marker check and required -rs with 0 skipped.
2. [MAJOR] baseline count update in a separate commit -> ACCEPTED (CLAUDE.md §4 "update it in the same commit"). Fix: each commit that changes collection updates the CLAUDE.md/AGENT.md count in that commit.
3. [MAJOR] `/path/to/hc-w07` placeholder -> ACCEPTED. Fix: define WT absolute path in Task 0 and use "$WT" everywhere.
