# G-C5 Task 7: real-model evidence (laptop, CPU)

**Last Updated:** 2026-10-20
**Owner:** repository owner
**Status:** Measured evidence only. No flag, code or default changed; `use_llm_entailment` stays off.
**Refresh Trigger:** the model pin changes, the verifier hunk (`verifier_agent.py:304-317`) changes, or the Ollama/GPU model-host run is done.

Plan: [GC5 plan, Task 7](../../plans/2026-10-18-GC5-hc-m11-nli-flag-off.md#task-7--owner-host-evidence-not-part-of-the-pr). Run by an agent on the owner's dev laptop (CPU, no GPU) under the owner's session /goal ("if huggingface.co is reachable, run the G-C5 real-model steps"). Plan Task 7 names the owner/model host; the owner is to confirm at the model host.

Scripts: [`gc5-evidence/`](gc5-evidence/) (`measure.py`, `routes_probe.py`, `run_all.sh`; scripts only, no model files). Re-run: `flock` all three `/tmp/claude-1000/hc-pytest.{1,2,3}.lock`, then `gc5-evidence/run_all.sh <worktree-root>`. The raw output of that run is pasted in [Raw output](#raw-output).

## Verdict

With the flag on and the real model present, **both legacy "answer" golden cases were abstained** (`answer_rate` 0.000, bar 1.000), so the legacy RAG eval gate fails flag-on. Two causes, both on fixed fixture text: the correct restatement "Your glucose was 95 mg/dL" scored `neutral` 0.858, and "Your glucose result was 95 mg/dL, within the reference range of 70-100 mg/dL" scored `entailment` 0.668, under the 0.7 floor. Real LLM output is UNMEASURED. Keep the flag off. The event loop was blocked about 8.3 s on the first answer, and 41 ms to 1.0 s on later answers that reach the verifier.

## Setup

| Item | Value |
|---|---|
| Host | WSL2, 6 vCPU, 22 GiB, CPU only (no GPU, no Ollama) |
| Stack | torch 2.14.0+cu130 (CPU used), sentence-transformers 6.1.0, transformers 5.17.0, `~/venvs/asclexis-311` |
| Tree | worktree from `origin/main` 699eb18 (flag code present), branch `docs/gc5-real-model-evidence-2026-10-20` |
| Isolation | all three pyslot locks held with nested `flock` for the fetch and for the re-run; no other pytest ran in this worktree |
| Network | only `download_models.py nli` (first run). Every measurement: `HF_HUB_OFFLINE=1` plus `socket.connect/connect_ex/bind/sendto/create_connection/getaddrinfo` patched to raise. Socket attempts: **0** in every run |
| Flag | on only via `settings.use_llm_entailment = True` and `api.assistant._rag_module = None` inside the measuring process |
| Runs | the first run (scratch scripts, since deleted) and the re-run of the committed scripts. Numbers that changed on re-run are marked |

## Results

| # | Measurement | Status | Value (re-run of committed scripts) |
|---|---|---|---|
| 1 | Real fetch | MEASURED | 8 files, 294,485,613 bytes on disk (`du -sb`), of which `model.safetensors` 283,353,172. The 5,604-byte difference from the plan's 294,480,009 is the `.cache/` directory Hugging Face writes into the target (`du -ab` below shows `.cache` = 5,604). Fetch took 33.1 s (first run, not repeated). **sha256 matched: yes** (`4e4fc497...d9e9`, equal to the manifest pin; `cmd_nli` printed "NLI model installed", which it does only on a match) |
| 2 | Offline load, sockets blocked | MEASURED | `id2label {0: 'contradiction', 1: 'entailment', 2: 'neutral'}`; tokenizer `DebertaV2Tokenizer`, `is_fast True`; **`sentencepiece` not installed and not needed** (absent from `sys.modules` after load); 0 socket attempts. No `requirements.txt` change |
| 3a | First-call latency | MEASURED | 7.73 s total = sha256 1.98 s + load 5.75 s (first run: 8.39 s = 1.99 + 6.40). Including the first `predict`: 9.15 s (first run 9.33 s) |
| 3b | `predict` latency | MEASURED | 138 pairs, 414 calls, one pair per call. **Changed on re-run:** median 60.5 ms, p95 489.4 ms, max 1,744 ms, mean 146.9 ms (first run: median 39.7, p95 136.9, max 850). The box was shared with other jobs; treat the spread, not either median, as the finding |
| 3c | Peak RSS | MEASURED | 92.7 MB before load, 1,001 MB after load, **1,098 MB peak** after 414 predicts (first run 1,098.5); 1,126 MB in the gate run (which also loads MiniLM) |
| 4 | Legacy RAG eval gate, flag on | MEASURED (gate fakes generation, no Ollama needed) | Flag off: PASS, 1.72 s, 0 NLI calls. **Flag on: FAIL `answer_rate=0.000`**, 7 NLI calls, 12.0 s. Abstained on fixed fixture text: both `answer-*` cases. Table below |
| 5 | Low-confidence CONTRADICTION failing a rules-verified claim | MEASURED, small and partly synthetic sample | **0 of 33** rules-verified pairs (138 pairs, 112 of them synthetic perturbations built for this measurement, not shipped fixtures; do not generalise). 6 of 33 were failed by NLI, none as `contradiction`. 3 sub-0.7 contradictions (0.487, 0.551, 0.571) all sit on claims the rules had already failed. NLI verified 7 pairs the rules failed |
| 6 | Route behaviour over HTTP | MEASURED | Via `tests/support/routes.py::route_client` (chat through `harness.legacy_chat_client`, which calls `route_client`; interpret-grounded through `route_client` directly), so FastAPI's dependency graph ran. Table below |
| 7 | Event-loop blocking, flag on | MEASURED | First answer **8,343 ms** (first run 9,401 to 9,839 ms). Later answers: 0 to 3 ms when no claim reaches the verifier, else 41 ms to 1,030 ms (the stall equals the whole `query()`). Flag off: 2 to 3 ms |
| - | Real LLM output, Ollama/GPU quality | UNMEASURED-needs-model-host | Gate `model_output` is fixed text; no GPU or Ollama here |
| - | Long source chunk truncation (plan risk 8) | UNMEASURED | `max_length` is 512 tokens; fixture sources are one to two sentences, so truncation was not exercised |

Pairs for 3b and 5: claims split from the 8 legacy golden `model_output` texts crossed with the glucose chunk set (26 pairs), plus 4 claims (true value, wrong value, "is high", "is normal") per observation in the 18 `tests/agent/golden/grounded-*.json` vaults (28 observations, 112 pairs).

### 4. Flag on vs off, per legacy golden case

| Case | Off | On | Claims off (verified, failed, total) | Claims on |
|---|---|---|---|---|
| abstain-generation-timeout | abstain | abstain | 0, 2, 2 | 0, 2, 2 |
| abstain-hallucinated-value | abstain | abstain | 0, 1, 1 | 0, 1, 1 (reason now "1 source(s) contradict"; NLI contradiction 0.998) |
| abstain-invalid-citation-id | abstain | abstain | 0, 1, 1 | 0, 1, 1 |
| abstain-uncited-report-facts | abstain | abstain | 0, 2, 2 | 0, 2, 2 |
| abstain-unverifiable-claim | abstain | abstain | 1, 1, 2 | 0, 2, 2 (a rules-verified claim now fails) |
| **answer-glucose-cited-latest** | served, valid | **abstained**, invalid | 1, 0, 1 | 0, 1, 1 |
| **answer-glucose-cited-with-reference** | served, valid | **abstained**, invalid | 2, 0, 2 | 0, 2, 2 |
| escalate-prohibited-advice | escalate | escalate | 1, 1, 2 | 0, 2, 2 |

`served_invalid`, `uncited_served` and `leaked` stayed 0 flag-on: the safety direction held, usefulness did not.

### 6. Routes (2-claim answer; retrieval and generation faked, real `validate_response`, real model)

| Scenario (flag on unless noted) | `POST /assistant/chat` | `POST /interpretations/observations/{id}/interpret-grounded` | NLI warning lines per answer |
|---|---|---|---|
| Flag off | 200, answer served | 201, `is_valid` true, 2 of 2 verified | 0 / 0 |
| Model present | 200, abstention template | 201, `is_valid` false, 0 of 2 verified, 2 failed, answer text still served | 0 / 0 |
| Model absent | 200, abstention template | 201, `is_valid` false, 0 of 2 verified, answer text still served | **2 / 2** (one per claim x source; path-free message) |
| `predict` raises `RuntimeError` | **500** "Error processing chat request" | **503** "The explanation could not be generated right now..." | 0 / 0 |
| Unmapped label index | **500** | **500** `Internal Server Error` (unhandled) | 0 / 0 |

Confirms plan rows 10 and 11. `faithfulness_score` stayed 0.814 on `interpret-grounded` while 0 of 2 claims verified, so a client reading only that score would miss the failure.

## Surprises

1. Flag on, the real model abstained both legacy answer cases on fixed fixture text (item 4). Whether real LLM output fares better is UNMEASURED.
2. No CONTRADICTION over-fail in the small sample (item 5).
3. Licence: README line 11 reads `license: apache-2.0`. `feature_list.json:142` ("MIT") is wrong. Base-model licence not reviewed.
4. `sentencepiece` not needed.
5. Peak RSS about 1.1 GB for a 283 MB model (F32 weights plus torch runtime); pyslot assigns about 2 GB per slot, so a slot holder running the model uses over half its budget.
6. First answer blocks the event loop about 8 to 10 s.

## What this evidence would fail to notice

- Fake generation: real LLM phrasing may sit closer to or further from the source.
- 138 pairs, 8 golden cases, one glucose chunk set: no medical-domain breadth. Latency is from 6 shared CPU cores.
- Routes stub retrieval and generation; DB-backed retrieval was not run.
- Latency and stall figures moved by 2 to 4x between two runs on a loaded box.

## Raw output

Commands and output of the re-run (`gc5-evidence/run_all.sh`, all three pyslot locks held, `HF_HUB_OFFLINE=1`, sockets blocked; progress bars and warnings filtered by the script). The download line of item 1 is from the first run: `cd src/backend && python scripts/download_models.py nli` printed `NLI model installed: .../models/nli/nli-deberta-v3-xsmall`, real 33.1 s, exit 0.

```text
$ ls -la models/nli/nli-deberta-v3-xsmall; du -sb models/nli/nli-deberta-v3-xsmall; du -ab models/nli/nli-deberta-v3-xsmall
total 287592
drwxrwxrwx 1 danny danny      4096 Oct 20 22:51 .
drwxrwxrwx 1 danny danny      4096 Oct 20 22:51 ..
drwxrwxrwx 1 danny danny      4096 Oct 20 22:50 .cache
-rwxrwxrwx 1 danny danny      2871 Oct 20 22:50 README.md
-rwxrwxrwx 1 danny danny        26 Oct 20 22:50 added_tokens.json
-rwxrwxrwx 1 danny danny      1053 Oct 20 22:50 config.json
-rwxrwxrwx 1 danny danny 283353172 Oct 20 22:51 model.safetensors
-rwxrwxrwx 1 danny danny       301 Oct 20 22:50 special_tokens_map.json
-rwxrwxrwx 1 danny danny   2464616 Oct 20 22:50 spm.model
-rwxrwxrwx 1 danny danny   8656624 Oct 20 22:50 tokenizer.json
-rwxrwxrwx 1 danny danny      1346 Oct 20 22:50 tokenizer_config.json
294485613	models/nli/nli-deberta-v3-xsmall
1	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/.gitignore
191	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/CACHEDIR.TAG
0	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/added_tokens.json.lock
101	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/added_tokens.json.metadata
0	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/config.json.lock
101	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/config.json.metadata
0	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/model.safetensors.lock
125	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/model.safetensors.metadata
0	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/README.md.lock
100	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/README.md.metadata
0	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/special_tokens_map.json.lock
101	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/special_tokens_map.json.metadata
0	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/spm.model.lock
125	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/spm.model.metadata
0	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/tokenizer.json.lock
101	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/tokenizer.json.metadata
0	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/tokenizer_config.json.lock
101	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download/tokenizer_config.json.metadata
855	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/download
4557	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/trees/a150876415327c80daeff35ca6f68f5ed8cf5c24.json
4557	models/nli/nli-deberta-v3-xsmall/.cache/huggingface/trees
5604	models/nli/nli-deberta-v3-xsmall/.cache/huggingface
5604	models/nli/nli-deberta-v3-xsmall/.cache
26	models/nli/nli-deberta-v3-xsmall/added_tokens.json
1053	models/nli/nli-deberta-v3-xsmall/config.json
283353172	models/nli/nli-deberta-v3-xsmall/model.safetensors
2871	models/nli/nli-deberta-v3-xsmall/README.md
301	models/nli/nli-deberta-v3-xsmall/special_tokens_map.json
2464616	models/nli/nli-deberta-v3-xsmall/spm.model
8656624	models/nli/nli-deberta-v3-xsmall/tokenizer.json
1346	models/nli/nli-deberta-v3-xsmall/tokenizer_config.json
294485613	models/nli/nli-deberta-v3-xsmall
$ sha256sum models/nli/nli-deberta-v3-xsmall/model.safetensors
4e4fc4977f8d29d2a164255c8f69b9d6c158deeb309bb5e70445b94666ccd9e9  models/nli/nli-deberta-v3-xsmall/model.safetensors
$ grep sha256 ../../config/model_manifest.json | grep 4e4fc
      "sha256": "4e4fc4977f8d29d2a164255c8f69b9d6c158deeb309bb5e70445b94666ccd9e9",
$ grep license models/nli/nli-deberta-v3-xsmall/README.md
11:license: apache-2.0

$ python measure.py load
sentencepiece importable: no -> ModuleNotFoundError
rss_before_MB 92.7
first_call_total_s 7.726 sha256_s 1.979 load_only_s 5.748
rss_after_load_MB 1001.3
id2label {0: 'contradiction', 1: 'entailment', 2: 'neutral'}
tokenizer DebertaV2Tokenizer is_fast True
sentencepiece loaded in sys.modules after load: False
socket attempts 0

$ python measure.py latency
pairs 138
first_call_s 9.147
n_calls 414 distinct_pairs 138
predict_ms median 60.5 p95 489.4 max 1744.1 mean 146.9
labels {'contradiction': 33, 'entailment': 35, 'neutral': 70}
peak_rss_MB 1098.3
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

=== flag=False elapsed 1.72s, nli calls 0 ===
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

=== flag=True elapsed 12.02s, nli calls 7 ===
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
peak_rss_MB 1126.3 socket attempts 0

$ python measure.py block
COLD abstain-hallucinated-value: query 8342 ms, max event-loop stall 8343 ms
warm abstain-invalid-citation-id: query 1 ms, max event-loop stall 2 ms
warm abstain-uncited-report-facts: query 1 ms, max event-loop stall 2 ms
warm abstain-unverifiable-claim: query 449 ms, max event-loop stall 450 ms
warm answer-glucose-cited-latest: query 276 ms, max event-loop stall 277 ms
warm answer-glucose-cited-with-reference: query 347 ms, max event-loop stall 349 ms
warm abstain-hallucinated-value: query 41 ms, max event-loop stall 41 ms
warm abstain-invalid-citation-id: query 0 ms, max event-loop stall 3 ms
warm abstain-uncited-report-facts: query 1 ms, max event-loop stall 2 ms
warm abstain-unverifiable-claim: query 1029 ms, max event-loop stall 1030 ms
warm answer-glucose-cited-latest: query 492 ms, max event-loop stall 493 ms
warm answer-glucose-cited-with-reference: query 316 ms, max event-loop stall 318 ms
warm abstain-hallucinated-value: query 51 ms, max event-loop stall 52 ms
warm abstain-invalid-citation-id: query 0 ms, max event-loop stall 2 ms
warm abstain-uncited-report-facts: query 1 ms, max event-loop stall 2 ms
warm abstain-unverifiable-claim: query 636 ms, max event-loop stall 638 ms
warm answer-glucose-cited-latest: query 92 ms, max event-loop stall 93 ms
warm answer-glucose-cited-with-reference: query 518 ms, max event-loop stall 519 ms
cold stall ms 8343 | warm stall median/max ms 93 1030
flag-off max stall ms median/max 2 3
peak_rss_MB 1105.6

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
R  docs/reviews/2026-10-20-gc5-real-model-evidence.md -> docs/reviews/2026-10-20/gc5-real-model-evidence.md
?? docs/reviews/2026-10-20/gc5-evidence/
```
