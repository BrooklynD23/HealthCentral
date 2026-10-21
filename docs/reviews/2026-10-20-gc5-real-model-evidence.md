# G-C5 Task 7: real-model evidence (laptop, CPU)

**Last Updated:** 2026-10-20
**Owner:** repository owner
**Status:** Measured evidence only. No flag, code or default changed; `use_llm_entailment` stays off.
**Refresh Trigger:** the model pin changes, the verifier hunk (`verifier_agent.py:304-317`) changes, or the Ollama/GPU model-host run is done.

Plan: [GC5 plan, Task 7](../plans/2026-10-18-GC5-hc-m11-nli-flag-off.md#task-7--owner-host-evidence-not-part-of-the-pr). Authorised by the owner's session goal ("if huggingface.co is reachable, run the G-C5 real-model steps").

## Verdict

With the flag on and the real model present, **both legacy "answer" golden cases are abstained** (`answer_rate` 0.000, bar 1.000). The legacy RAG eval gate **fails** flag-on. Cause: the NLI model labels a correct restatement ("Your glucose was 95 mg/dL") as `neutral` (0.858) against the source ("Glucose: 95 mg/dL (reference range ...)"), and `neutral` never reaches the 0.7 ENTAILMENT floor. Keep the flag off. The event loop is blocked 9.4 s on the first answer and 47 ms to 2.2 s per answer after.

## Setup

| Item | Value |
|---|---|
| Host | WSL2, 6 vCPU, 22 GiB, CPU only (no GPU, no Ollama) |
| Stack | torch 2.14.0+cu130 (CPU used), sentence-transformers 6.1.0, transformers 5.17.0, `~/venvs/asclexis-311` |
| Tree | worktree from `origin/main` 699eb18 (flag code present), branch `docs/gc5-real-model-evidence-2026-10-20` |
| Isolation | all three `/tmp/claude-1000/hc-pytest.{1,2,3}.lock` held with nested `flock` for every model run; no other pytest ran in this worktree |
| Network | only `download_models.py nli`; every later run `HF_HUB_OFFLINE=1` plus `socket.connect/connect_ex/bind/sendto/create_connection/getaddrinfo` patched to raise. Socket attempts counted: **0** in every run |
| Flag | flag on only by `settings.use_llm_entailment = True` and `api.assistant._rag_module = None` inside the measuring process |
| Scratch | scripts lived in the session scratchpad (outside the repo) and are deleted. Raw output is summarised below, not committed |

## Results

| # | Measurement | Status | Value |
|---|---|---|---|
| 1 | Real fetch | MEASURED | 8 files, 294,485,613 bytes on disk (`du -sb`; the plan predicted 294,480,009 from API sizes, the 5,604 difference is directory entry overhead). `model.safetensors` 283,353,172 bytes. Fetch took 33.1 s. **sha256 matched: yes** (`4e4fc497...d9e9`, identical to the manifest pin; `cmd_nli` installs nothing on a mismatch and printed "NLI model installed"; re-verified with `sha256sum`) |
| 2 | Offline load, sockets blocked | MEASURED | `id2label = {0: 'contradiction', 1: 'entailment', 2: 'neutral'}` (matches the labels `EntailmentLabel` accepts). Tokenizer `DebertaV2Tokenizer`, `is_fast=True`. **`sentencepiece` is not installed in the venv and is not needed** (`sentencepiece` absent from `sys.modules` after load). No `requirements.txt` change. 0 socket attempts |
| 3a | First-call latency | MEASURED | 8.39 s total = sha256 1.99 s + load 6.40 s (cold process, warm page cache for the sha). A second cold run through `_check_entailment_llm` measured 9.33 s including the first `predict` |
| 3b | `predict` latency | MEASURED | 138 distinct claim/source pairs, 414 calls (3 passes) through `VerifierAgent._check_entailment_llm`: **median 39.7 ms, p95 136.9 ms**, mean 53.2 ms, max 850 ms. One pair per call. Labels across the 138 pairs: 70 neutral, 35 entailment, 33 contradiction |
| 3c | Peak RSS | MEASURED | 92.9 MB before load, 1,001 MB after load, **1,098.5 MB peak** after 414 predicts (`ru_maxrss`); 1,119.5 MB peak in the gate run (which also loads MiniLM) |
| 4 | Legacy RAG eval gate, flag on | MEASURED (no Ollama needed) | The gate fakes retrieval and generation (`tests/legacy_eval/harness.py`), so it ran fully. Flag off: PASS, all bars met, 0.35 s, 0 NLI calls. **Flag on: FAIL, `answer_rate=0.000`**, 7 NLI calls, 10.4 s. Details below |
| 5 | Low-confidence CONTRADICTION failing a rules-verified claim | MEASURED | **0 of 33** rules-verified pairs. 6 of 33 were failed by NLI, all as `neutral` or sub-0.7 `entailment`, none `contradiction`. 3 contradictions below 0.7 exist (0.487, 0.551, 0.571), all on claims the rules had already failed ("Your HbA1c result is normal."). Reverse: NLI verified 7 pairs the rules failed |
| 6 | Route behaviour through HTTP | MEASURED | See table below |
| 7 | Event-loop blocking, flag on | MEASURED | First answer: **9,401 to 9,839 ms** stall (sha + load + predict, two runs). Later answers: 0 to 3 ms when no claim reaches the verifier, otherwise 47 to 2,153 ms (the stall equals the whole `query()`). Flag off: max 2 ms. Warm numbers are noisy: the host was shared with other jobs |
| - | Ollama/GPU generation quality, real LLM output claims | UNMEASURED-needs-model-host | The gate's `model_output` is fixed text. No real LLM text was produced; no GPU or Ollama on this laptop |
| - | Long source chunk truncation (plan risk 8) | UNMEASURED | Model `max_length` is 512 tokens; fixture sources are one to two sentences, so truncation was not exercised |

Pair sources for 3b and 5: claims split from the 8 legacy golden `model_output` texts crossed with the glucose chunk set (the app's `CHUNK_SETS`), plus 4 claims (true value, wrong value, "is high", "is normal") per observation in the 18 `tests/agent/golden/grounded-*.json` vaults (28 observations, 112 pairs; the other 26 pairs are legacy). Those last three are synthetic perturbations built for this measurement, not shipped fixtures.

### 4. Where answers change, flag on vs off (legacy gate, per case)

| Case | Off | On | Claims off (verified, failed, total) | Claims on |
|---|---|---|---|---|
| abstain-generation-timeout | abstain | abstain | 0, 2, 2 | 0, 2, 2 |
| abstain-hallucinated-value | abstain | abstain | 0, 1, 1 | 0, 1, 1 (reason text now "1 source(s) contradict this claim"; NLI contradiction 0.998 on "182 mg/dL"; faithfulness 0.10 to 0.00) |
| abstain-invalid-citation-id | abstain | abstain | 0, 1, 1 | 0, 1, 1 |
| abstain-uncited-report-facts | abstain | abstain | 0, 2, 2 | 0, 2, 2 |
| abstain-unverifiable-claim | abstain | abstain | 1, 1, 2 | 0, 2, 2 (a claim the rules verified now fails) |
| **answer-glucose-cited-latest** | served, valid | **abstained**, invalid | 1, 0, 1 | 0, 1, 1 |
| **answer-glucose-cited-with-reference** | served, valid | **abstained**, invalid | 2, 0, 2 | 0, 2, 2 |
| escalate-prohibited-advice | escalate | escalate | 1, 1, 2 | 0, 2, 2 |

NLI calls flag on (claim / source / label / confidence): "Your glucose was 182 mg/dL" contradiction 0.998; "...95 mg/dL, within the reference range of 70-100 mg/dL" entailment 0.668 (under the 0.7 floor); "Glucose is the primary source of energy..." neutral 0.997; "Glucose: 95 mg/dL (reference range 70-100 mg/dL)" neutral 0.996; "Your glucose was 95 mg/dL" neutral 0.858; "Normal fasting glucose is typically 70-100 mg/dL" neutral 0.963. Safety direction held (no invalid answer served; `served_invalid=0`, `uncited_served=0`, `leaked=0`); usefulness did not (every grounded answer abstained).

### 6. Routes through HTTP (`route_client`; retrieval and generation faked, real `validate_response` and real model)

Answer used: `REPORT FACTS: Your glucose was 95 mg/dL [cite:1]. GENERAL INFO: Normal fasting glucose is typically 70-100 mg/dL [cite:2].` (2 claims).

| Scenario (flag on unless noted) | `POST /assistant/chat` | `POST /interpretations/observations/{id}/interpret-grounded` | NLI warning lines per answer |
|---|---|---|---|
| Flag off (baseline) | 200, answer served | 201, `is_valid=true`, 2 of 2 claims verified | 0 / 0 |
| Model present | 200, **abstention** template | 201, **`is_valid=false`, 0 of 2 verified, 2 failed, answer text still served** | 0 / 0 |
| Model absent | 200, abstention template | 201, `is_valid=false`, 0 verified, 2 failed, answer text still served | **2 / 2** (one per claim x source; message is path-free) |
| `predict` raises `RuntimeError` | **500** `{"detail":"Error processing chat request"}` | **503** "The explanation could not be generated right now. Please try again." | 0 / 0 |
| `predict` returns an index with no label (unexpected label) | **500** generic detail | **500** `Internal Server Error` (unhandled, not the 503 path) | 0 / 0 |

Confirms plan rows 10 and 11: a `predict` failure is loud on both routes and the unexpected-label `ValueError` is unhandled on `interpret-grounded`; with the model absent `interpret-grounded` serves the answer with every claim failed (option B). Faithfulness score stayed 0.814 on that route while 0 of 2 claims verified, so a client reading only `faithfulness_score` would not see the failure.

## Surprises

1. **Flag-on abstains all grounded answers** with the real model (item 4). The 0.7 ENTAILMENT floor plus NLI scoring paraphrase as `neutral` makes the flag unusable as is; this is a quality finding, not a safety one.
2. **No CONTRADICTION over-fail** (item 5): 0 of 33 rules-verified pairs. The feared asymmetry did not occur on these fixtures. Small sample, synthetic perturbations; do not generalise.
3. **Licence** matches the plan: `apache-2.0` in the downloaded README; `feature_list.json:142` ("MIT") remains wrong. Base-model licence still not reviewed.
4. **`sentencepiece` not needed** (fast tokenizer from `tokenizer.json`), as the plan hoped.
5. **Peak RSS about 1.1 GB** for a 283 MB, 71 M-parameter model (F32 weights plus torch runtime), above the ~2 GB-per-slot budget's comfort for sharing a slot with pytest.
6. **First answer after start blocks the loop about 9.4 s**; the plan's accepted cost, now quantified.

## What this evidence would fail to notice

- Fixtures are fake generation: real LLM phrasing may be closer to or further from the source than the fixed text here.
- 138 pairs, 8 golden cases, one glucose chunk set: no medical-domain breadth. Latency was measured on 6 shared CPU cores; the model host differs.
- Route tests stub retrieval and generation; the real DB-backed retrieval path was not run.
- Warm stall figures varied 47 ms to 2.2 s between runs on a loaded box.

## Not done

Flag default unchanged. No code, test, manifest or requirements edit. Ollama/GPU: UNMEASURED-needs-model-host.
