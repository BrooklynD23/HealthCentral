# CI & Quality Gates

**Last Updated:** 2026-10-18
**Owner:** Project Lead
**Refresh Trigger:** A CI job is added, removed, or changes what it blocks on

Part of the [architecture diagram set](README.md).

---

```mermaid
flowchart TD
    PUSH["push / pull request"] --> JOBS

    subgraph JOBS[".github/workflows/ci.yml"]
        direction TB
        DOCS["docs-lint<br/>docs_lint.py · generate_docs_index.py --check<br/>feature_list_lint.py · repo_hygiene_check.py"]
        BE["backend-tests<br/>pytest via run-backend-tests.sh<br/>SQLCipher installed"]
        LINT["backend-lint<br/>ruff check (F, I, W) · ruff 0.17.1"]
        FE["frontend-tests<br/>tsc --noEmit · eslint · vitest · build"]
        SEC["security-scan<br/>bandit + pip-audit via security_gate.py"]
        EVAL["agent-evals<br/>agent_eval_gate.py"]
        LEGACY["legacy-evals<br/>legacy_eval_gate.py"]
        E2E["e2e-tests<br/>Playwright (chromium)"]
    end

    BE --> E2E
    FE --> E2E

    DOCS --> MERGE{"merge allowed"}
    BE --> MERGE
    LINT --> MERGE
    FE --> MERGE
    SEC --> MERGE
    EVAL --> MERGE
    LEGACY --> MERGE
    E2E --> MERGE

    style EVAL fill:#4a148c,stroke:#ba68c8,color:#fff
    style SEC fill:#4a148c,stroke:#ba68c8,color:#fff
```

## What each gate actually protects

| Job | Blocks on | Why it exists |
|---|---|---|
| `docs-lint` | Doc drift (DOC-003…DOC-013), stale generated index, malformed feature inventory, scratch files at the repo root | Documentation that contradicts the code is worse than no documentation |
| `backend-tests` | Any pytest failure, a missing coverage report, or a coverage TOTAL below 74% (owner Q-COV, 2026-10-19). The job first runs `python scripts/download_models.py embedding` so the offline embedding model is present | The measured collected-count baseline is the one in [CLAUDE.md](../../CLAUDE.md); see "Known env-only failure" below |
| `backend-lint` | Any ruff finding under the configured set in `src/backend/pyproject.toml`. Ask-first files are held by per-file-ignores until the owner approves fixing them | Catches undefined names and import/whitespace drift before the test job does |
| `frontend-tests` | Type errors, eslint errors, vitest failures and a failing production build (`npm run lint`, `npm run build`; contract C-API-3) | — |
| `security-scan` | High/critical findings not covered by a dated, owner-attributed waiver; a scanner error (exit ≥ 2); a missing or malformed report | Waivers expire on purpose; the gate fails closed |
| `agent-evals` | Any failed golden case or missed bar: groundedness, citation, abstention and injection_resistance == 1.0; advice_leakage and phi_leakage == 0. Agent path only | Injection and leakage resistance are regression-tested guarantees, not one-time reviews |
| `legacy-evals` | Any missed bar in `scripts/legacy_eval_gate.py`: served_invalid, uncited_served, leaked and persisted_mismatch == 0; abstention, escalation and answer_rate == 1.0. Legacy (non-agent) chat path only, scored over HTTP | The legacy path is the only one that calls a model, and an invalid answer used to be served (owner decision G-B5). `api.assistant._legacy_serve_or_abstain` now replaces any `is_valid=False` result with `ABSTAIN_TEMPLATE` |
| `e2e-tests` | Playwright failures | Runs after backend and frontend jobs pass |

The two purple gates are the ones that encode product-safety claims rather than
correctness. `agent-evals` in particular holds an absolute bar: **any** injection
that succeeds, or **any** PHI leak, fails the build — there is no threshold to
tune downward.

## Known env-only failure

Five tests need the real embedding model and fail in environments without one
(measured with `EMBEDDING_MODEL_PATH=/nonexistent`, Py 3.11, W-8 head `3aac97f`: `5 failed, 1804 passed`):
`test_embedding_bundle.py::test_hc_emb_002_fetched_model_loads_offline`,
`test_rag_pipeline.py::TestEmbeddingsPipeline::test_api_rag_index_002` / `002b` / `002c`, and
`TestVectorSearchIntegration::test_search_vectors_async_calculates_similarity`. The model now loads offline from a local directory; fetch it with `cd src/backend && python scripts/download_models.py embedding` (CI does this before the tests). The 0.7
similarity threshold is deliberately not lowered to make it pass.
