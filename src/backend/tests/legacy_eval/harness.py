"""Legacy RAG eval harness: W-4 / owner decision G-B5 (2026-09-27).

Drives POST /assistant/chat over HTTP (tests/support/routes.py::route_client),
so FastAPI's dependency graph runs. Only these are faked:
  - auth + master DB (route_client), and the profile DB session (AsyncMock);
  - session / history / memory helpers and the agent flag (forced off, so the
    request takes the legacy rag.query branch);
  - RAGModule.retrieve_context -> the case's fixed chunks;
  - the external-runner lookup returns a FakeRunner whose generate_async
    yields the case's model output and finish_reason ("stop" or "timeout").
RAGModule._generate_with_runner is REAL, including its timeout branch.
Everything after the runner is real product code: validate_response (claim
extraction, verify_all_claims, FaithfulnessScorer at the unchanged 0.6
threshold), the G-B5 abstain mapping, response formatting, and the
_append_turns call site. Fixture text is synthetic; it holds no patient data.
"""

from __future__ import annotations

import asyncio
import json
import re
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Iterator
from unittest.mock import AsyncMock, MagicMock, patch

CHAT_PATH = "/assistant/chat"

CHUNK_SETS: dict[str, tuple[dict, ...]] = {
    "glucose": (
        {
            "chunk_id": "1",
            "source_type": "user_observation",
            "doc_id": "doc-1",
            "doc_title": "Your Glucose Result",
            "page": 1,
            "text": "Glucose: 95 mg/dL (reference range 70-100 mg/dL), collected 2026-01-10.",
            "relevance_score": 0.95,
            "is_user_verified": True,
        },
        {
            "chunk_id": "2",
            "source_type": "reference",
            "doc_id": None,
            "doc_title": "Medical Reference",
            "page": None,
            "text": (
                "Glucose is a simple sugar that is the primary source of energy for the "
                "body's cells. Normal fasting glucose is typically 70-100 mg/dL."
            ),
            "relevance_score": 0.8,
        },
    ),
}


def build_chunks(chunk_set: str) -> list:
    """Return fresh RetrievedChunk objects for a named fixture set."""
    from modules.rag import RetrievedChunk

    return [RetrievedChunk(**spec) for spec in CHUNK_SETS[chunk_set]]


class FakeRunner:
    """Stands in for the runner get_runner_for_request would return. Test-only."""

    def __init__(self, text: str, finish_reason: str = "stop") -> None:
        self._result = SimpleNamespace(text=text, finish_reason=finish_reason)

    def is_available(self) -> bool:
        return True

    async def generate_async(self, prompt: str, config: object) -> SimpleNamespace:
        return self._result


def generated_text(model_output: str, finish_reason: str = "stop") -> str:
    """What the REAL RAGModule._generate_with_runner returns for this runner output."""
    from modules.rag import RAGModule

    rag = RAGModule(enable_verification=True)
    return asyncio.run(rag._generate_with_runner("prompt", FakeRunner(model_output, finish_reason)))


