"""W-2 / owner decision D3 (2026-09-27): doctor-summary redaction (HC-EXPR-NNN).

The doctor summary goes to a third party, so it passes strict
modules/redaction.py before it is stored or rendered, in every download format
(text, html, pdf). CSV and JSON are the patient's own full-fidelity export and
stay byte-for-byte unredacted (named exceptions, W-10).

Scope of the claim: labelled name/DOB/MRN in free-text fields. Underscore-joined
identifiers are a known, owner-gated gap (O-3), pinned by a strict xfail.

Every test drives FastAPI's dependency graph through
tests/support/routes.py::route_client (recurring-failures #1).
"""

from __future__ import annotations

import io
import json
import os
import sys
import types
from contextlib import ExitStack, contextmanager
from datetime import datetime
from types import SimpleNamespace
from typing import Iterator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

import api.export as export_api
from core.auth import get_profile_db_session
from tests.support.routes import route_client

PROFILE_A = "profile-a"
PROFILE_B = "profile-b"

# PHI seeded into the free-text fields the summary renders (unit, flag), in the
# labelled shapes the strict engine documents (name_context, dob, mrn).
PHI_STRINGS = ("Jane", "Doe", "01/02/1980", "A12345")


def _obs(
    obs_id: str,
    analyte: str,
    value: float,
    unit: str,
    flag: str | None,
    collected_at: datetime,
    ref_low: float,
    ref_high: float,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=obs_id,
        profile_id=PROFILE_A,
        analyte_canonical=analyte,
        analyte_raw=analyte,
        value=value,
        value_text=None,
        unit=unit,
        ref_low=ref_low,
        ref_high=ref_high,
        ref_range_text=None,
        flag=flag,
        is_abnormal=flag is not None,
        user_verified=False,
        collected_at=collected_at,
    )


PHI_ROWS = (
    _obs("00000000-0000-4000-8000-000000000001", "glucose", 100.0, "mg/dL", None, datetime(2024, 1, 10), 70.0, 99.0),
    _obs("00000000-0000-4000-8000-000000000002", "glucose", 250.0, "mg/dL", "HH", datetime(2024, 3, 15), 70.0, 99.0),
    _obs("00000000-0000-4000-8000-000000000003", "potassium", 6.1, "mmol/L (Patient: Jane Doe)", "H", datetime(2024, 3, 15), 3.5, 5.1),
    _obs("00000000-0000-4000-8000-000000000004", "hemoglobin", 9.1, "g/dL", "L DOB: 01/02/1980", datetime(2024, 3, 15), 12.0, 16.0),
    _obs("00000000-0000-4000-8000-000000000005", "sodium", 150.0, "mmol/L MRN: A12345", "H", datetime(2024, 3, 15), 135.0, 145.0),
)


class _Scalars:
    def __init__(self, rows: tuple) -> None:
        self._rows = rows

    def all(self) -> list:
        return list(self._rows)


class _Result:
    def __init__(self, rows: tuple) -> None:
        self._rows = rows

    def scalars(self) -> _Scalars:
        return _Scalars(self._rows)


class _FakeProfileDb:
    """Returns the fixture rows for any query (pattern: test_observations_audit.py)."""

    def __init__(self, rows: tuple) -> None:
        self._rows = rows

    async def execute(self, _stmt: object) -> _Result:
        return _Result(self._rows)


@pytest.fixture(autouse=True)
def _fresh_summary_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(export_api, "_summary_store", {})


def _override_profile_db_for(rows: tuple):
    """Dependency override returning a fake vault holding `rows`."""
    fake_db = _FakeProfileDb(rows)

    async def _override_profile_db() -> _FakeProfileDb:
        return fake_db

    return _override_profile_db


