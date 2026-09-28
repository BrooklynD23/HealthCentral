# W-5 Citation-Marker Prompt Alignment (D11) Implementation Plan

**Last Updated:** 2026-09-27
**Owner:** repository owner
**Refresh Trigger:** P1 merges to main, or any commit touches `RAGModule.SYSTEM_PROMPT` / `compose_prompt` / `validate_response` in `src/backend/modules/rag.py` before this plan runs
**Status:** PROPOSED — not executed
Post-review consistency edit 2026-09-27 (baseline-sentence rule); not re-reviewed.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the legacy RAG prompt tell the model to cite in one format only — `[cite:N]`, the only marker the code validates. Then make the four docs that describe this rule say the same thing.

**Architecture:** One constant changes: `RAGModule.SYSTEM_PROMPT` in `src/backend/modules/rag.py`. Three lines keep their context-label text but lose the word "cite", so no line tells the model to cite `[YOUR_RESULTS:N]` or `[REFERENCE:N]`. The validator, claim extractor, context labels and frontend stay unchanged. Three new tests pin the rule:
- HC-CIT-001: the prompt constant.
- HC-CIT-002: the prompt actually sent to the model.
- HC-CIT-003: every marker the prompt asks for is one the validator parses.

**Tech Stack:** Python 3.11 (D9 venv), pytest + pytest-asyncio, `scripts/docs_lint.py`, `scripts/generate_docs_index.py`.

**Spec:** the W-5 row in [handoff §5](../../audit/2026-09-25/handoff-2026-09-27-execution.md). Scope comes from owner decision D11 in [owner-decisions-2026-09-27.md](../capstone-report/owner-decisions-2026-09-27.md).

---

## 1. Approval scope

Owner decision **D11 — "Docs match code"**. The option text, verbatim from [owner-decisions-2026-09-27.md](../capstone-report/owner-decisions-2026-09-27.md):

> "Keep [cite:N] as the validated marker; document [YOUR_RESULTS:N]/[REFERENCE:N] as context labels; remove the contradictory prompt line. … no validator edit."

The ellipsis is in the record itself. Nothing hidden by the ellipsis is licensed.

**This plan does:**
1. Remove the cite-instruction from the three prompt lines that tell the model to cite a context label.
2. Update four doc sections that describe the rule.
3. Move the **collected** test count in `CLAUDE.md`/`AGENT.md` by +3, in the same commit as the tests, because `CLAUDE.md` §4 requires it. Pass-count sentences stay as they are.

**Does NOT license** (each item is owner-gated or belongs to another plan):
1. Any edit to `validate_response` (`rag.py:793-872`), its `citation_pattern` (`:819`), `modules/claim_extractor.py`, `faithfulness.py`, `verifier_agent.py` or `interpret_safety.py`.
2. New instruction content in the prompt. For example, the clause "where N is the number in that source's context label" on rule 1 is **owner-gated** (sign-off line in §12).
3. Renaming or removing the context labels. `compose_prompt` (`rag.py:634-644`) keeps emitting `[YOUR_RESULTS:N]`, `[REFERENCE:N]` and `[USER_DOCUMENT:N]`.
4. Frontend changes, including the chip-numbering mismatch in §14 finding F-3.
5. The Lab Interpreter prompt vocabulary `[KB:…]`/`[INT:…]` (`modules/interpret.py:48-52`, checked by `interpret_safety.py:77`). That is a separate feature and belongs to W-7's territory.
6. Edits to `CLAUDE.md` or `AGENT.md` beyond the baseline count lines that `CLAUDE.md` §4 requires (§3), or to the capstone contract and matrix (§6 hand-offs).
7. Any threshold change, including the 0.6 faithfulness threshold at `rag.py:862`.

## 2. Traceability

| ID | Source | Quoted text (verified by grep, 2026-09-27) |
|---|---|---|
| C-SAFE-5 | [architecture-engineering-contract.md](../capstone-report/architecture-engineering-contract.md) §5 | "**C-SAFE-5 · PROPOSED.** … **Rule:** One citation-marker vocabulary across docs, prompt and validator." Enforced at: "none". |
| C-SAFE-2 | same, §5 | "Legacy path: `modules/rag.py:793` `validate_response` (`[cite:N]`, `:819`) …" |
| C-SAFE-1 | same, §5 | ask-first files: `interpret_safety.py`, `faithfulness.py`, `verifier_agent.py`, `redaction.py` MUST NOT change without owner approval |
| SAFE-08 | [specs-compliance-matrix.md](../capstone-report/specs-compliance-matrix.md) | "\| SAFE-08 \| One citation-marker vocabulary \| `CLAUDE.md:62` … \| the legacy validator uses `[cite:N]`; the prompt instructs both (`modules/rag.py:120-132`) \| — \| none \| **partial** (doc/code mismatch) \|" |
| W-5 | [handoff §5](../../audit/2026-09-25/handoff-2026-09-27-execution.md) | "HC-CIT-001: the prompt string contains exactly one citation-format instruction. Existing validator tests unchanged" · acceptance "docs lint passes; RAG tests pass" |
| D11 | [implementation-program.md](../capstone-report/implementation-program.md) decision table | "Citation-marker vocabulary … **DECIDED: docs match code (`[cite:N]`)**" |

**Line-range correction.** The handoff and SAFE-08 cite `rag.py:120-132`. The prompt constant is actually at `rag.py:123-140` (`main@40f590e`). The contradictory lines are `:128`, `:133` and `:134`, while `:126` holds the `[cite:N]` instruction this plan keeps. `rag.py` is byte-identical at `main@40f590e`, `A@692fdf3` and `B@7b2ff1f` (`git diff --stat` shows it empty for both branches).

### Evidence: `[cite:N]` is the only validated marker

All refs below are `main@40f590e`, which is identical at A and B. Re-verify the line numbers on the post-P1 tree.

| Claim | path:line |
|---|---|
| The validator parses only `[cite:N]` | `src/backend/modules/rag.py:819` `citation_pattern = r"\[cite:(\d+)\]"`; used at `:820` (found IDs), `:823-826` (invalid IDs), `:831-833` ("Report facts section missing citations"), `:842-844` → `:885-887` (maps `[cite:N]` to `retrieved_chunks[N-1]`) |
| The claim extractor feeding faithfulness parses only `[cite:N]` | `src/backend/modules/claim_extractor.py:92` `CITATION_PATTERN = r"\[cite:(\d+)\]"`; consumed through `claim.cited_sources` at `rag.py:972` |
| The frontend parses only `[cite:N]` | `src/frontend/src/services/assistant.ts:378` (extract), `:394` (`[cite:N]` → `[N]`); `src/frontend/src/pages/ExplainAssistant.tsx:374-375`. Identical at A and B |
| The no-LLM fallback emits `[cite:N]` | `src/backend/api/assistant.py:1346` (`main@40f590e`) = `:1403` (`B@7b2ff1f`) |
| Context labels are rendered only by `compose_prompt` | `rag.py:634-644`: observation summaries get `[YOUR_RESULTS:{i}]`; other chunks get `[{source_type.upper()}:{i}]`. Source types are `user_document` (`:238`), `user_observation` (`:440`) and `reference` (`:501`) |
| The contradictory instructions | `rag.py:126` asks for `[cite:N]`. `:128` "must cite [YOUR_RESULTS:N] or user documents". `:133` "Context labeled [YOUR_RESULTS:N] … — cite these in REPORT FACTS". `:134` "Context labeled [REFERENCE:N] … — cite these in GENERAL INFO" |
| No product code parses `[YOUR_RESULTS:N]`/`[REFERENCE:N]` in model output | `git grep -n "YOUR_RESULTS\|REFERENCE:" 40f590e -- src ':!src/backend/tests'` → only `rag.py:128,133,134` (prompt) and `:636` (label). Frontend: 0 hits at main, A and B |
| The agent path has no LLM prompt with markers | `grep -rn "generate_async\|get_model_runner" src/backend/modules/agent` → 0 hits at main and B. Citations are structured objects (`modules/agent/schemas.py:19`, `nodes/draft.py:102`) |
| The legacy path is not cached | `B@7b2ff1f` `api/assistant.py:689-716`: the semantic cache wraps the agent path only, so a prompt change needs no cache-version bump |

