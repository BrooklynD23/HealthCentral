# Phase 3 — Guardrails as a Node

**Last Updated:** 2026-06-23
**Owner:** [Owner]
**Refresh Trigger:** Guard order, advice classifier, fixed templates, or terminal schema change

| Map | Value |
|---|---|
| Release | **R2 — Governed & live** |
| Epic | **E2 — Guardrails** (`skills/healthcentral-guardrails`) |
| Sprint | **S3** (S3-1…S3-4) |
| Binding skills | `healthcentral-guardrails`, `healthcentral-agent`, `healthcentral-evals` |

## Objective
Make safety structural: a dedicated `guard` node that runs the advice classifier
pre-model AND on the draft, drops unmapped sentences mechanically, abstains below a
confidence threshold (never hedges), and returns a schema-validated `answer | abstain |
escalate` — every decision audited.

## Exit criteria
- "should I stop my statin?" → `escalate` with a **fixed template**, never generated prose (FR-8).
- Injected unmapped claim is removed before display; zero survivors → `abstain` (FR-9).
- Terminal output schema-validated; abstain/escalate first-class successes (FR-10).
- Low-confidence fixture → `abstain`, asserted **not** hedged (FR-11).
- Each guard decision emits an audit event (SG-5).

## CONTRACTS

### API / routes
No new routes; `endpoints.md` diff: **none** (response shape change ships at cutover, Phase 5).

### Guard order (guardrails skill — mechanical, in this order)
1. **Advice gate** on the draft (and pre-model on the question) → `escalate` + fixed template.
2. **Groundedness mapping** → drop unmapped sentences; zero survivors → `abstain`.
3. **Confidence threshold** → below → `abstain` (no hedge).
4. **Emit audit event** (which gate fired, what was dropped).

### Pydantic / module contracts (`modules/agent/guardrails/`)
```python
# classifier.py — ONE classifier shared by both call sites (pre-model + draft)
class AdviceVerdict(BaseModel):
    is_advice_seeking: bool
    category: Literal["diagnosis","treatment","medication","none"]
# guard.py
class GuardDecision(BaseModel):
    terminal: Literal["answer","abstain","escalate"]
    surviving_sentences: list[str]
    dropped_sentences: list[str]
    gate_fired: Literal["advice","groundedness","confidence","none"]
```
**Fixed templates** (`guardrails/templates.py`) are module constants — editing copy is a
code change with a test, never a prompt tweak:
- `ESCALATE_TEMPLATE`: static "this is a question for your doctor / pharmacist", may list
  relevant **verified values only**, no advice.
- `ABSTAIN_TEMPLATE`: static "there isn't enough verified information to explain this";
  suggests verifying the relevant document; never speculates.

### Audit-event schema
`event_type="agent.guard"`, `details={gate_fired, dropped_count, terminal}`. Never log the
dropped sentence text if it could carry PHI — log counts + handles.

## CONTACTS (RACI)
| Role | Who |
|---|---|
| Responsible | [Safety-reviewer] |
| Accountable | [Owner] |
| Consulted | [Reviewer] (terminal schema → frontend) |
| Informed | [Reviewer] |

## Dependencies
Phase 2 (draft node, terminal contract, run log). The agent **calls** guard, never inlines it.

## Risk + mitigation
| Risk | Mitigation |
|---|---|
| Advice leaks mid-conversation | Classifier runs pre-model AND on draft, shared instance (no drift) |
| Unmapped claim survives | Mechanical sentence→source mapping; drop before display |
| Hedged medical text | Below threshold = abstain; test asserts NOT hedged |
| Escalation prose drifts | Template is a constant; covered by a copy test |
