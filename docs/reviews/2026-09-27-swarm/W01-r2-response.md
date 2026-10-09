R2 (codex) dispositions:
1. [BLOCKER] smoke check may miss data/ *.db .env in the agent worktree -> ACCEPTED (config.py:37 @B DB path data/asclexis.db). Fix: pre-dispatch gate fails if "$AGENT_WT/data", "$AGENT_WT/src/backend/data", any *.db / *.db-wal / *.db-shm, or any .env exists anywhere in the worktree (find-based); break-it: create each and show the gate fails.
2. [BLOCKER] HC-AGENTS-008 puts the drift checker into the backend CI suite without OG-3 -> ACCEPTED. Keep HC-AGENTS-008 out of the collected backend suite unless OG-3 is signed: default = run the drift check as a manual Task-level command in the PR; adding it to the suite is a separate post-OG-3 step. Adjust counts accordingly.
3. [MAJOR] count inconsistency start+8(+1) -> ACCEPTED: one consistent number derived from the final test list.
Apply reviews/GLOBAL-rules.md too.
