"""Tests for lab provider importers: Generic CSV, Quest, LabCorp, HL7v2, Google Fit."""

import pytest
from datetime import datetime
from modules.importers.base import ImportResult
from modules.importers.generic_csv import GenericCSVImporter
from modules.importers.quest import QuestImporter
from modules.importers.labcorp import LabCorpImporter
from modules.importers.hl7v2 import HL7v2Importer
from modules.importers.google_fit import GoogleFitImporter
from modules.importers import get_importer, IMPORTER_REGISTRY


# --- Generic CSV ---

SAMPLE_CSV = b"""Test Name,Result,Units,Reference Range,Flag,Date
Glucose,95,mg/dL,70-100,,2024-01-15
Hemoglobin A1c,6.5,%,4.0-5.6,H,2024-01-15
Cholesterol Total,210,mg/dL,< 200,H,2024-01-15
"""


class TestGenericCSVImporter:
    def setup_method(self):
        self.importer = GenericCSVImporter()

    def test_parse_valid_csv(self):
        result = self.importer.parse(SAMPLE_CSV, "labs.csv")
        assert isinstance(result, ImportResult)
        assert len(result.observations) == 3

    def test_column_mapping(self):
        result = self.importer.parse(SAMPLE_CSV, "labs.csv")
        glucose = result.observations[0]
        assert glucose.analyte_raw == "Glucose"
        assert glucose.value == 95.0
        assert glucose.unit == "mg/dL"

    def test_reference_range_parsed(self):
        result = self.importer.parse(SAMPLE_CSV, "labs.csv")
        glucose = result.observations[0]
        assert glucose.ref_low == 70.0
        assert glucose.ref_high == 100.0

    def test_date_parsed(self):
        result = self.importer.parse(SAMPLE_CSV, "labs.csv")
        assert result.observations[0].collected_at == datetime(2024, 1, 15)

    def test_empty_csv_returns_empty(self):
        result = self.importer.parse(b"Test Name,Result\n", "empty.csv")
        assert len(result.observations) == 0

    def test_missing_analyte_column_raises(self):
        with pytest.raises(ValueError, match="analyte"):
            self.importer.parse(b"Foo,Bar\n1,2\n", "bad.csv")


# --- Quest ---

class TestQuestImporter:
    def test_is_csv_importer(self):
        importer = QuestImporter()
        assert importer.source_name == "quest"
        assert "csv" in importer.supported_extensions

    def test_parse_standard_csv(self):
        result = QuestImporter().parse(SAMPLE_CSV, "quest_results.csv")
        assert len(result.observations) >= 1


# --- LabCorp ---

class TestLabCorpImporter:
    def test_is_csv_importer(self):
        importer = LabCorpImporter()
        assert importer.source_name == "labcorp"
        assert "csv" in importer.supported_extensions

    def test_parse_standard_csv(self):
        result = LabCorpImporter().parse(SAMPLE_CSV, "labcorp_results.csv")
        assert len(result.observations) >= 1


# --- HL7 v2 ---

SAMPLE_HL7 = b"""MSH|^~\\&|LAB|HOSPITAL|EMR|HOSPITAL|20240115||ORU^R01|12345|P|2.5
PID|1||12345||Doe^John
OBR|1||12345|CBC^Complete Blood Count
OBX|1|NM|2345-7^Glucose^LN||95|mg/dL|70-100|N|||F|||20240115083000
OBX|2|NM|4548-4^Hemoglobin A1c^LN||6.5|%|4.0-5.6|H|||F|||20240115083000
"""


class TestHL7v2Importer:
    def setup_method(self):
        self.importer = HL7v2Importer()

    def test_parse_valid_hl7(self):
        result = self.importer.parse(SAMPLE_HL7, "results.hl7")
        assert isinstance(result, ImportResult)
        assert len(result.observations) == 2

    def test_obx_values_extracted(self):
        result = self.importer.parse(SAMPLE_HL7, "results.hl7")
        glucose = result.observations[0]
        assert glucose.value == 95.0
        assert glucose.unit == "mg/dL"
        assert glucose.ref_low == 70.0
        assert glucose.ref_high == 100.0

    def test_analyte_name_from_obx3(self):
        result = self.importer.parse(SAMPLE_HL7, "results.hl7")
        assert "Glucose" in result.observations[0].analyte_raw

    def test_date_parsed_from_obx14(self):
        result = self.importer.parse(SAMPLE_HL7, "results.hl7")
        assert result.observations[0].collected_at == datetime(2024, 1, 15, 8, 30, 0)

    def test_invalid_hl7_raises(self):
        with pytest.raises(ValueError, match="MSH"):
            self.importer.parse(b"NOT|HL7|MESSAGE", "bad.hl7")

    def test_supported_extensions(self):
        assert "hl7" in self.importer.supported_extensions


# --- Google Fit ---

SAMPLE_GOOGLE_FIT_JSON = b"""[
  {
    "dataTypeName": "com.google.blood_glucose",
    "startTimeNanos": "1705305000000000000",
    "fitValue": [{"value": {"fpVal": 95.0}}]
  },
  {
    "dataTypeName": "com.google.heart_rate.bpm",
    "startTimeNanos": "1705315800000000000",
    "fitValue": [{"value": {"fpVal": 72.0}}]
  }
]"""


class TestGoogleFitImporter:
    def setup_method(self):
        self.importer = GoogleFitImporter()

    def test_parse_valid_json(self):
        result = self.importer.parse(SAMPLE_GOOGLE_FIT_JSON, "data.json")
        assert isinstance(result, ImportResult)
        assert len(result.observations) == 2

    def test_values_extracted(self):
        result = self.importer.parse(SAMPLE_GOOGLE_FIT_JSON, "data.json")
        glucose = next(o for o in result.observations if "glucose" in o.analyte_raw)
        assert glucose.value == 95.0

    def test_dates_parsed(self):
        result = self.importer.parse(SAMPLE_GOOGLE_FIT_JSON, "data.json")
        for obs in result.observations:
            assert obs.collected_at is not None

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="JSON"):
            self.importer.parse(b"not json", "bad.json")

    def test_supported_extensions(self):
        assert "json" in self.importer.supported_extensions


# --- Registry ---

class TestImporterRegistry:
    def test_all_importers_registered(self):
        assert "apple_health" in IMPORTER_REGISTRY
        assert "google_fit" in IMPORTER_REGISTRY
        assert "generic_csv" in IMPORTER_REGISTRY
        assert "quest" in IMPORTER_REGISTRY
        assert "labcorp" in IMPORTER_REGISTRY
        assert "hl7v2" in IMPORTER_REGISTRY

    def test_get_importer_valid(self):
        importer = get_importer("apple_health")
        assert importer.source_name == "apple_health"

    def test_get_importer_invalid_raises(self):
        with pytest.raises(ValueError, match="Unknown"):
            get_importer("nonexistent")
