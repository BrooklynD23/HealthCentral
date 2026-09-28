# P8 Amendment: Gated-Items Decision Packet Under the HIPAA-Aligned Posture (W-9, D10)

**Last Updated:** 2026-09-27
**Owner:** repository owner
**Refresh Trigger:** any change before execution to `docs/capstone-report/owner-decisions-2026-09-27.md` rows D10 or Q6; P1 landing (or failing to land) on `origin/main`; P4's `hipaa-controls.md:169` task starting; any edit to `src/backend/core/{audit,config,database,profile_database}.py`, `src/backend/models/audit.py` or `src/backend/scripts/backup.py`; the W-8 plan changing `src/backend/scripts/download_models.py`.
**Status:** PROPOSED. Not executed. Nothing in this plan is implemented, wired or tested. D10 is **owner-approved** as a design posture (verbatim below). Every brief in the packet stays **owner-gated** and **unsigned**. The audit-retention *implementation* stays owner-gated: Brief 4 proposes options and implements nothing.
**Review status:** 4 Codex rounds; round-4 BLOCKER fixed after the last round, not re-reviewed (owner acceptance required).
**Prerequisites:** P0-B and P1 merged to `origin/main`; the D9 venv `~/venvs/asclexis-311` built. If Task 0's ancestry check fails before P1 lands, that is the intended STOP, not a defect.

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to run this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**What this is.** An amendment to [plan 08](../../audit/2026-09-25/plans/08-gated-items-review-packet.md), not a copy. Read plan 08 **and its 2026-09-27 banner** first. This file says which of its 7 tasks run as written and which change. It re-verifies plan 08's premises on the post-P1 refs (B@7b2ff1f, A@692fdf3) and specifies the changes that D10, N-04, N-15 and F-08 require.

**Goal:** Produce `audit/2026-09-25/gated-items-decision-packet.md`. It holds five unsigned owner briefs: MFA, key rotation, pen-test scope, audit retention, and HC-M11. Brief 4 is designed as if HIPAA applied, never asserts a legal status, and implements nothing. Log the work in `docs/features/TASK_LIST.md` Session Notes.

**Architecture:** This is a DOCS → OWNER phase and changes zero product code. Plan 08's fixed brief template stays. The changes are:
- Brief 4 is rewritten around three retention classes: Security Rule documentation, audit-log rows, and audit data at rest.
- Brief 5 is narrowed to two questions: production-behaviour change (Q5a) and how the NLI model reaches the machine (Q5b). It does not re-ask the build approval.
- Brief 2 gains a stated ordering dependency on P4.
- Two mechanical checks are added: a forbidden-phrase grep and a mandatory-phrase grep, each broken on purpose once.

**Tech Stack:** Markdown, `git`, `grep`/`awk`, `python3 scripts/docs_lint.py`, and the D9 3.11 venv (`~/venvs/asclexis-311/bin/python`). The venv is used for the start/end measurement and the log-sink probe only.

**Spec:** [handoff §5 row W-9](../../audit/2026-09-25/handoff-2026-09-27-execution.md) and [program P8](../capstone-report/implementation-program.md) (`:261-271`).

## Global Constraints

- **Shell blocks:** every block starts with `set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-p8; cd "$WT"` (the worktree path is absolute; it is a sibling of the main checkout). After that single `cd`, paths are relative to `$WT`, and no block does another relative `cd`.
- **Baseline lines:** this phase adds no tests, so `CLAUDE.md`/`AGENT.md` baseline lines are **not** touched. If the end collected count differs from the start count, stop: something other than docs changed.
- **Break-it-on-purpose** steps run on `mktemp` copies of the packet only, never on tracked files.
- **No product code.** `git diff --name-only origin/main...HEAD` at the end lists exactly `audit/2026-09-25/gated-items-decision-packet.md` and `docs/features/TASK_LIST.md`.
- **Mandatory phrasing (owner-decisions consequence 5, `:46`):** "designed as if HIPAA applied (owner choice, 2026-09-27)". It appears in the packet header and in Brief 4.
- **Forbidden phrasing (F-08, consequence 5):**
  - "Asclexis is a covered entity";
  - "is HIPAA-compliant";
  - any legal conclusion about HIPAA status, in either direction. This includes "not a covered entity".

  The packet does not reproduce such text even when quoting existing files. It cites them by `path:line` instead (for example, `core/audit.py:4` @B already carries a compliance claim).
- **The six-year rule is scoped** to 45 CFR 164.316(b)(1) documentation, per 164.316(b)(2)(i). It is never described as a general rule for audit-log rows.
- **CFR citations:** quote only text that was read. The quotes in Task 5 were read on 2026-09-27 via the Cornell LII mirror; eCFR and HHS were not re-read. Any other citation carries "citation to verify by legal/owner".
- **Ask-first surfaces stay read-only** (CLAUDE.md §1): `modules/interpret_safety.py`, `modules/redaction.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`, and anything auth or encryption. That includes `core/auth.py`, `core/security.py`, `core/profile_database.py`, `core/document_crypto.py`, `core/database.py` (master engine; any encryption option lands here) and the auth hunks of `api/profiles.py`. Briefs whose options would touch them are **briefs only, no code** (item 4 of the W-9 prompt).
- **Tracker honesty:** `feature_list.json` is untouched. HC-M11 stays `pending` (not built). Its build approval is on record and is cited, not re-asked.
- **Agents never record an approval** (program ground rule 1). Every sign-off line in the packet is left unsigned.
- **Every `path:line` in the packet is labelled with its ref** (`@B7b2ff1f`, `@A692fdf3`, `@main40f590e`, or `@start<sha>` once re-verified on the start tree). The executor re-verifies every line on the start tree, because P2, P5, P6 and P7 may have moved lines between P1 and this phase.
- **Explicit pathspecs only** (C-GATE-3). Plan 08's `git commit -am` steps (Tasks 2–6 Step 5, and Task 6 Step 4) are **replaced** by path-scoped commits. `-a` sweeps any other tracked edit in the worktree.

## Review Focus

Failure modes no grep in this plan fully catches. Each one is pinned by a named step.

1. **Paraphrased legal conclusions** ("Asclexis falls under HIPAA", "the app must keep logs for six years") that slip past the regex. Pinned by Task 7 Step 4, the human-read checklist item C3.
2. **A reader taking the D10 posture as overriding the 2026-07-27 purge-on-erase decision.** Pinned by Task 5 Step 5, which puts the conflict in the decision question itself.
3. **Brief 4 quietly asserting a log file exists** (N-15). Pinned by Task 5 Step 1: the runtime probe output is pasted into the brief.
4. **Brief 5 re-asking the build approval, or treating D8 as covering the NLI model.** Pinned by Task 6 Step 3: exactly two questions (Q5a production behaviour, Q5b NLI-model distribution), and D8 is stated to cover the embedding model only.
5. **P4 editing `hipaa-controls.md:169` before Brief 2 is signed.** Pinned by Task 3 Step 3 (dependency sentence) and the Stop gates.

## Approval scope

**D10** ([owner-decisions-2026-09-27.md](../capstone-report/owner-decisions-2026-09-27.md) `:24`, "Treat as HIPAA-aligned", not the recommended option), verbatim:

> "Design retention/controls as if HIPAA applied (6-year Security Rule documentation, etc.) regardless of legal status."

Consequence 5 (`:46`), verbatim:

> "**D10 is a design posture, not a legal conclusion.** Documents must say "designed as if HIPAA applied (owner choice, 2026-09-27)". They must never say "Asclexis is a covered entity" or "is HIPAA-compliant"."

**Earlier records still in force** (same file, `:35`, `:38`):

> "HC-M11 approved behind a default-off flag only | branch A §14 d2 | G-C5; production scoring change still gated"
> "MFA, key rotation, pen test, audit retention: prepare only | audit §21 Q6 | P8 briefs; D10 now frames brief 4"

**HC-M11 record** (`docs/plans/2026-09-08-backlog-closure-plan.md:403` @A692fdf3, §14 row 2, commit `fe31e78`, 2026-09-08), verbatim:

> "| 2 | `HC-M11` approval (§12) | **Approved, scheduled after band A** | Building the cross-encoder behind a flag that defaults off, in two ask-before-touching files. **Not** changing production scoring behaviour, thresholds, or anything else in those files. Its model-distribution prerequisite is still unbuilt. |"

