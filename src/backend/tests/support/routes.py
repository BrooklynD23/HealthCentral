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
from sqlalchemy.ext.asyncio import async_sessionmaker

from core.auth import Session, get_profile_db_session, require_auth
from core.database import get_db


class _NoCutoff:
    def scalar(self):
        return None


def no_logout_cutoff(db):
    """Make a mock master DB answer the export download's logout/lock cutoff read with "no
    such audit row" (C-GC1, EXPORT-LIVE-LOGIN). Every other query keeps the mock's own
    `execute.return_value`, read at call time, so a test that sets it afterwards still works.
    Returns `db`."""
    async def _execute(statement, *_args, **_kwargs):
        if "audit_logs" in str(statement):
            return _NoCutoff()
        return db.execute.return_value

    db.execute.side_effect = _execute
    return db


@contextmanager
def route_client(
    router: APIRouter,
    prefix: str,
    profile_id: str = "profile-a",
    master_db: Optional[object] = None,
    raise_server_exceptions: bool = True,
    profile_name: str = "T",
    profile_db: Optional[async_sessionmaker] = None,
    real_auth: bool = False,
) -> Iterator[TestClient]:
    """Yield a TestClient for `router` with auth and the master DB overridden.

    `master_db` defaults to an AsyncMock, which is enough for routes that only
    write audit rows. Pass a real session when the assertion needs one.

    `profile_name` sets the authenticated session's display name (routes that
    gate on it, such as the synthetic test reset, need a real one).
    `profile_db` is an async_sessionmaker for the per-profile vault; when given,
    `get_profile_db_session` yields a session from it for each request.
    `real_auth=True` leaves `require_auth` un-overridden, so the real token check runs (401 tests).
    """
    app = FastAPI()
    app.include_router(router, prefix=prefix)

    db = master_db if master_db is not None else no_logout_cutoff(AsyncMock())

    async def _override_auth() -> Session:
        return Session(
            profile_id=profile_id,
            profile_name=profile_name,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            token_jti="jti-test",
        )

    async def _override_master_db():
        return db

    if not real_auth:
        app.dependency_overrides[require_auth] = _override_auth
    app.dependency_overrides[get_db] = _override_master_db

    if profile_db is not None:

        async def _override_profile_db():
            async with profile_db() as session:
                yield session

        app.dependency_overrides[get_profile_db_session] = _override_profile_db

    with TestClient(app, raise_server_exceptions=raise_server_exceptions) as client:
        yield client
