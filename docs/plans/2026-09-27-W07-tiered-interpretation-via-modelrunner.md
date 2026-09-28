# W-7 Tiered Interpretation via ModelRunner Implementation Plan

**Last Updated:** 2026-09-27
**Owner:** repository owner
**Refresh Trigger:** P1 merged (branch B's `modules/model_selector.py` lands on main), P5 or P7 merged (shared files below), or any change to `core/model_runner.py`, `core/llm/`, `modules/interpret.py` or `api/interpretations.py` before this plan starts
**Status:** PROPOSED — not executed
Post-review consistency edit 2026-09-27 (baseline-sentence rule); not re-reviewed.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the dormant tiered-interpretation path (`InterpretModule.interpret_with_model`) so it drafts through the `ModelRunner` facade instead of loading `llama_cpp` itself, delete the `from llama_cpp import Llama` in `modules/model_selector.py`, expose the path on one new authenticated, audited route, and add an automated import-boundary test.

**Architecture:** `ModelRunner` has no notion of tiers. It exposes `is_available()`, `generate(prompt, config)`, `generate_async(prompt, config)` and `unload()` over one process-wide provider chosen by `settings.llm_provider` / `settings.llm_model` (`core/model_runner.py:55-229`, `core/llm/factory.py:25-75`, main@40f590e). This plan does **not** add a tier layer on top of it (CLAUDE.md §2). The tier stays what `ModelSelector.get_active_tier` already computes (user preference, else hardware recommendation). It now decides one thing: `template` skips the LLM, and any other tier asks `ModelRunner` for a draft. `ModelSelector`'s own model loading and inference (`load_model`, `load_model_async`, `get_model_for_inference`, `run_inference`) are **deleted, not rewritten**. Rewriting `run_inference` to call `ModelRunner` would make `ModelSelector` a second facade over the facade. A draft that fails, times out, lacks citations, or trips an `interpret_safety` prohibited pattern is replaced by the existing template interpretation. The new route is `POST /api/v1/interpretations/observations/{observation_id}/interpret-tiered`.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy async (per-profile vault via `ProfileDbSession`), pytest + pytest-asyncio + aiosqlite, `tests/support/routes.py::route_client`, `ast` (stdlib) for the boundary scanner.

**Spec:** handoff §5 row W-7 in [handoff-2026-09-27-execution.md](../../audit/2026-09-25/handoff-2026-09-27-execution.md); owner decision D7 in [owner-decisions-2026-09-27.md](../capstone-report/owner-decisions-2026-09-27.md); rules in [architecture-engineering-contract.md](../capstone-report/architecture-engineering-contract.md); rows in [specs-compliance-matrix.md](../capstone-report/specs-compliance-matrix.md); sequencing in [implementation-program.md](../capstone-report/implementation-program.md).

---

## Approval scope

**Owner's choice, D7, recorded 2026-09-27, verbatim:**

> "Keep the tiered-interpretation feature but rewrite it to call ModelRunner, then wire it to a route. New feature work."

The record marks it **not** the recommendation ("delete" was recommended). Consequence #3 of the same record, verbatim:

> "**D7 creates feature work beside a safety module.** Rewriting tiered interpretation onto ModelRunner and wiring it to a route touches `modules/interpret.py`, which calls `modules/interpret_safety.py`. The safety module stays read-only unless the owner separately approves an edit to it."

**This plan does:**
1. Rewrite `interpret_with_model` and its helper `_llm_interpretation` to call `ModelRunner.generate_async`.
2. Remove the `llama_cpp` import and the inference methods from `ModelSelector`.
3. Add one new route that calls `interpret_with_model`.
4. Add tests.
5. Update the measured baseline lines in `CLAUDE.md`/`AGENT.md`, which CLAUDE.md §4 requires whenever the collected count changes.

**Does NOT license** (each item is owner-gated; the sign-off lines at the end are unsigned):
- Any edit to `modules/interpret_safety.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`, `modules/redaction.py`, `core/auth.py`, `core/audit.py`, or anything encryption-related. The plan only **calls** `InterpretationSafetyGuard.validate_interpretation`, `check_critical_value` and `add_required_disclaimers`.
- Per-tier model weights, meaning loading the selected tier's GGUF for the request. That needs a change inside `core/llm/`, a second resident model or a provider swap per request. It is a different feature (OG-1).
- Any change to `core/model_runner.py`, `core/llm/*`, `core/external_runner.py` (W-6), or the `LLM_INTERPRETATION_PROMPT` text.
- Switching the existing `/interpret`, `/interpret-grounded`, `/panels/.../interpret` or `/batch` routes to the tiered path (OG-2).
- Any frontend change (service function, hook, page, button). D7 says "wire it to a route", not "build UI" (OG-2).
- Routing tiered interpretation through the opt-in `ExternalModelRunner`. The tiered route uses the local `ModelRunner` only, so no text leaves the device and `redaction.py` is not on this path.
- Adding audit rows to the other interpretation routes (finding F-3 below; OG-3).
- Extending the boundary test to `httpx`/`ollama`/HTTP clients. That is the remainder of C-LLM-2, tied to D12/W-6.
- Any `.github/workflows/ci.yml` edit. The boundary test runs inside the existing `backend-tests` job (Task 1, Step 6).
- Deleting other `ModelSelector` behaviour: tier config, downloads, `get_fallback_chain`, `get_tier_capabilities`.

## Traceability

| Kind | ID | Verified text (grep, 2026-09-27) |
|---|---|---|
| Contract | C-LLM-1 · BINDING (`architecture-engineering-contract.md:206`) | "All LLM calls MUST go through the `ModelRunner` facade (`CLAUDE.md:25`). Feature code MUST NOT import `llama_cpp` or call Ollama directly. New providers are added inside `core/llm/`, never as a layer on top of it." |
| Contract | C-LLM-2 · PROPOSED (`:216`) | "An automated boundary check … MUST fail on a new `llama_cpp`/`ollama`/HTTP-client import outside `core/llm/`" (this plan implements the `llama_cpp` part) |
| Contract | C-LLM-3 · BINDING (`:223`) | "The no-LLM fallback MUST keep answering (knowledge fallback) when no model is available." |
| Contract | C-SAFE-1 · BINDING (`:131`) | "`interpret_safety` prohibited patterns MUST keep passing. `interpret_safety.py` … MUST NOT change without owner approval." |
| Contract | C-AUDIT-1 · BINDING (`:323`) | "Every route that touches documents, observations or profile data MUST write an audit row via `core/audit.py` … without PHI." |
| Contract | C-ISO-1 / C-ISO-2 · BINDING (`:60`, `:68`) | profile data only via `ProfileDbSession`; auth/scoping/status tests go through HTTP (`route_client`) |
| Matrix | LLM-02 (`specs-compliance-matrix.md:98`) | "No `llama_cpp` import in feature code … **dormant violation** at `modules/model_selector.py:438` … **partial**" |
| Matrix | LLM-03 (`:99`) | "The boundary is checked automatically … **gap**" |
| Matrix | LLM-01 (`:97`) | "Live local inference goes through `ModelRunner`" (the new route must keep this true) |
| Matrix | SAFE-05 (`:74`), AUD-01 (`:105`), ISO-01 (`:49`) | prohibited patterns; audited observation routes; `ProfileDbSession` only |
| Handoff | §5 row W-7 | "Rewrite tiered interpretation (`modules/interpret.py:877` `interpret_with_model`, `model_selector.run_inference`) to call ModelRunner, then wire it to a route. Remove the `from llama_cpp import` at `modules/model_selector.py:438`. `interpret_safety.py` stays read-only" |
| Program | G-B3 | "Inference-boundary check; resolve the dormant `model_selector` path (LLM-02/03)" · acceptance "The boundary test fails on a seeded `import llama_cpp` in `modules/`" |

**Expected matrix status changes.** The PR body reports them; this plan does not edit the matrix (see Shared files):
- LLM-02: partial → **tested**. HC-LLMB-001 is collected by CI `backend-tests` (B `ci.yml:51`, `bash scripts/run-backend-tests.sh -q`; no `continue-on-error` or `|| true` on B), so a violation fails that job.
  - This plan still proposes `tested`, not `enforced`: the matrix rates the backend suite itself `tested` (GATE-02, `specs-compliance-matrix.md:136`).
  - Whether `backend-tests` is green on main and a required merge check is UNMEASURED. Measure it with `gh run list --branch main --workflow ci.yml --limit 5` and the branch-protection settings.
  - Promotion to `enforced` is the matrix owner's call.
- LLM-03: gap → **partial** (`llama_cpp` only; HTTP clients are still unchecked).

## Code facts this plan relies on (re-verify on the post-P1/P5/P7 tree)

Line numbers are labelled by ref. **The executor must re-run every grep on the START tree**; P1, P5 and P7 all shift lines.

| Fact | Evidence |
|---|---|
| Only 2 `llama_cpp` import sites in the whole tree on B | `git grep -nE "(^\|\s)(import llama_cpp\|from llama_cpp)\|importlib.*llama_cpp\|__import__\(.llama" origin/claude/healthcentral-agentic-research-r1n54x -- .` → `src/backend/core/llm/llama_cpp_provider.py:36` and `src/backend/modules/model_selector.py:456`. No test file imports `llama_cpp`. Branch A does not touch either file |
| The handoff's `:438` is main-relative | main@40f590e `modules/model_selector.py:438`; **B@7b2ff1f `:456`**. B's commit `3eb9e9d` added 18 comment/config lines above it |
| Chain to the import | B@7b2ff1f `model_selector.py`: `load_model` `:437-478` (import at `:456`) ← `load_model_async` `:480-504` ← `get_model_for_inference` `:506-536` ← `InterpretModule.interpret_with_model` (main@40f590e `modules/interpret.py:903`). `run_inference` `:538-570` ← `interpret.py:761`. `interpret_with_model` has **0 callers** (`git grep -n interpret_with_model` on B → definition only) |
| Selector state used only by the deleted methods | B@7b2ff1f `:206-211` (`_loaded_model`, `_current_tier`, `_load_lock`). `asyncio` is still used at `:701` |
| `interpret.py`, `core/model_runner.py`, `core/llm/*`, `api/interpretations.py`, `modules/interpret_safety.py`, `tests/support/routes.py` | unchanged on A and B (`git diff --stat origin/main <branch> -- …` empty) |
| ModelRunner async API | main@40f590e `core/model_runner.py:174-221`: `generate_async(prompt: str, config: Optional[InferenceConfig]) -> InferenceResult`. Provider failure → `RuntimeError`. Timeout → `InferenceResult(finish_reason="timeout", text="I apologize…")`. `InferenceConfig` fields: `max_tokens, temperature, top_p, stop_sequences, timeout_seconds` (`:31-38`) |
| Lazy `llama_cpp` | `core/llm/llama_cpp_provider.py:32-38` (`_load_llama_class`, called only at `:129` inside `_ensure_initialized`). This plan does not touch it |
| `InferenceResult.model_name` can be a full local path | `core/llm/llama_cpp_provider.py` `generate()`: `model_name = self._model_path or self._settings.default_chat_model`, which may be a Windows path containing the OS user name. The plan stores the basename only |
| Safety guard API (read-only) | main@40f590e `modules/interpret_safety.py:101` `validate_interpretation(interpretation_text, advice_text=None, require_citations=True) -> SafetyValidationResult`. Prohibited hits are appended as `f"prohibited_{violation_type}"` at `:127`. `add_required_disclaimers` is at `:247`. **`passed` is also False for `missing_disclaimers` (`:143-144`), which the template triggers before disclaimers are added. So the gate keys on `prohibited_*`, not on `passed`.** |
| Unique constraint | `models/interpretation.py:50-54`: `LabInterpretation.observation_id` is `unique=True`. The current `interpret_with_model` never checks for an existing row when `force_regenerate=False` (`interpret.py:999-1008`), so once wired it would 500 on the second call (IntegrityError). Fixed in Task 2 |
| Mislabelled provenance today | `interpret.py:783-785` silently falls back to the template, but `:1019-1021` still records `model_tier=active_tier` and the tier's description as `model_id`. Fixed in Task 2 |
| Existing interpretation routes | `api/interpretations.py` (main@40f590e) is mounted at `/api/v1/interpretations` (`api/__init__.py:42`, `main.py:150`). Auth pattern: `session: RequireAuth` + `profile_db: ProfileDbSession` + observation-ownership 404/403 (`:328-362`). There are **0 audit calls in the file** |
| Why not `require_profile_access()` | `core/auth.py:251-289` reads `request.path_params["profile_id"]`. This route has only `observation_id`, so the guard would 400 every request, exactly as recurring-failures #1 records for the restore endpoint. The profile id comes from the JWT (`session.profile_id`, C-ISO-1) |
| Audit helper (B) | B@7b2ff1f `core/audit.py`: `log_observation_event(db, event, profile_id, observation_id, analyte, details)` `:338-365` (`analyte` is never persisted). `audit_and_commit(db, log_fn, **kw)` `:474-487` is fail-closed. Allowed detail keys include `action` (`:70`) and `llm_assist` (`:102`). Precedent: `api/observations.py:332-340` uses `event="view", details={"action": "list", …}`. **No `core/audit.py` edit is needed** |
| `route_client` | main@40f590e `tests/support/routes.py:26-58`: `route_client(router, prefix, profile_id="profile-a", master_db=None)`. It overrides `require_auth` and `get_db` only, **not** `get_profile_db_session`. Tests add that override on `client.app.dependency_overrides`. P7 owns this file and may change the signature, so re-read it at start |
| CI runs the new tests without a ci.yml edit | B@7b2ff1f `.github/workflows/ci.yml:51` runs `bash scripts/run-backend-tests.sh -q`, which runs `python3 -m pytest -q` from `src/backend` (`scripts/run-backend-tests.sh`). There is no `testpaths` in `src/backend/pyproject.toml`, so every `tests/test_*.py` is collected |

## Findings for the orchestrator (not fixed here)

- **F-1 (stale line):** handoff §5 W-7 and matrix LLM-02 cite `model_selector.py:438`. After P1 the import is at `:456` (B@7b2ff1f). Plan 05 Task 11 cites main-relative `model_selector.py` utcnow sites (`:266,:273,…`). On B they are +18 (`:284,:291,…`), so plan 05's line list is stale after P1.
- **F-2 (spec command gap):** the acceptance grep `grep -rnE "from llama_cpp" src/backend | grep -v tests` misses the `import llama_cpp` form. It also scans `__pycache__` without `--include=*.py`. Task 4 runs it verbatim **and** a stricter form.
- **F-3 (C-AUDIT-1 gap outside the matrix):** `api/interpretations.py` has 7 routes and 0 audit calls (main@40f590e; `grep -c audit` → 0). 6 of the 7 read or write observation-derived profile data. Matrix AUD-01 counts only `documents` and `observations` routes. Out of D7 scope → OG-3.
- **F-4 (ID prefix):** `HC-INT` is a substring of the existing `HC_INTERP_*` tests (5 hits in `tests/test_interpret_history_units.py` on main, A and B). `HC-INT-0NN` itself has 0 hits. Select these tests with `-k "HC_INT_0"`, never `-k HC_INT`.
- **F-5 (latent bugs in dormant code that wiring would make live):** the unique-constraint 500 and the template-labelled-as-LLM provenance described above. Task 2 fixes both; tests HC-INT-012/016 pin them.

## Global Constraints

- Python **3.11** target; no 3.12+ syntax. Phase-gate interpreter: `$HOME/venvs/asclexis-311/bin/python` (D9). If it does not exist, STOP.
- **Shell preamble.** Shell state does not persist between tool calls, so every command block and every inline `Run:` starts with
  `WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w07; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail`.
  - `WT` is the worktree created in Task 0 Step 1.
  - Every `cd` is absolute (`cd "$WT/src/backend"`); never a relative `cd` after an earlier one.
  - `pipefail` makes a pipe fail when its first command fails. Where only the tail of the output is recorded, the exit code is recorded too (`; echo "exit=$?"`).
- `core.time.utcnow` for any new timestamp. This plan adds none. Do not revert P5's `utcnow` swaps in `model_selector.py` or `api/interpretations.py`.
- All LLM calls go through `ModelRunner` (C-LLM-1). `llama-cpp-python` stays optional: the only import stays lazy inside `core/llm/llama_cpp_provider.py`.
- Local-first: no network call is added. The tiered route never calls `get_runner_for_request`.
- Per-profile isolation: observations and interpretations are read and written only via `ProfileDbSession`. Audit rows go to the master DB via `get_db()` with ids, counts, enums and booleans only (AUDIT-PHI-001).
- No medical advice: a draft that trips any `prohibited_*` check is never stored or served. Disclaimers come from `add_required_disclaimers`.
- Never lower a threshold or weaken a guard to make a test pass.
- Route, auth and status tests go through HTTP with `route_client`. Each safety test gets a break-it-on-purpose step.
- WSL: clear bytecode before pytest (`find src/backend -name __pycache__ -type d -prune -exec rm -rf {} +`, run inside the worktree only).
- Test IDs: `HC-INT-001…005` (route, HTTP), `HC-INT-011…017` (module), `HC-LLMB-001/001b/001c/002` (boundary). Functions are named `test_HC_INT_0NN_*` / `test_HC_LLMB_0NN_*`.

## Review Focus

Five conditions the spec implies that a patient or operator could hit, most likely first, each pinned by a test in the owning task:

1. **The configured local model is not the selected tier's model** (e.g. tier `gemma4-12b` preferred, provider loaded a Qwen 0.5B GGUF). The record must not claim otherwise: `model_tier` = the selected tier, `model_id` = the model that actually answered, basename only. Pinned by HC-INT-011.
2. **LLM text with ordinary wording that trips a prohibited pattern** ("certain", "you have …", "go to the ER") → the patient gets the template text, never the draft. Pinned by HC-INT-013 (3 pattern families) and HC-INT-003 over HTTP.
3. **Calling the route twice for the same observation** (double-click, retry) → the stored interpretation is returned, not a 500 from the unique constraint. Pinned by HC-INT-016. Regenerating with `force_regenerate=true` replaces it cleanly: HC-INT-017.
4. **No model installed, or the model hangs** → 201 with the template, labelled `template`/`template-v1`. The apology text from a timeout is never served. Pinned by HC-INT-012, HC-INT-014 and HC-INT-002 over HTTP.
5. **Spill-over into the existing UI.** One interpretation row per observation, so after a tiered call the existing `/interpret` and `GET /interpretation` routes (used by `LabInterpreter`) return the tiered row. The row is safety-checked and carries honest `model_tier`/`model_id`. This is a behaviour the owner should know about (OG-2). Pinned by HC-INT-016 (returns existing) and re-walked in Task 4 Step 5.

Known, not tested: on its first call per process, `get_active_tier` may run synchronous hardware detection (`modules/hardware_detection.py:76` `subprocess.run(["nvidia-smi", …])`) on the event loop. This is existing behaviour shared with `GET /model-settings`; the plan does not change it.

## Owned files

| Action | Path | Responsibility |
|---|---|---|
| Modify | `src/backend/modules/interpret.py` | `InterpretModule.__init__` gains `model_runner`; `_llm_interpretation` and `interpret_with_model` rewritten; new `_template_draft`, `_model_label` |
| Modify | `src/backend/modules/model_selector.py` | delete `load_model`, `load_model_async`, `get_model_for_inference`, `run_inference` and their state; fix 2 docstrings |
| Modify | `src/backend/api/interpretations.py` | new route `generate_tiered_interpretation` + 2 imports |
| Create | `src/backend/tests/test_llm_import_boundary.py` | HC-LLMB-001/001b/001c/002 |
| Create | `src/backend/tests/test_interpret_tiered.py` | HC-INT-011…017 (module), HC-INT-001…005 (route) |
| Modify | `CLAUDE.md`, `AGENT.md` | the backend baseline numbers only, inside C1 and C2 (CLAUDE.md §4 same-commit rule) |

**Read-only (ask-first; STOP if an edit seems needed):** `src/backend/modules/interpret_safety.py`, `modules/redaction.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`, `src/backend/core/auth.py`, `src/backend/core/audit.py`, `src/backend/core/model_runner.py`, `src/backend/core/llm/*`, `src/backend/core/external_runner.py`, `src/backend/tests/support/routes.py`, `.github/workflows/ci.yml`, `src/frontend/**`.

## Shared files and ordering

| Shared file | Other owners | Order |
|---|---|---|
| `src/backend/modules/model_selector.py` | P1 (brings B's version), P5 plan 05 Task 11 (utcnow) | P1 → P5 → **W-7** |
| `src/backend/api/interpretations.py` | P5 plan 05 Task 3 (`:559` utcnow); possibly W-4 (legacy abstention, if it reaches `/interpret-grounded`) and W-6 (`get_runner_for_request` use at main@40f590e `:436-440`) | P5 → **W-7**; W-4/W-6 never concurrently. The second to land rebases, and its plan re-reads this file |
| `src/backend/tests/support/routes.py` | P7, then G-B1 (edit) | W-7 only **reads** it; run after P7 and re-read the signature |
| `CLAUDE.md`, `AGENT.md` baseline lines | P1, P2, P4, P5, W-10 governance commit, every PRODUCT phase | never concurrent; each writes its own measured count |
| `.github/workflows/ci.yml` | P1 → P5 → G-B3/G-B4 (W-11a) | **W-7 does not edit it.** If the owner later wants a dedicated boundary job, it goes after P5 and before W-11a, in its own plan |
| `src/backend/tests/test_llm_import_boundary.py` (new) | W-6 may extend it to HTTP clients with an `external_runner` allowance (C-LLM-2 remainder, D12) | **W-7** creates it → W-6 extends it |
| `docs/capstone-report/specs-compliance-matrix.md`, `architecture-engineering-contract.md` | many W-plans | **not edited here.** The PR body lists the LLM-02/03 status changes for the serialized docs pass |

## Dependencies

- **P1** (hard): the plan targets B's `model_selector.py`. STOP if `git grep -n "def get_tier_capabilities" -- src/backend/modules/model_selector.py` is empty on the start tree.
- **P5** (program edge P5 → G-B; shares `model_selector.py` and `api/interpretations.py`).
- **P7** (program edge P7 → G-B; P7 may change `route_client`).
- **D7** (approved, scope above). **D9** (3.11 venv). **D12** is not needed for W-7. It governs the external-runner half of G-B3 (W-6).

---

### Task 0: Phase-start measurement (no code, no commit)

**Files:** none modified.

- [ ] **Step 1: Create a clean worktree on the post-P1/P5/P7 main and prove P1 ancestry**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w07; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
REPO=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral
git -C "$REPO" fetch origin
git -C "$REPO" worktree add "$WT" -b feat/w07-tiered-interpretation-modelrunner origin/main
git -C "$WT" log --oneline -1
git -C "$WT" merge-base --is-ancestor 7b2ff1f HEAD && git -C "$WT" merge-base --is-ancestor 692fdf3 HEAD && echo "P1 ancestry OK"
```
Expected:
- `git log` prints the tip of `origin/main` with P1, P5 and P7 merged. Record the SHA.
- The last line prints `P1 ancestry OK`, meaning branch B tip `7b2ff1f` and branch A tip `692fdf3` are both ancestors of HEAD.

If `P1 ancestry OK` is missing, one of the two `merge-base` calls exited 1: STOP (Stop gate 1).

- [ ] **Step 2: Confirm the prerequisites are on this tree**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w07; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
git -C "$WT" grep -n "def get_tier_capabilities" -- src/backend/modules/model_selector.py
git -C "$WT" grep -nE "(^|\s)(import llama_cpp|from llama_cpp)|importlib.*llama_cpp|__import__\(.llama" -- .
git -C "$WT" grep -n "interpret_with_model\|run_inference\|get_model_for_inference\|load_model_async\|\.load_model(" -- src/backend
sed -n '/^def route_client/,/^    """/p' "$WT/src/backend/tests/support/routes.py"
git -C "$WT" grep -c "audit" -- src/backend/api/interpretations.py; echo "exit=$?"
```
Expected:
1. `get_tier_capabilities` is found.
2. Exactly 2 import sites: `core/llm/llama_cpp_provider.py` and `modules/model_selector.py` (≈`:456`).
3. The only callers are in `modules/interpret.py` and `model_selector.py`, with **no test file**.
4. `route_client(router, prefix, profile_id=..., master_db=...)`.
5. No audit lines. `git grep -c` prints nothing and `exit=1` when there are 0 matches.

STOP if any of these differ (Stop gates 1–3).

- [ ] **Step 3: Confirm no test-ID collision**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w07; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
git -C "$WT" grep -niE "HC[-_]INT[-_]0|HC[-_]LLMB" -- src/backend/tests; echo "exit=$?"
```
Expected: no output and `exit=1` (git grep's "no match"). (`HC_INTERP_*` exists; do not select with `-k HC_INT`.)

- [ ] **Step 4: Measure collection and the full run**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w07; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT/src/backend"
find "$WT/src/backend" -name __pycache__ -type d -prune -exec rm -rf {} +
"$PY" --version
"$PY" -m pytest tests/ -p no:cacheprovider -q --collect-only > "$WT/../w07-start-collect.txt" 2>&1; echo "collect exit=$?"; tail -1 "$WT/../w07-start-collect.txt"
"$PY" -m pytest tests/ -p no:cacheprovider -q -rfE > "$WT/../w07-start-run.txt" 2>&1; echo "run exit=$?"; grep -E "^(FAILED|ERROR) " "$WT/../w07-start-run.txt"; tail -1 "$WT/../w07-start-run.txt"
"$PY" -c "from main import app; import sys; print('llama_cpp loaded:', 'llama_cpp' in sys.modules)"
"$PY" -c "import importlib.util as u; print('llama_cpp installed:', u.find_spec('llama_cpp') is not None)"
```
The two result files sit beside the worktree, outside any repo tree.
Record in the PR draft: interpreter version, SHA, `START_COLLECTED`, the list of failing test node ids (`START_FAILURES`), the boot line, and whether `llama_cpp` is installed. Expected boot line: `llama_cpp loaded: False`. STOP if the boot fails (Stop gate 4).

---

### Task 1: Import-boundary test (HC-LLMB) — RED

**Files:**
- Create: `src/backend/tests/test_llm_import_boundary.py`

**Interfaces:**
- Produces: `_python_files(root: Path) -> list[Path]`, `_banned_imports(path: Path) -> list[tuple[int, str]]`, `_violations(root: Path, allowed: Path) -> list[str]` (test-local helpers; W-6 may extend `BANNED_TOP_LEVEL`).

- [ ] **Step 1: Write the test file**

```python
"""C-LLM-1 / C-LLM-2 import boundary (HC-LLMB-NNN).

Feature code must reach local inference only through core.model_runner.ModelRunner.
The only module allowed to import llama_cpp is the provider layer, core/llm/.
Scans with ast (not grep), so comments and strings cannot false-positive, and
self-tests the scanner so a wrong root or a missed import form cannot make the
boundary test pass vacuously (recurring-failures #1).
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROVIDER_LAYER = BACKEND_ROOT / "core" / "llm"
BANNED_TOP_LEVEL = frozenset({"llama_cpp"})
SKIP_DIRS = frozenset({"tests", "__pycache__", ".venv", "venv", "node_modules"})
DYNAMIC_IMPORTERS = frozenset({"import_module", "__import__"})


def _python_files(root: Path) -> list[Path]:
    return sorted(
        p for p in root.rglob("*.py")
        if not SKIP_DIRS.intersection(p.relative_to(root).parts)
    )


def _is_banned(module: str | None) -> bool:
    return bool(module) and module.split(".")[0] in BANNED_TOP_LEVEL


def _banned_imports(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    hits: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            hits.extend((node.lineno, a.name) for a in node.names if _is_banned(a.name))
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and _is_banned(node.module):
                hits.append((node.lineno, node.module))
        elif isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
            if (
                name in DYNAMIC_IMPORTERS
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
                and _is_banned(node.args[0].value)
            ):
                hits.append((node.lineno, node.args[0].value))
    return hits


def _violations(root: Path, allowed: Path) -> list[str]:
    found: list[str] = []
    for path in _python_files(root):
        if allowed == path.parent or allowed in path.parents:
            continue
        for lineno, module in _banned_imports(path):
            found.append(f"{path.relative_to(root).as_posix()}:{lineno} imports {module}")
    return found


def test_HC_LLMB_001_no_llama_cpp_import_outside_provider_layer():
    scanned = _python_files(BACKEND_ROOT)
    assert len(scanned) > 100, f"scanner walked {len(scanned)} files; wrong root?"
    violations = _violations(BACKEND_ROOT, PROVIDER_LAYER)
    assert violations == [], (
        "llama_cpp may only be imported inside core/llm/ (C-LLM-1); "
        "call core.model_runner.ModelRunner instead:\n" + "\n".join(violations)
    )


@pytest.mark.parametrize(
    "source",
    [
        "from llama_cpp import Llama\n",
        "import llama_cpp\n",
        "import llama_cpp.llama as backend\n",
        "import importlib\nm = importlib.import_module('llama_cpp')\n",
    ],
)
def test_HC_LLMB_001b_scanner_catches_each_import_form(tmp_path, source):
    feature = tmp_path / "modules" / "seeded.py"
    feature.parent.mkdir()
    feature.write_text("def f():\n    pass\n" + source, encoding="utf-8")
    allowed = tmp_path / "core" / "llm"
    assert _violations(tmp_path, allowed), f"scanner missed: {source!r}"


def test_HC_LLMB_001c_provider_layer_import_is_seen_and_allowed():
    provider = PROVIDER_LAYER / "llama_cpp_provider.py"
    assert [m for _, m in _banned_imports(provider)] == ["llama_cpp"], (
        "positive control: the provider's lazy import must be visible to the scanner"
    )
    assert not any(
        v.startswith("core/llm/") for v in _violations(BACKEND_ROOT, PROVIDER_LAYER)
    )


def test_HC_LLMB_002_app_import_does_not_load_llama_cpp():
    """llama-cpp-python stays optional: booting the app must not import it."""
    env = {**os.environ, "TEST_MODE": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    proc = subprocess.run(
        [sys.executable, "-c",
         "import sys; from main import app; print('llama_cpp' in sys.modules)"],
        cwd=BACKEND_ROOT, env=env, capture_output=True, text=True, timeout=180,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert proc.stdout.strip().splitlines()[-1] == "False"
```

- [ ] **Step 2: Run it and confirm RED for the right reason**

Run: `WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w07; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail; cd "$WT/src/backend" && "$PY" -m pytest tests/test_llm_import_boundary.py -p no:cacheprovider -q -rs`
Expected:
- `1 failed, 6 passed`.
- The failure is `test_HC_LLMB_001_…` with `AssertionError: llama_cpp may only be imported inside core/llm/ … modules/model_selector.py:456 imports llama_cpp` (the line may differ; the file must be `modules/model_selector.py` and nothing else).
- `001b` ×4, `001c` and `002` pass.

STOP if another file is listed (Stop gate 2).

- [ ] **Step 3: Break the scanner on purpose (recurring-failures #1)**

Temporarily change `BANNED_TOP_LEVEL = frozenset({"llama_cpp"})` to `frozenset({"llama_cppX"})`, then re-run. Expected: `001b` fails ×4 and `001c` fails. `001` now passes, which proves `001b`/`001c` guard against a vacuous `001`. Revert the change and confirm the Step 2 output again.

- [ ] **Step 4: Break the lazy-import guard on purpose**

Temporarily add `import llama_cpp  # noqa` as the first import line of `$WT/src/backend/modules/model_selector.py`. Run `WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w07; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail; cd "$WT/src/backend" && "$PY" -m pytest tests/test_llm_import_boundary.py -p no:cacheprovider -q -k HC_LLMB_002`. Expected FAIL:
- when `llama_cpp` is installed: `assert 'True' == 'False'`;
- when it is not: `returncode == 1` with `ModuleNotFoundError: No module named 'llama_cpp'` in stderr.

Revert. `git -C "$WT" diff --stat -- src/backend/modules/model_selector.py` → empty.

- [ ] **Step 5: What this test would fail to notice**

Record in the PR:
- (a) an HTTP call to a local LLM server from feature code (httpx/ollama). Out of scope (W-6/C-LLM-2 remainder).
- (b) `exec("import llama_cpp")` or a string-built module name. Not detected. Accepted: review catches it.
- (c) imports under `src/backend/tests/`. Deliberately excluded.

- [ ] **Step 6: Confirm CI will collect it without a ci.yml edit**

Run: `WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w07; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail; cd "$WT" && PATH="$(dirname "$PY"):$PATH" bash scripts/run-backend-tests.sh --collect-only -q 2>&1 | grep -c "test_llm_import_boundary.py"; echo "exit=$?"`
Expected: `7` then `exit=0`. A non-zero exit means either the collection failed or the file was not collected; both are failures. This is the exact command CI's `backend-tests` job runs (B `ci.yml:51`).

Do **not** commit yet. Task 2 turns HC-LLMB-001 green, and both land in one commit.

---

### Task 2: Tiered interpretation on ModelRunner (module) — RED → GREEN

**Files:**
- Create: `src/backend/tests/test_interpret_tiered.py`
- Modify: `src/backend/modules/interpret.py` (main@40f590e: imports `:10-43`, `__init__` `:118-137`, `_llm_interpretation` `:735-785`, `interpret_with_model` `:877-1045`)
- Modify: `src/backend/modules/model_selector.py` (B@7b2ff1f: docstring `:1-8`, class docstring `:185-194`, state `:206-211`, methods `:437-570`)

**Interfaces:**
- Consumes: `core.model_runner.InferenceConfig`, `InferenceResult`, `ModelRunner.generate_async(prompt, config) -> InferenceResult`, `get_model_runner()`; `ModelSelector.get_active_tier(profile_id, db) -> str`; `InterpretationSafetyGuard.validate_interpretation(...) -> SafetyValidationResult`.
- Produces: `InterpretModule(..., model_runner: Optional[ModelRunner] = None)`; `InterpretModule.interpret_with_model(observation_id: str, profile_id: str, profile_db: AsyncSession, master_db: AsyncSession, force_regenerate: bool = False) -> InterpretationResult` (unchanged signature). The stored `LabInterpretation.model_tier` is `"template"` whenever template text was stored. Task 3 relies on this.

- [ ] **Step 1: Write the module tests**

```python
"""W-7 / owner decision D7: tiered interpretation via ModelRunner (HC-INT-0NN).

Module tests (HC-INT-011..017) drive InterpretModule.interpret_with_model with a
real in-memory profile DB, the REAL interpret_safety guard (read-only, called
not edited) and a fake ModelRunner. Route tests (HC-INT-001..005) go through
HTTP with tests/support/routes.py::route_client (C-ISO-2).
Select with -k "HC_INT_0" (HC_INT alone also matches HC_INTERP_*).
"""

from __future__ import annotations

import json
import uuid
from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from core.model_runner import InferenceResult
from core.profile_database import ProfileDatabaseBase
from models import Document, LabInterpretation, Observation
from modules.interpret import InterpretModule
from modules.interpret_safety import get_safety_guard

PROFILE_A = "profile-a"
PROFILE_B = "profile-b"
DOC_A = str(uuid.uuid4())
OBS_A = str(uuid.uuid4())
OBS_B = str(uuid.uuid4())

CLEAN_DRAFT = (
    "Your glucose result is above the reference range [KB:glucose]. "
    "Glucose reflects the sugar level in your blood at the time of the test."
)
TEMPLATE_OPENING = "Your GLUCOSE result is 250.0 mg/dL."
WINDOWS_MODEL_PATH = r"C:\Users\jane.doe\models\qwen2.5-0.5b-instruct-q4_k_m.gguf"


class _FakeRunner:
    """Stands in for core.model_runner.ModelRunner (generate_async only)."""

    def __init__(self, *, text=CLEAN_DRAFT, finish_reason="stop",
                 model_name=WINDOWS_MODEL_PATH, exc=None):
        self._text = text
        self._finish_reason = finish_reason
        self._model_name = model_name
        self._exc = exc
        self.calls: list[tuple[str, object]] = []

    async def generate_async(self, prompt, config=None):
        self.calls.append((prompt, config))
        if self._exc is not None:
            raise self._exc
        return InferenceResult(
            text=self._text,
            tokens_generated=12,
            finish_reason=self._finish_reason,
            model_name=self._model_name,
        )


def _module(runner, *, tier: str = "low") -> InterpretModule:
    return InterpretModule(
        knowledge_loader=SimpleNamespace(get_biomarker_knowledge=AsyncMock(return_value=None)),
        safety_guard=get_safety_guard(),  # the real guard is what is under test
        recommendation_engine=SimpleNamespace(
            generate_recommendations=AsyncMock(return_value=None)
        ),
        model_selector=SimpleNamespace(get_active_tier=AsyncMock(return_value=tier)),
        model_runner=runner,
    )


def _observation(obs_id: str, profile_id: str) -> Observation:
    return Observation(
        id=obs_id, profile_id=profile_id, doc_id=DOC_A,
        analyte_canonical="glucose", analyte_raw="GLUCOSE",
        value=250.0, unit="mg/dL", ref_low=70.0, ref_high=99.0,
        flag="H", is_abnormal=True,
        collected_at=datetime(2024, 6, 1, 8, 0, 0), user_verified=True,
    )


@pytest_asyncio.fixture
async def profile_db():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    session.add(Document(
        id=DOC_A, profile_id=PROFILE_A, path_hash="x" * 64, content_hash="a" * 64,
        doc_type="lab_pdf", status="parsed", imported_at=datetime(2024, 6, 1, 12, 0, 0),
    ))
    session.add(_observation(OBS_A, PROFILE_A))
    session.add(_observation(OBS_B, PROFILE_B))  # another profile's row, for HC-INT-004
    await session.commit()
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


async def _interpret(module, db, *, force=False):
    return await module.interpret_with_model(
        observation_id=OBS_A, profile_id=PROFILE_A,
        profile_db=db, master_db=AsyncMock(), force_regenerate=force,
    )


@pytest.mark.asyncio
async def test_HC_INT_011_llm_draft_goes_through_model_runner_with_honest_labels(profile_db):
    runner = _FakeRunner()
    result = await _interpret(_module(runner, tier="gemma4-12b"), profile_db)

    assert result.success
    interp = result.interpretation
    assert len(runner.calls) == 1
    assert "[KB:glucose]" in interp.interpretation_text
    assert "educational purposes only" in interp.interpretation_text  # add_required_disclaimers ran
    assert interp.model_tier == "gemma4-12b"          # the tier the selector chose
    assert interp.model_id == "qwen2.5-0.5b-instruct-q4_k_m.gguf"  # the model that answered
    assert "jane.doe" not in interp.model_id           # no local path / OS user name
    # missing_disclaimers may appear: validation runs before disclaimers are added
    # (interpret.py:958-981). Only prohibited_* must be absent.
    failed = json.loads(interp.safety_validation_json)["checks_failed"]
    assert not any(c.startswith("prohibited_") for c in failed)


@pytest.mark.asyncio
async def test_HC_INT_012_no_llm_falls_back_to_template_labelled_template(profile_db):
    runner = _FakeRunner(exc=RuntimeError("LlamaCppProvider: model not available"))
    result = await _interpret(_module(runner), profile_db)

    assert result.success
    interp = result.interpretation
    assert interp.interpretation_text.startswith(TEMPLATE_OPENING)
    assert interp.model_tier == "template"
    assert interp.model_id == "template-v1"
    assert len(runner.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("draft", "forbidden"),
    [
        ("You have diabetes based on this result [KB:glucose].", "diabetes"),
        ("Take 500 mg of metformin daily [KB:glucose].", "500 mg"),
        ("Go to the ER now about this value [KB:glucose].", "ER now"),
    ],
    ids=["diagnostic_language", "dosing_recommendation", "emergency_advice"],
)
async def test_HC_INT_013_prohibited_draft_is_never_stored(profile_db, draft, forbidden):
    result = await _interpret(_module(_FakeRunner(text=draft)), profile_db)

    interp = result.interpretation
    assert forbidden not in interp.interpretation_text
    assert forbidden not in (interp.advice_text or "")
    assert interp.interpretation_text.startswith(TEMPLATE_OPENING)
    assert interp.model_tier == "template"


@pytest.mark.asyncio
async def test_HC_INT_014_timeout_result_is_not_served(profile_db):
    runner = _FakeRunner(text="Partial answer [KB:glucose]", finish_reason="timeout")
    result = await _interpret(_module(runner), profile_db)

    assert "Partial answer" not in result.interpretation.interpretation_text
    assert result.interpretation.model_tier == "template"


@pytest.mark.asyncio
async def test_HC_INT_015_template_tier_never_calls_the_runner(profile_db):
    runner = _FakeRunner()
    result = await _interpret(_module(runner, tier="template"), profile_db)

    assert runner.calls == []
    assert result.interpretation.model_tier == "template"


@pytest.mark.asyncio
async def test_HC_INT_016_second_call_returns_existing_without_regenerating(profile_db):
    runner = _FakeRunner()
    module = _module(runner)
    first = await _interpret(module, profile_db)
    second = await _interpret(module, profile_db)

    assert second.success
    assert second.interpretation.id == first.interpretation.id
    assert len(runner.calls) == 1


@pytest.mark.asyncio
async def test_HC_INT_017_force_regenerate_replaces_the_single_row(profile_db):
    module = _module(_FakeRunner())
    first = await _interpret(module, profile_db)
    second = await _interpret(module, profile_db, force=True)

    assert second.interpretation.regeneration_count == 1
    assert second.interpretation.previous_interpretation_id == first.interpretation.id
    count = (await profile_db.execute(
        select(func.count()).select_from(LabInterpretation)
        .where(LabInterpretation.observation_id == OBS_A)
    )).scalar_one()
    assert count == 1
```

The fixture mirrors `tests/test_timeline.py:119-130` (`pytest_asyncio.fixture` + `sqlite+aiosqlite://` + `ProfileDatabaseBase.metadata.create_all`). If the event-loop setup differs on the start tree, copy that file's current fixture shape; do not invent a new one.

- [ ] **Step 2: Run and confirm RED**

Run: `WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w07; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail; cd "$WT/src/backend" && "$PY" -m pytest tests/test_interpret_tiered.py -p no:cacheprovider -q -rs -k "HC_INT_0"`
Expected: `9 failed`, with **0 skipped**. Each fails with `TypeError: InterpretModule.__init__() got an unexpected keyword argument 'model_runner'`.

**Async-marker audit.** No `asyncio_mode` is set in `src/backend/pyproject.toml` or `scripts/run-backend-tests.sh`, so pytest-asyncio (`>=0.23.0` in `requirements.txt`) runs in strict mode. An `async def` test without `@pytest.mark.asyncio` is **skipped with a warning, not failed**, which would silently turn a RED into "skipped".
- Every async test in this plan carries `@pytest.mark.asyncio`: HC-INT-011, 012, 013 (placed above `@pytest.mark.parametrize`, so all 3 cases inherit it), 014, 015, 016, 017.
- The route tests HC-INT-001…005 and all HC-LLMB tests are plain `def`.
- Before running, check with `grep -B1 -n "^async def test_" "$WT/src/backend/tests/test_interpret_tiered.py"`: every hit must be preceded by `@pytest.mark.asyncio` or by the `ids=` line of a parametrize that sits below one.
- If the `-rs` summary shows any `SKIPPED … async def functions are not natively supported`, a marker is missing. Fix the marker, not the expectation.

- [ ] **Step 3: Implement in `modules/interpret.py`**

(a) Imports. After `from typing import Optional, Any` (main@40f590e `:17`), add `from pathlib import PureWindowsPath`. After the `.model_selector` import (`:43`), add:

```python
from core.model_runner import InferenceConfig, ModelRunner, get_model_runner
```

(b) `__init__` (`:118-137`): add the parameter and attribute. Leave the other lines unchanged.

```python
    def __init__(
        self,
        knowledge_loader: Optional[KnowledgeLoader] = None,
        safety_guard: Optional[InterpretationSafetyGuard] = None,
        recommendation_engine: Optional[RecommendationEngine] = None,
        model_selector: Optional[ModelSelector] = None,
        model_runner: Optional[ModelRunner] = None,
    ):
        """
        Initialize the interpretation module.

        Args:
            knowledge_loader: Knowledge base loader
            safety_guard: Safety validation
            recommendation_engine: Recommendation generator
            model_selector: Tier selection (Phase 0.3); does not run models
            model_runner: LLM facade (C-LLM-1); defaults to get_model_runner()
        """
        self._knowledge_loader = knowledge_loader or get_knowledge_loader()
        self._safety_guard = safety_guard or get_safety_guard()
        self._recommendation_engine = recommendation_engine or get_recommendation_engine()
        self._model_selector = model_selector or get_model_selector()
        self._model_runner = model_runner or get_model_runner()
```

(c) Replace `_llm_interpretation` (`:735-785`) with this code, plus two helpers:

```python
    @staticmethod
    def _model_label(model_name: str) -> str:
        """Basename of the answering model; a local path can carry the OS user name."""
        return PureWindowsPath(model_name).name[:100] or "unknown"

    async def _template_draft(
        self,
        context: InterpretationContext,
        master_db: AsyncSession,
        reason: str,
    ) -> tuple[str, Optional[str], None]:
        logger.warning("Tiered interpretation: %s; using template", reason)
        text, advice = await self._generate_interpretation(context, master_db)
        return text, advice, None

    async def _llm_interpretation(
        self,
        context: InterpretationContext,
        master_db: AsyncSession,
    ) -> tuple[str, Optional[str], Optional[str]]:
        """Draft through ModelRunner (C-LLM-1); fall back to the template.

        Returns (interpretation_text, advice_text, model_name). model_name is None
        whenever template text is returned, so callers never label it as model
        output. The template is used when no model answers (C-LLM-3), on timeout,
        when citations are missing, or when the draft trips an interpret_safety
        prohibited pattern (C-SAFE-1). The guard is called, never edited.
        """
        prompt = self._build_llm_prompt(context)
        config = InferenceConfig(
            max_tokens=512,
            temperature=0.3,
            stop_sequences=["</s>", "\n\n\n"],
        )
        try:
            result = await self._model_runner.generate_async(prompt, config)
        except Exception as exc:  # no model / provider failure: keep answering
            return await self._template_draft(
                context, master_db, f"LLM unavailable ({type(exc).__name__})"
            )

        text = (result.text or "").strip()
        if result.finish_reason == "timeout":
            return await self._template_draft(context, master_db, "LLM timed out")
        if not self._validate_llm_citations(text):
            return await self._template_draft(context, master_db, "LLM draft lacks citations")

        advice_text = self._extract_advice_from_llm(text, context)
        draft_check = self._safety_guard.validate_interpretation(
            interpretation_text=text,
            advice_text=advice_text,
            require_citations=True,
        )
        prohibited = [c for c in draft_check.checks_failed if c.startswith("prohibited_")]
        if prohibited:
            return await self._template_draft(
                context, master_db, f"LLM draft failed {prohibited}"
            )
        return text, advice_text, self._model_label(result.model_name)
```

(d) Replace the body of `interpret_with_model` (`:877-1045`). Keep the signature. The unchanged middle is the severity, citations, `validate_interpretation`, `check_critical_value`, `add_required_disclaimers`, `context_json` and `safety_json` block, `:947-992` verbatim.

```python
        """Generate an interpretation on the profile's selected model tier (D7).

        The tier (user preference, else hardware recommendation) only decides
        whether to try the local LLM: "template" skips it. Inference goes through
        ModelRunner, which serves whichever local model the provider layer is
        configured with. model_tier records the selected tier, model_id the model
        that actually answered; template text is always labelled template.
        """
        active_tier = await self._model_selector.get_active_tier(profile_id, profile_db)
        if active_tier == self.MODEL_TIER_TEMPLATE:
            return await self.interpret_observation(
                observation_id=observation_id,
                profile_db=profile_db,
                master_db=master_db,
                force_regenerate=force_regenerate,
            )

        result = await profile_db.execute(
            select(Observation).where(Observation.id == observation_id)
        )
        observation = result.scalar_one_or_none()
        if not observation:
            return InterpretationResult(
                success=False,
                error_message=f"Observation not found: {observation_id}",
            )

        existing = await profile_db.execute(
            select(LabInterpretation).where(
                LabInterpretation.observation_id == observation_id
            )
        )
        existing_interp = existing.scalar_one_or_none()
        if existing_interp and not force_regenerate:
            return InterpretationResult(success=True, interpretation=existing_interp)

        context = await self._assemble_context(
            observation=observation,
            profile_db=profile_db,
            master_db=master_db,
        )
        interpretation_text, advice_text, model_name = await self._llm_interpretation(
            context, master_db
        )
        llm_used = model_name is not None

        # --- unchanged block: main@40f590e interpret.py:947-992 (severity,
        # citations, validate_interpretation, check_critical_value,
        # add_required_disclaimers, context_json, safety_json) ---

        interpretation = LabInterpretation(
            id=str(uuid.uuid4()),
            profile_id=observation.profile_id,
            observation_id=observation_id,
            interpretation_text=interpretation_text,
            severity_level=severity_level,
            advice_text=advice_text if advice_text else None,
            citations_json=json.dumps(citations),
            context_json=context_json,
            model_id=model_name if llm_used else self.MODEL_ID_TEMPLATE,
            model_tier=active_tier if llm_used else self.MODEL_TIER_TEMPLATE,
            confidence_score=0.90 if (llm_used and active_tier == "high") else 0.85,
            requires_physician_review=safety_result.requires_physician_review,
            physician_review_reason=safety_result.physician_review_reason,
            safety_validation_json=safety_json,
            regeneration_count=0,
        )

        if existing_interp:
            interpretation.regeneration_count = existing_interp.regeneration_count + 1
            interpretation.previous_interpretation_id = existing_interp.id
            await profile_db.delete(existing_interp)
            await profile_db.flush()  # free the unique observation_id before the insert

        profile_db.add(interpretation)
        await profile_db.commit()

        logger.info(
            "Generated tiered interpretation for observation %s: tier=%s llm=%s severity=%s",
            observation_id, interpretation.model_tier, llm_used, severity_level,
        )
        return InterpretationResult(
            success=True,
            interpretation=interpretation,
            safety_validation=safety_result,
        )
```

This deletes the `from .model_selector import TIER_MODEL_CONFIG` inside the method (`:995-997`). The tier description is no longer used as `model_id`.

- [ ] **Step 4: Implement in `modules/model_selector.py` (B@7b2ff1f lines)**

1. Delete the methods `load_model` (`:437-478`, **the `from llama_cpp import Llama` at `:456`**), `load_model_async` (`:480-504`), `get_model_for_inference` (`:506-536`) and `run_inference` (`:538-570`).
2. In `__init__` (`:206-211`), delete 4 lines: `self._loaded_model: Optional[Any] = None  # Llama instance` (`:206`), `self._current_tier: Optional[str] = None` (`:207`), `# Lock for thread-safe model loading` (`:210`) and `self._load_lock = asyncio.Lock()` (`:211`). **Keep** `self._hardware_profile: Optional[HardwareProfile] = None` (`:208`); `get_active_tier` uses it.
3. Replace the module docstring (`:1-8`):

```python
"""
Model selector module for tiered LLM inference.

Phase 0.3: Tiered Hardware Model System

Selects the model tier (user preference > hardware recommendation) and manages
tier model files (availability, downloads). It does not load or run models:
inference goes through core.model_runner.ModelRunner (C-LLM-1).
"""
```

4. Replace the class docstring (`:185-194`):

```python
    """
    Tier selection and model-file management.

    Handles:
    - Hardware detection and tier recommendation
    - User preference storage (UserModelSettings table)
    - Model file availability and downloads
    - Fallback chain metadata

    Inference is not done here; see core.model_runner (C-LLM-1).
    """
```

5. Check: `grep -n "asyncio\|_load_lock\|_loaded_model\|_current_tier\|llama_cpp" "$WT/src/backend/modules/model_selector.py"`. Expected: only `import asyncio` and the `asyncio.to_thread(self.download_model, tier)` line. Line numbers shift after the deletions.

- [ ] **Step 5: Run and confirm GREEN**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w07; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT/src/backend"
"$PY" -m pytest tests/test_interpret_tiered.py tests/test_llm_import_boundary.py -p no:cacheprovider -q -rs
"$PY" -m pytest tests/test_interpret_history_units.py tests/test_interpret_safety_adversarial.py tests/test_tier_capabilities.py tests/test_model_integrity.py tests/test_llm_provider_layer.py -p no:cacheprovider -q
```
Expected:
- First command: `16 passed` (9 module + 7 boundary), 0 skipped.
- Second command: the same pass/fail as at START (these are the neighbours of the edited files; the adversarial safety tests prove the guard was not affected).

- [ ] **Step 6: Break each safety branch on purpose**

Do each break alone, run `WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w07; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail; cd "$WT/src/backend" && "$PY" -m pytest tests/test_interpret_tiered.py -p no:cacheprovider -q -rs -k "HC_INT_0"`, then revert. `git -C "$WT" diff --stat` must return to the Step 3/4 state after each one.

| Break | Expected RED |
|---|---|
| In `_llm_interpretation`, change `if prohibited:` to `if False:` | HC-INT-013 ×3 fail (`assert 'diabetes' not in …`) |
| Delete the `finish_reason == "timeout"` check | HC-INT-014 fails (`'Partial answer' not in …`) |
| Return `result.model_name` instead of `self._model_label(result.model_name)` | HC-INT-011 fails (`'jane.doe' not in …` / model_id mismatch) |
| Change `model_tier=active_tier if llm_used else …` to `model_tier=active_tier` | HC-INT-012 fails (`assert 'low' == 'template'`) |
| Delete the `if existing_interp and not force_regenerate:` return | HC-INT-016 fails (IntegrityError or `len(calls) == 2`) |
| Delete `await profile_db.flush()` | HC-INT-017: record whether it fails. If it still passes, SQLAlchemy ordered the DELETE first on its own. Keep the flush anyway and note it as UNMEASURED-on-SQLCipher |

- [ ] **Step 7: What these tests would fail to notice**

Record in the PR:
- (a) a real GGUF producing different text shapes, since the tests use a fake runner. The live smoke is UNMEASURED; see Task 4 Step 6.
- (b) prohibited patterns outside the three families tested. The guard's own suite `tests/test_interpret_safety_adversarial.py` covers the families.
- (c) `detect_hardware` blocking the loop. Not tested.

- [ ] **Step 8: Measure, update the baseline lines, commit (Task 1 + Task 2)**

**Baseline lines in the same commit (CLAUDE.md §4: "update it in the same commit").** This commit changes the collected count, so it carries the new count.

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w07; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT/src/backend"
find "$WT/src/backend" -name __pycache__ -type d -prune -exec rm -rf {} +
"$PY" -m pytest tests/ -p no:cacheprovider -q --collect-only > "$WT/../w07-c1-collect.txt" 2>&1; echo "collect exit=$?"; tail -1 "$WT/../w07-c1-collect.txt"
"$PY" -m pytest tests/ -p no:cacheprovider -q -rfE > "$WT/../w07-c1-run.txt" 2>&1; echo "run exit=$?"; grep -E "^(FAILED|ERROR) " "$WT/../w07-c1-run.txt"; tail -1 "$WT/../w07-c1-run.txt"
grep -n "Baseline" "$WT/CLAUDE.md"; grep -n "collected;" "$WT/AGENT.md"
```

Expected:
- collect exit 0, with `START_COLLECTED + 16` collected (9 HC-INT module + 7 HC-LLMB). Call this `NEW`.
- Every FAILED/ERROR node id is in START_FAILURES; otherwise Stop gate 6.

Then edit **collected-count slots only** (GLOBAL baseline-sentence rule, 2026-09-27):
1. `$WT/CLAUDE.md` §4 "Baseline" bullet: replace the collected count in "**N backend tests collected.**" and in "if it differs from N" with `NEW`.
2. `$WT/AGENT.md` Commands pytest line: replace the "N collected" figure with `NEW`.

Do **not** touch the pass-count clauses ("all N pass", "N pass in CI", "N-1 without …"). A pass count changes only with a figure measured in a named environment (interpreter + whether an embedding model is present), and this step does not measure CI.
- Leave those clauses as they are.
- Flag them in the PR body as "pass-count sentences not updated: unmeasured after +16/+23 tests".
- Do not describe CI as having a real embedding model: `ci.yml` has no model step, and CI's `test_api_rag_index_002b` result relies on an implicit Hugging Face fetch (matrix LOCAL-03).

STOP if either collected-count slot no longer exists in this shape (Stop gate 8).

Check with `git -C "$WT" diff -U0 -- CLAUDE.md AGENT.md`: only the collected-count digits may differ.

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w07; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
git -C "$WT" add -- src/backend/modules/interpret.py src/backend/modules/model_selector.py \
        src/backend/tests/test_llm_import_boundary.py src/backend/tests/test_interpret_tiered.py \
        CLAUDE.md AGENT.md
git -C "$WT" diff --cached --name-only
```
Expected: exactly those 6 paths.

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w07; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
git -C "$WT" commit -m "fix(llm): route tiered interpretation through ModelRunner; drop model_selector's llama_cpp import

Owner decision D7 (2026-09-27). ModelSelector no longer loads or runs models;
InterpretModule.interpret_with_model drafts via ModelRunner and falls back to the
template on no model, timeout, missing citations or an interpret_safety
prohibited pattern (guard called, not edited). Adds HC-LLMB-001/001b/001c/002
and HC-INT-011..017. Baseline lines updated to the measured collected count.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- src/backend/modules/interpret.py src/backend/modules/model_selector.py src/backend/tests/test_llm_import_boundary.py src/backend/tests/test_interpret_tiered.py CLAUDE.md AGENT.md
```

---

### Task 3: Wire the route (HTTP) — RED → GREEN

**Files:**
- Modify: `src/backend/api/interpretations.py` (main@40f590e imports `:21-31`; insert the route after `generate_grounded_interpretation`, which ends at `:505`, and before `get_interpretation` `:508`)
- Modify: `src/backend/tests/test_interpret_tiered.py` (append)

**Interfaces:**
- Consumes: `InterpretModule.interpret_with_model` (Task 2), `route_client(router, prefix, profile_id, master_db)`, `audit_and_commit`, `log_observation_event` (B `core/audit.py`), `get_profile_db_session`, `require_auth` (`core/auth.py`).
- Produces: `POST /api/v1/interpretations/observations/{observation_id}/interpret-tiered?force_regenerate=bool` → `201 InterpretationResponse`; `400` bad uuid; `401` no auth; `403` other profile's observation; `404` unknown observation. Audit: one `observation.view` row with `details={"action": "interpret_tiered", "llm_assist": bool}` per 201.

- [ ] **Step 1: Append the route tests**

```python
# ---------------------------------------------------------------------------
# Route tests: through HTTP (route_client), never direct calls (C-ISO-2)
# ---------------------------------------------------------------------------

from core.auth import get_profile_db_session, require_auth  # noqa: E402
from tests.support.routes import route_client  # noqa: E402

TIERED = "/interpretations/observations/{}/interpret-tiered"


@contextmanager
def _tiered_client(profile_db, module, monkeypatch, *, authed: bool = True):
    import api.interpretations as interp_api

    log_mock = AsyncMock(return_value=object())
    monkeypatch.setattr(interp_api, "get_interpret_module", lambda: module)
    monkeypatch.setattr(interp_api, "log_observation_event", log_mock)
    master_db = AsyncMock()

    async def _override_profile_db():
        return profile_db

    with route_client(
        interp_api.router, "/interpretations", profile_id=PROFILE_A, master_db=master_db
    ) as client:
        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        if not authed:
            client.app.dependency_overrides.pop(require_auth)
        yield client, log_mock, master_db


def test_HC_INT_001_tiered_route_serves_checked_llm_output_and_audits(profile_db, monkeypatch):
    runner = _FakeRunner()
    with _tiered_client(profile_db, _module(runner), monkeypatch) as (client, log_mock, master_db):
        response = client.post(TIERED.format(OBS_A))

    assert response.status_code == 201, response.text
    body = response.json()
    assert "[KB:glucose]" in body["interpretation_text"]
    assert "educational purposes only" in body["interpretation_text"]
    assert body["model_tier"] == "low"
    assert body["model_id"] == "qwen2.5-0.5b-instruct-q4_k_m.gguf"
    assert len(runner.calls) == 1
    log_mock.assert_awaited_once()
    kwargs = log_mock.await_args.kwargs
    assert kwargs["event"] == "view"
    assert kwargs["profile_id"] == PROFILE_A
    assert kwargs["observation_id"] == OBS_A
    assert kwargs["details"] == {"action": "interpret_tiered", "llm_assist": True}
    master_db.commit.assert_awaited_once()


def test_HC_INT_002_no_llm_fallback_answers_over_http(profile_db, monkeypatch):
    runner = _FakeRunner(exc=RuntimeError("LlamaCppProvider: model not available"))
    with _tiered_client(profile_db, _module(runner), monkeypatch) as (client, log_mock, _):
        response = client.post(TIERED.format(OBS_A))

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["interpretation_text"].startswith(TEMPLATE_OPENING)
    assert body["model_tier"] == "template"
    assert body["model_id"] == "template-v1"
    assert log_mock.await_args.kwargs["details"] == {
        "action": "interpret_tiered", "llm_assist": False,
    }


def test_HC_INT_003_prohibited_draft_never_reaches_the_response(profile_db, monkeypatch):
    runner = _FakeRunner(text="You have diabetes based on this result [KB:glucose].")
    with _tiered_client(profile_db, _module(runner), monkeypatch) as (client, _, _):
        response = client.post(TIERED.format(OBS_A))

    assert response.status_code == 201, response.text
    assert "diabetes" not in response.text
    assert response.json()["model_tier"] == "template"


@pytest.mark.parametrize(
    ("obs_id", "status"),
    [("not-a-uuid", 400), (str(uuid.uuid4()), 404), (OBS_B, 403)],
    ids=["bad_uuid", "unknown", "other_profile"],
)
def test_HC_INT_004_scoping_errors_do_not_interpret_or_audit(
    profile_db, monkeypatch, obs_id, status
):
    runner = _FakeRunner()
    with _tiered_client(profile_db, _module(runner), monkeypatch) as (client, log_mock, _):
        response = client.post(TIERED.format(obs_id))

    assert response.status_code == status, response.text
    assert runner.calls == []
    log_mock.assert_not_awaited()


def test_HC_INT_005_requires_authentication(profile_db, monkeypatch):
    runner = _FakeRunner()
    with _tiered_client(profile_db, _module(runner), monkeypatch, authed=False) as (client, _, _):
        response = client.post(TIERED.format(OBS_A))

    assert response.status_code == 401
    assert runner.calls == []
```

The import form `from tests.support.routes import route_client` matches `tests/test_backup_routes.py:15` (main@40f590e). If the start tree uses a different form, copy that file.

- [ ] **Step 2: Run and confirm RED, stage 1 (audit hook absent)**

Run: `WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w07; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail; cd "$WT/src/backend" && "$PY" -m pytest tests/test_interpret_tiered.py -p no:cacheprovider -q -rs -k "HC_INT_00"`
Expected: `7 failed`. Each fails with `AttributeError: <module 'api.interpretations' …> has no attribute 'log_observation_event'`, because `monkeypatch.setattr` raises when the name does not exist. This proves the route module has no audit import yet (F-3).

- [ ] **Step 3: Add the imports only, then confirm RED, stage 2 (route absent)**

Add next to the existing imports (main@40f590e `:21-31`):

```python
from core.audit import audit_and_commit, log_observation_event
from modules.interpret import InterpretModule
```

Re-run the Step 2 command. Expected: `6 failed, 1 passed`.
- HC-INT-001/002/003 fail with `assert 404 == 201`.
- HC-INT-004 `bad_uuid` and `other_profile` fail on status `404`.
- HC-INT-005 fails with `assert 404 == 401`.
- HC-INT-004 `unknown` passes for the wrong reason (404 = no route). Its real check is Step 5's `other_profile` break.

Record both outputs.

- [ ] **Step 3b: Implement the route**

Insert after `generate_grounded_interpretation`:

```python
@router.post(
    "/observations/{observation_id}/interpret-tiered",
    response_model=InterpretationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_tiered_interpretation(
    observation_id: str,
    session: RequireAuth,
    force_regenerate: bool = Query(False, description="Force regeneration even if exists"),
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """Generate an interpretation on the profile's selected model tier (D7).

    Drafts through the local ModelRunner unless the selected tier is "template".
    A draft that fails, times out, lacks citations or trips an interpret_safety
    prohibited pattern is replaced by the template interpretation. The profile
    comes from the JWT (C-ISO-1); an existing interpretation is returned unless
    force_regenerate is set.
    """
    validate_uuid(observation_id, "observation_id")

    result = await profile_db.execute(
        select(Observation).where(Observation.id == observation_id)
    )
    observation = result.scalar_one_or_none()
    if not observation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Observation not found",
        )
    if observation.profile_id != session.profile_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this observation",
        )

    interp_result = await get_interpret_module().interpret_with_model(
        observation_id=observation_id,
        profile_id=session.profile_id,
        profile_db=profile_db,
        master_db=master_db,
        force_regenerate=force_regenerate,
    )
    if not interp_result.success or not interp_result.interpretation:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate interpretation",
        )

    interpretation = interp_result.interpretation
    # C-AUDIT-1, fail-closed; ids and booleans only (AUDIT-PHI-001).
    await audit_and_commit(
        master_db,
        log_observation_event,
        event="view",
        profile_id=session.profile_id,
        observation_id=observation_id,
        analyte=observation.analyte_canonical,  # accepted, never persisted
        details={
            "action": "interpret_tiered",
            "llm_assist": interpretation.model_tier != InterpretModule.MODEL_TIER_TEMPLATE,
        },
    )
    return InterpretationResponse.from_model(interpretation)
```

The interpretation is committed to the profile vault inside the module, before the audit call. If the audit commit fails, the request fails (500) with the row already stored. That is the same order as the existing view routes, and a retry returns the stored row (HC-INT-016).

- [ ] **Step 4: Run and confirm GREEN**

Run: `WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w07; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail; cd "$WT/src/backend" && "$PY" -m pytest tests/test_interpret_tiered.py tests/test_llm_import_boundary.py -p no:cacheprovider -q -rs`
Expected: `23 passed` (9 module + 7 route + 7 boundary), 0 skipped.

- [ ] **Step 5: Break each route guard on purpose**

One at a time: apply the break, run `WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w07; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail; cd "$WT/src/backend" && "$PY" -m pytest tests/test_interpret_tiered.py -p no:cacheprovider -q -rs -k "HC_INT_00"`, then revert and confirm with `git -C "$WT" diff --stat -- src/backend/api/interpretations.py` that only the Step 3/3b change remains.

| Break | Expected RED |
|---|---|
| Delete the `observation.profile_id != session.profile_id` check | HC-INT-004[other_profile] fails (`201 != 403`) |
| Replace `session: RequireAuth` with `session: OptionalAuth` (and import it) | HC-INT-005 fails (`!= 401`); HC-INT-001 still passes |
| Delete the `audit_and_commit(...)` call | HC-INT-001 and HC-INT-002 fail (`assert_awaited_once`) |
| Add `Depends(require_profile_access())` to the decorator's `dependencies=[...]` | HC-INT-001 fails with `400` "Missing profile_id parameter", which reproduces recurring-failures #1 |
| Call `interpret_observation` instead of `interpret_with_model` | HC-INT-001 fails (`model_tier == 'template'`, `[KB:glucose]` missing) |

- [ ] **Step 6: What these tests would fail to notice**

Record in the PR:
- (a) the real `get_profile_db_session` path (SQLCipher connection opened at login). It is overridden, as in every existing route test.
- (b) the real `create_audit_log` scrubbing of `details`. It is mocked. Mitigation: `action` (`core/audit.py:70`) and `llm_assist` (`:102`) are on B's allowlist; grep them again on the start tree.
- (c) the route being mounted in the real app. Task 4 Step 3 checks this with `app.routes`.

- [ ] **Step 7: Measure END, update the baseline lines, commit**

**Baseline lines in the same commit (CLAUDE.md §4: "update it in the same commit").** This commit changes the collected count, so it carries the new count.

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w07; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT/src/backend"
find "$WT/src/backend" -name __pycache__ -type d -prune -exec rm -rf {} +
"$PY" -m pytest tests/ -p no:cacheprovider -q --collect-only > "$WT/../w07-end-collect.txt" 2>&1; echo "collect exit=$?"; tail -1 "$WT/../w07-end-collect.txt"
"$PY" -m pytest tests/ -p no:cacheprovider -q -rfE > "$WT/../w07-end-run.txt" 2>&1; echo "run exit=$?"; grep -E "^(FAILED|ERROR) " "$WT/../w07-end-run.txt"; tail -1 "$WT/../w07-end-run.txt"
grep -n "Baseline" "$WT/CLAUDE.md"; grep -n "collected;" "$WT/AGENT.md"
```

Expected:
- collect exit 0, with `START_COLLECTED + 23` collected (all new tests; this is the END measurement Task 4 Step 1 compares). Call this `NEW`.
- Every FAILED/ERROR node id is in START_FAILURES; otherwise Stop gate 6.

Then edit **collected-count slots only** (GLOBAL baseline-sentence rule, 2026-09-27):
1. `$WT/CLAUDE.md` §4 "Baseline" bullet: replace the collected count in "**N backend tests collected.**" and in "if it differs from N" with `NEW`.
2. `$WT/AGENT.md` Commands pytest line: replace the "N collected" figure with `NEW`.

Do **not** touch the pass-count clauses ("all N pass", "N pass in CI", "N-1 without …"). A pass count changes only with a figure measured in a named environment (interpreter + whether an embedding model is present), and this step does not measure CI.
- Leave those clauses as they are.
- Flag them in the PR body as "pass-count sentences not updated: unmeasured after +16/+23 tests".
- Do not describe CI as having a real embedding model: `ci.yml` has no model step, and CI's `test_api_rag_index_002b` result relies on an implicit Hugging Face fetch (matrix LOCAL-03).

STOP if either collected-count slot no longer exists in this shape (Stop gate 8).

Check with `git -C "$WT" diff -U0 -- CLAUDE.md AGENT.md`: only the collected-count digits may differ.

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w07; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
git -C "$WT" add -- src/backend/api/interpretations.py src/backend/tests/test_interpret_tiered.py CLAUDE.md AGENT.md
git -C "$WT" diff --cached --name-only
```
Expected: exactly those 4 paths.

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w07; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
git -C "$WT" commit -m "feat(interpretations): wire tiered interpretation to POST /observations/{id}/interpret-tiered

Owner decision D7 (2026-09-27). RequireAuth + ProfileDbSession + observation
ownership (403/404); audited via log_observation_event (view, action
interpret_tiered, llm_assist). No UI and no change to existing routes.
Adds HC-INT-001..005 through route_client. Baseline lines updated to the
measured collected count.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- src/backend/api/interpretations.py src/backend/tests/test_interpret_tiered.py CLAUDE.md AGENT.md
```

---

### Task 4: Measured acceptance (no code)

- [ ] **Step 1: Compare END with START**

Use the files written by Task 3 Step 7 (`$WT/../w07-end-collect.txt`, `$WT/../w07-end-run.txt`) and Task 0 Step 4 (`w07-start-*.txt`). Do not re-run here unless the tree changed since that commit.

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w07; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
tail -1 "$WT/../w07-start-collect.txt"; tail -1 "$WT/../w07-end-collect.txt"
comm -13 <(grep -E "^(FAILED|ERROR) " "$WT/../w07-start-run.txt" | awk '{print $2}' | sort) <(grep -E "^(FAILED|ERROR) " "$WT/../w07-end-run.txt" | awk '{print $2}' | sort); echo "exit=$?"
```
Expected:
- END collected = START collected + 23.
- The `comm` output (END failures not in START) is empty, then `exit=0`.

Any line printed → Stop gate 6.

- [ ] **Step 2: Boundary acceptance, the spec's command verbatim plus the strict form**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w07; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT"
grep -rnE "from llama_cpp" src/backend | grep -v tests; echo "exit=$?"
grep -rnE "(^|\s)(import llama_cpp|from llama_cpp)" src/backend --include=*.py | grep -v /tests/; echo "exit=$?"
```
Expected, both commands: exactly one line, `src/backend/core/llm/llama_cpp_provider.py:36:        from llama_cpp import Llama  # noqa: PLC0415`, then `exit=0`.

- [ ] **Step 3: App boots and mounts the route**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w07; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT/src/backend"
"$PY" -c "from main import app; import sys; print('llama_cpp loaded:', 'llama_cpp' in sys.modules); print([r.path for r in app.routes if r.path.endswith('/interpret-tiered')])"
```
Expected:
- `llama_cpp loaded: False`
- `['/api/v1/interpretations/observations/{observation_id}/interpret-tiered']`

- [ ] **Step 4: CI command and seeded violation (program G-B3 acceptance)**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w07; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT"
PATH="$(dirname "$PY"):$PATH" bash scripts/run-backend-tests.sh tests/test_llm_import_boundary.py -q; echo "exit=$?"
printf 'from llama_cpp import Llama  # seeded W-7 check\n' >> "$WT/src/backend/modules/model_selector.py"
PATH="$(dirname "$PY"):$PATH" bash scripts/run-backend-tests.sh tests/test_llm_import_boundary.py -q; echo "exit=$?"
git -C "$WT" checkout -- src/backend/modules/model_selector.py && git -C "$WT" status --short -- src/backend/modules/model_selector.py
```
Expected:
1. First run: `7 passed`, `exit=0`.
2. Seeded run: `test_HC_LLMB_001` fails naming `modules/model_selector.py:<last line> imports llama_cpp`, and `exit=1`.
3. `git status` output is empty afterwards.

Only restore with `git checkout -- <that one file>`, and only for the line this step appended. The worktree is this plan's own.

- [ ] **Step 5: Re-walk the whole flow (recurring-failures #2)**

This step reads code only; nothing changes.
1. Trace: tiered POST stores a row → `GET /interpretations/observations/{id}/interpretation` returns it (`api/interpretations.py` `get_interpretation`) → template `POST …/interpret` returns the **same** row (`interpret_observation` `:170-182` returns an existing row) → `…/interpret-grounded` embeds it.
2. Confirm that each of these serves `interpretation_text` that passed the prohibited-pattern gate or is template text.
3. Write the spill-over in the PR body for OG-2.
4. Confirm that `api/model_settings.py` `GET /model-settings` still calls `selector.get_active_tier` and `is_model_available`, and that nothing calls the deleted methods: `git -C "$WT" grep -n "load_model_async\|get_model_for_inference\|run_inference\|\.load_model(" -- src/backend; echo "exit=$?"` → no output, `exit=1`.

- [ ] **Step 6: Live smoke (UNMEASURED unless a GGUF is present)**

1. If `settings.models_path` has a GGUF and `llama_cpp` is installed, start the backend and log in.
2. Set `PORT` to the backend port `dev.ps1` prints at startup, `TOKEN` to the login response's `access_token`, and `OBS_ID` to any `id` from `GET /api/v1/observations/`.
3. Run: `set -o pipefail; curl -sf -X POST -H "Authorization: Bearer $TOKEN" "http://127.0.0.1:$PORT/api/v1/interpretations/observations/$OBS_ID/interpret-tiered" | python3 -m json.tool; echo "exit=$?"`. Expect `exit=0`.
4. Record `model_tier`, `model_id`, and whether the text was LLM or template.

Otherwise write `UNMEASURED: no local GGUF` in the PR. To measure it later, install a tier model with `src/backend/scripts/download_models.py` and repeat.

- [ ] **Step 7: Frontend untouched**

Run: `git -C /mnt/c/Users/DangT/Documents/GitHub/hc-w07 diff --stat origin/main...HEAD -- src/frontend`
Expected: empty. So `tsc`/`vitest` are not re-run; say so in the PR.

---

### Task 5: PR, confirm the baseline against CI, stop

**Files:** none, unless Step 2 finds CI contradicting the committed baseline.

- [ ] **Step 1: Open the PR and let CI run**

Write the PR body to `/mnt/c/Users/DangT/Documents/GitHub/w07-pr-body.md`, outside the repo. It has the handoff §6 sections:
1. START/END measurements.
2. Each new test with its RED output.
3. C-LLM-1/2/3, C-SAFE-1, C-AUDIT-1, C-ISO-1/2; matrix LLM-02 partial→tested and LLM-03 gap→partial.
4. The explicit file list, plus OG-1/2/3.
5. One next action.

It ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w07; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
git -C "$WT" push -u origin feat/w07-tiered-interpretation-modelrunner
cd "$WT" && gh pr create --title "feat(llm): W-7 tiered interpretation via ModelRunner + interpret-tiered route" --body-file /mnt/c/Users/DangT/Documents/GitHub/w07-pr-body.md
```

- [ ] **Step 2: Confirm the committed baseline against CI's measured output**

After CI's `backend-tests` job finishes:

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w07; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT"
RUN_ID=$(gh run list --branch feat/w07-tiered-interpretation-modelrunner --workflow ci.yml --limit 1 --json databaseId -q '.[0].databaseId'); echo "run=$RUN_ID"
gh run view "$RUN_ID" --log | grep -E "[0-9]+ (passed|failed)" | tail -1; echo "exit=$?"
```
Expected: `exit=0` and a pytest summary line. Record it in the PR, with the environment named: CI, Python 3.11, no model-install step in `ci.yml`, embedding availability via an implicit HF fetch (LOCAL-03).

Then:
1. If the summary's total (passed + failed + skipped …) differs from the `NEW` collected count committed in C2, STOP and report to the orchestrator.
2. The pass-count clauses in `CLAUDE.md`/`AGENT.md` change only if the orchestrator decides this CI figure is the named-environment measurement to record. In that case, add one `docs:` commit (C3) changing only those digits, with the environment named in the commit body. Stage it with `git -C "$WT" add -- CLAUDE.md AGENT.md` and commit with `-- CLAUDE.md AGENT.md`.
3. Otherwise leave the clauses untouched and flagged in the PR.

- [ ] **Step 3: STOP for the owner's merge.** Humans merge.

---

## Measured acceptance (summary)

| Check | Command | Expected |
|---|---|---|
| Collected | Task 4 Step 1 (`"$PY" -m pytest tests/ -p no:cacheprovider -q --collect-only`, output to a file) | START + 23 |
| Failures | full run | ⊆ START failures (by node id) |
| Boundary (spec) | `grep -rnE "from llama_cpp" src/backend \| grep -v tests` | only `core/llm/llama_cpp_provider.py:36` |
| Boundary (strict) | Task 4 Step 2 second grep | same single line |
| Boundary in CI | `run-backend-tests.sh --collect-only` counts the file; seeded violation → exit 1 | 7 collected; seeded exit 1 |
| Lazy optional import | Task 4 Step 3 | `llama_cpp loaded: False` |
| Route mounted | Task 4 Step 3 | one `/interpret-tiered` path |
| Safety/auth guards | Task 2 Step 6, Task 3 Step 5 | each break → named RED |
| Live GGUF smoke | Task 4 Step 6 | UNMEASURED unless a model is present |
| Frontend | `git diff --stat … -- src/frontend` | empty |

## Stop gates

Stop and ask the owner, or the orchestrator for sequencing, when any of these happens:

1. The start tree fails the P1 ancestry check (`merge-base --is-ancestor 7b2ff1f` / `692fdf3`), lacks B's `model_selector.py` (no `get_tier_capabilities`), or P5/P7 are not merged.
2. HC-LLMB-001 lists any violation other than `modules/model_selector.py` at start. That is a new violation outside D7's scope: report it, do not fix it.
3. Any test on the start tree references `load_model`, `load_model_async`, `get_model_for_inference` or `run_inference`. Deleting a test is not licensed.
4. `from main import app` fails on the start tree.
5. Any change appears to need `interpret_safety.py`, `faithfulness.py`, `verifier_agent.py`, `redaction.py`, `core/auth.py`, `core/audit.py`, `core/model_runner.py`, `core/llm/*`, `core/external_runner.py`, `ci.yml` or frontend files. That includes adding a registered audit action, or loosening a prohibited pattern that trips on normal LLM wording.
6. Any END failure that is not in START_FAILURES and not explained by this change.
7. Anyone asks to switch the existing routes or the UI to the tiered path, or to make the tier select the loaded weights (OG-1/OG-2).
8. `route_client`'s signature or the baseline-line shape differs from what this plan quotes.

## Rollback

1. `git revert` the PR's merge commit (or the commits in reverse order: C3 if present, then C2, then C1). The revert restores the previous baseline numbers in `CLAUDE.md`/`AGENT.md` automatically, because they changed in the same commits.
2. No migration, no schema change, no config change.
3. `LabInterpretation` rows written by the tiered route stay in profile vaults. They are ordinary interpretation rows, readable by `GET /interpretation`, with honest `model_tier`/`model_id`. No data cleanup is needed.
4. The revert brings back the dormant `llama_cpp` import. LLM-02 returns to partial.

## Owner sign-offs (unsigned)

- [ ] D7 implementation merged as scoped above: ____________________ (owner, date)
- [ ] **OG-1** Should the selected tier choose the loaded weights (per-tier GGUF inside `core/llm/`)? Not approved by D7's text: ____________________
- [ ] **OG-2** Should the existing `/interpret` route or the `LabInterpreter` UI use the tiered path, given the spill-over in Review Focus #5? Not approved: ____________________
- [ ] **OG-3** Should audit rows be added to the 6 unaudited interpretation routes (F-3), under G-B1/W-11? Not approved here: ____________________

## Commit plan

| # | Prefix | Paths (explicit) |
|---|---|---|
| C1 | `fix(llm):` | `src/backend/modules/interpret.py`, `src/backend/modules/model_selector.py`, `src/backend/tests/test_llm_import_boundary.py`, `src/backend/tests/test_interpret_tiered.py`, `CLAUDE.md`, `AGENT.md` (baseline = START+16) |
| C2 | `feat(interpretations):` | `src/backend/api/interpretations.py`, `src/backend/tests/test_interpret_tiered.py`, `CLAUDE.md`, `AGENT.md` (baseline = START+23) |
| C3 (only if the orchestrator adopts the CI pass figure, Task 5 Step 2) | `docs:` | `CLAUDE.md`, `AGENT.md` (pass-count digits only) |

Before every commit, run `git -C "$WT" diff --cached --name-only` and check it against the table. Commit with `-- <paths>`. Never use `git add -A`, `git add .` or `git reset`. Each message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Recurring-failures recheck

Source: [recurring-failures.md](../agentic/recurring-failures.md).

| # | Applies? | Concrete recheck in this plan |
|---|---|---|
| 1 Green suite that could not fail | yes | Route tests via `route_client`. The scanner self-tests (001b/001c) plus a >100-file guard. Break-it tables in Task 2 Step 6 and Task 3 Step 5, including the `require_profile_access` 400 reproduction |
| 2 Fix creates the next bug one layer over | yes | Latent unique-constraint 500 and provenance mislabel fixed and pinned (HC-INT-016/012). Whole-flow re-walk in Task 4 Step 5 (spill-over into `/interpret`, `GET /interpretation`, `/interpret-grounded`, model-settings) |
| 3 Figures asserted, not measured | yes | START/END measured with the 3.11 venv; "+23" is checked against collection, not assumed. The handoff's `:438` is shown to be `:456` on B (F-1) |
| 4 Environment-dependent results | yes | HC-LLMB-002 passes for the right reason whether or not `llama_cpp` is installed (Task 1 Step 4 covers both). Judge on collected counts; `test_api_rag_index_002b` is environmental |
| 5 Gates run in a contaminated tree | yes | Dedicated worktree `/mnt/c/Users/DangT/Documents/GitHub/hc-w07` (`$WT`), with P1 ancestry checked by `merge-base --is-ancestor`; the seeded-violation restore touches only that worktree's one file |
| 6 Documented commands nobody ran | yes | The spec's grep is run verbatim and its gap noted (F-2). The CI command `scripts/run-backend-tests.sh` is run exactly |
| 7 SQL three-valued logic | checked, n/a | New queries use `==` on non-null ids only. `_assemble_context`'s `Observation.id != observation.id` compares a non-null primary key |
| 8 Stale guidance that reads as authority | yes | The matrix and handoff line numbers are re-verified at start (Task 0 Step 2). "0 callers" re-grepped. `docs/06_mvp_to_rag_execution_board.md:227` ("use existing `ModelSelector.run_inference()`") becomes stale; this is reported for the P4-style drift sweep, not edited here |

Back to: [implementation program](../capstone-report/implementation-program.md) · [owner decisions](../capstone-report/owner-decisions-2026-09-27.md) · [handoff](../../audit/2026-09-25/handoff-2026-09-27-execution.md)
