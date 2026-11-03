"""VERIFY-KEEPS-FLAG: a plain Verify keeps the stored flag unless it is normal.

POST /observations/{id}/verify used to recompute flag/is_abnormal from
value vs ref_low/ref_high on every call. A report's own flag ("CRITICAL",
or "H" with no printed range) was erased by a Verify click that changed
nothing. The flag is recalculated only when this request really changes
value, ref_low or ref_high, or when the row has no flag or a normal word
(NORMAL, N, WNL after strip().upper(); see 008 and 010). Any other stored
flag is kept with its is_abnormal, even one that disagrees with the number
(009, 011, 012). Every case goes through HTTP and asserts the STORED
columns, not only the response.
"""

import json
import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import api.export as export_api
import api.observations as obs_api
from core.auth import get_profile_db_session
from core.profile_database import ProfileDatabaseBase
from models import Document, Observation
from tests.support.routes import route_client

PROFILE = "profile-a"
OBS_AT = datetime(2026, 3, 1, 19, 45)


@pytest_asyncio.fixture
async def profile_db():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


async def _seed_obs(db: AsyncSession, *, flag, is_abnormal, value, ref_low, ref_high,
                    user_verified=False) -> str:
    doc_id, obs_id = str(uuid.uuid4()), str(uuid.uuid4())
    db.add(Document(
        id=doc_id, profile_id=PROFILE, path_hash="p" * 64, content_hash="c" * 64,
        doc_type="lab_report", status="verified", imported_at=OBS_AT,
    ))
    db.add(Observation(
        id=obs_id, profile_id=PROFILE, doc_id=doc_id, analyte_canonical="hemoglobin",
        analyte_raw="Hemoglobin", value=value, unit="g/dL", ref_low=ref_low,
        ref_high=ref_high, flag=flag, is_abnormal=is_abnormal, user_verified=user_verified,
        collected_at=OBS_AT,
    ))
    await db.commit()
    return obs_id


def _get(router, prefix, profile_db, method, url, master_db=None, **kwargs):
    with route_client(router, prefix, profile_id=PROFILE, master_db=master_db) as client:
        async def _override_profile_db():
            return profile_db

        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        return client.request(method, url, **kwargs)


async def _verify_and_load(profile_db, obs_id, body) -> Observation:
    """POST verify, assert 200, then re-read the stored row from the DB."""
    resp = _get(obs_api.router, "/observations", profile_db, "POST",
                f"/observations/{obs_id}/verify", json=body)
    assert resp.status_code == 200, resp.text
    profile_db.expire_all()
    obs = (
        await profile_db.execute(select(Observation).where(Observation.id == obs_id))
    ).scalar_one()
    # A kept flag must not come from a verify that did nothing.
    assert obs.user_verified is True
    return obs


@pytest.mark.asyncio
async def test_hc_vkf_001_critical_flag_kept_when_value_in_range(profile_db):
    obs_id = await _seed_obs(profile_db, flag="CRITICAL", is_abnormal=True,
                             value=14.0, ref_low=12.0, ref_high=16.0)
    obs = await _verify_and_load(profile_db, obs_id, {})
    assert obs.flag == "CRITICAL"
    assert obs.is_abnormal is True


@pytest.mark.asyncio
async def test_hc_vkf_002_flag_kept_when_report_printed_no_range(profile_db):
    obs_id = await _seed_obs(profile_db, flag="H", is_abnormal=True,
                             value=14.0, ref_low=None, ref_high=None)
    obs = await _verify_and_load(profile_db, obs_id, {})
    assert obs.flag == "H"
    assert obs.is_abnormal is True


@pytest.mark.asyncio
async def test_hc_vkf_003_flag_kept_when_value_inside_printed_range(profile_db):
    obs_id = await _seed_obs(profile_db, flag="H", is_abnormal=True,
                             value=14.0, ref_low=12.0, ref_high=16.0)
    obs = await _verify_and_load(profile_db, obs_id, {})
    assert obs.flag == "H"
    assert obs.is_abnormal is True


