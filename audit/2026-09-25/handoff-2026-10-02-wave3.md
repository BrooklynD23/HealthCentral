# Handoff — L0 Orchestrator, Wave 2 close + Wave 3 (2026-10-02)

Paste §1 into a fresh Claude Code session at the repo root (Opus 5.5, high effort). Process: [docs/agentic/orchestration.md](../../docs/agentic/orchestration.md). Brief templates (L1/L2/reviewer, Codex): [handoff-2026-09-28 §4-§7](handoff-2026-09-28-execution-orchestrator.md). Folder index: [README.md](README.md).

## 1. Prompt

```
You are the L0 Program Orchestrator for Asclexis (HealthCentral repo). Waves
0-2 are merged. Your job: run Wave 3 through L1 orchestrators, merges serial.
Stop at every owner gate and every PR merge.

<working_directory>/mnt/c/Users/DangT/Documents/GitHub/HealthCentral</working_directory>

<read_first>
1. CLAUDE.md, AGENT.md; docs/agentic/orchestration.md; docs/agentic/recurring-failures.md
2. audit/2026-09-25/handoff-2026-10-02-wave3.md (this file): §2 state, §3 Wave 3, §4 lessons
3. audit/2026-09-25/swarm-2026-09-27/ledger.md: the LAST RESUME POINT
4. audit/2026-09-25/waves/wave-2.md; handoff-2026-09-28-execution-orchestrator.md §4-§7
5. docs/capstone-report/implementation-program.md (graph, shared-file order, owner items)
   and owner-decisions-2026-09-27.md (verbatim scope)
</read_first>

<roles>L0 = you (Opus): never edit product code, never merge, never sign a gate.
L1 = Agent(general-purpose, opus), L2 implementers = Agent(general-purpose, sonnet),
reviewers = Agent(code-reviewer, opus) + security-reviewer on PHI/auth/export/logging
diffs. Every Agent prompt includes:
Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)</roles>

<resources>12 GB RAM host. At most 2 code L1s at once; every full backend suite runs
as `flock /tmp/claude-1000/hc-pytest.lock <venv python> -m pytest tests/ ...`;
one L2 per L1 at a time. Docs-only L1s may run alongside.</resources>

<start_here>
1. Is the Wave 2 close docs PR merged? If not, ask the owner to merge it.
2. Ask the owner the Wave 3 gates in §3.2 (max 4 questions per prompt).
3. Dispatch §3.1 phases; verify each PR yourself before handing it over.
</start_here>
```

## 2. State at handoff (2026-10-02)

