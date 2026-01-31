"""
Hardware detection module for model tier selection.

Phase 0.3: Tiered Hardware Model System

Detects system capabilities (RAM, CPU, disk) to recommend appropriate
model tiers. GPU detection is optional - tiers are based primarily on RAM.
"""

import logging
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import psutil

logger = logging.getLogger(__name__)


# Tier requirements (RAM-based, GPU is bonus)
TIER_REQUIREMENTS: dict[str, dict[str, float]] = {
    "low": {"ram_gb": 8, "disk_gb": 1},      # Qwen 0.5B
    "mid": {"ram_gb": 16, "disk_gb": 3},     # Phi-3-mini
    "high": {"ram_gb": 32, "disk_gb": 5},    # BioMistral-7B
}

# Tier priority order (highest to lowest)
TIER_ORDER = ["high", "mid", "low"]


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
        # py-cpuinfo not available or failed
        pass

    # Disk space detection
    disk_free_gb = 0.0
    check_path = models_path or "."
    try:
        disk_usage = shutil.disk_usage(check_path)
        disk_free_gb = disk_usage.free / (1024**3)
    except Exception as e:
        logger.warning(f"Could not determine disk space: {e}")

    # GPU detection (optional - don't fail if not available)
    gpu_available = False
    gpu_vram_gb = None
    gpu_name = None

    try:
        # Try torch for GPU detection
        import torch
        if torch.cuda.is_available():
            gpu_available = True
            gpu_name = torch.cuda.get_device_name(0)
            # Get VRAM in GB
            props = torch.cuda.get_device_properties(0)
            gpu_vram_gb = props.total_memory / (1024**3)
    except ImportError:
        # torch not installed - GPU detection skipped
        logger.debug("torch not available, skipping GPU detection")
    except Exception as e:
        logger.debug(f"GPU detection failed: {e}")

    # Determine recommended tier
    recommended_tier = get_recommended_tier_from_hardware(
        ram_gb=ram_total_gb,
        disk_gb=disk_free_gb,
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
        f"Hardware detected: RAM={ram_total_gb:.1f}GB, "
        f"CPU={cpu_cores} cores, Disk={disk_free_gb:.1f}GB free, "
        f"GPU={'Yes' if gpu_available else 'No'}, "
        f"Recommended tier={recommended_tier}"
    )

    return profile


def can_run_tier(profile: HardwareProfile, tier: str) -> bool:
    """
    Check if hardware supports a specific tier.

    Args:
        profile: Hardware profile from detect_hardware()
        tier: Tier string ("low", "mid", "high")

    Returns:
        True if hardware meets tier requirements, False otherwise.
    """
    if tier not in TIER_REQUIREMENTS:
        return tier == "template"  # Template always works

    requirements = TIER_REQUIREMENTS[tier]
    ram_ok = profile.ram_total_gb >= requirements["ram_gb"]
    disk_ok = profile.disk_free_gb >= requirements["disk_gb"]

    return ram_ok and disk_ok


def get_recommended_tier_from_hardware(
    ram_gb: float,
    disk_gb: float,
) -> str:
    """
    Determine the recommended tier based on raw hardware values.

    Returns the highest tier that meets requirements.

    Args:
        ram_gb: Total RAM in gigabytes
        disk_gb: Free disk space in gigabytes

    Returns:
        Tier string: "high", "mid", or "low"
    """
    # Check tiers from highest to lowest
    for tier in TIER_ORDER:
        requirements = TIER_REQUIREMENTS[tier]
        if ram_gb >= requirements["ram_gb"] and disk_gb >= requirements["disk_gb"]:
            return tier

    # Default to low even if requirements not met
    # (system will use templates as fallback)
    return "low"


def get_recommended_tier(profile: HardwareProfile) -> str:
    """
    Get the recommended tier from an existing hardware profile.

    This is a convenience wrapper that returns the pre-computed
    recommended_tier from the profile.

    Args:
        profile: Hardware profile from detect_hardware()

    Returns:
        Tier string: "high", "mid", or "low"
    """
    return profile.recommended_tier


def get_tier_display_info(tier: str) -> dict:
    """
    Get display information for a tier.

    Args:
        tier: Tier string ("low", "mid", "high", "template")

    Returns:
        Dictionary with tier display information.
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
