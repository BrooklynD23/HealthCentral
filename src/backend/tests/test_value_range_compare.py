"""VALUE-RANGE-COMPARE: a result is read against its own numeric range.

Spec: the VALUE-RANGE-COMPARE row of the build-program queue; owner answer
"Compare to range (Recommended)". Before this row, `flag is not None` decided
`is_abnormal` at import, and `modules/interpret.py` branched on that and on an
exact-match flag list, so an unflagged 300 against 70-100 read "within the
normal reference range" and a printed `N` at 85 read "outside".

HC-VRC-001  the helper's truth table (api.observations.observation_range_status
            and status_is_abnormal), every row
HC-VRC-002  sentences, unflagged 300 / 40 / 85, no KB and KB
HC-VRC-003  printed normal words in range never read "outside"
HC-VRC-004  printed H/L words: unchanged where they agree, `High` and `h` now read
HC-VRC-005  one-sided ranges, a bound of 0.0, a value equal to a bound
HC-VRC-006  disagreements: own status, today's sentence, no new wording
HC-VRC-007  other flags read today's sentence
HC-VRC-008  no comparison possible
HC-VRC-009  the real safety guard, in pipeline order
HC-VRC-010  interpret over HTTP, severity agrees with the sentence
HC-VRC-011  both import writers over HTTP (CSV, FHIR and ruled-grid PDF)
HC-VRC-012  GET /observations/?abnormal_only=true
HC-VRC-013  panel summary over HTTP
HC-VRC-014  the LLM prompt's Flag line
HC-VRC-015  parity with a plain Verify and with _classify_severity
HC-VRC-016  the doctor summary and the questions never print a stored None flag
HC-VRC-017  a saved template card on the old wording is rebuilt on read (single)
HC-VRC-018  below, and a printed N at an in-range value with an old "outside"
HC-VRC-019  a card in agreement is returned untouched, no write
HC-VRC-020  a model-written card is never rebuilt, the model is never called
HC-VRC-021  a saved template panel on the old wording is rebuilt on read
HC-VRC-022  a panel in agreement, or written by another model_id, is untouched
HC-VRC-023  disagreements and uncomparable rows are never rebuilt
HC-VRC-024  a withheld rebuild keeps the old row and serves none of its text
HC-VRC-025  strict safety mode refuses first
HC-VRC-026  audit rows of a rebuilding read (the started/completed pair)
HC-VRC-027  no rewrite loop: a fresh card is never stale
HC-VRC-028  grounded and batch reach the rebuild; GET keeps its ownership check
HC-VRC-029  the A2 pair on every rebuilding route: fail closed, order, no rows on agreement
HC-VRC-030  a withheld member of a stale panel fails the read closed; the saved panel stays
HC-VRC-031  a withheld member with a saved card fails closed whatever the saved panel is
HC-VRC-032  a withheld batch card writes the interpretation.withheld row
HC-VRC-033  a withheld first-generation member is counted, never named, audited

The helper is reached through a function (not a module-level import), so before
the fix each test fails on its own id instead of the whole file failing to collect.
"""

from __future__ import annotations

import hashlib
import inspect
import io
import json
import uuid
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

import api.export as export_api
import api.interpretations as interp_api
import api.observations as obs_api
import models  # noqa: F401  (registers tables on Base.metadata)
from api import documents as documents_api
from api.documents import router as documents_router
from api.interpretations import router as interpretations_router
from core.auth import get_profile_db_session
from core.database import Base
from core.profile_database import ProfileDatabaseBase
from models import Document, LabInterpretation, Observation, PanelInterpretation, UserModelSettings
from models.audit import AuditLog
from models.knowledge_base import BiomarkerKnowledge
from modules.agent.guardrails.templates import ESCALATE_TEMPLATE
from modules.interpret import InterpretationContext, InterpretModule
from modules.interpret_safety import InterpretationSafetyGuard
from modules.knowledge_loader import BiomarkerInfo, get_knowledge_loader
from modules.model_selector import ModelSelector
from scripts.seed_knowledge_base import BIOMARKER_DATA
from tests.support.routes import route_client

PROFILE_ID = "profile-a"  # route_client's default session profile_id
LO, HI = 70.0, 100.0

ABOVE = "This value is above the reference range."
BELOW = "This value is below the reference range."
WITHIN = "This value is within the normal reference range."
OUTSIDE = "This value is outside the normal reference range."
NO_RANGE = (
    "This report did not include a reference range, "
    "so this result can't be compared to one."
)
# KEPT-FLAG-DISAGREES: what a "disagrees" status says, owner's words.
FLAG_RANGE_DISAGREE = (
    "The flag printed on your report and the printed range disagree for this value. "
    "Ask your clinician or the lab which applies."
)
# Every status sentence main can produce without a knowledge-base entry.
CLOSED = [ABOVE, BELOW, WITHIN, OUTSIDE, NO_RANGE, FLAG_RANGE_DISAGREE]


# ── the helper, reached lazily ───────────────────────────────────────────────


def _status(flag, value, ref_low, ref_high, has_range_text=None):
    if has_range_text is None:
        return obs_api.observation_range_status(flag, value, ref_low, ref_high)
    return obs_api.observation_range_status(flag, value, ref_low, ref_high, has_range_text)


def _abnormal(status, fallback):
    return obs_api.status_is_abnormal(status, fallback)


# ── scaffolding (patterns copied from test_no_range_wording.py) ──────────────


def _module() -> InterpretModule:
    return InterpretModule(
        knowledge_loader=SimpleNamespace(get_biomarker_knowledge=AsyncMock(return_value=None)),
        safety_guard=SimpleNamespace(),
        recommendation_engine=SimpleNamespace(generate_recommendations=AsyncMock(return_value=None)),
        model_selector=SimpleNamespace(),
    )


def _kb_from(data: dict) -> BiomarkerInfo:
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
    analyte_canonical="glucose",
    display_name="Synthetic Marker",
    description="SENTINEL-DESCRIPTION",
    clinical_significance=None,
    normal_interpretation="SENTINEL-NORMAL",
    high_interpretation="SENTINEL-HIGH",
    low_interpretation="SENTINEL-LOW",
)
SEED_KBS = [pytest.param(_kb_from(d), id=d["analyte_canonical"]) for d in BIOMARKER_DATA]
KB_CASES = [pytest.param(None, id="no-kb"), pytest.param(SYNTHETIC_KB, id="synthetic-kb")] + SEED_KBS


def _obs(**kw) -> Observation:
    base = dict(
        id=str(uuid.uuid4()), profile_id=PROFILE_ID, doc_id=str(uuid.uuid4()),
        analyte_canonical="glucose", analyte_raw="Glucose",
        value=85.0, unit="mg/dL", ref_low=LO, ref_high=HI, ref_range_text=None,
        flag=None, is_abnormal=False, collected_at=datetime(2026, 3, 1, 9, 0, 0),
    )
    base.update(kw)
    return Observation(**base)


async def _text(obs: Observation, kb: BiomarkerInfo | None = None) -> str:
    text, _ = await _module()._generate_interpretation(
        InterpretationContext(observation=obs, biomarker_info=kb), AsyncMock()
    )
    return text


def _kb_text(kb: BiomarkerInfo, place: str) -> str:
    field = {"above": kb.high_interpretation, "below": kb.low_interpretation,
             "within": kb.normal_interpretation}[place]
    return f"{field} [KB:{kb.id}]"


def _sentence(kb: BiomarkerInfo | None, place: str) -> str:
    if kb is not None:
        return _kb_text(kb, place)
    return {"above": ABOVE, "below": BELOW, "within": WITHIN}[place]


def _residue(text: str, obs: Observation) -> str:
    """What is left of a no-KB card after the value sentence, the range sentence and
    every sentence main can already produce are removed. Non-empty means new wording."""
    known = [f"Your {obs.analyte_canonical.upper()} result is {obs.value} {obs.unit}."]
    if obs.ref_low is not None and obs.ref_high is not None:
        known.append(f"The reference range is {obs.ref_low}-{obs.ref_high} {obs.unit}.")
    if obs.ref_range_text and obs.ref_range_text.strip():
        known.append(f"Reference range: {obs.ref_range_text}.")
    for s in known + CLOSED:
        text = text.replace(s, "")
    return text.strip()


PLACE_VALUE = {"above": 300.0, "below": 40.0, "within": 85.0}


# ── HC-VRC-001: the helper's truth table ─────────────────────────────────────

_MIXED = lambda words: sorted({v for w in words for v in (w, w.lower(), w.capitalize(), f" {w.lower()} ")})  # noqa: E731
NORMAL_WORDS = _MIXED(obs_api._NORMAL_FLAGS)
HIGH_WORDS = _MIXED(["H", "HH", "HIGH"]) + ["\tHIGH\n"]
LOW_WORDS = _MIXED(["L", "LL", "LOW"]) + ["\tlow\n"]
OTHER_WORDS = ["A", "a", "ABNORMAL", "CRITICAL", "Positive", "  ", "", "\t"]

# place -> (value, ref_low, ref_high)
ARGS = {
    "above": (300.0, LO, HI),
    "below": (40.0, LO, HI),
    "inside": (85.0, LO, HI),
    "no-bounds": (300.0, None, None),
    "no-value": (None, LO, HI),
    "no-value-no-bounds": (None, None, None),
}
NO_COMPARE = ("no-bounds", "no-value", "no-value-no-bounds")

NONE_FLAG = {"above": "above", "below": "below", "inside": "within",
             **{k: "keep" for k in NO_COMPARE}}
NORMAL = {"above": "disagrees", "below": "disagrees", "inside": "within",
          **{k: "normal_uncompared" for k in NO_COMPARE}}
HIGH = {"above": "above", "below": "disagrees", "inside": "disagrees",
        **{k: "above" for k in NO_COMPARE}}
LOW = {"above": "disagrees", "below": "below", "inside": "disagrees",
       **{k: "below" for k in NO_COMPARE}}
OTHER = {k: "keep" for k in ARGS}

TABLE = (
    [(None, p, want) for p, want in NONE_FLAG.items()]
    + [(w, p, want) for w in NORMAL_WORDS for p, want in NORMAL.items()]
    + [(w, p, want) for w in HIGH_WORDS for p, want in HIGH.items()]
    + [(w, p, want) for w in LOW_WORDS for p, want in LOW.items()]
    + [(w, p, want) for w in OTHER_WORDS for p, want in OTHER.items()]
)


@pytest.mark.parametrize(
    "flag,place,want", [pytest.param(f, p, w, id=f"{f!r}-{p}") for f, p, w in TABLE]
)
def test_hc_vrc_001_truth_table(flag, place, want):
    assert _status(flag, *ARGS[place]) == want


@pytest.mark.parametrize("word", NORMAL_WORDS)
@pytest.mark.parametrize(
    "place,value,has_text,want",
    [
        ("text-only-number", 300.0, True, "keep"),            # value, no bounds, a range text
        ("text-only-no-value", None, True, "normal_uncompared"),
        ("no-text", 300.0, False, "normal_uncompared"),
    ],
)
def test_hc_vrc_001_normal_word_with_a_text_only_range(word, place, value, has_text, want):
    assert _status(word, value, None, None, has_text) == want


@pytest.mark.parametrize("flag,want", [(None, "keep"), ("H", "above"), ("L", "below"), ("A", "keep")])
def test_hc_vrc_001_text_only_range_does_not_change_other_flags(flag, want):
    assert _status(flag, 300.0, None, None, True) == want


def test_hc_vrc_001_numeric_bounds_win_over_range_text():
    assert _status("N", 85.0, LO, HI, True) == "within"
    assert _status("N", 300.0, LO, HI, True) == "disagrees"


def test_hc_vrc_001_normal_words_come_from_the_existing_set():
    # The helper reuses _NORMAL_FLAGS, it does not copy it: every word in the real set
    # must take the normal-word rows, and the set is the one VERIFY-FLAG-WORDS defined.
    assert obs_api._NORMAL_FLAGS == frozenset({"NORMAL", "N", "WNL", "NO", "FALSE", "0"})
    for word in obs_api._NORMAL_FLAGS:
        assert _status(word, 85.0, LO, HI) == "within", word
        assert _status(word, 300.0, LO, HI) == "disagrees", word
        assert _status(word, None, None, None) == "normal_uncompared", word


def test_hc_vrc_001_status_to_abnormal_mapping():
    for fallback in (True, False, None):
        assert _abnormal("above", fallback) is True
        assert _abnormal("below", fallback) is True
        assert _abnormal("within", fallback) is False
        assert _abnormal("normal_uncompared", fallback) is False
    assert _abnormal("disagrees", True) is True
    assert _abnormal("disagrees", False) is False
    assert _abnormal("keep", True) is True
    assert _abnormal("keep", False) is False
    # A stored None is "not abnormal", as every reader treats it today.
    assert _abnormal("keep", None) is False
    assert _abnormal("disagrees", None) is False


def test_hc_vrc_001_helper_takes_no_range_text():
    # ref_range_text is never parsed: the helper cannot receive the text, only whether
    # one is present (a bool, default False).
    params = inspect.signature(obs_api.observation_range_status).parameters
    assert list(params) == ["flag", "value", "ref_low", "ref_high", "has_range_text"]
    assert params["has_range_text"].default is False


@pytest.mark.parametrize(
    "value,lo,hi,want",
    [
        (70.0, LO, HI, "within"),      # equal to a bound is inside (Verify, _classify_severity)
        (100.0, LO, HI, "within"),
        (69.99, LO, HI, "below"),
        (100.01, LO, HI, "above"),
        (-1.0, 0.0, None, "below"),    # 0.0 is a real bound, not "missing"
        (0.0, 0.0, None, "within"),
        (0.1, None, 0.0, "above"),
        (0.0, None, 0.0, "within"),
        (-5.0, None, 0.0, "within"),
        (0.0, 0.0, 0.0, "within"),
        (1.0, 0.0, 0.0, "above"),
        (85.0, HI, LO, "below"),       # inverted range: low is checked first, as Verify does
    ],
)
def test_hc_vrc_001_bounds_and_zero(value, lo, hi, want):
    assert _status(None, value, lo, hi) == want


# ── HC-VRC-002: unflagged value, sentences ───────────────────────────────────

PLACES = [pytest.param(p, id=p) for p in ("above", "below", "within")]


@pytest.mark.asyncio
@pytest.mark.parametrize("stored", [False, None, True])
@pytest.mark.parametrize("place", PLACES)
@pytest.mark.parametrize("kb", [None, SYNTHETIC_KB], ids=["no-kb", "synthetic-kb"])
async def test_hc_vrc_002_unflagged_value_reads_against_its_range(kb, place, stored):
    text = await _text(_obs(value=PLACE_VALUE[place], is_abnormal=stored), kb)
    want = _sentence(kb, place)
    assert want in text, text
    for other in {"above", "below", "within"} - {place}:
        assert _sentence(kb, other) not in text, text
    assert NO_RANGE not in text, text
    if kb is None:
        assert _residue(text, _obs(value=PLACE_VALUE[place])) == "", text


@pytest.mark.asyncio
@pytest.mark.parametrize("place", PLACES)
@pytest.mark.parametrize("kb", SEED_KBS)
async def test_hc_vrc_002_seeded_kb_text_keeps_its_marker(kb, place):
    text = await _text(_obs(value=PLACE_VALUE[place], analyte_canonical=kb.analyte_canonical), kb)
    assert _kb_text(kb, place) in text, text
    assert f"[KB:{kb.id}]" in text
    for other in {"above", "below", "within"} - {place}:
        assert _kb_text(kb, other) not in text, text


# ── HC-VRC-003: a printed normal word in range never reads "outside" ─────────


@pytest.mark.asyncio
@pytest.mark.parametrize("stored", [True, False])
@pytest.mark.parametrize("word", ["N", "Normal", "WNL", "NO", "FALSE", "0", "n", "normal", "wnl", "no", "false"])
@pytest.mark.parametrize("kb", [None, SYNTHETIC_KB], ids=["no-kb", "synthetic-kb"])
async def test_hc_vrc_003_printed_normal_word_in_range_reads_within(kb, word, stored):
    text = await _text(_obs(flag=word, value=85.0, is_abnormal=stored), kb)
    assert _sentence(kb, "within") in text, text
    assert "outside" not in text.lower(), text
    assert "above" not in text.lower() and "below" not in text.lower(), text


# ── HC-VRC-004: printed H / L words ──────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("kb", [None, SYNTHETIC_KB], ids=["no-kb", "synthetic-kb"])
@pytest.mark.parametrize("word", ["H", "HH", "HIGH"])
async def test_hc_vrc_004_guard_printed_high_words_at_a_high_value_unchanged(kb, word):
    text = await _text(_obs(flag=word, value=300.0, is_abnormal=True), kb)
    assert _sentence(kb, "above") in text, text


@pytest.mark.asyncio
@pytest.mark.parametrize("kb", [None, SYNTHETIC_KB], ids=["no-kb", "synthetic-kb"])
@pytest.mark.parametrize("word", ["L", "LL", "LOW"])
async def test_hc_vrc_004_guard_printed_low_words_at_a_low_value_unchanged(kb, word):
    text = await _text(_obs(flag=word, value=40.0, is_abnormal=True), kb)
    assert _sentence(kb, "below") in text, text


@pytest.mark.asyncio
@pytest.mark.parametrize("stored", [True, False])
@pytest.mark.parametrize("kb", [None, SYNTHETIC_KB], ids=["no-kb", "synthetic-kb"])
@pytest.mark.parametrize("word", ["High", "h", "hh", " H ", "high"])
async def test_hc_vrc_004_mixed_case_high_at_a_high_value_reads_above(kb, word, stored):
    text = await _text(_obs(flag=word, value=300.0, is_abnormal=stored), kb)
    assert _sentence(kb, "above") in text, text
    assert "outside" not in text.lower(), text


@pytest.mark.asyncio
@pytest.mark.parametrize("stored", [True, False])
@pytest.mark.parametrize("kb", [None, SYNTHETIC_KB], ids=["no-kb", "synthetic-kb"])
@pytest.mark.parametrize("word", ["Low", "l", "ll", " L ", "low"])
async def test_hc_vrc_004_mixed_case_low_at_a_low_value_reads_below(kb, word, stored):
    text = await _text(_obs(flag=word, value=40.0, is_abnormal=stored), kb)
    assert _sentence(kb, "below") in text, text
    assert "outside" not in text.lower(), text