| Item | State | Evidence |
|---|---|---|
| `origin/main` | `f5d829b` (PR #28 merged) | `git log origin/main` |
| Waves 0-2 | done: #19; #21-#27; #28-#35 | [waves/wave-2.md](waves/wave-2.md), ledger |
| Collected backend count | **1346** (`CLAUDE.md:30`, `AGENT.md:76`) | L0 `--collect-only` on `f5d829b` |
| Docs gates on main | docs_lint, index --check, feature_list_lint, repo_hygiene_check, harness_drift_check all rc=0 | L0, 2026-10-02 |
| D9 venv | `~/venvs/asclexis-311/bin/python` 3.11.16 (no pip; `uv pip install -p …`) | ledger |
| Owner actions open from Wave 2 | W-1 `/agents` smoke (Task 7 Steps 2-5); P8 packet owner lines; G-C4 S-C4-1…5 | [wave-2.md §Owner actions](waves/wave-2.md) |
| Worktrees | `../hc-l0-docs` (docs branch), `../hc-l0-verify` (detached, reuse for PR checks); Wave 2 phase worktrees removed at close | `git worktree list` |

## 3. Wave 3

### 3.1 Phases now unblocked (dependencies on `origin/main`)

| Phase | Plan | Kind | Signed gates | Still owner-gated | Codex |
|---|---|---|---|---|---|
| **P4-core** | [P04](../../docs/plans/2026-09-27-P04-doc-drift-sweep-amendment.md) + audit plan 04 | DOCS | D2, D3 (docs only); deps P1, P2, W-1 merged | OG-4/5/6 per commit; S1-S9 in P04; OG-2 = D4-EXPORTS (documents only). `hipaa-controls.md:169` only after P8 Brief 2 is signed (P8-B2-ORDER) | no |
| **W-11a PR-4** | [W11a](../../docs/plans/2026-09-27-W11a-test-and-gate-hardening.md) G-B6 | DOCS | — | — | no |
| **G-C3b** | [W11b](../../docs/plans/2026-09-27-W11b-roadmap-items-gc1-gc4.md) G-C3b | PRODUCT | deps P2 merged | **S-C3-3** | no |
| *Suggested small security phases (no plan yet; owner schedules):* DOC-DELETE-INTERP, RECOVERY-CODE-CACHE, NPM-AUDIT | — | PRODUCT | — | owner scheduling + plan | DOC-DELETE-INTERP: yes |

P4 owns many docs (and the DOC-OVERCLAIM items route to it or to W-10); run it as one L1 alone on the docs files. W-11a PR-4 needs Windows vitest/Playwright output (`powershell.exe -NoProfile -Command "cd C:\Users\DangT\Documents\GitHub\<wt>\src\frontend; npm ci; npx vitest run"`).

### 3.2 Gates to ask the owner before Wave 3

1. **S-C3-3** (G-C3b) — or skip G-C3b this wave.
2. Schedule DOC-DELETE-INTERP and RECOVERY-CODE-CACHE (security) as small phases now? (plans needed first)
3. NPM-AUDIT (21 vulns: 1 critical, 14 high): `npm audit fix` phase now, or later?
4. P4's per-commit OG-4/5/6 and S1-S9 as listed in P04 (ask in batches of ≤4).

### 3.3 After Wave 3 (Wave 4 preview)

P5 (utcnow; after P4; D13 signed; touches ask-first `api/profiles.py`), W-10 (governance; after P4; GOV-BG, GOV-D11 unsigned), G-C2 (owner run; after P4 Task 13), G-C5 (after P8 Brief 5 is signed).

### 3.4 Merge rules (unchanged)

Serial merges. Every PR that changes the collected count merges `origin/main`, re-measures and rewrites `CLAUDE.md:30,:35` + `AGENT.md:76` before the owner merges it. Docs PRs that regenerate `docs/INDEX.md` regenerate again after the previous one lands. Before handing over: re-run one acceptance command and one break-it at the PR head in `../hc-l0-verify`; `gh pr checks <n>` 6/6.

## 4. Lessons from Wave 2

1. **Size parallelism to the host.** 4 parallel L1s running suites exhausted 12 GB and killed every agent. Commits survived; resuming with `flock` + one L2 per L1 + ≤2 code L1s finished the wave.
2. **Persist L0 notes in the repo worktree, not the scratchpad.** A restart wiped the scratchpad (including a patched artifact); `waves/wave-2-L0-notes.md` survived.
3. **A message to an idle agent can sit unread.** If a requested refresh has not started after ~20 min, check the worktree, then nudge or replace the agent.
4. **Each refresh is cheap and serial:** merge main → collect → rewrite slots → full suite under flock → push → L0 verifies. Six code PRs went through this without a failure.
5. **`gh pr edit` fails here** (Projects-classic GraphQL error); use `gh api -X PATCH repos/BrooklynD23/HealthCentral/pulls/<n>`. `gh pr checks` has no `--json`; parse the tab output.
6. **Break-it at the PR head catches vacuous tests:** one per code PR, delete by line number after `grep -n`, restore with `git checkout`.
7. **CI `-q` output cannot prove a named test ran** (HC-AGENTS-008): keep such gates at `tested` until a log names the test.
