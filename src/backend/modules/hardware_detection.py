"""
Hardware detection module for model tier selection.

Phase 0.3: Tiered Hardware Model System

Detects system capabilities (RAM, CPU, disk) to recommend appropriate
model tiers. GPU detection uses PyTorch CUDA (optional), nvidia-smi, or
Windows WMI. Tier selection uses RAM + disk; when GPU reports sufficient VRAM,
an effective-RAM boost can recommend a higher tier (GPU assists local inference).
"""

import logging
import platform
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Tuple

import psutil

logger = logging.getLogger(__name__)


# Tier requirements (RAM-based; GPU VRAM can lift effective RAM for recommendation)
TIER_REQUIREMENTS: dict[str, dict[str, float]] = {
    "low": {"ram_gb": 8, "disk_gb": 1},      # Qwen 0.5B
    "mid": {"ram_gb": 16, "disk_gb": 3},     # Phi-3-mini
    "high": {"ram_gb": 32, "disk_gb": 5},    # BioMistral-7B
}

# Tier priority order (highest to lowest)
TIER_ORDER = ["high", "mid", "low"]

# Minimum GPU VRAM (GB) before we apply an effective-RAM boost toward tier selection.
GPU_VRAM_BUMP_MIN_GB = 8.0
# Max GB added to effective RAM when GPU VRAM exceeds the threshold (caps overshoot).
GPU_EFFECTIVE_RAM_BOOST_CAP_GB = 24.0

_NVIDIA_SMI_TIMEOUT_SEC = 5.0
_WMIC_TIMEOUT_SEC = 5.0


def _effective_ram_gb(ram_gb: float, gpu_vram_gb: Optional[float]) -> float:
    """RAM used for tier rules; VRAM beyond the threshold counts toward RAM need up to a cap."""
    if gpu_vram_gb is None or gpu_vram_gb < GPU_VRAM_BUMP_MIN_GB:
        return ram_gb
    over = max(0.0, gpu_vram_gb - GPU_VRAM_BUMP_MIN_GB)
    boost = min(GPU_EFFECTIVE_RAM_BOOST_CAP_GB, over)
    return ram_gb + boost


def _detect_gpu_torch_cuda() -> Tuple[Optional[str], Optional[float]]:
    try:
        import torch
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            vram = props.total_memory / (1024**3)
            return name, vram
    except ImportError:
        logger.debug("torch not available for GPU detection")
    except Exception as e:
        logger.debug("torch GPU detection failed: %s", e)
    return None, None


def _detect_gpu_nvidia_smi() -> Tuple[Optional[str], Optional[float]]:
    """Use nvidia-smi when NVIDIA drivers are installed (no PyTorch required)."""
    try:
        completed = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=_NVIDIA_SMI_TIMEOUT_SEC,
        )
        if completed.returncode != 0 or not (completed.stdout or "").strip():
            return None, None
        first = (completed.stdout or "").strip().splitlines()[0]
        parts = [p.strip() for p in first.split(",")]
        if len(parts) < 2:
            return None, None
        name, mem_raw = parts[0], parts[1]
        if not name:
            return None, None
        try:
            mem_mb = float(re.sub(r"[^\d.]", "", mem_raw) or 0.0)
        except ValueError:
            mem_mb = 0.0
        vram_gb = mem_mb / 1024.0 if mem_mb else None
        return name, vram_gb
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
        logger.debug("nvidia-smi GPU detection skipped or failed: %s", e)
    except Exception as e:
        logger.debug("nvidia-smi GPU detection failed: %s", e)
    return None, None


