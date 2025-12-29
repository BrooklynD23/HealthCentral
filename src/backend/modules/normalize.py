"""
Normalization module.

Handles:
- Analyte name canonicalization
- Synonym mapping
- Unit preservation and conversion
"""

from typing import Optional
from dataclasses import dataclass


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
