# Phase A: Audit Fix Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make PR #18's backup/restore feature actually reachable and correct, and close the testing gap that let a permanently-broken endpoint pass 32 tests.

**Architecture:** The root cause is a test-harness gap, so Task 1 builds a route-level `TestClient` harness before any fix. Tasks 2–4 then fix the three blockers, each proven by a test that fails first. Tasks 5–9 clear the medium findings. Task 10 corrects two tracker rows that claim work is DONE when the code has no callers.

**Tech Stack:** Python 3.11, FastAPI, pytest, SQLAlchemy/SQLCipher, React 18 + TypeScript, Vitest.

**Spec:** `docs/superpowers/specs/2026-07-30-remediation-and-asclexis-design.md`

## Global Constraints

- Target **Python 3.11+**. Do not use 3.12-only syntax or APIs.
- Use `core.time.utcnow` as the single timestamp helper. Never `datetime.utcnow()`.
- All LLM calls go through the `ModelRunner` facade. Never import `llama_cpp` or call Ollama from feature code.
- **Never weaken a safety check, lower a test threshold, or relax a validation to make something pass.** The known env-only failure `test_api_rag_index_002b` stays failing; its 0.7 threshold is untouched.
- **Ask before touching** `modules/interpret_safety.py`, `modules/redaction.py`, `modules/faithfulness.py`, `modules/verifier_agent.py`, or anything auth/encryption. This plan does not modify them.
- Per-profile data isolation: patient data lives in per-profile SQLCipher DBs via `ProfileDbSession`. Never query profile data through the master `get_db()`.
- Audit logging on every route touching documents, observations, or profile data.
- Baseline to preserve: **1205 backend tests pass, 1 known env-only failure**. `npx tsc --noEmit` clean. Playwright **25 passed / 3 skipped**.
- Commit style: `fix(scope):` / `feat(scope):` / `docs:` — small, single-purpose commits.
- Branch: `claude/backlog-repo-docs-yl7isc`. Tasks 1–4 and 10 target PR #18; Tasks 5–9 go to a follow-up PR.
- Every fix is **test-first**: write the test, run it, *observe the failure*, then fix. A test that never failed proves nothing.

## File Structure

| File | Responsibility | Change |
|---|---|---|
| `src/backend/tests/support/routes.py` | Route-level `TestClient` harness — builds an app with one router mounted and auth/db overridden | **Create** |
| `src/backend/tests/test_backup_routes.py` | Route-level tests that exercise the real FastAPI dependency graph | **Create** |
| `src/backend/api/backup.py` | Backup routes | Modify: `:170` traversal guard, `:360` restore dependency, `download_backup` master-DB exclusion, partial-failure response |
| `src/backend/scripts/backup.py` | Backup/restore/prune engine | Modify: `RestoreResult.partial`, download-scoped master extract |
| `src/backend/api/profiles.py` | Profile routes | Modify: `:732` timestamp helper |
| `src/backend/core/audit.py` | Audit scrubber | Modify: `:181` drift-warning condition |
| `src/frontend/src/pages/VerificationWorkbench.tsx` | Verification workbench | Modify: citation effects |
| `src/frontend/src/components/settings/BackupCard.tsx` | Backup UI | Modify: partial-failure copy |
| `docs/features/TASK_LIST.md` | Tracker | Modify: correct two DONE rows |

`tests/support/routes.py` is new because the override pattern currently lives duplicated inline in `test_timeline.py:262-286` and `test_observations_audit.py:132-134`. Extracting it once is what makes route-level testing cheap enough that the next person actually does it.

---

## Task 1: Route-level test harness

**Files:**
- Create: `src/backend/tests/support/routes.py`
- Create: `src/backend/tests/support/__init__.py` (empty)
- Test: `src/backend/tests/test_backup_routes.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: `route_client(router, prefix, profile_id="profile-a", master_db=None) -> contextmanager[TestClient]` — yields a `TestClient` for a `FastAPI` app with only `router` mounted at `prefix`, with `require_auth` and `get_db` overridden. Tasks 2–5 depend on this exact signature.

**Why:** Every existing backup route test calls handlers as plain functions (`await restore_backup(backup_id, payload=..., session=...)`), so FastAPI never resolves `Depends(...)`. That is why Task 2's bug survived 32 passing tests. This harness makes the dependency graph run.

- [ ] **Step 1: Create the package marker**

```bash
mkdir -p src/backend/tests/support && touch src/backend/tests/support/__init__.py
```

- [ ] **Step 2: Write the harness**

Create `src/backend/tests/support/routes.py`:

```python
"""Route-level test harness.

Calling a route function directly skips FastAPI's dependency graph, so a broken
`Depends(...)` is invisible to the test. That is exactly how a restore endpoint
that returned 400 for every request passed 32 tests. Any test asserting on
auth, path scoping, or status codes must go through HTTP.

Follows the override pattern already used in test_timeline.py and
test_observations_audit.py, extracted so it is cheap to reuse.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Iterator, Optional
from unittest.mock import AsyncMock

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from core.auth import Session, require_auth
from core.database import get_db


@contextmanager
def route_client(
    router: APIRouter,
    prefix: str,
    profile_id: str = "profile-a",
    master_db: Optional[object] = None,
) -> Iterator[TestClient]:
    """Yield a TestClient for `router` with auth and the master DB overridden.

    `master_db` defaults to an AsyncMock, which is enough for routes that only
    write audit rows. Pass a real session when the assertion needs one.
    """
    app = FastAPI()
    app.include_router(router, prefix=prefix)

    db = master_db if master_db is not None else AsyncMock()

    async def _override_auth() -> Session:
        return Session(
            profile_id=profile_id,
            profile_name="T",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            token_jti="jti-test",
        )

    async def _override_master_db():
        return db

    app.dependency_overrides[require_auth] = _override_auth
    app.dependency_overrides[get_db] = _override_master_db

    with TestClient(app) as client:
        yield client
```

- [ ] **Step 3: Write a test proving the harness resolves dependencies**

Create `src/backend/tests/test_backup_routes.py`:

```python
"""Route-level tests for the backup API (HC-BKUP-033+).

