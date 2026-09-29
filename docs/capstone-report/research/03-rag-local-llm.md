# Research 03 — RAG, Grounded Generation & Local-LLM Advances

**Last Updated:** 2026-09-25

Scouting pass over the 2023–2026 grounded-generation and local-LLM literature, mapped onto Asclexis's assistant path (`modules/agent` graph: plan→act→reflect→draft→guard, `MAX_STEPS=5`, 8 read-only tools — `src/backend/modules/agent/graph.py:176`; legacy `modules/rag.py` chat path). Prior internal art: `docs/plans/2026-06-30-tech-upgrade-survey-9-areas.md` (Areas 1, 2, 4 cover NLI models, vector indexing, OCR — this doc does not relitigate those verdicts, it updates them with post-survey sources and extends to eval/calibration areas the survey did not cover).

## Constraints that shape every verdict

- **Local-first, patient hardware.** Everything must run on a single-user CPU/mid-tier laptop (~8GB RAM floor). No network calls in product code paths; the only sanctioned egress is model download (`scripts/download_models.py`, integrity-pinned via `modules/model_integrity.py` MODEL-INT-001).
- **Ask-first files.** `modules/faithfulness.py`, `modules/verifier_agent.py`, `modules/redaction.py` (and the guardrail chain under `modules/agent/guardrails/`) require owner sign-off before modification. Contracts below describe *proposed* seams, not committed work.
- **Established anchors.** Citation enforcement is already mechanical — `rag.py:793 validate_response` + `groundedness.py:42 map_sentences` (drop uncited sentences) + `guard.py` zero-survivors→`abstain` and `CONFIDENCE_THRESHOLD`→`abstain`. Eval gate: `modules/agent/eval/scorer.py` six axes (groundedness must be 1.0; advice_leakage and phi_leakage must be 0). Known gaps: `faithfulness.py:99` `entailment_scores` param exists but is never fed; `faithfulness.py:134` `consistency_score=1.0` is a disclosed placeholder (HC-M11); `verifier_agent.py:88` `use_llm_entailment` routes to a stub; `scripts/download_models.py` is GGUF-only (the HC-M11 distribution blocker).

---

## 1. NLI cross-encoders for entailment (nli-deberta-v3 family)

**What it is.** `cross-encoder/nli-deberta-v3-xsmall` — the HC-M11 tracker candidate — is a ~22M-param DeBERTa-v3 encoder trained on SNLI+MultiNLI emitting 3-way softmax scores (contradiction/entailment/neutral): 91.64% SNLI-test, 87.77% MNLI-mismatched, ~90MB on disk, CPU-fast for short premise-hypothesis pairs, loads via the already-present `sentence-transformers` `CrossEncoder` API. The TRUE benchmark line of work (Honovich et al.; "With a Little Push…" follow-up) shows NLI models are the strongest *efficient* faithfulness signal when inference uses both entailment and contradiction probabilities — outperforming more complex QA-based metrics at a fraction of the cost. Known limitation relevant to us: clinical-NLI work (SemEval NLI4CT) shows encoder NLI models are weakest exactly where our risk is highest — numerical and multi-hop inference over clinical text (best system F1 0.57 on perturbed contrast sets).

**Proposed contract.** `modules/faithfulness.py`: a lazy `CrossEncoder` loaded from a local path (offline at inference) feeds the existing `entailment_scores` parameter of `score_claim` (faithfulness.py:99); `modules/verifier_agent.py`: `use_llm_entailment` (config.py:151) routes to the real NLI call instead of the stub. Regex/lexical scoring stays unconditional as the floor — NLI is additive confirmation, especially for contradiction detection (high/low flips). Flag default off. Requires extending `scripts/download_models.py` with a named non-GGUF entry + `model_integrity.py` hash pin. Owner-gated per HC-M11.

**Verdict: ADOPT** — as scoped in `feature_list.json` HC-M11, pending owner sign-off. Sources validate the model-class choice (xsmall is the right RAM/latency point; -small/-base are the upgrade path). The NLI4CT evidence *reinforces* keeping the deterministic numeric checks as floor — the contract above already does this. Do not widen scope: the NLI model is a tightening signal, never a reason to relax `ENTAILMENT_INDICATORS`/`CONTRADICTION_PATTERNS`.

