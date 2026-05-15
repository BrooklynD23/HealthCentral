"""Unit tests for hardware detection and tier recommendation."""

import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_HD_PATH = _ROOT / "modules" / "hardware_detection.py"
_spec = importlib.util.spec_from_file_location("hardware_detection_under_test", _HD_PATH)
_hd = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_hd)

_effective_ram_gb = _hd._effective_ram_gb
_detect_gpu_nvidia_smi = _hd._detect_gpu_nvidia_smi
can_run_tier = _hd.can_run_tier
get_recommended_tier_from_hardware = _hd.get_recommended_tier_from_hardware
HardwareProfile = _hd.HardwareProfile
GPU_VRAM_BUMP_MIN_GB = _hd.GPU_VRAM_BUMP_MIN_GB


class TestEffectiveRam:
    def test_no_boost_without_gpu(self):
        assert _effective_ram_gb(16.0, None) == 16.0

    def test_no_boost_below_threshold(self):
        assert _effective_ram_gb(16.0, GPU_VRAM_BUMP_MIN_GB - 1) == 16.0

    def test_boost_at_threshold_plus_delta(self):
        assert _effective_ram_gb(16.0, 16.0) == pytest.approx(24.0)
        out = _effective_ram_gb(8.0, 40.0)
        assert out == pytest.approx(32.0)


class TestRecommendedTier:
    def test_ram_only_high(self):
        assert get_recommended_tier_from_hardware(64.0, 100.0, None) == "high"

    def test_gpu_bumps_mid_when_ram_was_low(self):
        assert get_recommended_tier_from_hardware(24.0, 100.0, None) == "mid"
        assert get_recommended_tier_from_hardware(24.0, 100.0, 16.0) == "high"

    def test_disk_blocks_high_even_with_gpu(self):
        assert get_recommended_tier_from_hardware(64.0, 4.0, 24.0) == "mid"


class TestNvidiaSmi:
    @patch.object(_hd.subprocess, "run")
    def test_parses_name_and_vram(self, mock_run):
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "NVIDIA GeForce RTX 3070, 8192\n"

        name, vram = _detect_gpu_nvidia_smi()
        assert name == "NVIDIA GeForce RTX 3070"
        assert vram == pytest.approx(8.0)

    @patch.object(_hd.subprocess, "run")
    def test_returns_none_on_failure(self, mock_run):
        mock_run.side_effect = FileNotFoundError()

        assert _detect_gpu_nvidia_smi() == (None, None)


class TestCanRunTier:
    def test_sufficient_effective_ram_and_disk(self):
        p = HardwareProfile(
            ram_total_gb=24.0,
            ram_available_gb=10.0,
            cpu_cores=8,
            disk_free_gb=100.0,
            gpu_available=True,
            gpu_vram_gb=16.0,
            gpu_name="Test",
            recommended_tier="high",
        )
        assert can_run_tier(p, "high") is True

    def test_insufficient_disk(self):
        p = HardwareProfile(
            ram_total_gb=64.0,
            ram_available_gb=20.0,
            cpu_cores=8,
            disk_free_gb=2.0,
            recommended_tier="high",
        )
        assert can_run_tier(p, "high") is False
