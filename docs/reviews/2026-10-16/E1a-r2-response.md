# E-1a Plan — Codex Round 2 Response (rev 3)

**Last Updated:** 2026-10-16
**Owner:** repository owner
**Status:** Applied to [E-1a plan](../../plans/2026-10-16-E1a-redaction-underscore-phi.md) rev 3. Owner answer recorded in the plan: "Yes, rev 3 same terms (Recommended)".
**Refresh Trigger:** a further Codex round on the E-1a plan.

Run: `codex exec -s read-only -C <hc-e-1a> -o /tmp/claude-1000/e1a-r2-codex.txt "<prompt>" </dev/null` (exit 0). Verdict: **REVISE**. Findings: 0 BLOCKER, 6 MAJOR, 1 MINOR. Prompt: [E1a-r2-prompt.md](E1a-r2-prompt.md); output: `E1a-r2-codex.txt`.

| # | Sev | Finding | Verified? | Action |
|---|---|---|---|---|
| 1 | MAJOR | Task 2 says "append" though PR #108 already has both rules | Yes | Task 2 now says: on PR #108 do not append; replace the `underscore_labelled_id` comment and pattern byte for byte |
| 2 | MAJOR | Task 1 adds a class that already exists; a second same-named class shadows the first | Yes (Python rebinds the name; pytest collects only the last) | Rev 3 note: extend the existing class and lists in place |
| 3 | MAJOR | Collected delta is 42, not 40 | Yes: 23+1+1+13+1+1+1+1 = 42 | Task 5, Files and Acceptance rows 3 and 7 say 42 |
| 4 | MAJOR | Acceptance row 1 says 11 failed; rev 3 RED is 12 | Yes | Row 1 lists both: rev 2 on `main` 11, rev 3 on PR #108 12 |
| 5 | MAJOR | HC-REDACT-001 checks one substring; `josé_` could survive | Yes in principle | Added `assert result.text.removeprefix("full_") == "[ID-REDACTED]"`. Prototype: all 23 rows pass it on rev 3; the 12 rev 2 rows also pass it on the rev 2 rule, so RED stays 12 |
| 6 | MINOR | Mutant 1 example `medical_record_#` and mutant 2 example `medical_record_no.:_44-ab` still redact under the mutation | Yes, prototype | Mutant lists replaced with measured fail sets (mutant 1: 8 rows; mutant 2: 7 rows; mutant 5: 008 at 6.7 s + 3 `#` rows) |
| 7 | MAJOR | Over-redaction of `mrn_status_ok`, `medical_record_review` exceeds approved scope | Partly. `mrn_status_ok` was already redacted by rev 2 and accepted as conservative in PR #108 round 1. `medical_record_review` is new, from the bare `medical_record` label that `medical_record_#:_` needs (an approved separator case) | **Not narrowed**: over-redaction only removes non-PHI text from strict output, which is the conservative side (CLAUDE.md §1). Made visible instead: the plan's accepted over-redaction list and the Owner gate now name both, and the PR body must repeat them for the owner's merge check |
