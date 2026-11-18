"""SEC-RECOV-001 — recovery key for profile encryption.

A forgotten password used to mean permanent, unrecoverable loss of the entire
health record: the DEK was sealed by the password alone, and local-first means
there is no server-side reset by design. A recovery code seals a **second copy
of the same DEK**, so the record survives a forgotten password without
weakening the password path.

Owner sign-off recorded 2026-07-27 (this touches core/security.py and
core/profile_database.py, both on CLAUDE.md's ask-first list).

Test IDs: HC-RECOV-0NN. The pre-change baseline lives in
tests/security/test_key_sealing_baseline.py.
"""

from __future__ import annotations

import json
import logging
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import api.profiles as profiles_api
from core import security as security_module
from core.security import (
    KeySealingError,
    generate_encryption_key,
    generate_recovery_code,
    normalize_recovery_code,
    seal_key_with_dpapi,
    unseal_key_with_dpapi,
)


class _FakeDb:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.committed = 0

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.committed += 1

    async def rollback(self):
        pass

    async def execute(self, _stmt):
        return SimpleNamespace(scalar_one_or_none=lambda: None, rowcount=0)


@pytest.fixture
def vault(tmp_path, monkeypatch):
    """Point app_data_path at a temp dir and create one profile vault."""
    monkeypatch.setattr(
        type(profiles_api.settings), "app_data_path", property(lambda self: tmp_path)
    )
    (tmp_path / "vaults" / "profile-a").mkdir(parents=True)
    return tmp_path / "vaults" / "profile-a"


# ---------------------------------------------------------------------------
# Code format and normalization
# ---------------------------------------------------------------------------

def test_hc_recov_005_generated_code_shape():
    code = generate_recovery_code()
    groups = code.split("-")

    assert len(groups) == 8
    assert all(len(g) == 4 for g in groups)
    # Crockford excludes the read-alikes.
    assert not set("ILOU") & set(code)


def test_hc_recov_006_codes_are_unique():
    codes = {generate_recovery_code() for _ in range(200)}
    assert len(codes) == 200


def test_hc_recov_014_crockford_aliases_accepted():
    """Someone transcribing from paper should not be punished for a legible
    mistake: O reads as 0, I and L read as 1."""
    code = generate_recovery_code()
    canonical = normalize_recovery_code(code)

    assert normalize_recovery_code(code.lower()) == canonical
    assert normalize_recovery_code(code.replace("-", "")) == canonical
    assert normalize_recovery_code(code.replace("-", " ")) == canonical
    assert normalize_recovery_code("  " + code + "  ") == canonical

    # Aliases map onto their canonical digits.
    assert normalize_recovery_code("O" * 32) == "0" * 32
    assert normalize_recovery_code("I" * 32) == "1" * 32
    assert normalize_recovery_code("L" * 32) == "1" * 32


@pytest.mark.parametrize("bad", ["", "TOOSHORT", "A" * 33, "!" * 32, "@BCD" * 8])
def test_hc_recov_013_malformed_codes_rejected(bad):
    with pytest.raises(ValueError):
        normalize_recovery_code(bad)


def test_hc_recov_013b_malformed_code_rejected_before_key_derivation():
    """A malformed code must cost no PBKDF2 work — otherwise the endpoint is a
    free CPU-exhaustion primitive."""
    with patch.object(security_module, "derive_key_from_password") as derive:
        with pytest.raises(ValueError):
            normalize_recovery_code("nope")
    derive.assert_not_called()


# ---------------------------------------------------------------------------
# HC-RECOV-010 — the load-bearing test: the recovery seal is never DPAPI
# ---------------------------------------------------------------------------

def test_hc_recov_010_recovery_seal_is_never_dpapi(vault):
    """A recovery code exists to survive losing the machine. DPAPI ties a seal
    to the current OS user account, so a DPAPI-sealed recovery copy would be
    worthless in exactly the situation it is meant for."""
    dek = generate_encryption_key()

    with patch.object(security_module, "is_dpapi_available", return_value=True), \
         patch.object(security_module.settings, "use_dpapi", True, create=True):
        profiles_api._issue_recovery_code("profile-a", dek)

    assert (vault / "key.recovery.method").read_text().strip() == "password"


