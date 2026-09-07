# Phase C: Agent Instruction Reoptimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `CLAUDE.md` and `AGENT.md` true, make the repo's 18 skills discoverable, and shift both files from procedural scaffolding to intent-plus-invariants.

**Architecture:** Three tasks, each independently reviewable. Task 1 corrects false facts — the highest-severity problem, because an agent that reads a wrong baseline cannot tell drift from its own breakage. Task 2 adds a skill routing table, the highest-value addition since all 18 skills already exist and are simply invisible. Task 3 changes register. Every claim added must be verified by running the command it describes.

**Tech Stack:** Markdown only. No code changes.

**Spec:** `docs/superpowers/specs/2026-07-30-remediation-and-asclexis-design.md` (Phase C)

**Ordering dependency:** Phase C runs **after Phase B**, because Phase B renames the product (and Task 1 of this plan renames it in `AGENT.md`, which Phase B deliberately skipped) and renames the four project-domain skills that Task 2's routing table must list by their new names.

## Global Constraints

- **Keep every existing hard invariant in `CLAUDE.md` verbatim.** They are load-bearing and were not the problem. Reword nothing in that section.
- **No claim ships unrun.** Every factual assertion added or edited must be verified by executing the command it describes and observing the output. This is the whole point of Task 3's verification rule; violating it while writing that rule would be self-defeating.
- The product is **Asclexis** after Phase B. `AGENT.md`'s title and prose change here.
- The four project-domain skills are `asclexis-agent`, `asclexis-backend`, `asclexis-evals`, `asclexis-guardrails` after Phase B Task 3.
- `docs_lint.py` enforces `DOC-004` (canonical docs need `**Owner:**` and `**Refresh Trigger:**`) and `DOC-011` (every doc under `docs/` reachable from the index). Check whether `AGENT.md` and `CLAUDE.md` are in the linter's `CANONICAL_DOCS` list before restructuring their headers.
- Commit style: `docs:` — one commit per task.

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `CLAUDE.md` | Behavioural rules for AI agents — what must stay true | Modify |
| `AGENT.md` | Onboarding briefing — what the project is, where things live, how to verify | Modify |

Both files are small (45 and 47 lines). Keeping them small is a feature: they are read in full at the start of every session, so every line competes for attention. Resist growing them beyond roughly 80 lines each.

---

## Task 1: Correct the false facts

**Files:**
- Modify: `CLAUDE.md:26`
- Modify: `AGENT.md:1` (title), `:26` (test count), and the Key Flows section

**Interfaces:** Consumes nothing; produces the corrected baseline figure used by Task 3's verification rule.

**Why:** Both files claim **"~620 backend tests"**. The real figure is roughly double. A stale baseline is worse than no baseline: an agent that reads "~620", runs the suite, and sees 1205 has no way to tell whether it is looking at documentation drift or at something it broke. These are the two files agents trust most.

- [ ] **Step 1: Measure the real numbers — do not copy them from this plan**

```bash
cd /home/user/HealthCentral/src/backend
python -m pytest tests/ -p no:cacheprovider -q 2>&1 | tail -3
```

Record the exact passed/failed counts. At the time of writing this plan the figure was 1205 passed / 1 failed, but Phase A adds tests, so **use what you measure**, not what this plan says.

```bash
cd ../frontend && npx vitest run 2>&1 | grep -E "Tests "
HC_E2E_CHROMIUM_PATH=/opt/pw-browsers/chromium npx playwright test --project=chromium 2>&1 | tail -3
```

Record the vitest and Playwright figures too.

- [ ] **Step 2: Correct `CLAUDE.md:26`**

Replace:

```markdown
- Baseline: ~620 backend tests pass; 1 known env-only failure (embedding similarity — needs a real embedding model). Do not "fix" it by lowering the 0.7 threshold.
```

with (substituting your measured count):

