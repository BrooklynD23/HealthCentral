"""One-time filesystem migrations that must run before any DB connection opens.

The master database is the only index of which profiles exist, and the only home
of password_hash and encryption_key_id. If the application looks for a filename
that is not present, Alembic creates an empty one and the profile list renders
empty — every vault on disk intact but unreachable. That is why the rename and
this migration are a single change.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

LEGACY_MASTER_DB_NAME = "healthcentral.db"
MASTER_DB_NAME = "asclexis.db"

# SQLite in WAL mode keeps these beside the database. Renaming only the main
# file orphans any unflushed transactions in the -wal.
_SIDECAR_SUFFIXES = ("-wal", "-shm")


def migrate_master_db_filename(data_dir: Path) -> bool:
    """Rename the legacy master DB (and its sidecars) if that is safe.

    Returns True if a rename happened, False if there was nothing to do.

    Guarded on absent-target AND present-source, so it is idempotent and a
    no-op on a fresh install. If both files exist the new one wins and the
    legacy file is left in place: silently clobbering a live database would be
    the worst possible outcome of a cosmetic rename.
    """
    data_dir = Path(data_dir)
    legacy = data_dir / LEGACY_MASTER_DB_NAME
    current = data_dir / MASTER_DB_NAME

    if not legacy.exists():
        return False

    if current.exists():
        logger.warning(
            "Both %s and %s exist; keeping %s and leaving the legacy file in "
            "place for inspection.",
            LEGACY_MASTER_DB_NAME,
            MASTER_DB_NAME,
            MASTER_DB_NAME,
        )
        return False

    legacy.rename(current)
    for suffix in _SIDECAR_SUFFIXES:
        sidecar = data_dir / f"{LEGACY_MASTER_DB_NAME}{suffix}"
        if sidecar.exists():
            sidecar.rename(data_dir / f"{MASTER_DB_NAME}{suffix}")

    logger.info("Migrated master database filename to %s", MASTER_DB_NAME)
    return True
