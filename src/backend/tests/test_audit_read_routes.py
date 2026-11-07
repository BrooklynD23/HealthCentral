"""HC-ARR-001..012: the vault read routes audit, and a guard keeps the class closed.

CLAUDE.md hard invariant: "Audit logging on every route that touches documents,
observations, or profile data." Eight GET routes read the per-profile vault and
wrote no audit row (chat session list and history, assistant memory settings,
feedback stats, medication list, detail, schedules, doses). HC-AUD-ORD-030 only
sees handlers from which a `.commit()` is reachable, so a read handler that never
committed was invisible to it (recurring-failures #9: an invariant enforced at
one site, not across its class).

HC-ARR-001..008  one per route: a 200 writes exactly one AuditLog with the session
                 profile_id and the event, entity and counts of the plan.
HC-ARR-009       sentinel strings seeded in the vault reach no audit row and no
                 app log line.
HC-ARR-010       fail closed: a master DB that cannot commit means the view is not
                 served, and the error body holds no sentinel.
HC-ARR-011       every handler in api/ reaches an audit sink or is named in
                 UNAUDITED_ROUTES with a reason; stale entries fail too.
HC-ARR-012       break-it: a new unaudited handler in a synthetic tree is reported.

Route tests go through HTTP via `tests/support/routes.py::route_client`
(recurring-failures #1).

Blind spot of HC-ARR-011, stated so nobody reads it as proof. The call graph links
calls by name and over-approximates (`x.foo()` reaches every def named `foo`), so a
handler can look audited through a name collision. And the guard sees handlers, not
paths: a handler that audits on one branch and returns on another passes, which is
exactly AUDIT-CHAT-LEGACY's gap. The per-route HTTP tests above are the proof of
behaviour; this guard only stops a new unaudited handler from appearing silently.
"""

from __future__ import annotations

import json
import logging
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Any, Optional

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import models.response_feedback  # noqa: F401  (MODELS-INIT-FEEDBACK: not in models/__init__ yet)
from api.assistant import router as assistant_router
from api.feedback import router as feedback_router
from api.medications import router as medications_router
from core.auth import get_profile_db_session
from core.database import Base
from core.profile_database import ProfileDatabaseBase
from models import DoseTaken, Medication, MedicationSchedule
from models.audit import AuditLog
from models.chat_session import ChatSession, ChatTurn
from models.response_feedback import ResponseFeedback
from tests.support.callgraph import Graph
from tests.support.routes import route_client

PROFILE = "profile-a"
OTHER_PROFILE = "profile-b"

SESSION_ID = str(uuid.uuid4())
MED_A = str(uuid.uuid4())  # the medication the detail, schedule and dose routes read
MED_B = str(uuid.uuid4())
MED_OTHER = str(uuid.uuid4())  # belongs to another profile: 403, never audited
MISSING_ID = str(uuid.uuid4())

# Enum-shaped on purpose: each one passes core.audit._ENUM_VALUE_RE, so the
# AUDIT-PHI-001 scrubber would keep it if a caller put it under an allowed key.
S_TITLE = "SENTINEL-QUESTION-ldl"
S_TURN = "SENTINEL-QUESTION-ldl-turn"
S_DRUG = "SENTINELDRUG"
S_NOTE = "SENTINELDOSENOTE"
S_TAG = "SENTINELTAG"
S_CORRECTION = "SENTINELCORRECTION"
S_MODEL = "SENTINELMODEL"
SENTINELS = (S_TITLE, S_TURN, S_DRUG, S_NOTE, S_TAG, S_CORRECTION, S_MODEL, "SENTINEL")


# --- harness ---------------------------------------------------------------


class _RecordingMasterDb:
    """Captures rows handed to the master DB (shape of tests/test_memory_audit.py)."""

    def __init__(self) -> None:
        self.added: list[object] = []
        self.commits = 0

    def add(self, obj: object) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commits += 1

    async def flush(self) -> None:  # pragma: no cover - not exercised
        pass

    def audit_rows(self) -> list[AuditLog]:
        return [o for o in self.added if type(o).__name__ == "AuditLog"]