```markdown
- Baseline: **<measured> backend tests pass**; 1 known env-only failure (`test_api_rag_index_002b`, embedding similarity — needs a real embedding model). Do not "fix" it by lowering the 0.7 threshold. If your measured count differs from this line, the line is stale — update it in the same commit rather than working around it.
```

- [ ] **Step 3: Correct `AGENT.md:26`**

Replace `# backend tests (~620 pass)` with `# backend tests (<measured> pass, 1 known env-only failure)`.

- [ ] **Step 4: Rename the product in `AGENT.md`**

Phase B deliberately skipped this file. Change the title `# AGENT.md — HealthCentral` to `# AGENT.md — Asclexis`, and replace remaining `HealthCentral` prose occurrences:

```bash
grep -n "HealthCentral\|healthcentral" AGENT.md
```

Update each. The `skills/` sentence must now name `asclexis-*`, and the master DB is `asclexis.db`.

- [ ] **Step 5: Refresh the Key Flows section**

`AGENT.md`'s "Key flows" lists three flows and predates several features. Add these two, keeping the existing terse style:

```markdown
4. **Backup → restore**: `api/backup` (create/verify/download/restore/prune) → `scripts/backup.py` engine → per-profile `backups/{profile_id}/`. Backups are **deliberately unredacted** (a redacted backup cannot be restored) and are the one export-shaped path that is. Restore is profile-scoped: vault and sealed keys verbatim, only this profile's master row re-applied. `modules/backup_scheduler` runs due backups from the lifespan task and records `skipped_locked` honestly when a vault is closed.
5. **Profile lifecycle**: create (`api/profiles`) issues a one-time recovery code sealing a *second copy of the same DEK* (`SEC-RECOV-001`); `DELETE /profiles/{id}` is an ordered crypto-erase — sealed keys first as the commit point, then the vault sweep, then the backup sweep, then one master transaction that purges audit rows and writes an anonymized tombstone.
```

- [ ] **Step 6: Verify every claim you just wrote**

For each factual statement added in Step 5, confirm it against the code:

```bash
cd /home/user/HealthCentral/src/backend
grep -n "skipped_locked" modules/backup_scheduler.py models/backup_schedule.py
grep -n "Step 3\|Step 4\|Step 5\|Step 6" api/profiles.py
grep -n "def restore" scripts/backup.py
```

If any statement does not match the code, fix the statement — not the code.

- [ ] **Step 7: Run the docs gates**

```bash
cd /home/user/HealthCentral
python3 scripts/docs_lint.py; echo "docs_lint=$?"
python3 scripts/generate_docs_index.py --check; echo "index=$?"
```

Expected: both `=0`.

- [ ] **Step 8: Commit**

```bash
git add CLAUDE.md AGENT.md
git commit -m "docs: correct the test baseline and refresh the agent briefing

Both files claimed ~620 backend tests, roughly half the real figure, in the two
documents agents trust most. A stale baseline is worse than none: an agent that
reads 620, runs the suite and sees twice that cannot tell drift from its own
breakage.

Also renames the product in AGENT.md (Phase B skipped this file so it would not
be rewritten twice) and adds the backup/restore and profile-lifecycle flows,
each claim checked against the code that implements it."
```

---

## Task 2: Make the skills discoverable

**Files:**
- Modify: `AGENT.md` (skills section)
- Modify: `CLAUDE.md` (new short section)

**Interfaces:** Consumes the renamed `asclexis-*` skill names from Phase B Task 3.

**Why:** 18 skills exist — 14 process skills in `.claude/skills/` and 4 domain skills in `skills/`. `CLAUDE.md` does not mention skills at all. `AGENT.md` names the two directories and warns not to confuse them, but never names a single skill or says when to reach for one. An unreferenced skill is a skill nobody invokes. This is the highest-value change in the phase because the capability already exists and is simply invisible.

- [ ] **Step 1: Inventory the actual skills — do not trust this plan's list**

