# Claims Ledger — Report Claims ↔ Repo Evidence

**Last Updated:** 2026-09-28

Every load-bearing claim headed for the capstone report, with its evidence and its verdict. Rule: **no claim ships without a row here.**

## Verdicts

| Verdict | Meaning |
|---|---|
| `VERIFIED` | Checked in code, git or a command on the date given. |
| `REPORTED` | Stated by the 2026-09-25 audit and not reproducible from the package. Replaces the old `AUDIT-VERIFIED` label, which claimed two-agent verification whose artifacts were never packaged (review F-16, audit addendum A-5). |
| `PARTIAL` | True for part of the scope only. The row says which part. |
| `CASE-STUDY` | An observation from specific runs. There is no denominator, comparison condition, or cost data. Report it as an example, never as a rate or cause. |
| `HYPOTHESIS` | Stated for testing. Not yet tested. |
| `NOT-EVIDENCED` | No evidence found. |
| `CONTRADICTED` | Evidence shows the claim is false. |
| `PENDING` | Needs a check before use. |

**2026-09-27 re-check.** Every row was re-checked against main @ `40f590e`, with the exact evidence shown. Some evidence came from read-only mapping agents; the orchestrator spot-verified the load-bearing lines. The previous verdict is kept in *italics* wherever it changed. Dispositions of the independent review: [`../../audit/2026-09-25/review/2026-09-27-followup.md`](../../audit/2026-09-25/review/2026-09-27-followup.md).

## Product claims

| # | Claim | Evidence (main @ `40f590e`) | Verdict |
|---|---|---|---|
| C1 | Patients import lab PDFs, images and FHIR into encrypted per-profile vaults | Upload `api/documents.py:400` → `IngestModule.import_document` encrypts into the vault (`api/documents.py:437-440`, `modules/ingest.py:175,247`). Structured import at `api/documents.py:708`. Vault is SQLCipher-keyed at `core/profile_database.py:349`. The suite runs with `DATABASE_ENCRYPTION_REQUIRED=false` (`tests/conftest.py:57`), so no backend test checks on-disk ciphertext. | `VERIFIED` (code path) · on-disk encryption untested in pytest *(was AUDIT-VERIFIED)* |
| C2 | AI extraction is gated by human verification | Observations are created `user_verified=False` (`api/documents.py:655,757`), and verify endpoints set it (`api/documents.py:1249-1278`, `api/observations.py:458-488`). Gated to verified data: agent tools, FHIR, visit-prep, pinboards. **Not gated:** the trends endpoint (`api/observations.py:529-535`), legacy RAG retrieval (`modules/rag.py:323-331`), and CSV/JSON/doctor summary (`api/export.py:130-150`). | `PARTIAL` *(was AUDIT-VERIFIED)* |
| C3 | Assistant must cite every claim | **Agent path (default ON, `modules/agent/settings.py:19`):** each drafted sentence carries a citation, and the guard drops unmapped sentences. **Legacy path:** `validate_response` (`modules/rag.py:793`) checks `[cite:N]` markers (`:819`). `[YOUR_RESULTS:N]`/`[REFERENCE:N]` are context labels (`:636,640`), not the validated markers. The 74-case CI gate scores the agent path only. On main the agent path shows the UI a hard-coded `faithfulness_score=1.0` (`api/assistant.py:608-617`); the fix `cc202d9` is on branch B. | `PARTIAL` *(was AUDIT-VERIFIED)* |
| C4 | Never diagnosis or dosing — constitutional prohibition | Prohibited-pattern suite `modules/interpret_safety.py:49`, reused in `modules/rag.py:176`. Tests: `test_interpret_safety_adversarial.py`, `test_phase4_ai_safety.py`. `advice_leakage == 0` bar in `scripts/agent_eval_gate.py`. The *mechanism* is verified; an absolute "never" is not provable. | `VERIFIED` (mechanism) *(was AUDIT-VERIFIED)* |
| C5 | Deletion is a cryptographic erase | `api/profiles.py:781-923`: re-auth and phrase check, close the vault, unlink sealed keys first (`:861-874`), sweep the vault, sweep backups, then one master transaction with an anonymized tombstone. Tests `test_profile_deletion.py` HC-PDEL-001…018 call handlers directly, not over HTTP. | `VERIFIED` (code path) *(was AUDIT-VERIFIED)* |
| C6 | Recovery codes exist | Backend `api/profiles.py:546-589,648-763`. No signed-in issuance UI on main; `RecoveryCodeCard.tsx` exists only on branch `claude/asclexis-repo-audit-349pjq` (`692fdf3`). | `PARTIAL` |
| C7 | Medication reminders notify patients | `start_notification_scheduler` (`modules/notification_scheduler.py:559`) has no production caller; the lifespan starts only the backup scheduler (`main.py:69-81`). Wiring is planned (plan 02) and not started. | `CONTRADICTED` — fix planned, not in flight *(was "fix in flight")* |
| C8 | Desktop app | No Tauri, Electron or PyInstaller config. The backend serves no built frontend (no `StaticFiles` mount). | `NOT-EVIDENCED` — present as roadmap, never as fact |
| C9 *(new)* | Every export except backups is redacted (`docs/compliance/data-privacy.md:173-174`) | Strict redaction runs on RL export, FHIR, visit-prep and pinboard export. **CSV, JSON and doctor summary** (text/html/pdf) do not call `modules/redaction.py` (`modules/export.py:82,223,267,290,358`; redaction only at `:533,637`). | `CONTRADICTED` — owner decision needed on scope (matrix PRIV-04) |
| C10 *(new)* | "All PHI stays on-device; the only network call is model download" | Opt-in external LLM path: `core/external_runner.py:261-300` (OpenAI/Anthropic via `httpx`). Off by default (`models/model_settings.py:78-81`), strict redaction by default (`core/config.py:135`). Implicit Hugging Face download on first embedding use: `modules/embeddings.py:56`. | `PARTIAL` — true by default; an opt-in path sends redacted text off-device |

