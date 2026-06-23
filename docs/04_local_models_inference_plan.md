# Local AI Models + Inference Plan

**Status:** Phase 0.3 Implemented (2026-01-30)
**Implementation:** See `docs/model_tiers/` for tier documentation

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

### Provider Selection (Implemented)

The provider abstraction described above is implemented in `src/backend/core/llm/`:

- `provider.py` — abstract provider interface (capabilities(), is_available(), generate(), generate_async(), generate_stream())
- `factory.py` — `get_provider()` / `reset_provider()` instantiate the active provider based on settings
- `llama_cpp_provider.py` — default provider; auto-detects the chat template from GGUF metadata
- `ollama_provider.py` — optional provider; enforces localhost-only via `_assert_localhost()` (privacy guarantee — Ollama base URL must never point off-device)

Configuration via `.env` (see `config/.env.example`):
- `LLM_PROVIDER` — `llama_cpp` (default) or `ollama`
- `LLM_MODEL` — model identifier (GGUF repo for llama_cpp, Ollama tag for ollama)
- `OLLAMA_BASE_URL` — must be localhost

The active provider/model can also be switched at runtime via `GET`/`PUT /api/v1/settings/model/provider` (src/backend/api/model_settings.py) — runtime changes are NOT persisted to `.env`.

Gemma 4 (E2B/E4B/12B) is now a registered model family across the hardware tiers — see `docs/model_tiers/`.

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
- clinician-ready narrative glue (facts and stats still come from code + retrieved observation context, with verified values marked separately)

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

---

## Implementation Notes (Phase 0.3)

### Implemented Tiered Model System

| Tier | String ID | Model | Size | RAM Required | Default |
|------|-----------|-------|------|--------------|---------|
| 1 | `"low"` | Qwen2.5-0.5B-Instruct | ~0.5GB | 8GB | **YES** |
| 2 | `"mid"` | Phi-3-mini-4k-instruct | ~2GB | 16GB | No |
| 3 | `"high"` | BioMistral-7B | ~4GB | 32GB | No |
| - | `"template"` | None | 0 | Any | Fallback |

### Key Implementation Files

- `modules/hardware_detection.py` - RAM/CPU/disk detection, tier recommendations
- `modules/model_selector.py` - Model loading, async inference, fallback chain
- `api/model_settings.py` - 6 REST endpoints for settings management
- `models/model_settings.py` - UserModelSettings table (per-profile database)
- `scripts/detect_hardware.py` - CLI hardware detection tool
- `scripts/model_manager.py` - CLI model management tool

### Citation Enforcement

LLM interpretations require `[KB:*]`, `[INT:*]`, or `[Source:*]` citations.
If missing, the system falls back to template-based interpretation.

### Fallback Chain

```
high → mid → low → template
```

### CLI Usage

```bash
# Check hardware capabilities
python scripts/detect_hardware.py

# Download a model
python scripts/model_manager.py download --tier low

# List downloaded models
python scripts/model_manager.py list
```

### API Endpoints

- `GET /api/v1/settings/model` - Current settings + hardware info
- `POST /api/v1/settings/model/detect` - Run hardware detection
- `POST /api/v1/settings/model/tier` - Set preferred tier
- `GET /api/v1/settings/model/tiers` - List all tiers
- `POST /api/v1/settings/model/download` - Start model download
- `GET /api/v1/settings/model/download-progress` - Check download status
