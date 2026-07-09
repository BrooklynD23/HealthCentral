# AI Safety Policy

How the assistant stays educational and grounded, and where each boundary is enforced. Companion to [Data Privacy](data-privacy.md) and [HIPAA Controls](hipaa-controls.md); the CI enforcement lives in `scripts/agent_eval_gate.py` and the backend test suite.

## Product boundary (non-negotiable)

The application organizes health information, visualizes trends, and explains results with citations. It does **not** diagnose, treat, prescribe, dose, or replace professional care, and must never be positioned as doing so. Enforced by:

- `modules/interpret_safety.py` — prohibited-pattern checks (diagnosis, dosing, treatment directives) that all assistant output must pass; adversarial cases in `src/backend/tests/test_interpret_safety_adversarial.py`.
- The agent eval gate's `advice_leakage == 0` axis: advice-bait golden cases must produce template refusals, not free prose.

## Refusal and escalation boundaries

- Requests for diagnosis, medication changes, or treatment decisions get a refusal template plus redirection to a clinician.
- Emergency-signal content (e.g., crisis or acute-symptom language) escalates to an emergency disclaimer directing the user to local emergency services — the assistant never triages.
- Abstention is a scored behavior: golden cases where the correct terminal is "abstain/escalate" must hit that terminal at 100% for the CI gate to pass.

## Grounding, citations, and uncertainty

- Answers must be grounded in retrieved context and cited: `[REFERENCE:N]` for seeded reference knowledge, `[YOUR_RESULTS:N]` for the user's own observations. Session memory is labeled non-citable.
- The eval gate requires groundedness == 1.0 and citation coverage == 1.0 on answer-terminal cases.
- When retrieval is insufficient, the assistant says so rather than filling gaps from the model's parametric knowledge; `modules/faithfulness.py` and `modules/verifier_agent.py` back-check outputs. (Current faithfulness scoring is rule-based; an NLI-model upgrade is on the roadmap.)

## Prompt injection

Retrieved documents, memory items, and any external text are data, not instructions. Injection cases live in `src/backend/tests/test_memory_integration.py` and `src/backend/tests/test_rag_pipeline.py`, and an adversarial injection corpus with an `injection_resistance` axis and an end-to-end compose check now runs in the CI eval gate (`scripts/agent_eval_gate.py`). Extending that corpus to instructions embedded in uploaded documents and in memory items remains open under HC-M05 in [feature_list.json](../../feature_list.json).

## PHI leakage

- No real PHI in development — synthetic seed data only.
- Anything leaving the local boundary (RL dataset export, any external runner) passes `modules/redaction.py` first and requires explicit user confirmation (see [Data Privacy — RL Dataset Export](data-privacy.md#reinforcement-learning-dataset-export)).
- PHI-leakage probes run in the CI eval gate (`phi_leakage` axis, must be 0); covering every export path is tracked under HC-M05. Redaction behavior is regression-tested in the backend suite.

## Change control

The modules named here are safety-critical: per [CLAUDE.md](../../CLAUDE.md), agents must get explicit human approval before modifying `modules/interpret_safety.py`, `modules/redaction.py`, `modules/faithfulness.py`, or `modules/verifier_agent.py`, and may never weaken a check or threshold to make something pass.
