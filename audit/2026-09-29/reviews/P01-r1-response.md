# P01 r1 — L0 response to Codex (2026-09-29)

Codex verdict: REVISE (4 BLOCKER, 4 MAJOR, 1 MINOR). Each finding was checked against the code at `origin/main@36b2ff2` and branch refs before acting.

| # | Codex | L0 verdict | Evidence | Action |
|---|---|---|---|---|
| 1 | BLOCKER cache not profile-isolated | **Accepted — worse than stated: live on main** | `modules/agent/cache.py:31-35` (main + B): key has no profile ID. Main `assistant.py:552-563` version = verified-observation count only; agent path default-on `assistant.py:726-731`. B `test_hc_a1_agent_verification.py:73-79` seeds a key without profile and a random new profile hits it. | Owner S-CACHE → new phase, [plan S02](../../../docs/plans/2026-09-29-S02-agent-cache-profile-isolation.md). B still merges as-is. |
| 2 | BLOCKER memory audit `category` | **Accepted** | B `api/memory.py:55,135,165`; `"category"` allowlisted `core/audit.py:73 @B` (also main :70); `_ENUM_VALUE_RE` admits `HIV`. | Owner MEM-AUDIT-CAT → folded into S-CACHE. |
| 3 | BLOCKER SLOT-RULE after PR #1 / PR #2 | **Accepted** | B `AGENT.md:76` 1269 vs `CLAUDE.md:30` 1288; plan Task 3/4 leaves `MEASURED_PENDING` across commits. | Owner P1-SLOTS: slot commit on PR #1 merge branch; PR #2 writes the measured count in its merge commit. |
| 4 | MAJOR stale conflict map | **Accepted** (L0 measured it first) | `git merge-tree origin/main B` → INDEX.md, _link_graph.json. | Owner P1-PR1-MERGE. L1 re-runs merge-tree for A after PR #1 lands. |
| 5 | MAJOR `-k` filter hides 3 files; CAREQ tests call handler directly | **Accepted** | `-k` applies to every path on the command line; A `test_documents_api.py:663-668` calls `delete_document(...)` with audit mocked. | L1 runs Task 6 Step 7 without `-k` on non-CAREQ files. Owner P1-CAREQ-HTTP: +1 route_client test in PR #2. |
| 6 | BLOCKER suite may write to real master DB | **Downgraded to MINOR** | Master path is relative `data/asclexis.db` (`core/config.py:37,160-185`); no `.env` in any worktree or the canonical checkout; baseline run in `../hc-baseline` created no `*.db` (`find -newer CLAUDE.md` empty) and left `git status` clean. | L1 runs `find . -name "*.db" -newer CLAUDE.md` + `git status --short` after every suite run; a hit STOPs. |
| 7 | MAJOR no worktree / venv / HF offline Task 0 | **Accepted** | plan :102, :288 hardcode the canonical checkout. | L1 brief: worktree `../hc-p1-*`, `~/venvs/asclexis-311`, `HF_HUB_OFFLINE=1`, START count. |
| 8 | MAJOR no CI-green requirement before merge; no rollback | **Accepted** | plan :193-198, :440. | L1 reports `gh pr checks`; L0 hands a PR to the owner only when required checks are green (E2E Smoke: CI-DISK known). Post-merge invariant failure → owner reverts. |
| 9 | MINOR final docs commit pathspec | **Accepted** | plan :508. | `git add docs/features/TASK_LIST.md`. |

No round 2: the plan text is amended by the banner (plan 01 item 6) and the L1 brief; the new S-CACHE plan gets its own Codex review.