@pytest.mark.asyncio
async def test_hc_vkf_004_resending_same_numbers_keeps_flag(profile_db):
    # Case a: flagged H, value above ref_high; the UI re-sends the same numbers.
    a_id = await _seed_obs(profile_db, flag="H", is_abnormal=True,
                           value=18.0, ref_low=12.0, ref_high=16.0)
    a = await _verify_and_load(
        profile_db, a_id, {"value": 18.0, "ref_low": 12.0, "ref_high": 16.0})
    assert a.flag == "H"
    assert a.is_abnormal is True

    # Case b: flagged H but value inside the range (today's rule clears it).
    b_id = await _seed_obs(profile_db, flag="H", is_abnormal=True,
                           value=14.0, ref_low=12.0, ref_high=16.0)
    b = await _verify_and_load(
        profile_db, b_id, {"value": 14.0, "ref_low": 12.0, "ref_high": 16.0})
    assert b.flag == "H"
    assert b.is_abnormal is True

    # Case c: a non-number edit (unit, value_text, notes, collected_at) is not
    # a change to value/ref_low/ref_high, so the printed flag stays.
    for body in ({"unit": "mg/dL"}, {"value_text": "<0.5"}, {"notes": "n"},
                 {"collected_at": "2026-03-02T08:00:00"}):
        c_id = await _seed_obs(profile_db, flag="CRITICAL", is_abnormal=True,
                               value=14.0, ref_low=12.0, ref_high=16.0)
        c = await _verify_and_load(profile_db, c_id, body)
        assert c.flag == "CRITICAL", body
        assert c.is_abnormal is True, body


@pytest.mark.asyncio
async def test_hc_vkf_005_edited_value_out_of_range_is_flagged(profile_db):
    # Seeded with a different printed flag so only the changed-value check
    # (not the "no flag" fallback of 008) can trigger the recalculation.
    hi_id = await _seed_obs(profile_db, flag="L", is_abnormal=True,
                            value=14.0, ref_low=12.0, ref_high=16.0)
    hi = await _verify_and_load(profile_db, hi_id, {"value": 18.0})
    assert hi.is_abnormal is True
    assert hi.flag == "H"

    lo_id = await _seed_obs(profile_db, flag="H", is_abnormal=True,
                            value=14.0, ref_low=12.0, ref_high=16.0)
    lo = await _verify_and_load(profile_db, lo_id, {"value": 9.0})
    assert lo.is_abnormal is True
    assert lo.flag == "L"


@pytest.mark.asyncio
async def test_hc_vkf_006_edited_value_back_in_range_clears_flag(profile_db):
    obs_id = await _seed_obs(profile_db, flag="H", is_abnormal=True,
                             value=18.0, ref_low=12.0, ref_high=16.0)
    obs = await _verify_and_load(profile_db, obs_id, {"value": 14.0})
    assert obs.is_abnormal is False
    assert obs.flag is None


@pytest.mark.asyncio
async def test_hc_vkf_007_edited_range_flags_unchanged_value(profile_db):
    # Rows carry a (different) printed flag so only the changed-range check,
    # not the "no flag" fallback of 008, can trigger the recalculation.
    # ref_high edited so the unchanged value is now above it.
    obs_id = await _seed_obs(profile_db, flag="L", is_abnormal=True,
                             value=14.0, ref_low=12.0, ref_high=16.0)
    obs = await _verify_and_load(profile_db, obs_id, {"ref_high": 13.0})
    assert obs.is_abnormal is True
    assert obs.flag == "H"

    # ref_low edited so the unchanged value is now below it.
    lo_id = await _seed_obs(profile_db, flag="H", is_abnormal=True,
                            value=14.0, ref_low=12.0, ref_high=16.0)
    lo = await _verify_and_load(profile_db, lo_id, {"ref_low": 15.0})
    assert lo.is_abnormal is True
    assert lo.flag == "L"


