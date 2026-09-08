# Frontier-model architecture audit — prompt pack

A ready-to-run brief for handing Asclexis to a frontier model (**Claude Fable
5.1** or **GPT-6 Astra**) for an independent architecture audit and roadmap.

Structure: §1 the data boundary (read first — it is the one hard rule), §2 the
context pack, §3 the portable core prompt, §4-5 per-model adapters, §6 the
output contract, §7 what to reject in the reply.

---

## 1. Data boundary — read before anything else

**No real patient data may enter a frontier-model context. Ever.** This is not
a style preference; it is the product's founding invariant applied to its own
development.

Concretely, before any paste or upload:

- **Never** attach a real `vault.db`, a real lab PDF, a backup archive, or the
  contents of `vaults/`, `backups/`, or any `.env`.
- **Never** paste audit rows, observation rows, or chat turns from a live
  profile — even your own. "It's my own data" is exactly the reasoning the
  product exists to make unnecessary.
- Synthetic fixtures under `src/backend/tests/` and Synthea-derived data are
  fine. Source code, docs, and schemas are fine.
- If you need to show a data shape, show the **SQLAlchemy model**, not a row.

One provider-specific note that reinforces the rule: **Claude Fable 5.1
requires 30-day data retention and is not available under zero-data-retention
unless expressly authorized by Anthropic.** ZDR is therefore not a control you
can lean on here. The control is not sending it.

---

## 2. Context pack

Give the model these, in this order. The ordering is deliberate — rules before
facts, facts before findings, findings before the ask.

| # | Path | Why it must be in context |
|---|---|---|
| 1 | `CLAUDE.md` | The hard invariants. An audit that violates these produces unusable output |
| 2 | `AGENT.md` | Stack, layout, commands, definition of done |
| 3 | `docs/research/2026-09-08/00-brief.md` | Verified repo state and the seven gaps — **including the two corrections** |
| 4 | `docs/research/2026-09-08/09-roadmap.md` | The current synthesis it is auditing |
| 5 | `docs/research/2026-09-08/01-codebase-audit.md` | Ground truth on what the code actually does |
| 6 | Tracks 02-08 | Load on demand; do not front-load all six unless the model has room |
| 7 | `docs/agentic/recurring-failures.md` | Eight failure modes this repo has actually produced |
| 8 | `feature_list.json`, `docs/agile/AGILE_PLAN.md` | Existing planning machinery the output must feed, not replace |

Both models hold ~1M tokens of context, and the whole research directory is
~6,800 lines, so items 1-5 plus the codebase fit comfortably. Prefer giving
**more source and fewer summaries** — these models reason better from primary
material than from someone else's compression of it.

### The five facts that change the audit

State these explicitly. A model that does not know them will produce a
confident, wrong plan — as this project's own first pass nearly did.

1. **The agent graph is entirely LLM-free.** `plan` is keyword matching,
   `reflect` is a dict-key check, `draft` composes f-string templates
   (`nodes/draft.py:80,108,116`), `guard` emits fixed strings.
   `grep -rn "ModelRunner" modules/agent/` returns only docstrings. The default
   `/assistant/chat` path never calls a model.
2. **Therefore every inference concern is prospective.** Routing, KV cache,
   structured outputs, MoE — all describe a model call that does not exist yet.
   These are designs for the *first* generative node, not optimizations.
3. **The deterministic path is the fallback, permanently.** It is not a
   stepping stone. `plan()` takes an injectable `planner`, and the swap is only
   safe because the keyword planner stays underneath it.
4. **`low` tier can never plan.** Qwen3-0.6B-class models score ~1.4% on
   BFCL-style multi-turn tool calling.
5. **Baseline is 1245 collected backend tests**, reproduced live on 2026-09-08.
   `test_api_rag_index_002b` fails without a real embedding model; that is
   environmental and must never be "fixed" by lowering its 0.7 threshold.

---

## 3. The portable core prompt

Model-agnostic. Copy this, then prepend the matching adapter from §4 or §5.

