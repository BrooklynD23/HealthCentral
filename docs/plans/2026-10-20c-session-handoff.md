# Session handoff: 2026-10-20 local session → GPU machine (L0)

**Last Updated:** 2026-10-20
**Owner:** repository owner
**Refresh Trigger:** the next L0 session reads this first, works §3, and replaces this file with its own handoff.
**Superseded by:** [2026-10-21 GPU-session handoff](2026-10-21-session-handoff.md).

Read this after [CLAUDE.md](../../CLAUDE.md), [AGENT.md](../../AGENT.md) and the [build-program RUNBOOK](2026-10-15-build-program/RUNBOOK.md). It replaces [the 2026-10-20b handoff](2026-10-20b-session-handoff.md). This session ran on the owner's laptop (no GPU, no Ollama). The owner's instruction: "commit & push everything off this dev machine; continue on the GPU machine". Treat this file as a lead: verify with `gh pr view` / `git log origin/main` before acting.

## 1. What this session did

**Merged since the 2026-10-20b handoff (batch #247 plus these):** harness and test rows #233 PYSLOT-MODE, #234 REDACT-NAME-PINS, #235 GATE12-MINORS, #236 WAVE-DEP-DONE, #237 F-4-FOLLOWUPS, #240 EMB-LOG-M7, #241 MSET-EXT-AUDIT-CT, #244 LLM-PATH-LOG-M2M3, #238 GRADE-PATTERN-REDOS, #245 PKT-Q-MINORS; docs #242 (RRSI owner answers OQ-1..27), #243 (OQ-8 RSI Track 1 status), #247 (post-merge batch, count 2106), #248 (plan of 10 follow-up rows), #249 (G-C5 real-model evidence, CPU).

- **Queue items done this session:** PYSLOT-MODE, REDACT-NAME-PINS, GATE12-MINORS, WAVE-DEP-DONE, F-4-FOLLOWUPS, EMB-LOG-M7, MSET-EXT-AUDIT-CT, LLM-PATH-LOG-M2M3, GRADE-PATTERN-REDOS, PKT-Q-MINORS.
- **#248 planned 10 rows:** UNCERTAINTY-VERIFY, NLI-LOG-M7, PATH-REGEX-NEWLINES, HARNESS-VITEST-HINT, RRSI-CI-REPLAY, RRSI-LOOP-CRITIC, RRSI-H2-SANDBOX, AGENT-ENABLED-TOGGLE, RUNSTEP-CONTRACT, CHAT-TREND-DEF. Their owner gates are in queue.md (UNC-VERIFY-DIFF, PATH-NL-DIFF, RRSI-CRITIC-LIST, DON-COPY-V3 are still open).
- **G-C5 real-model evidence (#249):** the NLI model was fetched and run on this laptop (CPU). Findings are the five GC5-* / FEATURE-LIST-LICENCE rows in queue.md "New rows found while planning": the real NLI model labels `Your glucose was 95 mg/dL` neutral (0.858) and scores another case entailment 0.668 < 0.7, so with `use_llm_entailment` on the legacy gate fails (answer_rate 0.000). The flag stays default-off.
- **rsi-loop ran** (`run_id 2026-10-20-local`): 33 Bash failures (17x exit 1, 10x exit 2, 6x exit 144) were unminable because the Track-1 logger records exit codes but no error text; the session was also not started with `--plugin-dir .claude/mods/asclexis-rsi`. Row RSI-LOG-STDERR. **#230** (hint rule `embedding-bundle-missing`) is still open for the owner.
- **Owner rows recorded:** DON-RECALL-NAMES, GRADE-REDOS-DIFF (a), RRSI-OQ-1..27 (`docs/capstone-report/owner-decisions-2026-09-27.md`; off-recommendation picks: OQ-2 (b) run harness2 itself sandboxed, OQ-12 (c), OQ-15 (c)), plus UNC-VERIFY-SCOPE (a), CTD-DEF (a), CTD-SCOPE (a), AET-LABEL (a), DON-RECALL-R2 (park #239), RRSI-CRITIC-PARAMS (numbers only; word list = open gate RRSI-CRITIC-LIST), H2-SOURCE (c) from the planning batch.
- **G-C5 Task 7 caveat:** the plan names the owner/model host; this was an agent run on the laptop CPU under the owner's /goal ("if huggingface.co is reachable, run the G-C5 real-model steps"). The owner confirms on the model host whether it counts. UNMEASURED there: real LLM-generated claims and long-chunk truncation.
- **Setup notes (laptop):** the venv has no pip; requirements went in with `uv pip install --python ~/venvs/asclexis-311/bin/python -r src/backend/requirements.txt`. The embedding bundle was fetched with `EMBEDDING_MODEL_PATH=$HOME/asclexis-models/embeddings/all-MiniLM-L6-v2` and copied into every worktree.
- **Salvage check ("uncommitted RSI-loop research"):** nothing to salvage. `legacy-unlinked/hc-rsi-plan` is fully in history (1169 of 1169 blobs). The GitHub Desktop `stash@{0}` (on `docs/rsi-loop-research`) holds 3778 files of Sept-27 audit wave3 repo copies; owner said **keep it** (not dropped). `.serena/project.yml` is locally modified in the main checkout (tool config) and was not committed.

**Count:** **2118 collected** (2106 → 2118, +12) on the batch PR branch (origin/main `5eaaeac` + this docs-only change; embedding bundle present, `HF_HUB_OFFLINE=1`, sentence-transformers installed). Full-suite tail: see the batch PR body.

## 2. In flight at handoff

| PR | Item | State | Next step |
|---|---|---|---|
| #246 | REDACT-NAME-GAPS | draft, title still `[claim:claude]`, **escalated** after 3 REVISE rounds | Retitle to `[escalated:claude]` first (build-item resume needs the title plus an `L0 ruling:` comment). Branch leaks at strict where main redacts: `Name (legal): Maria de la Cruz Patient ID: 98765` main `[ID-REDACTED] de la Cruz [ID-REDACTED]`, branch `[ID-REDACTED]: 98765`; `Patient Name: José Núñez A12345` → `[NAME-REDACTED] A12345`. Resume from the round-3 reviewer's `name_context`-only conditional tail (fixes the 4 rows at both levels, HC-REDACT-013/021 byte-identical, strict fuzz down to 5 of 40k). REDACT-NG-DIFF not asked. |
| #239 | RSI1-DONATE PR-2 | draft, `[blocked:claude]`, parked by owner DON-RECALL-R2 | Do not resume until the owner un-parks it. It holds `test_audit_order_guard.py` (blocks AUDIT-GUARD-MINORS) and one `SettingsPage.tsx` line (AGENT-ENABLED-TOGGLE builds beside it; #239 rebases later). |
| #210 | F-9 showcase | draft, Task 8 done | On or after **2026-10-24** ask the owner **O-6**, run Task 10 Steps 2-3, then ready and merge. |
| #230 | RSI candidate | open, never agent-merged | Owner reviews and merges or closes. |

## 3. Next (dynamic workflow: build-wave, then one top-level `build-item` per id)

Every row below carries a dated stop in queue.md (2026-10-20, machine move): not started. The stop ends when the next L0 starts the row.

1. **Ready rows (no owner gate on the build):** NLI-LOG-M7, HARNESS-VITEST-HINT, RUNSTEP-CONTRACT, CHAT-TREND-DEF, AGENT-ENABLED-TOGGLE (L0 ruling: build now, #239 rebases later), RRSI-CI-REPLAY (owner merges).
2. **Build on draft, merge gated:** UNCERTAINTY-VERIFY (UNC-VERIFY-DIFF), PATH-REGEX-NEWLINES (PATH-NL-DIFF; GRADE-PATTERN-REDOS is merged), REDACT-NAME-GAPS (REDACT-NG-DIFF, resume #246 per §2).
3. **Needs the GPU machine:** model-bound rows and measurements. Start with G-C5 follow-ups (GC5-NLI-NEUTRAL, GC5-PREDICT-FAILCLOSED, GC5-FAITH-SCORE need planning first), then MM-1 / MM-2 / MM-4 (owner: run on the RTX 3080 machine; B-7, B-4, B-9 are needs-model-machine). No pytest while a model run holds the pyslot locks.
4. **Plan the new bullets** in queue.md "New rows found while planning": GC5-NLI-NEUTRAL, GC5-PREDICT-FAILCLOSED, GC5-FAITH-SCORE, FEATURE-LIST-LICENCE, RSI-LOG-STDERR (plus the older unplanned COUNT-ENV-VARIES governance wording, owner).
5. **Blocked:** RRSI-LOOP-CRITIC on RRSI-CRITIC-TRUST (open design issue; Workflow scripts have no filesystem access, so "trusted JS reads the bytes" needs a design); RRSI-H2-SANDBOX on H2-SETUP (owner action); RSI1-DONATE PR-2/PR-3 (#239 parked); AUDIT-GUARD-MINORS (queue rule "never beside RSI1-DONATE PR-2", and parked #239 still holds `test_audit_order_guard.py`; L0 may rule it buildable beside the parked draft, as for AGENT-ENABLED-TOGGLE).
6. **Owner-blocked:** O-6 (2026-10-24); P6-ORPHAN (C-P6 Tasks 2-5 → C-P7 → E-2, C-GC1, RSI1 reset tuple); OW-3, OW-W0/W3/W7; E-6 (interactive `/agents`); REDACT-NG-DIFF; UNC-VERIFY-DIFF; PATH-NL-DIFF; DON-COPY-V3; RRSI-CRITIC-LIST; #230. G-C2 stays deferred; F-8 stays disabled.
7. **Post-merge batch** after each merge group (SLOT-RULE-2).
8. **RSI:** start the session with `--plugin-dir .claude/mods/asclexis-rsi`, run `rsi-loop` once after the day's run.

## 4. Harness defects and gotchas

- **The Track-1 session logger records exit codes but no error text** (RSI-LOG-STDERR): rsi-loop cannot mine Bash failures until it does.
- **A released draft cannot be resumed:** build-item resume needs a `[blocked:claude]` or `[escalated:claude]` title plus an `L0 ruling:` comment. L0 retitles first (#246).
- **An `l0_note` that says "commit nothing new" also stops review-fix rounds.** Scope such notes to the first implement call.
- **gh 2.45:** no `gh pr checks --json`; read `statusCheckRollup` instead. On Projects-classic GraphQL errors use `gh api`.
- **Windows `gh pr merge` prunes WSL worktree metadata** (owner's Windows `gh`): run `git worktree list` after merges.
- **Stale-checkout pitfall:** `git fetch` and fast-forward main in the main checkout before reading queue.md.
- **The collected count varies by environment** (COUNT-ENV-VARIES): sentence-transformers adds tests. Measure in the same environment; the baseline is 2118 with it installed.
- **Docs PRs go stale against main:** Backend Tests fails on `test_docs_lint.py::test_docs_index_check_passes_on_real_repo` when `docs/INDEX.md` lags (seen on #249). Merge main into the branch, re-run `scripts/generate_docs_index.py`, push. `merge_par.sh`'s server-side `update-branch` does not regenerate the index, so merge docs PRs one at a time.
- **The auto-mode classifier blocks merging a PR that had no review** (seen on #242/#243 written by a plain agent). Get a reviewer's PASS first.
- **merge_par.sh used to report "all done" when a PR's checks failed** (the failed PR was dropped silently). Fixed below: it now prints `done; FAILED (not merged): …` and exits 1.
- **Haiku test-runner reports were wrong twice** (a "2091 passed" beside 2103 collected; mutant runs skipped). The Sonnet/Opus verify step caught both; keep it.
- **Session rate limit** killed 2 agents mid-run. Continue with `SendMessage` to the agent or `Workflow` `resumeFromRunId`; do not start fresh.
- **Review-loop depth:** RRSI-LOOP-CRITIC took 4 Codex (gpt-6.1-sol) rounds; L0 stopped it with a documented block (RRSI-CRITIC-TRUST) rather than a 5th round. Codex CLI 0.163.0 is on the laptop; check it on the GPU machine (CODEX-UNAVAIL substitute otherwise).
- Unchanged: never `ruff format`; three-dot diffs only; no pytest during model runs (hold all three pyslot locks); build-wave can misread multi-task depends_on chains (WAVE-DEP-DONE is advisory only).

`merge_par.sh` (updated: reads `statusCheckRollup`, retries up to 90 x 40 s; recreate at `/tmp/claude-1000/merge_par.sh` and replace `<repo checkout>` with the path of this repo's main checkout). Usage: `bash merge_par.sh <pr> <pr> ...`; it merges each PR only when every check is green and the PR is mergeable. It never merges RSI PRs on its own: do not pass #230.

```bash
#!/usr/bin/env bash
# Update all branches once, then merge each PR as soon as its checks are all green.
cd "<repo checkout>"
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

## 5. /goal prompt for the next L0 (GPU machine)

```
/goal Resume the Asclexis build program from docs/plans/2026-10-20c-session-handoff.md on this GPU machine. Setup first: git fetch and fast-forward main in the main checkout (stale-checkout pitfall); create ~/venvs/asclexis-311 with src/backend requirements if missing; make sure the embedding bundle exists (~/asclexis-models/embeddings/all-MiniLM-L6-v2, else cd src/backend && python scripts/download_models.py embedding) and copy it into every worktree you create; install Ollama or llama-cpp and confirm a local model runs through ModelRunner; recreate /tmp/claude-1000/merge_par.sh from handoff §4 if missing; measure the collected count in this environment (2118 with sentence-transformers) and the app import. Start the session with --plugin-dir .claude/mods/asclexis-rsi. Then: (1) retitle #246 to [escalated:claude], add an L0 ruling comment, and resume REDACT-NAME-GAPS from the round-3 reviewer's name_context-only conditional tail, then ask the owner REDACT-NG-DIFF with the exact diff; (2) run build-wave and start each eligible row as its own top-level build-item workflow (dynamic workflow; Opus L1, Sonnet implement, Haiku tests), beginning with the §3 item 1 ready rows; build UNCERTAINTY-VERIFY and PATH-REGEX-NEWLINES on drafts and ask UNC-VERIFY-DIFF / PATH-NL-DIFF with the exact diffs; (3) run the planner on the five new queue bullets (GC5-NLI-NEUTRAL, GC5-PREDICT-FAILCLOSED, GC5-FAITH-SCORE, FEATURE-LIST-LICENCE, RSI-LOG-STDERR); (4) run the model-bound steps the laptop could not: the G-C5 real-model measurements on the GPU and the MM-1 / MM-2 / MM-4 runs, holding all three pyslot locks (no pytest during model runs); the use_llm_entailment flag stays off. On or after 2026-10-24 ask the owner O-6 for #210, then finish F-9. L0 merges green review-PASS PRs with merge_par.sh and runs a post-merge batch after each group; RSI PRs (#230 and new ones) are never agent-merged; #239 stays parked until the owner un-parks it. Rules as in CLAUDE.md: owner gates never inferred; ask-first diffs (redaction.py, interpret_safety, faithfulness, verifier_agent, auth/encryption) need the owner's yes; never ruff format; three-dot diffs only. Done when every non-owner-blocked row is merged or has a documented stop, a new handoff replaces this one, and rsi-loop has run once after the full-day run.
```

## 6. Final report

- **Merged this session:** 16 PRs: 10 queue rows (§1) plus docs #242, #243, #247, #248, #249, and this batch.
- **Measured count:** 2118 collected (2106 → 2118); full-suite result in the batch PR body.
- **Open PRs:** #246 (escalated draft), #239 (parked draft), #210 (draft, 2026-10-24), #230 (RSI, owner).
- **Open owner gates:** O-6 (2026-10-24), P6-ORPHAN, OW-3, OW-W0/W3/W7, E-6, REDACT-NG-DIFF, UNC-VERIFY-DIFF, PATH-NL-DIFF, DON-COPY-V3, RRSI-CRITIC-LIST, COUNT-ENV-VARIES, #230; G-C2 deferred, F-8 disabled.
- **Cleanup:** old worktrees under `../hc-*` and `../HealthCentral.worktrees/*` for merged PRs can go (`git worktree list`, then `git worktree remove`); `hc-redact-name-gaps` and `hc-rsi1-donate` hold unmerged work, keep them until #246 and #239 are resolved.
