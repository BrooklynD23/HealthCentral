# Consultation prompt — what to actually integrate

For **Claude Fable 5.1** (`claude-fable-5-1`). **4,390 characters** — everything
between the fences is the prompt.

## What this is for, and how it differs from the other two

The ten Sonnet tracks produced roughly **128 candidate changes** across their
recommendation tables. They are research output: leads, not decisions. No track
carries authority, none could see the other nine, and several candidates are
already stale or were rejected after implementation.

| Prompt | Question it answers |
|---|---|
| [`GOAL-PROMPT.md`](GOAL-PROMPT.md) | Is the roadmap in `09-roadmap.md` right? |
| **This one** | Which of the 128 candidates should we actually do? |
| [`INDUSTRY-PROMPT.md`](INDUSTRY-PROMPT.md) | What has changed outside the repo since May 2026? |

The first two overlap — both audit the same corpus. If you only run one, run
this one: it subsumes the roadmap verdict (it asks explicitly where
`09-roadmap.md` has it wrong) and adds the cross-track reconciliation the audit
prompt does not request.

## Why a frontier model, specifically

Not for raw capability. For **context width**. Ten tracks at ~6,000 lines plus
the code fits inside a 1M-token window, and no individual Sonnet researcher
could hold more than its own track. Every conflict, duplicate and hidden
dependency between tracks is invisible from inside any one of them — that is
the work this prompt asks for, and it is the one thing a wide-context reader
can do that parallel narrow ones structurally cannot.

## Settings

Effort `high`. Omit the `thinking` parameter entirely — any explicit
configuration returns a 400 on this model. Forced `tool_choice` (`any`/`tool`)
also 400s. Sub-agent delegation is granted in the prompt because the reading
fans out cleanly and this model sustains asynchronous sub-agents well.

**No real patient data in the context.** Fable 5.1 requires 30-day retention and
is unavailable under zero-data-retention unless Anthropic authorizes it, so ZDR
is not a control to lean on. Source, docs and synthetic fixtures are fine; a
vault, a backup, a real lab PDF or a `.env` are not.

## The prompt

```text
Consult on what Asclexis should actually integrate.

Ten research tracks ran in parallel, in isolated contexts, and produced roughly 128 candidate changes across their recommendation tables. They are in docs/research/2026-09-08/ (files 01-08 and 10-11; 09 is my own synthesis). Every one is research output — a lead, not a decision. Nothing in that directory carries authority, and several candidates are already stale or were rejected after implementation.

You can do something none of those agents could: hold all ten at once. They could not see each other. That is where the value is.

Read first:
- STATUS.md — what shipped, what was rejected and why, what is still open. Read it before any track; without it you will recommend finished work, and one change that was rejected as actively harmful.
- 00-brief.md, then 09-roadmap.md — the existing sequencing.
- All ten tracks.
- CLAUDE.md, AGENT.md, docs/agentic/recurring-failures.md.

Asclexis is a local-first health app: patients import lab PDFs, verify the extractions, see trends, and ask questions answered from their own records with per-sentence citations. It runs on-device. Educational, never diagnostic. One person maintains it.

I want a consultation, not a summary. Work the candidates and tell me which to integrate, in what order, and which to drop.

Find what the isolated tracks could not. Candidates that conflict. Candidates that are cheap only if another lands first. Candidates individually sensible and collectively unaffordable. Places where two tracks propose the same thing in different words — and places where they propose opposite things. Tracks 2 and 3 already disagree on constrained-decoding cost by roughly an order of magnitude, and neither measured it on this codebase.

Reject freely. A consultation that keeps 128 items is not a consultation. I would rather have twenty things I will actually do than a ranked list of everything possible. Say what you are dropping and why; "individually reasonable, but it competes with X for the same month" is a legitimate reason.

Judge each survivor on four things: what it changes for a patient, what it costs to build and to keep, what breaks if it is wrong, and whether this repo can evidence it working. That last one matters more here than usual — the project has already written narrative ahead of its evidence once (see the claim-vs-evidence table in STATUS.md), and a recommendation that cannot be demonstrated repeats the mistake.

Binding constraints: local-first, no network calls in product paths; the agent is read-only over clinical data; no medical advice, every answer sentence maps to a source, abstention is a first-class success; per-profile SQLCipher isolation; redaction before anything leaves. Ask before touching interpret_safety.py, redaction.py, faithfulness.py, verifier_agent.py, or anything auth/encryption. It ships on a patient's laptop: 8-16GB RAM, often no GPU, Windows-native. Baseline is 1269 collected backend tests; test_api_rag_index_002b fails without an embedding model and its 0.7 threshold is not to be touched.

One fact reframes most of the technical candidates: the agent graph is entirely LLM-free today. `plan` is keyword matching, `draft` emits f-string templates, `guard` emits fixed strings, and `grep ModelRunner modules/agent/` returns only docstrings. So routing, KV cache, structured outputs and MoE all describe a model call that does not exist yet — designs for a first generative node, not optimizations of an existing one.

Deliver docs/research/2026-09-08/13-consultation.md: the integrations you recommend and why; what you are dropping and why; the cross-track conflicts and dependencies you found; and anywhere the roadmap in 09-roadmap.md has it wrong. Disagreeing with that roadmap is welcome — I wrote it from the same tracks, and I would rather know now than after a quarter.

How to work: read the code, not just the research — every repo claim carries a file:line. Delegate independent reading to sub-agents and keep working while they run. Before reporting anything, audit it against a tool result from this session; if it is unverified, say so rather than asserting it.

Do not edit source. The document is the deliverable.

Lead your final message with your actual recommendation — what you would do first — in plain sentences, for someone who watched none of your work.
```

## What to reject in the reply

- **A ranked list of all 128.** That is a summary wearing a consultation's
  clothes. The instruction to reject freely is the point of the exercise.
- Endorsement of `09-roadmap.md` with nothing added. It was written from the
  same tracks; agreeing with it costs nothing and proves nothing.
- Any recommendation that fails the fourth criterion — *can this repo evidence
  it* — but is ranked highly anyway.
- Cross-track conflicts reported as "these differ" without a call on which is
  right, or an explicit "this needs measurement here before either is trusted."
