STILLNESS-NAV-LATE — L0 quiet-box measurement on `main` (2026-11-07, Devin session)

Tree: `hc-stillness-probe` worktree detached at origin/main `9ab89972` (#534 merge).
`src/` is exactly main's. Preview dist built from the same tree (`vite build` 39.05 s).

Spec: `docs/reviews/2026-11-02/stillness-nav-evidence/run/nav-sets.spec.ts`, copied to
untracked `snl-run-1107/` in the worktree with ONE adaptation (documented inline in the
file): `navigateTo('/search')` used `getByRole('banner').getByRole('searchbox')`, which no
longer exists on main — the banner's search input was replaced by the CommandPalette
trigger. The patched trigger clicks the banner "Search health records" button, fills the
dialog's `role="combobox"` input, presses Enter → `/search?q=migraine`. Same user path to
the same lazy route; measured gap class unchanged. All other triggers untouched.

Runs: both wraps via `/tmp/claude-1000/quiet_run.sh --max-wait 7200` → `run_wrap.sh`.
Prechecks pasted in wrapA.out/wrapP.out and per-batch `*.precheck.log` (load < 1.5,
pgrep only own pids, no foreign ports). wrap A exit 0, wrap P exit 0. Own server pids
only; nothing left listening (cleanup trap verified: `ss` clean after).

Result (counted probe runs, max gap per run):

  dev server (:3000), wrap A:   14 of 15 ≤ 40 ms
    b1: 31 37 37 33 27 | b2: 36 34 28 30 25 | b3: 30 **45** 33 29 27
    miss: /search, batch 3, 45 ms (same route as the historical misses; dev pattern again)
  vite preview (:4173), wrap P: 15 of 15 ≤ 40 ms
    b1: 27 28 22 25 27 | b2: 25 32 24 24 31 | b3: 33 35 33 35 34
  bare-timer set (wrap A, evidence): all ≤ 40 (route maxima: 30–39; /search max 39)

Verdict vs the row's acceptance ("15 of 15 at 40 ms or less on dev and on preview"):
  NOT earned — dev 14 of 15 (max 45), preview 15 of 15 (max 35). Row stays open.
  This matches the previously recorded dev pattern (14 of 15, max 44) and the row's
  finding that a miss under load is inconclusive; this run was on a quiet box, so the
  45 ms dev-server miss counts. /search remains the worst route.

Logs: /tmp/claude-1000/snl-main-1107b/ (RESULT lines in A1..A3.log, P1..P3.log,
warmA/warmP.log; per-run load1Start/load1End in the JSON rows).
The failed first attempt (/tmp/claude-1000/snl-main-1107/) is kept for the record: it
proved the committed spec stale on main (searchbox timeouts, measured:false) before
the one-line adaptation above.
