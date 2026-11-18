"""EXPORT-REF-NONE: the reference range in the doctor summary and visit packet never prints "None".

HC-ERN-001  doctor summary, no bounds, printed range "<100" -> "(ref: <100)"
HC-ERN-002  visit packet, same -> "(ref <100)"
HC-ERN-003  one-sided bounds -> "up to 100.0" / "0.0 and above" in both texts; neither + no text -> "not printed"
HC-ERN-004  both bounds -> byte-identical to before ("70.0-99.0")
HC-ERN-005  through HTTP (pinboard export) the printed range reaches the packet
"""

import uuid
from datetime import datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from core.profile_database import ProfileDatabaseBase
from modules.export import ExportModule

COLLECTED = datetime(2026, 3, 1, 9, 0, 0)


def _obs(**kw) -> dict:
    base = {
        "id": str(uuid.uuid4()),
        "analyte_canonical": "ldl_cholesterol",
        "value": 162.0,
        "unit": "mg/dL",
        "ref_low": None,
        "ref_high": None,
        "ref_range_text": None,
        "flag": "H",
        "is_abnormal": True,
        "user_verified": True,
        "collected_at": COLLECTED,
    }
    base.update(kw)
    return base


async def _summary_line(obs: dict) -> str:
    summary = await ExportModule().generate_doctor_summary(
        profile_id=str(uuid.uuid4()), observations=[obs], trends=[]
    )
    section = next(s for s in summary.sections if s.title == "Values Outside Reference Range")
    return section.content


def _packet_line(obs: dict) -> str:
    packet = ExportModule().compose_visit_prep_packet(
        profile_id=str(uuid.uuid4()), observations=[obs]
    )
    section = next(s for s in packet["sections"] if "bservation" in s["title"] or "Lab" in s["title"])
    return section["content"]


@pytest.mark.asyncio
async def test_hc_ern_001_summary_prints_the_reports_range_when_no_bounds():
    text = await _summary_line(_obs(ref_range_text="<100"))
    assert "(ref: <100)" in text
    assert "None" not in text


def test_hc_ern_002_packet_prints_the_reports_range_when_no_bounds():
    text = _packet_line(_obs(ref_range_text="<100"))
    assert "(ref <100)" in text
    assert "None" not in text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kw,want",
    [
        (dict(ref_high=100.0), "up to 100.0"),
        (dict(ref_low=0.0), "0.0 and above"),
        (dict(), "not printed"),
    ],
    ids=["high-only", "low-only", "nothing-known"],
)
async def test_hc_ern_003_one_sided_and_unknown_ranges(kw, want):
    summary = await _summary_line(_obs(**kw))
    packet = _packet_line(_obs(**kw))
    assert f"(ref: {want})" in summary and "None" not in summary
    assert f"(ref {want})" in packet and "None" not in packet


@pytest.mark.asyncio
async def test_hc_ern_004_two_sided_range_is_byte_identical():
    obs = _obs(ref_low=70.0, ref_high=99.0, ref_range_text="70-99")
    assert "(ref: 70.0-99.0)" in await _summary_line(obs)
    assert "(ref 70.0-99.0)" in _packet_line(obs)


@pytest_asyncio.fixture
async def real_profile_db():
    from models import Pinboard, PinboardItem  # noqa: F401 -- register tables

    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(ProfileDatabaseBase.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_hc_ern_005_pinboard_export_over_http_shows_the_printed_range(real_profile_db):
    import api.export as export_api
    import api.pinboards as pinboards_api
    from core.auth import get_profile_db_session
    from core.time import utcnow
    from models import Observation
    from models.pinboard import Pinboard, PinboardItem
    from tests.support.routes import route_client

    db = real_profile_db
    observation = Observation(
        id=str(uuid.uuid4()), profile_id="profile-a", doc_id=str(uuid.uuid4()),
        analyte_canonical="ldl_cholesterol", analyte_raw="LDL",
        value=162.0, unit="mg/dL", ref_low=None, ref_high=None, ref_range_text="<100",
        flag="H", is_abnormal=True, user_verified=True, collected_at=COLLECTED,
    )
    board = Pinboard(id=str(uuid.uuid4()), name="Next appointment",
                     created_at=utcnow(), updated_at=utcnow())
    db.add_all([observation, board])
    await db.flush()
    db.add(PinboardItem(id=str(uuid.uuid4()), pinboard_id=board.id, item_type="observation",
                        item_id=observation.id, created_at=utcnow()))
    await db.commit()

    packet_id = None
    try:
        with route_client(pinboards_api.router, "/pinboards", profile_id="profile-a") as client:

            async def _override_profile_db():
                return db

            client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
            response = client.post(f"/pinboards/{board.id}/export", json={"confirm": True})
            assert response.status_code == 200, response.text
            packet_id = response.json()["packet_id"]
            markdown = response.json()["markdown"]
        assert "ldl_cholesterol" in markdown.lower() or "LDL" in markdown, markdown
        assert "(ref <100)" in markdown, markdown
        assert "None" not in markdown
    finally:
        if packet_id is not None:
            export_api._packet_store.pop(packet_id, None)
