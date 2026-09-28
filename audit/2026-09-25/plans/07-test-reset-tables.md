# Test-Reset Profile Table Coverage Implementation Plan

> **2026-09-27 corrections ([review follow-up](../review/2026-09-27-followup.md), F-07/N-02/N-03):**
> 1. The expected count is now the start-of-plan measurement plus 7, not 1252.
> 2. The FK-state comments are true both before and after plan 06.
> 3. **N-02:** `modules/search.py:28-50` creates raw-SQL `search_records` and `search_records_fts` (FTS5) tables inside the profile vault. They hold record titles and content. They are not ORM models, so an ORM-metadata coverage test (HC-RESET-010) cannot see them. Decide whether reset clears or rebuilds them, and assert it explicitly.
> 4. **N-03:** `/profiles/test/reset` writes no audit row (`api/profiles.py:477-531`) and echoes `{exc}` in its 500 detail. Both are out of this plan's scope; they are recorded as gaps in the specs-compliance matrix.
> 5. **Overlap with plan 06:** plan 06 Task 3 Step 5 would edit the same reset tuple. Land this plan's version, and treat plan 06 Step 5 as superseded rather than doing it twice.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `POST /profiles/test/reset` delete rows from **every** profile-scoped table — currently it misses 6 (`ChatSession`, `ChatTurn`, `ResponseFeedback`, `CarePlanTask`, `Pinboard`, `PinboardItem`), so Playwright e2e resets leave stale patient data and cross-test contamination (audit 2026-09-25 §11 P2).

**Architecture:** Extract the endpoint's inline model tuple into a module-level constant `_SYNTHETIC_RESET_MODELS`, ordered children-before-parents (before plan 06, FK enforcement is off, so order is the only guard; after plan 06, a parent-first order would raise. Keep child-first in both states. Corrected 2026-09-27). Add the 6 missing models in the correct positions. A metadata-enumeration test pins the constant to `ProfileDatabaseBase.metadata` so any future profile table fails CI until the reset list is updated. Route tests go through HTTP via `tests/support/routes.py::route_client`, extended with `profile_name` / `profile_db` params.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy async, pytest + pytest-asyncio, `TestClient`.

**Audit finding being fixed:** `Devin-Audit-report.md` §11 P2 — "`/profiles/test/reset` misses 6 profile tables (ChatSession/ChatTurn/ResponseFeedback/CarePlanTask/Pinboard*)".

## Global Constraints

- **Per-profile isolation:** all deleted rows live in the per-profile vault DB via `ProfileDbSession`; never touch master `get_db()` tables for profile data (invariant).
- **Target Python 3.11+.** Use `core.time.utcnow` for timestamps.
- **Route tests go through HTTP** — use `route_client`; never call `reset_synthetic_test_profile()` directly (recurring-failure mode: dependency-graph bypass).
- **FK order matters even with enforcement off** (SQL-FK-001): children deleted before parents.
- **`badge_definition` is reference/seed data, not patient data** — it is populated by profile migration `003_gamification_voice_settings.py`, is only ever `SELECT`ed by app code (`api/gamification.py:75`), and nothing re-seeds it. The reset must NOT clear it. (Executor: verify migration 003 seeds rows before relying on this — `grep -n "insert\|bulk_insert" src/backend/migrations/profile/versions/003_gamification_voice_settings.py`.)
- **Reset ≠ delete.** The endpoint must NOT touch `vault.db`, `key.bin`, `key.method`, `key.recovery.bin`, or `backups/{profile_id}/`. Only vault table rows + `vaults/{profile_id}/docs/` are reset.
- **Guard must be preserved, not weakened:** endpoint is already double-gated (`app_env == "production"` → 404 at `profiles.py:489-490`; profile name must start with `"Playwright E2E"` → 403 at `profiles.py:492-496`; JWT auth + live profile-vault connection required). Assessed adequate — a caller can only wipe a vault they hold a session for. Do not relax; pin with tests.
- Commit style: `fix(profiles):` prefix, small single-purpose commits.

## Verified current state (evidence)

