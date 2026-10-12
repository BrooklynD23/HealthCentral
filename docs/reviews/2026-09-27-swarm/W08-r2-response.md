R2 (codex) dispositions:
1. [BLOCKER] downloader rm -r of an existing `<target>.partial` -> ACCEPTED. Refuse (exit non-zero with a message) if `<target>.partial` already exists; only delete a .partial this run created (e.g. created via mkdir exclusive in this run). Add HC-EMB test for a pre-existing .partial (not deleted, command fails).
2. [BLOCKER] worktree at origin/main fails ancestry check -> REJECTED as a defect: this is the intended STOP until P1 is merged. Fix wording: add explicit "Prerequisites: P0-B and P1 merged to origin/main" at top and in Task 0.
3. [MAJOR] route break-it edits read-only api/interpretations.py with git checkout -- -> ACCEPTED: monkeypatch the mapping or use a disposable detached worktree.
