# W-10 Governance Commit: Invariant Amendments for D3, D4 and D12

**Last Updated:** 2026-09-27
**Owner:** repository owner
**Refresh Trigger:** P1 merges; P4 merges; any of W-2 / W-3 / W-6 merges; any edit to `CLAUDE.md` lines 25 or 59-62; any edit to `docs/compliance/data-privacy.md`
**Status:** PROPOSED — not executed
**Prerequisites:** P0-B and P1 merged to `origin/main`; P4 merged, or a written orchestrator waiver. If Task 0 Step 2 fails before P1 lands, that is the intended STOP, not a plan defect.
**Revision:** r1, 2026-09-27, after the Codex review verdict REVISE:
1. The export inventory is now an AST scan that handles multiline decorators, and it now finds `POST /feedback/export` (§3.5, Task 1 Step 4).
2. Every assertion run uses one `W10_ARGS`.
3. Variant I needs the W-item PR's red-first and break-it evidence.
4. If Q1 is unsigned, `CLAUDE.md:62` stays unchanged as an open owner item.

**Review status:** 3 Codex rounds. Round-3 findings were fixed after the last round; the owner decides whether there is a round 4.
**Revision:** r3, 2026-09-27, round-3 findings:
1. The route inventory prints **mounted** paths: the `main.py` prefix, then the `api/__init__.py` `include_router` prefix, then any `APIRouter(prefix=)`, then the decorator path (§3.5, Task 1 Step 4).
2. Q2 is no longer a gate. D12's text licenses naming audited break-glass, so the clause is unconditional, the alternate blocks are removed, and C-2 quotes D12 verbatim.

