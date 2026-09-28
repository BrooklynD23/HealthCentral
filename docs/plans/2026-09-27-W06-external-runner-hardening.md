# W-6 External Runner Hardening Implementation Plan

**Last Updated:** 2026-09-27
**Owner:** repository owner
**Refresh Trigger:** P1 merges (branches A + B land on main), W-10's governance commit merges, or any edit to `src/backend/core/external_runner.py`
**Status:** PROPOSED — not executed

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The opt-in external LLM runner always applies strict redaction. The only exception is an explicit break-glass. That exception now writes a PHI-free audit row before any text leaves, is refused when the row cannot be written, and is shown to the user as a warning in Settings.

**Architecture:** All runtime changes stay in `core/external_runner.py`. One module-level predicate, `redaction_bypass_active()`, decides whether break-glass is weakening redaction. `generate_async` forces `strict` whenever the predicate is false. When it is true, `generate_async` writes the audit row through `core.audit.create_audit_log` on its own master-DB session, and fails closed if that write fails. `GET /settings/model/external-api` exposes the same predicate as a read-only boolean. A new small component in the Settings page renders the warning from that boolean. No new config, no new env var, no new network destination.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy async (aiosqlite), pytest + pytest-asyncio; React 18 + TypeScript, vitest + Testing Library.

**Spec:** [owner-decisions-2026-09-27.md](../capstone-report/owner-decisions-2026-09-27.md) row D12; [handoff §5 row W-6](../../audit/2026-09-25/handoff-2026-09-27-execution.md).

---

## 1. Approval scope

**Owner text (D12, verbatim, [owner-decisions-2026-09-27.md](../capstone-report/owner-decisions-2026-09-27.md)):**

> "Keep the opt-in feature as a documented ModelRunner exception, but make strict redaction unconditional (remove the dev bypass; keep break-glass only with audit + UI warning). Amend CLAUDE.md to name the exception."

How each clause maps to work:

| D12 clause | Where it is done | Covered by this plan? |
|---|---|---|
| "Keep the opt-in feature" | nothing removed; `get_runner_for_request` and the provider calls are untouched | yes (no-op) |
| "as a documented ModelRunner exception" / "Amend CLAUDE.md to name the exception" | **W-10's** governance `docs:` commit | **no — dependency only** |
| "make strict redaction unconditional (remove the dev bypass)" | Task 1 | yes |
| "keep break-glass only with audit" | Task 2 | yes |
| "+ UI warning" | Tasks 3–4 | yes. It needs a read-only API field, because the frontend has no way to learn break-glass state today (§4.4). This plan reads that field as implied by "UI warning". It is listed for the owner's confirmation in §11 anyway |

**Does NOT license:**

1. Any edit to `src/backend/modules/redaction.py` (ask-first; read-only here).
2. Any edit to `src/backend/core/audit.py`, including its `ALLOWED_ACTIONS` / `ALLOWED_DETAIL_KEYS` allowlists. This plan passes `action == event_type` (the HC-AUD-010 pattern) and uses only keys that are already allowlisted.
3. Any new config field, env var, request flag or per-request break-glass trigger. `EXTERNAL_API_REDACTION_BREAK_GLASS` keeps its current meaning. Changing what break-glass *does* is out of scope.
4. Removing or weakening the production block (`core/external_runner.py:170-198` at B@7b2ff1f), the `is_available()` gate (`:126-136`) or `validate_startup` (`core/config.py:227-262` at B@7b2ff1f).
5. Any edit to the API-key encryption helpers `_get_profile_encryption_manager` / `_decrypt_or_migrate_api_key` (`core/external_runner.py:27-92`), or to `get_runner_for_request` (`:328-369`).
6. A new outbound destination, provider or HTTP client. The two existing URLs (`:267`, `:300`) stay the only ones.
7. Editing `CLAUDE.md`, `docs/compliance/data-privacy.md`, `skills/asclexis-guardrails/SKILL.md`, the capstone matrix or the contract. Those are W-10 / P4 / docs work. The one exception is the collected-count slots in `CLAUDE.md` and `AGENT.md`, and only if program gate SLOT-RULE is signed (§4.3 carve-out).
8. Routing the external runner through `ModelRunner`. D12 keeps it as a named exception.
9. A warning anywhere other than the Settings "External API" card, such as `ExplainAssistant.tsx`. That is owner question Q3.

## 2. Traceability

| ID | Source | Quoted text (verified by grep, 2026-09-27) |
|---|---|---|
| C-REDACT-2 | [architecture-engineering-contract.md](../capstone-report/architecture-engineering-contract.md) §6 | "**C-REDACT-2 · BINDING.** … The external runner MUST apply strict redaction before any network call, unconditionally (`CLAUDE.md:60`)." Known exceptions: "`redaction_enabled=False` skips redaction (`core/external_runner.py:201`); in production, break-glass bypasses the block (`:172`)." |
| C-LLM-1 | same file §7 | "**C-LLM-1 · BINDING.** … All LLM calls MUST go through the `ModelRunner` facade (`CLAUDE.md:25`)." Deviation 2: "**Live, opt-in:** `ExternalModelRunner` (`core/external_runner.py:95` …) … Whether it is an allowed exception is **OWNER-GATED**." |
| LOCAL-04 | [specs-compliance-matrix.md](../capstone-report/specs-compliance-matrix.md) line 42 | "The opt-in external LLM is off by default and redacted … **partial**: two bypasses." |
| LLM-01 | same file line 97 | "Live local inference goes through `ModelRunner` (the opt-in cloud `ExternalModelRunner`, `core/external_runner.py:95`, does not; owner-gated deviation)" |
| W-6 | [handoff §5](../../audit/2026-09-25/handoff-2026-09-27-execution.md) | "External runner: strict redaction is **unconditional**, with the dev bypass at `core/external_runner.py:201` removed. Break-glass is allowed only with an audit event and a UI warning." Tests HC-EXT-001/002/003; acceptance "3 tests; `tests/test_redaction.py` still green" |
| Program | [implementation-program.md](../capstone-report/implementation-program.md) D12 row | "Blocks: G-B3". "**DECIDED: keep, harden** (unconditional redaction; break-glass with audit + UI warning)" |

**Proposed matrix status change** (reported in the PR only; this plan does not edit the matrix): LOCAL-04 moves from `partial` to `tested` once Tasks 1–4 merge *and* W-10 names the exception. LLM-01 changes only its note: the deviation becomes "owner-approved exception (D12)" after W-10.

## 3. Verified current state (evidence for the plan)

`core/external_runner.py`, `tests/test_redaction.py`, `tests/test_external_runner.py` and `modules/redaction.py` are byte-identical at main@40f590e and B@7b2ff1f (`git diff --quiet` exit 0), and branch A does not touch them. **The executor must re-verify every line number on the post-P1 tree.**

### 3.1 The dev bypass is real, and it covers the default install

- `core/external_runner.py:201` (B@7b2ff1f): `if redaction_enabled:`. The whole `RedactionEngine` block (`:202-223`) is skipped when `REDACTION_ENABLED=false`, and nothing blocks the call outside production.
- A second, unlisted weakening: with `redaction_enabled=True`, `policy_level` comes from settings (`:168`). Outside production, `standard` or `minimal` is honoured, so DOB, address, MRN and numeric dates (strict-only rules, `modules/redaction.py:90-127` at B@7b2ff1f) are sent. "Strict … unconditional" covers this, so Task 1 fixes both.
- `app_env` defaults to `"development"` (`core/config.py:27` at B@7b2ff1f). **So the "dev bypass" applies to any install that has not set `APP_ENV=production`**, not only to developer machines. Defaults (`redaction_enabled=True`, `strict`, `:134-135`) keep it closed unless someone edits `.env`.

### 3.2 Every bypass path today

| # | Condition | Behaviour today | After this plan |
|---|---|---|---|
| 1 | any env, break-glass off, redaction on + `strict` | strict redaction | unchanged |
| 2 | dev, break-glass off, `REDACTION_ENABLED=false` | **unredacted** (`:201`) | strict (HC-EXT-001) |
| 3 | dev, break-glass off, redaction on + `standard`/`minimal` | **non-strict** (`:220`) | strict (HC-EXT-001) |
| 4 | prod, break-glass off, redaction off or non-strict | blocked (`:172-198`); startup also raises (`config.py:241-251`) | unchanged, still blocked |
| 5 | any env, break-glass on, redaction off or non-strict | unredacted / non-strict, plus a `logger.warning("SECURITY_AUDIT: …")` line (`:236-237`) | same data, but an audit row is written first, fail-closed (HC-EXT-002), and the UI warns (HC-EXT-003/004) |
| 6 | any env, break-glass on, redaction on + `strict` | strict | unchanged, no audit row (nothing is bypassed) |

Row 5 applies in dev today as well: the `:236` condition does not check `app_env`. Keeping break-glass env-independent therefore keeps its current meaning. The only behaviour removed is rows 2–3, which is D12's "dev bypass".

### 3.3 How break-glass is triggered

- Process-wide env var `EXTERNAL_API_REDACTION_BREAK_GLASS` → `Settings.external_api_redaction_break_glass` (`core/config.py:136-137` at B@7b2ff1f; pydantic `BaseSettings` with `env_file=".env"`, `:18-20`).
- There is no request flag, no per-profile setting, no API and no UI (`git grep -i break_glass` over `src/frontend` returns 0 hits on main, A and B).
- `validate_startup` adds a warning when it is set (`config.py:236-239`, `:252-262`). That warning goes to the startup log only.

