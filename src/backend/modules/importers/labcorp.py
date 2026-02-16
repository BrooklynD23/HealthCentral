"""
LabCorp CSV importer.

Extends GenericCSVImporter with LabCorp-specific column names.
"""

from .generic_csv import GenericCSVImporter, COLUMN_ALIASES


class LabCorpImporter(GenericCSVImporter):
    source_name = "labcorp"
    supported_extensions = ["csv"]
    column_aliases = {
        **COLUMN_ALIASES,
        "analyte": ["Test", "Test Name", "Component"] + COLUMN_ALIASES["analyte"],
        "value": ["Result", "Value"] + COLUMN_ALIASES["value"],
        "reference_range": ["Reference Interval", "Reference Range", "Ref Range"] + COLUMN_ALIASES["reference_range"],
        "flag": ["Flag", "Abnormal"] + COLUMN_ALIASES["flag"],
        "date": ["Collection Date", "Specimen Date"] + COLUMN_ALIASES["date"],
        "unit": ["Units"] + COLUMN_ALIASES["unit"],
    }
