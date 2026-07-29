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

from core.time import utcnow

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


def _validate_manifest_path(base_dir: Path, relative_path: str) -> Path:
    """
    Validate a relative path from a backup manifest against path traversal.

    Args:
        base_dir: The trusted base directory.
        relative_path: The path string read from the manifest.

    Returns:
        Resolved absolute path guaranteed to be under base_dir.

    Raises:
        ValueError: If the path is absolute, contains '..' components, or
                    resolves outside base_dir.
    """
    # Reject absolute paths (Unix and Windows drive letters)
    if relative_path.startswith("/") or relative_path.startswith("\\"):
        raise ValueError(
            f"Manifest contains absolute path: {relative_path}"
        )
    if len(relative_path) >= 2 and relative_path[1] == ":":
        raise ValueError(
            f"Manifest contains absolute Windows path: {relative_path}"
        )

    # Reject any '..' components
    parts = Path(relative_path).parts
    if ".." in parts:
        raise ValueError(
            f"Manifest contains path traversal: {relative_path}"
        )

    # Reject null bytes
    if "\x00" in relative_path:
        raise ValueError(
            f"Manifest path contains null byte: {relative_path!r}"
        )

    # Resolve and confirm it stays under base_dir
    resolved = (base_dir / relative_path).resolve()
    base_resolved = base_dir.resolve()
    try:
        resolved.relative_to(base_resolved)
    except ValueError:
        raise ValueError(
            f"Manifest path escapes base directory: {relative_path}"
        )

    return resolved


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
    """Discover all database files in the data directory.

    Profile vaults live at ``vaults/{profile_id}/vault.db`` — one directory per
    profile — so this must recurse. A flat ``vaults/*.db`` glob matches nothing
    and silently produces a backup containing only the master database, i.e.
    no patient health data at all.
    """
    dbs: list[Path] = []

    # Master database
    master_db = data_dir / "healthcentral.db"
    if master_db.exists():
        dbs.append(master_db)

    # Profile vault databases (one per profile subdirectory)
    vaults_dir = data_dir / "vaults"
    if vaults_dir.exists():
        for db_file in sorted(vaults_dir.rglob("*.db")):
            dbs.append(db_file)

    return dbs


def _discover_key_files(data_dir: Path) -> list[Path]:
    """Discover the sealed key files that make the vault databases readable.

    A vault database without its sealed key is ciphertext with no way in, so a
    backup that omits these restores nothing usable. Both the password-sealed
    primary key and the recovery-sealed copy (SEC-RECOV-001) are included —
    omitting the recovery copy would silently break recovery after a restore.

    These files are sealed, not plaintext: the primary needs the profile
    password and the recovery copy needs the recovery code. The backup is
    therefore no more sensitive than the vault it accompanies — but it does
    mean a backup plus a known password is full access, which is exactly what
    "restore" has to mean.
    """
    key_files: list[Path] = []
    vaults_dir = data_dir / "vaults"
    if not vaults_dir.exists():
        return key_files

    for profile_dir in sorted(p for p in vaults_dir.iterdir() if p.is_dir()):
        for name in ("key.bin", "key.method", "key.recovery.bin", "key.recovery.method"):
            candidate = profile_dir / name
            if candidate.exists():
                key_files.append(candidate)
    return key_files


def backup(
    data_dir: Path,
    backup_dir: Path,
    profile_id: str | None = None,
) -> BackupResult:
    """
    Create a timestamped backup of all databases.

    Uses SQLite's backup() API for consistent online snapshots.
    """
    if not data_dir.exists():
        raise FileNotFoundError(f"Data directory not found: {data_dir}")
    if not data_dir.is_dir():
        raise NotADirectoryError(f"Data directory is not a directory: {data_dir}")

    timestamp = utcnow().strftime("%Y%m%d_%H%M%S")
    dest_dir = backup_dir / f"backup_{timestamp}"
    dest_dir.mkdir(parents=True, exist_ok=True)

    databases = _discover_databases(data_dir)

    key_files = _discover_key_files(data_dir)

    if profile_id:
        # Vaults are directories named by profile id, so match on the parent.
        databases = [
            db for db in databases
            if db.name == "healthcentral.db" or db.parent.name == profile_id
        ]
        key_files = [k for k in key_files if k.parent.name == profile_id]

    if not databases and not key_files:
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

    # Sealed key files are copied verbatim -- they are opaque blobs, not
    # SQLite databases, so the backup API does not apply.
    for key_path in key_files:
        rel_path = key_path.relative_to(data_dir)
        dest_file = dest_dir / rel_path
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(key_path, dest_file)
        manifest_files.append({
            "path": str(rel_path),
            "sha256": _compute_sha256(dest_file),
            "size_bytes": dest_file.stat().st_size,
            "method": "file_copy",
        })

    manifest = {
        "timestamp": timestamp,
        "created_at": utcnow().isoformat() + "Z",
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
        files_checked += 1

        try:
            file_path = _validate_manifest_path(backup_path, entry["path"])
        except ValueError as e:
            errors.append(str(e))
            continue

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
        try:
            src_file = _validate_manifest_path(backup_path, entry["path"])
            dest_file = _validate_manifest_path(data_dir, entry["path"])
        except ValueError as e:
            return RestoreResult(
                success=False,
                files_restored=files_restored,
                safety_copies=safety_copies,
                error=f"Path validation failed: {e}",
            )

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
    cutoff = utcnow() - timedelta(days=retention_days)
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
