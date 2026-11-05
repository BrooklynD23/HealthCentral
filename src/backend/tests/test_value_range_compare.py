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
HC-VRC-026  audit rows of a rebuilding read
HC-VRC-027  no rewrite loop: a fresh card is never stale

The helper is reached through a function (not a module-level import), so before
the fix each test fails on its own id instead of the whole file failing to collect.
"""

from __future__ import annotations

import hashlib
import inspect
import io
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

import api.export as export_api
import api.observations as obs_api
import models  # noqa: F401  (registers tables on Base.metadata)
from api import documents as documents_api
from api.documents import router as documents_router
from api.interpretations import router as interpretations_router
from core.auth import get_profile_db_session
from core.database import Base
from core.profile_database import ProfileDatabaseBase
from models import Document, Observation
from models.knowledge_base import BiomarkerKnowledge
from modules.interpret import InterpretationContext, InterpretModule
from modules.interpret_safety import InterpretationSafetyGuard
from modules.knowledge_loader import BiomarkerInfo, get_knowledge_loader
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
# Every status sentence main can produce without a knowledge-base entry.
CLOSED = [ABOVE, BELOW, WITHIN, OUTSIDE, NO_RANGE]


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
    assert literal in text, text
    # Closed list: remove everything main can already say; nothing may be left over.
    assert _residue(text, obs) == "", text
    for other in [s for s in CLOSED if s != literal]:
        assert other not in text, text


@pytest.mark.asyncio
@pytest.mark.parametrize("flag,stored,field", [("N", True, None), ("H", True, "high_interpretation")])
async def test_hc_vrc_006_guard_disagreement_with_kb_uses_todays_kb_text(flag, stored, field):
    obs = _obs(flag=flag, value=300.0 if flag == "N" else 85.0, is_abnormal=stored)
    text = await _text(obs, SYNTHETIC_KB)
    if field is None:
        assert OUTSIDE in text, text
    else:
        assert f"SENTINEL-HIGH [KB:{SYNTHETIC_KB.id}]" in text, text
    assert "SENTINEL-NORMAL" not in text and "SENTINEL-LOW" not in text, text


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
        assert "flagged as abnormal" in q["context"], q["context"]


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
    assert "flagged as H" in next(x for x in q.json() if x["category"] == "abnormal")["context"]
