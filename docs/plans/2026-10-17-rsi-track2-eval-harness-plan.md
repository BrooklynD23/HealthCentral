# RSI-T2-EVAL: Track-2 Eval Harness (Legacy Cite Eval) — Implementation Plan

**Last Updated:** 2026-10-17
**Owner:** repository owner
**Status:** PROPOSED (Opus planner). Docs only. No owner approval is recorded here; gates keep their state in [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md).
**Base measured:** `origin/main` @ `3536cc6` (2026-10-17).
**Refresh Trigger:** any edit to `src/backend/tests/legacy_eval/harness.py`, `src/backend/api/assistant.py` (`_legacy_serve_or_abstain`, `ChatResponse`), `src/backend/modules/rag.py` (`_generate_with_runner`, `validate_response`), `src/backend/core/model_runner.py`; LEGACY-CITE-PROMPT merging; the owner answering OW-3 (sealed set S5).

**Queue row:** [queue.md](2026-10-15-build-program/queue.md) RSI-T2-EVAL. **Sources:** session handoff 2026-10-17 §2 item 4(a) and §1 MM-1 (`docs/plans/2026-10-17-session-handoff.md`, lands with #123); owner rows RSI-3, RSI-4, RSI-BUILD (2026-10-17, land with #123); research package `docs/research/2026-10-17-rsi-opt-in-data/00-README.md` §C and `03-small-model-citation-finetuning.md` (land with #122); the MM-1 script, PR #72 comment 6116808120; MM-1 results, #72 comments 6226130965 and 6228253080.

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:test-driven-development. Domain skills: `asclexis-evals`, `asclexis-backend`.

## Goal

Turn the throw-away MM-1 count script into a committed, tested eval harness for the legacy RAG chat path. Run it on the four local Ollama models and get two headline metrics per model: **abstain rate** and **cited-answer rate**. Write the results as JSON and as Markdown. This harness is the Track-2 (app agent) measurement for RSI-4, and it is the acceptance instrument for LEGACY-CITE-PROMPT ([plan](2026-10-17-legacy-cite-prompt-constrained-decoding-plan.md)).

## Scope

**Does:**
- Add `src/backend/scripts/legacy_cite_eval.py`. It drives the real `POST /assistant/chat` legacy route over HTTP through `tests/legacy_eval/harness.py::legacy_chat_client`, exactly as MM-1 did: fixed synthetic chunks, retrieval faked, the external-runner lookup patched to `None` so the real `ModelRunner` generates.
- Add the MM-1 question set and chunks, copied verbatim, as a versioned synthetic fixture, so the new numbers compare with the MM-1 baseline.
- Run one subprocess per model, because `core.config.settings` reads `LLM_PROVIDER`/`LLM_MODEL` once at import. Merge the per-model JSON into one report plus a Markdown table, with an optional delta column against a baseline JSON.
- Refuse to run under pytest. The real-model run is an owner/model-machine step.
- Provide a `--sealed` mode for a question file kept outside the repo (OW-3 / S5). It writes counts and the file's sha256 only, never question or response text. **The S5 gate itself is later.** This plan only adds the hook.

**Does NOT:**
- Change any product code. No edit to `modules/rag.py`, `api/assistant.py`, `core/`, or any ask-first module (`interpret_safety.py`, `redaction.py`, `faithfulness.py`, `verifier_agent.py`).
- Change `tests/legacy_eval/harness.py`, the golden cases, `scripts/legacy_eval_gate.py` or the `legacy-evals` CI job. The harness is imported read-only.
- Add a CI job. The real-model run never runs in CI or in pytest.
- Measure the agent chat path. It never calls the LLM (RSI-Q3), so there is nothing to measure here.

## Evidence (verified on `3536cc6`)

| Fact | Where |
|---|---|
| MM-1 script is not committed. It lives only in PR #72 comment 6116808120 and imports `tests.legacy_eval.harness` (`CHAT_PATH`, `legacy_chat_client`) and `ABSTAIN_TEMPLATE`/`ESCALATE_TEMPLATE` | `gh api repos/BrooklynD23/HealthCentral/issues/comments/6116808120` |
| `legacy_chat_client(chunks, model_output, finish_reason)` patches `core.external_runner.get_runner_for_request` to a `FakeRunner`. MM-1 overrode that patch with `AsyncMock(return_value=None)` to reach the real runner | `src/backend/tests/legacy_eval/harness.py:89-135` |
| Abstain shape is `full_response == "**UNCERTAINTY**\n" + ABSTAIN_TEMPLATE`. Escalate is `ESCALATE_TEMPLATE`. No-model fallback contains `knowledge base only` | MM-1 script `classify` block |
| `ChatResponse` carries `segments` (each with `citations`), `full_response`, `is_valid`, `validation_errors` | `src/backend/api/assistant.py:147-159` |
| A runner timeout returns the fixed `UNCERTAINTIES:\nI was unable to fully process…` text, which MM-1 did not count separately | `src/backend/modules/rag.py:1297-1300` |
| `settings.llm_provider` / `llm_model` come from env at settings construction | `src/backend/core/config.py:102-115` |
| Default pytest collection is `test_*.py`. A file named `legacy_cite_eval.py` is not collected, and no `python_files` override exists | `src/backend/pyproject.toml` (no pytest section) |
| Prior art for a read-only measurement script under `src/backend/scripts/` | `src/backend/scripts/measure_prohibited_patterns.py:1-25` |
| MM-1 baseline (Ollama 0.40.5, RTX 3080, branch `18661db`): abstained `gemma4:e4b` 20/20, `llama3.1:8b` 20/20, `gemma3:12b` 19/20, `qwen3:8b` 15/20; `Report facts section missing citations` 19 / 19 / 20 / 11 | #72 comment 6228253080 |
| Running pytest at the same time inflates abstain counts (60 s generation timeout) | handoff §4 |

## Metric definitions (frozen by this plan)

Every rate has the question count `N` as its denominator and is reported next to the raw count.

| Kind (one per question) | Rule, applied in order |
|---|---|
| `no_model` | `full_response` contains `knowledge base only` |
| `timeout` | `full_response` contains `unable to fully process your question within the time limit` |
| `escalated` | `full_response == ESCALATE_TEMPLATE` |
| `abstained` | `full_response == "**UNCERTAINTY**\n" + ABSTAIN_TEMPLATE` |
| `answered_cited` | none of the above, and at least one segment has a non-empty `citations` list |
| `answered_uncited` | none of the above, and no segment has citations |

- **abstain rate** = `abstained / N`.
- **cited-answer rate** = `answered_cited / N`.
- Also reported: escalate, timeout, no-model and uncited-answer counts; a `validation_errors` histogram; p50/p95 latency per question; and one diagnostic.
- **Diagnostic: cite-value match.** For each `answered_cited` question, take every number in a `report_facts` segment and check that it appears in the text of a chunk that segment cites. Report the number of segments where this fails. This is a smoke check for a citation that points at the wrong chunk. It is not a faithfulness gate, and it never changes the kind.
- A run whose `no_model` count is above 0 exits 1, as MM-1 did, so a run that never reached the model cannot be reported as a result.

## Files

| File | Change |
|---|---|
| `src/backend/scripts/legacy_cite_eval.py` | new: CLI, `classify`, `run_questions`, `summarise`, `render_markdown`, pytest guard, sealed mode, per-model subprocess loop |
| `src/backend/tests/fixtures/legacy_cite_eval/questions_v1.json` | new: the 20 MM-1 questions and 6 MM-1 lab chunks, verbatim, with `"version": 1` and a note that they are synthetic |
| `src/backend/tests/test_legacy_cite_eval.py` | new: HC-T2E-001…008 |
| slots | none (PRs never edit slots, contracts §d) |

Imports are read-only: `tests.legacy_eval.harness`, `modules.agent.guardrails.templates`, `modules.rag.RetrievedChunk`, `core.model_runner.get_model_runner`.

## Tasks (test-first)

### Task 0: Re-verify

1. `git grep -n "def legacy_chat_client\|CHAT_PATH" src/backend/tests/legacy_eval/harness.py`: the signature is unchanged from the evidence table. If it changed, STOP and re-plan the import.
2. `git grep -n "ABSTAIN_TEMPLATE\|ESCALATE_TEMPLATE" src/backend/modules/agent/guardrails/templates.py`: both exist.
3. Measure collected (contracts §d step 2) and record it with its delta from the slot.

### Task 1: Fixture plus classifier (HC-T2E-001, 002)

- **HC-T2E-001:** `classify(body)` returns each of the six kinds for six hand-built `ChatResponse`-shaped dicts. The order rule is pinned: a body that is both `timeout`-text and has citations is `timeout`.
- **HC-T2E-002:** loading `questions_v1.json` gives exactly 20 questions and 6 chunks, and a sha256 equal to the one recorded in the test. Changing the fixture must be a visible test edit, never a silent drift from the MM-1 baseline.

RED: the module does not exist (`ModuleNotFoundError`). GREEN: write `classify` and the loader. Commit `test(eval): ...` then `feat(eval): ...`.

### Task 2: Run through the real route with a fake runner (HC-T2E-003, 004)

`run_questions(questions, chunks, runner_patch=None)` loops over questions inside `legacy_chat_client`. When `runner_patch` is `None` (CLI) it patches `get_runner_for_request` to `None`, as MM-1 does. In tests it passes the harness `FakeRunner`.

- **HC-T2E-003 (can fail both ways):** a `FakeRunner` returning a correctly cited answer (`REPORT FACTS:\nGlucose: 95 mg/dL [cite:1]\n…` built from chunk 1) gives `answered_cited == 20`. A `FakeRunner` returning the same text without `[cite:1]` gives `abstained == 20` and `validation_errors["Report facts section missing citations"] == 20`. This shows the metric is driven by the real `validate_response` and the G-B5 mapping, and is not hard-wired (recurring-failures §1).
- **HC-T2E-004:** `summarise(per_question)` returns `schema_version`, `model`, `n`, a count for every kind, `abstain_rate`, `cited_answer_rate`, `validation_errors`, `latency_ms_p50`, `latency_ms_p95` and `cite_value_mismatch`. The rates equal count / n.

**Verification on:** for the real-model path, the harness's `RAGModule.enable_verification` is the product default (`True`), so the faithfulness gate is part of what is measured.

### Task 3: Report writers (HC-T2E-005, 008)

- **HC-T2E-005:** `render_markdown(report, baseline=None)` gives one row per model, with columns *model, abstained, cited, uncited, escalated, timeout, no-model, abstain rate, cited-answer rate, cite-value mismatches*. With a baseline JSON it adds `Δ abstain` and `Δ cited` columns. A model missing from the baseline shows `—`, never 0.
- **HC-T2E-008:** cite-value match. A cited answer whose number (`96`) is not in the cited chunk (`95`) counts 1 mismatch. The matching answer counts 0.

### Task 4: Guards (HC-T2E-006, 007)

- **HC-T2E-006:** `main([...])` returns exit code 3 and never calls `get_model_runner` while `PYTEST_CURRENT_TEST` is set. Message: `refusing to run a real-model eval inside pytest`. The test sets the variable itself (it is already set under pytest) and asserts on a spy.
- **HC-T2E-007:** `--sealed --questions <tmp path>` writes JSON and Markdown that contain no question text, no `full_response` text and no chunk text: only counts, rates, the error histogram and `questions_sha256`. The test greps the output for every question string.

### Task 5: CLI and per-model loop

```
python scripts/legacy_cite_eval.py \
  --models gemma4:e4b,llama3.1:8b,qwen3:8b,gemma3:12b \
  --out-dir <dir> [--baseline <json>] [--questions <json>] [--sealed] [--repeats 1]
```

- `--out-dir` is required, with no default inside the repo, so no result file is ever written into the tracked tree by accident.
- For each model the parent re-invokes itself as `--one-model <id> --json-out <dir>/<model>.json`, with `LLM_PROVIDER=ollama`, `LLM_MODEL=<id>`, `TEST_MODE=1` and `HF_HUB_OFFLINE=1` set in the child env. The child makes one untimed warm-up generation (MM-1 lost Q1 to a cold-load timeout), then the N questions.
- The parent writes `<dir>/legacy_cite_eval.json` (all models, plus `git_sha`, `ollama_version` read from `ollama --version`, `questions_sha256` and the UTC timestamp from `core.time.utcnow`) and `<dir>/legacy_cite_eval.md`.
- No network beyond the existing localhost-only Ollama provider (`core/llm/ollama_provider.py:40` `_assert_localhost`).

No new test for the subprocess loop (it needs a model). Task 6 is its evidence.

### Task 6: Model-machine run (owner / model-machine step; not part of the PR's CI)

On the owner's RTX 3080 WSL box (MM-HOST), with no pytest running (handoff §4):

```bash
cd src/backend
~/venvs/asclexis-311/bin/python scripts/legacy_cite_eval.py \
  --models gemma4:e4b,llama3.1:8b,qwen3:8b,gemma3:12b \
  --out-dir ~/asclexis-evals/t2e-$(git rev-parse --short HEAD)
```

Paste `legacy_cite_eval.md` and the RESULT lines on the PR. The first run on unchanged `main` is the **committed baseline**: compare it with the MM-1 numbers above. A difference of more than 2/20 on any model is reported, not explained away (recurring-failures §4). Expected runtime is 5-20 minutes per model.

## Acceptance

```bash
cd src/backend
"$(git rev-parse --show-toplevel)/scripts/pyslot.sh" env HF_HUB_OFFLINE=1 \
  ~/venvs/asclexis-311/bin/python -m pytest tests/test_legacy_cite_eval.py -p no:cacheprovider -q
# RED output per HC-T2E id first, then GREEN: 8 passed
"$(git rev-parse --show-toplevel)/scripts/pyslot.sh" env HF_HUB_OFFLINE=1 \
  ~/venvs/asclexis-311/bin/python -m pytest tests/ --collect-only -q -p no:cacheprovider | tail -1   # report delta (+8 expected; measure it)
~/venvs/asclexis-311/bin/python -m pytest tests/legacy_eval -p no:cacheprovider -q   # unchanged
PYTEST_CURRENT_TEST=x ~/venvs/asclexis-311/bin/python scripts/legacy_cite_eval.py --models x --out-dir /tmp/t2e; echo "exit=$?"   # exit=3
git diff --stat origin/main...HEAD -- src/backend/modules src/backend/api src/backend/core   # must print nothing
```

**Done** means all of the above pasted with output, plus Task 6's Markdown table for all four models, posted by the owner or the model-machine runner. Until Task 6 is posted, the PR body says `real-model numbers: UNMEASURED`.

## Gates

| Gate | State | Governs |
|---|---|---|
| RSI-4 (two tracks; Track 2 = app agent) | answered 2026-10-17 (lands with #123) | the item exists |
| MM-HOST | answered | Task 6 host |
| OW-3 (sealed set S5) | **open, owner-held** | a later run of `--sealed` on S5; this plan only adds the mode. No S5 result is claimed here |

No open owner gate blocks building this item.

## Ask-first

None edited. `tests/legacy_eval/harness.py` and the guardrail templates are imported read-only. If a test needs a harness change, STOP and ask (it is the `legacy-evals` gate's harness, contracts I-2).

## Risks

- **Model nondeterminism** (temperature 0.1): `--repeats N` reports the mean and the range, and a single run is labelled `repeats=1`.
- **Fixture drift from the MM-1 baseline:** pinned by HC-T2E-002's sha256.
- **Importing a test package from a script:** the same as MM-1. The script imports and never edits it. If `tests/` stops being importable, the script fails loudly and does not fall back.
