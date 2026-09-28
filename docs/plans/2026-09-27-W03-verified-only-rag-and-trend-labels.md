# W-3: Verified-only legacy RAG and labelled unverified trend points (D4)

**Last Updated:** 2026-09-27
**Owner:** repository owner
**Refresh Trigger:** re-verify every `path:line` below when P1 (branches A+B), P5 (utcnow), W-5 (legacy prompt) or W-10 (governance docs) lands, or when `modules/rag.py`, `api/observations.py`, `pages/TrendsDashboard.tsx` or `components/lab-interpreter/InterpretedTrendChart.tsx` changes on main
**Status:** PROPOSED — not executed

**Review status:** 4 Codex rounds. The round-4 MAJOR (manual-check copy per chart) was fixed after the last round and has not been re-reviewed; owner acceptance is required.

**Prerequisites:** P0-B and P1 merged to origin/main. The plan set (`docs/plans/2026-09-27-*.md`) is committed to main by an owner-approved docs commit. Plan-specific: P5, the W-10 governance commit and W-4 merged; D9 venv built. Task 0's ancestry check fails before P1 lands. That is the intended STOP, not a defect.

> **For agentic workers:** REQUIRED SUB-SKILL: use `subagent-driven-development` (recommended) or `executing-plans` to carry out this plan task by task. Steps use checkbox (`- [ ]`) syntax. Use `test-driven-development` for every task. Use `verification-before-completion` before claiming anything.

**Goal:** Trend points carry `user_verified`, and both trend charts visibly mark unverified points as "Unverified". The legacy chat path cites only verified values:
- `modules/rag.py` retrieves only verified observations;
- the no-LLM knowledge fallback reads only verified observations, **only if O-1 is signed "yes"** (Task 7, opt-in);
- `modules/rag.py` retrieves chunks only from verified documents, if O-5 is signed.

This is the same rule the agent path already applies.

**Architecture:** SQL `WHERE` clauses copy the agent tools' filters exactly: `Observation.user_verified == True` and `Document.status == "verified"`. They go in `modules/rag.py`, and in `api/assistant.py::_build_knowledge_fallback._fetch_latest_obs` only if O-1 is signed. The trends route adds one boolean field per point. A small shared frontend module draws a hollow, dashed, titled dot for unverified points and a text note with the count. There is no schema change, no migration and no new route.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy async, pytest + `pytest_asyncio`, in-memory `sqlite+aiosqlite`. React 18 + TS, Recharts `^3.9.1`, vitest `^4` + Testing Library.

## Global Constraints

- **Python 3.11 target.** Gates run with the D9 venv `~/venvs/asclexis-311/bin/python`. If that venv does not exist, STOP (D9 has not been executed).
- **Shell rules.** Every bash block starts with `set -o pipefail` and an absolute `cd`:
  - `pytest` and the boot check run in `/mnt/c/Users/DangT/Documents/GitHub/hc-w03/src/backend`;
  - `git`, `grep` and `scripts/agent_eval_gate.py` run in `/mnt/c/Users/DangT/Documents/GitHub/hc-w03`.

  Never use a relative `cd` after a `cd`. PowerShell blocks use one absolute `Set-Location` and check `$LASTEXITCODE` after each command whose result matters.
- **Evidence directory (outside the repo).** WSL `/mnt/c/Users/DangT/Documents/GitHub/w03-evidence`; the same folder from Windows is `C:\Users\DangT\Documents\GitHub\w03-evidence`. Task 0 Step 1 creates it. Shell state does not persist between blocks, so every block that uses it sets `EV=/mnt/c/Users/DangT/Documents/GitHub/w03-evidence` (bash) or `$EV = 'C:\Users\DangT\Documents\GitHub\w03-evidence'` (PowerShell) itself. The start commit is stored in `$EV/START_SHA`; blocks that need it read it with `START=$(cat "$EV/START_SHA")`.
- **Break-it-on-purpose** steps only edit files this plan owns. Undo the edit by hand, never with `git checkout --`, and confirm `git diff` shows only the intended change before committing. Read-only files are never edited, not even temporarily.
- **Frontend runs on Windows.** `vitest` stalls under WSL on `/mnt/c` (implementation-program ground rule 3; AGENT.md "Commands"). Run every `npx` command below from Windows PowerShell in the same worktree. Never report a vitest result produced under WSL.
- **Ask-first files are read-only in this plan:** `modules/faithfulness.py`, `modules/verifier_agent.py`, `modules/interpret_safety.py`, `modules/redaction.py`, and anything auth/encryption, including `core/auth.py`. `modules/rag.py` imports three of them (`main@40f590e` `modules/rag.py:40-45`). It is not itself ask-first. Edit only the two statement hunks named below.
- **Never lower a threshold:** 0.6 faithfulness (`modules/rag.py:862`), the eval-gate bars (`scripts/agent_eval_gate.py`), and the 0.7 embedding assertion.
- **Agent path untouched:** nothing under `src/backend/modules/agent/`, `src/backend/tests/agent/` or `scripts/agent_eval_gate.py` changes.
- **No-LLM fallback keeps working** (matrix SAFE-09). `api/assistant.py` is untouched unless O-1 is signed "yes". If it is, Task 7 adds one `WHERE` clause and the fallback must still return KB segments without an LLM.
- **Per-profile isolation:** every new query runs on the profile session that is passed in. Nothing touches master `get_db()` except the existing audit call.
- **Line numbers are pre-P1.** Each is labelled with its ref. `modules/rag.py`, `api/observations.py`, `api/interpretations.py` and every frontend file named here are byte-identical at `main@40f590e`, `B@7b2ff1f` and `A@692fdf3`: `git diff --stat main origin/claude/healthcentral-agentic-research-r1n54x -- src/backend/modules/rag.py src/backend/api/observations.py src/backend/api/interpretations.py src/frontend/src` and the same against `origin/claude/asclexis-repo-audit-349pjq` was empty on 2026-09-27. `api/assistant.py` differs at B. Re-verify each line on the post-P1, post-P5 tree before editing (Task 0 Step 5).
- **Test IDs:** backend `HC-VER-001…005` (functions `test_hc_ver_00N_*`), vitest `HC-VER-FE-001…003`. Branch B already has `HC-VERIFY-001…007` (`B@7b2ff1f` `src/backend/tests/test_verify_model_repos.py:1,39-89`). Anchor every grep and `-k` on `HC-VER-[0-9]` / `hc_ver_0`, never on the bare prefix.
- **Commits:** explicit pathspecs; `git diff --cached --name-only` before each commit; never `git add -A` or `git add .`; never `git reset` shared work (contract C-GATE-3).

---

## 1. Approval scope

Owner decision **D4**, [owner-decisions-2026-09-27.md](../capstone-report/owner-decisions-2026-09-27.md). Owner's choice: **Label, exclude from RAG**. Option text, verbatim:

> "Trends may show unverified points but visibly marked 'unverified'; legacy RAG cites verified values only (matches the agent path). Docs updated to say so."

**Licensed here:**
- the `user_verified` flag on trend points;
- visible "Unverified" marking on the charts that plot `/observations/trends/{analyte}`;
- restricting legacy RAG retrieval to verified observations, and to verified documents (the agent-path rule), in `modules/rag.py`;
- **not licensed by default:** restricting the legacy path's no-LLM knowledge fallback (Task 7). It runs only after O-1 is signed "yes" (§3.7(a), §10).

**Does NOT license:**
1. Hiding or filtering unverified points out of trends. D4 says trends *may show* them.
2. Any edit to the agent path, the golden set, eval thresholds or `scripts/agent_eval_gate.py`.
3. Any edit to `faithfulness.py`, `verifier_agent.py`, `interpret_safety.py`, `redaction.py`, `core/auth.py`.
4. The legacy prompt text (`main@40f590e` `modules/rag.py:123-140`). **W-5** owns it.
5. Abstention behaviour or patient-facing message wording, including the insufficient-context text at `modules/rag.py:1236-1245`. **W-4** owns abstention behaviour; new wording for that text is the program owner item MSG-UNVERIFIED; see O-4.
6. Any other change to `api/assistant.py`: the agent branch, W-4's abstention helper, the care-task and med-change fallbacks, and wording. Task 7's single `WHERE` clause becomes licensed only once O-1 is signed "yes".
7. The observation value embedded in the interpretations question (`api/interpretations.py:427-432`). Owner question O-3; this plan makes no change.
8. A new data model: no `Chunk.verified` column, no migration, and no verify button for documents with zero observations (O-5 follow-up).
9. Documentation wording. The "Docs updated to say so" clause belongs to **W-10** (`docs/compliance/data-privacy.md`) and **P4** (`docs/architecture/pipelines.md:53-56`). This plan only lists what they must say (§11).
10. CSV/JSON/doctor-summary exports. Matrix SAFE-02 lists them, but D4 does not cover them; D3/W-2 governs exports.
11. Search, timeline and highlights surfaces. They already label verification state (`modules/search.py:224-272`, `modules/timeline.py:189`, `modules/highlights.py:119`).

Anything wider than this list is owner-gated (§10).

## 2. Traceability

Each ID below was confirmed by grep on 2026-09-27.

| ID | Source | Quoted text |
|---|---|---|
| **C-VERIFY-2** | [contract](../capstone-report/architecture-engineering-contract.md) line 119 | "**C-VERIFY-2 · OWNER-GATED.** Rule: Which consumers MUST read verified rows only. … Today: the trends endpoint, legacy RAG and CSV/JSON/doctor summary do not." Verify: `grep -n "user_verified" src/backend/api/observations.py src/backend/modules/rag.py src/backend/api/export.py` |
| C-VERIFY-1 | contract line 112 | "Extraction and structured import MUST create observations with `user_verified=False`." Its grep must still return exactly 2 hits after this plan (Task 8) |
| C-SAFE-1, C-SAFE-4 | contract lines 131, 158 | ask-first files; thresholds never lowered |
| C-AUDIT-1 | contract line 323 | the trends route already audits (`api/observations.py:716-724`). The audit call is unchanged; HC-VER-002 goes through it |
| C-GATE-1, C-GATE-3 | contract lines ~347, 360 | measured counts; explicit pathspecs |
| **SAFE-02** | [matrix](../capstone-report/specs-compliance-matrix.md) line 71 | "Downstream consumers use verified data … **Not** verified-only: trends (`api/observations.py:529-535`), legacy RAG (`modules/rag.py:322-328`) … **partial** … **owner-gated**" |
| SAFE-09 | matrix line 78 | "The no-LLM fallback stays functional … **tested**" |
| GATE-05 | matrix line 139 | "Agent behavioural eval gate … `scripts/agent_eval_gate.py`, 74 cases" |
| Handoff W-3 | [handoff §5](../../audit/2026-09-25/handoff-2026-09-27-execution.md) | "Trends points carry `user_verified`, and the UI marks unverified points. Legacy RAG observation and chunk retrieval filter `user_verified == True`" · tests HC-VER-001/002 + vitest · acceptance "the agent golden set is unchanged" |
| Program | [implementation-program.md](../capstone-report/implementation-program.md) G-A2 | "A test proves an unverified observation is excluded or labelled on each surface" |

