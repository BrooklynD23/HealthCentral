# Session handoff: 2026-10-28/29 GPU-box L0 → next L0

**Last Updated:** 2026-10-29
**Owner:** repository owner
**Refresh Trigger:** the next L0 session reads this first, works §3, and replaces this file with its own handoff.

Read this after [CLAUDE.md](../../CLAUDE.md), [AGENT.md](../../AGENT.md) and the [build-program RUNBOOK](2026-10-15-build-program/RUNBOOK.md). It replaces [the 2026-10-26 handoff](2026-10-26-session-handoff.md). Main is at `144b5d4` (#411) when this was written. Treat everything below as a lead: verify it with `gh pr view N` and `git log origin/main` before you act on it. This PR itself was not reviewed before the session ran out of context, so the next L0 has it Opus-reviewed and merges it.

## 1. What this session did

- **Merged, in order:**
  - #391 post-merge batch: the count went to 2545.
  - #370 UI-SHELL `b1ee579`. Before merging, L0 ran T4 on dev and preview, and an A/B of HC-UIPV-006 gave 20/20 on main and 20/20 on the branch.
  - #392 four follow-up plans.
  - #394 batch: UI-SHELL marked done.
  - #395 QWEN3-4B-TIER evidence, recorded as **partly met**.
  - #396 VITEST-TZ-PIN `434179a`.
  - #397 AUDIT-GUARD-ATTR-DYNAMIC `f7c5dcd`.
  - #402 SESSION-REENTRY Task 3 `8e4c977`.
  - #403 SAFETY-MODE-TOGGLE plan delta.
  - #404 DARK-PRIMITIVE-CONTRAST plan.
  - #405 DARK-PRIMITIVE-CONTRAST `41fa382`.
  - #406 batch: the count went to 2547.
  - #407 POPOVER-OPEN-COST widened to dialog opens.
  - #408 routing.
  - #409 TOAST-SHELL plan.
  - #411 batch.
- **Owner answers this session.** Each is recorded verbatim in owner-decisions.
  - **SAFETY-NOTE-WORDING:** "Specific, staged".
  - **MODEL-ROUTING-SONNET**, a chat direction given on 2026-10-29: "Revert the changes. Set Haiku 5.5 agent medium to be in charge of running test scripts only. Sonnet 5.5 agents for implementations…". It was applied in #408: Sonnet implements, and Haiku at effort `medium` runs test scripts only. It supersedes MODEL-ROUTING-HAIKU.
  - **Shared box:** the owner chose "I'll pause Stellaris".
- **Collected count:** 2547 on main.
- **Dashboard** refreshed on 2026-10-29: https://claude.ai/artifact/61W8zR9zbR3QbGtwREWrgf (242 rows, 187 done, 77%).

## 2. Open PRs at handoff

| PR | Item | State | Next |
|---|---|---|---|
| #410 | TOAST-SHELL | `[claim:claude]`, running | The `ui-toast` head run is GREEN: L0 got 15 passed for routing plus `ui-toast` with `TMPDIR=/dev/shm`. Tasks 4-8 remain: the dev and preview runs of 5 specs, the preview delta against the baseline, #400's G5 record, vitest/tsc/build/lint, and the backend run. Then review, CI, merge. It **builds before POPOVER-OPEN-COST** on `globals.css`. |
| #393 | POPOVER-OPEN-COST (now covers dialogs) | `[blocked:claude]`, no commits | Resume after #410 merges. The `@property` rule may merge alone if the stop rule fires (plan delta #407). |
| #398 | UI-PG-MEDS | `[blocked:claude]` | Waits for POPOVER-OPEN-COST: HC-UIMED-002's dialog-open stillness misses 40 ms because of the shared `Modal` scroll lock. Review-round-1 fixes are pushed, and L0 rulings A, B and C are done. |
| #400 | UI-PG-CARE | `[blocked:claude]` | Waits for TOAST-SHELL (G5 on `/care-tasks`), then rebases and re-runs dark G1. |
| #399 | UI-PALETTE | `[blocked:claude]` | After #398 merges. L0 ruling 6475095462 licenses `ui-shell.spec.ts` `:165` and `:635-636`. |
| #401 | SAFETY-MODE-TOGGLE | `[blocked:claude]` | After #398, #399 and #402 (#402 is merged). The plan delta (#403) has the owner's wording, a fixed header height and N=4 lines. |
| #316 | launcher bundle | draft | The **owner's Windows session** (WIN-TEST-BUNDLE). |
| #239 | RSI1-DONATE PR-2 | draft, **never agent-merged** | Built and measured **NOT MET**: on R2-gate, age_over_89 is 70%; on R1∪R2, names are 94%, age_over_89 84% and canaries 23/24. The owner decides the next step. |
| #264 | B-3 | draft, **never agent-merged** | Waits on JUDGE-LAYA-FT, JUDGE-NLI-TUNE and JUDGE-SWAP-ADOPT. |

## 3. Next, in order

The quiet-box queue runs strictly one item at a time. The owner asked to "dispatch all 6 ready". L0 explained that they must run serially and queued them in this order:

1. **Finish #410** (TOAST-SHELL), then **#393** (POPOVER-OPEN-COST).
2. **#400**, then **#398**, then **#399**, then UI-PG-EXPORT, then **#401**.
3. **UIG006-PASS3-FLAKE**, then **STILLNESS-NAV-LATE**, then **G1-VERIFY-TRACE-RACE**. Each needs a quiet box.
4. **Model host, one at a time:** AUDIT-DB-LOCKED Task 1, then JUDGE-NLI-TUNE (about 4 h), then JUDGE-LAYA-FT (about 8 h).
5. **Owner prompts.** The owner interrupted these before they were asked. Ask them via AskUserQuestion, and have every drafted question reviewed first:
   - the #316 Windows session;
   - RSI-REPLAY-REQUIRED: not done yet, `main` has no "RSI Replay" required check;
   - SHOW-O3, before **2026-10-31**;
   - EXF-SAMPLE;
   - B-4/OW-3 (nothing to do until the JUDGE rows report);
   - #239's next step;
   - permission to build `llama-bench` for QWEN3-4B-TIER.
6. **New bullets to plan:**
   - NAV70-CI-MISS: HC-UISH-009 failed the 70 ms bound in CI 3 times across 2 runs since #370 (`/search` in run 40920267687). If STILLNESS-NAV-LATE finds no fix, draft an owner question.
   - SOURCE-TRACE-UNWIRED.
   - SHELL-NAVREF-DEAD.
   - UIG002-TITLE.
   - FOREIGN-CHROMIUM-ON-BOX.
   - GH-READY-REFUSED.
   - Also a post-merge batch whenever PRs land.

## 4. Gotchas from this session

- **The WSL disk fsync is slow.** On 2026-10-29 a synchronous 4 KiB write took about 33 ms, and up to about 500 ms under load. Every Playwright page load took 35-150 s.
  - **Run every Playwright run with `TMPDIR=/dev/shm`.** `hold_slots.sh` exports it.
  - Diagnose with `/proc/pressure/io` and `dd bs=4k count=500 oflag=dsync`.
  - The owner cleared drive space on 2026-10-29. Re-measure on a quiet box to see whether that fixed it.
- **The box is shared with the owner's Stellaris-Adaptive-AI-Engine sessions**, which run Rust builds, pytest and Chromium, at load up to 59.
  - Extend the quiet-box precheck to `rustc|cargo|rust-lld|chrom` and foreign pytest.
  - Never kill another project's processes; ask the owner to pause them.
- **A reboot wipes `/tmp/claude-1000`.** Recreate the five scripts from the [2026-10-26 handoff](2026-10-26-session-handoff.md) §4 appendix. Add `--delete-branch=false` to `merge_par.sh`'s merge, and add `export TMPDIR=/dev/shm` to `hold_slots.sh`.
- **`resumeFromRunId` does not survive a restart.** Restart build-items with `resume_pr`. A stopped item can leave a dirty worktree or never post its stop comment. L0 recovered both here (#402, #400): save the work, push or patch it, post the stop, then rule.
- **Implementers sometimes background a long job and return.** Briefs say "never background a long job and return before it finishes; commit and push before returning".
- **The quiet-box rule applies only to stillness timing runs.** Functional e2e and vitest run under normal load (ruling on #402).
- **`gh pr ready` is often refused for build-item agents.** L0 runs it.
- **A security flag fired once on a Task 0 agent** ("Instruction Poisoning", #410). L0 reviewed every action and found it a false positive, triggered by reading routing text in the docs.
- **Docs PRs conflict on queue.md's Last Updated and Totals lines.** Merge them one at a time and resolve by hand: prepend or append both entries.
- **CI E2E on docs PRs can fail on NAV70-CI-MISS.** Re-run once, and record it.
