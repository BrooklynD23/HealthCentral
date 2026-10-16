# E-1a: Strict Redaction for Underscore-Joined Identifiers (O-3)

**Last Updated:** 2026-10-16 (rev 2: Codex r1 applied)
**Owner:** repository owner
**Status:** PROPOSED (L1 planner). No owner approval is recorded here. `src/backend/modules/redaction.py` is ask-first (`CLAUDE.md` §1); the diff this plan produces needs the owner's own yes before merge (see [Owner gate](#owner-gate)).
**Refresh Trigger:** any commit to `src/backend/modules/redaction.py`, `src/backend/tests/test_redaction.py`, `src/backend/modules/normalize.py` (`ANALYTE_SYNONYMS` or the unknown-analyte branch) or `src/backend/modules/export.py` (`_format_abnormal_values`); E-1 merging; an owner answer that changes S-3 + S-6.

**Queue row:** [queue.md](2026-10-15-build-program/queue.md) E-1a. **Sources:** [W-2 plan](2026-09-27-W02-doctor-summary-redaction.md) fact 6 (`:182`) and O-3 (`:203-209`), the strict-xfail test text (`:831-845`), `GAP_ROWS` (`:745-749`); [lane E](2026-10-15-build-program/lane-E-privacy-gates-ci.md) §5 (`:162`); [owner-decisions](../capstone-report/owner-decisions-2026-09-27.md) row "S-3 + S-6" (`:176`): **"Close the gap first"** — "Fix redaction.py for underscore-joined identifiers before W-2 merges. That edit needs your yes on its own diff."

## Goal

Strict `RedactionEngine` matches the underscore-joined labelled shapes that unknown analytes are stored in, without redacting normal analyte names. Standard and minimal levels do not change.

## Why strict misses them today (verified against `origin/main` @ `d6475cf`)

Unknown analytes are stored as `raw.lower().strip().replace(" ", "_")` (`modules/normalize.py:279-284`). So `Patient Name: Jane Doe` becomes `patient_name:_jane_doe`, and the doctor summary renders it verbatim (`modules/export.py:205`: `• {analyte_canonical}: {value} ...`).

| Shape | Rule that should fire | Why it does not |
|---|---|---|
| `patient_name:_jane_doe` | `name_context` (`redaction.py:81-89`) | `_` is a word character: no `\b` before `name`, and the separator `\s*:?\s*` cannot consume `_` |
| `dob:_01/02/1980` | `dob` (`:90-98`), `numeric_date` (`:122-127`) | separator cannot consume `_`; no `\b` between `_` and `0` |
| `mrn:_a12345` | `mrn` (`:114-121`) | separator `\s*[:#]?\s*` cannot consume `_` |

## Design: two additive strict-only rules

Same precedent as RL-REDACT-001 (`redaction.py:108-113`): add rules, change no existing rule or level. Rollback is deleting them.

Append to `_RULES` after `numeric_date`:

```python
    # E-1a (O-3, strict only, additive): underscore-joined labelled identifiers,
    # the shape unknown analytes are stored in (normalize.py: spaces -> "_").
    # Specific labels may omit the colon; bare "patient"/"name" need one, so
    # analyte-like tokens such as "name_of_test" or "patient_count_3" survive.
    RedactionRule(
        name="underscore_labelled_id",
        pattern=re.compile(
            r"(?i)(?<![^\W_])"
            r"(?:(?:patient_name|dob|date_of_birth|birth_?date|mrn|medical_record_(?:number|no))_*:?"
            r"|(?:patient|name)_*:)"
            r"_+[^\W_][\w/.\-]*"
        ),
        replacement="[ID-REDACTED]",
        policy_levels=frozenset({"strict"}),
    ),
    RedactionRule(
        name="underscore_numeric_date",
        pattern=re.compile(r"(?<=_)\d{1,2}[/-]\d{1,2}[/-]\d{2,4}(?!\d)"),
        replacement="[DATE-REDACTED]",
        policy_levels=frozenset({"strict"}),
    ),
```

Design notes:

1. **Label, then at least one `_`.** The rule only fires on the underscore shape. Spaced shapes stay with the existing rules.
2. **Value is Unicode-aware and stops at `:`, `<`, whitespace.** `\w` matches accented letters, so `patient_name:_josé_álvarez` is fully replaced (an ASCII-only class left `é_álvarez`; Codex r1). In `• patient_name:_jane_doe: 1.0 ...` it consumes `jane_doe` and keeps `: 1.0`; in HTML `<td>patient_name:_jane_doe</td>` the tags survive.
3. **Leading `(?<![^\W_])` (no letter or digit before) admits `_`.** `full_name:_jane_doe` becomes `full_[ID-REDACTED]`.
4. **ISO dates are untouched.** `underscore_numeric_date` is `d{1,2}`-first, like `numeric_date`, so `hba1c_2025-05-01` and `2024-03-15` never match (`redaction.py:110-113`).
5. **Email is unaffected.** `jane_doe@example.com` is still fully replaced by `email`, which runs first.

### Prototype evidence (scratchpad only, not committed)

The two rules above were passed as `RedactionEngine("strict", rules=_RULES + new)` under `~/venvs/asclexis-311/bin/python` on this worktree:

```
'• patient_name:_jane_doe: 1.0  (ref: 0.0-0.5) [H] - 2024-03-15' -> '• [ID-REDACTED]: 1.0  (ref: 0.0-0.5) [H] - 2024-03-15'
'<td>patient_name:_jane_doe</td>' -> '<td>[ID-REDACTED]</td>'
'dob:_01/02/1980: 1.0' -> '[ID-REDACTED]: 1.0'
'mrn:_a12345: 1.0' -> '[ID-REDACTED]: 1.0'
'admitted_03/15/1985' -> 'admitted_[DATE-REDACTED]'
'name_of_test' -> 'name_of_test'
'patient_count_3' -> 'patient_count_3'
132 names; FP: []      # every NormalizeModule.ANALYTE_SYNONYMS key and synonym, underscore form
```

The Task 1 test code was also run against the unmodified engine and the prototype (scratchpad copy, rules patched in): **11 failed, 14 passed** before, **25 passed** after (r1 revision, with the Unicode case). Both Task 3 mutants failed HC-REDACT-004 as specified (`name_of_test`, `patient_count_3`; `hba1c_2025-05-01`).

A first draft let bare `patient_`/`name_` match without a colon. It redacted `name_of_test` and `patient_count_3`. That is why bare labels need `:`, and why HC-REDACT-004 pins both strings.

### False-positive risks and their tests

| Risk | Example | Guard |
|---|---|---|
| Analyte name contains a label word | `name_of_test`, `patient_count_3` | colon required for bare labels; HC-REDACT-004 |
| Label is a prefix of a longer word | `mrna_level` | `mrn` must be followed by `_`/`:`; HC-REDACT-004 |
| Title-like prefixes | `ms_afp` (maternal serum AFP) | titles `mr/mrs/ms/dr` are **not** labels here; HC-REDACT-004 |
| Normal multi-word analytes | `vitamin_d`, `ldl_cholesterol`, `hemoglobin_a1c`, `25_hydroxy_vitamin_d`, `t4_free`, `glucose_fasting` | HC-REDACT-004 (explicit) and HC-REDACT-005 (all 132 known names) |
| ISO collection date after `_` | `hba1c_2025-05-01` | `d{1,2}`-first shape; HC-REDACT-004 |

### Residual gaps (stated, not fixed)

Strict stays pattern-based. After E-1a it still does **not** match:

1. Underscore names with a title, not a label: `mr_john_smith`, `dr_jane_doe`. Adding titles would hit `ms_afp`.
2. Unlabelled underscore names or IDs: `jane_doe`, `a12345`.
3. Bare `name_`/`patient_` without a colon: `patient_name` is covered, `name_jane_doe` is not.
4. Hyphen- or dot-joined labels: `patient-name-jane-doe`.
5. Free text the existing spaced rules already miss (see W-2 `:1042`).

## Ordering with E-1 (read before scheduling)

The owner said the fix lands **before W-2 merges** (`owner-decisions:176`; queue `:23`: "E-1 merge now waits on a new item E-1a"). So E-1a must **not** wait for E-1 to merge, or E-1 and E-1a block each other.

