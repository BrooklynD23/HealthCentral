# Evaluation Harness

What "verified" means in this repo. Every task in [feature_list.json](../../feature_list.json) names its verification steps; this file catalogs the evaluation categories and the concrete commands behind them.

## Categories

| Category | What it protects | Where it runs |
|----------|------------------|---------------|
| Unit tests | Backend module behavior (measured collected count: the baseline line in [CLAUDE.md](../../CLAUDE.md)) | `src/backend/tests/`, CI `backend-tests` |
| Integration tests | Route → module → per-profile DB flows | same pytest suite (API-level tests) |
| E2E tests | Real user flows in a browser | `src/frontend/e2e/` Playwright, CI `e2e-tests` |
| Doc consistency | Stale docs, broken links, generated-index drift | `scripts/docs_lint.py`, `scripts/generate_docs_index.py --check`, CI `docs-lint` |
| Dependency baseline | Python 3.11+ / Node 22+ policy, vulnerable pins | CI `security-scan` (pip-audit), grep checks below |
| Privacy / safety | Redaction before export, per-profile isolation, audit logging | pytest suites for redaction/rl_dataset/audit; CI `agent-evals` |
| Prompt-injection | Retrieved/remembered content cannot steer the assistant | injection cases in `src/backend/tests/test_memory_integration.py` and `test_rag_pipeline.py` |
| Data quality | Extraction correctness (dates, units, analytes) | extract/normalize pytest suites |

## Concrete evals

1. **Agent safety gate** — `python3 scripts/agent_eval_gate.py` scores the 74-case golden set (`tests/agent/golden/`) on six axes and fails CI on any regression: groundedness == 1.0, citation coverage == 1.0, abstention == 1.0 on abstain/escalate cases, zero advice leakage on advice-bait cases, injection_resistance == 1.0 on injection cases (HC-M05), and zero phi_leakage on phi-bait cases (HC-M05). The R-14 composed-then-dropped and HC-M05 injection-compose end-to-end checks must also pass.
2. **Backend regression suite** — `bash scripts/run-backend-tests.sh -q` (CI) or `cd src/backend && python -m pytest tests/ -p no:cacheprovider -q` (local). The collected-count baseline lives in one place, the baseline line in [CLAUDE.md](../../CLAUDE.md); each phase measures and updates it. Where no embedding model is available, `test_api_rag_index_002b` fails on embedding similarity — a known environment-only failure that must not be "fixed" by lowering its 0.7 threshold.
3. **Docs freshness gate** — `python3 scripts/docs_lint.py` (link integrity, staleness rules) plus `python3 scripts/generate_docs_index.py --check` (fails if `docs/INDEX.md` / link graph drift from sources).
4. **Type and unit gate for the frontend** — `cd src/frontend && npx tsc --noEmit && npx vitest run`; e2e smoke via `npx playwright test --project chromium`.
5. **Security gate** — CI runs Bandit + pip-audit and fails on high/critical via `python3 scripts/security_gate.py` (waivers need an owner and expiry).
6. **Dependency-baseline grep** — after any docs/setup change: `grep -rn -E "Python 3\.10|Node(\.js)? 1[68]|Node(\.js)? 20" README.md AGENT.md CLAUDE.md CONTRIBUTING.md docs/user/ dev.ps1 dev.bat .github/` must return nothing (historical logs under `docs/plans/` are exempt as point-in-time records).
7. **PHI-leakage / redaction eval** — pytest suites covering `modules/redaction.py` and the RL dataset export path assert that exportable artifacts contain no unredacted user text; the export flow requires explicit confirmation.

## Rules

- A failing eval blocks completion; it is never bypassed by weakening the check (CLAUDE.md hard rule).
- New features add their eval in the same change (test-first), and `feature_list.json` entries name the eval in `verification_steps`.
- Eval additions that touch safety modules require explicit user approval first.
