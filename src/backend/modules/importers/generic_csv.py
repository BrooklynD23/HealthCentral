"""
Generic CSV importer.

Parses CSV files with configurable column mapping via header detection.
Enforces max_rows and max_columns limits.
"""

import csv
import io
import logging
from datetime import datetime
from typing import Optional

from .base import BaseImporter, ImportResult, ImportedObservation, ImportError

logger = logging.getLogger(__name__)

# Common column name aliases
COLUMN_ALIASES = {
    "analyte": ["analyte", "test", "test name", "test_name", "analyte_name", "component", "lab test"],
    "value": ["value", "result", "result value", "result_value", "numeric result"],
    "unit": ["unit", "units", "unit of measure", "uom"],
    "date": ["date", "collected_at", "collection_date", "test_date", "specimen date", "draw date"],
    "ref_low": ["ref_low", "reference low", "low", "normal low", "range low"],
    "ref_high": ["ref_high", "reference high", "high", "normal high", "range high"],
    "flag": ["flag", "abnormal flag", "status", "abnormal", "interpretation"],
    "reference_range": ["reference range", "reference_range", "ref range", "normal range", "range"],
}


def _detect_column(headers: list[str], aliases: list[str]) -> Optional[int]:
    """Find column index by matching against aliases (case-insensitive)."""
    lower_headers = [h.lower().strip() for h in headers]
    for alias in aliases:
        if alias.lower() in lower_headers:
            return lower_headers.index(alias.lower())
    return None


def _parse_date(value: str) -> Optional[datetime]:
    """Try multiple date formats."""
    formats = [
        "%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y",
        "%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M",
        "%d-%b-%Y", "%B %d, %Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


def _parse_reference_range(range_str: str) -> tuple[Optional[float], Optional[float]]:
    """Parse a reference range string like '70-100' or '< 200'."""
    if not range_str:
        return None, None
    range_str = range_str.strip()
    if "-" in range_str and not range_str.startswith("-"):
        parts = range_str.split("-", 1)
        try:
            return float(parts[0].strip()), float(parts[1].strip())
        except ValueError:
            return None, None
    return None, None


class GenericCSVImporter(BaseImporter):
    source_name = "generic_csv"
    supported_extensions = ["csv"]
    column_aliases: dict[str, list[str]] = COLUMN_ALIASES

    def __init__(self):
        # Copy aliases per instance so subclasses/tests can customize safely.
        self.column_aliases = {
            field: list(aliases)
            for field, aliases in self.column_aliases.items()
        }

    def parse(self, file_bytes: bytes, filename: str) -> ImportResult:
        try:
            text = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                text = file_bytes.decode("latin-1")
            except UnicodeDecodeError:
                raise ValueError("Unable to decode CSV file (tried UTF-8 and Latin-1)")

        reader = csv.reader(io.StringIO(text))
        observations = []
        errors = []

        # Read and validate headers
        try:
            headers = next(reader)
        except StopIteration:
            return ImportResult(source_metadata={"source": self.source_name, "filename": filename})

        if len(headers) > self.max_columns:
            raise ValueError(
                f"Too many columns: {len(headers)} (max: {self.max_columns})"
            )

        # Detect column mappings
        aliases = self.column_aliases
        col_analyte = _detect_column(headers, aliases["analyte"])
        col_value = _detect_column(headers, aliases["value"])
        col_unit = _detect_column(headers, aliases["unit"])
        col_date = _detect_column(headers, aliases["date"])
        col_ref_low = _detect_column(headers, aliases["ref_low"])
        col_ref_high = _detect_column(headers, aliases["ref_high"])
        col_flag = _detect_column(headers, aliases["flag"])
        col_ref_range = _detect_column(headers, aliases["reference_range"])

        if col_analyte is None:
            raise ValueError(
                f"Could not detect analyte/test name column. Headers: {headers}"
            )

        row_idx = 0
        for row in reader:
            row_idx += 1
            if row_idx > self.max_rows:
                errors.append(ImportError(
                    row=row_idx, field="", message=f"Row limit {self.max_rows} exceeded"
                ))
                break

            if not row or all(c.strip() == "" for c in row):
                continue

            analyte_raw = row[col_analyte].strip() if col_analyte < len(row) else ""
            if not analyte_raw:
                continue

            # Parse value
            value = None
            value_text = None
            if col_value is not None and col_value < len(row):
                raw_val = row[col_value].strip()
                try:
                    value = float(raw_val)
                except ValueError:
                    value_text = raw_val if raw_val else None

            # Parse unit
            unit = row[col_unit].strip() if col_unit is not None and col_unit < len(row) else None

            # Parse date
            collected_at = None
            if col_date is not None and col_date < len(row):
                collected_at = _parse_date(row[col_date])

            # Parse reference range
            ref_low = None
            ref_high = None
            if col_ref_low is not None and col_ref_low < len(row):
                try:
                    ref_low = float(row[col_ref_low].strip())
                except ValueError:
                    pass
            if col_ref_high is not None and col_ref_high < len(row):
                try:
                    ref_high = float(row[col_ref_high].strip())
                except ValueError:
                    pass
            if ref_low is None and ref_high is None and col_ref_range is not None and col_ref_range < len(row):
                ref_low, ref_high = _parse_reference_range(row[col_ref_range])

            # Parse flag
            flag = row[col_flag].strip() if col_flag is not None and col_flag < len(row) else None

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
                "source": self.source_name,
                "record_count": row_idx,
                "filename": filename,
                "columns_detected": {
                    k: v is not None
                    for k, v in {
                        "analyte": col_analyte, "value": col_value,
                        "unit": col_unit, "date": col_date,
                        "flag": col_flag,
                    }.items()
                },
            },
            errors=errors,
        )
