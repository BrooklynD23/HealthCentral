"""FIXED escalation / abstention templates (Phase 3).

These are constants. Editing copy is a code change WITH A TEST, never a prompt
tweak (skills/asclexis-guardrails). The model is NEVER allowed to generate
escalation or abstention prose — the guard node returns these verbatim.
"""

from __future__ import annotations

# Escalate: a static "ask your doctor / pharmacist" block. May list relevant
# VERIFIED VALUES ONLY (values, never advice). No diagnosis, no recommendation.
ESCALATE_TEMPLATE = (
    "This is a question for your doctor or pharmacist. Asclexis can explain "
    "what your verified results say, but it can't advise on diagnosis, treatment, "
    "or medication decisions. Please bring this question to your clinician."
)

# Abstain: a static "not enough verified information" block. Suggest verifying the
# relevant document; never speculate to fill the gap.
ABSTAIN_TEMPLATE = (
    "There isn't enough verified information in your record to explain this yet. "
    "If the relevant document is imported but not verified, verifying it will let "
    "Asclexis explain the values it contains."
)
