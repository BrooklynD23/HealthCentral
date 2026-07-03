"""
Normalization module.

Handles:
- Analyte name canonicalization
- Synonym mapping
- Unit preservation and conversion
"""

from typing import Optional
from dataclasses import dataclass


# --- Cross-lab unit conversion (NORM-UNIT-001) ---------------------------------
#
# The same analyte is reported in different units by different labs (mg/dL vs
# mmol/L, etc.). Without conversion, a trend line mixing units is not just
# fragmented — its computed change percentage is meaningless (94 mg/dL vs
# 5.22 mmol/L is the SAME glucose, but naive subtraction reads as a ~94% drop).
#
# Each table entry gives the analyte's canonical (display) unit plus a factor
# per recognized unit variant that converts a value in that unit INTO the
# canonical unit. The canonical unit's own factor is 1.0. Factors are
# established clinical constants (conventional <-> SI). Canonical is the
# conventional (US) unit here because the app's reference ranges come from
# US-style lab reports.
#
# Scope note (deliberately conservative for a patient health app): this table
# covers mass/molar-concentration conversions where cross-unit reporting is
# common and the factor is an unambiguous scalar. It intentionally omits CBC
# cell-count "x10^3/µL <-> x10^9/L" cases — those are numerically identical
# (factor 1.0, a cosmetic relabel only) but their unit strings vary wildly and
# parsing them wrong is a real risk. Untabled analytes keep legacy behavior.
#
# NEVER guess a factor for an unlisted unit — `convert_to_canonical` returns
# None and callers must treat the point as non-comparable.

# Per analyte: (canonical_unit, {normalized_unit: factor_to_canonical})
UNIT_CONVERSIONS: dict[str, tuple[str, dict[str, float]]] = {
    "glucose": ("mg/dL", {"mg/dl": 1.0, "mmol/l": 18.0156}),
    "total_cholesterol": ("mg/dL", {"mg/dl": 1.0, "mmol/l": 38.67}),
    "hdl_cholesterol": ("mg/dL", {"mg/dl": 1.0, "mmol/l": 38.67}),
    "ldl_cholesterol": ("mg/dL", {"mg/dl": 1.0, "mmol/l": 38.67}),
    "triglycerides": ("mg/dL", {"mg/dl": 1.0, "mmol/l": 88.57}),
    "creatinine": ("mg/dL", {"mg/dl": 1.0, "umol/l": 1.0 / 88.42}),
    "bun": ("mg/dL", {"mg/dl": 1.0, "mmol/l": 1.0 / 0.357}),
    "calcium": ("mg/dL", {"mg/dl": 1.0, "mmol/l": 4.008}),
    "bilirubin_total": ("mg/dL", {"mg/dl": 1.0, "umol/l": 1.0 / 17.1}),
    "hemoglobin": ("g/dL", {"g/dl": 1.0, "g/l": 0.1}),
    "albumin": ("g/dL", {"g/dl": 1.0, "g/l": 0.1}),
    "total_protein": ("g/dL", {"g/dl": 1.0, "g/l": 0.1}),
    "iron": ("µg/dL", {"ug/dl": 1.0, "umol/l": 1.0 / 0.179}),
    "vitamin_d": ("ng/mL", {"ng/ml": 1.0, "nmol/l": 1.0 / 2.496}),
    "vitamin_b12": ("pg/mL", {"pg/ml": 1.0, "pmol/l": 1.0 / 0.738}),
    "folate": ("ng/mL", {"ng/ml": 1.0, "nmol/l": 1.0 / 2.266}),
    "ferritin": ("ng/mL", {"ng/ml": 1.0, "ug/l": 1.0}),
    "tsh": ("µIU/mL", {"uiu/ml": 1.0, "miu/l": 1.0}),
    "free_t4": ("ng/dL", {"ng/dl": 1.0, "pmol/l": 1.0 / 12.87}),
}

_SUPERSCRIPTS = {"¹": "1", "²": "2", "³": "3", "⁶": "6", "⁹": "9"}


def normalize_unit(unit: str) -> str:
    """Fold a raw unit string to a canonical lowercase-ASCII key for lookup.

    Unifies the micro sign / greek mu, superscript digits, the multiplication
    sign, and whitespace/case so that "µmol/L", "μmol/L", and "UMOL/L " all
    map to the same key.
    """
    u = unit.strip().lower()
    u = u.replace("µ", "u").replace("μ", "u")  # µ (micro), μ (mu)
    for sup, digit in _SUPERSCRIPTS.items():
        u = u.replace(sup, digit)
    u = u.replace("×", "x")  # ×
    u = u.replace(" ", "")
    return u


