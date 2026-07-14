"""Bounded, audit-logged local search over one profile database (HC-M21)."""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit import audit_and_commit, create_audit_log
from core.auth import ProfileDbSession, RequireAuth
from core.database import get_db
from modules.highlights import HIGHLIGHT_TYPES
from modules.search import SearchResult, search_records

router = APIRouter()


class SearchResultResponse(BaseModel):
    """A bounded hit from the encrypted profile database."""

    type: str
    id: str
    doc_id: str
    title: str
    snippet: str
    date: Optional[str] = None
    verified_status: str
    category: Optional[str] = None
    highlight_types: list[str]

    @classmethod
    def from_result(cls, result: SearchResult) -> "SearchResultResponse":
        return cls(
            type=result.record_type,
            id=result.record_id,
            doc_id=result.doc_id,
            title=result.title,
            snippet=result.snippet,
            date=result.record_date,
            verified_status=result.verified_status,
            category=result.category,
            highlight_types=result.highlight_types,
        )


class SearchResponse(BaseModel):
    results: list[SearchResultResponse]
    count: int


@router.get("/", response_model=SearchResponse)
async def get_search_results(
    session: RequireAuth,
    q: str = Query(..., min_length=1, max_length=200, description="Search text"),
    provider: Optional[str] = Query(None, max_length=100, description="Filter by provider"),
    date_from: Optional[date] = Query(None, description="Inclusive start date"),
    date_to: Optional[date] = Query(None, description="Inclusive end date"),
    category: Optional[str] = Query(None, max_length=50, description="Filter by category"),
    highlight_type: Optional[str] = Query(
        None, max_length=50, description="Filter by smart-highlight type"
    ),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    profile_db: ProfileDbSession = None,
    master_db: AsyncSession = Depends(get_db),
):
    """Search documents, extracted entities, and observations locally."""
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from must be on or before date_to",
        )
    if highlight_type is not None and highlight_type not in HIGHLIGHT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown highlight_type. Valid values: {sorted(HIGHLIGHT_TYPES)}",
        )

    results = await search_records(
        profile_db,
        session.profile_id,
        q.strip(),
        provider=provider,
        date_from=date_from,
        date_to=date_to,
        category=category,
        highlight_type=highlight_type,
        limit=limit,
    )

    await audit_and_commit(
        master_db,
        create_audit_log,
        event_type="search.view",
        action="Searched health records",
        profile_id=session.profile_id,
        entity_type="search",
        entity_id="all",
        details={
            "count": len(results),
            "limit": limit,
            "provider_filter": provider is not None,
            "date_filter": date_from is not None or date_to is not None,
            "category": category,
            "highlight_type": highlight_type,
        },
    )

    response_results = [SearchResultResponse.from_result(result) for result in results]
    return SearchResponse(results=response_results, count=len(response_results))
