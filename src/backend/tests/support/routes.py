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
