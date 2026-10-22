# Session handoff: 2026-10-21 local L0 (laptop) → GPU box tonight

**Last Updated:** 2026-10-21
**Owner:** repository owner
**Refresh Trigger:** the next L0 session reads this first, works §3, and replaces this file with its own handoff.

Read this after [CLAUDE.md](../../CLAUDE.md), [AGENT.md](../../AGENT.md) and the [build-program RUNBOOK](2026-10-15-build-program/RUNBOOK.md). It replaces [the 2026-10-21b handoff](2026-10-21b-session-handoff.md). This session ran as a **local** L0 on the laptop: Danny-Lenovo, WSL, 6 vCPU, no GPU and no model host. It was started with `--plugin-dir .claude/mods/asclexis-rsi`. Owner instruction mid-session: "defer anything that needs RTX 3080 GPU computing dev environment for later tonight. We want to implement as much of the works as possible, then run the tests later due to time-constraints." Builds therefore ran focused tests only, and CI ran the full suite. Treat this file as a lead: verify with `gh pr view` / `git log origin/main` before acting.

## 1. What this session did

- **Setup (main `5c94a75`):** `2233 tests collected`, `from main import app` ok. The embedding bundle was present, and the 5 environmental tests (CLAUDE.md §4) gave `5 passed`. That closes the 2026-10-21b §4 "embedding tests on main" item. `merge_par.sh` was recreated (20 lines, `bash -n` clean). The venv `~/venvs/asclexis-311` is uv-managed and has no pip. Install with `uv pip install --python ~/venvs/asclexis-311/bin/python -r src/backend/requirements.txt`.
- **Merged by L0 (each had a review PASS and green checks):**

  | PR | Item | Merge |
  |---|---|---|
  | #268 | GC5-FAITH-SCORE (second lander: merged main, 139 focused passed, legacy gate byte-identical) | `8bbade2` |
  | #272 | plan: five rows (round 3 PASS) | `a8e5ead` |
  | #275 | RRSI-CI-DOCS | `5b0ccdf` |
  | #278 | AET-FALLBACK-LABEL (first lander beside #264, L0 ruling 6325911120) | `3bfa69c` |
  | #274 | AUDIT-READ-SETTINGS (rulings 6326101071, 6326185272) | `a5bda6e` |
  | #277 | EXTRACT-REGEX-NEWLINES (owner EXTRACT-NL-DIFF yes, prompt 28) | `35cdb10` |

- **Also merged by L0 after this file was first written:** #279 post-merge batch + this handoff (`89b16d2`; #273 merged with it); #276 REDACT-NG-GUARD-TAIL (`79963ee`; `redaction.py` equals licensed head `8986c95`; 4 strict pins; full suite 2315 passed).
- **Owner merged:** #267 RSI-LOG-STDERR (`1e9ed8d`) and #259 RRSI-CI-REPLAY (`0976557`).
- **Prompt 30, O-6:** "Freeze now; sign if all pass". Recorded on #210 in comment 6329347525 and in its owner-decisions row. The claim freeze moves from 2026-10-24 to the GPU-box session (2026-10-22). O-6 is signed for that date only if §10 checks 1-11 all pass at the freeze SHA, with outputs in plan §15. Any failure stops F-9 and goes back to the owner.
- **RSI logs archived:** `.claude/logs/` is git-ignored, so this session committed copies to [docs/agentic/rsi-runs/2026-10-21-laptop/](../agentic/rsi-runs/README.md) (`rsi-log.jsonl` 348 rows, `session-log.jsonl` 7633 rows since 2026-10-11, `summary.json`). The GPU box adds its own folder the same way, so both machines can be combined for the report.
- **Owner answers this session (local L0 AskUserQuestion):**
  - **Prompt 28, EXTRACT-NL-DIFF:** "Yes, merge #277's diff". Recorded on #277 in comment 6327249339 and in its owner-decisions row.
  - **Prompt 29, REDACT-NG-GT-DIFF:** "Yes, merge with rule last". Recorded on #276 in comment 6328178224 and in its owner-decisions row.
  - Prompt 29 supersedes the "right after name_context" placement in REDACT-NG-GT-SCOPE. An L0 read-only investigation found that the "0 newly visible" figure shown for REDACT-NG-GT-SCOPE came from a generator that reached the rule on 2 of 40,000 inputs. Placed right after `name_context`, the rule leaks on 3872/3901 of 40k HC-025 inputs: it consumes the anchor a later strict rule needs. Placed last, it leaks on 0.
