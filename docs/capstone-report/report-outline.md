# Capstone Report Outline — Evidence-Mapped

**Last Updated:** 2026-10-22

Working outline. Each section names the artifacts that back it — the report is an assembly of verifiable evidence, not narrative invention. Item status: ✅ ready · 🔶 needs work · ⬜ pending.

2026-09-27: statuses were re-checked against the [review follow-up](../../audit/2026-09-25/review/2026-09-27-followup.md). The system description now draws on the [architecture overview](architecture-overview.md) rather than the audit alone. Multi-agent material is framed as case studies (review F-11).

2026-10-20: rewritten against the [claims ledger](claims-ledger.md) rows C11–C32, H12–H21 and M4–M11, including the plan-set status row M9 (stakeholder-showcase claim audit, plan `docs/plans/2026-09-27-senior-report-showcase-plan.md`). Figures point to the ledger-gated [showcase copy](asclexis-showcase-2026-10-22.html), not to the 2026-09-25 page.

## 1. Introduction & motivation

- Problem: longitudinal lab data is inaccessible to patients; cloud tools trade privacy for convenience
- Author motivation: mother's autoimmune labs
- Dual contribution: a locally run product (dev launcher; no installer yet, C8) + agentic-SWE methodology study
- Evidence: [00-original-goal.md](00-original-goal.md) ✅

## 2. System description