class FailingCommitSession(AsyncSession):
    """Master session whose Nth commit (1-based) raises a disk error."""

    fail_on: int | None = None
    commits = 0

    async def commit(self) -> None:
        self.commits += 1
        if self.fail_on == self.commits:
            await self.rollback()
            raise OperationalError("COMMIT", {}, Exception("disk I/O error"))
        await super().commit()


@pytest_asyncio.fixture
async def vault():
    """A real in-memory vault holding the sentinels."""
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        await _seed(session)
        yield session
    finally:
        await session.close()
        await engine.dispose()


@pytest_asyncio.fixture
async def failing_master():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session = FailingCommitSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


def _med(id_: str, name: str, profile_id: str = PROFILE) -> Medication:
    return Medication(
        id=id_, profile_id=profile_id, name=name, dosage_amount=10.0,
        dosage_unit="mg", frequency="once_daily", instructions=S_NOTE,
    )


async def _seed(db: AsyncSession) -> None:
    """1 session with 3 turns, 3 feedback rows (2 positive), 2 active medications
    (one holds 1 schedule and 4 doses), 1 medication of another profile."""
    db.add(ChatSession(id=SESSION_ID, profile_id=PROFILE, title=S_TITLE))
    for i, role in enumerate(("user", "assistant", "user")):
        db.add(ChatTurn(
            id=str(uuid.uuid4()), session_id=SESSION_ID, profile_id=PROFILE,
            turn_index=i, role=role, content=S_TURN,
        ))
    for rating in (1, 1, -1):
        db.add(ResponseFeedback(
            id=str(uuid.uuid4()), profile_id=PROFILE, session_id=SESSION_ID,
            turn_id=str(uuid.uuid4()), rating=rating, correction_text=S_CORRECTION,
            feedback_tags=[S_TAG], model_name=S_MODEL, provider="llama_cpp",
        ))
    db.add(_med(MED_A, S_DRUG))
    db.add(_med(MED_B, S_DRUG + "B"))
    db.add(_med(MED_OTHER, S_DRUG + "OTHER", OTHER_PROFILE))
    await db.flush()
    db.add(MedicationSchedule(
        id=str(uuid.uuid4()), medication_id=MED_A, schedule_label="morning",
        target_time=time(8, 0),
    ))
    base = datetime(2026, 1, 1, 8, 0)
    for i in range(4):
        db.add(DoseTaken(
            id=str(uuid.uuid4()), medication_id=MED_A, taken_at=base + timedelta(days=i),
            log_method="manual", notes=S_NOTE,
        ))
    await db.commit()


@dataclass(frozen=True)
class Route:
    rid: str
    router: Any
    prefix: str
    url: str
    event_type: str
    entity_type: str
    entity_id: str
    details: Optional[dict]
    sentinel_in_body: str


ROUTES = [
    Route("HC-ARR-001", assistant_router, "/assistant", "/assistant/sessions",
          "assistant.session.list", "chat_session", "all", {"count": 1}, S_TITLE),
    Route("HC-ARR-002", assistant_router, "/assistant", f"/assistant/sessions/{SESSION_ID}",
          "assistant.session.view", "chat_session", SESSION_ID, {"count": 3}, S_TURN),
    Route("HC-ARR-003", assistant_router, "/assistant", "/assistant/memory-settings",
          "settings.assistant_memory.view", "settings", "assistant_memory", None, "global_default"),
    Route("HC-ARR-004", feedback_router, "/feedback", "/feedback/stats",
          "feedback.stats.view", "response_feedback", "all", {"count": 3}, S_TAG),
    Route("HC-ARR-005", medications_router, "/medications", "/medications/",
          "document.view", "document", "all",
          {"entity_type": "medication_list", "count": 2}, S_DRUG),
    Route("HC-ARR-006", medications_router, "/medications", f"/medications/{MED_A}",
          "document.view", "document", MED_A, {"entity_type": "medication"}, S_DRUG),
    Route("HC-ARR-007", medications_router, "/medications", f"/medications/{MED_A}/schedules",
          "document.view", "document", MED_A,
          {"entity_type": "medication_schedules", "count": 1}, "morning"),
    Route("HC-ARR-008", medications_router, "/medications", f"/medications/{MED_A}/doses",
          "document.view", "document", MED_A,
          {"entity_type": "medication_doses", "count": 4, "date_filter": False}, "manual"),
]
BY_ID = {r.rid: r for r in ROUTES}


