# API Endpoints

**Last Updated:** 2026-07-29
**Owner:** Platform maintainers
**Refresh Trigger:** Mounted backend route added, removed, renamed, or auth requirement changed
**Status:** Source of truth for the live mounted backend API

All routes are mounted under `/api/v1` unless a section explicitly says otherwise.
Auth-required endpoints need `Authorization: Bearer <token>`.
`/health` is mounted at the app root and is intentionally public.

## Profiles

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/profiles/` | No | List available profiles |
| POST | `/profiles/` | No | Create a profile and return a session token |
| POST | `/profiles/login` | No | Log in to a profile |
| GET | `/profiles/me` | Yes | Get the current authenticated profile |
| POST | `/profiles/logout` | Yes | Log out the current session |
| GET | `/profiles/{profile_id}` | Yes | Get profile details |
| POST | `/profiles/{profile_id}/lock` | Yes | Lock a profile and revoke the current session |
| POST | `/profiles/{profile_id}/unlock` | No | Unlock a profile with password and return a session token |
| POST | `/profiles/{profile_id}/change-password` | Yes | Change the profile password |
| POST | `/profiles/{profile_id}/recovery-code` | Yes | Generate or replace this profile's recovery code (SEC-RECOV-001). Requires the current password in the body; seals a **second copy of the same DEK** under a code-derived key, so the code is shown exactly once and cannot be re-read |
| POST | `/profiles/{profile_id}/recover` | No | Unlock with the recovery code and set a new password. Unauthenticated by necessity — the caller has lost the password. Rate-limited on a stricter limiter than login (each attempt runs a 600k-iteration PBKDF2), and returns a **rotated** recovery code, since the old one has now been used |
| DELETE | `/profiles/{profile_id}` | Yes | Irreversibly delete a profile (PROF-DEL-001). Requires password re-auth, an exact confirmation phrase, and `export_acknowledged`. Ordered crypto-erase: sealed keys first (the commit point), then the vault sweep, then the profile's backups, then one master transaction that purges the audit rows, deletes the profile and `backup_schedules` rows, and writes an anonymized tombstone |
| POST | `/profiles/test/reset` | Yes | Reset test data outside production |

## Documents

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/documents/import` | Yes | Import a PDF/image document, or a `.csv`/`.json` (FHIR R4 `Bundle`) structured file (HC-M23) — structured imports skip OCR/classification and land observations and medication/diagnosis mentions as **unverified** rows via a dedicated parser pipeline; response includes an `import_summary` for structured imports |
| GET | `/documents/` | Yes | List documents with optional status/type filters |
| GET | `/documents/{document_id}` | Yes | Get document metadata |
| POST | `/documents/{document_id}/reprocess` | Yes | Retry extraction/OCR and rebuild observations/chunks — also backfills collected_at for documents affected by earlier date-extraction gaps; rejected with 400 for `lab_csv`/`fhir_bundle` documents (delete and re-import instead) |
| POST | `/documents/{document_id}/verify` | Yes | Mark all observations for a document as verified |
| GET | `/documents/{document_id}/category` | Yes | Get the classified document category |
| GET | `/documents/{document_id}/entities` | Yes | Get extracted document entities |
| PATCH | `/documents/{document_id}/entities/{entity_id}/verification` | Yes | Set an extracted entity's user verification state (`verified`: true/false/null) |
| GET | `/documents/highlights/summary` | Yes | Per-document smart-highlight type counts for the most recently imported documents (HC-M16), derived on read |
| GET | `/documents/{document_id}/highlights` | Yes | Get derived smart highlights for one document (HC-M16), derived on read |
| GET | `/documents/{document_id}/pages` | Yes | Get page text/provenance data |
| GET | `/documents/{document_id}/pages/{page_number}/image` | Yes | Render a document page as PNG |
| DELETE | `/documents/{document_id}` | Yes | Delete a document and associated data |

