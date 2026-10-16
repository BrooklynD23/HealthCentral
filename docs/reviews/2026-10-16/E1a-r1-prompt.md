Adversarial review of docs/plans/2026-10-16-E1a-redaction-underscore-phi.md (Asclexis, a local-first health app handling PHI).

Verify every claim against the repo: src/backend/modules/redaction.py, src/backend/tests/test_redaction.py, src/backend/modules/normalize.py (:240-290), src/backend/modules/export.py (:199-209), docs/plans/2026-09-27-W02-doctor-summary-redaction.md (:182, :203-209, :745-749, :831-845), docs/plans/2026-10-15-build-program/queue.md (:23, E-1 and E-1a rows), docs/capstone-report/owner-decisions-2026-09-27.md (:176), CLAUDE.md §1/§3/§4.

Hunt for: (1) regex PHI misses in the target shapes or false positives on real analyte names; (2) tests that cannot fail or assert the wrong thing; (3) wrong line refs, counts or commands; (4) ordering/dependency deadlocks with E-1; (5) any over-claim (e.g. "PHI-free"); (6) owner-gate gaps for an ask-first file; (7) other strict callers (fhir_export, rl_dataset, external_runner, agent/eval/scorer) that the change could break.

Output exactly: first line `VERDICT: PASS` or `VERDICT: REVISE`, then one finding per line as `[BLOCKER|MAJOR|MINOR] path:line — problem — fix`. No preamble.
