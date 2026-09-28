# P4 — Doc-Drift Sweep, Extended: Amendment to Plan 04

**Last Updated:** 2026-09-27
**Owner:** repository owner
**Refresh Trigger:** P1 merges (re-verify every `B@`/`A@`/`M@` anchor below); P2, P3/W-1, W-2, W-3, W-4, W-5, W-6, W-7, W-8 or W-10 merges (each unlocks or changes a task here); the owner signs plan 08 Brief 2; OpenWiki content is generated (G-C2)
**Status:** PROPOSED — not executed
**Review status:** 4 Codex rounds; round-4 MAJORs fixed after the last round, not re-reviewed (owner acceptance required).
**Prerequisites:** P0-B and P1 merged to `origin/main`; the 2026-09-27 plan set (`docs/plans/2026-09-27-*.md`, this file included) committed on main via an owner-approved docs commit (P0-B's approved text covers only `audit/` + `docs/capstone-report/` + `docs/INDEX.md`, not these plans); plus, for P4-core, P2 and P3/W-1 merged and the D9 venv `~/venvs/asclexis-311` built (§5). Before P1 lands, Task 0 Step 2's ancestry check fails: that is the intended stop, not a defect.

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to run this plan task by task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Run the doc-drift sweep in [plan 04](../../audit/2026-09-25/plans/04-doc-drift-sweep.md) against the post-P1 tree, correct the plan 04 tasks that branches A and B have already overtaken, and add the drift that plan 04 never covered. When a later work item has not merged yet, the doc says "approved, not yet implemented" and never claims the change has landed.

**Architecture:** This file amends plan 04; it does not copy it. Tasks marked **run as written** execute plan 04's own text, with the anchor corrections given here. Tasks marked **amended**, **replaced**, **new** or **deferred** execute the text in this file. The work ships in two parts:
- **P4-core.** One docs PR in the program's P4 slot.
- **P4-deferred.** Small follow-up `docs:` commits (F1–F6, N8, N9, N10). Each one runs only after its named trigger merges.

**Tech stack:** Markdown, Mermaid, one Python comment edit (N7), and the gates `scripts/docs_lint.py` (DOC rules), `scripts/generate_docs_index.py --check`, `scripts/harness_drift_check.py` (B), `scripts/repo_hygiene_check.py` (B), plus a relative-link resolver for files outside DOC-007.

**Spec:** [implementation-program.md](../capstone-report/implementation-program.md) §P4 · [owner-decisions-2026-09-27.md](../capstone-report/owner-decisions-2026-09-27.md) · [architecture-overview.md §12](../capstone-report/architecture-overview.md#12-divergences-from-docsarchitecturemd-code-wins) · [handoff](../../audit/2026-09-25/handoff-2026-09-27-execution.md) §4 row "04 doc drift", §5 rows W-5 and W-10.

**New tests:** none. This phase is docs-only. Acceptance is by greps and gates, and the collected count must stay at the start value.

---

## 0. Ref labels used in this file

| Label | Meaning |
|---|---|
| `main@40f590e` | `origin/main`, 2026-09-27 |
| `B@7b2ff1f` | `origin/claude/healthcentral-agentic-research-r1n54x` |
| `A@692fdf3` | `origin/claude/asclexis-repo-audit-349pjq` |
| `M@86606d0` | `git merge-tree --write-tree` of B and A. This is the closest thing to the post-P1 tree that exists before P1. 5 files carry conflict markers (`AGENT.md`, `CLAUDE.md`, `docs/INDEX.md`, `docs/_link_graph.json`, `docs/agentic/recurring-failures.md`). The planner exported it and grepped it on 2026-09-27 |

Anchors for files that neither A nor B changes are labelled `main@40f590e`. They are identical at `M@86606d0`. **Every line number is a lead, not a fact.** At execution, match the **Before** text exactly once and re-verify each line on the post-P1 tree. If a Before block does not match, stop (stop gate S1).

## 1. Approval scope

This phase is `DOCS` (program ground rule 1). Its mandate is the program's P4 row (`implementation-program.md:185-203`). These owner decisions set what the docs may say, verbatim from [owner-decisions-2026-09-27.md](../capstone-report/owner-decisions-2026-09-27.md):

| # | Owner's choice | Option text (verbatim) | Used by |
|---|---|---|---|
| D2 | Delete them | "git rm the 7 stale memory files; Serena can regenerate on demand." | Task 12 |
| D4 | Label, exclude from RAG | "Trends may show unverified points but visibly marked 'unverified'; legacy RAG cites verified values only (matches the agent path). Docs updated to say so." | N1, F1 |
| D11 | Docs match code | "Keep [cite:N] as the validated marker; document [YOUR_RESULTS:N]/[REFERENCE:N] as context labels; remove the contradictory prompt line. … no validator edit." | N8 |
| D3 | Redact doctor summary only | "Doctor summary goes to a third party → redact it (strict). CSV/JSON are the patient's own data export → keep full-fidelity like backups, and amend CLAUDE.md/data-privacy.md to name them as deliberate exceptions." | N3, F2 (description only) |
| D12 | Keep, harden | "Keep the opt-in feature as a documented ModelRunner exception, but make strict redaction unconditional (remove the dev bypass; keep break-glass only with audit + UI warning). Amend CLAUDE.md to name the exception." | N4, N5, N10, F3 (description only) |
| D7 | Route via ModelRunner | "Keep the tiered-interpretation feature but rewrite it to call ModelRunner, then wire it to a route. New feature work." | N4, N5, F3 (description only) |
| D8 | Bundle the model | "Ship the small embedding model with the app / installer so no download is ever needed." | N4, F5 (description only) |
| D8-delivery | Script + offline load (owner, 2026-09-27; recorded in the orchestrator ledger, not in the decisions file) | "Interim: `src/backend/scripts/download_models.py` fetches it once into a local models dir; runtime loads that path with HF offline and fails closed if absent. Installer bundles it later (G-C4). No weights in git." | N4, F5 (description only) |

D8 is the goal (no download ever needed at runtime); D8-delivery is the interim mechanism before an installer exists. P4 text must not describe D8 as "bundled" until G-C4 ships; it describes the D8-delivery mechanism once W-8 lands.

**Does NOT license:**
1. Any edit to `CLAUDE.md` invariant text (`:25`, `:57-63` at main; `:62` "No medical advice" included). W-10 owns it. P4 may touch only the test-baseline count line, and only with a count P4 measured itself (Task 0).
2. Any edit to `docs/compliance/data-privacy.md`. Orchestrator ruling, 2026-09-27: the D3/D4 wording (`:173-174` and the D4 passages) and the stale break-glass bullet (`main@40f590e:200` = `M@86606d0:217`) belong to **W-10**. The program's P4 bullet at `implementation-program.md:195` has **moved to W-10**.
3. Describing any W-item as implemented before its PR merges. The wording is "approved, not yet implemented (W-n)" until the matching F-task runs.
4. Any product behaviour change, or any non-docs action without its own approval. P4 is `DOCS`, and the program's P4 sign-off is "none beyond D2/D3 (docs only)" (`implementation-program.md:204`). The only non-markdown actions P4 takes by default are:
   - the `core/config.py` comment (N7; listed as comment-only in the program's P4 owned files, `:198`);
   - `git rm` of the 7 `.serena/memories/*.md` files (Task 12; licensed by D2).

   Three plan-04 actions are **owner-gated** and run only if their sign-off line in §12 is signed, each as its own commit:
   - OG-4: edit `config/.env.example` (Task 3);
   - OG-5: edit the docstrings in `src/backend/api/__init__.py` and `src/backend/modules/agent/__init__.py` (Task 10);
   - OG-6: delete `scripts/download_models.py` (Task 14).

   Unsigned means P4 does only the docs part of each task (see each task).
5. Touching `.serena/project.yml`, which carries uncommitted owner edits. Adding `/memories` to `.serena/.gitignore` is also out: D2 does not cover it (owner-gated, §12).
6. Editing `hipaa-controls.md:169` before plan 08 Brief 2 is signed (N9).
7. Editing `docs/capstone-report/*`, `audit/*`, `docs/archive/**`, `docs/plans/**` (dated records), or `docs/research/**`. **One exemption:** the executor fills in §15 (Execution record) of this plan file, and nothing else in it.
8. Editing any ask-first file: `modules/interpret_safety.py`, `modules/redaction.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`, `core/auth.py`, or any other auth or encryption code.

## 2. Traceability

Contract IDs are verified by `grep -n "C-…" docs/capstone-report/architecture-engineering-contract.md`, matrix rows by `grep -n "| ROW |" docs/capstone-report/specs-compliance-matrix.md` (2026-09-27).

| Task | Contract | Matrix rows | Other source |
|---|---|---|---|
| N1, F1 | C-VERIFY-1 (`:112`), C-VERIFY-2 (`:119`: "`docs/architecture/pipelines.md:53-56` claims all do") | SAFE-01, SAFE-02 ("Downstream consumers use verified data") | overview §12 row 1; W-3 §11 |
| N2, F4 | C-LLM-1 (`:206`), C-SAFE-1 (`:131`), C-SAFE-2 (`:141`) | LLM-01, SAFE-03, SAFE-04, SAFE-05 | overview §12 rows 2–3 |
| N3, F2 | C-REDACT-1 (`:177`) | PRIV-01…05 | overview §12 row 4 |
| N4, N5, F3, F5 | C-LLM-1, C-LLM-2 (`:216`), C-LOCAL-1 (`:25`), C-LOCAL-2 (`:44`), C-REDACT-2 (`:185`) | LLM-01, LLM-02, LOCAL-01, LOCAL-03, LOCAL-04 | overview §12 rows 5–6 |
| N6 | C-API-3 (`:295`), C-GATE-1 (`:340`), C-GATE-2 (`:353`) | GATE-01, GATE-02, GATE-03, GATE-04, GATE-05 | overview §12 row 7 |
| N7 | C-LOCAL-1 | LOCAL-02 ("Ollama is localhost-only") | overview §7 `:135` |
| N8 | C-SAFE-5 (`:165`: "One citation-marker vocabulary across docs, prompt and validator.") | SAFE-08 | handoff §5 W-5 row; W-5 §6 |
| N9 | C-KEY-3 (`:103`) | KEY-05, GATED-02 | plan 08 Brief 2; P08 amendment Task 3 |
| N10 | C-REDACT-2, C-LLM-1 | LOCAL-04 | W-6 |
| Task 1, Task 9 | — | GATE-05 | plan 04 ledger rows 1, 12 |
| Task 11 | C-API-2 (`:288`) | — | plan 04 ledger row 11 |
| Task 12 | — | GATED-07 ("Serena memories: delete, regenerate, or freshness gate") | D2 |
| Task 15 | — | GATE-09 | W-1 Task 9 Step 6 |
| Task 16, all commits | C-GATE-3 (`:360`), C-GATE-4 (`:367`) | GATE-01, GATE-08 | recurring-failures #5 |

## 3. Plan 04 Tasks 1–16, re-verified against the post-P1 tree

Each premise was re-grepped on `M@86606d0` on 2026-09-27. "Holds" means the stale text is still there after both branches merge.

| # | Plan 04 task | Premise at M@86606d0 | Verdict | Evidence |
|---|---|---|---|---|
| 1 | evals.md counts | Holds: `:9` "~620", `:20` "four axes", `:21` "~620 pass" | **Amended** (no hard-coded test count) | `docs/agentic/evals.md:9,20,21` main@40f590e; 74 golden files; 6 bars printed at `scripts/agent_eval_gate.py:57-62` |
| 2 | README agent/FAISS/API table | Holds: `:202` FAISS, `:495` "default OFF", `:516` "stubs, flag OFF"; table has 12 rows, 7 mounted groups missing | Run as written | `api/__init__.py:39-58` (18 `include_router`); `modules/agent/settings.py:19` `= True` |
| 3 | `.env.example` VECTOR_STORE_TYPE | Holds: `:95-96` | **Owner-gated (OG-4).** A config-file edit, not docs. Default: docs part only (no live doc mentions `VECTOR_STORE_TYPE` at M@86606d0, so no edit). If signed: plan 04 Task 3; re-anchor `embedding_dimensions` to `B@7b2ff1f core/config.py:112`, not `:113` | `grep -rn VECTOR_STORE_TYPE --include=*.md` at M → only history (`TASK_LIST.md:675`, `docs/plans/`) |
| 4 | features-index notifications | Holds at M: `00_features_index.md:26` "all implemented" | **Resequenced after P2.** Plan 02 Task 6 edits "features doc(s) claiming implementation", which is probably this line | see amended Task 4 |
| 5 | INGEST-FHIR-001 → DONE | **Does not hold.** A (`3bb4d0d`, 2026-09-08) already rewrote `TASK_LIST.md:59`: "Premise partly overtaken…" and kept it `[ ] OPEN` with a verified remaining gap (DiagnosticReport unhandled, LOINC dropped). Plan 04's flip to DONE would erase a real open gap | **Dropped.** Replaced by Task 5R (date fix) | `A@692fdf3 docs/features/TASK_LIST.md:59` |
| 6 | S06-SEC-003/004 banner | Holds. Both fixes present (`security/input_validator.py:92,110`; `scripts/backup.py:108` def, used `:433,:576-577`). The 2026-07-01 banner also says CI scanners "run with `continue-on-error: true` … unchanged", which is false at B: `ci.yml` has 0 `continue-on-error`, and the scanner steps fail on exit ≥ 2 | **Amended** (status line also corrects the CI clause) | `B@7b2ff1f .github/workflows/ci.yml:95-148` |
| 7 | FAQ password recovery | Holds: `docs/user/faq.md:44-47` "There is no password recovery mechanism". **Plan 04's replacement text is false after A:** A adds `RecoveryCodeCard` to Settings (`A@692fdf3 SettingsPage.tsx`, card title "Recovery code"), and `POST /profiles/{id}/recovery-code` "Generate (or replace)s" a code for an existing profile | **Amended** (new text) | `M@86606d0 src/backend/api/profiles.py:589-603`; `components/settings/RecoveryCodeCard.tsx:1-14,69-70`; `pages/ProfileSetup.tsx:323-326` "Use your recovery code" |
| 8 | CONTRIBUTING `.gsd` | Holds: `:179`; `.gitignore:118` | Run as written | — |
| 9 | skills tool/axis counts + AGENT.md row | Holds: `skills/asclexis-agent/SKILL.md:37-39` lists 5 tools; `skills/asclexis-evals/SKILL.md:3,37` "four"; AGENT.md `:46` at both A and B | Run as written; anchor the AGENT.md row by text | registry `:42-67` lists 8 tools |
| 10 | `__init__.py` docstrings | Holds: both unchanged. **Plan 04's "preserve the stdlib-only paragraph if still accurate": it is not accurate.** `modules/agent` imports `sqlalchemy`, `core.audit`, `modules.faithfulness`, `modules.redaction`, `monitoring.metrics` | **Owner-gated (OG-5)** (Python source edit). Default: no edit; the drift is recorded in the PR. If signed: amended docstring text given; paragraph dropped | `B@7b2ff1f modules/agent/guardrails/guard.py:32`; `tools/compute_trend.py:9`; `audit.py:10`; `metrics.py:10` |
| 11 | endpoints.md verify-only | Holds as verify-only. 130 route decorators in `api/*.py` (main and M); 131 method rows in `docs/api/endpoints.md` | Run as written | counted 2026-09-27 |
| 12 | `.serena/memories/` | Holds: 7 tracked files, last commit `a0aa235` 2026-01-07. D2 decided **delete** | **Resequenced after D2 (done).** Amended: explicit 7 paths; never `project.yml` | `git ls-files .serena` |
| 13 | openwiki referrers | Holds. B fixed only `CLAUDE.md`. `AGENT.md:20` unchanged at A and B; `docs/00_architecture_plans_index.md` wording now at `A@692fdf3:63-65` (was `:56-60`); `openwiki/` still README-only | Run as written; re-anchor index to `:63-65` | `find openwiki -type f` → 1 file |
| 14 | root `scripts/download_models.py` | Holds: root copy is 4,318 B, Qwen2.5/Phi-3 tiers, "for HealthCentral"; canonical `src/backend/scripts/download_models.py` is 12,501 B at B. `AGENT.md` reference moved to `B@7b2ff1f:80-81` (backend path). `tests/test_verify_model_repos.py:18` imports from `src/backend/scripts`, not root | **Owner-gated (OG-6)** (file deletion is not a docs action). Default: docs part only; no live doc names the root path at M@86606d0 (AGENT.md `:84-85` and `docs/model_tiers/README.md:35` use the backend path), so no edit. If signed: `git rm scripts/download_models.py` as its own commit | `diff -q` differs |
| 15 | `.claude/agents/` claim | B removed the claims (`7b2ff1f`); W-1 (D1 Branch A) re-adds 5 agents and rewords `harness.md`/`roadmap.md` | **Resequenced after P3/W-1.** Verify-only with W-1's checks. W-1 not merged = STOP (S2) | W-1 Task 9 Step 6 |
| 16 | close-out | — | **Amended:** explicit pathspecs, new grep list, index regenerated only on a clean tree | — |

## 4. Files

**Owned by P4-core (modify unless noted):**

| File | Tasks |
|---|---|
| `docs/agentic/evals.md` | 1 |
| `README.md` | 2 |
| `docs/features/00_features_index.md` | 4 |
| `docs/features/TASK_LIST.md` | 5R, 16 (Session Notes) |
| `docs/compliance/security-review-sprint06.md` | 6 |
| `docs/user/faq.md` (`:44-47` only) | 7 |
| `CONTRIBUTING.md` | 8 |
| `skills/asclexis-agent/SKILL.md`, `skills/asclexis-evals/SKILL.md` | 9 |
| `AGENT.md` (the `asclexis-evals` row and the openwiki line only; baseline line only if Task 0 measured a different count) | 9, 13 |
| `.serena/memories/*.md` (7 files, **delete**) | 12 |
| `docs/00_architecture_plans_index.md` | 13 |
| `docs/architecture/pipelines.md` | N1, N2, N3 |
| `docs/architecture/README.md` | N4 |
| `docs/architecture/backend.md` | N5 |
| `docs/architecture/ci-and-quality-gates.md` | N6 |
| `src/backend/core/config.py` (one comment, `B@7b2ff1f:108`) | N7 |
| `docs/INDEX.md`, `docs/_link_graph.json` (regenerated, Task 16) | 16 |

**Owner-gated (touched only if the §12 line is signed, each as its own commit):** `config/.env.example` (OG-4, Task 3); `src/backend/api/__init__.py` and `src/backend/modules/agent/__init__.py`, docstrings only (OG-5, Task 10); `scripts/download_models.py`, delete (OG-6, Task 14).

**Owned by P4-deferred:**
- N8: `docs/architecture/pipelines.md`, `docs/features/00_features_index.md`, `docs/features/04_self_improvement_loop.md`, `docs/features/TASK_LIST.md`.
- N9: `docs/compliance/hipaa-controls.md`.
- N10: `skills/asclexis-guardrails/SKILL.md`.
- F1–F6: `docs/architecture/pipelines.md`, `docs/architecture/README.md`, `docs/architecture/backend.md`, `docs/architecture/ci-and-quality-gates.md`.

**Read-only here, routed elsewhere:**
- `CLAUDE.md` invariant text → W-10.
- `docs/compliance/data-privacy.md`, all of it → W-10. This includes `:173-174`, the D4 passages, `M@86606d0:217` (the break-glass bullet) and `A@692fdf3:33` "Audit logs | Master DB + log file", which the P08 amendment F-P8-2 flagged.
- `docs/features/01_lab_result_interpreter_architecture.md:195-216`, `docs/compliance/ai-safety.md:20`, `docs/user/faq.md:108-110`, `docs/user/workflows.md:113-116` → W-5 (its §5 owned files).
- `docs/architecture/README.md:121-124` scheduler text → P2 (plan 02 Task 6).
- `docs/agentic/harness.md`, `docs/agentic/roadmap.md` → W-1.
- `docs/architecture/ci-and-quality-gates.md:58` → W-8.
- `docs/capstone-report/*` → the capstone maintainer.
- Ask-first files (§1 item 8).

**Shared-file order.** Never edit concurrently. The later phase rebases and re-anchors.

| File | Order |
|---|---|
| `AGENT.md` | P1 (conflict resolution) → P2 → P3/W-1 → **P4-core** → W-10 (if any) → W-8 → later baseline lines |
| `CLAUDE.md` | P1 → P2 → P3 → **P4 (baseline line only, only if measured-different)** → W-10 → P5… |
| `docs/features/TASK_LIST.md` | P1 (A) → P2 (Session Notes) → **P4-core** → **N8** → later Session Notes |
| `docs/features/00_features_index.md` | P2 (Task 6) → **P4-core Task 4** → **N8** |
| `docs/architecture/README.md` | P2 (`:121-124`) → **P4-core N4** → F3/F5 |
| `docs/architecture/pipelines.md` | **P4-core N1–N3** → N8 → F1, F2, F4 (any order, serial) |
| `docs/architecture/ci-and-quality-gates.md` | **P4-core N6** → W-8 (`:58`) → F4 (W-4 job row) |
| `docs/agentic/evals.md` | **P4-core Task 1** → W-4 (its "after P4" row) |
| `docs/user/faq.md` | **P4 Task 7** (`:44-47`) and W-5 (`:108-110`): disjoint, serial |
| `config/.env.example`, `src/backend/core/config.py` | P1 (B) → **P4-core** → W-8 |
| `docs/compliance/data-privacy.md` | P1 (A) → W-10 → W-10b. **P4 does not edit it**; the program's "P1 → P4 → G-A1" is superseded |
| `docs/INDEX.md`, `docs/_link_graph.json` | P0-B → every docs phase regenerates on its own clean tree |

## 5. Dependencies and sequencing

**P4-core preconditions (all hard):**
1. P0-B merged: the capstone package and the 2026-09-27 W-plans are committed, so the new links resolve and DOC-011 passes.
2. D9: `~/venvs/asclexis-311/bin/python` exists.
3. P1 merged: A and B are on main.
4. P2 merged (Task 4).
5. P3/W-1 merged (Task 15).

D2, D3, D4, D11 are decided and need nothing further.

**P4-deferred triggers:**

| Task | Runs after | Why |
|---|---|---|
| N8 D11 docs | W-5 merged | W-5 §7: "Before P4's D11 doc task, which consumes §6" |
| N9 hipaa `:169` | plan 08 Brief 2 **signed** (owner) | program `:196`; P08 amendment Task 3 |
| N10 guardrails SKILL | W-6 merged | orchestrator ruling |
| F1 D4 flip | W-3 merged | trends labelling and legacy RAG verified-only become true |
| F2 D3 flip | W-2 merged **and** W-10 merged | doctor summary redacted; CSV/JSON named exceptions |
| F3 ModelRunner flip | W-7 merged (dormant bypass gone); separately W-6 + W-10 (external-runner exception named) | D7, D12 |
| F4 legacy-abstain flip | W-4 merged | legacy low-faithfulness abstains; new CI job |
| F5 outbound flip | W-8 merged | offline embedding load |
| F6 D12 wording flip in N4/N5 | W-6 **and** W-10 merged | break-glass audited + UI warning exists |

**Downstream:** W-10 needs P4-core merged (W-10 `:158`). W-4 edits `evals.md` after P4 (W-4 `:149`). W-8 re-anchors `core/config.py`, `ci-and-quality-gates.md` and (if OG-4 was signed) `.env.example` after P4 (W-8 `:158,:164`).

## 6. Review focus

These are the failure modes most likely to mislead a reader or an agent, most likely first.

1. **A doc claims an approved change is implemented before it lands.** This is recurring-failures #8 in reverse. Every "approved, not yet implemented" line has an F-task with a trigger. Task 16's grep `grep -rn "not yet implemented" docs/architecture` must list exactly the open W-items.
2. **A plan-04 replacement text is false on the post-P1 tree** (Tasks 5, 7 and 10 were). Each amended task re-verifies against code before editing.
3. **Staging sweeps owner edits** (`.serena/project.yml`, `docs/INDEX.md`). Explicit pathspecs plus the `git diff --cached --name-only` check in every commit.
4. **A Mermaid edit that renders but lies, or does not render.** Each diagram task includes a parse check (Task 16 Step 3) and an edge-by-edge evidence table.
5. **P4 writes an unmeasured test count.** Task 1 removes counts from `evals.md`. The baseline line changes only when Task 0 measured a different count.

---

## Task 0: Worktree and phase-start measurement

**Shell rules for every task:** start each shell with `set -o pipefail` and `WT=/mnt/c/Users/DangT/Documents/GitHub/hc-p4`. Commands shown with repo-relative paths run from `"$WT"` (`cd "$WT"` first). Any other `cd` uses an absolute path, never a relative `cd` after an earlier `cd`. The one intended exception to pipefail is a `grep` whose expected result is "no output".

**Files:** none (this task records into §15 of this plan in the PR branch).

- [ ] **Step 1: Clean worktree at post-P1 main**

```bash
set -o pipefail
WT=/mnt/c/Users/DangT/Documents/GitHub/hc-p4
git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral fetch origin
git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral worktree add "$WT" -b docs/p4-doc-drift origin/main
cd "$WT"
git status --short          # expect: empty
```

- [ ] **Step 2: Confirm preconditions.** Every line must print. If any is missing, stop (S2).

```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-p4; cd "$WT"
git merge-base --is-ancestor 7b2ff1f HEAD && echo B-in-main
git merge-base --is-ancestor 692fdf3 HEAD && echo A-in-main
test -f docs/capstone-report/owner-decisions-2026-09-27.md && echo P0-B-ok
grep -rn "start_notification_scheduler" src/backend/main.py && echo P2-wired
git ls-files .claude/agents | wc -l          # W-1: expect 5
test -x ~/venvs/asclexis-311/bin/python && echo D9-ok
git -C "$WT" ls-files --error-unmatch docs/plans/2026-09-27-P04-doc-drift-sweep-amendment.md && echo plan-on-main   # the plan set is committed; missing = STOP (S2)
```

- [ ] **Step 3: Measure the start tree**

```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-p4
cd "$WT/src/backend"
find "$WT/src/backend" -name __pycache__ -type d -prune -exec rm -rf {} +
~/venvs/asclexis-311/bin/python --version
~/venvs/asclexis-311/bin/python -m pytest tests/ --collect-only -q -p no:cacheprovider > /tmp/p4-collect.txt 2>&1; echo "collect_exit=$?"; tail -1 /tmp/p4-collect.txt
~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q -rf > /tmp/p4-run.txt 2>&1; echo "pytest_exit=$?"; tail -40 /tmp/p4-run.txt
cd "$WT"
python3 scripts/docs_lint.py; echo "lint=$?"
python3 scripts/generate_docs_index.py --check; echo "index=$?"
```

The exit codes are captured before `tail`, so a crashed collection cannot hide behind a successful `tail`. `collect_exit` must be 0. `pytest_exit` is 1 when tests fail; record every `FAILED` line from `-rf`.

Record the interpreter, OS, command, collected count (`START_COLLECTED`), and every failing node id (`START_FAILURES`) in §15. **Do not reuse any number from this plan.** For context only: `M@86606d0` collected 1291 with Windows Python 3.13.7 (program ground rule 2).

- [ ] **Step 4: Compare with the baseline lines.** Run `grep -n "tests collected\|collected;" "$WT/CLAUDE.md" "$WT/AGENT.md"`.
  - If both state `START_COLLECTED`, P4 does not touch them.
  - If either differs, it is stale. Task 16 Step 5 updates **only** the collected figure to `START_COLLECTED`, naming the interpreter. It does not change pass counts: P4 does not run CI, so writes no CI pass figure.

---

## Task 1 (amended): `docs/agentic/evals.md` — axes and counts, no hard-coded test count

**Files:** Modify `docs/agentic/evals.md:9,20,21` (main@40f590e).

Plan 04 wrote "1,245 collected" into this file. That is a figure P4 would not have measured on its tree (recurring-failures #3). This amendment points at the one measured baseline instead of copying it.

- [ ] **Step 1: Re-verify**

```bash
ls src/backend/tests/agent/golden/*.json | wc -l                  # M@86606d0: 74
sed -n '57,62p' scripts/agent_eval_gate.py                       # six bars
sed -n '9p;20p;21p' docs/agentic/evals.md
```

- [ ] **Step 2: Edit `:9`**

Before: `| Unit tests | Backend module behavior (~620 pytest tests) | \`src/backend/tests/\`, CI \`backend-tests\` |`

After:

```markdown
| Unit tests | Backend module behavior (measured collected count: the baseline line in [CLAUDE.md](../../CLAUDE.md)) | `src/backend/tests/`, CI `backend-tests` |
```

- [ ] **Step 3: Edit `:20`.** Use plan 04 Task 1 Step 2's `:20` text verbatim. If Step 1 printed a count other than 74, use the Step 1 count.

- [ ] **Step 4: Edit `:21`**

Before: the line beginning `2. **Backend regression suite**` and ending `lowering its 0.7 threshold.`

After:

```markdown
2. **Backend regression suite** — `bash scripts/run-backend-tests.sh -q` (CI) or `cd src/backend && python -m pytest tests/ -p no:cacheprovider -q` (local). The collected-count baseline lives in one place, the baseline line in [CLAUDE.md](../../CLAUDE.md); each phase measures and updates it. Where no embedding model is available, `test_api_rag_index_002b` fails on embedding similarity — a known environment-only failure that must not be "fixed" by lowering its 0.7 threshold.
```

- [ ] **Step 5: Verify**

```bash
grep -n "620\|four axes\|1,245\|1245" docs/agentic/evals.md      # expect: no output
grep -c "six axes" docs/agentic/evals.md                          # expect: 1
python3 scripts/harness_drift_check.py                             # expect: Harness drift check passed.
```

- [ ] **Step 6: Commit.** Use the pattern in §13: path `docs/agentic/evals.md`, message `docs(agentic): correct evals axes; point at the measured baseline`.

## Task 2 (run as written): README

Execute plan 04 Task 2. Anchors are unchanged at `main@40f590e` (`README.md:202`, `:493-517`, `:523-536`). Verify:

```bash
grep -n -i "faiss\|default OFF\|stubs, flag" README.md        # expect: none
grep -c "^| \*\*" README.md                                   # API table rows: 12 before, 19 after (check the table only)
```

Commit per §13. Paths: `README.md`.

## Task 3 (owner-gated, OG-4): `config/.env.example`

- [ ] **Step 1 (default, always): docs part.** `grep -rn "VECTOR_STORE_TYPE" README.md AGENT.md CLAUDE.md CONTRIBUTING.md docs/ src/frontend/README.md | grep -vE "docs/(archive|plans|research)/"`. Expected at M@86606d0: only `docs/features/TASK_LIST.md:675` (a dated session note: history, keep). Any other live hit: remove the mention, commit `docs: drop stale VECTOR_STORE_TYPE mention`.
- [ ] **Step 2: Check the sign-off.** If OG-4 in §12 is unsigned, record "Task 3 config edit: not licensed, skipped" in §15 and stop here.
- [ ] **Step 3 (only if OG-4 signed):** execute plan 04 Task 3 Step 2. Anchors: the block `config/.env.example:92-99` main@40f590e; `embedding_dimensions` at `B@7b2ff1f core/config.py:112`. Verify: `grep -n "VECTOR_STORE_TYPE\|faiss" config/.env.example` → none; `grep -c "^EMBEDDING_DIMENSIONS=384" config/.env.example` → 1. Own commit; paths: `config/.env.example`. Message: `chore(config): drop dead VECTOR_STORE_TYPE lines from the env template (owner OG-4)`.

## Task 4 (resequenced after P2): features-index notifications

- [ ] **Step 1: Did P2 already fix it?**

```bash
sed -n '26p' docs/features/00_features_index.md
git log --oneline -3 -- docs/features/00_features_index.md
grep -n "start_notification_scheduler" src/backend/main.py
```

- [ ] **Step 2: Decide**
  - If `:26` no longer says "all implemented" and P2's commit changed it: mark Task 4 **DONE by P2**, cite the commit sha in §15, and make no edit.
  - If `:26` is unchanged and `main.py` starts the scheduler: apply plan 04 Task 4 **Step 2b** only (Step 2a is obsolete after P2). Bump `**Last Updated:**` (`:3`).
  - If `main.py` does not start the scheduler: P2 did not land as planned. Stop (S2).
- [ ] **Step 3:** Run `python3 scripts/docs_lint.py`, then commit per §13. Paths: `docs/features/00_features_index.md`.

## Task 5R (replaces Task 5): correct the HC-M23 date in A's rescoped row

Plan 04 Task 5 is **dropped** (§3 row 5). A's row is correct except its date.

**Files:** Modify `docs/features/TASK_LIST.md:59` (A@692fdf3), row text only. `:256` is a dated session note and stays as history.

- [ ] **Step 1: Re-verify**

```bash
git log --format='%h %ad' --date=short --diff-filter=A -- src/backend/modules/import_structured.py   # 15b152c 2026-07-17
sed -n '853p' docs/features/TASK_LIST.md                                                             # "### 2026-07-17 - HC-M23 …"
grep -c "on 2026-07-30, so \"zero structured ingest\"" docs/features/TASK_LIST.md                     # expect 1
```

If the first command does not print `15b152c 2026-07-17`, stop and write what it printed.

- [ ] **Step 2: Edit.** Replace the exact fragment:

Before: `(FHIR R4 Bundle + lab CSV) on 2026-07-30, so "zero structured ingest" is no longer true.`

After: `(FHIR R4 Bundle + lab CSV; code dated 2026-07-17, \`15b152c\`), so "zero structured ingest" is no longer true.`

Keep the status cell `[ ] OPEN` and all 7 columns. Bump `**Last Updated:**` (`:4`).

- [ ] **Step 3: Verify.** `grep -n "2026-07-30, so" docs/features/TASK_LIST.md` → none; `python3 scripts/docs_lint.py` → passes (rule 4 still sees the OPEN row as well-formed). Commit paths: `docs/features/TASK_LIST.md`.

## Task 6 (amended): security-review status line

- [ ] **Step 1: Re-verify.** Run plan 04 Task 6 Step 1, plus:

```bash
grep -c "continue-on-error" .github/workflows/ci.yml                      # expect 0
grep -n 'if \[ "$code" -ge 2 \]' .github/workflows/ci.yml                  # expect 2 hits
```

- [ ] **Step 2: Insert after the `:9` blockquote** (main@40f590e), using the execution date:

```markdown
> **Status update (YYYY-MM-DD):** Re-verified during the P4 doc-drift sweep. **S06-SEC-003 is RESOLVED**: oversized request bodies get a clean 413 via `_send_error` in `security/input_validator.py`. **S06-SEC-004 is RESOLVED**: `scripts/backup.py::_validate_manifest_path` rejects absolute and `..` manifest paths and resolves within the intended base before verify and restore. The 2026-07-01 line's CI remark is also stale: `.github/workflows/ci.yml` has no `continue-on-error`, the bandit and pip-audit steps fail on a scanner error (exit code ≥ 2), and `scripts/security_gate.py` fails closed on a missing or malformed report. The finding bodies below are the original Sprint-06 record.
```

- [ ] **Step 3:** Commit per §13. Paths: `docs/compliance/security-review-sprint06.md`.

## Task 7 (amended): FAQ password recovery

- [ ] **Step 1: Re-verify**

```bash
grep -n "Generate (or replace)" src/backend/api/profiles.py
grep -n "RecoveryCodeCard" src/frontend/src/pages/SettingsPage.tsx
grep -n "Use your recovery code" src/frontend/src/pages/ProfileSetup.tsx
grep -n "Recovery code" src/frontend/src/components/settings/RecoveryCodeCard.tsx
```

All four must hit. If the Settings card or the link text differs, use the text found.

- [ ] **Step 2: Replace the answer** under `### What happens if I forget my password?` (`docs/user/faq.md:44-47` main@40f590e):

```markdown
When you create a profile, Asclexis shows a **one-time recovery code**. Store it
somewhere safe. While you can still sign in, you can create a new code (or a
first one, for a profile made before recovery codes existed) under **Settings →
Recovery code**. It asks for your password, and it replaces any earlier code.

If you forget your password, the recovery code is the only way back in: choose
**Use your recovery code** on the profile screen. Without a code the vault cannot
be opened. The password derives the encryption key, so there is no backdoor by
design. **Keep backups of your data** using the backup utility, and keep your
recovery code with them.
```

- [ ] **Step 3: Verify.** `grep -n "no password recovery" docs/user/faq.md` → none; `sed -n '100,112p' docs/user/faq.md` is unchanged, because that is W-5's range. Commit paths: `docs/user/faq.md`.

## Tasks 8, 9, 11, 13 (run as written)

| Task | Anchor corrections | Commit paths |
|---|---|---|
| 8 | none | `CONTRIBUTING.md` |
| 9 | Anchor the `AGENT.md` row by its text ("the four scoring axes"); the line number moves in P1's conflict resolution | `skills/asclexis-agent/SKILL.md skills/asclexis-evals/SKILL.md AGENT.md` |
| 11 | Expected counts at M@86606d0: 130 route decorators, 131 method rows. Diff prefix by prefix before concluding; `/health` and metrics rows live outside `api/*.py` | none if nothing is missing; else `docs/api/endpoints.md` |
| 13 | Index lines `A@692fdf3:63-65`; AGENT.md openwiki line anchored by "**Generated repo map**". First run `find openwiki -type f`: if G-C2 generated content, stop (S7) | `docs/00_architecture_plans_index.md AGENT.md` |
## Task 14 (owner-gated, OG-6): root `scripts/download_models.py`

- [ ] **Step 1 (default, always): docs part.** Run plan 04 Task 14 Step 1's grep. Expected hits, all fine: `AGENT.md` (`B@7b2ff1f:80-81`, backend path), `docs/model_tiers/README.md:35` (backend path), `docs/agentic/recurring-failures.md` (history), `TASK_LIST.md:65` (DONE row, history). A live doc naming the **root** path: repoint it to `src/backend/scripts/download_models.py` in a `docs:` commit.
- [ ] **Step 2: Check the sign-off.** If OG-6 in §12 is unsigned, record "Task 14 deletion: not licensed, skipped; root script remains" in §15 and stop here.
- [ ] **Step 3 (only if OG-6 signed):** delete the file as its own commit, then re-run the one test that imports a `download_models`:

```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-p4; cd "$WT"
git rm scripts/download_models.py
git diff --cached --name-only        # exactly: scripts/download_models.py
git commit -m "chore(scripts): remove the stale root download_models.py duplicate (owner OG-6)" -- scripts/download_models.py
cd "$WT/src/backend" && ~/venvs/asclexis-311/bin/python -m pytest tests/test_verify_model_repos.py -p no:cacheprovider -q   # same result as at start
```

## Task 10 (owner-gated, OG-5): the two package docstrings

**Files:** Modify `src/backend/api/__init__.py:1-14` and `src/backend/modules/agent/__init__.py:1-18` (main@40f590e). Docstrings only.

**Gate:** these are Python source files, so this is not a docs action. If OG-5 in §12 is unsigned, make no edit: record "Task 10: not licensed, skipped" in §15 and list both stale docstrings in the PR body (`api/__init__.py` says "HealthCentral" and lists 9 of 18 routers; `modules/agent/__init__.py` says "SCAFFOLD ONLY"). If signed, run the steps below as their own commit with message `docs(backend): correct the api and agent package docstrings (owner OG-5)`.

- [ ] **Step 1: Re-verify the agent fallback claim before writing it**

```bash
grep -n "run_agent\|except Exception" src/backend/api/assistant.py | head
grep -rnE "^\s*(from|import) (sqlalchemy|core|modules\.(faithfulness|redaction)|monitoring)" src/backend/modules/agent --include=*.py | head
```

The first command must show an `except` around the `run_agent` call that falls back to the legacy path. If it does not, delete the sentence "Any agent exception also falls back to the legacy path." from the text below.

- [ ] **Step 2: `api/__init__.py`.** Use plan 04 Task 10 Step 2 text verbatim. Re-check the order against `include_router` in the same file.

- [ ] **Step 3: `modules/agent/__init__.py`.** Replace the whole module docstring with:

```python
"""Asclexis read-only plan->act->reflect agent (E1 — Agent Core).

SHIPPED: this is the default ``/assistant/chat`` path
(``settings.AGENT_ENABLED_DEFAULT = True``). The per-profile ``agent_enabled``
setting is a kill switch back to the legacy single-shot RAG path, not a gate for
unfinished code. Any agent exception also falls back to the legacy path.

The one inviolable rule: the agent is READ-ONLY over clinical data. No module
here may write an observation, interpretation, medication, or any clinical row.
Write capability is a NEW epic, never a story (AGILE_PLAN §7).

Contents: the graph runner, the plan/act/reflect/draft nodes (draft composes
from templates and makes no LLM call), the read-only tool registry (8 tools),
the guardrails, and the eval scorer. Several modules import backend packages
(SQLAlchemy models, ``core.audit``, ``modules.faithfulness``,
``modules.redaction``), so the package no longer imports with only the standard
library and pydantic. Changes here affect the production safety path: read
skills/asclexis-agent and skills/asclexis-guardrails first.
"""
```

- [ ] **Step 4: Verify.** No test pins these docstrings (checked 2026-09-27: `grep -rln "SCAFFOLD ONLY\|API routes for" src/backend/tests` → none).

```bash
set -o pipefail; cd /mnt/c/Users/DangT/Documents/GitHub/hc-p4/src/backend && ~/venvs/asclexis-311/bin/python -c "import api, modules.agent; from main import app; print('import-ok')"
grep -n "SCAFFOLD ONLY\|NotImplementedError\|HealthCentral" /mnt/c/Users/DangT/Documents/GitHub/hc-p4/src/backend/api/__init__.py /mnt/c/Users/DangT/Documents/GitHub/hc-p4/src/backend/modules/agent/__init__.py   # expect none
```

Commit paths: `src/backend/api/__init__.py src/backend/modules/agent/__init__.py`.

## Task 12 (resequenced; D2): delete the 7 Serena memories

- [ ] **Step 1: Re-verify**

```bash
git ls-files .serena/memories | wc -l                       # expect 7
git log -1 --format='%h %ad' --date=short -- .serena/memories   # a0aa235 2026-01-07
git status --short .serena                                  # note ' M .serena/project.yml' if present — do not touch
```

If the count is not 7, stop (S1): D2 names exactly "the 7 stale memory files".

- [ ] **Step 2: Remove by explicit path.** No glob and no directory pathspec:

```bash
git rm .serena/memories/code_style_conventions.md .serena/memories/critical_01_07.md \
  .serena/memories/feature_implementation_progress.md .serena/memories/project_overview.md \
  .serena/memories/security_audit_findings.md .serena/memories/suggested_commands.md \
  .serena/memories/task_completion_checklist.md
git diff --cached --name-only        # exactly these 7 paths; .serena/project.yml absent
git commit -m "docs(agent-context): delete the 7 stale .serena memories (owner decision D2)" -- \
  .serena/memories/code_style_conventions.md .serena/memories/critical_01_07.md \
  .serena/memories/feature_implementation_progress.md .serena/memories/project_overview.md \
  .serena/memories/security_audit_findings.md .serena/memories/suggested_commands.md \
  .serena/memories/task_completion_checklist.md
```

The commit pathspec lists the same seven files, never the directory (C-GATE-3).

## Task 15 (resequenced after P3/W-1): verify only

Run W-1's hand-off checks (W-1 Task 9 Step 6):

```bash
grep -n "\.claude/agents/" docs/agentic/harness.md docs/agentic/roadmap.md   # 5 file paths + directory in harness.md; directory in roadmap.md (B lines :10, :17)
python3 scripts/harness_drift_check.py                                        # Harness drift check passed.
git ls-files .claude/agents | wc -l                                           # 5
```

If all pass: mark DONE-N/A and make no edit. If W-1 has not merged, or any check fails: **STOP (S2)**. P3/W-1 is a hard prerequisite of P4-core (§5), and the `AGENT.md` edit order needs it (§4).

---

## Task N1 (new): `pipelines.md` Document → insight: what each surface reads (divergence 1; D4 approved and pending)

**Files:** Modify `docs/architecture/pipelines.md:41-46` and `:52-57` (main@40f590e), and bump `:3`.

**Evidence** (M@86606d0, planner-verified 2026-09-27; re-run at execution):

| Surface | What it does with unverified rows | Evidence |
|---|---|---|
| agent tools | verified only | `modules/agent/tools/query_observations.py:56`, `compute_trend.py:45-56`, `retrieve_chunks.py:73` (overview §5) |
| FHIR, visit prep, pinboards | verified only | `modules/fhir_export.py:358`, `api/export.py:764`, `api/pinboards.py:146,452` |
| medications | verified by default; `verified_only` is overridable | `api/medications.py:461,499,514` |
| timeline | labels each event `verification_status` | `modules/timeline.py:116-118` |
| highlights | unreviewed entities labelled; rejected dropped | `modules/highlights.py:22-26,93` |
| care-task candidates | rejected entities dropped | `api/care_tasks.py:171,192,245` |
| medication reconciliation | rejected entities dropped | `modules/med_reconcile.py:218,229`; `api/med_reconcile.py:66` |
| trends | included; `TrendPoint` has no verification field | `api/observations.py:529-535` (no filter), `:156-169` (schema) |
| legacy RAG | included | `modules/rag.py:322-328,433` |
| CSV / JSON / doctor summary | included (CSV/JSON carry a `user_verified` column) | `api/export.py:130-150,170` |

- [ ] **Step 1: Re-verify.** Run the evidence commands and note any difference in §15:

```bash
grep -n "user_verified" src/backend/api/observations.py src/backend/modules/rag.py src/backend/api/export.py src/backend/modules/timeline.py
grep -n "verified_by_user" src/backend/modules/highlights.py src/backend/api/care_tasks.py src/backend/modules/med_reconcile.py
```

If W-3 has already merged, skip to F1's After text instead of the pending wording below.

- [ ] **Step 2: Diagram edges.** Replace lines `:41-46`:

Before:
```
    VERIFIED --> TRENDS["trends"]
    VERIFIED --> TL["timeline"]
    VERIFIED --> HL["highlights"]
    VERIFIED --> TASKS["care-task candidates"]
    VERIFIED --> RECON["medication reconciliation"]
    VERIFIED --> EXPORT["exports: doctor summary · visit prep · FHIR · CSV/JSON"]
```
After:
```
    VERIFIED --> VONLY["verified only: agent tools · FHIR ·<br/>visit prep · pinboards · medications (default)"]
    STORE -.->|"labelled pending"| TL["timeline"]
    STORE -.->|"unreviewed labelled, rejected dropped"| HL["highlights"]
    STORE -.->|"rejected dropped"| TASKS["care-task candidates"]
    STORE -.->|"rejected dropped"| RECON["medication reconciliation"]
    STORE -.->|"unverified included, unlabelled (D4 approved, W-3 pending)"| TRENDS["trends"]
    STORE -.->|"unverified included (outside D4)"| EXPU["exports: doctor summary · CSV/JSON"]
```

- [ ] **Step 3: Prose.** Replace `:52-57`:

Before (exact): the paragraph from `**Everything lands unverified.**` through `rather than presenting them as history.`

After:
```markdown
**Everything lands unverified.** That is the load-bearing property of this
diagram: extraction is a suggestion, not a fact, until a human confirms it.
Structured imports are no exception — a FHIR bundle is more accurate than OCR
but still arrives unverified. Surfaces differ in what they do with unverified
rows:

- **Verified only:** agent tools, FHIR export, visit prep, pinboards, and
  medications (unless the caller passes `verified_only=false`).
- **Shown with a label:** the timeline (pending) and highlights (unreviewed).
  Rows the user rejected are dropped from highlights, care-task candidates and
  medication reconciliation.
- **Included without a label:** trends and the legacy (non-agent) RAG path.
  Owner decision [D4](../capstone-report/owner-decisions-2026-09-27.md)
  (2026-09-27) approved the change: trends may show unverified points only
  when visibly marked "unverified", and legacy RAG cites verified values only.
  **Approved, not yet implemented** (work item W-3).
- **Included, outside D4:** CSV / JSON exports and the doctor summary.
```

- [ ] **Step 4: Verify**

```bash
grep -n "Downstream surfaces consume the \*verified\* set" docs/architecture/pipelines.md   # expect none
grep -c "W-3 pending\|work item W-3" docs/architecture/pipelines.md                       # expect 2
```

Commit is combined with N2 and N3 (one file). See N3 Step 4.

## Task N2 (new): `pipelines.md` assistant graph: the agent draft makes no LLM call; legacy checks run on the legacy path (divergences 2 and 3)

**Evidence:**
- Agent draft is template composition: `main@40f590e modules/agent/nodes/draft.py:1-31`, and `grep -rn "model_runner\|ModelRunner" src/backend/modules/agent` → no call.
- The guard imports only `FaithfulnessConfig` from `modules.faithfulness` (`B@7b2ff1f guardrails/guard.py:32`), for the 0.6 threshold at `:34`.
- Nothing in `modules/agent` imports `interpret_safety` or `verifier_agent`.
- The legacy path imports all three at `modules/rag.py:33-45`. `validate_response` is at `:793`; `[cite:N]` at `:819`; the 0.6 check at `:862` only sets `is_valid=False` (C-SAFE-2 "This threshold does not block").

- [ ] **Step 1: Re-verify**

```bash
grep -rn "interpret_safety\|verifier_agent\|faithfulness" src/backend/modules/agent --include=*.py | grep -v "^\s*#"
grep -n "verifier_agent\|faithfulness\|interpret_safety\|is_valid=len" src/backend/modules/rag.py | head
```

If W-4 has merged, use F4's edge instead of the dashed "still served" edge.

- [ ] **Step 2: Replace `:95-96`**

Before:
```
    RAGONLY --> MR
    DRAFT --> MR["ModelRunner"]
```
After:
```
    RAGONLY --> MR["ModelRunner"]
```

- [ ] **Step 3: Replace `:110` and `:112`.** Keep `:111`: N8 owns that label.

Before:
```
    GUARD --> SAFE["interpret_safety<br/>faithfulness · verifier_agent"]
    SAFE --> OUT["cited answer<br/>[REFERENCE:N] / [YOUR_RESULTS:N]"]
    SAFE -->|"fails"| ABSTAIN["abstain with reason"]
```
After:
```
    GUARD --> AOUT["agent answer<br/>template-composed, every sentence cited"]
    GUARD -->|"ungrounded or advice-bait"| ABSTAIN["abstain / escalate<br/>fixed templates"]
    MR --> SAFE["legacy-path checks: validate_response ·<br/>verifier_agent · faithfulness · interpret_safety patterns"]
    SAFE --> OUT["cited answer<br/>[REFERENCE:N] / [YOUR_RESULTS:N]"]
    SAFE -.->|"faithfulness below 0.6: is_valid=false,<br/>answer still served (W-4 pending)"| OUT
```

- [ ] **Step 4: Prose.** Change `Three things this diagram is asserting:` to `Four things this diagram is asserting:`, and append after item 3 (after `end.` at `:127`):

```markdown
4. **Only the legacy path calls a model.** The agent's `draft` node composes
   answers from templates over tool output; it makes no LLM call. The legacy
   safety modules (`interpret_safety`, `faithfulness`, `verifier_agent`) run on
   the legacy path only. The agent guard reuses just the 0.6 confidence cutoff
   from `modules/faithfulness.py` and abstains below it.
```

- [ ] **Step 5: Verify**

```bash
grep -n "DRAFT --> MR" docs/architecture/pipelines.md               # expect none
grep -n "GUARD --> SAFE" docs/architecture/pipelines.md             # expect none
grep -c "W-4 pending" docs/architecture/pipelines.md                # expect 1
```

## Task N3 (new): `pipelines.md` export redaction (divergence 4; D3 approved and pending)

**Evidence:**
- Redacted: RL `modules/rl_dataset.py:105`; FHIR `modules/fhir_export.py:58`; visit prep `modules/export.py:533,637-640`; pinboard export → `compose_visit_prep_packet` (`api/pinboards.py:382,485`).
- Not redacted: CSV/JSON (`api/export.py:904,960` → `modules/export.py:223,267`); doctor summary (`modules/export.py:82,290,358`); backups (deliberate, `data-privacy.md:173-178`).

- [ ] **Step 1: Re-verify**

```bash
grep -n "RedactionEngine" src/backend/modules/export.py src/backend/modules/fhir_export.py src/backend/modules/rl_dataset.py
```

If W-2 **and** W-10 have merged, use F2's After text.

- [ ] **Step 2: Replace `:164`**

Before: `        EXP["exports · FHIR · visit-prep · RL dataset"]`

After: `        EXP["redacted exports:<br/>RL dataset · FHIR · visit prep · pinboards"]`

- [ ] **Step 3: Replace `:181-184`**

Before (exact): the paragraph from `The purple nodes are the mandatory chokepoints. Redaction is unconditional on` through `be made *less* redacted by configuration.`

After:
```markdown
The purple nodes are the mandatory chokepoints. On the export path, redaction
runs on the RL dataset export (forced `policy_level="strict"` with no
configuration knob, because an export must not be made *less* redacted by
configuration) and on FHIR, visit-prep and pinboard exports. It does **not** run
on CSV / JSON exports, the doctor summary, or backups. Backups are deliberately
unredacted: a redacted backup cannot be restored. For the other three, owner
decision [D3](../capstone-report/owner-decisions-2026-09-27.md) (2026-09-27)
applies: the doctor summary is to be strictly redacted (**approved, not yet
implemented**, work item W-2), and CSV / JSON stay full-fidelity as the
patient's own data, to be named as deliberate exceptions in `CLAUDE.md` and
`docs/compliance/data-privacy.md` (work item W-10).
```

- [ ] **Step 4: Verify and commit N1–N3**

```bash
grep -n "Redaction is unconditional" docs/architecture/pipelines.md   # expect none
sed -i 's/^\*\*Last Updated:\*\* .*/**Last Updated:** YYYY-MM-DD/' docs/architecture/pipelines.md   # use the execution date
```

Render check: Task 16 Step 3. Commit per §13. Paths: `docs/architecture/pipelines.md`. Message: `docs(architecture): pipelines match code — verification scope, agent draft, legacy checks, export redaction`.

## Task N4 (new): `docs/architecture/README.md`: ModelRunner scope and outbound paths (divergence 5, plus the outbound claim)

**Evidence** (M@86606d0):
- `modules/model_selector.py:456` `from llama_cpp import Llama` (B moved it from main `:438`); `interpret_with_model` (`modules/interpret.py:877`) has 0 callers (`grep -rn interpret_with_model src/backend --include=*.py | grep -v tests` → only the def).
- `core/external_runner.py:267,300` call `api.openai.com` / `api.anthropic.com`.
- `modules/embeddings.py:56` `SentenceTransformer(self.config.model_name)` has no offline flag.

- [ ] **Step 1: Re-verify** with the three greps above. For each W-item already merged (W-6, W-7, W-8, W-10), use that bullet's F3/F5/F6 text instead.

- [ ] **Step 2: Replace `:50`** (main@40f590e)

Before: `            MR["ModelRunner facade<br/><i>the only LLM entry point</i>"]`

After: `            MR["ModelRunner facade<br/><i>entry point for local inference</i>"]`

- [ ] **Step 3: Replace `:94-97`**

Before (exact): the paragraph from `The dashed Hugging Face edge is the **only** outbound connection in the` through `design; see [\`CLAUDE.md\`](../../CLAUDE.md) hard invariants.`

After:
```markdown
The dashed Hugging Face edge is a model download the user chooses in Settings.
It is not the only outbound path in code today:

- **Embedding model, first use.** `modules/embeddings.py` builds
  `SentenceTransformer(name)` with no offline flag, so the first embedding call
  can fetch the model from Hugging Face. Owner decision D8 (2026-09-27): no
  runtime download. Interim delivery (D8-delivery): `download_models.py`
  fetches the model once into a local models dir, and the runtime loads that
  path with Hugging Face offline and fails closed if it is absent; an
  installer bundles it later (G-C4). **Approved, not yet implemented** (work
  item W-8).
- **Opt-in cloud LLM.** `core/external_runner.py` can call OpenAI or Anthropic
  when the user enables the external API (off by default). It does not go
  through `ModelRunner`. Owner decision D12 (2026-09-27) keeps it as a
  documented exception and makes strict redaction unconditional, with
  break-glass only with audit and a UI warning: **approved, not yet
  implemented** (work items W-6, W-10).

`ModelRunner` is the entry point for local inference. One dormant path bypasses
it: `modules/model_selector.py` imports `llama_cpp` directly, and its only
caller, `interpret_with_model`, is never called. Owner decision D7 routes it
through `ModelRunner` (work item W-7, not yet implemented). `OllamaProvider` is
pinned to localhost by design; see [`CLAUDE.md`](../../CLAUDE.md) hard
invariants. All decisions: [owner-decisions-2026-09-27.md](../capstone-report/owner-decisions-2026-09-27.md).
```

- [ ] **Step 4: Verify.** `grep -n "the only LLM entry point\|is the \*\*only\*\* outbound" docs/architecture/README.md` → none. Bump `:3`. Commit paths: `docs/architecture/README.md`.

## Task N5 (new): `docs/architecture/backend.md`: layering rule and ModelRunner rule (divergence 6)

**Evidence.** `grep -rnE "^\s*(from|import) (modules|api)\b" src/backend/core` at main@40f590e and M@86606d0 returns **5** hits, all function-local:
- `core/config.py:229` (B `:228`)
- `core/document_crypto.py:65`
- `core/external_runner.py:202`
- `core/llm/llama_cpp_provider.py:122`
- `core/model_runner.py:117`

Overview §12 lists only 3 (§14 finding 1). `api/model_settings.py:770,809-810,828` imports `core.llm.factory` / `ollama_provider` directly.

- [ ] **Step 1: Re-verify** with the two greps above (the second: `grep -rnE "(from|import) core\.(llm|model_runner)" src/backend/api`). Use the counts and paths found.

- [ ] **Step 2: Replace `:86`**

Before: `    api -.->|"never directly"| C3`

After: `    api -.->|"provider switch only, no generation"| C3`

- [ ] **Step 3: Replace `:93-97`**

Before (exact): the two bullets from `- Dependencies point **downward only**.` through `violation, which is why that edge is drawn dotted and labelled.`

After:
```markdown
- Dependencies point **downward** by design: `api/` → `modules/` → `core/`.
  Five `core/` modules import from `modules/` today, all inside functions:
  `core/config.py` (`modules.redaction`), `core/external_runner.py`
  (`modules.redaction`), `core/model_runner.py` (`modules.model_selector`),
  `core/document_crypto.py` (`modules.ingest`) and
  `core/llm/llama_cpp_provider.py` (`modules.model_integrity`). None imports
  from `api/`. New `core/` → `modules/` imports should not be added.
- Feature code reaches local inference through `ModelRunner` → `llm/factory`.
  Importing `llama_cpp` or calling Ollama directly from feature code is a
  violation. Known deviations: the dormant `llama_cpp` import in
  `modules/model_selector.py` (owner decision D7: route it through
  `ModelRunner`, work item W-7, not yet implemented) and the opt-in cloud runner
  `core/external_runner.py` (owner decision D12: a documented exception, work
  items W-6 and W-10, not yet implemented). `api/model_settings.py` calls
  `llm/factory` directly only to inspect and switch the provider; it generates
  no text. That is the dotted edge.
```

- [ ] **Step 4: Verify.** `grep -n "never imports from\|never directly" docs/architecture/backend.md` → none. Bump `:3`. Commit paths: `docs/architecture/backend.md`.

## Task N6 (new): `docs/architecture/ci-and-quality-gates.md` matches `ci.yml` (divergence 7, plus drift B introduced)

**Evidence** (`B@7b2ff1f .github/workflows/ci.yml`):
- docs-lint runs `repo_hygiene_check.py` (`:31`).
- frontend runs `npm ci`, `tsc --noEmit`, `vitest run` only (`:68-76`); no build, no eslint.
- The scanner steps fail on exit ≥ 2 (`:95-133`), and `security_gate.py` fails closed.
- agent-evals fails on any bar or case (`scripts/agent_eval_gate.py:111-135`).
- The doc's `:44` "~1160 passing" is an asserted figure (recurring-failures #3).

- [ ] **Step 1: Re-verify**

```bash
grep -n "run: \|needs:" .github/workflows/ci.yml
sed -n '111,135p' scripts/agent_eval_gate.py
```

If W-4 has merged, also apply F4's job row.

- [ ] **Step 2: Edits** (main@40f590e anchors; match the Before text exactly)

| Line | Before | After |
|---|---|---|
| `:17` | `DOCS["docs-lint<br/>docs_lint.py · generate_docs_index.py --check<br/>feature_list_lint.py"]` | `DOCS["docs-lint<br/>docs_lint.py · generate_docs_index.py --check<br/>feature_list_lint.py · repo_hygiene_check.py"]` |
| `:19` | `FE["frontend-tests<br/>tsc --noEmit · vitest · build"]` | `FE["frontend-tests<br/>tsc --noEmit · vitest"]` |
| `:43` | `\| \`docs-lint\` \| Doc drift (DOC-003…DOC-013), stale generated index, malformed feature inventory \|` | `\| \`docs-lint\` \| Doc drift (DOC-003…DOC-013), stale generated index, malformed feature inventory, scratch files at the repo root \|` |
| `:44` | `\| \`backend-tests\` \| Any pytest failure \| Baseline is ~1160 passing, 1 known env-only embedding-similarity failure \|` | `\| \`backend-tests\` \| Any pytest failure \| The measured collected-count baseline is the one in [CLAUDE.md](../../CLAUDE.md); see "Known env-only failure" below \|` |
| `:45` | `\| \`frontend-tests\` \| Type errors, vitest failures, build failures \| — \|` | `\| \`frontend-tests\` \| Type errors and vitest failures. \`npm run build\` and eslint are **not** run in CI (contract C-API-3) \| — \|` |
| `:46` | `\| \`security-scan\` \| High/critical findings not covered by a dated, owner-attributed waiver \| Waivers expire on purpose \|` | `\| \`security-scan\` \| High/critical findings not covered by a dated, owner-attributed waiver; a scanner error (exit ≥ 2); a missing or malformed report \| Waivers expire on purpose; the gate fails closed \|` |
| `:47` | `\| \`agent-evals\` \| \`injection_resistance < 1.0\` or \`phi_leakage > 0\` \|` (row start) | `\| \`agent-evals\` \| Any failed golden case or missed bar: groundedness, citation, abstention and injection_resistance == 1.0; advice_leakage and phi_leakage == 0. Agent path only \|` (keep the third cell) |

- [ ] **Step 3: Verify**

```bash
grep -n "~1160\|· build\"\|build failures" docs/architecture/ci-and-quality-gates.md   # expect none
grep -c "repo_hygiene_check" docs/architecture/ci-and-quality-gates.md                 # expect 1
```

Bump `:3`. Commit paths: `docs/architecture/ci-and-quality-gates.md`.

## Task N7 (new): `core/config.py` Ollama comment vs `validate_startup`

**Evidence (B@7b2ff1f):**
- `:108` reads `# Ollama base URL (must be localhost — non-local URLs are rejected at startup)`.
- `validate_startup` (`:196`) contains no Ollama or localhost check (`awk '/def validate_startup/,/^def |^class /' … | grep -i ollama` → none).
- Enforcement lives in `_assert_localhost` (`core/llm/ollama_provider.py:40`, called at `:73`) and `PUT /settings/model/provider` (`api/model_settings.py:810-817`).
- `core/llm/factory.py:51` builds `OllamaProvider(model=model)` without this setting, so the provider uses its own `127.0.0.1:11434` default (`ollama_provider.py:31,71`).

- [ ] **Step 1: Re-verify** with the evidence commands, and `grep -rn "ollama_base_url" src/backend --include=*.py | grep -v tests`.

- [ ] **Step 2: Replace the one comment line** (keep the code line):

Before:
```python
    # Ollama base URL (must be localhost — non-local URLs are rejected at startup)
```
After:
```python
    # Ollama base URL. Must be localhost. validate_startup does not check it; the
    # model-settings API asserts it via _assert_localhost. core/llm/factory.py does
    # not pass it to OllamaProvider, which uses its own 127.0.0.1:11434 default.
```

- [ ] **Step 3: Verify**

```bash
git -C /mnt/c/Users/DangT/Documents/GitHub/hc-p4 diff -U0 src/backend/core/config.py | grep '^[+-][^+-]' | grep -v '^[+-]\s*#'   # expect none (comment-only); no pipefail here: grep finding nothing is the pass
set -o pipefail; cd /mnt/c/Users/DangT/Documents/GitHub/hc-p4/src/backend && ~/venvs/asclexis-311/bin/python -c "from core.config import settings; print(settings.ollama_base_url)"   # http://127.0.0.1:11434
grep -n "rejected at startup" /mnt/c/Users/DangT/Documents/GitHub/hc-p4/src/backend/core/config.py                                            # expect none
```

Commit paths: `src/backend/core/config.py`. Message: `docs(config): correct the Ollama URL comment; startup does not check it`.

---

## Deferred tasks (each its own branch, commit and PR, after its trigger)

Common steps for every deferred task:
1. Create a fresh worktree from `origin/main`.
2. Confirm the trigger with the given command.
3. Match the Before text exactly once.
4. Edit, then run the §11 gates.
5. Commit per §13 and open a PR.
6. Stop for the owner's merge.

### Task N8 (after W-5): D11 citation vocabulary in P4-owned docs

**Trigger:** `grep -n "YOUR_RESULTS:N\]\|REFERENCE:N\]" src/backend/modules/rag.py` no longer shows the `:128`/`:133`/`:134` cite instructions (W-5 merged), and `grep -n 'citation_pattern = r"\\\[cite:' src/backend/modules/rag.py` still hits (no validator edit).

**Not owned:** `CLAUDE.md:62` (D11 invariant line). It is never P4's (orchestrator ruling). If W-10's Q1 is unsigned, the line stays **unchanged** as an open owner item; P4 does not edit it in any case (§14 finding 11). Also not owned: W-5's four docs (§4).

| File (anchor) | Before | After |
|---|---|---|
| `docs/architecture/pipelines.md:111` | `    SAFE --> OUT["cited answer<br/>[REFERENCE:N] / [YOUR_RESULTS:N]"]` | `    SAFE --> OUT["cited answer<br/>[cite:N] markers (context labels are not citations)"]` |
| `docs/features/00_features_index.md:38` | `ground in two citation layers. \`[YOUR_RESULTS:N]\` cites patient's own observation context (latest measured value, normal range, trend direction), while \`[REFERENCE:N]\` cites auto-seeded reference knowledge base (general biomarker definitions, clinical significance).` | `ground in two context layers, labelled \`[YOUR_RESULTS:N]\` (the patient's own observation context: latest measured value, normal range, trend direction) and \`[REFERENCE:N]\` (the auto-seeded reference knowledge base: general biomarker definitions, clinical significance). Answers cite both with \`[cite:N]\` markers, the only format \`validate_response\` checks; the labels are not citation markers.` |
| `docs/features/04_self_improvement_loop.md:113` | `- Grounded, cited responses — \`[REFERENCE:N]\` / \`[YOUR_RESULTS:N]\` format preserved.` | `- Grounded, cited responses — \`[cite:N]\` citation format preserved (\`[REFERENCE:N]\` / \`[YOUR_RESULTS:N]\` are context labels, not citation markers).` |
| `docs/features/TASK_LIST.md:63` (A@692fdf3) | `` `[YOUR_RESULTS:N]` chips in ExplainAssistant become deep links`` | `citation chips in ExplainAssistant (rendered from \`[cite:N]\` markers, \`services/assistant.ts:378\`) become deep links` |

- [ ] **Step 1: Check the rest of the features-index `:38` sentence against merged W-5.** `grep -n "REPORT FACTS\|GENERAL INFO" src/backend/modules/rag.py`: if W-5 removed the Report Facts / General Info split, rewrite that clause to match; otherwise keep it.
- [ ] **Step 2: Apply the 4 rows.** Bump `**Last Updated:**` in `00_features_index.md` and `TASK_LIST.md` (both canonical, DOC-004).
- [ ] **Step 3: Sweep.** Every remaining hit must be W-5-owned, accurate, `CLAUDE.md` (W-10), or point-in-time:

```bash
grep -rn "YOUR_RESULTS:N\|REFERENCE:N" --include=*.md . | grep -vE "^\./(docs/(archive|plans|research)|audit)/"
```

Expected remaining:
- `AGENT.md` flow 2 (describes retrieval labels; accurate).
- `CLAUDE.md` (W-10).
- `docs/brand/brand-guidelines.md:37-38` (accurate).
- `docs/compliance/ai-safety.md`, `docs/features/01_lab_result_interpreter_architecture.md`, `docs/user/faq.md`, `docs/user/workflows.md` (W-5 has rewritten these as label wording; confirm).
- `docs/features/00_features_index.md:38` and `04_self_improvement_loop.md:113` (now label wording).

Any other hit: stop and route it (S5).

- [ ] **Step 4: Commit.** Paths: `docs/architecture/pipelines.md docs/features/00_features_index.md docs/features/04_self_improvement_loop.md docs/features/TASK_LIST.md`. Message: `docs: describe [cite:N] as the citation marker and the context labels as labels (D11)`.

### Task N9 (owner-gated: after plan 08 Brief 2 is signed): `hipaa-controls.md:169`

**Trigger:** the packet's sign-off ledger row "2 | Key rotation" has a ticked choice, a date and the owner's name (`grep -n "Key rotation" audit/2026-09-25/gated-items-decision-packet.md`). No signature → do not run (S6).

Before (`docs/compliance/hipaa-controls.md:169` main@40f590e, unchanged by A/B): `| Key rotation | Medium | Manual via password change |`

After: the row matching the signed option, as proposed in the [P08 amendment](2026-09-27-P08-gated-packet-hipaa-aligned-amendment.md) Task 3:
- A (docs only), reject or defer: `| Key rotation | Medium | Not implemented. A password change re-seals the existing data key under the new password; the database and document key itself does not change. |`
- B or C approved: `| Key rotation | Medium | Owner-approved <signed date>, not yet implemented (plan: <link>). Until it ships, a password change re-seals the existing data key only. |`
- D only: A's row, plus `| Session-secret rotation | Low | <as implemented> |`

Verify: `grep -n "Manual via password change" docs/compliance/hipaa-controls.md` → none. Evidence behind the wording: `api/profiles.py` `change_password` re-seals the same DEK (plan 08 Task 3; C-KEY-3). Commit paths: `docs/compliance/hipaa-controls.md`.

### Task N10 (after W-6): `skills/asclexis-guardrails/SKILL.md:63`

**Trigger:**
```bash
grep -n "redaction_bypass_active\|BREAK_GLASS_AUDIT_EVENT" src/backend/core/external_runner.py   # hits
grep -rn "redaction_break_glass" src/frontend/src | head -1                                      # hit
```

Before (`main@40f590e:62-64`):
```
Generate escalation/abstention prose · let an unmapped claim survive · hedge below
threshold · run the advice gate only once · bypass redaction for any reason ·
treat abstain/escalate as failures.
```
After:
```
Generate escalation/abstention prose · let an unmapped claim survive · hedge below
threshold · run the advice gate only once · bypass redaction, except through the
external runner's owner-approved break-glass (D12, 2026-09-27: "keep break-glass
only with audit + UI warning") · add any new bypass · treat abstain/escalate as
failures.
```

The wording deliberately says nothing about which environments break-glass works in (W-6 Q1) or where the warning shows (W-6 Q3); both are open. `:41-46` ("PHI redaction gate") is checked and kept: it is scoped to the agent's gate, `gate_external_payload` has no bypass (`modules/agent/guardrails/redaction_gate.py:1-30`), and D12 removes the "debugging" (dev) bypass it forbids.

Verify:
```bash
grep -c "bypass redaction for any reason" skills/asclexis-guardrails/SKILL.md          # 0
grep -c "keep break-glass" skills/asclexis-guardrails/SKILL.md                         # 1
```

Then run the relative-link check (§11). Commit paths: `skills/asclexis-guardrails/SKILL.md`.

### Tasks F1–F6: flip "approved, not yet implemented" when the work lands

| # | Trigger (command must hit) | File: Before (P4-core text) → After |
|---|---|---|
| F1 | W-3 merged: `grep -n "user_verified" src/backend/api/observations.py` shows a `TrendPoint` field, and `modules/rag.py` filters `user_verified` | `pipelines.md`: the bullet `**Included without a label:** trends and the legacy …` → `**Shown with a label (trends):** unverified trend points are marked "Unverified" (owner decision D4).` Add `the legacy (non-agent) RAG path` to the **Verified only** bullet. Add "chunks" there only if W-3's O-5 was signed (read its PR). Change the TRENDS edge label to `"unverified points marked Unverified (D4)"`. Grep: `grep -c "W-3 pending\|work item W-3" pipelines.md` → 0 |
| F2 | W-2 **and** W-10 merged: `grep -n "RedactionEngine" src/backend/modules/export.py` shows the summary path; `grep -nE "CSV\|JSON" CLAUDE.md` shows the D3 exception | `pipelines.md` `:164` label gains `· doctor summary`. In the N3 paragraph, replace `the doctor summary is to be strictly redacted (**approved, not yet implemented**, work item W-2), and CSV / JSON stay full-fidelity as the patient's own data, to be named as deliberate exceptions in` with `the doctor summary is strictly redacted, and CSV / JSON stay full-fidelity as the patient's own data, named as deliberate exceptions in`. Also remove "the doctor summary," from `It does **not** run on …`. Grep: `grep -c "work item W-2" pipelines.md` → 0 |
| F3 | W-7 merged: `grep -rnE "from llama_cpp\|import llama_cpp" src/backend --include=*.py \| grep -v tests` → only `core/llm/llama_cpp_provider.py` | `README.md` N4: delete the sentence pair `One dormant path bypasses it: … (work item W-7, not yet implemented).`. `backend.md` N5: replace `Known deviations: the dormant \`llama_cpp\` import in \`modules/model_selector.py\` (owner decision D7: route it through \`ModelRunner\`, work item W-7, not yet implemented) and the opt-in cloud runner` with `The one documented exception is the opt-in cloud runner`. Grep: `grep -rc "W-7" docs/architecture` → 0 |
| F4 | W-4 merged: `grep -n "legacy-evals" .github/workflows/ci.yml` hits | `pipelines.md`: replace the dashed `SAFE -.->` edge with `SAFE -->\|"faithfulness below 0.6"\| LABST["abstention / knowledge-fallback template"]`, using the template name from W-4's merged code. `ci-and-quality-gates.md`: add a `LEGACY` job node and a table row using W-4's job name and bar. Grep: `grep -c "W-4 pending" pipelines.md` → 0 |
| F5 | W-8 merged: `grep -n "local_files_only\|HF_HUB_OFFLINE" src/backend/modules/embeddings.py` hits | `README.md` N4 bullet `**Embedding model, first use.** …` → `**Embedding model.** Fetched once by \`src/backend/scripts/download_models.py\` into a local models dir, then loaded from that path with Hugging Face offline; the app fails closed if it is absent (owner decisions D8 / D8-delivery). Installer bundling is later work (G-C4).` (Adjust to W-8's merged command.) Do not write "bundled" unless G-C4 has shipped. Grep: `grep -c "W-8" docs/architecture/README.md` → 0 |
| F6 | W-6 **and** W-10 merged: N10 trigger hits, and `grep -n "external runner" CLAUDE.md` names the exception | `README.md` N4 bullet `**Opt-in cloud LLM.**`: replace `: **approved, not yet implemented** (work items W-6, W-10).` with `. Break-glass writes an audit record and shows a warning in Settings.` `backend.md`: replace `work items W-6 and W-10, not yet implemented` with `named in \`CLAUDE.md\``. Grep: `grep -rc "W-6" docs/architecture` → 0 |

Each F-task commit lists only its files. Message: `docs(architecture): <item> landed — drop the pending note`.

---

## Task 16 (amended): P4-core close-out, gates, index

- [ ] **Step 1: Stale-claim greps.** Expected output is given for each.

```bash
grep -n "620\|four axes" docs/agentic/evals.md                                            # none
grep -ni "faiss" README.md                                                              # none
grep -n "VECTOR_STORE_TYPE" config/.env.example                                          # none if OG-4 signed; 1 hit if not
grep -n "default OFF\|stubs, flag" README.md                                              # none
grep -n "2026-07-30, so" docs/features/TASK_LIST.md                                       # none (Task 5R)
grep -c "INGEST-FHIR-001.*\[ \] OPEN" docs/features/TASK_LIST.md                          # 1 (A's rescope kept)
grep -n "no password recovery" docs/user/faq.md                                           # none
grep -n "gsd" CONTRIBUTING.md                                                             # none
grep -n "SCAFFOLD ONLY\|NotImplementedError" src/backend/modules/agent/__init__.py        # none if OG-5 signed; hits if not
grep -n "HealthCentral" src/backend/api/__init__.py                                       # none if OG-5 signed; hit if not
ls scripts/download_models.py 2>&1                                                        # No such file if OG-6 signed; present if not
git diff --name-only origin/main...HEAD -- config/.env.example src/backend/api/__init__.py src/backend/modules/agent/__init__.py scripts/download_models.py   # only the files whose OG line is signed
git ls-files .serena/memories | wc -l                                                     # 0
git ls-files .serena/project.yml                                                          # still tracked, unchanged
grep -n "OpenWiki-generated repo map\|OpenWiki-generated navigation" docs/00_architecture_plans_index.md AGENT.md   # none
grep -n "rejected at startup" src/backend/core/config.py                                  # none
grep -n "DRAFT --> MR\|GUARD --> SAFE\|Redaction is unconditional\|consume the \*verified\* set" docs/architecture/pipelines.md   # none
grep -n "the only LLM entry point\|never imports from\|~1160" docs/architecture/*.md      # none
grep -rn "not yet implemented\|pending)" docs/architecture/*.md                           # only W-2, W-3, W-4, W-6, W-7, W-8, W-10 mentions; list them in §15
```

- [ ] **Step 2: Guard the not-owned files**

```bash
git diff --name-only origin/main...HEAD -- docs/compliance/data-privacy.md .serena/project.yml docs/capstone-report audit   # expect none
git diff -U0 origin/main...HEAD -- CLAUDE.md                                               # expect none, or only the baseline count line (Task 0 Step 4)
```

- [ ] **Step 3: Mermaid parse check** for the 4 edited diagrams. Run on Windows, where Node works (the WSL `node_modules` is unreliable, AGENT.md):

```powershell
Set-Location C:\Users\DangT\Documents\GitHub\hc-p4
npx -y @mermaid-js/mermaid-cli@11 -i docs/architecture/pipelines.md -o $env:TEMP\p4-pipelines.md
if ($LASTEXITCODE -ne 0) { Write-Error "mermaid parse failed: docs/architecture/pipelines.md"; exit $LASTEXITCODE }
npx -y @mermaid-js/mermaid-cli@11 -i docs/architecture/README.md -o $env:TEMP\p4-readme.md
if ($LASTEXITCODE -ne 0) { Write-Error "mermaid parse failed: docs/architecture/README.md"; exit $LASTEXITCODE }
npx -y @mermaid-js/mermaid-cli@11 -i docs/architecture/backend.md -o $env:TEMP\p4-backend.md
if ($LASTEXITCODE -ne 0) { Write-Error "mermaid parse failed: docs/architecture/backend.md"; exit $LASTEXITCODE }
npx -y @mermaid-js/mermaid-cli@11 -i docs/architecture/ci-and-quality-gates.md -o $env:TEMP\p4-ci.md
if ($LASTEXITCODE -ne 0) { Write-Error "mermaid parse failed: docs/architecture/ci-and-quality-gates.md"; exit $LASTEXITCODE }
```

Expected: exit 0 with one SVG per diagram. If `npx` cannot fetch (offline), write `UNMEASURED: mermaid parse` in §15, paste each edited block into the GitHub PR preview, and record what it rendered.

- [ ] **Step 4: Docs gates on the clean worktree (§11).** Regenerate the index here only: this worktree has no owner edits.

```bash
git status --short                     # only this PR's files
python3 scripts/generate_docs_index.py && python3 scripts/docs_lint.py --link-graph
python3 scripts/docs_lint.py            # "Docs lint passed."
python3 scripts/generate_docs_index.py --check; echo "index=$?"   # index=0
```

- [ ] **Step 5: Baseline line.** Only if Task 0 Step 4 found a mismatch: edit only the collected figure in `CLAUDE.md`/`AGENT.md` to `START_COLLECTED`, naming the interpreter. Leave every pass-count sentence ("… pass in CI", "… without an embedding model") unchanged unless a pass count was measured in a named environment (interpreter + embedding model present/absent); otherwise flag it in the PR. Never write a collected number into a pass-count slot.

- [ ] **Step 6: End measurement.** Run Task 0 Step 3 again. Acceptance: `collected == START_COLLECTED` (P4 adds no tests), and failures ⊆ `START_FAILURES`. The regenerated index must now let `tests/test_docs_lint.py::test_docs_index_check_passes_on_real_repo` pass if it failed at start. Record both runs in §15.

- [ ] **Step 7: Close-out note** in `docs/features/TASK_LIST.md` Session Notes, with the execution date. Record:
  - the tasks landed;
  - Task 5 dropped (A's rescope) and 5R applied;
  - Task 11's result;
  - Task 4 DONE-by-P2 or edited;
  - Task 15's state;
  - the deferred list (N8, N9, N10, F1–F6) and each trigger.

  Bump `**Last Updated:**`.

- [ ] **Step 8: Commit the close-out and the index**

```bash
set -o pipefail; cd /mnt/c/Users/DangT/Documents/GitHub/hc-p4
PATHS="docs/features/TASK_LIST.md docs/INDEX.md docs/_link_graph.json docs/plans/2026-09-27-P04-doc-drift-sweep-amendment.md"
BASELINE=$(git diff --name-only -- CLAUDE.md AGENT.md)   # non-empty only if Step 5 edited a baseline line
PATHS="$PATHS $BASELINE"
git add $PATHS
git diff --cached --name-only           # exactly $PATHS: the 4 files (the plan = its §15 execution record) plus any file listed in $BASELINE
git commit -m "docs: close out the P4 doc-drift sweep; record execution; regenerate the docs index" -- $PATHS
```

- [ ] **Step 9: Push, open the PR, STOP for the owner's merge.** The PR body follows handoff §6:
  1. start and end measurements;
  2. "no new tests" with the reason;
  3. contract and matrix rows touched (§2), with the status changes proposed but **not** made in the capstone files: SAFE-08 stays partial until N8 and W-10; GATED-07 → resolved by D2 + Task 12;
  4. the explicit file list;
  5. the deferred list;
  6. one next action.

  End the body with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.

## 11. Gates (every P4 commit set)

| Gate | Command | Expected |
|---|---|---|
| Docs lint | `python3 scripts/docs_lint.py` | `Docs lint passed.` |
| Index freshness | `python3 scripts/generate_docs_index.py --check` | exit 0. Regenerate **only** on a clean worktree (C-GATE-4); never in the owner's checkout |
| Relative links outside DOC-007 (`CONTRIBUTING.md`, `skills/**`) | the resolver below | `relative links OK` |
| Harness drift | `python3 scripts/harness_drift_check.py` | `Harness drift check passed.` (evals.md is in its glob) |
| Repo hygiene | `python3 scripts/repo_hygiene_check.py` | exit 0 |
| Import smoke | `cd /mnt/c/Users/DangT/Documents/GitHub/hc-p4/src/backend && ~/venvs/asclexis-311/bin/python -c "import api, modules.agent; from main import app"` | no error |
| Suite | Task 0 Step 3 command | collected = start; failures ⊆ start |

Relative-link resolver (tested 2026-09-27 on the current files: `relative links OK`):

```bash
python3 - CONTRIBUTING.md skills/asclexis-agent/SKILL.md skills/asclexis-evals/SKILL.md skills/asclexis-guardrails/SKILL.md <<'PY'
import re, sys
from pathlib import Path
bad = []
for f in sys.argv[1:]:
    p = Path(f); fence = False
    for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if line.lstrip().startswith("```"):
            fence = not fence; continue
        if fence:
            continue
        for t in re.findall(r"\]\(([^)\s]+)\)", line):
            if re.match(r"(https?:|mailto:|tel:|#)", t):
                continue
            if not (p.parent / t.split("#")[0].split("?")[0]).exists():
                bad.append(f"{f}:{n}: {t}")
print("\n".join(bad) or "relative links OK"); sys.exit(1 if bad else 0)
PY
```

**Measured at planning time (owner's dirty tree, 2026-09-27):** `docs_lint.py` exits 1 with 9 errors:
- 8 DOC-011 orphans: the untracked `docs/plans/2026-09-27-W0*/W10` plans;
- 1 DOC-007: `W10…md` "broken internal link -> target".

This file will add a 10th orphan until the index is regenerated. These are P0-B/orchestrator items, not P4. P4's gates run only on its clean worktree after they are resolved.

## 12. Stop gates (stop and ask)

| # | Condition | Ask |
|---|---|---|
| S1 | A **Before** block does not match exactly once, or a premise in §3 does not reproduce | Write the measured truth in §15; ask before editing |
| S2 | A precondition in Task 0 Step 2 fails, or P2 did not wire the scheduler | orchestrator |
| S3 | Any change would touch `CLAUDE.md` (other than the count line), `docs/compliance/data-privacy.md`, `.serena/project.yml`, an ask-first file, or code beyond §1 item 4 | owner / W-10 |
| S4 | A deferred task's trigger does not hit | do not run it |
| S5 | A citation-vocabulary hit outside the N8 expected list | route to W-5, W-10 or the owner |
| S6 | N9 without a signed Brief 2 | owner |
| S7 | `openwiki/` now holds generated content (G-C2 ran) | rewrite Task 13 to the measured truth; confirm with the owner |
| S8 | Any test failure not in `START_FAILURES`, or a collected-count change | stop, diagnose (`systematic-debugging`) |
| S9 | Index regeneration would run in a tree with uncommitted owner edits | stop |

**Owner-gated items found (unsigned):**

- [ ] **OG-1.** Add `/memories` to `.serena/.gitignore` so regenerated Serena memories are not committed again. D2's text does not cover it. Approve: ______ Date: ______
- [ ] **OG-2.** CSV / JSON / doctor-summary exports include unverified rows, and D4 does not cover exports. P4 only documents this. Decide or accept: ______ Date: ______
- [ ] **OG-4 (Task 3).** Approve removing the dead `VECTOR_STORE_TYPE` lines (the `# Vector store type` comment and `VECTOR_STORE_TYPE=sqlite-vss`) from `config/.env.example`, keeping `EMBEDDING_DIMENSIONS=384`. Approve: ______ Date: ______
- [ ] **OG-5 (Task 10).** Approve docstring-only edits to `src/backend/api/__init__.py` and `src/backend/modules/agent/__init__.py` with the text in Task 10. Approve: ______ Date: ______
- [ ] **OG-6 (Task 14).** Approve deleting `scripts/download_models.py` (the root copy; `src/backend/scripts/download_models.py` stays). Approve: ______ Date: ______
- [ ] **OG-3.** `settings.ollama_base_url` is never passed to `OllamaProvider` (`core/llm/factory.py:51`), but `AGENT.md` Configuration presents `OLLAMA_BASE_URL` as a setting. P4 corrects only the code comment (N7). Wire it or document it as unused: ______ Date: ______

## 13. Commit plan

- One commit per task in P4-core, all on branch `docs/p4-doc-drift`. Deferred tasks go on their own branches.
- Pattern for every commit:

```bash
git add <explicit paths from the task>
git diff --cached --name-only        # must equal exactly those paths
git commit -m "docs(<scope>): <summary>" -- <same explicit paths>
```

- Never `git add -A`, `git add .`, or a directory pathspec, with no exceptions. Task 12 names its seven files explicitly in both `git rm` and `git commit --`.
- Never `git reset` shared work.
- Prefixes: `docs(...)` for all docs tasks and N7 (comment-only). Owner-gated commits use their own prefix: OG-4 `chore(config):`, OG-5 `docs(backend):`, OG-6 `chore(scripts):`. Each OG commit contains only its own files.
- Every commit ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

**Owner sign-offs (unsigned):**
- [ ] P4-core PR merged by owner: ______ Date: ______
- [ ] N9: plan 08 Brief 2 signed (prerequisite): ______ Date: ______
- [ ] Each deferred PR (N8, N10, F1–F6) merged by owner: ______

**Rollback:**
- Before merge (pushed branch or open PR): `gh pr close <n> --delete-branch`, then `git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral worktree remove /mnt/c/Users/DangT/Documents/GitHub/hc-p4`.
- After merge: `git revert <sha>` per commit on a new branch from `origin/main`, in reverse order, through a PR.
- Task 12's revert restores the 7 memory files.
- Task 14's revert (only if OG-6 was signed and executed) restores the root script.
- N7 is comment-only.
- After any revert, regenerate the index on a clean worktree.
- No schema, data or behaviour to unwind.

## 13a. Recurring-failures recheck

| # | Applies | Concrete recheck |
|---|---|---|
| 1 Green suite that could not fail | yes | No new tests. The "test" is the grep list. Each grep was chosen to fail on the old text; confirm each one printed the old line in its Step 1 before editing |
| 2 Fix creates the next bug one layer over | **yes, twice already** | Plan 04's Task 5 and Task 7 texts would have created new false statements after A. Each amended task re-verifies against code first. N1–N6 each name the W-item whose landing makes them stale, and F1–F6 exist for exactly that |
| 3 Figures asserted | yes | Task 1 removes counts from `evals.md`; N6 removes "~1160"; baseline lines change only to a P4-measured count. Numbers in this plan (74, 130/131, 5 imports) are re-measured at execution |
| 4 Environment-dependent results | yes | `test_api_rag_index_002b` wording in Task 1 says "where no embedding model is available", not "locally". Record the interpreter. The Mermaid check runs on Windows |
| 5 Gates in a contaminated tree | yes | All gates run in `../hc-p4`. The owner's checkout currently fails docs_lint on untracked W-plans (§11) |
| 6 Documented commands nobody ran | yes | Every command a P4 edit quotes (`python -m pytest …`, `scripts/download_models.py` backend path) is run in Task 0/16. The FAQ's UI labels were grepped from source (Task 7 Step 1) |
| 7 SQL three-valued logic | no | No SQL |
| 8 Stale guidance reads as authority | **yes, the whole phase** | Overview §12 itself undercounts (3 vs 5 imports) and names the wrong phase; the code wins over it too (§14) |

## 14. Findings for the orchestrator (facts found wrong, with evidence)

1. `architecture-overview.md:185` (§12 row 6) lists 3 `core/` → `modules/` imports. There are 5 at main@40f590e: `core/document_crypto.py:65` and `core/llm/llama_cpp_provider.py:122` are missing.
2. `architecture-overview.md:188` says the divergences are fixed in "the doc-drift phase (P3 of the program)". It is P4.
3. `implementation-program.md:195` gives P4 the `data-privacy.md:173-174` wording. The orchestrator ruling moves it to W-10. The program's shared-file order "`docs/compliance/data-privacy.md` (P1 → P4 → G-A1)" is superseded: P4 does not edit that file.
4. Plan 04 Task 5 would regress A's `3bb4d0d` rescope of `INGEST-FHIR-001`. Plan 04 Task 7's FAQ text is false after A (the `RecoveryCodeCard`; `POST /profiles/{id}/recovery-code` "Generate (or replace)"). Plan 04 Task 10's stdlib-only paragraph is false (`modules/agent` imports SQLAlchemy and backend modules).
5. `A@692fdf3 TASK_LIST.md:59,256` dates HC-M23 to 2026-07-30. The code is `15b152c` 2026-07-17, and it first reached main in `f10e70e` 2026-07-24.
6. `B@7b2ff1f AGENT.md:76` says "1269 collected", while B's own commit message measured 1288 (`CLAUDE.md` updated, `AGENT.md` not). P1's conflict resolution must write the merged measured count in both.
7. `docs/architecture/ci-and-quality-gates.md:17,44` was already stale on main: "~1160 passing", and B's `repo_hygiene_check.py` step is missing.
8. `settings.ollama_base_url` is not used to build the provider (`core/llm/factory.py:51`). See OG-3.
9. `pipelines.md:44-45` also mis-states highlights, care-task candidates and medication reconciliation as reading only verified data. They read unreviewed entities and drop rejected ones.
10. `docs/architecture/README.md:94-97` calls the Hugging Face download the "only" outbound connection. The implicit embedding fetch and the opt-in cloud runner also exist.
11. **Ownership (resolved by the orchestrator):** `CLAUDE.md:62` (D11) is never P4's; if W-10's Q1 is unsigned it stays unchanged as an open owner item. The W-10 plan (§1.3, `:52`) still says the row "goes to P4" and needs that text updated.

## 15. Execution record

*(The executor fills this in.)*

| Item | Value |
|---|---|
| Interpreter / OS | |
| Start: collected / failures | |
| End: collected / failures | |
| Task 4 outcome (DONE-by-P2 sha, or edited) | |
| Task 11 outcome | |
| Task 15 outcome | |
| Mermaid parse | |
| Deferred tasks outstanding | |

Related: [plan 04](../../audit/2026-09-25/plans/04-doc-drift-sweep.md) · [program](../capstone-report/implementation-program.md) · [contract](../capstone-report/architecture-engineering-contract.md) · [matrix](../capstone-report/specs-compliance-matrix.md) · [recurring failures](../agentic/recurring-failures.md) · [W-1](2026-09-27-W01-harness-agents-branch-a.md) · [W-3](2026-09-27-W03-verified-only-rag-and-trend-labels.md) · [W-5](2026-09-27-W05-citation-marker-prompt.md) · [W-6](2026-09-27-W06-external-runner-hardening.md) · [W-10](2026-09-27-W10-governance-invariant-amendments.md)