**Sources**
- https://huggingface.co/cross-encoder/nli-deberta-v3-xsmall (model card: 91.64 SNLI / 87.77 MNLI-mm)
- https://exa.ai/library/publication/nsnsb7ggh4x — "With a Little Push, NLI Models can Robustly and Efficiently Predict Faithfulness" (TRUE benchmark)
- https://aclanthology.org/2024.semeval-1.143.pdf + https://sites.google.com/view/nli4ct/ — clinical NLI weakness on numerical inference
- Internal: `feature_list.json` HC-M11; `docs/plans/2026-06-30-tech-upgrade-survey-9-areas.md` Area 1; `audit/2026-09-25/plans/08-gated-items-review-packet.md` Brief 5

## 2. Purpose-built claim-checkers (MiniCheck / Bespoke-MiniCheck-7B)

**What it is.** MiniCheck (EMNLP 2024) distills claim-vs-document support checking into small specialist models trained on GPT-4-synthesized error data: MiniCheck-FT5 (770M) reaches GPT-4-level accuracy on the unified LLM-AggreFact benchmark at ~400× lower cost than LLM judges; `Bespoke-MiniCheck-7B` is the current leaderboard SOTA. Interface is exactly `score(document, claim) -> {0,1} + probability` — a drop-in for `verifier_agent`'s per-claim check, and it handles multi-sentence claims via sentence splitting (which `modules/claim_extractor.py` already does).

**Proposed contract.** If HC-M11 lands and the 74-case eval gate shows NLI misses on our claim distribution (especially numeric lab claims), `verifier_agent._check_entailment` gets a second flag-gated backend (`use_minicheck`) loading MiniCheck-FT5 from local weights; distribution goes through the same non-GGUF `download_models.py` extension. Bespoke-MiniCheck-7B is too heavy for the 8GB tier — exclude it.

**Verdict: WATCH** — strictly stronger than generic NLI on claim grounding (it was trained for exactly this primitive), but a second non-GGUF dependency with its own download path. Sequence behind HC-M11: ship the 22M cross-encoder first, measure its eval-gate deltas, adopt FT5 only if a measured gap remains. Ranking on LLM-AggreFact vs deberta-xsmall is real but both sit below an LLM judge; the question is whether the gap matters at our claim complexity.

**Sources**
- https://aclanthology.org/2024.emnlp-main.499.pdf — MiniCheck paper + LLM-AggreFact benchmark
- https://github.com/Liyan06/MiniCheck + https://huggingface.co/bespokelabs/Bespoke-MiniCheck-7B (SOTA card)
- Leaderboard: https://llm-aggrefact.github.io (referenced from repo README)

## 3. AlignScore (unified information-alignment metric)

**What it is.** ACL 2023 metric: a RoBERTa-based alignment function trained on 4.7M examples unified from 7 tasks (NLI, QA, paraphrase, fact verification, IR, STS, summarization). Score = max chunk↔sentence alignment averaged over sentences. 355M params (~1.4GB); matched or beat ChatGPT/GPT-4-based metrics across 22 factual-consistency datasets.

**Proposed contract.** Alternative backend for the same `entailment_scores`/`_check_entailment` seams as §1/§2 — nothing new. Its chunk-level max-alignment maps naturally onto our `RetrievedChunk` boundaries (one score per cited chunk rather than per source-text blob).

**Verdict: WATCH** — the best-documented single-signal fallback if nli-deberta-xsmall proves too weak on medical claims but MiniCheck is too heavy to ship. ~16× the xsmall's size; still CPU-viable for per-claim offline checks, marginal for per-turn online use on low tier.

**Sources**
- https://aclanthology.org/2023.acl-long.634/ + https://github.com/yuh-zha/AlignScore

## 4. Vectara HHEM-2.1-Open

**What it is.** Open-weights T5-family classifier purpose-built for RAG hallucination detection, outputting a 0–1 factual-consistency score; multilingual (EN/FR/DE). RAGAS documents it as a drop-in for the verification step of its faithfulness metric.

