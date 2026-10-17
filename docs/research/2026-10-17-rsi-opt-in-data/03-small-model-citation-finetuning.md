# 03: Small local models and citation-faithful medical QA (2026-10-17)

**Last Updated:** 2026-10-17

Haiku 5.5 web sweep, 2026-10-17. Markers: **[V]** fetched, **[S]** search snippet only, **[U]** unverified. Synthesis: [00-README.md](00-README.md).

**Problem it addresses.** MM-1 (TASK_LIST, 2026-10-16): with the legacy prompt, `gemma4:e4b` and `llama3.1:8b` abstained on 20/20 questions, `gemma3:12b` on 19/20 and `qwen3:8b` on 15/20. The REPORT FACTS section carried no `[cite:N]`, and the models invented ADA/AHA references.

| # | Title | Org / venue | Date | URL | Key result | Relevance |
|---|---|---|---|---|---|---|
| 1 | Enabling LLMs to Generate Text with Citations (ALCE) [V] | Princeton; EMNLP 2023 | 2023-05 | https://arxiv.org/abs/2305.14627 | A citation-generation benchmark measuring fluency, correctness and citation quality. | The eval to use for the before/after measurement. |
| 2 | Training LMs to Generate Text with Citations via Fine-grained Rewards [V] | Huang et al.; ACL 2024 | 2024-02 | https://arxiv.org/abs/2402.04315 | Prompting for citations works poorly for small models. Rejection sampling plus RL lets LLaMA-2-7B beat GPT-3.5 on ALCE. | Training beats prompting at 7B. |
| 3 | Attributed Question Answering [S] | Google Research | 2022-12 | https://arxiv.org/abs/2212.08037 | Defines the attributed QA task and its metric. | Framing. |
| 4 | Self-RAG [S] | UW / AI2 | 2023-10 | https://arxiv.org/abs/2310.11511 | Reflection tokens trained at 7B/13B improve citation accuracy. | Citation behaviour is trainable as ordinary tokens. |
| 5 | QLoRA [V] | UW (Dettmers et al.) | 2023-05 | https://arxiv.org/abs/2305.14314 | 4-bit base model plus LoRA adapters. | The basis for training on the 10 GB RTX 3080. |
| 6 | LoRA [V] | Microsoft | 2021-06 | https://arxiv.org/abs/2106.09685 | Low-rank adapters. | Background. |
| 7 | Distilling Step-by-Step! [S] | UW / Google | 2023-05 | https://arxiv.org/abs/2305.02301 | Small models trained on teacher rationales need about half the data. | Supports teacher-generated cited answers as training data. |
| 8 | Grammar-Constrained Decoding for Structured NLP Tasks without Finetuning [V] | EPFL; EMNLP 2023 | 2023-05 | https://arxiv.org/abs/2305.13971 | Grammar constraints without fine-tuning beat unconstrained decoding. | Forces the output shape. It does not check faithfulness. |
| 9 | llama.cpp GBNF grammars README [V] | ggml-org | ongoing | https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md | GBNF grammars, with a JSON Schema to GBNF converter. | Local runtime support. |
| 10 | Ollama structured outputs [V] | Ollama | 2024-12 (ongoing) | https://docs.ollama.com/capabilities/structured-outputs | A JSON schema in `format` constrains the output. | The same constraint through our default provider. Check the installed version (0.40.5). |
| 11 | BioMistral [V] | Avignon / Nantes; ACL 2024 Findings | 2024-02 | https://arxiv.org/abs/2402.10373 | Mistral 7B continued on PubMed Central. | A 7B medical base. Not evaluated for citations. |
| 12 | MEDITRON-70B [V] | EPFL | 2023-11 | https://arxiv.org/abs/2311.16079 | Llama-2 continued on PubMed and guidelines, in 7B and 70B. | A 7B medical base. Its weights may be gated. |
| 13 | MedGemma Technical Report [V] | Google | 2025-07 (rev. 2026) | https://arxiv.org/abs/2507.05201 | Gemma 3 medical models at 4B and 27B. | A 4B base that fits the 10 GB budget. |

**Gap:** no 2024-2026 paper measures fine-tuning for citation markers on medical text at 1-12B. The MM-1 script is our measurement.

## Options for the citation problem (cheapest first)

1. **Constrained decoding plus the existing faithfulness gate** (#8, #9, #10). The schema or grammar limits each sentence's cite to valid passage indices. The gate is unchanged and still checks support. Hours of work. Recommended for LEGACY-CITE-PROMPT (gate RSI-3).
2. **Two-pass prompting** (claims, then citations): a stage of option 1, not a fix on its own (#2).
3. **QLoRA on rejection-sampled, teacher-generated cited answers** (#2, #5, #7, #13), measured ALCE-style (#1). This is where the opt-in donated set (README pipeline A) is used. Training data stays local and is redacted.

Estimate (unsourced, measure it): QLoRA in 4-bit fits ≤8B with short sequences on 10 GB.
