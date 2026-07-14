"""Runtime-managed local search index for one encrypted profile database.

The canonical ``search_records`` table and its FTS5 mirror are derived,
rebuildable data inside the per-profile SQLCipher database.  No migration is
required.  If FTS5 is unavailable, queries use ``LIKE`` against the canonical
rows and return the same result shape and filters.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from models import Chunk, Document, DocumentCategory, DocumentEntity, Observation
from modules.highlights import derive_entity_highlights, derive_observation_highlights

logger = logging.getLogger(__name__)

_PROVIDER_ENTITY_TYPES = {"provider", "ordering_provider"}

_CREATE_RECORDS_SQL = """
CREATE TABLE IF NOT EXISTS search_records (
    row_key TEXT PRIMARY KEY,
    record_type TEXT NOT NULL,
    record_id TEXT NOT NULL,
    doc_id TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    record_date TEXT,
    provider TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT '',
    verified_status TEXT NOT NULL,
    highlight_types TEXT NOT NULL DEFAULT ''
)
"""

_CREATE_FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS search_records_fts USING fts5(
    row_key UNINDEXED,
    record_type UNINDEXED,
    record_id UNINDEXED,
    doc_id UNINDEXED,
    profile_id UNINDEXED,
    title,
    content,
    record_date UNINDEXED,
    provider UNINDEXED,
    category UNINDEXED,
    verified_status UNINDEXED,
    highlight_types UNINDEXED,
    tokenize='unicode61'
)
"""

_INSERT_SQL = """
INSERT INTO search_records (
    row_key, record_type, record_id, doc_id, profile_id, title, content,
    record_date, provider, category, verified_status, highlight_types
) VALUES (
    :row_key, :record_type, :record_id, :doc_id, :profile_id, :title, :content,
    :record_date, :provider, :category, :verified_status, :highlight_types
)
"""

_INSERT_FTS_SQL = _INSERT_SQL.replace("search_records (", "search_records_fts (")


@dataclass(frozen=True)
class SearchResult:
    """One document, extracted entity, or observation search hit."""

    record_type: str
    record_id: str
    doc_id: str
    title: str
    snippet: str
    record_date: Optional[str]
    verified_status: str
    category: Optional[str]
    highlight_types: list[str]


async def _create_record_table(db: AsyncSession) -> None:
    await db.execute(text(_CREATE_RECORDS_SQL))


async def _create_fts_table(db: AsyncSession) -> None:
    await db.execute(text(_CREATE_FTS_SQL))


async def ensure_search_index(db: AsyncSession) -> bool:
    """Idempotently ensure runtime tables; return whether FTS5 is usable."""
    await _create_record_table(db)
    try:
        await _create_fts_table(db)
        await db.commit()
        return True
    except SQLAlchemyError as exc:
        await db.rollback()
        await _create_record_table(db)
        await db.commit()
        logger.info("FTS5 unavailable; local search will use LIKE fallback: %s", exc)
        return False


def _iso_day(value) -> Optional[str]:
    if value is None:
        return None
    return value.date().isoformat() if hasattr(value, "date") else str(value)


def _filename(source: Optional[str]) -> str:
    if not source:
        return "Imported document"
    return source.replace("\\", "/").rsplit("/", 1)[-1]


def _humanize(value: str) -> str:
    return value.replace("_", " ").strip().capitalize()


def _observation_content(observation: Observation) -> str:
    value = observation.value_text
    if value is None and observation.value is not None:
        value = str(observation.value)
    parts = [observation.analyte_raw, observation.analyte_canonical]
    if value is not None:
        parts.append(value)
    if observation.unit:
        parts.append(observation.unit)
    if observation.notes:
        parts.append(observation.notes)
    return " ".join(parts)


