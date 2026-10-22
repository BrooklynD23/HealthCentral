# Session handoff: 2026-10-21 cloud L0 → local dev machine

**Last Updated:** 2026-10-21
**Owner:** repository owner
**Refresh Trigger:** the next L0 session reads this first, works §3, and replaces this file with its own handoff.

Read this after [CLAUDE.md](../../CLAUDE.md), [AGENT.md](../../AGENT.md) and the [build-program RUNBOOK](2026-10-15-build-program/RUNBOOK.md). It replaces [the 2026-10-21 GPU handoff](2026-10-21-session-handoff.md). This session ran as a **cloud** L0 (claude.ai/code container, Linux, 4 CPUs, no GPU, no model host). The owner's instruction at the end: "pull this back to the local dev machine … commit everything & push, then provide a goal handoff to continue parallelizing dynamic workflow agents." Every branch is pushed and every worktree was clean at handoff. Treat this file as a lead: verify with `gh pr view` / `git log origin/main` before acting.

## 1. What this session did

- **Setup measured (cloud):** main `3f2484f` at start: `2125 tests collected`, `from main import app` ok. Main `5c94a75` at handoff: **`2233 tests collected`**, app import ok (slots `CLAUDE.md:30`, `:39` and `AGENT.md:76` updated to 2233 in this PR). The embedding bundle could **not** be fetched: the cloud network policy blocks `huggingface.co`, so locally the 5 CLAUDE.md environmental tests failed on every run here. CI has the bundle and was green on every merged head.
- **Merged (12 PRs, each with a review PASS and 8/8 checks green on the merged head):**

  | PR | Item | Merge |
  |---|---|---|
  | #251 | UNCERTAINTY-VERIFY | `2e94b6a` |
  | #261 | plan: GC5 follow-ups, RSI-LOG-*, EMPTY-ANSWER-SERVED | `086466d` |
  | #260 | AUDIT-GUARD-MINORS (resumed) | `b9d285e` |
  | #254 | PATH-REGEX-NEWLINES | `24a46ad` |
  | #256 | HARNESS-VITEST-HINT | `1a41615` |
  | #255 | AGENT-ENABLED-TOGGLE | `376df7c` |
  | #262 | G-C5 Task 7 model-host evidence | `7bbdddd` |
  | #265 | FEATURE-LIST-LICENCE | `14e721d` |
  | #263 | 2026-10-21 GPU handoff | `596abb6` |
  | #246 | REDACT-NAME-GAPS (resumed) | `518ea96` |
  | #269 | owner prompts 22-26 recorded | `68bfba1` |
  | #270 | EMPTY-ANSWER-SERVED | `5c94a75` |

- **Built to READY (owner merges):** #266 GC5-PREDICT-FAILCLOSED, #267 RSI-LOG-STDERR (RSI). **Built to READY (agent may merge):** #268 GC5-FAITH-SCORE.
- **Planned:** #272 (AET-FALLBACK-LABEL, EXTRACT-REGEX-NEWLINES, AUDIT-READ-SETTINGS, RRSI-CI-DOCS, REDACT-NG-GUARD-TAIL); review round 2 REVISE, fixes **not yet pushed** (§3 step 2).
- **rsi-loop ran once** (`run_id 2026-10-21-cloud`): 0 tool calls logged, 0 candidates. This is a logging gap, not a clean result: the cloud session could not start with `--plugin-dir .claude/mods/asclexis-rsi`.

### Owner answers this session (cloud L0 AskUserQuestion)