@contextmanager
def _http(route: Route, master, vault, *, raise_server_exceptions: bool = True):
    with route_client(
        route.router, route.prefix, profile_id=PROFILE, master_db=master,
        raise_server_exceptions=raise_server_exceptions,
    ) as client:

        async def _vault():
            return vault

        client.app.dependency_overrides[get_profile_db_session] = _vault
        yield client


def _get(route: Route, master, vault, url: str | None = None, **kw):
    with _http(route, master, vault, **kw) as client:
        return client.get(url or route.url)


def _row_blob(row: AuditLog) -> str:
    return " ".join(str(getattr(row, c.name)) for c in row.__table__.columns)


def _assert_one_row(rid: str, *, master: _RecordingMasterDb, resp) -> None:
    route = BY_ID[rid]
    assert resp.status_code == 200, resp.text
    rows = master.audit_rows()
    assert len(rows) == 1, f"{rid}: GET {route.url} wrote {len(rows)} AuditLog rows, expected 1"
    row = rows[0]
    assert row.profile_id == PROFILE
    assert row.event_type == route.event_type
    assert row.entity_type == route.entity_type
    assert row.entity_id == route.entity_id
    got = json.loads(row.details_json) if row.details_json else None
    assert got == route.details, f"{rid}: details {got!r} != {route.details!r}"
    assert master.commits >= 1, f"{rid}: audit row was added but never committed"


async def _one_row(rid: str, vault) -> None:
    master = _RecordingMasterDb()
    resp = _get(BY_ID[rid], master, vault)
    _assert_one_row(rid, master=master, resp=resp)


# --- HC-ARR-001..008 -------------------------------------------------------


@pytest.mark.asyncio
async def test_hc_arr_001_session_list_writes_one_audit_row(vault):
    await _one_row("HC-ARR-001", vault)


@pytest.mark.asyncio
async def test_hc_arr_002_session_history_writes_one_audit_row(vault):
    await _one_row("HC-ARR-002", vault)


@pytest.mark.asyncio
async def test_hc_arr_003_memory_settings_writes_one_audit_row(vault):
    await _one_row("HC-ARR-003", vault)


@pytest.mark.asyncio
async def test_hc_arr_004_feedback_stats_writes_one_audit_row(vault):
    await _one_row("HC-ARR-004", vault)


@pytest.mark.asyncio
async def test_hc_arr_005_medication_list_writes_one_audit_row(vault):
    await _one_row("HC-ARR-005", vault)


@pytest.mark.asyncio
async def test_hc_arr_006_medication_detail_writes_one_audit_row(vault):
    await _one_row("HC-ARR-006", vault)


@pytest.mark.asyncio
async def test_hc_arr_007_medication_schedules_writes_one_audit_row(vault):
    await _one_row("HC-ARR-007", vault)


@pytest.mark.asyncio
async def test_hc_arr_008_medication_doses_writes_one_audit_row(vault):
    await _one_row("HC-ARR-008", vault)


@pytest.mark.asyncio
async def test_hc_arr_008b_doses_date_filter_is_a_boolean_not_the_date(vault):
    route = BY_ID["HC-ARR-008"]
    master = _RecordingMasterDb()
    resp = _get(route, master, vault, url=route.url + "?from_date=2026-01-03T00:00:00")
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 2  # the 3rd and 4th day
    (row,) = master.audit_rows()
    assert json.loads(row.details_json) == {
        "entity_type": "medication_doses", "count": 2, "date_filter": True,
    }
    assert "2026-01-03" not in _row_blob(row)


