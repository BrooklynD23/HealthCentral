"""
Verification module.

Handles:
- Verification data models
- Field validation utilities

Production verification is implemented in api/observations.py:verify_observation.
"""

from typing import Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class VerificationPayload:
    """Data for verification UI."""
    observation_id: str
    analyte_raw: str
    analyte_canonical: str
    value: Optional[float]
    value_text: Optional[str]
    unit: Optional[str]
    ref_low: Optional[float]
    ref_high: Optional[float]
    flag: Optional[str]
    collected_at: Optional[str]
    extraction_confidence: float
    extraction_method: str
    provenance_page: Optional[int]
    provenance_snippet: str
    user_verified: bool


@dataclass
class VerificationEdit:
    """User edit to an observation."""
    observation_id: str
    field_name: str
    old_value: str
    new_value: str
    edited_at: datetime


# Fields that can be edited during verification
EDITABLE_FIELDS = [
    "value",
    "value_text",
    "unit",
    "ref_low",
    "ref_high",
    "collected_at",
    "notes",
]


def validate_edit_value(value, field_name: str) -> tuple[bool, str]:
    """
    Validate a user-entered value for a verification edit.

    Args:
        value: Value to validate
        field_name: Field being edited

    Returns:
        Tuple of (is_valid, error_message)
    """
    if field_name not in EDITABLE_FIELDS:
        return False, f"Field not editable: {field_name}"

    if field_name in ("value", "ref_low", "ref_high"):
        try:
            float(value)
            return True, ""
        except (ValueError, TypeError):
            return False, "Must be a number"

    if field_name == "collected_at":
        if not isinstance(value, str) or not value.strip():
            return False, "Date is required"
        # Accept ISO format or common date formats
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y"):
            try:
                datetime.strptime(value.strip(), fmt)
                return True, ""
            except ValueError:
                continue
        return False, "Invalid date format. Use YYYY-MM-DD"

    return True, ""
