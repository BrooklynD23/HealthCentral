"""
Search module.

Provides hybrid search combining:
- FTS5 full-text search on observations and chunks
- Semantic similarity using existing embeddings (SQL + cosine)
- Reciprocal Rank Fusion (RRF) for score combination

Design Decision DD-1: SQL+cosine for v1, no FAISS.
Design Decision DD-5: FTS5 on both observations and chunks.
"""

import html
import logging
import re
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
HTML_TAG_RE = re.compile(r"<[^>]+>")


def _snippet_to_plain_text(snippet: Optional[str]) -> str:
    """Return a plain-text snippet safe for direct rendering."""
    if not snippet:
        return ""
    without_tags = HTML_TAG_RE.sub("", snippet)
    return html.unescape(without_tags)


@dataclass
class SearchResult:
    """A single search result."""
    id: str
    type: str  # "observation" or "chunk"
    title: str
    score: float = 0.0
    snippet: str = ""
    highlight: str = ""
    collected_at: Optional[datetime] = None
    analyte: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    explanation: str = ""


@dataclass
class SearchFilters:
    """Filters for search queries."""
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    analyte: Optional[str] = None
    abnormal_only: bool = False


@dataclass
class SearchResponse:
    """Complete search response."""
    results: list[SearchResult] = field(default_factory=list)
    total_count: int = 0
    query: str = ""
    mode: str = "hybrid"


def reciprocal_rank_fusion(
    ranked_lists: list[list[SearchResult]],
    k: int = 60,
) -> list[SearchResult]:
    """
    Combine multiple ranked lists using Reciprocal Rank Fusion.

    score(doc) = sum(1 / (k + rank_i)) for each list i.
    """
    if not ranked_lists:
        return []

    scores: dict[str, float] = {}
    result_map: dict[str, SearchResult] = {}

    for ranked_list in ranked_lists:
        for rank, result in enumerate(ranked_list, start=1):
            rrf_score = 1.0 / (k + rank)
            scores[result.id] = scores.get(result.id, 0.0) + rrf_score
            if result.id not in result_map:
                result_map[result.id] = result

    # Sort by fused score descending
    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    fused_results = []
    for doc_id in sorted_ids:
        result = result_map[doc_id]
        result.score = scores[doc_id]
        fused_results.append(result)

    return fused_results


class SearchModule:
    """
    Hybrid search engine combining FTS5 and semantic similarity.
    """

    async def search_fulltext(
        self,
        query: str,
        profile_db: AsyncSession,
        profile_id: str,
        filters: Optional[SearchFilters] = None,
        limit: int = 20,
    ) -> list[SearchResult]:
        """Search using FTS5 on observations and chunks."""
        results = []

        # Sanitize query for FTS5
        safe_query = query.replace('"', '""')

        # Search observations FTS
        try:
            obs_sql = text("""
                SELECT o.id, o.analyte_canonical, o.value, o.unit, o.collected_at,
                       o.is_abnormal, snippet(observations_fts, 0, '', '', '...', 32) as snip,
                       rank
                FROM observations_fts
                JOIN observations o ON observations_fts.rowid = o.rowid
                WHERE observations_fts MATCH :query
                  AND o.profile_id = :profile_id
                ORDER BY rank
                LIMIT :limit
            """)
            params = {"query": f'"{safe_query}"', "profile_id": profile_id, "limit": limit}
            result = await profile_db.execute(obs_sql, params)
            for row in result.fetchall():
                r = SearchResult(
                    id=row.id,
                    type="observation",
                    title=row.analyte_canonical,
                    snippet=_snippet_to_plain_text(row.snip or ""),
                    analyte=row.analyte_canonical,
                    value=row.value,
                    unit=row.unit,
                    collected_at=row.collected_at,
                    explanation="Full-text match on observation",
                )
                if filters:
                    if filters.abnormal_only and not row.is_abnormal:
                        continue
                    if filters.from_date and row.collected_at and row.collected_at < filters.from_date:
                        continue
                    if filters.to_date and row.collected_at and row.collected_at > filters.to_date:
                        continue
                    if filters.analyte and row.analyte_canonical != filters.analyte:
                        continue
                results.append(r)
        except Exception as e:
            logger.warning(f"Observation FTS search failed: {e}")

        # Search chunks FTS
        try:
            chunk_sql = text("""
                SELECT c.id, c.doc_id, c.text, c.page_number,
                       snippet(chunks_fts, 0, '', '', '...', 48) as snip,
                       rank
                FROM chunks_fts
                JOIN chunks c ON chunks_fts.rowid = c.rowid
                WHERE chunks_fts MATCH :query
                ORDER BY rank
                LIMIT :limit
            """)
            chunk_params = {"query": f'"{safe_query}"', "limit": limit}
            result = await profile_db.execute(chunk_sql, chunk_params)
            for row in result.fetchall():
                results.append(SearchResult(
                    id=row.id,
                    type="chunk",
                    title=f"Document content (page {row.page_number or '?'})",
                    snippet=_snippet_to_plain_text(
                        row.snip or (row.text[:200] if row.text else "")
                    ),
                    explanation="Full-text match on document content",
                ))
        except Exception as e:
            logger.warning(f"Chunk FTS search failed: {e}")

        return results

    async def search_semantic(
        self,
        query: str,
        profile_db: AsyncSession,
        profile_id: str,
        top_k: int = 10,
    ) -> list[SearchResult]:
        """
        Semantic search using existing embeddings with SQL+cosine.

        Reuses the pattern from rag.py:_search_vectors_async.
        """
        try:
            from modules.rag import RAGModule
            rag = RAGModule()
            vector_results = await rag._search_vectors_async(
                query=query,
                profile_id=profile_id,
                top_k=top_k,
                profile_db=profile_db,
            )
            results = []
            for chunk_data, similarity in vector_results:
                results.append(SearchResult(
                    id=chunk_data.get("chunk_id", ""),
                    type="chunk",
                    title=chunk_data.get("doc_title", "Document"),
                    snippet=_snippet_to_plain_text((chunk_data.get("text", "") or "")[:200]),
                    score=similarity,
                    explanation=f"Semantic similarity: {similarity:.3f}",
                ))
            return results
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
            return []

    async def search_hybrid(
        self,
        query: str,
        profile_db: AsyncSession,
        profile_id: str,
        filters: Optional[SearchFilters] = None,
        limit: int = 20,
    ) -> SearchResponse:
        """Hybrid search combining FTS5 + semantic via RRF."""
        fts_results = await self.search_fulltext(
            query, profile_db, profile_id, filters, limit=limit
        )

        semantic_results = await self.search_semantic(
            query, profile_db, profile_id, top_k=limit
        )

        fused = reciprocal_rank_fusion([fts_results, semantic_results], k=60)

        return SearchResponse(
            results=fused[:limit],
            total_count=len(fused),
            query=query,
            mode="hybrid",
        )

    async def get_suggestions(
        self,
        prefix: str,
        profile_db: AsyncSession,
        profile_id: str,
        limit: int = 10,
    ) -> list[str]:
        """Autocomplete suggestions from observation analyte names."""
        safe_prefix = prefix.replace("'", "''")
        sql = text("""
            SELECT DISTINCT analyte_canonical
            FROM observations
            WHERE profile_id = :profile_id
              AND analyte_canonical LIKE :prefix
            ORDER BY analyte_canonical
            LIMIT :limit
        """)
        result = await profile_db.execute(sql, {
            "profile_id": profile_id,
            "prefix": f"{safe_prefix}%",
            "limit": limit,
        })
        return [row[0] for row in result.fetchall()]
