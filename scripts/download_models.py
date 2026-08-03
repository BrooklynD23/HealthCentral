#!/usr/bin/env python3
"""
Model Download Script for HealthCentral

Downloads LLM models from Hugging Face for local inference.

Usage:
    python scripts/download_models.py              # Download recommended model
    python scripts/download_models.py --tier low   # Download specific tier
    python scripts/download_models.py --tier mid
    python scripts/download_models.py --tier high
    python scripts/download_models.py --list       # List downloaded models
"""

import argparse
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "backend"))


def main():
    parser = argparse.ArgumentParser(
        description="Download LLM models for Asclexis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Model Tiers:
  low   - Qwen2.5-0.5B (~350MB) - Fast, lightweight, good for basic tasks
  mid   - Phi-3-mini (~2.3GB)   - Balanced quality and speed
  high  - BioMistral-7B (~4GB)  - Medical-specialized, highest quality

Examples:
  python scripts/download_models.py              # Download 'low' tier (recommended for first use)
  python scripts/download_models.py --tier mid   # Download 'mid' tier
  python scripts/download_models.py --list       # Show downloaded models
        """,
    )
    parser.add_argument(
        "--tier",
        choices=["low", "mid", "high"],
        default="low",
        help="Model tier to download (default: low)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List downloaded models and exit",
    )
    parser.add_argument(
        "--models-path",
        type=str,
        default=None,
        help="Path to models directory (default: models/)",
    )

    args = parser.parse_args()

    # Import after path setup
    from modules.model_selector import ModelSelector, TIER_MODEL_CONFIG

    selector = ModelSelector(models_path=args.models_path)

    if args.list:
        print("\n=== Downloaded Models ===\n")
        downloaded = selector.list_downloaded_models()

        if not downloaded:
            print("No models downloaded yet.")
            print("\nRun 'python scripts/download_models.py' to download the recommended model.")
        else:
            for tier, info in downloaded.items():
                print(f"  [{tier.upper()}] {info['filename']}")
                print(f"         Size: {info['size_gb']} GB")
                print(f"         Path: {info['path']}")
                print(f"         {info['description']}")
                print()

        print("\n=== Available Tiers ===\n")
        for tier, config in TIER_MODEL_CONFIG.items():
            available = "✓ Downloaded" if tier in downloaded else "○ Not downloaded"
            print(f"  {tier.upper():5} - {config['description']}")
            print(f"         Repo: {config['repo']}")
            print(f"         Status: {available}")
            print()

        return

    # Download the model
    tier = args.tier
    config = TIER_MODEL_CONFIG.get(tier)

    print(f"\n=== Downloading {tier.upper()} Tier Model ===\n")
    print(f"  Description: {config['description']}")
    print(f"  Repository:  {config['repo']}")
    print(f"  Destination: {selector.models_path}")
    print()

    # Check if already downloaded
    if selector.is_model_available(tier):
        existing = selector.get_model_path(tier)
        print(f"Model already downloaded: {existing}")
        print("Use --list to see all models, or delete the file to re-download.")
        return

    print("Downloading... (this may take a while)")
    print()

    result = selector.download_model(tier)

    if result:
        size_gb = result.stat().st_size / (1024**3)
        print(f"\n✓ Download complete!")
        print(f"  File: {result}")
        print(f"  Size: {size_gb:.2f} GB")
        print("\nThe model will be loaded automatically when you use the assistant.")
    else:
        print("\n✗ Download failed. Please check your internet connection.")
        print("  You can also manually download a GGUF model and place it in the models/ directory.")
        sys.exit(1)


if __name__ == "__main__":
    main()