@contextmanager
def _export_client(
    profile_id: str = PROFILE_A,
    rows: tuple = PHI_ROWS,
    master_db: object | None = None,
) -> Iterator[TestClient]:
    """route_client for /export over a fixture vault.

    master_db=None: route_client's AsyncMock master DB, with the audit helper
    stubbed. HC-EXPR-003 passes a real AsyncSession so audit rows persist.
    """
    with ExitStack() as stack:
        if master_db is None:
            stack.enter_context(
                patch.object(export_api, "log_export_event", AsyncMock(return_value=object()))
            )
        client = stack.enter_context(
            route_client(export_api.router, "/export", profile_id=profile_id, master_db=master_db)
        )
        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db_for(rows)
        yield client


def _export_bytes(path: str) -> bytes:
    """GET /export/{path} over HTTP with the PHI fixture; return the body."""
    with _export_client() as client:
        response = client.get(f"/export/{path}")
    assert response.status_code == 200, response.text
    return response.content


# Captured on the W-2 start tree BEFORE any product change (Task 1 Step 3).
# Escaped bytes literals, not golden files: `.gitattributes` has
# `* text=auto`, which would rewrite the CSV's \r\n endings in a file.
BASELINE_CSV = (
    b'Date,Analyte,Value,Unit,Reference Low,Reference High,Flag,Verified\r\n'
    b'2024-01-10,glucose,100.0,mg/dL,70.0,99.0,,No\r\n'
    b'2024-03-15,glucose,250.0,mg/dL,70.0,99.0,HH,No\r\n'
    b'2024-03-15,hemoglobin,9.1,g/dL,12.0,16.0,L DOB: 01/02/1980,No\r\n'
    b'2024-03-15,potassium,6.1,mmol/L (Patient: Jane Doe),3.5,5.1,H,No\r\n'
    b'2024-03-15,sodium,150.0,mmol/L MRN: A12345,135.0,145.0,H,No\r\n'
)
BASELINE_JSON = (
    b'[\n'
    b'  {\n'
    b'    "id": "00000000-0000-4000-8000-000000000001",\n'
    b'    "analyte_canonical": "glucose",\n'
    b'    "analyte_raw": "glucose",\n'
    b'    "value": 100.0,\n'
    b'    "value_text": null,\n'
    b'    "unit": "mg/dL",\n'
    b'    "ref_low": 70.0,\n'
    b'    "ref_high": 99.0,\n'
    b'    "ref_range_text": null,\n'
    b'    "flag": null,\n'
    b'    "is_abnormal": false,\n'
    b'    "user_verified": false,\n'
    b'    "collected_at": "2024-01-10T00:00:00"\n'
    b'  },\n'
    b'  {\n'
    b'    "id": "00000000-0000-4000-8000-000000000002",\n'
    b'    "analyte_canonical": "glucose",\n'
    b'    "analyte_raw": "glucose",\n'
    b'    "value": 250.0,\n'
    b'    "value_text": null,\n'
    b'    "unit": "mg/dL",\n'
    b'    "ref_low": 70.0,\n'
    b'    "ref_high": 99.0,\n'
    b'    "ref_range_text": null,\n'
    b'    "flag": "HH",\n'
    b'    "is_abnormal": true,\n'
    b'    "user_verified": false,\n'
    b'    "collected_at": "2024-03-15T00:00:00"\n'
    b'  },\n'
    b'  {\n'
    b'    "id": "00000000-0000-4000-8000-000000000003",\n'
    b'    "analyte_canonical": "potassium",\n'
    b'    "analyte_raw": "potassium",\n'
    b'    "value": 6.1,\n'
    b'    "value_text": null,\n'
    b'    "unit": "mmol/L (Patient: Jane Doe)",\n'
    b'    "ref_low": 3.5,\n'
    b'    "ref_high": 5.1,\n'
    b'    "ref_range_text": null,\n'
    b'    "flag": "H",\n'
    b'    "is_abnormal": true,\n'
    b'    "user_verified": false,\n'
    b'    "collected_at": "2024-03-15T00:00:00"\n'
    b'  },\n'
    b'  {\n'
    b'    "id": "00000000-0000-4000-8000-000000000004",\n'
    b'    "analyte_canonical": "hemoglobin",\n'
    b'    "analyte_raw": "hemoglobin",\n'
    b'    "value": 9.1,\n'
    b'    "value_text": null,\n'
    b'    "unit": "g/dL",\n'
    b'    "ref_low": 12.0,\n'
    b'    "ref_high": 16.0,\n'
    b'    "ref_range_text": null,\n'
    b'    "flag": "L DOB: 01/02/1980",\n'
    b'    "is_abnormal": true,\n'
    b'    "user_verified": false,\n'
    b'    "collected_at": "2024-03-15T00:00:00"\n'
    b'  },\n'
    b'  {\n'
    b'    "id": "00000000-0000-4000-8000-000000000005",\n'
    b'    "analyte_canonical": "sodium",\n'
    b'    "analyte_raw": "sodium",\n'
    b'    "value": 150.0,\n'
    b'    "value_text": null,\n'
    b'    "unit": "mmol/L MRN: A12345",\n'
    b'    "ref_low": 135.0,\n'
    b'    "ref_high": 145.0,\n'
    b'    "ref_range_text": null,\n'
    b'    "flag": "H",\n'
    b'    "is_abnormal": true,\n'
    b'    "user_verified": false,\n'
    b'    "collected_at": "2024-03-15T00:00:00"\n'
    b'  }\n'
    b']'
)


