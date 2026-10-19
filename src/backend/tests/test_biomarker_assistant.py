"""
Tests for Symptom 2 fixes: biomarker knowledge seeding + observation grounding.

Covers:
- Seeding idempotency
- Observation context injection in RAG
- Fallback path with seeded knowledge + user observation
- Safety guard still intact after changes
"""

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).parent.parent))


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _make_obs(
    analyte="ldl_cholesterol",
    value=145.0,
    unit="mg/dL",
    ref_low=0.0,
    ref_high=100.0,
    flag="H",
    collected_at=None,
    verified=False,
    doc_id=None,
):
    obs = MagicMock()
    obs.id = str(uuid.uuid4())
    obs.profile_id = "test-profile"
    obs.analyte_canonical = analyte
    obs.value = value
    obs.unit = unit
    obs.ref_low = ref_low
    obs.ref_high = ref_high
    obs.ref_range_text = f"{ref_low}–{ref_high} {unit}"
    obs.flag = flag
    obs.is_abnormal = True
    obs.collected_at = collected_at or datetime(2025, 3, 10, tzinfo=timezone.utc)
    obs.user_verified = verified
    obs.doc_id = doc_id or str(uuid.uuid4())
    obs.notes = None
    # Nullable on the real model, but they must be real values rather than
    # MagicMocks: CITE-SRC-001 reads them into a Pydantic Citation, and a
    # MagicMock fails validation.
    obs.source_page = None
    obs.source_bbox_json = None
    return obs


def _make_kb_info(analyte="ldl_cholesterol"):
    """Return a minimal BiomarkerInfo-like object."""
    from modules.knowledge_loader import BiomarkerInfo
    return BiomarkerInfo(
        id=str(uuid.uuid4()),
        analyte_canonical=analyte,
        display_name="LDL Cholesterol",
        description="LDL is the 'bad' cholesterol.",
        clinical_significance="High LDL raises cardiovascular risk.",
        normal_interpretation="Your LDL is at a healthy level.",
        high_interpretation="Elevated LDL may increase plaque buildup.",
        low_interpretation="Low LDL is generally favorable.",
        standard_unit="mg/dL",
        category="lipid",
    )


# ──────────────────────────────────────────────────────────────────────────────
# 1. Seeding idempotency
# ──────────────────────────────────────────────────────────────────────────────

class TestSeedingIdempotency:
    """KB seeding must be safe to call multiple times without duplicating rows."""

    @pytest.mark.asyncio
    async def test_seed_biomarker_knowledge_skips_existing_rows(self):
        """Second call to seed_biomarker_knowledge() inserts zero new rows."""
        from scripts.seed_knowledge_base import BIOMARKER_DATA, seed_biomarker_knowledge

        # Simulate an existing row for the first analyte
        existing_canonical = BIOMARKER_DATA[0]["analyte_canonical"]

        mock_existing = MagicMock()
        mock_existing.analyte_canonical = existing_canonical

        async def fake_execute(stmt):
            result = MagicMock()
            result.scalar_one_or_none.return_value = mock_existing
            return result

        mock_session = AsyncMock()
        mock_session.execute = fake_execute

        count = await seed_biomarker_knowledge(mock_session)
        assert count == 0, "Expected 0 new rows when all analytes already exist"

    @pytest.mark.asyncio
    async def test_seed_biomarker_knowledge_inserts_when_table_empty(self):
        """seed_biomarker_knowledge() inserts all rows when table is empty."""
        from scripts.seed_knowledge_base import BIOMARKER_DATA, seed_biomarker_knowledge

        added_objects = []

        async def fake_execute(stmt):
            result = MagicMock()
            result.scalar_one_or_none.return_value = None  # nothing in DB yet
            return result

        mock_session = AsyncMock()
        mock_session.execute = fake_execute
        mock_session.add = lambda obj: added_objects.append(obj)

        count = await seed_biomarker_knowledge(mock_session)
        assert count == len(BIOMARKER_DATA)
        assert mock_session.commit.called

    @pytest.mark.asyncio
    async def test_seed_all_accepts_skip_db_init_flag(self):
        """seed_all(skip_db_init=True) must not call init_database()."""
        from scripts import seed_knowledge_base as skb

        with patch.object(skb, "init_database", new_callable=AsyncMock) as mock_init, \
             patch.object(skb, "async_session_maker") as mock_sm:

            # Make the context manager return an async session
            mock_session = AsyncMock()

            async def fake_execute(stmt):
                r = MagicMock()
                r.scalar_one_or_none.return_value = MagicMock()  # already exists
                return r

            mock_session.execute = fake_execute
            mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sm.return_value.__aexit__ = AsyncMock(return_value=False)

            await skb.seed_all(skip_db_init=True)

            mock_init.assert_not_called()

    @pytest.mark.asyncio
    async def test_seed_all_calls_db_init_by_default(self):
        """seed_all() without flag DOES call init_database() for standalone use."""
        from scripts import seed_knowledge_base as skb

        with patch.object(skb, "init_database", new_callable=AsyncMock) as mock_init, \
             patch.object(skb, "async_session_maker") as mock_sm:

            mock_session = AsyncMock()

            async def fake_execute(stmt):
                r = MagicMock()
                r.scalar_one_or_none.return_value = MagicMock()
                return r

            mock_session.execute = fake_execute
            mock_sm.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_sm.return_value.__aexit__ = AsyncMock(return_value=False)

            await skb.seed_all(skip_db_init=False)

            mock_init.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# 1b. INTERP-ADVICE-WORDING (owner gate IAW-WORDING option b)
