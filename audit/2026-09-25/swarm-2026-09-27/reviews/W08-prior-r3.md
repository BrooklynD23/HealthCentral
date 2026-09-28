R1 (codex) findings and orchestrator dispositions:
1. [MAJOR] interpret-grounded 501 not tested over HTTP -> ACCEPTED. Fix: route_client test for POST /interpretations/observations/{id}/interpret-grounded asserting 501 and the fixed detail (no file path), plus break-it on the route mapping. Keep Q-FC owner gate on the wording.
Also apply repo-wide executability rules: absolute WT path, no relative cd after cd, pipefail/PIPESTATUS for piped exit codes, count updates in the same commit that changes collection.
R2 (codex) dispositions:
1. [BLOCKER] downloader rm -r of an existing `<target>.partial` -> ACCEPTED. Refuse (exit non-zero with a message) if `<target>.partial` already exists; only delete a .partial this run created (e.g. created via mkdir exclusive in this run). Add HC-EMB test for a pre-existing .partial (not deleted, command fails).
2. [BLOCKER] worktree at origin/main fails ancestry check -> REJECTED as a defect: this is the intended STOP until P1 is merged. Fix wording: add explicit "Prerequisites: P0-B and P1 merged to origin/main" at top and in Task 0.
3. [MAJOR] route break-it edits read-only api/interpretations.py with git checkout -- -> ACCEPTED: monkeypatch the mapping or use a disposable detached worktree.
