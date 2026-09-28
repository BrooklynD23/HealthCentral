# Capstone Report Outline — Evidence-Mapped

**Last Updated:** 2026-09-27

Working outline. Each section names the artifacts that back it — the report is an assembly of verifiable evidence, not narrative invention. Item status: ✅ ready · 🔶 needs work · ⬜ pending.

2026-09-27: statuses were re-checked against the [review follow-up](../../audit/2026-09-25/review/2026-09-27-followup.md). The system description now draws on the [architecture overview](architecture-overview.md) rather than the audit alone. Multi-agent material is framed as case studies (review F-11).

## 1. Introduction & motivation

- Problem: longitudinal lab data is inaccessible to patients; cloud tools trade privacy for convenience
- Author motivation: mother's autoimmune labs
- Dual contribution: working product + agentic-SWE methodology study
- Evidence: [00-original-goal.md](00-original-goal.md) ✅

## 2. System description

- Architecture: FastAPI + per-profile SQLCipher vaults + React/TS; middleware stack; dual Alembic
- The five core flows (upload→verify→trends; assistant; record intelligence; lifecycle; feedback→RL)
- Evidence: [architecture-overview.md](architecture-overview.md) (verified current state + integration diagram) ✅; audit §3–4, §7 as dated context; [`asclexis-showcase.html`](../../audit/2026-09-25/asclexis-showcase.html) §01–05 for figures (a showcase, not an audit source; re-check each figure against the overview) 🔶
- Honest status column: what's wired vs built-but-inert (notifications) vs absent (packaging) vs partial (verification gate, export redaction; see [specs-compliance-matrix.md](specs-compliance-matrix.md)) ✅
- Agent path note: the default agent path makes no LLM call; the draft is deterministic ([overview §6](architecture-overview.md#6-assistant-path)) ✅

## 3. Safety & privacy design

- Citation contract, interpret_safety suite, abstention/escalation, redaction gate
- Vault model, DEK sealing, recovery codes, ordered crypto-erase
- Evidence: [architecture-engineering-contract.md](architecture-engineering-contract.md) (the rules) + [specs-compliance-matrix.md](specs-compliance-matrix.md) (4 of 73 rows `enforced`, recounted 2026-09-28) ✅; audit §4, §11 as context
- Must-own gaps: `consistency_score=1.0` placeholder (HC-M11); the agent path's hard-coded `faithfulness_score=1.0` on main (fix unmerged); CSV/JSON/doctor-summary exports unredacted despite `data-privacy.md:173`; trends and legacy RAG read unverified data; export-store ephemerality ✅

## 4. Methodology — the developer→orchestrator shift

- Eras E0–E6 with the authorship curve (evidence figure: showcase §07)
- Harness layers as they accreted: constitution → skills → ledger → gates → memory
- Evidence: audit §9, §12–14; commits ✅

## 5. Harness engineering in depth

- CLAUDE.md/AGENT.md as constitution; 18 skills + routing; feature_list.json as machine-checked ledger; `route_client` as a targeted blind-spot fix; recurring-failures.md as institutional memory
- Evidence: audit §12–13; `docs/agentic/` ✅

## 6. Evaluation — what the harness caught

- Defect taxonomy with commit evidence (July backup storm; restore 400s under green suite; credential leak past filename-level assertions)
- Fail-open security gate as the flagship case: a green signal that couldn't fail
- Phantom layer: `.claude/agents/` + AgentShield claims vs three-level absence (repo/history/user) — `plans/03-phantom-layer.md` evidence table ✅
- Multi-agent review as **case studies** (corrected 2026-09-27, review F-11): the audit reconciler (3 sibling errors), the planning pass (4 audit errors), and the 2026-09-27 re-check, which upheld 16 of 17 independent-review findings and refuted 1; its own reviewers then corrected its F-02 label, a scorecard written before counting, and two miscounts. No capture rates, costs or causal claims: there are no denominators, no seeded errors, and no single-agent comparison. Listed as a Part-2 hypothesis in [research/04](research/04-papers-evals.md) ✅

## 7. Related work — technology landscape

- Agentic SWE tools (commercial vs open-source), harness/context-engineering practice, RAG+citation techniques, safety evals
- Evidence: [`research/`](research/) scouting documents. 01–03 carry proposed integration contracts with sourced verdicts; 04 is a literature map (`CITE`, not contracts). Laya is framed as an owner-selected test candidate with vendor-reported numbers ✅

## 8. Limitations & threats to validity

- Single-developer project; agent-authored bulk → attribution ambiguity
- Claims-outrun-artifacts failure mode observed in Part-1 report itself
- Runtime behaviors unexecuted during audit (marked UNKNOWN)
- Evidence: audit §20, methodology note ✅

## 9. Roadmap / future work

- Owner-sequenced program: branches → notifications → phantom-layer decision → doc-drift → utcnow → FK → reset → gated items, plus the gap phases G-A…G-C
- Evidence: [implementation-program.md](implementation-program.md) (dependency graph, stop gates, measured acceptance, owner decisions D1–D13) ✅; audit §16–18; `plans/01`–`08` (corrected 2026-09-27)

## 10. Conclusion

- Thesis answer: the harness is the deliverable; its failures are the findings
- Maturity verdict: L3 structured → L4 (audit §14). This is the auditor's qualitative rubric, not a measurement; present it as a judgment with its evidence column 🔶

## Figures inventory (for the demo/screenshots)

| Figure | Source | Status |
|---|---|---|
| Pipeline diagram | showcase §02 | 🔶 re-check vs overview/ledger |
| Safety dual-path lane | showcase §04 | 🔶 re-check vs overview/ledger |
| Vault + crypto-erase diagram | showcase §05 | 🔶 re-check vs overview/ledger |
| Authorship/era timeline | showcase §07 | 🔶 re-check vs overview/ledger |
| Maturity bars | showcase §06 | 🔶 re-check vs overview/ledger |
| Findings table (filtered) | showcase §08 | 🔶 re-check vs overview/ledger |
| Implementation-program dependency graph | [implementation-program.md](implementation-program.md) (Mermaid) | ✅ |
| Integration diagram (current state) | [architecture-overview.md §2](architecture-overview.md#2-integration-diagram-current-state-only) (Mermaid) | ✅ |
| Compliance scorecard | [specs-compliance-matrix.md](specs-compliance-matrix.md) | ✅ |

Back to index: [README.md](README.md)