- **E-1a depends on nothing.** Its PR edits `redaction.py` and `test_redaction.py` only. Both exist on `origin/main` today.
- **The O-3 strict xfail lives in E-1's file** (`tests/test_export_redaction.py`, created by E-1, not on `main`). Whichever PR merges **second** removes it (Task 4):
  - **(A) E-1a merges first** (the owner's order). E-1 rebases on `main`; `test_hc_expr_001_known_gap_underscore_phi` reports `XPASS(strict)` and fails, which is the trigger. E-1 removes the marker in its own file.
  - **(B) E-1 merges first** (only if the owner reverses S-3). E-1a rebases and removes the marker in the same PR, adding `be/tests/test_export_redaction.py` to its file list.

## Tasks

Work from `WT=$(git rev-parse --show-toplevel)`, `cd "$WT/src/backend"`. Every pytest call goes through this shell function (define it once per shell):

```bash
pyt() { "$WT/scripts/pyslot.sh" env HF_HUB_OFFLINE=1 "$HOME/venvs/asclexis-311/bin/python" -m pytest -p no:cacheprovider "$@"; }
```

### Task 0: Start measurement

1. `git fetch origin && git merge-base --is-ancestor origin/main HEAD` (fresh branch from `origin/main`).
2. Collected count N0: `pyt tests/ --collect-only -q | tail -1`. Compare with the `CLAUDE.md` slot. A mismatch is reported, never fixed (SLOT-RULE-2, `contracts.md:131-142`).
3. Baseline on unmodified code: run the Acceptance row 3, row 4 and row 6 commands and record pass/fail/skip counts and every failing test id. Rows 3, 4 and 6 compare against these.

### Task 1: RED tests in `src/backend/tests/test_redaction.py`

Add one class after `TestNumericDateRedaction`. Test ids follow the repo's `HC-XXX-NNN` style.

```python
# ---------------------------------------------------------------------------
# Underscore-joined identifiers (E-1a / W-2 O-3, strict only)
# ---------------------------------------------------------------------------

UNDERSCORE_PHI = [
    ("patient_name:_jane_doe", "jane"),
    ("dob:_01/02/1980", "01/02/1980"),
    ("mrn:_a12345", "a12345"),
    ("patient_name_jane_doe", "jane"),
    ("date_of_birth:_1/2/80", "1/2/80"),
    ("medical_record_number:_44-ab-9921", "44-ab-9921"),
    ("full_name:_jane_doe", "jane"),
    ("PATIENT_NAME:_JANE_DOE", "JANE"),
    ("patient_name:_josé_álvarez", "álvarez"),
]

ANALYTE_LIKE = [
    "vitamin_d", "ldl_cholesterol", "hemoglobin_a1c", "25_hydroxy_vitamin_d",
    "t4_free", "glucose_fasting", "ms_afp", "mrna_level",
    "name_of_test", "patient_count_3", "hba1c_2025-05-01",
]


class TestUnderscoreJoinedRedaction:
    @pytest.mark.parametrize("text,secret", UNDERSCORE_PHI)
    def test_hc_redact_001_underscore_labelled_shapes_redacted_strict(self, text, secret):
        """HC-REDACT-001: labelled underscore-joined name/DOB/MRN are redacted."""
        result = _engine("strict").redact(text)
        assert secret not in result.text
        assert "[ID-REDACTED]" in result.text

    def test_hc_redact_002_underscore_numeric_date_redacted_strict(self):
        """HC-REDACT-002: an unlabelled d/m/y date after '_' is redacted."""
        result = _engine("strict").redact("admitted_03/15/1985")
        assert "03/15/1985" not in result.text
        assert "[DATE-REDACTED]" in result.text

    def test_hc_redact_003_rendered_summary_line_keeps_value_and_markup(self):
        """HC-REDACT-003: only the identifier goes; value, ISO date and tags stay."""
        line = "• patient_name:_jane_doe: 1.0  (ref: 0.0-0.5) [H] - 2024-03-15"
        assert _engine("strict").redact(line).text == (
            "• [ID-REDACTED]: 1.0  (ref: 0.0-0.5) [H] - 2024-03-15"
        )
        html = "<td>mrn:_a12345</td>"
        assert _engine("strict").redact(html).text == "<td>[ID-REDACTED]</td>"

    @pytest.mark.parametrize("name", ANALYTE_LIKE)
    def test_hc_redact_004_analyte_like_tokens_not_redacted_strict(self, name):
        """HC-REDACT-004: no over-redaction of analyte-shaped tokens."""
        result = _engine("strict").redact(name)
        assert result.text == name
        assert result.redacted_count == 0

    def test_hc_redact_005_all_known_analyte_names_unchanged_strict(self):
        """HC-REDACT-005: every known canonical name and synonym, underscore form."""
        from modules.normalize import NormalizeModule

        names = set()
        for canonical, synonyms in NormalizeModule.ANALYTE_SYNONYMS.items():
            names.add(canonical)
            names.update(synonyms)
        assert len(names) >= 100  # the list loaded; an empty loop proves nothing
        hits = [n for n in sorted(names)
                if _engine("strict").redact(n.replace(" ", "_")).redacted_count]
        assert hits == []

    def test_hc_redact_006_underscore_rules_strict_only(self):
        """HC-REDACT-006: standard and minimal are unchanged."""
        text = "patient_name:_jane_doe mrn:_a12345 admitted_03/15/1985"
        for level in ("standard", "minimal"):
            assert _engine(level).redact(text).text == text

    def test_hc_redact_007_underscore_email_still_fully_redacted(self):
        """HC-REDACT-007: underscore in an email local part is not split."""
        result = _engine("strict").redact("contact jane_doe@example.com")
        assert "jane" not in result.text
        assert "[EMAIL-REDACTED]" in result.text
```

Run `pyt tests/test_redaction.py -q -rfE`. **RED expectation:** 11 failed (001 ×9, 002, 003), the rest passed. 004–007 are guards that pass before and after; Task 3 proves they can fail.

### Task 2: GREEN — edit `src/backend/modules/redaction.py`

Append the two rules from [Design](#design-two-additive-strict-only-rules) after `numeric_date` (`:122-127`). No other line changes. Run `pyt tests/test_redaction.py -q`: 0 failed.

### Task 3: Prove the guards can fail (not committed)

1. Make the colon optional for bare labels (`(?:patient|name)_*:` → `(?:patient|name)_*:?`). Run HC-REDACT-004: it must fail on `name_of_test` and `patient_count_3`. Revert.
2. Change `underscore_numeric_date` to `(?<=_)\d{1,4}[/-]\d{1,2}[/-]\d{2,4}`. HC-REDACT-004 must fail on `hba1c_2025-05-01`. Revert.
3. Paste both failing outputs into the PR body. `git diff --stat` after reverting must show only Task 1 and Task 2 files.

### Task 4: Remove the O-3 strict xfail (in whichever PR merges second; see Ordering)

In `src/backend/tests/test_export_redaction.py`:

1. Delete the `@pytest.mark.xfail(strict=True, reason="O-3 known gap ...")` decorator above `test_hc_expr_001_known_gap_underscore_phi` (W-2 plan `:831-838`).
2. Rename the test to `test_hc_expr_001_underscore_phi_redacted` and its docstring to `"""HC-EXPR-001 (underscore shape): closed by E-1a."""`. Keep `GAP_ROWS` and the three asserts unchanged.
3. Run `pyt tests/test_export_redaction.py -q -rsxX`. Expected: **0 xfailed, 0 xpassed**, 0 failed. Before step 1 the same run must show `XPASS(strict)` for that test — that is the proof the fix reached the export path.

### Task 5: Docs and collected count

1. `redaction.py` module docstring: no change. The rule comment above is the only prose in code.
2. E-1a adds 25 collected tests (001 ×9, 002, 003, 004 ×11, 005, 006, 007). The PR **never edits** the `CLAUDE.md`/`AGENT.md` slots (SLOT-RULE-2, `contracts.md:133`). It pastes the measured `--collect-only` line on its head and the delta from the slot into the PR body; L0's post-merge batch updates the slots.
3. Do not edit `docs/capstone-report/specs-compliance-matrix.md` here (other items own it). Hand the PRIV-04 gap-column wording below to L0's post-merge batch.

## Doc claims

Never write "PHI-free", "all PHI" or "fully redacted". The allowed claim, for the PR body, the commit and the PRIV-04 gap column:

> Strict redaction now also matches underscore-joined **labelled** identifiers (`patient_name`, `patient:`, `name:`, `dob`, `date_of_birth`, `birth_date`, `mrn`, `medical_record_number`, followed by `_`) and `d/m/y` dates directly after `_`. Strict is still pattern-based: titled (`mr_`, `dr_`), unlabelled and hyphen-joined identifiers are not matched.

## Files

| File | Change |
|---|---|
| `src/backend/modules/redaction.py` | +2 rules appended to `_RULES` (ask-first) |
| `src/backend/tests/test_redaction.py` | +1 class, 7 test functions, 25 collected |
| `src/backend/tests/test_export_redaction.py` | Task 4, **only** under ordering (B) |
| `docs/INDEX.md`, `docs/_link_graph.json` | regenerated only if a doc changes (SLOT-RULE-2a) |

## Acceptance

| # | Check | Command (from `src/backend`) | Expected |
|---|---|---|---|
| 1 | RED recorded | `pyt tests/test_redaction.py -q -rfE` before Task 2 | 11 failed, all in `TestUnderscoreJoinedRedaction` 001–003 |
| 2 | GREEN | `pyt tests/test_redaction.py -q` | 0 failed |
| 3 | Safety suites | `pyt tests/test_redaction.py tests/test_interpret_safety_adversarial.py tests/test_phase4_ai_safety.py tests/agent/test_s3_guardrails.py -q` | 0 failed; counts equal the Task 0 baseline plus 25 passed |
| 4 | Other strict callers | `pyt tests/test_fhir_export.py tests/test_visit_prep_packet.py tests/test_rl_feedback.py tests/test_rl_export_prompt_snapshot.py tests/test_external_runner_hardening.py tests/agent/test_s4_phi_gate.py tests/agent/test_s6_evals.py -q` | same pass/fail as Task 0 (strict is also used by `fhir_export.py:58`, `export.py:637`, `rl_dataset.py`, `external_runner.py:279` and the eval PHI scorer `agent/eval/scorer.py:186`) |
| 5 | Guards can fail | Task 3 | both mutants fail HC-REDACT-004; outputs in PR body |
| 6 | Full suite | `pyt tests/ -q` | failures ⊆ Task 0 failures, each named |
| 7 | Collected | `--collect-only` (Task 0 step 2) | N0 + 25, pasted in the PR body (no slot edit) |
| 8 | Export path (Task 4) | `pyt tests/test_export_redaction.py -q -rsxX` | after Task 4: 0 xfailed, 0 xpassed |

Report each command with its actual tail output. A skipped check is named with its reason.

## Owner gate

- `modules/redaction.py` is ask-first (`CLAUDE.md` §1). S-3 answered "Close the gap first" approves the **work**, not the diff: "That edit needs your yes on its own diff."
- **Editing vs merging.** CLAUDE.md §1 says ask before touching the file. The owner's row-176 answer is the ask for the *edit*: "Fix redaction.py for underscore-joined identifiers". Before Task 2 the implementer quotes that row in the PR body as the authority to edit. The edit is limited to the two rules in this plan, and anything beyond them needs a new ask. The *merge* needs a second yes on the exact final diff (Codex r1 MAJOR, partly accepted; see `docs/reviews/2026-10-16/E1a-r1-response.md`).
- The PR opens and **stays draft** until the owner replies yes on the exact `redaction.py` diff. L0 records that yes as a new owner-decisions row (for example `E1A-DIFF`) before anyone marks the PR ready or merges it.
- Owner question: "May E-1a merge this `redaction.py` diff — two strict-only rules that redact underscore-joined labelled name/DOB/MRN values (`patient_name:_jane_doe` and accented names such as `patient_name:_josé_álvarez` → `[ID-REDACTED]`) and `d/m/y` dates after `_`, leaving titled and unlabelled shapes as a stated residual gap?"

## Rollback

1. `git revert <E-1a merge commit>`. Both rules and their tests go together; no data, migration or config is involved.
2. If E-1 already removed its xfail (ordering A), restore the `@pytest.mark.xfail(strict=True, ...)` marker in `tests/test_export_redaction.py` in the same revert PR, or E-1's test fails.
3. The PRIV-04 gap column goes back to "underscore-joined identifiers are not matched".
