**GATED** — dependencies P1 and P4 Task 13 are on `origin/main`; S-C2-1, S-C2-2 and S-C2-3 are unsigned, and the owner's generation run has not happened (`openwiki/` holds only `README.md`).

# G-C2 — OpenWiki generation review (readiness pack)

**Measured:** 2026-10-07, worktree `hc-scaffold` @ `8d6f02e`, `origin/main` = `6b4dd84`.
**Plan:** `docs/plans/2026-09-27-W11b-roadmap-items-gc1-gc4.md`, Group G-C2 (`:1071-1210`), approval scope `:109-119`, files `:213-218`, sign-offs `:1946-1948`.
**Kind:** OWNER → PRODUCT (docs content). The owner runs the tool; a session reviews the diff. Not architectural (orchestration §5 table does not list G-C2).

## 1. Readiness verdict

| Item | State |
|---|---|
| P1 | merged |
| P4 Task 13 (referrer wording → "stub") | merged: `884b83c`, `e462a4b` inside PR #40 |
| Owner record "owner generates locally; this session reviews the diff" | in force (`owner-decisions-2026-09-27.md:76` in this worktree, `:58` on `origin/main`; branch A plan `docs/plans/2026-09-08-backlog-closure-plan.md:405`) |
| S-C2-1 (run + send tracked source to an LLM API) | UNSIGNED (`W11b:1946`) → Task C2.0 STOPS |
| S-C2-2 (tool edits to `CLAUDE.md` / `AGENT.md` / `AGENTS.md`) | UNSIGNED (`:1947`; default reject) |
| S-C2-3 (reword referrers after generation) | UNSIGNED (`:1948`) |
| Owner generation run | not done |

## 2. Task 0 evidence (measured; plan Task C2.0 commands)

| Check | Command | Output |
|---|---|---|
| post-P1 | `git merge-base --is-ancestor 7b2ff1f origin/main; echo $?` and `… 692fdf3 …` | 0 and 0 |
| P4 Task 13 commits | `git merge-base --is-ancestor 884b83c origin/main; echo $?` and `… e462a4b …` | 0 and 0 |
| Status line | `git show origin/main:openwiki/README.md \| sed -n 15,17p` | "**Status:** still not generated (as of 2026-07-27). Wiki content has not been produced; only this hand-written README exists …" |
| Stub wording | `git show origin/main:AGENT.md \| grep -n openwiki` | `:20` "… (**not yet generated**; README-only stub). Advisory only once generated …" (P4 Task 13 wording) |
| Second referrer | `grep -n openwiki docs/00_architecture_plans_index.md` | `:63` (plan says `:58`) |
| Tree | `git ls-tree -r --name-only origin/main -- openwiki` | exactly `openwiki/README.md` |
| Plan tracked | `git ls-files docs/plans/2026-09-27-W11b-*.md` | 1 file; on `origin/main` |
| Tool needs an LLM key | `grep -n "LLM API key" openwiki/README.md` | `:27` "Requires an LLM API key (OpenWiki runs a DeepAgents documentation agent), so run locally" |
| Start gates | `docs_lint.py`, `generate_docs_index.py --check` | pass, exit 0 |

Gate rows on `origin/main`: the record is in the "Earlier owner records" table and is on main at `owner-decisions-2026-09-27.md:58` (`:76` in this worktree, which carries the 18 rows of `docs/wave3-close`). No 2026-10-07 row applies to G-C2.

UNMEASURED: whether `openwiki` honours `.gitignore`; the tool's current version and its behaviour on `CLAUDE.md` / `AGENTS.md`; output size. No network use was allowed in this pack.

## 3. Owner questions still to ask

1. **S-C2-1.** "OpenWiki sends tracked repository source to an LLM API with your key. Do you want to run `openwiki --init` yourself in a clean worktree?"
   - A. Yes: I run it from a clean worktree of `origin/main` and push `docs/gc2-openwiki-generation`. **(recommended; it is the branch-A d4 record)**
   - B. Not now; `openwiki/` stays a README-only stub and the docs keep saying so.
   - C. Drop G-C2 and remove the `openwiki/` references (new docs task; needs its own approval).
2. **S-C2-2.** "If the tool edits `CLAUDE.md`, `AGENT.md` or creates `AGENTS.md`, what happens to those hunks?"
   - A. Reject all of them. **(recommended; plan default. `CLAUDE.md` invariant text belongs to W-10)**
   - B. Accept a new `AGENTS.md` only.
   - C. Accept as listed: ____.
3. **S-C2-3.** "After generation, may the review session reword the two referrer lines (`AGENT.md:20`, `docs/00_architecture_plans_index.md:63`) from 'not yet generated; stub' to 'generated, advisory'?"
   - A. Yes. **(recommended; otherwise both lines are false the moment the PR merges)**
   - B. No; leave them and flag the stale wording in the PR.
4. **GC2-CLAUDE-67.** "`CLAUDE.md:67` also says 'generation has not run yet'. The plan forbids G-C2 from touching it. Who fixes it after generation?"
   - A. W-10 addendum or its own one-line governance commit, after G-C2 merges. **(recommended; `CLAUDE.md` text order is P1 → P4 → W-10)**
   - B. License G-C2 to edit that one paragraph.

