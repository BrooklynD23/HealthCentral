"""CITE-SRC-001 — citations carry a deep-link target.

Bbox and page provenance has been stored since HC-M12 but never reached the
client, so a citation chip was a label rather than checkable evidence. These
tests pin the additive `Citation` fields and, importantly, that they are only
populated when there is a real target — a fabricated deep link is worse than
no link, because it sends the patient to the wrong part of their record.

Test IDs: HC-CITE-0NN.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from api.assistant import Citation, _agent_terminal_to_response_parts
from modules.agent.schemas import AgentTerminal
from modules.agent.schemas import Citation as AgentCitation


def _terminal(citations, terminal="answer"):
    return AgentTerminal(
        terminal=terminal, text="Some grounded sentence.", citations=citations, run_id="run-1"
    )


# ---------------------------------------------------------------------------
# The API model
# ---------------------------------------------------------------------------

def test_hc_cite_001_citation_deeplink_fields_default_to_none():
    """A citation with no resolvable source must not invent one."""
    c = Citation(source_type="reference", text_snippet="x")

    assert c.observation_id is None
    assert c.entity_id is None
    assert c.source_page is None
    assert c.source_bbox_json is None


def test_hc_cite_002_observation_citation_carries_its_target():
    c = Citation(
        source_type="user_observation",
        text_snippet="Glucose: 94 mg/dL",
        doc_id="doc-1",
        observation_id="obs-1",
        source_page=3,
        source_bbox_json="[10,20,30,40]",
    )
    assert c.observation_id == "obs-1"
    assert c.source_page == 3
    assert c.source_bbox_json == "[10,20,30,40]"


# ---------------------------------------------------------------------------
# Agent path mapping
# ---------------------------------------------------------------------------

def test_hc_cite_003_agent_observation_citation_maps_to_observation_id():
    segments, _ = _agent_terminal_to_response_parts(
        _terminal([
            AgentCitation(
                source_type="document", source_id="obs-42",
                locator="obs-42", source_kind="observation",
            )
        ])
    )
    c = segments[0].citations[0]

    assert c.observation_id == "obs-42"
    assert c.entity_id is None


def test_hc_cite_004_agent_entity_citation_maps_to_entity_id_and_doc():
    """For entity citations the agent puts the document id in `locator`."""
    segments, _ = _agent_terminal_to_response_parts(
        _terminal([
            AgentCitation(
                source_type="document", source_id="ent-7",
                locator="doc-9", source_kind="entity",
            )
        ])
    )
    c = segments[0].citations[0]

    assert c.entity_id == "ent-7"
    assert c.doc_id == "doc-9"
    assert c.observation_id is None


@pytest.mark.parametrize("kind", ["task", "event"])
def test_hc_cite_005_tasks_and_events_get_no_deeplink(kind):
    """Care tasks and timeline events have no page or bbox of their own. They
    must render as plain labels, not as buttons that navigate nowhere."""
    segments, _ = _agent_terminal_to_response_parts(
        _terminal([
            AgentCitation(
                source_type="document", source_id=f"{kind}-1",
                locator=f"{kind}-1", source_kind=kind,
            )
        ])
    )
    c = segments[0].citations[0]

    assert c.observation_id is None
    assert c.entity_id is None
    assert c.doc_id is None


def test_hc_cite_006_reference_citations_never_get_a_document_target():
    segments, _ = _agent_terminal_to_response_parts(
        _terminal([
            AgentCitation(
                source_type="reference", source_id="REF:3",
                locator="REF:3", source_kind="reference",
            )
        ])
    )
    c = segments[0].citations[0]

    assert c.source_type == "reference"
    assert c.doc_id is None
    assert c.observation_id is None
    assert c.entity_id is None


def test_hc_cite_007_untagged_agent_citation_degrades_safely():
    """`source_kind` is optional for backward compatibility. An untagged
    citation must produce no deep link rather than a guessed one."""
    segments, _ = _agent_terminal_to_response_parts(
        _terminal([
            AgentCitation(source_type="document", source_id="unknown-1", locator=None)
        ])
    )
    c = segments[0].citations[0]

    assert c.observation_id is None
    assert c.entity_id is None
    assert c.doc_id is None


# ---------------------------------------------------------------------------
# Draft node tags what it emits
# ---------------------------------------------------------------------------

def test_hc_cite_008_draft_citations_are_all_tagged():
    """Every Citation built in the agent must carry a source_kind, or the API
    layer silently loses the deep link."""
    from pathlib import Path

    def _calls(text: str, needle: str) -> list[str]:
        """Slice out whole Citation(...) calls with paren balancing.

        A naive `[^)]*` regex stops at the first close paren, which lands in
        the middle of a nested call like `locator=row.get("doc_id")` and
        reports a false positive.
        """
        out = []
        start = text.find(needle)
        while start != -1:
            depth, i = 0, text.index("(", start)  # the opening paren of the call
            while i < len(text):
                if text[i] == "(":
                    depth += 1
                elif text[i] == ")":
                    depth -= 1
                    if depth == 0:
                        out.append(text[start:i + 1])
                        break
                i += 1
            start = text.find(needle, start + 1)
        return out

    backend = Path(__file__).resolve().parent.parent
    for rel in ("modules/agent/nodes/draft.py", "modules/agent/graph.py"):
        text = (backend / rel).read_text(encoding="utf-8")
        calls = _calls(text, 'Citation(source_type="document"')
        assert calls, f"{rel}: expected document citations to exist"
        for call in calls:
            assert "source_kind=" in call, (
                f"{rel}: untagged document citation -> {call[:90]}"
            )


# ---------------------------------------------------------------------------
# Entity response exposes its bbox
# ---------------------------------------------------------------------------

def test_hc_cite_009_entity_response_exposes_source_bbox():
    from api.documents import DocumentEntityResponse

    entity = SimpleNamespace(
        id="ent-1", doc_id="doc-1", category="lab", entity_type="medication_change",
        entity_value="Metformin 500mg", confidence=0.9, source_page=2,
        source_bbox_json="[1,2,3,4]", char_start=10, char_end=25,
        quote="Start Metformin 500mg", verified_by_user=None, extraction_version="v1",
    )
    response = DocumentEntityResponse.model_validate(entity)

    assert response.source_bbox_json == "[1,2,3,4]"
    assert response.source_page == 2
