# QWEN3-4B-TIER: Qwen3-4B vs Phi-4-mini on CPU (measurement only)

**Last Updated:** 2026-10-28
**Owner:** repository owner
**Status:** Partly met. Measured on CPU here: the judge preview, the chat subset and peak RSS. Not met: (1) `llama-bench` pp and tg at 4 and 8 threads for both models. That needs the owner to allow building the vendored llama.cpp, or to supply a prebuilt `llama-bench` binary. (2) A pp512 re-run on a quiet box. The first set was measured on a loaded box, and its pp512 cells are marked not usable for comparison. The original 2026-10-22 40-text judge set is unavailable, so the judge rows here cannot be compared with that run. No product code, test, config, flag or default changed. No pytest run. No queue, count slot or ask-first file edited. No recommendation is made here: CPU-MODEL-FINAL decides which model becomes the long-term CPU default from this table.
**Refresh Trigger:** a change to the GGUF files or their pinned commits, to `held_out_dev.json`, to the judge prompt or its parser, to the chat prompts, or to `JUDGE-THINK` (`InferenceConfig.think`).

Plan: [QWEN3-4B-TIER](../../plans/2026-10-22-mvp-rows-plan.md#qwen3-4b-tier--measure-qwen3-4b-on-cpu-as-the-candidate-long-term-default-no-product-code). Queue row: [queue.md](../../plans/2026-10-15-build-program/queue.md) (`QWEN3-4B-TIER`). Judge context: [judge research](../../research/2026-10-22-judge-laya/00-README.md). Baseline for the KV and MM-4 prompts: [kv-prefix-measure.md](../2026-10-22/kv-prefix-measure.md) and [kv-numctx-verify](../2026-10-27/).

## Verdict

- Both models ran on the same box, the same day, CPU only (`CUDA_VISIBLE_DEVICES=` and `n_gpu_layers=0`). Every model call was held under the pyslot locks (`/tmp/claude-1000/hold_slots.sh`). `quiet-box.lock` was absent before every wrapped call.
- Thinking was off for both models. For Qwen3-4B the GGUF template was rendered with `enable_thinking=False`, so the prompt ends in an empty think block. No output of either model contained a `<think>` tag.
- Qwen3-4B blocked all 20 must-block items of the judge sample (19 BLOCK, 1 over the 2 s clock) and blocked 2 of 20 must-allow items. Phi-4-mini returned ALLOW for 3 of 20 must-block items and blocked 4 of 20 must-allow items. This is a 40-text dev sample, not S5 (see deviations 2 and 3).
- All ten chat answers (5 per model) were valid JSON with finish_reason `stop`. No cited ID fell outside the labels in its prompt.
- Peak RSS is 5.67 GiB for Qwen3-4B and 5.00 GiB for Phi-4-mini. These include the KV cache at `n_ctx` 8192.

## Measurements

One table, both models, same machine, same day. Throughput numbers come from llama-cpp-python 0.3.35 timing, not from `llama-bench` (deviation 1). Values in brackets are the individual repetitions.

| Measure (CPU only, same box, same day) | Qwen3-4B Q4_K_M | Phi-4-mini Q4_K_M |
|---|---|---|
| pp512, tok/s, 4 threads (mean of 3; reps) | 94.4 (90.6, 92.4, 100.1), loaded box, not usable for comparison | 68.3 (99.2, 65.7, 40.0), loaded box, not usable for comparison |
| pp512, tok/s, 8 threads (mean of 3; reps) | 92.3 (97.5, 98.0, 81.5), loaded box, not usable for comparison | 99.5 (106.0, 98.7, 93.9), loaded box, not usable for comparison |
| tg128, tok/s, 4 threads (mean of 3; reps) | 13.00 (13.03, 13.09, 12.87) | 13.17 (12.80, 13.32, 13.37) |
| tg128, tok/s, 8 threads (mean of 3; reps) | 13.53 (13.53, 13.46, 13.61) | 14.40 (14.42, 14.36, 14.43) |
| Judge, 40 texts, production 2 s clock: ALLOW / BLOCK / UNAVAILABLE | 18 / 21 / 1 | 19 / 19 / 2 |
| Judge, must_block (20): ALLOW / BLOCK / UNAVAILABLE | 0 / 19 / 1 | 3 / 15 / 2 |
| Judge, must_allow (20): ALLOW / BLOCK / UNAVAILABLE | 18 / 2 / 0 | 16 / 4 / 0 |
| Judge, UNAVAILABLE by reason (clock over 2 s / unparseable) | 1 / 0 | 2 / 0 |
| Judge caveat, 2 s clock: the UNAVAILABLE rows were raw BLOCK replies that ran over the clock (none unparseable) | 1 of 1 raw BLOCK over the clock | 2 of 2 raw BLOCK over the clock |
| Judge, raw labels with no clock (ALLOW / BLOCK / other) | 18 / 22 / 0 | 19 / 21 / 0 |
| Judge, seconds per call, median (min to max) | 0.94 (0.70 to 2.49) | 0.65 (0.39 to 2.45) |
| Chat a, a2, c, c2, d: finish_reason | stop, stop, stop, stop, stop | stop, stop, stop, stop, stop |
| Chat: answer parsed as JSON | 5 of 5 | 5 of 5 |
| Chat: completion tokens (a, a2, c, c2, d) | 148, 120, 166, 471, 466 | 114, 115, 111, 100, 590 |
| Chat: answer characters (a, a2, c, c2, d) | 629, 491, 664, 1579, 1638 | 435, 438, 423, 386, 2294 |
| Chat: cites / invalid cites / `[cite:N]` text markers | 36 / 0 / 0 | 18 / 0 / 0 |
| Chat: wall seconds (a, a2, c, c2, d); load-sensitive, see Machine | 52.6, 37.1, 74.4, 95.7, 123.5 | 47.6, 37.8, 48.6, 49.2, 122.6 |
| `<think>` tags in output (judge / chat) | 0 / 0 | not a thinking model: 0 / 0 |
| Peak RSS, whole process, highest of five runs | 5,949,328 KB (5.67 GiB) | 5,245,524 KB (5.00 GiB) |

Reading the judge rows. The B-3 rule is exact `ALLOW` or `BLOCK`, anything else `UNAVAILABLE`, with a 2 s wall-clock limit (`FROZEN_PROMPT`, `JUDGE_TIMEOUT_S`). Fail-closed reading, where UNAVAILABLE counts as a block as it does in the app:

- Must-block blocked (fail-closed): Qwen3-4B 20 of 20 (95% Wilson interval 0.839 to 1.000). Phi-4-mini 17 of 20 (0.640 to 0.948); its 3 ALLOW answers are dev indices 135, 144 and 153 of the must-block list.
- Must-allow blocked: Qwen3-4B 2 of 20 (0.028 to 0.301; dev indices 63 and 99 of the must-allow list). Phi-4-mini 4 of 20 (0.081 to 0.416; indices 18, 27, 45 and 63).
- Clock: Qwen3-4B's one UNAVAILABLE is the first timed call after the warm-up (must-block index 0, 2.49 s). Phi-4-mini's two are must-block indices 0 (2.09 s) and 18 (2.45 s).

## Step 0: setup check through ModelRunner

Run from `src/backend` with `~/venvs/asclexis-311/bin/python`, env `LLM_PROVIDER=ollama LLM_MODEL=llama3.1:8b`, via `core.model_runner.ModelRunner().generate` (default `InferenceConfig` apart from `max_tokens=8, temperature=0.0`). The provider is `core/llm/factory.py` `get_provider()`. This step ran on the GPU through Ollama. It checks that the app's facade answers. The CPU-only rule applies to the measurements below.

```text
provider OllamaProvider model llama3.1:8b
text= 'OK' | finish_reason= stop | model_name= llama3.1:8b | tokens_generated= 2
```

## Machine

- Host: WSL2 on Linux 6.6.114.1-microsoft-standard-WSL2 (`Danny-PC`).
- CPU: AMD Ryzen 9 5900X, 12 cores, 24 threads. RAM: 37 GiB.
- GPU present but not used: NVIDIA RTX 3080 10 GiB, driver 610.88. `llama_supports_gpu_offload()` returned `false` in this llama-cpp-python build.
- Ollama 0.40.5 (`ollama serve`, pid 881, left running and untouched). Used for step 0 only.
- Python 3.11.17 (`~/venvs/asclexis-311`), llama-cpp-python 0.3.35, numpy 2.4.6, jinja2 3.1.6.
- Load average during the first set of runs was high: 13.4 (1 min), 18.4 (5 min), 15.9 (15 min) at the end of those runs. A `vite build` and a `docs_lint.py` from another worktree (`hc-popover-open-cost`) were running during the check. They were not started or stopped by this run. Low prompt-processing repetitions appeared in that first set: Phi-4-mini 4-thread (65.7 and 40.0 tok/s against 99.2, so two of three reps are low) and Qwen3-4B 8-thread (81.5 tok/s against 97.5 and 98.0, so one low rep). Contention is the likely cause. The chat wall-seconds row is load-sensitive for the same reason.
- Ollama: step 0 loaded `llama3.1:8b` on the GPU. The Ollama default keep_alive is 5 minutes, so the model may have stayed in GPU memory after step 0. I did not unload it or stop Ollama. `ollama ps` run during re-run preparation showed no loaded model.
- Repo: `origin/main` `9d0dc2ad` at worktree creation. Branch `docs/qwen3-4b-tier`.

## Model provenance

Both files were fetched with `curl -L --fail -C -` from pinned commit URLs into `~/hc-models-scratch/` (outside the repo). The LFS size and sha256 from the Hugging Face tree API were compared with the local file. Both matched.

| Model | Repo and pinned commit | File | Bytes | sha256 | Licence |
|---|---|---|---|---|---|
| Qwen3-4B Q4_K_M | `Qwen/Qwen3-4B-GGUF` @ `bc640142c66e1fdd12af0bd68f40445458f3869b` | `Qwen3-4B-Q4_K_M.gguf` | 2497280256 | `7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5` | Apache-2.0 (repo card; upstream `Qwen/Qwen3-4B` is Apache-2.0) |
| Phi-4-mini Q4_K_M | `bartowski/microsoft_Phi-4-mini-instruct-GGUF` @ `7ff82c2aaa4dde30121698a973765f39be5288c0` | `microsoft_Phi-4-mini-instruct-Q4_K_M.gguf` | 2491874688 | `01999f17c39cc3074afae5e9c539bc82d45f2dd7faa3917c66cbef76fce8c0c2` | MIT (upstream `microsoft/Phi-4-mini-instruct` is MIT; the GGUF repo card carries no licence tag) |

The Phi-4-mini repo is the one `modules/model_selector.py` names for the mid tier (lines 86 to 110, which also state that the app needs llama-cpp-python 0.3.35).

## Exact commands

Every model call was wrapped individually, as `bash /tmp/claude-1000/hold_slots.sh <command>`, with a `test ! -e /tmp/claude-1000/quiet-box.lock` check before it. The helper `qwen_tier.py` (listed in the appendix) lives in `~/hc-models-scratch/scripts/`, outside the repo, and was run with `-I`. Model files were only read by it.

```text
# download (wrapped), both files, pinned commits
bash /tmp/claude-1000/hold_slots.sh curl -L --fail -C - -o ~/hc-models-scratch/qwen3-4b/Qwen3-4B-Q4_K_M.gguf "https://huggingface.co/Qwen/Qwen3-4B-GGUF/resolve/bc640142c66e1fdd12af0bd68f40445458f3869b/Qwen3-4B-Q4_K_M.gguf"
bash /tmp/claude-1000/hold_slots.sh curl -L --fail -sS -C - -o ~/hc-models-scratch/phi4-mini/microsoft_Phi-4-mini-instruct-Q4_K_M.gguf "https://huggingface.co/bartowski/microsoft_Phi-4-mini-instruct-GGUF/resolve/7ff82c2aaa4dde30121698a973765f39be5288c0/microsoft_Phi-4-mini-instruct-Q4_K_M.gguf"

# smoke, thinking off, CPU only (wrapped)
CUDA_VISIBLE_DEVICES= bash /tmp/claude-1000/hold_slots.sh ~/venvs/asclexis-311/bin/python -I ~/hc-models-scratch/scripts/qwen_tier.py smoke --model <gguf> --threads 8 --out <json>

# throughput, 4 and 8 threads, 3 reps after 1 warm-up (wrapped, each)
CUDA_VISIBLE_DEVICES= bash /tmp/claude-1000/hold_slots.sh /usr/bin/time -f "maxrss_kb=%M elapsed_s=%e" -o <rss> ~/venvs/asclexis-311/bin/python -I ~/hc-models-scratch/scripts/qwen_tier.py bench --model <gguf> --threads {4,8} --reps 3 --out <json>

# judge preview, 40 texts, thinking off, 8 threads (wrapped, each)
CUDA_VISIBLE_DEVICES= bash /tmp/claude-1000/hold_slots.sh /usr/bin/time -f "maxrss_kb=%M elapsed_s=%e" -o <rss> ~/venvs/asclexis-311/bin/python -I ~/hc-models-scratch/scripts/qwen_tier.py judge --model <gguf> --threads 8 --out <json>

# chat subset, thinking off, 8 threads, split in two calls per model (wrapped, each)
CUDA_VISIBLE_DEVICES= bash /tmp/claude-1000/hold_slots.sh /usr/bin/time -f "maxrss_kb=%M elapsed_s=%e" -o <rss> ~/venvs/asclexis-311/bin/python -I ~/hc-models-scratch/scripts/qwen_tier.py chat --model <gguf> --threads 8 --cases a,a2,c --out <json>
CUDA_VISIBLE_DEVICES= bash /tmp/claude-1000/hold_slots.sh /usr/bin/time -f "maxrss_kb=%M elapsed_s=%e" -o <rss> ~/venvs/asclexis-311/bin/python -I ~/hc-models-scratch/scripts/qwen_tier.py chat --model <gguf> --threads 8 --cases c2,d --out <json>
```

Raw JSON outputs (per-item judge rows, per-case chat text, RSS files) are in `~/hc-models-scratch/results/` on this box. They are not committed.

## Method

- **Throughput.** `bench`: pp512 is `eval` of 512 tokens after `reset`, timed. tg128 is `generate` of 128 greedy tokens with EOS banned, rate over tokens 2 to 128 after a 16-token prompt. One warm-up run, then three timed reps.
- **Judge.** The FROZEN_PROMPT text and the `neut()` marker rule come from `judge-laya/scripts2/ollama_judge.py`, read with `ast`, not retyped. Each text is one user message, rendered with the GGUF chat template. Thinking is off (`enable_thinking=False`). The call is `max_tokens` 3, temperature 0, top_p 0.9. An untimed warm-up runs first, as in `ollama_judge.py`. A verdict is `UNAVAILABLE` when the call takes over 2 s or the reply is not exactly `ALLOW` or `BLOCK`.
- **Chat.** The five prompts come from the 2026-10-27 KV-NUMCTX-VERIFY scratch `prompts.json` (sha256 `955a486cf967bb91b4b741a9c646b8fdba8219b964a2da6be3ab4e4b5dae895a`). They were built with the app's `OllamaProvider._build_request_body` on the synthetic MM-4-style profile (`synthetic-lab` PDFs, "Test Person"). The sampling options are copied from each request body (temperature 0.1, top_p 0.9, `num_predict` 1024). The request's `format` JSON schema is applied as a GBNF grammar. Citation validity counts each `cites` integer against the labels between `CONTEXT:` and `USER QUESTION` in that prompt. Text markers `[cite:N]` are counted separately.
- **Thinking off on llama.cpp.** `think=false` is an Ollama request field (`core/llm/ollama_provider.py:152`). `LlamaCppProvider` does not read `InferenceConfig.think`, so on llama.cpp the switch is in the template. For Qwen3-4B the smoke output shows the prompt ending in `<|im_start|>assistant\n<think>\n\n</think>\n\n`. The `<think>` token is one special id (151667), so the prefill is parsed as control text. Phi-4-mini's template has no thinking variable, so the same render gives its ordinary prompt.
- **Context.** `n_ctx` 8192 for every run. The default 4096 would truncate case d (4016 Qwen3 prompt tokens plus 1024 output). 8192 is the value `OLLAMA-NUM-CTX` already uses.
- **RSS.** GNU `time` `%M` on each whole process. This includes mapped model pages and the KV cache. The table reports the highest of the five runs for each model.

## Deviations from the plan

1. **`llama-bench` was not built or run.** The `llama-bench` binary needs the vendored llama.cpp from the llama-cpp-python 0.3.35 sdist (fetched to `~/hc-models-scratch/llama-cpp-python-src/`). Building it was refused by the auto-mode permission check as external code execution, and I did not retry it or route around the refusal. Substitute: llama-cpp-python 0.3.35 timing (`bench` above). This is the same llama.cpp library the app loads. The two models are comparable with each other; the numbers are not comparable with published `llama-bench` figures. Permission to build the sdist's vendored llama.cpp, or a prebuilt `llama-bench` binary, would let pp and tg at 4 and 8 threads be rerun as `llama-bench` for both models. That is the remaining part of the row.
2. **The 40-text judge set is not the 2026-10-22 set.** The `gpu-1022/judge_preview.py` script and its 40 texts are not on this box (`/tmp/claude-1000/gpu-1022` is absent), and `git grep` over all remote branches found only plan references to them. Substitute: `held_out_dev.json` (sha256 `63d59bb902095a691be176e9770e0c23db64a08e6e66288683c5b1319adabae5`, from this worktree at `origin/main`). The sample is every 9th item by list index: must_block indices 0, 9, ..., 171 (20 items) and must_allow indices 0, 9, ..., 171 (20 items). The 2026-10-22 llama.cpp result for Phi-4-mini (37 ALLOW, 3 BLOCK) is on another text set, so the two Phi-4-mini results are not comparable.
3. **The judge prompt is the JUDGE-LAYA mirror, not `origin/main`.** B-3 (#264) is not merged. `FROZEN_PROMPT` was read from `/tmp/claude-1000/judge-laya/scripts2/ollama_judge.py` (sha256 `bfd64273bd934dfb140d5f85836368403cec538a3ffade0ada7499d0dcab12f3`), the research mirror of #264 head `48a50b5`. Checked: `FROZEN_PROMPT` is byte-identical to the one in `git show 48a50b5:src/backend/modules/agent/guardrails/advice_judge.py` (877 characters; both parsed with `ast`, neither executed).
4. **Thinking off uses the template, not the request field.** On llama.cpp the call is `create_completion` with the template rendered by hand (`enable_thinking=False`), because `create_chat_completion` cannot pass that variable. The Phi-4-mini render was not separately compared with `create_chat_completion`.
5. **The MM-4 chat subset is not written down in the repo.** Five cases were used: a, a2, c, c2 and d from the 2026-10-27 scratch `prompts.json`. These are the lab-explanation and legacy-chat cases of the KV evidence. Case b (visit-note extraction) is not a chat question and was left out. The MM-4 question list itself was not located.
6. **The grammar controls the chat outputs.** Applying the request's JSON schema as a grammar forces a JSON object, so thinking could not appear in the chat outputs even without the switch. The chat rows therefore say little about thinking-off. The judge rows (no grammar) are the thinking-off test.
7. **Citation validity is counted on the schema path.** The app's `RAGModule.validate_response` checks `[cite:N]` text markers, which the schema-constrained answers do not use. Counts are integer `cites` against the labels in each prompt, plus a count of text markers (0 for both models).
8. **Threads.** The judge and chat runs used 8 threads. The plan does not name a thread count for them. Throughput ran at 4 and 8.
9. **Step 0 ran on the GPU.** It checks the facade through Ollama and is not part of the CPU measurement. Ollama may have kept `llama3.1:8b` in GPU memory afterwards (default keep_alive 5 minutes); I did not unload it.
10. **Judge "UNAVAILABLE" is split by cause.** The B-3 rule counts both clock timeouts and unparseable replies as `UNAVAILABLE`. Here only clock timeouts occurred (no unparseable replies), and the raw labels are shown without the clock.
11. **No re-run of the bench calls.** The pp512 and tg128 bench calls were not re-run on a quiet box, because the box stayed loaded during the UI build wave. The pp512 cells are marked as not usable for comparison. The monitor that waited for a quiet box was stopped after two readings, 9.46 at 09:08:31 and 5.23 at 09:09:29, both above the 1.5 threshold, so no quiet window was observed. The tg128 cells were run in the same loaded window. Their repetitions agree within about 0.6 tok/s, but they were not checked on a quiet box either.
12. **Box load.** The first set of CPU runs ran on a loaded box (load average 13 to 18, see Machine). The pp512 and tg128 figures, and the chat wall seconds, are load-sensitive. The first-set numbers are kept as measured. The pp512 cells are marked, and the chat wall-seconds row is labelled.
13. **`n_ctx` 8192 for every run.** The llama-cpp-python default is 4096 and the app's chat default is `chat_context_size` 4096. 8192 was used so that case d (4016 Qwen3-4B prompt tokens plus up to 1024 output) fits. It matches the value `OLLAMA-NUM-CTX` already uses. It is a deviation from the chat default, and it changes the KV-cache part of the RSS.

## Findings for CPU-MODEL-FINAL

- At 8 threads the two models' decode speeds are 13.5 and 14.4 tok/s, measured in a loaded window (deviation 11). Prompt processing was measured in the same loaded window and is not usable for comparison, so no prefill ranking is claimed.
- On this 40-text dev sample, with thinking off: Qwen3-4B had 0 of 20 must-block items ALLOW and 2 of 20 must-allow blocked. Phi-4-mini had 3 of 20 must-block items ALLOW and 4 of 20 must-allow blocked. The sample is small (wide intervals above), it is not S5, and it is not the 2026-10-22 set. It cannot decide the default.
- Both models answered all five chat cases as valid JSON with `stop`, with no invalid cites. Phi-4-mini's case d answer is about 40% longer than Qwen3-4B's (2294 characters against 1638), with 5 uncertainty items against 1.
- Peak RSS is about 0.67 GiB higher for Qwen3-4B (5.67 GiB against 5.00 GiB) at `n_ctx` 8192.

## Appendix: `qwen_tier.py` (scratch, not committed)

sha256 `222ad8ebbd0185ff129608311103b73efa010b3b011b8292816f0cbe95b910df`, at `~/hc-models-scratch/scripts/qwen_tier.py`.

```python
#!/usr/bin/env python3
"""QWEN3-4B-TIER measurement helper. Scratch script, not committed.

CPU only: every model is loaded with n_gpu_layers=0 (this llama-cpp-python build
reports llama_supports_gpu_offload() == False). Thinking is switched off through the
GGUF chat template (enable_thinking=False), rendered with the same Jinja environment
llama-cpp-python uses for create_chat_completion, then sent with create_completion.

Run as:  ~/venvs/asclexis-311/bin/python -I qwen_tier.py <smoke|bench|judge|chat> ...
"""
import argparse
import ast
import json
import re
import statistics
import time

import llama_cpp
import numpy as np
from llama_cpp import Llama, LlamaGrammar
from llama_cpp.llama_chat_format import Jinja2ChatFormatter

N_CTX = 8192
JUDGE_SRC = "/tmp/claude-1000/judge-laya/scripts2/ollama_judge.py"
DEV_JSON = ("/mnt/e/Programming/Github Repo/hc-qwen3-4b-tier/src/backend/tests/fixtures/"
            "prohibited_patterns/held_out_dev.json")
PROMPTS_JSON = "/tmp/claude-1000/kvv-2026-10-27/prompts.json"


def frozen_prompt():
    """FROZEN_PROMPT text, read from the JUDGE-LAYA judge mirror (#264 head 48a50b5), not retyped."""
    tree = ast.parse(open(JUDGE_SRC, encoding="utf-8").read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "FROZEN_PROMPT" for t in node.targets):
            return ast.literal_eval(node.value)
    raise SystemExit("FROZEN_PROMPT not found in " + JUDGE_SRC)


def neut(t):
    # Same markers neutralisation as ollama_judge.py.
    t = re.sub(r"(?i)<<<(?=\s*answer)", "<<< ", t)
    return re.sub(r"(?i)(?<=answer)(?=\s*>>>)", " ", t)


def load(model, threads):
    llm = Llama(model_path=model, n_ctx=N_CTX, n_threads=threads, n_gpu_layers=0, verbose=False)
    eos = llm.detokenize([llm.token_eos()], special=True).decode("utf-8", "replace")
    bos = llm.detokenize([llm.token_bos()], special=True).decode("utf-8", "replace")
    fmt = Jinja2ChatFormatter(template=llm.metadata["tokenizer.chat_template"], eos_token=eos, bos_token=bos)
    return llm, fmt


def _raise(msg):
    raise ValueError(msg)


def render(fmt, messages):
    # Thinking off: enable_thinking=False. Qwen3's template then pre-fills an empty think block;
    # templates without the variable (Phi-4-mini) render exactly as the default does.
    return fmt._environment.render(
        messages=messages, eos_token=fmt.eos_token, bos_token=fmt.bos_token,
        raise_exception=_raise, add_generation_prompt=True, functions=None,
        function_call=None, tools=None, tool_choice=None, enable_thinking=False)


def complete(llm, fmt, messages, max_tokens, temperature, top_p, grammar=None):
    prompt = render(fmt, messages)
    stop = list(getattr(fmt(messages=messages), "stop", None) or [])
    add_bos = bool(llm._model.add_bos_token())
    tokens = llm.tokenize(prompt.encode("utf-8"), add_bos=add_bos, special=True)
    kwargs = {"max_tokens": max_tokens, "temperature": temperature, "top_p": top_p, "stop": stop}
    if grammar is not None:
        kwargs["grammar"] = grammar
    t0 = time.perf_counter()
    out = llm.create_completion(prompt=tokens, **kwargs)
    secs = time.perf_counter() - t0
    ch = out["choices"][0]
    return {"text": ch["text"], "finish_reason": ch.get("finish_reason"),
            "prompt_tokens": out["usage"]["prompt_tokens"],
            "completion_tokens": out["usage"]["completion_tokens"],
            "seconds": secs, "stop": stop, "add_bos": add_bos,
            "prompt_tail": prompt[-80:]}


def write(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)


def run_smoke(args):
    llm, fmt = load(args.model, args.threads)
    specials = {t: llm.tokenize(t.encode(), add_bos=False, special=True)
                for t in ("<|im_start|>", "<|user|>", "<|assistant|>", "<think>")}
    r = complete(llm, fmt, [{"role": "user", "content": "Reply with the single word OK."}],
                 max_tokens=8, temperature=0.0, top_p=0.9)
    out = {"llama_cpp_version": llama_cpp.__version__,
           "gpu_offload_supported": llama_cpp.llama_supports_gpu_offload(),
           "n_threads": args.threads, "special_token_ids": specials, "reply": r}
    write(args.out, out)
    print(json.dumps(out, ensure_ascii=False, indent=1))


class BanEOS:
    def __init__(self, eos):
        self.eos = eos

    def __call__(self, input_ids, scores):
        scores[..., self.eos] = -np.inf
        return scores


class Chain(list):
    def __call__(self, input_ids, scores):
        for proc in self:
            scores = proc(input_ids, scores)
        return scores


def run_bench(args):
    llm, _ = load(args.model, args.threads)
    eos = llm.token_eos()
    text = ("The laboratory report lists the lipid panel values with their reference ranges "
            "and the date of collection. ") * 80
    toks = llm.tokenize(text.encode("utf-8"), add_bos=True, special=False)
    assert len(toks) >= 528, len(toks)
    pp_toks, gen_prompt = toks[:512], toks[:16]
    llm.reset()
    llm.eval(pp_toks)  # warm-up, not counted
    pp = []
    for _ in range(args.reps):
        llm.reset()
        t0 = time.perf_counter()
        llm.eval(pp_toks)
        pp.append(512 / (time.perf_counter() - t0))
    tg, counts = [], []
    for rep in range(args.reps + 1):
        n, t_first, t_last = 0, None, None
        for _tok in llm.generate(gen_prompt, temp=0.0, reset=True, logits_processor=Chain([BanEOS(eos)])):
            now = time.perf_counter()
            if t_first is None:
                t_first = now
            n += 1
            t_last = now
            if n == 128:
                break
        if rep == 0:
            continue  # warm-up
        counts.append(n)
        tg.append((n - 1) / (t_last - t_first))
    out = {"model": args.model, "n_threads": args.threads, "reps": args.reps,
           "llama_cpp_version": llama_cpp.__version__,
           "gpu_offload_supported": llama_cpp.llama_supports_gpu_offload(),
           "pp512_tps": pp, "pp512_mean": statistics.mean(pp),
           "tg128_tps": tg, "tg128_mean": statistics.mean(tg), "tg_token_counts": counts,
           "method": "pp: llama_cpp eval of 512 tokens after reset; tg: generate 128 tokens, EOS banned, "
                     "rate over tokens 2..128 after prompt of 16 tokens"}
    write(args.out, out)
    print(json.dumps({k: out[k] for k in ("n_threads", "pp512_tps", "pp512_mean", "tg128_tps",
                                          "tg128_mean", "tg_token_counts")}))


def run_judge(args):
    fp = frozen_prompt()
    dev = json.load(open(DEV_JSON, encoding="utf-8"))
    blk = [x["text"] for x in dev["must_block"]]
    alw = [x["text"] for x in dev["must_allow"]]
    items = ([("must_block", i, blk[i]) for i in range(0, len(blk), 9)]
             + [("must_allow", i, alw[i]) for i in range(0, len(alw), 9)])
    llm, fmt = load(args.model, args.threads)
    t0 = time.perf_counter()
    complete(llm, fmt, [{"role": "user", "content": "hi"}], max_tokens=3, temperature=0.0, top_p=0.9)
    warm = time.perf_counter() - t0  # untimed warm-up, as in ollama_judge.py
    rows = []
    for kind, idx, text in items:
        msgs = [{"role": "user", "content": fp.replace("{answer}", neut(text))}]
        r = complete(llm, fmt, msgs, max_tokens=3, temperature=0.0, top_p=0.9)
        raw = r["text"].strip()
        exact = raw if raw in ("ALLOW", "BLOCK") else "OTHER"
        if r["seconds"] > 2.0:
            verdict = "UNAVAILABLE"
            reason = "clock>2s"
        elif exact in ("ALLOW", "BLOCK"):
            verdict, reason = exact, "exact"
        else:
            verdict, reason = "UNAVAILABLE", "unparseable"
        rows.append({"set": kind, "dev_index": idx, "verdict_2s": verdict, "reason": reason,
                     "raw_text": r["text"], "exact": exact, "seconds": round(r["seconds"], 3),
                     "prompt_tokens": r["prompt_tokens"], "completion_tokens": r["completion_tokens"],
                     "finish_reason": r["finish_reason"]})
    def tally(sub):
        return {v: sum(1 for x in sub if x["verdict_2s"] == v) for v in ("ALLOW", "BLOCK", "UNAVAILABLE")}
    summary = {
        "all": tally(rows),
        "must_block": tally([x for x in rows if x["set"] == "must_block"]),
        "must_allow": tally([x for x in rows if x["set"] == "must_allow"]),
        "reasons": {k: sum(1 for x in rows if x["reason"] == k) for k in ("exact", "clock>2s", "unparseable")},
        "raw_exact_counts": {k: sum(1 for x in rows if x["exact"] == k) for k in ("ALLOW", "BLOCK", "OTHER")},
        "median_seconds": statistics.median(x["seconds"] for x in rows),
        "warmup_seconds": round(warm, 3), "n_texts": len(rows),
        "dev_json_sha_source": DEV_JSON,
    }
    out = {"model": args.model, "n_threads": args.threads, "thinking": "off (enable_thinking=False)",
           "summary": summary, "rows": rows}
    write(args.out, out)
    print(json.dumps(summary))


def context_labels(content):
    i = content.find("CONTEXT:")
    j = content.find("USER QUESTION")
    seg = content[i:j] if (i >= 0 and j > i) else content
    return sorted({int(n) for n in re.findall(r"\[(?:YOUR_RESULTS|USER_DOCUMENT|REFERENCE):(\d+)\]", seg)})


def analyse_chat(text, valid):
    rec = {"chars": len(text), "words": len(text.split()),
           "think_open_tags": text.count("<think>"),
           "cite_markers_text": re.findall(r"\[cite:(\d+)\]", text)}
    try:
        obj = json.loads(text)
    except Exception:
        rec["json_ok"] = False
        return rec
    rec["json_ok"] = isinstance(obj, dict)
    if isinstance(obj, dict):
        items = []
        for key in ("report_facts", "general_info"):
            items += [x for x in obj.get(key, []) if isinstance(x, dict)]
        cites = [c for it in items for c in it.get("cites", [])]
        rec.update(n_items=len(items), n_cites=len(cites),
                   invalid_cites=[c for c in cites if c not in valid],
                   items_without_cites=sum(1 for it in items if not it.get("cites")),
                   n_uncertainties=len(obj.get("uncertainties", []) or []),
                   top_level_fields=sorted(obj.keys()))
    return rec


def run_chat(args):
    prompts = json.load(open(PROMPTS_JSON, encoding="utf-8"))
    llm, fmt = load(args.model, args.threads)
    results = {}
    for case in args.cases.split(","):
        body = prompts["cases"][case]["body"]
        msgs = body["messages"]
        opts = body["options"]
        grammar = (LlamaGrammar.from_json_schema(json.dumps(body["format"]), verbose=False)
                   if body.get("format") else None)
        r = complete(llm, fmt, msgs, max_tokens=opts["num_predict"], temperature=opts["temperature"],
                     top_p=opts["top_p"], grammar=grammar)
        valid = context_labels(msgs[-1]["content"])
        analysis = analyse_chat(r["text"], valid)
        results[case] = {"desc": prompts["cases"][case]["desc"], "finish_reason": r["finish_reason"],
                         "prompt_tokens": r["prompt_tokens"], "completion_tokens": r["completion_tokens"],
                         "seconds": round(r["seconds"], 2), "valid_context_labels": valid,
                         "analysis": analysis, "text": r["text"], "prompt_tail": r["prompt_tail"]}
        print(case, r["finish_reason"], r["completion_tokens"], analysis.get("json_ok"),
              analysis.get("invalid_cites"), analysis.get("think_open_tags"), flush=True)
    write(args.out, {"model": args.model, "n_threads": args.threads, "thinking": "off (enable_thinking=False)",
                     "prompts_json": PROMPTS_JSON, "prompts_json_note": "built by kvv-2026-10-27 prompts.py", "cases": results})


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("smoke", "bench", "judge", "chat"):
        p = sub.add_parser(name)
        p.add_argument("--model", required=True)
        p.add_argument("--threads", type=int, required=True)
        p.add_argument("--out", required=True)
        if name == "bench":
            p.add_argument("--reps", type=int, default=3)
        if name == "chat":
            p.add_argument("--cases", required=True)
    args = ap.parse_args()
    {"smoke": run_smoke, "bench": run_bench, "judge": run_judge, "chat": run_chat}[args.cmd](args)


if __name__ == "__main__":
    main()
```
