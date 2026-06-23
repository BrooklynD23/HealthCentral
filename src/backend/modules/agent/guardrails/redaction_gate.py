"""PHI redaction gate for the agent's external-LLM path (Phase 4, story S4-1).

Thin adapter over the EXISTING engine (modules/redaction.py:
``RedactionEngine(policy_level).redact(text)``). No new redaction logic. Every
external-runner call site routes its payload through this gate first. There is
NO bypass — not for debugging, not "just this once"
(skills/healthcentral-guardrails). Nothing leaves the device without passing it.
"""

from __future__ import annotations


def gate_external_payload(payload: str, policy_level: str = "standard") -> str:
    """Return the redacted payload; raise if redaction is unavailable.

    SCAFFOLD: Sprint 4 (S4-1). At implementation time::

        from modules.redaction import RedactionEngine
        result = RedactionEngine(policy_level=policy_level).redact(payload)
        return result.text

    The network-disabled integration test (S4-2) asserts the full loop completes
    locally without ever reaching this gate (no external call by default).
    """
    raise NotImplementedError("S4-1: inherit modules.redaction RedactionEngine; no bypass")
