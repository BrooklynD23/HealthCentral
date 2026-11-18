"""PANEL-CANONICAL-NAMES: PANEL_DEFINITIONS must list the names the normalizer stores.

`NormalizeModule.normalize_analyte` stores `white_blood_cells`, `ldl_cholesterol`,
`free_t4` and friends. PANEL_DEFINITIONS listed `wbc`, `ldl`, `t4_free`, so a real
upload never matched its panel: the panel routes and the panel interpretation
skipped those rows, and strict safety mode did not see them as panel members.

Every route test goes through HTTP (`route_client`) with a real in-memory master DB
and profile DB. Names are seeded through the real normalizer, never hard-coded.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

import models  # noqa: F401  register every table on both bases
from api.assistant import router as assistant_router
from api.interpretations import router as interpretations_router
from api.observations import PANEL_DEFINITIONS
from api.observations import router as observations_router
from core.auth import get_profile_db_session
from core.database import Base
from core.profile_database import ProfileDatabaseBase
from models import LabInterpretation, Observation, PanelInterpretation
from modules.normalize import NormalizeModule
from tests.support.routes import route_client

PROFILE_ID = "profile-a"  # route_client's default session profile_id
COLLECTED = datetime(2026, 3, 1, 9, 0, 0)
COLLECTED_TXT = "2026-03-01T09:00:00"

# (panel, raw lab label, name the row used before the fix). The stored name is
# whatever the normalizer returns for the raw label.
STORED_NAMES = [
    ("cbc", "WBC", "wbc"),
    ("cbc", "RBC", "rbc"),
    ("cmp", "CO2", "co2"),
    ("cmp", "Protein, Total", "protein_total"),
    ("lipid", "Cholesterol", "cholesterol_total"),
    ("lipid", "HDL", "hdl"),
    ("lipid", "LDL", "ldl"),
    ("thyroid", "FT3", "t3_free"),
    ("thyroid", "FT4", "t4_free"),
]
STORED_PARAMS = [pytest.param(p, raw, old, id=raw) for p, raw, old in STORED_NAMES]


def _stored(raw: str) -> str:
    return NormalizeModule().normalize_analyte(raw).canonical_name


# ---------------------------------------------------------------------------
# Databases and HTTP helpers (same pattern as test_safety_mode_verified.py)
# ---------------------------------------------------------------------------

async def _engine_session(base):
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(base.metadata.create_all)
    return AsyncSession(engine, expire_on_commit=False), engine


@dataclass
class Db:
    profile: AsyncSession
    master: AsyncSession
    ids: list[str]


@asynccontextmanager
async def _dbs(rows):
    """rows: (analyte_canonical, value, is_abnormal, user_verified). One document, one day."""
    profile_db, p_engine = await _engine_session(ProfileDatabaseBase)
    master_db, m_engine = await _engine_session(Base)
    try:
        doc_id = str(uuid.uuid4())
        ids = []
        for analyte, value, abnormal, verified in rows:
            obs = Observation(
                id=str(uuid.uuid4()), profile_id=PROFILE_ID, doc_id=doc_id,
                analyte_canonical=analyte, analyte_raw=analyte, value=value,
                unit="mg/dL", ref_low=0.0, ref_high=100.0, collected_at=COLLECTED,
                flag="H" if abnormal else None, is_abnormal=abnormal,
                user_verified=verified,
            )
            profile_db.add(obs)
            ids.append(obs.id)
        await profile_db.commit()
        yield Db(profile_db, master_db, ids)
    finally:
        await profile_db.close()
        await master_db.close()
        await p_engine.dispose()
        await m_engine.dispose()


def _call(db: Db, method: str, url: str, *, router=interpretations_router,
          prefix: str = "/interpretations", **kwargs):
    with route_client(router, prefix, profile_id=PROFILE_ID, master_db=db.master) as client:
        async def _profile_db():
            return db.profile
        client.app.dependency_overrides[get_profile_db_session] = _profile_db
        return client.request(method, url, **kwargs)


def _get_panel(db: Db, panel: str):
    return _call(db, "GET", f"/observations/panels/{panel}",
                 router=observations_router, prefix="/observations")


def _get_snapshots(db: Db, panel: str):
    return _call(db, "GET", f"/observations/panels/{panel}/snapshots",
                 router=observations_router, prefix="/observations")


def _interpret_panel(db: Db, panel: str):
    return _call(db, "POST", f"/interpretations/panels/{panel}/interpret",
                 params={"collected_at": COLLECTED_TXT})


async def _set_strict(db: Db) -> None:
    """Switch strict mode on through PATCH /assistant/safety-mode, with a throwaway master
    DB so the setting's own audit row does not reach the real one."""
    throwaway = Db(db.profile, MagicMock(commit=AsyncMock()), db.ids)
    resp = _call(throwaway, "PATCH", "/assistant/safety-mode", router=assistant_router,
                 prefix="/assistant", json={"strict_safety_mode": True})
    assert resp.status_code == 200, resp.text


