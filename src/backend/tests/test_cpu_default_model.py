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
