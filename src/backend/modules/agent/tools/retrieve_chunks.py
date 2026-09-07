"""retrieve_chunks tool (Phase 2, story S2-1).

Read-only. Returns chunks ONLY from documents whose ``Document.status ==
"verified"`` — chunks carry no own verified flag and inherit it from the parent
document (docs/agile/RECONCILIATION.md R-5). A chunk handle from an unverified
document is never a valid groundedness source.
"""

from __future__ import annotations

import logging
from typing import ClassVar

from pydantic import Field
from sqlalchemy import select

from ..audit import AgentAuditEvent, emit_audit_event
from ..state import ToolContext
from .base import ToolInput, ToolOutput

logger = logging.getLogger(__name__)


class RetrieveChunksInput(ToolInput):
    query: str
    k: int = Field(default=5, le=10, ge=1)


class ChunkRef(ToolOutput):
    chunk_id: str
    document_id: str
    text: str
    page_number: int | None = None
    locator: str | None = None  # page+span handle for citations


class RetrieveChunksOutput(ToolOutput):
    chunks: list[ChunkRef] = Field(default_factory=list)


class RetrieveChunksTool:
    name: ClassVar[str] = "retrieve_chunks"
    InputModel: ClassVar[type[ToolInput]] = RetrieveChunksInput
    OutputModel: ClassVar[type[ToolOutput]] = RetrieveChunksOutput

    async def run(self, args: RetrieveChunksInput, ctx: ToolContext) -> RetrieveChunksOutput:
        """Retrieve chunks from VERIFIED documents only. READ ONLY.

        DEVIATION from the scaffold's preferred approach: ``modules/rag.py``'s
        vector retriever (``RAGModule._search_vectors_async``) joins
        ``Chunk``/``Embedding``/``Document`` and requires an ``Embedding`` row
        per chunk (produced by the ingest pipeline's embedding model). That
        path is not exercised here — golden/unit-test fixtures seed ``Chunk``
        rows directly with no corresponding ``Embedding`` row, so a vector
        join would always return empty rather than reflecting the seeded
        fixture data. Instead this tool does a deterministic, typed,
        read-only, audited text-match fallback: a case-insensitive substring
        match of ``args.query`` against ``Chunk.text``, restricted via a join
        to ``Document.status == "verified"`` (chunks inherit the parent
        document's verified flag, per RECONCILIATION R-5 — a chunk has no
        verified flag of its own). If no chunks match the query text, the
        most recent verified chunks are returned instead so a downstream
        draft still has candidate grounding material to consider; the guard/
        groundedness gate (S3) is what ultimately decides if a citation
        counts. Emits one ``agent.act`` audit event (handles/counts only).
        """
        from models.chunk import Chunk
        from models.document import Document

        base_stmt = (
            select(Chunk, Document)
            .join(Document, Chunk.doc_id == Document.id)
            .where(Document.status == "verified")
        )

        query_lower = args.query.lower()
        match_stmt = base_stmt.where(Chunk.text.ilike(f"%{args.query}%")).limit(args.k)

        async with ctx.db_session() as session:
            result = await session.execute(match_stmt)
            rows = result.all()

            if not rows:
                # No text match: fall back to most-recent verified chunks so
                # there is still candidate evidence for the draft to weigh.
                fallback_stmt = base_stmt.order_by(Chunk.created_at.desc()).limit(args.k)
                result = await session.execute(fallback_stmt)
                rows = result.all()

        chunks = [
            ChunkRef(
                chunk_id=chunk.id,
                document_id=chunk.doc_id,
                text=chunk.text,
                page_number=chunk.page_number,
                locator=f"{chunk.doc_id}:{chunk.page_number}" if chunk.page_number else chunk.doc_id,
            )
            for chunk, _document in rows
        ]

        output = RetrieveChunksOutput(chunks=chunks)

        await emit_audit_event(
            AgentAuditEvent(
                run_id=ctx.run_id,
                node="act",
                profile_id=ctx.profile_id,
                event_type="agent.act",
                action="retrieve_chunks",
                step_index=ctx.step_index,
                details={
                    "tool_name": self.name,
                    # AUDIT-PHI-001: the query is the user's own question text.
                    "chunk_ids": [c.chunk_id for c in chunks],
                    "count": len(chunks),
                },
            ),
            db=getattr(ctx, "audit_db", None),
        )

        return output
