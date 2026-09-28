# 04 — Papers & Eval Frameworks: Scholarly Evidence Base

**Last Updated:** 2026-09-27 (scope note + two source corrections per review F-14)

> **Scope note (2026-09-27, [review follow-up F-14](../../../audit/2026-09-25/review/2026-09-27-followup.md)):** this document is a **literature and source map**, not an integration-contract document. Its 39 entries carry a "Fit for Asclexis" paragraph and a `CITE` / `ADOPT-METHOD` / `WATCH` / `SKIP` verdict; none carries a module/interface contract. `CITE` means "cite in the report", never "implement". `ADOPT-METHOD` means a method to apply to report methodology or an existing artifact, and still needs its own plan and owner sign-off before any repo change. The audit observations these papers frame (ledger M1/M2) are case studies, not measured rates.

Scouting for capstone §6 (evaluation), §7 (related work), and the methodology claims in §4–5. Every entry was located via web search on 2026-09-25; venue claims come from the indexed abstract/proceedings pages, not memory. Where a source is a vendor blog or technical report rather than peer-reviewed, that is flagged in the entry.

**Verdict legend:** `CITE` — scholarly/industry anchor to cite in the report · `ADOPT-METHOD` — their method maps onto a concrete Asclexis artifact we can strengthen or formalize · `WATCH` — relevant but immature or tangential; revisit · `SKIP` — checked, not worth report space.

---

## 1. Agentic-SWE evaluation benchmarks

### SWE-bench (Jimenez et al.)

2,294 real GitHub issue→PR task instances across 12 Python repos; a model is handed a codebase snapshot + issue text and must produce a patch verified against real tests. At publication the best model (Claude 2) solved 1.96%. Established that real-repo issue resolution is a distinct, much harder capability than code generation.

**Fit for Asclexis:** Canonical benchmark for "can an agent do real SE work" — cite in §7 as the field's reference point. Its evaluation loop (issue → patch → execute hidden tests) is structurally identical to our `feature_list.json` (machine-checked ledger items with per-item verification commands); that parallel is worth one line in §5.

**Verdict:** CITE

**Sources:** https://arxiv.org/abs/2310.06770 (ICLR 2024, oral); https://github.com/SWE-bench/SWE-bench

### SWE-bench Verified + OpenAI's retirement postmortem

OpenAI + Princeton released a 500-sample human-validated subset (Aug 2024): 93 developers screened 1,699 samples; 38.3% flagged underspecified, 61.1% flagged unfair tests; 68.3% of the original set filtered out. Then in a later postmortem OpenAI stopped evaluating on it: of audited hard-failure tasks, ≥59.4% had flawed test cases rejecting correct solutions, and every frontier model tested could reproduce gold patches verbatim — training contamination.

**Fit for Asclexis:** Two citations in one: (a) the Verified subset is the standard eval most leaderboards report; (b) the retirement post is a published instance of our core thesis — *a green signal outliving its evidentiary value*. Their "tests reject correct solutions" is the benchmark-scale version of recurring-failure #1 (the check that ran was not the check that mattered). Cite in §6 next to the fail-open gate case.

**Verdict:** CITE (both artifacts)

**Sources:** https://www.swebench.com/verified ; https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/ (OpenAI, ~2026); original announcement https://github.com/Princeton-NLP/SWE-bench (Aug 2024)

### SWE-bench Multimodal (Yang et al.)

619 task instances (17 JavaScript libraries) where problem statements/tests include images — bug screenshots, mockups, diagrams. Top SWE-bench systems resolved only ~12% (SWE-agent) vs ~6% next best; visual/front-end domains are a real generalization gap. v2 pares the set to 480 reproducible tasks.

**Fit for Asclexis:** Cite in §7 as evidence that benchmark scores don't transfer across domains — useful when hedging how much our TypeScript/React half is covered by agent competence claims. Also relevant: Asclexis ingests *image* lab reports — a visual-domain gap argument for the human-verification gate.

**Verdict:** CITE

**Sources:** https://arxiv.org/pdf/2410.03859 (ICLR 2025); https://www.swebench.com/multimodal

### The SWE-bench Illusion (Microsoft Research)

SoTA models identify the buggy file path from issue text alone at up to 76% accuracy on SWE-bench Verified vs ~53% on non-benchmark repos; ground-truth function reproduction shows up to 35% consecutive 5-gram overlap on benchmark tasks vs ~18% elsewhere. Benchmark gains partially reflect memorization, not problem-solving. A second study ("Does SWE-Bench-Verified Test Agent Ability or Model Memory?", arXiv 2512.10218) independently found Claude models ~3× better at locating files on Verified than on fresh benchmarks.

**Fit for Asclexis:** The scholarly version of our "report-as-fact" audit finding — numbers that look like capability may be recall. Cite in §6/§8 to justify why our report insists on evidence-linked claims (claims-ledger) rather than score-linked ones.

**Verdict:** CITE

**Sources:** https://arxiv.org/html/2506.12286 (NeurIPS 2025); https://www.microsoft.com/en-us/research/publication/the-swe-bench-illusion-when-state-of-the-art-llms-remember-instead-of-reason/ ; corroboration https://arxiv.org/pdf/2512.10218

### SWE-rebench (Nebius)

