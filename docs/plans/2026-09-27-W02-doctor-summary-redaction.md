# W-2 Doctor-Summary Redaction (D3) Implementation Plan

**Last Updated:** 2026-09-27 (rev 3: Codex review rounds 1–2 and GLOBAL executability rules applied)
**Owner:** repository owner
**Refresh Trigger:** any of these before this plan runs:
- a change to `src/backend/modules/export.py`, `src/backend/api/export.py`, `src/backend/modules/redaction.py` or `src/backend/tests/support/routes.py`;
- the W-10 governance commit landing;
- an owner answer to O-1…O-4 below.

**Prerequisites:** P0-B and P1 merged to `origin/main`, plus P4, the W-10 governance commit, P5 and the D9 venv (see Dependencies). Task 0's ancestry check failing before P1 lands is the **intended STOP**, not a defect.

**Review status:** 4 Codex rounds. The round-4 BLOCKER was fixed after the last round and has not been re-reviewed (owner acceptance required).

**Status:** PROPOSED — not executed. Nothing in this plan is implemented, wired or tested.
- D3 is **owner-approved** (verbatim scope below).
- O-2 is **owner-gated** and blocks Task 3.
- O-3 is **owner-gated** and blocks the **merge** (sign-off S-3).
- All are unsigned.

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The doctor summary (text, html, pdf) passes strict `RedactionEngine` before it is stored or rendered. CSV and JSON stay byte-for-byte unredacted.

**Architecture:** There is one choke point.
- `POST /export/doctor-summary` builds `summary_data` and stores it in `_summary_store`, and all three download formats render only from that stored dict.
- A new method, `ExportModule.redact_summary_data()`, returns a strict-redacted copy, and the route stores that copy.
- This mirrors the visit-prep packet, which redacts "BEFORE it is stored or rendered" (`modules/export.py:525-530,635-642` main@40f590e).
- `export_csv` and `export_json` are not touched.

**Tech Stack:** Python 3.11 (D9 venv), FastAPI `TestClient`, pytest, SQLAlchemy + aiosqlite (a real `audit_logs` table for HC-EXPR-003), `modules/redaction.py` (called, never edited), `pypdf` (already in `src/backend/requirements.txt`) for the real-PDF check. That check needs WeasyPrint to actually render; it skips otherwise, or fails when `HC_REQUIRE_WEASYPRINT=1`.

## Global Constraints

- **Target Python 3.11.** Do not use 3.12-only syntax. Use `core.time.utcnow` for any new timestamp; this plan adds none.
- **`modules/redaction.py` is ask-first and read-only here.** This plan *calls* `RedactionEngine(policy_level="strict")`. It never edits rules, levels or patterns.
- **Surgical edits only.** Touch the owned files and hunks listed below, nothing else.
- **Audit logging stays.** The `doctor_summary` and `summary_download` audit rows must still be written, with no PHI (C-AUDIT-1). HC-EXPR-003 asserts them as **persisted rows**.
- **No over-claim.** No commit, PR or doc may say the summary is "PHI-free". The claim is limited to the tested shapes: labelled name, DOB and MRN in free-text fields. The underscore-joined gap (O-3) is stated alongside.
- **Local-first.** No new network or dependency. `pypdf`, `weasyprint` and `aiosqlite` are already pinned (`requirements.txt:38,108` main@40f590e; `:38,:128` B@7b2ff1f).
- **Never lower a threshold, and never relax a guard to pass a test.**
- **Route tests go through HTTP** via `src/backend/tests/support/routes.py::route_client`.
- **Shell rules** (orchestrator, 2026-09-27):
  - Every bash block starts with the preamble line `WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail`. `$WT` is absolute.
  - Every `cd` is to an absolute path (`"$WT"`, `"$WT/src/backend"`); no relative `cd` after a prior `cd`.
  - `set -o pipefail` covers every pipe whose exit code matters.
- **Baseline sentences (GLOBAL rule).** Any commit that changes the collected test count updates **only the collected-count slots** in `CLAUDE.md` and `AGENT.md`, in **that same commit** (CLAUDE.md §4: "update it in the same commit").
  - A pass-count slot ("all N pass", "N pass in CI", "N−1 without an embedding model") changes only with a pass count measured in a **named environment**: interpreter plus embedding model present or absent. Otherwise it stays as it is and is flagged in the PR.
  - Never write a collected number into a pass-count slot.
- **Break-it-on-purpose never edits the phase worktree.** Every deliberate break runs in a disposable detached worktree, created from the phase worktree's HEAD and removed afterwards. Nothing is edited and then restored with `git checkout --` in `$WT`. Every break-it block carries the same guards:
  1. a **unique** path, `BRK="$(mktemp -u -d "$HOME/w02-break.XXXXXX")"`;
  2. `test ! -e "$BRK"`, or stop;
  3. `git worktree add --detach "$BRK" HEAD`, or stop;
  4. a recorded `git -C "$BRK" rev-parse --show-toplevel` that must equal `realpath "$BRK"` and differ from `$WT`, checked before any `cd` into it;
  5. `git worktree remove --force "$BRK"`, run only after that toplevel check passes again. It is forced because the disposable tree is dirty by design.

  Each block runs inside a subshell, so a guard's `exit 1` stops only that block.
- **Line numbers are labelled with their ref.** The executor re-verifies every one on the post-P5 start tree (Task 0 Step 5). By then P5 will have moved `modules/export.py:164,352` to `utcnow()`.

---

## Approval scope

**Owner decision D3** ([owner-decisions-2026-09-27.md](../capstone-report/owner-decisions-2026-09-27.md), row D3, "Redact doctor summary only"), verbatim:

> "Doctor summary goes to a third party → redact it (strict). CSV/JSON are the patient's own data export → keep full-fidelity like backups, and amend CLAUDE.md/data-privacy.md to name them as deliberate exceptions."

This plan implements the first sentence and pins the "keep full-fidelity" half with a test. The "amend CLAUDE.md/data-privacy.md" half belongs to **W-10** (handoff §5 row W-10), not to this plan.

**D3 does NOT license** (each item is out of scope, or owner-gated if wanted):

1. **Any edit to `modules/redaction.py`**: rules, patterns or policy levels. That includes closing the O-3 gap.
2. **Redacting CSV or JSON.** D3 says the opposite.
3. **Wording edits to `CLAUDE.md` or `docs/compliance/data-privacy.md`.** W-10 owns both. The one carve-out is the **collected-count slots** in the `CLAUDE.md` baseline paragraph and the `AGENT.md` backend-tests command line. CLAUDE.md §4 and the GLOBAL baseline-sentence rule require those to change in the commit that changes collection. That edit is count maintenance, not D3 governance. Pass-count slots are not edited by this plan unless a named-environment pass count was measured.
4. **Changes to other export paths:** `/export/questions`, the visit-prep packet, FHIR, RL-dataset, pinboard or backup exports.
5. **Changes to the ExportPage preview or its "Copy" button** (`src/frontend/src/pages/ExportPage.tsx:108-121` main@40f590e). See O-4.
6. **Adding a patient identifier** (name, DOB, MRN) to the summary. See O-1.
7. **Changing the summary's date format.** O-2 is owner-gated; Task 3 runs only once O-2 is signed.
8. **Changing which observations feed the summary** (verified vs unverified). D4 covers trends and legacy RAG only.
9. **Persisting `_summary_store` across restarts** (G-C1, PRIV-08).
10. **Editing the matrix or contract status text.** The PR *reports* the proposed status change; the owner or orchestrator updates those docs.

## Traceability

| ID | Where | Quoted (verified by grep 2026-09-27) |
|---|---|---|
| C-REDACT-1 | [architecture-engineering-contract.md](../capstone-report/architecture-engineering-contract.md) `:177-183` | "**C-REDACT-1 · BINDING (ask-first).** … Any path that writes user text to exportable files or external runners MUST pass through `modules/redaction.py` first … **contradicted** for CSV/JSON/doctor summary (`modules/export.py:82,223,267,290,358`)" |
| C-AUDIT-1 | same file `:323-329` | "Every route that touches documents, observations or profile data MUST write an audit row via `core/audit.py` … without PHI." |
| C-GATE-1 / C-GATE-3 | same file `:340`, `:360` | Measured collected counts. Explicit pathspecs plus `git diff --cached --name-only` |
| PRIV-04 | [specs-compliance-matrix.md](../capstone-report/specs-compliance-matrix.md) `:87` | "Every non-backup export is redacted … **CSV, JSON and doctor summary** (text/html/pdf) do not call redaction … **contradicted** \| **owner-gated**" |
| PRIV-02, PRIV-03, PRIV-01 | same file `:85`, `:86`, `:84` | FHIR, visit-prep/pinboard and RL export: redacted and **tested**. They must stay green and untouched |
| GATED-08 | same file `:158` | "Export-redaction and verified-only scope … PRIV-04, SAFE-02 … new: program P0-D" |
| G-A1 | [implementation-program.md](../capstone-report/implementation-program.md) `:389` | "Export redaction for CSV/JSON/doctor summary, or scope the doc (PRIV-04) … `modules/redaction.py` is ask-first" |
| W-2 | [handoff §5](../../audit/2026-09-25/handoff-2026-09-27-execution.md) `:139` | "The doctor summary (text/html/pdf) passes strict `RedactionEngine` before render … HC-EXPR-001 … HC-EXPR-002 … HC-EXPR-003 … 3 new tests; failures ⊆ start" |

**Proposed matrix change** (for the PR description only; not edited here):
- PRIV-04, doctor summary → **`tested`** (HC-EXPR-001/003; labelled PHI shapes only). The known gap is O-3, recorded as a strict xfail and named in the row's gap column.
- PRIV-04, CSV/JSON → **`tested`** as a named D3 exception (HC-EXPR-002 pins the bytes unchanged). Effective once W-10 lands.
- The PRIV-04 row as a whole stays **`partial`** while `/export/questions` is open (EXPORT-QUESTIONS). Status values are only those defined at matrix `:18-27`.

## Files

**Create**
- `src/backend/tests/test_export_redaction.py`. It holds HC-EXPR-001/002/003 as **8 collected items**:
  - 001 × 3 formats;
  - 001 real-PDF;
  - 001 known-gap strict xfail;
  - 002 × 2;
  - 003.

**Modify** (anchors are main@40f590e; neither branch A nor branch B touches the two `export.py` files, per `git diff --stat 40f590e 7b2ff1f|692fdf3`)
- `src/backend/modules/export.py`:
  - add `ExportModule.redact_summary_data()` after `_format_trends` (`:211-221`);
  - Task 3 only, if O-2 is signed (a): change the date format in `_format_abnormal_values` (`:203`).
- `src/backend/api/export.py`, `generate_doctor_summary` (`:379-479`):
  - redact before the store at `:446`;
  - return the redacted `key_findings` in the response (`:476`);
  - add `redaction_count` to the `doctor_summary` audit details (`:455-459`). This is the same allowlisted field the visit-prep audit carries (`:806-810`; `core/audit.py` `ALLOWED_DETAIL_KEYS` includes `"redaction_count"`).