# ──────────────────────────────────────────────────────────────────────────────

_OLD_LDL_HIGH = (
    "Elevated LDL cholesterol increases your risk of plaque buildup in arteries. "
    "Lifestyle changes and possibly medication may help reduce this risk."
)

# Hard-coded on purpose: never import these from _TEXT_REVISIONS, or a typo there
# would also be a typo here and the test could not fail.
_OLD_GLUCOSE_HIGH = (
    "Elevated fasting glucose may indicate prediabetes or diabetes. "
    "Further testing and lifestyle modifications may be recommended."
)


def _seed_data(analyte: str) -> dict:
    from scripts.seed_knowledge_base import BIOMARKER_DATA

    return next(d for d in BIOMARKER_DATA if d["analyte_canonical"] == analyte)


@pytest_asyncio.fixture
async def real_master_session():
    """Real sqlite master DB (tables created from the ORM), not a mock."""
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

    import models  # noqa: F401  (registers tables on Base.metadata)
    from core.database import Base

    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session, engine
    finally:
        await session.close()
        await engine.dispose()


def _session_maker_for(engine):
    from sqlalchemy.ext.asyncio import AsyncSession

    return lambda: AsyncSession(engine, expire_on_commit=False)


async def _high_text_in_db(engine, analyte: str = "ldl_cholesterol") -> str:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from models.knowledge_base import BiomarkerKnowledge

    async with AsyncSession(engine, expire_on_commit=False) as s:
        row = (
            await s.execute(
                select(BiomarkerKnowledge).where(
                    BiomarkerKnowledge.analyte_canonical == analyte
                )
            )
        ).scalar_one()
        return row.high_interpretation


class TestSeedAdviceWording:
    """HC-IAW-001..003: a seeded KB sentence must not suggest medication."""

    def test_hc_iaw_001_seed_high_wording_is_educational(self):
        ldl = _seed_data("ldl_cholesterol")["high_interpretation"]
        glucose = _seed_data("glucose_fasting")["high_interpretation"]
        assert "medication" not in ldl.lower()
        assert "lifestyle modifications may be recommended" not in glucose.lower()

    @pytest.mark.asyncio
    async def test_hc_iaw_002_untouched_installed_row_is_revised(
        self, real_master_session
    ):
        from models.knowledge_base import BiomarkerKnowledge
        from scripts import seed_knowledge_base as skb

        session, engine = real_master_session
        for analyte, old_text in (
            ("ldl_cholesterol", _OLD_LDL_HIGH),
            ("glucose_fasting", _OLD_GLUCOSE_HIGH),
        ):
            old_row = dict(_seed_data(analyte))
            old_row["high_interpretation"] = old_text
            session.add(BiomarkerKnowledge(id=str(uuid.uuid4()), **old_row))
        await session.commit()

        with patch.object(skb, "async_session_maker", _session_maker_for(engine)):
            await skb.seed_all(skip_db_init=True)

        for analyte in ("ldl_cholesterol", "glucose_fasting"):
            stored = await _high_text_in_db(engine, analyte)
            assert stored == _seed_data(analyte)["high_interpretation"]
        assert "medication" not in (await _high_text_in_db(engine)).lower()

    @pytest.mark.asyncio
    async def test_hc_iaw_003_edited_row_is_left_alone(self, real_master_session):
        from models.knowledge_base import BiomarkerKnowledge
        from scripts import seed_knowledge_base as skb

        session, engine = real_master_session
        edited = "Locally edited LDL text that the owner wrote."
        row = dict(_seed_data("ldl_cholesterol"))
        row["high_interpretation"] = edited
        session.add(BiomarkerKnowledge(id=str(uuid.uuid4()), **row))
        await session.commit()

        with patch.object(skb, "async_session_maker", _session_maker_for(engine)):
            await skb.seed_all(skip_db_init=True)

        assert await _high_text_in_db(engine) == edited