**The agent-path filters this plan copies** (`main@40f590e`; unchanged at B):
- Observations: `modules/agent/tools/query_observations.py:56`, `stmt = select(Observation).where(Observation.user_verified == True)`. The same filter is at `modules/agent/tools/compute_trend.py:56`.
- Chunks: `modules/agent/tools/retrieve_chunks.py:70-74`, `.join(Document, Chunk.doc_id == Document.id).where(Document.status == "verified")`. Its docstring (`:3-6`, `:58-61`) cites RECONCILIATION R-5 (`docs/archive/agile/RECONCILIATION.md:444-448`): "`Chunk` has no own `verified` flag. Verified status for retrieved chunks is inherited from `Document.status == "verified"`."
- Branch B restates the pairing: `B@7b2ff1f` `api/assistant.py:564-567` (`_profile_version` docstring: "two feed the agent's tools: verified observations (`query_observations`, `compute_trend`) and verified … `Document.status == "verified"`").

## 3. Investigation findings the executor must know

1. **What the legacy code does today (`main@40f590e`, same at B).**
   - `modules/rag.py:323-332` selects observations by profile, analyte and non-null value only; the `where` is at `:325-329`. The handoff/matrix cite this as `:322-328`, where `:322` is the `try:`.
   - `modules/rag.py:549-553` joins `Chunk`/`Embedding`/`Document` with no status filter. It already *computes* `"is_user_verified": document.status == "verified"` (`:607`), but never filters on it.
2. **Chunks have no verification state of their own** (`models/chunk.py:24-80`: no verified column). Verification lives on the parent `Document.status`, set to `"verified"` in exactly two places:
   - `POST /documents/{id}/verify` (`api/documents.py:1249-1280`, `:1278`);
   - auto-promotion when the last unverified observation of a document is verified (`api/observations.py:476-489`).

   The narrowest faithful reading, which invents no data model, is the agent's R-5 rule (Task 3). **Owner question O-5** covers it.
