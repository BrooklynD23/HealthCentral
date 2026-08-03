---
name: asclexis-guardrails
description: Medical-safety guardrails for Asclexis's agent and assistant. Use whenever creating or modifying the guard node, the advice classifier, abstention/escalation templates, groundedness/claim-to-source mapping, confidence thresholds, or the PHI redaction gate before any opt-in external LLM call. Triggers include any work mentioning "guardrail", "medical advice", "abstain", "escalate to doctor", "groundedness", "claim mapping", "PHI redaction", "confidence threshold", or anything that decides whether the model is allowed to speak.
---

# Asclexis Guardrails — medical safety

This skill owns the `guard` node and everything that decides whether output is
allowed to reach the user. Governance here is MECHANICAL — enforced in code, never
"asked for" in a prompt. If a guarantee lives only in prompt text, it is not a
guardrail yet; move it here.

## What the guard node does (in order)

1. **Advice gate.** Run the advice classifier on the draft. If it requests or
   contains diagnosis/treatment/medication recommendations → terminal `escalate`
   with a FIXED template. Never let the model generate the escalation prose.
2. **Groundedness mapping.** For each answer sentence, confirm it maps to a real
   retrieved chunk or curated reference handle. Drop any unmapped sentence BEFORE
   the user sees it. An answer with zero surviving grounded sentences → `abstain`.
3. **Confidence threshold.** Below threshold → `abstain`. Do NOT hedge. Hedged
   medical text is the dangerous failure mode — abstention is the safe one.
4. **Emit audit event** for the decision (which gate fired, what was dropped).

## Where the advice gate runs

Twice: **pre-model** (on the incoming question) AND **on the draft**. Bait can
enter mid-conversation, so a single front-door check is insufficient. Both checks
share one classifier so behavior can't drift between them.

## Fixed templates (never generated)

- **Escalate**: a static "this is a question for your doctor / pharmacist" block,
  optionally listing which verified values are relevant — values only, no advice.
- **Abstain**: a static "there isn't enough verified information to explain this"
  block. Suggest verifying the relevant document, never speculate to fill the gap.

Store templates as constants in `modules/agent/guardrails/templates.py`. Editing
copy is a code change with a test, not a prompt tweak.

## PHI redaction gate

The agent's external-LLM tool path INHERITS the existing opt-in redaction check.
Nothing leaves the device without passing it. There is a network-disabled
integration test asserting the full loop completes locally; keep it green. No
exceptions, no "just this once for debugging" bypass.

## Terminal contract

The guard returns a schema-validated `answer | abstain | escalate` plus citations.
`abstain` and `escalate` are first-class successes — evals score them as CORRECT
when appropriate, so never treat them as error paths.

## Verify before done

Advice-bait fixture → `escalate`; planted unmapped claim → dropped; low-confidence
fixture → `abstain` (assert NOT hedged); network-disabled loop test passes; guard
decision appears in the audit log.

## Never

Generate escalation/abstention prose · let an unmapped claim survive · hedge below
threshold · run the advice gate only once · bypass redaction for any reason ·
treat abstain/escalate as failures.