**Proposed contract.** Same seam again — third candidate behind the `use_llm_entailment` flag. No new interface.

**Verdict: REJECT** — functionally redundant with §1/§2/§3 and its license/distribution terms for a redistributed patient app are UNVERIFIED (the "Open" in the name needs a license read before any download). Weaker positioning than MiniCheck on LLM-AggreFact. Revisit only if both predecessors fail *and* license clears.

**Sources**
- https://www.vectara.com/blog/hhem-2-1-a-better-hallucination-detection-model
- https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/ (documents HHEM as the verification-step model)

## 5. LLM-as-judge for faithfulness

**What it is.** Prompting a generative LLM to grade claim-vs-source consistency, typically with a rubric. NAACL 2025 ("On a Scale From 1 to 5") found rubric-graded GPT-4 judges beat NLI models on hallucination sensitivity, especially with reasoning; ContextualJudgeBench (ACL 2025) measures where contextual judges fail. At our scale the only available judge is the *same local model* that generated the answer — self-judging, plus full generation cost per claim.

**Proposed contract.** Do not put LLM judging in the request path. The viable placement is **offline, in the eval harness**: `modules/agent/eval/scorer.py` or a sibling script runs the tier model as judge over golden cases to *calibrate* the mechanical/cross-encoder signals (which threshold on `min_faithfulness_score`, `min_entailment_confidence` actually separates good from bad?). Judge output never reaches users; it tunes constants.

**Verdict: ADAPT** — adopt the technique as an offline calibration instrument only. In-path judging is rejected on two independent grounds: latency (a second full generation per response on patient CPU) and self-grading bias (the same small model that hallucinated the claim scores its own support). Both failure modes are documented in the sources.

**Sources**
- https://aclanthology.org/2025.findings-naacl.433.pdf — rubric LLM judging vs NLI; synthetic unfaithful-data generation
- https://aclanthology.org/anthology-files/anthology-files/pdf/acl/2025.acl-long.470.pdf — ContextualJudgeBench

## 6. Multi-pass consistency / semantic entropy

**What it is.** Semantic entropy (Farquhar et al., Nature 2024): sample N answers, cluster by meaning via bidirectional entailment, compute entropy over clusters — high entropy ≈ confabulation. This is exactly what `faithfulness.py`'s `consistency_score` (placeholder 1.0, `enable_consistency_check`/`consistency_passes=3` config at :66-68) was designed to consume.

**Proposed contract.** Populate `consistency_score` for real only if a consistency pass is ever enabled: `ModelRunner` generates K samples at temperature>0, pairwise-entail (reusing the §1 cross-encoder) clusters them, entropy normalizes to 0–1. Lives entirely behind `FaithfulnessConfig.enable_consistency_check` (already False).

**Verdict: WATCH** — the literature method is sound and its target failure mode (confabulation) is ours, but N sampled generations × pairwise entailment on patient CPU multiplies per-turn cost 3–10×. Keep `enable_consistency_check` off; this becomes viable only on a GPU-capable tier or for the eval harness. Cheaper precursor if needed: single extra regeneration + entailment agreement check (K=2, no clustering).

**Sources**
- https://www.nature.com/articles/s41586-024-07421-0 — semantic entropy, incl. medical-domain motivation
- https://arxiv.org/html/2405.01563v1 — conformal abstention over self-consistency samples (same machinery, adds coverage guarantees)

## 7. ALCE-style citation-quality evaluation

**What it is.** ALCE (Princeton, EMNLP 2023): the canonical automatic citation eval — per-statement citation *recall* (is the statement entailed by its cited passages, via NLI) and citation *precision* (is every citation actually contributing). Headline finding: even the best 2023 systems leave ~50% of ELI5 statements without full citation support — the empirical case for mechanical enforcement rather than prompt-asking.

