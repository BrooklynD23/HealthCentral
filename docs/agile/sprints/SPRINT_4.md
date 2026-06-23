# Sprint 4 — PHI gate + external path (07-20 → 07-26)

**Last Updated:** 2026-06-23
**Owner:** [Owner] · **Safety:** [Safety-reviewer]
**Refresh Trigger:** S4 story scope/AC, redaction-gate contract, or offline-test harness changes
**Release:** R2 · **Epic:** E2 · **Phase:** [PHASE_4](../../prd/phases/PHASE_4_phi_gate.md)

## Goal
Safe opt-in egress: redaction gate inherited; full loop proven offline; golden set ~30.

## Stories
| ID | Story | Acceptance criteria | Pts |
|---|---|---|---|
| S4-1 | PHI redaction gate inherited by the agent's external-LLM path | nothing leaves local without passing existing redaction | 5 |
| S4-2 | Network-disabled integration test for the full loop | loop completes offline on local GGUF | 3 |
| S4-3 | Grow golden set to ~30 incl. advice-bait + abstention categories | categories represented; all pass | 3 |

## DoR / DoD
- **DoR:** AC + touched-files + proving tests in `test_s4_phi_gate.py`.
- **DoD:** green CI; external-path act events record `redacted: true`; **no bypass**
  exists in `redaction_gate`; offline test green; proof bundle passes. [Safety-reviewer]
  sign-off on S4-1/S4-2.

## Test-coverage plan
- **Eval axes:** axis 4 (advice leakage) + axis 3 (abstention) as the set grows to ~30.
- **Guard/answer-path rule:** advice-bait + abstain + grounded all represented (the set
  only grows these categories, never drops them).
- **Unit suites:** `test_s4_phi_gate.py` — gate signature has no bypass param ✓ live;
  skip-marked: payload-redacted-before-egress, offline-loop-completes,
  golden-categories-pass. Coverage target: **≥ 90%** (PHI-critical).

## Code templates (committed scaffolds)
- `modules/agent/guardrails/redaction_gate.py` (`gate_external_payload`, adapter over
  `modules/redaction.py`, no bypass).
- Offline integration test stub (S4-2) lives in `test_s4_phi_gate.py`.

## Standup / retro pointers
- STANDUP daily; RETRO Sunday — iteration Q (PHI egress): confirm the offline test
  truly disables the network and asserts no external call.
