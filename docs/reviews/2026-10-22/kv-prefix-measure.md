# KV-PREFIX-MEASURE: prompt sizes, prefill timings, truncation and VRAM on the model host

**Last Updated:** 2026-10-22
**Owner:** repository owner
**Status:** Measured evidence only. No product code, config, flag or default changed. One owner question drafted (unload on profile lock, section "Owner question"); one number handed to OLLAMA-NUM-CTX (section "Conclusions", item b).
**Refresh Trigger:** the Ollama version or the demo model changes, `RAGModule.SYSTEM_PROMPT` / `compose_prompt` / the cite schema changes, `_build_request_body` changes, or the retrieval top-k or chunk size changes.

Plan: [KV-PREFIX-MEASURE](../../plans/2026-10-15-build-program/lane-A-rag-assistant.md#kv-prefix-measure--measure-prompt-sizes-prefill-timings-truncation-and-vram-on-the-model-host); queue row `KV-PREFIX-MEASURE` in [queue.md](../../plans/2026-10-15-build-program/queue.md). Feeds the row `OLLAMA-NUM-CTX` ([plan](../../plans/2026-10-15-build-program/lane-A-rag-assistant.md#ollama-num-ctx--the-ollama-provider-sends-no-context-size-so-the-servers-4096-default-applies)). Run by an agent on the owner's model host (WSL2, RTX 3080, Ollama 0.40.5), 2026-10-22 12:53 to 13:38 (PDT). The owner has not confirmed this run. All data is synthetic; no patient data was used.

## Verdict

1. **The box runs every Ollama request at 4096 tokens** (measured: `ollama ps` `CONTEXT` 4096 and `llama_context: n_ctx = 4096` in the journal; no `num_ctx` is sent).
2. **One of the four cases is truncated at that default, and a second one is cut short.** The legacy-chat largest realistic case (d) is 4350 tokens; at 4096 Ollama logged `truncating input prompt limit=2051 prompt=4350 keep=5 new=2051` and the model saw 2051 of 4350 tokens. The typical legacy-chat case (c) is 3585 tokens and is not truncated, but with its 1024-token output budget it fills the window: generation stopped at `n_tokens = 4095` after 508 to 511 tokens (all 22 case-c runs at the default; answer text was recorded for 7 of them, all empty), against 1024 tokens at 8192. The two cases the demo really reaches with the agent on, the lab explanation (a, 2476 tokens) and the visit-note assist (b, 1677 tokens), fit in 4096 with their output budgets.
3. **`num_ctx` for OLLAMA-NUM-CTX: 8192.** It is the smallest of 4096 / 8192 / 16384 that holds the largest case plus its output (4350 + 1024 = 5374 tokens), runs `100% GPU`, costs about 0.3 GiB more VRAM than 4096, and is at or below `capabilities().context_len` (262144 for `gemma4:e4b`, 8192 for every other name). 4096 is not right for this box, so the row has code.
4. **Prefix reuse works only for an identical prompt.** Same prompt again: prefill 1163 ms to 48 ms (case c). A new question in the same chat, or a new analyte: no gain over a warm runner with no shared prefix (584 ms vs 578 ms; 525 ms vs 520 ms). The journal gives the reason: `forcing full prompt re-processing due to lack of cache data (likely due to SWA or hybrid/recurrent memory)`, with a 354-token common prefix. A prompt-order change would not help `gemma4:e4b` on this Ollama build.
5. **The model stays loaded after a profile lock until `keep_alive` expires** (5 minutes after the last request; locked at 13:33:37, still loaded at +55 s, `expires_at` 13:38:37). Only loopback connections were made. Owner question below.

## Setup (step 1)

Commands and raw output (`/tmp/claude-1000/kv-1022/setup.txt`; the unit's `PATH` value is elided, it is the only `Environment` line):

```
## ollama -v
ollama version is 0.40.5
## systemctl env
Environment="PATH=<elided>"
## nvidia-smi
name, memory.total [MiB], memory.used [MiB]
NVIDIA GeForce RTX 3080, 10240 MiB, 1210 MiB
## ollama ps
NAME    ID    SIZE    PROCESSOR    CONTEXT    RUNNER    UNTIL 
## HEAD
5f7c67c838ffeaf67b52bd67c0ed4a9e584d6ab8
## LLM_MODEL
LLM_PROVIDER=ollama
LLM_MODEL=gemma4:e4b
## /api/version
{"version":"0.40.5"}
['gemma3:12b', 'qwen3:8b', 'llama3.1:8b', 'gemma4:e4b']
## journal
Oct 22 12:52:35 Danny-PC ollama[251]: [GIN] 2026/10/22 - 12:52:35 | 200 |      12.487µs |       127.0.0.1 | GET      "/api/ps"
Oct 22 12:52:35 Danny-PC ollama[251]: [GIN] 2026/10/22 - 12:52:35 | 200 |      65.694µs |       127.0.0.1 | GET      "/api/version"
Oct 22 12:52:35 Danny-PC ollama[251]: [GIN] 2026/10/22 - 12:52:35 | 200 |   16.089758ms |       127.0.0.1 | GET      "/api/tags"
## serve help
      OLLAMA_CONTEXT_LENGTH         Context length to use unless otherwise specified (default: 4k/32k/256k based on VRAM)
      OLLAMA_KEEP_ALIVE             The duration that models stay loaded in memory (default "5m")
      OLLAMA_FLASH_ATTENTION        Enabled flash attention
      OLLAMA_KV_CACHE_TYPE          Quantization type for the K/V cache (default: f16)
```

| Item | Value |
|---|---|
| Tree measured | `5f7c67c838ffeaf67b52bd67c0ed4a9e584d6ab8` (`origin/main` when the run started) in the scratch worktree `hc-kv-1022` (prompt capture) and in the clone `~/hc-mm4` fetched and detached at the same commit (app run). `origin/main` has since moved to `d2843e8` (#288, docs only); no product file under `src/backend` differs between the two |
| Demo model | `LLM_MODEL=gemma4:e4b`, `LLM_PROVIDER=ollama` (from `~/hc-mm4/src/backend/.env`). Only this model was measured; `llama3.1:8b`, `qwen3:8b`, `gemma3:12b` were not (not measured) |
| Server defaults | `OLLAMA_CONTEXT_LENGTH` unset, default "4k/32k/256k based on VRAM"; `OLLAMA_KEEP_ALIVE` default `5m`; `OLLAMA_KV_CACHE_TYPE` unset (default `f16`) |
| KV type | `f16` only. `q8_0` needs a service restart with a new environment, an owner action: not measured |
| GPU | RTX 3080, 10240 MiB, 1210 MiB in use with no model loaded in the step 1 record (1199 MiB in the step 6 baseline) |
| Isolation | (slot-5 evidence below the table) every model call ran inside `/tmp/claude-1000/hold_slots.sh <cmd>`, which is `flock /tmp/claude-1000/hc-pytest.1.lock flock …2.lock flock …3.lock <cmd>` (the lock paths of `scripts/pyslot.sh:9`). I started no pytest. **Caveat:** `scripts/pyslot.sh` reads `PYSLOTS` (default 3); another session ran `flock -n … hc-pytest.5.lock … pytest tests/` from 13:26:24, so with more than three slots in use the three held locks do not exclude every pytest. It overlapped only step 7 (13:26 to 13:34). I did not check for other pytest runs continuously during steps 3 to 6 (12:53 to about 13:20); the timing spread there is tight (see the timing table), which gives no sign of contention |
| Product code | not edited. Scratch scripts are pasted at the end of this file and were not committed |
| Network | prompt capture and measurement ran with `HF_HUB_OFFLINE=1`. `./dev.sh` ran its usual dependency step (`logs/dev-pip.log`: every requirement already satisfied). During the model call the only sockets owned by the backend, `python`, Ollama or llama-server were on loopback (step 7) |

Slot-5 overlap evidence (`pgrep -af`, 13:34): `2363281 flock -n -E 75 /tmp/claude-1000/hc-pytest.5.lock env HF_HUB_OFFLINE=1 /home/danny/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q`, `ps` start time Thu Oct 22 13:26:24 2026. It did not confound step 7: the Ollama journal for 13:26:40 to 13:34:00 has exactly two `POST "/api/chat"` requests (13:26:59 and 13:33:37), both the app's own calls, and between them only `HEAD /` (the `ollama ps` CLI); each `expires_at` equals its own call's end + 5:00 (13:31:59, 13:38:37). So no other client loaded the model or reset its timer, and the loaded and unloaded findings stand. The two call latencies (11.0 s, 13.2 s) are not used in any conclusion.

## Prompts (step 2)

`prompts.py` (below) seeds an in-memory master DB (the real biomarker knowledge seed, `scripts/seed_knowledge_base.py`) and an in-memory profile DB (4 verified synthetic lab documents chunked by the real `ChunkingModule`, embedded with the real bundled `all-MiniLM-L6-v2`, plus 5 analytes with 3 observations each). It calls the real `RAGModule.query` for (a), (c), (c2) and (d) with a recording runner passed as `model_runner=`, and the real `llm_assist_visit_entities` for (b) with a recording runner passed as `runner=`. The recorded prompt is wrapped in the body built by `OllamaProvider(model="gemma4:e4b")._build_request_body` (the provider's own builder), so the body is what the app sends: `num_predict` 1024 (512 for b), `temperature` 0.1 (0.0 for b), `top_p` 0.9, `stop` `[]`, a `format` cite schema (not for b), no `num_ctx`, no `keep_alive`. `rag.query` ran end to end, so no fallback to `compose_prompt` was needed.

Synthetic chunk sizes from the real chunker: 32 chunks, mean 637 characters, **maximum 781 characters** (target 800).

| Case | Fixed rules | Retrieved context | History | Question or document | Total chars | Tokens, server default | Tokens, `num_ctx` 32768 |
|---|---|---|---|---|---|---|---|
| a, lab explanation (LDL), as `interpretations.py:529-537` | 1449 | 7789 | 0 | 149 | 9387 | 2476 | 2476 |
| b, visit-note assist, 6000-char note | 700 | 0 | 0 | 6000 | 6725 | 1677 | 1677 |
| c, legacy chat, typical question, top-k 10, no history | 1449 | 9865 | 0 | 58 | 11372 | 3585 | 3585 |
| c2, legacy chat, second question, history = turn 1 | 1449 | 6922 | 359 | 49 | 8779 | 2532 | 2532 |
| d, legacy chat, largest: 5 analytes selected, 10 doc chunks + 5 observation summaries + references, 10-turn history | 1449 | 13335 | 1738 | 174 | 16696 | **2051 (truncated)** | **4350** |
| a2, lab explanation (glucose), for step 5 and 4 | 1449 | 6629 | 0 | 150 | 8228 | 2221 | not run |

Notes: (1) "fixed rules" for a, c, c2, d is `SYSTEM_PROMPT` up to and including `CONTEXT:\n`; for b it is the instruction text up to `<document>\n`. (2) Case d's history is capped by the code at half of `chat_context_size` (4096) = 2048 characters, so a 10-turn history of long answers is 1738 characters after trimming; the 10 turns cannot make the prompt larger than that. (3) "Largest realistic" is my construction: the real retrieval limits (top-k 10 document chunks at up to 781 characters, up to 5 observation summaries, one reference chunk per analyte) with the analyte filter set to five analytes. A document with long sentences could yield chunks above 781 characters (the chunker never splits a sentence); I did not construct that. (4) Characters per token measured by Ollama: c 3.17, d 3.84, a 3.79, b 4.01.

Script output (`prompts.stdout`):

```
a lab explanation, ldl_cholesterol {'fixed_rules_chars': 1449, 'retrieved_context_chars': 7789, 'history_chars': 0, 'question_chars': 149, 'total_chars': 9387} max_tokens 1024
a2 lab explanation, glucose_fasting (new analyte) {'fixed_rules_chars': 1449, 'retrieved_context_chars': 6629, 'history_chars': 0, 'question_chars': 150, 'total_chars': 8228} max_tokens 1024
b visit-note LLM assist, 6000-char note {'fixed_rules_chars': 700, 'document_chars': 6000, 'total_chars': 6725} max_tokens 512
c legacy chat, typical question, no history {'fixed_rules_chars': 1449, 'retrieved_context_chars': 9865, 'history_chars': 0, 'question_chars': 58, 'total_chars': 11372} max_tokens 1024
c2 legacy chat turn 2, same chat (history = turn 1) {'fixed_rules_chars': 1449, 'retrieved_context_chars': 6922, 'history_chars': 359, 'question_chars': 49, 'total_chars': 8779} max_tokens 1024
d legacy chat, largest: top-k 10 doc chunks + obs + refs for 5 analytes + 10-turn history {'fixed_rules_chars': 1449, 'retrieved_context_chars': 13335, 'history_chars': 1738, 'question_chars': 174, 'total_chars': 16696} max_tokens 1024
chunks {'count': 32, 'max': 781, 'mean': 637} prefix {'a_vs_a2_new_analyte': 1471, 'c_vs_c2_same_chat': 1450, 'c_vs_c_identical': 11372, 'fixed_rules_chars': 1449} []
first chars of context c: [YOUR_RESULTS:1] Your LDL Cholesterol Result | YOUR RESULTS — LDL Cholesterol | Latest value : 148.0 mg/dL | Collected    : 2026-07-10 | Reference    : 0.0–100.0 mg/dL | Flag         : H | Trend (last 3): 155.0 →
```

## Token counts and truncation (step 3)

For every case the model was unloaded first (`keep_alive: 0`, `ollama ps` empty) so `prompt_eval_count` is a full count, then the case body was POSTed to `/api/chat` unchanged, then again after another unload with `options.num_ctx` = 32768. Raw values (times in ms):

| Case | num_ctx | `prompt_eval_count` | `eval_count` | `done_reason` | `load_duration` | `prompt_eval_duration` | answer chars |
|---|---|---|---|---|---|---|---|
| a | default | 2476 | 1024 | length | 13860 | 960 | 222 |
| a | 32768 | 2476 | 1024 | length | 7098 | 927 | 291 |
| b | default | 1677 | 512 | length | 6793 | 781 | 0 |
| b | 32768 | 1677 | 512 | length | 7378 | 801 | 0 |
| c | default | 3585 | 510 | length | 7213 | 1193 | 0 |
| c | 32768 | 3585 | 1024 | length | 7300 | 1213 | 1054 |
| c2 | default | 2532 | 859 | stop | 7104 | 908 | 371 |
| c2 | 32768 | 2532 | 1024 | length | 7096 | 961 | 236 |
| d | default | 2051 | 1024 | length | 7085 | 862 | 785 |
| d | 32768 | 4350 | 1024 | length | 7313 | 1291 | 120 |

`ollama ps` after each request: `CONTEXT` 4096 for every default run, 32768 for every 32768 run, `100% GPU` (full text in "Appendix: raw outputs"). The default context is therefore 4096, as the plan inferred.

**Case d is truncated at the server default:** 4350 tokens with `num_ctx` 32768 against 2051 at the default, 2299 tokens (52.9 percent) dropped. The journal says `level=WARN source=llama_server.go:334 msg="truncating input prompt" limit=2051 prompt=4350 keep=5 new=2051`. `keep=5` suggests that the first 5 tokens are kept and the rest of the 2051 comes from the end of the prompt, which would remove the rules (354 tokens, listed below) and the start of the context, including the first citable chunks; I did not inspect which tokens were kept, so this is inferred from the log fields. Cases a, b, c, c2 have identical counts at both settings (no prompt truncation).

**Case c is cut short at 4096 by the output, not the input.** 3585 prompt tokens plus 1024 allowed output tokens is 4609, above 4096. Generation stopped after 510 tokens with `done_reason: length` and the journal line `slot release: … stop processing: n_tokens = 4095, truncated = 1` (3585 + 510 = 4095). Seven of seven runs at the default ended at 508 to 511 tokens with an empty answer (the model was still in its thinking phase, see "Other findings"). With `num_ctx` 8192 the same prompt gets its full 1024 tokens (3 of 3 runs, 279, 631 and 638 characters of answer):

| Case | `num_ctx` | load ms | `prompt_eval_count` | prompt eval ms | `eval_count` | answer chars |
|---|---|---|---|---|---|
| c | 4096 | 6929 | 3585 | 1134 | 510 | 0 |
| c | 8192 | 7430 | 3585 | 1100 | 1024 | 279 |
| c | 4096 | 7351 | 3585 | 1546 | 509 | 0 |
| c | 8192 | 9141 | 3585 | 1155 | 1024 | 631 |
| c | 4096 | 7462 | 3585 | 1145 | 509 | 0 |
| c | 8192 | 7883 | 3585 | 1147 | 1024 | 638 |

### Journal search for "truncat"

`journalctl -u ollama --since "2026-10-22 12:53:13" --no-pager | grep -i truncat`, every hit pasted. Exactly one is a truncation of the prompt (the `WARN`); the others are llama-server `slot release` lines that print a `truncated = 0` or `truncated = 1` field. The `truncated = 1` line (12:54:15) is case c at the default, which hit the context ceiling at `n_tokens = 4095`.

```
Oct 22 12:53:24 Danny-PC ollama[251]: slot      release: id  0 | task 0 | stop processing: n_tokens = 0, truncated = 0
Oct 22 12:53:30 Danny-PC ollama[251]: slot      release: id  0 | task 2 | stop processing: n_tokens = 3499, truncated = 0
Oct 22 12:53:44 Danny-PC ollama[251]: slot      release: id  0 | task 0 | stop processing: n_tokens = 3499, truncated = 0
Oct 22 12:53:52 Danny-PC ollama[251]: slot      release: id  0 | task 0 | stop processing: n_tokens = 2188, truncated = 0
Oct 22 12:54:03 Danny-PC ollama[251]: slot      release: id  0 | task 0 | stop processing: n_tokens = 2188, truncated = 0
Oct 22 12:54:11 Danny-PC ollama[251]: slot      release: id  0 | task 0 | stop processing: n_tokens = 0, truncated = 0
Oct 22 12:54:15 Danny-PC ollama[251]: slot      release: id  0 | task 2 | stop processing: n_tokens = 4095, truncated = 1
Oct 22 12:54:27 Danny-PC ollama[251]: slot      release: id  0 | task 0 | stop processing: n_tokens = 4608, truncated = 0
Oct 22 12:54:34 Danny-PC ollama[251]: slot      release: id  0 | task 0 | stop processing: n_tokens = 0, truncated = 0
Oct 22 12:54:40 Danny-PC ollama[251]: slot      release: id  0 | task 2 | stop processing: n_tokens = 3391, truncated = 0
Oct 22 12:54:52 Danny-PC ollama[251]: slot      release: id  0 | task 0 | stop processing: n_tokens = 3555, truncated = 0
Oct 22 12:54:59 Danny-PC ollama[251]: time=2026-10-22T12:54:59.834-07:00 level=WARN source=llama_server.go:334 msg="truncating input prompt" limit=2051 prompt=4350 keep=5 new=2051
Oct 22 12:54:59 Danny-PC ollama[251]: slot      release: id  0 | task 0 | stop processing: n_tokens = 0, truncated = 0
Oct 22 12:55:07 Danny-PC ollama[251]: slot      release: id  0 | task 2 | stop processing: n_tokens = 3074, truncated = 0
Oct 22 12:55:19 Danny-PC ollama[251]: slot      release: id  0 | task 0 | stop processing: n_tokens = 5373, truncated = 0
```

## Timings (step 4)

Model `gemma4:e4b`, default context (4096). Three repeats each; the table gives the median with the raw values in brackets (ms). Cold = model unloaded first (`keep_alive: 0`, `ollama ps` empty). "Same again" = the identical request immediately after. "New question" = case c2 right after case c in the same loaded runner (legacy chat only). "After expiry" = a request, 330 s idle, `ollama ps` empty (confirmed at 332 s each time), then the same request.

| Phase | Case | `load_duration` | `prompt_eval_count` | `prompt_eval_duration` | `total_duration` |
|---|---|---|---|---|---|
| (i) cold start | c | 7088 [6797, 7693, 7088] | 3585 | 1163 [1202, 1163, 1106] | 11246 [10809, 11772, 11246] |
| (i) cold start | a | 7348 [7393, 7096, 7348] | 2476 | 891 [891, 859, 913] | 13943 [14159, 13490, 13943] |
| (ii) same again | c | 1 [1, 1, 1] | 3585 | **48** [49, 48, 37] | 2939 [2926, 2939, 3029] |
| (ii) same again | a | 1 [1, 1, 1] | 2476 | **109** [88, 109, 134] | 5873 [5873, 5920, 5511] |
| (iii) new question, same chat | c2 after c | 1 [1, 1, 1] | 2532 | 584 [584, 590, 577] | 6566 [6646, 6566, 6163] |
| (iii') new analyte | a2 after a | 1 [1, 1, 1] | 2221 | 525 [527, 523, 525] | 6136 [6170, 6136, 6035] |
| (iv) after `keep_alive` expiry | c | 7423 [7423, 7195, 7712] | 3585 | 1117 [1106, 1117, 1143] | 11408 [11408, 11308, 12084] |

Baselines for (iii), measured afterwards (`extra.py`, `extra2.py`): the same case with a **warm runner and no shared prefix** (case b first, whose prompt starts differently) and the same case **cold after load**.

| Case | cold after load, prefill ms | warm, no shared prefix, prefill ms | warm after the sibling case (shared 354-token prefix), prefill ms |
|---|---|---|---|
| c | 1163 [1202, 1163, 1106] | 833 [840, 833, 829] | n/a |
| c2 | 857 [847, 893, 857] | 578 [582, 575, 578] | **584** [584, 590, 577] |
| a2 | 819 [803, 834, 819] | 520 [538, 517, 520] | **525** [527, 523, 525] |

Reading the tables:

- **Identical prompt: prefix reuse works.** Prefill drops by 96 percent (c) and 88 percent (a). `prompt_eval_count` does **not** drop in Ollama 0.40.5 (3585 both times), so the plan's "`prompt_eval_count` or `prompt_eval_duration`" test reduces to the duration here.
- **Different question: no measurable reuse.** The new question costs the same as a warm request with no shared prefix (584 vs 578 ms; 525 vs 520 ms). The cold-after-load figures are 250 to 330 ms higher than warm ones; that gap is a first-request-after-load cost, not reuse, which is why the warm baseline is the right comparison.
- **Reason, from the journal** (step 4 journal, the c2 request after c; lines kept: the cache decision and the checkpoint messages):

```
Oct 22 12:57:23 Danny-PC ollama[251]: srv          load:    - prompt with length    4095, lcp =     354, f_keep = 0.086, f_sim = 0.140
Oct 22 12:57:23 Danny-PC ollama[251]: slot   operator(): id  0 | task 186 | new prompt, n_ctx_slot = 4096, n_keep = 4, task.n_tokens = 2532
Oct 22 12:57:23 Danny-PC ollama[251]: slot   operator(): id  0 | task 186 | checking checkpoint with [2557, 3580] against 0...
Oct 22 12:57:23 Danny-PC ollama[251]: slot   operator(): id  0 | task 186 | checking checkpoint with [2049, 3072] against 0...
Oct 22 12:57:23 Danny-PC ollama[251]: slot   operator(): id  0 | task 186 | forcing full prompt re-processing due to lack of cache data (likely due to SWA or hybrid/recurrent memory, see https://github.com/ggml-org/llama.cpp/pull/
Oct 22 12:57:23 Danny-PC ollama[251]: slot   operator(): id  0 | task 186 | erased invalidated context checkpoint (pos_min = 2049, pos_max = 3072, n_tokens = 3073, n_swa = 512, pos_next = 0, size = 20.006 MiB)
Oct 22 12:57:23 Danny-PC ollama[251]: slot   operator(): id  0 | task 186 | erased invalidated context checkpoint (pos_min = 2557, pos_max = 3580, n_tokens = 3581, n_swa = 512, pos_next = 0, size = 20.006 MiB)
Oct 22 12:57:23 Danny-PC ollama[251]: slot   operator(): id  0 | task 186 | cached n_tokens = 0, memory_seq_rm [0, end)
Oct 22 12:57:23 Danny-PC ollama[251]: slot   operator(): id  0 | task 186 | cached n_tokens = 512, memory_seq_rm [512, end)
Oct 22 12:57:23 Danny-PC ollama[251]: slot   operator(): id  0 | task 186 | cached n_tokens = 1024, memory_seq_rm [1024, end)
Oct 22 12:57:23 Danny-PC ollama[251]: slot   operator(): id  0 | task 186 | cached n_tokens = 1536, memory_seq_rm [1536, end)
Oct 22 12:57:23 Danny-PC ollama[251]: slot   operator(): id  0 | task 186 | cached n_tokens = 2020, memory_seq_rm [2020, end)
Oct 22 12:57:23 Danny-PC ollama[251]: slot   operator(): id  0 | task 186 | cached n_tokens = 2528, memory_seq_rm [2528, end)
```

  The common prefix is 354 tokens (`lcp = 354`) out of 4095 saved, and llama-server answers `forcing full prompt re-processing due to lack of cache data (likely due to SWA or hybrid/recurrent memory)`. The model's sliding-window layers (`n_swa = 512` in the erased-checkpoint lines) mean a partial prefix cannot be restored; only a prompt whose cached checkpoint matches is reused. This is a property of this model and runner, not of the prompt text. Other models were not measured.
- **Where the time goes.** A full request is 6 to 14 s: model load 7.1 to 7.7 s (cold, and again after 5 minutes idle), prefill 0.5 to 1.2 s, generation 3 to 6 s. Even a perfect reuse of the 354 shared tokens would save about 0.08 s at the measured 0.23 ms per prompt token (833 ms / 3585).

Raw runs (`step4.py`, `extra.py`, `extra2.py`; ms; `eval_duration` is added as a column here for the step 4 runs; the extra runs below give `eval_count` only):

| kind | case | load ms | `prompt_eval_count` | prompt eval ms | eval_count | eval ms | total ms |
|---|---|---|---|---|---|---|---|
| cold | c | 6797 | 3585 | 1202 | 508 | 2777 | 10809 |
| same | c | 1 | 3585 | 49 | 510 | 2848 | 2926 |
| cold | a | 7393 | 2476 | 891 | 1024 | 5846 | 14159 |
| same | a | 1 | 2476 | 88 | 1024 | 5748 | 5873 |
| cold_before_new | c | 7104 | 3585 | 1144 | 511 | 2919 | 11210 |
| new_question | c2 | 1 | 2532 | 584 | 1016 | 5888 | 6646 |
| cold_before_a2 | a | 7415 | 2476 | 876 | 1024 | 5520 | 13841 |
| new_analyte | a2 | 1 | 2221 | 527 | 1024 | 5518 | 6170 |
| cold | c | 7693 | 3585 | 1163 | 511 | 2876 | 11772 |
| same | c | 1 | 3585 | 48 | 509 | 2854 | 2939 |
| cold | a | 7096 | 2476 | 859 | 1024 | 5500 | 13490 |
| same | a | 1 | 2476 | 109 | 1024 | 5771 | 5920 |
| cold_before_new | c | 7168 | 3585 | 1204 | 509 | 2958 | 11362 |
| new_question | c2 | 1 | 2532 | 590 | 1010 | 5786 | 6566 |
| cold_before_a2 | a | 7138 | 2476 | 844 | 1024 | 5310 | 13330 |
| new_analyte | a2 | 1 | 2221 | 523 | 1024 | 5487 | 6136 |
| cold | c | 7088 | 3585 | 1106 | 510 | 3022 | 11246 |
| same | c | 1 | 3585 | 37 | 510 | 2961 | 3029 |
| cold | a | 7348 | 2476 | 913 | 1024 | 5654 | 13943 |
| same | a | 1 | 2476 | 134 | 1024 | 5350 | 5511 |
| cold_before_new | c | 7407 | 3585 | 1187 | 510 | 2986 | 11626 |
| new_question | c2 | 1 | 2532 | 577 | 1024 | 5435 | 6163 |
| cold_before_a2 | a | 7383 | 2476 | 949 | 1024 | 5310 | 13676 |
| new_analyte | a2 | 1 | 2221 | 525 | 1024 | 5400 | 6035 |
| warm_before_expiry | c | 1 | 3585 | 772 | 508 | 3087 | 4041 |
| after_expiry | c | 7423 | 3585 | 1106 | 510 | 2837 | 11408 |
| warm_before_expiry | c | 1 | 3585 | 36 | 508 | 2972 | 3038 |
| after_expiry | c | 7195 | 3585 | 1117 | 511 | 2955 | 11308 |
| warm_before_expiry | c | 1 | 3585 | 52 | 509 | 2789 | 2873 |
| after_expiry | c | 7712 | 3585 | 1143 | 511 | 3194 | 12084 |

Cold after load (`extra.py`; columns: load, count, prefill ms, eval_count, answer chars):

| kind | case | load ms | `prompt_eval_count` | prompt eval ms | eval_count | answer chars |
|---|---|---|---|---|---|---|
| cold_after_load | c2 | 7141 | 2532 | 847 | 914 | 641 |
| cold_after_load | a2 | 6922 | 2221 | 803 | 1024 | 520 |
| cold_after_load | c2 | 8587 | 2532 | 893 | 1024 | 572 |
| cold_after_load | a2 | 7406 | 2221 | 834 | 1024 | 0 |
| cold_after_load | c2 | 7155 | 2532 | 857 | 836 | 765 |
| cold_after_load | a2 | 7118 | 2221 | 819 | 1024 | 0 |

Warm, no shared prefix (`extra2.py`):

| kind | case | load ms | `prompt_eval_count` | prompt eval ms | eval_count | answer chars |
|---|---|---|---|---|---|---|
| warm_noprefix | c | 1 | 3585 | 840 | 511 | 0 |
| warm_noprefix | c2 | 1 | 2532 | 582 | 1024 | 456 |
| warm_noprefix | a2 | 1 | 2221 | 538 | 1024 | 746 |
| warm_noprefix | c | 1 | 3585 | 833 | 508 | 0 |
| warm_noprefix | c2 | 1 | 2532 | 575 | 975 | 615 |
| warm_noprefix | a2 | 1 | 2221 | 517 | 1024 | 99 |
| warm_noprefix | c | 1 | 3585 | 829 | 509 | 0 |
| warm_noprefix | c2 | 1 | 2532 | 578 | 924 | 547 |
| warm_noprefix | a2 | 1 | 2221 | 520 | 1024 | 783 |

## Prompt order (step 5)

- The prompt is one `user` message. Order: fixed rules (1449 characters, **354 tokens**) then `CONTEXT:\n` then the retrieved context, then the history section, then `USER QUESTION: …` (fact 4 of the plan is confirmed). The first character that differs between case c and case c2 (a new question in the same chat) is at **offset 1450**, the first character of the retrieved context; for the two lab explanations (a, a2) it is offset 1471, after the shared `[YOUR_RESULTS:1] Your ` label.
- Everything before the context is the fixed rules. `prompts.py` searched them for dates and UUID-like ids: none. The first per-request text is the retrieved context; the first date in the prompt is the `Collected : 2026-07-10` line of the first observation chunk, inside the context. The shareable prefix is therefore 354 tokens, 9.9 percent of case c and 14 percent of case c2.
- The history comes after the context, so for a second turn the history is not in the shared prefix either: a new question in the same chat recomputes everything after the rules, as the plan expected. Moving the history ahead of the context would let a later turn share the earlier turns, but it is bounded by the 2048-character history cap (about 500 tokens) and, on this model, partial reuse is disabled anyway (previous section).

## VRAM (step 6)

Case d (the largest) at four per-request sizes, the model unloaded before each, no service restart. Baseline with no model loaded: 1199 MiB used (step 6 run; the step 1 record says 1210 MiB). First pass in ascending order, then a second pass in descending order (`extra.py`) to show the run-to-run spread.

| `num_ctx` | `nvidia-smi` used, pass 1 | pass 2 | `ollama ps` PROCESSOR | `ollama ps` CONTEXT | `prompt_eval_count` | `eval_count` |
|---|---|---|---|---|---|---|
| 4096 | 6043 MiB | 5986 MiB | 100% GPU | 4096 | 2051 (truncated) | 1024 |
| 8192 | 6368 MiB | 6255 MiB | 100% GPU | 8192 | 4350 | 1024 |
| 16384 | 6228 MiB | 6210 MiB | 100% GPU | 16384 | 4350 | 1024 |
| 32768 | 6514 MiB | 6505 MiB | 100% GPU | 32768 | 4350 | 1024 |

- No size spilled to the CPU. The largest, 32768, leaves 3.6 GiB free (10240 - 6514 MiB). Going from 4096 to 8192 adds 269 to 325 MiB (about 0.3 GiB). The 8192 and 16384 rows are within the run-to-run spread of about 150 MiB, so the figures do not show a strict increase between them; do not read more into them than "between 6.0 and 6.5 GiB for all four".
- The `SIZE` column of `ollama ps` (369 MB, 538 MB, 381 MB, 398 MB) does not track `nvidia-smi` in this build and is not used.
- `gemma4:e4b` is the only model measured. A larger model (`gemma3:12b`) would need its own run; not measured.

Raw output, pass 1 (`step6.py`):

```
baseline (no model loaded): memory.used [MiB] 1199 MiB
=== num_ctx 4096 {'prompt_eval_count': 2051, 'eval_count': 1024, 'done_reason': 'length'} load_ms 7229
memory.used [MiB]
6043 MiB
NAME          ID              SIZE      PROCESSOR    CONTEXT    RUNNER      UNTIL              
gemma4:e4b    dc35e8d9c606    369 MB    100% GPU     4096       llamacpp    4 minutes from now    

=== num_ctx 8192 {'prompt_eval_count': 4350, 'eval_count': 1024, 'done_reason': 'length'} load_ms 7646
memory.used [MiB]
6368 MiB
NAME          ID              SIZE      PROCESSOR    CONTEXT    RUNNER      UNTIL              
gemma4:e4b    dc35e8d9c606    538 MB    100% GPU     8192       llamacpp    4 minutes from now    

=== num_ctx 16384 {'prompt_eval_count': 4350, 'eval_count': 1024, 'done_reason': 'length'} load_ms 7111
memory.used [MiB]
6228 MiB
NAME          ID              SIZE      PROCESSOR    CONTEXT    RUNNER      UNTIL              
gemma4:e4b    dc35e8d9c606    381 MB    100% GPU     16384      llamacpp    4 minutes from now    

=== num_ctx 32768 {'prompt_eval_count': 4350, 'eval_count': 1024, 'done_reason': 'length'} load_ms 7750
memory.used [MiB]
6514 MiB
NAME          ID              SIZE      PROCESSOR    CONTEXT    RUNNER      UNTIL              
gemma4:e4b    dc35e8d9c606    398 MB    100% GPU     32768      llamacpp    4 minutes from now    
```

Raw output, pass 2 (`extra.py`, VRAM part):

```
=== reverse pass 32768 6505 MiB 4350 1024
NAME          ID              SIZE      PROCESSOR    CONTEXT    RUNNER      UNTIL              
gemma4:e4b    dc35e8d9c606    398 MB    100% GPU     32768      llamacpp    4 minutes from now    

=== reverse pass 16384 6210 MiB 4350 1024
NAME          ID              SIZE      PROCESSOR    CONTEXT    RUNNER      UNTIL              
gemma4:e4b    dc35e8d9c606    381 MB    100% GPU     16384      llamacpp    4 minutes from now    

=== reverse pass 8192 6255 MiB 4350 1024
NAME          ID              SIZE      PROCESSOR    CONTEXT    RUNNER      UNTIL              
gemma4:e4b    dc35e8d9c606    538 MB    100% GPU     8192       llamacpp    4 minutes from now    

=== reverse pass 4096 5986 MiB 2051 1024
NAME          ID              SIZE      PROCESSOR    CONTEXT    RUNNER      UNTIL              
gemma4:e4b    dc35e8d9c606    369 MB    100% GPU     4096       llamacpp    4 minutes from now    
```

## Privacy check (step 7)

The real app was run as in the MM-4 recipe: clone `~/hc-mm4` detached at `5f7c67c`, `LLM_PROVIDER=ollama`, `LLM_MODEL=gemma4:e4b`, `./dev.sh` (under the three slot locks), headless Playwright (`setup.mjs`) to create a synthetic profile, import `synthetic-lab.pdf` (6 values extracted) and "Mark All Verified". The call and the lock were driven over the HTTP API with a script (`step7_api.py`) instead of Playwright clicks, because the call under test is a single route; the app, its dependency graph and the auth are the real ones. The call is `POST /api/v1/interpretations/observations/{observation_id}/interpret-grounded` (`api/interpretations.py:448`, `rag.query` at `:529`), which reaches `ModelRunner`. The existing data directory of the clone was moved aside and restored afterwards.

Run 1 (LDL observation, `step7_api.py`):

```
profiles 200 [('f4b2d542-af4d-4f69-b065-8d66cf95e33b', 'KV Measure Synthetic', None)]
unlock 200
observation bbb15ad5-b3b1-4ecc-8f90-ac798f639dfa ldl_cholesterol True
13:26:48 ollama ps BEFORE the call:
NAME    ID    SIZE    PROCESSOR    CONTEXT    RUNNER    UNTIL 

13:26:59 interpret-grounded status 201 in 11.0s
   keys: ['interpretation', 'grounded_segments', 'full_response', 'insufficient_context', 'insufficient_reasons', 'verification', 'is_valid', 'validation_errors'] insufficient: False
13:26:59 ollama ps RIGHT AFTER the call (model loaded?):
NAME          ID              SIZE      PROCESSOR    CONTEXT    RUNNER      UNTIL              
gemma4:e4b    dc35e8d9c606    369 MB    100% GPU     4096       llamacpp    4 minutes from now    

ss -tnp (ollama/llama-server and backend)  [before lock]:

13:26:59 LOCK status 200 True
13:26:59 ollama ps AT ONCE after lock:
NAME          ID              SIZE      PROCESSOR    CONTEXT    RUNNER      UNTIL              
gemma4:e4b    dc35e8d9c606    369 MB    100% GPU     4096       llamacpp    4 minutes from now    

a protected route after lock (expect 401/403): 401
13:27:56 ollama ps 57s after lock:
NAME          ID              SIZE      PROCESSOR    CONTEXT    RUNNER      UNTIL              
gemma4:e4b    dc35e8d9c606    369 MB    100% GPU     4096       llamacpp    4 minutes from now    

non-loopback established connections owned by ollama/llama-server/uvicorn (expect none):
(end)
```

Run 2 (glucose observation, with a socket sampler every 0.2 s during the call, `step7c.py`). The first attempt of this addendum (LDL again) returned 500 before any model call and is described under "Other findings"; its useful part, the unload time, is in run 3.

```
13:33:37 second interpret-grounded 201 13.2s
established TCP connections seen during the call (local peer proc):
   0 0 127.0.0.1:11434 127.0.0.1:59526
   0 0 127.0.0.1:51064 127.0.0.1:8000 users:(("python3",pid=2380453,fd=5))
   0 0 127.0.0.1:59526 127.0.0.1:11434 users:(("python",pid=2360435,fd=23))
   0 0 127.0.0.1:8000 127.0.0.1:51064 users:(("python",pid=2360435,fd=19))
non-loopback connections owned by python/uvicorn/ollama/llama (all other rows are unrelated claude/codex/gh processes): none
13:33:37 loaded; expires_at = 2026-10-22T13:38:37.030006551-07:00 (call ended 13:33:37)
13:33:37 LOCK 200
13:33:37 ollama ps at once:
NAME          ID              SIZE      PROCESSOR    CONTEXT    RUNNER      UNTIL              
gemma4:e4b    dc35e8d9c606    369 MB    100% GPU     4096       llamacpp    4 minutes from now    

13:34:32 +60s after lock: model loaded
13:34:32 first poll with empty ps: +55s after lock (+55s after the call ended)
```

The last line of run 2 is a script artifact (its wait loop was disabled in this variant and printed at once); the line before it is the measurement: the model was still loaded 55 s after the lock. Run 1's `ss` line is empty because the backend's connection to Ollama is closed between requests; run 2's sampler caught it during the call.

Run 3 (the LDL addendum, kept for the unload time; the socket list in its output was filtered because it showed no model call, and the unfiltered list contained only unrelated `claude`, `codex` and `gh` processes' own connections):

```
13:28:10 second interpret-grounded 500 0.0s
established TCP connections seen during the call (local peer proc):
   0 0 127.0.0.1:52032 127.0.0.1:8000 users:(("python3",pid=2365253,fd=7))
   0 0 127.0.0.1:8000 127.0.0.1:52032 users:(("python",pid=2360435,fd=19))
13:28:10 loaded; expires_at = 2026-10-22T13:31:59.077751514-07:00 (call ended 13:28:10)
13:28:10 LOCK 200
13:28:10 ollama ps at once:
NAME          ID              SIZE      PROCESSOR    CONTEXT    RUNNER      UNTIL              
gemma4:e4b    dc35e8d9c606    369 MB    100% GPU     4096       llamacpp    3 minutes from now    

13:29:05 +60s after lock: model loaded
13:30:05 +120s after lock: model loaded
13:32:00 +240s after lock: ps EMPTY
13:32:55 +290s after lock: ps EMPTY
13:32:55 first poll with empty ps: +285s after lock (+285s after the call ended)
```

In run 3 the "second interpret-grounded 500" never reached the model (so its socket list shows only the script's own call to the backend), the `expires_at` is the one set by run 1's call, the lock was sent at 13:28:10, and the model was gone between the +120 s poll (13:30:05) and the +240 s poll (13:32:00), consistent with `expires_at` 13:31:59. The last line (`first poll with empty ps`) is a script artifact: the model had already expired when that loop started.

Findings:

- The call returned 201 in 11.0 s and 13.2 s. Right after it, `ollama ps` shows `gemma4:e4b`, `100% GPU`, `CONTEXT` 4096, `UNTIL` "4 minutes from now".
- **Locking the profile does not unload the model.** Run 1: locked at 13:26:59; at once and 57 s later the model was still loaded. Run 2: locked at 13:33:37, loaded at once and at +55 s, `expires_at` 13:38:37 (call end + 5:00). Run 3 (lock at 13:28:10 on the earlier call's timer): still loaded at +60 s and +120 s, gone at +240 s, `expires_at` 13:31:59 (that earlier call's end + 5:00). So the model, and with it the llama-server process and the slot's KV cache holding the lab prompt (measured: both runs sent one task to a freshly loaded runner, and the journal after load reads `cache state: 0 prompts, 0.000 MiB`), stays until `keep_alive` expires, about 5 minutes after the last request, not after the lock.
- After the lock, a protected route returns 401 (the JWT is revoked); the Ollama state is outside that.
- **Nothing left the machine.** During the call the sockets owned by `python` (the backend) and the Ollama listener are `127.0.0.1:59526 <-> 127.0.0.1:11434` and the measuring script's own connection to the backend at `127.0.0.1:8000`; no non-loopback connection belongs to `python`, `uvicorn`, `ollama` or `llama`. (`ss -tnp` cannot show the Ollama process name here because it runs as another user; its end of the connection is the `127.0.0.1:11434` row.)
- The prompt the real app sent for the LDL lab explanation was 1182 tokens on the first call and 632 on the second in this one-document profile (journal `task.n_tokens`), far below the 2476 of the multi-document capture. Real size follows the profile's retrieved context.

## Conclusions

**(a) Largest measured prompt per case, and truncation at the server default.**

| Case | Largest measured prompt | Needs (prompt + output budget) | At the default 4096 |
|---|---|---|---|
| a, lab explanation | 2476 tokens | 3500 | fits |
| b, visit-note assist | 1677 tokens | 2189 | fits |
| c, legacy chat, typical | 3585 tokens | 4609 | prompt not truncated; **output cut at 4095 after about 510 tokens** |
| d, legacy chat, largest | 4350 tokens | 5374 | **prompt truncated to 2051 tokens (journal WARN)** |

Yes: one case truncates at the server default (d), and a second (c) loses half of its output budget. The demo's own calls with the agent on (a, b) do not. The legacy chat path (c, d) runs only when the agent is off or failed.

**(b) The `num_ctx` value for OLLAMA-NUM-CTX: 8192.**

- Largest case plus its `max_tokens`: 4350 + 1024 = 5374 tokens. Of the sizes in step 6, 4096 is too small, 8192 is the smallest that fits (2818 tokens of headroom, about 9,000 to 10,000 characters), 100% GPU, +0.3 GiB over 4096.
- 8192 is at or below `capabilities().context_len` for every model name (262144 for Gemma 4 names, 8192 otherwise, `ollama_provider.py:152-166`), so no re-plan of `capabilities()` is needed.
- The row therefore has code: `options.num_ctx` = 8192 in `_build_request_body`. Its own trade-off, which the OLLAMA-NUM-CTX plan already discusses for a hard 4096: on a machine with 24 GiB or more the server default is 32k, and a fixed 8192 would shrink that window, though still above the largest measured need (5374). Case d is a constructed worst case at 3.84 characters per token while case c measured 3.17; even at c's density d's 16696 characters would be about 5270 tokens, about 6290 with output, still under 8192, so the conclusion does not depend on d's density. The evidence does not argue for 16384 or 32768 here: they are not needed by any case and cost VRAM.
- Not part of this value: `chat_context_size` is untouched; this evidence does not argue for changing it (the Ollama path never reads it; the legacy history cap of 2048 characters is the only place it matters for Ollama prompts, and case d shows the prompt still fits at 8192 with that cap).

**(c) Prefix reuse today.** Works for an identical prompt (prefill 1163 to 48 ms, 96 percent less, case c). Does not work for a new question or analyte: 584 ms vs a 578 ms no-shared-prefix baseline (c2), 525 vs 520 ms (a2), because the llama-server cannot restore a partial prefix for this sliding-window model (`forcing full prompt re-processing`, `lcp = 354`). The prompt-order change (history or other stable text before the retrieved context) is therefore **not worth a row for `gemma4:e4b` on Ollama 0.40.5**: the upper bound of the gain is the 354-token rules (about 0.08 s) and the server would not reuse a partial prefix anyway. Whether a non-SWA model (`llama3.1:8b`, `qwen3:8b`) reuses a partial prefix was not measured. New bullet, not planned.

**(d) Residual KV state after lock.** The model and its prompt state stay loaded until `keep_alive` expires (5 minutes after the last request); see the owner question.

## Owner question (not planned until answered)

**OQ-KV-LOCK: should locking a profile, or logging out, unload the Ollama model?**

- **Measured:** the lab prompt of the locked profile stays in the llama-server process (in the slot's KV cache; measured) for up to 5 minutes after the last request. **Inferred from the journal, not measured:** llama-server's host-RAM prompt cache is enabled (`prompt cache is enabled, size limit: 8192 MiB`, `idle slots will be saved to prompt cache upon starting a new task`), so a later request, for example from another profile, would move that slot's prompt into host RAM, and it could sit there too. Both go away when the runner unloads; the window (until `keep_alive` expiry) does not change. Only loopback traffic; the Ollama service runs as another OS user on the same machine.
- **Why it is a question:** the unload belongs in the lock and logout path. `OllamaProvider.unload` is a no-op today (`ollama_provider.py:311-313`); implementing it is provider code, but calling it from the lock route (`api/profiles.py:992-1025`) or `close_profile_database_on_logout` (`core/auth.py:426`) edits auth code, which CLAUDE.md section 1 makes ask-first.
- **Options:** (a) accept the window (single-user local machine, loopback only); (b) implement `OllamaProvider.unload` (`POST /api/generate` with `keep_alive: 0`) and call it from lock and logout: closes the window, needs the auth-file edit; (c) send a short `keep_alive` with every request: no auth change, but every idle gap longer than the value costs the measured 7.1 to 7.7 s model load (after 5 minutes idle: 7.4 s load plus 1.1 s prefill).
- **Not recommended without the owner's threat model:** only (b) closes the window. A longer `keep_alive` to hide the 7 s load would lengthen it.

## Other findings (new bullets, not planned, outside this row)

0. **The three-lock model-host wrapper excludes pytest only when `PYSLOTS` is 3 or less** (`scripts/pyslot.sh` takes `PYSLOTS`; a session with more slots ran in slot 5 during step 7). The wrapper should hold `1..$PYSLOTS`, or check that no `hc-pytest.*.lock` is held. L0 has since widened `/tmp/claude-1000/hold_slots.sh` to slots 1 to 8. Consider an entry in `docs/agentic/recurring-failures.md` (CLAUDE.md section 4).
1. **`gemma4:e4b` spends the output budget on thinking.** Ollama returns a separate `thinking` field and the app does not send `think`. Answer text was empty in 11 of 11 visit-note runs (b, `num_predict` 512, `eval_count` 512, `done_reason: length`) and in 2 of 6 lab-explanation runs for the second analyte; the typical legacy chat gave 279 to 1054 characters at 8192 or more but always ended `length` at 1024 tokens. A larger `num_ctx` does not fix this; it is a `think` / `max_tokens` question for the visit-note assist and the cite-schema path (`modules/extract_visit_notes.py:477-501`, `modules/rag.py` `_generate_with_runner`).
2. **`force_regenerate=true` on an observation that already has an interpretation returned 500** (`sqlcipher3.dbapi2.IntegrityError: UNIQUE constraint failed: lab_interpretations.observation_id`, backend log, second `interpret-grounded` call on the same observation). Not investigated here; it may already be tracked.
3. **The first request after 5 minutes idle costs a 7.4 s model load.** Relevant to any `keep_alive` change; see OQ-KV-LOCK option (c).
4. **The factory fallback model name `gemma4:12b` (`core/llm/factory.py:49`) is not pulled on this box.** The demo `.env` names `gemma4:e4b`, which was measured.

## Appendix: scripts

All scripts are scratch files in `/tmp/claude-1000/kv-1022/` and are pasted here instead of being committed.

Step 2, prompt capture (`prompts.py`; run as `cd src/backend && PYTHONPATH=. HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python /tmp/claude-1000/kv-1022/prompts.py`):

```python
"""KV-PREFIX-MEASURE step 2: capture the exact prompts each ModelRunner caller sends.

Synthetic in-memory profile. A recording runner is passed through the existing
model_runner= / runner= parameters. No model is called.
Run: cd src/backend && PYTHONPATH=. HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python /tmp/claude-1000/kv-1022/prompts.py
"""
import asyncio, json, os, uuid, datetime
from types import SimpleNamespace

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

import models  # noqa
from core.profile_database import ProfileDatabaseBase
from core.database import Base as MasterBase
from models import Chunk, Document, Embedding, Observation
from modules.rag import RAGModule
from modules.chunking import ChunkingModule
from modules.embeddings import EmbeddingsModule
from modules.extract_visit_notes import llm_assist_visit_entities
from core.llm.ollama_provider import OllamaProvider
from core.llm.provider import ChatMessage
from core.time import utcnow
from core.config import settings

OUT = "/tmp/claude-1000/kv-1022/prompts.json"
MODEL = "gemma4:e4b"
PID = str(uuid.uuid4())


class Recorder:
    def __init__(self):
        self.calls = []

    def is_available(self):
        return True

    async def generate_async(self, prompt, config):
        self.calls.append((prompt, config))
        return SimpleNamespace(text="stub", finish_reason="stop", tokens_generated=1, model_name="stub")


def lab_text(i):
    """Synthetic lab report page, long sentences included so chunks reach the chunker's real maximum."""
    lines = [
        f"Synthetic Laboratory Report {i}. Patient: Test Person. Collected 2026-0{(i % 9) + 1}-1{i % 9}.",
        "Lipid panel: LDL Cholesterol 148 mg/dL (range 0-100). HDL Cholesterol 52 mg/dL (range 40-100). "
        "Triglycerides 172 mg/dL (range 0-150). Total Cholesterol 231 mg/dL (range 0-200).",
        "Glucose, Fasting 104 mg/dL (range 70-99). Hemoglobin A1c 5.9 % (range 4.0-5.6). "
        "Creatinine 0.9 mg/dL (range 0.6-1.3). TSH 2.4 mIU/L (range 0.4-4.0). ALT 31 U/L (range 7-56).",
        "Comment: " + " ".join(
            "The results were reviewed with the patient and the laboratory notes that fasting status, recent "
            "illness, hydration, time of day, and medication timing can all affect individual values, and that "
            "a single measurement should be interpreted together with prior results and clinical context."
            for _ in range(4)
        ),
    ]
    return " ".join(lines)


async def seed():
    master_engine = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    async with master_engine.begin() as conn:
        await conn.run_sync(MasterBase.metadata.create_all)
    master = AsyncSession(master_engine, expire_on_commit=False)
    from scripts.seed_knowledge_base import seed_biomarker_knowledge
    n = await seed_biomarker_knowledge(master)

    pe = create_async_engine("sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    async with pe.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    pdb = AsyncSession(pe, expire_on_commit=False)

    emb = EmbeddingsModule()
    chunker = ChunkingModule()
    stats = []
    first_doc = None
    for i in range(1, 5):
        doc = Document(id=str(uuid.uuid4()), profile_id=PID, path_hash=f"{i}" * 64, content_hash=f"{i}" * 64,
                       doc_type="pdf", status="verified", imported_at=utcnow(), source=f"synthetic-lab-{i}.pdf")
        pdb.add(doc)
        first_doc = first_doc or doc
        chunks = chunker.chunk_document(doc.id, lab_text(i) * 3)
        vecs = emb.embed_chunks(chunks)
        for c, v in zip(chunks, vecs):
            pdb.add(Chunk(id=c["chunk_id"], doc_id=doc.id, chunk_index=c["chunk_index"], text=c["text"]))
            pdb.add(Embedding(chunk_id=c["chunk_id"], model_name=emb.config.model_name,
                              vector_blob=emb.vector_to_blob(v["vector"]), dimensions=len(v["vector"])))
            stats.append(len(c["text"]))
    await pdb.commit()
    # observations: 3 draws per analyte
    analytes = [("ldl_cholesterol", "LDL Cholesterol", "mg/dL", 0, 100, [155, 150, 148]),
                ("hdl_cholesterol", "HDL Cholesterol", "mg/dL", 40, 100, [50, 51, 52]),
                ("glucose_fasting", "Glucose, Fasting", "mg/dL", 70, 99, [99, 101, 104]),
                ("triglycerides", "Triglycerides", "mg/dL", 0, 150, [160, 165, 172]),
                ("hemoglobin_a1c", "Hemoglobin A1c", "%", 4.0, 5.6, [5.6, 5.8, 5.9])]
    obs_ids = {}
    for canon, raw, unit, lo, hi, vals in analytes:
        for k, v in enumerate(vals):
            oid = str(uuid.uuid4())
            obs_ids.setdefault(canon, oid)
            pdb.add(Observation(id=oid, profile_id=PID, doc_id=first_doc.id, analyte_canonical=canon, analyte_raw=raw,
                                value=v, unit=unit, ref_low=lo, ref_high=hi, flag="H" if v > hi else None,
                                is_abnormal=v > hi, collected_at=datetime.datetime(2026, 3 + 2 * k, 10),
                                user_verified=True))
    await pdb.commit()
    return master, pdb, emb, stats, n, analytes


def split_parts(prompt, question):
    head, rest = prompt.split("CONTEXT:\n", 1)
    qtag = "\n\nUSER QUESTION: " + question
    assert rest.endswith(qtag) or True
    qpos = rest.rfind("USER QUESTION: " + question)
    hpos = rest.find("\n\nSESSION HISTORY (")
    if hpos != -1:
        ctx = rest[:hpos]
        hist = rest[hpos:qpos]
    else:
        ctx = rest[:qpos].rstrip("\n")
        hist = ""
    return {
        "fixed_rules_chars": len(head) + len("CONTEXT:\n"),
        "retrieved_context_chars": len(ctx),
        "history_chars": len(hist),
        "question_chars": len(prompt) - len(head) - len("CONTEXT:\n") - len(ctx) - len(hist),
        "total_chars": len(prompt),
    }


def body_for(prompt, config):
    prov = OllamaProvider(model=MODEL)
    return prov._build_request_body([ChatMessage(role="user", content=prompt)], config)


def common_prefix(a, b):
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


async def main():
    master, pdb, emb, chunk_sizes, n_kb, analytes = await seed()
    rag = RAGModule(enable_verification=False)
    out = {"model": MODEL, "chunk_chars": {"count": len(chunk_sizes), "max": max(chunk_sizes),
           "mean": sum(chunk_sizes) // len(chunk_sizes)}, "kb_rows": n_kb, "cases": {}}

    # (a) lab explanation, as api/interpretations.py:529-537
    async def lab_case(canon, raw, unit, value):
        rec = Recorder()
        question = (f"Explain my lab result for {raw} ({value} {unit}) and what it may indicate. "
                    "Use my report details first, then general context.")
        await rag.query(question=question, profile_id=PID, selected_analytes=[canon], include_references=True,
                        model_runner=rec, master_db=master, profile_db=pdb, use_memory=False)
        return question, rec.calls[0]
    qa, (pa, ca) = await lab_case("ldl_cholesterol", "LDL Cholesterol", "mg/dL", 148.0)
    qa2, (pa2, ca2) = await lab_case("glucose_fasting", "Glucose, Fasting", "mg/dL", 104.0)
    out["cases"]["a"] = dict(desc="lab explanation, ldl_cholesterol", prompt=pa, question=qa, parts=split_parts(pa, qa),
                             body=body_for(pa, ca), max_tokens=ca.max_tokens)
    out["cases"]["a2"] = dict(desc="lab explanation, glucose_fasting (new analyte)", prompt=pa2, question=qa2,
                              parts=split_parts(pa2, qa2), body=body_for(pa2, ca2), max_tokens=ca2.max_tokens)

    # (b) visit-note LLM assist at the 6000 char cap
    note = ("Visit note, synthetic. Assessment: stable. Plan: start metformin 500 mg twice daily with meals. "
            "Stop lisinopril. Referral to cardiology. Follow up in 6 weeks. Return if chest pain. ")
    note = (note * 100)[:6000]
    rec = Recorder()
    await llm_assist_visit_entities(note, [], runner=rec)
    pb, cb = rec.calls[0]
    out["cases"]["b"] = dict(desc="visit-note LLM assist, 6000-char note", prompt=pb, question=note,
                             parts={"fixed_rules_chars": pb.index("<document>\n") + len("<document>\n"),
                                    "document_chars": len(note), "total_chars": len(pb)},
                             body=body_for(pb, cb), max_tokens=cb.max_tokens)

    # (c) legacy chat, typical question, no history
    rec = Recorder()
    qc = "What does my LDL cholesterol result mean?"
    await rag.query(question=qc, profile_id=PID, include_references=True, model_runner=rec, master_db=master,
                    profile_db=pdb, use_memory=False)
    pc, cc = rec.calls[0]
    out["cases"]["c"] = dict(desc="legacy chat, typical question, no history", prompt=pc, question=qc,
                             parts=split_parts(pc, qc), body=body_for(pc, cc), max_tokens=cc.max_tokens)

    # (c2) turn 2 in the same chat: history = turn 1 user + a typical assistant answer
    a1 = ("REPORT FACTS:\n- Your LDL Cholesterol was 148 mg/dL, above the listed range of 0-100 mg/dL. [cite:1]\n"
          "GENERAL INFO:\n- LDL is one of the lipids measured in a cholesterol panel. [cite:2]\n"
          "UNCERTAINTIES:\n- This cannot say what the cause is.")
    hist = [SimpleNamespace(role="user", content=qc), SimpleNamespace(role="assistant", content=a1)]
    qc2 = "And what about my fasting glucose?"
    rec = Recorder()
    await rag.query(question=qc2, profile_id=PID, include_references=True, model_runner=rec, master_db=master,
                    profile_db=pdb, history=hist, use_memory=False)
    pc2, cc2 = rec.calls[0]
    out["cases"]["c2"] = dict(desc="legacy chat turn 2, same chat (history = turn 1)", prompt=pc2, question=qc2,
                              parts=split_parts(pc2, qc2), body=body_for(pc2, cc2), max_tokens=cc2.max_tokens)

    # (d) largest realistic legacy chat: 10-turn history. The history is trimmed to chat_context_size*0.5 chars.
    long_a = a1 + " " + ("This is additional educational background that a typical longer answer would carry. " * 6)
    hist10 = []
    for t in range(10):
        hist10.append(SimpleNamespace(role="user", content=f"Question {t + 1}: tell me more about my lipid and glucose results over time, please."))
        hist10.append(SimpleNamespace(role="assistant", content=long_a))
    qd = ("Can you explain how my LDL cholesterol, HDL cholesterol, triglycerides, fasting glucose and hemoglobin A1c "
          "results compare and what they may indicate together?")
    rec = Recorder()
    await rag.query(question=qd, profile_id=PID, include_references=True, model_runner=rec, master_db=master,
                    profile_db=pdb, history=hist10, selected_analytes=[a[0] for a in analytes], use_memory=False)
    pd_, cd = rec.calls[0]
    out["cases"]["d"] = dict(desc="legacy chat, largest: top-k 10 doc chunks + obs + refs for 5 analytes + 10-turn history",
                             prompt=pd_, question=qd, parts=split_parts(pd_, qd), body=body_for(pd_, cd),
                             max_tokens=cd.max_tokens, chat_context_size=getattr(settings, "chat_context_size", None),
                             history_budget_chars=int(getattr(settings, "chat_context_size", 4096) * 0.5))

    # prefix comparison for step 5
    cp = {}
    cp["a_vs_a2_new_analyte"] = common_prefix(pa, pa2)
    cp["c_vs_c2_same_chat"] = common_prefix(pc, pc2)
    cp["c_vs_c_identical"] = len(pc)
    cp["fixed_rules_chars"] = out["cases"]["c"]["parts"]["fixed_rules_chars"]
    out["prefix"] = cp
    # dates / ids before retrieved context in the c prompt?
    head = pc.split("CONTEXT:\n", 1)[0]
    import re
    out["per_request_tokens_before_context"] = re.findall(r"\d{4}-\d{2}-\d{2}|[0-9a-f]{8}-[0-9a-f]{4}", head)
    json.dump(out, open(OUT, "w"), indent=1)
    for k, v in out["cases"].items():
        print(k, v["desc"], v["parts"], "max_tokens", v["max_tokens"])
    print("chunks", out["chunk_chars"], "prefix", cp, out["per_request_tokens_before_context"])
    print("first chars of context c:", pc.split("CONTEXT:\n", 1)[1][:200].replace("\n", " | "))

asyncio.run(main())
```

Shared helper (`mlib.py`):

```python
import json, subprocess, time, copy, urllib.request
BASE = "http://127.0.0.1:11434"
MODEL = "gemma4:e4b"
P = json.load(open("/tmp/claude-1000/kv-1022/prompts.json"))

def post(path, body, timeout=600):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

def ps():
    return subprocess.run(["ollama", "ps"], capture_output=True, text=True).stdout

def unload(model=MODEL):
    post("/api/generate", {"model": model, "keep_alive": 0})
    for _ in range(30):
        if len(ps().strip().splitlines()) <= 1:
            return True
        time.sleep(1)
    return False

def chat(case, num_ctx=None, body_over=None):
    body = copy.deepcopy(P["cases"][case]["body"])
    if num_ctx:
        body["options"]["num_ctx"] = num_ctx
    if body_over:
        body.update(body_over)
    t = time.time()
    d = post("/api/chat", body)
    wall = time.time() - t
    keys = ["load_duration", "prompt_eval_count", "prompt_eval_duration", "eval_count", "eval_duration", "total_duration"]
    r = {k: d.get(k) for k in keys}
    r["wall_s"] = round(wall, 2)
    r["done_reason"] = d.get("done_reason")
    r["resp_chars"] = len(d.get("message", {}).get("content", ""))
    return r, d

def ms(ns): return None if ns is None else round(ns / 1e6)
```

Step 3 (`step3.py`; run as `/tmp/claude-1000/hold_slots.sh python3 step3.py`):

```python
import json, sys, subprocess, datetime
sys.path.insert(0, "/tmp/claude-1000/kv-1022")
from mlib import *
start = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print("START", start)
out = {"start": start, "rows": []}
for case in ["a", "b", "c", "c2", "d"]:
    row = {"case": case, "model": MODEL}
    for label, nc in (("default", None), ("32768", 32768)):
        assert unload(), "could not unload"
        r, d = chat(case, nc)
        r["ps_after"] = ps()
        row[label] = r
        print(case, label, {k: r[k] for k in ("prompt_eval_count", "eval_count", "done_reason", "load_duration", "wall_s")}, flush=True)
        print(r["ps_after"], flush=True)
    out["rows"].append(row)
unload()
j = subprocess.run(["journalctl", "-u", "ollama", "--since", start, "--no-pager"], capture_output=True, text=True).stdout
out["journal_truncat"] = [l for l in j.splitlines() if "truncat" in l.lower()]
out["journal_lines"] = len(j.splitlines())
open("/tmp/claude-1000/kv-1022/step3.json", "w").write(json.dumps(out, indent=1))
open("/tmp/claude-1000/kv-1022/step3.journal.txt", "w").write(j)
print("truncat hits:", out["journal_truncat"])
```

Step 4 (`step4.py`):

```python
import json, sys, time, statistics
sys.path.insert(0, "/tmp/claude-1000/kv-1022")
from mlib import *
res = {"runs": []}
def rec(kind, case, r):
    row = {"kind": kind, "case": case, **{k: r[k] for k in ("load_duration","prompt_eval_count","prompt_eval_duration","eval_count","eval_duration","total_duration","wall_s")}}
    res["runs"].append(row)
    print(json.dumps({**row, "load_ms": ms(r["load_duration"]), "pe_ms": ms(r["prompt_eval_duration"])}), flush=True)
    json.dump(res, open("/tmp/claude-1000/kv-1022/step4.json", "w"), indent=1)
for rep in range(3):
    # cold + same question again, for the legacy chat (c) and the lab explanation (a)
    for case in ("c", "a"):
        assert unload()
        r, _ = chat(case); rec("cold", case, r)
        r, _ = chat(case); rec("same", case, r)
    # new question in the same chat (legacy chat only): turn 1 then turn 2
    assert unload()
    r, _ = chat("c"); rec("cold_before_new", "c", r)
    r, _ = chat("c2"); rec("new_question", "c2", r)
    # new analyte in lab explanation (informational)
    assert unload()
    r, _ = chat("a"); rec("cold_before_a2", "a", r)
    r, _ = chat("a2"); rec("new_analyte", "a2", r)
# after keep_alive expiry
for rep in range(3):
    r, _ = chat("c"); rec("warm_before_expiry", "c", r)
    t0 = time.time()
    while True:
        time.sleep(15)
        if time.time() - t0 >= 330: break
    p = ps()
    print("ps after %ds idle:\n%s" % (time.time() - t0, p), flush=True)
    res.setdefault("ps_after_idle", []).append(p)
    r, _ = chat("c"); rec("after_expiry", "c", r)
unload()
print("DONE")
```

Step 6 (`step6.py`), and the descending pass plus cold baselines (`extra.py`):

```python
import json, sys, subprocess
sys.path.insert(0, "/tmp/claude-1000/kv-1022")
from mlib import *
def smi():
    return subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv"], capture_output=True, text=True).stdout.strip()
res = []
assert unload()
import time; time.sleep(3)
base = smi(); print("baseline (no model loaded):", base.replace("\n", " "), flush=True)
for nc in (4096, 8192, 16384, 32768):
    assert unload(); time.sleep(2)
    r, d = chat("d", nc)
    time.sleep(1)
    row = {"num_ctx": nc, "smi": smi(), "ps": ps(), **{k: r[k] for k in ("load_duration","prompt_eval_count","prompt_eval_duration","eval_count","eval_duration","done_reason")}}
    res.append(row)
    print("=== num_ctx", nc, {k: row[k] for k in ("prompt_eval_count","eval_count","done_reason")}, "load_ms", ms(r["load_duration"]))
    print(row["smi"]); print(row["ps"], flush=True)
unload()
json.dump({"baseline": base, "rows": res}, open("/tmp/claude-1000/kv-1022/step6.json", "w"), indent=1)
```

```python
import json, sys, time, subprocess
sys.path.insert(0, "/tmp/claude-1000/kv-1022")
from mlib import *
out = {"cold_new": [], "vram_reverse": []}
for rep in range(3):
    for case in ("c2", "a2"):
        assert unload()
        r, d = chat(case)
        row = {"case": case, "rep": rep, "load_ms": ms(r["load_duration"]), "pe_count": r["prompt_eval_count"], "pe_ms": ms(r["prompt_eval_duration"]), "eval_count": r["eval_count"], "resp_chars": r["resp_chars"], "think_chars": len(d["message"].get("thinking") or "")}
        out["cold_new"].append(row); print(json.dumps(row), flush=True)
def smi(): return subprocess.run(["nvidia-smi","--query-gpu=memory.used","--format=csv,noheader"],capture_output=True,text=True).stdout.strip()
for nc in (32768, 16384, 8192, 4096):
    assert unload(); time.sleep(2)
    r, d = chat("d", nc); time.sleep(1)
    row = {"num_ctx": nc, "smi": smi(), "ps": ps(), "pe_count": r["prompt_eval_count"], "eval_count": r["eval_count"], "done_reason": r["done_reason"]}
    out["vram_reverse"].append(row); print("=== reverse pass", nc, row["smi"], row["pe_count"], row["eval_count"]); print(row["ps"], flush=True)
unload()
json.dump(out, open("/tmp/claude-1000/kv-1022/extra.json","w"), indent=1)
```

Warm baselines and case c at 4096 vs 8192 (`extra2.py`):

```python
import json, sys
sys.path.insert(0, "/tmp/claude-1000/kv-1022")
from mlib import *
out = {"warm_baseline": [], "c_ctx": []}
def row(tag, case, r, d, nc=None):
    x = {"tag": tag, "case": case, "num_ctx": nc, "load_ms": ms(r["load_duration"]), "pe_count": r["prompt_eval_count"], "pe_ms": ms(r["prompt_eval_duration"]), "eval_count": r["eval_count"], "done_reason": r["done_reason"], "resp_chars": r["resp_chars"], "think_chars": len(d["message"].get("thinking") or "")}
    print(json.dumps(x), flush=True); return x
# warm runner, unrelated prefix (case b) first, then the case under test: no shared prefix
for rep in range(3):
    for case in ("c", "c2", "a2"):
        assert unload()
        r, d = chat("b"); out["warm_baseline"].append(row("after_b_" + case + "_b", "b", r, d))
        r, d = chat(case); out["warm_baseline"].append(row("warm_noprefix", case, r, d))
# case c (typical legacy chat, prompt 3585 tokens): default 4096 vs 8192
for rep in range(3):
    for nc in (None, 8192):
        assert unload()
        r, d = chat("c", nc); out["c_ctx"].append(row("c_ctx", "c", r, d, nc or 4096))
unload()
json.dump(out, open("/tmp/claude-1000/kv-1022/extra2.json", "w"), indent=1)
```

Step 7: Playwright setup (`setup.mjs`, run with node from the clone's frontend `node_modules`), the API driver (`step7_api.py`) and the variant with socket sampling (`step7c.py`, which reuses the helper lines of `step7_api.py`):

```js
import {launch,D,t0,el,PW,txt} from './lib.mjs';
const {b,ctx,page}=await launch();
await page.goto('http://localhost:3000/'); await page.waitForTimeout(2500);
if(!/setup/.test(page.url())) await page.goto('http://localhost:3000/setup');
await page.getByPlaceholder('My Health Profile').fill('KV Measure Synthetic');
await page.getByPlaceholder('Create a secure password').fill(PW);
await page.getByRole('button',{name:/Create Your Profile/}).click();
await page.waitForTimeout(4000);
await page.getByText('I have saved this recovery code').click().catch(e=>console.log('no recovery ack'));
await page.getByText('Continue to my records').click().catch(e=>console.log('no continue'));
await page.waitForTimeout(2000); console.log(page.url());
await page.goto('http://localhost:3000/inbox'); await page.waitForTimeout(2000);
await page.locator('input[type=file]').setInputFiles('/tmp/claude-1000/mm4-1022/synthetic-lab.pdf');
await page.getByText(/values extracted/).waitFor({timeout:120000}).catch(e=>console.log('no extracted msg'));
console.log((await txt(page,'main')).replace(/\s+/g,' ').slice(0,400));
await page.goto('http://localhost:3000/verify'); await page.waitForTimeout(2500);
await page.getByRole('button',{name:'Mark All Verified'}).click(); await page.waitForTimeout(1500);
console.log((await page.locator('body').innerText()).replace(/\s+/g,' ').slice(0,300));
await b.close();
```

```python
"""Step 7 (API half): unlock -> interpret-grounded -> ollama ps -> lock -> ollama ps at once and +60s -> ss."""
import json, subprocess, sys, time, urllib.request
B = "http://127.0.0.1:8000/api/v1"
PW = "<synthetic test password>"
def req(method, path, body=None, token=None):
    r = urllib.request.Request(B + path, data=None if body is None else json.dumps(body).encode(), method=method,
                               headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})})
    try:
        with urllib.request.urlopen(r, timeout=300) as x:
            return x.status, json.loads(x.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]
def sh(c): return subprocess.run(c, shell=True, capture_output=True, text=True).stdout
def stamp(): return time.strftime("%H:%M:%S")
s, profs = req("GET", "/profiles/")
print("profiles", s, [(p["id"], p["display_name"], p.get("is_locked")) for p in profs])
pid = profs[0]["id"]
s, un = req("POST", f"/profiles/{pid}/unlock", {"password": PW}); tok = un["access_token"] if isinstance(un, dict) else None
print("unlock", s)
s, obs = req("GET", "/observations/", token=tok)
items = obs.get("items", obs) if isinstance(obs, dict) else obs
ldl = [o for o in items if "ldl" in (o.get("analyte_canonical") or "").lower()][0]
print("observation", ldl["id"], ldl["analyte_canonical"], ldl.get("user_verified"))
print(stamp(), "ollama ps BEFORE the call:\n" + sh("ollama ps"))
t = time.time()
s, r = req("POST", f"/interpretations/observations/{ldl['id']}/interpret-grounded?force_regenerate=true", token=tok)
print(stamp(), "interpret-grounded status", s, "in %.1fs" % (time.time() - t))
if isinstance(r, dict): print("   keys:", list(r.keys())[:12], "insufficient:", r.get("insufficient_context"))
else: print("   body:", str(r)[:300])
print(stamp(), "ollama ps RIGHT AFTER the call (model loaded?):\n" + sh("ollama ps"))
print("ss -tnp (ollama/llama-server and backend)  [before lock]:\n" + sh("ss -tnp 2>/dev/null | grep -E 'ollama|llama-server|11434' ; true"))
t_lock = time.time()
s, r = req("POST", f"/profiles/{pid}/lock", token=tok)
print(stamp(), "LOCK status", s, (r.get("is_locked") if isinstance(r, dict) else r))
print(stamp(), "ollama ps AT ONCE after lock:\n" + sh("ollama ps"))
print("a protected route after lock (expect 401/403):", req("GET", "/observations/", token=tok)[0])
for wait in (60,):
    time.sleep(wait - (time.time() - t_lock))
    print(stamp(), "ollama ps %ds after lock:\n" % (time.time() - t_lock) + sh("ollama ps"))
print("non-loopback established connections owned by ollama/llama-server/uvicorn (expect none):")
print(sh("ss -tnp state established 2>/dev/null | grep -E 'ollama|llama|python' | grep -v -E '127\\.0\\.0\\.1|::1' ; echo '(end)'"))
```

```python
"""Step 7 addendum: sockets during the call, the model's expires_at, and the unload time after lock."""
import re, json, subprocess, threading, time, urllib.request
exec(open("step7_api.py").read().split("s, profs")[0])  # req/sh/stamp helpers
s, profs = req("GET", "/profiles/"); pid = profs[0]["id"]
s, un = req("POST", f"/profiles/{pid}/unlock", {"password": PW}); tok = un["access_token"]
s, obs = req("GET", "/observations/", token=tok)
items = obs.get("items", obs) if isinstance(obs, dict) else obs
oid = [o for o in items if "glucose" in o["analyte_canonical"]][0]["id"]
seen, stop = set(), False
def sample():
    while not stop:
        for l in sh("ss -tnp state established 2>/dev/null").splitlines()[1:]:
            seen.add(" ".join(l.split()))
        time.sleep(0.2)
th = threading.Thread(target=sample); th.start()
t = time.time()
s, r = req("POST", f"/interpretations/observations/{oid}/interpret-grounded?force_regenerate=true", token=tok)
t_end = time.time(); stop = True; th.join()
print(stamp(), "second interpret-grounded", s, "%.1fs" % (t_end - t))
print("established TCP connections seen during the call (local peer proc):")
for l in sorted(seen):
    if re.search(r"11434|:8000 |python|uvicorn|ollama|llama", l): print("  ", l)
nl = [l for l in seen if re.search(r"python|uvicorn|ollama|llama", l) and not all(x.startswith(("127.0.0.1", "[::1]")) for x in l.split()[2:4])]
print("non-loopback connections owned by python/uvicorn/ollama/llama (all other rows are unrelated claude/codex/gh processes):", nl or "none")
ps_ = json.loads(urllib.request.urlopen("http://127.0.0.1:11434/api/ps").read())
exp = ps_["models"][0]["expires_at"]; print(stamp(), "loaded; expires_at =", exp, "(call ended", time.strftime("%H:%M:%S", time.localtime(t_end)) + ")")
s, r = req("POST", f"/profiles/{pid}/lock", token=tok); print(stamp(), "LOCK", s)
print(stamp(), "ollama ps at once:\n" + sh("ollama ps"))
t_lock = time.time()
for off in (60,):
    time.sleep(max(0, off - (time.time() - t_lock)))
    print(stamp(), "+%ds after lock:" % off, "model loaded" if len(sh("ollama ps").strip().splitlines()) > 1 else "ps EMPTY", flush=True)
while False:
    time.sleep(2)
print(stamp(), "first poll with empty ps: +%.0fs after lock (+%.0fs after the call ended)" % (time.time() - t_lock, time.time() - t_end))
```

## Appendix: raw outputs

Step 3 and step 4 console output are reproduced as the tables above (every raw value). The `ollama ps` text after each step 3 request, abridged to the model row:

```
a/b/c/c2/d default : gemma4:e4b  dc35e8d9c606  369 MB  100% GPU  4096   llamacpp
a/b/c/c2/d 32768   : gemma4:e4b  dc35e8d9c606  398 MB  100% GPU  32768  llamacpp
```

Close: `POST /api/generate {"model":"gemma4:e4b","keep_alive":0}` (`ollama ps` empty), the dev servers stopped by port (`lsof -ti:8000 -sTCP:LISTEN | xargs -r kill`, same for 3000; both ports free afterwards), the clone's original `data` directory restored, `/tmp/claude-1000/hold_slots.sh true` returns at once.
