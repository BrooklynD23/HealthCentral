# STILLNESS-NAV-LATE quiet-box result (2026-11-13; agent cut off by an API auth error, L0 wrote this from its logs)
Main abec056f (after #621 per-frame G10 sampler, #640 eager mono font). Spec = verbatim copy of e2e/ui-shell.spec.ts
(+1 console.log line, +1 uncounted bare-timer describe), grep "HC-UISH-009: the Safety Rail stays still through the
navigation|HC-UISH-003: opacity-only", --repeat-each 20, --retries=0, 1 worker, via scripts/quiet_run.sh, TMPDIR=/dev/shm.
| Run | Result | Log |
|---|---|---|
| dev (vite) | 540 passed (23.0m), EXIT=0 | dev-r20.log |
| preview (prod build) | 540 passed (21.7m), EXIT=0 | preview-r20.log |
| calibration dev | 41 passed (1.5m) | cal-dev.log |
Before (queue, 2026-10-27/28): origin/main missed 9/15 on dev; HC-UISH-009 failed 2/44 CI attempts (NAV70-CI-MISS).
Reading: on this box the page-change stillness misses no longer reproduce at the current 70 ms page-change bound.
Not done (agent cut off): traced runs at the 40 ms diagnosis bound; CI-side confirmation. Nightly gates do not cover
ui-shell (mocked G3 leg only). SNLGAP lines in the logs hold per-route max gaps (timer vs rAF) if needed.
Owner questions: close STILLNESS-NAV-LATE + NAV70-CI-MISS? Restore the 40 ms page-change bound (STILLNESS-NAV-70 interim)?
Largest sampling gap per run (SNLGAP max, ms): dev n=280 median 20, p95 34, max 48; preview n=280 median 19, p95 34, max 49.
=> At the 70 ms page-change bound: 0 misses in 1080. At the old 40 ms bound some runs would still miss (max 48-49 ms,
   about the top 5%), so restoring 40 ms is NOT supported by this data. Recommend: close STILLNESS-NAV-LATE and
   NAV70-CI-MISS as "fixed by #621/#640 at 70 ms", keep the 70 ms page-change bound.
