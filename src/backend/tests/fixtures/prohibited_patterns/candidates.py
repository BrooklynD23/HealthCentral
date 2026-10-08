"""Candidate PROHIBITED_PATTERNS lists, for MEASUREMENT ONLY.

Nothing in product code imports this module. The live list is
``InterpretationSafetyGuard.PROHIBITED_PATTERNS`` in
``modules/interpret_safety.py`` (ask-first); it is not edited by the phase that
added this file (owner row PARA-1-REDO: "Measure first").

Each entry: (id, pattern, category name). Lists are compiled with
``re.IGNORECASE`` only, exactly as the product compiles the live list.

``PLAN_18`` is copied character for character from the ``candidates.py``
listing in docs/plans/2026-10-04-PROHIBITED-PARAPHRASE.md.
"""

COND = r"\w*(?:itis|osis|emia|aemia|ism|disease|disorder|deficiency|failure|syndrome|cancer|diabetes|infection|damage)\b"

PLAN_18 = [
    # --- replacements of existing patterns (false-positive fixes) ---
    ("R1", r"\b(?:you|you've|you\s+have\s+been)\s+(?:diagnosed with|have|got)\s+(?:an?\s+)?" + COND, "diagnostic_language"),  # replaces "you have \w+"
    ("K2", r"\b(this (means|indicates|confirms) you have)\b", "diagnostic_language"),
    ("K3", r"\b(definitely|certainly|clearly) (have|indicates?|shows?)\b", "certainty_claims"),
    ("K4", r"\btake\s+\d+\s*(mg|mcg|g|ml|units?)\b", "dosing_recommendation"),
    ("K5", r"\b(prescribe|prescription|should take|must take|need to take)\b", "medication_advice"),
    ("K6", r"\b(medication dosage|dose adjustment|increase.*dose|decrease.*dose)\b", "dosing_recommendation"),
    ("K7", r"\b(start taking|stop taking|discontinue)\s+\w+", "medication_advice"),
    ("R8", r"\b(always means|never means|absolutely)\b|\b100\s?%", "certainty_claims"),   # fixes the 100% boundary bug
    ("R9", r"\b(guaranteed|definitely|certainly|without a doubt|no question|no doubt)\b", "certainty_claims"),  # drops bare "certain"/"definite"
    ("K10", r"\b(call 911|go to (the )?ER|emergency room|seek immediate)\b", "emergency_advice"),
    ("K11", r"\b(medical emergency|life.?threatening)\b", "emergency_advice"),
    # --- additions (miss fixes) ---
    ("A1", r"\byou\s+(?:likely|probably|possibly|may|might|could)\s+(?:have|be suffering from)\s+(?:an?\s+)?" + COND, "diagnostic_language"),
    ("A2b", r"\b(?:consistent with|suggestive of|diagnostic of|points? to|confirms?)\s+(?:an?\s+)?(?:[\w-]+\s+)?" + COND, "diagnostic_language"),  # no "indicate": +6 FPs on hedged KB text (measured)
    ("A3", r"\byou(?:'re| are)\s+(?:diabetic|prediabetic|anemic|anaemic|hypothyroid|hyperthyroid)\b|\byou(?:'ve)?\s+got\s+\w+", "diagnostic_language"),
    ("A4", r"\b(?:take|try|use|be on|dose of|increase\s+\w+\s+to)\b[^.]{0,40}?\b\d[\d,.]*\s*(?:mg|mcg|µg|iu|units?|ml)\b", "dosing_recommendation"),
    ("A5", r"\b(?:double|halve|cut)\s+(?:your\s+)?(?:\w+\s+)?dose\b|\bdose\s+in\s+half\b", "dosing_recommendation"),
    ("A6", r"\b(?:should|consider|need to|must|wise to)\s+(?:\w+\s+){0,2}?(?:start|begin|stop|switch|go on)\w*\b|(?:^|[.!?]\s+)(?:begin|start|stop|switch to|discontinue)\b", "medication_advice"),
    ("A7", r"\b(?:emergency department|get to (?:a|the) hospital|go to (?:the )?hospital)\b", "emergency_advice"),
]
