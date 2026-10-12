# W-10 Codex round 5 — L1-C response (2026-10-08)

Reviewed: the r5 amendment set of `docs/plans/2026-09-27-W10-governance-invariant-amendments.md` at `5e2bc66` (on `origin/main` `777adf5`).
Runner: `node …/codex-companion.mjs task --fresh "<W10-r5-prompt.md>"` (no `--write`), from the worktree `hc-w10`. Model: Codex's configured default, `gpt-6-luna` at `xhigh` (`~/.codex/config.toml:2-3`); the runtime reported "GPT-6 / HIGH".
Read-only check: `git status --short`, `git rev-parse HEAD` and the sha256 of `CLAUDE.md`, `data-privacy.md`, `hipaa-controls.md`, the plan, `docs/INDEX.md` and `docs/_link_graph.json` were identical before and after the job.

Verdict: **REVISE** (1 BLOCKER, 3 MAJOR, 1 MINOR). Each finding was checked against the files before it was applied.

| # | Finding | Check | Disposition |
|---|---|---|---|
| 1 | [BLOCKER] Task 0 Step 1 runs `git worktree add` for a worktree and branch that already exist | True: the L1 creates `../hc-w10` before Task 0; `git worktree add` on an existing path exits non-zero | ACCEPTED. Step 1 reuses the worktree when `git -C "$WT" rev-parse --is-inside-work-tree` succeeds and adds it only if absent |
| 2 | [MAJOR] The green-gate block can end successfully after a failed gate; pytest output is piped through `tail` | True: `set -o pipefail` does not stop a `;` chain, and the last `git diff --stat` exits 0 | ACCEPTED. Task 4b Step 5 uses `set -euo pipefail`, one gate per line, and prints `ALL GREEN` last. The two collect / pytest pairs write full output to a file and print the pytest exit code |
| 3 | [MAJOR] HC-1 calls `details_json` "a JSON field"; the column is SQL `Text` | True: `src/backend/models/audit.py:55` `mapped_column(Text, nullable=True)`; `core/audit.py` stores `json.dumps(...)` in it | ACCEPTED. HC-1 now says "a text `details_json` column that holds serialized JSON"; the §3.6 evidence row names the column type |
| 4 | [MAJOR] W10-A3 accepts "only bypass" anywhere in the privacy file without the audit and UI-warning conditions; W10-F2 does not check the Security events row | True for both | ACCEPTED. A3 now reads only the "Optional External API" subsection and requires the full clause with both conditions (and, when GOV-BG is unsigned, that "only bypass" is absent from that subsection). F2 asserts both replacement rows in full; F3 and F4 now assert the full replacement sentences too |
| 5 | [MINOR] Task 3 Step 5 says "only A6-A8 fail for any W10_ARGS", then says A3 also fails | True | ACCEPTED. One sentence: with `--c3 --govbg`, A3, A6, A7 and A8 fail (`5/9`) |

No finding questioned an After block's scope against the owner rows, a Before anchor, or a cited `file:line`.
The prior-round items (2026-10-07 review) were not re-raised: sign-off defaults, LOCAL-07, the two other fold-ins, and the `hipaa-controls.md` scope under W10-HIPAA.

Next: round 6 re-reviews the five fixes (last round allowed).
