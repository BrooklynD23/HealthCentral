"""ANALYTE-NAME-SWEEP Phase A: question/panel labels resolve to stored canonical names."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from modules.normalize import NormalizeModule
from tests.agent.conftest import agent_profile_db, make_run_context  # noqa: F401  (fixtures)

FE_PANEL_LABELS = [
    "Lipid Panel", "Metabolic Panel", "CBC", "Thyroid Panel", "Liver Panel", "Kidney Panel",
]


def test_hc_ans_001_panel_labels_resolve():
    n = NormalizeModule()
    assert set(n.get_panel_analytes("Lipid Panel")) == {
        "total_cholesterol", "hdl_cholesterol", "ldl_cholesterol", "triglycerides"}
    assert n.get_panel_analytes("Thyroid Panel") == ["tsh", "free_t4", "free_t3"]
    assert n.get_panel_analytes("CBC") == NormalizeModule.ANALYTE_CATEGORIES["cbc"]
    assert n.get_panel_analytes("cbc") == NormalizeModule.ANALYTE_CATEGORIES["cbc"]


@pytest.mark.parametrize("label", FE_PANEL_LABELS)
def test_hc_ans_002_every_fe_option_resolves_non_empty(label):
    assert NormalizeModule().get_panel_analytes(label)


def test_hc_ans_002b_unknown_panel_still_empty():
    assert NormalizeModule().get_panel_analytes("Nonsense Panel") == []


def test_hc_ans_002c_panel_labels_are_stored_canonical_keys():
    stored = set(NormalizeModule.ANALYTE_SYNONYMS)
    for label, analytes in NormalizeModule.PANEL_LABELS.items():
        assert set(analytes) <= stored, (label, set(analytes) - stored)


@pytest.mark.asyncio
async def test_hc_ans_003_cholesterol_plan_filter_finds_stored_total_cholesterol(
    agent_profile_db, make_run_context  # noqa: F811  # pytest fixture parameter
):
    """The planner's real filter, run through query_observations, hits the stored name.

    plan.py keeps "Cholesterol"; query_observations expands it through
    canonical_keys_for (CHAT-FACT-ROUTING), so no plan.py change is needed.
    """
    import uuid

    from modules.agent.nodes.plan import _default_planner
    from modules.agent.state import RunLog
    from modules.agent.tools.query_observations import QueryObservationsInput, QueryObservationsTool
    from tests.agent.conftest import seed_document, seed_observation

    profile_id = str(uuid.uuid4())
    doc_id = await seed_document(agent_profile_db, profile_id=profile_id)
    obs_id = await seed_observation(
        agent_profile_db, profile_id=profile_id, doc_id=doc_id,
        analyte="total_cholesterol", value=210.0, verified=True,
    )
    d = _default_planner("Explain my cholesterol", RunLog(run_id="r", profile_id=profile_id))
    assert d.tool_name == "query_observations"
    out = await QueryObservationsTool().run(
        QueryObservationsInput(**d.tool_args), make_run_context(agent_profile_db, profile_id=profile_id)
    )
    assert [r.observation_id for r in out.rows] == [obs_id]


def test_hc_ans_004_lookup_reference_canonicalizes_name():
    from modules.agent import knowledge_lookup
    from modules.agent.tools.lookup_reference import LookupReferenceInput, LookupReferenceTool

    seen = []

    async def fake(analyte, session):
        seen.append(analyte)
        return None

    class _Sess:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *a):
            return False

    ctx = SimpleNamespace(run_id="r", profile_id="p", step_index=0, audit_db=None)
    with patch.object(knowledge_lookup, "lookup_reference_range", fake), \
         patch("core.database.async_session_maker", lambda: _Sess()), \
         patch("modules.agent.tools.lookup_reference.emit_audit_event", AsyncMock()):
        out = asyncio.run(LookupReferenceTool().run(LookupReferenceInput(analyte="LDL"), ctx))
    assert seen == ["ldl_cholesterol"]
    assert out.handle == "reference:ldl"  # handle semantics unchanged
