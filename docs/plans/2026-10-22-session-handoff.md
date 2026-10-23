# Session handoff: 2026-10-22 GPU-box L0 (RTX 3080) → next L0

**Last Updated:** 2026-10-22
**Owner:** repository owner
**Refresh Trigger:** the next L0 session reads this first, works §3, and replaces this file with its own handoff.

Read this after [CLAUDE.md](../../CLAUDE.md), [AGENT.md](../../AGENT.md) and the [build-program RUNBOOK](2026-10-15-build-program/RUNBOOK.md). It replaces [the 2026-10-21c handoff](2026-10-21c-session-handoff.md). This session ran as the **GPU-box** L0 (RTX 3080, WSL, Ollama 0.40.5 with gemma4:e4b, llama3.1:8b, qwen3:8b and gemma3:12b), from 2026-10-21 evening to 2026-10-22, started from main `c97192d` with `--plugin-dir .claude/mods/asclexis-rsi`. Treat this file as a lead: verify with `gh pr view` / `git log origin/main` before acting. PR states below were checked at write time (main `afbe1af`); several PRs were still in CI.

## 1. What this session did

- **Setup (main `c97192d`):** `2328 tests collected`, `from main import app` ok, Ollama and the RSI mod loaded. `merge_par.sh` was recreated from the 2026-10-20c handoff lines 67-86 (the 21 handoff's "66,85" was off by one). `hold_slots.sh` now holds pyslot locks 1-8: a `PYSLOTS>3` pytest slipped past the 3-lock version. `chain_merge.sh` and `docs_chain.sh` merge PRs in order; `docs_chain.sh` regenerates `docs/INDEX.md` and `docs/_link_graph.json` on index-only conflicts. All four scripts are pasted in the §4 appendix: recreate them from there.
- **Merged by L0 (each re-verified with one focused test run, review PASS, green checks):** #282, #281, #283 GC5-NLI-NEUTRAL, #285 RUNNER-EXC-LOG, #286, #287, #210 F-9 showcase (below), #288, #289 (13-row bug plan), #290 AGENT-CACHE-CARETASKS, #291, #292 (README and architecture refresh), #293, #294 (mg/L lab lines and DOB), #296 (archive), #297 (llama provider: chat_format, serial lock, GPU layers), #298 (KV evidence), #299 (MVP research), #301. **Owner merged** #266 and #271 before the session (`f6019f1`, `c97192d`).
- **F-9 / O-6:** signed 2026-10-22 under the owner's conditional answer (prompt 30), all 11 §10 checks pass at `75c1106`. The Task 9 dry run is recorded on #210 (comment 6334394792). #210 merged as `0f7939e`.
- **Owner prompts 31-41 answered**, all verbatim in [owner-decisions-2026-09-27.md](../capstone-report/owner-decisions-2026-09-27.md) (machine-readable copies in `/tmp/claude-1000/prompts-33-37.json`, `-38-39.json`, `-40-41.json`, which are not committed):

  | Prompt item | Answer |
  |---|---|
  | GC5-NEUTRAL-DIFF | yes |
  | O-6-CHECK8 | L0 dry run |
  | CACHE-STALE | (c) |
  | KV-CACHE-NEXT | measure first |
  | RSI1-DONATE-PR2 | plan an on-device detector |
  | DON-COPY-V3 | (a) |
  | SHOW-O3 | yes |
  | RRSI-CRITIC-LIST | (a) |
  | NPM-AUDIT-CI | scheduled |
  | RSI-REPLAY-REQUIRED | make it required (owner action) |
  | OW-W7 | research the MIT decoder |
  | OW-W13 | order P6, G-C1, WEAR-02, WEAR-15 |
  | EXF-SAMPLE | share one page (owner action) |
  | H2-ALT | Codex as second proposer (H2-SETUP superseded) |
  | JUDGE-THINK | think-off now, research Laya |
  | INTERP-DISC-ORDER | (a) |
  | EXTRACT-DATE-PRIORITY | (a) |
  | INTERP-SAFETY-ENFORCE | plan the enforce fix |
  | SQLCIPHER-WHEEL | free text: sqlcipher3 on Windows and macOS, keep Linux |
  | SESSION-REENTRY | (a) unlock screen |
  | OCR-FOR-MVP | (b) bundle RapidOCR |
  | MVP-PACKAGING | (a) then (c) installer |
  | CPU-DEFAULT-MODEL | "A and B" |
  | CODE-SIGNING | (a) none |
  | TEST-DEV-DEPS | (a) |
  | OQ-KV-LOCK | (a) accept the window |

  OW-3 (sealed S5) is still open: guide and validator at `~/asclexis-sealed/` (`S5-GUIDE.md`, `check_s5.py`); the owner writes S5. The mid GGUF tier is downloaded at `~/asclexis-models/gguf/microsoft_Phi-4-mini-instruct-Q4_K_M.gguf` (sha256 `01999f17c39cc3074afae5e9c539bc82d45f2dd7faa3917c66cbef76fce8c0c2`).
- **GPU-box evidence:**
  - MM-4 re-smoke and the F-9 Task 9 dry run (record on #210, comment 6334394792).
  - B-9 full suite `2338 passed` at `386ad18`.
  - B-3 judge app check **fails closed**: gemma4 withholds every answer; llama3.1:8b ALLOW in about 0.1 s.
  - GC5 flag-on legacy gate PASS on main.
  - KV measurement (#298): Ollama ran at 4096, the largest legacy prompt was truncated, 8192 recommended. A profile lock leaves the model loaded until keep_alive (owner accepted, OQ-KV-LOCK (a)).
- **rsi-loop has NOT run this session** with the mod loaded (§3 step 9).
- **Progress dashboard:** https://claude.ai/artifact/GWTm1XfwuuZZe2mFVFXBuv, a snapshot at 19:23 UTC on main `5f7c67c`. It is owned by an account used this session; the old `Fd658…` link is not readable from it. Refreshing it is a Sonnet task.

### L0 rulings this session

The L0 rulings are on the PRs themselves; the binding ones are the #210 O-6 sign-off and the #284 resume ruling (QUEUE-E6-W1 under the corrected acceptance in #289). Owner free-text answers are quoted verbatim in the owner-decisions file, never summarised (the #291 correction).

## 2. Open PRs at handoff

States checked with `gh pr view` at write time (main `afbe1af`).

| PR | Item | State at write time | Next step |
|---|---|---|---|
| #295 | frontend bundle (interp grounded markdown, gauge axis, citation keys) | ready; Fable PASS; E2E Smoke still running | In the merge chain: merge after green |
| #300 | RUNNER-EXC-CHAIN | ready; Fable PASS; 9/9 green | In the chain: merge |
| #284 | QUEUE-E6-W1 | ready; Fable PASS; 9/9 green | In the chain: merge |
| #304 | INTERP-SAFETY-META | ready; review round 1 PASS; Backend, Security, Agent Eval and Legacy RAG gates still running | Merge after green. INTERP-SAFETY-ENFORCE waits on it |
| #305 | JUDGE-THINK | draft; build-item workflow was still running | Check the workflow finished; review loop; merge |
| #306 | NPM-AUDIT-SCHEDULED | draft; build-item workflow was still running | Same |
| #302 | FIT-DECODER-RESEARCH | draft; build-item workflow was still running | Same |
| #303 | RSI-CODEX-PROPOSER | draft; build-item workflow was still running | Same; RSI PR: **owner merges** |
| #307 | MVP plan (35 rows) from the MVP planner | ready; **no review comment yet**; E2E Smoke running | Check its review loop finished (it did not, at write time); merge after PASS |
| #264 | B-3 advice judge | draft | Draft until B-4; never agent-merged |
| #239 | RSI1-DONATE PR-2 | draft, parked | Never agent-merged |
| #230 | RSI candidate | ready | Owner merges |

The four workflows (#302, #303, #305, #306) may have died with the session: if a PR is still `[claim:claude]` with no workflow, resume it with `build-item {id, resume_pr}` after a dirty-worktree ruling.

Owner merge commands:

```
gh pr merge 230 --merge --delete-branch=false
gh pr merge 303 --merge --delete-branch=false
```

## 3. Next

1. **Finish the merge chain** (non-RSI PRs only, review PASS and green CI): #284, #300, #295, #304, then #305, #306, #302 and #307 once their review loops end. Use `chain_merge.sh` / `docs_chain.sh` from the §4 appendix; one focused test run per code PR before merging. #230, #303, #239 and #264 are never agent-merged.
2. **Post-merge batch** (one docs PR, orchestrator edits): update the count slots in CLAUDE.md and AGENT.md (main collects about 2372 or more: **measure**); queue Last Updated and Totals; mark done rows; KV-PREFIX-MEASURE done, OLLAMA-NUM-CTX ready at 8192; fix the CLAUDE.md embedding command to `cd src/backend` first (it sits in a slot paragraph, so the orchestrator edits it in the batch, not a PR).
3. **build-wave**, then start every eligible row as its own top-level build-item workflow in one message: INTERP-SAFETY-ENFORCE after #304; OLLAMA-NUM-CTX after JUDGE-THINK; the #307 MVP rows once it merges. MVP blockers first: SQLCIPHER per-OS (gate SQLC-WHEEL-DIFF), session unlock, extract table and text forms, scanned-page warning plus RapidOCR, `dev.ps1` first-run, FE import errors, re-auth 401.
4. **Model-host rows on this box**, holding `hold_slots.sh` with no pytest running: DON-NER-MEASURE, JUDGE-LAYA-RESEARCH, AUDIT-DB-LOCKED Task 1 repro, QWEN3-4B tier after JUDGE-THINK.
5. **Ask the owner the new gates** as their inputs arrive: DON-NER-MODEL, WEAR-FIT-LIC, INTERP-ENFORCE-DIFF, JUDGE-SWAP, SQLC-WHEEL-DIFF, SESSION-AUTH-DIFF, DB-LOCK-FIX (after the repro), CPU-MODEL-FINAL, VISIT-ASSIST-THINK. Docs-agent questions: bulky record files, archiving the 6 remaining handoffs, DOC-OVERCLAIM-2. Owner gates are never inferred.
6. **Owner actions pending** (remind, do not do): write S5 (OW-3); P6 orphan audit on a vault copy; Garmin export notes (OW-W3); one de-identified lab page (EXF-SAMPLE); add "RSI Replay" as a required check; demo-clone `.env` (SHOW-O3) before 2026-10-31.
7. **Refresh the dashboard** (Sonnet task) from queue.md on the new main.
8. **Archive this machine's RSI logs:** copy `.claude/logs/rsi/*.jsonl` and `.claude/logs/session-log.jsonl` (since 2026-10-21) to `docs/agentic/rsi-runs/2026-10-22-gpubox/` per [its README](../agentic/rsi-runs/README.md), after a secret scan.
9. **Run rsi-loop** with the mod loaded (it has not run this session), then do step 8 again for the new rows.
10. **Write the next handoff** replacing this file.

## 4. Harness gotchas

- **Claude Code accounts switched 3 times** this session (rate limits; an org 403 `oauth_org_not_allowed`). Subagents died mid-run: always resume with SendMessage, never restart.
- **Owner free-text answers are quoted verbatim, never L0 summaries** (the #291 correction).
- **New prompt numbers must not collide:** planners guessed "31" and "33". Take the next number from the owner-decisions file.
- **Acceptance greps must target live cells, not quoted text** (QUEUE-E6-W1, LLAMA `chat_format=`).
- **Haiku and agent reports are leads.** Every PR was re-verified with one focused test run before merge.
- **`hold_slots.sh` must cover locks 1-8**; a 3-lock hold lets a `PYSLOTS>3` pytest through.
- **`gh pr edit` fails** (Projects classic GraphQL error): use `gh api -X PATCH repos/{owner}/{repo}/pulls/N`. gh 2.45 has no `pr checks --json`: read `statusCheckRollup`.
- Unchanged: never `ruff format`; three-dot diffs only; docs PRs merge one at a time (regenerate `docs/INDEX.md` after merging main); merge only after a review PASS; the owner merges RSI PRs with `--delete-branch=false` so WSL worktrees survive.

### Appendix: the four merge and slot scripts (recreate in `/tmp/claude-1000/`)

`merge_par.sh`:

```bash
#!/usr/bin/env bash
# Update all branches once, then merge each PR as soon as its checks are all green.
cd "/mnt/e/Programming/Github Repo/HealthCentral"
pending=("$@"); failed=()
for n in "${pending[@]}"; do gh pr update-branch "$n" >/dev/null 2>&1 && echo "#$n updated" || echo "#$n update skipped"; done
for i in $(seq 1 90); do
  sleep 40; left=()
  for n in "${pending[@]}"; do
    # gh 2.45 has no `pr checks --json`; read the rollup instead
    st=$(gh pr view "$n" --json statusCheckRollup --jq '[.statusCheckRollup[] | (.conclusion // .state // "")] | if length==0 then "WAIT" elif all(.=="SUCCESS" or .=="SKIPPED" or .=="NEUTRAL") then "OK" elif any(.=="FAILURE" or .=="CANCELLED" or .=="TIMED_OUT" or .=="ERROR") then "FAIL" else "WAIT" end' 2>/dev/null)
    m=$(gh pr view "$n" --json mergeable --jq .mergeable)
    if [ "$st" = OK ] && [ "$m" = MERGEABLE ]; then
      gh pr merge "$n" --merge >/dev/null 2>&1 && gh pr view "$n" --json mergeCommit --jq '"#'"$n"' MERGED \(.mergeCommit.oid[0:7])"' || { echo "#$n merge refused"; left+=("$n"); }
    elif [ "$st" = FAIL ]; then failed+=("$n"); echo "#$n FAILED: $(gh pr view "$n" --json statusCheckRollup --jq '[.statusCheckRollup[]|select((.conclusion // .state)!="SUCCESS")|"\(.name // .context)=\(.conclusion // .state)"]|join(",")')"
    elif [ "$m" = CONFLICTING ]; then echo "#$n CONFLICTING"
    else left+=("$n"); fi
  done
  pending=("${left[@]}"); [ ${#pending[@]} -eq 0 ] && { [ ${#failed[@]} -eq 0 ] && { echo "all done"; exit 0; }; echo "done; FAILED (not merged): ${failed[*]}"; exit 1; }
done
echo "timeout; still pending: ${pending[*]}"
```

`chain_merge.sh`:

```bash
#!/usr/bin/env bash
# Merge docs PRs one at a time, in order; stop at the first that fails.
for n in "$@"; do
  for try in 1 2 3; do
    out=$(bash /tmp/claude-1000/merge_par.sh "$n"); echo "$out"
    gh pr view "$n" --json state --jq .state | grep -q MERGED && break
    echo "$out" | grep -q FAILED && { echo "stop at #$n"; exit 1; }
  done
  gh pr view "$n" --json state --jq .state | grep -q MERGED || { echo "#$n not merged"; exit 1; }
done
echo "chain done"
```

`docs_chain.sh`:

```bash
#!/usr/bin/env bash
# Merge docs PRs in order; on an index conflict, merge main in the PR's worktree and regenerate the index.
R="/mnt/e/Programming/Github Repo/HealthCentral"
wt_for() { git -C "$R" worktree list --porcelain | awk -v b="refs/heads/$1" '/^worktree /{w=substr($0,10)} $0=="branch "b{print w}'; }
for n in "$@"; do
  for i in $(seq 1 240); do [ "$(gh pr view "$n" --json mergeable --jq .mergeable)" != UNKNOWN ] && break; sleep 15; done
  if [ "$(gh pr view "$n" --json mergeable --jq .mergeable)" = CONFLICTING ]; then
    br=$(gh pr view "$n" --json headRefName --jq .headRefName); W=$(wt_for "$br")
    [ -n "$W" ] || { echo "#$n conflicting, no worktree"; exit 1; }
    git -C "$W" fetch -q origin && git -C "$W" merge -q origin/main -m "Merge branch 'main' into $br" 2>/dev/null
    bad=$(git -C "$W" diff --name-only --diff-filter=U | grep -v -E '^docs/(INDEX\.md|_link_graph\.json)$')
    [ -z "$bad" ] || { echo "#$n real conflict: $bad"; git -C "$W" merge --abort; exit 1; }
    (cd "$W" && python3 scripts/generate_docs_index.py >/dev/null && python3 scripts/docs_lint.py --link-graph >/dev/null && python3 scripts/docs_lint.py | tail -1) || { echo "#$n lint failed"; exit 1; }
    git -C "$W" add docs/INDEX.md docs/_link_graph.json && git -C "$W" commit -q --no-edit && git -C "$W" push -q && echo "#$n index regenerated"
  fi
  bash /tmp/claude-1000/chain_merge.sh "$n" || exit 1
done
echo "docs chain done"
```

`hold_slots.sh` (usage: `bash hold_slots.sh <model command>`):

```bash
#!/usr/bin/env bash
# Hold every pyslot lock (slots 1..8, covers PYSLOTS up to 8) for a model run, so no pytest runs meanwhile.
L=/tmp/claude-1000/hc-pytest
cmd=("$@")
for i in 8 7 6 5 4 3 2 1; do cmd=(flock "$L.$i.lock" "${cmd[@]}"); done
exec "${cmd[@]}"
```

## 5. /goal prompt for the next L0

```
/goal Resume the Asclexis build program from docs/plans/2026-10-22-session-handoff.md (read it, CLAUDE.md, AGENT.md and the build-program RUNBOOK first; verify every claim with gh / git log). Setup: fast-forward main (or fresh clone), venv ~/venvs/asclexis-311 (uv-managed: uv pip install --python ~/venvs/asclexis-311/bin/python -r src/backend/requirements.txt), the embedding bundle in every worktree (cd src/backend && python scripts/download_models.py embedding), measure the collected count (expect about 2372 or more on afbe1af plus later merges) and `from main import app`, recreate merge_par.sh, chain_merge.sh, docs_chain.sh and hold_slots.sh in /tmp/claude-1000/ from the handoff §4 appendix, confirm a local model runs through ModelRunner (Ollama: llama3.1:8b or qwen3:8b; gemma4 fails the judge closed), and start the session with --plugin-dir .claude/mods/asclexis-rsi. Then, in priority order: (1) finish the merge chain: #284, #300, #295, #304, then #305, #306, #302 and #307 once each review loop has a PASS (check that the four build-item workflows and the #307 review actually finished; resume with build-item resume_pr after a dirty-worktree ruling if not), each after green CI and one focused test run; (2) post-merge batch: measure the collected count and update the slots in CLAUDE.md and AGENT.md, queue Last Updated and Totals, mark done rows, KV-PREFIX-MEASURE done, OLLAMA-NUM-CTX ready at 8192, and fix the CLAUDE.md embedding command to cd src/backend; (3) run build-wave and start every eligible row as its own top-level build-item workflow in one message (INTERP-SAFETY-ENFORCE after #304; OLLAMA-NUM-CTX after JUDGE-THINK; the #307 MVP rows once merged, MVP blockers first: SQLCIPHER per-OS gate SQLC-WHEEL-DIFF, session unlock, extract table/text forms, scanned-page warning plus RapidOCR, dev.ps1 first-run, FE import errors, re-auth 401); (4) model-host rows holding hold_slots.sh with no pytest running: DON-NER-MEASURE, JUDGE-LAYA-RESEARCH, AUDIT-DB-LOCKED Task 1 repro, QWEN3-4B tier after JUDGE-THINK; (5) ask the owner the new gates as inputs arrive (DON-NER-MODEL, WEAR-FIT-LIC, INTERP-ENFORCE-DIFF, JUDGE-SWAP, SQLC-WHEEL-DIFF, SESSION-AUTH-DIFF, DB-LOCK-FIX after the repro, CPU-MODEL-FINAL, VISIT-ASSIST-THINK, and the docs-agent questions: bulky record files, archiving the 6 remaining handoffs, DOC-OVERCLAIM-2) and remind the owner of their pending actions (write S5/OW-3, P6 orphan audit, Garmin export notes OW-W3, de-identified lab page EXF-SAMPLE, make RSI Replay a required check, demo-clone .env SHOW-O3 before 2026-10-31); (6) refresh the progress dashboard (Sonnet task); (7) run rsi-loop with the mod loaded, then archive this machine's RSI logs (.claude/logs/rsi/*.jsonl and .claude/logs/session-log.jsonl since 2026-10-21) to docs/agentic/rsi-runs/2026-10-22-gpubox/ per its README after a secret scan. Merge each non-owner PR yourself once it has a review PASS and all checks green; #230, #303 and other RSI PRs are owner-merged, #239 and #264 are never agent-merged. Rules as in CLAUDE.md: owner gates never inferred; owner free-text answers quoted verbatim; ask-first files (interpret_safety, redaction, faithfulness, verifier_agent, auth/encryption) need the owner's yes; never ruff format; three-dot diffs only; resume dead subagents with SendMessage, never restart; Haiku and agent reports are leads, re-verify with a focused test run; acceptance greps target live cells. Done when every non-owner-blocked row is merged or has a documented stop, the RSI archive has a 2026-10-22-gpubox folder, rsi-loop has run once with the mod loaded, and a new handoff replaces this one.
```
