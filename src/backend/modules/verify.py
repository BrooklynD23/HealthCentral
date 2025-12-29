"""
Verification module.

Handles:
- Verification workflow management
- User edit tracking
- Version history
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


class VerifyModule:
    """
    Verification workflow service.
    
    Manages the human-in-the-loop verification process
    for extracted observations.
    """
    
    # Fields that can be edited
    EDITABLE_FIELDS = [
        "value",
        "value_text",
        "unit",
        "ref_low",
        "ref_high",
        "collected_at",
        "notes",
    ]
    
    def __init__(self):
        """Initialize verification module."""
        pass
    
    def get_needs_verification(
        self,
        profile_id: str,
        confidence_threshold: float = 0.7,
    ) -> list[str]:
        """
        Get observation IDs that need verification.
        
        Criteria:
        - Not yet verified
        - Confidence below threshold
        - OCR-derived (Phase 1+)
        
        Args:
            profile_id: Profile ID
            confidence_threshold: Minimum confidence for auto-accept
            
        Returns:
            List of observation IDs needing verification
        """
        # TODO: Implement database query
        return []
    
    def prepare_verification_payload(
        self,
        observation_id: str,
    ) -> VerificationPayload:
        """
        Prepare data for verification UI.
        
        Includes extracted values and source snippet for comparison.
        """
        # TODO: Implement payload preparation
        raise NotImplementedError()
    
    def apply_verification(
        self,
        observation_id: str,
        edits: dict[str, any],
        verified_by: str = "user",
    ) -> bool:
        """
        Apply verification edits to an observation.
        
        Args:
            observation_id: Observation to verify
            edits: Dictionary of field -> new value
            verified_by: Who verified (for audit)
            
        Returns:
            True if successful
        """
        # Validate edits
        for field in edits:
            if field not in self.EDITABLE_FIELDS:
                raise ValueError(f"Field not editable: {field}")
        
        # TODO: Implement edit application with version tracking
        raise NotImplementedError()
    
    def validate_value(
        self,
        value: any,
        field_name: str,
    ) -> tuple[bool, str]:
        """
        Validate a user-entered value.
        
        Args:
            value: Value to validate
            field_name: Field being edited
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if field_name in ["value", "ref_low", "ref_high"]:
            try:
                float(value)
                return True, ""
            except (ValueError, TypeError):
                return False, "Must be a number"
        
        if field_name == "collected_at":
            # TODO: Validate date format
            return True, ""
        
        return True, ""
