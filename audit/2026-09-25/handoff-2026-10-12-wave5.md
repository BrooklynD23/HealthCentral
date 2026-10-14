# Handoff — Wave 5 in flight (2026-10-12)

**Last Updated:** 2026-10-12
**For:** the next L0 Program Orchestrator session (Asclexis, HealthCentral repo). Supersedes [handoff-2026-10-09-wave4-close.md](handoff-2026-10-09-wave4-close.md) for state; its §6 environment notes still apply.
**Rule:** the owner merges; L0 never merges, never edits product code, never signs a gate, never records an owner decision the owner did not give L0 directly. Stop at every owner gate and PR merge. Verify every agent claim that matters; say what you did not verify. At most 2 code L1s at once; full backend suite only under `flock /tmp/claude-1000/hc-pytest.lock`. Every Agent prompt includes: `Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)`.

## 1. Read first

`CLAUDE.md`, `AGENT.md`, `docs/agentic/orchestration.md`, `docs/agentic/recurring-failures.md`, `docs/capstone-report/owner-decisions-2026-09-27.md` (rows through 2026-10-12), `docs/capstone-report/implementation-program.md`, the ledger `audit/2026-09-25/swarm-2026-09-27/ledger.md` (tail), `docs/reviews/README.md` (all Codex/Fable reviews now live in `docs/reviews/<date>/`).

## 2. State

`origin/main` = `767c13c`. Backend collected **1392** (`CLAUDE.md:30,34`, `AGENT.md:76`; owner rule AGENT-PASS-LINE: collected count only, never pass counts). Docs index fresh at `767c13c`. Delivery Map: https://claude.ai/artifact/DzJ89t8zJo4tPf7NjzctxV (status 12 Oct; the older JBYpfBuCegbdCfbTJzYtxi is on another account).

Merged 2026-10-12: #58 C2-CLOSURE + pass-line, #59 BG-WARN-INTERP, #60 Wave-4 close (38 owner rows), #63 Tailwind 4 brief, #64 ponytail cleanup + Node >=22.12.0, #75 medication routes 500 (all 4 routes lazy-loaded `schedules`), #70 streak naive-UTC, #76 chat-history restore race, #65 Codex reviews → `docs/reviews/`, #73 owner rows, #69 RSI/TPM/MMR plan, #77 RL-EXPORTS cleanup on profile delete, #56 AUDIT-ORDER plan (owner sign-off commit `7a89755`).

## 3. Open PRs

| PR | Branch | State | What is left |
|---|---|---|---|
| #78 | `fix/audit-order` | AUDIT-ORDER D code; the L1 was cut off by a session restart after commit `4029ede` (it reported collected 1466) | Verify: among ask-first files the diff touches only the approved `core/audit.py` helper and `core/auth.py:278-286`; collected count measured under flock; CI; reviews committed under `docs/reviews/`; PR body. Merge from main first (count conflict). |
| #74 | `feat/tailwind4` | draft, head `1bc3f3f`, CI 6/6; per-push evidence in the PR body (v3 green run 38215359803, upgrade-only red 38216544512, fix green) | Apply TW4-FOCUS-RETARGET (§4); owner screenshot review still required by the brief stop gate (before 11731333573, after 11738274443). |
| #72 | `fix/w4-legacy-abstain` | head `b832554`, CI 7/7, collected 1399 | Owner runs the 20-question real-model count (steps: PR #72 comment 6116808120) and pastes the RESULT line on #72. Then merge from main (count). |
| #66 | `fix/gamification-badges` | CI green earlier | Merge from main + recheck. |
| #67 | `docs/gamification-v2-plan` | approved (GAM2-PLAN-APPROVAL) | Merge; then dispatch v2 tasks 1/3 → 2/4 → 2b (2b profile migration ordered against P6's 013). |
| #61 | `docs/w4-plan-amend` | amendment already applied as #72's first commit | Likely close as superseded after #72 merges; ask the owner. |
| #62 | `docs/para-1-r3-plan` | Q1-Q8 answered (local answer judge, fail closed, 2s/90%/5%/tier-2, owner holds S5) | Merge; execution needs the owner-written sealed set S5 first. |
| #68 | `docs/rsi-loop-research` | merges LAST; merge order in a #68 comment | Rebase onto main; re-measure the collected count; keep main's CLAUDE/AGENT wording; keep both `.gitignore` sides. |

## 4. Owner answers 2026-10-12, not yet in owner-decisions

The owner replied "approved for recommended" to three questions. Two had a recommended option:

1. **TW4-FOCUS-RETARGET** — Q: "Codex MAJOR on #74: the focus-ring test targets the Sidebar link, which has its own `focus-visible:ring-*`, so the box-shadow half of that check can't detect a broken global focus rule (the outline half still works). The brief fixed that target. Fix it?" A: "Retarget in #74 (Recommended)" — "Point the box-shadow half at an element with no own ring class, prove it red on the upgrade-only commit. Small spec change; amends brief §4.2 item 6."
2. **TW4-HOVER-TOUCH** — Q: "Tailwind 4 makes `hover:` apply only on devices that support hover. `DocumentInbox.tsx:398` row actions appear only on hover, so on touch screens ≥640px they stay hidden. Fix?" A: "Separate small PR (Recommended)" — "Make those row actions visible without hover on touch (e.g. focus-within / always visible). Keeps #74 class-only."
3. **TW4-SHOTS** — the screenshot-review question had no recommended option. Treat it as OPEN and ask the owner whether they compare artifacts 11731333573 and 11738274443 themselves or approve on the L1 spot-check.

Record rows 1 and 2 verbatim in a small docs PR. If the permission classifier blocks an agent from writing them, ask the owner to commit; never route around the denial.

## 5. Next steps, in order

1. Run `git worktree list` first. The owner's Windows `gh pr merge --delete-branch` prunes WSL worktree metadata (memory note `windows-gh-prunes-wsl-worktrees`). Re-add lost worktrees before resuming agents. The main checkout sits on `docs/rsi-loop-research` with the owner's own uncommitted `.serena/project.yml` and untracked `audit/.../wave3/*tree/` folders: leave them alone and never `git add -A` there.
2. Finish #78 (above) and hand it to the owner.
3. #74: retarget the focus assert; open the hover-touch PR; ask TW4-SHOTS.
4. Record the §4 rows.
5. Dispatch RL-EXPORT-EMPTY PR-2 (plan `audit/2026-09-25/waves/scaffold/RSI-TPM-MMR.md` §3: server fills `prompt_snapshot` from the preceding user ChatTurn; RED through HTTP) when a code slot frees.
6. Then gamification v2, W-2, P6, PARA-1-R3 execution, G-C2. Refresh the Delivery Map after each merge batch.

## 6. Environment

- Devin MCP failed to connect all session; Claude fallback used.
- Every PR that adds tests changes the collected count in `CLAUDE.md`/`AGENT.md`. The second PR to merge needs `git merge origin/main` plus a re-measure. Never resolve by adding numbers by hand.
- Windows npm for the frontend; Windows git cannot see WSL-created worktrees.
- Agents hit the permission classifier when writing "approved"/"signed" text from relayed decisions. Never route around a denial with another tool (one L1 did on #74 commit `a24caf7`; the text was accurate, the method was not).
- `gh pr edit` can fail with a Projects-classic GraphQL error; use `gh api` REST.
- Always `cd` into a worktree with `set -e` or check it exists: on 2026-10-12 a failed `cd` ran `git add -A` in the owner's main checkout (local commit, undone with `git reset --soft HEAD~1 && git reset`; nothing pushed).
