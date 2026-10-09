R3 (codex) dispositions — POST-ROUND-3 fixes (owner will be asked about round 4):
1. [BLOCKER] fixed $BRK path could be an existing worktree; failed add doesn't stop; forced remove could delete it -> ACCEPTED: every break-it block: `test ! -e "$BRK" || { echo "BRK exists"; exit 1; }`; `git worktree add --detach "$BRK" ... || exit 1`; record `git -C "$BRK" rev-parse --show-toplevel` equals "$BRK"; remove with `git worktree remove --force "$BRK"` only after that check; use a unique path per block (mktemp -d suffix).
2. [MAJOR] non-forced remove fails on a dirty disposable worktree -> ACCEPTED: guarded forced removal as above.
Add a line near the top: "Review status: 3 Codex rounds; round-3 findings fixed after the last round (owner decides on round 4)."