async def _card_observation_ids(db: Db) -> list[str]:
    """Observation ids that got a per-row interpretation card. Wording-independent."""
    db.profile.expire_all()
    rows = (await db.profile.execute(select(LabInterpretation.observation_id))).scalars().all()
    return list(rows)


async def _stored_panels(db: Db) -> list[PanelInterpretation]:
    db.profile.expire_all()
    return list((await db.profile.execute(select(PanelInterpretation))).scalars().all())


# ---------------------------------------------------------------------------
# HC-PCN-001: GET /observations/panels/{panel} returns the normalizer-named row
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("panel,raw,old", STORED_PARAMS)
async def test_hc_pcn_001_panel_route_returns_normalizer_named_row(panel, raw, old):
    stored = _stored(raw)
    async with _dbs([(stored, 50.0, False, True)]) as db:
        resp = _get_panel(db, panel)

    assert resp.status_code == 200, resp.text
    returned = [o["id"] for o in resp.json()["observations"]]
    assert returned == db.ids, f"{stored!r} (from {raw!r}) is not a member of panel {panel!r}"


# ---------------------------------------------------------------------------
# HC-PCN-002: the snapshots route returns them in panel order
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_pcn_002_cbc_snapshot_order_is_wbc_rbc_hemoglobin():
    wbc, rbc = _stored("WBC"), _stored("RBC")
    # Inserted out of panel order on purpose.
    async with _dbs([("hemoglobin", 14.0, False, True), (rbc, 4.8, False, True),
                     (wbc, 6.0, False, True)]) as db:
        resp = _get_snapshots(db, "cbc")

    assert resp.status_code == 200, resp.text
    snapshots = resp.json()
    assert len(snapshots) == 1
    assert [o["analyte_canonical"] for o in snapshots[0]["observations"]] == [
        "white_blood_cells", "red_blood_cells", "hemoglobin",
    ]


@pytest.mark.asyncio
async def test_hc_pcn_002_lipid_snapshot_order():
    total, hdl, ldl = _stored("Cholesterol"), _stored("HDL"), _stored("LDL")
    async with _dbs([(ldl, 90.0, False, True), (hdl, 55.0, False, True),
                     ("triglycerides", 120.0, False, True), (total, 180.0, False, True)]) as db:
        resp = _get_snapshots(db, "lipid")

    assert resp.status_code == 200, resp.text
    snapshots = resp.json()
    assert len(snapshots) == 1
    assert [o["analyte_canonical"] for o in snapshots[0]["observations"]] == [
        "total_cholesterol", "triglycerides", "hdl_cholesterol", "ldl_cholesterol",
    ]


# ---------------------------------------------------------------------------
# HC-PCN-003: panel interpretation includes the normalizer-named row
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("panel,raw,old", STORED_PARAMS)
async def test_hc_pcn_003_panel_interpretation_includes_normalizer_named_row(panel, raw, old):
    stored = _stored(raw)
    async with _dbs([(stored, 50.0, False, True)]) as db:
        resp = _interpret_panel(db, panel)
        # observation_ids is appended before the card exists; a withheld card would still
        # pass the assertions below and drop the row from the summary. Assert the card
        # itself (not the summary wording, which #482 edits). Read it before the DB closes.
        cards = await _card_observation_ids(db)

    assert resp.status_code == 201, resp.text
    assert resp.json()["observation_ids"] == db.ids
    assert cards == db.ids


@pytest.mark.asyncio
async def test_hc_pcn_003_abnormal_ldl_cholesterol_alone_is_not_a_normal_panel():
    ldl = _stored("LDL")
    async with _dbs([(ldl, 190.0, True, True)]) as db:
        resp = _interpret_panel(db, "lipid")

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["observation_ids"] == db.ids
    assert body["overall_status"] != "normal"