- **rsi-loop ran with the mod loaded** (`run_id 2026-10-21-local`). It logged 344 tool calls (the cloud run logged 0) and found 6 clusters. It made 0 candidates: the session-log clusters carry no command or stderr text, which #271 (RSI-LOG-SESSIONLOG) adds.
- **Progress dashboard:** a private artifact built from queue.md on `a8e5ead`, at https://claude.ai/artifact/Fd658oHTdingcbggbcLEQC. It is a fixed snapshot: ask L0 to refresh it.

### L0 rulings this session (binding, on the PRs)

- **#264 B-3 (6325488646):** option (a). Inject `AllowJudge` at request time via `patch('modules.rag.get_model_runner', ...)` in `test_empty_answer.py`, with no assertion change. Option (b), skipping the judge on an empty answer, is not licensed. The 5 widened test files are acknowledged.
- **#264 / AET (6325911120):** AET-FALLBACK-LABEL could land first beside #264. #264 merges main afterwards and re-runs its full acceptance.
- **#274 (6326101071, 6326185272):** `test_model_settings_api.py` joined the edit list for one `master_db=MagicMock(commit=AsyncMock())` argument. The stopped L2's uncommitted GREEN diff was kept, not reset.
- **B-3 harness flag:** the workflow's "[Security Test Removal]" warning was a false positive. On the three-dot diff, 0 test functions, 0 assertions and 0 skips were removed; the 12 deleted lines were `with patch(...)` lines rewritten to add `AllowJudge`.

## 2. Open PRs at handoff

| PR | Item | State | Next step |
|---|---|---|---|
| #266 | GC5-PREDICT-FAILCLOSED | ready, refreshed on main at `aa7ffa6` (88 focused passed, legacy gate PASS) | **Owner merges**. Then plan or ask GC5-NEUTRAL-DIFF for GC5-NLI-NEUTRAL |
| #271 | RSI-LOG-SESSIONLOG | ready at `b2a5a72` | **Owner merges** (RSI) |
| #264 | B-3 advice judge | draft at `48a50b5`; 148 focused passed; +39 tests | Merge main again (#278 touched `api/assistant.py`). It stays a draft until the **B-4 sign-off**. The S5 judge measurement needs the GPU box |
| #210 | F-9 showcase | draft; O-6 answered (conditional) | Run F-9 Task 10 on the GPU box (§3 step 2) |
| #230, #239 | RSI candidate / RSI1-DONATE PR-2 | owner / parked | Untouched |

Owner merge commands (Windows cmd or WSL; `--delete-branch=false` keeps WSL worktrees):

```
gh pr merge 266 --merge --delete-branch=false
gh pr merge 271 --merge --delete-branch=false
```

## 3. Next (GPU box, RTX 3080)

1. **Model-host items, holding all three pyslot locks and running no pytest during model runs:**
   - MM-4 re-smoke of current main (fresh clone in `~`, `dev.sh`, Playwright);
   - B-3's S5 two-pass judge measurement (180 block / 200 allow, PR3-S5N) on #264;
   - the B-9 judge check after B-3;
   - MM-2 after OW-3.
2. **F-9 Task 10, the claim freeze (O-6, prompt 30).** `{FREEZE_DATE}` is the session date (2026-10-22).
   - On #210, run plan §10 checks 1-11 at main's SHA and paste each output into plan §15.
   - Check 8 needs the Task 9 dry-run record (owner, Windows demo machine). If it is missing, stop and ask the owner.
   - If all 11 pass, record O-6 as signed for that date, commit C7 and mark #210 ready.
   - If any check fails, stop and ask the owner.
   - O-1, O-2, O-5 and O-7 were answered yes on 2026-10-20; O-3 and O-4 still gate only their own tasks.
