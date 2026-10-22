# RSI1-DONATE: Opt-In Local Data Donation Pipeline (RSI-1 / RSI-2) — Implementation Plan

**Last Updated:** 2026-10-22 (Delta 2026-10-22: DON-NER-MEASURE, gate DON-NER-MODEL, PR-2 resume delta, DON-COPY-V3 build and order); 2026-10-17
**Owner:** repository owner
**Status:** PROPOSED (Opus planner). Docs only. No owner approval is recorded here. **Build is blocked on the open owner gates listed at the end.** No answer is inferred. Gates keep their state in [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md).
**Base measured:** `origin/main` @ `3536cc6` (2026-10-17). Profile migration head `013_adaptive_windows_local`.
**Delta 2026-10-20:** all DON-* gates answered; PR-2 gains `api/feedback.py` and the chat-session delete route; PR-3's leak rule follows DON-CANARY (b). See [Delta 2026-10-20](#delta-2026-10-20-planner-answered-gates-pr-2-file-list-pr-3-leak-rule).
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

- **Canaries.** On each `collect`, insert K synthetic canary records (`origin=canary`), each with a unique random fake identifier in every Safe Harbor shape the detectors claim to cover (fake MRN, phone, email, SSN-shaped, date, name). They are passed through the **same** steps 3-4. A canary that survives into `donated_records` with its secret intact means the pipeline leaked. `leak_check` fails and the purpose's manifest is blocked (DON-CANARY). **Superseded by [Delta 2026-10-20](#delta-2026-10-20-planner-answered-gates-pr-2-file-list-pr-3-leak-rule) (DON-CANARY (b)).**
- **Store scan.** `leak_check` also scans every stored `real` and `synthetic` row for the profile's own display name (the only personal identifier the master `Profile` row stores, `models/profile.py:47`), by exact and case-folded match. Any hit blocks the manifest. **Superseded by [Delta 2026-10-20](#delta-2026-10-20-planner-answered-gates-pr-2-file-list-pr-3-leak-rule) (DON-CANARY (b)).**
- **Extraction probe (model-machine, later).** `src/backend/scripts/donation_extraction_probe.py` prompts a model with each canary's prefix and checks whether the secret comes back (research 02 #3, #4). It runs only on a model tuned on a manifest, which is DON-FT-SCOPE. If fine-tuning is out of scope, this script is not built here, and the plan says so in the PR.

### Synthetic and mix (DON-SYNTH, DON-MIX)

