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


# ---------------------------------------------------------------------------
# Revised candidates (Wave 4 L1-A, 2026-10-08). Derived on the in-sample
# corpus, the must-not-regress set, the product must-allow texts and the
# held-out DEV split only. Frozen in git BEFORE the sealed held-out FINAL split
# was first measured; the figures on FINAL are the out-of-sample figures.
#
# Ids: K<n> = pattern n of the live list, kept character for character.
# D = diagnosis, T = certainty, O = dosing, M = medication, E = emergency.
# The live "you have \w+" (pattern 1) and bare "definite/certain" (pattern 9)
# and "100%" (pattern 8) are the only live patterns that are changed.
# ---------------------------------------------------------------------------
# Sentence start (the product compiles with re.IGNORECASE only, so "^" is the
# start of the whole answer; newlines and bullets are handled explicitly).
SENT = r"(?:^|(?<=[.!?;:\n]))"
# From the sentence start up to the match, no negation / limit word.
NONEG = r"(?:(?!\b(?:not|never|no|nor|neither|cannot|can't|won't|don't|doesn't|isn't|aren't|unable|whether|only|none|nothing|without|rule out|rather than)\b)[^.!?\n])*?"
ASSERT = SENT + NONEG
# Start of an instruction: sentence / bullet start, or an advice lead-in.
IMP = (r"(?:^|[.!?;:\n]\s*|[-*•]\s*|\b\d[.)]\s+|\b(?:and|then|please|just|also|so|now|safely|should|ought to|need to|have to|must|"
       r"can|could|may want to|might want to|consider|recommend|suggest|advise|idea to|help to|wise to|best to|better to|time to|want to|you to|try|i'd|i would)\s+(?:probably\s+|definitely\s+|really\s+|simply\s+|to\s+)?)")
COND = (r"(?:(?!diagnosis|prognosis|analysis|basis|emphasis|metabolism|mechanism|organism)\w*(?:itis|osis|emia|aemia|uria|pathy|oma|ism|penia|philia|megaly)|disease|disorder|deficiency|failure|syndrome|cancer|diabetes|infection|"
        r"damage|injury|an[ae]?emia|hypertension|hypotension|high blood pressure|high cholesterol|thyroid|resistance|bleeding|"
        r"tumou?r|lupus|gout|arthritis|hepatitis|leuk[ae]?emia|overload|dehydration|insufficiency|fatty liver|stroke|heart attack|clot|"
        r"sepsis|malnutrition|obesity|condition)\b")
STATE = (r"(?:(?:pre-?)?diabetic|an[ae]?emic|hypothyroid|hyperthyroid|dehydrated|deficient|malnourished|septic|jaundiced|obese|"
         r"insulin[- ]resistant|immunocompromised|hypertensive|in (?:[\w-]+\s+){0,2}(?:kidney|renal|liver|heart|organ) failure)\b")
DRUG = (r"(?:\w*(?:statin|pril|sartan|olol|formin|oxine|farin|parin|gliptin|gliflozin|glutide|dipine|azole|mycin|cillin|cycline|floxacin|"
        r"prazole|tidine|semide|thiazide|lactone|mab)|insulin|aspirin|ibuprofen|acetaminophen|paracetamol|lipitor|crestor|zocor|synthroid|"
        r"glucophage|ozempic|lantus|coumadin|eliquis|xarelto|lasix|plavix|ezetimibe|allopurinol|prednisone|iron|vitamin\s+\w+|b12|"
        r"folic acid|folate|magnesium|potassium|calcium|zinc|fish oil|omega-3|probiotics?|antibiotics?|anticoagulants?|blood thinners?|"
        r"supplements?|medications?|medicines?|meds|pills?|tablets?|capsules?|doses?|dosage|injections?|drugs?|steroids?|diuretics?|"
        r"beta[- ]?blockers?|ace inhibitors?|inhibitors?)\b")
NUM = r"(?:\d[\d,.]*|one|two|three|four|five|half(?: a| of a)?|a single)"
DOSE = (r"(?:" + NUM + r"\s*(?:mg|mcg|µg|iu|units?|ml|g)\b(?!\s*/|\s+per\s+(?:dl|l|ml|liter|litre|deciliter)\b)"
        r"|" + NUM + r"\s+(?:\d+\s*(?:mg|mcg)\s+)?(?:tablets?|capsules?|pills?|teaspoons?|tablespoons?|drops?|puffs?|doses?)\b)")
