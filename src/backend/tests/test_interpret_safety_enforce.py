"""INTERP-SAFETY-ENFORCE: a lab card that fails the safety check is withheld,
and no built-in (seeded) card fails that check.

Plan: docs/plans/2026-10-15-build-program/lane-B-interpretation-eval.md,
"Delta 2026-10-30" and "Delta 2026-10-30b" (ISE-DISC-SCOPE, ISE-SEED-HITS).

HC-ISE-005 / HC-ISE-006: the reworded seed text (Task 1).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import models  # noqa: F401  (registers tables on Base.metadata)
from core.database import Base
from core.profile_database import ProfileDatabaseBase
from models import InterventionMapping, Observation
from models.knowledge_base import BiomarkerKnowledge
from modules.interpret import InterpretModule
from modules.knowledge_loader import get_knowledge_loader


# Copied from tests/test_biomarker_assistant.py (not imported across test modules).
@pytest_asyncio.fixture
async def real_master_session():
    """Real sqlite master DB (tables created from the ORM), not a mock."""
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
    return lambda: AsyncSession(engine, expire_on_commit=False)


# ──────────────────────────────────────────────────────────────────────────────
# HC-ISE-005: every seeded card passes the unchanged guard
# ──────────────────────────────────────────────────────────────────────────────

# (name, flag, is_abnormal, value) against a 10-20 reference range.
_FLAG_CASES = (
    ("H", "H", True, 30.0),
    ("L", "L", True, 5.0),
    ("none", None, False, 15.0),
    ("other", "A", True, 30.0),
)
_CASES_PER_PASS = 48  # 12 seeded analytes x 4 flag states


async def _run_every_seeded_card(engine, label: str) -> tuple[int, list[str]]:
    """Run interpret_observation for every seeded analyte x flag state."""
    from scripts.seed_knowledge_base import BIOMARKER_DATA

    module = InterpretModule()
    cases = 0
    failures: list[str] = []
    for data in BIOMARKER_DATA:
        analyte = data["analyte_canonical"]
        for flag_name, flag, abnormal, value in _FLAG_CASES:
            cases += 1
            p_engine = create_async_engine("sqlite+aiosqlite://")
            async with p_engine.begin() as conn:
                await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
            profile_db = AsyncSession(p_engine, expire_on_commit=False)
            master_db = AsyncSession(engine, expire_on_commit=False)
            try:
                obs_id = str(uuid.uuid4())
                profile_db.add(
                    Observation(
                        id=obs_id, profile_id=f"profile-ise-{cases}",
                        doc_id=str(uuid.uuid4()), analyte_canonical=analyte,
                        analyte_raw=analyte, value=value, unit="mg/dL",
                        ref_low=10.0, ref_high=20.0, flag=flag,
                        is_abnormal=abnormal, user_verified=True,
                        collected_at=datetime(2026, 3, 1),
                    )
                )
                await profile_db.commit()
                result = await module.interpret_observation(
                    observation_id=obs_id, profile_db=profile_db, master_db=master_db,
                )
                if result.safety_validation is None:
                    failures.append(f"{label}: ({analyte}, {flag_name}) no safety_validation")
                elif not result.safety_validation.passed:
                    failures.append(
                        f"{label}: ({analyte}, {flag_name}) "
                        f"checks_failed={result.safety_validation.checks_failed}"
                    )
            finally:
                await profile_db.close()
                await master_db.close()
                await p_engine.dispose()
    return cases, failures


@pytest.mark.asyncio
async def test_hc_ise_005_every_seeded_card_passes_the_guard(real_master_session):
    from scripts import seed_knowledge_base as skb

    session, engine = real_master_session
    with patch.object(skb, "async_session_maker", _session_maker_for(engine)):
        await skb.seed_all(skip_db_init=True)

    loader = get_knowledge_loader()
    failures: list[str] = []
    try:
        # Pass 1: with the seeded interventions (cards carry recommendations).
        loader.clear_cache()  # the process-wide cache would hide the DB rows
        cases_with, f_with = await _run_every_seeded_card(engine, "with interventions")
        failures += f_with

        # Pass 2: no interventions, so a card has no recommendation disclaimer.
        await session.execute(delete(InterventionMapping))
        await session.commit()
        loader.clear_cache()
        cases_without, f_without = await _run_every_seeded_card(
            engine, "without interventions"
        )
        failures += f_without
    finally:
        loader.clear_cache()

    # A shrinking loop must not pass.
    assert cases_with == _CASES_PER_PASS, cases_with
    assert cases_without == _CASES_PER_PASS, cases_without
    assert not failures, f"{len(failures)} seeded card(s) fail the guard:\n" + "\n".join(
        failures
    )


# ──────────────────────────────────────────────────────────────────────────────
# HC-ISE-006: installed rows pick up the reworded text
# ──────────────────────────────────────────────────────────────────────────────

# Hard-coded on purpose: never import these from _TEXT_REVISIONS, or a typo there
# would also be a typo here and the test could not fail.
# (analyte, field, exact text installed before this change)
_OLD_TEXTS = (
    (
        "total_cholesterol", "high_interpretation",
        "Elevated total cholesterol may increase your risk of heart disease. "
        "Your healthcare provider will consider this alongside your LDL, HDL, "
        "and other risk factors to assess your cardiovascular health.",
    ),
    (
        "total_cholesterol", "low_interpretation",
        "Very low cholesterol is uncommon but may be associated with certain "
        "conditions. Your healthcare provider can help determine if further "
        "evaluation is needed.",
    ),
    (
        "ldl_cholesterol", "high_interpretation",
        "Elevated LDL cholesterol increases your risk of plaque buildup in "
        "arteries. Your healthcare provider can explain what this result means "
        "for you.",
    ),
    (
        "glucose_fasting", "high_interpretation",
        "Elevated fasting glucose may indicate prediabetes or diabetes. "
        "Your healthcare provider can explain whether further testing is needed.",
    ),
    (
        "glucose_fasting", "low_interpretation",
        "Low blood glucose (hypoglycemia) can cause symptoms like shakiness, "
        "confusion, and fatigue. Causes include certain medications, missed "
        "meals, or underlying conditions.",
    ),
    (
        "hemoglobin", "high_interpretation",
        "Elevated hemoglobin may indicate dehydration, lung disease, heart "
        "disease, or polycythemia. Your healthcare provider may recommend "
        "further evaluation.",
    ),
    (
        "hemoglobin", "low_interpretation",
        "Low hemoglobin indicates anemia, which can cause fatigue, weakness, "
        "and shortness of breath. There are many potential causes including "
        "iron deficiency, vitamin deficiencies, or chronic diseases.",
    ),
    (
        "wbc", "low_interpretation",
        "Low WBC (leukopenia) can increase infection risk. Causes include "
        "viral infections, bone marrow problems, autoimmune conditions, or "
        "certain medications.",
    ),
    (
        "platelets", "low_interpretation",
        "Low platelets (thrombocytopenia) can increase bleeding risk. Causes "
        "include viral infections, certain medications, autoimmune conditions, "
        "or bone marrow problems.",
    ),
    (
        "platelets", "description",
        "Platelets (thrombocytes) are blood cells that help your blood clot. "
        "They stick together to form clots that stop bleeding when you have a "
        "cut or injury.",
    ),
    (
        "creatinine", "high_interpretation",
        "Elevated creatinine may indicate reduced kidney function. However, "
        "levels can also be affected by muscle mass, diet, and hydration. "
        "Your healthcare provider will interpret this in context.",
    ),
    (
        "vitamin_d", "description",
        "Vitamin D is essential for calcium absorption and bone health. Your "
        "body makes it when skin is exposed to sunlight, and you can get it "
        "from certain foods and supplements.",
    ),
)

# Texts installed before INTERP-ADVICE-WORDING: they revise twice in one seed
# pass (pre-IAW -> IAW text -> this change's text).
_PRE_IAW_TEXTS = (
    (
        "ldl_cholesterol", "high_interpretation",
        "Elevated LDL cholesterol increases your risk of plaque buildup in "
        "arteries. Lifestyle changes and possibly medication may help reduce "
        "this risk.",
    ),
    (
        "glucose_fasting", "high_interpretation",
        "Elevated fasting glucose may indicate prediabetes or diabetes. "
        "Further testing and lifestyle modifications may be recommended.",
    ),
)


async def _install_rows_with(session, overrides) -> None:
    """Insert one row per seeded analyte, with `overrides` as its stored text."""
    from scripts.seed_knowledge_base import BIOMARKER_DATA

    for data in BIOMARKER_DATA:
        row = dict(data)
        for analyte, field, text in overrides:
            if analyte == data["analyte_canonical"]:
                row[field] = text
        session.add(BiomarkerKnowledge(id=str(uuid.uuid4()), **row))
    await session.commit()


async def _stored(engine, analyte: str, field: str) -> str:
    async with AsyncSession(engine, expire_on_commit=False) as s:
        row = (
            await s.execute(
                select(BiomarkerKnowledge).where(
                    BiomarkerKnowledge.analyte_canonical == analyte
                )
            )
        ).scalar_one()
        return getattr(row, field)


@pytest.mark.asyncio
async def test_hc_ise_006_installed_rows_pick_up_reworded_text(real_master_session):
    from scripts import seed_knowledge_base as skb
    from scripts.seed_knowledge_base import BIOMARKER_DATA

    session, engine = real_master_session
    current = {d["analyte_canonical"]: d for d in BIOMARKER_DATA}
    problems: list[str] = []

    async def _seed_and_check(scenario: str, installed) -> None:
        with patch.object(skb, "async_session_maker", _session_maker_for(engine)):
            await skb.seed_all(skip_db_init=True)
        for analyte, field, installed_text in installed:
            stored = await _stored(engine, analyte, field)
            if stored != current[analyte][field]:
                problems.append(f"{scenario}: ({analyte}, {field}) not at the current text")
            if stored == installed_text:
                problems.append(f"{scenario}: ({analyte}, {field}) was not revised")

    # Scenario A: every row holds the exact text installed before this change.
    await _install_rows_with(session, _OLD_TEXTS)
    await _seed_and_check("installed", _OLD_TEXTS)

    # Scenario B: LDL-high and glucose-high hold the pre-IAW text, so the chain
    # (two revisions in one pass) has to land on the current text.
    await session.execute(delete(BiomarkerKnowledge))
    await session.commit()
    await _install_rows_with(session, _PRE_IAW_TEXTS)
    await _seed_and_check("pre-IAW", _PRE_IAW_TEXTS)
    for analyte, field, _ in _PRE_IAW_TEXTS:
        iaw_text = next(t for a, f, t in _OLD_TEXTS if (a, f) == (analyte, field))
        if await _stored(engine, analyte, field) == iaw_text:
            problems.append(f"pre-IAW: ({analyte}, {field}) stopped at the IAW text")

    assert len(_OLD_TEXTS) == 12
    assert not problems, "\n".join(problems)
