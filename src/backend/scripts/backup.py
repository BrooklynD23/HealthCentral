"""
Backup and recovery utility for HealthCentral databases.

Uses SQLite's built-in backup() API for consistent online snapshots.
Supports backup, verify, restore, and prune operations.

Usage:
    python scripts/backup.py --action backup --data-dir data/ --backup-dir backups/
    python scripts/backup.py --action verify --backup-dir backups/
    python scripts/backup.py --action restore --backup-dir backups/ --data-dir data/
    python scripts/backup.py --action prune --backup-dir backups/ --retention-days 30
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import shutil
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

APP_VERSION = "0.1.0"


@dataclass(frozen=True)
class BackupResult:
    """Result of a backup operation."""
    success: bool
    backup_path: Path
    files_backed_up: int
    manifest_path: Path
    method: str
    error: str = ""


@dataclass(frozen=True)
class VerifyResult:
    """Result of a verify operation."""
    valid: bool
    files_checked: int
    errors: list[str]


@dataclass(frozen=True)
class RestoreResult:
    """Result of a restore operation."""
    success: bool
    files_restored: int
    safety_copies: list[Path]
    error: str = ""


def _compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _backup_sqlite(source: Path, dest: Path) -> str:
    """
    Backup a SQLite database using the backup() API.

    Returns the backup method used ('sqlite_backup' or 'file_copy').
    """
    try:
        src_conn = sqlite3.connect(str(source))
        dst_conn = sqlite3.connect(str(dest))
        src_conn.backup(dst_conn)
        dst_conn.close()
        src_conn.close()
        return "sqlite_backup"
    except Exception as e:
        logger.warning(
            "SQLite backup API failed for %s, falling back to file copy: %s",
            source, e,
        )
        shutil.copy2(source, dest)
        return "file_copy"


def _discover_databases(data_dir: Path) -> list[Path]:
    """Discover all database files in the data directory."""
    dbs: list[Path] = []

    # Master database
    master_db = data_dir / "healthcentral.db"
    if master_db.exists():
        dbs.append(master_db)

    # Profile vault databases
    vaults_dir = data_dir / "vaults"
    if vaults_dir.exists():
        for db_file in sorted(vaults_dir.glob("*.db")):
            dbs.append(db_file)

    return dbs


def backup(
    data_dir: Path,
    backup_dir: Path,
    profile_id: str | None = None,
) -> BackupResult:
    """
    Create a timestamped backup of all databases.

    Uses SQLite's backup() API for consistent online snapshots.
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dest_dir = backup_dir / f"backup_{timestamp}"
    dest_dir.mkdir(parents=True, exist_ok=True)

    databases = _discover_databases(data_dir)

    if profile_id:
        vault_name = f"{profile_id}.db"
        databases = [
            db for db in databases
            if db.name == "healthcentral.db" or db.name == vault_name
        ]

    if not databases:
        return BackupResult(
            success=True,
            backup_path=dest_dir,
            files_backed_up=0,
            manifest_path=dest_dir / "manifest.json",
            method="none",
        )

    manifest_files: list[dict] = []
    backup_method = "sqlite_backup"

    for db_path in databases:
        # Preserve relative structure
        rel_path = db_path.relative_to(data_dir)
        dest_file = dest_dir / rel_path
        dest_file.parent.mkdir(parents=True, exist_ok=True)

        method = _backup_sqlite(db_path, dest_file)
        if method == "file_copy":
            backup_method = "file_copy"

        checksum = _compute_sha256(dest_file)
        manifest_files.append({
            "path": str(rel_path),
            "sha256": checksum,
            "size_bytes": dest_file.stat().st_size,
            "method": method,
        })

    manifest = {
        "timestamp": timestamp,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "app_version": APP_VERSION,
        "backup_method": backup_method,
        "files": manifest_files,
    }

    manifest_path = dest_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    logger.info(
        "Backup complete: %d files to %s",
        len(manifest_files), dest_dir,
    )

    return BackupResult(
        success=True,
        backup_path=dest_dir,
        files_backed_up=len(manifest_files),
        manifest_path=manifest_path,
        method=backup_method,
    )