Ask-first touches: none in `src/`. Governance files: `AGENT.md:20` (S-C2-3) and, only if question 4 = B, `CLAUDE.md:67`.

## 4. Plan drift check

| Plan citation | Now | Result |
|---|---|---|
| `openwiki/README.md` status sentence "still not generated (as of 2026-07-27)" | `:15` | MATCH |
| `AGENT.md:20` referrer | `:20`, P4 Task 13 "stub" wording | MATCH (wording is the post-P4 one the plan expects) |
| `docs/00_architecture_plans_index.md:58` | `:63` | **MOVED** (`git log -S` → `884b83c` "docs(index): mark openwiki as not-yet-generated stub in referrer wording", PR #40) |
| `CLAUDE.md:65-67` "OpenWiki usage" | `:65-67` | MATCH; `:67` now carries "generation has not run yet" (P1) |
| `CLAUDE.md` Hard invariants `:55-63` (Task C2.2 Step 4) | `:55-63` | MATCH. If W-10 merges first, `:60` and `:62` are longer; compare against the then-current text |
| `openwiki/README.md:28` "Requires an LLM API key" | `:27` | MOVED by 1 line |
| `scripts/docs_lint.py:97-101,288-292` (lint does not scan `openwiki/`) | `EXTRA_LINK_ROOTS` at `:106`, loop at `:297` | MOVED; the claim still holds (no `openwiki` in `docs_lint.py`: `grep -n openwiki scripts/docs_lint.py` → 0) |
| Task C2.0 `ROOT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral` | the main checkout is on `docs/p0b-plan-set` with local edits | usable for `fetch` and `worktree add` only |
| Task C2.1 worktree `HealthCentral-openwiki` | — | caller convention: `../hc-gc2` |

**Plan amendments to make (not made here):**

1. Referrer line: `docs/00_architecture_plans_index.md:63`.
2. Task C2.3 Step 3 pathspec: the two referrers only if S-C2-3 is signed (already stated); add the measured line numbers.
3. Task C2.2 Step 4: compare against `CLAUDE.md` as it stands when the review runs (W-10 may have landed).
4. Add question 4 (`CLAUDE.md:67`) as an explicit out-of-scope follow-up, so the stale sentence is tracked.
5. Task C2.1: `npm install -g openwiki` is a global install on the owner's machine and a network call; it is the owner's action only. Record the installed version in the PR.

## 5. File ownership and overlap

**Owned:** `openwiki/**` (generated; owner commit) · `openwiki/README.md` status line · `docs/INDEX.md`, `docs/_link_graph.json` (regenerated) · with S-C2-3: `AGENT.md:20`, `docs/00_architecture_plans_index.md:63`.
**Read-only:** `CLAUDE.md`, `AGENTS.md`, `.github/**`, all `src/**`.

| Other phase | Shared file | Rule |
|---|---|---|
| Every count-changing PRODUCT phase (P5, P6, P7, W-2, W-3, W-4, W-7, W-8, W-11a PR-1/PR-3, G-C1, G-C3a, G-C5, PROHIBITED-PARAPHRASE) | `AGENT.md:76` slot vs G-C2's `AGENT.md:20` | different lines, same file: serial at merge; the second PR rebases (ground rule 8) |
| W-10 | `CLAUDE.md` | G-C2 carries no `CLAUDE.md` hunk (S-C2-2 default) |
| AUDIT-ORDER plan PR, G-C3a, any PR that adds a doc or a link | `docs/INDEX.md`, `docs/_link_graph.json` | generated files: the PR that merges second regenerates on a clean tree |
| P4-deferred | none (P04 stop gate S7 says: if `openwiki/` holds generated content, re-check Task 13 wording) | G-C2 after P4-core: satisfied |
| NPM-AUDIT-2, React Router 7, Tailwind 4, W-4, W-2, W-3, P6, P7, W-7, W-8, W-11a, W-10b, G-C1 | none | generated pages may go stale as those land; `openwiki/` is advisory |

## 6. Briefs

### Owner step (the agent only prepares this; plan Task C2.1)

The owner runs the plan's Task C2.1 block (`:1097-1108`) with `GEN=/mnt/c/Users/DangT/Documents/GitHub/hc-gc2`, leaves any `CLAUDE.md` / `AGENT.md` / `AGENTS.md` change uncommitted, and pastes `git diff -- CLAUDE.md AGENT.md AGENTS.md` into the PR.

### L1 brief (filled; review half)

```
You are the L1 Wave Orchestrator for Wave 4 (docs lane) of the Asclexis execution
program. Follow docs/agentic/orchestration.md §3 exactly; you are L1.
Phase: G-C2 review: docs/plans/2026-09-27-W11b-roadmap-items-gc1-gc4.md, Tasks
C2.0, C2.2, C2.3 (:1073-1210). Task C2.1 is the owner's; you never run `openwiki`
and never hold an LLM API key.
Base: origin/main @ <sha>. Confirmed merged dependencies: P1 (7b2ff1f, 692fdf3),
P4 Task 13 (884b83c, e462a4b, PR #40).
Signed gates: <S-C2-1, S-C2-2, S-C2-3 answers verbatim from owner-decisions once
recorded>. Earlier record in force: owner-decisions :76 (:58 on main) "OpenWiki: the owner
generates it locally".
Unsigned at the time of writing: S-C2-1 (STOP at C2.0), S-C2-2, S-C2-3.
Not architectural: no Codex review.
Worktree: the owner's branch docs/gc2-openwiki-generation, checked out at ../hc-gc2.
Run every Task C2.2 step (9 steps) yourself and paste each output. Any miss =
request changes to the owner; do not rewrite generated text silently.
Then spawn one implementer (Agent general-purpose, model="sonnet") for Task C2.3
with the L2 brief below, and one reviewer (code-reviewer, model="opus").
security-reviewer (opus) also reviews: generated pages can restate an invariant
weaker or leak a secret or identifier (Steps 4-6).
Acceptance, pasted:
  git diff --name-only origin/main...HEAD | grep -v '^openwiki/'  -> only
    docs/INDEX.md, docs/_link_graph.json (+ AGENT.md,
    docs/00_architecture_plans_index.md if S-C2-3 is signed)
  git diff --name-only origin/main...HEAD -- CLAUDE.md AGENTS.md .github | wc -l -> 0
  git ls-files openwiki | wc -l                  -> > 1
  python3 scripts/docs_lint.py                   -> Docs lint passed.
  python3 scripts/generate_docs_index.py --check -> exit 0
  python3 scripts/harness_drift_check.py         -> passed
  python3 scripts/repo_hygiene_check.py          -> passed
  the Step 8 link resolver over openwiki/        -> links-ok
  grep -rniE "HIPAA[- ]compliant|covered entity" openwiki || echo d10-ok -> d10-ok
  collect-only (D9 venv, HF_HUB_OFFLINE=1)       -> unchanged vs origin/main
Write audit/2026-09-25/waves/wave-4-L1-<X>.md: PR URL, outputs, collected delta
(0), gates used, rejected hunks, open findings.
Do not merge. Do not sign gates. Do not edit CLAUDE.md or any src/** file.
Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)
```

### L2 implementer brief (filled; Task C2.3 only)

```
Implement docs/plans/2026-09-27-W11b-roadmap-items-gc1-gc4.md, Task C2.3
(:1193-1210), in worktree /mnt/c/Users/DangT/Documents/GitHub/hc-gc2 on branch
docs/gc2-openwiki-generation (the owner's generation commit is already there).
Python: python3 for the docs scripts.
Step 1: replace only the "**Status:** still not generated (as of 2026-07-27) …"
sentence in openwiki/README.md with the generated-status sentence; values (date,
version, provider/model, PR number) come from L1.
Step 2: only if L1 says S-C2-3 is signed: reword AGENT.md:20 and
docs/00_architecture_plans_index.md:63 to "generated, advisory". Otherwise leave
both and say so.
Step 3: python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py
--link-graph; stage explicit pathspecs; commit
"docs: record OpenWiki generation status and referrers", ending
Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Never touch CLAUDE.md, AGENTS.md, .github/**, src/**, or any generated page.
Ask-first files: none.
Stop and report if: the status sentence does not match exactly once; the index
regeneration changes a file outside docs/INDEX.md and docs/_link_graph.json;
`git diff --cached --name-only` shows anything else.
Do NOT spawn agents. Do NOT push.
Return: commit sha + subject, before/after of each edited line, gate outputs.
Output style: follow ~/.claude/rules/common/subagent-output.md (i-have-adhd)
```

## 7. Risks and open findings

| # | Finding | Evidence | Recurring-failures mode |
|---|---|---|---|
| 1 | Repository source leaves the machine to an LLM API (owner-run). Local-first covers product code paths, not this tool, but S-C2-1 must be explicit | `openwiki/README.md:27`; plan O-C2-1 | owner decision; not a product path |
| 2 | Whether the tool reads git-ignored files (`data/` vaults, `.env`) is UNVERIFIED; the clean-worktree step is the only control | plan `:1095` | #5 contaminated tree |
| 3 | `docs_lint.py` does not scan `openwiki/`; a green lint proves nothing about generated pages | `grep -n openwiki scripts/docs_lint.py` → 0 | #1 green check that cannot fail |
| 4 | Three statements go false at merge: `AGENT.md:20`, `00_architecture_plans_index.md:63` (S-C2-3), `CLAUDE.md:67` (no owner) | lines quoted in §2, §4 | #8 stale guidance |
| 5 | Generated pages will cite counts and line numbers that drift with every later phase | Task C2.2 Step 5 greps `[0-9]{3,5} (tests\|passing\|collected)` | #3 |
| 6 | W-10 changes the invariants while generated pages may restate the old text | `CLAUDE.md:60`, `:62` | #8: run G-C2 after W-10, or re-check Step 4 after W-10 merges |

Next action: ask the owner S-C2-1 (question 1); nothing else can start before it.
