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


# ---------------------------------------------------------------------------
# REVISED_B (2026-10-08). REVISED_A measured 154/191 (80.6%) with 3 false
# positives and 2 regressions on held_out_final, so it fails the owner's
# conditions. REVISED_B was then derived WITH held_out_final in view, so its
# figures on held_out_dev and held_out_final are in-sample. It was frozen in
# git before a third independent split (held_out_final2.json) was written;
# only the held_out_final2 figures are out-of-sample for REVISED_B.
# ---------------------------------------------------------------------------
# Building blocks for REVISED_B (suffix _B). REVISED_A's blocks above are frozen.
NEG_B = r"\b(?:not|never|no|nor|neither|cannot|can't|won't|don't|doesn't|isn't|aren't|unable|whether|only|none|nothing|without|rule out|rather than)\b"
# Clause start: sentence start, or after a comma / semicolon / colon / newline.
CLAUSE_B = r"(?:^|(?<=[.!?;:,\n]))"
# From the clause start up to the match: no negation / limit word.
ASSERT_B = CLAUSE_B + r"(?:(?!" + NEG_B + r")[^.!?\n,;])*?"
# Filler of up to n characters that contains no negation / limit word.
def _nn(n: int) -> str:
    return r"(?:(?!" + NEG_B + r")[^.!?\n]){0," + str(n) + r"}?"
# Start of an instruction: (1) at a sentence start, or after a comma when no
# negation / limit word comes earlier in the sentence, optionally after a list
# bullet; or (2) after an advice lead-in, when no negation / limit word comes
# earlier in the clause ("I can't say whether you should take ..." is allowed).
IMP_B = (r"(?:(?:^|(?<=[.!?;:\n]))(?:(?:(?!" + NEG_B + r")[^.!?\n])*?,)?\s*(?:[-*\u2022]\s*|\d[.)]\s+)?|"
         + ASSERT_B + r"\b(?:and|then|please|just|also|so|now|safely|should|ought to|need to|have to|must|"
         r"can|could|may want to|might want to|consider|recommend|suggest|advise|idea to|help to|wise to|best to|better to|time to|want to|"
         r"you to|would be to|step is to|try|i'd|i would)\s+(?:probably\s+|definitely\s+|really\s+|simply\s+|to\s+)?)")
COND_B = COND
STATE_B = r"(?:(?:[\w-]+\s+){0,2}?" + STATE + r")"
DRUG_B = (DRUG[:-3] + r"|jardiance|farxiga|trulicity|victoza|januvia|humalog|novolog|levemir|basaglar|tresiba|antihistamines?|"
          r"antidepressants?|\w*(?:flozin|xaban|grel|sone|zide)|red yeast rice|over-the-counter\s+\w+|agonists?)\b")
NUM_B = r"(?:\d[\d,.]*|one|two|three|four|five|six|ten|twenty|thirty|forty|fifty|half(?: a| of a)?|a single)"
DOSE_B = (r"(?:" + NUM_B + r"\s*(?:mg|mcg|µg|iu|units?|ml|g|meq|grams?|milligrams?|micrograms?|international units)\b(?!\s*/|\s+per\s+(?:dl|l|ml|liter|litre|deciliter)\b)"
          r"|" + NUM_B + r"\s+(?:\d+\s*(?:mg|mcg)\s+)?(?:tablets?|capsules?|pills?|teaspoons?|tablespoons?|drops?|puffs?|doses?)\b)")
MED_VERB_B = (r"(?:start(?:ing)?|begin(?:ning)?|stop(?:ping)?|quit(?:ting)?|restart(?:ing)?|resum(?:e|ing)|switch(?:ing)?|swap(?:ping)?|"
              r"skip(?:ping)?|paus(?:e|ing)|hold(?:ing)?|add(?:ing)?|try(?:ing)?|tak(?:e|ing)|us(?:e|ing)|refill(?:ing)?|pick(?:ing)? up|"
              r"replac(?:e|ing)|taper(?:ing)?|drop(?:ping)?|bump(?:ing)?|(?:come|coming|get|getting|go|going|leave|leaving) off|"
              r"go(?:ing)? (?:back )?on|get(?:ting)? (?:yourself )?on|be on|put you on|switch you to)")
