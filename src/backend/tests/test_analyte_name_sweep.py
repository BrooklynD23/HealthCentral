"""ANALYTE-NAME-SWEEP Phase A: question/panel labels resolve to stored canonical names."""
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from modules.normalize import NormalizeModule

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


def test_hc_ans_003_cholesterol_plan_filter_matches_stored_name():
    from modules.agent.nodes.plan import _default_planner
    from modules.agent.state import RunLog

    d = _default_planner("Explain my cholesterol", RunLog(run_id="r", profile_id="p"))
    keys = {d.tool_args["analyte"].lower(), *NormalizeModule.canonical_keys_for(d.tool_args["analyte"])}
    assert "total_cholesterol" in keys


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