@pytest.mark.asyncio
async def test_hc_arr_008c_a_404_or_403_writes_no_view_row(vault):
    """The audit comes after the lookup and the access check, so a read that is
    refused leaves no "viewed" row for data that was never served."""
    refused = [
        (BY_ID["HC-ARR-002"], f"/assistant/sessions/{MISSING_ID}", 404),
        (BY_ID["HC-ARR-006"], f"/medications/{MISSING_ID}", 404),
        (BY_ID["HC-ARR-006"], f"/medications/{MED_OTHER}", 403),
        (BY_ID["HC-ARR-007"], f"/medications/{MISSING_ID}/schedules", 404),
        (BY_ID["HC-ARR-007"], f"/medications/{MED_OTHER}/schedules", 403),
        (BY_ID["HC-ARR-008"], f"/medications/{MISSING_ID}/doses", 404),
        (BY_ID["HC-ARR-008"], f"/medications/{MED_OTHER}/doses", 403),
    ]
    for route, url, code in refused:
        master = _RecordingMasterDb()
        resp = _get(route, master, vault, url=url)
        assert resp.status_code == code, (url, resp.status_code, resp.text)
        assert master.audit_rows() == [], f"{url} ({code}) wrote a view row"


# --- HC-ARR-009: no patient text in any row or log line --------------------


@pytest.mark.asyncio
async def test_hc_arr_009_sentinels_reach_no_audit_row_and_no_log(vault, caplog):
    caplog.set_level(logging.DEBUG)
    master = _RecordingMasterDb()
    for route in ROUTES:
        resp = _get(route, master, vault)
        assert resp.status_code == 200, (route.rid, resp.text)
        # The route did read the sentinel data, so the checks below are not vacuous.
        assert route.sentinel_in_body in resp.text, (route.rid, resp.text)

    # One row per GET, checked first: with no rows the leak checks pass vacuously.
    rows = master.audit_rows()
    assert len(rows) == len(ROUTES), f"{len(rows)} audit rows for {len(ROUTES)} GETs"

    for row in rows:
        blob = _row_blob(row)
        for s in SENTINELS:
            assert s not in blob, f"{s} reached an audit row: {blob}"
        for col in ("action", "entity_id", "details_json"):
            value = str(getattr(row, col) or "")
            assert not any(s in value for s in SENTINELS), (col, value)

    # SQL bound-parameter debug lines from the DB drivers are excluded: any read
    # of the seeded vault logs them. Everything the app itself logged is checked.
    app_logs = [
        r.getMessage() for r in caplog.records
        if not r.name.startswith(("aiosqlite", "sqlalchemy"))
    ]
    assert app_logs, "no app log lines captured; the log check would be vacuous"
    for line in app_logs:
        for s in SENTINELS:
            assert s not in line, f"{s} reached the app log: {line}"


# --- HC-ARR-010: fail closed ----------------------------------------------


@pytest.mark.asyncio
async def test_hc_arr_010_a_view_that_cannot_be_audited_is_not_served(vault, failing_master):
    for route in ROUTES:
        failing_master.commits = 0
        failing_master.fail_on = 1
        resp = _get(route, failing_master, vault, raise_server_exceptions=False)
        assert resp.status_code >= 500, (
            f"{route.rid}: GET {route.url} served {resp.status_code} although its audit "
            f"row could not be committed: {resp.text[:200]}"
        )
        for s in SENTINELS:
            assert s not in resp.text, f"{route.rid}: {s} in the error body"
    failing_master.fail_on = None
    rows = (await failing_master.execute(select(AuditLog))).scalars().all()
    assert rows == [], "a failed audit commit left a row behind"


# --- HC-ARR-011 / 012: the route inventory guard -----------------------------

_AUDIT_SINKS = ("create_audit_log", "audit_and_commit", "audit_intent")

