# Tiered Model System

HealthCentral uses a tiered model system for lab interpretation that automatically adapts to your hardware capabilities.

## Overview

The system supports three quality tiers plus a template fallback:

| Tier | ID | Model | Size | Default |
|------|-----|-------|------|---------|
| 1 (Low) | `low` | Qwen2.5-0.5B-Instruct | ~0.5GB | **YES** |
| 1 (Alt) | `gemma4-e2b` | Gemma 4 E2B | ~1.5GB | No |
| 2 (Mid) | `mid` | Phi-3-mini-4k-instruct | ~2GB | No |
| 2 (Alt) | `gemma4-e4b` | Gemma 4 E4B | ~2.8GB | No |
| 3 (High) | `high` | BioMistral-7B | ~4GB | No |
| 3 (Alt) | `gemma4-12b` | Gemma 4 12B | ~7-8GB | No |
| Fallback | `template` | None (templates) | 0 | Auto |

**Note on Gemma 4 models**: The Gemma 4 family (released 2026-06-03, Apache 2.0) offers multimodal capability and extended 256K context. HuggingFace repository names for GGUF quantizations are marked as PLACEHOLDER in the source code and have not yet been verified to exist. These alternate IDs are registered/read-visible in model configuration, but the current set/download request schemas only accept `low`, `mid`, and `high`; use `LLM_PROVIDER`/`LLM_MODEL` or the provider endpoint for direct provider/model switching rather than treating Gemma IDs as downloadable tier selections.

## Tier Selection Logic

1. **Hardware Detection**: The system detects your RAM, CPU cores, and available disk space
2. **Recommendation**: Based on hardware, a maximum supported tier is recommended
3. **User Preference**: You can select any tier at or below your max supported tier
4. **Fallback Chain**: If the selected model isn't available, the system falls back gracefully

### Fallback Order

```
high → mid → low → template
```

If you select `high` but the model isn't downloaded, it tries `mid`, then `low`, then uses templates.

## Requirements by Tier

### Tier 1: Low (Default)
- **RAM**: 8GB minimum
- **Disk**: 1GB free
- **CPU**: Any modern CPU
- See [tier1_low.md](tier1_low.md) for details

### Tier 2: Mid
- **RAM**: 16GB minimum
- **Disk**: 3GB free
- **CPU**: 4+ cores recommended
- See [tier2_mid.md](tier2_mid.md) for details

### Tier 3: High
- **RAM**: 32GB minimum
- **Disk**: 5GB free
- **CPU**: 8+ cores recommended
- **GPU**: Optional (improves speed)
- See [tier3_high.md](tier3_high.md) for details

## Model Download

Models are downloaded from Hugging Face on first use:

```bash
# Check your hardware
python scripts/detect_hardware.py

# Download a model
python scripts/model_manager.py download --tier low

# List downloaded models
python scripts/model_manager.py list

# Switch active tier
python scripts/model_manager.py switch --tier mid
```

## Citation Enforcement

All LLM-generated interpretations must include citations:

- `[KB:analyte_name]` - Knowledge base reference
- `[INT:intervention_id]` - Intervention/recommendation reference
- `[Source:source_id]` - External source reference

If the LLM fails to include citations, the system falls back to template-based interpretation.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/settings/model` | GET | Get current settings |
| `/api/v1/settings/model/detect` | POST | Run hardware detection |
| `/api/v1/settings/model/tier` | POST | Set preferred tier |
| `/api/v1/settings/model/tiers` | GET | List tiers with availability |
| `/api/v1/settings/model/download` | POST | Start model download |
| `/api/v1/settings/model/download-progress` | GET | Check download status |

## Configuration

Settings in `core/config.py`:

```python
default_model_tier: str = "low"       # Default tier for new users
auto_detect_hardware: bool = True      # Run hardware detection on startup
model_download_timeout: int = 3600     # Download timeout (seconds)
```

## Database Storage

Model preferences are stored in `UserModelSettings` table in each profile's encrypted database:

- `preferred_tier`: User's selected tier
- `auto_detect_enabled`: Whether to auto-recommend based on hardware
- `last_hardware_json`: Cached hardware detection results
- `download_state_json`: Download progress (persists across restarts)
