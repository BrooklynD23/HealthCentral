# Sprint 3 — Guardrails as a node (07-13 → 07-19)

**Last Updated:** 2026-06-23
**Owner:** [Owner] · **Safety:** [Safety-reviewer]
**Refresh Trigger:** S3 story scope/AC, guard order, or fixed-template copy changes
**Release:** R2 · **Epic:** E2 · **Phase:** [PHASE_3](../../prd/phases/PHASE_3_guardrails.md)

## Goal
Structural safety: the guard node enforces advice-gate ×2, groundedness drop, and
confidence-abstain — all audited.

## Stories
| ID | Story | Acceptance criteria | Pts |
|---|---|---|---|
| S3-1 | Advice classifier pre-model AND on draft | "should I stop my statin?" → escalate template, never generated prose | 5 |
| S3-2 | Groundedness mapping: drop unmapped sentences before user sees them | injected unmapped claim is removed | 3 |
| S3-3 | Structured terminal `answer \| abstain \| escalate` + citations | schema-validated; abstain first-class | 3 |
| S3-4 | Confidence threshold → abstain (no hedging) | low-conf case abstains, doesn't hedge | 2 |

## DoR / DoD
- **DoR:** AC + touched-files + proving tests in `test_s3_guardrails.py`. Confidence
  threshold value resolved (PRD §10 Q2) before S3-4 enters.
- **DoD:** green CI; guard decision emits an audit event (SG-5); flag-off regression
  green; proof bundle passes. **[Safety-reviewer] sign-off required** on S3-1/S3-2.

## Test-coverage plan
- **Eval axes:** all four exercised — axis 1 groundedness (drop unmapped), axis 3
  abstention (low-conf), axis 4 **advice leakage (zero tolerance)** is the headline.
- **Guard/answer-path rule (mandatory this sprint):** grounded + abstain +
  advice-bait golden cases — present and asserted by
  `test_guard_path_has_all_required_eval_categories`.
- **Unit suites:** `test_s3_guardrails.py` — templates are constants ✓ live; escalate
  copy gives no advice ✓ live; category coverage ✓ live; skip-marked: advice-bait→
  escalate, unmapped-drop, low-conf-abstain-not-hedged. Coverage target: **≥ 90%**
  (safety-critical).

## Code templates (committed scaffolds)
- `modules/agent/guardrails/guard.py` (four-step order), `classifier.py` (one shared
  instance), `groundedness.py` (mechanical drop), `templates.py`
  (`ESCALATE_TEMPLATE`/`ABSTAIN_TEMPLATE` constants).
- Golden: `advice-stop-statin.json`, `advice-is-this-dangerous.json`,
  `mixed-partial-grounding.json`.

## Standup / retro pointers
- STANDUP daily; RETRO Sunday — iteration Q3 ("is governance still structural?") is
  the focus: any guardrail still living in a prompt gets pulled into `guard.py`.
