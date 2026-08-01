"""BKUP-UX-001 — backup must capture a *restorable* profile.

Two defects found 2026-07-27 while wiring backup to the recovery key:

1. `_discover_databases` globbed `vaults/*.db`, but vaults live at
   `vaults/{profile_id}/vault.db`. The glob matched nothing, so every backup
   contained only the master database — none of the patient's health data.
2. Sealed key files were never backed up at all. A vault database without its
   key is ciphertext with no way in, so even a corrected database backup would
   have restored nothing usable.

Test IDs: HC-BKUP-0NN.
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from scripts.backup import backup, _discover_databases, _discover_key_files


def _seed(data_dir, profile_ids=("profile-a",), with_recovery=True):
    data_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(data_dir / "asclexis.db")
    conn.execute("CREATE TABLE profiles (id TEXT)")
    conn.commit()
    conn.close()

    for pid in profile_ids:
        vault = data_dir / "vaults" / pid
        (vault / "docs").mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(vault / "vault.db")
        conn.execute("CREATE TABLE observations (id TEXT)")
        conn.commit()
        conn.close()
        (vault / "key.bin").write_bytes(b"sealed-primary")
        (vault / "key.method").write_text("password")
        if with_recovery:
            (vault / "key.recovery.bin").write_bytes(b"sealed-recovery")
            (vault / "key.recovery.method").write_text("password")
    return data_dir


def test_hc_bkup_001_profile_vault_databases_are_discovered(tmp_path):
    """The regression: a flat vaults/*.db glob found nothing."""
    data_dir = _seed(tmp_path / "data")

    found = {p.name for p in _discover_databases(data_dir)}

    assert "asclexis.db" in found
    assert "vault.db" in found, "profile vault databases must be discovered"


def test_hc_bkup_002_key_files_are_discovered(tmp_path):
    data_dir = _seed(tmp_path / "data")

    found = {p.name for p in _discover_key_files(data_dir)}

    assert found == {"key.bin", "key.method", "key.recovery.bin", "key.recovery.method"}


def test_hc_bkup_003_recovery_key_is_included_in_the_backup(tmp_path):
    """SEC-RECOV-001 interaction: omitting the recovery copy would silently
    break recovery after a restore."""
    data_dir = _seed(tmp_path / "data")

    result = backup(data_dir, tmp_path / "backups")
    manifest = json.loads(result.manifest_path.read_text())
    paths = {entry["path"].replace("\\", "/") for entry in manifest["files"]}

    assert "vaults/profile-a/key.recovery.bin" in paths
    assert "vaults/profile-a/key.recovery.method" in paths


def test_hc_bkup_004_backup_contains_everything_needed_to_restore(tmp_path):
    data_dir = _seed(tmp_path / "data")

    result = backup(data_dir, tmp_path / "backups")
    paths = {
        entry["path"].replace("\\", "/")
        for entry in json.loads(result.manifest_path.read_text())["files"]
    }

    assert {
        "asclexis.db",
        "vaults/profile-a/vault.db",
        "vaults/profile-a/key.bin",
        "vaults/profile-a/key.method",
    } <= paths


def test_hc_bkup_005_key_bytes_survive_the_round_trip(tmp_path):
    """A key file copied wrong is a vault that never opens again."""
    data_dir = _seed(tmp_path / "data")

    result = backup(data_dir, tmp_path / "backups")
    restored = result.backup_path / "vaults" / "profile-a" / "key.bin"

    assert restored.read_bytes() == b"sealed-primary"


def test_hc_bkup_006_profile_filter_selects_the_right_vault(tmp_path):
    data_dir = _seed(tmp_path / "data", profile_ids=("profile-a", "profile-b"))

    result = backup(data_dir, tmp_path / "backups", profile_id="profile-a")
    paths = {
        entry["path"].replace("\\", "/")
        for entry in json.loads(result.manifest_path.read_text())["files"]
    }

    assert "vaults/profile-a/vault.db" in paths
    assert "vaults/profile-a/key.bin" in paths
    assert not any("profile-b" in p for p in paths)


def test_hc_bkup_007_profiles_without_recovery_keys_still_back_up(tmp_path):
    """Profiles created before SEC-RECOV-001 have no recovery copy."""
    data_dir = _seed(tmp_path / "data", with_recovery=False)

    result = backup(data_dir, tmp_path / "backups")
    paths = {
        entry["path"].replace("\\", "/")
        for entry in json.loads(result.manifest_path.read_text())["files"]
    }

    assert "vaults/profile-a/key.bin" in paths
    assert not any("recovery" in p for p in paths)


def test_hc_bkup_008_manifest_checksums_match_the_copied_bytes(tmp_path):
    import hashlib

    data_dir = _seed(tmp_path / "data")
    result = backup(data_dir, tmp_path / "backups")

    for entry in json.loads(result.manifest_path.read_text())["files"]:
        copied = result.backup_path / entry["path"]
        assert hashlib.sha256(copied.read_bytes()).hexdigest() == entry["sha256"]
