# `/goal` prompt — frontier architecture audit

A single-turn brief for a higher-reasoning model to audit the whole research
corpus and produce the architecture plan. **3,475 characters** — everything
between the fences is the prompt; nothing outside them is.

## Why one dense turn rather than a conversation

Both target models reward a complete task spec in the first turn. Anthropic's
guidance for Claude Fable 5.1 is that ambiguous prompts delivered progressively
across several turns *reduce* token efficiency and sometimes performance, and
that prompts written for earlier models are often too prescriptive and lower
output quality — so this states the goal, the constraints, and what "finished"
means, and then gets out of the way. It deliberately contains no numbered
methodology.

## Settings

- **Claude Fable 5.1** (`claude-fable-5-1`): effort `high`, not `xhigh`. The
  deliverable is long prose, and at `xhigh`/`max` the model tends to draft a long
  deliverable inside its thinking and write it again as the reply — roughly
  double the output tokens for no quality gain. Omit the `thinking` parameter
  entirely; any explicit configuration returns a 400.
- **GPT-6 Astra** (`gpt-6-astra`): `reasoning_effort: high`. Astra asks
  clarifying questions more readily and under-delegates, so if you want it to
  fan out across tracks, add one line telling it to run them as parallel
  sub-agents. See [`FRONTIER-AUDIT-PROMPT.md`](FRONTIER-AUDIT-PROMPT.md) §5.
- **No real patient data in the context, on either model.** Fable 5.1 requires
  30-day retention and is not available under zero-data-retention unless
  Anthropic authorizes it, so ZDR is not a control you can lean on here — the
  control is not sending it. See [`FRONTIER-AUDIT-PROMPT.md`](FRONTIER-AUDIT-PROMPT.md) §1.

## The prompt

```text
Audit Asclexis and produce the architecture plan for its next two quarters.

Asclexis is a local-first health app: patients import lab PDFs, verify extracted values, see trends, and ask questions answered from their own records with per-sentence citations. It runs entirely on the patient's machine. Educational, never diagnostic.

Read in this order first:
1. docs/research/2026-09-08/STATUS.md — what shipped and what was REJECTED since the research was written. Without it you will re-propose finished work and implement a rejected, harmful change.
2. CLAUDE.md, AGENT.md — invariants and definition of done.
3. docs/research/2026-09-08/00-brief.md, then 09-roadmap.md.
4. Tracks 01-11, on demand.
5. docs/agentic/recurring-failures.md — eight failure modes this repo has actually produced.

Five facts that change the audit:
- The agent graph is entirely LLM-free. `plan` is keyword matching, `draft` emits f-string templates, `guard` emits fixed strings; `grep ModelRunner modules/agent/` returns only docstrings. /assistant/chat serves deterministic templated prose today.
- So every inference concern — routing, KV cache, structured output, MoE — describes a model call that does not exist yet: designs for the first generative node, not optimizations.
- The deterministic planner is a permanent fallback, not scaffolding to delete when an LLM planner ships.
- The low tier cannot plan: 0.5B-class models score ~1.4% on multi-turn tool calling.
- Baseline is 1269 collected backend tests. test_api_rag_index_002b fails without an embedding model; its 0.7 threshold is not to be touched.

Invariants — a recommendation that breaks one is unusable however good it is: local-first, no network calls in product paths; the agent is read-only over clinical data; no medical advice; every answer sentence maps to a source; abstention is a success; per-profile SQLCipher isolation; redaction before anything leaves. Ask before touching interpret_safety.py, redaction.py, faithfulness.py, verifier_agent.py, or anything auth/encryption. It ships on a patient's laptop: 8-16GB RAM, often no GPU, Windows-native.

Deliver three documents:
1. An architecture assessment — the real structural weaknesses, independent of the drafted roadmap. Every claim carries a file:line.
2. A verdict on 09-roadmap.md — per item across Waves 0-4: keep, reorder, cut, or missing, with one reason each.
3. A revised epic list with dependencies, only if you disagree materially. "Your sequence is right" is an acceptable outcome; don't pad it into a document.

How to work: read the code, not just the research. Where you reason from something you cannot verify in source, say so rather than asserting it. Audit each claim against a tool result before reporting it.

Disagreement is the point — I can generate agreement myself. If the central bet is wrong — constrained decoding first, then a tier-gated LLM planner, with the deterministic planner kept underneath — say so now rather than after a quarter of work. Tell me what a strong engineer would say in review that eight parallel research agents were too close to the material to see.

Do not propose a rewrite. This is a working system with 1269 passing tests and real safety properties; the plausible failure mode of this audit is a beautiful architecture nobody can migrate to. Anchor every recommendation to something that exists.

The deliverable is your assessment. Report findings and stop — do not edit source.
```

## What to reject in the reply

The full list is in [`FRONTIER-AUDIT-PROMPT.md`](FRONTIER-AUDIT-PROMPT.md) §7.
The one that matters most: **agreement without engagement.** If it endorses
every wave and finds nothing missing, it did not read the code — re-run it
rather than accepting the validation.