NOT_A_CONDITION = (r"(?:\d|(?:no|not|any|one|two|three|four|five|six|seven|eight|nine|ten|several|many|multiple|more|other|another|additional|"
                   r"all|each|enough|only|just|already|also|ever|had|been|taken|seen|heard|read|received|recorded|logged|uploaded|entered|"
                   r"completed|verified|imported|added|asked|noticed|started|stopped|missed|shared|done|made|to|questions?|concerns?|"
                   r"results?|records?|access|time|trouble|difficulty|your|their|them|it)\b|"
                   r"(?:a|an|the)\s+(?:question|few|chance|right|choice|copy|record|result|reminder|follow|scheduled|recent|new|pending|"
                   r"total|lot|number|couple|appointment|upcoming|open|option|opportunity|account|same|results|following|ability|"
                   r"cut|test|repeat|visit|report|list|document|profile|doctor|clinician)\b|"
                   r"(?:[\w-]+\s+)?(?:readings?|results?|values?|tests?|reports?|documents?|reminders?|tasks?|appointments?|items?|entries)\b)")
NOT_COND = r"(?<!\bif )(?<!\bwhen )(?<!whether )(?<!unless )(?<!\bonce )(?<!\bwhile )(?<!whenever )(?<!\bin case )(?<!\bwho )"
HAVE_ADV = r"(?:\s+(?:most|very|quite|almost|likely|probably|possibly|certainly|definitely|clearly|now|also|still|currently|really|actually|both|do|appear to|seem to))*"

