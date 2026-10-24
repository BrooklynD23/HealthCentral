# Session handoff: 2026-10-24 GPU-box L0 (RTX 3080) → next L0

**Last Updated:** 2026-10-24
**Owner:** repository owner
**Refresh Trigger:** the next L0 session reads this first, works §3, and replaces this file with its own handoff.

Read this after [CLAUDE.md](../../CLAUDE.md), [AGENT.md](../../AGENT.md) and the [build-program RUNBOOK](2026-10-15-build-program/RUNBOOK.md). It replaces [the 2026-10-22 handoff](2026-10-22-session-handoff.md). This session continued the **GPU-box** L0 (RTX 3080, WSL, Ollama, llama.cpp tiers, `--plugin-dir .claude/mods/asclexis-rsi`), from 2026-10-22 evening through 2026-10-24, picking up where the 2026-10-22 handoff left main at `afbe1af`. Treat this file as a lead: verify with `gh pr view` / `git log origin/main` before acting. PR states below were checked at write time (main `b3c6228`, 2026-10-24 ~01:25 PT) and updated by the interim L0 at ~01:55 PT after #333, #329 and #338 merged (main `8103e4f`).

**Interim session (Cursor, 2026-10-24 ~01:20-02:00 PT, while Claude Code was rate-limited).** Haiku 5.5 was not available there, so Composer 2.5 implemented and Opus 5.5 (L0) reviewed and merged. It merged #333 E2E-UIFULL-CI (`4c5e619`), #329 AXE-E2E (`a48cdbc`) and #338 SAFETY-MODE-REAL (`8103e4f`), asked the owner SAFETY-MODE-BEHAVIOUR (prompt 51), and opened the post-merge batch #343, this handoff #344 and the RSI archive merge #342 through the docs chain.

## 1. What this session did

