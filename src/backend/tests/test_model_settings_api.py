"""
Tests for model settings persistence and background download status.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import types
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import api.model_settings as model_settings_api
from api.model_settings import (
    ExternalApiSettingsRequest,
    OcrSettingsUpdate,
    TimezoneUpdate,
    VoiceSettingsUpdate,
    _clear_live_progress,
    _diagnostics_list_response,
    _download_model_task,
    _get_live_progress,
    _make_progress_key,
    _set_live_progress,
    get_external_api_settings,
    save_external_api_settings,
    set_timezone,
    update_ocr_settings,
    update_voice_settings,
)
from core.auth import Session, get_profile_db_session, get_profile_encryption_manager
from core.profile_database import ProfileDatabaseBase
from core.security import EncryptionManager
from models import UserModelSettings
from modules.hardware_detection import HardwareProfile
from tests.support.routes import route_client


class _ScalarResult:
    def __init__(self, one=None):
        self._one = one

    def scalar_one_or_none(self):
        return self._one


class _FakeProfileDb:
    def __init__(self, existing_settings=None):
        self._existing_settings = existing_settings
        self._added = []
        self._committed = False

    async def execute(self, _stmt):
        return _ScalarResult(one=self._existing_settings)

    async def commit(self):
        self._committed = True

    def add(self, obj):
        self._added.append(obj)
        self._existing_settings = obj


def _session(profile_id: str) -> Session:
    return Session(
        profile_id=profile_id,
        profile_name="Test",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )


@pytest.mark.asyncio
async def test_put_external_api_requires_consent():
    profile_id = str(uuid.uuid4())

    with pytest.raises(HTTPException) as exc_info:
        await save_external_api_settings(
            request=ExternalApiSettingsRequest(
                use_external_api=True,
                provider="openai",
                api_key="sk-test",
                consent_acknowledged=False,
            ),
            session=_session(profile_id),
            profile_db=_FakeProfileDb(),
            encryption_manager=EncryptionManager(),
        )

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_put_external_api_persists():
    profile_id = str(uuid.uuid4())
    profile_db = _FakeProfileDb(existing_settings=None)

    response = await save_external_api_settings(
        request=ExternalApiSettingsRequest(
            use_external_api=True,
            provider="openai",
            api_key="sk-test-key-123",
            model="gpt-4o-mini",
            consent_acknowledged=True,
        ),
        session=_session(profile_id),
        profile_db=profile_db,
        encryption_manager=EncryptionManager(),
        master_db=MagicMock(commit=AsyncMock()),
    )

    assert response.use_external_api is True
    assert response.provider == "openai"
    assert response.model == ""
    assert response.api_key_configured is True
    stored = profile_db._existing_settings.external_api_key_encrypted
    assert stored != "sk-test-key-123"
    assert stored.startswith("gAAAAA")
    assert profile_db._committed is True


def test_download_task_writes_terminal_status(monkeypatch):
    """Task writes 'downloading' at start then 'completed' on success."""
    profile_id = str(uuid.uuid4())
    selector = MagicMock()
    selector.models_path = "/tmp/models"
    selector.update_download_progress = AsyncMock()

    monkeypatch.setattr(
        "api.model_settings.TIER_MODEL_CONFIG",
        {"low": {"repo": "test/repo", "filename": "model.gguf", "revision": "main"}},
    )
    monkeypatch.setitem(
        sys.modules,
        "huggingface_hub",
        types.SimpleNamespace(
            hf_hub_download=MagicMock(return_value="/tmp/models/model.gguf"),
            list_repo_files=MagicMock(return_value=["model.gguf"]),
        ),
    )

    async def inline_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    with patch("api.model_settings._write_download_status", new_callable=AsyncMock) as mock_write:
        with patch("asyncio.to_thread", side_effect=inline_to_thread):
            asyncio.run(_download_model_task("low", profile_id, selector))

        assert mock_write.call_count == 2
        first_call = mock_write.call_args_list[0]
        assert first_call.args == (profile_id, "low", selector, "downloading", 0.0)
        second_call = mock_write.call_args_list[1]
        assert second_call.args == (profile_id, "low", selector, "completed", 100.0)


def test_download_task_writes_failure_status(monkeypatch):
    """Task writes 'downloading' at start then 'failed' with error message on exception."""
    profile_id = str(uuid.uuid4())
    selector = MagicMock()
    selector.models_path = "/tmp/models"

    monkeypatch.setattr(
        "api.model_settings.TIER_MODEL_CONFIG",
        {"low": {"repo": "test/repo", "filename": "model.gguf", "revision": "main"}},
    )
    monkeypatch.setitem(
        sys.modules,
        "huggingface_hub",
        types.SimpleNamespace(
            hf_hub_download=MagicMock(side_effect=RuntimeError("Download failed")),
            list_repo_files=MagicMock(return_value=["model.gguf"]),
        ),
    )

    async def inline_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    with patch("api.model_settings._write_download_status", new_callable=AsyncMock) as mock_write:
        with patch("asyncio.to_thread", side_effect=inline_to_thread):
            asyncio.run(_download_model_task("low", profile_id, selector))

        assert mock_write.call_count == 2
        first_call = mock_write.call_args_list[0]
        assert first_call.args == (profile_id, "low", selector, "downloading", 0.0)
        second_call = mock_write.call_args_list[1]
        assert second_call.args == (profile_id, "low", selector, "failed", 0.0, "Download failed")


def test_download_task_uses_to_thread(monkeypatch):
    """hf_hub_download must run in a thread pool to keep the event loop unblocked."""
    profile_id = str(uuid.uuid4())
    selector = MagicMock()
    selector.models_path = "/tmp/models"

    monkeypatch.setattr(
        "api.model_settings.TIER_MODEL_CONFIG",
        {"low": {"repo": "test/repo", "filename": "model.gguf", "revision": "main"}},
    )
    monkeypatch.setitem(
        sys.modules,
        "huggingface_hub",
        types.SimpleNamespace(
            hf_hub_download=MagicMock(return_value="/tmp/models/model.gguf"),
            list_repo_files=MagicMock(return_value=["model.gguf"]),
        ),
    )

    to_thread_calls: list = []

    async def tracking_to_thread(func, *args, **kwargs):
        to_thread_calls.append(func)
        return func(*args, **kwargs)

    with patch("api.model_settings._write_download_status", new_callable=AsyncMock):
        with patch("asyncio.to_thread", side_effect=tracking_to_thread):
            asyncio.run(_download_model_task("low", profile_id, selector))

    # The task must offload at least the download itself to a thread pool worker
    assert len(to_thread_calls) >= 1, (
        "Expected asyncio.to_thread to be called at least once for the blocking download"
    )


def test_live_progress_store_lifecycle():
    """Live progress is set, readable, and cleared correctly."""
    profile_id = str(uuid.uuid4())
    key = _make_progress_key(profile_id, "low")

    # Initially absent
    assert _get_live_progress(key) is None

    # Write progress
    _set_live_progress(key, downloaded=512_000_000, total=1_073_741_824)
    result = _get_live_progress(key)
    assert result is not None
    assert result["downloaded_bytes"] == 512_000_000
    assert result["total_bytes"] == 1_073_741_824
    assert abs(result["progress"] - 47.68) < 0.1

    # Clear removes entry
    _clear_live_progress(key)
    assert _get_live_progress(key) is None


@pytest.mark.asyncio
async def test_get_external_api_masks_key():
    profile_id = str(uuid.uuid4())

    mock_settings = MagicMock()
    mock_settings.use_external_api = True
    mock_settings.external_api_provider = "anthropic"
    mock_settings.external_api_key_encrypted = "encrypted-key-data"

    response = await get_external_api_settings(
        session=_session(profile_id),
        profile_db=_FakeProfileDb(existing_settings=mock_settings),
    )

    assert response.api_key_configured is True
    assert "encrypted-key-data" not in str(response)


@pytest.mark.asyncio
async def test_put_timezone_upserts_when_missing():
    profile_id = str(uuid.uuid4())
    profile_db = _FakeProfileDb(existing_settings=None)

    response = await set_timezone(
        data=TimezoneUpdate(timezone="America/New_York"),
        session=_session(profile_id),
        profile_db=profile_db,
        master_db=MagicMock(commit=AsyncMock()),
    )

    assert response.timezone == "America/New_York"
    assert profile_db._existing_settings is not None
    assert profile_db._existing_settings.timezone == "America/New_York"
    assert profile_db._committed is True


@pytest.mark.asyncio
async def test_patch_voice_upserts_when_missing():
    profile_id = str(uuid.uuid4())
    profile_db = _FakeProfileDb(existing_settings=None)

    response = await update_voice_settings(
        data=VoiceSettingsUpdate(voice_logging_enabled=True, voice_modal_seen=True),
        session=_session(profile_id),
        profile_db=profile_db,
        master_db=MagicMock(commit=AsyncMock()),
    )

    assert response.voice_logging_enabled is True
    assert response.voice_modal_seen is True
    assert profile_db._existing_settings is not None
    assert profile_db._existing_settings.voice_logging_enabled is True
    assert profile_db._existing_settings.voice_modal_seen is True
    assert profile_db._committed is True


@pytest.mark.asyncio
async def test_patch_ocr_persists_preference():
    profile_id = str(uuid.uuid4())
    profile_db = _FakeProfileDb(existing_settings=None)

    response = await update_ocr_settings(
        data=OcrSettingsUpdate(ocr_preference_enabled=False),
        session=_session(profile_id),
        profile_db=profile_db,
        master_db=MagicMock(commit=AsyncMock()),
    )

    assert response.ocr_preference_enabled is False
    assert profile_db._existing_settings is not None
    assert profile_db._existing_settings.ocr_preference_enabled is False
    assert profile_db._committed is True


def test_diagnostics_response_has_core_components():
    r = _diagnostics_list_response()
    assert r.checked_at
    ids = {c.id for c in r.components}
    assert "tesseract" in ids
    assert "ocr_python" in ids


# --- AUDIT-C-MSET: audit row after each settings change (HC-AUDCMS-001/002) ---

_AUD_PROFILE = "profile-aud"

# route id -> (method, path, body, event_type, entity_id, details, settings column)
_AUD_ROUTES = {
    "detect": ("POST", "/detect", None, "settings.hardware.detect", "hardware", None, None),
    "tier": ("POST", "/tier", {"tier": "mid"}, "settings.model_tier.update",
             "model_tier", {"changed_fields": ["tier"]}, None),
    "download": ("POST", "/download", {"tier": "mid"}, "settings.model_download.start",
                 "model_download", None, None),
    "timezone": ("PUT", "/timezone", {"timezone": "America/New_York"},
                 "settings.timezone.update", "timezone",
                 {"changed_fields": ["timezone"]}, ("timezone", "America/New_York")),
    "voice": ("PATCH", "/voice", {"voice_logging_enabled": True},
              "settings.voice.update", "voice",
              {"changed_fields": ["voice_logging_enabled"]},
              ("voice_logging_enabled", True)),
    "ocr": ("PATCH", "/ocr", {"ocr_preference_enabled": False},
            "settings.ocr.update", "ocr",
            {"changed_fields": ["ocr_preference_enabled"]},
            ("ocr_preference_enabled", False)),
    "agent": ("PATCH", "/agent", {"agent_enabled": False},
              "settings.agent.update", "agent",
              {"changed_fields": ["agent_enabled"]}, ("agent_enabled", False)),
}


class _StubSelector:
    def __init__(self):
        self.calls = []

    def detect_hardware_tier(self):
        return HardwareProfile(ram_total_gb=16.0, ram_available_gb=8.0, cpu_cores=8)

    async def save_hardware_detection(self, **kwargs):
        self.calls.append("save_hardware_detection")

    async def set_user_preference(self, **kwargs):
        self.calls.append("set_user_preference")

    async def update_download_progress(self, **kwargs):
        self.calls.append("update_download_progress")

    def is_model_available(self, tier):
        return False


_STUB_CALL = {
    "detect": "save_hardware_detection",
    "tier": "set_user_preference",
    "download": "update_download_progress",
}


@pytest_asyncio.fixture
async def aud_vault():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(ProfileDatabaseBase.metadata.create_all)
    session = AsyncSession(engine, expire_on_commit=False)
    # Seed the row so the default-vs-changed check is meaningful.
    session.add(UserModelSettings(profile_id=_AUD_PROFILE))
    await session.commit()
    try:
        yield session
    finally:
        await session.close()
        await engine.dispose()


def _aud_setup(monkeypatch, vault, order):
    stub = _StubSelector()
    monkeypatch.setattr(model_settings_api, "get_model_selector", lambda: stub)
    monkeypatch.setattr(model_settings_api, "can_run_tier", lambda hw, tier: True)

    async def _noop_download(**kwargs):
        return None

    monkeypatch.setattr(model_settings_api, "_download_model_task", _noop_download)

    calls = []

    async def spy(**kwargs):
        calls.append(kwargs)
        order.append("audit")

    monkeypatch.setattr(model_settings_api, "create_audit_log", spy)

    real_commit = vault.commit

    async def _commit():
        await real_commit()
        order.append("vault")

    monkeypatch.setattr(vault, "commit", _commit)
    return stub, calls


def _aud_client(master):
    return route_client(
        model_settings_api.router, "/settings/model",
        profile_id=_AUD_PROFILE, master_db=master,
        raise_server_exceptions=False,
    )


@pytest.mark.parametrize("route", list(_AUD_ROUTES))
@pytest.mark.asyncio
async def test_hc_audcms_001_audit_row_after_vault_commit(route, aud_vault, monkeypatch):
    method, path, body, event, entity, details, _ = _AUD_ROUTES[route]
    order: list[str] = []
    _, calls = _aud_setup(monkeypatch, aud_vault, order)
    master = MagicMock()
    master.commit = AsyncMock(side_effect=lambda: order.append("master_commit"))

    with _aud_client(master) as client:
        async def _pdb():
            return aud_vault
        client.app.dependency_overrides[get_profile_db_session] = _pdb
        resp = client.request(method, f"/settings/model{path}", json=body)

    assert resp.status_code == 200, resp.text
    assert len(calls) == 1
    call = calls[0]
    assert call["event_type"] == event
    assert call["action"] == event
    assert call["entity_type"] == "settings"
    assert call["entity_id"] == entity
    assert call["details"] == details
    assert call["profile_id"] == _AUD_PROFILE
    assert order == ["vault", "audit", "master_commit"]
    master.commit.assert_awaited()


@pytest.mark.parametrize("route", list(_AUD_ROUTES))
@pytest.mark.asyncio
async def test_hc_audcms_002_audit_commit_failure_logged_and_raised(
    route, aud_vault, monkeypatch, caplog
):
    method, path, body, event, entity, details, column = _AUD_ROUTES[route]
    order: list[str] = []
    stub, _ = _aud_setup(monkeypatch, aud_vault, order)
    master = MagicMock()

    async def _failing_commit():
        order.append("master_commit")
        raise RuntimeError("audit db down")

    master.commit = AsyncMock(side_effect=_failing_commit)
    caplog.set_level(logging.INFO)

    with _aud_client(master) as client:
        async def _pdb():
            return aud_vault
        client.app.dependency_overrides[get_profile_db_session] = _pdb
        resp = client.request(method, f"/settings/model{path}", json=body)

    assert resp.status_code == 500
    assert order == ["vault", "audit", "master_commit"]
    if column is None:
        assert _STUB_CALL[route] in stub.calls
    else:
        row = (await aud_vault.execute(
            select(UserModelSettings).where(UserModelSettings.profile_id == _AUD_PROFILE)
        )).scalar_one()
        assert getattr(row, column[0]) == column[1]
    records = [r for r in caplog.records
               if r.levelno == logging.ERROR and "AUDIT-ORDER" in r.getMessage()]
    assert len(records) == 1
    assert entity in records[0].getMessage()
    assert "America/New_York" not in caplog.text
    assert "mid" not in caplog.text


# --- AUDIT-C-MSET-EXT: audit row after external-api settings save (HC-AUDCMS-003/004) ---

_EXT_BODY = {
    "use_external_api": True,
    "provider": "openai",
    "api_key": "sk-canary-123",
    "consent_acknowledged": True,
}


def _ext_put(vault, master, body=None):
    with _aud_client(master) as client:
        async def _pdb():
            return vault

        async def _enc():
            return EncryptionManager()

        client.app.dependency_overrides[get_profile_db_session] = _pdb
        client.app.dependency_overrides[get_profile_encryption_manager] = _enc
        return client.put(
            "/settings/model/external-api", json=_EXT_BODY if body is None else body
        )


@pytest.mark.asyncio
async def test_hc_audcms_003_external_api_audit_row_after_vault_commit(
    aud_vault, monkeypatch
):
    order: list[str] = []
    _, calls = _aud_setup(monkeypatch, aud_vault, order)
    master = MagicMock()
    master.commit = AsyncMock(side_effect=lambda: order.append("master_commit"))

    resp = _ext_put(aud_vault, master)

    assert resp.status_code == 200, resp.text
    assert len(calls) == 1
    call = calls[0]
    assert call["event_type"] == "settings.external_api.update"
    assert call["action"] == "settings.external_api.update"
    assert call["entity_type"] == "settings"
    assert call["entity_id"] == "external_api"
    assert call["details"] == {"changed_fields": ["api_key", "provider", "use_external_api"]}
    assert call["profile_id"] == _AUD_PROFILE
    assert "sk-canary-123" not in repr(call)
    assert "openai" not in repr(call)
    assert order == ["vault", "audit", "master_commit"]
    master.commit.assert_awaited()


@pytest.mark.asyncio
async def test_hc_audcms_004_external_api_audit_commit_failure_logged_and_raised(
    aud_vault, monkeypatch, caplog
):
    order: list[str] = []
    _aud_setup(monkeypatch, aud_vault, order)
    master = MagicMock()

    async def _failing_commit():
        order.append("master_commit")
        raise RuntimeError("audit db down")

    master.commit = AsyncMock(side_effect=_failing_commit)
    caplog.set_level(logging.INFO)

    resp = _ext_put(aud_vault, master)

    assert resp.status_code == 500
    assert order == ["vault", "audit", "master_commit"]
    row = (await aud_vault.execute(
        select(UserModelSettings).where(UserModelSettings.profile_id == _AUD_PROFILE)
    )).scalar_one()
    assert row.external_api_key_encrypted.startswith("gAAAAA")
    assert row.external_api_key_encrypted != "sk-canary-123"
    assert row.use_external_api is True
    records = [r for r in caplog.records
               if r.levelno == logging.ERROR and "AUDIT-ORDER" in r.getMessage()]
    assert len(records) == 1
    assert "external_api" in records[0].getMessage()
    assert "sk-canary-123" not in caplog.text


@pytest.mark.asyncio
async def test_hc_audcms_005_external_api_save_without_key_keeps_key_and_audits_no_key(
    aud_vault, monkeypatch
):
    order: list[str] = []
    _, calls = _aud_setup(monkeypatch, aud_vault, order)
    master = MagicMock()
    master.commit = AsyncMock()

    resp1 = _ext_put(aud_vault, master)
    assert resp1.status_code == 200, resp1.text
    row = (await aud_vault.execute(
        select(UserModelSettings).where(UserModelSettings.profile_id == _AUD_PROFILE)
    )).scalar_one()
    stored_key = row.external_api_key_encrypted
    assert stored_key.startswith("gAAAAA")

    resp2 = _ext_put(
        aud_vault,
        master,
        {"use_external_api": False, "provider": "openai", "consent_acknowledged": False},
    )

    assert resp2.status_code == 200, resp2.text
    assert len(calls) == 2
    assert calls[1]["details"] == {"changed_fields": ["provider", "use_external_api"]}
    assert resp2.json()["api_key_configured"] is True
    row = (await aud_vault.execute(
        select(UserModelSettings)
        .where(UserModelSettings.profile_id == _AUD_PROFILE)
        .execution_options(populate_existing=True)
    )).scalar_one()
    assert row.external_api_key_encrypted == stored_key
    assert row.use_external_api is False
    assert "sk-canary-123" not in resp2.text
    assert stored_key not in resp2.text
    assert "sk-canary-123" not in repr(calls[1])
    assert stored_key not in repr(calls[1])


# --- AGENT-ENABLED-TOGGLE: PATCH /settings/model/agent through HTTP (HC-AET-001) ---

@pytest.mark.asyncio
async def test_hc_aet_001_agent_toggle_persists_and_audits(aud_vault, monkeypatch):
    stub, calls = _aud_setup(monkeypatch, aud_vault, [])

    async def _active_tier(profile_id, db):
        return "template"

    stub.get_active_tier = _active_tier
    master = MagicMock()
    master.commit = AsyncMock()

    with _aud_client(master) as client:
        async def _pdb():
            return aud_vault
        client.app.dependency_overrides[get_profile_db_session] = _pdb
        before = client.get("/settings/model")
        resp = client.patch("/settings/model/agent", json={"agent_enabled": False})
        after = client.get("/settings/model")

    assert before.status_code == 200, before.text
    assert before.json()["agent_enabled"] is True
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"agent_enabled": False}
    assert after.status_code == 200, after.text
    assert after.json()["agent_enabled"] is False
    agent_rows = [c for c in calls if c["event_type"] == "settings.agent.update"]
    assert len(agent_rows) == 1
