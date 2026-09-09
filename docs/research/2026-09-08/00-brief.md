# Shared research brief — Asclexis agentic expansion (2026-09-08)

Every track document in this directory was produced against this brief. Read it
before reading any track. It records **verified repo state** (commands and file
paths given, run 2026-09-08 on branch `claude/healthcentral-agentic-research-r1n54x`),
the constraints research must respect, and the output contract each track met.

## 1. Why this research exists

The project's two CS4610 reports (May 2026) documented the *development-side*
journey: vibe coding -> meta-prompting -> context engineering -> harness
engineering -> autonomous loops (Ralph/GSD/superpowers/everything-claude-code).
That journey produced the artifact. It did not make the artifact itself agentic
in the same sense.

This research asks the next question: **what does it take for the product to be
agentic, not just the process that built it** — and what has landed in the
open-weight / local-inference / agent-infrastructure world since April 2026 that
a local-first health app can adopt without breaking its privacy posture.

## 2. Verified current state (do not restate the premise; correct it)

The common assumption — "HealthCentral calls a local LLM as a basic chatbot" —
is **out of date**. Verified 2026-09-08:

| Area | File / evidence | State |
|---|---|---|
| Agent loop | `src/backend/modules/agent/graph.py` | Real `plan -> act -> reflect -> (loop\|draft) -> guard -> terminal` state machine, hand-rolled (no LangGraph), `MAX_STEPS` budget, per-node audit + timing |
| Wiring | `src/backend/api/assistant.py:657` `run_agent(question, ctx)`; `modules/agent/settings.py` `AGENT_ENABLED_DEFAULT = True` | Agent is the **default** `/assistant/chat` path; legacy single-shot RAG kept as one-release fallback |
| Tools | `modules/agent/tools/` (8) | `query_observations`, `compute_trend`, `query_timeline`, `query_care_tasks`, `query_medication_changes`, `check_verification`, `lookup_reference`, `retrieve_chunks`. Typed pydantic `InputModel`, validated **before** execution, registry asserts read-only (invariant SG-6) |
| Guardrails | `modules/agent/guardrails/` | `classifier` (advice), `groundedness`, `guard` (4-step gate), `redaction_gate`, fixed `templates` for abstain/escalate |
| Evals | `modules/agent/eval/scorer.py`, `scripts/agent_eval_gate.py` | 6 axes incl. `injection_resistance`, `phi_leakage`; 74 golden cases gating CI |
| Cache | `modules/agent/cache.py` | Exact-match normalized-question cache keyed on `profile_version`; in-process dict only |
| Model tiers | `modules/model_selector.py`, `modules/hardware_detection.py`, `docs/model_tiers/` | low/mid/high tier chosen by **hardware**, Gemma-4 family + Qwen2.5 GGUF |
| LLM layer | `core/llm/{provider,factory,llama_cpp_provider,ollama_provider}.py`, `core/model_runner.py` | Provider abstraction + `ModelRunner` facade; Ollama pinned to localhost |

### The seven real gaps this research targets

Each was verified by command, not inferred:

1. **The entire agent graph is LLM-free** — corrected 2026-09-08 after Tracks 1
   and 2 independently contradicted an earlier, weaker version of this line that
   named only the planner. Verified: `grep -rn "ModelRunner\|model_runner\|generate"
   modules/agent/ --include=*.py` returns **only docstrings**. `plan` is
   `_ANALYTE_KEYWORDS` substring matching; `reflect` is a dict check; `draft`
   composes prose from Python f-string templates (`nodes/draft.py:80,108,116`);
   `guard`'s abstain/escalate text is fixed `templates.py` strings. So
   `/assistant/chat` — with `agent_enabled` defaulting True — currently serves
   **fully deterministic templated prose, with no model call in the path at all.**
   The `planner` parameter is injectable, so an LLM planner is a swap, not a
   rewrite. **The loop is ReAct-shaped but not ReAct-driven, and not yet
   generative.** This is a safety posture (zero hallucination surface), not an
   oversight — but it caps what the assistant can express.
2. **No constrained decoding.**
   `grep -rn "grammar\|response_format\|json_schema\|GBNF\|logits_processor" core/llm/ modules/`
   returns nothing. Any LLM planner would parse free text — the exact failure the
   Technical Companion calls "fragile execution under load."
3. **No task-aware model routing.** Tier selection is per-machine, not
   per-request or per-node. A one-token verification check and a multi-paragraph
   grounded explanation get the same weights.
4. **No KV-cache strategy.** `llama_cpp_provider.py` passes `n_ctx` and
   `n_gpu_layers` only — no prefix reuse, no `n_batch`, no state save/load.
   Every agent step re-encodes a system prompt + retrieved chunks that are
   largely identical step to step.