- `CLAUDE.md` and `AGENT.md`: **collected-count slots only**, in the Task 1 and Task 2 commits. Anchors:
  - main@40f590e: collected slots at `CLAUDE.md:30` ("**1245 backend tests collected.**") and `:35` ("if it differs from 1245"), and in `AGENT.md:57` ("1245 collected"); pass slots at `CLAUDE.md:31` ("all 1245 pass") and in `AGENT.md:57` ("1245 pass in CI, 1244 without…").
  - B@7b2ff1f: `CLAUDE.md:30,31,35` and `AGENT.md:76`.
  - Re-locate them post-P1/W-10 in Task 0 Step 5, recorded as `COLLECTED_SLOTS` and `PASS_SLOTS`.
- `docs/plans/2026-09-27-W02-doctor-summary-redaction.md` (this file): the execution record only (Task 5).

**Read-only; must show zero diff at the end**
- Ask-first files: `src/backend/modules/redaction.py`, `modules/interpret_safety.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`, `src/backend/core/auth.py`.
- Neighbouring files:
  - `src/backend/tests/support/routes.py` (owned by P7);
  - `modules/fhir_export.py`, `modules/rl_dataset.py`;
  - `api/feedback.py`, `api/pinboards.py`, `api/backup.py`;
  - `src/backend/core/audit.py`, `src/backend/models/audit.py`;
  - `docs/compliance/data-privacy.md` (owned by W-10);
  - `docs/capstone-report/*`;
  - `src/frontend/**`.

**Shared-file ordering**

| File | Order | Why |
|---|---|---|
| `modules/export.py` | P5 → **W-2** | Program `:143`: "`modules/export.py`: P5 → W-2.". Plan 05 Task 10 edits `:164`, `:352` |
| `api/export.py` | **W-2** → G-C1 | G-C1 (PRIV-08) persists the export stores; it should persist already-redacted summaries. Never concurrent |
| `CLAUDE.md` (wording), `data-privacy.md` | W-10 → **W-2** | W-2 edits no wording. HC-EXPR-002 pins CSV/JSON as unredacted, which is only lawful once W-10 names them as exceptions |
| `CLAUDE.md` / `AGENT.md` collected-count slots | every phase, never concurrent (program overlap table: "Each phase writes its own measured count") | W-2 writes N0+2, then N0+8, each in the commit that changes collection. Pass slots are left alone and flagged in the PR |
| `tests/support/routes.py` | P7 → G-B1. W-2 only **reads** it | W-2 sets the profile-DB override on `client.app` and passes a real `master_db` through the existing parameter, so it never edits this file |

## Dependencies

| Needs | Why | Check (Task 0) |
|---|---|---|
| D3 | the approval | quoted above |
| P0-B, P0-B2 | the capstone package and this plan file are committed on main; commit 4 edits this plan file (owner gate P0-B2) | `git -C "$WT" ls-files docs/plans/2026-09-27-W02-*.md` prints the plan path |
| D9 | the 3.11 venv at `$HOME/venvs/asclexis-311` | `"$PY" --version` → `Python 3.11.x` |
| P1 | branches A and B on main | `git merge-base --is-ancestor 7b2ff1f HEAD && git merge-base --is-ancestor 692fdf3 HEAD` |
| P4, then the W-10 governance commit | handoff §3 `:96`: "P4 doc drift … → **governance commit** (§5) → P5". The CSV/JSON exception must already be in `CLAUDE.md` | `grep -nE "CSV\|JSON" "$WT/CLAUDE.md"` shows the D3 exception wording |
| P5 | shares `modules/export.py` | `! grep -q "datetime.utcnow" "$WT/src/backend/modules/export.py"` |
| P0-D | the program graph (`:120`) lists P0-D ⇢ W-2 ("superseded?") | **Not found:** there is no D3/D4 brief in `docs/plans/` (`ls`, 2026-09-27). D3 is already decided; the orchestrator confirms P0-D is moot for W-2 (sign-off S-5; canonical gate P0-D-MOOT) |

---

## Measured before writing (context, not targets)

All of this was prototyped in a scratchpad (not committed) on **main@40f590e**, dirty tree, **Windows Python 3.13.7** (`/mnt/c/Python313/python.exe`). That is *not* the D9 venv; the executor re-measures.

1. **Strict mode exists.**
   - Constructor: `RedactionEngine(policy_level: str = "standard", rules: Sequence[RedactionRule] | None = None)` (`modules/redaction.py:148-151`).
   - Call: `.redact(text: str) -> RedactionResult(text, redacted_count, metadata)` (`:171`, `:45-51`).
   - Strict rules: `ssn, email, phone, name_context, dob, address, mrn, numeric_date` (`:58-128`).
2. **The doctor summary contains no patient identity today.** Its rendered text comes only from:
   - observation `analyte_canonical`, `value`, `unit`, `ref_low`, `ref_high`, `flag` and dates (`modules/export.py:115-128,199-221`);
   - counts and `generated_at`;
   - template questions (`:407-429`).

   No name, DOB or MRN field is read (`api/export.py:130-174,434-445,551-604`). PHI can only reach the summary through free-text observation fields.
3. **RED against current code** (test code as in Task 2):
   ```
   FAILED ::test_hc_expr_001[text] - AssertionError: assert 'Jane' not in '=====...
   FAILED ::test_hc_expr_001[html] - assert 'Jane' not in '<!DOCTYPE h...dy>\n</...
   FAILED ::test_hc_expr_001[pdf] - assert 'Jane' not in '<!DOCTYPE h...dy>\n</h...
   (preview) AssertionError: ... 'Jane' is contained here: (Patient: Jane Doe) (H)", "hemoglobin: 9.1 g/dL (L DOB: 01/02/1980)", ...
   ```
4. **Store-time redaction, simulated.** With the store wrapped in a redacting dict, all 3 formats and the stored dict went GREEN. The same run also turned **every collection date** in "Values Outside Reference Range" into `[DATE-REDACTED]`, because `%m/%d/%Y` (`modules/export.py:203`) matches strict `numeric_date` (`redaction.py:122-127`). See O-2.
5. **No false positives.** 0 across 132 analyte names and synonyms (`NormalizeModule.ANALYTE_SYNONYMS`), each rendered as a summary line.
6. **The coverage gap is real, even after the fix.** Strict leaves `'patient_name:_jane_doe'`, `'dob:_01/02/1980'` and `'mrn:_a12345'` unchanged, and that underscore-joined shape is how unknown analytes are stored (`modules/normalize.py:279-284`). The known-gap test was prototyped **after** simulated store-time redaction and reported `XFAIL`: the text download still carried `patient_name:_jane_doe`, `dob:_01/02/1980` and `mrn:_a12345`. See O-3.
7. **Real persisted audit rows work over HTTP.** The setup:
   - a file-backed SQLite master DB holding the `profiles` and `audit_logs` tables, with `PRAGMA foreign_keys=ON`;
   - an aiosqlite `AsyncSession` with `NullPool`, passed as `route_client(..., master_db=session)`.

   It returned 2 rows: `('export.create', 'profile-a', {"summary_id": …, "format": "text", "observation_count": 5, "question_count": 4, "export_type": "doctor_summary"})` and `('export.create', 'profile-a', {…, "export_type": "summary_download"})`. The other profile's 403 wrote none.
8. **WeasyPrint** is not installed under Windows 3.13.7 (`ModuleNotFoundError`); `pypdf 6.5.0` is.
9. **CSV baselines cannot be golden files.** CSV bytes use `\r\n` (the `csv.writer` default), and `.gitattributes:2` is `* text=auto`, so git would rewrite a golden CSV *file*. The baseline lives in the test as escaped bytes literals instead.

## Owner questions (unsigned; see Sign-offs)

- **O-1 · Identity tension.** Not blocking.
  - A doctor needs to know whose results these are, but the summary carries no identifier today (fact 2). W-2 therefore removes nothing a doctor relies on.
  - After W-2, strict redaction would also strip any identifier added later.
  - The question: is an unidentified summary acceptable, with the patient handing it over in person?
  - A name/DOB header would need a new owner decision. D3 does not cover it and must not be read into it.
- **O-2 · Collection dates.** **Blocks Task 3.** Strict `numeric_date` erases every abnormal value's date (fact 4).
  - **(a)** Render those dates ISO-8601 (`%Y-%m-%d`). The visit-prep packet already does this (`modules/export.py:528-530,573`; HC-PKT-004), and strict deliberately does not match ISO (`redaction.py:110-113`). Patient-visible. **Recommended.**
  - **(b)** Keep `%m/%d/%Y` and accept `[DATE-REDACTED]`.

  Either option is a rendering choice, not a redaction change; `redaction.py` is untouched.
- **O-3 · Regex coverage gap.** **Pre-merge gate (S-3 must be signed before the W-2 PR merges).**
  - The strict engine misses underscore-joined PHI (fact 6).
  - HC-EXPR-001 seeds PHI only in labelled, spaced shapes. The strict-xfail `test_hc_expr_001_known_gap_underscore_phi` keeps the gap visible, and fails the suite (`XPASS(strict)`) as soon as anything changes it.
  - **(a)** Accept it as a documented residual gap for W-2. The PR and W-10/P4 wording say "pattern-based; underscore-joined identifiers are not matched".
  - **(b)** Separately approve a `redaction.py` change under its own plan (ask-first). W-2 does not wait for it, but the xfail marker is removed there.

  Nothing here licenses an export-side workaround.
- **O-4 · Adjacent surfaces.** Not in W-2.
  - ExportPage "Copy" (`ExportPage.tsx:108-121`) joins the summary `key_findings`, which W-2 redacts, with output from `POST /export/questions`.
  - `/export/questions` is **not** redacted and returns verbatim care-task `source_quote` (plan 01 `:78`; `api/export.py:607-661`).
  - Is that clipboard text "the doctor summary"? D3 does not say. Decide separately (canonical gate EXPORT-QUESTIONS; sign-off S-4).

---

## Task 0: Preconditions and phase-start measurement

**Files:** none modified.

- [ ] **Step 1: Create the worktree and prove it is post-P1**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
(  # subshell: a guard's `exit 1` stops only this block
git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral fetch origin || { echo "STOP: fetch failed"; exit 1; }
test ! -e "$WT" || { echo "STOP: $WT already exists; ask before touching it"; exit 1; }
git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral worktree add "$WT" -b fix/w02-doctor-summary-redaction origin/main || { echo "STOP: worktree add failed"; exit 1; }
WT_TOP="$(git -C "$WT" rev-parse --show-toplevel)" || { echo "STOP: $WT is not a git worktree"; exit 1; }
test "$WT_TOP" = "$(realpath "$WT")" || { echo "STOP: toplevel $WT_TOP != $WT"; exit 1; }
echo "WT=$WT toplevel=$WT_TOP"
cd "$WT" || exit 1
git merge-base --is-ancestor 7b2ff1f HEAD && git merge-base --is-ancestor 692fdf3 HEAD && echo post-P1
git rev-parse HEAD
"$PY" --version
)
```
Expected:
- `WT=… toplevel=…` with two identical paths;
- `post-P1`;
- a SHA;
- `Python 3.11.x`.

**STOP** if any of these holds:
- any `STOP:` line prints: fetch failed, `$WT` already exists, `worktree add` failed, or the toplevel does not match. Nothing was created that needs removing, so ask before touching any existing path or branch;
- `post-P1` is not printed (P1 has not landed);
- the venv is missing (D9 not executed).

- [ ] **Step 2: Check the other dependencies**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
! grep -q "datetime.utcnow" "$WT/src/backend/modules/export.py" && echo P5-in
grep -nE "CSV|JSON" "$WT/CLAUDE.md"
git -C "$WT" ls-files docs/plans/2026-09-27-W02-*.md
```
Expected:
- `P5-in`;
- at least one `CLAUDE.md` line naming CSV/JSON as a deliberate redaction exception (W-10);
- `docs/plans/2026-09-27-W02-doctor-summary-redaction.md` (P0-B2: the plan set is committed, so commit 4 has a tracked file).

