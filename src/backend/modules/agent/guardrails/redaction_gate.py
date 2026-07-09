"""PHI redaction gate for the agent's external-LLM path (Phase 4, story S4-1).

Thin adapter over the EXISTING engine (modules/redaction.py:
``RedactionEngine(policy_level).redact(text)``). No new redaction logic. Every
external-runner call site routes its payload through this gate first. There is
NO bypass — not for debugging, not "just this once"
(skills/healthcentral-guardrails). Nothing leaves the device without passing it.

Current state of the agent's external egress (verified at S4 implementation
time by searching ``modules/agent/`` for any external-runner/external-LLM call
path): there is NONE. ``run_agent`` (graph.py) is fully local/deterministic —
``plan`` never calls a real model (nodes/plan.py docstring), every tool in
``tools/`` is read-only against the local profile-scoped SQLite session, and
``draft``/``guard`` only compose/filter already-gathered local evidence. The
only external-call path in this codebase today is ``core/external_runner.py``
(``ExternalModelRunner``), which belongs to the separate, opt-in, non-agent
``/assistant/`` flow and already enforces its own strict redaction before any
provider call — that call site is OUT OF SCOPE for the agent overhaul (S5
wires `/assistant/` cutover, not S4) and is left untouched here.

So today ``gate_external_payload`` has no caller in the agent graph — by
design. It exists as the SINGLE mandatory chokepoint any future agent
external-egress tool MUST route its payload through before anything leaves
the device. (``sanitize_untrusted_field`` below IS called from the graph —
by ``draft`` on vault-derived free-text fields; that is inbound-field
hygiene, not external egress, and does not change this gate's charter.) The network-
disabled offline integration test (S4-2, ``test_s4_2_offline_loop_completes``)
asserts the full default loop never needs this gate at all: zero network
access end-to-end. If a future sprint adds an agent tool that calls out
(e.g. an LLM-backed planner/drafter), its call site MUST pass its outbound
payload through ``gate_external_payload`` first — no new redaction logic
should be written at that call site; this is the seam.
"""

from __future__ import annotations


def gate_external_payload(payload: str, policy_level: str = "standard") -> str:
    """Return the redacted payload; raise if redaction is unavailable.

    Thin adapter — all redaction logic lives in ``modules.redaction.
    RedactionEngine``; this function adds none of its own. Fail-closed: any
    exception raised while constructing the engine or redacting (e.g. an
    invalid ``policy_level``) propagates to the caller rather than being
    swallowed, and the unredacted ``payload`` is NEVER returned on that path.
    There is intentionally no bypass/skip parameter — the signature is
    enforced by ``test_s4_1_redaction_gate_signature_has_no_bypass``.
    """
    from modules.redaction import RedactionEngine

    result = RedactionEngine(policy_level=policy_level).redact(payload)
    return result.text


def sanitize_untrusted_field(text: str | None) -> str | None:
    """Neutralize injection markers and PHI patterns in a vault-derived field.

    Observation ``analyte``/``unit`` strings originate from document
    extraction — attacker-influenceable input that ``draft`` composes
    verbatim into the terminal text (HC-M05). This scrubs, in order:

      1. prompt-injection markers, using the SAME pattern list
         ``modules.rag.RAGModule`` applies to history/memory (imported, not
         copied, so the two surfaces cannot drift), and
      2. PHI patterns via the strict ``RedactionEngine`` rule set.

    Same thin-adapter charter as ``gate_external_payload``: no redaction
    logic of its own, no bypass parameter, and it never returns the raw
    ``text`` on an exception path — errors propagate (fail closed).
    """
    import re

    from modules.rag import RAGModule
    from modules.redaction import RedactionEngine

    if not text:
        return text

    sanitized = text
    for pattern in RAGModule.PROMPT_INJECTION_PATTERNS:
        sanitized = re.sub(pattern, "[SANITIZED]", sanitized, flags=re.IGNORECASE)
    return RedactionEngine(policy_level="strict").redact(sanitized).text
