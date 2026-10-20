# RRSI / harness2 for HealthCentral agents: research package (2026-10-20)

**Last Updated:** 2026-10-20
**Owner:** repository owner
**Refresh Trigger:** any owner answer in [04-owner-questions.md](04-owner-questions.md); arXiv 2609.24972 or 2610.14224 becomes reachable and is read; PR #211 merges; any change to `src/backend/modules/agent/` or `.claude/workflows/rsi-loop.js`.

> **Point-in-time research (2026-10-20).** Planning and documentation only. No product code changed, and no owner gate is answered here. HealthCentral was read at `origin/main` `d5ca71d`. `google-research/harness2` was read as text at `1cfe254`; none of its code was run. Markers: **[V]** read in the file or command output at that commit; **[I]** inferred from what was read; **[U]** could not be checked (used only where a source was unreachable).

## The question

The owner asked for a research pass on RRSI using `google-research/harness2` as its base, with verdicts that depend on how the user consents to each function, reviewed adversarially. The functions are in-app agents that access the patient's items, convert files into a readable format, and run data analytics, plus a dev / expanded mode in which the user can see everything the agent does, so that agents do not pass critical gates unchecked.

## The owner's intent (2026-10-20, owner in chat)

> "yes, start the RRSI research pass in parallel. It is based off this repo. https://github.com/google-research/harness2. Depending on how the user consents to some of our functionalities, the research agents & their subagents should provide verdicts (Have [reviewer model] as adverserial review of the verdicts). Because we want our custom agents in HealthCentral to be able to access items, convert files into a readable format for user, data analytics, etc. However, the user would be able to see (in dev / expanded mode), to see everything the agent is doing for some aspects of HITL so that we're not allowing agents to go through critical gates unchecked."

Verbatim except one edit: the name of the reviewing model is replaced by "[reviewer model]", because this package does not name models.

## The headline finding

**harness2 is not the RRSI code.** It implements Harness² (arXiv 2610.14224), a different paper that shares two authors with RRSI (arXiv 2609.24972). It has no critic, pruner or OOD check, adopts harness changes automatically with no human gate, and runs with permission-bypass flags and open network. It is useful to HealthCentral only as a source of patterns for the development harness. Details: [01-harness2.md](01-harness2.md).

## Method

1. **Two mapping passes.** One read harness2 (read-only clone, text only). One mapped HealthCentral's agent, consent, audit, ingest, export and analytics code and the RSI tracks.
2. **Five verdict passes**, one per question below. Each gave a verdict, a per-consent-tier table, critical gates, a design, risks, owner questions and evidence.
3. **Five adversarial passes.** An independent reviewer per verdict, told to refute it against the code, returned upheld true/false, a revised verdict, tagged refutations and missed risks.
4. **Synthesis.** Where a reviewer did not uphold a verdict, its revised verdict is adopted. Every refutation was adopted (two in a narrower form); none was rejected. The synthesizer re-read the load-bearing lines at `d5ca71d` (the build-program default, the rsi-loop gate, the act payload, the legacy fallback, the cache-hit and pre-model-escalate audit gaps, the SG-6 test, the frontend toggle, the migration chain, and the harness2 title, Python floor, bypass flags and judge boundary). Resolutions: [03-adversarial-review.md](03-adversarial-review.md).

## Verdicts

| # | Question | Final verdict | Upheld by adversarial review? | Key critical gates |
|---|---|---|---|---|
| 1 | Track 1: adopt, adapt or reject harness2 for the dev harness? | **ADAPT, patterns only**: budget identity, deterministic critic, leak tripwire, accepted archive; never vendor or run harness2 | Yes, with corrections (default is standing, not off; gate reads agent-reported diffs; `recurring-failures.md` unguarded; S5 scope inconsistent) | Owner merges every promotion; no deletion or rewrite in any ALLOW file; no edits to tests, gates, thresholds, ask-first modules or `rsi-loop.js` from the loop; S5 never in agent context |
| 2 | How should agents read the patient's items? | **ADAPT**: keep the read-only agent as baseline; new capabilities off by default, per-action then standing consent; expanded mode is visibility only | Yes, with corrections (care tasks not verified-only; answers persisted; fallback breaks fail-closed) | No writes, verifies, exports, off-device calls or consent changes in any tier; no cross-profile access; gated outcomes are terminals that never reach the legacy fallback |
| 3 | Converting files into a readable format | **ADAPT (revised)**: deterministic re-render of verified data, read-only, cited, unstored; an LLM rewrite only after its own gates | **No**: revised verdict adopted (no LLM on the agent path; guard chain cannot vet prose; trace is raw PHI; toggle needs a migration; new uploads get counts only) | Human-only verify; no agent export, file write or external-runner call; escalate and critical-value text unchanged; no threshold edits to make conversion pass |
| 4 | Data analytics on the patient's data | **ADAPT (revised)**: trend and adherence as read-only template tools; wearables correlation deferred | **No**: revised verdict adopted (SG-6 does not cover new tools; answers persist; cache ignores doses; harness2 adopts automatically; templates are the primary wording control) | No writes or dose/schedule changes; describe, never recommend; no correlation or causal wording; analytics never off-device |
| 5 | Dev / expanded trace and HITL | **ADAPT**: per-request trace in the chat response, handle-only by default, not stored; critical gates stop in every mode; trace donation only after owner rulings | Yes, with corrections (migration needed; "never stored" conflicts with rated-turn trace donation; cache-hit and pre-model escalate unaudited) | Advice escalation never approvable; off-device and break-glass need their own confirmation; donation collect needs explicit confirmation and a leak check; no "approve all" |

Shared rules that all four Track-2 verdicts depend on (X1-X11) are in [02-verdicts.md](02-verdicts.md) §0.2.

## Files

- [01-harness2.md](01-harness2.md): what `google-research/harness2` is, with path:line evidence.
- [02-verdicts.md](02-verdicts.md): final verdicts, per-consent-tier tables, critical gates, design, risks.
- [03-adversarial-review.md](03-adversarial-review.md): every refutation and how it was resolved.
- [04-owner-questions.md](04-owner-questions.md): 27 de-duplicated owner questions with options and a recommendation; none answered.
- [05-report-angle.md](05-report-angle.md): how the senior report can show RSI developing the repo (Track 1) and improving the user experience (Track 2 and in-app agents), with strict status labels.

Related: the earlier package [2026-10-17-rsi-opt-in-data](../2026-10-17-rsi-opt-in-data/00-README.md); the capstone section [rsi-in-development-and-application.md](../../capstone-report/rsi-in-development-and-application.md); owner decisions in [owner-decisions-2026-09-27.md](../../capstone-report/owner-decisions-2026-09-27.md).
