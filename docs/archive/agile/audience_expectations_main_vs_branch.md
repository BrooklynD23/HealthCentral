# Audience Expectations — `origin/main` vs `fix/agent-overhaul` (target)

> Historical Reference: this is a point-in-time snapshot retained for history and is not an active tracker. For active remaining work, use [`docs/features/TASK_LIST.md`](../../features/TASK_LIST.md).

> **Read this first.** The left column is what HealthCentral does **today** on
> `origin/main`. The right column is the **target finished state** of the
> `fix/agent-overhaul` branch as defined by the Agile plan — it is a commitment to
> build toward, not a description of shipped code. Where a target is unproven until
> its eval/CI gate is green, it is marked *(gated)*.
>
> **One thing that does NOT change in either column:** HealthCentral never gives
> medical advice, diagnosis, or treatment recommendations. It explains *your own
> verified data* in plain language and points you back to your clinician. The
> overhaul makes that boundary stronger, never weaker.

This document is a *list of reports*, each a different lens for a different reader.
Skim the matrix in Report 0, then read whichever lens matters to you.

---

## Report 0 — Executive comparison matrix

| Dimension | `origin/main` today | `fix/agent-overhaul` target |
|---|---|---|
| Assistant model | Single-shot: retrieve → answer once | Plan→act→reflect loop, up to 5 read-only lookups |
| Can it combine multiple values/trends? | Limited to one retrieval pass | Yes — chains observations, trends, references |
| Safety mechanism | Mostly prompt + verification-status display | Mechanical guard node: advice gate ×2, unmapped-claim drop, abstain/escalate |
| "I don't know" behavior | Best-effort answer | First-class **abstain** / **escalate** *(gated)* |
| Proof it behaves | Limited behavioral tests | Golden eval suite, 4 axes, CI gate *(gated)* |
| Privacy posture | Local-first, SQLCipher vaults | Same + explicit PHI redaction gate + offline-verified loop |
| Speed | Fast (one call) | Slower per question, capped + cached; target ≤ +50% p95 |
| Auditability | Security/audit logging present | Every agent decision emits a structured event |
| Rollback safety | n/a | Behind a flag; legacy path kept one release |

**Audience takeaway:** today you get a careful one-shot explainer; the target is a
careful *reasoner* that can follow a question across your record and that proves its
own safety before shipping.

---

## Report 1 — End-user experience (for the person using the app)

**Today.** You ask the assistant about a value in your record. It retrieves the most
relevant context and gives you one grounded explanation with citations and a
verification badge. If the question needs two or three things stitched together, you
ask follow-ups yourself.

**Target.** You ask the same question. The assistant can now look up the value,
pull its trend over time, fetch the reference range, and check whether the value is
verified — then either give you one combined, cited explanation *or* clearly tell
you it can't (and why). You feel less like you're driving a search box and more like
you're asking a careful study partner who refuses to guess.

**What to expect:** richer, multi-fact answers and honest "not enough info" replies.
**What NOT to expect:** advice, urgency calls, or anything your doctor should say.

---

## Report 2 — Trust & safety (for a cautious user or a clinician reviewer)

**Today.** Safety leans on how the model is prompted plus the verification status
shown alongside answers. It works, but the guarantee lives mostly in instructions.

**Target.** Safety becomes structural. A dedicated guard step runs an advice check
*twice* (on your question and on the draft), drops any sentence that doesn't map to
a real source before you ever see it, and abstains rather than hedging when
confidence is low. Diagnosis/treatment bait returns a fixed "ask your doctor"
response the model is not allowed to rewrite. Every one of these decisions is logged.

**What to expect:** fewer confident-sounding-but-unsupported statements; clearer
hand-offs to your clinician.
**What NOT to expect:** a system that will ever tell you what to do about a result.

---

## Report 3 — Capability & feature comparison (for a contributor or PM)

**Gained in the target:** multi-step tool-using loop; typed read-only tool registry;
step budget + replayable run logs; mechanical groundedness mapping; first-class
abstain/escalate; PHI redaction gate on any opt-in external path; semantic answer
cache; per-node latency/token metrics; golden eval suite gating CI; optional local
LoRA adapter.

**Unchanged / preserved:** local-first SQLCipher per-profile vaults; human
verification flow as the *only* writer of clinical data; citations; memory;
middleware stack; opt-in-only external LLMs.

**Explicitly out of scope:** the agent never writes clinical data, never books
appointments, never acts on your behalf. It reads and explains.

**Audience takeaway:** the surface area you trust (local, encrypted, human-verified)
is preserved; what's added is reasoning + provable guardrails on top of it.

---

## Report 4 — Privacy & data handling (for a privacy-conscious user)

**Today.** PHI lives only in per-profile encrypted vaults; the master DB holds no
clinical data; external models are opt-in.

**Target.** Same foundation, plus: any external-LLM tool path the agent uses
inherits the existing redaction gate, and there is a network-disabled integration
test asserting the full assistant loop completes locally on your device.

**What to expect:** the new "smarter" assistant still runs entirely offline by
default; nothing about your record leaves the device unless you opt in *and* it
passes redaction.
**What NOT to expect:** any silent cloud dependency introduced by the overhaul.

---

## Report 5 — Reliability & performance (for a power user)

**Today.** One model call per question — fast, but shallow on multi-part questions.

**Target.** Several reasoning steps per question, so an individual answer can take
longer. This is bounded three ways: a hard 5-step budget, a semantic cache that
serves repeated questions instantly (and invalidates when new verified data lands),
and per-node timing surfaced in the dashboard. The performance commitment is p95
latency no worse than the current path + 50%.

**What to expect:** noticeably better answers on complex questions, comparable speed
on repeats, a small latency cost on novel multi-part ones.
**What NOT to expect:** unbounded "thinking" — if it can't ground an answer within
budget, it abstains.

---

## Report 6 — Quality assurance / "how do we know it works" (for a skeptic)

**Today.** The assistant's *behavior* (does it stay grounded? does it refuse
advice?) is not systematically measured before release.

**Target.** A golden set of 50–100 cases — including abstention and advice-bait
categories — scores four axes automatically: groundedness, citation accuracy,
abstention correctness, and advice leakage (zero tolerance). A CI job fails any pull
request where advice leaks or groundedness drops below 100%.

**What to expect:** safety claims backed by a suite you can inspect and that blocks
regressions.
**What NOT to expect:** perfection — evals catch known failure shapes, so the suite
grows every time a real miss is found.

---

## Report 7 — Limitations & "what NOT to expect" (everyone, read this)

Both today and at target, HealthCentral:
- is **not a doctor** and gives **no diagnosis, advice, or treatment guidance**;
- explains **only your own data**, and leans on whether that data is **verified**;
- is **read-only** over your clinical record — it never edits or acts;
- depends on the quality of what's in your vault — garbage in, abstention out.

And specific to this comparison: the right-hand column is a **plan**, not a shipped
product. Each *(gated)* capability is real only once its eval/CI gate is green on the
branch. Until then, treat the target column as the bar you're building to.

---

### How to use these reports

- **Release notes / changelog:** lift Reports 1, 3, 5.
- **User-facing trust page:** lift Reports 2, 4, 7.
- **Stakeholder / contributor brief:** lift Reports 0, 3, 6.
- **Acceptance gate:** Report 0's matrix doubles as a release checklist — a row is
  "true" only when its backing story in `AGILE_PLAN.md` is accepted.