| Fact | Location |
|---|---|
| Endpoint `POST /profiles/test/reset`, 204 on success | `src/backend/api/profiles.py:477-532` |
| Deletes only 16 models inline | `profiles.py:499-516` |
| Guards: production→404, name prefix→403 | `profiles.py:489-496`; prefix const at `profiles.py:82` |
| `docs/` dir wiped + recreated | `profiles.py:519-522` |
| 23 profile-scoped models total | `models/__init__.py` (22) + `models/response_feedback.py` (not re-exported) |
| Missing: ResponseFeedback, PinboardItem, Pinboard, ChatTurn, ChatSession, CarePlanTask | confirmed by diff of model list vs delete list |
| FK edges relevant to ordering | `ChatTurn→chat_sessions` (`chat_session.py:87`); `PinboardItem→pinboard` (`pinboard.py:40`); `CarePlanTask→documents,document_entity` (`care_plan_task.py:38-43`); `EarnedBadge→badge_definition` (`gamification.py:56`); `ResponseFeedback` has NO db-level FK (logical `turn_id` only, `response_feedback.py:48-54`) |
| `route_client` harness; hardcodes `profile_name="T"`, no profile-db override | `tests/support/routes.py:26-57` |
| Prior art for `get_profile_db_session` override | `tests/test_timeline.py:262-286`, `tests/test_observations_audit.py:133` |
| No existing tests for this endpoint | `grep "test/reset" tests/` → no hits |
| e2e caller | `src/frontend/e2e/support/auth.ts:51` |

## File structure

- **Modify** `src/backend/tests/support/routes.py` — add `profile_name` and `profile_db` params (backward compatible).
- **Modify** `src/backend/api/profiles.py` — add `_SYNTHETIC_RESET_MODELS` constant, extend imports, replace inline tuple, add audit logging.
- **Create** `src/backend/tests/test_profile_test_reset.py` — all new tests (`test_hc_reset_*`).

## Residual-state decision table (what "reset" covers)

| State | Action | Why |
|---|---|---|
| All profile-vault table rows except `badge_definition` | **Delete** (this fix) | Patient data; e2e isolation requires it |
| `vaults/{pid}/docs/` files | Already wiped (`:519-522`) | Keep; tests set `app_data_path` to `tmp_path` |
| `vault.db`, key files | **Untouched** | Would brick the vault — reset is not delete |
| `backups/{profile_id}/` | **Untouched** | Belong to profile lifecycle/deletion, not test reset |
| `api/export.py` in-memory `_summary_store`/`_packet_store`/`_fhir_store` (`:44,:47,:50`) | **Flag, out of scope** | Already P1 for being in-memory; keyed by artifact UUID, die on restart; purging belongs with that P1 fix. Record in plan notes |
| Semantic cache / LLM caches (`modules/rag`, `core/llm`) | **Investigate in Task 3**; flag if keyed by profile | Stale cache could leak prior test's context into post-reset answers; out of scope unless purge is trivial |
| `BackupSchedule`, `AuditLog` (master tables) | **Untouched** | Master DB, not profile data. Audit should gain a `synthetic_test_reset` event row (hard invariant: audit logging on every route touching profile data — currently missing) |

---

### Task 1: Extend `route_client` and write failing tests

**Files:**
- Modify: `src/backend/tests/support/routes.py`
- Test: `src/backend/tests/test_profile_test_reset.py` (create)

**Interfaces:**
- Produces: `route_client(router, prefix, profile_id="profile-a", profile_name="T", master_db=None, profile_db=None)` — `profile_db` accepts an `async_sessionmaker`; when given, `get_profile_db_session` is overridden to yield a session from it.
- Produces: test fixture `profile_session_factory` (real sqlite vault DB, `ProfileDatabaseBase.metadata.create_all`), reused by Task 2/3 tests.

- [ ] **Step 1: Extend `route_client`**

In `tests/support/routes.py`, add the import and new params (defaults preserve current behavior for all existing callers):

```python
from core.auth import Session, get_profile_db_session, require_auth
```

```python
@contextmanager
def route_client(
    router: APIRouter,
    prefix: str,
    profile_id: str = "profile-a",
    profile_name: str = "T",
    master_db: Optional[object] = None,
    profile_db: Optional[object] = None,
) -> Iterator[TestClient]:
    """Yield a TestClient for `router` with auth and the master DB overridden.

    `master_db` defaults to an AsyncMock, which is enough for routes that only
    write audit rows. `profile_db` (an async_sessionmaker) overrides the
    per-profile vault dependency `get_profile_db_session`.
    """
    app = FastAPI()
    app.include_router(router, prefix=prefix)

    db = master_db if master_db is not None else AsyncMock()

    async def _override_auth() -> Session:
        return Session(
            profile_id=profile_id,
            profile_name=profile_name,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            token_jti="jti-test",
        )

    async def _override_master_db():
        return db

    app.dependency_overrides[require_auth] = _override_auth
    app.dependency_overrides[get_db] = _override_master_db

    if profile_db is not None:

        async def _override_profile_db():
            async with profile_db() as session:
                yield session

        app.dependency_overrides[get_profile_db_session] = _override_profile_db

    with TestClient(app) as client:
        yield client
```