### 3.4 Is break-glass audited today? No, not durably

- The only record is `logger.warning("SECURITY_AUDIT: %s", …)` at `core/external_runner.py:236-237`, an application-log line. **No `AuditLog` row is written.**
- The contract (C-AUDIT-2) records that no product code configures a file log handler, so the line reaches stderr only.
- It was once silently dropped by `fileConfig(disable_existing_loggers=True)`. See `docs/plans/implementation-log/2026-06-11_verification-report.md:24` and `tests/test_migration_logging_not_disabled.py`.

### 3.5 Who calls `get_runner_for_request` (B@7b2ff1f)

| Caller | Lines | Notes |
|---|---|---|
| `api/assistant.py` | `:754-755` | Wrapped in `except (ImportError, Exception): pass`. Runner passed to `rag.query(model_runner=runner)` at `:821` |
| `api/interpretations.py` | `:436-438` | Same pattern; `rag.query(model_runner=runner)` at `:443-452` |

`rag._generate_with_runner` awaits `runner.generate_async` (`modules/rag.py:1275-1291` at B@7b2ff1f), on the request's event loop. **So the fix belongs at `generate_async`: it is the single choke point both callers reach.** Neither route file is edited.

### 3.6 Audit API and row shape (B@7b2ff1f)

- Entry point: `create_audit_log(db, event_type, action, profile_id=None, entity_type=None, entity_id=None, details=None, client_info="Asclexis v0.1.0")` (`core/audit.py:201-266`).
- It runs `_scrub_action` (`:173-192`) and `_scrub_details` (`:118-170`) before `db.add`. It does not commit.
- `AuditLog` columns (`models/audit.py:33-60`): `id` (uuid), `profile_id` (FK `profiles.id`, nullable), `event_type` String(50), `action` String(500), `entity_type` String(50), `entity_id` String(36), `details_json` Text, `client_info` String(255), timestamp.
- The row this plan writes, field by field:

  | Column | Value | Why it carries no PHI |
  |---|---|---|
  | `event_type` | `"security.external_api.break_glass"` (33 chars) | static string |
  | `action` | same string | Passing `event_type` as `action` is the sanctioned no-warning path (HC-AUD-010, `tests/test_audit_phi_minimization.py:430`), so `core/audit.py` needs no edit |
  | `profile_id` | the session's UUID | UUIDs are already stored on every audit row |
  | `entity_type` | `"external_api"` | static string |
  | `entity_id` | `None` | — |
  | `details_json` | `{"trigger": "break_glass", "decision": "unredacted" \| "non_strict", "redaction_count": int \| null}` | All three keys are already allowlisted: `trigger` and `decision` in `STRING_DETAIL_KEYS` (`:69-76`), `redaction_count` in the counts set (`:97`) |

- **No prompt text, provider name, model name or API key is passed to `create_audit_log`.** HC-EXT-002 proves this by serialising every column and searching it for each PHI token in the fixture and for the API key.
- Non-route writers open their own master session with `core.database.async_session_maker` (`core/database.py:51`). Examples: `modules/backup_scheduler.py:103-107`, `modules/agent/tools/lookup_reference.py:56-59`. This plan follows that pattern.

### 3.7 Where the frontend could learn break-glass: nowhere today

- `GET /settings/model/external-api` returns `ExternalApiSettingsResponse{use_external_api, provider, model, api_key_configured}` (`api/model_settings.py:208-213`, handler `:690-716`, PUT `:719-757` at B@7b2ff1f).
- Frontend type: `ExternalApiSettings` (`src/frontend/src/services/modelSettings.ts:214-219` at B@7b2ff1f).
- UI: the "External API" card in `SettingsPage.tsx:665-677` (B@7b2ff1f).
- **So the UI warning must be built.** It needs one read-only response field and one small component.

### 3.8 Is `core/external_runner.py` ask-first?

**Treat it as ask-first.** It holds the API-key encryption helpers (`:27-92`, `EncryptionManager`), and it is the product's only sanctioned network path to a third party.

- D12 is the owner's explicit approval for the redaction and break-glass edits in `generate_async` (`:147-259`), plus two new module-level functions.
- Any hunk inside `:1-94` or `:261-369` is outside D12 → **stop gate S3**.

## 4. Files

### 4.1 Owned (create / modify)

| File | Change | Task |
|---|---|---|
| `src/backend/core/external_runner.py` | modify `generate_async` (`:165-239` at B@7b2ff1f); add `BREAK_GLASS_AUDIT_EVENT`, `redaction_bypass_active()`, `_record_break_glass_audit()` | 1, 2 |
| `src/backend/tests/test_external_runner_hardening.py` | **create**: HC-EXT-001, 002, 002b, 002c, 002d, 004, 004b | 1–3 |
| `src/backend/tests/test_redaction.py` | modify **one** existing test (`test_break_glass_allows_unredacted_call_with_audit_warning`, `:366-397` at B@7b2ff1f): add an audit-sink patch and one added assertion. **Zero lines removed** | 2 |
| `src/backend/api/model_settings.py` | add the `redaction_break_glass` field to `ExternalApiSettingsResponse` (`:208-213`) plus one import | 3 |
| `src/frontend/src/components/settings/ExternalApiBreakGlassWarning.tsx` | **create** | 4 |
| `src/frontend/src/__tests__/ExternalApiBreakGlassWarning.test.tsx` | **create**: HC-EXT-003, 003b, 003c | 4 |
| `src/frontend/src/services/modelSettings.ts` | add the optional `redaction_break_glass?: boolean` to `ExternalApiSettings` (`:214-219`) | 4 |
| `src/frontend/src/pages/SettingsPage.tsx` | add 1 import and 1 JSX line in the External API card (after `:674-677` at B@7b2ff1f) | 4 |

### 4.2 Read-only (must show zero diff at the end)

| Files | Why read-only |
|---|---|
| `src/backend/modules/redaction.py`, `modules/interpret_safety.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`, `core/auth.py` | ask-first (CLAUDE.md §1) |
| `src/backend/core/audit.py`, `src/backend/models/audit.py` | privacy-critical; no allowlist change needed |
| `src/backend/core/config.py` | no new config. Shared with P4 (comment edit at main@40f590e:109 = B@7b2ff1f:108) and possibly W-8 |
| `src/backend/api/assistant.py`, `src/backend/api/interpretations.py`, `src/backend/modules/rag.py` | callers; shared with W-4 and W-5 |
| `CLAUDE.md` | owned by W-10. Only exception: the collected-count slots, if SLOT-RULE is signed (§4.3 carve-out) |
| `docs/compliance/data-privacy.md`, `skills/asclexis-guardrails/SKILL.md`, `docs/capstone-report/*` | docs owned elsewhere (§12 lists the claims they need to update) |

### 4.3 Shared-file ordering

No two phases edit one file at the same time (program ground rules).

| File | Order | Reason |
|---|---|---|
| `src/frontend/src/pages/SettingsPage.tsx` | **P1 (A: `RecoveryCodeCard`; B: `TierCapabilities`) → W-6** | Both branches edit it. W-6 starts only after P1 merges |
| `src/frontend/src/services/modelSettings.ts` | P1 (B) → W-6 | |
| `src/backend/api/model_settings.py` | P1 (B) → **W-6 → P5** | P5 swaps `datetime.utcnow` at B@7b2ff1f:660 and :876. Recommended: W-6 merges before P5 starts, because W-6 is small. Otherwise W-6 waits for P5 to merge |
| `src/backend/core/external_runner.py` | W-6 only | W-7/G-B3's import-boundary test (HC-LLMB-001) may allowlist this path. That is a read, not an edit |
| `src/backend/tests/test_redaction.py` | W-6 only | If W-2 adds tests here, W-2 goes after W-6 |
| `CLAUDE.md` | W-10 only (invariant text); every collection-changing phase (collected-count slots) | W-6 never edits CLAUDE.md text. Count-slot carve-out below, owner-gated by SLOT-RULE |
| `core/config.py` | P1 → S-1 → P4 (N7 comment) → W-8 (program canonical order) | W-6 does not touch it |

**Count-slot carve-out (3a B-4; owner-gated by program gate SLOT-RULE, unsigned).**
- If SLOT-RULE is **signed**: commits 1–3 (the backend-test commits: +4, +8, +5 collected) each also update the collected-count slots, and only those: `CLAUDE.md` "**N backend tests collected.**" and "if it differs from N", and `AGENT.md` "N collected". N is the collected count measured just before that commit. Add `CLAUDE.md AGENT.md` to that commit's `git add`, its expected `--cached` list and its pathspec, as W-2 does. Never touch a pass-count slot ("all N pass", "N pass in CI", "N-1 without …"). Merges on these two lines are serial; the second PR re-measures.
- If SLOT-RULE is **unsigned**: W-6 does not touch either file. The PR body states "collected-count slots stale by +17 (SLOT-RULE unsigned)" for the orchestrator.

## 5. Dependencies

