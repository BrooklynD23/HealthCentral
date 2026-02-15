"""
FHIR R4 resource models for export.

Pydantic models (not SQLAlchemy) for serializing observations
and profile data into FHIR R4 JSON format.

Design Decision DD-4: Minimal Patient resource, LOINC via BiomarkerKnowledge lookup.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class FHIRCoding(BaseModel):
    system: Optional[str] = None
    code: Optional[str] = None
    display: Optional[str] = None


class FHIRCodeableConcept(BaseModel):
    coding: list[FHIRCoding] = Field(default_factory=list)
    text: Optional[str] = None


class FHIRHumanName(BaseModel):
    text: str


class FHIRAbsentExtension(BaseModel):
    url: str = "http://hl7.org/fhir/StructureDefinition/data-absent-reason"
    valueCode: str = "unknown"


class FHIRAbsentField(BaseModel):
    extension: list[FHIRAbsentExtension] = Field(
        default_factory=lambda: [FHIRAbsentExtension()]
    )


class FHIRQuantity(BaseModel):
    value: Optional[float] = None
    unit: Optional[str] = None
    system: str = "http://unitsofmeasure.org"


class FHIRReferenceRange(BaseModel):
    low: Optional[FHIRQuantity] = None
    high: Optional[FHIRQuantity] = None


class FHIRReference(BaseModel):
    reference: str


class FHIRPatient(BaseModel):
    resourceType: str = Field(default="Patient", alias="resourceType")
    id: str
    display_name: str = Field(exclude=True)
    name: list[FHIRHumanName] = None
    _birthDate: Optional[FHIRAbsentField] = Field(
        default_factory=FHIRAbsentField, alias="_birthDate"
    )

    def model_post_init(self, __context) -> None:
        if self.name is None:
            self.name = [FHIRHumanName(text=self.display_name)]

    class Config:
        populate_by_name = True


class FHIRObservation(BaseModel):
    resourceType: str = Field(default="Observation", alias="resourceType")
    id: str
    status: str = "final"
    code: FHIRCodeableConcept
    subject: Optional[FHIRReference] = None
    effectiveDateTime: Optional[str] = Field(default=None, alias="effectiveDateTime")
    valueQuantity: Optional[FHIRQuantity] = Field(default=None, alias="valueQuantity")
    valueString: Optional[str] = Field(default=None, alias="valueString")
    referenceRange: list[FHIRReferenceRange] = Field(
        default_factory=list, alias="referenceRange"
    )

    class Config:
        populate_by_name = True


class FHIRBundleEntry(BaseModel):
    resource: dict


class FHIRBundle(BaseModel):
    resourceType: str = Field(default="Bundle", alias="resourceType")
    type: str = "collection"
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    entry: list[FHIRBundleEntry] = Field(default_factory=list)

    class Config:
        populate_by_name = True


def map_observation_to_fhir(
    obs: dict,
    patient_ref: str,
    loinc_map: Optional[dict[str, list[str]]] = None,
) -> FHIRObservation:
    """Map an observation dict to a FHIR R4 Observation resource."""
    analyte = obs.get("analyte_canonical", "")

    # Build code with LOINC lookup
    codings = []
    if loinc_map and analyte in loinc_map:
        for loinc_code in loinc_map[analyte]:
            codings.append(FHIRCoding(
                system="http://loinc.org",
                code=loinc_code,
                display=analyte,
            ))
    codings.append(FHIRCoding(display=analyte))
    code = FHIRCodeableConcept(coding=codings, text=analyte)

    # Value
    value_quantity = None
    value_string = None
    if obs.get("value") is not None:
        value_quantity = FHIRQuantity(value=obs["value"], unit=obs.get("unit", ""))
    elif obs.get("value_text"):
        value_string = obs["value_text"]

    # Reference range
    ref_ranges = []
    if obs.get("ref_low") is not None or obs.get("ref_high") is not None:
        ref_range = FHIRReferenceRange()
        if obs.get("ref_low") is not None:
            ref_range.low = FHIRQuantity(value=obs["ref_low"], unit=obs.get("unit", ""))
        if obs.get("ref_high") is not None:
            ref_range.high = FHIRQuantity(value=obs["ref_high"], unit=obs.get("unit", ""))
        ref_ranges.append(ref_range)

    # Effective date
    effective_dt = None
    if obs.get("collected_at"):
        dt = obs["collected_at"]
        effective_dt = dt.isoformat() if isinstance(dt, datetime) else str(dt)

    return FHIRObservation(
        id=obs.get("id", ""),
        code=code,
        subject=FHIRReference(reference=patient_ref),
        effectiveDateTime=effective_dt,
        valueQuantity=value_quantity,
        valueString=value_string,
        referenceRange=ref_ranges,
    )


def create_fhir_bundle(
    patient: FHIRPatient,
    observations: list[FHIRObservation],
) -> FHIRBundle:
    """Create a FHIR Bundle containing a Patient and Observations."""
    entries = [
        FHIRBundleEntry(resource=patient.model_dump(by_alias=True, exclude_none=True))
    ]
    for obs in observations:
        entries.append(
            FHIRBundleEntry(resource=obs.model_dump(by_alias=True, exclude_none=True))
        )
    return FHIRBundle(entry=entries)
