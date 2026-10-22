# Session handoff: 2026-10-19 → 2026-10-20 (L0, Opus 5.5)

**Last Updated:** 2026-10-20
**Owner:** repository owner
**Refresh Trigger:** the next L0 session reads this first, finishes §2 "In flight", works §3, and replaces this file with its own handoff.
**Superseded by:** [2026-10-20 cloud-session handoff](../archive/plans/2026-10-20b-session-handoff.md).

Read this after [CLAUDE.md](../../CLAUDE.md), [AGENT.md](../../AGENT.md) and the [build-program RUNBOOK](2026-10-15-build-program/RUNBOOK.md). It replaces [the 2026-10-19 handoff](../archive/plans/2026-10-19-session-handoff.md). The session ended because the owner moved development to another machine ("Please push everything, so that it can be properly recorded on origin main. Pass a handoff prompt, to be continue development in another machine"). Every worktree was clean and fully pushed at handoff. Treat this file as a lead, not a finding: verify with `gh pr view` before acting.

## 1. What this session did

**Merged** (each with a final review PASS and green CI; ask-first diffs only after the owner's yes): #183 #189 #192 #193 #194 #195 #196 #197 #198 #199 #200 #201 #185 #202 #203 #204 #205 #206 #207 #209 #212 #213 #214 #216, and #208 if its merge loop finished (check).

- **Queue items done:** G-C5-PLAN, REPROCESS-ATOMIC, AUDIT-GUARD-TEST, MSET-EXT-NOKEY-TEST, E-1c, W-8-HARDEN, EXPORT-TZ-PINS, F-4, LEGACY-CITE-PROMPT (+ eval metric fix #201), W-8-FC-NOTICE, CFR-CACHE-TZ, GATE-12, Q-COV-GATE, MSET-EXT-NOKEY-PIN, REDACT-WS-REDOS, PKT-QUESTIONS-REDACT, EMB-LOAD-LOG-PATH, LLM-PATH-LOG (#208, if merged).
- **Planning PRs:** #189 (8 follow-ups of 2026-10-18), #202 (9 follow-ups of 2026-10-19).
- **Owner rows:** #199, #205, and this PR (showcase O-1/O-2/O-4/O-5/O-7, PKT-Q-DIFF, REDACT-WS-REDOS-DIFF).
- **Post-merge batches:** #197, #216.

**Count:** 2026 collected on `2ab550a` (#216 wrote the slots). Full suite with `--cov-fail-under=74` on `2ab550a`: `2026 passed`, coverage 75.70%, and no `src/backend/data/asclexis.db` created (the GATE-12 guard holds). This was the recurring-failures #12 recheck for GATE-12 and Q-COV-GATE.

**LCP Task 5:** the quiet re-run is `~/asclexis-evals/t2e-lcp-d13b9a5-quiet` on the old machine; it was run with vLLM stopped and all pyslot locks held. Rule (a) failed as measured on one artefact: the eval counted digits in `[USER_OBSERVATION:N]` labels as values. The owner ruled LCP-METRIC-RULING, so #201 stripped a closed label set, the saved JSON was re-scored, and rule (a) passed. #185 merged. The Δ table and the served answers are in #185 comment 6270643786.

**Owner answers this session:** all recorded in `docs/capstone-report/owner-decisions-2026-09-27.md`.
- **2026-10-19:** GC5-OL-1..3, E1C-SCOPE, E1C-DIFF, LCP-ACCEPT, LCP-HEADERLESS, REDACT-WS-REDOS, SHOW-FREEZE (showcase 2026-10-31, freeze 2026-10-24), all 13 DON-*, OW-W6/8/9/10/11/12, P8-B2, G-C2-UNDEFER (keep deferred), GATE-12, Q-COV (74%), F-8-ENABLE (keep disabled).
- **Prompts 15 and 16:** LCP-HL-SCOPE (a), LCP-HL-LABELS (a), REDACT-WS-REDOS-BUILD (a), PKT-Q-SCOPE (a), AUDIT-SCHED-READ (a), LCP-METRIC-RULING.
- **2026-10-20:** SHOW-O1/O2/O4/O5/O7, PKT-Q-DIFF, REDACT-WS-REDOS-DIFF.

**Not-recommended choices to respect:**
- DON-CANARY (b), drop and continue. It contradicts plan :79-80/:85 and HC-DON-017/018, so PR-3 needs a plan delta.
- DON-FT-SCOPE (b), LoRA + extraction probe. This puts model-machine work into PR-3.

## 2. In flight at handoff (finish these first)

| PR | Item | State | Next step |
|---|---|---|---|
| #208 | LLM-PATH-LOG | ready, 2× PASS, merge loop was running | `gh pr view 208`; merge on green if still open |
| #215 | LCP-HEADERLESS | draft `[blocked:claude]`, head `529cb99`. L0 rulings on the PR: (1) scope extension to `claim_extractor.py` `_parse_sections` (round-1 BLOCKER: prefixed text was served unverified, so a false "300 mg/dL" reached the patient); (2) the PROTECTED-FILE stop was a two-dot-diff false positive | `build-item {id: LCP-HEADERLESS, resume_pr: 215}`: merge origin/main, three-dot protected check, suite, review round 2. Then ask the owner **LCP-HL-DIFF**, disclosing everything listed in the ruling |
| #211 | RSI1-DONATE PR-1 | draft `[blocked:claude]`, head `d30a1f4`. Round 2 REVISE on `b7206f8` (MAJOR: the consent copy left out a decided point). `d30a1f4` is an unreviewed fix. L0 rulings: correction_redacted column in 015; reject an unknown consent_text_version (422); copy names question + answer + correction; test_gamification_settings.py head asserts made head-agnostic | `build-item {id: RSI1-DONATE, resume_pr: 211}`: verify the round-2 MAJOR fix, run round 3, then Codex. Then ask the owner **DON-COPY** with the final copy verbatim. Never edit `api/profiles.py` (waits on C-P7) |
| #210 | F-9 showcase | draft, round 3 PASS. Must stay draft until the freeze: plan Task 10 Step 3 puts the binding freeze record (O-6) in this PR, and plan §14 says do not mark it ready before then. Task 8 was skipped for want of O-4, which is now answered (B) | resume to do Task 8 (O-4 B). On or after **2026-10-24**, ask the owner **O-6** (claim freeze), then ready and merge. O-3 and Task 9 (demo dry runs) are the owner's, on the Windows demo machine |

## 3. Next (dynamic workflow: build-wave, then one top-level `build-item` per id)

1. **After #215 merges:** G-C5. Its gates are all answered (GC5-ASKFIRST, Q5a/Q5b, GC5-OL-1..3). It is never beside LCP-HEADERLESS or EMB-LOAD-LOG-PATH (done), and is last on `rag.py`. It fetches the NLI model once via `download_models.py`, which is network use by design (Q5b).
2. **After #211 releases `test_audit_order_guard.py`:** AUDIT-GUARD-MINORS. AUDIT-SCHED-READ (a) is answered.
3. **RSI1-DONATE PR-2:**
   - Its file list needs `api/feedback.py` (DON-RLEXPORT) and the chat-session delete route (DON-SRC-DELETE).
   - PR-3 needs a plan delta for DON-CANARY (b) and model-machine time for DON-FT-SCOPE (b).
4. **Follow-up bullets** in queue.md "New rows found while planning", added by #216: run the planner on them. One more to add: LLM-PATH-LOG review M2/M3, model paths still logged at ERROR (`llama_cpp_provider.py:152`, `model_selector.py:477`) and at INFO/WARNING (`model_selector.py:660,740`, `llama_cpp_provider.py:110`). Never beside B-5.
5. **Owner-blocked:**
   - P6-ORPHAN: run `python scripts/fk_orphan_audit.py --profile <id> --source <COPY of vault>` and paste the counts. This is the biggest unblock: C-P6 Tasks 2-5, then C-P7, then E-2, C-GC1 and the RSI1 reset tuple.
   - OW-3 (S5 sealed set), after a B-3 draft exists. B-3 also needs the Codex plan review (R-22, an L0 ruling, not an owner gate).
   - Wearables actions OW-W0, OW-W3, OW-W7.
   - E-6: W1-SMOKE-RUN says an agent runs it, but it needs an interactive `/agents` session.
   - G-C2 stays deferred; F-8 stays disabled.
6. **Post-merge batch** after each merge group (SLOT-RULE-2).
7. **RSI:** run `rsi-loop` once after the full-day run. The owner asked for an asclexis-rsi check-in; it has not run this session.

## 4. Harness defects and gotchas (new this session)

- **build-item explore reads `queue.md` from the main checkout when it exists.** If that checkout is stale, the row is "not found" (seen with E-1c right after #189 merged). Workaround: fast-forward main before starting items. Fix: always `git show origin/main:<queue>`.
- **build-wave misread C-P6 as done** because Task 1 (#113) merged, and picked C-P7. L0 skipped it. Check the depends_on chains yourself.
- **The protected-file check uses a two-dot diff**, so a branch older than a merged ask-first change looks like it edits that file (#215). Fix: `origin/main...HEAD`.
- **Embedding bundle per worktree:** build-item Task 0 still doesn't install it, and L0 notes forgot it twice (F-4, and the main checkout). Every l0_note should say: copy `~/asclexis-models/embeddings/all-MiniLM-L6-v2` into `<wt>/src/backend/models/embeddings/`, or run `python scripts/download_models.py embedding`.
- **The main checkout's `scripts/pyslot.sh` is CRLF in the working tree** (`git ls-files --eol`: i/lf w/crlf), so it fails with `bash\r`. Worktrees are fine. Use `bash <(tr -d '\r' < scripts/pyslot.sh) …` or re-checkout with LF.
- **Model runs vs pytest:** the eval was wrapped to hold all three `/tmp/claude-1000/hc-pytest.{1,2,3}.lock` slots, so build-item pytest waited. Reuse that pattern for any model run.
- **A Haiku runner pasted another worktree's suite output** (#211; it named `hc-redact-ws-redos`). L1 caught it. Check paths in runner output.
- **The harness flagged "CI Bypass"** on the Q-COV-GATE implementer (#207). L0 checked the transcript and diff: it only added `--cov-fail-under=74`, with no skip, no-verify or force-push. The flag fires on `ci.yml` edits.
- **Merge-on-green script:** it lived at `/tmp/claude-1000/merge_par.sh` on the old machine; recreate it from §6.
- **Old machine state:** the owner's vLLM server (`local-classify`, port 8800) was stopped for the eval and left off at the owner's choice.

## 5. /goal prompt for the next L0 (other machine)

```
/goal Resume the Asclexis build program from docs/plans/2026-10-20-session-handoff.md on this machine. Setup first: clone or pull main; create the Python 3.11 venv at ~/venvs/asclexis-311 with src/backend requirements; fetch the embedding bundle once (cd src/backend && python scripts/download_models.py embedding) and copy it into every worktree you create (src/backend/models/embeddings/, gitignored); recreate the merge-on-green script from handoff §6 as /tmp/claude-1000/merge_par.sh; measure the collected count (expect 2026) and the app import. Then finish §2 in flight: merge #208 on green; resume #215 (LCP-HEADERLESS) and then ask the owner LCP-HL-DIFF; resume #211 (RSI1-DONATE PR-1) and then ask the owner DON-COPY with the final copy verbatim; resume #210 (F-9) for Task 8 (O-4 = B), keep it draft until the 2026-10-24 freeze, then ask O-6. Then run build-wave and start each eligible row as its own top-level build-item workflow (dynamic workflow; Opus L1, Sonnet implement, Haiku tests): G-C5 after #215, AUDIT-GUARD-MINORS after #211, and the planner for the queue's unplanned follow-up bullets. L0 merges green review-PASS PRs with merge_par.sh and runs a post-merge batch after each group. Rules as in CLAUDE.md and the 2026-10-18 handoff §5: owner gates never inferred; ask-first diffs need the owner's yes; never ruff format; no pytest during model runs (hold the pyslot locks); fix stale-checkout and two-dot-diff pitfalls per §4. Done when every non-owner-blocked row is merged or has a documented stop, a new handoff replaces this one, and rsi-loop has run once after the full-day run.
```

## 6. merge_par.sh (recreate on the new machine)

```bash
#!/usr/bin/env bash
# Update all branches once, then merge each PR as soon as its checks are all green.
cd "<repo checkout>"
pending=("$@")
for n in "${pending[@]}"; do gh pr update-branch "$n" >/dev/null 2>&1 && echo "#$n updated" || echo "#$n update skipped"; done
for i in $(seq 1 90); do
  sleep 40; left=()
  for n in "${pending[@]}"; do
    st=$(gh pr checks "$n" --json state --jq '[.[].state] | if length==0 then "WAIT" elif all(.=="SUCCESS") then "OK" elif any(.=="FAILURE" or .=="CANCELLED") then "FAIL" else "WAIT" end' 2>/dev/null)
    m=$(gh pr view "$n" --json mergeable --jq .mergeable)
    if [ "$st" = OK ] && [ "$m" = MERGEABLE ]; then
      gh pr merge "$n" --merge >/dev/null 2>&1 && gh pr view "$n" --json mergeCommit --jq '"#'"$n"' MERGED \(.mergeCommit.oid[0:7])"' || { echo "#$n merge refused"; left+=("$n"); }
    elif [ "$st" = FAIL ]; then echo "#$n FAILED: $(gh pr checks "$n" --json name,state --jq '[.[]|select(.state!="SUCCESS")|"\(.name)=\(.state)"]|join(",")')"
    elif [ "$m" = CONFLICTING ]; then echo "#$n CONFLICTING"
    else left+=("$n"); fi
  done
  pending=("${left[@]}"); [ ${#pending[@]} -eq 0 ] && { echo "all done"; exit 0; }
done
echo "timeout; still pending: ${pending[*]}"
```

## 7. Final report

- **Merged this session:** 24 PRs (§1), plus #208 if its loop finished.
- **Measured count:** 2026 collected on `2ab550a`; 2026 passed with 75.70% coverage.
- **Open owner gates:**
  - LCP-HL-DIFF, after #215 passes review.
  - DON-COPY, after #211 passes review.
  - O-6, at the 2026-10-24 freeze.
  - P6-ORPHAN, OW-3, OW-W0/W3/W7, E-6, and the deferred G-C2 and disabled F-8 (§3 item 5).
- **Cleanup:** merged-PR worktrees on the old machine (`git worktree list`; remove the clean, merged ones as on 2026-10-19).
