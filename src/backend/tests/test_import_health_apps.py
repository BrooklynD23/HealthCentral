"""Tests for Apple Health and Google Fit importers."""

import builtins
import pytest
from datetime import datetime
from modules.importers.base import ImportResult
from modules.importers.apple_health import AppleHealthImporter


SAMPLE_APPLE_HEALTH_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData locale="en_US">
  <Record type="HKQuantityTypeIdentifierBloodGlucose"
          sourceName="Health" unit="mg/dL" value="95"
          startDate="2024-01-15 08:30:00 -0500"
          endDate="2024-01-15 08:30:00 -0500"/>
  <Record type="HKQuantityTypeIdentifierBodyMass"
          sourceName="Health" unit="lb" value="175"
          startDate="2024-01-15 07:00:00 -0500"
          endDate="2024-01-15 07:00:00 -0500"/>
  <Record type="HKQuantityTypeIdentifierHeartRate"
          sourceName="Apple Watch" unit="count/min" value="72"
          startDate="2024-01-15 12:00:00 -0500"
          endDate="2024-01-15 12:00:00 -0500"/>
</HealthData>
"""

SAMPLE_APPLE_HEALTH_CSV = b"""type,sourceName,unit,value,startDate,endDate
HKQuantityTypeIdentifierBloodGlucose,Health,mg/dL,98,2024-01-15 08:30:00 -0500,2024-01-15 08:30:00 -0500
HKQuantityTypeIdentifierHeartRate,Apple Watch,count/min,72,2024-01-15 12:00:00 -0500,2024-01-15 12:00:00 -0500
"""


class TestAppleHealthImporter:
    def setup_method(self):
        self.importer = AppleHealthImporter()

    def test_parse_valid_xml(self):
        result = self.importer.parse(SAMPLE_APPLE_HEALTH_XML, "export.xml")
        assert isinstance(result, ImportResult)
        assert len(result.observations) == 3
        assert len(result.errors) == 0

    def test_observation_values_mapped(self):
        result = self.importer.parse(SAMPLE_APPLE_HEALTH_XML, "export.xml")
        glucose = next(o for o in result.observations if "glucose" in o.analyte_raw.lower())
        assert glucose.value == 95.0
        assert glucose.unit == "mg/dL"

    def test_dates_parsed(self):
        result = self.importer.parse(SAMPLE_APPLE_HEALTH_XML, "export.xml")
        for obs in result.observations:
            assert obs.collected_at is not None
            assert isinstance(obs.collected_at, datetime)

    def test_source_metadata(self):
        result = self.importer.parse(SAMPLE_APPLE_HEALTH_XML, "export.xml")
        assert result.source_metadata["source"] == "apple_health"
        assert "record_count" in result.source_metadata

    def test_empty_xml_returns_empty(self):
        xml = b'<?xml version="1.0"?><HealthData></HealthData>'
        result = self.importer.parse(xml, "empty.xml")
        assert len(result.observations) == 0

    def test_malformed_xml_raises(self):
        with pytest.raises(ValueError, match="XML"):
            self.importer.parse(b"not xml at all", "bad.xml")

    def test_missing_defusedxml_fails_closed(self, monkeypatch):
        real_import = builtins.__import__

        def _blocked_import(name, *args, **kwargs):
            if name.startswith("defusedxml"):
                raise ImportError("No module named defusedxml")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _blocked_import)

        with pytest.raises(ValueError, match="defusedxml is required"):
            self.importer.parse(SAMPLE_APPLE_HEALTH_XML, "export.xml")

    def test_supported_extensions(self):
        assert "xml" in self.importer.supported_extensions
        assert "csv" in self.importer.supported_extensions

    def test_parse_csv_variant(self):
        result = self.importer.parse(SAMPLE_APPLE_HEALTH_CSV, "export.csv")
        assert len(result.observations) == 2
        assert result.source_metadata["source"] == "apple_health_csv"
        assert result.observations[0].analyte_raw == "blood_glucose"

    def test_csv_variant_records_row_errors(self):
        bad_csv = (
            b"type,unit,value,startDate\n"
            b"HKQuantityTypeIdentifierBloodGlucose,mg/dL,abc,2024-01-15\n"
        )
        result = self.importer.parse(bad_csv, "bad.csv")
        assert len(result.observations) == 0
        assert len(result.errors) == 1
        assert result.errors[0].field == "value"
