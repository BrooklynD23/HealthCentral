"""Advice classifier (Phase 3, story S3-1).

ONE classifier instance is shared by both call sites — pre-model (on the incoming
question) AND on the draft — so behavior can't drift between them. A single
front-door check is insufficient: bait can enter mid-conversation
(skills/asclexis-guardrails).
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel


class AdviceVerdict(BaseModel):
    is_advice_seeking: bool
    category: Literal["diagnosis", "treatment", "medication", "none"]


# Deterministic keyword/pattern matching — NO LLM. Order matters: medication
# cues are checked first (most specific: "stop/start/change my <drug/dose>"),
# then treatment, then diagnosis/urgency. The first category whose patterns
# match wins; ``none`` means no advice-seeking signal was found.
#
# Patterns are intentionally small and easy to extend (mirrors the spirit of
# nodes/plan.py's _ANALYTE_KEYWORDS) — richer NLU is out of scope here; this
# is a mechanical gate, not a model call (skills/asclexis-guardrails).
_MEDICATION_PATTERNS = [
    r"\b(?:should|can|could|may) i (?:still )?(?:stop|start|begin|quit|change|switch|increase|decrease|adjust|lower|raise|skip|double|take|use|inject)\b",
    r"\b(?:stop|start|quit|change|switch|increase|decrease|adjust)\s+(?:taking\s+)?my\s+\w*\s*(?:statin|medication|medicine|pill|dose|dosage|drug|prescription|insulin|antibiotic)",
    r"\bcan i (?:stop|start|quit|skip)\b.*\b(?:medication|medicine|pill|dose|dosage|drug|statin|insulin|prescription)\b",
    r"\bis it (?:safe|okay|ok) (?:for me )?to (?:stop|start|quit|change|skip|increase|decrease|adjust|lower|raise|double|halve|take|use)\b.*\b(?:medication|medicine|pill|dose|statin|insulin|drug)\b",
    r"\bshould i (?:still )?(?:be )?tak(?:e|ing) my\b",
    r"\bdo i (?:still )?need my\b.*\b(?:medication|medicine|pill|dose|statin|insulin|drug)\b",
    r"\bhow (?:much|many|often)\b(?:\s+[\w'-]+){0,6}?\s+(?:should|do|can|could|may) i (?:take|use|inject)\b",
    r"\b(?:(?:do|does|should|can|could|may|will|would|must|shall) (?:i|we)(?:\s+[\w'-]+){0,3}?|is it (?:safe|okay|ok)(?: for me)?)\s+(?:to\s+)?(?:take|use|inject)\s+(?:more|less|extra|double|half)\b",
]

_TREATMENT_PATTERNS = [
    r"\bwhat (?:should|can) i do (?:about|for)\b",
    r"\bhow (?:should|do) i treat\b",
    r"\bwhat treatment\b(?!\s+(?:was|is|were)\s+(?:listed|noted|written|recorded|mentioned|documented)\s+in\s+my\s+(?:(?:visit|doctor's|clinic|recent|last|latest|discharge|lab)\s+){0,2}(?:notes?|visits?|reports?|documents?|records?|summary|chart|file|results?)[\s?.!]*$)",
    r"\bshould i see a doctor\b",
    r"\bdo i need (?:to see a doctor|treatment|surgery|a procedure)\b",
    r"\bwhat('s| is) the best (?:treatment|way to treat|remedy)\b",
    r"\bhow (?:do|can) i (?:lower|reduce|fix|cure|treat) my\b",
    r"\bshould i go to the (?:er|emergency room|hospital)\b",
]

_DIAGNOSIS_PATTERNS = [
    # Record frames (a question about what the records hold) are anchored to the END of the
    # question: words after the frame are still read, and so are severity words before it (the
    # filler ahead of a marked/flagged frame skips none of them). The analyte list is a copy of the keys of
    # nodes/plan.py:_ANALYTE_KEYWORDS (test_hc_acf_015 lists what the copy lacks).
    r"\bis (?:this |that |my (?!(?:ldl|hdl|cholesterol|triglycerides|glucose|a1c|hba1c|tsh|creatinine|potassium|sodium|vitamin d|hemoglobin)(?:\s+(?:cholesterol|a1c|level|levels|result|results|value|reading))?\s+(?:normal|(?:in|within)\s+(?:the\s+)?normal\s+range)\b[\s?.!]*$))(?!(?:(?!(?:dangerous|serious|normal|abnormal|bad|ok|okay|concerning|worrying|critical|enough)\b)\w+\s+){0,4}?(?:marked|flagged|listed|labeled|labelled|noted)\s+(?:as\s+)?(?:abnormal|high|low)[\s?.!]*$).*\b(?:dangerous|serious|normal|abnormal|bad|ok|okay|concerning|worrying|critical|high enough|low enough)\b",
    r"\bdo i have\b(?!\s+(?:an?|any|my|the)\s+(?:(?:recent|latest|current|last|new|old|lab|blood|test|ldl|hdl|cholesterol|triglycerides|glucose|a1c|hba1c|tsh|creatinine|potassium|sodium|vitamin d|hemoglobin)\s+){0,3}(?:results?|reports?|tests?|labs?|readings?|values?|records?)(?:\s+on file)?(?:\s+from\s+(?:the\s+)?(?:(?:last|this)\s+(?:year|month|week)|(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)(?:\s+\d{4})?|\d{4}))?[\s?.!]*$)(?!\s+(?:an?|any|my|the)\s+(?:(?:recent|latest|current|last)\s+)?(?:ldl|hdl|cholesterol|triglycerides|glucose|a1c|hba1c|tsh|creatinine|potassium|sodium|vitamin d|hemoglobin)\s+on file[\s?.!]*$)",
    r"\bcould (?:i (?:be|have)\b|this have\b|this be\b(?!\s+(?:from\s+my\s+(?:(?:(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)|last|latest|recent|previous|most recent|\d{4})\s+){0,2}(?:(?:visit|labs?|reports?|tests?|blood|appointment|results?|bloodwork|panel)\b\s*){1,3}|the\s+same\s+(?:test|lab|labs|report|result|value)(?:\s+as\s+(?:last time|before|the (?:last|previous) one))?)[\s?.!]*$))",
    r"\bam i (?:at risk|in danger|going to be (?:ok|okay|fine))\b",
    r"\bis (?:this|that|it) bad\b",
    r"\bwhat does this (?:mean|indicate) for my health\b",
    r"\bshould i be worried\b",
    r"\bhow worried should i be\b",
]

_CATEGORY_PATTERNS: list[tuple[Literal["medication", "treatment", "diagnosis"], list[str]]] = [
    ("medication", _MEDICATION_PATTERNS),
    ("treatment", _TREATMENT_PATTERNS),
    ("diagnosis", _DIAGNOSIS_PATTERNS),
]

_COMPILED = [
    (category, [re.compile(p, re.IGNORECASE) for p in patterns])
    for category, patterns in _CATEGORY_PATTERNS
]


def classify_advice(text: str) -> AdviceVerdict:
    """Classify whether ``text`` requests/contains medical advice.

    Deterministic keyword/pattern matching — no LLM call. Checked in a fixed
    category order (medication -> treatment -> diagnosis); the first matching
    category wins. Used at BOTH guard call sites (pre-model on the incoming
    question, and on the drafted sentences) via the SAME compiled patterns so
    behavior cannot drift between the two checks.
    """
    if not text:
        return AdviceVerdict(is_advice_seeking=False, category="none")

    for category, patterns in _COMPILED:
        if any(pattern.search(text) for pattern in patterns):
            return AdviceVerdict(is_advice_seeking=True, category=category)

    return AdviceVerdict(is_advice_seeking=False, category="none")
