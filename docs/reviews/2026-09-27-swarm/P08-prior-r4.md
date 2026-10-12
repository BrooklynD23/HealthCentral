R1 (codex) dispositions:
1. [BLOCKER] worktree from origin/main lacks P0-B package -> REJECTED as a defect (intended STOP until P0-B/P1 merge). Fix wording: explicit "Prerequisites: P0-B and P1 merged to origin/main".
2. [MAJOR] D8 delivery settled -> ACCEPTED: cite owner decision D8-delivery (2026-09-27, "Script + offline load": interim download_models.py fetch into a local models dir; HF offline at runtime; fails closed if absent; installer bundles it later (G-C4); no weights in git) and point to W-8.
3. [MAJOR] failures ⊆ start with no end run -> ACCEPTED: either run the suite at END and compare failure names, or mark that acceptance line UNMEASURED (docs-only phase).
4. [MAJOR] uvicorn relative --app-dir -> ACCEPTED: absolute app dir + full launch/probe commands.
5. [MAJOR] pre-merge rollback leaves remote PR/branch -> ACCEPTED: gh pr close --delete-branch.
R2 (codex) dispositions:
1. [MAJOR] no check that P1 reconciled CLAUDE.md (1288 @B) vs AGENT.md (1269 @B) counts -> ACCEPTED: Task 0 stop gate: CLAUDE.md and AGENT.md collected counts on origin/main agree with each other and with the measured START collection; else STOP and report (P1's job).
R3 (codex) dispositions — POST-ROUND-3 fixes (owner will be asked about round 4):
1-4. [MAJOR] `git add <packet>` placeholder; escaped `\|` in grep -E at C2, C7, C13 (verified by the reviewer with seeded inputs) -> ACCEPTED: concrete path audit/2026-09-25/gated-items-decision-packet.md; unescaped ERE alternation everywhere (scan every grep -E in the plan); each check keeps its seeded-positive proof.
Add a line near the top: "Review status: 3 Codex rounds; round-3 findings fixed after the last round (owner decides on round 4)."