3. **After the owner merges #266 and #271:** ask GC5-NEUTRAL-DIFF (GC5-NLI-NEUTRAL). Then run rsi-loop again so the clusters carry error classes.
4. **Plan the new backlog bullets:** AGENT-CACHE-CARETASKS (`api/assistant.py` `_profile_version` leaves care tasks out of the agent cache key), RUNNER-EXC-LOG (`core/model_runner.py:164,214` log the exception text) and QUEUE-E6-W1. Run one planning agent, then build-wave.
5. **Owner asks:** OW-3, OW-W0, OW-W3, OW-W7, OW-W13 and H2-SETUP. Owner task, not a question: C-P6 waits on the owner running `scripts/fk_orphan_audit.py` on a vault copy and pasting the counts (P6-ORPHAN answered 2026-10-16).
6. **RSI archive:** after each rsi-loop run, copy the logs to `docs/agentic/rsi-runs/<date>-gpubox/` per [its README](../agentic/rsi-runs/README.md). Commit them with the next docs PR, after the secret scan.
7. **Count slots:** main is 2315 collected after #276 (the slots say 2291). The next post-merge batch updates them.

## 4. Harness gotchas (local)

- **`gh pr edit` fails** with the "Projects (classic) is being deprecated" GraphQL error. Use `gh api -X PATCH repos/{owner}/{repo}/pulls/N`. `gh pr ready`, `gh pr comment` and `gh pr merge` work.
- **Read the harness's security flags before you trust a workflow, and verify them against the three-dot diff.** One flag was a false positive this session (B-3 above).
- **A build-item resume stops on a dirty worktree** (go=false, nothing touched), and also on a `[claim:claude]` title. Rule explicitly (keep or discard; retitle `[escalated:claude]` plus a fresh `L0 ruling:` comment) and say so in the `l0_note`.
- **A haiku queue parser misreads gate status.** It missed REDACT-NG-GT-DIFF, OW-3 and O-6. (Its "P6-ORPHAN answered" was right; L0 wrongly overrode it from the 21b handoff.) Check owner gates against owner-decisions by hand.
- **rsi-loop writes no summary file when it finds nothing to propose.** Copy the workflow result into `summary.json` by hand.
- Unchanged: never `ruff format`; three-dot diffs only; docs PRs merge one at a time (regenerate `docs/INDEX.md` after merging main); merge only after a review PASS; RSI PRs (#230, #271) and #239 are never agent-merged; the owner merges with `gh pr merge N --merge --delete-branch=false` so WSL worktrees survive.

## 5. /goal prompt for the next L0 (GPU box)

```
/goal Resume the Asclexis build program on the RTX 3080 GPU box from docs/plans/2026-10-21c-session-handoff.md (read it, CLAUDE.md, AGENT.md and the build-program RUNBOOK first; verify every claim with gh / git log). Setup: fresh clone or fast-forward main, venv ~/venvs/asclexis-311 with src/backend/requirements.txt, the embedding bundle in every worktree (cd src/backend && python scripts/download_models.py embedding), measure the collected count (expect 2315 on 79963ee plus later merges) and `from main import app`, recreate merge_par.sh per the 2026-10-21 handoff §5, confirm a local model runs through ModelRunner, and start the session with --plugin-dir .claude/mods/asclexis-rsi. Then: (1) model-host items holding all three pyslot locks, no pytest during model runs: MM-4 re-smoke, B-3 S5 two-pass judge measurement on #264 (post results on #264; it stays a draft until B-4), B-9 judge check, MM-2 after OW-3; (2) F-9 Task 10 claim freeze per owner O-6 prompt 30 (#210 comment 6329347525): FREEZE_DATE = today, run plan §10 checks 1-11 at main's SHA into §15, sign O-6 only if all 11 pass, else stop and ask; check 8 needs the owner's Task 9 dry-run record; (3) after the owner merges #266 and #271 ask GC5-NEUTRAL-DIFF and run rsi-loop; (4) plan AGENT-CACHE-CARETASKS, RUNNER-EXC-LOG, QUEUE-E6-W1, run build-wave and start every eligible row as its own top-level build-item workflow in one message; (5) archive this machine's RSI logs to docs/agentic/rsi-runs/<date>-gpubox/ per its README. Merge each non-owner PR yourself once it has a review PASS and all checks green; RSI PRs (#230, #271), #266 and #239 are never agent-merged. Rules as in CLAUDE.md: owner gates never inferred; ask-first diffs need the owner's yes; never ruff format; three-dot diffs only. Done when every non-owner-blocked row is merged or has a documented stop, the RSI archive has a gpubox folder, a new handoff replaces this one, and rsi-loop has run once with the mod loaded.
```
