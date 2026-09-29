# Workflow Orchestration — Execution Program

**Status:** current as of 2026-09-28. Owner-directed. It applies to executing the program in [implementation-program.md](../capstone-report/implementation-program.md) (phases P1–P8, W-1…W-11b, S-1, G-C*). Behavioural rules stay in [CLAUDE.md](../../CLAUDE.md); definition of done stays in [AGENT.md](../../AGENT.md#definition-of-done). The paste-ready prompt for the next session is [handoff-2026-09-28-execution-orchestrator.md](../../audit/2026-09-25/handoff-2026-09-28-execution-orchestrator.md).

## 1. Three tiers

| Tier | Runs as | Model (`Agent` tool `model`) | Does | Never |
|---|---|---|---|---|
| **L0 Program orchestrator** | the main Claude Code session | Opus 5.5, effort high | Picks the next wave, checks its owner gates are signed, spawns one L1 per wave, verifies L1 reports, updates the ledger, program and stakeholder artifact | Edits product code; merges PRs; signs gates |
| **L1 Wave orchestrator** | `Agent`, `subagent_type: "general-purpose"` | `"opus"`, effort high | Owns one wave: one worktree + one branch + one PR per phase; spawns L2 agents; runs the measured acceptance itself; opens PRs; writes the wave report | Implements code itself; starts a phase whose dependencies are not on `origin/main`; widens scope |
| **L2 Implementer** | `Agent`, `"general-purpose"` | `"sonnet"` | Executes one plan's tasks in its worktree, test-first, commit by commit as the plan lists them | Spawns agents; edits outside the plan's file list; edits ask-first files without a signed gate |
| **L2 Reviewer** | `Agent`, `"code-reviewer"`, plus `"security-reviewer"` when the diff touches redaction, auth, encryption, export, logging or the external runner | `"opus"`, effort high | Read-only review of each implementer report: spec compliance first, then quality, then the recurring-failures recheck | Edits files |
| **Codex** | `codex exec` read-only, or the codex plugin companion script | Codex default | Adversarial review of architectural plans before a wave, and of architectural PR diffs before they open (§5) | Writes to the repo |

**Model policy.** Implementation runs on the `sonnet` alias; reviews and orchestration run on `opus`. The owner set this on 2026-09-28 for this program, and it overrides the user-level "Opus for coding" default here. The owner calls the implementer model "Sonnet 5.5"; the `Agent` tool exposes it as `"sonnet"`, which resolves to the current Sonnet release. `"haiku"` is only for read-only search fan-out.

**Nesting (measured 2026-09-28).** A `general-purpose` subagent has the `Agent` tool (models `sonnet`, `opus`, `haiku`, `fable`), and a nested spawn from it returned. Subagents do **not** have the `Workflow` tool. So L0 may use `Agent` or `Workflow` to start L1, L1 uses `Agent` for L2, and L2 spawns nothing. Maximum depth is 2 below L0.

## 2. Wave loop (L0)

1. Read the RESUME POINT in [`ledger.md`](../../audit/2026-09-25/swarm-2026-09-27/ledger.md), the program graph and [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md).
2. Confirm every dependency of the wave's phases is merged: `git merge-base --is-ancestor <commit> origin/main`.
3. List each owner gate the wave needs **before** a Task 0 or a merge. Ask the owner about any that are unsigned (at most 4 questions per prompt) and record each answer verbatim in owner-decisions in the same session.
4. Spawn one L1 per wave, with the brief template in the handoff §4. Independent waves never run at once; phases inside one wave may.
5. When L1 reports, re-run one acceptance command from each PR yourself and compare the output. A report is a lead, not a finding (CLAUDE.md §1).
6. Update the ledger (append-only, dated), the program state labels and the stakeholder artifact. Commit docs on a `docs/` branch.
7. The owner merges PRs in the order L1 gives. The next wave starts only after its dependencies are on `origin/main`.

## 3. Phase loop (L1)

1. **Task 0** of the plan: ancestry checks, gate checks, and `git ls-files docs/plans/2026-09-27-<ID>-*.md` non-empty. A failed check stops the phase; report it, do not work around it.
2. **Codex plan review** if the phase is architectural (§5). Verify each finding against the code before applying it (`receiving-code-review`), then commit plan amendments as the first commit on the phase branch.
3. **Worktree:** `git worktree add ../hc-<id> -b <fix|feat|docs>/<id>-<slug> origin/main`. One phase, one worktree, one PR.
4. **Implement:** spawn the L2 implementer with the brief in the handoff §5. For a plan whose tasks touch disjoint files, spawn one implementer per task group; otherwise one implementer runs the whole plan.
5. **Review:** after each implementer report, spawn the L2 reviewer (handoff §6). Send issues back to the same implementer with `SendMessage`, then re-review. After 3 failed loops, stop and escalate to L0.
6. **Verify yourself:** run the plan's measured acceptance commands in the worktree and paste the output. A green suite is evidence, not proof (CLAUDE.md §4).
7. **Codex diff review** for architectural phases: `node <codex-plugin>/scripts/codex-companion.mjs adversarial-review --wait --base origin/main "<focus>"`, run from the worktree.
8. **Open the PR:** the body names the plan, the gates used, the commands and their output, and the collected-count delta. Then stop. Humans merge (program ground rule 6).

## 4. Environment rules

- **Interpreter (D9, D9-SRC):** `uv venv -p 3.11 ~/venvs/asclexis-311 && uv pip install -p ~/venvs/asclexis-311/bin/python -r src/backend/requirements.txt`.
- **Offline tests:** set `HF_HUB_OFFLINE=1` on every backend test run until W-8 lands. Without it the suite silently downloads the embedding model (matrix LOCAL-03).
- **Run suites in the phase worktree only.** Tests that touch the master engine can write to the developer's real master DB (S-1 finding). After a run, `git status --short` must show only the phase's files.
- **Frontend:** `vitest` stalls under WSL on `/mnt/c`. Run frontend checks from Windows, or record them as skipped with the reason.
- **Staging:** explicit pathspecs only; never `git add -A`.
- **Counts:** ground rule 8 (SLOT-RULE). A commit that changes the collected backend count updates the `CLAUDE.md` / `AGENT.md` collected slots in the same commit.
- **Ask-first files** (CLAUDE.md §1) need a signed gate naming that exact edit, even inside an approved phase.
- **Dependencies:** `src/backend/requirements.txt:27` pins `sqlalchemy[asyncio]>=2.0.25,<2.1` (PR #20). SQLAlchemy 2.1 no longer installs `greenlet` by default. Do not unpin it inside another phase.

## 5. When to use Codex

Codex reviews the decisions that are expensive to reverse. The phases below are **architectural**: they change a data path, a safety boundary, the schema or governance text.

| Architectural phases | Why |
|---|---|
| P1, P6, G-C1 | branch merge; FK enforcement + migration; persisted export store |
| S-1, W-6, W-2 | PHI leaving the process: logs, cloud runner, doctor summary |
| W-3, W-4, W-8 | what the assistant may cite or answer; offline model |
| W-7 | new LLM route through ModelRunner, beside `interpret_safety` |
| W-10 | governance invariants in `CLAUDE.md` / `data-privacy.md` |

- **Plan review (before the wave):** `codex exec -s read-only -C <repo> -o <out>.txt "$(cat <prompt>.md)"`. The prompt template is the proven one at [`audit/2026-09-25/swarm-2026-09-27/reviews/W04-r1-prompt.md`](../../audit/2026-09-25/swarm-2026-09-27/reviews/W04-r1-prompt.md). Its output contract is `VERDICT: PASS | REVISE` plus one `[BLOCKER|MAJOR|MINOR]` line per finding.
- **Rounds:** at most 2 per plan amendment. Store the prompt, output and response under `audit/<date>/reviews/`.
- **Diff review (before the PR opens):** the `adversarial-review` command in §3 step 7.
- **Not for:** docs-only phases (P4, P8, W-11a PR-4, G-C4), except where the owner asks.

## 6. Reports and records

- **L1 wave report:** `audit/<date>/waves/wave-<N>.md`. It lists each phase with its PR link, commands and output, collected delta, gates used, findings not fixed, and merge order.
- **Ledger:** L0 appends a dated section per wave with a RESUME POINT. A session can end at any time (a usage limit ended the 2026-09-27 swarm), so the ledger must always say what to do next.
- **Stakeholder view:** the artifact "Asclexis Delivery Map" shows the waves. L0 republishes it after each wave.
