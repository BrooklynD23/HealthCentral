"""HC-M18 visit-prep packet tests (HC-PKT-NNN).

One exportable packet before an appointment: reason for visit, current
medications, recent abnormal verified labs, recent visit/diagnosis mentions,
open follow-up tasks with source quotes, generated questions (HC-M17), and
the selected source documents.

Hard invariants under test:
- confirm: true is REQUIRED (400 without it) — mirrors the RL-export flow.
- The assembled packet passes through modules/redaction.py (strict) before
  it can be downloaded; seeded PII (phone, MRN) never survives.
- Unverified-data policy: unverified observations and unverified entities
  are EXCLUDED from the packet (verified-only, everywhere).
- Audit rows on generate and download.
"""

from __future__ import annotations

import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.auth import Session
from core.time import utcnow
from modules.export import ExportModule


def _make_session(profile_id: str = "test-profile") -> Session:
    return Session(
        profile_id=profile_id,
        profile_name="Test Profile",
        expires_at=utcnow() + timedelta(hours=1),
    )


@pytest.fixture
def export_module():
    return ExportModule()


def _obs(**overrides) -> dict:
    fields = dict(
        id=str(uuid.uuid4()),
        analyte_canonical="hemoglobin_a1c",
        value=7.2,
        unit="%",
        ref_low=4.0,
        ref_high=5.6,
        flag="H",
        is_abnormal=True,
        user_verified=True,
        collected_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    fields.update(overrides)
    return fields


def _med(**overrides) -> dict:
    fields = dict(
        id=str(uuid.uuid4()),
        name="Lisinopril",
        dosage_amount=10.0,
        dosage_unit="mg",
        frequency="once_daily",
        instructions=None,
    )
    fields.update(overrides)
    return fields


def _mention(**overrides) -> dict:
    fields = dict(
        id=str(uuid.uuid4()),
        entity_type="diagnoses",
        entity_value="Type 2 diabetes",
        doc_date="2026-05-20",
        verified_by_user=True,
    )
    fields.update(overrides)
    return fields


def _task(**overrides) -> dict:
    fields = dict(
        id=str(uuid.uuid4()),
        title="Repeat CBC",
        status="open",
        due_date=date(2026, 7, 20),
        source_quote="Repeat CBC in 4 weeks",
        source_entity_id=None,
    )
    fields.update(overrides)
    return fields


def _doc(**overrides) -> dict:
    fields = dict(
        id=str(uuid.uuid4()),
        source="visit-note-2026-05.pdf",
        collection_date=datetime(2026, 5, 20, tzinfo=timezone.utc),
    )
    fields.update(overrides)
    return fields


class TestPacketAssembly:
    def test_hc_pkt_001_all_sections_assembled(self, export_module):
        packet = export_module.compose_visit_prep_packet(
            profile_id="test-profile",
            reason_for_visit="Persistent headaches for two weeks",
            medications=[_med()],
            observations=[_obs()],
            visit_mentions=[_mention()],
            care_tasks=[_task()],
            questions=export_module.generate_questions(
                observations=[_obs()], trends=[], today=date(2026, 7, 12)
            ),
            selected_documents=[_doc()],
        )

        titles = [s["title"] for s in packet["sections"]]
        assert "Reason for Visit" in titles
        assert "Current Medications" in titles
        assert "Recent Abnormal Lab Results (verified)" in titles
        assert "Recent Visits and Diagnoses (verified)" in titles
        assert "Open Follow-up Items" in titles
        assert "Questions for Your Provider" in titles
        assert "Source Documents" in titles

        md = packet["markdown"]
        assert md.startswith("# Visit Prep Packet")
        assert "Persistent headaches for two weeks" in md
        assert "Lisinopril" in md
        assert "hemoglobin_a1c" in md
        assert "Type 2 diabetes" in md
        assert "Repeat CBC" in md
        assert "visit-note-2026-05.pdf" in md
        # Not-medical-advice footer.
        assert "not medical advice" in md.lower()
        assert packet["packet_id"]
        assert packet["profile_id"] == "test-profile"

    def test_hc_pkt_002_omitted_sections_are_absent(self, export_module):
        """None means the user excluded the section; it must not render."""
        packet = export_module.compose_visit_prep_packet(
            profile_id="test-profile",
            reason_for_visit=None,
            medications=None,
            observations=[_obs()],
            visit_mentions=None,
            care_tasks=None,
            questions=None,
            selected_documents=None,
        )
        titles = [s["title"] for s in packet["sections"]]
        assert titles == ["Recent Abnormal Lab Results (verified)"]
        assert "Current Medications" not in packet["markdown"]

    def test_hc_pkt_003_included_but_empty_section_says_none_recorded(self, export_module):
        packet = export_module.compose_visit_prep_packet(
            profile_id="test-profile",
            medications=[],
            observations=None,
        )
        med_section = next(
            s for s in packet["sections"] if s["title"] == "Current Medications"
        )
        assert "none recorded" in med_section["content"].lower()

    def test_hc_pkt_004_dates_render_iso(self, export_module):
        """ISO-8601 dates carry the clinical signal and survive strict
        redaction (the numeric_date rule matches d/m/y shapes only)."""
        packet = export_module.compose_visit_prep_packet(
            profile_id="test-profile",
            observations=[_obs(collected_at=datetime(2026, 6, 1, tzinfo=timezone.utc))],
        )
        assert "2026-06-01" in packet["markdown"]
        assert "[DATE-REDACTED]" not in packet["markdown"]


class TestUnverifiedDataPolicy:
    """Chosen policy: unverified data is EXCLUDED from the packet."""

    def test_hc_pkt_005_unverified_observations_excluded(self, export_module):
        packet = export_module.compose_visit_prep_packet(
            profile_id="test-profile",
            observations=[
                _obs(analyte_canonical="hemoglobin_a1c", user_verified=True),
                _obs(analyte_canonical="cholesterol_total", user_verified=False),
                _obs(analyte_canonical="glucose", user_verified=True, is_abnormal=False),
            ],
        )
        md = packet["markdown"]
        assert "hemoglobin_a1c" in md
        # Unverified: excluded outright.
        assert "cholesterol_total" not in md
        # Normal (non-abnormal) values are not part of the labs section.
        assert "glucose" not in md

    def test_hc_pkt_006_unverified_visit_mentions_excluded(self, export_module):
        packet = export_module.compose_visit_prep_packet(
            profile_id="test-profile",
            visit_mentions=[
                _mention(entity_value="Type 2 diabetes", verified_by_user=True),
                _mention(entity_value="Hypertension", verified_by_user=None),
                _mention(entity_value="Asthma", verified_by_user=False),
            ],
        )
        md = packet["markdown"]
        assert "Type 2 diabetes" in md
        assert "Hypertension" not in md
        assert "Asthma" not in md

    def test_hc_pkt_007_policy_stated_in_packet(self, export_module):
        """The packet itself says only verified data is included, so the
        clinician knows what they are looking at."""
        packet = export_module.compose_visit_prep_packet(
            profile_id="test-profile",
            observations=[_obs()],
        )
        assert "verified" in packet["markdown"].lower()


class TestPacketRedaction:
    def test_hc_pkt_008_seeded_pii_is_redacted(self, export_module):
        """A phone number and an MRN seeded into free-text fields must be
        redacted in every packet output."""
        packet = export_module.compose_visit_prep_packet(
            profile_id="test-profile",
            reason_for_visit="Nurse said call 555-123-4567 about MRN: A12345",
            care_tasks=[
                _task(source_quote="Call clinic at 555-123-4567 to book, MRN: A12345")
            ],
        )
        md = packet["markdown"]
        assert "555-123-4567" not in md
        assert "A12345" not in md
        assert "[PHONE-REDACTED]" in md
        assert "[MRN-REDACTED]" in md
        # Section contents (used by the html/pdf renderer) are redacted too.
        for section in packet["sections"]:
            assert "555-123-4567" not in section["content"]
            assert "A12345" not in section["content"]
        assert packet["redaction_count"] >= 2


# ---------------------------------------------------------------------------
# Route level: POST /export/visit-prep + download flow
# ---------------------------------------------------------------------------

from api.export import (  # noqa: E402
    VisitPrepRequest,
    _packet_store,
    download_visit_prep,
    generate_visit_prep,
)


def _patch_fetchers(monkeypatch, observations=None, meds=None, mentions=None,
                    tasks=None, entities=None, docs=None):
    monkeypatch.setattr(
        "api.export._fetch_observations", AsyncMock(return_value=observations or [])
    )
    monkeypatch.setattr(
        "api.export._fetch_active_medication_dicts", AsyncMock(return_value=meds or [])
    )
    monkeypatch.setattr(
        "api.export._fetch_visit_mention_dicts", AsyncMock(return_value=mentions or [])
    )
    monkeypatch.setattr(
        "api.export._fetch_care_task_dicts", AsyncMock(return_value=tasks or [])
    )
    monkeypatch.setattr(
        "api.export._fetch_question_entity_dicts", AsyncMock(return_value=entities or [])
    )
    monkeypatch.setattr(
        "api.export._fetch_selected_document_dicts", AsyncMock(return_value=docs or [])
    )


class TestVisitPrepRoute:
    @pytest.mark.asyncio
    async def test_hc_pkt_009_confirm_required_400(self):
        from fastapi import HTTPException

        request = VisitPrepRequest(confirm=False)
        with pytest.raises(HTTPException) as exc_info:
            await generate_visit_prep(
                request, _make_session(), AsyncMock(), AsyncMock()
            )
        assert exc_info.value.status_code == 400

        # Default (field omitted) is also rejected.
        with pytest.raises(HTTPException) as exc_info:
            await generate_visit_prep(
                VisitPrepRequest(), _make_session(), AsyncMock(), AsyncMock()
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_hc_pkt_010_generate_returns_packet_and_audits(self, monkeypatch):
        _patch_fetchers(
            monkeypatch,
            observations=[_obs()],
            meds=[_med()],
            mentions=[_mention()],
            tasks=[_task()],
            docs=[_doc()],
        )
        audit_mock = AsyncMock()
        monkeypatch.setattr("api.export.log_export_event", audit_mock)

        request = VisitPrepRequest(
            reason_for_visit="Annual check-in",
            selected_doc_ids=[str(uuid.uuid4())],
            confirm=True,
        )
        response = await generate_visit_prep(
            request, _make_session(), AsyncMock(), AsyncMock()
        )

        assert response.packet_id
        assert "Annual check-in" in response.markdown
        assert "Lisinopril" in response.markdown
        assert "Current Medications" in response.section_titles
        assert response.packet_id in _packet_store

        audit_mock.assert_awaited_once()
        assert audit_mock.await_args.kwargs["export_type"] == "visit_prep"
        assert audit_mock.await_args.kwargs["profile_id"] == "test-profile"

    @pytest.mark.asyncio
    async def test_hc_pkt_011_include_flags_omit_sections(self, monkeypatch):
        _patch_fetchers(monkeypatch, observations=[_obs()], meds=[_med()])
        monkeypatch.setattr("api.export.log_export_event", AsyncMock())

        request = VisitPrepRequest(
            include_medications=False,
            include_visits=False,
            include_tasks=False,
            include_questions=False,
            confirm=True,
        )
        response = await generate_visit_prep(
            request, _make_session(), AsyncMock(), AsyncMock()
        )
        assert "Current Medications" not in response.section_titles
        assert "Recent Abnormal Lab Results (verified)" in response.section_titles

    @pytest.mark.asyncio
    async def test_hc_pkt_012_download_markdown_flow(self, monkeypatch):
        _patch_fetchers(monkeypatch, observations=[_obs()])
        audit_mock = AsyncMock()
        monkeypatch.setattr("api.export.log_export_event", audit_mock)

        response = await generate_visit_prep(
            VisitPrepRequest(confirm=True), _make_session(), AsyncMock(), AsyncMock()
        )

        download = await download_visit_prep(
            packet_id=response.packet_id,
            session=_make_session(),
            format="markdown",
            master_db=AsyncMock(),
        )
        assert download.media_type == "text/markdown"
        body = bytes(download.body).decode("utf-8")
        assert body.startswith("# Visit Prep Packet")
        assert "attachment" in download.headers["Content-Disposition"]

        # Download is audited too.
        download_calls = [
            c for c in audit_mock.await_args_list
            if c.kwargs.get("export_type") == "visit_prep_download"
        ]
        assert len(download_calls) == 1

    @pytest.mark.asyncio
    async def test_hc_pkt_013_download_html_reuses_summary_renderer(self, monkeypatch):
        _patch_fetchers(monkeypatch, observations=[_obs()])
        monkeypatch.setattr("api.export.log_export_event", AsyncMock())

        response = await generate_visit_prep(
            VisitPrepRequest(confirm=True), _make_session(), AsyncMock(), AsyncMock()
        )
        download = await download_visit_prep(
            packet_id=response.packet_id,
            session=_make_session(),
            format="html",
            master_db=AsyncMock(),
        )
        assert download.media_type == "text/html"
        html = bytes(download.body).decode("utf-8")
        assert "hemoglobin_a1c" in html

    @pytest.mark.asyncio
    async def test_hc_pkt_014_download_denied_for_other_profile(self, monkeypatch):
        from fastapi import HTTPException

        _patch_fetchers(monkeypatch, observations=[_obs()])
        monkeypatch.setattr("api.export.log_export_event", AsyncMock())

        response = await generate_visit_prep(
            VisitPrepRequest(confirm=True), _make_session(), AsyncMock(), AsyncMock()
        )
        with pytest.raises(HTTPException) as exc_info:
            await download_visit_prep(
                packet_id=response.packet_id,
                session=_make_session("another-profile"),
                format="markdown",
                master_db=AsyncMock(),
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_hc_pkt_015_download_404_for_unknown_packet(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await download_visit_prep(
                packet_id=str(uuid.uuid4()),
                session=_make_session(),
                format="markdown",
                master_db=AsyncMock(),
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_hc_pkt_016_route_output_redacts_seeded_pii(self, monkeypatch):
        """End-to-end through the route: PII in a task quote never reaches
        the downloadable artifact."""
        _patch_fetchers(
            monkeypatch,
            tasks=[_task(source_quote="Call 555-123-4567, MRN: A12345")],
        )
        monkeypatch.setattr("api.export.log_export_event", AsyncMock())

        response = await generate_visit_prep(
            VisitPrepRequest(confirm=True), _make_session(), AsyncMock(), AsyncMock()
        )
        download = await download_visit_prep(
            packet_id=response.packet_id,
            session=_make_session(),
            format="markdown",
            master_db=AsyncMock(),
        )
        body = bytes(download.body).decode("utf-8")
        assert "555-123-4567" not in body
        assert "A12345" not in body
        assert "[PHONE-REDACTED]" in body


# ---------------------------------------------------------------------------
# Excluded-section leakage into the Questions section (review fix)
# ---------------------------------------------------------------------------


class TestQuestionsSectionExclusion:
    """Content the user excluded from the packet (include_tasks=False /
    include_labs=False) must not resurface as a question source — the
    Questions section may only draw on sections the user chose to include."""

    @pytest.mark.asyncio
    async def test_hc_pkt_017_excluded_tasks_do_not_leak_into_questions(
        self, monkeypatch
    ):
        _patch_fetchers(
            monkeypatch,
            tasks=[
                _task(
                    status="needs_review",
                    source_quote="Repeat CBC in 4 weeks",
                )
            ],
        )
        monkeypatch.setattr("api.export.log_export_event", AsyncMock())

        request = VisitPrepRequest(
            include_tasks=False,
            include_questions=True,
            confirm=True,
        )
        response = await generate_visit_prep(
            request, _make_session(), AsyncMock(), AsyncMock()
        )
        assert "Questions for Your Provider" in response.section_titles
        assert "Repeat CBC" not in response.markdown
        assert "clarify" not in response.markdown.lower()

    @pytest.mark.asyncio
    async def test_hc_pkt_018_excluded_labs_do_not_leak_into_questions(
        self, monkeypatch
    ):
        _patch_fetchers(
            monkeypatch,
            observations=[_obs(analyte_canonical="hemoglobin_a1c")],
        )
        monkeypatch.setattr("api.export.log_export_event", AsyncMock())

        request = VisitPrepRequest(
            include_labs=False,
            include_questions=True,
            confirm=True,
        )
        response = await generate_visit_prep(
            request, _make_session(), AsyncMock(), AsyncMock()
        )
        assert "Questions for Your Provider" in response.section_titles
        assert "Recent Abnormal Lab Results" not in response.markdown
        assert "hemoglobin_a1c" not in response.markdown


# ---------------------------------------------------------------------------
# Real profile-DB fetchers: date filtering and verified-only policy
# ---------------------------------------------------------------------------

import pytest_asyncio  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402

from core.profile_database import ProfileDatabaseBase  # noqa: E402
from models import Document  # noqa: E402
from models.document_category import DocumentEntity  # noqa: E402
from api.export import (  # noqa: E402
    _fetch_question_entity_dicts,
    _fetch_visit_mention_dicts,
)


@pytest_asyncio.fixture
async def real_profile_db():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


def _document(doc_id: str, collection_date, profile_id: str = "test-profile") -> Document:
    return Document(
        id=doc_id,
        profile_id=profile_id,
        path_hash="x" * 64,
        content_hash="y" * 64,
        doc_type="visit_notes",
        source="visit-note.pdf",
        status="parsed",
        collection_date=collection_date,
        imported_at=datetime(2026, 4, 2, 12, 0, 0),
    )


def _document_entity(doc_id: str, entity_type: str, value: str, **overrides) -> DocumentEntity:
    fields = dict(
        id=str(uuid.uuid4()),
        doc_id=doc_id,
        category="visit_notes",
        entity_type=entity_type,
        entity_value=value,
        confidence=0.8,
        source_page=None,
        char_start=0,
        char_end=len(value),
        quote=value,
        verified_by_user=None,
        extraction_version="rule-v2",
    )
    fields.update(overrides)
    return DocumentEntity(**fields)


class TestRealFetchers:
    @pytest.mark.asyncio
    async def test_hc_pkt_019_visit_mentions_respect_date_range(self, real_profile_db):
        db = real_profile_db
        in_range_doc = str(uuid.uuid4())
        out_of_range_doc = str(uuid.uuid4())
        db.add(_document(in_range_doc, datetime(2026, 5, 20, tzinfo=timezone.utc)))
        db.add(_document(out_of_range_doc, datetime(2026, 1, 1, tzinfo=timezone.utc)))
        db.add(_document_entity(
            in_range_doc, "diagnoses", "Type 2 diabetes", verified_by_user=True,
        ))
        db.add(_document_entity(
            out_of_range_doc, "diagnoses", "Hypertension", verified_by_user=True,
        ))
        await db.commit()

        mentions = await _fetch_visit_mention_dicts(
            db,
            from_date=datetime(2026, 4, 1, tzinfo=timezone.utc),
            to_date=datetime(2026, 6, 1, tzinfo=timezone.utc),
        )
        values = {m["entity_value"] for m in mentions}
        assert values == {"Type 2 diabetes"}

        # Without a range, both are returned (unchanged existing behavior).
        all_mentions = await _fetch_visit_mention_dicts(db)
        assert {m["entity_value"] for m in all_mentions} == {
            "Type 2 diabetes", "Hypertension",
        }

    @pytest.mark.asyncio
    async def test_hc_pkt_020_question_entities_real_fetcher_excludes_unverified(
        self, real_profile_db
    ):
        db = real_profile_db
        doc_id = str(uuid.uuid4())
        db.add(_document(doc_id, datetime(2026, 5, 20, tzinfo=timezone.utc)))
        db.add(_document_entity(
            doc_id, "medication_change", "start metformin 500 mg",
            verified_by_user=True,
        ))
        db.add(_document_entity(
            doc_id, "test_ordered", "repeat CBC in 4 weeks",
            verified_by_user=False,
        ))
        db.add(_document_entity(
            doc_id, "referral", "see cardiology",
            verified_by_user=None,
        ))
        await db.commit()

        entities = await _fetch_question_entity_dicts(db)
        values = {e["entity_value"] for e in entities}
        assert values == {"start metformin 500 mg"}
