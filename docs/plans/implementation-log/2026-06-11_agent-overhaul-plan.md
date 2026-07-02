# Agent Overhaul Plan — 2026-06-11

> Historical Reference: this plan predates later implementation work and contains completed items.
> Use `docs/features/TASK_LIST.md` for active remaining tasks. Its own P0-P5 phase goals (pipeline
> fixes, provider abstraction, RAG memory, biomarker chat, RL feedback) were superseded by the more
> granular `docs/prd/phases/PHASE_0-7_*.md` + `docs/agile/sprints/` structure and are confirmed shipped.

Branch: `fix/agent-overhaul`

## Goals
1. Fix document import → parse → display pipeline (graphs in user profiles).
2. Make the assistant converse about the user's biomarkers, grounded in their data.
3. Fix RAG to persist patient/user history as agent memory.
4. Model-agnostic provider layer; Gemma 4 (June 2026, Apache 2.0) as a supported local model via llama.cpp GGUF, Ollama optional.
5. RL for agentic LLM: feedback capture (thumbs + corrections) → local preference store → DPO/GRPO-ready dataset export (training deferred; TRL/Unsloth-compatible).

## Phases
- **P0 Diagnosis** — run backend pytest + frontend build/tests; write breakage map to `implementation_plan/2026-06-11_breakage-map.md`.
- **P1 (parallel)** — Pipeline fixes (ingest/extract/observations/TrendsDashboard) ∥ Provider abstraction (`core/model_runner.py` → provider interface: LlamaCppProvider primary, OllamaProvider optional; Gemma 4 chat template + model_selector/model_settings updates).
- **P2** — RAG memory: per-profile history persistence wired into retrieval (`modules/rag.py`, `api/memory.py`, embeddings/chunking).
- **P3** — Biomarker chat: assistant grounded in observations + RAG memory (`api/assistant.py`, `ExplainAssistant.tsx`, interpret modules).
- **P4** — RL feedback pipeline: feedback API + UI, SQLite preference store, JSONL export in DPO format.
- **P5 Verification** — full test suites, frontend build, diff review.

## Constraints
- Local-first / privacy-first: no network calls in product code paths.
- Grounded outputs, no medical advice — preserve safety modules (interpret_safety, faithfulness, verifier_agent).
- Incremental commits per phase on the feature branch.