@pytest.mark.parametrize(
    ("path", "baseline"),
    [("csv", BASELINE_CSV), ("json", BASELINE_JSON)],
    ids=["csv", "json"],
)
def test_hc_expr_002_csv_json_unchanged_byte_for_byte(path: str, baseline: bytes) -> None:
    """HC-EXPR-002: CSV/JSON are the patient's own full-fidelity export (D3)."""
    body = _export_bytes(path)
    assert body == baseline
    # Not vacuous: the exception is real, the seeded identifiers are still there.
    for phi in PHI_STRINGS:
        assert phi.encode() in body


from sqlalchemy import create_engine, event, insert, select  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from core import denial_audit  # noqa: E402
from core.database import Base  # noqa: E402
from models.audit import AuditLog  # noqa: E402
from models.profile import Profile  # noqa: E402

# Underscore-joined identifiers: the storage shape of unknown analytes
# (modules/normalize.py fallback). Strict redaction does not match it (O-3).
GAP_ROWS = (
    _obs("00000000-0000-4000-8000-000000000011", "patient_name:_jane_doe", 1.0, "", "H", datetime(2024, 3, 15), 0.0, 0.5),
    _obs("00000000-0000-4000-8000-000000000012", "dob:_01/02/1980", 1.0, "", "H", datetime(2024, 3, 15), 0.0, 0.5),
    _obs("00000000-0000-4000-8000-000000000013", "mrn:_a12345", 1.0, "", "H", datetime(2024, 3, 15), 0.0, 0.5),
)


