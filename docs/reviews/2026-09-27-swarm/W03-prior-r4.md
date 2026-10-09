R1 (codex) dispositions:
1. [BLOCKER] Task 7 (knowledge fallback filter) runs by default though O-1 unresolved -> ACCEPTED. D4 names legacy RAG; the no-LLM knowledge fallback changes patient-visible output and is not literally named. Task 7 runs ONLY if O-1 is signed "yes" (opt-in), not default-with-veto; otherwise it is skipped and listed as an open owner item.
2. [MAJOR] `.\dev.ps1` run from src/frontend -> ACCEPTED: Set-Location to the worktree root first (absolute path).
3. [MAJOR] frontend baseline lacks failed test IDs -> ACCEPTED: record failing test names at START and END (vitest --reporter=verbose or json), compare sets.
R2 (codex) dispositions:
1. [MAJOR] backend baseline truncated by tail -15 -> ACCEPTED: write full output (or --junitxml/json report) at START and END to files outside the repo; extract and compare full failure-ID sets.
2. [MAJOR] `SCRATCH=<your scratchpad dir>` not runnable -> ACCEPTED: concrete absolute path (e.g. /mnt/c/Users/DangT/Documents/GitHub/w03-scratch) with mkdir -p.
3. [MAJOR] `START` used as a git revision without assignment -> ACCEPTED: `START=$(git -C "$WT" rev-parse HEAD)` in Task 0 persisted to a file, re-read in later blocks.
R3 (codex) dispositions — fix applied after round 3 (owner will be asked about round 4):
1. [MAJOR] PR status claims legacy RAG verified-only even when O-5 (chunks) / O-1 (fallback) are skipped -> ACCEPTED: PR/status text is conditional: name each retrieval path (observations, chunks, knowledge fallback) as filtered / owner-gated-not-filtered; matrix SAFE-02 stays partial unless all paths are filtered.
Add "Review status: 3 Codex rounds; round-3 MAJOR fixed after the last round (owner decides on round 4)."