- [ ] **Step 2: Create the test file**

First check how an existing test imports the harness (`grep -rn "support.routes\|route_client" src/backend/tests/`) and match that import path — `tests/` may not be a package. Also check `tests/conftest.py` for an existing profile-DB fixture; if one exists, use it instead of the fixture below. Fallback complete file:

```python
"""HC-RESET: POST /profiles/test/reset must clear every profile-scoped table.

Audit 2026-09-25 §11 P2: the synthetic reset skipped ChatSession, ChatTurn,
ResponseFeedback, CarePlanTask, Pinboard and PinboardItem, leaving stale rows
that cross-contaminate Playwright e2e runs.
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from api.profiles import router
from core.config import settings
from core.profile_database import ProfileDatabaseBase
from models import (
    BadgeDefinition,
    CarePlanTask,
    ChatSession,
    ChatTurn,
    Pinboard,
    PinboardItem,
)
from models.response_feedback import ResponseFeedback  # not re-exported by models/
from tests.support.routes import route_client

E2E_NAME = "Playwright E2E Reset"

# Reference/seed tables the reset must NOT clear: badge_definition rows are
# written by profile migration 003 and nothing re-seeds them.
REFERENCE_TABLES = {"badge_definition"}

# The six tables the audit flagged as missed.
AUDIT_FLAGGED_MODELS = (
    ResponseFeedback,
    PinboardItem,
    Pinboard,
    ChatTurn,
    ChatSession,
    CarePlanTask,
)


@pytest_asyncio.fixture
async def profile_session_factory(tmp_path, monkeypatch):
    """Real per-profile vault DB on a throwaway sqlite file.

    NullPool: sessions are opened per-call and the endpoint runs them on
    TestClient's portal loop — pooled connections are event-loop-bound.
    """
    monkeypatch.setattr(settings, "app_data_path", str(tmp_path))
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{tmp_path}/vault.db", poolclass=NullPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def _seed_audit_flagged_tables(factory) -> None:
    """Insert one row into each table the audit says reset misses."""
    async with factory() as s:
        chat = ChatSession(
            id=str(uuid.uuid4()), profile_id="profile-a", title="t"
        )
        s.add(chat)
        await s.flush()  # chat_turns.session_id needs the parent id
        s.add(
            ChatTurn(
                id=str(uuid.uuid4()),
                session_id=chat.id,
                profile_id="profile-a",
                turn_index=0,
                role="user",
                content="hello",
            )
        )
        s.add(
            ResponseFeedback(
                id=str(uuid.uuid4()),
                profile_id="profile-a",
                session_id=chat.id,
                turn_id="turn-1",
                rating=1,
            )
        )
        s.add(CarePlanTask(id=str(uuid.uuid4()), title="Book follow-up"))
        board = Pinboard(id=str(uuid.uuid4()), name="b")
        s.add(board)
        await s.flush()  # pinboard_item.pinboard_id needs the parent id
        s.add(
            PinboardItem(
                id=str(uuid.uuid4()),
                pinboard_id=board.id,
                item_type="observation",
                item_id="obs-1",
            )
        )
        await s.commit()


async def _count(session, model) -> int:
    result = await session.execute(select(func.count()).select_from(model))
    return result.scalar_one()


async def test_hc_reset_001_clears_audit_flagged_tables(profile_session_factory):
    """Each of the 6 missed tables is seeded, then must be empty after reset."""
    await _seed_audit_flagged_tables(profile_session_factory)
    with route_client(
        router,
        prefix="/profiles",
        profile_id="profile-a",
        profile_name=E2E_NAME,
        profile_db=profile_session_factory,
    ) as client:
        resp = client.post("/profiles/test/reset")
    assert resp.status_code == 204
    async with profile_session_factory() as s:
        for model in AUDIT_FLAGGED_MODELS:
            assert await _count(s, model) == 0, (
                f"{model.__tablename__} still has rows after reset"
            )


async def test_hc_reset_002_every_cleared_table_is_empty(profile_session_factory):
    """Parametrized over the endpoint's own model list: no table can be skipped."""
    from api.profiles import _SYNTHETIC_RESET_MODELS

    await _seed_audit_flagged_tables(profile_session_factory)
    with route_client(
        router,
        prefix="/profiles",
        profile_id="profile-a",
        profile_name=E2E_NAME,
        profile_db=profile_session_factory,
    ) as client:
        resp = client.post("/profiles/test/reset")
    assert resp.status_code == 204
    async with profile_session_factory() as s:
        for model in _SYNTHETIC_RESET_MODELS:
            assert await _count(s, model) == 0, (
                f"{model.__tablename__} still has rows after reset"
            )


def test_hc_reset_010_reset_list_covers_every_profile_table():
    """Anti-drift invariant: a new profile-scoped model that is not added to
    the reset list fails here — metadata and the endpoint cannot diverge."""
    from api.profiles import _SYNTHETIC_RESET_MODELS

    all_tables = set(ProfileDatabaseBase.metadata.tables)
    covered = {m.__tablename__ for m in _SYNTHETIC_RESET_MODELS}
    assert covered == all_tables - REFERENCE_TABLES, (
        f"reset misses {sorted(all_tables - REFERENCE_TABLES - covered)}; "
        f"unexpected extras {sorted(covered - all_tables)}"
    )


def test_hc_reset_011_delete_order_respects_foreign_keys():
    """SQL-FK-001: children must precede parents in the delete order.
    Before plan 06 lands, FK enforcement is off and this ordering is the only
    thing preventing dangling references; after plan 06 turns
    PRAGMA foreign_keys ON, a parent-first order would raise IntegrityError.
    The property holds in both states. (Wording corrected 2026-09-27, review F-07.)"""
    from api.profiles import _SYNTHETIC_RESET_MODELS

    order = {m.__tablename__: i for i, m in enumerate(_SYNTHETIC_RESET_MODELS)}
    for table in ProfileDatabaseBase.metadata.tables.values():
        if table.name not in order:
            continue
        for fk in table.foreign_keys:
            parent = fk.column.table.name
            if parent in order:
                assert order[table.name] < order[parent], (
                    f"{table.name} is deleted after its parent {parent}"
                )


async def test_hc_reset_020_production_mode_returns_404(
    profile_session_factory, monkeypatch
):
    monkeypatch.setattr(settings, "app_env", "production")
    with route_client(
        router,
        prefix="/profiles",
        profile_name=E2E_NAME,
        profile_db=profile_session_factory,
    ) as client:
        resp = client.post("/profiles/test/reset")
    assert resp.status_code == 404


async def test_hc_reset_021_non_synthetic_profile_returns_403(
    profile_session_factory,
):
    with route_client(
        router,
        prefix="/profiles",
        profile_name="Regular User",
        profile_db=profile_session_factory,
    ) as client:
        resp = client.post("/profiles/test/reset")
    assert resp.status_code == 403


async def test_hc_reset_030_badge_definitions_survive(profile_session_factory):
    """badge_definition is migration-seeded reference data — reset must keep it."""
    async with profile_session_factory() as s:
        s.add(
            BadgeDefinition(
                id="first-log",
                name="First Log",
                description="d",
                icon="i",
                criteria_type="count",
                criteria_json="{}",
            )
        )
        await s.commit()
    with route_client(
        router,
        prefix="/profiles",
        profile_name=E2E_NAME,
        profile_db=profile_session_factory,
    ) as client:
        assert client.post("/profiles/test/reset").status_code == 204
    async with profile_session_factory() as s:
        assert await _count(s, BadgeDefinition) == 1
```

