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
    r"\b(?:take|use|inject)\s+(?:more|less|extra|double|half)\b",
]

_TREATMENT_PATTERNS = [
    r"\bwhat (?:should|can) i do (?:about|for)\b",
    r"\bhow (?:should|do) i treat\b",
    r"\bwhat treatment\b(?!\s+(?:was|is|were)\s+(?:listed|noted|written|recorded|mentioned|documented)\s+in my\s+(?:\w+\s+){0,2}?(?:notes?|visits?|reports?|documents?|records?|summary|chart|file|results?)\b)",
    r"\bshould i see a doctor\b",
    r"\bdo i need (?:to see a doctor|treatment|surgery|a procedure)\b",
    r"\bwhat('s| is) the best (?:treatment|way to treat|remedy)\b",
    r"\bhow (?:do|can) i (?:lower|reduce|fix|cure|treat) my\b",
    r"\bshould i go to the (?:er|emergency room|hospital)\b",
]

_DIAGNOSIS_PATTERNS = [
    r"\bis (?:my|this|that) (?!(?:\w+\s+){0,4}?(?:marked|flagged|listed|labeled|labelled|noted)\s+(?:as\s+)?(?:abnormal|high|low)\b).*\b(?:dangerous|serious|normal|abnormal|bad|ok|okay|concerning|worrying|critical|high enough|low enough)\b",
    r"\bdo i have\b(?!\s+(?:an?|any|my|the)\s+(?:\w+\s+){0,3}?(?:results?|reports?|tests?|labs?|readings?|values?|records?)\b)(?!\s+(?:an?|any|my|the)\s+(?:\w+\s+){0,4}?on file\b)",
    r"\bcould (?:i (?:be|have)\b|this have\b|this be\b(?!\s+(?:from my\s+(?:\w+\s+){0,2}?(?:visit|lab|labs|report|test|tests|appointment|results?|bloodwork|panel)\b|the same\s+(?:test|lab|labs|report|result|value)\b)))",
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