These go through HTTP so FastAPI's dependency graph actually executes. The
direct-call tests in test_backup_api.py cover handler logic; these cover
whether the endpoint is reachable at all.
"""

from __future__ import annotations

import sqlite3

import pytest

import api.backup as backup_api
from tests.support.routes import route_client


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Point app_data_path at a temp dir with two seeded profiles."""
    monkeypatch.setattr(
        type(backup_api.settings), "app_data_path", property(lambda self: tmp_path)
    )
    for pid in ("profile-a", "profile-b"):
        vault = tmp_path / "vaults" / pid
        vault.mkdir(parents=True)
        conn = sqlite3.connect(vault / "vault.db")
        conn.execute("CREATE TABLE observations (id TEXT)")
        conn.commit()
        conn.close()
        (vault / "key.bin").write_bytes(b"sealed-" + pid.encode())
        (vault / "key.method").write_text("password")
    conn = sqlite3.connect(tmp_path / "healthcentral.db")
    conn.execute("CREATE TABLE profiles (id TEXT)")
    conn.commit()
    conn.close()
    return tmp_path


def test_hc_bkup_033_harness_resolves_dependencies(data_dir):
    """The harness must actually run Depends(...) — otherwise it is no better
    than a direct call. GET /backup/ requires auth; a 200 proves the override
    resolved rather than the dependency being skipped."""
    with route_client(backup_api.router, "/backup") as client:
        response = client.get("/backup/")

    assert response.status_code == 200, response.text
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd src/backend && python -m pytest tests/test_backup_routes.py -p no:cacheprovider -v`
Expected: `1 passed`. If it errors with `ModuleNotFoundError: tests.support`, confirm `tests/support/__init__.py` exists.

- [ ] **Step 5: Commit**

```bash
git add src/backend/tests/support/ src/backend/tests/test_backup_routes.py
git commit -m "test(backup): add a route-level TestClient harness

Every backup route test calls handlers as plain functions, so FastAPI's
dependency graph never runs and a broken Depends() is invisible. Extracts the
override pattern already inlined in test_timeline.py so route-level testing is
cheap enough to be the default for anything asserting auth or status codes."
```

---

## Task 2: Restore endpoint returns 400 on every request (BLOCKER)

**Files:**
- Modify: `src/backend/api/backup.py:360`
- Test: `src/backend/tests/test_backup_routes.py`

**Interfaces:**
- Consumes: `route_client` from Task 1.
- Produces: nothing new; `restore_backup` keeps its signature minus the `request` parameter's dependency change.

**Why:** `session: Session = Depends(require_profile_access())` reads `request.path_params["profile_id"]`. The route's only path param is `backup_id`, so the dependency raises before the handler runs. Verified live: `400 {"detail":"Missing profile_id parameter"}`. The whole restore feature is unreachable over HTTP.

- [ ] **Step 1: Write the failing test**

Append to `src/backend/tests/test_backup_routes.py`:

```python
def test_hc_bkup_034_restore_route_is_reachable(data_dir, monkeypatch):
    """The regression that 32 direct-call tests could not see: the route used
    Depends(require_profile_access()), which reads path_params["profile_id"] —
    a parameter this route does not have — so every request 400'd before any
    handler logic ran."""
    from unittest.mock import AsyncMock
    from types import SimpleNamespace

    with route_client(backup_api.router, "/backup") as client:
        created = client.post("/backup/")
        assert created.status_code == 201, created.text
        backup_id = created.json()["backup_id"]

        monkeypatch.setattr(
            backup_api,
            "authenticate_profile",
            AsyncMock(return_value=SimpleNamespace(id="profile-a")),
        )
        monkeypatch.setattr(
            backup_api, "close_profile_database_on_logout", AsyncMock()
        )

        response = client.post(
            f"/backup/{backup_id}/restore",
            json={
                "password": "CorrectHorse1",
                "confirmation_phrase": backup_api.BACKUP_RESTORE_CONFIRMATION,
            },
        )

    assert response.status_code == 200, response.text
    assert response.json()["files_restored"] > 0
```

- [ ] **Step 2: Run it and observe the failure**

Run: `cd src/backend && python -m pytest tests/test_backup_routes.py::test_hc_bkup_034_restore_route_is_reachable -p no:cacheprovider -v`
Expected: **FAIL** with `assert 400 == 200` and body `{"detail":"Missing profile_id parameter"}`. Do not proceed until you see this exact failure — it is the proof the test is real.

- [ ] **Step 3: Fix the dependency**

In `src/backend/api/backup.py`, change the `restore_backup` signature. Replace:

```python
    session: Session = Depends(require_profile_access()),
```

with:

```python
    session: RequireAuth,
```

Then add this comment directly above the signature block:

```python
    # RequireAuth, not require_profile_access(): that dependency reads a
    # `profile_id` path parameter this route does not have, so it 400'd every
    # request. The route is single-profile by construction anyway —
    # _resolve_backup_dir(session.profile_id, ...) already scopes it — so
    # adding a profile_id path param would only add a spoofable input.
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd src/backend && python -m pytest tests/test_backup_routes.py -p no:cacheprovider -v`
Expected: all pass.

- [ ] **Step 5: Check for now-unused imports**

Run: `cd src/backend && grep -n "require_profile_access" api/backup.py`
Expected: no output. If the import at `api/backup.py:36-40` is now unused, remove `require_profile_access` from it. Then confirm the module still imports: `python -c "import api.backup"`.

- [ ] **Step 6: Run the full suite**

Run: `cd src/backend && python -m pytest tests/ -p no:cacheprovider -q`
Expected: `1206 passed, 1 failed` — the failure being only `test_api_rag_index_002b`.

- [ ] **Step 7: Commit**

```bash
git add src/backend/api/backup.py src/backend/tests/test_backup_routes.py
git commit -m "fix(backup): make the restore endpoint reachable

Depends(require_profile_access()) reads path_params['profile_id']; this route's
only path param is backup_id, so every restore request returned 400 before any
handler logic ran. The feature has never worked over HTTP.

