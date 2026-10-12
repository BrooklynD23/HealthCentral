R4 (codex, FINAL) dispositions — fixed after the last round; open for owner acceptance:
1. [BLOCKER] PHI gate prints matches but exits 0 -> ACCEPTED: gate = `hits=$(find ... -print); test -z "$hits" || { printf '%s\n' "$hits"; exit 1; }` (also exit 1 on find error); each planted-path break-it asserts exit 1 before dispatch.
2. [MAJOR] harness.md find command not runnable (<path>, unescaped parens) -> ACCEPTED: put the exact tested, escaped command with a defined AGENT_WT variable.
Update review-status line: "4 Codex rounds; round-4 findings fixed after the last round, not re-reviewed (owner acceptance required)."