**Proposed contract.** `modules/agent/eval/scorer.py`: extend the `groundedness` axis. Today it proves every surviving sentence *has* a citation handle; ALCE adds whether the cited chunk *entails* the sentence — which is precisely the §1 cross-encoder's output applied to the (sentence, cited-chunk) pairs `map_sentences` already pairs up. Same flag as HC-M11; new axis `citation_support` with the gate's existing 1.0-bar discipline. Do not adopt the ALCE benchmark itself — its corpora (Wikipedia/Sphere) don't transfer to private labs; the *metric design* does.

**Verdict: ADAPT** — the metric design is the right upgrade to our strongest axis, and it's free once HC-M11 lands (same model, same seam). The ~50% headline number also justifies in the report why `map_sentences` drops sentences mechanically instead of trusting citation-format compliance.

**Sources**
- https://arxiv.org/html/2305.14627 + https://github.com/princeton-nlp/ALCE (eval.py: NLI-based citation scoring)
- https://aclanthology.org/2023.emnlp-main.398.pdf — the ~50%-unsupported finding

## 8. RAGAS metric definitions

**What it is.** RAGAS defines the field-standard reference-free RAG metrics. Faithfulness = (claims decomposed from response, verified vs retrieved context) → supported/total; answer relevancy = reverse-engineered questions compared by embedding cosine.

**Proposed contract.** No dependency — our pipeline already implements its faithfulness definition end-to-end (`claim_extractor` → `verifier_agent` → `faithfulness.score_claim` → `score_response`). Adopt only the vocabulary: report our `groundedness`/`citation` axes in the capstone with RAGAS names so reviewers recognize them. If an answer-relevancy-style axis is ever wanted, its embedding-cosine machinery already exists in `modules/embeddings.py`.

**Verdict: REJECT** the library (its metric implementations are LLM-call-driven — violates the no-extra-inference constraint and pulls a dependency chain), **ADAPT** the definitions (already aligned; rename/map in report prose only).

**Sources**
- https://arxiv.org/html/2309.15217v1 — RAGAS paper
- https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/ + …/answer_relevance/

## 9. Verbatim-quote commitment gates

**What it is.** Require the model to commit, per citation, to the verbatim quote supporting each claim; a deterministic substring/normalized-match gate verifies the quote exists *in that source* before any entailment judging. Kills fabricated quotes, frankenquotes, and misattributions for zero tokens. FRONT (ACL 2024 Findings) trains quote-first citation generation (+14.2% citation quality on ALCE); "Attribute First, then Generate" (ACL 2024) selects supporting segments before drafting; small open implementations (verbatim-citation-gate, VeriQuote) show the deterministic half is ~100 lines of regex.

**Proposed contract.** `modules/agent/nodes/draft.py` + `guardrails/groundedness.py`: extend the draft output schema so each cited sentence carries an optional `quote` field; `map_sentences` gains a normalized-substring check (quote ∈ cited chunk text) ahead of index-mapping — a sentence whose quote isn't found in its cited chunk is dropped exactly like an uncited one. For `[YOUR_RESULTS]` claims the check degenerates to "does the chunk contain this value string" — which `faithfulness._extract_key_entities` already approximates (rag.py-side).

**Verdict: ADAPT** — cheap, deterministic, orthogonal to NLI, and catches citation-fabrication classes our current citation-existence check structurally cannot see (it validates the handle, not the evidence). Gate behind eval evidence that the tier model's quote fidelity is high enough not to nuke recall — Gemma-4-class models quote poorly at 2B, so measure first on the golden set. This is the strongest *additive* candidate found in this pass after the NLI wiring itself.

**Sources**
- https://aclanthology.org/2024.findings-acl.838.pdf — FRONT, quote-grounded citations on ALCE
- https://aclanthology.org/2024.acl-long.182.pdf — Attribute First, then Generate
- https://github.com/Palo-Alto-AI-Research-Lab/verbatim-citation-gate + https://github.com/rickintoplace/veriquote/blob/main/docs/DESIGN.md — deterministic-gate reference designs

## 10. Conformal / selective abstention

