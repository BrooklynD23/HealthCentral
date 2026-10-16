# UTC-SWEEP diff code review

Reviewer: code-reviewer subagent (Opus 5.5), read-only, 2026-10-13.
Diff: `fix/utc-sweep` against `origin/main` f853308.

**Verdict: approve-with-nits.** The diff is correct at every site it touches. It missed one client datetime input: `api/assistant.py:99-100`.

| Sev | file:line | Issue | Fix |
|---|---|---|---|
| MEDIUM | `api/assistant.py:99-100` | **Missed site.** `ChatRequest.from_date` and `to_date` are typed `Optional[str]`. `modules/rag.py:339,345,560,567` parses them with `datetime.fromisoformat` and binds them aware to SQLite, so they hit the same wall-clock bug. The rag code silently drops bad strings (`except: pass`). The `datetime` grep cannot see this site because the fields are `str`. | Fix in this PR, or scope it out by name. |
| MEDIUM | `api/observations.py:773-774`, `modules/interpret.py:325-326` | **What the day bucket means.** Panel `collection_date` and interpret `collected_at` select a calendar day, and stored lab dates are naive calendar midnight from extraction (`api/documents.py:177`). An aware `00:00+05:00` value now searches the UTC day before. No impact today, because the frontend sends naive values. | Owner call: should the bucket be the UTC day or the client's wall-clock day? |
| LOW | `api/export.py:465-471`, `modules/export.py:186-188` | The doctor-summary `date_range` label and summary text now show the UTC date for aware input. Before this fix, aware input returned a 500 (`TypeError` at `modules/export.py:106`). | Accept, or note it in the owner row. |
| LOW | `tests/test_utc_sweep_http.py` test 010 | Asserts only the API `date_range` label: not the downloaded summary text, and not the case where both dates are set. | Add a both-dates case and a download assertion. |
| NIT | `core/time.py` | `core/time.py` now imports pydantic. It was stdlib-only before. | None. |

The reviewer's checks:

1. **Missed sites:** 1 (`assistant.py`). The remaining hits are internal helpers (`export.py` `_fetch_*`), extraction output (`documents.py`), or `date` types (`timeline.py`, `search.py`).
2. **Naive input:** unchanged. `to_naive_utc` returns naive values as-is, and the tests cover naive and `Z` input.
3. **Redaction:** unchanged. The diff touches annotations and imports only. Visit-prep (strict) and doctor-summary redaction are untouched, and `/export/csv` and `/export/json` remain the only D3 exemptions.
4. **Audit and ProfileDbSession:** unchanged on every edited route.

Gaps the reviewer found in the tests:
- No negative-offset case.
- No assistant test.
- No audit-row assertion.
- The download tests are substring-only.
- Test 006 is coupled to the 404 wording.
