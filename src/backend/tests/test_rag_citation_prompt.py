"""Legacy RAG prompt carries one citation-format instruction (owner decision D11).

Test IDs: HC-CIT-001..003. Contract C-SAFE-5; matrix SAFE-08.

Operational definition (the thing these tests count):
  A *citation-format instruction* is one line of prompt text that contains BOTH
  (a) a cite-word: cite / cites / cited / citing / citation / citations, and
  (b) a bracketed marker template: ``[NAME:N]`` or ``[NAME:<digits>]``.
  "exactly one" means exactly one such line, and it names ``[cite:N]`` --
  the only marker ``RAGModule.validate_response`` parses (modules/rag.py,
  ``citation_pattern = r"\\[cite:(\\d+)\\]"``).
Context labels (``[YOUR_RESULTS:N]``, ``[REFERENCE:N]``, ``[USER_DOCUMENT:N]``)
may be *described* in the prompt, but never on a line that tells the model to cite.
"""
from __future__ import annotations

import re
from unittest.mock import AsyncMock, patch

import pytest

_CITE_WORD = re.compile(r"\bcit(?:e|es|ed|ing|ation|ations)\b", re.IGNORECASE)
_MARKER = re.compile(r"\[([A-Za-z_]+):(?:N|\d+)\]")
# Context-label names rendered by RAGModule.compose_prompt:
# "YOUR_RESULTS" for observation summaries, else source_type.upper()
# for source_type in {"user_document", "user_observation", "reference"}.
_CONTEXT_LABELS = {"YOUR_RESULTS", "USER_DOCUMENT", "USER_OBSERVATION", "REFERENCE"}


def _citation_format_instructions(text: str) -> list[tuple[str, list[str]]]:
    """Return (line, marker-names) for every citation-format instruction line."""
    return [
        (line.strip(), _MARKER.findall(line))
        for line in text.splitlines()
        if _CITE_WORD.search(line) and _MARKER.search(line)
    ]


def _cite_lines_naming_a_label(text: str, labels: set[str]) -> list[str]:
    """Lines that tell the model to cite AND name a context label, bracketed or not."""
    label_re = re.compile(r"\b(" + "|".join(sorted(labels)) + r")\b")
    return [ln.strip() for ln in text.splitlines() if _CITE_WORD.search(ln) and label_re.search(ln)]


def _instruction_header() -> str:
    from modules.rag import RAGModule

    return RAGModule.SYSTEM_PROMPT.split("CONTEXT:", 1)[0]


def test_hc_cit_001_system_prompt_has_exactly_one_citation_format_instruction():
    header = _instruction_header()
    found = _citation_format_instructions(header)
    assert [markers for _, markers in found] == [["cite"]], (
        "SYSTEM_PROMPT must carry exactly one citation-format instruction, naming "
        f"[cite:N]; found {len(found)}: {found}"
    )
    offenders = _cite_lines_naming_a_label(header, _CONTEXT_LABELS)
    assert offenders == [], f"a cite instruction names a context label: {offenders}"


@pytest.mark.asyncio
async def test_hc_cit_002_prompt_sent_to_model_has_exactly_one_citation_format_instruction():
    """The prompt RAGModule.query() actually hands the runner -- after context,
    session history and memory are spliced in -- still has one instruction."""
    from modules.rag import RAGModule, RetrievedChunk

    rag = RAGModule()
    chunks = [
        RetrievedChunk(
            chunk_id="obs_1", source_type="user_observation", doc_id=None,
            doc_title="Your LDL Result", page=None,
            text="YOUR RESULTS - LDL\nLatest value : 145 mg/dL",
            relevance_score=0.95, is_observation_summary=True,
        ),
        RetrievedChunk(
            chunk_id="ref_1", source_type="reference", doc_id=None,
            doc_title="Medical Reference: LDL", page=None,
            text="LDL is a lipoprotein that carries cholesterol.",
            relevance_score=0.8, is_peer_reviewed=True,
        ),
        RetrievedChunk(
            chunk_id="doc_1", source_type="user_document", doc_id="d1",
            doc_title="Lab Report", page=2,
            text="LDL 145 mg/dL (ref < 100)",
            relevance_score=0.7, is_user_verified=True,
        ),
    ]
    memory = (
        "\nUSER PREFERENCES (from memory store — do NOT cite, "
        "use only for personalisation):\n- prefers metric units\n"
    )
    history = [
        {"role": "user", "content": "What was my LDL last time?"},
        {"role": "assistant", "content": "Your LDL was 150 mg/dL."},
    ]
    generate = AsyncMock(return_value="REPORT FACTS:\nYour LDL is 145 mg/dL [cite:1].")

    with (
        patch.object(rag, "retrieve_context", new_callable=AsyncMock, return_value=chunks),
        patch.object(rag, "_retrieve_memory_context", new_callable=AsyncMock, return_value=memory),
        patch.object(rag, "_generate_with_runner", generate),
    ):
        await rag.query(
            question="Is my LDL high?", profile_id="prof-1",
            history=history, use_memory=True,
        )

    prompt = generate.call_args.args[0]
    rendered_labels = set(re.findall(r"^\[([A-Z_]+):\d+\]", prompt, re.MULTILINE))
    assert rendered_labels == {"YOUR_RESULTS", "REFERENCE", "USER_DOCUMENT"}, rendered_labels
    assert "USER PREFERENCES" in prompt and "SESSION HISTORY" in prompt

    found = _citation_format_instructions(prompt)
    assert [markers for _, markers in found] == [["cite"]], (
        f"prompt sent to the model carries {len(found)} citation-format instructions: {found}"
    )
    offenders = _cite_lines_naming_a_label(prompt, rendered_labels)
    assert offenders == [], f"a cite instruction names a context label: {offenders}"


def test_hc_cit_003_every_instructed_marker_is_one_the_validator_counts():
    """Each marker the prompt tells the model to write is parsed by
    validate_response and ClaimExtractor; a bare context label is not."""
    from modules.claim_extractor import ClaimExtractor
    from modules.rag import RAGModule, RetrievedChunk

    rag = RAGModule(enable_verification=False)
    chunk = RetrievedChunk(
        chunk_id="obs_1", source_type="user_observation", doc_id=None,
        doc_title="Your LDL Result", page=None,
        text="YOUR RESULTS - LDL\nLatest value : 145 mg/dL",
        relevance_score=0.95, is_observation_summary=True,
    )
    instructed = sorted(
        {m for _, ms in _citation_format_instructions(_instruction_header()) for m in ms}
    )
    assert instructed, "no citation-format instruction found in SYSTEM_PROMPT"

    not_counted = []
    for name in instructed:
        marker = f"[{name}:1]"
        validated = rag.validate_response(
            f"REPORT FACTS:\nYour LDL is 145 mg/dL {marker}.\n", [chunk]
        )
        report = [s for s in validated.segments if s.segment_type == "report_facts"]
        counted = bool(report and report[0].citations) and not any(
            "missing citations" in e for e in validated.validation_errors
        )
        if not counted or not re.search(ClaimExtractor.CITATION_PATTERN, marker):
            not_counted.append(marker)
    assert not_counted == [], (
        f"prompt instructs markers the validator/claim extractor do not parse: {not_counted}"
    )

    # Pin: a bare context label is not a citation (D11: labels, not markers).
    label_only = rag.validate_response(
        "REPORT FACTS:\nYour LDL is 145 mg/dL [YOUR_RESULTS:1].\n", [chunk]
    )
    assert "Report facts section missing citations" in label_only.validation_errors
