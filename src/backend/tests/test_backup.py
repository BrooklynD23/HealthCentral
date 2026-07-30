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

    # Create vault database. The real on-disk layout is one directory per
    # profile: vaults/{profile_id}/vault.db, alongside its sealed key files.
    # This fixture previously used a flat vaults/{profile_id}.db, which matched
    # the (broken) flat glob in backup.py and hid the fact that profile data
    # was never actually being backed up.
    vault_dir = d / "vaults" / "profile-123"
    vault_dir.mkdir(parents=True)
    vault_db = vault_dir / "vault.db"
    conn = sqlite3.connect(str(vault_db))
    conn.execute("CREATE TABLE records (id INTEGER PRIMARY KEY)")
    conn.execute("INSERT INTO records VALUES (1)")
    conn.commit()
    conn.close()

    # Sealed key files — without these a restored vault is unopenable.
    (vault_dir / "key.bin").write_bytes(b"sealed-primary")
    (vault_dir / "key.method").write_text("password")

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
        # master DB + vault DB + the two sealed key files
        assert len(manifest["files"]) == 4
        for entry in manifest["files"]:
            assert "sha256" in entry
            assert "path" in entry
            assert "method" in entry

    def test_backup_specific_profile(self, data_dir, backup_dir):
        """Backup with profile_id only includes master + that profile."""
        result = backup(data_dir, backup_dir, profile_id="profile-123")
        # master DB + the profile vault DB + its two sealed key files
        assert result.files_backed_up == 4

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
        assert result.files_checked == 4

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
        assert result.files_restored == 4
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


def test_hc_bkup_037_partial_restore_is_reported_as_partial(tmp_path, monkeypatch):
    """A reconciliation failure happens *after* the vault and both sealed keys
    are replaced. Reporting success=False makes the API and UI say "Nothing was
    changed", which is false and leaves the user unable to reason about state."""
    import sqlite3
    from scripts import backup as backup_script

    data_dir = tmp_path / "data"
    vault = data_dir / "vaults" / "profile-a"
    vault.mkdir(parents=True)
    conn = sqlite3.connect(vault / "vault.db")
    conn.execute("CREATE TABLE observations (id TEXT)")
    conn.commit()
    conn.close()
    (vault / "key.bin").write_bytes(b"sealed")
    (vault / "key.method").write_text("password")

    master = data_dir / "healthcentral.db"
    conn = sqlite3.connect(master)
    conn.execute("CREATE TABLE profiles (id TEXT, display_name TEXT)")
    conn.execute("INSERT INTO profiles VALUES ('profile-a', 'Ann')")
    conn.commit()
    conn.close()

    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    created = backup_script.backup(
        data_dir=data_dir, backup_dir=backup_dir, profile_id="profile-a"
    )

    def _boom(*args, **kwargs):
        raise sqlite3.Error("simulated reconciliation failure")

    monkeypatch.setattr(backup_script, "_reapply_profile_row", _boom)

    result = backup_script.restore(
        created.backup_path, data_dir, profile_id="profile-a"
    )

    assert result.success is False
    assert result.partial is True, (
        "files were already replaced, so this is a partial restore — reporting "
        "it as a clean failure tells the user nothing changed, which is false"
    )
    assert result.files_restored > 0
    assert result.safety_copies, "the .bak copies must be named so recovery is possible"