@dataclass(frozen=True)
class UnitConversion:
    """Result of expressing a value in its analyte's canonical unit."""
    canonical_value: float
    canonical_unit: str
    original_value: float
    original_unit: str
    converted: bool  # True when the original unit differed from canonical


def canonical_unit_for(analyte_canonical: str) -> Optional[str]:
    """The canonical display unit for an analyte, or None if it has no
    conversion table entry (caller should keep legacy per-observation units)."""
    entry = UNIT_CONVERSIONS.get(analyte_canonical.lower())
    return entry[0] if entry else None


def convert_to_canonical(
    analyte_canonical: str, value: float, unit: Optional[str]
) -> Optional[UnitConversion]:
    """Express `value` (given in `unit`) in the analyte's canonical unit.

    Returns None when the analyte is untabled, the unit is missing, or the unit
    is not a recognized variant for that analyte — the caller must then treat
    the point as non-comparable and never assume a factor.
    """
    entry = UNIT_CONVERSIONS.get(analyte_canonical.lower())
    if entry is None or not unit:
        return None
    canonical_unit, factors = entry
    factor = factors.get(normalize_unit(unit))
    if factor is None:
        return None
    return UnitConversion(
        canonical_value=value * factor,
        canonical_unit=canonical_unit,
        original_value=value,
        original_unit=unit,
        converted=factor != 1.0,
    )


@dataclass
class NormalizedAnalyte:
    """Normalized analyte information."""
    canonical_name: str
    display_name: str
    category: str  # "cbc", "cmp", "lipid", "thyroid", etc.
    loinc_code: Optional[str] = None