```bash
cd /home/user/HealthCentral
for f in .claude/skills/*/SKILL.md skills/*/SKILL.md; do
  echo "--- $f"
  sed -n '2,4p' "$f"
done
```

This prints each skill's `name` and `description` frontmatter. The routing table must match what you see; skills may have been added or renamed.

- [ ] **Step 2: Add the routing table to `AGENT.md`**

Replace the existing sentence about the two skills directories with a section. Use the descriptions from Step 1 to write the "when" column — do not paraphrase from memory:

```markdown
## Skills

Two directories, different purposes. `.claude/skills/` holds vendored **process**
skills; `skills/` (no dot) holds this project's **domain** skills. Invoke by name.

| Skill | Reach for it when |
|---|---|
| `test-driven-development` | Implementing any feature or bugfix, before writing implementation code |
| `systematic-debugging` | Any bug, test failure, or unexpected behaviour, before proposing a fix |
| `writing-plans` | You have a spec for a multi-step task, before touching code |
| `executing-plans` | You have a written plan to execute with review checkpoints |
| `subagent-driven-development` | Executing a plan whose tasks are independent |
| `brainstorming` | Before any creative work — new features, components, behaviour changes |
| `verification-before-completion` | About to claim work is complete, fixed, or passing |
| `requesting-code-review` | Finishing a task or feature, before merging |
| `receiving-code-review` | Acting on review feedback, especially if it seems questionable |
| `dispatching-parallel-agents` | 2+ independent tasks with no shared state |
| `using-git-worktrees` | Feature work needing isolation from the current workspace |
| `finishing-a-development-branch` | Implementation done and tests pass; deciding how to integrate |
| `writing-skills` | Creating or editing a skill |
| `using-superpowers` | Starting a conversation — establishes how to find and use skills |
| `asclexis-backend` | Backend work: routes, models, migrations, the dual Alembic chains |
| `asclexis-agent` | The assistant/agent graph, RAG, prompt composition |
| `asclexis-guardrails` | Safety guards, injection filtering, redaction gates |
| `asclexis-evals` | Golden sets, eval axes, the agent eval gate |

Full descriptions: [`.claude/skills/README.md`](.claude/skills/README.md) and
[`skills/README.md`](skills/README.md).
```

- [ ] **Step 3: Add a short pointer to `CLAUDE.md`**

`CLAUDE.md` is behavioural rules, so it gets a rule rather than a table. Add as a new section before `## Commit style`:

```markdown
## Skills

This repo ships 18 skills — process skills in `.claude/skills/`, project-domain
skills in `skills/`. The routing table is in [AGENT.md](AGENT.md#skills).

- Check for a covering skill **before** improvising a workflow. A skill exists
  because someone already worked out the right approach and wrote it down.
- `test-driven-development` and `systematic-debugging` apply to essentially all
  feature and bug work in this repo. Reach for them by default, not as a
  ceremony when a task feels large.
```

- [ ] **Step 4: Verify every skill name in the table resolves**

```bash
cd /home/user/HealthCentral
for s in $(grep -oE '^\| `[a-z-]+`' AGENT.md | tr -d '|` '); do
  if [ -f ".claude/skills/$s/SKILL.md" ] || [ -f "skills/$s/SKILL.md" ]; then
    echo "OK    $s"
  else
    echo "BROKEN $s"
  fi
done
```

Expected: every line `OK`. Any `BROKEN` line is a routing table entry pointing at a skill that does not exist — fix the table.

- [ ] **Step 5: Run the docs gates**

```bash
python3 scripts/docs_lint.py; echo "docs_lint=$?"
python3 scripts/generate_docs_index.py --check; echo "index=$?"
```

Expected: both `=0`. `DOC-007` validates relative links, so the two README links must resolve.

- [ ] **Step 6: Commit**

```bash
git add AGENT.md CLAUDE.md
git commit -m "docs: give the 18 repo skills a routing table