DOSE_VERB_B = (r"(?:tak(?:e|ing)|try(?:ing)?|us(?:e|ing)|inject(?:ing)?|increas(?:e|ing)|rais(?:e|ing)|lower(?:ing)?|reduc(?:e|ing)|"
               r"decreas(?:e|ing)|split(?:ting)?|halv(?:e|ing)|doubl(?:e|ing)|cut(?:ting)?|taper(?:ing)?|bump(?:ing)?|drop(?:ping)?|"
               r"be on|go(?:ing)? (?:up|down) to)")

REVISED_B = [
    # --- diagnosis ---
    ("D1b", ASSERT_B + NOT_COND + r"\byou" + HAVE_ADV + r"\s+have\s+(?!" + NOT_A_CONDITION + r")\w+", "diagnostic_language"),
    ("D2b", ASSERT_B + r"\byou(?:'ve|\s+have)?\s+(?:got|developed|been living with)\s+(?!" + NOT_A_CONDITION + r")\w+", "diagnostic_language"),
    _BY_ID["D3"],
    ("D4b", ASSERT_B + r"\bdiagnosis\s+(?:of|is|was|would be)\s+\w+|\bdiagnosis\s*:\s*\w+", "diagnostic_language"),
    _BY_ID["K2"],
    ("D5b", ASSERT_B + r"\byou(?:'re|\s+are)(?:\s+(?:most|very|quite|likely|probably|clearly|definitely|now|also|severely|mildly|slightly|borderline))*\s+(?:" + STATE_B + r"|(?:suffering from|living with|showing signs of)\s+\w+|experiencing\s+(?:[\w-]+\s+){0,3}?" + COND_B + r")", "diagnostic_language"),
    _BY_ID["D6"],
    ("D7b", ASSERT_B + r"\byou\s+(?:may|might|could)\s+(?:well\s+)?(?:have|be suffering from)\s+(?:(?!risk|chance|history|question|test)[\w-]+\s+){0,4}?" + COND_B, "diagnostic_language"),
    ("D8b", ASSERT_B + r"\b(?:this|that|these|those|your|it)\b" + _nn(50) + r"(?<!may )(?<!might )(?<!can )(?<!could )(?<!sometimes )(?<!often )\b(?:indicates?|confirms?|proves?|means?|shows?|reveals?|is diagnostic of|(?:is|are) consistent with|points? to|adds? up to|makes? it clear)\s+(?:that\s+)?(?:you(?:r)?\s+)?(?:an?\s+|the\s+)?(?:(?!risk|chance|whether|if)[\w-]+\s+){0,3}?" + COND_B, "diagnostic_language"),
    ("D9b", ASSERT_B + r"\b(?:this|that|it)\s+is\s+(?:(?!not|no|test|screen|marker|measure|check|common|way|risk|general|educational|information|question)[\w-]+\s+){0,3}?" + COND_B, "diagnostic_language"),
    _BY_ID["D10"],
    # --- certainty ---
    _BY_ID["K3"],
    ("T1b", r"\b(always means|never means|absolutely)\b|\b100\s?(?:%|percent)\s+(?:sure|certain|certainty|a sign|sign|guarantee\w*|positive|confirm\w*|fine|safe|normal|healthy)", "certainty_claims"),
    _BY_ID["T2"],
    ("T3b", r"\b(?:it is|it's|i am|i'm|we are)\s+(?:(?!not\b)\w+\s+)?certain\b|\bwith (?:absolute |complete |total )?certainty\b|\b(?:a|is)\s+(?:100\s?(?:%|percent)\s+)?certainty\b|\bcertain that\b", "certainty_claims"),
    ("T4b", ASSERT_B + r"\b(?:guarantees?|conclusive(?:ly)?|zero chance|(?:can|may) be (?:\w+\s+)?(?:sure|certain|confident)|is always (?:a sign|caused|due)|rest assured|undoubtedly|unquestionably|inevitabl[ey]|for sure|a sure thing|i promise|trust me|it is impossible|(?:you are|you're)\s+100\s?(?:%|percent)|(?:will|is|are)\s+never)\b", "certainty_claims"),
    _BY_ID["T5"],
    # --- dosing ---
    _BY_ID["K4"],
    _BY_ID["K6"],
    ("O1b", IMP_B + DOSE_VERB_B + r"\b[^.!?\n]{0,60}?" + DOSE_B, "dosing_recommendation"),
    ("O2b", IMP_B + r"(?:doubl(?:e|ing)|halv(?:e|ing)|cut(?:ting)?|split(?:ting)?|rais(?:e|ing)|lower(?:ing)?|increas(?:e|ing)|decreas(?:e|ing)|reduc(?:e|ing)|taper(?:ing)?|bump(?:ing)?)\s+(?:your|the|that)\s+(?:[\w'-]+\s+){0,3}?(?:" + DRUG_B + r"|in half)", "dosing_recommendation"),
    ("O3b", r"\bdose\s+(?:of\s+" + NUM_B + r"[^.!?\n]{0,40}?)?(?:should|would|ought to|needs to)\s+be\b|\bdose\s+in\s+half\b|\bgood dose\b|" + DOSE_B + r"[^.!?\n]{0,60}?\bwould be (?:better|best|appropriate|ideal|right|enough|good)\b", "dosing_recommendation"),
    ("O4b", r"\byou\s+(?:need|require|should have|should be (?:on|taking))\s+" + _nn(20) + DOSE_B, "dosing_recommendation"),
    ("O5b", r"(?:^|\n)\s*(?:dosing plan|treatment plan|recommended|recommendations?|what i'd do|my advice)\s*:\s*\n", "dosing_recommendation"),
    # --- medication ---
    ("M0b", ASSERT_B + r"\b(?:prescribe|should take|must take|need to take)\b|\b(?:ask for|request|get|need|want|have)\s+(?:a|an|your|the)\s+(?:new\s+)?prescription\b", "medication_advice"),
    _BY_ID["M1"],
    _BY_ID["K7"],
    ("M2b", IMP_B + MED_VERB_B + r"\b(?!\s+(?:by|with a list|a list|notes?))[^.!?\n]{0,40}?" + DRUG_B + r"(?!\s+(?:list|label|record|history|review|names?|organi[sz]er|box|bottle|reminders?)\b)", "medication_advice"),
    ("M3b", r"\b(?:don't|do not|no longer)\s+(?:need\s+(?:to\s+take\s+)?|take\s+|refill\s+|skip\s+|stop\s+|use\s+)(?:your|the|that|any)\s+(?:[\w'-]+\s+){0,2}?" + DRUG_B, "medication_advice"),
    ("M4b", IMP_B + r"(?:stop|hold|skip|pause|restart|resume|refill|quit|taper|replace|bump|double|halve|cut|increase|decrease|reduce|lower|raise)\s+(?:your|the)\s+(?-i:[A-Z][a-z]{3,})", "medication_advice"),
    ("M5b", r"\b(?:ask|tell|request|insist|push|demand)\b" + _nn(40) + r"\b(?:for|put on|prescribed|switch(?:ed)? to)\s+(?:a\s+|an\s+|your\s+|the\s+)?(?:[\w-]+\s+)?(?:" + DRUG_B + r"|(?-i:[A-Z][a-z]{3,}))", "medication_advice"),
    # --- emergency ---
    _BY_ID["K10"],
    _BY_ID["K11"],
    ("E1b", r"\b(?:call|dial|phone|ring|get)\s+(?:for\s+)?(?:an?\s+|the\s+)?(?:ambulance|911|999|112|000|triple zero|emergency services)\b|\b(?:call|dial|phone|ring)\b[^.!?\n]{0,30}?\bemergency (?:number|line)\b|\bemergency (?:medical )?(?:department|services|care|help)\b|\burgent care\b|\bA&E\b|\b(?:get|go|head|drive you)\s+to\s+(?:a|an|the|your)\s+(?:nearest\s+|local\s+)?hospital\b|\bseek (?:emergency|urgent)\b", "emergency_advice"),
]

