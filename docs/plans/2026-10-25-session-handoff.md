# Session handoff: 2026-10-25 GPU-box L0 (RTX 3080) → next L0

**Last Updated:** 2026-10-25
**Owner:** repository owner
**Refresh Trigger:** the next L0 session reads this first, works §3, and replaces this file with its own handoff.

Read this after [CLAUDE.md](../../CLAUDE.md), [AGENT.md](../../AGENT.md) and the [build-program RUNBOOK](2026-10-15-build-program/RUNBOOK.md). It replaces [the 2026-10-24 handoff](2026-10-24-session-handoff.md). This session continued the **GPU-box** L0 (RTX 3080, WSL, Ollama, llama.cpp tiers, `--plugin-dir .claude/mods/asclexis-rsi`) across 2026-10-24 and 2026-10-25, following the 2026-10-24 handoff's `/goal`. It left main at `d0708cb` (#368). Treat this file as a lead: verify with `gh pr view` / `git log origin/main` before acting. PR states and merge SHAs below were checked with `gh pr view N --json state,mergeCommit` on origin/main `d0708cb` (2026-10-25). Open-PR mergeability changes, so re-read it before any merge.

## 1. What this session did

- **Merged 27 PRs.** Each passed L0 review, had green CI and an L0 focused test run; docs went through the docs chain one at a time. Grouped by area, with merge SHAs on main:
  - **RSI and routing:** #230 `5f6cda6` (RSI hint, embedding bundle missing); #341 `2a440dc` (RSI hint, "No such file or directory"; L0 resolved its conflict with #230); #340 `29dca22` (Sonnet to Haiku 5.5 xhigh routing).
  - **Docs:** #345 `0a59639` (2026-10-24 handoff fact-check); #346 `d12180c` (SAFETY-MODE build rows planned, A11Y-CRIT-LABELS row added); #352 `0fe6a59` (post-merge batch, count 2472); #354 `86d0e01` (SAFETY-MODE-STRICT may build beside parked #264); #360 `94deaaa` (post-merge batch, count 2534); #366 `012439f` (README reorganised: setup to `docs/dev/setup.md`, overview to `docs/architecture/overview.md`, four handoffs archived); #369 `41b9ba8` (post-merge batch 2026-10-25).
  - **Extract and import:** #347 `baf9faf` (IMPORT-SCANNED-PAGE); #353 `b9e5ab0` (EXTRACT-TEXT-FORMS); #358 `01f8c23` (EXTRACT-DOB-FORMS).
  - **Safety Mode:** #349 `d775215` (SAFETY-MODE-SETTING); #355 `feb7b5a` (SAFETY-MODE-STRICT); #359 `c4a183c` (SAFETY-MODE-VERIFIED).
  - **UI:** #348 `4ffdd9a` (A11Y-CRIT-LABELS); #350 `57a7f41` (UI-GATES); #351 `525cab8` (UI-MOTION); #356 `335e5f9` (UI-TOKENS); #357 `d33b333` (UI-ROUTES); #361 `e3f9a38` (UI-BUDGET); #362 `3ebd2fb` (UI-RIBBON); #363 `aa7e5a1` (UI-PRIM-OVERLAYS); #364 `a7a2a20` (UI-PRIM-FEEDBACK); #365 `ff41143` (UI-PRIM-CONTROLS); #368 `d0708cb` (UI-SHOWCASE-KIT).
