# RSI with opt-in user data: research package (2026-10-17)

**Last Updated:** 2026-10-17
**Owner:** repository owner
**Refresh Trigger:** any owner answer to RSI-1..RSI-4 below; the merge of #68 (RSI-loop research + session-log hook); any plan that collects user data for training.

> **Point-in-time research (2026-10-17).** Planning and documentation only. No product code changed. Four Haiku 5.5 research agents swept primary sources on 2026-10-17. Opus 5.5 (L0) synthesised the results here. Every source keeps its verification marker: **[V]** page fetched and confirmed, **[S]** search snippet only, **[U]** unverified. Re-check [S]/[U] items before citing them outside the repo.

## The owner's direction (2026-10-17, owner to L0 in chat)

> "RSI is a good focus to help include the senior project, we're trying to use the data that our model collect in the user's setting if they opt-in, that way the dataset is not only for fine-tuning smaller models, but can be used to expand as synthetic data for RSI + RSI-enabled harness engineering."

That gives three uses of one opt-in dataset:

1. **Fine-tune small local models** (the 4-12B models Asclexis runs through Ollama/llama.cpp).
2. **Seed synthetic data**, so the set can grow without collecting more real patient text.
3. **Drive an RSI-enabled harness**: the agent harness improves itself from logged runs, behind eval gates.

Related prior work in the repo: the RSI-loop applicability report and session-log hook in #68 (`docs/plans/2026-10-10-rsi-loop-applicability-report.md`, lands with #68).

## What the repo's invariants already decide

These are not open questions. They come from [CLAUDE.md](../../../CLAUDE.md) Hard invariants and §1.

| Invariant | Consequence for this design |
|---|---|
| Local-first, no network in product paths | Collection, redaction, training and synthesis run on the user's machine. Cloud "DP synthesis via API" (Aug-PE) is out unless only redacted, DP-protected aggregates leave the device, which would need a new owner decision (RSI-2). |
| Redaction before anything leaves (`modules/redaction.py`, `strict`) | Every exported training or synthetic record passes `strict` redaction. The patient's own CSV/JSON export (D3) is not a training export. |
| Per-profile isolation (`ProfileDbSession`) | The donated set is built per profile, from that profile's vault, only after that profile opts in. |
| Ask-first modules (`interpret_safety`, `redaction`, `faithfulness`, `verifier_agent`, auth/encryption) | An RSI loop may never self-modify them. Changes to them stay human-authored with an owner yes. |
| No medical advice; cited answers | Faithfulness and citation gates are the RSI loop's held-out evaluator. Weakening them to raise a score is forbidden (CLAUDE.md §3). |

## Recommended architecture

### A. Data donation pipeline (uses 1 and 2)

