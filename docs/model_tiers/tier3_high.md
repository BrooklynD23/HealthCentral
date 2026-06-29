# Tier 3: High (BioMistral-7B)

Premium tier with specialized medical knowledge. Requires significant resources.

## Model Details

| Property | Value |
|----------|-------|
| Model Name | BioMistral-7B |
| Hugging Face Repo | `BioMistral/BioMistral-7B-GGUF` |
| File | Auto-discovered (Q4_K_M preferred) |
| Size | ~4GB (Q4_K_M quantization) |
| Context Size | 4096 tokens |
| Type | Medical domain-specialized model |

## Hardware Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 32GB | 64GB |
| Disk Space | 5GB | 10GB |
| CPU Cores | 8 | 12+ |
| GPU | Optional | Recommended (6GB+ VRAM) |

## Performance Characteristics

- **Inference Speed**: Slow on CPU (~10-20 tokens/sec), Fast with GPU (~50+ tokens/sec)
- **Quality**: Best medical interpretations
- **Memory Usage**: ~8-12GB during inference
- **Startup Time**: ~20-30 seconds

## When to Use

- High-spec workstation or desktop
- Medical accuracy is critical
- Have dedicated GPU with 6GB+ VRAM
- Processing complex lab panels

## Advantages

- **Medical Domain Training**: Pre-trained on medical literature
- **Better Medical Terminology**: Understands clinical concepts
- **Nuanced Interpretations**: Recognizes subtle patterns
- **Higher Accuracy**: Fewer hallucinations on medical topics

## Limitations

- Requires significant resources
- Slow on CPU-only systems
- Larger download size
- May be overkill for simple interpretations

## GPU Acceleration

BioMistral-7B benefits significantly from GPU acceleration:

| Hardware | Speed | Quality |
|----------|-------|---------|
| CPU Only | ~10-20 tok/s | Same |
| GPU (6GB) | ~50-80 tok/s | Same |
| GPU (12GB+) | ~100+ tok/s | Same |

The system auto-detects available GPU but does not require it.

## Download

```bash
# Via CLI
python scripts/model_manager.py download --tier high

# Via API
POST /api/v1/settings/model/download
{"tier": "high"}
```

## Model Discovery

The exact GGUF filename is discovered at download time using `huggingface_hub.list_repo_files()`. The system prefers Q4_K_M quantization for balance of size and quality.

## Fallback Behavior

If BioMistral-7B isn't available or fails, the system falls back to:
1. Tier 2 (Phi-3-mini) if downloaded
2. Tier 1 (Qwen2.5-0.5B) if downloaded
3. Template-based interpretation

## Citation Quality

BioMistral-7B produces higher-quality citations due to medical training:

```
Your HbA1c result is 7.2% which is above the reference range of 4.0-5.6%.
[KB:hba1c] This indicates average blood glucose over 2-3 months.
A value above 6.5% suggests diabetes. [INT:lifestyle_diet]
Consider consulting your healthcare provider about dietary changes.
```

## Alternative: Gemma 4 12B

For users with 16GB RAM who want extended context and multimodal capability:

| Property | Value |
|----------|-------|
| Model Name | Gemma 4 12B |
| Size | ~7-8GB (Q4_K_M quantization) |
| Context Size | 256K tokens |
| Type | Multimodal with function-calling |
| Features | Image understanding, extended context, long-form reasoning |

**Repository** (PLACEHOLDER—not yet verified on HuggingFace): `ggml-org/gemma-4-12b-it-GGUF`
**Ollama tag**: `gemma4:12b`

Registered as a read-visible alternate near Tier 3 (`high`). Requires half the RAM of BioMistral-7B (16GB vs 32GB) while offering a significantly larger context window (256K vs 4K tokens) and multimodal support. Trade-off: BioMistral-7B remains the preferred choice for maximum medical-domain specialization; Gemma 4 12B prioritizes context length and multimodal capability. Current tier set/download APIs accept only `low`, `mid`, and `high`; use `LLM_PROVIDER=llama_cpp` or `LLM_PROVIDER=ollama` plus `LLM_MODEL`, or use the `/api/v1/settings/model/provider` endpoint at runtime for direct provider/model switching.
