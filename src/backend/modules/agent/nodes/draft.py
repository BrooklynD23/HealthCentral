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

HC-M24 (Phase E, bounded agentic queries): also composes grounded
record-navigation sentences from ``query_care_tasks``/
``query_medication_changes``/``query_timeline`` output — one sentence per
row plus a single summary sentence per tool call (mirrors the trend
composition's "per-point sentence + one summary citing every point"
shape). ``title``/``source_quote``/``entity_value``/``quote`` are already
sanitized by their tools (unlike ``analyte``/``unit`` above, which the tool
leaves raw and THIS module sanitizes) — see each tool's module docstring —
so draft composes them as-is, framed as record-keeping only ("The note
says: …", "You have N open follow-up items"), never advice.
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
            Citation(source_type="document", source_id=p["observation_id"], locator=p["observation_id"], source_kind="observation")
            for p in points
        ]

        for p in points:
            unit = ""  # TrendPoint carries no unit; value-only point sentence
            sentences.append(f"Your verified {analyte} result was {p['value']}{unit} (collected {p['collected_at']}).")
            citations.append(
                Citation(source_type="document", source_id=p["observation_id"], locator=p["observation_id"], source_kind="observation")
            )

        if len(points) >= 2:
            direction = output.get("direction", "flat")
            verb = {"up": "increased", "down": "decreased", "flat": "stayed about the same"}[direction]
            sentences.append(f"Your {analyte} has {verb} across your verified results.")
            citations.extend(point_citations)

    return sentences, citations


def _care_task_sentences(run_log: RunLog) -> tuple[list[str], list[Citation]]:
    """Compose grounded follow-up-task sentences from query_care_tasks outputs.

    One sentence per task row, citing that task's ``task_id``, plus a single
    "You have N ... follow-up items" summary sentence citing every row (same
    "per-row + trailing summary" shape as ``_trend_sentences``). Fields are
    already sanitized by the tool (see tools/query_care_tasks.py) — this
    composes them as-is, record-keeping framing only.
    """
    sentences: list[str] = []
    citations: list[Citation] = []

    for output in _act_outputs(run_log, "query_care_tasks"):
        rows = output.get("rows", [])
        if not rows:
            continue

        row_citations = [
            Citation(source_type="document", source_id=r["task_id"], locator=r["task_id"], source_kind="task")
            for r in rows
        ]

        for row in rows:
            due = f" (due {row['due_date']})" if row.get("due_date") else ""
            quote = row.get("source_quote")
            quote_part = f' The note says: "{quote}"' if quote else ""
            sentences.append(f"Open follow-up: {row['title']}{due}.{quote_part}")
            citations.append(
                Citation(source_type="document", source_id=row["task_id"], locator=row["task_id"], source_kind="task")
            )

        status = rows[0].get("status", "open") if len({r.get("status") for r in rows}) == 1 else "matching"
        plural = "s" if len(rows) != 1 else ""
        sentences.append(f"You have {len(rows)} {status} follow-up item{plural}.")
        citations.extend(row_citations)

    return sentences, citations


def _med_change_sentences(run_log: RunLog) -> tuple[list[str], list[Citation]]:
    """Compose grounded medication-change sentences from query_medication_changes outputs.

    One sentence per entity row, citing that entity's ``entity_id``, plus a
    single "You have N recorded medication changes" summary sentence citing
    every row. Fields are already sanitized by the tool (see
    tools/query_medication_changes.py) — this composes them as-is,
    record-keeping framing only.
    """
    sentences: list[str] = []
    citations: list[Citation] = []

    for output in _act_outputs(run_log, "query_medication_changes"):
        rows = output.get("rows", [])
        if not rows:
            continue

        row_citations = [
            Citation(source_type="document", source_id=r["entity_id"], locator=r["doc_id"], source_kind="entity")
            for r in rows
        ]

        for row in rows:
            date_part = f" ({row['document_date']})" if row.get("document_date") else ""
            quote = row.get("quote")
            quote_part = f' The note says: "{quote}"' if quote else ""
            sentences.append(f"Medication change: {row['entity_value']}{date_part}.{quote_part}")
            citations.append(
                Citation(source_type="document", source_id=row["entity_id"], locator=row["doc_id"], source_kind="entity")
            )

        plural = "s" if len(rows) != 1 else ""
        sentences.append(f"You have {len(rows)} recorded medication change{plural}.")
        citations.extend(row_citations)

    return sentences, citations


def _timeline_sentences(run_log: RunLog) -> tuple[list[str], list[Citation]]:
    """Compose grounded history sentences from query_timeline outputs.

    query_timeline returns every event with its ``verification_status``
    (build_timeline emits "unverified"/"mixed" for unverified observations
    or documents — see modules/timeline.py). Only events whose status is
    "verified" or "n/a" (no verification concept applies, e.g. a medication
    start/stop entry) get a full grounded sentence, one per event, citing
    that event's ``event_id`` (timeline events are already their own
    deterministic source handle). This mirrors query_observations/
    query_medication_changes, which only ever surface verified rows — an
    unverified/mixed event must never be presented as established history
    with no label. Verified events get a single "Your history includes N
    recorded events" summary sentence citing every one of them; any
    excluded (unverified/mixed) events are rolled into a single labeled
    "N more recorded event(s) pending your verification" sentence citing
    one of them, so the pending count itself stays grounded. ``title`` is
    already sanitized by the tool (see tools/query_timeline.py).
    """
    sentences: list[str] = []
    citations: list[Citation] = []

    for output in _act_outputs(run_log, "query_timeline"):
        rows = output.get("rows", [])
        if not rows:
            continue

        verified_rows = [r for r in rows if r.get("verification_status") in ("verified", "n/a")]
        pending_rows = [r for r in rows if r.get("verification_status") not in ("verified", "n/a")]

        row_citations = [
            Citation(source_type="document", source_id=r["event_id"], locator=r.get("doc_id"), source_kind="event")
            for r in verified_rows
        ]

        for row in verified_rows:
            date_part = f" on {row['event_date']}" if row.get("event_date") else ""
            sentences.append(f"{row['title']}{date_part}.")
            citations.append(
                Citation(source_type="document", source_id=row["event_id"], locator=row.get("doc_id"), source_kind="event")
            )

        if verified_rows:
            plural = "s" if len(verified_rows) != 1 else ""
            sentences.append(f"Your history includes {len(verified_rows)} recorded event{plural}.")
            citations.extend(row_citations)

        if pending_rows:
            plural = "s" if len(pending_rows) != 1 else ""
            sentences.append(
                f"You have {len(pending_rows)} more recorded event{plural} pending your verification."
            )
            citations.append(
                Citation(
                    source_type="document",
                    source_id=pending_rows[0]["event_id"],
                    locator=pending_rows[0].get("doc_id"),
                )
            )

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

    care_task_sentences, care_task_citations = _care_task_sentences(run_log)
    sentences.extend(care_task_sentences)
    citations.extend(care_task_citations)

    med_change_sentences, med_change_citations = _med_change_sentences(run_log)
    sentences.extend(med_change_sentences)
    citations.extend(med_change_citations)

    timeline_sentences, timeline_citations = _timeline_sentences(run_log)
    sentences.extend(timeline_sentences)
    citations.extend(timeline_citations)

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
