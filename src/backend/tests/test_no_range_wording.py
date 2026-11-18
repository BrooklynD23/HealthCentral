"""NO-RANGE-WORDING: a result whose report gave no reference range never
tells the patient it is "within the normal reference range".

Spec: the NO-RANGE-WORDING row of the build-program queue;
owner answer "Say no range is available".

HC-NRW-001..005: no range -> the "no range available" sentence, with and
  without a knowledge-base entry, for every non-abnormal flag state.
HC-NRW-006/007: behaviour that must NOT change (a range is present; the
  kept-flag path).
HC-NRW-008: the real safety guard still passes the new text, in pipeline order.
HC-NRW-009: the text the patient receives over HTTP.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

import models  # noqa: F401  (registers tables on Base.metadata)
from api.interpretations import router as interpretations_router
from core.auth import get_profile_db_session
from core.database import Base
from core.profile_database import ProfileDatabaseBase
from models import Observation
from models.knowledge_base import BiomarkerKnowledge
from modules.interpret import InterpretationContext, InterpretModule
from modules.interpret_safety import InterpretationSafetyGuard
from modules.knowledge_loader import BiomarkerInfo, get_knowledge_loader
from scripts.seed_knowledge_base import BIOMARKER_DATA
from tests.support.routes import route_client

NO_RANGE = (
    "This report did not include a reference range, "
    "so this result can't be compared to one."
)
OLD_NO_KB = "This value is within the normal reference range."
MEASURES = "**What this test measures:**"
PROFILE_ID = "profile-a"  # route_client's default session profile_id


# ── scaffolding ──────────────────────────────────────────────────────────────


def _module() -> InterpretModule:
    # Copied from tests/test_verify_keeps_flag.py (not imported across modules).
    return InterpretModule(
        knowledge_loader=SimpleNamespace(get_biomarker_knowledge=AsyncMock(return_value=None)),
        safety_guard=SimpleNamespace(),
        recommendation_engine=SimpleNamespace(generate_recommendations=AsyncMock(return_value=None)),
        model_selector=SimpleNamespace(),
    )


def _kb_from(data: dict) -> BiomarkerInfo:
    """A BiomarkerInfo carrying the real seed text fields of one table entry."""
    return BiomarkerInfo(
        id=f"kb-{data['analyte_canonical']}",
        analyte_canonical=data["analyte_canonical"],
        display_name=data["display_name"],
        description=data["description"],
        clinical_significance=data["clinical_significance"],
        normal_interpretation=data["normal_interpretation"],
        high_interpretation=data["high_interpretation"],
        low_interpretation=data["low_interpretation"],
    )


SYNTHETIC_KB = BiomarkerInfo(
    id="kb-synthetic",
    analyte_canonical="ldl_cholesterol",
    display_name="Synthetic Marker",
    description="SENTINEL-DESCRIPTION",
    clinical_significance=None,
    normal_interpretation="SENTINEL-NORMAL",
    high_interpretation="SENTINEL-HIGH",
    low_interpretation="SENTINEL-LOW",
)

SEED_KB0 = _kb_from(BIOMARKER_DATA[0])
SEED_KBS = [pytest.param(_kb_from(d), id=d["analyte_canonical"]) for d in BIOMARKER_DATA]
KB_CASES = [pytest.param(None, id="no-kb"), pytest.param(SYNTHETIC_KB, id="synthetic-kb")] + SEED_KBS


def _obs(**kw) -> Observation:
    base = dict(
        id=str(uuid.uuid4()), profile_id=PROFILE_ID, doc_id=str(uuid.uuid4()),
        analyte_canonical="ldl_cholesterol", analyte_raw="LDL Cholesterol",
        value=120.0, unit="mg/dL", ref_low=None, ref_high=None, ref_range_text=None,
        flag=None, is_abnormal=False, collected_at=datetime(2026, 3, 1, 9, 0, 0),
    )
    base.update(kw)
    return Observation(**base)


async def _text(obs: Observation, kb: BiomarkerInfo | None) -> str:
    text, _ = await _module()._generate_interpretation(
        InterpretationContext(observation=obs, biomarker_info=kb), AsyncMock()
    )
    return text


# ── HC-NRW-001..005: no range -> the new sentence ────────────────────────────


@pytest.mark.asyncio
async def test_hc_nrw_001_no_kb_no_range_says_no_range_available():
    text = await _text(_obs(), None)
    assert NO_RANGE in text, text
    assert OLD_NO_KB not in text, text
    assert "normal" not in text.lower(), text
    assert "within" not in text.lower(), text


@pytest.mark.asyncio
@pytest.mark.parametrize("kb", SEED_KBS)
async def test_hc_nrw_002_kb_no_range_does_not_use_the_kb_normal_text(kb):
    text = await _text(_obs(analyte_canonical=kb.analyte_canonical), kb)
    assert NO_RANGE in text, text
    assert kb.normal_interpretation not in text, text
    # The split is on purpose: a description may say "normal muscle metabolism",
    # which is not a range claim. Only the part before the description counts.
    assert MEASURES in text, "seed entry has clinical_significance, so the description follows"
    before = text.split(MEASURES)[0].lower()
    assert "normal" not in before, before
    assert "within" not in before, before
    assert NO_RANGE + " [KB:" not in text, text


@pytest.mark.asyncio
async def test_hc_nrw_002_synthetic_kb_text_never_reaches_the_patient():
    # Holds for any KB text, not only today's seed: a later row loads more of it.
    text = await _text(_obs(), SYNTHETIC_KB)
    assert NO_RANGE in text, text
    assert "SENTINEL-NORMAL" not in text, text
    assert NO_RANGE + " [KB:" not in text, text
    assert "normal" not in text.lower(), text
    assert "within" not in text.lower(), text


@pytest.mark.asyncio
@pytest.mark.parametrize("kb", [None, SYNTHETIC_KB, SEED_KB0], ids=["no-kb", "synthetic", "seed"])
async def test_hc_nrw_003_is_abnormal_none_takes_the_same_branch(kb):
    text = await _text(_obs(is_abnormal=None), kb)
    assert NO_RANGE in text, text
    assert OLD_NO_KB not in text, text
    if kb is not None:
        assert kb.normal_interpretation not in text, text


@pytest.mark.asyncio
@pytest.mark.parametrize("range_text", ["", "   "])
@pytest.mark.parametrize("kb", [None, SYNTHETIC_KB, SEED_KB0], ids=["no-kb", "synthetic", "seed"])
async def test_hc_nrw_004_blank_range_text_is_no_range(range_text, kb):
    text = await _text(_obs(ref_range_text=range_text), kb)
    assert NO_RANGE in text, text
    assert "Reference range:" not in text, text
    assert OLD_NO_KB not in text, text
    if kb is not None:
        assert kb.normal_interpretation not in text, text


@pytest.mark.asyncio
@pytest.mark.parametrize("flag", [None, "N", "Normal", "  "])
@pytest.mark.parametrize("kb", [None, SYNTHETIC_KB, SEED_KB0], ids=["no-kb", "synthetic", "seed"])
async def test_hc_nrw_005_not_abnormal_flag_does_not_matter(flag, kb):
    # Follows the row's acceptance, which does not condition on the flag.
    text = await _text(_obs(flag=flag, is_abnormal=False), kb)
    assert NO_RANGE in text, text
    assert OLD_NO_KB not in text, text
    if kb is not None:
        assert kb.normal_interpretation not in text, text


# ── HC-NRW-006: a range is present -> today's wording is unchanged ───────────

RANGE_CASES = [
    pytest.param(dict(ref_low=10.0, ref_high=200.0), id="both-bounds"),
    pytest.param(dict(ref_low=10.0), id="ref-low-only"),
    pytest.param(dict(ref_high=200.0), id="ref-high-only"),
    pytest.param(dict(ref_low=0.0), id="ref-low-zero-only"),  # 0.0 is a real bound
    pytest.param(dict(ref_high=0.0, value=0.0), id="ref-high-zero-only"),
    pytest.param(dict(ref_range_text="70-100"), id="range-text-only"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("rng", RANGE_CASES)
async def test_hc_nrw_006_range_present_no_kb_keeps_old_wording(rng):
    text = await _text(_obs(**rng), None)
    assert OLD_NO_KB in text, text
    assert NO_RANGE not in text, text


@pytest.mark.asyncio
@pytest.mark.parametrize("rng", RANGE_CASES)
async def test_hc_nrw_006_range_present_with_kb_keeps_kb_normal_text(rng):
    kb = SEED_KB0
    text = await _text(_obs(**rng), kb)
    assert kb.normal_interpretation + f" [KB:{kb.id}]" in text, text
    assert NO_RANGE not in text, text


# ── HC-NRW-007: kept-flag path (is_abnormal True) is untouched ───────────────


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "flag, no_kb_text, kb_field",
    [
        ("H", "This value is above the reference range.", "high_interpretation"),
        ("L", "This value is below the reference range.", "low_interpretation"),
        ("A", "This value is outside the normal reference range.", None),
    ],
)
async def test_hc_nrw_007_abnormal_flag_wording_unchanged(flag, no_kb_text, kb_field):
    text = await _text(_obs(flag=flag, is_abnormal=True), None)
    assert no_kb_text in text, text
    assert NO_RANGE not in text, text

    kb = SEED_KB0
    kb_text = await _text(_obs(flag=flag, is_abnormal=True), kb)
    assert NO_RANGE not in kb_text, kb_text
    if kb_field:
        assert getattr(kb, kb_field) + f" [KB:{kb.id}]" in kb_text, kb_text
    else:
        assert no_kb_text in kb_text, kb_text


# ── HC-NRW-008: the real guard, in pipeline order ────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("kb", KB_CASES)
async def test_hc_nrw_008_real_guard_passes_the_no_range_text(kb):
    guard = InterpretationSafetyGuard()
    text = await _text(_obs(), kb)
    assert NO_RANGE in text, text
    # Pipeline order (modules/interpret.py): disclaimers first, then validate.
    # The bare sentence fails missing_disclaimers, which is why order matters.
    final_text, final_advice = guard.add_required_disclaimers(
        interpretation_text=text, advice_text=None
    )
    verdict = guard.validate_interpretation(
        interpretation_text=final_text, advice_text=final_advice, require_citations=True
    )
    assert verdict.passed is True, verdict
    assert verdict.checks_failed == [], verdict.checks_failed
    if kb is not None and kb.clinical_significance:
        assert "has_citations" in verdict.checks_passed, verdict.checks_passed
    else:
        # The new sentence carries no [KB:] marker; a missing citation is a warning.
        assert "no_citations_found" in verdict.warnings, verdict.warnings


# ── HC-NRW-009: what the patient receives over HTTP ──────────────────────────


@pytest_asyncio.fixture
async def http_dbs():
    # Engine setup copied from tests/test_interpret_safety_enforce.py.
    async def _engine_session(base):
        engine = create_async_engine(
            "sqlite+aiosqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        async with engine.begin() as conn:
            await conn.run_sync(base.metadata.create_all)
        return AsyncSession(engine, expire_on_commit=False), engine

    profile_db, p_engine = await _engine_session(ProfileDatabaseBase)
    master_db, m_engine = await _engine_session(Base)
    obs = _obs()
    profile_db.add(obs)
    await profile_db.commit()
    loader = get_knowledge_loader()
    loader.clear_cache()  # the process-wide cache would hide the master DB rows
    try:
        yield profile_db, master_db, obs.id
    finally:
        loader.clear_cache()
        await profile_db.close()
        await master_db.close()
        await p_engine.dispose()
        await m_engine.dispose()


# Copied from tests/test_interpret_safety_enforce.py (not imported across modules).
async def _post_interpret(profile_db, master_db, obs_id):
    with route_client(
        interpretations_router, "/interpretations", profile_id=PROFILE_ID, master_db=master_db
    ) as client:

        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        return client.post(f"/interpretations/observations/{obs_id}/interpret")


@pytest.mark.asyncio
async def test_hc_nrw_009_http_no_kb_row(http_dbs):
    profile_db, master_db, obs_id = http_dbs
    resp = await _post_interpret(profile_db, master_db, obs_id)
    assert resp.status_code == 201, resp.text
    text = resp.json()["interpretation_text"]
    assert NO_RANGE in text, text
    assert OLD_NO_KB not in text, text


@pytest.mark.asyncio
async def test_hc_nrw_009_http_seeded_kb_row(http_dbs):
    profile_db, master_db, obs_id = http_dbs
    data = next(d for d in BIOMARKER_DATA if d["analyte_canonical"] == "ldl_cholesterol")
    master_db.add(BiomarkerKnowledge(id=str(uuid.uuid4()), **data))
    await master_db.commit()
    resp = await _post_interpret(profile_db, master_db, obs_id)
    assert resp.status_code == 201, resp.text
    text = resp.json()["interpretation_text"]
    assert NO_RANGE in text, text
    assert data["normal_interpretation"] not in text, text
    assert OLD_NO_KB not in text, text
    assert NO_RANGE + " [KB:" not in text, text
    # Precondition: the KB entry really loaded (its description is in the card),
    # so the assertions above ran against the KB branch and not the no-KB one.
    assert data["display_name"] in text, text
