# Backlog Closure Plan — every open item, sequenced

> Status: **PLAN ONLY — no product code changes in this document's commit**
> Date: 2026-09-08
> Owner: Project Lead
> Refresh Trigger: An item below is completed, or a new open item is identified
> Authority: [CLAUDE.md](../../CLAUDE.md) and [AGENT.md](../../AGENT.md) override everything here.
> Trackers this plan feeds: [docs/features/TASK_LIST.md](../features/TASK_LIST.md) and [feature_list.json](../../feature_list.json)

Input: a repository audit dated 2026-09-08 listing partial features, open tickets,
and pending milestones. Every claim in it was re-verified against the tree before
being planned — §1 records what survived that check and what did not. Each item
below carries the evidence it was planned from, so the next agent can start
without re-deriving state.

---

## 1. Audit verification pass

Verified 2026-09-08 by reading the code. An audit is a lead, not a finding.

| Audit claim | Verdict | Evidence |
|---|---|---|
| `MED-CORR-001` backend complete, frontend still on the heuristic | **Confirmed, and narrower than stated** | Endpoint at `api/medications.py:452-540`. But the frontend service layer is *already done*: `fetchMedicationCorrelations` (`services/medications.ts:141`) and `useMedicationCorrelations` (`:350`) exist and are exported through the barrel. Only the two pages are unwired — `TrendsDashboard.tsx:33,198` and `MedicationDetail.tsx:42` still import `utils/correlation`. |
| `SEC-RECOV-001` frontend unwired; existing profiles can never get a code | **Confirmed** | `issueRecoveryCode` (`services/profiles.ts:60`) and `useIssueRecoveryCode` (`:264`) exist and are exported (`services/index.ts:59`); no page imports either. Backend route `POST /profiles/{id}/recovery-code` is live. |
| `SQL-FK-001`: pragma enabled nowhere, all CASCADEs inert | **Confirmed** | Only two repo-wide hits, both comments saying it is off (`api/profiles.py:914`, `tests/test_profile_deletion.py:408`). Full audit: [2026-09-08-sql-fk-001-foreign-key-audit.md](2026-09-08-sql-fk-001-foreign-key-audit.md). |
| `CITE-AGENT-001`: agent tools return no page/bbox | **Confirmed** | `nodes/draft.py:104,110` builds every `locator` from `observation_id`. |
| `HC-M07`: correlation ID absent from log records, no JSON log format | **Confirmed** | `monitoring/correlation.py` stores the ID in a contextvar and a response header only; no `logging.Filter` exists, and `core/config.py` has no log-format setting. |
| OpenWiki not generated | **Confirmed** | `openwiki/` contains only the hand-written `README.md`. |
| `INGEST-FHIR-001` open — "zero structured ingest exists today" | **STALE — the tracker row is wrong** | HC-M23 shipped `modules/import_structured.py`, which parses FHIR R4 Bundles (`Observation`, `MedicationStatement`, `Condition`) and lab CSV. The row's premise was overtaken by work that landed after it was written. Real remaining scope is much smaller — see §5. |
| 1245 backend tests, 6 CI jobs, no TODO/FIXME in product code | **Confirmed, measured** | 6 jobs in `.github/workflows/ci.yml`; zero TODO/FIXME/XXX/HACK in non-test backend code. Test count measured after installing the backend dependencies: **1245 collected, 1244 passed, 1 failed** — the failure is `test_api_rag_index_002b`, the documented env-only embedding case (`sentence-transformers` deliberately not installed). Matches `AGENT.md`'s baseline exactly. |

Two things the audit did not surface, both found while verifying `SQL-FK-001`:

- **A live data-retention defect.** `CarePlanTask.source_quote` holds verbatim
  clinician text and is never deleted when its source document is deleted, even
  though `delete_document` deletes `DocumentEntity` rows for exactly that reason
  (`api/documents.py:1846-1851`). Planned as §3.1 — it is not an FK problem and
  should not wait for the pragma.
- **An orphan class the pragma would fix for free.** `api/documents.py:867`
  deletes chunks with a core `delete()` statement, which bypasses ORM cascade and
  leaves `embeddings` rows behind. Detail in the FK audit, §4.1.

---

## 2. Execution order

Sequenced by risk-adjusted value, not by the audit's priority labels. Items in the
same band are independent and can be parallelized.

