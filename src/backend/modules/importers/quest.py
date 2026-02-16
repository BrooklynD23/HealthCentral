"""
Quest Diagnostics CSV importer.

Extends GenericCSVImporter with Quest-specific column names.
"""

from .generic_csv import GenericCSVImporter, COLUMN_ALIASES


class QuestImporter(GenericCSVImporter):
    source_name = "quest"
    supported_extensions = ["csv"]
    column_aliases = {
        **COLUMN_ALIASES,
        "analyte": ["Test Name", "Test", "Component"] + COLUMN_ALIASES["analyte"],
        "value": ["Result", "Result Value", "Numeric Result"] + COLUMN_ALIASES["value"],
        "unit": ["Units", "Unit of Measure"] + COLUMN_ALIASES["unit"],
        "reference_range": ["Reference Range", "Ref Range", "Normal Range"] + COLUMN_ALIASES["reference_range"],
        "flag": ["Abnormal Flag", "Flag", "Status"] + COLUMN_ALIASES["flag"],
        "date": ["Specimen Date", "Collection Date", "Draw Date"] + COLUMN_ALIASES["date"],
    }