```text
You are auditing Asclexis, a local-first health application: patients import
lab PDFs, verify the extracted values, see longitudinal trends, and ask
questions answered from their own records with per-sentence citations. It runs
entirely on the patient's machine. It is educational software, never
diagnostic.

I am deciding what to build over the next two quarters, and I need an
independent read before I commit. Eight parallel research agents produced the
documents in docs/research/2026-09-08/. They were thorough, and they were also
working from a premise I got wrong at the start, which they corrected. I want
to know what else is wrong.

## What I want from you

Three deliverables, in this order:

1. An architecture assessment: what this system's real structural weaknesses
   are, independent of the roadmap I've drafted.
2. A verdict on that roadmap (09-roadmap.md): what is correctly sequenced,
   what is misordered, what is missing, and what should be cut.
3. A revised roadmap if you disagree with mine — as epics with dependencies,
   not a task list.

## What makes this system unusual, and what constrains any answer

These are invariants, not preferences. A recommendation that breaks one is
unusable, however good it is otherwise:

- Local-first: no network calls in product code paths. There is no server, and
  adding one is not on the table.
- The agent is read-only over clinical data. Write capability is a separate
  epic, never a story.
- No medical advice. Every answer sentence maps to a retrieved source.
  Abstention is a first-class success, not a failure path.
- Per-profile SQLCipher isolation; redaction before anything leaves the process.
- It ships on a patient's laptop — often 8-16GB RAM, often no GPU, Windows
  native. Abstraction is paid for in watts.

The most important thing to understand before you start: the agent loop is
ReAct-shaped but calls no model at all today. Answers are assembled from
Python f-string templates. That is a deliberate safety posture with a zero
hallucination surface, and it is also a ceiling — a template cannot explain a
question nobody anticipated, which is the entire product premise. Adding the
first generative node is the central architectural decision in front of me,
and I want your judgment on whether my sequencing of it is right.

## How to work

Read the code, not just the research documents. Every claim you make about the
repo should carry a file:line I can check; where you are reasoning from
something you cannot verify in the source, say so rather than asserting it.

Disagreement is the point. I can generate agreement myself. If the roadmap's
central bet — constrained decoding, then a tier-gated LLM planner, with the
deterministic planner as permanent fallback — is wrong, I would much rather
hear it now than after a quarter of work. Tell me what a strong engineer would
say in review that the eight agents were too close to the material to see.

Do not propose a rewrite. This is a working system with 1245 passing tests and
real safety properties; the plausible failure mode of this audit is a
beautiful architecture nobody can migrate to. Anchor every recommendation to
something that exists.
```

---

## 4. Adapter — Claude Fable 5.1

`claude-fable-5-1` · 1M context · 128K max output · thinking always on
(omit the `thinking` parameter entirely — `{type:"disabled"}` and
`budget_tokens` both return 400) · forced `tool_choice` (`any`/`tool`)
returns 400 — use `auto` plus an instruction, or `strict: true`.

**Effort: `high`.** Not `xhigh`. This audit's deliverable is long prose, and at
`xhigh`/`max` Fable 5.1 tends to draft a long deliverable inside its thinking
and then write it again as the reply — roughly double the output tokens for no
quality gain. Move up only if you measure one.

**The single most important adaptation: do not over-specify.** Anthropic's own
guidance is that prompts written for earlier models are often too prescriptive
for Fable 5.1 and *reduce* output quality. The core prompt in §3 is
deliberately goal-shaped rather than step-shaped. Resist the urge to add a
numbered methodology.

Prepend:

```text
You are operating with substantial autonomy on a hard, open-ended problem. I
have given you the goal and the constraints rather than a procedure; choose
your own approach.

Before reporting any finding about this codebase, audit it against a tool
result from this session. Only report what you can point to evidence for; if
something is unverified, say so explicitly. Report faithfully — if you checked
something and it contradicts the research documents, that contradiction is the
most valuable thing you can give me.

When you have enough information to act, act. Don't re-derive facts already
established in the documents, and don't narrate options you won't pursue.
Where you're weighing a choice, give me a recommendation, not a survey.

Delegate independent subtasks to sub-agents and keep working while they run —
one per research track is a natural split, and separate fresh-context
verifiers outperform self-critique for checking claims. Intervene if one goes
off track.

Keep a scratch file at docs/research/2026-09-08/frontier-notes.md. Record what
you verified and what surprised you, one finding per entry with a one-line
summary. Update entries rather than duplicating them; delete what turns out
wrong. That file is for you, not for me.

The deliverable is your assessment. Report findings and stop — don't apply
fixes, don't open branches, don't edit source. If you think something should
change, tell me what and why.

Your final message is my first look at any of this. Lead with the outcome —
the first sentence should answer "what did you find." Write it as a
re-grounding for someone who watched none of your work: complete sentences,
no arrow chains, no shorthand you coined along the way, each file or identifier
introduced in plain language. Supporting detail after. If you must choose
between short and clear, choose clear.
```

