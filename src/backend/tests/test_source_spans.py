"""HC-M12 source-span extraction tests (HC-SPAN-NNN).

Every extracted document entity must carry a verbatim source span
(char_start/char_end/quote with text[char_start:char_end] == quote),
an extraction_version, and support user verification state.
"""

from __future__ import annotations

import sys
import uuid
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.auth import Session
from core.time import utcnow
from modules.extract_imaging import extract_imaging_entities
from modules.extract_pathology import extract_pathology_entities
from modules.extract_spans import EXTRACTION_VERSION, with_span
from modules.extract_visit_notes import extract_visit_note_entities
from models.document_category import DocumentEntity


IMAGING_TEXT = (
    "RADIOLOGY REPORT\n"
    "Exam Date: 03/12/2026\n"
    "MRI of the left knee without contrast\n"
    "FINDINGS: Complex tear of the medial meniscus.\n"
    "IMPRESSION: Medial meniscal tear, no fracture.\n"
)

PATHOLOGY_TEXT = (
    "SURGICAL PATHOLOGY REPORT\n"
    "Specimen: skin, left forearm, biopsy\n"
    "FINAL DIAGNOSIS: Compound nevus, no atypia.\n"
    "MARGINS: Negative\n"
    "Pathologist: Dr. Smith\n"
)

VISIT_NOTE_TEXT = (
    "PROGRESS NOTE\n"
    "Date of visit: 04/02/2026\n"
    "Chief Complaint: intermittent headaches\n"
    "VITALS: BP 118/76, HR 64\n"
    "ASSESSMENT: Tension-type headache, stable.\n"
    "PLAN: Hydration, sleep hygiene, follow-up in 3 months.\n"
    "Signed by: Dr. Jones\n"
)


def _assert_span_integrity(entities: list[dict], text: str) -> None:
    assert entities, "extractor should find entities in fixture text"
    for ent in entities:
        assert ent["extraction_version"] == EXTRACTION_VERSION
        assert "quote" in ent and "char_start" in ent and "char_end" in ent
        if ent["quote"] is None:
            assert ent["char_start"] is None
            assert ent["char_end"] is None
            assert ent["confidence"] <= 0.5
        else:
            assert isinstance(ent["char_start"], int)
            assert isinstance(ent["char_end"], int)
            assert text[ent["char_start"]:ent["char_end"]] == ent["quote"]


class TestExtractorSpans:
    def test_hc_span_001_imaging_quotes_are_exact_substrings(self):
        entities = extract_imaging_entities(IMAGING_TEXT)
        _assert_span_integrity(entities, IMAGING_TEXT)
        # All fixture entities are regex hits, so spans must resolve.
        assert all(e["quote"] is not None for e in entities)
        by_type = {e["entity_type"]: e for e in entities}
        assert by_type["modality"]["quote"] == "MRI"
        assert "medial meniscus" in by_type["finding"]["quote"]

    def test_hc_span_002_pathology_quotes_are_exact_substrings(self):
        entities = extract_pathology_entities(PATHOLOGY_TEXT)
        _assert_span_integrity(entities, PATHOLOGY_TEXT)
        assert all(e["quote"] is not None for e in entities)
        by_type = {e["entity_type"]: e for e in entities}
        assert "Compound nevus" in by_type["diagnosis"]["quote"]

    def test_hc_span_003_visit_note_quotes_are_exact_substrings(self):
        entities = extract_visit_note_entities(VISIT_NOTE_TEXT)
        _assert_span_integrity(entities, VISIT_NOTE_TEXT)
        assert all(e["quote"] is not None for e in entities)
        by_type = {e["entity_type"]: e for e in entities}
        assert "intermittent headaches" in by_type["chief_complaint"]["quote"]

    def test_hc_span_004_unresolvable_span_caps_confidence(self):
        entity = {
            "entity_type": "finding",
            "entity_value": "something",
            "confidence": 0.9,
            "source_page": None,
        }
        result = with_span(entity, "irrelevant text", None)
        assert result["quote"] is None
        assert result["char_start"] is None
        assert result["char_end"] is None
        assert result["confidence"] <= 0.5
        assert result["extraction_version"] == EXTRACTION_VERSION

        # Already-low confidence is not raised by the cap.
        low = with_span({"confidence": 0.3}, "text", None)
        assert low["confidence"] == 0.3


# ---------------------------------------------------------------------------
# API round-trip and verification endpoint (mock-session style matches
# tests/test_document_category_api.py)
# ---------------------------------------------------------------------------

from api.documents import (  # noqa: E402
    DocumentEntityResponse,
    EntityVerificationRequest,
    get_document_entities,
    set_entity_verification,
)


class _ScalarResult:
    def __init__(self, one: object = None, all_items: list | None = None):
        self._one = one
        self._all_items = all_items or []

    def scalar_one_or_none(self):
        return self._one

    def scalars(self):
        return self

    def all(self):
        return self._all_items


def _make_session(profile_id: str = "test-profile") -> Session:
    return Session(
        profile_id=profile_id,
        profile_name="Test Profile",
        expires_at=utcnow() + timedelta(hours=1),
    )


