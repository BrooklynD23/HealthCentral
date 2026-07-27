"""lookup_reference tool (Phase 2, story S2-1).

Read-only lookup of curated reference ranges from the master-DB knowledge base.
Returns a stable ``handle`` that the groundedness mapping accepts as a source.
"""

from __future__ import annotations

import logging
from typing import ClassVar

from ..audit import AgentAuditEvent, emit_audit_event
from ..state import ToolContext
from .base import ToolInput, ToolOutput

logger = logging.getLogger(__name__)


class LookupReferenceInput(ToolInput):
    analyte: str


class ReferenceRange(ToolOutput):
    analyte: str
    low: float | None = None
    high: float | None = None
    unit: str | None = None


class LookupReferenceOutput(ToolOutput):
    reference: ReferenceRange | None = None
    handle: str  # curated-reference source handle for citations


class LookupReferenceTool:
    name: ClassVar[str] = "lookup_reference"
    InputModel: ClassVar[type[ToolInput]] = LookupReferenceInput
    OutputModel: ClassVar[type[ToolOutput]] = LookupReferenceOutput

    async def run(self, args: LookupReferenceInput, ctx: ToolContext) -> LookupReferenceOutput:
        """Look up a curated reference range from the master-DB knowledge base.

        This is master-DB curated data (``BiomarkerKnowledge``), NOT PHI, so it
        is read through ``core.database``'s own session factory rather than
        ``ctx.db_session()`` (which is scoped to the per-profile vault). If the
        master database isn't reachable in this context (e.g. unit tests with
        no live master DB/migrations), this degrades gracefully: ``reference``
        is ``None`` but a stable handle is still returned so a citation can
        still point at "no curated reference available" rather than crashing
        the run. READ ONLY. Emits one ``agent.act`` audit event.
        """
        handle = f"reference:{args.analyte.lower()}"
        reference: ReferenceRange | None = None

        try:
            from core.database import async_session_maker
            from .. import knowledge_lookup  # local import to keep this seam swappable

            async with async_session_maker() as session:
                reference = await knowledge_lookup.lookup_reference_range(
                    args.analyte, session
                )
        except Exception as exc:  # noqa: BLE001 - graceful degradation, not a crash
            logger.debug("lookup_reference: knowledge base unreachable for %s: %s", args.analyte, exc)
            reference = None

        output = LookupReferenceOutput(reference=reference, handle=handle)

        await emit_audit_event(
            AgentAuditEvent(
                run_id=ctx.run_id,
                node="act",
                profile_id=ctx.profile_id,
                event_type="agent.act",
                action="lookup_reference",
                step_index=ctx.step_index,
                details={
                    "tool_name": self.name,
                    # AUDIT-PHI-001: analyte names are clinical content.
                    "handle": handle,
                    "found": reference is not None,
                },
            ),
            db=getattr(ctx, "audit_db", None),
        )

        return output