**D10 does NOT license** (each item is out of scope here, or owner-gated if wanted):

1. Implementing any retention mechanism: purge job, archive, window setting or migration. Brief 4 proposes. A signed Brief 4 still needs its own `writing-plans` plan.
2. Asserting or denying HIPAA applicability, or writing any legal conclusion (F-08).
3. Encrypting the master DB, moving audit rows into vaults, or editing `core/database.py`, `core/audit.py`, `models/audit.py` or `scripts/backup.py`.
4. Changing the 2026-07-27 purge-on-erase decision (`docs/compliance/data-privacy.md:144-156` @A692fdf3). Brief 4 may *ask*. It may not assume.
5. Editing `docs/compliance/hipaa-controls.md` or `docs/compliance/data-privacy.md`. P4, W-10 and G-A1 own those. The packet may propose wording for them.
6. Editing code comments that carry compliance claims (`core/audit.py:4,215`, `models/audit.py:4,24`, `migrations/master/env.py:6`, `migrations/master/versions/001_initial_schema.py:9`, all @B7b2ff1f). Flag them only.
7. Any edit to `feature_list.json` (HC-M11 row or new rows).
8. Fixing the debug SQL-echo finding (F-P8-3 below). Report it; do not fix it in this phase.

## Traceability

| ID | Where | Quoted (grep-verified 2026-09-27) |
|---|---|---|
| C-AUDIT-2 | [contract](../capstone-report/architecture-engineering-contract.md) `:331-337` | "**C-AUDIT-2 · OWNER-GATED.** … An audit-retention window or cap for `audit_logs` (plus any log sink the owner configures; no product code configures a file handler today, so the "`logs/asclexis.log` echo" in plan 08 is UNVERIFIED). HIPAA applicability is conditional on the operator and contracts and must not be asserted." |
| C-KEY-3 | same `:103` | "**C-KEY-3 · OWNER-GATED.** … DEK rotation … and MFA / step-up re-auth." |
| C-GATE-1 / C-GATE-3 / C-GATE-4 | same `:340`, `:360`, `:367` | measured counts with command; explicit pathspecs + `git diff --cached --name-only`; `docs_lint.py` passes |
| AUD-03 | [matrix](../capstone-report/specs-compliance-matrix.md) `:107` | "Audit retention policy … none (retention is unbounded) … **owner-gated** (HIPAA status conditional; legal review)" |
| AUD-04 | same `:108` | "Audit data is protected at rest … master DB is **unencrypted** (`core/config.py:180-184`); audit helpers also log each row at INFO (`core/audit.py:254-261`); plan 08's "`logs/asclexis.log`" file sink is **UNVERIFIED**" |
| KEY-05, KEY-06 | same `:62`, `:63` | DEK rotation **gap**, doc overstates; MFA **owner-gated** |
| PRIV-06 | same `:89` | "No PHI in logs or audit rows … **partial**" (F-P8-3 adds evidence) |
| GATED-01…05 | same `:151-155` | the five packet items; GATED-05 "approved for build behind a default-off flag" |
| P8 | [program](../capstone-report/implementation-program.md) `:261-271` | owned files; stop gates "No legal status asserted (F-08)", "six-year rule is scoped to 45 CFR 164.316 documentation", "HC-M11's existing flag-only approval is cited, not re-asked" |
| P4 dependency | same `:196` | "**Added:** `hipaa-controls.md:169` ("key rotation") wording, after plan 08 brief 2 is signed." |
| G-C5 | same `:292` | "HC-M11 cross-encoder behind a default-off flag \| P8 brief 5; P1" |
| W-9 | [handoff §5](../../audit/2026-09-25/handoff-2026-09-27-execution.md) `:146` | "Plan 08 brief 4 designs retention as if HIPAA applied … C-AUDIT-2 / AUD-03, AUD-04 \| docs only: packet review checklist \| brief signed by the owner" |
| F-08 | [review follow-up](../../audit/2026-09-25/review/2026-09-27-followup.md) `:46` | "asserted "not a HIPAA covered entity" … scoped to Security Rule documentation" |

Line numbers in the matrix and contract cite main. The post-P1 equivalents are in the premise table below.

## Files

**Create**
- `audit/2026-09-25/gated-items-decision-packet.md`: the packet. Its path sits outside `docs/`, so the docs_lint header and index rules do not apply.

**Modify**
- `docs/features/TASK_LIST.md`: one new entry at the top of `## Session Notes` (`:153` @A692fdf3; entries are newest first), plus the `**Last Updated:**` line (`:4` @A692fdf3). This is a CANONICAL doc (`scripts/docs_lint.py:38-42`), so DOC-004 requires `**Owner:**` and `**Refresh Trigger:**` to stay.

**Read-only (evidence only)**
- Ask-first: `src/backend/core/{auth,security,profile_database,document_crypto,database}.py`, `src/backend/api/profiles.py`, `src/backend/modules/{faithfulness,verifier_agent}.py`.
- Other: `src/backend/core/{audit,config}.py`, `src/backend/models/audit.py`, `src/backend/scripts/{backup,download_models}.py`, `src/backend/main.py`, `src/backend/security/*.py`, `scripts/security_gate.py`, `.github/workflows/ci.yml`, `src/backend/alembic.ini`, `src/backend/migrations/master/env.py`, `docs/compliance/{hipaa-controls,data-privacy}.md`, `docs/plans/2026-09-08-backlog-closure-plan.md`, `feature_list.json`, `dev.ps1`.

**Shared-file ordering**
- `docs/features/TASK_LIST.md` is appended by most phases' Definition of Done. Edit it **only in Task 7**, on a fresh `origin/main`. If another phase's open PR also edits it, rebase after that PR merges. Never edit it concurrently (program, "Shared files are ordered…", `:69`).
- `docs/compliance/hipaa-controls.md`: P4 edits `:169` **only after Brief 2 is signed**. P8 must therefore reach owner sign-off on Brief 2 **before** P4's `:169` task. This conflicts with the handoff §3 order (`:96`, "… P7 reset → P8 packet"), which puts P8 after P4. The resolution needs the orchestrator/owner: either run P8 (at least Brief 2) right after P1, as the program graph allows (`:49`, "P1 --> P8"), or have P4 skip its `:169` task and leave it open. Sign-off line S-2 below.
- `docs/compliance/data-privacy.md` (P1 → P4 → W-10 → G-A1) is read-only here. Brief 4 may propose wording for `:33` and `:61` (@A692fdf3) and route it to whichever of those phases is current.

## Dependencies

- **P1 landed** on `origin/main` (both tips are ancestors). This brings the HC-M11 record (A) and the fail-closed security gate (B) to main.
- **P0-B landed** (`audit/2026-09-25/plans/08-gated-items-review-packet.md` is tracked on main).
- **D9** 3.11 venv built. If it is missing: stop (see Stop gates).
- **D10** (the posture), the Q6 record ("prepare only") and the §14 d2 record (HC-M11 build).
- **W-8** is *context* for Brief 5 only, not a blocker. The owner settled D8's delivery mechanism on 2026-09-27 (owner decision **D8-delivery**, "Script + offline load"), verbatim: "Interim: `src/backend/scripts/download_models.py` fetches it once into a local models dir; runtime loads that path with HF offline and fails closed if absent. Installer bundles it later (G-C4). No weights in git." If that record is not yet in `owner-decisions-2026-09-27.md` on the start tree, cite it as "owner-recorded 2026-09-27 (D8-delivery), pending entry in owner-decisions". The W-8 plan implements that path. **D8 and D8-delivery cover the embedding model only.** They do not cover HC-M11's NLI cross-encoder. How that model reaches the machine is therefore an explicit owner question in Brief 5 (Q5b). W-8's mechanism may be offered there as one option, not as a decision already made.

## Plan 08 premise re-verification at post-P1

Method: `git diff --stat 40f590e 7b2ff1f|692fdf3 -- <evidence files>`.
- **Branch B** touches 4 of plan 08's evidence files: `core/audit.py`, `core/config.py`, `scripts/download_models.py`, `scripts/security_gate.py` (plus `ci.yml`).
- **Branch A** touches 2: `docs/features/TASK_LIST.md`, `docs/compliance/data-privacy.md` (plus `api/documents.py`, which is not plan-08 evidence).
- Every other anchor is byte-identical on main, A and B. Main line numbers therefore equal post-P1 line numbers, as of P1 only.