| Band | Items | Rationale |
|---|---|---|
| A | §3.1 care-task quote retention, §4 `MED-CORR-002`, §4 `SEC-RECOV-002` | A privacy defect and two shipped-but-unreachable backends. Highest value per line changed. |
| B | §3 `SQL-FK-001`, §6 `HC-M07` | Correctness and diagnosability foundations. `SQL-FK-001` depends on §3.1 landing first. |
| C | §5 `INGEST-FHIR-001`, §7 `HC-M06`, §8 `CITE-AGENT-001`, §12 `HC-M11` | Feature and rigor work, each self-contained. `HC-M11` was approved 2026-09-08 and scheduled here ("after band A"); it still cannot start until its non-GGUF model-distribution dependency is built. |
| D | §9 OpenWiki, §10 `HC-M09`, §11 `HC-M02` | Tooling and verification chores; no product risk. |
| E | §13 `HC-M08a-d` | Large, and strictly sequential — `HC-M08a`'s decision spike gates everything after it. |

**Gates — all four cleared 2026-09-08.** The decisions that blocked parts of this
plan have been made; see §14 for what was decided and what each one licenses. The
approvals are scoped: `HC-M11` is approved to be *built*, not to be turned on by
default, and §3.1's retention answer is approved as specified, not as a general
licence to delete derived data.

