"""
Redaction pipeline for external API prompts.

Applies deterministic regex-based redaction to reduce PHI/PII leakage
before any prompt is sent to an external LLM provider.

PRIV-RED-001: Phase 5 — Privacy + Provenance
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Sequence

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Immutable data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RedactionRule:
    """A single redaction rule with a compiled regex pattern."""

    name: str
    pattern: re.Pattern[str]
    replacement: str
    policy_levels: frozenset[str]  # which policy levels include this rule
    # Email-only: the anchored branch in RedactionEngine.redact assumes the
    # email local-part walk-back (_LOCAL_CHARS). Do not set on other rules.
    anchor: str | None = None


@dataclass(frozen=True)
class RedactionMetadataEntry:
    """Metadata for a single redaction — records rule name + position only.

    Never stores the original plaintext.
    """

    rule_name: str
    start: int
    end: int
    replacement_length: int


@dataclass(frozen=True)
class RedactionResult:
    """Immutable result of a redaction pass."""

    text: str
    redacted_count: int
    metadata: tuple[RedactionMetadataEntry, ...]


# ---------------------------------------------------------------------------
# Built-in rule definitions (consistent with extract.py regex style)
# ---------------------------------------------------------------------------

_RULES: tuple[RedactionRule, ...] = (
    RedactionRule(
        name="ssn",
        pattern=re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        replacement="[SSN-REDACTED]",
        policy_levels=frozenset({"strict", "standard", "minimal"}),
    ),
    RedactionRule(
        name="email",
        pattern=re.compile(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        ),
        replacement="[EMAIL-REDACTED]",
        policy_levels=frozenset({"strict", "standard"}),
        anchor="@",
    ),
    RedactionRule(
        name="phone",
        pattern=re.compile(
            r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
        ),
        replacement="[PHONE-REDACTED]",
        policy_levels=frozenset({"strict", "standard"}),
    ),
    RedactionRule(
        name="name_context",
        pattern=re.compile(
            r"(?i)\b(?:patient\s+name(?P<pn>)\s*(?::\s*)?"
            r"(?=[^\W\d_](?:[\w\s\u0300-\u036f-]{0,80}?[^\x00-\x7f-]|[\w\s\u0300-\u036f]{0,80}?-))"
            r"|(?:patient|name|mr\.?|mrs\.?|ms\.?|dr\.?)\s*(?::\s*)?)"
            r"((?:[A-Za-z]{2,}(?![\w\u0300-\u036f-])(?:\s+[A-Za-z]{2,}(?![\w\u0300-\u036f-]))*\s+[^\W\d_](?:[^\W\d_]|[\u0300-\u036f])+(?:-[^\W\d_](?:[^\W\d_]|[\u0300-\u036f])+)?"
            r"(?:[^\S\n]+(?!(?:mrn|medical|patient|name|id|dob|date|ssn|address|phone|dr|mr|mrs|ms)(?![\w\u0300-\u036f-]))[^\W\d_](?:[^\W\d_]|[\u0300-\u036f])+(?:-[^\W\d_](?:[^\W\d_]|[\u0300-\u036f])+)?)*"
            r"|[^\W\d_](?:[^\W\d_]|[\u0300-\u036f])+(?:-[^\W\d_](?:[^\W\d_]|[\u0300-\u036f])+)?"
            r"(?:[^\S\n]+(?!(?:mrn|medical|patient|name|id|dob|date|ssn|address|phone|dr|mr|mrs|ms)(?![\w\u0300-\u036f-]))[^\W\d_](?:[^\W\d_]|[\u0300-\u036f])+(?:-[^\W\d_](?:[^\W\d_]|[\u0300-\u036f])+)?)+))"
            r"(?(pn)(?:[.,]?[ \t]+(?!(?:mrn|medical|patient|name|id|dob|date|ssn|address|phone|dr|mr|mrs|ms)(?![\w\u0300-\u036f-]))"
            r"(?-i:[^\W\d_a-z\u00df-\u00f6\u00f8-\u00ff])[\w/.'\u2019\u0300-\u036f-]*){0,3})"
        ),
        replacement="[NAME-REDACTED]",
        policy_levels=frozenset({"strict", "standard"}),
    ),
    RedactionRule(
        name="dob",
        pattern=re.compile(
            r"(?i)\b(?:dob|date\s+of\s+birth|birth\s*date)\s*(?::\s*)?"
            r"\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}"
        ),
        replacement="[DOB-REDACTED]",
        policy_levels=frozenset({"strict"}),
    ),
    RedactionRule(
        name="address",
        pattern=re.compile(
            r"\b\d{1,5}\s+[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*"
            r"\s+(?:St\.?|Ave\.?|Blvd\.?|Dr\.?|Rd\.?|Ln\.?|Ct\.?|Way)\b",
        ),
        replacement="[ADDRESS-REDACTED]",
        policy_levels=frozenset({"strict"}),
    ),
    RedactionRule(
        name="name_guard_tail",
        pattern=re.compile(
            r"\[NAME-REDACTED\][^\S\n]+(?i:medical|patient|name|id|dob|date|ssn|address|phone|dr|mr|mrs|ms)"
            r"(?![\w\u0300-\u036f-])"
            r"(?![^\S\n]*(?:(?i:id|name|legal)\b|(?i:no)\.)|[^\S\n]*[(:#])"
            r"[^\S\n]+(?!\[)(?!(?i:patient|name|dr|mr|mrs|ms|mrn|record|rec)\b)[^\s,.;:]+"
        ),
        replacement="[NAME-REDACTED] [ID-REDACTED]",
        policy_levels=frozenset({"strict"}),
    ),
    # RL-REDACT-001 additions (strict only — additive, no existing rule or
    # level changed). Context-labeled MRN, and slash/dash NUMERIC dates
    # (DOB/admission style, e.g. 01/02/1980). ISO-8601 collection timestamps
    # (2025-05-01) are deliberately NOT matched: they are the longitudinal
    # clinical signal RL exports exist to carry, and the yyyy-first shape
    # never matches the d{1,2}-first pattern below.
    # E-1c: the label may be followed by, in this order and each optional, one
    # "(qualifier)" of at most 40 characters, "#" or "no.", ":", and one
    # space-led separator from "-", en dash, em dash, "=" or ";", then the
    # identifier ("MRN (hospital): A12345", "MRN #: A12345", "MRN no. A12345",
    # "MRN - A12345"). The separator needs a space before it, so "MRN-a1234"
    # stays with underscore_labelled_id. Every optional piece carries its own
    # leading \s* and starts with a non-space character, so no two \s* are
    # ever adjacent and a long space run cannot backtrack quadratically (the
    # old "\s*[:#]?\s*" could, 2.2 s at 20k spaces).
    RedactionRule(
        name="mrn",
        pattern=re.compile(
            r"(?i)\b(?:mrn|medical\s+record\s+(?:number|no\.?))"
            r"(?:\s*\([^()\n]{1,40}\))?(?:\s*(?:no\.|#))?(?:\s*:)?(?:\s+[-\u2013\u2014=;])?"
            r"\s*[A-Z0-9][A-Z0-9/.-]{3,}\b"
        ),
        replacement="[MRN-REDACTED]",
        policy_levels=frozenset({"strict"}),
    ),
    # E-1c (strict only): spaced labelled patient identifiers and names that
    # name_context cannot see. Matches "patient id" or "patient name" followed
    # by a colon or a separator, and bare "patient" / "name" with a "(qualifier)"
    # and/or "#" / "no." before a required colon ("Patient #: 98765",
    # "Name (legal): Jane Doe"), then the value: a capitalised name of up to
    # four words (optionally "Last, First"), or one token. A word starts with
    # any non-lowercase letter (Latin, Cyrillic, Vietnamese, Turkish ...) and
    # "/" and "." stay inside it, so "A123.456" is not cut short. Side effects:
    # a trailing "." lets the name run into the next sentence ("Name (legal):
    # Jane Doe. Follow Up With Cardiology" loses up to four capitalised words
    # in total), and the value may follow a newline. An identifier containing
    # spaces ("98765 4321") is only partly matched. A bare label with a colon
    # and nothing else ("Patient: 98765") is NOT matched, and neither is
    # "Patient ID no.: 98765" (name_context, which runs first, takes "ID no"
    # as a name and leaves the number). Same piece rules as mrn above.
    RedactionRule(
        name="spaced_labelled_id",
        pattern=re.compile(
            r"(?i)\b(?:"
            r"patient\s+(?:id|name)\b(?:\s*\([^()\n]{1,40}\))?(?:\s*#)?"
            r"(?:\s*:(?:\s*[-\u2013\u2014=;])?|\s*[-\u2013\u2014=;])"
            r"|(?:patient|name)(?:\s*\([^()\n]{1,40}\)(?:\s*(?:no\.|#))?|\s*(?:no\.|#))"
            r"\s*:(?:\s*[-\u2013\u2014=;])?"
            r")\s*"
            r"(?:(?-i:[^\W\d_a-z\u00df-\u00f6\u00f8-\u00ff])[\w/.'\u2019\u0300-\u036f-]*"
            r"(?:,[ \t]+(?-i:[^\W\d_a-z\u00df-\u00f6\u00f8-\u00ff])[\w/.'\u2019\u0300-\u036f-]*)?"
            r"(?:[ \t]+(?-i:(?:de|la|del|van|der|von|da|di|du|le|bin|al)[ \t]+)*(?-i:[^\W\d_a-z\u00df-\u00f6\u00f8-\u00ff])[\w/.'\u2019\u0300-\u036f-]*){0,3}"
            r"|[^\W_][\w/.'\u2019-]*)"
        ),
        replacement="[ID-REDACTED]",
        policy_levels=frozenset({"strict"}),
    ),
    RedactionRule(
        name="numeric_date",
        pattern=re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"),
        replacement="[DATE-REDACTED]",
        policy_levels=frozenset({"strict"}),
    ),
    # E-1a (O-3, strict only, additive): underscore-joined labelled identifiers,
    # the shape unknown analytes are stored in (normalize.py: spaces -> "_").
    # Specific labels may omit the colon; bare "patient"/"name" need one, so
    # analyte-like tokens such as "name_of_test" or "patient_count_3" survive.
    # Rev 3: a value may run on across ":_", "#_" or ",_" (qualifier words such
    # as "mrn_number:_123" or "name:_doe,_jane"), specific labels take "#"/"."
    # separators like the spaced mrn rule, and the separator is unambiguous so
    # a long "_" run cannot backtrack quadratically.
    # E-1b: any label may carry one "_(word)" qualifier, a bare label may have
    # "#" or "no." before its colon, and "-", "=" or ";" may separate label and
    # value after ANY label, including after a bare label's colon
    # ("mrn_-_a12345", "patient:_-_jane"). The qualifier stays disjoint from
    # the neighbouring "_" runs because of its "(", and the "#"/"no." and
    # separator pieces because they start with a non-"_" character, so
    # matching stays linear.
    # E-1c: the qualifier may hold "_"-joined words ("mrn_(hospital_a):_x1",
    # at most 40 characters, no nested parenthesis; a single-word qualifier of
    # any length still matches, as in E-1b), "_" may sit between "#" /
    # "no." and a bare label's colon, the separator set gains en dash and em dash,
    # up to two separators may repeat ("mrn_=_=_a1"), a qualifier may follow the
    # colon ("mrn:_(hospital)_a1"), and a separator may follow the label with no
    # "_" at all ("mrn_-a1", "mrn-a1"; never before "REDACTED]", so the
    # "[MRN-REDACTED]" tag of an earlier rule is not matched again). Each new
    # piece starts with a non-"_" character, so no two "_*" runs are adjacent.
    RedactionRule(
        name="underscore_labelled_id",
        pattern=re.compile(
            r"(?i)(?<![^\W_])"
            r"(?:(?:patient_name|dob|date_of_birth|birth_?date|mrn|medical_record)"
            r"(?:_\((?:[^\W_]+|[^()\n]{1,40})\))?(?:_*[:#.]+)?"
            r"|(?:patient|name)(?:_[^\W_]+)?(?:_\((?:[^\W_]+|[^()\n]{1,40})\))?_*(?:(?:#|no\.)_*)?:)"
            r"(?:_+(?:\([^()\n]{1,40}\)_+)?(?:[-\u2013\u2014=;]_*){0,2}"
            r"|(?:[-\u2013\u2014=;]_*){1,2}(?!redacted\]))"
            r"[^\W_][\w/.'\u2019\-]*(?:[:#,]_+[^\W_][\w/.'\u2019\-]*)*"
        ),
        replacement="[ID-REDACTED]",
        policy_levels=frozenset({"strict"}),
    ),
    RedactionRule(
        name="underscore_numeric_date",
        pattern=re.compile(r"(?<=_)\d{1,2}[/-]\d{1,2}[/-]\d{2,4}(?!\d)"),
        replacement="[DATE-REDACTED]",
        policy_levels=frozenset({"strict"}),
    ),
)

# Valid policy levels
VALID_POLICY_LEVELS = frozenset({"strict", "standard", "minimal"})


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

_WORD_BOUNDARY = re.compile(r"\b")
# Must mirror the email rule local-part class [A-Za-z0-9._%+-] (pinned by HC-REDACT-012b).
_LOCAL_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._%+-")


class RedactionEngine:
    """Stateless, deterministic redaction engine.

    Usage::

        engine = RedactionEngine(policy_level="standard")
        result = engine.redact("Patient: John Doe, SSN 123-45-6789")
        assert "123-45-6789" not in result.text
    """

    def __init__(
        self,
        policy_level: str = "standard",
        rules: Sequence[RedactionRule] | None = None,
    ) -> None:
        if policy_level not in VALID_POLICY_LEVELS:
            raise ValueError(
                f"Invalid policy_level '{policy_level}'; "
                f"must be one of {sorted(VALID_POLICY_LEVELS)}"
            )
        self._policy_level = policy_level
        self._rules = tuple(rules) if rules is not None else _RULES

    @property
    def policy_level(self) -> str:
        return self._policy_level

    def _active_rules(self) -> tuple[RedactionRule, ...]:
        """Return rules that apply to the current policy level."""
        return tuple(
            r for r in self._rules if self._policy_level in r.policy_levels
        )

    def redact(self, text: str) -> RedactionResult:
        """Apply redaction rules and return an immutable result.

        The input ``text`` is never mutated — a new string is built.
        Metadata records rule name + character positions only;
        original plaintext is never stored.
        """
        if not text:
            return RedactionResult(text=text, redacted_count=0, metadata=())

        active = self._active_rules()
        metadata_entries: list[RedactionMetadataEntry] = []

        # We apply rules sequentially; each rule operates on the *current*
        # (already partially redacted) text so that earlier replacements don't
        # interfere with later rule positions.
        current_text = text
        total_redacted = 0

        for rule in active:
            new_text_parts: list[str] = []
            last_end = 0

            if rule.anchor is None:
                matches = rule.pattern.finditer(current_text)
            else:
                # Linear time: one match attempt per anchor, at the first \b
                # of the local-part run ending there (same matches as finditer).
                matches = []
                prev_end = 0
                at = current_text.find(rule.anchor)
                while at != -1:
                    ws = at
                    while ws > prev_end and current_text[ws - 1] in _LOCAL_CHARS:
                        ws -= 1
                    boundary = _WORD_BOUNDARY.search(current_text, ws, at)
                    m = rule.pattern.match(current_text, boundary.start()) if boundary else None
                    if m:
                        matches.append(m)
                        prev_end = m.end()
                    at = current_text.find(rule.anchor, max(at + 1, prev_end))

            for match in matches:
                start, end = match.start(), match.end()
                new_text_parts.append(current_text[last_end:start])
                new_text_parts.append(rule.replacement)

                metadata_entries.append(
                    RedactionMetadataEntry(
                        rule_name=rule.name,
                        start=start,
                        end=end,
                        replacement_length=len(rule.replacement),
                    )
                )
                total_redacted += 1
                last_end = end

            new_text_parts.append(current_text[last_end:])
            current_text = "".join(new_text_parts)

        return RedactionResult(
            text=current_text,
            redacted_count=total_redacted,
            metadata=tuple(metadata_entries),
        )