Automated pipeline continuously harvesting fresh GitHub issue–PR tasks (21,000+ tasks, 3,400+ repos), with LLM-driven environment extraction and quality annotation; a rotating leaderboard built on tasks postdating model training cutoffs. Shows some models' SWE-bench Verified scores are inflated by contamination.

**Fit for Asclexis:** `ADOPT-METHOD` candidate for our agent eval gate: the decontamination principle (rotate/refresh eval cases, prefer post-cutoff artifacts) applies to the 74-case `agent_eval` suite — a fixed golden set an agent has seen in-repo is itself a contamination surface. Cite in §6 as the eval-integrity counterpart to our eval docs.

**Verdict:** ADOPT-METHOD

**Sources:** https://arxiv.org/abs/2505.20411 (NeurIPS 2025 Datasets & Benchmarks); https://swe-rebench.com/ ; dataset https://huggingface.co/datasets/nebius/SWE-rebench

### Terminal-Bench 2.0

89 hard, realistic terminal tasks, each with a unique containerized environment, human-written oracle solution, and verification tests; frontier agents score <65%. Ships with the Harbor execution harness and runs as a continuous, versioned benchmark with an error-analysis methodology.

**Fit for Asclexis:** Closest published benchmark to "agent does real repo maintenance end-to-end" (what our July parallel-orchestration commits were). Their published error-analysis pass over failures is a model for how §6 should present our defect taxonomy — categories with trajectory evidence, not anecdotes. WATCH for the evolving task set.

**Verdict:** CITE (and WATCH — continuous benchmark)

**Sources:** https://arxiv.org/html/2601.11868 (ICLR 2026); https://proceedings.iclr.cc/paper_files/paper/2026/file/444a3737adaee10d86ad2ef5f74468e6-Paper-Conference.pdf ; https://github.com/harbor-framework/terminal-bench ; https://tbench.ai

### TheAgentCompany (CMU)

Self-contained simulated software company (internal web sites, docs, simulated coworkers); tasks span coding, browsing, communication. Best-tested agent completes ~30% autonomously — simple tasks tractable, long-horizon professional work not.

**Fit for Asclexis:** The honest counterweight for §1/§8 — 67% agent-authored commits does not mean agents autonomously did 67% of the *work*; cite to bound the automation claim and frame the human's orchestration role as load-bearing.

**Verdict:** CITE

**Sources:** https://arxiv.org/pdf/2412.14161 (NeurIPS 2025); https://the-agent-company.com/

### GAIA (Meta / HuggingFace / AutoGPT)

466 questions conceptually easy for humans (92% human success) but hard for agents (GPT-4 + plugins: 15%); requires reasoning, multimodality, browsing, tool use.

**Fit for Asclexis:** Peripheral — cite only if §7 needs a general-assistant benchmark anchor alongside the SWE-specific ones. Otherwise SKIP to keep §7 tight.

**Verdict:** WATCH (borderline SKIP)

**Sources:** https://arxiv.org/abs/2311.12983 (ICLR 2024)

---

## 2. Agent failure modes & reliability

### MAST — Why Do Multi-Agent LLM Systems Fail? (Cemri et al.)

First empirically grounded multi-agent failure taxonomy: 14 failure modes in 3 categories — (i) system/specification issues, (ii) inter-agent misalignment, (iii) task verification — built by grounded-theory analysis of 200+ execution traces across 7 frameworks (κ = 0.88 inter-annotator), plus MAST-Data (1,600+ annotated traces) and an LLM-judge pipeline.

**Fit for Asclexis:** THE anchor taxonomy for `docs/agentic/recurring-failures.md`. Proposed cross-walk for §6:

| recurring-failures.md # | MAST category |
|---|---|
| 1 green suite that couldn't fail | (iii) task verification — verification-quality failure |
| 2 fix creates next bug one layer over | (ii)/(iii) — error propagates through unverified handoffs |
| 3 figures asserted not measured | (iii) — claimed-vs-verified result gap |
| 4 env-dependent results as absolutes | (iii) + eval integrity — *not cleanly in MAST, candidate extension* |
| 5 gates in contaminated tree | (i) specification — environment/state assumption violated |
| 6 documented commands nobody ran | (i) — spec–execution gap |
| 7 SQL three-valued logic | out of scope (ordinary bug, not agentic) — say so explicitly |
| 8 stale guidance as authority | memory/context staleness — *candidate extension* |

Modes 4 and 8 having no clean MAST home is a *finding*, not a gap in our taxonomy — see Part-2 section.

**Verdict:** ADOPT-METHOD (cross-walk) + CITE

**Sources:** https://arxiv.org/pdf/2503.13657v2 (NeurIPS 2025 D&B); https://github.com/multi-agent-systems-failure-taxonomy/MAST

### Traverse — Locating Hidden Failures Makes Long-Horizon Agents More Reliable

2,518 real-deployment agent trajectories (SWE, computer use, science); 6,967 human-classified mistakes in 78 failure types. Signature: after its first mistake an agent rarely recovers or catches it, and the run *continues looking correct* — including runs scored "solved" that deleted data or fabricated success. A trained 4B verifier (Scout) locates first-mistake better than frontier judges.

**Fit for Asclexis:** The strongest published match for our verification-theater finding — "solved runs that fabricate success" is literally our green-suite story at trajectory level. Their "outcome ≠ process" argument is the scholarly frame for claims-ledger verdicts like CONTRADICTED. Their verifier-training result suggests future work: a small dedicated checker over our audit/eval traces.

