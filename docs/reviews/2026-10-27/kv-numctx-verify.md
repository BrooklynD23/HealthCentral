# KV-NUMCTX-VERIFY: Ollama runs the app's requests at num_ctx 8192 on the model host

**Last Updated:** 2026-10-27
**Owner:** repository owner
**Status:** Measured evidence only. All five pass conditions hold. No product code, test, config, flag or default changed. No queue, count slot or ask-first file edited.
**Refresh Trigger:** the Ollama version or the demo model changes, `_OLLAMA_NUM_CTX` or `_build_request_body` changes, `RAGModule.SYSTEM_PROMPT` / `compose_prompt` / the cite schema changes, or the journal format of the Ollama server changes.

Plan: [KV-NUMCTX-VERIFY](../../plans/2026-10-22-mvp-rows-plan.md#kv-numctx-verify-show-that-ollama-really-runs-the-apps-requests-at-num_ctx-8192-model-host-no-code). Queue row: [queue.md, Planned 2026-10-27](../../plans/2026-10-15-build-program/queue.md#planned-2026-10-27-planner). Baseline: [kv-prefix-measure.md](../2026-10-22/kv-prefix-measure.md).

## Verdict

- All five pass conditions hold on this run (table below). Nothing failed, so no follow-up bullet is proposed for a failed check.
- Ollama 0.40.5 loaded `gemma4:e4b` at context 8192 for the app's own runner (step 3) and for the raw requests (step 4). `ollama ps` shows `CONTEXT 8192` and `100% GPU`.
- The journal has no `truncating input prompt` line and no `truncated = 1` line in any window of an 8192 request.
- Case d at 8192 gives the same prompt count as at 32768 (4020 tokens). The 2026-10-22 run had 4350 at 32768 and a truncated 2051 at the 4096 default. This run's case d prompt is 772 characters shorter than the 2026-10-22 one (step 2 table), so the two runs are not directly comparable.
- Three observations outside the pass conditions are listed at the end. None changes a pass result.

## Pass conditions

The conditions were written in the plan before the run. They were not changed after the raw outputs were seen.

| # | Condition | Evidence | Result |
|---|---|---|---|
| (i) | step 2: `num_ctx` is 8192 in both captured bodies (c and d) | `prompts.json`: case c `options.num_ctx` 8192, case d `options.num_ctx` 8192 | PASS |
| (ii) | step 3: `ollama ps` shows CONTEXT 8192 and PROCESSOR 100% GPU | step 3 `PS_AFTER`: `gemma4:e4b ... 100% GPU  8192` | PASS |
| (iii) | step 4: case d `prompt_eval_count` at 8192 equals the 32768 run's count | 4020 at 8192 and 4020 at 32768 | PASS |
| (iv) | step 5: no `truncating input prompt` and no `truncated = 1` line inside any 8192 request window | 0 and 0. The journal has 8 `truncat` hits and every one reads `truncated = 0` (step 5) | PASS |
| (v) | step 4: case c at 8192 reaches `eval_count` 1024 or ends with `done_reason` `stop` | `eval_count` 1024 (the `num_predict` cap); `done_reason` `length` | PASS |

## Isolation

- Every model call ran as `bash /tmp/claude-1000/hold_slots.sh <cmd>` (pyslot locks 1 to 8). No pytest ran in this PR. No UI test process ran.
- The pre-step check is `quiet_check.sh` (script below). Its raw output before each model step:

```text
before step 2 (exit 0): load1=1.30 gpu_mib_used=501 ollama_ps_lines=0 at=2026-10-27T22:32:00-07:00
before step 3 (exit 0): load1=0.62 gpu_mib_used=502 ollama_ps_lines=0 at=2026-10-27T22:33:01-07:00
before step 4 (exit 0): load1=1.08 gpu_mib_used=5577 ollama_ps_lines=1 at=2026-10-27T22:33:36-07:00
```

Before step 4 the GPU held the gemma4 model that step 3 had left loaded (keep_alive 5 min). That is expected: step 4 unloads before each request. Step 5 is a journal read and makes no model call.
- The first three check runs reported false matches: two for `playwright/vitest` and one for `pytest/pyslot`. Each match was the agent's own shell command text, not a running process. Each check was re-run clean. They are not evidence of another job.
- Other model-host rows were checked by process name (QWEN3-4B-TIER, JUDGE-LAYA-FT, JUDGE-NLI-TUNE, MM-2, AUDIT-DB). No matching process was found. The repo does not record their process names, so this check cannot rule out a row that runs under another name.

## Step 1: setup record

Commands and raw output. The unit's `PATH` value is elided; it is the only line in `Environment`.

```
## ollama -v
ollama version is 0.40.5

## systemctl show ollama -p Environment
Environment="PATH=<elided>"
(no other variable. OLLAMA_CONTEXT_LENGTH is NOT set on this unit.)

## ollama list | grep gemma4:e4b
gemma4:e4b     dc35e8d9c606    6.6 GB    11 days ago

## nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv
name, memory.total [MiB], memory.used [MiB]
NVIDIA GeForce RTX 3080, 10240 MiB, 501 MiB

## ollama ps (before any step)
NAME    ID    SIZE    PROCESSOR    CONTEXT    RUNNER    UNTIL
(header only: no model loaded)

## worktree SHA
8d313b5afe22305446f087e2c4c38bb9270157db
(branch docs/kv-numctx-verify-ollama-8192-evidence: origin/main 6b3dd27d plus the empty claim commit 8d313b5a)

## git grep -n "_OLLAMA_NUM_CTX = 8192" -- src/backend/core/llm/ollama_provider.py
src/backend/core/llm/ollama_provider.py:42:_OLLAMA_NUM_CTX = 8192
```

The embedding bundle is present in the worktree at `src/backend/models/embeddings/all-MiniLM-L6-v2` (gitignored; `model.safetensors`, tokenizer and config files), so the step 2 script ran with `HF_HUB_OFFLINE=1`.

## Step 2: capture

Command: `cd src/backend && OUT=/tmp/claude-1000/kvv-2026-10-27/prompts.json PYTHONPATH=. HF_HUB_OFFLINE=1 bash /tmp/claude-1000/hold_slots.sh ~/venvs/asclexis-311/bin/python /tmp/claude-1000/kvv-2026-10-27/prompts.py`. Exit code 0, and `prompts.json` was written (138641 bytes). The full log is at `/tmp/claude-1000/kvv-2026-10-27/step2_prompts.log`. Only the case summary lines are pasted here. SQLAlchemy `greenlet is being finalized` tracebacks printed after the last line were filtered out.

Raw case summary:

```text
a lab explanation, ldl_cholesterol {'fixed_rules_chars': 1449, 'retrieved_context_chars': 7789, 'history_chars': 0, 'question_chars': 149, 'total_chars': 9387} max_tokens 1024
a2 lab explanation, glucose_fasting (new analyte) {'fixed_rules_chars': 1449, 'retrieved_context_chars': 6629, 'history_chars': 0, 'question_chars': 150, 'total_chars': 8228} max_tokens 1024
b visit-note LLM assist, 6000-char note {'fixed_rules_chars': 700, 'document_chars': 6000, 'total_chars': 6725} max_tokens 512
c legacy chat, typical question, no history {'fixed_rules_chars': 1449, 'retrieved_context_chars': 9865, 'history_chars': 0, 'question_chars': 58, 'total_chars': 11372} max_tokens 1024
c2 legacy chat turn 2, same chat (history = turn 1) {'fixed_rules_chars': 1449, 'retrieved_context_chars': 6922, 'history_chars': 359, 'question_chars': 49, 'total_chars': 8779} max_tokens 1024
d legacy chat, largest: top-k 10 doc chunks + obs + refs for 5 analytes + 10-turn history {'fixed_rules_chars': 1449, 'retrieved_context_chars': 12563, 'history_chars': 1738, 'question_chars': 174, 'total_chars': 15924} max_tokens 1024
chunks {'count': 32, 'max': 781, 'mean': 637} prefix {'a_vs_a2_new_analyte': 1471, 'c_vs_c2_same_chat': 1450, 'c_vs_c_identical': 11372, 'fixed_rules_chars': 1449} []
```

Comparison with the 2026-10-22 table (`kv-prefix-measure.md`, "Prompt sizes"). Differences are reported, not adjusted.

| Case | 2026-10-22 total chars | 2026-10-27 total chars | Difference | `num_ctx` in captured body |
|---|---|---|---|---|
| a, lab explanation (LDL) | 9387 | 9387 | 0 | 8192 |
| a2, lab explanation (glucose) | 8228 | 8228 | 0 | 8192 |
| b, visit-note assist (6000 chars) | 6725 | 6725 | 0 | 8192 |
| c, legacy chat, typical | 11372 | 11372 | 0 | **8192** |
| c2, legacy chat, turn 2 | 8779 | 8779 | 0 | 8192 |
| d, legacy chat, largest | 16696 | 15924 | **-772** | **8192** |

Case d: the retrieved-context part went from 13335 to 12563 characters (-772). The fixed rules (1449), history (1738) and question (174) are unchanged. The cause was not investigated in this run.

## Step 3: through the app's runner

Setup: `LLM_PROVIDER=ollama`, `LLM_MODEL=gemma4:e4b`, `get_model_runner()`, then `generate_async(prompt_d, config_d)`. `config_d` is an `InferenceConfig` built from the captured case d body: `max_tokens` 1024 (`num_predict`), `temperature` 0.1, `top_p` 0.9, `stop_sequences` none, `response_schema` = the cite schema (`format`), `think` none, `timeout_seconds` 300. The model was unloaded first and `ollama ps` was empty before the call. The provider's `_build_request_body` was wrapped in the scratch script only to record the body the runner sent; product code is not changed.

Command: `cd src/backend && PYTHONPATH=. HF_HUB_OFFLINE=1 bash /tmp/claude-1000/hold_slots.sh ~/venvs/asclexis-311/bin/python /tmp/claude-1000/kvv-2026-10-27/step3_runner.py`. Exit code 0. Raw output (INFO and progress lines removed):

```text
STEP3_START 2026-10-27T22:33:02-07:00
PROVIDER OllamaProvider model gemma4:e4b
RESULT {
 "step3_start": "2026-10-27T22:33:02-07:00",
 "t0": "2026-10-27T22:33:02-07:00",
 "t1": "2026-10-27T22:33:20-07:00",
 "provider_class": "OllamaProvider",
 "provider_is_ollama": true,
 "finish_reason": "stop",
 "tokens_generated": 1024,
 "model_name": "gemma4:e4b",
 "text_chars": 0,
 "sent_num_ctx": 8192,
 "sent_body_equals_captured_d": true
}
PS_AFTER
NAME          ID              SIZE      PROCESSOR    CONTEXT    RUNNER      UNTIL              
gemma4:e4b    dc35e8d9c606    538 MB    100% GPU     8192       llamacpp    4 minutes from now    

ANSWER_BEGIN

ANSWER_END
```

Notes on step 3:

- The body the runner sent equals the captured case d body (`sent_body_equals_captured_d` true), and `num_ctx` in that body is 8192.
- `finish_reason` shows `stop` although 1024 tokens (the cap) were generated. See observation 1.
- The answer text is empty (0 characters). See observation 2.
- The journal window for this request is 22:33:02 to 22:33:20 (`t0` to `t1`).

## Step 4: token counts

Order: for case d, then case c; for each, 8192 first (captured body unchanged), then the same body with `options.num_ctx` 32768. The model was unloaded before each request (`keep_alive` 0, measurement only). `t_before` and `t_after` are the `date -Is` format (local, PDT). Raw output of `step4_tokens.py`:

```text
{"case": "d", "num_ctx_sent": 8192, "t_before": "2026-10-27T22:33:37-07:00", "t_after": "2026-10-27T22:33:48-07:00", "prompt_eval_count": 4020, "eval_count": 1024, "done_reason": "length", "content_chars": 113, "thinking_chars": 3085}
PS_AFTER
NAME          ID              SIZE      PROCESSOR    CONTEXT    RUNNER      UNTIL              
gemma4:e4b    dc35e8d9c606    538 MB    100% GPU     8192       llamacpp    4 minutes from now    

{"case": "d", "num_ctx_sent": 32768, "t_before": "2026-10-27T22:33:49-07:00", "t_after": "2026-10-27T22:33:58-07:00", "prompt_eval_count": 4020, "eval_count": 1024, "done_reason": "length", "content_chars": 0, "thinking_chars": 3069}
PS_AFTER
NAME          ID              SIZE      PROCESSOR    CONTEXT    RUNNER      UNTIL              
gemma4:e4b    dc35e8d9c606    398 MB    100% GPU     32768      llamacpp    4 minutes from now    

{"case": "c", "num_ctx_sent": 8192, "t_before": "2026-10-27T22:33:59-07:00", "t_after": "2026-10-27T22:34:11-07:00", "prompt_eval_count": 3585, "eval_count": 1024, "done_reason": "length", "content_chars": 601, "thinking_chars": 2885}
PS_AFTER
NAME          ID              SIZE      PROCESSOR    CONTEXT    RUNNER      UNTIL              
gemma4:e4b    dc35e8d9c606    538 MB    100% GPU     8192       llamacpp    4 minutes from now    

{"case": "c", "num_ctx_sent": 32768, "t_before": "2026-10-27T22:34:11-07:00", "t_after": "2026-10-27T22:34:24-07:00", "prompt_eval_count": 3585, "eval_count": 1024, "done_reason": "length", "content_chars": 612, "thinking_chars": 2718}
PS_AFTER
NAME          ID              SIZE      PROCESSOR    CONTEXT    RUNNER      UNTIL              
gemma4:e4b    dc35e8d9c606    398 MB    100% GPU     32768      llamacpp    4 minutes from now    

DONE 2026-10-27T22:34:24-07:00
```

| Order | Case | `num_ctx` sent | Window (local) | `prompt_eval_count` | `eval_count` | `done_reason` | content chars | thinking chars | `ollama ps` after: CONTEXT / PROCESSOR |
|---|---|---|---|---|---|---|---|---|---|
| 1 | d | 8192 | 22:33:37 to 22:33:48 | 4020 | 1024 | length | 113 | 3085 | 8192 / 100% GPU |
| 2 | d | 32768 | 22:33:49 to 22:33:58 | 4020 | 1024 | length | 0 | 3069 | 32768 / 100% GPU |
| 3 | c | 8192 | 22:33:59 to 22:34:11 | 3585 | 1024 | length | 601 | 2885 | 8192 / 100% GPU |
| 4 | c | 32768 | 22:34:11 to 22:34:24 | 3585 | 1024 | length | 612 | 2718 | 32768 / 100% GPU |

Case c at 8192 is the same prompt count as the 2026-10-22 baseline (3585), and it stopped at the 1024 cap, not near `n_tokens` 4095.

## Step 5: journal

Command: `journalctl -u ollama --since "2026-10-27 22:33:02" --no-pager | grep -i truncat`, which is the step 3 start from the plan. Every hit, with the request whose window contains it. The full journal window (2790 lines) is at `/tmp/claude-1000/kvv-2026-10-27/journal_window.txt`.

```text
Oct 27 22:33:14 Danny-PC ollama[881]: slot      release: id  0 | task 0 | stop processing: n_tokens = 0, truncated = 0
    window: R1 step 3 runner, num_ctx 8192
Oct 27 22:33:20 Danny-PC ollama[881]: slot      release: id  0 | task 2 | stop processing: n_tokens = 5043, truncated = 0
    window: R1 step 3 runner, num_ctx 8192
Oct 27 22:33:42 Danny-PC ollama[881]: slot      release: id  0 | task 0 | stop processing: n_tokens = 0, truncated = 0
    window: R2 case d, num_ctx 8192
Oct 27 22:33:48 Danny-PC ollama[881]: slot      release: id  0 | task 2 | stop processing: n_tokens = 5043, truncated = 0
    window: R2 case d, num_ctx 8192
Oct 27 22:33:58 Danny-PC ollama[881]: slot      release: id  0 | task 0 | stop processing: n_tokens = 5043, truncated = 0
    window: R3 case d, num_ctx 32768
Oct 27 22:34:05 Danny-PC ollama[881]: slot      release: id  0 | task 0 | stop processing: n_tokens = 0, truncated = 0
    window: R4 case c, num_ctx 8192
Oct 27 22:34:11 Danny-PC ollama[881]: slot      release: id  0 | task 2 | stop processing: n_tokens = 4608, truncated = 0
    window: R4 case c, num_ctx 8192, R5 case c, num_ctx 32768
Oct 27 22:34:24 Danny-PC ollama[881]: slot      release: id  0 | task 0 | stop processing: n_tokens = 4608, truncated = 0
    window: R5 case c, num_ctx 32768
```

Reading the hits:

- Every hit is `truncated = 0`. There is no `truncating input prompt` line, and no `truncated = 1` line, in any window.
- Each 8192 load runs a warm-up first: `task 0` with `n_tokens = 0` (its `new prompt` line shows `task.n_tokens = 0`). The 32768 loads have no warm-up; their first task is the request. The request's own lines carry its prompt size in `new prompt` (`task.n_tokens` 4020 for case d, 3585 for case c) and prompt plus output in `release`: 4020 + 1024 at 22:33:20, 22:33:48 and 22:33:58 (`n_tokens` 5043), and 3585 + 1024 at 22:34:11, 22:34:24 (`n_tokens` 4608).
- The 22:34:11 hit falls on the boundary between the case c 8192 window and the case c 32768 window. Its size (4608) identifies it as the case c 8192 request. Both windows pass, because the line reads `truncated = 0`.

The model load lines show that each request ran in a slot of the size it asked for:

```text
Oct 27 22:33:14 Danny-PC ollama[881]: srv    load_model: initializing, n_slots = 1, n_ctx_slot = 8192, kv_unified = 'false'
Oct 27 22:33:14 Danny-PC ollama[881]: slot   load_model: id  0 | task -1 | new slot, n_ctx = 8192
Oct 27 22:33:42 Danny-PC ollama[881]: srv    load_model: initializing, n_slots = 1, n_ctx_slot = 8192, kv_unified = 'false'
Oct 27 22:33:42 Danny-PC ollama[881]: slot   load_model: id  0 | task -1 | new slot, n_ctx = 8192
Oct 27 22:33:54 Danny-PC ollama[881]: srv    load_model: initializing, n_slots = 1, n_ctx_slot = 32768, kv_unified = 'false'
Oct 27 22:33:54 Danny-PC ollama[881]: slot   load_model: id  0 | task -1 | new slot, n_ctx = 32768
Oct 27 22:34:04 Danny-PC ollama[881]: srv    load_model: initializing, n_slots = 1, n_ctx_slot = 8192, kv_unified = 'false'
Oct 27 22:34:04 Danny-PC ollama[881]: slot   load_model: id  0 | task -1 | new slot, n_ctx = 8192
Oct 27 22:34:17 Danny-PC ollama[881]: srv    load_model: initializing, n_slots = 1, n_ctx_slot = 32768, kv_unified = 'false'
Oct 27 22:34:17 Danny-PC ollama[881]: slot   load_model: id  0 | task -1 | new slot, n_ctx = 32768
```

## Pass table (summary)

| # | Condition | Result |
|---|---|---|
| (i) | `num_ctx` 8192 in both captured bodies | PASS |
| (ii) | `ollama ps` CONTEXT 8192, PROCESSOR 100% GPU | PASS |
| (iii) | case d `prompt_eval_count` at 8192 equals the 32768 run (4020) | PASS |
| (iv) | no truncation line in any 8192 window | PASS |
| (v) | case c at 8192 reaches `eval_count` 1024 | PASS |

## Observations (outside the pass conditions)

1. **`finish_reason` reports `stop` for a request that hit the cap.** `core/llm/ollama_provider.py` lines 223 and 272 set `finish_reason = "stop" if data.get("done") else "length"`. Ollama's non-streaming response sets `done` to true even when `done_reason` is `length`. Step 3 returned `finish_reason` `stop` with `tokens_generated` 1024, while the raw `done_reason` for the same body is `length` (step 4, row 1). In product code, `modules/rag.py` (lines 862 and 1475) checks only for `timeout`, and no branch on `length` was found, so this has no effect today. Candidate follow-up for L0 (not added to `queue.md`): `OLLAMA-FINISH-REASON`: map `done_reason` from the Ollama response (`length` stays `length`), with a RED test that uses a `done_reason: length` body. Low priority.
2. **The answer budget goes to thinking, not to the answer.** Step 3 returned 0 characters of answer text. In step 4 at 8192, case d had 113 answer characters and 3085 thinking characters, and case c had 601 and 2885, all at `eval_count` 1024. The 32768 runs show the same pattern (`eval_count` 1024, answer 0 or 612). This matches baseline finding 1 in `kv-prefix-measure.md` ("gemma4:e4b spends the output budget on thinking"). It is not a context-size effect, and it is not a truncation. It is recorded again here and is not new.
3. **Case d prompt size differs from 2026-10-22.** The 2026-10-27 prompt is 15924 characters (4020 tokens at 8192 and 32768), against 16696 characters (4350 tokens) in the baseline. The difference is in the retrieved-context part only (step 2). The cause was not investigated. It does not change any pass result, because 8192 and 32768 agree in this run.

**Count line (not measured here).** The brief's count line (start 2545, slot 2540, +5) is not reproduced. This PR adds no test file and runs no pytest. The plan row says "no pytest, no slot change", so the expected delta is 0. The slot value 2540 matches `AGENT.md` line 77 and the queue header. The start value 2545 was not found in the repo. The count slots were not edited. L0 to reconcile the count line before the PR body is written.

## Scratch scripts

The scripts run from `/tmp/claude-1000/kvv-2026-10-27/`. They are not product code and are not committed; they are pasted here so the run can be repeated. The 2026-10-22 appendix scripts were recreated verbatim from the code between the fences at `kv-prefix-measure.md` lines 459 to 693 (`prompts.py`) and 697 to 736 (`mlib.py`), then changed only as shown in the two diffs.

Diff from the appendix, `prompts.py` (the output path now comes from the `OUT` environment variable; its default points at the scratch directory):

```diff
--- prompts.orig.py
+++ prompts.py
@@ -23,7 +23,7 @@
 from core.time import utcnow
 from core.config import settings
 
-OUT = "/tmp/claude-1000/kv-1022/prompts.json"
+OUT = os.environ.get("OUT", "/tmp/claude-1000/kvv-2026-10-27/prompts.json")
 MODEL = "gemma4:e4b"
 PID = str(uuid.uuid4())
 
```

Diff from the appendix, `mlib.py` (the prompt file path only):

```diff
--- mlib.orig.py
+++ mlib.py
@@ -1,7 +1,7 @@
 import json, subprocess, time, copy, urllib.request
 BASE = "http://127.0.0.1:11434"
 MODEL = "gemma4:e4b"
-P = json.load(open("/tmp/claude-1000/kv-1022/prompts.json"))
+P = json.load(open("/tmp/claude-1000/kvv-2026-10-27/prompts.json"))
 
 def post(path, body, timeout=600):
     req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
```

The appendix's step 3 (which posted captured bodies to `/api/chat` directly) was not used: `step3_runner.py` below replaces it and goes through the app's runner. The appendix's step 4 is replaced by `step4_tokens.py`. The appendix's step 4 (cold and warm runs), step 5 and step 6 were not run in this PR and are not included.

`quiet_check.sh` (new; step 0 check before each step):

```bash
#!/usr/bin/env bash
# KV-NUMCTX-VERIFY step 0: isolation check before each step. Exit 1 when busy.
busy=0
if [ -e /tmp/claude-1000/quiet-box.lock ]; then echo "BUSY: quiet-box.lock present"; busy=1; fi
if pgrep -f "[p]laywright|[v]itest" >/dev/null; then echo "BUSY: UI test process"; pgrep -af "[p]laywright|[v]itest" | cut -c1-160; busy=1; fi
if pgrep -f "[q]wen3|[j]udge[-_]laya|[j]udge[-_]nli|[m]m-2|[a]udit[-_]db" >/dev/null; then echo "BUSY: other model-host row"; pgrep -af "[q]wen3|[j]udge[-_]laya|[j]udge[-_]nli|[m]m-2|[a]udit[-_]db" | cut -c1-160; busy=1; fi
if pgrep -f "[h]c-pytest|[p]yslot|[p]ytest" >/dev/null; then echo "BUSY: pytest or pyslot"; pgrep -af "[h]c-pytest|[p]yslot|[p]ytest" | cut -c1-160; busy=1; fi
load1=$(awk '{print $1}' /proc/loadavg)
if awk -v l="$load1" 'BEGIN{exit !(l>3.0)}'; then echo "BUSY: load1=$load1"; busy=1; fi
used=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits | head -1)
echo "load1=$load1 gpu_mib_used=$used ollama_ps_lines=$(ollama ps | tail -n +2 | wc -l) at=$(date -Is)"
exit $busy
```

`step3_runner.py` (new):

```python
"""KV-NUMCTX-VERIFY step 3: case d through the app's runner (get_model_runner -> OllamaProvider).

Scratch measurement script (not product code). Run from src/backend under hold_slots.sh.
The unload() call uses keep_alive 0 for measurement only (OQ-KV-LOCK (a)); product code is not changed.
"""
import asyncio
import datetime
import json
import os
import sys

os.environ["LLM_PROVIDER"] = "ollama"
os.environ["LLM_MODEL"] = "gemma4:e4b"
sys.path.insert(0, "/tmp/claude-1000/kvv-2026-10-27")
from mlib import P, ps, unload  # noqa: E402

from core.llm.ollama_provider import OllamaProvider  # noqa: E402
from core.model_runner import InferenceConfig, get_model_runner  # noqa: E402

OUT = "/tmp/claude-1000/kvv-2026-10-27/step3_runner.json"


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


# Record the body the runner actually sends, to compare with the captured case d body.
captured = []
_orig_build = OllamaProvider._build_request_body


def _recording_build(self, messages, config):
    body = _orig_build(self, messages, config)
    captured.append(body)
    return body


OllamaProvider._build_request_body = _recording_build

case = P["cases"]["d"]
cbody = case["body"]
o = cbody["options"]
config_d = InferenceConfig(
    max_tokens=o["num_predict"],
    temperature=o["temperature"],
    top_p=o["top_p"],
    stop_sequences=o["stop"] or None,
    timeout_seconds=300,
    response_schema=cbody.get("format"),
    think=cbody.get("think"),
)
prompt_d = case["prompt"]


async def main():
    assert unload(), "model did not unload before step 3"
    start = now()
    print("STEP3_START", start, flush=True)
    runner = get_model_runner()
    provider = runner._get_provider()
    print("PROVIDER", type(provider).__name__, "model", provider._model, flush=True)
    t0 = now()
    result = await runner.generate_async(prompt_d, config_d)
    t1 = now()
    ps_after = ps()
    sent = captured[-1] if captured else None
    out = {
        "step3_start": start,
        "t0": t0,
        "t1": t1,
        "provider_class": type(provider).__name__,
        "provider_is_ollama": isinstance(provider, OllamaProvider),
        "finish_reason": result.finish_reason,
        "tokens_generated": result.tokens_generated,
        "model_name": result.model_name,
        "text_chars": len(result.text),
        "text": result.text,
        "sent_num_ctx": sent["options"].get("num_ctx") if sent else None,
        "sent_body_equals_captured_d": sent == cbody if sent else None,
        "ps_after": ps_after,
    }
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)
    print("RESULT", json.dumps({k: v for k, v in out.items() if k not in ("text", "ps_after")}, indent=1), flush=True)
    print("PS_AFTER\n" + ps_after, flush=True)
    print("ANSWER_BEGIN\n" + result.text + "\nANSWER_END", flush=True)


asyncio.run(main())
```

`step4_tokens.py` (new):

```python
"""KV-NUMCTX-VERIFY step 4: token counts for cases d and c, raw POSTs to /api/chat.

Each request: model unloaded first (keep_alive 0, measurement only), then the captured body.
Order per case: num_ctx 8192 (captured body unchanged), then the same body with options.num_ctx 32768.
Scratch measurement script (not product code). Run under hold_slots.sh.
"""
import copy
import datetime
import json
import sys

sys.path.insert(0, "/tmp/claude-1000/kvv-2026-10-27")
from mlib import P, post, ps, unload  # noqa: E402

OUT = "/tmp/claude-1000/kvv-2026-10-27/step4_tokens.json"


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


rows = []
for case in ("d", "c"):
    for nc in (8192, 32768):
        body = copy.deepcopy(P["cases"][case]["body"])
        if nc != 8192:
            body["options"]["num_ctx"] = nc
        assert unload(), f"model did not unload before case {case} num_ctx {nc}"
        ps_before = ps()
        sent_num_ctx = body["options"]["num_ctx"]
        t_before = now()
        resp = post("/api/chat", body, timeout=600)
        t_after = now()
        ps_after = ps()
        msg = resp.get("message", {})
        row = {
            "case": case,
            "num_ctx_sent": sent_num_ctx,
            "t_before": t_before,
            "t_after": t_after,
            "prompt_eval_count": resp.get("prompt_eval_count"),
            "eval_count": resp.get("eval_count"),
            "done": resp.get("done"),
            "done_reason": resp.get("done_reason"),
            "load_duration_ms": None if resp.get("load_duration") is None else round(resp["load_duration"] / 1e6),
            "prompt_eval_duration_ms": None if resp.get("prompt_eval_duration") is None else round(resp["prompt_eval_duration"] / 1e6),
            "eval_duration_ms": None if resp.get("eval_duration") is None else round(resp["eval_duration"] / 1e6),
            "content_chars": len(msg.get("content", "")),
            "thinking_chars": len(msg.get("thinking", "") or ""),
            "ps_before": ps_before,
            "ps_after": ps_after,
        }
        rows.append(row)
        print(json.dumps({k: row[k] for k in ("case", "num_ctx_sent", "t_before", "t_after", "prompt_eval_count",
                                               "eval_count", "done_reason", "content_chars", "thinking_chars")}), flush=True)
        print("PS_AFTER", ps_after, sep="\n", flush=True)
        with open(OUT, "w") as fh:
            json.dump(rows, fh, indent=1)
assert unload(), "final unload failed"
print("DONE", now(), flush=True)
```

## Privacy

The captured prompts are synthetic fixtures. `prompts.py` seeds an in-memory profile with a synthetic patient ("Test Person"), synthetic lab values, and synthetic dates (2026-02-11 and 2026-07-10 in case d). Before pasting, the captured prompts were checked for names and identifiers (the patient-name field holds `Test Person` only; no `@`, MRN, DOB or SSN pattern was found). The prompt text itself is not pasted, only character and token counts. The `keep_alive: 0` unload is a measurement call in the scratch scripts only. No `keep_alive` was added to product code (OQ-KV-LOCK (a)).
