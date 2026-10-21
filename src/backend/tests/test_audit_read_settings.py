"""AUDIT-READ-SETTINGS: settings read routes write one audit row (owner gate AUDIT-READ-SCOPE (a)).

HC-ARS-001 one metadata-only audit row; HC-ARS-002 audit commit failure fails closed;
HC-ARS-003 pins routes that stay unaudited. Tests go through HTTP (route_client).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

sys.path.insert(0, str(Path(__file__).parent.parent))

import api.model_settings as model_settings_api
from core.auth import get_profile_db_session
from core.profile_database import ProfileDatabaseBase
from models.model_settings import UserModelSettings
from tests.support.routes import route_client

PREFIX = "/settings/model"
PROFILE_A = "profile-a"
KEY_MARKER = "PLAINTEXT-KEY-MARKER-9f3"
CIPHERTEXT = "gAAAAA-CIPHERTEXT-MARKER-7c1"

AUDITED = [
    (f"{PREFIX}", "model"),
    (f"{PREFIX}/external-api", "external_api"),
    (f"{PREFIX}/timezone", "timezone"),
    (f"{PREFIX}/voice", "voice"),
]


def _master_db(commit_error: Exception | None = None) -> MagicMock:
    db = MagicMock()
    db.commit = AsyncMock(side_effect=commit_error)
    return db


@pytest_asyncio.fixture
async def vault():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    session.add(UserModelSettings(
        profile_id=PROFILE_A,
        use_external_api=True,
        external_api_provider="openai",
        external_api_key_encrypted=CIPHERTEXT,
    ))
    await session.commit()
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


def _call(method, path, profile_db, master_db):
    selector = MagicMock()
    selector.detect_hardware_tier.return_value = _hardware()
    selector.is_model_available.return_value = False
    selector.get_active_tier = AsyncMock(return_value="template")
    with patch.object(model_settings_api, "get_model_selector", return_value=selector), \
         patch.object(model_settings_api, "build_environment_diagnostics", return_value=[]), \
         route_client(
             model_settings_api.router, PREFIX,
             profile_id=PROFILE_A, master_db=master_db,
             raise_server_exceptions=False,
         ) as client:
        async def _profile_db():
            return profile_db
        client.app.dependency_overrides[get_profile_db_session] = _profile_db
        return client.request(method, path)


def _hardware():
    from datetime import datetime, timezone
    hw = MagicMock()
    hw.ram_total_gb = 8.0
    hw.ram_available_gb = 4.0
    hw.cpu_cores = 4
    hw.cpu_name = "cpu"
    hw.disk_free_gb = 50.0
    hw.gpu_available = False
    hw.gpu_vram_gb = 0.0
    hw.gpu_name = ""
    hw.recommended_tier = "template"
    hw.max_supported_tier = "template"
    hw.detection_timestamp = datetime.now(timezone.utc)
    return hw


def _rows(master_db):
    return [c.args[0] for c in master_db.add.call_args_list]


@pytest.mark.asyncio
@pytest.mark.parametrize("path,x", AUDITED)
async def test_hc_ars_001_read_writes_one_metadata_only_audit_row(vault, path, x):
    master_db = _master_db()
    resp = _call("GET", path, vault, master_db)
    assert resp.status_code == 200, resp.text
    rows = _rows(master_db)
    assert len(rows) == 1
    row = rows[0]
    assert row.event_type == f"settings.{x}.view"
    assert row.entity_type == "settings"
    assert row.profile_id == PROFILE_A
    blob = repr(row) + repr(vars(row))
    assert CIPHERTEXT not in blob and KEY_MARKER not in blob


@pytest.mark.asyncio
@pytest.mark.parametrize("path,x", AUDITED)
async def test_hc_ars_002_audit_commit_failure_fails_closed(vault, path, x):
    master_db = _master_db(commit_error=RuntimeError("audit down"))
    resp = _call("GET", path, vault, master_db)
    assert resp.status_code == 500


@pytest.mark.asyncio
@pytest.mark.parametrize("method,path", [
    ("GET", f"{PREFIX}/tiers"),
    ("GET", f"{PREFIX}/diagnostics"),
    ("POST", f"{PREFIX}/diagnostics/recheck"),
    ("GET", f"{PREFIX}/provider"),
])
async def test_hc_ars_003_exempt_routes_write_no_audit_row(vault, method, path):
    master_db = _master_db()
    resp = _call(method, path, vault, master_db)
    assert resp.status_code == 200, resp.text
    assert _rows(master_db) == []
