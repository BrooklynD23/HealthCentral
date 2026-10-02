# Capstone Report Knowledge Base

**Last Updated:** 2026-10-02

Knowledge base for the CS4610 capstone report. It tracks the distance between the project's original goal, the repository's verified state, and the claims the report makes. Everything here is evidence-linked. A claim without a `file:line`, commit hash, or command output is marked UNVERIFIED, not asserted.

**Source of truth for repo state (corrected 2026-09-27):**

- **The live checkout** is authoritative for current implementation.
- The 2026-09-25 audit ([`../../audit/2026-09-25/Devin-Audit-report.md`](../../audit/2026-09-25/Devin-Audit-report.md), main @ `40f590e`) is a dated historical record. Its correction addendum lists what the 2026-09-27 re-check changed.
- The audit's "verified by two independent agents" labels are not reproducible from the package and read as `REPORTED` (review F-16).
- Current-state facts in this folder come from the 2026-09-27 re-check, with evidence inline.

## Contents

| File | Purpose |
|---|---|
| [00-original-goal.md](00-original-goal.md) | Product goal and research question, restated for the report, with the re-checked state beside the stated intent |
| [claims-ledger.md](claims-ledger.md) | Every load-bearing claim ↔ repo evidence ↔ verdict. The anti-overclaim artifact. |
| [report-outline.md](report-outline.md) | Capstone structure; each section mapped to the evidence that backs it |
| [architecture-overview.md](architecture-overview.md) | Verified current architecture (process, data, document/assistant paths, model/network boundary, exports, jobs, migrations, CI) kept separate from proposed change; integration diagram; divergences from `docs/architecture/` |
| [architecture-engineering-contract.md](architecture-engineering-contract.md) | Testable MUST / MUST NOT contracts, each classed `BINDING`, `PROPOSED` or `OWNER-GATED`, with enforcement, verification command, failure response and owner |
| [specs-compliance-matrix.md](specs-compliance-matrix.md) | Requirement → source → implementation → tests → gate → status. 73 rows (recounted 2026-09-28); only 4 `enforced` |
| [implementation-program.md](implementation-program.md) | Dependency-ordered phases over the 8 audit plans plus uncovered gaps, with stop gates, measured acceptance, rollback and owner sign-offs. In execution: Waves 0-2 merged (2026-10-02). |
| [owner-decisions-2026-09-27.md](owner-decisions-2026-09-27.md) | Owner answers to P0-B, D1–D13 and G-B5 (2026-09-27), with the exact option text each licenses |
| Next-agent handoff: [`handoff-2026-09-27-execution.md`](../../audit/2026-09-25/handoff-2026-09-27-execution.md) | Paste-ready brief to start execution at P0-B |
| [research/](research/) | Technology scouting. 01–03 carry proposed integration contracts with sourced verdicts; 04 is a literature map (`CITE`, not contracts). |
| Review follow-up: [`2026-09-27-followup.md`](../../audit/2026-09-25/review/2026-09-27-followup.md) | Disposition of all 17 independent-review findings (F-01…F-17) plus new findings from the re-check |

### 2026-09-27 plan set (`docs/plans/`)

Proposed plans for the program's W-items, amendments and new findings. None is executed; each carries its own owner gates.