| Dependency | Kind | Why |
|---|---|---|
| **P1** merged (A + B on main) | hard | `SettingsPage.tsx`, `modelSettings.ts`, `api/model_settings.py` and `core/audit.py` change on B. Every line number here is labelled with its ref |
| **D9** — `~/venvs/asclexis-311/bin/python` built from `src/backend/requirements.txt` | hard | phase-gate interpreter. It does not exist yet (Wave 0). Stop if it is absent; never substitute another interpreter silently |
| **D12** | hard, given | scope in §1 |
| **W-10** governance commit | soft for the code, hard for "D12 done" | W-6's code can merge without it. D12 and LOCAL-04 are **not** reported closed until CLAUDE.md names the exception (§11 Q2 → GOV-BG, W-10 §10) |
| P5 | ordering only | shares `api/model_settings.py` (§4.3) |
| P6 (FK pragma ON) | awareness | After P6, `audit_logs.profile_id` must reference an existing `profiles.id`. HC-EXT-002d seeds a profile, so it holds on both sides of P6 |
| Downstream: **G-B3 / W-7** | W-6 unblocks it | The program says D12 blocks G-B3. The boundary test may allowlist `core/external_runner.py` only after D12 plus W-10 |

## 6. Global constraints

- Python 3.11 target; no 3.12-only syntax. Use `core.time.utcnow` (naive UTC) for any timestamp; only the 002d fixture needs one.
- No network in tests. `_call_openai` / `_call_anthropic` are always patched.
- Never lower a threshold. Never remove an assertion from an existing test.
- Test IDs: `HC-EXT-NNN`. The prefix had 0 hits on main, A and B (`git grep -i 'HC-EXT\|hc_ext_'`, 2026-09-27). Re-check in Task 0.
- The frontend toolchain runs on **Windows** (vitest stalls on `/mnt/c` under WSL).
- User-visible copy is plain language, educational, and gives no medical advice.

## 7. Review focus

These are the failure modes most likely to reach a patient that the D12 text does not spell out. Each one is pinned by a test in the task named.

1. **Non-strict policy outside production** (`standard`/`minimal`) silently leaks DOB/MRN. Pinned by the HC-EXT-001 `standard` and `minimal` cases (Task 1).
2. **Audit row written *after* dispatch**, so a crash between the two leaves an unaudited send. Pinned by HC-EXT-002's order assertion (Task 2).
3. **Audit store unavailable** (master DB locked, missing or migrating), so break-glass proceeds unaudited. Pinned by HC-EXT-002b (Task 2).
4. **Row too long or FK-invalid in a real schema** (String(50) `event_type`; FK once P6 turns it on). A fake session cannot show this. Pinned by HC-EXT-002d on a real aiosqlite master schema (Task 2).
5. **The PUT response reports `false` while break-glass is on**, or the page shows a stale "safe" state. Pinned by using a `default_factory` field, so every constructor site reports the truth, and by HC-EXT-004b, an HTTP PUT (Task 3).

---

## Task 0: Phase-start measurement (no commit)

**Files:** none modified.

- [ ] **Step 1: Create the phase worktree and confirm the tree and refs.** Only after P1 is merged to `origin/main` (program P1). From the main checkout:

```bash
export WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w06    # Windows: C:\Users\DangT\Documents\GitHub\hc-w06
git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral fetch origin
git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral worktree add "$WT" -b feat/w06-external-runner-hardening origin/main
cd "$WT"
git merge-base --is-ancestor 7b2ff1f HEAD && git merge-base --is-ancestor 692fdf3 HEAD && echo post-P1-ok   # expect: post-P1-ok; else STOP (P1 not landed)
git rev-parse --short HEAD
git status --short          # expect: empty
git log --oneline -1 -- src/backend/core/external_runner.py
```

Record all three outputs in the PR body.

**Every later bash block starts with an absolute `cd` built from `$WT`.** Blocks never `cd` relative to a previous block. If your shell does not keep variables between calls, re-run the `export WT=…` line above first; the `${WT:?…}` guard stops the block if you forget.

- [ ] **Step 2: Confirm the interpreter (D9).**

```bash
~/venvs/asclexis-311/bin/python --version     # expect: Python 3.11.x
```

If the file is missing: **STOP (S7)**. Do not fall back to another interpreter without the owner's say-so.

- [ ] **Step 3: Measure the backend start state.**

```bash
cd "${WT:?export WT per Task 0 Step 1}"/src/backend
find . -name __pycache__ -type d -prune -exec rm -rf {} +
~/venvs/asclexis-311/bin/python -B -m pytest tests/ --collect-only -q -p no:cacheprovider 2>&1 | tail -1; echo "collect exit=${PIPESTATUS[0]}"
~/venvs/asclexis-311/bin/python -B -m pytest tests/ -p no:cacheprovider -q 2>&1 | tail -15; echo "full-suite exit=${PIPESTATUS[0]}"
~/venvs/asclexis-311/bin/python -B -m pytest tests/test_redaction.py tests/test_external_runner.py tests/test_config_validation.py tests/test_model_settings_api.py -p no:cacheprovider -q 2>&1 | tail -3; echo "targeted exit=${PIPESTATUS[0]}"   # expect 0
```

Record: `START_COLLECTED=<n>`, `START_FAILURES=<list of node ids>`, all three exit codes, and the targeted-file result. `collect exit` must be 0. `full-suite exit` is non-zero exactly when `START_FAILURES` is non-empty. The targeted files must all pass (`targeted exit=0`). Anything else is **STOP (S6)**.

- [ ] **Step 4: Measure the frontend start state (Windows PowerShell).**

```powershell
Set-Location C:\Users\DangT\Documents\GitHub\hc-w06\src\frontend
npx tsc --noEmit; "tsc exit=$LASTEXITCODE"   # record; nonzero at start is recorded, not fixed here
npx vitest run 2>&1 | Select-Object -Last 6; "vitest exit=$LASTEXITCODE"   # $LASTEXITCODE is npx's (Select-Object is a cmdlet)
```

Record: tsc exit code, vitest exit code, and vitest files/tests passed/failed.

- [ ] **Step 5: Confirm no ID collision and re-anchor the lines.**

```bash
cd "${WT:?export WT per Task 0 Step 1}"
git grep -n -i 'HC-EXT\|hc_ext_' -- src | wc -l        # expect: 0
grep -n "if redaction_enabled:" src/backend/core/external_runner.py          # expect: one hit (201 at B@7b2ff1f)
grep -n "break_glass and (not redaction_enabled" src/backend/core/external_runner.py   # expect: one hit (236 at B@7b2ff1f)
grep -n "class ExternalApiSettingsResponse" src/backend/api/model_settings.py
grep -n "External API Section" src/frontend/src/pages/SettingsPage.tsx
```

Use the fresh line numbers from here on. A non-zero ID count, or a missing anchor, is **STOP (S6)**.

---

## Task 1: Strict redaction is unconditional outside break-glass (HC-EXT-001)

**Files:**
- Create: `src/backend/tests/test_external_runner_hardening.py`
- Modify: `src/backend/core/external_runner.py` (add functions after `_decrypt_or_migrate_api_key`, i.e. after `:92`; edit `generate_async` at `:200-201`, B@7b2ff1f)

**Interfaces:**
- Produces: `redaction_bypass_active() -> bool` in `core.external_runner`. It reads the module global `settings`, so `patch("core.external_runner.settings")` controls it. Task 2 and Task 3 use it.

- [ ] **Step 1: Write the failing test.** Create `src/backend/tests/test_external_runner_hardening.py`:

```python
"""HC-EXT-001…004 — D12 (owner, 2026-09-27): external runner hardening.

"make strict redaction unconditional (remove the dev bypass; keep break-glass
only with audit + UI warning)". See
docs/plans/2026-09-27-W06-external-runner-hardening.md.

No test here touches the network: the provider call is always patched.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.external_runner import ExternalModelRunner
from core.model_runner import InferenceResult

PROFILE = "profile-a"
API_KEY = "test-key-do-not-log"

# Tokens covering every strict rule class that matters here. DOB and MRN are
# strict-ONLY (modules/redaction.py), so they prove the level is strict, not
# merely "some redaction ran".
PHI_PROMPT = (
    "Patient: John Doe DOB: 01/15/1990 MRN: 8834412 SSN 123-45-6789 "
    "takes metformin 500 mg, HbA1c 7.2"
)
REDACTABLE_TOKENS = ("John Doe", "01/15/1990", "8834412", "123-45-6789")


def _runner() -> ExternalModelRunner:
    return ExternalModelRunner(provider="openai", api_key=API_KEY, profile_id=PROFILE)


def _set(mock_settings, *, env: str, enabled: bool, level: str, break_glass: bool) -> None:
    mock_settings.app_env = env
    mock_settings.redaction_enabled = enabled
    mock_settings.redaction_policy_level = level
    mock_settings.external_api_redaction_break_glass = break_glass


def _capturing(sent: list[str], order: list[str] | None = None):
    async def _fake_call(prompt, config):
        if order is not None:
            order.append("dispatch")
        sent.append(prompt)
        return InferenceResult(text="ok", tokens_generated=1, finish_reason="stop", model_name="m")
    return _fake_call


# ---------------------------------------------------------------------------
# HC-EXT-001 — no dev bypass: without break-glass, the prompt is always
# strictly redacted, whatever REDACTION_ENABLED / REDACTION_POLICY_LEVEL say.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "enabled,level",
    [(False, "strict"), (False, "standard"), (True, "standard"), (True, "minimal")],
)
async def test_hc_ext_001_dev_without_break_glass_always_redacts_strictly(enabled, level):
    runner = _runner()
    sent: list[str] = []
    with patch.object(runner, "_call_openai", side_effect=_capturing(sent)), \
         patch("core.external_runner.settings") as s:
        _set(s, env="development", enabled=enabled, level=level, break_glass=False)
        result = await runner.generate_async(PHI_PROMPT)

    assert result.finish_reason == "stop"
    assert len(sent) == 1, "provider was not called exactly once"
    for token in REDACTABLE_TOKENS:
        assert token not in sent[0], f"{token!r} left the device (enabled={enabled}, level={level})"
```