@pytest.mark.asyncio
async def test_hc_vkf_008_no_flag_or_normal_word_row_is_recalculated_by_plain_verify(profile_db):
    # The extractor never derives a flag from the range, and ingest sets
    # is_abnormal = flag is not None. A report line with no printed flag but a
    # value outside its printed range must still be flagged by a plain Verify
    # (what origin/main did). A row with no flag or a normal word is
    # recalculated; any other stored flag is kept on a plain Verify (001-004,
    # 009-012).
    hi_id = await _seed_obs(profile_db, flag=None, is_abnormal=False,
                            value=18.0, ref_low=12.0, ref_high=16.0)
    hi = await _verify_and_load(profile_db, hi_id, {})
    assert hi.is_abnormal is True
    assert hi.flag == "H"

    lo_id = await _seed_obs(profile_db, flag=None, is_abnormal=False,
                            value=9.0, ref_low=12.0, ref_high=16.0)
    lo = await _verify_and_load(profile_db, lo_id, {})
    assert lo.is_abnormal is True
    assert lo.flag == "L"

    # An unflagged row inside its range stays unflagged.
    ok_id = await _seed_obs(profile_db, flag=None, is_abnormal=False,
                            value=14.0, ref_low=12.0, ref_high=16.0)
    ok = await _verify_and_load(profile_db, ok_id, {})
    assert ok.is_abnormal is False
    assert ok.flag is None

    # A row with no value is left alone (the value-is-None guard).
    nv_id = await _seed_obs(profile_db, flag=None, is_abnormal=False,
                            value=None, ref_low=12.0, ref_high=16.0)
    nv = await _verify_and_load(profile_db, nv_id, {})
    assert nv.is_abnormal is False
    assert nv.flag is None

    # Structured import stores free text as the flag and sets is_abnormal from
    # "flag is not None". A normal-word flag is not an abnormal marker: it is
    # recalculated from the range as before, never kept as abnormal.
    for word, value, want_flag, want_abn in (
        ("N", 14.0, None, False),
        ("Normal", 14.0, None, False),
        ("Normal", 18.0, "H", True),
    ):
        w_id = await _seed_obs(profile_db, flag=word, is_abnormal=True,
                               value=value, ref_low=12.0, ref_high=16.0)
        w = await _verify_and_load(profile_db, w_id, {})
        assert (w.flag, w.is_abnormal) == (want_flag, want_abn), (word, value)


# --- L0 ruling (#463): a plain Verify keeps any flag except a normal word ----

# Every shape a kept flag must survive: no printed range, inside it, outside it.
_SHAPES = (
    ("no_range", 14.0, None, None),
    ("in_range", 14.0, 12.0, 16.0),
    ("out_of_range", 18.0, 12.0, 16.0),
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "word",
    ["Critical high", "Yes", "Positive", "Elevated",
     # Near-misses of the normal set and the owner's own example: only the
     # exact words NORMAL, N, WNL count as normal, never a substring or a
     # negation. A padded word is kept as stored, whatever its case.
     "Negative", "Normal range", "Non-critical", " High "],
)
@pytest.mark.parametrize("shape", _SHAPES, ids=[s[0] for s in _SHAPES])
async def test_hc_vkf_009_unknown_words_are_kept(profile_db, word, shape):
    _, value, ref_low, ref_high = shape
    obs_id = await _seed_obs(profile_db, flag=word, is_abnormal=True,
                             value=value, ref_low=ref_low, ref_high=ref_high)
    obs = await _verify_and_load(profile_db, obs_id, {})
    assert obs.flag == word
    assert obs.is_abnormal is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "word",
    ["Normal", "N", "WNL", "normal", "n", "wnl", "WnL", " Normal ", " n ", " WNL "],
)
async def test_hc_vkf_010_normal_words_are_recalculated(profile_db, word):
    # Pin: green on 3f9bfee7 and on origin/main as well (a normal word was
    # always recalculated); it guards the new keep rule against over-reach.
    for value, ref_low, ref_high, want_flag, want_abn in (
        (14.0, 12.0, 16.0, None, False),
        (18.0, 12.0, 16.0, "H", True),
        (9.0, 12.0, 16.0, "L", True),
        (14.0, None, None, None, False),
    ):
        obs_id = await _seed_obs(profile_db, flag=word, is_abnormal=True,
                                 value=value, ref_low=ref_low, ref_high=ref_high)
        obs = await _verify_and_load(profile_db, obs_id, {})
        assert (obs.flag, obs.is_abnormal) == (want_flag, want_abn), (word, value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "word", ["H", "L", "HH", "LL", "A", "HIGH", "LOW", "ABNORMAL", "CRITICAL"]
)
@pytest.mark.parametrize("shape", _SHAPES, ids=[s[0] for s in _SHAPES])
async def test_hc_vkf_011_all_coded_words_are_kept(profile_db, word, shape):
    # Green on 3f9bfee7, red on the origin/main route (which recalculated).
    _, value, ref_low, ref_high = shape
    obs_id = await _seed_obs(profile_db, flag=word, is_abnormal=True,
                             value=value, ref_low=ref_low, ref_high=ref_high)
    obs = await _verify_and_load(profile_db, obs_id, {})
    assert obs.flag == word
    assert obs.is_abnormal is True


