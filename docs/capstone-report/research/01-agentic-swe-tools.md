# Research 01 — Agentic Software-Engineering Tools

**Last Updated:** 2026-09-27 (Laya claims corrected per review F-09)

Scouting survey for the capstone report's Related Work section (outline §7) and the
project roadmap. Scope: commercial agentic coders, open-source counterparts, and —
the point of the exercise — what each one's architecture would concretely mean
inside this repo's harness (CLAUDE.md constitution, 18 skills, `feature_list.json`
ledger, `route_client`, eval gates, `recurring-failures.md`, the `modules/agent`
plan→act→reflect→draft→guard graph with its 8 read-only tools).

> **Ambiguity-resolution note (honest read of the request).** The owner asked for
> "Jev & their open-source counter Layla (or something on Github)". Both names were
> uncertain. What actually exists:
>
> - **"Jev" is real and is not a coding agent.** Jev is TypeSafe AI's hosted
>   "System One" *decision model* — launched **2026-09-15**, ten days before this
>   writing — that returns typed Choice/Score/Noul answers with calibrated
>   probabilities instead of generating text. It is marketed *to* agentic-SWE
>   systems (it ships agent skills for Claude Code/Codex/Cursor and a reference
>   Rust coding-agent harness, `jevdev`), which is almost certainly how the owner
>   encountered it — the launch went viral on X within the last week.
> - **"Layla" is almost certainly Laya** (ConvAI Innovations) — the flagship
>   open-weights (Apache-2.0) Jev counterpart, released **2026-09-18**, three days
>   after Jev. Same `/v1/systemone` wire shape, ~19.8k GitHub stars within a week.
>   A real "Layla" does exist on GitHub (`l3utterfly` — a local-LLM chat app with a
>   WebRTC `llama-server` wrapper) but it is a consumer chat product, not a Jev
>   counterpart; it does not fit "open-source counter to Jev" in any dimension.
> - **Fallback interpretation covered anyway:** the other plausible reading —
>   Devin (Cognition's commercial agent) vs. open-source "Devin clones" — is also
>   covered below (Devika, OpenHands). If the owner meant that pair, §Devin and
>   §Dormant-and-cautionary have it; the Jev→Laya mapping is judged the closer one
>   because it matches "commercial X and its open-source counter" exactly, and it
>   is the pair that is *news right now*.
>
> **RESOLVED 2026-09-26 (owner-confirmed):** the intended pair is **Jev → Laya**.
> Owner rationale: Laya is open-weights (Apache-2.0), so the project pays no
> commercial licensing — the budget constraint that also drives the local-first
> stack. The Devin/Devika material below stays as secondary landscape coverage
> (useful for the dormancy/supply-chain argument), but Related Work anchors on
> Jev↔Laya.

Constraint applied throughout: **this repo is local-first — no network calls in
product code paths.** Any tool that requires a cloud API is reference-only
material for the report, and its contract says so explicitly.

---

## Jev (TypeSafe AI) — the named "commercial"

Hosted decision-model API (`POST /v1/systemone`), not a code generator. You send
state plus typed questions — `Choice` (pick one of N options), `Score` (ordinal
rating), `Noul` (calibrated yes/no probability) — and get structured answers with
per-option probabilities in ~70–500 ms (independent p50 measurement: 236–276 ms
end-to-end). $0.042/M input tokens, output free, 64k-token combined request
budget, up to 255 options per Choice. Proprietary; weights not released; claims a
novel architecture + "RLCD" (Reinforcement Learning for Calibrated Decisions)
post-training, undisclosed internals. Ships a `jevdev` Rust coding-agent harness
(state as typed content-addressed chunks, Cedar policy gate, per-turn decision
points delegated to Jev: context visibility, tool routing, permission allow/ask/deny)
and official agent skills that teach Claude Code/Codex/Cursor when to call it.
The emerging pattern is "Jev Engineering": an LLM writes, Jev decides, code acts.

- **Proposed contract:** *none for product paths* — it is a network call to a
  proprietary API; adoption in `modules/agent` would break the local-first
  invariant outright. The transferable pattern is the *interface*, not the
  service: replace free-text judgments inside the agent graph with typed,
  bounded, probability-carrying questions. Candidate touchpoints if a local
  equivalent is ever wanted: `modules/agent/guardrails` advice classification
  (currently shared `classify_advice` on input + draft), the `plan`/`reflect`
  routing decision in `graph.py`, and confidence gating — all are finite
  answer-set judgments we currently pay an LLM call (or regex) for. Jev itself:
  reference-only.
- **Owner note (2026-09-26):** Jev is out entirely — owner selected Laya as the
  free/open-weights replacement. Jev remains in this doc only as the named
  commercial reference point for Related Work.
- **Verdict:** **REJECT** (as a dependency — cloud API violates the hard
  local-first invariant); the typed-decision *pattern* is worth tracking via its
  open counterpart below. Ten days old; every claim about accuracy/calibration
  originates with the vendor or week-old third parties — treat as unproven.
- **Sources:**
  - https://thejevai.com/docs (official docs; typed-question API, agent-skill install)
  - https://jevtypesafeai.com/integrations/claude-code (decision primitives: Choice/Score/Noul, gate-a-tool-call use case)
  - https://docs.rs/jevdev/latest/jevdev/ (Rust harness: typed state chunks, Jev-answered decision points, Cedar policy)
  - https://madewithjev.com/what-is-jev-engineering (the "LLM writes / Jev decides / code acts" pattern; launch timeline)
  - https://supercode.sh/en/blog/guides/jev-for-coding-agents (third-party framing: Jev beside Codex, not in its chair)

## Laya (ConvAI Innovations) — the open-source counter ("Layla")

Open-weights Apache-2.0 System-1 decision-model family — the most-liked open
response to Jev (~19.8k stars within days of its 2026-09-18 release). Three
checkpoints on HF (`convaiinnovations/laya`): English `ModernBERT-large` 421M
(ctx 512), multilingual `mmBERT-base` 322M (ctx 1,024, 100+ languages), and
`laya-typed-decisions` 421M (ctx 1,024; 0.766 acc on the typed-decisions bench —
*corrected 2026-09-27: per the model card, 0.766 belongs to the checkpoint fine-tuned on
that benchmark's own training split; the zero-shot base scores 0.362, below the 0.461
majority-class baseline. Laya is "a fast base to specialise, not a zero-shot decision engine"*).
Non-autoregressive: one forward pass, ~33–40 ms on a T4, no text generation.
`pip install laya`, runs fully in-process/self-hosted; an independent hosted
option (Laya Studio, Switzerland) exists but is unnecessary — weights are yours.
Speaks the same `/v1/systemone` wire shape, so code written for Jev can run
against it by changing URL+key. Published head-to-head vs Jev: Laya wins on
latency and some classification suites (AG News 0.950 vs 0.910); Jev wins
decisively on many-option choice (Banking77 0.870 vs 0.425 — keep Laya choices
under ~20 options) and long inputs (32k vs 512–1,024 tokens). Calibration: ECE
0.081 after temperature refit (0.466 as shipped).
Also in the post-Jev wave, for completeness: `SemIf` (MIT, runs on llama.cpp/
WebGPU), `Kev` (Apache-2.0, Qwen3.5 0.8B–9B), `Open-Jev` (MIT, 2B–27B),
`open-alternative-jev` (Apache-2.0, any ChatML model via HF/vLLM), `jevper`
(Jev-shaped wrapper over any OpenAI-compatible server incl. self-hosted
llama.cpp). A tracker listed 33 entries by 2026-09-23 — the space is 8 days old
and churning.

- **Proposed contract:** `modules/agent/guardrails` + `core/llm` — *if* a future
  profiling pass shows the advice classifier or plan/reflect routing burning
  model latency on bounded judgments, a Laya-class encoder could serve as a
  local, in-process decision head behind a thin adapter (same typed-question
  interface, `noul` for "does this draft contain advice?", `choice` for tool
  routing among our 8 read-only tools — under the ~20-option ceiling). It is
  Apache-2.0 and local, so it *can* enter product paths — but any swap of a
  guardrails component is a CLAUDE.md ask-first change, and a week-old model is
  not what you put in front of a medical-safety gate today.
- **Hardware check (owner-requested, 2026-09-26 — corrected 2026-09-27, [review F-09](../../../audit/2026-09-25/review/2026-09-27-followup.md)):**
  *vendor-reported, not measured on Asclexis hardware.* 421M params ≈ ~808 MB English weights
  (`allow_patterns` pulls only the checkpoint needed); non-autoregressive =
  one forward pass, no KV cache growth; `torch>=2.0` + `transformers>=4.45`
  (already in our dep tree via sentence-transformers). The model card (published
  by ConvAI, the vendor) reports GPU latency (32.8 ms) and CPU latency (193–464 ms),
  CUDA usage with CPU fallback, and "about 1.7 s on an Apple GPU" for a 4,000-token
  input; it does **not** mention MPS by name. The 33–40 ms T4 figure is the vendor's,
  not an independent benchmark. The earlier "runs at every hardware level" claim is
  **withdrawn** until latency and accuracy are measured on Asclexis tasks and the
  owner's actual target machines. No GGUF needed — it's a HF checkpoint, same distribution
  path as the planned HC-M11 NLI model.
- **Owner note (2026-09-26):** Laya **replaces** Jev in the evaluation — open
  weights, zero license cost, on-device. Its candidate role here is a local
  decision head (advice-classification, tool routing, possibly entailment-style
  judgments overlapping HC-M11), not a generative model — the GGUF chat tiers
  stay as-is.
- **Verdict:** **WATCH→candidate** — the only open-weight entrant that fits
  local-first cleanly and now the owner's chosen path for the decision-model
  role. Still hold adoption until (a) advice-classifier latency/accuracy is a
  measured bottleneck, and (b) it survives scrutiny past the launch window —
  it is days old. For the report it's a primary Related-Work anchor.
- **Sources:**
  - https://huggingface.co/convaiinnovations/laya (model card: architecture, RLCD, calibration temps, Apache-2.0)
  - https://laya.studio/compare/laya-vs-jev (head-to-head with "where Jev wins" tables; reachable 2026-09-27. Its footer says it is not affiliated with ConvAI or TypeSafe, but it sells hosted Laya, so it is not a neutral evaluator. The model card itself says Jev figures are "third-party published, never measured here".)
  - https://laya.convaiinnovations.com/ (founder writeup: three checkpoints, latency, language coverage)
  - https://pypi.org/project/laya/ (package, license, install surface)
  - https://decisioneval.dev/alternatives/typesafe-jev/ (tracker of open alternatives; measured-vs-unmeasured gaps)
  - https://stackness.dev/blog/open-source-alternatives-to-jev-and-what-each-one-actually-replaces (taxonomy of the 33-entry wave)

## Devin (Cognition) — commercial flagship

The tool the whole category is named after — and, disclosure-relevant, the class
of agent that authored ~67% of this repo. Architecture is a two-part split: a
stateless cloud **Brain** (planning/reasoning, always in Cognition's cloud) plus a
sandboxed **Devbox** VM per session carrying shell, code editor, and browser —
"everything a human would need." Long-horizon planning over thousands of
decisions, real-time progress reporting, user collaboration mid-task; SWE-bench
was its launch benchmark. Enterprise variants move the Devbox into customer VPCs;
**Devin Outposts** (2026) run sessions on customer machines/K8s behind a named
queue. Cognition acquired Windsurf: the IDE is being renamed **Devin Desktop**, an
"agent command center" (Spaces, kanban, multi-agent management via ACP) on top of
the Windsurf editor.

- **Proposed contract:** *none — reference only.* Closed, cloud-resident Brain;
  even Outposts keeps the brain in Cognition's cloud. Its harness-relevant
  exports to this project are conceptual and already partially landed: the
  Brain/Devbox split ≈ our feature-code/sandbox separation of concerns;
  session-reporting ≈ our `audit.emit_audit_event` per node; the Devin Desktop
  "manage a fleet of agents" posture ≈ the developer→orchestrator shift the
  capstone studies. Cite it in Related Work as the category archetype and as the
  authorship-disclosure anchor.
- **Verdict:** **REJECT** (adoption — closed/cloud/expensive, violates
  local-first); **primary reference** for the report.
- **Sources:**
  - https://cognition.com/blog/introducing-devin (launch post: planning claim, sandboxed shell/editor/browser)
  - https://docs.devin.ai/enterprise/deployment/overview (Brain/Devbox split, deployment models)
  - https://devin.ai/blog/introducing-devin-outposts (self-hosted execution plane behind queues)
  - https://beta.codeium.com/cascade (Devin Desktop, ex-Windsurf: multi-agent command center, ACP)

## Google Jules — commercial async agent

Google Labs' asynchronous coding agent: clones your GitHub repo into a secure
cloud VM (preconfigured Node/Python/Rust/Bun image), plans with Gemini 2.5/3 Pro,
executes unattended, and returns plan + reasoning + diff → PR. Async-first:
approve the plan, walk away, review the diff. Entry points: web UI, `jules` issue
label, Jules Tools CLI, `jules-action` GitHub Action (cron-triggered agent tasks),
and `jules-sdk` for fleets (`jules.all()` — Promise.all over agent sessions with
concurrency control). Free tier (15 tasks/day, 3 concurrent); data isolated in
the execution environment, no training on private code.

- **Proposed contract:** *none — cloud-only, reference only.* The transferable
  pattern is the **plan-approval gate before execution**: Jules shows its plan
  and waits — the same shape as our VerificationWorkbench (machine-extracted
  data, human verifies before it becomes truth) and a defensible citation for
  "human checkpoint inside the autonomous loop" as industry practice rather than
  our invention. Fleet-of-sessions SDK is a Related Work data point for the
  orchestrator-shift argument.
- **Verdict:** **REJECT** (adoption — every session ships the repo to Google's
  cloud); cite for async plan→approve→diff workflow.
- **Sources:**
  - https://blog.google/innovation-and-ai/models-and-research/google-labs/jules/ (public beta announcement: async, cloud VM, private-by-default)
  - https://jules.google/ (product: plan approval, diff, PR; tiers/concurrency)
  - https://developers.googleblog.com/meet-jules-tools-a-command-line-companion-for-googles-async-coding-agent/ (CLI, scriptable composition)
  - https://github.com/google-labs-code/jules-sdk/ (fleet orchestration SDK)
  - https://github.com/google-labs-code/jules-action (agent-in-CI: cron security scans → PRs)

## GitHub Copilot coding agent — commercial, governance-forward

GitHub's integrated SWE agent: assign an issue (or prompt) → spins an ephemeral
GitHub Actions-powered dev environment (customizable via
`.github/workflows/copilot-setup-steps.yml`) → researches, plans, edits on a
branch → PR. The interesting part is its **permission architecture**: pushes only
to `copilot/*` branches it created, cannot approve/merge its own PRs, CI doesn't
run without human approval, commits co-authored for traceability, restricted
internet, dedicated `Agents` secrets scope isolated from Actions secrets. A
capability-scoped agent operating under org branch protections — least-privilege
as default, not opt-in.

- **Proposed contract:** *reference only* (hosted; requires GitHub cloud).
  Transferable: **capability-scoped writes as a default posture.** We already
  enforce the mirror image — `modules/agent/tools/registry.py` holds only
  read-only tools and a test asserts no write path exists (invariant SG-6).
  Copilot's version adds *scoped* writes with forced review. If the product agent
  ever gains any write (e.g., annotation suggestions), the Copilot pattern —
  write to a namespace only the agent can touch + mandatory human merge — is the
  shape to copy, gated by `route_client` HTTP tests for the auth path.
- **Verdict:** **REJECT** (adoption — cloud); **ADOPT its permission-scoping
  pattern** conceptually if agent write access is ever scoped in a roadmap item.
- **Sources:**
  - https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-cloud-agent (ephemeral Actions environment, plan→branch→PR)
  - https://github.blog/ai-and-ml/github-copilot/github-copilot-coding-agent-101-getting-started-with-agentic-workflows-on-github/ (security model: branch scoping, forced human review)
  - https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/configure-secrets-and-variables (isolated `Agents` secrets scope)
  - https://github.com/github/docs/blob/main/content/copilot/how-tos/use-copilot-agents/coding-agent/customize-the-agent-environment.md (`copilot-setup-steps.yml` env contract)

## Claude Code — commercial CLI agent; also this repo's actual harness

Anthropic's terminal-native agent — and almost certainly one of the tools in this
repo's own authorship mix (the `.claude/` tree, skills, and CLAUDE.md hooks
infrastructure assume it). Architecture of note: **lifecycle hooks**
(`SessionStart`, `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Stop`… — shell
commands, HTTP endpoints, or LLM prompts that can block/modify behavior),
**subagents** with isolated context windows, per-agent tool restrictions, model
caps, `worktree` isolation, and background execution; **plugins** bundling
skills/agents/hooks/MCP; permission modes. The pattern that matters for Related
Work: the harness is *configurable file-system state* — markdown agents in
`.claude/agents/`, skills in `.claude/skills/`, hooks in settings — exactly the
"constitution + skills + memory" layering this project's own harness replicates.

- **Proposed contract:** *development-side only* (it is a cloud-backed CLI, but it
  is our dev tooling, not a product path — the local-first invariant covers
  shipped code, not the editor). Already adopted: this repo's 18 skills,
  `AGENT.md`/`CLAUDE.md` constitution, and `docs/agentic/` institutional memory
  are Claude-Code-shaped. One unexploited surface worth a roadmap note: its
  `PreToolUse`-style blocking hooks have no equivalent inside `modules/agent` —
  our guard runs at draft/output and input boundaries; a per-tool-call hook seam
  (before `act` executes) is a candidate hardening point for `graph.py`.
- **Verdict:** **ADOPT** (as development harness — de facto already in use;
  evidence is the repo's own `.claude/` tree). Reference-only for product code.
- **Sources:**
  - https://code.claude.com/docs/en/hooks (lifecycle hook events, blocking semantics)
  - https://code.claude.com/docs/en/sub-agents (isolated context, tool restriction, worktree isolation)
  - https://code.claude.com/docs/en/plugins-reference (plugin bundle: skills+agents+hooks+MCP)
  - https://deepwiki.com/anthropics/claude-code/3.1-agent-system-and-subagents (hierarchical task decomposition, background execution)

## Cursor + Windsurf — commercial IDE agents (cluster)

The IDE-side pair. **Cursor** (Anysphere): VS Code fork; Agent/Composer mode
executes multi-step edits and commands with human-in-loop checkpoints; a
background Rust indexing daemon maintains a tree-sitter AST of the workspace for
context. **Windsurf** (ex-Codeium): "Flows = Agents + Copilots" — Cascade agent
is ambient rather than a mode you invoke; three-tier command auto-execution
(Off / Auto model-decides / Turbo allowlist), aware of your real-time edits.
Now folded into Cognition as **Devin Desktop** (above). Both are single-agent,
synchronous-loop designs — you watch it work; contrast with the
fire-and-forget Devin/Jules/Copilot async pattern.

- **Proposed contract:** *none — reference only.* Proprietary editors, cloud
  inference paths. Relevant to the report as the *synchronous* end of the
  autonomy spectrum (developer inside the loop, agent around it) vs. the async
  end — and as the acquisition evidence that the market is consolidating around
  "one command center for many agents," the posture the capstone calls the
  orchestrator shift.
- **Verdict:** **REJECT** (adoption); **WATCH** the Devin Desktop/ACP
  consolidation trend as Related Work movement.
- **Sources:**
  - https://cuckoo.network/blog/2025/06/03/coding-agent (architectural comparison: Cursor serial agent + human control; Windsurf Flows)
  - https://docs.devin.ai/windsurf/plugins/cascade/cascade-overview (Cascade modes, three-tier auto-execution, real-time awareness)
  - https://beta.codeium.com/cascade (Windsurf → Devin Desktop rename, agent command center)
  - https://egghead.io/windsurf-cascade-vs-cursor-composer-agent-side-by-side-comparison~jbct2 (side-by-side agent UX comparison)

## OpenHands (ex-OpenDevin) — open-source flagship

MIT-licensed, actively developed (2.1k+ commits from 188+ contributors by its
paper; now repositioned as a self-hosted "developer control center" that runs
OpenHands, Claude Code, Codex, or any ACP-compatible agent across local/remote/
cloud backends). The V1 architecture — codified in an MLSys 2026 SDK paper — is
the most documented open agent stack: **event-sourced state** (all interactions
as immutable events on an append-only log, deterministic replay; the event
stream *is* the history, filtered for the prompt rather than stored as
action/observation pairs), immutable agent config, **typed tool system** with MCP
integration, workspace abstraction (same agent locally or in containerized remote
runtimes), built-in REST/WebSocket server, secret registry, and a
confirmation/security layer.

- **Proposed contract:** `modules/agent` — **adopt the event-sourced history
  pattern, not the framework.** Our `audit.py` already emits per-node events but
  treats them as telemetry; OpenHands' stronger claim is that the event log *is*
  the agent state — replayable, diffable, prompt-derivable. Concrete adaptation:
  make `run_agent`'s event log the canonical record of a run (tool call →
  observation causally linked by IDs, à la their `cause` field), enabling
  deterministic replay for evals and debugging — fits our eval-gate posture. Do
  not vendor the SDK: it is a full platform, we need ~200 lines of it, and our
  hand-rolled graph exists precisely to avoid framework weight (see
  `graph.py`'s no-LangGraph note).
- **Verdict:** **ADAPT** — event-sourcing + typed-tool + workspace-separation
  patterns are directly transplantable; the platform itself is too heavy and its
  agent loop solves a different problem (SWE tasks, not cited medical answers).
- **Sources:**
  - https://proceedings.mlsys.org/paper_files/paper/2026/file/8ae9cf363ea625161f885b798c1f1f78-Paper-Conference.pdf (V1 SDK paper: nine components, event-sourced state, typed tools)
  - https://arxiv.org/pdf/2407.16741v3.pdf (OpenHands platform paper: sandboxed execution, multi-agent, evals; MIT)
  - https://github.com/OpenDevin/OpenDevin/pull/2709 (event-stream-as-history refactor: causal `cause` fields, stream is source of truth)
  - https://github.com/OpenDevin/OpenDevin?tab=readme-ov-file (current positioning: multi-backend agent control center, ACP)

## SWE-agent + mini-swe-agent — the ACI lineage (cluster)

Princeton/Stanford research project, MIT. The **SWE-agent** paper (NeurIPS 2024)
contributed the field's most-cited design concept: the **Agent-Computer
Interface (ACI)** — LM agents are a new class of *end users* who need interfaces
built for them, not human tools bolted on. Findings: agents fail on raw-shell
editing; tailored commands (lint-guarded `edit`, specialized search/view) and
well-formed feedback measurably change behavior and performance (12.5% pass@1
SWE-bench, SOTA at the time). Single YAML governs behavior; maximal agency,
hackable codebase. **mini-swe-agent** is the maintainers' recommended successor:
~100 lines for the agent class, *bash as the only tool* (no tool-calling API —
works with literally any model), linear history (trajectory ≡ messages),
`subprocess.run` actions (trivially swappable for `docker exec`), >74% on
SWE-bench Verified with Gemini 3 Pro — the empirical case that scaffold
sophistication contributes less than model capability.

- **Proposed contract:** `modules/agent/tools/` — **adopt ACI as a design
  review lens, adopt mini-swe-agent as a minimalism control.** Concretely:
  (a) audit our 8 read-only tools' docstrings/feedback formats as an *interface
  for an LM user* — does `query_observations` fail loudly with corrective
  feedback on bad args (ACI lesson), or return empty results that read as "no
  data"? A half-day pass over `base.py`/`registry.py` error surfaces with the
  ACI paper open is cheap and on-brand. (b) mini-swe-agent is the benchmark for
  "is our graph complexity earning its keep" — if our plan→act→reflect loop
  can't beat a linear loop on our own golden evals, the difference is
  guardrails (which mini lacks entirely), and that comparison is itself a
  capstone finding worth one eval run.
- **Verdict:** **ADAPT** — the ACI lens applies verbatim to our tool surface;
  mini-swe-agent is the control experiment our eval suite should acknowledge.
- **Sources:**
  - https://arxiv.org/html/2405.15793v2 (ACI paper: agents-as-end-users thesis, edit/lint tool design, feedback formatting)
  - https://github.com/SWE-agent/mini-swe-agent (100-line bash-only agent, >74% SWE-bench Verified, linear history)
  - https://github.com/swe-agent/mini-swe-agent/blob/main/docs/index.md (design rationale; "use mini by default" guidance)
  - https://unvendored.com/swe-agent (status: maintainers recommend mini; full repo now research reference)

## Aider — open-source terminal pair-programmer

Apache-2.0, ~49.2k stars, 13k+ commits, actively maintained. Not an autonomous
agent — a *pair programmer*: git-native (auto-commits every AI change with sane
messages, diffable/revertable), edit-format discipline (SEARCH/REPLACE blocks
rather than whole-file rewrites), and the standout mechanism: a **repo map** —
tree-sitter-extracted symbols across the whole codebase, ranked by a PageRank-
style graph algorithm over dependency edges weighted by chat relevance
(`mentioned_idents` ×10, snake_case/camelCase long identifiers ×10), trimmed to a
token budget (default ~1k tokens, adaptive). Auto-lint after edits, optional
auto-test loop with reflection budget (`max_reflections = 3`).

- **Proposed contract:** `modules/rag` context assembly — **adapt the
  budgeted-relevance idea, not the code.** Our retrieval ranks reference chunks
  and user observations; Aider demonstrates that *ranked-into-a-token-budget* is
  a first-class design decision (map tokens are budgeted, ranking is
  chat-state-aware). Candidate adaptation: a bounded context budget in the RAG
  prompt composer where `[YOUR_RESULTS:N]`/`[REFERENCE:N]` blocks compete for
  tokens by relevance-weighted priority rather than fixed truncation — check
  `modules/rag` prompt assembly for current truncation behavior before scoping.
  Also citable in Related Work: auto-commit-per-change = our small
  single-purpose-commit convention; lint/test reflection loop = our eval gates.
- **Verdict:** **ADAPT** — repo-map's budgeted-relevance-ranking pattern is the
  most directly useful context-engineering idea in this survey for `modules/rag`;
  the tool itself is a pair-programmer, not an orchestrator.
- **Sources:**
  - https://aider.chat/docs/repomap.html (repo-map mechanism: tree-sitter symbols, graph ranking, token budget)
  - https://github.com/Aider-AI/aider/blob/main/aider/repomap.py (PageRank weighting implementation detail)
  - https://github.com/Aider-AI/aider (49.2k stars, 13k commits — active)
  - https://github.com/Aider-AI/aider/blob/main/aider/coders/base_coder.py (reflection/lint/test loop knobs)

## Dormant & cautionary: Devika, Plandex, Mentat, GPT-Pilot (cluster)

The graveyard half of the landscape — as load-bearing for the report as the
living tools, since it documents what hype-cycle adoption costs.

- **Devika** (MIT, 19.6k stars) — the headline "open-source Devin" of March
  2024. Multi-agent (planner/researcher/coder), web browsing, broad LLM support
  incl. Ollama. **Effectively dormant:** last substantive commit Sep 2024; only
  a README touch in Sep 2025. 19.6k stars, 147 open issues, zero maintained
  momentum — the canonical "viral clone abandoned inside a year" specimen.
- **Plandex** (MIT, 15.7k stars) — terminal agent for large tasks: 2M-token
  effective context, tree-sitter project maps, and a genuinely good idea — a
  **cumulative diff-review sandbox** keeping AI changes quarantined from the
  working tree until approved. Semi-maintained: v2.2.1 (Jul 2025) added local
  model/Ollama support, but **Plandex Cloud wound down Oct 2025**; repo is
  self-hostable, single-maintainer-paced.
- **Mentat** (Apache-2.0, ~2.6k stars) — early streaming-context CLI agent.
  **Archived Jan 2025**; the name now belongs to a commercial GitHub bot
  (mentat.ai). Confirmed dead upstream.
- **GPT-Pilot** (Pythagora) — the cautionary tale that lands in
  `recurring-failures.md` territory: a **Shai-Hulud-class supply-chain worm**
  lived in `core/telemetry/` from Aug 2025 to Jun 2026 — a hidden loader that
  fetched a Bun runtime and executed a credential stealer — unnoticed because
  the repo was unmaintained. Removed in PR #1183 (2026-06-12) after external
  disclosure; still in git history. Repo explicitly unmaintained. *The
  tool-selection lesson: "open source" ≠ "watched"; dormancy is a security
  property, not just a features property.*

- **Proposed contract:** none — reference and evidence only. For the report:
  Devika/Plandex/Mentat give the adoption-lifecycle curve (viral launch →
  dormancy inside ~18 months); GPT-Pilot gives the dependency-hygiene case —
  our `modules/agent` deliberately vendored *no* agent framework, and this is
  the receipt for that instinct. Plandex's quarantined-diff-sandbox is the one
  pattern worth a footnote if the product agent ever proposes writes (it echoes
  Copilot's scoped-branches posture: agent output lands in a review lane, never
  inline).
- **Verdict:** **REJECT** all four for adoption (dormant/archived/unmaintained;
  one actively hostile in history). Cite all four in Related Work.
- **Sources:**
  - https://github.com/stitionai/devika (repo: "modeled after Devin", 19.6k★)
  - https://github.com/stitionai/devika/commits/main (dormancy evidence: Sep 2024 → Sep 2025 README-only)
  - https://github.com/plandex-ai/plandex (2M-token context, diff-review sandbox)
  - https://github.com/plandex-ai/plandex/commits/main (Oct 2025 cloud wind-down commits)
  - https://github.com/AbanteAI/archive-old-cli-mentat (archived; name reassigned to mentat.ai bot)
  - https://github.com/Pythagora-io/gpt-pilot (README security notice; unmaintained)
  - https://github.com/Pythagora-io/gpt-pilot/pull/1183 (worm removal PR: loader, payload, timeline)

---

## Summary verdict table

| Tool | Kind | License / access | Alive? | Verdict | One-line reason |
|---|---|---|---|---|---|
| **Jev** (TypeSafe) | Decision-model API | Proprietary hosted | 10 days old | **REJECT** (dropped) | Owner picked Laya over it (2026-09-26); kept as commercial reference only |
| **Laya** (ConvAI) | Decision model | Apache-2.0, open weights | 1 week old | **WATCH→candidate** | Owner-selected test candidate to replace Jev; vendor reports CPU/GPU latency (hardware fit on Asclexis tiers unmeasured); zero-shot typed-decisions below majority baseline; hold for measured need + age |
| **Devin** | Async SWE agent | Closed commercial | Active | **REJECT / reference** | Category archetype + this repo's authorship disclosure anchor; Brain never leaves Cognition cloud |
| **Jules** | Async SWE agent | Closed commercial | Active (public beta) | **REJECT / reference** | Repo→cloud-VM→PR; cite for plan-approval-gate pattern |
| **Copilot coding agent** | Async SWE agent | Closed (GH sub) | Active | **REJECT / ADAPT pattern** | Scoped-write + forced-human-review posture is the right shape if our agent ever writes |
| **Claude Code** | CLI agent harness | Closed commercial | Active | **ADOPT (dev-side)** | De facto already this repo's harness; hooks/subagents/skills model is what we replicate |
| **Cursor / Windsurf** | IDE agents | Closed | Active (Windsurf→Devin Desktop) | **REJECT / WATCH** | Synchronous-loop end of the spectrum; consolidation evidence for the orchestrator thesis |
| **OpenHands** | Agent platform | MIT | Very active | **ADAPT** | Event-sourced run state → our `audit.py`; transplant the pattern, not the platform |
| **SWE-agent / mini** | Research agents | MIT | Active (mini supersedes) | **ADAPT** | ACI lens for our 8 tools' docs/errors; mini is the minimalism control for our graph |
| **Aider** | Pair-programmer | Apache-2.0 | Very active | **ADAPT** | Budgeted-relevance repo map → context-assembly idea for `modules/rag` |
| **Devika** | "Open-source Devin" | MIT | Dormant (~1 yr) | **REJECT** | Viral-clone lifecycle specimen; cite, don't use |
| **Plandex** | Terminal agent | MIT | Semi-maintained; cloud dead | **REJECT** | Quarantined diff-sandbox is a good pattern; project momentum insufficient to depend on |
| **Mentat (CLI)** | Terminal agent | Apache-2.0 | Archived Jan 2025 | **REJECT** | Dead upstream; name reassigned to a commercial bot |
| **GPT-Pilot** | App-builder agent | MIT (repo) | Unmaintained + compromised | **REJECT** | Supply-chain worm lived in-tree ~10 months; dormancy-as-security-risk evidence |

**UNVERIFIED flags (corrected 2026-09-27):** Laya hardware fit on Asclexis target
machines and Laya accuracy on Asclexis decision tasks — both unmeasured; the only
figures are vendor-reported. Every verdict above carries sources, but a source is
not the same as verification. Caveat on
recency: all Jev/Laya ecosystem claims are ≤10 days old at writing; star counts
and benchmark numbers in that section are vendor/tracker-published and will drift.
Re-verify before the report freezes.

Back to index: [../README.md](../README.md)