CLAUDE.md never mentioned skills at all; AGENT.md named the two directories and
warned not to confuse them but never named a skill or said when to use one. An
unreferenced skill is a skill nobody invokes.

Every entry verified to resolve to an actual SKILL.md."
```

---

## Task 3: Shift register — intent and invariants over scaffolding

**Files:**
- Modify: `CLAUDE.md` (sections 1–4, leaving Hard Invariants untouched)
- Modify: `AGENT.md` ("Definition of done")

**Interfaces:** Consumes the corrected baseline from Task 1.

**Why:** Neither file contains a model-version string, so this is not a find-and-replace — it is a change of register. The useful adjustment for a more capable model is fewer procedural rails and sharper statements of what must remain true: the model can derive the steps, but it cannot derive an invariant nobody wrote down.

The verification rule earns its place because this session produced a concrete, expensive counterexample. **1205 green backend tests coexisted with a restore endpoint that returned 400 for every request and a backup download that carried every profile's password hash**, because the route tests called handlers as plain functions and the isolation assertion checked filenames rather than file contents.

- [ ] **Step 1: Add the verification rule to `CLAUDE.md` section 4**

Under `## 4. Loop toward verifiable success criteria`, add:

```markdown
- **Run verification; never assert it.** Report the command and its actual
  output. "Tests pass" without the output is not a result. If a check was
  skipped, say which and why.
- **A green suite is evidence, not proof.** On this branch 1205 passing backend
  tests coexisted with a restore endpoint that returned 400 for every request
  and a backup download that shipped every profile's password hash. The route
  tests called handlers as plain functions, so FastAPI's dependency graph never
  ran; the isolation test asserted on filenames, so it could not see data
  leaking inside a file. Ask what your test would fail to notice.
- **Route tests go through HTTP.** A test that calls a route function directly
  cannot see a broken `Depends(...)`. Use `tests/support/routes.py::route_client`
  for anything asserting auth, path scoping, or status codes.
```

- [ ] **Step 2: Add parallel-investigation guidance to `CLAUDE.md` section 1**

Under `## 1. Surface assumptions — never guess silently`, add:

```markdown
- For read-only investigation across unfamiliar areas, prefer one broad
  exploration pass over many narrow sequential greps; dispatch independent
  searches in parallel when they share no state. Then verify what matters
  yourself — an agent's report is a lead, not a finding.
```

- [ ] **Step 3: Trim procedural scaffolding where an invariant already covers it**

Read `CLAUDE.md` sections 1–4 in full. Where a bullet prescribes a *sequence* that a stated invariant already implies, compress it to the invariant. Where a bullet states something that must remain true, keep it verbatim.

**Do not touch `## Hard invariants`.** Every line there is load-bearing.

Target: sections 1–4 get shorter, the file's total length grows by no more than ~15 lines net after Steps 1–2.

- [ ] **Step 4: Sharpen `AGENT.md`'s Definition of done**

Replace the existing "Definition of done" paragraph with:

```markdown
## Definition of done

A task is done when all of the following are true **and you have seen the output
that proves each one**:

- Tests written or updated, and the new ones observed failing before the fix.
- `cd src/backend && python -m pytest tests/ -p no:cacheprovider -q` shows no new
  failures against the baseline above.
- `cd src/frontend && npx tsc --noEmit` is clean and `npx vitest run` passes.
- The app boots: `python -c "from main import app"`.
- Every hard invariant in [CLAUDE.md](CLAUDE.md) still holds.
- Non-trivial work logged in `docs/features/TASK_LIST.md` Session Notes, or a
  dated file under `docs/plans/` for a substantial standalone plan.

"I believe these pass" is not done. Run them.
```

- [ ] **Step 5: Verify every command in the Definition of done actually works**

Run each of the four commands listed. If any fails or has different output than the text implies, fix the text.

- [ ] **Step 6: Confirm the hard invariants are byte-identical**

