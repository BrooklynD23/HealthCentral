# 04: RSI-enabled harness engineering (2026-10-17)

**Last Updated:** 2026-10-17

Haiku 5.5 web sweep, 2026-10-17. Markers: **[V]** fetched, **[S]** search snippet only, **[U]** unverified. Synthesis: [00-README.md](00-README.md). Relevance letters: **S** = the session-log hook (#68), **G** = golden sets and CI eval gates, **M** = the multi-agent build workflows (`.claude/workflows/`).

| # | Title | Org / authors | Date | URL | Key result | Relevance |
|---|---|---|---|---|---|---|
| 1 | Building effective agents [V] | Anthropic | 2024-12-19 | https://www.anthropic.com/engineering/building-effective-agents | Workflows vs agents; start simple; orchestrator-workers and evaluator-optimizer patterns. | M: the Opus-plans / Sonnet-implements split. |
| 2 | Effective context engineering for AI agents [V] | Anthropic | 2025-09-29 | https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents | Compaction, notes kept outside the context window, subagents returning condensed results. | S, M. |
| 3 | Demystifying evals for AI agents [V] | Anthropic | 2026-01-09 | https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents | Code graders are cheap but brittle; model graders need calibration; capability vs regression evals; pass^k. | G. |
| 4 | Claude Code hooks reference [V, page truncated] | Anthropic | current | https://code.claude.com/docs/en/hooks | SessionEnd can only observe; Stop can block. | S: keep the log hook observe-only. |
| 5 | Large Language Models as Optimizers (OPRO) [S] | Google DeepMind; ICLR 2024 | 2023-09 | https://arxiv.org/abs/2309.03409 | Prompt search from past scored candidates. | A baseline. |
| 6 | MIPRO: Optimizing Instructions and Demonstrations for Multi-Stage LM Programs [V] | Opsahl-Ong et al.; EMNLP 2024 | 2024-06 | https://arxiv.org/abs/2406.11695 | Per-module instruction and demo optimisation from traces. A separate MIPROv2 paper was not verified. | S, G. |
| 7 | GEPA: Reflective Prompt Evolution Can Outperform RL [V] | Agrawal, Khattab et al.; ICLR 2026 oral | 2025-07 (v2 2026-02-14) | https://arxiv.org/abs/2507.19457 | Natural-language reflection on trajectories with a Pareto frontier: +6% over GRPO with up to 35x fewer rollouts; +10% over MIPROv2. Figures differ across versions. | S: the most direct method for mining logged runs. |
| 8 | TextGrad, Nature 639 [S] | Yuksekgonul et al. | 2025-03-20 | https://doi.org/10.1038/s41586-025-08661-4 | Textual feedback "backpropagated" through compound systems. | Moderate fit. |
| 9 | Darwin Gödel Machine [V] | Zhang, Hu, Lu, Lange, Clune; ICLR 2026 | 2025-05 (v3 2026-03) | https://arxiv.org/abs/2505.22954 | Archive, self-edit, benchmark gate. | G, M: closest prior art. |
| 10 | Meta-Harness: End-to-End Optimization of Model Harnesses [V] | Lee, Nair, Zhang, Lee, Khattab, Finn | 2026-03-30 | https://arxiv.org/abs/2603.28052 | The proposer reads the full code, scores and traces of past candidates from disk: +7.7 points with 4x fewer context tokens. | Highest fit: harness-as-code with traces on disk. |
| 11 | Recursive self-improvement of AI research agents (AIDE²) [V] | Srikanth et al. | 2026-09-22 | https://arxiv.org/abs/2609.26457 | Held-out transfer; reward-hacking rate 55% → 32% on a held-out family. | G: measure hacking on held-out task families. |
| 12 | EvilGenie: A Reward Hacking Benchmark [S] | authors unverified | 2025-11 (rev. 2026-05) | https://arxiv.org/abs/2511.21654 | Held-out tests, LLM judge and detection of test-file edits. | G: block test-file edits as a cheap gate. |
| 13 | A Survey on LLM-as-a-Judge [S] | Gu et al. | 2024-11 | https://arxiv.org/abs/2411.15594 | Judge consistency and bias. | G. |
| 14 | Reliability without Validity (judge audit) [S] | Norman, Rivera, Hughes | 2026-06 | https://arxiv.org/abs/2606.19544 | Test-retest above 0.95 coexists with position bias above 0.10; rankings shift by up to 14 places. Provisional. | G: audit any judge against a sealed set. |
| 15 | A Practical Guide to Building Agents [U content] | OpenAI | n/a | https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf | The URL resolves; the text was unreadable. | Cite as "URL resolves" only. |

Dropped as unverifiable: Agent SDK hook-event claims from third-party pages, the SpecBench growth figure from this sweep (see [01](01-rsi-self-improving-agents.md) #13 for the verified abstract), and an "ExploitGym" incident.

## RSI loop for the Asclexis harness

1. **Log**: #68's hook, observe-only (#4). Full traces (#10). Redacted before mining (CLAUDE.md redaction invariant).
2. **Mine**: GEPA-style reflections, keeping a Pareto set (#7). Code graders first; calibrate judges against a sealed set (#3, #13, #14).
3. **Propose**: small harness-code edits; the archive of candidates on disk (#10, #9). No new layers (CLAUDE.md §2).
4. **Sealed-eval gate**: the regression gates already in CI plus a held-out sealed set (OW-3 / S5), pass^k (#3), test-file-edit and hack-rate checks (#11, #12).
5. **Human gate**: an owner-merged PR. Ask-first modules are excluded (CLAUDE.md §1).
6. **Merge + re-gate**: keep rejected candidates for lineage (#9) and re-run held-out gates after merge (#11).

**Repo caveat:** session logs can hold patient data, so mining runs locally on redacted traces only. A cloud optimiser would break local-first and the redaction invariant.
