# Owner questions

**Last Updated:** 2026-10-20
**Owner:** repository owner
**Refresh Trigger:** any answer below (record it in `docs/capstone-report/owner-decisions-2026-09-27.md` with the date and channel, then mark it here); the merge of PR #211.

> **Point-in-time research (2026-10-20). No gate below is answered.** Each question was merged from the five verdicts and their reviews ([02-verdicts.md](02-verdicts.md), [03-adversarial-review.md](03-adversarial-review.md)) and de-duplicated. Options are listed neutrally and are not ordered by preference; the recommendation is the research's suggestion only. "From" names the verdict questions merged into each item.

## A. Research record and Track 1 (development harness)

**OQ-1 Citation in the senior report.** harness2 implements Harness² (arXiv 2610.14224), not RRSI (arXiv 2609.24972), and contains no critic, pruner or OOD check. arXiv was unreachable this pass. How should the report cite it?
- (a) Cite Harness² and RRSI separately; credit harness2 only for the patterns borrowed; mark RRSI's critic, pruner and OOD figures "reported, not re-verified".
- (b) Drop RRSI until its arXiv page and any code are confirmed.
- (c) Keep the current notes unchanged.
- Recommendation: (a). It keeps the design rationale and fixes the attribution. From: Track 1 Q1, items Q9, conversion Q8.

**OQ-2 Form of adoption.**
- (a) Patterns only, re-implemented as deterministic checks in `rsi-loop.js`.
- (b) Run harness2 itself as a dev-only tool in an isolated sandbox with an egress firewall.
- (c) Reject harness2 entirely.
- Recommendation: (a). (b) needs Python 3.12, Vertex credentials and permission-bypass flags; (c) loses the budget identity and leak-tripwire ideas. From: Track 1 Q2.

**OQ-3 Held-out check for Track 1, and the scope of sealed set S5.** The repo says both that S5 is for the Track-2 advice judge (`docs/research/2026-10-17-rsi-opt-in-data/00-README.md:54`) and that the Track-1 replay gate uses it (`docs/capstone-report/rsi-in-development-and-application.md:48`; `00-README.md:77`). RSI-4 (owner-decisions :203) is silent.
- (a) Time split: replay cases mined after a candidate's window re-check it on a later run; S5 stays with the advice judge.
- (b) S5 (or a separate owner-held negative command corpus outside every worktree) also gates Track 1.
- (c) No held-out check beyond the human merge.
- Recommendation: (a) now, with an owner-held negative command corpus as an optional later step. The owner's intent for S5 decides whether (b) is required. From: Track 1 Q3 (reframed by review).

**OQ-4 CI coverage of the replay set.** `ci.yml` does not run the mod's replay test, although the RSI PR body says CI is half the gate.
- (a) Add a CI job that runs `.claude/mods/asclexis-rsi/rsi.test.ts` on every PR, through an owner-gated build-item PR.
- (b) Keep workflow-only replay and reword the PR body so it no longer claims CI coverage.
- Recommendation: (a). From: Track 1 Q4.

**OQ-5 Pruning.**
- (a) Keep additions-only; removing a rule or case takes a separate human-authored PR.
- (b) Add a pruner phase that proposes deletions for the owner to merge.
- Recommendation: (a). A deletion weakens a guard (CLAUDE.md §3), and there are 5 rules. From: Track 1 Q5.

**OQ-6 Critic.**
- (a) Deterministic checks: evidence threshold by distinct sessions, run-specific-literal rejection, over-broad-match corpus check, message cap; budget stays at 9.
- (b) An LLM critic agent; budget documented at 10.
- Recommendation: (a). Auditable and within the documented budget. From: Track 1 Q6 (over-broad check added by review).

**OQ-7 `docs/agentic/recurring-failures.md` in the RSI write scope.** It is in ALLOW without a deletion guard, and every implementer and reviewer reads it.
- (a) Extend additions-only to it (deletions = 0) with a cap on added lines and the imperative-text check.
- (b) Move it out of ALLOW; changes go through build-item.
- (c) Leave as is.
- Recommendation: (a). It keeps the loop able to record new failure modes, which CLAUDE.md §4 asks for, without letting it remove one. From: Track 1 review.

