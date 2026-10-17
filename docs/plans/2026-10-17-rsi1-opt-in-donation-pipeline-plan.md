# RSI1-DONATE: Opt-In Local Data Donation Pipeline (RSI-1 / RSI-2) — Implementation Plan

**Last Updated:** 2026-10-17
**Owner:** repository owner
**Status:** PROPOSED (Opus planner). Docs only. No owner approval is recorded here. **Build is blocked on the open owner gates listed at the end.** No answer is inferred. Gates keep their state in [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md).
**Base measured:** `origin/main` @ `3536cc6` (2026-10-17). Profile migration head `013_adaptive_windows_local`.
**Refresh Trigger:** any owner answer to a DON-* gate; any commit to `src/backend/modules/redaction.py` (its rule set changes the recall numbers), `src/backend/modules/rl_dataset.py`, `src/backend/api/feedback.py`, `src/backend/models/response_feedback.py`, `src/backend/api/profiles.py` (`_SYNTHETIC_RESET_MODELS`, deletion sweep); C-P6 or C-P7 merging (FK and reset-tuple rules, contracts §c item 5); a new profile migration on `main`.

**Queue row:** [queue.md](2026-10-15-build-program/queue.md) RSI1-DONATE. **Sources:** owner rows RSI-1 (**"Build it as part of the workflow"**; owner: "RSI 1 - build out as part of workflow"; pipeline "consent → local strict redaction → local-only store (RSI-2) → leak eval → mix real+synthetic") and RSI-2 (**"No: everything stays local"**), both 2026-10-17 and landing with #123; handoff 2026-10-17 §2 item 4(c) (lands with #123); research `docs/research/2026-10-17-rsi-opt-in-data/00-README.md` §A and `02-private-synthetic-health-data.md` (land with #122); [contracts](2026-10-15-build-program/contracts.md) §b, §c.

> **For agentic workers:** REQUIRED SUB-SKILLS: superpowers:test-driven-development, superpowers:subagent-driven-development. Domain skills: `asclexis-backend`, `asclexis-guardrails`, `asclexis-evals` (no frontend domain skill exists; follow existing `src/frontend/src/components/settings/` cards).

## Goal

A patient can opt in, **per purpose and revocably**, to donate a copy of their own chat data for improving local models. Every donated record:
1. is redacted locally at `strict` by **calling** `modules/redaction.py` (never editing it);
2. is checked by a second, independent PHI detector whose recall is measured; a flagged record is dropped;
3. is stored only in that profile's encrypted vault (RSI-2: nothing leaves the device);
4. is leak-checked against planted canaries and the profile's own identifiers before any use;
5. can be combined with synthetic records, but synthetic data is only ever added. Real records are never replaced.

Revoking a purpose deletes that purpose's donated records and everything derived from them. Deleting the profile deletes everything, because it all lives in the vault.

## Non-negotiables

1. **`modules/redaction.py` is CALLED ONLY.** `RedactionEngine(policy_level="strict").redact(text)` is the only use. A missed identifier becomes a failing recall row in the report and an owner question. It is never "fixed" in `redaction.py` by this item (ask-first; any rule change is its own row, as E-1a / E-1b were).
2. **Local-first (RSI-2).** No network call anywhere in the pipeline. Synthetic generation uses `core.model_runner.get_model_runner()` only, never `core.external_runner.get_runner_for_request` (owner D12 covers the external runner, and RSI-2 rules it out here). A test pins that.
3. **Per-profile isolation.** All new tables live in the per-profile SQLCipher DB, used through `ProfileDbSession`. Nothing goes through the master `get_db()` except the audit log.
4. **Audit logging** on every new route: counts and opaque ids only (AUDIT-PHI-001). The purpose goes in `entity_id`, which is already an allowed string key (`core/audit.py:69-75`), so `core/audit.py` is **not** edited.
5. **Redaction before anything leaves.** If a file export is approved (DON-FILE-EXPORT), the writer runs strict redaction again at write time, as `rl_dataset.py` does (`:78-83`), and writes only under `rl_exports/profile_{id}/donation/`. The profile-delete route already sweeps `rl_exports/profile_{id}/` (`api/profiles.py:792-806`).
6. **Mix, never replace.** A manifest always contains every eligible real record, and synthetic records are tagged as synthetic.
7. **No safety thresholds lowered.** The recall target and the leak rule are owner numbers (DON-RECALL, DON-CANARY). A build that misses one stops and reports. It never relaxes the number.