@contextmanager
def legacy_chat_client(
    chunks: list, model_output: str, finish_reason: str = "stop"
) -> Iterator[tuple[object, AsyncMock]]:
    """Yield (TestClient, append_turns_mock) wired to the legacy chat path."""
    import api.assistant as assistant_api
    from core.auth import get_profile_db_session
    from modules.rag import RAGModule
    from tests.support.routes import route_client

    profile_db = AsyncMock()
    # SAFE-CHAT's audit_and_commit calls create_audit_log -> synchronous db.add (core/audit.py:252);
    # route_client's default AsyncMock would turn that into an unawaited coroutine.
    master = MagicMock()
    master.commit = AsyncMock()
    master.flush = AsyncMock()
    master.refresh = AsyncMock()
    chat_session = SimpleNamespace(id="sess-legacy-eval", updated_at=None)
    append_turns = AsyncMock(return_value="turn-legacy-eval")

    async def _profile_db_override():
        yield profile_db

    with ExitStack() as stack:
        stack.enter_context(patch.object(assistant_api, "is_agent_enabled", return_value=False))
        stack.enter_context(patch.object(assistant_api, "_get_user_model_settings", AsyncMock(return_value=None)))
        stack.enter_context(patch.object(assistant_api, "_get_or_create_session", AsyncMock(return_value=chat_session)))
        stack.enter_context(patch.object(assistant_api, "_load_session_history", AsyncMock(return_value=[])))
        stack.enter_context(patch.object(assistant_api, "_effective_use_memory", AsyncMock(return_value=False)))
        stack.enter_context(patch.object(assistant_api, "_append_turns", append_turns))
        stack.enter_context(
            patch(
                "core.external_runner.get_runner_for_request",
                AsyncMock(return_value=FakeRunner(model_output, finish_reason)),
            )
        )
        stack.enter_context(patch.object(RAGModule, "retrieve_context", AsyncMock(return_value=chunks)))
        client = stack.enter_context(route_client(assistant_api.router, "/assistant", master_db=master))
        client.app.dependency_overrides[get_profile_db_session] = _profile_db_override
        yield client, append_turns


GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
_CITE = re.compile(r"\[cite:\d+\]")
_EXPECTS = frozenset({"answer", "abstain", "escalate"})
_SECTION = re.compile(r"^(REPORT FACTS|GENERAL INFO):\s*$")
_REQUIRED = frozenset({"id", "question", "chunk_set", "model_output", "expect"})
_FINISH_REASONS = frozenset({"stop", "timeout"})


def load_cases(directory: Path | None = None) -> list[dict]:
    """Load and validate every golden case JSON (sorted by filename)."""
    root = directory or GOLDEN_DIR
    cases = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(root.glob("*.json"))]
    for case in cases:
        missing = sorted(_REQUIRED - case.keys())
        if (
            missing
            or case["expect"] not in _EXPECTS
            or case["chunk_set"] not in CHUNK_SETS
            or case.get("finish_reason", "stop") not in _FINISH_REASONS
        ):
            raise ValueError(f"malformed legacy golden case {case.get('id', '?')}: missing={missing}")
    return cases


def _leak_probe(model_output: str) -> str:
    """First report-facts/general-info line of the model output, minus any [cite:N]."""
    lines = model_output.splitlines()
    for i, line in enumerate(lines[:-1]):
        if _SECTION.match(line):
            return _CITE.split(lines[i + 1])[0].strip()
    return ""


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    expect: str
    abstained: bool
    escalated: bool
    is_valid: bool
    uncited_served: bool
    leaked: bool
    persisted_matches: bool

    @property
    def ok(self) -> bool:
        return (
            self.abstained == (self.expect == "abstain")
            and self.escalated == (self.expect == "escalate")
            and (self.abstained or self.escalated or self.is_valid)
            and not self.uncited_served
            and self.persisted_matches
        )