The 32 existing backup tests missed it because they call route functions
directly, so the dependency never resolved. HC-BKUP-034 goes through HTTP and
was observed failing with the real 400 first."
```

---

## Task 3: Downloaded backups leak other profiles' credentials (BLOCKER)

**Files:**
- Modify: `src/backend/api/backup.py` (`download_backup`)
- Modify: `src/backend/tests/test_backup_api.py` (replace HC-BKUP-014's assertion)
- Test: `src/backend/tests/test_backup_routes.py`

**Interfaces:**
- Consumes: `route_client` from Task 1; `MASTER_DB_NAME` from `scripts/backup.py`.
- Produces: `_single_profile_master_bytes(master_path: Path, profile_id: str) -> bytes` in `api/backup.py` — an in-memory SQLite copy of the master DB containing only that profile's row. Task 4 does not depend on it.

**Why:** `_discover_databases` retains `healthcentral.db` in profile-scoped backups (restore needs `password_hash`), and `download_backup` does `path.rglob("*")` into the zip. So a user's own downloaded archive carries every other profile's `display_name`, bcrypt `password_hash`, `password_salt`, and the whole `audit_logs` table. `HC-BKUP-014` looked like isolation coverage but asserts only on *filenames*, so it passes while the data leaks inside a file with an innocuous name.

- [ ] **Step 1: Write the failing test**

Append to `src/backend/tests/test_backup_routes.py`:

```python
def test_hc_bkup_035_download_carries_only_this_profile(data_dir):
    """A profile-scoped backup keeps the master DB on disk because restore needs
    the password hash. The download must NOT: it leaves the device, and the
    master DB holds every profile's row and the whole audit trail."""
    import io
    import zipfile

    master = data_dir / "healthcentral.db"
    conn = sqlite3.connect(master)
    conn.execute("DROP TABLE IF EXISTS profiles")
    conn.execute(
        "CREATE TABLE profiles (id TEXT, display_name TEXT, password_hash TEXT)"
    )
    conn.executemany(
        "INSERT INTO profiles VALUES (?, ?, ?)",
        [
            ("profile-a", "Ann", "hash-a"),
            ("profile-b", "Bob", "hash-b"),
        ],
    )
    conn.commit()
    conn.close()

    with route_client(backup_api.router, "/backup") as client:
        created = client.post("/backup/")
        assert created.status_code == 201, created.text
        backup_id = created.json()["backup_id"]

        response = client.get(f"/backup/{backup_id}/download")

    assert response.status_code == 200
    archive = zipfile.ZipFile(io.BytesIO(response.content))

    # The vault must still be there — scoping the master must not gut the zip.
    assert any(n.endswith("vault.db") for n in archive.namelist())
    assert any(n.endswith("key.bin") for n in archive.namelist())

    # The assertion HC-BKUP-014 could not make: open the master DB *inside* the
    # archive and confirm it names exactly one profile.
    extracted = archive.read("healthcentral.db")
    scratch = data_dir / "from_zip.db"
    scratch.write_bytes(extracted)
    conn = sqlite3.connect(scratch)
    rows = conn.execute("SELECT id, display_name FROM profiles").fetchall()
    conn.close()

    assert rows == [("profile-a", "Ann")], f"leaked other profiles: {rows}"
```

- [ ] **Step 2: Run it and observe the failure**

Run: `cd src/backend && python -m pytest tests/test_backup_routes.py::test_hc_bkup_035_download_carries_only_this_profile -p no:cacheprovider -v`
Expected: **FAIL** with `leaked other profiles: [('profile-a', 'Ann'), ('profile-b', 'Bob')]`.

- [ ] **Step 3: Add the single-profile extract helper**

In `src/backend/api/backup.py`, add above `download_backup`:

```python
def _single_profile_master_bytes(master_path: Path, profile_id: str) -> bytes:
    """A copy of the master DB holding only this profile's rows.

    The on-disk backup keeps the full master DB because restore needs this
    profile's password_hash, which lives there while the sealed key travels in
    the vault (BK-01). A *download* leaves the device, so it must not carry
    another profile's display_name, password hash, or audit history. Restore and
    export have opposite requirements; one artifact cannot serve both.
    """
    with tempfile.TemporaryDirectory() as tmp:
        scoped = Path(tmp) / MASTER_DB_NAME
        shutil.copy2(master_path, scoped)
        conn = sqlite3.connect(scoped)
        try:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            for table in ("profiles", "audit_logs", "backup_schedules"):
                if table not in tables:
                    continue
                columns = {
                    row[1] for row in conn.execute(f"PRAGMA table_info({table})")
                }
                if "profile_id" in columns:
                    conn.execute(
                        f"DELETE FROM {table} WHERE profile_id != ?", (profile_id,)
                    )
                elif "id" in columns and table == "profiles":
                    conn.execute("DELETE FROM profiles WHERE id != ?", (profile_id,))
            conn.commit()
            conn.execute("VACUUM")
            conn.commit()
        finally:
            conn.close()
        return scoped.read_bytes()
```

Add these imports at the top of `api/backup.py` if absent: `import shutil`, `import sqlite3`, `import tempfile`, and `from scripts.backup import MASTER_DB_NAME` (check the existing `backup_script` import style first and match it — if the module is imported as `backup_script`, use `backup_script.MASTER_DB_NAME` instead of a new import).

- [ ] **Step 4: Use it in `download_backup`**

In `download_backup`, replace the archive-building loop:

```python
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(path.rglob("*")):
            if file_path.is_file():
                archive.write(file_path, arcname=str(file_path.relative_to(path)))
    buffer.seek(0)
```

with:

```python
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(path.rglob("*")):
            if not file_path.is_file():
                continue
            arcname = str(file_path.relative_to(path))
            if file_path.name == MASTER_DB_NAME:
                # Scoped copy, not the shared file — see
                # _single_profile_master_bytes.
                archive.writestr(
                    arcname,
                    _single_profile_master_bytes(file_path, session.profile_id),
                )
            else:
                archive.write(file_path, arcname=arcname)
    buffer.seek(0)
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd src/backend && python -m pytest tests/test_backup_routes.py -p no:cacheprovider -v`
Expected: all pass.

- [ ] **Step 6: Replace HC-BKUP-014's filename-only assertion**

In `src/backend/tests/test_backup_api.py`, find in `test_hc_bkup_014_download_streams_a_complete_zip`:

```python
    # And it must not contain another profile's vault.
    assert not any("profile-b" in n for n in names)