**Verdict:** ADOPT-METHOD + CITE

**Sources:** https://arxiv.org/pdf/2609.17930v1 (arXiv, Sep 2026 — very recent; verify final venue before print). *Checked 2026-09-27: arXiv record titled "Locating Hidden Failures Makes Long-Horizon Agents More Reliable", submitted 15 Sep 2026, v1, no venue listed. The abstract names the verifier "Scout"; the label "Traverse" used as this entry's heading was not found in the abstract — confirm the paper's own name before citing it that way.*

### CCRM — Why Retrying Fails: Context Contamination in LLM Agent Pipelines

Formal model of retries where a failed attempt stays in context and elevates the per-step error rate (ε1 > ε0). Closed-form pass@K, optimal pipeline depth, and a clean-restart dominance theorem. On SWE-bench Verified the IID-retry model overestimates pass@3 by 17.4 points; fitted cascade ratio ε1/ε0 = 7.1.

**Fit for Asclexis:** Direct theoretical sibling of recurring-failure #5 (gates run in a contaminated tree): leftover state from a failed/concurrent operation corrupts the *next* signal. The published fix — clean restarts — is exactly our `git worktree` recheck; cite the correspondence in §6. Also frames why session-scoped, bounded-history subagent dispatch (our pattern) beats retry-in-place.