| # | Plan 08 premise (task) | Post-P1 finding | Action |
|---|---|---|---|
| R1 | `core/audit.py:254-261` echoes each row to the logger (T5) | Moved to `:257-264` @B7b2ff1f (B added 3 allowlist lines at `:63-65`). Content unchanged | Cite @B lines |
| R2 | That echo lands in `logs/asclexis.log` (T5, N-15) | **Not supported.** No product code creates a file handler. `log_file_path` (`core/config.py:124` @B) is used only to `mkdir` the directory (`core/database.py:87-88` @B). `alembic.ini` `[logger_root] level = WARN` with a stderr handler is applied in-process by `migrations/master/env.py:38` @B. `dev.ps1:718-722` @B does not redirect backend output. **Measured** (main@40f590e; logging code identical at B): see F-P8-2 | Task 5 Step 1 re-measures on the start tree; Brief 4 cites the output |
| R3 | Master DB unencrypted, `core/config.py:180-184` (matrix AUD-04) | `database_url` is at `:179-184` @B7b2ff1f (`:180-185` @main40f590e; B removed one line at `:89`). The master engine is plain `sqlite+aiosqlite` | Cite @B |
| R4 | `config.py:79,125-126` (T5) | `audit_security_events_to_db` `:79` @B. `log_file_path` `:124` @B. `audit_log_enabled` `:125` @B, which is **never read** (`git grep audit_log_enabled 7b2ff1f -- src/backend` → config only). `log_level` `:123` @B is also never read | Cite; state that both settings are inert |
| R5 | Option C "archive-into-backup … audit history lands inside the encrypted artifact, off the master DB" (T5 Step 3) | **Wrong.** Backups already copy the master DB (`scripts/backup.py:203-205` @main=B), scoped to the profile's `audit_logs` rows (`:243-290`). That copy is a **plaintext** SQLite file; only `vault.db` is SQLCipher. Backups prune at 30 days by default (`:658-673`) and are swept on profile delete (`api/profiles.py:890-900`) | Drop option C as written; see Task 5 |
| R6 | `api/profiles.py:909`, `:935` purge + tombstone (T5) | Unchanged @B/A. Governing owner decision (2026-07-27, `data-privacy.md:144-156` @A692fdf3): "The alternative considered and rejected was retaining the full audit trail for HIPAA-style accountability" | Brief 4 must surface the tension with D10 |
| R7 | Plan 08 T5 Step 2 legal framing | Already corrected by the 2026-09-27 banner (F-08). D10 now adds the posture sentence | Task 5 Step 3 |
| R8 | `hipaa-controls.md:168-171` (T2, T3, T4) | Unchanged at A/B: `:168` MFA "Planned for server mode", `:169` "Manual via password change", `:171` "Scheduled for post-launch" | Cite @main=post-P1 |
| R9 | `TASK_LIST.md` HIPAA note "~line 549" (global) | `:692` @A692fdf3 (`:549` @main). Session Notes heading `:153` @A | Cite @A |
| R10 | Security gate fails open "on main (P1 — fix on unmerged branch)" (T4) | Stale after P1. `scripts/security_gate.py:58,84` @B catch `FileNotFoundError`/`JSONDecodeError` and treat them as gate failure (docstring `:49` "exit 2") | Brief 3 lists it as a **verify fail-closed** row, not a known open hole |
| R11 | `/export/questions` unredacted `source_quote` "(quote-leak fix on unmerged branch1)" (T4) | A's P1 fix `45ac889` clears care-task quotes on document delete. It does **not** redact `/export/questions`: `api/export.py:115,126` @main is unchanged by A/B | Keep as an open surface; cross-reference W-2 O-4 |
| R12 | HC-M11 "gated" (T6) | Approved for build behind a default-off flag: `backlog-closure-plan.md:359-382` (§12) and `:403` (§14 d2) @A692fdf3, commit `fe31e78`. On main after P1 | Task 6 rewritten |
| R13 | `download_models.py` is GGUF-only (T6) | Still true @B7b2ff1f. The new `verify` subcommand filters `.gguf` (`:223-246`) | Cite @B; note W-8 |
| R14 | Faithfulness/verifier anchors (T6) | Unchanged: `faithfulness.py:95-121,134,191` and `verifier_agent.py:88,223,304`. Config `:145-151` @B (`:146-152` @main). `modules/agent/guardrails/guard.py:27,32` @B imports only `FaithfulnessConfig` (the threshold), and `modules/agent/eval/scorer.py` @B has no faithfulness/verifier reference | Cite @B; answers plan 08 T6 gap (b) provisionally, and the executor re-checks |
| R15 | Auth/key anchors (T2, T3): `core/auth.py:98,133,163,361,405`, `core/security.py:38-39,86-127`, `profile_database.py:153,183-192,342-349`, `api/profiles.py:535,727-728,773,1072`, `tests/test_profile_recovery.py:210` | Spot-checked on main (= A = B for these files). All present. `change_password` def is `:1072` (plan says `:1071`, the decorator line) | Re-verify on the start tree: P2 edits `core/auth.py:361-419`; P5 edits `api/profiles.py` and `models/audit.py:62`; P6 edits `profile_database.py`; P7 edits `api/profiles.py` |

**Corrections for the orchestrator (found while re-verifying):**
- **F-P8-1:** plan 08 option C premise is wrong (R5).
- **F-P8-2:** the log-file premise is refuted in the default configuration (R2). Measured 2026-09-27 with `/mnt/c/Python313/python.exe` 3.13.7 on main@40f590e, `TestClient` lifespan, profile create, temp cwd:
  ```
  core.audit INFO enabled: False
  AUDIT: records reaching core.audit handlers: 0
  root level: WARNING root handlers: ['StreamHandler']
  FileHandlers: []
  logs/asclexis.log exists: False
  ```
  `data-privacy.md:33` @A692fdf3 ("Audit logs | Master DB + log file") therefore overstates. Route the fix to P4 or W-10.
- **F-P8-3 (security, new):** in the default development config (`debug=True`, `core/config.py:28` @B), both engines set `echo=settings.debug`: `core/database.py:46` and `core/profile_database.py:308` @B. SQLAlchemy then logs every statement **with bound parameters** to stderr. Same probe:
  ```
  sqlalchemy.engine echo records: 7 | INSERT INTO audit_logs echoed: 1
  display name echoed in SQL log: True
  ```
  Profile-vault writes use the same flag, so vault row values are echoed too (static reading; not measured). Production forces `debug` off (`:155-156` @B). This is a PRIV-06 gap, outside P8 scope (item 8 of "Does NOT license"). `core/profile_database.py` is encryption-adjacent (ask-first). Recommend a separate owner-gated fix and a `security-reviewer` pass.

## Task disposition (plan 08's 7 tasks)

| Plan 08 task | Disposition | What changes |
|---|---|---|
| 1 Scaffold | **Changed** (small) | Header adds the D10 sentence and an "unsigned" rule. The ledger gains rows 4a–4c. Runs inside the Task 0 worktree |
| 2 Brief 1 MFA | **Runs as written**, plus deltas | Ask-first banner. Ref labels (R15). Path-scoped commit |
| 3 Brief 2 Key rotation | **Changed** | P4 dependency sentence. Proposed `hipaa-controls.md:169` wording per option. Backup-master fact (R5). Ask-first banner |
| 4 Brief 3 Pen test | **Runs as written**, plus deltas | R10 and R11 corrections. Path-scoped commit |
| 5 Brief 4 Audit retention | **Rewritten** | HIPAA-aligned design (three classes). Runtime probe. CFR quotes. Conflict with the 2026-07-27 purge decision. Options only |
| 6 Brief 5 HC-M11 | **Changed** | Cites the A record; two questions: production behaviour (Q5a) and NLI-model distribution (Q5b) |
| 7 Assemble | **Changed** | Forbidden/mandatory-phrase greps with break-it steps; the W-9 review checklist; TASK_LIST at the A location; start/end measurement; PR and stop |

---

### Task 0: Worktree, post-P1 proof, start measurement

**Files:** none modified.

- [ ] **Step 1: Create the phase worktree** (from the main checkout):

