# The Original Goal — Restated

**Last Updated:** 2026-09-27

For the capstone report's introduction and evaluation sections. Two coupled goals — the product is the substrate; the research is the thesis.

## Product goal (the app)

A **local-first, privacy-first medical results companion**: patients with frequent lab testing (motivation: the author's mother's autoimmune labs) import lab PDFs/images/FHIR exports into per-profile encrypted vaults, verify AI-extracted data through a human-in-the-loop workbench, view longitudinal trends, and ask a local-LLM assistant questions that must be answered with citations — education only, never diagnosis.

Non-negotiables that define the product:
- All PHI stays on-device (per-profile SQLCipher vaults; AES-GCM documents; the only sanctioned network call is model download)
- Human verification gates extracted data before it's trusted
- Every assistant claim cites `[YOUR_RESULTS:N]` (own data) or `[REFERENCE:N]` (knowledge base); memory/history is non-citable
- Deletion is a real cryptographic erase, not a row flag

The non-negotiables above are the product's **stated intent**. Re-checked state on 2026-09-27 (main @ `40f590e`; see [specs-compliance-matrix.md](specs-compliance-matrix.md)):

- All five core flows are implemented and reachable (audit §6, `REPORTED`). The document and assistant flows were re-traced in [architecture-overview.md](architecture-overview.md) §5–§6, and backup and deletion in §3–§4 (code read, not executed).
- Four intents are only **partly** met today: human verification gates the agent path, FHIR and visit-prep, but not the trends endpoint, legacy RAG, or CSV/JSON/doctor-summary exports; those three exports are not redacted; an opt-in external-LLM path can send *redacted* text off-device; and the agent path's trust score is hard-coded on main (fix on an unmerged branch).
- Absent or unwired: desktop packaging; the notification scheduler (built, never started; audit §21 records the owner answer "wire it up"); recovery-code UI for existing profiles (on an unmerged branch).

The report must present these as findings, not as met goals.

## Research goal (the thesis)

Evidence artifact for the **developer → orchestrator shift**: studying how a developer's role changes when the work is done by coding agents — the progression vibe coding → meta-prompting → context engineering → **harness engineering**, where the environment surrounding the agent (constitutions, skills, gates, memory) is itself the engineered deliverable.

What the repo provides as evidence (audit §19; strength of each item corrected 2026-09-27 per review F-11):
- Commit-authorship curve: 100% human Dec–May → ~67% agent overall (239/355 by git author name, re-counted 2026-09-27); ~96% agent after the June pivot (reported by the audit, not re-counted). A measured proxy, not a measure of who did the thinking.
- Defect taxonomy with commit-hash evidence: verification theater, report-as-fact, contaminated-tree gates, phantom layers (qualitative case evidence)
- Drift-vs-gates **hypothesis**: the stale items observed sat where no lint rule runs. There was no systematic sample or comparison, so this is a hypothesis to test, not a correlation.
- Multi-agent review **case studies**: the Sep-25 audit (reported as 6 agents + reconciler) and the planning pass (reported as 8 agents; both counts `REPORTED`, not reproducible from the package) each caught errors in sibling output, and the 2026-09-27 re-check refuted 1 of 17 independent-review findings (plus three sub-claims), while the review in turn caught errors in the re-check. These show that review found errors in these runs. They do **not** measure capture rates, cost, or a causal advantage over single-agent work: there were no denominators, seeded errors, comparison condition, or token/time accounting.

## The honest gap the report must own

The same audit that validates the thesis also documents its failure modes: a fail-open security gate that shipped green, docs citing an agents/hooks layer that doesn't exist (verified: not at repo level, not in git history, not at user level — `plans/03-phantom-layer.md`), and three contradictory test counts. The 2026-09-27 re-check adds more instances of the same pattern: plans that hard-coded a test baseline for trees that will collect more, and a review blocker (F-02) that missed an owner record held on an unmerged branch. The capstone's credibility rests on presenting these *as* findings — Part-2 material, not footnotes.

## Related

- Claims register: [claims-ledger.md](claims-ledger.md)
- Report structure: [report-outline.md](report-outline.md)
- Back to index: [README.md](README.md)
