#!/usr/bin/env python3
"""
Model manager CLI tool.

Usage:
    python scripts/model_manager.py detect              # Hardware detection
    python scripts/model_manager.py list                # List downloaded models
    python scripts/model_manager.py download --tier low # Download a model
    python scripts/model_manager.py switch --tier mid   # Set active tier
    python scripts/model_manager.py cleanup             # Remove unused models

Manages model downloads, switching, and cleanup for the tiered model system.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.hardware_detection import detect_hardware, can_run_tier, get_tier_display_info
from modules.model_selector import (
    TIER_MODEL_CONFIG,
    ModelSelector,
    get_model_selector,
)


def cmd_detect(args):
    """Run hardware detection."""
    profile = detect_hardware(args.models_path)

    print("\n[Hardware Detection Results]")
    print(f"  RAM:              {profile.ram_total_gb:.1f} GB")
    print(f"  CPU Cores:        {profile.cpu_cores}")
    print(f"  Disk Free:        {profile.disk_free_gb:.1f} GB")
    print(f"  GPU:              {'Yes' if profile.gpu_available else 'No'}")
    print(f"  Recommended Tier: {profile.recommended_tier}")

    if args.json:
        print("\n[JSON Output]")
        print(json.dumps(profile.to_dict(), indent=2))


def cmd_list(args):
    """List downloaded models."""
    selector = ModelSelector(args.models_path)
    downloaded = selector.list_downloaded_models()

    print("\n[Downloaded Models]")
    if not downloaded:
        print("  No models downloaded yet.")
        print("\n  To download a model:")
        print("    python scripts/model_manager.py download --tier low")
    else:
        for tier, info in downloaded.items():
            print(f"\n  Tier: {tier.upper()}")
            print(f"    File:   {info['filename']}")
            print(f"    Size:   {info['size_gb']:.2f} GB")
            print(f"    Path:   {info['path']}")

    print("\n[Available Tiers]")
    for tier, config in TIER_MODEL_CONFIG.items():
        is_downloaded = tier in downloaded
        status = "[Downloaded]" if is_downloaded else "[Not Downloaded]"
        print(f"  {tier:6} - {config['description']:40} {status}")


def cmd_download(args):
    """Download a model."""
    tier = args.tier.lower()

    if tier not in TIER_MODEL_CONFIG:
        print(f"Error: Invalid tier '{tier}'. Valid options: {list(TIER_MODEL_CONFIG.keys())}")
        sys.exit(1)

    # Check hardware compatibility
    profile = detect_hardware(args.models_path)
    if not can_run_tier(profile, tier):
        print(f"\nWarning: Your hardware may not support tier '{tier}'.")
        print(f"  Recommended tier: {profile.recommended_tier}")
        if not args.force:
            response = input("Continue anyway? [y/N]: ")
            if response.lower() != 'y':
                print("Download cancelled.")
                sys.exit(0)

    config = TIER_MODEL_CONFIG[tier]
    repo = config["repo"]

    print(f"\n[Downloading Model]")
    print(f"  Tier:  {tier}")
    print(f"  Repo:  {repo}")

    try:
        from huggingface_hub import hf_hub_download, list_repo_files

        # Discover GGUF file if filename not specified
        filename = config.get("filename")
        if not filename:
            print(f"  Discovering GGUF files in {repo}...")
            files = list_repo_files(repo)
            gguf_files = [f for f in files if f.endswith(".gguf")]

            if not gguf_files:
                print(f"Error: No GGUF files found in {repo}")
                sys.exit(1)

            # Prefer Q4_K_M quantization
            pattern = config.get("filename_pattern", "q4_k_m").lower()
            matching = [f for f in gguf_files if pattern in f.lower()]

            if matching:
                filename = matching[0]
            else:
                # Fall back to first GGUF file
                filename = gguf_files[0]

            print(f"  Selected: {filename}")

        # Download
        models_dir = Path(args.models_path)
        models_dir.mkdir(parents=True, exist_ok=True)

        print(f"  Downloading to: {models_dir / filename}")
        print("  This may take a while...\n")

        # Use revision pinning for reproducible builds
        revision = config.get("revision", "main")
        local_path = hf_hub_download(
            repo_id=repo,
            filename=filename,
            revision=revision,
            local_dir=str(models_dir),
            local_dir_use_symlinks=False,
        )

        print(f"\n[Download Complete]")
        print(f"  Path: {local_path}")

        # Verify
        selector = ModelSelector(args.models_path)
        if selector.is_model_available(tier):
            print(f"  Status: Model verified and ready for tier '{tier}'")
        else:
            print(f"  Warning: Model downloaded but not detected for tier '{tier}'")

    except ImportError:
        print("Error: huggingface-hub not installed.")
        print("  Install with: pip install huggingface-hub")
        sys.exit(1)
    except Exception as e:
        print(f"Error downloading model: {e}")
        sys.exit(1)


def cmd_switch(args):
    """Switch active tier (preference only, no download)."""
    tier = args.tier.lower()

    if tier not in TIER_MODEL_CONFIG and tier != "template":
        print(f"Error: Invalid tier '{tier}'. Valid options: {list(TIER_MODEL_CONFIG.keys()) + ['template']}")
        sys.exit(1)

    selector = ModelSelector(args.models_path)

    if tier != "template" and not selector.is_model_available(tier):
        print(f"\nWarning: Model for tier '{tier}' is not downloaded.")
        print("  Download first with:")
        print(f"    python scripts/model_manager.py download --tier {tier}")
        if not args.force:
            sys.exit(1)

    # Note: This only prints the intended action
    # Actual preference saving requires database access via API
    print(f"\n[Tier Switch]")
    print(f"  New tier: {tier}")
    print(f"\n  Note: To persist this preference, use the API:")
    print(f"    POST /api/v1/settings/model/tier")
    print(f'    {{"tier": "{tier}"}}')

    info = get_tier_display_info(tier)
    print(f"\n  {info['name']}")
    print(f"  Model: {info['model'] or 'Template-based (no model)'}")
    print(f"  Description: {info['description']}")


def cmd_cleanup(args):
    """Remove unused model files."""
    models_dir = Path(args.models_path)

    if not models_dir.exists():
        print("Models directory does not exist.")
        return

    gguf_files = list(models_dir.glob("*.gguf"))

    if not gguf_files:
        print("No model files found to clean up.")
        return

    print("\n[Model Files Found]")
    total_size = 0
    for f in gguf_files:
        size_gb = f.stat().st_size / (1024**3)
        total_size += size_gb
        print(f"  {f.name}: {size_gb:.2f} GB")

    print(f"\n  Total: {total_size:.2f} GB")

    if args.dry_run:
        print("\n  [Dry run - no files deleted]")
        return

    response = input("\nDelete all model files? [y/N]: ")
    if response.lower() == 'y':
        for f in gguf_files:
            f.unlink()
            print(f"  Deleted: {f.name}")
        print("\nCleanup complete.")
    else:
        print("Cleanup cancelled.")


def main():
    parser = argparse.ArgumentParser(
        description="Model manager for Asclexis tiered model system"
    )
    parser.add_argument(
        "--models-path",
        type=str,
        default="models/",
        help="Path to models directory",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # detect command
    detect_parser = subparsers.add_parser("detect", help="Detect hardware capabilities")
    detect_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # list command
    list_parser = subparsers.add_parser("list", help="List downloaded models")

    # download command
    download_parser = subparsers.add_parser("download", help="Download a model")
    download_parser.add_argument(
        "--tier",
        type=str,
        required=True,
        choices=list(TIER_MODEL_CONFIG.keys()),
        help="Tier to download",
    )
    download_parser.add_argument(
        "--force",
        action="store_true",
        help="Force download even if hardware insufficient",
    )

    # switch command
    switch_parser = subparsers.add_parser("switch", help="Switch active tier")
    switch_parser.add_argument(
        "--tier",
        type=str,
        required=True,
        help="Tier to switch to",
    )
    switch_parser.add_argument(
        "--force",
        action="store_true",
        help="Switch even if model not downloaded",
    )

    # cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Remove model files")
    cleanup_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without deleting",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "detect": cmd_detect,
        "list": cmd_list,
        "download": cmd_download,
        "switch": cmd_switch,
        "cleanup": cmd_cleanup,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
