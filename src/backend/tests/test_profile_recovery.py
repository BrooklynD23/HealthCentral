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
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

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
