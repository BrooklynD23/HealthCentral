# Research Scouting — Index

**Last Updated:** 2026-09-27

Technology-scouting documents for the capstone report's Related Work section and the project's roadmap.

Documents 01–03 end every entry with:

- **Proposed contract** — the concrete interface/integration point if adopted (which module, what boundary, what changes)
- **Verdict** — `ADOPT` / `ADAPT` (adopt with modification) / `WATCH` (revisit later) / `REJECT` — with the reasoning
- **Sources** — links/papers; a verdict without sources is flagged, not trusted

Document 04 is a **literature and source map**: each entry has a "Fit for Asclexis" paragraph and a `CITE` / `ADOPT-METHOD` / `WATCH` / `SKIP` verdict, not an integration contract (corrected 2026-09-27, review F-14).

A research `ADOPT` is a recommendation, not a decision. Nothing here is owner-approved or implemented unless a row says so and cites the approval. Anything touching a CLAUDE.md ask-first file, auth/crypto, or the product's network boundary is owner-gated. The gates are listed in [`../implementation-program.md`](../implementation-program.md).

## Documents

| Doc | Scope | Status |
|---|---|---|
| [01-agentic-swe-tools.md](01-agentic-swe-tools.md) | Commercial agents + open-source counterparts. Owner (2026-09-26) chose **Laya over Jev** as the decision-model candidate: open weights, no licence cost. Hardware fit and task accuracy are **vendor-reported, unmeasured on Asclexis** (corrected 2026-09-27, review F-09). Includes a dormancy audit with the GPT-Pilot supply-chain incident. | ✅ 11 entries; Laya claims corrected |
| [02-harness-techniques.md](02-harness-techniques.md) | Context engineering, skills, memory, hooks, orchestration. Top proposal: committed PreToolUse deny-rules on ask-first files. The `.claude/agents/` entry is **owner-gated** under plan 03; it was previously mislabelled "Branch-B"/ADOPT (corrected 2026-09-27, review F-10). | ✅ 17 entries |
| [03-rag-local-llm.md](03-rag-local-llm.md) | Faithfulness/NLI, citation evals (ALCE/RAGAS), abstention, Gemma 4 tiers, retrieval tripwires. Scouting only: product adoption stays behind local evals, licence review and measured hardware checks. | ✅ 16 entries (3 UNVERIFIED) |
| [04-papers-evals.md](04-papers-evals.md) | Literature map: SWE-bench family, MAST failure-taxonomy cross-walk vs `recurring-failures.md`, orchestration studies, 7 Part-2 extension hypotheses. Hypotheses, not results. | ✅ 39 entries |

Verdicts: ADOPT / ADAPT / WATCH / REJECT (01–03); CITE / ADOPT-METHOD / WATCH / SKIP (04). Each has sources. Entries whose claims couldn't be sourced are flagged UNVERIFIED inline.

Back to index: [../README.md](../README.md)
