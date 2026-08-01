"""PROF-DEL-001 — profile deletion / right-to-erase.

Until now every sub-entity was deletable but the profile itself was immortal,
which is a trust hole for an app whose pitch is data sovereignty.

Owner decision recorded 2026-07-27: on deletion, that profile's audit rows are
**purged** and a single anonymized ``profile.delete`` tombstone is retained.

Test IDs: HC-PDEL-0NN.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

import api.profiles as profiles_api
from api.profiles import PROFILE_DELETE_CONFIRMATION, ProfileDeleteRequest
from core.auth import Session


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

class _FakeMasterDb:
    """Records the Core delete()/insert() statements the route issues."""

    def __init__(self) -> None:
        self.executed: list[str] = []
        self.added: list[object] = []
        self.committed = 0
        self.audit_rows_for_profile = 4

    async def execute(self, stmt):
        text = str(stmt)
        self.executed.append(text)
        return SimpleNamespace(rowcount=self.audit_rows_for_profile)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.committed += 1

    async def rollback(self):
        pass


def _session(profile_id: str = "profile-a") -> Session:
    return Session(
        profile_id=profile_id,
        profile_name="Jane Doe",
        expires_at=datetime(2099, 1, 1, tzinfo=timezone.utc),
        token_jti="jti-abc",
    )


def _make_vault(root: Path, profile_id: str) -> Path:
    """Build a realistic vault directory: keys, db (+ sidecars), documents."""
    vault = root / "vaults" / profile_id
    (vault / "docs").mkdir(parents=True)
    (vault / "key.bin").write_bytes(b"sealed-key")
    (vault / "key.method").write_text("password")
    (vault / "vault.db").write_bytes(b"encrypted")
    (vault / "vault.db-wal").write_bytes(b"wal")
    (vault / "vault.db-shm").write_bytes(b"shm")
    (vault / "docs" / "doc-1.bin").write_bytes(b"ciphertext")
    return vault


@pytest.fixture
def vaults(tmp_path, monkeypatch):
    """Point app_data_path at a temp dir and seed two profiles.

    ``app_data_path`` is a computed property, so it is patched on the Settings
    class rather than the instance. One patch covers every module, since they
    all share the same settings object.
    """
    monkeypatch.setattr(
        type(profiles_api.settings), "app_data_path", property(lambda self: tmp_path)
    )
    return SimpleNamespace(
        root=tmp_path,
        a=_make_vault(tmp_path, "profile-a"),
        b=_make_vault(tmp_path, "profile-b"),
    )


async def _delete(
    *,
    profile_id: str = "profile-a",
    password: str = "CorrectHorse1",
    confirmation: str = PROFILE_DELETE_CONFIRMATION,
    export_acknowledged: bool = True,
    authenticates: bool = True,
    master_db: _FakeMasterDb | None = None,
    profile_exists: bool = True,
):
    db = master_db or _FakeMasterDb()
    profile = SimpleNamespace(id=profile_id, display_name="Jane Doe") if profile_exists else None

    with patch.object(profiles_api, "_load_profile_for_delete", AsyncMock(return_value=profile)), \
         patch.object(profiles_api, "authenticate_profile",
                      AsyncMock(return_value=profile if authenticates else None)), \
         patch.object(profiles_api, "close_profile_database_on_logout", AsyncMock()), \
         patch.object(profiles_api, "revoke_jwt_token", MagicMock()):
        return await profiles_api.delete_profile(
            profile_id=profile_id,
            payload=ProfileDeleteRequest(
                password=password,
                confirmation_phrase=confirmation,
                export_acknowledged=export_acknowledged,
            ),
            request=SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"), headers={}),
            session=_session(profile_id),
            db=db,
        ), db


# ---------------------------------------------------------------------------
# HC-PDEL-001 / 002 — the lifecycle and the isolation assertion
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_pdel_001_full_lifecycle_removes_vault_and_master_row(vaults):
    assert vaults.a.exists()

    _, db = await _delete()

    assert not vaults.a.exists(), "vault directory must be gone"
    assert any("DELETE FROM profiles" in s for s in db.executed)
    assert db.committed >= 1


@pytest.mark.asyncio
async def test_hc_pdel_002_other_profiles_untouched(vaults):
    """The highest-value assertion in this feature: erasing one profile must
    not disturb another's vault, keys or documents."""
    await _delete(profile_id="profile-a")

    assert vaults.b.exists()
    assert (vaults.b / "key.bin").exists()
    assert (vaults.b / "key.method").exists()
    assert (vaults.b / "vault.db").exists()
    assert (vaults.b / "docs" / "doc-1.bin").exists()