# ---------------------------------------------------------------------------
# UNION_R2 (round 2, 2026-10-09, owner row PARA-1-R2 "One more round").
# Construction rule: the 11 live patterns from interpret_safety.py copied
# character for character (ids K1..K11 — K<n> is live pattern n, kept as the
# third element of each tuple exactly as compiled there), PLUS additive
# patterns only (ids U-*). 0 of the 215 must-not-regress catches can be lost
# by construction. Derived on in_sample, held_out_dev, must_not_regress and
# the must-allow/product sets ONLY; frozen in git before the fourth held-out
# split (to be loaded later via --final3) is written by an independent author.
# Every added pattern is linear-time: keyword-anchored, gaps bounded by
# {0,4} words or {0,60} chars, no nested quantifiers, no unbounded .*, and no
# clause-start scanning (the revised_b timing failure mode).
# ---------------------------------------------------------------------------
# Condition words: suffix forms + an explicit list; excludes diagnosis/prognosis etc.
COND_R2 = (r"(?:(?!diagnosis|prognosis|analysis|basis|emphasis|metabolism|mechanism|organism)"
           r"\w*(?:itis|osis|emia|aemia|uria|pathy|oma|ism|penia|philia|megaly)|"
           r"disease|disorder|deficiency|failure|syndrome|cancer|diabetes|pre-?diabetes|infection|"
           r"damage|injury|an[ae]?emia|hypertension|hypotension|high blood pressure|high cholesterol|"
           r"thyroid|resistance|bleeding|tumou?r|lupus|gout|arthritis|hepatitis|leuk[ae]?emia|"
           r"overload|dehydration|insufficiency|fatty liver|stroke|heart attack|clot|sepsis|"
           r"malnutrition|obesity|condition)\b")

