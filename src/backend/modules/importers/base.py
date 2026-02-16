"""
Base importer interface.

All external source parsers implement BaseImporter.
Design Decisions DD-2, DD-8: Synthetic Document provenance, security guardrails.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from core.config import settings


@dataclass
class ImportedObservation:
    """A single observation parsed from an external source."""
    analyte_raw: str
    value: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    collected_at: Optional[datetime] = None
    ref_low: Optional[float] = None
    ref_high: Optional[float] = None
    flag: Optional[str] = None


@dataclass
class ImportError:
    """A per-row parsing error."""
    row: int
    field: str
    message: str


@dataclass
class ImportResult:
    """Result of parsing an external file."""
    observations: list[ImportedObservation] = field(default_factory=list)
    source_metadata: dict = field(default_factory=dict)
    errors: list[ImportError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class BaseImporter(ABC):
    """Abstract base for all external source importers."""

    source_name: str = ""
    supported_extensions: list[str] = []

    # Security limits (DD-8)
    max_rows: int = 100_000
    max_columns: int = 50
    max_error_rate: float = 0.10  # Hard-fail above 10%

    def validate_file_size(self, file_bytes: bytes) -> None:
        """Check file size against config limit."""
        max_bytes = settings.max_import_file_size_mb * 1024 * 1024
        if len(file_bytes) > max_bytes:
            raise ValueError(
                f"File too large: {len(file_bytes) / 1024 / 1024:.1f}MB "
                f"(max: {settings.max_import_file_size_mb}MB)"
            )

    def validate_extension(self, filename: str) -> None:
        """Check file extension against allowed list."""
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext not in self.supported_extensions:
            raise ValueError(
                f"Unsupported extension '.{ext}' for {self.source_name}. "
                f"Supported: {self.supported_extensions}"
            )

    def check_error_rate(self, result: ImportResult) -> None:
        """Hard-fail if error rate exceeds threshold."""
        total = len(result.observations) + len(result.errors)
        if total > 0 and len(result.errors) / total > self.max_error_rate:
            raise ValueError(
                f"Error rate {len(result.errors)}/{total} ({len(result.errors)/total:.0%}) "
                f"exceeds maximum of {self.max_error_rate:.0%}"
            )

    @abstractmethod
    def parse(self, file_bytes: bytes, filename: str) -> ImportResult:
        """Parse an external file into observations."""
        ...

    def safe_parse(self, file_bytes: bytes, filename: str) -> ImportResult:
        """Parse with validation guardrails."""
        self.validate_file_size(file_bytes)
        self.validate_extension(filename)
        result = self.parse(file_bytes, filename)
        self.check_error_rate(result)
        return result