1. **Consent.** Opt-in per purpose (fine-tune / synthetic seeds / harness traces), revocable, and stated plainly in Settings. Revoking deletes the donated set. This follows the Apple Research app pattern (per-study choice, stop anytime) [02 #13] and a LINDDUN threat model for data donation [02 #12].
2. **Local redaction.** Run `strict` redaction, then a second PHI detector (Philter [02 #10] or Presidio [02 #15]) as a recall check. Safe Harbor's 18 identifiers are the floor [02 #14]. Measure recall on our own synthetic vaults, because small-LLM redactors over- and under-redact [02 #11]. Treat redaction as a leaky filter, not a guarantee.
3. **Privacy mechanism.**
   - Local fine-tune: DP-SGD [02 #5], or LoRA, which cuts memorization by up to about 10x [02 #9].
   - Synthetic seeds: local DP synthesis in the Private Evolution family [02 #6, #8], run against the local model.
4. **Leak eval before anything is used.** Plant canaries in the donated set and run extraction and membership probes on the tuned model [02 #3, #4]. Any recovered canary blocks the run. Clinical memorization is severe and survives further fine-tuning (up to 87%) [02 #3].
5. **Mix, never replace.** Keep a real-data anchor and add synthetic data on top. Replacing real data with synthetic data collapses the model [02 #1, #2] [01 #11].

### B. RSI-enabled harness loop (use 3)

The transferable pattern from DGM, ADAS, AIDE² and RRSI [01 #1, #5, #14, #15]: an **archive of harness variants, promoted only by held-out gates plus a human sign-off, with the evaluator outside the agent's write scope.**

| Step | Asclexis mapping | Sources |
|---|---|---|
| 1. Log | #68's session-log hook, observe-only (SessionEnd/PostToolUse, never a blocking Stop hook). Full traces on disk; redacted before mining. | [04 #4, #10, #2] |
| 2. Mine failures | GEPA-style reflection over failing traces, keeping a Pareto set rather than one winner. Code graders first; any model judge calibrated against a sealed set. | [04 #7, #3, #14] |
| 3. Propose | Small harness-code edits only (prompts, workflows, tool routing); weights frozen. The proposer reads the archive of past candidates and traces. | [04 #10, #9] [01 #4] |
| 4. Sealed-eval gate | The existing CI gates (agent eval gate, legacy RAG eval gate) plus a **sealed held-out set the proposer never sees**. OW-3 / sealed set S5 is that set for the advice judge. Detect hacking: block test-file edits, hold out whole task families, block on a rising hack rate even when the metric improves. | [01 #13, #12] [04 #11, #12] |
| 5. Human gate | Every promotion is a PR the owner merges. Ask-first modules are excluded from the loop's write scope. | CLAUDE.md §1, §3 |
| 6. Merge + re-gate | Merge with eval counts in the body. Keep rejected variants in the archive. Re-run held-out gates after merge. | [01 #1] [04 #11] |

**Main failure mode to design against: reward hacking.** The DGM optimised its own evaluation [01 #1]. SpecBench agents saturate visible tests and fail held-out ones [01 #13]. Anthropic found reward hacking in production coding RL generalising to sabotage [01 #12]. Self-judging (Self-Rewarding LMs) [01 #10] is therefore not acceptable as the only signal in a health app.

### C. First concrete win: the citation problem (MM-1)

MM-1 measured 15-20/20 abstentions across four local models, because they skip `[cite:N]` and invent references (TASK_LIST MM-1). In order of cost [03]:

1. **Constrained decoding.** An Ollama `format` JSON schema or a llama.cpp GBNF grammar forces each sentence to carry a cite index from the valid set [03 #8, #9, #10]. The faithfulness gate stays and still checks support. This is the natural approach for queue row LEGACY-CITE-PROMPT (RSI-3).
2. **Two-pass prompting** (extract claims, then cite). Only useful as a stage of option 1; prompting alone works poorly at 7B [03 #2].
3. **QLoRA on teacher-generated, rejection-sampled cited answers**, e.g. MedGemma 4B or an 8B model in 4-bit on the RTX 3080 [03 #2, #5, #13]. Measure with ALCE-style citation precision and recall [03 #1]. This is where the donated set (A) feeds use 1.

Gap: no 2024-2026 paper measures citation-marker fine-tuning on medical text at 1-12B [03]. Our own MM-1 script is the measurement.

## Owner decisions this raises

| Gate | Question | Options (recommended first) |
|---|---|---|
| RSI-1 | Is opt-in data donation (pipeline A) in scope for the senior project, or research-only for now? | **Research + design doc only this term** / build a consent screen and local donated-set export / full pipeline |
| RSI-2 | May any derived data leave the device (e.g. DP synthesis through an API)? | **No: everything stays local (local-first)** / only DP-protected aggregates, with a new owner decision row |
| RSI-3 | Fix LEGACY-CITE-PROMPT with constrained decoding first? | **Yes: Ollama `format` schema / GBNF, gate unchanged** / prompt-only / go straight to QLoRA |
| RSI-4 | Should the harness RSI loop (B) start once #68 lands, using the existing CI gates plus OW-3's sealed set? | **Yes, harness-only, PR-gated, ask-first modules excluded** / wait for S5 / no |

## Files

- [01-rsi-self-improving-agents.md](01-rsi-self-improving-agents.md): RSI and self-improving agents (15 sources)
- [02-private-synthetic-health-data.md](02-private-synthetic-health-data.md): opt-in data, de-identification, DP, memorization, collapse (15 sources)
- [03-small-model-citation-finetuning.md](03-small-model-citation-finetuning.md): small-model fine-tuning, distillation, constrained decoding for citations (13 sources)
- [04-rsi-harness-engineering.md](04-rsi-harness-engineering.md): harness optimisation from traces, eval gates, judges (15 sources)
