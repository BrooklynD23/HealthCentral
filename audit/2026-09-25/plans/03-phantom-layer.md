# Phantom Agent/Hook Layer Reconciliation Plan

> **2026-09-27 corrections ([review follow-up](../review/2026-09-27-followup.md), F-10/F-17):** (1) The user-level count is **33** agent `.md` files, not 34. `find ~/.claude/agents -maxdepth 1 -type f -name '*.md' | wc -l` → `33`; there are no non-`.md` entries, and all 33 files are dated 2026-09-20, so the count was already 33 at audit time. 17 of them are `gsd-*`, not 13. The material result stands: none of the 5 claimed names exist. (2) `~/.claude/settings.json` registers PreToolUse hooks for continuous-learning and GSD only. The disabled `everything-claude-code` plugin's cache lists an `agentshield-pack` component, but no AgentShield hook is registered. (3) Research 02 §5.1 used to call Branch A "Branch-B" and mark it ADOPT. That text is now corrected to match this plan. The STOP gate below is unchanged, and the owner's answer on record is still "Not sure" (audit §21 Q2). (4) Branch A's `git add .gitignore .claude/agents/ …` is allowed only after `git status --short .claude/` shows the new agent files and nothing else (contract C-GATE-3). "~80% pre-built" is the plan author's estimate, not a measurement.

> **For agentic workers:** This is an investigation+decision plan, not an implementation plan. The deliverable is a STOP gate: present the evidence table to the owner, get an explicit "A" or "B", then execute only that branch. Do not edit `.gitignore`, `docs/`, or `CS4610_Report_Demo/` before the gate. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the contradiction between committed docs + CS4610 coursework that claim a `.claude/agents/` + hook enforcement layer, and a repo that contains neither — and whose `.gitignore` makes the agent layer impossible to commit today.

**Architecture:** One evidence table (claim | location | verdict) recording repo-side and user-level findings; then exactly one of two mutually exclusive remediation branches — **A:** make the claim true (author + commit real `.claude/agents/` definitions, un-ignore them), or **B:** make the docs true (correct claims; substantially pre-written in unmerged commit `7b2ff1f`).

**Evidence base:** `audit/2026-09-25/Devin-Audit-report.md` §8, §12, §15 items 3+7, §19, §20-Q2, §21-Q2, §22 item 3; owner-machine `~/.claude/` inspection (pre-verified 2026-09-25); repo-side greps/git-log recorded below.

## Global Constraints

