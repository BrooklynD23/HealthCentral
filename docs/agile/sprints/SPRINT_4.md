# Sprint 4 — PHI gate + external path (07-20 → 07-26)

**Last Updated:** 2026-06-24 (S4 delivered, commit 43f7a4b)
**Owner:** [Owner] · **Safety:** [Safety-reviewer]
**Refresh Trigger:** S4 story scope/AC, redaction-gate contract, or offline-test harness changes
**Release:** R2 · **Epic:** E2 · **Phase:** [PHASE_4](../../prd/phases/PHASE_4_phi_gate.md)

## Goal
Safe opt-in egress: redaction gate inherited; full loop proven offline; golden set ~30.

## Stories
| ID | Story | Acceptance criteria | Pts | Status |
|---|---|---|---|---|
| S4-1 | PHI redaction gate inherited by the agent's external-LLM path | nothing leaves local without passing existing redaction | 5 | **DELIVERED** |
| S4-2 | Network-disabled integration test for the full loop | loop completes offline on local GGUF | 3 | **DELIVERED** |
| S4-3 | Grow golden set to ~30 incl. advice-bait + abstention categories | categories represented; all pass | 3 | **DELIVERED** |

All three stories landed in commit `43f7a4b` (S4 — PHI redaction gate + offline test +
golden set to ~30). Agent suite: **40 passed, 6 skipped**. Golden set is now 30 cases
(9 grounded, 8 abstain, 8 advice-bait, 5 mixed) — S6 grows it further to 50–100. The
agent has **no external-egress call site today** (verified by grep of `modules/agent/`
at implementation time), so `redaction_gate.py` ships as a forward-looking mandatory
chokepoint for any FUTURE agent external-LLM tool, not a path with a live caller yet —
distinct from `core/external_runner.py`'s existing `/assistant/`-scoped enforcement.
R-12 (planner analyte-synonym gap, opened at S3 close-out) is RESOLVED as part of this
sprint via a `nodes/plan.py` fix (`_detect_topics()`), unblocking the
`mixed-partial-grounding` golden case — see RECONCILIATION.md R-12 and SPRINT_3.md.

## DoR / DoD
- **DoR:** AC + touched-files + proving tests in `test_s4_phi_gate.py`.
- **DoD:** green CI; external-path act events record `redacted: true`; **no bypass**
  exists in `redaction_gate`; offline test green; proof bundle passes. [Safety-reviewer]
  sign-off on S4-1/S4-2.
  **Status:** no-bypass and offline-test-green are DELIVERED and unit/integration
  tested. "External-path act events record `redacted: true`" does not yet apply
  live: there is no external-path caller in the agent graph today (verified by
  grep), so no `agent.act` event with `external:true` is emitted anywhere — the
  assertion will become checkable once a future sprint adds the first agent tool
  that calls out. [Safety-reviewer] sign-off still pending (process item, not
  code).

## Test-coverage plan
- **Eval axes:** axis 4 (advice leakage) + axis 3 (abstention) as the set grows to ~30.
- **Guard/answer-path rule:** advice-bait + abstain + grounded all represented (the set
  only grows these categories, never drops them).
- **Unit suites:** `test_s4_phi_gate.py` — all live: gate signature has no bypass
  param (`test_s4_1_redaction_gate_signature_has_no_bypass`), payload redacted
  before any (hypothetical) egress (`test_s4_1_payload_redacted_before_external_call`),
  two added fail-closed cases (`test_s4_1_gate_fails_closed_on_invalid_policy_level`,
  `test_s4_1_gate_fails_closed_when_engine_raises`), offline-loop-completes
  (`test_s4_2_offline_loop_completes`), golden-categories-pass
  (`test_s4_3_golden_set_categories_pass`). Coverage target: **≥ 90%** (PHI-critical).

## Code templates (delivered, commit 43f7a4b)
- `modules/agent/guardrails/redaction_gate.py` (`gate_external_payload`, adapter over
  `modules/redaction.py`, no bypass; docstring documents the no-live-caller-today
  scope note above).
- Offline integration test (S4-2) lives in `test_s4_phi_gate.py`.

## Standup / retro pointers
- STANDUP daily; RETRO Sunday — iteration Q (PHI egress): confirm the offline test
  truly disables the network and asserts no external call.