REVISED_A = [
    # --- diagnosis ---
    ("D1", ASSERT + NOT_COND + r"\byou" + HAVE_ADV + r"\s+have\s+(?!" + NOT_A_CONDITION + r")\w+", "diagnostic_language"),
    ("D2", ASSERT + r"\byou(?:'ve|\s+have)?\s+(?:got|developed)\s+(?!" + NOT_A_CONDITION + r")\w+", "diagnostic_language"),
    ("D3", r"\byou\s+(?:are|were|have been|'ve been)\s+(?:being\s+)?diagnosed with\s+\w+", "diagnostic_language"),
    ("D4", ASSERT + r"\bdiagnosis\s+of\s+\w+|\bdiagnosis\s*:\s*\w+", "diagnostic_language"),
    ("K2", r"\b(this (means|indicates|confirms) you have)\b", "diagnostic_language"),
    ("D5", ASSERT + r"\byou(?:'re|\s+are)(?:\s+(?:most|very|quite|likely|probably|clearly|definitely|now|also|severely|mildly|slightly|borderline))*\s+(?:" + STATE + r"|(?:suffering from|living with|showing signs of)\s+\w+)", "diagnostic_language"),
    ("D6", ASSERT + r"\byou(?:\s+(?:likely|probably|clearly|definitely|now|also))*\s+suffer\s+from\s+\w+", "diagnostic_language"),
    ("D7", ASSERT + r"\byou\s+(?:may|might|could)\s+(?:well\s+)?(?:have|be suffering from)\s+(?:(?!risk|chance|history|question|test)[\w-]+\s+){0,4}?" + COND, "diagnostic_language"),
    ("D8", ASSERT + r"\b(?:this|that|these|those|your|it)\b[^.!?\n]{0,50}?(?<!may )(?<!might )(?<!can )(?<!could )(?<!sometimes )(?<!often )\b(?:indicates?|confirms?|proves?|means?|shows?|reveals?|is diagnostic of|(?:is|are) consistent with|points? to|adds? up to)\s+(?:that\s+)?(?:you(?:r)?\s+)?(?:an?\s+|the\s+)?(?:(?!risk|chance)[\w-]+\s+){0,3}?" + COND, "diagnostic_language"),
    ("D9", ASSERT + r"\b(?:this|that|it)\s+is\s+(?:(?!not|no|test|screen|marker|measure|check|common|way|risk|general|educational|information|question)[\w-]+\s+){0,3}?" + COND, "diagnostic_language"),
    ("D10", r"(?:(?:^|(?<=[.!?;:\n]))\s*(?:\w+,\s+)?|\b(?:means?|shows?|confirms?|proves?)\s+(?:that\s+)?)your\s+(?:kidneys?|liver|thyroid|heart|pancreas|bone marrow)\s+(?:is|are)\s+(?:\w+\s+)?(?:failing|damaged|underactive|overactive|diseased|shutting down|inflamed|enlarged)\b", "diagnostic_language"),
    # --- certainty ---
    ("K3", r"\b(definitely|certainly|clearly) (have|indicates?|shows?)\b", "certainty_claims"),
    ("T1", r"\b(always means|never means|absolutely)\b|\b100\s?%\s+(?:sure|certain|certainty|a sign|sign|guarantee\w*|positive|confirm\w*)", "certainty_claims"),
    ("T2", r"\b(guaranteed|definitely|certainly|definite)\b", "certainty_claims"),
    ("T3", r"\b(?:it is|it's|i am|i'm|we are)\s+(?:(?!not\b)\w+\s+)?certain\b|\bwith (?:absolute |complete |total )?certainty\b|\b(?:a|is)\s+(?:100\s?%\s+)?certainty\b", "certainty_claims"),
    ("T4", ASSERT + r"\b(?:guarantees?|conclusive(?:ly)?|zero chance|you can be (?:sure|certain|confident)|is always (?:a sign|caused|due)|rest assured|undoubtedly|unquestionably|inevitabl[ey]|for sure)\b", "certainty_claims"),
    ("T5", r"\b(?:no doubt|without (?:a |any )?(?:doubt|question)|no question|beyond (?:any |a )?doubt|no (?:chance|possibility|way) (?:that|this|it)|never worry)\b", "certainty_claims"),
    # --- dosing ---
    ("K4", r"\btake\s+\d+\s*(mg|mcg|g|ml|units?)\b", "dosing_recommendation"),
    ("K6", r"\b(medication dosage|dose adjustment|increase.*dose|decrease.*dose)\b", "dosing_recommendation"),
    ("O1", IMP + r"(?:tak(?:e|ing)|try(?:ing)?|us(?:e|ing)|inject(?:ing)?|increas(?:e|ing)|rais(?:e|ing)|lower(?:ing)?|reduc(?:e|ing)|decreas(?:e|ing)|split(?:ting)?|halv(?:e|ing)|doubl(?:e|ing)|cut(?:ting)?|be on|go(?:ing)? (?:up|down) to)\b[^.!?\n]{0,60}?" + DOSE, "dosing_recommendation"),
    ("O2", IMP + r"(?:doubl(?:e|ing)|halv(?:e|ing)|cut(?:ting)?|split(?:ting)?|rais(?:e|ing)|lower(?:ing)?|increas(?:e|ing)|decreas(?:e|ing)|reduc(?:e|ing))\s+(?:your|the|that)\s+(?:[\w'-]+\s+){0,3}?(?:" + DRUG + r"|in half)", "dosing_recommendation"),
    ("O3", r"\bdose\s+(?:of\s+" + NUM + r"[^.!?\n]{0,40}?)?(?:should|would|ought to|needs to)\s+be\b|\bdose\s+in\s+half\b|\bgood dose\b", "dosing_recommendation"),
    # --- medication ---
    ("K5", r"\b(prescribe|prescription|should take|must take|need to take)\b", "medication_advice"),
    ("M1", r"\b(?:put|switch|start)\s+you\s+(?:on|to)\s+\w+", "medication_advice"),
    ("K7", r"\b(start taking|stop taking|discontinue)\s+\w+", "medication_advice"),
    ("M2", IMP + r"(?:start(?:ing)?|begin(?:ning)?|stop(?:ping)?|quit(?:ting)?|restart(?:ing)?|resum(?:e|ing)|switch(?:ing)?|swap(?:ping)?|skip(?:ping)?|paus(?:e|ing)|hold(?:ing)?|add(?:ing)?|try(?:ing)?|tak(?:e|ing)|refill(?:ing)?|pick(?:ing)? up|com(?:e|ing) off|go(?:ing)? (?:back )?on|get(?:ting)? (?:yourself )?on|be on|put you on|switch you to)\b(?!\s+(?:by|with a list|a list|notes?))[^.!?\n]{0,40}?" + DRUG + r"(?!\s+(?:list|label|record|history|review|names?)\b)", "medication_advice"),
    ("M3", r"\b(?:don't|do not)\s+(?:take|refill|skip|stop|use)\s+(?:your|the|that|any)\s+(?:[\w'-]+\s+){0,2}?" + DRUG, "medication_advice"),
    # --- emergency ---
    ("K10", r"\b(call 911|go to (the )?ER|emergency room|seek immediate)\b", "emergency_advice"),
    ("K11", r"\b(medical emergency|life.?threatening)\b", "emergency_advice"),
    ("E1", r"\b(?:call|dial|phone|ring)\s+(?:an?\s+|the\s+)?(?:ambulance|911|999|112|000|emergency services)\b|\bemergency (?:department|services|care|help)\b|\burgent care\b|\bA&E\b|\b(?:get|go|head|drive you)\s+to\s+(?:a|an|the|your)\s+(?:nearest\s+|local\s+)?hospital\b|\bseek (?:emergency|urgent)\b", "emergency_advice"),
]

# Precision-only variant: the live 11 patterns with the three measured
# false-positive causes fixed (D1/D3/D4 replace pattern 1; T1 replaces
# pattern 8; T2 + T3 replace pattern 9). No recall additions.
_BY_ID = {row[0]: row for row in REVISED_A}
REVISED_MIN = [_BY_ID[i] for i in ("D1", "D3", "D4", "K2", "K3", "K4", "K5", "K6", "K7", "T1", "T2", "T3", "K10", "K11")]

LISTS = {"plan_18": PLAN_18, "revised_min": REVISED_MIN, "revised_a": REVISED_A}
