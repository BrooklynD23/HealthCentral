# 02: Opt-in health data to fine-tuning and synthetic seeds without PHI leakage (2026-10-17)

**Last Updated:** 2026-10-17

Haiku 5.5 web sweep, 2026-10-17. Markers: **[V]** fetched, **[S]** search snippet only, **[U]** unverified. Synthesis: [00-README.md](00-README.md).

| # | Source | Date | URL | Key result | Relevance |
|---|---|---|---|---|---|
| 1 | Gerstgrasser et al. "Is Model Collapse Inevitable? Breaking the Curse of Recursion by Accumulating Real and Synthetic Data" [V] | 2024-04-01 | https://arxiv.org/abs/2404.01413 | Accumulating real and synthetic data avoids collapse; replacing real data collapses. | Mix, never replace. |
| 2 | Shumailov et al. "AI models collapse when trained on recursively generated data", Nature [S] | 2024-07 | https://doi.org/10.1038/s41586-024-07566-y | Recursive training loses the distribution tails. | The canonical collapse reference. |
| 3 | Li et al. "Memorization in Large Language Models in Medicine" [V] | 2025-09-10 | https://arxiv.org/abs/2509.08604 | Trained on 13k+ inpatient records: memorization exceeds general-domain levels, and up to 87% survives later fine-tuning. | Local fine-tuning does not remove memorization. Canary tests are required. |
| 4 | Carlini et al. "Extracting Training Data from Large Language Models" [V] | 2020-12-14 | https://arxiv.org/abs/2012.07805 | Verbatim PII extracted even from sequences seen once. | Baseline for extraction probes. |
| 5 | Abadi et al. "Deep Learning with Differential Privacy" [V] | 2016-07-01 | https://arxiv.org/abs/1607.00133 | DP-SGD at modest accuracy cost. | Foundation for local DP fine-tuning. |
| 6 | Lin et al. "DP Synthetic Data via Foundation Model APIs 1: Images" (Private Evolution) [V] | 2023-05-24 | https://arxiv.org/abs/2305.15560 | DP synthesis with API access only, no training. | Origin of the PE family. |
| 7 | Xie et al. "DP Synthetic Data via Foundation Model APIs 2: Text" (Aug-PE) [V] | 2024-03-04 | https://arxiv.org/abs/2403.01749 | DP synthetic text comparable to DP fine-tuning. | Sends seeds to an API, which conflicts with local-first (RSI-2) unless run against the local model. |
| 8 | Xu et al. "DP-RFT: … via Differentially Private Reinforcement Fine-Tuning" [V] | 2026-02-20 | https://arxiv.org/abs/2602.18633 | DP nearest-neighbour votes used as the RL reward close the PE-to-DP-fine-tuning gap; evaluated on medical abstracts. | 2026 state of the art for DP synthesis. |
| 9 | Bossy et al. "Mitigating Unintended Memorization with LoRA in Federated Learning for LLMs" [V] | 2025-02-07 (v3 2026-03-09) | https://arxiv.org/abs/2502.05087 | LoRA cuts memorization up to ~10x with performance largely kept. | Supports LoRA as the default fine-tune path. |
| 10 | Norgeot et al. "Protected Health Information filter (Philter)", npj Digit. Med. 3:57 [S] | 2020-04-14 | https://doi.org/10.1038/s41746-020-0258-y | Open-source clinical free-text de-identification (BSD-3). | Second local PHI pass after `strict` redaction. |
| 11 | Kuo et al. de-identification benchmark, UK clinical records (medRxiv; iScience 2025-12) [S] | 2025 | https://www.medrxiv.org/content/10.1101/2025.05.05.25326979 | Small open LLMs over-redact and hallucinate. | Do not use a small LLM as the redactor. Measure recall. |
| 12 | Reichert & Scheuermann "Requirements and Privacy Threats in Mobile Data Donations" (IWPE 2023) [S] | 2023 | https://eprint.iacr.org/2023/1043 | A LINDDUN threat model for data donation. Strong guarantees cost utility. | Threat model for the consent design. |
| 13 | Apple Research app privacy page [S] | current | https://www.apple.com/legal/privacy/data/en/apple-research-app/ | Per-study choice; stop at any time. | Opt-in and revocability pattern. |
| 14 | HHS OCR "Guidance Regarding Methods for De-identification of PHI" (45 CFR 164.514(b)) [S] | 2012-11 | https://www.hhs.gov/guidance/document/de-identification-guidance | Safe Harbor: 18 identifiers plus no actual knowledge. Or Expert Determination. | The legal floor (Asclexis is designed as if HIPAA applied, D10). |
| 15 | Microsoft Presidio [U content] | current | https://presidio.dataprivacystack.org/ | PII detection and anonymisation SDK. | An alternative second pass. Verify licence and features first. |

Not verified, so excluded: an Apple DP health-donation publication, DP-FedLoRA (arXiv 2509.09097), the SHIELD dataset.

## Minimum safe pipeline

Consent (#13, #12) → local `strict` redaction plus a second detector, with recall measured (#10, #11, #14) → DP mechanism kept local (#5, #9, #6-#8) → canary and extraction eval before use (#3, #4) → mix real and synthetic, never replace; re-redact anything exported (#1, #2).

## Top risks

1. **Memorization survives fine-tuning** (#3, #4).
2. **Redaction recall gaps** in free text and quasi-identifiers (#10, #11).
3. **Synthetic drift and collapse** (#1, #2).
