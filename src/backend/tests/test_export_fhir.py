"""Tests for FHIR R4 export models and mapping."""

import json
import pytest
from datetime import datetime
from models.fhir_resources import (
    FHIRPatient,
    FHIRObservation,
    FHIRBundle,
    map_observation_to_fhir,
    create_fhir_bundle,
    validate_fhir_bundle,
)


class TestFHIRPatient:
    def test_minimal_patient(self):
        patient = FHIRPatient(id="test-123", display_name="John Doe")
        data = patient.model_dump(by_alias=True, exclude_none=True)
        assert data["resourceType"] == "Patient"
        assert data["id"] == "test-123"
        assert data["name"][0]["text"] == "John Doe"

    def test_absent_fields_have_extension(self):
        patient = FHIRPatient(id="test-123", display_name="Jane Doe")
        data = patient.model_dump(by_alias=True, exclude_none=True)
        assert "_birthDate" in data
        assert data["_birthDate"]["extension"][0]["url"] == (
            "http://hl7.org/fhir/StructureDefinition/data-absent-reason"
        )


class TestFHIRObservation:
    def test_observation_mapping(self):
        obs = {
            "id": "obs-001",
            "analyte_canonical": "glucose",
            "value": 95.0,
            "unit": "mg/dL",
            "ref_low": 70.0,
            "ref_high": 100.0,
            "collected_at": datetime(2024, 1, 15, 10, 30),
            "is_abnormal": False,
        }
        fhir_obs = map_observation_to_fhir(obs, patient_ref="Patient/test-123")
        data = fhir_obs.model_dump(by_alias=True, exclude_none=True)
        assert data["resourceType"] == "Observation"
        assert data["status"] == "final"
        assert data["valueQuantity"]["value"] == 95.0
        assert data["valueQuantity"]["unit"] == "mg/dL"
        assert len(data["referenceRange"]) == 1

    def test_observation_with_loinc(self):
        obs = {
            "id": "obs-002",
            "analyte_canonical": "glucose",
            "value": 95.0,
            "unit": "mg/dL",
            "collected_at": datetime(2024, 1, 15),
        }
        loinc_map = {"glucose": ["2345-7"]}
        fhir_obs = map_observation_to_fhir(
            obs, patient_ref="Patient/p1", loinc_map=loinc_map
        )
        data = fhir_obs.model_dump(by_alias=True, exclude_none=True)
        codings = data["code"]["coding"]
        assert any(c["system"] == "http://loinc.org" for c in codings)
        assert any(c["code"] == "2345-7" for c in codings)

    def test_observation_without_value_uses_text(self):
        obs = {
            "id": "obs-003",
            "analyte_canonical": "urinalysis_color",
            "value": None,
            "value_text": "Yellow",
            "collected_at": datetime(2024, 1, 15),
        }
        fhir_obs = map_observation_to_fhir(obs, patient_ref="Patient/p1")
        data = fhir_obs.model_dump(by_alias=True, exclude_none=True)
        assert "valueString" in data
        assert data["valueString"] == "Yellow"


class TestFHIRBundle:
    def test_bundle_structure(self):
        patient = FHIRPatient(id="p1", display_name="Test User")
        obs = {
            "id": "obs-001",
            "analyte_canonical": "glucose",
            "value": 95.0,
            "unit": "mg/dL",
            "collected_at": datetime(2024, 1, 15),
        }
        fhir_obs = map_observation_to_fhir(obs, patient_ref="Patient/p1")
        bundle = create_fhir_bundle(patient, [fhir_obs])
        data = bundle.model_dump(by_alias=True, exclude_none=True)
        assert data["resourceType"] == "Bundle"
        assert data["type"] == "collection"
        assert len(data["entry"]) == 2  # patient + 1 observation

    def test_bundle_json_serializable(self):
        patient = FHIRPatient(id="p1", display_name="Test")
        bundle = create_fhir_bundle(patient, [])
        data = bundle.model_dump(by_alias=True, exclude_none=True)
        json_str = json.dumps(data)
        assert '"resourceType": "Bundle"' in json_str


class TestFHIRValidationHooks:
    def test_validation_passes_for_generated_bundle(self):
        patient = FHIRPatient(id="p1", display_name="Valid Patient")
        obs = {
            "id": "obs-1",
            "analyte_canonical": "glucose",
            "value": 95.0,
            "unit": "mg/dL",
            "collected_at": datetime(2024, 1, 15),
        }
        fhir_obs = map_observation_to_fhir(obs, patient_ref="Patient/p1")
        bundle = create_fhir_bundle(patient, [fhir_obs])
        issues = validate_fhir_bundle(bundle.model_dump(by_alias=True, exclude_none=True))
        assert issues == []

    def test_validation_reports_missing_required_fields(self):
        invalid_bundle = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {"resource": {"resourceType": "Observation", "id": "obs-1"}}
            ],
        }
        issues = validate_fhir_bundle(invalid_bundle)
        diagnostics = {issue["diagnostics"] for issue in issues}
        assert "Observation.status is required" in diagnostics
        assert "Observation.code is required" in diagnostics