```bash
cd /home/user/HealthCentral
git diff CLAUDE.md | grep -E "^[-+]" | grep -iE "invariant|SQLCipher|ProfileDbSession|redaction|audit logging|REFERENCE|migration"
```

Expected: **no output.** Any hit means you modified an invariant line — revert that specific change.

- [ ] **Step 7: Run the docs gates and check length**

```bash
python3 scripts/docs_lint.py; echo "docs_lint=$?"
python3 scripts/generate_docs_index.py --check; echo "index=$?"
wc -l CLAUDE.md AGENT.md
```

Expected: gates `=0`; both files under ~80 lines. They are read in full every session, so length is a cost.

- [ ] **Step 8: Commit**

```bash
git add CLAUDE.md AGENT.md
git commit -m "docs: state invariants and require verification, not scaffolding

Neither file contained a model-version string, so this is a change of register
rather than a find-and-replace: intent plus what must stay true, since the steps
are derivable but an unwritten invariant is not.

The verification rules are earned. On this branch 1205 passing backend tests
coexisted with a restore endpoint that 400'd every request and a download that
shipped every profile's password hash — the route tests called handlers as plain
functions and the isolation assertion checked filenames. Says so explicitly, so
the next reader knows why the rule exists.

Hard invariants left byte-identical."
```

---

## Task 4: Final verification

**Files:** none

- [ ] **Step 1: Confirm both files are true, claim by claim**

Re-read `CLAUDE.md` and `AGENT.md` top to bottom. For each factual claim — a path, a command, a count, a module name — run or check it. List in your report every claim you verified and how.

- [ ] **Step 2: Confirm no stale product name remains**

```bash
cd /home/user/HealthCentral && grep -n "HealthCentral\|healthcentral" CLAUDE.md AGENT.md
```

Expected: no output.

- [ ] **Step 3: Run all gates**

```bash
python3 scripts/docs_lint.py; echo "docs_lint=$?"
python3 scripts/generate_docs_index.py --check; echo "index=$?"
python3 scripts/feature_list_lint.py; echo "feature_list=$?"
```

Expected: all `=0`.

- [ ] **Step 4: Sanity-check that the files still serve a cold reader**

Read `AGENT.md` as if you had never seen this repo. Can you find the backend routes, run the tests, and learn which files require asking first? If not, the compression in Task 3 Step 3 went too far — restore what a newcomer needs.

---

## Self-Review

**Spec coverage.** C1 → Task 1; C2 → Task 2; C3 → Task 3; the spec's Phase C verification requirement ("every factual claim spot-verified by running the command it describes") → Task 1 Step 6, Task 2 Step 4, Task 3 Step 5, and Task 4 Step 1.

**Placeholders.** None. The routing table is written out in full; the Definition of done is written out in full; the compression step in Task 3 names its criterion (sequence → invariant) and its guard (Step 6 asserts the invariants are byte-identical) rather than saying "tidy up".

**Type consistency.** N/A — no code. Cross-file consistency instead: the four `asclexis-*` skill names in Task 2's table match Phase B Task 3's renames; the baseline figure in Task 1 Step 2 is the one Task 3's Definition of done refers to as "the baseline above"; `tests/support/routes.py::route_client` cited in Task 3 Step 1 is created by Phase A Task 1.

**Cross-phase dependency, flagged.** Task 3 Step 1 references `tests/support/routes.py`, which **Phase A Task 1 creates**. If Phase C somehow runs before Phase A, that reference dangles. Verify the file exists before writing that bullet; if it does not, Phase A has not landed and Phase C should wait.

**One judgement call left to the implementer.** Task 3 Step 3 asks for compression without enumerating every line to cut, because the right cut depends on reading the current text as a whole. The guard is Step 6 (invariants byte-identical) and Step 4 of Task 4 (a cold reader can still onboard). If those two hold, the compression was safe.