class TestInterpretRouteAdviceWording:
    """HC-IAW-004: the shipped template path, over HTTP, with the seed row."""

    @pytest.mark.asyncio
    async def test_hc_iaw_004_high_ldl_interpretation_has_no_medication(
        self, real_master_session
    ):
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

        from api.interpretations import router as interpretations_router
        from core.auth import get_profile_db_session
        from core.profile_database import ProfileDatabaseBase
        from models import Observation
        from models.knowledge_base import BiomarkerKnowledge
        from modules.knowledge_loader import get_knowledge_loader
        from tests.support.routes import route_client

        master, _engine = real_master_session
        # Built from the seed dict itself: hard-coded text could never fail.
        master.add(
            BiomarkerKnowledge(id=str(uuid.uuid4()), **_seed_data("ldl_cholesterol"))
        )
        await master.commit()

        p_engine = create_async_engine("sqlite+aiosqlite://")
        async with p_engine.begin() as conn:
            await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
        profile_db = AsyncSession(p_engine, expire_on_commit=False)
        obs_id = str(uuid.uuid4())
        profile_db.add(
            Observation(
                id=obs_id, profile_id="profile-iaw", doc_id=str(uuid.uuid4()),
                analyte_canonical="ldl_cholesterol", analyte_raw="LDL",
                value=165.0, unit="mg/dL", ref_low=0.0, ref_high=100.0,
                flag="H", is_abnormal=True, user_verified=True,
                collected_at=datetime(2025, 3, 10),
            )
        )
        await profile_db.commit()

        async def _override_profile_db():
            return profile_db

        loader = get_knowledge_loader()
        loader.clear_cache()  # process-wide cache would hide the DB row
        try:
            with route_client(
                interpretations_router, "/interpretations",
                profile_id="profile-iaw", master_db=master,
            ) as client:
                client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
                response = client.post(
                    f"/interpretations/observations/{obs_id}/interpret"
                )
        finally:
            loader.clear_cache()
            await profile_db.close()
            await p_engine.dispose()

        assert response.status_code == 201, response.text
        text = response.json()["interpretation_text"]
        # Guard against a vacuous pass: the KB sentence must actually be there.
        assert "Elevated LDL cholesterol" in text, text
        assert "medication" not in text.lower(), text


# ──────────────────────────────────────────────────────────────────────────────
# 2. Observation context injection
# ──────────────────────────────────────────────────────────────────────────────