- `build_manifest(purpose)` returns every `real` row plus at most `ratio × real_count` `synthetic` rows. It never returns `canary` rows, and it refuses (raises) if `leak_check` fails. **Superseded by [Delta 2026-10-20](#delta-2026-10-20-planner-answered-gates-pr-2-file-list-pr-3-leak-rule) (DON-CANARY (b)).**
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

## Delta 2026-10-20 (planner): answered gates, PR-2 file list, PR-3 leak rule

Planned 2026-10-20 on `origin/main` @ `b2b3f4e` from the #211 L0 comment (queue bullets RSI1-DONATE-PR2-FILES and RSI1-DONATE-PR3-DELTA). This section overrides the lines it names; everything else above stands. No owner answer is inferred: each one below is quoted from [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md), and none is re-asked.

### All 13 DON-* gates are answered (2026-10-19, `owner-decisions-2026-09-27.md:278-290`)

The "Open owner gates" list at the end of this plan is now a record of the questions asked. The answers:

| Gate | Answer (quoted) | Effect on the plan |
|---|---|---|
| DON-PURPOSES `:278` | **(a) All three** — "Fine-tune, synthetic seed, app-agent traces." | as designed |
| DON-REVOKE `:279` | **(a) Delete now** — "Delete that purpose's records and synthetic children immediately; keep a dated record of the choice." | as designed (HC-DON-006) |
| DON-COPY `:280` | **(a) Agent drafts, I approve** — "Owner approves the text before PR-1 merges." | PR-1 merge; also covers PR-2's one new refusal string (below), approved at PR-2 merge |
| DON-SRC-DELETE `:281` | **(a) Yes** — "Donated copy is deleted with its source session." | PR-2 edits the chat-session delete route (below) |
| DON-SOURCE `:282` | **(a) Rated chat turns** — "Only chat turns the patient rated with feedback: question, answer and correction." | as designed |
| DON-DETECTOR `:283` | **(a) In-repo Safe Harbor** | as designed (`modules/phi_second_pass.py`) |
| DON-RECALL `:284` | **(a) 100% canary, >=95% per category** — "a flagged record is dropped, not re-redacted." | as designed (HC-DON-013 gate unchanged) |
| DON-RLEXPORT `:285` | **(a) Yes, one consent** — "One consent model for both donation and the RL export." | PR-2 edits `api/feedback.py` (below) |
| DON-CANARY `:286` | **(b) Drop and continue** — "Drop the leaking record and carry on." (not the recommended (a)) | PR-3 leak rule rewritten (below) |
| DON-MIX `:287` | **(a) 1:1** — "1:1, and every real record is always kept." | as designed (HC-DON-019) |
| DON-SYNTH `:288` | **(a) Local rewrite** — "labelled 'synthetic, no DP guarantee'." | as designed (HC-DON-020) |
| DON-FT-SCOPE `:289` | **(b) Yes, LoRA + probe** — "Local LoRA fine-tune and the extraction probe are in scope; widens PR-3 and needs the model machine." (not the recommended (a)) | PR-3 split proposed (below) |
| DON-FILE-EXPORT `:290` | **(a) Yes** — "Re-redacted local JSONL under rl_exports/profile_<id>/donation/." | as designed |

### PR-2 file list delta (DON-RLEXPORT, DON-SRC-DELETE)

The plan's "Files" table and the queue row named neither route file, but PR-2 needs both (#211 L0 comment):

1. **`src/backend/api/feedback.py`** (`export_dataset`, `POST /feedback/export`, `:340-448` on `b2b3f4e`). After the existing `confirmed` check (`:356-360`) and before any feedback row is read, refuse with HTTP 403 when the profile has no active `fine_tune` consent (DON-RLEXPORT (a)); no file is written. The detail string is new text the Settings export button can show (`src/frontend/src/pages/SettingsPage.tsx:916`), so it is drafted in PR-2 and approved by the owner at PR-2 merge under DON-COPY (a). The audit-guard row for `export_dataset` (`tests/test_audit_order_guard.py:54`, "excluded: writes export files; master audit only") does not change.
2. **`src/backend/api/assistant.py`** (`delete_session`, `DELETE /assistant/sessions/{session_id}`, `:501-529` only). Before `profile_db.delete(chat_session)`, in the same transaction, delete the `donated_records` rows with `origin="real"`, `source_kind="response_feedback"` and `source_id` in that session's `ResponseFeedback.id`s (`models/response_feedback.py` carries `session_id`), plus their `synthetic` children (`parent_id`). A `data_donation.delete_for_session(profile_db, session_id) -> int` helper does the work; the route only calls it. The A2 started/completed audit around the delete (AUDIT-C-ASSIST) is unchanged.
3. **Tests:** `src/backend/tests/test_donation_routes_http.py` (already in the list) gains, through `route_client`:
   - **HC-DON-021:** `POST /feedback/export {confirmed: true}` with no fine-tune consent → 403 and no file under the export root; with the consent granted → 200 and the files, as today.
   - **HC-DON-022:** two sessions with rated turns, both donated; `DELETE /assistant/sessions/{a}` → session a's donated `real` rows and their `synthetic` children are gone, session b's stay.
   Existing callers of the export route need a consent row (fixture lines only): `src/backend/tests/test_rl_export_prompt_snapshot.py` (`_rate_and_export`, `:67-85`) and `src/backend/tests/test_rl_feedback.py` (the direct `export_dataset` calls at `:303-360` whose expected status would otherwise become 403).
4. **Shared file:** `api/assistant.py` is in B-3's and G-C5's lists. PR-2 never runs beside a non-draft PR on it (contracts §b rules 1-2; B-3 is a parked draft).

PR-2 expected collected delta: +2 on top of Tasks 3-4.

### PR-3 delta: the leak rule under DON-CANARY (b)

The owner chose "Drop the leaking record and carry on." These lines are superseded: Design "Leak eval", the last two sentences of **Canaries** ("…`leak_check` fails and the purpose's manifest is blocked (DON-CANARY)") and the last sentence of **Store scan** ("Any hit blocks the manifest"); Design "Synthetic and mix", "and it refuses (raises) if `leak_check` fails"; Task 5 HC-DON-017 and HC-DON-018 as written.

**New rule:**
- `leak_check(profile_db, purpose)` deletes every leaking record it finds and returns counts only: `canaries_planted`, `canaries_survived`, `display_name_hits`, `dropped`. It never blocks the purpose.
  - A canary whose secret survives into `donated_records` is a leaking record: it is deleted and counted in `canaries_survived`. Canaries are never in a manifest either way.
  - A `real` or `synthetic` row that contains the profile's display name (exact or case-folded) is deleted together with its `synthetic` children and counted in `display_name_hits` and `dropped`.
- `build_manifest(purpose)` runs `leak_check` first and builds from what is left. It does not raise for a leak.
- `GET /donation/{purpose}/report` shows the last `leak_check` counts (the route table already says "pass/fail plus counts"; "pass/fail" becomes the counts).

**What (b) does not cover, stated for the record (not a question):** a surviving canary shows that a real record of the same shape may have leaked too, and that record cannot be found, because its secret is unknown. Under (b) the pipeline drops what it can see and carries on. DON-RECALL (a) is unchanged: Task 3's corpus gate (100% of canaries, ≥95% per category) still holds PR-2 at draft if missed, and non-negotiable 7 still holds, because "drop and continue" is the owner's leak rule, not a relaxed one. The PR-3 body repeats this paragraph next to the measured `canaries_survived` count.

**Tests (replace HC-DON-017 and HC-DON-018):**
- **HC-DON-017 (rev):** a canary whose secret survives (forced by a patched detector) → `leak_check` deletes it and returns `canaries_survived == 1`; `build_manifest` returns without raising, with every `real` row and no canary row.
- **HC-DON-018 (rev):** a stored `real` row with the display name and its `synthetic` child → `leak_check` deletes both (`display_name_hits == 1`, `dropped == 2`) and keeps the other rows; the manifest does not contain them.
- **HC-DON-018b (new):** `build_manifest` with no explicit `leak_check` call first still excludes a display-name row (it runs the check itself).

PR-3 expected collected delta: +1 on top of Task 5 (HC-DON-018b).

### DON-FT-SCOPE (b): proposed PR-3 split

The plan has no trainer design: the extraction-probe bullet says "If fine-tuning is out of scope, this script is not built here". DON-FT-SCOPE (b) puts the LoRA run and the probe in scope and "needs the model machine". Proposal (L0 may merge the two back):
- **PR-3a** (runtime claude): Task 5 as revised above.
- **PR-3b** (model machine): the local LoRA run on a PR-3a manifest and `src/backend/scripts/donation_extraction_probe.py`. It needs its own plan delta before it starts, because three design points are open: the trainer and its dependencies (a new training dependency is its own dependency row and licence check); where the probe loads the tuned model (CLAUDE.md §3 routes LLM calls through `ModelRunner`; compare GC5-OL-3); and what revoke does to an adapter trained on revoked records (DON-REVOKE (a) deletes records and synthetic children; its option (b), which also deleted adapters, was not chosen). Queue bullet **RSI1-DONATE-FT-PLAN** tracks that plan delta; it is not planned here.

## Delta 2026-10-20, second (planner): #211 review notes for PR-2, and RRSI-OQ-25

Planned on `origin/main` @ `699eb18`. PR-2 is draft #239 (head `5f2c7d3`); this delta edits none of its files and changes no PR-2 task. **PR-2 is parked** (owner DON-RECALL-R2, 2026-10-20: "Keep #239 as a draft with the measured table and the residual-risk list recorded; donation stays off. Revisit after the 2026-10-24 freeze with a stronger local detector … as its own planned row and owner gate. The 95% target stays."), so "PR-2 (in flight)" below means "in #239, parked".

**Requirement carried for whichever row turns collection on** (moved here from RUNSTEP-CONTRACT after the #248 Codex review, MAJOR 4): a RunLog-isolation test with a positive control. Grant `fine_tune` consent on the current copy version, run one agent chat whose stub tool output carries a canary in a field `draft` never renders, rate that turn (a `ResponseFeedback` row), run `collect`; require the rated turn's redacted question and answer to be donated (count ≥ 1) and the canary to be absent from every donated row. A scratch mutant that copies `run_log` payloads into the donated record must fail it. An empty collection must fail it too. Each #211 adversarial-review note (the queue bullet "RSI1-DONATE-PR2 notes") was checked against `main` and #239's diff:

| Note | State on `699eb18` / #239 | Where it goes |
|---|---|---|
| An `ended_reason` column (a closed consent row may be a patient revoke or a supersede by a new copy version) | No column; the model docstring now says so (`src/backend/models/data_donation.py:19-25`, "revoked_at also closes a row superseded by …"). #239 adds no migration. | No row. Revisit only if an audit or UI must tell the two apart; that needs a profile migration (contracts §c) |
| Revoke deletes cross-purpose synthetic children, unpinned | **Fixed in PR-1:** HC-DON-006 seeds a synthetic child filed under another purpose; only the `parent_id` delete removes it (count 9, `src/backend/tests/test_donation_routes_http.py:258-294`) | Done |
| Canary rows after revoke | Kept by design today and pinned (HC-DON-006b, `:319-332`); DON-REVOKE (`owner-decisions-2026-09-27.md:279`) covers "records and synthetic children" and is silent on canaries | PR-3 (leak eval and canaries), as the #211 final review said; no new gate unless PR-3 proposes sweeping them |
| Move the logic to `modules/data_donation.py` | #239 adds `src/backend/modules/data_donation.py` (collect, consent check) | PR-2 (in flight) |
| HC-DON-007 isolation via 403 + `denial.cross_profile` | Not applicable: the donation routes are session-scoped with no `{profile_id}` in the path, so there is nothing to deny; isolation is the vault plus the `profile_id` filter, which HC-DON-007b proves in one vault (`:370`) | No row (PR-1 body records the deviation) |
| Stale-version consent shows as granted (final-review finding 1) | `ConsentState.current` exists on `main` (`src/backend/api/donation.py:46-47`, `:69-77`); #239's `collect` refuses a non-current row (DON-STALE) | PR-2 (in flight) |

**RRSI-OQ-25** (`owner-decisions-2026-09-27.md:346`): "Accept as already decided, under strict redaction plus the Safe Harbor detector, and make sure the DON-COPY wording says agent answers are included." The approved copy (`2026-10-20-v2`, DON-COPY-R2 `:320`; `src/frontend/src/components/settings/DataDonationCard.tsx:20-45`) says "For chat answers I have rated or will rate" for all three purposes and never says that answers written by the step-by-step assistant (agent) are included. The row itself says "Any v3 consent copy needs its own DON-COPY yes." So a copy bump is needed, and it is gated:

- **DON-COPY-V3** (open; asked with the exact v3 strings once drafted; donation is parked by DON-RECALL-R2, so not before the post-freeze donation row): "RRSI-OQ-25 asks the consent copy to say agent answers are included. Approve this v3 change? (a) add one sentence to the intro: 'This includes answers from the step-by-step assistant.', version `2026-10-2x-v3`; existing grants become not current and must re-agree (DON-STALE) (Recommended: one sentence, every purpose covered) (b) add 'including step-by-step assistant answers' inside each purpose description (c) no copy change; record that 'chat answers' already covers agent answers."
- **Files** (after #239 merges; both files are PR-1/PR-2 files): `src/frontend/src/components/settings/DataDonationCard.tsx` (copy and version), the module that defines `CURRENT_CONSENT_TEXT_VERSION` at build time (on #239's head `19e7a32` it moves to `src/backend/modules/data_donation.py:27`, `collect` compares it at `:60` and `api/donation.py:27-32` imports it; on `main` today it is `src/backend/api/donation.py:34`; #248 Codex re-review MAJOR 3): bump it there and nowhere else, `src/backend/tests/test_data_donation.py` (two version tests), `src/frontend/src/__tests__/DataDonationCard.test.tsx`, `src/backend/tests/test_donation_routes_http.py` (version literal lines only). It rides on PR-3, or a small PR-2b if PR-3 is not near; either way after #239 merges and after DON-COPY-V3 is answered. Under (c), no files.
- A copy bump marks every existing grant not current (`api/donation.py:77` on `main`), so a patient who agreed to v2 must re-agree before `collect` reads anything. The PR body must say so. Tests (`src/backend/tests/test_data_donation.py`, ids after #239's, e.g. HC-DON-023/024): a profile with an active **v2** `fine_tune` consent and a rated turn collects **0** rows after the bump; the same profile after re-granting on **v3** collects ≥ 1 (positive control); a mutant that compares against the old constant fails the first test.

## Delta 2026-10-22 (planner): on-device detector (DON-NER-MEASURE), new gate DON-NER-MODEL, PR-2 resume delta, DON-COPY-V3 build

Planned 2026-10-22 on `origin/main` @ `d2843e8` from owner rows RSI1-DONATE-PR2 and DON-COPY-V3 (`owner-decisions-2026-09-27.md:379`, `:380`; L0 comment 6349489069 on PR #288 records both verbatim). This section overrides the lines it names; everything above stands. No owner answer is inferred.

- **RSI1-DONATE-PR2** (`:379`): **"Plan an on-device detector"**: "Planner writes a row to pick and measure a local NER model (offline, bundled like the embedding model); its model/dependency choice comes back to you as a gate; donation stays off until >=95%. Most work, new dependency, no recall guarantee."
- **DON-COPY-V3** (`:380`): **"(a) One intro sentence (Recommended)"**: "Add 'This includes answers from the step-by-step assistant.' to the intro as v3; existing grants must be renewed. One string; source says 'one sentence, every purpose covered'."
- **Unchanged:** DON-RECALL (a) (`:284`, 100% canaries, ≥95% per Safe Harbor category, a flagged record is dropped, not re-redacted); DON-RECALL-R2 (`:355`, "The 95% target stays"); non-negotiable 1 (`modules/redaction.py` is **called only**, never edited); non-negotiable 7 (no target is lowered). Donation stays off: #239 stays a `[blocked:claude]` draft until the "PR-2 resume" bar below is met.

### Facts (`d2843e8`, #239 head `19e7a32`)

1. At park (#239 L0 comment 6307117650): name 10/14 (71%), geographic 6/8 (75%), age_over_89 8/10 (80%); "over-drop 6/10 Title Case answers". The widened name rule includes a bare Title Case pair alternative (`\b{_NAME}\s+{_NAME}\b`, `src/backend/modules/phi_second_pass.py` on `19e7a32`), which is what drops "Key Findings", "Mayo Clinic", "Healthcare Provider"; `1/2` and `3/4` read as dates (#239 review, comments on the PR).
2. `corpus_v1.json` on `19e7a32` has 12 categories, 109 items (name 14, geographic 8, date 14, phone 5, email 5, ssn 10, mrn 8, account_number 10, url 5, ip_address 5, age_over_89 10, device_vehicle_id 5) plus 20 `non_phi` lab sentences. It was written by the implementer after the detector; the #239 reviews flagged it three times as written to fit (recurring-failures mode 1).
3. **No new pip dependency is needed for a Hugging Face token-classification model:** `src/backend/requirements.txt:73` already has `sentence-transformers>=2.2.0`, which pulls `transformers` and `torch`; the box's 3.11 venv has `transformers 5.20.1`, `torch 2.14.1+cpu`, `tokenizers 0.23.3` (`ls ~/venvs/asclexis-311/lib/python3.11/site-packages`, 2026-10-22).
4. **Bundle precedent:** the NLI cross-encoder is fetched once by `scripts/download_models.py nli` (`cmd_nli`, `src/backend/scripts/download_models.py:407`): pinned repo + revision + weights sha256, exclusive `.partial` directory, sha check, never deletes a directory it did not create; loaded with `local_files_only=True` and an integrity check (`src/backend/modules/embeddings.py:52-105`). The detector bundle follows this pattern exactly.
5. **Good-answer text already in the repo, written by independent agents** (false-drop set): `src/backend/tests/fixtures/prohibited_patterns/held_out_dev.json` (175 `must_allow`), `held_out_final.json` (185), `held_out_final2.json` (171), `in_sample.json` (15); and the served-answer `model_output` of `src/backend/tests/legacy_eval/golden/answer-*.json`.

### Candidates (licence read from each model card's metadata via the Hugging Face API on 2026-10-22; the row re-reads the card text and records the revision)

| Candidate | Licence (card) | Weights | Labels relevant to the misses | New pip dependency | Notes |
|---|---|---|---|---|---|
| `obi/deid_roberta_i2b2` @ `78f2152eb93d` | MIT | `model.safetensors` 1.42 GB | `PATIENT`, `STAFF`, `LOC`, `AGE`, `DATE`, `ID`, `PHONE`, `EMAIL`, `HOSP`, `PATORG`, `OTHERPHI` (BILOU) | none (`transformers`) | trained on i2b2 2014 clinical notes (surrogate PHI, n2c2 data-use agreement): the row records what the card says about training data |
| `StanfordAIMI/stanford-deidentifier-base` @ `661b9c1c717d` | MIT | `pytorch_model.bin` only, 438 MB | `PATIENT`, `HCW`, `HOSPITAL`, `DATE`, `ID`, `PHONE`, `VENDOR`; **no** `AGE` or location label | none | pickle-only weights: load only with `weights_only` / converted to safetensors at fetch, or exclude; cannot help geographic or age |
| `dslim/bert-base-NER` @ `d1a3e8f13f8c` | MIT | `model.safetensors` 433 MB | `PER`, `LOC` (CoNLL-03, news text) | none | general NER; no age or date |
| `urchade/gliner_multi_pii-v1` @ `1fcf13e85f4e` | Apache-2.0 | `pytorch_model.bin` 1.16 GB | zero-shot PII labels by name (person, address, age, …) | **`gliner`** (Apache-2.0, PyPI 0.2.29, `>=3.10`) | new dependency + pickle weights |
| Presidio analyzer + spaCy `en_core_web_lg` | MIT (both) | spaCy model wheel | `PERSON`, `LOCATION`, `DATE_TIME`; no age entity by default | **`presidio-analyzer`** (MIT, `>=3.10,<3.15`), **`spacy`** (MIT) | two new dependencies; rules + NER hybrid |
| ~~`iiiorg/piiranha-v1-detect-personal-information`~~ | CC-BY-NC-ND-4.0 | — | — | — | **excluded**: non-commercial, no derivatives |
| ~~`nvidia/gliner-PII`~~ | "other" | — | — | — | **excluded** unless its licence text is read and recorded |

### DON-NER-MEASURE (new queue row): measure, no product code

Runs on the GPU box in a scratch worktree from #239's head (`19e7a32`; the second pass, `measure_phi_recall.py` and the corpus live there, not on `main`). Network is used **only** by the measurer to fetch candidate weights into a scratch directory outside the repo; nothing under `src/` changes and no product path fetches anything.

1. **Freeze the corpora before the first candidate runs** (recurring-failures mode 1): record `sha256sum` of every corpus file in the evidence file before any number is taken; no corpus file changes after that.
   - **R1** = `corpus_v1.json` as on `19e7a32`.
   - **R2** = new `corpus_v2.json` ("realistic shapes"), written by a **separate agent session that has not read `phi_second_pass.py`, any candidate's label set or R1's results** (the `held_out_*.json` author pattern): at least 20 items each for name, geographic and age_over_89, at least 5 for every other category; shapes that today's rules miss by design (#239 L0 residual-risk list: lowercase and ALL-CAPS names, bare first names with no cue, a name inside a patient's question, a bare 5-digit ZIP, a bare city or county, "she is 95", "ninety-three years old", "age 101"); every identifier invented; one `canary: true` item per category.
   - **G** (false-drop set) = all `must_allow` texts of the four `prohibited_patterns` files (546) plus the served answers in `legacy_eval/golden/answer-*.json` plus the 10 Title Case answers from #239's review (copied verbatim from the PR comment into the scratch set). Any G item a candidate flags is read by the measurer: if it really holds an identifier, it is listed as a G defect and left out of the rate (never silently).
   - **R3** (optional, only if the owner picks the sealed option in DON-NER-MODEL): the owner's sealed corpus, never seen by an agent (below).
2. **Configurations per candidate:** C0 = #239's second pass as is (must reproduce the park numbers on R1, or the measurement is wrong and stops); C1 = C0 ∪ candidate; C2 = C0 without the bare Title Case pair alternative ∪ candidate (tests whether the model can replace the rule that over-drops). Order as `collect()` runs it: strict redaction (called, `RedactionEngine(policy_level="strict").redact`), then the detectors on the strict output; a record is caught if strict removed the planted string or any detector flags it.
   - Model hit → Safe Harbor category: `PATIENT`/`STAFF`/`PER`/`person` → name; `LOC`/`location`/`address` → geographic; `AGE` with a number ≥ 90 or a spelled number ≥ ninety → age_over_89 (any `AGE` span counts as a hit in a second column, so the cost of dropping every age is visible); `DATE`/`ID`/`PHONE`/`EMAIL` → their categories; a confidence threshold of 0.5 for every candidate (fixed before the run, never tuned per corpus).
3. **Measure and paste** into `docs/reviews/<run date>/don-ner-measure.md` (new evidence file): per candidate × configuration × corpus, the per-category table (`n`, strict, detector, union, union %), canaries caught, DON-RECALL MET / NOT MET; false-drop count and rate on G; CPU latency p50/p95 per record over G (and GPU if used); peak RSS; on-disk size; cold load time with `HF_HUB_OFFLINE=1` and `local_files_only=True` and the network blocked (`unshare -n` or a socket-blocking shim, as `test_embedding_no_network.py` does); whether `trust_remote_code` or pickle loading is needed; Python 3.11 + `transformers 5.20.1` import and load clean; licence of weights and training data as the card states it. Commands and outputs are pasted, not paraphrased. Scratch scripts are pasted in the evidence file, not committed.
4. **Never tune to fit:** no threshold, label map, corpus item or C0 rule is changed after the first number is taken; a candidate that misses stays a miss in the table.
5. **Output:** the evidence file plus a short "Answer for DON-NER-MODEL" block: the best configuration (highest minimum per-category union recall on R1 ∪ R2, then lowest false-drop rate), whether it meets DON-RECALL, and its cost (size, latency, new dependency).

**Files:** `docs/reviews/<run date>/don-ner-measure.md` (new), `docs/INDEX.md`, `docs/_link_graph.json`. No product file; `corpus_v2.json` is committed later on #239 (PR-2 resume), not here. **Est:** 3 h. **Runtime:** claude on the GPU box (L0 or a build-item agent with network for the fetch only). **Never beside** another model-host measurement (KV-PREFIX-MEASURE); it does not run pytest.
**Acceptance:** the evidence file holds the corpus sha256 lines taken before the first result; C0 on R1 reproduces name 10/14, geographic 6/8, age_over_89 8/10 (or the row stops and reports why); one table per candidate × configuration; the false-drop rate on G; `git diff --name-only origin/main...HEAD` lists only the three files; `python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py --link-graph && python3 scripts/docs_lint.py` clean.

### New owner gate DON-NER-MODEL (asked after DON-NER-MEASURE, with its table)

Execution gate for the PR-2 resume. Draft wording, plain language (the bracketed numbers are filled from the evidence file; no option is recommended until the numbers exist, then the planner's recommendation goes on the option the evidence supports):

> "Donation is still off. We measured local (on-device) name-and-place detectors on the old test set, a new set written by a separate agent, and 546 ordinary answers that must not be dropped. The best one, [model], catches [x%] names, [y%] places and [z%] ages over 89 (target 95% each) and wrongly drops [n] of 546 good answers. It adds a [size] download that is checked once and never fetched at runtime[, plus a new package: name]. Which way?"

| Option (≤ 5 words) | Description |
|---|---|
| **Adopt [model], agent sets** | Bundle the model like the embedding model; PR-2 resumes and must reach 95% on the agent-written sets. Donation turns on only after that and DON-COPY-V3. |
| **Adopt [model] + sealed set** | As above, plus you write a small sealed test set yourself (as S5 is for the judge); it must also reach 95%, and agents see only the counts. |
| **Adopt a different candidate** | You pick another row of the table (for example a smaller model with lower recall). |
| **Keep donation off** | No model is added; #239 stays a draft; DON-COPY-V3 waits with it. |

**Tradeoffs:** agent sets only is faster, but every set so far was written by agents who knew the goal, so 95% may still be optimistic. The sealed set makes 95% mean something, at the cost of your time (roughly 60-100 invented examples). A bigger model catches more but adds download size and seconds per record; a new package adds supply-chain risk. Keeping it off costs nothing and risks nothing, and the feature stays stalled.
**Analogy:** trying shredders on test pages: the store's test pages, plus a few pages you prepared yourself and kept in a drawer, so the shredder could not have been tuned to them.

**Sealed-set mechanics (only under the sealed option):** the owner writes `~/asclexis-sealed/phi_r3.json` outside every worktree in R1's JSON shape, never pastes a line into a chat, and runs `python scripts/measure_phi_recall.py ~/asclexis-sealed/phi_r3.json` from #239's worktree; the script prints counts only (`format_table`, no text). The owner reports `sha256sum`, the table and the exit code. The PR-2 body records those three things and nothing else.

### PR-2 resume delta (after DON-NER-MODEL picks a model; edits #239, not `main`)

Adds to the RSI1-DONATE row's PR-2 file list: `src/backend/modules/phi_second_pass.py` (a model pass beside the rules: detect-only, category only, never the value; a hit drops the record, as today), `src/backend/scripts/download_models.py` (a `phi-ner` subcommand that copies the `cmd_nli` pattern: pinned repo, revision, weights sha256), `src/backend/core/config.py` (one field, `phi_ner_model_path`), `config/.env.example` (one line), `src/backend/tests/fixtures/phi_recall/corpus_v2.json` (the frozen R2, byte-identical to the measured file), `src/backend/tests/test_phi_second_pass.py`; under the C2 configuration, also the removal of the bare Title Case pair alternative in `phi_second_pass.py`. A new pip package (GLiNER or Presidio options) adds `src/backend/requirements.txt` (exact `==` pin) and a licence line in the PR body. `modules/redaction.py` is still called only.

- **Fail closed:** if the model bundle is missing or fails its sha check, `collect()` donates nothing and returns a fixed reason; it never falls back to rules only.
- **Tests (ids after #239's):** HC-DON-025 missing bundle → `collect` stores 0 rows (positive control: the same profile with a fake loaded model stores ≥ 1); HC-DON-026 a fake model hit (`PATIENT` span) drops the record and `detect` returns the category only (no text in the `Hit`); HC-DON-027 loading uses `local_files_only=True` and makes no socket call (socket-blocking fixture); HC-DON-013 (corpus gate) now runs on R1 ∪ R2 and keeps the 95% / 100% bar unchanged.
- **Bar to leave draft:** HC-DON-013 MET on R1 ∪ R2 with the real bundle (pasted), the false-drop rate on G pasted, R3 counts pasted under the sealed option, the RunLog-isolation test above (Delta 2026-10-20, second) green, and DON-COPY-V3 merged. Otherwise #239 stays a draft and the table goes to the owner (non-negotiable 7).

### DON-COPY-V3 build (new queue row), and why it is ordered with the detector

**Order (planner ruling):** DON-COPY-V3 is built **after DON-NER-MODEL is answered with an "Adopt" option** and must **merge before #239 leaves draft**; it is not built now. Reasons: (1) collection must never start under v2 consent, which does not disclose agent answers (RRSI-OQ-25, `owner-decisions-2026-09-27.md:346`), so v3 is a hard precondition of PR-2; (2) a copy bump forces every patient who agreed to re-agree (`api/donation.py:77`), and while nothing is collected a re-consent buys the patient nothing; if the owner answers "Keep donation off", no one is asked to re-agree for nothing; (3) building it as its own small PR on `main` (not inside #239) keeps one item per PR and leaves #239 to pick up the new constant when it merges `origin/main`. Under "Keep donation off", the row is parked with #239.

**Exact v3 copy** (`src/frontend/src/components/settings/DataDonationCard.tsx`): `CONSENT_TEXT_VERSION = '<build date YYYY-MM-DD>-v3'` (the date the PR is built, for example `2026-10-23-v3`; matches `^[A-Za-z0-9_.\-]+$`, `api/donation.py:59`). `CONSENT_INTRO` gains one paragraph, verbatim from the owner's option text, placed **last in the intro, directly above the three purpose switches** whose descriptions begin "For chat answers…" (placement is the planner's call; the owner fixed the words, not the position):

```
'Nothing here is medical advice. Donated copies only help improve this app.',
'This includes answers from the step-by-step assistant.',
```

Nothing else in the intro or in `PURPOSE_COPY` changes.

**Files:** `src/frontend/src/components/settings/DataDonationCard.tsx` (`CONSENT_TEXT_VERSION` and the one new `CONSENT_INTRO` line only); `src/backend/api/donation.py` (`CURRENT_CONSENT_TEXT_VERSION` `:34` only; if #239 has merged first, the constant lives at `src/backend/modules/data_donation.py:27` and that line is edited instead, nowhere else); `src/frontend/src/__tests__/DataDonationCard.test.tsx` (HC-DON-FE-010 pin updated to the v3 text and version; new HC-DON-FE-011); `src/backend/tests/test_donation_routes_http.py` (new HC-DON-023, 024 only; `VERSION = CURRENT_CONSENT_TEXT_VERSION` at `:35` already follows the constant); slots.
**Tests (test-first):**
- HC-DON-FE-010 (rev): the v3 copy and version are pinned exactly; RED on `main` (the pin reads v2).
- HC-DON-FE-011: `CONSENT_INTRO` contains `This includes answers from the step-by-step assistant.` exactly once and the card renders it.
- HC-DON-023 (`route_client`): a profile with an active `fine_tune` row on `2026-10-20-v2` → `GET /donation/consents` reports `granted: true, current: false` after the bump; the PUT with the v2 version is refused (`:163`), the PUT with v3 makes it `current: true` (positive control).
- HC-DON-024: the frontend and backend constants are equal (read `DataDonationCard.tsx` text with a regex, compare to `CURRENT_CONSENT_TEXT_VERSION`); a scratch mutant that bumps only one side fails it (pasted).
- When #239 merges `origin/main` afterwards, its own `collect` test of a v2 grant must collect 0 rows (Delta 2026-10-20, second, already specifies it).
**PR body:** says in one line that every existing grant becomes not current and patients must agree again before anything is collected; screenshot of the rendered card (Windows, or recorded as skipped). **Owner gates:** DON-COPY-V3 answered (a) (`:380`): the words are approved; no further copy gate unless a word changes. **Est:** 1 h. **Runtime:** claude.

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

- **HC-DON-017:** with a canary whose secret survives (forced by a patched detector in the test), `leak_check` fails and `build_manifest` raises. **Superseded by [Delta 2026-10-20](#delta-2026-10-20-planner-answered-gates-pr-2-file-list-pr-3-leak-rule) (DON-CANARY (b)).**
- **HC-DON-018:** a stored row containing the profile's display name fails `leak_check`. **Superseded by [Delta 2026-10-20](#delta-2026-10-20-planner-answered-gates-pr-2-file-list-pr-3-leak-rule) (DON-CANARY (b)).**
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

All answered 2026-10-19 (`owner-decisions-2026-09-27.md:278-290`); the answers and their effect are in [Delta 2026-10-20](#delta-2026-10-20-planner-answered-gates-pr-2-file-list-pr-3-leak-rule). The questions stay below as asked.

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
