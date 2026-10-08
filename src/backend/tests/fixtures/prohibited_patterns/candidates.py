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

LISTS = {"plan_18": PLAN_18, "revised_min": REVISED_MIN, "revised_a": REVISED_A, "revised_b": REVISED_B}