def verify(backup_path: Path) -> VerifyResult:
    """
    Verify a backup's integrity using SHA-256 checksums.

    Checks that all files listed in manifest.json exist and match.
    """
    manifest_path = backup_path / "manifest.json"
    if not manifest_path.exists():
        return VerifyResult(
            valid=False,
            files_checked=0,
            errors=["manifest.json not found"],
        )

    manifest = json.loads(manifest_path.read_text())
    errors: list[str] = []
    files_checked = 0

    for entry in manifest.get("files", []):
        file_path = backup_path / entry["path"]
        files_checked += 1

        if not file_path.exists():
            errors.append(f"Missing file: {entry['path']}")
            continue

        actual_hash = _compute_sha256(file_path)
        if actual_hash != entry["sha256"]:
            errors.append(
                f"Checksum mismatch: {entry['path']} "
                f"(expected {entry['sha256'][:16]}..., got {actual_hash[:16]}...)"
            )

    return VerifyResult(
        valid=len(errors) == 0,
        files_checked=files_checked,
        errors=errors,
    )


def restore(backup_path: Path, data_dir: Path) -> RestoreResult:
    """
    Restore databases from a backup.

    Creates .bak safety copies of existing files before overwriting.
    """
    # Verify first
    verify_result = verify(backup_path)
    if not verify_result.valid:
        return RestoreResult(
            success=False,
            files_restored=0,
            safety_copies=[],
            error=f"Backup verification failed: {'; '.join(verify_result.errors)}",
        )

    manifest = json.loads((backup_path / "manifest.json").read_text())
    safety_copies: list[Path] = []
    files_restored = 0

    for entry in manifest.get("files", []):
        src_file = backup_path / entry["path"]
        dest_file = data_dir / entry["path"]

        # Create safety copy of existing file
        if dest_file.exists():
            bak_path = dest_file.with_suffix(dest_file.suffix + ".bak")
            shutil.copy2(dest_file, bak_path)
            safety_copies.append(bak_path)

        dest_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_file, dest_file)
        files_restored += 1

    logger.info(
        "Restore complete: %d files from %s",
        files_restored, backup_path,
    )

    return RestoreResult(
        success=True,
        files_restored=files_restored,
        safety_copies=safety_copies,
    )


def prune(backup_dir: Path, retention_days: int = 30) -> int:
    """
    Remove backups older than retention_days.

    Returns the number of backup directories removed.
    """
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    removed = 0

    for entry in sorted(backup_dir.iterdir()):
        if not entry.is_dir() or not entry.name.startswith("backup_"):
            continue

        manifest_path = entry / "manifest.json"
        if not manifest_path.exists():
            continue

        try:
            manifest = json.loads(manifest_path.read_text())
            created_str = manifest.get("created_at", "")
            created = datetime.fromisoformat(created_str.rstrip("Z"))
            if created < cutoff:
                shutil.rmtree(entry)
                removed += 1
                logger.info("Pruned old backup: %s", entry.name)
        except (json.JSONDecodeError, ValueError, OSError) as e:
            logger.warning("Skipping %s during prune: %s", entry.name, e)

    return removed


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="HealthCentral backup and recovery utility"
    )
    parser.add_argument(
        "--action",
        choices=["backup", "verify", "restore", "prune"],
        required=True,
        help="Action to perform",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Data directory (default: data/)",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path("backups"),
        help="Backup directory (default: backups/)",
    )
    parser.add_argument(
        "--profile-id",
        type=str,
        default=None,
        help="Backup specific profile only",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=30,
        help="Retention period for prune (default: 30 days)",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if args.action == "backup":
        if not args.data_dir.exists():
            print(f"Error: Data directory '{args.data_dir}' does not exist")
            sys.exit(1)
        result = backup(args.data_dir, args.backup_dir, args.profile_id)
        print(f"Backup: {result.files_backed_up} files -> {result.backup_path}")
        print(f"Method: {result.method}")

    elif args.action == "verify":
        # Find latest backup
        backups = sorted(
            [d for d in args.backup_dir.iterdir() if d.is_dir()],
            reverse=True,
        )
        if not backups:
            print("No backups found")
            sys.exit(1)
        result = verify(backups[0])
        print(f"Verify: {'VALID' if result.valid else 'INVALID'}")
        print(f"Files checked: {result.files_checked}")
        for err in result.errors:
            print(f"  ERROR: {err}")
        sys.exit(0 if result.valid else 1)

    elif args.action == "restore":
        backups = sorted(
            [d for d in args.backup_dir.iterdir() if d.is_dir()],
            reverse=True,
        )
        if not backups:
            print("No backups found")
            sys.exit(1)
        result = restore(backups[0], args.data_dir)
        if result.success:
            print(f"Restore: {result.files_restored} files restored")
            for bak in result.safety_copies:
                print(f"  Safety copy: {bak}")
        else:
            print(f"Restore failed: {result.error}")
            sys.exit(1)

    elif args.action == "prune":
        removed = prune(args.backup_dir, args.retention_days)
        print(f"Pruned {removed} old backup(s)")


if __name__ == "__main__":
    main()