**OQ-8 Stale Track-1 status in the capstone RSI section.** `rsi-in-development-and-application.md:17` and `:27` say Track 1 is not merged; its own §6 says it is.
- (a) Correct §2 in a separate small docs PR.
- (b) Leave it until the next scheduled refresh of that section.
- Recommendation: (a). The report must not contradict itself. This package does not edit that file. From: all five verdicts.

## B. Track 2: what the in-app agent may do

**OQ-9 The existing read-only agent (T0).** It is on by default, has no UI switch, and one of its 8 tools (`query_care_tasks`) returns unverified extracted text.
- (a) Keep T0 on by default; add a Settings toggle for `agent_enabled`; label care-task text as unverified in answers.
- (b) Keep T0 exactly as it is.
- (c) Put T0 behind a first-run consent, or turn it off by default.
- Recommendation: (a). (c) is a regression with no clear safety gain; (b) leaves no opt-out and unlabelled unverified text. From: Track 1 Q7, items Q1, analytics Q6.

**OQ-10 Consent model for new capabilities** (full-document read, readable view, analytics).
- (a) Per-action ask only.
- (b) Standing per-purpose consent only.
- (c) Per-action ask by default, which the patient can upgrade to standing consent per purpose; critical gates always ask.
- Recommendation: (c) as the target, delivered per-action first because standing consent needs storage (OQ-11). From: trace AGENT-CAP-CONSENT, conversion Q2, analytics Q5.

**OQ-11 Where capability consent is stored.**
- (a) A new profile table `agent_capability_consents` on PR #211's `DonationConsent` pattern, after #211 merges.
- (b) New purpose values in #211's `donation_consents`.
- (c) Boolean flags in model settings.
- Recommendation: (a). Donation and feature permission mean different things on revoke; (c) has no history or versioning. From: items Q2, conversion Q2, analytics Q3.

**OQ-12 Where the expanded-mode trace lives.**
- (a) Only in the chat response, never stored.
- (b) Stored per profile in a new table, kept N days, deleted with the profile and source session, with a read route.
- (c) Both, with (b) only while the `agent_traces` donation consent is on.
- Recommendation: (a) now; revisit with OQ-24. From: conversion Q3, trace DEV-TRACE-SCOPE.

**OQ-13 What the trace shows.** RunStep payloads hold raw values and chunk text.
- (a) A handle-only projection always (tool names, ids, counts, gate decisions).
- (b) Full tool outputs on the patient's own screen, never stored.
- (c) Handle-only by default, with a separate "show values" toggle and an on-screen warning.
- Recommendation: (c). It meets the intent that the patient can see everything while keeping the default free of raw PHI on screen, and it carries the review's handle-only test. From: items Q3, analytics Q4, conversion review.

**OQ-14 The RunStep payload contract** (`state.py:64` says handles; `act.py:56` stores outputs).
- (a) Correct the comment; add a test that RunLog never reaches audit, cache, persistence or donation.
- (b) Make payloads handle-only and re-read rows for display (requires redesigning draft and replay).
- (c) Leave as is.
- Recommendation: (a). From: items Q4, analytics Q8, trace DEV-TRACE-PAYLOAD.

**OQ-15 Who can turn on expanded mode.**
- (a) A per-profile setting, off by default, with a profile migration and an audit row on toggle.
- (b) Only in a development build.
- (c) Both.
- Recommendation: (a). The intent is that the patient sees the trace. From: Track 1 Q8, items Q6, conversion Q4.

**OQ-16 How interactive expanded mode is.**
- (a) View-only, after each run.
- (b) An optional pause before each act step.
- (c) A pause before every act step, always.
- Recommendation: (a) first, then (b). Critical gates stop in every mode anyway. From: items Q5, trace HITL-STEP.

**OQ-17 What "convert files into a readable format" produces.**
- (a) An on-screen deterministic re-render of verified data only; unverified values shown as status and counts with a Workbench link.
- (b) (a), plus a per-action "unverified transcription" of extracted page text, clearly labelled.
- (c) An LLM plain-language rewrite (needs OQ-18 and a content-level faithfulness check first).
- (d) A stored converted artifact (needs a write path and a migration).
- Recommendation: (a), with (b) as a per-action option; (c) and (d) deferred. From: items Q7, conversion Q1 and Q6, conversion review.

