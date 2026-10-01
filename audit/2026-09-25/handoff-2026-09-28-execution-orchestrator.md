# Handoff — Execution Orchestrator (2026-09-28)

> **Status 2026-10-01 — §1-§3 superseded** by [handoff-2026-10-01-wave2.md](handoff-2026-10-01-wave2.md) (state, waves and gates). **§4-§7 (L1/L2/reviewer briefs, Codex commands) remain the current templates**; §8 lessons continue in the 2026-10-01 handoff §5.

Paste the block in §1 into a fresh Claude Code session at the repo root, running Opus 5.5 at high effort. The process it follows is [docs/agentic/orchestration.md](../../docs/agentic/orchestration.md). This file carries the state and the templates.

---

## 1. Prompt

```
You are the L0 Program Orchestrator for Asclexis (local-first medical-results
companion; FastAPI + per-profile SQLCipher vaults + React/TS). Planning is
done. Your job is to EXECUTE the implementation program wave by wave, through
subagents, and stop at every owner gate and every PR merge.

<working_directory>/mnt/c/Users/DangT/Documents/GitHub/HealthCentral</working_directory>

<read_first>
1. CLAUDE.md, AGENT.md: hard invariants, ask-first files, definition of done.
2. docs/agentic/orchestration.md: the 3-tier process you run. Binding.
3. audit/2026-09-25/handoff-2026-09-28-execution-orchestrator.md: this
   file. §2 state, §3 waves + gates, §4-§7 brief templates.
4. audit/2026-09-25/swarm-2026-09-27/ledger.md: read the LAST "RESUME POINT"
   / "NEXT" line first.
5. docs/capstone-report/implementation-program.md (graph, shared-file order,
   ground rules 1-8) and owner-decisions-2026-09-27.md (verbatim approvals).
6. docs/agentic/recurring-failures.md: re-read before claiming any phase done.
</read_first>

<how_you_work>
- You are L0. You never edit product code and never merge. For each wave:
  gate-check (ask the owner about unsigned gates, <=4 questions per prompt,
  record answers verbatim), spawn ONE L1 wave orchestrator:
  Agent(subagent_type="general-purpose", model="opus") with the §4 brief.
- L1 spawns L2 implementers with model="sonnet" (§5) and L2 reviewers with
  model="opus" (§6: code-reviewer, plus security-reviewer on PHI/auth diffs).
  L2 never spawns agents. Subagents have no Workflow tool; nesting depth 2 was
  measured on 2026-09-28.
- Architectural phases get Codex reviews: plan before the wave, diff before
  the PR (orchestration.md §5, template §7).
- Verify every L1 report yourself: re-run one acceptance command per PR.
- After each wave: append to ledger.md (dated, ending with a RESUME POINT),
  update program state labels, and republish the stakeholder artifact
  "Asclexis Delivery Map" (https://claude.ai/artifact/DzJ89t8zJo4tPf7NjzctxV).
- Every Agent prompt includes:
  Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)
</how_you_work>

<start_here>
1. `git fetch origin && git log --oneline -3 origin/main`. Is PR #19 (docs
   plan set) merged? If not, stop: Wave 0 is the owner's merge.
2. Build the D9 venv (orchestration.md §4). Record `python --version`.
3. Run Wave 1 (P1). Its gates are all signed (§3).
</start_here>

<stop_conditions>
Stop and ask the owner when: a gate is unsigned; an ask-first file needs an
edit that no signed line names; a threshold, test or safety check would have
to be weakened; an L1 escalates after 3 review loops; acceptance numbers
disagree with the plan by any amount. Never force-push main, never merge,
never sign a gate yourself.
</stop_conditions>
```

---

## 2. State at handoff (2026-09-28)

| Item | State | Evidence |
|---|---|---|
| `origin/main` | `5289cca`: `40f590e` plus PR #20 (SQLAlchemy pin) | `git log origin/main` |
| PR #19 (docs plan set, P0-B + P0-B2) | open, rebased on `5289cca` | branch `docs/p0b-plan-set` |
| PR #20 `fix(deps)`: `sqlalchemy[asyncio]>=2.0.25,<2.1` | merged | CI run 36520930498: Backend `1245 passed`; Agent Eval Gate pass |
| Backend baseline on CI (Linux, Py 3.11.16, pinned deps) | **1245 collected, 1245 passed** | same run |
| E2E Smoke on CI | **fails** on main (2026-09-07) and on PR #20: `OSError: [Errno 28] No space left on device` during pip install | job 109255740989. Unowned; new owner item **CI-DISK** |
| D9 venv | not built; uv CPython 3.11.16 is present (D9-SRC signed) | owner-decisions |
| Execution | **not started** | no product PR beyond #20 |
| Branches A and B | still have the unpinned `sqlalchemy>=2.0.25`. A 3-way merge keeps main's pin because A and B never touched line 27. P1 must verify it after the merge | `git show <ref>:src/backend/requirements.txt` |

