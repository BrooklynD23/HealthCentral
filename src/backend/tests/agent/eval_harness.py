"""Eval harness skeleton (story S2-4).

Loads a golden case (see ``tests/agent/golden/*.json`` and ``conftest.
load_golden_cases``), materializes its ``vault`` block into an in-memory
profile database using the same seeding helpers unit tests use
(``seed_document``/``seed_observation``/``seed_chunk``), runs ``run_agent``
on the case's ``question``, and asserts the run's terminal matches
``expect``.

This is intentionally a SKELETON: it covers what the two S2 seed cases need
(``terminal`` and ``min_citations``). Later sprints (S6: evals gate CI) grow
this into the four-axis-scored, CI-gating harness; this module is the seam
that work extends, not a final harness.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from modules.agent.graph import RunContext, new_run_id, run_agent
from modules.agent.schemas import AgentTerminal

from .conftest import seed_chunk, seed_document, seed_observation


def _parse_collected_at(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


async def build_vault(case: dict, *, profile_id: str):
    """Materialize a golden case's ``vault`` block into a fresh in-memory DB.

    Returns the ``session_maker`` for the populated profile database. Vault
    shape (per the golden fixtures):

      ``observations``: [{name, value, unit, collected_at, verified}, ...]
      ``documents``:     [{id, status}, ...]
      ``chunks``:        [{id, document_id, text}, ...]

    Observations with no explicit document reference are attached to a
    single auto-created "default" document (most golden cases don't care
    which document an observation belongs to, only its own verified flag);
    cases that DO specify ``documents``/``chunks`` get those exact rows,
    keyed by the ids given in the fixture so chunk->document linkage in the
    fixture is preserved.
    """
    from core.profile_database import ProfileDatabaseBase
    from models import document, observation, chunk  # noqa: F401  (register tables)

    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    vault = case.get("vault", {})

    documents = vault.get("documents", [])
    doc_ids: dict[str, str] = {}
    for doc in documents:
        doc_id = await seed_document(session_maker, profile_id=profile_id, doc_id=doc["id"])
        doc_ids[doc["id"]] = doc_id
        # seed_document always inserts status="verified"; only patch it if
        # this fixture explicitly wants something else.
        if doc.get("status") != "verified":
            from sqlalchemy import update as sa_update

            from models.document import Document

            async with session_maker() as session:
                await session.execute(
                    sa_update(Document).where(Document.id == doc_id).values(status=doc["status"])
                )
                await session.commit()

    # Observations attach to whichever document the fixture declared, or to
    # one auto-created "default" document if the fixture didn't bother
    # declaring any (most golden cases only care about the observation's own
    # verified flag, not which document backs it).
    if doc_ids:
        default_doc_id = next(iter(doc_ids.values()))
    else:
        default_doc_id = str(uuid.uuid4())
        await seed_document(session_maker, profile_id=profile_id, doc_id=default_doc_id)

    for obs in vault.get("observations", []):
        await seed_observation(
            session_maker,
            profile_id=profile_id,
            doc_id=default_doc_id,
            analyte=obs["name"],
            value=obs["value"],
            unit=obs.get("unit"),
            verified=bool(obs.get("verified", False)),
            collected_at=_parse_collected_at(obs.get("collected_at")),
        )

    for chunk_def in vault.get("chunks", []):
        document_id = doc_ids.get(chunk_def["document_id"], chunk_def["document_id"])
        await seed_chunk(
            session_maker,
            doc_id=document_id,
            text=chunk_def["text"],
            chunk_id=chunk_def.get("id"),
        )

    return session_maker


async def run_golden_case(case: dict) -> tuple[AgentTerminal, list[str]]:
    """Run one golden case end-to-end through ``run_agent``.

    Returns ``(terminal, failures)`` where ``failures`` is a list of
    human-readable mismatches against ``case["expect"]`` (empty == pass).
    Checks ``terminal`` always; checks ``min_citations`` when present in
    ``expect``. (Reason-string / advice-leakage / drops_unmapped axes are out
    of scope for this skeleton — S6 grows the harness to score those.)
    """
    profile_id = str(uuid.uuid4())
    session_maker = await build_vault(case, profile_id=profile_id)

    @asynccontextmanager
    async def _db_session():
        async with session_maker() as session:
            yield session

    ctx = RunContext(
        profile_id=profile_id,
        run_id=new_run_id(),
        db_session_factory=_db_session,
    )

    terminal = await run_agent(case["question"], ctx)

    expect = case["expect"]
    failures: list[str] = []

    if terminal.terminal != expect["terminal"]:
        failures.append(
            f"terminal: expected {expect['terminal']!r}, got {terminal.terminal!r}"
        )

    if "min_citations" in expect and len(terminal.citations) < expect["min_citations"]:
        failures.append(
            f"min_citations: expected >= {expect['min_citations']}, got {len(terminal.citations)}"
        )

    return terminal, failures