def _detect_gpu_wmi_windows() -> Tuple[Optional[str], Optional[float]]:
    """Fallback display adapter name on Windows (VRAM often unavailable)."""
    if platform.system() != "Windows":
        return None, None
    try:
        completed = subprocess.run(
            [
                "wmic",
                "path",
                "Win32_VideoController",
                "get",
                "Name",
                "/format:list",
            ],
            capture_output=True,
            text=True,
            timeout=_WMIC_TIMEOUT_SEC,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if completed.returncode != 0 or not (completed.stdout or "").strip():
            return None, None
        lines = [ln.strip() for ln in completed.stdout.splitlines() if ln.strip()]
        names: list[str] = []
        for ln in lines:
            if ln.startswith("Name="):
                val = ln.split("=", 1)[1].strip()
                if val:
                    names.append(val)
        if not names:
            return None, None
        # Prefer non-Generic/Microsoft Basic if multiple entries
        preferred = next((n for n in names if "basic" not in n.lower() and "microsoft" not in n.lower()), names[0])
        return preferred, None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as e:
        logger.debug("WMI GPU detection skipped or failed: %s", e)
    except Exception as e:
        logger.debug("WMI GPU detection failed: %s", e)
    return None, None


def _detect_gpu() -> Tuple[bool, Optional[float], Optional[str]]:
    """
    Try multiple strategies. Prefer concrete name + VRAM when available.
    Order: torch CUDA, nvidia-smi, Windows WMI (name only).
    """
    name, vram = _detect_gpu_torch_cuda()
    if name:
        return True, vram, name

    name, vram = _detect_gpu_nvidia_smi()
    if name:
        return True, vram, name

    name, _v = _detect_gpu_wmi_windows()
    if name:
        return True, vram, name

    return False, None, None


@dataclass
class HardwareProfile:
    """
    System hardware capabilities detected for model selection.

    Attributes:
        ram_total_gb: Total system RAM in gigabytes
        ram_available_gb: Currently available RAM in gigabytes
        cpu_cores: Number of CPU cores (logical)
        cpu_name: CPU model name if available
        disk_free_gb: Free disk space in the data directory
        gpu_available: Whether a GPU was detected (optional)
        gpu_vram_gb: GPU VRAM in gigabytes if detected
        gpu_name: GPU model name if detected
        recommended_tier: Highest tier the hardware can support
        max_supported_tier: Same as recommended_tier (for backwards compat)
        detection_timestamp: When detection was performed
    """

    ram_total_gb: float
    ram_available_gb: float
    cpu_cores: int
    cpu_name: Optional[str] = None
    disk_free_gb: float = 0.0

    # GPU is optional bonus (torch not in deps)
    gpu_available: bool = False
    gpu_vram_gb: Optional[float] = None
    gpu_name: Optional[str] = None

    # Computed recommendations
    recommended_tier: str = "low"
    max_supported_tier: str = "low"

    # Metadata
    detection_timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage."""
        return {
            "ram_total_gb": round(self.ram_total_gb, 2),
            "ram_available_gb": round(self.ram_available_gb, 2),
            "cpu_cores": self.cpu_cores,
            "cpu_name": self.cpu_name,
            "disk_free_gb": round(self.disk_free_gb, 2),
            "gpu_available": self.gpu_available,
            "gpu_vram_gb": self.gpu_vram_gb,
            "gpu_name": self.gpu_name,
            "recommended_tier": self.recommended_tier,
            "max_supported_tier": self.max_supported_tier,
            "detection_timestamp": self.detection_timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HardwareProfile":
        """Create from dictionary (JSON storage)."""
        timestamp = data.get("detection_timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.utcnow()

        return cls(
            ram_total_gb=data.get("ram_total_gb", 0),
            ram_available_gb=data.get("ram_available_gb", 0),
            cpu_cores=data.get("cpu_cores", 1),
            cpu_name=data.get("cpu_name"),
            disk_free_gb=data.get("disk_free_gb", 0),
            gpu_available=data.get("gpu_available", False),
            gpu_vram_gb=data.get("gpu_vram_gb"),
            gpu_name=data.get("gpu_name"),
            recommended_tier=data.get("recommended_tier", "low"),
            max_supported_tier=data.get("max_supported_tier", "low"),
            detection_timestamp=timestamp,
        )


def detect_hardware(models_path: Optional[str] = None) -> HardwareProfile:
    """
    Detect system hardware capabilities for model tier selection.

    Uses psutil for RAM/CPU/disk detection. GPU detection is attempted
    but not required (torch is not a dependency).

    Args:
        models_path: Path to models directory for disk space check.
                    Defaults to current working directory.

    Returns:
        HardwareProfile with detected capabilities and recommended tier.
    """
    # RAM detection
    mem = psutil.virtual_memory()
    ram_total_gb = mem.total / (1024**3)
    ram_available_gb = mem.available / (1024**3)

    # CPU detection
    cpu_cores = psutil.cpu_count(logical=True) or 1

    # Try to get CPU name
    cpu_name = None
    try:
        import cpuinfo
        info = cpuinfo.get_cpu_info()
        cpu_name = info.get("brand_raw") or info.get("brand")
    except Exception:
        pass

    # Disk space detection
    disk_free_gb = 0.0
    check_path = models_path or "."
    try:
        disk_usage = shutil.disk_usage(check_path)
        disk_free_gb = disk_usage.free / (1024**3)
    except Exception as e:
        logger.warning("Could not determine disk space: %s", e)

    gpu_available, gpu_vram_gb, gpu_name = _detect_gpu()

    recommended_tier = get_recommended_tier_from_hardware(
        ram_gb=ram_total_gb,
        disk_gb=disk_free_gb,
        gpu_vram_gb=gpu_vram_gb,
    )

    profile = HardwareProfile(
        ram_total_gb=ram_total_gb,
        ram_available_gb=ram_available_gb,
        cpu_cores=cpu_cores,
        cpu_name=cpu_name,
        disk_free_gb=disk_free_gb,
        gpu_available=gpu_available,
        gpu_vram_gb=gpu_vram_gb,
        gpu_name=gpu_name,
        recommended_tier=recommended_tier,
        max_supported_tier=recommended_tier,
        detection_timestamp=datetime.utcnow(),
    )

    logger.info(
        "Hardware detected: RAM=%.1fGB, CPU=%d cores, Disk=%.1fGB free, "
        "GPU=%s, Recommended tier=%s",
        ram_total_gb,
        cpu_cores,
        disk_free_gb,
        "Yes" if gpu_available else "No",
        recommended_tier,
    )

    return profile


def can_run_tier(profile: HardwareProfile, tier: str) -> bool:
    """
    Check if hardware supports a specific tier.

    Uses the same effective-RAM rules as recommended tier when GPU VRAM is known.
    """
    if tier not in TIER_REQUIREMENTS:
        return tier == "template"

    requirements = TIER_REQUIREMENTS[tier]
    effective_ram = _effective_ram_gb(profile.ram_total_gb, profile.gpu_vram_gb)
    ram_ok = effective_ram >= requirements["ram_gb"]
    disk_ok = profile.disk_free_gb >= requirements["disk_gb"]

    return ram_ok and disk_ok


def get_recommended_tier_from_hardware(
    ram_gb: float,
    disk_gb: float,
    gpu_vram_gb: Optional[float] = None,
) -> str:
    """
    Determine the recommended tier based on raw hardware values.

    Uses effective RAM (Physical RAM + capped VRAM boost when VRAM >= GPU_VRAM_BUMP_MIN_GB).
    Returns the highest tier that meets requirements.
    """
    effective_ram = _effective_ram_gb(ram_gb, gpu_vram_gb)

    for tier in TIER_ORDER:
        requirements = TIER_REQUIREMENTS[tier]
        if effective_ram >= requirements["ram_gb"] and disk_gb >= requirements["disk_gb"]:
            return tier

    return "low"


def get_recommended_tier(profile: HardwareProfile) -> str:
    """Return pre-computed recommended_tier from the profile."""
    return profile.recommended_tier


def get_tier_display_info(tier: str) -> dict:
    """
    Get display information for a tier.
    """
    info = {
        "low": {
            "name": "Tier 1: Low",
            "model": "Qwen2.5-0.5B-Instruct",
            "description": "Fast, lightweight model for basic interpretations",
            "requirements": TIER_REQUIREMENTS["low"],
        },
        "mid": {
            "name": "Tier 2: Mid",
            "model": "Phi-3-mini-4k-instruct",
            "description": "Balanced quality and performance",
            "requirements": TIER_REQUIREMENTS["mid"],
        },
        "high": {
            "name": "Tier 3: High",
            "model": "BioMistral-7B",
            "description": "Medical-specialized model for best accuracy",
            "requirements": TIER_REQUIREMENTS["high"],
        },
        "template": {
            "name": "Template Mode",
            "model": None,
            "description": "Template-based interpretations (no AI model)",
            "requirements": {"ram_gb": 0, "disk_gb": 0},
        },
    }
    return info.get(tier, info["template"])