```bash
set -o pipefail
MAIN=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-p8
git -C "$MAIN" fetch origin && git -C "$MAIN" worktree add "$WT" -b docs/p8-gated-packet-hipaa-aligned origin/main && cd "$WT" && pwd
```

- [ ] **Step 2: Prove the tree is post-P1 and post-P0-B**

```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-p8; cd "$WT"
git merge-base --is-ancestor 7b2ff1f HEAD && git merge-base --is-ancestor 692fdf3 HEAD && echo post-P1-ok
git ls-files --error-unmatch audit/2026-09-25/plans/08-gated-items-review-packet.md docs/capstone-report/owner-decisions-2026-09-27.md && echo package-tracked-ok
test ! -e audit/2026-09-25/gated-items-decision-packet.md && echo packet-absent-ok
git grep -n "Approved, scheduled after band A" -- docs/plans/2026-09-08-backlog-closure-plan.md
```

Expected: `post-P1-ok`, `package-tracked-ok`, `packet-absent-ok`, and one hit at `:403` (or its moved line). Anything else: **STOP**.

- [ ] **Step 3: Record the interpreter and backend baseline** (docs-only phase; recorded per program ground rule 2):

```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-p8; OUT=/tmp/hc-p8-measure; mkdir -p "$OUT"
test -x ~/venvs/asclexis-311/bin/python || { echo "D9 venv missing - STOP"; exit 1; }
~/venvs/asclexis-311/bin/python --version
cd "$WT/src/backend"
~/venvs/asclexis-311/bin/python -m pytest tests/ --collect-only -q -p no:cacheprovider | tail -1
~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q -rfE > "$OUT/start-run.txt" 2>&1; echo "pytest-exit=$?"
tail -1 "$OUT/start-run.txt"
grep -E '^(FAILED|ERROR) ' "$OUT/start-run.txt" | sed 's/ - .*//' | sort > "$OUT/start-failures.txt" || true; wc -l < "$OUT/start-failures.txt"
```

Record: Python version, `N tests collected`, the summary line, and the contents of `start-failures.txt` (names).

