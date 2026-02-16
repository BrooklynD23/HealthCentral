"""
Apple Health XML importer.

Parses Apple Health export.xml files.
Uses defusedxml for safe XML parsing (DD-8: prevents XXE).
"""

import logging
from datetime import datetime
from typing import Optional

from .base import BaseImporter, ImportResult, ImportedObservation, ImportError

logger = logging.getLogger(__name__)

# Map Apple Health type identifiers to canonical analyte names
TYPE_MAP = {
    "HKQuantityTypeIdentifierBloodGlucose": "blood_glucose",
    "HKQuantityTypeIdentifierBodyMass": "body_mass",
    "HKQuantityTypeIdentifierBodyMassIndex": "bmi",
    "HKQuantityTypeIdentifierHeartRate": "heart_rate",
    "HKQuantityTypeIdentifierBloodPressureSystolic": "blood_pressure_systolic",
    "HKQuantityTypeIdentifierBloodPressureDiastolic": "blood_pressure_diastolic",
    "HKQuantityTypeIdentifierOxygenSaturation": "oxygen_saturation",
    "HKQuantityTypeIdentifierBodyTemperature": "body_temperature",
    "HKQuantityTypeIdentifierRespiratoryRate": "respiratory_rate",
    "HKQuantityTypeIdentifierLeanBodyMass": "lean_body_mass",
    "HKQuantityTypeIdentifierBodyFatPercentage": "body_fat_percentage",
}


def _parse_apple_date(date_str: str) -> Optional[datetime]:
    """Parse Apple Health date format: '2024-01-15 08:30:00 -0500'."""
    try:
        # Strip timezone offset for simplicity (store as naive UTC-ish)
        parts = date_str.rsplit(" ", 1)
        return datetime.strptime(parts[0], "%Y-%m-%d %H:%M:%S")
    except (ValueError, IndexError):
        return None


class AppleHealthImporter(BaseImporter):
    source_name = "apple_health"
    supported_extensions = ["xml"]

    def parse(self, file_bytes: bytes, filename: str) -> ImportResult:
        try:
            import defusedxml.ElementTree as ET
        except ImportError:
            import xml.etree.ElementTree as ET
            logger.warning("defusedxml not available, falling back to stdlib xml (less safe)")

        try:
            root = ET.fromstring(file_bytes)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML: {e}")

        observations = []
        errors = []
        row_idx = 0

        for record in root.iter("Record"):
            row_idx += 1
            if row_idx > self.max_rows:
                errors.append(ImportError(
                    row=row_idx, field="", message=f"Row limit {self.max_rows} exceeded"
                ))
                break

            record_type = record.get("type", "")
            analyte_raw = TYPE_MAP.get(record_type, record_type)

            try:
                value_str = record.get("value", "")
                value = float(value_str) if value_str else None
            except ValueError:
                errors.append(ImportError(
                    row=row_idx, field="value",
                    message=f"Non-numeric value: {record.get('value')}",
                ))
                continue

            collected_at = _parse_apple_date(record.get("startDate", ""))
            unit = record.get("unit", "")

            observations.append(ImportedObservation(
                analyte_raw=analyte_raw,
                value=value,
                unit=unit,
                collected_at=collected_at,
            ))

        return ImportResult(
            observations=observations,
            source_metadata={
                "source": "apple_health",
                "record_count": row_idx,
                "filename": filename,
            },
            errors=errors,
        )
