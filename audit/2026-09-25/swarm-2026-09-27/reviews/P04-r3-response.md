R3 (codex) dispositions — fixes applied after round 3 (owner will be asked about round 4):
1. [BLOCKER] execution worktree from origin/main won't contain this untracked plan -> ACCEPTED (program-level): add prerequisite "the 2026-09-27 plan set (docs/plans/2026-09-27-*.md) is committed on main via an owner-approved docs commit — P0-B's approved text covers only audit/ + docs/capstone-report/ + docs/INDEX.md" and verify in Task 0 Step 2 (`git -C "$WT" ls-files --error-unmatch docs/plans/2026-09-27-P04-doc-drift-sweep-amendment.md`).
2. [MAJOR] final commit omits this plan's §15 execution record -> ACCEPTED: add the plan path to staging, the expected staged-path check and the commit pathspec.
3. [MAJOR] F6 dependency row says W-6 only; task says W-6 and W-10 -> ACCEPTED: W-6 AND W-10 at line 198.
Add "Review status: 3 Codex rounds; round-3 findings fixed after the last round (owner decides on round 4)."
