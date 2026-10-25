# Session handoff: 2026-10-21 GPU session → cloud L0 (merges), then next machine

> **Superseded** by [the 2026-10-21b handoff](../archive/plans/2026-10-21b-session-handoff.md) and its successors (newest: [the 2026-10-24 handoff](2026-10-24-session-handoff.md)); retained for history, not an active tracker.

**Last Updated:** 2026-10-21
**Owner:** repository owner
**Refresh Trigger:** the next L0 session reads this first, works §3, and replaces this file with its own handoff.

Read this after [CLAUDE.md](../../CLAUDE.md), [AGENT.md](../../AGENT.md) and the [build-program RUNBOOK](2026-10-15-build-program/RUNBOOK.md). It replaces [the 2026-10-20c handoff](2026-10-20c-session-handoff.md). This session ran on the owner's GPU WSL box (RTX 3080, Ollama). The owner's instruction at the end: "Commit & push all of our works … provide me a handoff … we will have the cloud agent take care of the merges." Every branch is pushed; nothing is only local. Treat this file as a lead: verify with `gh pr view` / `git log origin/main` before acting.

## 1. What this session did

- **Setup measured (GPU box):** main `b902e0f`, `2118 tests collected` (sentence-transformers 6.1.0, embedding bundle present), `from main import app` ok, ModelRunner → `OllamaProvider` (llama3.1:8b) answered. The venv's torch is `2.14.1+cpu`: the NLI cross-encoder runs on CPU; the GPU is used only through Ollama. The session was started with the asclexis-rsi mod (log rows carry its session id).
- **Merged (L0, `merge_par.sh`, review PASS):** #253 NLI-LOG-M7 (`3e5a835`, +1), #252 RUNSTEP-CONTRACT (`b8e30a3`, +1), #258 CHAT-TREND-DEF (`7fd0c26`, +5), #257 RRSI-H2-SANDBOX runbook (`3f2484f`, 0). Main is `3f2484f`; expected collected 2125 (not measured on main: measure it in the batch).
- **G-C5 Task 7 on the model host:** PR #262 (review round 2 PASS). The laptop's flag-on findings reproduce exactly. New: real LLM output (llama3.1:8b served 0 of 26 both ways; qwen3:8b served 8 flag-off and 7 flag-on). With the flag on, no abstention ever became a served answer. Truncation past 512 tokens did not change the label on one fixture. Pyslot locks were held about 633 s, with no pytest. `use_llm_entailment` stays off.
- **Planning:** #261 planned GC5-PREDICT-FAILCLOSED, GC5-NLI-NEUTRAL, GC5-FAITH-SCORE, FEATURE-LIST-LICENCE, RSI-LOG-STDERR, plus new rows RSI-LOG-SESSIONLOG and EMPTY-ANSWER-SERVED (review round 2 PASS; owner prompt 21 recorded in it).
- **R-22 B-3 Codex plan review:** REVISE. The review is [committed verbatim](../reviews/2026-10-21/b3-codex-plan-review.md). Per R-22 the B-3 L1 fixes the gaps as the first commit on its branch.
- **rsi-loop ran once** (`run_id 2026-10-21-gpu`): 1,951 tool calls; **0 candidates, 0 PRs**. Bash/other 42 failures remain unminable without finer classes. This confirms RSI-LOG-STDERR and RSI-LOG-SESSIONLOG.
- **MM runs:** MM-1 is done (2026-10-16, #72), with no re-run needed. MM-2 is blocked on OW-3 (owner writes sealed set S5) and on B-3. MM-4 is done (2026-10-16); a re-smoke of current main on the model host was **not** run (machine move). B-9's judge check waits on B-3.

### Owner answers this session (L0 AskUserQuestion)

- **Prompt 21** (recorded by #261 in `owner-decisions-2026-09-27.md`): GC5-PFC-DIFF **(a)** approve the hunk in advance; GC5-NEUTRAL-SCOPE **(a)** veto only (the costs the question left out are noted under the row); GC5-FS-SCOPE **(a)** never more than the share of claims verified; RSI-LOG-WIDEN **(b)** add a fixed `error_class` field to `session_log.py` rows.
- **Prompt 22, NOT yet recorded:** EMPTY-ANS-SCOPE **(a) "Treat it as a failed answer"**: "chat shows the existing abstention text ('There isn't enough verified information…') and saves that; the lab explanation shows the caution badge with no text" (one check in `rag.py`). Record it in `owner-decisions-2026-09-27.md` ("answered 2026-10-21, L0 AskUserQuestion, prompt 22") in the post-merge batch, after #261 merges, and set EMPTY-ANSWER-SERVED ready.

### L0 rulings this session (binding, on the PRs)

- **#246 REDACT-NAME-GAPS:** comments 6310876075 and 6311078477. The task-1 `name_context` conditional tail is kept (strict un-redactions per 40k: 321/338 → 190/208; standard 0). The task-2 continuation guard raised strict to 441/452 and was reverted per the stop rule. Leftover rows are pinned as `*_leftover`. HC-REDACT-024 (seeded differential) is committed on the branch.
- **#251 UNCERTAINTY-VERIFY:** comment 6311246284. Fact-free uncertainty hedges stay skipped at extraction, because UNC-VERIFY-SCOPE (a) says "stay unchecked", which means unchanged from main. Cause: `rag.py`'s timeout text is an `UNCERTAINTIES:` hedge, and removing the skip served it. After the fix the legacy gate is PASS with abstention 1.000.
- **#255:** the `Gamification.test.tsx` `@/services` mock was added to the row's file list. **#256:** use the §2.17 parse command with its `export const meta` rewrite.
- **#260 AUDIT-GUARD-MINORS:** retitled `[escalated:claude]`, ruling comment 6319097302. Relabel the 4 read routes `excluded: read route, writes no audit row (follow-up AUDIT-READ-SETTINGS)`; resume with `resume_pr: 260`.
- **RSI-LOG-SESSIONLOG is owner-merged** (conservative; #261 round-2 finding 1: the hook is the Track-1 "Observe leg" and widens a logger approved as metadata-only). Set the queue row to say so in the batch.

## 2. Open PRs at handoff

| PR | Item | State | Next step |
|---|---|---|---|
| #255 | AGENT-ENABLED-TOGGLE | ready, review PASS, all 8 checks green, +1 | **Cloud L0 merges** (`merge_par.sh 255 256`) |
| #256 | HARNESS-VITEST-HINT | ready, review PASS, all 8 green, 0 | **Cloud L0 merges** with #255 |
| #261 | plan: 5 rows + RSI-LOG-SESSIONLOG + EMPTY-ANSWER-SERVED | ready, review round 2 PASS, CI green on `04da78f` | **Cloud L0 merges** after #255/#256, alone (docs PR) |
| #262 | G-C5 Task 7 model-host evidence | ready, review round 2 PASS, CI green on `e6a2470` | **Cloud L0 merges** after #261: merge main into the branch, run `generate_docs_index.py`, push, wait green, merge (docs PRs one at a time) |
| this PR | handoff 2026-10-21 | docs | Cloud L0 merges last, after #262, the same way |
| #251 | UNCERTAINTY-VERIFY | draft, review PASS, gate PASS, +4 | Ask owner **UNC-VERIFY-DIFF** with `gh pr diff 251`. The PR body discloses the deviations. On a yes: ready, merge, then start B-3 (never beside UNCERTAINTY-VERIFY) |
| #254 | PATH-REGEX-NEWLINES | draft, review PASS, +20, differential 0 violations | Ask owner **PATH-NL-DIFF** with `gh pr diff 254` |
| #246 | REDACT-NAME-GAPS | draft `[blocked:claude]` | Ask the owner (with REDACT-NG-DIFF): strict still un-redacts against main on 190/208 of 40k structured inputs (standard 0). Options: (a) accept the net trade as disclosed REDACT-NG-DIFF exceptions; (b) require strict 0 un-redactions against main before merge; (c) widen scope so the run-on stops at the next label. The numbers are in the last "blocked: tell L0" comment |
| #260 | AUDIT-GUARD-MINORS | `[escalated:claude]` + L0 ruling | `build-item {id: "AUDIT-GUARD-MINORS", resume_pr: 260}` |
| #259 | RRSI-CI-REPLAY | ready, CI proven both ways | **Owner merges** (RRSI-OQ-4, squash). Then #230 re-runs on main |
| #239 | RSI1-DONATE PR-2 | parked (DON-RECALL-R2) | Untouched |
| #230 | RSI candidate | owner | Untouched; re-run after #259 |
| #210 | F-9 showcase | draft | On or after **2026-10-24** ask the owner **O-6**, then Task 10 Steps 2-3 |

## 3. Next

1. **Merges (cloud L0):** #255 + #256 → #261 → #262 → this PR, as in §2. Then a **post-merge batch**: record EMPTY-ANS-SCOPE (a), set RSI-LOG-SESSIONLOG to owner-merged, mark the merged rows done, add the §4 bullets, measure the collected count on main and write the slots (`CLAUDE.md:30`, `AGENT.md`). Expected 2126 after #255/#256 (2118 +1 +1 +5 +1), but measure it; do not copy this number.
2. **Owner asks:** UNC-VERIFY-DIFF (#251), PATH-NL-DIFF (#254), REDACT-NAME-GAPS options (#246), GC5-NEUTRAL-DIFF (when its draft exists), O-6 on or after 2026-10-24.
3. **build-wave**, then one top-level `build-item` per id. Ready once #261 is merged: GC5-PREDICT-FAILCLOSED (GC5-PFC-DIFF (a): the one hunk is licensed; owner merges), GC5-FAITH-SCORE (`rag.py` only), FEATURE-LIST-LICENCE, RSI-LOG-STDERR (RSI: owner merges), EMPTY-ANSWER-SERVED (after the prompt 22 row is recorded), then RSI-LOG-SESSIONLOG (after RSI-LOG-STDERR; owner merges). Also resume #260. B-3 goes after #251 is decided, with the [Codex review](../reviews/2026-10-21/b3-codex-plan-review.md) as its first-commit brief.
4. **Plan the new bullets** (§4) once their sources have merged.
5. **Model host only** (not the cloud): the MM-4 re-smoke of current main (memory recipe: fresh clone in `~`, `dev.sh`, Playwright). MM-2 waits on OW-3 and B-3. Hold all three pyslot locks during model runs, and run no pytest.
6. **RSI:** start sessions with `--plugin-dir .claude/mods/asclexis-rsi`; run `rsi-loop` once after the day's run.

## 4. New bullets (not yet planned): add to queue "New rows found while planning"

- **AET-FALLBACK-LABEL** (#255 review MAJOR): the no-model fallback at `api/assistant.py:1319` writes care-task text without the AET-LABEL label, and users who turn the agent off reach it.
- **EXTRACT-REGEX-NEWLINES** (#254 review): `extract_imaging.py` (FINDINGS/IMPRESSION) and `extract_visit_notes.py` (ASSESSMENT/PLAN/VITALS) use the same quadratic newline pattern, about 4.6-4.75 s at 20,000 newlines.
- **AUDIT-READ-SETTINGS** (#260 review): `get_model_settings` and `list_tiers` read per-profile data via `ProfileDbSession` and write no audit row (CLAUDE.md audit invariant). `get_environment_diagnostics` and `recheck_environment_diagnostics` write none either.
- **RRSI-CI-DOCS** (#259): `docs/architecture/ci-and-quality-gates.md` lacks the `rsi-replay` job, and lane E §2.24 Fact 1's grep is wrong (it prints 9 lines). "RSI Replay" is not a required check; only the owner can change branch protection.
- #261 already adds RULES-RANGE-VALUE, LLAMA-CITE-DETACH and EMPTY-ANSWER-SERVED.

## 5. Harness defects and gotchas

- **CRLF:** in the Windows checkout, handoff and queue files have CRLF line endings. Extracting the `merge_par.sh` fence with `sed` silently produced an empty script. Use `tr -d '\r'`.
- **Worktree paths contain a space** ("Github Repo"): parse `git worktree list --porcelain`, not the default output.
- **Haiku runner reports were wrong twice again.** On #254 its warning paths came from another worktree and it reported 2123 passed against 2138 collected. On #255 it skipped vitest for a "stall" that does not happen. The verify step caught both; keep it.
- **build-item stop rules worked:** all 4 stops this session (#246 ×2, #251, #255, #256) had a clear ruling path. Write rulings as `L0 ruling:` comments, and retitle a released draft before resuming it.
- `/tmp/claude-1000` scratch does not move with the repo. Everything that matters is committed: HC-REDACT-024 on #246, the B-3 review in this PR.
- Unchanged: never `ruff format`; use three-dot diffs only; run no pytest during model runs; on Windows, `gh pr merge` prunes WSL worktree metadata; docs PRs merge one at a time (regenerate `docs/INDEX.md` after merging main); merge only after a reviewer's PASS.

`merge_par.sh` is unchanged from [the 2026-10-20c handoff §4](2026-10-20c-session-handoff.md#4-harness-defects-and-gotchas). Recreate it with `sed -n '66,85p' docs/plans/2026-10-20c-session-handoff.md | tr -d '\r' | sed "s|<repo checkout>|$PWD|" > /tmp/claude-1000/merge_par.sh` from the repo root, then run `bash -n` on it and check that it has 20 lines. It never merges RSI PRs on its own: do not pass #230 or #259.

## 6. /goal prompt for the next L0

```
/goal Resume the Asclexis build program from docs/plans/2026-10-21-session-handoff.md. Setup: git fetch and fast-forward main in the main checkout; venv ~/venvs/asclexis-311 with src/backend requirements; embedding bundle in every worktree (cd src/backend && python scripts/download_models.py embedding if missing); recreate /tmp/claude-1000/merge_par.sh per handoff §5; measure the collected count and the app import. Start with --plugin-dir .claude/mods/asclexis-rsi. Then: (1) merge in order with merge_par.sh, each only with a review PASS and all checks green: #255 + #256, then #261 alone, then #262 (merge main into it, regenerate docs/INDEX.md, push, wait green), then the 2026-10-21 handoff PR; run the post-merge batch per handoff §3 item 1 (record owner prompt 22 EMPTY-ANS-SCOPE (a), RSI-LOG-SESSIONLOG owner-merged, the §4 bullets, measured count in the slots); (2) ask the owner UNC-VERIFY-DIFF (#251), PATH-NL-DIFF (#254) with the exact diffs and the REDACT-NAME-GAPS options (#246); (3) run build-wave and start each eligible row as its own top-level build-item workflow (GC5-PREDICT-FAILCLOSED, GC5-FAITH-SCORE, FEATURE-LIST-LICENCE, RSI-LOG-STDERR, EMPTY-ANSWER-SERVED, resume #260; B-3 only after #251 is decided, with the committed Codex review as its first-commit brief); (4) plan the §4 bullets; model-bound steps (MM-4 re-smoke, MM-2 after OW-3) only on the model host. On or after 2026-10-24 ask the owner O-6 for #210. RSI PRs (#230, #259, RSI-LOG-STDERR, RSI-LOG-SESSIONLOG) and #239 are never agent-merged. Rules as in CLAUDE.md: owner gates never inferred; ask-first diffs need the owner's yes; never ruff format; three-dot diffs only. Done when every non-owner-blocked row is merged or has a documented stop, a new handoff replaces this one, and rsi-loop has run once.
```

## 6b. Final report

- **Merged this session:** 4 PRs (#253, #252, #258, #257).
- **Ready for the cloud L0 to merge:** #255, #256, #261, #262 and this handoff PR.
- **Measured count:** 2118 collected on `b902e0f` at session start. Per-PR heads: #253 2119, #252 2119, #258 2123, #255 2119, #256 2118, #251 2122, #254 2138. Main after the merges is not yet measured.
- **Open owner gates:** UNC-VERIFY-DIFF, PATH-NL-DIFF, REDACT-NG-DIFF (+ the #246 options), GC5-NEUTRAL-DIFF, O-6 (2026-10-24), OW-3, P6-ORPHAN, OW-W0/W3/W7, E-6, DON-COPY-V3, RRSI-CRITIC-LIST, COUNT-ENV-VARIES, #230, #259 (owner merges). G-C2 stays deferred, F-8 disabled, #239 parked.
- **Cleanup:** worktrees for merged PRs can go (`git worktree list --porcelain`, then `git worktree remove`). Keep `hc-redact-name-gaps`, `hc-uncertainty-verify`, `hc-path-regex-newlines`, `hc-audit-guard-minors` and `hc-rsi1-donate` until their PRs resolve.