class TestObservationGrounding:
    """_get_observation_chunks() must surface the user's own values."""

    @pytest.mark.asyncio
    async def test_observation_chunk_built_from_profile_obs(self):
        """_get_observation_chunks returns a YOUR RESULTS chunk for a matched analyte."""
        from modules.rag import RAGModule

        rag = RAGModule()
        obs = _make_obs("ldl_cholesterol", value=145.0)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [obs]

        mock_profile_db = AsyncMock()
        mock_profile_db.execute = AsyncMock(return_value=mock_result)

        chunks = await rag._get_observation_chunks(
            query="how is my LDL?",
            profile_id="test-profile",
            selected_analytes=None,
            from_date=None,
            to_date=None,
            profile_db=mock_profile_db,
        )

        assert len(chunks) >= 1
        chunk = chunks[0]
        assert chunk.source_type == "user_observation"
        assert chunk.is_observation_summary is True
        assert "145.0" in chunk.text
        assert "YOUR RESULTS" in chunk.text
        assert "LDL" in chunk.text or "ldl" in chunk.text.lower()

    @pytest.mark.asyncio
    async def test_observation_chunk_includes_flag_and_ref_range(self):
        """Observation chunk text contains the flag and reference range."""
        from modules.rag import RAGModule

        rag = RAGModule()
        obs = _make_obs("ldl_cholesterol", value=145.0, ref_low=0.0, ref_high=100.0, flag="H")

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [obs]

        mock_profile_db = AsyncMock()
        mock_profile_db.execute = AsyncMock(return_value=mock_result)

        chunks = await rag._get_observation_chunks(
            query="explain my ldl",
            profile_id="test-profile",
            selected_analytes=["ldl_cholesterol"],
            from_date=None,
            to_date=None,
            profile_db=mock_profile_db,
        )

        assert chunks, "Expected at least one chunk"
        text = chunks[0].text
        assert "HIGH" in text or "H" in text
        assert "0.0" in text or "100.0" in text  # ref range boundary

    @pytest.mark.asyncio
    async def test_observation_chunk_shows_trend_direction(self):
        """When multiple observations exist, trend direction appears in the chunk."""
        from modules.rag import RAGModule

        rag = RAGModule()

        def make_with_date(value, date):
            obs = _make_obs("ldl_cholesterol", value=value)
            obs.collected_at = date
            return obs

        rows = [
            make_with_date(145.0, datetime(2025, 3, 10, tzinfo=timezone.utc)),
            make_with_date(150.0, datetime(2024, 12, 1, tzinfo=timezone.utc)),
            make_with_date(155.0, datetime(2024, 9, 1, tzinfo=timezone.utc)),
        ]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = rows

        mock_profile_db = AsyncMock()
        mock_profile_db.execute = AsyncMock(return_value=mock_result)

        chunks = await rag._get_observation_chunks(
            query="LDL trend",
            profile_id="test-profile",
            selected_analytes=["ldl_cholesterol"],
            from_date=None,
            to_date=None,
            profile_db=mock_profile_db,
        )

        assert chunks
        text = chunks[0].text
        assert "Trend" in text or "trend" in text
        assert "decreasing" in text or "improving" in text or "→" in text

    @pytest.mark.asyncio
    async def test_observation_chunks_prepended_in_retrieve_context(self):
        """Observation chunks appear before reference chunks in retrieve_context output."""
        from modules.rag import RAGModule, RetrievedChunk

        rag = RAGModule()

        obs_chunk = RetrievedChunk(
            chunk_id="obs_test",
            source_type="user_observation",
            doc_id=None,
            doc_title="Your LDL Result",
            page=None,
            text="YOUR RESULTS — LDL Cholesterol\nLatest value : 145.0 mg/dL",
            relevance_score=0.95,
            is_observation_summary=True,
        )
        ref_chunk = RetrievedChunk(
            chunk_id="ref_test",
            source_type="reference",
            doc_id=None,
            doc_title="Medical Reference: LDL",
            page=None,
            text="LDL is the bad cholesterol.",
            relevance_score=0.8,
            is_peer_reviewed=True,
        )

        with patch.object(rag, "_search_vectors_async", new_callable=AsyncMock, return_value=[]), \
             patch.object(rag, "_get_reference_chunks", new_callable=AsyncMock, return_value=[ref_chunk]), \
             patch.object(rag, "_get_observation_chunks", new_callable=AsyncMock, return_value=[obs_chunk]):

            chunks = await rag.retrieve_context(
                query="how is my LDL?",
                profile_id="test-profile",
                profile_db=AsyncMock(),
                master_db=AsyncMock(),
            )

        assert len(chunks) >= 2
        assert chunks[0].is_observation_summary is True, "Observation chunk should come first"
        assert chunks[0].source_type == "user_observation"

    @pytest.mark.asyncio
    async def test_observation_chunk_labeled_YOUR_RESULTS_in_prompt(self):
        """compose_prompt labels observation chunks as [YOUR_RESULTS:N]."""
        from modules.rag import RAGModule, RetrievedChunk

        rag = RAGModule()
        obs_chunk = RetrievedChunk(
            chunk_id="obs_1",
            source_type="user_observation",
            doc_id=None,
            doc_title="Your LDL Result",
            page=None,
            text="YOUR RESULTS — LDL\nLatest: 145 mg/dL",
            relevance_score=0.95,
            is_observation_summary=True,
        )

        prompt = rag.compose_prompt("explain my LDL", [obs_chunk])
        assert "[YOUR_RESULTS:1]" in prompt

    @pytest.mark.asyncio
    async def test_reference_chunk_still_labeled_REFERENCE_in_prompt(self):
        """Reference chunks keep their [REFERENCE:N] label (not YOUR_RESULTS)."""
        from modules.rag import RAGModule, RetrievedChunk

        rag = RAGModule()
        ref_chunk = RetrievedChunk(
            chunk_id="ref_1",
            source_type="reference",
            doc_id=None,
            doc_title="Medical Reference: LDL",
            page=None,
            text="LDL is bad cholesterol.",
            relevance_score=0.8,
            is_peer_reviewed=True,
        )

        prompt = rag.compose_prompt("explain LDL", [ref_chunk])
        assert "[REFERENCE:1]" in prompt
        assert "[YOUR_RESULTS:1]" not in prompt