# Adjective states after "you are/you're"
STATE_R2 = (r"(?:pre-?diabetic|diabetic|an[ae]mic|hypothyroid|hyperthyroid|dehydrated|deficient|"
            r"malnourished|septic|jaundiced|obese|hypertensive|insulin[- ]resistant|"
            r"immunocompromised)\b")

# Drug words: suffix forms + brand/generic list + generic nouns
DRUG_R2 = (r"(?:\w*(?:statin|pril|sartan|olol|formin|oxine|farin|parin|gliptin|gliflozin|glutide|"
           r"dipine|azole|mycin|cillin|cycline|floxacin|prazole|tidine|semide|thiazide|lactone|mab|"
           r"flozin|xaban|grel|sone|zide)|insulin|aspirin|ibuprofen|acetaminophen|paracetamol|"
           r"lipitor|crestor|zocor|synthroid|glucophage|ozempic|lantus|coumadin|eliquis|xarelto|"
           r"lasix|plavix|ezetimibe|allopurinol|prednisone|jardiance|farxiga|trulicity|victoza|"
           r"januvia|humalog|novolog|levemir|basaglar|tresiba|levothyroxine|metformin|lisinopril|"
           r"atorvastatin|rosuvastatin|warfarin|losartan|ferrous|iron|vitamin\s+\w+|b12|folic acid|"
           r"folate|magnesium|potassium|calcium|zinc|fish oil|omega-3|probiotics?|antibiotics?|"
           r"anticoagulants?|blood thinners?|supplements?|medications?|medicines?|meds|pills?|"
           r"tablets?|capsules?|doses?|injections?|drugs?|steroids?|diuretics?|beta[- ]?blockers?|"
           r"ace inhibitors?|inhibitors?|antihistamines?|antidepressants?|red yeast rice|"
           r"over-the-counter\s+\w+|agonists?)\b")

NUM_R2 = (r"(?:\d[\d,.]*|one|two|three|four|five|six|seven|eight|nine|ten|twenty|thirty|forty|"
          r"fifty|half(?:\s+a|\s+of\s+a)?|a single)")
UNIT_R2 = (r"(?:mg|mcg|µg|iu|units?|ml|g|meq|grams?|milligrams?|micrograms?|millilit(?:er|re)s?)\b"
           r"(?!\s*/|\s+per\s+(?:d?l|ml|liter|litre|deciliter)\b)")
COUNTN_R2 = r"(?:tablets?|capsules?|pills?|teaspoons?|tablespoons?|drops?|puffs?|doses?|sprays?|patches?)"
DOSE_R2 = (r"(?:" + NUM_R2 + r"\s*" + UNIT_R2 + r"|" + NUM_R2 +
           r"\s+(?:\d[\d,.]*\s*(?:mg|mcg|g)\s+)?" + COUNTN_R2 + r"\b)")

