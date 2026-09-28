# Merge Unmerged Fix Branches Implementation Plan

> **2026-09-27 corrections ([review follow-up](../review/2026-09-27-followup.md), F-05/F-06/F-07):** re-measured on 2026-09-27 against the local `origin/*` refs; no fetch was run, so re-fetch before executing.
> - Branch B is **19** commits ahead of main, not 21 (`git rev-list --count HEAD..origin/claude/healthcentral-agentic-research-r1n54x` → `19`). Branch A is 5 ahead. Both fork from `40f590e` and are 0 behind.
> - Collected counts (`python.exe -B -m pytest tests/ --collect-only -q -p no:cacheprovider`, Windows Python 3.13.7, on `git archive` copies of each ref):
>
>   | Ref | Collected |
>   |---|---|
>   | main | 1245 |
>   | A | 1248 |
>   | B | 1288 |
>   | merge-tree of A onto B (5 doc files left with conflict markers) | 1291 |
>
>   These are **collected** counts. Pass counts are unmeasured, and Python 3.13 is not CI's 3.11.
> - `git merge-tree` confirms the 5 conflicted files listed below. `SettingsPage.tsx` auto-merges.
> - Preflight: the working tree holds uncommitted owner edits to `docs/INDEX.md` and `.serena/project.yml`, plus the untracked `audit/` and `docs/capstone-report/`. Do not merge in this tree, and do not stash or discard these without the owner. Use a clean worktree (recurring-failures #5).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land both unmerged `claude/*` branches onto `main` via two sequential, human-approved PRs — `claude/healthcentral-agentic-research-r1n54x` first (it carries the P1 fail-open security-gate fix), then `claude/asclexis-repo-audit-349pjq` — resolving the five known doc conflicts on the second PR's branch before its human merge.

**Architecture:** Both branches forked from the same commit that is still `main`'s tip (`40f590e`), so each is individually conflict-free against `main` today; the five overlapping files conflict only once the first PR lands. All merge mechanics are done on branches and PRs — the executor never commits to or merges `main` directly (repo convention: humans merge). Conflict resolution is a real authored artifact, so the full gate suite runs on the conflict-resolution branch before its PR opens.

**Tech Stack:** git + GitHub CLI (`gh`), FastAPI/pytest backend, React/TS/vitest frontend, repo gate scripts under `scripts/`.

## Global Constraints

- **Humans merge.** The executor opens PRs via `gh` and resolves conflicts on branches. It never runs `git merge` into `main`, never pushes to `main`, never clicks merge. Twice in this plan execution STOPS for a human merge.
- **Python 3.11+**; use `core.time.utcnow` for timestamps. No 3.12-only syntax.
- **Per-profile data isolation** — profile data via `ProfileDbSession`, never `get_db()`.
- **Local-first** — no network calls in product code paths; Ollama stays localhost-only. (`download_models.py verify` talking to HuggingFace is the sanctioned exception and is never run by CI or this plan.)
- **Redaction before anything leaves** — any path writing user text to exportable files or external runners passes `modules/redaction.py`. Do not extend or weaken it in this plan.
- **Never lower a safety check or test threshold.** `test_api_rag_index_002b`'s 0.7 embedding threshold stays; its local failure without a real embedding model is environmental and expected.
- **Dual Alembic chains** — neither branch adds migrations; if a conflict resolution ever touches `migrations/`, stop and ask.
- **WSL/9p notes (this environment):** run `find src/backend -name __pycache__ -type d -exec rm -rf {} +` before every pytest invocation; `node_modules` may be unusable under WSL — run the frontend toolchain (`npx tsc --noEmit`, `npx vitest run`) on the Windows host, not in WSL. `/mnt/c` I/O errors are a known transient mount failure — if `ls /mnt/c` returns `Input/output error`, stop and report rather than working in a stale clone.
- **`gh` authentication:** verified working 2026-09-25 (`gh auth status` → account `BrooklynD23`, scopes include `repo`, `workflow`). Re-check at Task 1; if it ever fails, STOP and ask the owner — do NOT fall back to pushing branches and printing compare URLs.
- **Owner decision (already given):** merge BOTH branches AS-IS; do not split the Phi-4-mini product change out of branch B.
- **Do not fix unrelated findings in passing.** `POST /export/questions` returning unredacted `source_quote` is a recorded P2, deliberately out of scope (see Semantic Risks).

## Branch Inventory (verified by inspection, 2026-09-25)

**Branch A — `origin/claude/asclexis-repo-audit-349pjq`** · 5 commits · +1,660/−102 · tip `692fdf3`
- `3bb4d0d` docs: plans for every open item + the `SQL-FK-001` FK audit (`docs/plans/2026-09-08-sql-fk-001-foreign-key-audit.md`, `docs/plans/2026-09-08-backlog-closure-plan.md`, `docs/features/TASK_LIST.md`)
- `fe31e78` docs: four owner decisions recorded
- `5669926` docs: regenerated `docs/INDEX.md` / `docs/_link_graph.json`; measured figures replace asserted ones (AGENT.md/CLAUDE.md baseline → 1248)
- `45ac889` fix(documents): CARE-QUOTE-001 — `delete_document` clears `CarePlanTask.source_document_id/source_entity_id/source_quote` (`src/backend/api/documents.py` ~:1867, tests `HC-CAREQ-001..003` in `src/backend/tests/test_documents_api.py`)
- `692fdf3` feat(frontend): `RecoveryCodeCard.tsx` (new, mounted in `SettingsPage.tsx`), `MedicationCorrelations.test.tsx` (new), `CorrelationContract.test.ts` updated, `MedicationDetail.tsx` rewired to `useMedicationCorrelations`, `utils/correlation.ts` cut to the inverse projection only, `RecoverProfile.tsx` copy, `e2e/recovery-code.spec.ts` (new)

**Branch B — `origin/claude/healthcentral-agentic-research-r1n54x`** · 19 commits (corrected 2026-09-27; was "21") · +15,050/−94 · tip `7b2ff1f`
- `934a842` **fix(ci): security gate fails closed** — `scripts/security_gate.py` raises `ReportError` → `main()` returns exit 2 on missing/malformed reports; `ci.yml` scanner steps become exit-code-aware (≥2 = scanner error fails the step; `|| true` removed); adds `scripts/repo_hygiene_check.py` to CI; tests `HC-SECGATE-001..007` (`src/backend/tests/test_security_gate.py`)
- `2c98ae6` fix(memory,cache): Wave-0 defects — audit logging on all 5 `api/memory.py` routes (new `log_memory_event` in `core/audit.py`); answer-cache version becomes a fingerprint over verified observations+documents (`modules/agent/cache.py`, `api/assistant.py`, `CacheKey.profile_version` int→str); removes dead `default_embeddings_model` from `core/config.py`
- `cc202d9` fix(assistant): agent verification derived from real groundedness counts (`api/assistant.py`, `modules/agent/guardrails/guard.py`, `modules/agent/schemas.py`)
- `3c77eec` + `3eb9e9d` feat(models): mid tier Phi-3-mini → Phi-4-mini-instruct; `llama-cpp-python>=0.2.0` → pinned `==0.3.35` (`src/backend/requirements.txt:72`)
- `f8ca137` feat(models): `download_models.py verify` subcommand (`src/backend/scripts/download_models.py`)
- `13b1466` feat(settings): `TierCapabilities.tsx` (new, mounted in `SettingsPage.tsx`), `model_settings.py` + `services/modelSettings.ts` capability fields
- `7b2ff1f` docs + `scripts/harness_drift_check.py` (new; exercised via `src/backend/tests/test_harness_drift_check.py`, not a CI step)
- 13 docs/research commits (~13k lines: `docs/research/2026-09-08/*`, vendored Pocock skills under `.claude/skills/`, `docs/INDEX.md`/`_link_graph.json` regens, `CS4610_Report_Demo/README.md`, Office lock-file removal)

**Note:** the task brief and audit §17 describe Wave-0 fixes "in `core/external_runner.py`" — inspection shows that file is NOT touched by branch B; the actual Wave-0 files are those listed under `2c98ae6`/`cc202d9` above. If a diff review ever shows `core/external_runner.py` in the branch, this inventory is stale — re-run the Task 1 verification.

## Conflict Map (verified via `git merge-tree --write-tree` on both branch tips)

Six files are touched by both branches; five conflict on content (`src/frontend/src/pages/SettingsPage.tsx` auto-merges — both branches add a different component import+mount in different regions):

| File | Branch A change | Branch B change | Resolution |
|---|---|---|---|
| `AGENT.md` | baseline 1245→1248 | skills-table add + `download_models.py verify` line + baseline →1269 (stale mid-branch value) | Union both changes; baseline = **measured** post-merge count |
| `CLAUDE.md` | baseline 1245→1248 | baseline →1288; OpenWiki paragraph reword; "18 skills"→"36 skills" | Union; baseline = **measured** post-merge count |
| `docs/agentic/recurring-failures.md` | +SEC-RECOV-002 mock-bullet + recheck sentence; +CARE-QUOTE-001 near-miss para + recheck sentence | +security-gate fail-open bullet + recheck sentence; +memory-sanitize near-miss para + recheck sentence | Union — keep ALL four additions; the recheck sentences are different texts in the same locations, combine them |
| `docs/INDEX.md` | regenerated | regenerated (different corpus) | **Do not hand-merge** — regenerate: `python3 scripts/generate_docs_index.py` |
| `docs/_link_graph.json` | regenerated | regenerated | **Do not hand-merge** — regenerate: `python3 scripts/docs_lint.py --link-graph` |
| `src/frontend/src/pages/SettingsPage.tsx` | `RecoveryCodeCard` import+mount | `TierCapabilities` import+mount | Auto-merges; verify both mounts present after merge |

**Expected merged backend test count:** main collects 1,245; branch A adds 3 (`HC-CAREQ-001..003`); branch B adds 43 (delta verified per file: +7 security_gate, +6 memory_audit, +7 tier_capabilities, +7 verify_model_repos, +5 s3_guardrails, +4 harness_drift, +3 cache_version, +3 hc_a1, +1 llm_provider, ±0 s5_cutover). Expected merged ≈ **1,291** — measure for real in Task 4 and write that number, not this estimate. *(2026-09-27: 1,291 was collected on the conflicted merge-tree; see the banner. That is an early measurement, not the acceptance figure. The resolved merge must be collected and run again.)* Branch B's own `AGENT.md` (1269) vs `CLAUDE.md` (1288) already disagree; the measured number fixes both.

## Semantic Risks (read before resolving anything)

1. **CARE-QUOTE-001's surface is retention, not export.** The fix (`api/documents.py`, `delete_document`) enforces "verbatim clinician text must not outlive the document it came from" — it nulls provenance + quote on `CarePlanTask` rows when the source document is deleted. It is deliberately NOT mirrored into the reprocess path (`get_care_task_candidates` keys duplicate detection on `(source_document_id, source_quote)` — clearing there resurfaces accepted tasks). **`POST /export/questions` still returns verbatim `source_quote` in JSON** (`api/export.py:607-661` → `modules/export.py:451,463,497`) — that data stays on-device, FHIR export (`modules/fhir_export.py:280`) and the visit-prep packet DO redact, and the audit lists the endpoint as a recorded P2 whose "leaves the device" interpretation needs an owner decision. This merge does NOT change it; do not expand scope.
2. **`llama-cpp-python` pin 0.2.0→`==0.3.35`.** A stale venv masks the change — reinstall deps (`pip install -r src/backend/requirements.txt`) before running the backend suite post-merge.
3. **Phi-4-mini tier swap is a product change merged as-is** (owner decision); the eval gate and tier tests are the safety net, not a re-review.
4. **`api/memory.py` gains `master_db: AsyncSession = Depends(get_db)` on all 5 routes** — any test calling handlers directly would bypass it; the new tests use `route_client` correctly. Preserve that style in any conflict touch-up.
5. **`SettingsPage.tsx` auto-merges textually** — but only `npx tsc --noEmit` + `npx vitest run` prove both mounts compile together.
6. **`docs/_link_graph.json`/`docs/INDEX.md` are generated artifacts** — regenerating is the only correct resolution; a hand-merged graph can silently disagree with the corpus.
7. **SQL-FK-001 stays OPEN after this merge** — branch A lands the FK *audit document* and the `CARE-QUOTE-001` prerequisite, not the pragma flip. `PRAGMA foreign_keys` remaining unset is expected, not a regression.
8. **Baseline-count conflict resolution is a measurement, not a choice.** Neither branch's number survives the merge; run `--collect-only` on the merged tree and write what you observe.

---

### Task 1: Pre-merge verification

**Files:** none (read-only)

- [ ] **Step 1: Enter the repo and fetch**

Work in the canonical checkout. If `/mnt/c` I/O-errors, either wait for the mount or use a fresh clone (`gh repo clone BrooklynD23/HealthCentral /tmp/hc-repo`) — never a stale one.

```bash
cd /mnt/c/Users/DangT/Documents/GitHub/HealthCentral   # or the fresh clone
git fetch origin --prune
git status --short --branch
```

Expected: `## main...origin/main` and no tracked modifications (untracked `audit/` is fine).

- [ ] **Step 2: Confirm both branches still fork from current main**

```bash
git rev-parse origin/main
git merge-base origin/main origin/claude/asclexis-repo-audit-349pjq
git merge-base origin/main origin/claude/healthcentral-agentic-research-r1n54x
git rev-parse origin/claude/asclexis-repo-audit-349pjq origin/claude/healthcentral-agentic-research-r1n54x
```

Expected: all three first commands print `40f590eee32a98bcafc2c4db39509f921e1d9994`; branch tips `692fdf3…` and `7b2ff1f…`. **If `origin/main` has moved past `40f590e`**, STOP — the conflict map and test-count estimates in this plan must be re-derived (`git merge-tree --write-tree` again; re-read `docs/agentic/recurring-failures.md` for drift).

- [ ] **Step 3: Re-confirm the commit inventories**

```bash
git log --oneline origin/main..origin/claude/asclexis-repo-audit-349pjq
git log --oneline origin/main..origin/claude/healthcentral-agentic-research-r1n54x
```

Expected: 5 commits and 19 commits (corrected 2026-09-27; was "21"). If either differs, the branch moved: stop and re-inventory before resolving anything.

- [ ] **Step 4: Verify `gh` auth**

```bash
gh auth status
```

Expected: `Logged in to github.com account BrooklynD23` with `repo` and `workflow` scopes. If unauthenticated or wrong account: STOP, tell the owner — do not proceed and do not fall back to compare URLs.

- [ ] **Step 5: Diff-review checklist (read each group, no edits)**

Per file group, confirm the diff matches the inventory (`git diff origin/main...origin/<branch> -- <paths>`). Checklist — each item must be eyeballed, not assumed:

| Group | What to verify |
|---|---|
| `api/documents.py` + `test_documents_api.py` (A) | Only the CARE-QUOTE-001 `update(CarePlanTask)` block added inside `delete_document`; `source_document_id`/`source_entity_id`/`source_quote`→None; task row itself NOT deleted; 3 tests present |
| `utils/correlation.ts`, `MedicationDetail.tsx` (A) | `findObservationsDuringMedication` and `buildCorrelationContext` deleted; `findActiveMedications` retained; `MedicationDetail` uses `useMedicationCorrelations`, no `useObservations` import |
| `RecoveryCodeCard.tsx`, `SettingsPage.tsx`, `RecoverProfile.tsx`, `e2e/recovery-code.spec.ts` (A) | Card reads `has_recovery_code` from the **list** response (`useProfiles`), not `GET /profiles/{id}`; code shown once, state-only; Settings mount is above `BackupCard` |
| `security_gate.py`, `ci.yml` (B) | `ReportError` raised on `FileNotFoundError`/`JSONDecodeError`; `main()` returns 2; scanner steps capture `code=$?` and fail only on `>=2`; `repo_hygiene_check.py` step added to docs-lint job |
| `api/memory.py`, `core/audit.py` (B) | `log_memory_event` + `audit_and_commit` on all 5 routes; `details` carries `category`/`value_length` only — never `value` |
| `modules/agent/cache.py`, `api/assistant.py`, `guard.py`, `schemas.py` (B) | `CacheKey.profile_version` str fingerprint covers verified observations + verified documents; memory items excluded; verification derived from real groundedness counts |
| `requirements.txt`, `model_selector.py`, `download_models.py`, `model_settings.py` (B) | `llama-cpp-python==0.3.35` pinned; mid tier Phi-4-mini-instruct @ 16384 ctx; `verify` subcommand new; capability fields additive only |
| `docs/research/2026-09-08/*`, `.claude/skills/*` (B) | Docs/vendored-skills only — no product code hidden in the large commits; `git diff origin/main...origin/claude/healthcentral-agentic-research-r1n54x -- '*.py' '*.ts' '*.tsx' ':!src/backend/tests' ':!docs'` lists only the files named in the inventory |

If any diff surprises (extra files, extra commits, unexpected hunks): STOP and report — do not "resolve" by dropping work.

---

### Task 2: Open PR #1 — branch B (fail-closed security gate first)

**Why first:** the audit's top recommendation is "security-gate fail-closed first" — every subsequent PR's CI run then produces a trustworthy security signal.

- [ ] **Step 1: Push nothing — the branch already exists on origin.** Open the PR:

```bash
gh pr create --base main --head claude/healthcentral-agentic-research-r1n54x \
  --title "feat: fail-closed security gate, Wave-0 memory/cache fixes, Phi-4-mini mid tier, agentic research corpus" \
  --body "$(cat <<'EOF'
## Summary
- fix(ci): `security_gate.py` fails closed (exit 2) on missing/malformed bandit/pip-audit reports; scanner steps become exit-code-aware (>=2 fails the step); `repo_hygiene_check.py` added to docs-lint job. Tests HC-SECGATE-001..007.
- fix(memory,cache): audit logging on all 5 api/memory routes; answer-cache version is now a fingerprint over verified evidence (not a COUNT). Wave-0 defects from the research pass.
- fix(assistant): agent verification derived from real groundedness counts.
- feat(models): mid tier Phi-3-mini -> Phi-4-mini-instruct; llama-cpp-python pinned ==0.3.35; `download_models.py verify`.
- feat(settings): TierCapabilities disclosure card.
- docs: eight-track agentic research corpus (~13k lines), vendored Pocock skills, harness_drift_check, roadmap consultation.

## Test plan
- [ ] CI green: docs-lint, backend (1288 collected on this branch), frontend, security, agent-evals, e2e
- [ ] Security gate proven fail-closed by HC-SECGATE-001..007 in src/backend/tests/test_security_gate.py

## Notes
- Owner decision: merged as-is, Phi-4-mini change intentionally not split.
- requirements.txt pins llama-cpp-python==0.3.35 — reinstall deps after merge.
EOF
)"
```

Expected: prints a PR URL. Note the PR number: `gh pr view --json number,url`.

- [ ] **Step 2: Verify CI is running on the PR**

```bash
gh pr checks <PR-number> --watch=false || gh pr checks <PR-number>
```

All 6 jobs should appear (docs-lint, backend-tests, frontend-tests, security-scan, agent-evals, e2e-tests). The security-scan job on THIS PR's workflow is already the fail-closed version — a green run here is the first trustworthy one.

- [ ] **Step 3: STOP — human merges this PR.** Do not proceed to Task 3 until `gh pr view <PR-number> --json state` shows `MERGED`. While waiting, Task 3's conflict resolution may be *prepared* on a local throwaway branch but not pushed.

---

### Task 3: Update branch A with merged main and resolve the 5 conflicts

**Files:**
- Modify (conflict resolution): `AGENT.md`, `CLAUDE.md`, `docs/agentic/recurring-failures.md`, `docs/INDEX.md`, `docs/_link_graph.json`
- Verify-only (auto-merge): `src/frontend/src/pages/SettingsPage.tsx`

- [ ] **Step 1: Fetch the new main and start the resolution branch**

```bash
git fetch origin
git rev-parse origin/main   # expect a merge commit ABOVE 40f590e containing 7b2ff1f
git checkout -b merge/asclexis-repo-audit-349pjq origin/claude/asclexis-repo-audit-349pjq
git merge origin/main
```

Expected: `CONFLICT (content)` in exactly `AGENT.md`, `CLAUDE.md`, `docs/INDEX.md`, `docs/_link_graph.json`, `docs/agentic/recurring-failures.md`; `src/frontend/src/pages/SettingsPage.tsx` auto-merges. `git status` must list exactly those 5 `both modified`.

- [ ] **Step 2: Resolve `docs/INDEX.md` + `docs/_link_graph.json` by regeneration (never by hand)**

```bash
git checkout --theirs docs/INDEX.md docs/_link_graph.json   # content irrelevant; next step rewrites both
python3 scripts/generate_docs_index.py
python3 scripts/docs_lint.py --link-graph
git add docs/INDEX.md docs/_link_graph.json
```

Expected: `python3 scripts/generate_docs_index.py --check` exits 0 afterwards (freshness proof); the regenerated files index the union of both branches' docs.

- [ ] **Step 3: Resolve `CLAUDE.md`**

Edit so the result has ALL of: branch B's "1288→measured" baseline paragraph shape (keep the surrounding wording from branch B's version — it's a superset edit location), branch B's OpenWiki-paragraph rewrite, and "36 skills". Set the baseline number to `MEASURED_PENDING` temporarily — Task 4 measures it. Every conflict hunk in this file is the same shape: `-1245/+1248` vs `-1245/+1288` — keep branch B's side everywhere and fix the number after measurement.

```bash
grep -n "collected\|OpenWiki\|ships 3" CLAUDE.md
```

Expected: no `<<<<<<<`/`>>>>>>>` markers; one consistent baseline statement; "36 skills" line present.

- [ ] **Step 4: Resolve `AGENT.md`**

Keep branch B's side for the Skills-table addition AND the `download_models.py verify` command pair, AND keep the single baseline line — set to `MEASURED_PENDING` until Task 4.

```bash
grep -n "collected\|download_models.py" AGENT.md
```

Expected: no markers; both `download_models.py list` and `verify` lines present.

- [ ] **Step 5: Resolve `docs/agentic/recurring-failures.md`** — the only file needing real editorial work

Union is mandatory; do not pick a side. Result must contain all four new passages:

1. Branch A's SEC-RECOV-002 bullet (mocked `has_recovery_code` on the wrong response model) **and** branch B's security-gate fail-open bullet — both inside the mode-1 section; keep branch B's recheck addition ("delete the report and confirm the gate goes RED") AND branch A's recheck addition ("a mock is an assertion about the API…") — concatenate both sentences.
2. Branch A's CARE-QUOTE-001 near-miss paragraph (reprocess-path duplicate-detection) in mode-2, **plus** its recheck sentence ("grep for every reader of it…").
3. Branch B's memory-sanitize near-miss paragraph (`sanitize_untrusted_field` would corrupt vault PHI) later in the file, **plus** its recheck sentence ("check whether the defense already exists somewhere better…").

```bash
grep -n "<<<<<<<\|>>>>>>>" docs/agentic/recurring-failures.md   # expect: no output
grep -cn "SEC-RECOV-002\|CARE-QUOTE-001\|fail.open\|sanitize_untrusted_field" docs/agentic/recurring-failures.md   # expect: several hits, all four topics present
```

- [ ] **Step 6: Verify the auto-merged `SettingsPage.tsx` carries both mounts**

```bash
grep -n "RecoveryCodeCard\|TierCapabilities" src/frontend/src/pages/SettingsPage.tsx
```

Expected: both imports and both `<… />` mounts present (4+ hits). If either is missing, the auto-merge went wrong — `git checkout --theirs`/`--ours` alone will NOT fix it; report before improvising.

- [ ] **Step 7: Commit the merge (still on the resolution branch, not pushed yet)**

```bash
git add AGENT.md CLAUDE.md docs/agentic/recurring-failures.md src/frontend/src/pages/SettingsPage.tsx
git commit --no-edit   # keeps git's default merge message
```

Do NOT push yet — Tasks 4–6 gate this branch first.

---

### Task 4: Measure the true collected count + write it into the resolved docs

- [ ] **Step 1: Clean bytecode, then count**

```bash
find src/backend -name __pycache__ -type d -exec rm -rf {} +
cd src/backend && python -m pytest tests/ --collect-only -q | tail -3
```

Expected last line: `NNNN tests collected` — predicted ≈1291. Whatever it prints is the truth.

- [ ] **Step 2: Write the measured number into both baseline spots**

In `AGENT.md` (Commands block comment) and `CLAUDE.md` (§4 baseline paragraph + the "if it differs from" line): replace `MEASURED_PENDING` with the observed count, and `N-1` for the "without an embedding model" figure. Commit:

```bash
cd <repo-root>
git add AGENT.md CLAUDE.md
git commit -m "docs: set merged backend test baseline to measured count"
```

---

### Task 5: Prove the security gate fails closed on the merged tree

The whole point of PR #1 — prove it end-to-end with a poisoned report, not just by trusting `HC-SECGATE-001..007`.

- [ ] **Step 1: Missing-report proof**

```bash
cd <repo-root>
python3 scripts/security_gate.py --bandit /tmp/definitely-absent-bandit.json --pip-audit /tmp/definitely-absent-pipaudit.json; echo "exit=$?"
```

Expected: `ERROR: Could not parse bandit report …` and `exit=2` (nonzero). On `main` pre-merge this printed `WARNING` and exited 0 — that was the bug.

- [ ] **Step 2: Malformed-JSON proof**

```bash
printf '{"results": [TRUNCATED' > /tmp/poisoned-bandit.json
printf '[{"name": "x"}' > /tmp/poisoned-pipaudit.json
python3 scripts/security_gate.py --bandit /tmp/poisoned-bandit.json --pip-audit /tmp/poisoned-pipaudit.json; echo "exit=$?"
```

Expected: `exit=2`.

- [ ] **Step 3: Clean control — prove it still passes valid clean reports (gate fails closed, not always-fail)**

```bash
printf '{"results": []}' > /tmp/clean-bandit.json
printf '{"dependencies": []}' > /tmp/clean-pipaudit.json
python3 scripts/security_gate.py --bandit /tmp/clean-bandit.json --pip-audit /tmp/clean-pipaudit.json; echo "exit=$?"
```

Expected: `exit=0` with the gate's normal pass output.

- [ ] **Step 4: Restore** — nothing to restore: no real report files were touched (`/tmp` paths only). If `bandit-report.json`/`pip-audit-report.json` exist in the repo root from earlier runs, `git status` must show them unmodified (they're untracked/ignored) — verify:

```bash
git status --short | grep -i "report" || echo "no report files modified"
```

Expected: `no report files modified`.

---

### Task 6: Full gate suite on the conflict-resolution branch

All commands from repo root unless noted. Record actual output — never assert.

- [ ] **Step 1: Reinstall backend deps (llama-cpp pin changed on branch B)**

```bash
pip install -r src/backend/requirements.txt
```

- [ ] **Step 2: Backend suite**

```bash
find src/backend -name __pycache__ -type d -exec rm -rf {} +
cd src/backend && python -m pytest tests/ -p no:cacheprovider -q
```

Expected: collected = the Task 4 number; failures = 0 (or exactly 1: `test_api_rag_index_002b`, environmental — do not touch the 0.7 threshold). Any other failure: STOP, `systematic-debugging`.

- [ ] **Step 3: App boots**

```bash
cd src/backend && python -c "from main import app"
```

Expected: no output, exit 0.

- [ ] **Step 4: Docs + repo gates (CI `docs-lint` job parity + the new ones branch B adds)**

```bash
cd /mnt/c/Users/DangT/Documents/GitHub/HealthCentral
python3 scripts/docs_lint.py; echo "docs_lint=$?"
python3 scripts/generate_docs_index.py --check; echo "index_fresh=$?"
python3 scripts/feature_list_lint.py; echo "feature_list=$?"
python3 scripts/repo_hygiene_check.py; echo "hygiene=$?"
python3 scripts/harness_drift_check.py; echo "drift=$?"
```

Expected: all `=0`. (`harness_drift_check.py` exists only post-merge — that's why it runs here and not on old main.)

- [ ] **Step 5: Agent eval gate**

```bash
python3 scripts/agent_eval_gate.py
```

Expected: exit 0 (74 golden cases, absolute bars — a regression here means a conflict resolution touched agent code; it shouldn't have).

- [ ] **Step 6: Frontend — on the WINDOWS host, not WSL**

```powershell
cd src\frontend
npx tsc --noEmit
npx vitest run
```

Expected: tsc clean; vitest all green including the new `RecoveryCodeCard.test.tsx` (FE-RECOV-001..006), `MedicationCorrelations.test.tsx` (FE-MCORR-001..004), updated `CorrelationContract.test.ts`, and `TierCapabilities.test.tsx`. If `node_modules` is broken on Windows too: `npm ci` first, then rerun.

- [ ] **Step 7: Targeted backend tests for the merged features**

```bash
cd src/backend && python -m pytest tests/test_documents_api.py -k "CAREQ or ENT_03" tests/test_security_gate.py tests/test_memory_audit.py tests/test_medication_correlations.py -p no:cacheprovider -q
```

Expected: all pass (HC-CAREQ-001..003, HC-SECGATE-001..007, HC-MEM-AUDIT-001..006, HC-MCORR-* green together — the union both branches promised).

- [ ] **Step 8: Push the resolution branch and open PR #2**

```bash
git push -u origin merge/asclexis-repo-audit-349pjq
gh pr create --base main --head merge/asclexis-repo-audit-349pjq \
  --title "feat: recovery-code Settings card, correlations endpoint wiring, care-task quote cleanup (merge of claude/asclexis-repo-audit-349pjq)" \
  --body "$(cat <<'EOF'
## Summary
- Merge of `claude/asclexis-repo-audit-349pjq` with main (post security-gate merge), conflicts resolved:
  - `AGENT.md`/`CLAUDE.md`: union; backend baseline set to measured merged count.
  - `recurring-failures.md`: union — all four new passages kept.
  - `docs/INDEX.md`/`docs/_link_graph.json`: regenerated, not hand-merged.
  - `SettingsPage.tsx`: auto-merge; both RecoveryCodeCard and TierCapabilities mounted.
- feat(frontend): RecoveryCodeCard in Settings (SEC-RECOV-002); MedicationDetail reads `GET /medications/{id}/correlations` (MED-CORR-002); dead utils removed; RecoverProfile copy made followable.
- fix(documents): CARE-QUOTE-001 — care-task verbatim quote + provenance cleared on document delete.
- docs: SQL-FK-001 audit + backlog-closure plan + owner decisions.

## Test plan
- [ ] Backend suite green at the measured collected count (Task 6 output attached in PR comments)
- [ ] `npx tsc --noEmit` + `npx vitest run` green on Windows
- [ ] Security gate fail-closed re-proven (poisoned report → exit 2)
EOF
)"
```

- [ ] **Step 9: STOP — human merges PR #2.** Verify after merge: `gh pr view <PR-number> --json state` → `MERGED`.

---

### Task 7: Post-merge functional checks (on merged main)

After the human merges PR #2: `git fetch origin && git checkout main && git pull --ff-only`.

- [ ] **Step 1: Recovery-code surface is reachable from Settings**

```bash
grep -n "RecoveryCodeCard" src/frontend/src/pages/SettingsPage.tsx src/frontend/src/components/settings/RecoveryCodeCard.tsx
npx vitest run src/__tests__/RecoveryCodeCard.test.tsx   # on Windows
```

Expected: import + mount in SettingsPage; all FE-RECOV tests pass. Manual smoke (optional, needs `.\dev.ps1`): Settings → "Recovery code" card visible, Create-vs-Replace wording driven by `has_recovery_code`.

- [ ] **Step 2: Correlations are served by the endpoint, not the frontend heuristic**

```bash
grep -rn "findObservationsDuringMedication" src/frontend/src/          # expect: no output (deleted)
grep -n "useMedicationCorrelations" src/frontend/src/pages/MedicationDetail.tsx   # expect: import + call
grep -n "correlations" src/backend/api/medications.py                  # expect: /{medication_id}/correlations at ~:452
cd src/backend && python -m pytest tests/test_medication_correlations.py -p no:cacheprovider -q
```

Expected: no frontend copies of the observation-side rule; endpoint tests green. (Note: `utils/correlation.ts::findActiveMedications` legitimately remains — it answers the inverse question for the chart overlay.)

- [ ] **Step 3: CARE-QUOTE-001 holds on merged main**

```bash
cd src/backend && python -m pytest tests/test_documents_api.py -k CAREQ -p no:cacheprovider -q -v
```

Expected: `HC-CAREQ-001..003` all pass.

---

### Task 8: Post-merge re-verification on main

- [ ] **Step 1: Collected count matches what the resolved docs claim**

```bash
find src/backend -name __pycache__ -type d -exec rm -rf {} +
cd src/backend && python -m pytest tests/ --collect-only -q | tail -3
grep -n "collected" ../../CLAUDE.md ../../AGENT.md
```

Expected: the collected number equals the value written in Task 4 — in BOTH files, identical.

- [ ] **Step 2: Security gate fail-closed re-proof on main** (repeat Task 5 Steps 1–3 verbatim — missing file → 2, malformed → 2, clean → 0)

- [ ] **Step 3: Full backend suite + boot on main**

```bash
cd src/backend && python -m pytest tests/ -p no:cacheprovider -q && python -c "from main import app"
```

Expected: same pass profile as Task 6 Step 2.

- [ ] **Step 4: Docs gates on main**

```bash
python3 scripts/docs_lint.py && python3 scripts/generate_docs_index.py --check && python3 scripts/feature_list_lint.py && python3 scripts/repo_hygiene_check.py && python3 scripts/harness_drift_check.py
```

Expected: all exit 0.

- [ ] **Step 5: Record the work** — append a dated entry to `docs/features/TASK_LIST.md` Session Notes noting: both branches merged (PR numbers), measured collected count, poison-proof result, and that `POST /export/questions` unredacted-quote + SQL-FK-001 pragma flip remain deliberately open. Commit with `docs:` prefix on a short branch and PR it per repo convention (human merges).

---

## Done checklist

- Both branches landed on `main` via human-merged PRs; executor never touched `main`.
- Security gate proven fail-closed on the merged tree with a poisoned report (exit 2), and still exit-0 on clean input.
- Backend suite collected count measured post-merge and written identically into `CLAUDE.md` and `AGENT.md`; suite green (modulo the documented `test_api_rag_index_002b` environmental failure).
- `npx tsc --noEmit` + `npx vitest run` green on Windows; both Settings mounts coexist.
- All five doc conflicts resolved by union-or-regeneration; no branch content silently dropped.
