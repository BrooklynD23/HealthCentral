"""
Medical Glossary Module.

Provides plain-language definitions for medical terms.
Uses a curated local glossary for privacy and consistency.
"""

from typing import Optional


# Curated medical terms glossary
# Focus on lab test-related terms patients commonly encounter
MEDICAL_GLOSSARY = {
    "hemoglobin": {
        "term": "Hemoglobin",
        "definition": "A protein in red blood cells that carries oxygen from your lungs to the rest of your body and returns carbon dioxide from the body back to the lungs. Hemoglobin levels are measured to check for conditions like anemia.",
        "related_terms": ["hematocrit", "red blood cells", "anemia", "iron"],
        "source": "Medical Reference Glossary",
    },
    "glucose": {
        "term": "Glucose",
        "definition": "A type of sugar that is the main source of energy for your body's cells. Blood glucose levels are measured to check how well your body processes sugar, which is important for detecting and managing diabetes.",
        "related_terms": ["blood sugar", "fasting glucose", "diabetes", "insulin"],
        "source": "Medical Reference Glossary",
    },
    "cholesterol": {
        "term": "Cholesterol",
        "definition": "A waxy, fat-like substance found in all cells of the body. Your body needs some cholesterol to function properly, but too much can build up in arteries and increase the risk of heart disease.",
        "related_terms": ["LDL", "HDL", "triglycerides", "lipid panel"],
        "source": "Medical Reference Glossary",
    },
    "ldl": {
        "term": "LDL (Low-Density Lipoprotein)",
        "definition": "Often called 'bad' cholesterol because high levels can lead to plaque buildup in arteries and increase the risk of heart disease and stroke. It carries cholesterol to tissues.",
        "related_terms": ["cholesterol", "HDL", "lipid panel", "cardiovascular"],
        "source": "Medical Reference Glossary",
    },
    "hdl": {
        "term": "HDL (High-Density Lipoprotein)",
        "definition": "Often called 'good' cholesterol because it helps remove other forms of cholesterol from your bloodstream. Higher levels of HDL are generally associated with lower risk of heart disease.",
        "related_terms": ["cholesterol", "LDL", "lipid panel", "cardiovascular"],
        "source": "Medical Reference Glossary",
    },
    "triglycerides": {
        "term": "Triglycerides",
        "definition": "A type of fat found in your blood. When you eat, your body converts extra calories into triglycerides and stores them in fat cells. High levels may increase the risk of heart disease.",
        "related_terms": ["cholesterol", "lipid panel", "fat", "cardiovascular"],
        "source": "Medical Reference Glossary",
    },
    "hemoglobin a1c": {
        "term": "Hemoglobin A1c (HbA1c)",
        "definition": "A blood test that measures your average blood sugar levels over the past 2-3 months. It shows how well your blood sugar has been controlled and is used to diagnose and monitor diabetes.",
        "related_terms": ["glucose", "diabetes", "blood sugar", "glycated hemoglobin"],
        "source": "Medical Reference Glossary",
    },
    "hba1c": {
        "term": "Hemoglobin A1c (HbA1c)",
        "definition": "A blood test that measures your average blood sugar levels over the past 2-3 months. It shows how well your blood sugar has been controlled and is used to diagnose and monitor diabetes.",
        "related_terms": ["glucose", "diabetes", "blood sugar", "glycated hemoglobin"],
        "source": "Medical Reference Glossary",
    },
    "creatinine": {
        "term": "Creatinine",
        "definition": "A waste product that muscles produce at a steady rate. Your kidneys filter creatinine from the blood and remove it in urine. Creatinine levels are measured to assess how well your kidneys are working.",
        "related_terms": ["kidney function", "BUN", "GFR", "renal"],
        "source": "Medical Reference Glossary",
    },
    "bun": {
        "term": "BUN (Blood Urea Nitrogen)",
        "definition": "A test that measures the amount of nitrogen in your blood that comes from urea, a waste product of protein breakdown. It helps evaluate kidney function and is often tested alongside creatinine.",
        "related_terms": ["creatinine", "kidney function", "urea", "renal"],
        "source": "Medical Reference Glossary",
    },
    "wbc": {
        "term": "WBC (White Blood Cell Count)",
        "definition": "A measure of the number of white blood cells in your blood. White blood cells are part of your immune system and help fight infections. Abnormal counts may indicate infection, immune disorders, or other conditions.",
        "related_terms": ["immune system", "infection", "CBC", "leukocytes"],
        "source": "Medical Reference Glossary",
    },
    "rbc": {
        "term": "RBC (Red Blood Cell Count)",
        "definition": "A measure of the number of red blood cells in your blood. Red blood cells carry oxygen from your lungs to the rest of your body. Abnormal counts may indicate anemia or other blood disorders.",
        "related_terms": ["hemoglobin", "hematocrit", "anemia", "CBC"],
        "source": "Medical Reference Glossary",
    },
    "hematocrit": {
        "term": "Hematocrit",
        "definition": "A test that measures the percentage of your blood that is made up of red blood cells. It helps detect anemia, dehydration, and other blood-related conditions.",
        "related_terms": ["hemoglobin", "RBC", "anemia", "CBC"],
        "source": "Medical Reference Glossary",
    },
    "platelets": {
        "term": "Platelets",
        "definition": "Small blood cells that help your blood clot to stop bleeding when you have a cut or injury. Platelet counts that are too high or too low can indicate various medical conditions.",
        "related_terms": ["blood clotting", "CBC", "bleeding disorders", "thrombocytes"],
        "source": "Medical Reference Glossary",
    },
    "tsh": {
        "term": "TSH (Thyroid-Stimulating Hormone)",
        "definition": "A hormone produced by the pituitary gland that controls how much thyroid hormone your thyroid gland makes. TSH levels are measured to check if your thyroid is working properly.",
        "related_terms": ["thyroid", "T4", "T3", "hyperthyroidism", "hypothyroidism"],
        "source": "Medical Reference Glossary",
    },
    "alt": {
        "term": "ALT (Alanine Aminotransferase)",
        "definition": "An enzyme found mainly in the liver. When liver cells are damaged, ALT is released into the bloodstream. Elevated levels may indicate liver disease or damage.",
        "related_terms": ["liver function", "AST", "hepatic", "liver enzymes"],
        "source": "Medical Reference Glossary",
    },
    "ast": {
        "term": "AST (Aspartate Aminotransferase)",
        "definition": "An enzyme found in the liver, heart, and muscles. Elevated levels may indicate damage to these tissues, particularly the liver. Often measured alongside ALT.",
        "related_terms": ["liver function", "ALT", "hepatic", "liver enzymes"],
        "source": "Medical Reference Glossary",
    },
    "gfr": {
        "term": "GFR (Glomerular Filtration Rate)",
        "definition": "A measure of how well your kidneys are filtering waste from your blood. It is the best overall indicator of kidney function and is used to stage chronic kidney disease.",
        "related_terms": ["kidney function", "creatinine", "renal", "eGFR"],
        "source": "Medical Reference Glossary",
    },
    "cbc": {
        "term": "CBC (Complete Blood Count)",
        "definition": "A common blood test that measures different components of your blood including red blood cells, white blood cells, hemoglobin, hematocrit, and platelets. It provides a general overview of your health.",
        "related_terms": ["WBC", "RBC", "hemoglobin", "platelets"],
        "source": "Medical Reference Glossary",
    },
    "cmp": {
        "term": "CMP (Comprehensive Metabolic Panel)",
        "definition": "A group of blood tests that provides information about your body's chemical balance, metabolism, kidney function, and liver function. It includes tests for glucose, electrolytes, and more.",
        "related_terms": ["glucose", "electrolytes", "kidney function", "liver function"],
        "source": "Medical Reference Glossary",
    },
    "electrolytes": {
        "term": "Electrolytes",
        "definition": "Minerals in your blood and body fluids that carry an electric charge. They include sodium, potassium, chloride, and bicarbonate. Electrolytes help balance fluid levels, regulate pH, and support nerve and muscle function.",
        "related_terms": ["sodium", "potassium", "chloride", "bicarbonate"],
        "source": "Medical Reference Glossary",
    },
    "sodium": {
        "term": "Sodium",
        "definition": "An electrolyte that helps control fluid balance in the body and is essential for nerve and muscle function. Sodium levels are tightly regulated by the kidneys.",
        "related_terms": ["electrolytes", "potassium", "fluid balance", "kidney"],
        "source": "Medical Reference Glossary",
    },
    "potassium": {
        "term": "Potassium",
        "definition": "An electrolyte essential for proper function of cells, nerves, and muscles, including the heart. Abnormal potassium levels can affect heart rhythm.",
        "related_terms": ["electrolytes", "sodium", "heart rhythm", "kidney"],
        "source": "Medical Reference Glossary",
    },
    "reference range": {
        "term": "Reference Range",
        "definition": "The range of values considered normal for a particular lab test. Reference ranges are established based on test results from large groups of healthy people and may vary between laboratories.",
        "related_terms": ["normal range", "lab values", "abnormal"],
        "source": "Medical Reference Glossary",
    },
    "fasting": {
        "term": "Fasting",
        "definition": "Not eating or drinking anything except water for a specified period before a blood test. Some tests, like fasting glucose or lipid panels, require fasting for accurate results.",
        "related_terms": ["glucose", "lipid panel", "blood test"],
        "source": "Medical Reference Glossary",
    },
    "anemia": {
        "term": "Anemia",
        "definition": "A condition where you don't have enough healthy red blood cells to carry adequate oxygen to your tissues. It can cause fatigue, weakness, and shortness of breath.",
        "related_terms": ["hemoglobin", "RBC", "iron", "fatigue"],
        "source": "Medical Reference Glossary",
    },
}


