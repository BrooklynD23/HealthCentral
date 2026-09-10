# HealthCentral — Agent Overhaul Agile Plan

> **Branch:** `fix/agent-overhaul`
> **Format:** Scrum-lite for a solo client/engineer. You wear both hats, so
> ceremonies collapse into short self-checkpoints (see §3). The structure exists
> so you can *revisit and re-groom* — not so you can perform process.
> **Cadence:** 1-week sprints, Monday→Sunday. Inception week begins **Mon 2026-06-22**.

---

## 1. Product vision & success metrics

**Vision.** Promote HealthCentral's single-shot `/assistant/` RAG explainer into a
read-only, plan→act→reflect agent where governance (no medical advice, grounded,
conservative, local-first) is enforced *per step* and *audited*, not hoped-for in
one prompt.

**Definition of success (release-level, measurable):**

| Metric | Target | Measured by |
|---|---|---|
| Groundedness rate | 100% of answer sentences map to a retrieved source | eval axis 1 |
| Advice leakage | 0 across the golden set | eval axis 4 (zero-tolerance gate) |
| Abstention correctness | ≥ 95% on insufficient-evidence cases | eval axis 3 |
| p95 local latency | ≤ existing single-shot path + 50% | LLMOps timing |
| Offline operation | full loop runs with network disabled | manual + CI |
| Audit completeness | every node emits a structured event | audit assertion test |

---

## 2. Roles, definitions, traceability

- **Product Owner / Client (you):** owns priority, accepts stories at review.
- **Engineer (you):** owns estimates, DoR/DoD, implementation.
- **Definition of Ready (DoR):** story has acceptance criteria, a touched-files
  list, and a test or eval that will prove it. No story enters a sprint without these.
- **Definition of Done (DoD):** code + test/eval green in CI; audit event emitted
  if the story adds a node/tool; `/assistant/` unchanged when the feature flag is
  off; docs/TASK_LIST updated; proof-bundle commands pass from the WSL interpreter.
- **Skill traceability:** each epic is backed by a repo Skill (see companion
  skills) so the *how* lives in version-controlled guidance, the *what/when* lives here.

---

## 3. Ceremonies as solo checkpoints

| Ceremony | Solo form | When |
|---|---|---|
| Sprint planning | Pull 1 sprint of stories from backlog; confirm DoR | Mon, 20 min |
| Daily standup | One line — yesterday / today / blocker. The log through S6 is archived at `docs/archive/agile/STANDUP.md`; active work is tracked in `docs/features/TASK_LIST.md` | Daily, 2 min |
| Backlog grooming | Re-estimate + re-order remaining epics | Mid-sprint |
| Review (client hat) | Demo the flag-gated behavior to yourself; accept/reject stories | Sun |
| Retro | 3 bullets — keep / drop / try. The log through S6 is archived at `docs/archive/agile/RETRO.md` | Sun, 10 min |

The retro is the "revisit & iterate" engine — every Sunday you re-decide whether
the next sprint's scope still matches what you learned.

---

## 4. Epics (work streams)

Each maps to one of the six layers from the build thesis and to one backing Skill.

- **E1 — Agent Core** (`asclexis-agent`): the graph runner, typed tool
  registry, read-only rule, step budget, audit hooks.
- **E2 — Guardrails** (`asclexis-guardrails`): advice classifier, abstention
  templates, groundedness mapping, PHI redaction gate.
- **E3 — Evals** (`asclexis-evals`): golden set, 4 scoring axes, CI workflow.
- **E4 — LLMOps** (`asclexis-backend` + agent): semantic cache, tier routing,
  per-node timing/token tracking.
- **E5 — Cutover & Fallback**: flip `/assistant/` to the agent, keep old path one release.
- **E6 — Fine-tuning (stretch)**: LoRA distillation of grounded refusals into the local model.

---

## 5. Release plan

| Release | Theme | Sprints | Exit criteria |
|---|---|---|---|
| **R1 — Walking skeleton** | Agent runs behind a flag | S0–S2 | One tool end-to-end, audited, flag off = no change |
| **R2 — Governed & live** | Guardrails + cutover | S3–S5 | Guard node enforces; `/assistant/` served by agent; cache on |
| **R3 — Measured & tuned** | Proof + optional LoRA | S6–S7 | Evals gate CI; (stretch) LoRA beats base on golden set |

---

## 6. Sprint backlog

Story points: 1 = a few hours, 2 = ~half a focused day, 3 = a full day, 5 = multi-day.

### Sprint 0 — Inception (2026-06-22 → 06-28) · Goal: provable foundation
| ID | Story | AC | Pts |
|---|---|---|---|
| S0-1 | As the engineer, I scaffold `modules/agent/` so future nodes have a home | dirs + empty graph runner import-clean; `pytest` collects | 2 |
| S0-2 | As the engineer, I add a `agent_enabled` flag to model settings so work is invisible to users | flag defaults off; `/assistant/` path unchanged when off | 2 |
| S0-3 | As the engineer, I define the audit event schema for agent nodes so governance is wired from day one | one event persists through existing monitoring/audit | 3 |
| S0-4 | As the client, I have an `AGILE_PLAN` + `STANDUP`/`RETRO` files so I can run the cadence | files committed under `docs/agile/` | 1 |