## Evidence (verified on `3536cc6`)

| Fact | Where |
|---|---|
| Prior art for local preference export: `export_rl_datasets` strict-redacts prompt, response and correction (`_redact` → `RedactionEngine.redact` → `(text, redacted_count)`) and writes JSONL | `src/backend/modules/rl_dataset.py:19`, `:38`, `:78-83`, `:86-290` |
| Feedback rows: `prompt_snapshot`, `response_text`, `correction_text`, `rating`, per profile | `src/backend/models/response_feedback.py`, profile migration `008_response_feedback.py` |
| `POST /feedback/export` requires `confirmed=true`, confines output under `rl_exports/`, and audits counts via best-effort `_emit_audit` | `src/backend/api/feedback.py:341-449`, `:41-57` |
| `rl_exports/` is git-ignored (RSI-Q2 done) and swept on profile delete | `.gitignore:83`; `src/backend/api/profiles.py:792-806` |
| `RedactionEngine` levels `strict`/`standard`/`minimal`; strict-only additive rules RL-REDACT-001, E-1a | `src/backend/modules/redaction.py:23-196` (read, not edited) |
| E-1b and REDACT-EMAIL-REDOS are known strict gaps, still unplanned | [queue.md](2026-10-15-build-program/queue.md) "Status 2026-10-16 (second batch)" |
| Profile head `013_adaptive_windows_local`; C-P6 expects the next free number for its FK migration. Numbers go by merge order | `src/backend/migrations/profile/versions/`; contracts §c |
| Allowed audit string keys include `entity_type`, `entity_id`, `source_kind` | `src/backend/core/audit.py:69-75` |
| Settings UI cards live in `src/frontend/src/components/settings/`. `SettingsPage.tsx` is a shared file (C-GAM2B, B-1; contracts §b) | `ls src/frontend/src/components/settings/` |
| Every new route handler needs a CLASSIFICATION row, or HC-AUD-ORD-030 fails | `src/backend/tests/test_audit_order_guard.py`; contracts R-9 |

## Design

### Data model (one new profile migration, `NNN_data_donation`, contracts §c)

| Table | Columns | Notes |
|---|---|---|
| `donation_consents` | `id`, `profile_id`, `purpose` (enum string), `granted_at`, `revoked_at` (nullable), `consent_text_version` | one active row per purpose; revoke sets `revoked_at` and never deletes the consent row (that row is the record of the choice) |
| `donated_records` | `id`, `profile_id`, `purpose`, `origin` (`real` \| `synthetic` \| `canary`), `source_kind`, `source_id` (opaque, nullable for synthetic), `parent_id` (synthetic → real, nullable), `prompt_redacted`, `response_redacted`, `strict_redaction_count`, `created_at` | **no raw text column**. `source_id` is an opaque reference with no FK (see DON-SRC-DELETE) |

- The `purpose` enum is fixed by DON-PURPOSES.
- `NNN` = head on `origin/main` at the final rebase + 1, with `down_revision` = that head. The head literal (4 literals, or `PROFILE_HEAD` after C-P6) is updated in the same PR. Both §c check commands are pasted in the PR.
- After C-P7: both models are appended to `_SYNTHETIC_RESET_MODELS` in `api/profiles.py` (ask-first file, gate RESET-APPEND, answered "approve" 2026-10-17). If C-P7 has not merged, do not touch `api/profiles.py`, and note the follow-up in the PR.
- After C-P6: no FK is added, so there is no `PROFILE_CHECKS` row. If a reviewer asks for an FK, it gets `ondelete=` plus a row.

### Modules

Prefer extending existing code (CLAUDE.md §2).
- **`src/backend/modules/data_donation.py` (new, one module):** `grant`, `revoke`, `collect`, `leak_check`, `build_manifest`. A new module is justified because consent, the second pass and the canary/leak logic have no home today. The JSONL writer is **reused** from `rl_dataset.py` (`_write_jsonl`, `_redact`), not copied.
- **Second PHI detector:** its location depends on DON-DETECTOR. With option (a) it is `src/backend/modules/phi_second_pass.py`, a small rule set written independently of `redaction.py` and keyed to the Safe Harbor 18 categories (45 CFR 164.514(b)(2)). It **detects only**: it returns hits, never rewritten text. Any hit drops the record. With options (b) or (c) it is a thin local adapter around the library, with a dependency row and a licence check first.