class GlossaryModule:
    """
    Medical term glossary for patient education.

    Provides plain-language definitions that avoid medical jargon
    and do not provide medical advice.
    """

    def __init__(self):
        """Initialize glossary module."""
        self.glossary = MEDICAL_GLOSSARY

    def lookup(self, term: str) -> Optional[dict]:
        """
        Look up a medical term definition.

        Args:
            term: Medical term to look up

        Returns:
            Dictionary with term, definition, related_terms, source
            or None if not found
        """
        if not term:
            return None

        # Normalize term for lookup
        normalized = term.lower().strip()

        # Direct lookup
        if normalized in self.glossary:
            return self.glossary[normalized].copy()

        # Try removing common suffixes/variations
        variations = [
            normalized,
            normalized.replace("-", " "),
            normalized.replace("_", " "),
            normalized.replace(" ", "_"),
        ]

        for var in variations:
            if var in self.glossary:
                return self.glossary[var].copy()

        # Try partial match for longer terms
        for key, entry in self.glossary.items():
            if normalized in key or key in normalized:
                return entry.copy()

        return None

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """
        Search for terms matching a query.

        Args:
            query: Search query
            limit: Maximum results to return

        Returns:
            List of matching term entries
        """
        if not query:
            return []

        query_lower = query.lower()
        results = []

        for key, entry in self.glossary.items():
            # Check if query matches term or definition
            score = 0
            if query_lower in key:
                score += 2
            if query_lower in entry["definition"].lower():
                score += 1
            if any(query_lower in rt.lower() for rt in entry.get("related_terms", [])):
                score += 1

            if score > 0:
                results.append((score, entry.copy()))

        # Sort by score descending
        results.sort(key=lambda x: x[0], reverse=True)

        return [entry for _, entry in results[:limit]]

    def get_all_terms(self) -> list[str]:
        """Get all available terms in the glossary."""
        return sorted(self.glossary.keys())