def _install_capturing_weasyprint(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stand-in WeasyPrint: the 'PDF' is exactly the HTML handed to the PDF
    writer. render_pdf_summary builds the PDF only from that HTML, so PHI absent
    here is PHI absent from the PDF. Runs in every environment."""
    fake = types.ModuleType("weasyprint")

    class HTML:
        def __init__(self, string: str) -> None:
            self._html = string

        def write_pdf(self) -> bytes:
            return self._html.encode("utf-8")

    fake.HTML = HTML
    monkeypatch.setitem(sys.modules, "weasyprint", fake)


def _download_summary(client: TestClient, fmt: str) -> tuple[str, bytes]:
    created = client.post(
        "/export/doctor-summary", json={"format": fmt, "include_questions": True}
    )
    assert created.status_code == 200, created.text
    summary_id = created.json()["summary_id"]
    response = client.get(
        f"/export/doctor-summary/{summary_id}/download", params={"format": fmt}
    )
    assert response.status_code == 200, response.text
    return summary_id, response.content


@pytest.mark.parametrize("fmt", ["text", "html", "pdf"])
def test_hc_expr_001_doctor_summary_has_no_phi(
    fmt: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """HC-EXPR-001: labelled name, DOB and MRN are absent from every format."""
    if fmt == "pdf":
        _install_capturing_weasyprint(monkeypatch)
    with _export_client() as client:
        _summary_id, raw = _download_summary(client, fmt)
    body = raw.decode("utf-8")
    for phi in PHI_STRINGS:
        assert phi not in body
    # Not vacuous: redaction ran, and the clinical content survived it.
    for token in ("[NAME-REDACTED]", "[DOB-REDACTED]", "[MRN-REDACTED]"):
        assert token in body
    for clinical in ("glucose", "250.0", "potassium", "6.1", "hemoglobin", "sodium", "mg/dL"):
        assert clinical in body


@pytest.fixture
def weasyprint_renders() -> None:
    """Probe a real render BEFORE the request. Importing WeasyPrint is not
    enough: a missing Pango raises OSError from write_pdf(), which would
    otherwise surface as an error (the route turns it into HTTP 500).
    HC_REQUIRE_WEASYPRINT=1 turns the skip into a failure, so an environment
    that is supposed to render PDFs cannot skip silently."""
    try:
        from weasyprint import HTML

        HTML(string="<p>x</p>").write_pdf()
    except (ImportError, OSError) as exc:
        reason = f"WeasyPrint cannot render here ({type(exc).__name__}: {exc})"
        if os.environ.get("HC_REQUIRE_WEASYPRINT") == "1":
            pytest.fail(f"HC_REQUIRE_WEASYPRINT=1 but {reason}")
        pytest.skip(f"{reason}; the fake-writer pdf case still ran")


def test_hc_expr_001_real_pdf_extracted_text_has_no_phi(weasyprint_renders: None) -> None:
    """HC-EXPR-001 (real PDF): runs only where WeasyPrint renders (see fixture)."""
    from pypdf import PdfReader

    with _export_client() as client:
        _summary_id, raw = _download_summary(client, "pdf")
    text = "".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(raw)).pages)
    assert "glucose" in text  # extraction works; otherwise absence proves nothing
    for phi in PHI_STRINGS:
        assert phi not in text


@pytest.mark.xfail(
    strict=True,
    reason=(
        "O-3 known gap: strict RedactionEngine does not match underscore-joined "
        "identifiers (unknown-analyte storage shape). Owner sign-off S-3. "
        "XPASS means redaction changed: update S-3 and remove this marker."
    ),
)
def test_hc_expr_001_known_gap_underscore_phi() -> None:
    """HC-EXPR-001 (known gap, visible not hidden): expected to fail today."""
    with _export_client(rows=GAP_ROWS) as client:
        _summary_id, raw = _download_summary(client, "text")
    body = raw.decode("utf-8").lower()
    for phi in ("jane", "01/02/1980", "a12345"):
        assert phi not in body


@pytest.fixture(autouse=True)
def _fresh_denial_state() -> None:
    """denial_audit._state is a module-level per-caller cap; earlier tests in a
    full run can exhaust PROFILE_B's, turning the denial row into a suppression
    (pattern: tests/test_denial_audit.py)."""
    denial_audit._state.clear()


@pytest.fixture
def master_audit_db(tmp_path, monkeypatch) -> Iterator[tuple[AsyncSession, Engine]]:
    """A real master DB file with `profiles` + `audit_logs`, FKs enforced, so
    HC-EXPR-003 asserts persisted rows. NullPool: every connection is opened
    inside the TestClient's own event loop."""
    db_path = tmp_path / "master_audit.db"
    sync_engine = create_engine(f"sqlite:///{db_path}")
    async_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", poolclass=NullPool)

    def _fk_on(dbapi_conn, _record) -> None:
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    event.listen(sync_engine, "connect", _fk_on)
    event.listen(async_engine.sync_engine, "connect", _fk_on)
    Base.metadata.create_all(sync_engine, tables=[Profile.__table__, AuditLog.__table__])
    now = datetime(2026, 9, 27)
    with sync_engine.begin() as conn:
        conn.execute(
            insert(Profile.__table__),
            [
                {"id": pid, "display_name": "T", "encryption_key_id": "k",
                 "is_locked": False, "created_at": now, "updated_at": now}
                for pid in (PROFILE_A, PROFILE_B)
            ],
        )
    session = AsyncSession(async_engine, expire_on_commit=False)
    # I-12: any denial write that opens its own session lands in the test master DB.
    monkeypatch.setattr(
        "core.database.async_session_maker",
        async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False),
    )
    try:
        yield session, sync_engine
    finally:
        sync_engine.dispose()