**What it is.** A 2024–2026 cluster giving abstention statistical guarantees instead of vibes: conformal abstention (self-consistency + conformal prediction bounds the hallucination rate); CIC (calibration set → per-threshold confidence bound → pick the largest threshold controlling accepted-answer error at level α); COIN (FDR-controlled answer selection); CAP (RL-tuned per-instance risk levels). Clinical work (QTGuard-SCDB) shows deterministic pre-reasoning guardrails take a small RAG system to 0% unsafe where unaugmented LLMs hit 31% — and that *verbalized* model confidence is epistemically vacuous (near-constant regardless of accuracy), validating the guard's mechanical-confidence design.

**Proposed contract.** `modules/agent/guardrails/guard.py` `CONFIDENCE_THRESHOLD` + `core/config.py` `min_faithfulness_score`/`min_entailment_confidence`: adopt the CIC recipe for *choosing* constants — over the 74-case golden set (held-out split), compute each candidate threshold's accepted-answer error rate with a Clopper–Pearson upper bound, pick the largest threshold whose bound clears the target risk. No runtime machinery changes; the abstain-on-zero-survivors and threshold-abstain gates stay exactly as they are. This is a method for the eval gate, not a runtime feature.

**Verdict: ADAPT** — the runtime abstention architecture already matches the literature's safety-critical pattern (mechanical gate, abstention as first-class success, no hedging); what's missing is principled threshold selection, and calibration-set error bounds give exactly that against a corpus we already own. Full conformal machinery is REJECTed on complexity grounds for a 74-case set.

**Sources**
- https://arxiv.org/html/2405.01563v1 — conformal abstention
- https://arxiv.org/html/2607.04430v1 — CIC confidence-interval calibration
- https://ojs.aaai.org/index.php/AAAI/article/download/40667/44628 — COIN (FDR-controlled selection)
- https://proceedings.mlr.press/v304/tayebati26a.html — CAP
- https://zenodo.org/records/19432640 — QTGuard-SCDB clinical abstention/guardrail evidence
- https://www.emergentmind.com/papers/2606.19509 — verbalized confidence is vacuous on clinical structured tasks

## 11. Gemma 4 family (generation tiers)

**What it is.** Google's 2026 open-weights release: E2B (2.3B effective, +embeddings 5.1B), E4B (4.5B/8B), 12B dense, 26B-A4B MoE, 31B dense; 128K–256K context, multimodal (image+audio on E-tiers/12B), 140+ languages. Officially published QAT GGUFs (`google/gemma-4-E4B-it-qat-q4_0-gguf` etc.) preserve near-bf16 quality at Q4 — which is what `scripts/download_models.py`'s gemma4-e2b/e4b/12b tiers already reference. llama.cpp supports the family including multimodal via `libmtmd` and per-layer-embedding drafter heads (MTP speculative decoding — measured ~30 tok/s for E2B on Apple Silicon, token-identical output).

**Proposed contract.** Status quo, plus two incremental knobs: (a) pin `download_models.py` tier URLs to the official `google/*-qat-*-gguf` repos where not already done (integrity-pinned via `model_integrity.py`); (b) WATCH-item — llama.cpp MTP draft-head support for the E-tiers if assistant latency is a measured complaint (new `drafter` field in `model_selector`/`LlamaCppProvider`, not a new tier).

**Verdict: ADOPT** — already adopted; this pass confirms rather than changes it. First-party QAT GGUFs remove the quality-vs-quantization concern that normally argues against 4-bit medical text, and the E2B/E4B "effective-parameter" design is the best current fit for the 8GB tier.

**Sources**
- https://ai.google.dev/gemma/docs/core/model_card_4 — sizes/architecture/context
- https://huggingface.co/google/gemma-4-E4B-it-qat-q4_0-gguf — official QAT GGUF
- https://github.com/ggml-org/llama.cpp/blob/b8886/docs/multimodal.md — llama.cpp Gemma-4 GGUF support
- https://github.com/wiltodelta/small-llm-testing — community llama.cpp benchmark harness incl. Gemma-4 E2B tok/s + MTP

## 12. Qwen3 small dense models (4B class)

**What it is.** Apache-2.0, first-party GGUFs (`Qwen/Qwen3-4B-GGUF`), 32K native / 131K YaRN context, thinking/non-thinking switch, best-in-class multilingual and agentic/tool-calling among open 4B models; 2507 refreshes split Instruct and Thinking variants. Broadly considered the safest all-around local default in 2025–2026 community comparisons.