Prompts 22-26 are recorded in `owner-decisions-2026-09-27.md` (#269). **Prompt 27 is NOT yet recorded there.**

| Prompt | Gate | Answer | Record |
|---|---|---|---|
| 23 | UNC-VERIFY-DIFF | (a) yes, merge #251's diff | owner-decisions row |
| 23 | PATH-NL-DIFF | (a) yes, merge #254's diff | owner-decisions row |
| 23 | REDACT-NG-TRADE / REDACT-NG-DIFF | (a) accept the strict net trade / yes | owner-decisions rows |
| 24 | AUDIT-READ-SCOPE | (a) audit four settings reads; download-progress is a labelled exception | owner-decisions row; verbatim in #272 comment 6321858654 |
| 25 | REDACT-NG-TAIL | merge #246; follow-up row REDACT-NG-GUARD-TAIL | owner-decisions row; #246 comment 6321723199 |
| 25 | AET-PREMISE | yes, label the fallback too, but reword both paths | owner-decisions row; #272 comment 6321858654 |
| 26 | AET-WORDING | `Open follow-up you saved (wording taken from your documents, not checked): …` (supersedes AET-LABEL (a) on the agent path) | owner-decisions row; #272 comment 6321858654 |
| 27 | **REDACT-NG-GT-SCOPE** | (a) build the strict-only `name_guard_tail` candidate (guard word redacted with the value) | **only** #272 comment 6322138371; add the owner-decisions row (in #272, as #261 did for prompt 21) |

### L0 rulings this session (binding, on the PRs)

- **Sequencing (#264 6320313698, #266, #268):** GC5-PREDICT-FAILCLOSED, GC5-FAITH-SCORE and EMPTY-ANSWER-SERVED may run beside B-3 and beside each other. B-3 is a parked draft until B-4 and lands last. Second-lander rule: the later PR merges `origin/main` (merge, no rebase) and re-runs its full acceptance before it is merged.
- **#268 (6321681016):** the 4 `MEASURED` entries of `tests/legacy_eval/test_legacy_eval_gate.py` are re-measured under 4 conditions (every `is_valid` unchanged; only `validation_errors` move; no other line; legacy gate PASS and byte-identical on main and branch). All 4 were met. The queue row file list still omits that file: fix it in the next batch.
- **#264 B-3 (6322138768):** add one row to `tests/test_audit_order_guard.py` naming `advice_judge.py::loaded_model_path::finder` (HC-AUD-ORD-030). Nothing else in that file.
- **RSI-LOG-SESSIONLOG:** built against #267's class list. It stays a draft until the owner merges #267, and the owner merges it as well.

## 2. Open PRs at handoff

| PR | Item | State | Next step |
|---|---|---|---|
| #268 | GC5-FAITH-SCORE | ready, review PASS, CI green on `3146484` except E2E still running at last look | **Second lander:** main moved (#270 also edits `rag.py`): merge `origin/main`, re-run full acceptance and the legacy gate, push, wait green, then L0 merges |
| #266 | GC5-PREDICT-FAILCLOSED | ready, 2× review PASS | **Owner merges** (GC5-PFC-DIFF). If #268 lands first, merge main and re-run acceptance first. Unblocks GC5-NLI-NEUTRAL (needs GC5-NEUTRAL-DIFF) |
| #267 | RSI-LOG-STDERR | ready, review PASS | **Owner merges** (RSI). Then #271 resumes |
| #271 | RSI-LOG-SESSIONLOG | draft `[blocked:claude]` | After #267 merges: `build-item {id: "RSI-LOG-SESSIONLOG", resume_pr: 271}` (merge main; HC-SLOG-004 then passes). **Owner merges** |
| #264 | B-3 advice-judge | draft `[blocked:claude]`, head `7c652ab` | `build-item {id: "B-3", resume_pr: 264}` with the ruling above; merge main after #266/#268 land. Stays a draft until B-4. The S5 two-pass judge measurement runs on the model host |
| #272 | plan: five rows | review round 2 **REVISE** | Push the round-2 fixes (§3 step 2), then round 3. Merge as a docs PR, alone |
| #259 | RRSI-CI-REPLAY | ready | **Owner merges** (RRSI-OQ-4, squash). Then #230 re-runs; RRSI-CI-DOCS unblocks |
| #230 | RSI candidate | owner | Untouched |
| #239 | RSI1-DONATE PR-2 | parked (DON-RECALL-R2) | Untouched |
| #210 | F-9 showcase | draft | On or after **2026-10-24** ask the owner **O-6** |

## 3. Next (local L0)

1. **Setup:** fast-forward main; venv `~/venvs/asclexis-311` with `src/backend/requirements.txt`; the embedding bundle in every worktree (`cd src/backend && python scripts/download_models.py embedding`); measure the collected count (expect 2233 on `5c94a75`, plus whatever merged since) and `from main import app`. Start the session with `--plugin-dir .claude/mods/asclexis-rsi`. Recreate `merge_par.sh` per [the 2026-10-21 handoff §5](2026-10-21-session-handoff.md#5-harness-defects-and-gotchas) (`tr -d '\r'`, 20 lines, `bash -n`). Locally `gh` GraphQL works again, so `merge_par.sh` runs as written.
2. **#272 round-2 fixes** (review comment 6322039225; worktree `hc-plan-s4`, merge main first):
   - (MAJOR) add REDACT-NG-GT-SCOPE as REDACT-NG-GUARD-TAIL's execution gate, answered (a), citing #272 comment 6322138371, in lane E §2.22a, the lane E §5 gate table and the queue row, and add its owner-decisions row ("via prompt 27" on Last Updated). REDACT-NG-GT-DIFF stays merge-only.
   - Add a surname example (`Dr Smith` → `[ID-REDACTED]`) to the REDACT-NG-GT-DIFF question.
   - Write the combining-mark range as `̀-ͯ`, not raw characters.
   - Refresh the stale queue section paragraph (`:411`) and lane D `:816`.
   - The reviewer asked for "ready once #269 merges"; #269 has merged, so keep "ready" and re-check that each cited owner row resolves on main.
   - Leave the queue PATH-NL-DIFF lines alone.
   - Widen HC-AGQ-050 scope to `:522-525`; fix the `:191-193` → `:193` nit.

   Then run review round 3, then merge (docs PR, alone; regenerate `docs/INDEX.md` after merging main).
3. **Merges:** #268 (second lander, above). Owner merges #266, #267, #259 when they choose; after each, re-run the dependents (§2).
4. **build-wave, then one top-level `build-item` per row, all in one message.** Ready once #272 merges, all file-disjoint except where noted:
   - AET-FALLBACK-LABEL (`draft.py`, `api/assistant.py`; never beside B-3 unless an L0 ruling allows it: #264 holds `api/assistant.py`)
   - AUDIT-READ-SETTINGS (AUDIT-READ-SCOPE (a))
   - REDACT-NG-GUARD-TAIL (REDACT-NG-GT-SCOPE (a); merge needs REDACT-NG-GT-DIFF)
   - EXTRACT-REGEX-NEWLINES (build allowed; merge needs EXTRACT-NL-DIFF)
   - RRSI-CI-DOCS after #259

   Resumes: B-3 (#264), RSI-LOG-SESSIONLOG (#271, after #267). After GC5-PREDICT-FAILCLOSED merges, plan or ask **GC5-NEUTRAL-DIFF** for GC5-NLI-NEUTRAL.
5. **Owner asks:** EXTRACT-NL-DIFF and REDACT-NG-GT-DIFF (each with its draft PR's exact diff and differential), GC5-NEUTRAL-DIFF, O-6 on or after 2026-10-24, P6-ORPHAN (C-P6 Tasks 2-5 wait on the owner's real-vault orphan counts; P6-Q1/Q3 are answered, so the queue status is stale), OW-3, OW-W0/W3/W7.
6. **Model host only:** see §4.
7. **RSI:** `rsi-loop` once after the day's run, with the mod loaded.

### Parallelism that worked (keep it)

- **L0 stays the orchestrator.** It starts every eligible row as its own **top-level** `build-item` Workflow in one message (each gets its own agent cap). Resumes get `{id, resume_pr}`. Pass environment facts and rulings as `l0_note` (max 2000 chars). Agents verify them against the comment IDs the note cites.
- **Review and planning run as background agents beside the builds.** Use a planning agent per batch of bullets, and an independent reviewer agent per docs PR (rounds via SendMessage). Docs PRs merge one at a time; code PRs merge as each goes green.
- **Stops are cheap.** Each stop this session (#266, #268 ×2, #264, #271) had a one-comment ruling path. Write `L0 ruling:` comments, then resume.
- Watch CI with one Monitor per PR batch (a REST loop over check-runs), not by polling.

## 4. Deferred to local dev machine (could not run in the cloud)

- **The embedding-bundle tests** (5 per CLAUDE.md §4) on every branch built here. CI ran them green on each merged head; re-run them locally on main once.
- **Per-PR "Deferred to local dev machine" sections:** #264, #266, #267, #268, #270 and #271 each list the exact commands not run.
- **Model host (GPU box):**
  - MM-4 re-smoke of current main (memory recipe: fresh clone in `~`, `dev.sh`, Playwright).
  - B-3's S5 two-pass judge measurement (180 block / 200 allow, PR3-S5N).
  - B-9 judge check after B-3.
  - MM-2 after OW-3.

  Hold all three pyslot locks during model runs, and run no pytest.
- **rsi-loop with the mod loaded:** the cloud run logged nothing.

## 5. Harness defects and gotchas (cloud-specific, recorded for the next cloud session)

- **gh GraphQL is blocked in cloud sessions (HTTP 403).** `gh pr list/view/edit/comment/ready/create/diff` and `merge_par.sh` fail. REST works: use `gh api repos/{owner}/{repo}/...`, `POST …/pulls/N/ccr/ready_for_review` and `PATCH …/pulls/N` (title/body). build-item agents adapted when the `l0_note` listed these.
- **The MCP `update_pull_request_branch` call desynced two PRs.** It errored ("expected head sha didn't match") but still moved the branch refs of #255/#256, and GitHub never refreshed the PRs (stale head, no CI). Two attempted fixes were refused by the permission classifier: a force-push round-trip and an auto-merge loop script. The fix that worked was merging the next `main` into each branch, a real commit. In the cloud, update branches with `git merge origin/main && git push`, never that MCP call.
- **`huggingface.co` is denied by the cloud network policy.** The owner can allow it under the environment's Network access settings.
- `pkill -f <pattern>` inside a Bash command matches its own command line and kills it.
- Unchanged: never `ruff format`; three-dot diffs only; docs PRs merge one at a time (regenerate `docs/INDEX.md` after merging main); merge only after a reviewer's PASS; RSI PRs (#230, #259, #267, #271) and #239 are never agent-merged.

## 6. /goal prompt for the next L0 (local dev machine)

```
/goal Resume the Asclexis build program from docs/plans/2026-10-21b-session-handoff.md. Setup per its §3 step 1 (fast-forward main, venv ~/venvs/asclexis-311, embedding bundle in every worktree, measure collected count + app import, recreate merge_par.sh, start with --plugin-dir .claude/mods/asclexis-rsi). Then, maximising parallel dynamic workflows with L0 as the orchestrator: (1) push the #272 round-2 fixes (record REDACT-NG-GT-SCOPE (a) from #272 comment 6322138371), get a review PASS, merge it alone; (2) #268 as second lander (merge main, re-run acceptance + legacy gate, green, merge); (3) run build-wave and start every eligible row as its own top-level build-item workflow in one message (AET-FALLBACK-LABEL, AUDIT-READ-SETTINGS, REDACT-NG-GUARD-TAIL, EXTRACT-REGEX-NEWLINES, RRSI-CI-DOCS after #259) plus resumes (B-3 resume_pr 264; RSI-LOG-SESSIONLOG resume_pr 271 after #267), with a background reviewer agent per docs PR and a planning agent for any new bullets; (4) ask the owner each merge-only diff gate (EXTRACT-NL-DIFF, REDACT-NG-GT-DIFF, GC5-NEUTRAL-DIFF) with the exact diff once its draft exists, and O-6 on or after 2026-10-24; (5) run the §4 deferred items that need this machine (embedding tests on main; model-host steps only on the GPU box). Merge each non-owner PR yourself once it has a review PASS and all checks green; RSI PRs (#230, #259, #267, #271), #266 (owner merges) and #239 are never agent-merged. Rules as in CLAUDE.md: owner gates never inferred; ask-first diffs need the owner's yes; never ruff format; three-dot diffs only. Done when every non-owner-blocked row is merged or has a documented stop, a new handoff replaces this one, and rsi-loop has run once with the mod loaded.
```