**Stop-gate analysis.** The request asked whether removing the instruction changes an output format that the frontend or the faithfulness scorer depends on.
- It does not. Every output consumer parses only `[cite:N]`: the validator, the claim extractor, the frontend and the fallback.
- Today a model that obeys `:128`/`:133` emits `[YOUR_RESULTS:1]`. That answer:
  - fails "Report facts section missing citations";
  - gives the claim extractor no `cited_sources`;
  - shows raw in the UI (`formatResponseText` only rewrites `[cite:N]`).
- The change therefore moves the model *toward* the one format every consumer reads. **No stop gate is triggered.** Task 0 re-checks this on the post-P1 tree.

## 3. Global constraints

- Interpreter: `~/venvs/asclexis-311/bin/python` (D9). If it is absent, **STOP**: D9 has not been executed.
- Python 3.11 syntax only. Do not add `datetime` code; if a timestamp is ever needed, use `core.time.utcnow`.
- No network in any test. The HC-CIT tests patch retrieval and generation; they never load a model.
- Commit prefixes are `fix(rag):` and `docs:`. Stage with explicit pathspecs; never `git add -A` or `git add .`.
- Edited docs get **no new markdown links**. Links would change `docs/_link_graph.json`/`docs/INDEX.md`, which every docs plan shares. Paths go in code spans.
- Record every measurement in §15 of this file. Do not add links there either.
- **Shell rules.** Shell state does not persist between tool calls, so every command block starts with `WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w05` and `cd` to an absolute path under `"$WT"`. Every block that pipes starts with `set -o pipefail`. Where a piped exit code matters, check it as `${PIPESTATUS[0]}` (pytest) and do not rely on the last command's status.
- **Baseline counts move with collection.** `CLAUDE.md` §4 requires the baseline count to be updated "in the same commit" that changes it. This plan adds 3 tests, so commit 1 also updates the **collected-count slots** in `CLAUDE.md` and `AGENT.md`, and nothing else (Task 1 Step 9; program ground rule, owner gate SLOT-RULE). Pass-count sentences change only with a pass count measured in a named environment: interpreter, plus embedding model present or absent. This plan measures none, so they stay as they are and the PR flags them as unverified. Do not describe CI as having a real embedding model: `ci.yml` has no model step, and CI's `test_api_rag_index_002b` result depends on an implicit Hugging Face download (matrix LOCAL-03). This is required by `CLAUDE.md`, not licensed by D11, and does not touch `CLAUDE.md:62`.
- Line numbers in this plan are `main@40f590e` unless labelled otherwise. Re-verify each one on the post-P1 tree before editing.

## 4. Review focus (inputs no task's tests exercise)

1. **Model compliance is behavioural and UNMEASURED.** A live model may still copy a context label into its answer. HC-CIT tests check the prompt, not the model. W-4's legacy eval gate fakes generation, so it cannot measure this either; no plan measures live-model compliance. §10 gives a manual measurement.
2. **Old turns in session history.** Persisted assistant turns written before this change may contain `[YOUR_RESULTS:1]` text. `compose_prompt` feeds them back under SESSION HISTORY (`rag.py:659-675`), where they can act as few-shot examples. That is not an instruction, so HC-CIT-002 correctly ignores it. The effect decays as new turns accumulate, and no code change is licensed.
3. **Chip numbering (pre-existing, finding F-3).** After this change more answers carry `[cite:N]`, so the existing mismatch between text `[N]` and chip `[i+1]` becomes visible more often. It is out of scope and flagged to the owner.
4. **A future second instruction without a bracket template**, such as "cite the results block". HC-CIT-001 and -002 also reject any cite-line that names a context label (`YOUR_RESULTS`, `REFERENCE`, `USER_DOCUMENT`, `USER_OBSERVATION`), bracketed or not. Generic wording with no label name is still invisible (§8).
5. **Frontend regex parity.** `services/assistant.ts:378,394` must keep matching the backend pattern. HC-CIT-003 covers the backend pair (validator + claim extractor) only. A vitest pin would be a follow-up; it is not licensed here.

## 5. Files

**Owned. Create or modify only these:**

| # | File | Change |
|---|---|---|
| 1 | `src/backend/modules/rag.py` | `:128`, `:133`, `:134` inside `SYSTEM_PROMPT` (`:123-140`) only |
| 2 | `src/backend/tests/test_rag_citation_prompt.py` | **create** (HC-CIT-001..003) |
| 3 | `docs/features/01_lab_result_interpreter_architecture.md` | §"Biomarker Grounding", `:195-216` |
| 4 | `docs/compliance/ai-safety.md` | `:20` (one bullet) |
| 5 | `docs/user/faq.md` | `:108-110` (bullets under "What do the [Your Results] / [Reference] labels mean…"; heading kept) |
| 6 | `docs/user/workflows.md` | `:113-116` ("Understanding Citations" body) |
| 7 | `docs/plans/2026-09-27-W05-citation-marker-prompt.md` | this file: §15 execution log only |
| 8 | `CLAUDE.md` | collected-count slots only (main@40f590e and B@7b2ff1f `:30`, `:35`) → START + 3. The pass-count sentence at `:31` is not edited |
| 9 | `AGENT.md` | the collected-count slot in the pytest command comment only (main@40f590e `:57`; B@7b2ff1f `:76`) → START + 3. Its pass figures are not edited |

Why W-5 owns docs 3–6:
- Each section describes the exact prompt rule or its patient-visible result, and nothing else.
- Each becomes false (3, 4) or misleading (5, 6) the moment the prompt changes.
- No other plan touches those sections.

Architecture and canonical docs are handed to P4 instead (§6).

**Read-only.** Stop if any of these needs a change:
- Ask-first files: `modules/interpret_safety.py`, `modules/redaction.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`, `core/auth.py`, any auth or encryption code.
- Also read-only here:
  - `modules/claim_extractor.py`. Task 1 Step 7 breaks it only with a test-local `unittest.mock.patch.object` on `ClaimExtractor.CITATION_PATTERN`; the file is never edited.
  - `rag.py` outside `:128,:133,:134`.
  - `api/assistant.py`, all of `src/frontend/`, all existing tests, `docs/capstone-report/*`.
  - `CLAUDE.md` and `AGENT.md` apart from the baseline count lines (owned rows 8–9). In particular, `CLAUDE.md:62` is not edited here (C-1).

**Shared-file ordering.** No two plans edit the same file at the same time. Whichever lands second rebases and re-verifies line numbers.

| File | Other editors | Order | Reason |
|---|---|---|---|
| `src/backend/modules/rag.py` | W-3 (legacy RAG verified-only, `:323-332` and `:549-553`), then W-8 (`_search_vectors_async`). The W-4 draft (`2026-09-27-W04-legacy-abstain-and-eval-gate.md` §Files) says W-4 does **not** edit `rag.py`; it edits `api/assistant.py`. | File order (canonical, Wave-3 integration B-2): **W-5 → W-3 → W-8**, serial. **Recommended behavioural order: W-5 before W-4.** | W-5 touches only `:128,133,134`. Today a model obeying `:128/:133` yields "Report facts section missing citations", so `is_valid=False`. Once W-4 serves an abstention for `is_valid=False`, that prompt bug would suppress answers that would otherwise pass. W-4's gate fakes generation, so W-5 cannot flip it. |
| `docs/user/faq.md` | P4 Task 7 (P04 §3 row 7, `:44-47`). W-3 edits no docs | any order, serial | disjoint lines |
| `docs/compliance/ai-safety.md` | none planned; W-4 or W-6 might add abstention or external-runner wording | serial | shared file |
| `CLAUDE.md`, `AGENT.md` | W-10 governance (`CLAUDE.md:62` and others); every test-adding plan edits the baseline count lines | serial. Whichever lands later re-measures and rewrites the count from its own START | W-5 edits only the count lines. `CLAUDE.md:62` goes to W-10 (C-1, §6). |

## 6. Hand-offs: doc wording this plan does NOT own