- [ ] **Step 2: Run the test to verify it fails.**

```bash
cd "${WT:?export WT per Task 0 Step 1}"/src/backend && ~/venvs/asclexis-311/bin/python -B -m pytest tests/test_external_runner_hardening.py -k hc_ext_001 -p no:cacheprovider -q
```

Expected: `4 failed`. Each fails with `AssertionError: '123-45-6789' left the device (enabled=False, …)`, or, for the `standard`/`minimal` cases, `'01/15/1990' left the device …`. A pass here means the bypass is already gone. **STOP (S6)**: re-read the code, because the premise is wrong.

- [ ] **Step 3: Minimal implementation.** In `core/external_runner.py`, add after `_decrypt_or_migrate_api_key` (after `:92` at B@7b2ff1f):

```python
def redaction_bypass_active() -> bool:
    """D12 (owner, 2026-09-27): is break-glass currently weakening redaction?

    True only when EXTERNAL_API_REDACTION_BREAK_GLASS is set AND the configured
    redaction is weaker than strict. Without break-glass, the external runner
    always applies strict redaction, whatever REDACTION_ENABLED /
    REDACTION_POLICY_LEVEL say. Also read by GET /settings/model/external-api
    so the UI can warn (one predicate, so the warning cannot drift from the
    runner).
    """
    if getattr(settings, "external_api_redaction_break_glass", False) is not True:
        return False
    enabled = getattr(settings, "redaction_enabled", False) is True
    level = getattr(settings, "redaction_policy_level", "strict")
    return (not enabled) or level != "strict"
```

In `generate_async`, leave the production block (`:170-198`) untouched. Replace the two lines at `:200-201`:

```python
        redacted_count: Optional[int] = None
        if redaction_enabled:
```

with:

```python
        # D12 (owner, 2026-09-27): strict redaction is unconditional. The only
        # exception is break-glass, which is audited and shown in the UI.
        bypass = redaction_bypass_active()
        if not bypass:
            redaction_enabled = True
            policy_level = "strict"

        redacted_count: Optional[int] = None
        if redaction_enabled:
```

Then change the condition at `:236` from `if break_glass and (not redaction_enabled or policy_level != "strict"):` to `if bypass:`. The two are equivalent on the bypass path. After the forcing above, the old expression would be false on every non-bypass path.

- [ ] **Step 4: Run the tests to verify they pass, and that nothing adjacent broke.**

```bash
cd "${WT:?export WT per Task 0 Step 1}"/src/backend && ~/venvs/asclexis-311/bin/python -B -m pytest tests/test_external_runner_hardening.py tests/test_redaction.py tests/test_external_runner.py tests/test_config_validation.py -p no:cacheprovider -q
```

Expected: all pass. That includes `4 passed` for HC-EXT-001 and every `TestExternalRunnerIntegration` test unchanged. (`test_redaction_applied_before_provider_dispatch` uses `standard` and asserts on SSN, which strict also redacts.)

