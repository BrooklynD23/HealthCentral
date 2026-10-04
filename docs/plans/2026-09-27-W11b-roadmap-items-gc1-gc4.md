# W-11b Roadmap Items G-C1…G-C4 Implementation Plan

**Last Updated:** 2026-09-27
**Owner:** repository owner
**Refresh Trigger:** P1, P5, P6, P7 or W-2 merges (line numbers and the profile-migration head move); the owner signs any S-line below; `openwiki` is generated; W-8 lands (G-C4 consumes its `EMBEDDING_MODEL_PATH` seam).
**Status:** PROPOSED — not executed. Nothing in this plan is implemented, wired or tested. No group is owner-approved as a whole. G-C2 and parts of G-C4 rest on owner records quoted below. G-C1 and G-C3 have **no owner option text** and are **owner-gated** until S-C1-1 / S-C3-1 are signed.
**Review status:** 4 Codex rounds. The round-4 MAJOR findings were fixed after the last round and have not been re-reviewed. **Owner acceptance is required.**
**Prerequisites:** P0-B and P1 merged to `origin/main`. This plan set (`docs/plans/2026-09-27-W*.md`) must also be committed to `main` through its own owner-approved `docs:` commit. P0-B covers only `audit/`, `docs/capstone-report/` and `docs/INDEX.md`, so the W-plans are not covered by it and are untracked today. Group-specific prerequisites:
- G-C1: P5, W-2, P6, P7 and S-C1-1.
- G-C2: P4 Task 13, the owner's generation run and S-C2-1.
- G-C3a: P4, W-4 and S-C3-1.
- G-C3b: P2 and S-C3-1.
- G-C4: nothing beyond P1; it reads W-8 if W-8 has landed.

If the ancestry check in any Task X.0 fails because P1 has not landed, that is the **intended STOP**, not a defect.

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the four remaining roadmap gaps G-C1…G-C4 as four separately shippable groups:
- **G-C1:** export downloads survive a backend restart.
- **G-C2:** a reviewed OpenWiki generation.
- **G-C3:** a minimal HC-M06 extraction eval card and the HC-M07 observability baseline.
- **G-C4:** a packaging decision record, written before any build.

**Architecture:**
- **G-C1** replaces the three module-level dicts in `api/export.py` with rows in a new per-profile table `export_artifact`. The table lives inside each profile's SQLCipher vault. It holds the payload the download routes already render from, so the crypto-erase vault sweep removes it with no new code.
- **G-C2** is an owner-run generation followed by a scripted diff review.
- **G-C3** reuses the HC-AVS golden-set pattern (`tests/test_visit_note_extraction.py`) for lab PDFs rendered by a stdlib-only PDF writer. It adds a process-wide log-record factory, because a handler `Filter` is wiped by `alembic.ini`'s `fileConfig` (measured below).
- **G-C4** is a decision document with measured inputs. It covers how the installer carries the embedding model (D8 / D8-delivery).

**Tech Stack:** Python 3.11 (D9 venv), FastAPI `TestClient`, SQLAlchemy 2 + aiosqlite, Alembic (profile chain), pdfplumber (already pinned), stdlib `logging`, Playwright (request fixture only), docs lint scripts.

**Spec:** [implementation-program.md](../capstone-report/implementation-program.md) gap table rows G-C1…G-C4; [handoff §5](../../audit/2026-09-25/handoff-2026-09-27-execution.md) row W-11; `feature_list.json` entries HC-M06, HC-M07, HC-M08a.

## Global Constraints

- **Target Python 3.11.** No 3.12-only syntax or APIs. New timestamps use `core.time.utcnow` (naive UTC).
- **Per-profile isolation (C-ISO-1).** Export artifacts are profile data. They are stored only in the profile vault via `ProfileDbSession`, and **never** in the master DB. They are not stored as loose files either, because that would be a new PHI location.
- **Local-first (C-LOCAL-1).** No product code path gains a network call. The OpenWiki run is an owner-run developer tool, not a product path.
- **Redaction before anything leaves (C-REDACT-1).** G-C1 persists exactly the dicts the routes store today. After W-2, the doctor-summary dict is the strict-redacted copy. `modules/redaction.py` is **read-only**.
- **Audit logging (C-AUDIT-1).** Every generate and download route keeps its audit row, with no PHI.
- **Dual migrations (C-MIG-1).** A new profile table gets a new profile migration with a linear `down_revision` equal to the head measured at Task C1.0.
- **Never lower a threshold (C-SAFE-4).** That covers the HC-M06 thresholds once set, the 0.6 faithfulness threshold, and the 0.7 embedding assertion.
- **Ask-first files stay read-only:** `modules/interpret_safety.py`, `modules/redaction.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`, `core/auth.py`, and anything encryption-related (`core/security.py`, `core/profile_database.py`, `core/document_crypto.py`).
- **Route/status tests go through HTTP** using `src/backend/tests/support/routes.py::route_client`. The signature measured at main@40f590e is `route_client(router, prefix, profile_id="profile-a", master_db=None)`. P7 adds `profile_name` and `profile_db`. This plan only passes `profile_id` and `master_db` by keyword, and sets the vault override on `client.app.dependency_overrides`, so it works with either signature.
- **Every `path:line` is labelled with its ref.** Every file cited from `src/backend/{api/export.py, api/pinboards.py, api/profiles.py, api/feedback.py, main.py, monitoring/, security/, modules/extract.py, alembic.ini, migrations/*/env.py}`, plus `openwiki/README.md` and `scripts/docs_lint.py`, is byte-identical on main@40f590e, A@692fdf3 and B@7b2ff1f. This was checked 2026-09-27 with `git diff --stat 40f590e <ref> -- <file>`, which printed nothing. `core/config.py` differs on B by one deleted line, so its lines are labelled B. **The executor re-verifies every line on the post-P1/P5/P6/P7/W-2 start tree** (W-2 and P5 edit `api/export.py`).
- Interpreter for every gate: `~/venvs/asclexis-311/bin/python` (D9), written `$PY`. Worktree root written `$WT`. On the WSL `/mnt/c` mount, clear `__pycache__` before pytest (AGENT.md "Commands").
- **Shell conventions.**
  - Each bash block is self-contained. It sets `set -o pipefail` and defines its own variables.
  - It `cd`s only to absolute paths (`"$WT"`, `"$WT/src/backend"`), never relatively after another `cd`.
  - Shell state does not persist between steps.
- **Baseline sentences (CLAUDE.md §4, AGENT.md "Commands").** The commit that changes the collected count also updates **only the collected count**:
  - the `**N backend tests collected.**` and "if it differs from N" tokens in `CLAUDE.md`;
  - the `(N collected; …)` token in `AGENT.md`.

  Take N from `--collect-only` in that worktree at that commit. A pass-count sentence ("all N pass", "N pass in CI") is changed only with a pass count measured in a named environment (interpreter, plus embedding model present or absent). Otherwise leave it and flag it in the PR. Never write a collected number into a pass-count slot. These two files are otherwise read-only here, except G-C2's one `AGENT.md:20` referrer line. They are shared with every phase (program "Plan overlaps" row 3), so never edit them concurrently with another phase.
- **Break-it protocol.** Nothing is ever edited and then restored with `git checkout --` in the phase worktree. Choose one of three modes:
  - **(a) Read-only files** (for example `modules/extract.py`): an in-process monkeypatch only, never an edit. The exact command is given at the step.
  - **(b) Committed state:** a **disposable detached worktree** made after the step's commit:
    ```bash
    set -o pipefail; WT="${WT:?set WT to the phase worktree first}"; BK="$WT-breakit"
    git -C "$WT" worktree add --detach "$BK" HEAD
    # make the break in $BK, run the named test from "$BK/src/backend", record the red line
    git -C "$WT" worktree remove --force "$BK"
    ```
  - **(c) Files this group creates or owns, before their commit:** `cp F F.breakit-bak`, edit, run, `mv F.breakit-bak F`, then `cmp` against a second copy taken before the edit, or re-run the step's GREEN command. Never `git checkout --`.

  After every break-it, the phase worktree must match its pre-break state. That means `git -C "$WT" diff --stat` is unchanged, and the step's GREEN command is green again.
