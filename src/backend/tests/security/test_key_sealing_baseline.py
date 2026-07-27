"""Baseline coverage for profile key sealing — SEC-RECOV-001 step 0.

Before this file there were **no** tests for ``seal_key_with_dpapi`` /
``unseal_key_with_dpapi``. SEC-RECOV-001's acceptance criterion is "the
existing password unlock path is byte-for-byte unaffected", which is
unverifiable without a baseline. These tests pin the current behaviour so the
recovery-key work has something to regress against.

Nothing here is recovery-specific: it is the pre-change contract.

Test IDs: HC-RECOV-00N.
"""

from __future__ import annotations

import pytest

from core.security import (
    KeySealingError,
    derive_key_from_password,
    generate_encryption_key,
    generate_salt,
    seal_key_with_dpapi,
    unseal_key_with_dpapi,
)


def test_hc_recov_001_password_seal_roundtrip():
    key = generate_encryption_key()

    sealed, method = seal_key_with_dpapi(key, fallback_password="CorrectHorse1")

    assert method == "password"
    assert unseal_key_with_dpapi(sealed, method, fallback_password="CorrectHorse1") == key


def test_hc_recov_002_wrong_password_raises_keysealingerror():
    key = generate_encryption_key()
    sealed, method = seal_key_with_dpapi(key, fallback_password="CorrectHorse1")

    with pytest.raises(KeySealingError):
        unseal_key_with_dpapi(sealed, method, fallback_password="WrongHorse2")


def test_hc_recov_002b_sealing_without_password_or_dpapi_fails_closed():
    """No silent plaintext fallback: with neither DPAPI nor a password the
    call must fail rather than store an unsealed key."""
    with pytest.raises(KeySealingError):
        seal_key_with_dpapi(generate_encryption_key(), fallback_password=None)


def test_hc_recov_002c_sealed_blob_layout_is_salt_prefixed():
    """The wire format is `16-byte salt || Fernet(key)`. Any second sealed
    copy must reuse this exact layout so one parser serves both."""
    key = generate_encryption_key()
    sealed, _ = seal_key_with_dpapi(key, fallback_password="CorrectHorse1")

    salt, encrypted = sealed[:16], sealed[16:]
    assert len(salt) == 16
    fernet_key = derive_key_from_password("CorrectHorse1", salt)

    from cryptography.fernet import Fernet

    assert Fernet(fernet_key).decrypt(encrypted) == key


def test_hc_recov_002d_truncated_blob_is_rejected():
    with pytest.raises(KeySealingError):
        unseal_key_with_dpapi(b"tooshort", "password", fallback_password="CorrectHorse1")


def test_hc_recov_002e_unknown_seal_method_is_rejected():
    with pytest.raises(KeySealingError):
        unseal_key_with_dpapi(b"x" * 64, "magic", fallback_password="CorrectHorse1")


def test_hc_recov_002f_each_seal_uses_a_fresh_salt():
    """Two seals of the same key under the same password must differ, or the
    sealed blob leaks equality information."""
    key = generate_encryption_key()
    first, _ = seal_key_with_dpapi(key, fallback_password="CorrectHorse1")
    second, _ = seal_key_with_dpapi(key, fallback_password="CorrectHorse1")

    assert first[:16] != second[:16]
    assert first != second


def test_hc_recov_002g_derive_key_is_deterministic_per_salt():
    salt = generate_salt()
    assert derive_key_from_password("CorrectHorse1", salt) == derive_key_from_password(
        "CorrectHorse1", salt
    )
    assert derive_key_from_password("CorrectHorse1", salt) != derive_key_from_password(
        "CorrectHorse1", generate_salt()
    )