| Plan | Purpose |
|---|---|
| [P04 amendment](../plans/2026-09-27-P04-doc-drift-sweep-amendment.md) | Runs audit plan 04's doc-drift sweep on the post-P1 tree, corrects tasks the branches overtook, and adds uncovered drift |
| [P08 amendment](../plans/2026-09-27-P08-gated-packet-hipaa-aligned-amendment.md) | Gated-items packet under the HIPAA-aligned posture (W-9, D10) |
| [S-1](../plans/2026-09-27-S01-sql-echo-phi-leak.md) | SQL echo PHI leak fix (new HIGH finding; gates SQL-ECHO / S1-A / S1-B) |
| [W-1](../plans/2026-09-27-W01-harness-agents-branch-a.md) | Commit the five named subagents (D1, Branch A) |
| [W-2](../plans/2026-09-27-W02-doctor-summary-redaction.md) | Strict redaction of the doctor summary (D3) |
| [W-3](../plans/2026-09-27-W03-verified-only-rag-and-trend-labels.md) | Verified-only legacy RAG and labelled unverified trend points (D4) |
| [W-4](../plans/2026-09-27-W04-legacy-abstain-and-eval-gate.md) | Legacy RAG abstains on invalid answers, plus a CI eval gate (G-B5) |
| [W-5](../plans/2026-09-27-W05-citation-marker-prompt.md) | Align the legacy prompt's citation-marker instruction (D11) |
| [W-6](../plans/2026-09-27-W06-external-runner-hardening.md) | External runner: unconditional redaction, audited break-glass (D12) |
| [W-7](../plans/2026-09-27-W07-tiered-interpretation-via-modelrunner.md) | Tiered interpretation routed through ModelRunner (D7) |
| [W-8](../plans/2026-09-27-W08-bundled-embedding-model.md) | Bundled embedding model, offline load, fail closed (D8) |
| [W-10](../plans/2026-09-27-W10-governance-invariant-amendments.md) | Governance commit: invariant amendments for D3, D4, D12 |
| [W-11a](../plans/2026-09-27-W11a-test-and-gate-hardening.md) | Test and gate hardening (G-B1, G-B2, G-B4, G-B6) |
| [W-11b](../plans/2026-09-27-W11b-roadmap-items-gc1-gc4.md) | Roadmap items G-C1…G-C4 |
| [Nightly doc-drift routine](../plans/2026-09-27-nightly-doc-drift-routine-spec.md) | Specification for a scheduled doc-drift check |
| [Senior report showcase](../plans/2026-09-27-senior-report-showcase-plan.md) | CS4610 senior report stakeholder showcase update plan |

## Maintenance rules

1. **Claims go through the ledger.** Before a claim appears in the report, it gets a claims-ledger row with evidence. Audit-sourced items are `REPORTED` until re-verified. They do not inherit the audit's verdict.
2. **Dates are real wall-clock** (owner answer, audit §21 Q5). Don't invent timeline entries.
3. **Research verdicts need sources.** Every `research/` entry cites URLs or papers. A verdict without sources is an opinion and gets flagged. A vendor's own benchmark is labelled vendor-reported.
4. **Current vs proposed.** Architecture, contract, matrix and program keep `implemented` / `wired` / `tested` / `proposed` / `owner-approved` / `owner-gated` / `unknown` distinct. An owner approval is cited to its record and never widened beyond its text.
5. **Update `**Last Updated:**` on every edit** and keep this index current. `docs_lint` DOC-011 flags files nobody links.
6. Corrections to submitted coursework (`CS4610_Report_Demo/*.docx`) live as scope notes in `CS4610_Report_Demo/README.md`, never as docx edits.

## Open threads

- [x] Specs/compliance matrix: [specs-compliance-matrix.md](specs-compliance-matrix.md) (2026-09-27)
- [x] Implementation program: [implementation-program.md](implementation-program.md) (2026-09-27; in execution — Waves 0-2 merged by 2026-10-02, see the [ledger](../../audit/2026-09-25/swarm-2026-09-27/ledger.md))
- [x] Research scouting: 4 docs in `research/` (2026-09-25). Laya claims corrected 2026-09-27. The Jev↔Laya choice is an owner preference (2026-09-26), not a measured result.
- [x] Owner decisions D1–D13, P0-B, G-B5: [owner-decisions-2026-09-27.md](owner-decisions-2026-09-27.md) (2026-09-27). The phantom layer is D1 = Branch A, all 5 agents.
- [ ] Decision: does the capstone present the phantom-layer finding as a defect, a correction, or a case study? (audit §19, plan `03-phantom-layer.md`)
- [ ] `docs/INDEX.md` regeneration to catalogue the new docs. It is blocked on the owner's uncommitted `docs/INDEX.md` edits (program P0-B).