def test_hc_recov_010b_primary_seal_still_prefers_dpapi_when_available():
    """The force_password kwarg must not leak into the primary path."""
    dek = generate_encryption_key()
    with patch.object(security_module, "is_dpapi_available", return_value=True), \
         patch.object(security_module.settings, "use_dpapi", True, create=True), \
         patch.dict("sys.modules", {"win32crypt": SimpleNamespace(
             CryptProtectData=lambda *a, **k: b"dpapi-sealed")}):
        _, method = seal_key_with_dpapi(dek, fallback_password="CorrectHorse1")
    assert method == "dpapi"


def test_hc_recov_010c_force_password_default_is_off():
    """Existing callers must be byte-for-byte unaffected (see the baseline
    file); the new kwarg defaults to the old behaviour."""
    import inspect

    sig = inspect.signature(seal_key_with_dpapi)
    assert sig.parameters["force_password"].default is False


# ---------------------------------------------------------------------------
# HC-RECOV-011/012 — the recovery copy really is the same key
# ---------------------------------------------------------------------------

def test_hc_recov_011_recovery_unseals_the_same_dek_bytes(vault):
    dek = generate_encryption_key()
    code = profiles_api._issue_recovery_code("profile-a", dek)

    assert profiles_api._unseal_dek_with_recovery_code("profile-a", code) == dek


def test_hc_recov_012_wrong_code_raises_keysealingerror(vault):
    profiles_api._issue_recovery_code("profile-a", generate_encryption_key())
    other = generate_recovery_code()

    with pytest.raises(KeySealingError):
        profiles_api._unseal_dek_with_recovery_code("profile-a", other)


def test_hc_recov_012b_no_recovery_seal_raises(vault):
    with pytest.raises(KeySealingError):
        profiles_api._unseal_dek_with_recovery_code("profile-a", generate_recovery_code())


def test_hc_recov_012c_the_code_itself_is_never_persisted(vault):
    """Only the seal derived from the code is stored — never the code, and not
    a hash of it either (a hash is an offline verification oracle)."""
    dek = generate_encryption_key()
    code = profiles_api._issue_recovery_code("profile-a", dek)

    for path in vault.iterdir():
        blob = path.read_bytes()
        assert code.encode() not in blob
        assert normalize_recovery_code(code).encode() not in blob
        for group in code.split("-"):
            assert group.encode() not in blob


def test_hc_recov_016_issuing_a_new_code_rotates_the_seal(vault):
    """Rotation, not invalidation: there is always exactly one valid code."""
    dek = generate_encryption_key()
    first = profiles_api._issue_recovery_code("profile-a", dek)
    second = profiles_api._issue_recovery_code("profile-a", dek)

    assert first != second
    assert profiles_api._unseal_dek_with_recovery_code("profile-a", second) == dek
    with pytest.raises(KeySealingError):
        profiles_api._unseal_dek_with_recovery_code("profile-a", first)


def test_hc_recov_017_recovery_seal_is_independent_of_the_password(vault):
    """The recovery copy seals the DEK, not the password, so an ordinary
    password change must not invalidate it."""
    dek = generate_encryption_key()
    code = profiles_api._issue_recovery_code("profile-a", dek)

    # Simulate change_password: re-seal only the primary copy.
    sealed, method = seal_key_with_dpapi(dek, fallback_password="BrandNewPass9")
    (vault / "key.bin").write_bytes(sealed)
    (vault / "key.method").write_text(method)

    assert profiles_api._unseal_dek_with_recovery_code("profile-a", code) == dek


# ---------------------------------------------------------------------------
# Key-file plumbing and its contract with PROF-DEL-001
# ---------------------------------------------------------------------------

def test_hc_recov_018_has_recovery_key_reflects_file_state(vault):
    from core.profile_database import get_profile_db_manager

    manager = get_profile_db_manager()
    assert manager.has_recovery_key("profile-a") is False

    profiles_api._issue_recovery_code("profile-a", generate_encryption_key())
    assert manager.has_recovery_key("profile-a") is True


