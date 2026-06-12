# Verification Report — 2026-06-11
Branch: `fix/agent-overhaul`  
Verified by: automated agent pass (Claude Sonnet 4.6)

---

## 1. Redaction test root-cause (TestExternalRunnerIntegration)

**Was it a product regression?  No.**

`core/external_runner.py` is correct and complete:
- `generate_async` always applies redaction when `redaction_enabled=True` before calling any provider.
- In production (`app_env == "production"`) without break-glass it hard-blocks and returns `finish_reason="error"` if redaction is disabled or policy is not `strict`.
- With break-glass it calls the provider AND emits `logger.warning("SECURITY_AUDIT: …")` before the call.

The `commit fedc500` refactor of `core/model_runner.py` did not touch `external_runner.py` at all; the security-audit logging path was never removed.

**Actual root cause: `logging.config.fileConfig` with `disable_existing_loggers=True` (Python default)**

`migrations/profile/env.py` called `fileConfig(config.config_file_name)` during the Alembic migration run in `test_profile_migrations_sqlcipher_fallback.py`.  Python's `fileConfig` defaults to `disable_existing_loggers=True`, which marks all pre-existing loggers (including `core.external_runner`) as disabled.  When the `test_break_glass_allows_unredacted_call_with_audit_warning` test ran immediately after in the full suite, the `core.external_runner` logger was disabled, so its `WARNING` record never propagated to pytest's `caplog` handler.  The test passed in isolation (no migration test preceding it) and passed with `-s` (logging to stderr bypasses the disabled state in that path).

The previous debugger's `caplog.set_level(logging.WARNING, logger="core.external_runner")` edit was a correct diagnostic step — it would have worked — but the right fix is in the migration env files, not in the test.

**Fix applied:**
```
migrations/master/env.py   — fileConfig(..., disable_existing_loggers=False)
migrations/profile/env.py  — fileConfig(..., disable_existing_loggers=False)
```

---

## 2. Backend test results

```
Platform: Linux, Python 3.10.12
Command:  pytest tests/ -p no:cacheprovider --tb=short -q
```

| Result | Count |
|--------|-------|
| Passed | 620   |
| Failed | 1     |
| Total  | 621   |

**Sole failure (env-blocked, do not fix):**
```
FAILED tests/test_rag_pipeline.py::TestEmbeddingsPipeline::
       test_api_rag_index_002b_similar_text_yields_similar_embeddings
  assert 0.6316... > 0.7
```
No real embedding model is installed in the sandbox; the hash-based fallback embedder produces lower cosine similarity than the threshold requires.  **Do not lower the threshold** — it is a meaningful quality gate.  This test will pass in any environment with a real sentence-transformer or similar embedding model installed.

---

## 3. Boot smoke test

```
cd src/backend && timeout 90 python3 -c "from main import app; print('BOOT OK')"
```
Result: `BOOT OK` (sqlcipher3 not available warning is expected in sandbox — stdlib sqlite3 fallback is the correct dev-mode behaviour).

---

## 4. Migration chain sanity

Profile migrations 001 → 008, verified clean linear chain:

| Revision | down_revision |
|----------|---------------|
| 001_initial | None |
| 002_external_api | 001_initial |
| 003_gamification_voice | 002_external_api |
| 004_document_categories | 003_gamification_voice |
| 005_memory_items | 004_document_categories |
| 006_ocr_preference | 005_memory_items |
| 007_chat_sessions | 006_ocr_preference |
| 008_response_feedback | 007_chat_sessions |

No duplicate revision IDs. Column sets in 007/008 match `models/chat_session.py` and `models/response_feedback.py` table definitions.

---

## 5. Frontend TypeScript audit

**Two real TS errors found and fixed:**

### 5a. `services/assistant.ts` — missing `apiDelete` / `apiPatch` imports
The file called `apiDelete(...)` and `apiPatch(...)` but only imported `apiGet, apiPost` from `./api`.  Both functions are exported by `api.ts`.

Fix:
```ts
// before
import { apiGet, apiPost } from './api';
// after
import { apiGet, apiPost, apiDelete, apiPatch } from './api';
```

### 5b. `services/index.ts` — `DocumentCategory` type not re-exported
`DOCUMENT_CATEGORIES` (the const) was re-exported from the barrel but the companion `DocumentCategory` type was not.  Any barrel consumer importing `type DocumentCategory` from `@/services` would get a TS error.  `ExplainAssistant.tsx` already imported it from `@/services/assistant` directly (no error there), but the barrel inconsistency is a latent bug for future consumers.

Fix: added `DocumentCategory` to the `export type { … } from './assistant'` block in `services/index.ts`.

### 5c. Full tsc / npm run build — not executable in sandbox

`node_modules/.bin/` is entirely absent and `node_modules/typescript/lib/*.d.ts` files are not mounted in the Linux 9p filesystem.  The Windows-side `node_modules` was installed there but the mount only exposes a partial view.

**Run these commands on Windows to complete the frontend build check:**
```powershell
cd C:\Users\DangT\Documents\GitHub\HealthCentral\src\frontend
npm install          # ensure lock is up-to-date (should be a no-op)
npx tsc --noEmit     # type-check only — should produce 0 errors after the two fixes above
npm run build        # full Vite production build
```

---

## 6. Env-blocked items and Windows commands

| Item | Status | Windows command |
|------|--------|-----------------|
| `tsc --noEmit` | Unverifiable in sandbox (partial node_modules mount) | `cd src\frontend && npx tsc --noEmit` |
| `npm run build` | Unverifiable in sandbox | `cd src\frontend && npm run build` |
| RAG embedding similarity test | Fails (no embedding model) | Install `sentence-transformers` + a model; do not lower threshold |
| `alembic upgrade head` (live DB) | Not run (no vault path/key in CI) | `cd src\backend && python -m alembic -n profile upgrade head` |

---

## 7. Suggested follow-ups

1. **Semantic retrieval over chat turns** — current RAG uses keyword/vector search over documents only; chat turn history is stored in `chat_sessions`/`chat_turns` but not indexed for retrieval.  Adding a turn-level embedding index would let the assistant recall prior conversations semantically.

2. **Real Gemma 4 GGUF URL verification** — `modules/model_selector.py` references a Gemma 4 GGUF download URL. This URL should be smoke-tested against Hugging Face to confirm the model file is accessible and the SHA matches before a production release.

3. **Bandit strategy selection for RL pipeline** — `modules/rl_dataset.py` exports DPO/GRPO/SFT datasets but the selection strategy for which pairs become training examples is a fixed heuristic. A contextual bandit or Bayesian approach over the `tag_distribution` signal would improve sample quality.

4. **`alembic.ini` `path_separator` warning** — both env.py files now use `version_path_separator = os` in the named sections, but the root `[alembic]` stanza still lacks `path_separator = os`.  Adding it removes the DeprecationWarning from the test output.

5. **httpx2 migration** — FastAPI's `testclient` emits a `StarletteDeprecationWarning` about `httpx`; upgrading `httpx` → `httpx2` in `pyproject.toml` will silence it.

---

## 8. Changes committed in this pass

```
fix(verify): disable_existing_loggers=False in alembic env.py files (fix caplog test-ordering)
fix(verify): add missing apiDelete/apiPatch imports to services/assistant.ts
fix(verify): export DocumentCategory type from services/index.ts barrel
```

Files changed:
- `src/backend/migrations/master/env.py`
- `src/backend/migrations/profile/env.py`
- `src/frontend/src/services/assistant.ts`
- `src/frontend/src/services/index.ts`
