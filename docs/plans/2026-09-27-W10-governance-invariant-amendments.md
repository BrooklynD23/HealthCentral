# W-10 Governance Commit: Invariant Amendments for D3, D4 and D12

**Last Updated:** 2026-10-08
**Owner:** repository owner
**Refresh Trigger:** P1 merges; P4 merges; any of W-2 / W-3 / W-6 merges; any edit to `CLAUDE.md` lines 25 or 59-62; any edit to `docs/compliance/data-privacy.md`
**Status:** IN EXECUTION — Wave 4, branch `docs/w10-governance-amendments` (r5 amendments below)
**Prerequisites:** P0-B and P1 merged to `origin/main`; P4 merged, or a written orchestrator waiver. If Task 0 Step 2 fails before P1 lands, that is the intended STOP, not a plan defect.
**Revision:** r5, 2026-10-08, execution amendments (measured on `origin/main` `777adf5`). Where an older paragraph conflicts with an r5 line, r5 wins.
1. **Gates as answered.** GOV-D11 (Q1) and GOV-BG (Q2) are signed, Q3 is skipped, Q4 and Q5 are answered (§10 cites the owner-decisions rows). `W10_ARGS` is ` --c3 --govbg` (Task 1 Step 5). Hunk C-4 is not applied.
2. **W-6 is merged** (PR #32, `2f0cb6f`). DP-4 uses variant **U**, as the owner's W-10-REST answer says ("merged; conformance unverified"). The DP-4 variant-P blocks and the §3.2 row "Dev bypass exists today" are superseded: they describe code that no longer exists.
3. **Three fold-ins are in scope**, each as its own commit after the governance commit, in the same PR (owner rows W-10-REST and W10-HIPAA): LOCAL-07, DOC-OVERCLAIM (this adds `docs/compliance/hipaa-controls.md` lines `:49` and `:52`; `:169` stays untouched) and CLAUDE-FAILURE-COUNT. Hunks, evidence and assertions: Task 4b.
4. **Commit rule.** The old rule "one commit, two files" becomes: commit 1 plan amendments; commit 2 the governance commit, exactly `CLAUDE.md` + `docs/compliance/data-privacy.md` (Consequence #1 still holds for it); commits 3-5 one per fold-in; then review records and the wave report (§13).
5. **Moved anchors.** Every Before block still matches exactly once (§3.6). The code line numbers in §3.2 are refreshed for W-5 (PR #34) and W-6 (PR #32).
6. **Trackers.** The DP-1 and DP-3 variant-P blocks now cite `docs/capstone-report/implementation-program.md`; the handoff they cited is superseded.
7. **Measurement.** The two full-suite runs become a collect-only run plus `tests/test_docs_lint.py` (a docs-only diff on the 12 GB host); the full suite is reported as skipped.
8. **Codex review.** This amended plan is reviewed by Codex before the hunks are applied (owner row W-10-REST: "Codex reviews the plan before it runs"). Records: `audit/2026-09-25/swarm-2026-09-27/reviews/W10-r5-*`.

**Revision:** r1, 2026-09-27, after the Codex review verdict REVISE:
1. The export inventory is now an AST scan that handles multiline decorators, and it now finds `POST /feedback/export` (§3.5, Task 1 Step 4).
2. Every assertion run uses one `W10_ARGS`.
3. Variant I needs the W-item PR's red-first and break-it evidence.
4. If Q1 is unsigned, `CLAUDE.md:62` stays unchanged as an open owner item.

**Review status:** 4 Codex rounds (round 4 final; no round 5). The round-4 MAJOR was fixed after the last round and was not re-reviewed (owner acceptance required).
**Revision:** r4 + Wave 6, 2026-09-28:
1. Codex r4: merge status of W-2/W-3/W-6 now comes from the item's PR (`gh pr view` + `merge-base --is-ancestor`), not from a test-ID grep. A merged item with missing or renamed tests gets U, never P (Task 1 Steps 2-3, S6).
2. 3a M-3: the break-glass clause is owner-gated again as **GOV-BG** (merges W-6 §11 Q2 and this plan's Q2). D12 names the external runner as a *ModelRunner* exception (Consequence #1); calling break-glass a bypass of "Redaction before anything leaves" is an inference. Unsigned, C-2 and DP-4 quote D12's conditions without calling break-glass a bypass (§1.2, Task 4, §10).
3. Q1 is registered as **GOV-D11**.
**Revision:** r3, 2026-09-27, round-3 findings:
1. The route inventory prints **mounted** paths: the `main.py` prefix, then the `api/__init__.py` `include_router` prefix, then any `APIRouter(prefix=)`, then the decorator path (§3.5, Task 1 Step 4).
2. Q2 is no longer a gate. D12's text licenses naming audited break-glass, so the clause is unconditional, the alternate blocks are removed, and C-2 quotes D12 verbatim.

**Revision:** r2, 2026-09-27, after the Codex review verdict REVISE:
1. The `route_client` evidence is now checked per function with `rc_check.py`, which records the call line (Task 1 Step 3).
2. When an item's code has merged but its evidence is incomplete, the text now says "merged; conformance unverified" (variant **U**), with its own blocks.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (recommended here: 7 small tasks (0-6), one file pair, no code) or superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One governance `docs:` commit that changes exactly two files, `CLAUDE.md` and `docs/compliance/data-privacy.md`, followed in the same PR by one commit per owner-approved fold-in (r5; Task 4b). The governance commit names the owner-approved exceptions to two invariants: CSV/JSON exports (D3) and the external runner (D12). It also records D3 and D4 in the privacy doc. Each claim about behaviour is marked as implemented or as owner-approved but not yet implemented.

**Architecture:** Docs only. `CLAUDE.md` gets **normative** text ("must"): the rule, the named exceptions, and a plain-path pointer to the decision record and the matrix rows that track code conformance. It never claims that code already conforms, so it never needs a status flip. `docs/compliance/data-privacy.md` is **descriptive**, so every behaviour sentence carries a status line: variant **P** (pending) or variant **I** (implemented). Task 1 picks the variant by measurement. No new markdown links are added to either file, which keeps `docs/INDEX.md` and `docs/_link_graph.json` byte-identical (§3.3).

**Tech stack:** Markdown; `scripts/docs_lint.py`; `scripts/generate_docs_index.py --check` (a CI gate, `.github/workflows/ci.yml` docs job); Python 3.11 venv from D9 for the pytest measurement.

**Spec:** handoff §5 W-10 row ([handoff](../../audit/2026-09-25/handoff-2026-09-27-execution.md)), owner-decisions Consequence #1 ([owner decisions](../capstone-report/owner-decisions-2026-09-27.md)).

---

## 1. Approval scope

### 1.1 Verbatim option text (from `owner-decisions-2026-09-27.md`)

| # | Owner's choice | Option text, verbatim |
|---|---|---|
| D3 | Redact doctor summary only | "Doctor summary goes to a third party → redact it (strict). CSV/JSON are the patient's own data export → keep full-fidelity like backups, and amend CLAUDE.md/data-privacy.md to name them as deliberate exceptions." |
| D4 | Label, exclude from RAG | "Trends may show unverified points but visibly marked 'unverified'; legacy RAG cites verified values only (matches the agent path). Docs updated to say so." |
| D12 | Keep, harden | "Keep the opt-in feature as a documented ModelRunner exception, but make strict redaction unconditional (remove the dev bypass; keep break-glass only with audit + UI warning). Amend CLAUDE.md to name the exception." |
| D11 (conditional, §1.3) | Docs match code | "Keep [cite:N] as the validated marker; document [YOUR_RESULTS:N]/[REFERENCE:N] as context labels; remove the contradictory prompt line. … no validator edit." |

Consequence #1, verbatim: "**Governance edits are now approved:** amend `CLAUDE.md` (D3: CSV/JSON as named exceptions; D12: the external runner as a named ModelRunner exception) and `docs/compliance/data-privacy.md` (D3, D4). These change invariants. Make them in their own `docs:` commit, citing this record, with nothing else in the diff."

### 1.2 Hunk → licence map

| Hunk | File | Licensed by | In by default? |
|---|---|---|---|
| C-1 | `CLAUDE.md` §3 ModelRunner rule | D12 "documented ModelRunner exception … Amend CLAUDE.md to name the exception" | yes |
| C-2 | `CLAUDE.md` invariant "Redaction before anything leaves" | D3 "amend CLAUDE.md … to name them as deliberate exceptions" and "Doctor summary … redact it (strict)". D12 "make strict redaction unconditional … keep break-glass only with audit + UI warning" | yes. The break-glass-as-only-bypass clause only if **GOV-BG** is signed; unsigned, C-2 quotes D12's conditions instead (Wave 6, 3a M-3; GOV-BG also answers W-6 §11 Q2) |
| C-3 | `CLAUDE.md` invariant "No medical advice" | D11 "document [YOUR_RESULTS:N]/[REFERENCE:N] as context labels" | **yes (r5): GOV-D11 signed 2026-10-07** (owner-decisions row GOV-BG / GOV-D11) |
| C-4 | `CLAUDE.md` invariant "Local-first" | none. D12 licenses naming the *ModelRunner* exception only | **no (r5): Q3 skipped** (owner row W-10-REST: "Q3 skipped (Local-first line unchanged)"). Not applied |
| DP-1 | `data-privacy.md` Data Portability | D3 | yes |
| DP-2 | `data-privacy.md` backup paragraph (`:173-178`) | D3 | yes |
| DP-3 | `data-privacy.md` new section "Unverified Extracted Values" | D4 "Docs updated to say so" | yes |
| DP-4 | `data-privacy.md` Optional External API redaction bullet | D12 "documented … make strict redaction unconditional … break-glass only with audit + UI warning". The orchestrator (2026-09-27) assigned this line to W-10 | yes; the break-glass-as-only-bypass wording only if GOV-BG is signed (r5: signed) |

Fold-in hunks (r5). These are **not** governance hunks and are not licensed by Consequence #1. Each is licensed by the owner rows quoted here and lands as its own commit (Task 4b):

| Hunk | File | Licensed by (owner-decisions rows, 2026-10-07) | Commit |
|---|---|---|---|
| DP-5 (LOCAL-07) | `data-privacy.md` Optional External API, first two bullets | W-10-REST: "the three doc contradictions fixed as separate commits in the W-10 PR" | fold-in 1 |
| DP-6 (DOC-OVERCLAIM) | `data-privacy.md` Tier 3 table, rows "Audit logs" and "Security events" | W-10-REST (same sentence) | fold-in 2 |
| HC-1, HC-2 (DOC-OVERCLAIM) | `docs/compliance/hipaa-controls.md` rows "Log format" (`:49`) and "Immutability" (`:52`) | W10-HIPAA: "W-10 also corrects hipaa-controls.md:49 and :52 to match the code (no correlation-ID column in the audit table; audit rows are deleted on profile delete), as its own commit. Line :169 stays untouched (it waits on the P8 Brief 2 decision)." | fold-in 2 |
| C-5 (CLAUDE-FAILURE-COUNT) | `CLAUDE.md` §4, the recurring-failures bullet | W-10-REST (same sentence) | fold-in 3 |

**Decision on break-glass (C-2, DP-4). Owner gate GOV-BG (Wave 6, 3a M-3), default "include".** The r3 reasoning below is the recommendation, not a licence. Consequence #1 reads D12 as "the external runner as a named ModelRunner exception"; naming break-glass as a bypass of "Redaction before anything leaves" goes one step further, and anything wider than the verbatim text is owner-gated. If GOV-BG is unsigned, C-2 and DP-4 quote D12's conditions ("make strict redaction unconditional (remove the dev bypass; keep break-glass only with audit + UI warning)") and do not call break-glass a bypass or an exception. *r3 reasoning:* D12 reads: "make strict redaction unconditional (remove the dev bypass; keep break-glass only with audit + UI warning). Amend CLAUDE.md to name the exception." That text itself keeps break-glass and sets its two conditions, so naming audited break-glass is licensed as written. Without the clause, `CLAUDE.md:60` as written would forbid a bypass the owner chose to keep, which is recurring failure #8. The clause is worded strictly inside D12:
- it restates D12's two conditions and quotes D12 verbatim;
- it names break-glass as the only bypass;
- it adds nothing about which `app_env` break-glass applies in. That question (W-6 §11 Q1) stays open and belongs to W-6.

### 1.3 D11 (C-3): recommendation, not included silently

- **Recommendation: include C-3 in this commit, if Q1 is signed.** It rewrites the text of an invariant (`CLAUDE.md:62`). Consequence #1 says invariant edits belong in their own governance commit, citing the record. If P4 makes this edit, a Hard-invariant change lands inside a mixed doc-drift commit.
- **Against:** the handoff W-10 row and Consequence #1 name D3/D12 for `CLAUDE.md`, not D11. The W-5 plan ([W-5 §6](2026-09-27-W05-citation-marker-prompt.md)) makes the same recommendation and marks it for owner confirmation.
- **If Q1 is not signed:** skip C-3. `CLAUDE.md:62` then **stays unchanged** and is recorded in the PR as an **open owner item** (orchestrator ruling, 2026-09-27). It does **not** go to P4, and P4 must not edit it. Either way the 2-file scope holds.
- **Text source:** the text is W-5 §6's proposal, verified against D11 and code, with two corrections:
  1. "Outputs … cited with `[cite:N]` markers" would claim the agent path uses `[cite:N]`. It does not: `git grep "cite:" 7b2ff1f -- src/backend/modules/agent` → no hits, because the agent uses structured `Citation` objects. The text is therefore scoped to the legacy RAG path.
  2. `modules/rag.py::validate_response` is a method, so it becomes `RAGModule.validate_response` (class at `modules/rag.py:114`, method at `:793`, pattern `\[cite:(\d+)\]` at `:819`, main@40f590e = B@7b2ff1f, file unchanged by A/B).

### 1.4 Does NOT license

1. Any code, test, config or CI change. W-2 (doctor-summary redaction), W-3 (trends label / RAG filter), W-5 (prompt line) and W-6 (runner hardening) are separate PRs.
2. Any third file in the **governance commit**, including `docs/INDEX.md` and `docs/_link_graph.json`. That is why no markdown links are added (§3.3). r5: the PR as a whole also holds this plan file, `docs/compliance/hipaa-controls.md` (fold-in 2), the review records and the wave report, each in its own commit (§13).
3. Claiming a behaviour before it is merged. Every behaviour sentence in `data-privacy.md` carries a P or I status (Task 1).
4. Widening the redaction exceptions beyond CSV and JSON, or treating the doctor summary as an exception.
5. Naming the external runner as an exception to **Local-first** (`CLAUDE.md:59`). That is C-4, owner-gated (Q3).
6. Deciding where break-glass works (any env vs production only), which is W-6 §11 Q1.
7. Editing `skills/asclexis-guardrails/SKILL.md`, `docs/architecture/pipelines.md`, `src/backend/api/backup.py` docstrings, the capstone contract or matrix, or the D11 doc rows W-5 §6 hands to P4. See §11 follow-ups.
8. Correcting other false statements in `data-privacy.md` that no decision covers. r5 exception: LOCAL-07 (F-2 in §11) and DOC-OVERCLAIM are now covered by owner rows W-10-REST and W10-HIPAA and are corrected in Task 4b. Anything else stays out (for example the "Log files" row of the Encryption table, `data-privacy.md:47`, and `hipaa-controls.md:50-51`): report it, do not edit it.
9. Touching the baseline-count lines in `CLAUDE.md` (§4, the two `1370` slots at `:30` and `:35`), which belong to the phases that change collection, or the OpenWiki/Skills paragraphs, which belong to P1. r5 exception: hunk C-5 changes one word in the recurring-failures bullet (`:50`), nothing else in §4.
10. r5: editing `docs/compliance/hipaa-controls.md:169` ("Key rotation … Manual via password change"). It waits on the P8 Brief 2 decision (owner row W10-HIPAA).
11. r5: any legal or compliance conclusion. The fold-in text says what the code does; it never says the app is or is not HIPAA-compliant (owner-decisions Consequence #5).

## 2. Traceability

| ID | Where | Quoted heading / row (verified by grep 2026-09-27) | Effect of W-10 |
|---|---|---|---|
| C-REDACT-1 | [contract](../capstone-report/architecture-engineering-contract.md) §6 | "**C-REDACT-1 · BINDING (ask-first).** … Backups are the single documented exception." "Until D3 is answered, CSV/JSON/doctor summary violate `CLAUDE.md:60` as written." | CSV/JSON become named exceptions. The doctor summary stays under the rule |
| C-REDACT-2 | contract §6 | "**C-REDACT-2 · BINDING.** The external runner MUST apply strict redaction before any network call, unconditionally (`CLAUDE.md:60`)." | break-glass named as the only bypass, with its conditions, if GOV-BG is signed; otherwise D12's conditions quoted verbatim |
| C-LLM-1 | contract §7 | "**C-LLM-1 · BINDING.** All LLM calls MUST go through the `ModelRunner` facade (`CLAUDE.md:25`)." Deviation 2: "Whether it is an allowed exception is **OWNER-GATED**." | the external runner becomes the named exception |
| C-VERIFY-2 | contract §4 | "**C-VERIFY-2 · OWNER-GATED.** Which consumers MUST read verified rows only." | D4 recorded in `data-privacy.md` (DP-3) |
| C-SAFE-5 | contract §5 | "**C-SAFE-5 · PROPOSED.** One citation-marker vocabulary across docs, prompt and validator." | only if Q1 is signed (C-3) |
| PRIV-04 | [matrix](../capstone-report/specs-compliance-matrix.md) | "Every non-backup export is redacted … **contradicted**" | stays contradicted for the doctor summary until W-2. For CSV/JSON the requirement text changes (maintainer edit, F-6) |
| LOCAL-04 | matrix | "The opt-in external LLM is off by default and redacted … **partial**: two bypasses" | W-6 plan: moves to `tested` only after W-6 **and** W-10 |
| LLM-01 | matrix | "(the opt-in cloud `ExternalModelRunner` … does not; owner-gated deviation)" | becomes "owner-approved exception (D12)" |
| SAFE-02 | matrix | "Downstream consumers use verified data … **partial**" | D4 recorded; status unchanged until W-3 |
| SAFE-08 | matrix | "One citation-marker vocabulary … `CLAUDE.md:62`" | only if Q1 is signed |
| Handoff W-10 | [handoff §5](../../audit/2026-09-25/handoff-2026-09-27-execution.md) | "One `docs:` commit amending `CLAUDE.md` (D3 exceptions, D12 exception) and `docs/compliance/data-privacy.md` (D3, D4) … `python3 scripts/docs_lint.py` … lint passes; the diff contains only these files" | this plan |

W-10 edits neither the matrix nor the contract. The PR reports the status changes (handoff §6 item 3).

## 3. Verified current state

### 3.1 Which text the executor edits: post-P1, re-anchored

| File | main@40f590e | B@7b2ff1f | A@692fdf3 | Post-P1 expectation |
|---|---|---|---|---|
| `CLAUDE.md` :25, :59, :60, :62 | as quoted in §5 | identical at the same lines (B changes only :30-35, :67, :71) | identical at the same lines (A changes only :30-35) | same text. **P1 resolves the :30-35 baseline conflict; the line numbers of :25/:59-62 do not move.** Re-verify by content, not by number |
| `docs/compliance/data-privacy.md` | table :70-74, backup para :173-178, Third-Party :187, bullet :200 | unchanged vs main | Document Deletion rewritten (:180-202). Third-Party at **:204**, bullet at **:217** | A's version (only A touches it). The W-6 plan's "`data-privacy.md:200` @B" is the same bullet as :217 @A |

**Re-anchor rule:** every hunk below is anchored on its exact **Before** text, which must match exactly once. If P4, or any other phase, changed a Before block, stop (§8 S3). Line numbers are for orientation only.

### 3.2 Code facts the new text relies on (written at main@40f590e; r5: the three rows marked r5 were re-read on `origin/main` `777adf5`, and §3.6 lists every moved line)

| Claim in new text | Evidence |
|---|---|
| CSV/JSON/doctor summary are not redacted today | `modules/export.py` calls `RedactionEngine` only at `:533`/`:637` (visit-prep). `api/export.py:904` (`/csv`), `:960` (`/json`), `:379` (`/doctor-summary`), `:482-487` (download `format=text\|html\|pdf`) contain no redaction call |
| Third-party exports are strict-redacted | visit-prep `modules/export.py:637` (`policy_level="strict"`). Pinboard export `api/pinboards.py:485` → `compose_visit_prep_packet` (B@7b2ff1f). FHIR `modules/fhir_export.py:58`. RL `modules/rl_dataset.py:19` |
| Every export-shaped route is classified | §3.5: AST inventory of mounted routes (multiline-safe), 14 routes at B@7b2ff1f, each classified from code |
| External runner is off by default and opt-in | `models/model_settings.py:78-81` `default=False`; `core/external_runner.py:433` (r5; was `:353`) returns a runner only if `use_external_api` |
| ~~Dev bypass exists today~~ **superseded (r5)** | W-6 (PR #32, `2f0cb6f`) removed it. Now: `core/external_runner.py:252-257` forces `redaction_enabled = True` and `policy_level = "strict"` unless `redaction_bypass_active()` (`:95-109`) is true; under break-glass a master-DB audit row is written before dispatch and the call is refused if the row cannot be written (`:115-144`, `:295-317`); the flag reaches the UI through `api/model_settings.py:217`, and `src/frontend/src/components/settings/ExternalApiBreakGlassWarning.tsx:15-16` renders the warning on `SettingsPage.tsx:681` and `ExplainAssistant.tsx:477` |
| Values start unverified | `models/observation.py:79` `default=False`; set True only at `api/documents.py:1275` (r5; was `:1274`) and `api/observations.py:458` (contract C-VERIFY-1 verify line) |
| Trends carry no verification flag; legacy RAG does not filter | `api/observations.py:156-168` `TrendPoint` has no `user_verified`; query `:530-535` has no filter. `modules/rag.py:322-331` has no filter (it labels verified rows at `:435`; r5, was `:433`) |
| `[cite:N]` is the validated legacy marker | r5 lines: pattern `\[cite:(\d+)\]` at `modules/rag.py:822` inside `RAGModule.validate_response` (class `:116`, method `:795`); label `[YOUR_RESULTS:{i}]` built at `:638`; every other chunk is labelled `[{source_type.upper()}:{i}]` at `:642`, which gives `[REFERENCE:N]` for reference chunks (`source_type="reference"`, `:503`); the prompt names both labels at `:135-136` |

### 3.3 Why no markdown links: a finding the handoff acceptance misses

CI runs **both** `python3 scripts/docs_lint.py` and `python3 scripts/generate_docs_index.py --check` (`.github/workflows/ci.yml:22,25`).

- `generate_docs_index.py --check` fails when `docs/INDEX.md` or `docs/_link_graph.json` is stale. Both are built from the markdown links in every doc under `docs/` **and** in `CLAUDE.md` (`EXTRA_LINK_ROOTS`, `scripts/docs_lint.py:101`).
- Adding one `[..]` + `(..)` link to either file would therefore force a regenerated `docs/INDEX.md` and `docs/_link_graph.json` into the diff (4 files, which breaks Consequence #1 and the W-10 acceptance), or else fail CI.
- All citations in the new text are therefore **inline-code paths**, e.g. `docs/capstone-report/owner-decisions-2026-09-27.md`. The H1 and the first paragraph of each file are untouched, so the index title and summary do not change either (`_extract_title`/`_extract_summary`, `scripts/generate_docs_index.py:33-63`).
- Acceptance adds `generate_docs_index.py --check`. The handoff lists only `docs_lint.py`.

`scripts/harness_drift_check.py` (B) scans only `docs/agentic/*.md`, so it does not apply here.

### 3.5 Export-shaped route inventory (r1: multiline-safe; r3: mounted paths; classified from code)

**Why r1 changed this.** The r0 inventory used a one-line `git grep` over `@router.get/post("…")`. It missed `POST /feedback/export`, whose decorator spans several lines (`api/feedback.py:306-310` at B@7b2ff1f; mounted at `/feedback`, `api/__init__.py:58`). The inventory now uses `$W10_SCRATCH/routes_inv.py` (Task 1 Step 4). The script parses every `src/backend/api/*.py` with `ast`. It lists every `@router.<method>(path)` whose **mounted** path matches `export|download|/csv|/json`, plus every route in `api/export.py`, which is mounted at `/export` (`api/__init__.py:46`). r3: each line shows the full mounted path, built from:
- the `main.py` prefix for the aggregated api router (`app.include_router(api_router, prefix="/api/v1")`, `main.py:150` at B@7b2ff1f);
- the router's `include_router(..., prefix=...)` in `api/__init__.py`;
- any module-level `APIRouter(prefix=...)`;
- the decorator path.

A module that no `include_router` mounts is printed as `UNMOUNTED`.

Measured by the author (r3 script), 2026-09-27, over the B@7b2ff1f `src/backend/api/*.py` + `src/backend/main.py` files written out with `git show`. main@40f590e gives the same 14 routes; only the `model_settings.py` line numbers differ (`:567`, `:612`):

```text
src/backend/api/backup.py:313 GET /api/v1/backup/{backup_id}/download -> download_backup
src/backend/api/export.py:379 POST /api/v1/export/doctor-summary -> generate_doctor_summary
src/backend/api/export.py:482 GET /api/v1/export/doctor-summary/{summary_id}/download -> download_summary
src/backend/api/export.py:607 POST /api/v1/export/questions -> generate_questions
src/backend/api/export.py:698 POST /api/v1/export/visit-prep -> generate_visit_prep
src/backend/api/export.py:824 GET /api/v1/export/visit-prep/{packet_id}/download -> download_visit_prep
src/backend/api/export.py:904 GET /api/v1/export/csv -> export_csv
src/backend/api/export.py:960 GET /api/v1/export/json -> export_json
src/backend/api/export.py:1148 POST /api/v1/export/fhir -> generate_fhir_export
src/backend/api/export.py:1253 GET /api/v1/export/fhir/{export_id}/download -> download_fhir_export
src/backend/api/feedback.py:306 POST /api/v1/feedback/export -> export_dataset
src/backend/api/model_settings.py:578 GET /api/v1/settings/model/download-progress -> get_download_progress
src/backend/api/model_settings.py:623 POST /api/v1/settings/model/download -> start_model_download
src/backend/api/pinboards.py:382 POST /api/v1/pinboards/{pinboard_id}/export -> export_pinboard_packet
```

**Classification.** Code evidence only; docstrings are not evidence. Paths are relative to `src/backend/`, at B@7b2ff1f, where main is identical.

| Route(s) | Class | DP text that covers it | Code evidence |
|---|---|---|---|
| `GET /backup/{id}/download` | patient-own, intentionally unredacted (BKUP-UX-001) | DP-2 "Backup archives …" | `api/backup.py` contains no `RedactionEngine`/`redact(` (`git show 7b2ff1f:src/backend/api/backup.py \| grep -c "RedactionEngine\|redact("` → `0`) |
| `GET /export/csv`, `GET /export/json` | patient-own, intentionally unredacted (D3) | DP-1, DP-2 | `api/export.py:904,960` → `modules/export.py:223` `export_csv`, `:267` `export_json`. `modules/export.py` calls `RedactionEngine` only inside `compose_visit_prep_packet` (`:502`; calls at `:533`, `:637`) |
| `POST /export/doctor-summary`, `GET …/download` | third party; D3 requires `strict`; **unredacted today** | DP-1, DP-2 (status P until W-2) | `api/export.py:379,482`; renderers `modules/export.py:290` (html), `:358` (pdf) have no redaction call |
| `POST /export/visit-prep`, `GET …/download` | third party, `strict` | DP-2 "visit-prep packet" | `modules/export.py:502` `compose_visit_prep_packet` → `:637` `RedactionEngine(policy_level="strict")` |
| `POST /pinboards/{id}/export` | third party, `strict` | DP-2 "pinboard export" | `api/pinboards.py:485` → `compose_visit_prep_packet` |
| `POST /export/fhir`, `GET …/download` | third party, `strict` | DP-2 "FHIR bundle" | `api/export.py:1210` → `modules/fhir_export.py:320` `build_fhir_bundle` → `:345` `_Redactor()` → `:58` `RedactionEngine(policy_level="strict")` |
| `POST /feedback/export` | RL dataset, `strict`, confirm-gated | DP-2 "RL dataset" | `api/feedback.py:363,384` → `modules/rl_dataset.py:85` `export_rl_datasets` → `:105` `RedactionEngine(policy_level="strict")` ("always strict, no knob"). Gate: `api/feedback.py:322` `if not body.confirmed` → 400 |
| `POST /export/questions` | **not export-shaped**: in-app JSON response, no file | none needed | `api/export.py:607` returns `list[QuestionItem]` to the caller. No `Content-Disposition` in `:607-697`, no stored artifact. It is the same class as any in-app read. (It carries `source_quote`, verbatim document text, to the patient's own UI) |
| `GET /settings/model/download-progress`, `POST /settings/model/download` (mounted `api/__init__.py:47`) | **not export-shaped**: inbound model download | none needed | `api/model_settings.py:578,623` fetch model weights *into* the app. They are C-LOCAL-1's "user-triggered model downloads", not user text leaving |

DP-2's enumeration (backup, CSV, JSON unredacted; visit-prep, pinboard, FHIR, RL dataset strict; doctor summary under D3) covers every export-shaped route above. A route the executor's run prints that is not in this table is unclassified, so stop (S5).

### 3.4 Measured dry run (2026-09-27, this author)

A throwaway script in the session scratchpad parsed this plan's Before/After blocks and the Task 2 assertion script out of this file. It applied the hunks in memory to the `git show` copies of both files at main@40f590e, and to B@7b2ff1f `CLAUDE.md` + A@692fdf3 `data-privacy.md` (the post-P1 proxy). It ran the assertions, then rebuilt `docs/INDEX.md` content and the link graph with the repo's own `generate_docs_index.generate` / `docs_lint.build_link_graph`, reading the patched text through a patched `Path.read_text`. No repo file was written. Output:

```text
start link counts main: CLAUDE 4 privacy 0 | B CLAUDE 4 A privacy 0
RED (main, unpatched): exit 1 — FAIL W10-A1, A2, A3, A4, A6, A7, A8; 2/9 assertions pass
GREEN P (main): exit 0 — 9/9 assertions pass
GREEN I (main): exit 0 — 9/9 assertions pass
GREEN P (B CLAUDE + A privacy): exit 0 — 9/9 assertions pass
INDEX identical P: True  I: True
link graph identical P: True  I: True
DOC-007 errors before/after: 0 0 0
GREEN alt (Q2 unsigned, no C-3): exit 0 — 9/9 assertions pass
GREEN P + C-4: exit 0 — 9/9 assertions pass
BREAK a assert: exit 1 — FAIL W10-A9: link count changed: CLAUDE 4->4, privacy 0->1
BREAK a INDEX identical: False  graph identical: False  DOC-007 errors: 0
BREAK b assert: exit 1 — FAIL W10-A6: DP-1/DP-2 text wrong
diff lines CLAUDE(B->P): 6      (3 hunks x 1 line removed + 1 added)
diff lines privacy(A->P): 43
routes_inv (plan copy) at B: 14 lines; feedback/export present: True
r1 shell snippets (W10_ARGS all-unsigned, W10_LINKS): ARGS=[ --no-breakglass] LINKS=4,0 -> RED 3/9, exit 1
```

r1 re-ran the whole block above with the r1 script, which reads `$WT`. The results were identical.

r2 dry run, 2026-09-27, variant U:

```text
GREEN U (main): exit 0 — 9/9;  GREEN U (B CLAUDE + A privacy): exit 0 — 9/9;  GREEN alt-U (Q2 unsigned): exit 0 — 9/9
INDEX/graph identical U: True True
U privacy text contains "not yet implemented": False; contains "conformance unverified": True
rc_check.py block in this plan is byte-identical to the tested script: True
```

r3 dry run, 2026-09-27. Q2 alternates removed; C-2 quotes D12; the inventory prints mounted paths. (The r1/r2 "alt" lines above are historical; those blocks no longer exist.)

```text
RED (main): exit 1 — 2/9 with --c3;  RED (B CLAUDE + A privacy, no flags): 3/9
GREEN P / I / U (main): 9/9 each;  GREEN P / U (B CLAUDE + A privacy): 9/9;  GREEN P + C-4: 9/9
INDEX identical (P, I, U): True;  link graph identical: True;  DOC-007 errors: 0
BREAK a: W10-A9 FAIL + INDEX/graph differ;  BREAK b: W10-A6 FAIL
routes_inv r3 (plan copy) at B: 14 lines; "feedback.py:306 POST /api/v1/feedback/export" present: 1; UNMOUNTED: 0
```

Wave 6 dry run, 2026-09-28 (GOV-BG blocks). A scratch script extracted the Task 2 script and the C-1, C-2, DP-1…DP-4 Before/After blocks from this file, applied them with an exactly-once match to main@40f590e and to B@7b2ff1f `CLAUDE.md` + A@692fdf3 `data-privacy.md`, and ran the assertions with `--links=4,0`. No repo file was written.

```text
RED (main, unpatched): 3/9 with and without --govbg
GREEN, GOV-BG signed (--govbg), P / U / I, main and B+A: 9/9 each, exit 0
GREEN, GOV-BG unsigned (no flag), P / U / I, main and B+A: 9/9 each, exit 0
Wrong flag for the text applied (12 runs): exit 1, "FAIL W10-A3: C-2/DP-4 break-glass wording does not match --govbg", 8/9
```
The index/link-graph rebuild was not re-run for the GOV-BG-unsigned blocks: **UNMEASURED**. They add no `](`, and W10-A9 passed on all 12 trees.

Two things were **not** run and are **UNMEASURED**: `python3 scripts/docs_lint.py` and `generate_docs_index.py --check` as whole-repo commands on a real post-P1 tree, because this checkout is dirty and P1 has not happened. To measure, run Task 4 Step 5 in the executor's clean worktree. The dry run shows the two files contribute nothing new to either gate: identical index and graph content, and 0 DOC-007 errors.

### 3.6 r5 re-measurement on `origin/main` `777adf5` (2026-10-08)

**Before blocks.** All 8 anchors of Task 0 Step 3 print `1` (`CLAUDE.md:25`, `:59`, `:60`, `:62`; `data-privacy.md:74-76`, `:173-178`, `:204`, `:217`). The fold-in anchors also match exactly once: `data-privacy.md:213-214`, `:33`, `:35`; `hipaa-controls.md:49`, `:52`; `CLAUDE.md:50`.

**Moved code lines** (orientation only; hunks anchor on text):

| Plan citation | Now | Moved by |
|---|---|---|
| `core/external_runner.py:172`, `:201`, `:220` (dev bypass) | gone; see the superseded §3.2 row | W-6, PR #32 |
| `core/external_runner.py:353` (`use_external_api`) | `:433` | W-6 |
| `modules/rag.py:114`, `:793`, `:819`, `:636`, `:433` | `:116`, `:795`, `:822`, `:638`, `:435` | W-5, PR #34 |
| `modules/rag.py:1257-1268` (F-2: composed prompt → runner) | `:1262` `compose_prompt(question, chunks, history=history)`, `:1264-1269` memory section, `:1271-1273` → runner | W-5 |
| `api/model_settings.py:578`, `:623` | `:582`, `:627` | W-6 |
| `api/documents.py:1274` | `:1275` | — |
| `main.py:150` | `:169` | — |
| `scripts/docs_lint.py:101` (`EXTRA_LINK_ROOTS`) | `:106` | — |

**Export inventory.** `routes_inv.py` prints 14 lines, 0 `UNMOUNTED`, the same 14 method + mounted path + function as §3.5 (only the two `model_settings.py` line numbers moved).

**Variant table** (Task 1, measured):

```text
Q1=signed  GOVBG=signed  Q3=skipped  Q4=answered (land now)  Q5=answered (keep)   W10_ARGS=[ --c3 --govbg]   W10_LINKS=4,0
W-2: P  no PR (gh pr list --state all: none; git grep HC-EXPR-001 origin/main -- src/backend/tests: 0 hits)   -> DP-1, DP-2
W-3: P  no PR (same list; git grep HC-VER-001: 0 hits)                                                        -> DP-3
W-6: U  PR #32 / 2f0cb6f (merge-base --is-ancestor: yes)  evidence 1-4: y y y n                              -> DP-4
     1: tests/test_external_runner_hardening.py -> 17 passed (Py 3.11.16, HF_HUB_OFFLINE=1)
     2-3: PR #32 body records red-first and break-it for HC-EXT-001, 002, 004 (and vitest 003, 005)
     4: rc_check.py ... HC-EXT-004 -> MISS test_hc_ext_004_external_api_settings_reports_break_glass:263
        (it reaches route_client through the helper _get_external_api, which the function-scoped check
        does not accept); OK test_hc_ext_004b...:271 -> :285. Exit 1 -> U, never I (S6).
routes_inv: 14 lines, all classified in §3.5: y
```

**Code evidence for the fold-ins** (all `src/backend/`, read on `777adf5`):

| Claim in fold-in text | Evidence |
|---|---|
| The external runner receives the whole composed prompt | `modules/rag.py:1262` `compose_prompt(question, chunks, history=history)`; `:679-682` `SYSTEM_PROMPT.format(context=…, question=…)`; history section `:662-677`; memory section `:1256-1269`; `:1272-1273` `runner = model_runner or self._model_runner` → `_generate_with_runner(prompt, runner)`; `core/external_runner.py:266-279` redacts that prompt, `:320-324` sends it |
| The context holds observation summaries, document passages and reference text | `modules/rag.py:52` (`source_type`: `user_document`, `reference`, `user_observation`); summaries built at `:322-331`, `:425-448` (at most 5 analytes, latest 5 values each) |
| Two routes pass the external runner | `api/assistant.py:757-758` → `rag.query(… history=…, model_runner=runner, … use_memory=inject_memory)` `:815-827` (legacy path only; `_serve_via_agent` `:792-797` takes no runner); `api/interpretations.py:476-478` → `rag.query(… model_runner=runner, … use_memory=False)` `:483-492` (no history) |
| What `strict` removes | `modules/redaction.py:56-128`, 8 rules at `strict`: `ssn`, `email`, `phone`, `name_context`, `dob`, `address`, `mrn`, `numeric_date`; the comment at `:108-113` says ISO-8601 dates are deliberately not matched. No rule matches lab values or analyte names |
| No log file is written | no `FileHandler` / `basicConfig` / `dictConfig` in product code (`grep -rn` over `src/backend`, tests and `scripts/` excluded → only `alembic.ini:61` `StreamHandler`, `args = (sys.stderr,)`); `core/config.py:130` `log_file_path` is only used to `mkdir` its directory (`core/database.py:88-89`) |
| `SecurityAuditMiddleware` lines are below the default level | `security/audit_middleware.py:78` `logger.info(…)`; root level WARN (`alembic.ini:45-47`); measured: `logging.getLogger("security.audit_middleware").getEffectiveLevel()` → `WARNING` after `main.create_app()` |
| The audit table has no correlation-ID column | `models/audit.py:31-63`: `id`, `profile_id`, `event_type`, `action`, `entity_type`, `entity_id`, `details_json`, `client_info`, `timestamp` |
| The security-audit log payload carries the correlation ID | `security/audit_middleware.py:69` (PR #45); log records get `record.correlation_id` (`core/logging_setup.py:18-29`); the console format does not print it (`alembic.ini:67`) |
| Audit rows are deleted on profile delete | `api/profiles.py:908-910` `delete(AuditLog).where(AuditLog.profile_id == profile_id)`; the only other writer is the insert in `core/audit.py:243-252` (`grep -rn AuditLog` over product code); no `TRIGGER` in `migrations/` |
| The failure-mode count | `grep -cE '^## [0-9]+\. ' docs/agentic/recurring-failures.md` → `10` |

## 4. Files

**Owned (modify only):**
- `CLAUDE.md`: hunks C-1, C-2, C-3 (r5: Q1 signed; C-4 not applied, Q3 skipped); fold-in hunk C-5
- `docs/compliance/data-privacy.md`: hunks DP-1, DP-2, DP-3, DP-4; fold-in hunks DP-5, DP-6
- `docs/compliance/hipaa-controls.md` (r5): fold-in hunks HC-1 (`:49`) and HC-2 (`:52`) only
- This plan file (r5 amendment commit), `audit/2026-09-25/swarm-2026-09-27/reviews/W10-r5-*` and `audit/2026-09-25/waves/wave-4-L1-C.md` (records, their own commits)

**Read-only (must show zero diff):** everything else. In particular:
- ask-first files (`modules/interpret_safety.py`, `modules/redaction.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`, `core/auth.py`, anything auth/encryption);
- `core/external_runner.py`, `modules/export.py`, `api/export.py`, `modules/rag.py`, `api/observations.py`;
- `docs/INDEX.md`, `docs/_link_graph.json` (regenerated by script only if `generate_docs_index.py --check` says they are stale, and then committed with the commit that staled them), `AGENT.md`, `skills/**`, `docs/capstone-report/**`, `audit/**` except the r5 record files named above.

**Scratch (never committed):** `$W10_SCRATCH` = `$HOME/.cache/asclexis-w10`, outside the repo (r5: any directory outside the repo works; every block reads the path from `w10.env`). It holds `w10.env`, `w10_assert.py`, `routes_inv.py`, PR-body captures and `dp.bak`.

**Shared-file ordering:**

| File | Order | Rule |
|---|---|---|
| `CLAUDE.md` | P1 (baseline, OpenWiki, skills count) → P2 (plan 02 Task 6 baseline) → P4 (baseline if moved; P4 must **not** touch `:25`/`:59-62`) → **W-10** → P5 and later (baseline lines only) | never concurrent; W-10 does not touch baseline lines |
| `docs/compliance/data-privacy.md` | P1 (A's Document Deletion hunk) → P4 → **W-10** → W-10b status flip (Task 6) | The program's "P1 → P4 → G-A1" becomes "P1 → P4 → W-10 → W-10b". W-2 (G-A1) does **not** edit this file. See F-5 |

## 5. Dependencies and order

| Dependency | Kind | Why |
|---|---|---|
| P0-B merged | hard | `docs/capstone-report/owner-decisions-2026-09-27.md` must exist on main for the cited path to be true |
| P1 merged | hard | the target text is the post-P1 file (§3.1) |
| P4 merged | hard (handoff §3 order) | no concurrent doc edits; P4 must have dropped its `data-privacy.md:173-174` and `CLAUDE.md:62` items (F-5) |
| D9 venv | soft | used for the pytest measurement; `python3` alone is enough for the docs gates |
| W-2, W-3, W-6 | **none** for landing; they select P vs I variants | see below |
| W-5 | none | C-3 describes the validator, which W-5 does not change ("no validator edit") |
| Downstream: W-7/G-B3 boundary test | W-10 unblocks it | C-LLM-2 may allowlist `core/external_runner.py` only after D12 **and** W-10 name the exception |

**Order (reconciles the handoff and the orchestrator): P1 → P2 → P3 → P4 → W-10 → P5 …**, with W-2, W-3 and W-6 landing after W-10, and W-10b (Task 6) after the last of them.

- **Why before the product PRs.** None of W-2/W-3/W-6 widens what leaves the device, but two of them pin exceptions in tests. W-2's HC-EXPR-002 asserts that CSV/JSON stay unredacted. W-6 keeps an audited break-glass. If W-10 lands first, those tests enforce a *documented* exception rather than a violation of `CLAUDE.md:60` as written. This matches handoff §3 (governance commit right after P4).
- **How it stays truthful.**
  - `CLAUDE.md` text is normative and points to the matrix for conformance, so it is true on landing and needs no later edit.
  - In `data-privacy.md`, each behaviour sentence uses variant P ("owner-approved, not yet implemented", naming the tracking item) until its W-item merges. It uses variant U ("code merged in `<sha>`; conformance unverified") once the code has merged but the variant-I evidence is incomplete. Task 6 (W-10b) then flips it to variant I in a separate `docs:` commit. That commit touches only status lines, not invariant text, so it is not a governance change.
- **If the orchestrator runs a W-item before W-10**, Task 1 measures that it merged and selects variant I for that item. No other change is needed. If all three have merged, Task 6 is not needed.

## 6. Global constraints

- The governance commit stages exactly 2 files (`git diff --cached --name-only`). r5: each fold-in commit stages exactly the files Task 4b names for it. Commit prefix `docs:` or `docs(scope):`.
- No bracket-paren (`[..]` + `(..)`) markdown links in any new text; inline-code paths only.
- Do not change the H1 or first paragraph of either file.
- Do not change any line outside the Before blocks (r5: including the Task 4b Before blocks). No reflow of neighbouring paragraphs.
- Quote the owner's wording where the text restates a decision. Never paraphrase it wider (e.g. never "exports may be unredacted").
- Keep the states distinct: normative "must" in `CLAUDE.md`. In `data-privacy.md` there are three states: P "owner-approved, not yet implemented", U "code merged in `<sha>`; conformance unverified", and I "implemented in `<sha>`".
- Health-app tone: say what is and is not redacted, plainly.
- **Baseline sentences untouched.** W-10 changes no test collection, so it edits neither the collected count nor the pass-count sentence in `CLAUDE.md` §4 (or `AGENT.md`). Task 5 proves collection is unchanged.
- Shell: every block starts `set -o pipefail` and `source "$HOME/.cache/asclexis-w10/w10.env"`. Paths are absolute. Any `cd` happens in a subshell to an absolute path.

## 7. Review focus (what the doc checks cannot see)

1. **A reader takes normative text as a conformance claim.** C-2 says the doctor summary "must be redacted". Mitigation: C-2 ends with the pointer to the matrix rows that track conformance. The reviewer checks that the sentence says "must", not "is".
2. **Variant chosen by belief, not measurement.** Variant I requires four pieces of evidence (Task 1 Step 3): tests present and passing, red-first output in the merged PR, a break-it run, and a function-scoped `route_client` call in the named HTTP test (`rc_check.py`, call line recorded). Test IDs alone never select I; merged code without that evidence selects U.
3. **The enumerated export list goes stale or misses a route.** DP-2 lists four redacted exports. Task 1 Step 4 re-runs the AST inventory: multiline decorators, all mounted routers. Any route not classified in §3.5 means stop (S5). r0's one-line grep missed `POST /feedback/export`.
4. **Break-glass wording drifts from W-6's final behaviour.** Variant I of DP-4 must match the merged W-6 code (audit before dispatch, UI warning). Task 6 re-reads W-6's merged diff before flipping.
5. **A later phase re-edits the amended lines without citing the decision.** The commit body lists each hunk and its decision, so `git log -L` / `git blame` on those lines leads back to the record.

---

## Task 0: Preconditions and phase-start measurement (no commit)

**Files:** none modified. Every shell block in this plan starts with `set -o pipefail` and sources one env file. All paths are absolute (`$MAIN`, `$WT`, `$W10_SCRATCH`), so no block depends on the directory an earlier block left behind.

- [ ] **Step 1: Env file and a fresh worktree from the merged main**

```bash
set -o pipefail
mkdir -p "$HOME/.cache/asclexis-w10"
cat > "$HOME/.cache/asclexis-w10/w10.env" <<'EOF'
export MAIN=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral
export WT=/mnt/c/Users/DangT/Documents/GitHub/hc-w10
export W10_SCRATCH="$HOME/.cache/asclexis-w10"
export PY="$HOME/venvs/asclexis-311/bin/python"
EOF
source "$HOME/.cache/asclexis-w10/w10.env"
git -C "$MAIN" fetch origin
git -C "$MAIN" worktree add "$WT" -b docs/w10-governance-amendments origin/main
git -C "$WT" status --short   # expect: empty
```

If the D9 venv does not exist yet, set `PY=/mnt/c/Python313/python.exe` in the env file. Record `UNMEASURED: D9 venv absent` and the interpreter in the PR.

- [ ] **Step 2: Prove the hard dependencies landed**

```bash
set -o pipefail
source "$HOME/.cache/asclexis-w10/w10.env"
git -C "$WT" cat-file -e origin/main:docs/capstone-report/owner-decisions-2026-09-27.md && echo P0-B-ok
git -C "$WT" merge-base --is-ancestor 7b2ff1f origin/main && echo B-in-main
git -C "$WT" merge-base --is-ancestor 692fdf3 origin/main && echo A-in-main
# r5: P4-core (PR #40), W-6 (PR #32), and the owner rows this plan cites
git -C "$WT" merge-base --is-ancestor 6b4dd84 origin/main && echo P4-core-in-main
git -C "$WT" merge-base --is-ancestor 2f0cb6f origin/main && echo W6-in-main
git -C "$WT" show origin/main:docs/capstone-report/owner-decisions-2026-09-27.md | grep -nE '^\| (D3|D4|D11|D12|GOV-BG / GOV-D11|W-10-REST|W10-Q4 / W10-Q5|W10-HIPAA) ' | cut -c1-60
```

Expected (r5, measured 2026-10-08 on `777adf5`): the two extra ancestry lines print, and the grep prints 8 rows at `:15`, `:16`, `:22`, `:25`, `:65`, `:68`, `:75`, `:76` (Consequence #1 is at `:93`). A missing row is S1: the governance text must not cite a record that is not on main.

Expected: `P0-B-ok`, `B-in-main` and `A-in-main` all print. If any is missing, stop (S1). Before P1 lands, this stop is the intended outcome. For P4, record its PR's merge sha from the PR page, or the orchestrator's written waiver. No grep reliably proves that P4 merged.

- [ ] **Step 3: Confirm every Before anchor matches exactly once**

```bash
set -o pipefail
source "$HOME/.cache/asclexis-w10/w10.env"
grep -cF -- '- All LLM calls go through the `ModelRunner` facade. Never import `llama_cpp` or call Ollama directly from feature code.' "$WT/CLAUDE.md"
grep -cF -- '- **Redaction before anything leaves.** Any path that writes user text to exportable files or external runners must pass through `modules/redaction.py` first.' "$WT/CLAUDE.md"
grep -cF -- '- **No medical advice.** Outputs are educational, grounded, cited (`[REFERENCE:N]` / `[YOUR_RESULTS:N]`). `interpret_safety` prohibited patterns (diagnosis, dosing) must keep passing.' "$WT/CLAUDE.md"
grep -cF -- '- **Local-first.** No network calls in product code paths. Ollama provider is localhost-only by design — keep it that way.' "$WT/CLAUDE.md"
grep -cF -- '| Doctor Summary | `POST /export/doctor-summary` | Formatted clinical report |' "$WT/docs/compliance/data-privacy.md"
grep -cF -- '**Backup archives are deliberately not redacted** (BKUP-UX-001). Every other' "$WT/docs/compliance/data-privacy.md"
grep -cF -- '## Third-Party Data Sharing' "$WT/docs/compliance/data-privacy.md"
grep -cF -- '- PHI redaction applied to API prompts per `modules/redaction.py` policy' "$WT/docs/compliance/data-privacy.md"
```

Expected: `1` on each of the 8 lines (measured `1 1 1 1 1 1 1 1` on main@40f590e, 2026-09-27). A `0` means another phase changed the anchor, so stop (S3). Do not improvise a new anchor.

- [ ] **Step 4: Record the start measurement**

```bash
set -o pipefail
source "$HOME/.cache/asclexis-w10/w10.env"
python3 --version
python3 "$WT/scripts/docs_lint.py"; echo "docs_lint exit=$?"
python3 "$WT/scripts/generate_docs_index.py" --check; echo "index_check exit=$?"
"$PY" --version
# r5: collect-only instead of the full suite (docs-only diff; 12 GB host). The full suite is reported as skipped.
(cd "$WT/src/backend" && HF_HUB_OFFLINE=1 "$PY" -m pytest tests/ -p no:cacheprovider --collect-only -q 2>&1 | tail -1)
(cd "$WT/src/backend" && HF_HUB_OFFLINE=1 "$PY" -m pytest tests/test_docs_lint.py -p no:cacheprovider -q 2>&1 | tail -3)
```

Expected:
- `Docs lint passed.` with exit 0.
- Index check exit 0 ("docs/INDEX.md and docs/_link_graph.json are fresh.").
- The collect-only line records **collected** (r5: `1370 tests collected`, equal to the `CLAUDE.md:30` slot).

If either docs gate fails on the start tree, stop (S4): W-10 must not land on a red docs job. Record all outputs verbatim in the PR body (handoff §6 item 1).

---

## Task 1: Select variants, build the export inventory, fix the assertion flags (no commit)

**Files:** none modified in the repo. Outputs: `$W10_SCRATCH/routes_inv.py`, the `W10_ARGS` line in the env file, and a "variant table" for the PR body.

- [ ] **Step 1: Read the confirmation boxes Q1 (GOV-D11), Q2 (GOV-BG), Q3 and Q4 in §10** (Q2 is a gate again as of Wave 6, 3a M-3)

| Q | If signed | If unsigned |
|---|---|---|
| Q1 (D11 → C-3) | apply C-3 | skip C-3. `CLAUDE.md:62` stays unchanged; list it in the PR as an open owner item (not P4) |
| Q2 (GOV-BG → C-2 clause, DP-4) | use the GOV-BG-signed C-2 and DP-4 text | use the GOV-BG-unsigned C-2 and DP-4 text (quotes D12; no "only bypass" wording) |
| Q3 (C-4 local-first) | apply C-4 | skip C-4 (default) |
| Q4 (order) | as §5 | if the owner says "land after W-2/W-3/W-6", wait, then use variant I throughout (only where Step 3's criteria hold) |

- [ ] **Step 2: Measure whether W-2, W-3 and W-6 code has merged, independently of test IDs** (r4)

A missing or renamed test ID does not prove the code is unmerged, so merge status comes from the item's PR, not from a test grep.

```bash
set -o pipefail
source "$HOME/.cache/asclexis-w10/w10.env"
# <PR#> = that item's PR number, from the orchestrator's merge record or the PR page. Run once per item (W-2, W-3, W-6).
gh pr view <PR#> --json number,state,mergeCommit -q '[.number,.state,.mergeCommit.oid] | @tsv'
git -C "$WT" merge-base --is-ancestor <mergeCommit oid> origin/main && echo "merged-in-main" || echo "NOT-in-main"
```

- State `MERGED` and `merged-in-main` → **code merged** → Step 3 (the result is I or U, never P).
- No PR for the item, a state other than `MERGED`, or `NOT-in-main` → **code not merged** → variant **P** for that item.
- If the orchestrator has no merge record and no PR can be found, stop and ask the orchestrator (S6). Never infer "not merged" from a missing test ID.

- [ ] **Step 3: For each merged item, collect the four pieces of evidence that variant I requires**

```bash
set -o pipefail
source "$HOME/.cache/asclexis-w10/w10.env"
git -C "$WT" grep -n "HC-EXPR-001" origin/main -- src/backend/tests | head -3   # W-2
git -C "$WT" grep -n "HC-VER-001"  origin/main -- src/backend/tests | head -3   # W-3
git -C "$WT" grep -n "HC-EXT-001"  origin/main -- src/backend/tests | head -3   # W-6
# Zero hits for a merged item = criterion 1 fails -> variant U (not P).
# <files> = the test files the grep above printed for that item, relative to src/backend; <PR#> = that item's merged PR from Step 2
(cd "$WT/src/backend" && "$PY" -m pytest <files> -p no:cacheprovider -q 2>&1 | tail -3)
python3 "$W10_SCRATCH/rc_check.py" "$WT/src/backend/<HTTP test file>" <HTTP test ID>   # W-2 HC-EXPR-003 · W-3 HC-VER-002 · W-6 HC-EXT-004
gh pr view <PR#> --json number,state,mergeCommit -q '[.number,.state,.mergeCommit.oid] | @tsv'
gh pr view <PR#> --json body -q .body > "$W10_SCRATCH/pr-<PR#>-body.md"
grep -n -i -E "red|fail(ed|s)?|break" "$W10_SCRATCH/pr-<PR#>-body.md" | head -30
```

Variant **I** is allowed for an item only when **all four** hold. Record each one in the variant table.
1. **Passing tests.** The item's tests exist on `origin/main` and pass now: non-zero count, 0 failed.
2. **Red first.** The merged PR body records the red-first output (command plus failing output) for each new test ID the item added (handoff §6 item 2).
3. **Break-it.** The PR body records at least one break-it-on-purpose run going red (recurring failure #1).
4. **HTTP test.** The named HTTP test itself calls `route_client`: W-2 HC-EXPR-003, W-3 HC-VER-002, W-6 HC-EXT-004. "Itself" means inside its own function body, or through a same-file fixture in its arguments. A `route_client` call somewhere else in the same file does not count. `rc_check.py` must exit 0 and print an `OK` line with the call's `file:line`. Paste that line into the variant table as evidence. Exit 1 (`MISS`) or 2 (`NO-TEST`) means criterion 4 fails.

If any of the four is missing:
- **Code not merged (Step 2):** use variant **P** ("owner-approved, not yet implemented").
- **Code merged (Step 2):** use variant **U** ("code merged in `<sha>`; conformance unverified"), including when the item's test IDs are missing or renamed. The Task 4 blocks give U explicitly. P's "Today …" sentence would be false for merged code, and "not yet implemented" would be false too.

In both cases, name the missing evidence in the PR and raise S6. Never write I on test IDs alone.

Create `$W10_SCRATCH/rc_check.py` (function-scoped, ast; the author tested it on 2026-09-27 against B@7b2ff1f `tests/test_backup_routes.py`: HC-BKUP-035 → `OK … :113`, HC-BKUP-042 → `OK … :238`, HC-BKUP-999 → `NO-TEST` exit 2; and on a synthetic file: a direct-call-free test → `MISS` exit 1, a fixture-provided client → `OK (via fixture)`):

```python
#!/usr/bin/env python3
"""Usage: rc_check.py <test_file.py> <TEST-ID>   e.g. rc_check.py tests/test_export_redaction.py HC-EXPR-003
Function-scoped check: every test function whose NAME contains the ID slug (HC-EXPR-003 -> hc_expr_003)
must call route_client inside its own body, or take a same-file pytest fixture whose body calls it.
Prints each call line as evidence. Exit 0 = all matched functions call it; 1 = a function does not;
2 = no function is named for the ID (evidence missing)."""
import ast
import sys

path, test_id = sys.argv[1], sys.argv[2]
slug = test_id.lower().replace("-", "_")
tree = ast.parse(open(path, encoding="utf-8").read())
funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]


def rc_calls(fn):
    return [c.lineno for c in ast.walk(fn) if isinstance(c, ast.Call) and (
        (isinstance(c.func, ast.Name) and c.func.id == "route_client")
        or (isinstance(c.func, ast.Attribute) and c.func.attr == "route_client"))]


def is_fixture(fn):
    return any("fixture" in ast.unparse(d) for d in fn.decorator_list)


fixtures = {f.name: f for f in funcs if is_fixture(f)}
tests = [f for f in funcs if f.name.startswith("test") and slug in f.name]
if not tests:
    print(f"NO-TEST: no test function named for {test_id} (slug {slug}) in {path}")
    sys.exit(2)
ok = True
for t in tests:
    lines = [f"{path}:{n} (in {t.name})" for n in rc_calls(t)]
    for a in t.args.args:
        fx = fixtures.get(a.arg)
        if fx:
            lines += [f"{path}:{n} (via fixture {fx.name})" for n in rc_calls(fx)]
    print(("OK   " if lines else "MISS ") + f"{t.name}:{t.lineno} -> " + ("; ".join(lines) or "no route_client call"))
    ok = ok and bool(lines)
sys.exit(0 if ok else 1)
```

- [ ] **Step 4: Rebuild the export-route inventory (multiline-safe) and compare with §3.5**

Create `$W10_SCRATCH/routes_inv.py`:

```python
#!/usr/bin/env python3
"""Usage: routes_inv.py <worktree root>
List every @router.<method>(path) decorator in src/backend/api/*.py (multiline-safe, via ast) whose
MOUNTED path contains export/download/csv/json, plus every route in api/export.py. Each line shows the
full mounted path: main.py prefix for the api router + api/__init__.py include_router prefix +
any APIRouter(prefix=...) in the module + the decorator path. A module with no include_router is
printed as UNMOUNTED (classify it anyway)."""
import ast
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1])
api = root / "src/backend/api"
pat = re.compile(r"export|download|/csv|/json", re.I)


def kw(call, name):
    for k in call.keywords:
        if k.arg == name and isinstance(k.value, ast.Constant):
            return k.value.value
    return ""


# 1. main.py: prefix of the aggregated api router (from api import router as api_router)
top = ""
for n in ast.walk(ast.parse((root / "src/backend/main.py").read_text(encoding="utf-8"))):
    if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "include_router"
            and n.args and isinstance(n.args[0], ast.Name) and n.args[0].id == "api_router"):
        top = kw(n, "prefix")
# 2. api/__init__.py: alias -> module, alias -> mount prefix
init = ast.parse((api / "__init__.py").read_text(encoding="utf-8"))
alias_mod, mount = {}, {}
for n in ast.walk(init):
    if isinstance(n, ast.ImportFrom) and n.level == 1 and n.module:
        for a in n.names:
            if a.name == "router":
                alias_mod[a.asname or a.name] = n.module
    if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "include_router"
            and n.args and isinstance(n.args[0], ast.Name)):
        mod = alias_mod.get(n.args[0].id)
        if mod:
            mount[mod] = kw(n, "prefix")
# 3. each module's routes
for f in sorted(api.glob("*.py")):
    if f.name == "__init__.py":
        continue
    tree = ast.parse(f.read_text(encoding="utf-8"))
    local = ""
    for n in ast.walk(tree):
        if (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "router" for t in n.targets)
                and isinstance(n.value, ast.Call) and getattr(n.value.func, "id", "") == "APIRouter"):
            local = kw(n.value, "prefix")
    mod = f.stem
    base = (top + mount[mod] + local) if mod in mount else None
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for d in node.decorator_list:
            if not (isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                    and isinstance(d.func.value, ast.Name) and d.func.value.id == "router"
                    and d.args and isinstance(d.args[0], ast.Constant) and isinstance(d.args[0].value, str)):
                continue
            full = (base + d.args[0].value) if base is not None else "UNMOUNTED " + d.args[0].value
            if f.name == "export.py" or pat.search(full):
                print(f"{f.relative_to(root).as_posix()}:{d.lineno} {d.func.attr.upper()} {full} -> {node.name}")
```

Run it:

```bash
set -o pipefail
source "$HOME/.cache/asclexis-w10/w10.env"
python3 "$W10_SCRATCH/routes_inv.py" "$WT" | tee "$W10_SCRATCH/routes_inv.out"
wc -l < "$W10_SCRATCH/routes_inv.out"
git -C "$WT" grep -n "include_router" -- src/backend/api/__init__.py
```

Expected: the 14 routes of §3.5, matched by method + **mounted** path + function name (line numbers may shift post-P1), and `wc -l` = `14`. No line says `UNMOUNTED`. Any route not in the §3.5 classification table is unclassified, so stop (S5). Classify it from code, never from its docstring, and get the owner's answer before DP-2 is written. A new or changed mount prefix is also S5, and so is any `UNMOUNTED` line.

- [ ] **Step 5: Derive `W10_ARGS` once; every assertion run uses it**

```bash
set -o pipefail
source "$HOME/.cache/asclexis-w10/w10.env"
Q1=signed; GOVBG=signed; Q3=unsigned   # r5: GOV-D11 and GOV-BG signed 2026-10-07 (owner-decisions row "GOV-BG / GOV-D11"); Q3 skipped (row W-10-REST), so it stays unsigned and C-4 is not applied
A=""
if [ "$Q1" = signed ]; then A="$A --c3"; fi
if [ "$GOVBG" = signed ]; then A="$A --govbg"; fi
if [ "$Q3" = signed ]; then A="$A --c4"; fi
echo "export W10_ARGS=\"$A\"" >> "$HOME/.cache/asclexis-w10/w10.env"
source "$HOME/.cache/asclexis-w10/w10.env"; echo "W10_ARGS=[$W10_ARGS]"
```

r5: the values above are the answered state, not a default; the expected line is `W10_ARGS=[ --c3 --govbg]`. Paste the printed line into the variant table.

- [ ] **Step 6: Write the variant table** (paste into the PR body)

```text
Q1=<signed|unsigned>  GOVBG=<…>  Q3=<…>  Q4=<…>   W10_ARGS=[…]
W-2: <P|U|I> <PR#/sha or -> evidence 1-4: <y/n y/n y/n y/n>  rc_check: <OK file:line | MISS | NO-TEST>   → DP-1, DP-2
W-3: <P|U|I> <PR#/sha or -> evidence 1-4: <…>  rc_check: <…>   → DP-3
W-6: <P|U|I> <PR#/sha or -> evidence 1-4: <…>  rc_check: <…>   → DP-4
routes_inv: 14 lines, all classified in §3.5 (y/n)
```

(`U` = merged; conformance unverified. It has its own blocks in Task 4.)

---

## Task 2: RED — write the doc assertions and watch them fail (no commit)

**Files:** Create `$W10_SCRATCH/w10_assert.py` (scratch, never staged).

The script is the "test" for a docs change. Assertion IDs W10-A1…A9 are local to this plan. They are not pytest tests and are not collected. The script reads the two files under `$WT`.

- [ ] **Step 1: Create the script**

```python
#!/usr/bin/env python3
"""W-10 doc assertions. Reads $WT/CLAUDE.md and $WT/docs/compliance/data-privacy.md. Exit 1 on any failure."""
import os
import re
import sys
from pathlib import Path

C3 = "--c3" in sys.argv          # passed when Q1 is signed
GOVBG = "--govbg" in sys.argv    # passed when GOV-BG (Q2) is signed
C4 = "--c4" in sys.argv          # passed when Q3 is signed

ROOT = Path(os.environ["WT"])
claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
priv = (ROOT / "docs/compliance/data-privacy.md").read_text(encoding="utf-8")
flat = lambda s: " ".join(s.split())
fc, fp = flat(claude), flat(priv)
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")  # same pattern as scripts/docs_lint.py _MD_LINK
FENCE = re.compile("`{3}.*?`{3}", re.DOTALL)

fails = []
def check(aid, ok, msg):
    if not ok:
        fails.append(f"{aid}: {msg}")

REC = "docs/capstone-report/owner-decisions-2026-09-27.md"
# W10-A1: C-1 names the D12 ModelRunner exception
check("W10-A1", "One named exception, owner decision D12 (2026-09-27): the opt-in cloud runner in `core/external_runner.py` does not go through `ModelRunner`." in fc, "C-1 text missing")
# W10-A2: C-2 names CSV/JSON (D3), keeps the doctor summary under strict, cites the record
check("W10-A2", "the CSV and JSON exports are the patient's own data export and stay full-fidelity, like backups" in fc
      and "The doctor summary goes to a third party and must be redacted at `strict`." in fc
      and REC in fc, "C-2 D3 text missing")
# W10-A3: C-2 and DP-4 external-runner wording (D12) matches GOV-BG (Wave 6: gated again)
D12Q = "\"make strict redaction unconditional (remove the dev bypass; keep break-glass only with audit + UI warning)\""
bypass_c = "break-glass is the only bypass, and only with an audit record and a UI warning (D12: \"keep break-glass only with audit + UI warning\")" in fc
bypass_p = any(k in fp for k in ("with break-glass as the only bypass", "Break-glass is the only bypass"))
check("W10-A3", (bypass_c and bypass_p) if GOVBG else (not bypass_c and not bypass_p and D12Q in fc and D12Q in fp),
      "C-2/DP-4 break-glass wording does not match --govbg")
# W10-A4: old D11 wording gone iff C-3 applied
old62 = "Outputs are educational, grounded, cited (`[REFERENCE:N]` / `[YOUR_RESULTS:N]`)."
check("W10-A4", (old62 not in fc and "are context labels, not citation markers (owner decision D11, 2026-09-27)" in fc) if C3 else (old62 in fc), "C-3 state does not match --c3")
# W10-A5: C-4 only when signed
c4 = "is an owner-approved exception to this rule and runs only after the user opts in" in fc
check("W10-A5", c4 == C4, "C-4 state does not match --c4")
# W10-A6: DP-1/DP-2 — the false universal claim is gone, CSV/JSON named, doctor summary status present
check("W10-A6", "Every other export path passes through" not in fp
      and "This is the one export-shaped path that is intentionally unredacted." not in fp
      and "CSV and JSON are deliberate exceptions to redaction." in fp
      and "These three are the export-shaped paths that are intentionally unredacted." in fp
      and any(k in fp.split("## Reinforcement Learning Dataset Export")[0].lower()
              for k in ("not yet implemented", "conformance unverified", "implemented in `")),
      "DP-1/DP-2 text wrong")
# W10-A7: DP-3 (D4) present with a status line
check("W10-A7", "## Unverified Extracted Values" in priv and "visibly marked \"unverified\"" in fp
      and "cites verified values only, matching the agent path" in fp, "DP-3 text missing")
# W10-A8: DP-4 (D12) — old vague bullet gone
check("W10-A8", "PHI redaction applied to API prompts per `modules/redaction.py` policy" not in fp
      and "owner decision D12" in fp.split("### Optional External API")[1], "DP-4 text wrong")
# W10-A9: no markdown links outside fences in either file beyond the start counts (argv: --links=<claude>,<priv>)
start = [a for a in sys.argv if a.startswith("--links=")]
if start:
    c0, p0 = (int(x) for x in start[0].split("=")[1].split(","))
    c1 = len(LINK.findall(FENCE.sub("", claude)))
    p1 = len(LINK.findall(FENCE.sub("", priv)))
    check("W10-A9", (c1, p1) == (c0, p0), f"link count changed: CLAUDE {c0}->{c1}, privacy {p0}->{p1}")
else:
    fails.append("W10-A9: pass --links=<claude>,<privacy> from Step 2")

for f in fails:
    print("FAIL", f)
print(f"{9 - len(fails)}/9 assertions pass")
sys.exit(1 if fails else 0)
```

- [ ] **Step 2: Record the start link counts in the env file** (same regex as `docs_lint`)

```bash
set -o pipefail
source "$HOME/.cache/asclexis-w10/w10.env"
LINKS=$(python3 - <<'EOF'
import os, re
from pathlib import Path
R = Path(os.environ["WT"])
L = re.compile(r"\[[^\]]*\]\(([^)]+)\)"); F = re.compile("`{3}.*?`{3}", re.DOTALL)
print(",".join(str(len(L.findall(F.sub("", (R / p).read_text(encoding="utf-8")))))
               for p in ("CLAUDE.md", "docs/compliance/data-privacy.md")))
EOF
)
echo "export W10_LINKS=$LINKS" >> "$HOME/.cache/asclexis-w10/w10.env"
echo "W10_LINKS=$LINKS"
```

Measured 2026-09-27: `4,0` on main@40f590e and on B@7b2ff1f `CLAUDE.md` + A@692fdf3 `data-privacy.md` (§3.4). Use the number you measure post-P1.

- [ ] **Step 3: RED run**

```bash
set -o pipefail
source "$HOME/.cache/asclexis-w10/w10.env"
python3 "$W10_SCRATCH/w10_assert.py" $W10_ARGS --links="$W10_LINKS"; echo "assert exit=$?"
```

Expected: `assert exit=1`.
- W10-A1, A2, A3, A6, A7 and A8 fail under every flag combination.
- W10-A4 also fails when `W10_ARGS` contains `--c3`.
- W10-A5 and A9 pass.
- The count is therefore `2/9 assertions pass` with `--c3`, and `3/9` without it. r5: `W10_ARGS` holds `--c3`, so expect `2/9` (measured 2026-10-08).

*What this cannot notice:* whether the prose is accurate about code. That is covered by Task 1 Steps 2-4 and §3.2/§3.5, which the reviewer re-verifies.

---

## Task 3: Amend `CLAUDE.md` (no commit yet)

**Files:** Modify `CLAUDE.md` (4 anchors; post-P1 lines ≈25, 59, 60, 62).

- [ ] **Step 1: Hunk C-1 (D12, §3 ModelRunner rule)**

Before:
```text
- All LLM calls go through the `ModelRunner` facade. Never import `llama_cpp` or call Ollama directly from feature code.
```
After:
```text
- All LLM calls go through the `ModelRunner` facade. Never import `llama_cpp` or call Ollama directly from feature code. One named exception, owner decision D12 (2026-09-27): the opt-in cloud runner in `core/external_runner.py` does not go through `ModelRunner`. It is off by default, its redaction rule is under Hard invariants, and it licenses no other runner outside `ModelRunner`.
```

- [ ] **Step 2: Hunk C-2 (D3 + D12, redaction invariant)**

Before:
```text
- **Redaction before anything leaves.** Any path that writes user text to exportable files or external runners must pass through `modules/redaction.py` first.
```
After, **GOV-BG signed**:
```text
- **Redaction before anything leaves.** Any path that writes user text to exportable files or external runners must pass through `modules/redaction.py` first. Named exceptions, owner decision D3 (2026-09-27): the CSV and JSON exports are the patient's own data export and stay full-fidelity, like backups (BKUP-UX-001). The doctor summary goes to a third party and must be redacted at `strict`. The opt-in external runner must apply `strict` redaction on every call (owner decision D12); break-glass is the only bypass, and only with an audit record and a UI warning (D12: "keep break-glass only with audit + UI warning"). Record: `docs/capstone-report/owner-decisions-2026-09-27.md`. Code conformance is tracked in `docs/capstone-report/specs-compliance-matrix.md` rows PRIV-04 and LOCAL-04.
```
After, **GOV-BG unsigned** (default until signed; quotes D12 and does not call break-glass a bypass):
```text
- **Redaction before anything leaves.** Any path that writes user text to exportable files or external runners must pass through `modules/redaction.py` first. Named exceptions, owner decision D3 (2026-09-27): the CSV and JSON exports are the patient's own data export and stay full-fidelity, like backups (BKUP-UX-001). The doctor summary goes to a third party and must be redacted at `strict`. The opt-in external runner must apply `strict` redaction on every call (owner decision D12: "make strict redaction unconditional (remove the dev bypass; keep break-glass only with audit + UI warning)"). Record: `docs/capstone-report/owner-decisions-2026-09-27.md`. Code conformance is tracked in `docs/capstone-report/specs-compliance-matrix.md` rows PRIV-04 and LOCAL-04.
```
Wording checks against the licence:
- "like backups" is D3's own words, and backups are already a documented exception (matrix PRIV-05 "tested (documented exception)"; C-REDACT-1). No new exception is created.
- "must" throughout: nothing here claims the code conforms.

- [ ] **Step 3: Hunk C-3 (D11). Apply only if Q1 is signed** (r5: signed, apply)

Before:
```text
- **No medical advice.** Outputs are educational, grounded, cited (`[REFERENCE:N]` / `[YOUR_RESULTS:N]`). `interpret_safety` prohibited patterns (diagnosis, dosing) must keep passing.
```
After:
```text
- **No medical advice.** Outputs are educational, grounded, and cited. On the legacy RAG path `[cite:N]` is the validated citation marker (`modules/rag.py`, `RAGModule.validate_response`); `[YOUR_RESULTS:N]` / `[REFERENCE:N]` are context labels, not citation markers (owner decision D11, 2026-09-27). `interpret_safety` prohibited patterns (diagnosis, dosing) must keep passing.
```

Check: none of the new text has `]` immediately followed by `(`, so DOC-007 sees no link. `` `[YOUR_RESULTS:N]` / `` has a backtick between `]` and anything else.

- [ ] **Step 4: Hunk C-4 (Local-first). Apply only if Q3 is signed; default skip** (r5: Q3 skipped by the owner. Do NOT apply; `CLAUDE.md:59` stays byte-identical)

Before:
```text
- **Local-first.** No network calls in product code paths. Ollama provider is localhost-only by design — keep it that way.
```
After:
```text
- **Local-first.** No network calls in product code paths. Ollama provider is localhost-only by design — keep it that way. The opt-in external runner named in §3 (owner decision D12) is an owner-approved exception to this rule and runs only after the user opts in.
```

- [ ] **Step 5: Partial GREEN**

```bash
set -o pipefail
source "$HOME/.cache/asclexis-w10/w10.env"
python3 "$W10_SCRATCH/w10_assert.py" $W10_ARGS --links="$W10_LINKS"; echo "assert exit=$?"
git -C "$WT" diff --stat
```

Expected: `assert exit=1` with only W10-A6, A7 and A8 failing, for any `W10_ARGS`. r5 correction: with GOV-BG signed, W10-A3 also still fails here, because it checks DP-4 as well as C-2 (`5/9`); it turns green in Task 4. `git diff --stat` shows `CLAUDE.md` only, with 2-4 lines changed (one per applied hunk).

---

## Task 4: Amend `docs/compliance/data-privacy.md`, then break it on purpose (no commit yet)

**Files:** Modify `docs/compliance/data-privacy.md` (post-P1 anchors ≈ :74, :173-178, :204, :217).

Fill `<W-n sha>` in the U and I variants from Task 1 Step 3 (short sha, 7 characters).

- [ ] **Step 1: Hunk DP-1 (D3). Insert after the Data Portability table**

Before (the last table row, the blank line and the next heading; match exactly):
```text
| Doctor Summary | `POST /export/doctor-summary` | Formatted clinical report |

## Reinforcement Learning Dataset Export
```
After, variant **P** (W-2 not merged):
```text
| Doctor Summary | `POST /export/doctor-summary` | Formatted clinical report |

**Redaction scope, owner decision D3 (2026-09-27).** Record:
`docs/capstone-report/owner-decisions-2026-09-27.md`.
- **CSV and JSON are deliberate exceptions to redaction.** They are the
  patient's own data export, so they stay full-fidelity, like backups.
- **The doctor summary must be redacted at the `strict` policy level,** because
  it goes to a third party. Status: owner-approved, **not yet implemented**.
  Today the summary and its text, HTML and PDF downloads are produced without
  redaction. Tracked as W-2 in
  `docs/capstone-report/implementation-program.md` (matrix PRIV-04).

## Reinforcement Learning Dataset Export
```
After, variant **U** (W-2 merged; variant-I evidence incomplete):
```text
| Doctor Summary | `POST /export/doctor-summary` | Formatted clinical report |

**Redaction scope, owner decision D3 (2026-09-27).** Record:
`docs/capstone-report/owner-decisions-2026-09-27.md`.
- **CSV and JSON are deliberate exceptions to redaction.** They are the
  patient's own data export, so they stay full-fidelity, like backups.
- **The doctor summary must be redacted at the `strict` policy level,** because
  it goes to a third party. Status: code merged in `<W-2 sha>`; **conformance
  unverified** until W-2's red-first, break-it and HTTP-test evidence is
  recorded (matrix PRIV-04).

## Reinforcement Learning Dataset Export
```
After, variant **I** (W-2 merged and all four Task 1 Step 3 criteria hold):
```text
| Doctor Summary | `POST /export/doctor-summary` | Formatted clinical report |

**Redaction scope, owner decision D3 (2026-09-27).** Record:
`docs/capstone-report/owner-decisions-2026-09-27.md`.
- **CSV and JSON are deliberate exceptions to redaction.** They are the
  patient's own data export, so they stay full-fidelity, like backups.
- **The doctor summary is redacted at the `strict` policy level,** because it
  goes to a third party, in all three download formats (text, HTML, PDF).
  Implemented in `<W-2 sha>`; tests HC-EXPR-001…003.

## Reinforcement Learning Dataset Export
```

- [ ] **Step 2: Hunk DP-2 (D3). Replace the backup paragraph**

Before:
```text
**Backup archives are deliberately not redacted** (BKUP-UX-001). Every other
export path passes through `modules/redaction.py` because it produces something
destined for a third party. A backup is the opposite: the user's own
full-fidelity record, going to their own machine, and a redacted backup cannot
be restored. This is the one export-shaped path that is intentionally
unredacted.
```
After, variant **P**:
```text
**Backup archives are deliberately not redacted** (BKUP-UX-001). A backup is
the user's own full-fidelity record, going to their own machine, and a redacted
backup cannot be restored. The CSV and JSON exports are deliberately not
redacted on the same grounds: they are the patient's own data export (owner
decision D3, 2026-09-27; see Data Portability). These three are the
export-shaped paths that are intentionally unredacted. The exports built for a
third party pass through `modules/redaction.py` at `strict`: the visit-prep
packet, the pinboard export, the FHIR bundle and the RL dataset. Under D3 the
doctor summary must join them; that is owner-approved but not yet implemented
(W-2).
```
After, variant **U**:
```text
**Backup archives are deliberately not redacted** (BKUP-UX-001). A backup is
the user's own full-fidelity record, going to their own machine, and a redacted
backup cannot be restored. The CSV and JSON exports are deliberately not
redacted on the same grounds: they are the patient's own data export (owner
decision D3, 2026-09-27; see Data Portability). These three are the
export-shaped paths that are intentionally unredacted. The exports built for a
third party pass through `modules/redaction.py` at `strict`: the visit-prep
packet, the pinboard export, the FHIR bundle and the RL dataset. Under D3 the
doctor summary must join them; its code merged in `<W-2 sha>`, conformance
unverified (W-2).
```
After, variant **I**:
```text
**Backup archives are deliberately not redacted** (BKUP-UX-001). A backup is
the user's own full-fidelity record, going to their own machine, and a redacted
backup cannot be restored. The CSV and JSON exports are deliberately not
redacted on the same grounds: they are the patient's own data export (owner
decision D3, 2026-09-27; see Data Portability). These three are the
export-shaped paths that are intentionally unredacted. The exports built for a
third party pass through `modules/redaction.py` at `strict`: the visit-prep
packet, the pinboard export, the FHIR bundle, the RL dataset and, under D3, the
doctor summary (implemented in `<W-2 sha>`).
```

- [ ] **Step 3: Hunk DP-3 (D4). Insert a section before Third-Party Data Sharing**

Before:
```text
## Third-Party Data Sharing
```
After, variant **P** (W-3 not merged):
```text
## Unverified Extracted Values

Values extracted from an imported document are stored as unverified until the
user confirms them. Owner decision D4 (2026-09-27): trends may show unverified
points, but each must be visibly marked "unverified"; the legacy assistant
(RAG) path cites verified values only, matching the agent path. Status:
owner-approved, **not yet implemented**. Today the trends response carries no
verification flag and legacy RAG retrieval does not filter on it. Tracked as
W-3 in `docs/capstone-report/implementation-program.md` (matrix SAFE-02).

## Third-Party Data Sharing
```
After, variant **U** (W-3 merged; variant-I evidence incomplete):
```text
## Unverified Extracted Values

Values extracted from an imported document are stored as unverified until the
user confirms them. Owner decision D4 (2026-09-27): trends may show unverified
points, but each must be visibly marked "unverified"; the legacy assistant
(RAG) path cites verified values only, matching the agent path. Status: code
merged in `<W-3 sha>`; **conformance unverified** until W-3's red-first,
break-it and HTTP-test evidence is recorded (matrix SAFE-02).

## Third-Party Data Sharing
```
After, variant **I** (W-3 merged and all four Task 1 Step 3 criteria hold):
```text
## Unverified Extracted Values

Values extracted from an imported document are stored as unverified until the
user confirms them. Owner decision D4 (2026-09-27): trends show unverified
points visibly marked "unverified", and the legacy assistant (RAG) path cites
verified values only, matching the agent path. Implemented in `<W-3 sha>`;
tests HC-VER-001, HC-VER-002 and the trends-chart vitest.

## Third-Party Data Sharing
```

Note: A7 checks the phrase "cites verified values only, matching the agent path", and all three variants (P, U, I) contain it.

- [ ] **Step 4: Hunk DP-4 (D12). Replace the redaction bullet under Optional External API**

Before:
```text
- PHI redaction applied to API prompts per `modules/redaction.py` policy
```
**r5: use the variant-U, GOV-BG-signed block.** W-6 is merged, so both variant-P blocks below are superseded (their "Today, outside production …" sentence is false since `2f0cb6f`); variant I is not allowed (criterion 4 fails, §3.6).

After, variant **P** (W-6 not merged; **superseded, do not use**), GOV-BG signed:
```text
- PHI redaction: owner decision D12 (2026-09-27) requires `strict` redaction
  through `modules/redaction.py` on every external call, with break-glass as
  the only bypass, allowed only with an audit record and a UI warning. Status:
  owner-approved, **not yet implemented**. Today, outside production, a
  disabled or non-strict redaction setting still reaches the provider
  (`core/external_runner.py`). Tracked as W-6 (matrix LOCAL-04).
```
After, variant **U** (W-6 merged; variant-I evidence incomplete), GOV-BG signed. r5: the tail no longer says "until W-6's red-first, break-it and HTTP-test evidence is recorded", because PR #32 does record the red-first and break-it runs; only the HTTP-test check is unmet (§3.6):
```text
- PHI redaction: owner decision D12 (2026-09-27) requires `strict` redaction
  through `modules/redaction.py` on every external call, with break-glass as
  the only bypass, allowed only with an audit record and a UI warning. Status:
  code merged in `2f0cb6f` (W-6); **conformance unverified** (matrix
  LOCAL-04).
```
After, variant **I** (W-6 merged; first re-read W-6's merged diff and confirm that both conditions hold as written), GOV-BG signed:
```text
- PHI redaction: `strict` through `modules/redaction.py` on every external
  call (owner decision D12, 2026-09-27; implemented in `<W-6 sha>`).
  Break-glass is the only bypass, and it is allowed only with an audit record
  and a UI warning.
```
**If GOV-BG is unsigned**, use these blocks instead of the three above. They quote D12 and do not call break-glass a bypass.

After, variant **P**, GOV-BG unsigned:
```text
- PHI redaction: owner decision D12 (2026-09-27) requires `strict` redaction
  through `modules/redaction.py` on every external call. D12: "make strict
  redaction unconditional (remove the dev bypass; keep break-glass only with
  audit + UI warning)". Status: owner-approved, **not yet implemented**.
  Today, outside production, a disabled or non-strict redaction setting
  still reaches the provider (`core/external_runner.py`). Tracked as W-6
  (matrix LOCAL-04).
```
After, variant **U**, GOV-BG unsigned:
```text
- PHI redaction: owner decision D12 (2026-09-27) requires `strict` redaction
  through `modules/redaction.py` on every external call. D12: "make strict
  redaction unconditional (remove the dev bypass; keep break-glass only with
  audit + UI warning)". Status: code merged in `<W-6 sha>`; **conformance
  unverified** until W-6's red-first, break-it and HTTP-test evidence is
  recorded (matrix LOCAL-04).
```
After, variant **I**, GOV-BG unsigned (same diff re-read as above):
```text
- PHI redaction: `strict` through `modules/redaction.py` on every external
  call (owner decision D12, 2026-09-27; implemented in `<W-6 sha>`). D12:
  "make strict redaction unconditional (remove the dev bypass; keep
  break-glass only with audit + UI warning)".
```

W10-A3 checks the choice in both files (`--govbg` is in `W10_ARGS` only when GOV-BG is signed).
- [ ] **Step 5: GREEN**

```bash
set -o pipefail
source "$HOME/.cache/asclexis-w10/w10.env"
python3 "$W10_SCRATCH/w10_assert.py" $W10_ARGS --links="$W10_LINKS"; echo "assert exit=$?"
python3 "$WT/scripts/docs_lint.py"; echo "docs_lint exit=$?"
python3 "$WT/scripts/generate_docs_index.py" --check; echo "index_check exit=$?"
git -C "$WT" diff --stat
```

Expected:
- `9/9 assertions pass`, exit 0.
- `Docs lint passed.` with exit 0.
- `docs/INDEX.md and docs/_link_graph.json are fresh.` with exit 0.
- `git diff --stat` shows exactly `CLAUDE.md` and `docs/compliance/data-privacy.md`.

- [ ] **Step 6: Break it on purpose (recurring failure #1), then restore**

`docs/compliance/data-privacy.md` is **owned** by this plan, so the global rule for read-only files does not apply here. Restore is by byte copy verified with `cmp`, never by `git checkout --`.

```bash
set -o pipefail
source "$HOME/.cache/asclexis-w10/w10.env"
DP="$WT/docs/compliance/data-privacy.md"
cp "$DP" "$W10_SCRATCH/dp.bak"
# (a) a real, resolvable markdown link: docs_lint still passes, but the index gate must go red
printf '\nSee [decisions](../capstone-report/owner-decisions-2026-09-27.md).\n' >> "$DP"
python3 "$WT/scripts/generate_docs_index.py" --check; echo "index_check exit=$?"   # expect non-zero, "stale"
python3 "$W10_SCRATCH/w10_assert.py" $W10_ARGS --links="$W10_LINKS"; echo "assert exit=$?"  # expect W10-A9 FAIL
cp "$W10_SCRATCH/dp.bak" "$DP" && cmp "$W10_SCRATCH/dp.bak" "$DP" && echo restored-a
# (b) restore the old universal claim: A6 must go red
printf '\nEvery other export path passes through `modules/redaction.py`.\n' >> "$DP"
python3 "$W10_SCRATCH/w10_assert.py" $W10_ARGS --links="$W10_LINKS"; echo "assert exit=$?"  # expect W10-A6 FAIL
cp "$W10_SCRATCH/dp.bak" "$DP" && cmp "$W10_SCRATCH/dp.bak" "$DP" && echo restored-b
python3 "$W10_SCRATCH/w10_assert.py" $W10_ARGS --links="$W10_LINKS" && python3 "$WT/scripts/generate_docs_index.py" --check
```

Expected: (a) index check non-zero ("docs/INDEX.md is stale.") **and** W10-A9 fails; `restored-a`. (b) W10-A6 fails; `restored-b`. The last line then passes again (`9/9`, "fresh").

*What these checks cannot notice:* a sentence that is well-formed but false about code. The reviewer re-verifies each §3.2 row on the post-P1 tree.

---

## Task 4b (r5): the three fold-ins, one commit each, after the governance commit

**Order:** Tasks 3-4 → Task 5 Steps 1-3 (the governance commit, 2 files) → this task → Task 5 Step 4 (push, PR).

**Licence:** owner-decisions rows W-10-REST and W10-HIPAA (2026-10-07), quoted in §1.2. These hunks state what the code does (§3.6 evidence table). They add no exception, no "must" rule and no compliance conclusion.

**Files:** `docs/compliance/data-privacy.md`, `docs/compliance/hipaa-controls.md` (lines `:49` and `:52` only), `CLAUDE.md` (`:50` only).

- [ ] **Step 1: Create `$W10_SCRATCH/w10_foldin_assert.py` and watch it fail**

```python
#!/usr/bin/env python3
"""W-10 fold-in assertions (r5). Reads $WT. Usage: w10_foldin_assert.py --hlinks=<n>
Exit 1 on any failure. IDs W10-F1…F7 are local to this plan; they are not pytest tests."""
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ["WT"])
read = lambda p: (ROOT / p).read_text(encoding="utf-8")
flat = lambda s: " ".join(s.split())
claude, priv, hipaa = read("CLAUDE.md"), read("docs/compliance/data-privacy.md"), read("docs/compliance/hipaa-controls.md")
fc, fp, fh = flat(claude), flat(priv), flat(hipaa)
base = lambda p: subprocess.run(["git", "-C", str(ROOT), "show", f"origin/main:{p}"], capture_output=True, text=True, check=True).stdout
LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
FENCE = re.compile("`{3}.*?`{3}", re.DOTALL)

fails = []
def check(aid, ok, msg):
    if not ok:
        fails.append(f"{aid}: {msg}")

# W10-F1 (LOCAL-07): the two false bullets are gone; the composed prompt is named
check("W10-F1", "Only the specific query text is sent to the external provider" not in fp
      and "Full health records are never transmitted" not in fp
      and "the whole prompt the assistant composes for that request, not only the question" in fp
      and "so health information in the prompt does reach the provider" in fp, "DP-5 text wrong")
# W10-F2 (DOC-OVERCLAIM, data-privacy): no log-file claim in the Tier 3 table
check("W10-F2", "Master DB + log file" not in priv and "| Security events | Log file |" not in priv
      and "| Audit logs | Master DB (not encrypted). No log file is written |" in priv, "DP-6 text wrong")
# W10-F3 (DOC-OVERCLAIM, hipaa :49): no correlation-ID claim for audit rows
check("W10-F3", "Structured JSON with timestamps and correlation IDs" not in fh
      and "They have no correlation-ID column" in fh, "HC-1 text wrong")
# W10-F4 (DOC-OVERCLAIM, hipaa :52): no append-only claim
check("W10-F4", "Audit log entries are append-only" not in fh and "| Immutability | Not append-only." in fh, "HC-2 text wrong")
# W10-F5: hipaa-controls.md differs from origin/main in exactly 2 lines, and the Key rotation row (:169) is unchanged
b = base("docs/compliance/hipaa-controls.md").splitlines()
h = hipaa.splitlines()
changed = [i + 1 for i, (x, y) in enumerate(zip(b, h)) if x != y]
check("W10-F5", len(b) == len(h) and changed in ([], [49, 52])
      and "| Key rotation | Medium | Manual via password change |" in hipaa,
      f"hipaa-controls.md changed lines {changed} (want [49, 52]) or the :169 row moved")
# W10-F6 (CLAUDE-FAILURE-COUNT): the word in CLAUDE.md equals the measured number of "## N." sections
count = len(re.findall(r"^## \d+\. ", read("docs/agentic/recurring-failures.md"), re.M))
WORDS = {8: "Eight", 9: "Nine", 10: "Ten", 11: "Eleven", 12: "Twelve"}
check("W10-F6", f"before claiming done.** {WORDS.get(count, str(count))} failure modes this repo has actually produced," in fc,
      f"CLAUDE.md does not say {WORDS.get(count, count)} (measured {count} sections)")
# W10-F7: the baseline-count slots are byte-identical to origin/main, and no markdown link was added to hipaa-controls.md
slot = lambda s: [l for l in s.splitlines() if "1370" in l or "1288" in l]
hl = [a for a in sys.argv if a.startswith("--hlinks=")]
check("W10-F7", slot(claude) == slot(base("CLAUDE.md")) and len(slot(claude)) == 3
      and bool(hl) and len(LINK.findall(FENCE.sub("", hipaa))) == int(hl[0].split("=")[1]),
      "CLAUDE.md count slots changed, or hipaa-controls.md link count changed (pass --hlinks=<start count>)")

for f in fails:
    print("FAIL", f)
print(f"{7 - len(fails)}/7 fold-in assertions pass")
sys.exit(1 if fails else 0)
```

```bash
set -o pipefail
source "$HOME/.cache/asclexis-w10/w10.env"
HL=$(python3 - <<'EOF'
import os, re
from pathlib import Path
L = re.compile(r"\[[^\]]*\]\(([^)]+)\)"); F = re.compile("`{3}.*?`{3}", re.DOTALL)
print(len(L.findall(F.sub("", (Path(os.environ["WT"]) / "docs/compliance/hipaa-controls.md").read_text(encoding="utf-8")))))
EOF
)
echo "export W10_HLINKS=$HL" >> "$HOME/.cache/asclexis-w10/w10.env"; echo "W10_HLINKS=$HL"
python3 "$W10_SCRATCH/w10_foldin_assert.py" --hlinks="$HL"; echo "foldin exit=$?"
```

Expected RED, run after the governance commit and before Step 2: `FAIL W10-F1`, `F2`, `F3`, `F4`, `F6`; `2/7 fold-in assertions pass`; exit 1. F5 and F7 pass on the unpatched files.

- [ ] **Step 2: Fold-in 1, LOCAL-07 (hunk DP-5). Replace the first two bullets under "Optional External API"**

Before (`data-privacy.md`, two lines; match exactly once):
```text
- Only the specific query text is sent to the external provider
- Full health records are never transmitted
```
After:
```text
- What is sent: the whole prompt the assistant composes for that request, not
  only the question. The prompt holds the assistant's instructions, the context
  retrieved for the question (summaries of the patient's own results, passages
  from their documents, and reference text) and the question. In assistant
  chat it also holds earlier turns of the chat session and, when memory is
  switched on, saved memory items (`modules/rag.py`, `compose_prompt` and
  `query`). Two features can use the external provider: assistant chat when it
  answers through the legacy RAG path, and the grounded interpretation of a
  single result.
- The prompt is redacted before it is sent (see the PHI redaction bullet
  below). `strict` redaction removes the identifier patterns it has rules for:
  SSNs, emails, phone numbers, context-prefixed names, dates of birth, street
  addresses, MRNs and slash/dash numeric dates. It does not remove lab values, analyte names,
  document passages or ISO-8601 dates, so health information in the prompt does
  reach the provider. The prompt is built from the context retrieved for that
  request, not from an export of the whole vault.
```

Commit: `git -C "$WT" add -- docs/compliance/data-privacy.md` → `git diff --cached --name-only` prints that 1 path → `docs(privacy): state what the external provider receives (LOCAL-07)`.

- [ ] **Step 3: Fold-in 2, DOC-OVERCLAIM (hunks DP-6, HC-1, HC-2)**

DP-6, `data-privacy.md` Tier 3 table. Before (2 separate lines, each matches once):
```text
| Audit logs | Master DB + log file | Indefinite |
```
```text
| Security events | Log file | Per log rotation policy |
```
After:
```text
| Audit logs | Master DB (not encrypted). No log file is written | Indefinite |
```
```text
| Security events | Application logger only, to the process's stderr; no log file is written. The request lines from `SecurityAuditMiddleware` are logged at INFO, below the default WARN level, so by default they are not emitted | Not retained by the app |
```

HC-1, `hipaa-controls.md:49`. Before:
```text
| Log format | Structured JSON with timestamps and correlation IDs |
```
After:
```text
| Log format | Audit rows are database rows (`models/audit.py`): typed columns with a timestamp, plus a JSON `details_json` field. They have no correlation-ID column. The `SecurityAuditMiddleware` log line is a JSON payload that carries the request correlation ID; it is logged at INFO, below the default WARN level, so by default the ID appears in no operator-visible output |
```

HC-2, `hipaa-controls.md:52`. Before:
```text
| Immutability | Audit log entries are append-only |
```
After:
```text
| Immutability | Not append-only. Application code only inserts audit rows, with one exception: deleting a profile deletes that profile's audit rows and keeps one anonymized tombstone (PROF-DEL-001, `api/profiles.py`). The database does not enforce immutability |
```

Do not touch any other line of `hipaa-controls.md`. `:169` ("Key rotation … Manual via password change") stays as it is (owner row W10-HIPAA). `:50-51` and `data-privacy.md:47` are reported, not edited (§1.4 #8).

Commit: `git -C "$WT" add -- docs/compliance/data-privacy.md docs/compliance/hipaa-controls.md` → exactly those 2 paths → `docs(compliance): correct the log-file, correlation-ID and append-only claims (DOC-OVERCLAIM)`.

- [ ] **Step 4: Fold-in 3, CLAUDE-FAILURE-COUNT (hunk C-5)**

Measure first: `grep -cE '^## [0-9]+\. ' "$WT/docs/agentic/recurring-failures.md"` (2026-10-08: `10`). Write the number you measure.

Before (`CLAUDE.md`, 1 line; match exactly once):
```text
  before claiming done.** Eight failure modes this repo has actually produced,
```
After (for a measured count of 10):
```text
  before claiming done.** Ten failure modes this repo has actually produced,
```

Commit: `git -C "$WT" add -- CLAUDE.md` → 1 path → `docs: CLAUDE.md states the measured count of recurring-failure modes (CLAUDE-FAILURE-COUNT)`.

- [ ] **Step 5: GREEN and the gates, after the third fold-in commit**

```bash
set -o pipefail
source "$HOME/.cache/asclexis-w10/w10.env"
python3 "$W10_SCRATCH/w10_foldin_assert.py" --hlinks="$W10_HLINKS"; echo "foldin exit=$?"      # expect 7/7
python3 "$W10_SCRATCH/w10_assert.py" $W10_ARGS --links="$W10_LINKS"; echo "assert exit=$?"      # still 9/9
python3 "$WT/scripts/docs_lint.py"; python3 "$WT/scripts/generate_docs_index.py" --check
python3 "$WT/scripts/harness_drift_check.py"; python3 "$WT/scripts/repo_hygiene_check.py"; python3 "$WT/scripts/feature_list_lint.py"
git -C "$WT" diff --stat origin/main -- docs/compliance/hipaa-controls.md   # expect 2 insertions, 2 deletions
```

Break-it for the fold-ins (recurring failure #1): append the old sentence `Full health records are never transmitted` to a scratch copy of `data-privacy.md` in the worktree, run the script (expect `FAIL W10-F1`), restore by `cp` + `cmp` as in Task 4 Step 6.

*What these checks cannot notice:* a sentence that is well-formed but false about code. Each sentence is tied to a `file:line` in §3.6, and the reviewers re-open those lines.

---

## Task 5: End measurement, stage, commit, PR

**Files:** the two owned files only (governance commit). r5: Steps 1-3 run before Task 4b; Step 4 runs after it.

- [ ] **Step 1: End measurement**

```bash
set -o pipefail
source "$HOME/.cache/asclexis-w10/w10.env"
# r5: collect-only, as in Task 0 Step 4
(cd "$WT/src/backend" && HF_HUB_OFFLINE=1 "$PY" -m pytest tests/ -p no:cacheprovider --collect-only -q 2>&1 | tail -1)
(cd "$WT/src/backend" && HF_HUB_OFFLINE=1 "$PY" -m pytest tests/test_docs_lint.py -p no:cacheprovider -q 2>&1 | tail -3)
git -C "$WT" diff --name-only    # expect exactly the 2 files
git -C "$WT" status --short      # expect exactly the 2 files, " M"
```

Acceptance:
- collected is **equal** to Task 0 (this plan adds no tests);
- r5: the full suite is not run (docs-only diff), so "failures ⊆ Task 0 failures" is reported as **skipped**, with this reason;
- `tests/test_docs_lint.py` has no new failure.

- [ ] **Step 2: Stage explicit pathspecs and check**

```bash
set -o pipefail
source "$HOME/.cache/asclexis-w10/w10.env"
git -C "$WT" add -- CLAUDE.md docs/compliance/data-privacy.md
git -C "$WT" diff --cached --name-only
```

Expected output, exactly:
```text
CLAUDE.md
docs/compliance/data-privacy.md
```
Never `git add -A` or `git add .`. Anything else staged: `git -C "$WT" restore --staged <path>` and investigate.

- [ ] **Step 3: Commit.** Remove the C-3 / C-4 lines from the body if not applied, and set P/I per Task 1. r5: GOV-BG signed, C-3 applied, no C-4; variants W-2=P, W-3=P, W-6=U; the body also cites the owner rows GOV-BG / GOV-D11, W-10-REST and W10-Q4 / W10-Q5.

```bash
set -o pipefail
source "$HOME/.cache/asclexis-w10/w10.env"
git -C "$WT" commit -F - <<'EOF'
docs: name owner-approved exceptions to the redaction and ModelRunner invariants

Governance commit required by owner-decisions Consequence #1
(docs/capstone-report/owner-decisions-2026-09-27.md). Invariant text only;
no code, tests or config.

CLAUDE.md
- C-1 (D12): core/external_runner.py named as the one ModelRunner exception.
- C-2 (D3, D12): CSV/JSON named as deliberate redaction exceptions; doctor
  summary must be strict-redacted; external runner strict on every call,
  break-glass only with audit record + UI warning (GOV-BG <signed|unsigned>:
  signed names it the only bypass; unsigned quotes D12 verbatim).
- C-3 (D11, owner-confirmed Q1): [cite:N] is the validated legacy marker;
  [YOUR_RESULTS:N]/[REFERENCE:N] are context labels.
  (If Q1 is unsigned, delete these two lines and add instead:
  "CLAUDE.md:62 unchanged; D11 wording is an open owner item.")

docs/compliance/data-privacy.md
- DP-1, DP-2 (D3): redaction scope of CSV/JSON/doctor summary; the false
  "every other export path" sentence replaced by an enumerated list.
- DP-3 (D4): unverified values on trends and legacy RAG.
- DP-4 (D12): external-runner redaction bullet.
Status variants: W-2=<P|U|I>, W-3=<…>, W-6=<…> (U = merged, conformance
unverified; evidence and rc_check lines in PR).
Export inventory: 14 routes, all classified (AST scan incl. /feedback/export).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
git -C "$WT" show --stat HEAD
```

Expected: `git show --stat HEAD` lists the 2 files only.

- [ ] **Step 4: Push and open the PR, then STOP for the owner's merge**

```bash
set -o pipefail
source "$HOME/.cache/asclexis-w10/w10.env"
git -C "$WT" push -u origin docs/w10-governance-amendments
```

r5: push only after Task 4b, the Codex diff review and the two agent reviews. The PR title starts `docs(governance):`.

The PR body (handoff §6) must contain:
1. start/end measurements (Task 0 Step 4, Task 5 Step 1), with interpreter and command;
2. the RED→GREEN assertion output and the break-it output;
3. the variant table (with `W10_ARGS`, the evidence columns, and the `routes_inv` result);
4. contract/matrix effects (§2);
5. the file list per commit (governance commit: 2 files);
5a. r5: the owner-decisions rows used, quoted verbatim; a table "sentence → code evidence `file:line`" for every changed sentence that describes code; both Codex verdicts; what W-10b must flip;
6. the unsigned Q-boxes that remain, including `CLAUDE.md:62` as an open owner item if Q1 is unsigned;
7. one next action.

End it with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

---

## Task 6 (W-10b, deferred): flip status lines after W-2 / W-3 / W-6 merge

Run once after the last of W-2/W-3/W-6 merges. Skip it if Task 1 already chose I for all three.

**Files:** `docs/compliance/data-privacy.md` only. `CLAUDE.md` never needs a flip, because its text is normative (§5).

- [ ] **Step 1:** Fresh worktree: in `w10.env` set `WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w10b`, then `git -C "$MAIN" worktree add "$WT" -b docs/w10b-privacy-status origin/main`.
- [ ] **Step 2:** Re-run Task 1 Steps 2-5. An item flips to I only when all four Task 1 Step 3 criteria hold. Otherwise it stays P, or becomes U if merged, and S6 applies.
- [ ] **Step 3:** For each item, replace the committed P or U block from Task 4 with its I block. Anchor on the committed text. For DP-4, first read W-6's merged diff and confirm that both "audit record" and "UI warning" exist in code. If they do not, stop (S6). For DP-3, reconcile with the W-3 plan's §11 list ([W-3 plan](2026-09-27-W03-verified-only-rag-and-trend-labels.md)). Add only what W-3 actually merged, stated as implemented fact and nothing wider than D4: the no-LLM fallback also verified-only; verified-document chunks only if W-3's O-5 was signed; the O-3 residue (interpretations question text) as a named gap.
- [ ] **Step 4:** `python3 "$W10_SCRATCH/w10_assert.py" $W10_ARGS --links="$W10_LINKS"`, then `python3 "$WT/scripts/docs_lint.py"` and `python3 "$WT/scripts/generate_docs_index.py" --check`, then `git -C "$WT" add -- docs/compliance/data-privacy.md && git -C "$WT" diff --cached --name-only`. Expect exactly `docs/compliance/data-privacy.md`.
- [ ] **Step 5:** Commit `docs(privacy): mark D3/D4/D12 behaviour implemented (W-2 <sha>, W-3 <sha>, W-6 <sha>)`, with the Co-Authored-By trailer; PR; STOP.

---

## 8. Stop gates (stop and ask; do not improvise)

| # | Condition | Ask whom |
|---|---|---|
| S1 | P0-B, P1 or P4 not on `origin/main`, and no written orchestrator waiver | orchestrator |
| S2 | A hunk needs wording the option text does not cover, e.g. naming break-glass environments, adding a third exception, or naming the runner under Local-first without Q3 | owner |
| S3 | A Before anchor matches 0 or more than 1 time, because another phase changed it | orchestrator: re-sequence; never merge texts by guess |
| S4 | `docs_lint.py` or `generate_docs_index.py --check` fails on the **start** tree | orchestrator (not W-10's to fix) |
| S5 | The AST export-route inventory (Task 1 Step 4) prints a route that is not classified in §3.5, or a new `include_router` mount | owner: third-party, patient-own, or not export-shaped? Classify from code; DP-2 must cover it before commit |
| S6 | A W-item's merge status cannot be established from its PR (Task 1 Step 2), or it has merged but any of the four variant-I criteria (Task 1 Step 3) is missing, or W-6's code does not match "audit record + UI warning" | orchestrator; use variant U ("code merged in `<sha>`; conformance unverified"), never I |
| S7 | `git diff --cached --name-only` shows anything besides the 2 files (r5: besides the files Task 4b names for a fold-in commit) | unstage and investigate; never `git reset` shared work |
| S9 (r5) | The code contradicts a Task 4b After block, or a fold-in needs an edit to `hipaa-controls.md:169`, the Local-first line, product code or an ask-first file | orchestrator / owner; do not soften the sentence on your own |
| S8 | Any pytest failure not in the Task 0 start set | stop; a docs change should not cause one, so find out why |

## 9. Rollback

- Before merge, after push/PR: `gh pr close <PR#> --delete-branch` (closes the PR and deletes the remote branch), then `git -C "$MAIN" worktree remove "$WT"` and `git -C "$MAIN" branch -D docs/w10-governance-amendments`.
- Before push: `git -C "$MAIN" worktree remove --force "$WT"` and `git -C "$MAIN" branch -D docs/w10-governance-amendments`.
- After merge: `git revert <W-10 sha>` on main through a PR, a single commit touching the same 2 files. This restores the pre-amendment invariants, so CSV/JSON again violate `CLAUDE.md:60` as written, and D12's named exception disappears. Any W-10b commit must be reverted first (it anchors on W-10 text). There is no schema, code or index to unwind.

## 10. Owner and orchestrator sign-offs

**r5 (2026-10-08): answered in `docs/capstone-report/owner-decisions-2026-09-27.md`.** The boxes below are left unticked on purpose: the executor does not tick owner boxes; L0 records sign-offs. The owner's answers, verbatim (rows on `origin/main` `777adf5`):

| Q | Owner-decisions row (line) | Option text, verbatim | Effect here |
|---|---|---|---|
| Q1 · GOV-D11, Q2 · GOV-BG | GOV-BG / GOV-D11 (`:65`), **Sign both** | "W-10 uses the GOV-BG-signed text (break-glass named as the only bypass, with its audit and warning conditions) and applies the D11 label wording. Both match what the code does since W-5 and W-6." | C-3 applied; C-2 and DP-4 use the GOV-BG-signed blocks; `W10_ARGS=" --c3 --govbg"` |
| Q3, DP-4 variant, fold-ins | W-10-REST (`:68`), **Defaults + fold-ins** | "Q3 skipped (Local-first line unchanged); W-6 described as \"merged; conformance unverified\"; the three doc contradictions fixed as separate commits in the W-10 PR. Codex reviews the plan before it runs." | C-4 not applied; DP-4 variant U; Task 4b |
| Q4, Q5 | W10-Q4 / W10-Q5 (`:75`), **Land now, keep wording** | "W-10 runs in Wave 4 with 'not yet implemented' status lines for W-2 and W-3; W-10b flips them later. 'like backups' stays, as a comparison only, not a new exception." | variant P for DP-1, DP-2, DP-3; "like backups" kept in C-2, DP-1, DP-2 |
| hipaa-controls scope | W10-HIPAA (`:76`), **Include both lines** | "W-10 also corrects hipaa-controls.md:49 and :52 to match the code (no correlation-ID column in the audit table; audit rows are deleted on profile delete), as its own commit. Line :169 stays untouched (it waits on the P8 Brief 2 decision)." | hunks HC-1, HC-2; `:169` untouched |

The PR merge box stays open. Original table (as written before the answers):

| Q | Question | Plan default / recommendation | Sign-off |
|---|---|---|---|
| Q1 · **GOV-D11** | Include D11 hunk C-3 (`CLAUDE.md:62`) in this governance commit? The handoff scopes W-10 to D3/D12. W-5 §6 recommends that W-10 absorb it | **recommend include** (§1.3). If unsigned, skip; `:62` stays unchanged as an open owner item. It does not go to P4 | ☐ owner/orchestrator: ____ date: ____ |
| Q2 · **GOV-BG** | *(Wave 6, 3a M-3: a gate again; r3 had called it "not a gate".)* Name audited break-glass as the only bypass of "Redaction before anything leaves" in `CLAUDE.md:60` (C-2) and `data-privacy.md` (DP-4)? D12 says "keep break-glass only with audit + UI warning", but Consequence #1 names the runner only as a *ModelRunner* exception, so the bypass wording is an inference. This one gate also answers W-6 §11 Q2 | **recommend include**. If unsigned, C-2 and DP-4 quote D12's conditions verbatim and do not call break-glass a bypass (Task 4) | ☐ owner: ____ date: ____ |
| Q3 | Also name the external runner as an owner-approved exception to **Local-first** (`CLAUDE.md:59`, hunk C-4)? D12's text licenses only the ModelRunner exception | **default skip** (owner-gated). Leaving `:59` unqualified keeps a known contradiction; the owner decides | ☐ owner: ____ date: ____ |
| Q4 | Land W-10 in the handoff §3 slot (after P4, before W-2/W-3/W-6), with P variants and a W-10b flip later? The alternative is to wait for all three and use I variants | **recommend the §3 slot** (§5) | ☐ orchestrator: ____ date: ____ |
| Q5 | `CLAUDE.md` C-2 says "like backups (BKUP-UX-001)": D3's own phrase, citing an existing documented exception (PRIV-05). Confirm this is not read as a new exception | recommend keep | ☐ owner: ____ date: ____ |
| — | PR merge | — | ☐ owner: ____ date: ____ |

## 11. Out-of-scope follow-ups (not in this diff; route each)

| # | Item | Evidence | Suggested owner |
|---|---|---|---|
| F-1 | `skills/asclexis-guardrails/SKILL.md:63` lists "bypass redaction for any reason" under **Never**, while D12 keeps audited break-glass | B@7b2ff1f `:60-64` | P4 (after W-6) or a separate owner-approved `docs:` commit |
| F-2 | `data-privacy.md` "Only the specific query text is sent to the external provider" and "Full health records are never transmitted" (A@692fdf3 `:213-214`; main `:196-197`) are **false**. `modules/rag.py:1257-1268` sends the whole composed prompt (question + retrieved observation/document chunks + history + optional memory) to the override runner | code read 2026-09-27 | owner-visible privacy correction. No D-decision covers it, so it is kept out of the governance diff. Not P4 (P04 §1 #2 routes every `data-privacy.md` edit to W-10); registered as program owner item LOCAL-07, proposed home a W-10 addendum or its own `docs:` commit, owner decides. **r5: decided (owner row W-10-REST): folded into this PR as its own commit, Task 4b Step 2** |
| F-3 | `api/backup.py:10-15` docstring: "Every other export path in this app passes [through redaction]". False for CSV/JSON (and for the doctor summary until W-2) | main@40f590e | W-2 PR (product file, comment-only) |
| F-4 | `docs/architecture/pipelines.md:53-56` claims all consumers are verified-only (D4); the W-5 §6 table rows (D11) | contract C-VERIFY-2; W-5 §6 | P4 for D11 rows; W-3 PR or P4 for pipelines (after W-3, or with a status line) |
| F-5 | Program P4 bullets "`data-privacy.md:173-174` wording, after D3" and the `CLAUDE.md:62` part of "citation-marker vocabulary" are no longer P4's. The data-privacy wording belongs to W-10. `:62` belongs to W-10 if Q1 is signed; otherwise it is an open owner item and stays unchanged. The program's order "`data-privacy.md` (P1 → P4 → G-A1)" becomes "P1 → W-10 → W-10b" (P4 does not edit it) | `implementation-program.md:69,195,197` @5d56557 → now `:154`, `:302`, `:304` (applied) | capstone maintainer; P4 executor must skip them |
| F-6 | After merge: contract C-REDACT-1 "Backups are the single documented exception", C-LLM-1 deviation 2 "OWNER-GATED", C-LOCAL-1 known exceptions, and matrix PRIV-04/LLM-01 text need updating | contract §1, §6, §7 | capstone maintainer (W-10 reports, does not edit) |

## 12. Recurring-failures recheck ([recurring-failures.md](../agentic/recurring-failures.md))

| # | Mode | Applies | Concrete recheck |
|---|---|---|---|
| 1 | Green suite that could not fail | yes | `w10_assert.py` observed RED first (Task 2), and two deliberate breaks go red (Task 4 Step 6): the index gate on a new link, and A6 on the old claim |
| 2 | Fix that creates the next bug one layer over | yes | A new markdown link would stale `INDEX.md`/`_link_graph.json` (§3.3). Adjacent stale claims are listed, not silently left (F-1…F-4) |
| 3 | Figures asserted | yes | Collected counts and link counts come from Task 0/5 output. Variant I needs four measured or recorded pieces of evidence (Task 1 Step 3), never test IDs alone |
| 4 | Environment-dependent results | low | Docs gates are pure Python. The pytest run names its interpreter. `test_api_rag_index_002b` may fail environmentally; it must be in the start set |
| 5 | Contaminated tree | yes | Dedicated worktree; explicit 2-path `git add`; `git diff --cached --name-only` must print exactly 2 lines |
| 6 | Documented commands nobody ran | yes | The author ran these (§3.4, §3.5): the anchor greps, the link counting, the P/U/I patches with `w10_assert.py` under several flag sets, and `routes_inv.py` on B and main. `gh pr view` and the pytest runs need merged W-items and the D9 venv, so they are UNMEASURED here. The executor reports any command that fails as a plan defect |
| 7 | SQL three-valued logic | no | no queries |
| 8 | Stale guidance that reads as authority | **central** | This commit exists to remove three: `CLAUDE.md:60` (contradicted by CSV/JSON and break-glass), `data-privacy.md:173-178` ("every other export path"), and `CLAUDE.md:62` if Q1 is signed. The handoff's acceptance omitted the index gate (§3.3); corrected here |

## 13. Commit plan (summary)

| Commit | Pathspecs | Prefix | Gate |
|---|---|---|---|
| r5 plan amendments (first commit) | this plan file | `docs(plan):` | `docs_lint.py`; `generate_docs_index.py --check` |
| W-10 governance | `CLAUDE.md docs/compliance/data-privacy.md` | `docs:` | `w10_assert.py` 9/9; `docs_lint.py` "Docs lint passed."; `generate_docs_index.py --check` exit 0; `git diff --cached --name-only` = the 2 paths |
| Fold-in 1 (LOCAL-07) | `docs/compliance/data-privacy.md` | `docs(privacy):` | `w10_foldin_assert.py` F1 |
| Fold-in 2 (DOC-OVERCLAIM) | `docs/compliance/data-privacy.md docs/compliance/hipaa-controls.md` | `docs(compliance):` | F2, F3, F4, F5 |
| Fold-in 3 (CLAUDE-FAILURE-COUNT) | `CLAUDE.md` | `docs:` | F6, F7; then all gates of Task 4b Step 5 |
| Records | `audit/2026-09-25/swarm-2026-09-27/reviews/W10-r5-*`, `audit/2026-09-25/waves/wave-4-L1-C.md` | `docs:` | `repo_hygiene_check.py` |
| W-10b (deferred) | `docs/compliance/data-privacy.md` | `docs(privacy):` | same gates; 1 path |
