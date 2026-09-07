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
    r"\bshould i (?:stop|start|begin|quit|change|switch|increase|decrease|adjust|lower|raise|skip|take)\b.*\b(?:taking|my|the|this)\b",
    r"\b(?:stop|start|quit|change|switch|increase|decrease|adjust)\s+(?:taking\s+)?my\s+\w*\s*(?:statin|medication|medicine|pill|dose|dosage|drug|prescription|insulin|antibiotic)",
    r"\bcan i (?:stop|start|quit|skip)\b.*\b(?:medication|medicine|pill|dose|dosage|drug|statin|insulin|prescription)\b",
    r"\bis it (?:safe|okay|ok) (?:for me )?to (?:stop|start|quit|change|skip)\b.*\b(?:medication|medicine|pill|dose|statin|insulin|drug)\b",
    r"\bshould i (?:still )?(?:be )?tak(?:e|ing) my\b",
    r"\bdo i (?:still )?need my\b.*\b(?:medication|medicine|pill|dose|statin|insulin|drug)\b",
]

_TREATMENT_PATTERNS = [
    r"\bwhat (?:should|can) i do (?:about|for)\b",
    r"\bhow (?:should|do) i treat\b",
    r"\bwhat treatment\b",
    r"\bshould i see a doctor\b",
    r"\bdo i need (?:to see a doctor|treatment|surgery|a procedure)\b",
    r"\bwhat('s| is) the best (?:treatment|way to treat|remedy)\b",
    r"\bhow (?:do|can) i (?:lower|reduce|fix|cure|treat) my\b",
    r"\bshould i go to the (?:er|emergency room|hospital)\b",
]

_DIAGNOSIS_PATTERNS = [
    r"\bis (?:my|this|that) .*\b(?:dangerous|serious|normal|abnormal|bad|ok|okay|concerning|worrying|critical|high enough|low enough)\b",
    r"\bdo i have\b",
    r"\bcould (?:this|i) (?:be|have)\b",
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
