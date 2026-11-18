# 04 — Local LLM serving on laptops without a GPU

**Last Updated:** 2026-10-22
**Owner:** repository owner
**Refresh Trigger:** a tier in `modules/model_selector.py` changes; the `llama-cpp-python` pin changes; the B-3 advice judge merges; owner answers Q6 in [07-owner-questions.md](07-owner-questions.md).

> **Point-in-time research (2026-10-22).** Markers as in [00-README.md](00-README.md). All serving stays behind `ModelRunner` and the providers in `core/llm/` (CLAUDE.md §2-3). Ollama stays localhost-only.

## Today

- Providers: `LlamaCppProvider` (default) and `OllamaProvider` (localhost), via `core/llm/factory.py`.
- Tiers (`modules/model_selector.py`): low = Qwen2.5-0.5B, gemma4-e2b, gemma4-e4b, mid = Phi-4-mini, gemma4-12b, high = BioMistral-7B. Some repo paths are marked as placeholders in comments.
- Known issues (not repeated here): the `chat_format` 500, no model lock, no GPU-layer setting, and thinking models against the judge. See PR #297 and [lane B, JUDGE-THINK](../../plans/2026-10-15-build-program/lane-B-interpretation-eval.md) (owner answer 2026-10-22, "Think off now + research Laya": [owner-decisions row](../../capstone-report/owner-decisions-2026-09-27.md)).

## Runtimes

| Runtime | Licence | Latest | Windows/macOS | Notes |
|---|---|---|---|---|
| llama-cpp-python | MIT **[A]** | 0.3.36, 2026-10-01, **sdist only on PyPI** **[V]** | CPU wheels on the project index for 0.3.35/0.3.36, win_amd64 and macOS arm64 **[V]**; Metal and CUDA indexes **[A]** | current default; use the CPU wheel index at install time |
| llama.cpp server binaries | MIT **[A]** | builds b118xx (22 Oct) **[A]** | `bin-win-cpu-x64.zip`, `bin-macos-arm64.tar.gz` **[A]** | the GBNF and JSON-schema features below also apply here |
| Ollama | MIT **[A]** | — | Windows and macOS installers **[A]** | API: `think` (boolean or a level), `keep_alive` (default 5m; 0 unloads), `format` ("json" or a JSON schema) **[A]** (github.com/ollama/ollama/blob/main/docs/api.md, page reachable **[V]**) |
| llamafile | Apache-2.0 (llama.cpp parts MIT) **[A]** | — | Windows needs a `.exe` rename; files over 4 GB do not run on Windows **[A]** | not needed alongside llama-cpp-python |
| LM Studio | proprietary; terms bar redistribution and bundling **[A]** | — | — | **never bundle**; a stakeholder may install it for themselves |

## Small models (8-16 GB RAM, CPU)

| Model | Licence | Q4_K_M size | Notes |
|---|---|---|---|
| Phi-4-mini-instruct | MIT **[V]** | 2.49 GB (bartowski GGUF) **[A]** | already the "mid" tier. Not a thinking model. The B-3 judge preview gave 37 ALLOW / 3 BLOCK over 40 texts on llama.cpp, so it returns labels, where Ollama thinking models returned none ([lane B](../../plans/2026-10-15-build-program/lane-B-interpretation-eval.md), JUDGE-THINK item 3) |
| Qwen3-4B | Apache-2.0 **[V]** | 2.5 GB **[A]** | hybrid thinking (`/think`, `/no_think`, `enable_thinking`) **[A]**; needs `think=false` handled first (B-3 / JUDGE-THINK) |
| Qwen2.5-1.5B-Instruct | Apache-2.0 **[V]** | 1.12 GB **[A]** | 8 GB tier; stronger than today's 0.5B low tier **[U]** |
| Gemma 4 E2B | Apache-2.0 **[V]** | — | Gemma 3 is under the Gemma Terms (not OSI) **[A]** |
| SmolLM3-3B | Apache-2.0 **[A]** | — | thinking toggle |
| Llama 3.2 3B | Llama 3.2 Community Licence (700M MAU clause, attribution) **[A]** | — | avoid for bundling |

No primary source gives CPU tokens per second. Secondary reports put 3-4B Q4 models at about 10-20 tok/s on desktop CPUs **[U]**. Measure with `llama-bench` on one target laptop before quoting a number.

## Guardrail classifiers and structured labels

| Option | Licence | Size | Notes |
|---|---|---|---|
| JSON-schema enum / GBNF alternation | MIT (llama.cpp, Ollama) | — | llama-server takes `json_schema` on completion endpoints and `response_format` on `/chat/completions`; GBNF via `grammar` **[A]**. Unsupported schema features are skipped silently, so keep the schema to a plain enum **[A]**. This is the cheapest way to make `ALLOW`/`BLOCK` reliable |
| IBM Granite Guardian 3.2 3B-A800M | Apache-2.0 **[V]** | 3B | harm risks plus RAG groundedness **[A]** |
| protectai deberta-v3-base-prompt-injection-v2 | Apache-2.0 **[A]** | 0.2B, ONNX available | English only; the project is archived **[A]** |
| Llama Guard 3 1B | Llama 3.2 licence **[A]** | 1B | licence limits |
| ShieldGemma 2B | Gemma Terms **[A]** | 2B | licence limits |

Any classifier added as a guard is a safety-semantics change and goes through the guardrail owner gates. This file does not propose one.

## Recommendation

- CPU default candidate: **Phi-4-mini Q4_K_M** (MIT, already a tier, not a thinking model). 8 GB fallback: **Qwen2.5-1.5B Q4_K_M**. Owner Q6.
- Install llama-cpp-python from the CPU wheel index in the launchers.
- When the B-3 judge lands, constrain its output with an enum schema or grammar through the provider's `InferenceConfig`, not a new layer.

## Sources

- https://pypi.org/project/llama-cpp-python/ ; https://github.com/abetlen/llama-cpp-python ; https://abetlen.github.io/llama-cpp-python/whl/cpu/llama-cpp-python/
- https://github.com/ggml-org/llama.cpp/releases ; https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md
- https://github.com/ollama/ollama/blob/main/docs/api.md ; https://ollama.com/download
- https://lmstudio.ai/app-terms ; https://github.com/Mozilla-Ocho/llamafile
- https://huggingface.co/microsoft/Phi-4-mini-instruct ; https://huggingface.co/bartowski/microsoft_Phi-4-mini-instruct-GGUF
- https://huggingface.co/Qwen/Qwen3-4B-GGUF ; https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF
- https://huggingface.co/google/gemma-4-E2B-it ; https://huggingface.co/google/gemma-3-4b-it ; https://huggingface.co/HuggingFaceTB/SmolLM3-3B ; https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct
- https://huggingface.co/ibm-granite/granite-guardian-3.2-3b-a800m ; https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2 ; https://huggingface.co/meta-llama/Llama-Guard-3-1B ; https://huggingface.co/google/shieldgemma-2b