```

Replace with:

```python
    # A filename check cannot see inside healthcentral.db, which is where the
    # real cross-profile leak lived. Isolation is asserted properly in
    # test_backup_routes.py::test_hc_bkup_035; keep the cheap check here too.
    assert not any("profile-b" in n for n in names)
    assert "healthcentral.db" in names, (
        "the scoped master copy must still be present, or a restore from this "
        "archive cannot re-apply the profile row"
    )
```

- [ ] **Step 7: Run the full suite**

Run: `cd src/backend && python -m pytest tests/ -p no:cacheprovider -q`
Expected: `1207 passed, 1 failed` (only `test_api_rag_index_002b`).

- [ ] **Step 8: Commit**

```bash
git add src/backend/api/backup.py src/backend/tests/test_backup_routes.py src/backend/tests/test_backup_api.py
git commit -m "fix(backup): stop the download carrying other profiles' credentials

Profile-scoped backups keep healthcentral.db on disk because restore needs this
profile's password_hash, which lives in the master DB while the sealed key
travels in the vault. download_backup then rglob'd the directory, so a user's
own archive carried every other profile's display_name, bcrypt hash, salt and
the whole audit trail.

Restore and export have opposite requirements, so the download now substitutes
a single-profile extract. HC-BKUP-014 looked like isolation coverage but only
checked filenames; HC-BKUP-035 opens the master DB inside the archive."
```

---

## Task 4: Restore reports "Nothing was changed" after replacing the vault (BLOCKER)

**Files:**
- Modify: `src/backend/scripts/backup.py:54-59` (`RestoreResult`), `:447-460` (the `_reapply_profile_row` failure path)
- Modify: `src/backend/api/backup.py` (`restore_backup` failure handling)
- Modify: `src/frontend/src/components/settings/BackupCard.tsx` (`handleRestore` error copy)
- Test: `src/backend/tests/test_backup.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `RestoreResult.partial: bool = False` — `True` means files were replaced but reconciliation failed. `success=False` continues to mean nothing was touched.

**Why:** If `_reapply_profile_row` raises, `restore()` returns `success=False` *after* the copy loop already replaced `vault.db`, `key.bin` and `key.recovery.bin`. The API 500s and the UI says "Restore failed. Nothing was changed." That is false, and the user is left with a vault whose keys may not match the live password hash. This failure mode was introduced by BK-01.

- [ ] **Step 1: Write the failing test**

Append to `src/backend/tests/test_backup.py`:

```python
def test_hc_bkup_036_partial_restore_is_reported_as_partial(tmp_path, monkeypatch):
    """A reconciliation failure happens *after* the vault and both sealed keys
    are replaced. Reporting success=False makes the API and UI say "Nothing was
    changed", which is false and leaves the user unable to reason about state."""
    import sqlite3
    from scripts import backup as backup_script

    data_dir = tmp_path / "data"
    vault = data_dir / "vaults" / "profile-a"
    vault.mkdir(parents=True)
    conn = sqlite3.connect(vault / "vault.db")
    conn.execute("CREATE TABLE observations (id TEXT)")
    conn.commit()
    conn.close()
    (vault / "key.bin").write_bytes(b"sealed")
    (vault / "key.method").write_text("password")

    master = data_dir / "healthcentral.db"
    conn = sqlite3.connect(master)
    conn.execute("CREATE TABLE profiles (id TEXT, display_name TEXT)")
    conn.execute("INSERT INTO profiles VALUES ('profile-a', 'Ann')")
    conn.commit()
    conn.close()

    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    created = backup_script.backup(
        data_dir=data_dir, backup_dir=backup_dir, profile_id="profile-a"
    )

    def _boom(*args, **kwargs):
        raise sqlite3.Error("simulated reconciliation failure")

    monkeypatch.setattr(backup_script, "_reapply_profile_row", _boom)

    result = backup_script.restore(
        created.backup_path, data_dir, profile_id="profile-a"
    )

    assert result.success is False
    assert result.partial is True, (
        "files were already replaced, so this is a partial restore — reporting "
        "it as a clean failure tells the user nothing changed, which is false"
    )
    assert result.files_restored > 0
    assert result.safety_copies, "the .bak copies must be named so recovery is possible"
```

- [ ] **Step 2: Run it and observe the failure**

Run: `cd src/backend && python -m pytest tests/test_backup.py::test_hc_bkup_036_partial_restore_is_reported_as_partial -p no:cacheprovider -v`
Expected: **FAIL** with `AttributeError: 'RestoreResult' object has no attribute 'partial'`.

- [ ] **Step 3: Add the field**

In `src/backend/scripts/backup.py`, change `RestoreResult`:

```python
@dataclass
class RestoreResult:
    """Result of a restore operation.

    `success=False` means nothing was touched — validation or verification
    failed before any copy. `partial=True` means files WERE replaced and
    reconciliation then failed: the vault and sealed keys are the backup's, but
    the master row was not re-applied, so the live password hash may not match.
    The distinction matters because "nothing changed" is a false reassurance
    during data loss.
    """
    success: bool
    files_restored: int
    safety_copies: list[Path]
    error: str = ""
    partial: bool = False
```

- [ ] **Step 4: Set it on the failure path**

In `restore()`, find the `_reapply_profile_row` failure return and change:

```python
            except sqlite3.Error as exc:
                return RestoreResult(
                    success=False,
                    files_restored=files_restored,
                    safety_copies=safety_copies,
                    error=f"Could not re-apply the profile row: {exc}",
                )
```

to:

```python
            except sqlite3.Error as exc:
                # The copy loop above already replaced vault.db and both sealed
                # keys. This is a partial restore, not a clean failure.
                return RestoreResult(
                    success=False,
                    partial=True,
                    files_restored=files_restored,
                    safety_copies=safety_copies,
                    error=f"Could not re-apply the profile row: {exc}",
                )
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd src/backend && python -m pytest tests/test_backup.py::test_hc_bkup_036_partial_restore_is_reported_as_partial -p no:cacheprovider -v`
Expected: PASS.

