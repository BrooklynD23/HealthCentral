# Handoff — L0 Orchestrator, Wave 1 close + Wave 2 (2026-10-01)

Paste §1 into a fresh Claude Code session at the repo root (Opus 5.5, high effort). Process: [docs/agentic/orchestration.md](../../docs/agentic/orchestration.md). Templates (L1/L2 briefs, Codex): [handoff-2026-09-28 §4-§7](handoff-2026-09-28-execution-orchestrator.md).

## 1. Prompt

```
You are the L0 Program Orchestrator for Asclexis (HealthCentral repo). Wave 1
is merged. Your job: (A) close Wave 1's documentation, (B) run Wave 2's phases
IN PARALLEL through several L1 orchestrators, merges serial. Stop at every
owner gate and every PR merge.

<working_directory>/mnt/c/Users/DangT/Documents/GitHub/HealthCentral</working_directory>

<read_first>
1. CLAUDE.md, AGENT.md; docs/agentic/orchestration.md; docs/agentic/recurring-failures.md
2. audit/2026-09-25/handoff-2026-10-01-wave2.md (this file): §2 state, §3 docs to update,
   §4 Wave 2 plan, §5 lessons
3. audit/2026-09-25/swarm-2026-09-27/ledger.md: the LAST RESUME POINT
4. audit/2026-09-25/waves/wave-1.md; audit/2026-09-25/handoff-2026-09-28-execution-orchestrator.md §4-§7
5. docs/capstone-report/implementation-program.md (shared-file order :135-160, owner items,
   program gates) and owner-decisions-2026-09-27.md (verbatim scope)
</read_first>

<roles>L0 = you (Opus): never edit product code, never merge, never sign a gate.
L1 = Agent(general-purpose, opus), L2 implementers = Agent(general-purpose, sonnet),
reviewers = Agent(code-reviewer, opus) + security-reviewer on PHI/auth/export/logging
diffs. Every Agent prompt includes:
Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)</roles>

<start_here>
1. Is PR #26 (docs: Wave 1 records) merged? If not, ask the owner to merge it.
2. Do §3 (Wave 1 close) — one docs branch, one PR.
3. Do §4 (Wave 2) — dispatch the L1 groups in parallel, background.
</start_here>
```

## 2. State at handoff (2026-10-01)