Any miss → **STOP** and name the missing phase.

- [ ] **Step 3: Confirm the redaction API is unchanged (read-only check)**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
git -C "$WT" diff --exit-code --stat 40f590e HEAD -- src/backend/modules/redaction.py && echo redaction-unchanged
grep -nE "VALID_POLICY_LEVELS = |policy_level: str|def redact|policy_levels=frozenset\(\{\"strict\"\}\)" "$WT/src/backend/modules/redaction.py"
grep -n '"redaction_count"' "$WT/src/backend/core/audit.py"
```
Expected:
- `redaction-unchanged`;
- `VALID_POLICY_LEVELS = frozenset({"strict", "standard", "minimal"})`;
- `policy_level: str = "standard",`;
- `def redact(self, text: str) -> RedactionResult:`;
- 4 strict-only rule lines (dob, address, mrn, numeric_date);
- at least one `"redaction_count"` hit in the audit allowlist.

Any miss → **STOP**.

- [ ] **Step 4: Confirm the HC-EXPR IDs and the test filename are free**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
git -C "$WT" grep -n "HC-EXPR\|hc_expr" -- src/ || echo no-collision
test ! -e "$WT/src/backend/tests/test_export_redaction.py" && echo file-free
```
Expected: `no-collision` and `file-free`. Otherwise **STOP**.