def test_hc_recov_023_recovery_key_files_are_in_the_deletion_enumeration(vault):
    """The SEC-RECOV <-> PROF-DEL contract: deletion enumerates key paths from
    this one accessor, so the recovery copy is destroyed with everything else.
    If this fails, deleting a profile leaves a usable key behind."""
    from core.profile_database import get_profile_db_manager

    paths = {p.name for p in get_profile_db_manager().get_profile_key_paths("profile-a")}
    assert {"key.bin", "key.method", "key.recovery.bin", "key.recovery.method"} <= paths


def test_hc_recov_024_atomic_write_leaves_no_partial_file(vault):
    """A half-written sealed key is an unopenable vault."""
    target = vault / "key.recovery.bin"
    profiles_api._atomic_write(target, b"first")
    profiles_api._atomic_write(target, b"second-and-longer")

    assert target.read_bytes() == b"second-and-longer"
    assert not list(vault.glob("*.tmp"))


# ---------------------------------------------------------------------------
# HC-RECOV-020/021 — the code stays out of logs and audit rows
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_recov_020_code_never_appears_in_logs(vault, caplog):
    dek = generate_encryption_key()
    with caplog.at_level(logging.DEBUG):
        code = profiles_api._issue_recovery_code("profile-a", dek)

    assert code not in caplog.text
    for group in code.split("-"):
        assert group not in caplog.text


@pytest.mark.asyncio
async def test_hc_recov_021_recovery_events_survive_the_audit_allowlist():
    """The AUDIT-PHI <-> SEC-RECOV contract: the new events must be registered
    in ALLOWED_ACTIONS, or they would be silently degraded to bare event types.
    """
    from core.audit import ALLOWED_ACTIONS, log_profile_event

    db = _FakeDb()
    for event, expected_detail in (
        ("recovery_code_generated", {"trigger": "profile_create"}),
        ("recovered", {"password_reset": True, "recovery_rotated": True}),
        ("recovery_failed", {"reason": "invalid_code"}),
    ):
        row = await log_profile_event(
            db=db, event=event, profile_id="profile-a",
            profile_name="Jane Doe", details=expected_detail,
        )
        assert row.action in ALLOWED_ACTIONS, f"{event} action is not registered"
        assert json.loads(row.details_json) == expected_detail, (
            f"{event} details did not survive the allowlist"
        )


# ---------------------------------------------------------------------------
# HC-RECOV-019 — rate limiting
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_recov_019_recovery_attempts_are_rate_limited(vault):
    """160 bits is not brute-forceable; the limiter exists because each attempt
    costs a 600k-iteration PBKDF2."""
    from core.rate_limiter import recovery_rate_limiter

    profiles_api._issue_recovery_code("profile-a", generate_encryption_key())
    key = "recover:127.0.0.1:profile-a"
    recovery_rate_limiter.reset(key)

    from core.config import settings as cfg
    if not cfg.auth_rate_limit_enabled:
        pytest.skip("rate limiting disabled in this environment")

    for _ in range(cfg.recovery_rate_limit_max_attempts):
        recovery_rate_limiter.add_failure(key)

    decision = recovery_rate_limiter.check(key)
    assert decision.allowed is False
    assert decision.retry_after_seconds > 0
    recovery_rate_limiter.reset(key)


def test_hc_recov_019b_recovery_limit_is_stricter_than_login():
    from core.config import settings as cfg

    assert cfg.recovery_rate_limit_max_attempts < cfg.auth_rate_limit_max_attempts
    assert cfg.recovery_rate_limit_window_seconds > cfg.auth_rate_limit_window_seconds


# ---------------------------------------------------------------------------
# HC-RECOV-022 — the existing password path is unchanged
# ---------------------------------------------------------------------------

