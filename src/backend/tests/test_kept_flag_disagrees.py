"""KEPT-FLAG-DISAGREES: a printed flag that disagrees with the printed range says so.

Spec: the KEPT-FLAG-DISAGREES row of the build-program queue; owner answer
"Say they disagree (Recommended)", sentence verbatim. Before this row a kept `L` at 18
against 12-16 read "below the reference range", which the number contradicts.

HC-KFD-001  every HC-VRC-006 disagreement reads exactly the new sentence, no KB text
HC-KFD-002  every other status keeps today's text; the new sentence is never added to it
HC-KFD-003  the real safety guard passes the sentence and a card that holds it
HC-KFD-004  single card over HTTP (POST then GET), severity and stored is_abnormal unchanged
HC-KFD-005  a panel holding a disagreeing member
HC-KFD-006  a saved template card on today's wording is rebuilt on read (GET and POST)
HC-KFD-007  a card that holds the sentence, has no readable claim, or is model-written is left alone
HC-KFD-008  a panel read that rebuilds reaches the disagreeing member's card

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
    PANEL_EVENT,
    READS,
    SODIUM_ROW,
    SYNTHETIC_KB,
    WITHIN,
    _add_card,
    _audit_pairs,
    _call,
    _cards_of,
    _dbs_ctx,
    _det,
    _guard,
    _kb_from,
    _kb_text,
    _obs,
    _ok,
    _old_card,
    _old_panel,
    _panels,
    _read,
    _read_panel,
    _rows_of,
    _snapshot,
    _text,
    _WriteSpy,
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


# ── HC-KFD-006: saved template cards on today's wording are rebuilt ──────────

# (observation, the sentence main printed before this row)
REBUILD = [
    pytest.param(dict(value=300.0, flag="N", is_abnormal=True), OUTSIDE, id="N-at-300-disagrees"),
    pytest.param(dict(value=85.0, flag="H", is_abnormal=True), ABOVE, id="H-at-85-disagrees"),
    pytest.param(dict(value=85.0, flag="L", is_abnormal=True), ABOVE, id="L-at-85-card-says-above"),
    pytest.param(dict(value=85.0, flag="L", is_abnormal=True), BELOW, id="L-at-85-card-says-below"),
    pytest.param(dict(value=300.0, flag="Normal", is_abnormal=False), WITHIN, id="Normal-at-300-stored-false"),
    pytest.param(dict(value=85.0, flag="High", is_abnormal=True), OUTSIDE, id="High-at-85-mixed-case"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("method", READS)
@pytest.mark.parametrize("kw,old", REBUILD)
async def test_hc_kfd_006_an_old_template_card_is_rebuilt_once(rdbs, method, kw, old):
    profile_db, master_db = rdbs
    obs, old_id, old_text = await _old_card(profile_db, kw, old, NEW)
    assert NEW not in old_text and old in old_text

    resp = _read(profile_db, master_db, obs.id, method)
    assert resp.status_code == _ok(method), resp.text
    body = resp.json()
    assert body["interpretation_text"].count(NEW) == 1, body["interpretation_text"]
    assert old not in body["interpretation_text"]
    assert body["id"] != old_id
    (row,) = await _cards_of(profile_db, obs.id)
    assert row.id == body["id"]
    assert row.regeneration_count == 1
    assert row.previous_interpretation_id == old_id
    assert row.model_id == "template-v1" and row.model_tier == "template"
    # the same audit pair a rebuild writes today (HC-VRC-026)
    want = {
        "GET": [("interpretation.generate", "started"), ("interpretation.generate", "completed"),
                ("interpretation.view", None)],
        "POST": [("interpretation.generate", "started"), ("interpretation.generate", "completed")],
    }[method]
    assert await _audit_pairs(master_db) == want

    spy = _WriteSpy(profile_db)  # a second read writes nothing
    before = await _snapshot(profile_db, obs.id)
    for _ in range(2):
        again = _read(profile_db, master_db, obs.id, method)
        assert again.status_code == _ok(method), again.text
        assert again.json()["id"] == body["id"]
    assert spy.writes == (0, 0), "a second read wrote"
    spy.close()
    assert await _snapshot(profile_db, obs.id) == before
    # rdbs raises if the model was selected or called; the count is checked again here
    assert ModelSelector.run_inference.await_count == 0
    assert ModelSelector.get_model_for_inference.await_count == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("method", READS)
@pytest.mark.parametrize("old_place", ["above", "below", "within"])
async def test_hc_kfd_006_a_knowledge_base_form_card_is_rebuilt(rdbs, method, old_place):
    profile_db, master_db = rdbs
    master_db.add(BiomarkerKnowledge(id="kb-ldl_cholesterol", **LDL))
    await master_db.commit()
    obs, old_id, old_text = await _old_card(
        profile_db, dict(analyte_canonical="ldl_cholesterol", value=85.0, flag="H", is_abnormal=True),
        _kb_text(LDL_KB, old_place), NEW, kb=LDL_KB)
    assert "[KB:kb-ldl_cholesterol]" in old_text
    resp = _read(profile_db, master_db, obs.id, method)
    assert resp.status_code == _ok(method), resp.text
    text = resp.json()["interpretation_text"]
    assert text.count(NEW) == 1, text
    for words in _kb_words(LDL_KB):
        assert words not in text, text
    assert resp.json()["id"] != old_id
    assert len(await _cards_of(profile_db, obs.id)) == 1


# ── HC-KFD-007: what is left alone ───────────────────────────────────────────


def _unchanged(profile_db, obs_id):
    async def _go(method, master_db, card_id, text, before):
        spy = _WriteSpy(profile_db)
        resp = _read(profile_db, master_db, obs_id, method)
        assert resp.status_code == _ok(method), resp.text
        assert resp.json()["id"] == card_id
        assert resp.json()["interpretation_text"] == text
        assert spy.writes == (0, 0)
        spy.close()
        assert await _snapshot(profile_db, obs_id) == before
    return _go


@pytest.mark.asyncio
@pytest.mark.parametrize("method", READS)
@pytest.mark.parametrize("kw", [p.values[0] for p in REBUILD], ids=[p.id for p in REBUILD])
async def test_hc_kfd_007_a_card_that_already_holds_the_sentence_is_never_rewritten(rdbs, method, kw):
    profile_db, master_db = rdbs
    obs, card_id, text = await _old_card(profile_db, kw, None, None, regeneration_count=2)
    assert NEW in text
    before = await _snapshot(profile_db, obs.id)
    await _unchanged(profile_db, obs.id)(method, master_db, card_id, text, before)


@pytest.mark.asyncio
@pytest.mark.parametrize("method", READS)
@pytest.mark.parametrize("old", OLD_SENTENCES)
@pytest.mark.parametrize("card_kw", [
    pytest.param(dict(model_tier="high", model_id="biomistral-7b-q4"), id="high-tier"),
    pytest.param(dict(model_tier="template", model_id="other-template-v2"), id="template-tier-other-id"),
    pytest.param(dict(model_tier="mid", model_id="template-v1"), id="other-tier-template-id"),
])
async def test_hc_kfd_007_a_model_written_card_with_a_disagreement_is_left_alone(
    rdbs, method, old, card_kw
):
    profile_db, master_db = rdbs
    obs, card_id, text = await _old_card(
        profile_db, dict(value=85.0, flag="H", is_abnormal=True), old, NEW, **card_kw)
    before = await _snapshot(profile_db, obs.id)
    await _unchanged(profile_db, obs.id)(method, master_db, card_id, text, before)
    assert old in text and NEW not in text


@pytest.mark.asyncio
@pytest.mark.parametrize("method", READS)
async def test_hc_kfd_007_a_template_card_with_no_readable_claim_is_not_stale(rdbs, method):
    # Same rule as HC-VRC-023: a card whose words say nothing the status block writes is kept.
    profile_db, master_db = rdbs
    obs = _obs(user_verified=True, value=300.0, flag="N", is_abnormal=True)
    obs_id = obs.id
    profile_db.add(obs)
    await profile_db.commit()
    text = "Your GLUCOSE result is 300.0 mg/dL. Ask your doctor."
    card_id = await _add_card(profile_db, obs_id, text)
    before = await _snapshot(profile_db, obs_id)
    await _unchanged(profile_db, obs_id)(method, master_db, card_id, text, before)


@pytest.mark.asyncio
@pytest.mark.parametrize("method", READS)
async def test_hc_kfd_007_a_knowledge_base_card_with_a_stale_marker_but_no_claim_is_kept(rdbs, method):
    # A KB card's "What this test measures ... [KB:id]" line carries a marker but no status claim.
    profile_db, master_db = rdbs
    master_db.add(BiomarkerKnowledge(id="kb-ldl_cholesterol", **LDL))
    await master_db.commit()
    obs = _obs(user_verified=True, analyte_canonical="ldl_cholesterol", value=85.0, flag="H",
               is_abnormal=True)
    obs_id = obs.id
    profile_db.add(obs)
    await profile_db.commit()
    text = f"Your LDL result is 85.0 mg/dL. {LDL['description']} [KB:kb-ldl_cholesterol]"
    card_id = await _add_card(profile_db, obs_id, text)
    before = await _snapshot(profile_db, obs_id)
    await _unchanged(profile_db, obs_id)(method, master_db, card_id, text, before)


# ── HC-KFD-008: a panel read that rebuilds reaches the member ────────────────


@pytest.mark.asyncio
async def test_hc_kfd_008_a_rebuilding_panel_read_rebuilds_the_disagreeing_member_card(rdbs):
    # The saved panel is stale for another reason (sodium 150 is above its range but the saved
    # summary lists nothing). The read goes through interpret_observation for every member, so
    # the disagreeing glucose card is rebuilt there; no change to the panel check is needed.
    profile_db, master_db = rdbs
    sodium_high = {**SODIUM_ROW, "value": 150.0, "is_abnormal": True}
    obs_list, old_panel_id, old_summary = await _old_panel(
        profile_db, [dict(value=300.0, flag="N", is_abnormal=True), sodium_high], [True, False],
        old_card=(OUTSIDE, NEW))
    glucose_id = obs_list[0].id
    (old_card,) = await _cards_of(profile_db, glucose_id)
    assert OUTSIDE in old_card.interpretation_text and NEW not in old_card.interpretation_text

    resp = _read_panel(profile_db, master_db)
    assert resp.status_code == 201, resp.text
    assert resp.json()["id"] != old_panel_id
    (card,) = await _cards_of(profile_db, glucose_id)
    assert card.interpretation_text.count(NEW) == 1, card.interpretation_text
    assert OUTSIDE not in card.interpretation_text
    assert card.previous_interpretation_id == old_card.id
    assert await _audit_pairs(master_db) == [(PANEL_EVENT, "started"), (PANEL_EVENT, "completed")]
    started, completed = await _rows_of(master_db, PANEL_EVENT)
    for row in (started, completed):
        assert _det(row)["observation_ids"] == [glucose_id], _det(row)
    assert len(await _panels(profile_db)) == 1