def _extractor_flag_words() -> set[str]:
    from modules.extract import ExtractModule

    pat = ExtractModule.FLAG_PATTERN.pattern
    return set(pat[pat.index("(") + 1:pat.rindex(")")].split("|"))


@pytest.mark.asyncio
async def test_hc_vkf_012_every_extractor_flag_word_is_kept(profile_db):
    # Parity with the extractor: derive the words from FLAG_PATTERN itself so a
    # word added there later is covered. A loop with a message, not parametrize,
    # because an empty parametrize would skip silently.
    words = _extractor_flag_words()
    assert words, "no flag words derived from ExtractModule.FLAG_PATTERN"
    assert {"HH", "LL"} <= words, words
    for word in sorted(words):
        for _, value, ref_low, ref_high in _SHAPES:
            obs_id = await _seed_obs(profile_db, flag=word, is_abnormal=True,
                                     value=value, ref_low=ref_low, ref_high=ref_high)
            obs = await _verify_and_load(profile_db, obs_id, {})
            assert obs.flag == word, (word, value, ref_low, ref_high)
            assert obs.is_abnormal is True, (word, value, ref_low, ref_high)


@pytest.mark.asyncio
async def test_hc_vkf_013_kept_word_beside_the_real_change_rule(profile_db):
    # A real edit of the value still rewrites a kept word.
    up_id = await _seed_obs(profile_db, flag="Critical high", is_abnormal=True,
                            value=14.0, ref_low=12.0, ref_high=16.0)
    up = await _verify_and_load(profile_db, up_id, {"value": 18.0})
    assert (up.flag, up.is_abnormal) == ("H", True)

    down_id = await _seed_obs(profile_db, flag="Critical high", is_abnormal=True,
                              value=18.0, ref_low=12.0, ref_high=16.0)
    down = await _verify_and_load(profile_db, down_id, {"value": 14.0})
    assert (down.flag, down.is_abnormal) == (None, False)

    # Re-sending the same numbers is not a change: the word is kept.
    same_id = await _seed_obs(profile_db, flag="Critical high", is_abnormal=True,
                              value=14.0, ref_low=12.0, ref_high=16.0)
    same = await _verify_and_load(
        profile_db, same_id, {"value": 14.0, "ref_low": 12.0, "ref_high": 16.0})
    assert (same.flag, same.is_abnormal) == ("Critical high", True)

    # "Exactly": a kept flag keeps is_abnormal too, even when it was False.
    yes_id = await _seed_obs(profile_db, flag="Yes", is_abnormal=False,
                             value=14.0, ref_low=12.0, ref_high=16.0)
    yes = await _verify_and_load(profile_db, yes_id, {})
    assert (yes.flag, yes.is_abnormal) == ("Yes", False)


@pytest.mark.asyncio
async def test_hc_vkf_014_blank_flag_is_kept_like_any_other_flag(profile_db):
    # Pin of the L0 ruling (#463): a whitespace-only flag (reachable through a
    # FHIR interpretation.text of spaces) is "any other flag", not "no flag",
    # and is kept exactly. Review round 1 asked L0 to re-confirm this choice;
    # if L0 rules blank = no flag, this test flips with the code.
    obs_id = await _seed_obs(profile_db, flag="   ", is_abnormal=True,
                             value=14.0, ref_low=12.0, ref_high=16.0)
    obs = await _verify_and_load(profile_db, obs_id, {})
    assert (obs.flag, obs.is_abnormal) == ("   ", True)


# --- L0 ruling (#463): the FHIR export redacts a kept free-text flag ---------
#
# A plain Verify keeps any stored flag that is not a normal word (001-014), so
# a flag can be report free text. document-level Verify also sets
# user_verified on rows without touching the flag. Either way the row reaches
# POST /export/fhir, which must redact the flag like other narrative.