def test_hc_recov_022_password_seal_roundtrip_still_works():
    """Re-run of the step-0 baseline after the change (the full baseline lives
    in tests/security/test_key_sealing_baseline.py)."""
    key = generate_encryption_key()
    sealed, method = seal_key_with_dpapi(key, fallback_password="CorrectHorse1")

    assert method == "password"
    assert unseal_key_with_dpapi(sealed, method, fallback_password="CorrectHorse1") == key


# ---------------------------------------------------------------------------
# HC-RECOV-025 — recover_profile uses the project's timestamp helper
# ---------------------------------------------------------------------------

def test_hc_recov_025_recovery_uses_the_project_time_helper():
    """CLAUDE.md names core.time.utcnow as the single timestamp helper.
    datetime.utcnow() is also deprecated from 3.12. This is a source assertion
    because the returned value is identical either way — only the call differs."""
    import inspect

    import api.profiles as profiles_api

    source = inspect.getsource(profiles_api.recover_profile)
    assert "datetime.utcnow()" not in source, (
        "use core.time.utcnow, per the hard invariant this branch enforces "
        "elsewhere"
    )


# ---------------------------------------------------------------------------
# HC-RECOV-026..030 (RECOVER-ORDER) — commit before rotation, through HTTP
# ---------------------------------------------------------------------------
#
# Owner answer RECOVER-ORDER-COMMIT (2026-11-09): "commit before rotation", and
# the same reorder for the standalone ``issue_recovery_code``. A master commit
# that fails after the recovery file was rotated used to leave neither the
# password nor the recovery code working. These tests drive the real routes via
# ``route_client`` with a master DB whose ``commit`` is fault-injected.

_OLD_PASS = "OldPassw0rd!"
_NEW_PASS = "NewPassw0rd!"


class _FaultDb:
    """Master-DB stand-in: one profile row, commits that can be made to raise."""

    def __init__(self, profile, fail_on=()):
        self._profile = profile
        self.fail_on = set(fail_on)  # 1-based commit numbers that raise; "all" = every one
        self.added: list[object] = []
        self.commit_calls = 0
        self.rollbacks = 0

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commit_calls += 1
        if "all" in self.fail_on or self.commit_calls in self.fail_on:
            raise RuntimeError("injected commit failure")

    async def rollback(self):
        self.rollbacks += 1

    async def flush(self):
        pass

    async def execute(self, _stmt):
        return SimpleNamespace(scalar_one_or_none=lambda: self._profile, scalar=lambda: None)


def _events(db):
    return [row.event_type for row in db.added]


@pytest.fixture
def sealed_vault(vault):
    """A profile whose primary key is sealed under _OLD_PASS and which holds one
    recovery code. Yields (dek, old_code, profile)."""
    import base64

    from core.rate_limiter import auth_rate_limiter, recovery_rate_limiter
    from core.security import generate_salt, hash_password

    dek = generate_encryption_key()
    sealed, method = seal_key_with_dpapi(dek, fallback_password=_OLD_PASS)
    (vault / "key.bin").write_bytes(sealed)
    (vault / "key.method").write_bytes(method.encode())
    old_code = profiles_api._issue_recovery_code("profile-a", dek)
    profile = SimpleNamespace(
        id="profile-a",
        display_name="T",
        password_hash=hash_password(_OLD_PASS),
        password_salt=base64.b64encode(generate_salt()).decode("ascii"),
        is_locked=True,
        last_accessed_at=None,
    )
    recovery_rate_limiter.reset("recover:testclient:profile-a")
    auth_rate_limiter.reset("recovery-code:testclient")
    return dek, old_code, profile


def _recover(db, old_code, raise_exc=False):
    from tests.support.routes import route_client

    with route_client(
        profiles_api.router, "/profiles", master_db=db, raise_server_exceptions=raise_exc
    ) as client:
        return client.post(
            "/profiles/profile-a/recover",
            json={"recovery_code": old_code, "new_password": _NEW_PASS},
        )


def test_hc_recov_026_failed_first_commit_leaves_the_old_code_working(sealed_vault):
    """The load-bearing RED: with every commit failing, the old recovery code
    must still unseal the DEK. On the old order the file was rotated first."""
    dek, old_code, profile = sealed_vault
    db = _FaultDb(profile, fail_on={"all"})

    response = _recover(db, old_code)

    assert response.status_code == 500
    assert profiles_api._unseal_dek_with_recovery_code("profile-a", old_code) == dek


