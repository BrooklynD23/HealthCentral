"""SQLCipher-enabled driver utilities.

Provides a unified interface for SQLCipher encryption support.
Falls back to stdlib sqlite3 if sqlcipher3 is not installed.
"""

import logging

logger = logging.getLogger(__name__)

try:
    import sqlcipher3 as _sqlcipher_module
    SQLCIPHER_AVAILABLE = True
except ImportError:
    import sqlite3 as _sqlcipher_module
    SQLCIPHER_AVAILABLE = False
    logger.warning("sqlcipher3 not available - using stdlib sqlite3")


def is_sqlcipher_available() -> bool:
    """Check if SQLCipher is available."""
    return SQLCIPHER_AVAILABLE


def get_sqlcipher_module():
    """Get the SQLCipher module (or sqlite3 fallback)."""
    return _sqlcipher_module


def verify_cipher_version() -> str | None:
    """Return SQLCipher version or None if unavailable."""
    try:
        conn = _sqlcipher_module.connect(":memory:")
        cursor = conn.cursor()
        cursor.execute("PRAGMA cipher_version")
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception:
        return None