# ──────────────────────────────────────────────────────────────────────────────
# 3. Fallback path with seeded knowledge + user observation
# ──────────────────────────────────────────────────────────────────────────────

class TestFallbackPath:
    """_build_knowledge_fallback must produce grounded answers when KB is seeded."""

    @pytest.mark.asyncio
    async def test_fallback_includes_kb_info_when_seeded(self):
        """Fallback produces informative text when KB entry exists."""
        from api.assistant import ChatRequest, _build_knowledge_fallback

        request = ChatRequest(question="How's my LDL cholesterol?")
        kb_info = _make_kb_info("ldl_cholesterol")

        with patch("modules.knowledge_loader.get_knowledge_loader") as mock_loader_fn:
            mock_loader = MagicMock()
            mock_loader.get_biomarker_knowledge = AsyncMock(return_value=kb_info)
            mock_loader_fn.return_value = mock_loader

            response = await _build_knowledge_fallback(
                request=request,
                profile_id="test-profile",
                db=AsyncMock(),
                profile_db=None,
            )

        texts = [s.content for s in response.segments]
        combined = " ".join(texts).lower()
        assert "ldl" in combined or "cholesterol" in combined
        # Must still include the uncertainty disclaimer
        assert any("knowledge base" in t.lower() for t in texts)

    @pytest.mark.asyncio
    async def test_fallback_includes_user_observation_when_profile_db_provided(self):
        """With profile_db, fallback embeds the user's actual value."""
        from api.assistant import ChatRequest, _build_knowledge_fallback

        request = ChatRequest(question="What's my LDL?")
        kb_info = _make_kb_info("ldl_cholesterol")
        obs = _make_obs("ldl_cholesterol", value=145.0)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = obs

        mock_profile_db = AsyncMock()
        mock_profile_db.execute = AsyncMock(return_value=mock_result)

        with patch("modules.knowledge_loader.get_knowledge_loader") as mock_loader_fn:
            mock_loader = MagicMock()
            mock_loader.get_biomarker_knowledge = AsyncMock(return_value=kb_info)
            mock_loader_fn.return_value = mock_loader

            response = await _build_knowledge_fallback(
                request=request,
                profile_id="test-profile",
                db=AsyncMock(),
                profile_db=mock_profile_db,
            )

        combined = " ".join(s.content for s in response.segments)
        assert "145.0" in combined or "145" in combined
        # At least one observation citation should be attached
        all_citations = [c for s in response.segments for c in s.citations]
        assert len(all_citations) >= 1
        assert all_citations[0].source_type == "user_observation"

    @pytest.mark.asyncio
    async def test_fallback_graceful_when_kb_empty(self):
        """With empty KB, fallback returns uncertainty segment (no crash)."""
        from api.assistant import ChatRequest, _build_knowledge_fallback

        request = ChatRequest(question="explain my LDL")

        with patch("modules.knowledge_loader.get_knowledge_loader") as mock_loader_fn:
            mock_loader = MagicMock()
            mock_loader.get_biomarker_knowledge = AsyncMock(return_value=None)
            mock_loader_fn.return_value = mock_loader

            response = await _build_knowledge_fallback(
                request=request,
                profile_id="test-profile",
                db=AsyncMock(),
                profile_db=None,
            )

        assert response is not None
        assert len(response.segments) >= 1
        assert any(s.segment_type == "uncertainty" for s in response.segments)

    @pytest.mark.asyncio
    async def test_fallback_observation_cite_refs_are_user_observation_type(self):
        """Citations produced by fallback are source_type='user_observation'."""
        from api.assistant import ChatRequest, _build_knowledge_fallback

        request = ChatRequest(question="LDL status?")
        kb_info = _make_kb_info("ldl_cholesterol")
        obs = _make_obs("ldl_cholesterol", value=150.0)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = obs

        mock_profile_db = AsyncMock()
        mock_profile_db.execute = AsyncMock(return_value=mock_result)

        with patch("modules.knowledge_loader.get_knowledge_loader") as mock_loader_fn:
            mock_loader = MagicMock()
            mock_loader.get_biomarker_knowledge = AsyncMock(return_value=kb_info)
            mock_loader_fn.return_value = mock_loader

            response = await _build_knowledge_fallback(
                request=request,
                profile_id="test-profile",
                db=AsyncMock(),
                profile_db=mock_profile_db,
            )

        all_citations = [c for s in response.segments for c in s.citations]
        user_obs_cites = [c for c in all_citations if c.source_type == "user_observation"]
        assert len(user_obs_cites) >= 1