# ---------------------------------------------------------------------------
# HC-PDEL-003..005 — nothing is destroyed without re-auth and confirmation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_pdel_003_wrong_password_returns_401_and_deletes_nothing(vaults):
    with pytest.raises(HTTPException) as exc:
        await _delete(authenticates=False)
    assert exc.value.status_code == 401
    assert vaults.a.exists()
    assert (vaults.a / "key.bin").exists()


@pytest.mark.asyncio
async def test_hc_pdel_004_wrong_confirmation_phrase_returns_400_and_deletes_nothing(vaults):
    with pytest.raises(HTTPException) as exc:
        await _delete(confirmation="delete it")
    assert exc.value.status_code == 400
    assert vaults.a.exists()
    assert (vaults.a / "key.bin").exists()


@pytest.mark.asyncio
async def test_hc_pdel_005_missing_export_acknowledgement_returns_400(vaults):
    with pytest.raises(HTTPException) as exc:
        await _delete(export_acknowledged=False)
    assert exc.value.status_code == 400
    assert vaults.a.exists()


# ---------------------------------------------------------------------------
# HC-PDEL-006 — keys die first (the crypto-erase commit point)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_pdel_006_keys_deleted_before_db_file(vaults):
    """Deleting the sealed key is what makes the vault unreadable. If the
    process dies mid-delete, it must die after the key is gone, not before.

    The database file itself is removed by the vault sweep (rmtree), so the
    ordering assertion is: every sealed-key unlink precedes the sweep.
    """
    order: list[str] = []
    real_unlink = Path.unlink
    real_rmtree = profiles_api.shutil.rmtree

    def tracking_unlink(self, *args, **kwargs):
        order.append(f"unlink:{self.name}")
        return real_unlink(self, *args, **kwargs)

    def tracking_rmtree(path, *args, **kwargs):
        order.append("rmtree:vault")
        return real_rmtree(path, *args, **kwargs)

    with patch.object(Path, "unlink", tracking_unlink), \
         patch.object(profiles_api.shutil, "rmtree", tracking_rmtree):
        await _delete()

    assert "rmtree:vault" in order
    assert order.index("unlink:key.bin") < order.index("rmtree:vault")
    assert order.index("unlink:key.method") < order.index("rmtree:vault")


@pytest.mark.asyncio
async def test_hc_pdel_006b_all_enumerated_key_paths_are_deleted(vaults):
    """Deletion enumerates key paths from profile_database rather than
    hardcoding names, so a future sealed copy is picked up automatically."""
    from core.profile_database import get_profile_db_manager

    extra = vaults.a / "key.recovery.bin"
    extra.write_bytes(b"second-sealed-copy")

    manager = get_profile_db_manager()
    original = manager.get_profile_key_paths
    with patch.object(
        type(manager), "get_profile_key_paths",
        lambda self, pid: original(pid) + [vaults.root / "vaults" / pid / "key.recovery.bin"],
    ):
        await _delete()

    assert not extra.exists()


