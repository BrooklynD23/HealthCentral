# G-C5 Task 7: model-host evidence, real LLM output (RTX 3080 via Ollama, NLI on CPU)

**Last Updated:** 2026-10-21
**Owner:** repository owner
**Status:** Measured evidence only. No flag, code or default changed; `use_llm_entailment` stays off (turned on only inside the measuring processes).
**Refresh Trigger:** the model pin changes, the verifier hunk (`verifier_agent.py:304-317`) changes, the legacy RAG prompt or cite schema changes, or the Ollama model set changes.

Plan: [GC5 plan, Task 7](../../plans/2026-10-18-GC5-hc-m11-nli-flag-off.md#task-7--owner-host-evidence-not-part-of-the-pr). Follows the laptop run, [2026-10-20 report](../2026-10-20/gc5-real-model-evidence.md), which listed "real LLM output" and "long source chunk truncation" as unmeasured. Run by an agent on the owner's model host (WSL2, RTX 3080, Ollama 0.40.5). The owner has not yet confirmed this run.

Scripts: [`gc5-host-evidence/real_llm.py`](gc5-host-evidence/real_llm.py) (new) plus the unchanged [`../2026-10-20/gc5-evidence/`](../2026-10-20/gc5-evidence/) scripts. Per-case raw results (model text, per-claim NLI calls, validation errors): [`real_llm_llama3.1_8b.json`](gc5-host-evidence/real_llm_llama3.1_8b.json), [`real_llm_qwen3_8b.json`](gc5-host-evidence/real_llm_qwen3_8b.json), [`trunc.json`](gc5-host-evidence/trunc.json). All fixture text is synthetic; none holds patient data.

## Verdict

With real LLM answers from the app's own legacy RAG prompt, **flag off already withheld most answers; flag on changed the outcome for one served answer and never turned an abstention into a served answer.** Over 26 cases per model (8 legacy golden questions plus all 18 grounded vault questions from `tests/agent/golden/grounded-*.json`): `llama3.1:8b` served 0 flag off and 0 flag on, abstained on all 26 both ways; `qwen3:8b` served 8 flag off and 7 flag on, and the one change is `grounded-sodium-latest`, where the correct claim "Your latest sodium level was 140 mmol/L, collected on 2025-09-01" scored `entailment` 0.619, under the 0.7 floor, and went from served to abstained. NLI changed the verified-claim count in 10 cases (llama 6 up and 1 down, qwen 2 up and 1 down), but no abstention became a served answer; the `faithfulness_score` is identical flag off and on in all 52 case-runs. Two findings are independent of the flag: llama3.1:8b answers fail claim verification flag off even when the sentence is a correct restatement (claims reported as "Cannot verify claim without source evidence"), and qwen3:8b hit the 1024-token generation cap in 6 of 26 cases; in 2 of those the model text was empty and `validate_response` returned `is_valid` true with 0 claims (served flag off and on). Source chunks over 512 tokens: the same supporting fact scored `entailment` 0.981 placed first and 0.960 placed last, so truncation did not change the label in this test. The laptop figures reproduced on this host (gate labels and confidences identical; latency lower and tighter). Keep the flag off; this report does not support turning it on.

## Setup

| Item | Value |
|---|---|
| Host | WSL2, 24 vCPU, 37 GiB, RTX 3080 (10 GiB, about 2.4 GiB in use by other processes before the run), Ollama 0.40.5 at 127.0.0.1:11434 |
| Models | `llama3.1:8b` and `qwen3:8b` for the real-LLM run (`gemma4:e4b`, `gemma3:12b` are installed and were not run) |
| Stack | `~/venvs/asclexis-311`: torch 2.14.1+cpu (**CPU build; `torch.cuda.is_available()` is False**), sentence-transformers 6.1.0, transformers 5.20.1. The NLI cross-encoder therefore ran on the CPU; the GPU was used only by Ollama. No CUDA torch was installed (not changed, by instruction). The laptop run's torch was 2.14.0+cu130 (CPU used) and transformers 5.17.0 |
| Tree | worktree from `origin/main` b902e0f (flag code present), branch `docs/gc5-model-host-evidence-2026-10-21`. Embedding bundle copied from `~/asclexis-models/embeddings` |
| Isolation | all three pyslot locks (`hc-pytest.{1,2,3}.lock`, nested blocking `flock`) held for the NLI fetch (33 s) and for the whole measurement session (600 s, no queue wait); no pytest ran |
| Network | one sanctioned fetch: `python scripts/download_models.py nli` (Q5b), then copied to `~/asclexis-models/nli/`. Every measurement after it: `HF_HUB_OFFLINE=1`. `measure.py`/`routes_probe.py` patch `connect`, `connect_ex`, `bind`, `sendto`, `create_connection`, `getaddrinfo` to raise (0 attempts). `real_llm.py` replaces `socket.connect` and `connect_ex` so that only 127.0.0.1 and ::1 on port 11434 connect (anything else is counted and refused), and `socket.getaddrinfo` so that only `127.0.0.1`, `localhost` and `::1` resolve (any other host is counted and refused); it does **not** patch `sendto`, `bind` or `create_connection`: **0 other attempts in `gen` (both models) and `trunc`**; 27 connects to Ollama per `gen` run (1 availability probe plus 26 generations) |
| Flag | on only via `settings.use_llm_entailment = True` and `api.assistant._rag_module = None` inside the measuring process |
| Generation path | `RAGModule.compose_prompt` (the app's `SYSTEM_PROMPT` and `[YOUR_RESULTS:N]`/`[REFERENCE:N]` context) then `RAGModule._generate_with_runner` (the app's cite schema for constrained decoding, `max_tokens` 1024, `top_p` 0.9) through the `ModelRunner` facade and the Ollama provider, `LLM_PROVIDER=ollama`, `LLM_MODEL=<tag>`. Then the real `RAGModule.validate_response` on the same text, flag off then flag on |
| Deviations from the app | (1) temperature forced to 0.0 by a wrapper (the app sends 0.1); the Ollama provider has no seed parameter, so **no seed was set** and repeatability was not tested; (2) retrieval is faked: legacy cases use the `glucose` chunk set from `tests/legacy_eval/harness.py`, vault cases use one observation-summary chunk rebuilt from the vault in the text format of `RAGModule._get_observation_chunks` (no DB, analyte name used as the display name, no reference range or flag lines because the vaults have none); (3) "served" means `is_valid` true and no `prohibited_advice` (the `_legacy_serve_or_abstain` rule), computed on `validate_response`; the HTTP route was not driven with a real LLM |

## Results

| # | Measurement | Status | Value |
|---|---|---|---|
| 1 | NLI fetch, sha256, size | MEASURED | `download_models.py nli` printed "NLI model installed", exit 0, 33.0 s wall. Directory 294,485,611 bytes (laptop: 294,485,613; 2-byte difference not investigated), sha256 `4e4fc497...d9e9` equals the manifest pin, licence line `apache-2.0` |
| 2 | Offline load | MEASURED | id2label `{0: contradiction, 1: entailment, 2: neutral}`, `DebertaV2Tokenizer` fast, `sentencepiece` not needed, 0 socket attempts. First call 9.62 s (sha256 2.13 s + load 7.49 s); laptop 7.73 s |
| 3 | `predict` latency, 414 calls | MEASURED | median 76.1 ms, p95 142.7, max 217.4, mean 84.7. First `predict` 14.07 s cold. Peak RSS 748 MB. Laptop: median 60.5, p95 489.4, max 1,744 |
| 4 | Legacy gate, golden fixtures, flag on | MEASURED | Flag off PASS (13.9 s, 0 NLI calls). **Flag on FAIL `answer_rate=0.000`**, 7 NLI calls, 20.7 s; both `answer-*` cases abstained. The 7 (claim, label, confidence) tuples are identical to the laptop's, including `neutral` 0.858 and `entailment` 0.668. Per-case claim counts identical to the laptop |
| 5 | Low-confidence CONTRADICTION failing a rules-verified claim (138 pairs) | MEASURED | 0 of 33 rules-verified pairs; 6 failed by NLI, none as contradiction; 3 sub-0.7 contradictions (0.487, 0.551, 0.571), all on claims the rules already failed; 7 NLI rescues. Identical to the laptop |
| 6 | Routes over HTTP (stubbed generation) | MEASURED | Identical to the laptop table: flag on, model present: chat abstention, interpret-grounded 201 `is_valid` false; `predict` raises: 500 / 503; unmapped label: 500 / 500; model absent: 2 warning lines per answer |
| 7 | Event-loop blocking, flag on | MEASURED | Cold first answer 14,102 ms (laptop 8,343). Warm: 1 to 3 ms with no claim reaching the verifier, else 76 to 229 ms (laptop 41 to 1,030). Flag off 2 to 3 ms |
| 8 | **Real LLM answers, flag off vs on** | MEASURED | Tables below. 26 cases x 2 models. `llama3.1:8b` served 0/0, `qwen3:8b` served 8/7 |
| 9 | **Long source chunk truncation (plan risk 8)** | MEASURED | Table below |
| - | Real LLM through the HTTP route (`POST /assistant/chat` with a real runner) | UNMEASURED | `real_llm.py` calls `validate_response` directly; the route's `_legacy_serve_or_abstain` mapping was reproduced, not exercised |
| - | Seed-fixed repeatability, `gemma4:e4b`, `gemma3:12b`, GPU-built torch for the NLI model | UNMEASURED | no seed parameter in the provider; the two other models were not run; CUDA torch was not installed by instruction |

### 8. Real LLM answers, flag off vs on

Cells are `status verified/failed/total claims f=faithfulness_score`. The NLI column lists every NLI call made flag on, in order (label, softmax confidence); only claims that reach the NLI branch appear there. Generation time is wall seconds on the 3080.

Aggregates:

| Model | Served off | Served on | Abstain off | Abstain on | Escalate | Tokens at cap (1024) | Empty model text | Gen time, median / total |
|---|---|---|---|---|---|---|---|---|
| llama3.1:8b | 0 | 0 | 26 | 26 | 0 / 0 | 0 | 0 | 1.835 s / 55.2 s |
| qwen3:8b | 8 | 7 | 18 | 19 | 0 / 0 | 6 | 2 | 9.775 s / 293.6 s |


### llama3.1:8b

| Case | gen s | Flag off | Flag on | NLI calls, flag on (label conf) |
|---|---|---|---|---|
| legacy:abstain-generation-timeout | 6.42 | abstain 2/3/5 f=0.775 | abstain 2/3/5 f=0.775 | entailment 0.91; neutral 0.981; neutral 0.999; entailment 0.896 |
| legacy:abstain-hallucinated-value | 1.78 | abstain 2/3/5 f=0.775 | abstain 2/3/5 f=0.775 | entailment 0.91; neutral 0.981; neutral 0.999; entailment 0.896 |
| legacy:abstain-invalid-citation-id | 1.77 | abstain 2/3/5 f=0.775 | abstain 2/3/5 f=0.775 | entailment 0.91; neutral 0.981; neutral 0.999; entailment 0.896 |
| legacy:abstain-uncited-report-facts | 1.91 | abstain 2/3/5 f=0.775 | abstain 2/3/5 f=0.775 | entailment 0.91; neutral 0.981; neutral 0.999; entailment 0.896 |
| legacy:abstain-unverifiable-claim | 1.77 | abstain 2/3/5 f=0.775 | abstain 2/3/5 f=0.775 | entailment 0.91; neutral 0.981; neutral 0.999; entailment 0.896 |
| legacy:answer-glucose-cited-latest | 1.83 | abstain 2/3/5 f=0.763 | abstain 2/3/5 f=0.763 | entailment 0.811; neutral 0.981; neutral 0.999; entailment 0.896 |
| legacy:answer-glucose-cited-with-reference | 2.05 | abstain 2/4/6 f=0.723 | abstain 2/4/6 f=0.723 | entailment 0.993; neutral 0.612; neutral 0.981; neutral 0.999; entailment 0.896 |
| legacy:escalate-prohibited-advice | 1.8 | abstain 2/2/4 f=0.822 | abstain 2/2/4 f=0.822 | entailment 0.993; entailment 0.896 |
| vault:grounded-a1c-latest | 1.61 | abstain 0/3/3 f=0.287 | abstain 0/3/3 f=0.287 | neutral 0.975 |
| vault:grounded-a1c-trend | 2.32 | abstain 1/4/5 f=0.349 | abstain 2/3/5 f=0.349 | entailment 0.937; entailment 0.99; neutral 0.997 |
| vault:grounded-creatinine-trend | 2.39 | abstain 0/4/4 f=0.36 | abstain 1/3/4 f=0.36 | entailment 0.95; neutral 0.996 |
| vault:grounded-glucose-trend | 2.18 | abstain 0/4/4 f=0.231 | abstain 1/3/4 f=0.231 | entailment 0.967; neutral 0.998 |
| vault:grounded-hdl-latest | 1.68 | abstain 0/3/3 f=0.221 | abstain 0/3/3 f=0.221 | neutral 0.987 |
| vault:grounded-hdl-trend | 2.31 | abstain 1/3/4 f=0.35 | abstain 1/3/4 f=0.35 | entailment 0.992; neutral 0.998 |
| vault:grounded-hemoglobin-latest | 1.78 | abstain 0/3/3 f=0.275 | abstain 0/3/3 f=0.275 | neutral 0.99 |
| vault:grounded-hemoglobin-trend | 2.81 | abstain 1/4/5 f=0.315 | abstain 1/4/5 f=0.315 | entailment 0.99; neutral 0.973; neutral 0.994 |
| vault:grounded-ldl-trend | 2.68 | abstain 0/4/4 f=0.345 | abstain 1/3/4 f=0.345 | entailment 0.964; neutral 0.996 |
| vault:grounded-potassium-latest | 1.61 | abstain 0/3/3 f=0.238 | abstain 0/3/3 f=0.238 | neutral 0.993 |
| vault:grounded-potassium-trend | 1.76 | abstain 0/3/3 f=0.22 | abstain 0/3/3 f=0.22 | contradiction 0.577 |
| vault:grounded-sodium-latest | 1.46 | abstain 0/3/3 f=0.391 | abstain 0/3/3 f=0.391 | neutral 0.998 |
| vault:grounded-sodium-trend | 2.29 | abstain 0/5/5 f=0.266 | abstain 2/3/5 f=0.266 | entailment 0.977; entailment 0.953; neutral 0.997 |
| vault:grounded-triglycerides-latest | 1.61 | abstain 1/2/3 f=0.405 | abstain 0/3/3 f=0.405 | neutral 0.998 |
| vault:grounded-tsh-latest | 1.84 | abstain 0/3/3 f=0.25 | abstain 0/3/3 f=0.25 | neutral 0.997 |
| vault:grounded-tsh-trend | 2.01 | abstain 0/3/3 f=0.232 | abstain 0/3/3 f=0.232 | neutral 0.998 |
| vault:grounded-vitamin-d-latest | 1.62 | abstain 0/3/3 f=0.201 | abstain 0/3/3 f=0.201 | neutral 0.993 |
| vault:grounded-vitamin-d-trend | 1.95 | abstain 0/4/4 f=0.337 | abstain 1/3/4 f=0.337 | entailment 0.991; neutral 0.998 |

### qwen3:8b

| Case | gen s | Flag off | Flag on | NLI calls, flag on (label conf) |
|---|---|---|---|---|
| legacy:abstain-generation-timeout | 22.91 | abstain 2/3/5 f=0.603 | abstain 2/3/5 f=0.603 | entailment 0.993; neutral 0.981; neutral 0.999; entailment 0.978 |
| legacy:abstain-hallucinated-value | 12.23 | abstain 0/2/2 f=0.0 | abstain 0/2/2 f=0.0 | - |
| legacy:abstain-invalid-citation-id | 12.51 | abstain 0/2/2 f=0.0 | abstain 0/2/2 f=0.0 | - |
| legacy:abstain-uncited-report-facts | 12.32 | abstain 0/2/2 f=0.0 | abstain 0/2/2 f=0.0 | - |
| legacy:abstain-unverifiable-claim | 12.16 | abstain 0/2/2 f=0.0 | abstain 0/2/2 f=0.0 | - |
| legacy:answer-glucose-cited-latest | 12.22 | served 0/0/0 f=1.0 | served 0/0/0 f=1.0 | - |
| legacy:answer-glucose-cited-with-reference | 5.53 | abstain 1/2/3 f=0.712 | abstain 1/2/3 f=0.712 | entailment 0.993 |
| legacy:escalate-prohibited-advice | 25.65 | abstain 0/3/3 f=0.71 | abstain 0/3/3 f=0.71 | - |
| vault:grounded-a1c-latest | 17.5 | abstain 1/0/1 f=0.562 | abstain 1/0/1 f=0.562 | entailment 0.982 |
| vault:grounded-a1c-trend | 14.46 | abstain 1/3/4 f=0.5 | abstain 1/3/4 f=0.5 | entailment 0.992; neutral 0.853 |
| vault:grounded-creatinine-trend | 6.52 | abstain 1/1/2 f=0.422 | abstain 1/1/2 f=0.422 | entailment 0.978; neutral 0.952; neutral 0.952 |
| vault:grounded-glucose-trend | 8.58 | abstain 1/1/2 f=0.495 | abstain 1/1/2 f=0.495 | entailment 0.994; entailment 0.994; neutral 0.974 |
| vault:grounded-hdl-latest | 7.44 | served 1/0/1 f=0.716 | served 1/0/1 f=0.716 | entailment 0.953 |
| vault:grounded-hdl-trend | 9.5 | abstain 1/1/2 f=0.321 | abstain 1/1/2 f=0.321 | entailment 0.994; entailment 0.994; neutral 0.997; neutral 0.997 |
| vault:grounded-hemoglobin-latest | 13.98 | abstain 0/2/2 f=0.045 | abstain 0/2/2 f=0.045 | - |
| vault:grounded-hemoglobin-trend | 8.25 | served 1/0/1 f=0.682 | served 1/0/1 f=0.682 | entailment 0.993; entailment 0.993 |
| vault:grounded-ldl-trend | 6.0 | abstain 1/0/1 f=0.57 | abstain 1/0/1 f=0.57 | entailment 0.99; entailment 0.99 |
| vault:grounded-potassium-latest | 7.42 | served 1/0/1 f=0.775 | served 1/0/1 f=0.775 | entailment 0.973 |
| vault:grounded-potassium-trend | 10.13 | served 1/0/1 f=0.637 | served 1/0/1 f=0.637 | entailment 0.993; entailment 0.993 |
| vault:grounded-sodium-latest | 8.98 | served 1/0/1 f=0.782 | abstain 0/1/1 f=0.782 | entailment 0.619 |
| vault:grounded-sodium-trend | 16.63 | served 0/0/0 f=1.0 | served 0/0/0 f=1.0 | - |
| vault:grounded-triglycerides-latest | 7.1 | abstain 1/3/4 f=0.485 | abstain 1/3/4 f=0.485 | entailment 0.971; neutral 0.971 |
| vault:grounded-tsh-latest | 7.68 | served 1/0/1 f=0.815 | served 1/0/1 f=0.815 | entailment 0.886 |
| vault:grounded-tsh-trend | 8.96 | abstain 0/1/1 f=0.592 | abstain 1/0/1 f=0.592 | entailment 0.992; entailment 0.992 |
| vault:grounded-vitamin-d-latest | 8.91 | abstain 0/2/2 f=0.497 | abstain 0/2/2 f=0.497 | entailment 0.688; neutral 0.992; neutral 0.992; neutral 0.992; neutral 0.992 |
| vault:grounded-vitamin-d-trend | 10.05 | abstain 0/1/1 f=0.526 | abstain 1/0/1 f=0.526 | entailment 0.993; entailment 0.993 |

Reading the tables, with the limits of what was checked:

- **llama3.1:8b, flag off, fails claims on correct text.** For `answer-glucose-cited-latest` the model wrote "Your glucose level was 95 mg/dL." and "Normal fasting glucose is typically 70-100 mg/dL." with correct values and citations; the verifier reported `claim_1: Cannot verify claim without source evidence`, `claim_3: Verification failed: Only 0 supporting source(s), need at least 1; Faithfulness score (0.10) below threshold (0.6)`, `claim_4: Cannot verify claim without source evidence`. These strings are in the committed JSON as `off.claims_with_issues_rederived`, re-derived without a model run by `summarize.py --rederive` (flag-off `validate_response` on the stored text; the assertion that its failed-claim count equals the recorded one passed for every legacy case; vault cases were not re-derived). The structured-output renderer emits bullets of the form `- text. [cite:1]`; the golden fixtures put the marker before the period (`text [cite:1].`). In the NLI premise/hypothesis column the claim text shows a leading `[cite:1]\n- ` fragment, so claim splitting appears to detach the marker from its sentence on this format. That is the likely cause, not proven here (the claim extractor was not read or modified).
- **Where NLI changed claim counts** (llama, 7 cases): `a1c-trend` 1 to 2 verified, `creatinine-trend` 0 to 1, `glucose-trend` 0 to 1, `ldl-trend` 0 to 1, `sodium-trend` 0 to 2, `vitamin-d-trend` 0 to 1, and `triglycerides-latest` 1 to 0. Every case still abstained: `faithfulness_score` is computed by `FaithfulnessScorer` and did not change with the flag (the "f=" values are identical off and on in all 52 case-runs), and it was below 0.6 in 18 of 26 llama cases (15 of 26 qwen).
- **qwen3:8b**: flag-on changes were `sodium-latest` served to abstain (entailment 0.619, claim failed), and `tsh-trend` and `vitamin-d-trend` 0 to 1 verified (abstained either way). `vitamin-d-latest` scored `entailment` 0.688 (also under 0.7) but was already abstained flag off. 2 of 26 qwen NLI entailments were under the 0.7 floor; 1 of 60 llama NLI calls was a `contradiction` (0.577, `potassium-trend`, on a claim the rules had already failed).
- **qwen3:8b empty output served.** `legacy:answer-glucose-cited-latest` and `vault:grounded-sodium-trend` hit 1024 generated tokens with empty text; `finish_reason` was reported as `stop`. `validate_response` returned `is_valid` true, 0 claims, `faithfulness_score` 1.0, so the pair counts as "served" in the table above, flag off and on. Whether qwen3's thinking tokens consumed the cap was not checked. Four more qwen cases at the cap returned truncated JSON and were withheld by the renderer (abstain). What the HTTP route shows the patient for an empty `is_valid` answer was not driven. **Inferred from code, not driven:** empty text passes `_generate_with_runner` unchanged (`rag.py:1362`, `1462-1464`), the claim extractor yields no claims (`claim_extractor.py:186`), `validate_response` returns `is_valid` True (`rag.py:956`), `_legacy_serve_or_abstain` passes a valid result through (`api/assistant.py:250-251`), so `POST /assistant/chat` would return 200 with `segments=[]`, `full_response=""` and `is_valid` true (`assistant.py:953-959`, `1036-1046`) and save an empty assistant turn.
- Llama's 8 legacy questions produced near-identical answers (same glucose chunk set); they are not 8 independent samples.

### 9. Long source chunk truncation

`max_length` is 512. The pair is `(source_text, claim)`, so with the default truncation the source is the side that is cut. Claim "Your glucose was 95 mg/dL." (8 tokens); supporting fact "Glucose: 95 mg/dL (reference range 70-100 mg/dL), collected 2026-01-10." (24 tokens) with generic lab-method filler (36 tokens per sentence pair) placed after it (fact first) or before it (fact last). Token counts from the model's own tokenizer.

| Filler tokens | Source tokens | Pair over 512 | Fact first: label conf | Fact last: label conf |
|---|---|---|---|---|
| 0 (fact alone) | 24 | no | entailment 0.973 | same |
| 400 | 456 | no | entailment 0.976 | entailment 0.984 |
| 700 | 744 | yes | entailment 0.981 | entailment 0.960 |
| 1500 | 1536 | yes | entailment 0.981 | entailment 0.960 |

The label did not change when the fact sat past the 512th token. This is not the result the plan's risk 8 predicted, and it was not investigated further: it is consistent with the tokenizer truncating a different side than assumed, or with the model reading the leading "Glucose" context or the filler as support, but no variant (wrong-value claim, unrelated filler) was run, so it does not show that a truncated-away fact is still checked. Treat it as "no label change observed in this one fixture". The transformers warning "Token indices sequence length is longer than the specified maximum sequence length for this model (540 > 512)" was printed once, by the tokenizer-length probe, not by `predict`.

### Laptop vs model host, `run_all.sh`

| Item | Laptop 2026-10-20 | Model host 2026-10-21 |
|---|---|---|
| First-call load | 7.73 s | 9.62 s |
| `predict` median / p95 / max | 60.5 / 489.4 / 1,744 ms | 76.1 / 142.7 / 217.4 ms |
| Peak RSS (latency run) | 1,098 MB | 748 MB (torch 2.14.1+cpu, transformers 5.20.1) |
| Gate flag off / on | PASS / FAIL `answer_rate=0.000` | PASS / FAIL `answer_rate=0.000` |
| Gate NLI calls on / elapsed | 7 / 12.0 s | 7 / 20.7 s |
| Rules-verified pairs failed by NLI; as contradiction | 6; 0 | 6; 0 |
| Cold event-loop stall | 8,343 ms | 14,102 ms |
| Routes table | as in the 2026-10-20 report | identical |

## Surprises

1. Real llama3.1:8b output was withheld in 26 of 26 cases with the flag off, so on this prompt path the verifier, not the NLI flag, decided the outcome. Why is partly explained above (marker detached from the sentence) and not proven.
2. Flag on never converted an abstention into a served answer for either model; its one served-answer change was a correct qwen claim scored 0.619.
3. qwen3:8b hit the generation cap in 6 of 26 cases and two empty answers were treated as valid and served (flag off and on). Independent of the flag.
4. The cold NLI stall was longer here (14.1 s) than on the laptop (8.3 s), and the CPU torch build is what runs on this host; the 3080 does not help the NLI model.
5. Truncation: no label change with the fact beyond token 512 (one fixture).
6. 2-byte difference in fetched directory size versus the laptop (`du -sb`), not investigated.

## What this evidence would fail to notice

- Two small local models and 26 questions, nearly all about a single analyte; no breadth across medical domains or wording. Temperature 0, no seed.
- Retrieval is faked and vault chunks lack reference ranges and flags, so the prompts are simpler than the app's real context.
- `validate_response` was called directly, not through the HTTP route; the empty-answer and abstention rendering a patient sees was not driven.
- The claim-extraction explanation for the llama failures is inferred from one case, not traced through the extractor.
- Truncation was tested on one fixture type with one claim.
- Latency came from a host with other jobs on the box (load average about 17 at the start of the run).

## Raw output

### Summary figures recomputed from the committed JSON (`summarize.py`)

```text
llama3.1:8b: cases=26 served_off=0 served_on=0 abstain_off=26 abstain_on=26 escalate_off=0 escalate_on=0
  tokens>=1024=0 empty_raw=0 gen_s median=1.835 total=55.2
  faithfulness identical off/on in 26 of 26; faith<0.6 (on)=18
  verified-count changed=7 up=6 down=1
  nli calls=60 {'entailment': 26, 'neutral': 33, 'contradiction': 1} entailment<0.7=0
  served->abstain: [] abstain->served: []
qwen3:8b: cases=26 served_off=8 served_on=7 abstain_off=18 abstain_on=19 escalate_off=0 escalate_on=0
  tokens>=1024=6 empty_raw=2 gen_s median=9.775 total=293.6
  faithfulness identical off/on in 26 of 26; faith<0.6 (on)=15
  verified-count changed=3 up=2 down=1
  nli calls=39 {'entailment': 26, 'neutral': 13} entailment<0.7=2
  served->abstain: ['vault:grounded-sodium-latest'] abstain->served: []
```

### `run_all.sh` on this host (filtered by the script)

```text
$ ls -la models/nli/nli-deberta-v3-xsmall; du -sb models/nli/nli-deberta-v3-xsmall; du -ab models/nli/nli-deberta-v3-xsmall
total 287592
drwxrwxrwx 1 danny danny      4096 Oct 21 00:54 .
drwxrwxrwx 1 danny danny      4096 Oct 21 00:54 ..
drwxrwxrwx 1 danny danny      4096 Oct 21 00:53 .cache
-rwxrwxrwx 1 danny danny      2871 Oct 21 00:53 README.md
-rwxrwxrwx 1 danny danny        26 Oct 21 00:53 added_tokens.json
-rwxrwxrwx 1 danny danny      1053 Oct 21 00:53 config.json
-rwxrwxrwx 1 danny danny 283353172 Oct 21 00:54 model.safetensors
-rwxrwxrwx 1 danny danny       301 Oct 21 00:53 special_tokens_map.json
-rwxrwxrwx 1 danny danny   2464616 Oct 21 00:53 spm.model
-rwxrwxrwx 1 danny danny   8656624 Oct 21 00:53 tokenizer.json
-rwxrwxrwx 1 danny danny      1346 Oct 21 00:53 tokenizer_config.json
294485611	models/nli/nli-deberta-v3-xsmall
1	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/.gitignore
191	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/CACHEDIR.TAG
0	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/added_tokens.json.lock
101	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/added_tokens.json.metadata
0	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/config.json.lock
100	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/config.json.metadata
0	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/model.safetensors.lock
125	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/model.safetensors.metadata
0	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/README.md.lock
101	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/README.md.metadata
0	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/special_tokens_map.json.lock
100	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/special_tokens_map.json.metadata
0	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/spm.model.lock
125	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/spm.model.metadata
0	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/tokenizer.json.lock
100	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/tokenizer.json.metadata
0	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/tokenizer_config.json.lock
101	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/tokenizer_config.json.metadata
853	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download
4557	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/trees/a150876415327c80daeff35ca6f68f5ed8cf5c24.json
4557	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/trees
5602	models/nli/nli-deberta-v3-xsmall/.cache/huggingface
5602	models/nli/nli-deberta-v3-xsmall/.cache
26	models/nli/nli-deberta-v3-xsmall/added_tokens.json
1053	models/nli/nli-deberta-v3-xsmall/config.json
283353172	models/nli/nli-deberta-v3-xsmall/model.safetensors
2871	models/nli/nli-deberta-v3-xsmall/README.md
301	models/nli/nli-deberta-v3-xsmall/special_tokens_map.json
2464616	models/nli/nli-deberta-v3-xsmall/spm.model
8656624	models/nli/nli-deberta-v3-xsmall/tokenizer.json
1346	models/nli/nli-deberta-v3-xsmall/tokenizer_config.json
294485611	models/nli/nli-deberta-v3-xsmall
$ sha256sum models/nli/nli-deberta-v3-xsmall/model.safetensors
4e4fc4977f8d29d2a164255c8f69b9d6c158deeb309bb5e70445b94666ccd9e9  models/nli/nli-deberta-v3-xsmall/model.safetensors
$ grep sha256 ../../config/model_manifest.json | grep 4e4fc
      "sha256": "4e4fc4977f8d29d2a164255c8f69b9d6c158deeb309bb5e70445b94666ccd9e9",
$ grep license models/nli/nli-deberta-v3-xsmall/README.md
11:license: apache-2.0

$ python measure.py load
sentencepiece importable: no -> ModuleNotFoundError
rss_before_MB 93.0
first_call_total_s 9.621 sha256_s 2.133 load_only_s 7.488
rss_after_load_MB 649.1
id2label {0: 'contradiction', 1: 'entailment', 2: 'neutral'}
tokenizer DebertaV2Tokenizer is_fast True
sentencepiece loaded in sys.modules after load: False
socket attempts 0

$ python measure.py latency
pairs 138
first_call_s 14.066
n_calls 414 distinct_pairs 138
predict_ms median 76.1 p95 142.7 max 217.4 mean 84.7
labels {'contradiction': 33, 'entailment': 35, 'neutral': 70}
peak_rss_MB 747.8
max_length 512
socket attempts 0

$ python measure.py contradiction
claim/source pairs 138 rules_verified 33 rules_ok->nli_fail 6 of which CONTRADICTION 0 of which conf<0.7 0
nli_ok->rules_fail (NLI rescues) 7
  lowconf-contradiction: {'tag': 'agent:grounded-a1c-latest:normal', 'claim': 'Your HbA1c result is normal.', 'rules_ok': False, 'nli_ok': False, 'nli_label': 'contradiction', 'nli_conf': 0.487}
  lowconf-contradiction: {'tag': 'agent:grounded-a1c-trend:normal', 'claim': 'Your HbA1c result is normal.', 'rules_ok': False, 'nli_ok': False, 'nli_label': 'contradiction', 'nli_conf': 0.551}
  lowconf-contradiction: {'tag': 'agent:grounded-a1c-trend:normal', 'claim': 'Your HbA1c result is normal.', 'rules_ok': False, 'nli_ok': False, 'nli_label': 'contradiction', 'nli_conf': 0.571}
all low-confidence (<0.7) contradiction rows (any rules result): 3

$ python measure.py gate

=== flag=False elapsed 13.94s, nli calls 0 ===
========================================================================
Legacy RAG eval gate: served output of POST /assistant/chat
========================================================================
  total cases:        8
  served_invalid:     0  (bar: == 0)
  uncited_served:     0  (bar: == 0)
  leaked:             0  (bar: == 0)
  persisted_mismatch: 0  (bar: == 0)
  abstention:         1.000  (bar: == 1.000)
  escalation:         1.000  (bar: == 1.000)
  answer_rate:        1.000  (bar: == 1.000)
Legacy eval gate: PASS

=== flag=True elapsed 20.73s, nli calls 7 ===
========================================================================
Legacy RAG eval gate: served output of POST /assistant/chat
========================================================================
  total cases:        8
  served_invalid:     0  (bar: == 0)
  uncited_served:     0  (bar: == 0)
  leaked:             0  (bar: == 0)
  persisted_mismatch: 0  (bar: == 0)
  abstention:         1.000  (bar: == 1.000)
  escalation:         1.000  (bar: == 1.000)
  answer_rate:        0.000  (bar: == 1.000)
  FAILED answer-glucose-cited-latest: expect=answer abstained=True escalated=False is_valid=False
  FAILED answer-glucose-cited-with-reference: expect=answer abstained=True escalated=False is_valid=False
Legacy eval gate: FAIL answer_rate=0.000 (must be 1.0)

=== per-case (off -> on) ===
abstain-generation-timeout: abstained True->True valid False->False text_same=True claims(v,f,t) (0, 2, 2)->(0, 2, 2)
abstain-hallucinated-value: abstained True->True valid False->False text_same=True claims(v,f,t) (0, 1, 1)->(0, 1, 1)
   issues_off ['claim_1: Verification failed: Only 0 supporting source(s), need at least 1; Faithfulness score (0.10) below threshold (0.6)']
   issues_on  ['claim_1: Verification failed: 1 source(s) contradict this claim; Only 0 supporting source(s), need at least 1; Faithfulness score (0.00) below threshold (0.6)']
abstain-invalid-citation-id: abstained True->True valid False->False text_same=True claims(v,f,t) (0, 1, 1)->(0, 1, 1)
abstain-uncited-report-facts: abstained True->True valid False->False text_same=True claims(v,f,t) (0, 2, 2)->(0, 2, 2)
abstain-unverifiable-claim: abstained True->True valid False->False text_same=True claims(v,f,t) (1, 1, 2)->(0, 2, 2)
   issues_off ['claim_2: Verification failed: Only 0 supporting source(s), need at least 1; Faithfulness score (0.10) below threshold (0.6)']
   issues_on  ['claim_1: Verification failed: Only 0 supporting source(s), need at least 1; Faithfulness score (0.10) below threshold (0.6)', 'claim_2: Verification failed: Only 0 supporting source(s), need at least 1; Faithfulness score (0.10) below threshold (0.6)']
answer-glucose-cited-latest: abstained False->True valid True->False text_same=False claims(v,f,t) (1, 0, 1)->(0, 1, 1)
   issues_off []
   issues_on  ['claim_1: Verification failed: Only 0 supporting source(s), need at least 1; Faithfulness score (0.10) below threshold (0.6)']
answer-glucose-cited-with-reference: abstained False->True valid True->False text_same=False claims(v,f,t) (2, 0, 2)->(0, 2, 2)
   issues_off []
   issues_on  ['claim_1: Verification failed: Only 0 supporting source(s), need at least 1; Faithfulness score (0.10) below threshold (0.6)', 'claim_2: Verification failed: Only 0 supporting source(s), need at least 1; Faithfulness score (0.10) below threshold (0.6)']
escalate-prohibited-advice: abstained False->False valid False->False text_same=True claims(v,f,t) (1, 1, 2)->(0, 2, 2)
   issues_off ['claim_2: Cannot verify claim without source evidence']
   issues_on  ['claim_1: Verification failed: Only 0 supporting source(s), need at least 1; Faithfulness score (0.10) below threshold (0.6)', 'claim_2: Cannot verify claim without source evidence']

NLI calls flag on (claim, src, label, conf):
   ('Your glucose was 182 mg/dL [cite:1].', '1', 'contradiction', 0.998)
   ('Your glucose result was 95 mg/dL, within the reference range of 70-100 mg/dL [cite:1].', '1', 'entailment', 0.668)
   ("Glucose is the primary source of energy for the body's cells [cite:2].", '2', 'neutral', 0.997)
   ('Glucose: 95 mg/dL (reference range 70-100 mg/dL) [cite:1].', '1', 'neutral', 0.996)
   ('Your glucose was 95 mg/dL [cite:1].', '1', 'neutral', 0.858)
   ('Normal fasting glucose is typically 70-100 mg/dL [cite:2].', '2', 'neutral', 0.963)
   ('Your glucose was 95 mg/dL [cite:1].', '1', 'neutral', 0.858)
peak_rss_MB 778.7 socket attempts 0

$ python measure.py block
COLD abstain-hallucinated-value: query 14101 ms, max event-loop stall 14102 ms
warm abstain-invalid-citation-id: query 2 ms, max event-loop stall 3 ms
warm abstain-uncited-report-facts: query 1 ms, max event-loop stall 3 ms
warm abstain-unverifiable-claim: query 208 ms, max event-loop stall 209 ms
warm answer-glucose-cited-latest: query 76 ms, max event-loop stall 77 ms
warm answer-glucose-cited-with-reference: query 153 ms, max event-loop stall 155 ms
warm abstain-hallucinated-value: query 112 ms, max event-loop stall 113 ms
warm abstain-invalid-citation-id: query 1 ms, max event-loop stall 2 ms
warm abstain-uncited-report-facts: query 3 ms, max event-loop stall 4 ms
warm abstain-unverifiable-claim: query 227 ms, max event-loop stall 229 ms
warm answer-glucose-cited-latest: query 101 ms, max event-loop stall 102 ms
warm answer-glucose-cited-with-reference: query 189 ms, max event-loop stall 190 ms
warm abstain-hallucinated-value: query 99 ms, max event-loop stall 100 ms
warm abstain-invalid-citation-id: query 1 ms, max event-loop stall 2 ms
warm abstain-uncited-report-facts: query 1 ms, max event-loop stall 2 ms
warm abstain-unverifiable-claim: query 157 ms, max event-loop stall 158 ms
warm answer-glucose-cited-latest: query 85 ms, max event-loop stall 86 ms
warm answer-glucose-cited-with-reference: query 175 ms, max event-loop stall 176 ms
cold stall ms 14102 | warm stall median/max ms 100 229
flag-off max stall ms median/max 2 3
peak_rss_MB 758.4

$ python routes_probe.py
--- flag off (baseline) ---
 POST /assistant/chat -> (200, 'answer-segments', '{"segments":[{"segment_type":"report_facts","content":"Your glucose was 95 mg/dL [cite:1].') 0
 interpret-grounded   -> (201, {'is_valid': True, 'verified': 2, 'failed': 0, 'faithfulness': 0.814, 'segments': 2, 'detail': None}) 0
--- flag on, model present (real predict) ---
 POST /assistant/chat                              -> (200, 'uncertainty', '{"segments":[{"segment_type":"uncertainty","content":"There isn\'t enough verified informat') 0
 POST /interpretations/observations/{id}/interpret-grounded -> (201, {'is_valid': False, 'verified': 0, 'failed': 2, 'faithfulness': 0.814, 'segments': 2, 'detail': None}) 0
--- flag on, model absent ---
 POST /assistant/chat                              -> (200, 'uncertainty', '{"segments":[{"segment_type":"uncertainty","content":"There isn\'t enough verified informat') 2
 POST /interpretations/observations/{id}/interpret-grounded -> (201, {'is_valid': False, 'verified': 0, 'failed': 2, 'faithfulness': 0.814, 'segments': 2, 'detail': None}) 2
--- flag on, predict raises RuntimeError ---
 POST /assistant/chat                              -> (500, 'answer-segments', '{"detail":"Error processing chat request"}') 0
 POST /interpretations/observations/{id}/interpret-grounded -> (503, {'is_valid': None, 'verified': None, 'failed': None, 'faithfulness': None, 'segments': 0, 'detail': 'The explanation could not be generated right now. Please try again.'}) 0
--- flag on, predict returns unmapped label index ---
 POST /assistant/chat                              -> (500, 'answer-segments', '{"detail":"Error processing chat request"}') 0
 POST /interpretations/observations/{id}/interpret-grounded -> (500, 'Internal Server Error') 0
socket attempts 0

$ git status --short (repo root)
?? docs/reviews/2026-10-21/
run_all_exit=0
```

### `real_llm.py trunc`

```text
  print("max_length", enc.max_length)
max_length 512
fact tokens 24 claim tokens 8 filler_unit tokens 36
{'filler_tokens': 0, 'fact_position': 'alone', 'source_tokens': 24, 'pair_tokens_approx': 35, 'over_512': False, 'label': 'entailment', 'conf': 0.973}
{'filler_tokens': 400, 'fact_position': 'first', 'source_tokens': 456, 'pair_tokens_approx': 467, 'over_512': False, 'label': 'entailment', 'conf': 0.976}
{'filler_tokens': 400, 'fact_position': 'last', 'source_tokens': 456, 'pair_tokens_approx': 467, 'over_512': False, 'label': 'entailment', 'conf': 0.984}
[transformers] Token indices sequence length is longer than the specified maximum sequence length for this model (540 > 512). Running this sequence through the model will result in indexing errors
{'filler_tokens': 700, 'fact_position': 'first', 'source_tokens': 744, 'pair_tokens_approx': 755, 'over_512': True, 'label': 'entailment', 'conf': 0.981}
{'filler_tokens': 700, 'fact_position': 'last', 'source_tokens': 744, 'pair_tokens_approx': 755, 'over_512': True, 'label': 'entailment', 'conf': 0.96}
{'filler_tokens': 1500, 'fact_position': 'first', 'source_tokens': 1536, 'pair_tokens_approx': 1547, 'over_512': True, 'label': 'entailment', 'conf': 0.981}
{'filler_tokens': 1500, 'fact_position': 'last', 'source_tokens': 1536, 'pair_tokens_approx': 1547, 'over_512': True, 'label': 'entailment', 'conf': 0.96}
socket: other attempts 0
```

### `real_llm.py gen llama3.1:8b` (summary lines)

```text
provider OllamaProvider model llama3.1:8b
SUMMARY model=llama3.1:8b cases=26 served_off=0 served_on=0 abstain_off=26 abstain_on=26 escalate_off=0 escalate_on=0
ollama connects 27 OTHER socket attempts 0 [] peak_rss_MB 770.5
```

### `real_llm.py gen qwen3:8b` (summary lines)

```text
provider OllamaProvider model qwen3:8b
SUMMARY model=qwen3:8b cases=26 served_off=8 served_on=7 abstain_off=18 abstain_on=19 escalate_off=0 escalate_on=0
ollama connects 27 OTHER socket attempts 0 [] peak_rss_MB 773.9
```
