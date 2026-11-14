# Senior Report Phase 1 — Evidence Index

**Last Updated:** 2026-11-11
**Owner:** repository owner
**Status:** DRAFT (Phase 1), measured on `origin/main` @ `e5c7bf80`.
**Refresh Trigger:** any edit to [report-draft.md](report-draft.md) that adds or changes a claim; any change to a row of the [claims ledger](../claims-ledger.md) cited here.

Claim → source table for [report-draft.md](report-draft.md) and [presentation-outline.md](presentation-outline.md). Where a claim already has a row in the [claims ledger](../claims-ledger.md), this index points to that row and does not restate its evidence; the ledger stays the single place for those claims. Rows marked **new** are claims this draft adds; they are candidates for ledger rows when the report is frozen (`docs/capstone-report/README.md`, Maintenance rule 1).

Verification legend: **R** = re-run or re-read for this draft on 2026-11-11 at `e5c7bf80`; **L** = taken from the ledger row as dated there; **D** = taken from the cited document as dated there, not re-run.

## 1. Claim → source

### Product (report §1-§3)

| # | Claim (report section) | Source | Ledger | Check |
|---|---|---|---|---|
| EI-P1 | Backend binds `127.0.0.1`; CORS only the local frontend (§1.2) | `src/backend/main.py:121-123,180-191` | C30 | R |
| EI-P2 | 19 routers under `/api/v1` (§1.2) | `src/backend/api/__init__.py:48-72` | H14 | R |
| EI-P3 | 45 module files plus the `agent/` package; 17 pages (§1.2) | `git ls-files 'src/backend/modules/*.py'`; `ls src/frontend/src/pages/*.tsx` | H14 (16 pages at `a16dd51`) | R |
| EI-P4 | Master DB is plain SQLite and holds names and password hashes (§1.2, App. A) | `core/config.py:41`; `core/database.py:62-71` | C18 | R |
| EI-P5 | Vault opened through `sqlcipher3` with `PRAGMA key`; migrations run on every open (§1.2) | `core/profile_database.py:264-393` | C1 | R |
| EI-P6 | PBKDF2-HMAC-SHA256 at 600,000 iterations; DPAPI or password sealing (§1.2) | `core/security.py:184-198,314-384` | — new | R |
| EI-P7 | AES-GCM document files with a fresh IV per file (§1.2) | `core/security.py:443`; `modules/ingest.py:175` | C21 | L |
| EI-P8 | Closed vault → 401 via `ProfileDbSession`; other profile's path → 403 (§1.2) | `core/auth.py:286,300-341` | — new (overview §3 says 403; code says 401) | R |
| EI-P9 | Foreign keys enforced on both engines (§1.2, §1.7) | `core/database.py:46-71`; `core/profile_database.py:380-382`; migration 017 | updates H10 | R |
| EI-P10 | Master chain 3 revisions; profile chain 19, head `019_export_artifacts` (§1.2) | `ls src/backend/migrations/*/versions/` | H8 | R |
| EI-P11 | Suite runs with encryption not required; no backend ciphertext test (§1.2) | `tests/conftest.py:57` | C1 | L |
| EI-P12 | Observations created `user_verified=False`; chunks before verification (§1.3) | `api/documents.py:681,794,864` | C2 | R (explorer lines) |
| EI-P13 | Trend points carry `user_verified`, per D4 (§1.3) | `api/observations.py:712-819`; owner D4 | C2 | R |
| EI-P14 | Extraction golden set 28/0/0 on 2026-10-18 (§1.3, §3) | `docs/agentic/eval-cards/extraction.md` | — new | R |
| EI-P15 | Agent path default on; no model call under `modules/agent/` (§1.4, §2) | `modules/agent/settings.py:19`; `grep` | C14 | R |
| EI-P16 | Hard-coded `faithfulness_score=1.0` removed (§1.4) | `cc202d98` (2026-09-10) via PR #21 (2026-09-29); no match in `api/assistant.py` (grep) | C3 | R |
| EI-P17 | Legacy validator: `[cite:N]`, prohibited patterns, faithfulness ≥ 0.6 (§1.4) | `modules/rag.py:888-985` | C3, C28 | R (explorer lines) |
| EI-P18 | Retrieval has no similarity cutoff; 0.7 is a test assertion and the verifier's entailment bound (§1.4) | `rag.py:696-699`; `tests/test_rag_pipeline.py:269`; `modules/verifier_agent.py:76` | — new | R |
| EI-P19 | Embedding model `all-MiniLM-L6-v2`, offline, fail-closed (§1.4) | `modules/embeddings.py:16-19`; W-8 | C12 | R |
| EI-P20 | Redaction levels strict / standard / minimal (§1.5) | `modules/redaction.py:23-286` | — | R |
| EI-P21 | Audit choke point `create_audit_log` with action allow-list (§1.5) | `core/audit.py:36,202-270` | C19 | R (explorer lines) |
| EI-P22 | 74 golden agent cases, six axes, absolute bars (§1.5, §3) | `docs/agentic/evals.md:22`; `ls tests/agent/golden` | H14 | R |
| EI-P23 | Doctor summary strict-redacted; only CSV/JSON exempt (§1.5) | `api/export.py:673-675`; `modules/export.py:235-248`; owner D3 | C24 | R |
| EI-P24 | Notification scheduler now started (§1.6) | `main.py:81-85`; `core/auth.py:414,445` | C31 | R |
| EI-P25 | Export artifacts persisted in the vault (§1.6) | `models/export_artifact.py:34`; migration 019 | C11 | R (migration and model names; store code not read) |
| EI-P26 | Restore 400 / credential leak under 32 green tests (§1.6, §5.2) | `842bc494`, `565f7085`, PR #18; `recurring-failures.md` §1 | H18 | R |
| EI-P27 | 11 CI jobs; frontend job runs eslint and a build (§1.7) | `.github/workflows/ci.yml` | H14 (9 jobs at `a16dd51`) | R |
| EI-P33 | CI green on `e5c7bf80` except E2E, still running at writing (§12) | `gh run view 43128414274` | — new | R |
| EI-P28 | Ollama provider localhost-only at construction (§2) | `core/llm/ollama_provider.py:34-78`; `api/model_settings.py:940-946` | H11 | R |
| EI-P29 | External runner off by default; strict always; break-glass audit row or refusal (§2) | `models/model_settings.py:79-82`; `core/external_runner.py:95-317` | C10 | R |
| EI-P30 | Four local models: abstain 0.75–1.00, cited 0.00–0.05, n=20 (§2, §3) | PR #150 comment 6247765961; `rsi-in-development-and-application.md` §6 | — | D |
| EI-P31 | Compliance matrix 3 of 78 enforced (§3) | `specs-compliance-matrix.md`; scorecard script | M4 | L |
| EI-P32 | `llama_cpp` import in `model_selector.py` still dormant (§1.7) | `modules/model_selector.py:456`; `grep interpret_with_model` | H11 | R |

