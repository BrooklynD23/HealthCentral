# Documentation Drift Reconciliation Implementation Plan

> **2026-09-27 corrections ([review follow-up](../review/2026-09-27-followup.md), F-01/F-12/F-13):** (1) Task 16's `git add -A` was replaced with explicit pathspecs. (2) Task 12 (Serena memories) is blocked on an owner choice; deletion is not authorized. (3) The ledger below has 16 rows. The "~40-row" reconciler table the audit mentions was never packaged. The only other drift artifact is `audit/repository-audit-dashboard.html`, whose §4 table has 12 rows. (4) "1,245 collected" in row 1 is main@`40f590e` (re-measured 2026-09-27). This plan runs after the branch merge (plan 01), where the tree collects 1,291, so measure the count at execution time. Sequencing lives in [`docs/capstone-report/implementation-program.md`](../../../docs/capstone-report/implementation-program.md).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile the documentation drift catalogued in `audit/2026-09-25/Devin-Audit-report.md` §8/§15 against verified code truth, so no doc an agent or contributor reads contradicts the code it describes.

**Architecture:** Docs-only sweep. Every task is a single `docs:`-prefixed commit touching markdown, plus two Python *docstring*-only edits (Task 10) and dead-config removal in `config/.env.example` (Task 3). No product behavior changes. Every task follows the same loop: re-verify the claim against code with the given command, edit the doc to the verified truth, run the docs gates, commit. Two items are explicitly dependent on sibling plans — `audit/2026-09-25/plans/02-notification-scheduler.md` (notifications wording) and `audit/2026-09-25/plans/03-phantom-layer.md` (`.claude/agents` claim) — and are written to stay true whichever way those land.

**Tech Stack:** Markdown docs corpus gated in CI by `scripts/docs_lint.py` (13 DOC rules) and `scripts/generate_docs_index.py --check`; conventions from `docs/00_architecture_plans_index.md` and the lint script itself.

## Global Constraints

- **Commit style:** `docs:` prefix, one commit per task (repo convention: `fix(scope):` / `feat(scope):` / `docs:`).
- **Verify-then-edit:** audits can be wrong — two of this audit's own claims already turned out to be false positives (see ledger rows 11 and 13). Every task's Step 1 re-runs the evidence command *at execution time*. If reality has moved (plan-02 landed, a router added), write the truth you measured — not the text quoted here.
- **Lint-enforced doc conventions** (`scripts/docs_lint.py`):
  - Canonical docs (`docs/00_architecture_plans_index.md`, `docs/features/00_features_index.md`, `docs/features/TASK_LIST.md`) need `**Last Updated:** YYYY-MM-DD`, `**Owner:**`, `**Refresh Trigger:**` (DOC-004). Bump `Last Updated` on any canonical doc you touch.
  - `HISTORICAL_DOCS` need a "Historical Reference" banner + inactive-tracker language in the top 15 lines (DOC-005). `docs/archive/` is historical by design — **never edit it** (DOC-013 polices it, not vice versa).
  - Every relative markdown link in `docs/`, `README.md`, `src/frontend/README.md`, `AGENT.md`, `CLAUDE.md` must resolve (DOC-007).
  - `README.md`, `docs/00_architecture_plans_index.md`, `docs/features/TASK_LIST.md` must state an identical numbered "Canonical Doc Order" / "Documentation Source of Truth" list (DOC-010). This plan never changes that list — do not let an edit alter it in only one file.
  - Every doc under `docs/` must be linked or present in `docs/INDEX.md` (DOC-011). No task adds a doc.
  - `docs/features/TASK_LIST.md` rows kept as `[ ] OPEN`/`[ ] TODO` need ≥7 columns with non-empty Phase T1–T3 (rule 4). Rows flipped to DONE are exempt; keep the row well-formed anyway.
  - Never reintroduce `LLM Required` into `docs/05_backend_integration_status.md`; frontend `npm run` names must exist in `src/frontend/package.json` (DOC-009) — this plan adds none.
