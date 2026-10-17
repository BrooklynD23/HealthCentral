# LEGACY-CITE-PROMPT: Constrained Decoding for Legacy RAG Citations (RSI-3) — Implementation Plan

**Last Updated:** 2026-10-17
**Owner:** repository owner
**Status:** PROPOSED (Opus planner). Docs only. No owner approval is recorded here; gates keep their state in [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md).
**Base measured:** `origin/main` @ `3536cc6` (2026-10-17).
**Refresh Trigger:** any commit to `src/backend/modules/rag.py`, `src/backend/core/model_runner.py`, `src/backend/core/llm/`, `src/backend/core/external_runner.py`, `src/backend/tests/test_rag_citation_prompt.py`; RSI-T2-EVAL merging; an Ollama upgrade on the model host; an owner answer to a gate below.

**Queue row:** [queue.md](2026-10-15-build-program/queue.md) LEGACY-CITE-PROMPT. **Sources:** owner rows MERGE-72 (2026-10-16) and RSI-3 (2026-10-17, lands with #123): **"Yes: Ollama format schema / GBNF, gate unchanged"**, "Faithfulness gate unchanged; it still checks support."; handoff 2026-10-17 §2 item 4(b) (lands with #123); research `docs/research/2026-10-17-rsi-opt-in-data/03-small-model-citation-finetuning.md` options 1-2 and sources #8-#10 (land with #122); MM-1 results, #72 comments 6226130965 and 6228253080. **Acceptance instrument:** [RSI-T2-EVAL plan](2026-10-17-rsi-track2-eval-harness-plan.md).

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:test-driven-development. Domain skills: `asclexis-backend`, `asclexis-guardrails`.

## Goal

Small local models skip `[cite:N]` in REPORT FACTS and invent outside references. MM-1 shows 15-20/20 legacy answers abstained, with 11-20/20 failing on `Report facts section missing citations`. Make the model emit a structured answer whose every REPORT FACTS and GENERAL INFO item carries cite indices from the valid set `1..len(chunks)`, enforced by the provider's constrained decoding (Ollama `format` JSON schema; llama.cpp `response_format` schema, which llama.cpp compiles to a GBNF grammar). Render that structure deterministically back into the existing `REPORT FACTS: … [cite:N]` text, then run the **unchanged** `validate_response`, verifier, faithfulness threshold (0.6) and G-B5 abstain mapping on it.

## Non-negotiables

1. **The gate is unchanged.** No diff to `RAGModule.validate_response`, `_parse_response_segments`, `_build_validated_segments`, `_run_verification_pipeline`, `api/assistant.py::_legacy_serve_or_abstain`, or the ask-first `modules/faithfulness.py`, `modules/verifier_agent.py`, `modules/interpret_safety.py`. Constrained decoding only forces the *shape*. Support is still checked by the verifier and faithfulness scorer (research 03 #8: grammar constraints do not check faithfulness).
2. **ModelRunner / provider layer only** (CLAUDE.md §2, §3). The schema travels in `InferenceConfig`, and each provider inside `core/llm/` maps it to its native parameter. No new layer, no direct Ollama or `llama_cpp` call from `modules/rag.py`.
3. **D11 holds.** `[cite:N]` stays the only validated marker. `tests/test_rag_citation_prompt.py` HC-CIT-001…003 keep passing **unedited**: the prompt still has exactly one citation-format instruction line, and it names `[cite:N]`.
4. **Local-first.** Ollama stays localhost-only (`core/llm/ollama_provider.py:40`). `core/external_runner.py` is not edited. An external runner ignores the schema, and its prose answer passes through unchanged (Task 4).
5. **Fail as today, never more open.** If the output is not valid structured JSON, `_generate_with_runner` returns the raw text exactly as it does today, so behaviour equals `main`.

## Evidence (verified on `3536cc6`)

| Fact | Where |
|---|---|
| `SYSTEM_PROMPT` (the queue text says `:125`; it is now at `:139`) asks for `[cite:N]` and three sections | `src/backend/modules/rag.py:139-158` |
| `compose_prompt` labels chunks `[YOUR_RESULTS:i]` / `[SOURCE_TYPE:i]`, with `i` from 1 | `src/backend/modules/rag.py:618-691` |
| `validate_response`: citation regex `\[cite:(\d+)\]`, valid ids `1..len(chunks)`, `Report facts section missing citations`, prohibited patterns, verifier, faithfulness `< 0.6` | `src/backend/modules/rag.py:795-877` |
| `query` → `_generate_with_runner(prompt, runner)` → `validate_response(response, chunks)`. `runner` may be an `ExternalModelRunner` | `src/backend/modules/rag.py:1262-1278`, `:1280-1303` |
| `generate_response` (`:749-793`) has no product caller (only `query` generates) | `git grep -n "generate_response(" src/backend --` excluding tests |
| `rag.query` also serves `POST /interpretations/observations/{id}/interpret-grounded` | `src/backend/api/interpretations.py:529` |
| `InferenceConfig` fields: `max_tokens`, `temperature`, `top_p`, `stop_sequences`, `timeout_seconds`. No schema field | `src/backend/core/model_runner.py:31-38` |
| **The Ollama provider does not send `format` today.** `_build_request_body` sends `model`, `messages`, `stream`, `options` | `src/backend/core/llm/ollama_provider.py:130-142` |
| llama.cpp provider calls `create_chat_completion(messages, max_tokens, temperature, top_p, stop)`, with no `response_format` | `src/backend/core/llm/llama_cpp_provider.py:237-243` (`generate_async` runs `generate` in an executor, `:271-280`) |
| Segment parser falls back to one `general_info` segment when no header matches (relevant to Open gate LCP-HEADERLESS) | `src/backend/modules/rag.py:1060-1065` |
| Tests that mock `_generate_with_runner` return prose, so they never reach the renderer | `tests/test_safe_interp_grounded.py:95`, `tests/test_rag_pipeline.py:1117`, `tests/test_memory_integration.py:221` |
| Ollama on the model host is 0.40.5. Structured outputs take a JSON schema in `format` (research 03 #10; verify on the host, Task 0 step 4) | handoff §1 |

## Design

**Schema** (built per request, because the enum depends on the chunk count `n`):

```json
{"type": "object", "additionalProperties": false,
 "required": ["report_facts", "general_info", "uncertainties"],
 "properties": {
  "report_facts":  {"type": "array", "items": {"$ref": "#/$defs/item"}},
  "general_info":  {"type": "array", "items": {"$ref": "#/$defs/item"}},
  "uncertainties": {"type": "array", "items": {"type": "string", "maxLength": 400}}},
 "$defs": {"item": {"type": "object", "additionalProperties": false,
   "required": ["text", "cites"],
   "properties": {"text":  {"type": "string", "maxLength": 400},
                  "cites": {"type": "array", "minItems": 1, "maxItems": 3,
                            "items": {"type": "integer", "enum": [1, "…", "n"]}}}}}}
```

If `$ref` is not honoured by the installed Ollama grammar converter (Task 0 step 4), inline the item schema twice. Never drop `minItems` or the `enum`.

**Rendering** (`RAGModule._render_structured_answer(text: str, n_chunks: int) -> str | None`, pure):
- `json.loads`. If it fails, or does not match the schema (checked in code, not trusted from the provider), return `None`.
- Return `None` if any item `text` contains a section header (`REPORT FACTS`, `GENERAL INFO`, `UNCERTAINTIES`, case-insensitive) or the substring `[cite:`. A model must not forge markers or re-split sections inside a field.
- Otherwise emit `REPORT FACTS:\n- {text} [cite:a] [cite:b]` per item, then `GENERAL INFO:` the same way, then `UNCERTAINTIES:\n- {text}`. Empty sections are omitted. Newlines in `text` become spaces.
- If the result is `None`, `_generate_with_runner` returns the raw text (non-negotiable 5).

**Prompt.** One new block under the existing rules. It describes the JSON fields and says *"the `cites` numbers are the context numbers shown in brackets; use only facts and references that appear in CONTEXT; do not name outside organisations, guidelines or URLs"* (the MERGE-72 "ban on outside sources"). It gains no line that has both a cite-word and a bracketed `[NAME:N]` marker (HC-CIT-001). The existing `[cite:N]` line stays as the single format instruction. Rule 7 (`I don't have enough information`) maps to `uncertainties` with empty facts.

**Where the schema goes.**
- `InferenceConfig.response_schema: Optional[dict] = None` (appended field; default keeps every caller unchanged).
- `OllamaProvider._build_request_body` adds `"format": config.response_schema` when it is set.
- `LlamaCppProvider.generate` passes `response_format={"type": "json_object", "schema": config.response_schema}` when it is set (llama-cpp-python compiles the schema to GBNF).
- `ExternalModelRunner` is untouched and simply never reads the field.
- `getattr(config, "response_schema", None)` in providers, so a duck-typed config from tests keeps working.

## Files

| File | Change |
|---|---|
| `src/backend/core/model_runner.py` | append `response_schema` to `InferenceConfig` |
| `src/backend/core/llm/ollama_provider.py` | `format` in `_build_request_body` |
| `src/backend/core/llm/llama_cpp_provider.py` | `response_format` in `create_chat_completion` (both `generate` and the async path that delegates to it) |
| `src/backend/modules/rag.py` | `_cite_schema(n)`, `_render_structured_answer`, prompt block, `_generate_with_runner` passes the schema and renders |
| `src/backend/tests/test_llm_structured_output.py` | new: HC-LCP-001…003 |
| `src/backend/tests/test_rag_structured_cite.py` | new: HC-LCP-004…010 |
| slots | none (contracts §d) |

**Shared-file order (contracts §b):** `modules/rag.py` is on the chain #95 → W-3 → W-8 → G-C5, with B-3 floating. LEGACY-CITE-PROMPT never runs at the same time as W-3, W-8, G-C5 or B-3. The second lander merges `origin/main` and re-anchors by symbol. `core/model_runner.py` and `core/llm/*` have no other open claimant in the queue today; re-check at claim time.

## Tasks (test-first)

### Task 0: Re-verify (STOP on any mismatch)

1. `git grep -n "class InferenceConfig" -A8 src/backend/core/model_runner.py`: no schema field yet.
2. `git grep -n "_build_request_body" -A14 src/backend/core/llm/ollama_provider.py`: no `format` key.
3. Read HC-CIT-001…003 in full and note the exact line rules the prompt block must obey.
4. **Model host (owner/model-machine, 5 min):** one localhost call `POST /api/chat` with `format` set to the schema above (n = 6) on each of the four models. Record whether the output parses and whether `enum`, `minItems` and `$ref` were honoured. If Ollama 0.40.5 rejects or ignores the schema on any model, STOP and report. Do not loosen the schema.
5. RSI-T2-EVAL is merged, and its baseline run on `main` is posted. Without it there is no "before" (recurring-failures §3).

### Task 1: Provider plumbing (HC-LCP-001…003)

- **HC-LCP-001:** `OllamaProvider._build_request_body(msgs, InferenceConfig(response_schema=S))["format"] == S`. With no schema, `"format"` is absent (the body is byte-identical to `main` for every existing caller).
- **HC-LCP-002:** `LlamaCppProvider.generate` with a fake `_model` records `response_format == {"type": "json_object", "schema": S}`. Without a schema, the kwarg is absent.
- **HC-LCP-003:** `ModelRunner.generate_async` forwards the same `InferenceConfig` object to the provider (fake provider spy).

RED, then GREEN; commit per task.

### Task 2: Schema and renderer (HC-LCP-004…007), pure unit tests

- **HC-LCP-004:** `_cite_schema(6)` puts enum `[1..6]` and `minItems: 1` on `cites`, and `additionalProperties: false` at both levels.
- **HC-LCP-005:** a valid structured answer renders to text whose `_parse_response_segments` yields a `report_facts` segment containing `[cite:1]`, and `validate_response` reports no `Report facts section missing citations`.
- **HC-LCP-006:** each of these returns `None`: not JSON; schema-invalid (`cites: []`, `cites: [7]` with n = 6, extra key); an item text containing `GENERAL INFO:`; an item text containing `[cite:2]`.
- **HC-LCP-007:** prose input (what `ExternalModelRunner` and every existing test mock return) returns `None`, and `_generate_with_runner` then returns the input unchanged.

### Task 3: Gate-unchanged proof through HTTP (HC-LCP-008…010)

Use `tests/legacy_eval/harness.py::legacy_chat_client` (route_client, real `validate_response`, verifier on). Its `FakeRunner` returns the JSON string.

- **HC-LCP-008:** a structured answer whose fact `Glucose: 95 mg/dL` cites the glucose chunk is **served** (`is_valid`, segment citations non-empty).
- **HC-LCP-009 (could fail):** a structured answer that cites a valid chunk but states an unsupported claim (`Glucose: 140 mg/dL, which indicates diabetes` citing chunk 1) is **abstained** or escalated, with a verifier/faithfulness or prohibited error in `validation_errors`. This proves the forced citation does not buy a pass. If this test passes before Task 2's renderer exists, it proves nothing: capture its RED as "renderer missing → raw JSON → …" and explain the transition in the PR.
- **HC-LCP-010:** HC-CIT-001…003, the `legacy-evals` golden suite and `tests/test_safe_interp_grounded.py` pass with **no edit** to those files: `git diff --stat origin/main...HEAD -- src/backend/tests/test_rag_citation_prompt.py src/backend/tests/legacy_eval src/backend/tests/test_safe_interp_grounded.py` prints nothing.

### Task 4: Wire it

`_generate_with_runner` builds `InferenceConfig(..., response_schema=_cite_schema(len(chunks)))`. It needs `chunks`, so `query` passes `len(chunks)` as a new keyword argument `n_chunks: Optional[int] = None`. When it is `None` there is no schema and no render, so other callers and mocks are unchanged. Then it calls `_render_structured_answer`, falling back to raw text. The timeout branch is unchanged.

### Task 5: Measured acceptance (owner/model-machine step)

Run RSI-T2-EVAL on the PR head with `--baseline <main baseline JSON>` on all four models, with no pytest running, and paste the Markdown with its Δ columns. Also paste, for one model, 3 served answers verbatim (synthetic data) so a human can read that the served citations are real.

## Acceptance

```bash
cd src/backend
P="$(git rev-parse --show-toplevel)/scripts/pyslot.sh"; PY=~/venvs/asclexis-311/bin/python
$P env HF_HUB_OFFLINE=1 $PY -m pytest tests/test_llm_structured_output.py tests/test_rag_structured_cite.py -p no:cacheprovider -q   # RED per id first, then 10 passed
$P env HF_HUB_OFFLINE=1 $PY -m pytest tests/test_rag_citation_prompt.py tests/legacy_eval tests/test_safe_interp_grounded.py tests/test_rag_pipeline.py -p no:cacheprovider -q   # unchanged files, all pass
$P env HF_HUB_OFFLINE=1 $PY -m pytest tests/ -p no:cacheprovider -q | tail -3   # full suite: no new failures vs baseline; report collected + delta
git diff origin/main...HEAD -- src/backend/modules/faithfulness.py src/backend/modules/verifier_agent.py src/backend/modules/interpret_safety.py src/backend/modules/redaction.py src/backend/core/external_runner.py src/backend/api/assistant.py   # must print nothing
git diff origin/main...HEAD -- src/backend/modules/rag.py | grep -nE "^[-+].*(def validate_response|0\.6|faithfulness_score|citation_pattern|_parse_response_segments)"   # must print nothing
```

Plus the Task 5 Δ table. **Before/after counts are reported as measured. This plan sets no pass threshold** (see LCP-ACCEPT).

## Gates

| Gate | State | Governs |
|---|---|---|
| RSI-3 | answered 2026-10-17 (lands with #123) | approach |
| MERGE-72 | answered 2026-10-16 | item exists; prompt bans outside sources |
| D11 | answered | `[cite:N]` only; HC-CIT unchanged |
| AUTO-MERGE | answered (lands with #123) | agent may merge if green and review-approved; LCP-ACCEPT below still needs the owner |
| **LCP-ACCEPT** | **open** | merge decision on the Task 5 numbers |
| **LCP-HEADERLESS** | **open** (finding, not in scope) | a possible follow-up row |

## Ask-first

None of the ask-first files is edited, and the acceptance `git diff` proves it. `modules/rag.py` is not ask-first, but this change alters what the model is asked to produce on a patient-facing safety path. The reviewer checks HC-LCP-009 and the unchanged-gate diff first. If any task seems to need an edit to `validate_response` or a threshold, STOP and ask (CLAUDE.md §3).

## Open owner gates (exact wording)

1. **LCP-ACCEPT:** "After constrained decoding, RSI-T2-EVAL will show before/after abstain and cited-answer counts for the four local models, with the faithfulness gate unchanged. What result lets LEGACY-CITE-PROMPT merge? (a) Merge if the abstain count falls on at least one model, no model's cite-value mismatches rise, and the gate diff is empty (Recommended). (b) Merge only if every model improves. (c) You review the numbers and the 3 sample answers each time, with no fixed rule."
2. **LCP-HEADERLESS** (found while planning; not fixed here, validator unchanged): "`_parse_response_segments` treats a response with no section headers as one GENERAL INFO segment, so the 'Report facts section missing citations' check never runs on it; only the verifier and faithfulness checks do. Do you want a separate ask-scoped row to look at this? (a) Yes, plan it as its own item (Recommended). (b) No, the verifier and faithfulness checks are enough."

## Risks

- **A forced citation on an unsupported sentence.** It is mitigated by the unchanged verifier and faithfulness checks (HC-LCP-009) and by RSI-T2-EVAL's cite-value mismatch diagnostic. This is the main risk. Constrained decoding raises the share of answers that reach the support check; it does not make them true.
- **Ollama 0.40.5 schema support differs by model:** Task 0 step 4 measures it per model before any code is written.
- **Latency:** grammar-constrained decoding can be slower. RSI-T2-EVAL reports p50/p95, and a rise in `timeout` count is reported, not hidden.
