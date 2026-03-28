"""Regression coverage for password hashing and verification."""

from __future__ import annotations

import bcrypt

from core.security import PASSWORD_HASH_ROUNDS, hash_password, verify_password


def test_hash_password_round_trips_with_verify() -> None:
    """New password hashes should verify successfully."""
    password = "CorrectHorseBatteryStaple!42"

    hashed_password = hash_password(password)

    assert hashed_password.startswith("$2")
    assert verify_password(password, hashed_password) is True


def test_hash_password_uses_unique_salts() -> None:
    """Hashing the same password twice should produce distinct valid hashes."""
    password = "same-password"

    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != second_hash
    assert verify_password(password, first_hash) is True
    assert verify_password(password, second_hash) is True



def test_verify_password_rejects_wrong_password() -> None:
    """Verification should fail cleanly for the wrong plaintext password."""
    hashed_password = hash_password("actual-password")

    assert verify_password("wrong-password", hashed_password) is False



def test_verify_password_rejects_invalid_bcrypt_hash(caplog) -> None:
    """Malformed stored hashes should fail closed without raising."""
    with caplog.at_level("WARNING"):
        result = verify_password("password", "not-a-valid-bcrypt-hash")

    assert result is False
    assert "not a valid bcrypt hash" in caplog.text



def test_verify_password_accepts_existing_bcrypt_hashes() -> None:
    """Direct bcrypt hashes remain compatible with the verification contract."""
    password = "legacy-compatible-password"
    legacy_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=PASSWORD_HASH_ROUNDS),
    ).decode("utf-8")

    assert verify_password(password, legacy_hash) is True