- **Point-in-time docs are exempt:** `docs/plans/`, `docs/archive/`, dated implementation logs, PRDs, and `audit/` itself are historical records. Stale-looking claims inside them (FAISS in `docs/06_mvp_to_rag_execution_board.md`, the tech-survey's *"at survey time"* passages, `docs/Local_First_Medical_Results_Companion_PRD_v0_1.md`) are correct history — do not edit.
- **No product code changes.** Allowed non-markdown edits: the two `__init__.py` docstrings (Task 10) and `config/.env.example` dead lines (Task 3). If a verify step shows the *code* is what's wrong, stop and file a bug — do not fix code in this sweep.
- **Safety surfaces:** this sweep does not touch `modules/interpret_safety.py`, `modules/redaction.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`, or auth/encryption code.

## Verified Drift Ledger (evidence re-checked 2026-09-25)

| # | Stale claim | Where | Verified truth | Evidence |
|---|---|---|---|---|
| 1 | "~620 pytest tests" (×2); "four axes" | `docs/agentic/evals.md:9,20,21` | 1,245 collected per AGENT.md/CLAUDE.md baseline (1,174 `def test_` + parametrized); **6** axes; **74** golden cases | `modules/agent/eval/scorer.py:3-27` (4 numeric + 2 HC-M05 adversarial axes), `ScoreReport` fields `:106-111`; `ls src/backend/tests/agent/golden/*.json \| wc -l` → 74 |
| 2 | API table lists 12 groups | `README.md:523-536` | 18 routers under `/api/v1` + `health` + `metrics` | `api/__init__.py:39-58` (18 `include_router`); `main.py:150-155` |
| 3 | Agent "default OFF", "stubs, flag OFF" | `README.md:494-495,516-517` | `AGENT_ENABLED_DEFAULT = True`; agent is the live default chat path | `modules/agent/settings.py:19` |
| 4 | FAISS in stack; `VECTOR_STORE_TYPE` in env template | `README.md:202`; `config/.env.example:92-96` | FAISS/`vector_store_type` removed 2026-07-01; pure-Python linear cosine scan. `EMBEDDING_DIMENSIONS` is still live | `modules/rag.py:597-598`; `grep vector_store_type core/config.py` → none; `core/config.py:113` has `embedding_dimensions` |
| 5 | Notifications "all implemented" | `docs/features/00_features_index.md:26` | Engine exists; scheduler never started — `main.py` lifespan wires only `backup_scheduler` | `main.py:67-81`; no callers of `start_notification_scheduler` outside the module |
| 6 | `INGEST-FHIR-001` `[ ] OPEN`, "zero structured ingest" | `docs/features/TASK_LIST.md:59` | HC-M23 shipped 2026-07-17; live module is `modules/import_structured.py` (the row's predicted `extract_fhir.py` name was never used) | `TASK_LIST.md:710-730`; `grep fhir_bundle modules/ api/` → `import_structured.py`, `ingest.py`, `api/documents.py` |
| 7 | S06-SEC-003/004 "CONFIRMED STILL OPEN" | `docs/compliance/security-review-sprint06.md:9` | Both fixed in code | `security/input_validator.py:92,110` (`_send_error(send, 413,…)`); `scripts/backup.py:120-156` `_validate_manifest_path` used at `:433` and `:576-577` |
| 8 | "no password recovery mechanism" | `docs/user/faq.md:44-46` | SEC-RECOV-001 backend shipped: one-time recovery code at profile creation, unlock + rotate endpoints | `api/profiles.py:26-35,161-198` (`generate_recovery_code`, `recovery_rate_limiter`, recovery request/response models); TASK_LIST SEC-RECOV-001 row = `[~] PARTIAL` (frontend stranded) |
| 9 | `.serena/memories/` = agent context | `.serena/memories/` (7 files) | All 7 last committed 2026-01-07; content says "HealthCentral", references `implementation_plan/` (moved), FAISS/sqlite-vss | `git log -1 -- .serena/memories/*`; `project_overview.md:1,23,41` |
| 10 | Update `.gsd/KNOWLEDGE.md` | `CONTRIBUTING.md:179` | `.gsd/` absent and gitignored (`.gitignore:118`) | `ls .gsd` → no such dir |
| 11 | `endpoints.md` missing med-reconciliation row | `docs/api/endpoints.md` | **FALSE POSITIVE** — row exists at `endpoints.md:196-201`; `api/med_reconcile.py` has exactly one route (`GET /`) | verified 2026-09-25 |
| 12 | asclexis-agent lists 5 tools; asclexis-evals says "four axes"; AGENT.md row same | `skills/asclexis-agent/SKILL.md:37-39`; `skills/asclexis-evals/SKILL.md:3,37`; `AGENT.md` skills table | 8 registered tools: `query_observations`, `compute_trend`, `check_verification`, `lookup_reference`, `retrieve_chunks`, `query_care_tasks`, `query_medication_changes`, `query_timeline`; 6 axes | `modules/agent/tools/registry.py:42-67` |
| 13 | `openwiki/` = generated repo map | `docs/00_architecture_plans_index.md:56-60`; `AGENT.md` | `openwiki/README.md:15-17` already says "still not generated"; only the *referrer wording* oversells it | `find openwiki -type f` → README only |
| 14 | `api/__init__.py` docstring: "HealthCentral" + 9 domains; `modules/agent/__init__.py` "SCAFFOLD ONLY… NotImplementedError" | `src/backend/api/__init__.py:1-14`; `src/backend/modules/agent/__init__.py:1-16` | Asclexis; 18 routers; agent is live default-ON | both files read in full |
| 15 | root `scripts/download_models.py` | `scripts/download_models.py` | Stale old-tier copy (Qwen2.5/Phi-3, own argparse); canonical is `src/backend/scripts/download_models.py` (gemma4 tiers + ollama); zero references to root copy | `diff -q` differs; `grep -rn download_models` → only `AGENT.md:61` (backend path) |
| 16 | `.claude/agents/` cited as live | `docs/agentic/harness.md:25`, `docs/agentic/roadmap.md:8,15` | Directory absent; `.gitignore:44` `.claude/*` (only `!.claude/skills/` excepted) makes it uncommittable | **BLOCKED on plan-03** — no edit in this sweep |

---

### Task 1: Fix evals doc test-count and axis-count drift

**Files:**
- Modify: `docs/agentic/evals.md` (lines 9, 20, 21)

**Why:** `evals.md` is where agents learn what "verified" means; it claims "~620 pytest tests" twice and "four axes" while the gate actually scores six axes over 74 golden cases and the baseline is 1,245 collected tests. This is recurring-failure mode #3 (numbers drift) inside the eval doc itself (audit §15.6).

- [ ] **Step 1: Re-verify the truth**

```bash
cd src/backend && python -m pytest tests/ --collect-only -q 2>/dev/null | tail -3   # expect "1245 tests collected" (or current real number)
ls src/backend/tests/agent/golden/*.json | wc -l                                     # expect 74
grep -n "groundedness\|citation\|abstention\|advice_leakage\|injection_resistance\|phi_leakage" src/backend/modules/agent/eval/scorer.py | head -12
```

- [ ] **Step 2: Edit `docs/agentic/evals.md`**

Line 9 (Unit tests table row):

```markdown
| Unit tests | Backend module behavior (1,245 pytest tests collected) | `src/backend/tests/`, CI `backend-tests` |
```

Line 20 (Concrete evals item 1):

```markdown
1. **Agent safety gate** — `python3 scripts/agent_eval_gate.py` scores the 74-case golden set (`tests/agent/golden/`) on six axes and fails CI on any regression: groundedness == 1.0, citation coverage == 1.0, abstention == 1.0 on abstain/escalate cases, zero advice leakage on advice-bait cases, injection_resistance == 1.0 on injection cases (HC-M05), and zero phi_leakage on phi-bait cases (HC-M05). The R-14 composed-then-dropped and HC-M05 injection-compose end-to-end checks must also pass.
```

Line 21 (Concrete evals item 2 baseline):

```markdown
2. **Backend regression suite** — `bash scripts/run-backend-tests.sh -q` (CI) or `cd src/backend && python -m pytest tests/ -p no:cacheprovider -q` (local). Baseline: 1,245 collected; all pass where a real embedding model is installed (CI). Without one, `test_api_rag_index_002b` fails on embedding similarity — a known env-only failure that must not be "fixed" by lowering its 0.7 threshold.
```

If the collected count has moved by execution time, use the real number here **and** in the `CLAUDE.md`/`AGENT.md` baseline lines in the same commit (the repo rule: a stale collected-count line gets fixed in the commit that notices it).

- [ ] **Step 3: Gate check**

```bash
python3 scripts/docs_lint.py && python3 scripts/generate_docs_index.py --check
```

- [ ] **Step 4: Commit**

```bash
git add docs/agentic/evals.md
git commit -m "docs(agentic): correct evals doc to 1245 collected tests and 6-axis gate"
```

---

### Task 2: Fix README agent-flag, FAISS, and API-table drift

**Files:**
- Modify: `README.md` (lines ~202, ~493-517, 523-536)

**Why:** Three stale claims in the repo entrypoint: (a) Technology Stack lists "FAISS/vector embeddings" though FAISS was removed 2026-07-01; (b) the Agent Overhaul section says the flag defaults OFF and the code is stubs — it is `AGENT_ENABLED_DEFAULT = True` and the live chat path; (c) the API Overview table lists 12 groups while 18 routers mount under `/api/v1` plus health/metrics.

- [ ] **Step 1: Re-verify**

```bash
grep -n "AGENT_ENABLED_DEFAULT" src/backend/modules/agent/settings.py        # expect = True
grep -n "include_router" src/backend/api/__init__.py src/backend/main.py     # expect 18 + health + metrics
grep -rn "faiss" src/backend/core/config.py src/backend/requirements.txt     # expect no matches
grep -n "cosine_similarity\|blob_to_vector" src/backend/modules/rag.py       # linear scan ~:597-598
```

- [ ] **Step 2a: Fix the Technology Stack line** (`README.md:202`)

```markdown
- **Vector/Retrieval**: Per-profile embedding blobs scanned with a linear cosine-similarity pass (no external vector index — deliberately simple at single-user corpus size), plus local curated reference content
```

- [ ] **Step 2b: Complete the API Overview table** (`README.md:523-536`)

The table has 12 rows; add the 7 missing mounted groups so it matches `api/__init__.py` (keep the `| Group | Endpoints | Description |` format; insert in mount order):

```markdown
| **Care Tasks** | `/care-tasks/` | Open follow-up / care task listing used by agent timeline queries |
| **Timeline** | `/timeline/` | Record timeline events for the "what changed?" assistant surface |
| **Med Reconciliation** | `/med-reconciliation/` | Medication mention → reconciliation suggestions (never direct tracker mutation) |
| **Pinboards** | `/pinboards/` | Saved comparison/pinboard views over observations |
| **Search** | `/search/` | Document/record search |
| **Backup** | `/backup/` | Create, verify, download, restore, and prune per-profile backups |
| **Feedback** | `/feedback/` | Per-turn thumbs/corrections upsert feeding RL dataset export |
```

Cross-check each description against `docs/api/endpoints.md` (the source of truth) before committing.

- [ ] **Step 2c: Fix the Agent Overhaul framing** (`README.md:493-517`)

The paragraph "…(behind the `agent_enabled` flag, default OFF)" and the closing "Code scaffolds (stubs, flag OFF) live under `src/backend/modules/agent/`" both predate the S5 cutover. Replace the framing sentence:

```markdown
The `agent-overhaul` workstream promoted the single-shot `/assistant/` RAG explainer
into a read-only, governed plan→act→reflect agent. **The agent is shipped and is the
default chat path** (`agent_enabled` defaults to True — `modules/agent/settings.py`);
the flag remains only as a per-profile kill switch back to single-shot RAG. Planning
artifacts live alongside the code:
```

and replace the scaffold sentence:

```markdown
The agent implementation lives under `src/backend/modules/agent/` (graph runner,
plan/act/reflect/draft nodes, tool registry, guardrails); the eval harness and 74
golden fixtures under `src/backend/tests/agent/`, gated by `scripts/agent_eval_gate.py`.
```

- [ ] **Step 3: Gate check**

```bash
python3 scripts/docs_lint.py
```

(README is a DOC-010 canonical-order member — do not touch the "Documentation Source of Truth" numbered list.)

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs(readme): correct agent default-on status, drop FAISS, complete 18-router API table"
```

---

### Task 3: Remove dead VECTOR_STORE_TYPE config from `.env.example`

**Files:**
- Modify: `config/.env.example:92-99`

**Why:** The `VECTOR STORE` block declares `VECTOR_STORE_TYPE=sqlite-vss` with a `"faiss"` option comment, but `vector_store_type` no longer exists in `core/config.py` (removed in the §14.5 cleanup, 2026-07-01). **`EMBEDDING_DIMENSIONS` is still live** (`core/config.py:113: embedding_dimensions: int = 384`) — keep it.

- [ ] **Step 1: Re-verify**

```bash
grep -rn "vector_store_type\|VECTOR_STORE_TYPE" src/backend/ | grep -v tests/   # expect: no production reads
grep -n "embedding_dimensions" src/backend/core/config.py                        # expect :113 — still live
```

- [ ] **Step 2: Edit `config/.env.example`** — remove only the dead pair, keep `EMBEDDING_DIMENSIONS`:

```diff
 # =============================================================================
-# VECTOR STORE
+# EMBEDDINGS
 # =============================================================================
-# Vector store type: "sqlite-vss" (default), "faiss"
-VECTOR_STORE_TYPE=sqlite-vss
-
 # Embedding dimensions (must match embeddings model)
 EMBEDDING_DIMENSIONS=384
```

- [ ] **Step 3: Gate check + stray references**

```bash
python3 scripts/docs_lint.py
grep -rn "VECTOR_STORE_TYPE" README.md AGENT.md CLAUDE.md CONTRIBUTING.md docs/ src/frontend/README.md  # expect none in live docs
```

If a live doc still mentions `VECTOR_STORE_TYPE`, remove that mention in the same commit (historical docs exempt).

- [ ] **Step 4: Commit**

```bash
git add config/.env.example
git commit -m "docs(config): drop dead VECTOR_STORE_TYPE/faiss lines from env template"
```

---

### Task 4: Reword features-index notifications claim — DEPENDENT on plan-02

**Files:**
- Modify: `docs/features/00_features_index.md:26` (+ `**Last Updated:**` at :3)

**Dependency:** `audit/2026-09-25/plans/02-notification-scheduler.md` (wire vs remove decision). **The Step-2a wording stays true either way**, so this may land now; if plan-02 has already merged and wired the scheduler, use Step 2b instead.

**Why:** "Notifications: Settings, history, scheduler, test notifications — all implemented" contradicts code (the scheduler is never started — `main.py:67-81` wires only `backup_scheduler`; `start_notification_scheduler` has no production callers) and contradicts docs that call it "deliberately unwired" (audit §15.2).

- [ ] **Step 1: Re-verify wiring state**

```bash
grep -rn "start_notification_scheduler\|register_profile_session" src/backend/ --include="*.py" | grep -v tests/
grep -n "scheduler" src/backend/main.py
```

- [ ] **Step 2a: If still unwired** — replace the bullet:

```markdown
- **Notifications**: Settings, history, and test notifications implemented. The reminder-scheduler engine exists but is not started in the app lifespan (locked-vault problem pending decision — see `audit/2026-09-25/plans/02-notification-scheduler.md`), so reminders cannot fire yet.
```

- [ ] **Step 2b: If plan-02 landed and wired it** — replace with:

```markdown
- **Notifications**: Settings, history, scheduler (started in app lifespan), and test notifications — all implemented.
```

- [ ] **Step 3: Bump `**Last Updated:**` to the execution date** (DOC-004), then gate + commit

```bash
python3 scripts/docs_lint.py
git add docs/features/00_features_index.md
git commit -m "docs(features): qualify notifications status — scheduler engine unwired pending decision"
```

---

### Task 5: Close the rotted INGEST-FHIR-001 tracker row

**Files:**
- Modify: `docs/features/TASK_LIST.md:59` (+ `**Last Updated:**` at :4)

**Why:** The row says "zero structured ingest exists today" and is `[ ] OPEN`, but HC-M23 shipped 2026-07-17 — the same file's own session notes (`:710-730`) record it, and the live code is `modules/import_structured.py` + `api/documents.py` `lab_csv`/`fhir_bundle` handling (the row's predicted `extract_fhir.py` filename was never used — worth correcting so nobody greps for a phantom module).

- [ ] **Step 1: Re-verify**

```bash
grep -rn "fhir_bundle\|lab_csv\|import_structured" src/backend/api/documents.py src/backend/modules/ | head -10
sed -n '710,715p' docs/features/TASK_LIST.md   # HC-M23 session note
```

- [ ] **Step 2: Flip the row to DONE**

In the `:59` row: change the description's false opener and the status cell, matching the file's `| [x] DONE (YYYY-MM-DD) — note |` convention:

```markdown
| `INGEST-FHIR-001` | FHIR R4 structured import (lab `Observation`/`DiagnosticReport` bundles). Portal FHIR exports (Cures Act) give exact values/units/ranges/LOINC codes with no OCR errors. Deterministic stdlib-JSON parsing, no new dependency, imports stay unverified until workbench review. | P2 | Full ticket at [`docs/plans/2026-07-02-architect-review-proposal-tickets.md`](../plans/2026-07-02-architect-review-proposal-tickets.md#ingest-fhir-001--fhir-r4-structured-import-lab-observations-first) | `src/backend/modules/import_structured.py`, `modules/ingest.py`, `modules/normalize.py`/`glossary.py` (LOINC map) | [x] DONE (2026-07-17) — shipped as HC-M23 alongside CSV lab import; structured docs skip OCR/classification and land unverified |
```

- [ ] **Step 3: Bump `**Last Updated:**`**, gate, commit

```bash
python3 scripts/docs_lint.py
git add docs/features/TASK_LIST.md
git commit -m "docs(task-list): mark INGEST-FHIR-001 done (shipped as HC-M23, 2026-07-17)"
```

---

### Task 6: Update the stale S06-SEC-003/004 status banner

**Files:**
- Modify: `docs/compliance/security-review-sprint06.md:9` (add a dated status line; never rewrite the historical finding bodies)

**Why:** The top banner (dated 2026-07-01) says "**S06-SEC-003 is CONFIRMED STILL OPEN**"; both findings are now fixed in code — verified: `security/input_validator.py:92,110` sends a 413 via `_send_error` for oversized bodies, and `scripts/backup.py` `_validate_manifest_path` (`:120-156`) rejects absolute/`..` paths and resolves within base, used at `:433` (verify) and `:576-577` (restore). The file's own convention is a dated `> **Status update (YYYY-MM-DD):**` blockquote — follow it.

- [ ] **Step 1: Re-verify both fixes are still present**

```bash
grep -n "_send_error\|413" src/backend/security/input_validator.py
grep -n "_validate_manifest_path" src/backend/scripts/backup.py
```

If either fix has regressed, do **not** claim it resolved — keep that finding OPEN in the banner and flag to the owner.

- [ ] **Step 2: Add a new dated status line** immediately after the existing `:9` blockquote:

```markdown
> **Status update (YYYY-MM-DD):** Re-verified during the doc-drift reconciliation sweep. **S06-SEC-003 is RESOLVED** — oversized request bodies now get a clean 413 via `_send_error` in `security/input_validator.py` (no downstream catch required). **S06-SEC-004 is RESOLVED** — `scripts/backup.py::_validate_manifest_path` rejects absolute/`..` manifest paths and resolves within the intended base before verify/restore. Finding bodies below are retained as the original Sprint-06 record.
```

(Use the execution date; adjust wording if Step 1 found a regression.)

- [ ] **Step 3: Gate + commit**

```bash
python3 scripts/docs_lint.py
git add docs/compliance/security-review-sprint06.md
git commit -m "docs(compliance): status-update banner — S06-SEC-003/004 resolved"
```

---

### Task 7: Correct the FAQ password-recovery answer (SEC-RECOV-001)

**Files:**
- Modify: `docs/user/faq.md:44-47`

**Why:** The FAQ says flatly "There is no password recovery mechanism." SEC-RECOV-001's backend shipped: profile creation issues a one-time recovery code sealing a second copy of the DEK, and `api/profiles.py` exposes unlock-with-recovery-code and rotation endpoints (`:161-198`). Honest caveat from TASK_LIST's SEC-RECOV-001 `[~] PARTIAL` row: codes are issued only at creation — there is no signed-in surface to mint one for an existing profile.

- [ ] **Step 1: Re-verify the endpoints**

```bash
grep -n "recovery_code\|recover" src/backend/api/profiles.py | head -15
```

Expected: issue-at-creation response field, an unlock/recover endpoint, a rotate endpoint.

- [ ] **Step 2: Replace the answer** under `### What happens if I forget my password?`

```markdown
At profile creation Asclexis issues a **one-time recovery code** — store it
somewhere safe. If you forget your password, that code is the only way back into
the encrypted vault: it seals a second copy of your encryption key. Recovery
codes are issued only when a profile is created — there is currently no way to
generate one afterwards for a profile that didn't save one. Without a code the
vault cannot be opened; the password derives the encryption key, so there is no
backdoor by design. **Keep backups of your data** using the backup utility, and
keep your recovery code with them.
```

- [ ] **Step 3: Gate + commit**

```bash
python3 scripts/docs_lint.py
git add docs/user/faq.md
git commit -m "docs(faq): correct password-recovery answer for SEC-RECOV-001 recovery codes"
```

---

### Task 8: Remove the phantom `.gsd/KNOWLEDGE.md` from CONTRIBUTING

**Files:**
- Modify: `CONTRIBUTING.md:179`

**Why:** The bullet tells contributors to update `.gsd/KNOWLEDGE.md` — a file that does not exist and cannot be committed (`.gitignore:118` ignores `.gsd`, a leftover GSD-workflow artifact).

- [ ] **Step 1: Re-verify**

```bash
ls .gsd 2>&1; grep -n "^\.gsd" .gitignore; sed -n '175,185p' CONTRIBUTING.md
```

- [ ] **Step 2: Edit the bullet**

```diff
-- **Document category:** when contributor guidance changes, update `README.md`, `CONTRIBUTING.md`, and `.gsd/KNOWLEDGE.md` together so future audits interpret local-only artifacts consistently.
+- **Document category:** when contributor guidance changes, update `README.md` and `CONTRIBUTING.md` together so future audits interpret local-only artifacts consistently.
```

- [ ] **Step 3: Gate + commit**

```bash
python3 scripts/docs_lint.py
git add CONTRIBUTING.md
git commit -m "docs(contributing): drop reference to nonexistent gitignored .gsd/KNOWLEDGE.md"
```

---

### Task 9: Sync skill docs + AGENT.md with real tool/axis counts

**Files:**
- Modify: `skills/asclexis-agent/SKILL.md` (:37-39 — the 5-tool list)
- Modify: `skills/asclexis-evals/SKILL.md` (:3 description, :37 heading — "four scoring axes")
- Modify: `AGENT.md` (skills-table row for `asclexis-evals` — "the four scoring axes")

**Why:** Skill docs are agent-facing routing context; a SKILL.md that undercounts the tool registry misleads every future agent task, and `skills/` files are outside the docs_lint corpus — wrongness here is invisible to CI.

- [ ] **Step 1: Enumerate the real registry**

```bash
sed -n '42,67p' src/backend/modules/agent/tools/registry.py
```

Verified set (8): `query_observations`, `compute_trend`, `check_verification`, `lookup_reference`, `retrieve_chunks`, `query_care_tasks`, `query_medication_changes`, `query_timeline`. Use whatever Step 1 prints at execution time if it has changed.

- [ ] **Step 2: Update `skills/asclexis-agent/SKILL.md`** — replace the tool list:

```markdown
`modules/agent/tools/`. Malformed args fail validation and are NEVER executed —
this is the first guardrail layer, not an afterthought. Current read-only tools:
`query_observations`, `compute_trend`, `check_verification`, `lookup_reference`,
`retrieve_chunks`, `query_care_tasks`, `query_medication_changes`,
`query_timeline`. New tools must be read-only and profile-scoped to the
unlocked vault session.
```

- [ ] **Step 3: Update `skills/asclexis-evals/SKILL.md`** — "the four scoring axes (groundedness, citation accuracy, abstention correctness, advice leakage)" → six axes everywhere it appears (description `:3` and the `:37` heading/body):

```markdown
… the six scoring axes (groundedness, citation accuracy, abstention correctness, advice leakage, injection resistance, PHI leakage) …
```

```markdown
## The six scoring axes (all automated)
```

and ensure the axis list inside the section names all six (groundedness, citation, abstention, advice_leakage + HC-M05's injection_resistance and phi_leakage).

- [ ] **Step 4: Update `AGENT.md`** skills-table row for `asclexis-evals`:

```markdown
| `asclexis-evals` | Golden eval cases, synthetic vault states, the six scoring axes (groundedness, citation accuracy, abstention correctness, advice leakage, injection resistance, PHI leakage), or the CI workflow that gates PRs on agent behavior |
```

- [ ] **Step 5: Gate + commit** (AGENT.md links are DOC-007-checked via EXTRA_LINK_ROOTS)

```bash
python3 scripts/docs_lint.py
git add skills/asclexis-agent/SKILL.md skills/asclexis-evals/SKILL.md AGENT.md
git commit -m "docs(skills): correct agent tool count (8) and eval axis count (6)"
```

---

### Task 10: Fix the two lying `__init__.py` docstrings

**Files:**
- Modify: `src/backend/api/__init__.py:1-14` (docstring only)
- Modify: `src/backend/modules/agent/__init__.py:1-16` (docstring only)

**Why:** (a) `api/__init__.py` says "API routes for HealthCentral backend" (pre-rename product name) and lists 9 of the 18 routers. (b) `modules/agent/__init__.py` says "SCAFFOLD ONLY. Bodies raise NotImplementedError" and describes a flag-gated stub — but this is the live, default-ON chat path; audit §15.4: *"an agent trusting that docstring could bypass a live safety path."* Docstring-only edits; `docs:` prefix applies since no behavior changes.

- [ ] **Step 1: Read both files** — confirm the quoted claims are still the docstring text.

- [ ] **Step 2: Rewrite `api/__init__.py` docstring** (match `include_router` order :39-58):

```python
"""
API routes for the Asclexis backend.

Organized by domain (all mounted under /api/v1 by main.py):
- profiles: Profile management, sessions, recovery codes
- documents: Import, list, view, reprocess documents (PDF/image + CSV/FHIR)
- observations: Lab values and verification
- interpretations: AI-powered lab result interpretations
- medications: Medication management and adherence tracking
- notifications: Medication reminder notifications
- assistant: RAG/agent-powered chat
- export: Summary, FHIR R4, and data export
- model_settings: Model tiers, downloads, external API config, voice
- memory: Persistent assistant memory per profile
- gamification: Badges and streaks
- care_tasks: Open follow-up / care task listing
- timeline: Record timeline events
- med_reconcile: Medication mention reconciliation suggestions
- pinboards: Saved comparison/pinboard views
- search: Document/record search
- backup: Per-profile backup create/verify/download/restore/prune
- feedback: Per-turn thumbs/corrections for RL dataset export
"""
```

- [ ] **Step 3: Rewrite `modules/agent/__init__.py` docstring**:

```python
"""Asclexis read-only plan->act->reflect agent (E1 — Agent Core).

SHIPPED — this is the default ``/assistant/chat`` path
(``settings.AGENT_ENABLED_DEFAULT = True``). The ``agent_enabled`` per-profile
setting is a kill switch back to the legacy single-shot RAG path, not a gate
for unfinished scaffolding.

The one inviolable rule: the agent is READ-ONLY over clinical data. No module
here may write an observation, interpretation, medication, or any clinical row.
Write capability is a NEW epic, never a story (AGILE_PLAN §7).

Graph runner, plan/act/reflect/draft nodes, the bounded read-only tool
registry (8 tools), and guardrails live here. Changes affect the production
safety path — see skills/asclexis-agent and skills/asclexis-guardrails before
editing.
"""
```

(Preserve any portion of the existing docstring that documents the stdlib-only import constraint — `:14-16` — if still accurate.)

- [ ] **Step 4: Sanity + commit**

```bash
cd src/backend && python -c "import api, modules.agent"   # docstring-only change must still import
cd .. && python3 scripts/docs_lint.py
git add src/backend/api/__init__.py src/backend/modules/agent/__init__.py
git commit -m "docs(backend): correct api/agent package docstrings (Asclexis, 18 routers, agent live)"
```

---

### Task 11: endpoints.md — verify-only (audit claim is a false positive)

**Files:** none expected; close as verified-accurate.

**Why:** The audit claimed `endpoints.md` was "missing one row (med reconciliation endpoint)." Re-check on 2026-09-25: the Medication Reconciliation section exists at `docs/api/endpoints.md:196-201` with the `GET /med-reconciliation/` row, and `api/med_reconcile.py` has exactly one route (`@router.get("/")`). Every mounted prefix has a matching section. The claim does not reproduce.

- [ ] **Step 1: Diff mounted routes vs the doc anyway** (cheap insurance — the audit may have meant a different row):

```bash
grep -o 'prefix="[^"]*"' src/backend/api/__init__.py src/backend/main.py | sort -u
grep -n "^## " docs/api/endpoints.md
grep -rn "@router\.\(get\|post\|patch\|put\|delete\)" src/backend/api/*.py | wc -l
grep -c "^| \(GET\|POST\|PATCH\|PUT\|DELETE\)" docs/api/endpoints.md
```

- [ ] **Step 2:** If the counts/sections reveal a genuinely missing row, add it in the file's format and commit `docs(api): add missing <endpoint> row to endpoints source of truth`. If nothing is missing, record "audit §8 med-reconciliation claim = false positive (verified <date>)" in the Task 16 close-out notes instead of editing the file.

---

### Task 12: Resolve `.serena/memories/` staleness — BLOCKED on owner choice

> **Corrected 2026-09-27 ([review F-13](../review/2026-09-27-followup.md)):** the audit (§16) says *decide* whether to refresh or delete, and the owner has not chosen. Deletion is **not authorized**. This task is blocked until the owner picks Option A (delete), Option B (regenerate), or a freshness gate. It is not deletion-by-default. Note also that `.serena/project.yml` carries uncommitted owner edits (observed 2026-09-27): do not stage or revert it as part of this task.

**Files (only after the owner chooses):**
- Option A would delete: `.serena/memories/code_style_conventions.md`, `critical_01_07.md`, `feature_implementation_progress.md`, `project_overview.md`, `security_audit_findings.md`, `suggested_commands.md`, `task_completion_checklist.md`

**Why:** All 7 files were last committed 2026-01-07 — frozen pre-`models/`, pre-Alembic, pre-rename. Content still says "HealthCentral Project Overview", references `implementation_plan/` (moved to `docs/plans/implementation-log/`), and claims "Vector Store: sqlite-vss or FAISS" (`project_overview.md:23`). They act as a second, contradicting context source that `docs_lint` never checks (audit §13).

- **Option A — DELETE (plan author's original preference; not owner-approved):** memories are machine-generated agent context, regenerable by Serena on demand; keeping them contradicts live docs.
- **Option B — REGENERATE:** if the owner actively drives sessions through the Serena MCP, rerun its memory-writing onboarding. Heavier, and re-rots silently.
- Optional follow-up (separate PR, NOT this sweep): a docs_lint rule for `.serena/` freshness, per audit §13's own suggestion.

- [ ] **Step 1: Confirm nothing references the memories**

```bash
grep -rn "serena" AGENT.md CLAUDE.md CONTRIBUTING.md README.md docs/ .mcp.json | grep -v archive | grep -v "docs/INDEX"
```

Expected: `.mcp.json` pins the Serena server itself (keep — we delete stale *contents*, not the server); no doc deep-links a memory file.

- [ ] **Step 2: Delete + commit**

```bash
git rm .serena/memories/*.md
git commit -m "docs(agent-context): delete frozen Jan-2026 .serena memories (contradict live docs; regenerable)"
```

If Option B chosen instead: regenerate each memory via the Serena tool, re-grep `.serena/` for `FAISS|sqlite-vss|implementation_plan/|HealthCentral Project`, then commit `docs(agent-context): regenerate .serena memories against current architecture`.

---

### Task 13: Fix openwiki referrer wording (the stub itself is already honest)

**Files:**
- Modify: `docs/00_architecture_plans_index.md:56-60` (+ `**Last Updated:**` at :3)
- Modify: `AGENT.md` (the `openwiki/` row in the layout section)

**Why:** `openwiki/README.md:15-17` already says "**Status:** still not generated (as of 2026-07-27)" — the stub is honest; generating the real map needs the OpenWiki tool + an LLM API key (manual owner action, documented in that README). The actual drift is in the *referrers*: the index calls it "OpenWiki-generated repo map" and AGENT.md "OpenWiki-generated navigation" — phrasing that implies generated content exists.

- [ ] **Step 1: Confirm stub state**

```bash
find openwiki -type f   # expect README.md only
sed -n '15,17p' openwiki/README.md
```

- [ ] **Step 2: Edit `docs/00_architecture_plans_index.md`:**

```markdown
- [`openwiki/README.md`](../openwiki/README.md) — reserved home for an OpenWiki-generated
  repo map for coding agents (**not yet generated**; README-only stub with regeneration
  instructions). Advisory when generated: if it conflicts with this index, `CLAUDE.md`,
  `AGENT.md`, or `docs/roles/00_roles_index.md`, the hand-maintained docs win.
```

- [ ] **Step 3: Edit `AGENT.md`** openwiki line similarly — "**Generated repo map** [`openwiki/`](openwiki/README.md) —" → note it is a not-yet-generated stub.

- [ ] **Step 4: Bump index `**Last Updated:**`**, gate, commit

```bash
python3 scripts/docs_lint.py
git add docs/00_architecture_plans_index.md AGENT.md
git commit -m "docs(index): mark openwiki as not-yet-generated stub in referrer wording"
```

---

### Task 14: Delete the stale root `scripts/download_models.py` duplicate

**Files:**
- Delete: `scripts/download_models.py`

**Why:** The root copy (4,318 B) is an old-tier script — own argparse, Qwen2.5/Phi-3 tiers, "for HealthCentral" docstring. The canonical copy is `src/backend/scripts/download_models.py` (7,904 B — Gemma 4 tiers + `ollama` pull path, per its docstring "the canonical reference for Gemma 4 GGUF download URLs"). `AGENT.md:61` already documents `cd src/backend; python scripts/download_models.py list`. Verified: zero references to the root path in docs, CI, or dev scripts. Duplicate-script drift is recurring-failure mode #6 — one canonical path.

- [ ] **Step 1: Re-verify no live references**

```bash
grep -rn "download_models" README.md AGENT.md CLAUDE.md CONTRIBUTING.md docs/ .github/ dev.ps1 dev.bat scripts/ src/frontend/ 2>/dev/null | grep -v "src/backend/scripts/download_models"
diff -q scripts/download_models.py src/backend/scripts/download_models.py
```

Expected: only `AGENT.md:61` (which uses the backend path); files differ. If a CI workflow or doc still references the root path, repoint it in the same commit.

- [ ] **Step 2: Delete + commit**

```bash
git rm scripts/download_models.py
python3 scripts/docs_lint.py
git commit -m "docs(scripts): remove stale root download_models.py duplicate (canonical: src/backend/scripts/)"
```

---

### Task 15: `.claude/agents/` claim — BLOCKED on plan-03, no edit

**Files:** none (explicitly).

**Dependency:** **BLOCKED on `audit/2026-09-25/plans/03-phantom-layer.md`.** The claim lives at `docs/agentic/harness.md:25` ("Subagent definitions live in `.claude/agents/`. Use them…" — names 5 subagents) and `docs/agentic/roadmap.md:8,15`. Verified: `.claude/` contains only `skills/`; `.gitignore:44` `.claude/*` (with only `!.claude/skills/` excepted) makes `.claude/agents/` uncommittable. Whether the fix is "commit the agents," "amend the gitignore," or "delete the claims" is plan-03's decision — this sweep must not guess.

- [ ] **Step 1:** If plan-03 has resolved, verify its doc edits landed and mark this task DONE-N/A. If not, leave this task unchecked and record the blockage in the sweep close-out notes (Task 16, Step 3).

---

### Task 16: Final sweep — gates green, zero stale items remain

- [ ] **Step 1: Full docs gates**

```bash
python3 scripts/docs_lint.py
python3 scripts/generate_docs_index.py --check
```

If `INDEX.md` drifted, run `python3 scripts/generate_docs_index.py` and include the regen.

- [ ] **Step 2: Re-run every stale-claim grep — expect zero hits in live docs**

```bash
grep -n "620\|four axes" docs/agentic/evals.md                                  # none
grep -ni "faiss\|VECTOR_STORE_TYPE" README.md config/.env.example               # none
grep -n "default OFF\|stubs, flag" README.md                                    # none
grep "INGEST-FHIR-001" docs/features/TASK_LIST.md | grep "OPEN"                 # none
grep -n "STILL OPEN" docs/compliance/security-review-sprint06.md                # only inside quoted history, if any
grep -n "no password recovery" docs/user/faq.md                                 # none
grep -n "gsd" CONTRIBUTING.md                                                   # none
grep -n "SCAFFOLD ONLY\|NotImplementedError" src/backend/modules/agent/__init__.py  # none
ls scripts/download_models.py 2>&1                                              # absent
grep -n "HealthCentral" src/backend/api/__init__.py                             # none
grep -n "sqlite-vss\|FAISS\|implementation_plan/" .serena/memories/*.md 2>/dev/null  # none (files gone)
```

- [ ] **Step 3: Write the close-out note** in `docs/features/TASK_LIST.md` Session Notes (repo definition-of-done requires non-trivial work logged): date, tasks landed, Task 11's false-positive finding, Task 15's blockage on plan-03, Task 4's dependency status on plan-02. Bump `**Last Updated:**`.

- [ ] **Step 4: Commit**

> **Corrected 2026-09-27 ([review F-01](../review/2026-09-27-followup.md)):** the original step ran `git add -A`. In this checkout that command would stage the owner's uncommitted edits (`.serena/project.yml`, `docs/INDEX.md`) and the untracked `audit/` and `docs/capstone-report/` package. Stage only this task's files, then review what is staged before committing.

```bash
git status --short                                   # review: nothing unexpected modified
git add docs/features/TASK_LIST.md                   # Task 16 owns only its close-out note
git diff --cached --name-only                        # must list exactly the task-owned paths
git commit -m "docs: close out doc-drift reconciliation sweep — gates green, ledger verified" -- docs/features/TASK_LIST.md
```

If the index regeneration in Step 1 changed `docs/INDEX.md` / `docs/_link_graph.json`, stage them by explicit path only after confirming with the owner that their pre-existing `docs/INDEX.md` edits are either committed or meant to be included.

---

## Notes for the executor

- **Order:** Tasks 1–3 and 5–14 are independent (no two touch the same hunk of the same file — Tasks 9 and 13 both touch `AGENT.md` but different sections; sequence them in either order, not concurrently). Task 4 may land now (plan-02-agnostic wording) or after plan-02 (post-wiring wording). Task 15 performs no edit unless plan-03 resolved. Task 16 runs last, always.
- **Do not touch:** `docs/archive/`, `docs/plans/` and `docs/superpowers/plans/` dated records, the PRDs, `audit/` itself, `docs/05_backend_integration_status.md`, and `.gsd`-era references inside archived docs.
- **Known env-only test failure:** `test_api_rag_index_002b` — not yours, do not chase it; do not lower its 0.7 threshold.
- **If a "stale" claim turns out true at execution time** (code regressed, plan-02 wired things differently): write the measured truth, note the divergence in the commit body, and flag the discrepancy to the owner rather than forcing this plan's wording. Two audit claims were already false positives at plan-writing time (ledger rows 11, 13) — treat every row as a hypothesis.