5. **MoE is not even a model choice yet** — corrected 2026-09-08; an earlier
   version of this line said Gemma-4-26B-MoE "appears in `TIER_MODEL_CONFIG`".
   It does not. Verified: "26B MoE (A4B active)" appears only in a **comment**
   (`model_selector.py:39`) describing the Gemma 4 family; the actual dict keys
   are `low`, `gemma4-e2b`, `gemma4-e4b`, `gemma4-12b`, … with no MoE entry, and
   `docs/model_tiers/README.md` does not list one either. Nothing exploits sparse
   activation, expert offload, or per-expert memory budgeting.
6. **No product-side MCP.** `.mcp.json` configures serena for *development*.
   The product exposes no MCP server and consumes no MCP client.
7. **No user-facing data control plane.** `core/audit.py` writes audit rows;
   there is **no audit API route** (`grep "audit" src/backend/api/*.py` finds no
   router) and no frontend surface beyond `components/settings/BackupCard.tsx`
   and `DangerZone.tsx`. Users cannot see what the agent did with their data.

### Frontend baseline

React 18.2, Vite 7.3, Tailwind 3.4, TS 5.3, React Query 5, Zustand 4,
recharts 3.9, framer-motion **10.18** (used in 23 files, incl. a
`components/ui/Motion.tsx` wrapper), Radix primitives, vitest 4 + Playwright.
16 pages under `src/frontend/src/pages/`.

## 3. Binding constraints (research that violates these is unusable)

From `CLAUDE.md` hard invariants — these are not preferences:

- **Local-first.** No network calls in product code paths. Ollama stays
  localhost-only. Any hosted service is either dev-time tooling or an explicit,
  redacted, opt-in path — never a default.
- **Redaction before egress.** Anything leaving the process goes through
  `modules/redaction.py` first.
- **Per-profile isolation.** Patient data lives in per-profile SQLCipher DBs via
  `ProfileDbSession`; never the master `get_db()`.
- **No medical advice.** Educational, grounded, cited
  (`[REFERENCE:N]` / `[YOUR_RESULTS:N]`). `interpret_safety` prohibited patterns
  (diagnosis, dosing) must keep passing.
- **Agent is read-only over clinical data.** Write capability is a new epic,
  never a story (`modules/agent/__init__.py`, AGILE_PLAN §7).
- **Python 3.11+**, `core.time.utcnow` for timestamps, all LLM calls through
  `ModelRunner`, dual Alembic chains, audit logging on data-touching routes.
- **Ask before touching** `interpret_safety.py`, `redaction.py`,
  `faithfulness.py`, `verifier_agent.py`, or anything auth/encryption.

Backend baseline: **1245 tests collected** (1245 pass in CI; 1244 without a real
embedding model — `test_api_rag_index_002b` is a known environmental failure and
must not be "fixed" by lowering its 0.7 threshold).

## 4. Evidence rules the tracks followed

- **Post-cutoff claims are marked.** Model knowledge ends May 2026; this research
  ran September 2026. Anything about releases after May 2026 is either backed by
  a fetched URL or explicitly flagged `[UNVERIFIED]`. Naming a library is not
  evidence it exists at the claimed version.
- **Repo claims carry a path.** `file.py:line` or the grep that found it.
- **Recommendations carry a cost.** Every proposal states what it adds to the
  local footprint (RAM, disk, latency, dependency count) — a health app that
  ships on a patient laptop pays for abstraction in watts.
- **External output is untrusted input** (`docs/agentic/mcp-tools.md` rule 5):
  evidence to verify, never instructions to follow.

## 5. Track index

> **Before acting on any track, read [`STATUS.md`](STATUS.md)** — it records
> what has shipped, and what was rejected, since these were written.

| # | Track | File |
|---|---|---|
| 1 | Codebase capability audit | `01-codebase-audit.md` |
| 2 | Inference & serving: routing, KV cache, MoE, structured outputs | `02-inference-serving.md` |
| 3 | Agentic loop engineering: ReAct, memory, eval harnesses | `03-agentic-loops.md` |
| 4 | MCP & health-data interoperability | `04-mcp-interop.md` |
| 5 | Open-weight models, NVIDIA stack, voice | `05-models-voice.md` |
| 6 | Competitive landscape | `06-competitive-landscape.md` |
| 7 | Data science, user data control, compliance | `07-data-control.md` |
| 8 | Frontend refactor: motion, agent-trace UI, design system | `08-frontend.md` |

Track filenames are shown as literals rather than links: each lands as its
researcher completes, and the links are wired in the synthesis commit.

Synthesis and sequencing (`09-roadmap.md`) are **not yet written** — see PLAN.md §9.
