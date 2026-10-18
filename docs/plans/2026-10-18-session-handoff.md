# Session handoff: 2026-10-17 → 2026-10-18 (L0, Opus 5.5)

**Last Updated:** 2026-10-18
**Owner:** repository owner
**Refresh Trigger:** the next L0 session reads this first, works the "Not started / next" list, and replaces this file with its own handoff.

Read this after [CLAUDE.md](../../CLAUDE.md), [AGENT.md](../../AGENT.md) and the [build-program RUNBOOK](2026-10-15-build-program/RUNBOOK.md). It replaces [the 2026-10-17 handoff](2026-10-17-session-handoff.md). Owner answers quoted here are recorded in [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md) (rows dated 2026-10-17 and 2026-10-18). Verify every fact below with `git`/`gh` before acting on it. This is a lead, not a finding.

## 1. What this session did

**State at close.** `origin/main` was `7d6774b` (E-3a, #142) when this handoff was written. Collected **1769** on that commit, full suite `1769 passed` (5 m 48 s, real embedding model), `ruff check .` clean, `from main import app` imports, `docs_lint.py` passes, `claude plugin validate` passes and `claude plugin test` gives 19 pass 0 fail on `.claude/mods/asclexis-rsi`. Count slots are written by the closing PR (1759 → 1769).

**Merged (all verified `MERGED` with `gh pr view`):**

| Area | PRs (merge sha) |
|---|---|
| Harness | #121 build-program (`269d410`), #126 rsi-loop (`5f46752`), #127 asclexis-rsi mod, Track 1 (`2ac361a`), #129 build-program runs rsi-loop last (`23c4bc1`), #144 reviewer agent type (`0440045`) |
| Plans, research, capstone | #122 RSI research (`2aea8cc`), #123 handoff 2026-10-17 (`7b209d4`), #125 capstone RSI section (`c2733b2`), #128 RSI app-track plans (`63caa9a`), #131 PARALLEL-WAVES (`b54f105`), #132 11 new rows planned (`b43576c`), #133 E-3a plan (`5386548`), #147 E-3a rulings (`de4808e`) |
| Queue items | D-4 #138, C-DUPAUD #141 (owner yes on `core/audit.py`), E-3 #143 (all but Task 7), B-8 #140, C-VAULTSC #139, C-BKUP #137, F-2 #135, W-3 #136, B-1 #134, C-GAM2B #146 (profile migration `014_streaks_hidden`), F-1 commit 1 #149, RSI-T2-EVAL #150 (`c0c80c6`), E-3a #142 (`7d6774b`) |
| Post-merge batches and owner rows | #124, #148, #151, #152 (`b6f1661`) |

**Goal items from the 2026-10-17 handoff.** (1) Post-merge batch: done (#124). (2) RSI mod Track 1: merged (#127). The general template is at `~/.claude/mods-templates/rsi-loop/` (not committed; validate passes, 10 pass 0 fail). Load the mod with `claude --plugin-dir .claude/mods/asclexis-rsi`. (3) `rsi-loop`: merged (#126, #129) but **never run**: no RSI logs existed before the mod loaded, so it needs a session started with the mod. (4) App track: planned (#128), RSI-T2-EVAL implemented and baseline measured (below). (5) Capstone section: merged (#125); the closing PR adds the Track-2 baseline. (6) F-8 routine: created, **disabled** (below). (7) `build-program` `{"max_waves":4,"auto_merge":true}` ran (85 agents, about 6.7 h); L0 also ran separate build-item workflows.

**Track-2 baseline (RSI-T2-EVAL, the LEGACY-CITE-PROMPT comparison point).** One run per model, n=20, ran alone on the model host, exit 0 in 11 m 7 s. Questions sha256 `ecb906035db228f1af9fc2d5698fe9bf9cf0e34bbd88296b5719a8a41c0d990e`. Source: PR #150 comment 6247765961; raw output `~/asclexis-evals/t2e-2e91ea2/`.

| Model | Abstained | Cited | Uncited | Escalated |
|---|---|---|---|---|
| `gemma4:e4b` | 19/20 | 0 | 0 | 1 |
| `llama3.1:8b` | 17/20 | 0 | 0 | 3 |
| `qwen3:8b` | 15/20 | 1 | 4 | 0 |
| `gemma3:12b` | 20/20 | 0 | 0 | 0 |

**F-8 nightly doc-drift routine.** Routine `trig_01FemPFiWdzSq6PuhSSQNodV` (https://claude.ai/code/routines/trig_01FemPFiWdzSq6PuhSSQNodV), cron `0 7 * * *`, `claude-sonnet-5`, tools Bash/Read/Glob/Grep, connectors cleared (the server auto-attached 5; L0 removed them), prompt = spec section 8 verbatim. **Disabled**, per RTN-Q6 "do not enable": the section 6.2 probe showed `git push --dry-run` rc=0 (the session can push; the `gh` token is invalid, rc=1), and `allowed_tools` did not restrict Write or PushNotification (the smoke run wrote a scratch file in `/tmp` and sent a mobile push). Smoke run `cse_01MggpnD8piK6FeSThRnSSBb`: C1-C4 pass, C5 1721 collected, C6 132 routes matching `docs/api/endpoints.md`, C7 zero `utcnow` drift (capstone docs still say 101/30), C9 clean; audit found no `git push`, commit or `gh` calls and no new remote refs. Enabling needs an owner decision (section 3).

**Owner answers recorded.**
- 2026-10-17: RSI-TEMPLATE-LOC, OWNER-PR-MERGE, FULL-QUEUE-MERGE ("You have full authorization to continue running, merging after tests pass & CI passes, to finish everything in queue.md"), PARALLEL-WAVES, PYSLOTS-6, Q-RUFF-SET (configured F/I/W), Q-RUFF-UNSAFE (safe only), Q-RUFF-PIN (0.17.1), C-DUPAUD-DIFF.
- 2026-10-18 (#152): E1B-SCOPE (b), REDOS-APPROACH (a), LHH-SCOPE (a, folds into W-8), IAW-WORDING (b), MSG-SCOPE (a), CFR-FORMAT (a), IR-FOOTER (a), P4D-PIPELINES-127 (fix both lines).

**Harness defects found.**

| # | Defect | Status |
|---|---|---|
| 1 | build-item reviewer `agentType` `code-reviewer`/`security-reviewer` not installed | **Fixed** (#144, general-purpose) |
| 2 | build-item implementer may not run the full suite, but some plans need full-suite measurements (E-3 Tasks 5 and 10): dead end | **Not fixed.** Fix: route plan measurement steps to the Haiku runner |
| 3 | Nested `workflow('build-item')` inside build-program shares a small agent cap (about 4 concurrent): 4 of 10 eligible items ran | **Not fixed.** Workaround: L0 starts separate background build-item workflows. Fix candidate: build-program starts items as top-level runs, or documents the cap |
| 4 | Auto-mode classifier blocks `gh pr merge` from subagents ("Merge Without Review"), so `auto_merge` cannot merge | **Not fixed.** L0 merges with a merge-on-green loop. The owner could add a Bash permission rule |
| 5 | build-item has no resume path for its own blocked claim | **Not fixed.** Workaround: close the `[blocked]` PR (keep the branch) and restart, or resume the run with `resumeFromRunId` after patching the session script copy |
| 6 | Row file lists omitted test files the change legitimately must update (W-3, B-1, C-GAM2B) | **Not fixed.** L1 ruled each time; the planner should list tests that pin changed behaviour |
| 7 | `PYSLOTS=6` set in `.claude/settings.local.json` env (owner PYSLOTS-6) | Done; likely applies only to new sessions |
| 8 | L0 queue-row text said `ruff format`, which would have edited ask-first files | **Fixed** (#147); recorded as recurring-failures #11 |

**Reviewer follow-ups noted (not rows unless stated).** B-1: page-level test for refetch error with cached `redaction_break_glass:true`. W-3: HC-VER-002 fake DB returns all rows; TrendsDashboard tooltip untested. C-GAM2B: query key lacks `profileId`; `PATCH {}` audits `changed_fields`. C-VAULTSC: docstring paths; test 008 has no decrypt positive control; 007 canary only in `vault.db`. B-8: `test_extraction_golden.py:106` run-log check should match `parser_version`. E-3a review: `api/notifications.py` routes have no audit (now row AUDIT-NOTIF-ALL), `tests/test_rl_feedback.py:687` has a hollow `or True` isolation check. D-4: test `uuid4` at import, expected value computed with the same call.

## 2. Not started / next (priority order, parallel where independent)

1. **Ready rows.** Run `build-wave` to confirm, then one background `build-item` workflow per id (at most 2 at once per the skill). Per the facts at close: E-1b and REDACT-EMAIL-REDOS (edit allowed, merge needs the owner's yes on the diff; never pair them), MED-STREAK-GRACE, INTERP-ADVICE-WORDING, CHAT-FACT-ROUTING, INTERP-RENDER (includes the footer), EXTRACT-FORMATS, DEV-SH-CC, AUDIT-MISSING-MED, EXPORT-TODAY-TZ (never pair with E-1b), F-1 commit 2, E-3-T7 (E-3a merged), W-8 (now includes LOCAL-HF-HUB), G-C5-PLAN (waits on W-8), F-5/F-6/F-13 on their triggers. Unplanned rows AUDIT-NOTIF-ALL and EXPORT-COLLECTED-TZ need a planner pass first.
2. **Harness fixes #2, #3, #5** (defects table). #2 and #3 stop whole items from running; do them before the next large `build-program` run.
3. **Run `rsi-loop` once**, in a session started with `--plugin-dir .claude/mods/asclexis-rsi` so logs exist. Leave its PRs for the owner (RSI promotions are never agent-merged).
4. **LEGACY-CITE-PROMPT** now that the baseline exists (RSI-T2-EVAL merged, numbers above). Never beside W-3, W-8, G-C5 or B-3 (`modules/rag.py`). Its merge rule needs the owner's LCP-ACCEPT.
5. **Cleanup of stale worktrees** (section 4).

## 3. Still waiting on the owner

| Item | What the owner does | Unblocks |
|---|---|---|
| P6-ORPHAN | Run `scripts/fk_orphan_audit.py --profile <id> --source <copy of real backup>` locally and paste the counts | C-P6 Tasks 2-5 → C-P7 → E-2, C-GC1 |
| OW-3 | Write sealed set S5 outside every worktree; commit only sha256 + counts | B-4, MM-2, B-3 merge, B-5 |
| Codex review of section B-3 (R-22) | Run or approve it | B-3 merge |
| P8 Brief 2 | Sign it | F-4 |
| SHOW-DATE | Give the showcase date (freeze = date − 7) | F-9 |
| G-C2 | Say when to un-defer the OpenWiki run | F-7 |
| OW-W0, OW-W3, OW-W6 to OW-W13 | Answer the wearables gates | F-12 and all WEAR code waves |
| 13 DON-* gates, LCP-ACCEPT, LCP-HEADERLESS (from #128) | Answer them | RSI1-DONATE; LEGACY-CITE-PROMPT merge rule |
| E1B-DIFF, REDOS-DIFF | Say yes on the `modules/redaction.py` diffs once an agent writes them | E-1b, REDACT-EMAIL-REDOS merge |
| F-8 enable decision | Accept a prompt-only read-only routine, or provide a no-push environment | Enabling `trig_01FemPFiWdzSq6PuhSSQNodV` |
| Q-COV | Pick the coverage threshold (report-only for now; local 74%) | E-3 threshold step |
| EXF-SAMPLE (optional) | Provide a real column-layout lab PDF sample | Improves EXTRACT-FORMATS; never blocks |
| EXPORT-COLLECTED-TZ display ruling | Say which timezone the doctor summary prints | EXPORT-COLLECTED-TZ planning |

## 4. Gotchas

- **Merges.** The auto-mode classifier blocks `gh pr merge` from subagents. L0 merges, with a merge-on-green loop (poll `gh pr checks`, then `gh pr merge`). FULL-QUEUE-MERGE lets L0 merge green, review-PASS PRs. Ask-first diffs and every RSI promotion still need the owner.
- **Agent caps.** Nested `workflow('build-item')` inside `build-program` shares a cap of about 4 concurrent agents; start eligible items as separate background `build-item` workflows instead.
- **Blocked nested item.** Resume with a patched copy of the session script plus `resumeFromRunId`, or close the `[blocked]` PR (branch kept) and restart the item.
- **Named-workflow registry** (`build-program`, `build-item`, `rsi-loop`) loads at session start. For a workflow merged mid-session, pass `scriptPath`.
- **Model host.** This box is the model host (RTX 3080, Ollama on localhost, `~/venvs/asclexis-311`). Do not run pytest during model runs: the 60 s generation timeout inflates abstain counts.
- **Never run `ruff format`.** It rewrites ask-first files and merged migrations. Use `ruff check --fix` safe fixes only (recurring-failures #11).
- **`docs/INDEX.md` and `docs/_link_graph.json`** conflict on nearly every sync: regenerate with `scripts/generate_docs_index.py`, never hand-merge, and merge soon after green.
- Stop dev servers by port (`lsof -ti:PORT -sTCP:LISTEN | xargs kill`); `pkill -f` can kill the agent's own shell. Playwright needs `executablePath` set to the cached chromium. Venv husk files can exit 0 without running anything: re-link after every checkout or merge.
- **Stale worktrees** (all branches' PRs merged; not removed here, cleanup for the owner or the next L0 with `git worktree remove` and `git branch -d`): `hc-b-1`, `hc-b-8`, `hc-bi-reviewer`, `hc-bp-rsi`, `hc-build-program`, `hc-c-bkup`, `hc-c-dupaud`, `hc-c-gam2b`, `hc-c-vaultsc`, `hc-capstone-rsi`, `hc-d-4`, `hc-e-3`, `hc-e-3a-r2`, `hc-e3a-plan`, `hc-e3a-ruling`, `hc-f-1`, `hc-f-2`, `hc-handoff`, `hc-owner-1018`, `hc-plan-new-rows`, `hc-pmb-1017d`, `hc-pmb-1017e`, `hc-queue-parallel`, `hc-rsi-app-plans`, `hc-rsi-loop`, `hc-rsi-mod`, `hc-rsi-research`, `hc-rsi-t2-eval`, `hc-w-3`. Also `hc-e-3a` (PR #130 closed, superseded by #142; branch kept), `hc68-sync` (`sync/68`, contained in main) and `hc-close-1018` (this PR, remove after merge). All sit beside the main checkout under `/mnt/e/Programming/Github Repo/`.

## 5. The /goal prompt

Paste this to start the next L0 (Opus 5.5):

```
/goal Resume the Asclexis build program from docs/plans/2026-10-18-session-handoff.md and drive docs/plans/2026-10-15-build-program/queue.md to done.

READ FIRST: CLAUDE.md, AGENT.md, docs/plans/2026-10-18-session-handoff.md, docs/plans/2026-10-15-build-program/RUNBOOK.md, queue.md, contracts.md section d, docs/agentic/recurring-failures.md, and the 2026-10-17 and 2026-10-18 rows of docs/capstone-report/owner-decisions-2026-09-27.md. Treat the handoff as leads: verify every PR number, state and sha with `gh pr view N --json state,mergeCommit` before relying on it.

DO (parallel where independent; dynamic workflow; Opus sub-orchestrators, Sonnet implementation, Haiku tests and search):
1. Audit main: `git fetch origin`, open PRs, CI on the latest main commit, collected count with the pyslot recipe (contracts.md section d), `ruff check .` clean.
2. Run build-wave, then start each eligible queue item as its own background build-item workflow (not nested inside build-program: nested items share a small agent cap). Run as many at once as the queue slot cap allows (12, queue rule 1; PARALLEL-WAVES). Use scriptPath for any workflow merged after session start.
3. Fix harness defects #2 (route full-suite plan steps to the Haiku runner), #3 (build-program starts items top-level or documents the cap) and #5 (build-item resume of a blocked claim) from the handoff.
4. Have a planner pass plan AUDIT-NOTIF-ALL and EXPORT-COLLECTED-TZ.
5. Start the session with `--plugin-dir .claude/mods/asclexis-rsi`, run rsi-loop once, and leave its PRs for the owner.
6. Run LEGACY-CITE-PROMPT against the Track-2 baseline in the handoff (PR #150 comment 6247765961).
7. L0 merges green, review-PASS PRs under FULL-QUEUE-MERGE with a merge-on-green loop (subagent merges are blocked by the classifier). Do a post-merge docs batch after each group of merges (SLOT-RULE-2).

RULES: Owner gates are never inferred; if a gate is unanswered the row stays blocked. Paste the command output for every claim; "tests pass" without output is not a result. E-1b and REDACT-EMAIL-REDOS diffs need the owner's explicit yes before merge, and never run them together. Ask first before touching modules/interpret_safety.py, modules/redaction.py, modules/faithfulness.py, modules/verifier_agent.py or anything auth or encryption. RSI promotions are never agent-merged. Never run `ruff format`. Never lower a test threshold or weaken a safety check. Do not run pytest while a model run is in progress. The F-8 routine stays disabled until the owner decides.

DONE WHEN: every queue row that is not owner-blocked is merged with green CI (or has an open PR with a documented stop reason); rsi-loop has run once and its PRs are left for the owner; a new docs/plans/YYYY-MM-DD-session-handoff.md replaces this handoff (with a "Superseded by" line added to this one) and ends with a final report of merged PRs, measured count, open owner gates and cleanup list.
```