## Harness / research claims

| # | Claim | Evidence | Verdict |
|---|---|---|---|
| H1 | ~67% of commits agent-authored (239/355) | `git log --format=%an HEAD` → 239 of 355 authored "Claude", 2026-09-27. The count includes merges (326 non-merge); 267 commits carry Claude as author or co-author. Author name is a proxy for "agent-authored". | `VERIFIED` (as a git-author count) *(was AUDIT-VERIFIED)* |
| H2 | 1,245 backend tests collected; 155 vitest; 25 e2e | **Backend:** `1245 tests collected`, re-measured 2026-09-27 (`/mnt/c/Python313/python.exe -B -m pytest tests/ --collect-only -q -p no:cacheprovider`, Python 3.13.7). Branch tips collect A 1248 and B 1288; the conflicted A+B merge-tree collects 1291. **Pass counts** were not run this pass; the historical record is `fd8984e` (CI 1245 passed on `7897e47`, 2026-08-03). **Vitest / e2e:** "155" and "25" are historical **pass** counts (`docs/features/TASK_LIST.md:794-795`: "vitest 155/155; Playwright 25 passed / 3 conditional skips"), not test counts. Listed @main on 2026-09-28: vitest **165 tests / 28 files** (static count of `it(`/`test(` declarations; W-11a's `npx vitest list` on Linux agrees); Playwright chromium **28 tests / 5 files** (static count minus 3 in-body `test.skip(true, …)` calls; W-11a listing agrees). A+B: 179 / 31 and 30 / 6. Pass counts not run. | `VERIFIED` (backend collected; vitest/e2e listed counts 165 / 28) · "155 vitest / 25 e2e" as test counts `CONTRADICTED` (they were pass counts) · pass counts `PENDING` *(was vitest/e2e PENDING)* |
| H3 | CI enforces docs and behavior | `.github/workflows/ci.yml` has 6 jobs: docs-lint, backend-tests, frontend-tests, security-scan, agent-evals, e2e-tests. The eval gate covers 74 golden cases (`src/backend/tests/agent/golden/*.json`) with == 1.0 / == 0 bars. Not gated: `npm run build`, eslint, ruff, mypy, coverage. Branch-protection "required" status is unknown (not in repo). | `PARTIAL` *(was AUDIT-VERIFIED)* |
| H4 | Security gate guards the build | On main, `scripts/security_gate.py:49-51,76-78` returns `[]` on `FileNotFoundError`/`JSONDecodeError`, and the scanner steps run `\|\| true` (`ci.yml:92,95`). The fail-closed fix `934a842` is on branch B. Read, not executed. | `CONTRADICTED` — fix exists, unmerged |
| H5 | `.claude/agents/` defines 5 project subagents | Absent from the repo and from git history (`git log --all -- .claude/agents` empty). `.gitignore:44` `.claude/*` blocks it. None of the 5 names are among the **33** user-level agents *(was "34")*. | `CONTRADICTED` |
| H6 | AgentShield PreToolUse hook enforces PHI | Not in the repo. `~/.claude/settings.json` registers PreToolUse hooks for continuous-learning and GSD only. A **disabled** plugin's cache lists `agentshield-pack`; no hook from it is registered. | `NOT-EVIDENCED` |
| H7 | `recurring-failures.md` predicts real defects | 8 documented modes. Several 2026-09 findings match modes #1, #3, #5 and #8, and this pass adds more instances (see the follow-up). Matching is an interpretation, not a prediction test. | `CASE-STUDY` *(was AUDIT-VERIFIED)* |
| H8 | Dual Alembic chains separate master and profile schema | `migrations/master/versions` has 2 revisions (head `002_backup_schedules`); `migrations/profile/versions` has 12 (head `012_pinboards`); both linear. No test enforces a single head. | `VERIFIED` (current state; unenforced) |
| H9 | Invariant: `core.time.utcnow` only | 101 product lines in 30 files hold **109** `datetime.utcnow` references (AST), plus 16 in 6 test files (by AST; `git grep -n 'datetime\.utcnow'` gives 18 lines in 7 test files, because it also matches the string literal in `tests/test_profile_recovery.py:344,350`). The count is identical on both branch tips. `core.time.utcnow` is naive UTC (`core/time.py:9-11`). | `CONTRADICTED` — systemic *(was "~101 sites")* |
| H10 | FK cascades protect referential integrity | `PRAGMA foreign_keys` is set nowhere: the only product hit is a comment, `api/profiles.py:914`. Declared cascades are inert. | `CONTRADICTED` |
| H11 *(new)* | ModelRunner is the only LLM entry point | Live default path: yes (`modules/rag.py` → `core/model_runner.py`). Dormant bypass: `modules/model_selector.py:438` (`:456` after P1) `from llama_cpp import Llama`, reachable only via `interpret_with_model` (0 callers). Opt-in bypass: `core/external_runner.py` (cloud). No lint or test enforces the rule. | `PARTIAL` |

## Methodology claims

| # | Claim | Evidence | Verdict |
|---|---|---|---|
| M1 | Multi-agent audit catches single-agent errors | Two runs: the 2026-09-25 reconciler caught 3 sibling errors, and the planning pass caught 4 audit errors. On 2026-09-27 the orchestrator's re-check refuted 1 of the independent review's 17 findings (F-03) and corrected a mapping agent's "live bypass" claim (H11). A second reviewer then overturned the orchestrator's draft `refuted` on F-02 and caught 2 miscounts in the follow-up. None of these runs had seeded errors, a single-agent comparison, a denominator, or time/token accounting. | `CASE-STUDY` — "review found errors in these runs"; no capture rate or economic claim *(was "VERIFIED — twice")* |
| M2 | Gates prevent drift; prose doesn't | Drift was observed on ungated surfaces (Serena memories, tracker rows, `evals.md`). There was no systematic sample of gated surfaces and no A/B. | `HYPOTHESIS` — testable, untested *(was AUDIT-VERIFIED)* |
| M3 | Test counts are consistent across docs | 620 / 1160 / 1245 in three docs; plans 02, 05, 06 and 07 hard-coded 1245 for trees that will collect more. | `CONTRADICTED` |

## Usage

- Report prose may cite `VERIFIED` rows freely. A `PARTIAL` row may be cited only with its stated scope.
- `CASE-STUDY` and `HYPOTHESIS` rows appear as examples or future work, **never** as rates, causes, or economics.
- `REPORTED` rows need re-verification before they appear as fact.
- `CONTRADICTED` and `NOT-EVIDENCED` rows may appear **only as findings**: the report narrates the discrepancy and its fix, never the original claim.
- New rows: append with evidence links and bump `**Last Updated:**`.

Back to index: [README.md](README.md)
