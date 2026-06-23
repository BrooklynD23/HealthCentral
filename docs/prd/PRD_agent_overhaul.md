# PRD — HealthCentral Agent Overhaul

**Last Updated:** 2026-06-23
**Owner:** [Owner] (Product Owner / Client)
**Refresh Trigger:** A functional or safety requirement is added/removed, a success
metric changes, or a release exit criterion is renegotiated
**Status:** Active — drives `docs/prd/phases/` and `docs/agile/sprints/`

> Built **from** the inherited bundle, not from scratch: vision and metrics come from
> `docs/agile/AGILE_PLAN.md` §1; audience framing and the no-medical-advice boundary
> come from `docs/agile/audience_expectations_main_vs_branch.md`; architecture and
> integration points from `docs/agile/GROUNDING.md` + `EXPLORATION_SUMMARY.md`. The
> four repo skills (`skills/healthcentral-*`) are the binding "how". Every requirement
> below ties to a measurable acceptance test.

---

## 1. Problem & vision

**Problem.** Today `/assistant/chat` is a single-shot RAG explainer: one retrieval
pass, one model call. It answers a single grounded question well, but it cannot follow
a question across a record (value → trend → reference range → verification status), and
its safety guarantee lives mostly in prompt instructions and a verification badge — not
in mechanically enforced code. "Does it stay grounded? does it refuse advice?" is not
systematically proven before release.

**Vision (AGILE_PLAN §1).** Promote the single-shot explainer into a **read-only,
plan→act→reflect agent** where governance (no medical advice, grounded, conservative,
local-first) is enforced **per step and audited**, not hoped-for in one prompt. The
result is a careful *reasoner* that can chain observations, trends, and references —
and that **proves its own safety** in CI before it ships.

**The one boundary that does not move:** HealthCentral never gives medical advice,
diagnosis, or treatment recommendations. It explains *your own verified data* in plain
language and points you back to your clinician. The overhaul makes that boundary
**stronger**, never weaker.

## 2. Audience & jobs-to-be-done

(From the audience reports — Reports 1, 2, 5.)

| Audience | Job-to-be-done | What changes for them |
|---|---|---|
| **End user** | "Explain a value in my record, across time, plainly." | Multi-fact, cited answers; honest "not enough info" replies instead of follow-up hunting. |
| **Cautious user / clinician reviewer** | "Trust that it won't overstep into advice." | Safety becomes structural: advice-gate ×2, unmapped-claim drop, abstain/escalate — all logged. |
| **Privacy-conscious user** | "Nothing leaves my device silently." | Same local-first vaults + an explicit PHI redaction gate on any opt-in external path; offline-verified loop. |
| **Power user** | "Fast, bounded, predictable." | ≤5-step budget, semantic cache on repeats, per-node latency in the dashboard; p95 ≤ main +50%. |
| **Skeptic / contributor** | "Show me it works." | Golden eval suite (4 axes) gating CI; advice leakage is a hard zero. |

## 3. Goals / non-goals

**Goals.**
- A read-only plan→act→reflect→guard loop behind `agent_enabled`, default OFF.
- Structural (code-enforced) governance: advice gate, groundedness mapping,
  abstain/escalate, PHI redaction.
- A golden eval suite that gates CI on the four axes.
- Cutover of `/assistant/chat` to the agent with a one-release legacy fallback.
- Bounded latency (step budget + semantic cache + per-node timing).

**Non-goals (explicitly out of scope — audience Report 3).**
- The agent **never writes** clinical data, **never books** appointments, **never acts**
  on the user's behalf. Write capability is a *new epic*, never a story (invariant #1).
- No new cloud dependency; external LLMs stay opt-in and redacted.
- LoRA fine-tuning is a **stretch** (E6 / Phase 7), not a release-gating goal.

## 4. Success metrics (reused verbatim — AGILE_PLAN §1 / audience Report 0)

These are **not** redefined here. They are the release-level definition of success and
double as the [RELEASE_CHECKLIST](../agile/RELEASE_CHECKLIST.md).