- [ ] **Step 5: Re-verify the anchors on this tree** (record the actual line numbers in the Task 5 record)

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
grep -n "_summary_store\[summary.summary_id\] = summary_data\|key_findings=summary.key_findings\|export_type=\"doctor_summary\"\|def download_summary\|def export_csv\|def export_json" "$WT/src/backend/api/export.py"
grep -n "def _format_trends\|strftime(\"%m/%d/%Y\")\|def render_pdf_summary\|from weasyprint import HTML" "$WT/src/backend/modules/export.py"
grep -n "def route_client\|master_db\|dependency_overrides" "$WT/src/backend/tests/support/routes.py"
grep -nE "[0-9]{4} (backend tests )?collected|all [0-9]{4} pass|this line is stale|[0-9]{4} collected;" "$WT/CLAUDE.md" "$WT/AGENT.md"
```
Expected:
- Each `api/export.py` pattern is found once.
- `%m/%d/%Y` is found once in `modules/export.py`.
- `route_client(` still takes `router, prefix, profile_id, master_db`, and overrides only `require_auth` and `get_db`. If P7 changed the signature, adapt the *calls* in Tasks 1–2; never edit the helper.
- The count lines are located. Record the collected-count slots as `COLLECTED_SLOTS` (e.g. "**N backend tests collected.**", "if it differs from N", "N collected") and the pass-count slots as `PASS_SLOTS` (e.g. "all N pass", "N pass in CI, N−1 without an embedding model"). Only `COLLECTED_SLOTS` are ever edited without a named-environment measurement.

- [ ] **Step 6: Measure the start tree**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT/src/backend"
find "$WT/src/backend" -name __pycache__ -type d -prune -exec rm -rf {} +
"$PY" -m pytest tests/ --collect-only -q -p no:cacheprovider 2>&1 | tail -1
"$PY" -m pytest tests/ -p no:cacheprovider -q -rfEsxX 2>&1 | tail -30; echo "pytest-exit=$?"
"$PY" -c "import pypdf; print('pypdf', pypdf.__version__)"
"$PY" -c "from weasyprint import HTML; HTML(string='<p>x</p>').write_pdf(); print('weasyprint-renders')" || echo weasyprint-cannot-render
```
Record verbatim:
- interpreter, OS and SHA;
- **N0** = collected;
- **F0** = the failing node IDs;
- **S0** = skipped;
- **X0** = xfailed;
- `pytest-exit`;
- **ENV0** = interpreter plus embedding model present or absent (`test_api_rag_index_002b` PASSED means present, FAILED means absent);
- **WP0** = `weasyprint-renders` or `weasyprint-cannot-render`. The probe is the same `write_pdf()` call the real-PDF test's fixture makes: import alone is not enough, because missing Pango raises `OSError` at render time.

If a figure in `COLLECTED_SLOTS` ≠ N0, **STOP**: an earlier phase left the baseline stale. Report it; do not fix it here. (Program owner gate SLOT-RULE, proposed, makes every earlier collection-changing phase update these slots; until it is signed and applied, this STOP is expected after P5.)

---

## Task 1: HC-EXPR-002 — pin CSV/JSON bytes BEFORE any product change

This is a characterization test. It is **GREEN by design** on the unchanged tree, because it pins the "keep full-fidelity" half of D3. Its RED evidence comes from Step 7: a deliberate break, run in a disposable worktree after the commit. No product file may be modified before Task 2.

**Files:**
- Create `src/backend/tests/test_export_redaction.py`.
- Modify the `CLAUDE.md` and `AGENT.md` count figures.

**Interfaces produced (used by Task 2):**
- `PHI_STRINGS: tuple[str, ...]`
- `PHI_ROWS: tuple[SimpleNamespace, ...]`
- `_export_client(profile_id: str = PROFILE_A, rows: tuple = PHI_ROWS, master_db: object | None = None) -> ContextManager[TestClient]`
- `_export_bytes(path: str) -> bytes`
- the autouse fixture `_fresh_summary_store`

- [ ] **Step 1: Write the test file.** The baseline literals are the reference measured on main@40f590e; Step 3 re-captures them.

```python
"""W-2 / owner decision D3 (2026-09-27): doctor-summary redaction (HC-EXPR-NNN).

The doctor summary goes to a third party, so it passes strict
modules/redaction.py before it is stored or rendered, in every download format
(text, html, pdf). CSV and JSON are the patient's own full-fidelity export and
stay byte-for-byte unredacted (named exceptions, W-10).

Scope of the claim: labelled name/DOB/MRN in free-text fields. Underscore-joined
identifiers are a known, owner-gated gap (O-3), pinned by a strict xfail.

Every test drives FastAPI's dependency graph through
tests/support/routes.py::route_client (recurring-failures #1).
"""

from __future__ import annotations

import io
import json
import os
import sys
import types
from contextlib import ExitStack, contextmanager
from datetime import datetime
from types import SimpleNamespace
from typing import Iterator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

import api.export as export_api
from core.auth import get_profile_db_session
from tests.support.routes import route_client

PROFILE_A = "profile-a"
PROFILE_B = "profile-b"

# PHI seeded into the free-text fields the summary renders (unit, flag), in the
# labelled shapes the strict engine documents (name_context, dob, mrn).
PHI_STRINGS = ("Jane", "Doe", "01/02/1980", "A12345")


def _obs(
    obs_id: str,
    analyte: str,
    value: float,
    unit: str,
    flag: str | None,
    collected_at: datetime,
    ref_low: float,
    ref_high: float,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=obs_id,
        profile_id=PROFILE_A,
        analyte_canonical=analyte,
        analyte_raw=analyte,
        value=value,
        value_text=None,
        unit=unit,
        ref_low=ref_low,
        ref_high=ref_high,
        ref_range_text=None,
        flag=flag,
        is_abnormal=flag is not None,
        user_verified=False,
        collected_at=collected_at,
    )


PHI_ROWS = (
    _obs("00000000-0000-4000-8000-000000000001", "glucose", 100.0, "mg/dL", None, datetime(2024, 1, 10), 70.0, 99.0),
    _obs("00000000-0000-4000-8000-000000000002", "glucose", 250.0, "mg/dL", "HH", datetime(2024, 3, 15), 70.0, 99.0),
    _obs("00000000-0000-4000-8000-000000000003", "potassium", 6.1, "mmol/L (Patient: Jane Doe)", "H", datetime(2024, 3, 15), 3.5, 5.1),
    _obs("00000000-0000-4000-8000-000000000004", "hemoglobin", 9.1, "g/dL", "L DOB: 01/02/1980", datetime(2024, 3, 15), 12.0, 16.0),
    _obs("00000000-0000-4000-8000-000000000005", "sodium", 150.0, "mmol/L MRN: A12345", "H", datetime(2024, 3, 15), 135.0, 145.0),
)


class _Scalars:
    def __init__(self, rows: tuple) -> None:
        self._rows = rows

    def all(self) -> list:
        return list(self._rows)


class _Result:
    def __init__(self, rows: tuple) -> None:
        self._rows = rows

    def scalars(self) -> _Scalars:
        return _Scalars(self._rows)


class _FakeProfileDb:
    """Returns the fixture rows for any query (pattern: test_observations_audit.py)."""

    def __init__(self, rows: tuple) -> None:
        self._rows = rows

    async def execute(self, _stmt: object) -> _Result:
        return _Result(self._rows)


@pytest.fixture(autouse=True)
def _fresh_summary_store(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(export_api, "_summary_store", {})


@contextmanager
def _export_client(
    profile_id: str = PROFILE_A,
    rows: tuple = PHI_ROWS,
    master_db: object | None = None,
) -> Iterator[TestClient]:
    """route_client for /export over a fixture vault.

    master_db=None: route_client's AsyncMock master DB, with the audit helper
    stubbed. HC-EXPR-003 passes a real AsyncSession so audit rows persist.
    """
    fake_db = _FakeProfileDb(rows)

    async def _override_profile_db() -> _FakeProfileDb:
        return fake_db

    with ExitStack() as stack:
        if master_db is None:
            stack.enter_context(
                patch.object(export_api, "log_export_event", AsyncMock(return_value=object()))
            )
        client = stack.enter_context(
            route_client(export_api.router, "/export", profile_id=profile_id, master_db=master_db)
        )
        client.app.dependency_overrides[get_profile_db_session] = _override_profile_db
        yield client


def _export_bytes(path: str) -> bytes:
    """GET /export/{path} over HTTP with the PHI fixture; return the body."""
    with _export_client() as client:
        response = client.get(f"/export/{path}")
    assert response.status_code == 200, response.text
    return response.content


# Captured on the W-2 start tree BEFORE any product change (Task 1 Step 3).
# Escaped bytes literals, not golden files: `.gitattributes` has
# `* text=auto`, which would rewrite the CSV's \r\n endings in a file.
BASELINE_CSV = (
    b'Date,Analyte,Value,Unit,Reference Low,Reference High,Flag,Verified\r\n'
    b'2024-01-10,glucose,100.0,mg/dL,70.0,99.0,,No\r\n'
    b'2024-03-15,glucose,250.0,mg/dL,70.0,99.0,HH,No\r\n'
    b'2024-03-15,hemoglobin,9.1,g/dL,12.0,16.0,L DOB: 01/02/1980,No\r\n'
    b'2024-03-15,potassium,6.1,mmol/L (Patient: Jane Doe),3.5,5.1,H,No\r\n'
    b'2024-03-15,sodium,150.0,mmol/L MRN: A12345,135.0,145.0,H,No\r\n'
)
BASELINE_JSON = (
    b'[\n'
    b'  {\n'
    b'    "id": "00000000-0000-4000-8000-000000000001",\n'
    b'    "analyte_canonical": "glucose",\n'
    b'    "analyte_raw": "glucose",\n'
    b'    "value": 100.0,\n'
    b'    "value_text": null,\n'
    b'    "unit": "mg/dL",\n'
    b'    "ref_low": 70.0,\n'
    b'    "ref_high": 99.0,\n'
    b'    "ref_range_text": null,\n'
    b'    "flag": null,\n'
    b'    "is_abnormal": false,\n'
    b'    "user_verified": false,\n'
    b'    "collected_at": "2024-01-10T00:00:00"\n'
    b'  },\n'
    b'  {\n'
    b'    "id": "00000000-0000-4000-8000-000000000002",\n'
    b'    "analyte_canonical": "glucose",\n'
    b'    "analyte_raw": "glucose",\n'
    b'    "value": 250.0,\n'
    b'    "value_text": null,\n'
    b'    "unit": "mg/dL",\n'
    b'    "ref_low": 70.0,\n'
    b'    "ref_high": 99.0,\n'
    b'    "ref_range_text": null,\n'
    b'    "flag": "HH",\n'
    b'    "is_abnormal": true,\n'
    b'    "user_verified": false,\n'
    b'    "collected_at": "2024-03-15T00:00:00"\n'
    b'  },\n'
    b'  {\n'
    b'    "id": "00000000-0000-4000-8000-000000000003",\n'
    b'    "analyte_canonical": "potassium",\n'
    b'    "analyte_raw": "potassium",\n'
    b'    "value": 6.1,\n'
    b'    "value_text": null,\n'
    b'    "unit": "mmol/L (Patient: Jane Doe)",\n'
    b'    "ref_low": 3.5,\n'
    b'    "ref_high": 5.1,\n'
    b'    "ref_range_text": null,\n'
    b'    "flag": "H",\n'
    b'    "is_abnormal": true,\n'
    b'    "user_verified": false,\n'
    b'    "collected_at": "2024-03-15T00:00:00"\n'
    b'  },\n'
    b'  {\n'
    b'    "id": "00000000-0000-4000-8000-000000000004",\n'
    b'    "analyte_canonical": "hemoglobin",\n'
    b'    "analyte_raw": "hemoglobin",\n'
    b'    "value": 9.1,\n'
    b'    "value_text": null,\n'
    b'    "unit": "g/dL",\n'
    b'    "ref_low": 12.0,\n'
    b'    "ref_high": 16.0,\n'
    b'    "ref_range_text": null,\n'
    b'    "flag": "L DOB: 01/02/1980",\n'
    b'    "is_abnormal": true,\n'
    b'    "user_verified": false,\n'
    b'    "collected_at": "2024-03-15T00:00:00"\n'
    b'  },\n'
    b'  {\n'
    b'    "id": "00000000-0000-4000-8000-000000000005",\n'
    b'    "analyte_canonical": "sodium",\n'
    b'    "analyte_raw": "sodium",\n'
    b'    "value": 150.0,\n'
    b'    "value_text": null,\n'
    b'    "unit": "mmol/L MRN: A12345",\n'
    b'    "ref_low": 135.0,\n'
    b'    "ref_high": 145.0,\n'
    b'    "ref_range_text": null,\n'
    b'    "flag": "H",\n'
    b'    "is_abnormal": true,\n'
    b'    "user_verified": false,\n'
    b'    "collected_at": "2024-03-15T00:00:00"\n'
    b'  }\n'
    b']'
)


@pytest.mark.parametrize(
    ("path", "baseline"),
    [("csv", BASELINE_CSV), ("json", BASELINE_JSON)],
    ids=["csv", "json"],
)
def test_hc_expr_002_csv_json_unchanged_byte_for_byte(path: str, baseline: bytes) -> None:
    """HC-EXPR-002: CSV/JSON are the patient's own full-fidelity export (D3)."""
    body = _export_bytes(path)
    assert body == baseline
    # Not vacuous: the exception is real, the seeded identifiers are still there.
    for phi in PHI_STRINGS:
        assert phi.encode() in body
```

- [ ] **Step 2: Run it**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT/src/backend" && "$PY" -B -m pytest tests/test_export_redaction.py -p no:cacheprovider -q
```
Expected: `2 passed`.

- [ ] **Step 3: Re-capture the baseline from the start tree and compare it with the reference**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT/src/backend" && "$PY" -B - <<'EOF'
from tests.test_export_redaction import _export_bytes
for name, path in (("BASELINE_CSV", "csv"), ("BASELINE_JSON", "json")):
    body = _export_bytes(path)
    print(f"{name} = (")
    for line in body.splitlines(keepends=True):
        print(f"    {line!r}")
    print(")")
EOF
```
Expected: identical to the Step 1 literals (352 bytes of CSV and 1923 bytes of JSON on main@40f590e).

If it differs, an earlier phase changed the CSV/JSON output. **STOP.** Find that commit with `git -C "$WT" log -p origin/main -- src/backend/modules/export.py src/backend/api/export.py` and explain it in the PR. Only then paste the captured literals over the reference. Never capture after Task 2 has started.

- [ ] **Step 4: Note what this test would fail to notice**
  - The fake DB ignores SQL, so a change to `_fetch_observations` filtering stays invisible unless it changes the rows returned for this fixture.
  - Only the unfiltered call is covered: no `analytes`, `from_date` or `to_date`.
  - Response headers are not compared (`Content-Disposition` carries today's date).

- [ ] **Step 5: Update the collected-count slots** (collection is now N0+2)

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT/src/backend" && find "$WT/src/backend" -name __pycache__ -type d -prune -exec rm -rf {} + && "$PY" -m pytest tests/ --collect-only -q -p no:cacheprovider 2>&1 | tail -1
```
Expected: `N0+2 tests collected`.

Edit by hand, following the GLOBAL baseline-sentence rule:
- Every figure in `COLLECTED_SLOTS` goes from N0 to N0+2.
- `PASS_SLOTS` are **not edited**. They name environments (CI with an embedding model; local without one) that this step has not measured. The PR flags them as "pass counts not re-measured by W-2".
- The `test_api_rag_index_002b` / 0.7-threshold sentence stays verbatim.
- Never write N0+2 into a pass slot.

Then check the diff:
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; set -o pipefail
git -C "$WT" diff -U0 -- CLAUDE.md AGENT.md
```
Expected: only digit changes, and only in `COLLECTED_SLOTS`.

- [ ] **Step 6: Commit.** This is a test-only product change, which proves the baseline predates the fix.

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; set -o pipefail
cd "$WT"
git add -- src/backend/tests/test_export_redaction.py CLAUDE.md AGENT.md
git diff --cached --name-only
```
Expected: exactly the 3 paths.

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; set -o pipefail
cd "$WT"
git commit -m "fix(export): pin CSV/JSON export bytes before doctor-summary redaction (HC-EXPR-002)

Test-only product change. Baseline captured on the W-2 start tree before any
product change. CSV/JSON stay full-fidelity per owner decision D3 (2026-09-27).
Collected-count slots updated in the same commit (CLAUDE.md section 4); pass
counts not re-measured.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- src/backend/tests/test_export_redaction.py CLAUDE.md AGENT.md
```

- [ ] **Step 7: Break it on purpose, in a disposable worktree** (GLOBAL rule: never edit and then restore in `$WT`)

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
(  # subshell: every guard's `exit 1` stops only this block
BRK="$(mktemp -u -d "$HOME/w02-break.XXXXXX")"   # unique per run; -u: name only, nothing created
test ! -e "$BRK" || { echo "STOP: $BRK already exists"; exit 1; }
git -C "$WT" worktree add --detach "$BRK" HEAD || { echo "STOP: worktree add failed"; exit 1; }
BRK_TOP="$(git -C "$BRK" rev-parse --show-toplevel)" || exit 1
test "$BRK_TOP" = "$(realpath "$BRK")" && test "$BRK_TOP" != "$(realpath "$WT")" || { echo "STOP: $BRK is not its own worktree ($BRK_TOP)"; exit 1; }
echo "BRK=$BRK toplevel=$BRK_TOP"
"$PY" - "$BRK" <<'EOF'
import sys
root = sys.argv[1]
p = f"{root}/src/backend/api/export.py"
s = open(p).read()
old = "    csv_content = export_module.export_csv(observations)\n"
assert s.count(old) == 1, "anchor moved; re-verify"
s = s.replace(old, old + '    from modules.redaction import RedactionEngine\n    csv_content = RedactionEngine(policy_level="strict").redact(csv_content).text\n')
open(p, "w").write(s)
EOF
(cd "$BRK/src/backend" && "$PY" -B -m pytest tests/test_export_redaction.py -p no:cacheprovider -q; echo "pytest-exit=$?")
test "$(git -C "$BRK" rev-parse --show-toplevel)" = "$BRK_TOP" || { echo "STOP: toplevel changed; not removing $BRK"; exit 1; }
git -C "$WT" worktree remove --force "$BRK"   # forced: the disposable tree is dirty by design
)
git -C "$WT" worktree list
git -C "$WT" status --short
```
Expected:
- a `BRK=… toplevel=…` line with two identical paths under `$HOME/w02-break.*`;
- `1 failed, 1 passed`, with `test_hc_expr_002_csv_json_unchanged_byte_for_byte[csv] - AssertionError: assert b'Date,Analyte...`;
- `pytest-exit=1`;
- `worktree list` no longer shows `$BRK`;
- `git status --short` in `$WT` is empty, because the phase worktree was never edited.

Any `STOP:` line means nothing was removed. Investigate by hand, and never force-remove a path you did not just create.

If the test stays green, **STOP**: it cannot see a redacted CSV.

---

## Task 2: HC-EXPR-001/003 fail first, then strict redaction before the store

**Files:**
- Modify `src/backend/tests/test_export_redaction.py` (append).
- Modify `src/backend/modules/export.py`.
- Modify `src/backend/api/export.py`.
- Modify the `CLAUDE.md` and `AGENT.md` count figures.

**Interfaces:**
- **Consumes:** the Task 1 helpers.
- **Produces:** `ExportModule.redact_summary_data(self, summary_data: dict) -> dict`. It returns a **new** dict and does not mutate the input.
  - Strict-redacted fields: `key_findings`, `sections[*].content`, and in `questions[*]` the fields `question`, `context`, `source_quote` and `related_analytes`.
  - Added field: `redaction_count: int`.

- [ ] **Step 1: Append the failing tests**

```python
from sqlalchemy import create_engine, event, insert, select  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from core.database import Base  # noqa: E402
from models.audit import AuditLog  # noqa: E402
from models.profile import Profile  # noqa: E402

# Underscore-joined identifiers: the storage shape of unknown analytes
# (modules/normalize.py fallback). Strict redaction does not match it (O-3).
GAP_ROWS = (
    _obs("00000000-0000-4000-8000-000000000011", "patient_name:_jane_doe", 1.0, "", "H", datetime(2024, 3, 15), 0.0, 0.5),
    _obs("00000000-0000-4000-8000-000000000012", "dob:_01/02/1980", 1.0, "", "H", datetime(2024, 3, 15), 0.0, 0.5),
    _obs("00000000-0000-4000-8000-000000000013", "mrn:_a12345", 1.0, "", "H", datetime(2024, 3, 15), 0.0, 0.5),
)


def _install_capturing_weasyprint(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stand-in WeasyPrint: the 'PDF' is exactly the HTML handed to the PDF
    writer. render_pdf_summary builds the PDF only from that HTML, so PHI absent
    here is PHI absent from the PDF. Runs in every environment."""
    fake = types.ModuleType("weasyprint")

    class HTML:
        def __init__(self, string: str) -> None:
            self._html = string

        def write_pdf(self) -> bytes:
            return self._html.encode("utf-8")

    fake.HTML = HTML
    monkeypatch.setitem(sys.modules, "weasyprint", fake)


def _download_summary(client: TestClient, fmt: str) -> tuple[str, bytes]:
    created = client.post(
        "/export/doctor-summary", json={"format": fmt, "include_questions": True}
    )
    assert created.status_code == 200, created.text
    summary_id = created.json()["summary_id"]
    response = client.get(
        f"/export/doctor-summary/{summary_id}/download", params={"format": fmt}
    )
    assert response.status_code == 200, response.text
    return summary_id, response.content


@pytest.mark.parametrize("fmt", ["text", "html", "pdf"])
def test_hc_expr_001_doctor_summary_has_no_phi(
    fmt: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """HC-EXPR-001: labelled name, DOB and MRN are absent from every format."""
    if fmt == "pdf":
        _install_capturing_weasyprint(monkeypatch)
    with _export_client() as client:
        _summary_id, raw = _download_summary(client, fmt)
    body = raw.decode("utf-8")
    for phi in PHI_STRINGS:
        assert phi not in body
    # Not vacuous: redaction ran, and the clinical content survived it.
    for token in ("[NAME-REDACTED]", "[DOB-REDACTED]", "[MRN-REDACTED]"):
        assert token in body
    for clinical in ("glucose", "250.0", "potassium", "6.1", "hemoglobin", "sodium", "mg/dL"):
        assert clinical in body


@pytest.fixture
def weasyprint_renders() -> None:
    """Probe a real render BEFORE the request. Importing WeasyPrint is not
    enough: a missing Pango raises OSError from write_pdf(), which would
    otherwise surface as an error (the route turns it into HTTP 500).
    HC_REQUIRE_WEASYPRINT=1 turns the skip into a failure, so an environment
    that is supposed to render PDFs cannot skip silently."""
    try:
        from weasyprint import HTML

        HTML(string="<p>x</p>").write_pdf()
    except (ImportError, OSError) as exc:
        reason = f"WeasyPrint cannot render here ({type(exc).__name__}: {exc})"
        if os.environ.get("HC_REQUIRE_WEASYPRINT") == "1":
            pytest.fail(f"HC_REQUIRE_WEASYPRINT=1 but {reason}")
        pytest.skip(f"{reason}; the fake-writer pdf case still ran")


def test_hc_expr_001_real_pdf_extracted_text_has_no_phi(weasyprint_renders: None) -> None:
    """HC-EXPR-001 (real PDF): runs only where WeasyPrint renders (see fixture)."""
    from pypdf import PdfReader

    with _export_client() as client:
        _summary_id, raw = _download_summary(client, "pdf")
    text = "".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(raw)).pages)
    assert "glucose" in text  # extraction works; otherwise absence proves nothing
    for phi in PHI_STRINGS:
        assert phi not in text


@pytest.mark.xfail(
    strict=True,
    reason=(
        "O-3 known gap: strict RedactionEngine does not match underscore-joined "
        "identifiers (unknown-analyte storage shape). Owner sign-off S-3. "
        "XPASS means redaction changed: update S-3 and remove this marker."
    ),
)
def test_hc_expr_001_known_gap_underscore_phi() -> None:
    """HC-EXPR-001 (known gap, visible not hidden): expected to fail today."""
    with _export_client(rows=GAP_ROWS) as client:
        _summary_id, raw = _download_summary(client, "text")
    body = raw.decode("utf-8").lower()
    for phi in ("jane", "01/02/1980", "a12345"):
        assert phi not in body


@pytest.fixture
def master_audit_db(tmp_path) -> Iterator[tuple[AsyncSession, Engine]]:
    """A real master DB file with `profiles` + `audit_logs`, FKs enforced, so
    HC-EXPR-003 asserts persisted rows. NullPool: every connection is opened
    inside the TestClient's own event loop."""
    db_path = tmp_path / "master_audit.db"
    sync_engine = create_engine(f"sqlite:///{db_path}")
    async_engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", poolclass=NullPool)

    def _fk_on(dbapi_conn, _record) -> None:
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    event.listen(sync_engine, "connect", _fk_on)
    event.listen(async_engine.sync_engine, "connect", _fk_on)
    Base.metadata.create_all(sync_engine, tables=[Profile.__table__, AuditLog.__table__])
    now = datetime(2026, 9, 27)
    with sync_engine.begin() as conn:
        conn.execute(
            insert(Profile.__table__),
            [
                {"id": pid, "display_name": "T", "encryption_key_id": "k",
                 "is_locked": False, "created_at": now, "updated_at": now}
                for pid in (PROFILE_A, PROFILE_B)
            ],
        )
    session = AsyncSession(async_engine, expire_on_commit=False)
    try:
        yield session, sync_engine
    finally:
        sync_engine.dispose()


def _audit_rows(sync_engine: Engine) -> list[dict]:
    with sync_engine.connect() as conn:
        return [dict(r) for r in conn.execute(select(AuditLog.__table__)).mappings()]


def test_hc_expr_003_doctor_summary_route_over_http(master_audit_db) -> None:
    """HC-EXPR-003: the preview and the store are redacted; generate and
    download each persist a real audit row without PHI; another profile gets
    403 and writes no row; an unknown id gets 404."""
    session, sync_engine = master_audit_db
    with _export_client(PROFILE_A, master_db=session) as client:
        created = client.post(
            "/export/doctor-summary", json={"format": "text", "include_questions": True}
        )
        assert created.status_code == 200, created.text
        payload = created.json()
        summary_id = payload["summary_id"]
        preview = json.dumps(payload["key_findings"])  # what ExportPage shows and copies
        for phi in PHI_STRINGS:
            assert phi not in preview
        stored = export_api._summary_store[summary_id]
        stored_text = json.dumps(stored, default=str)  # incl. unrendered question context
        for phi in PHI_STRINGS:
            assert phi not in stored_text
        assert stored["redaction_count"] >= 3

        download = client.get(
            f"/export/doctor-summary/{summary_id}/download", params={"format": "text"}
        )
        assert download.status_code == 200
        unknown = client.get(
            "/export/doctor-summary/00000000-0000-4000-8000-00000000ffff/download"
        )
        assert unknown.status_code == 404

    rows = _audit_rows(sync_engine)
    assert all(r["event_type"] == "export.create" and r["profile_id"] == PROFILE_A for r in rows)
    details = [json.loads(r["details_json"]) for r in rows]
    assert sorted(d["export_type"] for d in details) == ["doctor_summary", "summary_download"]
    assert all(d["summary_id"] == summary_id for d in details)
    generate = next(d for d in details if d["export_type"] == "doctor_summary")
    assert generate["redaction_count"] == stored["redaction_count"]
    audit_text = json.dumps(rows, default=str)
    for phi in PHI_STRINGS:
        assert phi not in audit_text

    with _export_client(PROFILE_B, master_db=session) as other:
        refused = other.get(f"/export/doctor-summary/{summary_id}/download")
    assert refused.status_code == 403
    assert len(_audit_rows(sync_engine)) == 2  # the refusal persisted no row
```

- [ ] **Step 2: Run them; they must fail**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT/src/backend" && "$PY" -B -m pytest tests/test_export_redaction.py -p no:cacheprovider -q -rsxX
```
Expected output (the 001 lines and the preview assertion were measured on the prototype):
```
FAILED tests/test_export_redaction.py::test_hc_expr_001_doctor_summary_has_no_phi[text] - AssertionError: assert 'Jane' not in '=====...
FAILED tests/test_export_redaction.py::test_hc_expr_001_doctor_summary_has_no_phi[html] - assert 'Jane' not in '<!DOCTYPE h...
FAILED tests/test_export_redaction.py::test_hc_expr_001_doctor_summary_has_no_phi[pdf] - assert 'Jane' not in '<!DOCTYPE h...
FAILED tests/test_export_redaction.py::test_hc_expr_003_doctor_summary_route_over_http - AssertionError: assert 'Jane' not in '["glucose: 250.0 mg/dL (critical - HH)", "potassium: 6.1 mmol/L (Patient: Jane Doe) (H)", ...
XFAIL tests/test_export_redaction.py::test_hc_expr_001_known_gap_underscore_phi - O-3 known gap ...
```
- The real-PDF test either shows `SKIPPED ... WeasyPrint cannot render here (...)` (WP0 = cannot-render) or fails on `assert 'Jane' not in ...` (WP0 = renders). Record which.
- HC-EXPR-002 stays at 2 passed.
- If any listed FAILED test passes here, **STOP**: that test cannot see the bug.

- [ ] **Step 3: Implement `redact_summary_data`** in `src/backend/modules/export.py`, directly after `_format_trends`

```python
    def redact_summary_data(self, summary_data: dict) -> dict:
        """Return a strict-redacted copy of a doctor summary (owner decision D3).

        D3 (2026-09-27): the doctor summary goes to a third party, so every
        user-derived text field passes through modules/redaction.py at the
        strict policy BEFORE it is stored or rendered. text, html and pdf all
        render from the stored dict. CSV/JSON (export_csv/export_json) are
        deliberately NOT redacted: they are the patient's own full-fidelity
        export. Strict is pattern-based: underscore-joined identifiers are not
        matched (owner-gated gap O-3). The input dict is not mutated.
        """
        from modules.redaction import RedactionEngine

        engine = RedactionEngine(policy_level="strict")
        redaction_count = 0

        def _redact(value: object) -> object:
            nonlocal redaction_count
            if not isinstance(value, str) or not value:
                return value
            result = engine.redact(value)
            redaction_count += result.redacted_count
            return result.text

        key_findings = [_redact(f) for f in summary_data.get("key_findings", [])]
        sections = [
            {**s, "content": _redact(s.get("content", ""))}
            for s in summary_data.get("sections", [])
        ]
        questions = [
            {
                **q,
                "question": _redact(q.get("question")),
                "context": _redact(q.get("context")),
                "source_quote": _redact(q.get("source_quote")),
                "related_analytes": [_redact(a) for a in q.get("related_analytes") or []],
            }
            if isinstance(q, dict)
            else _redact(q)
            for q in summary_data.get("questions", [])
        ]
        return {
            **summary_data,
            "key_findings": key_findings,
            "sections": sections,
            "questions": questions,
            "redaction_count": redaction_count,
        }
```

- [ ] **Step 4: Call it before the store** in `src/backend/api/export.py` `generate_doctor_summary`
  1. Replace `    _summary_store[summary.summary_id] = summary_data` (`:446` main@40f590e) with:
     ```python
         # D3 (2026-09-27): the doctor summary goes to a third party. Strict
         # redaction runs BEFORE it is stored, so the preview below and every
         # download format (text/html/pdf render from the store) are redacted.
         summary_data = export_module.redact_summary_data(summary_data)
         _summary_store[summary.summary_id] = summary_data
     ```
  2. In the `doctor_summary` audit `details` (`:455-459`), add this line after `"question_count": len(questions),`:
     ```python
                 "redaction_count": summary_data["redaction_count"],
     ```
  3. In `SummaryResponse(...)` (`:476`), change `key_findings=summary.key_findings,` to:
     ```python
         key_findings=summary_data["key_findings"],
     ```

- [ ] **Step 5: Run to GREEN, then check that the WeasyPrint gate cannot pass silently**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT/src/backend" && "$PY" -B -m pytest tests/test_export_redaction.py -p no:cacheprovider -q -rsxX; echo "pytest-exit=$?"
HC_REQUIRE_WEASYPRINT=1 "$PY" -B -m pytest tests/test_export_redaction.py -k real_pdf -p no:cacheprovider -q -rs; echo "require-exit=$?"
```
Expected, first run:
- WP0 = cannot-render: `6 passed, 1 skipped, 1 xfailed`, `pytest-exit=0`;
- WP0 = renders: `7 passed, 1 xfailed`.

Expected, second run:
- WP0 = renders: `1 passed`, `require-exit=0`;
- WP0 = cannot-render: `1 error` (a fixture failure is reported as ERROR at setup) with `Failed: HC_REQUIRE_WEASYPRINT=1 but WeasyPrint cannot render here (...)`, `require-exit=1`. This proves the flag turns the skip into a hard failure. Measured in a scratch copy with Windows 3.13.7 (WeasyPrint absent); the env var needs `WSLENV` only when a Windows interpreter is driven from WSL.

Also:
- HC-EXPR-002 must still pass; that proves CSV/JSON did not change.
- An `XPASS(strict)` on the known-gap test here means redaction behaves differently from the prototype. **STOP.**

- [ ] **Step 6: Note what these tests would fail to notice**
  - **001:**
    - PHI in shapes strict does not match: names without a `patient`/`name`/`mr`/`ms`/`dr` label, DOB without a `dob` label, unlabelled MRNs. The underscore shape is *pinned* by the xfail, not fixed (O-3).
    - Any future render path that bypasses `_summary_store`. G-C1 must persist the stored, redacted dict.
    - The fake-writer PDF case proves only which HTML the PDF writer received.
    - The real-PDF case skips wherever the fixture's `write_pdf()` probe fails, unless `HC_REQUIRE_WEASYPRINT=1`. **CI does not set that flag and this plan does not edit `ci.yml`**, so CI skips the test whenever Pango is missing. Real-PDF render coverage in CI is **UNMEASURED** until the PR's CI log shows PASSED; the fake-writer pdf case still runs there. Whether to add Pango plus `HC_REQUIRE_WEASYPRINT=1` to CI goes to whoever owns `ci.yml` next (G-B4).
  - **003:**
    - `route_client` overrides `require_auth`, so token validation is not exercised here (by design; it is covered elsewhere).
    - The audit rows are real, but they live in a test SQLite file, not the SQLCipher master DB, so encryption-at-rest of audit rows is out of scope (KEY-02 / G-B2).

- [ ] **Step 7: Update the collected-count slots** (collection is now N0+8)

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
cd "$WT/src/backend" && find "$WT/src/backend" -name __pycache__ -type d -prune -exec rm -rf {} + && "$PY" -m pytest tests/ --collect-only -q -p no:cacheprovider 2>&1 | tail -1
```
Expected: `N0+8 tests collected`.

Edit by hand, following the GLOBAL baseline-sentence rule:
- Every figure in `COLLECTED_SLOTS` → N0+8.
- `PASS_SLOTS` stay **unchanged**. They are now known to be stale: the strict xfail means "all N pass" cannot hold in any environment, and the real-PDF test skips where Pango is missing. Neither slot's environment (CI with an embedding model; local without one) has been measured, so the PR flags both slots with that reason.
- A pass slot may be rewritten only with a pass count measured in a **named environment** (interpreter + embedding model present/absent, e.g. ENV0 from Task 4 Step 5). If the executor does that, the commit message names the environment and the command.
- The 0.7-threshold sentence stays verbatim.
- Never write N0+8 into a pass slot.

Then check the diff:
```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; set -o pipefail
git -C "$WT" diff -U0 -- CLAUDE.md AGENT.md
```
Expected: only digit changes, and only in `COLLECTED_SLOTS`.

- [ ] **Step 8: Commit**

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; set -o pipefail
cd "$WT"
git add -- src/backend/modules/export.py src/backend/api/export.py src/backend/tests/test_export_redaction.py CLAUDE.md AGENT.md
git diff --cached --name-only
```
Expected: exactly those 5 paths.

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; set -o pipefail
cd "$WT"
git commit -m "fix(export): strict-redact the doctor summary before it is stored or rendered (D3)

HC-EXPR-001 (text/html/pdf) and HC-EXPR-003 (HTTP route: preview, store,
persisted audit rows, 403/404) observed failing first. Scope: labelled
name/DOB/MRN; underscore-joined identifiers are a known gap (O-3), pinned by a
strict xfail. CSV/JSON unchanged (HC-EXPR-002). modules/redaction.py not
modified. Collected-count slots updated in the same commit; pass counts not
re-measured.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- src/backend/modules/export.py src/backend/api/export.py src/backend/tests/test_export_redaction.py CLAUDE.md AGENT.md
```

- [ ] **Step 9: Break it on purpose, 5 ways, each in a fresh disposable worktree** (GLOBAL rule; `$WT` is never edited)

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
brk() (  # subshell body: $1 = label; stdin = python patch script (argv[1] = $BRK). A guard's exit 1 ends only this call.
  BRK="$(mktemp -u -d "$HOME/w02-break.XXXXXX")"   # unique per run; -u: name only, nothing created
  test ! -e "$BRK" || { echo "STOP: $BRK already exists"; exit 1; }
  git -C "$WT" worktree add --detach "$BRK" HEAD || { echo "STOP: worktree add failed"; exit 1; }
  BRK_TOP="$(git -C "$BRK" rev-parse --show-toplevel)" || exit 1
  test "$BRK_TOP" = "$(realpath "$BRK")" && test "$BRK_TOP" != "$(realpath "$WT")" || { echo "STOP: $BRK is not its own worktree ($BRK_TOP)"; exit 1; }
  echo "BRK=$BRK toplevel=$BRK_TOP"
  if "$PY" - "$BRK"; then
    (cd "$BRK/src/backend" && "$PY" -B -m pytest tests/test_export_redaction.py -p no:cacheprovider -q -rsxX; echo "[$1] pytest-exit=$?")
  else
    echo "[$1] STOP: patch failed (anchor moved?); tests not run"
  fi
  test "$(git -C "$BRK" rev-parse --show-toplevel)" = "$BRK_TOP" || { echo "STOP: toplevel changed; not removing $BRK"; exit 1; }
  git -C "$WT" worktree remove --force "$BRK"   # forced: the disposable tree is dirty by design
)
PATCH='import sys
root = sys.argv[1]
def patch(rel, old, new):
    p = f"{root}/{rel}"; s = open(p).read()
    assert s.count(old) == 1, (rel, old[:60]); open(p, "w").write(s.replace(old, new))
'
brk B1-no-redaction <<EOF
$PATCH
patch("src/backend/api/export.py", "    summary_data = export_module.redact_summary_data(summary_data)\n", '    summary_data = {**summary_data, "redaction_count": 0}\n')
EOF
brk B2-standard-policy <<EOF
$PATCH
patch("src/backend/modules/export.py", 'matched (owner-gated gap O-3). The input dict is not mutated.\n        """\n        from modules.redaction import RedactionEngine\n\n        engine = RedactionEngine(policy_level="strict")', 'matched (owner-gated gap O-3). The input dict is not mutated.\n        """\n        from modules.redaction import RedactionEngine\n\n        engine = RedactionEngine(policy_level="standard")')
EOF
brk B3-no-download-audit <<EOF
$PATCH
patch("src/backend/api/export.py", '    # Log download\n    await audit_and_commit(\n        master_db,\n        log_export_event,\n        profile_id=session.profile_id,\n        export_type="summary_download",\n        details={"summary_id": summary_id, "format": format},\n    )\n', "")
EOF
brk B4-no-ownership-check <<EOF
$PATCH
patch("src/backend/api/export.py", '    if summary_data["profile_id"] != session.profile_id:\n        raise HTTPException(\n            status_code=status.HTTP_403_FORBIDDEN,\n            detail="Access denied to this summary"\n        )\n', "")
EOF
brk B5-gap-shapes-now-matched <<EOF
$PATCH
t = "src/backend/tests/test_export_redaction.py"
patch(t, '"patient_name:_jane_doe"', '"patient name: jane doe"')
patch(t, '"dob:_01/02/1980"', '"dob: 01/02/1980"')
patch(t, '"mrn:_a12345"', '"mrn: a12345"')
EOF
git -C "$WT" worktree list
git -C "$WT" status --short
```
Expected (each `[B*] pytest-exit=1`; all five were simulated on a scratch copy of the backend, Windows 3.13.7, with these results):

| Break | What fails |
|---|---|
| B1 | all 3 `test_hc_expr_001_doctor_summary_has_no_phi[*]` and `test_hc_expr_003_…` on `assert 'Jane' not in`; the real-PDF test too wherever it runs |
| B2 | 001×3 and 003 on `assert '01/02/1980' not in` (standard has no `dob`/`mrn` rules, which proves the test requires *strict*) |
| B3 | 003 on `assert ['doctor_summary'] == ['doctor_summary', 'summary_download']`, read from the persisted rows |
| B4 | 003 on `assert 200 == 403` |
| B5 | `test_hc_expr_001_known_gap_underscore_phi` as `[XPASS(strict)] O-3 known gap ...` |

Afterwards:
- each call printed its own unique `BRK=$HOME/w02-break.* toplevel=…` pair;
- `worktree list` shows no `w02-break.*` entry;
- `status --short` is empty.

A `STOP:` line means that call removed nothing it had not just created and verified.

A patch `AssertionError` (anchor not found) means the anchor moved: re-verify it, never loosen it. If any break leaves its test green, **STOP**. Fix the test in a follow-up test-only commit before the PR.

---

## Task 3: Collection dates under strict redaction (owner-gated, O-2)

**STOP until O-2 is signed.** Neither branch below adds a test ID or a collected item; each only extends HC-EXPR-001, so the collected-count slots stay unchanged.

**Files:** `src/backend/tests/test_export_redaction.py`. For (a), also `src/backend/modules/export.py:203` (main@40f590e).

### If O-2 = (a) ISO-8601

- [ ] **Step 1: Add the fidelity assertion.** In `test_hc_expr_001_doctor_summary_has_no_phi`, after the `clinical` loop:
  ```python
      # O-2 (a): collection dates render ISO-8601, which strict numeric_date
      # does not match (the visit-prep packet already does this, HC-PKT-004).
      assert "2024-03-15" in body
      assert "[DATE-REDACTED]" not in body
  ```
- [ ] **Step 2: Run it; it must fail**
  ```bash
  WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
  cd "$WT/src/backend" && "$PY" -B -m pytest tests/test_export_redaction.py -k "hc_expr_001_doctor" -p no:cacheprovider -q
  ```
  Expected: `3 failed`, with `AssertionError: assert '2024-03-15' in '...` (the date is currently `[DATE-REDACTED]`; prototype fact 4).
- [ ] **Step 3: Implement.** In `_format_abnormal_values`, change `.strftime("%m/%d/%Y")` to `.strftime("%Y-%m-%d")`. Nothing else changes. The overview's `%B %d, %Y` format is not matched by strict and stays as it is.
- [ ] **Step 4: Run to GREEN**
  ```bash
  WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
  cd "$WT/src/backend" && "$PY" -B -m pytest tests/test_export_redaction.py tests/test_export_api.py -p no:cacheprovider -q -rsxX
  ```
  Expected: 0 failed, and the known-gap test still `XFAIL`. `test_export_api.py` has no `%m/%d/%Y` assertion (grep 2026-09-27).
- [ ] **Step 5: Commit**
  ```bash
  WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; set -o pipefail
  cd "$WT"
  git add -- src/backend/modules/export.py src/backend/tests/test_export_redaction.py
  git diff --cached --name-only
  git commit -m "fix(export): render doctor-summary collection dates ISO-8601 so strict redaction keeps them (O-2a)

  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- src/backend/modules/export.py src/backend/tests/test_export_redaction.py
  ```
- [ ] **Step 6: Break it in a disposable worktree.** The `strftime` change is reverted there, never in `$WT`. Run this block unindented:

```bash
WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
(
BRK="$(mktemp -u -d "$HOME/w02-break.XXXXXX")"   # unique per run; -u: name only, nothing created
test ! -e "$BRK" || { echo "STOP: $BRK already exists"; exit 1; }
git -C "$WT" worktree add --detach "$BRK" HEAD || { echo "STOP: worktree add failed"; exit 1; }
BRK_TOP="$(git -C "$BRK" rev-parse --show-toplevel)" || exit 1
test "$BRK_TOP" = "$(realpath "$BRK")" && test "$BRK_TOP" != "$(realpath "$WT")" || { echo "STOP: $BRK is not its own worktree ($BRK_TOP)"; exit 1; }
echo "BRK=$BRK toplevel=$BRK_TOP"
"$PY" - "$BRK" <<'EOF'
import sys
p = f"{sys.argv[1]}/src/backend/modules/export.py"
s = open(p).read()
old = 'strftime("%Y-%m-%d") if obs.get("collected_at") else "Unknown date"'
assert s.count(old) == 1, "anchor moved; re-verify"
open(p, "w").write(s.replace(old, 'strftime("%m/%d/%Y") if obs.get("collected_at") else "Unknown date"'))
EOF
(cd "$BRK/src/backend" && "$PY" -B -m pytest tests/test_export_redaction.py -k "hc_expr_001_doctor" -p no:cacheprovider -q; echo "pytest-exit=$?")
test "$(git -C "$BRK" rev-parse --show-toplevel)" = "$BRK_TOP" || { echo "STOP: toplevel changed; not removing $BRK"; exit 1; }
git -C "$WT" worktree remove --force "$BRK"   # forced: the disposable tree is dirty by design
)
git -C "$WT" worktree list
git -C "$WT" status --short
```
Expected:
- a unique `BRK=… toplevel=…` pair;
- `3 failed`, with `assert '2024-03-15' in`;
- `pytest-exit=1`;
- no `w02-break.*` entry in `worktree list`;
- an empty status.

### If O-2 = (b) accept date loss

- [ ] **Step 1:** Add `assert "[DATE-REDACTED]" in body  # O-2 (b): owner accepted` after the `clinical` loop.
- [ ] **Step 2:** Run the file. Expected: 0 failed, 1 xfailed. This records the accepted behaviour; there is no product change.
- [ ] **Step 3:** Commit the test file alone, using the same pathspec form, with the message `fix(export): record owner-accepted date redaction in the doctor summary (O-2b)`.

---

## Task 4: Regression, whole-flow re-walk, end measurement

**Files:** none modified.

- [ ] **Step 1: Run the neighbour suites.** The untouched exporters must stay green.
  ```bash
  WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
  cd "$WT/src/backend" && find "$WT/src/backend" -name __pycache__ -type d -prune -exec rm -rf {} +
  "$PY" -m pytest tests/test_export_redaction.py tests/test_export_api.py tests/test_export_questions.py tests/test_export_trend_units.py tests/test_visit_prep_packet.py tests/test_fhir_export.py tests/test_rl_feedback.py tests/test_redaction.py tests/test_audit_phi_minimization.py -p no:cacheprovider -q -rsxX
  ```
  Expected: 0 failed and exactly 1 xfailed (the O-3 gap).
- [ ] **Step 2: Confirm the untouched files are untouched**
  ```bash
  WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; set -o pipefail
  git -C "$WT" diff --name-only origin/main...HEAD
  git -C "$WT" diff --exit-code origin/main...HEAD -- src/backend/modules/redaction.py src/backend/modules/fhir_export.py src/backend/modules/rl_dataset.py src/backend/tests/support/routes.py src/backend/core/audit.py src/backend/models/audit.py docs/compliance/data-privacy.md src/frontend && echo untouched
  git -C "$WT" diff -U0 origin/main...HEAD -- CLAUDE.md AGENT.md
  grep -n "RedactionEngine" "$WT/src/backend/modules/export.py"
  ```
  Expected:
  - The name list shows only the owned files: the test file, `modules/export.py`, `api/export.py`, `CLAUDE.md`, `AGENT.md`, and this plan once Task 5 is done.
  - `untouched`.
  - The `CLAUDE.md`/`AGENT.md` diff touches only `COLLECTED_SLOTS`, and no `PASS_SLOTS` (unless a named-environment pass count was measured and recorded).
  - `RedactionEngine` has 2 import lines (visit-prep and `redact_summary_data`) plus 2 `RedactionEngine(policy_level="strict")` lines. This is the C-REDACT-1 verify command.
- [ ] **Step 3: Re-walk the whole flow** (recurring-failures #2): generate → preview → text/html/pdf download → visit-prep download, which shares `render_html_summary` and `render_pdf_summary`.
  - Step 1 covers visit-prep (HC-PKT-012/013/016).
  - Confirm the shared renderers are unchanged:
    ```bash
    WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; set -o pipefail
    git -C "$WT" diff -U0 origin/main...HEAD -- src/backend/modules/export.py | { ! grep -n "render_html_summary\|render_pdf_summary"; } && echo renderers-untouched
    ```
    Expected: `renderers-untouched`.
  - Record the **patient-visible change** in the PR: the ExportPage preview and "Copy" now show `[NAME-REDACTED]`-style tokens wherever labelled PHI appeared. Add the date format if O-2 = (a).
- [ ] **Step 4: Boot check**
  ```bash
  WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
  cd "$WT/src/backend" && "$PY" -c "from main import app; print('ok')"
  ```
  Expected: `ok`.
- [ ] **Step 5: Measure the end tree**
  ```bash
  WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; PY="$HOME/venvs/asclexis-311/bin/python"; set -o pipefail
  cd "$WT/src/backend" && find "$WT/src/backend" -name __pycache__ -type d -prune -exec rm -rf {} +
  "$PY" -m pytest tests/ --collect-only -q -p no:cacheprovider 2>&1 | tail -1
  "$PY" -m pytest tests/ -p no:cacheprovider -q -rfEsxX 2>&1 | tail -30; echo "pytest-exit=$?"
  "$PY" -c "from weasyprint import HTML; HTML(string='<p>x</p>').write_pdf(); print('weasyprint-renders')" || echo weasyprint-cannot-render
  ```
  Expected:
  - collected = **N0 + 8**, matching `COLLECTED_SLOTS`;
  - failures ⊆ **F0**, each one named;
  - xfailed = X0 + 1;
  - skipped = S0 + 1 if the probe prints `weasyprint-cannot-render`, S0 + 0 if it renders.

  Record **ENV1** = interpreter plus embedding model present or absent (`test_api_rag_index_002b` PASSED or FAILED), and the passed count, as the one named-environment pass count this phase measured. If the probe renders, re-run the suite with `HC_REQUIRE_WEASYPRINT=1` and record that the real-PDF test PASSED.
- [ ] **Step 6: Frontend check** (no frontend file changed). On Windows, run:
  ```powershell
  cd C:\Users\DangT\Documents\GitHub\HealthCentral-w02\src\frontend; npx tsc --noEmit; npx vitest run src/__tests__/ExportPage.test.tsx
  ```
  If it is not run, write `UNMEASURED: vitest stalls under WSL on /mnt/c; no frontend diff` in the record.

---

## Task 5: Execution record and PR

**Files:** this plan file (append `## Execution record` at the end).

- [ ] **Step 1: Append the execution record.** Include:
  - the Task 0 start measurement: N0, F0, S0, X0, ENV0, WP0, the interpreter and the SHA;
  - the `COLLECTED_SLOTS` and `PASS_SLOTS` found;
  - the RED output of every test (Task 1 Step 7; Task 2 Steps 2, 5 and 9; Task 3 Step 2 and, under (a), Step 6);
  - the end measurement;
  - which O-2 branch was taken;
  - the skip reason.
- [ ] **Step 2: Lint the docs**
  ```bash
  WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; set -o pipefail
  cd "$WT" && python3 scripts/docs_lint.py && python3 scripts/generate_docs_index.py --check
  ```
  Expected: `Docs lint passed.` and exit 0.
- [ ] **Step 3: Commit**
  ```bash
  WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; set -o pipefail
  cd "$WT"
  git add -- docs/plans/2026-09-27-W02-doctor-summary-redaction.md
  git diff --cached --name-only
  git commit -m "docs: record W-2 doctor-summary redaction execution measurements

  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- docs/plans/2026-09-27-W02-doctor-summary-redaction.md
  ```
- [ ] **Step 4: Push and open the PR,** using the handoff §6 format:
  1. the start and end measurements;
  2. the new tests, with RED evidence for each;
  3. C-REDACT-1 / PRIV-04, plus the proposed matrix change;
  4. the explicit list of changed files;
  5. the status of O-1…O-4;
  6. **Flags:**
     - `PASS_SLOTS` in `CLAUDE.md`/`AGENT.md` were not re-measured by W-2. They are stale because of the strict xfail and the environment-dependent real-PDF skip. Give ENV1's measured pass count as the only named-environment figure.
     - Real-PDF render coverage in CI is **UNMEASURED** unless the CI log shows `test_hc_expr_001_real_pdf_extracted_text_has_no_phi PASSED`. CI does not set `HC_REQUIRE_WEASYPRINT=1`.

  The PR text states the claim as "labelled name/DOB/MRN redacted in text/html/pdf" and names the O-3 gap and its xfail. It must never say "PHI-free". End it with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
- [ ] **Step 5: Pre-merge gate.** **Do not merge, and ask the owner not to merge, until S-3 (O-3) and S-6 are signed.** An unsigned S-3 keeps the PR open.

---

## Measured acceptance

| Check | Command | Expected |
|---|---|---|
| New tests | `"$PY" -m pytest tests/test_export_redaction.py -q -rsxX` | 8 collected: 001×3, 001-real-pdf, 001-known-gap, 002×2, 003. Results: 0 failed, 1 xfailed. The real-PDF test passes or skips, with the reason named |
| Collected | `"$PY" -m pytest tests/ --collect-only -q` | N0 + 8. The `CLAUDE.md`/`AGENT.md` **collected** slots equal it at HEAD. Pass slots are unchanged and flagged in the PR |
| Failures | full suite | ⊆ F0, each one named; xfailed = X0 + 1 |
| RED evidence | Task 1 Step 7; Task 2 Steps 2, 5 (require-flag) and 9 (B1–B5); Task 3 Steps 2 and 6 | recorded verbatim. Every break ran in the disposable `$BRK`, and `git -C "$WT" status --short` stayed empty |
| `redaction.py` untouched | `git -C "$WT" diff --exit-code origin/main...HEAD -- src/backend/modules/redaction.py` | exit 0 |
| CSV/JSON byte-stable | HC-EXPR-002 | passes; the baseline commit precedes the fix commit in `git log` |
| Audit persists | HC-EXPR-003 | 2 `export.create` rows (`doctor_summary`, `summary_download`) with no PHI; the 403 writes none |
| Known gap visible | `test_hc_expr_001_known_gap_underscore_phi` | `XFAIL`; an `XPASS(strict)` fails the suite |
| Real PDF in CI | PR CI log | **UNMEASURED.** CI does not set `HC_REQUIRE_WEASYPRINT=1` and this plan does not edit `ci.yml`, so a Pango-less runner SKIPs the test (the fixture probes `write_pdf()`). Only a CI `PASSED` counts as coverage |
| Real PDF in D9 venv | Task 0 Step 6 (WP0) and Task 4 Step 5 | If WP0 = renders: PASSED under `HC_REQUIRE_WEASYPRINT=1`. If it cannot render: SKIPPED with the reason, plus the Task 2 Step 5 proof that the flag makes it FAIL |

## Stop gates

1. The worktree is not post-P1, or the D9 venv, W-10 or P5 is missing (Task 0 Steps 1–2).
2. `modules/redaction.py` differs from main@40f590e, or lacks `strict`, or any step appears to need an edit there, including an O-3 fix.
3. The start `COLLECTED_SLOTS` figure ≠ N0 (Task 0 Step 6).
4. The baseline re-capture differs from the reference without an explained earlier commit (Task 1 Step 3).
5. A Task 2 Step 2 test marked FAILED passes before the implementation, or the known-gap test XPASSes after it.
6. O-2 is unsigned when Task 3 is reached.
7. **S-3 (O-3) is unsigned at merge time. The PR stays open.**
8. Any failure not in F0, or any failure in the Task 4 Step 1 neighbour suites.
9. A change would touch `CLAUDE.md`/`AGENT.md` beyond `COLLECTED_SLOTS` (or a pass slot without a named-environment measurement), `data-privacy.md`, the frontend, `/export/questions`, visit-prep/FHIR/RL code, `tests/support/routes.py`, `core/audit.py` or a threshold.
10. An HC-EXPR ID collision (Task 0 Step 4).
11. A break-it step would need an edit in `$WT` instead of `$BRK`, or any `STOP:` guard fires: the path exists, `worktree add` fails, or the toplevel mismatches. Remove nothing by hand that the block did not create.

## Rollback

There is no schema, migration or persisted artifact. `_summary_store` is in-memory.

Pick the case that matches where the work has got to:

1. **Before push:** abandon the branch and remove the worktree. Ask the owner before deleting the branch.
   ```bash
   WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; set -o pipefail
   git -C /mnt/c/Users/DangT/Documents/GitHub/HealthCentral worktree remove "$WT"
   ```
2. **After push, PR open, not merged:** close the PR and delete the remote branch.
   ```bash
   WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; set -o pipefail
   cd "$WT" && gh pr close <pr-number> --delete-branch
   ```
3. **After merge:** revert on main through a new branch and PR. Humans merge; never push to main directly.
   ```bash
   WT=/mnt/c/Users/DangT/Documents/GitHub/HealthCentral-w02; set -o pipefail
   git -C "$WT" fetch origin
   git -C "$WT" switch -c revert/w02 origin/main
   git -C "$WT" revert <task3-commit> <task2-commit>   # restores the unredacted doctor summary and the N0+2 collected slots
   git -C "$WT" revert <task1-commit>                  # optional: removes the CSV/JSON pin and restores the N0 collected slots
   git -C "$WT" push -u origin revert/w02
   ```
   Then open a PR, and **STOP** for the owner's merge.

Each revert restores the collected slots together with the tests it removes, so the baseline never goes stale. A restart clears any summaries generated under either behaviour. If W-2 is reverted, PRIV-04 returns to **contradicted** for the doctor summary.

## Owner sign-offs (unsigned)

- [ ] **S-1 / O-1.** Choose one:
  - [ ] The doctor summary stays unidentified (no name/DOB/MRN).
  - [ ] The owner wants an identifier, which needs a new decision.

  Signed: ________ Date: ________
- [ ] **S-2 / O-2** (blocks Task 3). Choose one:
  - [ ] (a) ISO-8601 dates.
  - [ ] (b) Accept `[DATE-REDACTED]`.

  Signed: ________ Date: ________
- [ ] **S-3 / O-3** (**pre-merge gate**). Choose one:
  - [ ] (a) Accept the documented residual gap (underscore-joined identifiers are not matched; pinned by the strict xfail).
  - [ ] (b) Separately approve a `redaction.py` change under its own plan.

  Signed: ________ Date: ________
- [ ] **S-4 / O-4** (canonical gate **EXPORT-QUESTIONS**, shared with P08 R11). Choose one:
  - [ ] `/export/questions` and ExportPage "Copy" stay outside W-2.
  - [ ] Open a separate item.

  Signed: ________ Date: ________
- [ ] **S-5** (canonical gate **P0-D-MOOT**). P0-D is moot for W-2, because D3 is decided. Signed (owner or orchestrator): ________ Date: ________
- [ ] **S-6.** Merge approval for the W-2 PR (only after S-3). Signed: ________ Date: ________

## Commit plan

| # | Task | Pathspecs (explicit; `git commit … -- <paths>`) | Message |
|---|---|---|---|
| 1 | 1 | `src/backend/tests/test_export_redaction.py CLAUDE.md AGENT.md` | `fix(export): pin CSV/JSON export bytes before doctor-summary redaction (HC-EXPR-002)` |
| 2 | 2 | `src/backend/modules/export.py src/backend/api/export.py src/backend/tests/test_export_redaction.py CLAUDE.md AGENT.md` | `fix(export): strict-redact the doctor summary before it is stored or rendered (D3)` |
| 3 | 3 | (a) `src/backend/modules/export.py src/backend/tests/test_export_redaction.py`; (b) the test file only | `fix(export): … (O-2a)` or `(O-2b)`. No collection change, so no count edit |
| 4 | 5 | `docs/plans/2026-09-27-W02-doctor-summary-redaction.md` | `docs: record W-2 doctor-summary redaction execution measurements` |

Before every commit, `git diff --cached --name-only` must list exactly the pathspecs. Never use `git add -A`, `git add .` or `git reset`. Every message ends with the `Co-Authored-By` line. Commits 1 and 2 change the collected count, so each carries its own collected-slot update. Pass slots are not touched.

## Recurring-failures recheck ([recurring-failures.md](../agentic/recurring-failures.md))

| # | Applies | Concrete recheck in this plan |
|---|---|---|
| 1 Green suite that could not fail | **yes** | Every test is broken on purpose, in a disposable worktree: Task 1 Step 7; Task 2 Step 9 (B1–B5); Task 3 Step 6. The real-PDF skip cannot hide: the fixture probes `write_pdf()`, and `HC_REQUIRE_WEASYPRINT=1` turns the skip into a failure (Task 2 Step 5). Routes are tested over HTTP via `route_client`. Audit is asserted as persisted rows, not a spy. Positive assertions (redaction tokens present, clinical values present, `glucose` extracted from the real PDF) stop a blanked output from passing. HC-EXPR-002 is honestly GREEN-first; its RED comes from the break step. The known gap is a strict xfail, visible rather than hidden |
| 2 A fix that creates the next bug one layer over | **yes** | Task 4 Step 3 re-walks generate → preview → 3 downloads → the visit-prep renderers they share. The patient-visible preview/Copy change is recorded. G-C1 ordering is stated |
| 3 Figures asserted instead of measured | **yes** | N0/F0/S0/X0 are measured in Task 0 and the end state in Task 4. Count lines are updated from measured collection in the same commit. The prototype numbers in this plan are labelled as Windows 3.13.7 / main@40f590e context |
| 4 Environment-dependent results written as absolutes | **yes** | The real-PDF test passes or skips depending on a real `write_pdf()` probe. The +8 collected count is the invariant and the only figure written into `CLAUDE.md`/`AGENT.md`. Pass slots are left alone and flagged; the one pass count reported names its environment (ENV1). CI PDF coverage is UNMEASURED unless the log shows PASSED |
| 5 Contaminated tree | **yes** | A dedicated worktree at an absolute `$WT`, and explicit pathspecs with `git commit -- <paths>`. Docs gates run in the worktree |
| 6 Documented commands nobody ran | **yes** | Every block carries the preamble and absolute `cd`s, so it runs exactly as written. `pipefail` guards the pipes |
| 7 SQL three-valued logic | no | No product SQL changes. The fake profile DB ignores queries. The test master DB only inserts and selects all rows |
| 8 Stale guidance treated as authority | **yes** | `data-privacy.md:173-174` ("Every other export path passes through `modules/redaction.py`") is false today (PRIV-04), so it is not cited as evidence. W-10 rewrites it |

## Found while planning (out of W-2 scope; for the orchestrator)

1. **The text format is rendered in the route, not the module.** The contract cites `modules/export.py:82,223,267,290,358` for the doctor summary, but the text download is built in `api/export.py:551-604` (main@40f590e). A fix confined to the renderers in `modules/export.py` would have missed it; this plan redacts at the store instead.
2. **The P0-D brief is absent**, although the program graph (`:120`) lists it as a W-2 input (sign-off S-5).
3. **Two plans claim the same wording.** P4 (program `:195` @5d56557; now `:302` "Moved to W-10") and W-10 (handoff `:147`) both claim the D3 wording in `data-privacy.md:173-174`; one owner is needed.
4. **The doctor summary includes unverified observations.** `api/export.py:130-174` has no `user_verified` filter, while visit-prep excludes them. D4 covers trends and legacy RAG only, so this is not addressed here.
5. **WeasyPrint without Pango returns the wrong status.** `render_pdf_summary` catches only `ImportError` (`modules/export.py:371-377`), but WeasyPrint installed without Pango raises `OSError`, which surfaces as HTTP 500 rather than 501. The real-PDF test's fixture probes `write_pdf()` before the request and skips on either error, or fails under `HC_REQUIRE_WEASYPRINT=1`. The product's 500-vs-501 handling (`modules/export.py:371-380`) stays out of scope.
6. **Branch B's count lines disagree with each other.** `CLAUDE.md:30` says 1288 collected, while `AGENT.md:76` says 1269 (B@7b2ff1f, `git show`). P1 must reconcile this, and Task 0 Step 6 stops if the start collected figure ≠ N0.
7. **CI never renders a real PDF under a hard requirement.** CI does not set `HC_REQUIRE_WEASYPRINT=1` or install Pango. Whoever next owns `ci.yml` (G-B4) decides whether it should; until then, CI PDF-render coverage is UNMEASURED.

Back to: [implementation program](../capstone-report/implementation-program.md) · [owner decisions](../capstone-report/owner-decisions-2026-09-27.md) · [handoff §5](../../audit/2026-09-25/handoff-2026-09-27-execution.md)
