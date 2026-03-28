"""
TEST-001: Backend test bootstrap verification.

Three assertions:
  1. pytest is importable (environment is set up correctly).
  2. TEST_MODE=1 is set (conftest.py did its job).
  3. Production default database_encryption_required=True is unchanged.

These tests guard against accidentally weakening production security
for the sake of test convenience.
"""

from __future__ import annotations

import importlib
import inspect
import os
import sys
import warnings


def test_pytest_importable() -> None:
    """Verify pytest is available in the test environment."""
    import pytest  # noqa: F401

    assert hasattr(pytest, "main"), "pytest should be importable and functional"


def test_test_mode_env_is_set() -> None:
    """Verify TEST_MODE=1 is set by conftest.py."""
    assert os.environ.get("TEST_MODE") == "1", (
        "TEST_MODE must be set to '1' in conftest.py. "
        "This ensures test-only config is active."
    )


def test_production_encryption_default_unchanged() -> None:
    """Verify the production default for database_encryption_required is True.

    This test ensures nobody has changed the production default to make
    testing easier. The test-only override belongs ONLY in conftest.py.
    """
    from core.config import Settings

    # Create a fresh Settings instance with no env overrides
    # to check the class-level default
    source = inspect.getsource(Settings)
    assert "database_encryption_required: bool = True" in source, (
        "Production default for database_encryption_required must remain True. "
        "Test-only overrides go in conftest.py, never in config.py."
    )


def test_security_import_has_no_passlib_or_crypt_deprecation_warning() -> None:
    """Verify importing the security module no longer emits passlib/crypt noise."""
    sys.modules.pop("core.security", None)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        security = importlib.import_module("core.security")

    warning_messages = [str(warning.message).lower() for warning in caught]
    assert not any(
        "passlib" in message or "crypt" in message
        for message in warning_messages
    ), "core.security import should not emit passlib/crypt deprecation warnings"
    assert hasattr(security, "hash_password")
    assert hasattr(security, "verify_password")
