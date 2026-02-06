"""
Test Intent Module.

Provides educational information about what lab tests are typically ordered for.
Uses curated local data for privacy and consistency.
"""

from typing import Optional


# Curated test intent information
# Explains what tests are for without providing medical advice
TEST_INTENT_DATA = {
    "hemoglobin_a1c": {
        "analyte": "hemoglobin_a1c",
        "analyte_display_name": "Hemoglobin A1c (HbA1c)",
        "intent_summary": "This test measures average blood sugar levels over the past 2-3 months. It is commonly ordered to diagnose diabetes or prediabetes and to monitor how well blood sugar is being controlled in people with diabetes.",
        "general_info": "The HbA1c test works by measuring the percentage of hemoglobin (a protein in red blood cells) that has glucose attached to it. Since red blood cells live for about 3 months, this test reflects long-term blood sugar patterns rather than daily fluctuations.",
        "typical_ordering_reasons": [
            "Screening for diabetes or prediabetes",
            "Monitoring diabetes management",
            "Assessing risk of diabetes-related complications",
        ],
        "source": "Medical Reference Database",
    },
    "glucose": {
        "analyte": "glucose",
        "analyte_display_name": "Blood Glucose",
        "intent_summary": "This test measures the amount of sugar in your blood at the time of the test. It is commonly ordered to screen for diabetes, monitor blood sugar control, or check for hypoglycemia (low blood sugar).",
        "general_info": "Glucose is the body's main source of energy. Fasting glucose tests are taken after not eating for at least 8 hours and are used to diagnose diabetes. Random glucose tests can be taken any time to check current blood sugar levels.",
        "typical_ordering_reasons": [
            "Screening for diabetes",
            "Monitoring blood sugar control",
            "Evaluating symptoms of high or low blood sugar",
            "Pre-surgical evaluation",
        ],
        "source": "Medical Reference Database",
    },
    "cholesterol_total": {
        "analyte": "cholesterol_total",
        "analyte_display_name": "Total Cholesterol",
        "intent_summary": "This test measures the total amount of cholesterol in your blood. It is commonly ordered as part of a lipid panel to assess cardiovascular disease risk.",
        "general_info": "Total cholesterol includes LDL (low-density lipoprotein), HDL (high-density lipoprotein), and other lipid components. Cholesterol is needed by the body, but high levels can increase the risk of heart disease and stroke.",
        "typical_ordering_reasons": [
            "Cardiovascular disease risk assessment",
            "Routine health screening",
            "Monitoring response to lifestyle changes or medications",
        ],
        "source": "Medical Reference Database",
    },
    "ldl": {
        "analyte": "ldl",
        "analyte_display_name": "LDL Cholesterol",
        "intent_summary": "This test measures low-density lipoprotein cholesterol, often called 'bad' cholesterol. It is commonly ordered to assess cardiovascular disease risk and guide treatment decisions.",
        "general_info": "LDL carries cholesterol to tissues and arteries. High LDL levels are associated with increased buildup of plaque in arteries (atherosclerosis), which can lead to heart attack or stroke.",
        "typical_ordering_reasons": [
            "Cardiovascular risk assessment",
            "Monitoring cholesterol-lowering therapy",
            "Evaluating need for lifestyle changes",
        ],
        "source": "Medical Reference Database",
    },
    "hdl": {
        "analyte": "hdl",
        "analyte_display_name": "HDL Cholesterol",
        "intent_summary": "This test measures high-density lipoprotein cholesterol, often called 'good' cholesterol. It is commonly ordered as part of cardiovascular risk assessment.",
        "general_info": "HDL helps remove cholesterol from the bloodstream and transport it back to the liver. Higher HDL levels are generally associated with lower cardiovascular disease risk.",
        "typical_ordering_reasons": [
            "Cardiovascular risk assessment",
            "Routine lipid screening",
            "Evaluating overall cholesterol profile",
        ],
        "source": "Medical Reference Database",
    },
    "triglycerides": {
        "analyte": "triglycerides",
        "analyte_display_name": "Triglycerides",
        "intent_summary": "This test measures the level of triglycerides (a type of fat) in your blood. It is commonly ordered as part of a lipid panel to assess cardiovascular risk.",
        "general_info": "Triglycerides are formed when the body converts excess calories into fat for storage. High levels, especially combined with high LDL or low HDL, may increase cardiovascular disease risk.",
        "typical_ordering_reasons": [
            "Cardiovascular risk assessment",
            "Evaluating metabolic health",
            "Monitoring response to diet and lifestyle changes",
        ],
        "source": "Medical Reference Database",
    },
    "creatinine": {
        "analyte": "creatinine",
        "analyte_display_name": "Creatinine",
        "intent_summary": "This test measures the level of creatinine, a waste product from muscle metabolism, in your blood. It is commonly ordered to assess kidney function.",
        "general_info": "The kidneys filter creatinine from the blood and excrete it in urine. When kidney function declines, creatinine levels in the blood rise. This test is often used with GFR to evaluate kidney health.",
        "typical_ordering_reasons": [
            "Kidney function assessment",
            "Monitoring kidney disease progression",
            "Pre-medication safety check",
            "Annual health screening",
        ],
        "source": "Medical Reference Database",
    },
    "bun": {
        "analyte": "bun",
        "analyte_display_name": "Blood Urea Nitrogen (BUN)",
        "intent_summary": "This test measures the amount of nitrogen in your blood from urea, a waste product of protein metabolism. It is commonly ordered to evaluate kidney function.",
        "general_info": "BUN levels can be affected by kidney function, hydration status, and protein intake. It is often measured alongside creatinine to provide a more complete picture of kidney health.",
        "typical_ordering_reasons": [
            "Kidney function assessment",
            "Evaluating hydration status",
            "Monitoring kidney disease",
            "Pre-surgical evaluation",
        ],
        "source": "Medical Reference Database",
    },
    "gfr": {
        "analyte": "gfr",
        "analyte_display_name": "Glomerular Filtration Rate (GFR)",
        "intent_summary": "This calculated value estimates how well your kidneys are filtering waste from your blood. It is the best overall indicator of kidney function.",
        "general_info": "GFR is calculated from creatinine levels along with age, sex, and other factors. It is used to detect, evaluate, and monitor kidney disease, and to determine chronic kidney disease stage.",
        "typical_ordering_reasons": [
            "Kidney disease detection and staging",
            "Monitoring kidney function over time",
            "Medication dosing adjustments",
            "Evaluating kidney transplant function",
        ],
        "source": "Medical Reference Database",
    },
    "tsh": {
        "analyte": "tsh",
        "analyte_display_name": "Thyroid-Stimulating Hormone (TSH)",
        "intent_summary": "This test measures the level of TSH, a hormone that controls thyroid function. It is commonly ordered to evaluate thyroid health and detect thyroid disorders.",
        "general_info": "TSH is produced by the pituitary gland and signals the thyroid to produce hormones. High TSH may indicate underactive thyroid (hypothyroidism), while low TSH may indicate overactive thyroid (hyperthyroidism).",
        "typical_ordering_reasons": [
            "Thyroid function screening",
            "Evaluating fatigue, weight changes, or other symptoms",
            "Monitoring thyroid medication",
            "Newborn screening",
        ],
        "source": "Medical Reference Database",
    },
    "wbc": {
        "analyte": "wbc",
        "analyte_display_name": "White Blood Cell Count (WBC)",
        "intent_summary": "This test measures the number of white blood cells in your blood. It is commonly ordered to detect infections, immune disorders, or blood cancers.",
        "general_info": "White blood cells are part of the immune system and help fight infections. The count can be high (indicating infection or inflammation) or low (indicating immune problems).",
        "typical_ordering_reasons": [
            "Detecting infection",
            "Evaluating immune function",
            "Monitoring cancer treatment effects",
            "Investigating unexplained symptoms",
        ],
        "source": "Medical Reference Database",
    },
    "rbc": {
        "analyte": "rbc",
        "analyte_display_name": "Red Blood Cell Count (RBC)",
        "intent_summary": "This test measures the number of red blood cells in your blood. It is commonly ordered to detect anemia or other blood disorders.",
        "general_info": "Red blood cells carry oxygen from the lungs to all parts of the body. Low counts may indicate anemia, while high counts may indicate dehydration or other conditions.",
        "typical_ordering_reasons": [
            "Anemia evaluation",
            "Routine health screening",
            "Investigating fatigue or weakness",
            "Monitoring blood loss recovery",
        ],
        "source": "Medical Reference Database",
    },
    "hemoglobin": {
        "analyte": "hemoglobin",
        "analyte_display_name": "Hemoglobin",
        "intent_summary": "This test measures the amount of hemoglobin, the oxygen-carrying protein in red blood cells. It is commonly ordered to detect anemia and evaluate blood health.",
        "general_info": "Hemoglobin carries oxygen from the lungs to tissues throughout the body. Low levels indicate anemia, which can cause fatigue, weakness, and shortness of breath.",
        "typical_ordering_reasons": [
            "Anemia diagnosis and monitoring",
            "Pre-surgical evaluation",
            "Evaluating blood loss",
            "Routine health screening",
        ],
        "source": "Medical Reference Database",
    },
    "platelets": {
        "analyte": "platelets",
        "analyte_display_name": "Platelet Count",
        "intent_summary": "This test measures the number of platelets in your blood. Platelets are essential for blood clotting. It is commonly ordered to evaluate bleeding or clotting disorders.",
        "general_info": "Platelets help stop bleeding by forming clots at injury sites. Low counts may increase bleeding risk, while high counts may increase clotting risk.",
        "typical_ordering_reasons": [
            "Evaluating bleeding disorders",
            "Pre-surgical assessment",
            "Monitoring bone marrow function",
            "Evaluating easy bruising",
        ],
        "source": "Medical Reference Database",
    },
    "alt": {
        "analyte": "alt",
        "analyte_display_name": "ALT (Alanine Aminotransferase)",
        "intent_summary": "This test measures the level of ALT enzyme in your blood. It is commonly ordered to evaluate liver health and detect liver damage.",
        "general_info": "ALT is found mainly in the liver. When liver cells are damaged, ALT is released into the blood, causing elevated levels. It is a sensitive marker of liver injury.",
        "typical_ordering_reasons": [
            "Liver function assessment",
            "Monitoring medication effects on liver",
            "Evaluating hepatitis or fatty liver",
            "Alcohol-related liver assessment",
        ],
        "source": "Medical Reference Database",
    },
    "ast": {
        "analyte": "ast",
        "analyte_display_name": "AST (Aspartate Aminotransferase)",
        "intent_summary": "This test measures the level of AST enzyme in your blood. It is commonly ordered to evaluate liver and heart health.",
        "general_info": "AST is found in the liver, heart, and muscles. Elevated levels may indicate damage to these tissues. It is often tested alongside ALT to assess liver function.",
        "typical_ordering_reasons": [
            "Liver function assessment",
            "Evaluating muscle or heart damage",
            "Monitoring medication effects",
            "Investigating elevated ALT",
        ],
        "source": "Medical Reference Database",
    },
}