Executor notes:
- If `create_async_engine` rejects `sqlite+aiosqlite` (project may use a sqlcipher dialect for vaults), copy the engine pattern from `core/profile_database.py` or the profile-session fixture in `tests/test_observations_audit.py:~120-140` / `tests/test_timeline.py:255-290`. Plain sqlite is sufficient — the test only needs the schema and real deletes.
- If pydantic-settings rejects `monkeypatch.setattr(settings, ...)`, use `monkeypatch.setattr("api.profiles.settings", <stand-in>)` or construct the app without `settings` mutation; verify Settings mutability in `core/config.py:27` first.

- [ ] **Step 3: Run tests to verify RED**

```bash
cd src/backend
find . -name __pycache__ -type d -exec rm -rf {} +   # WSL/9p stale-bytecode guard
python -m pytest tests/test_profile_test_reset.py -p no:cacheprovider -v
```

Expected:
- `test_hc_reset_001` FAIL — the 6 tables still hold rows (endpoint never deletes them).
- `test_hc_reset_002` / `test_hc_reset_010` / `test_hc_reset_011` FAIL — `ImportError: cannot import name '_SYNTHETIC_RESET_MODELS'`.
- `test_hc_reset_020` / `test_hc_reset_021` / `test_hc_reset_030` PASS — pinning existing hardening (if 020/021 fail here, the guard is already broken — stop and report).