async def _build_rows(db: AsyncSession, profile_id: str) -> list[dict]:
    document_result = await db.execute(
        select(Document).where(Document.profile_id == profile_id)
    )
    documents = list(document_result.scalars().all())
    if not documents:
        return []

    doc_ids = [document.id for document in documents]
    category_result = await db.execute(
        select(DocumentCategory).where(DocumentCategory.doc_id.in_(doc_ids))
    )
    categories = {
        item.doc_id: item.category for item in category_result.scalars().all()
    }
    entity_result = await db.execute(
        select(DocumentEntity).where(DocumentEntity.doc_id.in_(doc_ids))
    )
    entities = list(entity_result.scalars().all())
    observation_result = await db.execute(
        select(Observation).where(
            Observation.profile_id == profile_id,
            Observation.doc_id.in_(doc_ids),
        )
    )
    observations = list(observation_result.scalars().all())
    chunk_result = await db.execute(
        select(Chunk)
        .where(Chunk.doc_id.in_(doc_ids))
        .order_by(Chunk.doc_id, Chunk.chunk_index)
    )

    chunks_by_doc: dict[str, list[str]] = {}
    for chunk in chunk_result.scalars().all():
        chunks_by_doc.setdefault(chunk.doc_id, []).append(chunk.text)

    entities_by_doc: dict[str, list[DocumentEntity]] = {}
    providers_by_doc: dict[str, list[str]] = {}
    for entity in entities:
        entities_by_doc.setdefault(entity.doc_id, []).append(entity)
        if entity.entity_type in _PROVIDER_ENTITY_TYPES and entity.verified_by_user is not False:
            providers_by_doc.setdefault(entity.doc_id, []).append(entity.entity_value)

    observations_by_doc: dict[str, list[Observation]] = {}
    for observation in observations:
        observations_by_doc.setdefault(observation.doc_id, []).append(observation)

    source_highlights: dict[tuple[str, str], set[str]] = {}
    highlights = derive_entity_highlights(entities) + derive_observation_highlights(
        observations
    )
    for highlight in highlights:
        source_highlights.setdefault(
            (highlight.source_kind, highlight.source_id), set()
        ).add(highlight.highlight_type)

    document_by_id = {document.id: document for document in documents}
    rows: list[dict] = []
    for document in documents:
        doc_highlights: set[str] = set()
        for entity in entities_by_doc.get(document.id, []):
            doc_highlights.update(source_highlights.get(("entity", entity.id), set()))
        for observation in observations_by_doc.get(document.id, []):
            doc_highlights.update(
                source_highlights.get(("observation", observation.id), set())
            )
        rows.append(
            _row(
                row_key=f"document:{document.id}",
                record_type="document",
                record_id=document.id,
                doc_id=document.id,
                profile_id=profile_id,
                title=_filename(document.source),
                content="\n".join(chunks_by_doc.get(document.id, [])),
                record_date=_iso_day(document.collection_date or document.imported_at),
                provider=" | ".join(providers_by_doc.get(document.id, [])),
                category=categories.get(document.id, ""),
                verified_status=(
                    "verified" if document.status == "verified" else "unverified"
                ),
                highlight_types=doc_highlights,
            )
        )

    for entity in entities:
        if entity.verified_by_user is False:
            continue
        document = document_by_id[entity.doc_id]
        rows.append(
            _row(
                row_key=f"entity:{entity.id}",
                record_type="entity",
                record_id=entity.id,
                doc_id=entity.doc_id,
                profile_id=profile_id,
                title=f"{_humanize(entity.entity_type)} — {entity.entity_value}",
                content=" ".join(part for part in (entity.entity_value, entity.quote) if part),
                record_date=_iso_day(document.collection_date or document.imported_at),
                provider=" | ".join(providers_by_doc.get(entity.doc_id, [])),
                category=categories.get(entity.doc_id, entity.category),
                verified_status=(
                    "verified" if entity.verified_by_user is True else "unverified"
                ),
                highlight_types=source_highlights.get(("entity", entity.id), set()),
            )
        )

    for observation in observations:
        document = document_by_id[observation.doc_id]
        rows.append(
            _row(
                row_key=f"observation:{observation.id}",
                record_type="observation",
                record_id=observation.id,
                doc_id=observation.doc_id,
                profile_id=profile_id,
                title=observation.analyte_raw or observation.analyte_canonical,
                content=_observation_content(observation),
                record_date=_iso_day(
                    observation.collected_at
                    or document.collection_date
                    or document.imported_at
                ),
                provider=" | ".join(providers_by_doc.get(observation.doc_id, [])),
                category=categories.get(observation.doc_id, ""),
                verified_status=(
                    "verified" if observation.user_verified else "unverified"
                ),
                highlight_types=source_highlights.get(
                    ("observation", observation.id), set()
                ),
            )
        )
    return rows


def _row(*, highlight_types: set[str], **values) -> dict:
    values["highlight_types"] = "|" + "|".join(sorted(highlight_types)) + "|"
    return values


async def _replace_rows(
    db: AsyncSession, profile_id: str, rows: list[dict], *, use_fts: bool
) -> None:
    await db.execute(
        text("DELETE FROM search_records WHERE profile_id = :profile_id"),
        {"profile_id": profile_id},
    )
    if use_fts:
        await db.execute(
            text("DELETE FROM search_records_fts WHERE profile_id = :profile_id"),
            {"profile_id": profile_id},
        )
    if rows:
        await db.execute(text(_INSERT_SQL), rows)
        if use_fts:
            await db.execute(text(_INSERT_FTS_SQL), rows)
    await db.commit()