- Architecture: FastAPI + per-profile vaults (SQLCipher where installed, C16) + React/TS; middleware stack; dual Alembic
- The five core flows (upload→verify→trends; assistant; record intelligence; lifecycle; feedback→RL) — 2 re-traced, lifecycle code-read, 2 reported (C13)
- Evidence: [architecture-overview.md](architecture-overview.md) (current state + integration diagram) ✅; audit §3–4, §7 as dated context; [`asclexis-showcase-2026-10-22.html`](asclexis-showcase-2026-10-22.html) §01–05 for figures (the ledger-gated copy; the 2026-09-25 page stays unchanged in `audit/` as a dated artifact) ✅
- Honest status column: what's wired vs built-but-inert (notifications) vs absent (packaging) vs partial (verification gate, export redaction; see [specs-compliance-matrix.md](specs-compliance-matrix.md)) ✅
- Agent path note: the default agent path makes no LLM call; the draft is deterministic (C14, [overview §6](architecture-overview.md#6-assistant-path)) ✅

## 3. Safety & privacy design

- Citation checks (agent guard vs legacy `validate_response`, C3, C14), interpret_safety patterns (C4), abstention (agent path; the legacy path abstains on a failed validation since W-4, C28), redaction (strict by default for the opt-in cloud runner, C10)
- Vault model, DEK sealing, recovery codes, ordered crypto-erase
- Evidence: [architecture-engineering-contract.md](architecture-engineering-contract.md) (the rules) + [specs-compliance-matrix.md](specs-compliance-matrix.md) (3 of 78 rows `enforced`, script count 2026-10-20, M4) ✅; audit §4, §11 as context
- Must-own gaps (each a finding, not a feature): `consistency_score=1.0` placeholder (C22, HC-M11); `POST /export/questions` returns `source_quote` unredacted (C20); each backup archive carries a plaintext master copy (C17); the master DB is unencrypted and holds names and password hashes (C18); a deleted profile's audit rows are purged and 4 of 13 profile routes are unaudited (C19); vaults are plain SQLite where SQLCipher is not installed (C16); export artifacts are lost on restart (C11). Fixed since the audit (merge status: ledger row M9): the agent path's hard-coded `faithfulness_score=1.0` (P1, `cc202d9`), the implicit embedding download (W-8, C12), default SQL echo of bound values (S-1, C15), the legacy path serving failed validations (W-4, C28), the unredacted doctor summary (W-2, C24). The ledger rows C2, C3, C6, C7 and C9 predate these merges and are re-verdicted by their owners ✅

## 4. Methodology — the developer→orchestrator shift

- Eras E0–E7 with measured git-author shares and co-author-trailer shares, method stated (H12; evidence figure: showcase §07). Git author name is a proxy: in October 2026 the agent shows mostly as a co-author trailer under a human author name (H12: 98 of 1428 October commits name the agent as author, dated 2026-10-20 or later)
- Harness layers as they accreted (H13): gates (docs lint 2026-02-12, security gate 2026-02-22) → constitution (2026-06-13) → skills (2026-06-23) → eval gate (2026-06-24) → task ledger (2026-07-07) → `route_client` (2026-07-30) → failure memory (2026-08-04)
- Evidence: claims-ledger H1, H12, H13 (commands); audit §9, §12–14 as context ✅

## 5. Harness engineering in depth

- CLAUDE.md/AGENT.md as constitution; 32 process skills + 4 domain skills + routing (H14); feature_list.json as machine-checked ledger; `route_client` (required; many route tests still direct-call, H17); recurring-failures.md as institutional memory
- Evidence: audit §12–13; `docs/agentic/` ✅

## 6. Evaluation — what the harness caught

- Defect taxonomy with commit evidence (July 2026 backup fixes, 12 `fix(backup)` commits 2026-07-29…31, H18; restore 400s under green suite; credential leak past filename-level assertions)
- Fail-open security gate as the flagship case: a green signal that couldn't fail (H4). Fixed in P1: a missing scan report now exits 2, measured 2026-10-20 (`security_gate.py --bandit /nonexistent.json --pip-audit /nonexistent.json` → `ERROR:` line, rc=2; plan §15)
- Phantom layer: `.claude/agents/` + AgentShield claims vs three-level absence (repo/history/user) — `plans/03-phantom-layer.md` evidence table; five definitions were authored new by owner decision D1 on 2026-10-01 (H5, H6) ✅
- Multi-agent review as **case studies** (corrected 2026-09-27, review F-11): the audit reconciler (3 sibling errors), the planning pass (4 audit errors), and the 2026-09-27 re-check, which upheld 16 of 17 independent-review findings and refuted 1; its own reviewers then corrected its F-02 label, a scorecard written before counting, and two miscounts. No capture rates, costs or causal claims: there are no denominators, no seeded errors, and no single-agent comparison. Listed as a Part-2 hypothesis in [research/04](research/04-papers-evals.md) ✅

## 6a. Case study — the 2026-09-27 reconciliation

- What ran: the orchestrator re-checked the package against main @ `40f590e` and recorded owner decisions D1–D13. It then dispatched one author agent per work item: 14 plans in `docs/plans/2026-09-27-*.md`. Each plan was reviewed read-only by Codex in rounds. An Opus reviewer was configured as the fallback when Codex was unavailable.
- Counts (claims-ledger M6, re-counted 2026-10-20 from the review log, which reproduces the 2026-09-27 snapshot): review rounds per plan and fallback events. Counts only. M6 is `CASE-STUDY`: owner decision SHOW-O4 (option B, 2026-10-20) packages the log and the Codex outputs under `docs/reviews/2026-09-27-swarm/`.
- Examples of errors found in these runs: plan authors caught two wrong test-ID notes in the orchestrator's own brief (M7); a security review found SQL echo of bound values in the default dev configuration (C15, since fixed by S-1); a plan author found that CI installed no embedding model, so a "CI has the model" baseline actually depended on an implicit download (C12, since fixed by W-8); the orchestrator's own Wave-0 suite run used unencrypted vaults (M8).
- Verdict: `CASE-STUDY`. Review found errors in these runs. There is no capture rate, cost or causal claim: no seeded errors, no single-agent comparison, no count of errors present, and no token or time accounting.
- Evidence: claims-ledger M6–M8, C12, C15.

## 7. Related work — technology landscape

- Agentic SWE tools (commercial vs open-source), harness/context-engineering practice, RAG+citation techniques, safety evals
- Evidence: [`research/`](research/) scouting documents. 01–03 carry proposed integration contracts with sourced verdicts; 04 is a literature map (`CITE`, not contracts). Laya is framed as an owner-selected test candidate with vendor-reported numbers ✅

## 8. Limitations & threats to validity

- Single-developer project; agent-authored bulk → attribution ambiguity
- Claims-outrun-artifacts failure mode observed in Part-1 report itself (H5, H6, H16)
- Runtime behaviors unexecuted during audit (marked UNKNOWN)
- Local results depend on environment: the Windows interpreter used on 2026-09-27 had no SQLCipher, so its suite run used unencrypted vaults (M8, C16); pass counts are named with their environment
- Evidence: audit §20, methodology note ✅

## 9. Roadmap / future work

- Owner-sequenced program: branches → notifications → phantom-layer decision → doc-drift → utcnow → FK → reset → gated items, plus the gap phases G-A…G-C; the 2026-09-27 plan set (14 plans + S-1) was written PROPOSED, and since then W-1…W-6, W-8, W-10, W-11a PR-4, S-1, P2, P5 and the report-only P6 FK orphan audit have merged (ancestry checks, ledger row M9) while W-7 and W-11b have not
- Evidence: [implementation-program.md](implementation-program.md) (dependency graph, stop gates, measured acceptance, owner decisions D1–D13) ✅; audit §16–18; `plans/01`–`08` (corrected 2026-09-27)

## 10. Conclusion

- Thesis answer: the harness is the deliverable; its failures are the findings
- Maturity verdict: L3 structured → L4 (audit §14). This is the auditor's qualitative rubric, not a measurement (M5); present it as a judgment with its evidence column ✅

## Figures inventory (for the demo/screenshots)

| Figure | Source | Status |
|---|---|---|
| Pipeline diagram | [showcase 2026-10-22](asclexis-showcase-2026-10-22.html) §02 (plan §5 F3) | ✅ ledger-gated copy |
| Safety dual-path lane | [showcase 2026-10-22](asclexis-showcase-2026-10-22.html) §04 (F5) | ✅ ledger-gated copy |
| Vault + crypto-erase diagram | [showcase 2026-10-22](asclexis-showcase-2026-10-22.html) §05 (F6, F7) | ✅ ledger-gated copy |
| Authorship/era timeline | [showcase 2026-10-22](asclexis-showcase-2026-10-22.html) §07 (F11, F12) | ✅ ledger-gated copy |
| Findings table (filtered) | [showcase 2026-10-22](asclexis-showcase-2026-10-22.html) §08 (F13) | ✅ ledger-gated copy |
| Implementation-program dependency graph | [implementation-program.md](implementation-program.md) (Mermaid) | ✅ |
| Integration diagram (current state) | [architecture-overview.md §2](architecture-overview.md#2-integration-diagram-current-state-only) (Mermaid) | ✅ |
| Compliance scorecard | [specs-compliance-matrix.md](specs-compliance-matrix.md) | ✅ |
| Demo script | `docs/plans/2026-09-27-senior-report-showcase-plan.md` §6 | ✅ |

Back to index: [README.md](README.md)
