# DDI round 1 — response (L1-A, 2026-10-04)

Codex verdict: **REVISE** (2 BLOCKER, 3 MAJOR). Output: [DDI-r1-codex.txt](DDI-r1-codex.txt). Each finding was checked against the repo before acting.

| # | Codex finding | Disposition | Evidence |
|---|---|---|---|
| 1 | [BLOCKER] Task 3 recurring-failures §9 edit is outside W3-SEC-SCHED | **Rejected in r1; reversed in r2 (accepted, edit dropped — see DDI-r2-response.md)** | `CLAUDE.md:49-52` @90c502a is a standing repo rule, not an owner-gated edit: "Catch a new instance of one — or a mode that is not listed — and add it in the same commit." `recurring-failures.md` is not ask-first and not on the governance list (only `CLAUDE.md:50`'s count is, item CLAUDE-FAILURE-COUNT). Prior phases added evidence the same way (§1 S-CACHE, 2026-09-29). The plan now cites `CLAUDE.md:49-52` at Task 3 Step 5. Escalated to L0 in the wave report so the owner can overrule. |
| 2 | [MAJOR] Goal says "every row"; commit text says all four tests use HTTP | **Accepted, fixed** | Care-plan tasks are kept by design (`api/documents.py:1854-1869`), `PanelInterpretation.observation_ids_json` is not an FK (`models/interpretation.py:159`). Goal now lists deleted vs retained rows; commit body says HC-DDI-001..003 use `route_client`, 004 is a session-level guard. |
| 3 | [BLOCKER] `git commit -- <paths>` cannot commit untracked files | **Accepted, fixed** | Measured: `git commit --dry-run -m x -- docs/plans/2026-10-04-DDI-…md` → `error: pathspec … did not match any file(s) known to git`. Task 0 Step 3 now runs `git add -- <explicit paths>` first. |
| 4 | [MAJOR] Blocks miss WT/PY setup, pipefail, full-output capture; lint does not gate commit | **Accepted, fixed** | Every block now starts with the full header (`set -euo pipefail`, `$LOG`), saves pytest output to `$LOG/*.txt`, and chains commits with `&&` behind lint / slot checks. |
| 5 | [MAJOR] Ancestry check does not enforce the refresh trigger; no serial-merge rule for slots | **Accepted, fixed** | `implementation-program.md:137-139` ("The PR that merges second rebases and re-measures"; slots serial at merge). Task 0 Step 1 now runs `git diff --quiet 90c502a origin/main -- <trigger paths>`; Global Constraints gained the merge-main / re-measure rule. |

Round 2: run to confirm the amendments (max 2 rounds).
