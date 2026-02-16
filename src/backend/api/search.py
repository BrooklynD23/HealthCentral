"""
Search API endpoints.

Hybrid full-text + semantic search with RRF ranking.
"""

import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth import RequireAuth, ProfileDbSession
from core.audit import log_search_event
from modules.search import SearchModule, SearchFilters

logger = logging.getLogger(__name__)

router = APIRouter()
MAX_SEARCH_OFFSET = 1000
MAX_SEARCH_WINDOW = 1000


class SearchResultItem(BaseModel):
    id: str
    type: str
    title: str
    score: float
    snippet: str
    highlight: str = ""
    collected_at: Optional[str] = None
    analyte: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    explanation: str = ""


class SearchResponseModel(BaseModel):
    results: list[SearchResultItem]
    total_count: int
    query: str
    mode: str


@router.get("", response_model=SearchResponseModel)
async def search(
    session: RequireAuth,
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    mode: str = Query("hybrid", description="Search mode: hybrid, text, or semantic"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0, le=MAX_SEARCH_OFFSET),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    analyte: Optional[str] = Query(None),
    abnormal_only: bool = Query(False),
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """
    Search observations and documents.

    Supports hybrid (FTS5 + semantic), text-only, or semantic-only modes.
    """
    profile_id = session.profile_id
    search_module = SearchModule()

    filters = SearchFilters(
        from_date=from_date,
        to_date=to_date,
        analyte=analyte,
        abnormal_only=abnormal_only,
    )
    fetch_window = min(limit + offset, MAX_SEARCH_WINDOW)

    if mode == "text":
        results = await search_module.search_fulltext(
            q, profile_db, profile_id, filters, limit=fetch_window,
        )
        total = len(results)
        results = results[offset:offset + limit]
        response_mode = "text"
    elif mode == "semantic":
        results_raw = await search_module.search_semantic(
            q, profile_db, profile_id, top_k=fetch_window,
        )
        total = len(results_raw)
        results = results_raw[offset:offset + limit]
        response_mode = "semantic"
    else:
        search_response = await search_module.search_hybrid(
            q, profile_db, profile_id, filters, limit=fetch_window,
        )
        total = search_response.total_count
        results = search_response.results[offset:offset + limit]
        response_mode = "hybrid"

    try:
        await log_search_event(
            db=master_db, profile_id=profile_id,
            query=q, mode=response_mode, result_count=total,
        )
        await master_db.commit()
    except Exception as e:
        logger.warning(f"Failed to log search event: {e}")

    return SearchResponseModel(
        results=[
            SearchResultItem(
                id=r.id,
                type=r.type,
                title=r.title,
                score=r.score,
                snippet=r.snippet,
                highlight=r.highlight,
                collected_at=r.collected_at.isoformat() if r.collected_at else None,
                analyte=r.analyte,
                value=r.value,
                unit=r.unit,
                explanation=r.explanation,
            )
            for r in results
        ],
        total_count=total,
        query=q,
        mode=response_mode,
    )


@router.get("/suggestions", response_model=list[str])
async def search_suggestions(
    session: RequireAuth,
    prefix: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(10, ge=1, le=50),
    profile_db: ProfileDbSession = None,
):
    """Autocomplete suggestions for analyte names."""
    search_module = SearchModule()
    return await search_module.get_suggestions(
        prefix=prefix,
        profile_db=profile_db,
        profile_id=session.profile_id,
        limit=limit,
    )