def test_hc_recov_027_first_commit_precedes_rotation_in_recover_profile():
    """Structural pin (same source-assertion convention as HC-RECOV-025)."""
    import inspect

    source = inspect.getsource(profiles_api.recover_profile)
    after_primary = source.index("_atomic_write(manager._get_profile_key_method_path")
    first_commit = source.index("await db.commit()", after_primary)
    rotation = source.index("_issue_recovery_code(", after_primary)
    assert first_commit < rotation


def test_hc_recov_028_failed_second_commit_keeps_the_new_password(sealed_vault, vault):
    """Window 3 pin. Not RED on the old order, where the second commit never
    existed: commit 1 has landed the credential state, rotation has run, only
    the commit of the second audit row failed. The new password still opens
    the vault."""
    dek, old_code, profile = sealed_vault
    db = _FaultDb(profile, fail_on={2})

    response = _recover(db, old_code)

    assert response.status_code == 500
    sealed = (vault / "key.bin").read_bytes()
    method = (vault / "key.method").read_text().strip()
    assert unseal_key_with_dpapi(sealed, method, fallback_password=_NEW_PASS) == dek


def test_hc_recov_029_happy_path_orders_audit_rows_and_commits_twice(sealed_vault):
    """Both audit rows are written, `recovered` before `recovery_code_generated`,
    in two commits; the response carries the new code and the old one is dead.
    The post-commit vault open and FK cleanup are stubbed (unchanged steps)."""
    from unittest.mock import AsyncMock

    dek, old_code, profile = sealed_vault
    db = _FaultDb(profile)

    with patch.object(profiles_api, "open_profile_database_on_login", AsyncMock()), \
         patch.object(profiles_api, "_audit_fk_orphan_cleanup", AsyncMock()):
        response = _recover(db, old_code)

    assert response.status_code == 200
    new_code = response.json()["recovery_code"]
    assert _events(db) == ["profile.recovered", "profile.recovery_code_generated"]
    assert db.commit_calls == 2
    assert profiles_api._unseal_dek_with_recovery_code("profile-a", new_code) == dek
    with pytest.raises(KeySealingError):
        profiles_api._unseal_dek_with_recovery_code("profile-a", old_code)


def _issue(db):
    from tests.support.routes import route_client

    with route_client(
        profiles_api.router, "/profiles", master_db=db, raise_server_exceptions=False
    ) as client:
        return client.post("/profiles/profile-a/recovery-code", json={"password": _OLD_PASS})


def test_hc_recov_030_issue_recovery_code_failed_commit_keeps_the_old_code(sealed_vault):
    """Owner answer RECOVER-ORDER-COMMIT, standalone route: a commit that fails
    must leave the existing recovery file untouched and return no code."""
    dek, old_code, profile = sealed_vault
    db = _FaultDb(profile, fail_on={"all"})

    response = _issue(db)

    assert response.status_code == 500
    assert "recovery_code" not in response.text
    assert profiles_api._unseal_dek_with_recovery_code("profile-a", old_code) == dek


def test_hc_recov_030b_issue_recovery_code_success_rotates_the_code(sealed_vault):
    dek, old_code, profile = sealed_vault
    db = _FaultDb(profile)

    response = _issue(db)

    assert response.status_code == 200
    body = response.json()
    assert body["replaced_existing"] is True
    assert profiles_api._unseal_dek_with_recovery_code("profile-a", body["recovery_code"]) == dek
    with pytest.raises(KeySealingError):
        profiles_api._unseal_dek_with_recovery_code("profile-a", old_code)
    assert _events(db) == ["profile.recovery_code_generated"]
    assert db.commit_calls == 1


