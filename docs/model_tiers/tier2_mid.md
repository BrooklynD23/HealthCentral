# Tier 2: Mid (Phi-3-mini-4k-instruct)

Balanced tier offering improved quality while maintaining reasonable resource usage.

## Model Details

| Property | Value |
|----------|-------|
| Model Name | Phi-3-mini-4k-instruct |
| Hugging Face Repo | `microsoft/Phi-3-mini-4k-instruct-gguf` |
| File | Auto-discovered (Q4_K_M preferred) |
| Size | ~2GB (Q4_K_M quantization) |
| Context Size | 4096 tokens |
| Type | Microsoft's efficient instruction model |

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
- Longer context needed (4k tokens)

## Advantages Over Tier 1

- Longer context window (4096 vs 2048)
- Better reasoning capabilities
- More detailed explanations
- Improved medical terminology understanding

## Limitations

- Slower than Tier 1
- Higher memory requirements
- Not specialized for medical domain (general-purpose)

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

## Fallback Behavior

If Phi-3-mini isn't available or fails, the system falls back to:
1. Tier 1 (Qwen2.5-0.5B) if downloaded
2. Template-based interpretation
