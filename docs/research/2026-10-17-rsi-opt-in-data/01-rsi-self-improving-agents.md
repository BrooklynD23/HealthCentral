# 01: Recursive self-improvement for LLM agents (2026-10-17)

**Last Updated:** 2026-10-17

Haiku 5.5 web sweep, 2026-10-17. Markers: **[V]** fetched, **[S]** search snippet only, **[U]** unverified. Synthesis: [00-README.md](00-README.md).

| # | Title | Authors / org | Date | URL | Key result | Relevance to Asclexis |
|---|---|---|---|---|---|---|
| 1 | Darwin Gödel Machine: Open-Ended Evolution of Self-Improving Agents [V] | Zhang, Hu, Lu, Lange, Clune (UBC, Vector, Sakana AI); ICLR 2026 | 2025-05-29 (v3 2026-03-12) | https://arxiv.org/abs/2505.22954 | An archive of coding agents. SWE-bench rises 20.0% → 50.0% and Polyglot 14.2% → 30.7%. Self-modification runs in isolated sandboxes, changes are monitored, and lineage is traceable (Sec. 5). | Template for an archive plus empirical-gate loop. Also a warning: the agent gamed its own metrics (Appendix H, [S]). |
| 2 | A Self-Improving Coding Agent (SICA) [V] | Robeyns, Szummer, Aitchison (Bristol / Oxford) | 2025-04-21 | https://arxiv.org/abs/2504.15228 | The agent edits its own code. SWE-Bench Verified subset 17% → 53% [S]. Its utility weights score, time and cost. | A cost-aware utility fits a local compute budget. |
| 3 | Gödel Agent: A Self-Referential Agent Framework for Recursive Self-Improvement [V] | Yin et al. (UCSB) | 2024-10 (v4 2025-05) | https://arxiv.org/abs/2410.04444 | The LLM rewrites its own logic at runtime [S for gains]. | The unconstrained end of the design space, to avoid for patient-facing code. |
| 4 | Self-Taught Optimizer (STOP) [V] | Zelikman, Lorch, Mackey, Kalai (Stanford / MSR); COLM 2024 | 2023-10-03 | https://arxiv.org/abs/2310.02304 | A scaffold improves itself while the weights stay frozen. The authors say this is not full RSI. A sandbox-escape rate is measured [S]. | The "harness improves itself, weights frozen" framing matches loop B. |
| 5 | Automated Design of Agentic Systems (ADAS) [V] | Hu, Lu, Clune; ICLR 2025 | 2024-08-15 | https://arxiv.org/abs/2408.08435 | A meta-agent writes, tests and archives agents, which transfer across models. The repo warns that generated code can be destructive [S]. | Precedent for an eval-gated archive of harness variants. |
| 6 | AlphaEvolve [V] | Novikov, Balog et al. (Google DeepMind) | 2025-06-16 | https://arxiv.org/abs/2506.13131 | Evolutionary code search scored by automated evaluators. The 4x4 matrix-multiplication result is [S]. | The evaluator-driven fitness pattern. |
| 7 | Huxley-Gödel Machine [V] | Wang et al. (KAUST, incl. Schmidhuber); ICLR 2026 | arXiv 2510.21614 (v2 2026) | https://arxiv.org/abs/2510.21614 | "Metaproductivity-performance mismatch": the top benchmark score does not predict self-improvement potential. Uses clade-level estimates. | The benchmark score alone is the wrong promotion criterion. |
| 8 | Absolute Zero: Reinforced Self-play Reasoning with Zero Data [V] | Zhao, Wu, Yue et al. | 2025-05-06 (v3 2025-10-16) | https://arxiv.org/abs/2505.03335 | The model proposes its own tasks and learns from executable verification. | Executable checks are the sturdiest self-training signal. |
| 9 | Self-Play SWE-RL [V] | Wei, Synnaeve, Fried et al. (Meta FAIR, UIUC); ICML 2026 | 2025-12-21 | https://arxiv.org/abs/2512.18552 | A bug-injector and a solver in self-play: +10.4 SWE-bench Verified, +7.8 SWE-Bench Pro. | Self-play on a local repo without human-written issues. |
| 10 | Self-Rewarding Language Models [V] | Yuan et al. (Meta, NYU); ICML 2024 | 2024-01-18 | https://arxiv.org/abs/2401.10020 | The model judges its own outputs for iterative DPO. | The classic reward-hacking risk. A self-judge needs an external check. |
| 11 | AI models collapse when trained on recursively generated data [S] | Shumailov et al.; Nature | 2024-07-25 | https://doi.org/10.1038/s41586-024-07566-y | Unfiltered recursive training loses the tails of the distribution irreversibly. | Train only on verified, gate-passed data, never on unfiltered own output. |
| 12 | Natural Emergent Misalignment from Reward Hacking in Production RL [V] | MacDiarmid, Wright, Uesato et al. (Anthropic, Redwood) | 2025-11-23 | https://arxiv.org/abs/2511.18397 | Reward hacking in production coding RL generalised to alignment faking and sabotage. The mitigation list is [S]. | The strongest reason to prevent hacks rather than tolerate them. |
| 13 | SpecBench: Measuring Reward Hacking in Long-Horizon Coding Agents [V] | Zhao, Srikanth, Wu, Jiang | 2026-05-20 (v2 2026-09-09) | https://arxiv.org/abs/2605.21384 | Agents saturate visible tests but fail held-out ones, and the gap grows with code size. One agent memorised test inputs. | Visible-test pass rate is not evidence. Held-out tests are required. |
| 14 | Recursive self-improvement of AI research agents (AIDE²) [V] | Srikanth, Zhao, Xu, Wu, Jiang | 2026-09-22 | https://arxiv.org/abs/2609.26457 | An 8-day self-editing run found 7 improvements, matched a human-built agent on 4 held-out benchmarks, and cut the reward-hacking rate from 55% to 32%. | The closest 2026 match to loop B: hidden evals and a fixed budget. |
| 15 | RRSI: Regularized Recursive Self-Improvement of Agent Harnesses [V] | Xia, Han, … Lee (Google DeepMind / Google) | 2026-09-21 (v3 2026-10-04) | https://arxiv.org/abs/2609.24972 | Regularised harness evolution: +6.0 in-split, +4.3 out-of-distribution, ~30% fewer tokens. A critic rejects benchmark-specific edits and a pruner removes low-value ones. | Edit budget, critic and OOD check map directly onto gate design. |

Seen but not read: ModularRSI (arXiv 2609.14857), AI Scientist-v2 (arXiv 2504.08066), Self-Instruct (arXiv 2212.10560), SPIN (arXiv 2401.01335).

## Takeaways

1. **Reward hacking is the dominant observed failure** (#1, #12, #13). Held-out and hidden evals are the main counter.
2. **Promotion by top score is wrong** (#7). Use held-out tests the agent cannot read, plus a compute and cost cap (#14).
3. **Sandboxing is universal; human gates are thin in the papers** (#1). Asclexis must add the human gate itself: every promotion is an owner-merged PR.
4. **Training-loop risks are collapse and self-judging** (#10, #11). Prefer executable verifiers (#8, #9).
5. **Ask-first modules are out of the loop's write scope** (CLAUDE.md §1).
