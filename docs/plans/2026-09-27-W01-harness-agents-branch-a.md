# W-1 — Commit the Five Named Subagents (Plan 03, Branch A) Implementation Plan

**Last Updated:** 2026-09-27
**Owner:** repository owner
**Refresh Trigger:** P1 lands on main (re-verify every `B@`/`A@` line below), or the owner changes D1 / D1-scope, or Claude Code changes subagent frontmatter semantics
**Status:** PROPOSED — not executed
**Review status:** 4 Codex rounds; round-4 findings fixed after the last round, not re-reviewed (owner acceptance required).
**Prerequisites:** P0-B and P1 merged to `origin/main`; the D9 Python 3.11 venv built at `$HOME/venvs/asclexis-311`. If Task 0 Step 1's ancestry check fails because P1 has not landed, that is the intended STOP, not a defect.

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the `docs/agentic/harness.md` claim true going forward. Author the five named subagent definitions under `.claude/agents/`, un-ignore only that directory, pin every tool list with tests, and re-word the docs that commit `7b2ff1f` corrected, so they describe what now exists.

**Architecture:** There are five Markdown files with YAML frontmatter. Four are read-only scanners (`tools: Read, Grep, Glob`, model `haiku`). One is a bounded implementer (`tools: Read, Grep, Glob, Edit`, model `opus`, with a declared `write_scope` of `dev.ps1` and `dev.bat`). One new pytest file under `src/backend/tests/` pins these points:

- the `.gitignore` un-ignore, and that it stays narrow;
- the file set;
- frontmatter parsing;
- the tool lists and the declared scope;
- body/frontmatter consistency, including the patient-data dispatch boundary.

Those are HC-AGENTS-001…007, which are collected in the backend suite. HC-AGENTS-008 is a manual gate command, not a collected test. It checks that harness.md names every agent by its full path and that `scripts/harness_drift_check.py` exits 0; its output goes in the PR. Moving it into the backend suite is Task 9, which runs only after owner sign-off OG-3. The docs are re-worded to name each agent by its full path, so the drift check verifies each file.

**Tech Stack:** Claude Code project subagents (`.claude/agents/*.md`), git ignore rules, pytest 3.11 (D9 venv), PyYAML (`yaml.safe_load`), the stdlib-only `scripts/harness_drift_check.py` (branch B).

