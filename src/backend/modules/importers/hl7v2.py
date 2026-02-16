"""
HL7 v2 message importer.

Parses pipe-delimited HL7 v2 messages, extracting OBX segments.
Enforces segment limit of 10,000 and field length limit of 10KB.
"""

import logging
from datetime import datetime
from typing import Optional

from .base import BaseImporter, ImportResult, ImportedObservation, ImportError

logger = logging.getLogger(__name__)

MAX_SEGMENTS = 10_000
MAX_FIELD_LENGTH = 10 * 1024  # 10KB


def _parse_hl7_date(date_str: str) -> Optional[datetime]:
    """Parse HL7 date format: YYYYMMDDHHMMSS or YYYYMMDD."""
    if not date_str:
        return None
    try:
        if len(date_str) >= 14:
            return datetime.strptime(date_str[:14], "%Y%m%d%H%M%S")
        elif len(date_str) >= 8:
            return datetime.strptime(date_str[:8], "%Y%m%d")
    except ValueError:
        pass
    return None


class HL7v2Importer(BaseImporter):
    source_name = "hl7v2"
    supported_extensions = ["hl7"]

    def parse(self, file_bytes: bytes, filename: str) -> ImportResult:
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = file_bytes.decode("latin-1")
            except UnicodeDecodeError:
                raise ValueError("Unable to decode HL7 file")

        # Split into segments
        segments = text.replace("\r\n", "\r").replace("\n", "\r").split("\r")
        segments = [s.strip() for s in segments if s.strip()]

        if not segments or not segments[0].startswith("MSH"):
            raise ValueError("Invalid HL7 v2 message: missing MSH segment")

        observations = []
        errors = []
        segment_count = 0

        for segment in segments:
            segment_count += 1
            if segment_count > MAX_SEGMENTS:
                errors.append(ImportError(
                    row=segment_count, field="",
                    message=f"Segment limit {MAX_SEGMENTS} exceeded",
                ))
                break

            if len(segment) > MAX_FIELD_LENGTH:
                errors.append(ImportError(
                    row=segment_count, field="segment",
                    message=f"Segment exceeds {MAX_FIELD_LENGTH} bytes",
                ))
                continue

            if not segment.startswith("OBX"):
                continue

            fields = segment.split("|")
            # OBX structure: OBX|SetID|ValueType|ObsID|SubID|Value|Units|RefRange|AbnFlag|...

            if len(fields) < 6:
                errors.append(ImportError(
                    row=segment_count, field="OBX",
                    message="OBX segment has fewer than 6 fields",
                ))
                continue

            # OBX-3: Observation Identifier (analyte)
            obs_id_field = fields[3] if len(fields) > 3 else ""
            # Parse component: code^display^system
            obs_components = obs_id_field.split("^")
            analyte_raw = obs_components[1] if len(obs_components) > 1 else obs_components[0]
            if not analyte_raw:
                analyte_raw = obs_id_field

            # OBX-2: Value Type
            value_type = fields[2] if len(fields) > 2 else ""

            # OBX-5: Observation Value
            value_str = fields[5] if len(fields) > 5 else ""
            value = None
            value_text = None
            if value_type in ("NM", "SN"):
                try:
                    value = float(value_str)
                except ValueError:
                    value_text = value_str
            else:
                value_text = value_str

            # OBX-6: Units
            unit_field = fields[6] if len(fields) > 6 else ""
            unit = unit_field.split("^")[0] if unit_field else None

            # OBX-7: Reference Range
            ref_range = fields[7] if len(fields) > 7 else ""
            ref_low = None
            ref_high = None
            if ref_range and "-" in ref_range:
                parts = ref_range.split("-", 1)
                try:
                    ref_low = float(parts[0].strip())
                    ref_high = float(parts[1].strip())
                except ValueError:
                    pass

            # OBX-8: Abnormal flags
            flag = fields[8].strip() if len(fields) > 8 else None

            # OBX-14: Date/Time of Observation
            obs_date_str = fields[14] if len(fields) > 14 else ""
            collected_at = _parse_hl7_date(obs_date_str)

            observations.append(ImportedObservation(
                analyte_raw=analyte_raw,
                value=value,
                value_text=value_text,
                unit=unit,
                collected_at=collected_at,
                ref_low=ref_low,
                ref_high=ref_high,
                flag=flag,
            ))

        return ImportResult(
            observations=observations,
            source_metadata={
                "source": "hl7v2",
                "segment_count": segment_count,
                "filename": filename,
            },
            errors=errors,
        )
