"""Advice classifier (Phase 3, story S3-1).

ONE classifier instance is shared by both call sites — pre-model (on the incoming
question) AND on the draft — so behavior can't drift between them. A single
front-door check is insufficient: bait can enter mid-conversation
(skills/healthcentral-guardrails).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class AdviceVerdict(BaseModel):
    is_advice_seeking: bool
    category: Literal["diagnosis", "treatment", "medication", "none"]


def classify_advice(text: str) -> AdviceVerdict:
    """Classify whether ``text`` requests/contains medical advice.

    SCAFFOLD: Sprint 3 (S3-1). Used at BOTH guard call sites (pre-model + draft).
    """
    raise NotImplementedError("S3-1: advice classifier shared by pre-model and draft checks")
