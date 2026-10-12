R4 (codex, FINAL) dispositions — fixed after the last round; open for owner acceptance:
1. [MAJOR] Task 16 allows a CLAUDE.md/AGENT.md collected-count edit but stages/commits neither -> ACCEPTED: add whichever baseline file changed to staging, the staged-path check and the commit pathspec (conditional list built from `git diff --name-only`).
2. [MAJOR] Windows Mermaid commands lack Set-Location -> ACCEPTED: `Set-Location C:\Users\DangT\Documents\GitHub\hc-p4` before the four commands; check $LASTEXITCODE.
Update review-status line: "4 Codex rounds; round-4 MAJORs fixed after the last round, not re-reviewed (owner acceptance required)."
