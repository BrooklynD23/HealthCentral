"""HC-RESET: POST /profiles/test/reset must clear every profile-scoped table.

Audit 2026-09-25 section 11 P2: the synthetic reset skipped ChatSession,
ChatTurn, ResponseFeedback, CarePlanTask, Pinboard and PinboardItem, leaving
stale rows that cross-contaminate Playwright e2e runs. C-P7 also covers
``donated_records`` / ``donation_consents`` (RESET-APPEND) and the runtime
``search_records`` / ``search_records_fts`` tables (N-02, option a).

Every route test goes through HTTP (``route_client``) against a real file-backed
vault with ``PRAGMA foreign_keys=ON``, so child-first ordering is enforced the
way it is in production.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

sys.path.insert(0, str(Path(__file__).parent.parent))

import models  # noqa: E402,F401  registers every model
import models.response_feedback  # noqa: E402,F401  not exported by models/__init__
from api.profiles import router  # noqa: E402
from core.config import settings  # noqa: E402
from core.database import install_sqlite_foreign_keys  # noqa: E402
from core.profile_database import ProfileDatabaseBase  # noqa: E402
from modules.search import (  # noqa: E402
    _INSERT_FTS_SQL,
    _INSERT_SQL,
    ensure_search_index,
)
from tests.support.routes import route_client  # noqa: E402
from tests.test_fk_enforcement import _row  # noqa: E402  NOT NULL filler

E2E_NAME = "Playwright E2E Reset"

# Migration-seeded reference data (profile migration 003): the reset keeps it.
REFERENCE_TABLES = {"badge_definition"}

# The six tables the audit flagged as missed.
AUDIT_FLAGGED_TABLES = (
    "response_feedback",
    "pinboard_item",
    "pinboard",
    "chat_turns",
    "chat_sessions",
    "care_plan_task",
)
DONATION_TABLES = ("donated_records", "donation_consents")
SEARCH_TABLES = ("search_records", "search_records_fts")


@pytest_asyncio.fixture
async def vault(tmp_path, monkeypatch):
    """A real file-backed profile vault, FK pragma ON like production.

    NullPool: the route runs on TestClient's portal loop and pooled aiosqlite
    connections are bound to the loop that opened them.
    """
    monkeypatch.setattr(type(settings), "app_data_path", property(lambda self: tmp_path))
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'vault.db'}", poolclass=NullPool)
    install_sqlite_foreign_keys(engine.sync_engine)
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    yield engine
    await engine.dispose()


def _factory(engine) -> async_sessionmaker:
    return async_sessionmaker(engine, expire_on_commit=False)


def _with_parents(names) -> list[str]:
    """`names` plus every FK ancestor, parents first (metadata order)."""
    tables = ProfileDatabaseBase.metadata.tables
    wanted: set[str] = set()
    stack = list(names)
    while stack:
        name = stack.pop()
        if name in wanted:
            continue
        wanted.add(name)
        stack.extend(fk.column.table.name for fk in tables[name].foreign_keys)
    return [t.name for t in ProfileDatabaseBase.metadata.sorted_tables if t.name in wanted]


async def _seed(engine, names) -> list[str]:
    """Insert one row into each of `names` and their FK parents; return the list."""
    ordered = _with_parents(names)
    tables = ProfileDatabaseBase.metadata.tables

    def _insert(sc):
        for name in ordered:
            fks = {fk.parent.name: f"{fk.column.table.name}-1" for fk in tables[name].foreign_keys}
            _row(sc, name, id=f"{name}-1", **fks)

    async with engine.begin() as conn:
        await conn.run_sync(_insert)
    return ordered


async def _seed_search_rows(engine) -> None:
    """Create the runtime search tables and put one row in each."""
    async with _factory(engine)() as session:
        fts_ok = await ensure_search_index(session)
        assert fts_ok is True, "FTS5 is required for this test: search_records_fts was not created"
        row = {
            "row_key": "k1", "record_type": "document", "record_id": "r1", "doc_id": "documents-1",
            "profile_id": "profile-a", "title": "stale title", "content": "stale content",
            "record_date": None, "provider": "", "category": "", "verified_status": "verified",
            "highlight_types": "",
        }
        await session.execute(text(_INSERT_SQL), row)
        await session.execute(text(_INSERT_FTS_SQL), row)
        await session.commit()


async def _counts(engine, names) -> dict[str, int]:
    async with engine.connect() as conn:
        return {
            n: (await conn.execute(text(f'SELECT count(*) FROM "{n}"'))).scalar() for n in names
        }


async def _search_tables_present(engine) -> set[str]:
    async with engine.connect() as conn:
        rows = await conn.execute(text("SELECT name FROM sqlite_master WHERE name LIKE 'search_records%'"))
        return {r[0] for r in rows} & set(SEARCH_TABLES)


def _reset(engine, profile_name: str = E2E_NAME):
    with route_client(
        router,
        "/profiles",
        profile_id="profile-a",
        profile_name=profile_name,
        profile_db=_factory(engine),
    ) as client:
        return client.post("/profiles/test/reset")


@pytest.mark.asyncio
async def test_hc_reset_001_clears_audit_flagged_donation_and_search_tables(vault):
    """The 6 audit-flagged tables, both donation tables and both search tables
    are seeded (each count >= 1), then all go to 0 through the HTTP route."""
    seeded = await _seed(vault, AUDIT_FLAGGED_TABLES + DONATION_TABLES)
    await _seed_search_rows(vault)
    checked = seeded + list(SEARCH_TABLES)

    before = await _counts(vault, checked)
    assert all(n >= 1 for n in before.values()), before
    for required in AUDIT_FLAGGED_TABLES + DONATION_TABLES + SEARCH_TABLES:
        assert required in before

    resp = _reset(vault)

    assert resp.status_code == 204, resp.text
    after = await _counts(vault, checked)
    assert after == {n: 0 for n in checked}, after


@pytest.mark.asyncio
async def test_hc_reset_002_fresh_vault_without_search_tables_resets_cleanly(vault):
    """A fresh vault has no search tables (they appear after a first search).
    The reset must still return 204, empty every table in the list, and must
    not create the search tables."""
    from api.profiles import _SYNTHETIC_RESET_MODELS

    reset_tables = [m.__tablename__ for m in _SYNTHETIC_RESET_MODELS]
    seeded = await _seed(vault, reset_tables)
    before = await _counts(vault, reset_tables)
    assert set(reset_tables) <= set(seeded)
    assert all(n >= 1 for n in before.values()), before
    assert await _search_tables_present(vault) == set()

    resp = _reset(vault)

    assert resp.status_code == 204, resp.text
    assert await _counts(vault, reset_tables) == {n: 0 for n in reset_tables}
    assert await _search_tables_present(vault) == set(), "the reset must not create the search tables"


def test_hc_reset_010_reset_list_covers_every_profile_table():
    """Anti-drift: a new profile table not added to the reset list fails here."""
    from api.profiles import _SYNTHETIC_RESET_MODELS

    all_tables = set(ProfileDatabaseBase.metadata.tables)
    covered = [m.__tablename__ for m in _SYNTHETIC_RESET_MODELS]
    assert len(covered) == len(set(covered)), "a model is listed twice"
    assert set(covered) == all_tables - REFERENCE_TABLES, (
        f"reset misses {sorted(all_tables - REFERENCE_TABLES - set(covered))}; "
        f"unexpected extras {sorted(set(covered) - all_tables)}"
    )


def test_hc_reset_011_delete_order_respects_foreign_keys():
    """With the FK pragma ON a parent-first order raises IntegrityError."""
    from api.profiles import _SYNTHETIC_RESET_MODELS

    order = {m.__tablename__: i for i, m in enumerate(_SYNTHETIC_RESET_MODELS)}
    edges = 0
    for table in ProfileDatabaseBase.metadata.tables.values():
        if table.name not in order:
            continue
        for fk in table.foreign_keys:
            parent = fk.column.table.name
            if parent in order:
                edges += 1
                assert order[table.name] < order[parent], f"{table.name} is deleted after its parent {parent}"
    assert edges >= 1, "no FK edge was checked, the test proves nothing"


@pytest.mark.asyncio
async def test_hc_reset_020_production_is_404_and_deletes_nothing(vault, monkeypatch):
    """P7-ROUTE: this route (which now deletes consent rows) is unreachable in
    production. Asserted through HTTP, and the seeded rows must still be there."""
    tables = ["donation_consents", "donated_records", "chat_turns"]
    seeded = await _seed(vault, tables)
    before = await _counts(vault, seeded)
    assert all(n >= 1 for n in before.values()), before
    monkeypatch.setattr(settings, "app_env", "production")

    resp = _reset(vault, "Playwright E2E Production Probe")

    assert resp.status_code == 404
    assert await _counts(vault, seeded) == before


@pytest.mark.asyncio
async def test_hc_reset_021_non_synthetic_profile_is_403_and_deletes_nothing(vault):
    seeded = await _seed(vault, ["donation_consents", "chat_sessions"])
    before = await _counts(vault, seeded)
    assert all(n >= 1 for n in before.values()), before

    resp = _reset(vault, "Regular User")

    assert resp.status_code == 403
    assert await _counts(vault, seeded) == before


@pytest.mark.asyncio
async def test_hc_reset_030_badge_definitions_survive(vault):
    """badge_definition is seed data: kept. earned_badge points at it: cleared."""
    seeded = await _seed(vault, ["earned_badge"])
    before = await _counts(vault, ["badge_definition", "earned_badge"])
    assert "badge_definition" in seeded
    assert before == {"badge_definition": 1, "earned_badge": 1}

    resp = _reset(vault)

    assert resp.status_code == 204, resp.text
    assert await _counts(vault, ["badge_definition", "earned_badge"]) == {
        "badge_definition": 1,
        "earned_badge": 0,
    }