# ──────────────────────────────────────────────────────────────────────────────
# 4. Safety guard still intact after all changes
# ──────────────────────────────────────────────────────────────────────────────

class TestSafetyGuardIntact:
    """Observation grounding must NOT weaken the interpret_safety guardrails."""

    def _obs_chunk(self):
        from modules.rag import RetrievedChunk
        return RetrievedChunk(
            chunk_id="obs_1",
            source_type="user_observation",
            doc_id=None,
            doc_title="Your LDL Result",
            page=None,
            text="YOUR RESULTS — LDL\nLatest: 145 mg/dL",
            relevance_score=0.95,
            is_observation_summary=True,
        )

    def test_prohibited_diagnostic_language_still_rejected(self):
        """Responses citing user_observation chunks must still fail on diagnosis patterns."""
        from modules.rag import RAGModule

        rag = RAGModule()
        bad_response = """
REPORT FACTS:
Your LDL is 145 mg/dL [cite:1].
This clearly shows you have heart disease.
"""
        validated = rag.validate_response(
            response=bad_response,
            retrieved_chunks=[self._obs_chunk()],
        )
        assert validated.is_valid is False
        assert any("prohibited" in e.lower() for e in validated.validation_errors)

    def test_prohibited_dosing_advice_still_rejected(self):
        """Dosing/medication advice is rejected even when observation context is present."""
        from modules.rag import RAGModule

        rag = RAGModule()
        bad_response = """
REPORT FACTS:
LDL is 145 mg/dL [cite:1].

GENERAL INFO:
You should take 20mg of statins daily to lower your LDL.
"""
        validated = rag.validate_response(
            response=bad_response,
            retrieved_chunks=[self._obs_chunk()],
        )
        assert validated.is_valid is False
        assert any("prohibited" in e.lower() for e in validated.validation_errors)

    def test_valid_educational_response_passes_with_observation_chunk(self):
        """A well-formed educational response citing [cite:1] (observation) passes."""
        from modules.rag import RAGModule

        rag = RAGModule()
        good_response = """
REPORT FACTS:
Your LDL cholesterol is 145 mg/dL [cite:1], which is above the optimal range.

GENERAL INFO:
LDL cholesterol is often called 'bad' cholesterol. Lifestyle changes such as
diet modification and regular exercise may help manage cholesterol levels.
Please consult your healthcare provider for guidance on next steps.

UNCERTAINTIES:
Individual factors such as age and medical history should be discussed with
your healthcare provider for a complete picture.
"""
        validated = rag.validate_response(
            response=good_response,
            retrieved_chunks=[self._obs_chunk()],
        )
        # Should NOT have prohibited-content validation errors
        safety_errors = [e for e in validated.validation_errors if "prohibited" in e.lower()]
        assert len(safety_errors) == 0, (
            f"Safety guard incorrectly flagged a clean response: {safety_errors}"
        )

    @pytest.mark.asyncio
    async def test_query_with_no_obs_still_returns_insufficient_context(self):
        """When there are no chunks at all (no obs, no docs), query returns insufficient."""
        from modules.rag import RAGModule

        rag = RAGModule()

        with patch.object(rag, "retrieve_context", new_callable=AsyncMock, return_value=[]):
            result = await rag.query(
                question="what is my LDL?",
                profile_id="test-profile",
            )

        assert result.insufficient_context is True
        assert len(result.insufficient_reasons) > 0