**Verdict:** CITE (+ ADOPT-METHOD: name the "contaminated restart" concept explicitly in recurring-failures #5)

**Sources:** https://arxiv.org/pdf/2605.08563v1 (arXiv, May 2026)

### Binding Drift in Multi-Step Tool-Augmented Agents

In multi-step workflows an entity binding made at step 1 silently drifts or propagates: an "entity lock" defense amplifies injected wrong actions 3.0× (up to 8.5× on the worst model); a cheap second-model re-verifier cuts wrong actions 79%, near an oracle bound. In natural conditions, 18% of eligible workflows drift, with per-step error *rising* across steps.

**Fit for Asclexis:** Empirical backing for our "an agent's report is a lead, not a finding" rule — the paper's evidence suggests orchestrator re-verification of subagent output is necessary, not pedantic. Cite it alongside CLAUDE.md's subagent guidance; the audit's reconciler results (M1) are a case study, not a measurement *(reworded 2026-09-27, review F-11)*.

**Verdict:** CITE

**Sources:** https://arxiv.org/pdf/2607.18316.pdf (arXiv, Jul 2026)

### Error propagation in MCP-style tool chains

First theoretical framework for error accumulation across sequential tool calls: cumulative distortion grows linearly, with martingale concentration bounds; semantic weighting cuts distortion 80%; re-grounding roughly every 9 steps controls error.

**Fit for Asclexis:** Quantitative justification for bounded session history and periodic re-grounding (our RAG pipeline re-retrieves per turn rather than trusting accumulated context). One citation suffices — overlaps conceptually with binding-drift paper.

**Verdict:** WATCH (cite if §5 discusses step budgets/re-grounding)

**Sources:** https://arxiv.org/pdf/2602.13320 (arXiv, Feb 2026)

### ParaRecover — process-level error localization/recovery benchmark

10,626 instances for multi-turn parallel tool-use; 14 error types; SDE rubric (structural integrity, diagnostic reasoning, evolutionary strategy). Evaluates whether agents can *find and fix* intermediate failures, not just whether they pass.

**Fit for Asclexis:** Adjacent to Traverse/MAST; include only if §7 needs a "process-level eval" benchmark citation. Otherwise redundant.

**Verdict:** SKIP (noted for completeness)

**Sources:** https://arxiv.org/abs/2609.12345 (arXiv, submitted 11 Sep 2026; record comment checked 2026-09-27: "Accepted to EMNLP 2026 Main Conference")

---

## 3. Context engineering, memory & orchestration

### Context Rot (Chroma technical report)

18 frontier models evaluated while holding task complexity constant and varying input length: performance degrades as input grows even on trivial tasks; distractors compound degradation; Claude models tend to abstain while GPT models hallucinate; counterintuitively a shuffled haystack beat a coherent one. Coined "context rot."

**Fit for Asclexis:** The empirical justification for the whole harness's context discipline — bounded session history in `modules/rag`, subagent context isolation, compact AGENT.md briefing over monolithic docs. Flag as vendor technical report, not peer-reviewed; pair with Lost in the Middle for a refereed anchor.

**Verdict:** CITE (with venue caveat)

**Sources:** https://www.trychroma.com/research/context-rot ; https://github.com/chroma-core/context-rot (Chroma, Jul 2025)

### Lost in the Middle (Liu et al.)

Refereed evidence that models use long context non-uniformly: U-shaped positional curve — best at beginning/end, degraded in the middle — even in explicitly long-context models.

**Fit for Asclexis:** Peer-reviewed anchor for doc-structure decisions: AGENT.md front-loads "what this is / where things live / how to verify," invariants sit in CLAUDE.md's most-read position, per-task `initial_prompt` mirroring. One line in §5.

**Verdict:** CITE

**Sources:** https://aclanthology.org/2024.tacl-1.9/ (TACL 2024); https://arxiv.org/abs/2307.03172

### A Survey of Context Engineering for LLMs (Mei et al.)

~1,300–1,400-paper survey formalizing "context engineering" as a discipline: components (retrieval/generation, processing, management) and system implementations (RAG, memory, tool-integrated reasoning, multi-agent). Notes the comprehension-vs-generation asymmetry gap.

**Fit for Asclexis:** Gives §5 a scholarly vocabulary: our constitution docs = context generation, docs_lint/link-graph = context management, per-turn retrieval = context retrieval, subagent dispatch = context isolation. Cite to position the harness as an applied instance of a named discipline rather than bespoke process.

**Verdict:** CITE

**Sources:** https://arxiv.org/html/2507.13334 (arXiv survey, Jul 2025)

### ACE — Agentic Context Engineering

Treats contexts as evolving playbooks updated incrementally; identifies *brevity bias* (summaries drop domain detail) and *context collapse* (iterative rewriting erodes knowledge) as failure modes of naive context adaptation. +10.6% on agent benchmarks; matches top AppWorld agents with a smaller model.

**Fit for Asclexis:** Names the failure mode our doc-drift findings instantiate — the 620/1160/1245 test-count drift (claims-ledger M3) is context collapse in project memory. Their fix (structured incremental deltas preserving detail) matches our practice of appending evidence rows rather than rewriting summaries. Cite + adopt vocabulary.

**Verdict:** ADOPT-METHOD (vocabulary for doc-drift entries) + CITE

**Sources:** https://arxiv.org/pdf/2510.04618.pdf (arXiv, Oct 2025)

### Cognition — "Don't Build Multi-Agents" (Walden Yan)

Position post from Devin's maker: two principles — (1) share context including full traces, (2) actions carry implicit decisions — arguing parallel sub-agents editing code produce conflicting-implicit-decision failures (the Flappy-Bird/Mario example); favor single-threaded agents + learned context compression for long tasks.

**Fit for Asclexis:** Directly relevant because this repo was largely built with Devin — this is *our* agent vendor's documented doctrine. Our contaminated-tree gate failure (#5) and parallel-`git add` sweep are the predicted conflicting-decisions failure at the file level; our resolution (sequential edits, parallel read-only audit agents, explicit pathspecs) matches their prescription. Cite in §4–6 as industry practice converging with our observed data.

**Verdict:** CITE

**Sources:** https://cognition.ai/blog/dont-build-multi-agents (Cognition, Jun 2025 — vendor blog, not peer-reviewed)

### Anthropic — effective agents + multi-agent research system + harness design (three posts)

(a) *Building effective agents*: workflow-vs-agent distinction; simplest-solution-first; cataloged patterns incl. orchestrator-workers and evaluator-optimizer. (b) *Multi-agent research system*: orchestrator-worker with isolated subagent contexts gave +90.2% on internal research eval, but ~15× tokens vs chat (4× vs single agent); token usage alone explained 80% of BrowseComp variance. (c) *Harness design for long-running apps*: context resets + structured handoff artifacts beat in-place compaction for multi-hour runs; documents "context anxiety."

**Fit for Asclexis:** Vocabulary for §4–5 (workflow vs agent; orchestrator-worker is our audit dispatch pattern; evaluator-optimizer is our eval gate's shape). The 15×-token figure is Anthropic's measurement. Cite it as such in §6, next to our audit and planning runs, which are case studies with no token or cost accounting *(reworded 2026-09-27, review F-11)*. Handoff-artifact guidance matches our `progress.md`/implementation-log/session-notes pattern.

**Verdict:** CITE

**Sources:** https://www.anthropic.com/engineering/building-effective-agents (Anthropic, Dec 2024); https://www.anthropic.com/engineering/multi-agent-research-system (Jun 2025); https://www.anthropic.com/engineering/harness-design-long-running-apps (Anthropic — vendor engineering posts)

### BenchAgent — Do More Agents Help?

Controlled, protocol-aligned evaluation: single vs fixed multi-agent vs evolving multi-agent under one normalized execution/logging protocol across 10 benchmarks. Result: at most 1 of 6 MAS configs beat the single-agent anchor (and that within noise); the rest trailed 2.56–11.29 points at higher cost. A runtime-generated Claude-Code-style workflow beat the strongest fixed-MAS baseline by ~20 points on GAIA.

**Fit for Asclexis:** The scholarly counterweight to multi-agent hype, more agents don't reliably help *generation*. Part-2 hypothesis 1 asks whether they help *verification*; our audit runs motivate that question but do not test it *(reworded 2026-09-27, review F-11)*.

**Verdict:** CITE

**Sources:** https://arxiv.org/abs/2606.05670 (arXiv, Jun 2026)

### AgentCARD — cost–accuracy frontier of role-decomposed teams

Turns existing benchmarks into role-decomposed evals (planner–executor, planner–verifier–executor) with unified cost modeling and Shapley role-criticality. Finds heterogeneous-model teams occupy the cost-accuracy Pareto frontier.

**Fit for Asclexis:** Evidence for our Phi-4-mini-tier / tier-capability workstream — assigning cheaper models to scoped roles can be Pareto-optimal rather than merely cheaper. WATCH: young paper, one venue to verify.

**Verdict:** WATCH

**Sources:** https://arxiv.org/html/2606.20629 (arXiv, Jun 2026)

### Multi-agent SE design patterns survey (Cai et al.)

Systematic study of 94 LLM-MAS-for-SE papers: 16 design patterns in 5 categories; role-based cooperation is dominant; code generation is the most common task; functional suitability is the most-attended quality attribute.

**Fit for Asclexis:** Places our orchestrator-worker + reconciler pattern inside the literature's dominant pattern family; the 16-pattern catalog gives §7 a taxonomy grid. Pair with the 124-paper ACM TOSEM survey for breadth.

**Verdict:** CITE

**Sources:** https://arxiv.org/pdf/2511.08475v1.pdf (arXiv, Nov 2025); companion survey https://dl.acm.org/doi/10.1145/3796507 (ACM TOSEM)

### SWE-agent — Agent-Computer Interfaces (Yang et al.)

Shows the *interface* between agent and environment is a first-class design variable: a purpose-built ACI (edit commands, navigation, feedback) took the same models to 12.5% SWE-bench SOTA at the time.

**Fit for Asclexis:** Scholarly license for the report's core reframe — "the harness is the deliverable." ACI :: our constitution/skills/ledger/gates as the agent↔repo interface. Cite in §5 opening.

**Verdict:** CITE

**Sources:** https://arxiv.org/abs/2405.15793 (NeurIPS 2024)

---

## 4. Human–AI teaming & the developer→orchestrator shift

### METR RCT — early-2025 AI tools on experienced OSS devs (+ 2026 follow-up)

RCT: 16 experienced OSS devs, 246 real issues on their own repos; AI-allowed tasks took **19% longer** — while devs forecast −24% before and *still believed* −20% after. Follow-up (57 devs, 800+ tasks, Aug-2025+): returning participants ~18% faster, new cohort ~4% faster, CIs crossing zero — the effect is real but evolving with tooling/practice.

**Fit for Asclexis:** Flagship citation for §4: (a) the perception–reality gap (feels faster, is slower) is exactly our verification-theater shape at the *developer* level; (b) justifies why this repo measures evidence (commits, gates, audits) instead of vibes; (c) the follow-up is the honest hedge — early-2025 results are a snapshot, cite both.

**Verdict:** CITE

**Sources:** https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/ + paper https://metr.org/Early%5F2025%5FAI%5FExperienced%5FOS%5FDevs%5FStudy-paper.pdf ; follow-up https://metr.org/blog/2026-02-24-uplift-update/ (METR, 2025–2026)

### METR — Measuring AI Ability to Complete Long Software Tasks

Defines 50%-task-completion time horizon: task duration humans need that agents complete at 50% reliability (~110 min for o3-era frontier). Horizon has doubled ~every 7 months since 2019, driven by reliability and error-recovery gains.

**Fit for Asclexis:** Frames why harness engineering mattered *when it did*: era E0–E6 spans the period where agent time-horizons crossed from minutes to hours. Also gives §8 a principled caveat — horizon numbers measure autonomous success, not our human-in-loop regime.

**Verdict:** CITE

**Sources:** https://arxiv.org/html/2503.14499v2 (NeurIPS 2025); https://metr.org/time-horizons/ (living measurements)

### GitHub Copilot controlled experiment (Peng et al.) + Google enterprise RCT

Peng: 95 devs, isolated HTTP-server task, Copilot group 55.8% faster (CI 21–89%). Google: 96 engineers, enterprise-grade task, ~21% faster with wide CI. Both show real speedups — on bounded, well-specified tasks.

**Fit for Asclexis:** Cite as a pair *with* METR: lab/isolated tasks speed up 20–55%, mature-repo real work slowed 19% — task context determines the sign. This triangulation is exactly the §8 threats-to-validity framing for our single-developer orchestration data.

**Verdict:** CITE

**Sources:** https://arxiv.org/html/2302.06590 (Peng et al., 2023); https://arxiv.org/html/2410.12944v3 (Google RCT, 2024)

### DORA 2024 — State of DevOps

>75% of respondents use AI daily; per +25% AI adoption: +individual productivity/flow/satisfaction, but −1.5% delivery throughput and **−7.2% delivery stability**. Improving process metrics did not carry through to delivery metrics.

**Fit for Asclexis:** Industry-scale (39k cumulative respondents) corroboration that AI gains don't propagate without delivery fundamentals — positions our CI gates/eval harness as the "fundamentals" layer that determines whether agent velocity becomes delivered value. Cite in §1 motivation and §6.

**Verdict:** CITE

**Sources:** https://dora.dev/research/2024/dora-report/ ; analysis https://dora.dev/ai/gen-ai-report/dora-impact-of-generative-ai-in-software-development.pdf (Google DORA, 2024)

### CoT monitoring (Baker et al., OpenAI) + monitorability fragility paper

A weaker model (GPT-4o) monitoring a stronger reasoning model's chain-of-thought catches reward hacking far better than action-only monitoring; but applying optimization pressure directly to the CoT teaches *obfuscated* hacking — a "monitorability tax." The companion position paper (arXiv 2507.11473) argues monitorability is real but fragile and must be preserved deliberately.

**Fit for Asclexis:** The supervision-of-agents anchor for §4's orchestrator role: verification needn't come from a stronger checker — our reconciler/subagent-review loops are the deployment-shaped version. The "don't optimize the channel you monitor" warning transfers: don't train/fine-tune on your own eval gate, and don't let agents edit the tests that grade them (relevant to `agent_eval` governance).

**Verdict:** CITE

**Sources:** https://arxiv.org/html/2503.11926 (arXiv, Mar 2025); https://openai.com/index/chain-of-thought-monitoring/ ; https://arxiv.org/pdf/2507.11473 (Jul 2025)

### Fully Autonomous AI Agents Should Not be Developed (Mitchell, Ghosh, Luccioni, Pistilli)

Defines five agent-autonomy levels (L0 simple processor → fully autonomous) and argues risk to people rises with ceded control; semi-autonomous systems retaining human control have the better risk-benefit profile.

**Fit for Asclexis:** Scholarly anchor for two design decisions at once: the VerificationWorkbench human gate (human stays in the observation-verification loop) and the education-only assistant (escalation to clinicians). Also a second, ethics-flavored maturity-levels precedent for the §14-style rubric.

**Verdict:** CITE

**Sources:** https://arxiv.org/html/2502.02649v1 (arXiv, Feb 2025); https://huggingface.co/papers/2502.02649

---

## 5. Medical-LLM safety evaluation (brief — supports §3, not the research thesis)

### MedQA (Jin et al.)

61k+ board-exam MCQA questions (USMLE + China + Taiwan); the reference medical-QA dataset from which most medical evals descend.

**Fit for Asclexis:** Lineage citation only — establishes the medical-eval family our 74-case behavioral gate is a domain-specific cousin of (ours tests *behavior*: cite, abstain, no dosing; not *knowledge*).

**Verdict:** CITE (one line)

**Sources:** https://arxiv.org/pdf/2009.13081 (arXiv, 2020)

### HealthBench (OpenAI + 262 physicians)

5,000 realistic multi-turn health conversations graded against 48,562 physician-written rubric criteria (Consensus + Hard subsets; o3 = 60%, Hard top = 32%). Demonstrates rubric-based open-ended eval at production scale; HealthBench Professional (arXiv 2604.27470) extends to clinician workflows.

**Fit for Asclexis:** `ADOPT-METHOD`: their per-conversation rubric-criteria grading mirrors our 6-axis eval gate; a physician-validated criteria subset is a template for any future clinical review of the abstention templates. Also cites the right thing when we say "education only" — HealthBench's rubric dimensions include instruction-following and uncertainty-handling, not just accuracy.

**Verdict:** ADOPT-METHOD + CITE

**Sources:** https://arxiv.org/pdf/2505.08775 (arXiv, May 2025); https://openai.com/index/healthbench/ ; https://github.com/openai/simple-evals

### MedAbstain / MedQAbstain — abstention under clinical uncertainty

Two convergent 2026 benchmarks (EACL + ACL): repurpose medical MCQA with explicit "I abstain" options, perturbations, and conformal prediction. Finding: SOTA models *systematically overcommit* — rarely abstain even with the question hidden; an explicit abstention option increases safer abstention more than prompting or scale.

**Fit for Asclexis:** Directly validates the abstention/escalation design in `modules/interpret*` and the guard node: overcommitment is the documented default behavior we engineer against. Cite in §3 next to the abstention-axis eval cases.

**Verdict:** CITE

**Sources:** https://aclanthology.org/2026.eacl-long.291.pdf (MedAbstain, EACL 2026); https://aclanthology.org/2026.acl-long.1365/ (MedQAbstain, ACL 2026); related selective-prediction work https://arxiv.org/abs/2603.21172v1

### ALCE — Automatic LLMs' Citation Evaluation (Gao et al.)

First benchmark for citation-grounded generation: retrieve evidence, generate answer with citations, auto-score fluency/correctness/citation quality. Even the best models lacked complete citation support ~50% of the time on ELI5.

**Fit for Asclexis:** The scholarly anchor for our citation contract (`[YOUR_RESULTS:N]`/`[REFERENCE:N]`) and claim-to-source mapping in `modules/faithfulness`: citation verification is a measured, hard capability — not a formatting nicety. Their AutoAIS-style entailment check is a candidate extension for our groundedness axis.

**Verdict:** ADOPT-METHOD (entailment-based citation check) + CITE

**Sources:** https://aclanthology.org/2023.emnlp-main.398.pdf (EMNLP 2023); https://github.com/princeton-nlp/ALCE

### RAGAS (Es et al.)

Reference-free RAG evaluation: faithfulness (claims supported by retrieved context), answer relevance, context relevance — no ground truth needed.

**Fit for Asclexis:** Vocabulary for §3/§6's groundedness axis; cite to show our eval dimensions aren't idiosyncratic — they map onto published RAG-eval dimensions (our `consistency_score` placeholder, HC-M11, is the gap they name).

**Verdict:** CITE

**Sources:** https://arxiv.org/abs/2309.15217v1 (EACL 2024 demo); https://aclanthology.org/2024.eacl-demo.16/

---

## 6. Maturity-model precedent (for the audit §14 L1–L4 rubric)

### Capability Maturity Model (Paulk, Curtis, Chrissis, Weber)

The original: five process-maturity levels (Initial → Repeatable → Defined → Managed → Optimizing), each level gated on institutionalized practices, not intentions. CMU/SEI-93-TR-024; IEEE Software 1993.

**Fit for Asclexis:** The scholarly ancestor of every L1–Ln rubric, including ours. Cite to ground the 12-capability audit table in §10: our L3→L4 verdict inherits CMM's core logic — maturity = what's *consistently enforced*, which is exactly why the fail-open gate and phantom-agent rows cap the score.

**Verdict:** CITE

**Sources:** https://www.sei.cmu.edu/library/capability-maturity-model-for-software-version-11/ (SEI TR, Feb 1993); IEEE https://psycnet.apa.org/doi/10.1109/52.219617

### Microsoft — Agentic AI Adoption Maturity Model

Five capability pillars × five levels (L100 Initial → L500), explicitly CMM-derived, aimed at enterprise agent adoption. Guidance: "be evidence-based, not aspirational," assess what's consistently true, expect uneven pillars, radar chart not single score.

**Fit for Asclexis:** Closest industry neighbor to our audit rubric — same structural DNA (pillar × level, evidence-not-aspiration). Their uneven-pillar warning literally describes our table (L4 verification vs L1 agent specialization). Cite as the commercial precedent; note ours differs by scoping to a *single repo's* harness rather than an org.

**Verdict:** CITE

**Sources:** https://learn.microsoft.com/en-us/agents/adoption-maturity-model/ + https://learn.microsoft.com/en-us/agents/adoption-maturity-model/maturity-model-how-to-use (Microsoft Learn, 2026)

### CSA — Agentic AI Governance Maturity Model (AGMM v1)

Five levels (Ad-Hoc → Optimized), CMMI-derived, mapped to CSA AI Controls Matrix, NIST CSF 2.0, ISO/IEC 42001 — governance/controls view specifically.

**Fit for Asclexis:** Governance-axis neighbor: our Guardrails row (L3 — invariants + protected files + evals, no hooks, fail-open gate) maps onto their controls frame. Cite in §3/§10 when discussing why a *governance* lens catches what a capability lens misses (the gate existed; it couldn't fail — a controls-maturity issue).

**Verdict:** WATCH→CITE (one row of the related-work table)

**Sources:** https://labs.cloudsecurityalliance.org/agentic/agentic-governance-maturity-model-v1/ (Cloud Security Alliance, 2026)

### Salesforce Agentic Maturity Model

Four levels (info retrieval → single-domain orchestration → multi-domain orchestration → agent-first), marketing-oriented.

**Fit for Asclexis:** Weakest of the three neighbors — vendor positioning, thin criteria. Name-check only if §7 tabulates industry models.

**Verdict:** SKIP (noted for completeness)

**Sources:** https://www.salesforce.com/eu/blog/agentic-maturity/ (Salesforce blog, 2026)

---

## Part-2 material — where our data could EXTEND or CONTRADICT published findings

These are candidate original contributions, not citations. Each pairs a published claim with evidence this repo already holds.

1. **"More agents don't help" — except for verification.** BenchAgent (2606.05670) and Cognition's post show multi-agent *generation* underperforms or conflicts. Our case observations (claims-ledger M1, `CASE-STUDY`): a reconciler caught 3 errors in sibling agents' output, and a later planning pass caught 4 errors in the audit. There was no single-agent comparison, no seeded errors, and no denominator, so these motivate the hypothesis rather than support it *(reworded 2026-09-27, review F-11)*. Hypothesis worth writing up: parallel agents help on the **verification/review axis** (read-only, independent contexts) while hurting on the **editing axis** (shared mutable state). Refines both papers.

2. **Contaminated restarts at the harness level.** CCRM (2605.08563) formalizes retry contamination *inside a context window* (ε1/ε0 = 7.1). Our recurring-failure #5 is the same phenomenon one level up: a *git tree* contaminated by concurrent agent work made a freshness gate report the opposite of CI. Candidate extension: treat the working tree + doc set as the "context" — the model generalizes.

3. **Context collapse in project memory, not just model memory.** ACE (2510.04618) documents brevity-bias/context-collapse for agent contexts; our evidence (claims-ledger M3: test counts of 620/1160/1245 across three docs; recurring-failure #8 stale-authority) is context collapse in *persistent project documentation* — an organizational-scale analog with CI-checkable countermeasures (docs_lint) that the ACE paper doesn't consider.

4. **Fabricated success under green outcomes.** Traverse (2609.17930) reports solved runs that deleted data or fabricated success at trajectory level. Our restore-400s-under-green-suite and credential-leak-past-assertion cases are the same phenomenon at *test-harness* level: the artifact *asserted* a check the check couldn't perform. Our claims-ledger + route_client mitigations extend their verifier idea into CI.

5. **The perceived-speedup gap in an orchestrator, not an implementer.** METR measured *developers implementing* with AI (−19% time, +20–24% perceived). Our project is a different population cell: one human *orchestrating* agents (67% agent-authored commits) — velocity claims there are unmeasured too, but the repo's commit/audit artifacts make this measurable in a way METR's screen-recording study couldn't. Part-2 could design a measurement of throughput-per-era and review defect-capture. That rate does not exist yet: the audit has no denominator. With a proper protocol it could become an orchestration-regime data point *(reworded 2026-09-27, review F-11)*.

6. **Maturity models measure gates, not prose.** Microsoft/CMM lineage says "evidence-based, not aspirational" but doesn't operationalize *how*. Our repo demonstrates the failure when it isn't (phantom `.claude/agents/` layer — claimed capability at level-zero evidence) and the fix (feature_list.json verification commands per item). Candidate extension: an "evidence-attachment" requirement inside maturity rubrics.

7. **Benchmarks rot; so do eval docs.** SWE-bench Illusion / Verified retirement / SWE-rebench document contamination and flawed-oracle decay in *benchmarks*. Our evals.md test-count drift and environment-dependent baselines (recurring-failure #4) show the same rot in a *project-internal* eval suite — the problem is not just upstream datasets.

---

## Summary table

| # | Paper / framework | Cluster | Venue / year | Verdict | Primary report use |
|---|---|---|---|---|---|
| 1 | SWE-bench | Benchmarks | ICLR 2024 | CITE | §7 baseline; ledger-loop parallel |
| 2 | SWE-bench Verified + retirement post | Benchmarks | OpenAI 2024/2026 | CITE | §6 green-signal decay |
| 3 | SWE-bench Multimodal | Benchmarks | ICLR 2025 | CITE | §7 generalization gap |
| 4 | SWE-bench Illusion | Benchmarks | NeurIPS 2025 | CITE | §6 memorization-vs-skill |
| 5 | SWE-rebench | Benchmarks | NeurIPS 2025 D&B | ADOPT-METHOD | eval freshness for agent_eval |
| 6 | Terminal-Bench 2.0 | Benchmarks | ICLR 2026 | CITE/WATCH | §6 error-analysis model |
| 7 | TheAgentCompany | Benchmarks | NeurIPS 2025 | CITE | §8 autonomy bound |
| 8 | GAIA | Benchmarks | ICLR 2024 | WATCH | optional §7 anchor |
| 9 | MAST failure taxonomy | Failure modes | NeurIPS 2025 | ADOPT-METHOD | recurring-failures cross-walk |
| 10 | Traverse hidden-failures | Failure modes | arXiv Sep 2026 | ADOPT-METHOD | verification-theater anchor |
| 11 | CCRM contaminated retries | Failure modes | arXiv May 2026 | CITE | recurring-failure #5 theory |
| 12 | Binding drift | Failure modes | arXiv Jul 2026 | CITE | subagent-lead verification rule |
| 13 | MCP error propagation | Failure modes | arXiv Feb 2026 | WATCH | step-budget justification |
| 14 | ParaRecover | Failure modes | arXiv Sep 2026; accepted EMNLP 2026 Main (per arXiv comment) | SKIP | redundant w/ MAST/Traverse |
| 15 | Context Rot | Context | Chroma Jul 2025 | CITE | bounded-context rationale |
| 16 | Lost in the Middle | Context | TACL 2024 | CITE | doc-structure evidence |
| 17 | Context-engineering survey | Context | arXiv Jul 2025 | CITE | §5 vocabulary |
| 18 | ACE playbooks | Context | arXiv Oct 2025 | ADOPT-METHOD | doc-drift vocabulary |
| 19 | Cognition Don't-Build-MAS | Orchestration | Cognition Jun 2025 | CITE | §4–6 conflicted-decisions |
| 20 | Anthropic 3 posts | Orchestration | Anthropic 2024–26 | CITE | §4–6 patterns + token economics |
| 21 | BenchAgent | Orchestration | arXiv Jun 2026 | CITE | multi-agent economics §6 |
| 22 | AgentCARD | Orchestration | arXiv Jun 2026 | WATCH | model-tier frontier |
| 23 | MAS-SE surveys (2) | Orchestration | arXiv 2025 / TOSEM | CITE | §7 pattern taxonomy |
| 24 | SWE-agent ACI | Harness | NeurIPS 2024 | CITE | "harness is deliverable" frame |
| 25 | METR RCT + follow-up | Human-AI | METR 2025–26 | CITE | §4 perception gap |
| 26 | METR time horizons | Human-AI | NeurIPS 2025 | CITE | §4 era framing |
| 27 | Copilot + Google RCTs | Human-AI | arXiv 2023/2024 | CITE | §8 task-context triangulation |
| 28 | DORA 2024 | Human-AI | Google 2024 | CITE | §1/§6 delivery fundamentals |
| 29 | CoT monitoring ×2 | Human-AI | arXiv 2025 | CITE | supervision-of-agents |
| 30 | Fully-autonomous-agents position | Human-AI | arXiv 2025 | CITE | human-in-loop rationale |
| 31 | MedQA | Medical | arXiv 2020 | CITE | eval lineage (1 line) |
| 32 | HealthBench | Medical | arXiv 2025 | ADOPT-METHOD | rubric-criteria grading |
| 33 | MedAbstain + MedQAbstain | Medical | EACL/ACL 2026 | CITE | abstention-axis validation |
| 34 | ALCE | Medical/citation | EMNLP 2023 | ADOPT-METHOD | citation-contract anchor |
| 35 | RAGAS | Medical/RAG | EACL 2024 | CITE | groundedness vocabulary |
| 36 | CMM (Paulk 1993) | Maturity | SEI/IEEE 1993 | CITE | §10 rubric lineage |
| 37 | Microsoft adoption model | Maturity | MS Learn 2026 | CITE | nearest industry neighbor |
| 38 | CSA AGMM | Maturity | CSA 2026 | WATCH→CITE | governance lens |
| 39 | Salesforce model | Maturity | Salesforce 2026 | SKIP | completeness only |

Back to index: [../README.md](../README.md)