def test_hc_bkup_039_midloop_path_failure_after_a_copy_is_partial(tmp_path):
    """The *other* post-copy return path: a manifest path that fails validation
    against the destination, part-way through the copy loop.

    HC-BKUP-037 covered the reconciliation failure. This one is the return
    inside the copy loop itself. On a full-install restore the master DB is
    copied first, so a validation failure on a later entry leaves real files
    already replaced — yet the result reported `partial=False`, which the API
    turns into "nothing was changed". Reproduced here with a `vaults` symlink
    in the destination that resolves outside the data directory (a plausible
    "put the vaults on another disk" layout), so the destination-side
    validation fails while the backup-side one succeeds.
    """
    from scripts import backup as backup_script

    data_dir = tmp_path / "data"
    vault = data_dir / "vaults" / "profile-a"
    vault.mkdir(parents=True)
    conn = sqlite3.connect(vault / "vault.db")
    conn.execute("CREATE TABLE observations (id TEXT)")
    conn.commit()
    conn.close()
    (vault / "key.bin").write_bytes(b"sealed")
    (vault / "key.method").write_text("password")

    master = data_dir / "healthcentral.db"
    conn = sqlite3.connect(master)
    conn.execute("CREATE TABLE profiles (id TEXT)")
    conn.commit()
    conn.close()

    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    created = backup_script.backup(data_dir=data_dir, backup_dir=backup_dir)

    # Destination: master DB present (so it copies), `vaults` a symlink that
    # escapes the destination root (so the next entry fails validation).
    target = tmp_path / "target"
    target.mkdir()
    (target / "healthcentral.db").write_bytes(b"live-master")
    outside = tmp_path / "elsewhere" / "vaults"
    outside.mkdir(parents=True)
    (target / "vaults").symlink_to(outside, target_is_directory=True)

    result = backup_script.restore(created.backup_path, target)

    assert result.success is False
    assert "path validation failed" in result.error.lower()
    assert result.files_restored > 0, "the master DB should already have been copied"
    assert result.partial is True, (
        "files were already replaced before validation failed, so the API must "
        "not tell the user nothing was changed"
    )


def test_hc_bkup_039b_first_entry_path_failure_is_not_partial(tmp_path):
    """The other half of the same truth: if the *first* entry fails validation,
    nothing was copied and `partial=True` would be just as false as
    `partial=False` is above. Blanket-setting it swaps one lie for another.
    """
    from scripts import backup as backup_script

    data_dir = tmp_path / "data"
    vault = data_dir / "vaults" / "profile-a"
    vault.mkdir(parents=True)
    conn = sqlite3.connect(vault / "vault.db")
    conn.execute("CREATE TABLE observations (id TEXT)")
    conn.commit()
    conn.close()

    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    created = backup_script.backup(data_dir=data_dir, backup_dir=backup_dir)

    target = tmp_path / "target"
    target.mkdir()
    outside = tmp_path / "elsewhere" / "vaults"
    outside.mkdir(parents=True)
    (target / "vaults").symlink_to(outside, target_is_directory=True)

    result = backup_script.restore(created.backup_path, target)

    assert result.success is False
    assert result.files_restored == 0
    assert result.partial is False, (
        "nothing was copied, so claiming a partial restore is its own falsehood"
    )


def test_hc_bkup_039c_reconciliation_failure_with_no_copies_is_not_partial(
    tmp_path, monkeypatch
):
    """Same truthfulness rule applied to the reconciliation return.

    A profile-scoped restore skips the master DB, so a backup of a profile that
    has no vault yet contains *only* the master DB and copies nothing. If
    re-applying the profile row then fails, `_reapply_profile_row` never
    committed, so no file and no row changed — `partial=True` would tell the
    user their data was replaced when it was not.
    """
    from scripts import backup as backup_script

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    master = data_dir / "healthcentral.db"
    conn = sqlite3.connect(master)
    conn.execute("CREATE TABLE profiles (id TEXT)")
    conn.execute("INSERT INTO profiles VALUES ('profile-a')")
    conn.commit()
    conn.close()

    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    created = backup_script.backup(
        data_dir=data_dir, backup_dir=backup_dir, profile_id="profile-a"
    )

    def _boom(*args, **kwargs):
        raise sqlite3.Error("simulated reconciliation failure")

    monkeypatch.setattr(backup_script, "_reapply_profile_row", _boom)

    result = backup_script.restore(
        created.backup_path, data_dir, profile_id="profile-a"
    )

    assert result.success is False
    assert result.files_restored == 0
    assert result.partial is False, (
        "no file was copied and the row re-apply never committed, so nothing "
        "was replaced"
    )
