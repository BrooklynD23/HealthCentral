"""HC-M22 FHIR R4 export tests (HC-FHIR-NNN).

Covers:
- Pure mapping (modules/fhir_export.py): bundle shape, per-resource field
  mapping, unverified-data exclusion, no-invented-dates, redaction,
  include_* toggles.
- API routes (api/export.py): confirm gating, download happy-path/404/403,
  audit logging on generate + download.
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.auth import Session
from core.time import utcnow
from modules.fhir_export import build_fhir_bundle


def _session(profile_id: str = "test-profile") -> Session:
    return Session(
        profile_id=profile_id,
        profile_name="Jane Doe",
        expires_at=utcnow() + timedelta(hours=1),
    )


def _obs(**overrides) -> dict:
    fields = dict(
        id=str(uuid.uuid4()),
        analyte_canonical="hemoglobin_a1c",
        value=7.2,
        value_text=None,
        unit="%",
        ref_low=4.0,
        ref_high=5.6,
        ref_range_text=None,
        flag="H",
        user_verified=True,
        collected_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    fields.update(overrides)
    return fields


def _med(**overrides) -> dict:
    fields = dict(
        id=str(uuid.uuid4()),
        name="Lisinopril",
        generic_name="lisinopril",
        dosage_amount=10.0,
        dosage_unit="mg",
        dosage_form="tablet",
        frequency="once_daily",
        instructions="Take in the morning",
        is_active=True,
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ended_at=None,
    )
    fields.update(overrides)
    return fields


def _doc(**overrides) -> dict:
    fields = dict(
        id=str(uuid.uuid4()),
        category="lab",
        collection_date=datetime(2026, 5, 20, tzinfo=timezone.utc),
        imported_at=datetime(2026, 5, 21, tzinfo=timezone.utc),
        metadata_json=None,
    )
    fields.update(overrides)
    return fields


def _entity(doc_id: str, **overrides) -> dict:
    fields = dict(
        id=str(uuid.uuid4()),
        doc_id=doc_id,
        entity_type="diagnosis",
        entity_value="Type 2 diabetes",
        quote="Assessment: Type 2 diabetes, stable",
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
    )
    fields.update(overrides)
    return fields


class TestBundleStructure:
    def test_hc_fhir_001_bundle_resourcetype_type_and_entry_fullurls(self):
        result = build_fhir_bundle(
            "Jane Doe", [_obs()], [_med()], [], [], [],
        )
        bundle = result["bundle"]
        assert bundle["resourceType"] == "Bundle"
        assert bundle["type"] == "collection"
        assert "timestamp" in bundle
        assert bundle["entry"], "bundle should have at least the Patient entry"
        for entry in bundle["entry"]:
            assert entry["fullUrl"] == f"urn:uuid:{entry['resource']['id']}"
            assert entry["resource"]["meta"]["source"] == "urn:healthcentral:local-export"

    def test_hc_fhir_002_patient_resource_present_and_referenced(self):
        result = build_fhir_bundle("Jane Doe", [_obs()], [], [], [], [])
        resources = [e["resource"] for e in result["bundle"]["entry"]]
        patients = [r for r in resources if r["resourceType"] == "Patient"]
        assert len(patients) == 1
        assert patients[0]["name"][0]["text"] == "Jane Doe"

        observations = [r for r in resources if r["resourceType"] == "Observation"]
        assert observations
        assert observations[0]["subject"]["reference"] == f"Patient/{patients[0]['id']}"


class TestObservationMapping:
    def test_hc_fhir_010_verified_observation_mapped_with_all_fields(self):
        obs = _obs(ref_range_text="4.0-5.6 %")
        result = build_fhir_bundle("Jane Doe", [obs], [], [], [], [])
        resources = [e["resource"] for e in result["bundle"]["entry"]]
        [fhir_obs] = [r for r in resources if r["resourceType"] == "Observation"]

        assert fhir_obs["status"] == "final"
        assert fhir_obs["code"]["text"] == "hemoglobin_a1c"
        assert fhir_obs["valueQuantity"] == {"value": 7.2, "unit": "%"}
        assert fhir_obs["referenceRange"][0]["low"] == {"value": 4.0}
        assert fhir_obs["referenceRange"][0]["high"] == {"value": 5.6}
        assert fhir_obs["referenceRange"][0]["text"] == "4.0-5.6 %"
        assert fhir_obs["interpretation"][0]["text"] == "H"
        assert fhir_obs["effectiveDateTime"].startswith("2026-06-01")

    def test_hc_fhir_011_value_text_maps_to_valuestring(self):
        obs = _obs(value=None, value_text="Positive")
        result = build_fhir_bundle("Jane Doe", [obs], [], [], [], [])
        [fhir_obs] = [
            e["resource"] for e in result["bundle"]["entry"]
            if e["resource"]["resourceType"] == "Observation"
        ]
        assert fhir_obs["valueString"] == "Positive"
        assert "valueQuantity" not in fhir_obs

    def test_hc_fhir_012_unverified_observation_excluded(self):
        verified = _obs(analyte_canonical="glucose", user_verified=True)
        unverified = _obs(analyte_canonical="private-unverified-marker", user_verified=False)
        result = build_fhir_bundle("Jane Doe", [verified, unverified], [], [], [], [])
        resources = [e["resource"] for e in result["bundle"]["entry"]]
        observations = [r for r in resources if r["resourceType"] == "Observation"]
        assert len(observations) == 1
        assert observations[0]["code"]["text"] == "glucose"
        serialized = json.dumps(result["bundle"])
        assert "private-unverified-marker" not in serialized

    def test_hc_fhir_013_no_effective_datetime_when_collected_at_is_none(self):
        obs = _obs(collected_at=None)
        result = build_fhir_bundle("Jane Doe", [obs], [], [], [], [])
        [fhir_obs] = [
            e["resource"] for e in result["bundle"]["entry"]
            if e["resource"]["resourceType"] == "Observation"
        ]
        assert "effectiveDateTime" not in fhir_obs

    def test_hc_fhir_014_include_observations_false_excludes_resource_type(self):
        result = build_fhir_bundle(
            "Jane Doe", [_obs()], [], [], [], [], include_observations=False,
        )
        resources = [e["resource"] for e in result["bundle"]["entry"]]
        assert not any(r["resourceType"] == "Observation" for r in resources)


class TestMedicationMapping:
    def test_hc_fhir_020_medication_statement_fields(self):
        med = _med()
        result = build_fhir_bundle("Jane Doe", [], [med], [], [], [])
        [stmt] = [
            e["resource"] for e in result["bundle"]["entry"]
            if e["resource"]["resourceType"] == "MedicationStatement"
        ]
        assert stmt["status"] == "active"
        assert stmt["medicationCodeableConcept"]["text"] == "Lisinopril"
        assert stmt["medicationCodeableConcept"]["coding"][0]["display"] == "lisinopril"
        assert "10.0 mg" in stmt["dosage"][0]["text"]
        assert "tablet" in stmt["dosage"][0]["text"]
        assert stmt["effectivePeriod"]["start"].startswith("2026-01-01")
        assert "end" not in stmt["effectivePeriod"]

    def test_hc_fhir_021_inactive_medication_status_completed(self):
        med = _med(is_active=False, ended_at=datetime(2026, 3, 1, tzinfo=timezone.utc))
        result = build_fhir_bundle("Jane Doe", [], [med], [], [], [])
        [stmt] = [
            e["resource"] for e in result["bundle"]["entry"]
            if e["resource"]["resourceType"] == "MedicationStatement"
        ]
        assert stmt["status"] == "completed"
        assert stmt["effectivePeriod"]["end"].startswith("2026-03-01")


class TestConditionMapping:
    def test_hc_fhir_030_verified_diagnosis_entity_mapped(self):
        doc = _doc(id="doc-1", category="pathology")
        entity = _entity("doc-1", entity_type="diagnosis", verified_by_user=True)
        result = build_fhir_bundle("Jane Doe", [], [], [doc], [entity], [])
        [condition] = [
            e["resource"] for e in result["bundle"]["entry"]
            if e["resource"]["resourceType"] == "Condition"
        ]
        assert condition["code"]["text"] == "Type 2 diabetes"
        assert condition["verificationStatus"]["text"] == "unconfirmed"
        assert condition["note"][0]["text"] == entity["quote"]

    @pytest.mark.parametrize("verified_by_user", [None, False])
    def test_hc_fhir_031_unreviewed_and_rejected_entities_excluded(self, verified_by_user):
        entity = _entity("doc-1", entity_type="diagnosis", verified_by_user=verified_by_user)
        result = build_fhir_bundle("Jane Doe", [], [], [], [entity], [])
        resources = [e["resource"] for e in result["bundle"]["entry"]]
        assert not any(r["resourceType"] == "Condition" for r in resources)

    def test_hc_fhir_032_non_diagnosis_entity_type_excluded_from_condition(self):
        entity = _entity("doc-1", entity_type="visit_type", entity_value="Annual physical")
        result = build_fhir_bundle("Jane Doe", [], [], [], [entity], [])
        resources = [e["resource"] for e in result["bundle"]["entry"]]
        assert not any(r["resourceType"] == "Condition" for r in resources)


class TestDocumentReferenceMapping:
    def test_hc_fhir_040_document_reference_fields(self):
        doc = _doc(category="imaging", metadata_json=json.dumps({"title": "Chest X-ray"}))
        result = build_fhir_bundle("Jane Doe", [], [], [doc], [], [])
        [doc_ref] = [
            e["resource"] for e in result["bundle"]["entry"]
            if e["resource"]["resourceType"] == "DocumentReference"
        ]
        assert doc_ref["status"] == "current"
        assert doc_ref["type"]["text"] == "imaging"
        assert doc_ref["date"].startswith("2026-05-20")
        assert doc_ref["description"] == "Chest X-ray"

    def test_hc_fhir_041_falls_back_to_imported_at_when_no_collection_date(self):
        doc = _doc(collection_date=None)
        result = build_fhir_bundle("Jane Doe", [], [], [doc], [], [])
        [doc_ref] = [
            e["resource"] for e in result["bundle"]["entry"]
            if e["resource"]["resourceType"] == "DocumentReference"
        ]
        assert doc_ref["date"].startswith("2026-05-21")


class TestEncounterMapping:
    def test_hc_fhir_050_visit_notes_document_becomes_encounter(self):
        doc = _doc(id="doc-visit", category="visit_notes")
        visit_type_entity = _entity(
            "doc-visit", entity_type="visit_type", entity_value="Annual physical",
            verified_by_user=True,
        )
        result = build_fhir_bundle("Jane Doe", [], [], [doc], [visit_type_entity], [])
        [encounter] = [
            e["resource"] for e in result["bundle"]["entry"]
            if e["resource"]["resourceType"] == "Encounter"
        ]
        assert encounter["class"]["text"] == "Annual physical"
        assert encounter["period"]["start"].startswith("2026-05-20")

    def test_hc_fhir_051_non_visit_notes_document_produces_no_encounter(self):
        doc = _doc(category="lab")
        result = build_fhir_bundle("Jane Doe", [], [], [doc], [], [])
        resources = [e["resource"] for e in result["bundle"]["entry"]]
        assert not any(r["resourceType"] == "Encounter" for r in resources)

    def test_hc_fhir_052_unverified_visit_type_entity_not_used_for_class(self):
        doc = _doc(id="doc-visit", category="visit_notes")
        visit_type_entity = _entity(
            "doc-visit", entity_type="visit_type", entity_value="Annual physical",
            verified_by_user=None,
        )
        result = build_fhir_bundle("Jane Doe", [], [], [doc], [visit_type_entity], [])
        [encounter] = [
            e["resource"] for e in result["bundle"]["entry"]
            if e["resource"]["resourceType"] == "Encounter"
        ]
        assert "class" not in encounter


class TestCarePlanMapping:
    def test_hc_fhir_060_open_needs_review_done_tasks_mapped_ignored_excluded(self):
        tasks = [
            _task(title="Repeat CBC", status="open"),
            _task(title="Follow up with cardiologist", status="needs_review"),
            _task(title="Flu shot", status="done"),
            _task(title="Old reminder", status="ignored"),
        ]
        result = build_fhir_bundle("Jane Doe", [], [], [], [], tasks)
        [plan] = [
            e["resource"] for e in result["bundle"]["entry"]
            if e["resource"]["resourceType"] == "CarePlan"
        ]
        descriptions = {a["detail"]["description"]: a["detail"]["status"] for a in plan["activity"]}
        assert descriptions["Repeat CBC"] == "in-progress"
        assert descriptions["Follow up with cardiologist"] == "scheduled"
        assert descriptions["Flu shot"] == "completed"
        assert "Old reminder" not in descriptions

    def test_hc_fhir_061_no_care_plan_resource_when_all_tasks_ignored(self):
        result = build_fhir_bundle(
            "Jane Doe", [], [], [], [], [_task(status="ignored")],
        )
        resources = [e["resource"] for e in result["bundle"]["entry"]]
        assert not any(r["resourceType"] == "CarePlan" for r in resources)

    def test_hc_fhir_062_scheduled_date_only_when_due_date_present(self):
        tasks = [_task(title="No due date", due_date=None)]
        result = build_fhir_bundle("Jane Doe", [], [], [], [], tasks)
        [plan] = [
            e["resource"] for e in result["bundle"]["entry"]
            if e["resource"]["resourceType"] == "CarePlan"
        ]
        assert "scheduledString" not in plan["activity"][0]["detail"]


class TestDiagnosticReportMapping:
    def test_hc_fhir_070_imaging_doc_with_verified_findings_becomes_report(self):
        doc = _doc(id="doc-img", category="imaging")
        entities = [
            _entity("doc-img", entity_type="impression", entity_value="No acute findings", verified_by_user=True),
            _entity("doc-img", entity_type="finding", entity_value="Mild degenerative changes", verified_by_user=True),
        ]
        result = build_fhir_bundle("Jane Doe", [], [], [doc], entities, [])
        [report] = [
            e["resource"] for e in result["bundle"]["entry"]
            if e["resource"]["resourceType"] == "DiagnosticReport"
        ]
        assert "No acute findings" in report["conclusion"]
        assert "Mild degenerative changes" in report["conclusion"]
        assert report["code"]["text"] == "imaging"

    def test_hc_fhir_071_no_report_when_no_verified_findings(self):
        doc = _doc(category="imaging")
        entities = [
            _entity("doc-img", entity_type="impression", entity_value="Unreviewed", verified_by_user=None),
        ]
        result = build_fhir_bundle("Jane Doe", [], [], [doc], entities, [])
        resources = [e["resource"] for e in result["bundle"]["entry"]]
        assert not any(r["resourceType"] == "DiagnosticReport" for r in resources)

    def test_hc_fhir_072_lab_category_document_never_becomes_report(self):
        doc = _doc(id="doc-lab", category="lab")
        entities = [
            _entity("doc-lab", entity_type="impression", entity_value="n/a", verified_by_user=True),
        ]
        result = build_fhir_bundle("Jane Doe", [], [], [doc], entities, [])
        resources = [e["resource"] for e in result["bundle"]["entry"]]
        assert not any(r["resourceType"] == "DiagnosticReport" for r in resources)


class TestRedaction:
    def test_hc_fhir_080_seeded_phi_redacted_from_serialized_bundle_and_counted(self):
        doc = _doc(id="doc-1", category="pathology")
        entity = _entity(
            "doc-1",
            entity_type="diagnosis",
            entity_value="Stage II adenocarcinoma",
            quote="Call patient at 555-123-4567, MRN: A1234567",
            verified_by_user=True,
        )
        task = _task(source_quote="Contact 555-987-6543 to schedule, MRN: B7654321")
        result = build_fhir_bundle("Jane Doe", [], [], [doc], [entity], [task])

        serialized = json.dumps(result["bundle"])
        assert "555-123-4567" not in serialized
        assert "555-987-6543" not in serialized
        assert "A1234567" not in serialized or "[MRN-REDACTED]" in serialized
        assert result["redaction_count"] > 0

    def test_hc_fhir_081_display_name_is_redacted(self):
        result = build_fhir_bundle(
            "Call me at 555-111-2222", [], [], [], [], [],
        )
        [patient] = [
            e["resource"] for e in result["bundle"]["entry"]
            if e["resource"]["resourceType"] == "Patient"
        ]
        assert "555-111-2222" not in patient["name"][0]["text"]
        assert result["redaction_count"] > 0

    def test_hc_fhir_082_unknown_analyte_unit_and_dosage_unit_redacted(self):
        """Finding 3 regression: for an unknown analyte,
        modules/normalize.py falls back to the cleaned raw document text as
        analyte_canonical (not a controlled vocabulary term), and both
        Observation.valueQuantity.unit and MedicationStatement's dosage
        unit are verbatim extraction-derived free text. All three must be
        redacted like any other narrative field before leaving the device.
        """
        obs = _obs(
            id="obs-1",
            analyte_canonical="call me at 555-222-3333",
            unit="see 555-222-3333",
        )
        med = _med(id="med-1", dosage_unit="555-222-3333 units")
        result = build_fhir_bundle("Jane Doe", [obs], [med], [], [], [])

        serialized = json.dumps(result["bundle"])
        assert "555-222-3333" not in serialized
        assert result["redaction_count"] > 0

        [observation] = [
            e["resource"] for e in result["bundle"]["entry"]
            if e["resource"]["resourceType"] == "Observation"
        ]
        assert "555-222-3333" not in observation["code"]["text"]
        assert "555-222-3333" not in observation["valueQuantity"]["unit"]

        [medication] = [
            e["resource"] for e in result["bundle"]["entry"]
            if e["resource"]["resourceType"] == "MedicationStatement"
        ]
        assert "555-222-3333" not in medication["dosage"][0]["text"]


class TestResourceCounts:
    def test_hc_fhir_090_resource_counts_reflect_included_resources(self):
        result = build_fhir_bundle("Jane Doe", [_obs()], [_med()], [], [], [])
        assert result["resource_counts"]["Patient"] == 1
        assert result["resource_counts"]["Observation"] == 1
        assert result["resource_counts"]["MedicationStatement"] == 1
        assert "Condition" not in result["resource_counts"]


# ---------------------------------------------------------------------------
# API route tests
# ---------------------------------------------------------------------------


class _Scalars:
    def __init__(self, items):
        self.items = items

    def all(self):
        return self.items


class _Result:
    def __init__(self, one=None, items=None):
        self.one = one
        self.items = items or []

    def scalar_one_or_none(self):
        return self.one

    def scalars(self):
        return _Scalars(self.items)


def _fake_profile(profile_id: str, display_name: str = "Jane Doe"):
    return type("Profile", (), {"id": profile_id, "display_name": display_name})()


@pytest.mark.asyncio
class TestFhirExportApi:
    async def test_hc_fhir_100_confirm_false_returns_400(self):
        from api.export import FhirExportRequest, generate_fhir_export
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await generate_fhir_export(
                FhirExportRequest(confirm=False),
                _session(), AsyncMock(), AsyncMock(),
            )
        assert exc.value.status_code == 400
        assert "confirm=true" in exc.value.detail

    async def test_hc_fhir_101_generate_returns_bundle_summary_and_audits(self, monkeypatch):
        from api.export import FhirExportRequest, generate_fhir_export

        profile = _fake_profile("test-profile")
        profile_db = AsyncMock()
        profile_db.execute.side_effect = [
            _Result(items=[]),  # observations
            _Result(items=[]),  # medications
            _Result(items=[]),  # documents
            _Result(items=[]),  # (documents categories, none needed)
            _Result(items=[]),  # entities
            _Result(items=[]),  # care tasks
        ]
        master_db = AsyncMock()
        master_db.execute.return_value = _Result(one=profile)
        audit = AsyncMock()
        monkeypatch.setattr("api.export.log_export_event", audit)

        response = await generate_fhir_export(
            FhirExportRequest(confirm=True),
            _session("test-profile"), profile_db, master_db,
        )
        assert response.profile_id == "test-profile"
        assert response.resource_counts["Patient"] == 1
        audit.assert_awaited_once()
        assert audit.await_args.kwargs["export_type"] == "fhir_r4"

    async def test_hc_fhir_102_download_happy_path(self, monkeypatch):
        from api.export import _fhir_store, download_fhir_export

        export_id = str(uuid.uuid4())
        _fhir_store[export_id] = {
            "profile_id": "test-profile",
            "bundle": {"resourceType": "Bundle", "type": "collection", "entry": []},
        }
        master_db = AsyncMock()
        audit = AsyncMock()
        monkeypatch.setattr("api.export.log_export_event", audit)

        response = await download_fhir_export(export_id, _session("test-profile"), master_db)
        assert response.media_type == "application/fhir+json"
        assert b"Bundle" in response.body
        audit.assert_awaited_once()
        assert audit.await_args.kwargs["export_type"] == "fhir_r4_download"
        del _fhir_store[export_id]

    async def test_hc_fhir_103_download_unknown_id_404(self):
        from api.export import download_fhir_export
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await download_fhir_export(str(uuid.uuid4()), _session("test-profile"), AsyncMock())
        assert exc.value.status_code == 404

    async def test_hc_fhir_104_download_cross_profile_403(self):
        from api.export import _fhir_store, download_fhir_export
        from fastapi import HTTPException

        export_id = str(uuid.uuid4())
        _fhir_store[export_id] = {
            "profile_id": "owner-profile",
            "bundle": {"resourceType": "Bundle"},
        }
        try:
            with pytest.raises(HTTPException) as exc:
                await download_fhir_export(
                    export_id, _session("other-profile"), AsyncMock(),
                )
            assert exc.value.status_code == 403
        finally:
            del _fhir_store[export_id]

    async def test_hc_fhir_105_include_flags_exclude_fetches_and_resources(self, monkeypatch):
        from api.export import FhirExportRequest, generate_fhir_export

        profile = _fake_profile("test-profile")
        profile_db = AsyncMock()
        # Only care_tasks fetch expected, since every other include_* is False.
        profile_db.execute.side_effect = [_Result(items=[])]
        master_db = AsyncMock()
        master_db.execute.return_value = _Result(one=profile)
        audit = AsyncMock()
        monkeypatch.setattr("api.export.log_export_event", audit)

        response = await generate_fhir_export(
            FhirExportRequest(
                confirm=True,
                include_observations=False,
                include_medications=False,
                include_documents=False,
                include_conditions=False,
                include_encounters=False,
                include_reports=False,
                include_care_plan=True,
            ),
            _session("test-profile"), profile_db, master_db,
        )
        assert "Observation" not in response.resource_counts
        assert "MedicationStatement" not in response.resource_counts
        assert "DocumentReference" not in response.resource_counts