### Pipeline per `collect(profile_db, purpose)`

1. Fail closed: no active consent for `purpose` → 0 records, and no read of source rows.
2. Read eligible source rows (DON-SOURCE) through `ProfileDbSession`.
3. For each text field: `RedactionEngine("strict").redact(...)`, then `phi_second_pass.detect(redacted)`. Any hit → drop the record, and count it by category, never by value.
4. Insert the survivors as `origin=real`.
5. Return counts only: collected, dropped by detector category, strict redaction count.

### Leak eval

- **Canaries.** On each `collect`, insert K synthetic canary records (`origin=canary`), each with a unique random fake identifier in every Safe Harbor shape the detectors claim to cover (fake MRN, phone, email, SSN-shaped, date, name). They are passed through the **same** steps 3-4. A canary that survives into `donated_records` with its secret intact means the pipeline leaked. `leak_check` fails and the purpose's manifest is blocked (DON-CANARY).
- **Store scan.** `leak_check` also scans every stored `real` and `synthetic` row for the profile's own display name (the only personal identifier the master `Profile` row stores, `models/profile.py:47`), by exact and case-folded match. Any hit blocks the manifest.
- **Extraction probe (model-machine, later).** `src/backend/scripts/donation_extraction_probe.py` prompts a model with each canary's prefix and checks whether the secret comes back (research 02 #3, #4). It runs only on a model tuned on a manifest, which is DON-FT-SCOPE. If fine-tuning is out of scope, this script is not built here, and the plan says so in the PR.

### Synthetic and mix (DON-SYNTH, DON-MIX)

- `build_manifest(purpose)` returns every `real` row plus at most `ratio × real_count` `synthetic` rows. It never returns `canary` rows, and it refuses (raises) if `leak_check` fails.
- If synthetic generation is in scope, it generates through `get_model_runner()` from already-redacted real rows. Each output is strict-redacted and second-pass-checked again, then stored as `origin=synthetic` with `parent_id`.
- Revoke deletes the purpose's `real` rows and every `synthetic` row whose `parent_id` points at one, in the same transaction.

### Routes (`src/backend/api/donation.py`, new router; each audited; route tests via `route_client`)

| Route | Behaviour | Audit `event_type` |
|---|---|---|
| `GET /donation/consents` | the purposes with state and `consent_text_version` | `donation.consent.view` |
| `PUT /donation/consents/{purpose}` `{granted: bool, consent_text_version}` | grant or revoke. Revoke deletes the derived rows and returns the deleted count | `donation.consent.grant` / `donation.consent.revoke` |
| `POST /donation/{purpose}/collect` `{confirmed: true}` | runs `collect`, returns counts | `donation.collect` |
| `GET /donation/{purpose}/report` | counts by origin, dropped-by-category, last `leak_check` result (pass/fail plus counts) | `donation.report.view` |
| `POST /donation/{purpose}/export` (only if DON-FILE-EXPORT = yes) | `build_manifest`, re-redact, JSONL under `rl_exports/profile_{id}/donation/` | `donation.export` |

Details are counts only. `entity_type="donation"`, and `entity_id=<purpose>`.

### Frontend

- `src/frontend/src/components/settings/DataDonationCard.tsx`: one switch per purpose, the owner-approved consent text (DON-COPY), a plain "Stop and delete" action per purpose, and counts from `/report`.
- `src/frontend/src/services/donation.ts`.
- One import plus render line in `src/frontend/src/pages/SettingsPage.tsx` (shared file; runs after C-GAM2B and B-1 or merges main over them, contracts §b).

## Files