# Word immediately before a med verb that makes it a description, not advice
# ("keep taking", "are taking", "is listed as taken" handled by "taken" not being a verb).
_MEDPRE_R2 = (r"(?<!\bkeep )(?<!\bkeeps )(?<!\bcontinue )(?<!\bcontinues )(?<!\bcontinued )"
              r"(?<!\bcurrently )(?<!\bbeen )(?<!\bis )(?<!\bare )(?<!\bwas )(?<!\bwere )"
              r"(?<!\bam )(?<!\bas )(?<!\bon )(?<!\bof )(?<!\byou're )(?<!\bthey're )(?<!\bwe're )")

# Trailing context that means the drug word is app data, not a recommendation
# ("add your medications to your profile", "a medication from the Medications page").
_MEDTAIL_R2 = (r"(?!\s+(?:(?:in|on|from|into|to|inside|via|within)\s+(?:the\s+|your\s+|this\s+|my\s+)?)?"
               r"(?:app|application|profile|records?|lists?|pages?|tabs?|sections?|trackers?|charts?|"
               r"library|calendar|journals?|logs?|notes?|organizers?|organisers?|cabinet|vault|device|"
               r"reminders?|entries|entry|history|review|feature|settings|screens?|dashboard|"
               r"medications?\s+(?:page|list|section|tab)|meds?\s+(?:page|list|section|tab)|"
               r"health\s+(?:record|app|app[s]?))\b)")

