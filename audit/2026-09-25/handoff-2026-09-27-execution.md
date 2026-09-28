# Handoff — Execution Start (2026-09-27)

**For:** the next orchestrator/implementer session on Asclexis / HealthCentral.
**From:** the 2026-09-27 reconciliation pass. Planning and docs only: nothing was merged, committed or implemented.
**Supersedes:** `handoff-prompt-claude-orchestrator.md` and audit §22 for sequencing.

Paste the block below into a fresh high-reasoning session.

---

```text
You are the execution orchestrator for Asclexis (local-first medical-results
companion; FastAPI + per-profile SQLCipher vaults + React/TS) and a CS4610
capstone on agentic SWE. Working dir: /mnt/c/Users/DangT/Documents/GitHub/HealthCentral

READ FIRST (binding, in order):
1. CLAUDE.md, AGENT.md, docs/agentic/recurring-failures.md
2. docs/capstone-report/owner-decisions-2026-09-27.md   <- what the owner approved, verbatim scope
3. docs/capstone-report/implementation-program.md       <- phases, gates, measured acceptance
4. docs/capstone-report/architecture-engineering-contract.md (rules C-*)
5. docs/capstone-report/specs-compliance-matrix.md       (requirement rows)
6. audit/2026-09-25/handoff-2026-09-27-execution.md      (this file: readiness + test-case requirements)
7. The plan for the phase you are executing: audit/2026-09-25/plans/0N-*.md (read its 2026-09-27 banner first)

MISSION: execute the program from P0-B onward, one phase per branch/worktree,
stopping at every PR for the owner to merge. Never widen an owner approval beyond
the option text quoted in owner-decisions-2026-09-27.md.

START HERE:
  P0-B  docs branch: commit the reconciliation package + regenerate docs index
  D9    build a Python 3.11 venv from src/backend/requirements.txt; record the
        measured collected + pass counts on main with it
  P1    land branch B then branch A (plan 01) in a clean worktree -> PR -> STOP

HARD RULES:
- Measure, never assume: every phase records `<venv>/bin/python -m pytest tests/
  -p no:cacheprovider -q` on its START tree and END tree (collected + failures),
  with interpreter + command. Acceptance = start + tests you added; failures ⊆ start.
- Stage explicit pathspecs; check `git diff --cached --name-only` before commit;
  never `git add -A`/`.`; never `git reset` shared work; never touch the owner's
  .serena/project.yml unless asked.
- Ask-first files stay read-only unless the owner approves that exact change:
  modules/interpret_safety.py, redaction.py, faithfulness.py, verifier_agent.py,
  anything auth/encryption. Approved exceptions: the plan-02 core/auth.py hooks (D6),
  the utcnow swap in api/profiles.py auth hunks (D13), the FK pragma listener
  beside the SQLCipher key hook (D5).
- Route/auth/status tests go through HTTP: tests/support/routes.py::route_client.
  Break the code on purpose once and see each new test go red.
- Never lower a threshold (eval bars, 0.6 faithfulness, 0.7 embedding test).
- Humans merge. Report command + actual output for every claim.

STOP AND ASK when: a plan needs an ask-first edit not listed above; an owner
approval's text doesn't clearly cover the change; the D8 bundling delivery
mechanism is reached; any test failure is not explained by the phase's own change.
```

---

## 1. State snapshot (verified 2026-09-27)

| Item | Value |
|---|---|
| main | `40f590e`; `origin/main` matched at the last fetch (no fetch was run this pass) |
| Branch A `origin/claude/asclexis-repo-audit-349pjq` | 5 ahead / 0 behind, tip `692fdf3` |
| Branch B `origin/claude/healthcentral-agentic-research-r1n54x` | 19 ahead / 0 behind, tip `7b2ff1f` |
| A onto B conflicts | 5 files: `AGENT.md`, `CLAUDE.md`, `docs/INDEX.md`, `docs/_link_graph.json`, `docs/agentic/recurring-failures.md` |
| Collected tests (Windows Py 3.13.7) | main 1245 · A 1248 · B 1288 · merge-tree 1291. Pass counts were **not** measured |
| Working tree | uncommitted owner edits in `.serena/project.yml` and `docs/INDEX.md`; untracked `audit/` and `docs/capstone-report/` (this package) |
| Interpreters | `python` is absent; `/home/danny/venvs/healthcentral-backend` has no SQLAlchemy; `/mnt/c/Python313/python.exe` collects. D9 → build a 3.11 venv |
| Docs gates | `docs_lint.py` passes. `generate_docs_index.py --check` is stale (fixed by P0-B) |

## 2. First three steps, concretely