UNAUDITED_ROUTES: dict[str, str] = {
    # No profile data. Static modules, the master knowledge base, process state.
    "api/assistant.py::get_test_intent":
        "no profile data: static test-intent module",
    "api/assistant.py::get_glossary_term":
        "no profile data: static glossary module",
    "api/interpretations.py::get_biomarker_knowledge":
        "no profile data: master knowledge base, 'Public knowledge - not patient-specific data'",
    "api/model_settings.py::list_tiers":
        "no profile data: tier catalogue and hardware tier (owner AUDIT-READ-SCOPE)",
    "api/model_settings.py::get_llm_provider":
        "no profile data: active provider and capability flags (owner AUDIT-READ-SCOPE)",
    "api/model_settings.py::get_environment_diagnostics":
        "no profile data: OCR, model, SQLCipher and GPU status (owner AUDIT-READ-SCOPE)",
    "api/model_settings.py::recheck_environment_diagnostics":
        "no profile data: same diagnostics as the GET (owner AUDIT-READ-SCOPE)",
    "api/model_settings.py::get_download_progress":
        "no profile data: model download progress, polled every 2 s "
        "(owner AUDIT-READ-SCOPE (a), labelled exception)",
    "api/notifications.py::send_test_notification":
        "no profile data: an OS toast with the request text, nothing read",
    "api/notifications.py::get_scheduler_status":
        "no profile data: process-wide scheduler state and counts",
    # Task 3 waits on the open L0 ruling PROVIDER-AUDIT.
    "api/model_settings.py::set_llm_provider":
        "process-wide runtime switch, no profile data; pending L0 ruling PROVIDER-AUDIT",
}


def _handler_reach(g: Graph) -> dict[str, bool]:
    """handler key -> whether any audit sink is reachable from it."""
    out = {}
    for h in g.handlers():
        reach = g.reachable(h)
        out[f"{h[0]}::{h[1]}"] = any(g.reaches(reach, s) for s in _AUDIT_SINKS)
    return out


_G = Graph()
_REACH = _handler_reach(_G)


def test_hc_arr_011_every_handler_audits_or_is_named_as_unaudited():
    assert len(_REACH) > 100, "handler discovery found too few routes"
    unlisted = sorted(k for k, audits in _REACH.items() if not audits and k not in UNAUDITED_ROUTES)
    assert not unlisted, (
        f"handlers that reach no audit sink and are not in UNAUDITED_ROUTES: {unlisted}"
    )
    no_handler = sorted(k for k in UNAUDITED_ROUTES if k not in _REACH)
    now_audits = sorted(k for k in UNAUDITED_ROUTES if _REACH.get(k))
    assert not no_handler, f"stale UNAUDITED_ROUTES entries naming no handler: {no_handler}"
    assert not now_audits, f"stale UNAUDITED_ROUTES entries that now audit: {now_audits}"
    for key, reason in UNAUDITED_ROUTES.items():
        assert key.startswith("api/") and "::" in key, key
        assert reason.startswith(("no profile data: ", "E-2 owns it", "process-wide runtime switch")), (
            key, reason,
        )


def _overlay(tmp_path, handler_src: str) -> Graph:
    (tmp_path / "api").mkdir()
    (tmp_path / "api" / "zz.py").write_text(
        "from fastapi import APIRouter\nrouter = APIRouter()\n" + handler_src)
    return Graph(tmp_path, ("api", "core", "modules"))


def test_hc_arr_012_break_it_new_unaudited_vault_read_is_reported(tmp_path):
    """A GET that reads profile_db and audits nothing is listed as unaudited, so
    HC-ARR-011 would fail on it; the audited twin is not."""
    g = _overlay(tmp_path, (
        '@router.get("/zz")\nasync def zz_read(profile_db=None):\n'
        "    return await profile_db.execute('select 1')\n"
        '@router.get("/yy")\nasync def zz_audited(profile_db=None, master_db=None):\n'
        "    rows = await profile_db.execute('select 1')\n"
        "    await audit_and_commit(master_db, None)\n"
        "    return rows\n"))
    reach = _handler_reach(g)
    unaudited = {k for k, audits in reach.items() if not audits}
    assert unaudited == {"api/zz.py::zz_read"}
    assert unaudited - set(UNAUDITED_ROUTES) == {"api/zz.py::zz_read"}