- [ ] **Step 6: Surface it honestly in the API**

In `src/backend/api/backup.py`, in `restore_backup`, replace:

```python
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Restore failed; safety copies were left in place.",
        )
```

with:

```python
    if not result.success:
        if result.partial:
            # Do not say "nothing changed" — the vault and sealed keys are
            # already the backup's. Name the safety copies so recovery is
            # possible, and warn that the password may have reverted.
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Your data was replaced from the backup, but the profile "
                    "record could not be updated. Sign in with the password "
                    "that was in use when this backup was made. "
                    f"{len(result.safety_copies)} safety copy/copies of the "
                    "replaced files were kept alongside them."
                ),
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Restore failed; nothing was changed and safety copies remain.",
        )
```

- [ ] **Step 7: Fix the frontend copy**

In `src/frontend/src/components/settings/BackupCard.tsx`, in `handleRestore`'s catch block, replace:

```tsx
      setError(
        err instanceof Error ? err.message : 'Restore failed. Nothing was changed.'
      );
```

with:

```tsx
      // The server's message distinguishes a clean failure from a partial one,
      // so prefer it. The fallback must not claim nothing changed — that is
      // exactly the false reassurance this fix removes.
      setError(
        err instanceof Error
          ? err.message
          : 'Restore failed. Check Settings to confirm your data before continuing.'
      );
```

- [ ] **Step 8: Verify frontend and full backend suite**

Run: `cd src/frontend && npx tsc --noEmit`
Expected: no output.

Run: `cd src/backend && python -m pytest tests/ -p no:cacheprovider -q`
Expected: `1208 passed, 1 failed` (only `test_api_rag_index_002b`).

- [ ] **Step 9: Commit**

```bash
git add src/backend/scripts/backup.py src/backend/api/backup.py src/backend/tests/test_backup.py src/frontend/src/components/settings/BackupCard.tsx
git commit -m "fix(backup): stop claiming nothing changed after a partial restore

If _reapply_profile_row raised, restore() returned success=False after the copy
loop had already replaced vault.db and both sealed keys, and the UI said
'Restore failed. Nothing was changed.' That is false, and it leaves the user
with a vault whose keys may not match the live password hash.

Adds partial=True, distinct from success=False, and copy that names the safety
copies and which password now applies. A false reassurance during data loss is
worse than an alarming true message. HC-BKUP-036."
```

---

## Task 5: Traversal guard accepts the backup root

**Files:**
- Modify: `src/backend/api/backup.py:170`
- Test: `src/backend/tests/test_backup_api.py`

**Interfaces:** Consumes nothing; produces nothing.

**Why:** The guard reads `if candidate != root and root not in candidate.parents`. When `candidate == root` the first clause is false, so the whole condition is false and nothing is rejected. `backup_id="."` therefore resolves to the backup root, which `.is_dir()` accepts, and the route zips every backup as one archive.

- [ ] **Step 1: Write the failing test**

Append to `src/backend/tests/test_backup_api.py`:

```python
@pytest.mark.parametrize("hostile", [".", "./", "profile-a/.."])
def test_hc_bkup_037_backup_root_is_not_a_backup(data_dir, hostile):
    """`candidate == root` short-circuits the traversal guard, so `.` resolved
    to the profile's whole backup root and the download zipped every backup at
    once. The root is not a backup and must never resolve."""
    (data_dir / "backups" / "profile-a").mkdir(parents=True, exist_ok=True)

    with pytest.raises(HTTPException) as exc:
        backup_api._resolve_backup_dir("profile-a", hostile)
    assert exc.value.status_code in (400, 404)
```

- [ ] **Step 2: Run it and observe the failure**

Run: `cd src/backend && python -m pytest tests/test_backup_api.py -p no:cacheprovider -k 037 -v`
Expected: **FAIL** — `DID NOT RAISE` for `.` and `./`.

- [ ] **Step 3: Fix the guard**

In `src/backend/api/backup.py`, in `_resolve_backup_dir`, replace:

```python
    if candidate != root and root not in candidate.parents:
```

with:

```python
    # `candidate == root` must be rejected, not exempted: the backup root is
    # not a backup, and `backup_id="."` resolved to it and zipped everything.
    if candidate == root or root not in candidate.parents:
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd src/backend && python -m pytest tests/test_backup_api.py tests/test_backup_routes.py -p no:cacheprovider -q`
Expected: all pass — confirm the existing `HC-BKUP-012` traversal cases still pass too.

- [ ] **Step 5: Commit**

```bash
git add src/backend/api/backup.py src/backend/tests/test_backup_api.py
git commit -m "fix(backup): reject the backup root as a backup id

The guard's first clause exempted candidate == root, so backup_id='.' resolved
to the profile's whole backup root and the download zipped every backup as one
archive. HC-BKUP-037."
```

---

## Task 6: Citation effects in the Verification Workbench

**Files:**
- Modify: `src/frontend/src/pages/VerificationWorkbench.tsx:193-215`
- Modify: `src/frontend/src/pages/ExplainAssistant.tsx` (`citationTarget`)
- Test: `src/frontend/src/__tests__/EntityCitationDeepLink.test.tsx`

**Interfaces:** Consumes nothing; produces nothing.

**Why two fixes in one task:** both are in the same effect block and a reviewer would accept or reject them together.

**A5:** the cited-observation effect lists `observations` in its deps. Verifying an observation invalidates that query, so every refetch re-applies the citation and snaps the user's selection back to the cited row. A citation should apply once per navigation, not once per fetch.

**A6:** an entity citation with `entity_id` but no `doc_id` leaves `entityDocId` empty, so the query is disabled, `docEntities` stays `[]`, and the effect latches `citedNotFound` permanently. The reset effect only fires on param *change*.

- [ ] **Step 1: Write the failing test**

Append to `src/frontend/src/__tests__/EntityCitationDeepLink.test.tsx`, inside the existing `describe` block:

```tsx
  it('FE-CITE-003: a resolved citation is applied once, not on every refetch', async () => {
    mockApi([entity]);

    renderAt('/verify?entity=ent-4&doc=doc-9');

    await waitFor(() => {
      expect(screen.getAllByText(/No acute intracranial abnormality/).length).toBeGreaterThan(0);
    });

    // The notice must not appear for a citation that resolved.
    expect(screen.queryByText(/no longer available/i)).not.toBeInTheDocument();
  });

  it('FE-CITE-004: an entity citation with no doc is not a dead link', async () => {
    mockApi([]);

    // No `doc` param: entityDocId is empty, the entities query never runs, and
    // the old code latched "no longer available" forever. A citation with no
    // inspectable source should render as text, not navigate nowhere.
    renderAt('/verify?entity=ent-4');

    await waitFor(() => {
      expect(screen.queryByText(/no longer available/i)).not.toBeInTheDocument();
    });
  });
```

- [ ] **Step 2: Run it and observe the failure**

Run: `cd src/frontend && npx vitest run src/__tests__/EntityCitationDeepLink.test.tsx`
Expected: **FAIL** on `FE-CITE-004` — the notice is present because the effect set `citedNotFound` with no entities loaded.

- [ ] **Step 3: Gate the observation effect on a ref**

In `src/frontend/src/pages/VerificationWorkbench.tsx`, add near the other hooks (after `const [loadingSource, setLoadingSource] = useState(false);`):

```tsx
  // A citation applies once per navigation. Without this the effect below
  // re-runs on every `observations` refetch — and verifying a row invalidates
  // that query — so the user's selection snaps back to the cited row.
  const appliedCitationRef = useRef<string | null>(null);
```

Add `useRef` to the React import at line 1:

```tsx
import { useState, useEffect, useCallback, useRef } from 'react';
```

Then change the cited-observation effect body. Replace:

```tsx
  useEffect(() => {
    if (!citedObservationId || !observations) return;
    const match = observations.find((o) => o.id === citedObservationId);
    if (match) {
      setCitedNotFound(false);
      void handleRowSelect(match);
```

with:

```tsx
  useEffect(() => {
    if (!citedObservationId || !observations) return;
    if (appliedCitationRef.current === citedObservationId) return;
    const match = observations.find((o) => o.id === citedObservationId);
    if (match) {
      appliedCitationRef.current = citedObservationId;
      setCitedNotFound(false);
      void handleRowSelect(match);
```

Then reset the ref in the existing notice-clearing effect. Replace:

```tsx
  useEffect(() => {
    setCitedNotFound(false);
  }, [citedObservationId, citedEntityId]);
```

with:

```tsx
  useEffect(() => {
    setCitedNotFound(false);
    appliedCitationRef.current = null;
  }, [citedObservationId, citedEntityId]);
```

- [ ] **Step 4: Stop latching the notice for un-inspectable entities**

In the entity effect, replace:

```tsx
  useEffect(() => {
    if (!citedEntityId || entitiesLoading) return;
    const match = docEntities.find((e) => e.id === citedEntityId);
    if (match) {
```

with:

```tsx
  useEffect(() => {
    if (!citedEntityId || entitiesLoading) return;
    // No doc means no entity list can be fetched, so "no longer available" is
    // the wrong message — nothing was ever looked up. Citations without an
    // inspectable source are filtered at emit time instead (citationTarget).
    if (!entityDocId) return;
    const match = docEntities.find((e) => e.id === citedEntityId);
    if (match) {
```

- [ ] **Step 5: Stop emitting those links at all**

In `src/frontend/src/pages/ExplainAssistant.tsx`, in `citationTarget`, replace:

```tsx
  } else if (citation.entityId) {
    params.set('entity', citation.entityId);
  } else {
```

with:

```tsx
  } else if (citation.entityId && citation.docId) {
    // An entity is only inspectable with its document — the workbench loads
    // entities per doc. Without docId this rendered as a chip that navigated
    // nowhere, which on a health record is worse than a plain label.
    params.set('entity', citation.entityId);
  } else {
```

- [ ] **Step 6: Update the mirrored contract test**

In `src/frontend/src/__tests__/CitationDeepLink.test.tsx`, the local `citationTarget` copy mirrors the component. Apply the identical change to it, then add:

```tsx
  it('renders as plain text when an entity has no document', () => {
    // The workbench loads entities per document, so an entity without docId
    // cannot be resolved. A chip that navigates nowhere is worse than a label.
    expect(citationTarget({ ...base, entityId: 'ent-4' })).toBeNull();
  });
```

- [ ] **Step 7: Run the frontend suite**

Run: `cd src/frontend && npx vitest run && npx tsc --noEmit`
Expected: all tests pass (161 total), no tsc output.

- [ ] **Step 8: Commit**

```bash
git add src/frontend/src/pages/VerificationWorkbench.tsx src/frontend/src/pages/ExplainAssistant.tsx src/frontend/src/__tests__/EntityCitationDeepLink.test.tsx src/frontend/src/__tests__/CitationDeepLink.test.tsx
git commit -m "fix(verify): apply a citation once, and stop emitting dead entity links

The cited-observation effect depended on \`observations\`, and verifying a row
invalidates that query, so every refetch re-applied the citation and snapped
the user's selection away. Gated on a ref that resets when the citation param
changes.

An entity citation with no docId could never resolve — the workbench loads
entities per document — so it latched 'no longer available' permanently. Those
citations now render as plain text at emit time, matching the rule already used
for reference-corpus entries. FE-CITE-003/004."
```

---

## Task 7: Timestamp helper in `recover_profile`

**Files:**
- Modify: `src/backend/api/profiles.py:732`
- Test: `src/backend/tests/test_profile_recovery.py`

**Interfaces:** Consumes nothing; produces nothing.

**Why:** New code on this branch uses `datetime.utcnow()`, violating the `core.time.utcnow` hard invariant the same branch enforces elsewhere. The other six occurrences in this file are pre-existing and out of scope.

- [ ] **Step 1: Write the failing test**

Append to `src/backend/tests/test_profile_recovery.py`:

```python
def test_hc_recov_025_recovery_uses_the_project_time_helper():
    """CLAUDE.md names core.time.utcnow as the single timestamp helper.
    datetime.utcnow() is also deprecated from 3.12. This is a source assertion
    because the returned value is identical either way — only the call differs."""
    import inspect
    import api.profiles as profiles_api

    source = inspect.getsource(profiles_api.recover_profile)
    assert "datetime.utcnow()" not in source, (
        "use core.time.utcnow, per the hard invariant this branch enforces "
        "elsewhere"
    )
```

- [ ] **Step 2: Run it and observe the failure**

Run: `cd src/backend && python -m pytest tests/test_profile_recovery.py -p no:cacheprovider -k 025 -v`
Expected: **FAIL** on the assertion.

- [ ] **Step 3: Fix the call**

In `src/backend/api/profiles.py:732`, replace `profile.last_accessed_at = datetime.utcnow()` with `profile.last_accessed_at = utcnow()`.

Confirm `utcnow` is imported: run `grep -n "from core.time import" src/backend/api/profiles.py`. If absent, add `from core.time import utcnow` next to the other `core` imports.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd src/backend && python -m pytest tests/test_profile_recovery.py -p no:cacheprovider -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add src/backend/api/profiles.py src/backend/tests/test_profile_recovery.py
git commit -m "fix(profiles): use core.time.utcnow in recover_profile

New code on this branch used datetime.utcnow(), against the hard invariant the
same branch enforces elsewhere. The six other occurrences in this file are
pre-existing and left alone. HC-RECOV-025."
```

---

## Task 8: Audit drift warning fires on routine operations

**Files:**
- Modify: `src/backend/core/audit.py:179-184`
- Test: `src/backend/tests/test_audit_phi.py` (if absent, use the module holding `HC-AUD-004`; find it with `grep -rln "HC-AUD-004" src/backend/tests/`)

**Interfaces:** Consumes nothing; produces nothing.

**Why:** `_scrub_action` warns whenever `action not in ALLOWED_ACTIONS`, including when the caller deliberately passed the static `event_type` as the action. Routine medication create/delete and password change therefore log an "Unregistered audit action" warning, training readers to ignore the one signal that would catch real drift.

- [ ] **Step 1: Write the failing test**

Append to the module holding the `HC-AUD` tests:

```python
def test_hc_aud_009_passing_event_type_as_action_is_not_drift(caplog):
    """_scrub_action's fallback IS event_type, so a caller that passes it
    deliberately has already complied. Warning anyway fires the drift alarm on
    routine operations and teaches readers to ignore it."""
    import logging
    from core.audit import _scrub_action

    with caplog.at_level(logging.WARNING):
        result = _scrub_action("medication.create", "medication.create")

    assert result == "medication.create"
    assert not [r for r in caplog.records if "Unregistered audit action" in r.message], (
        "action == event_type is already the safe static value, not drift"
    )
```

- [ ] **Step 2: Run it and observe the failure**

Run: `cd src/backend && python -m pytest tests/ -p no:cacheprovider -k hc_aud_009 -v`
Expected: **FAIL** — the warning record is present.

- [ ] **Step 3: Narrow the warning**

In `src/backend/core/audit.py`, replace:

```python
    if action in ALLOWED_ACTIONS:
        return action
    logger.warning(
        "Unregistered audit action replaced by event type (AUDIT-PHI-001)",
        extra={"event_type": event_type},
    )
    return event_type
```

with:

```python
    if action in ALLOWED_ACTIONS:
        return action
    if action != event_type:
        # Only warn when something was actually replaced. A caller that passed
        # event_type as the action already supplied the safe static value, so
        # warning there fires this alarm on routine operations and trains
        # readers to ignore the one signal that catches real drift.
        logger.warning(
            "Unregistered audit action replaced by event type (AUDIT-PHI-001)",
            extra={"event_type": event_type},
        )
    return event_type
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd src/backend && python -m pytest tests/ -p no:cacheprovider -k "hc_aud" -v`
Expected: all pass, including the existing `HC-AUD-004` drift gate — that one passes a genuinely unregistered action *different* from `event_type`, so it must still warn.

- [ ] **Step 5: Commit**

```bash
git add src/backend/core/audit.py src/backend/tests/
git commit -m "fix(audit): only warn when an action was actually replaced

_scrub_action warned whenever the action was not in the allowlist, including
when the caller deliberately passed event_type — already the safe static value.
Routine medication create/delete and password change tripped the drift alarm,
which is how a real drift signal gets ignored. HC-AUD-009."
```

---

## Task 9: Correct two tracker rows that claim DONE

**Files:**
- Modify: `docs/features/TASK_LIST.md` (the `SEC-RECOV-001` and `MED-CORR-001` rows, and the Session Notes)

**Interfaces:** Consumes nothing; produces nothing.

**Why:** `useIssueRecoveryCode` and the medications correlations hook both have **zero callers** outside `services/` — verified by grep. So `SEC-RECOV-001` is complete only for newly created profiles (pre-existing ones can never obtain a recovery code, and `RecoverProfile.tsx` points them at a screen that does not exist), and `MED-CORR-001`'s endpoint is dead code while both pages still use `utils/correlation.ts` with a differing `verified_only` default. Both rows say DONE. That is a documentation defect fixable now; the implementations belong in the follow-up PR.

- [ ] **Step 1: Re-verify before editing**

Run:

```bash
cd src/frontend && grep -rn "useIssueRecoveryCode" src/ | grep -v "services/"
grep -rn "useCorrelations\|useMedicationCorrelations" src/ | grep -v "services/"
```

Expected: **no output for either** — confirming both hooks are unreferenced. If either now has a caller, stop and re-assess; the row may be accurate.

- [ ] **Step 2: Correct the `SEC-RECOV-001` row**

In `docs/features/TASK_LIST.md`, find the `SEC-RECOV-001` row's status cell and replace `[x] DONE (2026-07-27) — owner sign-off 2026-07-27; recovery code seals a second DEK copy, always password-derived. Tests HC-RECOV-001..024` with:

```
[~] PARTIAL (2026-07-30) — backend complete and tested (HC-RECOV-001..024); recovery code seals a second DEK copy, always password-derived. **Frontend incomplete:** `useIssueRecoveryCode` has zero callers, so codes are issued only at profile creation and pre-existing profiles can never obtain one, while `RecoverProfile.tsx` directs them to a screen that does not exist. Settings entry point tracked as follow-up.
```

- [ ] **Step 3: Correct the `MED-CORR-001` row**

Replace that row's `[x] DONE (2026-07-27) — GET /medications/{id}/correlations built; frontend heuristic ported to the backend so there is one definition. Tests HC-MCORR-001..010` with:

```
[~] PARTIAL (2026-07-30) — endpoint built and tested (HC-MCORR-001..010), but **unwired**: `TrendsDashboard.tsx` and `MedicationDetail.tsx` both still use `utils/correlation.ts`, and the two implementations disagree on the `verified_only` default. The stated goal — one definition of the rule — is not yet met. Wiring tracked as follow-up.
```

- [ ] **Step 4: Add a Session Notes entry**

Under `## Session Notes`, immediately after the heading, add:

