#!/usr/bin/env python3
"""
scripts/download_models.py — Download GGUF models for HealthCentral.

Usage:
    # Download the recommended model for your hardware
    python scripts/download_models.py auto

    # Download a specific tier
    python scripts/download_models.py --tier gemma4-e4b
    python scripts/download_models.py --tier gemma4-12b
    python scripts/download_models.py --tier low

    # List available tiers and their download status
    python scripts/download_models.py list

    # Pull a model via Ollama instead of direct GGUF download
    python scripts/download_models.py ollama --tag gemma4:12b

This script is the canonical reference for Gemma 4 GGUF download URLs.

PLACEHOLDER NOTICE
==================
The Gemma 4 GGUF repos below were the expected canonical sources as of
2026-06-11.  Exact filenames may differ from what is discovered at runtime.
Before deploying, verify at:
  - https://huggingface.co/unsloth/gemma-4-e2b-it-GGUF
  - https://huggingface.co/unsloth/gemma-4-e4b-it-GGUF
  - https://huggingface.co/ggml-org/gemma-4-12b-it-GGUF

The downloader uses list_repo_files() at runtime to discover actual filenames,
so the script will work once the repo exists even if the filename differs from
the placeholder comment.

Python 3.10-compatible: no 3.11+ syntax.
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

# Allow running from repo root or scripts/ directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.hardware_detection import detect_hardware, TIER_REQUIREMENTS
from modules.model_selector import TIER_MODEL_CONFIG, ModelSelector, get_model_selector

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tier display info (augmented with Gemma 4 entries)
# ---------------------------------------------------------------------------

TIER_INFO: dict[str, dict] = {
    "low": {
        "label": "Tier: low  (Qwen2.5 0.5B)",
        "ram_gb": 8,
        "disk_gb": 1,
        "note": "CPU-only, fast, lightweight.",
    },
    "gemma4-e2b": {
        "label": "Tier: gemma4-e2b  (Gemma 4 E2B edge, ~1.5 GB Q4)",
        "ram_gb": 8,
        "disk_gb": 2,
        "note": "Multimodal, 256K ctx, Apache 2.0. Edge/phone-class hardware.",
        "ollama_tag": "gemma4:e2b",
        "placeholder": True,
    },
    "gemma4-e4b": {
        "label": "Tier: gemma4-e4b  (Gemma 4 E4B edge, ~2.8 GB Q4)",
        "ram_gb": 12,
        "disk_gb": 4,
        "note": "Multimodal, 256K ctx, Apache 2.0. Good mid-range laptop default.",
        "ollama_tag": "gemma4:e4b",
        "placeholder": True,
    },
    "mid": {
        "label": "Tier: mid  (Phi-3-mini 4k)",
        "ram_gb": 16,
        "disk_gb": 3,
        "note": "Balanced quality, 4K ctx.",
    },
    "gemma4-12b": {
        "label": "Tier: gemma4-12b  (Gemma 4 12B, ~7-8 GB Q4)",
        "ram_gb": 16,
        "disk_gb": 8,
        "note": "Multimodal, 256K ctx, Apache 2.0. Recommended for 16+ GB RAM.",
        "ollama_tag": "gemma4:12b",
        "placeholder": True,
    },
    "high": {
        "label": "Tier: high  (BioMistral-7B)",
        "ram_gb": 32,
        "disk_gb": 5,
        "note": "Medical-specialised, best accuracy.",
    },
}


def cmd_list(models_path: str) -> None:
    """List all tiers and whether they are already downloaded."""
    selector = ModelSelector(models_path)
    hardware = detect_hardware(models_path)

    print("\nAvailable model tiers:")
    print(f"  Detected hardware: {hardware.ram_total_gb:.0f} GB RAM, "
          f"{hardware.disk_free_gb:.0f} GB disk free")
    print(f"  Recommended tier: {hardware.recommended_tier}\n")

    for tier, info in TIER_INFO.items():
        downloaded = selector.is_model_available(tier)
        cfg = TIER_MODEL_CONFIG.get(tier, {})
        status = "[downloaded]" if downloaded else "[not downloaded]"
        placeholder = " [PLACEHOLDER URL - verify before use]" if info.get("placeholder") else ""
        print(f"  {info['label']}")
        print(f"    RAM: {info['ram_gb']} GB   Disk: {info['disk_gb']} GB   {status}{placeholder}")
        if cfg.get("ollama_tag"):
            print(f"    Ollama: ollama pull {cfg['ollama_tag']}")
        print(f"    {info['note']}")
        print()


def cmd_auto(models_path: str) -> None:
    """Download the hardware-recommended model."""
    hardware = detect_hardware(models_path)
    recommended = hardware.recommended_tier
    print(f"Hardware recommended tier: {recommended}")
    cmd_download(recommended, models_path)


def cmd_download(tier: str, models_path: str) -> None:
    """Download a specific tier's GGUF model."""
    if tier not in TIER_MODEL_CONFIG:
        print(f"ERROR: Unknown tier '{tier}'.  Run 'list' to see valid tiers.")
        sys.exit(1)

    cfg = TIER_MODEL_CONFIG[tier]
    if cfg.get("placeholder"):
        print(f"NOTE: {tier} has a placeholder repo URL.  Verify at "
              f"https://huggingface.co/{cfg['repo']} before use.")

    selector = ModelSelector(models_path)
    if selector.is_model_available(tier):
        path = selector.get_model_path(tier)
        print(f"Model for tier '{tier}' already downloaded: {path}")
        return

    print(f"Downloading tier '{tier}' from {cfg['repo']} ...")
    path = selector.download_model(tier)
    if path:
        print(f"Download complete: {path}")
    else:
        print(f"ERROR: Download failed for tier '{tier}'.")
        print(f"  Repo: {cfg['repo']}")
        print("  Check your internet connection and that the repo exists.")
        sys.exit(1)


def cmd_ollama(tag: str) -> None:
    """Pull a model from the Ollama library."""
    print(f"Pulling Ollama model: {tag}")
    try:
        subprocess.run(["ollama", "pull", tag], check=True)
        print(f"OK: ollama pull {tag} complete")
    except FileNotFoundError:
        print("ERROR: 'ollama' not found on PATH.  Install from https://ollama.com")
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: ollama pull failed with exit code {exc.returncode}")
        sys.exit(exc.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download GGUF models for HealthCentral",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--models-path",
        default="models/",
        help="Path to models directory (default: models/)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List available tiers and download status")

    sub.add_parser("auto", help="Download hardware-recommended tier")

    dl = sub.add_parser("download", help="Download a specific tier")
    dl.add_argument("--tier", required=True, help="Tier to download")

    ol = sub.add_parser("ollama", help="Pull a model via Ollama")
    ol.add_argument("--tag", required=True, help="Ollama model tag, e.g. gemma4:12b")

    args = parser.parse_args()

    if args.command == "list":
        cmd_list(args.models_path)
    elif args.command == "auto":
        cmd_auto(args.models_path)
    elif args.command == "download":
        cmd_download(args.tier, args.models_path)
    elif args.command == "ollama":
        cmd_ollama(args.tag)


if __name__ == "__main__":
    main()