For an unattended run, also append the anti-early-stopping clause: *"You are
operating autonomously; I am not watching and cannot answer mid-task. Before
ending your turn, check your last paragraph — if it is a plan, a question, or a
promise about work you haven't done, do that work now."*

---

## 5. Adapter — GPT-6 Astra

`gpt-6-astra` · ~1.05M context · 128K max output · `reasoning_effort` accepts
`low`/`medium`/`high`/`xhigh`/`max`.

> **Provenance caveat:** `developers.openai.com` is blocked by this
> environment's egress proxy, so these figures come from third-party
> aggregators (OpenRouter, LiteLLM, llm-stats) rather than OpenAI's own docs.
> Verify against the [official model page](https://developers.openai.com/api/docs/models/gpt-6-astra)
> before relying on the numbers. The behavioral guidance below is from OpenAI's
> published prompting guidance as reported by
> [The Decoder](https://the-decoder.com/openai-shares-prompting-tips-for-gpt-6-astra-including-a-blocklist-of-slop-words/).

**Effort: `high`.** Same reasoning as Fable.

**The adaptations that matter are the mirror image of Fable's.** Astra asks
clarifying questions more readily than its predecessor and can under-delegate,
so where Fable needs *less* prescription, Astra needs the assumption boundary
and the delegation degree stated explicitly. OpenAI's guidance also emphasizes
describing a **visible outcome** — the more concretely a prompt describes what
finished looks like, the more reliably Astra executes it.

Prepend:

```text
Treat this as a call to act, not an invitation to scope it with me first.

Where to assume and where to confirm: make your own call on anything about
research method, document structure, ordering, or which files to read — assume
and note the assumption. Come back to me only if you find something that
changes whether this audit is worth doing at all, or if a constraint in
CLAUDE.md appears to contradict another one.

Delegation: run the tracks as parallel sub-agents rather than sequentially —
roughly one per area (agent loop, inference, data/compliance, frontend,
interop), with a separate verifier pass over their claims. Fan out wide; this
is a read-heavy audit and serial reading is the slow path.

What finished looks like, concretely: three documents I can act on Monday —
(1) an architecture assessment where every structural claim carries a
file:line, (2) a per-item verdict on 09-roadmap.md's waves marked keep /
reorder / cut / missing with a reason each, (3) a revised epic list with
explicit dependencies. A finding I can't trace to a file, or a recommendation
without a stated cost, is not finished.

Writing style: concise paragraphs, plain language, active voice, main point
first. No bullet-point walls where prose carries the argument better. Don't
hedge findings you're confident in, and flag the ones you aren't.
```

OpenAI's Astra guidance includes a "slop words" blocklist — a set of filler
terms to prohibit explicitly. Its contents are not reproduced here because this
environment could not reach the primary source; pull it from the official guide
and append it if you want the prose tightened further.

---

## 6. Output contract

Ask for these three files. Naming them up front is what makes the run
resumable if it stops early.

| File | Contents |
|---|---|
| `docs/research/2026-09-08/frontier-assessment.md` | Architecture assessment. Every structural claim carries `file:line`. Explicit section on what it could **not** verify |
| `docs/research/2026-09-08/frontier-roadmap-review.md` | Per-item verdict on `09-roadmap.md`: keep / reorder / cut / missing, one reason each. Waves 0-4 individually |
| `docs/research/2026-09-08/frontier-roadmap.md` | Revised epics with dependencies — only if it disagrees materially. "Your sequence is right" is an acceptable outcome and should not be padded into a document |

---

## 7. What to reject in the reply

Apply the same verification bar to a frontier model that this project applied
to its own eight agents. A bigger model is not a source of truth; it is a
faster source of claims.

- **Any `file:line` that does not resolve.** Check a sample. One bad citation
  invalidates the surrounding claim, not just the citation.
- **A recommendation that breaks an invariant** — a network call in a product
  path, a write to clinical data, an LLM judging a safety axis. However elegant.
- **"Rewrite it in X."** Anchor or discard.
- **Agreement without engagement.** If it endorses all five waves and finds
  nothing missing, it did not read the code. Push back and re-run.
- **Confident claims about post-May-2026 releases.** Both models have training
  cutoffs; neither is exempt from the `[UNVERIFIED]` rule the eight tracks ran
  under.
- **A plan that ignores the fallback.** Any proposal that treats the
  deterministic planner as temporary scaffolding has missed the safety argument
  and should be sent back with §2's five facts restated.