**Proposed contract.** `scripts/download_models.py` + `core/model_selector.py`: a challenger tier, not a replacement — `qwen3-4b-instruct` alongside `gemma4-e4b`, A/B'd through the existing eval gate (`scripts/agent_eval_gate.py`) on citation fidelity and abstention correctness before any default changes. Apache-2.0 is a distribution-license improvement over Gemma Terms if packaging (HC-M08) ever ships weights.

**Verdict: WATCH** — strongest challenger for the mid tier; the trigger to adopt is a measured Gemma-4 shortfall (citation discipline at 4B, or licensing friction), not benchmark tables. Thinking-mode output must be stripped before `validate_response` if adopted — flag for implementation.

**Sources**
- https://huggingface.co/Qwen/Qwen3-4B-GGUF — license, context, official quants, llama.cpp/ollama invocations
- https://daily.dev/blog/best-local-llm-models-run/ — 2026 local-model landscape position
- https://github.com/quantumaikr/quant.cpp/issues/68 — 3–4B-class comparison table (community)

## 13. Phi-4-mini-instruct (3.8B)

**What it is.** Microsoft, MIT license, Feb 2025, 128K context, built-in function calling. Best-in-class math/code in the 3–4B bracket (GSM8K 88.6, MATH 64.0, HumanEval 74.4) but middling knowledge scores (MMLU 67.3) and weaker instruction following — a skewed profile for a medical-knowledge companion.

**Proposed contract.** None needed — same challenger-tier slot as §12 if ever trialed.

**Verdict: REJECT** — wrong strength profile: its edge is math/code while our bottleneck is knowledge-grounded prose with strict citation discipline (MMLU/IFBench are the relevant predictors). The MIT license is the one thing it has over Gemma; insufficient alone.

**Sources**
- https://huggingface.co/microsoft/Phi-4-mini-instruct — model card + benchmarks
- https://llmlearner.com/models/phi-4-mini-instruct — independent benchmark aggregation

## 14. Vector indexing (sqlite-vec / HNSW / FAISS) vs the linear scan

**What it is.** ANN libraries (HNSW et al.) trade recall for speed at million-plus scale; sqlite-vec is the maintained successor to sqlite-vss — pure-C MIT SQLite extension doing *exact* brute-force KNN (17ms on SIFT1M's million 128-dim vectors vs FAISS-flat's 10ms). Community guidance converges: <~100k vectors → brute force is both fast enough and *exact*; ANN earns complexity only in the high-hundred-thousands+. Our scale: `rag.py:515-614` scans a per-profile corpus realistically in the hundreds-to-low-thousands of 384-dim chunks, in pure Python.

**Proposed contract.** None today — hold the 2026-07-01 decision. Documented tripwire: if a profile's chunk count exceeds ~10k or measured p95 retrieval latency breaches ~250ms, `modules/rag.py::_search_vectors_async` moves the inner loop to sqlite-vec `vec0` (still brute-force → no recall regression, no index-staleness problem) — the pure-Python loop is the bottleneck, not brute force per se. Never reintroduce FAISS or resurrect sqlite-vss (unmaintained).

**Verdict: REJECT** ANN indexing for this app; **WATCH** sqlite-vec behind the tripwire. Sources validate the survey's "no change justified" — and add that at our scale the scan's *exactness* is a feature the report can claim (no recall loss vs ANN).

**Sources**
- https://github.com/asg017/sqlite-vec + benchmarks/exhaustive-memory — brute-force-at-scale numbers
- http://alexgarcia.xyz/blog/2024/sqlite-vec-stable-release/index.html — design rationale
- https://ai-tldr.dev/learn/embeddings-vector-databases/vectors-in-production/vector-database-alternatives/ — scale thresholds
- Internal: `docs/plans/2026-06-30-tech-upgrade-survey-9-areas.md` Area 2 (prior verdict); `modules/rag.py:598`

## 15. Medical-domain and on-device embedding models