**Collision C-1: `CLAUDE.md:62` (for the orchestrator/owner).**
- The line says: "Outputs are educational, grounded, cited (`[REFERENCE:N]` / `[YOUR_RESULTS:N]`)." This is the stale-authority failure (recurring #8), and it is the root of the drift.
- It is an invariant line. Owner consequence #1 routes invariant edits into one governance `docs:` commit (W-10), which lists D3 and D12 but **not D11**.
- Recommendation: W-10 absorbs it, with owner confirmation (§12). Proposed text:

  > - **No medical advice.** Outputs are educational, grounded, and cited with `[cite:N]` markers (validated by `modules/rag.py::validate_response`; `[YOUR_RESULTS:N]` / `[REFERENCE:N]` are context labels, not citation markers). `interpret_safety` prohibited patterns (diagnosis, dosing) must keep passing.

  The line number is the same at A and B (`:62`). Re-verify after P1.

**Handed to P4.** The program's P4 bullet "the citation-marker vocabulary in docs, after D11" covers these. Run them after W-5 lands, so the docs describe merged code.

| File:line (main@40f590e) | Now | Proposed |
|---|---|---|
| `docs/architecture/pipelines.md:111` | `OUT["cited answer<br/>[REFERENCE:N] / [YOUR_RESULTS:N]"]` | `OUT["cited answer<br/>[cite:N] markers (context labels are not citations)"]` |
| `docs/features/00_features_index.md:38` (canonical: bump Last Updated) | "two citation layers. `[YOUR_RESULTS:N]` cites … `[REFERENCE:N]` cites …" | "two context layers, labelled `[YOUR_RESULTS:N]` (…) and `[REFERENCE:N]` (…); answers cite both with `[cite:N]`" |
| `docs/features/04_self_improvement_loop.md:113` | "`[REFERENCE:N]` / `[YOUR_RESULTS:N]` format preserved" | "`[cite:N]` citation format preserved (`[REFERENCE:N]`/`[YOUR_RESULTS:N]` are context labels)" |
| `docs/features/TASK_LIST.md:63` (optional) | "`[YOUR_RESULTS:N]` chips in ExplainAssistant" | "source chips in ExplainAssistant" |

**Accurate as written, no edit needed:**
- `AGENT.md:69` (main) / `:89` (B), flow 2: describes retrieval labels.
- `docs/brand/brand-guidelines.md:37-38`: "`rag.py` labels retrieved context …".

**Point-in-time, never edit** (plan 04 Global Constraints):
- `docs/plans/2026-06-30-*`, `2026-07-02-*`, `2026-07-10-*`
- `docs/archive/**`
- `docs/06_mvp_to_rag_execution_board.md`, which already says `[cite:N]`
- `B@7b2ff1f` `docs/research/2026-09-08/*` and `docs/plans/2026-09-10-implementation-roadmap.md:29`

**Capstone package.** After W-5 and W-10 land, the maintainer updates C-SAFE-5 "Enforced at: none" → `tests/test_rag_citation_prompt.py` (HC-CIT-001..003, backend CI job). SAFE-08 stays **partial** until C-1 and the P4 rows land. W-5's PR reports this status change (handoff §6 item 3) and does not edit those files.

## 7. Dependencies

- **Phases:**
  - P0-B, so the capstone package is committed and the links above resolve.
  - P0-B2 (owner gate), so this plan file is committed on main: commit 2 edits its §15. Task 0 Step 1 checks it.
  - D9, the 3.11 venv.
  - P1, the post-merge tree. `rag.py` itself is not changed by A or B.
- **Decisions:** D11 is decided. There is no dependency on P2–P8.
- **Ordering:**
  - Recommended before W-4 (behavioural rationale in §5; no shared file).
  - Before W-3 (shared `rag.py`; canonical order W-5 → W-3 → W-8).
  - Before P4's D11 doc task, which consumes §6.
  - Before or with W-10, which carries C-1.

---

### Task 0: Preconditions and phase-start measurement

**Files:** none modified except §15 of this plan.

- [ ] **Step 1: Create the worktree and prove it is post-P1.**
  ```bash
  WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w05
  cd /mnt/c/Users/DangT/Documents/GitHub/HealthCentral
  git fetch origin
  git worktree add "$WT" -b fix/w05-citation-marker-prompt origin/main
  cd "$WT"
  git merge-base --is-ancestor 7b2ff1f HEAD && git merge-base --is-ancestor 692fdf3 HEAD && echo "P1 landed"
  git rev-parse --short HEAD   # record as <START>
  git status --short           # must print nothing
  git ls-files docs/plans/2026-09-27-W05-*.md   # P0-B2: expect this plan's path
  ```
  Expected: `P1 landed`, `git status --short` prints nothing, and `ls-files` prints `docs/plans/2026-09-27-W05-citation-marker-prompt.md`. If `P1 landed` is not printed, **STOP**: this plan targets the post-P1 tree. If `ls-files` prints nothing, **STOP**: P0-B2 has not landed, so §15 and commit 2 have no tracked file. Remove the unused worktree with `git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral worktree remove "$WT"`.

- [ ] **Step 2: Confirm the interpreter.**
  ```bash
  ~/venvs/asclexis-311/bin/python --version
  ```
  Expected: `Python 3.11.x`. If missing, **STOP** (D9).

- [ ] **Step 3: Re-verify the target lines.**
  ```bash
  WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w05; cd "$WT"
  grep -n "SYSTEM_PROMPT = \|using \[cite:N\] format\|must cite \[YOUR_RESULTS:N\]\|cite these in REPORT FACTS\|cite these in GENERAL INFO\|citation_pattern = r" src/backend/modules/rag.py
  grep -n "CITATION_PATTERN = " src/backend/modules/claim_extractor.py
  ```
  Expected, matching `main@40f590e`:
  - `123` (SYSTEM_PROMPT), `126` (`[cite:N]`), `128`, `133`, `134`, `819` in `rag.py`;
  - `92` in `claim_extractor.py`.

  If the text differs, **STOP** and re-derive. Line numbers may shift; that is fine, update this plan's references in §15.

- [ ] **Step 4: Re-run the consumer grep (stop gate).**
  ```bash
  WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w05; cd "$WT"
  git grep -n "YOUR_RESULTS\|\[REFERENCE:\|REFERENCE:{" -- src ':!src/backend/tests'
  git grep -n "cite:" -- src/frontend/src ':!src/frontend/src/__tests__'
  ```
  Expected:
  - The first grep hits only `rag.py` (`:128`, `:133`, `:134`, `:636`).
  - The second hits only `services/assistant.ts` and `pages/ExplainAssistant.tsx` comments/regex.

  If any product code parses `[YOUR_RESULTS:` or `[REFERENCE:` out of **model output**, **STOP**: removing the instruction would break a consumer.

- [ ] **Step 5: Test-ID collision check.**
  ```bash
  WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w05; cd "$WT"
  git grep -n "HC-CIT-0\|hc_cit_0" -- src/backend/tests; echo "grep-exit=$?"
  ```
  Expected: no hits and `grep-exit=1`.
  - The similar prefix `HC-CITE-0NN` / `test_hc_cite_*` exists in `tests/test_citation_source_links.py`, so `pytest -k hc_cit` would also select those.
  - Always select HC-CIT tests by file or full node ID.

- [ ] **Step 6: Phase-start measurement.** WSL/9p: clear stale bytecode first (AGENT.md).
  ```bash
  set -o pipefail
  WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w05; cd "$WT/src/backend"
  find . -name __pycache__ -type d -prune -exec rm -rf {} +
  ~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q --collect-only 2>&1 | tail -1; echo "collect-exit=${PIPESTATUS[0]}"
  ~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q -rf 2>&1 | tail -25; echo "pytest-exit=${PIPESTATUS[0]}"
  grep -n "backend tests collected\|all [0-9]* pass\|differs from" "$WT/CLAUDE.md"
  grep -n "collected; " "$WT/AGENT.md"
  ```
  Record in §15: interpreter, `<START>`, collected count (`collect-exit=0` required), `pytest-exit`, every failing node ID (`-rf` lists them), and the baseline figures and line numbers printed from `CLAUDE.md`/`AGENT.md`.
  - At `B@7b2ff1f`, `CLAUDE.md:30` says 1288 while `AGENT.md:76` says 1269. P1 settles the merged count; W-5 starts from whatever P1 left and only adds 3.
  - `test_api_rag_index_002b` may fail without an embedding model. That is environmental; never lower its 0.7 threshold.

- [ ] **Step 7: Targeted RAG baseline.**
  ```bash
  set -o pipefail
  WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w05; cd "$WT/src/backend"
  ~/venvs/asclexis-311/bin/python -m pytest -p no:cacheprovider -q -rf \
    tests/test_rag_pipeline.py tests/test_biomarker_assistant.py tests/test_chat_sessions.py \
    tests/test_memory_integration.py tests/test_phase4_ai_safety.py \
    tests/test_interpret_safety_adversarial.py tests/test_citation_source_links.py \
    tests/test_rag_category_filter.py tests/test_rag_trend_units.py tests/agent/test_s3_guardrails.py 2>&1 | tail -6; echo "pytest-exit=${PIPESTATUS[0]}"
  ```
  ```bash
  WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w05; cd "$WT"
  ~/venvs/asclexis-311/bin/python scripts/agent_eval_gate.py; echo "exit=$?"
  ```
  Record the pass/fail line, `pytest-exit`, any failing node IDs, and the START eval-gate exit in §15.
  - Author context (not a target): on Windows Python 3.13.7, `main@40f590e`, the first 9 files gave `167 passed` with the Task 1 prompt edit applied in memory.

---

### Task 1: HC-CIT-001..003 red → prompt fix → green

**Files:**
- Create: `src/backend/tests/test_rag_citation_prompt.py`
- Modify: `src/backend/modules/rag.py:128,133,134`

**Interfaces:**
- Consumes:
  - `modules.rag.RAGModule.SYSTEM_PROMPT: str`
  - `RAGModule.query(question, profile_id, *, history, use_memory, …) -> ValidatedResponse`, which calls `self._generate_with_runner(prompt, runner)` with the prompt as the first positional arg (`rag.py:1268`)
  - `RAGModule.validate_response(response: str, retrieved_chunks: list[RetrievedChunk]) -> ValidatedResponse`
  - `RetrievedChunk` (dataclass, `rag.py:49-64`)
  - `modules.claim_extractor.ClaimExtractor.CITATION_PATTERN: str`
- Produces: test-local helpers `_citation_format_instructions(text) -> list[tuple[str, list[str]]]` and `_cite_lines_naming_a_label(text, labels) -> list[str]`. No product API changes.

**Operational definition** (this is what makes HC-CIT-001 able to fail):
- A *citation-format instruction* is one line of prompt text containing both:
  - (a) a cite-word: `cite|cites|cited|citing|citation|citations`, case-insensitive, whole word;
  - (b) a bracketed marker template `[NAME:N]` or `[NAME:<digits>]`.
- "Exactly one" means exactly one such line, and its only marker is `cite`.
- Additionally, no line containing a cite-word may name a context label (`YOUR_RESULTS`, `REFERENCE`, `USER_DOCUMENT`, `USER_OBSERVATION`), bracketed or not.
- Measured on the current prompt, 4 lines qualify: `:126` names `cite`, `:128` and `:133` name `YOUR_RESULTS`, `:134` names `REFERENCE`.

- [ ] **Step 1: Write the failing tests.** Create `src/backend/tests/test_rag_citation_prompt.py`:

```python
"""Legacy RAG prompt carries one citation-format instruction (owner decision D11).

Test IDs: HC-CIT-001..003. Contract C-SAFE-5; matrix SAFE-08.

Operational definition (the thing these tests count):
  A *citation-format instruction* is one line of prompt text that contains BOTH
  (a) a cite-word: cite / cites / cited / citing / citation / citations, and
  (b) a bracketed marker template: ``[NAME:N]`` or ``[NAME:<digits>]``.
  "exactly one" means exactly one such line, and it names ``[cite:N]`` --
  the only marker ``RAGModule.validate_response`` parses (modules/rag.py,
  ``citation_pattern = r"\\[cite:(\\d+)\\]"``).
Context labels (``[YOUR_RESULTS:N]``, ``[REFERENCE:N]``, ``[USER_DOCUMENT:N]``)
may be *described* in the prompt, but never on a line that tells the model to cite.
"""
from __future__ import annotations

import re
from unittest.mock import AsyncMock, patch

import pytest

_CITE_WORD = re.compile(r"\bcit(?:e|es|ed|ing|ation|ations)\b", re.IGNORECASE)
_MARKER = re.compile(r"\[([A-Za-z_]+):(?:N|\d+)\]")
# Context-label names rendered by RAGModule.compose_prompt:
# "YOUR_RESULTS" for observation summaries, else source_type.upper()
# for source_type in {"user_document", "user_observation", "reference"}.
_CONTEXT_LABELS = {"YOUR_RESULTS", "USER_DOCUMENT", "USER_OBSERVATION", "REFERENCE"}


def _citation_format_instructions(text: str) -> list[tuple[str, list[str]]]:
    """Return (line, marker-names) for every citation-format instruction line."""
    return [
        (line.strip(), _MARKER.findall(line))
        for line in text.splitlines()
        if _CITE_WORD.search(line) and _MARKER.search(line)
    ]


def _cite_lines_naming_a_label(text: str, labels: set[str]) -> list[str]:
    """Lines that tell the model to cite AND name a context label, bracketed or not."""
    label_re = re.compile(r"\b(" + "|".join(sorted(labels)) + r")\b")
    return [ln.strip() for ln in text.splitlines() if _CITE_WORD.search(ln) and label_re.search(ln)]


def _instruction_header() -> str:
    from modules.rag import RAGModule

    return RAGModule.SYSTEM_PROMPT.split("CONTEXT:", 1)[0]


def test_hc_cit_001_system_prompt_has_exactly_one_citation_format_instruction():
    header = _instruction_header()
    found = _citation_format_instructions(header)
    assert [markers for _, markers in found] == [["cite"]], (
        "SYSTEM_PROMPT must carry exactly one citation-format instruction, naming "
        f"[cite:N]; found {len(found)}: {found}"
    )
    offenders = _cite_lines_naming_a_label(header, _CONTEXT_LABELS)
    assert offenders == [], f"a cite instruction names a context label: {offenders}"


@pytest.mark.asyncio
async def test_hc_cit_002_prompt_sent_to_model_has_exactly_one_citation_format_instruction():
    """The prompt RAGModule.query() actually hands the runner -- after context,
    session history and memory are spliced in -- still has one instruction."""
    from modules.rag import RAGModule, RetrievedChunk

    rag = RAGModule()
    chunks = [
        RetrievedChunk(
            chunk_id="obs_1", source_type="user_observation", doc_id=None,
            doc_title="Your LDL Result", page=None,
            text="YOUR RESULTS - LDL\nLatest value : 145 mg/dL",
            relevance_score=0.95, is_observation_summary=True,
        ),
        RetrievedChunk(
            chunk_id="ref_1", source_type="reference", doc_id=None,
            doc_title="Medical Reference: LDL", page=None,
            text="LDL is a lipoprotein that carries cholesterol.",
            relevance_score=0.8, is_peer_reviewed=True,
        ),
        RetrievedChunk(
            chunk_id="doc_1", source_type="user_document", doc_id="d1",
            doc_title="Lab Report", page=2,
            text="LDL 145 mg/dL (ref < 100)",
            relevance_score=0.7, is_user_verified=True,
        ),
    ]
    memory = (
        "\nUSER PREFERENCES (from memory store — do NOT cite, "
        "use only for personalisation):\n- prefers metric units\n"
    )
    history = [
        {"role": "user", "content": "What was my LDL last time?"},
        {"role": "assistant", "content": "Your LDL was 150 mg/dL."},
    ]
    generate = AsyncMock(return_value="REPORT FACTS:\nYour LDL is 145 mg/dL [cite:1].")

    with (
        patch.object(rag, "retrieve_context", new_callable=AsyncMock, return_value=chunks),
        patch.object(rag, "_retrieve_memory_context", new_callable=AsyncMock, return_value=memory),
        patch.object(rag, "_generate_with_runner", generate),
    ):
        await rag.query(
            question="Is my LDL high?", profile_id="prof-1",
            history=history, use_memory=True,
        )

    prompt = generate.call_args.args[0]
    rendered_labels = set(re.findall(r"^\[([A-Z_]+):\d+\]", prompt, re.MULTILINE))
    assert rendered_labels == {"YOUR_RESULTS", "REFERENCE", "USER_DOCUMENT"}, rendered_labels
    assert "USER PREFERENCES" in prompt and "SESSION HISTORY" in prompt

    found = _citation_format_instructions(prompt)
    assert [markers for _, markers in found] == [["cite"]], (
        f"prompt sent to the model carries {len(found)} citation-format instructions: {found}"
    )
    offenders = _cite_lines_naming_a_label(prompt, rendered_labels)
    assert offenders == [], f"a cite instruction names a context label: {offenders}"


def test_hc_cit_003_every_instructed_marker_is_one_the_validator_counts():
    """Each marker the prompt tells the model to write is parsed by
    validate_response and ClaimExtractor; a bare context label is not."""
    from modules.claim_extractor import ClaimExtractor
    from modules.rag import RAGModule, RetrievedChunk

    rag = RAGModule(enable_verification=False)
    chunk = RetrievedChunk(
        chunk_id="obs_1", source_type="user_observation", doc_id=None,
        doc_title="Your LDL Result", page=None,
        text="YOUR RESULTS - LDL\nLatest value : 145 mg/dL",
        relevance_score=0.95, is_observation_summary=True,
    )
    instructed = sorted(
        {m for _, ms in _citation_format_instructions(_instruction_header()) for m in ms}
    )
    assert instructed, "no citation-format instruction found in SYSTEM_PROMPT"

    not_counted = []
    for name in instructed:
        marker = f"[{name}:1]"
        validated = rag.validate_response(
            f"REPORT FACTS:\nYour LDL is 145 mg/dL {marker}.\n", [chunk]
        )
        report = [s for s in validated.segments if s.segment_type == "report_facts"]
        counted = bool(report and report[0].citations) and not any(
            "missing citations" in e for e in validated.validation_errors
        )
        if not counted or not re.search(ClaimExtractor.CITATION_PATTERN, marker):
            not_counted.append(marker)
    assert not_counted == [], (
        f"prompt instructs markers the validator/claim extractor do not parse: {not_counted}"
    )

    # Pin: a bare context label is not a citation (D11: labels, not markers).
    label_only = rag.validate_response(
        "REPORT FACTS:\nYour LDL is 145 mg/dL [YOUR_RESULTS:1].\n", [chunk]
    )
    assert "Report facts section missing citations" in label_only.validation_errors
```

- [ ] **Step 2: Run the tests and confirm they fail (RED).**
  ```bash
  set -o pipefail
  WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w05; cd "$WT/src/backend"
  ~/venvs/asclexis-311/bin/python -m pytest tests/test_rag_citation_prompt.py -p no:cacheprovider -q 2>&1 | grep -E "^E  +AssertionError|passed|failed"; echo "pytest-exit=${PIPESTATUS[0]}"
  ```
  Expected: `3 failed` and `pytest-exit=1`, with these messages. The author measured them on Windows Python 3.13.7 against `main@40f590e` on 2026-09-27, running an identical scratch copy.
  - `AssertionError: SYSTEM_PROMPT must carry exactly one citation-format instruction, naming [cite:N]; found 4: [('1. You must cite sources for ALL factual claims using [cite:N] format', ['cite']), ("- REPORT FACTS: … (must cite [YOUR_RESULTS:N] or user documents)", ['YOUR_RESULTS']), ("5. Context labeled [YOUR_RESULTS:N] … cite these in REPORT FACTS", ['YOUR_RESULTS']), ('6. Context labeled [REFERENCE:N] … cite these in GENERAL INFO', ['REFERENCE'])]`
  - `AssertionError: prompt sent to the model carries 4 citation-format instructions: […same 4 lines…]`
  - `AssertionError: prompt instructs markers the validator/claim extractor do not parse: ['[REFERENCE:1]', '[YOUR_RESULTS:1]']`

  Any other failure (import error, fixture error) is **not** a valid RED. Fix the test, not the product.

- [ ] **Step 3: Minimal implementation.** In `src/backend/modules/rag.py`, change only these three lines inside `SYSTEM_PROMPT`. Keep the em-dash (U+2014) and indentation.

  `:128` before / after:
  ```text
     - REPORT FACTS: What the patient's report shows (must cite [YOUR_RESULTS:N] or user documents)
     - REPORT FACTS: What the patient's report shows (from [YOUR_RESULTS:N] context or user documents)
  ```
  `:133` before / after:
  ```text
  5. Context labeled [YOUR_RESULTS:N] contains the patient's own measured values — cite these in REPORT FACTS
  5. Context labeled [YOUR_RESULTS:N] contains the patient's own measured values — use these in REPORT FACTS
  ```
  `:134` before / after:
  ```text
  6. Context labeled [REFERENCE:N] contains general medical knowledge — cite these in GENERAL INFO
  6. Context labeled [REFERENCE:N] contains general medical knowledge — use these in GENERAL INFO
  ```
  - Rule 1 (`:126`, `[cite:N]`) and rule 7 (`:135`) stay unchanged.
  - Nothing is added. The optional N-mapping clause is owner-gated (§12).

- [ ] **Step 4: Run the tests and confirm they pass (GREEN).**
  ```bash
  set -o pipefail
  WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w05; cd "$WT/src/backend"
  ~/venvs/asclexis-311/bin/python -m pytest tests/test_rag_citation_prompt.py -p no:cacheprovider -q 2>&1 | tail -1; echo "pytest-exit=${PIPESTATUS[0]}"
  ```
  Expected: `3 passed` and `pytest-exit=0`. Author context: the same edit, applied in memory on Windows 3.13.7, gave `3 passed`.

- [ ] **Step 5: Break it on purpose, 1 of 3 (all three tests).** Put the word `cite` back into `:133` only (`— use these in REPORT FACTS` → `— cite these in REPORT FACTS`). Run Step 4's command.
  - Expected: `3 failed`, `pytest-exit=1`. HC-CIT-001/002 report 2 instructions; HC-CIT-003 reports `['[YOUR_RESULTS:1]']`.
  - Restore `:133` and re-run: `3 passed`.

- [ ] **Step 6: Break it on purpose, 2 of 3 (HC-CIT-002 only).** This shows what HC-CIT-001 cannot see: an instruction added during composition.
  - The history header is a string literal inside `compose_prompt` (`rag.py:672`). No attribute exposes it, so a monkeypatch cannot reach it and this step keeps a **temporary, never-staged** edit (review R1 disposition).
  - Temporarily change the literal at `rag.py:672` from `"\n\nSESSION HISTORY (do NOT cite these turns \u2014 for context only):\n"` (the source spells the dash as the escape `\u2014`) to `"\n\nSESSION HISTORY (cite earlier answers as [HISTORY:N]):\n"`. Run Step 4's command.
  - Expected: `1 failed, 2 passed`, `pytest-exit=1`, with `test_hc_cit_002…` failing on "carries 2 citation-format instructions".
  - Restore `:672` exactly, then run the guard:
    ```bash
    set -o pipefail
    WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w05; cd "$WT"
    git diff -U0 -- src/backend/modules/rag.py | grep "^@@"
    grep -c 'SESSION HISTORY (do NOT cite these turns \\u2014 for context only)' src/backend/modules/rag.py
    ```
    Expected: only hunks at `:128`, `:133` and `:134`, then `1`. Anything else → restore before continuing.

- [ ] **Step 7: Break it on purpose, 3 of 3 (HC-CIT-003 only).** This shows the prompt→parser drift that HC-CIT-001 cannot see. It uses a test-local monkeypatch of `ClaimExtractor.CITATION_PATTERN`; **no file is edited** (review R1 disposition).
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w05; cd "$WT/src/backend"
~/venvs/asclexis-311/bin/python - <<'EOF'
import asyncio, sys
from unittest.mock import patch
from modules.claim_extractor import ClaimExtractor
import tests.test_rag_citation_prompt as t
with patch.object(ClaimExtractor, "CITATION_PATTERN", r"\[ref:(\d+)\]"):
    t.test_hc_cit_001_system_prompt_has_exactly_one_citation_format_instruction()
    asyncio.run(t.test_hc_cit_002_prompt_sent_to_model_has_exactly_one_citation_format_instruction())
    print("HC-CIT-001/002 still pass")
    try:
        t.test_hc_cit_003_every_instructed_marker_is_one_the_validator_counts()
    except AssertionError as e:
        print("HC-CIT-003 RED as expected:", e)
        sys.exit(0)
print("HC-CIT-003 did NOT go red")
sys.exit(1)
EOF
echo "breakit-exit=$?"
git -C "$WT" diff --quiet -- src/backend/modules/claim_extractor.py && echo "claim_extractor untouched"
```
  Expected:
  - `HC-CIT-001/002 still pass`
  - `HC-CIT-003 RED as expected: prompt instructs markers the validator/claim extractor do not parse: ['[cite:1]']`
  - `breakit-exit=0`
  - `claim_extractor untouched`

  The author measured this on Windows Python 3.13.7 against `main@40f590e`, with the Step 3 edit applied in memory; that run exited 0. The validator (`rag.py:819`) is **not** used for break-it, not even temporarily.

- [ ] **Step 8: Existing validator and prompt tests are unchanged and green.** Re-run Task 0 Step 7's command.
  - Expected: the same result as recorded at start, plus nothing new failing.
  - Then, from `"$WT"`: `git diff --name-only <START> -- src/backend/tests` → only `src/backend/tests/test_rag_citation_prompt.py` (untracked until staged; check `git status --short src/backend/tests`).

- [ ] **Step 9: Update the baseline counts in the same commit.** This commit changes collection by +3, and `CLAUDE.md` §4 requires the count to move in the same commit.
  ```bash
  set -o pipefail
  WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w05; cd "$WT/src/backend"
  ~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q --collect-only 2>&1 | tail -1; echo "collect-exit=${PIPESTATUS[0]}"
  ```
  Expected: `<START collected + 3> tests collected` and `collect-exit=0`. Call START collected `S` and this figure `E`; E must equal S + 3, otherwise **STOP**.
  - Edit `$WT/CLAUDE.md` collected-count slots only (Task 0 Step 6 printed them; `:30` "**S backend tests collected.**" and `:35` "differs from S" at main and B). Each becomes `E`.
  - Leave the pass-count sentence (`:31`, "all S pass") as it is. It changes only with a pass count measured in a named environment (interpreter, plus embedding model present or absent), and this plan measures none. Flag it in the PR as unverified.
  - Edit `$WT/AGENT.md` on the pytest command comment (`:57` main, `:76` B): change only the "`S'` collected" figure, to `E`. Leave the pass figures in that comment as they are, and flag them in the PR as unverified.
  - If `CLAUDE.md` and `AGENT.md` disagree at START, as they do at `B@7b2ff1f` (1288 vs 1269): set both collected figures to the measured `E`, and state both old values in the commit body.
  - Change nothing else in either file. In particular, `CLAUDE.md:62` stays (C-1).
  ```bash
  WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w05; cd "$WT"
  git diff -U0 -- CLAUDE.md AGENT.md
  ```
  Expected: only the collected-count slots changed; no pass figure moved.

- [ ] **Step 10: Commit.**
  ```bash
  WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w05; cd "$WT"
  git add src/backend/modules/rag.py src/backend/tests/test_rag_citation_prompt.py CLAUDE.md AGENT.md
  git diff --cached --name-only
  ```
  Expected: exactly those 4 paths.
  ```bash
  WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w05; cd "$WT"
  git commit -m "fix(rag): legacy prompt carries one citation-format instruction, [cite:N] (D11)" \
    -m "Removes the instruction to cite [YOUR_RESULTS:N]/[REFERENCE:N] (rag.py:128,133,134); they stay context labels. validate_response and claim_extractor unchanged. Tests HC-CIT-001..003. Contract C-SAFE-5, matrix SAFE-08. Owner decision D11 (docs/capstone-report/owner-decisions-2026-09-27.md)." \
    -m "Baseline: collected S -> E measured with <interpreter> (CLAUDE.md, AGENT.md collected-count slots only). Pass-count sentences left unchanged: not measured in a named environment."
  ```
  Replace `S`, `E` and `<interpreter>` with the measured values.
  Follow the session's attribution rule for trailers.

**What each test would fail to notice:**

| Test | Blind spot |
|---|---|
| HC-CIT-001 | Anything added outside the constant, such as composition (covered by -002). A second instruction worded with no bracket template and no label name, such as "cite using the label above". Whether the model obeys. |
| HC-CIT-002 | Real memory rendering: `_retrieve_memory_context` is patched with the header string copied from `rag.py:1089-1091`. Retrieval-side changes (patched). Model behaviour. |
| HC-CIT-003 | The frontend regex (`services/assistant.ts:378,394`). Whether faithfulness *scores* change. Only markers named in a qualifying instruction line are checked. |

---

### Task 2: Docs describe `[cite:N]` as the validated marker and the others as context labels

**Files** (re-verify line numbers first):
- `docs/features/01_lab_result_interpreter_architecture.md:195-216`
- `docs/compliance/ai-safety.md:20`
- `docs/user/faq.md:108-110`
- `docs/user/workflows.md:113-116`

**Interfaces:** consumes Task 1's merged prompt text. Produces no code.

Rule for every edit: **no new markdown links**, and paths go in code spans.

- [ ] **Step 1: Write the failing doc check (RED).**
  ```bash
  WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w05; cd "$WT"
  grep -nE "cites? \`?\[(YOUR_RESULTS|REFERENCE):N\]|\*\*\[(YOUR_RESULTS|REFERENCE):N\]\*\*|citation layers|\`\[(REFERENCE|YOUR_RESULTS):N\]\` for" \
    docs/features/01_lab_result_interpreter_architecture.md docs/compliance/ai-safety.md docs/user/faq.md docs/user/workflows.md; echo "grep-exit=$?"
  ```
  Expected now: 8 hits and `grep-exit=0` (measured on `main@40f590e`, 2026-09-27):
  - `01_lab…:197,213,214`
  - `ai-safety.md:20`
  - `faq.md:109,110`
  - `workflows.md:115,116`

  After Step 5: no hits and `grep-exit=1`. The author checked the four replacement blocks in Steps 2–5 against this pattern: 0 hits.

- [ ] **Step 2: Edit `docs/features/01_lab_result_interpreter_architecture.md` §"Biomarker Grounding"** (`:195-216`). Keep the eight data bullets under the two bold headings (`:200-203`, `:206-210`) and the last two Response Structure bullets (`:215-216`) unchanged. Replace the rest so the section reads:

  ```markdown
  ### Biomarker Grounding

  The assistant RAG pipeline grounds biomarker-related responses in **two kinds of retrieved context**. Each context block reaches the model under a numbered context label:

  **Patient's Own Results — context label `[YOUR_RESULTS:N]`:**
  - Latest measured value for the biomarker
  - Normal reference range (sex-specific if applicable)
  - Trend direction over time (improving/stable/worsening)
  - Extracted from patient's observation history

  **General Reference Knowledge — context label `[REFERENCE:N]`:**
  - Auto-seeded at startup via `seed_knowledge_base.py` if empty
  - Clinical significance of the biomarker
  - Common causes of abnormality
  - General management principles
  - Sourced from `biomarker_knowledge` table

  Chunks from the patient's imported documents are labelled `[USER_DOCUMENT:N]`. Context labels tell the model where a block came from; they are not citation markers.

  **Citations:** the model cites every factual claim with `[cite:N]`. `validate_response` in `src/backend/modules/rag.py` maps `[cite:N]` to the N-th retrieved context block. `[cite:N]` is the only marker that `validate_response` and the claim extractor (`src/backend/modules/claim_extractor.py`) parse, so a context label copied into an answer does not count as a citation. The chat UI renders `[cite:N]` as `[N]` and lists the cited sources under the answer. This vocabulary follows owner decision D11 (2026-09-27, `docs/capstone-report/owner-decisions-2026-09-27.md`).

  **Response Structure:**
  - "Report Facts" section draws on the patient's own results and documents (`[YOUR_RESULTS:N]` / `[USER_DOCUMENT:N]` context), cited with `[cite:N]`
  - "General Info" section draws on reference knowledge (`[REFERENCE:N]` context), cited with `[cite:N]`
  - This separation maintains the education-only framing and ensures no medical advice is provided
  - All outputs include disclaimers directing user to healthcare provider
  ```

- [ ] **Step 3: Edit `docs/compliance/ai-safety.md:20`.** Replace that one bullet with:

  ```markdown
  - Answers must be grounded in retrieved context and cited. On the legacy RAG path the model cites with `[cite:N]`, where `N` is the number of the retrieved context block; it is the only marker `RAGModule.validate_response` parses. `[YOUR_RESULTS:N]` (the user's own observations), `[REFERENCE:N]` (seeded reference knowledge) and `[USER_DOCUMENT:N]` (imported documents) are context labels, not citation markers (owner decision D11, 2026-09-27). The agent path returns structured citation objects (`modules/agent/schemas.py` `Citation`) instead of inline markers. Session memory is labeled non-citable.
  ```

- [ ] **Step 4: Edit `docs/user/faq.md:108-110`.** Keep the heading at `:106` (the chips literally read "Your Results" / "Reference") and the sentence at `:112`. Replace `:108-110` with:

  ```markdown
  The assistant lists the sources behind an answer under **Sources**, below the answer. Where it marks a specific sentence, it uses a number in square brackets, such as [1]. Each source shows its title (for example "Your LDL Result" or "Medical Reference: LDL") or, when it has no title, one of these labels:
  - **Your Results** — your own lab values from imported documents, including your latest result, normal range, and whether the value is trending up or down
  - **Your Document** — a passage from a document you imported
  - **Reference** — general medical knowledge from a trusted reference library
  ```
  Evidence: `ExplainAssistant.tsx:358-365` (fallback labels), `:551` ("Sources:"), `rag.py:442` (`f"Your {display_name} Result"`), `:503` (`f"Medical Reference: {…}"`). The text deliberately does not claim that the number in the sentence matches the number on the chip (finding F-3).

- [ ] **Step 5: Edit `docs/user/workflows.md:113-116`.** Keep the heading at `:111` and the sentence at `:118`. Replace `:113-116` with:

  ```markdown
  When the assistant answers your question, it lists its sources under **Sources**, below the answer, and may mark a sentence with a number such as [1]:

  - **Your Results** (or the result's name) — your own measured lab values from imported documents (latest result, normal range, and trend direction, used under "Report Facts")
  - **Your Document** (or the document's name) — a passage from a document you imported
  - **Reference** (or the reference's name) — general medical knowledge from the reference library, used under "General Info"
  ```

- [ ] **Step 6: Re-run the Step 1 grep (GREEN) and the docs gates.**
  ```bash
  WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w05; cd "$WT"
  grep -nE "cites? \`?\[(YOUR_RESULTS|REFERENCE):N\]|\*\*\[(YOUR_RESULTS|REFERENCE):N\]\*\*|citation layers|\`\[(REFERENCE|YOUR_RESULTS):N\]\` for" \
    docs/features/01_lab_result_interpreter_architecture.md docs/compliance/ai-safety.md docs/user/faq.md docs/user/workflows.md; echo "grep-exit=$?"
  python3 scripts/docs_lint.py; echo "lint-exit=$?"
  python3 scripts/generate_docs_index.py --check; echo "exit=$?"
  ```
  Expected:
  - The grep prints no hits and `grep-exit=1`.
  - The lint prints `Docs lint passed.` and `lint-exit=0`.
  - The index check prints `docs/INDEX.md and docs/_link_graph.json are fresh.` and `exit=0`. No links were added and no title or summary paragraph changed.

  If `--check` reports stale, an edit added a link or changed a first paragraph. Undo that, and do not regenerate the shared index from this plan.

- [ ] **Step 7: Break it on purpose (doc check).** Temporarily restore the old `ai-safety.md:20` text and re-run the Step 1 grep.
  - Expected: 1 hit at `ai-safety.md:20` and `grep-exit=0`.
  - Restore the new text. The grep again prints no hits and `grep-exit=1`.

- [ ] **Step 8: Commit.**
  ```bash
  WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w05; cd "$WT"
  git add docs/features/01_lab_result_interpreter_architecture.md docs/compliance/ai-safety.md docs/user/faq.md docs/user/workflows.md docs/plans/2026-09-27-W05-citation-marker-prompt.md
  git diff --cached --name-only
  ```
  Expected: exactly those 5 paths.
  ```bash
  WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w05; cd "$WT"
  git commit -m "docs: [cite:N] is the validated citation marker; [YOUR_RESULTS:N]/[REFERENCE:N] are context labels (D11)"
  ```

---

### Task 3: Phase-end measurement, acceptance, PR, STOP

- [ ] **Step 1: Full suite on the end tree.**
  ```bash
  set -o pipefail
  WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w05; cd "$WT/src/backend"
  find . -name __pycache__ -type d -prune -exec rm -rf {} +
  ~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q --collect-only 2>&1 | tail -1; echo "collect-exit=${PIPESTATUS[0]}"
  ~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q -rf 2>&1 | tail -25; echo "pytest-exit=${PIPESTATUS[0]}"
  ```
  Expected:
  - Collected = START + 3 (= `E` from Task 1 Step 9, and equal to the figure now in `CLAUDE.md`/`AGENT.md`), with `collect-exit=0`.
  - Failures ⊆ START failures, compared by node ID from `-rf`. `pytest-exit` is 0 only if START had no failures.

  A new failure that this change does not explain → **STOP**.

- [ ] **Step 2: Scope checks.**
  ```bash
  set -o pipefail
  WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w05; cd "$WT"
  git diff --name-only <START>..HEAD
  git diff --name-only <START>..HEAD -- src/backend/modules/interpret_safety.py src/backend/modules/redaction.py src/backend/modules/faithfulness.py src/backend/modules/verifier_agent.py src/backend/modules/claim_extractor.py src/backend/core/auth.py src/frontend docs/capstone-report
  git diff -U0 <START>..HEAD -- src/backend/modules/rag.py | grep -c "^@@"
  grep -c 'citation_pattern = r"\\\[cite:(\\d+)\\\]"' src/backend/modules/rag.py
  grep -n "cite these in\|must cite \[YOUR_RESULTS" src/backend/modules/rag.py
  git diff --stat <START>..HEAD -- src/backend/tests
  git diff -U0 <START>..HEAD -- CLAUDE.md AGENT.md | grep "^[-+][^-+]"
  ```
  Expected:
  1. Exactly the 9 owned files (§5).
  2. Empty.
  3. `3`, or `1` or `2` if the hunks merge.
  4. `1`.
  5. Empty.
  6. Only `tests/test_rag_citation_prompt.py`.
  7. Only the collected-count slots, with old → new figures matching Task 1 Step 9. No pass-count figure changed, and `CLAUDE.md:62` is not among them.

- [ ] **Step 3: Other gates.**
  ```bash
  WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w05
  cd "$WT/src/backend" && ~/venvs/asclexis-311/bin/python -c "from main import app" && echo boots
  cd "$WT" && ~/venvs/asclexis-311/bin/python scripts/agent_eval_gate.py; echo "exit=$?"
  cd "$WT" && python3 scripts/docs_lint.py && python3 scripts/generate_docs_index.py --check; echo "docs-exit=$?"
  ```
  Expected:
  - `boots`.
  - Eval gate `exit=0`, equal to the START run in Task 0 Step 7.
  - `docs-exit=0`.
  - Docs lint passes and the index is fresh.
  - Frontend (Windows, no frontend change): `npx tsc --noEmit` and `npx vitest run`, each compared to a START run. If they cannot run, write `UNMEASURED` and why.

- [ ] **Step 4: Record §15, push, and open the PR** in the handoff §6 format:
  1. Start and end measurements.
  2. HC-CIT RED output and break-it output.
  3. C-SAFE-5 / SAFE-08, and the status change the capstone maintainer should apply (§6).
  4. The 9-file list.
  5. One next action.

  Then **STOP** for the owner to merge.

## 8. Stop gates

Stop and ask the owner or orchestrator when:
1. A needed change touches `validate_response`, `citation_pattern`, `claim_extractor.py`, or an ask-first file. D11 says "no validator edit".
2. The prompt needs *new* instruction content (for example the N-mapping clause) rather than removal of the cite-instruction. It is owner-gated (§12).
3. The Task 0 Step 3 text differs from `main@40f590e`, or Step 4 finds a consumer of label-form markers in model output.
4. Any existing test changes status, or needs editing, to pass.
5. `generate_docs_index.py --check` goes stale from this plan's edits (never regenerate the shared index here).
6. Any failure at the end is not in the START failures and is not explained by this change.
7. Someone proposes editing `CLAUDE.md:62` inside this plan. Route it to W-10 (C-1).

## 9. Rollback

- `git revert <docs-commit> <fix-commit>`, newest first. Reverting the fix commit also restores the `CLAUDE.md`/`AGENT.md` collected counts, because they moved in that same commit.
- No schema, migration, data, cache or config changes are involved. Legacy answers are not cached (`B@7b2ff1f` `api/assistant.py:689-716`).
- A revert restores the contradictory prompt. HC-CIT-001..003 leave with the fix commit.

## 10. Measured acceptance

| Check | Command | Expected |
|---|---|---|
| New tests red first | Task 1 Step 2 | `3 failed`, with the 3 messages shown |
| New tests green | Task 1 Step 4 | `3 passed` |
| Break-it ×3 | Task 1 Steps 5–7 | `3 failed` / `1 failed, 2 passed` / `HC-CIT-003 RED as expected` + `breakit-exit=0` (monkeypatch, no file edit) |
| RAG tests pass | Task 0 Step 7 command at end | = START result; no new failures |
| Existing validator tests unchanged | Task 3 Step 2 (6) | only the new test file in `tests/` diff |
| Full suite | Task 3 Step 1 | collected = START + 3; failures ⊆ START |
| Docs lint passes | `python3 scripts/docs_lint.py` | `Docs lint passed.` |
| Index fresh | `python3 scripts/generate_docs_index.py --check` | exit 0 |
| Scope | Task 3 Step 2 | 9 files; ask-first/validator/frontend untouched; `CLAUDE.md`/`AGENT.md` collected-count slots only |
| **UNMEASURED:** live-model marker compliance | Manual measurement below | before/after counts recorded; no pass bar is licensed here |

Manual measurement for the UNMEASURED row:
1. With a local GGUF tier loaded, run 20 fixed questions through `RAGModule.query` on a synthetic vault, before and after.
2. Count answers containing `[cite:` versus `[YOUR_RESULTS:` or `[REFERENCE:`.

A pass bar would be an owner decision. W-4's gate uses canned generation, so a live-model check would need its own plan.

## 11. Recurring-failures recheck ([recurring-failures.md](../agentic/recurring-failures.md))

| # | Applies | Recheck in this plan |
|---|---|---|
| 1 Green suite that could not fail | yes | 3 break-it steps, each turning a named test red. The operational definition was measured RED (4 instructions) on today's prompt. |
| 2 Fix creates the next bug one layer over | yes | Re-walk the whole path: prompt → model → `validate_response` → claim extractor → `api/assistant.py` → `formatResponseText` → chips. Known consequence: F-3 chip numbering shows up more often. W-4 order rationale (§5). |
| 3 Figures asserted | yes | Every count comes from a command in §15. Author figures are labelled "context, Windows 3.13.7". |
| 4 Environment-dependent results | yes | `test_api_rag_index_002b` is in the targeted set; judge on collected count and failures ⊆ START. |
| 5 Contaminated tree | yes | Dedicated worktree; explicit pathspecs; `git diff --cached --name-only` before each commit. |
| 6 Documented commands nobody ran | yes | Run every command in this plan as written, from the stated directory, before quoting it in the PR. |
| 7 SQL three-valued logic | no | No SQL touched. |
| 8 Stale guidance as authority | **yes, the root cause** | `CLAUDE.md:62` asserts the wrong vocabulary. The handoff and SAFE-08 cite `rag.py:120-132` (actual `:123-140`, contradictions at `:128/:133/:134`). Wave 0 said "HC-CIT zero hits", but `git grep HC-CIT` has 2 hits from the existing `HC-CITE` IDs. Verify, do not inherit. |

## 12. Owner sign-offs (unsigned)

- [ ] Owner merges the W-5 PR. Signed: ______ Date: ______
- [ ] Owner confirms D11 covers rewording `CLAUDE.md:62`, to land in W-10's governance commit (C-1; canonical gate **GOV-D11**, signature line in W-10 §10). Signed: ______ Date: ______
- [ ] **(Not licensed by D11. Only if wanted.)** Owner approves adding "where N is the number in that source's context label" to prompt rule 1 (`rag.py:126`). Signed: ______ Date: ______
- [ ] Owner decides whether F-3 (chip numbering) becomes a work item. Signed: ______ Date: ______

## 13. Commit plan

| # | Prefix | Pathspecs (explicit) | Check |
|---|---|---|---|
| 1 | `fix(rag):` | `src/backend/modules/rag.py src/backend/tests/test_rag_citation_prompt.py CLAUDE.md AGENT.md` (the count lines move with the collection change) | `git diff --cached --name-only` = 4 lines |
| 2 | `docs:` | `docs/features/01_lab_result_interpreter_architecture.md docs/compliance/ai-safety.md docs/user/faq.md docs/user/workflows.md docs/plans/2026-09-27-W05-citation-marker-prompt.md` | = 5 lines |

Never `git add -A` or `git add .`. Branch `fix/w05-citation-marker-prompt`, one PR, humans merge.

## 14. Findings for the orchestrator

- **F-1 (line range).** Handoff W-5 and SAFE-08 cite `modules/rag.py:120-132`. At `main@40f590e` (= A = B), `SYSTEM_PROMPT` is at `:123-140` and the contradictory lines are `:128`, `:133` and `:134`.
- **F-2 (test-ID prefix).** Wave 0 said HC-CIT has zero hits. Re-measured on 2026-09-27, identical at main, A and B:
  - `git grep -n "HC-CIT"` → **2** hits, both from existing `HC-CITE` IDs: `tests/test_citation_source_links.py:9` and `docs/features/TASK_LIST.md:63`.
  - `git grep -n "hc_cit"` → 9 hits, the functions `test_hc_cite_001..009`.
  - My earlier "11" was the combined pattern `HC-CIT\|HC_CIT\|hc_cit` (2 + 9).
  - `HC-CIT-0`/`hc_cit_0` → 0 hits. The IDs are usable, but `-k hc_cit` is ambiguous.
- **F-3 (pre-existing UI mismatch, not licensed here).**
  - The answer text shows `[N]`, where N is the retrieved-chunk index (`services/assistant.ts:394`; `rag.py:885-887`).
  - Chips are numbered by position, `[{i + 1}]` (`ExplainAssistant.tsx:558`), over a flattened list with duplicates (`:356-371`).
  - So "[3]" in the text can sit beside a chip labelled "[1]". `Citation.citation_id` (`rag.py:904`) carries the real N but the UI ignores it.
- **F-4 (program wording).** Program D11 says "any prompt change is ask-first-adjacent". `rag.py` is not on the ask-first list; it imports `InterpretationSafetyGuard.PROHIBITED_PATTERNS` (`rag.py:176-178`), which this plan does not touch. D11's text licenses the removal.

## 15. Execution log (fill in during execution; no links)

| Item | Value |
|---|---|
| Interpreter (`--version`) | |
| `<START>` sha | |
| START collected / failing node IDs | |
| START baseline figures in `CLAUDE.md`/`AGENT.md` (line: value) | |
| `S` → `E` written in commit 1 | |
| START targeted RAG line | |
| START agent_eval_gate exit | |
| HC-CIT RED output (3 lines) | |
| Break-it 1/2/3 results | |
| END collected / failing node IDs | |
| END targeted RAG line | |
| docs_lint / index --check | |
| Frontend tsc / vitest (Windows) or UNMEASURED + reason | |
| Line-number drift vs this plan (if any) | |
