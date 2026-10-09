GLOBAL executability rules (apply everywhere in the plan):
- Preconditions: state at the top "Prerequisites: P0-B and P1 merged to origin/main" (plus plan-specific ones). Task 0's ancestry check failing BEFORE P1 lands is the intended STOP, not a defect.
- Baseline sentences: each commit that changes collection updates ONLY the collected count in CLAUDE.md/AGENT.md. The "all N pass"/pass-count sentence is updated only with a pass count measured in a named environment (interpreter + embedding model present/absent); otherwise leave it and flag in the PR. Never write a collected number into a pass-count slot.
- Break-it-on-purpose on files the plan marks read-only: use monkeypatch or a disposable detached worktree; never edit then `git checkout --` in the phase worktree.
- Rollback after push/PR: include closing the PR and deleting the remote branch (`gh pr close <n> --delete-branch`), or `git revert` on main after merge.
- Absolute paths, `set -o pipefail`, no relative cd after cd.