- **Finished the 2026-10-22 merge chain** (non-RSI, review PASS and green CI): #284, #300, #295, #304, #305, #306, #302, #307, #308 (2026-10-22 handoff), #309 (CI e2e ubuntu-24.04), #310 (post-merge batch 2026-10-23), #311 (frontend revamp plan), and the MVP / wave-1 code PRs through #323. **Owner merged** #303 RSI-CODEX-PROPOSER at `b7288bd` during wave 3 (the wave notes had still listed it open; that line was stale).
- **Three build-waves** on main (see `/tmp/claude-1000/wave-2026-10-23.txt` for workflow ids): wave 1 from `15fe095` (SESSION-REENTRY Task 1, MVP-REAUTH-401, OLLAMA-NUM-CTX, FE rows, RAPIDOCR-RESEARCH, and related); wave 2 from `45640d5` (NORMALIZE-COMMA-NAMES, CACHE-DATE-TEST, EXPORT-STORE-PURGE, AXE-E2E, E2E-UIFULL-CI, and related); wave 3 from `f3f2003` (post-merge batch #335, EXTRACT-PAGE-MERGE, UI-THEME, RUNNER-EXC-INTERP, SAFETY-MODE-REAL, and the remaining wave-2 merges).
- **Merged by L0 since `f3f2003` (each after review PASS, green checks, and a focused test run where the row is code):** #326 `7972a2e`, #324 `c459398`, #330 `bc13072`, #325 `035637e`, #332 `9bed7a8`, #327 `fe9581f`, #339 `fc4750e`, #303 `b7288bd`, #337 `1343b62`, #331 `2bf4647`, #328 `782509d`, #334 `8087b73`, #336 `b3c6228`. **origin/main** is `b3c6228`.
- **Frontend revamp planning:** Opus agents produced [docs/research/2026-10-23-frontend-revamp/](../research/2026-10-23-frontend-revamp/00-README.md) and the revamp plan on #311; owner prompt 44 (UI direction) and follow-ups 45–48 landed in [owner-decisions-2026-09-27.md](../capstone-report/owner-decisions-2026-09-27.md). **UI-THEME** (#337) merged; main chunk **181.05 kB gz > 180 kB** budget was already over limit on `fe9581f` — note for the post-merge batch; **UI-ROUTES** must bring it under.
- **Owner prompts 43–50 answered** (43–49 in owner-decisions; prompt 50 evidence on #334 comment 6381125044 — batch must add the EXPORT-PURGE-DIFF row). Table gives the option chosen; free-text answers are quoted verbatim in the owner-decisions file; anything else in a cell is labelled as L0 reading:

  | Prompt item | Answer |
  |---|---|
  | WEAR-FIT-LIC (43) | MIT decoder (fitdecode); JSON too; upstream-safe (Recommended) — see `:405` |
  | UI-SAAS-MEANING (44) | Craft + bold showcase |
  | UI-SCOPE-1031 (44) | Full plan, no freeze |
  | UI-DARK-MODE (44) | Follow OS setting (once every page migrated) |
  | UI-SAFETY-TOGGLE (44) | Make it real |
  | UI-DEPS (45) | Keep framer-motion 10 / 7-day cooldown path per evidence on #311 |
  | UI-FIXTURE-NAME (45) | Replace with fixture ("Alex Rivera") |
  | SRE-LOGIN-GCTIME (46) | Yes, both edits (`useLogin` `gcTime: 0` + e2e auth spec) |
  | OCR-SIZE (47) | Accept 271 MB |
  | UI-ROUTE-MOTION (48) | Whole-page fade |
  | UI-AUTH-SCREENS (48) | Layout, motion and Lift |
  | SESSION-LOCK-NOW (48) | Add Lock now |
  | EXPORT-PURGE-EDIT (49) | Yes, these three lines |
  | EXPORT-PURGE-DIFF (50) | **Merge, purge first** (L0 evidence comment 6381125044 on #334; owner-decisions row added by batch #343) |
  | SAFETY-MODE-BEHAVIOUR (51, multi-select) | **Stricter checks**, **Always-on citations view**, **Verified-only data**; not Template-only explanations (L0 evidence comment 6382001534 on #338; owner-decisions row added by batch #343) |

- **SAFETY-MODE-REAL (#338)** escalated after three REVISE rounds (Option D missed four interpretation routes). The interim L0 had Composer fix it (`cf45e4e`): Option D now lists all six handlers in `api/interpretations.py` (`:380`, `:453`, `:626`, `:689`, `:743`, `:806` on `b3c6228`), L0 verified every cite and that no other module reads stored interpretations, the owner answered prompt 51, and #338 merged (`8103e4f`). **Next:** plan build rows for the three chosen options (A Stricter checks, C Always-on citations view, D Verified-only data). As designed none edits an ask-first file; if a build finds it must edit `faithfulness.py` or `verifier_agent.py`, stop and ask SAFETY-MODE-DIFF with the draft wording in the research README.
- **Model routing (owner 2026-10-24):** never use Sonnet 5.5; Haiku 5.5 **xhigh** replaces every former Sonnet role. Until #340 merges, launch workflows from patched copies in `/tmp/claude-1000/wf-haiku/` (copy to the session scratchpad; `Workflow({scriptPath})`). During this Cursor interim handoff session Haiku was unavailable, so **Composer 2.5** implemented with **Opus 5.5** review.
- **RSI archive PR #342** (`docs/rsi-archive-gpubox-1024`): windowed GPU-box logs 2026-10-21..24. L0 review PASS (comment 6381973844: metadata-only keys, no command or text fields, file paths only `<outside-repo>`/`.claude`, secret hits only `tokens_per_item`); merged through the docs chain after #343 by the interim L0 (check `gh pr view 342`).
- **Post-merge batch #343** (interim session): done rows for all 13 merges since `f3f2003` plus #329, #333, #338; owner rows prompts 50 and 51; count slot 2462; the follow-up bullets below. Merged through the docs chain (check `gh pr view 343`). The list below is what it applied, kept for reference. The orchestrator must apply everything under **batch todo** / **follow-ups** in the wave file, including: **A11Y-CRIT-LABELS** (label on `/explain` date inputs, `select-name` on `/settings` select; critical axe; CI run 40068287285); **UI-TOKENS** remove KNOWN_A11Y color-contrast entries; **EXTRACT-PAGE-MERGE** row files + HC-EXF-006 rewrite, HC-EPM-004/005, delta +5; **EXTRACT-LEGEND-LINES** (legend/target lines with units on table pages → unverified obs); **RECOVER-CACHE-CLEAR** (`RecoverProfile.tsx:73` no `queryClient.clear`); **RECOVERY-CODE-RATELIMIT** (`POST /profiles/{id}/recovery-code` no limiter); **DOCS-VISIT-EXC-LOG** (`api/documents.py:988` logs `{e}`); **EXPORT-RESTORE-PURGE** (`backup.py:453` restore doesn't clear exports); **EXPORT-ARTIFACT-PURGE** (with I-20/C-GC1); queue row **EXPORT-STORE-PURGE** files + `api/pinboards.py`; record prompt **50** in owner-decisions; **FE-IMPORT-ERROR** queue row add `e2e/document-import.spec.ts` (L0 ruling #313); **EXTRACT-TABLE-VALUE** delta +19 not +11; LLAMA follow-ups from wave 1; prior batch bullets still open (VERIFY-UNDO, AUTO-LOCK-UNUSED, RAG-TIMEOUT grounded path plan delta, and wave-2 notes on HYPOTHESIS-EXTRACT / AGENT-DATEONLY-TZ).
- **Collected count:** **2462** measured by L0 on `b3c6228` and again on `8103e4f` (`pytest --collect-only -q`); batch #343 moves the CLAUDE.md / AGENT.md slot from 2423 to 2462. Measure again on fresh main after every merge wave.
- **Harness scripts** unchanged in behaviour: `merge_par.sh` (not `gatemerge_par.sh`), `chain_merge.sh`, `docs_chain.sh`, `hold_slots.sh` — full copies in §4.

### L0 rulings this session

- **Dirty-worktree resume:** comments that license keeping uncommitted work and `resume_pr` must start with the literal prefix **`L0 ruling:`** (not a markdown heading). Example: E2E-UIFULL-CI #333 needed such a ruling for `ExplainAssistant.tsx` before resume.
- **Ready PR retitle:** to resume a PR that is already ready, first retitle it **`[blocked:claude]`** (with `gh api -X PATCH` if `gh pr edit` fails): `build-item.js:150` only resumes the item's own stopped `[blocked:claude]` draft, or an `[escalated:claude]` one with an `L0 ruling:` comment after the escalation.
- Owner free-text answers are quoted verbatim in the owner-decisions file or PR evidence comments, never L0 summaries.

## 2. Open PRs at handoff

States checked with `gh pr list --state open` and `gh pr view` at write time (main `b3c6228`).

| PR | Item | State at write time | Next step |
|---|---|---|---|
| #344 | this handoff | open (interim L0) | Docs chain after #342; check `gh pr view 344` |
| #343 | post-merge batch 2026-10-24 | open (interim L0) | Docs chain first; check `gh pr view 343` |
| #342 | RSI archive GPU-box 2026-10-21..24 | open; L0 review PASS | Docs chain after #343 (rebase + regenerate index); check `gh pr view 342` |
| #341 | RSI hint Bash "No such file" (RSI-4) | open; MERGEABLE | **Owner merges** (RSI PR) |
| #340 | Sonnet → Haiku 5.5 xhigh routing | open; MERGEABLE | **Owner merges**; unblocks default workflow scripts |
| #317 | RAG-TIMEOUT-ANSWER | draft `[blocked:claude]` | Blocked pending plan delta (grounded path) |
| #316 | DEV-PS1-FIRSTRUN | draft | Waits on owner Windows **DPF-1..3** |
| #264 | B-3 advice judge | draft; CONFLICTING | Draft until B-4; **never agent-merged** |
| #239 | RSI1-DONATE PR-2 | draft `[blocked:claude]` | Parked; **never agent-merged** |
| #230 | RSI embedding-bundle hint | open; MERGEABLE | **Owner merges** (RSI PR) |

Owner merge commands (RSI; `--delete-branch=false` so WSL worktrees survive):

```
gh pr merge 230 --merge --delete-branch=false
gh pr merge 341 --merge --delete-branch=false
gh pr merge 340 --merge --delete-branch=false
```

## 3. Next

1. **Confirm the interim docs chain landed:** `gh pr view 343`, `342`, `344` all MERGED; if any is still open, finish it one at a time (`docs_chain.sh`).
2. *(done in the interim session: #333 `4c5e619`, #329 `a48cdbc`, #338 `8103e4f`, owner prompt 51.)*
3. **Plan the SAFETY-MODE build rows** for the owner's three choices (A Stricter checks, C Always-on citations view, D Verified-only data) from the #338 research README; D must gate all six interpretation handlers including the two GET routes.
4. **A11Y-CRIT-LABELS** and **UI-TOKENS** now own the `KNOWN_A11Y` entries in `e2e/accessibility.spec.ts`: each fix deletes its entries; nothing may add one.
5. **Merge order reminder:** frontend UI-\* rows that touch `ExplainAssistant.tsx` must keep `data-testid="chat-message"` / `data-role` (E2E-UIFULL-CI ROUTES-002).
6. **build-wave** after batch: frontend **UI-\*** rows from the revamp plan, **A11Y-CRIT-LABELS**, IMPORT-SCANNED-PAGE / extract follow-ups unblocked by queue updates.
7. **Model-host rows on this box**, holding `hold_slots.sh` with **no pytest running:** JUDGE-LAYA-RESEARCH, DON-NER-MEASURE, QWEN3-4B-TIER, AUDIT-DB-LOCKED Task 1 repro, KV-NUMCTX-VERIFY.
8. **Owner actions pending** (remind, do not do): write S5 (OW-3); P6 orphan audit; Garmin export notes (OW-W3); de-identified lab page (EXF-SAMPLE); RSI Replay required check; demo-clone `.env` (SHOW-O3) before 2026-10-31; Windows DPF-1..3 for #316.
9. **Refresh the progress dashboard** (Haiku xhigh task once #340 merges; was Sonnet in older handoffs).
10. **Run rsi-loop** with the mod loaded, then archive any new RSI logs per [rsi-runs README](../agentic/rsi-runs/README.md) (windowed copy policy).
11. **Write the next handoff** replacing this file.

## 4. Harness gotchas

- **Never Sonnet 5.5** (owner 2026-10-24); use Haiku 5.5 xhigh for prior Sonnet roles, or patched workflows until #340 merges.
- **L0 ruling:** literal prefix `L0 ruling:` for dirty-worktree resume; retitle a ready PR to `[blocked:claude]` before resuming it.
- **Owner gates** never inferred; ask-first files (`interpret_safety`, `redaction`, `faithfulness`, `verifier_agent`, auth/encryption) need the owner's yes.
- **Haiku and agent reports are leads.** Re-verify with a focused test run before merge.
- **`hold_slots.sh` must cover locks 1–8** so no `PYSLOTS>3` pytest runs during model-host work.
- **`gh pr edit` fails** (Projects classic GraphQL error): use `gh api -X PATCH repos/{owner}/{repo}/pulls/N`. gh 2.45 has no `pr checks --json`: read `statusCheckRollup`.
- Unchanged: never `ruff format`; three-dot diffs only; docs PRs merge one at a time (`docs_chain.sh`); merge only after review PASS; owner merges RSI PRs with `--delete-branch=false`.

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

## 5. /goal prompt for the next L0

```
/goal Resume the Asclexis build program from docs/plans/2026-10-24-session-handoff.md (read it, CLAUDE.md, AGENT.md and the build-program RUNBOOK first; verify every claim with gh / git log). Setup: fast-forward main (or fresh clone), venv ~/venvs/asclexis-311 (uv-managed: uv pip install --python ~/venvs/asclexis-311/bin/python -r src/backend/requirements.txt), the embedding bundle in every worktree (cd src/backend && python scripts/download_models.py embedding), measure the collected count (expect 2462 on 8103e4f plus later merges) and `from main import app`, recreate merge_par.sh, chain_merge.sh, docs_chain.sh and hold_slots.sh in /tmp/claude-1000/ from the handoff §4 appendix (merge_par.sh not gatemerge_par.sh), confirm a local model runs through ModelRunner (Ollama: llama3.1:8b or qwen3:8b), and start the session with --plugin-dir .claude/mods/asclexis-rsi. Until #340 merges, launch build-item/build-wave workflows from patched copies in /tmp/claude-1000/wf-haiku/; never use Sonnet 5.5. Then, in priority order: (1) confirm #343 (post-merge batch), #342 (RSI archive) and #344 (this handoff) merged, and finish any that did not, one at a time through the docs chain; (2) #333, #329 and #338 are already merged and SAFETY-MODE-BEHAVIOUR is answered (prompt 51: Stricter checks, Always-on citations view, Verified-only data), so plan the SAFETY-MODE build rows for those three from the #338 research README; (3) build-wave UI-* rows and A11Y-CRIT-LABELS; (4) model-host rows holding hold_slots.sh with no pytest: JUDGE-LAYA-RESEARCH, DON-NER-MEASURE, QWEN3-4B-TIER, AUDIT-DB-LOCKED Task 1, KV-NUMCTX-VERIFY; (5) remind owner pending actions (S5, P6, Garmin, EXF-SAMPLE, RSI Replay, SHOW-O3 .env, DPF-1..3 for #316); (6) refresh dashboard (Haiku xhigh); (7) rsi-loop then archive windowed logs. Merge each non-owner PR yourself once review PASS and checks green; #230, #341 RSI PRs and #340 are owner-merged; #239 and #264 never agent-merged. Rules: L0 rulings that license dirty-worktree resume start with literal "L0 ruling:"; a ready PR is retitled [blocked:claude] before it is resumed; owner answers quoted verbatim; ask-first files need owner yes. Done when the docs chain has landed, the SAFETY-MODE build rows are planned, open PRs are merged or documented, rsi-loop has run once with the mod loaded, and a new handoff replaces this one.
```