# ---------------------------------------------------------------------------
# HC-RCR-001..003 (RECOVERY-CODE-RATELIMIT) — POST /{id}/recovery-code throttle
# ---------------------------------------------------------------------------
#
# Owner answer RECOVERY-CODE-THROTTLE (2026-11-09): "auth_rate_limiter, login
# pattern". The password re-auth on this route used to be an unthrottled
# guessing oracle. Ordering implemented: limiter check FIRST (before the
# profile lookup), like login; failures counted on 401; reset on success.

_RCR_PASS = "RcrPassw0rd!"
_RCR_KEY = "recovery-code:testclient"


class _RcrDb:
    def __init__(self, profile):
        self._profile = profile
        self.added: list[object] = []

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        pass

    async def rollback(self):
        pass

    async def flush(self):
        pass

    async def execute(self, _stmt):
        return SimpleNamespace(scalar_one_or_none=lambda: self._profile, scalar=lambda: None)


@pytest.fixture
def rcr_env(vault, monkeypatch):
    """A sealed vault, a real password hash, and the limiter armed and clean."""
    from core.rate_limiter import auth_rate_limiter
    from core.security import hash_password

    monkeypatch.setattr(profiles_api.settings, "auth_rate_limit_enabled", True)
    dek = generate_encryption_key()
    sealed, method = seal_key_with_dpapi(dek, fallback_password=_RCR_PASS)
    (vault / "key.bin").write_bytes(sealed)
    (vault / "key.method").write_bytes(method.encode())
    profile = SimpleNamespace(
        id="profile-a", display_name="T", password_hash=hash_password(_RCR_PASS)
    )
    auth_rate_limiter.reset(_RCR_KEY)
    yield _RcrDb(profile), dek
    auth_rate_limiter.reset(_RCR_KEY)


def _rcr_post(db, password, profile_id="profile-a"):
    from tests.support.routes import route_client

    with route_client(
        profiles_api.router, "/profiles", profile_id="profile-a", master_db=db,
        raise_server_exceptions=False,
    ) as client:
        return client.post(f"/profiles/{profile_id}/recovery-code", json={"password": password})


def test_hc_rcr_001_wrong_passwords_are_throttled_with_retry_after(rcr_env):
    db, _dek = rcr_env
    limit = profiles_api.settings.auth_rate_limit_max_attempts

    statuses = [_rcr_post(db, "wrong-password").status_code for _ in range(limit)]
    blocked = _rcr_post(db, "wrong-password")

    assert statuses == [401] * limit
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) >= 1
    # The throttle also stops the correct password: a guesser cannot tell.
    assert _rcr_post(db, _RCR_PASS).status_code == 429
    assert db.added == [], "a throttled request must not write an audit row"


def test_hc_rcr_002_correct_password_after_failures_succeeds_and_resets(rcr_env):
    db, dek = rcr_env
    limit = profiles_api.settings.auth_rate_limit_max_attempts

    for _ in range(limit - 1):
        assert _rcr_post(db, "wrong-password").status_code == 401
    ok = _rcr_post(db, _RCR_PASS)

    assert ok.status_code == 200, ok.text
    assert profiles_api._unseal_dek_with_recovery_code(
        "profile-a", ok.json()["recovery_code"]
    ) == dek
    assert [r.event_type for r in db.added] == ["profile.recovery_code_generated"]
    # The success cleared the window: a full set of fresh failures is allowed.
    assert [_rcr_post(db, "wrong-password").status_code for _ in range(limit)] == [401] * limit


def test_hc_rcr_003_limiter_is_checked_before_the_profile_lookup(rcr_env):
    """Ordering pinned: check first, like login. A missing-profile 404 consumes
    no failure, and an exhausted limiter answers 429 before any lookup."""
    db, _dek = rcr_env
    limit = profiles_api.settings.auth_rate_limit_max_attempts
    missing_db = _RcrDb(None)

    for _ in range(limit + 2):
        assert _rcr_post(missing_db, "x").status_code == 404
    assert _rcr_post(db, "wrong-password").status_code == 401  # nothing was consumed

    for _ in range(limit - 1):
        _rcr_post(db, "wrong-password")
    assert _rcr_post(missing_db, "x").status_code == 429
