# Fixture build queue

## Planned wave A

| id | lane | kind | depends_on | owner gates | ask-first | files | est h | runtime | status |
|---|---|---|---|---|---|---|---|---|---|
| ROW-ONE | B | PRODUCT | none | none | — | `be/api/widgets.py:40-80`, `be/tests/test_widgets.py`, `fe/src/pages/Widgets.tsx` | 2 | claude | **READY** |
| ROW-BRACE | B | PRODUCT | none | none | — | `be/modules/{alpha,beta}.py`, `be/api/` , `e2e/widgets.spec.ts`, `scripts/tool_stem` | 2 | claude | **READY** |
| ROW-ASK | B | PRODUCT | none | gate ROW-ASK-DIFF | `modules/redaction.py` | `be/modules/redaction.py` | 2 | claude | **READY** |
| ROW-PLAN | B | PRODUCT | none | none | — | see [the plan](fixture_plan.md#section-for-row-plan); edits the RUNBOOK and the builder brief | 2 | claude | **READY** |
| ROW-PLAN-EXTRA | B | PRODUCT | none | none | — | `be/modules/gamma.py` | 2 | claude | **READY** |
| ROW-BROAD | B | PRODUCT | none | none | — | `src/` | 1 | claude | **READY** |
| UI-PG | B | PRODUCT | none | none | — | `fe/src/pg.tsx` | 1 | claude | **READY** |
| UI-PG-ASK | B | PRODUCT | none | none | — | `fe/src/ask.tsx` | 1 | claude | **READY** |
| ROW-NOT | B | PRODUCT | none | none | — | `be/api/yes.py` and `fe/pages/Yes.tsx`. **Not** `be/api/no.py`, `be/api/nope.py`. | 1 | claude | **READY** |