# One Observation per export, so every PII span below comes from the flag.
_PII_FLAG = "Called Dr Smith 555-123-4567 jane@example.com MRN: A1234567"
_PII_BITS = ("555-123-4567", "jane@example.com", "A1234567")


@pytest.fixture
def fhir_store(monkeypatch):
    """A fresh api.export._fhir_store so no export outlives its test."""
    store: dict = {}
    monkeypatch.setattr(export_api, "_fhir_store", store)
    return store


def _master_db_with_profile():
    """POST /export/fhir reads the Profile row; route_client's default
    AsyncMock cannot return one."""
    db = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = SimpleNamespace(display_name="Jane Doe")
    db.execute = AsyncMock(return_value=result)
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _export_fhir(profile_db):
    """POST /export/fhir then GET its download, both through HTTP.

    Returns (POST json, raw download text, parsed bundle).
    """
    master_db = _master_db_with_profile()
    post = _get(export_api.router, "/export", profile_db, "POST", "/export/fhir",
                master_db=master_db, json={"confirm": True})
    assert post.status_code == 200, post.text
    body = post.json()
    dl = _get(export_api.router, "/export", profile_db, "GET",
              f"/export/fhir/{body['export_id']}/download", master_db=master_db)
    assert dl.status_code == 200, dl.text
    return body, dl.text, json.loads(dl.text)


def _observation_resources(bundle) -> list[dict]:
    return [e["resource"] for e in bundle["entry"]
            if e["resource"]["resourceType"] == "Observation"]


async def _set_flag(profile_db, obs_id, flag) -> None:
    obs = (
        await profile_db.execute(select(Observation).where(Observation.id == obs_id))
    ).scalar_one()
    obs.flag = flag
    await profile_db.commit()


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["route_verify", "document_level_verify"])
async def test_hc_vkf_015_fhir_export_redacts_a_kept_free_text_flag(
        profile_db, fhir_store, path):
    if path == "route_verify":
        # (a) stored unverified, then a plain Verify through the route, which
        # keeps the free-text flag (001-004, 009).
        obs_id = await _seed_obs(profile_db, flag=_PII_FLAG, is_abnormal=True,
                                 value=14.0, ref_low=12.0, ref_high=16.0)
        kept = await _verify_and_load(profile_db, obs_id, {})
        assert kept.flag == _PII_FLAG
    else:
        # (b) the state document-level Verify leaves: user_verified True with
        # the flag as stored, and no route Verify on the row.
        obs_id = await _seed_obs(profile_db, flag=_PII_FLAG, is_abnormal=True,
                                 value=14.0, ref_low=12.0, ref_high=16.0,
                                 user_verified=True)

    body, raw, bundle = _export_fhir(profile_db)
    for bit in _PII_BITS:
        assert bit not in raw, bit
    (resource,) = _observation_resources(bundle)
    assert "[PHONE-REDACTED]" in resource["interpretation"][0]["text"]

    # Same row, same export, flag H: the flag is the only thing that differs,
    # so a higher redaction_count comes from the flag. The display name can
    # count too, so no absolute number is asserted.
    await _set_flag(profile_db, obs_id, "H")
    body_h, _, _ = _export_fhir(profile_db)
    assert body["redaction_count"] > body_h["redaction_count"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "word",
    ["H", "L", "HH", "LL", "A", "HIGH", "LOW", "ABNORMAL", "CRITICAL",
     "Critical high", "Positive", "Yes", "Elevated", "Non-critical",
     "Negative", "NEG"],
)
async def test_hc_vkf_016_fhir_export_leaves_a_coded_flag_unchanged(
        profile_db, fhir_store, word):
    # Pin: green before the fix and after it. Strict redaction leaves every
    # coded flag word alone (measured, L0 ruling), so redacting the flag costs
    # no clinical meaning. If a word here ever changes, stop and tell L0.
    await _seed_obs(profile_db, flag=word, is_abnormal=True, value=14.0,
                    ref_low=12.0, ref_high=16.0, user_verified=True)
    _, _, bundle = _export_fhir(profile_db)
    (resource,) = _observation_resources(bundle)
    assert resource["interpretation"] == [{"text": word}]