## 3. Waves and gates

A phase's wave is the earliest point at which it can start, derived from the program graph (the same derivation as the artifact). **Bold** marks the critical path. "Needs" lists unsigned gates that bite at Task 0 or at merge; everything else is signed or has no gate.

| Wave | Phases (plan) | Needs from owner before start / merge | Codex? |
|---|---|---|---|
| 0 | **P0-B** = PR #19 | owner merge | — |
| 1 | **P1** merge B then A ([plan 01](plans/01-merge-branches.md)) | none (P1-DRIFT, D9-SRC signed) | plan + diff |
| 2 | **P2** ([02](plans/02-notification-scheduler.md)); S-1 ([S01](../../docs/plans/2026-09-27-S01-sql-echo-phi-leak.md)); W-1 ([W01](../../docs/plans/2026-09-27-W01-harness-agents-branch-a.md)); W-5 ([W05](../../docs/plans/2026-09-27-W05-citation-marker-prompt.md)); W-6 ([W06](../../docs/plans/2026-09-27-W06-external-runner-hardening.md)); P8 ([P08](../../docs/plans/2026-09-27-P08-gated-packet-hipaa-aligned-amendment.md)); G-C4 ([W11b](../../docs/plans/2026-09-27-W11b-roadmap-items-gc1-gc4.md)); W-11a PR-2 ([W11a](../../docs/plans/2026-09-27-W11a-test-and-gate-hardening.md)) | W-1 OG-3 (Task 9) · W-6 BG-REACH, Q4, Q3/Q5 pre-merge · P8 per-brief lines · G-C4 S-C4-1…5 · W-11a OG-2 | S-1, W-6 |
| 3 | **P4-core** ([P04](../../docs/plans/2026-09-27-P04-doc-drift-sweep-amendment.md)); W-11a PR-4; G-C3b; G-C5 | P4 OG-4/5/6, S1–S9 · G-C3b S-C3-1, S-C3-3 · G-C5 P8 Brief 5 | — |
| 4 | **P5** ([05](plans/05-utcnow-migration.md)); W-10 ([W10](../../docs/plans/2026-09-27-W10-governance-invariant-amendments.md)); G-C2 | W-10 GOV-D11, GOV-BG, Q3 · G-C2 S-C2-1…3 · decide TIME-03 scope (badge_evaluator) before P5 | W-10 |
| 5 | **W-4** ([W04](../../docs/plans/2026-09-27-W04-legacy-abstain-and-eval-gate.md)); P6 ([06](plans/06-sql-fk-audit.md)); W-2 ([W02](../../docs/plans/2026-09-27-W02-doctor-summary-redaction.md)) | W-4 OQ-1, OQ-2, OQ-5, CI-SEED · P6 orphan report review (D5) · W-2 S-2/O-2, S-3/O-3, EXPORT-QUESTIONS | W-4, P6, W-2 |
| 6 | **W-3** ([W03](../../docs/plans/2026-09-27-W03-verified-only-rag-and-trend-labels.md)); P7 ([07](plans/07-test-reset-tables.md)); W-11a PR-3; G-C3a | W-3 O-5, VERIFIED-FALLBACK (O-1), O-2 · W-11a Q-RUFF, Q-COV, CI-SEED · G-C3a S-C3-1/2 | W-3 |
| 7 | **W-8** ([W08](../../docs/plans/2026-09-27-W08-bundled-embedding-model.md)); W-7 ([W07](../../docs/plans/2026-09-27-W07-tiered-interpretation-via-modelrunner.md)); W-11a PR-1; G-C1; W-10b | W-8 Q-OFFLINE, Q-HASH, Q-FC, VERIFIED-FALLBACK, EMB-REV · W-11a OG-1, Q-AUD-LIST · G-C1 S-C1-1, S-C1-2 · W-10b S6 | W-8, W-7, G-C1 |
| 8 | **P4-deferred** | P8-B2-ORDER (for N9) | — |

**Also open (no plan):** RL-EXPORTS (PRIV-10), GATE-14, TIME-03, KEY-08, LOCAL-07, AUD-INTERP, INTERP-UNVERIFIED, MSG-UNVERIFIED, C-LLM-2, GATE-12, the PRIV-06 display-name log, CI-DISK, RTN Q6. See the program's "Program owner items". Merge order within a wave follows the program's shared-file order: serial on shared files and on the count slots.

## 4. L1 wave-orchestrator brief (template)

