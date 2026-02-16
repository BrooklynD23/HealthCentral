"""
Apple Health XML importer.

Parses Apple Health export.xml files.
Uses defusedxml for safe XML parsing (DD-8: prevents XXE).
"""

import csv
import io
import logging
from datetime import datetime
from typing import Optional

from .base import (
    BaseImporter,
    ImportResult,
    ImportedObservation,
    ImportError as ImportRowError,
)

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
    """Parse common Apple Health datetime formats."""
    if not date_str:
        return None

    candidates: list[str] = []
    stripped = date_str.strip()
    candidates.append(stripped)

    # Apple XML often uses "YYYY-mm-dd HH:MM:SS -0500"
    parts = stripped.rsplit(" ", 1)
    if len(parts) == 2 and parts[1].startswith(("+", "-")):
        candidates.append(parts[0])

    for candidate in candidates:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(candidate, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(candidate.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            continue
    return None


class AppleHealthImporter(BaseImporter):
    source_name = "apple_health"
    supported_extensions = ["xml", "csv"]

    def parse(self, file_bytes: bytes, filename: str) -> ImportResult:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "xml"
        if ext == "csv":
            return self._parse_csv(file_bytes, filename)
        return self._parse_xml(file_bytes, filename)

    def _parse_xml(self, file_bytes: bytes, filename: str) -> ImportResult:
        try:
            import defusedxml.ElementTree as ET
        except ImportError as e:
            raise ValueError(
                "defusedxml is required for Apple Health XML imports"
            ) from e

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
                errors.append(ImportRowError(
                    row=row_idx, field="", message=f"Row limit {self.max_rows} exceeded"
                ))
                break

            record_type = record.get("type", "")
            analyte_raw = TYPE_MAP.get(record_type, record_type)

            try:
                value_str = record.get("value", "")
                value = float(value_str) if value_str else None
            except ValueError:
                errors.append(ImportRowError(
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

    def _parse_csv(self, file_bytes: bytes, filename: str) -> ImportResult:
        try:
            text = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = file_bytes.decode("latin-1")

        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            return ImportResult(
                source_metadata={"source": "apple_health_csv", "filename": filename}
            )

        observations = []
        errors = []
        row_idx = 0

        for row in reader:
            row_idx += 1
            if row_idx > self.max_rows:
                errors.append(ImportRowError(
                    row=row_idx,
                    field="",
                    message=f"Row limit {self.max_rows} exceeded",
                ))
                break

            record_type = (
                row.get("type")
                or row.get("Type")
                or row.get("record_type")
                or row.get("Record Type")
                or row.get("analyte")
                or row.get("Analyte")
                or ""
            ).strip()
            if not record_type:
                continue

            analyte_raw = TYPE_MAP.get(record_type, record_type)
            value_raw = (
                row.get("value")
                or row.get("Value")
                or row.get("result")
                or row.get("Result")
                or ""
            ).strip()
            value: Optional[float]
            if value_raw == "":
                value = None
            else:
                try:
                    value = float(value_raw)
                except ValueError:
                    errors.append(ImportRowError(
                        row=row_idx,
                        field="value",
                        message=f"Non-numeric value: {value_raw}",
                    ))
                    continue

            start_raw = (
                row.get("startDate")
                or row.get("start_date")
                or row.get("date")
                or row.get("Date")
                or row.get("timestamp")
                or ""
            )
            unit = (
                row.get("unit")
                or row.get("Unit")
                or row.get("units")
                or row.get("Units")
                or ""
            ).strip()

            observations.append(
                ImportedObservation(
                    analyte_raw=analyte_raw,
                    value=value,
                    unit=unit,
                    collected_at=_parse_apple_date(start_raw),
                )
            )

        return ImportResult(
            observations=observations,
            source_metadata={
                "source": "apple_health_csv",
                "record_count": row_idx,
                "filename": filename,
            },
            errors=errors,
        )