- [ ] **Step 3b: Baseline-line consistency gate (P1's job; checked here, never fixed here).** At B@7b2ff1f the two files disagree: `CLAUDE.md:30` says "**1288 backend tests collected.**" and `AGENT.md:76` says "(1269 collected; …)". P1 must reconcile them.

```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-p8; cd "$WT"
grep -nE "Baseline: \*\*[0-9]+ backend tests collected" CLAUDE.md
grep -nE "\([0-9]+ collected" AGENT.md
C=$(grep -oE "Baseline: \*\*[0-9]+" CLAUDE.md | grep -oE "[0-9]+"); A=$(grep -oE "\([0-9]+ collected" AGENT.md | grep -oE "[0-9]+")
echo "CLAUDE=$C AGENT=$A"
```

Expected: exactly one number from each file, `C == A`, and both equal the `N tests collected` from Step 3. If the numbers disagree with each other, or with Step 3, or a grep finds no line: **STOP** and report "baseline lines not reconciled by P1" with the three numbers. This phase does not edit `CLAUDE.md`/`AGENT.md` (Global Constraints). A non-zero `pytest-exit` is expected when the start tree has failures; the names are the baseline. No number is carried from another ref.

- [ ] **Step 4: Record the docs gates**

```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-p8; cd "$WT"
python3 scripts/docs_lint.py; echo "lint-exit=$?"
python3 scripts/generate_docs_index.py --check; echo "index-exit=$?"
```

Record both exit codes. If either is non-zero on the start tree, record it as a start failure. It is not this phase's to fix.

### Task 1: Scaffold the packet (plan 08 Task 1, amended)

**Files:** Create `audit/2026-09-25/gated-items-decision-packet.md`.

**Interfaces:** Produces the anchors `## Brief 1 — MFA`, `## Brief 2 — Key Rotation`, `## Brief 3 — Penetration-Test Scope`, `## Brief 4 — Audit Retention`, `## Brief 5 — HC-M11 NLI Faithfulness`, `## Sign-off ledger`. Tasks 5 and 7 extract sections with `awk` on `^## `, so briefs must not use other `## ` headings. Use `###` inside a brief.

- [ ] **Step 1: Write the skeleton.** Use plan 08 Task 1 Step 1's block, with these changes:
  - After the first blockquote, add:
    ```markdown
    > **Posture (D10):** retention and controls in this packet are designed as if HIPAA applied (owner choice, 2026-09-27). This is a design posture, not a statement about legal status. Whether any rule applies depends on who operates Asclexis and under what contracts, which is for owner/legal review.
    > **Nothing here is signed.** An agent prepared every brief. Only the owner fills a decision box.
    ```
  - Replace the ledger rows with the following. Every box is unticked, and the Date and Notes cells stay empty:

    | # | Item | Decision | Date | Notes |
    |---|---|---|---|---|
    | 1 | MFA | ☐ approve ☐ reject ☐ defer | | |
    | 2 | Key rotation (gates P4 `hipaa-controls.md:169`) | ☐ approve ☐ reject ☐ defer | | |
    | 3 | Pen-test scope | ☐ approve ☐ reject ☐ defer | | |
    | 4a | Security Rule documentation retention | ☐ approve ☐ reject ☐ defer | | |
    | 4b | Audit-row window + purge-on-erase | ☐ approve ☐ reject ☐ defer | | |
    | 4c | Audit data at rest | ☐ approve ☐ reject ☐ defer | | |
    | 5a | HC-M11 production-behaviour change | ☐ approve ☐ reject ☐ defer | | |
    | 5b | HC-M11 NLI-model distribution | ☐ approve ☐ reject ☐ defer | | |

- [ ] **Step 2: Verify:** `grep -c "^## " audit/2026-09-25/gated-items-decision-packet.md` → `7` (How to read, 5 briefs, ledger; the `# ` title is not counted). Also `grep -c "☐ approve" …` → `8`.
- [ ] **Step 3: Commit**

```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-p8; cd "$WT"
git add audit/2026-09-25/gated-items-decision-packet.md && git diff --cached --name-only
git commit -m "docs: scaffold gated-items owner decision packet (D10 posture)" -- audit/2026-09-25/gated-items-decision-packet.md
```

Expected: `--name-only` prints exactly that one path.

### Task 2: Brief 1, MFA (plan 08 Task 2, runs as written, plus deltas)

**Files:** Modify the packet (`## Brief 1 — MFA`).

- [ ] **Step 1:** Run plan 08 Task 2 Steps 1–4 as written, with these deltas:
  - Label every anchor with its ref (R15).
  - If P2 has landed, `core/auth.py:361-419` holds the D6 hooks, so cite the moved lines.
  - Open the brief with: "**Ask-first surface:** every option except A touches `core/auth.py` (CLAUDE.md §1). This brief proposes; it changes no code."
- [ ] **Step 2: Commit.** `git add audit/2026-09-25/gated-items-decision-packet.md && git diff --cached --name-only && git commit -m "docs: MFA decision brief" -- audit/2026-09-25/gated-items-decision-packet.md`

### Task 3: Brief 2, key rotation (plan 08 Task 3, changed)

**Files:** Modify the packet (`## Brief 2 — Key Rotation`).

- [ ] **Step 1:** Run plan 08 Task 3 Steps 1–2 as written. Record the backup file list from `scripts/backup.py:189-215`: master copy (plaintext, profile-scoped) + `vaults/<id>/*` (sealed keys, SQLCipher vault). State: "old backups keep the old DEK's sealed copies until pruned (default 30 days, `scripts/backup.py:658-673` @main) or swept on profile delete".
- [ ] **Step 2:** Draft the brief per plan 08 Task 3 Step 3, and open it with: "**Ask-first surface:** options B and C touch `core/profile_database.py`, `core/security.py`, `core/document_crypto.py` and `api/profiles.py` (encryption). Brief only; no code."
- [ ] **Step 3: Add the ordering dependency and the proposed P4 wording** as a `### Downstream: hipaa-controls.md:169` subsection:

```markdown
### Downstream: hipaa-controls.md:169
This brief must be signed before P4 edits `docs/compliance/hipaa-controls.md:169` @main40f590e (unchanged by A/B; re-verify @start)
(program P4, "after plan 08 brief 2 is signed"). P4 applies the row matching the signed option:
- If A (docs only) or reject/defer: `| Key rotation | Medium | Not implemented. A password change re-seals the existing data key under the new password; the database and document key itself does not change. |`
- If B or C approved: `| Key rotation | Medium | Owner-approved <date>, not yet implemented (plan: <link>). Until it ships, a password change re-seals the existing data key only. |`
- If D only: A's row, plus `| Session-secret rotation | Low | <as implemented> |`
```

- [ ] **Step 4: Self-check** per plan 08 Task 3 Step 4, plus: `awk '/^## Brief 2/{f=1;next} /^## /{f=0} f' audit/2026-09-25/gated-items-decision-packet.md | grep -c "must be signed before P4"` → `1`.
- [ ] **Step 5: Commit** (path-scoped, as in Task 2): `docs: key-rotation decision brief`.

### Task 4: Brief 3, pen-test scope (plan 08 Task 4, runs as written, plus deltas)

**Files:** Modify the packet (`## Brief 3 — Penetration-Test Scope`).

- [ ] **Step 1:** Run plan 08 Task 4 Steps 1–4 as written, with these deltas:
  - **R10:** the security gate is a "verify fail-closed" row. Evidence command: `python3 scripts/security_gate.py --bandit /nonexistent.json --pip-audit /nonexistent.json; echo $?` → non-zero (program P1 step 7). Run it and paste the output.
  - **R11:** `/export/questions` `source_quote` stays an open surface; cross-reference W-2 O-4.
  - Add F-P8-3 (debug SQL echo) as a surface row: "debug-mode stderr carries bound parameters".
- [ ] **Step 2: Commit** (path-scoped): `docs: pen-test scope decision brief`.

### Task 5: Brief 4, audit retention designed as if HIPAA applied (plan 08 Task 5, rewritten)

**Files:** Modify the packet (`## Brief 4 — Audit Retention`).

- [ ] **Step 1: Re-measure the log sinks on the start tree** (N-15, AUD-04). The probe is read-only against the repo and writes only to a temp cwd outside the worktree.

```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-p8; P="$(mktemp -d)"; cat > "$P/probe.py" <<'EOF'
import logging, os, sys, pathlib
sys.path.insert(0, sys.argv[1]); os.environ.setdefault("DATABASE_ENCRYPTION_REQUIRED", "false")
class C(logging.Handler):
    def __init__(self): super().__init__(logging.NOTSET); self.m = []
    def emit(self, r): self.m.append(r.getMessage())
from fastapi.testclient import TestClient
from main import app
from core.config import settings
a, s = C(), C()
with TestClient(app) as c:
    logging.getLogger("core.audit").addHandler(a); logging.getLogger("sqlalchemy.engine").addHandler(s)
    r = c.post("/api/v1/profiles/", json={"display_name": "Probe Person", "password": "ProbePass9!x"})
    root = logging.getLogger()
    print("debug:", settings.debug, "| create status:", r.status_code)
    print("core.audit INFO enabled:", logging.getLogger("core.audit").isEnabledFor(logging.INFO))
    print("AUDIT: records reaching core.audit handlers:", sum("AUDIT:" in m for m in a.m))
    print("root level:", logging.getLevelName(root.level), "root handlers:", [type(h).__name__ for h in root.handlers])
    print("FileHandlers:", [(n, h.baseFilename) for n, l in logging.Logger.manager.loggerDict.items() if isinstance(l, logging.Logger) for h in l.handlers if isinstance(h, logging.FileHandler)] + [("root", h.baseFilename) for h in root.handlers if isinstance(h, logging.FileHandler)])
    print("INSERT INTO audit_logs echoed:", sum("INSERT INTO audit_logs" in m for m in s.m), "| display name echoed:", any("Probe Person" in m for m in s.m))
print("logs/asclexis.log exists:", pathlib.Path("logs/asclexis.log").exists())
EOF
(cd "$P" && ~/venvs/asclexis-311/bin/python -B probe.py "$WT/src/backend" 2>/dev/null); rm -rf "$P"
```

Expected on an unchanged tree (as measured on main@40f590e, Windows Py 3.13.7): `core.audit INFO enabled: False`, `AUDIT: … 0`, `FileHandlers: []`, `logs/asclexis.log exists: False`, `INSERT INTO audit_logs echoed: 1`, `display name echoed: True`. Paste the actual output into the brief with the interpreter and the start SHA.
- If `create status` is not `201`, record it and use only the logging-state lines.
- If a FileHandler **does** appear, the brief cites it (path and config line) and treats it as a retention surface.
- The probe above exercises `TestClient`. Step 1b measures the real `uvicorn` CLI path.

- [ ] **Step 1b: Measure the `uvicorn` CLI path** (same questions, real server, temp cwd, absolute `--app-dir`):

```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-p8; U="$(mktemp -d)"; PORT=8799
cd "$U"
DATABASE_ENCRYPTION_REQUIRED=false ~/venvs/asclexis-311/bin/python -m uvicorn main:app \
  --app-dir "$WT/src/backend" --host 127.0.0.1 --port "$PORT" > "$U/uv.out" 2> "$U/uv.err" &
UVPID=$!
for i in $(seq 1 60); do curl -sf "http://127.0.0.1:$PORT/health" > /dev/null && break; sleep 1; done
curl -s -o /dev/null -w "create=%{http_code}\n" -X POST "http://127.0.0.1:$PORT/api/v1/profiles/" \
  -H 'Content-Type: application/json' -d '{"display_name":"Probe Person","password":"ProbePass9!x"}'
kill "$UVPID"; wait "$UVPID" 2> /dev/null
echo "log file: $(test -e "$U/logs/asclexis.log" && echo present || echo absent)"
echo "AUDIT lines on stderr: $(grep -c 'AUDIT:' "$U/uv.err" || true)"
echo "audit INSERT echoed on stderr: $(grep -c 'INSERT INTO audit_logs' "$U/uv.err" || true)"
echo "display name on stderr: $(grep -c 'Probe Person' "$U/uv.err" || true)"
cd /; rm -rf "$U"
```

Expected (static prediction; this path was not run 2026-09-27): `create=201`, `log file: absent`, `AUDIT lines on stderr: 0`, audit INSERT ≥ 1, display name ≥ 1. If `/health` never answers within 60 s, record "uvicorn probe: server did not start" plus the last 20 lines of `uv.err`, and mark this row UNMEASURED in the brief. Paste the actual output into Brief 4 next to Step 1's.

- [ ] **Step 2: Build the current-state table.** Cite every row with its ref, re-verified on the start tree:

| Anchor (post-P1) | Proves |
|---|---|
| `models/audit.py:20-68` @B (`timestamp` default `:61-62`; P5 converts it) | `audit_logs` sits on the master `Base` |
| `core/config.py:179-184` @B | master URL is plain `sqlite+aiosqlite` (AUD-04) |
| `core/audit.py:23-32` @B | design note: rows in the unencrypted master; "Phase B (encrypting the master DB) is explicitly out of scope and gated" |
| `core/audit.py:36-112` @B | AUDIT-PHI-001 allowlist minimizes content (`audit_rows_purged` at `:100`) |
| `core/audit.py:257-264` @B + Step 1 output | the INFO echo exists in code; measured sinks: say what Step 1 showed |
| `core/database.py:46`, `core/profile_database.py:308`, `core/config.py:28` @B + Step 1 output | debug SQL echo of bound parameters (F-P8-3) |
| `api/profiles.py:890-900,909,935` @B | profile delete sweeps backups, purges rows, writes the anonymized tombstone |
| `scripts/backup.py:203-205,243-290,658-673` @B | backups carry a plaintext, profile-scoped master copy including audit rows; 30-day default prune |
| `ls src/backend/api/` + `git grep -n "AuditLog" -- src/backend/api` | no audit-read route (only `api/profiles.py` references `AuditLog`) → no patient-visible history to lose |
| `docs/compliance/data-privacy.md:33,61,144-156` @A | "Indefinite"; "Master DB + log file"; 2026-07-27 purge decision |
| `docs/compliance/hipaa-controls.md:49-52` @main | doc claims "Structured JSON … correlation IDs" and "append-only". Check each against code and state what code does (recurring-failures #8) |

- [ ] **Step 3: Write the framing paragraph.** It must contain the mandatory sentence verbatim and the following quotes. Do not add any other regulatory text unless read and dated.

```markdown
Audit retention and audit-data protection here are designed as if HIPAA applied (owner choice, 2026-09-27).
This is a design posture, not a statement of legal status; applicability depends on the operator,
its contracts and data flows, which are for owner/legal review.

Regulatory text used (read 2026-09-27 via the Cornell LII mirror of 45 CFR; the official eCFR/HHS
text was not re-read — citation to verify by legal/owner):
- 164.316(b)(1): "(i) Maintain the policies and procedures implemented to comply with this subpart in
  written (which may be electronic) form; and (ii) If an action, activity or assessment is required by
  this subpart to be documented, maintain a written (which may be electronic) record…"
- 164.316(b)(2)(i) Time limit (Required): "Retain the documentation required by paragraph (b)(1) of this
  section for 6 years from the date of its creation or the date when it last was in effect, whichever is later."
- 164.312(b) Audit controls (standard): "Implement hardware, software, and/or procedural mechanisms that
  record and examine activity in information systems that contain or use electronic protected health information."
  The text read states no retention period for the activity records themselves.
- 164.312(a)(2)(iv) Encryption and decryption (Addressable): "Implement a mechanism to encrypt and decrypt
  electronic protected health information."
- 164.308(a)(1)(ii)(D) Information system activity review (Required): "Implement procedures to regularly
  review records of information system activity, such as audit logs, access reports, and security incident
  tracking reports."
```

Then: "The six-year period attaches to the documentation in 164.316(b)(1). It is not, by that text, a period for keeping every audit-log row. Treating rows the same way would be an extra owner choice."

- [ ] **Step 4: Draft the three decision parts.** Each part has an options table (`| Option | Effort | Risk | Value |`), a recommendation, and its own unsigned line.

**4a: Security Rule documentation (six years, under the posture).**
- What counts as documentation: `docs/compliance/*.md`, this packet and its signed ledger, dated owner-decision records, the Session Notes that record them, and any future risk analysis or activity-review record.
- Options:
  - **A.** Git history on the owner's canonical remote is the store. Add a documentation register listing each document and its six-year horizon ("6 years from creation or last in effect"). Docs only. S.
  - **B.** A plus an exported archive (signed tag or release) per year. S.
  - **C.** Do nothing.
- Risk to name: force-push or repo deletion defeats A.
- Recommend A.

**4b: Audit-log rows.**
- State: rows are unbounded today (AUD-03), except for purge-on-erase.
- Options:
  - **A.** Six-year rolling window, chosen to mirror 4a by owner choice and not required by the text above. Purge-on-erase unchanged. S–M.
  - **B.** Shorter window (owner fills in days), as data minimization. S–M.
  - **C.** Unbounded, documented. S.
  - **D.** Revisit the 2026-07-27 purge-on-erase: keep rows after erase for the window.
- Conflict to print in bold: D contradicts the 2026-07-27 decision (`data-privacy.md:150-153` @A, which rejected "retaining the full audit trail for HIPAA-style accountability"). D10 does not by itself reverse it, because D10 licenses design posture and is silent on erase.
- Note: if the owner adopts an activity-review procedure (164.308(a)(1)(ii)(D) text above), the *records of those reviews* fall under 4a, and the rows they summarise do not.
- Recommend A with purge-on-erase kept, and the anonymized tombstone kept as the deletion record.

**4c: Audit data at rest (AUD-04).**
- Options:
  - **A.** Document the current state: plaintext master, minimized rows, the measured sinks from Step 1. S.
  - **B.** Encrypt the master DB (SQLCipher with an install key sealed by DPAPI). L. **Ask-first** (encryption, `core/database.py`), and it must preserve pre-login audit events (failed logins happen before any vault is open).
  - **C.** Move profile-linked rows into each vault. L. **Ask-first.** It breaks pre-unlock events and changes crypto-erase semantics.
  - **D.** Stop plaintext echo surfaces: the `core/audit.py:257-264` echo and debug SQL echo (F-P8-3). S–M.
  - **E.** Encrypt the master copy inside backups. M. **Ask-first** (backup + keys).
- Recommend A now, plus a separate owner decision on D. B, C and E each need their own plan and an explicit ask-first yes.

**Implementation sketch** (recommended options only; prose, no code; plan 08 template item 6):
- 4a: docs-only register.
- 4b: a `modules/audit_retention.py`-style sweep over the master `get_db()` (never `ProfileDbSession`). Delete rows with `timestamp < utcnow() - window` (naive UTC, `core.time.utcnow`), excluding NULL-profile tombstones. Handle the NULL row explicitly (recurring-failures #7). The sweep writes one audit row using the existing `audit_rows_purged` key. HTTP tests via `tests/support/routes.py::route_client` for any new route. A test inserts aged, fresh and NULL-profile rows and asserts which survive. Break it on purpose: flip the comparison and watch the test go red.
- State plainly: **this brief implements nothing; a signed 4b needs its own `writing-plans` plan.**

- [ ] **Step 5: Owner questions** (each ends with `Owner decision: ☐ approve ☐ reject ☐ defer — notes/date: ____`):
  - Q4a: "Approve keeping Security Rule documentation (list above) for 6 years from creation or last in effect, stored as git history plus a register (option A)?"
  - Q4b: "Approve an audit-row window of ☐ 6 years ☐ ____ days ☐ unbounded, **keeping** the 2026-07-27 purge-on-erase (tombstone kept)? If you want rows kept after erase, say so explicitly; that reverses the 2026-07-27 decision."
  - Q4c: "Approve documenting the current at-rest state now (A), and commissioning a plan for D (stop plaintext echo surfaces)? B, C and E would each come back as their own ask-first brief."
- [ ] **Step 6: Self-check.**
  - `awk '/^## Brief 4/{f=1;next} /^## /{f=0} f' audit/2026-09-25/gated-items-decision-packet.md | grep -cF "designed as if HIPAA applied (owner choice, 2026-09-27)"` → ≥ `1`.
  - The same extraction piped to `grep -c "Owner decision: ☐ approve ☐ reject ☐ defer"` → `3`.
  - The same extraction piped to `grep -niE "six[- ]year|6[- ]year|6 years" | grep -viE "164\.316|documentation|owner choice|mirror|window of"` → no output.
- [ ] **Step 7: Commit** (path-scoped): `docs: audit-retention decision brief (designed as if HIPAA applied, D10)`.

### Task 6: Brief 5, HC-M11 (plan 08 Task 6, changed)

**Files:** Modify the packet (`## Brief 5 — HC-M11 NLI Faithfulness`).

- [ ] **Step 1:** Run plan 08 Task 6 Step 1 (anchors + gaps a/b) with R13/R14 refs. Gap (a): `download_models.py` @B is GGUF-only (`:223-246`). D8-delivery ("Script + offline load", 2026-09-27) makes W-8 extend that script for the **embedding model only**; it does not cover the NLI model. State whether W-8 has landed on the start tree (`git log --oneline origin/main -- src/backend/scripts/download_models.py`). Gap (b): `guard.py:27,32` @B reads only the threshold; state what the start tree shows.
- [ ] **Step 2: Replace "Current state / what the owner must approve" with "What is already approved".** Quote `backlog-closure-plan.md:403` @A692fdf3 (commit `fe31e78`) verbatim. Quote `:365-368` (§12 "Read the approval narrowly…") verbatim. Then list what that record already covers:
  - building the scorer behind a default-off flag in `faithfulness.py` and `verifier_agent.py`;
  - that a model-distribution prerequisite "comes first" (`:370-373`). The record names the prerequisite but does **not** choose how the NLI model is distributed. That is Q5b;
  - pinning in `config/model_manifest.json` (`:381-382`).

  Say: "HC-M11's ledger status stays `pending` (not built). That is not the same as unapproved." Keep plan 08's model-choice and cost notes. A model other than the tracker candidate is outside the record, and the brief does not propose one.
- [ ] **Step 3: Exactly two decision questions** (program P8 stop gate "cited, not re-asked"; overlap row `:302`). Neither re-asks the build approval:
  - Q5: "The build behind a default-off flag is already approved (2026-09-08). Separately, approve any **production-behaviour change**: the flag defaulting on, or NLI scores changing production faithfulness outcomes. ☐ not now (keep default off; bring back eval evidence from G-C5) ☐ approve enabling after G-C5 shows `<criterion the owner writes>` ☐ reject. Thresholds are not in scope; 0.6 is never lowered."
  - End Q5a with `Owner decision: ☐ approve ☐ reject ☐ defer — notes/date: ____`. Recommend "not now".
  - Q5b: "How may the NLI cross-encoder reach the machine? D8/D8-delivery covered the embedding model only. ☐ one-time fetch by `src/backend/scripts/download_models.py` into a local models dir, HF offline at runtime, fail closed if absent (W-8's mechanism, extended to this model) ☐ bundled with the installer when one exists (G-C4) ☐ other: ____. Model weights are not committed to git without a separate yes." The options table states, per option: the model (tracker candidate `cross-encoder/nli-deberta-v3-xsmall`), licence (MIT per the `feature_list.json` HC-M11 row; re-verify on the model card at execution; mark UNVERIFIED if it cannot be read), artifact size (UNMEASURED unless downloaded and measured with `du -sh`), the `config/model_manifest.json` pin, and that PHI never leaves (the only network use is the one-time model fetch).
  - End Q5b with `Owner decision: ☐ approve ☐ reject ☐ defer — notes/date: ____`. Recommend the one-time fetch (fewest new mechanisms, matches D8-delivery's pattern). The owner still chooses; D8 does not decide it.
  - Open the brief with the ask-first banner (`faithfulness.py`, `verifier_agent.py`).
- [ ] **Step 4: Self-check.**
  - `awk '/^## Brief 5/{f=1;next} /^## /{f=0} f' audit/2026-09-25/gated-items-decision-packet.md | grep -c "Owner decision:"` → `2`.
  - `… | grep -c "fe31e78"` → ≥ `1`.
  - `… | grep -niE "approve HC-M11 implementation|is unapproved|not approved to build"` → no output.
  - `… | grep -niE "D8[^.]*(covers|approved|licen[cs]es)[^.]*(NLI|cross-encoder|HC-M11)"` → no output (D8 must not be presented as covering the NLI model). Break it once on a `mktemp` copy with the line "D8 covers the NLI cross-encoder." → one hit.
- [ ] **Step 5: Commit** (path-scoped): `docs: HC-M11 brief cites the flag-only approval; asks production behaviour and NLI-model distribution`.

### Task 7: Assemble, mechanical checks, review checklist, log, PR (plan 08 Task 7, changed)

**Files:** Modify the packet (final pass) and `docs/features/TASK_LIST.md`.

- [ ] **Step 1: Completeness and evidence audit.** Run plan 08 Task 7 Steps 1–2 as written. `grep -c "Owner decision:" audit/2026-09-25/gated-items-decision-packet.md` → `8` (1+1+1+3+2).
- [ ] **Step 2: Write the TASK_LIST entry.** Rebase on `origin/main` first (`set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-p8; cd "$WT" && git fetch origin && git rebase origin/main`). Insert directly under `## Session Notes`:

```markdown
### <YYYY-MM-DD> - Gated-items decision packet prepared (P8 / W-9, D10)

Prepared [the gated-items decision packet](../../audit/2026-09-25/gated-items-decision-packet.md): five owner briefs (MFA, key rotation, pen-test scope, audit retention, HC-M11), all **unsigned**. Brief 4 is designed as if HIPAA applied (owner choice, 2026-09-27); it proposes options and implements nothing. Brief 5 cites the 2026-09-08 flag-only HC-M11 approval and asks two things only: production behaviour and how the NLI model is distributed (D8 covers the embedding model only). Brief 2 must be signed before P4 edits `hipaa-controls.md:169`. Findings routed: debug SQL echo prints bound parameters (PRIV-06); no `logs/asclexis.log` sink in the default config.
```

  Set `**Last Updated:**` to the same date. Leave `**Owner:**` and `**Refresh Trigger:**` untouched.
- [ ] **Step 3: Forbidden-phrase check, then break it on purpose** (recurring-failures #1):

```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-p8; cd "$WT"
FORBID='covered entit|business associate|HIPAA[- ]complian|complian(t|ce) with HIPAA|is (fully )?compliant|(meets|satisfies) HIPAA|HIPAA (requires|mandates)|legally (required|obligated)|legal obligation'
PKT=audit/2026-09-25/gated-items-decision-packet.md
grep -niE "$FORBID" "$PKT"; echo "packet-exit=$?"
git diff origin/main -- docs/features/TASK_LIST.md | grep '^+' | grep -v '^+++' | grep -niE "$FORBID"; echo "tasklist-exit=$?"
T="$(mktemp)"; cp "$PKT" "$T"; echo "Asclexis is a covered entity and is HIPAA-compliant." >> "$T"
grep -ciE "$FORBID" "$T"; rm -f "$T"
```

Expected: `packet-exit=1`, `tasklist-exit=1` (no match), then the seeded copy prints `1`. If the seeded copy prints `0`, the regex is broken: fix the regex, never the seed. Mandatory phrase: `grep -cF "designed as if HIPAA applied (owner choice, 2026-09-27)" "$PKT"` → ≥ `2` (header + Brief 4). Break it too: `sed 's/owner choice, 2026-09-27/owner choice/' "$PKT" | grep -cF "designed as if HIPAA applied (owner choice, 2026-09-27)"` → `0`.
- [ ] **Step 4: Packet review checklist (W-9 test case).** Paste this table into the PR description with each cell filled from a command or a read:

| # | Check | How | Pass |
|---|---|---|---|
| C1 | 5 briefs, each with current-state table, options (effort/risk/value), recommendation, owner question, sketch | read + `grep -c "^## Brief"` → 5 | ☐ |
| C2 | Every decision line unsigned; no filled date | block `C2` below → `C2-ok`; ledger Date cells empty (read) | ☐ |
| C3 | No legal conclusion, including paraphrase | Step 3 greps + a human read of Brief 4 framing | ☐ |
| C4 | Mandatory phrase in header and Brief 4 | Step 3 | ☐ |
| C5 | Six-year period tied to 164.316(b)(1) documentation only | Task 5 Step 6 grep | ☐ |
| C6 | Every CFR quote is either dated/sourced or marked "citation to verify by legal/owner" | block `C6` below lists the lines; read each | ☐ |
| C7 | Brief 4 cites C-AUDIT-2, AUD-03, AUD-04; implements nothing | block `C7` below → `C7-ok` | ☐ |
| C8 | Log-sink status is the Step 1 measurement, with interpreter + SHA | read | ☐ |
| C9 | 2026-07-27 purge conflict shown in Q4b | read | ☐ |
| C10 | Brief 5 cites `fe31e78` + path:line; exactly Q5a + Q5b; no text implying D8 covers the NLI model | Task 6 Step 4 | ☐ |
| C11 | Brief 2 states the P4 `:169` dependency | Task 3 Step 4 | ☐ |
| C12 | Ask-first banner on briefs 1, 2, 4 (4c) and 5; zero code in the diff | `git diff --name-only origin/main...HEAD` → exactly 2 files | ☐ |
| C13 | Every `path:line` carries a ref | block `C13` below → `C13-ok` | ☐ |
| C14 | `feature_list.json` untouched | `git diff --quiet origin/main -- feature_list.json && echo unchanged` | ☐ |

Checklist commands (kept out of the table so `|` is never escaped; every `grep -E` uses plain `|` alternation):

```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-p8; cd "$WT"
PKT=audit/2026-09-25/gated-items-decision-packet.md
# C2: no ticked box anywhere
grep -nE '☒|☑|✅|\[x\]' "$PKT" && echo C2-FAIL || echo C2-ok
# C6: every line naming CFR or a 164.x section, for a line-by-line read
grep -nE 'CFR|164\.[0-9]' "$PKT"
# C7: each ID appears at least once inside Brief 4
B4="$(awk '/^## Brief 4/{f=1;next} /^## /{f=0} f' "$PKT")"
ok=1; for id in C-AUDIT-2 AUD-03 AUD-04; do printf '%s\n' "$B4" | grep -qF "$id" || { echo "C7-missing $id"; ok=0; }; done; [ "$ok" = 1 ] && echo C7-ok
# C13: every path:line citation line carries a ref label
grep -nE '\.(py|md|json|ini|yml|ps1):[0-9]' "$PKT" | grep -v '@' && echo C13-FAIL || echo C13-ok
```

Break each once on a `mktemp` copy before trusting it: append `| 1 | MFA | ☒ approve | | |` (C2 must print `C2-FAIL`), a line `` `core/audit.py:257` `` with no `@` (C13 must print `C13-FAIL`), and point C7 at a copy whose Brief 4 lacks `AUD-04` (must print `C7-missing AUD-04`).

- [ ] **Step 5: End measurement and docs gates**

```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-p8; OUT=/tmp/hc-p8-measure
cd "$WT/src/backend"
~/venvs/asclexis-311/bin/python -m pytest tests/ --collect-only -q -p no:cacheprovider | tail -1
~/venvs/asclexis-311/bin/python -m pytest tests/ -p no:cacheprovider -q -rfE > "$OUT/end-run.txt" 2>&1; echo "pytest-exit=$?"
tail -1 "$OUT/end-run.txt"
grep -E '^(FAILED|ERROR) ' "$OUT/end-run.txt" | sed 's/ - .*//' | sort > "$OUT/end-failures.txt" || true
echo "new failures (end minus start):"; comm -13 "$OUT/start-failures.txt" "$OUT/end-failures.txt"
cd "$WT"
python3 scripts/docs_lint.py; echo "lint-exit=$?"
python3 scripts/generate_docs_index.py --check; echo "index-exit=$?"
git diff --name-only origin/main...HEAD
```

Expected:
- collected = start (Task 0 Step 3) + 0;
- `new failures` prints nothing (end failures ⊆ start failures, compared by name);
- `Docs lint passed.` / `lint-exit=0` (DOC-007 resolves the new TASK_LIST link because the packet exists);
- index exit equals its start value. TASK_LIST.md already exists, so no new doc is added under `docs/`;
- exactly the 2 owned paths.

If `new failures` lists anything, stop: a docs-only diff cannot explain it (Stop gates).
- [ ] **Step 6: Re-read `docs/agentic/recurring-failures.md`** and fill in the recheck table below in the PR.
- [ ] **Step 7: Commit, push, PR, STOP**

```bash
set -o pipefail; WT=/mnt/c/Users/DangT/Documents/GitHub/hc-p8; cd "$WT"
git add docs/features/TASK_LIST.md audit/2026-09-25/gated-items-decision-packet.md && git diff --cached --name-only
git commit -m "docs: gated-items owner decision packet - awaiting sign-off (P8/W-9)" -- docs/features/TASK_LIST.md audit/2026-09-25/gated-items-decision-packet.md
git push -u origin docs/p8-gated-packet-hipaa-aligned
```

Open a PR in the handoff §6 format, with the checklist and F-P8-1…3. **Stop.** The owner signs in the packet via their own commit. Agents never tick a box.

## Measured acceptance

| Check | Command | Expected |
|---|---|---|
| Post-P1 tree | Task 0 Step 2 | `post-P1-ok` |
| Tests collected | Task 0 Step 3 vs Task 7 Step 5 | end = start + 0 |
| Failures | Task 0 Step 3 vs Task 7 Step 5 | `comm -13 start-failures end-failures` prints nothing |
| Diff scope | `git diff --name-only origin/main...HEAD` | exactly the 2 owned files |
| Forbidden phrasing | Task 7 Step 3 | exit 1 on packet and TASK_LIST additions; seeded copy → 1 |
| Mandatory phrasing | Task 7 Step 3 | ≥ 2; broken copy → 0 |
| Unsigned | C2 | no ticked box, no date |
| Log sinks | Task 5 Steps 1 and 1b | both outputs pasted into Brief 4 with interpreter and start SHA; if Step 1b's server does not start, that row is recorded UNMEASURED with the `uv.err` tail |
| Docs gates | Task 7 Step 5 | lint exit 0; index exit = start |
| Owner signature | — | **not an acceptance item for this phase.** W-9's "brief signed by the owner" is the owner's step after the PR |

## Stop gates

- Task 0 Step 2 fails (not post-P1, package not tracked, packet already exists, HC-M11 record missing).
- The D9 venv is missing.
- Any step would edit a file other than the 2 owned files, or any ask-first file (read-only here).
- A draft needs a legal conclusion to make sense. Rewrite it as a conditional plus "owner/legal review". If that is impossible, stop and ask.
- A CFR citation is needed that was not read. Mark it "citation to verify by legal/owner", or drop it.
- The start tree shows a FileHandler, or other logging config, that contradicts F-P8-2. Record it, update Brief 4, and flag it. Do not "fix".
- P4's `hipaa-controls.md:169` task is in flight before Brief 2 is signed. Tell the orchestrator (sign-off S-2).
- Another open PR edits `docs/features/TASK_LIST.md`. Wait and rebase; never merge-resolve someone else's notes.
- Any unexplained start-tree failure: record it. It is not this phase's to fix.
- Task 7 Step 5 prints any `new failures` (end minus start). A docs-only diff cannot cause one: stop and report it.
- Task 0 Step 3b: the `CLAUDE.md`/`AGENT.md` collected counts disagree with each other or with the measured start collection (P1 did not reconcile them). Report the three numbers; do not edit either file.

## Rollback

Docs only.
- **Before push:** `git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral worktree remove /mnt/c/Users/DangT/Documents/GitHub/hc-p8 && git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral branch -D docs/p8-gated-packet-hipaa-aligned`.
- **After push, before merge:** `gh pr close <pr-number> --delete-branch` (closes the PR and deletes the remote branch), then the two commands above.
- **After merge:** `git revert -m 1 <merge-sha>` on a branch from `origin/main`, via PR. No schema, config or runtime state changes. The probe's temp dir is removed by the probe step itself.

## Owner sign-offs (unsigned)

- S-1: The packet's per-brief lines (7) are the owner's. This plan records none of them.
- S-2 (ordering): "Run P8 Brief 2 to signature before P4's `hipaa-controls.md:169` task, or have P4 skip that task." Owner/orchestrator: ☐ P8-first ☐ P4 skips `:169` — notes/date: ____
- S-3 (routing F-P8-3): "Debug SQL echo prints bound parameters (PRIV-06). Open a separate owner-gated fix?" ☐ yes ☐ no ☐ defer — notes/date: ____

## Commit plan

| # | Message | Pathspec |
|---|---|---|
| 1 | `docs: scaffold gated-items owner decision packet (D10 posture)` | `audit/2026-09-25/gated-items-decision-packet.md` |
| 2 | `docs: MFA decision brief` | same |
| 3 | `docs: key-rotation decision brief` | same |
| 4 | `docs: pen-test scope decision brief` | same |
| 5 | `docs: audit-retention decision brief (designed as if HIPAA applied, D10)` | same |
| 6 | `docs: HC-M11 brief cites the flag-only approval; asks production behaviour and NLI-model distribution` | same |
| 7 | `docs: gated-items owner decision packet - awaiting sign-off (P8/W-9)` | packet + `docs/features/TASK_LIST.md` |

Rules for every commit:
- `git add <explicit paths>` then `git diff --cached --name-only`, then `git commit … -- <paths>`.
- Never `git add -A`, `git add .`, or `commit -a`.

## Recurring-failures recheck

| # | Applies? | Recheck in this plan |
|---|---|---|
| 1 Green check that could not fail | yes: greps | Task 7 Step 3 seeds a violation and removes the mandatory phrase; both must flip |
| 2 Fix creates next bug | yes: 4b/4c options | Brief 4 walks erase → backup → prune → tombstone; the D option's conflict with purge-on-erase is printed in Q4b |
| 3 Asserted figures | yes | every count and line has a command; the probe output is pasted, not paraphrased |
| 4 Environment-dependent results | yes: probe | interpreter and SHA stated; both `TestClient` (Step 1) and `uvicorn` CLI (Step 1b) measured |
| 5 Contaminated tree | yes | dedicated worktree (Task 0); diff-scope check |
| 6 Documented commands nobody ran | yes | every command in the packet (e.g. the security-gate check) is run and its output pasted |
| 7 SQL three-valued logic | yes: 4b sketch | the NULL-profile tombstone is handled explicitly in the sketch and its test |
| 8 Stale guidance as authority | yes | R2/R5 overturned plan 08 premises. `hipaa-controls.md:49-52` and `data-privacy.md:33` claims are checked against code, not repeated |
