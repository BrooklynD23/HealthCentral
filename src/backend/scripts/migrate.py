#!/usr/bin/env python3
"""
CLI tool for running Alembic migrations.

Usage:
    python -m scripts.migrate master              # Run master DB migrations
    python -m scripts.migrate profile --profile-id <id> --password <pwd>
    python -m scripts.migrate status              # Show migration status

Examples:
    # Run master database migrations
    python -m scripts.migrate master

    # Run profile migrations (prompts for password if not provided)
    python -m scripts.migrate profile --profile-id abc123

    # Show current migration status
    python -m scripts.migrate status
"""

import argparse
import getpass
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import settings
from core.migrations import (
    run_master_migrations,
    run_profile_migration,
    get_master_current_revision,
    get_profile_current_revision,
)
from core.security import unseal_key_with_dpapi

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def cmd_master(args: argparse.Namespace) -> int:
    """Run master database migrations."""
    logger.info("Running master database migrations...")
    try:
        run_master_migrations()
        logger.info("Master migrations completed successfully.")
        return 0
    except Exception as e:
        logger.error(f"Master migration failed: {e}")
        return 1


def cmd_profile(args: argparse.Namespace) -> int:
    """Run profile database migrations."""
    profile_id = args.profile_id
    password = args.password

    if not password:
        password = getpass.getpass(f"Enter password for profile {profile_id}: ")

    # Get vault paths
    vault_dir = Path(settings.app_data_path) / "vaults" / profile_id
    vault_path = vault_dir / "vault.db"
    key_path = vault_dir / "key.bin"
    method_path = vault_dir / "key.method"

    if not key_path.exists():
        logger.error(f"Vault key not found at {key_path}")
        logger.error("Make sure the profile exists and has been set up.")
        return 1

    # Load and unseal the encryption key
    try:
        sealed_key = key_path.read_bytes()
        seal_method = method_path.read_text().strip() if method_path.exists() else "password"

        encryption_key = unseal_key_with_dpapi(
            sealed_key,
            seal_method,
            fallback_password=password,
        )
    except Exception as e:
        logger.error(f"Failed to unseal encryption key: {e}")
        return 1

    # Run migrations
    logger.info(f"Running profile database migrations for {profile_id}...")
    try:
        run_profile_migration(vault_path, encryption_key)
        logger.info("Profile migrations completed successfully.")
        return 0
    except Exception as e:
        logger.error(f"Profile migration failed: {e}")
        return 1


def cmd_status(args: argparse.Namespace) -> int:
    """Show migration status."""
    print("\n=== Migration Status ===\n")

    # Master database status
    try:
        master_rev = get_master_current_revision()
        master_db = Path(settings.app_data_path) / settings.master_db_filename
        print(f"Master Database: {master_db}")
        print(f"  Current revision: {master_rev or '(not initialized)'}")
        print(f"  Exists: {master_db.exists()}")
    except Exception as e:
        print(f"  Error checking master: {e}")

    # List profile vaults
    vaults_dir = Path(settings.app_data_path) / "vaults"
    if vaults_dir.exists():
        profiles = [d for d in vaults_dir.iterdir() if d.is_dir()]
        print(f"\nProfile Vaults: {len(profiles)} found")
        for profile_dir in profiles:
            vault_db = profile_dir / "vault.db"
            print(f"\n  Profile: {profile_dir.name}")
            print(f"    Vault DB exists: {vault_db.exists()}")
            print(f"    (Run 'migrate profile --profile-id {profile_dir.name}' to check/migrate)")
    else:
        print("\nProfile Vaults: (vaults directory not found)")

    print()
    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="HealthCentral database migration tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", help="Migration commands")

    # master command
    master_parser = subparsers.add_parser(
        "master",
        help="Run master database migrations",
    )
    master_parser.set_defaults(func=cmd_master)

    # profile command
    profile_parser = subparsers.add_parser(
        "profile",
        help="Run profile database migrations",
    )
    profile_parser.add_argument(
        "--profile-id",
        required=True,
        help="Profile UUID to migrate",
    )
    profile_parser.add_argument(
        "--password",
        help="Profile password (prompts if not provided)",
    )
    profile_parser.set_defaults(func=cmd_profile)

    # status command
    status_parser = subparsers.add_parser(
        "status",
        help="Show migration status",
    )
    status_parser.set_defaults(func=cmd_status)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