3. **Consequence of the chunk rule.** A document with **zero observations** can never reach `status == "verified"` through the UI: "Mark Document Verified" is `disabled={!observations?.length || …}` (`main@40f590e` `src/frontend/src/pages/VerificationWorkbench.tsx:523-527`; not changed by A or B). This affects text-only visit notes, imaging and pathology reports (INGEST-F categories, `modules/rag.py:186`). Under Task 3 their chunks leave legacy RAG permanently, as they are already absent from the agent's `retrieve_chunks`. Filtering observations but **not** chunks is not a faithful alternative: a lab PDF's chunk text contains the same unverified values verbatim.
4. **Every existing legacy-retrieval test is blind to a `WHERE` clause.** `tests/test_rag_trend_units.py:36-41`, `tests/test_biomarker_assistant.py:186-192` and `tests/test_rag_category_filter.py:120-130` all use fake sessions that return seeded rows whatever the statement says. Some seed `user_verified=False` (`test_rag_trend_units.py:57`; `test_biomarker_assistant.py:35` default). They will stay green after the filter, and they cannot prove it (recurring-failures #1). HC-VER-001/003/004 therefore use a real in-memory SQLite session.
5. **`_get_observation_chunks` swallows every exception** (`modules/rag.py:450-451`, `except Exception … logger.debug`). A broken query returns no chunks, so "value absent" assertions pass vacuously. Every absence test below is paired with a positive control.
6. **Other legacy-RAG callers affected by the filter** (`B@7b2ff1f`):
   - chat legacy branch `api/assistant.py:811-826`, which runs when the agent is off or raises; `AGENT_ENABLED_DEFAULT = True` at `modules/agent/settings.py:19`;
   - the LabInterpreter grounded explanation, which **always** uses legacy RAG: `api/interpretations.py:426-452`.
   - The eval scorer only calls `RAGModule.compose_prompt` (`B@7b2ff1f` `modules/agent/eval/scorer.py:387-401`), never retrieval, so the golden set cannot move.
7. **Unverified values reach patients by paths that are not `modules/rag.py` retrieval.**
   - (a) **The no-LLM knowledge fallback** (independently confirmed after the W-4 author flagged it). `_fetch_latest_obs` selects the newest observation with no verified filter: `B@7b2ff1f` `api/assistant.py:1329-1347`, where the `where` is `:1337-1341`; `main@40f590e` `:1272-1290`. The fallback cites it as `Citation(source_type="user_observation", …)` with `[cite:N]` (B `:1383-1403`).

     **Decision: owner-gated, opt-in (O-1; revised after review round 1).** D4 names "legacy RAG". This fallback changes patient-visible output and is not literally named, so Task 7 runs **only if O-1 is signed "yes"**. Otherwise it is skipped and listed in the PR as an open owner item.

     The case for "yes", for the owner:
     1. Its only caller is the chat route's `except ModelUnavailableError` (B `:904-923`).
     2. `ModelUnavailableError` is raised only by legacy `rag.query` (`modules/rag.py:1277-1281`). So the fallback is the legacy path's answer when no model is installed.
     3. It cites the value, and the agent never cites an unverified value.
   - (b) The interpretations question string embeds the observation's own value: `api/interpretations.py:427-432`. See O-3.
8. **A second trend chart plots the same endpoint:** `components/lab-interpreter/InterpretedTrendChart.tsx:36-43`. Its latest-value badge uses the green `'verified'` variant for any non-abnormal point, verified or not (`:78-81`). D4's "visibly marked" applies to it (Task 6; owner may veto, O-2).
9. **Measured 2026-09-27 (context, not a target).** `/mnt/c/Python313/python.exe -B scripts/agent_eval_gate.py` on `main@40f590e` (Windows Python 3.13.7, dirty tree):
   - it printed `total cases: 74`, all bars met, `All 74 golden cases passed.`, `Agent eval gate: PASS`;
   - the process then **did not exit within 300 s** (`timeout` exit 124).
   - Re-measure with the 3.11 venv in Task 0. If the hang reproduces, record it; do not treat it as a W-3 failure.

## 4. Files

**Create**

| Path | Responsibility |
|---|---|
| `src/backend/tests/test_verified_only_consumers.py` | HC-VER-001…005 |
| `src/frontend/src/components/TrendVerificationMarkers.tsx` | `TrendPointDot`, `UnverifiedTrendNote`, `UNVERIFIED_LABEL`, shared by both charts |
| `src/frontend/src/__tests__/TrendVerificationMarkers.test.tsx` | HC-VER-FE-002 |
| `src/frontend/src/__tests__/InterpretedTrendChart.test.tsx` | HC-VER-FE-003 |

**Modify** (`main@40f590e` lines)

| Path | Hunk |
|---|---|
| `src/backend/api/observations.py` | `TrendPoint` `:156-168`; point construction `:608-618` |
| `src/backend/modules/rag.py` | observation statement `:323-332`; vector statement `:549-553` (Task 3, gated by O-5) |
| `src/frontend/src/services/types.ts` | `TrendPoint` `:192-204` |
| `src/frontend/src/pages/TrendsDashboard.tsx` | `chartData` `:145-156`; tooltip `:434-461`; `Line` `:479-487`; info box `:496-515` |
| `src/frontend/src/components/lab-interpreter/InterpretedTrendChart.tsx` | `chartData` `:36-43`; badge `:78-81`; `Line` `:158-166`; note after the chart `:169` |
| `src/frontend/src/__tests__/TrendsDashboard.test.tsx` | fixture `:68-107` (+`user_verified: true`); new describe block |
| `src/backend/api/assistant.py` (**only if O-1 is signed "yes"**) | the `where` in `_build_knowledge_fallback._fetch_latest_obs` only (Task 7): `B@7b2ff1f` `:1337-1341`, `main@40f590e` `:1280-1284`. W-4 lands first and shifts these lines; re-anchor by grep |
| `CLAUDE.md`, `AGENT.md` | the **collected-count slot only**, updated in each commit that changes collection (Tasks 1, 2, 3, 7). Locate them with `grep -n "collected" CLAUDE.md AGENT.md`: `main@40f590e` `CLAUDE.md:30-35`, `AGENT.md:57`; `B@7b2ff1f` `AGENT.md:76` |

**Read-only (do not edit):**
- ask-first: `modules/faithfulness.py`, `modules/verifier_agent.py`, `modules/interpret_safety.py`, `modules/redaction.py`, `core/auth.py`;
- agent path and eval gate: `modules/agent/**`, `tests/agent/**` (incl. `golden/*.json`), `scripts/agent_eval_gate.py`;
- `tests/support/routes.py`: P7 then G-B1 own it; this plan uses `client.app.dependency_overrides` instead of editing it;
- W-7's surface: `api/interpretations.py`, `modules/interpret.py`;
- other product code: `api/documents.py`, `pages/VerificationWorkbench.tsx`;
- docs: `docs/compliance/data-privacy.md` (W-10), `docs/architecture/pipelines.md` (P4), everything under `docs/capstone-report/` and `audit/`.

## 5. Dependencies and shared-file order

| Needs | Why |
|---|---|
| **P1** merged | brings B's `api/assistant.py`, the `agent-evals` CI job (`B@7b2ff1f` `.github/workflows/ci.yml:150-168`) and the merged baseline |
| **P5** merged | P5 Task 3 edits `api/observations.py:459,489` (program: "`api/observations.py` (P5 → G-A)") |
| **W-10** governance commit landed | it edits `CLAUDE.md`; this plan edits only the baseline lines of `CLAUDE.md`/`AGENT.md` afterwards (program overlap row "each phase writes its own measured count; never edit concurrently") |
| **D4** | approval (§1) |
| **D9** | 3.11 venv |
| **W-4** merged | W-4 adds a helper to `api/assistant.py` (orchestrator-set order **P1 → W-4 → W-3** on that file). W-4 does not edit `modules/rag.py` (W-4 §4 shared-file table) |
| **O-5** signed | before Task 3 only |
| **O-1** signed "yes" | before Task 7 only (opt-in) |

**Shared-file order (the orchestrator confirms):**
- `api/observations.py`: **P5 → W-3**.
- `api/assistant.py`: **P1 → W-4 → W-3** (Task 7), as set by the orchestrator.
- `modules/rag.py`: **W-5 → W-3 → W-8**, serialized and never concurrent (canonical order, Wave-3 integration B-2). W-4 does not edit this file.
  - The hunks are disjoint: W-5 edits the prompt at `:123-140`; W-3 edits `:323-332` and `:549-553`.
  - There is no functional coupling. The W-4 author reports that W-4's legacy eval gate fakes retrieval, so W-3's filters cannot flip it.
  - W-3 goes after W-5 on `rag.py` and after W-4 on `api/assistant.py`, so one phase finishes each file at a time. W-8 follows W-3 on `rag.py`: both edit the `_search_vectors_async` statement (`:549-553`).
- `CLAUDE.md` / `AGENT.md`: **W-10 → W-3**, collected-count slot only, and never concurrent with any other phase's baseline edit.
- `src/frontend/src/services/types.ts`: no other 2026-09-27 plan edits this file (W-6 edits `services/modelSettings.ts`, not `types.ts`).

## 6. Tasks

### Task 0: Worktree, preconditions, phase-start measurement

**Files:** none modified.

- [ ] **Step 1: Create the phase worktree and prove it is post-P1:**
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/HealthCentral
  git fetch origin && git worktree add /mnt/c/Users/DangT/Documents/GitHub/hc-w03 -b feat/w03-verified-only-rag origin/main
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03
  git merge-base --is-ancestor 7b2ff1f HEAD && git merge-base --is-ancestor 692fdf3 HEAD && echo post-P1-ok
  EV=/mnt/c/Users/DangT/Documents/GitHub/w03-evidence
  mkdir -p "$EV"
  git -C /mnt/c/Users/DangT/Documents/GitHub/hc-w03 rev-parse HEAD > "$EV/START_SHA"
  cat "$EV/START_SHA"
  ```
  Expected: `post-P1-ok`, then a 40-character SHA. Otherwise **STOP**. `$EV/START_SHA` is the phase's start commit, used by Task 8 Step 3.
- [ ] **Step 2: Confirm the other dependencies landed:**
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03
  grep -c "datetime\.utcnow" src/backend/api/observations.py        # expect 0 → P5 landed
  grep -n "owner-decisions-2026-09-27" CLAUDE.md                    # expect >=1 hit → W-10 governance commit landed
  git log -1 --format='%h %s' origin/main -- src/backend/api/assistant.py   # expect W-4's commit subject → W-4 landed
  test -x ~/venvs/asclexis-311/bin/python && ~/venvs/asclexis-311/bin/python --version   # expect Python 3.11.x
  ```
  If any check fails: **STOP** and report which one.
- [ ] **Step 3: Confirm no test-ID collision:**
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03
  git grep -nE "HC-VER-[0-9]|hc_ver_0|HC-VER-FE" -- src
  ```
  Expected: no output.
- [ ] **Step 4: Measure the backend** (WSL):
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03/src/backend
  EV=/mnt/c/Users/DangT/Documents/GitHub/w03-evidence
  find . -name __pycache__ -type d -prune -exec rm -rf {} +
  ~/venvs/asclexis-311/bin/python -m pytest tests/ --collect-only -q -p no:cacheprovider > "$EV/collect-start.txt" 2>&1; echo "collect exit=$?"
  grep -E "[0-9]+ tests? collected" "$EV/collect-start.txt"
  ~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q -rfE --junitxml="$EV/junit-start.xml" > "$EV/pytest-start.txt" 2>&1; echo "pytest exit=$?"
  ~/venvs/asclexis-311/bin/python - "$EV/junit-start.xml" "$EV/failed-start.txt" <<'EOF'
  import sys, xml.etree.ElementTree as ET
  root = ET.parse(sys.argv[1]).getroot()
  ids = sorted(
      f"{tc.get('classname')}::{tc.get('name')}"
      for tc in root.iter("testcase")
      if tc.find("failure") is not None or tc.find("error") is not None
  )
  with open(sys.argv[2], "w") as fh:
      fh.write("".join(i + "\n" for i in ids))
  print(f"failed+errored={len(ids)}")
  print("\n".join(ids))
  EOF
  ```
  Record the start collected count (the `collected` line; the full output is in `$EV/collect-start.txt`), the full failure-ID set (`$EV/failed-start.txt`, all of it, printed above), the interpreter, the OS and the command. The complete run log is `$EV/pytest-start.txt`; nothing is truncated.
- [ ] **Step 5: Re-verify line anchors on this tree:**
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03
  grep -n "Observation.value.isnot(None)" src/backend/modules/rag.py          # observation stmt; main had :328
  grep -n "join(Document, Chunk.doc_id == Document.id)" src/backend/modules/rag.py  # vector stmt; main had :552
  grep -n "class TrendPoint\|data_points.append(TrendPoint" src/backend/api/observations.py  # main :156, :608
  grep -n "dot={{" src/frontend/src/pages/TrendsDashboard.tsx src/frontend/src/components/lab-interpreter/InterpretedTrendChart.tsx
  grep -n "async def _fetch_latest_obs\|async def _build_knowledge_fallback\|except ModelUnavailableError" src/backend/api/assistant.py  # B: :1329, :1281, :904
  ```
  Use the lines printed, not the ones in this plan.
- [ ] **Step 6: Capture the eval-gate baseline:**
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03
  EV=/mnt/c/Users/DangT/Documents/GitHub/w03-evidence
  mkdir -p "$EV"
  timeout 900 ~/venvs/asclexis-311/bin/python scripts/agent_eval_gate.py > "$EV/w03-eval-start.txt" 2>&1; echo "exit=$?"
  cat "$EV/w03-eval-start.txt"
  ```
  Expected: the full report, including `All 74 golden cases passed.` and `Agent eval gate: PASS`. 74 was measured on main on 2026-09-27; if the number differs, record the number printed. Record the exit code. `124` means the process hung after printing (§3.9).
- [ ] **Step 7: Measure the frontend** (Windows PowerShell). Set the location once; every later PowerShell block in this plan assumes it:
  ```powershell
  $EV = 'C:\Users\DangT\Documents\GitHub\w03-evidence'
  New-Item -ItemType Directory -Force -Path $EV | Out-Null
  Set-Location C:\Users\DangT\Documents\GitHub\hc-w03\src\frontend
  npx tsc --noEmit; "tsc exit=$LASTEXITCODE"
  npx vitest run --reporter=default --reporter=json --outputFile.json="$EV\vitest-start.json"; "vitest exit=$LASTEXITCODE"
  $r = Get-Content "$EV\vitest-start.json" -Raw | ConvertFrom-Json
  "total=$($r.numTotalTests) failed=$($r.numFailedTests)"
  @($r.testResults | ForEach-Object { $_.assertionResults } | Where-Object { $_.status -eq 'failed' } |
    ForEach-Object { $_.fullName } | Sort-Object) | Set-Content "$EV\vitest-start-failed.txt"
  Get-Content "$EV\vitest-start-failed.txt"
  ```
  Record both exit codes, `total`/`failed` as `START_VITEST`, and every failing test name (`$EV\vitest-start-failed.txt`) as `START_VITEST_FAILED`. If vitest cannot run, record `UNMEASURED` with the exact error text, then continue with the backend tasks. Do not claim frontend results later.

---

### Task 1: HC-VER-002 — trend points carry `user_verified` (over HTTP)

**Files:**
- Modify: `src/backend/api/observations.py` (`TrendPoint`, point construction)
- Create: `src/backend/tests/test_verified_only_consumers.py`

**Interfaces:**
- Produces: `TrendPoint.user_verified: bool` (default `False`). JSON key `data_points[i].user_verified`. Task 4 consumes it.
- The default is `False`, not a required field. `tests/test_date_extraction.py:369-377` builds `TrendPoint(...)` without the field. A required field would break that unrelated test, and `False` fails toward labelling.

- [ ] **Step 1: Write the failing test.** Create `src/backend/tests/test_verified_only_consumers.py`:
  ```python
  """W-3 / owner decision D4 (2026-09-27): verified-only legacy RAG, labelled trends.

  HC-VER-001..004. Retrieval tests use a REAL in-memory SQLite session: every
  pre-existing legacy-retrieval test uses a fake session that ignores WHERE
  clauses, so it cannot see a verification filter (recurring-failures #1).
  """
  from __future__ import annotations

  import sys
  import uuid
  from datetime import datetime
  from pathlib import Path
  from types import SimpleNamespace
  from unittest.mock import AsyncMock

  import pytest
  import pytest_asyncio
  from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

  sys.path.insert(0, str(Path(__file__).parent.parent))

  import api.observations as observations_api  # noqa: E402
  from api.observations import router as observations_router  # noqa: E402
  from core.auth import get_profile_db_session  # noqa: E402
  from core.profile_database import ProfileDatabaseBase  # noqa: E402
  from models import Chunk, Document, Embedding, Observation  # noqa: E402
  from modules.rag import RAGModule  # noqa: E402
  from tests.support.routes import route_client  # noqa: E402

  PROFILE = "profile-w03"


  # ── HC-VER-002: trends over HTTP ─────────────────────────────────────────────

  class _Scalars:
      def __init__(self, rows: list) -> None:
          self._rows = rows

      def all(self) -> list:
          return self._rows


  class _Result:
      def __init__(self, rows: list) -> None:
          self._rows = rows

      def scalars(self) -> _Scalars:
          return _Scalars(self._rows)


  class _FakeProfileDb:
      """Returns the seeded rows whatever the statement: fine here, because the
      trends route must NOT filter by verification (D4: trends may show them)."""

      def __init__(self, rows: list) -> None:
          self._rows = rows

      async def execute(self, _stmt) -> _Result:
          return _Result(self._rows)


  def _trend_row(*, value: float, collected_at: datetime, user_verified: bool) -> SimpleNamespace:
      return SimpleNamespace(
          id=str(uuid.uuid4()), profile_id=PROFILE, doc_id="doc-a",
          analyte_canonical="glucose", analyte_raw="Glucose",
          value=value, value_text=None, unit="mg/dL",
          ref_low=70.0, ref_high=99.0, ref_range_text=None,
          flag=None, is_abnormal=False, collected_at=collected_at,
          user_verified=user_verified, extraction_confidence=0.9,
          source_page=None, source_bbox_json=None,
      )


  def test_hc_ver_002_trend_points_carry_user_verified_over_http(monkeypatch) -> None:
      rows = [
          _trend_row(value=90.0, collected_at=datetime(2025, 1, 10), user_verified=True),
          _trend_row(value=130.0, collected_at=datetime(2025, 6, 10), user_verified=False),
      ]
      monkeypatch.setattr(
          observations_api, "log_observation_event", AsyncMock(return_value=object())
      )

      async def _override_profile_db():
          return _FakeProfileDb(rows)

      with route_client(observations_router, "/observations", profile_id=PROFILE) as client:
          # route_client overrides auth + master DB only; add the profile DB here
          # rather than editing tests/support/routes.py (owned by P7 / G-B1).
          client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
          response = client.get("/observations/trends/glucose")

      assert response.status_code == 200, response.text
      points = response.json()["data_points"]
      # Both points are still shown (D4: trends MAY show unverified) and each
      # carries its own row's flag — a constant True or False fails this.
      assert [(p["value"], p["user_verified"]) for p in points] == [
          (90.0, True),
          (130.0, False),
      ]
  ```
- [ ] **Step 2: Run it and watch it fail:**
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03/src/backend
  ~/venvs/asclexis-311/bin/python -m pytest tests/test_verified_only_consumers.py -p no:cacheprovider -q -k hc_ver_002
  ```
  Expected: `FAILED … KeyError: 'user_verified'`. Paste the line into the task log.
- [ ] **Step 3: Minimal implementation** in `src/backend/api/observations.py`:
  ```python
  class TrendPoint(BaseModel):
      """Single point in a trend series."""
      date: str
      value: float
      unit: str
      is_abnormal: bool
      flag: Optional[str] = None
      doc_id: str
      extraction_confidence: Optional[float] = None
      # Provenance when the point was converted from a differently-reported unit
      # (NORM-UNIT-001). Both None when no conversion happened.
      original_value: Optional[float] = None
      original_unit: Optional[str] = None
      # D4 (owner, 2026-09-27): trends may show unverified points but must mark
      # them. Defaults to False so a point is never presented as verified by omission.
      user_verified: bool = False
  ```
  In the `TrendPoint(...)` call (main `:608-618`), add one keyword after `original_unit=original_unit,`:
  ```python
                      user_verified=obs.user_verified is True,
  ```
- [ ] **Step 4: Run to green.** Same command. Expected: `1 passed`.
- [ ] **Step 5: Break it on purpose.** Temporarily change the keyword to `user_verified=True,`, re-run, and see `AssertionError` on `(130.0, False)`. Restore and re-run to `1 passed`.
- [ ] **Step 6: Run the neighbours:**
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03/src/backend
  ~/venvs/asclexis-311/bin/python -m pytest tests/test_observations_audit.py tests/test_unit_conversion.py tests/test_date_extraction.py -p no:cacheprovider -q
  ```
  Expected: every test named in a `FAILED`/`ERROR` summary line also appears in `/mnt/c/Users/DangT/Documents/GitHub/w03-evidence/failed-start.txt`. That file holds junit ids in dotted form (`tests.test_rag_pipeline::test_name`), so match on the test name.
- [ ] **Step 7a: Update the collected count only** (CLAUDE.md rule: the commit that changes collection updates the baseline):
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03/src/backend
  EV=/mnt/c/Users/DangT/Documents/GitHub/w03-evidence
  ~/venvs/asclexis-311/bin/python -m pytest tests/ --collect-only -q -p no:cacheprovider > "$EV/collect-now.txt" 2>&1; echo "collect exit=$?"
  grep -E "[0-9]+ tests? collected" "$EV/collect-now.txt"
  ```
  Write that number into the **collected slots only**: `CLAUDE.md` "Baseline: **N backend tests collected.**" and `AGENT.md` "(N collected;". Leave every pass-count sentence ("all N pass", "N pass in CI, N-1 without an embedding model") unchanged. Flag it in the PR unless you measured a pass count in a named environment.
- [ ] **Step 7b: Commit** (code + test + collected slots):
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03
  git add src/backend/api/observations.py src/backend/tests/test_verified_only_consumers.py CLAUDE.md AGENT.md
  git diff --cached --name-only    # exactly these 4 paths
  git commit -m "feat(observations): flag user_verified on each trend point (D4)" -- src/backend/api/observations.py src/backend/tests/test_verified_only_consumers.py CLAUDE.md AGENT.md
  ```

**What this test would fail to notice:** whether the UI shows the flag (Tasks 4-6). It also cannot see SQL-level behaviour, because the fake session ignores the statement. That is acceptable here only because the route must not filter.

---

### Task 2: HC-VER-001 + HC-VER-004 — legacy RAG reads verified observations only

**Files:**
- Modify: `src/backend/modules/rag.py` (observation statement, main `:323-332`)
- Test: `src/backend/tests/test_verified_only_consumers.py`

**Interfaces:**
- Consumes: `RAGModule.query(question, profile_id, selected_analytes, include_references, model_runner, master_db, profile_db)` (`modules/rag.py:1174-1189`).
- Produces: no signature change. `RetrievedChunk.is_user_verified` becomes always `True` for `user_observation` chunks.

- [ ] **Step 1: Write the failing tests.** Append to the test file:
  ```python
  # ── real profile DB + legacy RAG helpers ────────────────────────────────────

  @pytest_asyncio.fixture
  async def real_profile_db():
      engine = create_async_engine("sqlite+aiosqlite://")
      async with engine.begin() as conn:
          await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
      session = AsyncSession(engine, expire_on_commit=False)
      try:
          yield session
      finally:
          await session.close()
          await engine.dispose()


  class _StubEmbedder:
      """Deterministic stand-in: the test never loads or downloads a model, so it
      does not depend on the environment the way test_api_rag_index_002b does."""

      def embed_text(self, text: str) -> list[float]:
          return [1.0, 0.0]

      def blob_to_vector(self, blob: bytes) -> list[float]:
          return [1.0, 0.0]

      def cosine_similarity(self, a: list[float], b: list[float]) -> float:
          return 1.0


  class _CapturingRunner:
      """ModelRunner-shaped fake: records every prompt the legacy path would send."""

      def __init__(self) -> None:
          self.prompts: list[str] = []

      def is_available(self) -> bool:
          return True

      async def generate_async(self, prompt: str, config) -> SimpleNamespace:
          self.prompts.append(prompt)
          return SimpleNamespace(
              text="UNCERTAINTIES:\nI don't have enough information", finish_reason="stop"
          )


  def _document(doc_id: str, status: str) -> Document:
      return Document(
          id=doc_id, profile_id=PROFILE, path_hash="x" * 64,
          content_hash=uuid.uuid4().hex * 2, doc_type="lab_pdf",
          source=f"{doc_id}.pdf", status=status, imported_at=datetime(2025, 1, 1),
      )


  def _ldl(obs_id: str, doc_id: str, value: float, verified: bool, collected_at: datetime) -> Observation:
      return Observation(
          id=obs_id, profile_id=PROFILE, doc_id=doc_id,
          analyte_canonical="ldl_cholesterol", analyte_raw="LDL Cholesterol",
          value=value, unit="mg/dL", collected_at=collected_at, user_verified=verified,
      )


  def _rag() -> tuple[RAGModule, _CapturingRunner]:
      rag = RAGModule(enable_verification=False)
      rag._embedder = _StubEmbedder()
      return rag, _CapturingRunner()


  async def _ask(rag: RAGModule, runner: _CapturingRunner, db: AsyncSession, question: str, analytes):
      return await rag.query(
          question=question, profile_id=PROFILE, selected_analytes=analytes,
          include_references=False, model_runner=runner, master_db=None, profile_db=db,
      )


  # ── HC-VER-001 / HC-VER-004: observations ──────────────────────────────────

  @pytest.mark.asyncio
  async def test_hc_ver_001_unverified_observation_absent_from_legacy_rag_context(real_profile_db) -> None:
      db = real_profile_db
      db.add_all([_document("doc-v", "verified"), _document("doc-u", "parsed")])
      db.add_all([
          _ldl("obs-v", "doc-v", 101.0, True, datetime(2025, 1, 10)),
          # Newer, so without the filter it becomes "Latest value".
          _ldl("obs-u", "doc-u", 187.0, False, datetime(2025, 6, 10)),
      ])
      await db.commit()
      rag, runner = _rag()

      await _ask(rag, runner, db, "How is my LDL?", ["ldl_cholesterol"])

      # Positive control first: _get_observation_chunks swallows exceptions
      # (modules/rag.py:450-451), so a broken query would make the absence
      # assertion pass vacuously.
      assert len(runner.prompts) == 1, "verified LDL should still reach the model"
      prompt = runner.prompts[0]
      assert "101.0" in prompt, "positive control: verified value missing from context"
      assert "187.0" not in prompt, "unverified value 187.0 reached the legacy RAG prompt"


  @pytest.mark.asyncio
  async def test_hc_ver_004_only_unverified_data_yields_insufficient_context_without_llm_call(real_profile_db) -> None:
      db = real_profile_db
      db.add(_document("doc-u", "parsed"))
      db.add(_ldl("obs-u", "doc-u", 187.0, False, datetime(2025, 6, 10)))
      await db.commit()
      rag, runner = _rag()

      result = await _ask(rag, runner, db, "How is my LDL?", ["ldl_cholesterol"])

      assert runner.prompts == [], "runner was called with a prompt although only unverified data exists"
      assert result.insufficient_context is True
  ```
- [ ] **Step 2: Run them and watch them fail:**
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03/src/backend
  ~/venvs/asclexis-311/bin/python -m pytest tests/test_verified_only_consumers.py -p no:cacheprovider -q -k "hc_ver_001 or hc_ver_004"
  ```
  Expected: `2 failed`, with `AssertionError: unverified value 187.0 reached the legacy RAG prompt` and `AssertionError: runner was called with a prompt although only unverified data exists`. If instead either test errors on fixture or model construction, fix the **test setup** (not `rag.py`) until both fail on those messages.
- [ ] **Step 3: Minimal implementation.** In `src/backend/modules/rag.py` `_get_observation_chunks`, change the `.where(...)`:
  ```python
                      .where(
                          Observation.profile_id == profile_id,
                          Observation.analyte_canonical == analyte,
                          Observation.value.isnot(None),
                          # D4 (owner, 2026-09-27): legacy RAG cites verified values
                          # only — same filter as the agent's query_observations /
                          # compute_trend tools.
                          Observation.user_verified == True,  # noqa: E712
                      )
  ```
  Leave `:433-434` (`"(User-verified result)"`) and `:446` unchanged; they are now always true. Surgical edits only.
- [ ] **Step 4: Run to green.** Same command. Expected: `2 passed`.
- [ ] **Step 5: Break it on purpose.** Delete the `Observation.user_verified == True` line, re-run, and see `2 failed` with the messages above. Restore and re-run to `2 passed`.
- [ ] **Step 6: Run the legacy-RAG neighbours:**
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03/src/backend
  ~/venvs/asclexis-311/bin/python -m pytest tests/test_biomarker_assistant.py tests/test_rag_trend_units.py tests/test_rag_pipeline.py tests/test_rag_category_filter.py tests/test_memory_integration.py tests/test_chat_sessions.py -p no:cacheprovider -q
  ```
  Expected: every test named in a `FAILED`/`ERROR` summary line also appears in `/mnt/c/Users/DangT/Documents/GitHub/w03-evidence/failed-start.txt`. That file holds junit ids in dotted form (`tests.test_rag_pipeline::test_name`), so match on the test name. If one appears, STOP (§8). It is either a test that asserted unverified data reaches legacy RAG (an intended D4 change, to be listed in the PR with the owner's knowledge) or a regression.
- [ ] **Step 7a: Update the collected count only** (CLAUDE.md rule: the commit that changes collection updates the baseline):
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03/src/backend
  EV=/mnt/c/Users/DangT/Documents/GitHub/w03-evidence
  ~/venvs/asclexis-311/bin/python -m pytest tests/ --collect-only -q -p no:cacheprovider > "$EV/collect-now.txt" 2>&1; echo "collect exit=$?"
  grep -E "[0-9]+ tests? collected" "$EV/collect-now.txt"
  ```
  Write that number into the **collected slots only**: `CLAUDE.md` "Baseline: **N backend tests collected.**" and `AGENT.md` "(N collected;". Leave every pass-count sentence ("all N pass", "N pass in CI, N-1 without an embedding model") unchanged. Flag it in the PR unless you measured a pass count in a named environment.
- [ ] **Step 7b: Commit** (code + test + collected slots):
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03
  git add src/backend/modules/rag.py src/backend/tests/test_verified_only_consumers.py CLAUDE.md AGENT.md
  git diff --cached --name-only    # exactly these 4 paths
  git commit -m "fix(rag): legacy RAG reads verified observations only (D4)" -- src/backend/modules/rag.py src/backend/tests/test_verified_only_consumers.py CLAUDE.md AGENT.md
  ```

**What these tests would fail to notice:**
- the chunk path (Task 3);
- the value that `api/interpretations.py:427-432` puts in the *question* (O-3);
- the no-LLM fallback (Task 7);
- whether the patient-facing insufficient-context wording is still accurate (O-4).
- HC-VER-004 alone could pass vacuously if the query raised. It relies on HC-VER-001's positive control, so keep both.

---

### Task 3 (gated by O-5): HC-VER-003 — legacy RAG retrieves chunks from verified documents only

**STOP before this task unless the O-5 line in §10 is signed.** Tasks 4-6 do not depend on it.

**Files:**
- Modify: `src/backend/modules/rag.py` (vector statement, main `:549-553`)
- Test: `src/backend/tests/test_verified_only_consumers.py`

**Interfaces:** no signature change. `chunk_data["is_user_verified"]` (`:607`) becomes always `True`.

- [ ] **Step 1: Write the failing test.** Append:
  ```python
  # ── HC-VER-003: document chunks (vector path, _search_vectors_async) ───────

  def _chunk_with_embedding(chunk_id: str, doc_id: str, text: str) -> list:
      return [
          Chunk(id=chunk_id, doc_id=doc_id, chunk_index=0, text=text, page_number=1),
          Embedding(chunk_id=chunk_id, model_name="stub", vector_blob=b"\x00", dimensions=2),
      ]


  @pytest.mark.asyncio
  async def test_hc_ver_003_unverified_document_chunk_absent_from_legacy_rag_context(real_profile_db) -> None:
      db = real_profile_db
      db.add_all([_document("doc-v", "verified"), _document("doc-u", "parsed")])
      # Distinct tokens: neither may be a substring of the other.
      db.add_all(_chunk_with_embedding("chunk-v", "doc-v", "ALPHA-VERIFIED-CHUNK report text"))
      db.add_all(_chunk_with_embedding("chunk-u", "doc-u", "BRAVO-PENDING-CHUNK report text"))
      await db.commit()
      rag, runner = _rag()

      await _ask(rag, runner, db, "What does my report say?", None)

      assert len(runner.prompts) == 1, "verified document chunk should still reach the model"
      prompt = runner.prompts[0]
      assert "ALPHA-VERIFIED-CHUNK" in prompt, "positive control: verified-document chunk missing"
      assert "BRAVO-PENDING-CHUNK" not in prompt, "unverified-document chunk text reached the legacy RAG prompt"
  ```
- [ ] **Step 2: Run it and watch it fail:**
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03/src/backend
  ~/venvs/asclexis-311/bin/python -m pytest tests/test_verified_only_consumers.py -p no:cacheprovider -q -k hc_ver_003
  ```
  Expected: `AssertionError: unverified-document chunk text reached the legacy RAG prompt`.
- [ ] **Step 3: Minimal implementation.** In `_search_vectors_async`, change the base statement:
  ```python
          stmt = (
              select(Chunk, Embedding, Document)
              .join(Embedding, Chunk.id == Embedding.chunk_id)
              .join(Document, Chunk.doc_id == Document.id)
              # D4: chunks have no verified flag of their own; they inherit the
              # parent document's (RECONCILIATION R-5), exactly as the agent's
              # retrieve_chunks tool filters (modules/agent/tools/retrieve_chunks.py:73).
              .where(Document.status == "verified")
          )
  ```
  `Document.status` is `nullable=False` (`models/document.py:57`), and this is an equality filter, so no NULL row slips through (recurring-failures #7).
- [ ] **Step 4: Run to green.** Expected: `1 passed`.
- [ ] **Step 5: Break it on purpose.** Remove the `.where(...)` line and see red. Restore and see green.
- [ ] **Step 6: Neighbours.** Re-run the Task 2 Step 6 command. Expected: no new failures.
- [ ] **Step 7a: Update the collected count only** (CLAUDE.md rule: the commit that changes collection updates the baseline):
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03/src/backend
  EV=/mnt/c/Users/DangT/Documents/GitHub/w03-evidence
  ~/venvs/asclexis-311/bin/python -m pytest tests/ --collect-only -q -p no:cacheprovider > "$EV/collect-now.txt" 2>&1; echo "collect exit=$?"
  grep -E "[0-9]+ tests? collected" "$EV/collect-now.txt"
  ```
  Write that number into the **collected slots only**: `CLAUDE.md` "Baseline: **N backend tests collected.**" and `AGENT.md` "(N collected;". Leave every pass-count sentence ("all N pass", "N pass in CI, N-1 without an embedding model") unchanged. Flag it in the PR unless you measured a pass count in a named environment.
- [ ] **Step 7b: Commit** (code + test + collected slots):
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03
  git add src/backend/modules/rag.py src/backend/tests/test_verified_only_consumers.py CLAUDE.md AGENT.md
  git diff --cached --name-only
  git commit -m "fix(rag): legacy RAG retrieves chunks from verified documents only (D4)" -- src/backend/modules/rag.py src/backend/tests/test_verified_only_consumers.py CLAUDE.md AGENT.md
  ```

**What this test would fail to notice:** the category-filtered path (`category="imaging"` etc.) is not exercised. The consequence for documents with zero observations (§3.3) is a product effect, not a test failure, so state it in the PR.

---

### Task 4: Frontend type + shared markers — HC-VER-FE-002

**Files:**
- Modify: `src/frontend/src/services/types.ts`
- Create: `src/frontend/src/components/TrendVerificationMarkers.tsx`
- Create: `src/frontend/src/__tests__/TrendVerificationMarkers.test.tsx`

**Interfaces (Produces):**
- `TrendPoint.user_verified: boolean`
- `UNVERIFIED_LABEL = 'Unverified'`
- `TrendPointDot({ cx?: number; cy?: number; verified: boolean; radius?: number; color?: string }): ReactElement | null`
- `UnverifiedTrendNote({ unverified: number; total: number }): ReactElement | null`, which renders `data-testid="trend-unverified-note"`.

- [ ] **Step 1: Write the failing test** `src/frontend/src/__tests__/TrendVerificationMarkers.test.tsx`:
  ```tsx
  import { describe, it, expect } from 'vitest';
  import { render, screen } from '@testing-library/react';
  import { TrendPointDot, UnverifiedTrendNote } from '@/components/TrendVerificationMarkers';

  describe('HC-VER-FE-002: trend verification markers (D4)', () => {
    it('draws an unverified point hollow, with a readable "Unverified" title', () => {
      const { container } = render(
        <svg><TrendPointDot cx={10} cy={20} verified={false} /></svg>
      );
      const marker = container.querySelector('[data-verified="false"]');
      expect(marker).not.toBeNull();
      expect(marker?.querySelector('title')?.textContent).toBe('Unverified');
      expect(marker?.querySelector('circle')?.getAttribute('fill')).toBe('#FFFFFF');
    });

    it('draws a verified point filled, with no unverified title', () => {
      const { container } = render(
        <svg><TrendPointDot cx={10} cy={20} verified /></svg>
      );
      expect(container.querySelector('[data-verified="true"]')).not.toBeNull();
      expect(container.querySelector('[data-verified="false"]')).toBeNull();
      expect(container.querySelector('title')).toBeNull();
    });

    it('states the unverified count in text, and renders nothing when there are none', () => {
      const { rerender } = render(<UnverifiedTrendNote unverified={1} total={3} />);
      expect(screen.getByTestId('trend-unverified-note')).toHaveTextContent(
        '1 of 3 points on this chart are unverified'
      );
      rerender(<UnverifiedTrendNote unverified={0} total={3} />);
      expect(screen.queryByTestId('trend-unverified-note')).not.toBeInTheDocument();
    });
  });
  ```
- [ ] **Step 2: Run it and watch it fail** (Windows; location already set in Task 0 Step 7):
  ```powershell
  npx vitest run src/__tests__/TrendVerificationMarkers.test.tsx; "vitest exit=$LASTEXITCODE"
  ```
  Expected: non-zero exit; `Failed to resolve import "@/components/TrendVerificationMarkers"`.
- [ ] **Step 3: Implement.** In `src/frontend/src/services/types.ts`, add inside `TrendPoint` after `original_unit?`:
  ```ts
    // D4 (owner, 2026-09-27): unverified points may be charted but must be marked.
    user_verified: boolean;
  ```
  Create `src/frontend/src/components/TrendVerificationMarkers.tsx`:
  ```tsx
  /**
   * Unverified-point markers for trend charts.
   * Owner decision D4 (2026-09-27): "Trends may show unverified points but
   * visibly marked 'unverified'". The state is never conveyed by colour alone:
   * the dot is hollow and dashed, carries an SVG <title>, and the chart shows a
   * text note with the count.
   */
  import type { ReactElement } from 'react';

  export const UNVERIFIED_LABEL = 'Unverified';

  interface TrendPointDotProps {
    cx?: number;
    cy?: number;
    verified: boolean;
    radius?: number;
    color?: string;
  }

  export function TrendPointDot({
    cx,
    cy,
    verified,
    radius = 5,
    color = '#2D7D6F',
  }: TrendPointDotProps): ReactElement | null {
    if (cx === undefined || cy === undefined) return null;
    if (verified) {
      return <circle cx={cx} cy={cy} r={radius} fill={color} strokeWidth={0} data-verified="true" />;
    }
    return (
      <g data-verified="false" role="img" aria-label={UNVERIFIED_LABEL}>
        <title>{UNVERIFIED_LABEL}</title>
        <circle
          cx={cx}
          cy={cy}
          r={radius}
          fill="#FFFFFF"
          stroke={color}
          strokeWidth={2}
          strokeDasharray="2 2"
        />
      </g>
    );
  }

  interface UnverifiedTrendNoteProps {
    unverified: number;
    total: number;
  }

  export function UnverifiedTrendNote({ unverified, total }: UnverifiedTrendNoteProps): ReactElement | null {
    if (unverified <= 0) return null;
    return (
      <p className="text-sm text-ink-secondary mt-1" data-testid="trend-unverified-note">
        <strong>{UNVERIFIED_LABEL}:</strong> {unverified} of {total} points on this chart are
        unverified (hollow markers). They have not been reviewed yet.
      </p>
    );
  }
  ```
- [ ] **Step 4: Run to green.** Same command. Expected: `3 passed`, `vitest exit=0`. Then run `npx tsc --noEmit; "tsc exit=$LASTEXITCODE"` → `tsc exit=0`.
- [ ] **Step 5: Break it on purpose.** Make `TrendPointDot` ignore `verified` (always the filled branch), see test 1 red (non-zero exit), then restore.
- [ ] **Step 6: Commit:**
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03
  git add src/frontend/src/services/types.ts src/frontend/src/components/TrendVerificationMarkers.tsx src/frontend/src/__tests__/TrendVerificationMarkers.test.tsx
  git diff --cached --name-only    # exactly these 3 paths
  git commit -m "feat(trends): shared unverified trend-point markers (D4)" -- src/frontend/src/services/types.ts src/frontend/src/components/TrendVerificationMarkers.tsx src/frontend/src/__tests__/TrendVerificationMarkers.test.tsx
  ```

---

### Task 5: TrendsDashboard marks unverified points — HC-VER-FE-001

**Files:**
- Modify: `src/frontend/src/pages/TrendsDashboard.tsx`
- Modify: `src/frontend/src/__tests__/TrendsDashboard.test.tsx`

**Interfaces:** consumes Task 4's exports and `TrendPoint.user_verified`.

- [ ] **Step 1: Update the fixture and write the failing tests.**
  - In `mockTrendData.data_points` (main `:74-107`), add `user_verified: true,` to each of the 4 points. The existing tests stay about verified data, and the fixture matches the new API contract.
  - Append inside `describe('TrendsDashboard', …)`:
  ```tsx
    describe('HC-VER-FE-001: unverified trend points are visibly marked (D4)', () => {
      const mixedTrend = {
        ...mockTrendData,
        data_points: [
          { ...mockTrendData.data_points[0], user_verified: true },
          { ...mockTrendData.data_points[1], user_verified: false },
        ],
      };

      it('shows a text note with the unverified count', async () => {
        setupApiMocks({ trendData: mixedTrend });
        renderWithProviders(<TrendsDashboard />);
        const note = await screen.findByTestId('trend-unverified-note');
        expect(note).toHaveTextContent('1 of 2 points on this chart are unverified');
      });

      it('marks the latest value as unverified when the newest point is unverified', async () => {
        setupApiMocks({ trendData: mixedTrend });
        renderWithProviders(<TrendsDashboard />);
        expect(
          await screen.findByText(/Latest value: 14\.1 g\/dL \(unverified\)/)
        ).toBeInTheDocument();
      });

      it('shows no unverified note when every charted point is verified', async () => {
        setupApiMocks({});
        renderWithProviders(<TrendsDashboard />);
        // Wait for a positive anchor first. A bare "not present" check passes on the
        // first empty render tick (recurring-failures #1).
        await screen.findByText(/increased by 2.9%/i);
        expect(screen.queryByTestId('trend-unverified-note')).not.toBeInTheDocument();
      });
    });
  ```
- [ ] **Step 2: Run them and watch them fail** (Windows):
  ```powershell
  npx vitest run src/__tests__/TrendsDashboard.test.tsx; "vitest exit=$LASTEXITCODE"
  ```
  Expected: non-zero exit; 2 new failures, with `Unable to find an element by: [data-testid="trend-unverified-note"]` and `Unable to find an element with the text: /Latest value: 14\.1 g\/dL \(unverified\)/`. The third new test and all pre-existing tests pass.
- [ ] **Step 3: Implement** in `TrendsDashboard.tsx`:
  - Import: `import { TrendPointDot, UnverifiedTrendNote, UNVERIFIED_LABEL } from '@/components/TrendVerificationMarkers';`
  - In `chartData` (main `:147-155`), add as the last property:
    ```ts
          // D4: a point without the flag is treated as unverified (fail toward labelling).
          verified: point.user_verified === true,
    ```
  - After `chartData`, add:
    ```ts
    const unverifiedPointCount = useMemo(
      () => chartData.filter((p) => !p.verified).length,
      [chartData]
    );
    ```
  - Tooltip (main `:436-458`): add `verified: boolean;` to the payload type. After the date line, add:
    ```tsx
                                  {!data.verified && (
                                    <p className="text-xs font-medium text-ink mt-1">
                                      {UNVERIFIED_LABEL}: not yet reviewed
                                    </p>
                                  )}
    ```
  - `Line` (main `:484`): replace `dot={{ fill: '#2D7D6F', strokeWidth: 0, r: 5 }}` with:
    ```tsx
                          dot={(dotProps: { cx?: number; cy?: number; index?: number; payload?: { verified?: boolean } }) => (
                            <TrendPointDot
                              key={`trend-dot-${dotProps.index ?? 0}`}
                              cx={dotProps.cx}
                              cy={dotProps.cy}
                              verified={dotProps.payload?.verified === true}
                            />
                          )}
    ```
    If `npx tsc --noEmit` rejects the parameter type, use the dot-props type that the tsc error names from `recharts` 3.9. Never use `any`.
  - Latest value (main `:497-499`): inside `<strong>`, after `{trendData.unit}`, add:
    ```tsx
                            {latestValue && latestValue.user_verified !== true && ' (unverified)'}
    ```
  - After the summary paragraph (main `:506-510`), add:
    ```tsx
                          <UnverifiedTrendNote unverified={unverifiedPointCount} total={chartData.length} />
    ```
- [ ] **Step 4: Run to green:**
  ```powershell
  npx vitest run src/__tests__/TrendsDashboard.test.tsx; "vitest exit=$LASTEXITCODE"
  npx tsc --noEmit; "tsc exit=$LASTEXITCODE"
  ```
  Expected: `vitest exit=0`, `tsc exit=0`.
- [ ] **Step 5: Break it on purpose.** Set `verified: true` in `chartData`, see the first two new tests red, then restore.
- [ ] **Step 6: Commit:**
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03
  git add src/frontend/src/pages/TrendsDashboard.tsx src/frontend/src/__tests__/TrendsDashboard.test.tsx
  git diff --cached --name-only
  git commit -m "feat(trends): mark unverified points on the trends chart (D4)" -- src/frontend/src/pages/TrendsDashboard.tsx src/frontend/src/__tests__/TrendsDashboard.test.tsx
  ```

**What these tests would fail to notice:**
- Whether Recharts actually draws `TrendPointDot` in the SVG. jsdom gives the mocked `ResponsiveContainer` no size, so the chart may not render marks. **UNMEASURED.** Task 8 Step 6 measures it manually.
- The tooltip line, which needs a hover on a laid-out chart.
- Colour contrast of the hollow marker.

---

### Task 6: LabInterpreter trend chart marks unverified points — HC-VER-FE-003

(In scope under D4 by default; the owner may veto via O-2. If vetoed, skip this task.)

**Files:**
- Modify: `src/frontend/src/components/lab-interpreter/InterpretedTrendChart.tsx`
- Create: `src/frontend/src/__tests__/InterpretedTrendChart.test.tsx`

- [ ] **Step 1: Write the failing test:**
  ```tsx
  import { describe, it, expect, vi } from 'vitest';
  import { render, screen } from '@testing-library/react';
  import { InterpretedTrendChart } from '@/components/lab-interpreter/InterpretedTrendChart';
  import type { TrendData } from '@/services/types';

  vi.mock('recharts', async () => {
    const actual = await vi.importActual('recharts');
    return {
      ...actual,
      ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
        <div data-testid="responsive-container">{children}</div>
      ),
    };
  });

  const point = (date: string, value: number, user_verified: boolean) => ({
    date, value, unit: 'mg/dL', is_abnormal: false, flag: null, doc_id: 'd',
    extraction_confidence: 0.9, user_verified,
  });

  const trend = (verified: boolean[]): TrendData => ({
    analyte_canonical: 'glucose', analyte_display_name: 'GLUCOSE', unit: 'mg/dL',
    ref_low: 70, ref_high: 99, summary: 'GLUCOSE summary',
    data_points: [point('2025-01-10T00:00:00', 90, verified[0]), point('2025-06-10T00:00:00', 95, verified[1])],
  });

  describe('HC-VER-FE-003: LabInterpreter trend chart marks unverified points (D4)', () => {
    it('shows the note and labels an unverified latest value', () => {
      render(<InterpretedTrendChart trendData={trend([true, false])} interpretation={undefined} isLoading={false} isError={false} />);
      expect(screen.getByTestId('trend-unverified-note')).toHaveTextContent('1 of 2 points on this chart are unverified');
      expect(screen.getByText(/95 mg\/dL \(unverified\)/)).toBeInTheDocument();
    });

    it('shows neither when every point is verified', () => {
      render(<InterpretedTrendChart trendData={trend([true, true])} interpretation={undefined} isLoading={false} isError={false} />);
      expect(screen.getByText('GLUCOSE summary')).toBeInTheDocument(); // positive anchor
      expect(screen.queryByTestId('trend-unverified-note')).not.toBeInTheDocument();
      expect(screen.queryByText(/\(unverified\)/)).not.toBeInTheDocument();
    });
  });
  ```
  Check the `TrendData` fields against `services/types.ts:206-215` and adjust the fixture to match exactly.
- [ ] **Step 2: Watch it fail:**
  ```powershell
  npx vitest run src/__tests__/InterpretedTrendChart.test.tsx; "vitest exit=$LASTEXITCODE"
  ```
  Expected: non-zero exit; test 1 fails with `Unable to find an element by: [data-testid="trend-unverified-note"]`.
- [ ] **Step 3: Implement** in `InterpretedTrendChart.tsx`:
  - Import `TrendPointDot` and `UnverifiedTrendNote`.
  - Add `verified: point.user_verified === true,` to `chartData`.
  - Add `const unverifiedPointCount = chartData.filter((p) => !p.verified).length;` next to `latestPoint`.
  - Badge (main `:79-81`):
    ```tsx
              <Badge variant={latestPoint.is_abnormal ? 'attention' : latestPoint.user_verified === true ? 'verified' : 'caution'}>
                {latestPoint.value} {trendData.unit}
                {latestPoint.user_verified !== true && ' (unverified)'}
              </Badge>
    ```
    An unverified value no longer wears the green "verified" style.
  - `Line` `dot` (main `:163`): the same callback as Task 5, with `radius={4}`.
  - After the chart block closes (main `:169`), add `<UnverifiedTrendNote unverified={unverifiedPointCount} total={chartData.length} />`.
- [ ] **Step 4: Green:** re-run the Step 2 command → `vitest exit=0`. Then `npx tsc --noEmit; "tsc exit=$LASTEXITCODE"` → `tsc exit=0`.
- [ ] **Step 5: Break it on purpose:** set `verified: true` in `chartData`, see red, then restore.
- [ ] **Step 6: Commit:**
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03
  git add src/frontend/src/components/lab-interpreter/InterpretedTrendChart.tsx src/frontend/src/__tests__/InterpretedTrendChart.test.tsx
  git diff --cached --name-only
  git commit -m "feat(lab-interpreter): mark unverified points on the interpreted trend chart (D4)" -- src/frontend/src/components/lab-interpreter/InterpretedTrendChart.tsx src/frontend/src/__tests__/InterpretedTrendChart.test.tsx
  ```

---

### Task 7 (opt-in, O-1): no-LLM knowledge fallback cites verified values only — HC-VER-005

**Run only if O-1 is signed "yes" (§10).** Otherwise skip this task, adjust the Task 8 counts, and list O-1 as open in the PR. Runs **after W-4 has merged** (order P1 → W-4 → W-3 on `api/assistant.py`). Re-anchor with Task 0 Step 5's grep, because W-4's helper shifts the lines.

**Files:**
- Modify: `src/backend/api/assistant.py`, only the `.where(...)` inside `_build_knowledge_fallback._fetch_latest_obs` (`B@7b2ff1f` `:1337-1341`).
- Test: `src/backend/tests/test_verified_only_consumers.py`.

**Interfaces:** consumes `_build_knowledge_fallback(request, profile_id, db, profile_db)` and `ChatRequest(question=...)` (B `:1281-1286`, `:86-88`). No signature change.

- [ ] **Step 1: Failing test.** Append:
  ```python
  @pytest.mark.asyncio
  async def test_hc_ver_005_knowledge_fallback_cites_verified_values_only(real_profile_db) -> None:
      from unittest.mock import MagicMock, patch
      from api.assistant import ChatRequest, _build_knowledge_fallback
      from modules.knowledge_loader import BiomarkerInfo

      db = real_profile_db
      db.add_all([_document("doc-v", "verified"), _document("doc-u", "parsed")])
      db.add_all([
          _ldl("obs-v", "doc-v", 101.0, True, datetime(2025, 1, 10)),
          _ldl("obs-u", "doc-u", 187.0, False, datetime(2025, 6, 10)),
      ])
      await db.commit()
      info = BiomarkerInfo(
          id="kb-ldl", analyte_canonical="ldl_cholesterol", display_name="LDL Cholesterol",
          description="d", clinical_significance="c", normal_interpretation="n",
          high_interpretation="h", low_interpretation="l", standard_unit="mg/dL", category="lipid",
      )
      with patch("modules.knowledge_loader.get_knowledge_loader") as loader_fn:
          loader = MagicMock()
          loader.get_biomarker_knowledge = AsyncMock(return_value=info)
          loader_fn.return_value = loader
          response = await _build_knowledge_fallback(
              request=ChatRequest(question="How is my LDL?"), profile_id=PROFILE,
              db=AsyncMock(), profile_db=db,
          )

      combined = " ".join(s.content for s in response.segments)
      assert "101.0" in combined, "positive control: verified value missing from fallback"
      assert "187.0" not in combined, "unverified value cited by the no-LLM fallback"
  ```
  Check the `BiomarkerInfo` fields against `tests/test_biomarker_assistant.py:62-77` before running.
- [ ] **Step 2: RED:**
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03/src/backend
  ~/venvs/asclexis-311/bin/python -m pytest tests/test_verified_only_consumers.py -p no:cacheprovider -q -k hc_ver_005
  ```
  Expected: `AssertionError: unverified value cited by the no-LLM fallback`. The real query returns the newer unverified row (187.0), and the fallback swallows nothing on this path.
- [ ] **Step 3: Implement.** Change the `.where(...)` in `_fetch_latest_obs` to:
  ```python
                  .where(
                      Observation.profile_id == profile_id,
                      Observation.analyte_canonical == analyte,
                      Observation.value.isnot(None),
                      # D4 (owner, 2026-09-27): the legacy path cites verified
                      # values only, matching the agent's query_observations tool.
                      Observation.user_verified == True,  # noqa: E712
                  )
  ```
- [ ] **Step 4: GREEN,** then run SAFE-09 (the fallback still answers without an LLM):
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03/src/backend
  ~/venvs/asclexis-311/bin/python -m pytest tests/test_verified_only_consumers.py -p no:cacheprovider -q -k hc_ver_005
  ~/venvs/asclexis-311/bin/python -m pytest tests/test_biomarker_assistant.py tests/test_chat_sessions.py -p no:cacheprovider -q -k "fallback"
  ```
  Expected: `1 passed`; the second run has every test named in a `FAILED`/`ERROR` summary line also appears in `/mnt/c/Users/DangT/Documents/GitHub/w03-evidence/failed-start.txt`. That file holds junit ids in dotted form (`tests.test_rag_pipeline::test_name`), so match on the test name. The existing fallback tests use fake sessions (`test_biomarker_assistant.py:404-408`) that ignore `WHERE`, so they stay green and cannot see this filter. That is why HC-VER-005 uses real SQLite.
- [ ] **Step 5: Break it on purpose.** Delete the new line, re-run `-k hc_ver_005`, see red, then restore and see green.
- [ ] **Step 6a: Update the collected count only** (CLAUDE.md rule: the commit that changes collection updates the baseline):
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03/src/backend
  EV=/mnt/c/Users/DangT/Documents/GitHub/w03-evidence
  ~/venvs/asclexis-311/bin/python -m pytest tests/ --collect-only -q -p no:cacheprovider > "$EV/collect-now.txt" 2>&1; echo "collect exit=$?"
  grep -E "[0-9]+ tests? collected" "$EV/collect-now.txt"
  ```
  Write that number into the **collected slots only**: `CLAUDE.md` "Baseline: **N backend tests collected.**" and `AGENT.md` "(N collected;". Leave every pass-count sentence ("all N pass", "N pass in CI, N-1 without an embedding model") unchanged. Flag it in the PR unless you measured a pass count in a named environment.
- [ ] **Step 6b: Commit** (code + test + collected slots):
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03
  git add src/backend/api/assistant.py src/backend/tests/test_verified_only_consumers.py CLAUDE.md AGENT.md
  git diff --cached --name-only    # exactly these 4 paths
  git commit -m "fix(assistant): no-LLM fallback cites verified values only (D4)" -- src/backend/api/assistant.py src/backend/tests/test_verified_only_consumers.py CLAUDE.md AGENT.md
  ```

**What this test would fail to notice:**
- The chat route wiring (`except ModelUnavailableError` → fallback), because it calls the helper directly. The chat route's existing tests cover that wiring, and Task 8 Step 7 item 4 re-walks it.
- Whether the patient understands why their value is missing (O-4).

---

### Task 8: Phase-end measurement, whole-flow re-walk, baseline lines, PR

- [ ] **Step 1: Run the full backend suite** (WSL):
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03/src/backend
  EV=/mnt/c/Users/DangT/Documents/GitHub/w03-evidence
  find . -name __pycache__ -type d -prune -exec rm -rf {} +
  ~/venvs/asclexis-311/bin/python -m pytest tests/ --collect-only -q -p no:cacheprovider > "$EV/collect-end.txt" 2>&1; echo "collect exit=$?"
  grep -E "[0-9]+ tests? collected" "$EV/collect-start.txt" "$EV/collect-end.txt"
  ~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q -rfE --junitxml="$EV/junit-end.xml" > "$EV/pytest-end.txt" 2>&1; echo "pytest exit=$?"
  ~/venvs/asclexis-311/bin/python - "$EV/junit-end.xml" "$EV/failed-end.txt" <<'EOF'
  import sys, xml.etree.ElementTree as ET
  root = ET.parse(sys.argv[1]).getroot()
  ids = sorted(
      f"{tc.get('classname')}::{tc.get('name')}"
      for tc in root.iter("testcase")
      if tc.find("failure") is not None or tc.find("error") is not None
  )
  with open(sys.argv[2], "w") as fh:
      fh.write("".join(i + "\n" for i in ids))
  print(f"failed+errored={len(ids)}")
  print("\n".join(ids))
  EOF
  echo "--- failures present at END but not at START (must be empty):"
  comm -13 "$EV/failed-start.txt" "$EV/failed-end.txt"
  ```
  Acceptance:
  - end collected == start collected + 5 (HC-VER-001…005), minus 1 for each task skipped (Task 3 if O-5 is unsigned; Task 7 unless O-1 is signed "yes");
  - the `comm -13` section prints nothing, so the end failure set ⊆ the start set;
  - paste both full failure lists into the PR.
- [ ] **Step 2: Eval gate identical:**
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03
  EV=/mnt/c/Users/DangT/Documents/GitHub/w03-evidence
  timeout 900 ~/venvs/asclexis-311/bin/python scripts/agent_eval_gate.py > "$EV/w03-eval-end.txt" 2>&1; echo "exit=$?"
  diff "$EV/w03-eval-start.txt" "$EV/w03-eval-end.txt" && echo IDENTICAL
  ```
  Expected: `IDENTICAL`, with the same exit code as Task 0. Any difference means STOP. Never edit the gate, the scorer or the golden files.
- [ ] **Step 3: Contract greps:**
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03
  grep -rnE "user_verified\s*=\s*True" src/backend/api src/backend/modules
  ```
  Expected: exactly 2 hits, `api/documents.py` (`obs.user_verified = True`) and `api/observations.py` (`observation.user_verified = True`). C-VERIFY-1 is unchanged.
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03
  grep -n "user_verified" src/backend/api/observations.py src/backend/modules/rag.py
  ```
  Expected: new hits for the `TrendPoint` field, the `user_verified=obs.user_verified is True` keyword and `Observation.user_verified == True` in `rag.py`.
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03
  grep -n 'Document.status == "verified"' src/backend/modules/rag.py
  ```
  Expected: 2 hits, `:607` plus the Task 3 filter, or 1 if Task 3 was skipped.
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03
  EV=/mnt/c/Users/DangT/Documents/GitHub/w03-evidence
  START=$(cat "$EV/START_SHA")
  git diff "$START"..HEAD --stat -- src/backend/modules/faithfulness.py src/backend/modules/verifier_agent.py src/backend/modules/interpret_safety.py src/backend/modules/redaction.py src/backend/core/auth.py src/backend/modules/agent scripts/agent_eval_gate.py src/backend/tests/agent src/backend/tests/support
  ```
  Expected: empty.
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03
  EV=/mnt/c/Users/DangT/Documents/GitHub/w03-evidence
  START=$(cat "$EV/START_SHA")
  git diff "$START"..HEAD -- src/backend/api/assistant.py | grep -E '^[+-][^+-]'
  ```
  Expected: empty if Task 7 was skipped. If it ran, only the added `user_verified` line and its 2 comment lines.
- [ ] **Step 4: Boot check:**
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03/src/backend
  ~/venvs/asclexis-311/bin/python -c "from main import app"; echo "exit=$?"
  ```
  Expected: `exit=0`.
- [ ] **Step 5: Frontend** (Windows, location from Task 0 Step 7):
  ```powershell
  $EV = 'C:\Users\DangT\Documents\GitHub\w03-evidence'
  Set-Location C:\Users\DangT\Documents\GitHub\hc-w03\src\frontend
  npx tsc --noEmit; "tsc exit=$LASTEXITCODE"
  npx vitest run --reporter=default --reporter=json --outputFile.json="$EV\vitest-end.json"; "vitest exit=$LASTEXITCODE"
  $r = Get-Content "$EV\vitest-end.json" -Raw | ConvertFrom-Json
  "total=$($r.numTotalTests) failed=$($r.numFailedTests)"
  @($r.testResults | ForEach-Object { $_.assertionResults } | Where-Object { $_.status -eq 'failed' } |
    ForEach-Object { $_.fullName } | Sort-Object) | Set-Content "$EV\vitest-end-failed.txt"
  $start = @(Get-Content "$EV\vitest-start-failed.txt")
  "--- failures present at END but not at START (must be empty):"
  @(Get-Content "$EV\vitest-end-failed.txt") | Where-Object { $_ -and ($start -notcontains $_) }
  ```
  Acceptance:
  - `tsc exit=0`;
  - end `total` = start `total` + 8 (3 FE-001, 3 FE-002, 2 FE-003), or + 6 if Task 6 was vetoed;
  - the "failures present at END but not at START" section prints nothing, so the set of failing test names is a subset of `START_VITEST_FAILED`. List every name in both files in the PR.
- [ ] **Step 6: Manual chart check.** This is the dot wiring that jsdom cannot show.
  - On Windows PowerShell: `Set-Location C:\Users\DangT\Documents\GitHub\hc-w03; .\dev.ps1`. `dev.ps1` lives at the worktree root, not in `src\frontend`.
  - Import a lab PDF with at least 2 values for one analyte. Verify one value in the Verification Workbench and leave the other unverified.
  - Open Trends and LabInterpreter.
  - **Both charts:** a hollow dashed dot for the unverified point, a filled dot for the verified one, the shared marker's SVG title "Unverified" when hovering the hollow dot (browser native tooltip), the `trend-unverified-note` text, and the "(unverified)" latest value.
  - **TrendsDashboard only:** the chart tooltip line "Unverified: not yet reviewed" (Task 5). Task 6 adds no tooltip copy to `InterpretedTrendChart`, so do not expect that phrase on LabInterpreter.
  - Save screenshots to `C:\Users\DangT\Documents\GitHub\w03-evidence\screenshots\` and cite their paths in the PR. If this cannot be done, write `UNMEASURED: dot rendering` in the PR.
- [ ] **Step 7: Whole-flow re-walk** (recurring-failures #2). Record the observed result of each step in the PR:
  1. With the agent disabled in model settings, ask the assistant about the unverified analyte. Observe that no unverified value appears in the answer or citations.
  2. Verify the observation. Ask again and observe the value now appears.
  3. Open the LabInterpreter for an unverified observation. Observe and record what the grounded explanation says (O-3 evidence).
  4. With no model installed, and one verified plus one newer unverified value for the analyte, repeat step 1. If Task 7 ran, the no-LLM fallback must show the verified value and not the unverified one. If it did not run, record what it shows and list O-1 as open in the PR.
- [ ] **Step 8: Baseline slots check** (no commit):
  ```bash
  set -o pipefail
  cd /mnt/c/Users/DangT/Documents/GitHub/hc-w03
  grep -n "backend tests collected" CLAUDE.md; grep -n "collected;" AGENT.md
  ```
  - **Collected slots:** both must show the end count from Task 8 Step 1 (`/mnt/c/Users/DangT/Documents/GitHub/w03-evidence/collect-end.txt`). Each backend commit already updated them.
  - **Pass-count sentences** (`CLAUDE.md` "all N pass…", `AGENT.md` "N pass in CI, N-1 without…") were **not** edited. Update them only with a pass count measured in a named environment: interpreter, plus whether an embedding model was present. Otherwise flag them as stale in the PR. Never write a collected number into a pass-count slot.
- [ ] **Step 9: Push and open the PR.** Use the handoff §6 format:
  1. start and end measurements;
  2. each new test with its RED output;
  3. C-VERIFY-2 / SAFE-02 status, stated per path. Report each path with exactly one of the two states in this table. Never write "legacy RAG verified-only" as a blanket claim.

     | Path | State to report |
     |---|---|
     | Trends | `labelled` (Tasks 1, 4, 5; plus 6 unless O-2 veto) |
     | Legacy RAG observations (`modules/rag.py` `_get_observation_chunks`) | `filtered` (Task 2) |
     | Legacy RAG document chunks (`_search_vectors_async`) | `filtered` if Task 3 ran; otherwise `owner-gated (O-5), not filtered` |
     | No-LLM knowledge fallback (`api/assistant.py` `_fetch_latest_obs`) | `filtered` if Task 7 ran; otherwise `owner-gated (O-1), not filtered` |
     | Interpretations question text (`api/interpretations.py:427-432`) | `owner-gated (O-3), not filtered` |

     SAFE-02 may be reported as moving past **partial** only when every row reads `labelled` or `filtered`. Otherwise it stays **partial**, and the PR lists the open owner items;
  4. the full file list;
  5. every owner line from §10 and its state.

  **STOP** for the owner's merge.

## 7. Measured acceptance (summary)

| Check | Command | Expected |
|---|---|---|
| New backend tests RED then GREEN | Tasks 1-3 Steps 2/4 | the RED messages quoted in each task; then `passed` |
| Suite | Task 8 Step 1 | collected = start + 5 (−1 per skipped task); failures ⊆ start |
| Agent golden set unchanged | Task 8 Step 2 | `IDENTICAL` |
| Ask-first / agent / gate files untouched | Task 8 Step 3 last command | empty |
| C-VERIFY-1 unchanged | Task 8 Step 3 first grep | exactly 2 hits |
| App boots | Task 8 Step 4 | exit 0 |
| Frontend | Task 8 Step 5 | tsc clean; vitest start + 8 |
| Dot rendering | Task 8 Step 6 | screenshots, or `UNMEASURED` |
| No-LLM fallback (SAFE-09) still answers | `pytest tests/test_biomarker_assistant.py -k fallback` (+ Task 7 Step 4 if O-1 is signed) | no new failures; HC-VER-005 passes if Task 7 ran |

Not measured by this plan (**UNMEASURED**):
- Recharts dot rendering in jsdom. Measure it by the manual check in Task 8 Step 6, or with a Playwright assertion on `[data-verified="false"]` once `HC_E2E_CHROMIUM_PATH` is set (recurring-failures #4).
- Whether the eval gate's post-PASS hang (§3.9) reproduces under 3.11. Task 0 Step 6 measures it.

## 8. Stop gates

Stop and ask the owner when:
1. Any step needs an edit to an ask-first file, `modules/agent/**`, `scripts/agent_eval_gate.py`, golden files, or `tests/support/routes.py`.
2. Task 3 is reached and O-5 is unsigned. Or Task 7 is reached and O-1 is not signed "yes" (skip it, do not ask twice). Or Task 7 is reached and W-4 has not merged; never edit `api/assistant.py` concurrently with W-4.
3. An existing test goes red after Task 2 or 3. Classify it first (§6 Task 2 Step 6). Never change an assertion to make it pass without the owner's knowledge in the PR.
4. The eval-gate outputs differ (Task 8 Step 2).
5. P5, W-10, W-4 or W-5 has not landed (W-4 for `api/assistant.py`; W-5 for `modules/rag.py`); or `modules/rag.py`, `api/observations.py`, `api/assistant.py`, `CLAUDE.md` or `AGENT.md` is being edited by another phase.
6. A line anchor from Task 0 Step 5 does not match the code this plan describes (the code moved).
7. Any failure not explained by this plan's own change.
8. Anything needs a threshold changed.

## 9. Rollback

- **Before merge** (PR open): close it and delete the remote branch with `gh pr close feat/w03-verified-only-rag --delete-branch`. Then remove the worktree: `git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral worktree remove /mnt/c/Users/DangT/Documents/GitHub/hc-w03`.
- **After merge:** on a new branch from `origin/main`, `git revert` the W-3 commits in reverse order (Task 7 if it ran, then 6, 5, 4, 3 if it ran, 2, 1). Open a PR; the owner merges.
- Reverting Task 7 alone (if it ran) restores the unfiltered no-LLM fallback. It touches only the one `WHERE` line, so it does not conflict with W-4's helper.
- There is no schema, migration or data change, so nothing to unwind in any vault.
- Reverting Task 2/3 restores unverified values to legacy RAG (the pre-D4 state). Reverting Task 1 removes a JSON field. The frontend treats a missing field as unverified, so a backend-only revert makes the charts over-label, never under-label. Revert the frontend commits with it.

## 10. Owner sign-offs (unsigned)

| # | Question | Default in this plan | Sign-off |
|---|---|---|---|
| O-5 | Chunks have no verification state. Apply the agent's R-5 rule (`Document.status == "verified"`) to legacy vector retrieval? Effect: documents with zero observations (visit notes, imaging, pathology) are unreachable by legacy chat, because the UI cannot verify them (`VerificationWorkbench.tsx:523-527`). A verify affordance for them would be a separate, new feature. | Task 3 **blocked** until signed | `O-5 approved: ____________ (owner, date)` |
| O-1 | The no-LLM knowledge fallback cites the latest observation with `[cite:N]`, unfiltered (`B@7b2ff1f` `api/assistant.py:1329-1347`). Does D4's "legacy RAG" include it? The case for yes is in §3.7(a). Canonical gate **VERIFIED-FALLBACK** (owner-gated): decided together with W-8 Q-FC (legacy-chat row), because W-8's fail-closed default routes legacy chat to this fallback; proposed default O-1 = yes, signed before W-8 merges. | Task 7 **skipped** unless signed "yes" (opt-in) | `O-1 yes/no: ____________ (owner, date)` |
| O-2 | Does D4's trend marking cover the LabInterpreter chart (`InterpretedTrendChart.tsx`), which plots the same endpoint? | Task 6 **runs** (marking is what D4 licenses) | `O-2 veto (skip Task 6): ____________` |
| O-3 | The interpretations route puts the observation's own value into the question (`api/interpretations.py:427-432`). For an unverified observation, the value still reaches the model; after W-3 the context holds only *other*, verified values. Leave it, or route a fix through W-7 (it sits beside `interpret_safety.py`)? Program owner item **INTERP-UNVERIFIED** (no W-7 gate covers it). | no change here | `O-3 decision: ____________` |
| O-4 | With only unverified data, legacy chat now answers "I don't have enough information… Please make sure you have uploaded relevant documents." (`modules/rag.py:1236-1245`). That misleads a patient whose document *is* uploaded but unverified. Should W-4 reword it? Program owner item **MSG-UNVERIFIED**: W-4 licenses no new wording and has no gate for it, so new wording needs its own licence. | no change here | `O-4 decision: ____________` |
| Merge | W-3 PR | — | `Merged by owner: ____________` |

## 11. For the docs owners (reference only; not edited here)

- **W-10** (`docs/compliance/data-privacy.md`) should state:
  - trends display unverified values, marked "Unverified";
  - legacy RAG, like the agent, uses verified observations only, plus verified-document chunks if O-5 is signed, and the no-LLM fallback if O-1 is signed;
  - the O-3 residue: the interpretations question text.
- **P4** (`docs/architecture/pipelines.md:53-56`): "Downstream surfaces consume the *verified* set" becomes true for legacy RAG. Trends is the second labelled exception, beside the timeline.
- **Capstone package:** the contract's C-VERIFY-2 class and matrix row SAFE-02 are updated by whoever owns those files, from this PR's per-path status table (Task 8 Step 9). SAFE-02 stays partial while any path is owner-gated and not filtered. This plan does not edit them.

## 12. Recurring-failures recheck

| # | Applies | Concrete recheck in this plan |
|---|---|---|
| 1 Green suite that could not fail | **yes** | Real SQLite for every retrieval test. Positive controls because of the swallowed exceptions. HTTP for the trends test. Anchor before the negative vitest assertions. A break-it step in every task |
| 2 Fix creates the next bug | **yes** | Task 8 Step 7 whole-flow re-walk, including the no-model chat. Other callers listed in §3.6 (interpretations, chat, eval scorer). The fallback found by the W-4 author is Task 7, opt-in (O-1). `is_user_verified` and "(User-verified result)" become constant. O-4 message |
| 3 Asserted figures | yes | Every count comes from Task 0 / Task 8 commands. The "74 cases" and the Windows hang are dated and scoped |
| 4 Environment-dependent | yes | Stub embedder, so no model is needed. Vitest runs on Windows only. The eval-gate hang is recorded per interpreter |
| 5 Contaminated tree | yes | Dedicated worktree. Explicit pathspecs. `git commit -m … -- ` followed by each commit block's explicit path list |
| 6 Documented commands nobody ran | yes | Run each command exactly as written in this plan. Fix the plan if one is wrong, rather than improvising |
| 7 SQL three-valued logic | checked | Both filters are equalities on `nullable=False` columns (`models/observation.py:79`, `models/document.py:57`). NULL rows cannot slip in |
| 8 Stale guidance | yes | `pipelines.md:53-56` is stale until P4. R-5 is an archived doc, re-checked against `retrieve_chunks.py:73` |

Back to: [implementation program](../capstone-report/implementation-program.md) · [owner decisions](../capstone-report/owner-decisions-2026-09-27.md) · [handoff](../../audit/2026-09-25/handoff-2026-09-27-execution.md) · [recurring failures](../agentic/recurring-failures.md)
