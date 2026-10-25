# Session handoff: 2026-10-20 cloud session → local machine (L0)

> **Historical Reference** — superseded by `docs/plans/2026-10-20c-session-handoff.md` and its successors; retained for history, not an active tracker. Moved from `docs/plans/2026-10-20b-session-handoff.md` on 2026-10-22.

**Last Updated:** 2026-10-20
**Owner:** repository owner
**Refresh Trigger:** the next L0 session reads this first, works §3, and replaces this file with its own handoff.
**Superseded by:** [2026-10-20 local-session handoff](../../plans/2026-10-20c-session-handoff.md).

Read this after [CLAUDE.md](../../../CLAUDE.md), [AGENT.md](../../../AGENT.md) and the [build-program RUNBOOK](../../plans/2026-10-15-build-program/RUNBOOK.md). It replaces [the 2026-10-20 handoff](2026-10-20-session-handoff.md). This session ran in a Claude Code cloud container; the owner moved development back to a local machine ("When all current processes are done, can you commit all works/merge into main. Then provide a handoff prompt"). Every PR below was merged with green CI and a final review PASS; ask-first and merge-gated diffs only after the owner's yes. Treat this file as a lead: verify with `gh pr view` / `git log origin/main` before acting.

## 1. What this session did

**Merged (16):** #208 LLM-PATH-LOG, #217 (2026-10-20 handoff), #218 #221 #223 #226 (build-item harness fixes), #219 #224 #225 #228 (owner rows), #220 (`pyslot.sh` exec bit), #222 (11 follow-up rows planned), #215 LCP-HEADERLESS, #211 RSI1-DONATE PR-1, #229 (RRSI / harness2 research), #227 G-C5, plus this batch PR.