**What it is.** The 2025–2026 entrants that matter at our scale: **EmbeddingGemma** (Google, 308M, 768-dim MRL-truncatable, <200MB quantized, SOTA-under-500M MTEB, 2K context, prompt-conditioned task modes) and its official medical finetune `sentence-transformers/embeddinggemma-300m-medical` (MIRIAD; ~0.92 cosine-acc@3 on medical-paper retrieval, beats 2×-larger models); **MedEmbed** family (abhinand; clinical-IR-tuned, tops medical MTEB subsets); **NeuML/pubmedbert-base-embeddings** (768-dim, 95.62 avg vs MiniLM's 93.46 on their PubMed suite); **Qwen3-Embedding-0.6B** + **Qwen3-Reranker-0.6B** (Apache-2.0, instruction-aware, MRL dims; reranker is a cross-encoder stage over top-k).

**Proposed contract.** `modules/embeddings.py`: model name is already a constructor arg — a swap is `EmbeddingsModule(model_name="google/embeddinggemma-300m")` + `embedding_dimensions` config 384→768 + a profile-DB embedding rebuild (re-embed all chunks; no schema change needed — blobs are dimension-agnostic). The hash-fallback keeps tests offline. Medical finetune is a drop-in alternative. Reranker, if ever added, inserts between `_search_vectors_async` and `top_k` slicing — a second lazy `CrossEncoder` like §1's.

**Verdict: WATCH** — retrieval quality is not a measured complaint, and the swap costs a full per-profile re-embed plus new-model distribution plumbing (same non-GGUF gap as HC-M11). When it happens, EmbeddingGemma-300m-medical is the first prototype (on-device-designed, medical finetune exists, MRL lets us keep 384-dim rows if desired); Qwen3-Embedding-0.6B the license-cleanest alternative; the -Reranker a later precision lever, not a starting point. PubMedBERT/MedEmbed gains (~2 points) don't justify the churn at our corpus size.

**Sources**
- https://developers.googleblog.com/introducing-embeddinggemma/ + https://ai.google.dev/gemma/docs/embeddinggemma/model_card + https://arxiv.org/abs/2509.20354
- https://huggingface.co/sentence-transformers/embeddinggemma-300m-medical — MIRIAD finetune numbers
- https://huggingface.co/abhinand/MedEmbed-large-v0.1 (+ -base-v0.1) — medical IR tuning
- https://huggingface.co/NeuML/pubmedbert-base-embeddings — head-to-head vs MiniLM
- https://qwenlm.github.io/blog/qwen3-embedding/ + https://huggingface.co/Qwen/Qwen3-Embedding-0.6B — MTEB-R table incl. rerankers
- https://arxiv.org/pdf/2507.19407v1 — MEDTE medical-embedding benchmark (51 tasks)

## 16. Post-survey OCR entrants (brief)

**What it is.** Since the June-30 survey's Area 4 (which held pdfplumber+pytesseract and named docTR/PaddleOCR-lightweight as the only license-clean prototypes): **Docling** (IBM, MIT, DocLayNet layout + TableFormer table-structure models, fully local, plugin OCR backends — incl. Surya and olmOCR hooks) became the de-facto modern document-conversion stack; **Surya 2** (650M single-VLM OCR/layout/table-rec, 83.3% olmOCR-bench — but weights are modified-OpenRAIL, the survey's license blocker stands); **olmOCR** (AllenAI 7B VLM — strong accuracy, far too heavy for the edge tier).

**Proposed contract.** `modules/extract.py`: pdfplumber stays the text-layer path. If scanned-lab table accuracy is measured deficient, prototype **Docling as the OCR backend** behind the existing `is_ocr_available()`/`ocr_preference_enabled` gates and `ocr_unavailable` graceful degradation (extract.py:463-520) — MIT-clean, keeps our provenance/confidence plumbing, replaces pdf2image+pytesseract rather than adding a parallel path.

**Verdict: WATCH** — survey's "no measured deficiency → no change" still stands; Docling supersedes docTR/PaddleOCR as the first prototype candidate (better table-structure story, MIT, actively maintained, plugin architecture matches our gating). Surya remains license-blocked; olmOCR is REJECTed on size.

