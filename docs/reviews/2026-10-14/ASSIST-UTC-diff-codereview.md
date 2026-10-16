# ASSIST-UTC diff — code review

Reviewer: code-reviewer subagent (Opus 5.5), read-only, 2026-10-14. Verdict: **approve**. No CRITICAL or HIGH findings; 1 MEDIUM and 4 LOW, of which the MEDIUM and one LOW are out-of-scope leads.

## Behavior unchanged for malformed and empty input

1. Empty or None: the old `if from_date:` guard is kept (`... if from_date else None`), so the filter is still skipped.
2. Unparseable strings (`not-a-date`, `2026-13-45`, `yesterday`): both versions catch the `fromisoformat` error and apply no filter. No new 422s, no new exceptions.
3. Naive and `Z`: `to_naive_utc` leaves naive values unchanged; `Z` becomes the same naive UTC instant.
4. One real change: values that used to parse and filter, but now overflow in `astimezone`, are ignored (see the `rag.py:57` row).

## Remaining date-filter sites

The legacy chat path has 4 date comparisons (`rag.py` observation and document filters). All 4 go through `_parse_filter_date`. `query()` and `retrieve_context()` only pass the strings along.

## Findings

| Sev | File:line | Issue | Suggested fix |
|---|---|---|---|
| MEDIUM (out of scope) | `src/backend/api/assistant.py:790-797`, `src/backend/modules/agent/settings.py:19` | `AGENT_ENABLED_DEFAULT = True` and `_serve_via_agent` takes no `from_date`/`to_date`, so by default the chat date filters are ignored. This fix applies only when the agent is disabled or fails. Recurring failure #10. | Add an owner row (ASSIST-AGENT-DATES); state the legacy-only scope in the PR. |
| LOW (out of scope) | `src/backend/api/export.py:145-148, 263-266`; `src/backend/modules/export.py:105-108` | Same bug class: `Optional[datetime]` query params compared as wall-clock against naive columns; the Python-side comparison may raise `TypeError` for aware input. Not verified. | Owner row; reuse the `NaiveUtcDatetime` pattern (`api/medications.py:90`). |
| LOW | `src/backend/modules/rag.py:57` | Overflow behavior change at the extremes: `to_date="0001-01-01T00:00:00+05:00"` used to exclude every row; it now drops the filter. Nonsense input only; no cross-profile leak. | Accept (conservative), or clamp to `datetime.min`/`max`. |
| LOW | `src/backend/tests/test_assist_utc_http.py:132-149` | No case with a bound exactly at the stored instant, so `>=` → `>` would go unnoticed. | Add `z_from_equal_includes` and `plus5_to_equal_includes`. |
| LOW | `src/backend/modules/rag.py:50` | `_parse_filter_date(value)` has no type hint. | `value: str`. |

## Other checks

- The test runs over HTTP via `route_client` and drives real `rag.query` against a real DB. It asserts on prompt contents, and observations and documents separately.
- No safety, redaction or faithfulness module is touched; there are no new network or LLM calls; the `ChatRequest` type is unchanged.
- The test DB uses `create_all`, not the Alembic chain. That is acceptable because no schema changes.
- The case count is 12, not 11; fix the figure in the PR body.