- [ ] **Step 5: Break it on purpose (recurring-failures #1).** Temporarily change `if not bypass:` to `if False:`. Re-run `-k hc_ext_001` and expect `4 failed`. Revert, re-run, and expect `4 passed`. Record both outputs.

- [ ] **Step 6: What would this test fail to notice?** It does not see production (production is pinned by the existing `test_production_blocks_*` tests), or Anthropic dispatch (same code path before `_call_*`). It also does not cover PHI shapes the strict engine has no rule for, such as a bare name without a "Patient:" label or a medication name. Those are a `redaction.py` coverage question. They are out of scope (ask-first); name them in the PR.

- [ ] **Step 7: Commit.**

```bash
cd "${WT:?export WT per Task 0 Step 1}"
# SLOT-RULE signed only (§4.3 carve-out): update the collected-count slots first, then add CLAUDE.md AGENT.md to git add, the expected list and the pathspec
git add src/backend/core/external_runner.py src/backend/tests/test_external_runner_hardening.py
git diff --cached --name-only    # expect exactly those 2 paths
git commit -m "fix(external-runner): make strict redaction unconditional outside break-glass (D12)" -m "Removes the dev bypass at core/external_runner.py:201: without break-glass the prompt is always redacted at policy 'strict'. HC-EXT-001. Owner decision D12, docs/capstone-report/owner-decisions-2026-09-27.md." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- src/backend/core/external_runner.py src/backend/tests/test_external_runner_hardening.py
```

---

## Task 2: Break-glass writes a PHI-free audit row first, or is refused (HC-EXT-002, 002b, 002c, 002d)

**Files:**
- Modify: `src/backend/core/external_runner.py` (new `_record_break_glass_audit`; the bypass branch at old `:236-239`)
- Modify: `src/backend/tests/test_external_runner_hardening.py` (append)
- Modify: `src/backend/tests/test_redaction.py` (the one existing break-glass test, `:366-397` at B@7b2ff1f; additions only)

**Interfaces:**
- Consumes: `redaction_bypass_active()` (Task 1).
- Produces:
  - `BREAK_GLASS_AUDIT_EVENT = "security.external_api.break_glass"`.
  - `async def _record_break_glass_audit(*, profile_id: Optional[str], decision: str, redaction_count: Optional[int]) -> None`. It raises on failure; the caller fails closed.
  - Tests patch `core.external_runner._record_break_glass_audit` or `core.database.async_session_maker`.

- [ ] **Step 1: Write the failing tests.** Append to `test_external_runner_hardening.py`:

```python
# ---------------------------------------------------------------------------
# HC-EXT-002 — break-glass writes one audit row, with no PHI, BEFORE dispatch.
# ---------------------------------------------------------------------------

class _RecordingMasterDb:
    """Stands in for a master-DB session; records what would be written."""

    def __init__(self, order: list[str]) -> None:
        self.added: list[object] = []
        self.commits = 0
        self._order = order

    def add(self, obj: object) -> None:
        self._order.append("audit_add")
        self.added.append(obj)

    async def commit(self) -> None:
        self._order.append("audit_commit")
        self.commits += 1

    async def rollback(self) -> None:  # pragma: no cover
        pass

    def audit_rows(self) -> list[object]:
        return [o for o in self.added if type(o).__name__ == "AuditLog"]


def _maker_for(db):
    @asynccontextmanager
    async def _session():
        yield db
    return lambda: _session()


_AUDIT_COLUMNS = (
    "profile_id", "event_type", "action", "entity_type", "entity_id",
    "details_json", "client_info",
)
_MUST_NOT_APPEAR = REDACTABLE_TOKENS + ("John", "Doe", "metformin", "HbA1c", "7.2", API_KEY, "openai")


@pytest.mark.asyncio
@pytest.mark.parametrize("env", ["development", "production"])
@pytest.mark.parametrize(
    "enabled,level,decision",
    [(False, "strict", "unredacted"), (True, "standard", "non_strict")],
)
async def test_hc_ext_002_break_glass_writes_phi_free_audit_row_before_dispatch(env, enabled, level, decision):
    from core.audit import ALLOWED_DETAIL_KEYS

    order: list[str] = []
    sent: list[str] = []
    master = _RecordingMasterDb(order)
    runner = _runner()
    with patch.object(runner, "_call_openai", side_effect=_capturing(sent, order)), \
         patch("core.external_runner.settings") as s, \
         patch("core.database.async_session_maker", _maker_for(master)):
        _set(s, env=env, enabled=enabled, level=level, break_glass=True)
        result = await runner.generate_async(PHI_PROMPT)

    assert result.finish_reason == "stop"
    rows = master.audit_rows()
    assert len(rows) == 1, f"expected one break-glass audit row, got {len(rows)}"
    assert master.commits == 1, "audit row was added but never committed"
    assert order == ["audit_add", "audit_commit", "dispatch"], f"audit row must be committed before dispatch, got {order}"

    row = rows[0]
    assert row.event_type == "security.external_api.break_glass"
    assert row.profile_id == PROFILE
    details = json.loads(row.details_json)
    assert details["trigger"] == "break_glass"
    assert details["decision"] == decision
    assert "_scrubbed" not in details, f"a non-allowlisted key was passed: {details}"
    assert set(details) <= ALLOWED_DETAIL_KEYS

    dump = json.dumps({c: getattr(row, c) for c in _AUDIT_COLUMNS}, default=str)
    for token in _MUST_NOT_APPEAR:
        assert token not in dump, f"{token!r} reached the unencrypted master DB audit row"


# HC-EXT-002b — no audit row, no break-glass: fail closed.
@pytest.mark.asyncio
async def test_hc_ext_002b_break_glass_is_refused_when_audit_cannot_be_written():
    sent: list[str] = []
    runner = _runner()
    with patch.object(runner, "_call_openai", side_effect=_capturing(sent)), \
         patch("core.external_runner.settings") as s, \
         patch("core.external_runner._record_break_glass_audit",
               AsyncMock(side_effect=RuntimeError("master db unavailable"))):
        _set(s, env="production", enabled=False, level="strict", break_glass=True)
        result = await runner.generate_async(PHI_PROMPT)

    assert sent == [], "an unaudited break-glass prompt left the device"
    assert result.finish_reason == "error"
    assert "audit" in result.text.lower()


# HC-EXT-002c — no row when nothing is bypassed (keeps the audit trail meaningful).
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "break_glass,enabled,level",
    [(False, False, "standard"), (True, True, "strict")],
)
async def test_hc_ext_002c_no_break_glass_row_when_redaction_is_strict(break_glass, enabled, level):
    sink = AsyncMock()
    sent: list[str] = []
    runner = _runner()
    with patch.object(runner, "_call_openai", side_effect=_capturing(sent)), \
         patch("core.external_runner.settings") as s, \
         patch("core.external_runner._record_break_glass_audit", sink, create=True):
        _set(s, env="development", enabled=enabled, level=level, break_glass=break_glass)
        await runner.generate_async(PHI_PROMPT)

    sink.assert_not_awaited()
    assert len(sent) == 1 and "123-45-6789" not in sent[0]


# HC-EXT-002d — the row persists in a real master schema (column lengths, FK).
@pytest.mark.asyncio
async def test_hc_ext_002d_break_glass_row_persists_in_real_master_schema(tmp_path):
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    import models  # noqa: F401  (registers master tables on Base.metadata)
    from core.database import Base
    from core.time import utcnow
    from models.audit import AuditLog
    from models.profile import Profile

    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'master.db'}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as db:
        now = utcnow()
        db.add(Profile(id=PROFILE, display_name="T", encryption_key_id="k",
                       created_at=now, updated_at=now))
        await db.commit()

    sent: list[str] = []
    runner = _runner()
    try:
        with patch.object(runner, "_call_openai", side_effect=_capturing(sent)), \
             patch("core.external_runner.settings") as s, \
             patch("core.database.async_session_maker", maker):
            _set(s, env="production", enabled=False, level="strict", break_glass=True)
            result = await runner.generate_async(PHI_PROMPT)
        async with maker() as db:
            rows = (await db.execute(select(AuditLog))).scalars().all()
    finally:
        await engine.dispose()

    assert result.finish_reason == "stop"
    assert [r.event_type for r in rows] == ["security.external_api.break_glass"]
    assert rows[0].profile_id == PROFILE
```

`create=True` on 002c lets it run before the function exists. 002b deliberately omits `create=True`, so it fails at RED.

- [ ] **Step 2: Run the tests to verify they fail.**

```bash
cd "${WT:?export WT per Task 0 Step 1}"/src/backend && ~/venvs/asclexis-311/bin/python -B -m pytest tests/test_external_runner_hardening.py -k "hc_ext_002" -p no:cacheprovider -q
```

Expected:
- HC-EXT-002 ×4 fail with `AssertionError: expected one break-glass audit row, got 0`.
- HC-EXT-002b fails with `AttributeError: <module 'core.external_runner' …> does not have the attribute '_record_break_glass_audit'`.
- HC-EXT-002d fails with `AssertionError: assert [] == ['security.external_api.break_glass']`.
- HC-EXT-002c ×2 **pass** at RED by construction: no row is ever written today. Its red run is the break-it step below.
- Total: `6 failed, 2 passed`.

- [ ] **Step 3: Minimal implementation.** In `core/external_runner.py`, add next to `redaction_bypass_active`:

```python
BREAK_GLASS_AUDIT_EVENT = "security.external_api.break_glass"


async def _record_break_glass_audit(
    *,
    profile_id: Optional[str],
    decision: str,
    redaction_count: Optional[int],
) -> None:
    """Write the D12 break-glass audit row to the master DB, or raise.

    Only static strings, the profile UUID and a count are written: never the
    prompt, provider, model or key (AUDIT-PHI-001; audit rows live in the
    unencrypted master DB). action == event_type is the sanctioned
    no-warning path through core.audit._scrub_action (HC-AUD-010).
    """
    from .audit import create_audit_log
    from .database import async_session_maker

    async with async_session_maker() as db:
        await create_audit_log(
            db=db,
            event_type=BREAK_GLASS_AUDIT_EVENT,
            action=BREAK_GLASS_AUDIT_EVENT,
            profile_id=profile_id,
            entity_type="external_api",
            details={
                "trigger": "break_glass",
                "decision": decision,
                "redaction_count": redaction_count,
            },
        )
        await db.commit()
```

Replace the `if bypass:` / `else:` logging block (old `:236-239`) with:

```python
        if bypass:
            logger.warning("SECURITY_AUDIT: %s", json.dumps(audit_data, default=str))
            try:
                await _record_break_glass_audit(
                    profile_id=self._profile_id,
                    decision="unredacted" if not redaction_enabled else "non_strict",
                    redaction_count=redacted_count,
                )
            except Exception as exc:
                logger.error(
                    "External API call blocked: break-glass audit row could not be written",
                    extra={
                        "provider": self._provider,
                        "profile_id": self._profile_id,
                        "error_type": type(exc).__name__,
                    },
                )
                return InferenceResult(
                    text="External API error: break-glass audit could not be recorded",
                    tokens_generated=0,
                    finish_reason="error",
                    model_name=self._model,
                )
        else:
            logger.info("SECURITY_AUDIT: %s", json.dumps(audit_data, default=str))
```

Keep the `try:` provider dispatch that follows (`:241-259`) unchanged.

- [ ] **Step 4: Keep the existing break-glass test off the real master DB, in the same step.** Without a patch, `test_break_glass_allows_unredacted_call_with_audit_warning` would now open `core.database.async_session_maker`, which is bound to `settings.database_url`. That either writes to a real master DB or fails closed. **Do not run it unpatched.** In `tests/test_redaction.py` (`:388-397` at B@7b2ff1f), change:

```python
        with patch.object(runner, "_call_openai", side_effect=mock_call_openai):
            with patch("core.external_runner.settings") as mock_settings:
```

to:

```python
        with patch.object(runner, "_call_openai", side_effect=mock_call_openai), \
             patch("core.external_runner._record_break_glass_audit", new=AsyncMock()) as audit_sink:
            with patch("core.external_runner.settings") as mock_settings:
```

Then append after the last existing assertion (`:397`):

```python
        audit_sink.assert_awaited_once()  # D12: break-glass only with audit
```

`AsyncMock` is already imported (`:9`). Verify additions only:

```bash
cd "${WT:?export WT per Task 0 Step 1}"
git diff -U0 src/backend/tests/test_redaction.py | grep -c '^-[^-]'
```

Expected: `1`. That one line is the old single-context `with patch.object(...)` line, which is re-added with the second context. Anything else removed is **STOP (S5)**.

- [ ] **Step 5: Run the tests to verify they pass.**

```bash
cd "${WT:?export WT per Task 0 Step 1}"/src/backend && ~/venvs/asclexis-311/bin/python -B -m pytest tests/test_external_runner_hardening.py tests/test_redaction.py tests/test_external_runner.py tests/test_audit_phi_minimization.py tests/test_migration_logging_not_disabled.py -p no:cacheprovider -q
```

Expected: all pass. HC-EXT 001 + 002 group = 4 + 4 + 1 + 2 + 1 = 12 passed. `test_redaction.py` has the same count as at Task 0, all green.

- [ ] **Step 6: Break it on purpose, three ways.** Revert after each and re-run to green; record every output.
  1. Comment out the `await _record_break_glass_audit(...)` call. Expect HC-EXT-002 ×4, 002d and the patched `test_break_glass_allows_…` to fail.
  2. Move the `if bypass:` audit block to *after* the provider `try:` block. Expect HC-EXT-002 ×4 to fail on `audit must precede dispatch`.
  3. Replace the `except` body with `pass`. Expect HC-EXT-002b to fail on `an unaudited break-glass prompt left the device`.
  4. Also: change `redaction_bypass_active` to `return True` on its first line. Expect HC-EXT-002c to fail.

- [ ] **Step 7: What would these tests fail to notice?**
  - The sync `ExternalModelRunner.generate()` (`:138-145`) wraps `asyncio.run`. An engine bound to another loop could then raise, and break-glass would fail *closed*: safe, but unavailable. No caller uses `generate()` today (§3.5); name it in the PR.
  - They also cannot see whether an operator reads the rows. Retention is P8 brief 4 / W-9.

- [ ] **Step 8: Commit.**

```bash
cd "${WT:?export WT per Task 0 Step 1}"
# SLOT-RULE signed only (§4.3 carve-out): update the collected-count slots first, then add CLAUDE.md AGENT.md to git add, the expected list and the pathspec
git add src/backend/core/external_runner.py src/backend/tests/test_external_runner_hardening.py src/backend/tests/test_redaction.py
git diff --cached --name-only    # expect exactly those 3 paths
git commit -m "fix(external-runner): audit break-glass before dispatch and fail closed (D12)" -m "Break-glass now writes a PHI-free AuditLog row (event security.external_api.break_glass; details trigger/decision/redaction_count only) before any prompt leaves, and the call is refused if the row cannot be written. HC-EXT-002/002b/002c/002d. test_redaction.py: one existing test gains an audit-sink patch and one assertion; no assertion removed." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- src/backend/core/external_runner.py src/backend/tests/test_external_runner_hardening.py src/backend/tests/test_redaction.py
```

---

## Task 3: The settings API reports break-glass state (HC-EXT-004, 004b)

**Files:**
- Modify: `src/backend/api/model_settings.py` (`ExternalApiSettingsResponse`, `:208-213` at B@7b2ff1f; imports near `:22-26`)
- Modify: `src/backend/tests/test_external_runner_hardening.py` (append)

**Interfaces:**
- Consumes: `redaction_bypass_active()` (Task 1).
- Produces: JSON field `redaction_break_glass: bool` on every `ExternalApiSettingsResponse` (GET and PUT `/settings/model/external-api`). Task 4 reads it.

- [ ] **Step 1: Write the failing tests** (through HTTP with `route_client`: `tests/support/routes.py:27-58`, signature `route_client(router, prefix, profile_id="profile-a", master_db=None)`; the profile DB is overridden per `tests/test_tier_capabilities.py` at B@7b2ff1f):

```python
# ---------------------------------------------------------------------------
# HC-EXT-004 — the frontend can learn break-glass state (for the UI warning).
# Through HTTP (recurring-failures #1): a direct call cannot see Depends(...).
# ---------------------------------------------------------------------------

def _get_external_api(user_row):
    from api.model_settings import router as ms_router
    from core.auth import get_profile_db_session
    from tests.support.routes import route_client

    with patch("api.model_settings._get_user_settings", AsyncMock(return_value=user_row)):
        with route_client(ms_router, "/settings/model", profile_id=PROFILE) as client:
            async def _profile_db():
                return MagicMock()
            client.app.dependency_overrides[get_profile_db_session] = _profile_db
            return client.get("/settings/model/external-api")


@pytest.mark.parametrize(
    "break_glass,enabled,level,expected",
    [
        (True, False, "strict", True),
        (True, True, "standard", True),
        (True, True, "strict", False),
        (False, False, "standard", False),
    ],
)
def test_hc_ext_004_external_api_settings_reports_break_glass(break_glass, enabled, level, expected):
    with patch("core.external_runner.settings") as s:
        _set(s, env="development", enabled=enabled, level=level, break_glass=break_glass)
        resp = _get_external_api(user_row=None)
    assert resp.status_code == 200, resp.text
    assert resp.json()["redaction_break_glass"] is expected


def test_hc_ext_004b_put_response_reports_break_glass_too():
    """The PUT handler (api/model_settings.py:719-757 @B) builds its own
    ExternalApiSettingsResponse; it must not report a stale False."""
    from api.model_settings import router as ms_router
    from core.auth import get_profile_db_session, get_profile_encryption_manager
    from tests.support.routes import route_client

    row = MagicMock(use_external_api=False, external_api_provider="",
                    external_api_key_encrypted="gAAAAAxyz")
    profile_db = AsyncMock()  # the handler awaits profile_db.commit()

    with patch("core.external_runner.settings") as s, \
         patch("api.model_settings._get_or_create_user_settings", AsyncMock(return_value=row)):
        _set(s, env="production", enabled=False, level="strict", break_glass=True)
        with route_client(ms_router, "/settings/model", profile_id=PROFILE) as client:
            async def _profile_db():
                return profile_db

            async def _enc():
                return MagicMock()

            client.app.dependency_overrides[get_profile_db_session] = _profile_db
            client.app.dependency_overrides[get_profile_encryption_manager] = _enc
            resp = client.put(
                "/settings/model/external-api",
                json={"use_external_api": True, "provider": "openai", "api_key": "",
                      "consent_acknowledged": True},
            )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["use_external_api"] is True
    assert body["redaction_break_glass"] is True
    assert "gAAAAAxyz" not in resp.text
    profile_db.commit.assert_awaited_once()
```

`api_key` is empty, so the handler never calls the encryption manager (`:743`). The override only satisfies `Depends(get_profile_encryption_manager)` (`core/auth.py:340-358` @B).

- [ ] **Step 2: Run to verify they fail.**

```bash
cd "${WT:?export WT per Task 0 Step 1}"/src/backend && ~/venvs/asclexis-311/bin/python -B -m pytest tests/test_external_runner_hardening.py -k hc_ext_004 -p no:cacheprovider -q
```

Expected: `5 failed`, each with `KeyError: 'redaction_break_glass'`. A `401`/`422` instead means the dependency overrides are wrong. Fix the test harness, never the route.

- [ ] **Step 3: Minimal implementation.** In `api/model_settings.py`, add the import beside the other `core.*` imports (`:22-24` at B@7b2ff1f):

```python
from core.external_runner import redaction_bypass_active
```

and in `ExternalApiSettingsResponse` (`:208-213`) add one field:

```python
    # D12: true while EXTERNAL_API_REDACTION_BREAK_GLASS is weakening redaction.
    # Read-only; computed on every construction so GET and PUT cannot disagree.
    redaction_break_glass: bool = Field(default_factory=redaction_bypass_active)
```

`Field` is already imported (`:19`). The three constructor sites (`:704`, `:711`, `:752`) stay unchanged.

- [ ] **Step 4: Run to verify they pass, plus the existing settings tests and the app boot.**

```bash
cd "${WT:?export WT per Task 0 Step 1}"/src/backend
~/venvs/asclexis-311/bin/python -B -m pytest tests/test_external_runner_hardening.py tests/test_model_settings_api.py tests/test_tier_capabilities.py -p no:cacheprovider -q
~/venvs/asclexis-311/bin/python -B -c "from main import app; print('ok')"
```

Expected: all pass (HC-EXT total 17), and `ok`. An import cycle here is **STOP (S6)**. Do not move the import into a function to hide it without reporting it.

- [ ] **Step 5: Break it on purpose.** Replace `default_factory=redaction_bypass_active` with `default=False`. Expect HC-EXT-004 (2 True cases) and 004b to fail. Revert and re-run to green.

- [ ] **Step 6: What would this fail to notice?**
  - That the frontend renders it. That is Task 4.
  - That a *remote* viewer can read it. The route sits behind `RequireAuth` like its siblings, and the value is a boolean about server config, not patient data.

- [ ] **Step 7: Commit.**

```bash
cd "${WT:?export WT per Task 0 Step 1}"
# SLOT-RULE signed only (§4.3 carve-out): update the collected-count slots first, then add CLAUDE.md AGENT.md to git add, the expected list and the pathspec
git add src/backend/api/model_settings.py src/backend/tests/test_external_runner_hardening.py
git diff --cached --name-only    # expect exactly those 2 paths
git commit -m "feat(model-settings): report break-glass redaction state to the UI (D12)" -m "ExternalApiSettingsResponse gains read-only redaction_break_glass, computed from core.external_runner.redaction_bypass_active so the warning cannot drift from the runner. HC-EXT-004/004b over HTTP." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- src/backend/api/model_settings.py src/backend/tests/test_external_runner_hardening.py
```

---

## Task 4: The Settings page warns while break-glass is active (HC-EXT-003, 003b, 003c) — Windows

**Files:**
- Create: `src/frontend/src/components/settings/ExternalApiBreakGlassWarning.tsx`
- Create: `src/frontend/src/__tests__/ExternalApiBreakGlassWarning.test.tsx`
- Modify: `src/frontend/src/services/modelSettings.ts:214-219` (B@7b2ff1f)
- Modify: `src/frontend/src/pages/SettingsPage.tsx` (import after `:32`; JSX after the description `<p>` at `:674-677`, B@7b2ff1f)

**Interfaces:**
- Consumes: `redaction_break_glass` from `GET /settings/model/external-api` (Task 3).
- Produces: `ExternalApiBreakGlassWarning({ active?: boolean })`. It renders `role="alert"` only when `active === true`.

- [ ] **Step 1: Write the failing test.** Create `src/frontend/src/__tests__/ExternalApiBreakGlassWarning.test.tsx`:

```tsx
/**
 * HC-EXT-003 — D12 (owner, 2026-09-27): break-glass is allowed only with a UI
 * warning. The backend reports `redaction_break_glass` on
 * GET /settings/model/external-api (HC-EXT-004).
 *
 * Positive assertions come first; absence is asserted synchronously on a
 * completed render, never via waitFor(... not ...) (recurring-failures #1).
 */
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

import { ExternalApiBreakGlassWarning } from '../components/settings/ExternalApiBreakGlassWarning';

describe('ExternalApiBreakGlassWarning', () => {
  it('HC-EXT-003 shows an alert that says data may leave unredacted and is audited', () => {
    render(<ExternalApiBreakGlassWarning active />);
    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent(/privacy protection override is on/i);
    expect(alert).toHaveTextContent(/reduced or no redaction/i);
    expect(alert).toHaveTextContent(/audit log/i);
  });

  it('HC-EXT-003b renders nothing when break-glass is off', () => {
    const { container } = render(<ExternalApiBreakGlassWarning active={false} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('HC-EXT-003c renders nothing when an older backend sends no flag', () => {
    const { container } = render(<ExternalApiBreakGlassWarning active={undefined} />);
    expect(container).toBeEmptyDOMElement();
  });
});
```

- [ ] **Step 2: Run to verify it fails** (Windows PowerShell):

```powershell
Set-Location C:\Users\DangT\Documents\GitHub\hc-w06\src\frontend
npx vitest run src/__tests__/ExternalApiBreakGlassWarning.test.tsx; "vitest exit=$LASTEXITCODE"   # expect non-zero (RED)
```

Expected: the suite fails with `Failed to resolve import "../components/settings/ExternalApiBreakGlassWarning"` (0 tests run, 1 failed file).

- [ ] **Step 3: Minimal implementation.** Create `src/frontend/src/components/settings/ExternalApiBreakGlassWarning.tsx`:

```tsx
/**
 * Break-glass redaction warning (D12, owner decision 2026-09-27).
 *
 * The external AI runner always applies strict redaction, except when the
 * installation sets EXTERNAL_API_REDACTION_BREAK_GLASS and weakens redaction.
 * That exception is audited server-side; this component is the required UI
 * warning. It renders nothing unless the backend says `true`.
 */
import { AlertCircle } from 'lucide-react';

interface ExternalApiBreakGlassWarningProps {
  active?: boolean;
}

export function ExternalApiBreakGlassWarning({ active }: ExternalApiBreakGlassWarningProps) {
  if (active !== true) return null;

  return (
    <div
      role="alert"
      className="flex items-start gap-2 px-3 py-2.5 rounded-xl bg-status-critical-subtle border border-status-critical/20"
    >
      <AlertCircle className="w-4 h-4 text-status-critical shrink-0 mt-0.5" aria-hidden />
      <p className="text-xs text-ink leading-relaxed">
        <strong>Privacy protection override is on.</strong> This installation is set to send
        external AI requests with reduced or no redaction, so names, birth dates and record
        numbers may leave this device. Each such request is recorded in the audit log.
      </p>
    </div>
  );
}
```

In `src/frontend/src/services/modelSettings.ts`, add one line to `ExternalApiSettings` (`:214-219`):

```ts
  /** D12: true while break-glass is weakening redaction. Absent on older backends. */
  redaction_break_glass?: boolean;
```

In `src/frontend/src/pages/SettingsPage.tsx`, add the import after the `TierCapabilities` import (`:32`):

```tsx
import { ExternalApiBreakGlassWarning } from '@/components/settings/ExternalApiBreakGlassWarning';
```

and directly after the External API description paragraph (`:674-677`, before the toggle `<button>` at `:679`):

```tsx
              <ExternalApiBreakGlassWarning active={externalApiData?.redaction_break_glass} />
```

It is rendered whether or not the toggle is on: break-glass is install-wide, and the user should see it *before* opting in.

- [ ] **Step 4: Run to verify it passes, with type check and the full frontend suite** (Windows):

```powershell
Set-Location C:\Users\DangT\Documents\GitHub\hc-w06\src\frontend
npx vitest run src/__tests__/ExternalApiBreakGlassWarning.test.tsx; if ($LASTEXITCODE -ne 0) { throw "HC-EXT-003 failed" }
npx tsc --noEmit; if ($LASTEXITCODE -ne 0) { throw "tsc failed" }
npx vitest run 2>&1 | Select-Object -Last 6; "vitest exit=$LASTEXITCODE"   # non-zero only if Task 0 recorded failures
```

Expected: `3 passed`; tsc exit 0; full suite = Task 0 passed count + 3, with failures ⊆ Task 0 failures.

- [ ] **Step 5: Break it on purpose.** Change `if (active !== true) return null;` to `return null;`. Expect HC-EXT-003 to fail with `Unable to find an accessible element with the role "alert"`. Revert and re-run to green.

- [ ] **Step 6: Wiring check (what the component test fails to notice: whether the page mounts it).**

```bash
cd "${WT:?export WT per Task 0 Step 1}"
grep -n "ExternalApiBreakGlassWarning" src/frontend/src/pages/SettingsPage.tsx
```

Expected: 2 hits (import and JSX), the JSX one inside the "External API Section" card.

**UNMEASURED:** the visual check in the running app. To measure it, on Windows:
1. Use a scratch data dir.
2. In `C:\Users\DangT\Documents\GitHub\hc-w06\src\backend\.env`, set `EXTERNAL_API_REDACTION_BREAK_GLASS=true` and `REDACTION_ENABLED=false`.
3. Run `.\dev.ps1`, sign in, open Settings, and screenshot the External API card.
4. Unset both, reload, and confirm the alert is gone.

Record the result in the PR. Do not leave the `.env` change behind.

- [ ] **Step 7: Commit.**

```bash
cd "${WT:?export WT per Task 0 Step 1}"
git add src/frontend/src/components/settings/ExternalApiBreakGlassWarning.tsx src/frontend/src/__tests__/ExternalApiBreakGlassWarning.test.tsx src/frontend/src/services/modelSettings.ts src/frontend/src/pages/SettingsPage.tsx
git diff --cached --name-only    # expect exactly those 4 paths
git commit -m "feat(settings): warn when break-glass weakens external API redaction (D12)" -m "Renders a role=alert notice in the External API card while GET /settings/model/external-api reports redaction_break_glass=true. HC-EXT-003/003b/003c (vitest, Windows)." -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- src/frontend/src/components/settings/ExternalApiBreakGlassWarning.tsx src/frontend/src/__tests__/ExternalApiBreakGlassWarning.test.tsx src/frontend/src/services/modelSettings.ts src/frontend/src/pages/SettingsPage.tsx
```

---

## Task 5: Measured acceptance, whole-flow re-walk, PR (no new code)

- [ ] **Step 1: Backend full suite** (clean worktree, D9 venv):

```bash
cd "${WT:?export WT per Task 0 Step 1}"/src/backend && find . -name __pycache__ -type d -prune -exec rm -rf {} +
~/venvs/asclexis-311/bin/python -B -m pytest tests/ --collect-only -q -p no:cacheprovider 2>&1 | tail -1; echo "collect exit=${PIPESTATUS[0]}"   # expect 0
~/venvs/asclexis-311/bin/python -B -m pytest tests/ -p no:cacheprovider -q 2>&1 | tail -15; echo "full-suite exit=${PIPESTATUS[0]}"
```

Expected: collected = `START_COLLECTED + 17`. The 17 are HC-EXT-001 ×4, 002 ×4, 002b, 002c ×2, 002d, 004 ×4, 004b. If SLOT-RULE is signed, this equals the figure commit 3 wrote into the collected-count slots. Failures ⊆ `START_FAILURES`, each named. `full-suite exit` is 0 exactly when that set is empty.

- [ ] **Step 2: Scope proofs** (each must print what is stated):

```bash
cd "${WT:?export WT per Task 0 Step 1}"
S=$(git merge-base HEAD origin/main)    # the Task 0 start commit; check it equals the sha recorded in Task 0 Step 1
git diff --name-only $S..HEAD
# expect exactly the 8 owned paths in §4.1, plus CLAUDE.md and AGENT.md only if SLOT-RULE is signed
git diff $S..HEAD -- src/backend/modules/ src/backend/core/audit.py src/backend/core/config.py src/backend/core/auth.py src/backend/models/ | wc -l
# expect 0
git diff -U0 $S..HEAD -- CLAUDE.md AGENT.md | grep -E '^[-+][^-+]'
# SLOT-RULE unsigned: expect no output. Signed: only the collected-count slot lines, differing only in digits
git diff -U0 $S..HEAD -- src/backend/core/external_runner.py | grep '^@@'
# every hunk starts after the encryption helpers (old line > 92) and before get_runner_for_request (old line < 328)
git diff $S..HEAD -- src/backend src/frontend/src | grep -E '^\+.*(https?://|import httpx|import requests|import socket|aiohttp)' | wc -l
# expect 0 — no new network path (C-LOCAL-1)
```

- [ ] **Step 3: Contract verify commands** (as the contract quotes them):

```bash
cd "${WT:?export WT per Task 0 Step 1}"/src/backend
~/venvs/asclexis-311/bin/python -B -m pytest tests/test_redaction.py -k ExternalRunner -p no:cacheprovider -q     # C-REDACT-2: all pass
~/venvs/asclexis-311/bin/python -B -m pytest tests/test_audit_phi_minimization.py -p no:cacheprovider -q            # C-REDACT-3 / C-AUDIT-1: all pass
```

- [ ] **Step 4: Re-walk the whole flow (recurring-failures #2).** Answer each question in the PR with a `path:line` or a test ID:
  1. Settings GET → `redaction_break_glass` (HC-EXT-004).
  2. The PUT response carries the same value (`default_factory`; HC-EXT-004b does an HTTP PUT through `route_client`).
  3. Chat → `api/assistant.py` → `get_runner_for_request` → `rag.query` → `generate_async`: strict without break-glass (HC-EXT-001).
  4. Same path via `api/interpretations.py`: the same runner code, no route change.
  5. Break-glass → audit row before dispatch (HC-EXT-002) → refused without a row (HC-EXT-002b).
  6. What does `rag` do with the refusal? It receives `InferenceResult(finish_reason="error")` text, exactly as it does for today's production block (`modules/rag.py:1291`, B@7b2ff1f). No new behaviour; name it.
  7. `validate_startup` warnings unchanged (`tests/test_config_validation.py` green).

- [ ] **Step 5: Docs gates** (the plan file itself, when it is committed by the docs owner):

```bash
cd "${WT:?export WT per Task 0 Step 1}"
python3 scripts/docs_lint.py; echo "docs_lint exit=$?"            # expect: "Docs lint passed." and exit 0
python3 scripts/generate_docs_index.py --check
```

If `--check` reports stale: regenerate **only** in a clean tree, with the owner's consent for `docs/INDEX.md` (C-GATE-4). This plan does not itself regenerate the index.

- [ ] **Step 6: Open the PR and stop for the owner's merge.** Use the handoff §6 body shape:
  1. start and end measurements;
  2. red-then-green output for every HC-EXT test;
  3. C-REDACT-2 / C-LLM-1 / LOCAL-04 / LLM-01 and the proposed status change (§2);
  4. the 8-file list and every stop gate reached;
  5. one next action.

  End the PR body with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

## 8. Measured acceptance (summary)

| Check | Command | Expected |
|---|---|---|
| Backend count | Task 5 Step 1 | collected = start + 17; failures ⊆ start failures |
| `test_redaction.py` | `pytest tests/test_redaction.py -q` | same collected as start; all pass |
| Dev bypass gone | HC-EXT-001 | 4 passed; red first (recorded) |
| Break-glass audited, fail-closed, PHI-free | HC-EXT-002/002b/002c/002d | 8 passed; red first except 002c (passes by construction at RED; red via break-it step 4) |
| UI learns state | HC-EXT-004/004b over HTTP | 5 passed; red first |
| UI warns | HC-EXT-003/003b/003c (Windows vitest) | 3 passed; red first |
| Frontend | `npx tsc --noEmit`; `npx vitest run` | exit 0; failures ⊆ start |
| App boots | `python -c "from main import app"` | `ok` |
| Scope | Task 5 Step 2 | 8 paths; 0-line diffs on read-only files; 0 new network lines |
| Visual warning | manual (Task 4 Step 6) | **UNMEASURED** until run on Windows |
| Master-DB row on a real vault install | 002d uses a real schema in `tmp_path`, not a user install | **UNMEASURED** on a real install. To measure: in a scratch data dir with break-glass on and a stubbed provider, send one chat; then `SELECT event_type, action, details_json FROM audit_logs WHERE event_type='security.external_api.break_glass'` |

## 9. Stop gates (stop and ask the owner)

| # | Condition |
|---|---|
| S1 | The owner does not confirm Q1 (break-glass keeps its current meaning in every `app_env`). |
| S2 | Any need to edit `modules/redaction.py`, `core/audit.py` (including its allowlists), `core/config.py`, `core/auth.py`, or `CLAUDE.md` beyond the SLOT-RULE collected-count slots. |
| S3 | Any hunk in `core/external_runner.py:1-92` (encryption helpers) or `:328-369` (`get_runner_for_request`), or any new provider, URL or HTTP client. |
| S4 | Any new config field, env var, request flag or per-profile toggle for break-glass. |
| S5 | `tests/test_redaction.py` needs more than the Task 2 Step 4 change, or any existing assertion would have to change or go. |
| S6 | A RED step passes, a GREEN step fails for an unexplained reason, a Task 0 anchor is missing, an import cycle appears, or any new failure appears outside `START_FAILURES`. |
| S7 | The D9 interpreter `~/venvs/asclexis-311/bin/python` is missing, or P1 has not merged. |
| S8 | Converting the production block (behaviour row 4) into "force strict and send" instead of "block". That relaxes a fail-closed guard, so it is not done here. |

## 10. Rollback

- Before merge: `cd "$WT" && git revert --no-edit $(git rev-list "$(git merge-base HEAD origin/main)"..HEAD)`. `rev-list` lists newest first, so this reverts Task 4 → Task 1 in order. After merge: `git revert -m 1` on this PR's merge commit, as GitHub shows it. There is no schema, migration or data change: the audit rows use the existing `audit_logs` table. Rows already written stay as history.
- Reverting only Task 4 or Task 3 leaves the server hardening in place. Reverting Task 1 restores the dev bypass, so that needs the owner's say.

## 11. Owner sign-offs and open questions (unsigned)

| # | Question | Plan's default | Sign-off |
|---|---|---|---|
| Q1 · **BG-REACH** | D12 says "keep break-glass". This plan keeps its **current meaning**: `EXTERNAL_API_REDACTION_BREAK_GLASS=true` lets the configured weaker/no redaction apply, in any `app_env` (as today, §3.2 row 5). It is now fail-closed on an audit row. Confirm; or say break-glass should work in production only. That narrower option is also within D12, but it changes the flag's reach | keep current meaning | ☐ owner: ____ date: ____ |
| Q2 · **GOV-BG** | W-10 names the external runner as a ModelRunner exception. Should W-10 also name **audited break-glass** as the one exception to `CLAUDE.md:60` ("Redaction before anything leaves")? Otherwise break-glass still contradicts that line as written. **Merged with W-10 Q2 into one gate, GOV-BG (3a M-3); sign it in the W-10 plan §10, not here** | yes (include) | see W-10 §10 |
| Q3 | The warning shows only in the Settings External API card. Should the chat page (`ExplainAssistant.tsx:276-290` at B@7b2ff1f, where the external model is named) also show it? | Settings only (D12 minimum) | ☐ owner: ____ date: ____ |
| Q4 | Approve the edit to the ask-first-adjacent `core/external_runner.py` (§3.8), plus the one-test change in `tests/test_redaction.py`, and the response-model field in `api/model_settings.py:208-213` plus its one import (`:22-24`), all outside the encryption handler (PUT `save_external_api_settings` `:719-757`, `encryption_manager.encrypt(` at `:745`, B@7b2ff1f), as covered by D12 | covered | ☐ owner: ____ date: ____ |
| Q5 | Warning copy (Task 4 Step 3) | as written | ☐ owner: ____ date: ____ |
| SLOT-RULE | Program gate (3a §5.4): every collection-changing commit updates the collected-count slots. Signed → the §4.3 carve-out applies to commits 1–3 | recommend yes | program owner gate (not signed here) |
| — | PR merge | — | ☐ owner: ____ date: ____ |

## 12. Recurring-failures recheck

| # | Mode | Applies | Concrete recheck |
|---|---|---|---|
| 1 | Green suite that could not fail | yes | Every HC-EXT test is observed red first. Five break-it steps (Tasks 1–4). HC-EXT-004 goes through HTTP. The frontend asserts absence only on completed renders. HC-EXT-002 searches every audit column, not just `action` |
| 2 | Fix that creates the next bug | yes | Task 5 Step 4 walks the whole flow. Doc claims that go stale and need their owners: `docs/compliance/data-privacy.md:200` at B@7b2ff1f ("per `modules/redaction.py` policy"; now strict, audited break-glass); `docs/plans/implementation-log/2026-06-11_verification-report.md:16` (historical); `skills/asclexis-guardrails/SKILL.md:63` ("bypass redaction for any reason" is a "Never", while audited break-glass stays). Route these to W-10/P4; W-6 does not edit them |
| 3 | Figures asserted | yes | Every count comes from Task 0 / Task 5 output. "+17 backend / +3 frontend" are the items this plan adds, not predictions of totals |
| 4 | Env-dependent results | yes | vitest runs on Windows only. `app_env` is patched per test; no test depends on the host `.env` |
| 5 | Contaminated tree | yes | Dedicated worktree; explicit pathspecs; `git diff --cached --name-only` before each commit; never `git add -A`/`.` |
| 6 | Documented commands nobody ran | yes | Run every command in this plan as written, from the directory it names. Report any that fail as a plan defect |
| 7 | SQL three-valued logic | no | No `!=`/`NOT IN` filter is added. 002d's `select(AuditLog)` is unfiltered |
| 8 | Stale guidance as authority | yes | The handoff's "`:201`" was checked in code (§3.1). The contract's "two bypasses" missed the non-strict level; this plan found and covers it. The guardrails skill's "Never bypass" is flagged, not obeyed silently |

## 13. Commit plan (summary)

| # | Prefix and subject | Pathspecs |
|---|---|---|
| 1 | `fix(external-runner): make strict redaction unconditional outside break-glass (D12)` | `src/backend/core/external_runner.py`, `src/backend/tests/test_external_runner_hardening.py` |
| 2 | `fix(external-runner): audit break-glass before dispatch and fail closed (D12)` | the two above + `src/backend/tests/test_redaction.py` |
| 3 | `feat(model-settings): report break-glass redaction state to the UI (D12)` | `src/backend/api/model_settings.py`, `src/backend/tests/test_external_runner_hardening.py` |
| 4 | `feat(settings): warn when break-glass weakens external API redaction (D12)` | the 4 frontend paths in §4.1 |

Each commit: `git add <paths>` → `git diff --cached --name-only` equals the listed paths → `git commit … -- <paths>`. If SLOT-RULE is signed, commits 1–3 also list `CLAUDE.md` and `AGENT.md` (collected-count slots only, §4.3). No `docs:` commit is in this plan: the CLAUDE.md amendment is W-10's.

Back to: [implementation program](../capstone-report/implementation-program.md) · [owner decisions](../capstone-report/owner-decisions-2026-09-27.md) · [recurring failures](../agentic/recurring-failures.md)