| File | Change |
|---|---|
| `src/backend/migrations/profile/versions/NNN_data_donation.py` | new |
| `src/backend/models/data_donation.py`, `src/backend/models/__init__.py` | new models plus registration |
| `src/backend/modules/data_donation.py` | new |
| `src/backend/modules/phi_second_pass.py` | new (DON-DETECTOR = a) |
| `src/backend/modules/rl_dataset.py` | only if `_write_jsonl` / `_redact` need to become importable without the leading underscore; otherwise import them as they are |
| `src/backend/api/donation.py`, `src/backend/api/__init__.py` (router include, as `feedback` at `:66-67`) | new router plus one include line |
| `src/backend/scripts/measure_phi_recall.py` | new: recall report (Task 3) |
| `src/backend/tests/fixtures/phi_recall/corpus_v1.json` | new: synthetic sentences with labelled planted identifiers per Safe Harbor category |
| `src/backend/tests/test_data_donation.py`, `src/backend/tests/test_donation_routes_http.py`, `src/backend/tests/test_phi_second_pass.py` | new: HC-DON-001…020 |
| `src/backend/tests/test_audit_order_guard.py` | own CLASSIFICATION rows only (R-9) |
| head literal (`src/backend/tests/test_care_tasks.py`, `src/backend/tests/test_profile_migrations_sqlcipher_fallback.py`, `src/backend/tests/test_source_spans.py`, or `src/backend/tests/support/migrations.py` after C-P6) | head bump |
| `src/backend/api/profiles.py` | `_SYNTHETIC_RESET_MODELS` append, **only after C-P7** (RESET-APPEND) |
| `src/frontend/src/components/settings/DataDonationCard.tsx`, `src/frontend/src/services/donation.ts`, `src/frontend/src/pages/SettingsPage.tsx`, `src/frontend/src/__tests__/DataDonationCard.test.tsx` | consent UI plus vitest |
| `docs/compliance/data-privacy.md` | one new section describing the donated set (owned lines only; after F-6 / WEAR-14 per contracts §b) |
| slots | none (contracts §d) |

Size: about 700 lines of non-test diff. **Split into 3 PRs** in this order, each its own build-item: **PR-1** migration, models, consent routes and UI (Tasks 1, 2, 6); **PR-2** collect, second pass and recall report (Tasks 3, 4); **PR-3** leak eval, manifest and synthetic (Task 5).

## Tasks (test-first)

### Task 0: Gates and re-verify

1. Every gate in "Open owner gates" that governs the PR being built is answered in owner-decisions. If one is not, that task is skipped (RUNBOOK §4 step 3). PR-1 needs DON-PURPOSES, DON-REVOKE and DON-COPY. PR-2 needs DON-SOURCE, DON-DETECTOR, DON-RECALL, DON-SRC-DELETE and DON-RLEXPORT. PR-3 needs DON-CANARY, DON-MIX, DON-SYNTH, DON-FT-SCOPE and DON-FILE-EXPORT.
2. `git diff origin/main -- src/backend/modules/redaction.py` is empty at the start and at the end.
3. The §c head check. Measure collected (contracts §d step 2).

### Task 1: Schema (HC-DON-001…003)

- **HC-DON-001:** upgrade from the current head creates both tables, and downgrade drops them. Single head (§c checks).
- **HC-DON-002:** `donated_records` has no column whose name matches `raw|original|unredacted|plain` (a structure pin).
- **HC-DON-003:** both tables are created in the **profile** DB and are absent from the master metadata.

### Task 2: Consent routes (HC-DON-004…009), all through `route_client`

- **HC-DON-004:** a fresh profile shows every purpose as not granted (opt-in default).
- **HC-DON-005:** grant, then `GET` shows it granted with its `consent_text_version`. Exactly one `donation.consent.grant` audit row, whose details hold no free text.
- **HC-DON-006:** revoke deletes that purpose's `real` rows and their `synthetic` children, keeps the other purposes' rows, sets `revoked_at`, and audits `donation.consent.revoke` with the deleted count.
- **HC-DON-007:** profile A cannot read or change profile B's consents (403 plus one `denial.cross_profile` row, contracts I-12).
- **HC-DON-008:** an unknown purpose gives 422.
- **HC-DON-009:** HC-AUD-ORD-030 passes with the new rows.

### Task 3: Second detector and recall (HC-DON-010…013)