@dataclass(frozen=True)
class LegacyReport:
    results: tuple[CaseResult, ...]

    def _count(self, predicate) -> int:
        return sum(1 for r in self.results if predicate(r))

    def _rate(self, expect: str) -> float:
        group = [r for r in self.results if r.expect == expect]
        if not group:
            return 0.0
        hit = {
            "abstain": lambda r: r.abstained,
            "escalate": lambda r: r.escalated,
            "answer": lambda r: not r.abstained and not r.escalated,
        }[expect]
        return sum(1 for r in group if hit(r)) / len(group)

    @property
    def served_invalid(self) -> int:
        return self._count(lambda r: not r.abstained and not r.escalated and not r.is_valid)

    @property
    def uncited_served(self) -> int:
        return self._count(lambda r: r.uncited_served)

    @property
    def leaked(self) -> int:
        return self._count(lambda r: r.leaked)

    @property
    def persisted_mismatch(self) -> int:
        return self._count(lambda r: not r.persisted_matches)

    @property
    def abstention(self) -> float:
        return self._rate("abstain")

    @property
    def escalation(self) -> float:
        return self._rate("escalate")

    @property
    def answer_rate(self) -> float:
        return self._rate("answer")

    def failure_reasons(self) -> list[str]:
        reasons: list[str] = []
        if not self.results:
            reasons.append("no golden cases loaded")
        if self.served_invalid:
            reasons.append(f"served_invalid={self.served_invalid} (must be 0)")
        if self.uncited_served:
            reasons.append(f"uncited_served={self.uncited_served} (must be 0)")
        if self.leaked:
            reasons.append(f"leaked={self.leaked} (must be 0)")
        if self.persisted_mismatch:
            reasons.append(f"persisted_mismatch={self.persisted_mismatch} (must be 0)")
        if self.abstention < 1.0:
            reasons.append(f"abstention={self.abstention:.3f} (must be 1.0)")
        if self.escalation < 1.0:
            reasons.append(f"escalation={self.escalation:.3f} (must be 1.0)")
        if self.answer_rate < 1.0:
            reasons.append(f"answer_rate={self.answer_rate:.3f} (must be 1.0)")
        return reasons

    @property
    def passed(self) -> bool:
        return not self.failure_reasons()

    def render(self) -> str:
        lines = [
            "=" * 72,
            "Legacy RAG eval gate: served output of POST /assistant/chat",
            "=" * 72,
            f"  total cases:        {len(self.results)}",
            f"  served_invalid:     {self.served_invalid}  (bar: == 0)",
            f"  uncited_served:     {self.uncited_served}  (bar: == 0)",
            f"  leaked:             {self.leaked}  (bar: == 0)",
            f"  persisted_mismatch: {self.persisted_mismatch}  (bar: == 0)",
            f"  abstention:         {self.abstention:.3f}  (bar: == 1.000)",
            f"  escalation:         {self.escalation:.3f}  (bar: == 1.000)",
            f"  answer_rate:        {self.answer_rate:.3f}  (bar: == 1.000)",
        ]
        lines += [
            f"  FAILED {r.case_id}: expect={r.expect} abstained={r.abstained} escalated={r.escalated} is_valid={r.is_valid}"
            for r in self.results
            if not r.ok
        ]
        return "\n".join(lines)


def run_case(case: dict) -> CaseResult:
    """Send one golden case through the real legacy route and classify the output."""
    from modules.agent.guardrails.templates import ABSTAIN_TEMPLATE, ESCALATE_TEMPLATE

    with legacy_chat_client(
        build_chunks(case["chunk_set"]), case["model_output"], case.get("finish_reason", "stop")
    ) as (client, append_turns):
        resp = client.post(CHAT_PATH, json={"question": case["question"]})
    if resp.status_code != 200:
        raise RuntimeError(f"{case['id']}: HTTP {resp.status_code}")
    body = resp.json()
    segments = body["segments"]
    abstained = segments == [
        {"segment_type": "uncertainty", "content": ABSTAIN_TEMPLATE, "citations": []}
    ] and body["full_response"] == f"**UNCERTAINTY**\n{ABSTAIN_TEMPLATE}"
    escalated = segments == [
        {"segment_type": "uncertainty", "content": ESCALATE_TEMPLATE, "citations": []}
    ] and body["full_response"] == ESCALATE_TEMPLATE
    uncited = (not abstained and not escalated) and any(
        s["segment_type"] == "report_facts" and not _CITE.search(s["content"]) for s in segments
    )
    persisted = append_turns.await_args.kwargs.get("assistant_content") if append_turns.await_args else None
    # Segments-only classification could pass while answer text stayed in full_response.
    probe = _leak_probe(case["model_output"]) if case["expect"] != "answer" else ""
    leaked = bool(probe) and (probe in resp.text or probe in (persisted or ""))
    return CaseResult(
        case_id=case["id"],
        expect=case["expect"],
        abstained=abstained,
        escalated=escalated,
        is_valid=bool(body["is_valid"]),
        uncited_served=uncited,
        leaked=leaked,
        persisted_matches=persisted == body["full_response"],
    )


def score_cases(cases: list[dict]) -> LegacyReport:
    return LegacyReport(results=tuple(run_case(case) for case in cases))