def _audit_rows(sync_engine: Engine) -> list[dict]:
    with sync_engine.connect() as conn:
        return [dict(r) for r in conn.execute(select(AuditLog.__table__)).mappings()]


def test_hc_expr_003_doctor_summary_route_over_http(master_audit_db) -> None:
    """HC-EXPR-003: the preview and the store are redacted; generate and
    download each persist a real audit row without PHI; another profile gets
    403 and writes exactly one denial.cross_profile row; an unknown id gets 404."""
    session, sync_engine = master_audit_db
    with route_client(
        export_api.router, "/export", profile_id=PROFILE_A, master_db=session
    ) as client:
        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db_for(PHI_ROWS)
        created = client.post(
            "/export/doctor-summary", json={"format": "text", "include_questions": True}
        )
        assert created.status_code == 200, created.text
        payload = created.json()
        summary_id = payload["summary_id"]
        preview = json.dumps(payload["key_findings"])  # what ExportPage shows and copies
        for phi in PHI_STRINGS:
            assert phi not in preview
        stored = export_api._summary_store[summary_id]
        stored_text = json.dumps(stored, default=str)  # incl. unrendered question context
        for phi in PHI_STRINGS:
            assert phi not in stored_text
        assert stored["redaction_count"] >= 3

        download = client.get(
            f"/export/doctor-summary/{summary_id}/download", params={"format": "text"}
        )
        assert download.status_code == 200
        unknown = client.get(
            "/export/doctor-summary/00000000-0000-4000-8000-00000000ffff/download"
        )
        assert unknown.status_code == 404

    rows = [r for r in _audit_rows(sync_engine) if r["event_type"] == "export.create"]
    assert len(rows) == 2
    assert all(r["profile_id"] == PROFILE_A for r in rows)
    details = [json.loads(r["details_json"]) for r in rows]
    assert sorted(d["export_type"] for d in details) == ["doctor_summary", "summary_download"]
    assert all(d["summary_id"] == summary_id for d in details)
    generate = next(d for d in details if d["export_type"] == "doctor_summary")
    assert generate["redaction_count"] == stored["redaction_count"]
    audit_text = json.dumps(rows, default=str)
    for phi in PHI_STRINGS:
        assert phi not in audit_text

    with route_client(
        export_api.router, "/export", profile_id=PROFILE_B, master_db=session
    ) as other:
        other.app.dependency_overrides[get_profile_db_session] = _override_profile_db_for(PHI_ROWS)
        refused = other.get(f"/export/doctor-summary/{summary_id}/download")
    assert refused.status_code == 403
    all_rows = _audit_rows(sync_engine)
    assert len([r for r in all_rows if r["event_type"] == "export.create"]) == 2
    denials = [r for r in all_rows if r["event_type"] == "denial.cross_profile"]
    assert len(denials) == 1
    denial = denials[0]
    assert denial["profile_id"] == PROFILE_B
    assert denial["entity_type"] == "summary"
    assert denial["entity_id"] is None
    assert summary_id not in json.dumps(denial, default=str)