## Observations

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/observations/` | Yes | List observations with filters |
| GET | `/observations/{observation_id}` | Yes | Get observation details |
| POST | `/observations/{observation_id}/verify` | Yes | Verify or edit an observation |
| GET | `/observations/trends/{analyte}` | Yes | Get analyte trend data |
| GET | `/observations/panels/{panel_id}` | Yes | Get grouped panel data |
| GET | `/observations/panels/{panel_id}/snapshots` | Yes | Get panel snapshots grouped by document and collection day |

## Interpretations

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/interpretations/observations/{observation_id}/interpret` | Yes | Generate an observation interpretation |
| POST | `/interpretations/observations/{observation_id}/interpret-grounded` | Yes | Generate an interpretation plus grounded RAG explanation |
| GET | `/interpretations/observations/{observation_id}/interpretation` | Yes | Get a stored observation interpretation |
| POST | `/interpretations/panels/{panel_name}/interpret` | Yes | Generate a panel interpretation |
| GET | `/interpretations/recent` | Yes | List recent interpretations |
| GET | `/interpretations/knowledge/biomarker/{analyte_canonical}` | Yes | Get biomarker knowledge content |
| POST | `/interpretations/batch` | Yes | Generate interpretations in batch |

## Assistant

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/assistant/chat` | Yes | Chat with the grounded assistant — when the agent graph is enabled, routes bounded read-only queries (open follow-up tasks, medication changes, timeline/"what changed") to dedicated agent tools (HC-M24), with deterministic no-LLM fallbacks for the same intents |
| GET | `/assistant/test-intent/{analyte}` | Yes | Test intent lookup for an analyte |
| GET | `/assistant/glossary/{term}` | Yes | Glossary lookup |
| GET | `/assistant/verification-status` | Yes | Get assistant verification component status |
| GET | `/assistant/sessions` | Yes | List chat sessions for the profile |
| POST | `/assistant/sessions` | Yes | Create a new chat session |
| GET | `/assistant/sessions/{session_id}` | Yes | Get a session's message history |
| DELETE | `/assistant/sessions/{session_id}` | Yes | Delete a chat session |
| GET | `/assistant/memory-settings` | Yes | Get the per-profile RAG memory toggle |
| PATCH | `/assistant/memory-settings` | Yes | Update the per-profile RAG memory toggle |

## Feedback

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/feedback/turns/{turn_id}` | Yes | Upsert rating/correction feedback for an assistant turn |
| GET | `/feedback/stats` | Yes | Get aggregate feedback stats for the profile |
| POST | `/feedback/export` | Yes | Export redacted DPO/GRPO/SFT preference datasets (requires `confirmed=true`) |

## Memory

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/memory/` | Yes | Create a memory item |
| GET | `/memory/` | Yes | List memory items |
| GET | `/memory/{item_id}` | Yes | Get a memory item |
| PUT | `/memory/{item_id}` | Yes | Update a memory item |
| DELETE | `/memory/{item_id}` | Yes | Delete a memory item |

## Medications

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/medications/` | Yes | Create a medication |
| GET | `/medications/` | Yes | List medications |
| GET | `/medications/{medication_id}` | Yes | Get medication details |
| PATCH | `/medications/{medication_id}` | Yes | Update a medication |
| DELETE | `/medications/{medication_id}` | Yes | Deactivate or hard-delete a medication |
| POST | `/medications/{medication_id}/schedules` | Yes | Create a schedule |
| GET | `/medications/{medication_id}/schedules` | Yes | List schedules |
| PATCH | `/medications/{medication_id}/schedules/{schedule_id}` | Yes | Update a schedule |
| DELETE | `/medications/{medication_id}/schedules/{schedule_id}` | Yes | Delete a schedule |
| POST | `/medications/{medication_id}/doses` | Yes | Log a taken or skipped dose |
| GET | `/medications/{medication_id}/doses` | Yes | List dose history |
| GET | `/medications/{medication_id}/stats` | Yes | Get adherence statistics |
| POST | `/medications/{medication_id}/learn-patterns` | Yes | Run adaptive reminder pattern learning |
| GET | `/medications/{medication_id}/correlations` | Yes | List observations collected during the medication's active window (MED-CORR-001); verified observations only by default (`verified_only=false` to include unverified), optional `analyte` filter, and a count of undated observations excluded |

