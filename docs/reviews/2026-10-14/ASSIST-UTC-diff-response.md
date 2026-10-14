# ASSIST-UTC diff — author response to code review

| # | Decision | What was done |
|---|----------|---------------|
| MEDIUM agent path | Deferred to owner | Out of scope for ASSIST-UTC (owner chose a rag.py parsing patch). The PR body states that the fix covers the legacy `rag.query` path only, and that the default agent path does not take `from_date`/`to_date` at all. This goes to the owner as candidate row ASSIST-AGENT-DATES. |
| LOW export | Deferred to owner | Same bug class in `api/export.py` / `modules/export.py`; not verified here. Candidate owner row; the `NaiveUtcDatetime` pattern from #85/#93 applies. |
| LOW overflow | Accepted | Ignoring an out-of-range aware bound matches the decision ("malformed dates still ignored, no new exceptions"); without `OverflowError` in the catch, the request returned 500 (mutation-checked). Covered by `overflow_from_ignored`. |
| LOW boundaries | Fixed | Added `z_from_equal_includes` and `plus5_to_equal_includes` (inclusive bounds at the stored instant). Collected count 1499 → 1501. |
| LOW type hint | Fixed | `_parse_filter_date(value: str) -> Optional[datetime]`. |
| Count nit | Fixed | RED is stated as 4 of 11 cases at the time it ran (the overflow case was added after RED, for the new `OverflowError` path). |