- **Queue items done:** LLM-PATH-LOG, LCP-HEADERLESS, RSI1-DONATE PR-1, G-C5 (flag-off build; real-model steps pending, §3), planner pass on all unplanned follow-up bullets.
- **F-9 (#210):** Task 8 done (O-4 = B packaged; `review.sh` and the prompt template were on the old machine and are listed as missing, not invented). Stays **draft** until the 2026-10-24 freeze.
- **rsi-loop:** ran once (`run_id 2026-10-20-cloud`): 1767 tool calls mined, Bash failure rate 1.49%, one candidate, **PR #230** (hint rule `embedding-bundle-missing`). Left open for the owner (RSI promotions are never agent-merged).

**Count:** **2091 collected** on `cb6660d` (sentence-transformers installed; see COUNT-ENV-VARIES in queue.md). Full suite on `cb6660d`: see the batch PR body (only the 5 CLAUDE.md §4 embedding tests fail, environmental: the bundle could not be fetched in the cloud container). App import OK, 110 OpenAPI paths.

**Owner answers this session** (all rows in `docs/capstone-report/owner-decisions-2026-09-27.md`):
- **CODEX-UNAVAIL:** with no Codex CLI, a separate Opus adversarial reviewer with the same RUNBOOK §10.2 prompt substitutes, disclosed in the PR body. On a machine with Codex, use Codex again.
- **REDACT-NG-SCOPE (a):** hyphen/accent name redaction may be built on a draft PR; merge needs REDACT-NG-DIFF.
- **LCP-HL-DIFF:** yes, merged #215. Known gap kept per LCP-HL-SCOPE (a): a false value inside an UNCERTAINTY section after verified facts is served → row UNCERTAINTY-VERIFY.
- **DON-COPY-R1 / DON-STALE / DON-COPY-R2:** consent copy revised, stale-version consent fixed in PR-1, final copy approved as `2026-10-20-v2` and pinned by HC-DON-FE-010.

**L0 rulings this session** (on the PRs): #215 header-form regex in scope, `filter_unverifiable_claims` meta-pattern exemption no longer applies to claims with `[cite:N]` or a digit; #227 `/src/backend/models/nli/` added to `.gitignore`; #222 WAVE-DEP-DONE advisory only, GRADE-PATTERN-REDOS gets merge gate GRADE-REDOS-DIFF.

## 2. In flight at handoff

| PR | Item | State | Next step |
|---|---|---|---|
| #210 | F-9 showcase | draft, Task 8 done, review PASS | On or after **2026-10-24** ask the owner **O-6** (claim freeze), run Task 10 Steps 2-3, then ready and merge. Task 9 / O-3 are the owner's (Windows demo machine). |
| #230 | RSI candidate | open, never agent-merged | Owner reviews and merges or closes. |

No other open PR. No `[claim:` slot is held.

## 3. Next (dynamic workflow: build-wave, then one top-level `build-item` per id)

Every row in items 1-2 carries a dated stop in queue.md (owner MOVE-LOCAL, 2026-10-20: "Stop; continue locally"): not started in the cloud session. The stop ends when the next L0 starts the row.

1. **Ready rows (planned in #222, plus unblocked rows):** WAVE-DEP-DONE (harness), PYSLOT-MODE, F-4-FOLLOWUPS, GATE12-MINORS, PKT-Q-MINORS, REDACT-NAME-PINS, EMB-LOG-M7, LLM-PATH-LOG-M2M3 (never beside B-5), MSET-EXT-AUDIT-CT, AUDIT-GUARD-MINORS (#211 released `test_audit_order_guard.py`), RSI1-DONATE PR-2 (file list per the plan delta in #222; adversarial MINORs 4-9 from #211 noted in queue.md).
2. **Build on draft, merge gated:** GRADE-PATTERN-REDOS (GRADE-REDOS-DIFF), REDACT-NAME-GAPS after REDACT-NAME-PINS merges (REDACT-NG-DIFF; never beside another `redaction.py` row).
3. **G-C5 real-model steps:** on a machine that can reach huggingface.co, fetch the NLI model once (`download_models.py`, Q5b) and run the plan's real-model measurements; the flag stays default-off.
4. **Plan the new bullets** in queue.md "New rows found while planning": UNCERTAINTY-VERIFY, HARNESS-VITEST-HINT, REDACT-NG-LABEL, COUNT-ENV-VARIES (governance wording, owner), RSI1-DONATE-PR2 notes.
5. **Owner-blocked:** O-6 (2026-10-24); P6-ORPHAN (biggest unblock: C-P6 Tasks 2-5 → C-P7 → E-2, C-GC1, RSI1 reset tuple); OW-3 (S5 sealed set, after a B-3 draft); OW-W0/W3/W7; E-6 (interactive `/agents`); GRADE-REDOS-DIFF; REDACT-NG-DIFF; the **27 RRSI questions** OQ-1..OQ-27 in [docs/research/2026-10-20-rrsi-harness2/04-owner-questions.md](../../research/2026-10-20-rrsi-harness2/04-owner-questions.md) (none answered; OQ-25 may require a v3 consent copy and a new DON-COPY yes); #230. G-C2 stays deferred; F-8 stays disabled.
6. **Post-merge batch** after each merge group (SLOT-RULE-2).
7. **RSI:** start the session with `--plugin-dir .claude/mods/asclexis-rsi` so Track-1 logs are recorded, and run `rsi-loop` once after the day's run.

## 4. Harness defects and gotchas (new this session)

Fixed and merged: build-item explore reads `queue.md` only via `git show origin/main:` and maps cells by each table's own header (#218, #226); protected-file checks run three-dot plus `git diff HEAD` (#218); Task 0 installs the embedding bundle (#218); `l0_note` reaches every post-claim agent (#218); the implementer returns done when only review/verify steps remain, but keeps before/after proof tasks (#221); Verify uses the CODEX-UNAVAIL substitute (#221); the runner exempts exactly the 5 §4 embedding tests and only when the bundle is absent, and runs backend scripts with the venv (#223); `scripts/pyslot.sh` is executable (#220).

Still open / environment notes:
- **An `l0_note` that says "commit nothing new" also stops review-fix rounds** (seen on #215). Scope such notes to the first implement call ("unless review findings later need fixes").
- **A released draft cannot be resumed** (F-9): build-item resume needs a `[blocked:claude]` title plus an `L0 ruling:` comment. L0 retitles first.
- **Cloud container specifics** (not needed locally): GraphQL `gh pr *` is blocked there (REST only); huggingface.co and download.pytorch.org were denied by the network policy (torch came from PyPI); no Codex CLI. `/tmp/claude-1000/merge_par.sh` was rewritten on REST; the §6 GraphQL version from the 2026-10-20 handoff works on the local machine.
- **The collected count varies by environment** (COUNT-ENV-VARIES): 2 tests appear only with sentence-transformers installed. Compare counts measured in the same environment.
- Unchanged from earlier handoffs: no pytest during model runs (hold all three pyslot locks); never `ruff format`; build-wave can misread multi-task depends_on chains (WAVE-DEP-DONE plans an advisory check).

## 5. /goal prompt for the next L0 (local machine)

```
/goal Resume the Asclexis build program from docs/plans/2026-10-20b-session-handoff.md on this machine. Setup first: git fetch and fast-forward main in the main checkout (stale-checkout pitfall); confirm ~/venvs/asclexis-311 has src/backend requirements; make sure the embedding bundle exists (~/asclexis-models/embeddings/all-MiniLM-L6-v2, else cd src/backend && python scripts/download_models.py embedding) and copy it into every worktree you create; recreate /tmp/claude-1000/merge_par.sh from the 2026-10-20 handoff §6 if missing; measure the collected count in this environment (2091 on cb6660d with sentence-transformers) and the app import. Start the session with --plugin-dir .claude/mods/asclexis-rsi. Then: run build-wave and start each eligible row as its own top-level build-item workflow (dynamic workflow; Opus L1, Sonnet implement, Haiku tests), beginning with the §3 item 1 ready rows; build GRADE-PATTERN-REDOS and REDACT-NAME-GAPS on drafts and ask the owner GRADE-REDOS-DIFF / REDACT-NG-DIFF with the exact diffs; run the planner on the new queue bullets; if huggingface.co is reachable, run the G-C5 real-model steps. On or after 2026-10-24 ask the owner O-6 for #210, then finish F-9. Ask the owner the 27 RRSI questions (docs/research/2026-10-20-rrsi-harness2/04-owner-questions.md) in batches of 4 with the research's recommendation first, and record each answer as an owner-decisions row. L0 merges green review-PASS PRs with merge_par.sh and runs a post-merge batch after each group; RSI PRs (#230 and new ones) are never agent-merged. Rules as in CLAUDE.md and the 2026-10-18 handoff §5: owner gates never inferred; ask-first diffs need the owner's yes; never ruff format; no pytest during model runs (hold the pyslot locks); three-dot diffs only. Done when every non-owner-blocked row is merged or has a documented stop, a new handoff replaces this one, and rsi-loop has run once after the full-day run.
```

## 6. Final report

- **Merged:** 16 PRs this session (§1) plus this batch.
- **Measured count:** 2091 collected on `cb6660d`; full-suite result in the batch PR body.
- **Open owner gates:** O-6 (2026-10-24), P6-ORPHAN, OW-3, OW-W0/W3/W7, E-6, GRADE-REDOS-DIFF, REDACT-NG-DIFF, RRSI OQ-1..27, COUNT-ENV-VARIES, #230; G-C2 deferred, F-8 disabled.
- **Cleanup:** the cloud container's worktrees go away with it; nothing local to clean. On the local machine, remove merged-PR worktrees from earlier sessions (`git worktree list`).