**Step 1 — P0-B.** Commit the package on a docs branch; the owner chose this.
1. `git switch -c docs/capstone-reconciliation-2026-09-27`
2. `git status --short audit/ docs/capstone-report/` → confirm these contain only package files.
3. `git add audit/ docs/capstone-report/ docs/INDEX.md`. These directories are wholly package-owned. `docs/INDEX.md` holds the owner's edits, which the owner approved committing.
4. `python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py --link-graph`
5. `git add docs/INDEX.md docs/_link_graph.json && git diff --cached --name-only`. Leave `.serena/project.yml` out: "handled separately" means ask the owner.
6. `git commit -m "docs: reconcile the 2026-09-25 audit package and add capstone architecture, contract, matrix and program"`
7. Verify: `python3 scripts/docs_lint.py` → "Docs lint passed."; `python3 scripts/generate_docs_index.py --check` → exit 0.
8. Push and open a PR. **STOP** for the owner to merge.

**Step 2 — D9.** Build the 3.11 venv on the machine that will run the gates.
- Command: `python3.11 -m venv ~/venvs/asclexis-311 && ~/venvs/asclexis-311/bin/pip install -r src/backend/requirements.txt`. If `python3.11` is missing, report that and ask.
- SQLCipher needs `libsqlcipher-dev`, as in CI.
- Record `cd src/backend && ~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q` on main. Expect `test_api_rag_index_002b` to fail if no embedding model is present.

**Step 3 — P1.** Follow plan 01 in a clean worktree.
- Merge order: branch B first (it carries the fail-closed security gate), then branch A.
- Resolve the 5 conflicts per plan 01's table.
- Acceptance is listed in program P1. In particular, the security gate must exit non-zero on a missing report.

## 3. Execution order after P1

P2 notifications → P3 (**new plan needed**, see §4) → P4 doc drift (Task 12 unblocked: delete) → **governance commit** (§5) → P5 utcnow → P6 FK → P7 reset → P8 packet.

The G-phases in §5 run after their dependencies land. Plans must never edit the same file concurrently; the shared-file order is in the program's ground rules.

## 4. Answer to "are the plans ready, with contracts, specs and test cases?"

**Partly.**
- 5 of the 8 plans are executable TDD plans with named test cases.
- 3 plans need rework because the owner's answers changed their scope.
- 11 approved work items have **no plan yet**.
- The contract and matrix supply requirements and verification commands, but **no plan cites contract IDs**, because the plans were written before the contract.

Measured structure (`grep` counts over `audit/2026-09-25/plans/*.md`, 2026-09-27):

| Plan | Tasks | Checkbox steps | Named test IDs | Interfaces blocks | Readiness after the 2026-09-27 decisions |
|---|---|---|---|---|---|
| 01 merge | 8 | 43 | 2 (branch tests carried in) | 0 | **Ready** through stop gates, after P0-B + D9 |
| 02 scheduler | 7 | 37 | 12 (HC-NSW) | 5 | **Ready** (D6 approved). Add the `caplog` no-PHI test (program P2) |
| 03 phantom layer | 0 | 11 | 0 | 0 | **Not ready.** It is a decision plan scoped for Branch B/3 agents; the owner chose A with 5 agents. Needs a new plan (§5, W-1) |
| 04 doc drift | 16 | 54 | 0 (docs) | 0 | **Ready with amendment.** Add the 7 architecture-doc divergences and the D3/D4/D11 doc wording as tasks |
| 05 utcnow | 15 | 61 | 6 | 0 | **Ready** (D13 approved). Directory adds need the status check |
| 06 FK | 5 | 37 | 7 (HC-FKA etc.) | 3 | **Ready** (D5 approved) through the orphan-report stop |
| 07 reset | 3 | 14 | 16 (HC-RESET) | 2 | **Ready with one decision.** FTS `search_records*` tables (N-02). Recommended engineering default: clear both tables and assert it; flag in the PR |
| 08 gated packet | 7 | 33 | 0 (docs) | 1 | **Ready with amendment.** Brief 4 now uses the HIPAA-aligned posture (D10); brief 5 cites the HC-M11 flag-only approval |

**Where requirements live today:**

| Need | Source |
|---|---|
| Rules | contract C-* |
| Current-state requirements | matrix rows |
| Measured acceptance and stop gates | program phases |
| Test-case requirements for the unplanned work | §5 below |

Each new plan must be written with the `writing-plans` skill, cite its contract and matrix IDs, and include the test cases below as failing-first tests.

## 5. Approved work with no plan yet: requirements and test cases

The IDs below are proposed; confirm there are no collisions with `grep -rn "HC-XXX" src/backend/tests` before use.

