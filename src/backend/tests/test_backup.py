"""Tests for backup and recovery utility."""

import json
import sqlite3
from pathlib import Path

import pytest

from scripts.backup import (
    backup,
    verify,
    restore,
    prune,
    _compute_sha256,
    BackupResult,
    VerifyResult,
    RestoreResult,
)


@pytest.fixture
def data_dir(tmp_path):
    """Create a data directory with test databases."""
    d = tmp_path / "data"
    d.mkdir()

    # Create master database
    master_db = d / "healthcentral.db"
    conn = sqlite3.connect(str(master_db))
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
    conn.execute("INSERT INTO test VALUES (1, 'hello')")
    conn.commit()
    conn.close()

    # Create vault database
    vaults = d / "vaults"
    vaults.mkdir()
    vault_db = vaults / "profile-123.db"
    conn = sqlite3.connect(str(vault_db))
    conn.execute("CREATE TABLE records (id INTEGER PRIMARY KEY)")
    conn.execute("INSERT INTO records VALUES (1)")
    conn.commit()
    conn.close()

    return d


@pytest.fixture
def backup_dir(tmp_path):
    """Create a backup directory."""
    b = tmp_path / "backups"
    b.mkdir()
    return b


class TestBackup:
    def test_creates_timestamped_dir(self, data_dir, backup_dir):
        """Backup creates a timestamped directory."""
        result = backup(data_dir, backup_dir)
        assert result.success
        assert result.backup_path.exists()
        assert result.backup_path.name.startswith("backup_")

    def test_uses_sqlite_backup_api(self, data_dir, backup_dir):
        """Backup uses sqlite3 backup() API."""
        result = backup(data_dir, backup_dir)
        assert result.method == "sqlite_backup"

    def test_generates_manifest(self, data_dir, backup_dir):
        """Backup generates manifest.json with checksums."""
        result = backup(data_dir, backup_dir)
        manifest = json.loads(result.manifest_path.read_text())
        assert "timestamp" in manifest
        assert "app_version" in manifest
        assert "files" in manifest
        assert len(manifest["files"]) == 2  # master + vault
        for entry in manifest["files"]:
            assert "sha256" in entry
            assert "path" in entry
            assert "method" in entry

    def test_backup_specific_profile(self, data_dir, backup_dir):
        """Backup with profile_id only includes master + that profile."""
        result = backup(data_dir, backup_dir, profile_id="profile-123")
        assert result.files_backed_up == 2  # master + profile-123.db

    def test_empty_data_dir_succeeds(self, tmp_path, backup_dir):
        """Backup of empty data dir succeeds with 0 files."""
        empty_dir = tmp_path / "empty_data"
        empty_dir.mkdir()
        result = backup(empty_dir, backup_dir)
        assert result.success
        assert result.files_backed_up == 0

    def test_nonexistent_source_raises(self, backup_dir):
        """Backup of nonexistent directory raises."""
        with pytest.raises(Exception):
            backup(Path("/nonexistent/dir"), backup_dir)


class TestVerify:
    def test_valid_backup_verifies(self, data_dir, backup_dir):
        """Valid backup passes verification."""
        backup(data_dir, backup_dir)
        backup_path = sorted(backup_dir.iterdir())[-1]
        result = verify(backup_path)
        assert result.valid
        assert result.files_checked == 2

    def test_corrupted_file_detected(self, data_dir, backup_dir):
        """Corrupted file is detected by checksum."""
        backup(data_dir, backup_dir)
        backup_path = sorted(backup_dir.iterdir())[-1]

        # Corrupt a file
        for db_file in backup_path.rglob("*.db"):
            db_file.write_bytes(b"corrupted data")
            break

        result = verify(backup_path)
        assert not result.valid
        assert len(result.errors) > 0
        assert "checksum" in result.errors[0].lower() or "mismatch" in result.errors[0].lower()

    def test_missing_file_detected(self, data_dir, backup_dir):
        """Missing file is detected by verification."""
        backup(data_dir, backup_dir)
        backup_path = sorted(backup_dir.iterdir())[-1]

        # Delete a file
        for db_file in backup_path.rglob("*.db"):
            db_file.unlink()
            break

        result = verify(backup_path)
        assert not result.valid
        assert any("missing" in e.lower() for e in result.errors)

    def test_missing_manifest_fails(self, tmp_path):
        """Verification fails if manifest.json missing."""
        empty_backup = tmp_path / "no_manifest"
        empty_backup.mkdir()
        result = verify(empty_backup)
        assert not result.valid
        assert "manifest" in result.errors[0].lower()


class TestRestore:
    def test_restore_copies_files(self, data_dir, backup_dir, tmp_path):
        """Restore copies files to destination."""
        backup(data_dir, backup_dir)
        backup_path = sorted(backup_dir.iterdir())[-1]

        restore_dir = tmp_path / "restored"
        restore_dir.mkdir()
        result = restore(backup_path, restore_dir)
        assert result.success
        assert result.files_restored == 2
        assert (restore_dir / "healthcentral.db").exists()

    def test_restore_creates_bak(self, data_dir, backup_dir):
        """Restore creates .bak of existing files."""
        backup(data_dir, backup_dir)
        backup_path = sorted(backup_dir.iterdir())[-1]

        # Restore over existing data
        result = restore(backup_path, data_dir)
        assert result.success
        assert len(result.safety_copies) > 0
        assert any(p.suffix == ".bak" for p in result.safety_copies)

    def test_restore_invalid_backup_raises(self, data_dir, backup_dir, tmp_path):
        """Restore of invalid backup returns failure."""
        backup(data_dir, backup_dir)
        backup_path = sorted(backup_dir.iterdir())[-1]

        # Corrupt a file
        for db_file in backup_path.rglob("*.db"):
            db_file.write_bytes(b"corrupted")
            break

        restore_dir = tmp_path / "restore_target"
        restore_dir.mkdir()
        result = restore(backup_path, restore_dir)
        assert not result.success
        assert "verification failed" in result.error.lower()


class TestPrune:
    def test_prune_removes_old_dirs(self, data_dir, backup_dir):
        """Prune removes backups older than retention period."""
        # Create a backup
        result = backup(data_dir, backup_dir)

        # Modify manifest to look old
        manifest_path = result.manifest_path
        manifest = json.loads(manifest_path.read_text())
        manifest["created_at"] = "2020-01-01T00:00:00Z"
        manifest_path.write_text(json.dumps(manifest))

        removed = prune(backup_dir, retention_days=30)
        assert removed == 1
        assert not result.backup_path.exists()
