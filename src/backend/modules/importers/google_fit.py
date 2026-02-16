"""
Google Fit JSON importer.

Parses Google Fit Takeout JSON exports.
"""

import json
import logging
from datetime import datetime
from typing import Optional

from .base import BaseImporter, ImportResult, ImportedObservation, ImportError

logger = logging.getLogger(__name__)

# Map Google Fit data type names to canonical analyte names
TYPE_MAP = {
    "com.google.blood_glucose": "blood_glucose",
    "com.google.blood_pressure": "blood_pressure",
    "com.google.body.fat.percentage": "body_fat_percentage",
    "com.google.body.temperature": "body_temperature",
    "com.google.heart_rate.bpm": "heart_rate",
    "com.google.oxygen_saturation": "oxygen_saturation",
    "com.google.weight": "body_mass",
}


def _parse_timestamp_nanos(nanos: str) -> Optional[datetime]:
    """Parse nanosecond timestamp from Google Fit."""
    try:
        ts = int(nanos) / 1_000_000_000
        return datetime.utcfromtimestamp(ts)
    except (ValueError, OverflowError):
        return None


class GoogleFitImporter(BaseImporter):
    source_name = "google_fit"
    supported_extensions = ["json"]

    def parse(self, file_bytes: bytes, filename: str) -> ImportResult:
        try:
            data = json.loads(file_bytes)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")

        # Google Fit exports can be a single object or array
        if isinstance(data, dict):
            data_points = data.get("Data Points", data.get("dataPoints", []))
        elif isinstance(data, list):
            data_points = data
        else:
            raise ValueError("Expected JSON object or array")

        observations = []
        errors = []
        row_idx = 0

        for point in data_points:
            row_idx += 1
            if row_idx > self.max_rows:
                errors.append(ImportError(
                    row=row_idx, field="", message=f"Row limit {self.max_rows} exceeded"
                ))
                break

            data_type = point.get("dataTypeName", point.get("originDataSourceId", ""))
            analyte_raw = TYPE_MAP.get(data_type, data_type)

            # Extract value from fitValue array
            fit_values = point.get("fitValue", point.get("value", []))
            value = None
            if isinstance(fit_values, list) and fit_values:
                val_entry = fit_values[0]
                if isinstance(val_entry, dict):
                    value = val_entry.get("value", {}).get("fpVal")
                    if value is None:
                        value = val_entry.get("fpVal")
                elif isinstance(val_entry, (int, float)):
                    value = float(val_entry)

            if value is None:
                try:
                    value = float(point.get("value", "")) if point.get("value") else None
                except (ValueError, TypeError):
                    pass

            # Parse timestamp
            start_time = point.get("startTimeNanos", point.get("startTime", ""))
            if isinstance(start_time, str) and start_time.isdigit():
                collected_at = _parse_timestamp_nanos(start_time)
            elif isinstance(start_time, str):
                try:
                    collected_at = datetime.fromisoformat(start_time.replace("Z", "+00:00")).replace(tzinfo=None)
                except ValueError:
                    collected_at = None
            else:
                collected_at = None

            if value is not None:
                observations.append(ImportedObservation(
                    analyte_raw=analyte_raw,
                    value=value,
                    collected_at=collected_at,
                ))
            else:
                errors.append(ImportError(
                    row=row_idx, field="value",
                    message=f"No numeric value found in data point",
                ))

        return ImportResult(
            observations=observations,
            source_metadata={
                "source": "google_fit",
                "record_count": row_idx,
                "filename": filename,
            },
            errors=errors,
        )
