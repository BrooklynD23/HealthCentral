# Build Program 2026-10-15 — Multi-Runtime Runbook

**Last Updated:** 2026-10-15
**Owner:** repository owner
**Status:** PROPOSED (L0 runbook author). No owner approval is recorded here. Every gate keeps its state in [owner-decisions](../../capstone-report/owner-decisions-2026-09-27.md).
**Refresh Trigger:** any edit to [queue.md](queue.md) scheduling rules, [contracts.md](contracts.md) §b–§d, or [orchestration.md](../../agentic/orchestration.md); a new runtime; a change to `codex exec` flags or the Devin MCP tools; a claim race or stale claim that this file did not resolve.

**Review:** [Codex adversarial review, 2026-10-15](../../reviews/2026-10-15/build-program-codex.md) (covers this file, contracts, queue and the workflow).

One item loop that **Claude Code, Codex CLI and Devin** run against the same [queue](queue.md), with GitHub as the only lock. It extends the tier model in [orchestration.md](../../agentic/orchestration.md) §1–§5 and does not repeat it. Behaviour rules stay in [CLAUDE.md](../../../CLAUDE.md); done stays in [AGENT.md](../../../AGENT.md#definition-of-done); shared files, migrations and count slots stay in [contracts.md](contracts.md) §b, §c, §d.

---

## 1. Roles per runtime

| Role | Claude Code | Codex CLI | Devin |
|---|---|---|---|
| Orchestrator / planner (L0, L1) | `model: "opus"` | no | no |
| Implementer (L2) | `model: "sonnet"`, any item | items with runtime `codex` or `any` | items with runtime `devin` or `any` |
| Reviewer | `model: "opus"` (`code-reviewer`; plus `security-reviewer` on redaction, auth, encryption, export, logging, external runner) | adversarial reviewer, `-s read-only` | no |
| Explore / search / web search | `model: "haiku"`, read-only | no | research only (`ask_wiki_question`, no repo writes) |
| Test runner (runs suites, never writes tests) | `model: "haiku"`, read-only, every pytest through `scripts/pyslot.sh` | no | no |

1. **Runtime column.** The queue's `runtime` column picks who may implement: `claude` = Claude Code only; `codex` / `devin` = that runtime, or another one only after L0 edits the queue row; `any` = any of the three. `(model machine)` items (B-4, B-7, B-9) are owner work and are never claimed.
2. **Reviewer rule.** The reviewer is never the same runtime **and** session as the implementer. A fresh Opus session may review a Sonnet implementer. A Codex or Devin implementation gets a Claude Code Opus review, or a Codex review of a Devin implementation. A Devin session never reviews.
3. **Architectural items** ([orchestration.md](../../agentic/orchestration.md) §5, or a queue row that says `+ Codex`) also get a Codex adversarial diff review before the PR leaves draft. If Codex was the implementer, the extra review is a second Claude Code Opus session instead.

---

## 2. Item loop (runtime-neutral)

| # | Step | Done when | Section |
|---|---|---|---|
| 1 | **Claim** the item | your draft PR is the only open PR on `<type>/<id>-*` | §3 |
| 2 | **Worktree** `git worktree add <repo-parent>/hc-<id> -b <type>/<id>-<slug> origin/main` (part of the claim) | `git -C <wt> status` is clean | §3 |
| 3 | **Task 0** checks | every check passes, or the item stops with the failing check in a PR comment | §4 |
| 4 | **Implement test-first**: RED output captured per new test id, then GREEN, commit by commit as the plan lists, explicit pathspecs | the item's file list covers every changed file | the item's plan |
| 5 | **Review** (another runtime or session) | `VERDICT: PASS`, at most 3 rounds | §5 |
| 6 | **Measured acceptance** after the final `git merge origin/main` | output pasted, not paraphrased | §6 |
| 7 | **PR** body filled, title changed from `[claim:…]` to a conventional title, `gh pr ready` unless a merge gate or the parked-draft rule holds it | slot released | §6 |
| 8 | **Stop.** Humans merge. L0 runs the post-merge batch | — | §7 |

"Item" = one queue row. One item = one worktree = one branch = one PR. `<id>` is the queue ID in lower case (`E-1` → `e-1`, `RAG-RUNTIME-500` → `rag-runtime-500`).

---

## 3. Claim protocol (GitHub is the lock)

No new infrastructure: a branch name is the lock, a PR title is the slot.

| Thing | Rule |
|---|---|
| **Lock** | an open PR whose head branch matches `^[a-z]+/<id>-`. The trailing hyphen keeps `f-1-` apart from `f-10-`. One pair still overlaps: `g-c5-` also matches `g-c5-plan-…`, so a G-C5 slug never starts with `plan`, and a G-C5 lock check ignores a `g-c5-plan-` branch. |
| **Slot** | an open PR titled `[claim:<runtime>] <ID> <slug>` holds one code slot. Queue rule 1 caps slot holders at **12** across all runtimes. No-slot items (DOCS, OWNER landings) use `[claim:<runtime>:noslot] <ID> <slug>`. |
| **Runtime tag** | `claude`, `codex` or `devin`. |
| **Heartbeat** | any push to the branch or any PR comment. |
| **Stale** | a `[claim:` PR with no heartbeat for **24 h**. Only L0 releases it: L0 comments `stale claim released` and closes the PR **without** deleting the branch, so the work can be salvaged. A runtime never closes another runtime's PR. |
| **Release** | step 7 retitles the PR, which frees the slot. The branch keeps the lock until the PR merges or closes. Escalation retitles to `[escalated:<runtime>] <ID> <slug>` (§8), and any other stop (failed Task 0 check, implementer stop, failed acceptance, Codex BLOCKER) retitles to `[blocked:<runtime>] <ID> <slug>`; both free the slot (queue rule 1: a PR that waits holds no slot). To resume, L0 retitles back to `[claim:…]` after the slot check passes. |
| **Race** | after opening, re-run the lock check. If another open PR holds the same prefix with a **lower** number, close yours with `lost claim race to #<n>`, delete your own remote branch and remove your worktree. The same applies when the slot count is now above 2 and yours is the highest-numbered claim. |

Paste-ready claim (bash, run from any checkout of the repo; the launcher runs it for Codex and Devin):

```bash
set -euo pipefail   # any failed step aborts the claim; nothing below runs on a failed check
ID=E-1; RT=claude; TYPE=fix; SLUG=doctor-summary-redaction   # TYPE: fix|feat|docs|test|chore
NOSLOT=""                                                       # set to ":noslot" for DOCS/OWNER rows
id=$(printf '%s' "$ID" | tr 'A-Z' 'a-z')
REPO=$(git rev-parse --show-toplevel); git -C "$REPO" fetch origin

# 1. lock check: must print nothing
LOCK=$(gh pr list --state open --limit 200 --json number,headRefName \
  --jq ".[] | select(.headRefName | test(\"^[a-z]+/${id}-\")) | .number")
[ -z "$LOCK" ] || { echo "locked by PR $LOCK"; exit 1; }

# 2. slot check (code rows only): must print 11 or less
SLOTS=$(gh pr list --state open --limit 200 --json title \
  --jq '[.[] | select(.title | startswith("[claim:") and (contains(":noslot]") | not))] | length')
[ -n "$NOSLOT" ] || [ "$SLOTS" -le 11 ] || { echo "no free slot ($SLOTS held)"; exit 1; }

# 3. claim (the push fails if the branch already exists on origin, which aborts the claim)
BR="$TYPE/$id-$SLUG"; WT="$(dirname "$REPO")/hc-$id"
! git -C "$REPO" ls-remote --exit-code --heads origin "$BR" >/dev/null || { echo "branch $BR exists"; exit 1; }
git -C "$REPO" worktree add "$WT" -b "$BR" origin/main
PUSHED=""   # a failure from here on removes only what this claim created, so a retry starts clean
trap '[ -z "$PUSHED" ] || git -C "$REPO" push origin --delete "$BR" || true; git -C "$REPO" worktree remove --force "$WT" || true; git -C "$REPO" branch -D "$BR" || true' ERR
git -C "$WT" commit --allow-empty -m "chore: claim $ID ($RT)"
git -C "$WT" push -u origin "$BR"; PUSHED=1
gh pr create --draft --base main --head "$BR" --title "[claim:$RT$NOSLOT] $ID $SLUG" \
  --body "claim: $RT session <session-ref>
item: docs/plans/2026-10-15-build-program/queue.md ($ID)"
trap - ERR

# 4. race re-check: step 1 must now print only your PR number, and (code rows)
#    step 2 must print 12 or less; otherwise apply the Race row above
```

---

## 4. Task 0 checks

Run in the worktree. A failed check stops the item: post the failing command and its output as a PR comment, keep the draft, retitle it `[blocked:<runtime>] <ID> <slug>` (§3 Release) and tell L0. Never work around a check.

1. **Spec exists.** Read the queue row, the lane-doc section it cites and the plan that section names. A plan path must exist on `origin/main` (`git ls-files <path>` non-empty) or be the lane-doc section itself.
2. **Dependencies merged.** For each `depends_on` PR: `gh pr view <n> --json state --jq .state` prints `MERGED`. For each queue ID (merged PR titles end in `(<ID>)`, §6): `gh pr list --state merged --limit 200 --json number,title --jq '.[] | select(.title | endswith("(<ID>)")) | .number'` prints a number (PRs merged before this program lack that suffix; check those by PR number). For each commit: `git merge-base --is-ancestor <sha> origin/main`.
3. **Gates.** Each execution gate in the row has an answer in [owner-decisions](../../capstone-report/owner-decisions-2026-09-27.md): quote the line. Gates marked "merge only" do not stop work; they stop step 7's `gh pr ready`. Tasks a row marks blocked (such as E-3 Tasks 7 and 8.4) are skipped and listed in the PR body.
4. **Ask-first files.** Every file in the row's `ask-first` column, and any [CLAUDE.md](../../../CLAUDE.md) §1 file the diff would touch, needs a signed gate that names the exact edit. Files marked "called only" are never edited.
5. **No shared file.** No other open non-draft PR touches a file in the row, apart from the exemptions in [contracts.md](contracts.md) §b rule 3. Parked drafts follow §b rule 2.
   ```bash
   for n in $(gh pr list --state open --json number,isDraft --jq '.[] | select(.isDraft|not) | .number'); do gh pr diff "$n" --name-only; done | sort -u > /tmp/claude-1000/open-files.txt
   ```
   Then intersect that file with the row's file list. The intersection must be empty. A freshly claimed PR is a draft with an empty diff, so also take every other open `[claim:` PR, read its queue row (its title names the ID) and intersect that row's file list with yours; it must be empty too. A parked draft that has already released its slot is exempt (§b rule 2).
6. **Start count** ([contracts.md](contracts.md) §d step 8). Run the §d step 2 command on the clean worktree. It must print the slot value (`grep -n collected CLAUDE.md AGENT.md`). If it differs, stop and report. Do not fix another PR's slot.
7. **Contracts.** List each `I-n` row in [contracts.md](contracts.md) §a that the item provides or consumes. A provider that has to change a signature stops and asks L0.

---

## 5. Review

1. The implementer finishes a round and pushes (or, for Codex, the launcher pushes).
2. The reviewer (§1 rule 2) reads `git diff origin/main...HEAD` and checks three things in order: the spec (plan + row + contracts), then quality, then the 10 modes in [recurring-failures.md](../../agentic/recurring-failures.md). Route tests must go through `route_client`, and a test that could not fail counts as a finding.
3. Output contract, matching [orchestration.md](../../agentic/orchestration.md) §5: first line `VERDICT: PASS | REVISE`, then one `[BLOCKER|MAJOR|MINOR] file:line — issue — fix` line per finding.
4. The reviewer posts the output as a PR comment headed `review round <k>/3 (<runtime>, <session-ref>)`. That comment is how the loop is counted on every runtime.
5. The implementer answers every BLOCKER and MAJOR finding, using `receiving-code-review`: verify against the code before changing it, and push back with evidence when a finding is wrong. Then the next round starts.
6. A third REVISE goes to escalation (§8).

---

## 6. Measured acceptance and the PR

Run in the worktree after the **final** `git merge origin/main`. Paste every command with its output.

1. The plan's acceptance commands, plus the RED → GREEN output for each new test id.
2. The full backend suite, run in the worktree only:
   ```bash
   cd src/backend && "$(git rev-parse --show-toplevel)/scripts/pyslot.sh" env HF_HUB_OFFLINE=1 \
     ~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q
   ```
   The only allowed failure is the environmental `test_api_rag_index_002b` ([CLAUDE.md](../../../CLAUDE.md) §4). Devin's VM has no flock file; it runs the same command without `flock`.
3. The collected count, measured with [contracts.md](contracts.md) §d step 2, pasted with its delta. Do not write the slots.
4. `cd src/backend && ~/venvs/asclexis-311/bin/python -c "from main import app"`.
5. The frontend, when touched: `npx tsc --noEmit`. `vitest` stalls on `/mnt/c`, so run it from Windows or CI, or record it as skipped with that reason.
6. `git status --short` shows only the item's files.

**PR body** (all sections required, even when the answer is "none"):

| Section | Content |
|---|---|
| Item | queue ID, lane-doc section, plan path |
| Runtimes | implementer runtime + session; reviewer runtime + session per round |
| Gates used | each gate id with the quoted owner-decisions line; ask-first edits with the gate that names them |
| Skipped tasks | tasks blocked by an unanswered gate |
| Contracts | `I-n` provided or consumed; for providers, the I-22 trigger grep and its output |
| Commands | §6 steps 1–6, command + output |
| Count | start count, final count, slot commit SHA |
| Files changed | full list |
| Review | final `VERDICT` line; Codex adversarial output for architectural items |

Then retitle, which releases the slot (§3): `gh pr edit <n> --title "<type>(<scope>): <summary> (<ID>)"`. Run `gh pr ready <n>` **unless** a merge-only gate is unanswered or the item is a parked draft ([contracts.md](contracts.md) §b rule 2, R-5).

---

## 7. Count slots and merge sync

[contracts.md](contracts.md) §d governs (SLOT-RULE-2, owner 2026-10-16). How a runtime applies it:

1. **Never edit** the count slots, `docs/INDEX.md`, `docs/_link_graph.json` or the `docs/reviews/README.md` table. Paste the measured collected line and its delta into the PR body instead.
2. **No merge token, no sync chain.** Merge `origin/main` into a PR only for a real code conflict or code dependency.
3. **After merges,** L0 opens the post-merge batch PR (§d step 3): slots, index, review rows. Nothing else.
4. **Migrations:** number at the final rebase per [contracts.md](contracts.md) §c, and run both §c checks in the PR body.
5. **After an owner merge from Windows,** run `git worktree list`. Windows `gh pr merge` can drop WSL worktree metadata; repair it with `git worktree repair <path>`.
6. **Main is protected** (MAIN-PROTECT): PR required, CI green, no direct or force push. Never try to bypass it.

---

## 8. Escalation and stops

| Trigger | Action |
|---|---|
| 3rd `REVISE` | Retitle to `[escalated:<runtime>] <ID> <slug>`. Keep the draft. Post a comment `escalation: owner` with all 3 review outputs and the open findings. L0 adds the item to the next owner prompt (at most 4 questions, [orchestration.md](../../agentic/orchestration.md) §2 step 3). |
| A Task 0 check fails, the implementer stops, or acceptance fails | Stop (§4). PR comment, keep the draft, retitle `[blocked:<runtime>] <ID> <slug>` (frees the slot), tell L0. |
| A guard, threshold or safety test blocks the work | Stop and ask. Never weaken it ([CLAUDE.md](../../../CLAUDE.md) §3). |
| A file outside the row's list is needed | Stop. L0 edits the queue row first ([contracts.md](contracts.md) §b). |
| A contract signature has to change | Stop. L0 rules first ([contracts.md](contracts.md) §a). |
| A Codex adversarial review returns a BLOCKER | Keep the draft. Treat it as a review round; if the review loop has already ended, retitle `[blocked:<runtime>]` and tell L0. |

---

## 9. Never (every runtime)

1. Merge a PR, or close another runtime's PR.
2. Sign a gate, record an owner answer, or tick an owner box. Only answers the owner gave are recorded, and only by L0, verbatim.
3. Edit an ask-first file ([CLAUDE.md](../../../CLAUDE.md) §1: `interpret_safety`, `redaction`, `faithfulness`, `verifier_agent`, auth/encryption, `core/auth.py`) without a signed gate that names that exact edit.
4. Edit outside the row's file list, edit a merged migration, or edit `docs/INDEX.md`, `docs/_link_graph.json` or the count slots.
5. Weaken a test, a threshold or a validation; add a blanket judge bypass (R-2).
6. Stage with `git add -A`, force-push, or push to a branch you did not claim.
7. Run any pytest outside `scripts/pyslot.sh` (3 machine-wide slots), or outside the item's worktree.
8. Claim a `(model machine)` or OWNER row.

---

## 10. Runtime adapters

### 10.1 Claude Code

Two workflows, explicit models throughout:

- [`.claude/workflows/build-wave.js`](../../../.claude/workflows/build-wave.js) **selects** every item eligible now: Haiku scans the queue, open PRs and owner decisions; Opus checks dependencies merged, execution gates answered, no claim; the script keeps a file-disjoint set of at most `max` (default 12) and returns it. L0 then starts **one `build-item` Workflow per id, all in one message, in the background**. The Workflow tool caps each workflow at `min(16, CPUs - 2)` concurrent agents (4 on this 6-vCPU WSL), so separate runs are what reach the owner's 30-agent cap; one item uses 1-2 agents at a time. `{"nested": true}` instead runs the items inside build-wave (capped at 4 agents). Every pytest goes through `scripts/pyslot.sh` (3 machine-wide slots; `PYSLOTS` overrides). Deferred items are logged with the reason; re-run after the next merges.
- [`.claude/workflows/build-item.js`](../../../.claude/workflows/build-item.js) runs one item: haiku explore, opus Task 0 + claim, sonnet implement test-first (writes tests, runs only its focused files), **haiku runs the full suite and acceptance** (failures go back to sonnet, at most 3 fixes), opus review (at most 3 rounds, haiku re-runs tests after each fix), opus verify + PR.

Paste into the main Claude Code session (L0, Opus):

```text
Run the Workflow `build-wave` with args {"max": 12}. When it returns its picked
ids, start one background Workflow `build-item` per id, all in one message
(args {"id": "<id>"}). Follow docs/plans/2026-10-15-build-program/RUNBOOK.md.
When each returns, re-run one
acceptance command from each PR yourself (orchestration.md §2 step 5), compare
the output, and report each PR link, its verdict and its count line, plus the
deferred and not-eligible lists.
Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)
```

One item only: run `build-item` with `{"id": "E-1"}`. Without the Workflow tool, L0 runs the same loop by hand with the L1/L2 tiers in [orchestration.md](../../agentic/orchestration.md) §1 and §3.

### 10.2 Codex CLI

Codex implements in its sandbox and has no network there. The launcher (a person or L0) claims the item (§3), runs Codex, then pushes. The linked worktree keeps its git data in the main repo's `.git`, so that directory must be writable as well.

```bash
GITDIR=$(git -C "$WT" rev-parse --path-format=absolute --git-common-dir)
codex exec -s workspace-write -C "$WT" --add-dir "$GITDIR" --add-dir /tmp/claude-1000 \
  -o "/tmp/claude-1000/codex-$id.txt" "$(cat /tmp/claude-1000/codex-$id-prompt.md)" </dev/null
git -C "$WT" push
```

`</dev/null` is required: with a non-TTY stdin, `codex exec` prints "Reading additional input from stdin..." and waits forever (seen 2026-10-15). If the sandbox cannot run the start-count command (§4 step 6), Codex stops and reports it. Never fall back to `danger-full-access`.

Implementer prompt (`codex-<id>-prompt.md`):

```text
You are the implementer (L2) for build-program item <ID> in this git worktree
(branch <branch>, draft PR #<n>). Follow
docs/plans/2026-10-15-build-program/RUNBOOK.md §4 (Task 0), then the item's
plan test-first: capture RED output per new test id, then GREEN; commit as the
plan lists, staging explicit paths only. Edit only the files in the queue row.
Rules: CLAUDE.md §1 ask-first files need a signed gate naming the exact edit;
never weaken a test or a threshold; never merge, push, or edit owner-decisions.
If a Task 0 check fails or a guard blocks you, stop and say which.
Review findings to answer (empty on round 1): <path or "none">.
Final message: first line DONE or STOPPED: <reason>; then commits, files
changed, RED and GREEN output, and the count line from contracts.md §d step 2.
```

Adversarial reviewer (read-only). Use it for Devin implementations and for the architectural extra review:

```bash
node ~/.claude/plugins/cache/openai-codex/codex/1.0.4/scripts/codex-companion.mjs \
  adversarial-review --wait --base origin/main "<ID>: spec = <plan path>; focus <risk>"
# or: codex exec -s read-only -C "$WT" -o "/tmp/claude-1000/codex-review-$id.txt" "$(cat review-prompt.md)" </dev/null
```

Use the reviewer prompt in §10.4.

### 10.3 Devin

Devin runs in its own VM, so it never holds the box's pytest slots. **Until L0 records otherwise, a Devin code item still counts toward the 2-slot cap.** The cap also limits how many rebases and merge syncs run at once.

1. The launcher claims the item with `RT=devin` (§3).
2. L0 starts the session with `devin_session_create` (Devin MCP), or the owner pastes the prompt into Devin web.
3. When Devin reports, L0 runs the §5 review with Claude Code Opus or Codex. Findings go back with `devin_session_interact` (send message) and point to the review comment.
4. L0 re-runs one acceptance command on the box before step 7.

Devin session prompt:

```text
Repo https://github.com/BrooklynD23/HealthCentral. Check out the existing
branch <branch> (draft PR #<n>, already claimed for you); never open another
PR. You implement build-program item <ID>.
1. Read CLAUDE.md, AGENT.md and docs/plans/2026-10-15-build-program/RUNBOOK.md.
2. Set up Python 3.11: uv venv -p 3.11 ~/venvs/asclexis-311 &&
   uv pip install -p ~/venvs/asclexis-311/bin/python -r src/backend/requirements.txt
3. Run RUNBOOK §4 (Task 0). If any check fails, comment the command and its
   output on PR #<n> and stop.
4. Implement test-first per the plan the queue row names. Paste RED, then GREEN,
   per new test id. Commit as the plan lists with explicit paths. Edit only the
   row's files.
5. Run RUNBOOK §6 steps 1–6 (no flock on your VM) and push to <branch>.
6. Comment on PR #<n> with: commits, files changed, every command and its output,
   and the start and final collected counts.
Never: merge, mark the PR ready, retitle it, edit owner-decisions, edit a
CLAUDE.md §1 ask-first file, weaken a test or threshold, or force-push.
Review findings arrive as PR comments titled "review round k/3". Answer each
BLOCKER and MAJOR finding, push, and comment again.
```

Research use (no claim, no slot): `ask_wiki_question` on `BrooklynD23/HealthCentral` for a second opinion. Its answer is a lead, not a finding ([CLAUDE.md](../../../CLAUDE.md) §1).

### 10.4 Reviewer prompt (any reviewing runtime)

```text
Review build-program item <ID>, PR #<n>, worktree <wt>. Read-only: do not edit,
commit or push. Spec: the queue row in docs/plans/2026-10-15-build-program/
queue.md, its lane-doc section and plan, and contracts.md §a rows <I-n>.
Diff: git diff origin/main...HEAD. Check in this order: (1) spec compliance and
the row's file list, (2) quality, (3) every mode in
docs/agentic/recurring-failures.md; route tests must use route_client, and say
what each new test would fail to notice. Flag any ask-first edit that has no
signed gate naming it, and any weakened test or threshold.
Output: first line VERDICT: PASS | REVISE, then one line per finding:
[BLOCKER|MAJOR|MINOR] file:line — issue — fix.
Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)
```

---

## 11. Open points for L0

1. **Devin and the slot cap** (§10.3): should an off-box Devin item count against queue rule 1? The default here is yes, which is the conservative choice.
2. **Committing the workflow:** `.gitignore:45` ignores `.claude/*`. Add the file with `git add -f .claude/workflows/build-item.js`, which leaves `.gitignore` untouched, because F-10 owns `.gitignore`.

Back to: [queue](queue.md) · [contracts](contracts.md) · [orchestration](../../agentic/orchestration.md)