- **Rollback after a push.** Before merge: `gh pr close <n> --delete-branch`. After merge: `git revert <sha>` on a new branch → PR. Details per group are under [Rollback](#rollback).

## Scope and order

| Group | Kind | Separately shippable as | Blocked on |
|---|---|---|---|
| **G-C1** | PRODUCT | PR `feat(export): persist export artifacts in the profile vault` | P1, P5, **W-2**, P6, **P7**, S-C1-1 |
| **G-C2** | OWNER→PRODUCT | PR `docs: add reviewed OpenWiki generation` | P1, P4 (Task 13), the owner's generation run, S-C2-1 |
| **G-C3a** | PRODUCT | PR `feat(extract): HC-M06 extraction golden set and eval card` | P1, P4 (`evals.md`), W-4 (`evals.md`), S-C3-1 |
| **G-C3b** | PRODUCT | PR `feat(monitoring): HC-M07 correlation IDs in log records and audit payload` | P1, P2 (`main.py`), S-C3-1 |
| **G-C4** | DOCS→OWNER | PR `docs: HC-M08a packaging decision record` | P1; reads W-8 if landed |

**G-C5 (HC-M11 cross-encoder behind a default-off flag) is OUT of scope.** The program makes it depend on "P8 brief 5; P1" (program gap table, G-C5 row). The owner record is "HC-M11 approved behind a default-off flag only | branch A §14 d2 | G-C5; production scoring change still gated" ([owner-decisions-2026-09-27.md](../capstone-report/owner-decisions-2026-09-27.md), "Earlier owner records"). Plan 08 brief 5 governs it. Nothing here touches `faithfulness.py`, `verifier_agent.py` or HC-M11 code. G-C4 only *lists* HC-M11's future cross-encoder weights as a packaging input, and does not license bundling them.

---

## Approval scope

### G-C1: no owner option text

- No owner-decision row names export persistence. The item comes from:
  - program gap row G-C1: "Persist export artifacts across restarts (PRIV-08; audit §16 #7) | P1 | — | A download succeeds after a restart";
  - audit §16 #7, an agent recommendation: "Export-store persistence + audit retention … Urgency Low".
- Both sources are agent-authored. **The whole group is owner-gated on S-C1-1** (go + storage design), unsigned.
- **Is a new PHI location involved?** No, by design: rows live in `vaults/{profile_id}/vault.db`, the same SQLCipher file as the source observations. They are covered by C-ISO-1 and C-KEY-1, and swept by C-KEY-2 step 4.
- **The rejected alternative is a new location.** That alternative is encrypted files under a profile directory. It would add a new PHI-at-rest location and new crypto calls. Neither is covered by any decision.
- **There is no `C-PRIV-*` rule.** `grep -c "C-PRIV" docs/capstone-report/architecture-engineering-contract.md` printed `0` on 2026-09-27. The privacy rules are C-LOCAL-\*, C-ISO-\*, C-KEY-\* and C-REDACT-\*.
- **A code comment argues against this.** `api/profiles.py:799-803` (main@40f590e, = A, B) says: "the export routes stream downloads rather than writing files server-side … Building a second, server-side export path that drops a PHI file somewhere with no delivery channel would be worse than the problem it solves."
  - G-C1 writes vault rows, not files. The rows have a delivery channel (download) and are erased with the vault.
  - After G-C1 the sentence is inaccurate, and it sits in an auth-adjacent shared file. Amending it is S-C1-2, unsigned.

**G-C1 does NOT license:**
1. Storing artifacts in the master DB, in loose files, or anywhere outside the profile vault.
2. A "recent exports" list route or UI. See O-C1-2.
3. A retention/TTL policy or a prune job. See O-C1-3.
4. Any change to what the artifacts contain: redaction scope (W-2 owns it), verified-only filtering (W-3/D4), dates, sections.
5. Edits to `modules/redaction.py`, `core/auth.py`, `core/profile_database.py` or the delete flow in `api/profiles.py`. The one exception is adding `ExportArtifact` to P7's `_SYNTHETIC_RESET_MODELS` tuple.
6. Persisting CSV/JSON exports. They stream today (`api/export.py:904`, `:960`) and stay streamed.
7. Fixing the `rl_exports/` finding (F-1 below). It is reported, not planned.

### G-C2: owner record, verbatim

- Branch A `docs/plans/2026-09-08-backlog-closure-plan.md` §14 row 4 (`692fdf3`, line 405; on main after P1):
  > "| 4 | OpenWiki (§9) | **Owner generates locally; this session reviews the diff** | Leaving the `openwiki/` references in `CLAUDE.md`/`AGENT.md` standing as scheduled intent. Revisit if generation does not happen. |"
- Cited in force by [owner-decisions-2026-09-27.md](../capstone-report/owner-decisions-2026-09-27.md):37: "| OpenWiki: the owner generates it locally | branch A §14 d4 | G-C2 |".

**G-C2 does NOT license:**
1. An agent running `openwiki` or holding the LLM API key.
2. Accepting any tool-made edit to `CLAUDE.md`, `AGENT.md` or a new `AGENTS.md`. Those are governance files, and W-10 owns `CLAUDE.md` amendments. The default is reject (S-C2-2).
3. Adding the OpenWiki CI workflow. `openwiki/README.md` "CI" defers it until one reviewed cycle has merged.
4. Treating generated pages as authority (CLAUDE.md:65-67 "OpenWiki usage").

### G-C3: no owner option text

- The items are ledger entries `feature_list.json` HC-M06 (`:67-77`) and HC-M07 (`:79-90`) (main@40f590e = A = B), both `"status": "pending"`.
- Also in branch A backlog plan §6-§7 (agent plan) and branch B `docs/plans/2026-09-10-implementation-roadmap.md` Phase E "**E1** HC-M06 extraction eval card in C2's format". That file is headed "accepted 2026-09-10"; the approver is not named.
- **Owner-gated on S-C3-1** (go for the minimal scope below), unsigned.

**G-C3 does NOT license:**
1. The optional JSON log formatter (HC-M07 item 2). Its verification steps do not require it, and backlog §6 T3 calls it a "new leak path". See O-C3-3.
2. Changing root log levels or handlers, or making INFO logs visible in production. See F-2 and O-C3-4.
3. Extractor changes to raise a score. The eval measures and does not tune.
4. Real patient documents in the repo. The golden set is synthetic only.
5. Lowering a threshold once it is recorded.

### G-C4: owner records, verbatim

- Audit §21 Q4 ([Devin-Audit-report.md](../../audit/2026-09-25/Devin-Audit-report.md):334): "**Both** — continue product work AND mine it for research. HC-M08 stays on the roadmap."
- D8 ([owner-decisions-2026-09-27.md](../capstone-report/owner-decisions-2026-09-27.md):21): "Ship the small embedding model with the app / installer so no download is ever needed." This was **not** the recommended option.
- **D8-delivery**, 2026-09-27, Claude Code chat. It is recorded verbatim in [W-8 plan](2026-09-27-W08-bundled-embedding-model.md):51, and it is **not yet a row in owner-decisions-2026-09-27.md** (finding F-5):
  > "**Script + offline load**" — "Interim: `src/backend/scripts/download_models.py` fetches it once into a local models dir; runtime loads that path with HF offline and fails closed if absent. Installer bundles it later (G-C4). No weights in git."

**G-C4 does NOT license:**
1. Any packaging build or code: HC-M08b/c/d, a PyInstaller spec, a launcher, `StaticFiles`.
2. Bundling any model other than "the small embedding model". GGUF tiers and a future HC-M11 cross-encoder stay user-triggered downloads unless the owner decides otherwise.
3. Committing model weights to git.
4. Changing `app_data_path`, CORS or the bind host now. The decision record only names what the build phase must change.

---

## Traceability

Every ID below was verified by `grep -n` on 2026-09-27. Lines refer to the untracked package files as they are today.

| ID | Location | Quoted |
|---|---|---|
| W-11 | [handoff](../../audit/2026-09-25/handoff-2026-09-27-execution.md):148 | "\| W-11 \| remaining gaps \| G-B1 …, G-B2 …, G-B4 …, G-C1…C4 per the program table \| per the program \| per the program G-table \| per the program \|" |
| G-C1…G-C5 | [program](../capstone-report/implementation-program.md):398-402 | the gap-table rows quoted in Approval scope |
| **G-C1** | | |
| PRIV-08 | [matrix](../capstone-report/specs-compliance-matrix.md):91 | "Export artifacts survive a restart \| audit §11 P1-3 \| module-level dicts in `api/export.py` (REPORTED) \| — \| — \| **unknown** (not re-checked)" |
| ISO-01 | matrix:49 | "Profile data only via `ProfileDbSession`, never master `get_db()`" |
| KEY-04 | matrix:61 | "Delete is an ordered crypto-erase" |
| MIG-01 / MIG-04 | matrix:116, :119 | "Dual Alembic chains, linear" / "Test reset wipes every profile table" |
| PRIV-04 | matrix:87 | W-2's row. G-C1 persists W-2's redacted copy |
| C-ISO-1, C-ISO-2 | [contract](../capstone-report/architecture-engineering-contract.md):60, :68 | ProfileDbSession only; route tests through HTTP |
| C-KEY-1, C-KEY-2 | contract:77, :88 | vault encryption; the ordered crypto-erase ("4. sweep the vault") |
| C-REDACT-1 | contract:177 | redaction before exportable files |
| C-AUDIT-1 | contract:323 | audit row on every route touching profile data |
| C-MIG-1 | contract:250 | new profile table ⇒ profile migration, linear, model = DDL |
| C-TIME-1 | contract:233 | `core.time.utcnow` |
| **G-C2** | | |
| GATE-01 | matrix:135 | docs lint and index freshness |
| C-GATE-4 | contract:367 | docs changes pass `docs_lint.py` |
| **G-C3a** (HC-M06) | | |
| PROD-01 | matrix:125 | "Import → extract → verify → trends" (extraction is part of it) |
| SAFE-07, C-SAFE-4 | matrix:76, contract:158 | thresholds never lowered |
| GATE-10 | matrix:144 | the feature ledger is linted |
| **G-C3b** (HC-M07) | | |
| PRIV-06, C-REDACT-3 | matrix:89, contract:196 | no PHI in logs or audit rows |
| AUD-04 | matrix:108 | "audit helpers also log each row at INFO". F-2 shows those INFO lines are dropped after startup |
| GATE-06 | matrix:140 | E2E critical flows |
| C-LOCAL-1 | contract:25 | no telemetry, no network |
| **G-C4** (HC-M08a) | | |
| PROD-03 | matrix:127 | "Desktop app \| … HC-M08 \| none \| … **gap** \| owner: 'Both' (§21 Q4); spike first" |
| LOCAL-03, C-LOCAL-2 | matrix:41, contract:44 | local-only embedding load (D8) |
| LOCAL-05, C-LOCAL-3 | matrix:43, contract:51 | bind 127.0.0.1 + localhost CORS |
| KEY-01, C-KEY-1 | matrix:58, contract:77 | SQLCipher + DPAPI sealing (portability) |

---

## Files

### G-C1

**Create**
- `src/backend/models/export_artifact.py`: the `ExportArtifact` model plus `EXPORT_ARTIFACT_KINDS`.
- `src/backend/migrations/profile/versions/014_export_artifacts.py`. The number is `NNN` = head + 1, measured at Task C1.0 (expected head `013_fk_cascade_alignment`, from P6).
- `src/backend/tests/test_export_artifact_persistence.py`: HC-EXPA-001…010, 16 collected items.

**Modify** (anchors are main@40f590e = A = B; W-2 and P5 move them)
- `src/backend/api/export.py`:
  - delete the stores at `:43-50`;
  - add `_save_artifact`/`_load_artifact`;
  - generate routes: store at `:446`, `:799`, `:1227-1230`; add a profile commit after each `audit_and_commit`;
  - download routes: lookups at `:498-511`, `:840-851`, `:1267-1278`; add a `profile_db: ProfileDbSession = None` parameter, appended last.
- `src/backend/api/pinboards.py`: the import at `:13` and the store at `:495`; add a profile commit after the audit at `:496-501`.
- `src/backend/models/__init__.py`: import and `__all__` entry, beside `Pinboard` (`:63`, `:103-105`).
- `src/backend/api/profiles.py`: **only** add `ExportArtifact` to P7's `_SYNTHETIC_RESET_MODELS`. If S-C1-2 is signed, also the one-sentence docstring amendment at `:799-803`.
- `src/backend/tests/test_care_tasks.py`: the two `get_profile_current_revision(...) ==` head literals (`:809`, `:825` main@40f590e; P6 will have changed them to its own head).
- `src/backend/tests/test_visit_prep_packet.py`: the import at `:255-262` and HC-PKT-010, 012, 013, 014, 015, 016. Mechanism only; every assertion kept.
- `src/backend/tests/test_fhir_export.py`: HC-FHIR-102, 103, 104. Mechanism only; every assertion kept.
- `CLAUDE.md`, `AGENT.md`: the collected-count tokens only, in the RED-test commit (Global Constraints, "Baseline sentences").
- This plan file: the execution record.

### G-C2
- **Modify:**
  - `openwiki/**` (generated);
  - `openwiki/README.md` "Status" line only;
  - the referrer lines `docs/00_architecture_plans_index.md:58` and `AGENT.md:20` (main@40f590e; P4 Task 13 edits them first).
- **Read-only:** `CLAUDE.md`, and `AGENTS.md` if created (S-C2-2).

### G-C3a (HC-M06)
- **Create:**
  - `src/backend/tests/support/minimal_pdf.py`;
  - `src/backend/tests/fixtures/extraction_golden/manifest.json`;
  - `src/backend/tests/test_extraction_golden.py` (HC-EXTR-001…003, 5 collected);
  - `docs/agentic/eval-cards/extraction.md`.
- **Modify:** `docs/agentic/evals.md` (append "Concrete evals" item 8); `docs/INDEX.md` and `docs/_link_graph.json` (regenerated); `CLAUDE.md` and `AGENT.md` (collected-count tokens only).

### G-C3b (HC-M07)
- **Create:** `src/backend/core/logging_setup.py`; `src/frontend/e2e/health-smoke.spec.ts`.
- **Modify:**
  - `src/backend/main.py`: one import plus one call at the top of `create_app()` (`:86-88`);
  - `src/backend/security/audit_middleware.py`: one key in `event_data` (`:60-67`);
  - `src/backend/tests/monitoring/test_correlation.py` (HC-OBSV-001, 002, 004);
  - `src/backend/tests/security/test_audit_middleware.py` (HC-OBSV-003);
  - `CLAUDE.md`, `AGENT.md`: collected-count tokens only.

### G-C4
- **Create:** `docs/plans/<execution-date>-packaging-decision.md`. The name comes from `feature_list.json:94` HC-M08a ("docs/plans/<date>-packaging-decision.md").
- **Modify, after S-C4-1 only:** `feature_list.json` HC-M08a `"status"`.

### Read-only for every group (zero diff at the end)
- `modules/redaction.py`, `interpret_safety.py`, `faithfulness.py`, `verifier_agent.py`;
- `core/auth.py`, `core/security.py`, `core/profile_database.py`, `core/migrations.py`;
- `migrations/*/env.py`, `alembic.ini`;
- `tests/support/routes.py` (P7 → G-B1 own it);
- `CLAUDE.md` and `AGENT.md`, except the collected-count tokens and G-C2's `AGENT.md:20` referrer;
- `docs/capstone-report/*`, `audit/**`.

### Shared-file ordering

| File | Order | Evidence |
|---|---|---|
| `api/export.py` | P5 → W-2 → **G-C1** | W-2 plan `:92` "`api/export.py` \| **W-2** → G-C1 \| … It should persist already-redacted summaries. Never concurrent" |
| `api/profiles.py` | P5 → P7 → {G-B1, **G-C1**}; never concurrent | program `:137` "`api/profiles.py`: P5 → P7 → {W-11a PR-1, G-C1}" (W-11a PR-1 = G-B1). G-C1 edits only P7's tuple |
| `migrations/profile/versions/` | P6 (`013`) → **G-C1** (`014`) | plan 06 Task 2 creates `013_fk_cascade_alignment` with `down_revision = "012_pinboards"` |
| `tests/test_care_tasks.py` head literal | P6 → **G-C1** | the literal pins the head at `:809`, `:825`. Plan 06 does not mention it (finding F-4) |
| `tests/test_visit_prep_packet.py`, `tests/test_fhir_export.py` | P5, W-2 → **G-C1** | W-2 plan lists both as neighbours; plan 05 only runs `test_fhir_export.py` (`05:338`; the file already uses `core.time.utcnow`), it does not edit it (3a m-4) |
| `docs/agentic/evals.md` | P4 → W-4 → **G-C3a** | plan 04 Task 1 (`:55`); W-4 plan `:149` |
| `main.py` | P2 → **G-C3b** | P2 edits the lifespan (`:66-81`). W-4 and W-7 do not edit `main.py` (3a m-2). G-C3b edits only `create_app()` |
| `feature_list.json` | **G-C4** only (status flip) | W-1 only reads it (W-1 `:671`); P08 forbids editing it (P08 "Does NOT license" #7, `:84`) (3a m-3) |
| `CLAUDE.md` / `AGENT.md` baseline tokens | serial across every phase that changes collection (P1, P2, P5, P6, P7, W-*, **G-C1/C3a/C3b**) | program "Plan overlaps" row 3: "Each phase writes its own measured count; never edit concurrently" |
| `AGENT.md:20`, `docs/00_architecture_plans_index.md:58` | P4 Task 13 → **G-C2** | plan 04 `:576-607` rewrites them to "not-yet-generated stub" |
| `docs/INDEX.md`, `docs/_link_graph.json` | whichever lands last regenerates on a clean tree | program "Plan overlaps" row 4 |

## Dependencies

| Needs | Groups | Check (in each Task X.0) |
|---|---|---|
| P1 (A + B on main) | all | `git merge-base --is-ancestor 7b2ff1f HEAD && git merge-base --is-ancestor 692fdf3 HEAD && echo post-P1-ok` |
| D9 venv | C1, C3a, C3b (C2 and C4 for the collected count) | `$PY --version` → `Python 3.11.x` |
| P5 | C1 | `grep -c "datetime.utcnow" src/backend/api/export.py src/backend/modules/export.py` → `0` for both |
| W-2 | C1 | `grep -n "redact_summary_data" src/backend/api/export.py` → at least 1 hit |
| P6 | C1 | the profile head file exists (Task C1.0 records it) |
| P7 | C1 | `grep -n "_SYNTHETIC_RESET_MODELS" src/backend/api/profiles.py` → at least 1; `grep -rln "hc_reset_010" src/backend/tests` → 1 file |
| P4 Task 13 | C2, C3a | `grep -n "openwiki" docs/00_architecture_plans_index.md AGENT.md` shows P4's stub wording |
| W-4 | C3a | `git log --oneline -1 -- docs/agentic/evals.md` shows W-4's commit, or the orchestrator confirms W-4 is not in flight |
| P2 | C3b | `grep -n "notification_scheduler" src/backend/main.py` → at least 1 (P2 landed) |
| W-8 (optional) | C4 | `grep -n "embedding_model_path" src/backend/core/config.py`. If absent, the decision record cites W-8 as *proposed* |
| D8, D8-delivery | C4 | quoted above |
| Owner go | C1: S-C1-1; C2: S-C2-1; C3a/C3b: S-C3-1 | the sign-off line carries a name and date; otherwise **STOP** |

---

## Measured before writing (context, not targets)

All runs below used Windows Python 3.13.7 (`/mnt/c/Python313/python.exe`, FastAPI 0.141.1, SQLAlchemy 2.0.44, pytest 9.1.1) on main@40f590e, with a dirty working tree. The code came from `src/backend`. Prototypes lived only in the session scratchpad. **This is not the D9 venv; the executor re-measures.**

1. **PRIV-08 verified.** Its status moves from `unknown` to confirmed `gap`. The prototype generated each artifact over HTTP through `route_client`, with a file-backed aiosqlite vault (`NullPool`) and seeded `Document` + `Observation` rows. It downloaded the artifact (200), cleared `_summary_store`/`_packet_store`/`_fhir_store` to model a restart, rebuilt the client, and downloaded again:
   ```
   E       AssertionError: {"detail":"Summary not found"}
   E       assert 404 == 200
   E       AssertionError: {"detail":"Visit-prep packet not found"}
   E       assert 404 == 200
   E       AssertionError: {"detail":"FHIR export not found"}
   E       assert 404 == 200
   3 failed, 20 warnings in 3.74s
   ```
   A third store user exists: `api/pinboards.py:13` imports the private `_packet_store` and writes it at `:495`. Neither branch touches `api/export.py` or `api/pinboards.py`. `git diff --stat 40f590e 692fdf3|7b2ff1f -- src/backend/api/export.py src/backend/api/pinboards.py` printed nothing. Branch A's `api/documents.py` diff contains no `store`/`export` hunk (`git diff 40f590e 692fdf3 -- src/backend/api/documents.py | grep -i "store\|export"` printed nothing).
2. **Direct-call tests depend on the dicts.** `tests/test_visit_prep_packet.py:259` imports `_packet_store`, and HC-PKT-010 asserts `response.packet_id in _packet_store`. HC-PKT-012…016 download without a vault. `tests/test_fhir_export.py:517-559` writes `_fhir_store` directly (HC-FHIR-102…104). **9 tests must change mechanism.** Removing the dicts breaks collection of `test_visit_prep_packet.py` at import.
3. **The vault sweep covers the vault DB.** `api/profiles.py` step 4 runs `shutil.rmtree(manager.get_profile_vault_path(profile_id))`, and that path is `app_data/vaults/{profile_id}` (`core/profile_database.py:179-181`). `vault.db` lives at `:134` inside it. A table in the vault is erased with no delete-flow change.
4. **Reset-coverage coupling.** P7 adds HC-RESET-010, which pins `_SYNTHETIC_RESET_MODELS` to `ProfileDatabaseBase.metadata` (plan 07 `:14`, `:292`). Any new profile table fails CI until it is added to the tuple.
5. **Minimal-PDF feasibility (G-C3a).** A 40-line stdlib PDF writer (Helvetica Type 1, `Tj`/`T*` operators) fed through the real `pdfplumber` and `ExtractModule.extract_from_pdf` reproduced every line exactly. Page 1 of the probe gave `'Page 1 of 2\nSpecimen Collected: 05-Feb-2024\nWBC 6.2 K/uL (4.0-11.0)\n…'`. Per-page collection dates propagated (`2024-02-05` on page 1, `2024-03-05` on page 2). The collection label beat the "Reported" date (`dates ['2024-03-15', '2024-03-20']`).
6. **Prototype golden set** (8 documents / 28 expected rows, the Task C3a.1 manifest):
   ```
   analyte {'tp': 26, 'fp': 0, 'fn': 2} P=1.00 R=0.93
   unit {'tp': 26, 'fp': 0, 'fn': 2} P=1.00 R=0.93
   date {'tp': 26, 'fp': 0, 'fn': 2} P=1.00 R=0.93
   lab_06 analyte missing {('iron',): 1, ('tsh',): 1}
   ```
   `Iron 60 ug/dL` and `TSH 2.1 mIU/L` are dropped **whole**, because their units are outside the hard-coded unit list (`modules/extract.py:74-77`). That is a real, silent extraction miss (finding F-3).
7. **Handler filters do not survive startup (G-C3b).** `alembic.ini` `[logger_root] level = WARN, handlers = console` is applied by `fileConfig` at master startup (`migrations/master/env.py:38`) and at **every vault open** (`migrations/profile/env.py:53`, reached from `core/profile_database.py:367`). Measured:
   ```
   before 20 [('StreamHandler', 1)]
   after WARNING [('StreamHandler', 0)]
   app INFO enabled: False
   ```
   Consequences:
   - A `logging.Filter` placed on root handlers is discarded at the first login.
   - The `SECURITY_AUDIT` INFO line (`security/audit_middleware.py:75-78`) is not emitted at all once any migration has run in-process. This is inferred from the measured root level; no product code configures another handler (`grep basicConfig|dictConfig` in product code: only scripts and the migration `env.py` files).
8. **Packaging inputs (G-C4).**
   - `app_data_path` returns `Path("data")` relative to the **working directory** in local mode (`core/config.py:159-163` B@7b2ff1f).
   - Four product paths resolve relative to source files: `api/feedback.py:66`, `core/migrations.py:31,46`, `modules/model_integrity.py:42`. The last one reaches the repo-root `config/model_manifest.json`.
   - The local-mode CORS list is hard-coded to `http://localhost:3000` and `http://127.0.0.1:3000` (`main.py:101`).
   - There is no `StaticFiles` mount (`architecture-overview.md:21`).
   - The embedding model is 11 files, 91,578,415 bytes, revision `1110a243…`, per W-8 (`:34`, `:103`, measured there).

## Findings outside this plan's scope (reported, not planned)

- **F-1 · RL exports escape the crypto-erase and git-ignore** (security; severity: redacted data).
  - `POST /feedback/export` writes `rl_exports/profile_<id>/` under `src/backend/rl_exports` by default (`api/feedback.py:64-67,331-341`).
  - `api/profiles.py` contains no `rl_exports` reference on main, A or B (`git show <ref>:src/backend/api/profiles.py | grep -c rl_export` → `0` for each). The files survive `DELETE /profiles/{id}`.
  - `git check-ignore -v --no-index src/backend/rl_exports/profile_x/dpo.jsonl` exits 1, so the path is not ignored and a directory `git add` would stage it.
  - Re-verified 2026-09-28 (Wave 6): the default is `Path(api/feedback.py).parents[1] / "rl_exports"` = `src/backend/rl_exports` (`api/feedback.py:64-66`, main = A = B). Only an `RL_EXPORT_DIR` under a `data/` directory is ignored (`git check-ignore` → `.gitignore:74:data/` for `data/rl_exports/…` and `src/backend/data/rl_exports/…`). Status: **not ignored at the default path; not swept by `DELETE /profiles`** (matrix row PRIV-10, gap, unowned; the erase fix is crypto-erase, ask-first).
  - The content is strict-redacted (PRIV-01), but it is still per-profile derived data left after erasure. `docs/compliance/data-privacy.md:108` documents the path.
  - The docstring at `api/profiles.py:799-800` ("the export routes stream downloads rather than writing files server-side") is already false for this route.
  - **Needs its own item and an owner decision**: sweep it in the delete flow (auth-adjacent, ask first) and ignore it.
- **F-2 · Production INFO logs are dropped.** See fact 7. This affects AUD-04's premise and HC-M07's usefulness. Owner question O-C3-4.
- **F-3 · Unknown units drop whole observations.** See fact 6. It is recorded on the eval card as a known miss. Fixing it is extractor work, not G-C3a.
- **F-4 · Plan 06 will break `tests/test_care_tasks.py:809,825`.** Those lines pin the profile head at `012_pinboards`, and plan 06's migration 013 moves the head. Plan 06 does not list the file.
- **F-6 · Direct-call status assertions in export tests** (recurring-failures #1). HC-PKT-014/015 (`tests/test_visit_prep_packet.py:403-432` main@40f590e) and HC-FHIR-103/104 (`tests/test_fhir_export.py:535-559`) assert 403/404 by calling handlers as plain functions, so a broken `Depends(...)` on those routes is invisible to them. G-C1 adds HTTP equivalents (HC-EXPA-003/004/005/010) and does not rely on them. Converting them is a separate test-only item.
- **F-5 · D8-delivery is not in the owner record.** It appears only in the W-8 plan and in orchestrator prompts. `owner-decisions-2026-09-27.md` should gain a row for it.

## Owner questions (unsigned; see Sign-offs)

- **O-C1-1 · Go and storage design.** This is S-C1-1 and **blocks all of G-C1**. The design: vault table `export_artifact`, one row per generated artifact, kept until the profile is deleted. Download needs the vault unlocked. After a real restart the vault connection is gone, so the first download returns `403 "Profile database not available. Please log in again."` (`core/auth.py:298-310`) until the user logs in. **Recommended.**
- **O-C1-2 · Is backend persistence enough?** After a restart plus re-login the SPA has usually lost the artifact ID, because it is held only in React mutation state (`pages/ExportPage.tsx:155,199,215`). Persistence helps a restart while the page stays open, such as `uvicorn --reload` or a backend crash. A "recent exports" list is new route and UI work. **Recommended: not now.** The program's acceptance only asks that "a download succeeds after a restart".
- **O-C1-3 · Retention.** The rows are derived copies of vault data inside the same encrypted vault. **Recommended: keep until profile deletion for now.** A prune or TTL is a separate decision, and relevant to D10's HIPAA-aligned posture.
- **O-C1-4 · Docstring.** This is S-C1-2. Should G-C1 amend `api/profiles.py:799-803` so it says that downloadable export artifacts live in the vault and are erased by step 4? The file is auth-adjacent and shared (P5 → P7 → G-B1). **Recommended: yes, one sentence, in its own commit.**
- **O-C2-1 · Sending the repository to an LLM API.** OpenWiki "runs a DeepAgents documentation agent" and "Requires an LLM API key" (`openwiki/README.md:28`). The owner runs it, which is the branch-A d4 scope. Whether it honours `.gitignore` is **UNVERIFIED**. Hence the clean-clone step in Task C2.1.
- **O-C3-1 · Threshold margin for HC-M06.** Precedent `tests/test_visit_note_extraction.py:7-21` sets thresholds "beneath those measured numbers". **Recommended: each threshold = measured value − 0.05, floored to 2 decimals, never lowered afterwards.**
- **O-C3-2 · Mechanism.** HC-M07's description says "via a logging.Filter in a new core/logging_setup.py". Fact 7 shows a handler filter is wiped at the first login. **Recommended:** a process-wide `logging.setLogRecordFactory` wrapper in the same new file, installed in `create_app()`. The verification step ("log records carry the correlation ID") is unchanged.
- **O-C3-3 · JSON log formatter.** **Recommended: not built.** It is not in the verification steps and it is a PHI risk.
- **O-C3-4 · Production log visibility (F-2).** Out of scope. Changing root levels or handlers widens log exposure (C-REDACT-3 / PRIV-06) and needs its own decision.
- **O-C4-x.** The decision record carries its own unsigned lines (Task C4.2).

## Review Focus

The five failure modes most likely to bite a real user that the spec implies but does not state. Each has a test in the owning task.
1. **A download arrives after a restart but before re-login** (vault closed). Expected: a clear 403 telling the user to log in, never a 500 or a misleading 404. → HC-EXPA-010 (Task C1.1).
2. **An artifact ID is requested through the wrong route kind** (a summary ID at `/fhir/{id}/download`). Expected: 404, as the per-kind dicts gave structurally. → HC-EXPA-005.
3. **A client supplies a hostile correlation header** (`evil\nSECURITY_AUDIT: …`). Expected: the audit payload carries a fresh UUID, never the raw header (log injection). → HC-OBSV-003 second assertion.
4. **A log record is created outside any request** (startup, schedulers). Expected: `correlation_id == "-"`, never an exception or a stale ID from the last request. → HC-OBSV-001 second assertion.
5. **The pdfplumber/pdfminer version differs between environments.** `requirements.txt:37` has `pdfplumber>=0.10.0`, which is unpinned. Expected: the eval card numbers are those of CI's interpreter. A local mismatch is an environment finding, recorded, and never "fixed" by editing numbers. → HC-EXTR-003 failure message plus Task C3a.3 Step 4.

---

# Group G-C1: persist export artifacts (PRIV-08)

## Task C1.0: Worktree, preconditions, phase-start measurement

**Files:** none modified.

- [ ] **Step 1: Create the worktree and prove it is post-P1**

```bash
ROOT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral; WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-gc1; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
git -C "$ROOT" fetch origin && git -C "$ROOT" worktree add "$WT" -b feat/gc1-export-artifact-persistence origin/main && cd "$WT"
git merge-base --is-ancestor 7b2ff1f HEAD && git merge-base --is-ancestor 692fdf3 HEAD && echo post-P1-ok
git rev-parse HEAD | tee "$WT.start-sha"; "$PY" --version     # START SHA saved beside the worktree for Task C1.2 Step 7
```
Expected: `post-P1-ok`, a SHA, then `Python 3.11.x`. **STOP** if `worktree add` fails (ask before removing anything), if `post-P1-ok` is missing, or if the venv is missing.

- [ ] **Step 2: Check the dependencies**

```bash
set -o pipefail
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-gc1; cd "$WT"
grep -c "datetime.utcnow" src/backend/api/export.py src/backend/modules/export.py      # P5: both 0
grep -n "redact_summary_data" src/backend/api/export.py                                  # W-2: >=1 hit
grep -n "_SYNTHETIC_RESET_MODELS" src/backend/api/profiles.py                            # P7: >=1 hit
grep -rln "hc_reset_010" src/backend/tests                                               # P7: 1 file
ls src/backend/migrations/profile/versions/*.py | sort | tail -1                          # P6 head file
for c in master profile; do grep -h "^down_revision" src/backend/migrations/$c/versions/*.py | sort | uniq -d; done   # empty
gh pr list --state open --json number,files --jq '.[] | select(any(.files[]; .path=="src/backend/api/profiles.py" or .path=="src/backend/api/export.py")) | .number'   # empty
```
Record `PREV_HEAD`, the `revision` string of the last profile file (expected `013_fk_cascade_alignment`). Then set `NEW_HEAD=014_export_artifacts`, or `(N+1)_export_artifacts` if the head number differs. **STOP** if any check misses, if `uniq -d` prints anything, or if an open PR touches either file (never concurrent).

- [ ] **Step 3: Confirm S-C1-1 is signed.** Open this file's Sign-offs. If S-C1-1 has no name and date, **STOP**.

- [ ] **Step 4: Confirm the ID and name collisions are clear**

```bash
set -o pipefail
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-gc1; cd "$WT"
git grep -n -i "hc_expa\|HC-EXPA\|export_artifact\|ExportArtifact" -- src/ || echo no-collision
test ! -e src/backend/tests/test_export_artifact_persistence.py && echo file-free
```
Expected: `no-collision`, then `file-free`. `-k hc_expa` does not match `hc_expr` (W-2): the substrings differ at the fifth character.

- [ ] **Step 5: Measure the start tree**

```bash
set -o pipefail
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-gc1; PY="$HOME/venvs/asclexis-311/bin/python"; cd "$WT/src/backend"
find . -name __pycache__ -prune -exec rm -rf {} +
"$PY" -m pytest tests/ --collect-only -q -p no:cacheprovider 2>&1 | tail -1
LOG="$WT.start-suite.log"                              # sibling of the worktree, never inside it
"$PY" -m pytest tests/ -p no:cacheprovider -q -rfE > "$LOG" 2>&1; echo "pytest exit=$?"
grep -E "^(FAILED|ERROR) " "$LOG" | sed -E 's/ - .*//' | sort -u > "$WT.start-failures.txt"
wc -l < "$WT.start-failures.txt"; cat "$WT.start-failures.txt"   # every failing node ID
tail -5 "$LOG"                                         # display only
```
Record in the Execution record: interpreter, OS, command, `START_COLLECTED`, and the full contents of `$WT.start-failures.txt` (`START_FAILURES`). The `tail` is for display only. The failure list comes from the full log (`-rfE` prints one `FAILED`/`ERROR` line per node), never from a truncated tail.

## Task C1.1: Write the failing tests (RED)

**Files:** create `src/backend/tests/test_export_artifact_persistence.py`.

**Interfaces**
- Consumes: `route_client(router, prefix, profile_id=..., master_db=...)`; `core.auth.get_profile_db_session`; `ProfileDatabaseBase`; models `Document`, `Observation`, `Pinboard`, `PinboardItem`; `tests.test_profile_deletion._delete` (async, keyword `profile_id`).
- Produces, used by C1.2 and C1.3: the model `models.export_artifact.ExportArtifact(id: str, kind: str, profile_id: str, payload_json: str, created_at: datetime)`; `EXPORT_ARTIFACT_KINDS = ("doctor_summary", "visit_prep", "fhir_r4")`.

- [ ] **Step 1: Write the test file**

```python
"""G-C1 / PRIV-08: export artifacts survive a restart (HC-EXPA-NNN).

Artifacts are profile data, so they live in the profile vault (C-ISO-1) and die
with it on crypto-erase (C-KEY-2). Every status assertion goes through HTTP
(C-ISO-2). A "restart" drops all process state: any in-memory export store is
cleared and every later request opens a fresh engine on the same vault file.
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import uuid
from contextlib import closing, contextmanager
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import api.export as export_api
import api.pinboards as pinboards_api
import api.profiles as profiles_api
from core.auth import get_profile_db_session
from core.profile_database import ProfileDatabaseBase
from models import Document, Observation, Pinboard, PinboardItem
from tests.support.routes import route_client

PROFILE_A = "profile-a"
PROFILE_B = "profile-b"
NEW_HEAD = "014_export_artifacts"          # set from Task C1.0 Step 2
PREV_HEAD = "013_fk_cascade_alignment"     # set from Task C1.0 Step 2

# (id, generate path, body, id key, download path, download audit type)
CASES = [
    ("summary", "/export/doctor-summary", {"format": "text"}, "summary_id",
     "/export/doctor-summary/{id}/download?format=text", "summary_download"),
    ("packet", "/export/visit-prep", {"confirm": True}, "packet_id",
     "/export/visit-prep/{id}/download?format=markdown", "visit_prep_download"),
    ("fhir", "/export/fhir", {"confirm": True}, "export_id",
     "/export/fhir/{id}/download", "fhir_r4_download"),
]
CASE_IDS = [c[0] for c in CASES]


def _engine(path: Path):
    return create_async_engine(f"sqlite+aiosqlite:///{path}", poolclass=NullPool)


async def _create_vault(path: Path, profile_id: str, marker: str, unit: str = "mg/dL") -> dict:
    """Real file-backed vault: every profile table, one document, two verified
    observations (one abnormal, carrying `marker`), and a pinboard pinning it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = _engine(path)
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        doc_id, obs_id = str(uuid.uuid4()), str(uuid.uuid4())
        s.add(Document(id=doc_id, profile_id=profile_id, path_hash="x" * 64, content_hash="y" * 64,
                       doc_type="lab_report", source="lab.pdf", status="verified",
                       collection_date=datetime(2024, 3, 15), imported_at=datetime(2024, 3, 16)))
        s.add(Observation(id=obs_id, profile_id=profile_id, doc_id=doc_id, analyte_canonical=marker,
                          analyte_raw=marker, value=250.0, unit=unit, ref_low=70.0, ref_high=99.0,
                          flag="H", is_abnormal=True, collected_at=datetime(2024, 3, 15),
                          user_verified=True))
        s.add(Observation(id=str(uuid.uuid4()), profile_id=profile_id, doc_id=doc_id,
                          analyte_canonical="glucose", analyte_raw="glucose", value=95.0,
                          unit="mg/dL", ref_low=70.0, ref_high=99.0, flag=None, is_abnormal=False,
                          collected_at=datetime(2024, 1, 10), user_verified=True))
        board = Pinboard(name="Visit")
        s.add(board)
        await s.flush()
        s.add(PinboardItem(pinboard_id=board.id, item_type="observation", item_id=obs_id))
        await s.commit()
        ids = {"pinboard_id": board.id}
    await engine.dispose()
    return ids


def _profile_db_override(path: Path):
    """Mirror ProfileDatabaseConnection.get_session (core/profile_database.py:75-85)."""
    maker = async_sessionmaker(_engine(path), expire_on_commit=False)

    async def _override():
        async with maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    return _override


class _Result:
    def __init__(self, obj):
        self._obj = obj

    def scalar_one_or_none(self):
        return self._obj


def _master_db(profile_id: str = PROFILE_A, commit_error: Exception | None = None):
    db = AsyncMock()  # the FHIR route reads Profile from master (api/export.py:1174-1177)
    db.execute.return_value = _Result(SimpleNamespace(id=profile_id, display_name="Jane Doe"))
    if commit_error is not None:
        db.commit.side_effect = commit_error
    return db


@contextmanager
def _client(router, prefix: str, vault: Path | None, profile_id: str = PROFILE_A, master_db=None):
    with route_client(router, prefix, profile_id=profile_id,
                      master_db=master_db or _master_db(profile_id)) as client:
        if vault is not None:
            client.app.dependency_overrides[get_profile_db_session] = _profile_db_override(vault)
        yield client


def _simulate_restart() -> None:
    for name in ("_summary_store", "_packet_store", "_fhir_store"):
        store = getattr(export_api, name, None)
        if store is not None:
            store.clear()


async def _rows(path: Path) -> list:
    from models.export_artifact import ExportArtifact
    engine = _engine(path)
    async with engine.connect() as conn:
        rows = (await conn.execute(select(ExportArtifact))).all()
    await engine.dispose()
    return rows


@pytest.mark.parametrize("kind,gen,body,idkey,dl,dl_type", CASES, ids=CASE_IDS)
def test_hc_expa_001_download_survives_restart(tmp_path, monkeypatch, kind, gen, body, idkey, dl, dl_type):
    audit = AsyncMock()
    monkeypatch.setattr(export_api, "log_export_event", audit)
    vault = tmp_path / "vault.db"
    asyncio.run(_create_vault(vault, PROFILE_A, "zzmarkera"))
    with _client(export_api.router, "/export", vault) as client:
        created = client.post(gen, json=body)
        assert created.status_code == 200, created.text
        art_id = created.json()[idkey]
        before = client.get(dl.format(id=art_id))
        assert before.status_code == 200, before.text
    _simulate_restart()
    with _client(export_api.router, "/export", vault) as client:
        after = client.get(dl.format(id=art_id))
    assert after.status_code == 200, after.text
    assert after.content == before.content
    types = [c.kwargs["export_type"] for c in audit.await_args_list]
    assert types.count(dl_type) == 2  # both downloads audited (C-AUDIT-1)


def test_hc_expa_002_pinboard_packet_survives_restart(tmp_path, monkeypatch):
    monkeypatch.setattr(pinboards_api, "log_pinboard_event", AsyncMock())
    monkeypatch.setattr(export_api, "log_export_event", AsyncMock())
    vault = tmp_path / "vault.db"
    ids = asyncio.run(_create_vault(vault, PROFILE_A, "zzmarkera"))
    with _client(pinboards_api.router, "/pinboards", vault) as client:
        created = client.post(f"/pinboards/{ids['pinboard_id']}/export", json={"confirm": True})
        assert created.status_code == 200, created.text
    _simulate_restart()
    with _client(export_api.router, "/export", vault) as client:
        after = client.get(f"/export/visit-prep/{created.json()['packet_id']}/download?format=markdown")
    assert after.status_code == 200, after.text
    assert after.content.decode("utf-8") == created.json()["markdown"]


@pytest.mark.parametrize("kind,gen,body,idkey,dl,dl_type", CASES, ids=CASE_IDS)
def test_hc_expa_003_other_profiles_vault_cannot_serve_it(tmp_path, monkeypatch, kind, gen, body, idkey, dl, dl_type):
    monkeypatch.setattr(export_api, "log_export_event", AsyncMock())
    vault_a, vault_b = tmp_path / "a" / "vault.db", tmp_path / "b" / "vault.db"
    asyncio.run(_create_vault(vault_a, PROFILE_A, "zzmarkera"))
    asyncio.run(_create_vault(vault_b, PROFILE_B, "zzmarkerb"))
    with _client(export_api.router, "/export", vault_a) as client:
        art_id = client.post(gen, json=body).json()[idkey]
    with _client(export_api.router, "/export", vault_b, profile_id=PROFILE_B) as client:
        response = client.get(dl.format(id=art_id))
    assert response.status_code == 404, response.text


# (kind, download path, 403 detail): the HTTP replacement for the direct-call
# 403 checks in HC-PKT-014 / HC-FHIR-104 (recurring-failures #1).
FOREIGN_ROW_CASES = [
    ("doctor_summary", "/export/doctor-summary/{id}/download?format=text", "Access denied to this summary"),
    ("visit_prep", "/export/visit-prep/{id}/download?format=markdown", "Access denied to this packet"),
    ("fhir_r4", "/export/fhir/{id}/download", "Access denied to this export"),
]


@pytest.mark.parametrize("kind,dl,detail", FOREIGN_ROW_CASES, ids=[c[0] for c in FOREIGN_ROW_CASES])
def test_hc_expa_004_row_owned_by_another_profile_is_refused(tmp_path, monkeypatch, kind, dl, detail):
    from models.export_artifact import ExportArtifact
    audit = AsyncMock()
    monkeypatch.setattr(export_api, "log_export_event", audit)
    vault = tmp_path / "vault.db"
    asyncio.run(_create_vault(vault, PROFILE_A, "zzmarkera"))
    art_id = str(uuid.uuid4())

    async def _insert():
        engine = _engine(vault)
        async with async_sessionmaker(engine)() as s:
            s.add(ExportArtifact(id=art_id, kind=kind, profile_id=PROFILE_B,
                                 payload_json=json.dumps({"id": art_id})))
            await s.commit()
        await engine.dispose()

    asyncio.run(_insert())
    with _client(export_api.router, "/export", vault) as client:
        response = client.get(dl.format(id=art_id))
    assert response.status_code == 403
    assert response.json()["detail"] == detail
    audit.assert_not_awaited()  # a refused download writes no download audit row


def test_hc_expa_005_artifact_id_is_bound_to_its_kind(tmp_path, monkeypatch):
    monkeypatch.setattr(export_api, "log_export_event", AsyncMock())
    vault = tmp_path / "vault.db"
    asyncio.run(_create_vault(vault, PROFILE_A, "zzmarkera"))
    with _client(export_api.router, "/export", vault) as client:
        summary_id = client.post("/export/doctor-summary", json={"format": "text"}).json()["summary_id"]
        as_fhir = client.get(f"/export/fhir/{summary_id}/download")
        as_packet = client.get(f"/export/visit-prep/{summary_id}/download?format=markdown")
    assert (as_fhir.status_code, as_packet.status_code) == (404, 404)


def test_hc_expa_006_failed_audit_commit_leaves_no_artifact(tmp_path, monkeypatch):
    monkeypatch.setattr(export_api, "log_export_event", AsyncMock())
    vault = tmp_path / "vault.db"
    asyncio.run(_create_vault(vault, PROFILE_A, "zzmarkera"))
    master = _master_db(commit_error=RuntimeError("audit commit failed"))
    with _client(export_api.router, "/export", vault, master_db=master) as client:
        with pytest.raises(RuntimeError, match="audit commit failed"):
            client.post("/export/doctor-summary", json={"format": "text"})
    assert asyncio.run(_rows(vault)) == []  # read through a fresh engine: commit-level, not session-level


def test_hc_expa_007_crypto_erase_removes_persisted_artifacts(tmp_path, monkeypatch):
    from tests.test_profile_deletion import _delete
    monkeypatch.setattr(type(profiles_api.settings), "app_data_path", property(lambda self: tmp_path))
    monkeypatch.setattr(export_api, "log_export_event", AsyncMock())
    vaults = {p: tmp_path / "vaults" / p / "vault.db" for p in (PROFILE_A, PROFILE_B)}
    art = {}
    for profile_id, marker in ((PROFILE_A, "zzerasemarkera"), (PROFILE_B, "zzerasemarkerb")):
        asyncio.run(_create_vault(vaults[profile_id], profile_id, marker))
        (vaults[profile_id].parent / "key.bin").write_bytes(b"sealed-key")
        (vaults[profile_id].parent / "key.method").write_text("password")
        with _client(export_api.router, "/export", vaults[profile_id], profile_id=profile_id) as client:
            art[profile_id] = client.post("/export/doctor-summary", json={"format": "text"}).json()["summary_id"]
    _simulate_restart()
    asyncio.run(_delete(profile_id=PROFILE_A))
    assert not (tmp_path / "vaults" / PROFILE_A).exists()
    needles = (art[PROFILE_A].encode(), b"zzerasemarkera")
    leaked = [p for p in tmp_path.rglob("*") if p.is_file() and any(n in p.read_bytes() for n in needles)]
    assert leaked == [], leaked  # content-level, not filename-level (recurring-failures #1)
    assert [r.id for r in asyncio.run(_rows(vaults[PROFILE_B]))] == [art[PROFILE_B]]


def test_hc_expa_008_profile_migration_matches_model(tmp_path, monkeypatch):
    from alembic import command
    from core import migrations
    from core.config import settings
    from models.export_artifact import ExportArtifact
    monkeypatch.setattr(settings, "database_encryption_required", False)
    vault, key = tmp_path / "vault.db", b"0" * 32
    migrations.run_profile_migration(vault, key)
    assert migrations.get_profile_current_revision(vault, key) == NEW_HEAD
    with closing(sqlite3.connect(vault)) as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(export_artifact)")}
    assert cols == set(ExportArtifact.__table__.columns.keys())
    config = migrations._get_alembic_config("profile")
    config.attributes["vault_path"] = vault
    config.attributes["encryption_key"] = key
    command.downgrade(config, PREV_HEAD)
    with closing(sqlite3.connect(vault)) as conn:
        assert conn.execute("SELECT name FROM sqlite_master WHERE name='export_artifact'").fetchall() == []
    command.upgrade(config, "head")
    assert migrations.get_profile_current_revision(vault, key) == NEW_HEAD


def test_hc_expa_009_persisted_summary_is_the_redacted_copy(tmp_path, monkeypatch):
    """W-2 lands first (W-2 plan :92): what persists must already be redacted."""
    monkeypatch.setattr(export_api, "log_export_event", AsyncMock())
    vault = tmp_path / "vault.db"
    asyncio.run(_create_vault(vault, PROFILE_A, "zzmarkera", unit="mmol/L (Patient: Jane Doe)"))
    with _client(export_api.router, "/export", vault) as client:
        assert client.post("/export/doctor-summary", json={"format": "text"}).status_code == 200
    payloads = [r.payload_json for r in asyncio.run(_rows(vault))]
    assert len(payloads) == 1
    assert "Jane" not in payloads[0] and "Doe" not in payloads[0]


def test_hc_expa_010_download_with_locked_vault_is_403(tmp_path, monkeypatch):
    """After a real restart no vault connection exists until re-login."""
    monkeypatch.setattr(export_api, "log_export_event", AsyncMock())
    with _client(export_api.router, "/export", vault=None) as client:  # real get_profile_db_session
        response = client.get(f"/export/doctor-summary/{uuid.uuid4()}/download?format=text")
    assert response.status_code == 403
    assert "log in again" in response.json()["detail"]
```

- [ ] **Step 2: Run and record RED**

```bash
set -o pipefail
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-gc1; PY="$HOME/venvs/asclexis-311/bin/python"; cd "$WT/src/backend"
"$PY" -m pytest tests/test_export_artifact_persistence.py -p no:cacheprovider -q -rfE -k hc_expa > "$WT.gc1-red.log" 2>&1
grep -E "^(FAILED|ERROR|PASSED) |passed|failed|error" "$WT.gc1-red.log" | tail -40   # display; the full log is the record
```
Expected, 16 collected:
- `001[summary|packet|fhir]`: `assert 404 == 200`, with detail `Summary not found` / `Visit-prep packet not found` / `FHIR export not found` (reproduced in the prototype above).
- `002`: `assert 404 == 200`.
- `003[×3]`: `assert 403 == 404` (the shared dict answers 403).
- `004[doctor_summary|visit_prep|fhir_r4]`, `006`, `007`, `008`: `ModuleNotFoundError: No module named 'models.export_artifact'`.
- `009`: `ModuleNotFoundError: No module named 'models.export_artifact'` (in `_rows`).
- `010`: `assert 404 == 403`.
- `005`: **PASSES** before the change. The per-kind dicts give it structurally. It guards the single-table design and is proved in the break-it step.

Record the output. **STOP** if anything is red for a different reason. **What these tests would fail to notice:**
- a real SQLCipher reopen with the unsealed key: the suite runs with encryption off (`tests/conftest.py:57`, matrix KEY-02);
- the SPA losing the ID after re-login (O-C1-2);
- payload shapes other than the three seeded ones.

- [ ] **Step 3: Commit RED** (tests only)

This commit changes collection (+16), so it also updates the baseline tokens (Global Constraints, "Baseline sentences"):

```bash
set -o pipefail
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-gc1; PY="$HOME/venvs/asclexis-311/bin/python"; cd "$WT"
N=$(cd "$WT/src/backend" && "$PY" -m pytest tests/ --collect-only -q -p no:cacheprovider 2>&1 | tail -1 | grep -oE '^[0-9]+'); echo "collected=$N"
grep -nE "tests collected|differs from [0-9]+|[0-9]+ collected" "$WT/CLAUDE.md" "$WT/AGENT.md"
# Edit by hand: replace ONLY the numbers in "**<n> backend tests collected.**" and "differs from <n>" (CLAUDE.md)
# and the "<n> collected" token (AGENT.md) with $N. Leave every pass-count ("all <n> pass", "<n> pass in CI") as is; flag it in the PR.
git -C "$WT" diff -U0 -- CLAUDE.md AGENT.md    # only those numeric tokens changed
P="src/backend/tests/test_export_artifact_persistence.py CLAUDE.md AGENT.md"
git add -- $P && git diff --cached --name-only    # exactly those 3 paths
git commit -m "feat(export): failing tests for export-artifact persistence (HC-EXPA, PRIV-08)" -- $P
```

## Task C1.2: Model, migration, reset tuple (HC-EXPA-008 green)

**Files:**
- create `src/backend/models/export_artifact.py` and `src/backend/migrations/profile/versions/014_export_artifacts.py`;
- modify `src/backend/models/__init__.py`, `src/backend/api/profiles.py` (tuple only), and `src/backend/tests/test_care_tasks.py` (2 head literals).

- [ ] **Step 1: Model**

```python
"""Downloadable export artifacts, persisted in each encrypted profile vault.

G-C1 / PRIV-08: a doctor summary, visit-prep or pinboard packet, or FHIR bundle
must still download after a backend restart. Rows hold the exact dict the
download routes render from. They live in the profile vault (never the master
DB) and are erased with it by DELETE /profiles/{id} (AGENT.md flow 5, step 4).
"""

from datetime import datetime

from sqlalchemy import DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.profile_database import ProfileDatabaseBase
from core.time import utcnow

EXPORT_ARTIFACT_KINDS = ("doctor_summary", "visit_prep", "fhir_r4")


class ExportArtifact(ProfileDatabaseBase):
    __tablename__ = "export_artifact"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    profile_id: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utcnow)
```

- [ ] **Step 2: Register it.** In `models/__init__.py`, add `from .export_artifact import ExportArtifact` below the `Pinboard` import, and add `"ExportArtifact",` to `__all__` below `"PinboardItem",`.

- [ ] **Step 3: Migration.** Pattern: `012_pinboards.py`. Use `PREV_HEAD` from Task C1.0.

```python
"""Persist downloadable export artifacts in the profile vault (G-C1, PRIV-08).

Revision ID: 014_export_artifacts
Revises: 013_fk_cascade_alignment
Create Date: <execution date>
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "014_export_artifacts"
down_revision: Union[str, None] = "013_fk_cascade_alignment"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "export_artifact",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("profile_id", sa.Text(), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
    )


def downgrade() -> None:
    op.drop_table("export_artifact")
```

- [ ] **Step 4: Reset tuple.** In `api/profiles.py`, add `ExportArtifact` to `_SYNTHETIC_RESET_MODELS`. It has no FK, so any position is valid; put it first. Import it the same way P7 imports its models. Change nothing else in the file.

- [ ] **Step 5: Head literals.** In `tests/test_care_tasks.py`, change the two `get_profile_current_revision(...) ==` expectations from `PREV_HEAD` to `NEW_HEAD`. Do not change the downgrade target.

- [ ] **Step 6: Run**

```bash
set -o pipefail
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-gc1; PY="$HOME/venvs/asclexis-311/bin/python"; cd "$WT/src/backend"
"$PY" -m pytest tests/test_export_artifact_persistence.py -p no:cacheprovider -q -rfE -k "hc_expa_008" > "$WT.gc1-c12a.log" 2>&1; grep -E "^(FAILED|ERROR) " "$WT.gc1-c12a.log"; tail -1 "$WT.gc1-c12a.log"
"$PY" -m pytest tests/ -p no:cacheprovider -q -rfE -k "hc_reset or care_task or pinboard" > "$WT.gc1-c12b.log" 2>&1; grep -E "^(FAILED|ERROR) " "$WT.gc1-c12b.log"; tail -1 "$WT.gc1-c12b.log"
for c in master profile; do grep -h "^down_revision" migrations/$c/versions/*.py | sort | uniq -d; done
```
Expected:
- `1 passed`;
- no failures (HC-RESET-010 is green because the tuple is updated);
- `uniq -d` empty.

**Break it** (mode (b), after Step 8's commit): in the disposable worktree, remove `ExportArtifact` from the tuple and confirm HC-RESET-010 goes red.

- [ ] **Step 7: Rollback rehearsal** (proves the Rollback section; disposable worktrees only)

```bash
set -o pipefail
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-gc1; PY="$HOME/venvs/asclexis-311/bin/python"
START=$(cat "$WT.start-sha"); RB="$WT-rollback"; RBV="$WT-rollback-vault"; mkdir -p "$RBV"
MIG='from pathlib import Path; from core import migrations; v=Path("'"$RBV"'/vault.db"); k=b"0"*32; migrations.run_profile_migration(v, k); print(migrations.get_profile_current_revision(v, k))'
cd "$WT/src/backend" && DATABASE_ENCRYPTION_REQUIRED=false "$PY" -c "$MIG"            # expect: 014_export_artifacts
git -C "$WT" worktree add --detach "$RB" "$START"
cd "$RB/src/backend" && DATABASE_ENCRYPTION_REQUIRED=false "$PY" -c "$MIG" 2>&1 | tail -2   # expect: Can't locate revision identified by '014_export_artifacts'
git -C "$WT" worktree remove --force "$RB"
rm -rf "$RBV"
```
The C1.2-only tree succeeds by construction: it is the tree that printed `014_export_artifacts` above. Record both outputs.
- If the pre-G-C1 tree **opens** the vault anyway, a full revert is safe. Record that and simplify the Rollback section.
- If it fails with a different error, **STOP** and report it.

- [ ] **Step 8: Commit**

```bash
set -o pipefail
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-gc1; cd "$WT"
P="src/backend/models/export_artifact.py src/backend/models/__init__.py src/backend/migrations/profile/versions/014_export_artifacts.py src/backend/api/profiles.py src/backend/tests/test_care_tasks.py"
git add -- $P && git diff --cached --name-only   # exactly those 5
git commit -m "feat(export): export_artifact profile table and migration 014" -- $P
```

## Task C1.3: Persist and load through the vault (routes GREEN), migrate 9 direct-call tests

**Files:** `src/backend/api/export.py`, `src/backend/api/pinboards.py`, `src/backend/tests/test_visit_prep_packet.py`, `src/backend/tests/test_fhir_export.py`.

**Interfaces**
- Produces, in `api/export.py`:
  - `async def _save_artifact(profile_db: AsyncSession, *, artifact_id: str, kind: str, profile_id: str, payload: dict) -> None`;
  - `async def _load_artifact(profile_db: AsyncSession, *, artifact_id: str, kind: str, profile_id: str, not_found: str, denied: str) -> dict`.
- `api/pinboards.py` imports `_save_artifact`.

- [ ] **Step 1: Helpers in `api/export.py`.** Replace the three store blocks (`:43-50`) with the following, and add `from models.export_artifact import EXPORT_ARTIFACT_KINDS, ExportArtifact` to the imports:

```python
async def _save_artifact(
    profile_db: AsyncSession, *, artifact_id: str, kind: str, profile_id: str, payload: dict
) -> None:
    """Stage a downloadable artifact in the caller's profile vault (G-C1).

    Flush only; the route commits the vault after its audit row commits, so a
    failed audit never leaves an unaudited artifact behind.
    """
    if kind not in EXPORT_ARTIFACT_KINDS:
        raise ValueError(f"unknown export artifact kind: {kind}")
    profile_db.add(ExportArtifact(
        id=artifact_id, kind=kind, profile_id=profile_id, payload_json=json.dumps(payload),
    ))
    await profile_db.flush()


async def _load_artifact(
    profile_db: AsyncSession, *, artifact_id: str, kind: str, profile_id: str,
    not_found: str, denied: str,
) -> dict:
    row = await profile_db.get(ExportArtifact, artifact_id)
    if row is None or row.kind != kind:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=not_found)
    if row.profile_id != profile_id:  # defence in depth; a vault only holds its own rows
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=denied)
    return json.loads(row.payload_json)
```
`json.dumps` is strict (no `default=`). A non-JSON value must fail loudly at generate time, not get silently stringified.

- [ ] **Step 2: Generate routes.** Each change keeps the order *stage → audit commit → vault commit*.
  - **Doctor summary.** Replace the store line (`:446` pre-W-2; after W-2 it stores the redacted dict) with `await _save_artifact(profile_db, artifact_id=summary.summary_id, kind="doctor_summary", profile_id=profile_id, payload=<the same dict W-2 stores>)`. After its `audit_and_commit(...)`, add `await profile_db.commit()`.
  - **Visit-prep.** Replace `:799` with `await _save_artifact(profile_db, artifact_id=packet["packet_id"], kind="visit_prep", profile_id=profile_id, payload=packet)`. After its audit, add `await profile_db.commit()`.
  - **FHIR.** Replace `:1227-1230` with `await _save_artifact(profile_db, artifact_id=export_id, kind="fhir_r4", profile_id=profile_id, payload=result["bundle"])`. After its audit, add `await profile_db.commit()`.
  - **Pinboard** (`api/pinboards.py`). Change the import at `:13` to `from api.export import _compute_trends, _save_artifact`. Replace `:495` with `await _save_artifact(profile_db, artifact_id=packet["packet_id"], kind="visit_prep", profile_id=session.profile_id, payload=packet)`. After the `audit_and_commit` at `:496-501`, add `await profile_db.commit()`.

- [ ] **Step 3: Download routes.** In each, append `profile_db: ProfileDbSession = None` as the **last** parameter, so existing positional direct calls keep their meaning. Replace the lookup and both checks:
  - **Summary** (`:497-511`): `summary_data = await _load_artifact(profile_db, artifact_id=summary_id, kind="doctor_summary", profile_id=session.profile_id, not_found="Summary not found", denied="Access denied to this summary")`.
  - **Visit-prep** (`:840-851`): `packet = await _load_artifact(..., kind="visit_prep", not_found="Visit-prep packet not found", denied="Access denied to this packet")`.
  - **FHIR** (`:1267-1278`): `bundle = await _load_artifact(..., kind="fhir_r4", not_found="FHIR export not found", denied="Access denied to this export")`. Then change `json.dumps(stored["bundle"], indent=2)` to `json.dumps(bundle, indent=2)`.

  Leave `validate_uuid`, the audit calls and rendering untouched.

- [ ] **Step 4: Migrate the 9 direct-call tests.** Change the mechanism only; every existing `assert` stays.
  - **`tests/test_visit_prep_packet.py`:**
    - Drop `_packet_store` from the `from api.export import (...)` block (`:255-262`).
    - **HC-PKT-010:** set `profile_db = AsyncMock(); profile_db.add = MagicMock()`, pass it, and replace `assert response.packet_id in _packet_store` with:
      ```python
      stored = profile_db.add.call_args.args[0]
      assert (stored.id, stored.kind) == (response.packet_id, "visit_prep")
      profile_db.commit.assert_awaited()
      ```
      Import `MagicMock` alongside `AsyncMock`.
    - **HC-PKT-012…016:** add the module fixture `real_profile_db` (already defined at `:568-578`) to each signature. Pass `real_profile_db` as the generate call's `profile_db` argument, where `AsyncMock()` was, and add `profile_db=real_profile_db` to every `download_visit_prep(...)` call. HC-PKT-014 still expects 403 and HC-PKT-015 still expects 404, because the same vault serves a row whose `profile_id` differs from `another-profile`.
      - **Not relied on.** HC-PKT-014/015 and HC-FHIR-103/104 stay **direct-call** status assertions. They bypass FastAPI's dependency graph, including the new `ProfileDbSession` dependency on the download routes (CLAUDE.md §4; recurring-failures #1). This plan relies on none of them. The status guarantees G-C1 depends on are proved over HTTP with break-its: 403 on a foreign row (HC-EXPA-004 ×3), 404 in another profile's vault (HC-EXPA-003 ×3), 404 on a kind mismatch (HC-EXPA-005), 403 on a locked vault (HC-EXPA-010). Converting those 4 legacy tests to `route_client` is recorded as a follow-up finding (F-6), not done here. It is out of scope, and the files are shared with P5/W-2.
  - **`tests/test_fhir_export.py`:**
    - Add a fixture copied from `test_visit_prep_packet.py:568-578`, named `artifact_db`, with the same imports (`create_async_engine`, `AsyncSession`, `ProfileDatabaseBase`, `import models`).
    - **HC-FHIR-102:** replace the dict write and `del` with `await _save_artifact(artifact_db, artifact_id=export_id, kind="fhir_r4", profile_id="test-profile", payload={"resourceType": "Bundle", "type": "collection", "entry": []})` followed by `await artifact_db.commit()`. Call `download_fhir_export(export_id, _session("test-profile"), master_db, artifact_db)`.
    - **HC-FHIR-103:** pass `artifact_db` as the 4th argument.
    - **HC-FHIR-104:** save with `profile_id="owner-profile"`, then call with `_session("other-profile")` and `artifact_db`, and keep `== 403`.
    - Import `_save_artifact` from `api.export` inside each test, as those tests already import locally.

- [ ] **Step 5: Run GREEN**

```bash
set -o pipefail
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-gc1; PY="$HOME/venvs/asclexis-311/bin/python"; cd "$WT/src/backend"
grep -n "_summary_store\|_packet_store\|_fhir_store" -r api tests | grep -v test_export_artifact_persistence   # none
"$PY" -m pytest tests/test_export_artifact_persistence.py tests/test_visit_prep_packet.py tests/test_fhir_export.py tests/test_pinboards.py tests/test_export_redaction.py tests/test_export_api.py -p no:cacheprovider -q -rfE > "$WT.gc1-c13.log" 2>&1; grep -E "^(FAILED|ERROR) " "$WT.gc1-c13.log"; tail -1 "$WT.gc1-c13.log"
git -C "$WT" diff -U0 -- src/backend/tests/test_visit_prep_packet.py src/backend/tests/test_fhir_export.py | grep -E '^-\s+assert' || echo no-assert-removed
```
Expected:
- the grep prints nothing;
- all pass (16 HC-EXPA items; W-2's `test_export_redaction.py` still green);
- `no-assert-removed`, except the single HC-PKT-010 `in _packet_store` line, which Step 4 replaced with a stronger check.

If any other `assert` line was removed, **STOP**. That would be weakening a test.

- [ ] **Step 6: Commit**

```bash
set -o pipefail
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-gc1; cd "$WT"
P="src/backend/api/export.py src/backend/api/pinboards.py src/backend/tests/test_visit_prep_packet.py src/backend/tests/test_fhir_export.py"
git add -- $P && git diff --cached --name-only   # exactly those 4
git commit -m "feat(export): persist doctor-summary, visit-prep and FHIR artifacts in the profile vault" -- $P
```

## Task C1.4: Break each test on purpose (recurring-failures #1)

**Files:** temporary edits only. After each item, confirm `git -C "$WT" diff --exit-code` shows a clean tree.

- [ ] **Step 1.** Use mode (b): one disposable worktree `$BK` from HEAD, which is after Task C1.3's commit. Apply one break at a time in `$BK`, run `cd "$BK/src/backend" && "$PY" -m pytest tests/test_export_artifact_persistence.py -p no:cacheprovider -q -k <id>`, and confirm it goes red. Undo the break in `$BK` with `git -C "$BK" checkout -- .`; that is the disposable worktree, not the phase worktree. Remove `$BK` at the end:

| Break | Expected red |
|---|---|
| Remove `or row.kind != kind` in `_load_artifact` | `005` → `(200, …) != (404, 404)` |
| Remove the `row.profile_id != profile_id` check | `004[×3]` → `200 == 403` fails |
| Move `await profile_db.commit()` above `audit_and_commit` | `006` → one row found |
| In the test, point `vaults[PROFILE_A]` at `tmp_path / "outside" / "vault.db"` | `007` → `leaked` non-empty |
| Drop `payload_json` from the migration | `008` column-set mismatch |
| Persist W-2's **pre**-redaction dict | `009` → `'Jane' not in …` fails |
| Remove `profile_db: ProfileDbSession` from `download_summary` | `010` → 404 ≠ 403 |
| In `api/pinboards.py`, skip `_save_artifact` | `002` 404 |

Record each red line in the Execution record.

One break is deliberately **not** listed: deleting the handler's own `await profile_db.commit()`. It stays green, because the vault dependency commits on exit, both in the test override and in `ProfileDatabaseConnection.get_session` (`core/profile_database.py:75-85` main@40f590e). The ordering guarantee that matters is "no artifact is committed unless its audit row committed". HC-EXPA-006 tests it directly, and its break-it row (move the commit above `audit_and_commit`) proves it can go red.

## Task C1.5: Whole-flow re-walk, full suite, boot, PR

- [ ] **Step 1: Full suite and boot**

```bash
set -o pipefail
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-gc1; PY="$HOME/venvs/asclexis-311/bin/python"; cd "$WT/src/backend"
find . -name __pycache__ -prune -exec rm -rf {} +
"$PY" -m pytest tests/ --collect-only -q -p no:cacheprovider 2>&1 | tail -1     # START_COLLECTED + 16
LOG="$WT.end-suite.log"
"$PY" -m pytest tests/ -p no:cacheprovider -q -rfE > "$LOG" 2>&1; echo "pytest exit=$?"
grep -E "^(FAILED|ERROR) " "$LOG" | sed -E 's/ - .*//' | sort -u > "$WT.end-failures.txt"
comm -13 "$WT.start-failures.txt" "$WT.end-failures.txt"   # must print nothing: failures ⊆ START_FAILURES
tail -5 "$LOG"                                             # display only
"$PY" -c "from main import app; print('boot-ok')"
```

- [ ] **Step 2: Frontend DoD** (Windows PowerShell; no frontend file changed)

```powershell
Set-Location C:\Users\DangT\Documents\GitHub\HealthCentral-gc1\src\frontend
npm ci; if ($LASTEXITCODE -ne 0) { throw "npm ci failed: $LASTEXITCODE" }
npx tsc --noEmit; if ($LASTEXITCODE -ne 0) { throw "tsc failed: $LASTEXITCODE" }
npx vitest run; if ($LASTEXITCODE -ne 0) { throw "vitest failed: $LASTEXITCODE" }
```

- [ ] **Step 3: Re-walk the whole flow** (recurring-failures #2). Run it by hand with `.\dev.ps1`, on a **new throwaway profile** created for this purpose. Never use a real profile: its vault would be stamped `014` (see Rollback). The walk: generate each of the 3 kinds plus a pinboard export → download → stop and restart the backend → download returns 403 "log in again" → log in → download by the same ID. The ID comes from the browser devtools network tab, because the SPA state is lost (O-C1-2) → 200 → create a backup → delete the profile → `data/vaults/<id>` is gone and `data/backups/<id>` is gone. Record what you saw. **UNMEASURED** until done.

- [ ] **Step 4 (only if S-C1-2 is signed): Docstring.** In `api/profiles.py:799-803`, after "rather than writing files server-side", add: "Downloadable summary/packet/FHIR artifacts are the exception: they are rows in the profile vault and are erased by step 4." Then commit with `git commit -m "docs: note vault-held export artifacts in the crypto-erase docstring" -- src/backend/api/profiles.py`, after `git diff --cached --name-only` shows only that path.

- [ ] **Step 5: Plan checks and PR.** Confirm that `git diff --stat origin/main...HEAD -- src/backend/modules/redaction.py src/backend/core/auth.py src/backend/core/profile_database.py src/backend/tests/support/routes.py CLAUDE.md` prints nothing. Push and open the PR. The PR body follows handoff §6:
  - start and end measurements;
  - the red and green outputs;
  - the proposed matrix change **PRIV-08 `unknown` → `tested`** (HC-EXPA-001/002; not edited here);
  - the file list;
  - F-1 and F-4.

  **STOP** for the owner to merge.

---

# Group G-C2: OpenWiki generation review (branch A §14 d4)

## Task C2.0: Preconditions (session)

- [ ] **Step 1.** Check that P1 and P4 Task 13 have landed:

```bash
set -o pipefail
ROOT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral; git -C "$ROOT" fetch origin
git -C "$ROOT" merge-base --is-ancestor 7b2ff1f origin/main && git -C "$ROOT" merge-base --is-ancestor 692fdf3 origin/main && echo post-P1-ok
git -C "$ROOT" show origin/main:openwiki/README.md | sed -n 15,17p
git -C "$ROOT" show origin/main:AGENT.md | grep -n "openwiki"
git -C "$ROOT" ls-tree -r --name-only origin/main -- openwiki
```
Expected:
- `post-P1-ok`;
- the "still not generated" status line;
- the P4 Task 13 stub wording, or the original wording if P4 has not run (record which);
- exactly `openwiki/README.md`.

**STOP** if S-C2-1 is unsigned.

## Task C2.1: Owner generates in a clean clone (OWNER; the agent only prepares this text)

- [ ] **Step 1.** The owner runs the following on their machine. The clean worktree keeps git-ignored local files out of what the tool reads: `data/` (vaults), `.env`, `.claude/settings.local.json`, and model files. Whether OpenWiki honours `.gitignore` is **UNVERIFIED**.

```bash
set -o pipefail
ROOT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral; GEN=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-openwiki
git -C "$ROOT" worktree add "$GEN" -b docs/gc2-openwiki-generation origin/main && cd "$GEN"
git status --short --ignored | grep -v '^!! .*__pycache__' ; echo "--- expect nothing above"
npm install -g openwiki && openwiki --version        # record version
openwiki --init                                     # needs the owner's LLM API key; record provider + model + date
git status --short && git diff --stat
git add -- openwiki && git status --short openwiki   # the directory add is allowed only if every listed path is under openwiki/
git commit -m "docs: generate OpenWiki repository map (owner run)" -- openwiki
git push -u origin docs/gc2-openwiki-generation
```
The owner leaves any `CLAUDE.md`/`AGENT.md`/`AGENTS.md` changes **uncommitted** and pastes `git diff -- CLAUDE.md AGENT.md AGENTS.md` into the PR.

## Task C2.2: Diff review checklist (session, in the owner's branch worktree)

Every item is a command with an expected result. Any miss means **request changes**; do not fix generated text silently.

- [ ] **Step 1: Scope**

```bash
set -o pipefail
GEN=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-openwiki; cd "$GEN"
git diff --name-only origin/main...HEAD | grep -v '^openwiki/' || echo scope-ok
git diff --name-only origin/main...HEAD -- .github | wc -l      # 0: no CI workflow (README "CI": deferred)
```

- [ ] **Step 2: The hand-maintained README survives**

```bash
set -o pipefail; GEN=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-openwiki; cd "$GEN"
git diff origin/main...HEAD -- openwiki/README.md
```
Expected: no diff. The status line is updated in Task C2.3. If the tool rewrote the authority order, review rules or CI deferral → reject.

- [ ] **Step 3: Governance files untouched (S-C2-2).** The owner-pasted `CLAUDE.md`/`AGENT.md`/`AGENTS.md` diff is rejected by default. `AGENTS.md` is accepted only if S-C2-2 says so.

- [ ] **Step 4: Invariants are never restated weaker.** List every hit and compare each against `CLAUDE.md` "Hard invariants" (`:55-63`). A hit that states a rule less strictly (for example "should avoid network", "usually redacted", "may call Ollama") → reject:

```bash
set -o pipefail; GEN=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-openwiki; cd "$GEN"
grep -rniE "network|offline|redact|ProfileDbSession|get_db|SQLCipher|encrypt|audit|ModelRunner|llama_cpp|ollama|diagnos|dosing|medical advice|migration|utcnow" openwiki | grep -v '^openwiki/README.md'
```

- [ ] **Step 5: Forbidden claims**

```bash
set -o pipefail; GEN=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-openwiki; cd "$GEN"
grep -rniE "HIPAA[- ]compliant|covered entity" openwiki || echo d10-ok          # D10 wording rule
grep -rnE "\[YOUR_RESULTS:N\]|\[REFERENCE:N\]" openwiki || echo d11-check-none  # D11: [cite:N] is the validated marker; others are context labels
grep -rnE "\b[0-9]{3,5} (tests|passing|collected)\b" openwiki || echo counts-ok # recurring-failures #3: no unsourced figures
```
Any hit needs the surrounding sentence fixed to match D10/D11, or removed.

- [ ] **Step 6: No secrets or identifiers**

```bash
set -o pipefail; GEN=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-openwiki; cd "$GEN"
grep -rnE "sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|BEGIN (RSA |EC )?PRIVATE KEY|jwt_secret\s*=\s*\S+|password\s*=\s*['\"][^'\"]+" openwiki || echo secrets-ok
```

- [ ] **Step 7: Paths exist** (recurring-failures #8)

```bash
set -o pipefail; GEN=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-openwiki; cd "$GEN"
grep -rhoE '`[A-Za-z0-9_./-]+\.(py|ts|tsx|md|json|yml|ps1)`' openwiki | tr -d '`' | sort -u | while read p; do
  [ -e "$p" ] || [ -e "src/backend/$p" ] || [ -e "src/frontend/$p" ] || echo "MISSING $p"; done
```
Expected: no `MISSING` lines. Otherwise, fix or reject.

- [ ] **Step 8: Links resolve.** `docs_lint.py` does **not** scan `openwiki/`: it covers `docs/**/*.md` plus `README.md`, the frontend README, `AGENT.md` and `CLAUDE.md` (`scripts/docs_lint.py:97-101,288-292`). A green lint proves nothing here.

```bash
set -o pipefail; GEN=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-openwiki; cd "$GEN"
python3 - <<'EOF'
import re, pathlib
bad = []
for f in pathlib.Path("openwiki").rglob("*.md"):
    for t in re.findall(r"\]\(([^)#\s]+)", f.read_text(encoding="utf-8")):
        if "://" in t or t.startswith("mailto:"):
            continue
        if not (f.parent / t).resolve().exists():
            bad.append(f"{f}: {t}")
print("\n".join(bad) or "links-ok")
EOF
```

- [ ] **Step 9: Size and repo gates**

```bash
set -o pipefail; GEN=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-openwiki; cd "$GEN"
du -sh openwiki; git ls-files openwiki | wc -l
python3 scripts/docs_lint.py && python3 scripts/generate_docs_index.py --check; echo "exit=$?"
```
Record the size. Flag anything over 2 MB to the owner; that is judgement, not a gate. Expected: `Docs lint passed.` and `exit=0`.

## Task C2.3: Status line, referrers, commit, PR

- [ ] **Step 1.** In `openwiki/README.md`, replace the "**Status:** still not generated (as of 2026-07-27) …" sentence with "**Status:** generated <date> with OpenWiki <version> (<provider/model>); reviewed in PR #<n>." Keep the rest of the paragraph.

- [ ] **Step 2 (only if S-C2-3 is signed).** Update the referrer wording that P4 Task 13 made "stub" at `docs/00_architecture_plans_index.md:58` and `AGENT.md:20` so it says the map is generated and advisory. Branch A §14 d4 licenses only *leaving* those references standing, not rewording them, so this edit is owner-gated. If S-C2-3 is unsigned, leave both lines as they are, drop them from Step 3's pathspecs, and flag the now-stale "stub" wording in the PR. **Do not** touch `CLAUDE.md:65-67`.

- [ ] **Step 3.** Regenerate the index and commit:

```bash
set -o pipefail
GEN=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-openwiki; cd "$GEN"
python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py --link-graph
P="openwiki/README.md docs/00_architecture_plans_index.md AGENT.md docs/INDEX.md docs/_link_graph.json"   # S-C2-3 unsigned: drop docs/00_architecture_plans_index.md and AGENT.md
git add -- $P && git diff --cached --name-only    # only those
git commit -m "docs: record OpenWiki generation status and referrers" -- $P
python3 scripts/docs_lint.py && python3 scripts/generate_docs_index.py --check; echo "exit=$?"
```
Push; the PR body contains the Task C2.2 outputs. **STOP** for the owner to merge. Program acceptance: `git ls-files openwiki | wc -l` > 1 on main after merge.

---

# Group G-C3a: HC-M06 extraction eval card

`feature_list.json:71-74` (main@40f590e = A = B), verbatim verification steps:
> "Golden-set pytest suite runs in CI with explicit thresholds",
> "Eval card records metric, dataset version, and date for each run"

**What must be decided, because the steps are vague.** Each row is a **proposal**. It binds only once S-C3-1 is signed, and S-C3-1 names M06-1…M06-6. M06-4 (the threshold margin) additionally needs S-C3-2:

| # | Question | Plan's proposal |
|---|---|---|
| M06-1 | Which fields? | analyte, unit, date. Description `:69`: "precision/recall on analyte, unit, date extraction" |
| M06-2 | Match rule | multiset keys: `(analyte,)`, `(analyte, unit)`, `(analyte, date)`. Analyte is the whitespace-collapsed lowercase of `analyte_raw`; date is `collected_at` ISO or `null` |
| M06-3 | "runs in CI" | a file under `src/backend/tests/`, collected by the existing `backend-tests` job (`ci.yml` B@7b2ff1f `:50-51` runs `scripts/run-backend-tests.sh`). No new job |
| M06-4 | Threshold values | measured baseline minus the margin in O-C3-1 (S-C3-2). Never lowered |
| M06-5 | "for each run" | a card run-log row per recorded run (date, dataset version, parser version, counts, command). A test fails when the card's current block disagrees with what the code measures ("generated, not hand-typed", branch B roadmap C2/E1) |
| M06-6 | PDFs | rendered at test time from `manifest.json` by a stdlib writer: no binaries in git, no new dependency. Table-layout PDFs are not in v1 (the `_extract_from_table` path is not covered; stated on the card) |

## Task C3a.0: Worktree, preconditions, measurement
- [ ] **Step 1: Create the worktree and measure.** Use Task C1.0 Steps 1 and 5 verbatim, with `WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-gc3a` and branch `feat/gc3a-extraction-eval-card`. Also check:
  - `git grep -n -i "hc_extr\|HC-EXTR\|extraction_golden\|eval-cards/extraction" -- src docs/agentic` → none (`no-collision`);
  - S-C3-1 is signed; otherwise **STOP**.

## Task C3a.1: Golden set and PDF writer (HC-EXTR-001)

**Files:** create `src/backend/tests/support/minimal_pdf.py`, `src/backend/tests/fixtures/extraction_golden/manifest.json`, and `src/backend/tests/test_extraction_golden.py`.

**Interfaces**
- Produces:
  - `minimal_pdf(pages: list[list[str]]) -> bytes`;
  - `MANIFEST: dict` with keys `dataset_version: str`, `synthetic: bool`, and `documents: list[{id, pages, expected: list[{analyte, unit, date|None}]}]`.

- [ ] **Step 1: Write the test first**

```python
"""HC-M06 extraction golden set (HC-EXTR-NNN).

Synthetic, fictional lab reports rendered to real PDFs at test time and run
through ExtractModule.extract_from_pdf (pdfplumber). Precision/recall per field,
thresholds from the measured baseline (never lowered), and a check that the eval
card at docs/agentic/eval-cards/extraction.md matches what the code measures.
"""

from __future__ import annotations

import asyncio
import io
import json
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

import pdfplumber
import pytest

from modules.extract import ExtractModule
from tests.support.minimal_pdf import minimal_pdf

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "extraction_golden"
MANIFEST = json.loads((GOLDEN_DIR / "manifest.json").read_text(encoding="utf-8"))
CARD = Path(__file__).resolve().parents[3] / "docs" / "agentic" / "eval-cards" / "extraction.md"
FIELDS = ("analyte", "unit", "date")
IDENTIFIER_LABELS = re.compile(r"(?i)\b(patient|name|dob|birth|mrn|ssn|address|phone|email)\b")
THRESHOLDS: dict[str, tuple[float, float]] = {}   # (min precision, min recall), set in Task C3a.2


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def test_hc_extr_001_golden_set_is_synthetic_and_renders():
    assert MANIFEST["synthetic"] is True
    assert re.fullmatch(r"\d{4}\.\d{2}-v\d+", MANIFEST["dataset_version"])
    ids = [d["id"] for d in MANIFEST["documents"]]
    assert len(ids) == len(set(ids)) >= 8
    for doc in MANIFEST["documents"]:
        lines = [line for page in doc["pages"] for line in page]
        assert not [l for l in lines if IDENTIFIER_LABELS.search(l)], doc["id"]
        with pdfplumber.open(io.BytesIO(minimal_pdf(doc["pages"]))) as pdf:
            text = _norm("\n".join(p.extract_text() or "" for p in pdf.pages))
        for line in lines:
            assert _norm(line) in text, (doc["id"], line)
```

- [ ] **Step 2: RED.** Run `"$PY" -m pytest tests/test_extraction_golden.py -p no:cacheprovider -q`. Expected: a collection error, `ModuleNotFoundError: No module named 'tests.support.minimal_pdf'`.

- [ ] **Step 3: Writer** (`tests/support/minimal_pdf.py`, prototyped; fact 5)

```python
"""Stdlib-only PDF writer for synthetic extraction fixtures (HC-M06).

One Helvetica text line per string, one page per list. Enough for pdfplumber's
text extraction; draws no ruling lines, so table-layout PDFs are out of scope.
"""

from __future__ import annotations

import io


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def minimal_pdf(pages: list[list[str]]) -> bytes:
    objects: list[bytes] = []
    font_id = 3 + 2 * len(pages)
    kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(len(pages)))
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
    for i, lines in enumerate(pages):
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {4 + 2 * i} 0 R >>".encode()
        )
        ops = ["BT", "/F1 11 Tf", "14 TL", "50 740 Td"] + [f"({_escape(l)}) Tj T*" for l in lines] + ["ET"]
        stream = "\n".join(ops).encode("latin-1")
        objects.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(out.tell())
        out.write(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    out.write("".join(f"{o:010d} 00000 n \n" for o in offsets).encode())
    out.write(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return out.getvalue()
```

- [ ] **Step 4: Manifest** (`tests/fixtures/extraction_golden/manifest.json`; set `dataset_version` to `<YYYY.MM>-v1` of the execution month). The coverage per document:
  - `lab_01`: colon lines; the collection label beats "Reported".
  - `lab_02`: no-colon lines; ISO date.
  - `lab_03`: CBC units; full month name.
  - `lab_04`: DD-Mon-YYYY; a `(<100)` range.
  - `lab_05`: two pages with different dates, plus "Page N of 2" bait.
  - `lab_06`: undated, with units outside the hard-coded list.
  - `lab_07`: abbreviated month; mEq/L and IU/L.
  - `lab_08`: ISO with time; pg/mL and fL.

```json
{
  "dataset_version": "2026.10-v1",
  "synthetic": true,
  "documents": [
    {"id": "lab_01", "pages": [["Synthetic Lab Report - fictional data", "Reported: 03/20/2024", "Collection Date: 03/15/2024", "Glucose: 95 mg/dL (70-100)", "Hemoglobin A1c: 6.1 % (4.0-5.6) H", "Potassium 5.8 mmol/L (3.5-5.1) H"]],
     "expected": [{"analyte": "glucose", "unit": "mg/dL", "date": "2024-03-15"}, {"analyte": "hemoglobin a1c", "unit": "%", "date": "2024-03-15"}, {"analyte": "potassium", "unit": "mmol/L", "date": "2024-03-15"}]},
    {"id": "lab_02", "pages": [["Synthetic Chemistry Panel - fictional data", "Collected: 2023-11-02", "Sodium 141 mmol/L (135-145)", "Chloride 103 mmol/L (98-107)", "BUN 18 mg/dL (7-20)", "Creatinine 1.4 mg/dL (0.6-1.2) H"]],
     "expected": [{"analyte": "sodium", "unit": "mmol/L", "date": "2023-11-02"}, {"analyte": "chloride", "unit": "mmol/L", "date": "2023-11-02"}, {"analyte": "bun", "unit": "mg/dL", "date": "2023-11-02"}, {"analyte": "creatinine", "unit": "mg/dL", "date": "2023-11-02"}]},
    {"id": "lab_03", "pages": [["Synthetic CBC - fictional data", "Date of Service: March 5, 2024", "WBC 3.1 K/uL (4.0-11.0) L", "RBC 4.6 M/uL (4.2-5.9)", "Hemoglobin: 11.2 g/dL (12.0-16.0) L", "Platelets 250 K/uL (150-400)"]],
     "expected": [{"analyte": "wbc", "unit": "K/uL", "date": "2024-03-05"}, {"analyte": "rbc", "unit": "M/uL", "date": "2024-03-05"}, {"analyte": "hemoglobin", "unit": "g/dL", "date": "2024-03-05"}, {"analyte": "platelets", "unit": "K/uL", "date": "2024-03-05"}]},
    {"id": "lab_04", "pages": [["Synthetic Lipid Panel - fictional data", "Specimen Collected: 05-Feb-2024", "Total Cholesterol: 212 mg/dL (125-200) H", "LDL Cholesterol: 162 mg/dL (<100) H", "HDL Cholesterol: 48 mg/dL (40-60)", "Triglycerides: 150 mg/dL (0-150)"]],
     "expected": [{"analyte": "total cholesterol", "unit": "mg/dL", "date": "2024-02-05"}, {"analyte": "ldl cholesterol", "unit": "mg/dL", "date": "2024-02-05"}, {"analyte": "hdl cholesterol", "unit": "mg/dL", "date": "2024-02-05"}, {"analyte": "triglycerides", "unit": "mg/dL", "date": "2024-02-05"}]},
    {"id": "lab_05", "pages": [["Synthetic Liver Panel - fictional data", "Page 1 of 2", "Collection Date: 01/10/2024", "ALT 45 U/L (7-56)", "AST 38 U/L (10-40)"], ["Page 2 of 2", "Collection Date: 01/24/2024", "ALT 61 U/L (7-56) H", "Albumin: 4.1 g/dL (3.5-5.0)"]],
     "expected": [{"analyte": "alt", "unit": "U/L", "date": "2024-01-10"}, {"analyte": "ast", "unit": "U/L", "date": "2024-01-10"}, {"analyte": "alt", "unit": "U/L", "date": "2024-01-24"}, {"analyte": "albumin", "unit": "g/dL", "date": "2024-01-24"}]},
    {"id": "lab_06", "pages": [["Synthetic Iron Studies - fictional data", "Ferritin: 12 ng/mL (15-150) L", "Iron 60 ug/dL (60-170)", "TSH 2.1 mIU/L (0.4-4.0)"]],
     "expected": [{"analyte": "ferritin", "unit": "ng/mL", "date": null}, {"analyte": "iron", "unit": "ug/dL", "date": null}, {"analyte": "tsh", "unit": "mIU/L", "date": null}]},
    {"id": "lab_07", "pages": [["Synthetic Electrolytes - fictional data", "Drawn on: Aug 14, 2023", "Bicarbonate: 24 mEq/L (22-29)", "Calcium 9.4 mg/dL (8.5-10.2)", "Alkaline Phosphatase: 130 IU/L (44-147)"]],
     "expected": [{"analyte": "bicarbonate", "unit": "mEq/L", "date": "2023-08-14"}, {"analyte": "calcium", "unit": "mg/dL", "date": "2023-08-14"}, {"analyte": "alkaline phosphatase", "unit": "IU/L", "date": "2023-08-14"}]},
    {"id": "lab_08", "pages": [["Synthetic Vitamin Panel - fictional data", "Specimen Date: 2024-06-01T08:30", "Vitamin B12: 410 pg/mL (200-900)", "MCV 88 fL (80-100)", "Vitamin D 18 ng/mL (30-100) L"]],
     "expected": [{"analyte": "vitamin b12", "unit": "pg/mL", "date": "2024-06-01"}, {"analyte": "mcv", "unit": "fL", "date": "2024-06-01"}, {"analyte": "vitamin d", "unit": "ng/mL", "date": "2024-06-01"}]}
  ]
}
```

- [ ] **Step 5: GREEN.** `-k hc_extr_001` → `1 passed`. **Break it** (mode (c), `manifest.json` is owned): add `"Patient Name: Test"` to a `lab_01` line → red with `('lab_01', ...)`; restore from the backup copy. **What the test would fail to notice:** layout realism (real lab PDFs use tables and columns), and identifiers phrased without a label word.

## Task C3a.2: Scoring and thresholds (HC-EXTR-002)

- [ ] **Step 1: Add scoring plus the test** (append to `test_extraction_golden.py`)

```python
@lru_cache(maxsize=1)
def _score() -> dict[str, dict[str, int]]:
    totals = {f: {"tp": 0, "fp": 0, "fn": 0} for f in FIELDS}
    for doc in MANIFEST["documents"]:
        result = asyncio.run(ExtractModule().extract_from_pdf(io.BytesIO(minimal_pdf(doc["pages"])), doc["id"]))
        for field in FIELDS:
            def exp_key(e):
                return (_norm(e["analyte"]),) if field == "analyte" else (_norm(e["analyte"]), e[field])
            def got_key(o):
                if field == "analyte":
                    return (_norm(o.analyte_raw),)
                return (_norm(o.analyte_raw), o.unit if field == "unit" else o.collected_at)
            expected = Counter(exp_key(e) for e in doc["expected"])
            got = Counter(got_key(o) for o in result.observations)
            tp = sum((expected & got).values())
            totals[field]["tp"] += tp
            totals[field]["fp"] += sum(got.values()) - tp
            totals[field]["fn"] += sum(expected.values()) - tp
    return totals


@pytest.mark.parametrize("field", FIELDS)
def test_hc_extr_002_precision_recall_meet_thresholds(field):
    c = _score()[field]
    assert field in THRESHOLDS, f"no threshold recorded for {field}; measured {c}"
    precision = c["tp"] / (c["tp"] + c["fp"]) if (c["tp"] + c["fp"]) else 0.0
    recall = c["tp"] / (c["tp"] + c["fn"])
    min_p, min_r = THRESHOLDS[field]
    assert precision >= min_p, f"{field}: precision {precision:.2f} < {min_p} ({c}); never lower the bar"
    assert recall >= min_r, f"{field}: recall {recall:.2f} < {min_r} ({c}); never lower the bar"
```

- [ ] **Step 2: RED + measure.** Run `-k hc_extr_002`. Expected: 3 failures of the form `AssertionError: no threshold recorded for analyte; measured {'tp': …}`. Record the three dicts. The prototype on Windows 3.13.7 gave `{'tp': 26, 'fp': 0, 'fn': 2}` for each field. **The executor's D9 measurement is authoritative.** If it differs from the prototype, record both; recurring-failures #4.

- [ ] **Step 3: Set the thresholds.** **STOP** here if S-C3-2 is unsigned, and show the owner the Step 2 measurements. Apply the rule S-C3-2 records. The proposal is measured − 0.05, floored to 2 decimals. With the prototype numbers that gives P = 1.00 → 0.95 and R = 0.93 → 0.88:
  ```python
  THRESHOLDS = {"analyte": (0.95, 0.88), "unit": (0.95, 0.88), "date": (0.95, 0.88)}
  ```
  Replace these with values derived from the D9 measurement. Add a module-docstring table of the measured numbers, as in the precedent at `test_visit_note_extraction.py:7-21`.

- [ ] **Step 4: GREEN + break it.** `-k hc_extr_002` → `3 passed`. **Break it** (mode (a): `modules/extract.py` is read-only here, so monkeypatch it in-process and never edit it):
  ```bash
  set -o pipefail
  WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-gc3a; PY="$HOME/venvs/asclexis-311/bin/python"; cd "$WT/src/backend"
  "$PY" -c 'import sys, pytest; from modules.extract import ExtractModule; ExtractModule._normalize_date_str = staticmethod(lambda raw: None); sys.exit(pytest.main(["tests/test_extraction_golden.py", "-q", "-p", "no:cacheprovider", "-k", "hc_extr_002"]))'; echo "exit=$?"
  git -C "$WT" diff --exit-code -- src/backend/modules/extract.py && echo extract-untouched
  ```
  Expected: `date` fails with `recall 0.00 < …`, then `exit=1`, then `extract-untouched`. **What it would fail to notice:** OCR (`extract_from_scanned_pdf`), table layouts, value and flag correctness (not scored; stated on the card).

## Task C3a.3: Eval card (HC-EXTR-003) and docs links

- [ ] **Step 1: Test** (append)

```python
def _card_block() -> dict:
    text = CARD.read_text(encoding="utf-8")
    m = re.search(r"<!-- eval-card:current:start -->\s*```json\s*(\{.*?\})\s*```\s*<!-- eval-card:current:end -->", text, re.S)
    assert m, f"{CARD} has no eval-card:current block"
    return json.loads(m.group(1))


def test_hc_extr_003_eval_card_matches_measurement():
    measured = {
        "dataset_version": MANIFEST["dataset_version"],
        "parser_version": ExtractModule().parser_version,
        "fields": _score(),
    }
    assert _card_block() == measured, "eval card is stale; record a run with:\n" + json.dumps(measured, indent=2)
    assert f"| {MANIFEST['dataset_version']} |" in CARD.read_text(encoding="utf-8"), "no run-log row for this dataset version"
```

- [ ] **Step 2: RED.** Expected: `FileNotFoundError: … docs/agentic/eval-cards/extraction.md`.

- [ ] **Step 3: Create the card** `docs/agentic/eval-cards/extraction.md`:

````markdown
# Extraction Eval Card (HC-M06)

**Owner:** repository owner
**Refresh Trigger:** `tests/test_extraction_golden.py::test_hc_extr_003` fails (dataset, parser or extractor changed).

What it measures: precision/recall of `ExtractModule.extract_from_pdf` on a synthetic, fictional
golden set (`src/backend/tests/fixtures/extraction_golden/manifest.json`) for three fields —
analyte, unit, collection date. Thresholds live in the test and are never lowered.

## Current (checked by HC-EXTR-003; paste the test's output, do not hand-edit numbers)

<!-- eval-card:current:start -->
```json
<paste the JSON printed by HC-EXTR-003>
```
<!-- eval-card:current:end -->

## Run log

| Date | Dataset | Parser | analyte tp/fp/fn | unit tp/fp/fn | date tp/fp/fn | Interpreter | Command |
|---|---|---|---|---|---|---|---|
| <date> | <dataset_version> | 0.1.0 | … | … | … | Python 3.11.x (D9) | `python -m pytest tests/test_extraction_golden.py -q` |

## Not covered

- Table-layout PDFs (`_extract_from_table`), scanned/OCR PDFs, images.
- Value, reference range and flag correctness.
- Known miss: lines whose unit is outside `ExtractModule.VALUE_PATTERN` (for example `ug/dL`, `mIU/L`) are dropped whole (lab_06).
- Environment: counts are CI's (Linux, Python 3.11). `pdfplumber>=0.10.0` is unpinned, so another version may differ.
````

- [ ] **Step 4: GREEN.** Run `-k hc_extr_003`. Paste the printed JSON into the block and fill the run-log row with today's date and the exact counts, then re-run → `1 passed`. **Break it** (mode (c)): bump `dataset_version` in the manifest → red with the stale message; restore from the backup copy. If the numbers differ between local and CI, the CI run's numbers win. Record both in the run log (Review Focus 5).

- [ ] **Step 5: Links.** In `docs/agentic/evals.md` "Concrete evals", append item 8:

```markdown
8. **Extraction eval (HC-M06)** — `cd src/backend && python -m pytest tests/test_extraction_golden.py -q` scores `ExtractModule.extract_from_pdf` on a synthetic golden set (analyte/unit/date precision and recall, thresholds never lowered). Numbers and run log: [eval-cards/extraction.md](eval-cards/extraction.md).
```
Then run `python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py --link-graph`.

## Task C3a.4: Full suite, gates, commit, PR

- [ ] **Step 1.** Run Task C1.5 Step 1 in `$WT` (expected collected = START + 5). Then run `python3 scripts/docs_lint.py && python3 scripts/generate_docs_index.py --check && python3 scripts/feature_list_lint.py; echo "exit=$?"` → `exit=0`.
- [ ] **Step 2: Commit** (two commits):

```bash
set -o pipefail
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-gc3a; cd "$WT"
PY="$HOME/venvs/asclexis-311/bin/python"
N=$(cd "$WT/src/backend" && "$PY" -m pytest tests/ --collect-only -q -p no:cacheprovider 2>&1 | tail -1 | grep -oE '^[0-9]+'); echo "collected=$N"
grep -nE "tests collected|differs from [0-9]+|[0-9]+ collected" "$WT/CLAUDE.md" "$WT/AGENT.md"
# Edit by hand: replace ONLY the numbers in "**<n> backend tests collected.**" and "differs from <n>" (CLAUDE.md)
# and the "<n> collected" token (AGENT.md) with $N. Leave every pass-count ("all <n> pass", "<n> pass in CI") as is; flag it in the PR.
git -C "$WT" diff -U0 -- CLAUDE.md AGENT.md    # only those numeric tokens changed
P="src/backend/tests/support/minimal_pdf.py src/backend/tests/fixtures/extraction_golden/manifest.json src/backend/tests/test_extraction_golden.py docs/agentic/eval-cards/extraction.md docs/agentic/evals.md docs/INDEX.md docs/_link_graph.json CLAUDE.md AGENT.md"
git add -- $P && git diff --cached --name-only    # exactly those 9
git commit -m "feat(extract): HC-M06 synthetic lab-PDF golden set, thresholds and eval card" -- $P
```
There is one commit: HC-EXTR-003 needs the card, so splitting tests and card would leave a red commit.
The PR notes that `feature_list.json` HC-M06 can move to `completed` in a follow-up ledger commit once merged; that ledger is shared with W-1/P8. **STOP** for the owner to merge.

---

# Group G-C3b: HC-M07 observability baseline

`feature_list.json:83-87` (main@40f590e = A = B), verbatim verification steps:
> "tests/monitoring/test_correlation.py asserts log records carry the correlation ID",
> "tests/security/test_audit_middleware.py asserts the audit JSON payload carries it",
> "e2e smoke hits /health and asserts 200 + status field"

**Proposed here, not decided.** Every item below is owner-gated as **S-C3-3** (O-C3-2/3). Task C3b.0 stops if S-C3-3 is unsigned:
- **Mechanism.** A record factory rather than a handler filter (fact 7).
- **Placement.** Installed in `create_app()`, which is synchronous and testable. The lifespan is shared with P2/W-4/W-7.
- **Value outside a request.** `"-"`.
- **Not built.** The JSON formatter and any root-level or handler change.

## Task C3b.0: Worktree, preconditions, measurement
- [ ] **Step 1.** Use Task C1.0 Steps 1 and 5 verbatim, with `WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-gc3b` and branch `feat/gc3b-observability-baseline`. Also check:
  - `git grep -n -i "hc_obsv\|HC-OBSV\|logging_setup\|E2E-HEALTH" -- src` → none;
  - S-C3-3 (mechanism, placement, no formatter) is signed. Otherwise **STOP**. Do not substitute a handler `Filter` or a lifespan placement without a new owner answer.
  - `grep -n "notification_scheduler" src/backend/main.py` → at least 1 (P2 in);
  - S-C3-1 is signed.

## Task C3b.1: Record factory (HC-OBSV-001, 002, 004)

**Files:** create `src/backend/core/logging_setup.py`; modify `src/backend/main.py` and `src/backend/tests/monitoring/test_correlation.py`.

**Interfaces**
- Produces `install_correlation_logging() -> None` (idempotent). Every `LogRecord` then carries `correlation_id: str`, which is the current request's ID or `"-"`.

- [ ] **Step 1: Tests** (append to `tests/monitoring/test_correlation.py`; add `import logging`, `import logging.config`, `from pathlib import Path` at the top)

```python
ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


@pytest.fixture
def restore_logging_state():
    root = logging.getLogger()
    factory, handlers, level = logging.getLogRecordFactory(), root.handlers[:], root.level
    yield
    logging.setLogRecordFactory(factory)
    root.handlers[:] = handlers
    root.setLevel(level)


async def _log_inside_and_outside_request(correlation_id: str) -> list[logging.LogRecord]:
    records: list[logging.LogRecord] = []

    class _ListHandler(logging.Handler):
        def emit(self, record):
            records.append(record)

    log = logging.getLogger("hc.obsv.test")
    handler = _ListHandler(level=logging.DEBUG)
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)
    log.propagate = False
    try:
        async def app(scope, receive, send):
            log.warning("inside request")
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        scope = make_scope([(b"x-correlation-id", correlation_id.encode())])
        await CorrelationIdMiddleware(app)(scope, make_receive, ResponseCapture())
        log.warning("outside request")
    finally:
        log.removeHandler(handler)
        log.propagate = True
    return records


@pytest.mark.asyncio
async def test_hc_obsv_001_log_record_carries_request_correlation_id(restore_logging_state):
    from core.logging_setup import install_correlation_logging
    install_correlation_logging()
    cid = str(uuid.uuid4())
    inside, outside = await _log_inside_and_outside_request(cid)
    assert inside.correlation_id == cid
    assert outside.correlation_id == "-"


@pytest.mark.asyncio
async def test_hc_obsv_002_correlation_survives_alembic_logging_reset(restore_logging_state):
    """alembic.ini fileConfig runs at startup and on every vault open
    (migrations/*/env.py); it replaces root handlers and their filters."""
    from core.logging_setup import install_correlation_logging
    install_correlation_logging()
    logging.config.fileConfig(ALEMBIC_INI, disable_existing_loggers=False)
    cid = str(uuid.uuid4())
    inside, _ = await _log_inside_and_outside_request(cid)
    assert inside.correlation_id == cid


def test_hc_obsv_004_create_app_installs_correlation_logging(restore_logging_state):
    import main
    logging.setLogRecordFactory(logging.LogRecord)
    main.create_app()
    record = logging.getLogRecordFactory()("x", logging.INFO, __file__, 1, "m", None, None)
    assert getattr(record, "correlation_id", None) == "-"
```

- [ ] **Step 2: RED.** `-k hc_obsv` in that file → 001/002 fail with `ModuleNotFoundError: No module named 'core.logging_setup'`; 004 fails with `assert None == '-'`.

- [ ] **Step 3: Implementation**

```python
"""Correlation IDs on every log record (HC-M07).

A process-wide LogRecord factory, not a handler Filter: alembic.ini's fileConfig
runs at startup and on every vault open and replaces the root handlers (and any
filters on them). The factory survives that. Local-only: no handler, format or
level is changed here, and nothing is sent anywhere.
"""

from __future__ import annotations

import logging

from monitoring.correlation import get_correlation_id

_MARKER = "_asclexis_correlation"


def install_correlation_logging() -> None:
    previous = logging.getLogRecordFactory()
    if getattr(previous, _MARKER, False):
        return

    def factory(*args, **kwargs) -> logging.LogRecord:
        record = previous(*args, **kwargs)
        record.correlation_id = get_correlation_id() or "-"
        return record

    setattr(factory, _MARKER, True)
    logging.setLogRecordFactory(factory)
```
In `main.py`, add `from core.logging_setup import install_correlation_logging` beside the other `core` imports (`:14-16`). Make `install_correlation_logging()` the first statement of `create_app()` (`:86-88`).

- [ ] **Step 4: GREEN + break it.** `-k hc_obsv` → `3 passed`.
  - Break A (mode (c), `core/logging_setup.py` is new and owned): replace the factory with a `Filter` added to `logging.getLogger().handlers` → 001 red (child-logger handler) and 002 red (wiped).
  - Break B: remove the call in `create_app()` → 004 red. Use mode (b) after the Task C3b.4 commit, because `main.py` is shared (P2/W-4/W-7).
  - Revert both. **What these would fail to notice:** that production INFO records never reach a handler (F-2). They only prove records *carry* the ID.

## Task C3b.2: Audit payload (HC-OBSV-003)

- [ ] **Step 1: Test** (append to `tests/security/test_audit_middleware.py`; add `import uuid`)

```python
@pytest.mark.asyncio
async def test_hc_obsv_003_audit_payload_carries_correlation_id(caplog):
    from monitoring.correlation import CorrelationIdMiddleware
    app = CorrelationIdMiddleware(SecurityAuditMiddleware(passthrough_app))  # main.py order: CorrelationId wraps Audit
    cid = str(uuid.uuid4())
    good = make_scope(method="POST", path="/api/v1/documents")
    good["headers"] = [(b"x-correlation-id", cid.encode())]
    hostile = make_scope(method="POST", path="/api/v1/documents")
    hostile["headers"] = [(b"x-correlation-id", b"evil\nSECURITY_AUDIT: forged")]
    with caplog.at_level(logging.INFO, logger="security.audit_middleware"):
        await app(good, make_receive, ResponseCapture())
        await app(hostile, make_receive, ResponseCapture())
    payloads = [json.loads(r.getMessage().split("SECURITY_AUDIT: ", 1)[1])
                for r in caplog.records if r.getMessage().startswith("SECURITY_AUDIT: ")]
    assert payloads[0]["correlation_id"] == cid
    assert payloads[1]["correlation_id"] != "evil\nSECURITY_AUDIT: forged"
    uuid.UUID(payloads[1]["correlation_id"])  # regenerated (monitoring/correlation.py:48-53)
```

- [ ] **Step 2: RED.** `KeyError: 'correlation_id'`.
- [ ] **Step 3: Implementation.** In `security/audit_middleware.py`, add `from monitoring.correlation import get_correlation_id`, and add `"correlation_id": get_correlation_id(),` to the `event_data` dict (`:60-67`). The value is a validated UUID, not PHI (C-REDACT-3).
- [ ] **Step 4: GREEN + break it.** → `1 passed`. **Break it** (mode (b), after the Task C3b.4 commit): use `"correlation_id": ""` → red. **What it would fail to notice:** a future reorder of middleware in `main.py` (the test composes the order by hand).

## Task C3b.3: E2E health smoke (E2E-HEALTH-001)

- [ ] **Step 1: Spec** `src/frontend/e2e/health-smoke.spec.ts`

```ts
import { test, expect } from '@playwright/test';
import { E2E_API_URL } from './support/auth';

test('E2E-HEALTH-001: /health returns 200 with a status field', async ({ request }) => {
  const response = await request.get(E2E_API_URL.replace(/\/api\/v1$/, '/health'));
  expect(response.status()).toBe(200);
  const body = await response.json();
  expect(body.status).toBe('healthy');
});
```
`E2E_API_URL` is exported at `e2e/support/auth.ts:3`. `/health` returns `{"status": "healthy", …}` (`monitoring/health.py:23-30`). The existing `global-setup.ts:19-35` only checks `response.ok()`.

- [ ] **Step 2: Run** (Windows PowerShell)

```powershell
Set-Location C:\Users\DangT\Documents\GitHub\HealthCentral-gc3b\src\frontend
npm ci; if ($LASTEXITCODE -ne 0) { throw "npm ci failed: $LASTEXITCODE" }
npx tsc --noEmit; if ($LASTEXITCODE -ne 0) { throw "tsc failed: $LASTEXITCODE" }
npx vitest run; if ($LASTEXITCODE -ne 0) { throw "vitest failed: $LASTEXITCODE" }
npx playwright test e2e/health-smoke.spec.ts --project chromium; $pw = $LASTEXITCODE; "playwright exit=$pw"
```
Expected: `playwright exit=0`. If the local environment cannot start the web servers or a browser (recurring-failures #4), record **UNMEASURED locally** and rely on CI `e2e-tests`. **Break it** (mode (c), the spec is new and owned): change `'healthy'` to `'ok'` → red; restore from the backup copy.

**Count sequencing (3b minor 7):** this spec adds one Playwright test, so the chromium list moves +1 (28 → 29 on a main-based tree, 30 → 31 on A+B). W-11a Task 11 (PR-4, G-B6) writes the measured Playwright count into the capstone rows. If PR-4 has merged, record `npx playwright test --list --project chromium | Select-Object -Last 1` in the PR body and name the now-stale rows for the orchestrator; this plan does not edit capstone rows.

## Task C3b.4: Full suite, commit, PR

- [ ] **Step 1.** Run Task C1.5 Step 1 in `$WT` (expected collected = START + 4). Check that `grep -rn "basicConfig\|dictConfig\|setLevel" "$WT/src/backend/core/logging_setup.py"` prints nothing: no handler or level change.
- [ ] **Step 2: Commit**

```bash
set -o pipefail
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-gc3b; cd "$WT"
PY="$HOME/venvs/asclexis-311/bin/python"
N=$(cd "$WT/src/backend" && "$PY" -m pytest tests/ --collect-only -q -p no:cacheprovider 2>&1 | tail -1 | grep -oE '^[0-9]+'); echo "collected=$N"
grep -nE "tests collected|differs from [0-9]+|[0-9]+ collected" "$WT/CLAUDE.md" "$WT/AGENT.md"
# Edit by hand: replace ONLY the numbers in "**<n> backend tests collected.**" and "differs from <n>" (CLAUDE.md)
# and the "<n> collected" token (AGENT.md) with $N. Leave every pass-count ("all <n> pass", "<n> pass in CI") as is; flag it in the PR.
git -C "$WT" diff -U0 -- CLAUDE.md AGENT.md    # only those numeric tokens changed
P="src/backend/core/logging_setup.py src/backend/main.py src/backend/security/audit_middleware.py src/backend/tests/monitoring/test_correlation.py src/backend/tests/security/test_audit_middleware.py src/frontend/e2e/health-smoke.spec.ts CLAUDE.md AGENT.md"
git add -- $P && git diff --cached --name-only   # exactly those 8
git commit -m "feat(monitoring): HC-M07 correlation IDs on log records and audit payload, /health e2e smoke" -- $P
```
The PR body carries F-2 and O-C3-4 prominently. **STOP** for the owner to merge.

---

# Group G-C4: HC-M08a packaging decision record

`feature_list.json:96` HC-M08a verification step, verbatim: "Decision doc exists, passes docs lint, and names a chosen path with rationale". The program stop gate: "a decision doc before any build".

## Task C4.0: Worktree, measurement
- [ ] **Step 1.** Use Task C1.0 Steps 1 and 5, with `WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-gc4` and branch `docs/gc4-packaging-decision`. Collection only; the acceptance is that the collected count is unchanged. Then run `grep -n "embedding_model_path" src/backend/core/config.py` and record whether W-8 has landed.

## Task C4.1: Measure the inputs (each result, or UNMEASURED plus its command)

- [ ] **Step 1.** Run on the D9 venv and on Windows, and record the outputs verbatim:

```bash
set -o pipefail
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-gc4; PY="$HOME/venvs/asclexis-311/bin/python"
SP=$("$PY" -c "import site; print(site.getsitepackages()[0])")
du -sh "$SP"/torch "$SP"/llama_cpp "$SP"/sqlcipher3* "$SP"/sentence_transformers "$SP"/transformers "$SP" 2>&1
"$PY" -c "import torch; print(torch.__version__)"      # sentence-transformers pulls torch; requirements.txt comment says torch is optional
cd "$WT/src/backend" && "$PY" scripts/download_models.py list   # GGUF tier sizes are *labels* in the script (B@7b2ff1f :77,:85,:99), not measurements
grep -n "embedding" "$WT/src/backend/scripts/download_models.py" | head -5   # W-8 landed? (absent at B@7b2ff1f :5-18: GGUF/Ollama commands only)
du -sb "$WT/src/backend/models/embeddings/all-MiniLM-L6-v2" 2>&1              # only if W-8 landed and was run; W-8 measured 91,578,415 bytes
```
```powershell
Set-Location C:\Users\DangT\Documents\GitHub\HealthCentral-gc4\src\frontend
npm ci; if ($LASTEXITCODE -ne 0) { throw "npm ci failed" }
npm run build; if ($LASTEXITCODE -ne 0) { throw "build failed: $LASTEXITCODE" }
"{0:N0} bytes" -f (Get-ChildItem dist -Recurse | Measure-Object Length -Sum).Sum
```

- [ ] **Step 2: Verify the embedding model's licence and notices.** W-8 (`:106`) leaves the base-model licence and whether upstream ships a LICENSE/NOTICE file **UNMEASURED**. This is a developer measurement that uses the network, not a product path. Run:

```bash
set -o pipefail
PY="$HOME/venvs/asclexis-311/bin/python"
"$PY" - <<'PYEOF'
from huggingface_hub import hf_hub_download, list_repo_files

def show(repo, rev=None):
    """Print licence facts for one repo; return its base_model repo id or None."""
    try:
        files = list_repo_files(repo, revision=rev)
        card = open(hf_hub_download(repo, "README.md", revision=rev), encoding="utf-8").read()
    except Exception as exc:  # no network, gated, missing card
        print(repo, rev, "UNMEASURED:", type(exc).__name__, exc)
        return None
    print(repo, rev, "LICENSE/NOTICE files:", [f for f in files if f.upper().startswith(("LICENSE", "NOTICE"))])
    front = card.split("---")[1] if card.startswith("---") else ""
    lines = [l for l in front.splitlines() if l.split(":")[0].strip() in ("license", "base_model")]
    print(repo, rev, "front matter:", lines)
    base = [l.split(":", 1)[1].strip() for l in lines if l.split(":")[0].strip() == "base_model"]
    return base[0] if base and base[0] else None

# The candidate W-8 proposes (owner-gated as S-C4-5); swap it if S-C4-5 names another.
base = show("sentence-transformers/all-MiniLM-L6-v2", "1110a243fdf4706b3f48f1d95db1a4f5529b4d41")
if base:
    show(base)
else:
    print("base_model: UNMEASURED (not declared in the card front matter, or the first read failed)")
PYEOF
```
One process reads both the model and its base model, and prints UNMEASURED for any read it cannot complete. Record every output verbatim:
- the `license:` value of the model;
- the `license:` value of the base model;
- the exact LICENSE/NOTICE file names, or `[]`.

If a fetch fails (no network, gated repo), write **UNMEASURED** plus this command. The decision record states only what this step measured. **Which files the installer must carry, and under what terms, is S-C4-4 (owner).** This plan does not decide it.

## Task C4.2: Write the decision record

- [ ] **Step 1.** Create `docs/plans/<YYYY-MM-DD>-packaging-decision.md` with these mandatory sections. Every fact carries a `path:line` or a Task C4.1 output.
  1. Header (`Last Updated`, `Owner`, `Refresh Trigger`, `Status: PROPOSED — owner decision pending`). Sources: HC-M08a, audit §21 Q4, D8, D8-delivery.
  2. **Options.**
     - (A) Portable folder plus launcher: FastAPI serves the built SPA via `StaticFiles`, same-origin.
     - (B) PyInstaller + Tauri.
     - (C) PyInstaller + Electron.
     - Branch A §13 "Prepared recommendation: portable folder first" is an input, not a conclusion.
  3. **Criteria matrix** (rows × A/B/C), with an evidence column:
     - SQLCipher native bundling (`sqlcipher3-binary`, `requirements.txt:32`);
     - llama-cpp native bundling (`:52`);
     - torch size (Task C4.1);
     - WeasyPrint's native GTK stack on Windows (`:108`; absent on the Windows 3.13 install per the W-2 plan fact 8);
     - code signing (SmartScreen; cost; owner);
     - total size;
     - update and uninstall path;
     - **data directory**: `app_data_path` is CWD-relative `Path("data")` (`core/config.py:159-163` B@7b2ff1f), so a packaged app needs an absolute per-user directory. That is a later product change, touching the vault, backup and delete-sweep paths;
     - **source-relative paths** that the bundle must carry or re-point: `api/feedback.py:66` (`rl_exports`, see F-1), `core/migrations.py:31,46` (`alembic.ini` + `migrations/`), `modules/model_integrity.py:42` (repo-root `config/model_manifest.json`);
     - **origin/CORS**: local mode allows only `:3000` origins (`main.py:101`). (A) is same-origin. (B) and (C) need a new origin, which is a C-LOCAL-3 change;
     - **bind host** 127.0.0.1 (C-LOCAL-3; `main.py:164-166`, `dev.ps1:719`);
     - **DPAPI portability**: sealed keys are user- and machine-bound (`core/security.py:314-323`). "Portable" must not promise vault portability across machines beyond the password-sealed copy;
     - GGUF delivery stays a user-triggered download (C-LOCAL-1's sanctioned call; D8 covers only the embedding model).
  4. **How the installer bundles the embedding model (mandatory; D8 + D8-delivery).**
     - **Status of the fetch mechanism depends on W-8** (Task C4.1 Step 1 grep).
       - If W-8 has landed, the build step runs `download_models.py embedding` on the build machine. Network is used at build time only, never at runtime.
       - If W-8 has not landed, the record labels this mechanism **"proposed (W-8, not on main)"**. `download_models.py` at B@7b2ff1f `:5-18` lists only GGUF/Ollama commands, and W-8 (`:15`) describes the embedding command as proposed.
     - **Which model: a PROPOSAL, owner-gated as S-C4-5.**
       - D8 approves only "the small embedding model" ([owner-decisions](../capstone-report/owner-decisions-2026-09-27.md):21). It names no model, revision, hash or file set.
       - The candidate is W-8's own *proposal* (W-8 `:34`, `:103`): `models/embeddings/all-MiniLM-L6-v2/`, 11 files, 91,578,415 bytes, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, `model.safetensors` sha256 `53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db`.
       - The record writes these values as "proposed (W-8), pending S-C4-5". It never writes them as the installer's contents.
       - If S-C4-5 names another model or revision, the record takes that one. The size and hash are then re-measured, never carried over.
     - The launcher sets `EMBEDDING_MODEL_PATH` to an **absolute** path inside the install directory. W-8 resolves relative paths against `Path(__file__)`, which PyInstaller one-file relocates to a temporary extraction directory.
     - The build verifies the sha256. Runtime failure stays fail-closed (W-8).
     - Licence facts come **only** from Task C4.1 Step 2: the model's and base model's `license:` values and any upstream LICENSE/NOTICE files, each measured or marked UNMEASURED. W-8 finding 5 (the model card says `apache-2.0`, not MIT) is carried as a lead, not a verified fact. Which licence and notice files the installer carries, and on what terms, is **S-C4-4 (owner, unsigned)**. The record does not mandate them.
     - No weights in git.
     - Acceptance for HC-M08b/c: re-run HC-EMB-002 against the packaged app with the network blocked (W-8 `:72`).
     - **Not licensed by D8:** GGUF tiers, and HC-M11's future cross-encoder. Branch A §14 d2: "Its model-distribution prerequisite is still unbuilt". D8 covers only "the small embedding model". The record states that bundling either one would need its own owner decision. It does not decide against bundling them.
  5. **Recommendation**, with rationale and the consequences for HC-M08b/c/d (what each must change: data dir, `StaticFiles`, CORS, paths).
  6. **Owner decisions (unsigned):**
     - S-C4-1: the chosen path.
     - S-C4-2: data-directory location.
     - S-C4-3: code signing (yes/no, who pays).
     - S-C4-4: licence notices for redistributed models and libraries.
     - S-C4-5: the exact embedding model and revision to bundle. W-8's candidate is `all-MiniLM-L6-v2@1110a243…`. It must match the revision signed under canonical owner gate **EMB-REV** (W-8's sign-off line; 3a M-6).
  7. **What this record does not decide:** no build is authorised; HC-M08b starts only after S-C4-1.

- [ ] **Step 2: Gates**

```bash
set -o pipefail
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-gc4; cd "$WT"
python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py --link-graph
python3 scripts/docs_lint.py && python3 scripts/generate_docs_index.py --check && python3 scripts/feature_list_lint.py; echo "exit=$?"
```
Expected: `exit=0`.

## Task C4.3: Commit and PR

- [ ] **Step 1.**

```bash
set -o pipefail
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-gc4; cd "$WT"; D="docs/plans/$(date +%F)-packaging-decision.md"
test -e "$WT/$D" && echo record-ok   # STOP if missing: the record was created on another day, so set D to its real name
git add -- "$D" docs/INDEX.md docs/_link_graph.json && git diff --cached --name-only   # exactly 3
git commit -m "docs: HC-M08a packaging decision record (owner decision pending)" -- "$D" docs/INDEX.md docs/_link_graph.json
```
Push and open the PR. **STOP**: the owner signs S-C4-1 in the record.

## Task C4.4: After S-C4-1 is signed (separate commit)

- [ ] **Step 1.** In `feature_list.json`, set HC-M08a `"status": "completed"`. Run `python3 scripts/feature_list_lint.py` → exit 0. Then `git commit -m "docs: mark HC-M08a decision recorded" -- feature_list.json`, after `git diff --cached --name-only` shows only `feature_list.json`.

---

## Measured acceptance (per group)

| Group | Command | Expected |
|---|---|---|
| C1 | `pytest tests/ --collect-only -q` | START + 16 |
| C1 | full suite | failures ⊆ START_FAILURES, each named |
| C1 | `pytest tests/test_export_artifact_persistence.py -q` | `16 passed` |
| C1 | `grep -rn "_summary_store\|_packet_store\|_fhir_store" src/backend/api` | none |
| C1 | `git diff --stat origin/main...HEAD -- src/backend/modules/redaction.py src/backend/core/auth.py src/backend/core/profile_database.py src/backend/tests/support/routes.py` | empty |
| C1 | `python -c "from main import app"` | no error |
| C1, C3a, C3b | `git diff origin/main...HEAD -U0 -- CLAUDE.md AGENT.md` | only the collected-count tokens changed, to the `--collect-only` number measured at that commit; no pass-count sentence changed unless a named-environment pass count is in the PR |
| C1 | flow re-walk (Task C1.5 Step 3) | **UNMEASURED** until done by hand; record it |
| C2 | Task C2.2 Steps 1-9 | `scope-ok`, `d10-ok`, `counts-ok`, `secrets-ok`, `links-ok`, no `MISSING`, lint `exit=0` |
| C2 | `git ls-files openwiki \| wc -l` on main after merge | > 1 |
| C3a | collected | START + 5; `tests/test_extraction_golden.py` `5 passed` |
| C3a | card | HC-EXTR-003 green in CI (Linux 3.11); local numbers recorded |
| C3b | collected | START + 4 (HC-OBSV-001/002/004 in monitoring, 003 in security) |
| C3b | Playwright E2E-HEALTH-001 | exit 0 locally, or **UNMEASURED locally** + CI `e2e-tests` green |
| C4 | docs gates | `exit=0`; collected unchanged |
| C4 | record | names a chosen path **only after** S-C4-1; before that it names a recommendation |

## Stop gates

1. Any Task X.0 precondition misses (post-P1, D9 venv, dependency phase, owner go line).
2. **G-C1:**
   - an open PR touches `api/export.py` or `api/profiles.py`;
   - W-2 has not landed;
   - the profile head is not the one P6 left;
   - any `assert` would be removed from an existing test;
   - a change would reach the delete flow, `core/auth.py`, `core/profile_database.py` or `redaction.py`.
3. **Any group:** a red test for a reason other than the documented RED line; a failure outside START_FAILURES that the group does not explain.
4. **G-C2:** the tool edited `CLAUDE.md`/`AGENT.md`/`AGENTS.md` and S-C2-2 is unsigned → reject those hunks, never merge them. Any invariant restated weaker → request changes.
5. **G-C3a:** a threshold would need lowering; any real document or identifier enters the fixtures.
6. **G-C3b:** any change to handlers, levels or formatters would be needed (F-2 is out of scope).
7. **G-C4:** anyone proposes building packaging before S-C4-1.

## Rollback

- **G-C1: never run a bare `alembic downgrade`.**
  - Why not: `alembic.ini` defaults to the master chain (`src/backend/alembic.ini:11-28` @40f590e). The profile chain refuses to run without `vault_path` and a key in `config.attributes` (`migrations/profile/env.py:84-89`). Obtaining a real vault's key means unsealing it, which is auth/encryption and ask-first.
  - **Before merge:** `gh pr close <n> --delete-branch`, then `git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral worktree remove /mnt/c/Users/DangT/Documents/GitHub/HealthCentral-gc1`. No product vault has been migrated: the only vault the branch opened is the throwaway re-walk profile, which Task C1.5 Step 3 deletes.
  - **After merge: partial code revert.**
    1. On a new branch, `git revert <C1.5 docstring sha, if any> <C1.3 sha> <C1.1 sha>` → PR.
    2. **Keep the C1.2 commit** (model, migration `014`, reset tuple, head literals). The table is additive and unused after the revert. Every vault already opened by the merged code is stamped `014`, and a codebase without `014` cannot open it.
    3. Proven by the Task C1.2 Step 7 rehearsal: `Can't locate revision` on the pre-G-C1 tree, success on the C1.2-only tree.
    4. The rows that stay behind are redacted derived copies inside the encrypted vault. They are still erased by the crypto-erase vault sweep and cleared by test reset.
  - **Removing the table later** is a new forward migration (`drop_table` in `upgrade`, recreate in `downgrade`) under its own plan. `run_profile_migration` applies it on the next vault open with the key the app already holds, so there is no manual key handling. Downloads then 404 as they do today; no source data is touched.
- **G-C2:** before merge, `gh pr close <n> --delete-branch`. After merge, `git revert <sha>` on a new branch → PR; `openwiki/README.md` returns to "still not generated".
- **G-C3a / G-C3b:** before merge, `gh pr close <n> --delete-branch`. After merge, `git revert <sha>…` → PR. G-C3a has no product code. G-C3b's record factory is installed only by `create_app()`, so a revert removes it. The reverted commits' collected-count tokens in `CLAUDE.md`/`AGENT.md` revert with them. Re-measure and state the count in the revert PR.
- **G-C4:** before merge, `gh pr close <n> --delete-branch`. After merge, revert the record, and the ledger status commit if S-C4-1 had flipped it.

## Owner sign-offs (unsigned)

- [ ] **S-C1-1** — G-C1 go. Persist doctor-summary, visit-prep/pinboard and FHIR artifacts as rows in a new profile-vault table `export_artifact` (profile migration `014`), kept until profile deletion. Download requires the vault unlocked. `ExportArtifact` is added to P7's reset tuple in `api/profiles.py` (that line only). Nine existing direct-call tests change mechanism with every assertion kept. Four of them, HC-PKT-014/015 and HC-FHIR-103/104, **remain legacy direct-call status checks**. They are not relied on (F-6), and their 403/404 behaviour is covered over HTTP by HC-EXPA-003/004/005/010. The rollback keeps migration 014. No list UI and no TTL now (O-C1-1…3). Signed: ________ Date: ______
- [ ] **S-C1-2** — Amend the `api/profiles.py:799-803` docstring (one sentence, Task C1.5 Step 4). Signed: ________ Date: ______
- [ ] **S-C2-1** — The owner runs `openwiki --init` in a clean worktree and accepts sending tracked repository source to the chosen LLM API (O-C2-1). Signed: ________ Date: ______
- [ ] **S-C2-2** — Tool-made edits to `CLAUDE.md` / `AGENT.md` / new `AGENTS.md`: reject (default) / accept as listed: ________. Signed: ________ Date: ______
- [ ] **S-C2-3** — After generation, reword the `openwiki/` referrer lines at `AGENT.md:20` and `docs/00_architecture_plans_index.md:58` to "generated, advisory" (Task C2.3 Step 2). Signed: ________ Date: ______
- [x] **S-C3-1** — G-C3 go for the minimal scope above: the HC-M06 golden set, scoring and eval card per proposals M06-1…M06-6; the HC-M07 audit-payload key and the /health e2e smoke. The HC-M07 mechanism itself is S-C3-3. Signed: Owner, chat 2026-10-04 (owner-decisions row S-C3-1) Date: 2026-10-04
- [ ] **S-C3-2** — HC-M06 threshold rule: measured − 0.05, floored, never lowered (or: ________). Signed: ________ Date: ______
- [x] **S-C3-3** — HC-M07 deviations from the ledger text: a record factory instead of a handler Filter, installed in `create_app()` rather than the lifespan; `"-"` outside a request; no JSON formatter; no level or handler change. Signed: Owner, chat 2026-10-04 (owner-decisions row S-C3-3) Date: 2026-10-04
- [ ] **S-C4-1…5** — carried inside the packaging decision record (Task C4.2). S-C4-5 selects the embedding model and revision that the installer bundles. D8 approves only "the small embedding model", so until S-C4-5 is signed the revision, hash and file set are a proposal.
- [ ] **F-1 follow-up** — open a new item for `rl_exports/` erase and ignore: yes / no. Signed: ________ Date: ______

## Commit plan (summary)

| Group | Commit | Pathspecs |
|---|---|---|
| C1 | `feat(export): failing tests for export-artifact persistence (HC-EXPA, PRIV-08)` | `src/backend/tests/test_export_artifact_persistence.py`, `CLAUDE.md`, `AGENT.md` (collected-count tokens only) |
| C1 | `feat(export): export_artifact profile table and migration 014` | `models/export_artifact.py`, `models/__init__.py`, `migrations/profile/versions/014_export_artifacts.py`, `api/profiles.py`, `tests/test_care_tasks.py` (under `src/backend/`) |
| C1 | `feat(export): persist … in the profile vault` | `api/export.py`, `api/pinboards.py`, `tests/test_visit_prep_packet.py`, `tests/test_fhir_export.py` |
| C1 | `docs: note vault-held export artifacts …` (S-C1-2 only) | `src/backend/api/profiles.py` |
| C2 | owner: `docs: generate OpenWiki repository map (owner run)` | `openwiki` (directory add only after `git status --short openwiki` shows only generated files) |
| C2 | `docs: record OpenWiki generation status and referrers` | `openwiki/README.md`, `docs/00_architecture_plans_index.md`, `AGENT.md`, `docs/INDEX.md`, `docs/_link_graph.json` |
| C3a | `feat(extract): HC-M06 synthetic lab-PDF golden set, thresholds and eval card` | as in Task C3a.4 (9 paths incl. `CLAUDE.md`/`AGENT.md` count tokens) |
| C3b | `feat(monitoring): HC-M07 …` | as in Task C3b.4 (8 paths incl. `CLAUDE.md`/`AGENT.md` count tokens) |
| C4 | `docs: HC-M08a packaging decision record …`; then `docs: mark HC-M08a decision recorded` | as in Tasks C4.3 and C4.4 |

Every commit follows the same routine: `git add -- <paths>`, then `git diff --cached --name-only`, then `git commit -m … -- <paths>`. Never `git add -A` or `git add .`, and never `git reset` shared work (C-GATE-3). Commit messages end with the session's attribution lines if the orchestrator requires them.

## Recurring-failures recheck

| # | Mode | Applies | Concrete recheck in this plan |
|---|---|---|---|
| 1 | Green suite that could not fail | yes, all | every test has a documented RED and a Task C1.4 / C3a / C3b break-it row. HC-EXPA-005 passes before the change and is proved only by its break-it row. HC-EXPA-007 scans file **contents**, not names. Every status assertion this plan relies on goes over HTTP. The legacy direct-call 403/404 checks HC-PKT-014/015 and HC-FHIR-103/104 **remain direct calls** after G-C1. They are recorded as F-6, are not relied on, and have HTTP coverage in HC-EXPA-003/004/005/010. Suite baselines record every failing node ID from the full log, never from a `tail`. Break-its follow the three-mode protocol and never `git checkout --` the phase worktree |
| 2 | Fix creates the next bug | yes, C1 | the flow re-walk (Task C1.5 Step 3) covers generate → download → restart → locked 403 → re-login → download → backup → delete. The 9 migrated tests keep every assert (`grep '^-\s+assert'` check) |
| 3 | Figures asserted | yes | every number here names its command and interpreter. The prototype counts are labelled context. Thresholds are derived from the executor's D9 measurement |
| 4 | Environment-dependent results | yes, C3a/C3b | the card states that CI numbers win, and that pdfplumber is unpinned. Playwright is UNMEASURED locally until run |
| 5 | Gates in a contaminated tree | yes | one worktree per group. Lint and index checks run in that worktree, not in the owner's dirty tree |
| 6 | Documented commands nobody ran | yes, C2/C4 | `openwiki` commands come from `openwiki/README.md:31-35`. The executor records the version and output. The `download_models.py list` output is recorded, not quoted |
| 7 | SQL three-valued logic | low | `_load_artifact` compares non-null columns only (`kind`, `profile_id` are `NOT NULL`) |
| 8 | Stale guidance as authority | yes | `api/profiles.py:799-803` (S-C1-2); the openwiki referrer wording (Task C2.3); the MIT licence claim (W-8 finding 5, carried into G-C4); F-5 (D8-delivery missing from the owner record) |

## Execution record (filled by the executor)

| Group | Start SHA | Interpreter / OS | START collected / failures | RED output | Break-it results | END collected / failures | PR |
|---|---|---|---|---|---|---|---|
| C1 | | | | | | | |
| C2 | | | n/a (docs) | n/a | Task C2.2 outputs | | |
| C3a | | | | | | | |
| C3b | | | | | | | |
| C4 | | | | n/a | n/a | | |