# ---------------------------------------------------------------------------
# HC-PCN-004: strict mode counts the normalizer-named row as a panel member
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hc_pcn_004_strict_mode_refuses_panel_with_unverified_ldl_cholesterol():
    ldl = _stored("LDL")
    async with _dbs([("triglycerides", 120.0, False, True), (ldl, 130.0, False, False)]) as db:
        await _set_strict(db)
        resp = _interpret_panel(db, "lipid")
        stored = await _stored_panels(db)

    assert resp.status_code == 409, resp.text
    assert stored == [], "a panel was generated with an unverified member"


# ---------------------------------------------------------------------------
# HC-PCN-005: the names used before the fix still match. These guard the fix and
# may pass on main; they are not the RED for the bug.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("panel,raw,old", STORED_PARAMS)
async def test_hc_pcn_005_old_name_still_returned_by_panel_route(panel, raw, old):
    async with _dbs([(old, 50.0, False, True)]) as db:
        resp = _get_panel(db, panel)

    assert resp.status_code == 200, resp.text
    assert [o["id"] for o in resp.json()["observations"]] == db.ids


@pytest.mark.asyncio
@pytest.mark.parametrize("panel,raw,old", STORED_PARAMS)
async def test_hc_pcn_005_old_name_still_in_panel_interpretation(panel, raw, old):
    async with _dbs([(old, 50.0, False, True)]) as db:
        resp = _interpret_panel(db, panel)

    assert resp.status_code == 201, resp.text
    assert resp.json()["observation_ids"] == db.ids


# ---------------------------------------------------------------------------
# HC-PCN-006: every panel name can be produced. normalize_analyte returns any
# unknown snake_case name unchanged, so `normalize(name) == name` cannot fail;
# the check is membership in ANALYTE_SYNONYMS or a named, reasoned exception.
# ---------------------------------------------------------------------------

NOT_SYNONYM_KEYS = {
    "wbc": "old name kept: the normalizer now stores white_blood_cells",
    "rbc": "old name kept: the normalizer now stores red_blood_cells",
    "co2": "old name kept: the normalizer now stores carbon_dioxide",
    "protein_total": "old name kept: the normalizer now stores total_protein",
    "cholesterol_total": "old name kept: the normalizer now stores total_cholesterol",
    "hdl": "old name kept: the normalizer now stores hdl_cholesterol",
    "ldl": "old name kept: the normalizer now stores ldl_cholesterol",
    "t3_free": "old name kept: the normalizer now stores free_t3",
    "t4_free": "old name kept: the normalizer now stores free_t4",
    "mpv": "not a synonym key; stored only through the snake_case fallback",
    "vldl": "not a synonym key; stored only through the snake_case fallback",
    "t3_total": "not a synonym key; stored only through the snake_case fallback",
    "t4_total": "not a synonym key; stored only through the snake_case fallback",
}


def _panel_names() -> set[str]:
    return {n for d in PANEL_DEFINITIONS.values() for n in d["analytes"]}


def test_hc_pcn_006_every_panel_name_is_a_synonym_key_or_a_named_exception():
    keys = set(NormalizeModule.ANALYTE_SYNONYMS)
    unexplained = sorted(_panel_names() - keys - set(NOT_SYNONYM_KEYS))
    assert unexplained == [], f"panel names the normalizer never stores, with no reason: {unexplained}"


def test_hc_pcn_006_every_exception_is_still_a_panel_name_and_not_a_synonym_key():
    keys = set(NormalizeModule.ANALYTE_SYNONYMS)
    stale = sorted(set(NOT_SYNONYM_KEYS) - _panel_names())
    assert stale == [], f"exceptions no longer in any panel: {stale}"
    promoted = sorted(set(NOT_SYNONYM_KEYS) & keys)
    assert promoted == [], f"exceptions that are now synonym keys, drop them: {promoted}"


# ---------------------------------------------------------------------------
# HC-PCN-007: every name the normalizer categorises under a panel is a member
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("panel", ["cbc", "cmp", "lipid", "thyroid"])
def test_hc_pcn_007_normalizer_category_is_subset_of_panel_definition(panel):
    missing = sorted(set(NormalizeModule.ANALYTE_CATEGORIES[panel]) - set(PANEL_DEFINITIONS[panel]["analytes"]))
    assert missing == [], f"{panel}: normalizer-stored names missing from PANEL_DEFINITIONS: {missing}"