```markdown
### 2026-07-30 - Pre-merge audit corrections

A pre-merge audit of PR #18 found two rows recorded DONE whose frontend has no
callers: `SEC-RECOV-001` (recovery codes unreachable for pre-existing profiles)
and `MED-CORR-001` (correlations endpoint dead, both pages still on the
heuristic). Both re-marked PARTIAL with the specific gap named. Implementations
are scoped to the follow-up PR; see
`docs/superpowers/specs/2026-07-30-remediation-and-asclexis-design.md`.

The audit's wider lesson: 1205 green backend tests coexisted with a restore
endpoint that returned 400 for every request and a backup download that carried
every profile's password hash, because the route tests called handlers as plain
functions and the isolation assertion checked filenames rather than file
contents. `tests/support/routes.py` now exists so route-level testing is the
cheap default.
```

- [ ] **Step 5: Run the docs gates**

Run:

```bash
cd /home/user/HealthCentral
python3 scripts/docs_lint.py; echo "docs_lint=$?"
python3 scripts/generate_docs_index.py --check; echo "index=$?"
python3 scripts/feature_list_lint.py; echo "feature_list=$?"
```

Expected: all three print `=0`. If `docs_lint` objects to the `[~] PARTIAL` marker, check its status-marker rule and use whatever marker the linter accepts for in-progress work.

- [ ] **Step 6: Commit**

```bash
git add docs/features/TASK_LIST.md
git commit -m "docs: mark SEC-RECOV-001 and MED-CORR-001 partial, not done

Both have zero frontend callers, verified by grep. Recovery codes are issued
only at profile creation, so pre-existing profiles can never get one while
RecoverProfile points them at a screen that does not exist. The correlations
endpoint is dead code with both pages still on utils/correlation.ts, and the
two rules already disagree on verified_only.

The implementations are follow-up work; the inaccurate DONE is fixable now."
```

---

## Task 10: Update the PR #18 description

**Files:** none (GitHub only)

**Interfaces:** Consumes nothing; produces nothing.

- [ ] **Step 1: Verify the full gate before touching the PR**

Run:

```bash
cd src/backend && python -m pytest tests/ -p no:cacheprovider -q
cd ../frontend && npx tsc --noEmit && npx vitest run
```

Expected: backend `1 failed` (only `test_api_rag_index_002b`), tsc silent, vitest all pass. **Report the actual numbers; do not assert them.**

- [ ] **Step 2: Run the e2e suite from a clean data dir**

```bash
cd /home/user/HealthCentral/src/backend && mv data /tmp/data_bak 2>/dev/null || true
cd ../frontend && HC_E2E_CHROMIUM_PATH=/opt/pw-browsers/chromium npx playwright test --project=chromium
cd ../backend && rm -rf data && mv /tmp/data_bak data 2>/dev/null || true
```

Expected: `25 passed / 3 skipped`.

- [ ] **Step 3: Amend the PR body**

Use `mcp__github__update_pull_request` on `BrooklynD23/HealthCentral` #18. In the body: change the `MED-CORR-001` and `SEC-RECOV-001` mentions from completed to partial with the reason, and add a section recording that a pre-merge audit found a permanently-400 restore endpoint and a cross-profile leak in the download, both fixed in this PR, plus the route-level harness that closes the class. End the body with the attribution footer already present.

- [ ] **Step 4: Confirm CI is green on the new head**

Use `mcp__github__pull_request_read` with `method: "get_check_runs"`. Expected: all 6 checks `success`. If `E2E Smoke Tests` is red, check whether it is `E2E-SET-004` (hardware-dependent, already fixed on this branch) before assuming a regression.

---

## Self-Review

**Spec coverage.** Phase A items A0→Task 1, A1→Task 2, A2→Task 3, A3→Task 4, A4→Task 5, A5+A6→Task 6, A7→Task 7, A8→Task 8, A9+A10 doc corrections→Task 9, delivery/PR update→Task 10. The A9/A10 *implementations* are explicitly deferred to the follow-up PR per the spec's delivery split, so they are not tasks here — Plan A's stated goal is "PR #18 mergeable".

**Placeholders.** None. Every code step contains the actual code; every command has an expected result; no "similar to Task N".

**Type consistency.** `route_client(router, prefix, profile_id, master_db)` is defined in Task 1 and used with that signature in Tasks 2, 3, and 5. `RestoreResult.partial` is added in Task 4 Step 3 and consumed in Step 6. `_single_profile_master_bytes(master_path, profile_id) -> bytes` is defined and used within Task 3. `appliedCitationRef` is declared and used within Task 6. `MASTER_DB_NAME` is pre-existing; Task 3 Step 3 flags the import-style check rather than assuming.

**One risk flagged for the implementer:** Task 3's helper deletes from `profiles`, `audit_logs`, and `backup_schedules` by introspecting columns. If the master schema gains another profile-linked table, the extract will silently carry it. A follow-up guard — assert every table with a `profile_id` column was filtered — would close that, but it needs the schema to stabilise first.