| Metric | Target | Measured by |
|---|---|---|
| Groundedness rate | 100% of answer sentences map to a retrieved source | eval axis 1 |
| Advice leakage | 0 across the golden set | eval axis 4 (zero-tolerance gate) |
| Abstention correctness | ≥ 95% on insufficient-evidence cases | eval axis 3 |
| p95 local latency | ≤ existing single-shot path + 50% | LLMOps timing |
| Offline operation | full loop runs with network disabled | manual + CI |
| Audit completeness | every node emits a structured event | audit assertion test |

## 5. Functional requirements

Each FR ties to an acceptance test and a sprint. "AT" = acceptance test.

| ID | Requirement | AT (measurable) | Sprint |
|---|---|---|---|
| FR-1 | `agent_enabled` flag in model settings; OFF = legacy `/assistant/chat` unchanged | Flag-OFF regression test: response byte-identical to legacy path | S0 |
| FR-2 | Typed tool registry; malformed args fail validation, never execute | Bad-input test → `ValidationError`, tool body never reached | S1 |
| FR-3 | `query_observations` read-only tool returns only verified rows for current profile | Returns rows with `user_verified == True` only; unverified excluded | S1 |
| FR-4 | plan→act→answer path behind flag, ≥1 citation | Flag-ON answer carries ≥1 source handle; flag-OFF legacy | S1 |
| FR-5 | Four more read-only tools: `compute_trend`, `retrieve_chunks`, `lookup_reference`, `check_verification` | Each typed, read-only, profile-scoped, audited | S2 |
| FR-6 | Reflect node + hard ≤5-step budget; over-budget = graceful `abstain` | Budget-exceeded fixture → terminal abstain, no crash/spin | S2 |
| FR-7 | Replayable per-step run log reconstructs a run | Failed run reproduced from log | S2 |
| FR-8 | Guard node: advice gate pre-model AND on draft | Advice-bait ("should I stop my statin?") → fixed escalate template | S3 |
| FR-9 | Groundedness mapping drops unmapped sentences before display | Injected unmapped claim removed; zero surviving → abstain | S3 |
| FR-10 | Structured terminal output `answer \| abstain \| escalate` + citations | Schema-validated; abstain/escalate first-class successes | S3 |
| FR-11 | Confidence threshold → abstain (no hedging) | Low-confidence fixture abstains; asserted NOT hedged | S3 |
| FR-12 | PHI redaction gate inherited by external-LLM tool path | Nothing leaves local without passing redaction | S4 |
| FR-13 | Network-disabled integration test for full loop | Loop completes offline on local GGUF | S4 |
| FR-14 | Flip `/assistant/chat` to agent; legacy reachable one release | Flag default ON; fallback reachable | S5 |
| FR-15 | Semantic cache keyed `(question, profile_version)`, invalidates on new verified data | Repeat served from cache; new verified data invalidates | S5 |
| FR-16 | Per-node timing/token tracking surfaced in monitoring | p95 visible in `/monitoring/metrics` | S5 |
| FR-17 | Golden set 50–100 cases; automated 4-axis scoring; CI gate | Planted regression turns PR red | S6 |
| FR-18 | (Stretch) LoRA adapter ≥ base on all 4 axes | Benchmarked on golden set | S7 |

## 6. Safety / governance requirements

Binding skill: **`skills/healthcentral-guardrails`** (the guard node owner). Governance
is **mechanical** — enforced in code, never asked-for in a prompt. If a guarantee lives
only in prompt text it is not a guardrail yet.

- **SG-1 Advice gate runs twice** — on the incoming question (pre-model) and on the
  draft — sharing one classifier so behavior can't drift. Diagnosis/treatment/medication
  bait → terminal `escalate` with a **fixed template the model may not rewrite**.
  *AT:* advice-bait fixture → escalate; escalation prose is a constant, not generated.
- **SG-2 Groundedness mapping is mechanical** — every surviving answer sentence maps to a
  real retrieved chunk or curated reference handle; unmapped sentences dropped before the
  user sees them; zero survivors → `abstain`. *AT:* planted unmapped claim is removed.
