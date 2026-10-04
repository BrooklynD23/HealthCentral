# CI & Quality Gates

**Last Updated:** 2026-10-04
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
        FE["frontend-tests<br/>tsc --noEmit · vitest"]
        SEC["security-scan<br/>bandit + pip-audit via security_gate.py"]
        EVAL["agent-evals<br/>agent_eval_gate.py"]
        E2E["e2e-tests<br/>Playwright (chromium)"]
    end

    BE --> E2E
    FE --> E2E

    DOCS --> MERGE{"merge allowed"}
    BE --> MERGE
    FE --> MERGE
    SEC --> MERGE
    EVAL --> MERGE
    E2E --> MERGE

    style EVAL fill:#4a148c,stroke:#ba68c8,color:#fff
    style SEC fill:#4a148c,stroke:#ba68c8,color:#fff
```

## What each gate actually protects

| Job | Blocks on | Why it exists |
|---|---|---|
| `docs-lint` | Doc drift (DOC-003…DOC-013), stale generated index, malformed feature inventory, scratch files at the repo root | Documentation that contradicts the code is worse than no documentation |
| `backend-tests` | Any pytest failure | The measured collected-count baseline is the one in [CLAUDE.md](../../CLAUDE.md); see "Known env-only failure" below |
| `frontend-tests` | Type errors and vitest failures. `npm run build` and eslint are **not** run in CI (contract C-API-3) | — |
| `security-scan` | High/critical findings not covered by a dated, owner-attributed waiver; a scanner error (exit ≥ 2); a missing or malformed report | Waivers expire on purpose; the gate fails closed |
| `agent-evals` | Any failed golden case or missed bar: groundedness, citation, abstention and injection_resistance == 1.0; advice_leakage and phi_leakage == 0. Agent path only | Injection and leakage resistance are regression-tested guarantees, not one-time reviews |
| `e2e-tests` | Playwright failures | Runs after backend and frontend jobs pass |

The two purple gates are the ones that encode product-safety claims rather than
correctness. `agent-evals` in particular holds an absolute bar: **any** injection
that succeeds, or **any** PHI leak, fails the build — there is no threshold to
tune downward.

## Known env-only failure

`test_rag_pipeline.py::...test_api_rag_index_002b_similar_text_yields_similar_embeddings`
needs a real embedding model and fails in environments without one. The 0.7
similarity threshold is deliberately not lowered to make it pass.