- **Model routing:** #340 is merged. Never Sonnet 5.5; Haiku 5.5 at effort xhigh replaces every former Sonnet role. `origin/main` has no Sonnet reference under `.claude/workflows/`, so the workflows now default to Haiku 5.5 xhigh.
- **Owner direction, verbatim:** "Merge everything that is ready, including RSI." and "keep going, merge them as they pass". Under it L0 merged the owner-merge PRs #230, #341 and #340 itself, and the owner-merge row UI-BUDGET (#361, the CI file). After #361, L0 ran `npm run build:check` on origin/main `e3f9a38`: every bundle budget PASS. Main JS measured 103.81 kB gz against the 165 kB budget in `src/frontend/scripts/check-bundle.mjs`. Before UI-BUDGET it was 181.05 kB gz, over the 180 kB budget the 2026-10-24 handoff recorded (recurring-failures #12: judge a gate on the merged main).
- **Collected backend count:** 2462 at the start, **2534** now. L0 measured 2534 on `01f8c23`; CLAUDE.md and AGENT.md both read 2534 after #360. Frontend-only merges since then add no backend tests.
- **Safety Mode** (owner prompt 51: "Stricter checks", "Always-on citations view", "Verified-only data"). Plan: [`docs/plans/2026-10-24-safety-mode-build-plan.md`](2026-10-24-safety-mode-build-plan.md). Backend rows SETTING, STRICT and VERIFIED are done (#349, #355, #359). It is one per-profile switch: OFF is today's behaviour, ON only adds stricter checks. No ask-first file was edited. Frontend rows SAFETY-MODE-TOGGLE (after UI-SHELL), SAFETY-MODE-CITATIONS and SAFETY-MODE-VERIFIED-FE wait on UI rows.
- **Progress dashboard** (private artifact): https://claude.ai/artifact/61W8zR9zbR3QbGtwREWrgf. Version 2 at main `41b9ba8`: 169 of 225 rows done. Republish from the same source when refreshing; the HTML is regenerated from queue.md.
- **Interruptions, all resumed:** a session restart wiped `/tmp/claude-1000` (scripts recreated from §4; workflows resumed with `resumeFromRunId`); a login expiry (resumed after `/login`); an auto-mode classifier outage (resumed).
- **Earlier interim session** (Cursor, 2026-10-24, while Claude Code was rate-limited) merged #333 `4c5e619`, #329 `a48cdbc`, #338 `8103e4f`, #343 `ae47612`, #342 `79dff7c` and #344 `f3c1106` (the 2026-10-24 handoff itself).

### L0 rulings this session

Every ruling is a PR comment that starts with `L0 ruling:`. One line each:

- **#347 IMPORT-SCANNED-PAGE:** a `types.ts` swap.
- **#349 SAFETY-MODE-SETTING:** head literals and audit-guard rows; audit details reuse the existing `changed_fields` and `status` keys, so `core/audit.py` is not edited.
- **#351 UI-MOTION:** keep `PageTransition` and `modalVariants`; HC-UIMO-002 tests `PageTransition`.
- **#355 SAFETY-MODE-STRICT:** the status route is audited and has a guard row; six mock-DB tests pin strict mode OFF, and the production helper stays fail-closed.
- **#359 SAFETY-MODE-VERIFIED:** the STRICT fixture is marked verified.
- **#356 UI-TOKENS:** the five TopBar ON-badge `KNOWN_A11Y` entries (`.px-1\.5`) are reassigned to fixBy UI-SHELL; one-token fixes in `ExplainAssistant.tsx` and `SettingsPage.tsx`; HC-UITK-006 stays active (an earlier fixme ruling was withdrawn after CLS measured 0).
- **#357 UI-ROUTES:** a pre-existing double-mount bug is fixed with `FrozenOutlet` in `AppLayout.tsx`.
- **#363, #364, #365 UI-PRIM-\*:** the browser stillness halves move to UI-SHELL; the Badge variant and the Motion barrel are kept.
- **#362 UI-RIBBON:** labels say "this chart's range" (TrendPoint has no per-point range); a transform-fill class is used instead of relaxing HC-UITK-002; the browser gates move to UI-PG-RESULTS.
- **#368 UI-SHOWCASE-KIT:** EmptyState's action is optional; the entrance uses a per-surface session key; the thinking-orbs real-build check moves to UI-PG-DOCUMENTS.
- **#367 UI-PROVENANCE** (open): the browser halves move to the page rows and UI-SHELL; no page is invented for KB citations.
- **#370 UI-SHELL** (open): the shell asserts no h1 of its own (PAGE-H1 goes to the page rows or UI-MICRO); the HC-UISH-006 regex is case-sensitive; `/explain` HC-UISH-009 moves to UI-PG-ASK; inherited HC-UIOV-007 must pass CI; out-of-row gate failures are recorded; mockApi fixtures are additive only.

**Pattern:** the e2e and browser halves of a component row move to the first row that mounts the component. An out-of-row gate failure is recorded, never waived. `KNOWN_A11Y` stays shrink-only.

## 2. Open PRs at handoff

States checked 2026-10-25 with `gh pr view` on origin/main `d0708cb`.

| PR | Item | State at write time | Next step |
|---|---|---|---|
| #370 | UI-SHELL responsive-shell | open draft, `[claim:claude]`; mergeable | **In flight.** The build item resumed after the L0 ruling in §1. Review, focused test, merge. |
| #367 | UI-PROVENANCE source-trace | open draft, `[claim:claude]`; mergeable | **In flight.** Resumed after the Gate G ruling; follow-up GATES-POPPER-TRANSFORM. Review, focused test, merge. |
| #317 | RAG-TIMEOUT-ANSWER abstain-on-timeout | draft `[blocked:claude]` | Blocked pending a plan delta (grounded path). |
| #316 | DEV-PS1-FIRSTRUN | draft | Waits on owner Windows **DPF-1..3**. |
| #264 | B-3 advice judge | draft; mergeable UNKNOWN at write time (CONFLICTING on 2026-10-24) | Draft until B-4; **never agent-merged**. |
| #239 | RSI1-DONATE PR-2 | draft `[blocked:claude]` | Parked; **never agent-merged**. |

No owner-merge PR is open: #230, #341 and #340 are merged.

**How the next L0 checks the two in-flight items:** `gh pr view 370` / `gh pr view 367`. If the workflow is gone and the PR is `[claim:claude]` with a stale worktree, retitle it to `[blocked:claude]` with `gh api -X PATCH repos/{owner}/{repo}/pulls/N -f title=...`, post a "## blocked: tell L0" comment, then an "L0 ruling:" comment, then run build-item with `resume_pr` (the resume gate requires that).

## 3. Next

1. **Finish #370 UI-SHELL and #367 UI-PROVENANCE** (review, focused test, merge). Then run a post-merge batch: mark both done; record on the UI-PG-DOCUMENTS row the thinking-orbs real-build PASS check (the #368 ruling); add PAGE-H1 and GATES-POPPER-TRANSFORM bullets; update CLAUDE.md's "Twelve failure modes" wording to thirteen (recurring-failures.md gained entry 13 in #369).
2. **build-wave for the next UI wave:** UI-PALETTE (after UI-SHELL and UI-BUDGET), UI-PG-* page rows as their deps land, SAFETY-MODE-TOGGLE after UI-SHELL. Each page row inherits the moved checks recorded in its queue row.
3. **Model-host rows on the GPU box**, with `hold_slots.sh` and **no pytest running** (not done this session; build items kept pytest busy): JUDGE-LAYA-RESEARCH, DON-NER-MEASURE, QWEN3-4B-TIER, AUDIT-DB-LOCKED Task 1, KV-NUMCTX-VERIFY.
4. **rsi-loop with the mod loaded** (not run this session; logs since the last run, 2026-10-24 ~00:26 PT, are in `.claude/logs/rsi/`), then archive per [`docs/agentic/rsi-runs/README.md`](../agentic/rsi-runs/README.md) (windowed copy).
5. **Decide the PROPOSED-status plans** whose rows are done: W02, legacy-cite-prompt, mvp-rows, frontend-revamp, safety-mode-build, AUDIT-ORDER. The README agent left their status lines alone.
6. **Follow-ups** logged in the `New rows (not yet planned)` sections of [queue.md](2026-10-15-build-program/queue.md): ALERTDIALOG-CANCEL-FOCUS (blocks destructive-flow consumers such as DangerZone and UI-PG-SECURITY), TREND-POINT-RANGE, VITEST-TZ-PIN, BUTTON-DARK-CONTRAST, MOTION-BARREL, PROGRESS-CLIPPATH, UI-GATES-TIMING-FLAKE, SAFETY-STRICT-CHAT-AUDIT, SAFETY-VERIFIED-MINORS, SAFETY-MODE-DUPROW, EXTRACT-DOB-MINORS, SHOWCASE-PROVENANCE-MOVES.
7. **Owner actions pending** (remind, do not do): S5 (OW-3); P6 orphan audit; Garmin export notes (OW-W3); EXF-SAMPLE; RSI Replay required check; SHOW-O3 demo-clone `.env` before 2026-10-31; Windows DPF-1..3 for #316.
8. **Refresh the progress dashboard** after merges; write the next handoff replacing this one.

### Known gaps

Carried from the 2026-10-24 handoff and not re-checked this session:

- **#333 and #329 PR bodies** lack the RUNBOOK §6 table sections (Item, Runtimes, Gates used, Skipped tasks, Contracts, Count and Review are missing from one or both). The fix is a post-merge comment with those sections; the next L0 or the owner decides.

## 4. Harness gotchas

- **Never Sonnet 5.5** (owner 2026-10-24). Every former Sonnet role runs as Haiku 5.5 at effort xhigh; #340 is merged, so the workflows on main already do this. Launch from scratchpad copies anyway: `git show origin/main:.claude/workflows/<f>.js > <session scratchpad>/<f>.js`, then `Workflow({scriptPath})`. The Workflow tool refuses `/tmp/claude-1000/...` paths.
- **L0 ruling:** a dirty-worktree resume needs a comment that starts with the literal prefix `L0 ruling:` (not a markdown heading). Retitle a ready PR to `[blocked:claude]` before resuming it.
- **Owner gates** are never inferred. Ask-first files (`interpret_safety`, `redaction`, `faithfulness`, `verifier_agent`, auth and encryption) need the owner's yes.
- **Haiku and agent reports are leads.** Re-verify with a focused test run before merge.
- **`hold_slots.sh` must cover locks 1–8** so no `PYSLOTS>3` pytest runs during model-host work.
- **`gh pr edit` fails** (Projects classic GraphQL error; not re-tested this session): use `gh api -X PATCH repos/{owner}/{repo}/pulls/N`. The scripts read `statusCheckRollup`, not `pr checks --json`, because they were written for gh 2.45; this box has gh 2.95.0.
- **Agents sometimes return while a background RED or mutation run is still editing the worktree** (recurring-failures entry 13). Before resuming, check `git status`, compare against the run's snapshot, and restore only what differs. Brief agents to run long commands in the foreground.
- **A stop that fails to retitle leaves a live-looking `[claim:claude]` PR.** Retitle it yourself before `resume_pr`.
- **`/mnt/e` is slow:** `npm ci` and vitest stall, and agents can return before installs finish. Confirm `node_modules/.package-lock.json` exists and no npm process is running before resuming.
- **`Gamification.test.tsx:202`** fails on this Pacific-time box only (VITEST-TZ-PIN); CI passes it.
- **Timing gates** (HC-UIG-\*, HC-UIOV-007) flake under CPU load. Judge them in CI or with the box quiet; never relax the limits.
- **Legacy RAG Eval Gate** can fail on an apt 403 from packages.microsoft.com (infra). Rerun with `gh run rerun <id> --failed`.
- **`/tmp/claude-1000` can be wiped by a restart.** Recreate the scripts from the appendix below.
- **Wait helper:** `wait_checks.sh` (in the appendix) waits for checks and prints OK or FAIL plus mergeable, without merging.
- **Unchanged:** never `ruff format`; three-dot diffs only; docs PRs merge one at a time (`docs_chain.sh`); merge only after review PASS. RSI PRs merge under the owner's direction above, with `--delete-branch=false` so WSL worktrees survive.

### Appendix: the four merge and slot scripts (recreate in `/tmp/claude-1000/`)

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

**`wait_checks.sh`** (added 2026-10-25, the wait helper used this session): waits until each PR's checks complete, prints OK or FAIL plus mergeable for each, and never merges. It uses the same `statusCheckRollup` jq as `merge_par.sh`, polls every 40 s, and gives up after 60 tries. The body was reconstructed from `merge_par.sh` and the session's description, not copied from the session's file, so run it once on a known PR before relying on it.

```bash
#!/usr/bin/env bash
# Wait until each PR's checks complete; print OK or FAIL plus mergeable. Never merges.
cd "/mnt/e/Programming/Github Repo/HealthCentral"
pending=("$@")
for i in $(seq 1 60); do
  left=()
  for n in "${pending[@]}"; do
    st=$(gh pr view "$n" --json statusCheckRollup --jq '[.statusCheckRollup[] | (.conclusion // .state // "")] | if length==0 then "WAIT" elif all(.=="SUCCESS" or .=="SKIPPED" or .=="NEUTRAL") then "OK" elif any(.=="FAILURE" or .=="CANCELLED" or .=="TIMED_OUT" or .=="ERROR") then "FAIL" else "WAIT" end' 2>/dev/null)
    if [ "$st" = OK ] || [ "$st" = FAIL ]; then
      echo "#$n $st mergeable=$(gh pr view "$n" --json mergeable --jq .mergeable)"
    else
      left+=("$n")
    fi
  done
  pending=("${left[@]}"); [ ${#pending[@]} -eq 0 ] && { echo "all checks complete"; exit 0; }
  sleep 40
done
echo "timeout; still waiting: ${pending[*]}"
exit 1
```

## 5. /goal prompt for the next L0

```
/goal Resume the Asclexis build program in /mnt/e/Programming/Github Repo/HealthCentral from docs/plans/2026-10-25-session-handoff.md. Read it first, then CLAUDE.md, AGENT.md and docs/plans/2026-10-15-build-program/RUNBOOK.md, and verify every claim with gh and git log origin/main before acting. Never edit the main checkout (it has CRLF working files); work in a worktree.
Setup: git fetch origin; venv ~/venvs/asclexis-311 (uv pip install --python ~/venvs/asclexis-311/bin/python -r src/backend/requirements.txt); embedding bundle in each worktree (cd src/backend && python scripts/download_models.py embedding); measure the collected count through scripts/pyslot.sh (expect 2534, the value in CLAUDE.md and AGENT.md); recreate merge_par.sh, chain_merge.sh, docs_chain.sh, hold_slots.sh and wait_checks.sh in /tmp/claude-1000/ from handoff §4 (merge_par.sh, not gatemerge_par.sh); confirm a local model runs through ModelRunner (Ollama: llama3.1:8b or qwen3:8b); start the session with --plugin-dir .claude/mods/asclexis-rsi.
Model rule: never Sonnet 5.5. Haiku 5.5 at effort xhigh implements; Opus 5.5 reviews; Haiku 5.5 does exploration and test runs. Launch workflow copies from the session scratchpad: git show origin/main:.claude/workflows/<f>.js > <session scratchpad>/<f>.js, then Workflow({scriptPath}).
Priority order: handoff §3 items 1 to 8, in order. Owner direction, verbatim: "Merge everything that is ready, including RSI." and "keep going, merge them as they pass". #239 and #264 are never agent-merged. Every other PR you merge yourself once review passes, checks are green and a focused test run passes, with gh pr merge N --merge --delete-branch=false.
Rules: a dirty-worktree resume needs an L0 ruling whose comment starts with the literal prefix "L0 ruling:"; retitle a ready PR to [blocked:claude] before resuming it (gh api -X PATCH if gh pr edit fails); owner answers are quoted verbatim from docs/capstone-report/owner-decisions-2026-09-27.md, never summarised; ask the owner first for interpret_safety, redaction, faithfulness, verifier_agent and anything auth or encryption; review three-dot diffs only; never run ruff format; docs PRs merge one at a time.
Done when the open PRs are merged or documented, the next UI wave (UI-PALETTE and the UI-PG-* rows whose deps have landed) is merged or in flight, the model-host rows are run or documented, rsi-loop has run with the mod loaded, and a new handoff replaces docs/plans/2026-10-25-session-handoff.md.
```