async def refresh_search_index(
    db: AsyncSession, profile_id: str, *, use_fts: bool
) -> bool:
    """Rebuild all derived rows for a profile; return the usable query mode."""
    rows = await _build_rows(db, profile_id)
    try:
        await _replace_rows(db, profile_id, rows, use_fts=use_fts)
        return use_fts
    except SQLAlchemyError as exc:
        if not use_fts:
            raise
        await db.rollback()
        logger.info("FTS5 refresh failed; rebuilding LIKE rows only: %s", exc)
        await _create_record_table(db)
        await _replace_rows(db, profile_id, rows, use_fts=False)
        return False


def _filter_sql(filters: dict, params: dict) -> str:
    conditions = ["profile_id = :profile_id"]
    if filters.get("provider"):
        conditions.append("lower(provider) LIKE :provider")
        params["provider"] = f"%{filters['provider'].lower()}%"
    if filters.get("date_from"):
        conditions.append("record_date >= :date_from")
        params["date_from"] = filters["date_from"].isoformat()
    if filters.get("date_to"):
        conditions.append("record_date <= :date_to")
        params["date_to"] = filters["date_to"].isoformat()
    if filters.get("category"):
        conditions.append("lower(category) = :category")
        params["category"] = filters["category"].lower()
    if filters.get("highlight_type"):
        conditions.append("highlight_types LIKE :highlight_type")
        params["highlight_type"] = f"%|{filters['highlight_type']}|%"
    return " AND ".join(conditions)


def _fts_expression(query: str) -> Optional[str]:
    tokens = re.findall(r"\w+", query, flags=re.UNICODE)
    if not tokens:
        return None
    return " AND ".join(f'"{token.replace(chr(34), chr(34) * 2)}"*' for token in tokens)


async def _search_fts(db: AsyncSession, query: str, params: dict, where: str):
    expression = _fts_expression(query)
    if expression is None:
        return []
    params["match_query"] = expression
    statement = text(
        f"""
        SELECT record_type, record_id, doc_id, title,
               snippet(search_records_fts, 6, '', '', ' … ', 24) AS snippet,
               record_date, verified_status, category, highlight_types
        FROM search_records_fts
        WHERE search_records_fts MATCH :match_query AND {where}
        ORDER BY bm25(search_records_fts), record_date DESC, row_key
        LIMIT :limit
        """
    )
    return (await db.execute(statement, params)).mappings().all()


async def _search_like(db: AsyncSession, query: str, params: dict, where: str):
    params["like_query"] = f"%{query.lower()}%"
    statement = text(
        f"""
        SELECT record_type, record_id, doc_id, title, content AS snippet,
               record_date, verified_status, category, highlight_types
        FROM search_records
        WHERE (lower(title) LIKE :like_query OR lower(content) LIKE :like_query)
          AND {where}
        ORDER BY record_date DESC, row_key
        LIMIT :limit
        """
    )
    return (await db.execute(statement, params)).mappings().all()


def _bounded_snippet(value: str, query: str) -> str:
    clean = " ".join((value or "").split())
    if len(clean) <= 280:
        return clean
    match_at = clean.lower().find(query.lower())
    start = max(0, match_at - 100) if match_at >= 0 else 0
    end = min(len(clean), start + 280)
    return ("…" if start else "") + clean[start:end] + ("…" if end < len(clean) else "")


def _to_result(row, query: str) -> SearchResult:
    return SearchResult(
        record_type=row["record_type"],
        record_id=row["record_id"],
        doc_id=row["doc_id"],
        title=row["title"],
        snippet=_bounded_snippet(row["snippet"] or row["title"], query),
        record_date=row["record_date"],
        verified_status=row["verified_status"],
        category=row["category"] or None,
        highlight_types=[item for item in row["highlight_types"].split("|") if item],
    )


async def search_records(
    db: AsyncSession,
    profile_id: str,
    query: str,
    *,
    provider: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    category: Optional[str] = None,
    highlight_type: Optional[str] = None,
    limit: int = 50,
) -> list[SearchResult]:
    """Refresh and query one profile's local index with identical filters."""
    use_fts = await ensure_search_index(db)
    use_fts = await refresh_search_index(db, profile_id, use_fts=use_fts)
    params = {"profile_id": profile_id, "limit": limit}
    filters = {
        "provider": provider,
        "date_from": date_from,
        "date_to": date_to,
        "category": category,
        "highlight_type": highlight_type,
    }
    where = _filter_sql(filters, params)
    if use_fts:
        try:
            rows = await _search_fts(db, query, params, where)
        except SQLAlchemyError as exc:
            logger.info("FTS5 query failed; using LIKE fallback: %s", exc)
            rows = await _search_like(db, query, params, where)
    else:
        rows = await _search_like(db, query, params, where)
    return [_to_result(row, query) for row in rows]