| W | Decision | Spec requirement | Contract / matrix | Required test cases (fail first) | Measured acceptance |
|---|---|---|---|---|---|
| W-1 | D1 Branch A, 5 agents | `.claude/agents/` with the 5 names in `docs/agentic/harness.md:25-28`. 4 are read-only (`tools: Read, Grep, Glob`). `windows-bootstrap-engineer` gets a bounded write scope declared in frontmatter. `.gitignore` gets `!.claude/agents/`. Drop no other claim silently | GATE-09 | (1) `git check-ignore .claude/agents/x.md` → not ignored. (2) Each file's frontmatter parses, and the 4 scanners list no write tools. (3) `scripts/harness_drift_check.py` (from branch B) exits 0 | 5 files committed; drift check exit 0; harness/roadmap claims true |
| W-2 | D3 | The doctor summary (text/html/pdf) passes strict `RedactionEngine` before render. CSV/JSON stay unredacted as named exceptions in CLAUDE.md and `data-privacy.md` | C-REDACT-1 / PRIV-04 | HC-EXPR-001: doctor summary with a PHI fixture (name, DOB, MRN) contains none of them, in all 3 formats. HC-EXPR-002: CSV/JSON unchanged byte-for-byte vs baseline. HC-EXPR-003: an HTTP route test through `route_client` | 3 new tests; failures ⊆ start |
| W-3 | D4 | Trends points carry `user_verified`, and the UI marks unverified points. Legacy RAG observation and chunk retrieval filter `user_verified == True` | C-VERIFY-2 / SAFE-02 | HC-VER-001: an unverified observation is absent from legacy RAG context (`modules/rag.py:322-328`). HC-VER-002: the trends response flags it `user_verified=false`. Vitest: the chart renders the unverified marker | backend + vitest tests green; the agent golden set is unchanged |
| W-4 | G-B5 | On the legacy path, `is_valid=False` returns the existing abstention/knowledge-fallback template, not the answer. Add a CI eval gate for the legacy path; the 0.6 threshold is unchanged | C-SAFE-2 / SAFE-04 | HC-LEG-001: a forced faithfulness of 0.5 yields the abstention template over HTTP. HC-LEG-002: an eval gate on a seeded uncited answer fails CI | the new CI job fails on the seed and passes on main |
| W-5 | D11 | Remove the contradictory `[YOUR_RESULTS:N]`/`[REFERENCE:N]` citation instruction from the legacy prompt (`modules/rag.py:120-132`). Docs describe `[cite:N]` as validated and the others as context labels. No validator edit | C-SAFE-5 / SAFE-08 | HC-CIT-001: the prompt string contains exactly one citation-format instruction. Existing validator tests unchanged | docs lint passes; RAG tests pass |
| W-6 | D12 | External runner: strict redaction is **unconditional**, with the dev bypass at `core/external_runner.py:201` removed. Break-glass is allowed only with an audit event and a UI warning. CLAUDE.md names the runner as a ModelRunner exception | C-REDACT-2, C-LLM-1 / LOCAL-04, LLM-01 | HC-EXT-001: `redaction_enabled=False` in dev still redacts. HC-EXT-002: break-glass writes an audit row with no PHI. HC-EXT-003: the frontend shows the warning (vitest) | 3 tests; `tests/test_redaction.py` still green |
| W-7 | D7 | Rewrite tiered interpretation (`modules/interpret.py:877` `interpret_with_model`, `model_selector.run_inference`) to call ModelRunner, then wire it to a route. Remove the `from llama_cpp import` at `modules/model_selector.py:438`. `interpret_safety.py` stays read-only | C-LLM-1, C-LLM-2 / LLM-02/03 | HC-LLMB-001: the import-boundary test fails on any `llama_cpp` import outside `core/llm/`. HC-INT-0xx: the route returns interpret_safety-checked output over HTTP, and the no-LLM fallback works | boundary test in CI; `grep -rnE "from llama_cpp" src/backend \| grep -v tests` → only the provider |
| W-8 | D8 | The embedding model ships with the app and loads from a local path, with HF offline at runtime. **Open:** delivery before an installer exists. Ask the owner; do not commit weights without approval | C-LOCAL-2 / LOCAL-03 | HC-EMB-001: with the network blocked and an empty HF cache, the embedding module loads from the bundled path or fails closed. It must not silently use the fallback | test green with the socket blocked |
| W-9 | D10 | Plan 08 brief 4 designs retention as if HIPAA applied: six-year Security Rule documentation, audit data protection. It states this as an owner design choice, never as legal status | C-AUDIT-2 / AUD-03, AUD-04 | docs only: packet review checklist | brief signed by the owner |
| W-10 | governance | One `docs:` commit amending `CLAUDE.md` (D3 exceptions, D12 exception) and `docs/compliance/data-privacy.md` (D3, D4), citing `owner-decisions-2026-09-27.md` | contract classes | `python3 scripts/docs_lint.py` | lint passes; the diff contains only these files |
| W-11 | remaining gaps | G-B1 (HTTP tests for profile guards + 4 audit rows), G-B2 (on-disk ciphertext test), G-B4 (single-head migration test, CI build/eslint/ruff), G-C1…C4 per the program table | per the program | per the program G-table | per the program |

## 6. Reporting format for every phase PR

1. Start and end measurements: collected, failures, interpreter, command.
2. The list of new tests, and proof each went red first (command + output).
3. Contract IDs and matrix rows affected, and each matrix status change.
4. The files changed (explicit list), plus any owner stop reached.
5. One next action.

Back to: [review follow-up](review/2026-09-27-followup.md) · [implementation program](../../docs/capstone-report/implementation-program.md) · [owner decisions](../../docs/capstone-report/owner-decisions-2026-09-27.md)