UNION_R2 = [
    # --- live list, copied character for character from
    #     modules/interpret_safety.py InterpretationSafetyGuard.PROHIBITED_PATTERNS ---
    ("K1", r"\b(you have|you are diagnosed with|diagnosis of)\s+\w+", "diagnostic_language"),
    ("K2", r"\b(this (means|indicates|confirms) you have)\b", "diagnostic_language"),
    ("K3", r"\b(definitely|certainly|clearly) (have|indicates?|shows?)\b", "certainty_claims"),
    ("K4", r"\btake\s+\d+\s*(mg|mcg|g|ml|units?)\b", "dosing_recommendation"),
    ("K5", r"\b(prescribe|prescription|should take|must take|need to take)\b", "medication_advice"),
    ("K6", r"\b(medication dosage|dose adjustment|increase.*dose|decrease.*dose)\b", "dosing_recommendation"),
    ("K7", r"\b(start taking|stop taking|discontinue)\s+\w+", "medication_advice"),
    ("K8", r"\b(always means|never means|100%|absolutely)\b", "certainty_claims"),
    ("K9", r"\b(guaranteed|definite(ly)?|certain(ly)?)\b", "certainty_claims"),
    ("K10", r"\b(call 911|go to (the )?ER|emergency room|seek immediate)\b", "emergency_advice"),
    ("K11", r"\b(medical emergency|life.?threatening)\b", "emergency_advice"),
    # --- additions ---
    # "you <adverb> have <cond>": you likely/probably/may have diabetes
    ("U-D1", r"\byou\s+(?:(?:most|very)\s+)?(?:likely|probably|possibly|clearly|definitely|"
             r"may|might|could|appear\s+to|seem\s+to)\s+(?:well\s+)?have\s+"
             r"(?:an?\s+|the\s+)?(?:[\w'-]+\s+){0,4}?" + COND_R2, "diagnostic_language"),
    # "you've got/developed <cond>", "you have been diagnosed/living with"
    ("U-D2", r"\byou(?:'ve|\s+have)\s+(?:got|developed|been\s+(?:diagnosed|living)\s+with)\s+"
             r"(?:an?\s+|the\s+)?(?:[\w'-]+\s+){0,4}?" + COND_R2, "diagnostic_language"),
    # "you are/you're <state-adj>" or "you are in <stage> kidney failure"
    ("U-D3", r"\byou(?:'re|\s+are)\s+(?:(?:most|very|quite|likely|probably|clearly|definitely|"
             r"now|also|still|severely|mildly|slightly|borderline|already|currently|simply)\s+)*"
             r"(?:" + STATE_R2 +
             r"|in\s+(?:[\w'-]+\s+){0,2}(?:kidney|renal|liver|heart|organ|respiratory|cardiac)"
             r"\s+failure\b)", "diagnostic_language"),
    # "you (may be/are/'re) suffering from <cond>" / "you suffer from <cond>"
    ("U-D4", r"\byou(?:'re)?(?:\s+(?:are|may|might|could|must|be|probably|likely|currently|also|"
             r"still|clearly|definitely))*\s+suffer(?:ing)?\s+from\s+(?:an?\s+|the\s+)?"
             r"(?:[\w'-]+\s+){0,4}?" + COND_R2, "diagnostic_language"),
    # "your kidneys/liver/thyroid/heart are failing/damaged/underactive";
    # "indicates your thyroid is underactive" is KB boilerplate, not advice
    ("U-D5", r"(?<!\bindicates )(?<!\bindicate )"
             r"\byour\s+(?:kidneys?|liver|thyroid|heart|pancreas|bone\s+marrow|lungs?|"
             r"immune\s+system)\s+(?:is|are|may\s+be|could\s+be|seems?|seems?\s+to\s+be|"
             r"appears?|appears?\s+to\s+be)\s+"
             r"(?:(?:probably|likely|slowly|already|also|still|now|severely|mildly|slightly|"
             r"clearly|definitely)\s+)*"
             r"(?:failing|damaged|underactive|overactive|diseased|shutting\s+down|inflamed|"
             r"enlarged|compromised|weak|struggling)\b", "diagnostic_language"),
    # "<verb> (that) you have/are/'ve got <cond|state>": means/shows/indicates/proves/suggests...
    ("U-D6a", r"\b(?:means?|indicates?|confirms?|shows?|proves?|reveals?|suggests?|points?\s+to|"
              r"adds?\s+up\s+to|tells?\s+(?:me|us)|is\s+consistent\s+with|are\s+consistent\s+with|"
              r"is\s+diagnostic\s+of|is\s+a\s+sign\s+of)\s+(?:that\s+)?you\s+"
              r"(?:(?:probably|likely|most\s+likely|also|still|now)\s+)?"
              r"(?:have|'ve\s+(?:got|developed)|are|'re|developed)\s+"
              r"(?:(?:likely|probably|severely|mildly|slightly|borderline)\s+)?"
              r"(?:an?\s+|the\s+)?(?:[\w'-]+\s+){0,4}?(?:" + COND_R2 + r"|" + STATE_R2 + r")",
     "diagnostic_language"),
    # "<subject> <verb> <up to 4 words> <cond>": subject is a demonstrative,
    # "your ...", or "the <result-noun>" — a bare analyte subject ("Low
    # hemoglobin indicates anemia") is KB anatomy text, not user diagnosis.
    # Verb blocked after may/might/can/could/sometimes/often/not/never/cannot
    # and before or|whether|if|and|no|not (hedged text, "confirm or rule out").
    ("U-D6b", r"\b(?:this|that|it|these|those|they|your(?:\s+[\w'-]+){0,3}?|"
              r"the\s+(?:results?|numbers|values?|labs?|levels?|findings?|pattern|picture|"
              r"combination|readings?|tests?|data|trend|workup))\s+"
              r"(?:[\w'-]+\s+){0,3}?"
              r"(?<!\bmay )(?<!\bmight )(?<!\bcan )(?<!\bcould )(?<!\bsometimes )(?<!\boften )"
              r"(?<!\bnot )(?<!\bnever )(?<!\bcannot )(?<!\bcan't )"
              r"(?:means?|indicates?|confirms?|proves?|reveals?|suggests?|points?\s+to|"
              r"adds?\s+up\s+to|is\s+consistent\s+with|are\s+consistent\s+with|"
              r"is\s+diagnostic\s+of)\s+"
              r"(?!\s+(?:or|whether|if|and|no|not)\b)(?:that\s+)?(?:[\w'-]+\s+){0,4}?" + COND_R2,
     "diagnostic_language"),
    # "this is <cond|state>": This is hypothyroidism. Tail guard keeps app nouns.
    ("U-D7", r"\b(?:this|that|it)\s+is\s+(?:(?!not\b|no\b)[\w'-]+\s+){0,3}?"
             r"(?:" + COND_R2 + r"|" + STATE_R2 + r")"
             r"(?!\s+(?:app|application|tool|feature|page|section|test|education|educational|"
             r"class|course|module|tracker|tracking|material|week|month|day|awareness|part|"
             r"step|screen|check|measure|marker|device)\b)", "diagnostic_language"),
    # "Diagnosis: <word>" (headers and bullets)
    ("U-D8", r"\bdiagnosis\s*:\s*\w+", "diagnostic_language"),

    # --- dosing ---
    # "take/try/use/inject/swallow <up to 4 words> <dose>"
    ("U-O1", r"\b(?:take|taking|try|trying|use|using|inject|injecting|swallow)\s+"
             r"(?:an?\s+|the\s+)?(?:[\w'-]+\s+){0,4}?" + DOSE_R2, "dosing_recommendation"),
    # "<change-verb> (your/the/that/my) <up to 4 words> (dose|dosage|in half|<dose>)"
    ("U-O2", r"\b(?:increase|increasing|reduce|reducing|lower|lowering|raise|raising|decrease|"
             r"decreasing|double|doubling|halve|halving|cut|cutting|split|splitting|taper|"
             r"tapering|bump|bumping|drop|dropping)\s+(?:your\s+|the\s+|that\s+|my\s+)?"
             r"(?:[\w'-]+\s+){0,4}?(?:dose\b|dosage\b|in\s+half\b|" + DOSE_R2 + r")",
     "dosing_recommendation"),
    # "dose (of NUM ...)? should|would|... be" / "good dose" / "dose in half"
    ("U-O3", r"\bdose\s+(?:of\s+" + NUM_R2 + r"[^.!?\n]{0,40}?)?"
             r"(?:should|would|could|might|needs?\s+to|ought\s+to|must)\s+be\b|"
             r"\b(?:your\s+[\w'-]+|the)\s+dose\s+(?:should|would|needs?\s+to|must|could|"
             r"ought\s+to)\s+be\b|\bgood\s+dose\b|\bdose\s+in\s+half\b", "dosing_recommendation"),
    # "you should/must/need to (safely)? (be on|take|try|use) ... <dose>"
    ("U-O4", r"\byou\s+(?:should|must|need\s+to|ought\s+to|have\s+to|could|can)\s+"
             r"(?:safely\s+)?(?:be\s+on|take|try|use)\s+(?:an?\s+|the\s+)?"
             r"(?:[\w'-]+\s+){0,4}?" + DOSE_R2, "dosing_recommendation"),

    # --- medication ---
    # "<med-verb> (your/the/a/my/that) <up to 4 words> <drug>" with benign-prefix
    # lookbehind (keep/are/is/... taking) and app-noun tail guard.
    ("U-M1", _MEDPRE_R2 +
             r"\b(?:start(?:ing)?|begin(?:ning)?|stop(?:ping)?|quit(?:ting)?|restart(?:ing)?|"
             r"resum(?:e|ing)|switch(?:ing)?|swap(?:ping)?|skip(?:ping)?|paus(?:e|ing)|"
             r"hold(?:ing)?|add(?:ing)?|drop(?:ping)?|discontinu(?:e|ing)|try(?:ing)?|"
             r"tak(?:e|ing)|refill(?:ing)?|pick(?:ing)?\s+up|com(?:e|ing)\s+off|"
             r"go(?:ing)?\s+(?:back\s+)?on|get(?:ting)?\s+(?:yourself\s+)?on|be\s+on|"
             r"put\s+you\s+on|place\s+you\s+on|switch\s+you\s+to|wean\s+off)\s+"
             r"(?:your\s+|the\s+|an?\s+|my\s+|that\s+|yourself\s+)?(?:[\w'-]+\s+){0,4}?"
             r"" + DRUG_R2 + _MEDTAIL_R2, "medication_advice"),
    # "don't / do not / no longer (need to)? (take|refill|skip|stop|use) your ... <drug>"
    ("U-M3", r"\b(?:don't|do\s+not|no\s+longer)\s+"
             r"(?:need\s+(?:to\s+take\s+)?|take\s+|refill\s+|skip\s+|stop\s+|use\s+)"
             r"(?:your|the|that|any)\s+(?:[\w'-]+\s+){0,2}?" + DRUG_R2, "medication_advice"),

    # --- certainty ---
    # "100% sure/certain/a sign/normal/..." (also "100 percent")
    ("U-T1", r"\b100\s?(?:%|percent)\s+(?:sure|certain|certainty|a\s+sign|sign|guarantee\w*|"
             r"positive|confirm\w*|fine|safe|normal|healthy|accurate|correct|right)\b",
     "certainty_claims"),
    # fixed certainty phrases
    ("U-T2", r"\b(?:no\s+doubt|without\s+(?:a\s+|any\s+)?(?:doubt|question)|no\s+question|"
             r"beyond\s+(?:any\s+|a\s+)?doubt|zero\s+chance|no\s+(?:chance|possibility|way)\s+"
             r"(?:that|this|it)|never\s+worry|rest\s+assured|for\s+sure|i\s+promise(?:\s+you)?|"
             r"i\s+can\s+promise|it\s+is\s+impossible)\b", "certainty_claims"),
    # "guarantee(s/d)" unless negated just before ("do not guarantee", "no guarantee")
    ("U-T3", r"(?<!\bnot )(?<!\bnever )(?<!\bno )(?<!\bcannot )(?<!\bcan't )(?<!\bdon't )"
             r"(?<!\bdoesn't )(?<!\bwon't )(?<!\bunable to )(?<!\bwithout )(?<!\bfar from )"
             r"\bguarantee[sd]?\b", "certainty_claims"),
    # "you can be sure/certain/confident", "with (absolute)? certainty", "conclusive"
    ("U-T4", r"\byou\s+can\s+be\s+(?:sure|certain|confident)\b|\bwe\s+(?:can|are)\s+"
             r"(?:sure|certain|confident)\b|\bwith\s+(?:absolute\s+|complete\s+|total\s+|"
             r"full\s+)?certainty\b|(?<!\bnot )(?<!\bnever )(?<!\bin )\bconclusive(?:ly)?\b|"
             r"\bcertain\s+that\b", "certainty_claims"),
    # "(definitely|certainly|...) (means|develops|caused|will|is|are|have)"
    ("U-T5", r"\b(?:definitely|certainly|clearly|absolutely|undoubtedly|unquestionably)\s+"
             r"(?:means?|indicates?|shows?|confirms?|proves?|have|has|is|are|was|will|"
             r"caused?|causes?|develop\w*|leads?|lead)\b", "certainty_claims"),
    # "is always a sign/symptom/...", "inevitable/inevitably", "cure your X"
    ("U-T6", r"\b(?:is|are)\s+always\s+(?:a\s+|the\s+)?(?:sign|caused|due|symptom|marker|"
             r"indicator|result|proof|evidence)\b|\binevitabl(?:e|y)\b|"
             r"\bcures?\s+(?:your|the|this|these|that|it)\b", "certainty_claims"),

    # --- emergency ---
    # "call/dial/phone/ring (an|the|your local|for an)? ambulance/911/999/112/000/..."
    ("U-E1", r"\b(?:call|dial|phone|ring)\s+(?:an?\s+|the\s+|your\s+local\s+|for\s+an?\s+)?"
             r"(?:ambulance|911|999|112|000|triple\s+zero|emergency\s+(?:services|number|line))\b",
     "emergency_advice"),
    # "emergency department/services/care/help/number/line/room", "urgent care", "A&E"
    ("U-E2", r"\b(?:emergency\s+(?:medical\s+)?(?:department|services|care|help|number|line|"
             r"room)|urgent\s+care|A&E)\b", "emergency_advice"),
    # "get/go/head/drive (you)/rush/walk to (a|the|your|nearest) hospital"
    ("U-E3", r"\b(?:get|go|head|drive|rush|walk)\s+(?:(?:yourself|you)\s+)?(?:over\s+)?to\s+"
             r"(?:a|an|the|your)\s+(?:nearest\s+|local\s+|nearby\s+|closest\s+)?hospital\b",
     "emergency_advice"),
]

LISTS = {"plan_18": PLAN_18, "revised_min": REVISED_MIN, "revised_a": REVISED_A,
         "revised_b": REVISED_B, "union_r2": UNION_R2}
