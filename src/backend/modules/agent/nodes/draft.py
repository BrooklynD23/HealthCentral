"""draft node (Phase 2 / Phase 3 boundary).

Compose the answer; EVERY sentence must carry a source handle. The draft is then
handed to the guard node (guardrails/guard.py) which runs the advice gate on it,
drops unmapped sentences, and applies the confidence threshold before anything
reaches the user. The draft node never decides the terminal — guard does.
Emits an ``agent.draft`` audit event.

S1 scope: a single-step draft composed directly from the verified
``query_observations`` rows already gathered by ``act`` — one sentence per
observation, each carrying a ``Citation`` keyed on that observation's id. The
full grounded-trend / multi-tool composition (compute_trend, retrieve_chunks,
etc.) is Sprint 2+; this is intentionally the simplest grounded draft that
still satisfies "every sentence carries a source handle".
"""

from __future__ import annotations

from pydantic import BaseModel

from ..audit import AgentAuditEvent, emit_audit_event
from ..schemas import Citation
from ..state import RunLog, ToolContext


class Draft(BaseModel):
    sentences: list[str]
    citations: list[Citation]  # parallel source handles, one+ per sentence


def _observation_rows_from_log(run_log: RunLog) -> list[dict]:
    """Pull every query_observations row out of the run log's act steps."""
    rows: list[dict] = []
    for step in run_log.steps:
        if step.node != "act":
            continue
        if step.payload.get("tool_name") != "query_observations":
            continue
        rows.extend(step.payload.get("output", {}).get("rows", []))
    return rows


async def draft(question: str, run_log: RunLog, ctx: ToolContext) -> Draft:
    """Compose a grounded draft from verified observations gathered so far.

    Every sentence carries a Citation referencing the observation_id it
    reports. Emits ``agent.draft`` recording the sentence/citation counts.
    """
    rows = _observation_rows_from_log(run_log)

    sentences: list[str] = []
    citations: list[Citation] = []
    for row in rows:
        unit = f" {row['unit']}" if row.get("unit") else ""
        sentences.append(
            f"Your verified {row['analyte']} result was {row['value']}{unit} "
            f"(collected {row['collected_at']})."
        )
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
