"""HC-GC5-001..005 - G-C5: HC-M11 NLI cross-encoder behind the default-off flag.

Owner decisions: Q5a (flag stays default off), Q5b (one-time fetch, HF offline,
fail closed), GC5-OL-2 option B (absent model => claim left unverified).
Plan: docs/plans/2026-10-18-GC5-hc-m11-nli-flag-off.md
"""

from __future__ import annotations

import pytest

from modules.rag import RAGModule, RetrievedChunk
from modules.verifier_agent import (
    EntailmentLabel,
    EntailmentResult,
    VerifierAgent,
)

_RESPONSE = """
REPORT FACTS:
Your glucose level is 95 mg/dL, which falls within the normal reference range of 70-100 mg/dL [cite:1].
"""


def _chunks() -> list[RetrievedChunk]:
    return [
        RetrievedChunk(
            chunk_id="1",
            source_type="user_document",
            doc_id="doc-1",
            doc_title="Quest Lab Report",
            page=1,
            text="Glucose: 95 mg/dL. Reference range: 70-100 mg/dL. Within normal limits.",
            relevance_score=0.95,
        ),
    ]


def test_hc_gc5_001_flag_reaches_verifier(monkeypatch):
    """USE_LLM_ENTAILMENT reaches VerifierAgent through get_rag_module() and validate_response()."""
    import api.assistant as assistant
    from core.config import settings

    monkeypatch.setattr(settings, "use_llm_entailment", True)
    monkeypatch.setattr(assistant, "_rag_module", None)  # restored by monkeypatch teardown

    rag = assistant.get_rag_module()
    assert rag.verifier.config.use_llm_entailment is True  # H2

    calls: list[tuple[str, str]] = []

    def _spy(self, claim, source):
        calls.append((claim, source.source_id))
        return EntailmentResult(
            source_id=source.source_id,
            label=EntailmentLabel.ENTAILMENT,
            confidence=0.9,
            explanation="spy",
        )

    monkeypatch.setattr(VerifierAgent, "_check_entailment_llm", _spy)
    rag.validate_response(response=_RESPONSE, retrieved_chunks=_chunks())
    assert calls, "use_llm_entailment=True never reached the verifier used by validate_response"  # H1
