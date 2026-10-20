"""Independent second PHI detector (RSI1-DONATE PR-2, DON-DETECTOR a).

Detect-only: returns the Safe Harbor category of each hit, never the matched
value and never rewritten text (45 CFR 164.514(b)(2)). Written independently
of modules/redaction.py (no import of it; HC-DON-012). Any hit drops the
record in modules/data_donation.collect.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

CATEGORIES = (
    "name", "geographic", "date", "phone", "email", "ssn", "mrn",
    "account_number", "url", "ip_address", "age_over_89", "device_vehicle_id",
)

_MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?"
_CAP = r"[A-Z][a-z]+(?:[-'][A-Z][a-z]+)?"
_STATES = (
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ "
    "NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC"
).replace(" ", "|")

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("email", re.compile(r"\b[\w.+-]{1,64}@[\w-]+(?:\.[\w-]+)+\b")),
    ("url", re.compile(r"\b(?:https?://|www\.)\S+", re.I)),
    ("ip_address", re.compile(r"\b(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}\b")),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b|\b(?:SSN|social security(?: number| no\.?| #)?)\s*[:#]?\s*\d{9}\b", re.I)),
    ("phone", re.compile(r"(?<!\d)(?:\+?1[-. ])?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}(?!\d)")),
    ("date", re.compile(
        rf"\b\d{{1,2}}[/-]\d{{1,2}}[/-]\d{{2,4}}\b|\b\d{{4}}-\d{{2}}-\d{{2}}\b"
        rf"|\b{_MONTH}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,\s*\d{{4}})?\b|\b\d{{1,2}}(?:st|nd|rd|th)?\s+{_MONTH}\b"
    )),
    ("mrn", re.compile(r"\b(?:MRN|medical record(?: number| no\.?| #)?|chart(?: number| no\.?| #))\s*[:#]?\s*[A-Z]*-?\d{4,}\b", re.I)),
    ("account_number", re.compile(
        r"\b(?:account|acct|member|policy|insurance|beneficiary|subscriber|license|licence|certificate|"
        r"patient id|health plan)(?: id| number| no\.?| #)?\s*[:#]?\s*[A-Z]{0,4}-?\d[\w-]{3,}\b", re.I)),
    ("device_vehicle_id", re.compile(
        r"\b(?:VIN|serial(?: number| no\.?| #)?|UDI|device id|plate)\s*[:#]?\s*[A-Z0-9-]{5,}\b", re.I)),
    ("age_over_89", re.compile(r"\b(?:age[d]?\s*:?\s*(?:9\d|1[0-2]\d)|(?:9\d|1[0-2]\d)[- ]year[- ]old|(?:9\d|1[0-2]\d)\s*y/?o)\b", re.I)),
    ("geographic", re.compile(
        rf"\b\d{{1,6}}\s+(?:[A-Z][a-z]+\s+){{1,3}}(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Way)\b\.?"
        rf"|\b(?:{_STATES})\s+\d{{5}}(?:-\d{{4}})?\b|\b[Zz][Ii][Pp](?: code)?\s*:?\s*\d{{5}}\b|\b{_CAP},\s*(?:{_STATES})\b")),
    ("name", re.compile(
        rf"\b(?i:patient name|name|patient|pt|mr|mrs|ms|miss|dr)\.?\s*(?i:is|:)?\s*{_CAP}(?:\s+[A-Z]\.)?(?:\s+{_CAP})?"
        rf"|\b(?i:seen by|referred by|signed by|spoke with|guardian|spouse|wife|husband|mother|father|son|daughter)\s+(?:Dr\.?\s+|Mr\.?\s+|Mrs\.?\s+|Ms\.?\s+)?{_CAP}(?:\s+{_CAP})?"
    )),
)


@dataclass(frozen=True)
class Hit:
    """One detection. Carries the Safe Harbor category only, never the value."""

    category: str


def detect(text: str | None) -> list[Hit]:
    """Return one Hit per matching category occurrence in ``text``."""
    if not text:
        return []
    hits: list[Hit] = []
    for category, pattern in _PATTERNS:
        hits.extend(Hit(category) for _ in pattern.finditer(text))
    return hits
