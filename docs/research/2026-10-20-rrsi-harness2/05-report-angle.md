# Report angle: RSI developing the repo, and RSI improving the user experience

**Last Updated:** 2026-10-20
**Owner:** repository owner
**Refresh Trigger:** the first `rsi:` promotion PR is opened or merged; any Track-2 item below changes status; PR #211 merges; the owner answers OQ-1 or OQ-8.

> **Point-in-time research (2026-10-20).** Advice for the senior project report, not report text. It builds on the capstone section [rsi-in-development-and-application.md](../../capstone-report/rsi-in-development-and-application.md) (cited below as "RSI section"). Status labels are strict and used exactly as defined in §1. Nothing planned is described as built.

## 1. Status labels

| Label | Meaning | Evidence needed |
|---|---|---|
| **Merged** | On `origin/main` | A merge commit or a merged PR |
| **Merged, not yet run** | On main, but no run output exists | As above, plus no run artifact |
| **In review** | An open PR, not merged | gh REST `state: open` |
| **Planned** | A design or plan document only | A plan or research file |
| **Proposed here** | First suggested in this package; not yet planned | This folder |

## 2. Track 1: RSI developing the repo

What the report can claim, and how strongly:

| Item | Status | Evidence |
|---|---|---|
| Dev-harness mod `.claude/mods/asclexis-rsi/` (metadata-only logs, guard and hint rules, `/rsi` scoreboard) | **Merged** | RSI section §6 (#127); files on main |
| `rsi-loop` workflow (Mine → Reflect → Propose ≤3 → Gate → Publish; never merges) | **Merged, not yet run** as of the RSI section's 2026-10-18 status | RSI section §6 (#126, #129). gh REST lists no PR titled `rsi: …` (the title `rsi-loop.js:252` uses) as of 2026-10-20 [V] |
| Runs after every build-program run (RSI-BUILD) | **Merged** | `.claude/workflows/build-program.js:26`, `:177-183` [V] |
| Human merge of every promotion (AUTO-MERGE) | **Merged** (as an owner rule and workflow behaviour) | owner-decisions :206; `rsi-loop.js:252` |
| Seed failures (5 rules, 14 replay cases) | **Merged** | `hooks/rules.ts`; `replay/cases.ts`; RSI section §5 |
| Before/after per-tool failure rate | **Not measured** | RSI section §6 "Results still to come" |
| Budget ledger, deterministic critic, leak tripwire, accepted archive (borrowed from harness2) | **Proposed here** | [02-verdicts.md](02-verdicts.md) §1.3 |
| CI job for the replay set | **Proposed here** (owner question OQ-4) | 02 §1.3 item 7 |

**The honest Track-1 story.** The repo has a bounded, human-gated self-improvement loop for its own build harness, merged and wired into every build run. Its gates are: a 3-file write scope, a deny list over tests, gate scripts, thresholds and ask-first modules, additions-only on the rule table and replay set, and an owner merge. The report should also say what review found: the gate is deterministic code over strings the agents report, so the owner's read of the real diff is the independent check; one ALLOW file has no deletion guard; and CI does not yet run the replay set. Naming these limits is stronger than hiding them, and each one has a proposed fix.

**What not to claim.** No measured improvement, because no promotion has merged. No critic, pruner or OOD check, because none exists, and harness2 does not have them either.

**Fix before citing.** RSI section §2 line 17 says Track 1 is "in review (PR pending). Not merged." and line 27 says the report "does not claim the workflow exists on main". Its own §6 says both parts are merged. This package does not edit that file; see OQ-8.

## 3. Track 2 and the in-app agents: RSI improving the user experience

| Item | Status | Evidence |
|---|---|---|
| Read-only chat agent: deterministic plan → act → reflect → draft → guard, 8 query tools, `MAX_STEPS = 5`, every node audited | **Merged** | `src/backend/modules/agent/graph.py`, `state.py:19`, `tools/registry.py:44-64` [V] |
| Track-2 legacy citation eval harness and its baseline (abstain rate 0.75-1.00, cited-answer rate 0.00-0.05, n = 20, one run per model) | **Merged** | RSI section §6 (#150) |
| Constrained-decoding citation fix (LEGACY-CITE-PROMPT) | **Planned** | RSI section §3 item 2 |
| Opt-in donation consent schema, routes and Settings card (RSI1-DONATE PR-1) | **In review** | PR #211, open, not merged, head `07866ed` (gh REST, 2026-10-20) [V] |
| Donation collect, redaction pipeline, leak evaluation | **Planned** | `docs/plans/2026-10-17-rsi1-opt-in-donation-pipeline-plan.md` |
| Agent capability consent (per-action and standing), readable-view tool, adherence analytics tool | **Proposed here** | 02 §§2-4 |
| Dev / expanded trace panel ("What the agent did") | **Proposed here** | 02 §5 |
| An RSI loop over donated agent traces | **Proposed here**, and blocked on owner questions OQ-24 and OQ-27 | 02 §5.3, §5.4 D |
| Wearables-to-lab correlation | **Deferred** (non-goal in the wearables program) | `docs/plans/2026-10-13-wearables-00-program.md:26` |

**The honest Track-2 story.** The improvement claim the report can make today is about measurement, not results: there is a merged harness that measures how often local models fail to cite, and a baseline. The UX story for the in-app agents is a design: consent tiers that grow what the agent may read only when the patient allows it, critical gates that no tier and no view can pass, and a trace view that lets the patient see each step. That trace view is the human-in-the-loop element the owner asked for. It is **Proposed here**, and the report must present it as design.

**Points of difference worth making in the report** (each backed by a finding, not a result):
- Visibility is not authority: expanded mode shows everything and approves nothing; advice escalation is never an approvable step (02 §5.1).
- The review found real defects in the current agent that the design must address before any capability is added: a fallback that can route a gated question to the legacy model path, a trace that holds raw values despite its own comment, and two paths without audit rows (02 §0.2, rules X3, X4, X7).
- Self-improvement on patient data is gated twice: by per-purpose donation consent and by an owner merge, with the evaluator outside the proposer's write scope.

## 4. Where harness2 fits in the report

Cite it as **Harness²** (arXiv 2610.14224, `google-research/harness2`), a source of patterns for Track 1: a fixed budget identity, an evaluator the method never imports, leak tripwires, and "no change" as a valid answer ([01-harness2.md](01-harness2.md) §2.2). State the contrast plainly: harness2 adopts changes automatically and runs with permission bypasses and open network; HealthCentral keeps a human merge and local-first. Keep RRSI (arXiv 2609.24972) as a separate citation for the critic, pruner and OOD ideas, marked "reported, not re-verified" until its arXiv page can be read (OQ-1).

## 5. Suggested figure and table

1. **Two-track diagram:** Track 1 (logs → mine → reflect → propose → gate → owner merge) and Track 2 (patient → consent tier → agent → critical gates → answer, with the trace view alongside). Mark each box with its §1 status label.
2. **Gate table:** one row per critical gate from 02 §1.2 and §5.2, with columns "who passes it" and "what evidence the human sees".
3. **Results table:** the existing Track-2 baseline (RSI section §6) plus empty rows for the Track-1 failure rate and the constrained-decoding re-run, labelled "to come".