| Item | State | Evidence |
|---|---|---|
| `origin/main` | `ee7c358` (PR #24 merged 2026-10-01T15:54:14Z) | `git log origin/main` |
| Wave 0 | done: PR #19 | ledger |
| Wave 1 | **all PRs merged:** #21 (branch B), #22 (docs), #23 (S-CACHE: cache key per profile + memory audit `category` dropped), #25 (CI-DISK: CPU torch in 3 CI test jobs), #24 (branch A + CAREQ HTTP test) | ledger "Wave 1 merged — handoff" |
| Collected backend count | **1296** (slots `CLAUDE.md:30`, `AGENT.md:76`) | PR #24 head `31574fb`: `1296 tests collected`, `1296 passed` |
| Main CI | `19f85b0`: all 6 jobs success incl. E2E (28 specs: 25 pass, 3 skip). `ee7c358`: was in progress | `gh run list --branch main` |
| D9 venv | `~/venvs/asclexis-311/bin/python` = 3.11.16, no pip module (use `uv pip install -p …`) | ledger 2026-09-29 |
| Open docs PR | **#26** `docs/exec-wave1-ledger-2`: ledger, wave-1 report, gates, owner items, this file | `gh pr view 26` |
| Worktrees left | `../hc-baseline`, `../hc-l0-verify`, `../hc-l0-docs`, `../hc-p1-b`, `../hc-s-cache`, `../hc-p1-a`, `../hc-ci-disk` | `git worktree list`; remove after Wave 1 close (they hold no unique work: all branches are merged) |

## 3. Wave 1 close — documentation to update (one docs branch, one PR)

1. **P1 post-merge checks (not run yet).** Spawn one L1 (or run read-only yourself in a detached worktree `../hc-p1-post` of `origin/main`): plan 01 [`audit/2026-09-25/plans/01-merge-branches.md`](plans/01-merge-branches.md) Task 7 Steps 1-3 + Task 8 Steps 1-4, venv + `HF_HUB_OFFLINE=1`. Expect `1296` collected in both slots, security-gate poison proofs exit 2/2/0, `harness_drift_check.py` exit 0, `RecoveryCodeCard.test.tsx` green on Windows (`powershell.exe -NoProfile -Command "cd C:\Users\DangT\Documents\GitHub\hc-p1-post\src\frontend; npm ci; npx vitest run src/__tests__/RecoveryCodeCard.test.tsx"`).
2. **Plan 01 Task 8 Step 5:** dated Session Note in `docs/features/TASK_LIST.md` (newest first): PRs #21/#24 (P1), #23 (S-CACHE), #25 (CI-DISK); measured 1296; poison proof result; `POST /export/questions` unredacted quote + SQL-FK-001 pragma still open. `git add docs/features/TASK_LIST.md`.
3. **Program state labels** in `docs/capstone-report/implementation-program.md`: P0-B (`:195` still says "not yet executed") → done (#19); P1 → done (#21, #24); add S-CACHE (#23) and CI-DISK (#25) as done; critical path line `:133`.
4. **Specs-compliance matrix** `docs/capstone-report/specs-compliance-matrix.md`: update every row that P1, S-CACHE, CI-DISK change (at least: per-profile isolation of the agent cache, memory audit logging, security-gate fail-closed, CARE-QUOTE-001, recovery-code UI, E2E in CI), each with PR + evidence; then **recount the scorecard by script** (do not hand-count).
5. **Delivery Map artifact** https://claude.ai/artifact/DzJ89t8zJo4tPf7NjzctxV: read it, mark Waves 0-1 done with PR links, republish to the same URL.
6. Run `python3 scripts/docs_lint.py`, `generate_docs_index.py --check` (regenerate if stale), `harness_drift_check.py`; ledger section ending in a RESUME POINT; commit with explicit pathspecs; open the PR.

## 4. Wave 2 — run in parallel (owner direction 2026-10-01)

**Rule:** implementation runs in parallel; **merges are serial**. Every phase changes the collected-count slots (SLOT-RULE) and most regenerate `docs/INDEX.md`, so each PR after the first merges `origin/main` into its branch, re-measures, and rewrites the slots before the owner merges it. Each phase: own worktree `../hc-<id>`, own branch, own PR, START = measured on the then-current main.

### 4.1 Phases, gates, files

| Phase | Plan | Gates (signed = may rely on, verbatim in owner-decisions) | Still owner-gated | Codex | Main files |
|---|---|---|---|---|---|
| **S-1** | [S01](../../docs/plans/2026-09-27-S01-sql-echo-phi-leak.md) | SQL-ECHO (S1-A + S1-B), SLOT-RULE, D9-SRC | — | plan + diff | `core/config.py`, `config/.env.example`, `core/database.py`, `core/profile_database.py` (1 line, ask-first, licensed) |
| **P2** | [02](plans/02-notification-scheduler.md) | D6 (auth hooks), audit §21 Q1 | — | — | `main.py`, `core/auth.py` (D6 only), scheduler module |
| **W-1** | [W01](../../docs/plans/2026-09-27-W01-harness-agents-branch-a.md) | D1, D1-scope, P1-DRIFT, **OG-3 (Task 9 runs)** | OG-1, OG-2, OG-4, OG-5 (optional; skip if unsigned) | — | `.claude/agents/*`, `.gitignore`, harness docs, `test_claude_agent_definitions.py` |
| **W-5** | [W05](../../docs/plans/2026-09-27-W05-citation-marker-prompt.md) | D11 | GOV-D11 is for W-10, not W-5 | — | `modules/rag.py` |
| **W-6** | [W06](../../docs/plans/2026-09-27-W06-external-runner-hardening.md) | D12, **W6-Q4 (Covered)**, **BG-REACH (keep current meaning)**, SLOT-RULE | **Q3, Q5 before merge** (warning placement + copy); GOV-BG lives in W-10 | plan + diff | `core/external_runner.py`, `api/model_settings.py`, `tests/test_redaction.py`, Settings card |
| **W-11a PR-2** | [W11a](../../docs/plans/2026-09-27-W11a-test-and-gate-hardening.md) Task 3 | **OG-2 (approved)** | — | — | `tests/security/test_vault_ciphertext.py` |
| **P8** | [P08](../../docs/plans/2026-09-27-P08-gated-packet-hipaa-aligned-amendment.md) | D10 | per-brief sign-off lines are signed **in the packet after the PR**; P8-B2-ORDER | — | `audit/2026-09-25/gated-items-decision-packet.md` (docs only) |
| **G-C4** | [W11b](../../docs/plans/2026-09-27-W11b-roadmap-items-gc1-gc4.md) G-C4 tasks | — | S-C4-1…5 signed **in the decision record after the PR** (S-C4-5 = EMB-REV) | — | packaging decision record; `feature_list.json` only after S-C4-1 |

Check each plan's Task 0 and its "Dependencies" section on the current tree before dispatch; plan line refs date from `40f590e`/`7b2ff1f` and must be re-verified (each plan's Refresh Trigger). W-6's program row lists *W-10* in italics (preferred, not hard); confirm with the owner only if W-6's Task 0 says it needs W-10 first.

### 4.2 Suggested L1 groups (disjoint files, so they can run at once)

| L1 | Phases | Why grouped |
|---|---|---|
| L1-A (security, architectural) | S-1, then P2 | Program order "S-1 before P2"; S-1 is a PHI leak (SQL echo); both need Codex (S-1) |
| L1-B (PHI boundary, architectural) | W-6 | Large plan; Codex plan + diff; Q3/Q5 asked before its merge |
| L1-C (tests/harness) | W-1 (incl. Task 9), W-11a PR-2, W-5 | Small, disjoint files |
| L1-D (docs → owner) | P8, G-C4 | Docs-only decision artifacts; no Codex |

Each L1 gets the handoff-2026-09-28 §4 brief plus: its phases, base sha, the signed gates **copied verbatim**, the unsigned gates (= STOP), Codex yes/no, worktree names, and "report each PR to main via SendMessage; poll until merged ≤3 h; do not merge". Run all four in the background in one message.

### 4.3 Merge order (L0 hands PRs to the owner one at a time)

1. **S-1** (PHI in logs; owns `core/config.py`/`database.py` before P4/P6)
2. **W-6** (PHI to external runner)
3. **W-11a PR-2**, **W-5**, **W-1** (any order; each re-measures slots)
4. **P2** (after S-1)
5. **P8**, **G-C4** (docs; then the owner signs their decision lines)

Before handing each PR over: re-run one acceptance command yourself in `../hc-l0-verify` (detached at the PR head), check the diff equals the plan's file list, check the collected delta against the plan, check `gh pr checks <n>` (tab output) is 6/6 green.

### 4.4 Gates to ask the owner during Wave 2

- W-6 **Q3** (warning also on the chat page?) and **Q5** (warning copy as written?) before W-6's merge. Option text: W06 §11 table.
- W-1 OG-1/OG-2/OG-4/OG-5 only if W-1's L1 wants them (all optional).
- After P8 and G-C4 merge: the owner signs the packet's brief lines and S-C4-1…5 in those documents (agents never record approvals).

### 4.5 Open owner items (no plan; do not fix inside Wave 2 phases)

SECGATE-SHAPE, CACHE-STALE, CACHE-HIT-AUDIT, AUDIT-KEYS-DROPPED, MODEL-PIN, TORCH-PIN, **DOC-DELETE-INTERP (security + data loss: document delete with a LabInterpretation → 500 after the encrypted file is unlinked)**, **RECOVERY-CODE-CACHE (security)**, AGENT-PASS-LINE (`CLAUDE.md:31`, `AGENT.md:76` pass sentences), CLAUDE-FAILURE-COUNT, plus the older RL-EXPORTS, GATE-14 (did not reproduce on Linux/3.11), TIME-03, KEY-08, LOCAL-07, AUD-INTERP, INTERP-UNVERIFIED, MSG-UNVERIFIED, C-LLM-2, GATE-12, PRIV-06, RTN Q6. CI-DISK is **closed** (#25). Register in the program "Program owner items" table. Suggest to the owner: schedule DOC-DELETE-INTERP and RECOVERY-CODE-CACHE as small security phases.

## 5. Lessons from Wave 1

1. **Re-derive when main moves.** Plan 01 assumed `40f590e`; main moved twice. `git merge-tree --write-tree` before dispatch caught the new conflicts.
2. **Codex plan reviews earn their cost.** P01 r1 found a cross-profile PHI leak that was live on main (S-CACHE). Verify each finding against the code: one BLOCKER (real master DB) was refuted by measurement.
3. **Break-it checks need precision.** One L0 `sed` removed the wrong `profile_id=` line. Delete by line number after `grep -n`, and confirm the failure message names the intended path.
4. **This `gh` has no `--json` on `gh pr checks`.** Parse the tab output (column 4 = job URL; job logs via `gh api repos/BrooklynD23/HealthCentral/actions/jobs/<id>/logs`).
5. **The owner merges slowly and the host can sleep.** L1 merge polls end after 3 h; brief L1s to write their section and hand back, and re-dispatch a fresh L1 from the RESUME POINT.
6. **Two docs PRs that both regenerate `docs/INDEX.md` merge cleanly only if the second regenerates after the first lands.** Run `generate_docs_index.py --check` on main after each merge.
7. **Use the venv for every Python script that imports backend code.** System `python3` 3.12 has no sqlalchemy (the eval gate gave rc=2 there).
