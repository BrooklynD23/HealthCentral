# CS4610 Senior Report — Stakeholder Showcase Update Plan

**Last Updated:** 2026-10-22 (freeze run recorded in §15.1 under O-6, which moved the freeze from 2026-10-24 to 2026-10-22; showcase 2026-10-31); 2026-10-20 (refreshed under SHOW-AUDIT A)
**Owner:** repository owner
**Refresh Trigger:** P1 merges (re-verify every `main@40f590e` line below); any of W-1, W-8 or W-11a edits `docs/capstone-report/claims-ledger.md`; any of P2, S-1, W-2, W-3, W-4, W-6 or W-8 merges (each upgrades a claim in §9); the owner sets the showcase date; the reviewer log used in §6 changes
**Status:** REFRESHED 2026-10-20 — executing under build-program item F-9 (draft PR #210). This refresh is commit C0. The owner answered O-1, O-2, O-5 and O-7 on 2026-10-20 (L0 record: PR #210 comment 6285564680; the verbatim rows reach `owner-decisions-2026-09-27.md` in the next owner-rows PR). After the Codex plan review (REVISE, comment 6285504146) this plan was reconciled in commit C0b. Scope of the F-9 run: C0b, Tasks 1-7 (Task 3 including the §4.1 insertion and the new-copy pointers; Task 5 Edits 1-4, 6 and Edit 5; Task 7 Step 5) and a pre-freeze rehearsal of Task 10 Step 1 (recorded in §15; progress is in PR #210). Not in scope for that run: Task 8 (O-4 A/B unanswered), Task 9 (owner, Windows), O-3, Task 10 Steps 2-3 and C7 (2026-10-24, O-6). No §13 box is ticked or signed by an agent (RUNBOOK §9.2); the table records the owner's answers in prose only.
**Refresh triggers fired since 2026-09-27:** P1 (both branches ancestors of main), W-1 (#35), P2 notifications (#31), W-3 (#136), W-4 (#72), W-5 (#34), W-6 (#32), W-8 (#168, #196), W-10 (#53), W-11a PR-2/PR-4 (#33, #39), W-2 doctor summary (#106), SAFE-CHAT (#44), SAFE-INTERP (#48), DDI (#41), P5 UTC sweep (#93, #95), F-10 (#68). Every `main@40f590e` line number and figure below is a lead, not a finding: Task 1 re-measures it, and Task 2 re-runs each ledger command before a verdict lands.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make everything a stakeholder sees at the CS4610 showcase — the report outline, a refreshed showcase page, a 10-minute live demo, and the coursework scope note — say only what the claims ledger backs, with each claim's scope stated.

**Architecture:** DOCS work plus a rehearsed demo. No product code changes. The claims ledger gains rows first (§3). Every other artifact is then checked against the ledger: the outline (§4), the figures (§5), a new dated showcase copy with a machine check (§7), the coursework scope note (§8), and the demo (§6). A dated claim freeze (§10) runs last.

**Tech Stack:** Markdown, a static HTML page, `python3 scripts/docs_lint.py`, `scripts/generate_docs_index.py`, git, Windows PowerShell for the demo (`dev.ps1`).

**Prerequisites:** P0-B and P1 merged to `origin/main`. The 2026-09-27 plan set (this file included) committed on main through an owner-approved docs commit. P0-B's approved text covers only `audit/`, `docs/capstone-report/` and `docs/INDEX.md`, not `docs/plans/`. Plan-specific: W-1 Task 6 merged before Task 5 (it owns `CS4610_Report_Demo/README.md:20-23`). If Task 0's ancestry check fails before P1 lands, that is the intended STOP, not a defect.

**Ref labels.** `main@40f590e` = main at the planning date. `B@7b2ff1f` = `origin/claude/healthcentral-agentic-research-r1n54x`. `A@692fdf3` = `origin/claude/asclexis-repo-audit-349pjq`. `showcase:N` = line N of [`audit/2026-09-25/asclexis-showcase.html`](../../audit/2026-09-25/asclexis-showcase.html) in the working tree on 2026-09-27 (untracked package; P0-B commits it unchanged). `FR` / `TC` = the submitted Final Report / Technical Companion (`CS4610_Report_Demo/*.docx`, text read with `zipfile`, never edited). The executor re-verifies every line number on the post-P1 tree. Task 1 re-measures the figures it lists (counts, authorship, dates, tallies, the security-gate exit code); Task 2 Step 3 re-runs every evidence command in §3.1, and Task 1 Step 9 re-checks the line citations and figures in §5 and §9.1; both record their results in §15. The collected-test figure comes from Task 1's measurement, never from a document (`CLAUDE.md` or this plan).

---

## 1. Approval scope

**No standing owner decision licenses the edits in this plan; each is licensed by its own §13 answer.** It is DOCS work. Every artifact it changes carries an owner sign-off in §13: O-1, O-2, O-5 and O-7 were answered 2026-10-20 (not yet ticked in the table); O-3, O-4 (options A/B) and O-6 are still open. The repo rules it follows, verbatim from [capstone README](../capstone-report/README.md) "Maintenance rules":

> 1. "**Claims go through the ledger.** Before a claim appears in the report, it gets a claims-ledger row with evidence. Audit-sourced items are `REPORTED` until re-verified. They do not inherit the audit's verdict."
> 6. "Corrections to submitted coursework (`CS4610_Report_Demo/*.docx`) live as scope notes in `CS4610_Report_Demo/README.md`, never as docx edits."

Owner records the showcase text must respect, verbatim:

- **D10** ([owner decisions](../capstone-report/owner-decisions-2026-09-27.md)): "Design retention/controls as if HIPAA applied (6-year Security Rule documentation, etc.) regardless of legal status." Consequence 5: "Documents must say "designed as if HIPAA applied (owner choice, 2026-09-27)". They must never say "Asclexis is a covered entity" or "is HIPAA-compliant"."
- **D8-delivery** (owner, 2026-09-27 Claude Code chat; recorded in the orchestrator ledger, **not yet** in `owner-decisions-2026-09-27.md` — W-11b finding F-5): "Interim: `src/backend/scripts/download_models.py` fetches it once into a local models dir; runtime loads that path with HF offline and fails closed if absent. Installer bundles it later (G-C4). No weights in git."
- **D11**: "Keep [cite:N] as the validated marker; document [YOUR_RESULTS:N]/[REFERENCE:N] as context labels; remove the contradictory prompt line. … no validator edit."

**Does NOT license:**

1. Any edit to `CS4610_Report_Demo/*.docx` or `*.pdf`. STOP.
2. Any product code, config, CI or schema change. Demo-machine settings (§6.3) live in an untracked local `.env` and need sign-off O-3.
3. Editing `audit/2026-09-25/asclexis-showcase.html`. It stays byte-identical (§7.1).
4. Editing any claims-ledger row other than the appended rows (§3.1) and the M1 evidence cell (§3.2). W-1 owns H5/H6, W-8 owns C10, W-11a owns H2.
5. Upgrading any verdict without the command output that shows it.
6. Any legal or HIPAA-compliance statement beyond D10's wording.
7. Using real patient data anywhere: demo, screenshots, rehearsal.
8. Packaging the review transcripts into the repo without sign-off O-4.

## 2. Traceability

| Kind | ID | Where (verified by grep 2026-09-27) | Used for |
|---|---|---|---|
| Contract | C-LOCAL-1 · BINDING | [contract](../capstone-report/architecture-engineering-contract.md) `:25-26` "Product code MUST NOT make network calls" | demo runs offline (§6) |
| Contract | C-LOCAL-2 · PROPOSED | contract `:44-45` "The embedding model MUST load from a local path or cache and MUST NOT download implicitly at query time" | C12, demo embedding check |
| Contract | C-REDACT-3 · PROPOSED | contract `:196-197` "Logs and audit rows MUST NOT contain PHI" | C15, demo console rule |
| Contract | C-GATE-2 · BINDING | contract `:353-354` "A CI gate MUST fail closed" | H4 upgrade after P1 |
| Contract | C-GATE-3 · BINDING | contract `:360-361` explicit pathspecs | §14 |
| Contract | C-GATE-4 · BINDING | contract `:367-368` docs lint, DOC-011 reachability | Task 3, Task 10 |
| Matrix | scorecard | [matrix](../capstone-report/specs-compliance-matrix.md) `:33` "73 requirement rows: 4 enforced …" (recounted by script 2026-09-28: 73 rows, 4 enforced, 18 tested, 4 implemented, 15 partial, 20 gap, 9 contradicted, 2 owner-gated, 1 unknown; was 62 on 2026-09-27) | M4 |
| Matrix | PRIV-01, PRIV-04, PRIV-05, PRIV-06, PRIV-08, ISO-01, ISO-04, LOCAL-02, LOCAL-03, LOCAL-04, LOCAL-05, KEY-01, KEY-07, SAFE-03, SAFE-04, SAFE-09, AUD-01, AUD-02, GATE-01, GATE-10 | matrix `:39-144` | evidence for new ledger rows |
| Outline | §1–§10 + figures | [report-outline.md](../capstone-report/report-outline.md) `:9-83` | §4 |
| Ledger | C1–C10, H1–H11, M1–M3 (24 rows) | [claims-ledger.md](../capstone-report/claims-ledger.md) `:26-59` | §3, §9 |
| Overview | §2 diagram, §5–§9 | [architecture-overview.md](../capstone-report/architecture-overview.md) `:25-150` | §5 |

## 3. Claims ledger: rows to add first

Rule: a claim with no row, or whose row is `REPORTED` / `HYPOTHESIS` / `NOT-EVIDENCED` / `CONTRADICTED` / `PENDING`, is dropped or rewritten (§9). `CONTRADICTED` and `NOT-EVIDENCED` rows appear only as findings. `CASE-STUDY` rows appear only as examples. The ledger edit itself is Task 2.

### 3.1 New rows (append; confirm the IDs are still free at Task 2)

All evidence was checked on 2026-09-27 at `main@40f590e` unless a ref says otherwise. Task 2 re-runs each command on the post-P1 tree and updates line numbers.

**Product claims — append after C10:**

| # | Claim | Evidence | Verdict |
|---|---|---|---|
| C11 *(new)* | Export artifacts live in process memory and are lost on restart | Module-level dicts `_summary_store`, `_packet_store`, `_fhir_store` at `api/export.py:44,47,50`; `api/pinboards.py:13,495` imports and writes `_packet_store`. The restart 404 is from code reading; W-11b plans the runtime test (G-C1). | `VERIFIED` (code path) · runtime 404 not executed |
| C12 *(new)* | The embedding model is fetched from Hugging Face implicitly on first use | `SentenceTransformer(self.config.model_name)` at `modules/embeddings.py:56`, no offline flag; on load failure the module silently switches to hash-fallback vectors (`:58-69,107`). CI installs no model: `grep -ciE 'sentence\|huggingface\|download_models\|HF_HOME\|all-MiniLM' .github/workflows/ci.yml` → 0 on main and B, so `CLAUDE.md:30` "installed (CI)" really means "fetched at test time". Sub-claim: the 2026-09-27 Wave-0 suite run triggered such a fetch — inferred from two file timestamps (HF cache `refs/main` 17:05:28 vs run output 17:05:46, orchestrator ledger), not captured on the wire. | `VERIFIED` (code path, CI config) · Wave-0 fetch: `HYPOTHESIS` |
| C13 *(new)* | The five core flows are implemented and reachable | Re-traced in code: document flow (overview §5: `api/documents.py:400` → `:567`/`:708` → observations `user_verified=False` `:655,757` → chunks + embeddings `:849-850` → classification `:928`, LLM assist `:983`; dedup `modules/ingest.py:6,46-49`; synonyms `modules/normalize.py`, `modules/glossary.py`; FAISS removed in `09f6056`, 2026-07-01) and assistant flow (overview §6). Backup and deletion: code read (overview §3–§4). Record intelligence and feedback→RL: audit §6 only. OCR runs only when Tesseract is installed (`dev.ps1:606` sets `OCR_ENABLED`). | `PARTIAL` — 2 of 5 flows re-traced, lifecycle code-read, 2 `REPORTED` |
| C14 *(new)* | The default agent path makes no LLM call | Agent default ON (`modules/agent/settings.py:19`; B@7b2ff1f `AGENT_ENABLED_DEFAULT = True`). `git grep -nE 'model_runner\|ModelRunner\|core\.llm\|llama_cpp\|external_runner\|httpx' -- src/backend/modules/agent` → 2 hits on main and B, both docstring lines (`guardrails/redaction_gate.py:15-16` at B). Draft is template composition (`nodes/draft.py:1-31`). `validate_response` has one caller, the legacy path (`modules/rag.py:1271`). 8 read-only tools (`tools/registry.py:42-67`), `MAX_STEPS = 5` (`state.py:19`). If the agent raises, the legacy path runs (`api/assistant.py:745-751`); with no model it returns the knowledge fallback (`:847,1224`; matrix SAFE-09 tested). | `VERIFIED` |
| C15 *(new)* | The default dev configuration echoes SQL with bound values (PHI) to stderr | `debug: bool = True` (`core/config.py:28`); `config/.env.example:14` `DEBUG=true`; `dev.ps1:573` writes `DEBUG=true`; `echo=settings.debug` on the master engine (`core/database.py:46`) and every vault engine (`core/profile_database.py:308`). `dev.ps1:718-721` starts the backend with `-WindowStyle Hidden`, so the echo goes to a hidden console, not a file. Values seen leaking (display name, bcrypt hash, analyte values, chat text): S-1 scratch probe on B@7b2ff1f, Windows Py 3.13.7, SQLCipher absent ([S-1 plan](2026-09-27-S01-sql-echo-phi-leak.md) fact 7); the probe files are not in the repo. Fix gated on S1-A/S1-B (unsigned). | `VERIFIED` (config + code) · leaked values: `REPORTED` until S-1 Task 1 re-measures — finding only |
| C16 *(new)* | Vaults are SQLCipher-encrypted | `core/profile_database.py:315-356` keys SQLCipher when present. The Windows launcher falls back to **no** SQLCipher when the `sqlcipher3-binary` install fails (`dev.ps1:473-487`) and rewrites `DATABASE_ENCRYPTION_REQUIRED=false` (`dev.ps1:583-591`). Windows Py 3.13.7: `import sqlcipher3` → `ModuleNotFoundError` (2026-09-27). The backend suite runs unencrypted (`tests/conftest.py:57`). | `PARTIAL` — encrypted where SQLCipher is installed (CI, Linux); a Windows dev install can run plain SQLite |
| C17 *(new)* | Backups are unredacted by design, restore is profile-scoped, and each archive carries a plaintext master copy | Unredacted by design: `docs/compliance/data-privacy.md:173-178` (matrix PRIV-05). Restore needs password + `RESTORE MY DATA` (`api/backup.py:54`); HTTP-tested profile scoping (`tests/test_backup_routes.py`, matrix ISO-04). The archive includes a plain-SQLite master copy reduced to this profile: display name, password hash, audit rows (`scripts/backup.py:199-205,243-251`). | `VERIFIED` (code path) |
| C18 *(new)* | The master DB is unencrypted and holds names, password hashes and audit rows | `sqlite+aiosqlite` URL (`core/config.py:180-184`); `profiles.display_name`, `password_hash`, `password_salt` (`models/profile.py:47,53-54`); `audit_logs`, `backup_schedules`, knowledge base (overview §4). | `VERIFIED` |
| C19 *(new)* | Audit logging covers document, observation and most profile routes; a profile's audit rows are purged when it is deleted | Documents 13/13, observations 6/6 (matrix AUD-01, HTTP test `tests/test_observations_audit.py`); profiles 9/13 (AUD-02). Delete purges `AuditLog` rows for the profile (`api/profiles.py:909`) before writing the anonymized tombstone (`:925-928`). The log is therefore not append-only. | `PARTIAL` — coverage gap on 4 profile routes |
| C20 *(new)* | `POST /export/questions` returns `source_quote` unredacted; neither branch fixes it | `api/export.py:115,126` (and `:192,1114`). `git diff --stat main A@692fdf3 -- src/backend` → only `api/documents.py` + its test; B changes no `api/export.py`. A's `45ac889` clears care-task quotes on document delete, a different defect (matrix PRIV-07). | `VERIFIED` — finding only |
| C21 *(new)* | Documents are AES-GCM encrypted with the profile key and a per-document IV | `DocumentEncryption` "per-document IVs", 12-byte IV, 32-byte key (`core/security.py:443-466`); the key is the profile's key (`core/document_crypto.py:19-36`). Not per-document keys. Matrix KEY-07 tested. | `VERIFIED` |
| C22 *(new)* | `consistency_score` is a 1.0 placeholder | `consistency_score = 1.0  # Default to 1.0 if not checking consistency` (`modules/faithfulness.py:134`). HC-M11 NLI cross-encoder: approved for build behind a default-off flag only; the production scoring change is owner-gated (matrix GATED-05; branch A §14 d2). | `VERIFIED` |
| C23 *(new)* | Memory and session history are labelled non-citable | Legacy prompt: "SESSION HISTORY (do NOT cite these turns — for context only)" (`modules/rag.py:672`); "USER PREFERENCES (from memory store — do NOT cite" (`:1090`). | `VERIFIED` (prompt text; model compliance not measured) |
| C24 *(new)* | Strict redaction runs on the feedback (RL) export, after explicit confirmation, and on the FHIR, visit-prep and pinboard exports | RL: `api/feedback.py:306,384` → `modules/rl_dataset.py:105-215`, `tests/test_rl_feedback.py` (matrix PRIV-01). FHIR: `modules/fhir_export.py:50-65`, HC-FHIR-080…082 (PRIV-02). Visit-prep/pinboard: `modules/export.py:533,637-642`, `api/pinboards.py:382`, HC-PKT-008/-016 (PRIV-03). Not the CSV, JSON or doctor-summary exports (C9). | `VERIFIED` (tested) |
| C25 *(new)* | Profile data is read only through `ProfileDbSession`, never the master session | `core/auth.py:313-339`; 2026-09-27 scan (matrix ISO-01, tested; HTTP tests only for backup routes). | `VERIFIED` (tested; most route tests direct-call) |
| C26 *(new)* | The Ollama provider refuses non-local URLs | `_assert_localhost` in `core/llm/ollama_provider.py` (called in `__init__`), `api/model_settings.py:806`; default `127.0.0.1:11434`. `settings.ollama_base_url` is not passed by the factory (`core/llm/factory.py:51`). Tests `TestOllamaProvider::test_refuses_non_local_url`, `::test_accepts_localhost` (matrix LOCAL-02). | `VERIFIED` (enforced in code, not config) |
| C27 *(new)* | GGUF models arrive through an explicit download step; the app boots without one | `src/backend/scripts/download_models.py` (18 `ollama` references; the root `scripts/download_models.py` has 0 — recurring-failures #6); llama-cpp imported lazily (overview §3). | `VERIFIED` |
| C28 *(new)* | The legacy path serves answers that fail validation | Faithfulness < 0.6 sets `is_valid=False` (`modules/rag.py:861-870`) but the answer is returned (`api/assistant.py:772-811`), flagged only in the payload (matrix SAFE-04). W-4 plans abstention (OQ-1 unsigned). | `VERIFIED` — finding only |
| C29 *(new)* | Auth uses bcrypt password hashes, JWT HS256 and token revocation | `ALGORITHM = "HS256"` (`core/security.py:38,144,150`); `$2b$` hashes (S-1 probe, REPORTED) and `password_hash` column (`models/profile.py:53`); `core/token_revocation.py` (overview §3). | `VERIFIED` (HS256, revocation module, hash column) |
| C30 *(new)* | In local mode the backend binds 127.0.0.1 with a localhost-only CORS list | `dev.ps1:719` `--host 127.0.0.1`; `src/backend/main.py:164-171` for `python main.py`; CORS `main.py:101-103,141-146` (matrix LOCAL-05, no test). | `VERIFIED` (code; untested) |

**Harness / research claims — append after H11:**

| # | Claim | Evidence | Verdict |
|---|---|---|---|
| H12 *(new)* | Per-era authorship figures | Command (§11 Task 1 step 4) over `git log <SHA> --format='%H\|%ad\|%an\|%(trailers:key=Co-Authored-By,valueonly,separator=;)' --date=format:%Y-%m-%d`. At `40f590e`, author name `Claude` / commits: E0 (2025-12) 0/2; E1 (Jan–Feb) 0/62, **27/62 carry a Claude co-author trailer**; E2 (Mar–May) 0/34 (1 co-author); E3 (Jun 11–13) **0/9**; E4 (Jun 23–Jul 31) 222/230; E5 (Aug 1–4) 17/17; E6 (Sep) 0/1. From 2026-06-23: 239/248. The showcase's E3 "30%", E4 "55% of all history" (measured 230/355), E5 "90%" and E6 "95%" are not reproducible by either proxy. | `VERIFIED` (measured values) · showcase era percentages: `CONTRADICTED` |
| H13 *(new)* | Order in which harness layers were first committed | `git log <SHA> --diff-filter=A --format='%ad %h' --date=short -- <path> \| tail -1`: `scripts/docs_lint.py` 2026-02-12 `e1c1b29`; `scripts/security_gate.py` 2026-02-22 `ae2e9ea`; `CLAUDE.md`/`AGENT.md` 2026-06-13 `ee8bd33`; `skills/` 2026-06-23 `caacd93`; `scripts/agent_eval_gate.py` 2026-06-24 `1571927`; `.claude/skills/` 2026-07-01 `9169c3e`; `feature_list.json` 2026-07-07 `ddad453`; `tests/support/routes.py` 2026-07-30 `7c90afd`; `docs/agentic/recurring-failures.md` 2026-08-04 `7e985e6`. First `Claude`-authored commit: 2026-06-23 `caacd93`. Outline §4's order "constitution → skills → ledger → gates → memory" is wrong for gates: two gates predate the constitution. | `VERIFIED` · outline order: `CONTRADICTED` |
| H14 *(new)* | Repository inventory counts | At `40f590e`: 18 routers (`grep -c include_router src/backend/api/__init__.py`); 16 pages (`ls src/frontend/src/pages/*.tsx`); 14 process + 4 domain skills (`ls -d .claude/skills/*/ skills/*/`); 74 golden cases (`ls src/backend/tests/agent/golden/*.json`); **27** `feature_list.json` features (18 completed, 8 pending, 1 in progress; A and B also 27); 13 numbered docs-lint rules (matrix GATE-01); 6 CI jobs (overview §11). Re-measured at the freeze SHA. | `VERIFIED` (at the SHA named) |
| H15 *(new)* | Stale docstrings and repo hygiene items | `modules/agent/__init__.py:3` "SCAFFOLD ONLY" beside a default-ON agent; `api/__init__.py:2` "API routes for HealthCentral backend"; two `download_models.py` (root and `src/backend/scripts/`); `.vite/deps/*` tracked; Office lock files tracked on main and deleted by B@7b2ff1f (gone after P1). P4 owns the docstring fixes (OG-5). | `VERIFIED` — finding only |
| H16 *(new)* | The coursework's analyte-synonym Skill exists | `git grep -il 'analyte' <ref> -- '*SKILL.md'` → 0 on main, A and B; no ingestion/analyte skill name in `git log --all --name-only` SKILL.md paths; skills present: 14 process + `skills/asclexis-{agent,backend,evals,guardrails}`. The synonym map is code (`modules/normalize.py`, `modules/glossary.py`). | `NOT-EVIDENCED` — finding only |
| H17 *(new)* | Route tests go through real HTTP via `route_client` | `tests/support/routes.py` added 2026-07-30 (`7c90afd`); CLAUDE.md §4 requires it for auth/scoping/status tests. Still direct-call: profile deletion HC-PDEL-001…018 (ledger C5), recovery tests (matrix KEY-03), no HTTP test for `require_profile_access` in `api/profiles.py` (matrix ISO-02 gap). | `PARTIAL` — exists and required; many route tests still direct-call |
| H18 *(new)* | Documented July 2026 backup incidents under a green suite | `842bc49` (2026-07-30) "fix(backup): make the restore endpoint reachable"; `565f708` (2026-07-30) "fix(backup): stop the download carrying other profiles' credentials"; `c4ef941` (2026-07-31) scope the master DB at creation. 12 `fix(backup)` commits 2026-07-29…31 (`git log --grep='fix(backup)'`). Narrative: `recurring-failures.md` #1 (`:17-31`). | `VERIFIED` (commits + documented narrative) |

**Methodology claims — append after M3:**

| # | Claim | Evidence | Verdict |
|---|---|---|---|
| M4 *(new)* | Only 4 of 73 requirement rows are `enforced` | Script count over matrix rows `^\| (LOCAL\|ISO\|KEY\|SAFE\|PRIV\|LLM\|AUD\|TIME\|MIG\|PROD\|GATE)-\d\d` by bold Status cell (2026-09-28, after Wave 6): 73 rows (62 on 2026-09-27); 4 enforced (SAFE-03, SAFE-05, GATE-01, GATE-10). Re-count at the freeze. | `VERIFIED` (at the matrix date) |
| M5 *(new)* | The audit rated harness maturity "L3 structured, trending L4" | Audit §14 table and verdict (`audit/2026-09-25/Devin-Audit-report.md:224-241`). A qualitative rubric by the auditing agents; not a measurement; some cells rest on evidence later contradicted (e.g. "HTTP-level route tests", H17). | `VERIFIED` as a statement of what the audit says · the rating itself: judgment |
| M6 *(new)* | 2026-09-27 reconciliation: multi-agent planning with adversarial review | One author agent per work item wrote 14 plans (P04, P08, S01, W01–W08, W10, W11a, W11b) from a shared brief. Each plan was reviewed read-only by Codex (effort high, one retry; exit 42 hands the review to an Opus reviewer). Owner allowed a 4th round for W-1, W-2, W-3, W-4, W-8, P04, P08, W-10, W-11a, W-11b (no 5th). Snapshot of `reviewer-log.tsv` 2026-09-27T21:02-07:00: 51 logged rounds (50 for the 14 plans + 1 routine spec); per plan P04 4, P08 4, S01 3, W01 4, W02 4, W03 4, W04 4, W05 2, W06 3, W07 2, W08 4, W10 4, W11a 4, W11b 4; reviewer `codex` on all 51; 0 fallback rows. Source files live in the session scratchpad and are not in the repo unless sign-off O-4 packages them. | `CASE-STUDY` — counts only (SHOW-O4 option B, 2026-10-20; the log is packaged under `docs/reviews/2026-09-27-swarm/`) |
| M7 *(new)* | Plan authors caught errors in the orchestrator's own notes | The orchestrator's Wave-0 brief said the proposed test-ID prefixes had "zero" hits and needed only a collision check. Authors found substring collisions: `HC-VER` ⊂ `HC-VERIFY-00x` (`git grep -c HC-VERIFY B@7b2ff1f -- src/backend/tests` → 1 file); `HC-CIT` ⊂ `HC-CITE` (main → 1 file). | `CASE-STUDY` (the matches are `VERIFIED`) |
| M8 *(new)* | The Wave-0 full-suite run and its environment | Windows Python 3.13.7, main@40f590e, dirty tree: 1245 collected, 4 failed / 1241 passed (`test_s4_2_offline_loop_completes`, `test_hc_bkup_039`, `test_hc_bkup_039b`, `test_docs_index_check_passes_on_real_repo`). No `sqlcipher3` in that interpreter, so vaults ran unencrypted. A recurring-failures #4 instance: an environment-dependent result. | `VERIFIED` as a record of that run (orchestrator ledger) · not a baseline |

### 3.2 Existing row edit (M1 evidence cell only)

Append to M1's evidence cell: "The follow-up also records the orchestrator writing a matrix scorecard before counting rows; a script count replaced it (`audit/2026-09-25/review/2026-09-27-followup.md` N-13, `:73`). The review was accurate on 16 of 17 findings (`:125`)." The verdict stays `CASE-STUDY`.

## 4. Report outline: section by section

Status after this plan assumes Tasks 2–7 ran. A 🔶 names what it still waits for.

| § | Now | What changes for the showcase | Evidence | Status after |
|---|---|---|---|---|
| 1 Introduction | ✅ | `:13` "working product" → "a locally run product (dev launcher; no installer yet)". Motivation lines stay (author statements, no statistics). | C8, C13, [00-original-goal](../capstone-report/00-original-goal.md) | ✅ |
| 2 System description | ✅ / 🔶 figures | `:18` add "SQLCipher where installed (C16)". `:19` five flows scoped "2 re-traced, lifecycle code-read, 2 reported (C13)". `:20` point figures at the new dated copy (§7), not the 2026-09-25 page. `:22` cite C14. | C13, C14, C16, overview §1–§9 | ✅ |
| 3 Safety & privacy | ✅ | `:26` scope each item: agent guard vs legacy `validate_response` (C14), legacy serves invalid answers (C28), redaction default + dev bypass (C10; W-6). `:29` must-owns: mark `faithfulness_score=1.0` "fixed by P1 (`cc202d9`), re-verified <date>" only after Task 1 measures it; add C12, C15, C16, C17, C19, C20. CSV/JSON wording becomes "named exceptions (D3)" only after W-10 merges. | C3, C9, C10, C12, C14–C20, C22, C28 | ✅ |
| 4 Methodology | 🔶 (figure) | `:33` era figure uses H12's measured values and states the method (author name; co-author trailers counted beside it). `:34` layer order replaced by H13's dated sequence: "gates (docs lint, security gate: 2026-02) → constitution (2026-06-13) → skills (2026-06-23) → eval gate (2026-06-24) → task ledger (2026-07-07) → `route_client` (2026-07-30) → failure memory (2026-08-04)". `:35` evidence → H1, H12, H13 commands. | H1, H12, H13 | ✅ |
| 5 Harness in depth | ✅ | `:39` "18 skills" (H14); `route_client` "required, but many route tests still direct-call" (H17); `feature_list.json` 27 items (H14). | H7, H14, H17 | ✅ |
| 6 Evaluation | ✅ | `:44` replace "July backup storm" with H18's commits ("12 `fix(backup)` commits, 2026-07-29…31"). `:45` fail-open gate: "fixed in P1; exit 2 on a missing report, measured <date>" after Task 1. `:46` phantom layer: after W-1, "absent when claimed; five definitions authored new by owner decision D1 on <date>". `:47` M1 as amended (§3.2). | H4, H5, H18, M1 | ✅ (🔶 until W-1 merges for `:46`) |
| **6a (new)** 2026-09-27 reconciliation | — | New section, exact text in §4.1. | M6, M7, M8, C12, C15 | ✅ inserted (O-5 answered 2026-10-20); M6 is `CASE-STUDY` since SHOW-O4 (B) was answered 2026-10-20 and the log is packaged (Task 8) |
| 7 Related work | ✅ | No change. | research/ | ✅ |
| 8 Limitations | ✅ | Add: "Local results depend on environment: the Windows interpreter used on 2026-09-27 had no SQLCipher, so its suite run used unencrypted vaults (M8, C16); pass counts are named with their environment." | M8, C16 | ✅ |
| 9 Roadmap | ✅ | `:63` add the 2026-09-27 plan set (14 plans + S-1 finding) with status **PROPOSED — not executed**, and name owner-gated items (§10 item 6). | [program](../capstone-report/implementation-program.md), plan files | ✅ |
| 10 Conclusion | 🔶 | `:69` cite M5; keep "auditor's qualitative rubric, not a measurement". | M5 | ✅ |
| Figures inventory | 🔶 ×6 | Rows `:75-80` point to the new dated copy with each figure's decision from §5; add a "Demo script" row pointing to this plan §6. | §5 | ✅ for kept/fixed, rows for dropped figures removed |

### 4.1 Exact text for the new outline section 6a

Insert after `report-outline.md:47` (the end of §6):

```markdown
## 6a. Case study — the 2026-09-27 reconciliation

- What ran: the orchestrator re-checked the package against main @ `40f590e` and recorded owner decisions D1–D13. It then dispatched one author agent per work item: 14 plans in `docs/plans/2026-09-27-*.md`. Each plan was reviewed read-only by Codex in rounds. An Opus reviewer was configured as the fallback when Codex was unavailable.
- Counts (claims-ledger M6, snapshot time stated there): review rounds per plan and fallback events. Counts only.
- Examples of errors found in these runs: plan authors caught two wrong test-ID notes in the orchestrator's own brief (M7); a security review found SQL echo of bound values in the default dev configuration (C15); a plan author found that CI installs no embedding model, so a "CI has the model" baseline actually depends on an implicit download (C12); the orchestrator's own Wave-0 suite run used unencrypted vaults (M8).
- Verdict: `CASE-STUDY`. Review found errors in these runs. There is no capture rate, cost or causal claim: no seeded errors, no single-agent comparison, no count of errors present, and no token or time accounting.
- Evidence: claims-ledger M6–M8, C12, C15.
```

## 5. Figures: re-check against the architecture overview

Checks run 2026-09-27: middleware order in overview §2 matches `src/backend/main.py:104-142` ("last added = outermost": CORS → CorrelationId → SecurityHeaders → RateLimit → InputValidation → SecurityAudit → Timing); B does not change `main.py`. External-runner call sites: `api/assistant.py:697-698` and `api/interpretations.py:436-438`. Agent path makes no LLM call (C14).

| # | Figure | Location | Check | Decision | Exact change |
|---|---|---|---|---|---|
| F1 | Hero stat tiles | showcase:195, :431-435 | "155 vitest", "25 e2e" are `PENDING` (H2); "~50 feature modules" has no row (measured 45 top-level, 72 total); others H14/H1/H3 | **fix** | Tiles: `{COLLECTED} backend tests collected`, `{ROUTERS} API routers`, `{PAGES} frontend pages`, `{SKILLS} agent skills`, `74 golden eval cases (agent path)`, `{CI_JOBS} CI jobs`, `{H1_TOTAL} commits · {H1_PCT}% agent git author`. Vitest/e2e tiles only if W-11a (G-B6) merged, with its listed counts. Drop "~50 feature modules". |
| F2 | Patient-journey stepper | showcase:204-205, :437-458 | Trends "all verified imports" contradicts C2; citation tags contradict D11/C3 | **fix** | Rows J1–J5 in §9.1. Render statically (no JS data arrays). |
| F3 | Document → observation pipeline | showcase:212-213, :460-485 | Order wrong: observations are stored unverified (`:655,757`) **before** chunk/embed (`:849-850`) and classify (`:928`); "Store" is shown after classify. The embedding node hides the implicit HF fetch. `core/audit.py` is helpers, not middleware. `modules/ingest/` is a file. | **fix** | Nodes: Upload (`api/documents.py:400`, AES-GCM file, audit helper) → Ingest (`modules/ingest.py`, dedup, FHIR structured path `:708`) → Extract + normalize (`modules/extract*.py`, `normalize.py`, `glossary.py`; OCR when Tesseract installed) → **Observations stored, unverified** (vault via `ProfileDbSession`) → Chunk + embed (dashed edge "first use: model fetch from huggingface.co" until W-8; after W-8 "explicit download, offline load") → Classify (`:928`, optional LLM assist `:983`) → Human verification (Workbench). |
| F4 | Provider cards + GGUF tier cards | showcase:220-228, :487-494 | "one facade, three providers" wrong: the external runner is outside ModelRunner (H11, overview §2); tier cards unevidenced | **fix** providers, **drop** tier cards | A box "ModelRunner" containing LlamaCpp (default, lazy) and Ollama (refuses non-local URLs). Outside the box: "External runner — opt-in, off by default" with two callers (assistant, interpretations). One line under it: C27 text (§9.1 S054). |
| F5 | Safety dual-path lane | showcase:239, :496-499, :588-596 | Agent lane shows `validate_response :793` (only caller is `modules/rag.py:1271`); "same validation gauntlet" false; legacy end node says "cited answer or abstain" but invalid answers are served (C28) | **fix** | Agent lane: CHAT → PLAN → ACT (8 read-only tools, ≤5 steps) → REFLECT → DRAFT (deterministic template, no LLM call) → GUARD (groundedness + advice classifier) → "sourced answer or abstention". Legacy lane (runs when the agent flag is off or the agent raises): CHAT → RETRIEVE (observations incl. unverified until W-3; knowledge base) → COMPOSE (history + memory, labelled do-not-cite) → RUN (ModelRunner) → VALIDATE (`validate_response`) → "answer served; `is_valid` flag in payload" (after W-4: "abstention template when `is_valid=False`"). Side note: "no model installed → knowledge-base fallback". |
| F6 | Vault architecture | showcase:262-281 | "no PHI", "metadata only", "append-only" contradicted (C18, C19); vault badge overstates (C16); backup master copy missing (C17) | **fix** | Master card badge "unencrypted"; items per §9.1 S086–S093. Vault badge "SQLCipher where installed · sealed key". Add a third card "Backup archive: vault + sealed keys + plaintext master copy of this profile (by design, unredacted)". |
| F7 | Crypto-erase steps | showcase:283-288 | Step 1 "data unreadable from this instant" overclaims: backups still hold key copies until step 3 | **fix** | Step 1: "Unlink the sealed key files first". Steps 2–4 unchanged (C5, C19). |
| F8 | Maturity bars (12 capabilities) | showcase:305-306, :501-505, :598-600 | A judgment drawn as a measurement (M5) | **drop** | One sentence instead: §9.1 S109. |
| F9 | Enforcement-layer cards | showcase:308-317 | Dots overstate: `route_client` (H17), security gate (H4), feature count 24 → 27 (H14) | **fix** | Texts per §9.1 S111–S118. Dots: green = a CI gate that fails on violation and is measured (docs lint, feature-list lint, agent evals; security gate only after Task 1 measures exit 2); amber = partial (`route_client`); grey = memory/docs. |
| F10 | "Recurring failure modes" cards | showcase:318-319, :507-516, :603-604 | The 8 cards are the audit's taxonomy, not the file's 8 modes; "Contaminated-tree gate" is mis-described (the security gate belongs to mode 1) | **fix** | Replace with the 8 headings of `docs/agentic/recurring-failures.md` (`:17,39,58,75,92,105,123,134`), each with one sentence quoted from that entry. Title: "Recorded failure modes (docs/agentic/recurring-failures.md)". |
| F11 | Era timeline | showcase:326, :518-526, :607-610 | E3/E4/E5/E6 figures not reproducible (H12) | **fix** | Bars = measured author-name share per era at `{SHA}`; each card shows "{agent}/{n} by author · {co}/{n} with co-author trailer". Caption: "Git author name is a proxy, not a measure of who did the work." |
| F12 | Lifetime authorship bar | showcase:328-329 | 239/355 correct at `40f590e` (H1); "8 model variants" no row | **fix** | Re-measured at `{SHA}`; drop "8 model variants". |
| F13 | Findings table | showcase:348-354, :528-541, :613-621 | 3 rows false or stale (S154, S159, S162); 2 rows without ledger rows | **fix** | Rows per §9.1 S151–S162; add finding rows for C12, C15, C16, C17, C20 (findings only). |
| F14 | Workstreams table | showcase:356-367 | "owner-approved order" superseded by the program; D1 decided | **fix** | Replace with program phases (P1…P8, G-A…G-C) and the 2026-09-27 plan set, each "PROPOSED — not executed" unless merged, owner-gated items named. |
| F15 | Delivery pipeline (capstone track) | showcase:375-386 | "READY"/"pending" stale; agent counts `REPORTED` | **fix** | Nodes per §9.1 S166–S170. |
| F16 | Ledger snapshot chips | showcase:395-401 | "11 verified / 1 partial / 6 contradicted / 2 not-evidenced" (20) vs 24 rows today (6 VERIFIED incl. H2 mixed, 6 PARTIAL, 7 CONTRADICTED, 2 NOT-EVIDENCED, 2 CASE-STUDY, 1 HYPOTHESIS) | **fix** | Generated by Task 1 Step 6's script at the freeze; never hand-typed. |
| F17 | Plan-files table | showcase:407-418 | Line counts stale (banners added); "corrected the audit on" items are `REPORTED` | **drop** | — |
| F18 | Implementation-program dependency graph | [program](../capstone-report/implementation-program.md) `:45-128` | Accurate for the program; since Wave 6 (d430fb7) it draws S-1 and the W-plans (every node *proposed*) | **keep** | Caption: "Proposed order; no node is owner-approved." |
| F19 | Integration diagram (current state) | [overview](../capstone-report/architecture-overview.md) `:27-67` | Middleware order ✓; agent path no LLM ✓; network boundary: missing `interpretations → EXT` edge (`api/interpretations.py:436-438`); EXT label "opt-in, redacted" omits the dev bypass (`core/external_runner.py:201`) | **fix** | Task 4: add node/edge `R -. "interpretations (opt-in)" .-> EXT` and relabel `ASST -. "opt-in; strict redaction by default (dev bypass until W-6)" .-> EXT`. After P2: add the notification scheduler to LIFE. After W-8: relabel `ST -. "HTTPS model fetch"` to "explicit download (D8-delivery); offline load". |
| F20 | Compliance scorecard | [matrix](../capstone-report/specs-compliance-matrix.md) `:31` | Recounted: 62 / 4 enforced (M4) | **keep** | — |

## 6. Stakeholder demo (≈10 min, post-P1 tree)

### 6.1 Rules

1. **Synthetic data only.** Fictional patient "Demo Patient", DOB 1970-01-01, MRN "DEMO-0001". Every page of the PDF carries the line "SYNTHETIC — NOT A REAL PATIENT". Write the DOB as "1 January 1970" inside a ruled (grid-line) results table: in the 2026-10-22 dry run a DOB written `1970-01-01` was parsed as the collection date (both files dated 1970-01-01, a duplicate-upload banner), and borderless or plain-line layouts missed CRP; the ruled table with the spelled-out DOB gave 4/4 values per file with the right dates. The files live outside the repo (`C:\Users\DangT\Documents\asclexis-demo\`) and are never committed. No real vault, backup or screenshot of real data is opened, on screen or off.
2. **A fresh clone runs the demo.** Local mode stores data under `src/backend/data` relative to the working directory (`core/config.py:160-164`). A fresh clone at the frozen SHA has no real vaults. Never run the demo from the everyday checkout. Never run pytest in the demo clone: tests that touch the master engine write into `<cwd>/data` (S-1 plan, finding at `:52`).
3. **Show only implemented and wired behaviour.** Each step names its ledger row. Gaps get the fallback lines in §6.4, never a workaround on stage.
4. **Never show a backend console.** `dev.ps1` starts the backend hidden (`dev.ps1:718-721`). Do not start `uvicorn` by hand in a visible terminal. Share one browser window, not the desktop. The optional `DEBUG=false` setting needs sign-off O-3 (§6.3).
5. **Offline on stage.** Wi-Fi off and `HF_HUB_OFFLINE=1` set in the launching PowerShell session, after the embedding cache is warm (§6.3 check 7).
6. **Do not open:** `/docs`, the external-runner (cloud) settings, the doctor-summary export (strict-redacted since W-2, merged #106 2026-10-16; not shown), "reprocess" on a document (W-8 plan found it deletes chunks before re-embedding, `api/documents.py:867-871` A@692fdf3), or citation-chip numbers on the Explain surface (W-5 finding F-3). On the export page, use only the visit-prep packet: the same page has Download CSV/JSON, Generate Summary (doctor summary) and FHIR buttons. Settings is one long page that also holds the External API toggle and the model tiers; scroll only to the card the step names. With `DEBUG=true` (O-3 unanswered) `/docs` and `/openapi.json` are served, so not opening them is presenter discipline, not a setting (dry run 2026-10-22).
7. **Known hazards from the 2026-10-22 dry run (recorded, not fixed).** Right after "Mark All Verified" the Workbench briefly shows a stale "Documents needing attention … parsed" panel; reload the page before moving on. The Workbench tip says "Click any value to edit", but only the pencil ("Edit value") opens the editor. The backend log showed two `database is locked` errors on an `INSERT INTO audit_logs` around Settings page loads; no UI failure was seen and the cause was not investigated. The header shows a model badge (`BioMistral-7B`) on the default assistant path even though no model runs there (`ollama ps` was empty); do not point at it.

### 6.2 Script

| Time | Step | Presenter does | Presenter says | Ledger |
|---|---|---|---|---|
| 0:00 | Frame | Browser on `http://localhost:3000`, Wi-Fi off | "Asclexis runs on this laptop. Everything today is synthetic data. It runs from a developer launcher; there is no installer yet." | C8, C30 |
| 0:45 | Create profile | Create "Demo Patient"; show the one-time recovery code; open Settings → recovery-code card | "Each profile gets its own vault and its own key. The recovery code seals a second copy of that key." | C6 (post-P1), C29 |
| 1:45 | Upload | Upload `demo-labs-2026-03.pdf` and `demo-labs-2026-06.pdf` | "The file is stored AES-GCM encrypted with this profile's key. Extraction produces draft values." | C1, C21, C13 |
| 3:00 | Ask before verifying | Assistant: "What was my most recent HbA1c?" | "Nothing is verified yet, so it declines: it says there isn't enough verified information and that verifying the document will let it explain the values." (dry run 2026-10-22: that text, "0/0 claims verified" and a "Some values are still unverified" banner) | C2, C14 |
| 4:00 | Verify | Verification Workbench: correct one value with the pencil ("Edit value" → "Save & Verify"), then "Mark All Verified"; reload the page (§6.1 rule 7) | "Nothing the AI extracted counts as trusted until you confirm it." | C2, SAFE-01 |
| 5:00 | Trends | Trends dashboard; select the analyte by name (the page opened on CRP with the "CBC 0" tab highlighted) | "Both imports, March and June, on one line per analyte. Each value on this chart is one you just confirmed." (In the scripted order nothing is unverified, so the W-3 unverified markers cannot be shown; the dry run saw them only in a scratch profile. The old before-W-3 line is cut: W-3 merged, #136.) | C2 |
| 5:45 | Ask again | "What was my most recent HbA1c?" → cited answer; then "Should I increase my metformin dose?" | "The default assistant builds answers from templates over your verified data. No language model runs on this path." On the first question: "It lists both verified HbA1c results with their dates, each with a source." (dry run: 5.9 % on Mar 02 and 6.1 % on Jun 01, two source chips, "2/2 claims verified"; it does not pick only the most recent.) On the metformin question: "It declines and refers you to your doctor or pharmacist." (dry run: the default agent path returned the fixed escalation text, not the abstain text.) The legacy path was not exercised in the dry run, so do not describe it on stage. | C14, C4 |
| 7:15 | Export | Visit-prep export | "Exports that go to a third party pass strict redaction." | C24 |
| 8:15 | Delete | Settings → Danger zone → "Delete profile…": either "Back up and download" or tick "I confirm I have a copy, or I don't want one"; enter the profile password; type `DELETE MY HEALTH DATA`; "Permanently delete this profile" (the app returns to `/setup`); show `src\backend\data\vaults\<id>` gone in Explorer | "Deletion unlinks the sealed keys first, then sweeps the vault and backups." | C5, C19 |
| 9:15 | Harness | A **separate** PowerShell window (repo root, not the backend): the security-gate command from §6.3 check 9 | "CI's security gate now fails when a scan report is missing: exit 2." | H4 (post-P1 measured) |
| 9:45 | Close | Open `docs/capstone-report/claims-ledger.md` from the merged showcase PR (#210); until #210 merges, rows C13, C14, C19, C21, C24, C29 and C30 exist only on branch `docs/f-9-showcase-delta`, so open it there, not from `main` | "Each step you saw names a row in this ledger." | — |

### 6.3 Pre-demo checklist (Windows PowerShell; run in full at T-1 day and T-1 hour)

`$D = 'C:\Users\DangT\Documents\GitHub\hc-demo'`. Check `$LASTEXITCODE` after each command whose result matters.

| # | Command | Expected | If not |
|---|---|---|---|
| 1 | `git clone https://github.com/BrooklynD23/HealthCentral $D; git -C $D checkout --detach {SHA}; $LASTEXITCODE` | `0` | STOP |
| 2 | `git -C $D merge-base --is-ancestor 7b2ff1f HEAD; $LASTEXITCODE; git -C $D merge-base --is-ancestor 692fdf3 HEAD; $LASTEXITCODE` | `0` `0` | STOP (pre-P1 tree) |
| 3 | `Test-Path $D\src\backend\data` (before first launch) | `False` | STOP: not a fresh clone |
| 4 | `Set-Location $D; .\dev.ps1` (first run installs venv + npm; network on). Note: `dev.sh` exists since #86 for Linux/macOS/WSL; the Windows demo stays on `dev.ps1` and nothing in this check changes. | browser opens; frontend on :3000 | follow dev.ps1 output |
| 5 | `Set-Location $D\src\backend; .\venv\Scripts\python.exe -c "from main import app; print('app ok', len(app.routes))"; $LASTEXITCODE` | `app ok <N>`, `0` | STOP |
| 6 | `.\venv\Scripts\python.exe -c "import sqlcipher3; print('sqlcipher ok')"` | `sqlcipher ok` → say "encrypted vault" | `ModuleNotFoundError` → vaults are plain SQLite here (C16): use fallback line F-ENC, never say "encrypted vault" |
| 7 | `$env:HF_HUB_OFFLINE='1'; .\venv\Scripts\python.exe -c "from modules.embeddings import EmbeddingsModule as E; e=E(); e._ensure_initialized(); print('model' if e._model is not None else 'hash-fallback')"` | `model` | `hash-fallback` → warm the cache once with network on (pre-W-8: the same command without `HF_HUB_OFFLINE`; post-W-8: W-8's documented fetch command), re-run until `model` |
| 8 | **(O-3 signed only)** `Select-String -Path .env -Pattern '^DEBUG='`, then `.\venv\Scripts\python.exe -c "from core.config import settings; from core.database import engine; print(settings.debug, engine.echo)"` | `DEBUG=false`; `False False` | edit `src\backend\.env` (gitignored, `.gitignore:89`) to `DEBUG=false`; re-run |
| 9 | `Set-Location $D; .\src\backend\venv\Scripts\python.exe scripts\security_gate.py --bandit nonexistent.json --pip-audit nonexistent.json; $LASTEXITCODE` | a line starting `ERROR:`; `2` | drop the harness step |
| 10 | After the dry run: `Get-ChildItem $D\src\backend\data\vaults` | only the synthetic profile IDs recorded in the dry run | STOP: unknown vault present |
| 11 | Dry run of §6.2 with Wi-Fi off, timed | ≤ 11 min; each "expected" recorded in the execution record (§15). 2026-10-22 GPU-box record: PR #210 comment 6334394792 (owner O-6-CHECK8); presenter talk time was not measured there | fix the synthetic PDF layout (never code) or cut the step |

`DEBUG=false` effects (why O-3 is low-risk, still owner-confirmed): it turns off SQL echo on both engines (`core/database.py:46`, `core/profile_database.py:308`), llama-cpp `verbose` (`core/llm/llama_cpp_provider.py:136`), and `/docs`/`/redoc` (`main.py:93-94`). `dev.ps1` passes `--reload` itself (`:719`), so reload is unaffected. No demo step uses `/docs`. **Safe option without O-3:** leave `.env` alone and rely on rule 4 (hidden backend window, browser-only screen share).

### 6.4 Fallback lines (exact)

- **F-INSTALL** (no installer): "Today it runs from a developer launcher. Choosing the packaging route is a planned decision spike (G-C4); nothing is built yet."
- **F-EMB** (embedding model): before W-8: "The small embedding model was fetched into a local cache before the demo. Today the app would fetch it on first use; the approved fix makes that an explicit one-time download that loads offline and fails closed." After W-8: "The embedding model was downloaded once with the model script and loads offline; the app refuses to run retrieval without it. Bundling it into an installer comes later."
- **F-NOTIFY** (dropped 2026-10-20): the line "reminders built but not started" is false since P2 (#31, the session-scoped notification scheduler). No demo step replaces it: the scheduler has not been run on the demo machine, so it is not shown (stop gate 9). If Task 9 runs it and records the result, add it as a §6.2 step with its ledger row (C7); otherwise say nothing about reminders.
- **F-ENC** (no SQLCipher on this laptop): "On this Windows laptop SQLCipher isn't installed, so this vault file is plain SQLite. Uploaded documents are still AES-GCM encrypted. CI runs with SQLCipher."
- **F-EXTRACT** (a value missed): "Extraction missed that one — this is why nothing counts until you verify it." Then switch to the pre-verified synthetic profile "Demo Backup". The app has no profile picker (`/` opens `/setup`), so either keep Demo Backup signed in in a second browser window prepared within the hour before the demo (sessions last 1 hour), or open `/recover`, pick Demo Backup, enter its recovery code (prepared beforehand) and set a new password; that took 5.1 s in the dry run and issues a new recovery code, which replaces the old one.
- **F-AGENT** (unexpected answer): "That came from the fallback path." Move on; do not retry live.

## 7. Showcase HTML refresh

### 7.1 Decision: a new dated copy

Create `docs/capstone-report/asclexis-showcase-{FREEZE_DATE}.html`. Leave `audit/2026-09-25/asclexis-showcase.html` byte-identical. Reasons:

1. The original is a dated artifact of the 2026-09-25 audit package. The follow-up and the review prompt cite it as context (`audit/2026-09-25/review/2026-09-27-followup.md:106`, `handoff-prompt-review-agent.md:81`). The README calls the audit "a dated historical record".
2. Its overclaims are themselves Part-2 evidence for "claims outrun artifacts" (outline §8). Editing it would destroy that evidence.
3. The review ruled the page "Not an audit source" (`Asclexis-Package-Review.md:194`). The report knowledge base (`docs/capstone-report/`) is where report assets live.

The outline, the capstone README and the new copy's footer point to each other. The old page gets no banner (it would stop being byte-identical).

### 7.2 Build rules

1. All claim text is static HTML. JavaScript only shows/hides existing markup (lane toggle, severity filter, stepper). No claim lives in a JS string.
2. Every claim-bearing element (`li`, `td`, `p`, `.stat`, `.gs`, `.et`, `.ed`, `.s`, `.tag`) carries `data-ledger="<IDs>"` or `data-exempt="metadata|pointer|navigation"` on itself or an ancestor. `data-kind="finding"` allows `CONTRADICTED`/`NOT-EVIDENCED`; `data-kind="case-study"` allows `CASE-STUDY`; `data-kind="hypothesis"` allows `HYPOTHESIS`. Default: `VERIFIED` or `PARTIAL` only.
3. Reuse the original CSS. No external requests (the original has 0 `http` strings; keep it that way).
4. Footer: "Claims frozen {FREEZE_DATE} at main @ {SHA} · every claim maps to docs/capstone-report/claims-ledger.md · supersedes the 2026-09-25 showcase (kept unchanged in audit/2026-09-25/)".
5. No HIPAA wording except, if needed, "designed as if HIPAA applied (owner choice, 2026-09-27)".

### 7.3 Change list

The change list is §9.1: each row names its ledger ID and exact text. Task 6 applies it; Task 7 checks it.

## 8. Coursework scope notes (`CS4610_Report_Demo/README.md`)

The file exists only after P1 (B@7b2ff1f). W-1 Task 6 and F-10 (#68) have already rewritten its hook bullet and the `.claude/agents/` bullet; line numbers below are the README at `92cd5d8`/main 2026-10-20 (reconciliation C0b), not B@7b2ff1f. The README's `:13-15` now reads: "No `PreToolUse` hook exists in this repo. The only committed hook (since 2026-10-10, owner HOOKS-COMMIT) is a metadata-only `PostToolUse`/`SessionEnd` session logger (`.claude/hooks/session_log.py`) that scans nothing and blocks nothing." That text is not touched. The pre-F-10 sentence "No hook mechanism and no `.claude/settings.json` exist in this repo at all" is gone, and any new text must not repeat it. Evidence below is from main@40f590e unless a line says otherwise; the README says so.

**Edit 1 — extend the sweep bullet** (README `:30-33` today; the bullet is now four lines, with the "There is no reranker…" evidence sentence after the part quoted here). Replace the first two lines:

```markdown
- **An overnight "Ralph-style" RAG parameter sweep** (chunk size, embedding
  model, reranker on/off) producing a Pareto frontier — Final Report §7.3.
  There is no reranker …
```

(only the `§7.3.` sentence end changes) with:

```markdown
- **An overnight "Ralph-style" RAG parameter sweep** (chunk size, embedding
  model, reranker on/off) producing a Pareto frontier — Final Report §7.3;
  the same campaign is described as a GSD v2 run in Technical Companion §5.6.
  There is no reranker …
```

**Edit 2 — append to the "not evidenced" list** (after the last bullet, before "This list was produced by …"):

```markdown
- **Hook-based secret scanning in this project's harness** — Final Report
  §5.1, §6 (timeline phase 8). Same finding as the AgentShield bullet above:
  no `PreToolUse` secret-scanning hook exists in the repo. The only committed
  hook is the metadata-only `PostToolUse`/`SessionEnd` session logger
  (`.claude/hooks/session_log.py`, F-10 #68), which scans nothing. The
  user-level PreToolUse hooks are continuous-learning and GSD only
  (`docs/capstone-report/claims-ledger.md` H6, whose last sentence about
  `.claude/settings.json` predates #68). The repo's scanner is the CI security
  gate, which failed open on main until branch B's fix was merged (ledger H4).
- **A project Skill holding the analyte-synonym map and unit-conversion rules,
  updated by a Stop hook from earlier corrections** — Final Report §7.2,
  Technical Companion §4.6. No such skill exists on main or either branch
  (`git grep -il analyte -- '*SKILL.md'` returns nothing). The synonym map is
  ordinary code in `src/backend/modules/normalize.py` and `glossary.py`
  (ledger H16).
```

**Edit 3 — new section after the "not evidenced" list** (before "This list was produced by …"):

```markdown
Claims checked against the repo on 2026-09-27 (main @ `40f590e`) and found
**false**:

- **"Every byte of patient data is stored in an AES-256-encrypted SQLCipher
  database with per-document keys and initialization vectors"** — Final
  Report §1; repeated in §3.2. The master database is plain SQLite and holds
  profile display names, password hashes and audit rows
  (`src/backend/core/config.py:180-184`, `models/profile.py:47,53`).
  Documents are AES-GCM files encrypted with the profile's key and a fresh IV
  per document, not per-document keys (`core/security.py:443-466`,
  `core/document_crypto.py:19-36`). On Windows the dev launcher falls back to
  unencrypted vaults when SQLCipher will not install (`dev.ps1:473-487`,
  `:583-591`). Ledger C16, C18, C21.
- **"Even a compromised backup file leaks nothing without the master key"** —
  Final Report §3.2. Each backup archive includes a plain-SQLite copy of the
  master database reduced to that profile: display name, password hash and
  audit rows (`src/backend/scripts/backup.py:199-205,243-251`). Ledger C17.
- **"HealthCentral never uploads patient data … a compromise of the cloud is
  architecturally impossible because there is no cloud"** — Final Report
  §3.3. True by default only. An opt-in, off-by-default assistant path sends
  redacted prompts to OpenAI or Anthropic (`src/backend/core/external_runner.py:261-300`),
  and outside production a setting can switch that redaction off (`:201`);
  owner decision D12 (2026-09-27) approved removing that bypass. Ledger C10.
- **"A local-first desktop application"** — Final Report §3.1. There is no
  desktop shell or installer; the app runs as a local web app started by
  `dev.ps1` (backend on 127.0.0.1:8000, frontend on :3000). Ledger C8, C30.
```

**Edit 4 — new section "Changed since submission":**

```markdown
Changed since submission (accurate or unverified when written; different on
main @ `40f590e`):

- The reports describe the assistant as a local LLM grounded by RAG (Final
  Report §1, §3.2). Since the June–July 2026 agent work, the default assistant
  path composes answers from templates over the patient's verified data and
  makes no LLM call. The LLM path still exists as the fallback when the agent
  is switched off or fails (`src/backend/modules/agent/settings.py:19`,
  `api/assistant.py:745-751`). Ledger C14.
```

**Edit 5 (O-7 answered yes 2026-10-20) — dates:**

```markdown
- The Final Report's cover gives the submission date as May 15th, 2026; its §6
  timeline (row 14) gives Apr 22, 2026. The two disagree; the repo does not
  record which is right.
```

**Edit 6 — closing paragraph** (README `:44-47` today): append one sentence: "The 2026-09-27 additions cite rows in `docs/capstone-report/claims-ledger.md`."

## 9. Claims audit

**Counting rule.** One row = one claim as a reader would quote it. Four rows group repeated pointers or table rows and count once: S022, S164 (8 workstream rows), S176 (8 plan-file rows), S184. Metadata (title, author, course, dates, commit hash) is `data-exempt` and checked, not ledgered. "Pointer" rows are file/route references: kept if the path exists at the freeze SHA.

### 9.1 Showcase (`audit/2026-09-25/asclexis-showcase.html`)

| ID | Where | Claim now | Ledger → verdict | Action | Exact text in the new copy |
|---|---|---|---|---|---|
| S001 | :190 | "CS4610 Senior Project · Danny Tran · Fall 2026" | metadata | KEEP | unchanged |
| S002 | :192 | "A local-first, privacy-first medical results companion" | C10 `PARTIAL` | REWRITE | "A local-first medical results companion: patient data stays on this computer by default (one opt-in cloud path, off by default)" |
| S003 | :193 | "67% of commits agent-authored" | H1 `VERIFIED` (git author) | REWRITE | "{H1_PCT}% of commits have an AI agent as git author ({H1_AGENT}/{H1_TOTAL} at `{SHA}`)" |
| S004 | :193 | "every claim verified" | none; ledger holds PENDING/REPORTED rows | REWRITE | "every claim on this page maps to a row in the claims ledger" |
| S005 | :193 | "every failure remembered" | H7 `CASE-STUDY` | REWRITE | "failure modes are written down (docs/agentic/recurring-failures.md)" |
| S006 | :194 | "main @ 40f590e · audited 2026-09-25" | metadata | REWRITE | "main @ {SHA} · claims frozen {FREEZE_DATE} · first audit 2026-09-25" |
| S007 | :432 | "1,245 backend tests" | H2 `VERIFIED` (collected, at 40f590e) | REWRITE | "{COLLECTED} backend tests collected ({INTERP}, {SHA})" |
| S008 | :432 | "155 vitest specs" | H2 `PENDING` | DROP | (after W-11a: "{VITEST_LISTED} vitest tests listed") |
| S009 | :432 | "25 e2e (playwright)" | H2 `PENDING` | DROP | (after W-11a: "{PW_LISTED} Playwright tests listed") |
| S010 | :433 | "18 API routers" | H14 `VERIFIED` | KEEP | "{ROUTERS} API routers" |
| S011 | :433 | "~50 feature modules" | none (measured 45/72) | DROP | — |
| S012 | :433 | "16 frontend pages" | H14 | KEEP | "{PAGES} frontend pages" |
| S013 | :434 | "18 agent skills" | H14 | KEEP | "{SKILLS} agent skills" |
| S014 | :434 | "74 golden eval cases" | H3 `PARTIAL` | REWRITE | "74 golden eval cases (agent path)" |
| S015 | :434 | "6 CI jobs" | H3/H14 | REWRITE | "{CI_JOBS} CI jobs" |
| S016 | :434 | "355 commits · 67% agent" | H1 | REWRITE | "{H1_TOTAL} commits · {H1_PCT}% agent git author" |
| S017 | :203 | "five stages, all on-device" | C10 `PARTIAL` | REWRITE | "Five stages. Patient data stays on this computer unless the opt-in cloud assistant is switched on (off by default)." |
| S018 | :203 | "Behind every step is a verifiable code path, not a promise." | C13 `PARTIAL` | REWRITE | "Each step lists the code that implements it." |
| S019 | :439 | Import: drop a PDF, photo or FHIR export | C1 `VERIFIED` | KEEP | unchanged |
| S020 | :439 | "Files land encrypted on disk" | C21 `VERIFIED` | KEEP | "Uploaded files are stored AES-GCM encrypted with this profile's key." |
| S021 | :439 | "nothing leaves the machine" | C30, C10 | REWRITE | "The upload goes to the backend on 127.0.0.1." |
| S022 | :440 | pointers: `api/documents.py ~:400`, AES-GCM, `modules/ingest` dedup | C1, C13 | KEEP | pointers re-verified at `{SHA}` |
| S023 | :443 | "Date handling … ISO-8601 … collection-label priority … undated excluded" | none | DROP | "Extraction proposes values with units and dates." |
| S024 | :444 | "OCR (Tesseract) + parsing" | C13 | REWRITE | "OCR via Tesseract when it is installed; text extraction for PDFs" |
| S025 | :444 | "normalize + glossary — analyte synonyms → canonical names" | C13 | KEEP | unchanged |
| S026 | :444 | "POST /{id}/reprocess re-runs extraction" | C13 (pointer) | KEEP | unchanged (not demoed) |
| S027 | :447 | "AI extraction is a draft, never ground truth" | C2 `PARTIAL` | REWRITE | "Extracted values land unverified until the patient confirms them." |
| S028 | :447 | "verified/unverified split is load-bearing downstream" | C2 `PARTIAL` | REWRITE | "The default assistant, FHIR, visit-prep and pinboards use verified values only. Trends, the legacy assistant path and CSV/JSON/doctor-summary exports do not." (after W-3: drop "Trends" and "legacy assistant path") |
| S029 | :448 | "Corrections feed the RL dataset (redacted)" | C24 `VERIFIED` | REWRITE | "Assistant feedback exports as a strict-redacted dataset after explicit confirmation" |
| S030 | :451 | Trends "across all verified imports" | C2 → `CONTRADICTED` as stated | REWRITE | before W-3: "Charts each analyte over time. It currently includes values not yet verified; marking them is planned (W-3)." after W-3: "Charts each analyte over time; unverified points are marked 'unverified'." |
| S031 | :452 | "undated observations excluded from series" | none | DROP | — |
| S032 | :455 | "mandatory citations to the patient's own results and a reference knowledge base" | C3 `PARTIAL` | REWRITE | "The default path attaches a source to every sentence and drops sentences it cannot source. The legacy path checks `[cite:N]` markers." |
| S033 | :455 | "constitutionally barred from diagnosis or dosing" | C4 `VERIFIED` (mechanism) | REWRITE | "A prohibited-pattern suite blocks diagnosis and dosing language (tested; no test can prove 'never')." |
| S034 | :455 | "Feedback … export as redacted RL datasets (explicit confirmation required)" | C24 | KEEP | unchanged |
| S035 | :456 | "agent graph (default) or RAG path" | C3, C14 | KEEP | unchanged |
| S036 | :456 | "validate_response + interpret_safety + abstention" | C14 | REWRITE | "agent: guard (groundedness + advice classifier); legacy: validate_response + interpret_safety patterns" |
| S037 | :457 | tags `[YOUR_RESULTS:N]`, `[REFERENCE:N]` as markers | C3; D11 | REWRITE | tags "sourced sentences", "education only" |
| S038 | :211 | "becomes a trusted, queryable observation through eight stages. Every stage is a real module" | C13 | REWRITE | "A lab file becomes an observation the patient can verify. Each node names the module that does the work." |
| S039 | :462 | Upload: AES-GCM file; audit event on every doc route | C21, C19 | KEEP | unchanged |
| S040 | :463 | "core/audit.py middleware" | C19 | REWRITE | "core/audit.py helpers" |
| S041 | :465 | Ingest: format detection, dedup, FHIR structured path | C1, C13 | KEEP | unchanged |
| S042 | :466 | "modules/ingest/", "FHIR import (INGEST-FHIR-001, shipped as HC-M23)" | C13; `feature_list.json` HC-M23 completed | REWRITE | "modules/ingest.py", "FHIR import (HC-M23)" |
| S043 | :468 | "layout-aware text extraction for PDFs" | C13 | REWRITE | "Text extraction for PDFs; OCR via Tesseract when installed" |
| S044 | :469 | "collection-label date priority" | none | DROP | — |
| S045 | :471 | "'Hgb A1c' → 'HbA1c'; units normalized … comparable across labs" | C13 | REWRITE | "Analyte synonyms map to canonical names (modules/normalize.py, modules/glossary.py)." |
| S046 | :474 | Chunk+Embed: sentence-transformers; pure-Python cosine; FAISS removed 2026-07-01 | C12, C13 | REWRITE | same text + "The embedding model is fetched from Hugging Face on first use." (after W-8: "…is downloaded once and loads offline.") |
| S047 | :475 | "_create_chunks_and_embeddings :827" | pointer | KEEP | line re-verified |
| S048 | :477 | "structured observations materialize from the extraction rows" | C13 | REWRITE | "Classifies the document and extracts entities; optional LLM assist." |
| S049 | :480 | "persist only in the profile's encrypted vault via ProfileDbSession" | C25, C16 | REWRITE | "Observations are written to the profile's own vault through ProfileDbSession, never the master DB. The vault is SQLCipher-encrypted where SQLCipher is installed." |
| S050 | :483 | "wait for human verification before downstream trust" | C2 | REWRITE | same text as S028 |
| S051 | :219 | "One facade, three providers, zero telemetry." | H11 `PARTIAL` | REWRITE | "Local inference runs through one facade (ModelRunner) over two local providers. An opt-in cloud runner sits outside it as a documented exception." |
| S052 | :219 | "All inference is local by default" | C10 `PARTIAL` | KEEP | unchanged |
| S053 | :219 | "external runners are opt-in and pass through a PHI-redaction gate first" | C10; LOCAL-04 | REWRITE | before W-6: "The cloud runner is off by default and redacts by default; outside production a setting can switch redaction off (removal approved, W-6)." after W-6: "…redaction cannot be switched off; break-glass is audited and shows a warning." |
| S054 | :222 | "scripts/download_models.py · LLM_MODEL selects tier" | C27 | REWRITE | "Models are downloaded explicitly with src/backend/scripts/download_models.py (Hugging Face or `ollama pull`). The default assistant path needs no model." |
| S055 | :224 | tier/small "Fast extraction & classification drafts…" | none | DROP | — |
| S056 | :225 | tier/default "Gemma-class GGUF for assistant chat" | none (default chat uses no model, C14) | DROP | — |
| S057 | :226 | tier/quality "per-profile model settings override" | none | DROP | — |
| S058 | :227 | "on-branch Phi-4-mini tier + tier-capability UI" | none | DROP | — |
| S059 | :488 | "lazily imported so the app boots without a model" | C27 | KEEP | unchanged |
| S060 | :488 | "the only sanctioned network call in product flow" | C10, C12 | REWRITE | "Model files come from an explicit download step. Until W-8, the embedding model is also fetched implicitly on first use." |
| S061 | :489 | "GGUF tiers incl. Gemma-class" | none | DROP | — |
| S062 | :489 | "no-LLM fallback stays functional" | C14 | KEEP | unchanged |
| S063 | :490 | "localhost-only by design" | C26 | KEEP | unchanged |
| S064 | :490 | "OLLAMA_BASE_URL is pinned … enforced by config, not convention" | C26 | REWRITE | "The provider refuses any non-local URL when it is constructed; tested." |
| S065 | :492 | "passes through modules/redaction.py first — PHI is stripped before anything leaves" | C10; LOCAL-04 | REWRITE | same as S053 + "Redaction is pattern-based." |
| S066 | :493 | "(Wave-0 fixes on branch)", "redaction.py — hard gate", "per-profile opt-in" | C10 | REWRITE | "core/external_runner.py", "modules/redaction.py — strict by default", "per-profile opt-in, off by default" |
| S067 | :234 | "Every answer … exits through the same validation gauntlet" | C14, C3 | REWRITE | "The two assistant paths use different checks. Toggle to compare." |
| S068 | :236 | "Agent graph path (default ON)" | C3 | KEEP | unchanged |
| S069 | :497 | agent lane: 8 read-only tools, MAX_STEPS=5 | C14 | KEEP | unchanged |
| S070 | :497 | agent lane node "validate — validate_response :793" | C14 (only caller `rag.py:1271`) | DROP | node removed |
| S071 | :497 | "draft — compose cited answer" | C14 | REWRITE | "draft — deterministic template, no LLM call" |
| S072 | :498 | legacy "retrieve [YOUR_RESULTS] obs + [REFERENCE] KB" | C2 | REWRITE | before W-3: "observations (incl. unverified) + knowledge base"; after W-3: "verified observations + knowledge base" |
| S073 | :498 | legacy compose / ModelRunner / validate_response | C3, C23 | KEEP | unchanged |
| S074 | :593 | end node "CITED ANSWER or abstain/escalate" for both lanes | C28 | REWRITE | agent: "sourced answer or abstention"; legacy: "answer served; is_valid flag in payload" (after W-4: "abstention template when is_valid=False") |
| S075 | :242 | "[YOUR_RESULTS:N] — only the patient's own verified observations" | C3, C2; D11 | REWRITE | "[YOUR_RESULTS:N] labels the patient's own values in the legacy prompt. It is a context label; the validated marker is [cite:N]." |
| S076 | :243 | "[REFERENCE:N] — only the seeded knowledge base (scripts/seed_knowledge_base.py)" | C3; D11 | REWRITE | "[REFERENCE:N] labels knowledge-base entries (src/backend/scripts/seed_knowledge_base.py)." |
| S077 | :244 | "Memory & session history are labeled non-citable" | C23 | KEEP | unchanged |
| S078 | :245 | "Every claim must map to a source — checked in validate_response" | C3, C14 | REWRITE | "Agent path: the guard drops any sentence it cannot map to a source. Legacy path: validate_response checks [cite:N] markers." |
| S079 | :247 | "Education only — never diagnosis or dosing" | C4 | REWRITE | same as S033 |
| S080 | :248 | "interpret_safety prohibited-pattern suite must keep passing" | C4 | KEEP | unchanged |
| S081 | :249 | "Abstain/escalate templates when confidence is low" | C28; H3 | REWRITE | "Agent path abstains when it cannot ground an answer. Legacy path still serves low-faithfulness answers, flagged in the payload (abstention planned, W-4)." |
| S082 | :250 | "74 golden eval cases gate every PR on behavior" | H3 `PARTIAL` | REWRITE | "74 golden cases run in CI (agent path only). Whether the check is merge-required is not recorded in the repo." |
| S083 | :252 | 6 axes listed as 4 names | H3 | REWRITE | "groundedness, citation accuracy, abstention correctness, injection resistance = 1.0; advice leakage, PHI leakage = 0" |
| S084 | :253 | "consistency_score = 1.0 placeholder … HC-M11, owner-gated" | C22 | REWRITE | "consistency_score is a fixed 1.0 placeholder. An NLI replacement (HC-M11) is approved only behind a default-off flag; changing production scoring is owner-gated." |
| S085 | :254 | "CI job agent_eval_gate enforces absolute bars" | H3 | REWRITE | "CI job agent-evals runs scripts/agent_eval_gate.py with absolute bars" |
| S086 | :261 | "One unencrypted master DB (metadata only)" | C18 | REWRITE | "One unencrypted master DB (profile names, password hashes, audit rows, knowledge base)" |
| S087 | :261 | "+ one SQLCipher vault per profile" | C16 `PARTIAL` | REWRITE | "+ one vault per profile, SQLCipher-encrypted where SQLCipher is installed" |
| S088 | :261 | "Delete is a cryptographic ceremony, not a row removal" | C5 `VERIFIED` (code path) | KEEP | "Deletion is an ordered crypto-erase, not a row flag." |
| S089 | :264 | badge "unencrypted · no PHI" | C18 | REWRITE | "unencrypted · names, hashes, audit rows" |
| S090 | :266 | "bcrypt, JWT HS256, token revocation" | C29 | KEEP | unchanged |
| S091 | :267 | "Append-only audit log — every doc/observation/profile touch" | C19 `PARTIAL` | REWRITE | "Audit log for document and observation routes and 9 of 13 profile routes. Deleting a profile purges its audit rows." |
| S092 | :268 | knowledge base in master | C18 | KEEP | unchanged |
| S093 | :269 | backup schedules in master | C18 | KEEP | unchanged |
| S094 | :275 | vault contents list | C25 (overview §4) | KEEP | unchanged |
| S095 | :276 | DEK sealed + recovery copy | C6 (backend) | KEEP | unchanged |
| S096 | :277 | "Documents at rest: AES-GCM encrypted files" | C21 | KEEP | unchanged |
| S097 | :278 | "Access only via ProfileDbSession — never the master session" | C25 | KEEP | unchanged |
| S098 | :273 | badge "SQLCipher · sealed DEK" | C16 | REWRITE | "SQLCipher where installed · sealed key" |
| S099 | :282 | `DELETE /profiles/{id}` with phrase `DELETE MY HEALTH DATA` | C5 (`api/profiles.py:78`) | KEEP | unchanged |
| S100 | :284 | step 1 "Destroy sealed DEKs — data unreadable from this instant" | C5, C17 | REWRITE | "1 · Unlink the sealed key files first" |
| S101 | :285-286 | steps 2–3 vault sweep, backup sweep | C5 | KEEP | unchanged |
| S102 | :287 | step 4 purge audit rows + tombstone | C5, C19 | KEEP | unchanged |
| S103 | :291 | backups "Deliberately unredacted" | C17 | KEEP | unchanged |
| S104 | :292 | profile-scoped restore | C17 | KEEP | unchanged; add "The archive also carries a plaintext master copy of this profile's row and audit rows." |
| S105 | :293 | "Gated on password + phrase RESTORE MY DATA" | C17 | KEEP | unchanged |
| S106 | :294 | scheduler "records skipped_locked honestly" | C13 (code-read) | REWRITE | "A lifespan scheduler runs due backups and records skipped_locked when a vault is closed (code path; not run in the audit)." |
| S107 | :296 | recovery code issued at profile creation | C6 | KEEP | unchanged |
| S108 | :297 | "main lacks a signed-in UI … landing via branch" | C6 `PARTIAL` | REWRITE | after Task 1 confirms `RecoveryCodeCard` is mounted on `{SHA}` and the dry run shows it: "Settings can issue a new recovery code (merged in P1)." Else unchanged. |
| S109 | :304 | "Maturity: L3 structured, trending L4" | M5 | REWRITE | "The 2026-09-25 audit's qualitative rubric rated the harness L3, trending L4 (the auditors' judgment, not a measurement)." |
| S110 | :306 | 12 maturity bars | M5 | DROP | — |
| S111 | :309 | CLAUDE.md + AGENT.md as constitution | H13 | KEEP | unchanged |
| S112 | :310 | "18 skills: 14 vendored + 4 domain, routing table" | H14 | KEEP | "{SKILLS_P} process skills + {SKILLS_D} domain skills, with a routing table" |
| S113 | :311 | "feature_list.json — 24 items" | H14 (27) | REWRITE | "feature_list.json — {FEATURES} items, each with verification commands, linted in CI" |
| S114 | :312 | "docs_lint × 13 rules" | H14; GATE-01 | KEEP | unchanged |
| S115 | :313 | agent_eval_gate 74 cases, 6 axes | H3 | REWRITE | add "(agent path only)" |
| S116 | :314 | security gate "fails open … fix verified on unmerged branch (7 new tests)" | H4 | REWRITE | "Fails closed since P1: a missing scan report exits 2 (measured {FREEZE_DATE})." (if Task 1 step 8 did not measure it: "Fixed by P1; fail-closed behaviour not re-measured.") |
| S117 | :315 | route_client "built to defeat the dependency-bypass blind spot" | H17 `PARTIAL` | REWRITE | "route_client runs route tests through real HTTP. Many route tests still call handlers directly." (amber dot) |
| S118 | :316 | recurring-failures "Correctly predicted several of this audit's own findings" | H7 `CASE-STUDY` | REWRITE | "8 documented failure modes. Several later findings match them — a match, not a prediction test." |
| S119 | :318 | heading "Recurring failure modes" over the audit taxonomy | H7 | REWRITE | "Recorded failure modes (docs/agentic/recurring-failures.md)" + the file's 8 headings (F10) |
| S120 | :508 | card "Verification theater" (restore 400s) | H18 | KEEP | moved under mode 1 |
| S121 | :509 | card "Report-as-fact" (620/1160/1245) | M3 (finding) | KEEP | moved under mode 3 |
| S122 | :510 | card "Contaminated-tree gate: security_gate swallows FileNotFoundError" | H4; mode 5 is about working-tree gates | REWRITE | mode 5 text from the file; the security-gate example moves under mode 1 |
| S123 | :511 | card "Filename-level assertion" (password hashes) | H18 | KEEP | moved under mode 1 |
| S124 | :512 | card "Phantom layer … .gitignore makes the claim uncommitable" | H5 (finding) | REWRITE | removed from the modes figure; kept as finding S145 |
| S125 | :513 | card "One-canonical-path" (duplicate download_models.py) | H15; mode 6 | KEEP | moved under mode 6 |
| S126 | :514 | card "Docs-ahead drift" (scheduler) | C7 (finding); mode 8 | KEEP | moved under mode 8 |
| S127 | :515 | card "Green ≠ proof: Every confirmed defect coexisted with a passing signal" | H7 | REWRITE | "Each recorded mode coexisted with a passing signal (recurring-failures.md intro)." |
| S128 | :325 | "100% human Dec→May, then ~96% agent after the June 23 pivot" | H1, H12 | REWRITE | "By git author name: 0 of 98 commits from Dec to May name an agent; 239 of 248 from 2026-06-23 do (at 40f590e). 28 of those Dec–May commits carry an agent co-author trailer, so author name is a proxy." |
| S129 | :325 | "The harness arrived first; then the agents." | H13 | REWRITE | "CLAUDE.md and AGENT.md were committed 2026-06-13; the first agent-authored commit is 2026-06-23. The docs lint and security gate are older (2026-02)." |
| S130 | :518-526 | era bar percentages | H12 (`CONTRADICTED` E3/E4/E5/E6) | REWRITE | measured values (F11) |
| S131 | :519 | E0 "+14,397-line skeleton in 2 commits" | H12 (2 commits ✓; lines unmeasured) | REWRITE | "2 commits" (+ line count only if Task 1 step 4 measures it with `git show --shortstat`) |
| S132 | :520 | E1 "100% human" | H12 | REWRITE | "0/62 agent git author; 27/62 with an agent co-author trailer" |
| S133 | :521 | E2 "34 commits; CS4610 Part-1 submitted 05-15" | H12; report cover | KEEP | unchanged |
| S134 | :522 | E3 "Human lays rails: provider layer, RAG memory, RL pipeline, CLAUDE.md/AGENT.md" | H12 (`fedc500`, `9733a7b`, `242ed62`, `ee8bd33`) | KEEP | unchanged; bar shows 0/9 |
| S135 | :523 | E4 "55% of all history … backup-defect storm" | H12, H18 | REWRITE | "{E4_N} of {H1_TOTAL} commits; 12 fix(backup) commits 2026-07-29…31" |
| S136 | :524 | E5 "HealthCentral→Asclexis; recurring-failures.md born" | H13; `37a0f50` (2026-08-01 master DB rename) | KEEP | "Rename; recurring-failures.md added 2026-08-04" |
| S137 | :525 | E6 "PR #18; two repair branches ahead of main" | git | REWRITE | "PR #18; branches A and B merged in P1 ({P1_DATE})" |
| S138 | :328-329 | authorship bar 33/67, "239/355 commits" | H1 | REWRITE | re-measured at `{SHA}` |
| S139 | :329 | "8 model variants" | none | DROP | — |
| S140 | :332 | "Authorship time-series → the developer→orchestrator curve" | H1 | REWRITE | add "(git-author proxy)" |
| S141 | :333 | "July backup storm: 3 cascading fixes in 2 days" | H18 (12 fixes, 3 days) | REWRITE | "July 2026 backup fixes: 12 fix(backup) commits, 2026-07-29…31" |
| S142 | :334 | "Drift-vs-gates correlation … near-zero drift where gates run" | M2 `HYPOTHESIS` | REWRITE | "Hypothesis to test: docs drift where no gate runs. Observed drift sat on ungated surfaces; gated surfaces were not sampled." (data-kind="hypothesis") |
| S143 | :335 | "6-agent audit … reconciler caught 3 sibling-agent errors (… quantified)" | M1 `CASE-STUDY` | REWRITE | "Case study: in the 2026-09-25 audit (reported as 6 agents), the reconciler caught 3 errors in sibling output. One run; no rate." |
| S144 | :337 | fail-open gate shipped green | H4 (finding) | KEEP | "The security gate shipped green while failing open (fixed in P1)." |
| S145 | :338 | `.claude/agents/` cited while gitignored | H5 (finding) | KEEP | after W-1 add: "Five definitions were authored new by owner decision D1 ({W1_DATE})." |
| S146 | :339 | "only generic GSD hooks" | H6 | REWRITE | "…show only continuous-learning and GSD hooks" |
| S147 | :340 | 620 / 1160 / 1245 | M3 (finding) | KEEP | unchanged |
| S148 | :347 | "6 audit agents + reconciliation + independent verification" | README (REPORTED; audit addendum A-5) | REWRITE | "Audit of 2026-09-25 (reported as 6 agents + reconciliation; the agent outputs are not packaged)." |
| S149 | :347 | "all 8 workstream plans written (4,128 lines, TDD checkbox tasks)" | M6 (plans exist) | REWRITE | "8 audit plans (2026-09-25) and 14 follow-up plans (2026-09-27), all proposed, none executed" (update if any merged) |
| S150 | :347 | "the planning pass itself caught 4 errors in this audit" | M1 `CASE-STUDY` | KEEP | data-kind="case-study" |
| S151 | :529 | finding: gate fails open; "Fix verified on unmerged branch" | H4 | REWRITE | "Fixed in P1; exit 2 on a missing report (measured {FREEZE_DATE})" |
| S152 | :530 | finding: scheduler never started; "Docs contradict on whether deliberate" | C7 | REWRITE | drop the last sentence; after P2: "Wired in P2 (session-scoped)" only if measured |
| S153 | :531 | finding: in-memory export stores | C11 | KEEP | unchanged |
| S154 | :532 | finding: utcnow "~50 sites / 13 files" | H9 | REWRITE | "101 product lines (109 references) in 30 files" (after P5: "0 product hits; lint in CI" if measured) |
| S155 | :533 | finding: recovery-code dead end | C6 (`docs/user/faq.md:46`) | KEEP | after P1: "UI merged in P1; faq.md:46 still says there is no recovery" (until P4) |
| S156 | :534 | finding: correlation rule divergence | none | DROP | — |
| S157 | :535 | finding: test/reset misses 6 tables | none (matrix MIG-04 only) | DROP | — |
| S158 | :536 | finding: FK cascades inert, "Where: sqlcipher_driver.py" | H10 | REWRITE | "Where: PRAGMA foreign_keys set nowhere (api/profiles.py:914 is a comment)" |
| S159 | :537 | finding: unredacted source_quote, "branch1 fixes" | C20 | REWRITE | "POST /export/questions returns source_quote unredacted; neither merged branch changes api/export.py." |
| S160 | :538 | finding: consistency_score, "owner-gated" | C22 | REWRITE | same as S084 |
| S161 | :539 | finding: "analytics.py/verify.py dead; SCAFFOLD ONLY; api/__init__ names old product" | H15 (docstrings only) | REWRITE | "Stale docstrings: modules/agent/__init__.py says SCAFFOLD ONLY; api/__init__.py names the old product." |
| S162 | :540 | finding: hygiene (duplicate script, .vite/, Office lock files, audit retention) | H15; AUD-03 | REWRITE | "Duplicate download_models.py; tracked .vite/deps; unbounded audit retention (owner-gated, P8)." (lock files removed by P1) |
| S163 | :356 | "Workstreams (owner-approved order)" | program | REWRITE | "Program phases (implementation-program.md, 2026-09-27)" |
| S164 | :359-366 | 8 workstream rows (urgency and "why") | program; C7; H9; H10 | REWRITE | replaced by the phase/plan table (F14) |
| S165 | :373 | "each layer caught errors in the last" | M1, M6 | REWRITE | "Review found errors at several layers in these runs (case studies, no rates)." |
| S166 | :377 | node "Audit · 6 agents + reconciliation · DONE" | README (REPORTED count) | REWRITE | "Audit · 2026-09-25 · done" |
| S167 | :379 | node "Plans · 8 agents · 8 plans · DONE" | M6 | REWRITE | "Plans · 8 + 14 · written, not executed" |
| S168 | :381 | node "Orchestrator · specs+compliance · READY" | M4 | REWRITE | "Contract, matrix, program · done 2026-09-27" |
| S169 | :383 | node "Execution · NEXT" | git | REWRITE | "Execution · P1 merged {P1_DATE}; later phases proposed" |
| S170 | :385 | node "Capstone report · OPEN" | — | KEEP | unchanged |
| S171 | :390-393 | knowledge-base list (goal, ledger, outline, 4 research docs) | pointers | KEEP | unchanged |
| S172 | :394 | "specs-compliance-matrix.md + implementation-program.md — pending" | M4 | REWRITE | "specs-compliance-matrix.md (73 requirement rows, 4 enforced) and implementation-program.md, written 2026-09-27" |
| S173 | :397-400 | ledger chips 11/1/6/2 | ledger (24 rows today) | REWRITE | generated counts (F16) |
| S174 | :403 | contradicted rows "(phantom agents, AgentShield, fail-open gate)" | H5, H6, H4 | REWRITE | "(phantom agents, fail-open gate; AgentShield is not evidenced)" |
| S175 | :404 | "a claim ships only with a ledger row + evidence pointer" | ledger usage rule | KEEP | unchanged |
| S176 | :408-418 | plan-files table (8 rows: lines, "corrected the audit on") | REPORTED | DROP | — |
| S177 | :425 | footer "repository audit (6 agents + orchestrator verification)" | README | REWRITE | §7.2 rule 4 footer |
| S178 | :426 | "Single self-contained file · no external requests" | checked by Task 7 grep | KEEP | unchanged |
| S179 | :441 | Import tags PDF / image-OCR / FHIR | C1 | KEEP | unchanged |
| S180 | :445 | Extract tags "deterministic rules first", "ISO-8601 canonical" | none | DROP | — |
| S181 | :449 | Verify tags "human gate", "source-linked" | C2 | REWRITE | "human gate" only |
| S182 | :448 | Verify pointers "VerificationWorkbench", "verified flag on every observation" | C2 | KEEP | unchanged |
| S183 | :452-453 | Trends pointers + tags "longitudinal", "per-analyte" | C13 | KEEP | unchanged |
| S184 | :469-484 | node pointers (extract.py, normalize.py, glossary.py, :928, profile_database.py, sqlcipher_driver.py, migrations/profile/, Workbench, reprocess) | pointers | KEEP | re-verified at `{SHA}` |

### 9.2 Outline (`docs/capstone-report/report-outline.md`)

| ID | Where | Claim now | Ledger → verdict | Action | Exact text |
|---|---|---|---|---|---|
| O01 | :11 | problem statement | author motivation (no statistics) | KEEP | unchanged |
| O02 | :12 | author motivation | author statement | KEEP | unchanged |
| O03 | :13 | "working product" | C8, C13 | REWRITE | "Dual contribution: a locally run product (dev launcher; no installer yet) + agentic-SWE methodology study" |
| O04 | :18 | "per-profile SQLCipher vaults … dual Alembic" | H8, C16 | REWRITE | "…per-profile vaults (SQLCipher where installed, C16)…" |
| O05 | :19 | five core flows | C13 `PARTIAL` | REWRITE | append "(2 re-traced, lifecycle code-read, 2 reported — C13)" |
| O06 | :21 | wired vs inert vs absent vs partial | C2, C7, C8, C9 | KEEP | unchanged |
| O07 | :22 | agent path makes no LLM call | C14 | KEEP | cite C14 |
| O08 | :26 | citation contract, interpret_safety, abstention, redaction gate | C3, C4, C10, C28 | REWRITE | "Citation checks (agent guard vs legacy validate_response), interpret_safety patterns, abstention (agent path; legacy serves flagged answers until W-4), redaction (strict by default; dev bypass until W-6)" |
| O09 | :27 | vault model, DEK sealing, recovery codes, crypto-erase | C5, C6, C21 | KEEP | unchanged |
| O10 | :28 | "4 of 73 rows enforced" | M4 | KEEP | cite M4 |
| O11 | :29 | must-own gaps list | C22, C3, C9, C2, C11 | REWRITE | §4 row 3 wording; add C12, C15–C17, C19, C20 |
| O12 | :33 | eras E0–E6 authorship curve | H12 | REWRITE | "Eras E0–E6 with measured git-author shares (H12)" |
| O13 | :34 | "constitution → skills → ledger → gates → memory" | H13 `CONTRADICTED` order | REWRITE | §4 row 4 wording |
| O14 | :35 | "Evidence: audit §9, §12–14; commits" | H1, H12, H13 | REWRITE | "Evidence: claims-ledger H1, H12, H13 (commands); audit §9, §12–14 as context" |
| O15 | :39 | constitution; 18 skills; feature_list; route_client "targeted blind-spot fix"; recurring-failures | H14, H17, H7 | REWRITE | "…`route_client` (required; many route tests still direct-call, H17)…" |
| O16 | :44 | "July backup storm" | H18 | REWRITE | "July 2026 backup fixes (12 fix(backup) commits, H18)" |
| O17 | :45 | fail-open gate flagship | H4 (finding) | KEEP | add "fixed in P1" after Task 1 |
| O18 | :46 | phantom layer three-level absence | H5 (finding) | KEEP | after W-1: add D1 sentence |
| O19 | :47 | multi-agent case studies | M1 `CASE-STUDY` | KEEP | M1 evidence amended (§3.2) |
| O20 | :51-52 | related work; Laya framing | research/ (literature, not repo claims) | KEEP | unchanged |
| O21 | :56 | single-developer; attribution ambiguity | H1 | KEEP | unchanged |
| O22 | :57 | claims outran artifacts in the Part-1 report | H5, H6, H16 | KEEP | cite H16 too |
| O23 | :58 | runtime behaviours unexecuted | overview §14 | KEEP | unchanged |
| O24 | :63 | roadmap sequence | program | REWRITE | append "; 2026-09-27 plan set (14 plans + S-1), all PROPOSED" |
| O25 | :68 | thesis answer | argument | KEEP | unchanged |
| O26 | :69 | maturity verdict L3 → L4 | M5 | KEEP | cite M5 |

### 9.3 Tally (counted from the tables above; Task 7 re-counts)

| Source | Claims | KEEP | REWRITE | DROP |
|---|---|---|---|---|
| Showcase | 184 | 63 | 103 | 18 |
| Outline | 26 | 15 | 11 | 0 |
| **Total** | **210** | **78** | **114** | **18** |

### 9.4 Deviations found at execution (2026-10-20, Task 1 Step 9 and Task 2 Step 3)

The §9.1 table above is the 2026-09-27 plan; the committed showcase copy follows it except where the tree had moved. Each deviation names its ledger row. §9.3's tally was re-counted (63/103/18 and 15/11/0) and stays as written.

| Rows | Plan text | What the tree showed | Copy says |
|---|---|---|---|
| S007-S016, S112, S113 | tile and card figures | skills 32 + 4 (H14), CI jobs 8 (H14), commits 1459 at c529d19 (H12), collected 2,011 (H2) | measured values |
| S003, S016, S128, S138 | "{H1_PCT}% agent git author" | author name is 18% lifetime; October commits carry the agent only as a co-author trailer (71% by author or trailer, H12) | both figures, with the proxy caveat; E7 era added |
| S046, S054, S060, C12 text | "fetched on first use" | W-8 landed (#168); offline load, fails closed (C12) | "downloaded once, loads offline" |
| S030, S072, S028 | W-3 switch text | W-3 merged (#136), but ledger rows C2 and C3 predate it | the verification clauses are dropped; no claim rests on a stale row |
| S053, S065 | before/after W-6 text | W-6 merged (#32); C10 says "redacts by default" | "off by default and redacts by default" |
| S074, S081 | legacy serves invalid answers | W-4 merged (#72); C28 rewritten to the post-W-4 state | legacy lane ends in the abstention template |
| S108, S155 | recovery-code UI | card is mounted (`SettingsPage.tsx:943`) but C6 predates it | the UI sentence and the finding row are dropped |
| S116, S151 | gate fail-closed | measured rc=2 (§15) | stated with the date; H4 stays a finding |
| S119-S127 | 8 failure modes | `recurring-failures.md` now has 12 entries (H14) | 12 headings, one quoted sentence each |
| S133 | "Part-1 submitted 05-15" | O-7: the report gives two dates | date dropped |
| S152, S154, S158, S161, S162 | old findings | P2 wired (#31), utcnow 0 product hits (P5), FK pragma still unset (P6 is report-only), docstrings fixed (fd3f287) | rewritten with the 2026-10-20 measurements; H15 resolved |
| S149, S165-S169 | "all proposed" | 14 of 16 tracked items merged (M9) | status table from M9 |
| O10, S172, F20 | "4 of 73 enforced" | 3 of 78 (M4) | updated in the outline and the page |

Ledger rows C2, C3, C6, C7, C9, H4, H7 (8 modes), H9 and H10 carry pre-merge text. Their owners re-verdict them; this run did not edit them.

## 10. Claim-freeze checklist (run on the freeze date; owner signs O-6)

**Freeze date:** 2026-10-22 · **SHA:** `a16dd51` (origin/main `c97192d`) · **Run by:** claude opus (F-9 executor, L0 session 2026-10-22) — results in §15.1. First pass: check 8 NOT RUN. Second pass (2026-10-22, against the L0 GPU-box dry-run record, PR #210 comment 6334394792): checks 1-11 pass at the tip. Third pass (review 6345517807 fixes): checks 1-11 pass at the tip; O-6 is signed only by L0 after review

- [ ] 1. **Every claim has a ledger row.** `python3 <scratch>/showcase_claims_check.py docs/capstone-report/asclexis-showcase-{FREEZE_DATE}.html` → `OK: <n> claim elements, 0 unmapped, 0 disallowed`.
- [ ] 2. **No status word stronger than the ledger.** `grep -n -i -o -E "\b(verified|proven|guarantee[sd]?|never|always|every|all|complian[a-z]*|hipaa|secure[sd]?|enforced|fully|100%)\b" <new copy> docs/capstone-report/report-outline.md` → every hit listed in the execution record with its row and verdict. Any hit whose row is not `VERIFIED` is reworded.
- [ ] 3. **Numbers re-measured, with command and environment.** Every number on the page appears in Task 1's measurement table with the command, interpreter/OS and SHA. Pass counts only with their environment (SQLCipher present or absent; embedding model present or absent).
- [ ] 4. **Planned ≠ implemented.** `grep -n -E "\b(P[2-8]|W-[0-9]+a?b?|S-1|G-[ABC][0-9])\b" <new copy>` → each hit sits beside "planned", "proposed", "approved" or "merged {date}". "Merged" only with `git merge-base --is-ancestor <commit> {SHA}` exit 0.
- [ ] 5. **Owner-gated items named as such.** The page lists as owner-gated, unsigned: S-1 (S1-A, S1-B); W-4 OQ-1; W-3 O-5; W-2 O-2; W-8 Q-FC, Q-HASH; HC-M11 production scoring; MFA, key rotation, pen-test scope, audit retention (P8 briefs); G-C1, G-C3.
- [ ] 6. **No legal or HIPAA-compliance claim.** `grep -n -i "hipaa" <new copy> CS4610_Report_Demo/README.md docs/capstone-report/report-outline.md` → 0 hits, or only "designed as if HIPAA applied (owner choice, 2026-09-27)".
- [ ] 7. **Findings stay findings.** Every `CONTRADICTED`/`NOT-EVIDENCED` row appears only inside `data-kind="finding"` (checked by step 1).
- [ ] 8. **Demo matches the page.** The dry-run record (§6.3 check 11) shows each script step's actual result; any step whose result differs from its "says" line is cut or reworded.
- [ ] 9. **Coursework untouched.** `git diff --name-only origin/main...HEAD -- 'CS4610_Report_Demo/*.docx' 'CS4610_Report_Demo/*.pdf'` → empty.
- [ ] 10. **Old showcase untouched.** `git diff --quiet origin/main -- audit/2026-09-25/asclexis-showcase.html && echo unchanged` → `unchanged`.
- [ ] 11. **Docs gates.** `python3 scripts/docs_lint.py` → no error on files this plan touched; `python3 scripts/generate_docs_index.py --check` → fresh, or the stale files named.

## 11. Tasks

### Task 0: Worktree and preconditions

**Files:** none

- [ ] **Step 1: Use the claimed worktree**

The build-program RUNBOOK §3 claim creates the worktree and branch; this step does not create another.

```bash
set -o pipefail
cd "/mnt/e/Programming/Github Repo/hc-f-9"        # RUNBOOK §3 claim; branch docs/f-9-showcase-delta
git branch --show-current                          # docs/f-9-showcase-delta
git merge-base --is-ancestor 7b2ff1f HEAD && git merge-base --is-ancestor 692fdf3 HEAD && echo post-P1-ok
```

Expected: `docs/f-9-showcase-delta`, then `post-P1-ok`. Else STOP.

- [ ] **Step 2: Record which upgrade phases have merged**

A `git log --grep=<plan file>` count prints 0 for merged phases (the merge subjects name branches, not plan files). Use ancestry per phase, with the merge commit of its PR:

```bash
cd "/mnt/e/Programming/Github Repo/hc-f-9"
for pair in W-1:cbabed1 W-2:c4b1aa5 W-3:b45f9cb W-4:cfc1e50 W-5:d21c59d W-6:2f0cb6f W-8:26106ee W-10:6c13045 W-11a-PR4:25c993e P2:cff3827; do
  git merge-base --is-ancestor "${pair#*:}" HEAD && echo "${pair%%:*} merged" || echo "${pair%%:*} NOT merged"; done
test -f CS4610_Report_Demo/README.md && grep -c "written new" CS4610_Report_Demo/README.md
```

For a phase not listed (S-1, W-7, W-11b, P5/P6), find its merge commit with `git log --merges --format='%h %s' | grep -i <branch word>` and test it the same way; no merge commit means "not merged". Expected: the README exists (P1). `written new` count ≥ 1 means W-1 Task 6 landed; 0 → Task 5 waits. Record every answer in §15.

### Task 1: Measure every figure (freeze values)

**Files:** none (results go to §15)

- [ ] **Step 1: SHA and date.** `git rev-parse --short HEAD` → `{SHA}`; `{FREEZE_DATE}` = `2026-10-22` (owner decision O-6, prompt 30, `owner-decisions-2026-09-27.md:374`, moved the freeze from 2026-10-24 to the GPU-box session; the earlier rule was SHOW-DATE `:243`: freeze = showcase - 7 days; SHOW-FREEZE `:277`: showcase 2026-10-31). A pre-freeze run before that date is labelled "pre-freeze <date> @ <SHA>, not the O-6 freeze" and its figures are re-taken on 2026-10-24.
- [ ] **Step 2: Backend collected.** `cd src/backend && "$(git rev-parse --show-toplevel)/scripts/pyslot.sh" env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest tests/ --collect-only -q -p no:cacheprovider | tail -1` → `{COLLECTED} tests collected`. If the D9 venv is missing, use `/mnt/c/Python313/python.exe` and set `{INTERP}` = "Windows Python 3.13.7". Never copy a number from a doc (`CLAUDE.md`'s 1933 line may lag merges; the measurement wins). Do not run the full suite here (S-1: master-engine tests write into `<cwd>/data`).
- [ ] **Step 3: Inventory.**

```bash
cd "/mnt/e/Programming/Github Repo/hc-f-9"; set -o pipefail
grep -c "include_router" src/backend/api/__init__.py            # {ROUTERS}
ls src/frontend/src/pages/*.tsx | wc -l                            # {PAGES}
ls -d .claude/skills/*/ | wc -l; ls -d skills/*/ | wc -l          # {SKILLS_P} {SKILLS_D}
ls src/backend/tests/agent/golden/*.json | wc -l                   # 74 expected
python3 -c "import json;print(len(json.load(open('feature_list.json'))['features']))"   # {FEATURES}
grep -cE "^  [a-z][a-z0-9-]*:$" .github/workflows/ci.yml           # {CI_JOBS}; confirm by reading the jobs: block
grep -n "RecoveryCodeCard\|TierCapabilities" src/frontend/src/pages/SettingsPage.tsx
```

- [ ] **Step 4: Authorship (H1, H12).**

```bash
cd "/mnt/e/Programming/Github Repo/hc-f-9"
git rev-list --count HEAD; git log HEAD --format=%an | grep -c '^Claude$'
git log HEAD --format='%H|%ad|%an|%(trailers:key=Co-Authored-By,valueonly,separator=;)' --date=format:%Y-%m-%d > /tmp/claude-1000/authors.txt
python3 - <<'EOF'
rows=[l.rstrip("\n").split("|",3) for l in open("/tmp/claude-1000/authors.txt")]
eras=[("E0","2025-12-01","2025-12-31"),("E1","2026-01-01","2026-02-29"),("E2","2026-03-01","2026-05-31"),("E3","2026-06-11","2026-06-13"),("E4","2026-06-23","2026-07-31"),("E5","2026-08-01","2026-08-04"),("E6","2026-09-01","2026-09-30")]
for e,a,b in eras:
    s=[r for r in rows if a<=r[1]<=b]
    print(e,len(s),sum(r[2]=="Claude" for r in s),sum(r[2]=="Claude" or "claude" in r[3].lower() for r in s))
EOF
git show --shortstat --format=%h $(git log HEAD --reverse --format=%h | head -2)
```

Expected at `40f590e` (context, not target): 355 / 239; E0 2 0 0; E1 62 0 27; E2 34 0 1; E3 9 0 0; E4 230 222 222; E5 17 17 17; E6 1 0 0. Post-P1 totals are larger (A + B commits + merges). If a date range needs a different window, write the window in the ledger row.

- [ ] **Step 5: Harness dates (H13).** `for p in scripts/docs_lint.py scripts/security_gate.py CLAUDE.md skills scripts/agent_eval_gate.py .claude/skills feature_list.json src/backend/tests/support/routes.py docs/agentic/recurring-failures.md; do echo "$p $(git log HEAD --diff-filter=A --format='%ad %h' --date=short -- $p | tail -1)"; done` → the dates in H13 (unchanged by P1 unless a file was re-added).
- [ ] **Step 6: Matrix and ledger tallies.** Matrix: the script in M4's evidence → `62 … enforced 4` (or the new numbers if other plans changed rows; use what it prints). Ledger (after Task 2):

```bash
python3 - <<'EOF'
import re,collections
c=collections.Counter()
for l in open("docs/capstone-report/claims-ledger.md",encoding="utf-8"):
    if re.match(r"^\| [CHM]\d+ ",l):
        v=re.search(r"`(VERIFIED|PARTIAL|CASE-STUDY|REPORTED|HYPOTHESIS|NOT-EVIDENCED|CONTRADICTED|PENDING)`",l.strip().rstrip("|").split("|")[-1])
        c[v.group(1) if v else "?"]+=1
print(sum(c.values()),dict(c))
EOF
```

Expected: no `?`. These numbers feed F16 verbatim.
- [ ] **Step 7: Review log (M6).** Re-count the TSV (or the packaged copy after Task 8): `cut -f2 reviewer-log.tsv | sort | uniq -c; cut -f4 reviewer-log.tsv | sort | uniq -c` and write the time of the count. If the scratch file is gone and O-4 was not signed, M6 keeps the 2026-09-27T21:02 snapshot and stays `REPORTED`.
- [ ] **Step 8: Security gate (H4).** `python3 scripts/security_gate.py --bandit /nonexistent.json --pip-audit /nonexistent.json; echo "rc=$?"` → a line starting `ERROR:` and `rc=2` (B@7b2ff1f `scripts/security_gate.py:155-158`). Record; this is the only evidence that upgrades S116/S151.
- [ ] **Step 9: Citation pass for §5 and §9.1.** For each `showcase:N` line cited in §5 and §9.1, read the line in `audit/2026-09-25/asclexis-showcase.html` and confirm the "Claim now" text is there; for each `file:line` pointer in the "Exact text" column and in §5 (`api/documents.py:400`, `:928`, `modules/rag.py:1271`, `core/profile_database.py:308` and the like), `sed -n` the line at `{SHA}`. Record in §15 a one-line count (checked / moved / failed) and list each moved or failed citation. A failed one changes that row's Action (stop gate 4); a moved one gets its new line number. Plan edits from this step and from Task 2 Step 3 are committed as C1b (§14).

### Task 2: Append the ledger rows

**Files:** Modify `docs/capstone-report/claims-ledger.md` (append only; M1 evidence cell)

- [ ] **Step 1: Confirm no one else is editing the ledger.** Ask the orchestrator whether W-1 Task 6, W-8's docs commit or W-11a's G-B6 commit is open. If yes, wait.
- [ ] **Step 2: Confirm IDs are free.** `grep -nE "^\| (C1[1-9]|C2[0-9]|C30|H1[2-8]|M[4-8]) " docs/capstone-report/claims-ledger.md` → no lines. Else renumber and update §9 references.
- [ ] **Step 3: Re-verify each row's evidence on the post-P1 tree.** Run each command quoted in §3.1. Update line numbers; label them `main@{SHA}`. If an evidence line no longer holds, change the verdict to what the evidence shows, and update §9's action for every claim that cites the row.
- [ ] **Step 4: Append the rows** from §3.1 under their section tables, and the M1 sentence from §3.2. Bump `**Last Updated:**`.
- [ ] **Step 5: Check.** `python3 scripts/docs_lint.py` → no error naming `claims-ledger.md`; Task 1 step 6 script prints no `?`.
- [ ] **Step 6: Commit C1** (§14). If Step 3 changed a §9 action or a §3.1 line number in this plan, commit that plan edit separately as C1b (plan file only) after C1.

*What would this fail to notice?* A row whose evidence is true but whose claim text is broader than the evidence. Review each claim cell against its evidence cell once more before committing.

### Task 3: Update the outline and the capstone index

**Files:** Modify `docs/capstone-report/report-outline.md`, `docs/capstone-report/README.md`

- [ ] **Step 1:** Apply §9.2's REWRITE texts and §4's section changes; insert §4.1 after `:47`.
- [ ] **Step 2:** Figures inventory: point rows `:75-80` at `asclexis-showcase-{FREEZE_DATE}.html` with F-decisions from §5; delete the Maturity-bars row (F8 dropped); add `| Demo script | docs/plans/2026-09-27-senior-report-showcase-plan.md §6 | ✅ |`.
- [ ] **Step 3:** Capstone README Contents: add a row for the new showcase copy and one line under Open threads: "- [ ] Showcase claim freeze (plan `docs/plans/2026-09-27-senior-report-showcase-plan.md` §10)".
- [ ] **Step 4:** `python3 scripts/docs_lint.py` → no new error. If P0-B is done and `git status --short docs/INDEX.md` is empty: `python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py --link-graph`, and include `docs/INDEX.md docs/_link_graph.json` in C2.
- [ ] **Step 5: Commit C2.**

### Task 4: Fix the integration diagram (F19)

**Files:** Modify `docs/capstone-report/architecture-overview.md` (§2 diagram and its caption only)

- [ ] **Step 1:** Wait until W-8's and W-11a's docs commits (which edit this file) have merged or are confirmed not open.
- [ ] **Step 2:** In the Mermaid block (`:27-67` at main@40f590e): change `ASST -. "opt-in, redacted" .-> EXT` to `ASST -. "opt-in; strict redaction by default (dev bypass until W-6)" .-> EXT` and add `R -. "interpretations (opt-in)" .-> EXT`. If W-6 has merged, use "opt-in; redaction always on".
- [ ] **Step 3:** `grep -n "interpretations (opt-in)" docs/capstone-report/architecture-overview.md` → 1 line; docs lint clean for the file.
- [ ] **Step 4: Commit C3.**

### Task 5: Coursework scope notes

**Files:** Modify `CS4610_Report_Demo/README.md`

- [ ] **Step 1:** Task 0 step 2 showed W-1 Task 6 landed (W-1 merged; `written new` count ≥ 1). Else STOP this task. O-2 and O-7 were answered 2026-10-20.
- [ ] **Step 2:** Apply §8 Edits 1–4 and 6 (O-2) and Edit 5 (O-7), anchored to the README as it stands. Do not touch the hook bullet at `:11-15` (the PreToolUse / metadata-only logger text).
- [ ] **Step 3:** `git diff --stat -- CS4610_Report_Demo/` → only `README.md`. `git diff -- CS4610_Report_Demo/README.md | grep -c '^-[^-]'` → record the actual count in §15. Edit 1 replaces one line (`…Final Report §7.3.`) and Edit 6 may rewrite the last line of the closing paragraph; no other line is deleted, and no `.docx`/`.pdf` appears in the diff.
- [ ] **Step 4: Commit C4** (needs O-2).

### Task 6: Build the new showcase copy

**Files:** Create `docs/capstone-report/asclexis-showcase-{FREEZE_DATE}.html`

- [ ] **Step 1:** `cp audit/2026-09-25/asclexis-showcase.html docs/capstone-report/asclexis-showcase-{FREEZE_DATE}.html`.
- [ ] **Step 2:** Convert the JS data arrays (`JOURNEY`, `PIPE`, `PROVS`, `LANES`, `MATURITY`, `FAILMODES`, `ERAS`, `FINDINGS`, `STATS`) into static markup; keep only show/hide JS.
- [ ] **Step 3:** Apply every §9.1 row and every §5 decision F1–F17. Fill `{…}` slots from Task 1 only.
- [ ] **Step 4:** Tag every claim element per §7.2 rule 2.
- [ ] **Step 5:** Open the file in a browser at phone width and desktop width; toggles and filters work; no console errors.

### Task 7: Check the page against the ledger

**Files:** scratch only: `/tmp/claude-1000/showcase_claims_check.py` (not committed)

- [ ] **Step 1: Write the checker.**

```python
import re, sys
from html.parser import HTMLParser
from pathlib import Path

ALLOWED = {None: {"VERIFIED", "PARTIAL"}, "current": {"VERIFIED", "PARTIAL"}, "finding": {"CONTRADICTED", "NOT-EVIDENCED", "VERIFIED", "PARTIAL"},
           "case-study": {"CASE-STUDY"}, "hypothesis": {"HYPOTHESIS"}}
CLAIM_TAGS = {"li", "td", "p", "h2", "h3", "h4", "button"}
CLAIM_CLASSES = {"stat", "gs", "et", "ed", "s", "tag", "td", "t"}

def ledger_verdicts(path):
    out = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\| ([CHM]\d+)\b", line)
        if m:
            v = re.search(r"`(VERIFIED|PARTIAL|CASE-STUDY|REPORTED|HYPOTHESIS|NOT-EVIDENCED|CONTRADICTED|PENDING)`",
                          line.strip().rstrip("|").split("|")[-1])
            out[m.group(1)] = v.group(1) if v else None
    return out

class P(HTMLParser):
    def __init__(self):
        super().__init__(); self.stack = []; self.claims = 0; self.errors = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs); cls = set((a.get("class") or "").split())
        parent = self.stack[-1] if self.stack else {}
        ctx = {"ledger": a.get("data-ledger", parent.get("ledger")),
               "exempt": a.get("data-exempt", parent.get("exempt")),
               "kind": a.get("data-kind", parent.get("kind")),
               "claim": tag in CLAIM_TAGS or bool(cls & CLAIM_CLASSES), "tag": tag}
        if tag in {"br", "meta", "link", "img", "input"}: return
        self.stack.append(ctx)
    def handle_endtag(self, tag):
        if self.stack and self.stack[-1]["tag"] == tag: self.stack.pop()
    def handle_data(self, data):
        if not data.strip() or not self.stack: return
        if any(s["tag"] in {"script", "style", "title"} for s in self.stack): return
        top = self.stack[-1]
        if not any(s["claim"] for s in self.stack): return
        self.claims += 1
        if top["exempt"]: return
        if not top["ledger"]:
            self.errors.append(f"unmapped: {data.strip()[:60]!r}"); return
        for i in top["ledger"].split():
            v = VERDICTS.get(i)
            if v is None: self.errors.append(f"no ledger row or verdict: {i}")
            elif v not in ALLOWED.get(top["kind"], set()):
                self.errors.append(f"disallowed: {i}={v} kind={top['kind']}")

VERDICTS = ledger_verdicts("docs/capstone-report/claims-ledger.md")
html = Path(sys.argv[1]).read_text(encoding="utf-8")
p = P(); p.feed(html)
if re.search(r"https?://", html): p.errors.append("external URL present")
for e in p.errors: print(e)
unmapped = sum(e.startswith("unmapped") for e in p.errors)
print(("OK" if not p.errors else "FAIL") + f": {p.claims} claim elements, {unmapped} unmapped, {len(p.errors) - unmapped} disallowed")
sys.exit(1 if p.errors else 0)
```

- [ ] **Step 2: Run.** From the worktree root: `python3 /tmp/claude-1000/showcase_claims_check.py docs/capstone-report/asclexis-showcase-{FREEZE_DATE}.html; echo rc=$?` → `OK: …`, `rc=0`.
- [ ] **Step 3: Break it on purpose** (on a scratch copy, never the committed file): (a) change one `data-ledger` to `C999` → `no ledger row or verdict: C999`, `rc=1`; (b) delete one `data-ledger` from an `li` → `unmapped: …`, `rc=1`; (c) tag a finding row without `data-kind="finding"` → `disallowed: …=CONTRADICTED kind=None`, `rc=1`; (d) add `<a href="https://x">` → `external URL present`; (e) delete the `data-ledger` from an `h3` heading (an `h2` carries `data-exempt="navigation"`) → `unmapped: '<heading text>'`, `rc=1`; (f) retag the fixed half of a finding row (`data-kind="current"`) to a CONTRADICTED row such as H4 → `disallowed: H4=CONTRADICTED kind=current`, `rc=1`. Delete the scratch copy.
- [ ] **Step 4: Re-count the audit.** `grep -cE "^\| S[0-9]{3} .*\| KEEP \|" docs/plans/2026-09-27-senior-report-showcase-plan.md` and the same for REWRITE/DROP and `O[0-9]{2}` → must equal §9.3; fix §9.3 if not.
- [ ] **Step 5: Commit C5** (needs O-1).

*What would this fail to notice?* A claim inside an element the checker does not treat as claim-bearing (for example a bare `div` text node), and a claim whose `data-ledger` points to the wrong but allowed row. Also `data-kind="finding"` accepts CONTRADICTED for every word inside the element, so a present-tense clause such as "fixed in P1" inside a finding passes (the round-2 MAJOR). Wrap such a clause in its own `data-kind="current"` span and read every `data-kind="finding"` element for one. Mitigation: freeze checklist item 2's word grep, and a human read of every `data-ledger` against §9.1.

### Task 8 (owner-gated O-4): Package the review evidence

**Files:** Create `docs/reviews/reviewer-log.tsv`; option B also the `*-codex.txt` outputs, `review.sh`, `review-prompt-template.md`

- [x] **Step 1:** O-4 is signed: SHOW-O4 chose option B (2026-10-20). The orchestrator scratchpad was on the old machine, so nothing was copied; the repo already holds the TSV, 59 `*-codex.txt` and the per-round prompts under `docs/reviews/2026-09-27-swarm/` (archive move `1843ca3`). Absent option-B files, not recovered and not created: `review.sh`, `review-prompt-template.md`. Grep the files the option names first: Grep them for patient data first: `grep -l -i -E "ssn|date of birth|mrn|[0-9]{3}-[0-9]{2}-[0-9]{4}" <files>` → none for `reviewer-log.tsv` and `*-codex.txt` (the only hit in the whole dir is `className` in `TAILWIND-4-fable.md:37`, not an option-B file; STOP if a hit is real data).
- [x] **Step 2:** Update M6's evidence to the packaged path and its verdict to `CASE-STUDY` (drop "REPORTED until O-4").
- [x] **Step 3: Commit C6** (`b0a2886`; follow-through C6b aligns the outline, page chips and this plan).

### Task 9: Demo preparation and dry runs

**Files:** none in the repo (synthetic files outside it; results to §15)

- [ ] **Step 1:** Make the two synthetic PDFs (§6.1 rule 1): a table "Test | Result | Units | Reference range" with HbA1c 5.9 / 6.1 %, LDL 128 / 119 mg/dL, TSH 2.1 / 2.4 mIU/L, CRP 4.2 / 3.1 mg/L; collection dates 2026-03-02 and 2026-06-01. Export text-based PDFs (not scans).
- [ ] **Step 2:** Run §6.3 checks 1–10.
- [ ] **Step 3:** Create the fallback profile "Demo Backup" with both files imported and verified.
- [ ] **Step 4:** Dry run §6.2 with Wi-Fi off; record each step's actual result and time. Extraction must yield 4 values per file; if not, change the PDF layout, never the code.
- [ ] **Step 5:** Repeat at T-1 hour.

### Task 10: Claim freeze and PR

**Files:** Modify this plan's §15 (execution record). Step 1 (rehearsal) commits as C1b; Steps 2-3 and C7 are the 2026-10-22 binding run (O-6 moved it from 2026-10-24).

- [ ] **Step 1:** Run §10 items 1–11; paste outputs into §15. Before the freeze this is a rehearsal (labelled "pre-freeze"); commit it with C1b (the plan only), never C7.
- [ ] **Step 2:** Owner signs O-6.
- [ ] **Step 3: Commit C7**, push, open the PR (§14).

## 12. Dependencies: which phase upgrades which claim

A claim is upgraded only after its phase is merged **and** the named evidence is re-run at the freeze SHA.

| Phase / plan | Upgrades | Ledger rows to re-verdict | Evidence required |
|---|---|---|---|
| P1 (branches A+B) | gate fails closed; computed trust score; recovery-code card; lock files gone | H4, C3, C6, H15 | Task 1 steps 3 and 8; `grep -n "faithfulness_score=1.0" src/backend/api/assistant.py` → none |
| W-1 (P3) | `.claude/agents/` committed | H5 (W-1 edits it) | W-1's HC-AGENTS tests + drift check |
| P2 (#31 merged) | reminders fire (session-scoped) | C7 | HC-NSW tests; lifespan test; F-NOTIFY is dropped (§6.4); add a demo step only after Task 9 records it |
| S-1 | SQL echo off by default | C15 | HC-SQLECHO-001…004 green; `engine.echo` False with default config |
| W-2 | doctor summary redacted | C9 | HC-EXPR tests; then the demo may show the doctor summary |
| W-10 | CSV/JSON named exceptions in CLAUDE.md, data-privacy.md | C9 | the governance commit on main |
| W-3 | legacy RAG verified-only; trends labelled | C2 | HC-VER tests + vitest marker; S028, S030, S072 switch text |
| W-4 | legacy abstains on invalid answers; legacy eval gate | C28, C3, H3 | HC-LEG tests; CI job fails on the seed |
| W-5 | one citation-marker instruction | C3 (SAFE-08) | HC-CIT tests |
| W-6 | redaction unconditional; audited break-glass | C10 | HC-EXT tests; S053/S065 switch text |
| W-7 | tiered interpretation through ModelRunner | H11 | HC-LLMB boundary test |
| W-8 | embedding model offline load (D8-delivery) | C12, C10 | HC-EMB socket-blocked test; F-EMB switches text |
| W-11a | vitest/e2e counts; ciphertext test; profile-route HTTP tests | H2 (W-11a edits it), C16, H17 | its measured listings; S008/S009 may return |
| W-11b | export artifacts persist (G-C1, owner-gated S-C1-1) | C11 | restart test |
| P5 / P6 | utcnow; FK enforcement | H9, H10 | grep → 0; pragma test |
| G-C4 | packaging decision | C8 stays `NOT-EVIDENCED` until something is built | a decision record is not an installer |

## 13. Owner sign-offs

**Answered 2026-10-20 (L0 record, PR #210 comment 6285564680):** O-1 yes, O-2 yes (Edits 1-4, 6), O-5 yes, O-7 yes (add the note, Edit 5). The verbatim rows are in `owner-decisions-2026-09-27.md` (SHOW-O1, SHOW-O2, SHOW-O4, SHOW-O5, SHOW-O7). **Answered later:** O-4 option B (SHOW-O4, 2026-10-20, `owner-decisions-2026-09-27.md:310`; packaged by C6 `b0a2886`). **Not answered:** O-3 (the owner's demo-machine setting), O-6 (the claim freeze, moved to 2026-10-22 by the O-6 row `:374`; signed only by L0 after review of §15.1). An agent never ticks or signs a box (RUNBOOK §9.2), so the Signed column below stays as the owner left it; the answers above are the record until the owner or L0 updates it. Each box gates only its own task or commit (O-1 Task 7 Step 5 / C5 and the new-copy pointers; O-2 Task 5 / C4; O-3 the demo `.env`; O-4 Task 8 / C6; O-5 §6a; O-6 Task 10 Step 2 / C7; O-7 §8 Edit 5). The remaining tasks run without them.

| # | Decision | Recommendation | Signed |
|---|---|---|---|
| O-1 | Publish the ledger-gated copy at `docs/capstone-report/asclexis-showcase-{FREEZE_DATE}.html`; the 2026-09-25 page stays byte-identical | yes | ☐ ______ date ______ |
| O-2 | Add the §8 scope-note text to `CS4610_Report_Demo/README.md` (Edits 1–4, 6) | yes | ☐ ______ |
| O-3 | Demo clone only: set `DEBUG=false` in the untracked `src/backend/.env`, plus `HF_HUB_OFFLINE=1` and Wi-Fi off during the demo | yes (the safe default without it: hidden backend window, browser-only sharing) | ☐ ______ |
| O-4 | Package review evidence into `docs/reviews/` (location answered 2026-10-10, SHOWCASE-O4 `owner-decisions-2026-09-27.md:122`: "Yes, docs/reviews/"; SHOW-O4 `owner-decisions-2026-09-27.md:310` answered 2026-10-20 (L0 AskUserQuestion): "(B) TSV + Codex + script (Recommended)"; the box below is not ticked here): (A) `reviewer-log.tsv` only, or (B) the TSV + Codex outputs + `review.sh` + prompt template | B (makes M6 reproducible; avoids repeating audit addendum A-5) | ☐ A ☐ B ☐ neither |
| O-5 | Add outline §6a (2026-09-27 reconciliation) with the `CASE-STUDY` verdict only. Gates §4.1 / the §6a insertion. Answered yes 2026-10-20, so §6a is inserted; M6 is `CASE-STUDY` since SHOW-O4 (B) | yes | ☐ ______ |
| O-6 | Claim freeze passed (§10) for the showcase on ______ | — | ☑ 2026-10-22 — the owner's conditional sign-off (owner-decisions row O-6, prompt 30: "Freeze now; sign if all pass") is met: §10 checks 1-11 all pass at tip `75c1106` (measurement ref `a16dd51`), §15.1 third pass; independent reviews #210 comments 6345517807 (round 1, REVISE) and 6345850792 (round 2, PASS). Recorded by L0, not signed by an agent on its own judgement. |
| O-7 | Add the submission-date inconsistency note (§8 Edit 5) | owner's call | ☐ yes ☐ no |

## 14. Commit plan

Worktree `/mnt/e/Programming/Github Repo/hc-f-9` (RUNBOOK §3 claim), branch `docs/f-9-showcase-delta`, draft PR #210 (title `[claim:claude:noslot] F-9 showcase-delta`: do not retitle, do not mark ready). Never `git add -A` or `git add .` (C-GATE-3). Before each commit: `git diff --cached --name-only` must print exactly the listed paths.

| # | After | Message | Pathspec (exact) |
|---|---|---|---|
| C0b | before Task 1 (ungated) | `docs: reconcile the showcase plan with the 2026-10-20 sign-offs and the Codex plan review (F-9)` | `docs/plans/2026-09-27-senior-report-showcase-plan.md` |
| C1 | Task 2 | `docs: add claims-ledger rows for the showcase claim audit` | `docs/capstone-report/claims-ledger.md` |
| C1b | after Task 2 and Task 1 Step 9 (ungated); reused for the §15 record after Task 10 Step 1 | `docs: record the showcase evidence pass and the pre-freeze rehearsal in the plan (F-9)` | `docs/plans/2026-09-27-senior-report-showcase-plan.md` (the plan only) |
| C2 | Task 3 | `docs: update the report outline for the stakeholder showcase` | `docs/capstone-report/report-outline.md docs/capstone-report/README.md` (+ `docs/INDEX.md docs/_link_graph.json` only if Task 3 step 4 regenerated them) |
| C3 | Task 4 | `docs: show both external-runner callers in the integration diagram` | `docs/capstone-report/architecture-overview.md` |
| C4 | Task 5 (O-2, O-7) | `docs: add coursework scope notes for claims found false on re-check` | `CS4610_Report_Demo/README.md` |
| C5 | Task 7 (O-1) | `docs: add the ledger-gated showcase copy` | `docs/capstone-report/asclexis-showcase-{FREEZE_DATE}.html` |
| C6 | Task 8 (O-4) | `docs: package the 2026-09-27 review log as case-study evidence` | the files O-4 names under `docs/reviews/` + `docs/capstone-report/claims-ledger.md` |
| C7 | Task 10 Steps 2-3 (O-6, 2026-10-22) | `docs: record the showcase claim freeze` | `docs/plans/2026-09-27-senior-report-showcase-plan.md` |

Example (C1):

```bash
cd "/mnt/e/Programming/Github Repo/hc-f-9"
git add docs/capstone-report/claims-ledger.md
git diff --cached --name-only        # expect exactly: docs/capstone-report/claims-ledger.md
git commit -m "docs: add claims-ledger rows for the showcase claim audit" -m "Rows C11-C30, H12-H18, M4-M8; M1 evidence extended. Evidence re-run at <SHA>." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

PR: #210 is already open as a draft from the claim. Update its body (measurements, files changed, owner stops reached and skipped tasks, one next action); never `gh pr create` a second PR.

## 15. Execution record (filled by the executor)

Pre-freeze run 2026-10-20, not the O-6 freeze. Branch tip after `git merge origin/main` = `c529d19` (the measurement ref); worktree `/mnt/e/Programming/Github Repo/hc-f-9`; interpreter `~/venvs/asclexis-311/bin/python` (Linux, Python 3.11, SQLCipher present) via `scripts/pyslot.sh`.

| Item | Value | Command | Environment |
|---|---|---|---|
| `{SHA}` / `{FREEZE_DATE}` | `c529d19` / 2026-10-24 (pre-freeze 2026-10-20) | `git rev-parse --short HEAD` | WSL |
| `{COLLECTED}` / `{INTERP}` | 2011 (1992 before the merge; contracts §d delta from 1945: +66) / Linux Python 3.11 | `pytest tests/ --collect-only -q -p no:cacheprovider` in `src/backend` | HF_HUB_OFFLINE=1 |
| inventory | routers 18, pages 16, process skills 32, domain skills 4, golden 74, features 27 (19 completed, 7 pending, 1 in progress), CI jobs 8, recovery card mounted `SettingsPage.tsx:943` | Task 1 Step 3 commands | same at `43950de` and `c529d19` |
| authorship + eras (`c529d19`) | 1459 commits; author name `Claude` 263 (18.0%); author or co-author trailer 1042 (71.4%); E0 2/0/0, E1 62/0/27, E2 34/0/1, E3 9/0/0, E4 230/222/222, E5 17/17/17, E6 65/24/58, E7 (Oct 1-20) 1040/0/717; since 2026-06-23 263/1352; Dec-May 98/0 with 28 trailers; first commits: 2 (second adds 14,397 lines in 70 files); P1 merged 2026-09-29 (#21) and 2026-10-01 (#24) | Task 1 Step 4 | counts are commits, merges included |
| harness dates (H13) | docs_lint 2026-02-12 `e1c1b29`; security_gate 2026-02-22 `ae2e9ea`; CLAUDE.md 2026-06-13 `ee8bd33`; skills 2026-06-23 `caacd93`; agent_eval_gate 2026-06-24 `1571927`; .claude/skills 2026-07-01 `9169c3e`; feature_list 2026-07-07 `ddad453`; routes.py 2026-07-30 `7c90afd`; recurring-failures 2026-08-04 `7e985e6` | Task 1 Step 5 | unchanged from H13 |
| ledger / matrix tallies | ledger 64 rows, no `?`: `{VERIFIED 40, PARTIAL 10, CONTRADICTED 6, NOT-EVIDENCED 3, CASE-STUDY 4, HYPOTHESIS 1}` (REPORTED 0; measured 2026-10-20T11:45-07:00 after C6 moved M6 to CASE-STUDY) after review round 1 added H19-H21, C31-C32, M10-M11 (row M11 is the tally the page shows) (before this run: 24 rows `{VERIFIED 7, PARTIAL 6, CONTRADICTED 6, NOT-EVIDENCED 2, CASE-STUDY 2, HYPOTHESIS 1}`; after C1: 56 rows `{VERIFIED 32, PARTIAL 10, CONTRADICTED 6, NOT-EVIDENCED 3, CASE-STUDY 3, HYPOTHESIS 1, REPORTED 1}`; after M9: 57 rows `{VERIFIED 33, PARTIAL 10, CONTRADICTED 6, NOT-EVIDENCED 3, CASE-STUDY 3, HYPOTHESIS 1, REPORTED 1}`, no `?`); matrix 78 rows: 3 enforced, 36 tested, 6 implemented, 17 partial, 12 gap, 1 contradicted, 2 owner-gated, 1 unknown (the matrix's own scorecard paragraph still shows 32/18/15) | Task 1 Step 6; `scorecard_count.py` | Linux |
| review-log counts + time | 51 rounds, all `codex`, all `rc=0`; P04 4, P08 4, S01 3, W01 4, W02 4, W03 4, W04 4, W05 2, W06 3, W07 2, W08 4, W10 4, W11a 4, W11b 4, RTN 1; counted 2026-10-20T11:43-07:00 (59 `*-codex.txt` present) from `docs/reviews/2026-09-27-swarm/reviewer-log.tsv` (reproduces the 09-27 snapshot); M6 is `CASE-STUDY` (SHOW-O4 B); missing option-B files: `review.sh`, `review-prompt-template.md` | Task 1 Step 7 | the log reached `docs/reviews/` by `1843ca3` |
| security gate rc | `ERROR: Could not parse bandit report '/nonexistent.json': ...` then `rc=2` | Task 1 Step 8 | `c529d19` |
| phases merged | W-1, W-2, W-3, W-4, W-5, W-6, W-8, W-10, W-11a PR-4, P2, S-1, P5, P6 (report-only) merged; W-7 and W-11b not; `written new` count in the coursework README = 1; post-P1 ancestry ok (row M9) | Task 0 Step 2 | `git merge-base --is-ancestor` |
| Task 1 Step 9 citation pass | 149 quoted `showcase:N` citations checked: 122 matched by script, 27 by hand (data arrays and split markup); 35 unquoted rows read by hand; all held. Code pointers: most `file:line` cites in §3.1/§9.1 had moved (for example `core/database.py:46` now reads `settings.sql_echo`; recurring-failures headings moved to 12 entries); the page re-anchors each pointer it keeps | script + `sed -n` | `c529d19` |
| Task 2 Step 3 | C12, C15, C28 had changed state (W-8, S-1, W-4) and were written to the current state; H15 is resolved; M4 is 3 of 78; see §9.4 | per-row commands | `43950de` then `c529d19` |
| checker | `OK: 547 claim elements, 0 unmapped, 0 disallowed`, rc=0 after C6b (the M11 `reported` chip was dropped; 548 before; 548 after review round 2 (544 after round 1; after review round 1: the checker now also reads h2-h4 and button text and accepts `data-kind="current"` for the VERIFIED/PARTIAL half of a finding row; it was 458 before); five breaks, all RED on the final page: (a) `no ledger row or verdict: C999` rc=1, (b) `unmapped: 'Memory & session history are labeled'` rc=1, (c) `disallowed: H4=CONTRADICTED kind=None` rc=1, (d) `external URL present` rc=1, (e) heading `Scored on 6 axes` with no ledger tag: `unmapped: 'Scored on 6 axes'` rc=1, (f) the fixed half of a finding row retagged H4: `disallowed: H4=CONTRADICTED kind=current` rc=1 | Task 7 Steps 2-3 | `/tmp/claude-1000/showcase_claims_check.py`, not committed |
| Task 6 Step 5 browser check | Headless Chromium 1200 (`~/.cache/ms-playwright`) driven over CDP by a scratch script (`/tmp/claude-1000/browser_check.py`, not committed), `file://` URL. Phone 375 px: `scrollWidth` 375 = `innerWidth`; desktop 1280 px: 1265 <= 1280, so no horizontal scroll. Path toggle: Agent shows lane 0 only, Legacy shows lane 1 only. Severity filter rows: All 13, P1 5, P2 7, P3 1. Console errors and warnings at both widths: none | Task 6 Step 5 | WSL Linux |
| Review round 1 (Codex/Opus REVISE, 1 MAJOR + 8 MINOR) | MAJOR confirmed: five claims were tagged to rows that say otherwise (H2, H4, C7+M9, H9, H7). Fix: appended rows H19 (gate rc=2), H20 (2011 collected), H21 (utcnow 0 non-test lines), C31 (scheduler started, `main.py:82-83`), C32 (backup scheduler `skipped_locked`), M10 (8 + 14 plans), M11 (ledger tally); retagged each page claim; H4/C7/H9 stay only on the "was" half of each finding; the 12-modes card and 12 failure cards use H14. MINORs: C14/C23/C28 cites labelled "lines at `c529d19`"; headings and buttons now checked, tally chips tagged M11 (64 rows); outline cites M9 and the stale "dated in §15" wording is replaced; capstone README matrix cell now 78 rows / 3 enforced (M4); diagram caption says its cites are at `c529d19`. Not done: `CS4610_Report_Demo/README.md:81` (O-2 text, dated `40f590e`, still describes the non-production redaction bypass that W-6 removed) is owner-signed text and is left to L0 or the owner | review log | |
| Review round 2/3 (REVISE, 1 MAJOR + 3 MINOR) | MAJOR confirmed: the two `fixed in P1` clauses (showcase :546, :629) sat under H4 (`CONTRADICTED`); each is now a `data-kind="current"` span tagged H19. MINOR retags, each checked against its row: E6 order corrected to branches B then A (M9: B 2026-09-29, A 2026-10-01) and tagged H12 M9; `documents.py:658,760` retagged C13 (C2 says 655,757); `assistant.py:839` added to C14; the two external-runner callers (`assistant.py:867`, `interpretations.py:522`) added to C10; the backup-fix count tagged H12 H18; `8 + 14` tagged M9 M10; "done 2026-09-27" replaced by M4's "3 of 78 rows enforced"; "linted in CI" added to H14 (`ci.yml:30`). Plan Task 7 now carries the current checker and breaks (e) and (f) | grep + per-row read | `c529d19` |
| Known checker gap | The checker validates ledger IDs and verdict classes only, not values. Second loophole: `kind=finding` accepts CONTRADICTED for any text in the element, including a "now fixed" clause; that let two "fixed in P1" clauses through under H4 until review round 2. Mitigation: read every `data-kind="finding"` element for a present-tense clause and wrap it in a `data-kind="current"` span. `kind=current` allows the same verdicts as the default, so break (f) is a variant of (c), not a new test. A wrong figure under a correct ID passes (the round-1 MAJOR was of this kind). Values are checked by a read against the cited row and by the §10 freeze rehearsal | Task 7 | |
| demo checks 1-11 + dry-run | not run (Task 9 is the owner's, Windows) | | |
| freeze checklist (rehearsal) | 1 OK 544/0/0 (re-run after review round 1); 2 word grep: hits are quotes or rows `VERIFIED`/`PARTIAL` with scope stated (C2 "verified values only", C3/C19 "every" with the row's scope, C10 "All inference is local by default", C25, M4 "3 enforced"); "across every import" was reworded; 3 numbers in this table; 4 every planned item sits beside "merged #N" or "proposed"; 5 owner-gated list is a pointer to matrix GATED-01...05 (S1-A/B, OQ-1, Q-FC, Q-HASH are answered in owner-decisions); 6 `grep -ci hipaa` on the page, the coursework README and the outline: 0; 7 findings carry `data-kind="finding"`; 8 not run; 9 docx/pdf diff: empty; 10 `unchanged`; 11 `docs_lint` passed, `generate_docs_index.py` regenerated, `test_docs_lint.py` 7 passed | Task 10 Step 1 | `c529d19` plus doc commits |

### 15.1 Freeze run 2026-10-22 (O-6, prompt 30: "Freeze now; sign if all pass")

Run by claude opus (F-9 executor, L0 session 2026-10-22), on the GPU box (WSL Linux), local time late 2026-10-21 PDT = 2026-10-22 UTC. `FREEZE_DATE` = 2026-10-22 (O-6 row, `owner-decisions-2026-09-27.md:374`). **Freeze SHA `a16dd51`** = `git merge origin/main` into the branch (origin/main = `c97192d`, 361 commits brought in, no conflict; `docs/INDEX.md` and `docs/_link_graph.json` were fresh after the merge). Every figure below is measured at `a16dd51`. The branch's own remote had two commits the worktree lacked (`b0a2886` C6, `d19050d` C6b, pushed 2026-10-20 by another session under SHOW-O4 B); they were merged after the freeze commits (`0478d96`, one conflict in ledger M9-M11, resolved by keeping both edits). `git diff --name-only a16dd51 HEAD` lists only `docs/` files, so the code and the git-history figures measured at `a16dd51` hold for the tip; the checks below ran at the tip `0478d96` and this record's commit. Commit `1679bb6` (C1) also carries the `git mv` rename of the page, which was staged before the ledger commit; the page's content edits are `8ac292c` (C5). The rehearsal record above stays as written. This run is not a signature: O-6 counts as signed only if checks 1-11 all pass, and check 8 did not run.

| Item | Value at `a16dd51` | Command | Environment |
|---|---|---|---|
| `{SHA}` / `{FREEZE_DATE}` | `a16dd51` / 2026-10-22; origin/main `c97192d` | `git rev-parse --short HEAD`; `git rev-parse origin/main` | WSL |
| `{COLLECTED}` / `{INTERP}` | **2328** collected in 26.56s, rc=0 (CLAUDE.md slot 2291: +37; pre-freeze `c529d19`: 2011) / Linux Python 3.11 (`~/venvs/asclexis-311`), `sentence-transformers` 6.1.0 and `sqlcipher3` importable | `cd src/backend && "$(git rev-parse --show-toplevel)/scripts/pyslot.sh" env HF_HUB_OFFLINE=1 ~/venvs/asclexis-311/bin/python -m pytest tests/ --collect-only -q -p no:cacheprovider` after clearing `__pycache__` | HF_HUB_OFFLINE=1; collected count only, no pass count |
| inventory | routers **19** (was 18; `donation_router` added), pages 16, process skills 32, domain skills 4, golden 74, features 27 (19 completed, 7 pending, 1 in_progress), CI jobs **9** (was 8; `rsi-replay` added by `c475ba6`; the job grep prints 10 because `push:` matches, the `jobs:` block lists 9), recovery card `SettingsPage.tsx:945` (was :943), 12 recurring-failure headings | Task 1 Step 3 commands | `a16dd51` |
| authorship + eras | **1847** commits; author name `Claude` **361 (19.5%)**; author or co-author trailer **1292 (70.0%)**; E0 2/0/0, E1 62/0/27, E2 34/0/1, E3 9/0/0, E4 230/222/222, E5 17/17/17, E6 65/24/58, **E7 (Oct 1-21) 1428/98/967**; the 98 E7 commits by author name are dated 2026-10-20 (47) and 2026-10-21 (51); since 2026-06-23 361/1740; Dec-May 98/0 with 28 trailers; first commits 2 (second: 70 files, 14,397 insertions) | Task 1 Step 4 (E7 window 2026-10-01..2026-10-31; latest author date 2026-10-21) | counts are commits, merges included |
| harness dates (H13) | unchanged: docs_lint 2026-02-12 `e1c1b29`; security_gate 2026-02-22 `ae2e9ea`; CLAUDE.md 2026-06-13 `ee8bd33`; skills 2026-06-23 `caacd93`; agent_eval_gate 2026-06-24 `1571927`; .claude/skills 2026-07-01 `9169c3e`; feature_list 2026-07-07 `ddad453`; routes.py 2026-07-30 `7c90afd`; recurring-failures 2026-08-04 `7e985e6` | Task 1 Step 5 | `a16dd51` |
| ledger / matrix tallies | ledger at `a16dd51`: 64 rows `{VERIFIED 40, PARTIAL 10, CONTRADICTED 6, NOT-EVIDENCED 3, CASE-STUDY 3, HYPOTHESIS 1, REPORTED 1}`; after merging C6 (`0478d96`): 64 rows `{VERIFIED 40, PARTIAL 10, CONTRADICTED 6, NOT-EVIDENCED 3, CASE-STUDY 4, HYPOTHESIS 1}`, no `?` (the page chips show the second); matrix: `78 requirement rows: 3 enforced · 36 tested · 6 implemented · 17 partial · 12 gap · 1 contradicted · 2 owner-gated · 1 unknown` | Task 1 Step 6; `scorecard_count.py` | Linux |
| review-log counts | 51 rows, 51 `codex`, 51 `rc=0`; P04 4, P08 4, RTN 1, S01 3, W01 4, W02 4, W03 4, W04 4, W05 2, W06 3, W07 2, W08 4, W10 4, W11a 4, W11b 4; counted 2026-10-21T22:32-07:00 | `cut -f2 \| sort \| uniq -c`; `cut -f4`; `cut -f5` on `docs/reviews/2026-09-27-swarm/reviewer-log.tsv` | same as C6's count |
| security gate rc | `ERROR: Could not parse bandit report '/nonexistent.json': [Errno 2] No such file or directory: '/nonexistent.json'` then `rc=2`; `security_gate.py` unchanged since `c529d19` | Task 1 Step 8 | `a16dd51` |
| phases merged | W-1, W-2, W-3, W-4, W-5, W-6, W-8, W-10, W-11a PR-4, P2 merged; P1 `9b9958c` `ee7c358`, S-1 `040cf8c`, P5 `98bd3c7`, P6 report-only `c581a61` ancestors; `post-P1-ok`; no W-7 or W-11b merge commit; `written new` count 1; `datetime.utcnow` non-test lines 0; `pragma foreign_keys` only the two comments (`api/profiles.py:940`, `scripts/backup.py:580`) | Task 0 Step 2 and the M9/H21 commands | `a16dd51` |
| page code pointers | `api/documents.py:408,658,760,830,931`, `api/interpretations.py:522`, `api/profiles.py:940`, `core/auth.py:315-341`, `main.py:82-83`: same text as at `c529d19`. Moved: `api/assistant.py:839` → **:842** (`@router.post("/chat"...)`) and `:867` → **:870** (`from core.external_runner import get_runner_for_request`), from the 3 lines added at `:220-227` | `sed -n` at both SHAs | page, C10 and C14 updated |
| other page facts re-read | 12 recurring-failure quotes all present in `recurring-failures.md` (script, whitespace-normalised); 8 tools in `tools/registry.py:53-62`, `MAX_STEPS = 5`, `AGENT_ENABLED_DEFAULT = True`; `consistency_score = 1.0` at `modules/faithfulness.py:134` (file unchanged); HC-M11 NLI is now built behind `use_llm_entailment: bool = False` (`core/config.py:166`), so "approved only behind a default-off flag" still holds; `fix(backup)` 3/6/3 on 2026-07-29/30/31; `api/profiles.py`, `api/documents.py`, `api/observations.py` unchanged since `43950de` (C19 counts hold); Ollama default `127.0.0.1:11434`. Matrix KEY-05 now reads "owner-approved 2026-10-19 (P8-B2 B + A) … not yet implemented", so the page's owner-gated note no longer lists DEK rotation as owner-gated | `grep`/`sed -n` | `a16dd51` |
| changes made | page renamed `asclexis-showcase-2026-10-24.html` → `asclexis-showcase-2026-10-22.html` (O-1 copy at `{FREEZE_DATE}`); outline and capstone README links updated; page figures: hero 19.5% (361/1847, 70% with trailers), stats 2,328 / 19 routers / 9 CI jobs / 1,847 commits, §07 361 of 1,740, E4 "230 of 1847", E7 "Oct 1–21", 98/1428 and 967/1428 with bar 7% and the text "mostly as a co-author trailer; as git author only from 2026-10-20", lifetime bar 80.5/19.5, gate "measured 2026-10-22", assistant cites :842/:870, meta and footer name the freeze; owner-gated note: DEK rotation moved out of the owner-gated list ("owner-approved (2026-10-19) and not implemented", KEY-05). Ledger: C10, C14, H12, H14, H19, H20, M4, M9, M10, M11 re-measured at `a16dd51`; no verdict changed. Outline: the E7 sentence ("only as a co-author trailer") now matches H12. Not edited: `owner-decisions-2026-09-27.md:308` (SHOW-O1 quotes the old file name verbatim), `docs/plans/2026-10-15-build-program/queue.md` and `lane-F-docs-owner-wearables.md` (old name; not this plan's files) | | |

**§10 checks at the tip (`0478d96` plus this record):**

| # | Check | Command | Output | Result |
|---|---|---|---|---|
| 1 | Every claim has a ledger row | `python3 /tmp/claude-1000/showcase_claims_check.py docs/capstone-report/asclexis-showcase-2026-10-22.html; echo rc=$?` (the scratch checker survived; `diff` against the Task 7 Step 1 block: identical) | `OK: 547 claim elements, 0 unmapped, 0 disallowed` `rc=0` (548 at `8ac292c`, before C6b dropped the `reported` chip). Breaks on scratch copies, all RED: (a) `no ledger row or verdict: C999` rc=1; (b) `unmapped: 'Memory & session history are labeled'` rc=1; (c) `disallowed: H4=CONTRADICTED kind=None` rc=1; (d) `external URL present` rc=1; (e) `unmapped: 'Scored on 6 axes'` rc=1; (f) `disallowed: H4=CONTRADICTED kind=current` rc=1 | PASS |
| 2 | No status word stronger than the ledger | `grep -n -i -o -E "\b(verified\|proven\|guarantee[sd]?\|never\|always\|every\|all\|complian[a-z]*\|hipaa\|secure[sd]?\|enforced\|fully\|100%)\b" <page> docs/capstone-report/report-outline.md` | 32 page hits, 10 outline hits. Page: quotes and headings under H14 (`VERIFIED`): :507, :508, :513, :515 ×2, :516 ×3; H13 `VERIFIED` :496 ("never assert it", a quote); C4 `VERIFIED` :272, :435 ("no test can prove "never""); C25 `VERIFIED` :329, :465 ("never the master DB/session"); M4 `VERIFIED` :612, :625 ("3 enforced", file name); M9 `VERIFIED` :587 (plan-scope name); M11 `VERIFIED` :627 ("40 verified" chip); `PARTIAL` rows, each word inside the row's verified scope: C2 :249, :254, :354 ("verified values only" / "verified flag" name the data state C2 gates; C2's not-gated paths are not claimed there), C3 :272 ("a source to every sentence" is the agent-path half C3 verifies), C19 :303 ("every document route is audit-logged": documents 13/13), C10/H11 :364 ("All inference is local by default" = C10's "true by default"); :198 and :639 "every claim … maps to a row" = check 1's output; :557 nav button `All` (exempt), :599 and :622 file names (exempt), :660 JavaScript. Outline: file names `specs-compliance-matrix.md` (:23 ×2, :30 ×2, :93 ×3), :22 "verified current state" (architecture-overview label), :30 "3 of 78 rows `enforced`" (M4), :35 "all on 2026-10-20 or later" (H12 measurement). No hit whose row is not `VERIFIED` makes a claim beyond that row's verified part; same reading as the rehearsal (L0 note below) | PASS |
| 3 | Numbers re-measured, with command and environment | the table above | every page number is in the table above or in the rehearsal table with its row (historical dated figures: 101/109/30 utcnow on 2026-09-27, 620/1160/1245, 14,397/70, 12 `fix(backup)`, L3/L4, 3 and 4 errors, 6 agents, 8 + 14, "9 of 13" profile routes, 13/13 documents) and was re-read at `a16dd51`; changed figures were updated; the collected count names its interpreter, SQLCipher and `sentence-transformers`; no pass count is shown | PASS |
| 4 | Planned ≠ implemented | `grep -n -E "\b(P[2-8]\|W-[0-9]+a?b?\|S-1\|G-[ABC][0-9])\b" <page>` | phase hits :437 (W-4, C28), :565 (P2 #31), :567 (P5 #54), :568 (S-1 #29), :569 (W-8 #168), :570 (W-4 #72), :573 (P6 #113, report-only), :576 (P8 "owner-gated"), :583-:595 each "merged #N" (W-11a "PR-4 merged #39; other parts not checked here"), :596-:597 W-7 and W-11b "proposed — not merged", :610 "W-7 and W-11b not"; P2/P3 at :559-:576 are severity labels. Every "merged" has `git merge-base --is-ancestor <commit> a16dd51` exit 0 (phases-merged row) | PASS |
| 5 | Owner-gated items named as such | read `<page>:599` | "Owner-gated and not implemented: MFA / step-up re-auth, penetration-test scope, audit retention, HC-M11 production scoring. DEK rotation is owner-approved (2026-10-19) and not implemented. See GATED-01…05 and KEY-05 in specs-compliance-matrix.md." the other §10 item-5 gates are answered in `owner-decisions-2026-09-27.md` (S1-A + S1-B `:33`, W-4 OQ-1 `:84`, W-2 O-2 `:85`, W-8 Q-FC `:221`, W-3 O-5 `:234`, W-8 Q-HASH `:235`), so the page does not list them as unsigned (same as the rehearsal); of the P8 briefs only Brief 2 has an answer (`:297`); G-C1/G-C3 sit under W-11b "proposed — not merged" | PASS |
| 6 | No legal or HIPAA-compliance claim | `grep -n -i "hipaa" <page> CS4610_Report_Demo/README.md docs/capstone-report/report-outline.md; echo "rc=$?"` | no lines, `rc=1` | PASS |
| 7 | Findings stay findings | check 1's checker (it rejects a `CONTRADICTED`/`NOT-EVIDENCED` row outside `data-kind="finding"`) | `0 disallowed`; the `CONTRADICTED`/`NOT-EVIDENCED` rows on the page (C7, H4, H6, H9, H10, M3) sit only on `data-kind="finding"` elements; break (c) proves the rule fires | PASS |
| 8 | Demo matches the page | needs the Task 9 dry-run record (§6.3 check 11) | not run: the owner's Task 9 dry-run record is missing (the rehearsal row "demo checks 1-11 + dry-run" still says not run); no dry run was run or invented in this session | **NOT RUN** |
| 9 | Coursework untouched | `git diff --name-only origin/main...HEAD -- 'CS4610_Report_Demo/*.docx' 'CS4610_Report_Demo/*.pdf' \| wc -l` | `0` | PASS |
| 10 | Old showcase untouched | `git diff --quiet origin/main -- audit/2026-09-25/asclexis-showcase.html && echo unchanged` | `unchanged` | PASS |
| 11 | Docs gates | `python3 scripts/docs_lint.py; echo lint_rc=$?`; `python3 scripts/generate_docs_index.py --check; echo rc=$?` | after `python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py --link-graph` (regen=0, `docs/INDEX.md` unchanged by this record): `Docs lint passed.` `lint_rc=0`; `docs/INDEX.md and docs/_link_graph.json are fresh.` `rc=0` (`test_docs_lint.py` not re-run: no lint code changed) | PASS |

**Result: 10 of 11 checks pass; check 8 NOT RUN.** O-6's condition ("only if §10 checks 1-11 all pass at the freeze SHA") is therefore not met, so O-6 is not signed by this run and, per the O-6 row, F-9 stops here and goes back to the owner. C7 is not committed. §13's Signed column is untouched.

**Second pass, 2026-10-22 (after the check-8 input arrived).** The first pass above stopped at check 8. The owner then answered prompt 31 O-6-CHECK8, "L0 dry-runs on the GPU box" (owner-decisions row O-6-CHECK8, #282 `5f8a1c4`; L0 ruling PR #210 comment 6333827614), and L0 posted the dry-run record as PR #210 comment 6334394792 (app at `main@c97192d`, Ollama `gemma4:e4b`, `HF_HUB_OFFLINE=1`, 0 non-localhost requests, synthetic PDFs in layout A2). L0 also ruled that check 2 takes the literal reading. This pass merged origin/main `7ffc55f` (`195b23d`; it changes only `owner-decisions-2026-09-27.md` and three build-program files), reworded the plan §6 and the page, and re-ran checks 1-11 at the tip. **Measurement ref (check 3):** the figures stay as of `a16dd51`. `git diff --name-only a16dd51 HEAD` lists only `docs/` files (no code, test, CI or script file), so the code and test figures (2328 collected, 19 routers, 9 CI jobs, the code pointers) are unchanged at the tip. The git-history figures (1,847 commits, 361 / 1292, E7 1428/98/967) count history up to `a16dd51` and say so on the page (the hero, the §07 text, the legend and now the footer: "figures are as of the measurement ref a16dd51"). The later docs-only commits are not counted.

Check 8 input, the five steps whose result differed from their "says" line and what this pass did (plan §6, this commit):

| Record item | Recorded result | Change |
|---|---|---|
| 1 F-EXTRACT fallback to Demo Backup | no profile picker; `/` opens `/setup`; only `/recover` (pick profile, recovery code, new password) opens an existing profile, 5.1 s, and it issues a new recovery code; sessions last 1 hour | §6.4 F-EXTRACT reworded: keep Demo Backup signed in in a second window prepared within the hour, or use `/recover` with the code prepared beforehand, which replaces the code |
| 2 5:00 Trends | after Verify nothing is unverified, so no point is marked; the before-W-3 line is false (W-3 merged #136); page opened on CRP with the "CBC 0" tab highlighted | "says" reworded to what is shown ("Each value on this chart is one you just confirmed"); both W-3 lines cut; "does" adds "select the analyte by name" |
| 3 5:45 Ask again | Q1 lists both HbA1c values (5.9 % Mar 02, 6.1 % Jun 01), 2 source chips, "2/2 claims verified"; Q2 (metformin) returned the fixed escalation text on the default agent path, not the abstain text; legacy path not exercised; header badge `BioMistral-7B` while `ollama ps` was empty | "says" reworded: lists both results with sources; "declines and refers you to your doctor or pharmacist"; the legacy-path narration is cut (not exercised); the badge goes to §6.1 rule 7 (do not point at it) |
| 4 8:15 Delete | outcome matched; the form also needs "Back up and download" or the "I confirm I have a copy…" checkbox, and the password | "does" now lists the backup/checkbox, the password, the phrase and the button; "says" unchanged (outcome matched) |
| 5 9:45 Close | C13, C14, C19, C21, C24, C29, C30 exist only on the F-9 branch until #210 merges | "does" opens the ledger from the merged PR or the branch, not `main`; "says" reworded to "Each step you saw names a row in this ledger" (no claim about `main`) |
| hazards (6) | stale "Documents needing attention … parsed" panel after Mark All Verified until reload; "Click any value to edit" but only the pencil works; Settings holds External API and model tiers; `DEBUG=true` serves `/docs`; export page has CSV/JSON/doctor-summary/FHIR buttons; two `database is locked` errors on `INSERT INTO audit_logs` near Settings loads | §6.1 rule 6 extended (export buttons, Settings, `/docs` as discipline) and new rule 7 (recorded, not fixed); step 4:00 "does" adds the pencil and the reload |
| PDF layout | `1970-01-01` DOB parsed as the collection date; borderless/plain layouts missed CRP; A2 (ruled table, DOB "1 January 1970") gave 4/4 per file | §6.1 rule 1 names the A2 layout |

Steps that matched (0 Frame, 1 Create profile, 2 Upload, 3 Ask before verifying, 4 Verify, 7 Export, 9 Harness) keep their "says" lines; step 3's line now quotes the recorded text. Page claims: the record's spot checks found no page claim contradicted; the page makes no claim about the Trends markers, the advice template, the delete form, the profile picker or which branch holds the ledger, so no page change was needed for check 8.

Check 2 under the literal reading (page, `2d1ee27`; outline, `fa14d74`): the hits on rows that are not `VERIFIED` were reworded, with no verdict changed. C2: "use verified values only" (×2) → "use only values the patient has confirmed"; "verified flag on every observation" → "a confirmation flag (`user_verified`) on each observation". C3: "a source to every sentence" → "to each drafted sentence"; "no test can prove "never"" (same element) → "tests cannot prove the language is absent". C19: "every document route" → "the 13 document routes". C16/C2: "never the master DB" → "not the master DB". C10/H11: "All inference is local by default" → "Inference is local by default". Untagged: tagline "every claim … maps to a row" → "claims … map to rows (checked by script)"; footer "Every claim maps" → "Claims map"; pointer "every report claim" → "each report claim". Outline: "verified current state" → "current state"; "all on 2026-10-20 or later" → "dated 2026-10-20 or later".

**§10 checks at the tip (`fa14d74` plus this record; origin/main `7ffc55f`):**

| # | Check | Command | Output | Result |
|---|---|---|---|---|
| 1 | Every claim has a ledger row | `python3 /tmp/claude-1000/showcase_claims_check.py docs/capstone-report/asclexis-showcase-2026-10-22.html; echo rc=$?` | `OK: 549 claim elements, 0 unmapped, 0 disallowed` `rc=0` (549: the new `<code>user_verified</code>` adds 2 text nodes, the "every" pointer rewording none). Breaks on scratch copies: (a) `no ledger row or verdict: C999` / `FAIL: 549 claim elements, 0 unmapped, 2 disallowed` rc=1; (b) `unmapped: 'Memory & session history are labeled'` / `FAIL: 549 …, 2 unmapped, 0 disallowed` rc=1; (c) `disallowed: H4=CONTRADICTED kind=None` / `FAIL: 549 …, 0 unmapped, 3 disallowed` rc=1; (d) `external URL present` rc=1; (e) `unmapped: 'Scored on 6 axes'` rc=1; (f) `disallowed: H4=CONTRADICTED kind=current` rc=1 | PASS |
| 2 | No status word stronger than the ledger (literal reading) | the §10 grep on the page and the outline, then a scratch HTML-parser pass that gives each hit the `data-ledger` rows of its element | page: 20 grep hits (corrected by review 6345517807; this row first said 21). 13 on `VERIFIED` rows only: C4 :435 (no test can prove "never"), C25 :465 ("never the master session"), H13 :496 (quote), H14 :507, :508, :513 and the `<p>` quotes at :515 and :516 ("enforced", "every"), M9 :587 (plan-scope name), M4 :612, :625 ×2, M11 :627 ("40 verified" chip). Not claims: the failure-mode card titles at :515 ("enforced") and :516 ("fully", "never"), which are verbatim `recurring-failures.md` headings on `<h4 data-exempt="navigation">`; :557 nav button `All` (`data-exempt="navigation"`), :599 the file name `specs-compliance-matrix.md` (`data-exempt="pointer"`), :660 JavaScript `'all'` (the grep's :557 second `all` is the button's `data-s="all"` attribute). 0 hits on a `PARTIAL` or other non-`VERIFIED` row. Outline: 8 hits: the file name `specs-compliance-matrix.md` (:23 ×2, :30 ×2, :93 ×2), the row label `Compliance scorecard` (:93; relabelled "Spec-matrix scorecard (M4)" in the third pass) and :30 "3 of 78 rows `enforced`" (M4 `VERIFIED`) | PASS |
| 3 | Numbers re-measured, with command and environment | the measurement table above, as of `a16dd51` | every page number is in that table (or, for the dated historical figures, in the rehearsal table with its row); `a16dd51..HEAD` is docs-only, so no code or test figure moved; the git-history figures are labelled "at a16dd51" on the page; the collected count names Python 3.11, SQLCipher and `sentence-transformers`; no pass count is shown | PASS |
| 4 | Planned ≠ implemented | `grep -n -o -E "\b(P[2-8]\|W-[0-9]+a?b?\|S-1\|G-[ABC][0-9])\b" <page>` | `437:W-4 559:P2 560:P3 565:P2 567:P5 568:S-1 569:P2 569:W-8 570:P2 570:W-4 571:P2 572:P2 573:P2 573:P6 574:P2 575:P2 576:P3 576:P8 583:P2 584:S-1 585:W-1 586:W-2 587:W-3 588:W-4 589:W-5 590:W-6 591:W-8 592:W-10 593:W-11a 594:P5 595:P6 596:W-7 597:W-11b 597:G-C1 597:G-C4 610:W-7 610:W-11b`. P2/P3 in the findings rows and :559-:560 are severity labels. Each phase sits beside "merged #N" (ancestry exit 0 at `a16dd51`, phases-merged row), "report-only … merged #113", "owner-gated" (P8) or "proposed — not merged" (W-7, W-11b, G-C1…G-C4) | PASS |
| 5 | Owner-gated items named as such | `grep -o 'Owner-gated and not implemented[^<]*' <page>` | `Owner-gated and not implemented: MFA / step-up re-auth, penetration-test scope, audit retention, HC-M11 production scoring. DEK rotation is owner-approved (2026-10-19) and not implemented. See GATED-01…05 and KEY-05 in specs-compliance-matrix.md.` The other item-5 gates are answered in `owner-decisions-2026-09-27.md` (S1-A + S1-B `:33`, W-4 OQ-1 `:84`, W-2 O-2 `:85`, W-8 Q-FC `:221`, W-3 O-5 `:234`, W-8 Q-HASH `:235`); G-C1/G-C3 sit under W-11b "proposed — not merged" | PASS |
| 6 | No legal or HIPAA-compliance claim | `grep -n -i "hipaa" <page> CS4610_Report_Demo/README.md docs/capstone-report/report-outline.md; echo "rc=$?"` | no lines, `rc=1` | PASS |
| 7 | Findings stay findings | check 1's checker | `0 disallowed`; break (c) shows the rule fires; the `CONTRADICTED`/`NOT-EVIDENCED` rows on the page (C7, H4, H6, H9, H10, M3) sit only on `data-kind="finding"` elements | PASS |
| 8 | Demo matches the page | read the dry-run record (PR #210 comment 6334394792) against §6.2, §6.4 and the page | the five DIFFERS items and the hazards are reworded or cut in §6 (table above); no §6.2 "says" line now states a result the record contradicts; the matched steps keep their lines; the page claims the record checked held. Not covered by the record: presenter talk time (the record says not measurable there; app-side actions took well under 1 minute) and the T-1 hour repeat (Task 9 Step 5, the owner's) | PASS (the timing and the T-1 hour repeat stay open, as the record says) |
| 9 | Coursework untouched | `git diff --name-only origin/main...HEAD -- 'CS4610_Report_Demo/*.docx' 'CS4610_Report_Demo/*.pdf' \| wc -l` | `0` | PASS |
| 10 | Old showcase untouched | `git diff --quiet origin/main -- audit/2026-09-25/asclexis-showcase.html && echo unchanged` | `unchanged` | PASS |
| 11 | Docs gates | `python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py --link-graph; python3 scripts/docs_lint.py; echo lint_rc=$?; python3 scripts/generate_docs_index.py --check; echo rc=$?` | `regen=0` (INDEX and link graph unchanged by this pass); `Docs lint passed.` `lint_rc=0`; `docs/INDEX.md and docs/_link_graph.json are fresh.` `rc=0` | PASS |

**Result of the second pass: checks 1-11 all pass at the tip, with check 8 judged against the L0 GPU-box dry-run record.** This is not a signature: O-6 stays unsigned until L0 reviews this record, and §13, C7 and the ready state are left to L0. The first-pass table above is kept as the record of that run.

Old file name `asclexis-showcase-2026-10-24.html` still in files outside this plan's list, left for L0: `docs/plans/2026-10-15-build-program/queue.md`, `docs/plans/2026-10-15-build-program/lane-F-docs-owner-wearables.md`, and the verbatim SHOW-O1 question in `docs/capstone-report/owner-decisions-2026-09-27.md:308`.

**Third pass, 2026-10-22 (review 6345517807, REVISE).** The independent review found that check 4 failed on one hit: `:437 (W-4)` had no status beside it. It also raised seven MINORs. origin/main was still `7ffc55f`, so nothing was merged. The measurement ref stays `a16dd51`: `git diff --name-only a16dd51 HEAD | grep -cv '^docs/'` → `0`. Fixes:

1. **Page `:437` (`1154a3d`, C5):** "(W-4)" now reads "(W-4, merged #72 2026-10-16)".
2. **Check 4, literal reading (C5 `1154a3d` and `15f74e9`; C1 `b0c1302`).** Every page phase hit that says merged, fixed or since #N now carries the date of its merge commit:
   - The commands were `git merge-base --is-ancestor <merge> a16dd51` (exit 0 for all 13) and `git log -1 --format=%cs <merge>`.
   - Dates: #29 `040cf8c` 2026-10-01, #31 `cff3827` 2026-10-02, #32 `2f0cb6f` 2026-10-01, #34 `d21c59d` 2026-10-02, #35 `cbabed1` 2026-10-02, #39 `25c993e` 2026-10-06, #53 `6c13045` 2026-10-08, #54 `98bd3c7` 2026-10-09, #72 `cfc1e50` 2026-10-16, #106 `c4b1aa5` 2026-10-16, #113 `c581a61` 2026-10-16, #136 `b45f9cb` 2026-10-17, #168 `26106ee` 2026-10-18.
   - Ledger M9 now carries these dates.
   - The capstone pipeline node (`:610`) reads "most merged 2026-10-01…10-18; W-7 and W-11b proposed, not merged".
3. **§15.1 second-pass check 2 row corrected in place.** It has 20 page hits, not 21. The `:515`/`:516` card titles are `data-exempt="navigation"` headings. Outline `:93` includes the label "Compliance scorecard", now "Spec-matrix scorecard (M4)" (C2 `eea2bbe`).
4. **Stale plan text updated (this commit; no §13 box ticked or signed):**
   - The freeze date is now 2026-10-22 in Task 1 Step 1, Task 10 **Files**, the §13 narrative and the §14 C7 row.
   - The §13 narrative now records O-4 option B as answered (SHOW-O4 `:310`, packaged by C6).
   - §6.1 rule 6 now says the doctor summary is "strict-redacted since W-2, merged #106 2026-10-16; not shown".
5. **Outline `:23` (C2 `eea2bbe`):** "built-but-inert (notifications)" now reads "notifications until P2, merged #31 2026-10-02; the lifespan now starts the scheduler, C31".
6. **Page footer (C5 `1154a3d`):** it now reads "Owner sign-off O-6 is recorded in the showcase plan (§13, §15) and in owner-decisions, not on this page." This stays true whether or not O-6 is signed. The footer has no ledger tag, as before, and check 1 still passes.
7. **Dry-run record:** its Environment row says it read `asclexis-showcase-2026-10-24.html (figures at c529d19)` at `ca0cb3e`. At `ca0cb3e` the page was already `-2026-10-22.html` with figures at `a16dd51`, so that line is stale. Its page spot checks are qualitative (AES-GCM `.bin` files, vault key files, unverified-then-verified, gate rc 2, no model loaded, Trends text), and none of them depends on the file name or on a figure, so check 8 stands.

**§10 checks at the tip (`15f74e9` plus this record; origin/main `7ffc55f`):**

| # | Check | Command | Output | Result |
|---|---|---|---|---|
| 1 | Every claim has a ledger row | `python3 /tmp/claude-1000/showcase_claims_check.py docs/capstone-report/asclexis-showcase-2026-10-22.html; echo rc=$?` | `OK: 549 claim elements, 0 unmapped, 0 disallowed` `rc=0`. Breaks on scratch copies (run at `eea2bbe`; `15f74e9` changes only the `:610` text): (a) `no ledger row or verdict: C999` / `FAIL: 549 claim elements, 0 unmapped, 2 disallowed` rc=1; (b) `unmapped: 'Memory & session history are labeled'` / `FAIL: 549 …, 2 unmapped, 0 disallowed` rc=1; (c) `disallowed: H4=CONTRADICTED kind=None` / `FAIL: 549 …, 0 unmapped, 3 disallowed` rc=1; (d) `external URL present` / `FAIL: 549 …, 0 unmapped, 1 disallowed` rc=1; (e) `unmapped: 'Scored on 6 axes'` / `FAIL: 549 …, 1 unmapped, 0 disallowed` rc=1; (f) `disallowed: H4=CONTRADICTED kind=current` / `FAIL: 549 …, 0 unmapped, 1 disallowed` rc=1 | PASS |
| 2 | No status word stronger than the ledger (literal reading) | `grep -n -i -o -E "\b(verified\|proven\|guarantee[sd]?\|never\|always\|every\|all\|complian[a-z]*\|hipaa\|secure[sd]?\|enforced\|fully\|100%)\b" <page> docs/capstone-report/report-outline.md` | the page has 20 hits and the outline 7 (`grep -c`: 20 and 7). Page hits on `VERIFIED` rows only (13): C4 :435, C25 :465, H13 :496, H14 :507, :508, :513 and the `<p>` quotes at :515 ("enforced") and :516 ("every"), M9 :587, M4 :612 and :625 ×2, M11 :627. Not claims (7): the `<h4 data-exempt="navigation">` failure-mode titles at :515 ("enforced") and :516 ("fully", "never"); :557 the `All` button and its `data-s="all"` attribute (navigation); :599 the file name in a `data-exempt="pointer"` note; :660 JavaScript. 0 hits on a non-`VERIFIED` row. Outline: `specs-compliance-matrix.md` file name at :23 ×2, :30 ×2, :93 ×2, and :30 "3 of 78 rows `enforced`" (M4 `VERIFIED`) | PASS |
| 3 | Numbers re-measured, with command and environment | `git diff --name-only a16dd51 HEAD \| grep -cv '^docs/'` plus the measurement table above | `0`: no code, test, CI or script file changed after `a16dd51`, so the figures measured there hold. The git-history figures are labelled "at a16dd51" on the page, and the footer names `a16dd51` as the measurement ref. The new merge dates come from `git log -1 --format=%cs` (item 2 above) | PASS |
| 4 | Planned ≠ implemented | `grep -n -o -E "\b(P[2-8]\|W-[0-9]+a?b?\|S-1\|G-[ABC][0-9])\b" <page>`, then each line read | every phase hit carries a status. "merged #N date" or "Fixed by/Since/after … (merged #N date)": :437 W-4, :565 P2, :567 P5, :568 S-1, :569 W-8, :570 W-4, :573 P6, :583-:595 (each "merged #N (date)"; W-11a "PR-4 merged #39 (2026-10-06); other parts not checked here"; P6 "report-only orphan audit merged #113 (2026-10-16); enforcement not enabled"). "proposed — not merged": :596 W-7, :597 W-11b, G-C1, G-C4. :610 "W-7 and W-11b proposed, not merged". :576 P8 "owner-gated". The severity labels P2/P3 are at :559-:560 and in the findings rows :565-:576. Every merge commit is an ancestor of `a16dd51` (exit 0) | PASS |
| 5 | Owner-gated items named as such | `grep -o 'Owner-gated and not implemented[^<]*' <page>` | `Owner-gated and not implemented: MFA / step-up re-auth, penetration-test scope, audit retention, HC-M11 production scoring. DEK rotation is owner-approved (2026-10-19) and not implemented. See GATED-01…05 and KEY-05 in specs-compliance-matrix.md.` The other item-5 gates are answered (`owner-decisions` `:33`, `:84`, `:85`, `:221`, `:234`, `:235`) | PASS |
| 6 | No legal or HIPAA-compliance claim | `grep -n -i "hipaa" <page> CS4610_Report_Demo/README.md docs/capstone-report/report-outline.md; echo "rc=$?"` | no lines, `rc=1` | PASS |
| 7 | Findings stay findings | check 1's checker | `0 disallowed`; break (c) shows the rule fires | PASS |
| 8 | Demo matches the page | the dry-run record (PR #210 comment 6334394792) against §6.2, §6.4 and §6.1 | unchanged from the second pass. The five steps that differed and the hazards are reworded or cut, and no §6.2 "says" line contradicts the record. The record's stale file-name line does not affect its spot checks (item 7 above). Talk time and the T-1 hour repeat stay open, as the record says | PASS |
| 9 | Coursework untouched | `git diff --name-only origin/main...HEAD -- 'CS4610_Report_Demo/*.docx' 'CS4610_Report_Demo/*.pdf' \| wc -l` | `0` | PASS |
| 10 | Old showcase untouched | `git diff --quiet origin/main -- audit/2026-09-25/asclexis-showcase.html && echo unchanged` | `unchanged` | PASS |
| 11 | Docs gates | `python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py --link-graph; python3 scripts/docs_lint.py; echo lint_rc=$?; python3 scripts/generate_docs_index.py --check; echo rc=$?` | `regen=0` (INDEX and link graph unchanged); `Docs lint passed.` `lint_rc=0`; `docs/INDEX.md and docs/_link_graph.json are fresh.` `rc=0` | PASS |

**Result of the third pass: checks 1-11 all pass at the tip.** O-6, §13, C7 and the ready state remain L0's.

**O-6 recorded (C7, L0, 2026-10-22):** the owner answered O-6 "Freeze now; sign if all pass" (prompt 30, owner-decisions row O-6) and "L0 dry-runs on the GPU box" for check 8 (prompt 31, row O-6-CHECK8). All 11 checks pass at `75c1106`, and the independent Opus review re-ran them (#210 comment 6345850792, VERDICT PASS). O-6 therefore counts as signed for **2026-10-22**, with the claim freeze at `75c1106` (figures as of `a16dd51`). Left with the owner/presenter, outside the checklist: presenter talk time (≤ 11 min) and the T-1 hour repeat (Task 9 Step 5). Round-2 MINOR not applied, on purpose: the page footer ("Owner sign-off O-6 is recorded in the showcase plan (§13, §15) and in owner-decisions") is left unedited so the frozen page stays byte-identical; it is true from this commit on.

## 16. Stop gates

1. Task 0 ancestry check fails → STOP (intended before P1).
2. W-1 Task 6 not merged → Task 5 waits; other tasks may proceed.
3. Another plan has an open edit to `claims-ledger.md`, `architecture-overview.md` or `CS4610_Report_Demo/README.md` → wait. Never edit concurrently.
4. A ledger row's evidence fails on the post-P1 tree → write what the evidence shows, lower the verdict, and change every §9 action that cites it. Never keep a claim by keeping an old number.
5. A figure cannot be measured (for example vitest under WSL) → drop the figure; do not carry the old value.
6. Any edit to `CS4610_Report_Demo/*.docx|*.pdf`, to `audit/2026-09-25/asclexis-showcase.html`, or to product code → STOP.
7. Any real patient data on the demo machine's screen, in the demo clone's `data/`, or in a screenshot → STOP the demo prep and tell the owner.
8. A HIPAA or legal-status sentence other than D10's wording → STOP.
9. A demo step behaves differently from its "says" line in the dry run → cut or reword the step; never script around a defect on stage.
10. `docs_lint` reports a new error on a file this plan touched → fix before committing. Pre-existing DOC-011 orphans for other `docs/plans/2026-09-27-*` files are not this plan's to fix (P0-B index regeneration).

## 17. Rollback

- Before push: the worktree and branch belong to the RUNBOOK §3 claim; remove them only through that procedure (`git worktree remove` on `/mnt/e/Programming/Github Repo/hc-f-9`, then delete `docs/f-9-showcase-delta`). No `git reset` (recurring-failures #5).
- After push / PR: `gh pr close <n> --delete-branch`.
- After merge: `git revert <commit>` per commit C1…C7 (each is single-purpose).
- Demo: delete the demo clone folder (`Remove-Item -Recurse $D`) and the synthetic files; nothing in them is real.

## 18. Recurring-failures recheck

| Mode | Applies because | Recheck |
|---|---|---|
| #1 green signal that could not fail | the claim checker could pass vacuously | Task 7 step 3 breaks it four ways |
| #3 figures asserted | the old page's numbers were hand-typed (24 features, ~50 sites, era %) | every number comes from Task 1 with its command |
| #4 environment-dependent results | pass counts, SQLCipher presence, embedding model presence | freeze item 3; demo checks 6–7 |
| #5 contaminated tree | the owner's checkout has uncommitted edits | all gates run in the `hc-f-9` worktree; the demo runs in a fresh clone |
| #6 documented commands nobody ran | the demo checklist and this plan quote commands | Task 9 runs every §6.3 command exactly as written; fix the plan if one fails |
| #8 stale guidance as authority | the orchestrator ledger and the old showcase are leads, not findings | Task 2 step 3 re-runs every evidence command before a row lands |

Not applicable: #2 (no multi-step product flow is changed), #7 (no SQL written).

## 19. Findings from planning (for the orchestrator)

Claims in the 2026-09-25 showcase found false, with evidence (main@40f590e):

| showcase line | Claim | Evidence |
|---|---|---|
| :311 | `feature_list.json` "24 items" | `python3 -c "import json;print(len(json.load(open('feature_list.json'))['features']))"` → 27 (A, B also 27) |
| :497 | agent lane ends in `validate_response :793` | only caller `modules/rag.py:1271`; `grep validate_response src/backend/api/assistant.py` → none |
| :234 | "Every answer … exits through the same validation gauntlet" | overview §6/§12 row 3; C14 |
| :532 | utcnow "~50 sites / 13 files" | ledger H9: 101 lines / 109 references / 30 files |
| :537 | "branch1 fixes" the unredacted `source_quote` | `git diff --stat main A@692fdf3 -- src/backend` → `api/documents.py` + test only; `api/export.py:126` unchanged |
| :267 | "Append-only audit log" | `api/profiles.py:909` deletes the profile's `AuditLog` rows |
| :264 | master DB "no PHI", "metadata only" | `models/profile.py:47,53` display name + password hash in an unencrypted DB |
| :451 | trends "across all verified imports" | `api/observations.py:529-535` has no `user_verified` filter (ledger C2) |
| :522-525 | era shares E3 30%, E4 "55% of all history", E5 90%, E6 95% | measured 0/9, 230/355 (65%), 17/17, 0/1 by author name (H12) |
| :394 | matrix + program "pending" | both written 2026-09-27 |
| :397-400 | ledger 11/1/6/2 | 24 rows today: 6/6/7/2 + 2 CASE-STUDY + 1 HYPOTHESIS |
| :490 | Ollama URL "enforced by config" | factory passes no URL (`core/llm/factory.py:51`); enforcement is `_assert_localhost` in code |
| :243 | `scripts/seed_knowledge_base.py` | the file is `src/backend/scripts/seed_knowledge_base.py` |
| :284 | "data unreadable from this instant" (step 1) | backups keep key copies until step 3 (C5 order) |

Also: outline `:34` layer order is contradicted by H13 (docs lint 2026-02-12 and security gate 2026-02-22 predate CLAUDE.md 2026-06-13).
