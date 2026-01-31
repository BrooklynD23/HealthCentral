#!/usr/bin/env python3
"""
Hardware detection CLI tool.

Usage:
    python scripts/detect_hardware.py [--json]

Shows system hardware capabilities and recommended model tier.
"""

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.hardware_detection import (
    detect_hardware,
    can_run_tier,
    get_tier_display_info,
    TIER_REQUIREMENTS,
    TIER_ORDER,
)


def main():
    parser = argparse.ArgumentParser(
        description="Detect system hardware for model tier recommendation"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "--models-path",
        type=str,
        default="models/",
        help="Path to models directory (for disk space check)",
    )
    args = parser.parse_args()

    # Detect hardware
    profile = detect_hardware(args.models_path)

    if args.json:
        print(json.dumps(profile.to_dict(), indent=2))
        return

    # Human-readable output
    print("\n" + "=" * 60)
    print("  HealthCentral Hardware Detection")
    print("=" * 60)

    print("\n[System Information]")
    print(f"  CPU:              {profile.cpu_name or 'Unknown'}")
    print(f"  CPU Cores:        {profile.cpu_cores}")
    print(f"  RAM (Total):      {profile.ram_total_gb:.1f} GB")
    print(f"  RAM (Available):  {profile.ram_available_gb:.1f} GB")
    print(f"  Disk (Free):      {profile.disk_free_gb:.1f} GB")

    print("\n[GPU Information]")
    if profile.gpu_available:
        print(f"  GPU:              {profile.gpu_name or 'Unknown'}")
        print(f"  VRAM:             {profile.gpu_vram_gb:.1f} GB" if profile.gpu_vram_gb else "  VRAM:             Unknown")
    else:
        print("  GPU:              Not detected (optional)")

    print("\n[Tier Compatibility]")
    for tier in TIER_ORDER:
        can_run = can_run_tier(profile, tier)
        info = get_tier_display_info(tier)
        reqs = TIER_REQUIREMENTS[tier]
        status = "[OK]" if can_run else "[X] "
        print(f"  {status} {info['name']:20} - Requires {reqs['ram_gb']}GB RAM, {reqs['disk_gb']}GB disk")
        print(f"          Model: {info['model']}")

    print("\n[Recommendation]")
    print(f"  Recommended Tier: {profile.recommended_tier.upper()}")
    rec_info = get_tier_display_info(profile.recommended_tier)
    print(f"  Model:            {rec_info['model']}")
    print(f"  Description:      {rec_info['description']}")

    print("\n" + "=" * 60)
    print("  To download the recommended model:")
    print(f"    python scripts/model_manager.py download --tier {profile.recommended_tier}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