**OQ-18 `interpret_safety` on conversion and analytics output.** It is not on the agent path today.
- (a) Call `validate_interpretation` (called, not edited) on any conversion or analytics text, in addition to the agent classifier.
- (b) Agent classifier and template tests only.
- Recommendation: (a) for any LLM-written text; for fixed templates, the banned-words CI test is the primary control either way. From: conversion Q5, analytics review.

**OQ-19 External runner and the legacy fallback.** Any agent exception falls back to `rag.query`, which uses the external runner when the patient enabled it.
- (a) Conversion and analytics never go off-device: gated outcomes are terminals, and the fallback is disabled for gated intents.
- (b) Allowed under D12 strict redaction like other chat.
- Recommendation: (a). Both computations are local and deterministic. From: conversion Q7, analytics Q7, reviews.

**OQ-20 Agent cache and consent.**
- (a) Add a consent version (and dose data, for adherence) to the cache fingerprint, and clear the cache on any grant or revoke.
- (b) Never cache answers that used a gated capability.
- (c) Leave the cache unchanged.
- Recommendation: (a). From: items Q8, analytics review.

**OQ-21 Trend definition in chat.**
- (a) Adopt the Trends page's latest-vs-prior comparison with a 5% stable band.
- (b) Keep first-vs-last with strict equality.
- (c) Report both, labelled.
- Recommendation: (a). One definition across the app; it changes user-visible text and needs a test. From: analytics Q2.

**OQ-22 Wearables-to-lab correlation.**
- (a) Keep the current non-goal: no correlation of any kind.
- (b) Side-by-side series on separate axes, no statistic, no linking wording.
- (c) A computed association with a fixed caveat.
- Recommendation: (a) now; revisit (b) after wearables code exists. From: analytics Q1.

**OQ-23 Agent audit gaps.** A semantic-cache hit and a pre-model advice escalate write no audit row today.
- (a) Add handle-only audit rows on both paths (new action strings need an allowlist entry, which is an owner gate).
- (b) Accept and document.
- Recommendation: (a). The audit invariant covers every route that touches profile data. From: trace review.

## C. Track 2: traces, donation and RSI

**OQ-24 Trace donation: source and retention.** A trace that is never stored cannot be collected when the patient rates the turn later; DON-SOURCE (:282) covers rated chat turns, not traces.
- (a) Collect no traces under `agent_traces` until a new owner row decides source and retention.
- (b) While `agent_traces` consent is on, persist a handle-only trace projection for every run; collect only rated ones; purge unrated after N days.
- (c) As (b), but persist raw traces.
- Recommendation: (a). From: trace TRACE-DONATE-SOURCE, items review, trace review.

**OQ-25 Agent and analytics answers in donation.** Every answer is stored as a `ChatTurn`, and a rated turn is donatable under DON-SOURCE.
- (a) Accept as already decided, under strict redaction plus the Safe Harbor detector, and make sure the DON-COPY wording says agent answers are included.
- (b) Exclude analytics-derived turns from donation.
- Recommendation: (a), with the wording check under DON-COPY-R1. From: analytics review.

**OQ-26 Canary handling for `agent_traces`.** DON-CANARY is "drop and continue".
- (a) For `agent_traces` only, a leaked canary blocks that purpose's dataset until the owner looks.
- (b) Drop and continue, as for the other purposes.
- Recommendation: (a). Traces carry structured values and dates, so a leak more likely points to a systematic fault. From: trace TRACE-CANARY.

**OQ-27 What a Track-2 RSI loop may change.** `rsi-loop.js` ALLOW does not cover `nodes/plan.py`, so Track 2 needs its own allow list and gate.
- (a) Planner rules and golden replay cases only, under a new Track-2 allow list, owner-merged.
- (b) Also draft templates.
- (c) Nothing yet: mine and report only.
- Recommendation: (c) until the showcase freeze (2026-10-24), then (a). From: trace RSI-T2-TRACE-PROMOTE, trace review.
