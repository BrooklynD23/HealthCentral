R4 (codex, FINAL) dispositions — fixed after the last round; open for owner acceptance:
1. [BLOCKER] Task 0 `git worktree add` failure not enforced -> ACCEPTED: `test ! -e "$WT" || exit 1`; `git worktree add ... || exit 1`; verify `git -C "$WT" rev-parse --show-toplevel` = "$WT" before any cd. Apply to EVERY worktree creation in the plan.
Update review-status line: "4 Codex rounds; round-4 BLOCKER fixed after the last round, not re-reviewed (owner acceptance required)."