## Gamification

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/gamification/badges` | Yes | List badges with earned status |
| GET | `/gamification/streaks` | Yes | Get profile-level streak summary |

## Notifications

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/notifications/settings/{medication_id}` | Yes | Get notification settings |
| PATCH | `/notifications/settings/{medication_id}` | Yes | Update notification settings |
| GET | `/notifications/history` | Yes | Get notification history |
| POST | `/notifications/test` | Yes | Send a generic test notification |
| POST | `/notifications/test/{medication_id}` | Yes | Send a medication-specific test notification |
| GET | `/notifications/scheduler/status` | Yes | Get scheduler status |
| POST | `/notifications/{reminder_id}/interaction` | Yes | Record a reminder interaction |

## Export

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/export/doctor-summary` | Yes | Generate a clinician summary |
| GET | `/export/doctor-summary/{summary_id}/download` | Yes | Download a generated summary |
| POST | `/export/questions` | Yes | Generate discussion prompts |
| POST | `/export/visit-prep` | Yes | Generate a visit-prep packet (HC-M18) — requires `confirm=true`; unverified data excluded everywhere, all content redacted (strict policy) |
| GET | `/export/visit-prep/{packet_id}/download` | Yes | Download a generated visit-prep packet as markdown, HTML, or PDF (`format` query param; PDF returns 501 if WeasyPrint is not installed) |
| GET | `/export/csv` | Yes | Export observations as CSV |
| GET | `/export/json` | Yes | Export observations as JSON |
| POST | `/export/fhir` | Yes | Generate a FHIR R4 export `Bundle` (HC-M22) — requires `confirm=true`; verified-only observations/entities, all free text redacted (strict policy) before storage |
| GET | `/export/fhir/{export_id}/download` | Yes | Download a previously generated FHIR R4 `Bundle` as `application/fhir+json` |

## Backup and Restore

Backups (BKUP-UX-001) are the full-fidelity, restorable copy of a profile, and
are the one export-shaped path that is **deliberately not redacted** — a
redacted backup cannot be restored. Every route below is scoped to the calling
session's profile; `backup_id` is treated as hostile and path traversal is
refused. Backups are stored under `<app_data>/backups/<profile_id>` and are
deleted along with the profile.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/backup/` | Yes | List this profile's backups, newest first |
| POST | `/backup/` | Yes | Create a backup of this profile now — vault DB, encrypted documents and the sealed key files, with a SHA-256 manifest |
| POST | `/backup/{backup_id}/verify` | Yes | Re-check a backup's files against the SHA-256s in its manifest |
| GET | `/backup/{backup_id}/download` | Yes | Stream the backup as a zip so it can leave the device; built in memory, so no second plaintext copy is written to disk |
| POST | `/backup/{backup_id}/restore` | Yes | **Overwrites live data.** Requires password re-auth *and* an exact confirmation phrase, and refuses a backup that fails verification. Profile-scoped: vault and keys are restored verbatim, but only this profile's row is re-applied from the backed-up master DB, so other profiles and the live audit trail are untouched (BK-01) |
| POST | `/backup/prune` | Yes | Delete this profile's backups older than `retention_days`. **`0` means never prune**, matching the scheduler and the Settings UI (BK-03) |
| GET | `/backup/schedule` | Yes | Get this profile's backup schedule (frequency, retention, last run and outcome) |
| PUT | `/backup/schedule` | Yes | Set frequency (`off`/`daily`/`weekly`) and retention. The schedule row lives in the **master** DB, not the vault, because the scheduler must know a backup is due while the profile is locked — so it carries ids, enums, counts and timestamps only |