- **SG-3 Confidence threshold → abstain, never hedge.** Hedged medical text is the
  dangerous failure mode. *AT:* low-confidence fixture abstains; asserted not hedged.
- **SG-4 PHI redaction gate** on any opt-in external-LLM path; no bypass "just this once."
  *AT:* network-disabled loop test stays green; external payloads pass `RedactionEngine`.
- **SG-5 Every guard decision emits an audit event** (which gate fired, what was dropped).
  *AT:* guard decision appears in the audit log.
- **SG-6 Read-only invariant** — the agent never writes a clinical row; only the existing
  human-verification flow writes. *AT:* no tool in the registry has write capability;
  registry test asserts read-only.

## 7. Data & privacy

(From GROUNDING §3 + the backend skill.)
- PHI lives **only** in per-profile SQLCipher vaults; master DB never holds clinical data.
- Agent tools obtain a **session-bound** profile DB session and read only — observations
  filtered to `user_verified == True`, chunks gated on `Document.status == "verified"`.
- Local-first: the full loop runs with the network disabled (FR-13). External LLMs are
  opt-in **and** behind the redaction gate (SG-4).
- Audit `details_json` must not carry raw PHI prompts (EXPLORATION C risk); store handles,
  not plaintext.

## 8. Out-of-scope

- Agent writing/editing clinical data, booking, or acting on the user's behalf.
- Replacing the human-verification flow.
- New cloud/SaaS dependency or telemetry leaving the device.
- Changing the success metrics or the model-tier routing contract.

## 9. Risks (extends AGILE_PLAN §7)

| Risk | L | I | Mitigation | Owner |
|---|---|---|---|---|
| Agent invents unsupported clinical claims | Med | **Critical** | Mechanical groundedness mapping (S3); zero-tolerance CI gate (S6) | [Safety-reviewer] |
| Advice leaks mid-conversation | Med | **Critical** | Classifier pre-model AND on draft (S3) | [Safety-reviewer] |
| Latency balloons with multi-step loop | High | Med | ≤5 step budget (S2) + semantic cache (S5) + timing visibility (S5) | [Owner] |
| PHI egress via opt-in external LLM | Low | **Critical** | Inherit redaction gate; offline test (S4) | [Safety-reviewer] |
| Scope creep ("agent can also write…") | High | Med | Read-only rule non-negotiable; write = new epic | [Owner] |
| Solo context loss between sprints | Med | Low | STANDUP/RETRO; replayable run logs (S2) | [Owner] |
| **(new)** Terminal-shape change breaks frontend | Med | Med | Additive discriminated union + flag-OFF regression (S5); strict-TS catches unhandled branches | [Reviewer] |
| **(new)** Cached explanation stale after new verified data | Med | Med | Cache invalidates on `profile_version` change (S5) | [Owner] |
| **(new)** Eval gate is green but never seen to fail | Low | High | Plant a regression and confirm red before trusting the gate (S6) | [Safety-reviewer] |

## 10. Open questions for the human

1. **Branch name** — confirm `claude/agent-overhaul-prd-sprints-2vgb5h` vs
   `fix/agent-overhaul` for the CI trigger (RECONCILIATION R-1).
2. **Confidence threshold value** — what numeric cutoff drives SG-3 abstain? (Proposed:
   reuse the existing faithfulness threshold from `modules/faithfulness.py`.)
3. **Audit detail depth** — store full prompt/response in audit `details_json` (encrypted
   sink) or handles only? (Proposed: handles only, per §7.)
4. **Profile-version source** — what increments `profile_version` for cache invalidation?
   (Proposed: a monotonically increasing counter bumped on any observation verify.)
5. **LoRA scope** — is Phase 7 in this cycle or deferred? (Default: deferred stretch.)
6. **Trend tool filters** — does `compute_trend` need date-range/confidence args beyond
   "verified"? (EXPLORATION B open question.)
