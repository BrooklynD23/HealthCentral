"""ASSIST-AGENT-DATES — the agent chat path honours the chat filters.

Owner rows AAD-ROW (2026-10-16) and AAD-SEMANTICS (2026-10-17):
- dates narrow observations and document chunks to the window;
- selected_analytes / selected_panel ADD to the analytes the question asks
  about (parity with legacy rag.py `_get_observation_chunks`); a selection never
  hides an observation the question itself asks about;
- document_category (and the analyte selection) narrow document chunks, as
  legacy `_search_vectors_async` does;
- the no-model fallback's `_fetch_latest_obs` honours the date window;
- the semantic cache never serves an answer across different filters.

Route-level tests go through HTTP (tests/support/routes.py::route_client) and
run the real `run_agent` graph against a real in-memory profile DB, so a filter
that only reached the cache key (and not the tool query) would still fail on
the cited observation ids. `retrieve_chunks` is not planned by today's
deterministic planner, so its filters are asserted at the tool (HC-AAD-004,
HC-AAD-010).
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

import api.assistant as A
from api.assistant import router as assistant_router
from core.auth import get_profile_db_session
from core.profile_database import ProfileDatabaseBase
from models import care_plan_task, chat_session, medication, model_settings  # noqa: F401  register tables
from models.care_plan_task import CarePlanTask
from models.chunk import Chunk
from models.document import Document
from models.document_category import DocumentCategory, DocumentEntity
from models.medication import Medication
from models.observation import Observation
from modules.agent.cache import clear_cache
from modules.agent.graph import RunContext
from modules.agent.schemas import AgentTerminal
from modules.agent.state import ChatFilters
from modules.agent.tools.query_observations import QueryObservationsInput, QueryObservationsTool
from modules.agent.tools.retrieve_chunks import RetrieveChunksInput, RetrieveChunksTool
from modules.knowledge_loader import BiomarkerInfo
from modules.rag import ModelUnavailableError
from tests.support.routes import route_client

PROFILE = "profile-a"  # route_client's default session
JAN = datetime(2026, 1, 15, 12, 0, 0)
JUN = datetime(2026, 6, 15, 0, 0, 0)  # stored naive UTC


async def _make_db():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    db = AsyncSession(engine, expire_on_commit=False)
    for doc_id, when, category in (("doc-jan", JAN, "lab"), ("doc-jun", JUN, "imaging")):
        db.add(Document(
            id=doc_id, profile_id=PROFILE, path_hash=doc_id, content_hash=doc_id,
            doc_type="pdf", status="verified", collection_date=when, imported_at=when,
        ))
        db.add(DocumentCategory(doc_id=doc_id, category=category, confidence=1.0, classified_by="t"))
        db.add(Chunk(id=f"chunk-{doc_id}", doc_id=doc_id, chunk_index=0, text=f"AADMARK {doc_id}"))

    def obs(oid, analyte, value, when, doc_id, verified=True):
        db.add(Observation(
            id=oid, profile_id=PROFILE, doc_id=doc_id, analyte_canonical=analyte,
            analyte_raw=analyte, value=value, unit="u", collected_at=when,
            user_verified=verified, verified_at=when if verified else None,
        ))

    obs("obs-g-jan", "glucose", 90.0, JAN, "doc-jan")
    obs("obs-g-jun", "glucose", 110.0, JUN, "doc-jun")
    obs("obs-k-jun", "potassium", 4.1, JUN, "doc-jun")
    obs("obs-fe-jun", "ferritin", 50.0, JUN, "doc-jun")
    obs("obs-ldl-unv", "LDL", 140.0, JUN, "doc-jun", verified=False)
    await db.commit()
    return db, engine


@pytest_asyncio.fixture
async def profile_db():
    db, engine = await _make_db()
    clear_cache()
    try:
        yield db
    finally:
        clear_cache()
        await db.close()
        await engine.dispose()


def _post(profile_db, body: dict, *, agent: bool = True):
    with patch.object(A, "is_agent_enabled", return_value=agent):
        with route_client(assistant_router, "/assistant", profile_id=PROFILE) as client:

            async def _override_profile_db():
                return profile_db

            client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
            resp = client.post("/assistant/chat", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _cited(body: dict) -> set[str]:
    """Observation ids cited in the response. Agent citations carry the row id
    as the snippet (the locator); fallback citations set ``observation_id``."""
    ids = set()
    for seg in body["segments"]:
        for c in seg["citations"]:
            oid = c.get("observation_id") or c.get("text_snippet") or ""
            if oid.startswith("obs-"):
                ids.add(oid)
    return ids


GLUCOSE_Q = "what is my glucose?"
TREND_Q = "how has my glucose changed over time?"


@pytest.mark.asyncio
async def test_hc_aad_001_from_date_narrows_agent_observations(profile_db):
    body = _post(profile_db, {"question": GLUCOSE_Q, "from_date": "2026-03-01"})
    assert _cited(body) == {"obs-g-jun"}


@pytest.mark.asyncio
async def test_hc_aad_002_date_filter_splits_the_cache(profile_db):
    unfiltered = _post(profile_db, {"question": GLUCOSE_Q})
    filtered = _post(profile_db, {"question": GLUCOSE_Q, "from_date": "2026-03-01"})
    assert _cited(unfiltered) == {"obs-g-jan", "obs-g-jun"}
    assert _cited(filtered) == {"obs-g-jun"}


# JUN is stored as 2026-06-15 00:00 UTC.
BOUND_CASES = [
    ("plus5_from_includes", {"from_date": "2026-06-15T04:30:00+05:00"}, {"obs-g-jun"}),
    ("plus5_from_excludes", {"from_date": "2026-06-15T05:30:00+05:00"}, set()),
    ("plus5_to_excludes", {"to_date": "2026-06-15T04:30:00+05:00"}, {"obs-g-jan"}),
    ("malformed_ignored", {"from_date": "not-a-date", "to_date": "2026-13-45"}, {"obs-g-jan", "obs-g-jun"}),
    # Bounds exactly at the stored instant are inclusive (legacy >= / <=).
    ("from_equal_includes", {"from_date": "2026-06-15T00:00:00"}, {"obs-g-jun"}),
    ("to_equal_includes", {"to_date": "2026-06-15T00:00:00"}, {"obs-g-jan", "obs-g-jun"}),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("name,filters,expected", BOUND_CASES, ids=[c[0] for c in BOUND_CASES])
async def test_hc_aad_003_bounds_are_naive_utc_and_malformed_ignored(profile_db, name, filters, expected):
    body = _post(profile_db, {"question": GLUCOSE_Q, **filters})
    assert _cited(body) == expected, name


def _ctx(profile_db, filters: ChatFilters) -> RunContext:
    @asynccontextmanager
    async def _factory():
        yield profile_db

    return RunContext(profile_id=PROFILE, run_id="run-aad", db_session_factory=_factory, filters=filters)


async def _chunk_docs(profile_db, query: str, filters: ChatFilters) -> set[str]:
    out = await RetrieveChunksTool().run(RetrieveChunksInput(query=query), _ctx(profile_db, filters))
    return {c.document_id for c in out.chunks}


@pytest.mark.asyncio
async def test_hc_aad_004_retrieve_chunks_honours_the_date_window(profile_db):
    window = ChatFilters(from_dt=datetime(2026, 3, 1))
    # Text match path and the no-match fallback path both inherit the window.
    assert await _chunk_docs(profile_db, "AADMARK", window) == {"doc-jun"}
    assert await _chunk_docs(profile_db, "no-such-text", window) == {"doc-jun"}
    upto = ChatFilters(to_dt=datetime(2026, 3, 1))
    assert await _chunk_docs(profile_db, "AADMARK", upto) == {"doc-jan"}
    assert await _chunk_docs(profile_db, "no-such-text", upto) == {"doc-jan"}


@pytest.mark.asyncio
@pytest.mark.parametrize("bound,expected", [("to_date", {"obs-g-jan"}), ("from_date", {"obs-g-jun"})])
async def test_hc_aad_005_compute_trend_honours_the_date_window(profile_db, bound, expected):
    body = _post(profile_db, {"question": TREND_Q, bound: "2026-03-01"})
    assert _cited(body) == expected


@pytest.mark.asyncio
async def test_hc_aad_006_selected_analytes_add_to_the_question_analyte(profile_db):
    body = _post(profile_db, {"question": GLUCOSE_Q, "selected_analytes": ["Potassium"]})
    # Added, not narrowed: the asked-about glucose rows stay.
    assert _cited(body) == {"obs-g-jan", "obs-g-jun", "obs-k-jun"}


@pytest.mark.asyncio
async def test_hc_aad_007_selected_panel_resolves_and_adds(profile_db):
    body = _post(profile_db, {"question": GLUCOSE_Q, "selected_panel": "iron"})
    assert _cited(body) == {"obs-g-jan", "obs-g-jun", "obs-fe-jun"}


@pytest.mark.asyncio
async def test_hc_aad_008_selection_does_not_mask_unverified_asked_analyte(profile_db):
    """The asked LDL row is unverified. Without a selection the agent abstains
    with 'not yet verified'; a selection must not turn that into an answer about
    a different analyte."""
    plain = _post(profile_db, {"question": "what is my ldl?"})
    selected = _post(profile_db, {"question": "what is my ldl?", "selected_analytes": ["potassium"]})
    assert _cited(plain) == set()
    assert selected["full_response"] == plain["full_response"]
    assert _cited(selected) == set()


@pytest.mark.asyncio
async def test_hc_aad_009_retrieve_chunks_honours_document_category(profile_db):
    assert await _chunk_docs(profile_db, "AADMARK", ChatFilters(category="lab")) == {"doc-jan"}
    assert await _chunk_docs(profile_db, "no-such-text", ChatFilters(category="lab")) == {"doc-jan"}


@pytest.mark.asyncio
async def test_hc_aad_010_retrieve_chunks_narrows_to_documents_with_selected_analytes(profile_db):
    assert await _chunk_docs(profile_db, "AADMARK", ChatFilters(analytes=("potassium",))) == {"doc-jun"}


CACHE_SPLIT_CASES = [
    ("from_date", {"from_date": "2026-03-01"}),
    ("to_date", {"to_date": "2026-03-01"}),
    ("selected_analytes", {"selected_analytes": ["potassium"]}),
    ("selected_panel", {"selected_panel": "iron"}),
    ("document_category", {"document_category": "lab"}),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("name,filters", CACHE_SPLIT_CASES, ids=[c[0] for c in CACHE_SPLIT_CASES])
async def test_hc_aad_011_requests_differing_only_in_a_filter_do_not_share_a_cache_entry(
    profile_db, name, filters
):
    """Spy on the cache: the filtered request must look up a different key
    than the unfiltered one, and must run the agent rather than replay."""
    seen_keys = []
    real_get = A.get_cached

    def _spy(key):
        seen_keys.append(key)
        return real_get(key)

    sentinel = AgentTerminal(terminal="answer", text="SENTINEL-UNFILTERED", citations=[], run_id="r")
    with patch.object(A, "get_cached", side_effect=_spy):
        _post(profile_db, {"question": GLUCOSE_Q})
        A.put_cached(seen_keys[0], sentinel)
        filtered = _post(profile_db, {"question": GLUCOSE_Q, **filters})
    assert seen_keys[0] != seen_keys[1], name
    assert "SENTINEL-UNFILTERED" not in filtered["full_response"], name


@pytest.mark.asyncio
async def test_hc_aad_012_fallback_latest_observation_honours_the_date_window(profile_db):
    rag = MagicMock()
    rag.query = AsyncMock(side_effect=ModelUnavailableError("no model"))
    info = BiomarkerInfo(
        id="kb-g", analyte_canonical="glucose", display_name="Glucose", description="d",
        clinical_significance="c", normal_interpretation="n", high_interpretation="h",
        low_interpretation="l",
    )
    loader = MagicMock()
    loader.get_biomarker_knowledge = AsyncMock(return_value=info)
    with patch.object(A, "get_rag_module", return_value=rag), \
         patch("modules.knowledge_loader.get_knowledge_loader", return_value=loader):
        unfiltered = _post(profile_db, {"question": GLUCOSE_Q}, agent=False)
        filtered = _post(profile_db, {"question": GLUCOSE_Q, "to_date": "2026-03-01"}, agent=False)
        after_all = _post(profile_db, {"question": GLUCOSE_Q, "from_date": "2026-07-01"}, agent=False)
    assert _cited(unfiltered) == {"obs-g-jun"}
    assert _cited(filtered) == {"obs-g-jan"}
    assert _cited(after_all) == set()


@pytest.mark.asyncio
async def test_hc_aad_013_limit_never_cuts_the_asked_analyte(profile_db):
    """Natural row order puts glucose first; asking potassium with glucose
    selected and limit=1 must still return the asked potassium row."""
    out = await QueryObservationsTool().run(
        QueryObservationsInput(analyte="potassium", limit=1),
        _ctx(profile_db, ChatFilters(analytes=("glucose",))),
    )
    assert [r.observation_id for r in out.rows] == ["obs-k-jun"]


@pytest.mark.asyncio
async def test_hc_aad_014_null_dated_selected_row_does_not_break_the_agent(profile_db):
    """A verified selected-analyte row with no collected_at must not crash the
    agent tool (ObservationRow.collected_at is required) and push the request
    onto the legacy fallback."""
    profile_db.add(Observation(
        id="obs-k-null", profile_id=PROFILE, doc_id="doc-jun", analyte_canonical="potassium",
        analyte_raw="potassium", value=4.0, unit="u", collected_at=None,
        user_verified=True, verified_at=JUN,
    ))
    await profile_db.commit()
    body = _post(profile_db, {"question": GLUCOSE_Q, "selected_analytes": ["potassium"]})
    assert body["verification"]["summary"].startswith("agent:"), body["verification"]
    assert _cited(body) == {"obs-g-jan", "obs-g-jun", "obs-k-jun"}


def _answer_text(body: dict) -> str:
    return " ".join(seg["content"] for seg in body["segments"])


@pytest.mark.asyncio
async def test_hc_cfr_009_cache_key_includes_profile_time_zone(profile_db):
    """The answer prints local dates, so a time-zone change must not replay the
    answer cached under the old zone. 2026-01-16 03:00 UTC is Jan 15 in Los
    Angeles and Jan 16 in Tokyo."""
    from sqlalchemy import update

    from models import UserModelSettings

    profile_db.add(Observation(
        id="obs-ldl-tz", profile_id=PROFILE, doc_id="doc-jun", analyte_canonical="ldl",
        analyte_raw="LDL", value=130.0, unit="mg/dL", collected_at=datetime(2026, 1, 16, 3, 0, 0),
        user_verified=True, verified_at=JUN,
    ))
    profile_db.add(UserModelSettings(profile_id=PROFILE, timezone="America/Los_Angeles"))
    await profile_db.commit()

    question = {"question": "Is my LDL cholesterol high?"}
    first = _answer_text(_post(profile_db, question))
    assert "Jan 15, 2026" in first, first

    await profile_db.execute(
        update(UserModelSettings)
        .where(UserModelSettings.profile_id == PROFILE)
        .values(timezone="Asia/Tokyo")
    )
    await profile_db.commit()

    second = _answer_text(_post(profile_db, question))
    assert "Jan 16, 2026" in second, second
    assert "Jan 15, 2026" not in second, second


# --- HC-CACHE-VER-004..008: the cache key covers every source the agent's
# tools read (AGENT-CACHE-CARETASKS, owner gate CACHE-STALE (c)). Each test
# asks, changes data a tool reads WITHOUT touching the verified-observation or
# verified-document fingerprint, and asks again: a stale cached answer fails.


def _unverified_doc(doc_id: str | None = None) -> Document:
    doc_id = doc_id or str(uuid.uuid4())
    return Document(
        id=doc_id, profile_id=PROFILE, path_hash=doc_id, content_hash=doc_id,
        doc_type="pdf", status="parsed", imported_at=JUN,
    )


@pytest.mark.asyncio
async def test_hc_cache_ver_004_closing_a_care_task_changes_the_answer(profile_db):
    task = CarePlanTask(id=str(uuid.uuid4()), title="Book MRI", status="open")
    profile_db.add(task)
    await profile_db.commit()

    question = {"question": "Which follow-up tasks are open?"}
    assert "Book MRI" in _answer_text(_post(profile_db, question))

    task.status = "done"
    await profile_db.commit()

    second = _answer_text(_post(profile_db, question))
    assert "Book MRI" not in second, second


@pytest.mark.asyncio
async def test_hc_cache_ver_005_deleted_document_quote_is_not_replayed(
    profile_db, monkeypatch, tmp_path
):
    """Privacy. The task survives a document delete but its verbatim clinician
    quote is cleared (CARE-QUOTE-001); a cached answer must not replay it."""
    from api import documents as documents_api
    from api.documents import router as documents_router

    monkeypatch.setattr(
        type(documents_api.settings), "app_data_path", property(lambda self: tmp_path)
    )
    doc = _unverified_doc()
    profile_db.add(doc)
    profile_db.add(DocumentCategory(
        doc_id=doc.id, category="visit_notes", confidence=1.0, classified_by="t",
    ))
    profile_db.add(CarePlanTask(
        id=str(uuid.uuid4()), title="Book knee scan", status="open",
        source_document_id=doc.id, source_quote="Schedule MRI of the left knee",
    ))
    await profile_db.commit()

    question = {"question": "Which follow-up tasks are open?"}
    first = _answer_text(_post(profile_db, question))
    assert "Schedule MRI of the left knee" in first, first

    with route_client(documents_router, "/documents", profile_id=PROFILE) as client:

        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        resp = client.delete(f"/documents/{doc.id}")
    assert resp.status_code == 204, resp.text
    profile_db.expire_all()

    second = _answer_text(_post(profile_db, question))
    assert "Book knee scan" in second, second
    assert "Schedule MRI of the left knee" not in second, second


@pytest.mark.asyncio
async def test_hc_cache_ver_006_verifying_a_medication_change_changes_the_answer(profile_db):
    doc = _unverified_doc()
    entity = DocumentEntity(
        id=str(uuid.uuid4()), doc_id=doc.id, category="visit_notes",
        entity_type="medication_change", entity_value="Start metformin 500 mg",
        confidence=0.9, quote="Start metformin 500 mg", verified_by_user=None,
    )
    profile_db.add(doc)
    await profile_db.commit()
    profile_db.add(entity)
    await profile_db.commit()

    question = {"question": "Show all medication changes"}
    assert "metformin" not in _answer_text(_post(profile_db, question)).lower()

    entity.verified_by_user = True
    await profile_db.commit()

    assert "metformin" in _answer_text(_post(profile_db, question)).lower()


@pytest.mark.asyncio
async def test_hc_cache_ver_007_new_medication_changes_the_timeline_answer(profile_db):
    profile_db.add(Medication(
        id=str(uuid.uuid4()), profile_id=PROFILE, name="Atorvastatin",
        started_at=datetime(2026, 2, 1),
    ))
    await profile_db.commit()

    question = {"question": "What changed since my last visit?"}
    assert "Started medication: Atorvastatin" in _answer_text(_post(profile_db, question))

    profile_db.add(Medication(
        id=str(uuid.uuid4()), profile_id=PROFILE, name="Lisinopril",
        started_at=datetime(2026, 3, 1),
    ))
    await profile_db.commit()

    assert "Started medication: Lisinopril" in _answer_text(_post(profile_db, question))


@pytest.mark.asyncio
async def test_hc_cache_ver_008_unchanged_data_is_still_a_cache_hit(profile_db):
    """No regression: the fingerprint must be stable across two reads (a
    salted ``hash()`` would make every ask a miss)."""
    real = A.run_agent
    spy = AsyncMock(side_effect=real)
    question = {"question": "Is my glucose high?"}
    with patch.object(A, "run_agent", spy):
        first = _answer_text(_post(profile_db, question))
        second = _answer_text(_post(profile_db, question))
    assert first == second
    assert spy.await_count == 1