- **HC-DON-010:** `phi_second_pass.detect` finds one planted example per supported Safe Harbor category in `corpus_v1.json`, and returns **no** hit on 20 synthetic lab sentences with analyte names, units and reference ranges (the over-redaction check; research 02 #11).
- **HC-DON-011:** `measure_phi_recall.py` reports per-category recall for `strict` alone, the second pass alone, and their union. On a 3-item toy corpus with one known miss it reports exactly 2/3 (the measurement can fail).
- **HC-DON-012:** `git grep -n "^from modules.redaction\|^import modules.redaction" src/backend/modules/phi_second_pass.py` is empty (independent second detector).
- **HC-DON-013:** the recall report on `corpus_v1.json` is pasted in the PR. If the union misses DON-RECALL in any category, the PR stays draft and the report goes to the owner. The target is never edited to fit.

### Task 4: Collect (HC-DON-014…016)

- **HC-DON-014:** with no consent, `collect` returns 0 and issues no `SELECT` on source tables (spy).
- **HC-DON-015:** with consent, a source row containing `Patient Name: Jane Doe, phone 555-123-4567` is stored only in redacted form. No stored column contains `Jane`, `Doe` or `555-123-4567`.
- **HC-DON-016:** a source row whose strict output still contains something the second pass flags (built from a known strict gap; Task 0 records which one) is **dropped**, and counted under its category.

### Task 5: Leak eval, manifest, synthetic (HC-DON-017…020)

- **HC-DON-017:** with a canary whose secret survives (forced by a patched detector in the test), `leak_check` fails and `build_manifest` raises.
- **HC-DON-018:** a stored row containing the profile's display name fails `leak_check`.
- **HC-DON-019:** the manifest includes every `real` row, includes no `canary` row, and keeps `synthetic ≤ ratio × real`. With 0 real rows it returns 0 synthetic rows.
- **HC-DON-020 (local only):** synthetic generation calls `get_model_runner()`. `core.external_runner.get_runner_for_request` is patched to raise, and generation still succeeds, which shows it is never consulted.

### Task 6: Consent UI (vitest)

- **HC-DON-FE-001:** each purpose renders with its switch off by default.
- **HC-DON-FE-002:** toggling calls `PUT` with the right purpose.
- **HC-DON-FE-003:** "Stop and delete" asks for confirmation, then calls revoke and shows the deleted count.

## Acceptance (per PR)

```bash
cd src/backend
P="$(git rev-parse --show-toplevel)/scripts/pyslot.sh"; PY=~/venvs/asclexis-311/bin/python
$P env HF_HUB_OFFLINE=1 $PY -m pytest tests/test_data_donation.py tests/test_donation_routes_http.py tests/test_phi_second_pass.py tests/test_audit_order_guard.py -p no:cacheprovider -q   # RED per id first
$P env HF_HUB_OFFLINE=1 $PY -m pytest tests/ -p no:cacheprovider -q | tail -3   # no new failures; collected + delta
grep -h "^down_revision" migrations/profile/versions/*.py | sort | uniq -d   # prints nothing
$PY -c "from alembic.script import ScriptDirectory; from core.migrations import _get_alembic_config as c; print(ScriptDirectory.from_config(c('profile')).get_heads())"   # one head
$PY scripts/measure_phi_recall.py   # PR-2: paste the per-category table
git diff origin/main...HEAD -- src/backend/modules/redaction.py src/backend/core/audit.py src/backend/core/external_runner.py   # prints nothing
git grep -nE "httpx|requests\.|urllib\.request|socket\." -- src/backend/modules/data_donation.py src/backend/modules/phi_second_pass.py src/backend/api/donation.py   # prints nothing
python -c "from main import app"
cd ../frontend && npx tsc --noEmit && npx vitest run src/__tests__/DataDonationCard.test.tsx
```

## Gates already answered (land with #123)

| Gate | Answer |
|---|---|
| RSI-1 | build the pipeline as part of the workflow (owner override) |
| RSI-2 | everything stays local |
| RSI-4 | Track 2 = app agent (relevant if "harness traces" is a purpose) |
| RESET-APPEND | approve (reset tuple append, after C-P7) |
| AUTO-MERGE | standing for build-program PRs; ask-first diffs still need the owner |

## Ask-first

- `src/backend/modules/redaction.py`: **called only, never edited.** The acceptance diff must be empty.
- `src/backend/api/profiles.py`: reset-tuple append only, after C-P7, under RESET-APPEND.
- Encryption/auth: none. The new tables use the existing SQLCipher profile engine. No key, KDF or `core/auth.py` edit. If one seems needed, STOP.
- `modules/interpret_safety.py`, `faithfulness.py`, `verifier_agent.py`: not touched.

## Open owner gates (exact wording, ready to ask; none inferred)

1. **DON-PURPOSES:** "The donation screen has one switch per purpose. Which purposes ship? (a) all three: fine-tune local models, seed synthetic data, and app-agent run traces (Recommended); (b) fine-tune and synthetic only; (c) fine-tune only."
2. **DON-SOURCE:** "Which of a patient's data may be donated? (a) only chat turns the patient rated with feedback: question, answer and correction (Recommended); (b) every legacy chat turn; (c) also document text and lab values."
3. **DON-DETECTOR:** "Which second PHI detector runs after strict redaction? (a) a small in-repo detector for the Safe Harbor identifier types, written separately from redaction.py, no new dependency (Recommended); (b) Microsoft Presidio (new dependency plus a spaCy model download at install time); (c) Philter (BSD-3, new dependency)."
4. **DON-RECALL:** "What must the redaction plus second detector catch on the synthetic test corpus before donation is enabled? (a) 100% of planted canaries and at least 95% per Safe Harbor category, and any record the second detector flags is dropped, not re-redacted (Recommended); (b) 100% in every category; (c) you set different numbers."
5. **DON-CANARY:** "If any planted canary or the profile's own display name is found in the donated set, should that purpose's dataset be blocked until you look? (a) Yes, zero tolerance (Recommended); (b) drop the leaking record and continue."
6. **DON-REVOKE:** "When a patient turns a purpose off: (a) delete that purpose's donated records and every synthetic record made from them, immediately, and keep only a dated record of the choice (Recommended); (b) also delete any model adapter trained on them (only applies if fine-tuning is built); (c) keep data until the patient deletes it separately."
7. **DON-SRC-DELETE:** "If a patient deletes the chat session a donated record came from, should the donated copy be deleted too? (a) Yes (Recommended); (b) No, the donated copy is already redacted and stands alone."
8. **DON-FT-SCOPE:** "Is local fine-tuning (QLoRA on the RTX 3080) part of this item? (a) No: build the consented, redacted, leak-checked dataset only; fine-tuning and the extraction probe are a later row (Recommended); (b) Yes, include a local LoRA run and the extraction probe."
9. **DON-SYNTH:** "How should synthetic records be made, if at all, in this item? (a) the local model rewrites already-redacted records through ModelRunner, labelled 'synthetic, no differential-privacy guarantee' (Recommended for v1); (b) local differentially-private synthesis (Private Evolution style) with a privacy budget ε you set; (c) no synthetic generation yet."
10. **DON-MIX:** "Most synthetic records allowed per real record in a dataset? (a) 1:1, and every real record is always kept (Recommended); (b) 2:1; (c) another ratio."
11. **DON-COPY:** "The consent screen wording is patient-facing. (a) I draft it from the research notes and you approve it before PR-1 merges (Recommended); (b) you write it."
12. **DON-FILE-EXPORT:** "May the pipeline write a local JSONL file of the dataset, strict-redacted again, under `rl_exports/profile_<id>/donation/` (already deleted with the profile) for a local trainer? (a) Yes (Recommended); (b) No, the dataset stays inside the encrypted vault only."
13. **DON-RLEXPORT:** "Once donation consent exists, should the existing `POST /feedback/export` RL export also require the fine-tune consent to be on? (a) Yes, one consent model for both (Recommended); (b) No, keep its confirmed=true flag as it is."

## Risks

- **Redaction recall gaps** (research 02 #10, #11; E-1b and REDACT-EMAIL-REDOS are known strict gaps). The second pass drops records rather than guessing, and the recall table makes gaps visible. Gaps are raised as `redaction.py` rows for the owner, never patched here.
- **Memorization survives fine-tuning** (research 02 #3): this is why the extraction probe is mandatory before any model trained on a manifest is used (DON-FT-SCOPE).
- **Synthetic drift and collapse** (research 02 #1, #2): mitigated by the mix rule (HC-DON-019).
- **Scope creep:** 3 PRs, each gated separately. The plan builds no trainer unless DON-FT-SCOPE says so.