- [ ] **Step 4: Commit the test scaffold**

```bash
git add tests/support/routes.py tests/test_profile_test_reset.py
git commit -m "test(profiles): failing coverage tests for test-reset table list"
```

---

### Task 2: Ordered full-table delete in the endpoint

**Files:**
- Modify: `src/backend/api/profiles.py` (imports `:52-72`, new constant after `:82`, endpoint body `:498-532`)

**Interfaces:**
- Consumes: `AUDIT_FLAGGED_MODELS`, `route_client(..., profile_db=...)` from Task 1.
- Produces: `api.profiles._SYNTHETIC_RESET_MODELS: tuple[type, ...]` — every profile-scoped model the reset clears, children before parents.

- [ ] **Step 1: Add model imports**

In the `from models import (...)` block at `profiles.py:52-72`, add `CarePlanTask`, `ChatSession`, `ChatTurn`, `Pinboard`, `PinboardItem` (alphabetical, matching existing order). Add a separate import — `ResponseFeedback` is not re-exported by `models/__init__.py` (`api/feedback.py:37` already imports it this way):

```python
from models.response_feedback import ResponseFeedback
```

- [ ] **Step 2: Define `_SYNTHETIC_RESET_MODELS`**

After `_SYNTHETIC_E2E_PROFILE_PREFIX = "Playwright E2E"` (`profiles.py:82`):

```python
# Profile tables wiped by POST /profiles/test/reset, in FK-safe order:
# children before parents. Pre-plan-06 (FK enforcement off) this ordering is the
# only thing preventing dangling references; post-plan-06 (PRAGMA foreign_keys=ON)
# a parent-first order would raise. Keep child-first in both states.
# Deliberately absent: badge_definition — migration-seeded reference data
# (profile migration 003), not patient data; nothing re-seeds it.
# test_hc_reset_010 fails if a profile table is added without updating this.
_SYNTHETIC_RESET_MODELS = (
    ResponseFeedback,       # logical turn_id -> chat_turns (no db FK)
    PinboardItem,           # FK -> pinboard
    Pinboard,
    ChatTurn,               # FK -> chat_sessions
    ChatSession,
    CarePlanTask,           # FK -> documents, document_entity
    Embedding,              # FK -> chunks
    Chunk,                  # FK -> documents
    DocumentEntity,         # FK -> documents
    DocumentCategory,       # FK -> documents
    LabInterpretation,      # FK -> observations
    PanelInterpretation,
    Observation,            # FK -> documents
    Document,
    DoseTaken,              # FK -> medications, medication_schedules
    ReminderLog,            # FK -> medications, medication_schedules
    AdherencePattern,       # FK -> medications
    MedicationSchedule,     # FK -> medications
    Medication,
    MemoryItem,
    UserModelSettings,
    EarnedBadge,            # FK -> badge_definition (parent kept: seed data)
)
```

(Ordering verified against every `ForeignKey` in `models/`; `CarePlanTask` sits before both `DocumentEntity` and `Document` because it references both.)

- [ ] **Step 3: Replace the inline tuple and add the audit event**

`profiles.py:477-481` — add the master-db dependency param (audit invariant: routes touching profile data must log):

```python
@router.post("/test/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset_synthetic_test_profile(
    session: RequireAuth,
    profile_db: ProfileDbSession,
    db: AsyncSession = Depends(get_db),
):
```

Replace the loop at `:499-517` and append audit logging before the return:

```python
    try:
        for model in _SYNTHETIC_RESET_MODELS:
            await profile_db.execute(delete(model))

        docs_path = Path(settings.app_data_path) / "vaults" / session.profile_id / "docs"
        if docs_path.exists():
            shutil.rmtree(docs_path)
        docs_path.mkdir(parents=True, exist_ok=True)

        await profile_db.commit()
    except Exception as exc:
        await profile_db.rollback()
        logger.exception("Synthetic profile reset failed for %s", session.profile_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Synthetic profile reset failed: {exc}",
        ) from exc

    await log_profile_event(
        db=db,
        event="synthetic_test_reset",
        profile_id=session.profile_id,
        profile_name=session.profile_name,
    )
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

(`log_profile_event` signature copied from the logout handler at `:460-465`. It stages a row on the master session; the commit persists it. In tests, `route_client`'s default `AsyncMock` master db absorbs this.)

- [ ] **Step 4: Run tests to verify GREEN**

```bash
cd src/backend
python -m pytest tests/test_profile_test_reset.py -p no:cacheprovider -v
```

Expected: all 7 tests PASS. If `test_hc_reset_010` fails, its diff message names exactly which table is missing/extra — fix the constant, not the test.

- [ ] **Step 5: Commit**

```bash
git add src/backend/api/profiles.py
git commit -m "fix(profiles): test-reset covers all profile tables in FK-safe order"
```

---

### Task 3: Residual-state sweep, baseline verification, docs

**Files:**
- Investigate only (no code changes unless noted): `src/backend/modules/rag/`, `src/backend/core/llm/`, `src/backend/api/export.py`
- Modify: `docs/features/TASK_LIST.md` (Session Notes), `docs/agentic/recurring-failures.md` (only if a new instance observed)

- [ ] **Step 1: Sweep for other profile-keyed in-memory/FS state**

```bash
cd src/backend
grep -rn "settings.app_data_path" api/ modules/ core/ | grep -v "vaults.*docs"
grep -rn "_store\b\|_cache\b" modules/rag/ core/llm/ | head -30
```

Expected: confirm `vaults/{pid}/docs` is the only vault subdir written by product code; identify whether any module-level dict caches per-profile data (semantic cache, export stores). The `api/export.py` stores (`:44,:47,:50`) are known P1 — do NOT fix here; note them in the commit/PR. If a trivially-purgeable per-profile cache exists and reset should cover it, discuss before adding — conservative beats clever.

- [ ] **Step 2: Guard hardening decision — record it**

Guards verified: production→404 + name-prefix→403 + JWT + open vault. Blast radius = caller's own vault only. Record in `TASK_LIST.md` session notes: "guard assessed adequate; no strengthening needed." If reviewer disagrees, candidate hardening = also require `settings.debug` — out of scope here.

- [ ] **Step 3: Full baseline**

```bash
cd src/backend
find . -name __pycache__ -type d -exec rm -rf {} +
python -m pytest tests/ -p no:cacheprovider -q
```

Expected: collected count = **(count measured at the start of this plan) + 7** (corrected 2026-09-27; was "1245 + 7 = 1252". This plan runs after plans 01–06, the merged tree alone collected 1,291 on 2026-09-27, and plans 02 and 06 add tests). All pass except possibly `test_api_rag_index_002b` (environmental — needs a real embedding model; do not touch its 0.7 threshold).

```bash
cd src/backend && python -c "from main import app"
```

Expected: clean import (catches a bad model import).

- [ ] **Step 4: Docs + failure-mode check**

- Re-read `docs/agentic/recurring-failures.md`. This bug is a new instance of **mode: "assertion can't see what it doesn't check"** (endpoint iterated a hand-maintained list; nothing compared it to metadata). If the file's mode list covers this, note the instance in Session Notes; if not, add a short entry in the same commit.
- Append a Session Note to `docs/features/TASK_LIST.md`: date, `POST /profiles/test/reset` now clears all 22 patient-data profile tables in FK order via `_SYNTHETIC_RESET_MODELS`; `badge_definition` intentionally retained; metadata-enumeration test prevents drift; `route_client` gained `profile_name`/`profile_db` params.

- [ ] **Step 5: Final commit**

```bash
git add docs/features/TASK_LIST.md docs/agentic/recurring-failures.md 2>/dev/null
git commit -m "docs: log test-reset table coverage fix"
```

---

## Self-review notes

- Spec coverage: failing seed→reset→assert-empty test (001/002) ✓; metadata enumeration anti-drift test (010) ✓; FK-order check (011) ✓; guard pinning via route_client (020/021) ✓; ordered implementation ✓; verification commands ✓.
- All code complete; no placeholders. Executor-verification points are stated inline where repo state could not be fully pre-verified (fixture dialect, settings mutability, import path, migration-003 seeding).
