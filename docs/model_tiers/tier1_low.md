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

## Fallback Behavior

If Qwen2.5-0.5B fails to include required citations, the system falls back to template-based interpretation automatically.