**Revision:** r2, 2026-09-27, after the Codex review verdict REVISE:
1. The `route_client` evidence is now checked per function with `rc_check.py`, which records the call line (Task 1 Step 3).
2. When an item's code has merged but its evidence is incomplete, the text now says "merged; conformance unverified" (variant **U**), with its own blocks.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (recommended here: 7 small tasks (0-6), one file pair, no code) or superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One `docs:` commit that changes exactly two files, `CLAUDE.md` and `docs/compliance/data-privacy.md`. It names the owner-approved exceptions to two invariants: CSV/JSON exports (D3) and the external runner (D12). It also records D3 and D4 in the privacy doc. Each claim about behaviour is marked as implemented or as owner-approved but not yet implemented.

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
| C-2 | `CLAUDE.md` invariant "Redaction before anything leaves" | D3 "amend CLAUDE.md … to name them as deliberate exceptions" and "Doctor summary … redact it (strict)". D12 "make strict redaction unconditional … keep break-glass only with audit + UI warning" | yes, including the break-glass clause (r3: no longer gated; D12's own text licenses it. This also answers W-6 §11 Q2) |
| C-3 | `CLAUDE.md` invariant "No medical advice" | D11 "document [YOUR_RESULTS:N]/[REFERENCE:N] as context labels" | **no: conditional on Q1** |
| C-4 | `CLAUDE.md` invariant "Local-first" | none. D12 licenses naming the *ModelRunner* exception only | **no: owner-gated, Q3** |
| DP-1 | `data-privacy.md` Data Portability | D3 | yes |
| DP-2 | `data-privacy.md` backup paragraph (`:173-178`) | D3 | yes |
| DP-3 | `data-privacy.md` new section "Unverified Extracted Values" | D4 "Docs updated to say so" | yes |
| DP-4 | `data-privacy.md` Optional External API redaction bullet | D12 "documented … make strict redaction unconditional … break-glass only with audit + UI warning". The orchestrator (2026-09-27) assigned this line to W-10 | yes |

**Decision on break-glass (C-2, DP-4). Settled by D12's text; not an owner gate (r3).** D12 reads: "make strict redaction unconditional (remove the dev bypass; keep break-glass only with audit + UI warning). Amend CLAUDE.md to name the exception." That text itself keeps break-glass and sets its two conditions, so naming audited break-glass is licensed as written. Without the clause, `CLAUDE.md:60` as written would forbid a bypass the owner chose to keep, which is recurring failure #8. The clause is worded strictly inside D12:
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
2. Any third file in the diff, including `docs/INDEX.md` and `docs/_link_graph.json`. That is why no markdown links are added (§3.3).
3. Claiming a behaviour before it is merged. Every behaviour sentence in `data-privacy.md` carries a P or I status (Task 1).
4. Widening the redaction exceptions beyond CSV and JSON, or treating the doctor summary as an exception.
5. Naming the external runner as an exception to **Local-first** (`CLAUDE.md:59`). That is C-4, owner-gated (Q3).
6. Deciding where break-glass works (any env vs production only), which is W-6 §11 Q1.
7. Editing `skills/asclexis-guardrails/SKILL.md`, `docs/architecture/pipelines.md`, `src/backend/api/backup.py` docstrings, the capstone contract or matrix, or the D11 doc rows W-5 §6 hands to P4. See §11 follow-ups.
8. Correcting other false statements in `data-privacy.md` that no decision covers (F-2 in §11), even though they sit next to DP-4.
9. Touching the baseline-count lines in `CLAUDE.md` (§4), which belong to P1/P2/P4/P5, or the OpenWiki/Skills paragraphs, which belong to P1.

## 2. Traceability

| ID | Where | Quoted heading / row (verified by grep 2026-09-27) | Effect of W-10 |
|---|---|---|---|
| C-REDACT-1 | [contract](../capstone-report/architecture-engineering-contract.md) §6 | "**C-REDACT-1 · BINDING (ask-first).** … Backups are the single documented exception." "Until D3 is answered, CSV/JSON/doctor summary violate `CLAUDE.md:60` as written." | CSV/JSON become named exceptions. The doctor summary stays under the rule |
| C-REDACT-2 | contract §6 | "**C-REDACT-2 · BINDING.** The external runner MUST apply strict redaction before any network call, unconditionally (`CLAUDE.md:60`)." | break-glass named as the only bypass, with its conditions |
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

### 3.2 Code facts the new text relies on (all main@40f590e; unchanged on A and B unless stated)

| Claim in new text | Evidence |
|---|---|
| CSV/JSON/doctor summary are not redacted today | `modules/export.py` calls `RedactionEngine` only at `:533`/`:637` (visit-prep). `api/export.py:904` (`/csv`), `:960` (`/json`), `:379` (`/doctor-summary`), `:482-487` (download `format=text|html|pdf`) contain no redaction call |
| Third-party exports are strict-redacted | visit-prep `modules/export.py:637` (`policy_level="strict"`). Pinboard export `api/pinboards.py:485` → `compose_visit_prep_packet` (B@7b2ff1f). FHIR `modules/fhir_export.py:58`. RL `modules/rl_dataset.py:19` |
| Every export-shaped route is classified | §3.5: AST inventory of mounted routes (multiline-safe), 14 routes at B@7b2ff1f, each classified from code |
| External runner is off by default and opt-in | `models/model_settings.py:78-81` `default=False`; `core/external_runner.py:353` (B@7b2ff1f) returns a runner only if `use_external_api` |
| Dev bypass exists today | `core/external_runner.py:172` blocks only when `app_env == "production"`; `:201` redacts only if `redaction_enabled`; `:220` uses whatever `policy_level` is set |
| Values start unverified | `models/observation.py:79` `default=False`; set True only at `api/documents.py:1274` and `api/observations.py:458` (contract C-VERIFY-1 verify line) |
| Trends carry no verification flag; legacy RAG does not filter | `api/observations.py:156-168` `TrendPoint` has no `user_verified`; query `:530-535` has no filter. `modules/rag.py:322-328` has no filter (it labels verified rows at `:433`) |
| `[cite:N]` is the validated legacy marker | `modules/rag.py:819`; labels `[YOUR_RESULTS:{i}]` built at `:636` |

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

Two things were **not** run and are **UNMEASURED**: `python3 scripts/docs_lint.py` and `generate_docs_index.py --check` as whole-repo commands on a real post-P1 tree, because this checkout is dirty and P1 has not happened. To measure, run Task 4 Step 5 in the executor's clean worktree. The dry run shows the two files contribute nothing new to either gate: identical index and graph content, and 0 DOC-007 errors.

## 4. Files

**Owned (modify only):**
- `CLAUDE.md`: hunks C-1, C-2; C-3 if Q1 is signed; C-4 if Q3 is signed
- `docs/compliance/data-privacy.md`: hunks DP-1, DP-2, DP-3, DP-4

**Read-only (must show zero diff):** everything else. In particular:
- ask-first files (`modules/interpret_safety.py`, `modules/redaction.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`, `core/auth.py`, anything auth/encryption);
- `core/external_runner.py`, `modules/export.py`, `api/export.py`, `modules/rag.py`, `api/observations.py`;
- `docs/INDEX.md`, `docs/_link_graph.json`, `AGENT.md`, `skills/**`, `docs/capstone-report/**`, `audit/**`.

**Scratch (never committed):** `$W10_SCRATCH` = `$HOME/.cache/asclexis-w10`, outside the repo. It holds `w10.env`, `w10_assert.py`, `routes_inv.py`, PR-body captures and `dp.bak`.

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

- Exactly 2 files in `git diff --cached --name-only`. Commit prefix `docs:`.
- No bracket-paren (`[..]` + `(..)`) markdown links in any new text; inline-code paths only.
- Do not change the H1 or first paragraph of either file.
- Do not change any line outside the Before blocks. No reflow of neighbouring paragraphs.
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
export WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w10
export W10_SCRATCH="$HOME/.cache/asclexis-w10"
export PY="$HOME/venvs/asclexis-311/bin/python"
EOF
source "$HOME/.cache/asclexis-w10/w10.env"
git -C "$MAIN" fetch origin
git -C "$MAIN" worktree add "$WT" -b docs/w10-governance-invariants origin/main
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
```

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
(cd "$WT/src/backend" && "$PY" -m pytest tests/ -p no:cacheprovider -q 2>&1 | tail -15)
(cd "$WT/src/backend" && "$PY" -m pytest tests/test_docs_lint.py -p no:cacheprovider -q 2>&1 | tail -3)
```

Expected:
- `Docs lint passed.` with exit 0.
- Index check exit 0 ("docs/INDEX.md and docs/_link_graph.json are fresh.").
- The pytest summary line records **collected** and **failures**.

If either docs gate fails on the start tree, stop (S4): W-10 must not land on a red docs job. Record all outputs verbatim in the PR body (handoff §6 item 1).

---

## Task 1: Select variants, build the export inventory, fix the assertion flags (no commit)

**Files:** none modified in the repo. Outputs: `$W10_SCRATCH/routes_inv.py`, the `W10_ARGS` line in the env file, and a "variant table" for the PR body.

- [ ] **Step 1: Read the confirmation boxes Q1, Q3 and Q4 in §10** (Q2 is no longer a gate as of r3)

| Q | If signed | If unsigned |
|---|---|---|
| Q1 (D11 → C-3) | apply C-3 | skip C-3. `CLAUDE.md:62` stays unchanged; list it in the PR as an open owner item (not P4) |
| Q3 (C-4 local-first) | apply C-4 | skip C-4 (default) |
| Q4 (order) | as §5 | if the owner says "land after W-2/W-3/W-6", wait, then use variant I throughout (only where Step 3's criteria hold) |

- [ ] **Step 2: Measure whether W-2, W-3 and W-6 have merged**

```bash
set -o pipefail
source "$HOME/.cache/asclexis-w10/w10.env"
git -C "$WT" grep -n "HC-EXPR-001" origin/main -- src/backend/tests | head -3   # W-2
git -C "$WT" grep -n "HC-VER-001"  origin/main -- src/backend/tests | head -3   # W-3
git -C "$WT" grep -n "HC-EXT-001"  origin/main -- src/backend/tests | head -3   # W-6
```

Zero hits → variant **P** for that item. Hits → Step 3.

- [ ] **Step 3: For each item with hits, collect the four pieces of evidence that variant I requires**

```bash
set -o pipefail
source "$HOME/.cache/asclexis-w10/w10.env"
# <files> = the test files Step 2's grep printed for that item, relative to src/backend; <PR#> = that item's merged PR
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
- **Code not merged:** use variant **P** ("owner-approved, not yet implemented").
- **Code merged:** use variant **U** ("code merged in `<sha>`; conformance unverified"). The Task 4 blocks give U explicitly. P's "Today …" sentence would be false for merged code, and "not yet implemented" would be false too.

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
Q1=unsigned; Q3=unsigned   # EDIT: change a value to "signed" only if its §10 box is signed
A=""
if [ "$Q1" = signed ]; then A="$A --c3"; fi
if [ "$Q3" = signed ]; then A="$A --c4"; fi
echo "export W10_ARGS=\"$A\"" >> "$HOME/.cache/asclexis-w10/w10.env"
source "$HOME/.cache/asclexis-w10/w10.env"; echo "W10_ARGS=[$W10_ARGS]"
```

The defaults are the conservative, all-unsigned state. Paste the printed line into the variant table.

- [ ] **Step 6: Write the variant table** (paste into the PR body)

```text
Q1=<signed|unsigned>  Q3=<…>  Q4=<…>   W10_ARGS=[…]
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
# W10-A3: C-2 external-runner clause (D12), unconditional since r3
check("W10-A3", "break-glass is the only bypass, and only with an audit record and a UI warning (D12: \"keep break-glass only with audit + UI warning\")" in fc, "C-2 break-glass clause missing")
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
- The count is therefore `2/9 assertions pass` with `--c3`, and `3/9` without it.

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
After:
```text
- **Redaction before anything leaves.** Any path that writes user text to exportable files or external runners must pass through `modules/redaction.py` first. Named exceptions, owner decision D3 (2026-09-27): the CSV and JSON exports are the patient's own data export and stay full-fidelity, like backups (BKUP-UX-001). The doctor summary goes to a third party and must be redacted at `strict`. The opt-in external runner must apply `strict` redaction on every call (owner decision D12); break-glass is the only bypass, and only with an audit record and a UI warning (D12: "keep break-glass only with audit + UI warning"). Record: `docs/capstone-report/owner-decisions-2026-09-27.md`. Code conformance is tracked in `docs/capstone-report/specs-compliance-matrix.md` rows PRIV-04 and LOCAL-04.
```
Wording checks against the licence:
- "like backups" is D3's own words, and backups are already a documented exception (matrix PRIV-05 "tested (documented exception)"; C-REDACT-1). No new exception is created.
- "must" throughout: nothing here claims the code conforms.

- [ ] **Step 3: Hunk C-3 (D11). Apply only if Q1 is signed**

Before:
```text
- **No medical advice.** Outputs are educational, grounded, cited (`[REFERENCE:N]` / `[YOUR_RESULTS:N]`). `interpret_safety` prohibited patterns (diagnosis, dosing) must keep passing.
```
After:
```text
- **No medical advice.** Outputs are educational, grounded, and cited. On the legacy RAG path `[cite:N]` is the validated citation marker (`modules/rag.py`, `RAGModule.validate_response`); `[YOUR_RESULTS:N]` / `[REFERENCE:N]` are context labels, not citation markers (owner decision D11, 2026-09-27). `interpret_safety` prohibited patterns (diagnosis, dosing) must keep passing.
```

Check: none of the new text has `]` immediately followed by `(`, so DOC-007 sees no link. `` `[YOUR_RESULTS:N]` / `` has a backtick between `]` and anything else.

- [ ] **Step 4: Hunk C-4 (Local-first). Apply only if Q3 is signed; default skip**

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

Expected: `assert exit=1` with only W10-A6, A7 and A8 failing (`6/9`), for any `W10_ARGS`. `git diff --stat` shows `CLAUDE.md` only, with 2-4 lines changed (one per applied hunk).

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
  `audit/2026-09-25/handoff-2026-09-27-execution.md` §5 (matrix PRIV-04).

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
W-3 in `audit/2026-09-25/handoff-2026-09-27-execution.md` §5 (matrix SAFE-02).

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
After, variant **P** (W-6 not merged):
```text
- PHI redaction: owner decision D12 (2026-09-27) requires `strict` redaction
  through `modules/redaction.py` on every external call, with break-glass as
  the only bypass, allowed only with an audit record and a UI warning. Status:
  owner-approved, **not yet implemented**. Today, outside production, a
  disabled or non-strict redaction setting still reaches the provider
  (`core/external_runner.py`). Tracked as W-6 (matrix LOCAL-04).
```
After, variant **U** (W-6 merged; variant-I evidence incomplete):
```text
- PHI redaction: owner decision D12 (2026-09-27) requires `strict` redaction
  through `modules/redaction.py` on every external call, with break-glass as
  the only bypass, allowed only with an audit record and a UI warning. Status:
  code merged in `<W-6 sha>`; **conformance unverified** until W-6's red-first,
  break-it and HTTP-test evidence is recorded (matrix LOCAL-04).
```
After, variant **I** (W-6 merged; first re-read W-6's merged diff and confirm that both conditions hold as written):
```text
- PHI redaction: `strict` through `modules/redaction.py` on every external
  call (owner decision D12, 2026-09-27; implemented in `<W-6 sha>`).
  Break-glass is the only bypass, and it is allowed only with an audit record
  and a UI warning.
```
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

## Task 5: End measurement, stage, commit, PR

**Files:** the two owned files only.

- [ ] **Step 1: End measurement**

```bash
set -o pipefail
source "$HOME/.cache/asclexis-w10/w10.env"
(cd "$WT/src/backend" && "$PY" -m pytest tests/ -p no:cacheprovider -q 2>&1 | tail -15)
(cd "$WT/src/backend" && "$PY" -m pytest tests/test_docs_lint.py -p no:cacheprovider -q 2>&1 | tail -3)
git -C "$WT" diff --name-only    # expect exactly the 2 files
git -C "$WT" status --short      # expect exactly the 2 files, " M"
```

Acceptance:
- collected is **equal** to Task 0 (this plan adds no tests);
- failures ⊆ Task 0 failures;
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

- [ ] **Step 3: Commit.** Remove the C-3 / C-4 lines from the body if not applied, and set P/I per Task 1.

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
  break-glass only with audit record + UI warning.
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
git -C "$WT" push -u origin docs/w10-governance-invariants
```

The PR body (handoff §6) must contain:
1. start/end measurements (Task 0 Step 4, Task 5 Step 1), with interpreter and command;
2. the RED→GREEN assertion output and the break-it output;
3. the variant table (with `W10_ARGS`, the evidence columns, and the `routes_inv` result);
4. contract/matrix effects (§2);
5. the 2-file list;
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
| S6 | A W-item has merged but any of the four variant-I criteria (Task 1 Step 3) is missing, or W-6's code does not match "audit record + UI warning" | orchestrator; use variant U ("code merged in `<sha>`; conformance unverified"), never I |
| S7 | `git diff --cached --name-only` shows anything besides the 2 files | unstage and investigate; never `git reset` shared work |
| S8 | Any pytest failure not in the Task 0 start set | stop; a docs change should not cause one, so find out why |

## 9. Rollback

- Before merge, after push/PR: `gh pr close <PR#> --delete-branch` (closes the PR and deletes the remote branch), then `git -C "$MAIN" worktree remove "$WT"` and `git -C "$MAIN" branch -D docs/w10-governance-invariants`.
- Before push: `git -C "$MAIN" worktree remove --force "$WT"` and `git -C "$MAIN" branch -D docs/w10-governance-invariants`.
- After merge: `git revert <W-10 sha>` on main through a PR, a single commit touching the same 2 files. This restores the pre-amendment invariants, so CSV/JSON again violate `CLAUDE.md:60` as written, and D12's named exception disappears. Any W-10b commit must be reverted first (it anchors on W-10 text). There is no schema, code or index to unwind.

## 10. Owner and orchestrator sign-offs (unsigned)

| Q | Question | Plan default / recommendation | Sign-off |
|---|---|---|---|
| Q1 | Include D11 hunk C-3 (`CLAUDE.md:62`) in this governance commit? The handoff scopes W-10 to D3/D12. W-5 §6 recommends that W-10 absorb it | **recommend include** (§1.3). If unsigned, skip; `:62` stays unchanged as an open owner item. It does not go to P4 | ☐ owner/orchestrator: ____ date: ____ |
| Q2 | *(r3: not a gate.)* Naming audited break-glass in `CLAUDE.md:60` (C-2) and `data-privacy.md` (DP-4) is licensed by D12's text "keep break-glass only with audit + UI warning … Amend CLAUDE.md to name the exception". This also answers W-6 §11 Q2 | included unconditionally, worded within D12 | n/a (licensed by D12, 2026-09-27) |
| Q3 | Also name the external runner as an owner-approved exception to **Local-first** (`CLAUDE.md:59`, hunk C-4)? D12's text licenses only the ModelRunner exception | **default skip** (owner-gated). Leaving `:59` unqualified keeps a known contradiction; the owner decides | ☐ owner: ____ date: ____ |
| Q4 | Land W-10 in the handoff §3 slot (after P4, before W-2/W-3/W-6), with P variants and a W-10b flip later? The alternative is to wait for all three and use I variants | **recommend the §3 slot** (§5) | ☐ orchestrator: ____ date: ____ |
| Q5 | `CLAUDE.md` C-2 says "like backups (BKUP-UX-001)": D3's own phrase, citing an existing documented exception (PRIV-05). Confirm this is not read as a new exception | recommend keep | ☐ owner: ____ date: ____ |
| — | PR merge | — | ☐ owner: ____ date: ____ |

## 11. Out-of-scope follow-ups (not in this diff; route each)

| # | Item | Evidence | Suggested owner |
|---|---|---|---|
| F-1 | `skills/asclexis-guardrails/SKILL.md:63` lists "bypass redaction for any reason" under **Never**, while D12 keeps audited break-glass | B@7b2ff1f `:60-64` | P4 (after W-6) or a separate owner-approved `docs:` commit |
| F-2 | `data-privacy.md` "Only the specific query text is sent to the external provider" and "Full health records are never transmitted" (A@692fdf3 `:213-214`; main `:196-197`) are **false**. `modules/rag.py:1257-1268` sends the whole composed prompt (question + retrieved observation/document chunks + history + optional memory) to the override runner | code read 2026-09-27 | owner-visible privacy correction. No D-decision covers it, so it is kept out of the governance diff. P4 addendum or its own `docs:` commit, **before** W-10 if possible |
| F-3 | `api/backup.py:10-15` docstring: "Every other export path in this app passes [through redaction]". False for CSV/JSON (and for the doctor summary until W-2) | main@40f590e | W-2 PR (product file, comment-only) |
| F-4 | `docs/architecture/pipelines.md:53-56` claims all consumers are verified-only (D4); the W-5 §6 table rows (D11) | contract C-VERIFY-2; W-5 §6 | P4 for D11 rows; W-3 PR or P4 for pipelines (after W-3, or with a status line) |
| F-5 | Program P4 bullets "`data-privacy.md:173-174` wording, after D3" and the `CLAUDE.md:62` part of "citation-marker vocabulary" are no longer P4's. The data-privacy wording belongs to W-10. `:62` belongs to W-10 if Q1 is signed; otherwise it is an open owner item and stays unchanged. The program's order "`data-privacy.md` (P1 → P4 → G-A1)" becomes "P1 → P4 → W-10 → W-10b" | `implementation-program.md:69,195,197` | capstone maintainer; P4 executor must skip them |
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
| W-10 | `CLAUDE.md docs/compliance/data-privacy.md` | `docs:` | `w10_assert.py` 9/9; `docs_lint.py` "Docs lint passed."; `generate_docs_index.py --check` exit 0; `git diff --cached --name-only` = the 2 paths |
| W-10b (deferred) | `docs/compliance/data-privacy.md` | `docs(privacy):` | same gates; 1 path |