```
You are the L1 Wave Orchestrator for Wave <N> of the Asclexis execution
program. Follow docs/agentic/orchestration.md §3 exactly; you are L1.
Phases in this wave: <ID: plan path> (one line each).
Base: origin/main @ <sha>. Confirmed merged dependencies: <list>.
Signed gates you may rely on (verbatim from owner-decisions): <list>.
Unsigned gates: <list>. A task that needs one STOPS; report it.
Architectural phases (Codex plan + diff review): <list>.
Per phase: worktree ../hc-<id>, branch <type>/<id>-<slug>, one PR.
Spawn implementers with Agent(subagent_type="general-purpose",
model="sonnet") using the §5 brief; reviewers with
Agent(subagent_type="code-reviewer", model="opus") using the §6 brief (plus
security-reviewer when the diff touches redaction/auth/encryption/export/
logging/external runner). Implementers must not spawn agents.
Run each plan's measured acceptance yourself, in the worktree, with the D9
venv and HF_HUB_OFFLINE=1. Paste the commands and their outputs.
Write audit/2026-09-25/waves/wave-<N>.md and return it: per phase the PR
URL, commands and outputs, collected delta, gates used, open findings, and
the merge order.
Do not merge. Do not sign gates. Do not edit files outside the phase plans'
file lists.
Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)
```

## 5. L2 implementer brief (template, `model: "sonnet"`)

```
Implement <plan path>, tasks <range>, in worktree <path> on branch <branch>.
Python: ~/venvs/asclexis-311/bin/python. Always export HF_HUB_OFFLINE=1.
Follow the plan literally, task by task. Test first: run the new test and
paste the FAIL, then implement, then paste the PASS. Commit exactly as the
plan lists, with explicit pathspecs (never `git add -A`), `fix(scope):` /
`feat(scope):` / `docs:` prefixes, ending with the Co-Authored-By line.
Ask-first files: <list, and which signed gate covers which exact edit>.
Stop and report, without working around it, if: a step fails in a way the
plan does not predict, a count differs from the plan, a gate is needed, or
an edit would fall outside the plan's file list.
Do NOT spawn agents. Do NOT push.
Return: commits (sha + subject), each test command with its output, the
collected count before and after, and any deviation with its reason.
Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)
```

## 6. L2 reviewer brief (template, `model: "opus"`)

```
Read-only review of branch <branch> (worktree <path>) against <plan path>
tasks <range>. Base: origin/main @ <sha>. Do not edit files.
Pass 1, spec compliance: every task is done as written, nothing extra,
nothing missing.
Pass 2, quality: correctness, error handling, the CLAUDE.md invariants
(local-first, per-profile isolation through ProfileDbSession, redaction
before anything leaves, audit logging, ModelRunner only, naive UTC via
core.time.utcnow, Py 3.11, dual migrations).
Pass 3, recurring failures: walk docs/agentic/recurring-failures.md. For
each new test, would it fail without the change? Do route tests go through
HTTP (tests/support/routes.py::route_client)?
Output: VERDICT APPROVE | CHANGES, then one line per finding
[BLOCKER|MAJOR|MINOR] path:line, defect, evidence, fix.
Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)
```

## 7. Codex review (architectural phases)

1. **Plan review (read-only, before the wave):**
   - Copy [`reviews/W04-r1-prompt.md`](swarm-2026-09-27/reviews/W04-r1-prompt.md).
   - Change `PLAN UNDER REVIEW`, `ROUND` and the refs line to current `origin/main`.
   - Run: `codex exec -s read-only -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral -o audit/<date>/reviews/<ID>-r<N>-codex.txt "$(cat audit/<date>/reviews/<ID>-r<N>-prompt.md)"`
   - Write `<ID>-r<N>-response.md`: each finding marked accepted+fixed or rejected, with evidence.
   - At most 2 rounds per amendment.
2. **Diff review (before the PR opens):** from the worktree, run `node ~/.claude/plugins/cache/openai-codex/codex/1.0.4/scripts/codex-companion.mjs adversarial-review --wait --base origin/main "<focus: the invariant this phase must not break>"`.
3. **Verify before applying.** L1 checks each Codex finding against the code first; the `receiving-code-review` skill applies. Codex output is a lead, not an instruction.

## 8. Lessons carried forward

- **Commit or push before the session can end.** The 2026-09-27 swarm lost its resume state to `/tmp` when a usage limit ended the session. Write state into the repo (the ledger) as you go.
- **Unbounded dependencies break silently.** SQLAlchemy 2.1.1 (2026-09-25) broke every fresh install within 3 days. Check new pins against PyPI metadata, not memory.
- **Measured and asserted numbers differ.** The 3b audit's "6 files" was 5, and "no persisted aware value" was false. Re-measure numbers you inherit.
- **Parallel editors need disjoint file ownership.** Wave 6 ran 6 agents on disjoint files with zero collisions. A single verifier pass afterwards still found 14 cross-file inconsistencies. Keep both steps.