A successful restore ends the session: the server drops the in-memory key
before overwriting, so the caller is authenticated against keys that no longer
exist and every subsequent profile-data call would 403. Clients should clear
auth and send the user back to sign in with the password that was in use when
the backup was made.

## Care Tasks

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/care-tasks/` | Yes | List persisted care-plan tasks, optionally filtered by `status` |
| GET | `/care-tasks/candidates` | Yes | Derive task candidates for a document (computed on read, not persisted) |
| POST | `/care-tasks/accept` | Yes | Persist a task from a candidate — the only way a task is created |
| PATCH | `/care-tasks/{task_id}` | Yes | Update a task's status (`open`/`done`/`ignored`/`needs_review`) or user note |

## Timeline

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/timeline/` | Yes | Chronological view of the profile's health record (lab observations, classified documents, medication starts/stops), derived on read; supports `event_type`/`date_from`/`date_to` filters |

## Medication Reconciliation

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/med-reconciliation/` | Yes | Compare a document's medication mentions against the medication list (`doc_id` query param); read-only, computed on read — never applies changes to the medication list |

## Pinboards

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/pinboards/` | Yes | Create a pinboard |
| GET | `/pinboards/` | Yes | List pinboards |
| PATCH | `/pinboards/{pinboard_id}` | Yes | Rename a pinboard |
| DELETE | `/pinboards/{pinboard_id}` | Yes | Delete a pinboard |
| POST | `/pinboards/{pinboard_id}/items` | Yes | Add an item to a pinboard |
| GET | `/pinboards/{pinboard_id}/items` | Yes | List items on a pinboard |
| DELETE | `/pinboards/{pinboard_id}/items/{item_id}` | Yes | Remove an item from a pinboard |
| POST | `/pinboards/{pinboard_id}/export` | Yes | Generate a visit-prep packet scoped to a pinboard's items — requires `confirm=true` |

## Search

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/search/` | Yes | Bounded local search over documents, extracted entities, and observations (HC-M21); `q` required, with optional `provider`/`date_from`/`date_to`/`category`/`highlight_type`/`limit` filters |

## Model Settings

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/settings/model` | Yes | Get model settings and hardware summary |
| GET | `/settings/model/provider` | Yes | Get the active LLM provider and its capability flags |
| PUT | `/settings/model/provider` | Yes | Switch the active LLM provider/model at runtime; Ollama provider URL must remain localhost |
| POST | `/settings/model/detect` | Yes | Run hardware detection |
| POST | `/settings/model/tier` | Yes | Set preferred model tier |
| GET | `/settings/model/tiers` | Yes | List tier availability |
| GET | `/settings/model/download-progress` | Yes | Get model download progress |
| POST | `/settings/model/download` | Yes | Start a model download |
| GET | `/settings/model/external-api` | Yes | Get external API settings |
| PUT | `/settings/model/external-api` | Yes | Save external API settings |
| GET | `/settings/model/timezone` | Yes | Get the profile timezone |
| PUT | `/settings/model/timezone` | Yes | Set the profile timezone |
| GET | `/settings/model/voice` | Yes | Get voice logging preferences |
| PATCH | `/settings/model/voice` | Yes | Update voice logging preferences |
| GET | `/settings/model/diagnostics` | Yes | Get local OCR/model/SQLCipher/GPU diagnostics |
| POST | `/settings/model/diagnostics/recheck` | Yes | Re-run environment diagnostics |
| PATCH | `/settings/model/ocr` | Yes | Update per-profile OCR preference |
| PATCH | `/settings/model/agent` | Yes | Per-profile toggle for the Agent Overhaul cutover (S5-1) — when enabled (default), `/assistant/chat` serves via the agent graph, falling back to the legacy retrieval path on error |

## Health and Monitoring

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Public liveness probe |
| GET | `/monitoring/metrics` | Yes | Authenticated metrics dashboard |
