# Tier 1: Low (Qwen2.5-0.5B-Instruct)

The default tier for all installations. Optimized for speed and low resource usage.

## Model Details

| Property | Value |
|----------|-------|
| Model Name | Qwen2.5-0.5B-Instruct |
| Hugging Face Repo | `Qwen/Qwen2.5-0.5B-Instruct-GGUF` |
| File | `qwen2.5-0.5b-instruct-q4_k_m.gguf` |
| Size | ~350MB (Q4_K_M quantization) |
| Context Size | 2048 tokens |
| Type | Instruction-tuned general assistant |

## Hardware Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 8GB | 16GB |
| Disk Space | 1GB | 2GB |
| CPU Cores | 2 | 4+ |
| GPU | Not required | Not needed |

## Performance Characteristics

- **Inference Speed**: Fast (~100+ tokens/sec on modern CPU)
- **Quality**: Basic medical interpretations
- **Memory Usage**: ~1-2GB during inference
- **Startup Time**: ~2-5 seconds

## When to Use

- Older or low-spec hardware
- Quick responses are priority
- Basic lab interpretation needs
- First-time setup/testing

## Limitations

- Shorter context window (2048 tokens)
- May miss subtle medical nuances
- Less detailed explanations compared to higher tiers

## Download

```bash
# Via CLI
python scripts/model_manager.py download --tier low

# Via API
POST /api/v1/settings/model/download
{"tier": "low"}
```

## Citation Prompt Template

The model uses a structured prompt that requires `[KB:*]` and `[INT:*]` citations:

```
You are a medical results assistant explaining lab values.

RULES:
1. Cite knowledge base facts as [KB:analyte_name]
2. Cite intervention advice as [INT:intervention_id]
3. NEVER diagnose conditions
4. ALWAYS recommend consulting healthcare provider

Lab Result: {analyte} = {value} {unit}
Reference Range: {ref_low} - {ref_high}
Knowledge: {knowledge_text}

Provide a patient-friendly explanation with citations:
```

## Alternative: Gemma 4 E2B

For users with 8GB RAM who want multimodal capability and extended context:

| Property | Value |
|----------|-------|
| Model Name | Gemma 4 E2B |
| Size | ~1.5GB (Q4_K_M quantization) |
| Context Size | 256K tokens |
| Type | Multimodal with function-calling |
| Features | Image understanding, extended context |

**Repository** (PLACEHOLDER—not yet verified on HuggingFace): `unsloth/gemma-4-e2b-it-GGUF`
**Ollama tag**: `gemma4:e2b`

Registered as a read-visible alternate near Tier 1 (`low`), offering the same 8GB RAM floor as Qwen2.5-0.5B but with multimodal and function-calling support. Current tier set/download APIs accept only `low`, `mid`, and `high`; use `LLM_PROVIDER=llama_cpp` or `LLM_PROVIDER=ollama` plus `LLM_MODEL`, or use the `/api/v1/settings/model/provider` endpoint at runtime for direct provider/model switching.

## Fallback Behavior

If Qwen2.5-0.5B fails to include required citations, the system falls back to template-based interpretation automatically.