Every item below follows the repo's TDD convention: **T1** writes the check and
observes it fail, **T2** is the smallest change that makes it pass, **T3**
stabilizes and documents. Definition of done is [AGENT.md](../../AGENT.md#definition-of-done)
— run the commands, read the output.

---

## 3. `SQL-FK-001` — Foreign key enforcement

Full constraint-by-constraint audit, with the decision for each of the 20 FKs:
[2026-09-08-sql-fk-001-foreign-key-audit.md](2026-09-08-sql-fk-001-foreign-key-audit.md).
That audit is the deliverable the ticket named as its prerequisite; what follows
is the implementation sequence it implies.

### 3.1 Prerequisite — care-task provenance and quote retention

**Do this first, and ship it separately.** It fixes a live defect and it unblocks
the pragma.

**Decided 2026-09-08 (owner):** keep the task, null its provenance, clear
`source_quote` — the recommendation from FK audit §4.2. The reasoning to preserve
if this is ever revisited: a follow-up the patient still has to do does not stop
being real because they deleted the PDF, but the verbatim clinician text has no
right to outlive its source. This is a decision about *derived verbatim text*
specifically; it does not license deleting other derived data on document delete.

- **T1** — In `tests/test_care_plan_tasks.py` (or a new module, `HC-FKPREP-0NN`):
  create a document, extract a care task from it, delete the document through
  `route_client` (HTTP, per CLAUDE.md — a direct handler call cannot see a broken
  `Depends`), then assert the task still exists, `source_document_id is None`, and
  `source_quote is None`. Watch it fail on the quote assertion.
- **T2** — In `delete_document` (`api/documents.py:1812`), before deleting the
  document, `UPDATE care_plan_task SET source_document_id=NULL,
  source_entity_id=NULL, source_quote=NULL` for rows pointing at it.
  ~~Mirror it in the reprocess path (`:1193`).~~ **Corrected during
  implementation — do NOT mirror this into reprocess.** There the document still
  exists, so the retention rationale does not apply, and
  `get_care_task_candidates` (`api/care_tasks.py:182-199`) keys duplicate
  detection on `(source_document_id, source_quote)`; clearing either would
  resurface every already-accepted task as a fresh candidate on each reprocess.
  The original instruction would have fixed one bug and created another one
  layer over — see [recurring-failures.md §2](../agentic/recurring-failures.md).
- **T3** — Add a row to `docs/compliance/data-privacy.md` recording that
  document deletion clears derived verbatim text. Check whether any other table
  stores verbatim document text with no delete path — this is the second instance
  of the pattern, so it deserves a sweep, not a point fix.

**Shipped 2026-09-08.** Tests `HC-CAREQ-001..003` in `tests/test_documents_api.py`
(HC-CAREQ-001 observed failing first, with the defect's own message: "verbatim
clinician text outlived the deleted document"). HC-CAREQ-003 is the scoping guard
— a broad `UPDATE care_plan_task` with no `WHERE` would pass HC-CAREQ-001 while
stripping every other document's tasks. Suite: 1248 collected, 1247 passed, 1
documented env-only failure. **The T3 sweep found a third instance,
`FEEDBACK-SNAP-001`, which is not fixed here** — see §15.

### 3.2 Migration — align the four mismatched constraints

- **T1** — Test asserting `PRAGMA foreign_keys` is ON for a freshly opened profile
  connection *and* a master connection, plus one test per changed constraint
  (P14/P15 cascade on document delete; P16/P17 null on document/entity delete).
  All fail before the change.
- **T2** — One profile migration (linear `down_revision`, per the dual-migration
  invariant) using **Alembic batch mode** — SQLite cannot `ALTER` a constraint, so
  the table is rebuilt, copied, and swapped. `document_category.doc_id` and
  `document_entity.doc_id` → `CASCADE`; `care_plan_task.source_document_id` and
  `source_entity_id` → `SET NULL`. Update the models to match in the same commit.
- **T3** — Verify the migration is reversible against a populated vault (rebuild
  migrations lose data silently when a column list is wrong; check row counts
  before and after, not just that it ran).

### 3.3 Flip the pragma

- **T2** — `PRAGMA foreign_keys=ON` in a `connect` event listener on **both**
  engines: `core/database.py:44` and the existing SQLCipher key hook at
  `core/profile_database.py:314`. Per-connection, not per-session — a single
  startup call covers exactly one pooled connection and silently misses the rest.
- **T3** — Run the **full** backend suite, not the FK tests. The point of this
  change is that previously-tolerated orphan writes start raising; the suite is
  the only place that surfaces which ones. Expect failures in tests that create
  child rows without parents. Each such failure is a real finding — fix the test's
  data setup, or the code path it exposed. **Do not** relax a constraint to make a
  test pass; that would invert the entire point of the change.
- Keep every existing explicit child-delete (`api/profiles.py:916`,
  `api/documents.py:1850-1851`, `_prune_document_pin_targets`). They are now
  belt-and-braces rather than the mechanism, and `pinboard_item`'s polymorphic
  `item_id` can never be an FK, so its manual prune stays load-bearing forever.

---

## 4. `MED-CORR-002` / `SEC-RECOV-002` — wire two shipped backends

Both are the same shape: the endpoint, the service function, the React Query hook,
and the tests exist; nothing renders them. Narrow, high-value work.

### 4.1 `MED-CORR-002` — correlations wiring

The stated goal of `MED-CORR-001` was *one* definition of the overlap rule. Two
still exist, and they disagree: the backend defaults to `verified_only=True`
(`api/medications.py:463` — "an unverified extraction is not a fact to correlate
against"), while `utils/correlation.ts` filters on no such thing. Until the pages
switch, the app shows the looser answer.

- **T1** — Extend `src/frontend/src/__tests__/CorrelationContract.test.ts`: assert
  `MedicationDetail` renders correlated observations from a mocked
  `useMedicationCorrelations` and that an *unverified* observation does not appear.
  The second assertion fails today, because the heuristic has no verified filter.
- **T2** — Replace `findObservationsDuringMedication` in `MedicationDetail.tsx:42`
  and `findActiveMedications` in `TrendsDashboard.tsx:33,198` with the hook.
  Surface `excluded_undated_count` — the backend counts undated observations
  deliberately rather than dropping them, and hiding that count in the UI throws
  away the honesty the endpoint was built for.
- **T3** — Delete `utils/correlation.ts` and its now-dead contract tests once no
  importer remains (`ChartExport.test.tsx:130` mocks it — update that too). A
  deleted second implementation is the only proof the drift cannot recur. Keep
  `toOverlayPeriod`'s dosage-label formatting if the overlay still needs it — move
  it next to the component rather than leaving the module alive for one helper.

### 4.2 `SEC-RECOV-002` — recovery-code entry point in Settings

`RecoverProfile.tsx` tells the user a recovery code "can only be created while you
can still sign in" — and no signed-in surface creates one. The instruction is
currently impossible to follow. Backfill for pre-existing profiles is the whole
point.

- **T1** — A `SettingsPage` test asserting: a "Recovery code" section exists; it
  requires the password before issuing; the returned code is displayed exactly
  once with a copy affordance and an explicit "this will not be shown again"
  warning; and a re-issue warns that the previous code stops working. Fails —
  there is no such section.
- **T2** — Add the section to `SettingsPage.tsx` calling `useIssueRecoveryCode`.
  Read `has_recovery_code` (already on the profile response,
  `api/profiles.py:138,149`) to choose "Create" vs "Replace" wording. **Never
  persist the code** anywhere — not in Zustand, not in `localStorage`, not in a
  query cache that survives navigation. It is shown once, from the mutation
  result, and then it is gone.
- **T3** — Playwright spec covering create → copy → reload → confirm the code is
  no longer displayed. Update `docs/user-guide/` with the backfill instructions,
  and re-read `RecoverProfile.tsx`'s copy so it now describes a path that exists.

---

## 5. `INGEST-FHIR-001` — rescope, then implement the remainder

The tracker row's premise ("zero structured ingest exists today") was overtaken by
HC-M23. **First action is to correct the row**, then plan the actual gap. Verified
remaining scope:

1. **`DiagnosticReport` is not handled.** `import_structured.py:365-390` handles
   `Observation`, `MedicationStatement`, and `Condition` only. Report-level
   resources carry panel grouping and collection metadata the repo already models.
2. **LOINC codes are discarded.** `_map_fhir_observation` identifies analytes from
   `code.text` (`:372`), so a bundle's `code.coding` LOINC — exact, unambiguous,
   OCR-free, the ticket's core argument — is thrown away. `normalize.py:129`
   already has a `loinc_code` field waiting for it.

- **T1** — Golden bundle fixtures: one with a `DiagnosticReport` wrapping contained
  `Observation`s, one where `code.text` is absent but `code.coding` carries a LOINC
  code (today: silently skipped as `unparseable_observation`), one with a LOINC
  code whose `code.text` disagrees with the repo's canonical analyte name.
- **T2** — Extend `_map_fhir_observation` to prefer LOINC over text, and add a
  `DiagnosticReport` branch. Keep the module's purity contract: no I/O, no network,
  no LLM, stdlib only, `_cap` on every free-text field. Imports stay unverified.
- **T3** — Confirm the reprocess-rejection guard (HC-FIMP-067) still holds for the
  new resource type, and that a hostile bundle (deeply nested, huge fields,
  contained-resource cycles) is capped rather than parsed forever.

---

## 6. `HC-M07` — Observability baseline

Most of the stack exists: `CorrelationIdMiddleware`, `/health`, `MetricsCollector`,
`TimingMiddleware`, DB audit logging. Three gaps remain, all small.

- **T1** — `tests/monitoring/test_correlation.py` asserting a log record emitted
  during a request carries the correlation ID; `tests/security/test_audit_middleware.py`
  asserting the audit JSON payload carries it; an e2e step asserting `/health`
  returns 200 with a `status` field.
- **T2** — New `core/logging_setup.py` with a `logging.Filter` reading
  `get_correlation_id()` (`monitoring/correlation.py:20`) onto each record, plus an
  optional stdlib-only JSON formatter behind a `core/config.py` setting, default
  off. Wire the filter in `main.py`'s lifespan.
- **T3** — Confirm the invariant holds: this is local-only diagnosis, no telemetry,
  no network. And confirm the formatter cannot widen PHI exposure — logs are not
  covered by `modules/redaction.py`, so a JSON formatter that starts serializing
  `extra` dicts wholesale is a new leak path. Log the ID, not the payload.

---

## 7. `HC-M06` — Extraction eval card

The flagship Data Science artifact, and the largest of the "rigor" items.

- **T1** — Build a synthetic labeled golden set under
  `src/backend/tests/fixtures/extraction_golden/`: generated lab PDFs with known
  analyte/unit/date ground truth. **Synthetic only** — no real patient documents
  enter the repo, ever. Cover the failure modes the repo has actually hit: date
  formats, collection-label priority, mixed units, undated results.
- **T2** — A pytest module computing precision/recall per field with explicit
  thresholds, wired into CI. It must fail on regression, not just report.
- **T3** — `docs/agentic/eval-cards/extraction.md` recording metric, dataset
  version, and date per run. Link it from `docs/agentic/evals.md` and
  `docs/00_architecture_plans_index.md`, or DOC-011 will flag it as an orphan.

Set thresholds from the measured baseline, and do not "fix" a miss by lowering
one. A number that only ever goes up because the bar moves down is not a metric.

---

## 8. `CITE-AGENT-001` — page numbers on agent-path citations

The RAG path deep-links citations to a document region; the agent path cannot,
because the tools never return the provenance. Enhancement, not regression.

- **T1** — Agent-path test asserting a citation for an observation extracted from a
  PDF carries `source_page`. Fails — `draft.py:104,110` uses the row id as locator.
- **T2** — Widen the return shape of `query_observations` and `compute_trend`
  (`modules/agent/tools/`) to include `source_page`/`source_bbox_json`, then build
  the `Citation.locator` from them in `draft.py`. Tool outputs feed the prompt, so
  any new field must go through `sanitize_untrusted_field` exactly like `analyte`
  and `unit` already do (`RAG-INJ-001`) — a page number is an integer, but a bbox
  JSON blob is attacker-influenced text.
- **T3** — Confirm the frontend renders an agent-path chip identically to a RAG one
  (`CITE-SRC-001` shipped that routing), and that a citation with no page still
  degrades to plain text rather than a dead link.

---

## 9. OpenWiki generation

Blocked on a human, not on code: generation needs an LLM API key and must run
locally, and the output needs review before it lands.

**Decided 2026-09-08 (owner):** the owner runs generation locally and hands over
the diff for review. The references to `openwiki/` in `CLAUDE.md` and `AGENT.md`
therefore stay as-is — they describe intent that is now scheduled rather than
stale guidance. If generation does not happen, revisit: an authority doc pointing
at an empty directory is the exact failure mode recorded as
[recurring-failures.md §8](../agentic/recurring-failures.md).

- Run `npm install -g openwiki && openwiki --init`, then review the **full** diff
  including `CLAUDE.md`/`AGENT.md`/`AGENTS.md`, which OpenWiki may rewrite.
- Reject any generated text that restates a hard invariant less strictly than
  `CLAUDE.md` does. The generated layer is advisory and ranks below `docs/`;
  `openwiki/README.md` already states that ordering — keep that file when
  regenerating.
- Update the "still not generated (as of 2026-07-27)" status line in the same
  commit as the generated output, so the two cannot disagree.
- Only after one reviewed cycle has merged, add the CI workflow — PR-only, never
  auto-merge.

## 10. `HC-M09` — MCP script tools

Implement the tools specified in [docs/agentic/mcp-tools.md](../agentic/mcp-tools.md)
(`run_tests`, `run_lint`, `run_typecheck`, `run_e2e`, `check_docs_versions`) as thin,
credential-free wrappers. Verification is behavioural: each must exit non-zero when
the underlying command fails — spot-check by injecting a failing test, because a
wrapper that always exits 0 is worse than no wrapper. The read-only SQLite/SQLCipher
inspection tool must reject write statements, and must be pointed only at synthetic
dev vaults.

## 11. `HC-M02` — Windows bootstrap verification

Implementation is done (`dev.ps1:361-372`); the milestone is open only because one
manual test has not run: execute `dev.ps1` on a Windows machine **without** Python
and confirm the winget path, the `[Y/n]` prompt, and the fallback messages. Nothing
to build. Either run it and close the milestone, or record explicitly that it is
unverifiable in the current environment — an untested install path should not be
marked complete on the strength of an AST parse.

## 12. `HC-M11` — NLI cross-encoder for faithfulness *(approved)*

**Approved 2026-09-08 (owner), scheduled after band A.** The gate is cleared: it
touches `modules/faithfulness.py` and `modules/verifier_agent.py`, both on
CLAUDE.md's ask-before-touching list, and the owner has authorised the work.

Read the approval narrowly. It licenses *building* the scorer behind a flag that
defaults off — it is not authorisation to change what production faithfulness
scoring does, to alter a threshold, or to touch anything else in those two files.
Any of that is a fresh ask.

**One prerequisite is not built.** `scripts/download_models.py` has no non-GGUF
distribution path, and a cross-encoder is not a GGUF artifact. That comes first,
or there is nothing to load. Do not work around it by fetching the model at
runtime — that would break local-first.

Scope: wire a real cross-encoder into the existing-but-never-fed
`entailment_scores` parameter, and make `use_llm_entailment` route to it instead of
its stub. Additive only — regex scoring stays the floor and the flag defaults off,
so the existing faithfulness and verifier tests must pass **unchanged** with it
off. That is the primary acceptance signal. Prove offline inference from a local
path; a model that reaches the network breaks the local-first invariant regardless
of how good its scores are. Pin the artifact in `config/model_manifest.json`
(`MODEL-INT-001`) — an unpinned model silently invalidates every tuned threshold.

## 13. `HC-M08a-d` — Packaging *(spike first)*

Strictly sequential, and **a-before-b is not negotiable**: `HC-M08a` is a decision
doc (PyInstaller+Tauri vs PyInstaller+Electron vs portable folder + launcher),
judged on SQLCipher and llama-cpp native bundling, model download-on-first-run,
code signing, and size. Prepared recommendation: portable folder first. Nothing in
`b`/`c`/`d` should start before that doc names a chosen path with rationale, or the
project will have built the packaging it then has to justify.

---

## 14. Owner decisions — all four answered 2026-09-08

Recorded here so no future session re-asks, and so the *scope* of each approval
survives longer than the conversation that produced it.

| # | Decision | Answer | What it licenses |
|---|---|---|---|
| 1 | Care-task quote retention (§3.1) | **Keep the task, null its provenance, clear `source_quote`** | The specific change in §3.1, for derived *verbatim text*. Not a general licence to delete derived data on document delete. |
| 2 | `HC-M11` approval (§12) | **Approved, scheduled after band A** | Building the cross-encoder behind a flag that defaults off, in two ask-before-touching files. **Not** changing production scoring behaviour, thresholds, or anything else in those files. Its model-distribution prerequisite is still unbuilt. |
| 3 | `SQL-FK-001` blast radius (§3.3) | **Full: fix the four constraints, then flip the pragma** | Fixing orphan-write failures as the suite surfaces them. Explicitly *not* a licence to relax a constraint or skip a test to get green — that would invert the point of the change. |
| 4 | OpenWiki (§9) | **Owner generates locally; this session reviews the diff** | Leaving the `openwiki/` references in `CLAUDE.md`/`AGENT.md` standing as scheduled intent. Revisit if generation does not happen. |

One consequence worth stating plainly, because it is the riskiest of the four:
decision 3 means the backend suite is expected to go red partway through §3.3.
Each failure is a finding about a real orphan write, and the fix belongs in the
test's data setup or the code path it exposed — never in the constraint. A
session that finds itself weakening an FK to get a green suite has misread this
approval and should stop.

**Baseline now measured** (after the decision, same session): 1245 collected,
1244 passing, 1 documented env-only failure. So the suite is a usable instrument
for §3.3 — the red the pragma produces will be attributable, because the green it
starts from is known. Measure the delta against this baseline, not against a
remembered number.

---

## 15. `FEEDBACK-SNAP-001` — prompt snapshots retain document text *(open)*

Found by the `CARE-QUOTE-001` T3 sweep, 2026-09-08. Recorded rather than fixed,
because it is a different mechanism and the fix is a design decision, not a
mechanic.

`response_feedback.prompt_snapshot` stores "the fully-composed prompt (with
retrieved context) at the time of inference" (`models/response_feedback.py:74-78`).
Retrieved context is document chunk text, so the column holds verbatim document
text — the same class `CARE-QUOTE-001` and the entity-quote deletion both protect.
Deleting a document does not clear it.

Why it is not the same fix:

- **No provenance link.** `response_feedback` has no `doc_id`. There is no way to
  find the rows quoting a given document without scanning text, so the targeted
  `UPDATE` that works for care tasks has nothing to key on.
- **Partly mitigated.** The rows stay inside the encrypted per-profile vault, and
  RL dataset export forces `policy_level="strict"` redaction unconditionally
  (`RL-REDACT-001`), so the export path is already covered.
- **Deleting it costs something real.** The snapshot exists so preference pairs
  can be reconstructed reproducibly; clearing it retroactively degrades the RL
  dataset the feature was built for.

Options, for whoever picks this up: add a `doc_ids` column populated at
composition time so deletion can target it; clear snapshots older than a
retention window; or accept it explicitly and say so in the privacy doc rather
than leaving it undocumented. A written decision either way beats the current
silence — the gap is now noted in `docs/compliance/data-privacy.md`.