### Method (report §4-§8)

| # | Claim (report section) | Source | Ledger | Check |
|---|---|---|---|---|
| EI-M1 | Per-era authorship counts E0–E7 (§4.1) | ledger H12 command at `a16dd51` | H12 | L |
| EI-M2 | 2563 of 3836 commits carry a Claude trailer (§4.1) | `git log -i --grep='Co-Authored-By: Claude'` | — new | R |
| EI-M3 | Harness layer order (§4.1) | ledger H13 | H13 | L |
| EI-M4 | Codex reviewed 14 plans in 51 rounds, no fallback (§4.3) | `docs/reviews/2026-09-27-swarm/reviewer-log.tsv` | M6 | L |
| EI-M5 | 80 Codex review files; 76 commits mention Codex (§4.3) | `find docs/reviews -iname '*codex*'`; `git log -i --grep=codex` | — new | R |
| EI-M6 | Codex unavailability rows (§4.3) | `owner-decisions-2026-09-27.md:173,315`; `2ffefdcc` | — | R |
| EI-M7 | Audit file has no Devin content; research/04 claim contradicted (§4.4) | `audit/2026-09-25/Devin-Audit-report.md:3`; `research/04-papers-evals.md:220`; `git log --author='Devin AI'` | — new | R |
| EI-M8 | Devin record: smoke test, #53 refresh, PARA branch, MCP failures (§4.4) | `audit/2026-09-25/waves/wave-4-L0-notes.md:35-43`; `wave-4.md:47`; `handoff-2026-10-12-wave5.md:51` | — new | R |
| EI-M9 | Interim Cursor session merged #333, #329, #338 (§4.5) | `docs/plans/2026-10-24-session-handoff.md:11` | — new | R |
| EI-M10 | 21 failure modes (§5.1) | `docs/agentic/recurring-failures.md` | H14 (12 at `a16dd51`) | R |
| EI-M11 | Count slot history (§5.5) | `git log -G 'backend tests collected' -- CLAUDE.md` | M3 | R |
| EI-M12 | 4984 collected on `e5c7bf80` (§5.5, summary) | Haiku test runner, `pytest --collect-only` output (Appendix B) | — new | R |
| EI-M12b | 5003 latest measured count slot value (§5.5) | `queue.md` count slot, BATCH-1111G (open PR #619) | — new | D (not re-run for this draft) |
| EI-M13 | 621 tests on 2026-06-11 (§5.5) | `docs/plans/implementation-log/2026-06-11_verification-report.md` §2 | — | R |
| EI-M14 | UIDOC-006A diagnosis and fix (§5.4) | `docs/plans/2026-11-11-batch-1111a-plan.md:75-119`; PR #591 | — new | R |
| EI-M15 | MEDS-G-FLAKE diagnosed as harness timing, not ICU; option A awaits owner gate MEDS-G-X1 (§5.4) | `queue.md` row MEDS-G-FLAKE, docs batch BATCH-1111G (open PR #619; `origin/docs/batch-1111g`) | — new | R (PR branch, not `main`) |
| EI-M16 | Three-tier L0/L1/L2 model; nesting depth measured (§6.1) | `docs/agentic/orchestration.md` §1 | — | R |
| EI-M17 | Build-program scripts and Task 0 (§6.2) | `RUNBOOK.md` §4, §10.1; `.claude/workflows/build-program.js` | — | R |
| EI-M18 | Docs batch must merge before the item's PR (§6.2) | `RUNBOOK.md` §10.1, L0 duty #5 | — | R |
| EI-M19 | Merge authority rows (§6.2) | `owner-decisions-2026-09-27.md:206,246,438,452` | — | R |
| EI-M20 | Routing history 09-28 → 10-24 → 10-29 (§6.3) | `orchestration.md` §1; owner rows `:421,432,433` | — | R |
| EI-M21 | Trailer counts per model and date ranges (§6.3) | `git log` trailers (Appendix B) | — new | R |
| EI-M22 | 18 build-item runs: 12.7 agent-hours, 10.8M tokens (§6.4, §7.5) | `docs/plans/2026-11-01-harness-speedup-plan.md:13-17` | — | R |
| EI-M23 | 677 agents, STYLE-FILE-MISSING cost (§7.5) | `queue.md` STYLE-FILE-MISSING | — | R |
| EI-M24 | Serena is the only configured MCP server (§7.2) | `.mcp.json` | — | R |
| EI-M25 | 36 skills: 32 + 4; added in three commits (§7.3) | `find … -name SKILL.md`; `git log --diff-filter=A` | H14 | R |
| EI-M26 | Only committed hook is the metadata session logger (§7.4) | `.claude/settings.json`; `.claude/hooks/session_log.py` | H6 | R |
| EI-M27 | RSI tracks, workflow stages, allow/deny lists (§8.1-§8.2) | `rsi-in-development-and-application.md`; `.claude/workflows/rsi-loop.js:36-54` | — | D (stage lines from explorer) |
| EI-M28 | 36 replay fixtures; RSI Replay CI job (§8.2) | `.claude/mods/asclexis-rsi/replay/cases.ts`; `ci.yml:498` | — | R |
| EI-M29 | RSI runs table; #341 from the 2026-10-24 run; #230 from an unarchived 2026-10-20 cloud run; both merged 2026-10-24 (§8.3) | `docs/agentic/rsi-runs/README.md`; `gh pr view 230 --json headRefName` | — | R |
| EI-M30 | pkill-self guard denied 8 of 10 (§8.3) | `docs/agentic/rsi-runs/2026-10-31-gpubox/summary.json` | — | R |
| EI-M31 | RSI1-DONATE PR-1 merged, PR-2 blocked on recall (§8.5) | #211, #239; owner rows `:349,379,427` | — | R |

## 2. Evidence gaps

Each gap is marked `[evidence gap]` at its place in the draft. IDs are prefixed `EI-` (claims) and `GAP-` (gaps) so they do not collide with ledger rows or UI gates.

| # | Gap | Where | What would close it |
|---|---|---|---|
| GAP-1 | No user study or usability test | §3 | a study with an ethics review, or state it as out of scope |
| GAP-2 | No accuracy figure on real lab reports (synthetic only, by design) | §3 | none without patient data; keep as a stated limit |
| GAP-3 | Compliance matrix not re-scored since migrations 017–019 | §3 | re-run the scorecard script |
| GAP-4 | Audit-coverage (AUD-02) not re-checked on `e5c7bf80` | §1.5 | route-by-route grep for audit calls |
| GAP-5 | Backup archive's master copy not re-checked after #603 | §1.6, App. A | open an archive built on current `main` |
| GAP-6 | D12 UI warning component not located | §2 | find the frontend component that reads `redaction_break_glass` |
| GAP-7 | No latency or memory figures per model tier | §2 | a measured run on the model host |
| GAP-8 | No comparison between Haiku and Sonnet as implementers | §6.3 | out of scope; the reversal was an owner decision |
| GAP-9 | No dollar-cost accounting anywhere | §6.4, §7.5 | billing export per session |
| GAP-10 | Session tool-call analysis is off-repo (14,227 calls; 29% rework) | §7.5 | commit the analysis output, or re-run `ingest.py` and `q1`–`q6` |
| GAP-11 | Narrow-agent vs full-resume call counts are off-repo | §7.5 | same |
| GAP-12 | No before/after token measurement of the HARNESS-SPEEDUP fixes | §7.5 | compare build-item runs before and after |
| GAP-13 | "Don't cut review rounds" note is in operator memory only | §7.5 | record in the RUNBOOK |
| GAP-14 | `gh pr merge` ignores non-required failures: operator memory only | §6.2 | record in the RUNBOOK |
| GAP-15 | No usage data per skill | §7.3 | count skill invocations from session logs |
| GAP-16 | Supabase, Vercel, Tavily MCP and Google Stitch use (May report) | §4.6, §7.2, App. A | none in repo; keep as not evidenced |
| GAP-17 | Which Codex model version ran in each review | §4.3 | record the model in each review file |
| GAP-18 | Why the audit file is named "Devin" | §4.4 | owner answer |
| GAP-19 | UIDOC-006A raw diagnosis is off-repo | §5.4 | commit the diagnosis file |
| GAP-20 | MEDS-G-FLAKE diagnosis is recorded only on an open PR (#619) and in an off-repo report; the fix awaits owner gate MEDS-G-X1 | §5.4 | merge of #619; commit the diagnosis report; owner answer to MEDS-G-X1 |
| GAP-21 | Causes of the 1560 spike (2026-10-13) and 3066 → 4141 jump (2026-11-05) | §5.5 | diff the commits around each slot change |
| GAP-22 | No current frontend test count | §5.5 | `npx vitest run` and `npx playwright test --list` on `main` |
| GAP-23 | No time log of the author's own hours per era | §10 | none retrospectively |
| GAP-24 | Master-database encryption is not planned in the sources read | §11 | owner decision |
| GAP-25 | Productivity effect of agents not measured | §9 | out of scope |
| GAP-26 | No ADR log (track 10 gap, still open) | App. A | add `docs/adr/` or record as declined |

### Gaps recorded by track 10 (2026-09-09), carried forward

`docs/research/2026-09-08/10-demonstration-artifact.md` §2 listed the evidence gaps in the earlier reports. Status on `e5c7bf80`:

| Track 10 gap | Status now | Where in this draft |
|---|---|---|
| `.claude/agents/` does not exist | **closed**: five definitions since 2026-10-01 (D1), written new | §6.1; ledger H5 |
| No hooks, no `settings.json` | **partly closed**: metadata session logger since 2026-10-10 (#68); no PHI hook | §7.4 |
| AgentShield PreToolUse hook (TC §4.6) | **carried**: not evidenced | App. A; ledger H6 |
| Final Report §7.2 hook claim | **carried**: not evidenced | App. A |
| Ralph-style RAG sweep (FR §7.3) | **carried**: not evidenced; an eval-card directory now exists (extraction only) | App. A; §3 |
| Superpowers on SQLCipher/JWT; unique-IV anecdote | workflow **evidenced**; anecdote **carried** | §7.3; App. A |
| Cross-vendor Codex review (FR §7.1) | workflow **closed** (51 rounds, ledger M6); JWT anecdote **carried** | §4.3; App. A |
| OpenWiki said to exist | **carried**: still not generated | App. A |
| No ADR log or `CONTEXT.md` | **carried** | GAP-26 |
| CS4610 PDFs not discoverable | **closed** by the scope note `CS4610_Report_Demo/README.md` and by §13.1 | §13.1 |
| Narrative logs stopped before the July bugs | **carried as a finding**: structured state replaced narrative logs | §7.1 |

## 3. Lineage

Each prior report, the commit or date it was measured at, and the sections of the new draft that supersede or extend it. Prior reports are not edited; they stay as dated records (`docs/capstone-report/README.md`, Maintenance rules 2 and 6).

| Prior report | Dated / measured at | Carried forward | Superseded or corrected | New draft sections |
|---|---|---|---|---|
| CS4610 Final Report (`CS4610_Report_Demo/HealthCentral_CS4610_Final_Report.pdf`, `.docx`) | May 2026 (cover May 15; §6 says Apr 22) | motivation, product scope, tool timeline frame, reflections, references | encryption, backup, cloud, desktop, assistant, hook, skill, sweep, JWT-anecdote claims | Summary; §1.1, §1.2, §1.4, §4 intro, §7.2-§7.4, §13.1, App. A |
| CS4610 Technical Companion (`…_Technical_Companion.pdf`, `.docx`) | May 2026 | SDLC → agentic-scaffold mapping; framework survey (ECC, GSD, Superpowers) | AgentShield adoption; GSD v2 RAG run; unique-IV anecdote | §6, §7.3, §9, App. A |
| `CS4610_Report_Demo/README.md` (scope note) | 2026-09-27 additions | every not-evidenced and false item | — (this draft extends it to current state) | App. A |
| `docs/capstone-report/README.md` | 2026-11-08 | maintenance rules, open threads | — | header; §13.1 |
| `docs/capstone-report/00-original-goal.md` | 2026-09-27 | product and research goals; non-negotiables | the "partly met" list is updated by §1.7 | §1.1, Summary |
| `docs/capstone-report/report-outline.md` | 2026-11-08 | thesis; sections; case-study framing (F-11); limitations | section order (product first, verification before orchestration, per advisor); harness-layer order (ledger H13) | whole draft |
| `docs/capstone-report/claims-ledger.md` | 2026-10-22 | every C, H and M row cited | stale counts in H14 (pages 16 → 17, CI jobs 9 → 11, failure modes 12 → 21) noted, ledger not edited | this index §1 |
| `docs/capstone-report/architecture-overview.md` | 2026-10-20, `40f590e` | the subsystem, data, path and boundary picture | 12 rows changed (§1.7), including 403 → 401, FK, export artifacts, scheduler, doctor summary, CI | §1, §1.7, §2 |
| `docs/capstone-report/architecture-engineering-contract.md` | 2026-10-02 | rules as stated | C-SCHED-2, C-MIG-3, C-REDACT-1 status changed (§1.7) | §1.7 |
| `docs/capstone-report/specs-compliance-matrix.md` | 2026-10-09/20 | scorecard (ledger M4) | not re-scored (GAP-3) | §3 |
| `docs/capstone-report/implementation-program.md` | 2026-10-02 | wave structure and owner gates | execution moved to the build program (2026-10-15) | §6.1-§6.2 |
| `docs/capstone-report/owner-decisions-2026-09-27.md` | 2026-11-11 | every owner row cited (D3, D4, D11, D12, routing, merge, RSI, donation, flakes) | — | §1-§8 |
| `docs/capstone-report/rsi-in-development-and-application.md` | 2026-10-31 | RSI definition, tracks, gates, baselines, limits | "PR #122 not merged" and "RSI1-DONATE planned" are stale (#122 and #211 merged) | §2, §8 |
| `docs/capstone-report/fit-decoder-journey.md` | — | decided direction for wearables | — | §11 |
| `docs/capstone-report/research/01`–`04` | 2026-09-25/27 | landscape, harness techniques, RAG and local LLM survey, literature map | research/04's "largely built with Devin" contradicted (§4.4) | §9, §13 |
| `docs/capstone-report/asclexis-showcase-2026-10-22.html` | 2026-10-22 | ledger-gated figures (pipeline, safety lane, vault, eras) | numbers dated 2026-10-22 | presentation slides 4-7, 10 |
| `audit/2026-09-25/Devin-Audit-report.md`, `asclexis-showcase.html`, `waves/scaffold/SHOWCASE.md` | 2026-09-25, `40f590e`; addendum 2026-09-27 | findings, maturity rubric (as judgment, M5), harness assessment | "E1 100% human" contradicted (ledger H12); not a Devin record (§4.4) | §4.1, §4.4, §7.1 |
| `docs/plans/2026-09-27-senior-report-showcase-plan.md` | 2026-09-27 | demo script, figure list, claim-freeze idea | — | presentation |
| `docs/plans/2026-10-10-rsi-loop-applicability-report.md` | 2026-10-10 | "~3/4 of an RSI loop"; RL export bug | — | §8.1 |
| `docs/research/2026-10-20-rrsi-harness2/05-report-angle.md` | 2026-10-20 | status labels; non-causal framing | "no promotion has merged" now stale (#230, #341) | §8.3-§8.4 |
| `docs/research/2026-09-08/10-demonstration-artifact.md` | 2026-09-09 | gap table (above); the process arc; narrative-log finding | gaps closed or carried, table above | §7.1, App. A, this index §2 |
| `docs/Local_First_Medical_Results_Companion_PRD_v0_1.md` | v0.1 | product requirements | PRD's FAISS/e5/Tauri proposals not built (all-MiniLM, vault table, no shell) | §1.1-§1.4 |
| `docs/archive/agile/RETRO.md` | sprint S0–S6 | product-agent sprint retro | — (no coding-agent content) | §4.1 context only |
| `docs/archive/plans/2026-07-02-consolidated-findings-report.md` | 2026-07-02 | CI gap list of that date | gaps since closed (§1.7 CI rows) | §1.7 |
| `docs/plans/implementation-log/2026-06-11_verification-report.md` | 2026-06-11 | 621-test baseline; "do not lower the threshold" | — | §5.5 |
| [workflow-optimization-quiet-box.md](workflow-optimization-quiet-box.md) (Phase 1 input) | 2026-11-11, `origin/main` @ `c79b7fd1`; read-only consultant review (Fable 5.2) | the three time sinks, the host measurement (24 CPUs / 37 GiB), options A-N with `[E]` estimates, the RSI proposal, the guardrails | — (new; estimates and operator reports are tagged in the file, not re-run) | §6.5, §8, §11 |

[PHASE 2 PLACEHOLDER: claim rows, gaps and lineage entries for other projects' material.]