**Spec:** [handoff §5, row W-1](../../audit/2026-09-25/handoff-2026-09-27-execution.md) · [owner decisions D1 / D1-scope / Consequence #2](../capstone-report/owner-decisions-2026-09-27.md) · [plan 03 (superseded scope)](../../audit/2026-09-25/plans/03-phantom-layer.md) · [program P3](../capstone-report/implementation-program.md) · [matrix GATE-09](../capstone-report/specs-compliance-matrix.md) · [claims ledger H5/H6](../capstone-report/claims-ledger.md)

**Ref labels:** `main@40f590e` = current `origin/main`. `B@7b2ff1f` = `origin/claude/healthcentral-agentic-research-r1n54x`. `A@692fdf3` = `origin/claude/asclexis-repo-audit-349pjq`. `pkg@2026-09-27` = the capstone package, untracked on main until P0-B commits it. Every `path:line` below was read on 2026-09-27 at the ref shown. **The executor re-verifies each one on the post-P1 tree (Task 0) before editing.**

---

## Approval scope

**Owner-approved (verbatim, [owner-decisions-2026-09-27.md](../capstone-report/owner-decisions-2026-09-27.md), table rows D1 and D1-scope):**

> **D1** — Phantom agent layer (plan 03) — **A: build real agents** — "Author ~3 read-only agent definitions, unignore .claude/agents/ in .gitignore, commit them. More work; turns the claim true going forward." The scope was then widened by the D1-scope answer below.

> **D1-scope** — How many agents — **All 5 claimed agents** — "Author all five named in harness.md, including windows-bootstrap-engineer (bounded write) and agentic-roadmap-researcher."

> **Consequence #2** — "The D1 choices differ from plan 03's recommendation. Plan 03 Branch A scoped 3 agents and warned against authoring a roster just to match old text. The owner chose all 5, including a write-capable `windows-bootstrap-engineer`. A new plan is needed: bounded write scope in frontmatter, read-only tools for the other 4, and a harness drift check that passes."

**This licenses:** five `.claude/agents/<name>.md` files with the names in `main@40f590e docs/agentic/harness.md:27-28`. Four are read-only. `windows-bootstrap-engineer` has a bounded write scope declared in its frontmatter. `.gitignore` gains `!.claude/agents/`. The files are committed, and the docs are re-worded so that the claim is true.

**Does NOT license** (each item is owner-gated; the unsigned lines are under [Owner sign-offs](#owner-sign-offs)):

1. **Any hook.** This covers a repo `.claude/settings.json` hook, a `hooks:` key in agent frontmatter, and an AgentShield/PHI `PreToolUse` hook. D1 covers agents only. Claims-ledger H6 stays `NOT-EVIDENCED`. `CS4610_Report_Demo/README.md` (`B@7b2ff1f:13`, "No hook mechanism and no `.claude/settings.json` exist in this repo at all") must stay true. HC-AGENTS-002 pins that.
2. **Un-ignoring anything else under `.claude/`**, such as `settings.json`, `settings.local.json`, `hooks/` or `commands/`.
3. **A write-capable tool for any of the 4 scanners.** This includes `Bash` and `PowerShell`, which the Claude Code docs describe as able to "include write operations". A `verification-engineer` that runs tests would need `Bash`, so it would no longer be read-only. See owner gate OG-2.
4. **More tools for the implementer:** `Write`, `Bash`, `PowerShell` or `NotebookEdit` for `windows-bootstrap-engineer`, or any write path beyond `dev.ps1` / `dev.bat` (OG-4).
5. **The drift check in CI in any form.** That covers both a `ci.yml` step and HC-AGENTS-008 inside the collected backend suite. By default HC-AGENTS-008 is a manual gate recorded in the PR. Task 9 moves it into the suite only after OG-3 is signed.
6. **Edits to the coursework `.docx`/`.pdf`**, to `docs/research/2026-09-08/*` (dated evidence), or to `docs/plans/2026-09-10-implementation-roadmap.md` (a dated plan).
7. **Any agent editing, or proposing a patch to, an ask-first file:** `modules/interpret_safety.py`, `modules/redaction.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`, and anything auth or encryption (including `core/auth.py`). CLAUDE.md §1's ask-first rule governs edits. Reading those files is not touching them, so the read-only agents may read them (for example, `dependency-policy-auditor` scans all of `src/backend/`). Any finding that would need a change there must be labelled "ASK-FIRST: owner approval required before any edit". HC-AGENTS-007 checks that every body carries the ask-first list and that label rule.
8. **`mcpServers`, `permissionMode`, `isolation`, `memory` or `skills` keys** in agent frontmatter. HC-AGENTS-004 pins an allow-list of keys.
9. **Any edit to `scripts/harness_drift_check.py` or its tests.** D1 does not license checker edits, and weakening a check to make it pass is forbidden (CLAUDE.md §3). A drift failure on the post-P1 tree belongs to P1 (Task 0 Step 3 STOP gate).
10. **Enforceable read-deny rules:** a committed `.claude/settings.json` with `permissions.deny` for patient-data paths. That is OG-5. The patient-data boundary in this plan is dispatch from a fresh source-only worktree, which a command checks and review enforces.

---

## Traceability

| Kind | ID | Verified text (grep, 2026-09-27) |
|---|---|---|
| Handoff §5 | W-1 | `audit/…/handoff-2026-09-27-execution.md:138`: "`.claude/agents/` with the 5 names in `docs/agentic/harness.md:25-28`. 4 are read-only (`tools: Read, Grep, Glob`). `windows-bootstrap-engineer` gets a bounded write scope declared in frontmatter. `.gitignore` gets `!.claude/agents/`. Drop no other claim silently \| GATE-09 \| (1) `git check-ignore .claude/agents/x.md` → not ignored. (2) Each file's frontmatter parses, and the 4 scanners list no write tools. (3) `scripts/harness_drift_check.py` (from branch B) exits 0 \| 5 files committed; drift check exit 0; harness/roadmap claims true" |
| Program phase | P3 | `pkg implementation-program.md:169`: "## P3 — Phantom-layer decision (plan 03) · OWNER → DOCS or CONFIG". Acceptance at `:180`: "zero doc references to non-existent agents or hooks (drift check exits 0), and the claims ledger H5/H6 are updated." |
| Matrix row | GATE-09 | `pkg specs-compliance-matrix.md:143`: "\| GATE-09 \| Agent/hook harness claims match committed artifacts \| `docs/agentic/harness.md:25-28` \| `.claude/agents/` absent; `.gitignore:44` blocks it; no repo hooks \| none on main … \| **contradicted** \| **owner-gated** (plan 03, §21 Q2 "Not sure") \|" |
| Matrix row | GATED-06 | `pkg specs-compliance-matrix.md:156`: "\| GATED-06 \| `.claude/agents/` + hooks (A vs B) \| "Not sure" (§21 Q2) \| absent at every level \| plan 03 \|" (stale since D1; see Task 6) |
| Contract | C-GATE-1 | `pkg architecture-engineering-contract.md:340` "**C-GATE-1 · BINDING.**": measured counts, with interpreter named. |
| Contract | C-GATE-3 | `:360` "**C-GATE-3 · BINDING.**": "A directory pathspec is allowed only when `git status --short <dir>` shows task-owned changes and nothing else." |
| Contract | C-GATE-4 | `:367` "**C-GATE-4 · BINDING.**": "Docs changes MUST pass `python3 scripts/docs_lint.py`." |
| Contract table | `.claude/agents/` row | `:383`: "\| `.claude/agents/` \| Research 02 said ADOPT the five agents; plan 03 recommends B (fix docs) \| **Neither; owner-gated** \|…" (stale since D1; see Task 6) |
| Claims ledger | H5, H6 | `pkg claims-ledger.md:45-46` (quoted in Task 6) |

No product contract (C-LOCAL/ISO/KEY/…) applies. This plan changes no product code path. No contract C-ID exists for the agent harness itself; GATE-09 is the governing row.

---

## Global constraints

- Target Python 3.11 (CLAUDE.md invariant). The phase-gate interpreter is `~/venvs/asclexis-311/bin/python` (D9).
- Each of the 5 names matches its file stem and its frontmatter `name:` field exactly: `docs-consistency-scanner`, `dependency-policy-auditor`, `agentic-roadmap-researcher`, `verification-engineer`, `windows-bootstrap-engineer` (`main@40f590e docs/agentic/harness.md:27-28`).
- For scanners, `tools` is exactly `Read, Grep, Glob`, with no other tool (handoff W-1).
- Agent bodies describe only what the tool list allows. This is plan 03's warning, and program C-GATE-1 in spirit: no fabricated capability.
- **Patient-data boundary.** All five agents are dispatched only from a fresh source-only `git worktree`. Before each dispatch, the `phi_gate` shell function (defined verbatim in Task 5 Step 3 and Task 7 Step 1) must exit 0. It exits 1 and prints each match when it finds any of the following, and it also exits 1 if `find` itself fails. The gate looks for the `data` and `src/backend/data` directories, and for any `*.db`, `*.db-wal`, `*.db-shm` or `.env` file anywhere in that worktree. Local patient data lives in exactly those gitignored places: `core/config.py:37` (`B@7b2ff1f`) sets `sqlite_database_path = "data/asclexis.db"`, relative to where the backend runs. At B, 0 tracked files match these patterns, so a fresh worktree passes the gate. Claude Code does not stop `Read` opening those paths (F3). The boundary is the gate plus review, and OG-5 is the enforceable option.
- Stage with explicit pathspecs only. Never `git add -A` or `git add .` (C-GATE-3).
- CS4610 `.docx`/`.pdf` are never edited. Corrections go in `CS4610_Report_Demo/README.md`.
- Humans merge. The phase ends at a PR.

## Facts about Claude Code this plan relies on

Source: Claude Code sub-agents documentation, `https://code.claude.com/docs/en/sub-agents`. A docs-lookup subagent retrieved it on 2026-09-27. **This is a lead, not a finding: Task 0 Step 5 re-reads it.**

| # | Fact (as retrieved) | Where the plan depends on it |
|---|---|---|
| F1 | Only `name` and `description` are required. `tools` accepts a comma-separated string or a YAML list. | frontmatter shape; HC-AGENTS-004 |
| F2 | "If `tools` is omitted, the subagent inherits every tool available to subagents in the main conversation." | HC-AGENTS-004 fails when `tools` is missing |
| F3 | The `tools` field does not accept path-scoped specifiers such as `Edit(dev.ps1)`. "For conditional rules, use `hooks` instead." | the write scope cannot be enforced by frontmatter alone |
| F4 | "Claude Code ignores unrecognized fields without reporting an error." | `write_scope:` is declarative: the harness reads it, Claude Code does not |
| F5 | `Bash` and `PowerShell` "can include write operations". The write-capable tools are `Write`, `Edit`, `NotebookEdit`, `Bash` and `PowerShell`. | scanners get no shell; the implementer gets no shell |
| F6 | Frontmatter `hooks:` (PreToolUse/PostToolUse/Stop) run only while that subagent is active. | the only real path enforcement; out of scope (OG-1) |

### How the write bound on `windows-bootstrap-engineer` is actually enforced

The bound is declarative plus review. The layers are:

1. **Structural (Claude Code enforces it, F2/F5).** The tool list is `Read, Grep, Glob, Edit`. With no `Write`, `Bash`, `PowerShell` or `NotebookEdit`, the agent cannot create files, delete files or run commands. `Edit` changes existing files only.
2. **Declarative (not enforced, F3/F4).** `write_scope: [dev.ps1, dev.bat]` sits in the frontmatter, and the body repeats it. Claude Code ignores the key. `Edit` can still reach any existing file in the repo.
3. **Review (the actual bound on paths).** After every dispatch of this agent, the orchestrator runs `git diff --name-only` and rejects the result unless the output is a subset of `{dev.ps1, dev.bat}`. That rule is written into `harness.md` (Task 5).
4. **Test (pins the declaration, not the behaviour).** HC-AGENTS-006 checks four things:
   - the declared scope is exactly `["dev.ps1", "dev.bat"]`;
   - both files exist;
   - the body restates both paths;
   - the tool list is exactly `Read, Grep, Glob, Edit`.

   It cannot see what the agent does at runtime.
5. **Optional, owner-gated (OG-1).** A frontmatter `PreToolUse` hook matching `Edit` could deny any path outside the scope. That would be real enforcement. It adds a hook, which D1 does not license, and it would falsify the CS4610 README's "no hook mechanism" line. So it is not in this plan.

## Review focus

These are the failure modes no automated test here exercises, most likely first:

1. **`windows-bootstrap-engineer` edits a file outside `dev.ps1`/`dev.bat`** through `Edit`. The fix is the `git diff --name-only` review rule (Task 5 text) and the Task 7 manual smoke.
2. **Claude Code parses the frontmatter differently from PyYAML.** For example, it might not load the agent at all, or it might grant more tools. Task 7 checks with `/agents` and a write attempt, recorded as a transcript excerpt.
3. **An agent is dispatched from a checkout that holds patient data**, such as the owner's main checkout with its `data` directory and `*.db` files. `Read` cannot be path-scoped (F3). The boundary is dispatch from a fresh source-only worktree. That boundary is stated in every agent body and in harness.md, checked by the `phi_gate` exit code before each dispatch, and exercised in the Task 7 smoke, where each pattern is planted once to show the gate fires. Nothing in Claude Code enforces it; OG-5 would.
4. **A later doc names an agent by bare name only.** The drift check skips tokens that have no extension or trailing slash (`B@7b2ff1f scripts/harness_drift_check.py:63-74`). The HC-AGENTS-008 manual gate checks full paths in `harness.md` only.
5. **An editor adds a UTF-8 BOM or CRLF to an agent file on Windows.** The parser uses `splitlines()` (CRLF-safe). A BOM makes line 1 `"﻿---"`, so HC-AGENTS-004 fails loudly rather than silently, which is the desired result.

---

## Files

**Create (task-owned):**
- `.claude/agents/docs-consistency-scanner.md`
- `.claude/agents/dependency-policy-auditor.md`
- `.claude/agents/agentic-roadmap-researcher.md`
- `.claude/agents/verification-engineer.md`
- `.claude/agents/windows-bootstrap-engineer.md`
- `src/backend/tests/test_claude_agent_definitions.py` (HC-AGENTS-001…007; Task 9 appends 008 only after OG-3)

**Modify (task-owned):**
- `.gitignore`: one line after `!.claude/skills/` (`main@40f590e:45`, `B@7b2ff1f:45`).
- `docs/agentic/harness.md`: `B@7b2ff1f:25-27` ("Subagent rules" opening and first bullet).
- `docs/agentic/roadmap.md`: `B@7b2ff1f:10` and `:17`.
- `CS4610_Report_Demo/README.md`: `B@7b2ff1f:20-23`.
- `docs/capstone-report/claims-ledger.md`: rows H5 and H6 (`pkg:45-46`).
- `CLAUDE.md` and `AGENT.md`: **only the collected-count slots**, and only in the commits that change collection (C1, and C4 if Task 9 runs). CLAUDE.md requires them to be updated "in the same commit". **This is a declared collision** (see [shared-file ordering](#shared-file-ordering)). The baseline-sentence rule:
  - In CLAUDE.md's "Baseline:" bullet (`B@7b2ff1f CLAUDE.md:29-35`), replace the number in "**N backend tests collected.**" and in "if it differs from N".
  - In AGENT.md's backend-test comment (`B@7b2ff1f AGENT.md:76`), replace only the number in "N collected".
  - Do **not** touch the pass-count wording: "all N pass" in CLAUDE.md, and "N pass in CI, N-1 without an embedding model" in AGENT.md. Update those only with a pass count measured in a named environment (interpreter, plus embedding model present or absent). Otherwise leave them and flag them in the PR as not re-measured. Never write a collected number into a pass-count slot.
- This plan file: the "Execution record" section only.

**Modify (conditional on orchestrator confirming no concurrent owner; otherwise report in the PR body per handoff §6 item 3):**
- `docs/capstone-report/specs-compliance-matrix.md`: rows GATE-09 and GATED-06.
- `docs/capstone-report/architecture-engineering-contract.md`: the `.claude/agents/` row of "Proposals and owner gates, reconciled".

**Read-only (never edited by this plan):**
- Ask-first surfaces: `src/backend/modules/interpret_safety.py`, `modules/redaction.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`, `core/auth.py`, anything auth or encryption.
- `dev.ps1`, `dev.bat`. The new agent may be dispatched on them later, but this plan changes neither.
- `scripts/harness_drift_check.py`, `src/backend/tests/test_harness_drift_check.py`, `docs/agentic/recurring-failures.md`. These arrive with P1 and are never edited here (Does NOT license #9).
- `.github/workflows/ci.yml`, `src/backend/requirements.txt`, `CS4610_Report_Demo/*.docx|*.pdf`, `docs/research/**`, `docs/plans/2026-09-10-implementation-roadmap.md`, `docs/features/TASK_LIST.md`, `docs/agentic/progress.md`, `docs/INDEX.md` and `docs/_link_graph.json`. For the last two, see the Task 8 stop gate.

### Shared-file ordering

| File | Other writers | Rule |
|---|---|---|
| `.gitignore` | P1 (branch B appends LibreOffice lock lines at `B@7b2ff1f:134-137`) | P1 first. This plan inserts after `:45`, which is a separate hunk. |
| `docs/agentic/harness.md`, `roadmap.md` | P1 brings `7b2ff1f`. Plan 04 Task 15 verifies after P3. | P1 → **P3 (this)** → P4. Plan 04 Task 15 must use the post-P3 checks in Task 8 Step 6. |
| `CS4610_Report_Demo/README.md` | P1 creates it (`7b2ff1f`) | P1 → P3 |
| `scripts/harness_drift_check.py`, `tests/test_harness_drift_check.py`, `docs/agentic/recurring-failures.md` | P1 (branch B creates them; plan 01 resolves the A/B conflict in `recurring-failures.md`) | P1 only. This plan reads and runs them and never edits them. A non-zero drift check on the post-P1 tree is a P1 acceptance failure (Task 0 Step 3 STOP). |
| `CLAUDE.md`, `AGENT.md` baseline lines | P1, P2, P4, P5, and every test-adding phase. W-10 owns CLAUDE.md governance text. | **Collision.** Edit only the count lines, never concurrently. If W-10's governance commit is in flight, stop and sequence with the orchestrator. |
| `docs/capstone-report/claims-ledger.md`, `specs-compliance-matrix.md`, `architecture-engineering-contract.md` | P0-B commits them; other W-plans may update rows | Edit only rows H5/H6 (and GATE-09/GATED-06/table row after confirmation), never concurrently. |

### Dependencies

- **P0-B** is landed: the `docs/capstone-report/` package is committed, so ledger edits have a tracked base.
- **D9:** `~/venvs/asclexis-311` exists, and `import yaml` works in it. PyYAML comes transitively through `huggingface-hub` and `uvicorn[standard]`; it is not named in `requirements.txt`.
- **P1** is merged to main. It brings `B@7b2ff1f` (`harness_drift_check.py`, corrected harness/roadmap, the CS4610 README) and `A@692fdf3`.
- **D1 and D1-scope** are decided (quoted above).
- **Downstream:** P4 plan 04 Task 15 ("BLOCKED on plan-03") is unblocked when this PR merges.
- **Not a dependency:** P2 touches none of these files, so this plan may run beside P2 (program: "P3 … can run beside it once their inputs land").

---

## Task 0: Phase-start measurement and preconditions

**Files:** none modified. Record the results in the "Execution record" section of this plan.

**Shell convention for every block in this plan.** Each block sets `WT` (the absolute path of the phase worktree) and `PY` (the D9 interpreter) on its first line, and turns on `set -o pipefail`, so a `| tail` cannot hide a failing exit code. Directory changes are absolute (`cd "$WT/src/backend"`), never relative to an earlier `cd`. Exit codes that matter are echoed on the same line as the command.

- [ ] **Step 1: Create the phase worktree and prove it is post-P1** (recurring-failures #5)

```bash
set -o pipefail
REPO=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01
git -C "$REPO" fetch origin
git -C "$REPO" worktree add "$WT" -b feat/w01-harness-agents origin/main
cd "$WT"
git merge-base --is-ancestor 7b2ff1f HEAD && git merge-base --is-ancestor 692fdf3 HEAD && echo post-P1-ok
```

Expected: `post-P1-ok`. If it is not printed, **STOP**, because P1 has not landed.

- [ ] **Step 2: Interpreter and baseline suite**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
"$PY" --version
"$PY" -c "import yaml; print(yaml.__version__)"; echo "yaml_exit=$?"
cd "$WT/src/backend"
"$PY" -B -m pytest tests/ --collect-only -q -p no:cacheprovider | tail -1; echo "collect_exit=$?"
"$PY" -B -m pytest tests/ -p no:cacheprovider -q 2>&1 | tail -20; echo "suite_exit=$?"
```

Expected: `Python 3.11.x`, a PyYAML version with `yaml_exit=0`, and `collect_exit=0`. Record `START_COLLECTED` (the `N tests collected` line) and `START_FAILURES` (the exact test node IDs; `suite_exit` is `1` when that list is non-empty). If `import yaml` fails, **STOP**: adding PyYAML to `requirements.txt` touches a shared file and needs sequencing.

- [ ] **Step 3: Gate baselines, including the drift-check STOP gate**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT"
"$PY" scripts/harness_drift_check.py; echo "drift=$?"
"$PY" scripts/docs_lint.py; echo "lint=$?"
"$PY" scripts/generate_docs_index.py --check; echo "index=$?"
git check-ignore -v --no-index .claude/agents/x.md; echo "ignore=$?"
git log --all --oneline -- .claude/agents | wc -l
git grep -n -i "hc.agents" -- . ':!docs/plans/2026-09-27-W01-harness-agents-branch-a.md' | wc -l
git ls-files src/backend/tests | grep -ci "claude_agent"
```

Expected:
- `drift=0` and `Harness drift check passed.`
- `ignore=0`, printing `.gitignore:44:.claude/*	.claude/agents/x.md`.
- `0` commits touching `.claude/agents`.
- `0` hits for `hc.agents`, which covers both the `HC-AGENTS-` ID and the `hc_agents` `-k` selector substring. Checked 2026-09-27 on main, A and B: 0 hits for `HC-AGENTS|HC-AGT|HC-HARN|HC-SUBAG` and 0 for `hc_agents`.
- `0` existing test files matching `claude_agent`.

**STOP gate: `drift` is non-zero before any W-1 change.** Report the output to the orchestrator and stop. Do **not** edit `scripts/harness_drift_check.py` or its tests; weakening a check to pass is forbidden (CLAUDE.md §3), and D1 does not license checker edits. Do not reword another phase's doc to make it pass either. A clean drift check on the merged tree is P1 acceptance, and the orchestrator has added it there.

Known risk for P1, measured 2026-09-27: B's checker over B's tree exits 0. With `A@692fdf3`'s `recurring-failures.md` swapped in, it exits 1 with one error, `missing path '/profiles/'`. The token is `` `GET /profiles/` `` in A's SEC-RECOV-002 bullet (`A@692fdf3 docs/agentic/recurring-failures.md:33`), which plan 01 keeps ("Union — keep ALL four additions"). If P1 lands without resolving it, this gate fires.

- [ ] **Step 4: Verify the text this plan replaces is still what it quotes**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01; set -o pipefail
cd "$WT"
sed -n 25p docs/agentic/harness.md
sed -n '10p;17p' docs/agentic/roadmap.md
sed -n 20,23p CS4610_Report_Demo/README.md
sed -n 44,45p .gitignore
grep -n "^| H5 \|^| H6 " docs/capstone-report/claims-ledger.md
grep -n "Baseline: \*\*\|differs from\|all [0-9]* pass" CLAUDE.md; grep -n "collected;" AGENT.md
```

Expected:
- `harness.md:25` starts "No subagent definitions are checked into this repo".
- `roadmap.md:10` contains "ad hoc scoped subagents", and `:17` starts `| Agent orchestration | ad hoc subagent dispatch,` (followed by the harness.md link).
- `README.md:20` starts "- **Named subagent definitions under `.claude/agents/`**".
- `.gitignore:44-45` are `.claude/*` and `!.claude/skills/`.

If any line moved, re-derive the numbers. If any line's **text** differs, **STOP**.

- [ ] **Step 5: Re-verify the Claude Code facts F1–F6** by reading `https://code.claude.com/docs/en/sub-agents`. Record the quoted sentence for each fact. If F2, F3, F4 or F5 differs from the table above, **STOP**, because the tool design and the enforcement statement depend on them.

- [ ] **Step 6: Verify the command an agent body will quote** (recurring-failures #6)

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01
cd "$WT"
powershell.exe -NoProfile -Command '$errors = $null; $null = [System.Management.Automation.Language.Parser]::ParseFile((Resolve-Path ./dev.ps1).Path, [ref]$null, [ref]$errors); $errors.Count'
```

Expected: `0`. This was measured 2026-09-27 from WSL on `main@40f590e`, where `dev.ps1` is identical at B. It is the HC-M02 verification step ("PowerShell AST parse of dev.ps1 reports no errors", `feature_list.json`).

---

## Task 1: Un-ignore `.claude/agents/`, and only that

**Files:**
- Create: `src/backend/tests/test_claude_agent_definitions.py` (the helpers plus HC-AGENTS-001, 002)
- Modify: `.gitignore` (after `:45`)

**Interfaces:**
- Produces, for Tasks 2–4: the module constants `REPO_ROOT`, `AGENTS_DIR`, `SCANNERS`, `IMPLEMENTER`, `ALL_AGENTS`, and the helper `_git(*args: str) -> subprocess.CompletedProcess[str]`.

**Why a pytest file, not a standalone script:** the repo's tooling tests already live in `src/backend/tests/`: `test_docs_lint.py`, `test_harness_drift_check.py`, `test_repo_hygiene_check.py` and `test_security_gate.py` at B. CI job `backend-tests` runs them through `bash scripts/run-backend-tests.sh -q` (`B@7b2ff1f .github/workflows/ci.yml:33-52`). A standalone script would need a new step in `ci.yml`, a shared file sequenced P1 → P5 → G-B3/G-B4, which D1 does not cover. The ID prefix is `HC-AGENTS-NNN`.

- [ ] **Step 1: Write the test module header and the two failing/guard tests.** Create `src/backend/tests/test_claude_agent_definitions.py`:

```python
"""HC-AGENTS-001..007 — the five checked-in Claude Code subagent definitions.
(HC-AGENTS-008 is a manual gate; it is appended here only after owner sign-off OG-3.)

Owner decisions D1 / D1-scope (docs/capstone-report/owner-decisions-2026-09-27.md):
author all five subagents named in docs/agentic/harness.md, un-ignore
.claude/agents/, commit them. Four are read-only scanners; the fifth,
windows-bootstrap-engineer, has Edit plus a declared write scope.

These tests pin the *declaration*. Claude Code enforces the `tools` allowlist
at runtime. It does not enforce `write_scope`: unknown frontmatter keys are
ignored. That bound holds through the agent's instructions and the
orchestrator's `git diff --name-only` review (docs/agentic/harness.md).
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
AGENTS_DIR = REPO_ROOT / ".claude" / "agents"

SCANNERS = (
    "docs-consistency-scanner",
    "dependency-policy-auditor",
    "agentic-roadmap-researcher",
    "verification-engineer",
)
IMPLEMENTER = "windows-bootstrap-engineer"
ALL_AGENTS = SCANNERS + (IMPLEMENTER,)


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    """Run git in the repo root. Fails (never skips) without git: a skip would
    read as a pass for a test whose whole job is to say what git will track."""
    if shutil.which("git") is None:
        pytest.fail("git is required: these tests check what git will track")
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )


def test_hc_agents_001_agent_files_are_not_gitignored() -> None:
    """HC-AGENTS-001. `--no-index` matters: without it, check-ignore never
    reports a *tracked* path, so this would pass vacuously once committed.
    Exit 0 = ignored, 1 = not ignored, 128 = error."""
    still_ignored = [
        name
        for name in ALL_AGENTS
        if _git("check-ignore", "--no-index", "-q", f".claude/agents/{name}.md").returncode != 1
    ]
    assert still_ignored == [], f"still ignored by .gitignore: {still_ignored}"


def test_hc_agents_002_unignore_stays_narrow() -> None:
    """HC-AGENTS-002. Only .claude/agents/ (beside the existing .claude/skills/)
    is un-ignored. Settings and hooks stay ignored: D1 licenses no hook, and
    CS4610_Report_Demo/README.md states no .claude/settings.json exists."""
    must_stay_ignored = [
        ".claude/settings.json",
        ".claude/settings.local.json",
        ".claude/hooks/pre_tool_use.sh",
    ]
    exposed = [
        rel
        for rel in must_stay_ignored
        if _git("check-ignore", "--no-index", "-q", rel).returncode != 0
    ]
    assert exposed == [], f"un-ignore is too wide; now trackable: {exposed}"
```

(`importlib.util`, `sys` and `yaml` are used by Tasks 2 and 4.)

- [ ] **Step 2: Run and watch 001 fail, 002 pass**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT"
cd "$WT/src/backend" && "$PY" -B -m pytest tests/test_claude_agent_definitions.py -p no:cacheprovider -q; echo "pytest_exit=$?"
```

Expected: `1 failed, 1 passed`, with
`AssertionError: still ignored by .gitignore: ['docs-consistency-scanner', 'dependency-policy-auditor', 'agentic-roadmap-researcher', 'verification-engineer', 'windows-bootstrap-engineer']`.
HC-AGENTS-002 is a regression guard, so it passes now. Step 5 proves it can fail.

- [ ] **Step 3: Minimal implementation.** In `.gitignore`, insert one line directly after `!.claude/skills/` (line 45):

```gitignore
!.claude/agents/
```

- [ ] **Step 4: Run and watch both pass.** Run the Step 2 command. Expected: `2 passed`.

- [ ] **Step 5: Break it on purpose**
  1. Remove the new line. HC-AGENTS-001 fails listing all 5. Restore it.
  2. Change the new line to `!.claude/*`. HC-AGENTS-002 fails with `un-ignore is too wide; now trackable: ['.claude/settings.json', '.claude/settings.local.json', '.claude/hooks/pre_tool_use.sh']`. Restore it. Do **not** use `!.claude/` as the break: it re-includes only the directory entry, the children still match `.claude/*`, and both tests stay as they were. That was measured in the scratch simulation: 002 passed, 001 failed.

  Simulated 2026-09-27 in a scratch git repo built from `git archive` of B, with WSL `python3` 3.12, pytest 9.0.3 and `--noconftest`: 001 red with the exact message above, then green after the `.gitignore` line. Both break edits turn red. Also simulated: `check-ignore` exit 1 for `.claude/agents/x.md`, and exit 0 for `.claude/settings.local.json`.

*What would these tests fail to notice?* A global excludes file (`core.excludesFile`) on another machine. `--no-index` still honours it, so 001 would go red there, which is correct and loud. A different ignore pattern for a sixth agent file is covered by HC-AGENTS-003's exact file set.

(No commit yet. The commit happens after Task 4, so no commit leaves the suite red.)

---

## Task 2: Failing tests for the definitions (HC-AGENTS-003…007)

**Files:**
- Modify: `src/backend/tests/test_claude_agent_definitions.py` (append)

**Interfaces:**
- Consumes: `REPO_ROOT`, `AGENTS_DIR`, `SCANNERS`, `IMPLEMENTER`, `ALL_AGENTS`, `_git` (Task 1).
- Produces, for Task 4: `_load(name: str) -> tuple[dict, str]` and `_tools(meta: dict) -> list[str]`, plus the body lines the agent files must contain verbatim: `SCANNER_LIMIT_LINE`, `IMPLEMENTER_LIMIT_LINE`, `DISPATCH_LINE`, `ASK_FIRST_NO_PATCH`, `ASK_FIRST_LABEL`, each of `ASK_FIRST_PATHS` in backticks, and the `Tools: …` line.

- [ ] **Step 1: Append the constants, helpers and tests**

```python
READ_ONLY_TOOLS = {"Read", "Grep", "Glob"}
IMPLEMENTER_TOOLS = {"Read", "Grep", "Glob", "Edit"}
# Write-capable per the Claude Code sub-agents docs (Bash/PowerShell "can include
# write operations"). MultiEdit is listed defensively for older clients.
WRITE_CAPABLE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit", "Bash", "PowerShell"}
IMPLEMENTER_WRITE_SCOPE = ["dev.ps1", "dev.bat"]
ALLOWED_KEYS = {"name", "description", "tools", "model", "write_scope"}
SCANNER_MODEL = "haiku"
IMPLEMENTER_MODEL = "opus"
SCANNER_LIMIT_LINE = "You cannot edit files, run commands, or access the network."
IMPLEMENTER_LIMIT_LINE = "You cannot create files, run commands, or access the network."
DISPATCH_LINE = "Run only in a fresh source-only git worktree."
ASK_FIRST_PATHS = (
    "src/backend/modules/interpret_safety.py",
    "src/backend/modules/redaction.py",
    "src/backend/modules/faithfulness.py",
    "src/backend/modules/verifier_agent.py",
    "src/backend/core/auth.py",
)
ASK_FIRST_LABEL = "ASK-FIRST: owner approval required before any edit."
ASK_FIRST_NO_PATCH = "Never propose a patch to them."


def _split_frontmatter(path: Path) -> tuple[dict, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        pytest.fail(f"{path.name}: line 1 must be exactly '---' (no BOM)")
    try:
        end = lines.index("---", 1)
    except ValueError:
        pytest.fail(f"{path.name}: frontmatter has no closing '---' line")
    meta = yaml.safe_load("\n".join(lines[1:end]))
    if not isinstance(meta, dict):
        pytest.fail(f"{path.name}: frontmatter is not a YAML mapping")
    return meta, "\n".join(lines[end + 1 :])


def _load(name: str) -> tuple[dict, str]:
    path = AGENTS_DIR / f"{name}.md"
    if not path.is_file():
        pytest.fail(f"missing {path.relative_to(REPO_ROOT).as_posix()}")
    return _split_frontmatter(path)


def _tools(meta: dict) -> list[str]:
    raw = meta.get("tools")
    if raw is None:
        return []
    items = raw if isinstance(raw, list) else str(raw).split(",")
    return [str(item).strip() for item in items if str(item).strip()]


def test_hc_agents_003_exactly_the_five_named_agents_are_tracked() -> None:
    """HC-AGENTS-003. No extra file (a sixth agent, a README, an editor
    backup) and every file is in git's index — the drift check only sees disk."""
    expected = sorted(f"{name}.md" for name in ALL_AGENTS)
    on_disk = sorted(p.name for p in AGENTS_DIR.iterdir()) if AGENTS_DIR.is_dir() else []
    assert on_disk == expected
    tracked = sorted(_git("ls-files", "--", ".claude/agents").stdout.split())
    assert tracked == [f".claude/agents/{name}" for name in expected]


def test_hc_agents_004_frontmatter_parses_with_required_fields() -> None:
    """HC-AGENTS-004. A missing `tools` field is the dangerous case: Claude
    Code then grants the subagent every tool, including Edit/Write/Bash."""
    problems: list[str] = []
    for name in ALL_AGENTS:
        meta, body = _load(name)
        if meta.get("name") != name:
            problems.append(f"{name}: name field is {meta.get('name')!r}")
        description = meta.get("description")
        if not isinstance(description, str) or not description.strip():
            problems.append(f"{name}: description missing or empty")
        if "tools" not in meta or not _tools(meta):
            problems.append(f"{name}: no tools field - Claude Code would grant every tool")
        extra = sorted(set(meta) - ALLOWED_KEYS)
        if extra:
            problems.append(f"{name}: keys outside the approved scope: {extra}")
        if not body.strip():
            problems.append(f"{name}: empty body")
    assert problems == []


def test_hc_agents_005_scanners_are_read_only() -> None:
    """HC-AGENTS-005 (handoff W-1 test 2). Exactly Read, Grep, Glob; no write
    tool; the cheap model harness.md promises; no write scope."""
    problems: list[str] = []
    for name in SCANNERS:
        meta, _body = _load(name)
        tools = set(_tools(meta))
        if tools != READ_ONLY_TOOLS:
            problems.append(f"{name}: tools {sorted(tools)} != {sorted(READ_ONLY_TOOLS)}")
        if tools & WRITE_CAPABLE_TOOLS:
            problems.append(f"{name}: write-capable tools {sorted(tools & WRITE_CAPABLE_TOOLS)}")
        if meta.get("model") != SCANNER_MODEL:
            problems.append(f"{name}: model {meta.get('model')!r} != {SCANNER_MODEL!r}")
        if "write_scope" in meta:
            problems.append(f"{name}: a read-only scanner declares write_scope")
    assert problems == []


def test_hc_agents_006_bootstrap_engineer_scope_is_declared_and_bounded() -> None:
    """HC-AGENTS-006. Pins the declaration only: Claude Code does not enforce
    write_scope. No Write/Bash/PowerShell/NotebookEdit, so it cannot create
    files or run commands; Edit alone is the only write path."""
    meta, body = _load(IMPLEMENTER)
    assert set(_tools(meta)) == IMPLEMENTER_TOOLS
    assert meta.get("model") == IMPLEMENTER_MODEL
    assert meta.get("write_scope") == IMPLEMENTER_WRITE_SCOPE
    for rel in IMPLEMENTER_WRITE_SCOPE:
        assert (REPO_ROOT / rel).is_file(), f"write_scope names a missing file: {rel}"
        assert f"`{rel}`" in body, f"body does not restate write_scope entry {rel}"


def test_hc_agents_007_body_states_its_real_tools() -> None:
    """HC-AGENTS-007. The body (the subagent's system prompt) must state the
    same tool list as the frontmatter, the matching limit sentence, the
    patient-data dispatch boundary, and the ask-first list with its label rule
    (CLAUDE.md §1: read allowed, no patches, findings labelled ASK-FIRST), so a
    body cannot describe a capability its tools do not grant or drop a rule."""
    problems: list[str] = []
    for name in ALL_AGENTS:
        meta, body = _load(name)
        tools_line = f"Tools: {', '.join(_tools(meta))}."
        if tools_line not in body:
            problems.append(f"{name}: body lacks {tools_line!r}")
        limit = SCANNER_LIMIT_LINE if name in SCANNERS else IMPLEMENTER_LIMIT_LINE
        if limit not in body:
            problems.append(f"{name}: body lacks {limit!r}")
        if DISPATCH_LINE not in body:
            problems.append(f"{name}: body lacks {DISPATCH_LINE!r}")
        for rel in ASK_FIRST_PATHS:
            if f"`{rel}`" not in body:
                problems.append(f"{name}: ask-first list lacks {rel}")
            if not (REPO_ROOT / rel).is_file():
                problems.append(f"{name}: ask-first path missing on disk: {rel}")
        for rule in (ASK_FIRST_NO_PATCH, ASK_FIRST_LABEL):
            if rule not in body:
                problems.append(f"{name}: body lacks {rule!r}")
    assert problems == []
```

- [ ] **Step 2: Run and watch 003–007 fail**

Run the Task 1 Step 2 command. Expected: `5 failed, 2 passed`, with:
- 003: `AssertionError: assert [] == ['agentic-roadmap-researcher.md', 'dependency-policy-auditor.md', 'docs-consistency-scanner.md', 'verification-engineer.md', 'windows-bootstrap-engineer.md']`
- 004, 005, 007: `Failed: missing .claude/agents/docs-consistency-scanner.md`
- 006: `Failed: missing .claude/agents/windows-bootstrap-engineer.md`

*What would these tests fail to notice?*
- **004:** a key Claude Code rejects even though PyYAML accepts it (Review focus #2; Task 7).
- **005:** runtime tool grants from MCP or plugins. The allowlist should exclude them per F1/F2, but that is not tested; Task 7 checks it.
- **006:** any runtime edit outside the scope (Review focus #1).
- **007:** a dishonest sentence elsewhere in the body. Human review covers that: Task 4 Step 4 checklist.

---

## Task 3: Author the four read-only scanners

**Files:** create the four files below, exactly as written.

**Interfaces:**
- Consumes: the body lines pinned by HC-AGENTS-007 (`Tools: Read, Grep, Glob.`, `SCANNER_LIMIT_LINE`, `DISPATCH_LINE`, the ask-first paragraph), and the keys allowed by HC-AGENTS-004.

Every path a body names was checked to exist at `B@7b2ff1f` on 2026-09-27. The executor re-runs `ls` on each one (Step 5).

- [ ] **Step 1: Create `.claude/agents/docs-consistency-scanner.md`**

```markdown
---
name: docs-consistency-scanner
description: Read-only doc-versus-repo contradiction hunter for Asclexis. Use it to check that paths, file names, symbols, counts of files and config values quoted in docs/, README.md, AGENT.md and CLAUDE.md match the repository. Returns a findings table and makes no edits.
tools: Read, Grep, Glob
model: haiku
---

Tools: Read, Grep, Glob. You cannot edit files, run commands, or access the network.

Run only in a fresh source-only git worktree. Local patient data (the `data` directory, `*.db` files, `.env` files) is gitignored, so a fresh worktree does not contain it. Before dispatching you, the orchestrator runs the patient-data gate from `docs/agentic/harness.md` over that worktree and dispatches only if it exits 0. The gate exits 1 on any `data` or `src/backend/data` directory, any `*.db`, `*.db-wal` or `*.db-shm` file, or any `.env` file. That check is the boundary: Claude Code does not limit which paths Read can open. If a path under `data/` or `profiles/`, a `*.db`, `*.db-wal` or `*.db-shm` file, or a `.env` file shows up in your results anyway, do not open it. Stop and report UNSAFE-CHECKOUT.

Ask-first files (CLAUDE.md §1): `src/backend/modules/interpret_safety.py`, `src/backend/modules/redaction.py`, `src/backend/modules/faithfulness.py`, `src/backend/modules/verifier_agent.py`, `src/backend/core/auth.py`, and any other auth or encryption code. You may read them; reading is not editing. Never propose a patch to them. Label any finding that would need a change there with this exact text: ASK-FIRST: owner approval required before any edit.

You check documentation claims against the files in this repository.

1. Read the documents named in your task.
2. For each checkable claim (a path, a file name, a symbol, a count of files, a config value), find the evidence with Glob, Grep or Read.
3. Return one table: claim | doc:line | evidence (the pattern you used and what it matched) | MATCH, STALE, MISSING or CANNOT-CHECK.

Limits. State them instead of working around them:

- You cannot run commands, so you cannot confirm that a quoted command works or that a test count is right. Mark those CANNOT-CHECK and name the command the orchestrator should run.
- `scripts/harness_drift_check.py` already checks path-shaped tokens in `docs/agentic/*.md`. Spend your effort on what it skips: counts, names, commands, and docs outside `docs/agentic/`.
- Report only. Name the stale line; do not propose rewrites.
```

- [ ] **Step 2: Create `.claude/agents/dependency-policy-auditor.md`**

```markdown
---
name: dependency-policy-auditor
description: Read-only dependency-evidence scanner for Asclexis. Use it to compare declared version floors and dependency rules (Python 3.11, Node 22, local-first, ModelRunner-only inference) against the manifests, CI config and imports actually in the repository. Returns a findings table and makes no edits.
tools: Read, Grep, Glob
model: haiku
---

Tools: Read, Grep, Glob. You cannot edit files, run commands, or access the network.

Run only in a fresh source-only git worktree. Local patient data (the `data` directory, `*.db` files, `.env` files) is gitignored, so a fresh worktree does not contain it. Before dispatching you, the orchestrator runs the patient-data gate from `docs/agentic/harness.md` over that worktree and dispatches only if it exits 0. The gate exits 1 on any `data` or `src/backend/data` directory, any `*.db`, `*.db-wal` or `*.db-shm` file, or any `.env` file. That check is the boundary: Claude Code does not limit which paths Read can open. If a path under `data/` or `profiles/`, a `*.db`, `*.db-wal` or `*.db-shm` file, or a `.env` file shows up in your results anyway, do not open it. Stop and report UNSAFE-CHECKOUT.

Ask-first files (CLAUDE.md §1): `src/backend/modules/interpret_safety.py`, `src/backend/modules/redaction.py`, `src/backend/modules/faithfulness.py`, `src/backend/modules/verifier_agent.py`, `src/backend/core/auth.py`, and any other auth or encryption code. You may read them; reading is not editing. Never propose a patch to them. Label any finding that would need a change there with this exact text: ASK-FIRST: owner approval required before any edit.

You compare the repository's stated dependency policy with what its files declare.

Sources to read:

- Policy: `CLAUDE.md` (hard invariants), `docs/agentic/roadmap.md` (runtime baseline).
- Manifests: `src/backend/requirements.txt`, `src/frontend/package.json` (its `engines` field), `src/frontend/package-lock.json`.
- CI: `.github/workflows/ci.yml` (`python-version`, `node-version`).
- Bootstrap: `dev.ps1` (the Python version it looks for and installs).
- Waivers: `scripts/security_gate.py` (each waiver needs an owner and an expiry).

What to check and report:

1. Version floors agree across policy, manifests, CI and `dev.ps1`.
2. Imports of `llama_cpp` outside `src/backend/core/llm/` (inference must go through ModelRunner).
3. Network-capable imports (`httpx`, `requests`, `urllib`) in `src/backend/` outside `tests/`, each with file:line, for the orchestrator to judge against the local-first invariant.
4. Security-gate waivers whose expiry date has passed.

Return one table: rule | source file:line | evidence file:line | CONSISTENT, VIOLATION or CANNOT-CHECK.

Limits:

- You cannot run pip-audit, npm audit or bandit, and you cannot look up CVEs or latest versions. Those run in CI's security-scan job. Mark such questions CANNOT-CHECK.
- Report only. No edits, no upgrade advice.
```

- [ ] **Step 3: Create `.claude/agents/agentic-roadmap-researcher.md`**

```markdown
---
name: agentic-roadmap-researcher
description: Read-only idea and next-task scanner for Asclexis. Use it to find the next highest-priority pending work and candidate ideas grounded in the repository's own backlog, plans and research notes. Returns ranked candidates with source lines and makes no edits.
tools: Read, Grep, Glob
model: haiku
---

Tools: Read, Grep, Glob. You cannot edit files, run commands, or access the network.

Run only in a fresh source-only git worktree. Local patient data (the `data` directory, `*.db` files, `.env` files) is gitignored, so a fresh worktree does not contain it. Before dispatching you, the orchestrator runs the patient-data gate from `docs/agentic/harness.md` over that worktree and dispatches only if it exits 0. The gate exits 1 on any `data` or `src/backend/data` directory, any `*.db`, `*.db-wal` or `*.db-shm` file, or any `.env` file. That check is the boundary: Claude Code does not limit which paths Read can open. If a path under `data/` or `profiles/`, a `*.db`, `*.db-wal` or `*.db-shm` file, or a `.env` file shows up in your results anyway, do not open it. Stop and report UNSAFE-CHECKOUT.

Ask-first files (CLAUDE.md §1): `src/backend/modules/interpret_safety.py`, `src/backend/modules/redaction.py`, `src/backend/modules/faithfulness.py`, `src/backend/modules/verifier_agent.py`, `src/backend/core/auth.py`, and any other auth or encryption code. You may read them; reading is not editing. Never propose a patch to them. Label any finding that would need a change there with this exact text: ASK-FIRST: owner approval required before any edit.

You generate candidate next tasks and ideas from what the repository already records.

Sources to read:

- `feature_list.json` (status and priority of each item)
- `docs/agentic/roadmap.md` and `docs/agentic/progress.md`
- `docs/features/TASK_LIST.md`
- `docs/plans/` and `docs/research/`

What to return:

1. Up to 5 candidates, ranked. Each has: item id or title | why now (the source file:line that says it is pending and unblocked) | blockers found (file:line) | what verification the source names.
2. Any contradiction you found between two sources about the same item's status, with both file:line references.

Limits:

- You cannot browse the web. Every idea must cite a file in this repository. External research is the orchestrator's job.
- You cannot change an item's status. Say what evidence would justify a change.
```

- [ ] **Step 4: Create `.claude/agents/verification-engineer.md`**

```markdown
---
name: verification-engineer
description: Read-only reviewer of verification evidence for Asclexis. Use it to judge whether a claim such as tests pass, a gate is green or a test would catch a regression is backed by the command output supplied, and whether the tests could have failed at all. Does not run anything and makes no edits.
tools: Read, Grep, Glob
model: haiku
---

Tools: Read, Grep, Glob. You cannot edit files, run commands, or access the network.

Run only in a fresh source-only git worktree. Local patient data (the `data` directory, `*.db` files, `.env` files) is gitignored, so a fresh worktree does not contain it. Before dispatching you, the orchestrator runs the patient-data gate from `docs/agentic/harness.md` over that worktree and dispatches only if it exits 0. The gate exits 1 on any `data` or `src/backend/data` directory, any `*.db`, `*.db-wal` or `*.db-shm` file, or any `.env` file. That check is the boundary: Claude Code does not limit which paths Read can open. If a path under `data/` or `profiles/`, a `*.db`, `*.db-wal` or `*.db-shm` file, or a `.env` file shows up in your results anyway, do not open it. Stop and report UNSAFE-CHECKOUT.

Ask-first files (CLAUDE.md §1): `src/backend/modules/interpret_safety.py`, `src/backend/modules/redaction.py`, `src/backend/modules/faithfulness.py`, `src/backend/modules/verifier_agent.py`, `src/backend/core/auth.py`, and any other auth or encryption code. You may read them; reading is not editing. Never propose a patch to them. Label any finding that would need a change there with this exact text: ASK-FIRST: owner approval required before any edit.

You review verification evidence that someone else produced. You do not produce it.

Inputs: a claim, plus the command output that supports it, either pasted into your task or saved at a file path you are given. If no output is supplied, your verdict is UNVERIFIED and you name the command that would produce it.

What to check, following `docs/agentic/recurring-failures.md`:

1. The output shows the command that was claimed, run on the tree that was claimed.
2. Counts are collected counts with the interpreter named. Compare them with the baseline line in `CLAUDE.md`.
3. Each new test was observed failing before the fix. Look for the red run in the evidence.
4. Route tests that assert auth, path scoping or status codes go through HTTP with `route_client` from `src/backend/tests/support/routes.py`, not by calling the handler as a plain function. Grep the test file.
5. Ask what each test would fail to notice, and say it.

Return: claim | evidence found (file:line or quoted output line) | VERIFIED, UNVERIFIED or CONTRADICTED | what is missing.

Limits:

- You cannot run pytest, vitest, Playwright or any other command. Never report a result you did not see in the supplied output.
- `test_api_rag_index_002b` fails where no embedding model is installed. Report it as environmental; never suggest lowering its 0.7 threshold.
```

- [ ] **Step 5: Confirm every path the bodies name exists**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT"
for p in scripts/harness_drift_check.py src/backend/requirements.txt src/frontend/package.json src/frontend/package-lock.json .github/workflows/ci.yml dev.ps1 scripts/security_gate.py src/backend/core/llm feature_list.json docs/agentic/roadmap.md docs/agentic/progress.md docs/features/TASK_LIST.md docs/plans docs/research docs/agentic/recurring-failures.md src/backend/tests/support/routes.py CLAUDE.md AGENT.md src/backend/modules/interpret_safety.py src/backend/modules/redaction.py src/backend/modules/faithfulness.py src/backend/modules/verifier_agent.py src/backend/core/auth.py; do test -e "$p" && echo "ok  $p" || echo "MISSING $p"; done
```

Expected: every line starts `ok`. Any `MISSING` means you must **fix the body** (never invent the path) and re-run.

---

## Task 4: Author `windows-bootstrap-engineer`, then turn 001–007 green and commit

**Files:**
- Create: `.claude/agents/windows-bootstrap-engineer.md`
- Modify: `CLAUDE.md`, `AGENT.md` (baseline count lines only; collision declared)

**Interfaces:**
- Consumes: `IMPLEMENTER_TOOLS`, `IMPLEMENTER_WRITE_SCOPE`, `IMPLEMENTER_MODEL`, `IMPLEMENTER_LIMIT_LINE`, `DISPATCH_LINE`, the ask-first paragraph (Task 2).

**Proposed write scope:** exactly `dev.ps1` and `dev.bat`.
- `dev.bat` is the double-click wrapper that runs `powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0dev.ps1"` (`B@7b2ff1f dev.bat:16`).
- `dev.ps1` is the bootstrap (855 lines at B; winget Python 3.11 install at `:361-368`).

Excluded on purpose:
- `src/backend/scripts/download_models.py`, which is W-8/D8 territory and changed by branch B.
- `scripts/*.ps1`, which are test runners, not bootstrap.
- The "packaging/installer files" plan 03 A4 named. They do not exist (HC-M08 is a spike).

Widening the scope is OG-4.

- [ ] **Step 1: Create `.claude/agents/windows-bootstrap-engineer.md`**

```markdown
---
name: windows-bootstrap-engineer
description: Bounded implementer for the Windows one-click bootstrap of Asclexis (dev.ps1 and its dev.bat launcher, feature HC-M02). Use it only when the whole change lives in those two files. Edits existing files only and cannot run commands.
tools: Read, Grep, Glob, Edit
model: opus
write_scope:
  - dev.ps1
  - dev.bat
---

Tools: Read, Grep, Glob, Edit. You cannot create files, run commands, or access the network.

Run only in a fresh source-only git worktree. Local patient data (the `data` directory, `*.db` files, `.env` files) is gitignored, so a fresh worktree does not contain it. Before dispatching you, the orchestrator runs the patient-data gate from `docs/agentic/harness.md` over that worktree and dispatches only if it exits 0. The gate exits 1 on any `data` or `src/backend/data` directory, any `*.db`, `*.db-wal` or `*.db-shm` file, or any `.env` file. That check is the boundary: Claude Code does not limit which paths Read can open. If a path under `data/` or `profiles/`, a `*.db`, `*.db-wal` or `*.db-shm` file, or a `.env` file shows up in your results anyway, do not open it. Stop and report UNSAFE-CHECKOUT.

Ask-first files (CLAUDE.md §1): `src/backend/modules/interpret_safety.py`, `src/backend/modules/redaction.py`, `src/backend/modules/faithfulness.py`, `src/backend/modules/verifier_agent.py`, `src/backend/core/auth.py`, and any other auth or encryption code. You may read them; reading is not editing. Never propose a patch to them. Label any finding that would need a change there with this exact text: ASK-FIRST: owner approval required before any edit.

Write scope: `dev.ps1` and `dev.bat`. Edit no other file. If the task needs a change anywhere else, stop and hand back a scope note that names the file and the change. Do not make it.

Claude Code does not enforce this path list. The Edit tool can reach any existing file, so the bound holds because you keep it, and because the orchestrator checks `git diff --name-only` against it after you return.

How to work:

1. Read the task, then the parts of `dev.ps1` and `dev.bat` it touches.
2. Make the smallest edit that does the task. Keep these behaviours intact:
   - picking the next free port when 8000 or 3000 is busy;
   - the winget Python 3.11 install prompt, with manual instructions as the fallback (HC-M02 in `feature_list.json`);
   - `dev.bat` keeping its window open on a non-zero exit.
3. `dev.bat` starts `powershell`, which is Windows PowerShell 5.1, not `pwsh`. Write syntax that parses there.
4. Hand back:
   - a summary of each change, with file:line;
   - this verification command for the orchestrator to run (you cannot run it). Expected output: `0`.

     powershell.exe -NoProfile -Command '$errors = $null; $null = [System.Management.Automation.Language.Parser]::ParseFile((Resolve-Path ./dev.ps1).Path, [ref]$null, [ref]$errors); $errors.Count'

   - the manual check HC-M02 still needs: run `dev.bat` on a Windows machine with no Python installed.

Never edit `.gitignore`, `.github/`, `CLAUDE.md`, `AGENT.md`, anything under `src/`, or any auth, encryption or safety module. All of these are outside your scope.
```

(The verification command is indented as a code line inside the list, so this file has no nested code fence.)

- [ ] **Step 2: Check the files, stage only them, and run 001–007**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT"
git status --short --untracked-files=all .claude/
```

Expected: exactly these 5 lines, and nothing else (C-GATE-3):

```text
?? .claude/agents/agentic-roadmap-researcher.md
?? .claude/agents/dependency-policy-auditor.md
?? .claude/agents/docs-consistency-scanner.md
?? .claude/agents/verification-engineer.md
?? .claude/agents/windows-bootstrap-engineer.md
```

If any other path appears (for example `.claude/settings.local.json`), **STOP**: the un-ignore is too wide.

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT"
git add .claude/agents/docs-consistency-scanner.md .claude/agents/dependency-policy-auditor.md .claude/agents/agentic-roadmap-researcher.md .claude/agents/verification-engineer.md .claude/agents/windows-bootstrap-engineer.md
cd "$WT/src/backend" && "$PY" -B -m pytest tests/test_claude_agent_definitions.py -p no:cacheprovider -q; echo "pytest_exit=$?"
```

Expected: `7 passed`. HC-AGENTS-003 reads git's index, so it needs the files staged.

- [ ] **Step 3: Break each test on purpose** (recurring-failures #1). Make each edit, confirm the named test fails, then restore the file.

| Edit | Expected red |
|---|---|
| `touch .claude/agents/scratch.md` | 003 (`on_disk` has a 6th name) |
| `git rm --cached .claude/agents/verification-engineer.md` (re-add after) | 003 (`tracked` is short by one) |
| delete the `tools:` line in `docs-consistency-scanner.md` | 004 ("Claude Code would grant every tool"), 005, 007 |
| `tools: Read, Grep, Glob, Bash` in `verification-engineer.md` | 005 (`write-capable tools ['Bash']`) and 007 |
| `model: sonnet` in `dependency-policy-auditor.md` | 005 |
| add `hooks: {}` to any file | 004 (`keys outside the approved scope: ['hooks']`) |
| add `  - src/backend/modules/redaction.py` to `write_scope` | 006 |
| `tools: Read, Grep, Glob, Edit, Write` in the implementer | 006 and 007 |
| delete the `Tools: …` line from any body | 007 |
| delete the sentence `Run only in a fresh source-only git worktree.` from any body | 007 (`body lacks 'Run only in a fresh source-only git worktree.'`) |
| delete the sentence `ASK-FIRST: owner approval required before any edit.` from `dependency-policy-auditor.md` | 007 (`body lacks 'ASK-FIRST: owner approval required before any edit.'`) |
| delete `` `src/backend/core/auth.py`, `` from any body's ask-first list | 007 (`ask-first list lacks src/backend/core/auth.py`) |
| save one file with a UTF-8 BOM | 004 ("line 1 must be exactly '---'"), plus every other test that loads that file (005, 007 for a scanner) |

After restoring everything, re-run and expect `7 passed`. Every row of this table was simulated 2026-09-27 in the scratch repo, and each turned exactly the listed tests red.

- [ ] **Step 4: Human honesty review of the five bodies** (plan 03's warning; HC-AGENTS-007 cannot see this). For each body, answer yes or no in the execution record:
  - (a) Does any sentence claim an action its tools do not allow (running, fetching, writing, installing)?
  - (b) Does every named path exist (Task 3 Step 5, plus `dev.bat` and `feature_list.json`)?
  - (c) Does any sentence claim enforcement that is only an instruction? The dispatch paragraph must call the worktree check "the boundary" and must say that Claude Code does not limit `Read`.

Every answer must be "no / yes / no". Otherwise fix the body and re-run Step 2.

- [ ] **Step 5: Measure, update the baseline lines, commit**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT"
cd "$WT/src/backend" && "$PY" -B -m pytest tests/ --collect-only -q -p no:cacheprovider | tail -1; echo "collect_exit=$?"
cd "$WT"
```

Expected: `START_COLLECTED + 7`, from the 7 tests HC-AGENTS-001…007. Write the measured number into the collected-count slots only, following the baseline-sentence rule in [Files](#files). Leave the pass-count wording alone, and flag it in the PR. This is a declared collision.

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT"
git add .gitignore src/backend/tests/test_claude_agent_definitions.py CLAUDE.md AGENT.md
git diff --cached --name-only
```

Expected: exactly `.claude/agents/agentic-roadmap-researcher.md`, `.claude/agents/dependency-policy-auditor.md`, `.claude/agents/docs-consistency-scanner.md`, `.claude/agents/verification-engineer.md`, `.claude/agents/windows-bootstrap-engineer.md`, `.gitignore`, `AGENT.md`, `CLAUDE.md` and `src/backend/tests/test_claude_agent_definitions.py`. That is 9 paths.

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT"
git commit -m "feat(harness): commit the five named subagents and un-ignore .claude/agents/" -m "Owner decision D1/D1-scope (2026-09-27). Four read-only scanners (Read, Grep, Glob; haiku) and windows-bootstrap-engineer (Read, Grep, Glob, Edit; opus) with a declared write_scope of dev.ps1 and dev.bat. Claude Code does not enforce write_scope; the tool list stops file creation and shell use, and diff review holds the path bound. HC-AGENTS-001..007." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

## Task 5: Make harness.md and roadmap.md name what now exists (manual gate HC-AGENTS-008)

**Files:**
- Modify: `docs/agentic/harness.md` (`B@7b2ff1f:25-27`)
- Modify: `docs/agentic/roadmap.md` (`B@7b2ff1f:10`, `:17`)

No test file changes and no collection change in this task. HC-AGENTS-008 is a **manual gate command**, not a collected pytest test. Its output is recorded in the execution record and pasted into the PR. It satisfies handoff W-1 test (3), "`scripts/harness_drift_check.py` (from branch B) exits 0". Putting it into the collected backend suite would make the drift checker a CI gate, which needs OG-3. That is Task 9, and it runs only after OG-3 is signed.

**Interfaces:**
- Consumes: the 5 agent file paths from Task 3/Task 4; `scripts/harness_drift_check.py` as a CLI (exit 0 = pass, 1 = drift; `B@7b2ff1f:130-142`).
- Produces: the HC-AGENTS-008 gate block below. Task 8 re-runs it verbatim, and Task 9 turns it into a pytest test.

**Lines from `7b2ff1f` that become false once the agents exist.** Each is reconciled here, or in Task 6 where noted:

| Ref | Text at B | Action |
|---|---|---|
| `harness.md:25` | "No subagent definitions are checked into this repo — there is no agents directory under `.claude/` — every subagent dispatch here is ad hoc, …" | Replace (Step 3) |
| `harness.md:27` | "- **Read-only scanners** for repo survey, contradiction hunting, dependency evidence, and idea generation. They return evidence, not edits." | Replace with the named, pinned list (Step 3) |
| `roadmap.md:10` | "orchestrator + ad hoc scoped subagents (see harness.md#subagent-rules)" (a markdown link in the file) | Replace (Step 4) |
| `roadmap.md:17` | "\| Agent orchestration \| ad hoc subagent dispatch, harness.md \|" (a markdown link in the file) | Replace (Step 4) |
| `CS4610_Report_Demo/README.md:22-23` | "That directory does not exist; subagent dispatch in this repo is ad hoc, not named, reusable configs." | Task 6 |
| `harness.md:28-29` | "Implementation stays in the orchestrator…", "Subagents never touch the safety-critical modules…" | Keep. Both stay true. "Touch" means edit; the scanners cannot edit, and the implementer's scope excludes them. |
| `scripts/harness_drift_check.py:12-14` docstring, `tests/test_harness_drift_check.py:44` fixture | Use "`.claude/agents/`" as an *example* of a missing path | Keep. They are synthetic examples in `tmp_path`, not claims about this repo. |
| `docs/research/2026-09-08/10-*.md`, `11-*.md`, `13-*.md`, `STATUS.md`, `INDUSTRY-PROMPT.md`; `docs/plans/2026-09-10-implementation-roadmap.md:83` | "does not exist" statements | Keep. These are dated evidence, true on their dates (plan 04: "Do not touch … dated records"). |

- [ ] **Step 1: Run the HC-AGENTS-008 gate and watch it fail (RED)**

HC-AGENTS-008 gate. Task 8 Step 2 and the PR re-run this block verbatim:

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT"
unnamed=0
for n in docs-consistency-scanner dependency-policy-auditor agentic-roadmap-researcher verification-engineer windows-bootstrap-engineer; do
  grep -qF "\`.claude/agents/$n.md\`" "$WT/docs/agentic/harness.md" || { echo "unnamed: $n"; unnamed=$((unnamed+1)); }
done
echo "unnamed=$unnamed"
"$PY" "$WT/scripts/harness_drift_check.py"; echo "drift=$?"
```

Expected (RED, before Step 3): five `unnamed: <name>` lines, `unnamed=5`, then `Harness drift check passed.` and `drift=0`. The drift check passes at this point because `7b2ff1f`'s wording names no missing path; the RED comes from the naming half. Full paths matter because the drift check skips bare names (no extension, no slash, `B@7b2ff1f scripts/harness_drift_check.py:63-74`), so only a full path makes it verify that each file exists.

- [ ] **Step 2: Record the RED output** in the execution record (the exact 7 lines).

- [ ] **Step 3: Edit `docs/agentic/harness.md`.** Replace line 25 with the first paragraph below, and line 27 with the three bullets below; the third bullet contains an indented `bash` code block (both lines are quoted in the table). Leave line 26 (blank) and lines 28–29 as they are. `<DATE>` is the execution date from `date -u +%F`.

````markdown
Five subagent definitions are checked in under `.claude/agents/`. They were written new on <DATE> by owner decision D1 (2026-09-27). Before that, the directory did not exist and this section said so. Use them to keep exploration noise out of the main context. Ad hoc dispatch without a definition is still allowed and follows the same rules.

- **Read-only scanners on the `haiku` model:** `.claude/agents/docs-consistency-scanner.md` (contradiction hunting), `.claude/agents/dependency-policy-auditor.md` (dependency evidence), `.claude/agents/agentic-roadmap-researcher.md` (idea generation from the repo's own backlog and research notes) and `.claude/agents/verification-engineer.md` (reviews verification output that someone else ran). Each lists only `Read`, `Grep` and `Glob` in its `tools` field, which Claude Code enforces, so it cannot edit files, run commands or reach the network. They return evidence, not edits.
- **One bounded implementer on the `opus` model:** `.claude/agents/windows-bootstrap-engineer.md`, for changes that live entirely in `dev.ps1` and `dev.bat`. Its tools are `Read`, `Grep`, `Glob` and `Edit`, so it cannot create files or run commands. Its frontmatter declares `write_scope` as those two files. Claude Code does not enforce that key. The bound holds through the agent's instructions and through the orchestrator, who runs `git diff --name-only` after every dispatch and rejects any path outside those two files. `src/backend/tests/test_claude_agent_definitions.py` pins every tool list and the declared scope.
- **Where they run:** dispatch any of the five only from a fresh source-only worktree, and only after the patient-data gate below exits 0. Run it from this repository's checkout:

  ```bash
  set -o pipefail
  AGENT_WT="$(git rev-parse --show-toplevel)-agent"   # sibling directory; must not exist yet
  git worktree add --detach "$AGENT_WT" HEAD
  phi_gate() {
    local root="$1" hits
    hits=$(find "$root" -path "$root/.git" -prune -o \( -path "$root/data" -o -path "$root/src/backend/data" -o -name '*.db' -o -name '*.db-wal' -o -name '*.db-shm' -o -name '.env' \) -print) || { echo "phi_gate: find failed" >&2; return 1; }
    test -z "$hits" || { printf '%s\n' "$hits"; return 1; }
  }
  phi_gate "$AGENT_WT"; echo "phi_gate_exit=$?"
  ```

  Dispatch only on `phi_gate_exit=0`, starting Claude Code inside that worktree. The gate exits 1 and prints each match when it finds a `data` or `src/backend/data` directory, or a `*.db`, `*.db-wal`, `*.db-shm` or `.env` file anywhere in the worktree. It also exits 1 if `find` itself fails. Local patient data is gitignored, so a fresh worktree holds none of it. That gate is the boundary. Claude Code does not limit which paths `Read` opens, so a checkout that holds patient data is never a place to dispatch these agents. Afterwards, remove the worktree with `git worktree remove --force "$AGENT_WT"`.
````

Drift-check behaviour of this text, per `_is_checkable` at `B@7b2ff1f:63-74`:
- Verified: `.claude/agents/`, the 5 `.claude/agents/*.md` paths, `dev.ps1` and `dev.bat` (both on `ROOT_ALLOWLIST`), and the test path.
- Skipped: `haiku`, `opus`, `Read`, `Grep`, `Glob`, `Edit`, `tools`, `write_scope` (no extension, no slash).
- Also skipped: every span whose first word is `git` (a command verb), spans containing `=` or `*`, and the fenced gate code, which contains no backtick spans. The gate code was run verbatim in scratch (see Task 7 Step 1b). That is why the new bullet writes the `data` directory without a trailing slash: a backticked `data/` would be checked and fail, because no such directory is tracked.

- [ ] **Step 4: Edit `docs/agentic/roadmap.md`**

Line 10, replace the phrase starting `orchestrator + ad hoc scoped subagents` up to and including its closing `)` after the `harness.md#subagent-rules` link, with:

```markdown
orchestrator + scoped subagents (five checked-in definitions under `.claude/agents/`, plus ad hoc dispatch; see [harness.md](harness.md#subagent-rules))
```

Line 17, replace the row with:

```markdown
| Agent orchestration | `.claude/agents/` (five definitions), [harness.md](harness.md) |
```

The `## Subagent rules` heading is unchanged, so the `#subagent-rules` anchor still resolves.

- [ ] **Step 5: Re-run the HC-AGENTS-008 gate (GREEN), then the docs gates**

Re-run the Step 1 block. Expected: no `unnamed:` lines, `unnamed=0`, `Harness drift check passed.`, `drift=0`. Then run:

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT/src/backend" && "$PY" -B -m pytest tests/test_claude_agent_definitions.py -p no:cacheprovider -q; echo "pytest_exit=$?"
cd "$WT"
"$PY" scripts/docs_lint.py; echo "lint=$?"
"$PY" scripts/generate_docs_index.py --check; echo "index=$?"
```

Expected: `7 passed` with `pytest_exit=0`; `Docs lint passed.` with `lint=0`; `index=0`. If `index` is non-zero, see the Task 8 stop gate.

- [ ] **Step 6: Break it on purpose** (owned files only; each edit is undone by reversing that same edit, never by `git checkout --`)
  1. In `$WT/docs/agentic/harness.md`, change `.claude/agents/verification-engineer.md` to `.claude/agents/verifier.md`. Re-run the Step 1 block. Expected: `unnamed: verification-engineer`, `unnamed=1`, and the drift check fails with `ERROR: docs/agentic/harness.md:<n>: missing path '.claude/agents/verifier.md'`, `drift=1`. Change it back, then re-run and expect `unnamed=0`, `drift=0`.
  2. Run `mv "$WT/.claude/agents/dependency-policy-auditor.md" "$WT/.claude/agents/dpa.md"`. The Step 1 block gives `drift=1` (`missing path '.claude/agents/dependency-policy-auditor.md'`), and the Step 5 pytest gives HC-AGENTS-003 red. Move it back, then re-run both and expect green.

  Simulated 2026-09-27 with the B checker: a harness line naming `.claude/agents/docs-consistency-scanner.md` gives exit 1 with the directory absent, exit 1 with only an empty directory, and exit 0 once the file exists.

*What would this gate fail to notice?*
- The drift check reads the working tree. An agent file that exists on disk but is untracked or ignored satisfies it. HC-AGENTS-003 (git index) and running in the clean worktree (recurring-failures #5) close that gap.
- It does not check `roadmap.md` names. `roadmap.md` names only the directory.
- Until Task 9 (OG-3), nothing re-runs it automatically. A later docs edit can break it silently between manual runs.

- [ ] **Step 7: Commit (no collection change, so no count edit)**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01; set -o pipefail
cd "$WT"
git add docs/agentic/harness.md docs/agentic/roadmap.md
git diff --cached --name-only
git commit -m "docs: name the committed subagents in harness docs" -m "Reverses the '.claude/agents does not exist' wording from 7b2ff1f now that the five definitions are committed. HC-AGENTS-008 manual gate (full-path names + harness_drift_check.py) recorded in the PR; not in the backend suite unless OG-3 is signed." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected `git diff --cached --name-only`: exactly `docs/agentic/harness.md` and `docs/agentic/roadmap.md`.

---

## Task 6: Coursework scope note and the claims ledger (docs only)

**Files:**
- Modify: `CS4610_Report_Demo/README.md` (`B@7b2ff1f:20-23`)
- Modify: `docs/capstone-report/claims-ledger.md` (H5, H6)
- Conditional: `docs/capstone-report/specs-compliance-matrix.md` (GATE-09, GATED-06); `docs/capstone-report/architecture-engineering-contract.md` (the reconciled-table `.claude/agents/` row)

- [ ] **Step 1: Edit `CS4610_Report_Demo/README.md`.** Replace lines 20–23 with the text below. `<DATE>` is the same date as Task 5. The bullet stays under "Claims checked against the repo and found **not evidenced**", because it was not evidenced when the reports were written.

```markdown
- **Named subagent definitions under `.claude/agents/`** (`docs-consistency-scanner`,
  `dependency-policy-auditor`, etc.) — implied throughout both documents.
  When the reports were written that directory did not exist, and subagent
  dispatch was ad hoc. On <DATE> the five named definitions were written new
  and committed by owner decision (D1, 2026-09-27). They were not recovered
  from anywhere, and they do not make the reports' description true
  retroactively: four are read-only scanners, and the one implementer's write
  scope is declared, not enforced by Claude Code. See `docs/agentic/harness.md`.
```

Do not touch line 13 ("No hook mechanism and no `.claude/settings.json` exist in this repo at all."). It stays true, and HC-AGENTS-002 pins it.

- [ ] **Step 2: Edit `docs/capstone-report/claims-ledger.md` rows H5 and H6.** The current rows (`pkg:45-46`) are:

> `| H5 | .claude/agents/ defines 5 project subagents | Absent from the repo and from git history (git log --all -- .claude/agents empty). .gitignore:44 .claude/* blocks it. None of the 5 names are among the **33** user-level agents *(was "34")*. | CONTRADICTED |`
> `| H6 | AgentShield PreToolUse hook enforces PHI | Not in the repo. ~/.claude/settings.json registers PreToolUse hooks for continuous-learning and GSD only. A **disabled** plugin's cache lists agentshield-pack; no hook from it is registered. | NOT-EVIDENCED |`

Replace them with the rows below, filling `<SHA>` with the Task 4 commit and `<DATE>`:

```markdown
| H5 | `.claude/agents/` defines 5 project subagents | **Before <DATE>:** absent from the repo and from git history; `.gitignore:44` `.claude/*` blocked it; none of the 5 names among the 33 user-level agents. **Since `<SHA>` (<DATE>, owner decision D1/D1-scope):** the 5 files are authored new and committed; `!.claude/agents/` un-ignores only that directory. 4 are read-only (`tools: Read, Grep, Glob`, `haiku`); `windows-bootstrap-engineer` has `Read, Grep, Glob, Edit` (`opus`) and a `write_scope` of `dev.ps1`, `dev.bat` that Claude Code does not enforce (declared + diff review). Pinned by HC-AGENTS-001…007 in the backend suite. The HC-AGENTS-008 manual gate (full-path names + drift check) is recorded in the PR, and runs in CI only after OG-3. The coursework claim was false when written. | `VERIFIED` (files, tool lists, declared scope, as of `<SHA>`) · write-scope runtime enforcement: `NOT-EVIDENCED` by design |
| H6 | AgentShield PreToolUse hook enforces PHI | Not in the repo. `~/.claude/settings.json` registers PreToolUse hooks for continuous-learning and GSD only. A **disabled** plugin's cache lists `agentshield-pack`; no hook from it is registered. W-1 (D1) added agent definitions only: no hook, and `.claude/settings.json` stays ignored and absent (HC-AGENTS-002). | `NOT-EVIDENCED` |
```

- [ ] **Step 3 (conditional): Matrix and contract rows.** First ask the orchestrator whether any other phase is editing `specs-compliance-matrix.md` or `architecture-engineering-contract.md`.
  - **If yes:** do not edit. Put the status change in the PR body instead (handoff §6 item 3).
  - **If no:** make these edits:
    - **GATE-09:**
      - Implementation cell: "5 files committed at `<SHA>`; `!.claude/agents/`; no repo hooks".
      - Gate cell: "HC-AGENTS-001…007 in CI `backend-tests`; HC-AGENTS-008 (drift check) manual, in CI only after OG-3 (Task 9)".
      - Status: `tested`. It becomes `enforced` only after Task 9 lands and a linked CI run shows `backend-tests` running HC-AGENTS-008.
      - Owner gate: "D1 decided 2026-09-27: A, all 5".
    - **GATED-06:** recorded position "D1: A, all 5 (2026-09-27)"; evidence "agents committed `<SHA>`; hooks still absent (not licensed)"; packet "this plan".
    - **Contract `.claude/agents/` row:** decision "**Decided: A, all 5** (owner, 2026-09-27, D1/D1-scope)"; rationale "owner-decisions-2026-09-27.md".

- [ ] **Step 4: Gates and commit**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT"
"$PY" scripts/docs_lint.py; echo "lint=$?"
"$PY" scripts/harness_drift_check.py; echo "drift=$?"
git add CS4610_Report_Demo/README.md docs/capstone-report/claims-ledger.md
# only if Step 3 edited them:
# git add docs/capstone-report/specs-compliance-matrix.md docs/capstone-report/architecture-engineering-contract.md
git diff --cached --name-only
git commit -m "docs: record the committed subagents in the coursework scope note and claims ledger" -m "H5 now separates before/after the D1 commit; H6 unchanged in verdict (no hook added). Coursework .docx/.pdf untouched." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

Expected: `lint=0`, `drift=0`, and the staged list is exactly the 2 (or 4) paths.

---

## Task 7: Runtime smoke (automated suite cannot see this — record as evidence)

**Files:** none. Record transcript excerpts and command output in the execution record.

No test in this plan measures this (`UNMEASURED` by automation), so it is measured here by hand. Every dispatch happens in a separate, disposable, source-only worktree, as `harness.md` now requires. The phase worktree `$WT` has had pytest run in it, and it is never used to dispatch agents.

- [ ] **Step 1: Create the dispatch worktree and run the patient-data gate**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01; AGENT_WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01-smoke; set -o pipefail
phi_gate() {
  local root="$1" hits
  hits=$(find "$root" -path "$root/.git" -prune -o \( -path "$root/data" -o -path "$root/src/backend/data" -o -name '*.db' -o -name '*.db-wal' -o -name '*.db-shm' -o -name '.env' \) -print) || { echo "phi_gate: find failed" >&2; return 1; }
  test -z "$hits" || { printf '%s\n' "$hits"; return 1; }
}
git -C "$WT" worktree add --detach "$AGENT_WT" HEAD
phi_gate "$AGENT_WT"; echo "phi_gate_exit=$?"
ls "$AGENT_WT/.claude/agents" | wc -l
```

Expected: no path printed, `phi_gate_exit=0`, then `5`. If `phi_gate_exit` is not `0`, **STOP**: this worktree is not source-only, and no agent is dispatched in it.

- [ ] **Step 1b: Break the gate on purpose**, in the disposable worktree only. Each planted item must make the gate exit 1 before any dispatch.

```bash
AGENT_WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01-smoke; set -o pipefail
phi_gate() {
  local root="$1" hits
  hits=$(find "$root" -path "$root/.git" -prune -o \( -path "$root/data" -o -path "$root/src/backend/data" -o -name '*.db' -o -name '*.db-wal' -o -name '*.db-shm' -o -name '.env' \) -print) || { echo "phi_gate: find failed" >&2; return 1; }
  test -z "$hits" || { printf '%s\n' "$hits"; return 1; }
}
for x in data src/backend/data probe.db src/probe.db-wal src/backend/probe.db-shm .env src/backend/.env; do
  case "$x" in data|src/backend/data) mkdir -p "$AGENT_WT/$x" ;; *) touch "$AGENT_WT/$x" ;; esac
  phi_gate "$AGENT_WT" >/dev/null; echo "$x -> exit=$?"
  rm -rf "${AGENT_WT:?}/${x:?}"
done
phi_gate "$AGENT_WT"; echo "after_cleanup_exit=$?"
phi_gate "$AGENT_WT/does-not-exist" 2>/dev/null; echo "find_error_exit=$?"
```

Expected: seven lines, each ending `-> exit=1` (`data`, `src/backend/data`, `probe.db`, `src/probe.db-wal`, `src/backend/probe.db-shm`, `.env`, `src/backend/.env`), then `after_cleanup_exit=0`, then `find_error_exit=1`. If any planted line shows `exit=0`, the gate misses that pattern: **STOP** and fix the gate before any dispatch.

Simulated 2026-09-27 (round 4) in a scratch git repo built from `git archive` of B, using the Task 5 harness block verbatim (`AGENT_WT="$(git rev-parse --show-toplevel)-agent"`). Output: `phi_gate_exit=0`; `data -> exit=1`; `src/backend/data -> exit=1`; `probe.db -> exit=1`; `src/probe.db-wal -> exit=1`; `src/backend/probe.db-shm -> exit=1`; `.env -> exit=1`; `src/backend/.env -> exit=1`; `after_cleanup_exit=0`; `find_error_exit=1`. A planted `src/backend/probe.db` also printed its path and gave exit 1, and `git worktree remove --force` gave exit 0. At B, `git ls-tree -r` has 0 tracked files matching these patterns.

- [ ] **Step 2: The agents load.** Run `cd /mnt/c/Users/DangT/Documents/GitHub/hc-w01-smoke && claude`, then `/agents`.
  - Expected: all 5 names are listed as project agents.
  - If any is missing: run `claude --debug`, record the parse error, and **STOP**.
- [ ] **Step 3: A scanner cannot write.**
  1. Ask `@docs-consistency-scanner` to "create the file tmp-w01-probe.txt containing 'x'". Expected: it reports that it has no tool to write.
  2. Run `git -C /mnt/c/Users/DangT/Documents/GitHub/hc-w01-smoke status --porcelain --untracked-files=all`. Expected: no output. If a file appears, **STOP**, because F2/F5 do not hold.
- [ ] **Step 4: The implementer cannot create or run.**
  1. Ask `@windows-bootstrap-engineer` to "create scripts/w01-probe.ps1" and to "run the AST parse command". Expected: it refuses, or reports it has no tool for either.
  2. Run the same `git -C … status --porcelain --untracked-files=all`. Expected: no output.
- [ ] **Step 5: The review rule works, then restore by explicit path.**
  1. Ask `@windows-bootstrap-engineer` to add a one-line comment at the top of `dev.ps1` and to "also fix a typo in README.md". Expected: it edits `dev.ps1` only and hands back a scope note for `README.md`.
  2. Run the block below.

```bash
AGENT_WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01-smoke
git -C "$AGENT_WT" status --short -- dev.ps1 README.md
git -C "$AGENT_WT" checkout -- dev.ps1 README.md
git -C "$AGENT_WT" status --porcelain --untracked-files=all | wc -l
```

Expected: the first command prints exactly ` M dev.ps1`; the last prints `0`.

If `README.md` was also listed, then:
- Record that as **evidence that the bound is prompt-only**.
- The `checkout` above has already restored it.
- Raise OG-1 with the owner.
- Do not "fix" the agent by adding a hook.

- [ ] **Step 6: Remove the dispatch worktree**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01; AGENT_WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01-smoke
phi_gate() {
  local root="$1" hits
  hits=$(find "$root" -path "$root/.git" -prune -o \( -path "$root/data" -o -path "$root/src/backend/data" -o -name '*.db' -o -name '*.db-wal' -o -name '*.db-shm' -o -name '.env' \) -print) || { echo "phi_gate: find failed" >&2; return 1; }
  test -z "$hits" || { printf '%s\n' "$hits"; return 1; }
}
phi_gate "$AGENT_WT"; echo "phi_gate_exit=$?"
git -C "$AGENT_WT" status --porcelain --ignored --untracked-files=all
git -C "$WT" worktree remove --force "$AGENT_WT"
git -C "$WT" worktree list
```

Record both outputs. Expected: `phi_gate_exit=0`, and the status prints nothing, or only `!! .claude/settings.local.json` if a permission prompt was answered with "always allow". Any other line means something was created during the smoke; record it. `--force` is safe here because this worktree is disposable and detached. The last command must no longer list `hc-w01-smoke`.

---

## Task 8: Final verification, recurring-failures recheck, PR

- [ ] **Step 1: Full suite in the clean worktree**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT/src/backend"
"$PY" -B -m pytest tests/ --collect-only -q -p no:cacheprovider | tail -1; echo "collect_exit=$?"
"$PY" -B -m pytest tests/ -p no:cacheprovider -q 2>&1 | tail -20; echo "suite_exit=$?"
"$PY" -c "from main import app" && echo "boot ok"
cd "$WT"
```

Expected:
- collected = `START_COLLECTED + 7`, from the final test list HC-AGENTS-001…007. It is `+ 8` only if Task 9 already ran after OG-3. The number must equal the collected-count slots now in `CLAUDE.md` and `AGENT.md`;
- failures ⊆ `START_FAILURES`;
- `boot ok`.

- [ ] **Step 2: Gates**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT"
"$PY" scripts/harness_drift_check.py; echo "drift=$?"
"$PY" scripts/docs_lint.py; echo "lint=$?"
"$PY" scripts/generate_docs_index.py --check; echo "index=$?"
"$PY" scripts/repo_hygiene_check.py; echo "hygiene=$?"
for n in docs-consistency-scanner dependency-policy-auditor agentic-roadmap-researcher verification-engineer windows-bootstrap-engineer; do git check-ignore --no-index -q .claude/agents/$n.md; echo "$n ignore=$?"; done
git ls-files .claude/agents | wc -l
```

Expected: `drift=0`, `lint=0`, `index=0`, `hygiene=0`, five lines ending `ignore=1`, and `5`. Then re-run the HC-AGENTS-008 gate block from Task 5 Step 1 verbatim. Expected: `unnamed=0` and `drift=0`. Paste that output into the PR.

**Stop gate:** if `index` is non-zero, the regeneration writes `docs/INDEX.md` and `docs/_link_graph.json`, which are shared with P0-B and P4. Regenerate only with the orchestrator's go-ahead, and stage by explicit path.

- [ ] **Step 3: Frontend untouched.** `git -C /mnt/c/Users/DangT/Documents/GitHub/hc-w01 diff --name-only origin/main...HEAD -- src/frontend | wc -l` → `0`. No frontend gate is needed.

- [ ] **Step 4: Recurring-failures recheck** (read [recurring-failures.md](../agentic/recurring-failures.md) first). Record each answer.

| # | Applies? | Concrete recheck |
|---|---|---|
| 1 Green suite that could not fail | yes | Every HC-AGENTS test or gate was seen red: Task 1 Steps 2 and 5, Task 2 Step 2, Task 4 Step 3, Task 5 Steps 1 and 6 (manual gate 008), Task 7 Step 1b (patient-data gate), and Task 9 Step 3 if it runs. HC-AGENTS-001 uses `--no-index`, or it passes vacuously on tracked files. The 008 gate pairs with 003, because the drift check reads disk, not git. |
| 2 Fix creates the next bug one layer over | yes | Walk every sentence `7b2ff1f` wrote about agents (Task 5 table): each is replaced, kept-and-justified, or dated history. Confirm the CS4610 README line 13 is still true (HC-AGENTS-002). Confirm plan 04 Task 15's checks (Step 6) match the new text. The post-P1 `/profiles/` drift risk is reported to P1 (Task 0 Step 3), not patched by weakening the checker. |
| 3 Figures asserted | yes | Collected counts come from Step 1 output, not from `START + N` arithmetic alone; write the measured number. |
| 4 Environment-dependent results | yes | The HC-AGENTS tests need `git` and a git work tree. They fail, never skip, from a `git archive` export. Windows `python.exe` driving Windows `git.exe` against a `\\wsl.localhost` repo gets exit 128 ("dubious ownership"): measured 2026-09-27, with 001 and 002 red. So run them with the Linux D9 venv, not `/mnt/c/Python313`. PyYAML is transitive. Record the interpreter and `git --version`. |
| 5 Gates in a contaminated tree | yes | All gates ran in `/mnt/c/Users/DangT/Documents/GitHub/hc-w01` (`$WT`); agent dispatch ran only in `/mnt/c/Users/DangT/Documents/GitHub/hc-w01-smoke` after `phi_gate` exited 0. The owner's tree has `.claude/settings.local.json`, and a local ignored agent file there could satisfy the drift check. |
| 6 Documented commands nobody ran | yes | The AST-parse command in the implementer body was run (Task 0 Step 6). Every path in the bodies was checked (Task 3 Step 5). |
| 7 SQL three-valued logic | no | No SQL is touched. |
| 8 Stale guidance reads as authority | yes | `7b2ff1f`'s "does not exist" was true and is now stale; it is replaced. The matrix GATED-06 and contract row said "Not sure / owner-gated" after D1 had decided; they are updated or reported (Task 6 Step 3). |

- [ ] **Step 5: Push and open the PR, then STOP for the owner's merge**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT"
git push -u origin feat/w01-harness-agents
gh pr create --base main --title "feat(harness): commit the five named subagents (W-1, D1 Branch A)" --body-file /mnt/c/Users/DangT/Documents/GitHub/w01-pr-body.md
```

Write `/mnt/c/Users/DangT/Documents/GitHub/w01-pr-body.md` (outside the worktree, so it is never staged) from the execution record. The PR body follows handoff §6:
1. start and end measurements;
2. each new test with its red output, plus the HC-AGENTS-008 manual gate's RED (Task 5 Step 1) and GREEN (Task 8 Step 2) output;
3. GATE-09 and GATED-06 status changes, and H5/H6;
4. the explicit file list;
5. the Task 7 transcript excerpts;
6. OG-1…OG-5 as open questions. OG-3 decides whether Task 9 runs;
7. a flag that the CLAUDE.md/AGENT.md pass-count wording was not re-measured, unless a named-environment pass count was measured;
8. one next action.

It ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

- [ ] **Step 6: Hand plan 04 Task 15 its checks** (post-merge):

```bash
REPO=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral; POST=/mnt/c/Users/DangT/Documents/GitHub/hc-w01-postmerge; set -o pipefail
git -C "$REPO" fetch origin
git -C "$REPO" worktree add --detach "$POST" origin/main   # throwaway; never switch the owner's checkout
grep -n "\.claude/agents/" "$POST/docs/agentic/harness.md" "$POST/docs/agentic/roadmap.md"   # 5 file paths + directory in harness.md; directory in roadmap.md:10,17
python3 "$POST/scripts/harness_drift_check.py"; echo "drift=$?"                                # Harness drift check passed. drift=0
git -C "$REPO" worktree remove "$POST"
```

Plan 04's line references (`harness.md:25`, `roadmap.md:8,15`) are `main@40f590e` numbers. After P1 the roadmap lines are `:10,:17`.

---

## Task 9 (OG-3-gated): Move HC-AGENTS-008 into the backend suite

**Run only if the OG-3 sign-off line is signed.** Otherwise skip this task; the plan is complete at Task 8, and the collected total stays `START_COLLECTED + 7`.

**Files:**
- Modify: `src/backend/tests/test_claude_agent_definitions.py` (append HC-AGENTS-008)
- Modify: `CLAUDE.md`, `AGENT.md` (collected count only)

**Interfaces:**
- Consumes: `REPO_ROOT`, `ALL_AGENTS` (Task 1); `scripts/harness_drift_check.py::main(argv: list[str] | None) -> int` (`B@7b2ff1f:130`).

- [ ] **Step 1: Append the test**

```python
def _load_drift_check():
    script = REPO_ROOT / "scripts" / "harness_drift_check.py"
    spec = importlib.util.spec_from_file_location("harness_drift_check_agents", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_hc_agents_008_harness_docs_name_every_agent_and_have_no_drift(capsys) -> None:
    """HC-AGENTS-008 (handoff W-1 test 3; in the suite by owner sign-off OG-3).
    harness.md must name each agent by its full path: the drift check skips
    bare names, so only a full path makes it verify that each file exists.
    Then the drift check must pass on the real repo. It checks disk, not git:
    HC-AGENTS-003 is what proves the files are tracked."""
    harness = (REPO_ROOT / "docs" / "agentic" / "harness.md").read_text(encoding="utf-8")
    unnamed = [name for name in ALL_AGENTS if f"`.claude/agents/{name}.md`" not in harness]
    assert unnamed == [], f"harness.md does not name by full path: {unnamed}"
    exit_code = _load_drift_check().main(["--repo-root", str(REPO_ROOT)])
    assert exit_code == 0, capsys.readouterr().out
```

- [ ] **Step 2: Run it.** It pins a state Task 5 already made true, so it passes at once:

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT/src/backend" && "$PY" -B -m pytest tests/test_claude_agent_definitions.py -p no:cacheprovider -q; echo "pytest_exit=$?"
```

Expected: `8 passed`, `pytest_exit=0`.

- [ ] **Step 3: Prove it can fail, in a disposable detached worktree** (never by editing the committed harness.md in `$WT`)

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01; PY="$HOME/venvs/asclexis-311/bin/python"; BREAK_WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01-break; set -o pipefail
git -C "$WT" worktree add --detach "$BREAK_WT" HEAD
cp "$WT/src/backend/tests/test_claude_agent_definitions.py" "$BREAK_WT/src/backend/tests/test_claude_agent_definitions.py"
sed -i 's|`.claude/agents/verification-engineer.md`|`.claude/agents/verifier.md`|' "$BREAK_WT/docs/agentic/harness.md"
cd "$BREAK_WT/src/backend" && "$PY" -B -m pytest tests/test_claude_agent_definitions.py -p no:cacheprovider -q -k hc_agents_008; echo "pytest_exit=$?"
cd "$WT"
git -C "$WT" worktree remove --force "$BREAK_WT"
```

Expected: `1 failed, 7 deselected`, with `AssertionError: harness.md does not name by full path: ['verification-engineer']`, then `pytest_exit=1`. This was simulated 2026-09-27. The worktree is then removed. `-k hc_agents_008` matches only this test; Task 0 Step 3 showed no other `hc_agents` IDs exist.

*What would this test fail to notice?* The same gaps as the Task 5 gate, except that CI now re-runs it on every push.

- [ ] **Step 4: Update the collected count only, then commit**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT/src/backend" && "$PY" -B -m pytest tests/ --collect-only -q -p no:cacheprovider | tail -1; echo "collect_exit=$?"
```

Expected: `START_COLLECTED + 8 tests collected`. Write that number into the collected-count slots only (see [Files](#files): the baseline-sentence rule). Then:

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01; set -o pipefail
cd "$WT"
git add src/backend/tests/test_claude_agent_definitions.py CLAUDE.md AGENT.md
git diff --cached --name-only
git commit -m "feat(harness): run the harness drift gate in the backend suite (OG-3)" -m "HC-AGENTS-008 moves from a manual gate into test_claude_agent_definitions.py by owner sign-off OG-3. Collected count updated; pass-count sentences not re-measured." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push
```

Expected `git diff --cached --name-only`: exactly those 3 paths. After the PR's CI run shows `backend-tests` passing with `test_hc_agents_008…` in its log, the matrix GATE-09 status may move from `tested` to `enforced`.

---

## Measured acceptance

| Criterion | Command | Expected | Measured? |
|---|---|---|---|
| 5 files committed | `git ls-files .claude/agents \| wc -l` | `5` | at execution |
| Not ignored (handoff test 1) | `git check-ignore --no-index -q .claude/agents/<name>.md; echo $?` ×5 | `1` ×5 | at execution; `!.claude/agents/` semantics simulated 2026-09-27 (exit 1 for `.claude/agents/x.md`, exit 0 for `.claude/settings.local.json`) |
| Frontmatter parses; scanners have no write tools (test 2) | `pytest tests/test_claude_agent_definitions.py` | `7 passed` (`8 passed` only after Task 9) | at execution. Pre-simulated 2026-09-27 after the round-2 revision. The plan's code blocks were extracted verbatim into a scratch git repo: `git archive` of B, with B's own `recurring-failures.md` standing in for a P1 that resolved the `/profiles/` token. They were run with WSL `python3` 3.12 and `--noconftest`. Results: `7 passed` for HC-AGENTS-001…007; each red step as stated; the 008 gate went RED (`unnamed=5`) and then GREEN (`unnamed=0`, `drift=0`); `Docs lint passed.` on the edited docs. This does not replace the D9 3.11 run. |
| Drift check exits 0 (test 3) | HC-AGENTS-008 gate block (Task 5 Step 1), re-run in Task 8 Step 2 | `unnamed=0`, `Harness drift check passed.`, `drift=0` | at execution, manual; the output goes in the PR. It must already be 0 at start (Task 0 Step 3 STOP gate). Measured risk, 2026-09-27: B + A's `recurring-failures.md` gives exit 1 with one error, `'/profiles/'`. That is owned by P1 acceptance. |
| Suite | full pytest, clean worktree | collected = `START_COLLECTED + 7`, or `+ 8` only if Task 9 ran; failures ⊆ start | at execution |
| Docs | `docs_lint.py`, `generate_docs_index.py --check` | pass, exit 0 | at execution |
| Agents load in Claude Code; scanners cannot write; `phi_gate` exits 0 on the fresh worktree, exits 1 on each planted pattern, and exits 1 on a `find` error | Task 7 Steps 1, 1b, 2–6 | per Task 7 | **UNMEASURED by automation.** Measured by hand in Task 7, with a transcript |
| Write scope honoured at runtime | Task 7 Step 5 + diff review per dispatch | only `dev.ps1`/`dev.bat` change | **UNMEASURED by automation.** Declarative by design. OG-1 is the only way to enforce it. |
| CI runs the new tests | the PR's `backend-tests` job log shows `test_claude_agent_definitions.py` | 7 passed (8 after Task 9) | at PR time. GATE-09 → `enforced` needs Task 9 plus this CI log. |

## Stop gates

Stop and ask the owner (or the orchestrator, where noted) when any of these happens:

1. P1 has not landed, or the text in Task 0 Step 4 differs from the quotes.
2. `harness_drift_check.py` exits non-zero on the post-P1 tree before any W-1 change (Task 0 Step 3). Report it to the orchestrator; never edit the checker or its tests.
3. `import yaml` fails in the D9 venv. The fix would touch `requirements.txt`, which is shared.
4. The Claude Code docs contradict F2, F3, F4 or F5 (Task 0 Step 5).
5. `git status --short .claude/` shows anything besides the 5 agent files.
6. Any request, from a reviewer or from the work itself, to do any of the following. These are OG-1…OG-5 or W-10 territory:
   - add a hook or a `.claude/settings.json` deny rule;
   - give a scanner a shell;
   - widen `write_scope`;
   - add a `ci.yml` step;
   - un-ignore more of `.claude/`;
   - edit the drift checker;
   - edit CLAUDE.md beyond the baseline count lines.
7. The Task 7 smoke shows a scanner writing, or the implementer creating a file or running a command.
8. `phi_gate` exits non-zero before a dispatch, exits 0 on any planted pattern in Task 7 Step 1b, or an agent reports UNSAFE-CHECKOUT.
9. Any new test failure outside `START_FAILURES`, or any failure you cannot explain.
10. `generate_docs_index.py --check` is stale (orchestrator: shared files).
11. Any step would edit an ask-first file. None should.

## Rollback

This plan makes three commits: C1 (Task 4), C2 (Task 5) and C3 (Task 6). It makes a fourth, C4 (Task 9), only after OG-3. See [Commit plan](#commit-plan).

**Before the PR is merged** (PR open, branch pushed):

```bash
REPO=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w01; set -o pipefail
gh pr list --head feat/w01-harness-agents --state open --json number --jq '.[0].number'
gh pr close <number> --delete-branch
git -C "$REPO" worktree remove --force "$WT"
git -C "$REPO" branch -D feat/w01-harness-agents
git -C "$REPO" ls-remote --heads origin feat/w01-harness-agents | wc -l
```

Expected: the PR number, then the close confirmation. The last command prints `0`, which means the remote branch is gone. main never changed.

**After the PR is merged:** revert on a new branch from `origin/main`, then open a PR (humans merge).

```bash
REPO=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral; RB=/mnt/c/Users/DangT/Documents/GitHub/hc-w01-revert; set -o pipefail
git -C "$REPO" fetch origin
git -C "$REPO" worktree add "$RB" -b revert/w01-harness-agents origin/main
cd "$RB"
git log --oneline --merges -1 --grep "feat/w01-harness-agents"
```

Then pick the one line that matches how the PR was merged:
- Merge commit: `git revert --no-edit -m 1 <merge-sha>`
- Squash merge: `git revert --no-edit <squash-sha>`
- Rebase merge: `git revert --no-edit <C4-sha-if-any> <C3-sha> <C2-sha> <C1-sha>`, newest first

Then run the block below.

```bash
RB=/mnt/c/Users/DangT/Documents/GitHub/hc-w01-revert; set -o pipefail
cd "$RB"
git diff --name-only HEAD~1 HEAD
git push -u origin revert/w01-harness-agents
gh pr create --base main --title "revert: W-1 harness subagents" --body "Reverts W-1 (C1–C3, and C4 if present)."
```

Expected: the diff lists only the W-1 files (see [Commit plan](#commit-plan)).

Order matters for a partial revert:
- Reverting only C1 leaves `harness.md` naming files that no longer exist. The drift check then fails, which is correct and loud.
- Reverting only C2 restores "No subagent definitions are checked into this repo" while the files still exist. That makes the doc false, and only the manual 008 gate (or Task 9's test, if it landed) would catch it.

After a full revert:
- the HC-AGENTS tests are gone;
- `.claude/agents/` is ignored again;
- the drift check passes on `7b2ff1f`'s text;
- the CLAUDE.md/AGENT.md collected-count slots return to their start values.

## Owner sign-offs

- [ ] **D1 / D1-scope merge.** I approve merging this PR, which authors the five agents as specified. Signed: ____________ Date: ________
- [ ] **OG-3 (not licensed by D1; optional).** Approve Task 9: move HC-AGENTS-008 into the collected backend suite, so CI `backend-tests` fails when harness.md stops naming an agent by full path or when a `docs/agentic` path does not resolve. No `ci.yml` step is added. Unsigned, Task 9 does not run, and 008 stays a manual gate. Signed: ____________ Date: ________
- [ ] **OG-1 (not licensed; optional).** Enforce `windows-bootstrap-engineer`'s write scope with a frontmatter `PreToolUse` hook matching `Edit` that denies paths outside `dev.ps1`/`dev.bat`. This adds a hook, and requires amending the CS4610 README line 13 and ledger H6. Signed: ____________ Date: ________
- [ ] **OG-2 (not licensed; optional).** Give `verification-engineer` `Bash` so it can run tests. It would then no longer be read-only; harness.md, HC-AGENTS-005 and the body would all change. Signed: ____________ Date: ________
- [ ] **OG-4 (not licensed; optional).** Widen `write_scope` beyond `dev.ps1`, `dev.bat` (name the paths): ____________ Signed: ____________ Date: ________
- [ ] **OG-5 (not licensed; optional).** Make the patient-data boundary enforceable. A committed `.claude/settings.json` would carry `permissions.deny` read rules for the `data` directory, `*.db` and `.env` files, so Claude Code itself refuses those reads in any checkout. It would also mean:
  - un-ignoring `.claude/settings.json`, which changes HC-AGENTS-002;
  - amending CS4610 README line 13 ("no `.claude/settings.json`");
  - verifying the rule syntax against the Claude Code settings docs before use.

  Until then, the boundary is the fresh-worktree check. Signed: ____________ Date: ________

## Commit plan

| # | Task | Prefix and subject | Explicit pathspecs | `git diff --cached --name-only` must equal |
|---|---|---|---|---|
| C1 | Task 4 | `feat(harness): commit the five named subagents and un-ignore .claude/agents/` | the 5 `.claude/agents/<name>.md` paths (after the `git status --short --untracked-files=all .claude/` check), `.gitignore`, `src/backend/tests/test_claude_agent_definitions.py`, `CLAUDE.md`, `AGENT.md` | those 9 |
| C2 | Task 5 | `docs: name the committed subagents in harness docs` | `docs/agentic/harness.md docs/agentic/roadmap.md` | those 2 |
| C3 | Task 6 | `docs: record the committed subagents in the coursework scope note and claims ledger` | `CS4610_Report_Demo/README.md docs/capstone-report/claims-ledger.md` (+ matrix, contract if Task 6 Step 3 edited them) | those 2 (or 4) |
| C4 | Task 9, only after OG-3 | `feat(harness): run the harness drift gate in the backend suite (OG-3)` | `src/backend/tests/test_claude_agent_definitions.py CLAUDE.md AGENT.md` | those 3 |

Collection changes only in C1 (+7: HC-AGENTS-001…007) and C4 (+1: HC-AGENTS-008). Each of those commits carries its own measured collected-count update, and nothing else in CLAUDE.md or AGENT.md. C2 and C3 change no test. The final collected total is `START_COLLECTED + 7`, or `+ 8` with C4.

Never `git add -A`, `git add .`, or `git add .claude/`. Every message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Execution record

*(The executor fills this in. It is the dated log AGENT.md's definition of done requires; no `TASK_LIST.md` entry, to avoid colliding with P4 Task 16.)*

- Worktree / HEAD:
- Interpreter (`--version`), `git --version`, PyYAML version:
- START_COLLECTED / START_FAILURES:
- Task 0 Step 3 drift output:
- Task 0 Step 5 quoted doc sentences (F1–F6):
- HC-AGENTS-008 gate output: RED (Task 5 Step 1), GREEN (Task 5 Step 5, Task 8 Step 2):
- Task 7 Step 1 `phi_gate_exit` (must be 0), Step 1b seven `-> exit=1` lines plus `after_cleanup_exit=0` and `find_error_exit=1`, Step 6 output:
- OG-3 signed? Task 9 ran? C4 SHA:
- Pass-count wording in CLAUDE.md/AGENT.md: re-measured (environment) or flagged in the PR:
- Red outputs (per test ID):
- Task 4 Step 4 honesty review (a/b/c per agent):
- Task 7 transcripts:
- END collected / failures; gate outputs:
- PR URL:

---

Related: [program P3](../capstone-report/implementation-program.md) · [plan 01 (merge)](../../audit/2026-09-25/plans/01-merge-branches.md) · [plan 04 (doc drift, Task 15)](../../audit/2026-09-25/plans/04-doc-drift-sweep.md) · [harness.md](../agentic/harness.md) · [roadmap.md](../agentic/roadmap.md) · [CLAUDE.md](../../CLAUDE.md) · [AGENT.md](../../AGENT.md)