class NormalizeModule:
    """
    Analyte normalization service.
    
    Maps various names and abbreviations to canonical forms.
    Preserves original names for provenance.
    """
    
    # Built-in synonym mappings (extendable via database)
    ANALYTE_SYNONYMS = {
        # CBC
        "hemoglobin": ["hgb", "hb", "haemoglobin"],
        "hematocrit": ["hct", "hcrit", "packed cell volume", "pcv"],
        "red_blood_cells": ["rbc", "red blood cell count", "erythrocytes"],
        "white_blood_cells": ["wbc", "white blood cell count", "leukocytes"],
        "platelets": ["plt", "platelet count", "thrombocytes"],
        "mcv": ["mean corpuscular volume"],
        "mch": ["mean corpuscular hemoglobin"],
        "mchc": ["mean corpuscular hemoglobin concentration"],
        "rdw": ["red cell distribution width"],
        
        # CMP/BMP
        "glucose": ["blood glucose", "fasting glucose", "glu"],
        "bun": ["blood urea nitrogen", "urea nitrogen"],
        "creatinine": ["creat", "cr"],
        "sodium": ["na", "na+"],
        "potassium": ["k", "k+"],
        "chloride": ["cl", "cl-"],
        "carbon_dioxide": ["co2", "bicarbonate", "hco3", "total co2"],
        "calcium": ["ca", "ca++"],
        "albumin": ["alb"],
        "total_protein": ["protein, total", "tp"],
        "bilirubin_total": ["total bilirubin", "tbili", "t. bili"],
        "alkaline_phosphatase": ["alk phos", "alp", "alkp"],
        "ast": ["aspartate aminotransferase", "sgot", "aspartate transaminase"],
        "alt": ["alanine aminotransferase", "sgpt", "alanine transaminase"],
        
        # Lipids
        "total_cholesterol": ["cholesterol", "total chol", "tc"],
        "hdl_cholesterol": ["hdl", "hdl-c", "high density lipoprotein"],
        "ldl_cholesterol": ["ldl", "ldl-c", "low density lipoprotein"],
        "triglycerides": ["trig", "tg"],
        
        # Thyroid
        "tsh": ["thyroid stimulating hormone", "thyrotropin"],
        "free_t4": ["ft4", "free thyroxine", "thyroxine free"],
        "free_t3": ["ft3", "free triiodothyronine"],
        
        # Iron studies
        "iron": ["serum iron", "fe"],
        "ferritin": ["serum ferritin"],
        "tibc": ["total iron binding capacity", "iron binding capacity"],
        
        # Vitamins
        "vitamin_d": ["25-hydroxy vitamin d", "25-oh vitamin d", "vitamin d 25-oh", "25(oh)d"],
        "vitamin_b12": ["b12", "cobalamin"],
        "folate": ["folic acid", "serum folate"],
        
        # Inflammation
        "crp": ["c-reactive protein", "c reactive protein"],
        "esr": ["erythrocyte sedimentation rate", "sed rate"],
        
        # HbA1c
        "hba1c": ["hemoglobin a1c", "glycated hemoglobin", "a1c", "glycohemoglobin"],
    }
    
    # Analyte categories
    ANALYTE_CATEGORIES = {
        "cbc": [
            "hemoglobin", "hematocrit", "red_blood_cells", "white_blood_cells",
            "platelets", "mcv", "mch", "mchc", "rdw"
        ],
        "cmp": [
            "glucose", "bun", "creatinine", "sodium", "potassium", "chloride",
            "carbon_dioxide", "calcium", "albumin", "total_protein",
            "bilirubin_total", "alkaline_phosphatase", "ast", "alt"
        ],
        "bmp": [
            "glucose", "bun", "creatinine", "sodium", "potassium", "chloride",
            "carbon_dioxide", "calcium"
        ],
        "lipid": ["total_cholesterol", "hdl_cholesterol", "ldl_cholesterol", "triglycerides"],
        "thyroid": ["tsh", "free_t4", "free_t3"],
        "iron": ["iron", "ferritin", "tibc"],
        "vitamin": ["vitamin_d", "vitamin_b12", "folate"],
        "inflammation": ["crp", "esr"],
        "diabetes": ["glucose", "hba1c"],
    }
    
    # Display names
    DISPLAY_NAMES = {
        "hemoglobin": "Hemoglobin",
        "hematocrit": "Hematocrit",
        "red_blood_cells": "Red Blood Cells (RBC)",
        "white_blood_cells": "White Blood Cells (WBC)",
        "platelets": "Platelets",
        "glucose": "Glucose",
        "bun": "BUN (Blood Urea Nitrogen)",
        "creatinine": "Creatinine",
        "sodium": "Sodium",
        "potassium": "Potassium",
        "chloride": "Chloride",
        "tsh": "TSH",
        "free_t4": "Free T4",
        "hba1c": "Hemoglobin A1c",
        "total_cholesterol": "Total Cholesterol",
        "hdl_cholesterol": "HDL Cholesterol",
        "ldl_cholesterol": "LDL Cholesterol",
        "triglycerides": "Triglycerides",
        "vitamin_d": "Vitamin D",
        "vitamin_b12": "Vitamin B12",
        "ferritin": "Ferritin",
        "crp": "C-Reactive Protein (CRP)",
    }
    
    def __init__(self):
        """Initialize normalization module."""
        # Build reverse lookup
        self._synonym_to_canonical = {}
        for canonical, synonyms in self.ANALYTE_SYNONYMS.items():
            self._synonym_to_canonical[canonical.lower()] = canonical
            for syn in synonyms:
                self._synonym_to_canonical[syn.lower()] = canonical
    
    def normalize_analyte(self, raw_name: str) -> NormalizedAnalyte:
        """
        Normalize an analyte name to canonical form.
        
        Args:
            raw_name: Raw analyte name from document
            
        Returns:
            NormalizedAnalyte with canonical name and metadata
        """
        # Clean and lowercase
        cleaned = raw_name.lower().strip()
        
        # Look up canonical name
        canonical = self._synonym_to_canonical.get(cleaned)
        
        if canonical:
            display_name = self.DISPLAY_NAMES.get(canonical, canonical.replace("_", " ").title())
            category = self._get_category(canonical)
            return NormalizedAnalyte(
                canonical_name=canonical,
                display_name=display_name,
                category=category,
            )
        else:
            # Unknown analyte - use cleaned raw name as canonical
            return NormalizedAnalyte(
                canonical_name=cleaned.replace(" ", "_"),
                display_name=raw_name.strip(),
                category="other",
            )
    
    def _get_category(self, canonical_name: str) -> str:
        """Get the category for an analyte."""
        for category, analytes in self.ANALYTE_CATEGORIES.items():
            if canonical_name in analytes:
                return category
        return "other"
    
    def get_panel_analytes(self, panel_name: str) -> list[str]:
        """Get list of analytes in a panel."""
        return self.ANALYTE_CATEGORIES.get(panel_name.lower(), [])
