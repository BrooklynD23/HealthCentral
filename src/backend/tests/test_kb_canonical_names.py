"""KB-CANONICAL-NAMES: the knowledge base is seeded under the names the normalizer stores.

`NormalizeModule.normalize_analyte` stores a white cell count as `white_blood_cells`,
HbA1c / A1C as `hba1c`, Glucose as `glucose`. The seed used `wbc`, `hemoglobin_a1c` and
`glucose_fasting`, and the lipid relationship rows were seeded under panel `lipid_panel`
while the panel key is `lipid`. Every read is an exact match on the stored name, so the names
the normalizer stores for those labels found no row: no knowledge-base text, no knowledge-base
critical limits, no interventions, no Total/HDL or LDL/HDL insight. A result stored under an old
name (for example label `Glucose Fasting`, stored as `glucose_fasting`) did find its row, and
HC-KCN-009 keeps that so after the rename.

The fix renames the seed (names only, never a word of seeded text) and adds master-chain
migration 003 to rename rows already installed.

Every test builds the master DB the way main does (run_master_migrations() on a tmp dir,
then seed_all as main.py calls it) on a tmp engine. None touches the module-level master engine.

HC-KCN-001  WBC / HbA1c / Glucose labels load their KB row through normalize -> loader ->
            interpret, and HbA1c high gets its interventions.
HC-KCN-002  every seeded analyte name is a name the normalizer can produce.
HC-KCN-003  lipid ratio insights attach through interpret_panel.
HC-KCN-004  HbA1c 10.5 reaches check_critical_value with the KB limit 10.0; 9.5 does not.
HC-KCN-005  migration 003: rename, no-op rerun, collisions, seed afterwards, downgrade,
            and the two accepted paths (standalone seed, baseline stamp).
HC-KCN-006  no word of seeded text changed (sha256 pins taken on origin/main d1f05349).
HC-KCN-007  prohibited-pattern guard over every newly reachable text field.
HC-KCN-008  the Explain chip key for a stored `hba1c` name.
HC-KCN-009  a result stored under an old name keeps its KB row and critical limits (loader and
            biomarker route read the old names through one alias map).
HC-KCN-010  KB-UNIT-BADGE: the critical badge compares in the KB limit's unit (D1).
HC-KCN-011  both severity callers pass observation.unit.
HC-KCN-012  KB-UNIT-BADGE D2: the physician-review banner follows the badge's unit rule.
HC-KCN-013  KB-UNIT-BADGE D3: a saved card whose severity the rule now disagrees with is rebuilt.

Known gap (HC-KCN-007 reader scan, HC-KCN-008): scripts/change_scope.py gives backend=false for a
PR that touches only src/frontend, so a frontend-only PR does not run this file. See HC-KCN-007.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool

import models  # noqa: F401  register every table on both bases
from core.config import settings
from core.migrations import _get_alembic_config, _get_sync_master_url, run_master_migrations
from core.profile_database import ProfileDatabaseBase
from models import Observation
from models.knowledge_base import BiomarkerKnowledge, BiomarkerRelationship, InterventionMapping
from modules.interpret import InterpretModule
from modules.interpret_safety import InterpretationSafetyGuard
from modules.knowledge_loader import KnowledgeLoader
from modules.normalize import NormalizeModule
from modules.recommend import RecommendationEngine
from scripts import seed_knowledge_base as skb

PROFILE_ID = "profile-kcn"
COLLECTED = datetime(2026, 3, 1, 9, 0, 0)

# old seed name -> name the normalizer stores
RENAMES = {"glucose_fasting": "glucose", "hemoglobin_a1c": "hba1c", "wbc": "white_blood_cells"}
UNRENAMES = {new: old for old, new in RENAMES.items()}
PANEL_RENAMES = {"lipid_panel": "lipid"}
PANEL_UNRENAMES = {new: old for old, new in PANEL_RENAMES.items()}

ANALYTE_KEYS = ("analyte_canonical", "primary_analyte", "related_analyte")

# Columns the migration is allowed to change, per table.
NAME_COLS = {
    "biomarker_knowledge": {"analyte_canonical"},
    "intervention_mappings": {"analyte_canonical"},
    "biomarker_relationships": {"primary_analyte", "related_analyte", "panel_name"},
}
TABLES = tuple(NAME_COLS)
MIGRATION_FILE = (
    Path(__file__).resolve().parents[1] / "migrations" / "master" / "versions" / "003_kb_canonical_names.py"
)


# ---------------------------------------------------------------------------
# scaffolding
# ---------------------------------------------------------------------------


def _as_named(row: dict, analytes: dict, panels: dict) -> dict:
    """A copy of a seed row with its name fields mapped; text fields are untouched."""
    out = dict(row)
    for key in ANALYTE_KEYS:
        if key in out:
            out[key] = analytes.get(out[key], out[key])
    if out.get("panel_name") is not None:
        out["panel_name"] = panels.get(out["panel_name"], out["panel_name"])
    return out


def _as_new(row: dict) -> dict:
    return _as_named(row, RENAMES, PANEL_RENAMES)


def _as_old(row: dict) -> dict:
    return _as_named(row, UNRENAMES, PANEL_UNRENAMES)


def _seed_rows(kind: str, naming) -> list[dict]:
    data = {
        "biomarker_knowledge": skb.BIOMARKER_DATA,
        "intervention_mappings": skb.INTERVENTION_DATA,
        "biomarker_relationships": skb.RELATIONSHIP_DATA,
    }[kind]
    return [naming(d) for d in data]


@pytest.fixture
def data_root(tmp_path, monkeypatch):
    """Point the settings at a tmp dir (pattern of tests/security/test_sql_echo_phi.py)."""
    root = tmp_path / "data"
    root.mkdir()
    monkeypatch.setattr(type(settings), "app_data_path", property(lambda self: root))
    return root


def _sync_url() -> str:
    return _get_sync_master_url()


def _async_url() -> str:
    return _sync_url().replace("sqlite://", "sqlite+aiosqlite://")


def _cfg():
    return _get_alembic_config("master")


def _upgrade(rev: str) -> None:
    command.upgrade(_cfg(), rev)


def _insert(table, rows: list[dict]) -> list[str]:
    """Insert rows with fresh ids (and the model's python-side defaults); return the ids."""
    ids = []
    engine = create_engine(_sync_url())
    try:
        with engine.begin() as conn:
            for row in rows:
                row_id = str(uuid.uuid4())
                values = dict(row)
                if table is InterventionMapping.__table__:
                    values.setdefault("is_active", True)
                conn.execute(table.insert().values(id=row_id, **values))
                ids.append(row_id)
    finally:
        engine.dispose()
    return ids


BIO = BiomarkerKnowledge.__table__
ITV = InterventionMapping.__table__
REL = BiomarkerRelationship.__table__


def _oldest_texts() -> dict[tuple[str, str], str]:
    """(stored name, field) -> the oldest text _TEXT_REVISIONS knows for it (first entry per pair)."""
    oldest: dict[tuple[str, str], str] = {}
    for analyte, field, old_text, _new in skb._TEXT_REVISIONS:
        # RENAMES.get: a revision key left on the old name must still count as this analyte's
        # oldest text, or the test would follow the broken key instead of catching it.
        oldest.setdefault((RENAMES.get(analyte, analyte), field), old_text)
    return oldest


def _install_old_names(old_text: bool = False) -> dict[str, list[str]]:
    """What an install made by the old seed holds: every row under its old name.

    old_text=True also puts the oldest revised text back on the renamed analytes, as an install
    made before the _TEXT_REVISIONS entries would hold them.
    """
    bio_rows = _seed_rows("biomarker_knowledge", _as_old)
    if old_text:
        oldest = _oldest_texts()
        for row in bio_rows:
            stored = RENAMES.get(row["analyte_canonical"])
            if stored is None:
                continue
            for (analyte, field), text_ in oldest.items():
                if analyte == stored:
                    row[field] = text_
    return {
        "biomarker_knowledge": _insert(BIO, bio_rows),
        "intervention_mappings": _insert(ITV, _seed_rows("intervention_mappings", _as_old)),
        "biomarker_relationships": _insert(REL, _seed_rows("biomarker_relationships", _as_old)),
    }


def _dump() -> dict[str, list[dict]]:
    engine = create_engine(_sync_url())
    try:
        with engine.connect() as conn:
            return {
                t: [dict(r._mapping) for r in conn.execute(text(f"SELECT * FROM {t} ORDER BY id"))]
                for t in TABLES
            }
    finally:
        engine.dispose()


def _keys(dump: dict[str, list[dict]]) -> dict[str, Counter]:
    return {
        "biomarker_knowledge": Counter(r["analyte_canonical"] for r in dump["biomarker_knowledge"]),
        "intervention_mappings": Counter(
            (r["analyte_canonical"], r["condition_type"], r["intervention_title"])
            for r in dump["intervention_mappings"]
        ),
        "biomarker_relationships": Counter(
            (r["primary_analyte"], r["related_analyte"], r["relationship_type"])
            for r in dump["biomarker_relationships"]
        ),
    }


def _seed_keys(naming) -> dict[str, Counter]:
    return {
        "biomarker_knowledge": Counter(r["analyte_canonical"] for r in _seed_rows("biomarker_knowledge", naming)),
        "intervention_mappings": Counter(
            (r["analyte_canonical"], r["condition_type"], r["intervention_title"])
            for r in _seed_rows("intervention_mappings", naming)
        ),
        "biomarker_relationships": Counter(
            (r["primary_analyte"], r["related_analyte"], r["relationship_type"])
            for r in _seed_rows("biomarker_relationships", naming)
        ),
    }


def _counts(dump) -> dict[str, int]:
    return {t: len(rows) for t, rows in dump.items()}


def _run_seed() -> tuple[int, int, int]:
    """seed_all, as main.py calls it (skip_db_init=True), with its session maker pointed at a tmp
    engine (pattern of test_biomarker_assistant.py:266). Never the module-level master engine."""

    async def _go():
        engine = create_async_engine(_async_url())
        try:
            maker = lambda: AsyncSession(engine, expire_on_commit=False)  # noqa: E731
            with patch.object(skb, "async_session_maker", maker):
                r = await skb.seed_all(skip_db_init=True)
            return r["biomarkers"], r["interventions"], r["relationships"]
        finally:
            await engine.dispose()

    return asyncio.run(_go())


def _without_names(rows: list[dict], table: str) -> dict[str, dict]:
    return {r["id"]: {k: v for k, v in r.items() if k not in NAME_COLS[table]} for r in rows}


# Fixtures for the loader / interpret tests: a DB built like main, and a profile DB.


@pytest_asyncio.fixture
async def master(data_root):
    """Master DB built the way main builds it: master migrations, then the seed."""
    run_master_migrations()
    engine = create_async_engine(_async_url())
    maker = lambda: AsyncSession(engine, expire_on_commit=False)  # noqa: E731
    with patch.object(skb, "async_session_maker", maker):
        await skb.seed_all(skip_db_init=True)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


@pytest_asyncio.fixture
async def profile_db():
    engine = create_async_engine(
        "sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


def _module() -> tuple[InterpretModule, KnowledgeLoader]:
    # A fresh loader per test: the module-level one caches by analyte name.
    loader = KnowledgeLoader()
    module = InterpretModule(
        knowledge_loader=loader, recommendation_engine=RecommendationEngine(knowledge_loader=loader)
    )
    return module, loader


def _obs(analyte: str, value: float, ref_low, ref_high, unit: str, flag=None, **kw) -> Observation:
    base = dict(
        id=str(uuid.uuid4()), profile_id=PROFILE_ID, doc_id=str(uuid.uuid4()),
        analyte_canonical=analyte, analyte_raw=analyte, value=value, unit=unit,
        ref_low=ref_low, ref_high=ref_high, flag=flag, is_abnormal=flag in ("H", "L"),
        user_verified=True, collected_at=COLLECTED,
    )
    base.update(kw)
    return Observation(**base)


def _stored(raw: str) -> str:
    return NormalizeModule().normalize_analyte(raw).canonical_name


# ---------------------------------------------------------------------------
# HC-KCN-001: the real path, normalize -> KnowledgeLoader -> interpret
# ---------------------------------------------------------------------------

# raw lab label, name the normalizer stores for it
LABELS = [
    ("WBC", "white_blood_cells"),
    ("HbA1c", "hba1c"),
    ("A1C", "hba1c"),
    ("Hemoglobin A1c", "hba1c"),
    ("Glucose", "glucose"),
    ("Fasting Glucose", "glucose"),
]
LABEL_PARAMS = [pytest.param(raw, stored, id=raw) for raw, stored in LABELS]
# stored name -> (value, ref_low, ref_high, unit) for a high result
HIGH_RESULT = {
    "white_blood_cells": (12.0, 4.0, 11.0, "10^3/uL"),
    "hba1c": (7.2, 4.0, 5.6, "%"),
    "glucose": (130.0, 70.0, 100.0, "mg/dL"),
}


@pytest.mark.asyncio
@pytest.mark.parametrize("raw,expected", LABEL_PARAMS)
async def test_hc_kcn_001_stored_name_loads_its_knowledge_base_row(master, raw, expected):
    """Would not notice: a wrong text in the row (HC-KCN-006 pins the text)."""
    stored = _stored(raw)
    assert stored == expected, "precondition: the normalizer's name for this label changed"
    info = await KnowledgeLoader().get_biomarker_knowledge(stored, master)
    assert info is not None, f"no knowledge-base row for {raw!r}, stored as {stored!r}"
    assert info.analyte_canonical == stored
    assert info.high_interpretation and info.description


@pytest.mark.asyncio
@pytest.mark.parametrize("raw,expected", LABEL_PARAMS)
async def test_hc_kcn_001_interpret_context_and_result_carry_the_kb_text(
    master, profile_db, raw, expected
):
    """Would not notice: the HTTP layer around interpret_observation; it uses the same call."""
    stored = _stored(raw)
    value, lo, hi, unit = HIGH_RESULT[stored]
    obs = _obs(stored, value, lo, hi, unit, flag="H")
    profile_db.add(obs)
    await profile_db.commit()
    module, _ = _module()

    context = await module._assemble_context(obs, profile_db, master)
    info = context.biomarker_info
    assert info is not None, f"interpret context has no knowledge-base row for {raw!r} ({stored!r})"

    result = await module.interpret_observation(obs.id, profile_db, master)
    assert result.success, result.error_message
    card = result.interpretation.interpretation_text
    assert f"{info.high_interpretation} [KB:{info.id}]" in card
    assert f"{info.description} [KB:{info.id}]" in card
    citations = json.loads(result.interpretation.citations_json)
    assert any(c["type"] == "knowledge_base" and c["id"] == info.id for c in citations), citations


@pytest.mark.asyncio
async def test_hc_kcn_001_hba1c_high_gets_its_interventions(master, profile_db):
    """Would not notice: glucose and WBC have no interventions in the seed (none expected)."""
    stored = _stored("HbA1c")
    module, loader = _module()
    recs = await RecommendationEngine(knowledge_loader=loader).generate_recommendations(
        analyte_canonical=stored, value=7.2, ref_low=4.0, ref_high=5.6, db=master
    )
    assert {r.title for r in recs.recommendations} == {
        "Reduce Refined Carbohydrates", "Regular Physical Activity",
    }

    obs = _obs(stored, 7.2, 4.0, 5.6, "%", flag="H")
    profile_db.add(obs)
    await profile_db.commit()
    result = await module.interpret_observation(obs.id, profile_db, master)
    assert result.success, result.error_message
    advice = result.interpretation.advice_text or ""
    assert "Reduce Refined Carbohydrates" in advice and "[INT:" in advice, advice


# ---------------------------------------------------------------------------
# HC-KCN-002: every seeded analyte name is a name the normalizer can produce.
# normalize_analyte returns any unknown snake_case name unchanged, so
# normalize(name) == name cannot fail (tests/test_panel_canonical_names.py HC-PCN-006).
# The check is membership in ANALYTE_SYNONYMS, or a named exception with a reason.
# ---------------------------------------------------------------------------

NOT_SYNONYM_KEYS: dict[str, str] = {}  # none needed after the rename


def _seeded_analyte_names() -> dict[str, set[str]]:
    return {
        "biomarker_knowledge": {d["analyte_canonical"] for d in skb.BIOMARKER_DATA},
        "intervention_mappings": {d["analyte_canonical"] for d in skb.INTERVENTION_DATA},
        "biomarker_relationships": (
            {d["primary_analyte"] for d in skb.RELATIONSHIP_DATA}
            | {d["related_analyte"] for d in skb.RELATIONSHIP_DATA}
        ),
    }


def test_hc_kcn_002_every_seeded_name_is_a_synonym_key_or_a_named_exception():
    """Would not notice: a name that is a synonym key but spelled for another analyte, or a label
    that is not a synonym and reaches the snake_case fallback (HC-KCN-009 and the unmatched-label
    list in the PR body cover those; a synonym key says nothing about them)."""
    keys = set(NormalizeModule.ANALYTE_SYNONYMS)
    for table, names in _seeded_analyte_names().items():
        unexplained = sorted(names - keys - set(NOT_SYNONYM_KEYS))
        assert unexplained == [], f"{table}: names the normalizer never stores, with no reason: {unexplained}"


def test_hc_kcn_002_exceptions_are_still_seeded_and_not_synonym_keys():
    keys = set(NormalizeModule.ANALYTE_SYNONYMS)
    every = set().union(*_seeded_analyte_names().values())
    assert sorted(set(NOT_SYNONYM_KEYS) - every) == [], "exceptions no longer seeded, drop them"
    assert sorted(set(NOT_SYNONYM_KEYS) & keys) == [], "exceptions that are now synonym keys, drop them"


def test_hc_kcn_002_the_old_names_are_not_synonym_keys():
    """Control: the membership check does fail for the names this row removes. That is a statement
    about synonym KEYS only: a label with no synonym falls through to the snake_case fallback and
    is stored under that name (`Glucose Fasting` -> `glucose_fasting`), whatever the keys say."""
    assert set(RENAMES).isdisjoint(NormalizeModule.ANALYTE_SYNONYMS)
    assert set(RENAMES.values()) <= set(NormalizeModule.ANALYTE_SYNONYMS)


# ---------------------------------------------------------------------------
# HC-KCN-003: lipid ratio insights through interpret_panel
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hc_kcn_003_lipid_ratio_insights_attach_when_both_values_exist(master, profile_db):
    """Would not notice: the insight wording; HC-KCN-006 pins the seeded clinical_significance."""
    profile_db.add_all([
        _obs("total_cholesterol", 220.0, 0.0, 200.0, "mg/dL", flag="H"),
        _obs("hdl_cholesterol", 40.0, 40.0, 100.0, "mg/dL"),
        _obs("ldl_cholesterol", 150.0, 0.0, 100.0, "mg/dL", flag="H"),
    ])
    await profile_db.commit()
    module, _ = _module()

    result = await module.interpret_panel("lipid", COLLECTED, PROFILE_ID, profile_db, master)
    assert result.success, result.error_message
    panel = result.interpretation
    insights = {i["relationship"]: i for i in json.loads(panel.relationship_insights_json or "[]")}
    assert set(insights) == {
        "total_cholesterol_hdl_cholesterol_ratio",
        "ldl_cholesterol_hdl_cholesterol_ratio",
    }, insights
    assert insights["total_cholesterol_hdl_cholesterol_ratio"]["value"] == 5.5
    assert insights["ldl_cholesterol_hdl_cholesterol_ratio"]["value"] == 3.75
    # 5.5 and 3.75 are above the seed's `optimal` upper bounds (3.5 and 2.0): status `high`
    assert insights["total_cholesterol_hdl_cholesterol_ratio"]["status"] == "high"
    assert insights["ldl_cholesterol_hdl_cholesterol_ratio"]["status"] == "high"
    by_ratio = {
        (d["primary_analyte"], d["related_analyte"]): d["clinical_significance"]
        for d in skb.RELATIONSHIP_DATA if d["relationship_type"] == "ratio"
    }
    assert insights["total_cholesterol_hdl_cholesterol_ratio"]["interpretation"] == by_ratio[
        ("total_cholesterol", "hdl_cholesterol")
    ]
    # the five panel-relationship citations (interpret.py:437) attach too
    citations = json.loads(panel.citations_json)
    assert [c["type"] for c in citations] == ["relationship"] * 5, citations


# (total, hdl, ldl) -> (Total/HDL, LDL/HDL), and the status interpret.py:1172 gives each.
# interpret.py compares the ratio with the seed's `optimal` band only; the seed's `normal` band
# (Total/HDL 3.5-5.0, LDL/HDL 2.0-3.5) is never read. So a ratio inside `normal` returns `high`.
# The case below pins that CURRENT behaviour as evidence for the owner, it does not endorse it:
# PanelInterpretationDashboard.tsx:146,150 shows this status as a badge beside the raw label
# `total_cholesterol_hdl_cholesterol_ratio`, but not the value. The fix is a code change in
# modules/interpret.py, outside this row (L0 shows the owner as is, or opens a row). When that
# fix lands, the `normal-band` ids below change to "normal" in the same commit.
RATIO_STATUS_CASES = [
    pytest.param(150.0, 50.0, 90.0, 3.0, 1.8, "optimal", "optimal", id="optimal-band"),
    pytest.param(200.0, 50.0, 110.0, 4.0, 2.2, "high", "high", id="normal-band-reads-as-high"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("total,hdl,ldl,r_total,r_ldl,s_total,s_ldl", RATIO_STATUS_CASES)
async def test_hc_kcn_003_ratio_status_the_panel_badge_shows(
    master, profile_db, total, hdl, ldl, r_total, r_ldl, s_total, s_ldl
):
    """Would not notice: the badge rendering (PanelInterpretationDashboard.tsx); this reads the
    status interpret_panel hands it."""
    profile_db.add_all([
        _obs("total_cholesterol", total, 0.0, 200.0, "mg/dL"),
        _obs("hdl_cholesterol", hdl, 40.0, 100.0, "mg/dL"),
        _obs("ldl_cholesterol", ldl, 0.0, 100.0, "mg/dL"),
    ])
    await profile_db.commit()
    module, _ = _module()

    result = await module.interpret_panel("lipid", COLLECTED, PROFILE_ID, profile_db, master)
    assert result.success, result.error_message
    insights = {i["relationship"]: i for i in json.loads(result.interpretation.relationship_insights_json or "[]")}
    total_ratio = insights["total_cholesterol_hdl_cholesterol_ratio"]
    ldl_ratio = insights["ldl_cholesterol_hdl_cholesterol_ratio"]
    assert (total_ratio["value"], total_ratio["status"]) == (r_total, s_total)
    assert (ldl_ratio["value"], ldl_ratio["status"]) == (r_ldl, s_ldl)

    # Where the seed's own bands put these values (the evidence the owner compares against).
    bands = {
        (d["primary_analyte"], d["related_analyte"]): json.loads(d["ratio_target_range_json"])
        for d in skb.RELATIONSHIP_DATA if d["relationship_type"] == "ratio"
    }
    t_band = bands[("total_cholesterol", "hdl_cholesterol")]
    l_band = bands[("ldl_cholesterol", "hdl_cholesterol")]
    if s_total == "high":
        assert t_band["normal"][0] <= r_total <= t_band["normal"][1], "precondition: inside the seed's normal band"
        assert l_band["normal"][0] <= r_ldl <= l_band["normal"][1], "precondition: inside the seed's normal band"


@pytest.mark.asyncio
async def test_hc_kcn_003_a_ratio_needs_both_values(master, profile_db):
    """Control: with HDL missing no ratio is reported, so the test above is not a constant."""
    profile_db.add_all([
        _obs("total_cholesterol", 220.0, 0.0, 200.0, "mg/dL", flag="H"),
        _obs("ldl_cholesterol", 150.0, 0.0, 100.0, "mg/dL", flag="H"),
    ])
    await profile_db.commit()
    module, _ = _module()
    result = await module.interpret_panel("lipid", COLLECTED, PROFILE_ID, profile_db, master)
    assert result.success, result.error_message
    assert json.loads(result.interpretation.relationship_insights_json or "[]") == []


# ---------------------------------------------------------------------------
# HC-KCN-004: the HbA1c limit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hc_kcn_004_kb_limits_that_become_active(master):
    """Would not notice: whether a limit is clinically right; the owner sees them at the gate."""
    loader = KnowledgeLoader()
    limits = {}
    for raw in ("HbA1c", "WBC", "Glucose"):
        info = await loader.get_biomarker_knowledge(_stored(raw), master)
        assert info is not None, raw
        limits[info.analyte_canonical] = (info.critical_low, info.critical_high)
    assert limits == {
        "hba1c": (None, 10.0),
        "white_blood_cells": (2.0, 30.0),
        "glucose": (50.0, 400.0),
    }


@pytest.mark.asyncio
async def test_hc_kcn_004_hba1c_critical_high_flags_physician_review(master, profile_db):
    """Would not notice: unit mix-ups. The limit compares the raw value (mmol/mol 35 flags)."""
    guard = InterpretationSafetyGuard()
    # Control: the default table has no HbA1c entry, so the KB limit is the only source.
    assert "hba1c" not in guard.DEFAULT_CRITICAL_THRESHOLDS
    assert guard.check_critical_value("hba1c", 10.5).requires_physician_review is False

    info = await KnowledgeLoader().get_biomarker_knowledge(_stored("A1C"), master)
    assert info is not None and info.critical_high == 10.0 and info.critical_low is None
    flagged = guard.check_critical_value(
        "hba1c", 10.5, critical_low=info.critical_low, critical_high=info.critical_high
    )
    assert flagged.requires_physician_review is True
    assert flagged.physician_review_reason == "Critical high value: 10.5 is above critical threshold of 10.0"
    assert guard.check_critical_value(
        "hba1c", 9.5, critical_low=info.critical_low, critical_high=info.critical_high
    ).requires_physician_review is False

    # And through the real pipeline, as the card gets it.
    module, _ = _module()
    high = _obs("hba1c", 10.5, 4.0, 5.6, "%", flag="H")
    below = _obs("hba1c", 9.5, 4.0, 5.6, "%", flag="H")
    profile_db.add_all([high, below])
    await profile_db.commit()
    r_high = await module.interpret_observation(high.id, profile_db, master)
    r_below = await module.interpret_observation(below.id, profile_db, master)
    assert r_high.success and r_below.success, (r_high.error_message, r_below.error_message)
    assert r_high.interpretation.requires_physician_review is True
    assert r_high.interpretation.physician_review_reason == (
        "Critical high value: 10.5 is above critical threshold of 10.0"
    )
    assert r_high.interpretation.severity_level == "critical_high"
    assert r_below.interpretation.requires_physician_review is False
    assert r_below.interpretation.physician_review_reason is None


# ---------------------------------------------------------------------------
# HC-KCN-005: migration 003
# ---------------------------------------------------------------------------


def test_hc_kcn_005_revision_ids_and_a_single_master_head():
    script = ScriptDirectory.from_config(_cfg())
    assert script.get_heads() == ["003_kb_canonical_names"]
    rev = script.get_revision("003_kb_canonical_names")
    assert rev.down_revision == "002_backup_schedules"


def test_hc_kcn_005_migration_is_data_only_and_inserts_nothing():
    """Would not notice: an insert hidden behind a helper imported from elsewhere (imports are banned)."""
    source = MIGRATION_FILE.read_text(encoding="utf-8")
    assert not re.search(r"^\s*(from|import)\s+(models|scripts|modules|core|api)\b", source, re.M)
    assert not re.search(r"insert", source, re.I), "migration 003 must not insert rows"
    assert "Revision ID: 003_kb_canonical_names" in source
    assert "Revises: 002_backup_schedules" in source


def test_hc_kcn_005_old_name_db_is_renamed_with_the_same_row_count(data_root):
    _upgrade("002_backup_schedules")
    ids = _install_old_names()
    before = _dump()
    assert _counts(before) == {t: len(v) for t, v in ids.items()} and all(_counts(before).values())
    assert _keys(before) == _seed_keys(_as_old), "precondition: the installed rows carry the old names"

    _upgrade("head")
    after = _dump()

    assert _counts(after) == _counts(before)
    assert _keys(after) == _seed_keys(_as_new)
    for table in TABLES:
        # same ids (so a stored [KB:id] citation stays valid) and no other column moved
        assert _without_names(after[table], table) == _without_names(before[table], table), table
    assert Counter(r["panel_name"] for r in after["biomarker_relationships"]) == {
        "lipid": 5, "thyroid": 1, "diabetes": 1,
    }


def test_hc_kcn_005_second_run_is_a_no_op(data_root):
    """Alembic alone skips a revision it already applied, so stamp 002 and run the statements again."""
    _upgrade("002_backup_schedules")
    _install_old_names()
    before = _dump()
    _upgrade("head")
    first = _dump()
    assert first != before, "precondition: the first run changed something"

    command.stamp(_cfg(), "002_backup_schedules")
    _upgrade("head")
    assert _dump() == first


@pytest.mark.parametrize("table", TABLES)
def test_hc_kcn_005_old_and_new_row_both_present_ends_with_one(data_root, table):
    _upgrade("002_backup_schedules")
    old_ids = _install_old_names()
    # the same install also holds a row under every new name (ids differ)
    renamed_old = {
        "biomarker_knowledge": lambda r: r["analyte_canonical"] in RENAMES.values(),
        "intervention_mappings": lambda r: r["analyte_canonical"] in RENAMES.values(),
        "biomarker_relationships": lambda r: {r["primary_analyte"], r["related_analyte"]} & set(RENAMES.values()),
    }[table]
    new_rows = [r for r in _seed_rows(table, _as_new) if renamed_old(r)]
    assert new_rows, "precondition: the seed holds rows under a renamed name"
    new_ids = _insert(BIO if table == "biomarker_knowledge" else ITV if table == "intervention_mappings" else REL, new_rows)
    before = _dump()
    assert _counts(before)[table] == len(old_ids[table]) + len(new_rows)

    _upgrade("head")
    after = _dump()

    assert _counts(after)[table] == len(old_ids[table]), f"{table}: duplicates left behind"
    assert _keys(after)[table] == _seed_keys(_as_new)[table]
    assert max(_keys(after)[table].values()) == 1
    kept = {r["id"] for r in after[table]}
    assert set(new_ids) <= kept, "the row already under the new name is the one kept"
    old_renamed = [i for i, r in zip(old_ids[table], _seed_rows(table, _as_old)) if _as_new(r) in new_rows]
    assert old_renamed and kept.isdisjoint(old_renamed), "the old row of each collision is deleted"


def test_hc_kcn_005_same_title_under_another_condition_type_is_not_a_collision(data_root):
    """The intervention key is (analyte, condition_type, title): a row under the new name with the
    same title but another condition_type is a different row, so the old one is renamed, not deleted."""
    _upgrade("002_backup_schedules")
    old_ids = _install_old_names()
    old_rows = _seed_rows("intervention_mappings", _as_old)
    old_row = next(r for r in old_rows if r["analyte_canonical"] in RENAMES)
    other_type = next(
        t for t in ("high", "low", "borderline_high", "borderline_low") if t != old_row["condition_type"]
    )
    twin = {**_as_new(old_row), "condition_type": other_type}
    assert (twin["analyte_canonical"], twin["condition_type"], twin["intervention_title"]) not in _seed_keys(
        _as_new
    )["intervention_mappings"], "precondition: the twin is not a seeded row"
    twin_id = _insert(ITV, [twin])[0]
    before = _dump()
    assert _counts(before)["intervention_mappings"] == len(old_ids["intervention_mappings"]) + 1

    _upgrade("head")
    after = _dump()

    assert _counts(after)["intervention_mappings"] == len(old_ids["intervention_mappings"]) + 1
    keys = _keys(after)["intervention_mappings"]
    new_name = RENAMES[old_row["analyte_canonical"]]
    assert keys[(new_name, old_row["condition_type"], old_row["intervention_title"])] == 1
    assert keys[(new_name, other_type, old_row["intervention_title"])] == 1
    assert twin_id in {r["id"] for r in after["intervention_mappings"]}


@pytest.mark.parametrize("has_new", [False, True], ids=["no-new-row", "new-row-exists"])
@pytest.mark.parametrize(
    "primary,related",
    [("glucose_fasting", "hemoglobin_a1c"), ("glucose_fasting", "hba1c"), ("glucose", "hemoglobin_a1c")],
    ids=["old-old", "old-new", "new-old"],
)
def test_hc_kcn_005_relationship_with_one_old_name_and_one_new(data_root, primary, related, has_new):
    """primary_analyte and related_analyte can each need a rename in one row."""
    _upgrade("002_backup_schedules")
    base = next(r for r in _seed_rows("biomarker_relationships", _as_new) if r["relationship_type"] == "confirms")
    mixed = dict(base, primary_analyte=primary, related_analyte=related)
    mixed_id = _insert(REL, [mixed])[0]
    new_id = _insert(REL, [base])[0] if has_new else None

    _upgrade("head")
    rows = _dump()["biomarker_relationships"]

    assert [(r["primary_analyte"], r["related_analyte"], r["relationship_type"]) for r in rows] == [
        ("glucose", "hba1c", "confirms")
    ]
    assert rows[0]["id"] == (new_id if has_new else mixed_id)


def test_hc_kcn_005_seed_after_the_migration_adds_nothing_and_raises_nothing(data_root):
    """seed_intervention_mappings uses scalar_one_or_none: a duplicate key would raise at startup."""
    _upgrade("002_backup_schedules")
    _install_old_names()
    _upgrade("head")
    before = _dump()

    assert _run_seed() == (0, 0, 0)

    after = _dump()
    assert _counts(after) == _counts(before)
    assert all(max(c.values()) == 1 for c in _keys(after).values())


def test_hc_kcn_005_old_name_and_old_text_install_gets_revised_after_the_migration(data_root):
    """_TEXT_REVISIONS keys follow the rename: an install holding the old name AND the oldest text
    is migrated, then seeded, and its text is revised to the current seed text. A key left on the
    old name matches no row after the migration and the old text would stay."""
    oldest = {k: v for k, v in _oldest_texts().items() if k[0] in RENAMES.values()}
    assert {a for a, _ in oldest} == {"glucose", "white_blood_cells"}, "precondition: revisions to follow"
    _upgrade("002_backup_schedules")
    _install_old_names(old_text=True)

    def texts() -> dict[tuple[str, str], str]:
        rows = {r["analyte_canonical"]: r for r in _dump()["biomarker_knowledge"]}
        return {(a, f): rows[a][f] for a, f in oldest}

    _upgrade("head")
    assert texts() == oldest, "precondition: the migration moved the name, not the text"
    before = _dump()

    assert _run_seed() == (0, 0, 0)

    seeded = {d["analyte_canonical"]: d for d in map(_as_new, skb.BIOMARKER_DATA)}
    revised = texts()
    assert revised == {(a, f): seeded[a][f] for a, f in oldest}
    assert all(revised[k] != oldest[k] for k in oldest), "every old text was replaced"
    after = _dump()
    assert _counts(after) == _counts(before)
    # the revised rows kept their ids, so stored [KB:id] citations still resolve
    assert [r["id"] for r in after["biomarker_knowledge"]] == [r["id"] for r in before["biomarker_knowledge"]]


def test_hc_kcn_005_seed_after_a_collision_adds_nothing_and_raises_nothing(data_root):
    _upgrade("002_backup_schedules")
    _install_old_names()
    assert _run_seed() == (3, 2, 1)  # standalone seed: adds the renamed rows beside the old
    _upgrade("head")
    healed = _dump()

    assert _counts(healed) == {"biomarker_knowledge": 12, "intervention_mappings": 9, "biomarker_relationships": 7}
    assert _run_seed() == (0, 0, 0)
    assert _counts(_dump()) == _counts(healed)


def test_hc_kcn_005_accepted_path_standalone_seed_on_an_unmigrated_old_db(data_root):
    """The standalone script runs init_database() only. On an old DB it adds renamed rows beside the
    old ones; the next app start's migration 003 deletes the old row of each collision."""
    _upgrade("002_backup_schedules")
    _install_old_names()

    assert _run_seed() == (3, 2, 1)  # 3 biomarkers, 2 hba1c interventions, glucose->hba1c
    beside = _dump()
    assert _counts(beside) == {"biomarker_knowledge": 15, "intervention_mappings": 11, "biomarker_relationships": 8}
    # the five lipid rows are found by (primary, related, type) and skipped: still lipid_panel
    assert Counter(r["panel_name"] for r in beside["biomarker_relationships"])["lipid_panel"] == 5

    _upgrade("head")  # the next app start
    healed = _dump()
    assert _counts(healed) == {"biomarker_knowledge": 12, "intervention_mappings": 9, "biomarker_relationships": 7}
    assert _keys(healed) == _seed_keys(_as_new)
    assert Counter(r["panel_name"] for r in healed["biomarker_relationships"])["lipid"] == 5


def test_hc_kcn_005_accepted_path_baseline_stamp_never_runs_the_migration(data_root):
    """core/migrations.py:136-146 stamps a DB that has tables but no alembic_version to head, so
    003 never runs. The seed then adds renamed biomarker rows beside dead old ones and the lipid rows
    stay `lipid_panel` (status quo, no crash). The row does not name this path; no guard is added."""
    _upgrade("002_backup_schedules")
    _install_old_names()
    engine = create_engine(_sync_url())
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE alembic_version"))
    engine.dispose()

    run_master_migrations()  # tables, no alembic_version -> stamp head
    stamped = _dump()
    assert _keys(stamped) == _seed_keys(_as_old), "003 did not run: names are still the old ones"

    assert _run_seed() == (3, 2, 1)  # no crash
    after = _dump()
    assert _counts(after) == {"biomarker_knowledge": 15, "intervention_mappings": 11, "biomarker_relationships": 8}
    assert Counter(r["panel_name"] for r in after["biomarker_relationships"])["lipid_panel"] == 5


def test_hc_kcn_005_downgrade_round_trip(data_root):
    """Downgrade is the same logic with the maps inverted, so the old code's seed finds its rows."""
    run_master_migrations()
    assert _run_seed() == (12, 9, 7)
    head = _dump()
    assert _keys(head) == _seed_keys(_as_new)

    command.downgrade(_cfg(), "002_backup_schedules")
    down = _dump()
    assert _counts(down) == _counts(head)
    assert _keys(down) == _seed_keys(_as_old), "old code's seed keys all exist: it would add no second row"
    for table in TABLES:
        assert _without_names(down[table], table) == _without_names(head[table], table), table

    _upgrade("head")
    assert _dump() == head


def test_hc_kcn_005_downgrade_with_both_names_present_ends_with_one(data_root):
    run_master_migrations()
    assert _run_seed() == (12, 9, 7)
    glucose = next(r for r in _seed_rows("biomarker_knowledge", _as_old) if r["analyte_canonical"] == "glucose_fasting")
    old_id = _insert(BIO, [glucose])[0]  # a row under the old name beside the new one

    command.downgrade(_cfg(), "002_backup_schedules")
    rows = _dump()["biomarker_knowledge"]
    assert [r["id"] for r in rows if r["analyte_canonical"] == "glucose_fasting"] == [old_id]
    assert len(rows) == 12
    assert max(Counter(r["analyte_canonical"] for r in rows).values()) == 1


# ---------------------------------------------------------------------------
# HC-KCN-006: not a word of seeded text changed.
#
# Each digest is sha256 of the row's fields as sorted JSON with the name fields
# (analyte_canonical, primary_analyte, related_analyte, panel_name) removed. The pins were
# computed on origin/main d1f05349, before any rename, and are keyed by the NEW names. A later
# owner-approved reword of seeded text updates the pin in the same commit; nothing else may.
# ---------------------------------------------------------------------------

DIGEST_NAME_FIELDS = {"analyte_canonical", "primary_analyte", "related_analyte", "panel_name"}


def _digest(row: dict) -> str:
    body = {k: v for k, v in row.items() if k not in DIGEST_NAME_FIELDS}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _revision_digest(field: str, old: str, new: str) -> str:
    return hashlib.sha256(json.dumps([field, old, new]).encode()).hexdigest()


# PINS-BEGIN
BIOMARKER_DIGESTS = {
    "total_cholesterol": "e9a4d2169c9e48b2caf1b4f23a26a8f5abcff5ba47a88f03b1b763d92429cc0f",
    "ldl_cholesterol": "ba5e8372e1940648bcfe3710bb8ec94127b3b2294af55b9ce3f9db01604874d6",
    "hdl_cholesterol": "8db68be13f760c5cfa63f9aa1f73a10a2b794ef85445b469679815d819b96365",
    "triglycerides": "d1a83d1ead956e3c7078b5db3bb51fc593921a91b8b6a2b872dc975593a1388e",
    "glucose": "025cc89c951cae16486ed1922f608d728b5e23f1696b9f5599369cdeb758ab26",
    "hba1c": "2aecb9f8cf91edf96a8330785d4acc447d85460d9cfe618fb5b48f05e15efc8c",
    "hemoglobin": "a4819856d5df91efe1431e8e1a88f3ef589a8a2697c4ee8be0c20579151770e9",
    "white_blood_cells": "6cde84343bd624f4a6380b883aea1316b20aa8c2280321a43cc400507b7b2389",
    "platelets": "8b98ada6a7244a9e79b884596c43e705008f992a8cd9cc605b842061b6ad541d",
    "tsh": "cef2ca27e9f3039fe7d04ff392f0305b6806ea6ab43854b1da17eb719bd5d44c",
    "creatinine": "976421e76078ba3d3e83234e08dddac18171da889c60bdb17c878222525d1354",
    "vitamin_d": "7d0e47292cbbd48e5b9e2cfdc522fb1880a71dbb68ff5caac7a0614a8d346742",
}
INTERVENTION_DIGESTS = {
    ("ldl_cholesterol", "high", "Reduce Saturated Fat Intake"): "b95cc7019077eb8169fd884a63037b24615c6e3c0c9d78a3c4744d7df9094f99",
    ("ldl_cholesterol", "high", "Increase Soluble Fiber"): "565b0a5b653123cc8f90c1ff0642e9545f64cdd986269beaee13c03ea3127b0a",
    ("ldl_cholesterol", "high", "Regular Aerobic Exercise"): "6ee4bfb0a44b21cbeaf85c35b345ceda63925ccdd9005131aa6a1553e632edb9",
    ("hdl_cholesterol", "low", "Regular Aerobic Exercise"): "f97385f0f104581ab0a98dc8dbc443cd06ed45b9f282e709d704ee998f5de681",
    ("hdl_cholesterol", "low", "Quit Smoking"): "37946ae85e8109ace359e1fa31e0ea9e521abc5b0b96b39417bc5825d47fd28e",
    ("hba1c", "high", "Reduce Refined Carbohydrates"): "7bd7cf40e50e8ba2e0b749ae1efa77affdfa79290a6395f902fab4dcda2bf4c4",
    ("hba1c", "high", "Regular Physical Activity"): "2e7f4b69ab7f9d73a2f6c29fa6b32d12b5a281fcdd629b4d4ada504525f22252",
    ("vitamin_d", "low", "Vitamin D Supplementation"): "72e2d9963e3afbe7928c09996f59de9b27730a551fafc179014f9297b3d4855d",
    ("vitamin_d", "low", "Safe Sun Exposure"): "12c256311e72f91298adb9af8278e36b3a000fb2fb39214e02510827a47edaaa",
}
RELATIONSHIP_DIGESTS = {
    ("total_cholesterol", "hdl_cholesterol", "ratio"): "e541312abdfa44d0c0bd262816d58672f784dfaa0033ac91a4aa88dc2c608344",
    ("ldl_cholesterol", "hdl_cholesterol", "ratio"): "548affff3873683a70a7d0489fb8fc63ee9cb264eb0889c1833f3958fff4e6f3",
    ("ldl_cholesterol", "total_cholesterol", "panel_member"): "d3a7b10d43f55e0c160c6369d600693f0bc69952669964c645d461479e47fee9",
    ("hdl_cholesterol", "total_cholesterol", "panel_member"): "ba2b37b1f677b9ec546c7a9459023ee37c86326969f59423b00f8dbdc974ff0d",
    ("triglycerides", "total_cholesterol", "panel_member"): "61329b1a8a1f3e1855115a7c8b549ec65521ae78165781ccc832f0b371e7dc7f",
    ("tsh", "free_t4", "inverse_correlation"): "b535374498551c670d957c01525764b2205fb900925a8e077dd1578a90f34650",
    ("glucose", "hba1c", "confirms"): "4688e3ebcdb99275c31d0edcceba336fd7ef93da46b12b2f301246f8dffd4d4e",
}
REVISION_DIGESTS = [
    ("ldl_cholesterol", "d0315fccec94b5aab1279e3a3b8a6232f43f7212a4ccd654e234ab7db33595bb"),
    ("glucose", "da7d04834334bc2825280642a0906ae562111d18409bd7b1573902d1a84cda55"),
    ("total_cholesterol", "01e8a20c5c34b79f82c4f451bc52d5a479db81a37f66d44c062a01e97afda974"),
    ("total_cholesterol", "eea981992fa7db7270ae77e72837d1da02a778a099de97df812576e64513ea71"),
    ("ldl_cholesterol", "961ab318fd8621384213c6ff45459b424d5868e7ba25d686b2938ff64a345c0f"),
    ("glucose", "a63f17c1a24742acc7d4275d3f7610394bd97a8750beeb609226522cf778c0c4"),
    ("glucose", "8f296eaa215bb9bf1f2d407fc316e5d47b52bc427415bdf71aecac52ffba2ff7"),
    ("hemoglobin", "0f1f5a45a86e3cfdefd4d645e5d314b2145911e77ddc2e5d399fa7eaf4e1c8c1"),
    ("hemoglobin", "16e4b1c737f1be93a798e9760f0c140413a3ffb8cce43438edb40e3a9dcdb359"),
    ("white_blood_cells", "a07ff59acca0f1e6719c50fca06037c3d1713e50d69efa84dc443b58a12fed6d"),
    ("platelets", "c49d30caa3af305ca59025a1945ee263b3ed85b9e7ad193ff607d0df37f39364"),
    ("platelets", "9c63742f279eb91fff7448f12f206b17df0feec397b6844b6e82a1ff3cae45a9"),
    ("creatinine", "9b8454eeeca1ad46370d10f9c96a6b10e7898f0722c37f7cb5201f3c0e9bb1cd"),
    ("vitamin_d", "940dde570aa7f6bad861dafc2ba9f2965943f03f72ab707ce8524635a2226701"),
]
# PINS-END

PANEL_NAMES = {
    ("total_cholesterol", "hdl_cholesterol", "ratio"): "lipid",
    ("ldl_cholesterol", "hdl_cholesterol", "ratio"): "lipid",
    ("ldl_cholesterol", "total_cholesterol", "panel_member"): "lipid",
    ("hdl_cholesterol", "total_cholesterol", "panel_member"): "lipid",
    ("triglycerides", "total_cholesterol", "panel_member"): "lipid",
    ("tsh", "free_t4", "inverse_correlation"): "thyroid",
    # Named exception (queue row): no PANEL_DEFINITIONS key is called "diabetes", so it stays.
    ("glucose", "hba1c", "confirms"): "diabetes",
}


def test_hc_kcn_006_biomarker_text_is_unchanged():
    """Would not notice: a reword made in the same commit that edits the pin."""
    got = {d["analyte_canonical"]: _digest(d) for d in skb.BIOMARKER_DATA}
    assert got == BIOMARKER_DIGESTS


def test_hc_kcn_006_intervention_text_is_unchanged():
    got = {
        (d["analyte_canonical"], d["condition_type"], d["intervention_title"]): _digest(d)
        for d in skb.INTERVENTION_DATA
    }
    assert got == INTERVENTION_DIGESTS


def test_hc_kcn_006_relationship_text_is_unchanged_and_panels_are_as_decided():
    got = {
        (d["primary_analyte"], d["related_analyte"], d["relationship_type"]): _digest(d)
        for d in skb.RELATIONSHIP_DATA
    }
    assert got == RELATIONSHIP_DIGESTS
    panels = {
        (d["primary_analyte"], d["related_analyte"], d["relationship_type"]): d["panel_name"]
        for d in skb.RELATIONSHIP_DATA
    }
    assert panels == PANEL_NAMES
    # panels_json memberships keep the old spelling `lipid_panel` (inside the digest above too)
    lipid = [d for d in skb.BIOMARKER_DATA if d["category"] == "lipid"]
    assert lipid and all("lipid_panel" in json.loads(d["panels_json"]) for d in lipid)


def test_hc_kcn_006_text_revisions_are_unchanged_and_chain_to_a_seeded_row():
    """A _TEXT_REVISIONS key that follows no seeded row would silently stop revising text."""
    got = [(a, _revision_digest(f, o, n)) for a, f, o, n in skb._TEXT_REVISIONS]
    assert got == REVISION_DIGESTS
    seeded = {d["analyte_canonical"] for d in skb.BIOMARKER_DATA}
    assert sorted({a for a, *_ in skb._TEXT_REVISIONS} - seeded) == []


# ---------------------------------------------------------------------------
# HC-KCN-007: every text field that becomes reachable passes the prohibited patterns.
#
# DEPARTS FROM THE ROW ("every text passes"): 5 of the fields checked hit a prohibited pattern.
# The wording is not changed (L0: "Do not change wording to fit: show what patients would see")
# and the guard is not edited or relaxed. The hit set is pinned, with the reason per entry, so
# any new hit fails. Only entries starting `prohibited` count; the disclaimer check is for a
# whole card, not one field.
# ---------------------------------------------------------------------------

REACHABLE_BIOMARKERS = ("glucose", "hba1c", "white_blood_cells")
BIOMARKER_TEXT_FIELDS = (
    "display_name", "description", "clinical_significance",
    "normal_interpretation", "high_interpretation", "low_interpretation",
)
BIOMARKER_LIST_FIELDS = ("common_causes_high_json", "common_causes_low_json")

COMMON_CAUSES_WHY = (
    "common_causes is returned by GET /interpretations/knowledge/biomarker/{analyte} but rendered by "
    "no frontend component (only the type in services/types.ts mentions it); on the word 'Certain' "
    "('Certain medications', 'Certain hemoglobin variants')"
)
ABNORMAL_INTERP_WHY = (
    "abnormal_interpretation has no reader past knowledge_loader (it is copied into RelationshipInfo "
    "and nothing reads it) and the diabetes panel is not a PANEL_DEFINITIONS key, so get_panel_relationships "
    "is never called for it"
)
KNOWN_HITS = {
    ("biomarker:glucose", "common_causes_high_json"): {"prohibited_certainty_claims"},
    ("biomarker:hba1c", "common_causes_high_json"): {"prohibited_certainty_claims"},
    ("biomarker:hba1c", "common_causes_low_json"): {"prohibited_certainty_claims"},
    ("biomarker:white_blood_cells", "common_causes_low_json"): {"prohibited_certainty_claims"},
    ("relationship:glucose->hba1c:confirms", "abnormal_interpretation"): {"prohibited_diagnostic_language"},
}
KNOWN_HIT_REASONS = {
    **{k: COMMON_CAUSES_WHY for k in KNOWN_HITS if k[1].startswith("common_causes")},
    ("relationship:glucose->hba1c:confirms", "abnormal_interpretation"): ABNORMAL_INTERP_WHY,
}


def _strings(value) -> list[str]:
    """Every string inside a decoded JSON value, in order."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in _strings(v)]
    if isinstance(value, list):
        return [s for v in value for s in _strings(v)]
    return []


def _reachable_fields() -> dict[tuple[str, str], str]:
    fields: dict[tuple[str, str], str] = {}
    for d in map(_as_new, skb.BIOMARKER_DATA):
        if d["analyte_canonical"] not in REACHABLE_BIOMARKERS:
            continue
        subject = f"biomarker:{d['analyte_canonical']}"
        for f in BIOMARKER_TEXT_FIELDS:
            fields[(subject, f)] = d[f]
        for f in BIOMARKER_LIST_FIELDS:
            fields[(subject, f)] = "; ".join(json.loads(d[f]))
        # rag.py:559-560 puts this dict into the reference text as `Reference range: {dict}`
        fields[(subject, "ref_range_adult_json")] = f"Reference range: {json.loads(d['ref_range_adult_json'])}"
        # interpret.py:723 copies the sources into the card's citations
        fields[(subject, "sources_json")] = "; ".join(_strings(json.loads(d["sources_json"])))
    for d in map(_as_new, skb.INTERVENTION_DATA):
        if d["analyte_canonical"] != "hba1c":
            continue
        subject = f"intervention:{d['analyte_canonical']}:{d['intervention_title']}"
        for f in ("intervention_title", "intervention_text", "rationale", "category", "strength_of_evidence"):
            fields[(subject, f)] = d[f]
        fields[(subject, "sources_json")] = "; ".join(_strings(json.loads(d["sources_json"])))
        if d["contraindications_json"]:
            fields[(subject, "contraindications_json")] = "; ".join(json.loads(d["contraindications_json"]))
        if d["details_json"]:
            fields[(subject, "details_json")] = "; ".join(_strings(json.loads(d["details_json"])))
    for d in map(_as_new, skb.RELATIONSHIP_DATA):
        if d["panel_name"] != "lipid" and (d["primary_analyte"], d["related_analyte"]) != ("glucose", "hba1c"):
            continue
        subject = f"relationship:{d['primary_analyte']}->{d['related_analyte']}:{d['relationship_type']}"
        for f in ("description", "clinical_significance", "abnormal_interpretation"):
            if d[f]:
                fields[(subject, f)] = d[f]
        if d["ratio_target_range_json"]:
            bands = json.loads(d["ratio_target_range_json"])
            fields[(subject, "ratio_target_range_json")] = "; ".join(f"{k}: {v}" for k, v in bands.items())
        if d.get("sources_json"):
            fields[(subject, "sources_json")] = "; ".join(_strings(json.loads(d["sources_json"])))
    return fields


def test_hc_kcn_007_reachable_text_hits_exactly_the_named_set():
    """Would not notice: a hit split across two fields, or a pattern the guard does not have."""
    guard = InterpretationSafetyGuard()
    fields = _reachable_fields()
    hits: dict[tuple[str, str], set[str]] = {}
    for key, value in fields.items():
        result = guard.validate_interpretation(value, require_citations=False)
        prohibited = {c for c in result.checks_failed if c.startswith("prohibited")}
        if prohibited:
            hits[key] = prohibited

    print(f"\nHC-KCN-007: {len(fields)} fields checked, {len(hits)} hit")
    for key, kinds in sorted(hits.items()):
        print(f"  HIT {key[0]} / {key[1]}: {sorted(kinds)}\n      text: {fields[key]!r}")
    assert hits == KNOWN_HITS
    assert set(KNOWN_HIT_REASONS) == set(KNOWN_HITS)
    assert all(KNOWN_HIT_REASONS.values())


# The only files allowed to mention common_causes in the backend: the loader copies the column into
# BiomarkerInfo, and GET /interpretations/knowledge/biomarker/{analyte} returns it.
COMMON_CAUSES_BACKEND_ALLOWED = {"modules/knowledge_loader.py", "api/interpretations.py"}


def test_hc_kcn_007_the_named_hits_are_not_rendered_anywhere():
    """The reason the five hits are tolerated, as a check: a new reader of either field fails this.

    common_causes: any backend file under api/, modules/ or core/ other than the two allowed above,
    or any frontend file other than the type in services/types.ts. abnormal_interpretation: any
    mention of the word in api/, modules/ or core/ outside knowledge_loader.py (attribute, subscript
    or .get reader alike).

    GAP: this runs in the backend job. change_scope.py gives backend=false for a PR that touches
    only src/frontend (measured on ExplainAssistant.tsx), so a frontend-only PR that starts
    rendering common_causes does not run this test, and neither does HC-KCN-008. Closing it takes a
    BACKEND_RES line in scripts/change_scope.py, which this row does not edit; L0 decides.

    Would not notice: a reader that builds the name dynamically (getattr(info, 'common_' + ...)).
    """
    src = Path(__file__).resolve().parents[2]  # .../src

    frontend = [
        p for p in (src / "frontend" / "src").rglob("*")
        if p.suffix in (".ts", ".tsx") and "common_causes" in p.read_text(encoding="utf-8", errors="ignore")
    ]
    assert [p.name for p in frontend] == ["types.ts"], frontend

    causes, abnormal = [], []
    for folder in ("api", "modules", "core"):
        for p in (src / "backend" / folder).rglob("*.py"):
            rel = str(p.relative_to(src / "backend")).replace("\\", "/")
            body = p.read_text(encoding="utf-8", errors="ignore")
            if "common_causes" in body and rel not in COMMON_CAUSES_BACKEND_ALLOWED:
                causes.append(rel)
            if rel != "modules/knowledge_loader.py" and "abnormal_interpretation" in body:
                abnormal.append(rel)
    assert causes == [], f"common_causes now has a backend reader: {causes}"
    assert abnormal == [], f"abnormal_interpretation now has a reader: {abnormal}"


def test_hc_kcn_007_the_reader_scan_can_fail():
    """Control: the scan above finds the two allowed files, so an empty result is not a missed folder."""
    src = Path(__file__).resolve().parents[2] / "backend"
    found = {
        str(p.relative_to(src)).replace("\\", "/")
        for folder in ("api", "modules", "core")
        for p in (src / folder).rglob("*.py")
        if "common_causes" in p.read_text(encoding="utf-8", errors="ignore")
    }
    assert found == COMMON_CAUSES_BACKEND_ALLOWED


@pytest.mark.asyncio
@pytest.mark.parametrize("flag", ["H", "L", None], ids=["high", "low", "no-flag"])
@pytest.mark.parametrize("stored", REACHABLE_BIOMARKERS)
async def test_hc_kcn_007_the_cards_patients_get_are_not_withheld_and_hold_no_hit_text(
    master, profile_db, stored, flag
):
    """The text a card really renders (interpret_observation runs the whole safety check on it)."""
    value, lo, hi, unit = HIGH_RESULT[stored]
    if flag == "L":
        value = lo - 1
    elif flag is None:
        value = (lo + hi) / 2
    obs = _obs(stored, value, lo, hi, unit, flag=flag)
    profile_db.add(obs)
    await profile_db.commit()
    module, _ = _module()

    result = await module.interpret_observation(obs.id, profile_db, master)

    assert result.success and not result.withheld, (result.error_message, result.safety_validation)
    shown = f"{result.interpretation.interpretation_text}\n{result.interpretation.advice_text or ''}"
    row = next(d for d in map(_as_new, skb.BIOMARKER_DATA) if d["analyte_canonical"] == stored)
    for field in BIOMARKER_LIST_FIELDS:
        assert all(c not in shown for c in json.loads(row[field])), f"{field} reached the card"


# ---------------------------------------------------------------------------
# HC-KCN-008: the Explain chip for a stored `hba1c`
# ---------------------------------------------------------------------------

EXPLAIN_TSX = Path(__file__).resolve().parents[3] / "src" / "frontend" / "src" / "pages" / "ExplainAssistant.tsx"


def test_hc_kcn_008_chip_display_key_is_the_stored_name():
    """Parity read of the TSX (no frontend test file is in the row). Would not notice: rendering;
    tsc and a browser check cover that. The chips are built from stored names (`DISPLAY[a] ?? ...`)."""
    assert _stored("HbA1c") == "hba1c" and _stored("Glucose") == "glucose"
    source = EXPLAIN_TSX.read_text(encoding="utf-8")
    block = re.search(r"const DISPLAY: Record<string, string> = \{(.*?)\n\s*\};", source, re.S)
    assert block, "DISPLAY map not found"
    entries = dict(re.findall(r"^\s*(\w+):\s*'([^']*)'", block.group(1), re.M))
    assert entries.get("hba1c") == "A1C", entries
    assert "hemoglobin_a1c" not in entries, "the chip map is keyed by the stored `hba1c`, not the old name"
    assert entries.get("glucose") == "Glucose"
    assert "DISPLAY[a] ??" in source and "How's my ${name}?" in source


# ---------------------------------------------------------------------------
# HC-KCN-009: a result stored under an OLD name keeps its KB row and its critical limits.
#
# `Glucose Fasting` has no synonym, so the normalizer stores `glucose_fasting`. The default
# critical table has no such key, so the KB row was that result's only critical limit. The
# rename must not turn that flag off (review round 1 BLOCKER, ruling 6651067212). One alias
# map in the loader (and the biomarker route) reads the old stored names from the renamed row.
# These tests are NOT parametrised through LABELS: HC-KCN-001 asserts
# `info.analyte_canonical == stored`, and an aliased lookup returns the renamed row.
# ---------------------------------------------------------------------------

# (value, flag, severity) for a `Glucose Fasting` result stored as `glucose_fasting`
OLD_NAME_GLUCOSE = [
    pytest.param(450.0, "H", "critical_high", id="450-high"),
    pytest.param(40.0, "L", "critical_low", id="40-low"),
]


async def _interpret_stored(master, profile_db, analyte, value, lo, hi, unit, flag):
    """interpret_observation on a result stored under `analyte`; returns (context info, result)."""
    obs = _obs(analyte, value, lo, hi, unit, flag=flag)
    profile_db.add(obs)
    await profile_db.commit()
    module, _ = _module()
    context = await module._assemble_context(obs, profile_db, master)
    result = await module.interpret_observation(obs.id, profile_db, master)
    assert result.success, result.error_message
    return context.biomarker_info, result.interpretation


@pytest.mark.asyncio
@pytest.mark.parametrize("value,flag,severity", OLD_NAME_GLUCOSE)
async def test_hc_kcn_009_glucose_fasting_label_keeps_its_critical_flag_and_kb_text(
    master, profile_db, value, flag, severity
):
    """Would not notice: whether 50 / 400 are clinically right (the owner sees them at the gate).
    It would also not notice a second route to the same flag, so the control below pins that
    the default table has no `glucose_fasting` key and the KB row is the only source."""
    stored = _stored("Glucose Fasting")
    assert stored == "glucose_fasting", "precondition: the normalizer's name for this label changed"
    assert "glucose_fasting" not in InterpretationSafetyGuard().DEFAULT_CRITICAL_THRESHOLDS

    info, card = await _interpret_stored(master, profile_db, stored, value, 70.0, 100.0, "mg/dL", flag)
    assert info is not None, "no knowledge-base row for a result stored as glucose_fasting"
    assert card.requires_physician_review is True
    assert card.severity_level == severity
    assert card.physician_review_reason and "critical" in card.physician_review_reason.lower()
    text_ = info.high_interpretation if flag == "H" else info.low_interpretation
    assert f"{text_} [KB:{info.id}]" in card.interpretation_text
    assert f"{info.description} [KB:{info.id}]" in card.interpretation_text
    citations = json.loads(card.citations_json)
    assert any(c["type"] == "knowledge_base" and c["id"] == info.id for c in citations), citations


@pytest.mark.asyncio
async def test_hc_kcn_009_glucose_fasting_in_range_is_not_flagged(master, profile_db):
    """Control: the alias does not flag everything. Would not notice: a limit set too high."""
    info, card = await _interpret_stored(
        master, profile_db, "glucose_fasting", 90.0, 70.0, 100.0, "mg/dL", None
    )
    assert info is not None
    assert card.requires_physician_review is False
    assert card.severity_level == "normal"


@pytest.mark.asyncio
async def test_hc_kcn_009_hemoglobin_a1c_stored_literally_keeps_its_critical_flag_and_kb_text(
    master, profile_db
):
    """Would not notice: unit mix-ups (the limit compares the raw value). The default table has
    no hba1c / hemoglobin_a1c key, so the KB limit 10.0 is the only source."""
    guard = InterpretationSafetyGuard()
    assert "hemoglobin_a1c" not in guard.DEFAULT_CRITICAL_THRESHOLDS
    info, card = await _interpret_stored(
        master, profile_db, "hemoglobin_a1c", 10.5, 4.0, 5.6, "%", "H"
    )
    assert info is not None, "no knowledge-base row for a result stored as hemoglobin_a1c"
    assert card.requires_physician_review is True
    assert card.severity_level == "critical_high"
    assert card.physician_review_reason == "Critical high value: 10.5 is above critical threshold of 10.0"
    assert f"{info.high_interpretation} [KB:{info.id}]" in card.interpretation_text
    assert f"{info.description} [KB:{info.id}]" in card.interpretation_text

    # Control: below the limit, no review flag.
    _, below = await _interpret_stored(master, profile_db, "hemoglobin_a1c", 9.5, 4.0, 5.6, "%", "H")
    assert below.requires_physician_review is False


@pytest.mark.asyncio
async def test_hc_kcn_009_hemoglobin_a1c_high_gets_its_interventions(master, profile_db):
    """Would not notice: that the advice text is educational (HC-KCN-007 scans the text)."""
    _, loader = _module()
    recs = await RecommendationEngine(knowledge_loader=loader).generate_recommendations(
        analyte_canonical="hemoglobin_a1c", value=7.2, ref_low=4.0, ref_high=5.6, db=master
    )
    assert {r.title for r in recs.recommendations} == {
        "Reduce Refined Carbohydrates", "Regular Physical Activity",
    }
    _, card = await _interpret_stored(master, profile_db, "hemoglobin_a1c", 7.2, 4.0, 5.6, "%", "H")
    advice = card.advice_text or ""
    assert "Reduce Refined Carbohydrates" in advice and "[INT:" in advice, advice


@pytest.mark.asyncio
@pytest.mark.parametrize("old,new", sorted(RENAMES.items()))
async def test_hc_kcn_009_loader_returns_the_same_rows_for_the_old_and_the_new_name(master, old, new):
    """Would not notice: the three loader methods each have their own key line, so this calls
    each one. A fresh loader per call: the cache is keyed by the name, and a shared loader could
    answer the second call from the first call's entry."""
    bio_old = await KnowledgeLoader().get_biomarker_knowledge(old, master)
    bio_new = await KnowledgeLoader().get_biomarker_knowledge(new, master)
    assert bio_new is not None, f"no row under the new name {new!r}"
    assert bio_old == bio_new

    for condition in ("high", "low"):
        itv_old = await KnowledgeLoader().get_interventions(old, condition, master)
        itv_new = await KnowledgeLoader().get_interventions(new, condition, master)
        assert itv_old == itv_new, (old, condition)
        if (new, condition) == ("hba1c", "high"):
            assert len(itv_new) == 2, "control: the comparison is not between two empty lists"

    rel_old = await KnowledgeLoader().get_relationships(old, master)
    rel_new = await KnowledgeLoader().get_relationships(new, master)
    assert rel_old == rel_new
    if new in ("glucose", "hba1c"):
        assert rel_new, "control: the comparison is not between two empty lists"


@pytest.mark.asyncio
async def test_hc_kcn_009_one_loader_asked_for_both_names_gives_one_answer(master):
    """Would not notice: a cache keyed by the raw name (it would still be right, just twice).
    Catches a cache key built from one name and a query built from another."""
    loader = KnowledgeLoader()
    first = await loader.get_biomarker_knowledge("hemoglobin_a1c", master)
    second = await loader.get_biomarker_knowledge("HbA1c", master)
    assert first is not None and first == second
    i_first = await loader.get_interventions("hemoglobin_a1c", "high", master)
    i_second = await loader.get_interventions("hba1c", "high", master)
    assert i_first and i_first == i_second


@pytest.mark.parametrize("name", ["glucose_fasting", "hemoglobin_a1c", "wbc"])
def test_hc_kcn_009_biomarker_route_reads_old_and_new_names_the_same(data_root, name):
    """Through HTTP (route_client), real master session. The session is created here, in a sync
    test, and first connects inside the TestClient's loop. It is closed on that loop and the engine
    disposed before the test ends, so no connection worker thread is left running (measured).
    Would not notice: the response_model hiding a field; both bodies come from the same model."""
    from sqlalchemy.pool import NullPool

    from api.interpretations import router
    from tests.support.routes import route_client

    run_master_migrations()
    _run_seed()
    engine = create_async_engine(_async_url(), poolclass=NullPool)
    session = AsyncSession(engine, expire_on_commit=False)
    new = RENAMES[name]
    with route_client(router, "/interpretations", master_db=session) as client:
        old_resp = client.get(f"/interpretations/knowledge/biomarker/{name}")
        new_resp = client.get(f"/interpretations/knowledge/biomarker/{new}")
        shout = client.get(f"/interpretations/knowledge/biomarker/{name.upper()}")
        missing = client.get("/interpretations/knowledge/biomarker/not_a_biomarker")
        client.portal.call(session.close)
        client.portal.call(engine.dispose)
    assert new_resp.status_code == 200, new_resp.text
    assert old_resp.status_code == 200, old_resp.text
    assert old_resp.json() == new_resp.json()
    assert new_resp.json()["analyte_canonical"] == new
    assert shout.status_code == 200 and shout.json() == new_resp.json(), "lookup lower-cases first"
    assert missing.status_code == 404, missing.text


def test_hc_kcn_009_alias_map_equals_the_migration_renames():
    """Would not notice: a name the normalizer stores for a fourth analyte. HC-KCN-002 owns that.
    The import is inside the test so the file still collects when the map does not exist yet."""
    from modules.knowledge_loader import KB_ANALYTE_ALIASES, kb_lookup_name

    migration = ScriptDirectory.from_config(_cfg()).get_revision("003_kb_canonical_names").module
    assert dict(KB_ANALYTE_ALIASES) == migration.ANALYTE_RENAMES == RENAMES
    for old, new in RENAMES.items():
        assert kb_lookup_name(old) == new
        assert kb_lookup_name(old.upper()) == new
        assert kb_lookup_name(new) == new
    assert kb_lookup_name("Total_Cholesterol") == "total_cholesterol"


# ---------------------------------------------------------------------------
# HC-KCN-010..013: KB-UNIT-BADGE. Critical limits are in the KB's standard_unit; a value
# reported in another unit is converted with normalize.convert_to_canonical (D1) and compared
# only when the KB unit is that canonical unit. Unknown or missing unit: never critical.
# Would not notice (all four): whether a KB limit or a normalize factor is clinically right
# (owner-approved content, and normalize's own tests), nor unit spellings outside both tables
# (K/uL for WBC, HbA1c mmol/mol, TSH uIU/mL against a mIU/L limit): those are never critical.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hc_kcn_010_seeded_units_and_limits_are_as_planned(master):
    loader = KnowledgeLoader()
    got = {}
    for name in ("glucose", "creatinine", "hba1c", "tsh"):
        info = await loader.get_biomarker_knowledge(name, master)
        got[name] = (info.standard_unit, info.critical_low, info.critical_high)
    assert got == {
        "glucose": ("mg/dL", 50.0, 400.0),
        "creatinine": ("mg/dL", None, 10.0),
        "hba1c": ("%", None, 10.0),
        "tsh": ("mIU/L", 0.1, 10.0),
    }


# analyte, value, unit, ref_lo, ref_hi, expected
UNIT_BADGE_CASES = {
    "same-unit-critical-high": ("glucose", 450.0, "mg/dL", 70, 100, "critical_high"),
    "same-unit-case-and-space": ("glucose", 450.0, " MG/DL ", 70, 100, "critical_high"),
    "same-unit-hba1c": ("hba1c", 10.5, "%", 4.0, 5.6, "critical_high"),
    "same-unit-tsh": ("tsh", 12.0, "mIU/L", 0.4, 4.0, "critical_high"),
    "converted-critical-high-direction": ("glucose", 25.0, "mmol/L", 3.9, 5.6, "critical_high"),
    "converted-critical-low": ("glucose", 2.5, "mmol/L", 3.9, 5.6, "critical_low"),
    "converted-not-critical": ("glucose", 7.0, "mmol/L", 3.9, 5.6, "abnormal_high"),
    "converted-creatinine-not-critical": ("creatinine", 500.0, "umol/L", 62, 106, "abnormal_high"),
    "converted-creatinine-critical": ("creatinine", 1000.0, "umol/L", 62, 106, "critical_high"),
    "unknown-unit-low-number": ("glucose", 4.5, "g/L", 0.7, 1.0, "abnormal_high"),
    "unknown-unit-huge-number": ("glucose", 450.0, "mg%", 70, 100, "abnormal_high"),
    "missing-unit-none": ("glucose", 450.0, None, 70, 100, "abnormal_high"),
    "missing-unit-empty": ("glucose", 450.0, "", 70, 100, "abnormal_high"),
    "missing-unit-blank": ("glucose", 40.0, "   ", 70, 100, "abnormal_low"),
    "hba1c-mmol-mol-normal": ("hba1c", 35.0, "mmol/mol", 20, 42, "normal"),
    "hba1c-mmol-mol-high-never-critical": ("hba1c", 120.0, "mmol/mol", 20, 42, "abnormal_high"),
    "tsh-other-unit-than-the-limit-never-critical": ("tsh", 12.0, "uIU/mL", 0.4, 4.0, "abnormal_high"),
}


@pytest.mark.asyncio
@pytest.mark.parametrize("case", list(UNIT_BADGE_CASES), ids=list(UNIT_BADGE_CASES))
async def test_hc_kcn_010_critical_badge_compares_in_the_limit_unit(master, case):
    analyte, value, unit, lo, hi, expected = UNIT_BADGE_CASES[case]
    info = await KnowledgeLoader().get_biomarker_knowledge(analyte, master)
    assert info is not None
    module, _ = _module()
    assert module._classify_severity(value, lo, hi, info, unit=unit) == expected


@pytest.mark.asyncio
async def test_hc_kcn_010_the_old_hba1c_name_is_never_critical_in_mmol_per_mol_either(master):
    info = await KnowledgeLoader().get_biomarker_knowledge("hemoglobin_a1c", master)
    assert info is not None
    module, _ = _module()
    assert module._classify_severity(120.0, 20, 42, info, unit="mmol/mol") == "abnormal_high"


@pytest.mark.asyncio
@pytest.mark.parametrize("unit", ["mg/dL", "g/L", None])
@pytest.mark.parametrize(
    "value,expected",
    [(85, "normal"), (105, "borderline_high"), (130, "abnormal_high"),
     (65, "borderline_low"), (55, "abnormal_low")],
)
async def test_hc_kcn_010_range_classification_is_unchanged(master, value, expected, unit):
    """The unit decides the critical step only, never the range step (also with no KB row)."""
    info = await KnowledgeLoader().get_biomarker_knowledge("glucose", master)
    module, _ = _module()
    assert module._classify_severity(value, 70, 100, info, unit=unit) == expected
    assert module._classify_severity(value, 70, 100, None, unit=unit) == expected


@pytest.mark.asyncio
async def test_hc_kcn_011_interpret_observation_card_badge_uses_the_unit(master, profile_db):
    for value, severity in ((7.0, "abnormal_high"), (25.0, "critical_high")):
        _, card = await _interpret_stored(master, profile_db, "glucose", value, 3.9, 5.6, "mmol/L", "H")
        assert card.severity_level == severity, value


@pytest.mark.asyncio
async def test_hc_kcn_011_interpret_with_model_passes_the_unit(master, profile_db):
    obs = _obs("glucose", 7.0, 3.9, 5.6, "mmol/L", flag="H")
    profile_db.add(obs)
    await profile_db.commit()
    selector = MagicMock()
    selector.get_model_for_inference = AsyncMock(return_value=(object(), "standard"))
    selector.run_inference = AsyncMock(return_value={"choices": [{"text": "Glucose is above range."}]})
    module = InterpretModule(knowledge_loader=KnowledgeLoader(), model_selector=selector)
    with patch.object(module, "_classify_severity", wraps=module._classify_severity) as spy:
        await module.interpret_with_model(
            observation_id=obs.id, profile_id=PROFILE_ID, profile_db=profile_db, master_db=master
        )
    spy.assert_called_once()
    assert spy.call_args.kwargs["unit"] == "mmol/L"


# unit, value, severity, does the banner fire
BANNER_CASES = {
    "same-unit": ("mg/dL", 450.0, "critical_high", True),
    "converted-critical": ("mmol/L", 25.0, "critical_high", True),
    "converted-not-critical": ("mmol/L", 7.0, "abnormal_low", False),
    "unknown-unit": ("g/L", 4.5, "abnormal_low", False),
    "missing-unit": (None, 450.0, "abnormal_high", False),
}


@pytest.mark.asyncio
@pytest.mark.parametrize("case", list(BANNER_CASES), ids=list(BANNER_CASES))
async def test_hc_kcn_012_banner_follows_the_badge_unit_rule(master, profile_db, case):
    from modules.normalize import convert_to_canonical

    unit, value, severity, fires = BANNER_CASES[case]
    info, card = await _interpret_stored(master, profile_db, "glucose", value, 70.0, 100.0, unit, "H")
    assert card.severity_level == severity
    assert bool(card.requires_physician_review) is fires
    assert (card.severity_level.startswith("critical")) == bool(card.requires_physician_review)
    if fires:
        in_kb_unit = value if unit == "mg/dL" else convert_to_canonical("glucose", value, unit).canonical_value
        expected = InterpretationSafetyGuard().check_critical_value(
            "glucose", in_kb_unit, info.critical_low, info.critical_high
        ).physician_review_reason
        assert card.physician_review_reason == expected
        assert expected.startswith("Critical high value: ")
        assert expected.endswith(" is above critical threshold of 400.0")
    else:
        assert card.physician_review_reason is None

@pytest.mark.asyncio
async def test_hc_kcn_013_a_saved_wrong_severity_card_is_rebuilt_on_read(master, profile_db):
    _, card = await _interpret_stored(master, profile_db, "glucose", 7.0, 3.9, 5.6, "mmol/L", "H")
    assert card.severity_level == "abnormal_high"
    card.severity_level = "critical_low"  # what the unit-blind rule saved for this value
    await profile_db.commit()
    saved_id = card.id

    module, _ = _module()
    result = await module.interpret_observation(card.observation_id, profile_db, master)
    assert result.success
    assert result.interpretation.id != saved_id
    assert result.interpretation.severity_level == "abnormal_high"
    assert result.interpretation.previous_interpretation_id == saved_id


@pytest.mark.asyncio
async def test_hc_kcn_013_a_saved_card_with_matching_severity_is_not_rebuilt(master, profile_db):
    _, card = await _interpret_stored(master, profile_db, "glucose", 25.0, 3.9, 5.6, "mmol/L", "H")
    assert card.severity_level == "critical_high"
    module, _ = _module()
    with patch.object(module, "_generate_interpretation", wraps=module._generate_interpretation) as gen:
        result = await module.interpret_observation(card.observation_id, profile_db, master)
    assert result.interpretation.id == card.id
    gen.assert_not_called()


@pytest.mark.asyncio
async def test_hc_kcn_013_a_saved_missed_critical_is_rebuilt_on_read(master, profile_db):
    """A template card saved as abnormal_* for a value the unit rule calls critical."""
    _, card = await _interpret_stored(master, profile_db, "glucose", 25.0, 3.9, 5.6, "mmol/L", "H")
    assert card.severity_level == "critical_high"
    card.severity_level = "abnormal_high"
    await profile_db.commit()
    saved_id = card.id
    result = await _module()[0].interpret_observation(card.observation_id, profile_db, master)
    assert result.interpretation.id != saved_id
    assert result.interpretation.severity_level == "critical_high"


@pytest.mark.asyncio
async def test_hc_kcn_013_a_saved_non_critical_mismatch_is_not_rebuilt(master, profile_db):
    _, card = await _interpret_stored(master, profile_db, "glucose", 7.0, 3.9, 5.6, "mmol/L", "H")
    assert card.severity_level == "abnormal_high"
    card.severity_level = "normal"
    await profile_db.commit()
    result = await _module()[0].interpret_observation(card.observation_id, profile_db, master)
    assert result.interpretation.id == card.id
    assert result.interpretation.severity_level == "normal"


@pytest.mark.asyncio
async def test_hc_kcn_013_a_same_unit_critical_mismatch_is_not_rebuilt(master, profile_db):
    """(c): a same-unit result's new rule equals the old one, so a difference is a KB revision."""
    _, card = await _interpret_stored(master, profile_db, "glucose", 450.0, 70.0, 100.0, "mg/dL", "H")
    assert card.severity_level == "critical_high"
    card.severity_level = "normal"
    await profile_db.commit()
    result = await _module()[0].interpret_observation(card.observation_id, profile_db, master)
    assert result.interpretation.id == card.id
    assert result.interpretation.severity_level == "normal"


@pytest.mark.asyncio
async def test_hc_kcn_013_a_missing_unit_card_saved_critical_is_rebuilt(master, profile_db):
    _, card = await _interpret_stored(master, profile_db, "glucose", 450.0, 70.0, 100.0, None, "H")
    assert card.severity_level == "abnormal_high"
    card.severity_level = "critical_high"  # what the unit-blind rule saved
    await profile_db.commit()
    saved_id = card.id
    result = await _module()[0].interpret_observation(card.observation_id, profile_db, master)
    assert result.interpretation.id != saved_id
    assert result.interpretation.severity_level == "abnormal_high"
    assert not result.interpretation.requires_physician_review