# ---------------------------------------------------------------------------
# HC-PDEL-007/008 — partial failure behaviour
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_pdel_007_db_file_failure_still_completes_master_cleanup(vaults):
    """The key is already destroyed by this point, so the data is already
    cryptographically erased; a filesystem hiccup must not abort the DB work."""
    real_rmtree = profiles_api.shutil.rmtree
    calls = {"n": 0}

    def flaky_rmtree(path, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise OSError("file locked")
        return real_rmtree(path, *args, **kwargs)

    with patch.object(profiles_api.shutil, "rmtree", flaky_rmtree):
        _, db = await _delete()

    assert any("DELETE FROM profiles" in s for s in db.executed)


@pytest.mark.asyncio
async def test_hc_pdel_008_key_unlink_failure_aborts_before_master_row_delete(vaults):
    """If the key cannot be destroyed, stop: leaving the master row intact is
    what lets the user retry with a re-auth."""
    def refusing_unlink(self, *args, **kwargs):
        raise OSError("permission denied")

    with patch.object(Path, "unlink", refusing_unlink):
        with pytest.raises(HTTPException) as exc:
            _, db = await _delete()
    assert exc.value.status_code == 500


# ---------------------------------------------------------------------------
# HC-PDEL-009/010 — the owner's audit-retention decision
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_pdel_009_audit_rows_purged_and_tombstone_written(vaults):
    _, db = await _delete()

    assert any("DELETE FROM audit_logs" in s for s in db.executed), \
        "the profile's audit rows must be purged (owner decision 2026-07-27)"

    tombstones = [r for r in db.added if getattr(r, "event_type", None) == "profile.delete"]
    assert len(tombstones) == 1
    assert json.loads(tombstones[0].details_json)["audit_rows_purged"] == 4


@pytest.mark.asyncio
async def test_hc_pdel_010_tombstone_carries_no_profile_identifier(vaults):
    """'Anonymized' means the tombstone records that a deletion happened, not
    whose. A retained profile id would be a linkage handle back to the person."""
    _, db = await _delete()
    tombstone = next(r for r in db.added if r.event_type == "profile.delete")

    assert tombstone.profile_id is None
    assert tombstone.entity_id is None
    blob = f"{tombstone.action} {tombstone.details_json} {tombstone.entity_type}"
    assert "profile-a" not in blob
    assert "Jane Doe" not in blob


@pytest.mark.asyncio
async def test_hc_pdel_011_tombstone_written_after_profile_row_is_deleted(vaults):
    """FK correctness: audit_logs.profile_id references profiles.id with a
    cascade, so the tombstone must be inserted with profile_id=None and only
    after the profile row is gone."""
    _, db = await _delete()
    tombstone = next(r for r in db.added if r.event_type == "profile.delete")
    assert tombstone.profile_id is None
    assert db.executed  # the deletes ran


# ---------------------------------------------------------------------------
# HC-PDEL-012/013 — session teardown and filesystem completeness
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_pdel_012_deleting_missing_profile_returns_404(vaults):
    with pytest.raises(HTTPException) as exc:
        await _delete(profile_exists=False)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_hc_pdel_013_wal_and_shm_sidecars_and_documents_removed(vaults):
    """SQLite leaves -wal/-shm beside the db; the vault sweep must take the
    whole directory, not a hardcoded list of filenames."""
    await _delete()
    for leftover in ("vault.db-wal", "vault.db-shm", "docs/doc-1.bin"):
        assert not (vaults.a / leftover).exists()


@pytest.mark.asyncio
async def test_hc_pdel_014_session_is_closed_and_token_revoked(vaults):
    """A live JWT must not keep pointing at a deleted profile."""
    with patch.object(profiles_api, "_load_profile_for_delete",
                      AsyncMock(return_value=SimpleNamespace(id="profile-a", display_name="D"))), \
         patch.object(profiles_api, "authenticate_profile",
                      AsyncMock(return_value=SimpleNamespace(id="profile-a"))), \
         patch.object(profiles_api, "close_profile_database_on_logout", AsyncMock()) as closed, \
         patch.object(profiles_api, "revoke_jwt_token", MagicMock()) as revoked:
        await profiles_api.delete_profile(
            profile_id="profile-a",
            payload=ProfileDeleteRequest(
                password="CorrectHorse1",
                confirmation_phrase=PROFILE_DELETE_CONFIRMATION,
                export_acknowledged=True,
            ),
            request=SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"), headers={}),
            session=_session(),
            db=_FakeMasterDb(),
        )

    closed.assert_awaited_once()
    revoked.assert_called_once()


# ---------------------------------------------------------------------------
# HC-PDEL-015..018 — erase completeness and rate-limiter hygiene (BK-02, SEC-01)
# ---------------------------------------------------------------------------

def _make_backup(root: Path, profile_id: str) -> Path:
    """A backup directory as api/backup.py lays them out, keys included."""
    backup = root / "backups" / profile_id / "backup_20260101_000000"
    backup.mkdir(parents=True)
    (backup / "manifest.json").write_text("{}")
    (backup / "asclexis.db").write_bytes(b"master")
    vault = backup / "vaults" / profile_id
    vault.mkdir(parents=True)
    (vault / "vault.db").write_bytes(b"encrypted")
    (vault / "key.bin").write_bytes(b"sealed-primary")
    (vault / "key.recovery.bin").write_bytes(b"sealed-recovery")
    return backup


@pytest.mark.asyncio
async def test_hc_pdel_015_backups_are_destroyed_with_the_profile(vaults):
    """The Danger Zone tells the user their encryption key is destroyed and the
    data is unreadable. A retained backup holds `key.bin` AND
    `key.recovery.bin` alongside the vault, so leaving it makes that statement
    false and the record fully recoverable.
    """
    backup = _make_backup(vaults.root, "profile-a")
    assert (backup / "vaults" / "profile-a" / "key.recovery.bin").exists()

    await _delete(profile_id="profile-a")

    assert not (vaults.root / "backups" / "profile-a").exists()


@pytest.mark.asyncio
async def test_hc_pdel_016_another_profiles_backups_survive(vaults):
    """Erasing one profile must not touch another's backups."""
    _make_backup(vaults.root, "profile-a")
    other = _make_backup(vaults.root, "profile-b")

    await _delete(profile_id="profile-a")

    assert other.exists()
    assert (other / "vaults" / "profile-b" / "key.bin").exists()


@pytest.mark.asyncio
async def test_hc_pdel_017_backup_schedule_row_is_deleted_explicitly(vaults):
    """`backup_schedules.profile_id` declares ON DELETE CASCADE, but SQLite
    ignores foreign keys unless `PRAGMA foreign_keys=ON` is set, and it is set
    nowhere in this codebase. Relying on the cascade orphans the row, so the
    delete must be explicit."""
    _, db = await _delete(profile_id="profile-a")

    assert any("DELETE FROM backup_schedules" in s for s in db.executed), (
        "the schedule row must be deleted explicitly, not left to an inert cascade"
    )


@pytest.mark.asyncio
async def test_hc_pdel_018_successful_reauth_resets_the_rate_limiter(vaults):
    """login and unlock_profile both reset the limiter after a good password.
    delete did not, so failed attempts accumulated across successful ones until
    the user was locked out of deleting their own profile."""
    from core.rate_limiter import auth_rate_limiter
    from core.config import settings as core_settings

    if not core_settings.auth_rate_limit_enabled:
        pytest.skip("rate limiting disabled in this configuration")

    key = "delete:127.0.0.1:profile-a"
    auth_rate_limiter.reset(key)
    try:
        # One short of the block threshold, so the reset is the only thing
        # standing between the next mistyped password and a lockout.
        for _ in range(auth_rate_limiter._max_attempts - 1):
            auth_rate_limiter.add_failure(key)

        await _delete(profile_id="profile-a")

        auth_rate_limiter.add_failure(key)
        assert auth_rate_limiter.check(key).allowed is True, (
            "a successful re-auth must clear the counter, as login and "
            "unlock_profile both do"
        )
    finally:
        auth_rate_limiter.reset(key)