### Sprint 1 — First tool, end-to-end (06-29 → 07-05) · Goal: one real loop
| ID | Story | AC | Pts |
|---|---|---|---|
| S1-1 | Typed tool registry with Pydantic I/O so malformed calls are rejected not executed | bad input → validation error, never reaches model | 3 |
| S1-2 | `query_observations` tool (read-only) so the agent can read verified values | returns only verified rows for current profile | 3 |
| S1-3 | Plan→Act→single-step Answer path behind the flag | flag on → answer with ≥1 citation; flag off → legacy | 5 |
| S1-4 | Audit event per node | assertion test: plan/act/answer each emit | 2 |

### Sprint 2 — The loop closes (07-06 → 07-12) · Goal: multi-step reflect
| ID | Story | AC | Pts |
|---|---|---|---|
| S2-1 | Add `compute_trend`, `retrieve_chunks`, `lookup_reference`, `check_verification` | each typed + read-only + audited | 5 |
| S2-2 | Reflect node with hard step budget (≤5) so it can't spin | budget exceeded → graceful terminal state | 3 |
| S2-3 | Replayability: structured per-step log reconstructs a run | failed run reproducible from log | 3 |
| S2-4 | Eval harness skeleton + 2 seed cases (1 grounded, 1 abstain) | both pass locally | 2 |

→ **R1 ships.** Review: demo flag-on agent answering a real biomarker question with citations.

### Sprint 3 — Guardrails as a node (07-13 → 07-19) · Goal: structural safety
| ID | Story | AC | Pts |
|---|---|---|---|
| S3-1 | Advice classifier pre-model AND on draft | "should I stop my statin?" → escalate template, never generated prose | 5 |
| S3-2 | Groundedness mapping: drop unmapped sentences before user sees them | injected unmapped claim is removed | 3 |
| S3-3 | Structured terminal output: `answer \| abstain \| escalate` + citations | schema-validated; abstain is first-class | 3 |
| S3-4 | Confidence threshold → abstain (no hedging) | low-conf case abstains, doesn't hedge | 2 |

### Sprint 4 — PHI gate + external path (07-20 → 07-26) · Goal: safe opt-in egress
| ID | Story | AC | Pts |
|---|---|---|---|
| S4-1 | PHI redaction gate inherited by the agent's external-LLM tool path | nothing leaves local without passing existing redaction | 5 |
| S4-2 | Network-disabled integration test for the full loop | loop completes offline on local GGUF | 3 |
| S4-3 | Grow golden set to ~30 cases incl. advice-bait + abstention categories | categories represented; all pass | 3 |

### Sprint 5 — Cutover + cache (07-27 → 08-02) · Goal: agent is the assistant
| ID | Story | AC | Pts |
|---|---|---|---|
| S5-1 | Flip `/assistant/` to agent; keep legacy path as one-release fallback | flag default on; fallback reachable | 3 |
| S5-2 | Semantic cache keyed on `(question, profile_version)` | repeat question served from cache; invalidates on new verified data | 5 |
| S5-3 | Per-node timing/token tracking surfaced in monitoring dashboard | p95 latency visible | 3 |

→ **R2 ships.** Review: legacy path retired-pending; agent live with cache + metrics.

### Sprint 6 — Evals gate CI (08-03 → 08-09) · Goal: it provably behaves
| ID | Story | AC | Pts |
|---|---|---|---|
| S6-1 | Golden set to 50–100 cases with synthetic vault states | coverage across panels + edge cases | 5 |
| S6-2 | Automated scoring of all 4 axes | groundedness/citation/abstention/advice scored numerically | 5 |
| S6-3 | `.github/workflows` job fails PR on advice leakage > 0 or groundedness < 100% | red PR on a planted regression | 3 |

→ **R3 core ships.**

### Sprint 7 — LoRA distillation (stretch) (08-10 → 08-16) · Goal: smaller, just as safe
| ID | Story | AC | Pts |
|---|---|---|---|
| S7-1 | Curate a labeled set of the big model's good grounded refusals | dataset versioned | 3 |
| S7-2 | LoRA/PEFT adapter on the local model for the explain+refuse task | adapter loads in llama.cpp pipeline | 5 |
| S7-3 | Benchmark adapter vs base on golden set | adapter ≥ base on all 4 axes | 3 |

---

## 7. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Agent invents unsupported clinical claims | Med | **Critical** | Groundedness mapping is mechanical (S3-2); zero-tolerance CI gate (S6-3) |
| Advice leaks mid-conversation | Med | **Critical** | Classifier runs pre-model *and* on draft (S3-1) |
| Latency balloons with multi-step loop | High | Med | Step budget (S2-2) + semantic cache (S5-2) + timing visibility (S5-3) |
| PHI egress via opt-in external LLM | Low | **Critical** | Inherit existing redaction gate; offline test (S4-1/2) |
| Scope creep from "agent can also..." | High | Med | Read-only rule is non-negotiable; new write-capability = new epic, not a story |
| Solo context loss between sprints | Med | Low | STANDUP + RETRO files; replayable run logs (S2-3) |

---

## 8. Iteration loop (how you revisit)

Every Sunday retro, re-ask three questions and re-groom the backlog accordingly:
1. **Did the eval set catch what mattered?** If a real failure slipped through, the
   first new story next sprint is a golden case that reproduces it.
2. **Is the read-only rule still holding?** Any pressure to let the agent write is a
   signal to spin up E-new, never to bend E1.
3. **Is governance still structural?** If a guardrail drifted into "we ask the model
   nicely in the prompt," pull it back into the guard node.

The backlog is a living artifact — reorder R3/stretch freely; R1/R2 exit criteria are fixed.