**Sources**
- https://arxiv.org/html/2501.17887 + https://arxiv.org/pdf/2408.09869 — Docling
- https://github.com/datalab-to/surya — Surya 2 (license caveat confirmed in Docling PR #2533 discussion)
- https://github.com/docling-project/docling/issues/1245 — olmOCR-as-backend status
- Internal: `docs/plans/2026-06-30-tech-upgrade-survey-9-areas.md` Area 4

---

## Summary verdict table

| # | Technology | Verdict | One-line why |
|---|---|---|---|
| 1 | nli-deberta-v3-xsmall cross-encoder (HC-M11) | **ADOPT** (owner-gated) | Tracker-scoped; literature-validated as the efficient faithfulness signal; regex floor stays |
| 2 | MiniCheck-FT5 / Bespoke-MiniCheck-7B | **WATCH** | Purpose-built beats generic NLI, but second non-GGUF dep; sequence behind HC-M11, decide on measured gap |
| 3 | AlignScore | **WATCH** | Best single-signal fallback if xsmall too weak and FT5 too heavy |
| 4 | Vectara HHEM-2.1-Open | **REJECT** | Redundant; redistribution license UNVERIFIED |
| 5 | LLM-as-judge | **ADAPT** | Offline calibration instrument for thresholds only — never in the request path |
| 6 | Semantic entropy / multi-pass | **WATCH** | Fills `consistency_score` properly but 3–10× cost; eval-harness viability first |
| 7 | ALCE citation metrics | **ADAPT** | Entailment-of-cited-chunk axis into `eval/scorer.py` once HC-M11 lands; benchmark itself doesn't transfer |
| 8 | RAGAS | **REJECT** (lib) / **ADAPT** (definitions) | LLM-call-driven metrics violate constraints; our axes already implement its faithfulness definition |
| 9 | Verbatim-quote commitment gate | **ADAPT** | Zero-token deterministic check catching fabrication classes citation-existence can't; needs quote-fidelity eval first |
| 10 | Conformal/selective abstention | **ADAPT** | Adopt calibration-set threshold selection (CIC-style) for gate constants; runtime machinery unchanged |
| 11 | Gemma 4 tiers | **ADOPT** (confirmed) | Official QAT GGUFs + MTP drafters; matches existing download tiers |
| 12 | Qwen3-4B | **WATCH** | Challenger tier; adopt on measured Gemma-4 shortfall or license need (Apache-2.0) |
| 13 | Phi-4-mini | **REJECT** | Math/code strength profile misses our knowledge-prose bottleneck |
| 14 | ANN indexing / sqlite-vec | **REJECT** ANN / **WATCH** sqlite-vec | Brute force is exact at our scale; sqlite-vec tripwire at ~10k chunks/profile |
| 15 | Medical/on-device embeddings | **WATCH** | EmbeddingGemma-300m-medical first prototype when retrieval is a measured complaint |
| 16 | Docling (post-survey OCR) | **WATCH** | Supersedes docTR/PaddleOCR as OCR prototype; Surya license-blocked, olmOCR too heavy |

**UNVERIFIED flags:** HHEM-2.1 redistribution terms (§4); Gemma-4 vs Qwen3-4B citation fidelity on our golden set (§11/§12 — measurable, not yet measured); small-model verbatim-quote fidelity (§9 — measurable via golden set).

## Cross-cutting note for the report

The strongest single finding of this pass: the literature (ALCE's ~50% unsupported-citation result, QTGuard's 0%-unsafe-via-deterministic-gates, vacuous-verbalized-confidence findings) converges on *mechanical enforcement over prompt-asking* — which is the architecture the guard node already implements (`map_sentences` drops, zero-survivors abstains, thresholds never hedge). The capstone can present the gap honestly: our enforcement scaffolding is state-of-the-art-shaped while two of its scoring internals (NLI entailment, consistency) remain wired-but-unfed, exactly as HC-M11 discloses.

Back to index: [README.md](README.md) · Parent: [../README.md](../README.md)
