# Session handoff: 2026-10-26 GPU-box L0 (RTX 3080) → next L0

**Last Updated:** 2026-10-26
**Owner:** repository owner
**Refresh Trigger:** the next L0 session reads this first, works §3, and replaces this file with its own handoff.

Read this after [CLAUDE.md](../../CLAUDE.md), [AGENT.md](../../AGENT.md) and the [build-program RUNBOOK](2026-10-15-build-program/RUNBOOK.md). It replaces [the 2026-10-25 handoff](2026-10-25-session-handoff.md). This session resumed the **GPU-box** L0 (RTX 3080, WSL, Ollama, `--plugin-dir .claude/mods/asclexis-rsi`, mod loaded) from that handoff's `/goal`, across 2026-10-25 and 2026-10-26. A `/clear` had killed the previous session's background agents and workflows. `resumeFromRunId` works only inside the session that started a run, so every item was restarted from its PR state. Main is at `64c758f` (#377). Treat this file as a lead: verify with `gh pr view` and `git log origin/main` before acting. The PR states and merge SHAs below were checked with `gh pr view N --json state,mergeCommit` on 2026-10-26.

## 1. What this session did

- **Merged** (L0 review, green CI, and an L0 focused check or a docs-chain merge, one docs PR at a time):
  - #372 `716384f`: post-merge batch 2026-10-25b, with the GATES-SAMPLE-TIME row and the UI-SHELL rulings.
  - #374 `e099a7c`: GATES-SAMPLE-TIME. `stillnessProbe` now stamps each sample at the start of `snapshot()`; new test HC-UIG-007. L0 ran HC-UIG-007: 2 passed.
  - #373 `0e8b2b2`: JUDGE-LAYA-RESEARCH. Laya, the NLI cross-encoder and today's think-off judge, measured. JUDGE-SWAP was drafted. The Opus review returned REVISE because the drafted question was selective; it was fixed, and L0 neutralised one line.
  - #377 `64c758f`: post-merge batch 2026-10-26.
    - Done: #373, #374.
    - Owner rows: UI-PHONE-TOGGLE, JUDGE-SWAP, SAFETY-LABEL-WORDING, WIN-TEST-BUNDLE, Q-E4.
    - New planned rows: JUDGE-LAYA-FT, JUDGE-NLI-TUNE, SETTINGS-DETECT-BLOCKING, POPOVER-OPEN-COST, GATES-SAMPLE-TIME-MINORS, ALERTDIALOG-CANCEL-FOCUS, NPM-AUDIT-PATCH.
    - New gates: JUDGE-SWAP-ADOPT, LAYA-CKPT-HOST.
    - New bullets: STILLNESS-GAP-BOUND, RSI-LOG-CMD.
    - The checks moved out of UI-SHELL are recorded on the page rows that receive them.
- **Owner answers** (L0 AskUserQuestion, 2026-10-26). Each decision below is recorded verbatim in [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md); the parallel-work direction is recorded only in the evidence comment. The full question and option texts are in L0 evidence comment 6419290199 on #377.
  - **UI-PHONE-TOGGLE:** "Second row on phones (Recommended)".
  - **JUDGE-SWAP:** free text, "Try both Layla fine tune and NLI judge". This became rows JUDGE-LAYA-FT and JUDGE-NLI-TUNE. Adoption comes back to the owner as JUDGE-SWAP-ADOPT. B-3 (#264) stays a draft.
  - **SAFETY-LABEL-WORDING:** "Keep plan default (Recommended)".
  - **WIN-TEST-BUNDLE:** "Bundle, one session (Recommended)".
  - **Q-E4:** "One row for the batch (Recommended)". This makes NPM-AUDIT-PATCH ready.
  - **Parallel work:** a multi-select direction, all four options chosen: "CI-CACHE + E-5 builds", "Plan unplanned follow-ups", "Run rsi-loop now", "Resume DON-NER now".
- **#370 UI-SHELL, L0 rulings 4 to 15** (PR comments starting `L0 ruling:`):
  - Ruling 3 replaced: the `/settings` gap was not branch-only (main measured 43-72 ms with a bare timer in the 03:57Z stop).
  - HC-UISH-008 waits for the More sheet to settle.
  - HC-UIFB-006 waits for `settleRoute` plus the inbox list. Its "toast stall" was the inbox's own data render, logged as INBOX-DATA-RENDER.
  - G6 is split per route, with four page-owned `test.fail` marks (PAGE-OVERFLOW): `/inbox`, `/medications/med-fixture-1`, `/explain`, `/export`.
  - Additive mockApi fixtures.
  - `/setup` is out of the shell checks.
  - `VerificationWorkbench.tsx` stacks below `lg` (two tokens, `79dec414`).
  - E2E-SET-001 belongs to SETTINGS-DETECT-BLOCKING. Main is at 10.2 s on a cold start; `detect_hardware` blocks the event loop three times.
  - The route fade already runs on WAAPI. HC-UISH-003 waits for a settled start page.
  - HC-UISH-009 `/settings` moves to UI-PG-SETTINGS (branch median 60 ms, main 49 ms).
  - HC-UIOV-007 moves to POPOVER-OPEN-COST as a `test.fixme`. The cost is under `ui/Popover.tsx`: Radix plus the React commit.
  - The phone toggle gets its own second row (owner UI-PHONE-TOGGLE), and search becomes an icon link to `/search` below `lg`.
  - `scroll-padding` goes on `html` in `globals.css`, so focus is not hidden by the shell chrome (WCAG 2.4.11).
  - No limit was relaxed and nothing was marked as flake.
- **rsi-loop** run `2026-10-26-gpubox` (`since` 2026-10-24T07:18Z, mod loaded): 2489 tool calls, 0 candidates. Claude and Codex both returned "nothing worth proposing".
  - Bash failure rate 2.61% → 1.98%, Edit 11.1% → 1.1%, Read 2.78% → 0%.
  - The loop is now limited by its data: the rsi-log has no command or stderr signature. See bullet RSI-LOG-CMD, which needs owner sign-off (privacy).
  - There is a log gap from 2026-10-24 08:15Z to 2026-10-26 02:55Z, because the previous session ran without the mod.
- **E-5, Linux half** (L0, origin/main `0e8b2b2`, `npm audit --package-lock-only`): 3 advisories.
  - vite high (7.3.6, GHSA-9jrq-w75r-8gcw and others), vitest and @vitest/mocker moderate.
  - `dev.ps1` runs the Vite dev server for patients, so the vite advisories apply to local runs.
  - The fix is NPM-AUDIT-PATCH (lockfile only).
- **Collected count:** 2534 on main. The #316 branch has 2535 (+1, HC-DEVSH-005). CLAUDE.md and AGENT.md read 2534. Update them in the batch after #316 merges.

## 2. Open PRs at handoff

| PR | Item | State | Next step |
|---|---|---|---|
| #370 | UI-SHELL | draft `[blocked:claude]` | **Blocked on a permission rule** (§4). Then post an `L0 ruling:` comment and run build-item `{id: "UI-SHELL", resume_pr: 370}` with the box quiet. **Done:** every code fix, including the phone second row (`72763a2c`) and focus scroll-padding. **Left:** T4 stillness on dev and preview (HC-UISH-009, HC-UIFB-006, HC-UIG-006), T5 PR-body lists (PAGE-H1, PAGE-A11Y, PAGE-OVERFLOW, E2E-SET-001 figures, every moved check with its target row), T6 acceptance, CI E2E on the final head. |
| #376 | CI-CACHE | draft; review PASS; 9/9 green | **Owner merges** (CI file). The auto-mode classifier refused the L0 merge ("Merge Without Review"). Warm CI run: 1090 s → 567 s. |
| #375 | DON-NER-MEASURE | open; Opus review REVISE, then fixed in `828e622`; L0 round-2 review PASS (comment 6434440876) | Docs-chain merge was in progress at write time; check `gh pr view 375`. After it merges, ask **DON-NER-MODEL** verbatim from `docs/reviews/2026-10-26/don-ner-measure.md` ("Input for owner gate DON-NER-MODEL"), with `[model]` = `obi/deid_roberta_i2b2`. No candidate meets DON-RECALL; #239 stays a draft. |
| #316 | DEV-PS1-FIRSTRUN + LLAMA-WHEEL-INDEX + DEV-EMB-FETCH | draft; suite green (2534 passed, 1 xfailed, 2535 collected) | **The owner's one Windows session** (WIN-TEST-BUNDLE): DPF-1..3, LWI-1, DEF-1, and E-5's `cd src/frontend && npm ci && npm audit`. The PR body's checklist covers DPF-1..3, LWI-1 and DEF-1 only; give the owner the E-5 step separately (the E-5 queue row assigns it to this session). Plan corrections: DPF-2 reads `logs\dev-backend.err.log`; DEF-1's path is `models\embeddings\`. L0 licensed `src/backend/tests/test_dev_sh_prereqs.py` (the stub fails only the binary-only wheel call). Record that on the LLAMA-WHEEL-INDEX row. |
| #317 | RAG-TIMEOUT-ANSWER | draft `[blocked:claude]` | Unchanged; needs a plan delta (grounded path; follow-up bullet RAG-TIMEOUT-GROUNDED). |
| #264 | B-3 advice judge | draft | **Never agent-merged.** Now also waits on JUDGE-LAYA-FT, JUDGE-NLI-TUNE and JUDGE-SWAP-ADOPT. |
| #239 | RSI1-DONATE PR-2 | draft `[blocked:claude]` | **Never agent-merged.** Waits on DON-NER-MODEL. |

## 3. Next

1. **Unblock and finish #370 UI-SHELL** (§2). Then a post-merge batch: UI-SHELL done; the LLAMA-WHEEL-INDEX test-file licence; the count line once #316 merges. **21 UI rows wait on UI-SHELL** (13 directly).
2. **#376 is left for the owner to merge** (CI file; the classifier refused the L0 merge). Do not merge it under the /goal's merge rule unless the owner says so.
3. **Ask DON-NER-MODEL** once #375 merges, and record the answer verbatim.
4. **The owner's Windows session for #316** (and the E-5 Windows half). Merge #316 after the checks pass.
5. **The next UI wave once #370 merges:** run build-wave for UI-PALETTE, the UI-PG-* rows whose deps have landed (each inherits the moved checks on its row), SAFETY-MODE-TOGGLE, and SESSION-REENTRY Task 3. ALERTDIALOG-CANCEL-FOCUS goes before UI-PG-SECURITY.
6. **NPM-AUDIT-PATCH** (ready; lockfile only; never beside another `package.json` or lockfile PR).
7. **Model-host rows, one at a time,** with `hold_slots.sh` and no pytest beside them: QWEN3-4B-TIER, AUDIT-DB-LOCKED Task 1, JUDGE-LAYA-FT, JUDGE-NLI-TUNE. KV-NUMCTX-VERIFY is not a queue row yet: it is an unplanned bullet (queue.md, "found 2026-10-23, #318 PR body"), so it needs a planner row before it can run. Never during a UI-SHELL stillness run (§4, quiet box).
8. **Archive the rsi-loop run** `2026-10-26-gpubox` per [`docs/agentic/rsi-runs/README.md`](../agentic/rsi-runs/README.md) (windowed copy). The run wrote no `.claude/logs/rsi/summary-*.json`, because it stopped at "nothing worth proposing". Write the archive's `summary.json` from the §1 figures, marked as reconstructed from this handoff: the full workflow result is in the L0 session's journal for run `wf_9e11b537-2db`, which a later session cannot read.
9. **Owner actions** (remind; do not do them):
   - RSI-REPLAY-REQUIRED: GitHub → Settings → Branches → `main` → add **RSI Replay**. Verify with `gh api repos/{owner}/{repo}/branches/main/protection/required_status_checks --jq .contexts`.
   - SHOW-O3 before **2026-10-31**.
   - EXF-SAMPLE.
   - OW-3 (S5).
   - OW-W0 and OW-W3 (F-12).
   - The P6 orphan audit.
10. **Decide the PROPOSED-status plans** (carried from 2026-10-25 §3 item 5), refresh the [progress dashboard](https://claude.ai/artifact/61W8zR9zbR3QbGtwREWrgf) from queue.md, and write the next handoff replacing this one.

**Progress at handoff** (queue.md on main `64c758f`; method: every queue table row whose first cell is a row ID, each ID counted once, "done" = status starting with done, closed, superseded, dropped, withdrawn or won't): 165 of 226 rows done (73%). By lane: D 20/21 (95%), A 49/54 (91%), B 29/36 (81%), E 32/47 (68%), F 12/18 (67%), C 5/8 (62%), UI 18/42 (43%). Other methods give other totals (the #378 fact-check counted 166 of 233 including the owner and model-machine table), so state the method when you refresh it (§3 item 10).

## 4. Harness gotchas

- **The auto-mode classifier refuses GitHub writes intermittently.** It refused the build-item claim retitle (`gh api -X PATCH .../pulls/370`) twice, PR comments once, and an L0 `gh pr merge` once ("Merge Without Review").
  - The owner chose to add an allow rule. At handoff it was not yet confirmed as added.
  - The rules to add (`.claude/settings.local.json` `permissions.allow`, or `/permissions`): `Bash(gh api -X PATCH repos/BrooklynD23/HealthCentral/pulls/:*)`, `Bash(gh pr comment:*)`, and, if the owner wants L0 merges, `Bash(gh pr merge:*)` and `Bash(gh pr ready:*)`.
  - Never work around a refusal.
- **Quiet-box protocol for UI-SHELL timing runs.**
  - L0 creates `/tmp/claude-1000/quiet-box.lock`. Model and measurement agents are briefed to wait while it exists, and also while `pgrep -f "playwright|vitest"` matches.
  - L0 removed the lock at handoff, since nothing was running. Hold it again before resuming #370.
  - A `pgrep -f measure_ner` wait loop also matches the agents' own idle shells (their command lines contain the name). Check the load instead.
- **The stillness 40 ms gap bound is about one React commit** on this box and in CI. Main exceeds it on `/settings` with no long task, so check main with a bare timer before ruling. Bullet STILLNESS-GAP-BOUND is a possible owner question, not asked. Never relax the bound.
- **Local Playwright** needs `HC_E2E_BACKEND_PYTHON=$HOME/venvs/asclexis-311/bin/python`.
- **GPU torch** exists only in `~/hc-mm4/src/backend/.venv-linux` (Python 3.12). The repo venv's torch is CPU-only. Agents may use it read-only for GPU latency, and must disclose it.
- **Have one reviewer read every drafted owner question.** Reviews caught selective reporting twice this session (JUDGE-SWAP in #373, DON-NER-MODEL in #375), both slanted toward one option. Each was fixed before anything was asked.
- **Grep the open owner questions before ruling.** L0 once settled an open owner question (Q-E4) inside a planner brief. The #377 review caught it, and L0 then asked the owner.
- **build-item refuses rows typed OWNER** (RUNBOOK §9 rule 8), for example E-5, even when the runtime cell says "any". L0 does those itself.
- **Carried, unchanged:**
  - Never Sonnet 5.5 (Haiku 5.5 xhigh implements).
  - Launch workflows from scratchpad copies (`git show origin/main:.claude/workflows/<f>.js > <scratchpad>/<f>.js`, then `Workflow({scriptPath})`).
  - A resume needs a comment starting with the literal `L0 ruling:`, posted after the `## blocked: tell L0` comment.
  - `gh pr edit` fails; use `gh api -X PATCH`.
  - `/mnt/e` is slow under load: a docs commit took over 2 minutes.
  - Never `ruff format`; three-dot diffs only; docs PRs merge one at a time.
  - `/tmp/claude-1000` can be wiped by a restart. The scripts are below.
  - `/tmp/claude-1000/windows-checklist-316.md` is in `/tmp` too; its content is also in #316's body.

### Appendix: the five merge, slot and wait scripts (recreate in `/tmp/claude-1000/`)

There is no `gatemerge_par.sh`; the parallel merge waiter is **`merge_par.sh`**.

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
    elif [ "$m" = CONFLICTING ]; then failed+=("$n"); echo "#$n CONFLICTING"
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
    git -C "$W" rev-parse -q --verify MERGE_HEAD >/dev/null || { echo "#$n merge did not start (dirty worktree?)"; exit 1; }
    bad=$(git -C "$W" diff --name-only --diff-filter=U | grep -v -E '^docs/(INDEX\.md|_link_graph\.json)$')
    [ -z "$bad" ] || { echo "#$n real conflict: $bad"; git -C "$W" merge --abort; exit 1; }
    (cd "$W" && python3 scripts/generate_docs_index.py >/dev/null && python3 scripts/docs_lint.py --link-graph >/dev/null && python3 scripts/docs_lint.py >/dev/null) || { echo "#$n lint failed"; exit 1; }
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

**`wait_checks.sh`** (added 2026-10-25, the wait helper used in the 2026-10-25 session): waits until each PR's checks complete, prints OK or FAIL plus mergeable for each, and never merges. It uses the same `statusCheckRollup` jq as `merge_par.sh`, polls every 40 s, and gives up after 60 tries. The body was as used by L0 this session; same jq as `merge_par.sh` and the session's description, not copied from the session's file, so run it once on a known PR before relying on it.

```bash
#!/usr/bin/env bash
# Wait until each PR's checks are all complete; print status. Does not merge.
cd "/mnt/e/Programming/Github Repo/HealthCentral"
for i in $(seq 1 60); do
  done_all=1; out=""
  for n in "$@"; do
    st=$(gh pr view "$n" --json statusCheckRollup --jq '[.statusCheckRollup[] | (.conclusion // .state // "")] | if length==0 then "WAIT" elif all(.=="SUCCESS" or .=="SKIPPED" or .=="NEUTRAL") then "OK" elif any(.=="FAILURE" or .=="CANCELLED" or .=="TIMED_OUT" or .=="ERROR") then "FAIL" else "WAIT" end')
    m=$(gh pr view "$n" --json mergeable --jq .mergeable)
    out="$out #$n=$st/$m"; [ "$st" = WAIT ] && done_all=0
  done
  [ $done_all = 1 ] && { echo "$out"; exit 0; }
  sleep 40
done
echo "timeout:$out"
```

## 5. /goal prompt for the next L0

```
/goal Resume the Asclexis build program in /mnt/e/Programming/Github Repo/HealthCentral from docs/plans/2026-10-26-session-handoff.md. Read it first, then CLAUDE.md, AGENT.md and docs/plans/2026-10-15-build-program/RUNBOOK.md, and verify every claim with gh and git log origin/main before acting. Never edit the main checkout (it has CRLF working files); work in a worktree.
Setup: git fetch origin; venv ~/venvs/asclexis-311; embedding bundle in each worktree (cd src/backend && python scripts/download_models.py embedding); measure the collected count through scripts/pyslot.sh (expect 2534 on main, or 2535 once #316 merges); recreate merge_par.sh, chain_merge.sh, docs_chain.sh, hold_slots.sh and wait_checks.sh in /tmp/claude-1000/ from handoff §4; confirm a local model runs through ModelRunner (Ollama: llama3.1:8b or qwen3:8b); start the session with --plugin-dir .claude/mods/asclexis-rsi. Check that the owner's GitHub-write allow rule from handoff §4 is in place before resuming any build item.
Model rule: never Sonnet 5.5. Haiku 5.5 at effort xhigh implements; Opus 5.5 reviews (including every drafted owner question); Haiku 5.5 does exploration and test runs. Launch workflow copies from the session scratchpad.
Priority order: handoff §3 items 1 to 10, in order. Owner direction, verbatim: "Merge everything that is ready, including RSI." and "keep going, merge them as they pass". #239 and #264 are never agent-merged, and #376 is left for the owner. Every other PR you merge yourself once review passes, checks are green and a focused test run passes, with gh pr merge N --merge --delete-branch=false; if the permission check refuses a merge, leave it for the owner and say so.
Rules: hold /tmp/claude-1000/quiet-box.lock during UI-SHELL stillness runs and keep model-host rows off the box meanwhile; a resume needs an "L0 ruling:" comment; owner answers are quoted verbatim from docs/capstone-report/owner-decisions-2026-09-27.md; grep open owner questions before ruling; ask the owner first for interpret_safety, redaction, faithfulness, verifier_agent and anything auth or encryption; three-dot diffs only; never ruff format; docs PRs merge one at a time.
Done when #370 is merged and the next UI wave is merged or in flight, DON-NER-MODEL is asked, #316 is merged or waiting only on the owner, the model-host rows are run or documented, the rsi-loop run is archived, and a new handoff replaces docs/plans/2026-10-26-session-handoff.md.
```
