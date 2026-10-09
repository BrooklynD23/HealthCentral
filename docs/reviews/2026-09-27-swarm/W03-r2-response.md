R2 (codex) dispositions:
1. [MAJOR] backend baseline truncated by tail -15 -> ACCEPTED: write full output (or --junitxml/json report) at START and END to files outside the repo; extract and compare full failure-ID sets.
2. [MAJOR] `SCRATCH=<your scratchpad dir>` not runnable -> ACCEPTED: concrete absolute path (e.g. /mnt/c/Users/DangT/Documents/GitHub/w03-scratch) with mkdir -p.
3. [MAJOR] `START` used as a git revision without assignment -> ACCEPTED: `START=$(git -C "$WT" rev-parse HEAD)` in Task 0 persisted to a file, re-read in later blocks.
