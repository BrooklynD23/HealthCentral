# Roles Index — "Which Doc Do I Read For X?"

**Owner:** Project Lead
**Refresh Trigger:** New subsystem added, or a role doc's link set goes stale

This is a domain-based entry point into HealthCentral's architecture documentation, organized like an
engineering team's subsystem ownership — not job titles (this is a solo-dev repo; see
`docs/agile/AGILE_PLAN.md` for the process side, "you wear both hats"). Each role doc below is a **thin
index only**: scope + links into existing docs, no duplicated content. If you're adding real
architectural detail, it belongs in the linked doc, not here.

| If you're working on... | Read |
|---|---|
| Understanding how the whole system fits together | [`../architecture/README.md`](../architecture/README.md) (diagrams) |
| FastAPI routes, modules, SQLCipher vault access | [`backend-api.md`](backend-api.md) |
| React/Vite/TS app, routing, state, accessibility | [`frontend.md`](frontend.md) |
| SQLAlchemy models, Alembic migrations, per-profile DB | [`data-and-migrations.md`](data-and-migrations.md) |
| Model provider layer, RAG, hardware tiers, agent guardrails | [`ai-llm-pipeline-and-safety.md`](ai-llm-pipeline-and-safety.md) |
| HIPAA, encryption, audit, privacy | [`security-and-compliance.md`](security-and-compliance.md) |
| CI pipeline, docs_lint.py, repo hygiene | [`devops-and-ci.md`](devops-and-ci.md) |
| Product intent, PRD, feature backlog | [`product-and-prd.md`](product-and-prd.md) |

For the full canonical doc order and repo-wide status, start at
[`docs/00_architecture_plans_index.md`](../00_architecture_plans_index.md). For a flat, all-docs map, see
[`docs/INDEX.md`](../INDEX.md).
