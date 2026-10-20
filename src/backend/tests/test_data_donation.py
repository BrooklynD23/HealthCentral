"""RSI1-DONATE PR-1 schema: donation_consents and donated_records (HC-DON-001..003)."""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from alembic.script import ScriptDirectory

TABLES = ("donation_consents", "donated_records")
RAW_COLUMN = re.compile(r"raw|original|unredacted|plain", re.I)


def _tables(vault_path: Path, key: bytes) -> set[str]:
    from sqlalchemy import create_engine, event, inspect

    from core.sqlcipher_driver import get_sqlcipher_module, is_sqlcipher_available

    url = f"sqlite:///{vault_path}"
    if is_sqlcipher_available():
        mod = get_sqlcipher_module()
        engine = create_engine(url, creator=lambda: mod.connect(str(vault_path)))
    else:
        engine = create_engine(url)

    @event.listens_for(engine, "connect")
    def _key(dbapi_conn, _rec):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA cipher_version")
        row = cur.fetchone()
        if row and row[0]:
            cur.execute(f"PRAGMA key = \"x'{key.hex()}'\"")
        cur.close()

    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_hc_don_001_migration_round_trip_single_head(tmp_path, monkeypatch):
    from alembic import command

    from core import migrations
    from core.config import settings

    monkeypatch.setattr(settings, "database_encryption_required", False)
    vault, key = tmp_path / "vault.db", b"0" * 32
    migrations.run_profile_migration(vault, key)
    cfg = migrations._get_alembic_config("profile")
    cfg.attributes["vault_path"] = vault
    cfg.attributes["encryption_key"] = key

    script = ScriptDirectory.from_config(cfg)
    assert script.get_heads() == ["015_data_donation"]
    rev = script.get_revision("015_data_donation")
    assert rev.down_revision == "014_streaks_hidden"

    assert migrations.get_profile_current_revision(vault, key) == "015_data_donation"
    assert set(TABLES) <= _tables(vault, key)

    command.downgrade(cfg, "014_streaks_hidden")
    assert not set(TABLES) & _tables(vault, key)

    command.upgrade(cfg, "head")
    assert set(TABLES) <= _tables(vault, key)


def test_hc_don_002_no_raw_text_column():
    from models.data_donation import DonatedRecord, DonationConsent

    for model in (DonationConsent, DonatedRecord):
        bad = [c.name for c in model.__table__.columns if RAW_COLUMN.search(c.name)]
        assert not bad, f"{model.__tablename__} has raw-text-looking columns: {bad}"
    assert {"prompt_redacted", "response_redacted"} <= set(DonatedRecord.__table__.columns.keys())
    assert not DonatedRecord.__table__.foreign_keys
    assert not DonationConsent.__table__.foreign_keys


def test_hc_don_003_profile_metadata_only():
    import models  # noqa: F401  (registers every model)
    from core.database import Base
    from core.profile_database import ProfileDatabaseBase

    for t in TABLES:
        assert t in ProfileDatabaseBase.metadata.tables
        assert t not in Base.metadata.tables
