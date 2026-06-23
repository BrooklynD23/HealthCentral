"""retrieve_chunks tool (Phase 2, story S2-1).

Read-only. Returns chunks ONLY from documents whose ``Document.status ==
"verified"`` — chunks carry no own verified flag and inherit it from the parent
document (docs/agile/RECONCILIATION.md R-5). A chunk handle from an unverified
document is never a valid groundedness source.
"""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from ..state import ToolContext
from .base import ToolInput, ToolOutput


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
        """SCAFFOLD: Sprint 2 (S2-1).

        Reuses the existing RAG retriever (modules/rag.py) but filters to chunks
        whose parent Document.status == "verified". Emits agent.act. READ ONLY.
        """
        raise NotImplementedError("S2-1: retrieve chunks from verified documents only")
