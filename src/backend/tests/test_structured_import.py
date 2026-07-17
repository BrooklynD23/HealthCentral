"""HC-M23 structured import tests (HC-FIMP-NNN).

Covers:
- Pure parsers (modules/import_structured.py): CSV header aliases,
  value_text fallback, skipped-row reasons, undated rows, FHIR
  Observation/MedicationStatement/Condition mapping, unknown-resource
  skip+count, malformed/non-Bundle JSON rejection, a round-trip against
  HC-M22's build_fhir_bundle, and untrusted-input hardening (length cap,
  injection-payload-as-analyte stays inert text).
- modules/ingest.py: detect_doc_type for .csv/.json, import_document
  rejecting non-Bundle/malformed JSON with a clear ValueError (surfaces
  as 400 at the route).
- api/documents.py POST /documents/import: csv/fhir uploads persist
  unverified observations/entities + a DocumentCategory row, audit
  details include source_kind/observations_imported/entities_imported/
  skipped_count, import_summary present in the response, duplicate
  warning on re-upload of identical content.

Design decision (documented per the milestone spec): an empty/header-only
CSV is NOT a 400 — it's a zero-observation import with a `skipped` note,
consistent between the pure parser and the full route (see
test_hc_fimp_007/008 and test_hc_fimp_066).
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.auth import Session
from core.profile_database import ProfileDatabaseBase
from modules.fhir_export import build_fhir_bundle
from modules.ingest import ImportResult, IngestModule
from modules.import_structured import parse_fhir_bundle, parse_lab_csv


def _session(profile_id: str = "test-profile") -> Session:
    return Session(
        profile_id=profile_id,
        profile_name="Test Profile",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )


def _bundle(entries: list[dict]) -> str:
    return json.dumps({"resourceType": "Bundle", "type": "collection", "entry": entries})


# ---------------------------------------------------------------------------
# parse_lab_csv
# ---------------------------------------------------------------------------


class TestParseLabCsv:
    def test_hc_fimp_001_happy_path_all_columns(self):
        csv_text = (
            "Date,Analyte,Value,Unit,Reference Low,Reference High,Flag\n"
            "2026-06-01,Hemoglobin A1c,7.2,%,4.0,5.6,H\n"
        )
        result = parse_lab_csv(csv_text)
        assert result.source_kind == "lab_csv"
        assert not result.skipped
        [obs] = result.observations
        assert obs["analyte_raw"] == "Hemoglobin A1c"
        assert obs["value"] == 7.2
        assert obs["unit"] == "%"
        assert obs["ref_low"] == 4.0
        assert obs["ref_high"] == 5.6
        assert obs["flag"] == "H"
        assert obs["collected_at"] == "2026-06-01"
        assert obs["confidence"] == 0.6

    def test_hc_fimp_002_header_aliases_case_insensitive(self):
        csv_text = (
            "collected,test,result,units,low,high,abnormal\n"
            "2026-05-15,Glucose,101,mg/dL,70,99,H\n"
        )
        result = parse_lab_csv(csv_text)
        [obs] = result.observations
        assert obs["analyte_raw"] == "Glucose"
        assert obs["value"] == 101
        assert obs["unit"] == "mg/dL"
        assert obs["ref_low"] == 70
        assert obs["ref_high"] == 99
        assert obs["flag"] == "H"
        assert obs["collected_at"] == "2026-05-15"

    def test_hc_fimp_003_unparseable_value_becomes_value_text(self):
        csv_text = "Analyte,Value\nUrine color,Amber\n"
        [obs] = parse_lab_csv(csv_text).observations
        assert obs["value"] is None
        assert obs["value_text"] == "Amber"

    def test_hc_fimp_004_missing_analyte_row_skipped_with_reason(self):
        csv_text = "Analyte,Value\n,5\nGlucose,100\n"
        result = parse_lab_csv(csv_text)
        assert len(result.observations) == 1
        assert result.skipped == [
            {"reason": "missing_analyte", "detail": "row 2: no analyte/test name"}
        ]

    def test_hc_fimp_005_unparseable_date_leaves_observation_undated(self):
        csv_text = "Date,Analyte,Value\nnot-a-date,Glucose,100\n"
        [obs] = parse_lab_csv(csv_text).observations
        assert obs["collected_at"] is None

    def test_hc_fimp_006_mmddyyyy_date_parses(self):
        csv_text = "Date,Analyte,Value\n06/01/2026,Glucose,100\n"
        [obs] = parse_lab_csv(csv_text).observations
        assert obs["collected_at"] == "2026-06-01"

    def test_hc_fimp_007_empty_csv_is_zero_import_not_error(self):
        result = parse_lab_csv("")
        assert result.observations == []
        assert result.skipped and result.skipped[0]["reason"] == "empty_file"

    def test_hc_fimp_008_header_only_no_data_rows(self):
        result = parse_lab_csv("Date,Analyte,Value\n")
        assert result.observations == []
        assert result.skipped == [
            {"reason": "no_data_rows", "detail": "CSV had a header but no data rows"}
        ]

    def test_hc_fimp_009_no_analyte_column_at_all(self):
        result = parse_lab_csv("Foo,Bar\n1,2\n")
        assert result.observations == []
        assert result.skipped[0]["reason"] == "no_analyte_column"

    def test_hc_fimp_010_injection_payload_analyte_stored_as_inert_text(self):
        payload = "'; DROP TABLE observations; --"
        csv_text = f"Analyte,Value\n{payload},5\n"
        [obs] = parse_lab_csv(csv_text).observations
        assert obs["analyte_raw"] == payload
        assert obs["value"] == 5

    def test_hc_fimp_011_huge_field_value_length_capped(self):
        huge = "x" * 5000
        csv_text = f"Analyte,Value\n{huge},5\n"
        [obs] = parse_lab_csv(csv_text).observations
        assert len(obs["analyte_raw"]) == 2000


# ---------------------------------------------------------------------------
# parse_fhir_bundle
# ---------------------------------------------------------------------------


class TestParseFhirBundle:
    def test_hc_fimp_020_observation_mapped_with_range_and_interpretation(self):
        bundle = _bundle([{
            "resource": {
                "resourceType": "Observation",
                "id": "obs-1",
                "code": {"text": "Hemoglobin A1c"},
                "valueQuantity": {"value": 7.2, "unit": "%"},
                "referenceRange": [
                    {"low": {"value": 4.0}, "high": {"value": 5.6}, "text": "4.0-5.6 %"}
                ],
                "interpretation": [{"text": "H"}],
                "effectiveDateTime": "2026-06-01T00:00:00Z",
            }
        }])
        result = parse_fhir_bundle(bundle)
        assert result.source_kind == "fhir_bundle"
        [obs] = result.observations
        assert obs["analyte_raw"] == "Hemoglobin A1c"
        assert obs["value"] == 7.2
        assert obs["unit"] == "%"
        assert obs["ref_low"] == 4.0
        assert obs["ref_high"] == 5.6
        assert obs["ref_range_text"] == "4.0-5.6 %"
        assert obs["flag"] == "H"
        assert obs["collected_at"] == "2026-06-01"
        assert obs["confidence"] == 0.6

    def test_hc_fimp_021_observation_value_string(self):
        bundle = _bundle([{
            "resource": {
                "resourceType": "Observation",
                "code": {"text": "Urine culture"},
                "valueString": "No growth",
            }
        }])
        [obs] = parse_fhir_bundle(bundle).observations
        assert obs["value"] is None
        assert obs["value_text"] == "No growth"

    def test_hc_fimp_022_medication_statement_active_start_verb(self):
        bundle = _bundle([{
            "resource": {
                "resourceType": "MedicationStatement",
                "status": "active",
                "medicationCodeableConcept": {"text": "metformin"},
                "dosage": [{"text": "500 mg twice daily"}],
            }
        }])
        [ent] = parse_fhir_bundle(bundle).entities
        assert ent["entity_type"] == "medication_change"
        assert ent["category"] == "visit_notes"
        assert ent["entity_value"] == "start metformin 500 mg twice daily"
        assert ent["quote"] is None
        assert ent["confidence"] == 0.6

    def test_hc_fimp_023_medication_statement_completed_stop_verb(self):
        bundle = _bundle([{
            "resource": {
                "resourceType": "MedicationStatement",
                "status": "completed",
                "medicationCodeableConcept": {"text": "amoxicillin"},
            }
        }])
        [ent] = parse_fhir_bundle(bundle).entities
        assert ent["entity_value"] == "stop amoxicillin"

    def test_hc_fimp_024_condition_maps_to_diagnosis_entity(self):
        bundle = _bundle([{
            "resource": {"resourceType": "Condition", "code": {"text": "Type 2 diabetes"}}
        }])
        [ent] = parse_fhir_bundle(bundle).entities
        assert ent["entity_type"] == "diagnosis"
        assert ent["category"] == "visit_notes"
        assert ent["entity_value"] == "Type 2 diabetes"
        assert ent["quote"] is None

    def test_hc_fimp_025_unknown_resource_type_skipped_and_counted(self):
        bundle = _bundle([{"resource": {"resourceType": "Encounter", "id": "enc-1"}}])
        result = parse_fhir_bundle(bundle)
        assert result.observations == []
        assert result.entities == []
        assert result.skipped == [{"reason": "unknown_resource_type", "detail": "Encounter"}]

    def test_hc_fimp_026_malformed_json_raises_value_error(self):
        with pytest.raises(ValueError):
            parse_fhir_bundle("{not valid json")

    def test_hc_fimp_027_truncated_json_raises_value_error(self):
        with pytest.raises(ValueError):
            parse_fhir_bundle('{"resourceType": "Bundle", "entry": [')

    def test_hc_fimp_028_non_bundle_json_raises_value_error(self):
        with pytest.raises(ValueError):
            parse_fhir_bundle(json.dumps({"resourceType": "Patient"}))

    def test_hc_fimp_029_observation_missing_code_text_skipped(self):
        bundle = _bundle([{"resource": {"resourceType": "Observation", "id": "obs-x"}}])
        result = parse_fhir_bundle(bundle)
        assert result.observations == []
        assert result.skipped[0]["reason"] == "unparseable_observation"

    def test_hc_fimp_030_round_trip_with_hc_m22_build_fhir_bundle(self):
        obs = {
            "id": str(uuid.uuid4()),
            "analyte_canonical": "glucose",
            "value": 101.0,
            "value_text": None,
            "unit": "mg/dL",
            "ref_low": 70.0,
            "ref_high": 99.0,
            "ref_range_text": None,
            "flag": "H",
            "user_verified": True,
            "collected_at": datetime(2026, 6, 1, tzinfo=timezone.utc),
        }
        med = {
            "id": str(uuid.uuid4()),
            "name": "Metformin",
            "generic_name": "metformin",
            "dosage_amount": 500.0,
            "dosage_unit": "mg",
            "dosage_form": "tablet",
            "frequency": "twice_daily",
            "instructions": None,
            "is_active": True,
            "started_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "ended_at": None,
        }
        exported = build_fhir_bundle("Jane Doe", [obs], [med], [], [], [])
        bundle_json = json.dumps(exported["bundle"])

        result = parse_fhir_bundle(bundle_json)

        [round_tripped_obs] = result.observations
        assert round_tripped_obs["analyte_raw"] == "glucose"
        assert round_tripped_obs["value"] == 101.0
        assert round_tripped_obs["unit"] == "mg/dL"
        assert round_tripped_obs["ref_low"] == 70.0
        assert round_tripped_obs["ref_high"] == 99.0
        assert round_tripped_obs["flag"] == "H"

        [round_tripped_med] = result.entities
        assert round_tripped_med["entity_type"] == "medication_change"
        assert round_tripped_med["entity_value"].startswith("start metformin")
        assert "500.0 mg" in round_tripped_med["entity_value"]


# ---------------------------------------------------------------------------
# modules/ingest.py doc-type detection
# ---------------------------------------------------------------------------


class TestIngestDocTypeDetection:
    def _module(self, tmp_path) -> IngestModule:
        return IngestModule(tmp_path, encryption_key=b"k" * 32)

    def test_hc_fimp_040_csv_extension_detected_as_lab_csv(self, tmp_path):
        ingest = self._module(tmp_path)
        assert ingest.detect_doc_type("labs.csv", b"Analyte,Value\nGlucose,100\n") == "lab_csv"

    def test_hc_fimp_041_valid_bundle_json_detected_as_fhir_bundle(self, tmp_path):
        ingest = self._module(tmp_path)
        data = json.dumps({"resourceType": "Bundle", "entry": []}).encode()
        assert ingest.detect_doc_type("export.json", data) == "fhir_bundle"

    def test_hc_fimp_042_non_bundle_json_detected_as_unknown(self, tmp_path):
        ingest = self._module(tmp_path)
        data = json.dumps({"resourceType": "Patient"}).encode()
        assert ingest.detect_doc_type("patient.json", data) == "unknown"

    def test_hc_fimp_043_malformed_json_detected_as_unknown(self, tmp_path):
        ingest = self._module(tmp_path)
        assert ingest.detect_doc_type("broken.json", b"{not json") == "unknown"

    @pytest.mark.asyncio
    async def test_hc_fimp_044_import_document_rejects_non_bundle_json(self, tmp_path):
        ingest = self._module(tmp_path)
        data = json.dumps({"resourceType": "Patient"}).encode()
        with pytest.raises(ValueError, match="FHIR"):
            await ingest.import_document(file=io.BytesIO(data), filename="patient.json", profile_id="p1")

    @pytest.mark.asyncio
    async def test_hc_fimp_045_import_document_accepts_valid_bundle(self, tmp_path):
        ingest = self._module(tmp_path)
        data = json.dumps({"resourceType": "Bundle", "entry": []}).encode()
        result = await ingest.import_document(file=io.BytesIO(data), filename="export.json", profile_id="p1")
        assert result.doc_type == "fhir_bundle"

    @pytest.mark.asyncio
    async def test_hc_fimp_046_import_document_accepts_csv(self, tmp_path):
        ingest = self._module(tmp_path)
        data = b"Analyte,Value\nGlucose,100\n"
        result = await ingest.import_document(file=io.BytesIO(data), filename="labs.csv", profile_id="p1")
        assert result.doc_type == "lab_csv"


# ---------------------------------------------------------------------------
# api/documents.py POST /documents/import route
# ---------------------------------------------------------------------------


class _FakeStructuredIngestModule:
    """Mirrors IngestModule's content-hash + doc-type-detection contract
    without touching disk/encryption, so route tests exercise the real
    persistence pipeline (_run_structured_import_pipeline) against a real
    in-memory profile DB."""

    def __init__(self, *_args, **_kwargs):
        pass

    async def import_document(self, *, file, filename, profile_id, source=None):
        data = file.read()
        content_hash = hashlib.sha256(data).hexdigest()
        ext = Path(filename).suffix.lower()
        if ext == ".csv":
            doc_type = "lab_csv"
        elif ext == ".json":
            try:
                parsed = json.loads(data.decode("utf-8"))
            except (UnicodeDecodeError, ValueError) as exc:
                raise ValueError("JSON file is not a valid FHIR R4 Bundle") from exc
            if not (isinstance(parsed, dict) and parsed.get("resourceType") == "Bundle"):
                raise ValueError("JSON file is not a valid FHIR R4 Bundle")
            doc_type = "fhir_bundle"
        else:
            raise ValueError(f"Unsupported file: {filename}")
        return ImportResult(
            document_id=str(uuid.uuid4()),
            path_hash="p" * 64,
            content_hash=content_hash,
            doc_type=doc_type,
            page_count=None,
            is_duplicate=False,
            metadata={"original_filename": filename},
            encrypted=True,
        )


class _FakeMasterDb:
    def add(self, obj):
        pass

    async def commit(self):
        return None


@pytest_asyncio.fixture
async def real_profile_db():
    """Real in-memory SQLite profile DB (mirrors tests/test_pinboards.py's
    `real_profile_db`), so duplicate-warning queries and persistence run as
    real SQL rather than call-order-dependent mocks."""
    from models import Document, DocumentCategory, DocumentEntity, Observation  # noqa: F401

    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(ProfileDatabaseBase.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
class TestStructuredImportRoute:
    async def test_hc_fimp_060_csv_upload_persists_unverified_observations_and_category(
        self, monkeypatch, real_profile_db
    ):
        from api import documents as documents_api
        from models import DocumentCategory, Observation
        import modules

        csv_bytes = (
            b"Date,Analyte,Value,Unit,Reference Low,Reference High,Flag\n"
            b"2026-06-01,Glucose,101,mg/dL,70,99,H\n"
        )

        monkeypatch.setattr(documents_api, "get_profile_encryption_key", lambda _pid: b"x" * 32)
        monkeypatch.setattr(documents_api, "get_decrypted_document", lambda _pid, _did: io.BytesIO(csv_bytes))
        monkeypatch.setattr(modules, "IngestModule", _FakeStructuredIngestModule)
        audit = AsyncMock()
        monkeypatch.setattr(documents_api, "log_document_event", audit)

        response = await documents_api.import_document(
            session=_session(),
            file=UploadFile(filename="labs.csv", file=io.BytesIO(csv_bytes)),
            profile_db=real_profile_db,
            master_db=_FakeMasterDb(),
        )

        assert response.document.doc_type == "lab_csv"
        assert response.observations_extracted == 1
        assert response.needs_verification is True
        assert response.import_summary is not None
        assert response.import_summary.source_kind == "lab_csv"
        assert response.import_summary.observations_imported == 1
        assert response.import_summary.entities_imported == 0
        assert response.import_summary.skipped == []

        obs_rows = (
            await real_profile_db.execute(select(Observation).where(Observation.doc_id == response.document.id))
        ).scalars().all()
        assert len(obs_rows) == 1
        assert obs_rows[0].analyte_raw == "Glucose"
        assert obs_rows[0].user_verified is False
        assert obs_rows[0].extraction_confidence == 0.6

        cat_rows = (
            await real_profile_db.execute(
                select(DocumentCategory).where(DocumentCategory.doc_id == response.document.id)
            )
        ).scalars().all()
        assert len(cat_rows) == 1
        assert cat_rows[0].category == "lab"

        audit.assert_awaited_once()
        details = audit.await_args.kwargs["details"]
        assert details["source_kind"] == "lab_csv"
        assert details["observations_imported"] == 1
        assert details["entities_imported"] == 0
        assert details["skipped_count"] == 0

    async def test_hc_fimp_061_fhir_upload_persists_entities_and_observations(
        self, monkeypatch, real_profile_db
    ):
        from api import documents as documents_api
        from models import DocumentCategory, DocumentEntity
        import modules

        bundle = _bundle([
            {"resource": {
                "resourceType": "Observation",
                "code": {"text": "Glucose"},
                "valueQuantity": {"value": 101, "unit": "mg/dL"},
            }},
            {"resource": {
                "resourceType": "MedicationStatement",
                "status": "active",
                "medicationCodeableConcept": {"text": "metformin"},
                "dosage": [{"text": "500 mg twice daily"}],
            }},
            {"resource": {"resourceType": "Condition", "code": {"text": "Type 2 diabetes"}}},
        ]).encode()

        monkeypatch.setattr(documents_api, "get_profile_encryption_key", lambda _pid: b"x" * 32)
        monkeypatch.setattr(documents_api, "get_decrypted_document", lambda _pid, _did: io.BytesIO(bundle))
        monkeypatch.setattr(modules, "IngestModule", _FakeStructuredIngestModule)

        response = await documents_api.import_document(
            session=_session(),
            file=UploadFile(filename="export.json", file=io.BytesIO(bundle)),
            profile_db=real_profile_db,
            master_db=_FakeMasterDb(),
        )

        assert response.document.doc_type == "fhir_bundle"
        assert response.import_summary.source_kind == "fhir_bundle"
        assert response.import_summary.observations_imported == 1
        assert response.import_summary.entities_imported == 2

        entity_rows = (
            await real_profile_db.execute(
                select(DocumentEntity).where(DocumentEntity.doc_id == response.document.id)
            )
        ).scalars().all()
        assert len(entity_rows) == 2
        for row in entity_rows:
            assert row.verified_by_user is None
            assert row.extraction_version == "import-v1"
            assert row.quote is None
        med_row = next(r for r in entity_rows if r.entity_type == "medication_change")
        assert med_row.entity_value.startswith("start metformin")
        diagnosis_row = next(r for r in entity_rows if r.entity_type == "diagnosis")
        assert diagnosis_row.entity_value == "Type 2 diabetes"

        cat_rows = (
            await real_profile_db.execute(
                select(DocumentCategory).where(DocumentCategory.doc_id == response.document.id)
            )
        ).scalars().all()
        assert len(cat_rows) == 1
        assert cat_rows[0].category == "lab"  # observations present -> lab wins the tie-break

    async def test_hc_fimp_062_duplicate_csv_reupload_warns(self, monkeypatch, real_profile_db):
        from api import documents as documents_api
        import modules

        csv_bytes = b"Analyte,Value\nGlucose,100\n"
        monkeypatch.setattr(documents_api, "get_profile_encryption_key", lambda _pid: b"x" * 32)
        monkeypatch.setattr(documents_api, "get_decrypted_document", lambda _pid, _did: io.BytesIO(csv_bytes))
        monkeypatch.setattr(modules, "IngestModule", _FakeStructuredIngestModule)

        session = _session()
        first = await documents_api.import_document(
            session=session,
            file=UploadFile(filename="labs.csv", file=io.BytesIO(csv_bytes)),
            profile_db=real_profile_db,
            master_db=_FakeMasterDb(),
        )
        assert first.duplicate_warning is None

        second = await documents_api.import_document(
            session=session,
            file=UploadFile(filename="labs.csv", file=io.BytesIO(csv_bytes)),
            profile_db=real_profile_db,
            master_db=_FakeMasterDb(),
        )
        assert second.duplicate_warning is not None
        assert second.duplicate_warning.match_type == "content_hash"
        assert second.document.id != first.document.id

    async def test_hc_fimp_063_injection_payload_analyte_via_route_stays_inert_and_unverified(
        self, monkeypatch, real_profile_db
    ):
        from api import documents as documents_api
        from models import Observation
        import modules

        payload = "Robert'); DROP TABLE observations;--"
        csv_bytes = f"Analyte,Value\n{payload},5\n".encode()
        monkeypatch.setattr(documents_api, "get_profile_encryption_key", lambda _pid: b"x" * 32)
        monkeypatch.setattr(documents_api, "get_decrypted_document", lambda _pid, _did: io.BytesIO(csv_bytes))
        monkeypatch.setattr(modules, "IngestModule", _FakeStructuredIngestModule)

        response = await documents_api.import_document(
            session=_session(),
            file=UploadFile(filename="labs.csv", file=io.BytesIO(csv_bytes)),
            profile_db=real_profile_db,
            master_db=_FakeMasterDb(),
        )

        obs_rows = (
            await real_profile_db.execute(select(Observation).where(Observation.doc_id == response.document.id))
        ).scalars().all()
        assert len(obs_rows) == 1
        assert obs_rows[0].analyte_raw == payload
        assert obs_rows[0].user_verified is False

    async def test_hc_fimp_064_malformed_json_upload_returns_400(self, monkeypatch, real_profile_db):
        from api import documents as documents_api
        import modules

        monkeypatch.setattr(documents_api, "get_profile_encryption_key", lambda _pid: b"x" * 32)
        monkeypatch.setattr(modules, "IngestModule", _FakeStructuredIngestModule)

        with pytest.raises(HTTPException) as exc:
            await documents_api.import_document(
                session=_session(),
                file=UploadFile(filename="broken.json", file=io.BytesIO(b"{not json")),
                profile_db=real_profile_db,
                master_db=_FakeMasterDb(),
            )
        assert exc.value.status_code == 400

    async def test_hc_fimp_065_non_bundle_json_upload_returns_400(self, monkeypatch, real_profile_db):
        from api import documents as documents_api
        import modules

        monkeypatch.setattr(documents_api, "get_profile_encryption_key", lambda _pid: b"x" * 32)
        monkeypatch.setattr(modules, "IngestModule", _FakeStructuredIngestModule)
        data = json.dumps({"resourceType": "Patient"}).encode()

        with pytest.raises(HTTPException) as exc:
            await documents_api.import_document(
                session=_session(),
                file=UploadFile(filename="patient.json", file=io.BytesIO(data)),
                profile_db=real_profile_db,
                master_db=_FakeMasterDb(),
            )
        assert exc.value.status_code == 400

    async def test_hc_fimp_066_empty_csv_upload_is_zero_import_not_error(self, monkeypatch, real_profile_db):
        from api import documents as documents_api
        import modules

        monkeypatch.setattr(documents_api, "get_profile_encryption_key", lambda _pid: b"x" * 32)
        monkeypatch.setattr(documents_api, "get_decrypted_document", lambda _pid, _did: io.BytesIO(b""))
        monkeypatch.setattr(modules, "IngestModule", _FakeStructuredIngestModule)

        response = await documents_api.import_document(
            session=_session(),
            file=UploadFile(filename="empty.csv", file=io.BytesIO(b"")),
            profile_db=real_profile_db,
            master_db=_FakeMasterDb(),
        )
        assert response.document.doc_type == "lab_csv"
        assert response.import_summary.observations_imported == 0
        assert response.import_summary.skipped[0]["reason"] == "empty_file"