- **STOP gate is binding.** Owner Q2 answer (audit §21) was "check `~/.claude/` and report before deciding commit-vs-doc-fix"; §22 work item 3: "Do not edit `.gitignore` or docs unilaterally."
- **Docs state only verifiable facts** — harness.md evidence rules: "no claim without a command." Authoring fictional agent configs to satisfy stale doc text is fabrication (the failure mode `7b2ff1f`'s commit message explicitly avoids, and recurring-failures territory: claims running ahead of evidence).
- **`.claude/*` is ignored by `.gitignore:44`**; only `!.claude/skills/` (line 45) is whitelisted. Verified: `git check-ignore -v .claude/agents/foo.md` → `.gitignore:44:.claude/*`. Committing anything else under `.claude/` requires an explicit un-ignore line.
- **CS4610 `.docx`/`.pdf` are submitted coursework — never rewrite report bodies.** Corrections live in `CS4610_Report_Demo/README.md` (precedent set by `7b2ff1f`).
- **Human merges** — orchestrator opens PRs and stops (repo convention, audit §22).
- Commit style: `docs:` / `fix(scope):` prefixes, single-purpose commits on a feature branch.

## Evidence table

| # | Claim (verbatim) | Location | Reality (repo + user level) | Verdict |
|---|---|---|---|---|
| 1 | "Subagent definitions live in `.claude/agents/`" + named agents `docs-consistency-scanner`, `dependency-policy-auditor`, `agentic-roadmap-researcher`, `verification-engineer` (read-only scanners, cheap models) and `windows-bootstrap-engineer` (specialist implementer) | `docs/agentic/harness.md:25-28` | `.claude/` contains only `skills/` (27 tracked files, all skills — `git ls-files .claude/`). `git log --all -- '.claude/agents'` → empty: **never committed on any branch**. `.gitignore:44` blocks the path. None of the 5 names exist among the 33 user-level (corrected 2026-09-27; was 34) `~/.claude/agents/` either. | **CONTRADICTED** |
| 2 | "orchestrator + scoped subagents (`.claude/agents/`)" and portfolio row "Agent orchestration \| `.claude/agents/`, harness.md" | `docs/agentic/roadmap.md:8`, `roadmap.md:15` | Same as #1 — the directory does not exist and cannot be committed under current `.gitignore`. `roadmap.md:38` "earlier subagent survey" is prose about a real July dispatch, not a file claim. | **CONTRADICTED** |
| 3 | "A PreToolUse hook scans for patterns that look like PHI and blocks any tool call that would send them to a network." | `CS4610_Report_Demo/HealthCentral_CS4610_Final_Report.docx` — "Skills and hooks as privacy enforcement" section | No hooks exist in the repo at all (no `.claude/settings.json`, no `hooks/`; audit §12 row: "Hooks — None"). User level: `~/.claude/settings.json` wires only continuous-learning `observe.sh` + `gsd-*.js`; grep for `agentshield\|phi\|redact\|hipaa` across settings.json and `hooks/*.js` → 0 hits. | **CONTRADICTED (repo); NOT-EVIDENCED (user level)** |
| 4 | "AgentShield was wired as a PreToolUse hook scanning every edit for PHI patterns; any tool call that would emit identifiable medical data onto a network interface is blocked before it runs." | `CS4610_Report_Demo/HealthCentral_CS4610_Technical_Companion.docx` — "AgentShield" section | AgentShield is real as a third-party scanner of the `everything-claude-code` (`affaan-m`) framework ("roughly 102 static rules", per the same doc). But it was never installed: `~/.claude/hooks/` holds only `gsd-check-update.js`, `gsd-context-monitor.js`, `gsd-prompt-guard.js`, `gsd-statusline.js`, `gsd-workflow-guard.js`, `statusline.js`; nothing in `settings.json` references it; zero repo hits outside the docx/pdf + audit. | **NOT-EVIDENCED — absent even at user level** |
| 5 | "hook-based secret scanning, a task tracker integrated with the planner subagent" | Final Report docx — harness-engineering paragraph | Partial user-level basis exists (`gsd-prompt-guard.js`, `gsd-context-monitor.js` hooks; a `planner` agent in `~/.claude/agents/`). Secret-scanning hook not evidenced; none of it is Asclexis-specific or committed. | **NOT-EVIDENCED as claimed** |
| 6 | A user-level agent/hook layer exists on the owner's machine | `~/.claude/` | VERIFIED: 33 agent `.md` files (re-counted 2026-09-27; plan said 34) — all generic ecosystem (gsd-*×17 per 2026-09-27 re-count — plan said ×13, ECC-style names like `code-reviewer`/`security-reviewer`/`tdd-guide`/`planner`/`architect`, `analytics-pm`, `data-scientist`, etc.); 6 hook scripts; settings.json hooks for GSD/continuous-learning only. **Zero Asclexis-specific agents; zero of the 5 claimed names; zero PHI enforcement.** | **VERIFIED — but generic, not the claimed layer** |
| 7 | The doc-correction is already written | commit `7b2ff1f` on `origin/claude/healthcentral-agentic-research-r1n54x` (2026-09-10) | Removes `.claude/agents/` claims from `harness.md`/`roadmap.md` (exact diff in Branch B below); creates `CS4610_Report_Demo/README.md` naming 5 aspirational coursework claims; adds `scripts/harness_drift_check.py` (path-token checker over `docs/agentic/*.md`, validated 62 tokens / 34 unique / 6 docs; **not CI-wired**). Branch merge already owner-approved (§21 Q3 — "merge both as-is"). | **VERIFIED — Branch B is ~80% pre-built** |

## Branch A — create and un-ignore `.claude/agents/` (make the claim true)

**Precondition:** owner wants named project subagents *going forward*. The 5 claimed names exist nowhere (not repo, not git history, not user level), so nothing can be rescued — every file below is authored new. Only author agents for roles with a demonstrated recurring need; do not fabricate a roster to match the old doc text. Recommended subset (3 of 5 — these map to real, repeated dispatch patterns; `agentic-roadmap-researcher` and `dependency-policy-auditor` have no evidenced repeat use — defer until they do).

**Sequencing:** execute AFTER `claude/healthcentral-agentic-research-r1n54x` merges (it removes the false claim text; Branch A re-adds a now-true reference in A5).

- [ ] **A1: Un-ignore `.claude/agents/`**

File: `.gitignore` — after line 45 (`!.claude/skills/`), add:

```gitignore
!.claude/agents/
```

Verify:

```bash
git check-ignore -v .claude/agents/docs-consistency-scanner.md ; echo "exit=$?"
```

Expected: no match output, `exit=1` (path no longer ignored).

- [ ] **A2: Author `.claude/agents/docs-consistency-scanner.md`**

```markdown
---
name: docs-consistency-scanner
description: Read-only doc-vs-code contradiction hunter. Use to verify that paths, file names, counts, and commands quoted in docs/, README.md, CLAUDE.md, AGENT.md resolve against the repo.
tools: Read, Grep, Glob, Bash
model: haiku
---

You are a read-only consistency scanner for the Asclexis repo.

- For every backtick-quoted path, filename, count, or command in the target docs, verify it against the working tree. `scripts/harness_drift_check.py` (once merged) already covers path-shaped tokens in docs/agentic/*.md — cover everything it skips: numbers, names, commands, other directories.
- Return a table only: claim | file:line | evidence command | MATCH/STALE/BROKEN. No edits, no fixes, no recommendations.
- Never open files under data/, profiles/, *.db, or .env* — patient data is not survey material.
```

- [ ] **A3: Author `.claude/agents/verification-engineer.md`**

```markdown
---
name: verification-engineer
description: Evidence runner. Use to execute a stated verification command list (pytest, tsc, vitest, lint scripts) and return raw output for orchestrator review.
tools: Read, Grep, Glob, Bash
model: sonnet
---

You run verification commands and report output verbatim.

- Run exactly the commands you are given, in order. Report command | exit code | key output lines (full output for failures).
- Never modify files. Never "fix" a failure — report it. A known env-only failure is `test_api_rag_index_002b` (no local embedding model); report it, do not work around it.
- WSL/9p: clear `__pycache__` before pytest if told the tree is on /mnt/c; frontend toolchain runs on Windows, not here — say so instead of attempting it.
```

- [ ] **A4: Author `.claude/agents/windows-bootstrap-engineer.md`**

```markdown
---
name: windows-bootstrap-engineer
description: Specialist implementer for dev.ps1 / Windows bootstrap work (HC-M02 line). Use only when the patch surface is a single bootstrap/packaging file set.
tools: Read, Grep, Glob, Bash, Edit
model: sonnet
---

Bounded-scope implementer for the Windows bootstrap path (dev.ps1 and adjacent packaging scripts).

- Scope limit: dev.ps1, scripts/download_models.py, packaging/installer files. Refuse edits outside it — hand back a scope note instead.
- dev.ps1 is the canonical bootstrap; keep its auto-port-selection and winget fallback behavior intact.
- PowerShell is the target shell — test mentally against PowerShell semantics, not bash.
```

- [ ] **A5: Re-true the docs post-merge**

File: `docs/agentic/harness.md` — the merged text (from `7b2ff1f`) reads "No subagent definitions are checked into this repo — there is no agents directory under `.claude/` — every subagent dispatch here is ad hoc, used to keep exploration noise out of the main context:". Replace that sentence's prefix with:

```markdown
Subagent definitions live in `.claude/agents/` (`docs-consistency-scanner`, `verification-engineer`, `windows-bootstrap-engineer`). Use them to keep exploration noise out of the main context:
```

File: `docs/agentic/roadmap.md:15` — change the portfolio row back to `` `.claude/agents/` `` only if all three files above are committed in the same PR.

- [ ] **A6: Verify + commit**

```bash
python3 scripts/docs_lint.py
python3 scripts/harness_drift_check.py   # exists after the branch merge
git status --short .claude/
git add .gitignore .claude/agents/ docs/agentic/harness.md docs/agentic/roadmap.md
git commit -m "feat(harness): commit real .claude/agents definitions and un-ignore the directory"
```

Expected: `git status` shows the 3 new agent files as addable; drift check clean.

## Branch B — correct the docs (make the docs true)

`7b2ff1f` on `claude/healthcentral-agentic-research-r1n54x` already performs most of this branch; that branch's merge is independently owner-approved (§21 Q3, work item 1). This branch = land it, verify the correction landed, add the Sep-25 user-level finding, and consider CI-wiring the drift check.

- [ ] **B1: Land `claude/healthcentral-agentic-research-r1n54x`** (per audit §22 work item 1 — shared with the merge workstream; do not duplicate). After merge, verify the corrected text is on main:

```bash
grep -n "claude/agents" docs/agentic/harness.md docs/agentic/roadmap.md
grep -n "No subagent definitions are checked in" docs/agentic/harness.md
ls CS4610_Report_Demo/README.md scripts/harness_drift_check.py
```

Expected: first command → no `.claude/agents/` path claims remain (any hit is a regression to fix); second → present; third → both files exist.

- [ ] **B2: Update `CS4610_Report_Demo/README.md` with the user-level finding**

The merged file's first bullet reads "**A `PreToolUse` hook ("AgentShield") that scans tool calls for PHI and blocks network-bound calls** — Final Report §7.2, Technical Companion §4.6. No hook mechanism and no `.claude/settings.json` exist in this repo at all." Append after "...exist in this repo at all.":

```markdown
A 2026-09-25 check (re-counted 2026-09-27) of the development machine's
user-level `~/.claude/` found 33 generic ecosystem agents and
GSD/continuous-learning hooks, but no active AgentShield hook and no
PHI-scanning hook — the claim is not merely uncommitted, it is not active at
any level. (A disabled plugin's cache lists an `agentshield-pack` component;
no hook from it is registered in `~/.claude/settings.json`.)
```

- [ ] **B3: Re-check remaining claim sites** (execution-time sweep — catches anything this plan's evidence grep missed)

```bash
grep -rn "\.claude/agents\|AgentShield\|PreToolUse" docs/ README.md CLAUDE.md AGENT.md CONTRIBUTING* 2>/dev/null
```

Expected: only historical/audit mentions (this plan, `Devin-Audit-report.md`, archive docs clearly marked historical). `docs/agentic/progress.md` and `docs/agentic/recurring-failures.md` matched a broad `subagent` grep during investigation — confirm they are dispatch prose, not file claims, and leave them.

- [ ] **B4: Decide CI wiring for `scripts/harness_drift_check.py`**

It landed un-wired (`7b2ff1f` notes "Not wired into CI"). Options: add to the docs_lint step in `.github/workflows/ci.yml`, or leave manual. Recommend wiring it — audit §13 shows drift clusters exactly where no gate runs. If wiring, it is a separate `fix(ci):` commit with its own run evidence.

- [ ] **B5: Commit the README update + log**

```bash
git add CS4610_Report_Demo/README.md
git commit -m "docs: record user-level absence of AgentShield/PHI hook in CS4610 scope note"
```

Log one line in `docs/features/TASK_LIST.md` Session Notes.

## Recommendation: Branch B

1. **There is nothing to commit.** The 5 named agents exist in zero locations — not repo, not git history (`git log --all -- '.claude/agents'` is empty), not even user-level (none of the 5 names among the 33 `~/.claude/agents/` files). Branch A would mean inventing a roster to retroactively satisfy doc text — the fabrication `7b2ff1f` explicitly refused.
2. **B is already written; only the branch *merge* is owner-approved** (§21 Q3, agent-recorded). Choosing B over A is still the owner's call (§21 Q2 "Not sure"; corrected 2026-09-27). `7b2ff1f` lands the harness.md/roadmap.md corrections plus a `CS4610_Report_Demo/README.md` scope note naming all five aspirational claims; the branch merge is approved work item 1. Branch B adds only the Sep-25 user-level sentence (B2).
3. **Research integrity is itself the Part-2 artifact.** Audit §19 lists "the phantom layer" and "CS4610 report vs repo" as research opportunities — an honest claims-vs-committed-artifacts scope note is worth more to the course narrative than a retrofitted `.claude/agents/` that exists only to erase the discrepancy.
4. **The product loses nothing.** Ad hoc dispatch carried 67% of commit authorship; named agents add real value only when a role repeats — and when one does, Branch A's `.gitignore` line plus one `.md` file is a 10-minute task (A1–A4 are written and waiting).

Branch A stays available as a fast-follow if the owner wants committed subagents for real future use — but it must be justified by future use, not by the old claim.

## STOP gate

**Report to owner before any edit:**

1. User level: `~/.claude/agents/` = 33 generic (re-counted 2026-09-27) ecosystem agents (gsd-*, ECC-style reviewers); none of the 5 names harness.md claims; `~/.claude/` hooks = GSD/learning/statusline only — **no AgentShield, no PHI hook anywhere**.
2. Repo level: `.claude/agents/` never committed on any branch; `.gitignore:44` blocks it; only `skills/` is whitelisted.
3. `7b2ff1f` (already-approved branch) already implements ~80% of Branch B including the coursework scope note.
4. Recommendation: **B** — land the correction, add the user-level finding, keep A's task list on file.

**Owner replies A or B → execute only that branch's checkboxes.**
