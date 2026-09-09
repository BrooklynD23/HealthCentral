# Industry-shift prompt — what to integrate next

A research brief for **Claude Fable 5.1** (`claude-fable-5-1`) exploring what
agentic engineering has changed since the CS4610 reports were written, and what
this project should adopt. **4,227 characters** — everything between the fences
is the prompt.

Distinct from [`GOAL-PROMPT.md`](GOAL-PROMPT.md): that one *audits* the existing
plan, this one *explores forward*. Run the audit first if you are doing both —
its verdict may change what is worth integrating.

## Settings

Effort `high`. Omit the `thinking` parameter entirely — any explicit
configuration returns a 400 on this model. Forced `tool_choice` (`any`/`tool`)
also 400s; use `auto` plus an instruction if you need a specific tool.

The prompt is goal-shaped rather than step-shaped on purpose. Anthropic's
guidance is that prompts written for earlier models are often too prescriptive
for Fable 5.1 and *reduce* output quality, so it states the question, the
scoring criteria and the constraints, then gets out of the way. It also grants
sub-agent delegation explicitly, since this model sustains asynchronous
sub-agents well and research fans out naturally.

**No real patient data in the context.** Fable 5.1 requires 30-day retention and
is not available under zero-data-retention unless Anthropic authorizes it, so
ZDR is not a control to lean on — the control is not sending it. Source code,
docs and synthetic fixtures are fine; a vault, a backup, a real lab PDF or a
`.env` are not. See [`FRONTIER-AUDIT-PROMPT.md`](FRONTIER-AUDIT-PROMPT.md) §1.

## Why the claim-vs-evidence paragraph is in the prompt

It is the load-bearing part. Tracks 9 and 10 established that the reports
describe harness features the repo does not have — and in the PHI-hook case,
name a mechanism that could not have done the job. A forward-looking proposal
written without that context will cheerfully add a second layer of described-
but-unbuilt capability on top of the first. The third scoring criterion — *can
this repo evidence it* — exists for the same reason.

## The prompt

```text
Research what has changed in agentic engineering since May 2026, and propose what Asclexis should integrate.

This repo is not only a health app. Its stated purpose is to explore how software engineering shifted from manual coding to agentic workflows, using Asclexis as the artifact that shows the journey. Two CS4610 reports in CS4610_Report_Demo/ documented that shift through April 2026 — vibe coding, meta-prompting, context engineering, harness engineering, autonomous loops, cross-vendor adversarial review. Read both. They are the project's own account of its thesis, and your work continues them.

It is now September 2026. Four months is a long time in this field.

Read first:
- CS4610_Report_Demo/*.pdf — both reports
- docs/research/2026-09-08/STATUS.md — what shipped, what was rejected
- .../10-demonstration-artifact.md and .../11-harness-engineering.md — the two tracks covering this territory
- .../09-roadmap.md — what is already planned
- CLAUDE.md, AGENT.md, docs/agentic/{roadmap,harness,evals,mcp-tools}.md

Understand one thing before proposing anything. Those two tracks found the reports describe harness features this repo does not have: a PreToolUse hook blocking PHI-bearing tool calls (no hooks and no settings.json exist anywhere), subagent definitions in .claude/agents/ (the directory does not exist), and a Ralph-style sweep that tuned RAG reranking (`grep -i rerank modules/rag.py` is empty — the swept feature does not exist). Track 10 went further: the hook claim named the wrong mechanism entirely. Claude Code hooks fire on the *coding agent's* tool calls and are documented upstream as "a convenience feature for automation, not a security boundary" — they could never have enforced the product's runtime network guarantee. That guarantee does exist, correctly, as code.

So this project has written narrative ahead of evidence once already. Your proposals must not do it again. Anything you recommend has to be something the repo can demonstrate, not merely describe.

Your question: what has emerged in agentic engineering since May 2026 that this project should adopt, and what should it deliberately not? Research the current state — Claude Code primitives and what changed, the three frameworks the reports studied (superpowers, GSD v2, everything-claude-code) and how they evolved, the Agent SDK, MCP's trajectory, and whatever is newer that the reports could not have known. Your training cutoff predates this window, so verify against primary sources and tag anything you cannot source [UNVERIFIED]. A short verified list beats a long speculative one.

Score every candidate on three things: does it move the product, does it move the harness, and can this repo evidence it. Something that scores on the first two and fails the third is a liability here — say so plainly rather than ranking it highly and hoping.

Binding constraints: local-first, no network calls in product paths; the agent is read-only over clinical data; no medical advice; per-profile SQLCipher isolation; redaction before anything leaves. One person maintains this — a proposal nobody can sustain is worse than none. The repo already ships 36 skills, and more is not automatically better; Track 10 recommends against three of four candidate subagents on exactly that basis.

Deliver docs/research/2026-09-08/12-industry-shift.md: what changed since May 2026 with sources; a ranked adoption list scored on the three criteria; an explicit do-not-adopt list with reasons; and a section on reconciling the reports with the repo, because a forward proposal that leaves the existing claim-vs-evidence gaps unaddressed inherits them.

How to work: delegate independent research to sub-agents and keep working while they run. Read the code, not just the docs — every repo claim carries a file:line. Before reporting a finding, audit it against a tool result from this session; if something is unverified, say so rather than asserting it. Keep working notes in docs/research/2026-09-08/industry-notes.md.

Do not edit source. This is research; the document is the deliverable.

Lead your final message with what you found, in plain sentences written for someone who watched none of your work.
```

## What to reject in the reply

- A long list of confidently-named tools and releases with no URLs. The window
  in question is entirely after the model's training cutoff; unsourced specifics
  are the expected failure mode, not an edge case.
- Anything scoring well on product and harness impact while failing the
  evidence criterion, ranked highly anyway.
- A proposal to add skills, subagents or hooks without saying what each one
  *enforces* that prose does not already.