def _make_document(doc_id: str, profile_id: str = "test-profile") -> MagicMock:
    doc = MagicMock()
    doc.id = doc_id
    doc.profile_id = profile_id
    doc.source = "report.pdf"
    return doc


def _make_entity(doc_id: str, **overrides) -> DocumentEntity:
    fields = dict(
        id=str(uuid.uuid4()),
        doc_id=doc_id,
        category="imaging",
        entity_type="modality",
        entity_value="MRI",
        confidence=0.95,
        source_page=None,
        char_start=17,
        char_end=20,
        quote="MRI",
        verified_by_user=None,
        extraction_version=EXTRACTION_VERSION,
    )
    fields.update(overrides)
    return DocumentEntity(**fields)


class TestEntitiesApiRoundTrip:
    @pytest.mark.asyncio
    async def test_hc_span_005_new_fields_round_trip_through_api(self):
        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id)
        ent = _make_entity(doc_id, verified_by_user=True)

        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _ScalarResult(one=doc)
            return _ScalarResult(all_items=[ent])

        mock_db = AsyncMock()
        mock_db.execute = mock_execute

        result = await get_document_entities(doc_id, _make_session(), mock_db, AsyncMock())
        assert len(result) == 1
        resp = result[0]
        assert isinstance(resp, DocumentEntityResponse)
        assert resp.quote == "MRI"
        assert resp.char_start == 17
        assert resp.char_end == 20
        assert resp.verified_by_user is True
        assert resp.extraction_version == EXTRACTION_VERSION


class TestEntityVerificationEndpoint:
    def _mock_dbs(self, doc, entity):
        call_count = 0

        async def mock_execute(stmt):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _ScalarResult(one=doc)
            return _ScalarResult(one=entity)

        profile_db = AsyncMock()
        profile_db.execute = mock_execute
        master_db = AsyncMock()
        return profile_db, master_db

    @pytest.mark.asyncio
    @pytest.mark.parametrize("verified", [True, False, None])
    async def test_hc_span_006_patch_sets_state_and_audits(self, verified, monkeypatch):
        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id)
        ent = _make_entity(doc_id, verified_by_user=None if verified is not None else True)
        profile_db, master_db = self._mock_dbs(doc, ent)

        audit_mock = AsyncMock()
        monkeypatch.setattr("api.documents.log_document_event", audit_mock)

        result = await set_entity_verification(
            doc_id,
            ent.id,
            EntityVerificationRequest(verified=verified),
            _make_session(),
            profile_db,
            master_db,
        )

        assert ent.verified_by_user is verified
        assert result.verified_by_user is verified
        profile_db.commit.assert_awaited()

        # Audit entry written and committed on the master DB.
        audit_mock.assert_awaited_once()
        audit_kwargs = audit_mock.await_args.kwargs
        assert audit_kwargs["profile_id"] == "test-profile"
        assert audit_kwargs["document_id"] == doc_id
        assert audit_kwargs["details"]["entity_id"] == ent.id
        assert audit_kwargs["details"]["verified"] is verified
        master_db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_hc_span_007_patch_404_when_entity_missing(self):
        from fastapi import HTTPException

        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id)
        profile_db, master_db = self._mock_dbs(doc, None)

        with pytest.raises(HTTPException) as exc_info:
            await set_entity_verification(
                doc_id,
                str(uuid.uuid4()),
                EntityVerificationRequest(verified=True),
                _make_session(),
                profile_db,
                master_db,
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_hc_span_008_patch_403_when_wrong_profile(self):
        from fastapi import HTTPException

        doc_id = str(uuid.uuid4())
        doc = _make_document(doc_id, profile_id="other-profile")
        profile_db, master_db = self._mock_dbs(doc, None)

        with pytest.raises(HTTPException) as exc_info:
            await set_entity_verification(
                doc_id,
                str(uuid.uuid4()),
                EntityVerificationRequest(verified=True),
                _make_session(),
                profile_db,
                master_db,
            )
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Migration 010 upgrade/downgrade
# ---------------------------------------------------------------------------


def test_hc_span_009_migration_010_upgrade_and_downgrade_run_clean(tmp_path, monkeypatch):
    from alembic import command

    from core import migrations
    from core.config import settings

    monkeypatch.setattr(settings, "database_encryption_required", False)

    vault_path = tmp_path / "vault.db"
    encryption_key = b"0" * 32

    migrations.run_profile_migration(vault_path, encryption_key)
    assert (
        migrations.get_profile_current_revision(vault_path, encryption_key)
        == "010_entity_source_spans"
    )

    config = migrations._get_alembic_config("profile")
    config.attributes["vault_path"] = vault_path
    config.attributes["encryption_key"] = encryption_key

    command.downgrade(config, "009_agent_enabled")
    assert (
        migrations.get_profile_current_revision(vault_path, encryption_key)
        == "009_agent_enabled"
    )

    command.upgrade(config, "head")
    assert (
        migrations.get_profile_current_revision(vault_path, encryption_key)
        == "010_entity_source_spans"
    )
