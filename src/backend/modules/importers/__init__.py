"""
External source importers.

Pluggable parsers for Apple Health, Google Fit, Quest, LabCorp, HL7 v2, and generic CSV.
"""

from .base import BaseImporter, ImportResult, ImportedObservation, ImportError as ImportRowError
from .apple_health import AppleHealthImporter
from .google_fit import GoogleFitImporter
from .generic_csv import GenericCSVImporter
from .quest import QuestImporter
from .labcorp import LabCorpImporter
from .hl7v2 import HL7v2Importer

IMPORTER_REGISTRY: dict[str, type[BaseImporter]] = {
    "apple_health": AppleHealthImporter,
    "google_fit": GoogleFitImporter,
    "generic_csv": GenericCSVImporter,
    "quest": QuestImporter,
    "labcorp": LabCorpImporter,
    "hl7v2": HL7v2Importer,
}

def get_importer(source_type: str) -> BaseImporter:
    """Get an importer instance by source type."""
    cls = IMPORTER_REGISTRY.get(source_type)
    if cls is None:
        raise ValueError(f"Unknown source type: {source_type}. Supported: {list(IMPORTER_REGISTRY.keys())}")
    return cls()

__all__ = [
    "BaseImporter", "ImportResult", "ImportedObservation", "ImportRowError",
    "IMPORTER_REGISTRY", "get_importer",
]
