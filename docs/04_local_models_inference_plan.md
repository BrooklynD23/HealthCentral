# Local AI Models + Inference Plan (Draft v0 — pending PM approval)

## Requirements (from PRD)
- Local-first assistant (RAG) with citations and conservative refusal behavior
- Runs on typical consumer Windows hardware (CPU-only supported)
- Offline-capable (models stored locally)
- Local embeddings model must be lightweight
- Model runner must not expose data over LAN by default

---

## Inference stack options (Windows)

### Option A (recommended): embed `llama.cpp`
- Bundle `llama.cpp` as the local inference engine; run GGUF quantized models.
- Benefits: no external dependency; full offline; no server process required; tighter control over data boundaries.

### Option B: integrate with Ollama / LM Studio (optional)
- Use an external local model manager/server.
- Hard requirements:
  - bind to localhost only
  - disable LAN exposure by default
  - require local auth token between app and runner
- Keep as “advanced” / opt-in because it expands the security surface.

---

## Recommended open-weight chat models (prioritize average hardware)
Assume quantized weights (e.g., 4-bit GGUF). Favor smaller models first.

### Tier 1: small + fast (best default)
- Gemma 2 2B Instruct
- Phi-3 Mini (3.8B)
- Qwen2.5 3B Instruct

Use cases:
- chat + summarization
- grounded explanations when retrieval context is strong
- clinician-ready narrative glue (facts and stats still come from code + verified data)

### Tier 2: balanced quality (mid-range laptops/desktops)
- Llama 3.1 8B Instruct
- Qwen2.5 7B Instruct
- Gemma 2 9B Instruct

### Tier 3: large (not default; advanced)
- 30B+ class models are typically not “average hardware”.
- Keep opt-in only with clear RAM/VRAM requirements.

---

## Embeddings models (local)
Default to small embedding models for speed and memory efficiency:
- BAAI/bge-small-en-v1.5
- intfloat/e5-small-v2

Rules:
- Keep embeddings deterministic and versioned.
- Store `embedding_model_id` with each vector.

---

## Guardrails specific to medical results
Model is never the source of truth.
- Parsing and trend stats computed by deterministic code.
- LLM only explains and summarizes retrieved, cited material.
- Response validator enforces:
  - citation presence
  - separation of “report facts” vs “general info”
  - refusal when insufficient context
  - no diagnosis/treatment advice

---

## Practical runtime assumptions
- CPU-only supported by default.
- Opportunistic acceleration (Vulkan / DirectML) where available.
- Default models must fit typical RAM budgets when quantized.
- Keep context sizes reasonable for local performance; prefer retrieval over huge contexts.

---

## Model selection UX
- “Recommended” default (Tier 1)
- “Higher quality” toggle (Tier 2)
- “Advanced” (Tier 3) behind explicit resource warnings
- Display per model:
  - model size and quantization
  - context length
  - disk usage estimate
  - whether images are supported (future)

---

## Open decisions (PM approval)
- Default runner: embedded llama.cpp vs external runner support policy
- Default chat model: Phi-3 Mini vs Gemma 2 2B vs Qwen2.5 3B
- Default embeddings: bge-small vs e5-small
- Distribution policy for model downloads (bundled vs user-installed)
