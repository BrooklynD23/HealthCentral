"""
Seed script for the medical knowledge base.

Populates BiomarkerKnowledge, InterventionMapping, and BiomarkerRelationship
tables with curated reference data for the Lab Result Interpreter.

Data sources:
- LOINC (Logical Observation Identifiers Names and Codes)
- American Heart Association guidelines
- American Diabetes Association guidelines
- Endocrine Society guidelines
- Clinical laboratory reference standards

Usage:
    cd src/backend
    python -m scripts.seed_knowledge_base

Or via API (when implemented):
    POST /api/v1/admin/seed-knowledge-base
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Add parent directory to path for imports
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import async_session_maker, init_database
from models.knowledge_base import (
    BiomarkerKnowledge,
    InterventionMapping,
    BiomarkerRelationship,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


# =============================================================================
# BIOMARKER KNOWLEDGE DATA
# =============================================================================

BIOMARKER_DATA = [
    # =========================================================================
    # LIPID PANEL
    # =========================================================================
    {
        "analyte_canonical": "total_cholesterol",
        "display_name": "Total Cholesterol",
        "loinc_codes_json": json.dumps(["2093-3"]),
        "description": "Total cholesterol measures the total amount of cholesterol in your blood, including LDL (bad) cholesterol, HDL (good) cholesterol, and triglycerides.",
        "clinical_significance": "Cholesterol is essential for building cells and making vitamins and hormones. However, too much cholesterol can build up in your arteries and increase your risk of heart disease and stroke.",
        "normal_interpretation": "Your total cholesterol is in a healthy range. This suggests a lower risk of heart disease, though other factors like LDL and HDL levels are also important.",
        "high_interpretation": "Elevated total cholesterol may increase your risk of heart disease. Your healthcare provider will consider this alongside your LDL, HDL, and other risk factors to assess your cardiovascular health.",
        "low_interpretation": "Very low cholesterol is uncommon but may be associated with certain conditions. Your healthcare provider can help determine if further evaluation is needed.",
        "ref_range_adult_json": json.dumps({
            "default": {"desirable": [0, 200], "borderline_high": [200, 240], "high": [240, None]},
            "unit": "mg/dL"
        }),
        "common_causes_high_json": json.dumps([
            "Diet high in saturated fats",
            "Lack of physical activity",
            "Obesity",
            "Genetics (familial hypercholesterolemia)",
            "Hypothyroidism",
            "Diabetes"
        ]),
        "common_causes_low_json": json.dumps([
            "Hyperthyroidism",
            "Liver disease",
            "Malnutrition",
            "Certain medications"
        ]),
        "critical_low": None,
        "critical_high": 300.0,
        "standard_unit": "mg/dL",
        "unit_conversions_json": json.dumps({"mmol/L": 0.0259}),
        "category": "lipid",
        "panels_json": json.dumps(["lipid_panel", "cardiovascular"]),
        "sources_json": json.dumps([
            {"name": "American Heart Association", "url": "https://www.heart.org/en/health-topics/cholesterol"},
            {"name": "NCEP ATP III Guidelines", "type": "clinical_guideline"}
        ]),
    },
    {
        "analyte_canonical": "ldl_cholesterol",
        "display_name": "LDL Cholesterol",
        "loinc_codes_json": json.dumps(["2089-1", "13457-7"]),
        "description": "LDL (low-density lipoprotein) cholesterol is often called 'bad' cholesterol because it can build up in the walls of your arteries, forming plaques that narrow and harden them.",
        "clinical_significance": "LDL is a primary target for cholesterol-lowering treatment. High LDL increases the risk of atherosclerosis, heart attack, and stroke.",
        "normal_interpretation": "Your LDL cholesterol is at a healthy level. This is associated with lower cardiovascular risk.",
        "high_interpretation": "Elevated LDL cholesterol increases your risk of plaque buildup in arteries. Lifestyle changes and possibly medication may help reduce this risk.",
        "low_interpretation": "Low LDL is generally favorable for heart health. Very low levels are uncommon and usually not concerning unless associated with other conditions.",
        "ref_range_adult_json": json.dumps({
            "default": {"optimal": [0, 100], "near_optimal": [100, 130], "borderline_high": [130, 160], "high": [160, 190], "very_high": [190, None]},
            "unit": "mg/dL"
        }),
        "common_causes_high_json": json.dumps([
            "Diet high in saturated and trans fats",
            "Sedentary lifestyle",
            "Obesity",
            "Genetics",
            "Diabetes",
            "Hypothyroidism"
        ]),
        "common_causes_low_json": json.dumps([
            "Hyperthyroidism",
            "Liver disease",
            "Certain medications (statins)"
        ]),
        "critical_low": None,
        "critical_high": 190.0,
        "standard_unit": "mg/dL",
        "unit_conversions_json": json.dumps({"mmol/L": 0.0259}),
        "category": "lipid",
        "panels_json": json.dumps(["lipid_panel", "cardiovascular"]),
        "sources_json": json.dumps([
            {"name": "American Heart Association", "url": "https://www.heart.org/en/health-topics/cholesterol/about-cholesterol/ldl-bad-cholesterol"},
            {"name": "2018 AHA/ACC Cholesterol Guidelines", "type": "clinical_guideline"}
        ]),
    },
    {
        "analyte_canonical": "hdl_cholesterol",
        "display_name": "HDL Cholesterol",
        "loinc_codes_json": json.dumps(["2085-9"]),
        "description": "HDL (high-density lipoprotein) cholesterol is called 'good' cholesterol because it helps remove other forms of cholesterol from your bloodstream and transports them to the liver for disposal.",
        "clinical_significance": "Higher HDL levels are associated with lower cardiovascular risk. HDL acts as a protective factor against heart disease.",
        "normal_interpretation": "Your HDL cholesterol is at a healthy level, which helps protect against heart disease.",
        "high_interpretation": "High HDL is generally beneficial and associated with lower cardiovascular risk. Very high levels (>100 mg/dL) are rare and usually not concerning.",
        "low_interpretation": "Low HDL increases cardiovascular risk. Lifestyle factors like exercise, diet, and avoiding smoking can help raise HDL levels.",
        "ref_range_adult_json": json.dumps({
            "male": {"low": [0, 40], "normal": [40, 60], "optimal": [60, None]},
            "female": {"low": [0, 50], "normal": [50, 60], "optimal": [60, None]},
            "unit": "mg/dL"
        }),
        "common_causes_high_json": json.dumps([
            "Regular aerobic exercise",
            "Moderate alcohol consumption",
            "Genetics",
            "Certain medications"
        ]),
        "common_causes_low_json": json.dumps([
            "Sedentary lifestyle",
            "Smoking",
            "Obesity",
            "Poor diet",
            "Type 2 diabetes",
            "Metabolic syndrome"
        ]),
        "critical_low": 20.0,
        "critical_high": None,
        "standard_unit": "mg/dL",
        "unit_conversions_json": json.dumps({"mmol/L": 0.0259}),
        "category": "lipid",
        "panels_json": json.dumps(["lipid_panel", "cardiovascular"]),
        "sources_json": json.dumps([
            {"name": "American Heart Association", "url": "https://www.heart.org/en/health-topics/cholesterol/about-cholesterol/hdl-good-ldl-bad-cholesterol-and-triglycerides"},
        ]),
    },
    {
        "analyte_canonical": "triglycerides",
        "display_name": "Triglycerides",
        "loinc_codes_json": json.dumps(["2571-8"]),
        "description": "Triglycerides are the most common type of fat in your body. They come from foods, especially butter, oils, and other fats. Excess calories are also converted to triglycerides and stored in fat cells.",
        "clinical_significance": "High triglycerides contribute to hardening of the arteries and increase risk of heart disease, heart attack, and stroke. Very high levels can also cause pancreatitis.",
        "normal_interpretation": "Your triglyceride level is in a healthy range, which is good for your cardiovascular health.",
        "high_interpretation": "Elevated triglycerides increase cardiovascular risk. Diet modifications, exercise, and weight management can help lower triglycerides.",
        "low_interpretation": "Low triglycerides are generally not concerning and may indicate a healthy metabolism.",
        "ref_range_adult_json": json.dumps({
            "default": {"normal": [0, 150], "borderline_high": [150, 200], "high": [200, 500], "very_high": [500, None]},
            "unit": "mg/dL",
            "note": "Fasting sample preferred"
        }),
        "common_causes_high_json": json.dumps([
            "Excess calorie intake",
            "High carbohydrate diet",
            "Obesity",
            "Sedentary lifestyle",
            "Excessive alcohol",
            "Diabetes",
            "Hypothyroidism",
            "Certain medications"
        ]),
        "common_causes_low_json": json.dumps([
            "Low-fat diet",
            "Malnutrition",
            "Hyperthyroidism"
        ]),
        "critical_low": None,
        "critical_high": 500.0,
        "standard_unit": "mg/dL",
        "unit_conversions_json": json.dumps({"mmol/L": 0.0113}),
        "category": "lipid",
        "panels_json": json.dumps(["lipid_panel", "cardiovascular"]),
        "sources_json": json.dumps([
            {"name": "American Heart Association", "url": "https://www.heart.org/en/health-topics/cholesterol/about-cholesterol/triglycerides"},
        ]),
    },
    # =========================================================================
    # DIABETES / GLUCOSE
    # =========================================================================
    {
        "analyte_canonical": "glucose_fasting",
        "display_name": "Fasting Glucose",
        "loinc_codes_json": json.dumps(["1558-6", "2339-0"]),
        "description": "Fasting blood glucose measures the amount of sugar (glucose) in your blood after not eating for at least 8 hours. It's a primary screening test for diabetes.",
        "clinical_significance": "Blood glucose is the body's main source of energy. Abnormal levels can indicate diabetes, prediabetes, or other metabolic conditions.",
        "normal_interpretation": "Your fasting glucose is in the normal range, suggesting healthy blood sugar regulation.",
        "high_interpretation": "Elevated fasting glucose may indicate prediabetes or diabetes. Further testing and lifestyle modifications may be recommended.",
        "low_interpretation": "Low blood glucose (hypoglycemia) can cause symptoms like shakiness, confusion, and fatigue. Causes include certain medications, missed meals, or underlying conditions.",
        "ref_range_adult_json": json.dumps({
            "default": {"normal": [70, 100], "prediabetes": [100, 126], "diabetes": [126, None]},
            "unit": "mg/dL"
        }),
        "common_causes_high_json": json.dumps([
            "Diabetes mellitus",
            "Prediabetes",
            "Stress",
            "Certain medications (steroids)",
            "Cushing's syndrome",
            "Pancreatic disorders"
        ]),
        "common_causes_low_json": json.dumps([
            "Diabetes medications (insulin, sulfonylureas)",
            "Missed meals",
            "Excessive alcohol",
            "Liver disease",
            "Adrenal insufficiency"
        ]),
        "critical_low": 50.0,
        "critical_high": 400.0,
        "standard_unit": "mg/dL",
        "unit_conversions_json": json.dumps({"mmol/L": 0.0555}),
        "category": "diabetes",
        "panels_json": json.dumps(["cmp", "diabetes"]),
        "sources_json": json.dumps([
            {"name": "American Diabetes Association", "url": "https://diabetes.org/diabetes/a1c/diagnosis"},
        ]),
    },
    {
        "analyte_canonical": "hemoglobin_a1c",
        "display_name": "Hemoglobin A1c (HbA1c)",
        "loinc_codes_json": json.dumps(["4548-4", "17856-6"]),
        "description": "HbA1c measures your average blood sugar level over the past 2-3 months. It reflects how well blood sugar has been controlled over time.",
        "clinical_significance": "HbA1c is a key marker for diagnosing and monitoring diabetes. It helps assess long-term blood sugar control and risk of diabetes complications.",
        "normal_interpretation": "Your HbA1c indicates good blood sugar control over the past few months.",
        "high_interpretation": "Elevated HbA1c suggests higher average blood sugar levels. This may indicate prediabetes, diabetes, or suboptimal diabetes management.",
        "low_interpretation": "Low HbA1c is generally good but very low levels in diabetics may indicate frequent hypoglycemia, which can be dangerous.",
        "ref_range_adult_json": json.dumps({
            "default": {"normal": [0, 5.7], "prediabetes": [5.7, 6.5], "diabetes": [6.5, None]},
            "unit": "%",
            "diabetes_target": {"general": [0, 7.0], "individualized": "May vary based on patient factors"}
        }),
        "common_causes_high_json": json.dumps([
            "Diabetes (Type 1 or Type 2)",
            "Prediabetes",
            "Poor diabetes management",
            "Certain hemoglobin variants"
        ]),
        "common_causes_low_json": json.dumps([
            "Recent blood loss or transfusion",
            "Hemolytic anemia",
            "Chronic kidney disease",
            "Certain hemoglobin variants"
        ]),
        "critical_low": None,
        "critical_high": 10.0,
        "standard_unit": "%",
        "unit_conversions_json": json.dumps({"mmol/mol": 10.929}),
        "category": "diabetes",
        "panels_json": json.dumps(["diabetes"]),
        "sources_json": json.dumps([
            {"name": "American Diabetes Association", "url": "https://diabetes.org/diabetes/a1c"},
            {"name": "ADA Standards of Care 2024", "type": "clinical_guideline"}
        ]),
    },
    # =========================================================================
    # COMPLETE BLOOD COUNT (CBC)
    # =========================================================================
    {
        "analyte_canonical": "hemoglobin",
        "display_name": "Hemoglobin",
        "loinc_codes_json": json.dumps(["718-7"]),
        "description": "Hemoglobin is a protein in red blood cells that carries oxygen from your lungs to the rest of your body and returns carbon dioxide to your lungs to be exhaled.",
        "clinical_significance": "Hemoglobin levels help diagnose anemia, polycythemia, and assess overall oxygen-carrying capacity of blood.",
        "normal_interpretation": "Your hemoglobin is in the normal range, indicating healthy oxygen-carrying capacity.",
        "high_interpretation": "Elevated hemoglobin may indicate dehydration, lung disease, heart disease, or polycythemia. Your healthcare provider may recommend further evaluation.",
        "low_interpretation": "Low hemoglobin indicates anemia, which can cause fatigue, weakness, and shortness of breath. There are many potential causes including iron deficiency, vitamin deficiencies, or chronic diseases.",
        "ref_range_adult_json": json.dumps({
            "male": {"low": [0, 13.5], "normal": [13.5, 17.5], "high": [17.5, None]},
            "female": {"low": [0, 12.0], "normal": [12.0, 16.0], "high": [16.0, None]},
            "unit": "g/dL"
        }),
        "common_causes_high_json": json.dumps([
            "Dehydration",
            "Chronic lung disease",
            "Heart disease",
            "Polycythemia vera",
            "Living at high altitude",
            "Smoking"
        ]),
        "common_causes_low_json": json.dumps([
            "Iron deficiency anemia",
            "Vitamin B12 or folate deficiency",
            "Chronic disease",
            "Blood loss",
            "Bone marrow disorders",
            "Kidney disease"
        ]),
        "critical_low": 7.0,
        "critical_high": 20.0,
        "standard_unit": "g/dL",
        "unit_conversions_json": json.dumps({"g/L": 10.0}),
        "category": "cbc",
        "panels_json": json.dumps(["cbc"]),
        "sources_json": json.dumps([
            {"name": "WHO Hemoglobin Guidelines", "type": "clinical_guideline"},
        ]),
    },
    {
        "analyte_canonical": "wbc",
        "display_name": "White Blood Cell Count (WBC)",
        "loinc_codes_json": json.dumps(["6690-2"]),
        "description": "White blood cells (leukocytes) are part of your immune system. They help your body fight infections and other diseases.",
        "clinical_significance": "WBC count helps detect infections, immune disorders, blood cancers, and monitor response to treatments.",
        "normal_interpretation": "Your white blood cell count is in the normal range, suggesting your immune system is functioning normally.",
        "high_interpretation": "Elevated WBC (leukocytosis) often indicates your body is fighting an infection. Other causes include inflammation, stress, medications, or rarely blood cancers.",
        "low_interpretation": "Low WBC (leukopenia) can increase infection risk. Causes include viral infections, bone marrow problems, autoimmune conditions, or certain medications.",
        "ref_range_adult_json": json.dumps({
            "default": {"low": [0, 4.5], "normal": [4.5, 11.0], "high": [11.0, None]},
            "unit": "10^3/uL"
        }),
        "common_causes_high_json": json.dumps([
            "Bacterial infections",
            "Inflammation",
            "Physical or emotional stress",
            "Allergic reactions",
            "Leukemia",
            "Corticosteroid medications"
        ]),
        "common_causes_low_json": json.dumps([
            "Viral infections",
            "Bone marrow disorders",
            "Autoimmune diseases",
            "Chemotherapy",
            "Certain medications"
        ]),
        "critical_low": 2.0,
        "critical_high": 30.0,
        "standard_unit": "10^3/uL",
        "unit_conversions_json": json.dumps({"10^9/L": 1.0}),
        "category": "cbc",
        "panels_json": json.dumps(["cbc"]),
        "sources_json": json.dumps([
            {"name": "Laboratory Medicine Practice Guidelines", "type": "clinical_guideline"},
        ]),
    },
    {
        "analyte_canonical": "platelets",
        "display_name": "Platelet Count",
        "loinc_codes_json": json.dumps(["777-3"]),
        "description": "Platelets (thrombocytes) are blood cells that help your blood clot. They stick together to form clots that stop bleeding when you have a cut or injury.",
        "clinical_significance": "Platelet count helps diagnose bleeding disorders, clotting problems, bone marrow diseases, and monitor effects of certain treatments.",
        "normal_interpretation": "Your platelet count is in the normal range, indicating normal blood clotting ability.",
        "high_interpretation": "Elevated platelets (thrombocytosis) can increase clotting risk. Causes include inflammation, infection, iron deficiency, or bone marrow disorders.",
        "low_interpretation": "Low platelets (thrombocytopenia) can increase bleeding risk. Causes include viral infections, certain medications, autoimmune conditions, or bone marrow problems.",
        "ref_range_adult_json": json.dumps({
            "default": {"low": [0, 150], "normal": [150, 400], "high": [400, None]},
            "unit": "10^3/uL"
        }),
        "common_causes_high_json": json.dumps([
            "Inflammation or infection",
            "Iron deficiency anemia",
            "Splenectomy",
            "Cancer",
            "Essential thrombocythemia"
        ]),
        "common_causes_low_json": json.dumps([
            "Viral infections",
            "Autoimmune disorders (ITP)",
            "Medications (heparin)",
            "Bone marrow disorders",
            "Liver disease with splenomegaly",
            "Chemotherapy"
        ]),
        "critical_low": 50.0,
        "critical_high": 1000.0,
        "standard_unit": "10^3/uL",
        "unit_conversions_json": json.dumps({"10^9/L": 1.0}),
        "category": "cbc",
        "panels_json": json.dumps(["cbc"]),
        "sources_json": json.dumps([
            {"name": "Laboratory Medicine Practice Guidelines", "type": "clinical_guideline"},
        ]),
    },
    # =========================================================================
    # THYROID
    # =========================================================================
    {
        "analyte_canonical": "tsh",
        "display_name": "TSH (Thyroid Stimulating Hormone)",
        "loinc_codes_json": json.dumps(["3016-3"]),
        "description": "TSH is produced by the pituitary gland and controls how much thyroid hormone your thyroid gland makes. It's the most sensitive test for thyroid function.",
        "clinical_significance": "TSH is the primary screening test for thyroid disorders. It helps diagnose hypothyroidism (underactive thyroid) and hyperthyroidism (overactive thyroid).",
        "normal_interpretation": "Your TSH is in the normal range, suggesting your thyroid is functioning normally.",
        "high_interpretation": "Elevated TSH typically indicates your thyroid is underactive (hypothyroidism). Your pituitary is producing more TSH to try to stimulate the thyroid.",
        "low_interpretation": "Low TSH typically indicates your thyroid is overactive (hyperthyroidism). Your pituitary is producing less TSH because thyroid hormone levels are high.",
        "ref_range_adult_json": json.dumps({
            "default": {"low": [0, 0.4], "normal": [0.4, 4.0], "high": [4.0, None]},
            "unit": "mIU/L",
            "note": "Reference ranges may vary by laboratory and age"
        }),
        "common_causes_high_json": json.dumps([
            "Primary hypothyroidism (Hashimoto's)",
            "Iodine deficiency",
            "TSH-secreting pituitary adenoma (rare)",
            "Recovery from severe illness"
        ]),
        "common_causes_low_json": json.dumps([
            "Hyperthyroidism (Graves' disease)",
            "Excessive thyroid medication",
            "Pituitary dysfunction",
            "Early pregnancy"
        ]),
        "critical_low": 0.1,
        "critical_high": 10.0,
        "standard_unit": "mIU/L",
        "unit_conversions_json": json.dumps({"uIU/mL": 1.0}),
        "category": "thyroid",
        "panels_json": json.dumps(["thyroid"]),
        "sources_json": json.dumps([
            {"name": "American Thyroid Association", "url": "https://www.thyroid.org/thyroid-function-tests/"},
        ]),
    },
    # =========================================================================
    # KIDNEY FUNCTION
    # =========================================================================
    {
        "analyte_canonical": "creatinine",
        "display_name": "Creatinine",
        "loinc_codes_json": json.dumps(["2160-0"]),
        "description": "Creatinine is a waste product from normal muscle metabolism. Healthy kidneys filter creatinine from the blood and excrete it in urine.",
        "clinical_significance": "Creatinine is a key marker of kidney function. Elevated levels may indicate reduced kidney function. It's used to calculate eGFR (estimated glomerular filtration rate).",
        "normal_interpretation": "Your creatinine level is normal, suggesting your kidneys are filtering waste effectively.",
        "high_interpretation": "Elevated creatinine may indicate reduced kidney function. However, levels can also be affected by muscle mass, diet, and hydration. Your healthcare provider will interpret this in context.",
        "low_interpretation": "Low creatinine is usually not concerning and may reflect decreased muscle mass or other factors.",
        "ref_range_adult_json": json.dumps({
            "male": {"normal": [0.7, 1.3]},
            "female": {"normal": [0.6, 1.1]},
            "unit": "mg/dL"
        }),
        "common_causes_high_json": json.dumps([
            "Chronic kidney disease",
            "Acute kidney injury",
            "Dehydration",
            "High protein diet",
            "Intense exercise",
            "Certain medications"
        ]),
        "common_causes_low_json": json.dumps([
            "Low muscle mass",
            "Pregnancy",
            "Severe liver disease"
        ]),
        "critical_low": None,
        "critical_high": 10.0,
        "standard_unit": "mg/dL",
        "unit_conversions_json": json.dumps({"umol/L": 88.4}),
        "category": "kidney",
        "panels_json": json.dumps(["cmp", "kidney"]),
        "sources_json": json.dumps([
            {"name": "National Kidney Foundation", "url": "https://www.kidney.org/atoz/content/what-creatinine"},
        ]),
    },
    # =========================================================================
    # VITAMINS
    # =========================================================================
    {
        "analyte_canonical": "vitamin_d",
        "display_name": "Vitamin D (25-Hydroxy)",
        "loinc_codes_json": json.dumps(["1989-3", "62292-8"]),
        "description": "Vitamin D is essential for calcium absorption and bone health. Your body makes it when skin is exposed to sunlight, and you can get it from certain foods and supplements.",
        "clinical_significance": "Vitamin D deficiency is common and can lead to bone disorders, muscle weakness, and has been linked to various health conditions including immune function.",
        "normal_interpretation": "Your vitamin D level is adequate for bone and overall health.",
        "high_interpretation": "Very high vitamin D (usually from excessive supplementation) can cause calcium buildup and adverse effects. This is uncommon with typical supplementation.",
        "low_interpretation": "Low vitamin D is common, especially in winter months or with limited sun exposure. Supplementation is often recommended to reach adequate levels.",
        "ref_range_adult_json": json.dumps({
            "default": {"deficient": [0, 20], "insufficient": [20, 30], "sufficient": [30, 100], "potentially_toxic": [100, None]},
            "unit": "ng/mL"
        }),
        "common_causes_high_json": json.dumps([
            "Excessive supplementation",
            "Granulomatous diseases"
        ]),
        "common_causes_low_json": json.dumps([
            "Limited sun exposure",
            "Dark skin pigmentation",
            "Malabsorption disorders",
            "Obesity",
            "Liver or kidney disease",
            "Certain medications"
        ]),
        "critical_low": None,
        "critical_high": 150.0,
        "standard_unit": "ng/mL",
        "unit_conversions_json": json.dumps({"nmol/L": 2.496}),
        "category": "vitamin",
        "panels_json": json.dumps(["vitamin"]),
        "sources_json": json.dumps([
            {"name": "Endocrine Society Clinical Practice Guideline", "type": "clinical_guideline"},
        ]),
    },
]


# =============================================================================
# INTERVENTION MAPPINGS DATA
# =============================================================================

INTERVENTION_DATA = [
    # LDL Cholesterol - High
    {
        "analyte_canonical": "ldl_cholesterol",
        "condition_type": "high",
        "category": "diet",
        "intervention_title": "Reduce Saturated Fat Intake",
        "intervention_text": "Consider limiting saturated fat to less than 7% of daily calories. This may help lower LDL cholesterol levels. Focus on replacing saturated fats with unsaturated fats.",
        "rationale": "Saturated fats raise LDL cholesterol by reducing the liver's ability to remove LDL from the bloodstream.",
        "strength_of_evidence": "strong",
        "details_json": json.dumps({
            "foods_to_limit": ["fatty meats", "full-fat dairy", "coconut oil", "palm oil"],
            "foods_to_increase": ["olive oil", "nuts", "avocados", "fatty fish"]
        }),
        "contraindications_json": None,
        "priority": 1,
        "sources_json": json.dumps([
            {"name": "AHA Diet Recommendations", "url": "https://www.heart.org/en/healthy-living/healthy-eating"}
        ]),
    },
    {
        "analyte_canonical": "ldl_cholesterol",
        "condition_type": "high",
        "category": "diet",
        "intervention_title": "Increase Soluble Fiber",
        "intervention_text": "Consider increasing soluble fiber intake to 10-25 grams per day. Soluble fiber may help reduce LDL cholesterol absorption.",
        "rationale": "Soluble fiber binds to cholesterol in the digestive system and helps remove it from the body before it enters the bloodstream.",
        "strength_of_evidence": "strong",
        "details_json": json.dumps({
            "good_sources": ["oatmeal", "beans", "lentils", "apples", "citrus fruits", "psyllium"]
        }),
        "contraindications_json": None,
        "priority": 2,
        "sources_json": json.dumps([
            {"name": "NCEP ATP III Guidelines", "type": "clinical_guideline"}
        ]),
    },
    {
        "analyte_canonical": "ldl_cholesterol",
        "condition_type": "high",
        "category": "exercise",
        "intervention_title": "Regular Aerobic Exercise",
        "intervention_text": "Consider at least 150 minutes of moderate-intensity aerobic exercise per week. Regular physical activity may help improve your cholesterol profile.",
        "rationale": "Exercise can help raise HDL cholesterol and may modestly lower LDL cholesterol, especially when combined with weight loss.",
        "strength_of_evidence": "moderate",
        "details_json": json.dumps({
            "examples": ["brisk walking", "cycling", "swimming", "jogging"],
            "frequency": "Most days of the week"
        }),
        "contraindications_json": json.dumps(["Consult your doctor before starting a new exercise program, especially if you have heart disease or other health conditions"]),
        "priority": 3,
        "sources_json": json.dumps([
            {"name": "AHA Physical Activity Recommendations", "url": "https://www.heart.org/en/healthy-living/fitness"}
        ]),
    },
    # HDL Cholesterol - Low
    {
        "analyte_canonical": "hdl_cholesterol",
        "condition_type": "low",
        "category": "exercise",
        "intervention_title": "Regular Aerobic Exercise",
        "intervention_text": "Consider increasing aerobic exercise to raise HDL cholesterol. Aim for at least 150 minutes of moderate-intensity exercise per week.",
        "rationale": "Regular aerobic exercise is one of the most effective lifestyle changes for raising HDL cholesterol.",
        "strength_of_evidence": "strong",
        "details_json": json.dumps({
            "examples": ["brisk walking", "running", "cycling", "swimming"],
            "optimal": "30 minutes, 5 days per week"
        }),
        "contraindications_json": json.dumps(["Consult your doctor before starting a new exercise program"]),
        "priority": 1,
        "sources_json": json.dumps([
            {"name": "American Heart Association", "url": "https://www.heart.org/en/healthy-living/fitness"}
        ]),
    },
    {
        "analyte_canonical": "hdl_cholesterol",
        "condition_type": "low",
        "category": "lifestyle",
        "intervention_title": "Quit Smoking",
        "intervention_text": "If you smoke, quitting may help raise your HDL cholesterol. HDL levels often improve within weeks of quitting.",
        "rationale": "Smoking lowers HDL cholesterol. Quitting can raise HDL by up to 10%.",
        "strength_of_evidence": "strong",
        "details_json": None,
        "contraindications_json": None,
        "priority": 2,
        "sources_json": json.dumps([
            {"name": "American Heart Association", "url": "https://www.heart.org/en/healthy-living/healthy-lifestyle/quit-smoking-tobacco"}
        ]),
    },
    # HbA1c - High
    {
        "analyte_canonical": "hemoglobin_a1c",
        "condition_type": "high",
        "category": "diet",
        "intervention_title": "Reduce Refined Carbohydrates",
        "intervention_text": "Consider limiting refined carbohydrates and sugary foods. Choosing whole grains and fiber-rich foods may help improve blood sugar control.",
        "rationale": "Refined carbohydrates are quickly converted to blood sugar, leading to spikes that contribute to higher HbA1c over time.",
        "strength_of_evidence": "strong",
        "details_json": json.dumps({
            "foods_to_limit": ["white bread", "white rice", "sugary drinks", "sweets", "pastries"],
            "foods_to_choose": ["whole grains", "vegetables", "legumes", "nuts"]
        }),
        "contraindications_json": None,
        "priority": 1,
        "sources_json": json.dumps([
            {"name": "American Diabetes Association", "url": "https://diabetes.org/healthy-living/recipes-nutrition"}
        ]),
    },
    {
        "analyte_canonical": "hemoglobin_a1c",
        "condition_type": "high",
        "category": "exercise",
        "intervention_title": "Regular Physical Activity",
        "intervention_text": "Consider at least 150 minutes of moderate-intensity exercise per week. Physical activity helps your body use insulin more effectively.",
        "rationale": "Exercise improves insulin sensitivity, allowing cells to better use available glucose and lower blood sugar levels.",
        "strength_of_evidence": "strong",
        "details_json": json.dumps({
            "types": ["aerobic exercise", "resistance training"],
            "note": "Both types of exercise are beneficial for blood sugar control"
        }),
        "contraindications_json": json.dumps(["Check blood sugar before and after exercise if taking diabetes medications", "Consult your doctor about exercise precautions"]),
        "priority": 2,
        "sources_json": json.dumps([
            {"name": "ADA Standards of Care", "type": "clinical_guideline"}
        ]),
    },
    # Vitamin D - Low
    {
        "analyte_canonical": "vitamin_d",
        "condition_type": "low",
        "category": "supplement",
        "intervention_title": "Vitamin D Supplementation",
        "intervention_text": "Consider discussing vitamin D supplementation with your healthcare provider. The appropriate dose depends on your current level and individual factors.",
        "rationale": "When diet and sun exposure are insufficient, supplements can help achieve adequate vitamin D levels.",
        "strength_of_evidence": "strong",
        "details_json": json.dumps({
            "note": "Dosing should be individualized based on deficiency severity",
            "forms": ["D3 (cholecalciferol) is generally preferred"]
        }),
        "contraindications_json": json.dumps(["Discuss with your doctor, especially if you have kidney disease, hypercalcemia, or take certain medications"]),
        "priority": 1,
        "sources_json": json.dumps([
            {"name": "Endocrine Society Clinical Practice Guideline", "type": "clinical_guideline"}
        ]),
    },
    {
        "analyte_canonical": "vitamin_d",
        "condition_type": "low",
        "category": "lifestyle",
        "intervention_title": "Safe Sun Exposure",
        "intervention_text": "Consider brief sun exposure (10-30 minutes) several times per week, depending on skin type and location. Your body produces vitamin D when skin is exposed to UVB rays.",
        "rationale": "Sunlight is the most natural source of vitamin D. The amount needed varies based on skin pigmentation, latitude, and season.",
        "strength_of_evidence": "moderate",
        "details_json": json.dumps({
            "note": "Balance vitamin D production with skin cancer risk",
            "factors": ["Darker skin requires more sun exposure", "Higher latitudes have less UVB in winter"]
        }),
        "contraindications_json": json.dumps(["Avoid excessive sun exposure", "Use sun protection to prevent skin cancer", "Some people should avoid sun exposure entirely - consult your doctor"]),
        "priority": 2,
        "sources_json": json.dumps([
            {"name": "NIH Office of Dietary Supplements", "url": "https://ods.od.nih.gov/factsheets/VitaminD-Consumer/"}
        ]),
    },
]


# =============================================================================
# BIOMARKER RELATIONSHIPS DATA
# =============================================================================

RELATIONSHIP_DATA = [
    {
        "primary_analyte": "total_cholesterol",
        "related_analyte": "hdl_cholesterol",
        "relationship_type": "ratio",
        "description": "The Total Cholesterol to HDL ratio is calculated by dividing total cholesterol by HDL cholesterol.",
        "clinical_significance": "This ratio is a useful indicator of cardiovascular risk. A lower ratio indicates better heart health.",
        "ratio_calculation": "total_cholesterol / hdl_cholesterol",
        "ratio_target_range_json": json.dumps({
            "optimal": [0, 3.5],
            "normal": [3.5, 5.0],
            "borderline": [5.0, 6.0],
            "high_risk": [6.0, None]
        }),
        "abnormal_interpretation": "A high Total/HDL ratio suggests increased cardiovascular risk. This may mean total cholesterol is too high, HDL is too low, or both.",
        "panel_name": "lipid_panel",
    },
    {
        "primary_analyte": "ldl_cholesterol",
        "related_analyte": "hdl_cholesterol",
        "relationship_type": "ratio",
        "description": "The LDL to HDL ratio compares 'bad' cholesterol to 'good' cholesterol.",
        "clinical_significance": "This ratio is another predictor of cardiovascular risk. A lower ratio is better.",
        "ratio_calculation": "ldl_cholesterol / hdl_cholesterol",
        "ratio_target_range_json": json.dumps({
            "optimal": [0, 2.0],
            "normal": [2.0, 3.5],
            "borderline": [3.5, 4.5],
            "high_risk": [4.5, None]
        }),
        "abnormal_interpretation": "A high LDL/HDL ratio indicates increased cardiovascular risk. Ideally, LDL should be low and HDL should be high.",
        "panel_name": "lipid_panel",
    },
    {
        "primary_analyte": "ldl_cholesterol",
        "related_analyte": "total_cholesterol",
        "relationship_type": "panel_member",
        "description": "LDL cholesterol is a component of total cholesterol.",
        "clinical_significance": "LDL typically makes up the largest portion of total cholesterol. High LDL is the main driver of elevated total cholesterol in most people.",
        "ratio_calculation": None,
        "ratio_target_range_json": None,
        "abnormal_interpretation": None,
        "panel_name": "lipid_panel",
    },
    {
        "primary_analyte": "hdl_cholesterol",
        "related_analyte": "total_cholesterol",
        "relationship_type": "panel_member",
        "description": "HDL cholesterol is a component of total cholesterol.",
        "clinical_significance": "Unlike LDL, higher HDL levels are protective. HDL helps remove cholesterol from arteries.",
        "ratio_calculation": None,
        "ratio_target_range_json": None,
        "abnormal_interpretation": None,
        "panel_name": "lipid_panel",
    },
    {
        "primary_analyte": "triglycerides",
        "related_analyte": "total_cholesterol",
        "relationship_type": "panel_member",
        "description": "Triglycerides contribute to the total cholesterol calculation.",
        "clinical_significance": "Triglycerides are included in lipid panels because they independently contribute to cardiovascular risk.",
        "ratio_calculation": None,
        "ratio_target_range_json": None,
        "abnormal_interpretation": None,
        "panel_name": "lipid_panel",
    },
    {
        "primary_analyte": "tsh",
        "related_analyte": "free_t4",
        "relationship_type": "inverse_correlation",
        "description": "TSH and Free T4 have an inverse relationship in thyroid function.",
        "clinical_significance": "When Free T4 is low, TSH rises to stimulate more thyroid hormone production. When Free T4 is high, TSH falls. This feedback loop is key to diagnosing thyroid disorders.",
        "ratio_calculation": None,
        "ratio_target_range_json": None,
        "abnormal_interpretation": "If TSH is high and Free T4 is low, this suggests hypothyroidism. If TSH is low and Free T4 is high, this suggests hyperthyroidism.",
        "panel_name": "thyroid",
    },
    {
        "primary_analyte": "glucose_fasting",
        "related_analyte": "hemoglobin_a1c",
        "relationship_type": "confirms",
        "description": "Fasting glucose and HbA1c both measure aspects of blood sugar control.",
        "clinical_significance": "Fasting glucose provides a snapshot of current blood sugar, while HbA1c reflects average blood sugar over 2-3 months. Together they provide a complete picture of glucose control.",
        "ratio_calculation": None,
        "ratio_target_range_json": None,
        "abnormal_interpretation": "If both are elevated, this strongly supports a diagnosis of diabetes. If they're discordant, further evaluation may be needed.",
        "panel_name": "diabetes",
    },
]


# =============================================================================
# SEEDING FUNCTIONS
# =============================================================================

async def seed_biomarker_knowledge(session: AsyncSession) -> int:
    """Seed biomarker knowledge data."""
    count = 0
    for data in BIOMARKER_DATA:
        # Check if already exists
        result = await session.execute(
            select(BiomarkerKnowledge).where(
                BiomarkerKnowledge.analyte_canonical == data["analyte_canonical"]
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"Biomarker {data['analyte_canonical']} already exists, skipping")
            continue

        biomarker = BiomarkerKnowledge(
            id=generate_uuid(),
            **data
        )
        session.add(biomarker)
        count += 1
        logger.info(f"Added biomarker: {data['analyte_canonical']}")

    await session.commit()
    return count


async def seed_intervention_mappings(session: AsyncSession) -> int:
    """Seed intervention mapping data."""
    count = 0
    for data in INTERVENTION_DATA:
        # Check if similar intervention exists
        result = await session.execute(
            select(InterventionMapping).where(
                InterventionMapping.analyte_canonical == data["analyte_canonical"],
                InterventionMapping.condition_type == data["condition_type"],
                InterventionMapping.intervention_title == data["intervention_title"],
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"Intervention {data['intervention_title']} for {data['analyte_canonical']} already exists, skipping")
            continue

        intervention = InterventionMapping(
            id=generate_uuid(),
            is_active=True,
            **data
        )
        session.add(intervention)
        count += 1
        logger.info(f"Added intervention: {data['intervention_title']} for {data['analyte_canonical']}")

    await session.commit()
    return count


async def seed_biomarker_relationships(session: AsyncSession) -> int:
    """Seed biomarker relationship data."""
    count = 0
    for data in RELATIONSHIP_DATA:
        # Check if relationship exists
        result = await session.execute(
            select(BiomarkerRelationship).where(
                BiomarkerRelationship.primary_analyte == data["primary_analyte"],
                BiomarkerRelationship.related_analyte == data["related_analyte"],
                BiomarkerRelationship.relationship_type == data["relationship_type"],
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"Relationship {data['primary_analyte']} -> {data['related_analyte']} already exists, skipping")
            continue

        relationship = BiomarkerRelationship(
            id=generate_uuid(),
            **data
        )
        session.add(relationship)
        count += 1
        logger.info(f"Added relationship: {data['primary_analyte']} -> {data['related_analyte']}")

    await session.commit()
    return count


async def seed_all(skip_db_init: bool = False) -> dict:
    """Seed all knowledge base data.

    Args:
        skip_db_init: When True, skip calling init_database() because the caller
                      (e.g. main.py lifespan) has already initialised the engine.
                      Defaults to False so standalone invocation still works.
    """
    # Initialize database unless the caller already did it
    if not skip_db_init:
        await init_database()

    results = {
        "biomarkers": 0,
        "interventions": 0,
        "relationships": 0,
    }

    async with async_session_maker() as session:
        results["biomarkers"] = await seed_biomarker_knowledge(session)
        results["interventions"] = await seed_intervention_mappings(session)
        results["relationships"] = await seed_biomarker_relationships(session)

    logger.info(f"Seeding complete: {results}")
    return results


if __name__ == "__main__":
    print("Seeding HealthCentral Knowledge Base...")
    print("=" * 50)

    results = asyncio.run(seed_all())

    print("=" * 50)
    print(f"Seeding complete!")
    print(f"  Biomarkers added: {results['biomarkers']}")
    print(f"  Interventions added: {results['interventions']}")
    print(f"  Relationships added: {results['relationships']}")