class TestIntentModule:
    """
    Lab test intent information for patient education.

    Provides educational information about what tests are typically
    ordered for, without providing medical advice.
    """

    def __init__(self):
        """Initialize test intent module."""
        self.data = TEST_INTENT_DATA

    def lookup(self, analyte: str) -> Optional[dict]:
        """
        Look up test intent for an analyte.

        Args:
            analyte: Analyte/test name to look up

        Returns:
            Dictionary with intent information or None if not found
        """
        if not analyte:
            return None

        # Normalize analyte name
        normalized = analyte.lower().strip().replace(" ", "_").replace("-", "_")

        # Direct lookup
        if normalized in self.data:
            return self.data[normalized].copy()

        # Try common variations
        variations = [
            normalized,
            normalized.replace("_", ""),
            normalized.replace("_", " "),
        ]

        for var in variations:
            if var in self.data:
                return self.data[var].copy()

        # Try partial match
        for key in self.data:
            if normalized in key or key in normalized:
                return self.data[key].copy()

        return None

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """
        Search for tests matching a query.

        Args:
            query: Search query
            limit: Maximum results

        Returns:
            List of matching test intent entries
        """
        if not query:
            return []

        query_lower = query.lower()
        results = []

        for key, entry in self.data.items():
            score = 0
            if query_lower in key:
                score += 2
            if query_lower in entry["intent_summary"].lower():
                score += 1
            if query_lower in entry["general_info"].lower():
                score += 1

            if score > 0:
                results.append((score, entry.copy()))

        results.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in results[:limit]]

    def get_all_analytes(self) -> list[str]:
        """Get all available analytes with intent info."""
        return sorted(self.data.keys())
