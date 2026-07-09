"""draft node (Phase 2 / Phase 3 boundary).

Compose the answer; EVERY sentence must carry a source handle. The draft is then
handed to the guard node (guardrails/guard.py) which runs the advice gate on it,
drops unmapped sentences, and applies the confidence threshold before anything
reaches the user. The draft node never decides the terminal — guard does.
Emits an ``agent.draft`` audit event.

S1 scope: a single-step draft composed directly from the verified
``query_observations`` rows already gathered by ``act`` — one sentence per
observation, each carrying a ``Citation`` keyed on that observation's id.

S2 scope (story S2-2): also compose grounded TREND sentences from
``compute_trend`` output gathered by ``act`` — one sentence per
``TrendPoint``, each carrying a ``Citation`` keyed on that point's
``observation_id`` (every trend point IS its own source handle; see
``tools/compute_trend.py``). ``retrieve_chunks``/``lookup_reference``
composition is left for later stories that need them (S3+); this stays the
simplest grounded draft that still satisfies "every sentence carries a source
handle" for the tools currently composed here.
"""

from __future__ import annotations

from pydantic import BaseModel

from ..audit import AgentAuditEvent, emit_audit_event
from ..guardrails.redaction_gate import sanitize_untrusted_field
from ..schemas import Citation
from ..state import RunLog, ToolContext


class Draft(BaseModel):
    sentences: list[str]
    citations: list[Citation]  # parallel source handles, one+ per sentence


def _act_outputs(run_log: RunLog, tool_name: str) -> list[dict]:
    """Pull every output dict for ``tool_name`` out of the run log's act steps."""
    outputs: list[dict] = []
    for step in run_log.steps:
        if step.node != "act":
            continue
        if step.payload.get("tool_name") != tool_name:
            continue
        outputs.append(step.payload.get("output", {}))
    return outputs


def _observation_rows_from_log(run_log: RunLog) -> list[dict]:
    """Pull every query_observations row out of the run log's act steps."""
    rows: list[dict] = []
    for output in _act_outputs(run_log, "query_observations"):
        rows.extend(output.get("rows", []))
    return rows


def _observation_sentence(row: dict) -> str:
    """Compose the one grounded sentence for an observation row.

    ``analyte``/``unit`` are extraction-derived free text — untrusted input
    that would otherwise reach the user verbatim through the terminal, so
    both are scrubbed of injection markers and PHI patterns first (HC-M05;
    see guardrails/redaction_gate.sanitize_untrusted_field).
    """
    analyte = sanitize_untrusted_field(row["analyte"])
    unit_value = sanitize_untrusted_field(row.get("unit"))
    unit = f" {unit_value}" if unit_value else ""
    return f"Your verified {analyte} result was {row['value']}{unit} (collected {row['collected_at']})."


def _trend_sentences(run_log: RunLog) -> tuple[list[str], list[Citation]]:
    """Compose grounded trend sentences from compute_trend outputs in the log.

    One sentence per TrendPoint (chronological — compute_trend already
    orders by collected_at ascending), each citing that point's
    observation_id, plus a single summary sentence per trend citing every
    point that supports it (groundedness needs at least one citation on the
    "changed over time" claim itself, not just on the individual values).
    """
    sentences: list[str] = []
    citations: list[Citation] = []

    for output in _act_outputs(run_log, "compute_trend"):
        analyte = sanitize_untrusted_field(output.get("analyte", "result"))
        points = output.get("points", [])
        if not points:
            continue

        point_citations = [
            Citation(source_type="document", source_id=p["observation_id"], locator=p["observation_id"])
            for p in points
        ]

        for p in points:
            unit = ""  # TrendPoint carries no unit; value-only point sentence
            sentences.append(f"Your verified {analyte} result was {p['value']}{unit} (collected {p['collected_at']}).")
            citations.append(
                Citation(source_type="document", source_id=p["observation_id"], locator=p["observation_id"])
            )

        if len(points) >= 2:
            direction = output.get("direction", "flat")
            verb = {"up": "increased", "down": "decreased", "flat": "stayed about the same"}[direction]
            sentences.append(f"Your {analyte} has {verb} across your verified results.")
            citations.extend(point_citations)

    return sentences, citations


async def draft(question: str, run_log: RunLog, ctx: ToolContext) -> Draft:
    """Compose a grounded draft from verified evidence gathered so far.

    Every sentence carries a Citation referencing the observation_id it
    reports. Emits ``agent.draft`` recording the sentence/citation counts.
    """
    sentences: list[str] = []
    citations: list[Citation] = []

    trend_sentences, trend_citations = _trend_sentences(run_log)
    sentences.extend(trend_sentences)
    citations.extend(trend_citations)

    # Avoid double-reporting a value both as a raw observation row AND as a
    # trend point if a run somehow gathered both for the same observation.
    cited_observation_ids = {c.source_id for c in citations}
    rows = _observation_rows_from_log(run_log)
    for row in rows:
        if row["observation_id"] in cited_observation_ids:
            continue
        sentences.append(_observation_sentence(row))
        citations.append(
            Citation(
                source_type="document",
                source_id=row["observation_id"],
                locator=row["observation_id"],
            )
        )

    result = Draft(sentences=sentences, citations=citations)

    await emit_audit_event(
        AgentAuditEvent(
            run_id=ctx.run_id,
            node="draft",
            profile_id=ctx.profile_id,
            event_type="agent.draft",
            action="draft:compose",
            step_index=ctx.step_index,
            details={
                "sentence_count": len(sentences),
                "citation_count": len(citations),
            },
        ),
        db=getattr(ctx, "audit_db", None),
    )

    return result
