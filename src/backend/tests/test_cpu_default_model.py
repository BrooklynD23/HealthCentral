"""CPU-DEFAULT-PHI4: Phi-4-mini is the default chat model on CPU-only machines.

Tier choice (hardware_detection) and GGUF discovery (LlamaCppProvider) only;
no model is loaded.
"""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[1]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from modules.hardware_detection import (  # noqa: E402
    get_recommended_tier_from_hardware,
    get_tier_display_info,
)


def test_hc_cpu_001_cpu_only_16_to_31_gb_gets_mid():
    assert get_recommended_tier_from_hardware(16.0, 100.0, None) == "mid"
    assert get_recommended_tier_from_hardware(24.0, 100.0, None) == "mid"


def test_hc_cpu_002_gpu_path_unchanged_pin():
    assert get_recommended_tier_from_hardware(24.0, 100.0, 16.0) == "high"


def test_hc_cpu_005_mid_label_names_phi4_mini():
    assert get_tier_display_info("mid")["model"] == "Phi-4-mini-instruct"


# --- GGUF discovery -------------------------------------------------------

from types import SimpleNamespace  # noqa: E402

from core.llm.llama_cpp_provider import LlamaCppProvider  # noqa: E402

_GEMMA = "gemma4-e4b-it-Q4_K_M.gguf"
_PHI4 = "microsoft_Phi-4-mini-instruct-Q4_K_M.gguf"


def _provider(tmp_path: Path, n_gpu_layers: int) -> LlamaCppProvider:
    (tmp_path / _GEMMA).write_bytes(b"x")
    (tmp_path / _PHI4).write_bytes(b"x")
    provider = LlamaCppProvider(n_gpu_layers=n_gpu_layers)  # no Llama is built here
    provider._settings = SimpleNamespace(
        models_path=str(tmp_path), default_chat_model="phi-3-mini"
    )
    return provider


def test_hc_cpu_003_cpu_prefers_phi4_mini_over_gemma(tmp_path):
    found = _provider(tmp_path, 0)._find_model_path()
    assert found is not None and found.name == _PHI4


def test_hc_cpu_004_gpu_layers_keep_gemma_first_pin(tmp_path):
    found = _provider(tmp_path, 35)._find_model_path()
    assert found is not None and found.name == _GEMMA
