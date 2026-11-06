"""KEPT-FLAG-DISAGREES: a printed flag that disagrees with the printed range says so.

Spec: the KEPT-FLAG-DISAGREES row of the build-program queue; owner answer
"Say they disagree (Recommended)", sentence verbatim. Before this row a kept `L` at 18
against 12-16 read "below the reference range", which the number contradicts.

HC-KFD-001  every HC-VRC-006 disagreement reads exactly the new sentence, no KB text
HC-KFD-002  every other status keeps today's text; the new sentence is never added to it
HC-KFD-003  the real safety guard passes the sentence and a card that holds it
HC-KFD-004  single card over HTTP (POST then GET), severity and stored is_abnormal unchanged
HC-KFD-005  a panel holding a disagreeing member

The new sentence is written out here as a literal, not imported, so each test fails on its
own id before the constant exists.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import select

import api.observations as obs_api
import modules.interpret as interpret_mod
from models import Observation
from models.knowledge_base import BiomarkerKnowledge
from modules.interpret_safety import InterpretationSafetyGuard
from modules.model_selector import ModelSelector
from scripts.seed_knowledge_base import BIOMARKER_DATA
from tests.test_value_range_compare import (
    ABOVE,
    BELOW,
    CLOSED,
    DAY,
    DISAGREE,
    DISAGREE_PARAMS,
    OUTSIDE,
    SODIUM_ROW,
    SYNTHETIC_KB,
    WITHIN,
    _call,
    _cards_of,
    _dbs_ctx,
    _guard,
    _kb_from,
    _obs,
    _read_panel,
    _text,
    interpretations_router,
)

NEW = (
    "The flag printed on your report and the printed range disagree for this value. "
    "Ask your clinician or the lab which applies."
)
OLD_SENTENCES = [ABOVE, BELOW, WITHIN, OUTSIDE]
CLOSED_OLD = [s for s in CLOSED if s != NEW]  # everything main said before, and the no-range line
LDL = next(d for d in BIOMARKER_DATA if d["analyte_canonical"] == "ldl_cholesterol")
LDL_KB = _kb_from(LDL)
KB_FORMS = [pytest.param(None, id="no-kb"), pytest.param(SYNTHETIC_KB, id="synthetic-kb"),
            pytest.param(LDL_KB, id="seeded-ldl")]


@pytest_asyncio.fixture
async def dbs():
    async with _dbs_ctx() as pair:
        yield pair


@pytest_asyncio.fixture
async def rdbs(monkeypatch):
    """Both databases, and a model that raises if anything touches it (a read never calls it)."""
    infer = AsyncMock(side_effect=AssertionError("the model was called on a read"))
    select_model = AsyncMock(side_effect=AssertionError("the model was selected on a read"))
    monkeypatch.setattr(ModelSelector, "run_inference", infer)
    monkeypatch.setattr(ModelSelector, "get_model_for_inference", select_model)
    async with _dbs_ctx() as pair:
        yield pair
    assert infer.await_count == 0 and select_model.await_count == 0


def _kb_words(kb) -> list[str]:
    return [kb.high_interpretation, kb.low_interpretation, kb.normal_interpretation]


# ── HC-KFD-001: the sentence ─────────────────────────────────────────────────


def test_hc_kfd_001_the_constant_is_the_owners_sentence():
    assert getattr(interpret_mod, "SENTENCE_FLAG_RANGE_DISAGREE", None) == NEW


@pytest.mark.asyncio
@pytest.mark.parametrize("kb", KB_FORMS)
@pytest.mark.parametrize("flag,value,lo,hi,stored,literal", DISAGREE_PARAMS)
async def test_hc_kfd_001_every_disagreement_reads_exactly_the_new_sentence(
    flag, value, lo, hi, stored, literal, kb
):
    obs = _obs(flag=flag, value=value, ref_low=lo, ref_high=hi, is_abnormal=stored)
    text = await _text(obs, kb)
    assert text.count(NEW) == 1, text
    for old in CLOSED_OLD:
        assert old not in text, (old, text)
    # no KB status text and no marker on this path; a seeded row's "what this test measures"
    # line is a separate part of the card and is the only marker there is
    assert text.count("[KB:") == (1 if kb is not None and kb.clinical_significance else 0), text
    if kb is not None:
        for words in _kb_words(kb):
            assert words not in text, text
    # Nothing but the value sentence, the range sentence and the new sentence is left.
    left = text.replace(f"Your {obs.analyte_canonical.upper()} result is {obs.value} {obs.unit}.", "")
    left = left.replace(f"The reference range is {obs.ref_low}-{obs.ref_high} {obs.unit}.", "")
    if kb is not None:
        left = left.replace(f"Your {kb.display_name} result is {obs.value} {obs.unit}.", "")
        if kb.clinical_significance:
            left = left.replace(f"\n\n**What this test measures:** {kb.description} [KB:{kb.id}]", "")
    left = left.replace(NEW, "")
    assert left.strip() == "", text


def test_hc_kfd_001_the_cases_cover_both_kinds_and_both_stored_values():
    # (a) a printed normal word against a value outside; (b) a printed H/L inside or across;
    # stored True and False; mixed-case words. A shorter list would let a branch slip by.
    assert {c[0] for c in DISAGREE} >= {"N", "Normal", "n", "H", "HH", "L", "LOW", "High", "low"}
    assert {c[4] for c in DISAGREE} == {True, False}
    assert all(obs_api.observation_range_status(c[0], c[1], c[2], c[3]) == "disagrees" for c in DISAGREE)


# ── HC-KFD-002: every other status is today's text ───────────────────────────

OTHERS = [
    pytest.param(dict(value=300.0), ABOVE, id="unflagged-above"),
    pytest.param(dict(value=40.0), BELOW, id="unflagged-below"),
    pytest.param(dict(value=85.0), WITHIN, id="unflagged-within"),
    pytest.param(dict(value=300.0, flag="H", is_abnormal=True), ABOVE, id="H-above"),
    pytest.param(dict(value=40.0, flag="Low", is_abnormal=True), BELOW, id="Low-below"),
    pytest.param(dict(value=85.0, flag="N", is_abnormal=True), WITHIN, id="N-within"),
    pytest.param(dict(value=85.0, flag="A", is_abnormal=True), OUTSIDE, id="other-flag-keep"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("kw,sentence", OTHERS)
async def test_hc_kfd_002_other_statuses_never_say_the_new_sentence(kw, sentence):
    text = await _text(_obs(**kw))
    assert sentence in text, text
    assert NEW not in text, text


@pytest.mark.asyncio
@pytest.mark.parametrize("kw", [
    dict(value=None, value_text="pending", flag="N", is_abnormal=True),
    dict(value=300.0, ref_low=None, ref_high=None, flag="N", is_abnormal=False),
    dict(value=300.0, ref_low=None, ref_high=None, ref_range_text="70-100", flag="N", is_abnormal=True),
])
async def test_hc_kfd_002_uncomparable_rows_never_say_the_new_sentence(kw):
    assert NEW not in await _text(_obs(**kw))


# ── HC-KFD-003: interpret_safety passes the sentence ─────────────────────────


def test_hc_kfd_003_no_prohibited_pattern_matches_the_sentence():
    guard = InterpretationSafetyGuard()
    assert guard.filter_prohibited_content(NEW) == NEW  # nothing in it is removed or softened
    verdict = guard.validate_interpretation(
        interpretation_text=f"{NEW} Consult your healthcare provider. For general information only.",
        require_citations=True,
    )
    assert not [c for c in verdict.checks_failed if c.startswith("prohibited_")], verdict
    assert "no_prohibited_content" in verdict.checks_passed


@pytest.mark.asyncio
@pytest.mark.parametrize("kb", KB_FORMS)
@pytest.mark.parametrize("kw", [
    dict(value=300.0, flag="N", is_abnormal=True),
    dict(value=85.0, flag="H", is_abnormal=True),
    dict(value=85.0, flag="L", is_abnormal=False),
    dict(value=85.0, flag="High", is_abnormal=True),
], ids=["N-300", "H-85", "L-85-stored-false", "High-85"])
async def test_hc_kfd_003_the_real_guard_passes_a_card_that_holds_the_sentence(kb, kw):
    text = await _text(_obs(**kw), kb)
    assert NEW in text, text  # precondition: RED on main
    verdict = _guard(text)
    assert verdict.passed is True, verdict
    assert verdict.checks_failed == [], verdict.checks_failed
    # The citation rule is a warning when there is no marker; it is never a failure here.
    assert "has_required_disclaimers" in verdict.checks_passed


# ── HC-KFD-004: single card over HTTP ────────────────────────────────────────

HTTP_DISAGREE = [
    pytest.param(dict(value=300.0, flag="N", is_abnormal=True), "high", id="N-300-true"),
    pytest.param(dict(value=300.0, flag="Normal", is_abnormal=False), "high", id="Normal-300-false"),
    pytest.param(dict(value=85.0, flag="H", is_abnormal=True), "normal", id="H-85-true"),
    pytest.param(dict(value=85.0, flag="L", is_abnormal=False), "normal", id="L-85-false"),
    pytest.param(dict(value=18.0, flag="L", ref_low=12.0, ref_high=16.0, is_abnormal=True),
                 "high", id="L-18-in-12-16"),
    pytest.param(dict(value=85.0, flag="High", is_abnormal=True), "normal", id="High-85-mixed-case"),
]


def _assert_only_the_new_sentence(text: str) -> None:
    assert text.count(NEW) == 1, text
    for old in CLOSED_OLD:
        assert old not in text, (old, text)
    assert "SENTINEL" not in text


@pytest.mark.asyncio
@pytest.mark.parametrize("kw,direction", HTTP_DISAGREE)
async def test_hc_kfd_004_post_then_get_say_the_new_sentence(dbs, kw, direction):
    profile_db, master_db = dbs
    obs = _obs(user_verified=True, **kw)
    profile_db.add(obs)
    await profile_db.commit()
    obs_id, stored = obs.id, (obs.is_abnormal, obs.flag)

    post = _call(profile_db, master_db, interpretations_router, "/interpretations", "POST",
                 f"/interpretations/observations/{obs_id}/interpret")
    assert post.status_code == 201, post.text
    _assert_only_the_new_sentence(post.json()["interpretation_text"])
    assert direction in post.json()["severity_level"], post.json()["severity_level"]

    get = _call(profile_db, master_db, interpretations_router, "/interpretations", "GET",
                f"/interpretations/observations/{obs_id}/interpretation")
    assert get.status_code == 200, get.text
    assert get.json()["id"] == post.json()["id"]
    _assert_only_the_new_sentence(get.json()["interpretation_text"])

    profile_db.expire_all()
    row = (await profile_db.execute(select(Observation).where(Observation.id == obs_id))).scalar_one()
    assert (row.is_abnormal, row.flag) == stored  # the stored value is never rewritten


@pytest.mark.asyncio
async def test_hc_kfd_004_a_knowledge_base_row_adds_no_text_to_a_disagreement(dbs):
    profile_db, master_db = dbs
    master_db.add(BiomarkerKnowledge(id="kb-ldl_cholesterol", **LDL))
    await master_db.commit()
    obs = _obs(user_verified=True, analyte_canonical="ldl_cholesterol", value=85.0, flag="H",
               is_abnormal=True)
    profile_db.add(obs)
    await profile_db.commit()
    post = _call(profile_db, master_db, interpretations_router, "/interpretations", "POST",
                 f"/interpretations/observations/{obs.id}/interpret")
    assert post.status_code == 201, post.text
    text = post.json()["interpretation_text"]
    assert text.count(NEW) == 1, text
    for words in _kb_words(LDL_KB):
        assert words not in text, text


# ── HC-KFD-005: a panel holding a disagreeing member ─────────────────────────


@pytest.mark.asyncio
async def test_hc_kfd_005_panel_member_card_says_the_new_sentence(dbs):
    profile_db, master_db = dbs
    glucose = _obs(user_verified=True, collected_at=DAY, value=300.0, flag="N", is_abnormal=True)
    sodium = _obs(user_verified=True, collected_at=DAY, **SODIUM_ROW)
    profile_db.add_all([glucose, sodium])
    await profile_db.commit()
    glucose_id, sodium_id = glucose.id, sodium.id
    resp = _read_panel(profile_db, master_db)
    assert resp.status_code == 201, resp.text
    assert "GLUCOSE: 300.0" in resp.json()["summary_text"]  # stored is_abnormal still counts
    (card,) = await _cards_of(profile_db, glucose_id)
    _assert_only_the_new_sentence(card.interpretation_text)
    (other,) = await _cards_of(profile_db, sodium_id)
    assert NEW not in other.interpretation_text