# ── HC-VRC-005: one-sided ranges, 0.0 bounds, a value equal to a bound ───────

ONE_SIDED = [
    # (ref_low, ref_high, value, place)
    (None, HI, 300.0, "above"),
    (None, HI, 85.0, "within"),
    (None, HI, 100.0, "within"),   # equal to the bound is inside
    (None, HI, 5.0, "within"),     # no low bound: nothing is below
    (LO, None, 40.0, "below"),
    (LO, None, 85.0, "within"),
    (LO, None, 70.0, "within"),
    (LO, None, 9999.0, "within"),  # no high bound: nothing is above
    (None, 0.0, 5.0, "above"),     # a high bound of 0.0 is a real bound
    (None, 0.0, 0.0, "within"),
    (None, 0.0, -3.0, "within"),
    (0.0, None, -1.0, "below"),    # a low bound of 0.0 is a real bound
    (0.0, None, 0.0, "within"),
    (0.0, None, 7.0, "within"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("lo,hi,value,place", [pytest.param(*c, id=f"{c[0]}-{c[1]}-{c[2]}") for c in ONE_SIDED])
@pytest.mark.parametrize("kb", [None, SYNTHETIC_KB], ids=["no-kb", "synthetic-kb"])
async def test_hc_vrc_005_one_sided_range_and_zero_bounds(kb, lo, hi, value, place):
    text = await _text(_obs(ref_low=lo, ref_high=hi, value=value, is_abnormal=False), kb)
    assert _sentence(kb, place) in text, text
    for other in {"above", "below", "within"} - {place}:
        assert _sentence(kb, other) not in text, text


# ── HC-VRC-006: disagreements ────────────────────────────────────────────────
# (flag, value, ref_low, ref_high, stored is_abnormal, the sentence main prints today)

DISAGREE = []
for _flag, _value, _lo, _hi in [
    ("N", 300.0, LO, HI), ("Normal", 300.0, LO, HI), ("N", 40.0, LO, HI), ("Normal", 40.0, LO, HI),
    ("WNL", 300.0, LO, HI), ("0", 40.0, LO, HI), ("n", 300.0, LO, HI),
]:
    DISAGREE += [(_flag, _value, _lo, _hi, True, OUTSIDE), (_flag, _value, _lo, _hi, False, WITHIN)]
for _flag, _value, _lo, _hi, _stored_true in [
    ("H", 85.0, LO, HI, ABOVE), ("HH", 85.0, LO, HI, ABOVE), ("H", 40.0, LO, HI, ABOVE),
    ("L", 85.0, LO, HI, BELOW), ("LOW", 85.0, LO, HI, BELOW), ("L", 18.0, 12.0, 16.0, BELOW),
    ("L", 300.0, LO, HI, BELOW),
]:
    DISAGREE += [(_flag, _value, _lo, _hi, True, _stored_true), (_flag, _value, _lo, _hi, False, WITHIN)]
# Mixed-case H/L words with a stored True do not match main's exact lists, so main
# prints "outside" for them; that is also today's sentence.
DISAGREE += [("High", 85.0, LO, HI, True, OUTSIDE), ("low", 300.0, LO, HI, True, OUTSIDE)]

DISAGREE_PARAMS = [pytest.param(*c, id=f"{c[0]}-{c[1]}-{c[2]}-{c[3]}-{c[4]}") for c in DISAGREE]


@pytest.mark.parametrize("flag,value,lo,hi,stored,literal", DISAGREE_PARAMS)
def test_hc_vrc_006_status_is_disagrees_and_follows_the_stored_value(flag, value, lo, hi, stored, literal):
    status = _status(flag, value, lo, hi)
    assert status == "disagrees"
    assert _abnormal(status, stored) is stored


@pytest.mark.asyncio
@pytest.mark.parametrize("flag,value,lo,hi,stored,literal", DISAGREE_PARAMS)
async def test_hc_vrc_006_guard_disagreement_sentence_is_main_literal_with_no_new_wording(
    flag, value, lo, hi, stored, literal
):
    obs = _obs(flag=flag, value=value, ref_low=lo, ref_high=hi, is_abnormal=stored)
    text = await _text(obs)
    assert FLAG_RANGE_DISAGREE in text, text
    # Closed list: remove everything main can already say; nothing may be left over.
    assert _residue(text, obs) == "", text
    for other in [s for s in CLOSED if s != FLAG_RANGE_DISAGREE]:
        assert other not in text, text


@pytest.mark.asyncio
@pytest.mark.parametrize("flag,stored,field", [("N", True, None), ("H", True, "high_interpretation")])
async def test_hc_vrc_006_guard_disagreement_with_kb_uses_todays_kb_text(flag, stored, field):
    obs = _obs(flag=flag, value=300.0 if flag == "N" else 85.0, is_abnormal=stored)
    text = await _text(obs, SYNTHETIC_KB)
    assert FLAG_RANGE_DISAGREE in text, text
    assert "SENTINEL" not in text, text


# ── HC-VRC-007: any other flag reads today's sentence ────────────────────────

OTHER_FLAGS = ["A", "ABNORMAL", "CRITICAL", "Positive", "  "]


@pytest.mark.parametrize("flag", OTHER_FLAGS + [""])
@pytest.mark.parametrize("value", [300.0, 85.0, 40.0])
def test_hc_vrc_007_other_flags_have_status_keep(flag, value):
    assert _status(flag, value, LO, HI) == "keep"


@pytest.mark.asyncio
@pytest.mark.parametrize("flag", OTHER_FLAGS)
@pytest.mark.parametrize("value", [300.0, 85.0, 40.0], ids=["above", "inside", "below"])
@pytest.mark.parametrize("stored", [True, False])
async def test_hc_vrc_007_guard_other_flags_read_todays_sentence(flag, value, stored):
    obs = _obs(flag=flag, value=value, is_abnormal=stored)
    text = await _text(obs)
    literal = OUTSIDE if stored else WITHIN
    assert literal in text, text
    assert _residue(text, obs) == "", text


# ── HC-VRC-008: no comparison is possible ────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("stored,literal", [(False, WITHIN), (True, OUTSIDE)])
async def test_hc_vrc_008_guard_range_text_only_is_not_parsed(stored, literal):
    # "70-100" in ref_range_text would make 300 high if someone parsed it. Nobody does.
    obs = _obs(value=300.0, ref_low=None, ref_high=None, ref_range_text="70-100", is_abnormal=stored)
    text = await _text(obs)
    assert literal in text, text
    assert ABOVE not in text, text
    assert "Reference range: 70-100." in text, text


@pytest.mark.asyncio
@pytest.mark.parametrize("stored,literal", [(False, WITHIN), (True, OUTSIDE)])
async def test_hc_vrc_008_guard_no_value_with_a_numeric_range_and_no_flag_is_todays(stored, literal):
    obs = _obs(value=None, value_text="pending", is_abnormal=stored)
    text = await _text(obs)
    assert literal in text, text
    assert ABOVE not in text and BELOW not in text, text


@pytest.mark.asyncio
@pytest.mark.parametrize("stored", [True, False])
@pytest.mark.parametrize("word", ["N", "Normal", "WNL"])
async def test_hc_vrc_008_normal_word_with_no_range_reads_the_no_range_sentence(word, stored):
    text = await _text(_obs(flag=word, value=85.0, ref_low=None, ref_high=None, is_abnormal=stored))
    assert NO_RANGE in text, text
    assert "outside" not in text.lower() and "within" not in text.lower(), text


@pytest.mark.asyncio
@pytest.mark.parametrize("word", ["N", "Normal", "WNL"])
@pytest.mark.parametrize("value", [300.0, 85.0])
async def test_hc_vrc_008_normal_word_with_range_text_only_stays_todays_sentence(value, word):
    # A printed normal word on a number whose range exists only as text cannot be
    # compared (the text is never parsed) and nothing says the number is normal, so the
    # stored value decides, as on main. Stored True stays "outside"; no new reassurance.
    stored_true = _obs(flag=word, value=value, ref_low=None, ref_high=None, ref_range_text="70-100", is_abnormal=True)
    text = await _text(stored_true)
    assert OUTSIDE in text, text
    assert WITHIN not in text, text
    stored_false = _obs(flag=word, value=value, ref_low=None, ref_high=None, ref_range_text="70-100", is_abnormal=False)
    text = await _text(stored_false)
    assert WITHIN in text and OUTSIDE not in text, text


@pytest.mark.asyncio
@pytest.mark.parametrize("stored", [True, False])
async def test_hc_vrc_008_normal_word_with_no_value_and_a_range_reads_within(stored):
    obs = _obs(flag="N", value=None, value_text="pending", is_abnormal=stored)
    text = await _text(obs)
    assert WITHIN in text, text
    assert "outside" not in text.lower(), text


@pytest.mark.asyncio
@pytest.mark.parametrize("stored", [True, False])
async def test_hc_vrc_008_printed_high_with_no_range_reads_above(stored):
    obs = _obs(flag="H", value=300.0, ref_low=None, ref_high=None, is_abnormal=stored)
    text = await _text(obs)
    assert ABOVE in text, text


@pytest.mark.asyncio
async def test_hc_vrc_008_printed_low_with_no_value_reads_below():
    text = await _text(_obs(flag="L", value=None, value_text="pending", is_abnormal=False))
    assert BELOW in text, text


@pytest.mark.asyncio
@pytest.mark.parametrize("range_text", ["", "   "])
async def test_hc_vrc_008_blank_range_text_prints_no_range_line(range_text):
    text = await _text(_obs(value=85.0, ref_low=None, ref_high=None, ref_range_text=range_text))
    assert "Reference range:" not in text, text
    assert NO_RANGE in text, text


# ── HC-VRC-009: the real safety guard, in pipeline order ─────────────────────


def _guard(text: str):
    guard = InterpretationSafetyGuard()
    final_text, final_advice = guard.add_required_disclaimers(interpretation_text=text, advice_text=None)
    return guard.validate_interpretation(
        interpretation_text=final_text, advice_text=final_advice, require_citations=True
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("kb", KB_CASES)
@pytest.mark.parametrize(
    "kw,place",
    [
        (dict(value=300.0), "above"),
        (dict(value=40.0), "below"),
        (dict(value=85.0), "within"),
        (dict(value=85.0, flag="N", is_abnormal=True), "within"),
        (dict(value=300.0, flag="High", is_abnormal=True), "above"),
        (dict(value=40.0, flag="low", is_abnormal=True), "below"),
    ],
    ids=["above", "below", "within", "N-in-range", "High-above", "low-below"],
)
async def test_hc_vrc_009_real_guard_passes_every_new_sentence(kb, kw, place):
    obs = _obs(**kw)
    if kb is not None:
        obs.analyte_canonical = kb.analyte_canonical
    text = await _text(obs, kb)
    # Precondition: the case really produced the new sentence (this is what is RED on main).
    assert _sentence(kb, place) in text, text
    verdict = _guard(text)
    assert verdict.passed is True, verdict
    assert verdict.checks_failed == [], verdict.checks_failed


# ── HTTP scaffolding ─────────────────────────────────────────────────────────


async def _engine_session(base):
    engine = create_async_engine(
        "sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(base.metadata.create_all)
    return AsyncSession(engine, expire_on_commit=False), engine


@asynccontextmanager
async def _dbs_ctx():
    profile_db, p_engine = await _engine_session(ProfileDatabaseBase)
    master_db, m_engine = await _engine_session(Base)
    get_knowledge_loader().clear_cache()  # the process-wide cache would hide master DB rows
    try:
        yield profile_db, master_db
    finally:
        get_knowledge_loader().clear_cache()
        await profile_db.close()
        await master_db.close()
        await p_engine.dispose()
        await m_engine.dispose()


@pytest_asyncio.fixture
async def dbs():
    async with _dbs_ctx() as pair:
        yield pair


def _call(profile_db, master_db, router, prefix, method, url, **kwargs):
    with route_client(router, prefix, profile_id=PROFILE_ID, master_db=master_db) as client:

        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        return client.request(method, url, **kwargs)


async def _seed(profile_db, **kw) -> str:
    obs = _obs(user_verified=True, **kw)
    profile_db.add(obs)
    await profile_db.commit()
    return obs.id


async def _interpret(profile_db, master_db, **kw) -> dict:
    obs_id = await _seed(profile_db, **kw)
    resp = _call(profile_db, master_db, interpretations_router, "/interpretations", "POST",
                 f"/interpretations/observations/{obs_id}/interpret")
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── HC-VRC-010: interpret over HTTP, severity agrees with the sentence ───────

HTTP_CASES = [
    pytest.param(dict(value=300.0), ABOVE, "high", id="300"),
    pytest.param(dict(value=40.0), BELOW, "low", id="40"),
    pytest.param(dict(value=85.0), WITHIN, "normal", id="85"),
    pytest.param(dict(value=85.0, flag="N", is_abnormal=True), WITHIN, "normal", id="N-85-stored-true"),
    pytest.param(dict(value=300.0, flag="High", is_abnormal=True), ABOVE, "high", id="High-300"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("kw,sentence,direction", HTTP_CASES)
async def test_hc_vrc_010_http_interpretation_and_severity_agree(dbs, kw, sentence, direction):
    profile_db, master_db = dbs
    body = await _interpret(profile_db, master_db, **kw)
    text, severity = body["interpretation_text"], body["severity_level"]
    assert sentence in text, text
    assert direction in severity, severity
    if direction == "high":
        assert "low" not in severity
    if direction == "low":
        assert "high" not in severity


@pytest.mark.asyncio
async def test_hc_vrc_010_http_seeded_kb_row_uses_the_kb_high_text(dbs):
    profile_db, master_db = dbs
    data = next(d for d in BIOMARKER_DATA if d["analyte_canonical"] == "ldl_cholesterol")
    master_db.add(BiomarkerKnowledge(id=str(uuid.uuid4()), **data))
    await master_db.commit()
    body = await _interpret(profile_db, master_db, analyte_canonical="ldl_cholesterol", value=300.0)
    assert data["high_interpretation"] in body["interpretation_text"], body["interpretation_text"]
    assert "[KB:" in body["interpretation_text"]
    assert data["normal_interpretation"] not in body["interpretation_text"]


# ── HC-VRC-011: both import writers over HTTP ────────────────────────────────

CSV_HEADER = "Date,Analyte,Value,Unit,Reference Low,Reference High,Flag\n"
# (analyte_raw, value, lo, hi, printed flag, stored flag, stored is_abnormal)
CSV_ROWS = [
    ("A-above", "300", "70", "100", "", None, True),
    ("A-below", "40", "70", "100", "", None, True),
    ("A-inside", "85", "70", "100", "", None, False),
    ("A-no-range", "300", "", "", "", None, False),
    ("A-high-only", "300", "", "100", "", None, True),
    ("A-low-only", "85", "70", "", "", None, False),
    ("A-zero-high", "5", "", "0", "", None, True),
    ("N-in-range", "85", "70", "100", "N", "N", False),
    ("Normal-in-range", "85", "70", "100", "Normal", "Normal", False),
    ("WNL-in-range", "85", "70", "100", "WNL", "WNL", False),
    ("N-no-range", "85", "", "", "N", "N", False),
    ("N-out-of-range", "300", "70", "100", "N", "N", True),  # disagrees: stored value kept
    ("H-in-range", "85", "70", "100", "H", "H", True),       # disagrees: stored value kept
    ("H-out-of-range", "300", "70", "100", "H", "H", True),
    ("L-out-of-range", "40", "70", "100", "L", "L", True),
    ("High-out-of-range", "300", "70", "100", "High", "High", True),
    ("Other-flag", "85", "70", "100", "A", "A", True),
]


class _ImportIngest:
    """Stands in for IngestModule (no disk, no encryption), as the other import tests do."""

    stored: dict[str, bytes] = {}

    def __init__(self, *_a, **_k):
        pass

    async def import_document(self, *, file, filename, profile_id, source=None):
        from modules.ingest import ImportResult

        data = file.read()
        doc_id = str(uuid.uuid4())
        _ImportIngest.stored[doc_id] = data
        return ImportResult(
            document_id=doc_id,
            path_hash=hashlib.sha256(doc_id.encode()).hexdigest(),
            content_hash=hashlib.sha256(data).hexdigest(),
            doc_type=(
                "lab_csv" if filename.endswith(".csv")
                else "fhir_bundle" if filename.endswith(".json") else "lab_pdf"
            ),
            page_count=1,
            is_duplicate=False,
            metadata={},
            encrypted=True,
        )


def _post_import(monkeypatch, tmp_path, profile_db, filename, data, content_type):
    import modules
    from tests.test_documents_api import _CommitTrackingMasterDb

    async def _no_classify(**_k):
        return None

    monkeypatch.setattr(type(documents_api.settings), "app_data_path", property(lambda self: tmp_path))
    monkeypatch.setattr(documents_api, "get_profile_encryption_key", lambda _p: b"x" * 32)
    monkeypatch.setattr(modules, "IngestModule", _ImportIngest)
    monkeypatch.setattr(
        documents_api, "get_decrypted_document", lambda _p, d: io.BytesIO(_ImportIngest.stored[d])
    )
    monkeypatch.setattr(documents_api, "_classify_and_extract_entities", _no_classify)
    with route_client(documents_router, "/documents", profile_id=PROFILE_ID,
                      master_db=_CommitTrackingMasterDb()) as client:

        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        return client.post("/documents/import", files={"file": (filename, data, content_type)})


async def _stored_by_raw(profile_db) -> dict[str, Observation]:
    rows = (await profile_db.execute(select(Observation))).scalars().all()
    return {o.analyte_raw: o for o in rows}


@pytest.mark.asyncio
async def test_hc_vrc_011_csv_import_stores_is_abnormal_from_the_range(dbs, monkeypatch, tmp_path):
    profile_db, master_db = dbs
    body = CSV_HEADER + "".join(
        f"2026-06-01,{raw},{v},mg/dL,{lo},{hi},{flag}\n" for raw, v, lo, hi, flag, _f, _a in CSV_ROWS
    )
    resp = _post_import(monkeypatch, tmp_path, profile_db, "labs.csv", body.encode(), "text/csv")
    assert resp.status_code == 201, resp.text
    by_raw = await _stored_by_raw(profile_db)
    assert set(by_raw) == {r[0] for r in CSV_ROWS}, sorted(by_raw)
    wrong = {
        raw: (by_raw[raw].flag, by_raw[raw].is_abnormal)
        for raw, _v, _lo, _hi, _fl, want_flag, want_abn in CSV_ROWS
        if (by_raw[raw].flag, by_raw[raw].is_abnormal) != (want_flag, want_abn)
    }
    assert wrong == {}, wrong

    # Then interpret one stored row through HTTP: the imported no-flag 300 reads above.
    above = by_raw["A-above"]
    resp = _call(profile_db, master_db, interpretations_router, "/interpretations", "POST",
                 f"/interpretations/observations/{above.id}/interpret")
    assert resp.status_code == 201, resp.text
    assert ABOVE in resp.json()["interpretation_text"], resp.json()["interpretation_text"]


# (code.text, value, numeric low/high or None, range text or None, printed interpretation,
#  stored flag, stored is_abnormal)
FHIR_ROWS = [
    ("F-above", 300, (70, 100), None, None, None, True),
    ("F-below", 40, (70, 100), None, None, None, True),
    ("F-inside", 85, (70, 100), None, None, None, False),
    ("F-text-only-no-flag", 300, None, "70-100", None, None, False),   # text is never parsed
    ("F-N-inside", 85, (70, 100), None, "N", "N", False),
    ("F-N-above", 300, (70, 100), None, "N", "N", True),               # disagrees: stored value kept
    ("F-N-text-only", 300, None, "70-100", "N", "N", True),            # cannot compare: stored value kept
    ("F-N-bounds-and-text", 85, (70, 100), "70-100", "N", "N", False),
    ("F-H-text-only", 300, None, "70-100", "H", "H", True),
    ("F-H-inside", 85, (70, 100), None, "H", "H", True),               # disagrees: stored value kept
]


def _fhir_bundle() -> bytes:
    import json

    entries = []
    for name, value, bounds, text, interp, _f, _a in FHIR_ROWS:
        resource = {
            "resourceType": "Observation", "status": "final", "code": {"text": name},
            "effectiveDateTime": "2026-06-01",
            "valueQuantity": {"value": value, "unit": "mg/dL"},
        }
        rng = {}
        if bounds:
            rng["low"], rng["high"] = {"value": bounds[0]}, {"value": bounds[1]}
        if text:
            rng["text"] = text
        if rng:
            resource["referenceRange"] = [rng]
        if interp:
            resource["interpretation"] = [{"text": interp}]
        entries.append({"resource": resource})
    return json.dumps({"resourceType": "Bundle", "type": "collection", "entry": entries}).encode()


@pytest.mark.asyncio
async def test_hc_vrc_011_fhir_import_stores_is_abnormal_from_the_range(dbs, monkeypatch, tmp_path):
    profile_db, master_db = dbs
    resp = _post_import(monkeypatch, tmp_path, profile_db, "bundle.json", _fhir_bundle(), "application/json")
    assert resp.status_code == 201, resp.text
    by_raw = await _stored_by_raw(profile_db)
    assert set(by_raw) == {r[0] for r in FHIR_ROWS}, sorted(by_raw)
    wrong = {
        raw: (by_raw[raw].flag, by_raw[raw].is_abnormal)
        for raw, _v, _b, _t, _i, want_flag, want_abn in FHIR_ROWS
        if (by_raw[raw].flag, by_raw[raw].is_abnormal) != (want_flag, want_abn)
    }
    assert wrong == {}, wrong

    # Interpret the stored text-only rows through HTTP: a printed N on a number whose range
    # is text only keeps main's sentence for its stored value; it is never newly "within".
    n_text = by_raw["F-N-text-only"]
    resp = _call(profile_db, master_db, interpretations_router, "/interpretations", "POST",
                 f"/interpretations/observations/{n_text.id}/interpret")
    assert resp.status_code == 201, resp.text
    assert OUTSIDE in resp.json()["interpretation_text"], resp.json()["interpretation_text"]
    assert WITHIN not in resp.json()["interpretation_text"], resp.json()["interpretation_text"]


def _grid_pdf(rows):
    """Raw-bytes one-page PDF with a ruled grid (pdfplumber reads it as a table)."""
    col_x, row_h, top = [30, 130, 230, 330, 450], 24, 740
    ops = ["0.5 w"]
    for i in range(len(rows) + 1):
        y = top - i * row_h
        ops.append(f"{col_x[0]} {y} m {col_x[-1]} {y} l S")
    for x in col_x:
        ops.append(f"{x} {top} m {x} {top - len(rows) * row_h} l S")
    ops += ["BT", "/F1 11 Tf"]
    for r, row in enumerate(rows):
        for c, text in enumerate(row):
            if text:
                esc = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
                ops.append(f"1 0 0 1 {col_x[c] + 6} {top - r * row_h - 16} Tm ({esc}) Tj")
    ops.append("ET")
    stream = "\n".join(ops).encode("latin-1")
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objs, start=1):
        offsets.append(out.tell())
        out.write(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode())
    out.write("".join(f"{o:010d} 00000 n \n" for o in offsets).encode())
    out.write(f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return out.getvalue()


# (analyte, result cell, unit, range cell, stored flag, stored is_abnormal)
PDF_ROWS = [
    ("Alpha", "300", "mg/dL", "70-100", None, True),     # above, no flag
    ("Bravo", "40", "mg/dL", "70-100", None, True),      # below, no flag
    ("Charlie", "85", "mg/dL", "70-100", None, False),   # inside, no flag
    ("Delta", "300", "mg/dL", "", None, False),          # no range, no flag
    ("Echo", "300 H", "mg/dL", "70-100", "H", True),     # agrees
    ("Foxtrot", "85 H", "mg/dL", "70-100", "H", True),   # disagrees: stored value kept
    ("Golf", "40 L", "mg/dL", "70-100", "L", True),      # agrees
]


@pytest.mark.asyncio
async def test_hc_vrc_011_pdf_import_stores_is_abnormal_from_the_range(dbs, monkeypatch, tmp_path):
    profile_db, master_db = dbs
    rows = [["Test", "Result", "Unit", "Range"]] + [list(r[:4]) for r in PDF_ROWS]
    resp = _post_import(monkeypatch, tmp_path, profile_db, "grid.pdf", _grid_pdf(rows), "application/pdf")
    assert resp.status_code == 201, resp.text
    by_raw = await _stored_by_raw(profile_db)
    assert set(by_raw) == {r[0] for r in PDF_ROWS}, sorted(by_raw)
    wrong = {
        raw: (by_raw[raw].flag, by_raw[raw].is_abnormal)
        for raw, _res, _u, _rng, want_flag, want_abn in PDF_ROWS
        if (by_raw[raw].flag, by_raw[raw].is_abnormal) != (want_flag, want_abn)
    }
    assert wrong == {}, wrong

    alpha = by_raw["Alpha"]
    resp = _call(profile_db, master_db, interpretations_router, "/interpretations", "POST",
                 f"/interpretations/observations/{alpha.id}/interpret")
    assert resp.status_code == 201, resp.text
    assert ABOVE in resp.json()["interpretation_text"], resp.json()["interpretation_text"]


# ── HC-VRC-012: abnormal_only ────────────────────────────────────────────────

# (analyte_raw, kwargs, listed)
ABNORMAL_ONLY = [
    ("unflagged-300", dict(value=300.0, is_abnormal=False), True),
    ("unflagged-40", dict(value=40.0, is_abnormal=False), True),
    ("unflagged-85-stored-false", dict(value=85.0, is_abnormal=False), False),
    ("unflagged-85-stored-true", dict(value=85.0, is_abnormal=True), False),
    ("N-85-stored-true", dict(value=85.0, flag="N", is_abnormal=True), False),
    ("other-flag-stored-false", dict(value=85.0, flag="A", is_abnormal=False), False),
    ("other-flag-stored-true", dict(value=85.0, flag="A", is_abnormal=True), True),
    ("H-85-stored-true", dict(value=85.0, flag="H", is_abnormal=True), True),
    ("H-300-stored-true", dict(value=300.0, flag="H", is_abnormal=True), True),
    ("High-300-stored-false", dict(value=300.0, flag="High", is_abnormal=False), True),
    ("no-range-stored-true", dict(value=300.0, ref_low=None, ref_high=None, is_abnormal=True), True),
    ("no-range-stored-false", dict(value=300.0, ref_low=None, ref_high=None, is_abnormal=False), False),
]


@pytest.mark.asyncio
async def test_hc_vrc_012_abnormal_only_follows_the_range_status(dbs):
    profile_db, master_db = dbs
    for raw, kw, _listed in ABNORMAL_ONLY:
        await _seed(profile_db, analyte_raw=raw, **kw)
    resp = _call(profile_db, master_db, obs_api.router, "/observations", "GET",
                 "/observations/", params={"abnormal_only": "true"})
    assert resp.status_code == 200, resp.text
    got = sorted(o["analyte_raw"] for o in resp.json())
    want = sorted(raw for raw, _kw, listed in ABNORMAL_ONLY if listed)
    assert got == want, {"got_only": sorted(set(got) - set(want)), "missing": sorted(set(want) - set(got))}


@pytest.mark.asyncio
async def test_hc_vrc_012_audit_count_is_the_filtered_count(dbs):
    # The audit call sits after the Python filter, so its count is what the patient was shown.
    import json

    from models.audit import AuditLog

    profile_db, master_db = dbs
    for raw, kw, _listed in ABNORMAL_ONLY:
        await _seed(profile_db, analyte_raw=raw, **kw)
    resp = _call(profile_db, master_db, obs_api.router, "/observations", "GET",
                 "/observations/", params={"abnormal_only": "true"})
    assert resp.status_code == 200, resp.text
    rows = (await master_db.execute(select(AuditLog).where(AuditLog.event_type == "observation.view"))).scalars().all()
    assert len(rows) == 1, [r.event_type for r in rows]
    assert json.loads(rows[0].details_json)["count"] == len(resp.json()) == sum(1 for *_x, listed in ABNORMAL_ONLY if listed)


@pytest.mark.asyncio
async def test_hc_vrc_012_without_the_filter_every_row_is_listed(dbs):
    profile_db, master_db = dbs
    for raw, kw, _listed in ABNORMAL_ONLY:
        await _seed(profile_db, analyte_raw=raw, **kw)
    resp = _call(profile_db, master_db, obs_api.router, "/observations", "GET", "/observations/")
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == len(ABNORMAL_ONLY)


# ── HC-VRC-013: panel summary over HTTP ──────────────────────────────────────

COLLECTED = datetime(2026, 3, 1, 9, 0, 0)


async def _panel(profile_db, master_db, rows):
    """rows: kwargs per observation, all in the cmp panel on one day."""
    for kw in rows:
        await _seed(profile_db, collected_at=COLLECTED, **kw)
    resp = _call(profile_db, master_db, interpretations_router, "/interpretations", "POST",
                 "/interpretations/panels/cmp/interpret",
                 params={"collected_at": COLLECTED.isoformat()})
    assert resp.status_code == 201, resp.text
    return resp.json()


SODIUM_OK = dict(analyte_canonical="sodium", analyte_raw="Sodium", value=140.0,
                 unit="mmol/L", ref_low=135.0, ref_high=145.0)


@pytest.mark.asyncio
async def test_hc_vrc_013_unflagged_300_is_counted_and_listed_as_abnormal(dbs):
    profile_db, master_db = dbs
    body = await _panel(profile_db, master_db, [dict(value=300.0, is_abnormal=False), SODIUM_OK])
    text = body["summary_text"]
    assert "1 of 2 values are within normal range." in text, text
    assert "**Items requiring attention:**" in text, text
    assert "GLUCOSE: 300.0 mg/dL (above normal)" in text, text
    assert body["overall_status"] == "borderline", body["overall_status"]


@pytest.mark.asyncio
async def test_hc_vrc_013_printed_n_in_range_stored_true_is_counted_as_normal(dbs):
    profile_db, master_db = dbs
    body = await _panel(profile_db, master_db,
                        [dict(value=85.0, flag="N", is_abnormal=True), SODIUM_OK])
    text = body["summary_text"]
    assert "2 of 2 values are within normal range." in text, text
    assert "Items requiring attention" not in text, text
    assert body["overall_status"] == "normal", body["overall_status"]
    assert body["requires_physician_review"] is False


@pytest.mark.asyncio
async def test_hc_vrc_013_two_unflagged_out_of_range_of_three_is_concerning(dbs):
    profile_db, master_db = dbs
    potassium = dict(analyte_canonical="potassium", analyte_raw="Potassium", value=9.0,
                     unit="mmol/L", ref_low=3.5, ref_high=5.0)
    body = await _panel(profile_db, master_db,
                        [dict(value=300.0, is_abnormal=False), potassium, SODIUM_OK])
    assert "1 of 3 values are within normal range." in body["summary_text"], body["summary_text"]
    assert body["overall_status"] == "concerning", body["overall_status"]
    assert body["requires_physician_review"] is True


# ── HC-VRC-014: the LLM prompt's Flag line ───────────────────────────────────


def _flag_line(obs: Observation) -> str:
    prompt = _module()._build_llm_prompt(InterpretationContext(observation=obs, biomarker_info=None))
    return next(line for line in prompt.splitlines() if line.startswith("- Flag:"))


@pytest.mark.parametrize(
    "kw,want",
    [
        (dict(value=300.0), "- Flag: H"),
        (dict(value=40.0), "- Flag: L"),
        (dict(value=85.0), "- Flag: normal"),
        (dict(value=300.0, ref_low=None, ref_high=None), "- Flag: normal"),  # no range: nothing to say
        (dict(value=None, value_text="pending"), "- Flag: normal"),
        (dict(value=300.0, flag="N"), "- Flag: N"),                           # printed flag stays printed
        (dict(value=85.0, flag="H"), "- Flag: H"),
        (dict(value=85.0, flag="A"), "- Flag: A"),
        (dict(value=300.0, flag="Normal"), "- Flag: Normal"),
    ],
    ids=["300", "40", "85", "no-range", "no-value", "N-300", "H-85", "A-85", "Normal-300"],
)
def test_hc_vrc_014_llm_prompt_flag_line(kw, want):
    assert _flag_line(_obs(**kw)) == want


# ── HC-VRC-015: parity with a plain Verify and with _classify_severity ───────

PARITY = [
    (69.99, LO, HI), (70.0, LO, HI), (70.01, LO, HI), (85.0, LO, HI),
    (99.99, LO, HI), (100.0, LO, HI), (100.01, LO, HI),
    (5.0, None, HI), (100.0, None, HI), (100.01, None, HI),
    (69.99, LO, None), (70.0, LO, None), (9999.0, LO, None),
    (-0.01, 0.0, None), (0.0, 0.0, None), (5.0, 0.0, None),
    (0.01, None, 0.0), (0.0, None, 0.0), (-1.0, None, 0.0),
    (85.0, HI, LO),   # inverted range: both readers check low first
    (70.0, 0.0, 0.0), (0.0, 0.0, 0.0),
]
VERIFY_FLAG = {"L": "below", "H": "above", None: "within"}


def _severity_place(sev: str) -> str:
    return "below" if "low" in sev else "above" if "high" in sev else "within"


@pytest.mark.asyncio
async def test_hc_vrc_015_helper_matches_plain_verify_and_severity_for_unflagged_rows(dbs):
    profile_db, master_db = dbs
    doc_id = str(uuid.uuid4())
    profile_db.add(Document(
        id=doc_id, profile_id=PROFILE_ID, path_hash="p" * 64, content_hash="c" * 64,
        doc_type="lab_report", status="verified", imported_at=COLLECTED,
    ))
    ids = {}
    for value, lo, hi in PARITY:
        obs = _obs(doc_id=doc_id, value=value, ref_low=lo, ref_high=hi, flag=None, is_abnormal=False)
        profile_db.add(obs)
        ids[(value, lo, hi)] = obs.id
    await profile_db.commit()

    mismatches = []
    for (value, lo, hi), obs_id in ids.items():
        resp = _call(profile_db, master_db, obs_api.router, "/observations", "POST",
                     f"/observations/{obs_id}/verify", json={})
        assert resp.status_code == 200, resp.text
        profile_db.expire_all()
        stored = (await profile_db.execute(select(Observation).where(Observation.id == obs_id))).scalar_one()
        verify_place = VERIFY_FLAG[stored.flag]
        helper = _status(None, value, lo, hi)
        helper_place = "within" if helper == "within" else helper
        severity_place = _severity_place(_module()._classify_severity(value, lo, hi, None))
        if not (helper_place == verify_place == severity_place):
            mismatches.append((value, lo, hi, helper, stored.flag, severity_place))
        assert _abnormal(helper, False) is bool(stored.is_abnormal), (value, lo, hi, helper, stored.is_abnormal)
    assert mismatches == [], mismatches


# ── HC-VRC-016: the doctor summary never prints a stored None flag ───────────
# Ruling 6651067491: `.get('flag', 'abnormal')` returns the stored None because the
# key exists. A row the range check calls out of range has flag None and is_abnormal
# True after import; the sentence must say "abnormal", not "None".

NONE_PRINTS = ("[None]", "(None)", "flagged as None")


def _no_none(text: str) -> None:
    for bad in NONE_PRINTS:
        assert bad not in text, text


async def _seed_unflagged_abnormal(profile_db) -> None:
    await _seed(profile_db, value=300.0, flag=None, is_abnormal=True,
                collected_at=datetime(2026, 3, 1, 9, 0, 0))


@pytest.mark.asyncio
async def test_hc_vrc_016_key_findings_line_says_abnormal(dbs):
    profile_db, master_db = dbs
    await _seed_unflagged_abnormal(profile_db)
    resp = _call(profile_db, master_db, export_api.router, "/export", "POST",
                 "/export/doctor-summary", json={})
    assert resp.status_code == 200, resp.text
    findings = resp.json()["key_findings"]
    assert findings, resp.text
    for line in findings:
        _no_none(line)
    assert any("(abnormal)" in line for line in findings), findings


@pytest.mark.asyncio
async def test_hc_vrc_016_abnormal_values_section_says_abnormal(dbs):
    profile_db, master_db = dbs
    await _seed_unflagged_abnormal(profile_db)
    resp = _call(profile_db, master_db, export_api.router, "/export", "POST",
                 "/export/doctor-summary", json={})
    assert resp.status_code == 200, resp.text
    summary_id = resp.json()["summary_id"]
    download = _call(profile_db, master_db, export_api.router, "/export", "GET",
                     f"/export/doctor-summary/{summary_id}/download", params={"format": "text"})
    assert download.status_code == 200, download.text
    _no_none(download.text)
    assert "[abnormal]" in download.text, download.text


@pytest.mark.asyncio
async def test_hc_vrc_016_question_context_says_abnormal(dbs):
    profile_db, master_db = dbs
    await _seed_unflagged_abnormal(profile_db)
    resp = _call(profile_db, master_db, export_api.router, "/export", "POST", "/export/questions")
    assert resp.status_code == 200, resp.text
    abnormal = [q for q in resp.json() if q["category"] == "abnormal"]
    assert abnormal, resp.text
    for q in abnormal:
        _no_none(q["context"] + " | " + q["question"])
        assert q["context"].endswith("outside the printed range."), q["context"]
        assert "flagged" not in q["context"]


@pytest.mark.asyncio
async def test_hc_vrc_016_a_printed_flag_still_prints_as_before(dbs):
    profile_db, master_db = dbs
    await _seed(profile_db, value=300.0, flag="H", is_abnormal=True,
                collected_at=datetime(2026, 3, 1, 9, 0, 0))
    resp = _call(profile_db, master_db, export_api.router, "/export", "POST",
                 "/export/doctor-summary", json={})
    assert resp.status_code == 200, resp.text
    assert any("(H)" in line for line in resp.json()["key_findings"]), resp.text
    q = _call(profile_db, master_db, export_api.router, "/export", "POST", "/export/questions")
    ctx = next(x for x in q.json() if x["category"] == "abnormal")["context"]
    assert "300.0" in ctx and ctx.endswith("outside the printed range."), ctx
    assert "flagged as H" not in ctx


# ── HC-VRC-017 to 027: saved template cards and panels are rebuilt on read ───
# L0 ruling 6651183114 (owner answer "Regenerate on read"). A card stores no status,
# so "disagrees with its wording" is read from the saved sentence. Only a card the
# template wrote (model_tier "template", model_id "template-v1") is rebuilt, only when
# the helper says above, below or within and the card claims the opposite; the
# model is never called on a read; every other case is returned as it is, with no write.

DAY = datetime(2026, 3, 1, 9, 0, 0)
VIEWED = datetime(2026, 3, 2, 8, 0, 0)
FALSE_DOSING = "Your LDL is 190 mg/dL [KB:ldl]. You should take 20 mg atorvastatin daily."
READS = [pytest.param("GET", id="GET"), pytest.param("POST", id="POST")]


class _WriteSpy:
    """Counts commits and non-empty flushes on one session (a read must make neither)."""

    def __init__(self, session):
        self._sync = session.sync_session
        self.commits = 0
        self.flushes = 0
        event.listen(self._sync, "after_commit", self._on_commit)
        event.listen(self._sync, "before_flush", self._on_flush)

    def _on_commit(self, _session):
        self.commits += 1

    def _on_flush(self, session, _ctx, _instances):
        if session.new or session.dirty or session.deleted:
            self.flushes += 1

    def reset(self):
        self.commits = self.flushes = 0

    @property
    def writes(self) -> tuple[int, int]:
        return self.commits, self.flushes

    def close(self):
        event.remove(self._sync, "after_commit", self._on_commit)
        event.remove(self._sync, "before_flush", self._on_flush)


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


def _obs_url(obs_id: str, method: str) -> str:
    base = f"/interpretations/observations/{obs_id}"
    return f"{base}/interpretation" if method == "GET" else f"{base}/interpret"


def _read(profile_db, master_db, obs_id: str, method: str):
    resp = _call(profile_db, master_db, interpretations_router, "/interpretations", method,
                 _obs_url(obs_id, method))
    return resp


def _ok(method: str) -> int:
    return 200 if method == "GET" else 201


async def _cards_of(profile_db, obs_id: str) -> list[LabInterpretation]:
    profile_db.expire_all()
    return list((await profile_db.execute(
        select(LabInterpretation).where(LabInterpretation.observation_id == obs_id)
    )).scalars().all())


async def _snapshot(profile_db, obs_id: str) -> tuple:
    (card,) = await _cards_of(profile_db, obs_id)
    return (card.id, card.interpretation_text, card.regeneration_count, card.updated_at,
            card.model_id, card.model_tier)


async def _audit_events(master_db) -> list[str]:
    master_db.expire_all()
    rows = (await master_db.execute(select(AuditLog).order_by(AuditLog.timestamp))).scalars().all()
    return [r.event_type for r in rows]


async def _add_card(profile_db, obs_id: str, text: str, *, model_tier="template",
                    model_id="template-v1", viewed_at=VIEWED, regeneration_count=0) -> str:
    card = LabInterpretation(
        id=str(uuid.uuid4()), profile_id=PROFILE_ID, observation_id=obs_id,
        interpretation_text=text, severity_level="normal", advice_text=None,
        citations_json="[]", context_json=None, model_id=model_id, model_tier=model_tier,
        confidence_score=0.85, requires_physician_review=False, safety_validation_json=None,
        regeneration_count=regeneration_count, viewed_at=viewed_at,
    )
    profile_db.add(card)
    await profile_db.commit()
    return card.id


async def _old_card(profile_db, kw: dict, old: str | None, new: str | None, kb=None, **card_kw):
    """An observation plus a saved card whose `new` sentence was written as `old`
    (the wording main printed before this row). With old=None the card is today's text."""
    obs = _obs(user_verified=card_kw.pop("verified", True), **kw)
    profile_db.add(obs)
    await profile_db.commit()
    text = await _text(obs, kb)
    if old is not None:
        assert new in text, text  # the precondition: the sentence being replaced is the new one
        text = text.replace(new, old)
        assert old in text
    return SimpleNamespace(id=obs.id), await _add_card(profile_db, obs.id, text, **card_kw), text


# ── HC-VRC-017: unflagged 300 against 70-100 whose card says "within" ────────


@pytest.mark.asyncio
@pytest.mark.parametrize("method", READS)
async def test_hc_vrc_017_unflagged_300_card_saying_within_is_rebuilt_once(rdbs, method):
    profile_db, master_db = rdbs
    obs, old_id, old_text = await _old_card(
        profile_db, dict(value=300.0, is_abnormal=False), WITHIN, ABOVE)
    assert WITHIN in old_text
    first = _read(profile_db, master_db, obs.id, method)
    assert first.status_code == _ok(method), first.text
    body = first.json()
    assert ABOVE in body["interpretation_text"], body["interpretation_text"]
    assert WITHIN not in body["interpretation_text"]
    assert body["id"] != old_id
    (row,) = await _cards_of(profile_db, obs.id)
    assert row.id == body["id"]
    assert row.regeneration_count == 1
    assert row.previous_interpretation_id == old_id
    assert row.model_id == "template-v1" and row.model_tier == "template"

    spy = _WriteSpy(profile_db)
    before = await _snapshot(profile_db, obs.id)
    for _ in range(2):
        again = _read(profile_db, master_db, obs.id, method)
        assert again.status_code == _ok(method), again.text
        assert again.json()["id"] == body["id"]
    assert spy.writes == (0, 0), "a second read wrote"
    assert await _snapshot(profile_db, obs.id) == before
    spy.close()


# ── HC-VRC-018: below, and a printed N in range with an old "outside" ────────

REBUILD_CASES = [
    pytest.param(dict(value=40.0, is_abnormal=False), WITHIN, BELOW, id="unflagged-40-within"),
    pytest.param(dict(value=300.0, is_abnormal=False), BELOW, ABOVE, id="unflagged-300-below"),
    pytest.param(dict(value=40.0, is_abnormal=False), ABOVE, BELOW, id="unflagged-40-above"),
    pytest.param(dict(value=85.0, flag="N", is_abnormal=True), OUTSIDE, WITHIN, id="N-85-outside"),
    pytest.param(dict(value=85.0, flag="Normal", is_abnormal=True), OUTSIDE, WITHIN, id="Normal-85-outside"),
    pytest.param(dict(value=85.0, is_abnormal=True), OUTSIDE, WITHIN, id="unflagged-85-outside"),
    pytest.param(dict(value=85.0, is_abnormal=True), ABOVE, WITHIN, id="unflagged-85-above"),
    pytest.param(dict(value=85.0, is_abnormal=True), BELOW, WITHIN, id="unflagged-85-below"),
    pytest.param(dict(value=300.0, flag="High", is_abnormal=True), WITHIN, ABOVE, id="High-300-within"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("method", READS)
@pytest.mark.parametrize("kw,old,new", REBUILD_CASES)
async def test_hc_vrc_018_other_stale_wordings_are_rebuilt(rdbs, method, kw, old, new):
    profile_db, master_db = rdbs
    obs, old_id, _ = await _old_card(profile_db, kw, old, new)
    resp = _read(profile_db, master_db, obs.id, method)
    assert resp.status_code == _ok(method), resp.text
    text = resp.json()["interpretation_text"]
    assert new in text, text
    assert old not in text, text
    assert resp.json()["id"] != old_id
    assert len(await _cards_of(profile_db, obs.id)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("method", READS)
@pytest.mark.parametrize("place,old_place", [("above", "within"), ("below", "within"),
                                              ("within", "above"), ("within", "below")])
async def test_hc_vrc_018_knowledge_base_form_is_rebuilt(rdbs, method, place, old_place):
    profile_db, master_db = rdbs
    data = next(d for d in BIOMARKER_DATA if d["analyte_canonical"] == "ldl_cholesterol")
    master_db.add(BiomarkerKnowledge(id="kb-ldl_cholesterol", **data))
    await master_db.commit()
    kb = _kb_from(data)
    value = {**PLACE_VALUE, "within": 85.0}[place]
    obs, old_id, old_text = await _old_card(
        profile_db, dict(value=value, analyte_canonical="ldl_cholesterol", is_abnormal=place != "within"),
        _kb_text(kb, old_place), _kb_text(kb, place), kb=kb)
    assert "[KB:kb-ldl_cholesterol]" in old_text
    resp = _read(profile_db, master_db, obs.id, method)
    assert resp.status_code == _ok(method), resp.text
    text = resp.json()["interpretation_text"]
    assert _kb_text(kb, place) in text, text
    assert _kb_text(kb, old_place) not in text, text
    assert resp.json()["id"] != old_id


@pytest.mark.asyncio
@pytest.mark.parametrize("method", READS)
@pytest.mark.parametrize("place,old_place", [("above", "within"), ("below", "within"),
                                              ("within", "above"), ("within", "below")])
async def test_hc_vrc_018_knowledge_base_form_is_rebuilt_when_the_kb_row_has_another_id(
    rdbs, method, place, old_place
):
    # Every install seeds its own KB row ids (seed_knowledge_base.py uses generate_uuid), so a
    # vault restored onto a re-seeded master DB holds cards whose [KB:<id>] marker names a row
    # that no longer exists. The words are the same; only the id differs.
    profile_db, master_db = rdbs
    data = next(d for d in BIOMARKER_DATA if d["analyte_canonical"] == "ldl_cholesterol")
    master_db.add(BiomarkerKnowledge(id="kb-from-another-seed", **data))
    await master_db.commit()
    kb = _kb_from(data)  # the id the card was written with: kb-ldl_cholesterol
    value = {**PLACE_VALUE, "within": 85.0}[place]
    obs, old_id, old_text = await _old_card(
        profile_db, dict(value=value, analyte_canonical="ldl_cholesterol", is_abnormal=place != "within"),
        _kb_text(kb, old_place), _kb_text(kb, place), kb=kb)
    assert "[KB:kb-ldl_cholesterol]" in old_text and "kb-from-another-seed" not in old_text
    resp = _read(profile_db, master_db, obs.id, method)
    assert resp.status_code == _ok(method), resp.text
    text = resp.json()["interpretation_text"]
    field = {"above": "high", "below": "low", "within": "normal"}
    assert data[f"{field[place]}_interpretation"] in text, text
    assert data[f"{field[old_place]}_interpretation"] not in text, text
    assert "[KB:kb-from-another-seed]" in text
    assert resp.json()["id"] != old_id
    assert len(await _cards_of(profile_db, obs.id)) == 1


# ── HC-VRC-019: a card in agreement is returned untouched ────────────────────

AGREE_CASES = [
    pytest.param(dict(value=300.0, is_abnormal=True), id="above"),
    pytest.param(dict(value=40.0, is_abnormal=True), id="below"),
    pytest.param(dict(value=85.0, is_abnormal=False), id="within"),
    pytest.param(dict(value=300.0, flag="H", is_abnormal=True), id="H-300"),
    pytest.param(dict(value=85.0, flag="N", is_abnormal=False), id="N-85"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("method", READS)
@pytest.mark.parametrize("kw", AGREE_CASES)
async def test_hc_vrc_019_card_in_agreement_is_returned_untouched_with_no_write(rdbs, method, kw):
    profile_db, master_db = rdbs
    obs, card_id, text = await _old_card(profile_db, kw, None, None, regeneration_count=3)
    before = await _snapshot(profile_db, obs.id)
    spy = _WriteSpy(profile_db)
    resp = _read(profile_db, master_db, obs.id, method)
    assert resp.status_code == _ok(method), resp.text
    assert resp.json()["id"] == card_id
    assert resp.json()["interpretation_text"] == text
    assert spy.writes == (0, 0), "a card in agreement was written"
    spy.close()
    assert await _snapshot(profile_db, obs.id) == before


@pytest.mark.asyncio
async def test_hc_vrc_019_get_marks_an_unviewed_card_viewed_and_nothing_else(rdbs):
    profile_db, master_db = rdbs
    obs, card_id, text = await _old_card(
        profile_db, dict(value=300.0, is_abnormal=True), None, None, viewed_at=None)
    resp = _read(profile_db, master_db, obs.id, "GET")
    assert resp.status_code == 200, resp.text
    (row,) = await _cards_of(profile_db, obs.id)
    assert (row.id, row.interpretation_text, row.regeneration_count) == (card_id, text, 0)
    assert row.viewed_at is not None


# ── HC-VRC-020: a model-written card is left alone ───────────────────────────

MODEL_CARDS = [
    pytest.param(dict(model_tier="high", model_id="biomistral-7b-q4"), id="high-tier"),
    pytest.param(dict(model_tier="template", model_id="other-template-v2"), id="template-tier-other-id"),
    pytest.param(dict(model_tier="mid", model_id="template-v1"), id="other-tier-template-id"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("method", READS)
@pytest.mark.parametrize("card_kw", MODEL_CARDS)
async def test_hc_vrc_020_model_written_card_with_a_false_sentence_is_unchanged(rdbs, method, card_kw):
    profile_db, master_db = rdbs
    obs, card_id, text = await _old_card(
        profile_db, dict(value=300.0, is_abnormal=False), WITHIN, ABOVE, **card_kw)
    before = await _snapshot(profile_db, obs.id)
    spy = _WriteSpy(profile_db)
    resp = _read(profile_db, master_db, obs.id, method)
    assert resp.status_code == _ok(method), resp.text
    assert resp.json()["id"] == card_id
    assert resp.json()["interpretation_text"] == text
    assert WITHIN in resp.json()["interpretation_text"]
    assert spy.writes == (0, 0)
    spy.close()
    assert await _snapshot(profile_db, obs.id) == before
    # rdbs asserts at teardown that get_model_for_inference and run_inference never ran
    assert ModelSelector.run_inference.await_count == 0
    assert ModelSelector.get_model_for_inference.await_count == 0


# ── HC-VRC-021/022: panels ───────────────────────────────────────────────────

CMP_GLUCOSE = dict(analyte_canonical="glucose", analyte_raw="Glucose", unit="mg/dL",
                   ref_low=LO, ref_high=HI)


def _panel_url() -> str:
    return "/interpretations/panels/cmp/interpret"


def _read_panel(profile_db, master_db, *, force: bool = False):
    params = {"collected_at": DAY.isoformat()}
    if force:
        params["force_regenerate"] = "true"
    return _call(profile_db, master_db, interpretations_router, "/interpretations", "POST",
                 _panel_url(), params=params)


async def _panels(profile_db) -> list[PanelInterpretation]:
    profile_db.expire_all()
    return list((await profile_db.execute(select(PanelInterpretation))).scalars().all())


async def _old_panel(profile_db, rows: list[dict], shown_abnormal: list[bool], *,
                     model_id="template-v1", old_card: tuple[str, str] | None = None):
    """Observations, their saved cards, and a saved cmp panel whose summary was written from
    `shown_abnormal` (what main stored: is_abnormal as import saved it) and each member's own
    severity from the real classifier, as main's panel writer read it from the saved card. With
    `old_card` = (old, new), the first member's card says `old` where today's text says `new`."""
    obs_list, summaries = [], []
    for kw in rows:
        obs = _obs(user_verified=True, collected_at=DAY, **kw)
        profile_db.add(obs)
        obs_list.append(obs)
    await profile_db.commit()
    texts = [await _text(o) for o in obs_list]
    if old_card is not None:
        assert old_card[1] in texts[0], texts[0]
        texts[0] = texts[0].replace(old_card[1], old_card[0])
    severities = [_module()._classify_severity(o.value, o.ref_low, o.ref_high, None) for o in obs_list]
    obs_list = [SimpleNamespace(id=o.id, analyte_canonical=o.analyte_canonical, value=o.value, unit=o.unit)
                for o in obs_list]
    for obs, shown, text, severity in zip(obs_list, shown_abnormal, texts, severities):
        await _add_card(profile_db, obs.id, text)
        summaries.append({"analyte": obs.analyte_canonical, "value": obs.value, "unit": obs.unit,
                          "severity": severity, "is_abnormal": shown})
    summary_text = _module()._generate_panel_summary("cmp", "Comprehensive Metabolic Panel", summaries)
    panel = PanelInterpretation(
        id=str(uuid.uuid4()), profile_id=PROFILE_ID, panel_name="cmp", collected_at=DAY,
        observation_ids_json=json.dumps([o.id for o in obs_list]),
        summary_text=summary_text, overall_status="normal", relationship_insights_json=None,
        advice_text=None, citations_json="[]", model_id=model_id, confidence_score=0.8,
        requires_physician_review=False,
    )
    profile_db.add(panel)
    await profile_db.commit()
    return obs_list, panel.id, summary_text


SODIUM_ROW = dict(analyte_canonical="sodium", analyte_raw="Sodium", value=140.0, unit="mmol/L",
                  ref_low=135.0, ref_high=145.0, is_abnormal=False)


@pytest.mark.asyncio
async def test_hc_vrc_021_panel_with_an_old_normal_line_is_rebuilt_once(rdbs):
    profile_db, master_db = rdbs
    obs_list, old_id, old_summary = await _old_panel(
        profile_db, [dict(value=300.0, is_abnormal=False), SODIUM_ROW], [False, False],
        old_card=(WITHIN, ABOVE))
    assert "2 of 2 values are within normal range." in old_summary
    assert "Items requiring attention" not in old_summary

    first = _read_panel(profile_db, master_db)
    assert first.status_code == 201, first.text
    body = first.json()
    assert "GLUCOSE: 300.0 mg/dL (above normal)" in body["summary_text"], body["summary_text"]
    assert "1 of 2 values are within normal range." in body["summary_text"]
    assert body["overall_status"] == "borderline"
    assert body["id"] != old_id
    (row,) = await _panels(profile_db)  # exactly one row: the old one is gone
    assert row.id == body["id"]
    glucose_card = (await _cards_of(profile_db, obs_list[0].id))
    assert [c.regeneration_count for c in glucose_card] == [1]
    assert ABOVE in glucose_card[0].interpretation_text

    spy = _WriteSpy(profile_db)
    second = _read_panel(profile_db, master_db)
    assert second.status_code == 201, second.text
    assert second.json()["id"] == body["id"]
    assert spy.writes == (0, 0), "a second panel read wrote"
    spy.close()
    assert len(await _panels(profile_db)) == 1


@pytest.mark.asyncio
async def test_hc_vrc_021_second_read_after_a_panel_rebuild_is_not_a_500(rdbs):
    # panel_interpretations has no unique constraint: a rebuild that leaves the old row makes
    # the next cached lookup raise MultipleResultsFound (measured at Task 0, 2026-11-04).
    profile_db, master_db = rdbs
    await _old_panel(profile_db, [dict(value=300.0, is_abnormal=False), SODIUM_ROW], [False, False],
                     old_card=(WITHIN, ABOVE))
    for _ in range(2):
        resp = _read_panel(profile_db, master_db)
        assert resp.status_code == 201, resp.text


@pytest.mark.asyncio
async def test_hc_vrc_021_panel_with_a_false_attention_line_is_rebuilt(rdbs):
    # printed N at 85 whose stored True put it under "Items requiring attention"
    profile_db, master_db = rdbs
    _, old_id, old_summary = await _old_panel(
        profile_db, [dict(value=85.0, flag="N", is_abnormal=True), SODIUM_ROW], [True, False])
    assert "GLUCOSE: 85.0 mg/dL" in old_summary
    resp = _read_panel(profile_db, master_db)
    assert resp.status_code == 201, resp.text
    assert "Items requiring attention" not in resp.json()["summary_text"]
    assert "2 of 2 values are within normal range." in resp.json()["summary_text"]
    assert resp.json()["id"] != old_id
    assert len(await _panels(profile_db)) == 1


@pytest.mark.asyncio
async def test_hc_vrc_022_panel_in_agreement_is_returned_untouched(rdbs):
    profile_db, master_db = rdbs
    _, old_id, old_summary = await _old_panel(
        profile_db, [dict(value=300.0, is_abnormal=True), SODIUM_ROW], [True, False])
    spy = _WriteSpy(profile_db)
    for _ in range(2):
        resp = _read_panel(profile_db, master_db)
        assert resp.status_code == 201, resp.text
        assert resp.json()["id"] == old_id
        assert resp.json()["summary_text"] == old_summary
    assert spy.writes == (0, 0)
    spy.close()


@pytest.mark.asyncio
async def test_hc_vrc_022_panel_with_another_model_id_is_unchanged(rdbs):
    profile_db, master_db = rdbs
    _, old_id, old_summary = await _old_panel(
        profile_db, [dict(value=300.0, is_abnormal=False), SODIUM_ROW], [False, False],
        model_id="biomistral-7b-q4", old_card=(WITHIN, ABOVE))
    spy = _WriteSpy(profile_db)
    resp = _read_panel(profile_db, master_db)
    assert resp.status_code == 201, resp.text
    assert resp.json()["id"] == old_id
    assert resp.json()["summary_text"] == old_summary
    assert spy.writes == (0, 0)
    spy.close()


@pytest.mark.asyncio
async def test_hc_vrc_022_a_member_without_a_saved_card_never_causes_a_rewrite(rdbs):
    # The glucose card was withheld when the panel was written: no card, no line, and
    # the read must not call that stale.
    profile_db, master_db = rdbs
    obs_list, old_id, old_summary = await _old_panel(
        profile_db, [dict(value=300.0, is_abnormal=False), SODIUM_ROW], [False, False])
    for card in await _cards_of(profile_db, obs_list[0].id):
        await profile_db.delete(card)
    await profile_db.commit()
    spy = _WriteSpy(profile_db)
    resp = _read_panel(profile_db, master_db)
    assert resp.status_code == 201, resp.text
    assert resp.json()["id"] == old_id
    assert spy.writes == (0, 0)
    spy.close()


# ── HC-VRC-023: disagreements and uncomparable rows are never rebuilt ────────

NEVER = [
    pytest.param(dict(value=None, value_text="pending", flag="N", is_abnormal=True),
                 OUTSIDE, WITHIN, id="N-no-value-old-outside"),
    pytest.param(dict(value=300.0, ref_low=None, ref_high=None, ref_range_text="70-100 mg/dL",
                      is_abnormal=False), None, None, id="text-only-range-keep"),
    pytest.param(dict(value=300.0, ref_low=None, ref_high=None, is_abnormal=False),
                 WITHIN, NO_RANGE, id="no-range-old-within"),
    pytest.param(dict(value=300.0, ref_low=None, ref_high=None, ref_range_text="  ", is_abnormal=False),
                 None, None, id="blank-range-text"),
    pytest.param(dict(value=300.0, flag="High", is_abnormal=True), OUTSIDE, ABOVE, id="outside-on-printed-High-300"),
    pytest.param(dict(value=40.0, flag="Low", is_abnormal=True), OUTSIDE, BELOW, id="outside-on-printed-Low-40"),
    pytest.param(dict(value=85.0, flag="A", is_abnormal=True), None, None, id="other-flag-keep"),
]


# KEPT-FLAG-DISAGREES (L0 ruling R3): a disagreement now has wording, so a saved template card
# holding today's old sentence for one is rebuilt to the flag-range sentence. These three left NEVER.
REBUILT_DISAGREEMENTS = [
    pytest.param(dict(value=300.0, flag="N", is_abnormal=True), OUTSIDE, id="N-at-300-disagrees"),
    pytest.param(dict(value=85.0, flag="H", is_abnormal=True), ABOVE, id="H-at-85-disagrees"),
    pytest.param(dict(value=85.0, flag="L", is_abnormal=True), ABOVE, id="L-at-85-card-says-above"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("method", READS)
@pytest.mark.parametrize("kw,old", REBUILT_DISAGREEMENTS)
async def test_hc_vrc_023_disagreements_are_rebuilt_to_the_flag_range_sentence(rdbs, method, kw, old):
    profile_db, master_db = rdbs
    obs, card_id, _ = await _old_card(profile_db, kw, old, FLAG_RANGE_DISAGREE)
    resp = _read(profile_db, master_db, obs.id, method)
    assert resp.status_code == _ok(method), resp.text
    text = resp.json()["interpretation_text"]
    assert FLAG_RANGE_DISAGREE in text, text
    assert old not in text, text
    assert resp.json()["id"] != card_id
    assert len(await _cards_of(profile_db, obs.id)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("method", READS)
@pytest.mark.parametrize("kw,old,new", NEVER)
async def test_hc_vrc_023_cases_the_helper_does_not_decide_are_not_rebuilt(rdbs, method, kw, old, new):
    profile_db, master_db = rdbs
    obs, card_id, text = await _old_card(profile_db, kw, old, new)
    before = await _snapshot(profile_db, obs.id)
    spy = _WriteSpy(profile_db)
    resp = _read(profile_db, master_db, obs.id, method)
    assert resp.status_code == _ok(method), resp.text
    assert resp.json()["id"] == card_id
    assert resp.json()["interpretation_text"] == text
    assert spy.writes == (0, 0)
    spy.close()
    assert await _snapshot(profile_db, obs.id) == before


@pytest.mark.asyncio
async def test_hc_vrc_023_a_card_with_no_readable_claim_is_not_stale(rdbs):
    profile_db, master_db = rdbs
    obs = _obs(user_verified=True, value=300.0, is_abnormal=False)
    profile_db.add(obs)
    await profile_db.commit()
    card_id = await _add_card(profile_db, obs.id, "Your GLUCOSE result is 300.0 mg/dL. Ask your doctor.")
    for method in ("GET", "POST"):
        resp = _read(profile_db, master_db, obs.id, method)
        assert resp.status_code == _ok(method), resp.text
        assert resp.json()["id"] == card_id


@pytest.mark.asyncio
async def test_hc_vrc_023_a_knowledge_base_card_whose_text_has_changed_is_not_stale(rdbs):
    profile_db, master_db = rdbs
    data = next(d for d in BIOMARKER_DATA if d["analyte_canonical"] == "ldl_cholesterol")
    kb = _kb_from(data)
    obs, card_id, text = await _old_card(
        profile_db, dict(value=300.0, analyte_canonical="ldl_cholesterol", is_abnormal=False),
        _kb_text(kb, "within"), _kb_text(kb, "above"), kb=kb)
    # the master DB holds a revised KB (another id and other words): the old claim cannot be read
    master_db.add(BiomarkerKnowledge(id="kb-revised", **{
        **data, "normal_interpretation": "Revised words.", "high_interpretation": "Other high words.",
        "low_interpretation": "Other low words."}))
    await master_db.commit()
    resp = _read(profile_db, master_db, obs.id, "POST")
    assert resp.status_code == 201, resp.text
    assert resp.json()["id"] == card_id
    assert resp.json()["interpretation_text"] == text


# ── HC-VRC-024: a withheld rebuild keeps the old row and serves none of its text ──


def _force_withhold():
    return patch.object(InterpretModule, "_generate_interpretation",
                        AsyncMock(return_value=(FALSE_DOSING, None)))


@pytest.mark.asyncio
@pytest.mark.parametrize("method", READS)
async def test_hc_vrc_024_withheld_rebuild_keeps_the_old_row_and_answers_500(rdbs, method):
    profile_db, master_db = rdbs
    obs, old_id, old_text = await _old_card(
        profile_db, dict(value=300.0, is_abnormal=False), WITHIN, ABOVE)
    before = await _snapshot(profile_db, obs.id)
    with _force_withhold():
        resp = _read(profile_db, master_db, obs.id, method)
    assert resp.status_code == 500, resp.text
    assert resp.json()["detail"] == ESCALATE_TEMPLATE
    assert WITHIN not in resp.text, "the old false sentence was served"
    assert "normal reference range" not in resp.text
    assert await _snapshot(profile_db, obs.id) == before
    # The rebuild is irreversible, so it opens with a started row; the withheld row closes it.
    assert await _audit_events(master_db) == ["interpretation.generate", "interpretation.withheld"]
    assert [s for _, s in await _audit_pairs(master_db)] == ["started", "completed"]


# ── HC-VRC-025: strict safety mode refuses first ─────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("method", READS)
async def test_hc_vrc_025_strict_mode_refuses_an_unverified_row_before_any_rebuild(rdbs, method):
    profile_db, master_db = rdbs
    profile_db.add(UserModelSettings(id=str(uuid.uuid4()), profile_id=PROFILE_ID, strict_safety_mode=True))
    await profile_db.commit()
    obs, _, _ = await _old_card(
        profile_db, dict(value=300.0, is_abnormal=False), WITHIN, ABOVE, verified=False, viewed_at=None)
    before = await _snapshot(profile_db, obs.id)
    spy = _WriteSpy(profile_db)
    resp = _read(profile_db, master_db, obs.id, method)
    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"]["code"] == "observation_unverified"
    assert spy.writes == (0, 0)
    spy.close()
    assert await _snapshot(profile_db, obs.id) == before
    assert await _audit_events(master_db) == ["interpretation.unverified_refused"]


# ── HC-VRC-026: the audit rows of a rebuilding read ──────────────────────────


def _no_phi(rows_blob: str) -> None:
    for leaked in ("glucose", "mg/dL", "above the reference", "within the normal", "300.0", "Your "):
        assert leaked not in rows_blob, leaked


async def _audit_blob(master_db) -> str:
    master_db.expire_all()
    rows = (await master_db.execute(select(AuditLog))).scalars().all()
    return " ".join(
        str(getattr(r, c.name)) for r in rows for c in r.__table__.columns if c.name != "timestamp"
    )


async def _audit_pairs(master_db) -> list[tuple[str, str | None]]:
    """(event_type, intent) per audit row, in order. The intent is the `status` stored on the row."""
    master_db.expire_all()
    rows = (await master_db.execute(
        select(AuditLog).order_by(AuditLog.timestamp, AuditLog.id))).scalars().all()
    return [(r.event_type, (json.loads(r.details_json) if r.details_json else {}).get("status"))
            for r in rows]


@pytest.mark.asyncio
@pytest.mark.parametrize("method,want", [
    ("GET", [("interpretation.generate", "started"), ("interpretation.generate", "completed"),
             ("interpretation.view", None)]),
    ("POST", [("interpretation.generate", "started"), ("interpretation.generate", "completed")]),
])
async def test_hc_vrc_026_a_rebuilding_read_writes_the_started_and_completed_pair(
    rdbs, method, want
):
    # AO-DESIGN "D: two-row on irreversible": the rebuild deletes the saved card, so it is
    # bracketed like an explicit regenerate. The GET keeps its view row after the pair.
    profile_db, master_db = rdbs
    obs, _, _ = await _old_card(profile_db, dict(value=300.0, is_abnormal=False), WITHIN, ABOVE)
    resp = _read(profile_db, master_db, obs.id, method)
    assert resp.status_code == _ok(method), resp.text
    assert ABOVE in resp.json()["interpretation_text"]  # it did rebuild
    assert await _audit_pairs(master_db) == want
    master_db.expire_all()
    started = (await master_db.execute(
        select(AuditLog).where(AuditLog.event_type == "interpretation.generate")
        .order_by(AuditLog.timestamp, AuditLog.id))).scalars().first()
    assert (started.entity_type, started.entity_id) == ("observation", obs.id)
    _no_phi(await _audit_blob(master_db))


PANEL_EVENT = "interpretation.panel_generate"


def _det(row: AuditLog) -> dict:
    return json.loads(row.details_json) if row.details_json else {}


async def _rows_of(master_db, event_type: str) -> list[AuditLog]:
    """The audit rows of one event type, in the order they were written."""
    master_db.expire_all()
    return list((await master_db.execute(
        select(AuditLog).where(AuditLog.event_type == event_type)
        .order_by(AuditLog.timestamp, AuditLog.id))).scalars().all())


@pytest.mark.asyncio
async def test_hc_vrc_026_a_rebuilding_panel_read_writes_the_started_and_completed_pair(rdbs):
    # L0 ruling 6656962109 items 1 and 2: a panel read that replaces a saved row or a member
    # card is bracketed (A2), and every replaced card's id is in both rows. Ids only.
    profile_db, master_db = rdbs
    obs_list, old_id, _ = await _old_panel(
        profile_db, [dict(value=300.0, is_abnormal=False), SODIUM_ROW], [False, False],
        old_card=(WITHIN, ABOVE))
    glucose_id = obs_list[0].id
    resp = _read_panel(profile_db, master_db)
    assert resp.status_code == 201, resp.text
    assert "GLUCOSE: 300.0" in resp.json()["summary_text"]
    assert await _audit_pairs(master_db) == [(PANEL_EVENT, "started"), (PANEL_EVENT, "completed")]
    started, completed = await _rows_of(master_db, PANEL_EVENT)
    assert (started.entity_type, started.entity_id) == ("panel_interpretation", old_id)
    assert (completed.entity_type, completed.entity_id) == ("panel_interpretation", resp.json()["id"])
    for row in (started, completed):  # read from details_json: core.audit drops unknown keys
        assert _det(row)["observation_ids"] == [glucose_id], _det(row)
        assert _det(row)["count"] == 1
    assert _det(completed)["skipped_count"] == 0
    _no_phi(await _audit_blob(master_db))


# ── HC-VRC-027: no rewrite loop ──────────────────────────────────────────────

LOOP_CASES = [
    ("above", dict(value=300.0)), ("below", dict(value=40.0)), ("within", dict(value=85.0)),
    ("stored-true-300", dict(value=300.0, is_abnormal=True)),
    ("H-300", dict(value=300.0, flag="H", is_abnormal=True)),
    ("L-40", dict(value=40.0, flag="L", is_abnormal=True)),
    ("High-300", dict(value=300.0, flag="High", is_abnormal=True)),
    ("N-85", dict(value=85.0, flag="N", is_abnormal=True)),
    ("N-300-disagrees", dict(value=300.0, flag="N", is_abnormal=True)),
    ("H-85-disagrees", dict(value=85.0, flag="H", is_abnormal=True)),
    ("A-85-keep", dict(value=85.0, flag="A", is_abnormal=True)),
    ("no-range", dict(value=300.0, ref_low=None, ref_high=None)),
    ("text-only-range", dict(value=300.0, ref_low=None, ref_high=None, ref_range_text="70-100")),
    ("blank-range-text", dict(value=300.0, ref_low=None, ref_high=None, ref_range_text=" ")),
    ("high-only", dict(value=300.0, ref_low=None)),
    ("zero-high", dict(value=5.0, ref_low=None, ref_high=0.0)),
    ("no-value", dict(value=None, value_text="pending")),
]
LOOP_KBS = [pytest.param(None, id="no-kb")] + [pytest.param(d, id=d["analyte_canonical"]) for d in BIOMARKER_DATA]


@pytest.mark.asyncio
@pytest.mark.parametrize("data", LOOP_KBS)
async def test_hc_vrc_027_a_fresh_card_is_never_stale(rdbs, data):
    profile_db, master_db = rdbs
    analyte = "glucose" if data is None else data["analyte_canonical"]
    if data is not None:
        master_db.add(BiomarkerKnowledge(id=f"kb-{analyte}", **data))
        await master_db.commit()
    ids = []
    for _, kw in LOOP_CASES:
        obs = _obs(user_verified=True, analyte_canonical=analyte, **kw)
        profile_db.add(obs)
        ids.append(obs.id)
    await profile_db.commit()

    created = {}
    with route_client(interpretations_router, "/interpretations", profile_id=PROFILE_ID,
                      master_db=master_db) as client:

        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        for obs_id in ids:
            resp = client.post(_obs_url(obs_id, "POST"))
            assert resp.status_code == 201, resp.text
            created[obs_id] = resp.json()["id"]
            assert client.get(_obs_url(obs_id, "GET")).status_code == 200  # marks viewed
        spy = _WriteSpy(profile_db)
        for obs_id in ids:
            for method in ("POST", "GET", "POST", "GET"):
                resp = client.request(method, _obs_url(obs_id, method))
                assert resp.status_code == _ok(method), resp.text
                assert resp.json()["id"] == created[obs_id], (analyte, obs_id, method)
        assert spy.writes == (0, 0), (analyte, "a read wrote")
        spy.close()


PANEL_LOOP = [
    pytest.param([dict(value=300.0)], id="above"),
    pytest.param([dict(value=85.0, flag="N", is_abnormal=True)], id="N-in-range-stored-true"),
    pytest.param([dict(value=300.0, flag="N", is_abnormal=True)], id="N-300-disagrees"),
    pytest.param([dict(value=300.0, ref_low=None, ref_high=None)], id="no-range"),
    pytest.param([dict(value=300.0, flag="A", is_abnormal=True)], id="other-flag"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("glucose_rows", PANEL_LOOP)
async def test_hc_vrc_027_a_fresh_panel_is_never_stale(rdbs, glucose_rows):
    profile_db, master_db = rdbs
    for kw in glucose_rows + [SODIUM_ROW]:
        profile_db.add(_obs(user_verified=True, collected_at=DAY, **{**CMP_GLUCOSE, **kw}))
    await profile_db.commit()
    first = _read_panel(profile_db, master_db)
    assert first.status_code == 201, first.text
    spy = _WriteSpy(profile_db)
    for _ in range(3):
        again = _read_panel(profile_db, master_db)
        assert again.status_code == 201, again.text
        assert again.json()["id"] == first.json()["id"]
    assert spy.writes == (0, 0)
    spy.close()
    assert len(await _panels(profile_db)) == 1


@pytest.mark.asyncio
async def test_hc_vrc_027_a_panel_with_a_withheld_member_is_never_stale(rdbs):
    profile_db, master_db = rdbs
    profile_db.add(_obs(user_verified=True, collected_at=DAY, value=300.0, is_abnormal=False))
    profile_db.add(_obs(user_verified=True, collected_at=DAY, **SODIUM_ROW))
    await profile_db.commit()
    real = InterpretModule._generate_interpretation

    async def _withhold_glucose(self, context, master_db):
        if context.observation.analyte_canonical == "glucose":
            return FALSE_DOSING, None
        return await real(self, context, master_db)

    with patch.object(InterpretModule, "_generate_interpretation", _withhold_glucose):
        first = _read_panel(profile_db, master_db)
        assert first.status_code == 201, first.text
        assert "GLUCOSE" not in first.json()["summary_text"]  # the withheld member is not in it
        spy = _WriteSpy(profile_db)
        for _ in range(3):
            again = _read_panel(profile_db, master_db)
            assert again.status_code == 201, again.text
            assert again.json()["id"] == first.json()["id"]
        assert spy.writes == (0, 0)
        spy.close()
    assert len(await _panels(profile_db)) == 1


# ── HC-VRC-028: the other POST routes reach the rebuild; GET keeps its ownership check ──


def _stub_rag():
    """A RAG module that answers without a model (the grounded route calls it after the card)."""
    verification = SimpleNamespace(
        verification_enabled=False, total_claims=0, verified_claims=0, failed_claims=0,
        faithfulness_score=0.0, authority_score=0.0, verification_summary="",
        claims_with_issues=[],
    )
    answer = SimpleNamespace(
        segments=[], verification=verification, prohibited_advice=False, is_valid=True,
        insufficient_context=False, insufficient_reasons=[], validation_errors=[],
    )
    return SimpleNamespace(query=AsyncMock(return_value=answer))


@pytest.mark.asyncio
async def test_hc_vrc_028_interpret_grounded_rebuilds_a_stale_card_once(rdbs):
    # the route LabInterpreter's Generate button calls
    profile_db, master_db = rdbs
    obs, old_id, _ = await _old_card(profile_db, dict(value=300.0, is_abnormal=False), WITHIN, ABOVE)
    url = f"/interpretations/observations/{obs.id}/interpret-grounded"
    with patch.object(interp_api, "get_rag_module", return_value=_stub_rag()):
        first = _call(profile_db, master_db, interpretations_router, "/interpretations", "POST", url)
        assert first.status_code == 201, first.text
        card = first.json()["interpretation"]
        assert ABOVE in card["interpretation_text"] and WITHIN not in card["interpretation_text"]
        assert card["id"] != old_id
        (row,) = await _cards_of(profile_db, obs.id)
        assert row.id == card["id"] and row.regeneration_count == 1
        spy = _WriteSpy(profile_db)
        again = _call(profile_db, master_db, interpretations_router, "/interpretations", "POST", url)
        assert again.status_code == 201, again.text
        assert again.json()["interpretation"]["id"] == card["id"]
        assert spy.writes == (0, 0), "a second grounded read wrote"
        spy.close()


@pytest.mark.asyncio
async def test_hc_vrc_028_batch_rebuilds_a_stale_card_once(rdbs):
    profile_db, master_db = rdbs
    obs, old_id, _ = await _old_card(profile_db, dict(value=300.0, is_abnormal=False), WITHIN, ABOVE)
    body = {"observation_ids": [obs.id]}
    first = _call(profile_db, master_db, interpretations_router, "/interpretations", "POST",
                  "/interpretations/batch", json=body)
    assert first.status_code == 200, first.text
    assert first.json()["successful"] == [obs.id] and first.json()["failed"] == []
    (row,) = await _cards_of(profile_db, obs.id)
    assert row.id != old_id
    assert ABOVE in row.interpretation_text and WITHIN not in row.interpretation_text
    assert row.regeneration_count == 1
    spy = _WriteSpy(profile_db)
    again = _call(profile_db, master_db, interpretations_router, "/interpretations", "POST",
                  "/interpretations/batch", json=body)
    assert again.status_code == 200, again.text
    assert again.json()["successful"] == [obs.id]
    assert spy.writes == (0, 0), "a second batch read wrote"
    spy.close()
    assert (await _cards_of(profile_db, obs.id))[0].id == row.id


@pytest.mark.asyncio
@pytest.mark.parametrize("method", READS)
async def test_hc_vrc_028_a_stale_card_on_another_profiles_row_is_403_and_untouched(rdbs, method):
    # The ownership check now guards a write: it must run before any rebuild.
    profile_db, master_db = rdbs
    obs, _, _ = await _old_card(
        profile_db, dict(value=300.0, is_abnormal=False, profile_id="another-profile"), WITHIN, ABOVE)
    before = await _snapshot(profile_db, obs.id)
    spy = _WriteSpy(profile_db)
    resp = _read(profile_db, master_db, obs.id, method)
    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == "Access denied to this observation"
    assert spy.writes == (0, 0)
    spy.close()
    assert await _snapshot(profile_db, obs.id) == before
    assert await _audit_events(master_db) == []


# ── HC-VRC-029: the A2 pair on every route that can rebuild ──────────────────
# L0 ruling 6654607932 item 1 (AO-DESIGN "D: two-row on irreversible"). A rebuild deletes
# the saved card, so it is bracketed like an explicit regenerate: a `started` row is
# committed first and a failed audit write stops the rebuild; `completed` follows it.
# Only a rebuild writes the pair: a card in agreement, a model-written card or a card the
# helper does not decide writes none.

ROUTES = [pytest.param(r, id=r) for r in ("GET", "POST", "grounded", "batch")]
ROUTE_EVENT = {"GET": "interpretation.generate", "POST": "interpretation.generate",
               "grounded": "interpretation.grounded", "batch": "interpretation.batch_generate"}
ROUTE_OK = {"GET": 200, "POST": 201, "grounded": 201, "batch": 200}


def _fire(route: str, profile_db, master_db, obs_id: str, *, soft: bool = False,
          force: bool = False):
    """One read through `route`. soft=True answers an unhandled server error as a 500
    response instead of raising it into the test (route_client's raise_server_exceptions).
    The "panel" route reads the cmp panel of DAY and ignores obs_id. force=True is
    force_regenerate on the panel and batch routes."""
    base = f"/interpretations/observations/{obs_id}"
    method, url, kwargs = {
        "GET": ("GET", f"{base}/interpretation", {}),
        "POST": ("POST", f"{base}/interpret", {}),
        "grounded": ("POST", f"{base}/interpret-grounded", {}),
        "batch": ("POST", "/interpretations/batch",
                  {"json": {"observation_ids": [obs_id], "force_regenerate": force}}),
        "panel": ("POST", _panel_url(),
                  {"params": {"collected_at": DAY.isoformat(),
                              **({"force_regenerate": "true"} if force else {})}}),
    }[route]
    with patch.object(interp_api, "get_rag_module", return_value=_stub_rag()), route_client(
        interpretations_router, "/interpretations", profile_id=PROFILE_ID, master_db=master_db,
        raise_server_exceptions=not soft,
    ) as client:

        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        return client.request(method, url, **kwargs)


def _audit_fails_on(status: str):
    """Make the audit_intent commit of one half of the pair (`started` or `completed`) raise."""
    real = interp_api.audit_intent

    async def _wrapped(db, st, log_fn, **kw):
        if st == status:
            raise RuntimeError("audit down")
        return await real(db, st, log_fn, **kw)

    return patch.object(interp_api, "audit_intent", _wrapped)


@contextmanager
def _ordered(profile_db):
    """Yield a log of 'started', 'completed' (after the audit commit returns) and 'delete'
    (a profile flush that removes a row), in the order they happened."""
    log: list[str] = []
    real = interp_api.audit_intent

    async def _wrapped(db, st, log_fn, **kw):
        row = await real(db, st, log_fn, **kw)
        log.append(st)
        return row

    def _on_flush(session, _ctx, _instances):
        if session.deleted:
            log.append("delete")

    sync = profile_db.sync_session
    event.listen(sync, "before_flush", _on_flush)
    try:
        with patch.object(interp_api, "audit_intent", _wrapped):
            yield log
    finally:
        event.remove(sync, "before_flush", _on_flush)


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ROUTES)
async def test_hc_vrc_029_a_failed_started_row_stops_the_rebuild(rdbs, route):
    profile_db, master_db = rdbs
    obs, old_id, old_text = await _old_card(
        profile_db, dict(value=300.0, is_abnormal=False), WITHIN, ABOVE)
    before = await _snapshot(profile_db, obs.id)
    with _audit_fails_on("started"):
        resp = _fire(route, profile_db, master_db, obs.id, soft=True)
    assert resp.status_code == 500, resp.text
    assert old_text not in resp.text and WITHIN not in resp.text
    assert "normal reference range" not in resp.text
    (row,) = await _cards_of(profile_db, obs.id)  # no new card, the old one is not deleted
    assert (row.id, row.interpretation_text) == (old_id, old_text)
    assert await _snapshot(profile_db, obs.id) == before
    assert await _audit_pairs(master_db) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ROUTES)
async def test_hc_vrc_029_started_is_committed_before_the_old_row_is_deleted(rdbs, route):
    profile_db, master_db = rdbs
    obs, old_id, _ = await _old_card(
        profile_db, dict(value=300.0, is_abnormal=False), WITHIN, ABOVE)
    with _ordered(profile_db) as log:
        resp = _fire(route, profile_db, master_db, obs.id)
    assert resp.status_code == ROUTE_OK[route], resp.text
    assert log == ["started", "delete", "completed"], log
    (row,) = await _cards_of(profile_db, obs.id)
    assert row.id != old_id and ABOVE in row.interpretation_text


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ROUTES)
async def test_hc_vrc_029_a_failed_completed_row_leaves_the_started_row_on_record(rdbs, route):
    profile_db, master_db = rdbs
    obs, old_id, _ = await _old_card(
        profile_db, dict(value=300.0, is_abnormal=False), WITHIN, ABOVE)
    with _audit_fails_on("completed"):
        resp = _fire(route, profile_db, master_db, obs.id, soft=True)
    assert resp.status_code == 500, resp.text
    assert await _audit_pairs(master_db) == [(ROUTE_EVENT[route], "started")]


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ["grounded", "batch"])
async def test_hc_vrc_029_grounded_and_batch_write_their_own_pair_with_ids_only(rdbs, route):
    profile_db, master_db = rdbs
    obs, _, _ = await _old_card(profile_db, dict(value=300.0, is_abnormal=False), WITHIN, ABOVE)
    resp = _fire(route, profile_db, master_db, obs.id)
    assert resp.status_code == ROUTE_OK[route], resp.text
    assert await _audit_pairs(master_db) == [
        (ROUTE_EVENT[route], "started"), (ROUTE_EVENT[route], "completed")]
    master_db.expire_all()
    rows = (await master_db.execute(
        select(AuditLog).order_by(AuditLog.timestamp, AuditLog.id))).scalars().all()
    if route == "batch":
        for row in rows:
            assert json.loads(row.details_json)["observation_ids"] == [obs.id]
            assert json.loads(row.details_json)["count"] == 1
    else:
        assert all((r.entity_type, r.entity_id) == ("observation", obs.id) for r in rows)
    _no_phi(await _audit_blob(master_db))


NO_ROW_CASES = (
    [pytest.param(p.values[0], None, None, {}, id=f"agree-{p.id}") for p in AGREE_CASES]
    + [pytest.param(dict(value=300.0, is_abnormal=False), WITHIN, ABOVE, p.values[0], id=f"model-{p.id}")
       for p in MODEL_CARDS]
    + [pytest.param(p.values[0], p.values[1], p.values[2], {}, id=f"keep-{p.id}") for p in NEVER]
)


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ROUTES)
@pytest.mark.parametrize("kw,old,new,card_kw", NO_ROW_CASES)
async def test_hc_vrc_029_a_read_that_does_not_rebuild_writes_no_started_row(
    rdbs, route, kw, old, new, card_kw
):
    profile_db, master_db = rdbs
    obs, card_id, text = await _old_card(profile_db, kw, old, new, **card_kw)
    before = await _snapshot(profile_db, obs.id)
    spy = _WriteSpy(profile_db)
    resp = _fire(route, profile_db, master_db, obs.id)
    assert resp.status_code == ROUTE_OK[route], resp.text
    assert spy.writes == (0, 0), "a read that does not rebuild wrote to the profile"
    spy.close()
    assert await _snapshot(profile_db, obs.id) == before
    statuses = [s for _, s in await _audit_pairs(master_db)]
    assert "started" not in statuses and "completed" not in statuses, statuses


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ROUTES)
async def test_hc_vrc_029_the_second_read_after_a_rebuild_writes_no_started_row(rdbs, route):
    profile_db, master_db = rdbs
    obs, old_id, _ = await _old_card(profile_db, dict(value=300.0, is_abnormal=False), WITHIN, ABOVE)
    assert _fire(route, profile_db, master_db, obs.id).status_code == ROUTE_OK[route]
    (new_card,) = await _cards_of(profile_db, obs.id)
    assert new_card.id != old_id
    rows_after_first = len(await _audit_pairs(master_db))
    spy = _WriteSpy(profile_db)
    for _ in range(2):
        assert _fire(route, profile_db, master_db, obs.id).status_code == ROUTE_OK[route]
    assert spy.writes == (0, 0), "a second read wrote"
    spy.close()
    pairs = await _audit_pairs(master_db)
    assert [s for _, s in pairs].count("started") == 1, pairs
    assert [s for _, s in pairs].count("completed") == 1, pairs
    assert (await _cards_of(profile_db, obs.id))[0].id == new_card.id
    assert len(pairs) > rows_after_first  # the reads still write their own plain audit rows


# ── HC-VRC-029 (panel): the A2 pair on the panel route ───────────────────────
# L0 ruling 6656962109 item 1. A panel read that would replace the saved panel or a member
# card writes `panel_generate` started first (it names the stale panel row and every stale
# member card), then completed. Reads that rebuild nothing keep the single plain row.

PANEL_ROWS = [dict(value=300.0, is_abnormal=False), SODIUM_ROW]


async def _panel_case(profile_db, kind: str):
    """(observations, saved panel id, saved summary) for one panel starting state."""
    shown, old_card = {
        "stale_panel_stale_card": ([False, False], (WITHIN, ABOVE)),
        "stale_panel_only": ([False, False], None),
        "fresh_panel_stale_card": ([True, False], (WITHIN, ABOVE)),
        "no_panel_stale_card": ([False, False], (WITHIN, ABOVE)),
        "fresh_panel": ([True, False], None),
    }[kind]
    obs_list, panel_id, summary = await _old_panel(profile_db, PANEL_ROWS, shown, old_card=old_card)
    if kind == "no_panel_stale_card":
        for panel in await _panels(profile_db):
            await profile_db.delete(panel)
        await profile_db.commit()
    return obs_list, panel_id, summary


async def _state(profile_db, obs_list) -> tuple:
    """Every saved card and every saved panel, as a read would find them."""
    return ([await _snapshot(profile_db, o.id) for o in obs_list],
            [(p.id, p.summary_text) for p in await _panels(profile_db)])


@pytest.mark.asyncio
async def test_hc_vrc_029_panel_a_failed_started_row_stops_the_rebuild(rdbs):
    profile_db, master_db = rdbs
    obs_list, panel_id, old_summary = await _panel_case(profile_db, "stale_panel_stale_card")
    before = await _state(profile_db, obs_list)
    with _audit_fails_on("started"):
        resp = _fire("panel", profile_db, master_db, "", soft=True)
    assert resp.status_code == 500, resp.text
    assert old_summary not in resp.text
    assert await _state(profile_db, obs_list) == before  # panel and every card are unchanged
    assert await _audit_pairs(master_db) == []


@pytest.mark.asyncio
async def test_hc_vrc_029_panel_started_is_committed_before_any_row_is_deleted(rdbs):
    profile_db, master_db = rdbs
    obs_list, panel_id, _ = await _panel_case(profile_db, "stale_panel_stale_card")
    with _ordered(profile_db) as log:
        resp = _fire("panel", profile_db, master_db, "")
    assert resp.status_code == 201, resp.text
    assert log[0] == "started" and log[-1] == "completed", log
    assert log[1:-1] and set(log[1:-1]) == {"delete"}, log  # the card, then the panel row
    assert [p.id for p in await _panels(profile_db)] == [resp.json()["id"]]


@pytest.mark.asyncio
async def test_hc_vrc_029_panel_a_failed_completed_row_leaves_the_started_row_on_record(rdbs):
    profile_db, master_db = rdbs
    await _panel_case(profile_db, "stale_panel_stale_card")
    with _audit_fails_on("completed"):
        resp = _fire("panel", profile_db, master_db, "", soft=True)
    assert resp.status_code == 500, resp.text
    assert await _audit_pairs(master_db) == [(PANEL_EVENT, "started")]


@pytest.mark.asyncio
async def test_hc_vrc_029_panel_fresh_saved_panel_beside_a_stale_member_card_writes_nothing(rdbs):
    # The cached return answers and touches no member card, so no started row is written.
    profile_db, master_db = rdbs
    obs_list, panel_id, _ = await _panel_case(profile_db, "fresh_panel_stale_card")
    before = await _state(profile_db, obs_list)
    spy = _WriteSpy(profile_db)
    resp = _fire("panel", profile_db, master_db, "")
    assert resp.status_code == 201, resp.text
    assert resp.json()["id"] == panel_id
    assert spy.writes == (0, 0), "a cached panel read wrote to the profile"
    spy.close()
    assert await _state(profile_db, obs_list) == before
    assert await _audit_pairs(master_db) == [(PANEL_EVENT, None)]


@pytest.mark.asyncio
async def test_hc_vrc_029_panel_first_generation_with_no_card_writes_no_started_row(rdbs):
    profile_db, master_db = rdbs
    for kw in PANEL_ROWS:
        profile_db.add(_obs(user_verified=True, collected_at=DAY, **kw))
    await profile_db.commit()
    resp = _fire("panel", profile_db, master_db, "")
    assert resp.status_code == 201, resp.text
    assert await _audit_pairs(master_db) == [(PANEL_EVENT, None)]


@pytest.mark.asyncio
async def test_hc_vrc_029_panel_forced_read_with_no_stale_member_writes_no_started_row(rdbs):
    # A forced read skips the saved-panel lookup and deletes nothing (PANEL-FORCE-DUPLICATE),
    # so a stale saved panel is not at risk and no card is stale.
    profile_db, master_db = rdbs
    obs_list, _, _ = await _panel_case(profile_db, "stale_panel_only")
    cards_before = (await _state(profile_db, obs_list))[0]
    resp = _fire("panel", profile_db, master_db, "", force=True)
    assert resp.status_code == 201, resp.text
    assert (await _state(profile_db, obs_list))[0] == cards_before
    assert await _audit_pairs(master_db) == [(PANEL_EVENT, None)]


@pytest.mark.asyncio
async def test_hc_vrc_029_panel_second_read_after_a_rebuild_writes_no_started_row(rdbs):
    profile_db, master_db = rdbs
    obs_list, _, _ = await _panel_case(profile_db, "stale_panel_stale_card")
    first = _fire("panel", profile_db, master_db, "")
    assert first.status_code == 201, first.text
    spy = _WriteSpy(profile_db)
    for _ in range(2):
        again = _fire("panel", profile_db, master_db, "")
        assert again.status_code == 201, again.text
        assert again.json()["id"] == first.json()["id"]
    assert spy.writes == (0, 0), "a second panel read wrote"
    spy.close()
    statuses = [s for _, s in await _audit_pairs(master_db)]
    assert statuses.count("started") == 1 and statuses.count("completed") == 1, statuses


@pytest.mark.asyncio
async def test_hc_vrc_029_panel_no_saved_panel_and_a_stale_member_card_writes_the_pair(rdbs):
    profile_db, master_db = rdbs
    obs_list, _, _ = await _panel_case(profile_db, "no_panel_stale_card")
    assert await _panels(profile_db) == []
    resp = _fire("panel", profile_db, master_db, "")
    assert resp.status_code == 201, resp.text
    assert await _audit_pairs(master_db) == [(PANEL_EVENT, "started"), (PANEL_EVENT, "completed")]
    started, completed = await _rows_of(master_db, PANEL_EVENT)
    assert started.entity_id is None  # there is no saved panel row to name
    assert completed.entity_id == resp.json()["id"]
    for row in (started, completed):
        assert _det(row)["observation_ids"] == [obs_list[0].id], _det(row)
    _no_phi(await _audit_blob(master_db))


@pytest.mark.asyncio
async def test_hc_vrc_029_panel_saved_stale_panel_with_no_stale_card_writes_the_pair_with_no_ids(rdbs):
    # The saved panel row itself is deleted, so it is the thing at risk; no card is replaced.
    profile_db, master_db = rdbs
    obs_list, panel_id, _ = await _panel_case(profile_db, "stale_panel_only")
    resp = _fire("panel", profile_db, master_db, "")
    assert resp.status_code == 201, resp.text
    assert await _audit_pairs(master_db) == [(PANEL_EVENT, "started"), (PANEL_EVENT, "completed")]
    started, completed = await _rows_of(master_db, PANEL_EVENT)
    assert started.entity_id == panel_id and completed.entity_id == resp.json()["id"]
    for row in (started, completed):
        assert _det(row)["observation_ids"] == [] and _det(row)["count"] == 0, _det(row)
    _no_phi(await _audit_blob(master_db))


# ── HC-VRC-030: a withheld member of a stale panel fails the read closed ─────
# L0 ruling 6654607932 item 2, widened by 6656962109 items 1-3. A stale saved panel is
# replaced only when every member's rebuild succeeded: a member the safety check withholds
# leaves the saved panel (and the old text of its summary) in place, answers 500 with the
# escalation message, and writes one `interpretation.withheld` row per withheld member. The
# read is bracketed by `panel_generate` started and completed (the route is A2); a sibling
# rebuilt before the withheld member stays rebuilt and its id is in both rows. A withheld
# member WITH a saved card fails closed whatever the saved panel is (HC-VRC-031). A
# first-generation member with NO saved card, withheld, is still left out of the summary
# and the status, but the panel is created and discloses it by count — never by analyte —
# and the route writes its withheld row (HC-VRC-033, PANEL-WITHHELD-FIRSTGEN "Keep Count
# only").

SODIUM_HIGH = {**SODIUM_ROW, "value": 160.0}


def _withhold_for(*analytes: str):
    """Withhold the card the template writes for these analytes (the rest are written as usual)."""
    real = InterpretModule._generate_interpretation

    async def _gen(self, context, master_db):
        if context.observation.analyte_canonical in analytes:
            return FALSE_DOSING, None
        return await real(self, context, master_db)

    return patch.object(InterpretModule, "_generate_interpretation", _gen)


async def _say(profile_db, obs_id: str, old: str, new: str) -> None:
    """Make a saved card say `old` where the template writes `new` (an older wording)."""
    (card,) = await _cards_of(profile_db, obs_id)
    assert new in card.interpretation_text
    card.interpretation_text = card.interpretation_text.replace(new, old)
    await profile_db.commit()


def _assert_closed(resp, old_summary: str) -> None:
    assert resp.status_code == 500, resp.text
    assert resp.json()["detail"] == ESCALATE_TEMPLATE
    assert old_summary not in resp.text
    assert "within normal range" not in resp.text and "2 of 2" not in resp.text


@pytest.mark.asyncio
async def test_hc_vrc_030_a_withheld_stale_member_fails_the_panel_read_closed(rdbs):
    profile_db, master_db = rdbs
    obs_list, panel_id, old_summary = await _old_panel(
        profile_db, [dict(value=300.0, is_abnormal=False), SODIUM_ROW], [False, False],
        old_card=(WITHIN, ABOVE))
    assert "2 of 2 values are within normal range." in old_summary
    glucose_before = await _snapshot(profile_db, obs_list[0].id)
    sodium_before = await _snapshot(profile_db, obs_list[1].id)
    with _withhold_for("glucose"):
        resp = _read_panel(profile_db, master_db)
    _assert_closed(resp, old_summary)
    (panel,) = await _panels(profile_db)  # the saved panel is neither deleted nor replaced
    assert (panel.id, panel.summary_text) == (panel_id, old_summary)
    assert await _snapshot(profile_db, obs_list[0].id) == glucose_before
    assert await _snapshot(profile_db, obs_list[1].id) == sodium_before
    # started, one withheld row for the one withheld member, completed; ids only
    assert await _audit_pairs(master_db) == [
        (PANEL_EVENT, "started"), ("interpretation.withheld", None), (PANEL_EVENT, "completed")]
    started, completed = await _rows_of(master_db, PANEL_EVENT)
    assert _det(started)["observation_ids"] == [obs_list[0].id]  # the stale card at risk
    assert (started.entity_id, completed.entity_id) == (panel_id, panel_id)  # the saved row is kept
    assert _det(completed)["observation_ids"] == [] and _det(completed)["count"] == 0
    assert _det(completed)["skipped_count"] == 1
    (withheld,) = await _rows_of(master_db, "interpretation.withheld")
    assert (withheld.entity_type, withheld.entity_id) == ("observation", obs_list[0].id)
    _no_phi(await _audit_blob(master_db))

    spy = _WriteSpy(profile_db)  # a second and a third read answer the same and write nothing
    with _withhold_for("glucose"):
        for _ in range(2):
            _assert_closed(_read_panel(profile_db, master_db), old_summary)
    assert spy.writes == (0, 0), "a failed-closed panel read wrote to the profile"
    spy.close()
    assert [p.id for p in await _panels(profile_db)] == [panel_id]


@pytest.mark.asyncio
async def test_hc_vrc_030_two_withheld_members_write_two_withheld_rows(rdbs):
    profile_db, master_db = rdbs
    obs_list, panel_id, old_summary = await _old_panel(
        profile_db, [dict(value=300.0, is_abnormal=False), SODIUM_HIGH], [False, False],
        old_card=(WITHIN, ABOVE))
    await _say(profile_db, obs_list[1].id, WITHIN, ABOVE)
    before = [await _snapshot(profile_db, o.id) for o in obs_list]
    with _withhold_for("glucose", "sodium"):
        resp = _read_panel(profile_db, master_db)
    _assert_closed(resp, old_summary)
    (panel,) = await _panels(profile_db)
    assert (panel.id, panel.summary_text) == (panel_id, old_summary)
    assert [await _snapshot(profile_db, o.id) for o in obs_list] == before
    assert await _audit_pairs(master_db) == [
        (PANEL_EVENT, "started"), ("interpretation.withheld", None),
        ("interpretation.withheld", None), (PANEL_EVENT, "completed")]
    rows = await _rows_of(master_db, "interpretation.withheld")
    assert {r.entity_id for r in rows} == {o.id for o in obs_list}
    started, completed = await _rows_of(master_db, PANEL_EVENT)
    assert set(_det(started)["observation_ids"]) == {o.id for o in obs_list}
    assert _det(started)["count"] == 2
    assert _det(completed)["observation_ids"] == [] and _det(completed)["skipped_count"] == 2
    _no_phi(await _audit_blob(master_db))


@pytest.mark.asyncio
async def test_hc_vrc_030_a_rebuilt_member_stays_rebuilt_when_the_other_is_withheld(rdbs):
    # L1 reading 3: the first member's rebuild is correct and kept; the panel row is not
    # touched; the second read writes nothing (the rebuilt card is no longer stale).
    profile_db, master_db = rdbs
    obs_list, panel_id, old_summary = await _old_panel(
        profile_db, [dict(value=300.0, is_abnormal=False), SODIUM_HIGH], [False, False],
        old_card=(WITHIN, ABOVE))
    await _say(profile_db, obs_list[1].id, WITHIN, ABOVE)
    glucose_id, sodium_id = obs_list[0].id, obs_list[1].id
    (old_glucose,) = await _cards_of(profile_db, glucose_id)
    old_glucose_id = old_glucose.id
    sodium_before = await _snapshot(profile_db, sodium_id)
    with _withhold_for("sodium"):
        resp = _read_panel(profile_db, master_db)
    _assert_closed(resp, old_summary)
    (glucose,) = await _cards_of(profile_db, glucose_id)
    assert glucose.id != old_glucose_id and glucose.previous_interpretation_id == old_glucose_id
    assert ABOVE in glucose.interpretation_text and WITHIN not in glucose.interpretation_text
    assert await _snapshot(profile_db, sodium_id) == sodium_before
    (panel,) = await _panels(profile_db)
    assert (panel.id, panel.summary_text) == (panel_id, old_summary)
    # L0 ruling 6656962109 item 2: the rebuilt sibling is named, not replaced unnamed
    assert await _audit_pairs(master_db) == [
        (PANEL_EVENT, "started"), ("interpretation.withheld", None), (PANEL_EVENT, "completed")]
    started, completed = await _rows_of(master_db, PANEL_EVENT)
    assert set(_det(started)["observation_ids"]) == {glucose_id, sodium_id}
    assert _det(started)["count"] == 2
    assert _det(completed)["observation_ids"] == [glucose_id]  # the card that was replaced
    assert _det(completed)["count"] == 1 and _det(completed)["skipped_count"] == 1
    assert (started.entity_id, completed.entity_id) == (panel_id, panel_id)
    (withheld,) = await _rows_of(master_db, "interpretation.withheld")
    assert withheld.entity_id == sodium_id
    _no_phi(await _audit_blob(master_db))

    spy = _WriteSpy(profile_db)
    glucose_after = await _snapshot(profile_db, glucose_id)
    with _withhold_for("sodium"):
        _assert_closed(_read_panel(profile_db, master_db), old_summary)
    assert spy.writes == (0, 0), "the second read wrote"
    spy.close()
    # only the card still stale is at risk on the second read
    second = [_det(r)["observation_ids"] for r in await _rows_of(master_db, PANEL_EVENT)
              if _det(r).get("status") == "started"][1]
    assert second == [sodium_id]
    assert await _snapshot(profile_db, glucose_id) == glucose_after
    assert await _snapshot(profile_db, sodium_id) == sodium_before



# ── Review round 1: grounded and batch guards, withheld on grounded and batch ─
# Each case below kills a line that no earlier test could see (a break on a /dev/shm copy
# stayed green): the batch owner filter, the strict `not in unverified` filter, the
# repeated-id discard, and the grounded ownership check in front of a rebuild.


async def _batch(profile_db, master_db, ids: list[str]):
    return _call(profile_db, master_db, interpretations_router, "/interpretations", "POST",
                 "/interpretations/batch", json={"observation_ids": ids})


async def _started_ids(master_db) -> list[list[str]]:
    master_db.expire_all()
    rows = (await master_db.execute(select(AuditLog).order_by(AuditLog.timestamp, AuditLog.id))).scalars().all()
    return [json.loads(r.details_json)["observation_ids"] for r in rows
            if r.details_json and json.loads(r.details_json).get("status") == "started"]


@pytest.mark.asyncio
async def test_hc_vrc_028_grounded_on_another_profiles_row_is_403_and_untouched(rdbs):
    profile_db, master_db = rdbs
    obs, _, _ = await _old_card(
        profile_db, dict(value=300.0, is_abnormal=False, profile_id="another-profile"), WITHIN, ABOVE)
    before = await _snapshot(profile_db, obs.id)
    spy = _WriteSpy(profile_db)
    resp = _fire("grounded", profile_db, master_db, obs.id)
    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == "Access denied to this observation"
    assert spy.writes == (0, 0)
    spy.close()
    assert await _snapshot(profile_db, obs.id) == before
    assert await _audit_events(master_db) == []


@pytest.mark.asyncio
async def test_hc_vrc_029_batch_started_row_names_only_this_profiles_stale_rows(rdbs):
    profile_db, master_db = rdbs
    mine, mine_old, _ = await _old_card(profile_db, dict(value=300.0, is_abnormal=False), WITHIN, ABOVE)
    theirs, _, _ = await _old_card(
        profile_db, dict(value=300.0, is_abnormal=False, profile_id="another-profile"), WITHIN, ABOVE)
    theirs_before = await _snapshot(profile_db, theirs.id)
    resp = await _batch(profile_db, master_db, [mine.id, theirs.id])
    assert resp.status_code == 200, resp.text
    assert resp.json()["successful"] == [mine.id]
    assert resp.json()["failed"] == [{"observation_id": theirs.id, "error": "Access denied"}]
    assert await _started_ids(master_db) == [[mine.id]]
    assert await _snapshot(profile_db, theirs.id) == theirs_before
    assert (await _cards_of(profile_db, mine.id))[0].id != mine_old
    _no_phi(await _audit_blob(master_db))


@pytest.mark.asyncio
async def test_hc_vrc_029_batch_alone_on_another_profiles_row_writes_no_started_row(rdbs):
    profile_db, master_db = rdbs
    theirs, _, _ = await _old_card(
        profile_db, dict(value=300.0, is_abnormal=False, profile_id="another-profile"), WITHIN, ABOVE)
    before = await _snapshot(profile_db, theirs.id)
    spy = _WriteSpy(profile_db)
    resp = await _batch(profile_db, master_db, [theirs.id])
    assert resp.status_code == 200, resp.text
    assert resp.json()["failed"] == [{"observation_id": theirs.id, "error": "Access denied"}]
    assert spy.writes == (0, 0)
    spy.close()
    assert await _snapshot(profile_db, theirs.id) == before
    assert await _started_ids(master_db) == []
    assert "started" not in [s for _, s in await _audit_pairs(master_db)]


@pytest.mark.asyncio
async def test_hc_vrc_029_batch_under_strict_mode_keeps_a_refused_row_out_of_the_started_row(rdbs):
    profile_db, master_db = rdbs
    profile_db.add(UserModelSettings(id=str(uuid.uuid4()), profile_id=PROFILE_ID, strict_safety_mode=True))
    await profile_db.commit()
    verified, verified_old, _ = await _old_card(
        profile_db, dict(value=300.0, is_abnormal=False), WITHIN, ABOVE)
    refused, _, _ = await _old_card(
        profile_db, dict(value=300.0, is_abnormal=False), WITHIN, ABOVE, verified=False)
    refused_before = await _snapshot(profile_db, refused.id)
    resp = await _batch(profile_db, master_db, [verified.id, refused.id])
    assert resp.status_code == 200, resp.text
    assert resp.json()["successful"] == [verified.id]
    (failure,) = resp.json()["failed"]
    assert failure["observation_id"] == refused.id and failure["error"] == interp_api.UNVERIFIED_BATCH_ERROR
    assert await _started_ids(master_db) == [[verified.id]]
    assert await _snapshot(profile_db, refused.id) == refused_before
    assert (await _cards_of(profile_db, verified.id))[0].id != verified_old


@pytest.mark.asyncio
async def test_hc_vrc_029_batch_alone_on_a_strict_refused_row_writes_no_started_row(rdbs):
    profile_db, master_db = rdbs
    profile_db.add(UserModelSettings(id=str(uuid.uuid4()), profile_id=PROFILE_ID, strict_safety_mode=True))
    await profile_db.commit()
    refused, _, _ = await _old_card(
        profile_db, dict(value=300.0, is_abnormal=False), WITHIN, ABOVE, verified=False)
    before = await _snapshot(profile_db, refused.id)
    spy = _WriteSpy(profile_db)
    resp = await _batch(profile_db, master_db, [refused.id])
    assert resp.status_code == 200, resp.text
    assert resp.json()["failed"][0]["error"] == interp_api.UNVERIFIED_BATCH_ERROR
    assert spy.writes == (0, 0)
    spy.close()
    assert await _snapshot(profile_db, refused.id) == before
    assert "started" not in [s for _, s in await _audit_pairs(master_db)]


@pytest.mark.asyncio
async def test_hc_vrc_029_batch_rebuilds_a_repeated_id_once(rdbs):
    profile_db, master_db = rdbs
    obs, old_id, _ = await _old_card(profile_db, dict(value=300.0, is_abnormal=False), WITHIN, ABOVE)
    resp = await _batch(profile_db, master_db, [obs.id, obs.id])
    assert resp.status_code == 200, resp.text
    assert resp.json()["successful"] == [obs.id, obs.id]
    (row,) = await _cards_of(profile_db, obs.id)
    assert row.id != old_id and row.regeneration_count == 1
    assert await _started_ids(master_db) == [[obs.id]]


@pytest.mark.asyncio
@pytest.mark.parametrize("route", ["grounded", "batch"])
async def test_hc_vrc_024_withheld_stale_rebuild_on_grounded_and_batch_serves_no_old_text(rdbs, route):
    profile_db, master_db = rdbs
    obs, old_id, old_text = await _old_card(
        profile_db, dict(value=300.0, is_abnormal=False), WITHIN, ABOVE)
    before = await _snapshot(profile_db, obs.id)
    with _force_withhold():
        resp = _fire(route, profile_db, master_db, obs.id)
    assert resp.status_code == ROUTE_OK[route], resp.text
    if route == "grounded":
        assert resp.json()["withheld"] is True
        assert resp.json()["interpretation"] is None
    else:
        assert resp.json()["successful"] == []
        assert resp.json()["failed"] == [{"observation_id": obs.id, "error": ESCALATE_TEMPLATE}]
    assert WITHIN not in resp.text and old_text not in resp.text
    assert "normal reference range" not in resp.text
    assert await _snapshot(profile_db, obs.id) == before
    pairs = await _audit_pairs(master_db)
    assert [s for _, s in pairs if s in ("started", "completed")] == ["started", "completed"], pairs
    if route == "grounded":
        # the withheld row closes the pair, as it does on GET and POST
        assert pairs == [("interpretation.grounded", "started"),
                         ("interpretation.withheld", "completed")], pairs
    _no_phi(await _audit_blob(master_db))


# ── HC-VRC-031: a withheld member with a saved card fails closed whatever the saved panel is ──
# L0 ruling 6656962109 item 3. The stale member's card is kept, nothing old is served, and
# the read answers the same every time. Measured at 26872a5a: read 1 answered 201 "normal"
# (the member dropped), read 2 answered 500.

SAVED_CARD_CASES = [
    pytest.param("no_panel_stale_card", False, id="no-saved-panel"),
    pytest.param("fresh_panel_stale_card", True, id="forced-with-a-saved-fresh-panel"),
    pytest.param("no_panel_stale_card", True, id="forced-with-no-saved-panel"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("kind,force", SAVED_CARD_CASES)
async def test_hc_vrc_031_a_withheld_member_with_a_saved_card_fails_the_panel_read_closed(
    rdbs, kind, force
):
    profile_db, master_db = rdbs
    obs_list, _, old_summary = await _panel_case(profile_db, kind)
    glucose_id = obs_list[0].id
    before = await _state(profile_db, obs_list)
    answers = []
    for read in (1, 2):
        with _withhold_for("glucose"):
            resp = _fire("panel", profile_db, master_db, "", force=force)
        _assert_closed(resp, old_summary)
        answers.append((resp.status_code, resp.json()["detail"]))
        assert await _state(profile_db, obs_list) == before, f"read {read} changed the vault"
        rows = await _rows_of(master_db, "interpretation.withheld")
        assert [r.entity_id for r in rows] == [glucose_id] * read  # one row per read
    assert answers[0] == answers[1] == (500, ESCALATE_TEMPLATE)
    # the first read: started naming the stale card, the withheld row, completed with no id
    first = (await _audit_pairs(master_db))[:3]
    assert first == [(PANEL_EVENT, "started"), ("interpretation.withheld", None),
                     (PANEL_EVENT, "completed")]
    started, completed = (await _rows_of(master_db, PANEL_EVENT))[:2]
    assert _det(started)["observation_ids"] == [glucose_id]
    assert _det(completed)["observation_ids"] == [] and _det(completed)["skipped_count"] == 1
    _no_phi(await _audit_blob(master_db))


# ── HC-VRC-032: a withheld batch card writes the interpretation.withheld row ──
# L0 ruling 6656962109 item 4. The single card writes one; the batch wrote none, on main
# (forced) and now on a stale rebuild too. The row is written after the loop, outside the
# per-item try, so a failed audit write raises instead of becoming an "Internal error".

BATCH_EVENT = "interpretation.batch_generate"


def _assert_batch_withheld(resp, obs_id: str, times: int = 1) -> None:
    assert resp.status_code == 200, resp.text
    assert resp.json()["successful"] == []
    assert resp.json()["failed"] == [{"observation_id": obs_id, "error": ESCALATE_TEMPLATE}] * times
    assert WITHIN not in resp.text and "normal reference range" not in resp.text


@pytest.mark.asyncio
async def test_hc_vrc_032_a_withheld_stale_batch_rebuild_writes_the_withheld_row(rdbs):
    profile_db, master_db = rdbs
    obs, _, _ = await _old_card(profile_db, dict(value=300.0, is_abnormal=False), WITHIN, ABOVE)
    before = await _snapshot(profile_db, obs.id)
    with _force_withhold():
        resp = _fire("batch", profile_db, master_db, obs.id)
    _assert_batch_withheld(resp, obs.id)
    assert await _snapshot(profile_db, obs.id) == before
    assert await _audit_pairs(master_db) == [
        (BATCH_EVENT, "started"), ("interpretation.withheld", None), (BATCH_EVENT, "completed")]
    (row,) = await _rows_of(master_db, "interpretation.withheld")
    assert (row.entity_type, row.entity_id) == ("observation", obs.id)
    assert _det(row)["reason"] == "safety_check_failed" and _det(row)["decision"] == "escalate"
    started, completed = await _rows_of(master_db, BATCH_EVENT)
    assert _det(started)["observation_ids"] == [obs.id]
    assert _det(completed)["observation_ids"] == [] and _det(completed)["skipped_count"] == 1
    _no_phi(await _audit_blob(master_db))


@pytest.mark.asyncio
async def test_hc_vrc_032_a_withheld_forced_batch_rebuild_writes_the_withheld_row(rdbs):
    profile_db, master_db = rdbs
    obs, _, _ = await _old_card(profile_db, dict(value=300.0, is_abnormal=False), None, None)
    before = await _snapshot(profile_db, obs.id)
    with _force_withhold():
        resp = _fire("batch", profile_db, master_db, obs.id, force=True)
    _assert_batch_withheld(resp, obs.id)
    assert await _snapshot(profile_db, obs.id) == before
    assert await _audit_pairs(master_db) == [
        (BATCH_EVENT, "started"), ("interpretation.withheld", None), (BATCH_EVENT, "completed")]
    (row,) = await _rows_of(master_db, "interpretation.withheld")
    assert row.entity_id == obs.id
    _no_phi(await _audit_blob(master_db))


@pytest.mark.asyncio
async def test_hc_vrc_032_a_withheld_first_generation_batch_card_writes_the_withheld_row(rdbs):
    profile_db, master_db = rdbs
    obs_id = await _seed(profile_db, value=300.0, is_abnormal=False)
    with _force_withhold():
        resp = _fire("batch", profile_db, master_db, obs_id)
    _assert_batch_withheld(resp, obs_id)
    assert await _cards_of(profile_db, obs_id) == []
    # nothing was at risk, so no started row; the plain rows are the withheld row and the batch row
    assert await _audit_pairs(master_db) == [("interpretation.withheld", None), (BATCH_EVENT, None)]


@pytest.mark.asyncio
async def test_hc_vrc_032_a_repeated_withheld_id_writes_one_row(rdbs):
    profile_db, master_db = rdbs
    obs, _, _ = await _old_card(profile_db, dict(value=300.0, is_abnormal=False), WITHIN, ABOVE)
    with _force_withhold():
        resp = await _batch(profile_db, master_db, [obs.id, obs.id])
    _assert_batch_withheld(resp, obs.id, times=2)  # failed still lists every request entry
    rows = await _rows_of(master_db, "interpretation.withheld")
    assert [r.entity_id for r in rows] == [obs.id]


@pytest.mark.asyncio
async def test_hc_vrc_032_a_failed_withheld_audit_write_raises_instead_of_an_internal_error_entry(rdbs):
    profile_db, master_db = rdbs
    obs, _, _ = await _old_card(profile_db, dict(value=300.0, is_abnormal=False), WITHIN, ABOVE)
    before = await _snapshot(profile_db, obs.id)
    real = interp_api.audit_and_commit

    async def _wrapped(db, log_fn, **kw):
        if kw.get("event_type") == "interpretation.withheld":
            raise RuntimeError("audit down")
        return await real(db, log_fn, **kw)

    with _force_withhold(), patch.object(interp_api, "audit_and_commit", _wrapped):
        resp = _fire("batch", profile_db, master_db, obs.id, soft=True)
    assert resp.status_code == 500, resp.text
    assert "Internal error" not in resp.text
    assert await _snapshot(profile_db, obs.id) == before
    assert await _audit_pairs(master_db) == [(BATCH_EVENT, "started")]  # the pair stays open


# ── HC-VRC-033: a withheld first-generation member is counted, never named ──
# PANEL-WITHHELD-FIRSTGEN, owner answer "Keep Count only" (2026-11-07): a member the
# safety check withholds on a first-generation read (no saved panel, no saved card) is
# still left out of the summary and the status — but the panel is created, discloses it
# by count (never by analyte), and the route writes one interpretation.withheld row for
# it, same shape as a kept member's. The member's own physician-review flag survives.

NOTICE_ONE = (
    "One result in this panel could not be checked and is not counted in this summary. "
    "Please review it with your healthcare provider."
)


def _notice(n: int) -> str:
    """The approved count-only sentence for n > 1 withheld first-generation members."""
    return (
        f"{n} results in this panel could not be checked and are not counted in this "
        "summary. Please review them with your healthcare provider."
    )


@pytest.mark.asyncio
async def test_hc_vrc_033_a_dropped_member_is_counted_never_named(rdbs):
    profile_db, master_db = rdbs
    glucose_id = await _seed(profile_db, value=300.0, is_abnormal=False)
    sodium_id = await _seed(profile_db, **SODIUM_ROW)
    with _withhold_for("glucose"):
        resp = _read_panel(profile_db, master_db)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert NOTICE_ONE in body["summary_text"], body["summary_text"]
    assert "1 of 1 values are within normal range." in body["summary_text"]
    assert "glucose" not in body["summary_text"].lower()
    assert set(body["observation_ids"]) == {glucose_id, sodium_id}
    assert body["overall_status"] == "normal"
    assert body["requires_physician_review"] is False
    # one withheld row for the dropped member: entity id and check names only
    (row,) = await _rows_of(master_db, "interpretation.withheld")
    assert (row.entity_type, row.entity_id) == ("observation", glucose_id)
    assert _det(row)["reason"] == "safety_check_failed"
    assert _det(row)["decision"] == "escalate"
    assert _det(row)["checks_failed"]
    assert "glucose" not in json.dumps(_det(row)).lower()
    assert "300.0" not in json.dumps(_det(row))
    assert await _audit_pairs(master_db) == [
        ("interpretation.withheld", None), (PANEL_EVENT, None)]
    assert await _cards_of(profile_db, glucose_id) == []
    assert len(await _cards_of(profile_db, sodium_id)) == 1
    _no_phi(await _audit_blob(master_db))


@pytest.mark.asyncio
async def test_hc_vrc_033_b_second_read_serves_the_saved_panel(rdbs):
    profile_db, master_db = rdbs
    glucose_id = await _seed(profile_db, value=300.0, is_abnormal=False)
    await _seed(profile_db, **SODIUM_ROW)
    with _withhold_for("glucose"):
        first = _read_panel(profile_db, master_db)
    assert first.status_code == 201, first.text
    assert NOTICE_ONE in first.json()["summary_text"]
    spy = _WriteSpy(profile_db)
    second = _read_panel(profile_db, master_db)
    assert second.status_code == 201, second.text
    assert second.json()["id"] == first.json()["id"]  # the saved row, not a rebuild
    assert second.json()["summary_text"] == first.json()["summary_text"]  # the notice persists
    assert spy.writes == (0, 0), "the second read wrote to the profile"
    spy.close()
    rows = await _rows_of(master_db, "interpretation.withheld")
    assert [r.entity_id for r in rows] == [glucose_id]  # no second withheld row


@pytest.mark.asyncio
async def test_hc_vrc_033_c_forced_read_rebuilds_and_writes_another_withheld_row(rdbs):
    profile_db, master_db = rdbs
    glucose_id = await _seed(profile_db, value=300.0, is_abnormal=False)
    await _seed(profile_db, **SODIUM_ROW)
    with _withhold_for("glucose"):
        first = _read_panel(profile_db, master_db)
        assert first.status_code == 201, first.text
        forced = _read_panel(profile_db, master_db, force=True)
    assert forced.status_code == 201, forced.text
    assert NOTICE_ONE in forced.json()["summary_text"], forced.json()["summary_text"]
    assert forced.json()["id"] != first.json()["id"]  # a forced read rebuilds
    rows = await _rows_of(master_db, "interpretation.withheld")
    assert [r.entity_id for r in rows] == [glucose_id, glucose_id]


@pytest.mark.asyncio
async def test_hc_vrc_033_d_both_members_withheld_prints_the_plural_notice(rdbs):
    profile_db, master_db = rdbs
    glucose_id = await _seed(profile_db, value=300.0, is_abnormal=False)
    sodium_id = await _seed(profile_db, **SODIUM_ROW)
    with _withhold_for("glucose", "sodium"):
        resp = _read_panel(profile_db, master_db)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert _notice(2) in body["summary_text"], body["summary_text"]
    assert "0 of 0" not in body["summary_text"]
    assert "values are within normal range" not in body["summary_text"]
    assert "glucose" not in body["summary_text"].lower()
    assert "sodium" not in body["summary_text"].lower()
    # Owner 2026-11-10: a panel with nothing checked never reads "normal".
    assert body["overall_status"] == "incomplete"
    rows = await _rows_of(master_db, "interpretation.withheld")
    assert {r.entity_id for r in rows} == {glucose_id, sodium_id}
    _no_phi(await _audit_blob(master_db))


@pytest.mark.asyncio
async def test_hc_vrc_033_e_dropped_members_physician_review_flag_is_kept(rdbs):
    # Glucose 500 mg/dL is above the critical threshold (400), so the withheld member's
    # own check set the flag before the withhold; the panel must not lose it.
    profile_db, master_db = rdbs
    glucose_id = await _seed(profile_db, value=500.0, is_abnormal=True)
    await _seed(profile_db, **SODIUM_ROW)
    with _withhold_for("glucose"):
        resp = _read_panel(profile_db, master_db)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["requires_physician_review"] is True
    assert body["overall_status"] == "normal"  # the one checked member is in range
    assert NOTICE_ONE in body["summary_text"]
    (row,) = await _rows_of(master_db, "interpretation.withheld")
    assert row.entity_id == glucose_id


@pytest.mark.asyncio
async def test_hc_vrc_033_f_no_withheld_member_keeps_todays_shape(rdbs):
    # Pin (already green on main): nothing withheld, so nothing is disclosed and the
    # summary is byte-for-byte today's.
    profile_db, master_db = rdbs
    for kw in PANEL_ROWS:
        profile_db.add(_obs(user_verified=True, collected_at=DAY, **kw))
    await profile_db.commit()
    resp = _read_panel(profile_db, master_db)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["summary_text"] == (
        "Your Comprehensive Metabolic Panel results:\n\n"
        "**Items requiring attention:**\n"
        "- GLUCOSE: 300.0 mg/dL (above normal)\n\n"
        "1 of 2 values are within normal range.\n\n"
        "This summary is for educational purposes only. "
        "Please consult your healthcare provider for personalized interpretation."
    )
    assert "could not be checked" not in body["summary_text"]
    assert body["overall_status"] == "borderline"
    assert body["requires_physician_review"] is False
    assert await _rows_of(master_db, "interpretation.withheld") == []
    assert await _audit_pairs(master_db) == [(PANEL_EVENT, None)]
