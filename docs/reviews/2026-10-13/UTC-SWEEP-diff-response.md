# UTC-SWEEP diff review response

| Finding | Response |
|---|---|
| MEDIUM missed site `api/assistant.py:99-100` | **Scoped out by name as follow-up ASSIST-UTC; this is an owner question.** The fields are `str`, and the parse happens inside `modules/rag.py`, the legacy RAG path. If the field type changes to `NaiveUtcDatetime`, malformed strings that are silently ignored today would start returning 422s. If the fix goes inside `rag.py` instead, the per-site HTTP test has to drive the real legacy `rag.query` (every current assistant route test mocks `get_rag_module`), with an embeddings and runner stub. Both options go beyond a type-annotation sweep. The frontend sends naive dates (`ExplainAssistant.tsx:320`), so there is no live impact today. |
| MEDIUM day bucket uses the UTC day | **Kept; recorded for the owner.** This matches the storage convention (naive UTC) and decision MED-UTC. Before this fix, aware input selected a wall-clock window that was offset arbitrarily. Naive input, which is all the frontend sends, is unchanged. |
| LOW summary label and text show the UTC date | **Accepted.** Aware input used to return a 500 (verified: RED run, `TypeError: can't compare offset-naive and offset-aware datetimes` at `modules/export.py:106`). The redaction path is unchanged. |
| LOW test 010 coverage | **Partly addressed.** `to_date` cases were added to every filter test before this review (8 cases per site). A both-dates case and a download assertion are deferred. The label already proves the normalised value reached the module. |
| NIT pydantic import in `core/time.py` | **Kept.** pydantic is already a hard dependency. A single shared alias is better than redefining it in each of 5 API modules. |

No code changes came out of this review.
