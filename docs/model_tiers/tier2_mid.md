# Tier 2: Mid (Phi-4-mini-instruct)

Balanced tier offering improved quality while maintaining reasonable resource usage.

> **Changed 2026-09-09:** this tier was `Phi-3-mini-4k-instruct` until the 4K
> context proved too small to hold retrieved chunks, a tool menu and a question
> at once. Phi-4-mini is the same size class under the same MIT license.
> It requires `llama-cpp-python >= 0.3.35` — the previously pinned 0.3.2 wheel
> (Nov 2024) predates the model. The repo path below is **not yet verified**
> against HuggingFace; confirm it before first download.

## Model Details

| Property | Value |
|----------|-------|
| Model Name | Phi-4-mini-instruct (3.8B) |
| Hugging Face Repo | `bartowski/microsoft_Phi-4-mini-instruct-GGUF` ⚠️ unverified |
| File | Auto-discovered (Q4_K_M preferred) |
| Size | ~2.5GB (Q4_K_M quantization) |
| Context Size | 16384 tokens (model supports 128K; capped for the CPU-only path) |
| Type | Microsoft instruction model, MIT |
| Minimum runtime | `llama-cpp-python >= 0.3.35` |

⚠️ Microsoft publishes no first-party Phi-4-**mini** GGUF (`microsoft/phi-4-gguf`
is the 14B). The repo above is a community quantizer, so it is a supply-chain
choice as well as a quality one: verify with `huggingface_hub.list_repo_files()`
and record a checksum in `modules/model_integrity.py` before relying on it.

## Hardware Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 16GB | 24GB |
| Disk Space | 3GB | 5GB |
| CPU Cores | 4 | 8+ |
| GPU | Not required | Optional (speeds up) |

## Performance Characteristics

- **Inference Speed**: Moderate (~30-50 tokens/sec on CPU)
- **Quality**: Good medical interpretations with better reasoning
- **Memory Usage**: ~4-6GB during inference
- **Startup Time**: ~10-15 seconds

## When to Use

- Mid-range hardware (most modern laptops)
- Need better explanations than Tier 1
- Willing to trade some speed for quality
- Longer context needed (16k tokens)

## Advantages Over Tier 1

- Much longer context window (16384 vs 2048)
- Better reasoning capabilities
- More detailed explanations
- Improved medical terminology understanding

## Limitations

- Slower than Tier 1
- Higher memory requirements
- Not specialized for medical domain (general-purpose) — deliberate; see
  `docs/research/2026-09-08/05-models-voice.md` on why a medically-tuned
  generator is a liability against the advice-leakage eval axis

## Download

```bash
# Via CLI
python scripts/model_manager.py download --tier mid

# Via API
POST /api/v1/settings/model/download
{"tier": "mid"}
```

## Model Discovery

The exact GGUF filename is discovered at download time using `huggingface_hub.list_repo_files()`. The system prefers Q4_K_M quantization when available.

## Alternative: Gemma 4 E4B

For users with 12GB RAM who want multimodal capability and extended context:

| Property | Value |
|----------|-------|
| Model Name | Gemma 4 E4B |
| Size | ~2.8GB (Q4_K_M quantization) |
| Context Size | 256K tokens |
| Type | Multimodal with function-calling |
| Features | Image understanding, extended context |

**Repository** (PLACEHOLDER—not yet verified on HuggingFace): `unsloth/gemma-4-e4b-it-GGUF`
**Ollama tag**: `gemma4:e4b`

Registered as a read-visible alternate near Tier 2. Requires slightly less RAM than Phi-4-mini (12GB vs 16GB) while offering multimodal support and a larger context window. Current tier set/download APIs accept only `low`, `mid`, and `high`; use `LLM_PROVIDER=llama_cpp` or `LLM_PROVIDER=ollama` plus `LLM_MODEL`, or use the `/api/v1/settings/model/provider` endpoint at runtime for direct provider/model switching.

## Fallback Behavior

If Phi-4-mini isn't available or fails, the system falls back to:
1. Tier 1 (Qwen2.5-0.5B) if downloaded
2. Template-based interpretation
